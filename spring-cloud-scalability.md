---
title: "Spring Cloud Scalability"
category: "Spring & Spring Boot"
description: "Microservices scalability patterns with Spring Cloud"
---

# Microservices Scalability Patterns with Spring Boot and Spring Cloud

Spring Boot provides robust implementations for all major microservices scalability patterns, with **Kotlin coroutines integration** making reactive and event-driven patterns particularly elegant. For an experienced developer deploying to AWS EKS with Kafka and Redis, the most impactful patterns are event-driven architecture with Spring Cloud Stream (enables independent service scaling), CQRS with Axon Framework (separates read/write workloads), and horizontal scaling through session externalization with Spring Session. Virtual Threads in Spring Boot 3.2+ now offer a compelling alternative to reactive programming for I/O-bound workloads, reducing code complexity while maintaining high throughput.

This guide covers implementation details, Kotlin code examples, and critical guidance on when each pattern helps versus when it adds unnecessary complexity—a crucial distinction since over-engineering with patterns like Event Sourcing or CQRS in simple domains is a common anti-pattern.

---

## CQRS separates reads from writes for independent scaling

Command Query Responsibility Segregation splits your application into a **command model** (handling writes) and a **query model** (handling reads), allowing each to scale independently and use optimized storage. This pattern shines when read and write workloads have vastly different scaling requirements—a common scenario where reads outnumber writes 10:1 or more.

**Axon Framework** provides the most mature Spring Boot implementation, with the `axon-spring-boot-starter` handling command routing, event publishing, and query dispatching automatically. For simpler needs, a lightweight custom approach using Spring's `ApplicationEventPublisher` with Kafka for event distribution works well.

```kotlin
// Axon Framework Command Handler (Kotlin)
@Aggregate
class OrderAggregate() {
    @AggregateIdentifier
    private lateinit var orderId: String
    
    @CommandHandler
    constructor(command: CreateOrderCommand) : this() {
        AggregateLifecycle.apply(
            OrderCreatedEvent(
                orderId = command.orderId,
                customerId = command.customerId,
                totalAmount = command.totalAmount
            )
        )
    }
    
    @EventSourcingHandler
    fun on(event: OrderCreatedEvent) {
        this.orderId = event.orderId
    }
}

// Query Side Projection (separate read model)
@Component
class OrderProjection(private val orderViewRepository: OrderViewRepository) {
    @QueryHandler
    fun handle(query: FindOrderByIdQuery): OrderView? =
        orderViewRepository.findById(query.orderId).orElse(null)
    
    @EventHandler
    fun on(event: OrderCreatedEvent) {
        orderViewRepository.save(OrderView(event.orderId, event.customerId, "CREATED"))
    }
}
```

**Kafka as the event bus** between command and query sides enables multiple query services to maintain their own projections, each optimized for specific access patterns. Configure Spring Cloud Stream to publish domain events to Kafka topics, with consumer groups ensuring each projection receives all events.

**When to avoid CQRS:** Simple CRUD applications, domains with minimal business logic, systems requiring strict real-time consistency, or teams unfamiliar with event-driven patterns. As Martin Fowler warns, "CQRS is a significant mental leap... the majority of cases I've run into have not been so good."

---

## Event Sourcing stores state as immutable events

Rather than storing current state, Event Sourcing persists **all state changes as an append-only sequence of events**. Current state is reconstructed by replaying events. This provides a complete audit trail, enables temporal queries ("what was the order status on January 15th?"), and naturally complements CQRS—though they're independent patterns.

Axon Framework with Axon Server provides a production-ready event store, while a custom implementation using Kafka as the event log with a backing database for snapshots offers more control:

```kotlin
// Custom Event Store with Kafka
@Service
class KafkaEventStore(
    private val kafkaTemplate: KafkaTemplate<String, DomainEvent>,
    private val eventRepository: EventRepository
) : EventStore {
    
    override fun append(aggregateId: String, events: List<DomainEvent>) {
        events.forEach { event ->
            // Persist to database for replay
            eventRepository.save(StoredEvent(
                aggregateId = aggregateId,
                eventType = event::class.simpleName!!,
                payload = objectMapper.writeValueAsString(event),
                version = event.version
            ))
            // Publish to Kafka for projections
            kafkaTemplate.send("event-store", aggregateId, event)
        }
    }
    
    override fun load(aggregateId: String): List<DomainEvent> =
        eventRepository.findByAggregateIdOrderByVersionAsc(aggregateId)
            .map { deserializeEvent(it) }
}
```

**Snapshots** are essential for performance—without them, aggregates with thousands of events become slow to reconstruct. Configure Axon to create snapshots every 100-1000 events, or implement a custom snapshot strategy that triggers based on event count or time.

**Event versioning** becomes critical as your system evolves. Axon's upcasting mechanism transforms old events to new schemas during replay, while a simpler approach adds optional fields with defaults to maintain backward compatibility.

**When NOT to use Event Sourcing:** Simple CRUD systems where audit trails aren't valuable, systems requiring strict real-time consistency, domains with low conflict update scenarios, or projects with tight timelines. The migration cost is high—once committed, changing course is expensive.

---

## Caching strategies multiply throughput with careful invalidation

Multi-level caching combines **Caffeine for sub-millisecond local cache hits** with **Redis for cross-instance consistency**. The Spring Cache abstraction (`@Cacheable`, `@CacheEvict`, `@CachePut`) works seamlessly with both, though multi-level caching requires custom configuration.

```kotlin
@Configuration
@EnableCaching
class MultiLevelCacheConfig(
    private val redisConnectionFactory: RedisConnectionFactory
) {
    @Bean
    fun cacheManager(): CacheManager {
        val caffeine = CaffeineCacheManager().apply {
            setCaffeine(Caffeine.newBuilder()
                .maximumSize(10_000)
                .expireAfterWrite(Duration.ofMinutes(5)))
        }
        
        val redis = RedisCacheManager.builder(redisConnectionFactory)
            .cacheDefaults(RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofHours(1))
                .serializeValuesWith(
                    RedisSerializationContext.SerializationPair
                        .fromSerializer(GenericJackson2JsonRedisSerializer())
                ))
            .build()
        
        return CompositeCacheManager(caffeine, redis)
    }
}

// Service with caching
@Service
class ProductService(private val productRepository: ProductRepository) {
    
    @Cacheable(value = ["products"], key = "#id", sync = true)
    fun getProduct(id: Long): Product? = productRepository.findById(id).orElse(null)
    
    @CacheEvict(value = ["products"], key = "#product.id")
    fun updateProduct(product: Product): Product = productRepository.save(product)
}
```

**Cache-aside** (application manages cache) is the most common pattern in Spring applications, while **read-through** and **write-behind** patterns are less common but useful for specific scenarios. The key configuration decision is **invalidation strategy**:

- **TTL-based:** Simple but allows stale data; configure per-cache TTLs based on data volatility
- **Event-based:** Use Redis Pub/Sub to broadcast invalidation events across instances
- **Version-based:** Include version in cache key; old versions expire naturally

**Cache stampede prevention** is critical under high load. Use `sync = true` in `@Cacheable` for single-instance locking, or implement distributed locking with Redis for cross-instance protection.

**When caching adds complexity without benefit:** Write-heavy workloads, rapidly changing data, user-specific sensitive data, or systems already achieving target latency without caching.

---

## Reactive programming handles more requests with fewer threads

Spring WebFlux with Project Reactor replaces the **thread-per-request model** (200 Tomcat threads blocking on I/O) with an **event loop model** where a small number of threads handle thousands of concurrent connections. Kotlin coroutines provide the cleanest integration, converting reactive types to familiar suspend functions:

```kotlin
@RestController
@RequestMapping("/orders")
class OrderController(private val orderService: OrderService) {
    
    @GetMapping("/{id}")
    suspend fun getOrder(@PathVariable id: String): Order =
        orderService.findById(id) ?: throw NotFoundException()
    
    @GetMapping("/stream", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
    fun streamOrders(): Flow<Order> = orderService.findAll()
    
    @GetMapping("/aggregate")
    suspend fun aggregateData(userId: String): UserDashboard = coroutineScope {
        val ordersDeferred = async { orderService.findByUser(userId) }
        val profileDeferred = async { userService.getProfile(userId) }
        val recommendationsDeferred = async { recommendationService.getFor(userId) }
        
        UserDashboard(
            orders = ordersDeferred.await(),
            profile = profileDeferred.await(),
            recommendations = recommendationsDeferred.await()
        )
    }
}
```

**R2DBC** provides reactive database access for PostgreSQL, MySQL, and other databases, enabling true end-to-end non-blocking:

```kotlin
interface OrderRepository : CoroutineCrudRepository<Order, Long> {
    @Query("SELECT * FROM orders WHERE customer_id = :customerId")
    fun findByCustomerId(customerId: String): Flow<Order>
}
```

**When reactive helps:** I/O-bound workloads with high concurrency, streaming data requirements, microservices making many downstream HTTP calls.

**When reactive doesn't help or hurts:** CPU-bound workloads (reactive adds overhead), simple CRUD with low concurrency, debugging complexity outweighs benefits, or blocking libraries (JDBC, JPA without R2DBC) negate the advantages.

---

## Virtual Threads offer blocking code with non-blocking scalability

Spring Boot 3.2+ supports **Project Loom virtual threads**, enabling the scalability of reactive programming with familiar blocking code. Enable with a single property:

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

This activates virtual threads for web requests, `@Async` methods, `@Scheduled` tasks, and message listeners. **No code changes required**—existing blocking code now yields during I/O instead of blocking OS threads.

```kotlin
// Existing blocking code works unchanged with virtual threads
@RestController
class UserController(
    private val userRepository: UserRepository,  // Standard JPA
    private val restTemplate: RestTemplate       // Blocking HTTP client
) {
    @GetMapping("/users/{id}/profile")
    fun getUserProfile(@PathVariable id: Long): UserProfile {
        val user = userRepository.findById(id).orElseThrow()  // Virtual thread yields
        val orders = restTemplate.getForObject<List<Order>>("/orders?userId=$id")
        return UserProfile(user, orders)
    }
}
```

**Virtual threads vs reactive comparison:** Benchmarks show virtual threads win in **45% of scenarios**, WebFlux wins in **30%**, with the remainder tied. WebFlux shows slightly better throughput at **800+ concurrent users**, while virtual threads have lower P99 latency in many high-load scenarios.

**For Kotlin developers:** Coroutines + WebFlux provides better structured concurrency, cancellation support, and Kotlin-native patterns than virtual threads. Virtual threads are most valuable when migrating existing blocking Java/Kotlin codebases without reactive rewrite.

---

## Asynchronous processing decouples request handling from work

**Spring Cloud Stream with Kafka** provides the production-grade solution for offloading work to background processors:

```kotlin
// Producer: Accept request immediately, process later
@RestController
class OrderController(private val streamBridge: StreamBridge) {
    
    @PostMapping("/orders")
    fun createOrder(@RequestBody request: CreateOrderRequest): ResponseEntity<AsyncResponse> {
        val correlationId = UUID.randomUUID().toString()
        streamBridge.send("order-processing", OrderCommand(request, correlationId))
        
        return ResponseEntity.accepted().body(
            AsyncResponse(correlationId, statusUrl = "/orders/status/$correlationId")
        )
    }
}

// Consumer: Process asynchronously with error handling
@Configuration
class OrderProcessorConfig {
    @Bean
    fun processOrder(orderService: OrderService): (OrderCommand) -> Unit = { command ->
        orderService.process(command)
    }
}
```

```yaml
spring:
  cloud:
    stream:
      bindings:
        processOrder-in-0:
          destination: orders
          group: order-processor
          consumer:
            concurrency: 3
            max-attempts: 3
            back-off-initial-interval: 1000
      kafka:
        bindings:
          processOrder-in-0:
            consumer:
              enable-dlq: true
              dlq-name: orders.errors
```

**@Async** works for simple fire-and-forget scenarios but lacks durability—work is lost on restart. Configure a bounded `ThreadPoolTaskExecutor` to prevent resource exhaustion:

```kotlin
@Configuration
@EnableAsync
class AsyncConfig : AsyncConfigurer {
    override fun getAsyncExecutor(): Executor = ThreadPoolTaskExecutor().apply {
        corePoolSize = 4
        maxPoolSize = 10
        queueCapacity = 100
        setRejectedExecutionHandler(CallerRunsPolicy())
        initialize()
    }
}
```

**Decision guide:** Use `@Async` for non-critical fire-and-forget operations; use **message queues (Kafka)** for cross-service communication, durability requirements, or long-running tasks.

---

## Database scaling patterns handle read-heavy workloads

**Read replicas with AbstractRoutingDataSource** automatically route read-only transactions to replicas:

```kotlin
class TransactionRoutingDataSource : AbstractRoutingDataSource() {
    override fun determineCurrentLookupKey(): Any =
        if (TransactionSynchronizationManager.isCurrentTransactionReadOnly())
            DataSourceType.REPLICA
        else
            DataSourceType.PRIMARY
}

@Configuration
class DataSourceConfig {
    @Bean
    @Primary
    fun routingDataSource(
        @Qualifier("primary") primary: DataSource,
        @Qualifier("replica") replica: DataSource
    ): DataSource = TransactionRoutingDataSource().apply {
        setTargetDataSources(mapOf(
            DataSourceType.PRIMARY to primary,
            DataSourceType.REPLICA to replica
        ))
        setDefaultTargetDataSource(primary)
    }
}

// Service usage - automatic routing
@Service
@Transactional
class OrderService(private val orderRepository: OrderRepository) {
    
    fun createOrder(order: Order) = orderRepository.save(order)  // → PRIMARY
    
    @Transactional(readOnly = true)
    fun getOrder(id: Long) = orderRepository.findById(id)  // → REPLICA
}
```

**HikariCP tuning** for Kubernetes requires careful pool sizing. The formula `connections = (core_count × 2) + spindle_count` translates to approximately **10 connections per pod** for modern SSDs. Critical: total pool size across all pods must not exceed database max connections.

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      minimum-idle: 2
      connection-timeout: 10000
      max-lifetime: 900000  # 15 min for cloud DB failovers
      keepalive-time: 300000
```

---

## Event-driven architecture enables independent service scaling

Spring Cloud Stream with Kafka allows producers and consumers to scale independently. **Consumer groups** distribute load across instances, while **partitions** determine maximum parallelism:

```yaml
spring:
  cloud:
    stream:
      bindings:
        processOrder-in-0:
          destination: orders
          group: order-processor-group  # All instances share workload
          consumer:
            concurrency: 3  # 3 threads per instance
      kafka:
        binder:
          min-partition-count: 10  # Maximum parallelism
```

**Scaling math:** With 10 partitions and 3 pods × 3 concurrency = 9 active consumers (optimal). If instances × concurrency > partitions, some consumers idle. Increase partition count to enable more parallelism.

**KEDA** (Kubernetes Event-Driven Autoscaler) scales consumers based on Kafka lag:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-consumer-scaler
spec:
  scaleTargetRef:
    name: order-consumer-deployment
  minReplicaCount: 1
  maxReplicaCount: 10  # Should not exceed partition count
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka:9092
      consumerGroup: order-processor-group
      topic: orders
      lagThreshold: "100"
```

---

## Horizontal scaling requires stateless services and externalized state

**Spring Session with Redis** externalizes HTTP session state, enabling seamless horizontal scaling:

```kotlin
// build.gradle.kts
implementation("org.springframework.session:spring-session-data-redis")
```

```yaml
spring:
  session:
    store-type: redis
    timeout: 30m
  data:
    redis:
      host: ${REDIS_HOST}
      port: 6379
```

**Distributed locking with Redisson** prevents race conditions in scaled-out services:

```kotlin
@Service
class InventoryService(private val redissonClient: RedissonClient) {
    
    fun reserveStock(productId: String, quantity: Int): Boolean {
        val lock = redissonClient.getLock("inventory:lock:$productId")
        
        return lock.tryLock(5, 30, TimeUnit.SECONDS).let { acquired ->
            if (!acquired) return false
            try {
                val stock = getStock(productId)
                if (stock >= quantity) {
                    updateStock(productId, stock - quantity)
                    true
                } else false
            } finally {
                if (lock.isHeldByCurrentThread) lock.unlock()
            }
        }
    }
}
```

**Graceful shutdown** is essential for zero-downtime scaling:

```yaml
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

```yaml
# Kubernetes deployment
spec:
  terminationGracePeriodSeconds: 60
  containers:
  - lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "sleep 10"]
```

---

## API Composition aggregates microservice data efficiently

The **Backend for Frontend (BFF)** pattern creates dedicated backends for each client type (mobile, web), aggregating and transforming data. Spring WebFlux with coroutines provides the cleanest implementation:

```kotlin
@Service
class MobileProductCompositionService(
    private val productClient: ProductServiceClient,
    private val reviewClient: ReviewServiceClient
) {
    suspend fun getProductForMobile(productId: String): MobileProductResponse = coroutineScope {
        val productDeferred = async { productClient.getProduct(productId) }
        val reviewsDeferred = async { reviewClient.getTopReviews(productId, limit = 3) }
        
        val product = productDeferred.await()
        val reviews = reviewsDeferred.await()
        
        MobileProductResponse(
            id = product.id,
            name = product.name,
            imageUrl = "${product.images.first()}?w=400&q=80",  // Optimized for mobile
            averageRating = reviews.map { it.rating }.average()
        )
    }
}
```

**Spring Cloud Gateway** handles cross-cutting concerns (authentication, rate limiting) and can perform simple aggregation via filters. For complex composition, a dedicated BFF service provides more flexibility.

---

## Saga pattern maintains consistency across distributed services

**Orchestration sagas** use a central coordinator (Axon Framework provides first-class support):

```kotlin
@Saga
class OrderSaga {
    @Autowired @Transient
    private lateinit var commandGateway: CommandGateway
    
    @StartSaga
    @SagaEventHandler(associationProperty = "orderId")
    fun handle(event: OrderCreatedEvent) {
        commandGateway.send(ReservePaymentCommand(event.orderId, event.amount))
    }
    
    @SagaEventHandler(associationProperty = "orderId")
    fun handle(event: PaymentReservedEvent) {
        commandGateway.send(ReserveInventoryCommand(event.orderId))
    }
    
    // Compensating transactions
    @SagaEventHandler(associationProperty = "orderId")
    fun handle(event: InventoryReservationFailedEvent) {
        commandGateway.send(ReleasePaymentCommand(event.orderId))
        commandGateway.send(CancelOrderCommand(event.orderId))
    }
}
```

**Choreography sagas** use event publishing without central coordination, implemented via Spring Cloud Stream. Simpler for 2-4 services but harder to trace flow.

**Critical pitfalls:** Always implement **idempotent handlers** (check if already processed), persist saga state before sending commands, and implement **timeout handling** with Axon's `DeadlineManager`.

---

## Essential resources for deeper learning

**Books ranked by relevance:**
- **Chris Richardson's "Microservices Patterns"** — Best for understanding "why" behind patterns; covers Saga, CQRS, Event Sourcing in depth
- **Magnus Larsson's "Microservices with Spring Boot and Spring Cloud" (4th Edition)** — Best for "how" with Spring Boot 3, Kubernetes deployment, Spring Cloud Gateway
- **Sam Newman's "Building Microservices" (2nd Edition)** — Excellent for organizational patterns and architecture strategy

**Official documentation:**
- Axon Framework Spring Boot Integration: `docs.axoniq.io/axon-framework-reference`
- Spring Cloud Stream Reference: `docs.spring.io/spring-cloud-stream`
- Spring WebFlux Coroutines: `docs.spring.io/spring-framework/reference/languages/kotlin/coroutines.html`
- KEDA Kafka Scaler: `keda.sh/docs/scalers/apache-kafka`

**GitHub repositories with Kotlin examples:**
- `hsenasilva/sample-cqrs` — CQRS + Event Sourcing with Kotlin, Axon, Kafka
- `idugalic/digital-restaurant` — DDD, Event Sourcing, CQRS with Axon and Kotlin
- `PacktPublishing/Microservices-with-Spring-Boot-and-Spring-Cloud-Third-Edition` — Magnus Larsson's book companion code
- `learnk8s/spring-boot-k8s-hpa` — Spring Boot HPA with custom metrics tutorial

---

## Conclusion

The most impactful patterns for a Spring Boot/Kotlin deployment on AWS EKS center on **event-driven architecture with Spring Cloud Stream** (enabling independent service scaling through Kafka partitions and KEDA), **CQRS with Axon Framework** (separating read/write concerns when workload ratios justify complexity), and **horizontal scaling through statelessness** (Spring Session + Redis, distributed locking with Redisson). 

Virtual Threads in Spring Boot 3.2+ represent a pragmatic middle ground—achieving reactive-level throughput with blocking code style—though Kotlin coroutines remain superior for greenfield Kotlin projects. The critical insight across all patterns: **apply complexity only where it delivers measurable value**. Event Sourcing and CQRS are powerful but frequently over-applied; most services perform better as simple, stateless request handlers with externalized session state and event-driven communication.