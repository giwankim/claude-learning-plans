---
title: "Mastering Spring Boot Actuator & Micrometer"
category: "Observability"
description: "16-week curriculum covering Actuator internals, Micrometer metrics, and production observability patterns for Kotlin Spring Boot on AWS EKS"
---

# Mastering Spring Boot Actuator & Micrometer: A 16-Week Curriculum

**This curriculum takes a mid-level backend engineer from understanding Actuator and Micrometer internals to designing production-grade observability systems on AWS EKS.** It follows an internals → advanced usage → production patterns arc, with Kotlin-specific guidance woven throughout. Each phase ends with a milestone project that builds toward a complete, observable microservice deployed on Kubernetes. The tech stack assumed throughout is Kotlin, Spring Boot 3.x (3.2–3.4), Gradle Kotlin DSL, Aurora MySQL/PostgreSQL, Redis (Lettuce), Kafka, Hibernate 6.x, and HikariCP.

---

## Phase 1: Actuator internals and endpoint architecture (weeks 1–3)

### Week 1 — Auto-configuration machinery

Spring Boot Actuator's power comes from dozens of `@AutoConfiguration` classes registered via `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`. The critical chain works like this: **`EndpointAutoConfiguration`** sets up core infrastructure, **`WebEndpointAutoConfiguration`** creates the `WebEndpointDiscoverer` that scans the `ApplicationContext` for `@Endpoint` beans, and **`WebMvcEndpointManagementContextConfiguration`** creates the `WebMvcEndpointHandlerMapping` that maps discovered endpoints to HTTP routes.

Each auto-configuration class uses conditional annotations to gate bean creation. The most important is **`@ConditionalOnAvailableEndpoint`**, which checks both enablement (`management.endpoint.<id>.enabled`) AND exposure (`management.endpoints.web.exposure.include/exclude`). This replaced the older `@ConditionalOnEnabledEndpoint` in Boot 3.4+. Other key conditionals include `@ConditionalOnEnabledHealthIndicator("name")` for individual health indicators and standard Spring Boot conditionals (`@ConditionalOnClass`, `@ConditionalOnBean`, `@ConditionalOnMissingBean`).

**Two-step registration model**: An endpoint must be both *enabled* and *exposed* to be accessible. By default in Spring Boot 3.x, only `/health` is exposed over HTTP — a breaking change from Boot 2.x. JMX exposes all endpoints by default. The `exclude` property always takes precedence over `include`.

Study objectives for this week:
- Read the source code of `EndpointAutoConfiguration`, `WebEndpointAutoConfiguration`, and `WebMvcEndpointHandlerMapping` in the Spring Boot GitHub repository
- Trace how `EndpointDiscoverer` scans for `@Endpoint`, `@WebEndpoint`, and `@JmxEndpoint` beans
- Understand the `EndpointLinksResolver` that powers the HAL-style discovery page at `/actuator`
- Learn endpoint caching: read operations without parameters are automatically cached, configurable via `management.endpoint.<id>.cache.time-to-live`

### Week 2 — Endpoint annotations and the health system

The endpoint architecture centers on three operation annotations: **`@ReadOperation`** (maps to HTTP GET, returns 200 or 404), **`@WriteOperation`** (maps to HTTP POST, returns 200 or 204), and **`@DeleteOperation`** (maps to HTTP DELETE). Parameters annotated with `@Selector` become path variables; all others resolve from query params (GET) or request body (POST).

The health indicator system builds on the `HealthContributor` marker interface, which has two implementations: `HealthIndicator` (leaf indicators) and `CompositeHealthContributor` (groups). The `AbstractHealthIndicator` base class provides a template method `doHealthCheck(Health.Builder)` with built-in exception handling. `Health` objects are immutable, built via `Health.up().withDetail("key","value").build()`, and carry one of four statuses: **UP**, **DOWN**, **OUT_OF_SERVICE**, or **UNKNOWN**.

**Health groups** are a powerful production feature configured via properties:

```yaml
management:
  endpoint:
    health:
      group:
        liveness:
          include: livenessState
        readiness:
          include: readinessState, db, redis
        custom:
          include: externalService, paymentGateway
          show-details: always
```

Groups are accessible at `/actuator/health/{groupName}` and are essential for Kubernetes probe mapping.

**Info contributors** follow a similar pattern. The `InfoContributor` interface has a single `contribute(Info.Builder)` method. Built-in contributors include `BuildInfoContributor` (reads `META-INF/build-info.properties`), `GitInfoContributor` (reads `git.properties`), and several disabled-by-default contributors for Java runtime, OS, and process information. Enable them via `management.info.<id>.enabled=true`.

### Week 3 — Security, exposure strategies, and custom endpoints

**Security is the most critical production concern.** If Spring Security is on the classpath with no custom `SecurityFilterChain`, all endpoints except `/health` are secured automatically. With a custom filter chain, Spring Boot backs off entirely. The recommended pattern in Kotlin:

```kotlin
@Bean
fun actuatorSecurity(http: HttpSecurity): SecurityFilterChain =
    http.securityMatcher(EndpointRequest.toAnyEndpoint())
        .authorizeHttpRequests { auth ->
            auth.requestMatchers(EndpointRequest.to("health", "info")).permitAll()
                .anyRequest().hasRole("ADMIN")
        }
        .build()
```

For defense in depth, run Actuator on a separate management port with `management.server.port=8081` and bind to localhost with `management.server.address=127.0.0.1`. Sensitive data in `/env` and `/configprops` is fully sanitized by default since Spring Boot 3.x.

**Access control** (Spring Boot 3.4+) introduces `management.endpoint.<id>.access` with values `none`, `read-only`, or `unrestricted`, providing finer control than the enable/expose model alone.

### Milestone project 1: Custom Actuator endpoint

Build a Kotlin Spring Boot application with:
- A custom `@Endpoint(id = "deployments")` that tracks deployment metadata with `@ReadOperation` (list deployments), `@WriteOperation` (register a deployment), and `@DeleteOperation` (remove old entries)
- A custom `HealthIndicator` that checks connectivity to Aurora PostgreSQL and Redis, plus a custom `CompositeHealthContributor` grouping them
- Health groups configured for Kubernetes (`liveness` and `readiness`)
- A custom `InfoContributor` that reads build and Git info
- Spring Security configured to expose only health and info publicly, with all other endpoints requiring authentication
- Full test coverage using `@SpringBootTest` and `WebTestClient`

```kotlin
// build.gradle.kts
plugins {
    kotlin("jvm") version "2.1.0"
    kotlin("plugin.spring") version "2.1.0"
    id("org.springframework.boot") version "3.4.0"
    id("io.spring.dependency-management") version "1.1.7"
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-security")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```

---

## Phase 2: Micrometer internals and the dimensional metrics model (weeks 4–6)

### Week 4 — MeterRegistry architecture and meter types

Micrometer uses a **dimensional metrics model** where meters are identified by name + tags (key-value pairs) rather than flat hierarchical names. Every meter has a `Meter.Id` composed of name, `List<Tag>`, type, optional base unit, and optional description. Two meters with the same name but different tags are distinct; same name + same tags = idempotent registration.

The **`MeterRegistry`** class hierarchy is central. `MeterRegistry` itself is abstract, storing meters in a `ConcurrentHashMap`. Key implementations include:

- **`SimpleMeterRegistry`** — In-memory, no export. Used for testing.
- **`CompositeMeterRegistry`** — Delegates to multiple child registries. Spring Boot auto-creates this as the primary `MeterRegistry` bean. Before any child is added, all meters are NOOPs.
- **`PrometheusMeterRegistry`** — Prometheus-specific. Uses the new Prometheus Java Client 1.x since Micrometer 1.13+.
- **`StepMeterRegistry`** (abstract) — Base for push-based registries (Datadog, InfluxDB) that publish on a fixed interval.

**Auto-configuration flow**: Boot detects `micrometer-registry-{backend}` JARs → creates backend-specific registries → creates `CompositeMeterRegistry` → applies `MeterRegistryCustomizer` beans → applies `MeterFilter` beans.

Master all **seven meter types**:

| Type | Purpose | When to use |
|------|---------|-------------|
| **Counter** | Monotonically increasing count | Request counts, error totals, events processed |
| **Gauge** | Instantaneous value (up or down) | Queue size, cache size, active connections |
| **Timer** | Short-duration latency + count | Request duration, method execution time |
| **DistributionSummary** | Non-time distributions | Response sizes, payload lengths, batch sizes |
| **LongTaskTimer** | Currently active long-running tasks | Batch jobs, background processes (reports *during* execution) |
| **FunctionCounter** | Wraps external monotonic function | Cache eviction counts from third-party libraries |
| **FunctionTimer** | Wraps external count+time function | Third-party timer objects |
| **TimeGauge** | Gauge for time values with unit conversion | Automatically converts to registry's base time unit |

**Critical gotcha**: `Gauge` and `FunctionCounter`/`FunctionTimer` hold `WeakReference` to the observed object. If the object is garbage collected, the meter reports NaN. Always maintain a strong reference.

### Week 5 — MeterFilter, naming conventions, and the Clock

**`MeterFilter`** is the primary mechanism for controlling metric registration and configuration. Filters serve three functions: deny/accept (control whether meters register), transform (modify meter IDs), and configure (set distribution statistics). Filters apply in registration order, and all filters must be registered **before** any meters — Micrometer 1.12+ logs a warning otherwise.

Key filter patterns in Kotlin:

```kotlin
@Configuration(proxyBeanMethods = false)
class MetricsFilterConfig {

    // Common tags for all metrics
    @Bean
    fun commonTags(
        @Value("\${spring.application.name}") appName: String
    ): MeterRegistryCustomizer<MeterRegistry> = MeterRegistryCustomizer { registry ->
        registry.config().commonTags("application", appName, "region", "ap-northeast-2")
    }

    // Cardinality guard
    @Bean
    fun cardinalityLimit(): MeterFilter =
        MeterFilter.maximumAllowableTags("http.server.requests", "uri", 100, MeterFilter.deny())

    // Strip query parameters from URI tags
    @Bean
    @Order(-10)
    fun stripQueryParams(): MeterFilter =
        MeterFilter.replaceTagValues("uri") { it.substringBefore('?') }

    // Histogram configuration for HTTP metrics
    @Bean
    fun httpHistogramConfig(): MeterFilter = object : MeterFilter {
        override fun configure(id: Meter.Id, config: DistributionStatisticConfig): DistributionStatisticConfig =
            if (id.name.startsWith("http")) {
                DistributionStatisticConfig.builder()
                    .percentilesHistogram(true)
                    .serviceLevelObjectives(
                        Duration.ofMillis(100).toNanos().toDouble(),
                        Duration.ofMillis(500).toNanos().toDouble(),
                        Duration.ofSeconds(1).toNanos().toDouble()
                    )
                    .minimumExpectedValue(Duration.ofMillis(1).toNanos().toDouble())
                    .maximumExpectedValue(Duration.ofSeconds(30).toNanos().toDouble())
                    .build()
                    .merge(config)
            } else config
    }
}
```

**Naming conventions** translate automatically per backend. Micrometer uses lowercase dot notation (`http.server.requests`) internally. The `NamingConvention` interface converts this to each backend's format: Prometheus uses snake_case with unit suffixes (`http_server_requests_seconds_total`), Datadog uses dot notation, Atlas uses tags natively. Always use dot notation in code and let the convention handle translation.

The **`Clock`** interface provides `wallTime()` (epoch millis) and `monotonicTime()` (monotonic nanos). Each registry takes a `Clock` in its constructor. `MockClock` is available for deterministic testing. Each registry also defines `getBaseTimeUnit()` — Prometheus uses seconds, which means Timer values stored in nanoseconds internally are automatically converted to seconds on export.

### Week 6 — Observation API and built-in binders

The **Observation API** (Micrometer 1.10+) is Spring Boot 3.x's unified instrumentation model: **instrument once, get metrics AND traces simultaneously**. Key components:

- **`ObservationRegistry`** — Central registry holding handlers, predicates, conventions, and filters. Auto-configured by Spring Boot.
- **`Observation`** — Core abstraction with lifecycle: `start()` → `observe(Runnable/Callable)` → `stop()`. Supports `lowCardinalityKeyValue` (safe for metrics tags) and `highCardinalityKeyValue` (traces only).
- **`ObservationHandler<T>`** — Reacts to lifecycle events (onStart, onStop, onError, onScopeOpened). `DefaultMeterObservationHandler` creates Timer + Counter metrics. `DefaultTracingObservationHandler` creates spans.
- **`ObservationConvention`** — Separates naming/tagging from lifecycle. Custom convention > global convention > default convention.
- **`@Observed`** annotation — Applied to methods/classes. Requires an `ObservedAspect` bean.

**Convention precedence**: Custom convention passed to `Observation.createNotStarted()` takes highest priority, then global conventions registered on `ObservationRegistry`, then the default convention.

Spring Boot auto-instruments HTTP server/client requests, `@Scheduled` methods, JMS, RestTemplate, RestClient, and WebClient through the Observation API. The `ServerHttpObservationFilter` handles MVC; `WebHttpHandlerBuilder` handles WebFlux.

**Built-in meter binders** auto-register when their target libraries are on the classpath:

- **JVM**: `JvmMemoryMetrics`, `JvmGcMetrics`, `JvmThreadMetrics`, `ClassLoaderMetrics`, `JvmHeapPressureMetrics` — all under `jvm.*`
- **System**: `ProcessorMetrics` (`system.cpu.*`, `process.cpu.*`), `UptimeMetrics`, `FileDescriptorMetrics`
- **HikariCP**: Auto-configured via `HikariDataSourceMetricsAutoConfiguration`. Metrics: `hikaricp.connections.active`, `.idle`, `.pending`, `.total`, `.timeout`, `.creation`, `.usage`, `.acquire`
- **Hibernate**: Requires `hibernate.generate_statistics=true`. Metrics: `hibernate.sessions.*`, `hibernate.entities.*`, `hibernate.query.*`, `hibernate.cache.*`
- **Kafka**: `MicrometerConsumerListener` and `MicrometerProducerListener` → `kafka.consumer.*`, `kafka.producer.*`
- **Lettuce/Redis**: `MicrometerCommandLatencyRecorder` → `lettuce.command.*`
- **Tomcat**: `TomcatMetrics` → `tomcat.sessions.*`, `tomcat.threads.*`
- **HTTP**: `http.server.requests` and `http.client.requests` (Timer) with tags for method, uri, status, outcome

### Milestone project 2: Instrumented service with custom metrics

Build a Kotlin order-processing service with:
- Aurora PostgreSQL (HikariCP + Hibernate 6.x), Redis cache (Lettuce), Kafka consumer/producer
- Verify all auto-configured binders produce metrics: JVM, HikariCP, Hibernate, Kafka, Lettuce, Tomcat
- Create custom business metrics: `orders.placed` (Counter), `orders.amount` (DistributionSummary), `orders.processing.duration` (Timer), `orders.queue.size` (Gauge), `orders.batch.duration` (LongTaskTimer)
- Implement `MeterFilter` beans for common tags, cardinality limiting, and URI normalization
- Use the Observation API for at least one business operation with both low and high cardinality key-values
- Configure `@Observed` with a custom `ObservationConvention`
- Write unit tests using `SimpleMeterRegistry` to verify all custom metrics

---

## Phase 3: Custom metrics, histograms, and SLO-based alerting (weeks 7–9)

### Week 7 — @Timed, @Counted, and programmatic patterns in Kotlin

**`@Timed` and `@Counted` annotations** use `TimedAspect` and `CountedAspect` under the hood. In Spring Boot 3.2+, auto-configuration requires `management.observations.annotations.enabled=true` (defaults to false due to startup performance impact). Without this, you must manually declare the aspect beans.

**Kotlin-specific gotcha**: The `kotlin-spring` compiler plugin (wrapping `all-open`) automatically opens classes annotated with `@Component`, `@Service`, `@Repository`, `@Configuration`, etc. However, **`@Timed` is NOT in this list**. For `@Timed` to work, the annotated method must be on a Spring-managed bean whose class is already opened. If you need `@Timed` on classes without Spring stereotypes, add to `build.gradle.kts`:

```kotlin
allOpen {
    annotation("io.micrometer.core.annotation.Timed")
}
```

**Critical: `@Timed` does NOT work correctly with Kotlin `suspend` functions.** Spring AOP's `TimedAspect` measures only until the first suspension point because the proxy sees a `COROUTINE_SUSPENDED` return marker and ends timing. A service layer taking 960ms may be measured as 11ms. The solution is manual timing:

```kotlin
// Coroutine-safe timer extension
suspend fun <T> Timer.recordSuspend(block: suspend () -> T): T {
    val sample = Timer.start()
    return try {
        block()
    } finally {
        sample.stop(this)
    }
}

// Usage
@Service
class OrderService(private val registry: MeterRegistry) {
    private val processTimer = Timer.builder("orders.processing.duration")
        .description("Order processing time")
        .publishPercentileHistogram()
        .register(registry)

    suspend fun processOrder(request: OrderRequest): Order =
        processTimer.recordSuspend {
            // Full suspend chain properly timed
            val validated = validate(request)
            val saved = repository.save(validated)
            notificationService.send(saved)
            saved
        }
}
```

Other Kotlin gotchas with AOP:
- Self-invocation bypasses the proxy — calling a `@Timed` method from within the same class skips timing
- `private` and `final` methods cannot be proxied
- Data class methods cannot be proxied
- Companion object methods cannot be proxied

### Week 8 — Histogram configuration and distribution statistics

Three histogram options have distinct behaviors and trade-offs:

**`publishPercentiles(0.5, 0.95, 0.99)`** computes percentiles client-side. Creates Prometheus Summary type. **Non-aggregable** across dimensions or instances. Use only when the backend lacks `histogram_quantile`.

**`publishPercentileHistogram()`** ships predetermined buckets (up to 276, bounded by min/max expected values). The backend computes percentiles via `histogram_quantile()`. **Aggregable** across instances. Preferred for Prometheus deployments.

**`serviceLevelObjectives(Duration.ofMillis(100), Duration.ofMillis(500), Duration.ofSeconds(1))`** publishes a cumulative histogram with only the SLO-defined buckets. Use when you need to know what fraction of requests meet specific latency thresholds.

**Breaking change in Micrometer 1.13+**: With the new Prometheus Java Client 1.x, you cannot combine `publishPercentiles` with `publishPercentileHistogram` or `serviceLevelObjectives` under the same metric name — the histogram is preferred and client-side percentiles are dropped.

Spring Boot property-based configuration:

```yaml
management:
  metrics:
    distribution:
      percentiles-histogram:
        http.server.requests: true
        http.client.requests: true
      slo:
        http.server.requests: 100ms,250ms,500ms,1s,5s
      minimum-expected-value:
        http.server.requests: 1ms
      maximum-expected-value:
        http.server.requests: 30s
```

**When NOT to use percentile histograms**: If you have a low-traffic service (fewer than ~100 requests per scrape interval), histogram buckets may produce noisy percentile calculations. In this case, client-side percentiles via `publishPercentiles` can be more accurate for single-instance metrics — just know they cannot be aggregated across pods.

### Week 9 — SLOs, error budgets, and burn-rate alerts

**SLI** (Service Level Indicator) is the metric measuring service performance — typically the ratio of successful requests to total requests, or the ratio of requests under a latency threshold. **SLO** (Service Level Objective) is the target reliability level expressed as a percentage over a time window (e.g., 99.9% availability over 30 days). **SLA** (Service Level Agreement) is the contractual obligation with consequences for breach. **Error budget** is the allowed unreliability: for a 99.9% SLO, the error budget is **0.1% = ~43.2 minutes of downtime per month**.

The **Google SRE golden signals** map directly to Spring Boot metrics:

| Signal | Spring Boot Metric | PromQL |
|--------|-------------------|--------|
| Latency | `http_server_requests_seconds` | `histogram_quantile(0.99, rate(http_server_requests_seconds_bucket[5m]))` |
| Traffic | `http_server_requests_seconds_count` | `sum(rate(http_server_requests_seconds_count[5m]))` |
| Errors | Status-filtered request count | `sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))` |
| Saturation | JVM + Tomcat metrics | `jvm_memory_used_bytes{area="heap"} / jvm_memory_max_bytes{area="heap"}` |

**Multi-window, multi-burn-rate alerts** (from Google SRE Workbook Chapter 5) are the gold standard for SLO alerting. Burn rate measures how fast you consume error budget relative to steady state. The alert structure uses a long window to detect the trend and a short window to confirm the issue is current:

| Severity | Long Window | Short Window | Burn Rate | Budget Consumed |
|----------|------------|--------------|-----------|-----------------|
| Critical (page) | 1h | 5m | 14.4 | 2% |
| Critical (page) | 6h | 30m | 6 | 5% |
| Warning (ticket) | 1d | 2h | 3 | 10% |
| Warning (ticket) | 3d | 6h | 1 | 10% |

Prometheus alerting rule example:

```yaml
groups:
  - name: slo_alerts
    rules:
      - alert: SLOHighBurnRate
        expr: |
          (
            slo:http_requests:burn_rate_1h{service="order-service"} > 14.4
            and
            slo:http_requests:burn_rate_5m{service="order-service"} > 14.4
          )
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "2% of error budget consumed in 1 hour"
```

**When NOT to use burn-rate alerts**: For services with very low traffic (fewer than ~1000 requests per hour), burn-rate calculations become statistically unreliable. Use simple threshold alerts instead. For extremely high-SLO services (99.99%+), the error budget is so small that burn-rate math may produce noisy alerts — consider increasing the `for` duration.

### Milestone project 3: SLO dashboard and alerting

Build on the order-processing service:
- Configure histogram buckets and SLO boundaries for all HTTP endpoints
- Write Prometheus recording rules for availability and latency SLIs
- Implement multi-window, multi-burn-rate alerting rules
- Create a Grafana dashboard with golden signals panels, error budget remaining gauge, and burn-rate visualization
- Calculate and display error budget consumption over a 30-day rolling window
- Write PromQL queries for p50/p95/p99 latency, error ratio, and throughput

---

## Phase 4: Monitoring backend integration (weeks 10–12)

### Week 10 — Prometheus deep integration

The `PrometheusMeterRegistry` is auto-configured when `micrometer-registry-prometheus` is on the classpath. Since Micrometer 1.13+, this uses the new Prometheus Java Client 1.x by default. For the legacy client, use `micrometer-registry-prometheus-simpleclient` instead.

Gradle Kotlin DSL setup:

```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("io.micrometer:micrometer-registry-prometheus")
    // For tracing exemplars:
    implementation("io.micrometer:micrometer-tracing-bridge-otel")
    implementation("io.opentelemetry:opentelemetry-exporter-otlp")
}
```

**Exemplars** attach trace IDs to metric data points, enabling the powerful drill-down from a metric spike to the exact traces causing it. Requires requesting OpenMetrics format: `Accept: application/openmetrics-text; version=1.0.0`. Spring Boot auto-configures `SpanContext` integration when both Micrometer Tracing and the Prometheus registry are present.

**Scrape vs push**: The pull model (Prometheus scrapes `/actuator/prometheus`) is simpler and gives Prometheus control over rate. The push model (OTLP export to Grafana Mimir, Thanos, or a remote-write endpoint) is better for serverless, ephemeral environments, or when pods are not network-reachable from Prometheus.

### Week 11 — Grafana dashboards and Datadog

**Grafana community dashboards** provide immediate value. The most useful dashboard IDs:

- **4701** — JVM (Micrometer): The most popular; covers memory, CPU, threads, GC, HTTP metrics, Tomcat
- **12464** — Spring Boot Statistics: Request counts, durations, status codes
- **20668** — JVM & DB Metrics: Includes HikariCP connection pool
- **22108** — JVM SpringBoot3 (Prometheus Operator): Specifically for Spring Boot 3

All require the `application` common tag. Dashboard design best practices: use RED metrics (Rate, Errors, Duration) as top-level panels, include JVM heap and GC pause times, add business metrics, use template variables for filtering by application/instance/environment, and **alert on p99 latency, never averages** — averages hide outliers.

**Datadog integration** offers two paths. The direct API approach uses `micrometer-registry-datadog` with an API key. The DogStatsD approach uses `micrometer-registry-statsd` with `flavor: datadog`, pushing metrics over UDP to a local Datadog Agent — preferred in containerized environments because it's more resilient and doesn't require direct internet access from the application.

Datadog's **Unified Service Tags** best practice requires `env`, `service`, and `version` tags on all telemetry. The Datadog Java Agent handles APM tracing via bytecode instrumentation with zero code changes for Spring MVC, JDBC, HTTP clients, Kafka, and more.

### Week 12 — OpenTelemetry and OTLP

Three integration paths exist:

**Path 1: OpenTelemetry Java Agent** — Zero code change, attach via `-javaagent`. Auto-instruments everything. Heaviest touch on the runtime.

**Path 2: Spring Boot OTel Starter** — For Spring Boot 4.x, use `spring-boot-starter-opentelemetry`. For Spring Boot 3.x, use the Micrometer bridges:

```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("io.micrometer:micrometer-tracing-bridge-otel")
    implementation("io.opentelemetry:opentelemetry-exporter-otlp")
    implementation("io.micrometer:micrometer-registry-otlp")
}
```

```yaml
management:
  otlp:
    metrics:
      export:
        url: http://otel-collector:4318/v1/metrics
        step: 30s
        resource-attributes:
          service.name: ${spring.application.name}
    tracing:
      endpoint: http://otel-collector:4318/v1/traces
  tracing:
    sampling:
      probability: 1.0  # 100% for dev; lower for production
```

**Path 3: Micrometer Observation API** — Spring's recommended approach. Instrument once with `Observation.createNotStarted()`, get both metrics and traces. The key insight from the Spring team: "It's the protocol (OTLP) that matters, not the library."

**OTLP metrics configuration details**: Default URL is `localhost:4318/v1/metrics`. Supports `cumulative` (default) or `delta` aggregation temporality. Default export interval is 1 minute. Supports Exponential Histograms when `publishPercentileHistogram` is configured, except when `serviceLevelObjectives` are set (requires explicit bucket boundaries).

**Log correlation** comes free: Spring Boot 3.x automatically includes `traceId` and `spanId` in MDC when Micrometer Tracing is on the classpath.

### Milestone project 4: Multi-backend observability stack

Deploy a complete observability stack using Docker Compose:
- Configure Prometheus scraping the Spring Boot `/actuator/prometheus` endpoint
- Set up Grafana with imported community dashboard (4701) plus a custom business metrics dashboard
- Configure OTLP export to an OpenTelemetry Collector
- Route traces from OTel Collector to Grafana Tempo
- Route logs to Grafana Loki
- Demonstrate log-metric-trace correlation: click from a Grafana metric panel spike → filtered traces → correlated logs
- Configure Prometheus alerting rules and Grafana alert notifications
- (Optional) Set up Datadog Agent with DogStatsD for comparison

---

## Phase 5: Production patterns on AWS EKS (weeks 13–15)

### Week 13 — Kubernetes health probes and ServiceMonitor

**Health probe mapping** is one of Actuator's most important production features. Spring Boot auto-configures probe endpoints when running in Kubernetes:

- **Liveness** (`/actuator/health/liveness`) — Must NOT depend on external systems. Only checks if the application itself is in a valid state. Failure triggers container restart. **Never include database or Redis checks here** — if Aurora is down, restarting your pod won't fix it, and you'll trigger restart cascades.
- **Readiness** (`/actuator/health/readiness`) — Can check external dependencies (carefully). Failure removes the pod from Service endpoints. Be cautious with shared dependencies: if Aurora goes down and readiness includes a DB check, ALL pods go unready simultaneously, causing a total outage.
- **Startup** — Use the liveness path with generous thresholds (`failureThreshold: 30`, `periodSeconds: 5` = 150s max startup) to handle JVM warmup without premature liveness failures.

```yaml
management:
  endpoint:
    health:
      probes:
        enabled: true
  health:
    livenessstate:
      enabled: true
    readinessstate:
      enabled: true
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

**ServiceMonitor CRDs** (from prometheus-operator) are the recommended way to configure Prometheus scraping on EKS. They declaratively specify scrape targets without modifying Prometheus configuration:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: order-service
  labels:
    release: kube-prometheus-stack  # Must match Prometheus serviceMonitorSelector
spec:
  namespaceSelector:
    matchNames: [production]
  selector:
    matchLabels:
      app: order-service
  endpoints:
    - port: http  # References Service port NAME, not number
      path: /actuator/prometheus
      interval: 30s
```

**Common debugging steps** when targets don't appear in Prometheus: verify ServiceMonitor labels match Prometheus's `serviceMonitorSelector`, verify Service labels match ServiceMonitor's `selector`, verify port names match (ServiceMonitor references by name), check endpoints exist with `kubectl get endpoints`.

Install kube-prometheus-stack with a critical setting:

```bash
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
```

The `serviceMonitorSelectorNilUsesHelmValues=false` flag is essential — without it, Prometheus only discovers ServiceMonitors with the exact Helm release label.

### Week 14 — Cardinality management and performance

**Cardinality explosions** are the single most common production failure mode with metrics. Each unique combination of metric name + tag values creates a new time series. Common culprits: untemplatized URIs (`/users/123` instead of `/users/{id}`), user IDs or session IDs as tags, query parameters leaking into URI tags, HTTP client `uri` tags with dynamic paths, and host/port tags in dynamic environments.

Defense-in-depth strategy:

```kotlin
@Configuration
class CardinalityDefense {

    @Bean
    @Order(Ordered.HIGHEST_PRECEDENCE)
    fun uriNormalization(): MeterFilter =
        MeterFilter.replaceTagValues("uri") { it.substringBefore('?') }

    @Bean
    fun uriCardinalityLimit(): MeterFilter =
        MeterFilter.maximumAllowableTags("http.server.requests", "uri", 100, MeterFilter.deny())

    @Bean
    fun globalMetricLimit(): MeterFilter =
        MeterFilter.maximumAllowableMetrics(10_000)

    @Bean
    fun denyHighCardinalityTags(): MeterFilter =
        MeterFilter.ignoreTags("userId", "sessionId", "requestId")

    // Allowlist pattern for cost-sensitive environments
    @Bean
    fun allowlistFilter(): MeterFilter = MeterFilter.denyUnless { id ->
        allowedPrefixes.any { id.name.startsWith(it) }
    }

    companion object {
        private val allowedPrefixes = listOf(
            "http.", "jvm.memory.", "jvm.gc.", "hikaricp.", "kafka.", "orders."
        )
    }
}
```

**Performance overhead**: Timer with no histogram costs a few hundred bytes. With percentile histogram, default 73 buckets per dimension at ~8 bytes each. Prometheus scrape serializes all meters to text — CPU-intensive with many metrics. Benchmarks from the Vert.x project showed metrics collection can reduce throughput by **~4-8%** in realistic workloads after Micrometer 1.12+ optimizations (the `MeterProvider` API introduced per-thread meter caches to reduce `ConcurrentHashMap` contention).

**When NOT to instrument**: Don't add `@Timed` to every method — only meaningful boundaries (controllers, service facades, external calls). Don't create metrics in hot paths; pre-register at startup. Don't add percentile histograms to every timer without bounding `minimumExpectedValue`/`maximumExpectedValue` (default 276 buckets creates massive cardinality). Don't register the same metric name with different tag key sets — Prometheus rejects inconsistent label sets.

### Week 15 — Kotlin-specific production patterns

**Coroutine context propagation** is an actively evolving area. Spring Framework 6.2+ provides `PropagationContextElement`, a `ThreadContextElement` that bridges Micrometer context-propagation with Kotlin coroutine context:

```kotlin
dependencies {
    implementation("io.micrometer:context-propagation")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-reactor")
}
```

```yaml
spring:
  reactor:
    context-propagation: auto  # Automatic context propagation
```

With `Hooks.enableAutomaticContextPropagation()`, Spring's `CoroutinesUtils#invokeSuspendingFunction` automatically adds `PropagationContextElement` to the coroutine context. However, known issues remain: context propagation works for `suspend` controller methods but may not work for `Flow` return types (Spring Framework issue #36427), and propagation can break when dispatchers change threads.

**Kotlin extension function patterns** for idiomatic metrics:

```kotlin
// DSL for meter creation
inline fun MeterRegistry.buildTimer(
    name: String,
    crossinline configure: Timer.Builder.() -> Unit = {}
): Timer = Timer.builder(name).apply(configure).register(this)

// Coroutine-safe observation
suspend fun <T> ObservationRegistry.observeSuspend(
    name: String,
    vararg lowCardinalityTags: Pair<String, String>,
    block: suspend () -> T
): T {
    val observation = Observation.createNotStarted(name, this).apply {
        lowCardinalityTags.forEach { (k, v) -> lowCardinalityKeyValue(k, v) }
    }
    observation.start()
    return try {
        block().also { observation.stop() }
    } catch (e: Exception) {
        observation.error(e)
        observation.stop()
        throw e
    }
}
```

**Testing metrics in Kotlin**:

```kotlin
class OrderMetricsTest {
    private val registry = SimpleMeterRegistry()
    private val service = OrderService(registry)

    @Test
    fun `should record order processing duration across suspension points`() = runBlocking {
        service.processOrder(testOrder)

        val timer = registry.get("orders.processing.duration").timer()
        assertThat(timer.count()).isEqualTo(1)
        assertThat(timer.totalTime(TimeUnit.MILLISECONDS)).isGreaterThan(0.0)
    }

    @Test
    fun `cardinality filter blocks excess tag values`() {
        registry.config().meterFilter(
            MeterFilter.maximumAllowableTags("http.requests", "uri", 3, MeterFilter.deny())
        )
        repeat(3) { i -> registry.counter("http.requests", "uri", "/api/v$i").increment() }

        // 4th URI gets denied
        val denied = registry.counter("http.requests", "uri", "/api/v99")
        assertThat(denied).isInstanceOf(NoopCounter::class.java)
    }
}
```

**Kotlin gotchas summary table**:

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| `@Timed` + `suspend` | AOP proxy sees COROUTINE_SUSPENDED marker | Use manual `Timer.start()/sample.stop()` |
| Final classes/methods | Kotlin default, Spring AOP needs `open` | `kotlin-spring` plugin or `allOpen` |
| Self-invocation | Internal calls bypass AOP proxy | Extract to separate bean |
| Context loss in coroutines | Thread switch loses ThreadLocal state | `PropagationContextElement` or manual `ContextSnapshotFactory` |
| `@Timed` not auto-configured | Disabled by default since Boot 3.2 | Set `management.observations.annotations.enabled=true` |
| `Flow` + context propagation | Spring issue #36427 | Use `suspend` return types for now |
| Data class methods + AOP | Data classes effectively final | Use regular classes for instrumented code |

### Milestone project 5: Production-ready EKS deployment

Deploy the order-processing service to AWS EKS with:
- Kubernetes Deployment with startup, liveness, and readiness probes mapped to Actuator health groups
- ServiceMonitor CRD for Prometheus scraping
- kube-prometheus-stack Helm chart with custom values
- `MeterFilter` beans implementing cardinality defense (URI normalization, tag limits, global metric cap)
- Grafana dashboards imported and custom business dashboards deployed via ConfigMap
- Prometheus alerting rules for multi-burn-rate SLO alerts
- Coroutine-safe timing using extension functions (no `@Timed` on suspend functions)
- Context propagation for distributed tracing across coroutine boundaries
- Integration tests that verify metric correctness using `SimpleMeterRegistry`
- Load test with k6 to verify metrics accuracy under load and measure performance overhead

---

## Phase 6: Synthesis and capstone (week 16)

### Capstone project: End-to-end observable microservice system

Build a system of 2-3 Kotlin Spring Boot microservices communicating via Kafka and REST, deployed to EKS, with complete observability:

- **All four golden signals** dashboarded in Grafana for each service
- **SLO definitions** with multi-window, multi-burn-rate Prometheus alerting rules
- **Error budget tracking** dashboard showing 30-day rolling budget consumption
- **Distributed tracing** across services via OTLP to Grafana Tempo, with exemplars linking metrics to traces
- **Log correlation** via Loki with traceId/spanId in structured logs
- **Custom business metrics** for order processing pipeline (orders/min, conversion rate, payment latency by provider)
- **Cardinality defense** with MeterFilter allowlisting, URI normalization, and tag limits
- **Kubernetes-native** ServiceMonitors, health probe groups, graceful shutdown
- **Kotlin-idiomatic** coroutine-safe instrumentation, extension function DSL, context propagation
- **Test coverage** for all custom metrics, health indicators, and MeterFilter behavior
- **Documentation** of SLO definitions, alert runbooks, and metric dictionary

---

## Common failure modes reference

| Failure Mode | Symptom | Root Cause | Prevention |
|-------------|---------|-----------|------------|
| OOM from high cardinality | Heap exhaustion, GC thrashing | Unbounded tag values (user IDs, dynamic URIs) | `maximumAllowableTags`, `maximumAllowableMetrics`, URI normalization |
| Prometheus scrape timeout | Targets showing as DOWN in Prometheus UI | Too many metrics, serialization too slow | Reduce cardinality, use allowlist `MeterFilter`, increase scrape timeout |
| Metric name collision | Prometheus rejects scrape with type mismatch | Same metric name registered as different types | Consistent naming, review auto-configured metric names |
| Restart cascades from liveness probes | Pods continuously restarting | Liveness probe includes external dependency checks (DB, Redis) | NEVER include external checks in liveness; use readiness for dependencies |
| All pods unready simultaneously | Complete outage despite pods being healthy | Readiness probe fails on shared dependency (Aurora down) | Use circuit-breaker pattern in readiness checks; consider removing shared deps from readiness |
| Inaccurate suspend function timing | Metrics show ~0ms for operations that take seconds | `@Timed` on Kotlin `suspend` function | Manual `Timer.start()/sample.stop()` wrapper |
| Missing trace context after suspension | Logs lose traceId after `delay()` or dispatcher switch | Thread-local context not propagated to coroutine | `PropagationContextElement`, `context-propagation: auto` |
| Gauges returning NaN | Metrics show NaN in Grafana | Tracked object garbage collected (WeakReference) | Maintain strong reference to gauge-tracked objects |
| Filters registered after meters | Warning logs, filters not applied to existing meters | MeterFilter beans created after metric registration | Ensure filters are declared with `@Order` and loaded early |

---

## Trade-off analysis reference

### Pull (Prometheus scrape) vs Push (OTLP/Datadog)

Pull is simpler, gives the monitoring system control over scrape rate, and works well when Prometheus can reach all pods. Push is better for serverless, ephemeral workloads, environments with strict network policies blocking inbound connections to pods, and multi-cloud scenarios where a centralized collector is preferred. For AWS EKS with kube-prometheus-stack, **pull is the standard choice**.

### Client-side percentiles vs server-side histograms

Client-side percentiles (`publishPercentiles`) are lightweight (one series per percentile) but **non-aggregable** across instances — useless for multi-pod deployments. Server-side histograms (`publishPercentileHistogram`) produce 73+ bucket series but allow `histogram_quantile()` aggregation across pods. **Always prefer histograms for Prometheus in Kubernetes**. Use `minimumExpectedValue` and `maximumExpectedValue` to bound bucket count.

### Observation API vs direct Micrometer

The Observation API is higher-level and produces both metrics and traces. Use it for cross-cutting instrumentation (HTTP, messaging, database calls). Use direct Micrometer (`Counter.builder()`, `Timer.builder()`) for simple business counters and gauges where you don't need tracing. Don't over-engineer: a simple `counter.increment()` doesn't need the Observation API.

---

## Resource library

### Books (recommended reading order)

1. **"Spring in Action" (6th Edition)** — Craig Walls. Spring Boot fundamentals including Actuator basics. Start here. (Beginner)
2. **"Cloud Native Spring in Action"** — Thomas Vitale. Spring Boot on Kubernetes, health probes, observability with Grafana Stack. (Intermediate)
3. **"Learning OpenTelemetry"** — Austin Parker & Ted Young (O'Reilly, 2024). Core OTel concepts, collectors, exporters. Essential for Spring Boot's OTel integration. (Intermediate)
4. **"Observability Engineering"** — Charity Majors, Liz Fong-Jones, George Miranda (O'Reilly, 2022). The definitive book on modern observability philosophy, SLOs, debugging culture. (Intermediate–Advanced)
5. **"Site Reliability Engineering"** — Google (free at sre.google/sre-book). The foundational SRE text covering monitoring, alerting, SLOs, error budgets. (Advanced)
6. **"The Site Reliability Workbook"** — Google (free at sre.google/workbook). Practical companion with hands-on SLO and alerting examples. (Advanced)

### Official documentation

- **Spring Boot Actuator**: docs.spring.io/spring-boot/reference/actuator/index.html
- **Spring Boot Metrics**: docs.spring.io/spring-boot/reference/actuator/metrics.html
- **Spring Boot Observability**: docs.spring.io/spring-boot/reference/actuator/observability.html
- **Micrometer**: micrometer.io/docs
- **Micrometer Observation API**: micrometer.io/docs/observation
- **Micrometer Tracing**: micrometer.io/docs/tracing
- **Prometheus**: prometheus.io/docs/introduction/overview/
- **Grafana**: grafana.com/docs/grafana/latest/
- **OpenTelemetry**: opentelemetry.io/docs/
- **OpenTelemetry Java**: opentelemetry.io/docs/languages/java/
- **Kubernetes Probes**: kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

### Courses and video content

1. **"Mastering Spring Boot Actuator: Advanced In-Depth Insights"** (Udemy) — Deep-dive into endpoints, Prometheus/Grafana integration. (Intermediate–Advanced)
2. **"OpenTelemetry Observability For Java Spring Boot Developers"** (Udemy) — Distributed traces, metrics, logs with OTel. (Advanced)
3. **"Ready for Production with Spring Boot Actuator"** (Udemy) — Focused starter on health endpoints, custom checks, K8s integration. (Beginner)
4. **Pluralsight Lab: "Implement OpenTelemetry for Java Observability"** — Hands-on with two Spring Boot services, Micrometer, Prometheus, Jaeger. (Intermediate)
5. **Baeldung tutorials** (free) — baeldung.com/spring-boot-actuators, baeldung.com/spring-boot-3-observability, baeldung.com/micrometer. (Beginner–Intermediate)

### Conference talks (must-watch)

1. **"Micrometer Mastery: Unleash Advanced Observability in your JVM Apps"** — Jonatan Ivanov (SpringOne 2024, Spring I/O 2024). Deep-dive into Observation API, dimensional metrics, ObservationHandler lifecycle. Slides on SpeakerDeck.
2. **"Observability for Modern Spring Applications"** — Jonatan Ivanov (SpringOne Tour 2023). Three pillars of observability, Micrometer unification, Observation API lifecycle.
3. **"Dive into Observability with Micrometer and Spring Boot 3"** — Jonatan Ivanov & Tommy Ludwig (Spring I/O 2024 Workshop). Hands-on exercises with the Observation API.
4. **"Observability of Your Application"** — Marcin Grzejszczak & Tommy Ludwig (Spring I/O 2023). Foundational talk on instrumentation and backend integration.
5. **A Bootiful Podcast episodes with Jonatan Ivanov and Tommy Ludwig** — Multiple episodes on spring.io/blog covering latest Micrometer features.

### GitHub repositories

- **micrometer-metrics/micrometer** — Core source code. Study meter implementations and registry abstractions.
- **spring-projects/spring-boot** — Actuator source at `spring-boot-project/spring-boot-actuator-autoconfigure/`. Study auto-configuration classes.
- **micrometer-metrics/micrometer-samples-spring-boot** — Official samples with various backends (Prometheus, Datadog, Atlas, etc.).
- **blueswen/spring-boot-observability** — Complete three-pillar observability demo with Tempo, Prometheus, Loki on Grafana. Docker Compose included.
- **prometheus-community/helm-charts** (kube-prometheus-stack) — Production-grade K8s monitoring stack.
- **rbiedrawa/spring-k8s-prometheus** — Spring Boot metrics on Kubernetes with ServiceMonitor and Grafana dashboards.
- **tutorialworks/spring-boot-with-metrics** — Clean, minimal Prometheus + Micrometer example for beginners.

### Blog posts and case studies

**Spring team official posts**:
- "Observability with Spring Boot 3" (spring.io/blog, Oct 2022) — Canonical introduction to Boot 3 observability
- "Let's use OpenTelemetry with Spring" (spring.io/blog, Oct 2024) — Micrometer + OTLP integration paths
- "OpenTelemetry with Spring Boot" (spring.io/blog, Nov 2025) — Latest guide for spring-boot-starter-opentelemetry

**Industry case studies**:
- Netflix Atlas (github.com/Netflix/atlas) — Origin of dimensional metrics concepts that influenced Micrometer's design
- Grafana Labs: "Set up and observe a Spring Boot application with Grafana Cloud, Prometheus, and OpenTelemetry" — Official integration tutorial
- Digma: "Spring Boot 3.3: Top 7 Observability Enhancements" — Detailed analysis of observability improvements per release
- Uptrace: "Monitoring Spring Boot Microservices with Actuator, Micrometer, and OpenTelemetry" — Comprehensive step-by-step guide

**Korean tech company resources**:
- **우아한형제들 (Woowahan/Baemin)**: Shop display system monitoring case study using Micrometer with InfluxDB + Grafana (woowabros.github.io) — covers WebFlux MDC challenges, reactive monitoring at scale
- **Korean Spring Boot monitoring guides**: jongmin92.github.io (building Micrometer + Prometheus + Grafana stack), acafela.github.io (custom metrics with Prometheus scraping)
- **Tech blog portals** for ongoing articles: tech.kakao.com, toss.tech, techblog.woowahan.com, d2.naver.com, engineering.linecorp.com, medium.com/coupang-engineering — search for "모니터링", "Prometheus", "Grafana", "observability"

### Specifications and design documents

- **OpenTelemetry Specification**: opentelemetry.io/docs/specs/otel/ (github.com/open-telemetry/opentelemetry-specification)
- **OTLP Protocol Specification**: opentelemetry.io/docs/specs/otlp/
- **W3C Trace Context**: w3.org/TR/trace-context/ — Default propagation format in Spring Boot 3
- **Prometheus Data Model**: prometheus.io/docs/concepts/data_model/
- **OpenMetrics Specification**: openmetrics.io — Standardized metrics format exposed by `/actuator/prometheus`
- **Micrometer Docs Generator**: github.com/micrometer-metrics/micrometer-docs-generator — Auto-generates documentation from ObservationDocumentation enums

---

## Weekly schedule summary

| Week | Phase | Focus | Key Deliverable |
|------|-------|-------|-----------------|
| 1 | Actuator Internals | Auto-configuration, conditional annotations | Trace auto-config chain in source code |
| 2 | Actuator Internals | Endpoints, health indicators, info contributors | Custom health indicators in Kotlin |
| 3 | Actuator Internals | Security, exposure, custom endpoints | **Milestone 1**: Custom endpoint + security |
| 4 | Micrometer Internals | MeterRegistry, meter types, Meter.Id | Instrument all 7 meter types |
| 5 | Micrometer Internals | MeterFilter, naming conventions, Clock | MeterFilter chain for production |
| 6 | Micrometer Internals | Observation API, built-in binders | **Milestone 2**: Instrumented service |
| 7 | Custom Metrics & SLOs | @Timed/@Counted, Kotlin suspend gotchas | Coroutine-safe timing extensions |
| 8 | Custom Metrics & SLOs | Histograms, percentiles, distribution config | Histogram/SLO bucket configuration |
| 9 | Custom Metrics & SLOs | SLIs/SLOs/SLAs, burn-rate alerts, golden signals | **Milestone 3**: SLO dashboard + alerts |
| 10 | Backend Integration | Prometheus, exemplars, scrape configuration | Prometheus + exemplars working |
| 11 | Backend Integration | Grafana dashboards, Datadog | Custom Grafana dashboard |
| 12 | Backend Integration | OpenTelemetry, OTLP, log correlation | **Milestone 4**: Multi-backend stack |
| 13 | Production Patterns | K8s probes, ServiceMonitor, EKS patterns | ServiceMonitor + probe config on EKS |
| 14 | Production Patterns | Cardinality management, performance tuning | Cardinality defense MeterFilter chain |
| 15 | Production Patterns | Kotlin patterns, coroutines, testing | **Milestone 5**: Production EKS deploy |
| 16 | Capstone | End-to-end system | **Capstone**: Multi-service observable system |