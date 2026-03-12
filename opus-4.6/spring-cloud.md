---
title: Spring Cloud mastery roadmap for Kotlin engineers on AWS EKS
category: Backend & Infrastructure
description: 26-week curriculum taking Kotlin/Spring Boot developers from zero Spring Cloud knowledge to production-ready microservices on AWS EKS, covering service discovery, config management, and Kubernetes-native migration.
---

# Spring Cloud mastery roadmap for Kotlin engineers on AWS EKS

**This is a 26-week, 8-phase curriculum that takes a mid-level Kotlin + Spring Boot developer from zero Spring Cloud knowledge to production-ready microservices on AWS EKS.** The plan teaches each Spring Cloud project standalone first—Eureka for discovery, Config Server for configuration—then systematically replaces them with Kubernetes-native equivalents via Spring Cloud Kubernetes. Every phase ends with a concrete milestone project that builds toward a complete e-commerce platform. The curriculum targets the **Spring Cloud 2024.0 (Moorgate)** release train with Spring Boot 3.4.x, the most stable production choice as of early 2026, while noting the newer 2025.0 (Northfields) and 2025.1 (Oakwood) trains for forward compatibility.

---

## Current Spring Cloud ecosystem: what's alive, what's dead

Before diving into the curriculum, you need a clear map of the Spring Cloud landscape in 2026. Spring Cloud uses **Calendar Versioning** (CalVer): the active release trains are **2025.1 (Oakwood)** on Spring Boot 4.0/Spring Framework 7, **2025.0 (Northfields)** on Spring Boot 3.5, and **2024.0 (Moorgate)** on Spring Boot 3.4. For production learning, target **2024.0 (Moorgate)** with Spring Boot 3.4.x—it's battle-tested and widely documented. Upgrade to 2025.0 once your team stabilizes on Spring Boot 3.5.

The Netflix OSS components that defined early Spring Cloud are mostly gone. **Hystrix, Ribbon, Zuul, and Archaius were deprecated in 2018 and fully removed by Spring Cloud 2022.0.** Only **Netflix Eureka survives** as an actively maintained project (version 5.0.0 in the 2025.1 train). The replacements are:

- **Hystrix → Spring Cloud Circuit Breaker with Resilience4j** (active, v5.0.0)
- **Ribbon → Spring Cloud LoadBalancer** (active, part of Spring Cloud Commons)
- **Zuul → Spring Cloud Gateway** (active, v5.0.0, now with both WebFlux and MVC variants)
- **Spring Cloud Sleuth → Micrometer Tracing** (migrated in Spring Boot 3.0; Sleuth's last version was 3.1.x)
- **Spring Cloud Data Flow → end of open-source** (April 2025, now Tanzu-commercial only)

Every other project in the curriculum—Config, Bus, Vault, OpenFeign, Stream, Function, Kubernetes, Contract, Task—remains **actively maintained and released** in the current trains.

---

## Phase 0: Ecosystem orientation and development environment (Week 1)

**Goal:** Build the mental model of Spring Cloud's architecture and set up a local development environment that mirrors production.

Start by reading the official Spring Cloud project page at `spring.io/projects/spring-cloud` and the release train compatibility matrix on the `spring-cloud-release` GitHub wiki. Understand how Spring Cloud is organized as an umbrella project with sub-projects, each solving a specific distributed systems concern. Map the **12-factor app** principles to Spring Cloud projects: Config Server = externalized config (Factor III), Eureka = service binding (Factor IV), Stream = backing services as attached resources (Factor IV), and so on.

Set up your local environment with **Docker Compose** running the production stack simulacra: Kafka (with Zookeeper or KRaft), Redis, MySQL, and PostgreSQL via Aurora-compatible images. Install **Minikube** or **kind** for local Kubernetes. Create a multi-module Kotlin Gradle project structure using Spring Initializr with the `spring-cloud-dependencies` BOM for **2024.0.x**. Configure Kotlin-specific settings: `kotlin-spring` compiler plugin (for open classes), `kotlin-jpa` plugin (for no-arg constructors), and coroutine dependencies.

**Key resources for this phase:**
- "Cloud Native Spring in Action" by Thomas Vitale (Manning, 2022)—Chapters 1-3 establish the cloud-native mental model. The book's **Polar Bookshop** project is the best pedagogical example of building a Spring Cloud system end-to-end. The companion code lives at `github.com/ThomasVitale/cloud-native-spring-in-action` with a Spring Boot 3.x branch.
- "Microservices with Spring Boot 3 and Spring Cloud" by Magnus Larsson (Packt, 3rd Edition, 2023)—the most comprehensive single book covering every Spring Cloud project with Spring Boot 3. Code at `github.com/PacktPublishing/Microservices-with-Spring-Boot-and-Spring-Cloud-Third-Edition`. A **4th edition** exists with the latest dependency updates.
- "Spring Microservices in Action" (2nd Edition) by John Carnell & Illary Huaylupo Sánchez (Manning, 2021)—covers Spring Boot 2.x patterns but remains excellent for conceptual understanding of why each Spring Cloud project exists.

**Korean resource:** Samsung SDS's overview article "스프링 클라우드를 활용한 클라우드 네이티브 애플리케이션 개발" at `samsungsds.com/kr/insights/spring_cloud.html` provides a concise Korean-language mapping of all Spring Cloud components. The **Inflearn course "Spring Cloud로 개발하는 마이크로서비스 애플리케이션(MSA)"** by Dowon Lee (`inflearn.com/course/스프링-클라우드-마이크로서비스`) is the most popular Korean-language Spring Cloud course and covers the full stack.

**Milestone:** A running multi-module Kotlin project with Docker Compose, all infrastructure services healthy, and a "hello world" Spring Boot service with Actuator endpoints exposed. You should be able to articulate which Spring Cloud project solves each distributed systems challenge and which Netflix components they replaced.

**Estimated time:** 1 week

---

## Phase 1: Service discovery and centralized configuration (Weeks 2–5)

**Goal:** Implement standalone service discovery with Eureka and centralized configuration with Config Server, Bus, and Vault—understanding the internals before relying on abstractions.

### Week 2-3: Eureka and Config Server from scratch

Since you prefer understanding internals first, begin by **building a naive service registry** yourself—a simple Kotlin service that accepts heartbeat registrations via REST and returns service instance lists. Experience the problems: stale entries, network partitions, consistency vs. availability tradeoffs. Then introduce **Spring Cloud Netflix Eureka** as the production solution.

Build a Eureka Server (`@EnableEurekaServer`) and register **3+ microservices** as Eureka clients. Understand Eureka's AP (availability + partition tolerance) design, self-preservation mode, registry cache refresh intervals (`eureka.client.registryFetchIntervalSeconds`), and heartbeat configuration. Explore the Eureka dashboard. Test failure scenarios: kill a service instance and observe deregistration timing. Configure zone-awareness for multi-AZ simulation.

For Config Server, again start manually: externalize properties to a Git repository, then stand up `@EnableConfigServer`. Configure **Git-backed configuration** with per-environment profiles (`application-dev.yml`, `application-prod.yml`). Implement **config encryption/decryption** using symmetric keys (`encrypt.key`) and asymmetric keys (JKS keystore). Test the `/encrypt` and `/decrypt` endpoints. Implement **`@RefreshScope`** on beans and trigger manual refresh via POST to `/actuator/refresh`.

### Week 4: Spring Cloud Bus and Vault

**Spring Cloud Bus** solves the "refresh every instance manually" problem. Add the Kafka binder for Bus (`spring-cloud-starter-bus-kafka` since Kafka is your production stack). When you POST `/actuator/busrefresh` to any instance, the config change propagates to all instances via Kafka topics. Trace the bus events to understand the message flow.

**Spring Cloud Vault** integrates HashiCorp Vault for secrets management. Set up a local Vault instance in dev mode, store database credentials and API keys, and configure Spring Cloud Vault to inject them as property sources at startup. Understand Vault token authentication, AppRole authentication (for production), and secret rotation. Compare this approach with Spring Cloud Config's encryption—Vault is superior for secrets that rotate frequently.

### Week 5: Integration and milestone project

**Milestone project — "Configuration-Driven Inventory Service":** Build a 3-service system (Inventory Service, Product Service, API Gateway placeholder) with:
- Eureka Server for discovery (services find each other by name, not URL)
- Config Server backed by a private Git repo with encrypted database credentials
- Spring Cloud Bus + Kafka for config refresh propagation
- Vault storing the Aurora MySQL connection credentials
- All services written in Kotlin with coroutine-based controllers
- Integration tests proving that changing a Git-backed property and triggering busrefresh updates all running instances

**Key resources:**
- Baeldung: "Quick Intro to Spring Cloud Configuration" (`baeldung.com/spring-cloud-configuration`), "Spring Cloud Bus" (`baeldung.com/spring-cloud-bus`)
- Official docs: `docs.spring.io/spring-cloud-config/reference/`, `spring.io/projects/spring-cloud-netflix/`
- Magnus Larsson's book, Chapters 12 (Config Server) and 10 (Service Discovery)
- GitHub: `spring-cloud-samples/config-repo` for Git-backed config patterns

**Estimated time:** 4 weeks

---

## Phase 2: API Gateway and inter-service communication (Weeks 6–9)

**Goal:** Master Spring Cloud Gateway as the edge server, OpenFeign for declarative service-to-service calls, and LoadBalancer for client-side load balancing.

### Week 6-7: Spring Cloud Gateway deep dive

Spring Cloud Gateway is built on **Project Reactor and Netty** (WebFlux variant) or Spring MVC (new in 2025.0). Since your team likely uses coroutines with WebFlux, the reactive variant is the natural choice. Study the three core concepts: **Routes** (predicate + URI + filters), **Predicates** (Path, Host, Header, Method, Query, Cookie, Weight, and custom), and **Filters** (AddRequestHeader, RewritePath, CircuitBreaker, RateLimiter, RequestSize, and custom).

Build filters incrementally: first `AddRequestHeader` and `StripPrefix` using YAML configuration, then graduate to **programmatic route definitions** using the Kotlin DSL (`RouteLocatorBuilder`). Implement a **custom GatewayFilter** in Kotlin that adds a correlation ID to every request. Implement a **global filter** for authentication token validation.

**Rate limiting** uses Redis (already in your stack). Configure `RequestRateLimiter` filter with `RedisRateLimiter`, specifying `replenishRate` and `burstCapacity`. Test with load tools to verify throttling behavior.

**Gateway patterns** to implement:
- **Backend for Frontend (BFF):** Create separate route configurations for mobile vs. web clients, each aggregating different backend responses
- **API Composition:** Build a gateway filter that fans out to multiple microservices and aggregates responses before returning to the client
- **Request/response transformation:** Modify request bodies (e.g., inject user context from JWT) and response bodies (e.g., strip internal fields)

### Week 8: OpenFeign and LoadBalancer

**Spring Cloud OpenFeign** provides declarative REST clients. Define a Kotlin interface annotated with `@FeignClient(name = "product-service")`, and Spring Cloud auto-discovers the service via Eureka and load-balances requests via **Spring Cloud LoadBalancer** (the Ribbon replacement). Explore custom Feign configuration: error decoders, request interceptors (for propagating auth headers), and logging levels.

**Spring Cloud LoadBalancer** supports round-robin (default) and random strategies out of the box. Implement a **custom `ServiceInstanceListSupplier`** that adds zone-preference filtering (relevant for multi-AZ EKS). Test LoadBalancer's caching behavior and health-check-based instance filtering.

Also implement **WebClient with service discovery integration**—annotate a `WebClient.Builder` bean with `@LoadBalanced` and use service names as hostnames (`http://product-service/api/products`). Compare the imperative Feign approach with the reactive WebClient approach. For Kotlin coroutines, WebClient's `awaitBody()` extensions make it particularly ergonomic.

**gRPC consideration:** Spring Cloud does not have a first-class gRPC project, but `grpc-spring-boot-starter` (by LogNet or yidongnan) integrates well. 오늘의집 (Ohouse) uses gRPC for internal communication in their MSA—their tech blog at `bucketplace.com/post/2022-01-14-오늘의집-msa-phase-1-백엔드-분리작업/` describes their gRPC + Kafka architecture.

### Week 9: Integration and milestone project

**Milestone project — "E-Commerce Gateway with BFF Pattern":** Extend the Phase 1 system with:
- Spring Cloud Gateway with **10+ configured routes** including path-based, header-based, and weighted predicates
- Redis-backed rate limiting (**5 requests/second** per API key)
- A BFF route that aggregates Product + Inventory + Pricing data into a single response
- OpenFeign clients between services with custom error decoders
- LoadBalancer with health-check filtering
- WebClient-based async calls using Kotlin coroutines for the composition endpoint
- Correlation ID propagation through gateway filters
- All discoverable via Eureka

**Key resources:**
- Baeldung: "Exploring the New Spring Cloud Gateway" (`baeldung.com/spring-cloud-gateway`), "Introduction to Spring Cloud OpenFeign" (`baeldung.com/spring-cloud-openfeign`)
- Thomas Vitale's repo `spring-cloud-gateway-resilience-security-observability` on GitHub—a Spring Boot 3 reference for gateway + resilience + observability
- **Toss engineering: "토스는 Gateway 이렇게 씁니다"** (`toss.tech/article/slash23-server`)—Toss's production Spring Cloud Gateway architecture with Kotlin Coroutines in filters, Prometheus/Grafana monitoring, and Istio integration. This is a must-read for your exact stack.
- Kakao: "이모티콘 서비스는 왜 MSA를 선택했나?" (`tech.kakao.com/posts/457`)—Kakao chose Spring Cloud Gateway over Kong because their team was Spring-native.
- Udemy: Ranga Karanam's "Master Microservices with Spring Boot and Spring Cloud" (250K+ students, 4.5 stars) covers Gateway and Feign comprehensively.

**Estimated time:** 4 weeks

---

## Phase 3: Resilience and fault tolerance (Weeks 10–12)

**Goal:** Implement all five Resilience4j patterns—circuit breaker, retry, bulkhead, rate limiter, time limiter—and integrate them with OpenFeign and Gateway.

### Understanding the internals first

Before using the Spring Cloud Circuit Breaker abstraction, **implement a circuit breaker from scratch in Kotlin**. Build a simple state machine with CLOSED, OPEN, and HALF_OPEN states, a failure counter, and a timeout. This takes about 2 hours and permanently demystifies the pattern. Then introduce **Resilience4j** and appreciate how it handles the edge cases your naive implementation missed: sliding window metrics (count-based and time-based), slow call detection, automatic state transitions, and event publishing.

### Week 10-11: The five Resilience4j patterns

**Circuit Breaker:** Configure `slidingWindowSize`, `failureRateThreshold`, `waitDurationInOpenState`, `permittedNumberOfCallsInHalfOpenState`. Test with a deliberately failing downstream service. Monitor state transitions via Actuator at `/actuator/circuitbreakers`.

**Retry:** Configure `maxAttempts`, `waitDuration`, exponential backoff with `IntervalBiFunction`. Understand the critical interaction: **retries should wrap circuit breakers** (Retry → CircuitBreaker), so retries happen before the circuit breaker counts failures. The default Resilience4j aspect ordering is `Retry(CircuitBreaker(RateLimiter(TimeLimiter(Bulkhead(Function)))))`.

**Bulkhead:** Two flavors—**semaphore bulkhead** (limits concurrent calls) and **thread pool bulkhead** (isolates calls to a separate thread pool). Semaphore is simpler and works with coroutines; thread pool bulkhead does not work with WebFlux/coroutines. Configure `maxConcurrentCalls` and `maxWaitDuration`.

**Rate Limiter:** Server-side rate limiting (distinct from Gateway's Redis-based rate limiting which is client-facing). Configure `limitForPeriod`, `limitRefreshPeriod`, `timeoutDuration`. Useful for protecting downstream services that have known capacity limits.

**Time Limiter:** Wraps calls with a timeout. Configure `timeoutDuration` and `cancelRunningFuture`. Essential for preventing thread starvation from slow downstream services.

### Week 12: Integration with OpenFeign and Gateway

Integrate Resilience4j with OpenFeign using `@CircuitBreaker` on Feign clients and implement **fallback classes** (create a class implementing the Feign interface that returns degraded responses). Integrate with Gateway using the built-in `CircuitBreaker` GatewayFilter factory with `FallbackHeaders`.

**Milestone project — "Chaos-Resistant Order Service":** Add an Order Service to the system that:
- Calls Product, Inventory, and Payment services via OpenFeign with circuit breakers (**50% failure threshold**, 10-second open window)
- Implements retry with exponential backoff for transient failures (max 3 attempts)
- Uses semaphore bulkhead to limit concurrent calls to Payment service to **20**
- Has time limiter of **3 seconds** on all downstream calls
- Gateway-level circuit breaker with fallback returning cached product data from Redis
- **Chaos testing:** Use a toggle to make Payment service fail 60% of the time; verify the circuit opens and fallback activates
- Actuator endpoints expose real-time circuit breaker metrics

**Key resources:**
- Baeldung: "Guide to Resilience4j With Spring Boot" (`baeldung.com/spring-boot-resilience4j`), "Quick Guide to Spring Cloud Circuit Breaker" (`baeldung.com/spring-cloud-circuit-breaker`)
- Official Resilience4j docs: `resilience4j.readme.io`
- Magnus Larsson's book, Chapter 13 (circuit breaker patterns)
- Carnell & Huaylupo Sánchez's book, Chapter 7 (dedicated resiliency patterns chapter)

**Estimated time:** 3 weeks

---

## Phase 4: Event-driven architecture with Spring Cloud Stream (Weeks 13–17)

**Goal:** Master Spring Cloud Stream with the Kafka binder, functional programming model, error handling, DLQ patterns, partitioning, and schema evolution. This phase gets extra time because Kafka is already in your production stack and Spring Cloud Stream will be heavily used.

### Week 13-14: Spring Cloud Stream fundamentals

Again, start from first principles. **Build a raw Kafka producer/consumer using Spring Kafka** (`spring-kafka`) with `KafkaTemplate` and `@KafkaListener`. Experience the boilerplate: serializer configuration, consumer group management, offset handling, error handling. Then introduce **Spring Cloud Stream** and see how it abstracts all of this behind the **functional programming model**.

Spring Cloud Stream's functional model uses `java.util.function` interfaces: `Function<Input, Output>` for processors, `Consumer<Input>` for sinks, and `Supplier<Output>` for sources. In Kotlin, these map beautifully to lambdas:

```kotlin
@Bean
fun processOrder(): Function<OrderEvent, PaymentEvent> = Function { order ->
    PaymentEvent(order.orderId, order.amount)
}
```

The binding is done purely through configuration (`spring.cloud.stream.bindings.processOrder-in-0.destination=orders`). Understand how Spring Cloud Stream's **binder abstraction** decouples your business logic from Kafka entirely—the same code works with RabbitMQ by swapping the binder dependency.

### Week 15: Error handling, DLQ, and partitioning

This is where production reality hits. Implement the three error handling strategies:
- **Stateless retry:** `maxAttempts`, `backOffInitialInterval`, `backOffMultiplier` in binding consumer properties
- **Dead Letter Queue:** `enableDlq: true` with custom `dlqName`. Failed messages route to the DLQ topic after retries exhaust.
- **Custom error handling:** `ListenerContainerCustomizer` for advanced scenarios like conditional DLQ routing

**Partitioning** ensures ordered processing per key. Configure `partitionKeyExpression` (e.g., `headers['orderId']`), `partitionCount`, and `instanceIndex`. Test with multiple consumer instances to verify order guarantee within a partition.

### Week 16: Schema evolution and Spring Cloud Function

**Schema evolution** is critical for event-driven systems. Integrate with **Confluent Schema Registry** (the production standard) using Avro serialization. Configure `spring.cloud.stream.kafka.binder.configuration.schema.registry.url` and use `@EnableSchemaRegistryClient`. Define Avro schemas, generate Kotlin data classes, and test schema backward/forward compatibility. The standalone Spring Cloud Schema Registry is effectively unmaintained—**use Confluent's**.

**Spring Cloud Function** provides a serverless abstraction layer. Define `@Bean` functions and deploy them as Spring Cloud Stream processors, REST endpoints, or AWS Lambda functions. In 2025.1, the web variant is "essentially deprecated" in favor of Spring Boot's native function support, but the core abstraction for Stream integration remains valuable. Practice composing functions: `processOrder|enrichWithInventory|publishPayment` via `spring.cloud.function.definition`.

### Week 17: Milestone project

**Milestone project — "Event-Driven Order Processing Pipeline":** Build a complete order lifecycle:
- **Order Service** publishes `OrderCreated` events to Kafka via Spring Cloud Stream Supplier
- **Payment Service** consumes `OrderCreated`, processes payment, publishes `PaymentProcessed` or `PaymentFailed`
- **Inventory Service** consumes `PaymentProcessed`, reserves stock, publishes `InventoryReserved`
- **Notification Service** consumes terminal events and sends notifications
- **DLQ handling:** Payment failures after 3 retries go to a DLQ; a DLQ processor service retries or escalates
- **Partitioning:** All events for the same order route to the same partition (ordered processing)
- **Avro schemas** registered in Confluent Schema Registry with backward compatibility enforced
- **Schema evolution test:** Add an optional field to `OrderCreated`, deploy new producer and old consumer, verify compatibility
- All services use Kotlin functional beans

**Key resources:**
- **KakaoPay: "Spring Cloud Stream 도입하기"** (`tech.kakaopay.com/post/spring-cloud-stream/`)—Detailed Korean-language article on adopting Spring Cloud Stream with functional model and Kotlin code examples. This is particularly relevant to your stack.
- Official Spring Cloud Stream docs: `spring.io/projects/spring-cloud-stream/`
- GitHub: `rogervinas/spring-cloud-stream-kafka-step-by-step`—**Kotlin-based** step-by-step tutorial covering functional model, DLQ, retries, and Confluent Avro Schema Registry. This is the single best Kotlin + Stream + Kafka repo.
- GitHub: `spring-cloud/spring-cloud-stream-samples`—Official samples including Kafka, Schema Registry, batch consumers
- Ali Gelenler's Udemy course "Event-Driven Microservices: Spring Boot, Kafka and Elastic" (4.6 stars, bestseller)—deep event-driven patterns with Kafka and Spring Cloud
- Spring blog: "Stream Processing with Spring Cloud Stream and Kafka Streams, Part 4 - Error Handling"

**Estimated time:** 5 weeks

---

## Phase 5: Observability—tracing, metrics, and logging (Weeks 18–20)

**Goal:** Implement comprehensive observability using Micrometer Tracing (the Sleuth successor), Prometheus metrics, and distributed tracing with Zipkin or Jaeger.

### The Sleuth-to-Micrometer migration context

Spring Cloud Sleuth was the tracing standard through Spring Boot 2.x. Starting with **Spring Boot 3.0 and Spring Cloud 2022.0**, all tracing moved to **Micrometer Tracing** (`io.micrometer:micrometer-tracing`). The key differences: W3C Trace Context is the default propagation format (not B3), trace IDs are **128-bit** by default, and auto-configuration lives in Spring Boot (not Spring Cloud). Properties changed from `spring.sleuth.*` to `management.tracing.*`. You need either `micrometer-tracing-bridge-brave` (for Zipkin) or `micrometer-tracing-bridge-otel` (for OpenTelemetry/Jaeger).

### Week 18-19: Tracing and metrics implementation

Add **Micrometer Tracing with the Brave bridge** and **Zipkin reporter** to all services. Configure the logging pattern to include trace/span IDs: `%5p [${spring.application.name},%X{traceId:-},%X{spanId:-}]`. Verify that a single HTTP request generates correlated trace spans across Gateway → Order Service → Payment Service → Inventory Service.

**Critical for Kafka:** Trace context propagation across Spring Cloud Stream / Kafka requires the `micrometer-tracing` instrumentation to be present on both producer and consumer sides. Spring Cloud Stream automatically propagates trace headers in Kafka message headers when Micrometer Tracing is on the classpath. Verify this by tracing an order through the entire event-driven pipeline from Phase 4.

Set up **Prometheus scraping** via Spring Boot Actuator's `/actuator/prometheus` endpoint. Export custom business metrics using Micrometer's `Counter`, `Timer`, `Gauge`, and `DistributionSummary`. Build **Grafana dashboards** showing: request rates, error rates, latency percentiles (p50/p95/p99), circuit breaker state, Kafka consumer lag, and JVM metrics.

Implement **custom `Observation`** spans for business-critical operations (e.g., payment processing, inventory reservation) using the Micrometer Observation API directly.

### Week 20: Milestone project

**Milestone project — "Full Observability Stack":** Add to the existing system:
- Distributed tracing across all HTTP calls and Kafka messages with **100% trace completeness** (every request traceable end-to-end)
- Zipkin or Jaeger UI showing the full call graph of an order lifecycle
- Prometheus + Grafana with dashboards for RED metrics (Rate, Errors, Duration) per service
- Custom business metrics: orders processed/minute, payment success rate, average order value
- Correlation ID propagation from Gateway through all services (HTTP and Kafka)
- Structured JSON logging with trace context for ELK/EFK stack compatibility
- Health checks via Actuator for all infrastructure dependencies (Kafka, Redis, DB, Eureka)
- Spring Boot Admin for operational overview (optional but valuable)

**Key resources:**
- Official: `docs.spring.io/spring-boot/reference/actuator/tracing.html`, `docs.micrometer.io/tracing/reference/`
- Baeldung: "Observability With Spring Boot 3" (`baeldung.com/spring-boot-3-observability`)
- Thomas Vitale's `spring-cloud-gateway-resilience-security-observability` repo demonstrates the complete observability pipeline with Grafana, Loki, Prometheus, and Tempo
- Magnus Larsson's book, Chapters 14-15 cover Micrometer Tracing, Prometheus, Grafana, and the EFK logging stack

**Estimated time:** 3 weeks

---

## Phase 6: Spring Cloud Kubernetes—the production migration (Weeks 21–24)

**Goal:** Migrate from standalone Spring Cloud infrastructure (Eureka, Config Server) to Kubernetes-native equivalents using Spring Cloud Kubernetes, targeting AWS EKS deployment.

This is the most architecturally significant phase. In production on EKS, running a separate Eureka cluster and Config Server adds operational burden that Kubernetes already solves natively. Spring Cloud Kubernetes bridges the gap by implementing the same Spring Cloud abstractions (`DiscoveryClient`, `PropertySource`) against Kubernetes APIs.

### Week 21-22: Service discovery and configuration migration

**Step 1 — Kubernetes service discovery replacing Eureka:** Add `spring-cloud-starter-kubernetes-client-all` (using the official Kubernetes Java Client, upgraded to v24.0.0 in 2025.1). Remove `spring-cloud-starter-netflix-eureka-client`. Spring Cloud Kubernetes implements `DiscoveryClient` by querying Kubernetes Endpoints. Your `@FeignClient(name = "product-service")` and `@LoadBalanced` WebClient calls **work identically**—they resolve via Kubernetes Services instead of Eureka. Test that OpenFeign and LoadBalancer function unchanged.

**Step 2 — ConfigMaps and Secrets replacing Config Server:** Create Kubernetes ConfigMaps containing your application YAML. Spring Cloud Kubernetes loads them as `ConfigMapPropertySource`. Create Kubernetes Secrets for database credentials (replacing Vault for basic secrets; Vault remains valuable for dynamic secrets and rotation). Remove `spring-cloud-starter-config` and `spring-cloud-starter-vault`. Configure `spring.cloud.kubernetes.config.sources` to specify which ConfigMaps to load.

**Step 3 — Config reload replacing Bus:** Spring Cloud Kubernetes supports **automatic config reload** when ConfigMaps change. Configure `spring.cloud.kubernetes.reload.enabled=true` with strategy `refresh` (default—updates `@ConfigurationProperties` and `@RefreshScope` beans) or `restart_context` (full context restart). This replaces Spring Cloud Bus entirely. The **Configuration Watcher** component can also notify apps via HTTP `/refresh` or Bus messages.

### Week 23: Leader election and health indicators

**Leader election** uses Kubernetes Lease or ConfigMap objects. Enable with `spring.cloud.kubernetes.leader.election.enabled=true`. This is essential for scenarios like scheduled tasks that should only run on one instance (e.g., report generation, cache warming). Implement a singleton scheduled task using the leader election callback.

**Health indicators** expose Pod metadata (name, IP, namespace, service account, node) through Actuator. Spring Cloud Kubernetes auto-activates the `kubernetes` profile when running inside a cluster, enabling K8s-specific configuration profiles. Configure **liveness and readiness probes** pointing to Actuator health groups.

### Week 24: Milestone project — the full migration

**Milestone project — "EKS-Native E-Commerce Platform":** Migrate the entire system built in Phases 1-5:

| Component | Before (Standalone) | After (K8s-Native) |
|---|---|---|
| Service Discovery | Eureka Server + Client | Kubernetes Services + Spring Cloud Kubernetes DiscoveryClient |
| Configuration | Config Server + Git repo | Kubernetes ConfigMaps + Spring Cloud Kubernetes Config |
| Secrets | Spring Cloud Vault | Kubernetes Secrets (+ AWS Secrets Manager via External Secrets Operator for rotation) |
| Config Propagation | Spring Cloud Bus + Kafka | Spring Cloud Kubernetes Config Reload (event-based) |
| Load Balancing | Spring Cloud LoadBalancer + Eureka | Spring Cloud LoadBalancer + K8s DiscoveryClient |
| Gateway | Spring Cloud Gateway (unchanged) | Spring Cloud Gateway (unchanged, now behind AWS ALB Ingress) |
| Resilience | Resilience4j (unchanged) | Resilience4j (unchanged) |
| Streaming | Spring Cloud Stream + Kafka (unchanged) | Spring Cloud Stream + Kafka (unchanged, Kafka via MSK or Strimzi) |
| Tracing | Micrometer Tracing + Zipkin (unchanged) | Micrometer Tracing + Tempo/Jaeger (unchanged) |

Deploy on a local **kind** cluster first, then provide Helm charts or Kustomize manifests for EKS deployment. Include: Kubernetes Deployments, Services, ConfigMaps, Secrets, Ingress (AWS ALB), HPA (horizontal pod autoscaler), PDB (pod disruption budget), and RBAC for Spring Cloud Kubernetes service account permissions.

**Key resources:**
- Official: `spring.io/projects/spring-cloud-kubernetes/` and the reference documentation
- GitHub: `piomin/sample-spring-microservices-kubernetes`—multiple branches showing K8s deployment with Spring Cloud Kubernetes, OpenFeign, Gateway, and multi-namespace discovery
- GitHub: `spring-petclinic/spring-petclinic-cloud`—PetClinic on Kubernetes with Helm charts
- **AWS Cloud Operations Blog: "Approach to Migrate Spring Cloud Microservices to Amazon EKS"**—comprehensive migration guide mapping Spring Cloud → AWS/K8s services
- Ryan Baxter (Spring Cloud Kubernetes lead) talks: "Spring on Kubernetes" Tanzu Tuesdays talk, and "A Bootiful Podcast" episodes on Spring Cloud Kubernetes
- Thomas Vitale's KubeCon EU 2025 talk: "From 0 to Production-Grade with Kubernetes Native Development"

**Estimated time:** 4 weeks

---

## Phase 7: Contract testing and short-lived tasks (Weeks 25–26)

**Goal:** Add consumer-driven contract testing with Spring Cloud Contract and batch/scheduled processing with Spring Cloud Task.

### Spring Cloud Contract

In a microservices system, **the API contract between services is the single most fragile point**. Spring Cloud Contract lets the service provider define contracts (in Groovy DSL or YAML), auto-generates tests for the provider, and publishes **WireMock stubs** that consumers use in their tests. This ensures both sides agree on the API shape without end-to-end integration tests.

Write contracts for the Product Service API. Run the generated verifier tests on the provider side. On the consumer side (Order Service), use `StubRunner` to auto-download and run WireMock stubs. Extend to **messaging contracts**—define contract expectations for Kafka messages published by Order Service and consumed by Payment Service.

### Spring Cloud Task

Spring Cloud Task manages **short-lived microservices**—batch jobs, data migrations, one-off processing. It records task execution metadata (start time, end time, exit code) in a database. Integrate with Spring Batch for complex batch processing. Build a nightly report generation task that uses leader election (from Phase 6) to ensure only one pod executes it.

**Milestone project — "Contract-Tested, Task-Enabled Platform":**
- **6+ Spring Cloud Contracts** covering REST APIs and Kafka message schemas between all services
- Contract tests running in CI preventing breaking API changes
- WireMock stubs published to a Maven repository (or local) for consumer testing
- A Spring Cloud Task for daily order reconciliation batch processing
- Task execution history stored in Aurora PostgreSQL
- Complete Kotlin test suite using `MockMvc`, `StubRunner`, and Testcontainers

**Key resources:**
- Official: `spring.io/projects/spring-cloud-contract/`
- GitHub: `spring-cloud-samples/spring-cloud-contract-samples`—comprehensive official samples including REST, messaging, Protocol Buffers, and stateful scenarios
- Magnus Larsson's book covers contract testing integration
- 배달의민족's MSA journey (Woowacon 2020 talk by 김영한, YouTube: `youtube.com/watch?v=BnS6343GTkY`) discusses how Woowahan handles service contracts in their MSA

**Estimated time:** 2 weeks

---

## Phase 8: Capstone project—production-grade e-commerce platform (Weeks 27–30, optional)

**Goal:** Consolidate everything into a polished, production-grade system that demonstrates mastery.

Build or refine the accumulated project into a **complete e-commerce platform** with these services:

- **API Gateway** (Spring Cloud Gateway) — rate limiting, BFF routes, circuit breaker fallbacks, correlation ID injection
- **User Service** — authentication, profile management, Aurora PostgreSQL
- **Product Catalog Service** — CRUD, search, Aurora MySQL, Redis caching
- **Order Service** — order lifecycle, saga orchestration via Kafka events
- **Payment Service** — payment processing simulation, circuit breaker to external payment API
- **Inventory Service** — stock management, partitioned Kafka consumption
- **Notification Service** — email/SMS simulation, Spring Cloud Stream consumer
- **Reconciliation Task** — Spring Cloud Task nightly batch job

Infrastructure: All deployed on Kubernetes (kind locally, EKS for production), using Spring Cloud Kubernetes for discovery and config, Confluent Schema Registry for Avro schemas, Micrometer Tracing + Prometheus + Grafana for observability, and Spring Cloud Contract for all service boundaries.

**Estimated time:** 4 weeks (optional extension)

---

## Resource compendium organized by priority

### Books (ranked by relevance to this curriculum)

1. **"Microservices with Spring Boot 3 and Spring Cloud"** — Magnus Larsson (Packt, 3rd/4th Ed., 2023-2024). Most comprehensive. Covers every Spring Cloud project with Spring Boot 3, Kubernetes, Istio, Prometheus/Grafana, and the EFK stack. Code actively maintained on GitHub.
2. **"Cloud Native Spring in Action"** — Thomas Vitale (Manning, 2022). Best for cloud-native mindset and Kubernetes-first development. The Polar Bookshop project is pedagogically excellent. Spring Boot 3.x branch available.
3. **"Spring Microservices in Action"** — Carnell & Huaylupo Sánchez (Manning, 2nd Ed., 2021). Best conceptual explanations of why each Spring Cloud component exists. Spring Boot 2.x but patterns transfer directly.

### Udemy courses (ranked by quality and relevance)

1. **Ali Gelenler — "Microservices: Clean Architecture, DDD, SAGA, Outbox & Kafka"** (4.6★). Best for advanced architectural patterns—DDD, SAGA, Outbox, CQRS with Kafka. Ideal for Phase 4+ depth.
2. **Ali Gelenler — "Event-Driven Microservices: Spring Boot, Kafka and Elastic"** (4.6★, bestseller). Deep event-driven focus with Spring Cloud Config, Sleuth/Zipkin, CQRS, OAuth2. Ideal for Phase 4.
3. **Ranga Karanam / in28minutes — "Master Microservices with Spring Boot and Spring Cloud"** (4.5★, 250K+ students). Best starting point, covers Eureka, Config, Gateway, Docker, Kubernetes. Ideal for Phases 1-2.
4. **Ramesh Fadatare — "Building Microservices with Spring Boot & Spring Cloud"** (4.6★). Great all-rounder with Spring Boot 3, Kafka, and RabbitMQ coverage.
5. **Dilip Sundarraj — "Build Reactive MicroServices using Spring WebFlux/SpringBoot"** (4.5★). Best for reactive specialization. Also offers a Kotlin + Spring Boot REST course.

### Conference talks (highest value)

- **KotlinConf 2025: "Next level Kotlin support in Spring Boot 4"** — Sébastien Deleuze. Essential for understanding Kotlin-first Spring features.
- **KotlinConf 2025: "Kotlin and Spring: The modern server side stack"** — Rod Johnson. The Spring creator's endorsement of Kotlin + Spring.
- **SpringOne 2025: Spencer Gibb & Ryan Baxter** on Spring Cloud roadmap and Kubernetes
- **Spring I/O 2024: "Dapr and Spring Boot"** — Thomas Vitale. Distributed systems patterns.
- **KubeCon EU 2025: "From 0 to Production-Grade with Kubernetes Native Development"** — Thomas Vitale
- **Spring I/O 2024: "The Modern Monolith, with Spring Modulith"** — Cora Iberkleid. Important counterpoint perspective.
- **Josh Long's "Spring Tips" YouTube series** (`bit.ly/spring-tips-playlist`) — weekly screencasts covering individual Spring Cloud features

### Korean tech blog essentials (must-reads)

- **Toss: "토스는 Gateway 이렇게 씁니다"** (`toss.tech/article/slash23-server`) — Production Spring Cloud Gateway with Kotlin Coroutines, Istio integration, Prometheus/Grafana. **Directly applicable to your stack.**
- **KakaoPay: "Spring Cloud Stream 도입하기"** (`tech.kakaopay.com/post/spring-cloud-stream/`) — Spring Cloud Stream adoption with functional model and Kotlin. **Directly applicable to Phase 4.**
- **Woowahan: "배달의민족 마이크로서비스 여행기"** (Woowacon 2020) — The canonical Korean MSA migration case study. Event-driven architecture, CQRS, lessons learned.
- **Woowahan: "Spring Boot Kotlin Multi Module로 구성해보는 헥사고날 아키텍처"** (`techblog.woowahan.com/12720/`) — Hexagonal architecture with Kotlin + Spring Boot multi-module.
- **Kakao: "이모티콘 서비스는 왜 MSA를 선택했나?"** (`tech.kakao.com/posts/457`) — MSA decision-making and Spring Cloud Gateway selection.
- **Inflearn: "Spring Cloud로 개발하는 마이크로서비스 애플리케이션(MSA)"** by Dowon Lee — The definitive Korean-language Spring Cloud course.
- **Coupang Engineering: "How Coupang built a microservice architecture"** — Custom MSA framework at scale, valuable for understanding when Spring Cloud isn't enough.

### GitHub repositories (by use case)

| Use Case | Repository | Notes |
|---|---|---|
| **Kotlin + Spring Cloud (best)** | `iokats/kotlin-microservices-spring-cloud` | Eureka, Gateway, OpenFeign, Stream, Kafka, Resilience4j—all in Kotlin |
| **Kotlin + Cloud Native Java** | `ddubson/cloud-native-kotlin` | Full Spring Cloud stack ported to Kotlin |
| **Kotlin + Stream + Kafka** | `rogervinas/spring-cloud-stream-kafka-step-by-step` | Step-by-step Kotlin tutorial with DLQ, Avro, Schema Registry |
| **Book companion (Vitale)** | `ThomasVitale/cloud-native-spring-in-action` | Polar Bookshop, Spring Boot 3.x branch |
| **Book companion (Larsson)** | `PacktPublishing/Microservices-with-Spring-Boot-and-Spring-Cloud-Third-Edition` | Most comprehensive, updated to 3.2/Java 21 |
| **K8s deployment** | `piomin/sample-spring-microservices-kubernetes` | Spring Cloud Kubernetes, multi-namespace, Skaffold |
| **Gateway reference** | `ThomasVitale/spring-cloud-gateway-resilience-security-observability` | Gateway + Resilience4j + OAuth2 + Grafana stack |
| **PetClinic on K8s** | `spring-petclinic/spring-petclinic-cloud` | Classic app on Kubernetes with Helm |
| **Contract testing** | `spring-cloud-samples/spring-cloud-contract-samples` | Official comprehensive samples |
| **All patterns (multi-branch)** | `piomin/sample-spring-microservices-new` | Nearly every Spring Cloud pattern across branches |

### Official documentation bookmarks

- Spring Cloud home: `spring.io/projects/spring-cloud/`
- Gateway: `spring.io/projects/spring-cloud-gateway/`
- Config: `docs.spring.io/spring-cloud-config/reference/`
- OpenFeign: `docs.spring.io/spring-cloud-openfeign/reference/`
- Stream: `spring.io/projects/spring-cloud-stream/`
- Kubernetes: `spring.io/projects/spring-cloud-kubernetes/`
- Circuit Breaker: `spring.io/projects/spring-cloud-circuitbreaker/`
- Micrometer Tracing: `docs.micrometer.io/tracing/reference/`
- Spring Boot Tracing: `docs.spring.io/spring-boot/reference/actuator/tracing.html`

---

## Conclusion: the learning philosophy behind this plan

Three design principles drive this curriculum. First, **internals before abstractions**: every phase begins by building the pattern manually (a naive service registry, a hand-rolled circuit breaker, a raw Kafka consumer) before introducing the Spring Cloud solution. This creates durable understanding rather than framework dependency. Second, **standalone before Kubernetes-native**: running Eureka, Config Server, and Bus independently reveals what problems they solve, making the Phase 6 migration to Spring Cloud Kubernetes a conscious architectural decision rather than cargo-cult infrastructure. Third, **your production stack throughout**: Kafka is the message broker from Phase 1 (Bus) through Phase 4 (Stream), Redis powers rate limiting from Phase 2, and Aurora MySQL/PostgreSQL backs every persistent service.

The total estimated timeline is **26 weeks for Phases 0-7** (about 6 months at a sustainable pace), with an optional 4-week capstone. The Korean tech ecosystem—particularly Toss's Gateway architecture, KakaoPay's Stream adoption, and Woowahan's MSA journey—provides production validation that these patterns work at scale in organizations with similar stacks. The **2024.0 (Moorgate)** release train with Spring Boot 3.4 is the recommended starting point; upgrade to **2025.0 (Northfields)** with Spring Boot 3.5 once the ecosystem stabilizes, and evaluate **2025.1 (Oakwood)** with Spring Boot 4.0 and Spring Framework 7 as a forward-looking target for late 2026.