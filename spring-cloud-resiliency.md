# Spring Cloud for Microservices: Resiliency & Scalability Mastery Plan

A structured 14-week curriculum for an experienced Spring Boot / Kotlin developer, focused on building deeply resilient and horizontally scalable microservice architectures using the modern Spring Cloud stack.

This plan assumes completion of (or concurrent progress on) the Spring Framework & Boot internals curriculum, and leverages your existing Kafka and Redis foundations.

---

## The Modern Spring Cloud Landscape (2025)

Before diving in, it's important to understand how the Spring Cloud ecosystem has evolved. Many of the Netflix OSS components that defined the first generation of Spring Cloud have been retired or replaced:

| Retired (Netflix OSS) | Modern Replacement | Status |
|---|---|---|
| Hystrix | **Resilience4j** via Spring Cloud Circuit Breaker | Production-ready, actively maintained |
| Zuul 1 | **Spring Cloud Gateway** (Project Reactor-based) | De facto standard |
| Ribbon | **Spring Cloud LoadBalancer** | Built-in, no Netflix dependency |
| Spring Cloud Sleuth | **Micrometer Tracing** + OpenTelemetry | Native in Spring Boot 3+ |
| Eureka (still available) | **Spring Cloud Kubernetes** or Eureka | Eureka still maintained; K8s-native preferred on K8s |
| Spring Cloud Config | **Spring Cloud Config** or K8s ConfigMaps | Config Server still actively maintained |

The curriculum below focuses entirely on the modern replacements.

---

## Phase 1: Resiliency Patterns with Resilience4j (Weeks 1–4)

This is the core of the plan. You'll build from understanding individual patterns in isolation to combining them into production-grade failure handling pipelines.

### Week 1–2: Circuit Breaker, Retry, and Fallback Fundamentals

**Conceptual foundation — read first:**

"Release It!" by Michael Nygard (2nd edition, 2018) remains the single best book on stability patterns for distributed systems. Chapters on Circuit Breaker, Bulkhead, Timeout, and Steady State are essential reading that gives you the *why* before the *how*. The patterns Resilience4j implements are directly drawn from this book.

**Resilience4j core documentation:**

Start with the official getting-started guide at `resilience4j.readme.io/docs/getting-started`. Resilience4j 2.x requires Java 17+ and integrates directly with Spring Boot 3. The library is modular — you pull in only the patterns you need. The key patterns to study in order are Circuit Breaker, Retry, Rate Limiter, Bulkhead, and TimeLimiter.

**Spring Cloud Circuit Breaker abstraction:**

Spring Cloud provides an abstraction layer (`spring-cloud-starter-circuitbreaker-resilience4j`) that sits on top of Resilience4j. Understand why the abstraction exists — it allows swapping implementations, though in practice everyone uses Resilience4j now.

**Dependencies for a Kotlin Spring Boot 3 project:**

```kotlin
// build.gradle.kts
implementation("org.springframework.cloud:spring-cloud-starter-circuitbreaker-resilience4j")
implementation("org.springframework.boot:spring-boot-starter-aop") // Required for annotations
implementation("org.springframework.boot:spring-boot-starter-actuator") // For metrics/monitoring
```

**Study materials:**

- Resilience4j official docs: `resilience4j.readme.io` — cover all six modules
- Baeldung "Guide to Resilience4j with Spring Boot" at `baeldung.com/spring-boot-resilience4j`
- Baeldung "Guide to Resilience4j" (standalone, without Spring) at `baeldung.com/resilience4j`
- Reflectoring.io series "Retry with Spring Boot and Resilience4j" at `reflectoring.io/retry-with-springboot-resilience4j/` — the entire series covers all patterns

**Hands-on exercise:** Build two Spring Boot services (Kotlin): an `order-service` that calls a `payment-service`. Implement a `@CircuitBreaker` on the payment call with a fallback method. Configure via `application.yml`:

```yaml
resilience4j:
  circuitbreaker:
    instances:
      paymentService:
        registerHealthIndicator: true
        slidingWindowSize: 10
        minimumNumberOfCalls: 5
        failureRateThreshold: 50
        waitDurationInOpenState: 10s
        permittedNumberOfCallsInHalfOpenState: 3
  retry:
    instances:
      paymentService:
        maxAttempts: 3
        waitDuration: 1s
        enableExponentialBackoff: true
        exponentialBackoffMultiplier: 2
        retryExceptions:
          - java.io.IOException
          - org.springframework.web.client.HttpServerErrorException
```

**Milestone:** Demonstrate the circuit breaker transitioning through CLOSED → OPEN → HALF_OPEN states under simulated failure, and verify via `/actuator/circuitbreakers` and `/actuator/health`.

### Week 3: Bulkhead, Rate Limiter, and TimeLimiter

**Why these matter together:** Circuit breakers protect against failing dependencies. Bulkheads prevent a slow dependency from consuming all your threads. Rate limiters prevent you from overwhelming an upstream service. TimeLimiters set deadlines on async calls. Together they form a complete defense.

**Key concepts:**

Resilience4j provides two bulkhead implementations — **semaphore-based** (limits concurrent calls) and **thread-pool-based** (isolates calls in a dedicated thread pool). The semaphore approach is simpler and works with coroutines; thread-pool provides full isolation but requires `CompletableFuture`.

**Critical: decorator ordering.** When composing multiple patterns, execution order matters. The default Spring Boot annotation ordering is:

```
Retry → CircuitBreaker → RateLimiter → TimeLimiter → Bulkhead → Method
```

This means Retry wraps the outermost layer — it retries the entire chain including circuit breaker evaluation. You can customize order via aspect order properties:

```yaml
resilience4j:
  retry:
    retryAspectOrder: 2  # Higher = outermost
  circuitbreaker:
    circuitBreakerAspectOrder: 1
```

**Study materials:**

- Resilience4j docs: Bulkhead and ThreadPoolBulkhead sections
- The `Decorators` fluent API for programmatic composition (beyond annotations)

**Hands-on exercise:** Extend the order-service with all five patterns combined on the payment call. Implement a `@Bulkhead(name = "paymentService", type = Bulkhead.Type.SEMAPHORE)` alongside your existing circuit breaker. Add rate limiting. Use tools like Apache JMeter or `wrk` to generate concurrent load and observe bulkhead rejections via actuator metrics.

### Week 4: Advanced Resilience — Programmatic API and Testing

**Moving beyond annotations:** The annotation approach (`@CircuitBreaker`, `@Retry`) is convenient but has limits. The programmatic `Decorators` API gives full control:

```kotlin
val supplier: Supplier<String> = Supplier { paymentClient.charge(order) }

val decorated = Decorators.ofSupplier(supplier)
    .withCircuitBreaker(circuitBreaker)
    .withBulkhead(bulkhead)
    .withRetry(retry)
    .decorate()

val result = Try.ofSupplier(decorated)
    .recover { throwable -> "Fallback: ${throwable.message}" }
```

This is especially powerful in Kotlin where you can combine it with coroutines and functional patterns.

**Testing resiliency:** Build integration tests that verify:

- Circuit opens after threshold failures
- Retry respects backoff timing
- Bulkhead rejects when full
- Fallbacks return correct responses
- Metrics are published to Micrometer

Use Testcontainers to spin up dependent services with controllable failure injection (WireMock with fault simulation).

**Study materials:**

- Medium article "Circuit Breaker and Retry with Resilience4j" (Jonhy Silva) — Spring Boot + Kotlin examples
- Official Resilience4j Spring Boot 3 demo at `github.com/resilience4j/resilience4j-spring-boot3-demo`

**Milestone:** You should be able to explain *why* you'd choose specific configurations (sliding window size, failure rate threshold, wait duration) for different service characteristics, and have test coverage proving your resiliency patterns work as intended.

---

## Phase 2: API Gateway and Edge Resiliency (Weeks 5–7)

### Week 5: Spring Cloud Gateway Fundamentals

**Why Gateway matters for resiliency:** The API gateway is your first line of defense. Rate limiting, circuit breaking, and request filtering at the edge prevent malformed or excessive traffic from ever reaching your services.

Spring Cloud Gateway is built on Project Reactor and Netty — it's fully reactive and non-blocking, designed for high throughput. Understanding its filter chain architecture is essential.

**Core architecture concepts:**

- **Routes:** The building blocks — each route has a predicate (when to match) and filters (what to apply)
- **Predicates:** Match on path, header, method, host, query params, time, etc.
- **Filters:** Transform requests/responses — `GatewayFilter` (per-route) and `GlobalFilter` (all routes)
- **Filter chain:** Filters execute in order — "pre" filters before proxying, "post" filters after

**Study materials:**

- Official docs: `docs.spring.io/spring-cloud-gateway/reference/` — read the architecture section first
- Spring blog: "API Rate Limiting with Spring Cloud Gateway" at `spring.io/blog/2021/04/05/api-rate-limiting-with-spring-cloud-gateway/`
- Piotr Minkowski's blog: "Rate Limiting in Spring Cloud Gateway with Redis" at `piotrminkowski.com`

**Hands-on exercise:** Build a gateway in Kotlin that routes to your order-service and payment-service. Configure route predicates, add request/response header manipulation filters, and implement path rewriting.

### Week 6: Gateway Rate Limiting and Circuit Breaking

**Redis-based rate limiting:** Spring Cloud Gateway includes a `RequestRateLimiter` filter backed by Redis using the Token Bucket algorithm. This is production-grade distributed rate limiting out of the box.

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 10
                redis-rate-limiter.burstCapacity: 20
                redis-rate-limiter.requestedTokens: 1
                key-resolver: "#{@userKeyResolver}"
            - name: CircuitBreaker
              args:
                name: orderServiceCB
                fallbackUri: forward:/fallback/orders
```

Key resolver implementations determine *what* you're rate limiting (per user, per IP, per API key):

```kotlin
@Bean
fun userKeyResolver(): KeyResolver = KeyResolver { exchange ->
    Mono.just(exchange.request.remoteAddress?.address?.hostAddress ?: "anonymous")
}
```

**Study materials:**

- Official docs: `RequestRateLimiter` GatewayFilter Factory section
- Baeldung "Rate Limiting With Client IP in Spring Cloud Gateway" at `baeldung.com/spring-cloud-gateway-rate-limit-by-client-ip`
- Andi Falk's Gateway Workshop: `andifalk.gitbook.io/spring-cloud-gateway-workshop`

**Hands-on exercise:** Add Redis-based rate limiting and Resilience4j circuit breaking to your gateway. Build a custom `KeyResolver` that resolves by API key from a header. Implement a custom `GatewayFilter` that adds circuit breaker metrics headers to responses.

### Week 7: Custom Gateway Filters and Security at the Edge

**Building custom filters:** Understanding the filter chain lets you implement cross-cutting concerns like authentication token validation, request logging, request/response modification, and custom rate limiting strategies.

```kotlin
@Component
class RequestTimingFilter : GlobalFilter, Ordered {
    override fun filter(exchange: ServerWebExchange, chain: GatewayFilterChain): Mono<Void> {
        val startTime = System.currentTimeMillis()
        exchange.attributes["startTime"] = startTime
        return chain.filter(exchange).then(Mono.fromRunnable {
            val elapsed = System.currentTimeMillis() - startTime
            logger.info("Request ${exchange.request.path} took ${elapsed}ms")
        })
    }
    override fun getOrder() = -1 // Execute early
}
```

**Study materials:**

- Spring Cloud Gateway docs: Writing Custom GatewayFilter Factories
- Spring Cloud Gateway docs: Writing Custom Global Filters

**Hands-on exercise:** Build a custom `AbstractGatewayFilterFactory` that implements JWT validation, extracting claims and passing them as headers to downstream services. This is a common production pattern where the gateway handles auth so services don't have to.

**Milestone:** Your gateway should route to multiple services, rate limit per client, circuit break on downstream failures, and apply custom filters — all observable via actuator endpoints.

---

## Phase 3: Service Discovery and Client-Side Load Balancing (Weeks 8–9)

### Week 8: Service Discovery — Eureka vs. Kubernetes Native

This week addresses a critical architectural decision: should your Spring Cloud services use a dedicated service registry (Eureka) or rely on Kubernetes-native DNS-based discovery?

**Option A — Spring Cloud Eureka:**

Eureka remains the default for non-Kubernetes deployments or when you need client-side awareness of instance health beyond what K8s provides.

```yaml
# Eureka Server
eureka:
  client:
    register-with-eureka: false
    fetch-registry: false
  server:
    enable-self-preservation: false

# Eureka Client (each microservice)
eureka:
  client:
    service-url:
      defaultZone: http://eureka:8761/eureka/
  instance:
    prefer-ip-address: true
```

**Option B — Spring Cloud Kubernetes:**

On Kubernetes, the platform already provides service discovery through DNS and Services. `spring-cloud-kubernetes-discovery` integrates with the K8s API to populate Spring's `DiscoveryClient`, enabling `@LoadBalanced` RestTemplate/WebClient without Eureka.

```kotlin
// Works identically with both Eureka and K8s discovery
@Bean
@LoadBalanced
fun webClientBuilder(): WebClient.Builder = WebClient.builder()

// Then call by service name
webClient.get()
    .uri("http://payment-service/api/payments/{id}", paymentId)
    .retrieve()
    .bodyToMono<Payment>()
```

**When to use which:**

- **Eureka:** Non-K8s environments, need for client-side health filtering, multi-datacenter scenarios, need to see registry dashboard
- **K8s native DNS:** Simplest approach on Kubernetes — no Spring Cloud discovery needed, just use K8s Service DNS names
- **Spring Cloud Kubernetes:** When you want Spring's `DiscoveryClient` abstraction on K8s for client-side load balancing across pods, or integration with Istio

**Study materials:**

- Spring Cloud Kubernetes reference: `docs.spring.io/spring-cloud-kubernetes/reference/`
- Baeldung "Guide to Spring Cloud Kubernetes" at `baeldung.com/spring-cloud-kubernetes`
- GitHub issue discussion on K8s vs client-side load balancing: `github.com/spring-cloud/spring-cloud-kubernetes/issues/298`

**Hands-on exercise:** Deploy your microservices to a local Kubernetes cluster (Minikube or Kind). First, use plain K8s DNS for service-to-service calls. Then add `spring-cloud-starter-kubernetes-client` and `@LoadBalanced` WebClient and observe client-side load balancing across multiple pod replicas.

### Week 9: Spring Cloud LoadBalancer and Inter-Service Communication

**Spring Cloud LoadBalancer** replaced Ribbon as the default client-side load balancer. It integrates with `DiscoveryClient` (Eureka, K8s, or Consul) to maintain an instance list and distribute requests.

**Load balancing strategies:**

- `RoundRobinLoadBalancer` (default)
- `RandomLoadBalancer`
- Custom: implement `ReactorServiceInstanceLoadBalancer`

**OpenFeign for declarative REST clients:**

```kotlin
@FeignClient(name = "payment-service")
interface PaymentClient {
    @PostMapping("/api/payments")
    fun createPayment(@RequestBody request: PaymentRequest): PaymentResponse
}
```

Feign integrates with Resilience4j — you can add `@CircuitBreaker` directly on Feign methods. This is a clean production pattern.

**WebClient with load balancing (reactive):**

For reactive services, use `@LoadBalanced` `WebClient.Builder` instead of Feign. This is often more natural in Kotlin with coroutines.

**Study materials:**

- Spring Cloud LoadBalancer docs
- Spring Cloud OpenFeign reference documentation
- Baeldung series on Spring Cloud OpenFeign

**Hands-on exercise:** Implement inter-service communication using both OpenFeign (for synchronous calls) and `@LoadBalanced` WebClient (for reactive calls). Add Resilience4j circuit breakers to both. Scale your payment-service to 3 replicas and verify load distribution.

**Milestone:** Your services discover each other dynamically, distribute load across instances, and handle instance failures gracefully through circuit breakers and load balancer health checks.

---

## Phase 4: Event-Driven Resiliency with Spring Cloud Stream (Weeks 10–11)

This phase leverages your Kafka foundation and connects it to Spring Cloud's messaging abstraction for building resilient, asynchronous microservices.

### Week 10: Spring Cloud Stream with Kafka

**Why event-driven = resilient:** Synchronous HTTP calls create temporal coupling — both services must be running simultaneously. Asynchronous event-driven communication via Kafka decouples services in time. If the consumer is down, messages wait in the topic. This is the single most impactful resiliency improvement for most architectures.

**Spring Cloud Stream's functional programming model:** Modern Spring Cloud Stream uses `java.util.function` interfaces — `Supplier`, `Function`, and `Consumer` — for producing, processing, and consuming events. No more `@StreamListener` (deprecated).

```kotlin
@Configuration
class OrderEventProcessor {

    @Bean
    fun processOrder(): Function<OrderCreatedEvent, PaymentRequestEvent> {
        return Function { event ->
            // Transform order event into payment request
            PaymentRequestEvent(
                orderId = event.orderId,
                amount = event.totalAmount,
                customerId = event.customerId
            )
        }
    }

    @Bean
    fun handlePaymentResult(): Consumer<PaymentResultEvent> {
        return Consumer { event ->
            logger.info("Payment ${event.status} for order ${event.orderId}")
        }
    }
}
```

```yaml
spring:
  cloud:
    stream:
      bindings:
        processOrder-in-0:
          destination: order-events
          group: payment-processor
        processOrder-out-0:
          destination: payment-requests
        handlePaymentResult-in-0:
          destination: payment-results
          group: order-service
      kafka:
        binder:
          brokers: localhost:9092
```

**Study materials:**

- Official Spring Cloud Stream reference docs: `docs.spring.io/spring-cloud-stream/`
- Spring Cloud Stream Kafka Binder reference
- Foojay article "Spring Cloud Stream for Real-Time Event-Driven Systems"

### Week 11: Error Handling, Dead Letter Topics, and Idempotency

**Error handling is where event-driven resiliency gets serious.** Spring Cloud Stream provides built-in mechanisms for dealing with message processing failures.

**Retry and dead-letter queue (DLQ) configuration:**

```yaml
spring:
  cloud:
    stream:
      bindings:
        processOrder-in-0:
          destination: order-events
          group: payment-processor
          consumer:
            max-attempts: 3
            back-off-initial-interval: 1000
            back-off-multiplier: 2.0
      kafka:
        bindings:
          processOrder-in-0:
            consumer:
              enableDlq: true
              dlqName: order-events.payment-processor.dlq
              dlqPartitions: 1
```

**Idempotent consumers:** In distributed systems, messages can be delivered more than once (at-least-once delivery). Your consumers must be idempotent — processing the same message twice should produce the same result. Common strategies include deduplication tables, database upserts, and idempotency keys.

**Partition-based ordering:** Kafka guarantees order within a partition. Use message keys to ensure related events are processed in order:

```kotlin
@Bean
fun orderEventProducer(): Supplier<Message<OrderCreatedEvent>> {
    return Supplier {
        MessageBuilder
            .withPayload(event)
            .setHeader(KafkaHeaders.KEY, event.customerId.toByteArray())
            .build()
    }
}
```

**Hands-on exercise:** Build a complete event-driven order processing pipeline: order-service → Kafka → payment-service → Kafka → notification-service. Implement DLQ handling, idempotent consumers, and manual offset acknowledgment. Simulate failures and verify messages land in DLQ after retries are exhausted.

**Milestone:** Your event-driven pipeline handles failures gracefully with retries, DLQ, and idempotent processing. You can demonstrate zero message loss under consumer failures.

---

## Phase 5: Observability for Resilient Systems (Weeks 12–13)

Resiliency patterns are only useful if you can observe them in production. This phase builds the monitoring and tracing infrastructure that makes your resiliency visible.

### Week 12: Distributed Tracing with Micrometer and OpenTelemetry

**The modern Spring Boot observability stack:**

Spring Boot 3+ uses **Micrometer** as the observability facade (replacing Spring Cloud Sleuth). Micrometer's Observation API creates observations that produce both metrics and traces. You choose a tracer bridge — either OpenZipkin Brave or OpenTelemetry. OpenTelemetry with OTLP export is the recommended path forward.

**Dependencies (Spring Boot 3.x):**

```kotlin
implementation("org.springframework.boot:spring-boot-starter-actuator")
implementation("io.micrometer:micrometer-tracing-bridge-otel")
implementation("io.opentelemetry:opentelemetry-exporter-otlp")
```

**Spring Boot 4 simplification:** Spring Boot 4 consolidates this into a single `spring-boot-starter-opentelemetry` starter that auto-configures metrics, traces, and log export via OTLP.

**Configuration:**

```yaml
management:
  tracing:
    sampling:
      probability: 1.0  # 100% in dev, tune for production
  otlp:
    tracing:
      endpoint: http://otel-collector:4318/v1/traces
    metrics:
      endpoint: http://otel-collector:4318/v1/metrics
```

**Key insight:** Micrometer Tracing automatically propagates trace context across HTTP calls (RestTemplate, WebClient, OpenFeign) and Kafka messages (Spring Cloud Stream). You get distributed tracing across your entire microservice chain with almost zero code changes.

**Study materials:**

- Spring blog: "OpenTelemetry with Spring Boot" (Moritz Halbritter, Nov 2025) at `spring.io/blog/2025/11/18/opentelemetry-with-spring-boot/`
- Spring blog: "Let's use OpenTelemetry with Spring" (Marcin Grzejszczak, Oct 2024) at `spring.io/blog/2024/10/28/lets-use-opentelemetry-with-spring/`
- Baeldung "Observability With Spring Boot" at `baeldung.com/spring-boot-3-observability`

**Hands-on exercise:** Set up a Docker Compose stack with the OpenTelemetry Collector, Jaeger (traces), and Prometheus + Grafana (metrics). Instrument your microservices and trace a request from the API gateway through order-service → Kafka → payment-service. Verify trace context propagation across HTTP and Kafka boundaries.

### Week 13: Metrics, Health Checks, and Resilience Monitoring

**Resilience4j metrics integration:**

Resilience4j automatically publishes metrics to Micrometer when actuator is on the classpath. Key metrics to monitor:

- `resilience4j.circuitbreaker.state` — current state per instance
- `resilience4j.circuitbreaker.calls` — tagged by outcome (successful, failed, not_permitted)
- `resilience4j.circuitbreaker.failure.rate` — current failure rate percentage
- `resilience4j.retry.calls` — tagged by result (successful_without_retry, successful_with_retry, failed_with_retry, failed_without_retry)
- `resilience4j.bulkhead.available.concurrent.calls` — remaining capacity

**Building Grafana dashboards:** Create dashboards that show circuit breaker state transitions over time, retry rates, bulkhead utilization, and rate limiter rejection rates. Correlate these with latency percentiles (p50, p95, p99) and error rates.

**Custom health indicators:**

```kotlin
@Component
class PaymentServiceHealthIndicator(
    private val circuitBreakerRegistry: CircuitBreakerRegistry
) : HealthIndicator {
    override fun health(): Health {
        val cb = circuitBreakerRegistry.circuitBreaker("paymentService")
        return when (cb.state) {
            CircuitBreaker.State.CLOSED -> Health.up()
                .withDetail("state", "CLOSED")
                .withDetail("failureRate", cb.metrics.failureRate)
                .build()
            CircuitBreaker.State.OPEN -> Health.down()
                .withDetail("state", "OPEN")
                .withDetail("failureRate", cb.metrics.failureRate)
                .build()
            CircuitBreaker.State.HALF_OPEN -> Health.unknown()
                .withDetail("state", "HALF_OPEN")
                .build()
            else -> Health.unknown().build()
        }
    }
}
```

**Kubernetes integration:** Map Spring Boot health endpoints to K8s probes:

```yaml
# K8s deployment
livenessProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
```

**Hands-on exercise:** Build a complete Grafana dashboard showing the health of your microservice system. Include panels for circuit breaker states, retry rates, gateway rate limiting, Kafka consumer lag, and end-to-end request latency from distributed traces. Set up alerts for circuit breaker state transitions.

**Milestone:** You should be able to inject failures into any service, watch your resiliency patterns activate in real-time on your dashboards, and trace the exact impact on end-to-end request flow.

---

## Phase 6: Scalability Patterns and Production Hardening (Week 14)

### Week 14: Scaling, Configuration, and Chaos Engineering

**Centralized configuration with Spring Cloud Config:**

Spring Cloud Config Server provides externalized configuration for all your services, backed by Git, Vault, or a database. Combined with `@RefreshScope` and Spring Cloud Bus, you can update configuration across all service instances without restart.

```yaml
# Config Server
spring:
  cloud:
    config:
      server:
        git:
          uri: https://github.com/your-org/config-repo
          default-label: main

# Client service
spring:
  config:
    import: optional:configserver:http://config-server:8888
```

This is critical for resiliency tuning in production — you can adjust circuit breaker thresholds, rate limits, and retry parameters without redeployment.

**Horizontal scaling considerations:**

- **Stateless services:** Ensure your services store no local state — use Redis for sessions, Kafka for event state, databases for persistent state
- **Kafka consumer groups:** Scale consumers by adding instances to the same consumer group — partitions are automatically rebalanced
- **Gateway scaling:** Spring Cloud Gateway is stateless by default; scale it behind a load balancer. Redis-backed rate limiting works across all instances
- **Config refresh:** Use Spring Cloud Bus (backed by Kafka or RabbitMQ) to broadcast config changes to all instances simultaneously

**Chaos engineering — testing resiliency in practice:**

Tools for injecting failures systematically:

- **Chaos Monkey for Spring Boot** (`codecentric/chaos-monkey-spring-boot`): Injects latency, exceptions, and kills beans at runtime
- **Toxiproxy:** Simulates network conditions (latency, bandwidth limitations, connection drops) between services
- **Kubernetes chaos tools:** LitmusChaos, Chaos Mesh for pod kills, network partitions

**Hands-on capstone project:**

Build a complete microservice system that demonstrates everything from this curriculum:

1. **API Gateway** (Spring Cloud Gateway) with rate limiting and circuit breaking
2. **Order Service** (Kotlin) with Resilience4j circuit breaker, retry, and bulkhead on downstream calls
3. **Payment Service** (Kotlin) with intentional failure simulation
4. **Notification Service** consuming events from Kafka via Spring Cloud Stream
5. **Config Server** providing centralized configuration
6. **Eureka Server** (or Kubernetes native discovery) for service discovery
7. **Observability stack:** OpenTelemetry Collector → Jaeger + Prometheus + Grafana
8. **Chaos testing:** Chaos Monkey enabled on all services, with a test scenario that kills the payment service and demonstrates graceful degradation

Deploy the entire system to Kubernetes (Minikube or Kind) with proper health probes, and demonstrate that you can:

- Kill the payment-service → circuit breaker opens → orders get fallback responses → payment-service recovers → circuit closes → orders resume normally
- Overwhelm the gateway → rate limiter kicks in → 429 responses for excess traffic
- Scale order-service from 1 to 5 replicas → load distributes automatically
- Change circuit breaker thresholds via Config Server → refresh propagates without restart
- Trace the entire request flow through all services in Jaeger

---

## Essential Resources Summary

### Books

| Book | Focus | Why |
|---|---|---|
| **Release It!** (Michael Nygard, 2nd ed.) | Stability patterns | The theoretical foundation for everything Resilience4j implements |
| **Microservices with Spring Boot and Spring Cloud** (Magnus Larsson, 3rd ed.) | Full stack | The most comprehensive Spring Cloud + K8s + Istio book available |
| **Practical Microservices Architectural Patterns** (2nd ed., Oct 2025) | Advanced patterns | Updated for Spring Boot 3, covers CQRS, event sourcing, distributed transactions |
| **Spring Boot in Practice** (Somnath Musib) | Production patterns | Good coverage of actuator, metrics, and production deployment |
| **Designing Data-Intensive Applications** (Martin Kleppmann) | Distributed systems theory | Essential background on consistency, replication, and fault tolerance |

### Official Documentation (Bookmark These)

- Spring Cloud Gateway: `docs.spring.io/spring-cloud-gateway/reference/`
- Spring Cloud Circuit Breaker: `docs.spring.io/spring-cloud-circuitbreaker/reference/`
- Spring Cloud Stream: `docs.spring.io/spring-cloud-stream/reference/`
- Spring Cloud Kubernetes: `docs.spring.io/spring-cloud-kubernetes/reference/`
- Resilience4j: `resilience4j.readme.io/docs/`
- Micrometer Tracing: `micrometer.io/docs/tracing`

### Conference Talks (Must Watch)

| Talk | Speaker | Why |
|---|---|---|
| "Resilient Microservices with Spring Cloud" | Ryan Baxter | Spring team overview of modern patterns |
| "It's a Kind of Magic" | Stéphane Nicoll, Brian Clozel | Auto-configuration understanding (supports gateway/discovery internals) |
| "Observability of Your Application" | Jonatan Ivanov | Micrometer + OTel integration deep dive |
| SpringOne talks on resilience | Various | Search the SpringDeveloper YouTube channel |

### GitHub Repositories

| Repository | Purpose |
|---|---|
| `resilience4j/resilience4j-spring-boot3-demo` | Official Spring Boot 3 + Resilience4j demo |
| `PacktPublishing/Microservices-with-Spring-Boot-and-Spring-Cloud-Third-Edition` | Companion code for Larsson's book |
| `spring-cloud/spring-cloud-kubernetes` | Spring Cloud K8s source |
| `codecentric/chaos-monkey-spring-boot` | Chaos engineering for Spring Boot |
| `piomin/sample-spring-cloud-gateway` | Piotr Minkowski's gateway examples |

---

## Success Criteria by Phase

**End of Phase 1 (Week 4):** Can implement and combine all five Resilience4j patterns, configure them via YAML, monitor via actuator, and test with load tools. Understand decorator ordering and can explain when to use semaphore vs thread-pool bulkhead.

**End of Phase 2 (Week 7):** Can build a production-grade API gateway with rate limiting (Redis-backed), circuit breaking, custom filters, and JWT validation. Gateway is observable via actuator.

**End of Phase 3 (Week 9):** Services discover each other dynamically (Eureka or K8s), distribute load across replicas, and handle instance failures via circuit breakers and load balancer health checks.

**End of Phase 4 (Week 11):** Event-driven pipeline handles failures with retries, DLQ, and idempotent consumers. Can demonstrate zero message loss under consumer failures.

**End of Phase 5 (Week 13):** Complete observability stack running — distributed traces across HTTP and Kafka, Resilience4j metrics in Grafana, alerts on circuit breaker state transitions.

**End of Phase 6 (Week 14):** Capstone project deployed on Kubernetes with centralized config, chaos testing, and demonstrated graceful degradation under failure scenarios.

---

## How This Connects to Your Other Learning Tracks

This curriculum integrates naturally with your existing learning:

- **Kafka mastery:** Phase 4 (Spring Cloud Stream) builds directly on your Kafka foundations, adding the Spring abstraction layer and production error handling patterns
- **Redis mastery:** Rate limiting in Spring Cloud Gateway uses Redis, and distributed caching patterns enhance service scalability
- **Spring Boot internals:** Understanding auto-configuration mechanics (from the internals curriculum) helps you debug and customize Spring Cloud component behavior
- **Spring WebFlux:** Spring Cloud Gateway is built on WebFlux/Reactor — your reactive programming knowledge applies directly
- **AWS/EKS deployment:** Phase 3's Kubernetes service discovery and Phase 6's deployment patterns map directly to your EKS expertise
