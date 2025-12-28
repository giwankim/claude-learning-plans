# Event-Driven Systems Learning Plan for Kotlin/Spring Boot Developers

Building event-driven microservices requires mastering **Apache Kafka**, understanding **architectural patterns** like CQRS and Saga, and implementing robust **error handling and observability**. This learning plan provides a structured 16-20 week curriculum with curated resources, practical projects, and Kotlin-specific guidance. All core learning materials are available free, with optional paid courses for accelerated, hands-on learning.

---

## Phase 1: Foundations of event-driven architecture (Weeks 1-3)

This foundational phase establishes the conceptual framework for understanding why event-driven systems exist and how they differ from request-response architectures. **Estimated time: 20-25 hours.**

### Core concepts to master

Event-driven architecture treats **events as first-class citizens**—immutable facts representing something that happened. Understanding the distinction between events, commands, and queries is essential:

- **Events**: Immutable facts about past occurrences ("OrderPlaced", "PaymentProcessed")
- **Commands**: Requests for action ("PlaceOrder", "ProcessPayment")
- **Queries**: Information requests with no side effects ("GetOrderStatus")

Event types include **domain events** (business-meaningful occurrences), **integration events** (cross-boundary communication), and **notification events** (lightweight signals). Event schemas define contracts between producers and consumers.

### Recommended resources

| Resource | Type | Time | Access |
|----------|------|------|--------|
| **"Designing Event-Driven Systems"** by Ben Stopford | Book | 4-6 hrs | **Free PDF** from Confluent |
| Confluent Developer: Designing Event-Driven Microservices | Course | 2.75 hrs | Free |
| Martin Fowler's "What do you mean by Event-Driven?" | Article | 45 min | Free |
| Solace Ultimate Guide to EDA Patterns | Guide | 1 hr | Free |
| AsyncAPI Event-Driven Architectures Guide | Documentation | 1 hr | Free |

**Primary reading**: Start with Ben Stopford's "Designing Event-Driven Systems" (https://www.confluent.io/resources/ebook/designing-event-driven-systems/). Despite being Kafka-focused, it excellently covers why streaming beats request-response, replayable logs as system backbone, and event collaboration patterns. The book's diagrams are particularly praised for clarity.

**Complementary viewing**: Martin Fowler's GOTO 2017 talk "The Many Meanings of Event-Driven Architecture" distinguishes four patterns often conflated: event notification, event-carried state transfer, event sourcing, and CQRS.

### Practical project: Event storming workshop

Before writing code, practice **event storming**—a collaborative design technique. Model a simple domain (e.g., online bookstore):

1. Identify domain events (BookOrdered, PaymentReceived, BookShipped)
2. Map commands triggering events (OrderBook → BookOrdered)
3. Define aggregates and bounded contexts
4. Design event schemas with required fields

**Deliverable**: Event catalog with 10-15 domain events, their schemas, and producer/consumer mapping.

---

## Phase 2: Apache Kafka deep dive (Weeks 4-6)

Kafka serves as the messaging backbone for most event-driven microservices. This phase covers core internals, delivery semantics, and operational fundamentals. **Estimated time: 25-30 hours.**

### Essential Kafka concepts

**Architecture fundamentals**: Topics organize events by category, partitions enable parallelism and ordering, consumer groups provide scalable consumption, and brokers form the distributed cluster. **Partitioning strategy directly impacts ordering guarantees**—events with the same key always land in the same partition.

**Delivery semantics** represent critical knowledge:
- **At-most-once**: Messages may be lost but never duplicated
- **At-least-once**: Messages delivered at least once, may duplicate
- **Exactly-once**: Each message processed exactly once (requires idempotent producers + transactions)

Exactly-once semantics, available since Kafka 0.11, uses idempotent producers (`enable.idempotence=true`) and transactions for atomic writes across partitions.

### Recommended resources

| Resource | Type | Time | Access |
|----------|------|------|--------|
| Confluent Apache Kafka 101 | Video Course | 1.5 hrs | Free |
| **"Kafka: The Definitive Guide" 2nd Ed** | Book | 15-20 hrs | **Free PDF** from Confluent |
| Stephane Maarek's Kafka for Beginners v3 (Udemy) | Course | 8.5 hrs | ~$15-20 |
| Confluent Kafka Streams 101 | Video Course | 2.25 hrs | Free |
| Apache Kafka Quickstart | Tutorial | 30 min | Free |

**Foundation path**: Complete Confluent's free Kafka 101 course first—it covers core concepts in 18 video modules with 6 hands-on exercises. Then read "Kafka: The Definitive Guide" (https://www.confluent.io/resources/ebook/kafka-the-definitive-guide/) chapters 1-6 covering producers, consumers, internals, and reliability.

**Accelerated hands-on path**: Stephane Maarek's Udemy course (241,000+ students, 4.6/5 rating) includes real-world projects building a Wikimedia producer and OpenSearch consumer. Updated for Kafka 4.0 in 2025.

### Deep dive resources for specific topics

- **Exactly-once semantics**: Confluent blog "Exactly Once Semantics Are Possible" + Baeldung tutorial
- **Consumer groups**: Kafka documentation on group coordination
- **Partitioning**: Understanding key-based partitioning for ordering guarantees

### Practical project: Real-time event pipeline

Build a Kafka pipeline processing real-time data:

```kotlin
// Producer sending events to Kafka
@Service
class OrderEventProducer(private val kafkaTemplate: KafkaTemplate<String, OrderEvent>) {
    fun publishOrderCreated(order: Order) {
        val event = OrderCreatedEvent(
            orderId = order.id,
            customerId = order.customerId,
            items = order.items,
            timestamp = Instant.now()
        )
        kafkaTemplate.send("orders", order.id.toString(), event)
    }
}
```

**Project requirements**:
1. Create multi-partition topic with key-based routing
2. Implement producer with idempotence enabled
3. Build consumer group with 3 consumers
4. Monitor consumer lag using `kafka-consumer-groups` CLI
5. Experiment with rebalancing by stopping/starting consumers

**Deliverable**: Working pipeline with producer, consumers, and documented observations on partition assignment and rebalancing behavior.

---

## Phase 3: Spring Boot Kafka integration (Weeks 7-9)

Spring Kafka provides elegant abstractions over Kafka clients. Spring Cloud Stream offers higher-level, binder-agnostic programming. **Estimated time: 20-25 hours.**

### Spring Kafka fundamentals

Spring Kafka's **KafkaTemplate** handles message production while **@KafkaListener** provides declarative consumption. The official documentation now includes **Kotlin code tabs alongside Java**, making adaptation straightforward.

```kotlin
@Configuration
class KafkaConfig {
    @Bean
    fun kafkaTemplate(
        producerFactory: ProducerFactory<String, Any>
    ): KafkaTemplate<String, Any> = KafkaTemplate(producerFactory)
}

@Component
class OrderListener {
    @KafkaListener(topics = ["orders"], groupId = "order-processor")
    fun handleOrder(event: OrderEvent, ack: Acknowledgment) {
        processOrder(event)
        ack.acknowledge() // Manual acknowledgment
    }
}
```

**Important Kotlin note**: Spring Kafka does **not** natively support Kotlin coroutines in `@KafkaListener` methods. For reactive workloads, use reactor-kafka. Virtual threads (Project Loom) represent the preferred path forward for non-blocking Kafka consumption.

### Spring Cloud Stream overview

Spring Cloud Stream provides a functional programming model with automatic serialization, DLQ support, and binder abstraction:

```kotlin
@Bean
fun processOrder(): Function<OrderEvent, ShipmentEvent> = { order ->
    ShipmentEvent(orderId = order.id, status = "PROCESSING")
}
```

### Recommended resources

| Resource | Type | Access |
|----------|------|--------|
| Spring Kafka Reference Guide | Documentation | https://docs.spring.io/spring-kafka/reference/ |
| Spring Boot Kafka Auto-configuration | Documentation | https://docs.spring.io/spring-boot/reference/messaging/kafka.html |
| Spring Cloud Stream Kafka Binder | Documentation | https://docs.spring.io/spring-cloud-stream/ |
| Codersee: Apache Kafka with Spring Boot and Kotlin | Tutorial | https://blog.codersee.com/apache-kafka-with-spring-boot-and-kotlin/ |
| Confluent: Spring Framework and Apache Kafka | Course (Free) | 1.5 hrs |
| Baeldung: Intro to Apache Kafka with Spring | Tutorial | https://www.baeldung.com/spring-kafka |

**Kotlin-specific tutorials**:
- DEV.to: "Spring Cloud Stream Step by Step" with Kotlin examples
- Sylhare blog: "Kafka with Spring Boot in Kotlin" covering @EmbeddedKafka testing
- Medium: "Asynchronous Webhook Handling with WebFlux, Kotlin Coroutines and Kafka"

### Practical project: Order processing microservice

Build a complete order processing service:

1. **Order Service**: Accepts HTTP orders, publishes `OrderCreated` events
2. **Inventory Service**: Consumes orders, checks stock, publishes `InventoryReserved` or `InventoryInsufficient`
3. **Notification Service**: Consumes all events, sends notifications

**Technical requirements**:
- Use Spring Kafka with Kotlin
- Implement JSON serialization with Jackson
- Configure consumer groups per service
- Add health checks for Kafka connectivity

**Deliverable**: Three-service system with Docker Compose for local Kafka, demonstrating event flow across service boundaries.

---

## Phase 4: Architectural patterns (Weeks 10-13)

This phase covers patterns that solve distributed data management challenges. **Estimated time: 35-40 hours.**

### CQRS: Command Query Responsibility Segregation

CQRS separates read and write models, enabling independent optimization. Martin Fowler warns that "for most systems CQRS adds risky complexity"—use it selectively for bounded contexts where reads vastly outnumber writes or require different data shapes.

| Aspect | Command Side | Query Side |
|--------|--------------|------------|
| Model | Optimized for writes | Optimized for reads |
| Database | Normalized, consistent | Denormalized, eventual |
| Scaling | Vertical typically | Horizontal easily |

**Key resources**:
- Martin Fowler's CQRS bliki (https://martinfowler.com/bliki/CQRS.html)
- Microsoft Azure Architecture Center CQRS Pattern
- Baeldung: Axon Framework Guide (Spring Boot implementation)

### Event sourcing

Instead of storing current state, event sourcing stores **all events that led to current state**. Benefits include complete audit trail, temporal queries, and event replay for rebuilding projections. Challenges include increased complexity, event schema evolution, and handling external system interactions during replay.

```kotlin
// Event-sourced aggregate
class Order : AggregateRoot() {
    lateinit var orderId: UUID
    var status: OrderStatus = OrderStatus.PENDING
    
    @CommandHandler
    fun handle(cmd: PlaceOrderCommand) {
        apply(OrderPlacedEvent(cmd.orderId, cmd.items))
    }
    
    @EventSourcingHandler
    fun on(event: OrderPlacedEvent) {
        this.orderId = event.orderId
        this.status = OrderStatus.PLACED
    }
}
```

**Key resources**:
- Martin Fowler's Event Sourcing (https://martinfowler.com/eaaDev/EventSourcing.html)
- Greg Young's "Versioning in an Event Sourced System" (free Leanpub ebook)
- Microsoft's "Exploring CQRS and Event Sourcing" (free PDF)

### Saga pattern: Managing distributed transactions

Sagas coordinate multi-service transactions through sequences of local transactions with compensating actions for rollback.

| Choreography | Orchestration |
|--------------|---------------|
| Decentralized, event-driven | Centralized coordinator |
| Loosely coupled | Easier debugging |
| Harder to trace flows | Single point of coordination |
| Best for simple workflows | Best for complex flows |

**Framework options for implementation**:
- **Axon Framework**: Spring Boot native, annotation-based sagas
- **Eventuate Tram Sagas**: Orchestration-focused
- **Temporal**: Durable workflow execution with automatic retry
- **Camunda**: BPMN-based process automation

**Key resources**:
- Chris Richardson's microservices.io Saga Pattern
- Microsoft Azure Architecture Saga Design Pattern
- ByteByteGo: "Saga Pattern Demystified"

### Outbox pattern and transactional messaging

The outbox pattern solves the dual-write problem: atomically updating database AND publishing events. Write events to an "outbox" table in the same transaction as business data, then use CDC (Change Data Capture) to relay to Kafka.

```kotlin
@Transactional
fun placeOrder(command: PlaceOrderCommand) {
    val order = orderRepository.save(Order(command))
    // Same transaction - atomic!
    outboxRepository.save(OutboxEvent(
        aggregateType = "Order",
        aggregateId = order.id,
        payload = objectMapper.writeValueAsString(OrderPlacedEvent(order))
    ))
}
// Debezium CDC tails outbox table → publishes to Kafka
```

**Key resources**:
- Chris Richardson's Transactional Outbox (https://microservices.io/patterns/data/transactional-outbox.html)
- Debezium: Reliable Microservices Data Exchange with Outbox Pattern
- Confluent Developer: Transactional Outbox Pattern course module

### Event-carried state transfer

Events contain **full state data** rather than just references. Consumers maintain local copies, reducing latency and improving resilience when source services are unavailable. Trade-off: data replication and eventual consistency management.

**Key resource**: Martin Fowler's "What do you mean by Event-Driven?" covers this pattern alongside others.

### Recommended books for patterns

| Book | Author | Focus | Access |
|------|--------|-------|--------|
| **"Building Event-Driven Microservices"** | Adam Bellemare | Comprehensive patterns | O'Reilly (~$45) |
| "Microservices Patterns" | Chris Richardson | Saga, CQRS, Event Sourcing | Manning (~$50) |
| "Practical Event-Driven Microservices Architecture" | Hugo Rocha | Migration patterns | Apress (~$50) |

Adam Bellemare's book (2nd edition 2024) is **the definitive resource** for this phase—it covers domain-driven design integration, testing strategies, and deployment patterns for event-driven systems.

### Practical project: E-commerce order saga

Implement a complete order saga with compensating transactions:

**Services**: Order, Payment, Inventory, Shipping

**Happy path**:
1. OrderService creates order → publishes `OrderCreated`
2. PaymentService reserves funds → publishes `PaymentReserved`
3. InventoryService reserves items → publishes `InventoryReserved`
4. ShippingService creates shipment → publishes `ShipmentCreated`
5. OrderService marks complete

**Compensation path** (payment fails):
1. InventoryService releases reservation
2. Order marked as failed

**Technical requirements**:
- Implement using Axon Framework OR custom choreography
- Use transactional outbox for reliable publishing
- Implement idempotent event handlers
- Add saga state visualization

**Deliverable**: Working saga demonstrating both happy and compensation paths with comprehensive logging.

---

## Phase 5: Schema management and evolution (Week 14)

Schema management prevents breaking changes from disrupting consumers. **Estimated time: 10-12 hours.**

### Confluent Schema Registry

Schema Registry provides centralized schema storage with **compatibility enforcement**. Compatibility modes include:

- **BACKWARD**: New schema can read old data (add optional fields)
- **FORWARD**: Old schema can read new data (remove optional fields)  
- **FULL**: Both backward and forward compatible
- **TRANSITIVE** variants: Check against all previous versions

### Apache Avro fundamentals

Avro provides compact binary serialization with schema evolution support:

```avro
{
  "type": "record",
  "name": "OrderEvent",
  "namespace": "com.example.events",
  "fields": [
    {"name": "orderId", "type": "string"},
    {"name": "amount", "type": "double"},
    {"name": "currency", "type": "string", "default": "USD"} // Safe addition
  ]
}
```

### Recommended resources

| Resource | Type | Access |
|----------|------|--------|
| Confluent Schema Registry 101 | Course | Free (41 min) |
| Confluent Schema Evolution Documentation | Docs | https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html |
| Expedia: Practical Schema Evolution with Avro | Article | Medium (excellent Q&A) |
| Baeldung: Spring Cloud Stream with Avro and Schema Registry | Tutorial | Free |

### Practical project: Schema evolution exercise

1. Create v1 schema for OrderEvent
2. Add optional field (v2)—verify backward compatibility
3. Attempt breaking change—observe rejection
4. Implement schema migration strategy

**Deliverable**: Documented schema evolution workflow with compatibility testing.

---

## Phase 6: Error handling and resilience (Week 15)

Production systems require robust error handling. **Estimated time: 12-15 hours.**

### Dead letter queues (DLQ)

Failed messages route to DLQ topics for later analysis and reprocessing. Spring Kafka's `@RetryableTopic` provides declarative non-blocking retry:

```kotlin
@RetryableTopic(
    attempts = "4",
    backoff = Backoff(delay = 1000, multiplier = 2.0),
    dltTopicSuffix = "-dlt"
)
@KafkaListener(topics = ["orders"], groupId = "order-processor")
fun processOrder(event: OrderEvent) {
    // Processing logic - exceptions trigger retry
}

@DltHandler
fun handleDeadLetter(event: OrderEvent) {
    logger.error("Message failed all retries: $event")
    alertService.notifyOperations(event)
}
```

### Idempotency patterns

Idempotent consumers handle duplicate messages gracefully:

1. **Deduplication table**: Store processed message IDs
2. **Idempotent operations**: Design operations to be naturally repeatable
3. **Version checks**: Reject stale updates

### Recommended resources

| Resource | Type | Access |
|----------|------|--------|
| Uber: Reliable Reprocessing and DLQ | Blog | https://www.uber.com/blog/reliable-reprocessing/ |
| Kai Waehner: Error Handling via DLQ | Blog | Comprehensive with case studies |
| Lydtech: Kafka Consumer Retry Patterns | Tutorial | Stateless vs stateful retry |
| Spring Kafka Non-Blocking Retries | Documentation | Official reference |

### Practical project: Resilient consumer

Build a consumer demonstrating:
1. Retry with exponential backoff
2. DLQ routing for poison messages
3. Idempotent processing with deduplication
4. Monitoring dashboard for DLQ depth

**Deliverable**: Consumer handling various failure modes with observability.

---

## Phase 7: Testing event-driven systems (Week 16)

Testing distributed, asynchronous systems requires specialized approaches. **Estimated time: 10-12 hours.**

### Testing strategies

**Unit testing**: Test event handlers in isolation with mock producers/consumers.

**Integration testing**: Use embedded Kafka or Testcontainers for realistic broker interaction:

```kotlin
@SpringBootTest
@Testcontainers
class OrderIntegrationTest {
    companion object {
        @Container
        val kafka = KafkaContainer(DockerImageName.parse("confluentinc/cp-kafka:7.4.0"))
        
        @JvmStatic
        @DynamicPropertySource
        fun kafkaProperties(registry: DynamicPropertyRegistry) {
            registry.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers)
        }
    }
    
    @Test
    fun `order event triggers inventory reservation`() {
        // Publish event, await async processing, verify state
    }
}
```

**Contract testing**: Pact enables consumer-driven contracts for event schemas.

### Recommended resources

| Resource | Type | Access |
|----------|------|--------|
| Spring Kafka Testing Documentation | Docs | Official reference |
| Testcontainers Kafka Module Guide | Tutorial | https://testcontainers.com/guides/testing-spring-boot-kafka-listener-using-testcontainers/ |
| Baeldung: Testing Kafka and Spring Boot | Tutorial | EmbeddedKafka + Testcontainers |
| Pact Kafka Documentation | Docs | Contract testing for messages |

### Practical project: Comprehensive test suite

Build test coverage including:
1. Unit tests for event handlers
2. Integration tests with Testcontainers
3. Contract tests with Pact for event schemas
4. End-to-end saga testing

**Deliverable**: Test suite with >80% coverage and documented testing strategy.

---

## Phase 8: Observability and monitoring (Weeks 17-18)

Observability enables understanding system behavior in production. **Estimated time: 15-18 hours.**

### Three pillars for Kafka systems

**Metrics** (what happened):
- Producer throughput and latency
- **Consumer lag** (critical health indicator)
- Message processing duration
- Error rates and DLQ depth

**Traces** (request flow):
OpenTelemetry provides distributed tracing across Kafka producers and consumers:

```yaml
# application.yml
management:
  tracing:
    sampling:
      probability: 1.0
  otlp:
    tracing:
      endpoint: http://localhost:4318/v1/traces
```

**Logs** (detailed context):
Structured logging with correlation IDs enables log aggregation and search.

### Recommended resources

| Resource | Type | Access |
|----------|------|--------|
| OpenTelemetry Kafka Instrumentation | Blog | https://opentelemetry.io/blog/2022/instrument-kafka-clients/ |
| Spring Kafka Micrometer Monitoring | Documentation | Official reference |
| Instaclustr: Tracing Kafka with OpenTelemetry | Tutorial | Jaeger + SigNoz setup |
| Strimzi OpenTelemetry Guide | Blog | Kubernetes-focused |

### Practical project: Observability stack

Deploy complete observability:
1. Prometheus for metrics collection
2. Grafana dashboards for consumer lag visualization
3. Jaeger for distributed tracing
4. ELK stack or Loki for log aggregation

**Deliverable**: Dashboard showing real-time system health with alerting for consumer lag.

---

## Phase 9: Distributed systems challenges (Weeks 19-20)

Understanding CAP theorem implications and eventual consistency management. **Estimated time: 12-15 hours.**

### Eventual consistency strategies

Most microservices interactions use eventual consistency. Key strategies:

1. **Design idempotent operations**: Safe to replay
2. **Use event logs for reconciliation**: Source of truth
3. **Implement compensating transactions**: Saga rollback
4. **Monitor consistency windows**: Alert on excessive lag
5. **Design for failure**: Graceful degradation

### When strong consistency is required

Reserve strong consistency for:
- Financial ledgers and transactions
- Distributed locking
- Real-time inventory during flash sales
- Safety-critical coordination

### Recommended resources

| Resource | Type | Access |
|----------|------|--------|
| Solace: Eventual Consistency in Microservices | Blog | Event-driven vs REST comparison |
| DZone: Data Consistency in Microservices | Article | Saga pattern focus |
| Chris Richardson's Virtual Bootcamp | Course | Distributed Data Patterns (Paid) |

### Capstone project: Production-ready e-commerce platform

Build a complete event-driven e-commerce system:

**Services**: Catalog, Cart, Order, Payment, Inventory, Shipping, Notification

**Requirements**:
- Event sourcing for Order aggregate
- CQRS for catalog queries (read-optimized projections)
- Saga pattern for order fulfillment
- Transactional outbox with Debezium CDC
- Schema Registry with Avro
- Comprehensive error handling with DLQ
- Full observability stack
- Integration and contract tests

**Deliverable**: Production-ready system with documentation, runbooks, and architecture decision records.

---

## Learning timeline summary

| Phase | Focus | Duration | Key Deliverable |
|-------|-------|----------|-----------------|
| 1 | EDA Fundamentals | Weeks 1-3 | Event catalog |
| 2 | Kafka Deep Dive | Weeks 4-6 | Real-time pipeline |
| 3 | Spring Kafka | Weeks 7-9 | Order processing microservices |
| 4 | Architectural Patterns | Weeks 10-13 | E-commerce saga |
| 5 | Schema Management | Week 14 | Schema evolution workflow |
| 6 | Error Handling | Week 15 | Resilient consumer |
| 7 | Testing | Week 16 | Comprehensive test suite |
| 8 | Observability | Weeks 17-18 | Monitoring dashboard |
| 9 | Distributed Systems | Weeks 19-20 | Capstone platform |

**Total estimated time**: 160-200 hours over 16-20 weeks

---

## Quick-start resource collection

### Essential free resources
1. **Confluent Developer** (https://developer.confluent.io/courses/) - 30+ hours of free courses
2. **"Designing Event-Driven Systems"** - Free PDF from Confluent
3. **"Kafka: The Definitive Guide"** - Free PDF from Confluent
4. **Spring Kafka Documentation** - Official reference with Kotlin examples

### Best paid resources
1. **Stephane Maarek's Udemy Kafka Series** (~$15-20 per course on sale)
2. **"Building Event-Driven Microservices"** by Adam Bellemare (~$45)
3. **Chris Richardson's Virtual Bootcamp** - Distributed data patterns

### Certification path
1. **Confluent Fundamentals Accreditation** (Free)
2. **Confluent Certified Developer (CCDAK)** (~$200)

---

## Conclusion

This learning plan transforms a Kotlin/Spring Boot developer into an event-driven systems practitioner through **progressive skill building**—from conceptual foundations through production-ready implementation. The combination of freely available Confluent resources, practical projects, and Kotlin-specific guidance creates an efficient path to competency.

**Three key insights** emerge from this curriculum: First, event-driven architecture requires both conceptual understanding (events vs commands, eventual consistency) AND practical skills (Kafka internals, Spring integration). Second, patterns like CQRS and Event Sourcing add significant complexity—use them selectively for appropriate bounded contexts, not system-wide. Third, production readiness requires equal investment in error handling, testing, and observability as in core functionality.

Start with Phase 1's conceptual foundations before diving into Kafka mechanics. The capstone project integrates all concepts into a portfolio-worthy demonstration of event-driven expertise.