---
title: "Micrometer with Spring Boot: Capability-Oriented Observability Guide"
category: "Observability"
description: "A capability-oriented reference to Micrometer as it actually ships with Spring Boot, organized by what the library can do rather than by a week-by-week schedule. The baseline is Micrometer 1.17 (June 2026) with maintenance lines 1.16 and 1.15, Spring Boot 4.0 GA shipping Micrometer 1.16 and Micrometer Tracing 1.6 on Spring Framework 7 / Jakarta EE 11, and Spring Boot 3.5 on roughly 1.15. It covers the meter hierarchy and its mapping onto Prometheus types, distribution statistics in depth (why client-side publishPercentiles cannot be aggregated across pods while percentile histograms can), the full catalog of Boot auto-configured metrics for JVM, HTTP, HikariCP, Kafka, caches, executors and Tomcat, custom instrumentation, the Observation API as one instrumentation point yielding metric plus span plus log with its low- vs high-cardinality tag split, Micrometer Tracing after Sleuth, exporters and backends including the Prometheus simpleclient 0.x to prometheus-metrics-core 1.x migration and Pushgateway lag, Kubernetes and EKS production concerns, cardinality hygiene, exemplars for metrics-to-trace pivots, and multi-window error-budget burn alerts, closing with recommendations, project ideas, and explicit version caveats."
---

# Micrometer with Spring Boot: A Capability-Oriented Guide for Senior Engineers

## TL;DR
- Micrometer is the "SLF4J for observability": a vendor-neutral metrics facade (plus the newer Observation API and Micrometer Tracing) that Spring Boot Actuator auto-wires. As of mid-2026, Micrometer 1.17.0 (released 8 June 2026) is current, with maintenance lines 1.16.x and 1.15.x. Spring Boot 3.5 manages roughly 1.15, and Spring Boot 4.0.0 (GA 20 November 2025) ships Micrometer 1.16 and Micrometer Tracing 1.6, built on Spring Framework 7 / Jakarta EE 11.
- The single most important modern concept is the Observation API, introduced in Micrometer 1.10: instrument once, emit metrics and traces (plus logs correlation) simultaneously. The docs describe it as "instrument once and have multiple benefits out of it," with an explicit split between low-cardinality data (metrics tags) and high-cardinality data (trace attributes). Spring Framework 6+/Boot 3+ moved native instrumentation (HTTP, Kafka, Redis, etc.) onto it and retired Spring Cloud Sleuth.
- For your Prometheus + Grafana + EKS + Kotlin stack, prefer server-side histograms (`publishPercentileHistogram`) over client-side percentiles so you can aggregate across pods with `histogram_quantile`, keep tag cardinality bounded (URI templating, common tags, no pod-name labels in-app), and wire exemplars end-to-end for metrics→trace pivots.

## Key findings
1. Micrometer's meter set (Counter, Gauge, Timer, LongTaskTimer, DistributionSummary, TimeGauge, FunctionCounter, FunctionTimer, MultiGauge) maps cleanly onto Prometheus types. The recurring pitfalls are gauge GC (weak references) and cardinality explosions.
2. Client-side percentiles (`publishPercentiles`) are not aggregable across dimensions or instances; percentile histograms are. This is decisive in a multi-pod Kubernetes deployment.
3. Spring Boot auto-configures a large catalog of metrics (JVM, system, HTTP server and client, HikariCP, Kafka clients, caches, executors, Tomcat, Logback/Log4j2, and more) once Actuator plus a registry are on the classpath.
4. The Prometheus registry migrated from the 0.x `simpleclient` to the 1.x `prometheus-metrics-core` client in Micrometer 1.13 / Spring Boot 3.3. The old client is deprecated, and Pushgateway support lagged behind on the 1.x client.
5. Spring Boot 4 renames observability modules (`spring-boot-micrometer-metrics/-observation/-tracing`), adds a `spring-boot-starter-opentelemetry`, removes `@AutoConfigureObservability`, and fixes coroutine and Reactor context propagation with `spring.reactor.context-propagation=auto`.

## Details

### 1. Architecture and core concepts

What Micrometer is. Micrometer provides an abstraction layer for metrics collection: an API for meter types (counters, gauges, timers, distribution summaries) plus a `MeterRegistry` API that generalizes collection and propagation to backends. It is explicitly positioned as "Think SLF4J, but for observability." Spring Boot Actuator auto-configures a `MeterRegistry` and binds a large set of instrumentation to it.

Registries.
- `SimpleMeterRegistry` holds the latest value of each meter in memory and exports nowhere. It is autowired in Spring apps as a fallback and is the workhorse for tests.
- `MeterRegistry` is the base abstraction, and exporters iterate over its meters to produce time series. Note that registering meters with the same ID multiple times keeps only the first registration.
- `CompositeMeterRegistry` fans out to multiple backends simultaneously. Spring Boot's injected `MeterRegistry` is in fact a composite.
- `Metrics.globalRegistry` is a static global composite with static builders (`Metrics.counter(...)`). In Spring apps, prefer injecting the `MeterRegistry` bean over the global static; the global is handy for library code or where DI is unavailable.

Meter types, and when to use each.
- Counter: a monotonic increasing count (requests, errors). In Prometheus you `rate()` it. Counters reset on restart, and Prometheus `rate()`/`increase()` handle resets.
- Gauge: an instantaneous, sampled value that "changes only when observed" (queue depth, cache size). Gauges hold a weak reference to the observed object so as not to prevent GC, so if the object is collected, the gauge reports `NaN`. Never hold the gauge value in a plain field you also mutate elsewhere without keeping a strong reference to the source object. Use gauges for values that can go up and down and that you can read on demand.
- Timer: short-duration events plus rate (latency). Records count, total time, and max.
- LongTaskTimer: measures the duration of in-flight long-running tasks, so you can see the currently-running time before completion. Good for batch jobs, scheduled tasks, and long polls.
- DistributionSummary: the distribution of non-time values (payload sizes, batch sizes).
- TimeGauge: a gauge whose value is a duration in a known time unit.
- FunctionCounter and FunctionTimer: "function-tracking" meters that derive a count or total from an external monotonic source, such as a third-party client's internal counters. Micrometer computes the deltas. Used heavily by binders (Kafka, HikariCP).
- MultiGauge: manages a set of gauges whose tag combinations change over time, such as per-status counts you recompute periodically, with `register(...)` replacing the previous set.

Naming. Use dot-separated, lowercase, hierarchical-looking names (`http.server.requests`). Micrometer's `NamingConvention` per registry translates these to the backend idiom (for Prometheus, `http_server_requests_seconds_...`, snake_case, base-unit suffixes). Prefer base units (seconds, bytes) and set them on the meter. Never register the same name with different tag key sets, since Prometheus strongly discourages inconsistent tag keys per name.

Tags and cardinality. Tags are dimensions, and the cartesian product of tag values is the number of time series. Guard against explosion with `MeterFilter`:
- `MeterFilter.deny(...)` / `accept(...)`, `denyNameStartsWith(...)`,
- `MeterFilter.maximumAllowableTags(...)` and `maximumAllowableMetrics(...)`,
- `MeterFilter.replaceTagValues(...)` to collapse high-cardinality values,
- and `renameTag`. There is also a `HighCardinalityTagsDetector` (docs added in the 1.16 line) to help find offenders at runtime.

`Meter.Id` is the (name, tags, base unit, type) tuple that identifies a meter. `MeterDocumentation` and `ObservationDocumentation` let you formally document meters and observations (names, tag keys) as enums, which is useful for governance across a microservice fleet.

### 2. Distribution statistics and percentiles (deep dive)

Two approaches:
- Percentile histograms (`publishPercentileHistogram()`): Micrometer accumulates into an underlying HdrHistogram and ships a preset set of cumulative buckets. Prometheus, Atlas, and Wavefront then compute percentiles server-side (`histogram_quantile` in Prometheus). These are aggregable across dimensions and across instances, so you sum bucket counts across pods and then take the quantile. This is what you want on EKS.
- Client-side percentiles (`publishPercentiles(0.5, 0.95, 0.99)`): Micrometer computes a percentile approximation per meter ID in-process and ships the value, as a gauge tagged `phi`/`quantile`. These cannot be aggregated across tags or instances, so averaging p99s across pods is statistically meaningless. Useful only where the backend can't do server-side quantiles.

When both are configured, the histogram is preferred (on OTLP, the Summary datapoint is treated as legacy).

Bucket math. For `publishPercentileHistogram`, buckets are preset by a generator empirically tuned by Netflix. Per the Micrometer docs (histogram-quantiles), verbatim: *"By default, the generator yields 276 buckets, but Micrometer includes only those that are within the range set by minimumExpectedValue and maximumExpectedValue, inclusive. Micrometer clamps timers by default to a range of 1 millisecond to 1 minute, yielding 73 histogram buckets per timer dimension."* Each bucket is a separate time series in Prometheus, so histograms are much more expensive than summaries. Tune the expected-value range to control both bucket count and the HdrHistogram memory footprint and accuracy.

SLOs. `serviceLevelObjectives(...)` publishes a cumulative histogram with buckets at your explicit SLO boundaries. Combined with `publishPercentileHistogram` it *adds* buckets; alone it publishes *only* those buckets. SLOs are based on recorded values, not percentiles, so `serviceLevelObjectives(Duration.ofMillis(100))` gives you a `le="0.1"` bucket you can turn into an SLO ratio.

Decay. `DistributionStatisticConfig` also controls `expiry` (default 2 min) and `bufferLength` (default 3): the client-side percentile and max statistics use a ring buffer of that many windows and decay over `expiry`, so a one-off spike ages out rather than pinning `max` forever.

Prometheus native histograms. These use exponential, sparse buckets for a compact, high-resolution representation. Support has been experimental and, historically, "not supported in Micrometer" per community write-ups. The newer Prometheus 1.x Java client and a `fstab/micrometer-registry-prometheus_native-example` demonstrate exposing native histograms (Protobuf exposition, viewable via `/actuator/prometheus?debug=prometheus-protobuf`). Treat native-histogram support as version-dependent and verify against your exact Micrometer and Boot versions before relying on it in production. When it works, it removes the fixed-bucket tradeoff and reduces series count dramatically.

Coordinated omission. When you correlate Micrometer server-side latency with k6 load tests, remember that Micrometer times only requests that actually reached the server and completed. Requests delayed because the system was stalled ("coordinated omission") are undercounted, so server-side p99 can look better than client-perceived p99. Trust k6's client-side latency, which sees queuing, for user-facing SLOs, and use Micrometer histograms for server-internal attribution. k6 also computes client-side percentiles per-instance, so the same non-aggregability caveat applies if you run distributed k6.

### 3. Auto-configured metrics in Spring Boot

With `spring-boot-starter-actuator` plus a registry (e.g. `micrometer-registry-prometheus`) and `management.endpoints.web.exposure.include=prometheus,health,metrics`, Spring Boot binds the following, non-exhaustively.

JVM, via `JvmMemoryMetrics`, `JvmGcMetrics`, `JvmThreadMetrics`, `ClassLoaderMetrics`, and JVM info:
- `jvm.memory.used/committed/max` (tags `area`=heap/nonheap, `id`=pool), `jvm.buffer.*`
- `jvm.gc.pause` (Timer), `jvm.gc.memory.allocated/promoted`, `jvm.gc.max.data.size`
- `jvm.threads.live/daemon/peak/states`, `jvm.classes.loaded/unloaded`
- Interpretation: a rising `jvm.gc.pause` sum or rate plus growing `jvm.memory.used{area="heap"}` after GC means heap pressure. Watch the old-gen pool `jvm.memory.used{id=~".*Old.*"}` trending toward `max`.

System and process, via `ProcessorMetrics`, `UptimeMetrics`, `FileDescriptorMetrics`:
- `system.cpu.usage`, `process.cpu.usage`, `system.load.average.1m`
- `process.uptime`, `process.start.time`, `process.files.open/max`
- `disk.free/total`

HTTP server, `http.server.requests` (a Timer; Spring MVC and WebFlux via `ServerHttpObservationFilter` and the Observation API). Tags: `method`, `uri` (the templated route, e.g. `/orders/{id}`), `status`, `outcome` (SUCCESS/CLIENT_ERROR/SERVER_ERROR), `exception`, `error`. Raw URIs cause cardinality explosion, so always use path templates. Unmatched routes report `uri="UNKNOWN"`, a known behavior change tightened in Boot 3.3 via `DefaultServerRequestObservationConvention`. Enable histograms with `management.metrics.distribution.percentiles-histogram.http.server.requests=true`.

HTTP client, `http.client.requests` for `RestTemplate`, `RestClient`, and `WebClient`, registered via observation customizers (`ObservationRestTemplateCustomizer`, `ObservationRestClientCustomizer`, `ObservationWebClientCustomizer`). URI templating is critical here: pass templates plus variables (`restClient.get().uri("/users/{id}", id)`, or `webClient...uri(b -> b.path("/v1/users/{id}").build(id))`) so the `uri` tag is the template, not the expanded URL. `management.metrics.web.client.max-uri-tags` (default 100) caps runaway URI tags. To always be sure, register a custom `ClientRequestObservationConvention` (Boot 3+).

Apache HttpClient 5 connection-pool metrics. Micrometer ships a built-in binder, `io.micrometer.core.instrument.binder.httpcomponents.hc5.PoolingHttpClientConnectionManagerMetricsBinder`, in `micrometer-core`. The `hc5` package is present in the micrometer-core 1.11.0 Javadoc, and the old HttpClient 4.x class in the parent `httpcomponents` package is deprecated as of 1.12.5 in favor of HttpComponents 5.x. It exposes gauges prefixed `httpcomponents.httpclient.pool`:

| Metric | Meaning |
|---|---|
| `httpcomponents.httpclient.pool.total.max` | max allowed persistent connections, all routes |
| `httpcomponents.httpclient.pool.total.connections` | connections in pool, tag `state`=available/leased |
| `httpcomponents.httpclient.pool.total.pending` | requests blocked awaiting a free connection |
| `httpcomponents.httpclient.pool.route.max.default` | default max connections per route |

All carry an `httpclient` tag (the pool name you pass) plus any custom tags. For per-request HttpClient 5 observations use `ObservationExecChainHandler`, registered as an exec interceptor named `"micrometer"`. `MicrometerHttpClientInterceptor` exists for `HttpAsyncClient`, and `MicrometerHttpRequestExecutor` is deprecated in favor of `ObservationExecChainHandler`. Kotlin wiring:

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

Spring Boot does not auto-register this pool binder, in 3.x or 4.x; it is manual. Note that Apache HttpClient 5.6+ now ships its own `httpclient5-observation` module, where the metric names differ (e.g. `http.client.pool.leased/available/pending`), and the Micrometer docs now flag the built-in hc5 instrumentation as deprecated in favor of that Apache module.

DataSource and HikariCP. With Actuator plus Micrometer on the classpath, HikariCP metrics are auto-bound: `hikaricp.connections` (total), `.active`, `.idle`, `.pending` (threads waiting), `.max`, `.min`, `.timeout` (count), `.acquire` (Timer), `.creation` (Timer), `.usage` (Timer). Plus generic `jdbc.connections.active/idle/max/min`. Interpretation: `hikaricp.connections.pending > 0` sustained means the pool is undersized for the load; rising `.acquire` p99 means contention; `.timeout` increments mean requests are failing to get a connection, so raise the pool size or fix slow queries. If you build a `HikariDataSource` manually, pass `new MicrometerMetricsTrackerFactory(registry)`. Aurora MySQL note: with a reader/writer split you typically run separate pools per endpoint, so tag them by `pool` name to make writer saturation distinguishable from reader. Aurora failover can invalidate connections, so also watch `.timeout` and `.creation` spikes around failover events. (No Aurora-specific Micrometer binder exists; these are the standard Hikari signals.)

JPA and Hibernate. `hibernate.*` statistics via `HibernateMetrics`, covering query counts, cache hits, and session stats, require `hibernate.generate_statistics=true`. Note that this instrumentation has been deprecated and removed from Spring Boot's auto-configuration in recent versions, moved out of the default path as Hibernate's own metrics and observation story evolved. `spring.data.repository.invocations` (a Repository-level Timer) remains useful.

Kafka. `KafkaClientMetrics` and `KafkaConsumerMetrics` (Micrometer) bind the native Kafka client metrics, and Spring Boot auto-exposes them from 2.5+ once Actuator is present. Key names, in dotted form: `kafka.consumer.fetch.manager.records.lag` (and `.records.lag.max`), `kafka.consumer.fetch.manager.fetch.latency.avg`, `kafka.consumer.coordinator.rebalance.rate.per.hour`, `kafka.consumer.last.poll.seconds.ago`, `kafka.producer.record.send.rate`, and the producer batch-size metrics. Also `spring.kafka.listener` (a listener Timer) and `spring.kafka.template`. Most important for lag monitoring: `records-lag-max` and per-partition `records.lag`. Caveat: some lag metrics historically lacked topic and partition tags depending on client state, and consumer-group lag is not a JVM metric, so use MSK CloudWatch or an offset exporter for authoritative group lag. For custom tags, add `MicrometerConsumerListener`/`MicrometerProducerListener` to the factory.

Caching. Caffeine (`CaffeineCacheMetrics`) and others bind `cache.gets` (tag `result`=hit/miss), `cache.puts`, `cache.evictions`, and `cache.size`. Hit ratio in PromQL: `sum(rate(cache_gets_total{result="hit"}[5m])) / sum(rate(cache_gets_total[5m]))`. For Redis and Valkey, per the Spring Boot 4.0 release notes: *"The Redis auto-configuration has been improved to auto-configure MicrometerTracing, rather than MicrometerCommandLatencyRecorder. The former operates on the Observation API and provides both metrics and spans."*

Task execution, scheduling, and executors. `executor.*` metrics come via `ExecutorServiceMetrics`: `executor.active`, `executor.completed`, `executor.pool.size/core/max`, `executor.queued`, `executor.queue.remaining`, plus `executor` (a task execution Timer) and `executor.idle` (a queue wait Timer) for `ThreadPoolExecutor`. Queue depth (`executor.queued`) climbing means pool saturation. For virtual threads (Loom), add `io.micrometer:micrometer-java21` for the virtual-thread binder. It measures the duration and count of virtual threads being pinned and counts failed starts and unparks, which is critical for spotting pinning regressions when you move blocking code onto virtual threads.

Web servers. `tomcat.sessions.*` and `tomcat.threads.*` for Tomcat; Jetty (`JettyServerThreadPoolMetrics`, `JettyStatisticsMetrics`); Netty and Reactor metrics for WebFlux. Spring Batch exposes `spring.batch.job` and `spring.batch.step` timers in recent versions.

Logging. `LogbackMetrics` → `logback.events` (tag `level`); `Log4j2Metrics` → `log4j2.events`. A rising `rate(logback_events_total{level="error"}[5m])` is a cheap error-rate signal.

Other. Spring Security (observation-based auth and filter-chain observations in recent versions), Spring Integration (`spring.integration.*` channel and handler timers), Spring GraphQL, and R2DBC pool metrics.

Configuration keys, and note the Boot 2 to 3 renames. Spring Boot 3 moved per-registry export properties from `management.metrics.export.<reg>.*` to top-level `management.<reg>.metrics.export.*` (e.g. `management.prometheus.metrics.export.enabled`). Common keys:
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
Spring Boot 4 changes: the observability modules were renamed (`spring-boot-metrics`→`spring-boot-micrometer-metrics`, `-observation`→`-micrometer-observation`, `-tracing`→`-micrometer-tracing`); a new `spring-boot-starter-opentelemetry` bundles most OTel and Micrometer deps; OTLP tracing export config moved under `management.opentelemetry.tracing.export.*` and `management.tracing.export.enabled`; and `logging.console.enabled` was added.

### 4. Custom instrumentation

Programmatic meters. Inject `MeterRegistry`, build meters with the fluent builders, and store the returned meter in a field to avoid per-call lookups:
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

MeterBinder. For metrics that depend on other beans, implement `MeterBinder` and register it as a `@Bean`. Spring Boot auto-calls `bindTo`, and this defers gauge registration until the registry is ready, which avoids the shutdown-ordering `NPE` and `BeanCreationNotAllowedException` you see when gauges reference beans being destroyed.

`@Timed` and `@Counted`. These require the aspect beans:
```kotlin
@Bean fun timedAspect(r: MeterRegistry) = TimedAspect(r)
@Bean fun countedAspect(r: MeterRegistry) = CountedAspect(r)
```
Limitations come from Spring AOP proxying: only public methods are instrumented, and self-invocation (calling the annotated method from within the same class) bypasses the proxy so no metric is recorded. Controllers are timed by default even without `TimedAspect`. Under native AspectJ compile-time weaving the aspect won't fire unless the Micrometer jar is post-compile woven. `longTask=true` switches to a `LongTaskTimer`.

Common tags via `MeterRegistryCustomizer`:
```kotlin
@Bean
fun commonTags(@Value("\${spring.application.name}") app: String) =
    MeterRegistryCustomizer<MeterRegistry> { r ->
        r.config().commonTags("application", app, "env", System.getenv("ENV") ?: "local")
    }
```
Use `MeterFilter` for renaming, denying, and limiting. Prefer injecting pod and region as *common tags* from the environment rather than per-meter.

Modeling business metrics dimensionally. Model outcomes as bounded low-cardinality tags (`result=success|declined|error`, `payment=card|bank`), never customer IDs or free text. Keep the meter name the noun (`payments`) and the tags the adjectives.

Testing. Use `SimpleMeterRegistry` in unit tests and assert with `micrometer-test`'s `MeterRegistryAssert` (`assertThat(registry).hasTimerWithNameAndTags(...)`). In Boot 4, `@AutoConfigureObservability` was removed in favor of the finer-grained `@AutoConfigureMetrics` and `@AutoConfigureTracing`, backed by `spring-boot-micrometer-metrics-test` and `-tracing-test`.

### 5. Micrometer Observation API

Introduced in Micrometer 1.10, the Observation API is the modern unified abstraction: you create one `Observation` and registered `ObservationHandler`s turn it into metrics, traces, logs, or anything else. The docs describe the goal as "instrument once and have multiple benefits out of it."

Components:
- `Observation` and `Observation.Context`, a mutable context holder carrying data for handlers.
- `ObservationRegistry`, which holds handlers, predicates, filters, and conventions.
- `ObservationHandler`, which reacts to lifecycle events (start, stop, scopes, error). `DefaultMeterObservationHandler` produces a Timer plus LongTaskTimer; a tracing handler produces spans. Compose them with `FirstMatchingCompositeObservationHandler`.
- `ObservationConvention`, which separates lifecycle from naming and tagging so names and key-values become configuration (override to rename or retag globally via `GlobalObservationConvention`).
- `ObservationPredicate`, to disable observations conditionally.
- `ObservationFilter`, to mutate or enrich contexts, for example by adding cloud tags.

```kotlin
Observation.createNotStarted("order.process", observationRegistry)
    .lowCardinalityKeyValue("channel", "web")      // becomes a metric tag
    .highCardinalityKeyValue("order.id", id)       // trace attribute only
    .observe { processOrder(id) }
```

Low vs high cardinality is a first-class distinction: low-cardinality key values become metric tags (bounded), while high-cardinality key values go only to traces (unbounded, e.g. IDs). This is exactly the discipline that prevents Prometheus series explosions while keeping rich trace context.

`@Observed`, with an `ObservedAspect` bean, instruments a method as an observation, yielding both a timer and, if tracing is on, a span. Boot 4 added support for `@ObservationKeyValue` to declaratively add key-values.

Migration reality. Spring Framework 6+/Boot 3+ moved native instrumentation onto the Observation API and retired Spring Cloud Sleuth, shifting responsibility for instrumentation to each component (Spring MVC/WebFlux, Spring Kafka, Spring Data Redis, etc.). Practically: you configure handlers and conventions once, and every instrumented component emits consistent metrics and spans.

Context propagation, which is critical for a Kotlin shop. `micrometer-context-propagation` is a zero-dependency SPI (`ThreadLocalAccessor`, `ContextAccessor`, `ContextRegistry`, `ContextSnapshot`) that bridges `ThreadLocal` ↔ Reactor Context ↔ coroutine context so trace and MDC context survive thread hops.
- Reactor: since Reactor 3.5 it embeds the SPI, and `Hooks.enableAutomaticContextPropagation()` enables automatic restoration. Automatic mode has real performance cost from ThreadLocal access in the pipeline, which is a documented tradeoff.
- Kotlin coroutines: this was a long-standing pain point (`kotlinx.coroutines` #4187, Spring Framework #32165). It is resolved in Spring Framework 7 / Spring Boot 4: set `spring.reactor.context-propagation=auto` and MDC and trace context propagate through `suspend` functions out of the box. Known remaining gotcha on Boot 4.0.x: context does not propagate into coroutines that collect a returned `Flow` (Spring Framework #36427), so MDC works in `suspend` controller methods but not inside Flow collectors, and exception-handler paths may lose context. For SLF4J MDC you also register `Slf4jThreadLocalAccessor`.
- Virtual threads: ThreadLocal-based propagation generally works, but pinning and per-carrier assumptions change, so verify traces are continuous when enabling virtual threads.

### 6. Micrometer Tracing

Micrometer Tracing is the successor to Spring Cloud Sleuth. It provides vendor-neutral `Tracer` and `Span` abstractions with bridges to OpenTelemetry (`micrometer-tracing-bridge-otel`) or OpenZipkin Brave (`micrometer-tracing-bridge-brave`). Boot 4 manages Micrometer Tracing 1.6.

Setup on Boot 3.x, with OTel and OTLP:
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
Boot 3 defaults to W3C `traceparent` and 128-bit IDs; switch or add B3 with `management.tracing.propagation.type=b3` (or `w3c,b3` for interop). Brave→Zipkin uses `spring-boot-starter-zipkin` plus `management.zipkin.tracing.endpoint`. Boot 4 note: the OTel→Zipkin auto-config is deprecated, since OpenTelemetry deprecated Zipkin support, and will be removed in Boot 4.2. Module names moved to `spring-boot-micrometer-tracing-opentelemetry` and friends, and Boot 4's `spring-boot-starter-opentelemetry` bundles the common path.

Correlating traces, metrics, and logs.
- Logs: Micrometer Tracing populates MDC `traceId` and `spanId`. Add them to your Logback pattern:
  ```
  logging.pattern.level=%5p [${spring.application.name},%X{traceId:-},%X{spanId:-}]
  ```
- Exemplars, the metrics→trace pivot in Grafana: with the 1.x Prometheus client you need a `SpanContext` bean (`io.prometheus.metrics.tracer.common.SpanContext`); with the deprecated simpleclient it was `SpanContextSupplier`. If you use Micrometer Tracing, Spring Boot auto-configures the exemplar provider. Exemplars require histogram buckets on the metric and the OpenMetrics exposition format, and only sampled traces become exemplars by default (`management.tracing.exemplars.include`). There is one exemplar per bucket per scrape, overwritten by later requests. Enable with:
  ```yaml
  management.metrics.distribution.percentiles-histogram.http.server.requests: true
  ```
  and ensure Grafana Alloy or Agent forwards exemplars (`send_exemplars`). Then Loki (logs by traceId) plus Tempo (traces) plus Prometheus (exemplars) give you a full LGTM pivot.

Micrometer Tracing versus the OpenTelemetry Java agent.
- Micrometer Tracing, the native path: instrumentation maintained by the Spring and library authors, one instrumentation yielding metrics plus traces, and it works with GraalVM native image, where agents can't be used. Metric names follow Micrometer and Spring conventions.
- The OTel Java agent (`-javaagent`): zero-code auto-instrumentation of many libraries, but it produces its own metric names, which can diverge from Micrometer and Spring dashboards, and running both can cause duplicate spans and metrics. The agent v2.x changed default behavior, with traces only on receive and send, and `@WithSpan` for manual spans.
- Recommendation: on Spring Boot, prefer Micrometer Tracing plus OTLP to a Collector. Use the OTel agent only for non-Spring libraries you can't instrument natively, and if you run both, disable overlapping instrumentation to avoid duplication.

### 7. Exporters and backends

Micrometer supports many registries: Prometheus, OTLP, Datadog, New Relic, CloudWatch, Dynatrace, Graphite, InfluxDB/Telegraf, SignalFx, Stackdriver, Wavefront, Atlas, StatsD, JMX, and more. Add the matching `micrometer-registry-*` and the composite fans out.

Prometheus (pull). Add `micrometer-registry-prometheus` and expose `/actuator/prometheus`. Scrape config:
```yaml
scrape_configs:
  - job_name: spring
    metrics_path: /actuator/prometheus
    static_configs: [{ targets: ["HOST:PORT"] }]
```
`registry.scrape("application/openmetrics-text")`, or the Actuator endpoint's content negotiation, gives you OpenMetrics for exemplars.

The Prometheus client migration. Micrometer 1.13 / Spring Boot 3.3 switched `micrometer-registry-prometheus` from the 0.x `simpleclient` to the 1.x `prometheus-metrics` (`prometheus-metrics-core`) client. Consequences:
- Some exported metric names changed, and there were behavioral differences.
- Pushgateway was not supported on the 1.x client initially.
- The old client remains available as `micrometer-registry-prometheus-simpleclient`, deprecated, with auto-config removed in Spring Boot 3.5.
- Don't override Micrometer's managed version. Forcing 1.13 on Boot 3.2, for example, breaks Prometheus auto-config, so let the Boot BOM manage it. The OpenRewrite recipe `UpgradeMicrometer_1_13` automates the package move `io.micrometer.prometheus`→`io.micrometer.prometheusmetrics`. Micrometer 1.16 upgraded the client to 1.4.x, bringing Unicode support with naming-convention behavioral changes (see the 1.16 migration guide).

OTLP. `micrometer-registry-otlp` pushes via OTLP, configured through `management.otlp.metrics.export.*` (url, step, headers). OTLP prefers Histogram and Exponential-Histogram datapoints, and the Summary datapoint (client percentiles) is legacy. Boot 4's `spring-boot-starter-opentelemetry` streamlines this.

Push vs pull, and step registries. Push registries extend `PushMeterRegistry`/`StepMeterRegistry`. Step registries normalize counts and sums to a rate over the publishing interval (the step), which is why a counter "looks different" on a step registry (Datadog, OTLP-step, etc.) than on Prometheus: within a step the value accumulates and is reported per-interval. For short-lived and batch jobs, step registries have a "last value" problem, where the final partial step may not be published on shutdown. Micrometer added partial-step-on-shutdown handling, but verify it.

Pushgateway for batch (Spring Batch). When the Pushgateway dependency is present, Spring Boot auto-configures a `PrometheusPushGatewayManager`, tunable via `management.prometheus.metrics.export.pushgateway.*`. Use it for jobs too short-lived to scrape. Caveat: Pushgateway support depends on the Prometheus client version, and it was unsupported on the early 1.x client, so pin accordingly.

AWS and EKS. `micrometer-registry-cloudwatch` pushes to CloudWatch, which costs per custom metric, so mind cardinality × dimensions. On EKS most teams prefer Prometheus scraping (or OTLP → Collector → AMP/Grafana Cloud) over CloudWatch for high-cardinality app metrics, using CloudWatch mainly for infra and MSK metrics like consumer-group lag.

### 8. Kubernetes and production concerns (EKS)

- Pod labeling and cardinality. Do not put pod name or IP as a Micrometer tag in-app, because that multiplies every series by pod churn. Let Prometheus or ServiceMonitor relabeling attach `pod`, `namespace`, and `instance` at scrape time. In-app common tags should be low-churn: `application`, `env`, `region`, maybe `version`.
- Aggregating percentiles across pods. You must use histograms and aggregate before you quantize: `histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))`. Never average per-pod client-side p99s.
- Scrape config. Use the Prometheus Operator `PodMonitor`/`ServiceMonitor` pointing at `/actuator/prometheus`, or Grafana Alloy scraping the Actuator endpoint (and enable `send_exemplars` and remote_write with exemplars for Tempo pivots).
- Endpoint exposure and security. Run Actuator on a separate management port (`management.server.port`) that isn't exposed publicly, restrict `management.endpoints.web.exposure.include` to what you scrape, and secure `/actuator/prometheus` via network policy or authn. Don't expose `env` or `heapdump`.
- Overhead. Each unique (name × tag-values) is a time series with memory cost in both the app and Prometheus. Client-side percentiles and histograms add per-meter HdrHistogram memory, bounded by min and max expected values, and histograms add many bucket series. Measure with the `/actuator/metrics` meter count, `prometheus_tsdb_head_series` on the Prometheus side, and the JVM heap of the app. A `HighCardinalityTagsDetector` helps catch offenders.
- Anti-patterns and troubleshooting.
  - *Missing metrics*: the registry dependency is absent, the endpoint isn't exposed, or a binder needs a classpath lib.
  - *Duplicated meters or `Collector already registered`*: the same name registered twice, for example `@Timed` colliding with a manual timer.
  - *Timers with zero counts or NaN percentiles*: client-side percentiles with no histogram, or a gauge target that was GC'd.
  - *Unbounded tags*: raw URIs, path variables, user input, or exception messages as tags. This is the #1 cause of Prometheus OOM.

### 9. Version and ecosystem currency (mid-2026)

- Micrometer: the current line is 1.17.x, with 1.17.0 released 8 June 2026 (Maven Central lists all `io.micrometer` modules with a last release of Jun 8, 2026; see the GitHub "Release 1.17.0" and the 1.17 migration guide). There is LTS-ish maintenance on 1.15 and 1.16. 1.13 brought the Prometheus 1.x client migration; 1.16 brought Prometheus client 1.4.x plus Unicode naming changes; and `micrometer-java11` and `micrometer-java21` split out the HTTP-client and virtual-thread binders respectively.
- Micrometer Tracing: the 1.5.x and 1.6.x lines, with Boot 4 managing 1.6.
- Spring Boot 3.x vs 4.x: Boot 4.0.0 (GA 20 November 2025) is built on Spring Framework 7 / Jakarta EE 11, manages Micrometer 1.16 and Tracing 1.6, renames the observability modules, adds `spring-boot-starter-opentelemetry`, removes `@AutoConfigureObservability`, improves Redis observability (Observation-based) and coroutine context propagation (`spring.reactor.context-propagation=auto`), and moves the OTLP tracing export props under `management.opentelemetry.tracing.export.*`. Zipkin-over-OTel auto-config is deprecated, with removal in 4.2.
- Deprecations to watch: `micrometer-registry-prometheus-simpleclient` (deprecated), the old `httpcomponents` (hc4) binders, `MicrometerHttpRequestExecutor`, Hibernate metrics auto-config, and Sleuth (gone).
- Community resources: the official docs (`docs.micrometer.io`, `docs.spring.io/spring-boot/reference/actuator`), the Micrometer and Spring Boot GitHub wikis and release notes, the Spring blog posts "Observability with Spring Boot 3" and "Let's use OpenTelemetry with Spring" (2024), and talks and posts by Tommy Ludwig (@shakuzen), Jonatan Ivanov, and Marcin Grzejszczak. In Korean, search Korean tech blogs (e.g. the Woowahan/우아한형제들 tech blog, Kakao, Naver D2) for "Micrometer 관측 가능성/옵저버빌리티" write-ups. Several good Spring Boot 3 observability posts exist, though verify version currency.

### 10. Practical learning path and project ideas

Progression for Kotlin, Boot, Kafka, Aurora, and EKS:
1. Basics: add Actuator plus `micrometer-registry-prometheus`, expose `/actuator/prometheus`, explore the auto-config metrics, and build a Grafana RED dashboard from `http.server.requests`.
2. Custom meters: instrument an order service with an `orders.placed` counter (tags: channel, result), an order-processing `Timer` with `publishPercentileHistogram`, and a MultiGauge of orders-by-status. Add `@Timed` plus `TimedAspect`.
3. DB and pool: enable HikariCP metrics for the Aurora writer and reader pools, alert on `hikaricp.connections.pending`, and wire the Apache HttpClient 5 pool binder for an outbound client.
4. Kafka: expose consumer lag (`kafka.consumer.fetch.manager.records.lag.max`) and producer send-rate, then alert on lag.
5. Distribution stats: add SLO buckets to a critical timer, compute an Apdex or SLO ratio in PromQL, and validate p99 against a k6 run (noting coordinated omission).
6. Observation API: convert a business flow to `@Observed`, add a custom `ObservationConvention` to rename and retag, and verify the low/high cardinality split.
7. Tracing plus exemplars: add `micrometer-tracing-bridge-otel` and OTLP to a Collector → Tempo, put `traceId` in logs → Loki, enable exemplars end-to-end, and pivot metric→trace in Grafana.
8. EKS production: ServiceMonitor or Alloy scrape, common tags, cross-pod `histogram_quantile`, SLO burn-rate alerts, and a separate management port.

Essential PromQL panels.
- RED, rate: `sum(rate(http_server_requests_seconds_count[5m]))`
- RED, errors: `sum(rate(http_server_requests_seconds_count{outcome="SERVER_ERROR"}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))`
- RED, duration p99 across pods: `histogram_quantile(0.99, sum by (le,uri) (rate(http_server_requests_seconds_bucket[5m])))`
- USE, CPU: `system_cpu_usage`, `process_cpu_usage`
- USE, saturation (pool): `hikaricp_connections_pending`, `executor_queued`
- JVM: `sum by (id) (jvm_memory_used_bytes{area="heap"})`, `rate(jvm_gc_pause_seconds_sum[5m])`
- Kafka lag: `max by (topic) (kafka_consumer_fetch_manager_records_lag_max)`
- Error budget burn (multi-window): the fast window is `(1 - sum(rate(http_server_requests_seconds_bucket{le="0.3",outcome="SUCCESS"}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))) > (14.4 * (1 - 0.99))`, combined with a 1h window for the classic multi-burn-rate SLO alert.

## Recommendations
1. Standardize on server-side histograms for latency SLIs (`management.metrics.distribution.percentiles-histogram.http.server.requests=true` plus explicit `slo` buckets). Only use client-side `percentiles` for single-instance local debugging. Threshold to change: if Prometheus head series from a service exceeds a few hundred thousand, trim buckets via `minimum`/`maximumExpectedValue` or drop unneeded SLO buckets.
2. Adopt the Observation API plus Micrometer Tracing plus OTLP→Collector as the default. Avoid the OTel Java agent on Spring services unless you're instrumenting non-Spring libs, and never run both without disabling overlaps. Wire exemplars now, since you already run Grafana and Tempo.
3. Enforce cardinality hygiene: URI templating everywhere, `MeterFilter.maximumAllowableTags`, common tags injected from env (no pod names in-app), and a periodic `HighCardinalityTagsDetector` and series-count review. Trigger to act: any new `uri="UNKNOWN"` surge, or the `max-uri-tags` cap being hit.
4. On the Boot 4 migration, update module names, adopt `spring-boot-starter-opentelemetry`, set `spring.reactor.context-propagation=auto` for coroutines, and replace `@AutoConfigureObservability` with `@AutoConfigureMetrics`/`@AutoConfigureTracing` in tests. Validate coroutine and `Flow` MDC propagation given the open Boot 4.0.x Flow gap.
5. For batch and Spring Batch, use Pushgateway (pinning a Prometheus client version that supports it) rather than relying on scrapes of short-lived pods.

## Caveats
- Several specifics are version-dependent: property names (Boot 2 vs 3 vs 4), the Prometheus client 0.x→1.x metric-name changes, native-histogram support, and the exact micrometer-core version that introduced the hc5 binder (evidence points to 1.11.0; confirm against the release notes). Verify against your exact Micrometer and Boot versions.
- Prometheus native histograms in Micrometer have moved between "experimental/unsupported" and demo-level support, so do not assume production readiness without testing your versions.
- Coroutine and Reactor context propagation works in Boot 4 with `spring.reactor.context-propagation=auto`, but there is an open issue (Spring Framework #36427) where MDC and trace context are not propagated into coroutines collecting a returned `Flow`, and exception-handler paths can lose context.
- Consumer-group lag from Kafka client JVM metrics is per-consumer, not authoritative group lag. For group-level lag use MSK CloudWatch metrics or an offset-based exporter.
- Some figures (bucket counts, defaults like 276 buckets and 73 timer buckets, expiry=2min, bufferLength=3) are Micrometer defaults that can change across versions and are overridable.
- The Apache `httpclient5-observation` module (HttpClient 5.6+) is now the Apache-recommended path and uses different metric names than Micrometer's built-in hc5 binder, so choose one to avoid confusion.
