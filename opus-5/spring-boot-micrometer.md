---
title: "Micrometer with Spring Boot — Capability-Oriented Observability Guide"
category: "Observability"
description: "A capability-oriented reference to Micrometer as it actually ships with Spring Boot, organized by what the library can do rather than by a week-by-week schedule. Baseline: Micrometer 1.17 (June 2026) with maintenance lines 1.16/1.15, Spring Boot 4.0 GA shipping Micrometer 1.16 and Micrometer Tracing 1.6 on Spring Framework 7 / Jakarta EE 11, and Spring Boot 3.5 on ~1.15. Covers the meter hierarchy and its mapping onto Prometheus types, distribution statistics in depth (why client-side publishPercentiles cannot be aggregated across pods while percentile histograms can), the full catalog of Boot auto-configured metrics for JVM, HTTP, HikariCP, Kafka, caches, executors and Tomcat, custom instrumentation, the Observation API as one instrumentation point yielding metric plus span plus log with its low- vs high-cardinality tag split, Micrometer Tracing after Sleuth, exporters and backends including the Prometheus simpleclient 0.x to prometheus-metrics-core 1.x migration and Pushgateway lag, Kubernetes and EKS production concerns, cardinality hygiene, exemplars for metrics-to-trace pivots, and multi-window error-budget burn alerts — closing with recommendations, project ideas, and explicit version caveats."
---

# Micrometer with Spring Boot: A Capability-Oriented Guide for Senior Engineers

## TL;DR
- **Micrometer is the "SLF4J for observability"**: a vendor-neutral metrics facade (plus the newer Observation API and Micrometer Tracing) that Spring Boot Actuator auto-wires. As of mid-2026, Micrometer **1.17.0 (released 8 June 2026)** is current, with maintenance lines 1.16.x/1.15.x; Spring Boot 3.5 manages ~1.15, and **Spring Boot 4.0.0 (GA 20 November 2025)** ships Micrometer 1.16 and Micrometer Tracing 1.6, built on Spring Framework 7 / Jakarta EE 11.
- **The single most important modern concept is the Observation API** (introduced in Micrometer 1.10): instrument once, emit metrics + traces (+ logs correlation) simultaneously — the docs describe it as "instrument once and have multiple benefits out of it" — with an explicit low-cardinality (metrics tags) vs high-cardinality (trace attributes) split. Spring Framework 6+/Boot 3+ moved native instrumentation (HTTP, Kafka, Redis, etc.) onto it and retired Spring Cloud Sleuth.
- **For your Prometheus + Grafana + EKS + Kotlin stack**, prefer server-side histograms (`publishPercentileHistogram`) over client-side percentiles so you can aggregate across pods with `histogram_quantile`, keep tag cardinality bounded (URI templating, common tags, no pod-name labels in-app), and wire exemplars end-to-end for metrics→trace pivots.

## Key Findings
1. Micrometer's meter set (Counter, Gauge, Timer, LongTaskTimer, DistributionSummary, TimeGauge, FunctionCounter, FunctionTimer, MultiGauge) maps cleanly onto Prometheus types; the recurring pitfalls are gauge GC (weak references) and cardinality explosions.
2. Client-side percentiles (`publishPercentiles`) are **not aggregable across dimensions/instances**; percentile histograms are. This is decisive in a multi-pod Kubernetes deployment.
3. Spring Boot auto-configures a large catalog of metrics (JVM, system, HTTP server/client, HikariCP, Kafka clients, caches, executors, Tomcat, Logback/Log4j2, and more) once Actuator + a registry are on the classpath.
4. The Prometheus registry migrated from the 0.x `simpleclient` to the 1.x `prometheus-metrics-core` client in Micrometer 1.13 / Spring Boot 3.3; the old client is deprecated and Pushgateway support lagged behind on the 1.x client.
5. Spring Boot 4 renames observability modules (`spring-boot-micrometer-metrics/-observation/-tracing`), adds a `spring-boot-starter-opentelemetry`, removes `@AutoConfigureObservability`, and fixes coroutine/Reactor context propagation with `spring.reactor.context-propagation=auto`.

## Details

### 1. Architecture and core concepts

**What Micrometer is.** Micrometer provides an abstraction layer for metrics collection — an API for meter types (counters, gauges, timers, distribution summaries) plus a `MeterRegistry` API that generalizes collection and propagation to backends. It is explicitly positioned as "Think SLF4J, but for observability." Spring Boot Actuator auto-configures a `MeterRegistry` and binds a large set of instrumentation to it.

**Registries.**
- `SimpleMeterRegistry` holds the latest value of each meter in memory and exports nowhere; it is autowired in Spring apps as a fallback and is the workhorse for tests.
- `MeterRegistry` is the base abstraction; exporters iterate over its meters to produce time series. Note: registering meters with the same ID multiple times keeps only the first registration.
- `CompositeMeterRegistry` fans out to multiple backends simultaneously. Spring Boot's injected `MeterRegistry` is in fact a composite.
- `Metrics.globalRegistry` is a static global composite with static builders (`Metrics.counter(...)`). In Spring apps prefer **injecting** the `MeterRegistry` bean over the global static; the global is handy for library code or where DI is unavailable.

**Meter types (and when to use each).**
- **Counter** — monotonic increasing count (requests, errors). In Prometheus you `rate()` it. Counters reset on restart; Prometheus `rate()/increase()` handle resets.
- **Gauge** — instantaneous, sampled value that "changes only when observed" (queue depth, cache size). **Gauges hold a weak reference** to the observed object so as not to prevent GC — if the object is collected, the gauge reports NaN. Never hold the gauge value in a plain field you also mutate elsewhere without keeping a strong reference to the source object. Use for values that can go up and down and that you can read on demand.
- **Timer** — short-duration events + rate (latency). Records count, total time, max.
- **LongTaskTimer** — measures the duration of **in-flight** long-running tasks (you can see the currently-running time before completion); good for batch jobs, scheduled tasks, long polls.
- **DistributionSummary** — distribution of non-time values (payload sizes, batch sizes).
- **TimeGauge** — a gauge whose value is a duration in a known time unit.
- **FunctionCounter / FunctionTimer** — "function-tracking" meters that derive a count/total from an external monotonic source (e.g. a third-party client's internal counters); Micrometer computes deltas. Used heavily by binders (Kafka, HikariCP).
- **MultiGauge** — manages a set of gauges whose tag combinations change over time (e.g. per-status counts you recompute periodically), with `register(...)` replacing the previous set.

**Naming.** Use dot-separated, lowercase, hierarchical-looking names (`http.server.requests`); Micrometer's `NamingConvention` per registry translates these to the backend idiom (Prometheus → `http_server_requests_seconds_...`; snake_case; base-unit suffixes). Prefer base units (seconds, bytes) and set them on the meter. Never register the same name with different tag key sets — Prometheus strongly discourages inconsistent tag keys per name.

**Tags / cardinality.** Tags are dimensions; the cartesian product of tag values is the number of time series. Guard against explosion with `MeterFilter`:
- `MeterFilter.deny(...)` / `accept(...)`, `denyNameStartsWith(...)`,
- `MeterFilter.maximumAllowableTags(...)` and `maximumAllowableMetrics(...)`,
- `MeterFilter.replaceTagValues(...)` to collapse high-cardinality values,
- and `renameTag`. There is also a `HighCardinalityTagsDetector` (docs added in the 1.16 line) to help find offenders at runtime.

`Meter.Id` is the (name, tags, base unit, type) tuple that identifies a meter. `MeterDocumentation` / `ObservationDocumentation` let you formally document meters/observations (names, tag keys) as enums — useful for governance across a microservice fleet.

### 2. Distribution statistics and percentiles (deep dive)

**Two approaches:**
- **Percentile histograms** (`publishPercentileHistogram()`): Micrometer accumulates into an underlying HdrHistogram and ships a preset set of cumulative buckets. Prometheus/Atlas/Wavefront then compute percentiles server-side (`histogram_quantile` in Prometheus). **These are aggregable across dimensions and across instances** — you sum bucket counts across pods, then take the quantile. This is what you want on EKS.
- **Client-side percentiles** (`publishPercentiles(0.5, 0.95, 0.99)`): Micrometer computes a percentile approximation per meter ID in-process and ships the value (as a gauge tagged `phi`/`quantile`). **These cannot be aggregated across tags or instances** — averaging p99s across pods is statistically meaningless. Useful only where the backend can't do server-side quantiles.

When both are configured, the histogram is preferred (on OTLP, the Summary datapoint is treated as legacy).

**Bucket math.** For `publishPercentileHistogram`, buckets are preset by a generator empirically tuned by Netflix. Per the Micrometer docs (histogram-quantiles), verbatim: *"By default, the generator yields 276 buckets, but Micrometer includes only those that are within the range set by minimumExpectedValue and maximumExpectedValue, inclusive. Micrometer clamps timers by default to a range of 1 millisecond to 1 minute, yielding 73 histogram buckets per timer dimension."* Each bucket is a separate time series in Prometheus, so histograms are much more expensive than summaries — tune the expected-value range to control both bucket count and the HdrHistogram memory footprint/accuracy.

**SLOs.** `serviceLevelObjectives(...)` publishes a cumulative histogram with buckets at your explicit SLO boundaries. Combined with `publishPercentileHistogram` it *adds* buckets; alone it publishes *only* those buckets. SLOs are based on **recorded values, not percentiles** — `serviceLevelObjectives(Duration.ofMillis(100))` gives you a `le="0.1"` bucket you can turn into an SLO ratio.

**Decay.** `DistributionStatisticConfig` also controls `expiry` (default 2 min) and `bufferLength` (default 3): the client-side percentile/max statistics use a ring buffer of that many windows and decay over `expiry`, so a one-off spike ages out rather than pinning `max` forever.

**Prometheus native histograms.** These use exponential/sparse buckets for a compact, high-resolution representation. Support has been experimental and, historically, "not supported in Micrometer" per community write-ups; the newer Prometheus 1.x Java client and a `fstab/micrometer-registry-prometheus_native-example` demonstrate exposing native histograms (Protobuf exposition, viewable via `/actuator/prometheus?debug=prometheus-protobuf`). Treat native-histogram support as version-dependent and verify against your exact Micrometer/Boot versions before relying on it in production. When it works, it removes the fixed-bucket tradeoff and reduces series count dramatically.

**Coordinated omission.** When you correlate Micrometer server-side latency with k6 load tests, remember Micrometer times only requests that actually reached the server and completed; requests delayed because the system was stalled ("coordinated omission") are undercounted, so server-side p99 can look better than client-perceived p99. Trust k6's client-side latency (which sees queuing) for user-facing SLOs and use Micrometer histograms for server-internal attribution. k6 also computes client-side percentiles per-instance — the same non-aggregability caveat applies if you run distributed k6.

### 3. Auto-configured metrics in Spring Boot

With `spring-boot-starter-actuator` plus a registry (e.g. `micrometer-registry-prometheus`) and `management.endpoints.web.exposure.include=prometheus,health,metrics`, Spring Boot binds (non-exhaustive):

**JVM (via `JvmMemoryMetrics`, `JvmGcMetrics`, `JvmThreadMetrics`, `ClassLoaderMetrics`, and JVM info):**
- `jvm.memory.used/committed/max` (tags `area`=heap/nonheap, `id`=pool), `jvm.buffer.*`
- `jvm.gc.pause` (Timer), `jvm.gc.memory.allocated/promoted`, `jvm.gc.max.data.size`
- `jvm.threads.live/daemon/peak/states`, `jvm.classes.loaded/unloaded`
- Interpretation: rising `jvm.gc.pause` sum/rate + growing `jvm.memory.used{area="heap"}` after GC = heap pressure; watch old-gen pool `jvm.memory.used{id=~".*Old.*"}` trending toward `max`.

**System/process (`ProcessorMetrics`, `UptimeMetrics`, `FileDescriptorMetrics`):**
- `system.cpu.usage`, `process.cpu.usage`, `system.load.average.1m`
- `process.uptime`, `process.start.time`, `process.files.open/max`
- `disk.free/total`

**HTTP server — `http.server.requests`** (Timer; Spring MVC + WebFlux via `ServerHttpObservationFilter` / the Observation API). Tags: `method`, `uri` (the **templated** route, e.g. `/orders/{id}`), `status`, `outcome` (SUCCESS/CLIENT_ERROR/SERVER_ERROR), `exception`, `error`. **Raw URIs cause cardinality explosion** — always use path templates; unmatched routes report `uri="UNKNOWN"` (a known behavior change tightened in Boot 3.3 via `DefaultServerRequestObservationConvention`). Enable histograms with `management.metrics.distribution.percentiles-histogram.http.server.requests=true`.

**HTTP client — `http.client.requests`** for `RestTemplate`, `RestClient`, and `WebClient`, registered via observation customizers (`ObservationRestTemplateCustomizer`, `ObservationRestClientCustomizer`, `ObservationWebClientCustomizer`). **URI templating is critical**: pass templates + variables (`restClient.get().uri("/users/{id}", id)`, or `webClient...uri(b -> b.path("/v1/users/{id}").build(id))`) so the `uri` tag is the template, not the expanded URL. `management.metrics.web.client.max-uri-tags` (default 100) caps runaway URI tags. To always be sure, register a custom `ClientRequestObservationConvention` (Boot 3+).

**Apache HttpClient 5 connection-pool metrics.** Micrometer ships a built-in binder: **`io.micrometer.core.instrument.binder.httpcomponents.hc5.PoolingHttpClientConnectionManagerMetricsBinder`** in `micrometer-core`. The `hc5` package is present in the micrometer-core 1.11.0 Javadoc; the old HttpClient 4.x class in the parent `httpcomponents` package is deprecated as of 1.12.5 in favor of HttpComponents 5.x. It exposes gauges prefixed `httpcomponents.httpclient.pool`:

| Metric | Meaning |
|---|---|
| `httpcomponents.httpclient.pool.total.max` | max allowed persistent connections, all routes |
| `httpcomponents.httpclient.pool.total.connections` | connections in pool, tag `state`=available/leased |
| `httpcomponents.httpclient.pool.total.pending` | requests blocked awaiting a free connection |
| `httpcomponents.httpclient.pool.route.max.default` | default max connections per route |

All carry an `httpclient` tag (the pool name you pass) plus any custom tags. For **per-request** HttpClient 5 observations use `ObservationExecChainHandler` (registered as an exec interceptor named `"micrometer"`); `MicrometerHttpClientInterceptor` exists for `HttpAsyncClient`, and `MicrometerHttpRequestExecutor` is deprecated in favor of `ObservationExecChainHandler`. Kotlin wiring:

```kotlin
@Configuration
class HttpClientConfig {
    @Bean
    fun connectionManager(): PoolingHttpClientConnectionManager =
        PoolingHttpClientConnectionManagerBuilder.create()
            .setMaxConnTotal(100).setMaxConnPerRoute(20).build()

    @Bean
    fun poolMetrics(cm: PoolingHttpClientConnectionManager, reg: MeterRegistry) =
        PoolingHttpClientConnectionManagerMetricsBinder(cm, "orders-http").apply { bindTo(reg) }
}
```

Spring Boot does **not** auto-register this pool binder (3.x or 4.x) — it is manual. Note Apache HttpClient 5.6+ now ships its own `httpclient5-observation` module (metric names differ, e.g. `http.client.pool.leased/available/pending`), and the Micrometer docs now flag the built-in hc5 instrumentation as deprecated in favor of that Apache module.

**DataSource / HikariCP.** With Actuator + Micrometer on the classpath, HikariCP metrics are auto-bound: `hikaricp.connections` (total), `.active`, `.idle`, `.pending` (threads waiting), `.max`, `.min`, `.timeout` (count), `.acquire` (Timer), `.creation` (Timer), `.usage` (Timer). Plus generic `jdbc.connections.active/idle/max/min`. **Interpretation:** `hikaricp.connections.pending > 0` sustained = pool undersized for load; rising `.acquire` p99 = contention; `.timeout` increments = requests failing to get a connection (raise pool size or fix slow queries). If you build a `HikariDataSource` manually, pass `new MicrometerMetricsTrackerFactory(registry)`. **Aurora MySQL note:** with a reader/writer split you typically run separate pools per endpoint — tag them (`pool` name) so writer saturation is distinguishable from reader; Aurora failover can invalidate connections, so also watch `.timeout` and `.creation` spikes around failover events. (No Aurora-specific Micrometer binder exists; these are the standard Hikari signals.)

**JPA/Hibernate.** `hibernate.*` statistics (via `HibernateMetrics`) — query counts, cache hits, session stats — require `hibernate.generate_statistics=true`. Note this instrumentation has been **deprecated/removed from Spring Boot's auto-configuration** in recent versions (moved out of the default path as Hibernate's own metrics/observation story evolved); `spring.data.repository.invocations` (Repository-level Timer) remains useful.

**Kafka.** `KafkaClientMetrics` / `KafkaConsumerMetrics` (Micrometer) bind the native Kafka client metrics; Spring Boot auto-exposes them from 2.5+ once Actuator is present. Key names (dotted form): `kafka.consumer.fetch.manager.records.lag` (and `.records.lag.max`), `kafka.consumer.fetch.manager.fetch.latency.avg`, `kafka.consumer.coordinator.rebalance.rate.per.hour`, `kafka.consumer.last.poll.seconds.ago`, `kafka.producer.record.send.rate`, producer batch-size metrics. Also `spring.kafka.listener` (listener Timer) and `spring.kafka.template`. **Most important for lag monitoring:** `records-lag-max` / per-partition `records.lag`. Caveat: some lag metrics historically lacked topic/partition tags depending on client state; consumer-group lag is not a JVM metric (use MSK CloudWatch or an offset exporter for authoritative group lag). For custom tags, add `MicrometerConsumerListener`/`MicrometerProducerListener` to the factory.

**Caching.** Caffeine (`CaffeineCacheMetrics`) and others bind `cache.gets` (tag `result`=hit/miss), `cache.puts`, `cache.evictions`, `cache.size`. Hit ratio in PromQL: `sum(rate(cache_gets_total{result="hit"}[5m])) / sum(rate(cache_gets_total[5m]))`. Redis/Valkey: per the Spring Boot 4.0 release notes, *"The Redis auto-configuration has been improved to auto-configure MicrometerTracing, rather than MicrometerCommandLatencyRecorder. The former operates on the Observation API and provides both metrics and spans."*

**Task execution / scheduling / executors.** `executor.*` metrics via `ExecutorServiceMetrics`: `executor.active`, `executor.completed`, `executor.pool.size/core/max`, `executor.queued`, `executor.queue.remaining`, plus `executor` (task execution Timer) and `executor.idle` (queue wait Timer) for `ThreadPoolExecutor`. **Queue depth (`executor.queued`) climbing = pool saturation.** **Virtual threads (Loom):** add `io.micrometer:micrometer-java21` for the virtual-thread binder — it measures the duration/count of virtual threads being **pinned** and counts failed starts/unparks (critical for spotting pinning regressions when you move blocking code onto virtual threads).

**Web servers.** `tomcat.sessions.*`, `tomcat.threads.*` (Tomcat); Jetty (`JettyServerThreadPoolMetrics`, `JettyStatisticsMetrics`); Netty/Reactor metrics for WebFlux. Spring Batch exposes `spring.batch.job`/`spring.batch.step` timers in recent versions.

**Logging.** `LogbackMetrics` → `logback.events` (tag `level`); `Log4j2Metrics` → `log4j2.events`. A rising `rate(logback_events_total{level="error"}[5m])` is a cheap error-rate signal.

**Other.** Spring Security (observation-based auth/filter-chain observations in recent versions), Spring Integration (`spring.integration.*` channel/handler timers), Spring GraphQL, R2DBC pool metrics.

**Configuration keys (note the Boot 2→3 renames).** Spring Boot 3 moved per-registry export properties from `management.metrics.export.<reg>.*` to top-level `management.<reg>.metrics.export.*` (e.g. `management.prometheus.metrics.export.enabled`). Common keys:
```yaml
management:
  endpoints.web.exposure.include: prometheus,health,metrics,info
  metrics:
    tags: { application: ${spring.application.name} }   # common tags
    distribution:
      percentiles-histogram:
        http.server.requests: true
      slo:
        http.server.requests: 50ms,100ms,200ms,500ms
      percentiles:
        http.server.requests: 0.95,0.99   # client-side; avoid for cross-pod
    web.client.max-uri-tags: 100
  prometheus.metrics.export.enabled: true
  observations:
    key-values: { region: ap-northeast-2 }
    http.server.requests.name: http.server.requests
  tracing:
    enabled: true
    sampling.probability: 0.1
  otlp.tracing.endpoint: http://otel-collector:4318/v1/traces
```
**Spring Boot 4 changes:** observability modules were renamed (`spring-boot-metrics`→`spring-boot-micrometer-metrics`, `-observation`→`-micrometer-observation`, `-tracing`→`-micrometer-tracing`); a new `spring-boot-starter-opentelemetry` bundles most OTel/Micrometer deps; OTLP tracing export config moved under `management.opentelemetry.tracing.export.*` and `management.tracing.export.enabled`; `logging.console.enabled` was added.

### 4. Custom instrumentation

**Programmatic meters.** Inject `MeterRegistry`; build meters with the fluent builders and **store the returned meter in a field** (avoid per-call lookups):
```kotlin
@Service
class OrderService(registry: MeterRegistry) {
    private val placed = Counter.builder("orders.placed")
        .description("Orders successfully placed")
        .tag("channel", "web")
        .register(registry)
    private val reg = registry
    fun place(order: Order) {
        // dimensional business metric: outcome as a low-cardinality tag
        reg.counter("orders.processed", "result", "success", "payment", order.method).increment()
        placed.increment()
    }
}
```

**MeterBinder.** For metrics that depend on other beans, implement `MeterBinder` and register it as a `@Bean` — Spring Boot auto-calls `bindTo` and this defers gauge registration until the registry is ready (avoids shutdown-ordering `NPE`/`BeanCreationNotAllowedException` seen when gauges reference beans being destroyed).

**`@Timed` / `@Counted`.** Require the aspect beans:
```kotlin
@Bean fun timedAspect(r: MeterRegistry) = TimedAspect(r)
@Bean fun countedAspect(r: MeterRegistry) = CountedAspect(r)
```
Limitations (Spring AOP proxying): **only public methods, and self-invocation (calling the annotated method from within the same class) bypasses the proxy** so no metric is recorded. Controllers are timed by default even without `TimedAspect`. Under native AspectJ compile-time weaving the aspect won't fire unless the Micrometer jar is post-compile woven. `longTask=true` switches to a `LongTaskTimer`.

**Common tags via `MeterRegistryCustomizer`:**
```kotlin
@Bean
fun commonTags(@Value("\${spring.application.name}") app: String) =
    MeterRegistryCustomizer<MeterRegistry> { r ->
        r.config().commonTags("application", app, "env", System.getenv("ENV") ?: "local")
    }
```
Use `MeterFilter` for renaming/denying/limiting. Prefer injecting pod/region as *common tags* from the environment rather than per-meter.

**Modeling business metrics dimensionally.** Model outcomes as bounded low-cardinality tags (`result=success|declined|error`, `payment=card|bank`), never customer IDs or free-text. Keep the meter name the noun (`payments`), the tags the adjectives.

**Testing.** Use `SimpleMeterRegistry` in unit tests; assert with `micrometer-test`'s `MeterRegistryAssert` (`assertThat(registry).hasTimerWithNameAndTags(...)`). In Boot 4, `@AutoConfigureObservability` was **removed** in favor of finer-grained `@AutoConfigureMetrics` / `@AutoConfigureTracing`, backed by `spring-boot-micrometer-metrics-test` / `-tracing-test`.

### 5. Micrometer Observation API

Introduced in Micrometer 1.10, the Observation API is the modern unified abstraction: you create one `Observation` and registered `ObservationHandler`s turn it into metrics, traces, logs, or anything else — the docs describe the goal as **"instrument once and have multiple benefits out of it."**

Components:
- `Observation` / `Observation.Context` — a mutable context holder carrying data for handlers.
- `ObservationRegistry` — holds handlers, predicates, filters, conventions.
- `ObservationHandler` — reacts to lifecycle events (start, stop, scopes, error). `DefaultMeterObservationHandler` produces a Timer + LongTaskTimer; a tracing handler produces spans. Compose with `FirstMatchingCompositeObservationHandler`.
- `ObservationConvention` — separates lifecycle from naming/tagging so names and key-values become configuration (override to rename/retag globally via `GlobalObservationConvention`).
- `ObservationPredicate` — disable observations conditionally.
- `ObservationFilter` — mutate/enrich contexts (e.g. add cloud tags).

```kotlin
Observation.createNotStarted("order.process", observationRegistry)
    .lowCardinalityKeyValue("channel", "web")      // becomes a metric tag
    .highCardinalityKeyValue("order.id", id)       // trace attribute only
    .observe { processOrder(id) }
```

**Low vs high cardinality is a first-class distinction:** low-cardinality key values become metric tags (bounded); high-cardinality key values go only to traces (unbounded, e.g. IDs). This is exactly the discipline that prevents Prometheus series explosions while keeping rich trace context.

**`@Observed`** (with an `ObservedAspect` bean) instruments a method as an observation → both a timer and, if tracing is on, a span. Boot 4 added support for `@ObservationKeyValue` to declaratively add key-values.

**Migration reality.** Spring Framework 6+/Boot 3+ moved native instrumentation onto the Observation API and **retired Spring Cloud Sleuth**; responsibility for instrumentation shifted to each component (Spring MVC/WebFlux, Spring Kafka, Spring Data Redis, etc.). Practically: you configure handlers/conventions once, and every instrumented component emits consistent metrics + spans.

**Context propagation (critical for a Kotlin shop).** `micrometer-context-propagation` (a zero-dependency SPI: `ThreadLocalAccessor`, `ContextAccessor`, `ContextRegistry`, `ContextSnapshot`) bridges `ThreadLocal` ↔ Reactor Context ↔ coroutine context so trace/MDC context survives thread hops.
- **Reactor**: since Reactor 3.5 it embeds the SPI; `Hooks.enableAutomaticContextPropagation()` enables automatic restoration. Automatic mode has real performance cost (ThreadLocal access in the pipeline) — a documented tradeoff.
- **Kotlin coroutines**: this was a long-standing pain point (`kotlinx.coroutines` #4187, Spring Framework #32165). **Resolved in Spring Framework 7 / Spring Boot 4**: set `spring.reactor.context-propagation=auto` and MDC/trace context propagates through `suspend` functions out of the box. **Known remaining gotcha (Boot 4.0.x):** context does **not** propagate into coroutines that collect a returned `Flow` (Spring Framework #36427) — MDC works in `suspend` controller methods but not inside Flow collectors; and exception-handler paths may lose context. For SLF4J MDC you also register `Slf4jThreadLocalAccessor`.
- **Virtual threads**: ThreadLocal-based propagation generally works, but pinning and per-carrier assumptions change; verify traces are continuous when enabling virtual threads.

### 6. Micrometer Tracing

Micrometer Tracing is the **successor to Spring Cloud Sleuth**. It provides vendor-neutral `Tracer`/`Span` abstractions with bridges to **OpenTelemetry** (`micrometer-tracing-bridge-otel`) or **OpenZipkin Brave** (`micrometer-tracing-bridge-brave`). Boot 4 manages Micrometer Tracing 1.6.

**Setup (Boot 3.x, OTel + OTLP):**
```kotlin
// build.gradle.kts
implementation("org.springframework.boot:spring-boot-starter-actuator")
implementation("io.micrometer:micrometer-tracing-bridge-otel")
implementation("io.opentelemetry:opentelemetry-exporter-otlp")
```
```yaml
management:
  tracing.sampling.probability: 0.1     # 10% in prod
  otlp.tracing.endpoint: http://otel-collector:4318/v1/traces
```
Boot 3 defaults to **W3C `traceparent`** and 128-bit IDs; switch/add B3 with `management.tracing.propagation.type=b3` (or `w3c,b3` for interop). Brave→Zipkin uses `spring-boot-starter-zipkin` + `management.zipkin.tracing.endpoint`. **Boot 4 note:** the OTel→Zipkin auto-config is deprecated (OpenTelemetry deprecated Zipkin support) and will be removed in Boot 4.2; module names moved to `spring-boot-micrometer-tracing-opentelemetry` etc. Boot 4's `spring-boot-starter-opentelemetry` bundles the common path.

**Trace–metrics–logs correlation.**
- **Logs**: Micrometer Tracing populates MDC `traceId`/`spanId`; add to your Logback pattern:
  ```
  logging.pattern.level=%5p [${spring.application.name},%X{traceId:-},%X{spanId:-}]
  ```
- **Exemplars** (metrics→trace pivot in Grafana): with the 1.x Prometheus client you need a `SpanContext` bean (`io.prometheus.metrics.tracer.common.SpanContext`); with the deprecated simpleclient it was `SpanContextSupplier`. **If you use Micrometer Tracing, Spring Boot auto-configures the exemplar provider.** Exemplars require **histogram buckets** on the metric and the **OpenMetrics** exposition format; only sampled traces become exemplars by default (`management.tracing.exemplars.include`). One exemplar per bucket per scrape (overwritten by later requests). Enable with:
  ```yaml
  management.metrics.distribution.percentiles-histogram.http.server.requests: true
  ```
  and ensure Grafana Alloy/Agent forwards exemplars (`send_exemplars`). Then Loki (logs by traceId) + Tempo (traces) + Prometheus (exemplars) give a full LGTM pivot.

**Micrometer Tracing vs the OpenTelemetry Java agent.**
- **Micrometer Tracing (native path):** instrumentation maintained by the Spring/library authors; **one instrumentation → metrics + traces**; works with **GraalVM native image** (agents can't be used with native). Metric names follow Micrometer/Spring conventions.
- **OTel Java agent (`-javaagent`):** zero-code auto-instrumentation of many libraries; but it produces its **own metric names** which can diverge from Micrometer/Spring dashboards, and running both can cause **duplicate spans/metrics**. The agent v2.x changed default behavior (traces only on receive/send; `@WithSpan` for manual spans).
- **Recommendation:** on Spring Boot, prefer **Micrometer Tracing + OTLP to a Collector**; use the OTel agent only for non-Spring libraries you can't instrument natively, and if you run both, disable overlapping instrumentation to avoid duplication.

### 7. Exporters and backends

Micrometer supports many registries: **Prometheus, OTLP**, Datadog, New Relic, CloudWatch, Dynatrace, Graphite, InfluxDB/Telegraf, SignalFx, Stackdriver, Wavefront, Atlas, StatsD, JMX, and more. Add the matching `micrometer-registry-*`; the composite fans out.

**Prometheus (pull).** Add `micrometer-registry-prometheus`, expose `/actuator/prometheus`. Scrape config:
```yaml
scrape_configs:
  - job_name: spring
    metrics_path: /actuator/prometheus
    static_configs: [{ targets: ["HOST:PORT"] }]
```
`registry.scrape("application/openmetrics-text")` (or the Actuator endpoint content negotiation) gives OpenMetrics for exemplars.

**The Prometheus client migration.** Micrometer 1.13 / Spring Boot 3.3 switched `micrometer-registry-prometheus` from the **0.x `simpleclient`** to the **1.x `prometheus-metrics` (`prometheus-metrics-core`)** client. Consequences:
- Some **exported metric names changed** and there were behavioral differences.
- **Pushgateway was not supported on the 1.x client** initially.
- The old client remains available as **`micrometer-registry-prometheus-simpleclient`** (deprecated; auto-config removed in Spring Boot 3.5).
- **Don't override Micrometer's managed version** — e.g. forcing 1.13 on Boot 3.2 breaks Prometheus auto-config; let the Boot BOM manage it. OpenRewrite recipe `UpgradeMicrometer_1_13` automates the package move `io.micrometer.prometheus`→`io.micrometer.prometheusmetrics`. Micrometer 1.16 upgraded the client to 1.4.x, bringing **Unicode support** with naming-convention behavioral changes (see the 1.16 migration guide).

**OTLP.** `micrometer-registry-otlp` pushes via OTLP; `management.otlp.metrics.export.*` (url, step, headers). OTLP prefers Histogram/Exponential-Histogram datapoints; the Summary (client percentiles) datapoint is legacy. Boot 4's `spring-boot-starter-opentelemetry` streamlines this.

**Push vs pull & step registries.** Push registries extend `PushMeterRegistry`/`StepMeterRegistry`. **Step registries normalize counts/sums to a rate over the publishing interval (step)** — this is why a counter "looks different" on a step registry (Datadog, OTLP-step, etc.) than on Prometheus: within a step the value accumulates and is reported per-interval. For short-lived/batch jobs, step registries have a **"last value" problem**: the final partial step may not be published on shutdown (Micrometer added partial-step-on-shutdown handling, but verify).

**Pushgateway for batch (Spring Batch).** When the Pushgateway dependency is present, Spring Boot auto-configures a `PrometheusPushGatewayManager`; tune via `management.prometheus.metrics.export.pushgateway.*`. Use it for jobs too short-lived to scrape. Caveat: Pushgateway support depends on the Prometheus client version (unsupported on the early 1.x client), so pin accordingly.

**AWS/EKS.** `micrometer-registry-cloudwatch` pushes to CloudWatch (costs per custom metric; mind cardinality × dimensions). On EKS most teams prefer Prometheus scraping (or OTLP → Collector → AMP/Grafana Cloud) over CloudWatch for high-cardinality app metrics, using CloudWatch mainly for infra/MSK metrics like consumer-group lag.

### 8. Kubernetes / production concerns (EKS)

- **Pod labeling / cardinality.** **Do not** put pod name/IP as a Micrometer tag in-app — that multiplies every series by pod churn. Let Prometheus/ServiceMonitor relabeling attach `pod`, `namespace`, `instance` at scrape time. In-app common tags should be low-churn: `application`, `env`, `region`, maybe `version`.
- **Aggregating percentiles across pods.** You **must** use histograms and aggregate then quantize: `histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))`. Never average per-pod client-side p99s.
- **Scrape config.** Use the Prometheus Operator `PodMonitor`/`ServiceMonitor` pointing at `/actuator/prometheus`, or **Grafana Alloy** scraping the Actuator endpoint (and enable `send_exemplars`/remote_write with exemplars for Tempo pivots).
- **Endpoint exposure & security.** Run Actuator on a **separate management port** (`management.server.port`) not exposed publicly; restrict `management.endpoints.web.exposure.include` to what you scrape; secure `/actuator/prometheus` via network policy/authn. Don't expose `env`/`heapdump`.
- **Overhead.** Each unique (name × tag-values) is a time series with memory cost in both app and Prometheus. Client-side percentiles and histograms add per-meter HdrHistogram memory (bounded by min/max expected values); histograms add many bucket series. Measure with the `/actuator/metrics` meter count, `prometheus_tsdb_head_series` on the Prometheus side, and JVM heap of the app. A `HighCardinalityTagsDetector` helps catch offenders.
- **Anti-patterns / troubleshooting.**
  - *Missing metrics*: registry dependency absent, endpoint not exposed, or binder needs a classpath lib.
  - *Duplicated meters / `Collector already registered`*: same name registered twice (e.g. `@Timed` colliding with manual timer).
  - *Timers with zero counts / NaN percentiles*: client-side percentiles with no histogram, or gauge target GC'd.
  - *Unbounded tags*: raw URIs, path variables, user input, exception messages as tags — the #1 cause of Prometheus OOM.

### 9. Version and ecosystem currency (mid-2026)

- **Micrometer:** current line **1.17.x** — 1.17.0 released 8 June 2026 (Maven Central lists all `io.micrometer` modules with a last release of Jun 8, 2026; see the GitHub "Release 1.17.0" and the 1.17 migration guide). LTS-ish maintenance on 1.15/1.16. 1.13 = Prometheus 1.x client migration; 1.16 = Prometheus client 1.4.x + Unicode naming changes; `micrometer-java11`/`micrometer-java21` split out HTTP-client and virtual-thread binders respectively.
- **Micrometer Tracing:** 1.5.x/1.6.x lines; Boot 4 manages 1.6.
- **Spring Boot 3.x vs 4.x:** Boot 4.0.0 (GA 20 November 2025) is built on **Spring Framework 7 / Jakarta EE 11**, manages **Micrometer 1.16 / Tracing 1.6**, renames observability modules, adds `spring-boot-starter-opentelemetry`, removes `@AutoConfigureObservability`, improves Redis observability (Observation-based) and coroutine context propagation (`spring.reactor.context-propagation=auto`), and moves OTLP tracing export props under `management.opentelemetry.tracing.export.*`. Zipkin-over-OTel auto-config deprecated (removal in 4.2).
- **Deprecations to watch:** `micrometer-registry-prometheus-simpleclient` (deprecated), old `httpcomponents` (hc4) binders, `MicrometerHttpRequestExecutor`, Hibernate metrics auto-config, Sleuth (gone).
- **Community resources:** official docs (`docs.micrometer.io`, `docs.spring.io/spring-boot/reference/actuator`), Micrometer/Spring Boot GitHub wikis & release notes, Spring blog "Observability with Spring Boot 3" and "Let's use OpenTelemetry with Spring" (2024), and talks/posts by **Tommy Ludwig (@shakuzen)**, **Jonatan Ivanov**, and **Marcin Grzejszczak**. Korean-language: search Korean tech blogs (e.g. Woowahan/우아한형제들 tech blog, Kakao/Naver D2) for "Micrometer 관측 가능성/옵저버빌리티" write-ups — several good Spring Boot 3 observability posts exist, though verify version currency.

### 10. Practical learning path and project ideas

**Progression (Kotlin/Boot/Kafka/Aurora/EKS):**
1. **Basics:** Add Actuator + `micrometer-registry-prometheus`; expose `/actuator/prometheus`; explore auto-config metrics; build a Grafana RED dashboard from `http.server.requests`.
2. **Custom meters:** Instrument an **order service** — `orders.placed` counter (tags: channel, result), an order-processing `Timer` with `publishPercentileHistogram`, a MultiGauge of orders-by-status. Add `@Timed` + `TimedAspect`.
3. **DB & pool:** Enable HikariCP metrics for Aurora writer/reader pools; alert on `hikaricp.connections.pending`; wire the Apache HttpClient 5 pool binder for an outbound client.
4. **Kafka:** Expose consumer lag (`kafka.consumer.fetch.manager.records.lag.max`), producer send-rate; alert on lag.
5. **Distribution stats:** Add SLO buckets to a critical timer; compute an Apdex/SLO ratio in PromQL; validate p99 against a **k6** run (note coordinated omission).
6. **Observation API:** Convert a business flow to `@Observed`; add a custom `ObservationConvention` to rename/retag; verify low/high cardinality split.
7. **Tracing + exemplars:** Add `micrometer-tracing-bridge-otel` + OTLP to a Collector → Tempo; put `traceId` in logs → Loki; enable exemplars end-to-end; pivot metric→trace in Grafana.
8. **EKS production:** ServiceMonitor/Alloy scrape, common tags, cross-pod `histogram_quantile`, SLO burn-rate alerts, separate management port.

**Essential PromQL panels.**
- **RED — Rate:** `sum(rate(http_server_requests_seconds_count[5m]))`
- **RED — Errors:** `sum(rate(http_server_requests_seconds_count{outcome="SERVER_ERROR"}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))`
- **RED — Duration p99 (cross-pod):** `histogram_quantile(0.99, sum by (le,uri) (rate(http_server_requests_seconds_bucket[5m])))`
- **USE — CPU:** `system_cpu_usage`, `process_cpu_usage`
- **USE — Saturation (pool):** `hikaricp_connections_pending`, `executor_queued`
- **JVM:** `sum by (id) (jvm_memory_used_bytes{area="heap"})`, `rate(jvm_gc_pause_seconds_sum[5m])`
- **Kafka lag:** `max by (topic) (kafka_consumer_fetch_manager_records_lag_max)`
- **Error budget burn (multi-window):** fast `(1 - sum(rate(http_server_requests_seconds_bucket{le="0.3",outcome="SUCCESS"}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))) > (14.4 * (1 - 0.99))` combined with a 1h window for the classic multi-burn-rate SLO alert.

## Recommendations
1. **Standardize on server-side histograms** for latency SLIs (`management.metrics.distribution.percentiles-histogram.http.server.requests=true` + explicit `slo` buckets). Only use client-side `percentiles` for single-instance local debugging. **Threshold to change:** if Prometheus head series from a service exceeds a few hundred thousand, trim buckets via `minimum/maximumExpectedValue` or drop unneeded SLO buckets.
2. **Adopt the Observation API + Micrometer Tracing + OTLP→Collector** as the default; avoid the OTel Java agent on Spring services unless instrumenting non-Spring libs, and never run both without disabling overlaps. Wire **exemplars** now since you already run Grafana/Tempo.
3. **Enforce cardinality hygiene**: URI templating everywhere, `MeterFilter.maximumAllowableTags`, common tags injected from env (no pod names in-app), and a periodic `HighCardinalityTagsDetector`/series-count review. **Trigger to act:** any new `uri="UNKNOWN"` surge or `max-uri-tags` cap being hit.
4. **On the Boot 4 migration**: update module names, adopt `spring-boot-starter-opentelemetry`, set `spring.reactor.context-propagation=auto` for coroutines, and replace `@AutoConfigureObservability` with `@AutoConfigureMetrics`/`@AutoConfigureTracing` in tests. Validate coroutine/`Flow` MDC propagation given the open Boot 4.0.x Flow gap.
5. **For batch/Spring Batch**, use Pushgateway (pin a Prometheus client version that supports it) rather than relying on scrapes of short-lived pods.

## Caveats
- Several specifics are **version-dependent**: property names (Boot 2 vs 3 vs 4), the Prometheus client 0.x→1.x metric-name changes, native-histogram support, and the exact micrometer-core version that introduced the hc5 binder (evidence points to 1.11.0; confirm against release notes). Verify against your exact Micrometer/Boot versions.
- **Prometheus native histograms** in Micrometer have moved between "experimental/unsupported" and demo-level support; do not assume production readiness without testing your versions.
- **Coroutine/Reactor context propagation** works in Boot 4 with `spring.reactor.context-propagation=auto`, but there is an open issue (Spring Framework #36427) where MDC/trace context is not propagated into coroutines collecting a returned `Flow`, and exception-handler paths can lose context.
- **Consumer-group lag** from Kafka client JVM metrics is per-consumer, not authoritative group lag; for group-level lag use MSK CloudWatch metrics or an offset-based exporter.
- Some figures (bucket counts, defaults like 276 buckets/73 timer buckets, expiry=2min, bufferLength=3) are Micrometer defaults that can change across versions and are overridable.
- The Apache `httpclient5-observation` module (HttpClient 5.6+) is now the Apache-recommended path and uses **different metric names** than Micrometer's built-in hc5 binder; choose one to avoid confusion.