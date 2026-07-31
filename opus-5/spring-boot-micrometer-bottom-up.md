---
title: "Spring Boot 4 + Micrometer: Bottom-Up Observability (Application Layer)"
category: "Observability"
description: "A 14 to 18 week, seven-phase curriculum that instruments a Spring Boot 4.1 / Kotlin app end-to-end first, then descends into Micrometer library internals rather than stopping at properties copied from a blog post. The baseline is Spring Boot 4.0/4.1, Micrometer 1.16 to 1.17, Micrometer Tracing 1.5/1.6, and Java 21+, a version landscape where Boot 4's modularization of spring-boot-autoconfigure across 70+ modules and the split property namespaces (metrics stay on management.otlp.metrics.*, tracing and logging move to management.opentelemetry.*) invalidate the module names in nearly every Boot 3.x tutorial. It covers the registry model, MeterFilter and MeterBinder, naming and tag discipline, gauges done right, distribution-statistics internals (why client-side percentiles cannot be aggregated across pods, and why Micrometer still does not emit Prometheus native histograms), OTLP histogram flavors and temporality, the Prometheus client 1.x default as a real breaking change, the Observation API as one instrumentation point yielding metric plus span plus log, context propagation across coroutines, Kafka and virtual threads where distributed tracing actually breaks, and reading the Micrometer source, ending in a two-week capstone."
---

# A Bottom-Up Learning Plan: Spring Boot 4 + Micrometer 1.16/1.17 Observability (Application Layer)

## TL;DR
- This is a 14 to 18 week, seven-phase curriculum. It starts with instrumenting a Spring Boot 4.1 / Kotlin app end-to-end (Phases 0 to 2), then descends into Micrometer library internals, covering the registry model, MeterFilter/MeterBinder, distribution statistics, the Observation API, context propagation, tracing, and reading the source (Phases 3 to 6), and ends in a capstone. Target versions: Spring Boot 4.0/4.1 (4.0 GA'd Nov 20, 2025; 4.1.0 published to Maven Central June 10, 2026), Micrometer 1.16 to 1.17 (1.17.0 released June 8, 2026), Micrometer Tracing 1.5/1.6, Java 21+.
- The single biggest version trap: Spring Boot 4 delivered a full modularization of `spring-boot-autoconfigure` across 70+ focused modules, added a first-party `spring-boot-starter-opentelemetry`, and split property namespaces. Metrics keep `management.otlp.metrics.*` (Micrometer OTLP registry) but tracing and logging moved to `management.opentelemetry.*` (OTel SDK). Nearly all Boot 3.x tutorials get the module names and some properties wrong, while the concepts (meters, Observation API, MeterFilter) remain valid.
- Bottom line for this engineer: skip Spring Boot basics; treat Micrometer as "SLF4J for metrics/observability" and learn it the way you'd learn a library, from its type hierarchy and source. The highest-leverage deep dives are the Observation API (one instrumentation point → metric + span + log), context propagation across coroutines, Kafka and virtual threads, and distribution-statistics internals (why client-side percentiles don't aggregate).

## Key findings

### The version landscape (verify everything against these)
- Spring Boot 4.0 GA shipped November 20, 2025, and Phil Webb's announcement describes it as "a complete modularization of the Spring Boot codebase providing smaller and more focused jars." Spring Boot 4.1.0 was published to Maven Central on June 10, 2026 (the latest 4.0 patch is 4.0.7, also June 10, 2026). The 3.x line is legacy: the final 3.x patch was 3.5.16 on June 25, 2026, ending OSS support.
- Micrometer 1.16.0 shipped alongside Boot 4, announced in Moritz Halbritter's Nov 18, 2025 "OpenTelemetry with Spring Boot" post. Micrometer 1.17.0, released June 8, 2026, is the current stable line. The BOM is managed by Spring Boot, so you rarely pin versions yourself.
- `spring-boot-starter-opentelemetry` is new in Boot 4: one dependency pulls the OTel API and SDK, `micrometer-registry-otlp` (metrics), and `micrometer-tracing-bridge-otel` (traces). It exists *because* of modularization, since you can now export metrics and traces without the full Actuator. Boot 4.0.1 fixed log export so it no longer requires Actuator, so use 4.0.1+.
- Module restructuring, which is the trap: autoconfig now lives under `org.springframework.boot.<module>.*`. Metrics autoconfig is `org.springframework.boot.micrometer.metrics.autoconfigure.*`; OTel is in `spring-boot-opentelemetry` and `spring-boot-micrometer-tracing-opentelemetry`. "Classic Starter POMs" preserve the old fat-starter behavior for migration.
- The property split, worth memorizing: metrics use `management.otlp.metrics.export.url` (Micrometer's OtlpMeterRegistry); traces use `management.opentelemetry.tracing.export.otlp.endpoint`; logs use `management.opentelemetry.logging.export.otlp.endpoint`. The different prefixes reflect which library integrates each signal, with metrics via Micrometer and traces and logs via the OTel SDK. Prometheus scrape stays at `/actuator/prometheus`.

### Micrometer's position and the OTel relationship
Micrometer is a vendor-neutral facade ("think SLF4J, but for observability") with built-in registries for Prometheus, OTLP, Atlas, CloudWatch, Datadog, Dynatrace, Wavefront, StatsD, and more. Spring's own instrumentation is written against the Micrometer Observation API, not the OTel API. The Spring team's guidance is to instrument with Micrometer and export via OTLP, because "it's the protocol that matters, not the library." Spring Boot does not auto-configure an OTel `SdkMeterProvider`; metrics always flow through Micrometer. If both Micrometer's OTLP registry and an OTel bridge are active you get duplicate metrics, so disable one with `management.otlp.metrics.export.enabled=false`.

### Prometheus client 1.x is now the default (a real breaking change)
Since Micrometer 1.13, `micrometer-registry-prometheus` is built on the Prometheus Java client 1.x (client_java), not the legacy `simpleclient` 0.x. The old path survives as the deprecated `micrometer-registry-prometheus-simpleclient`, which is interim only. Micrometer 1.16 upgraded the client to 1.4.x, confirmed in the 1.16.0 release notes: "We upgraded the Prometheus Java Client to 1.4.x (#6830) which brings support for Unicode which includes some behavioral change in naming conventions, see the 1.16 Migration-Guide." Counters now use longs and some metric names changed, so dashboards and alerts can break on upgrade.

### Distribution statistics internals (the part most people get wrong)
From the current source, `DistributionStatisticConfig.DEFAULT` is `percentilesHistogram(false)`, `percentilePrecision(1)`, `minimumExpectedValue(1.0)`, `maximumExpectedValue(Double.POSITIVE_INFINITY)`, `expiry(Duration.ofMinutes(2))`, `bufferLength(3)`. So statistics live in a ring buffer of 3 histograms rotating every 2 minutes, with full decay after 6 minutes.
- `TimeWindowPercentileHistogram` uses HdrHistogram (`DoubleRecorder`/`DoubleHistogram`) internally and backs client-side percentiles (`percentiles(...)`). These are computed per-instance and cannot be aggregated across instances, so averaging p99s across pods is statistically meaningless.
- `TimeWindowFixedBoundaryHistogram` uses fixed bucket boundaries (no HdrHistogram, smaller footprint) and backs percentile histograms and SLO buckets (`publishPercentileHistogram`, `serviceLevelObjectives`). These ship buckets that the backend aggregates (`histogram_quantile` in Prometheus), which is the aggregable, cross-pod-correct approach.
- Bucket generation: the preset generator yields ~276 buckets, and Micrometer ships only those within `[minimumExpectedValue, maximumExpectedValue]`. A Timer clamped to the default 1 ms to 1 min yields ~73 buckets per dimension. `percentilePrecision` (default 1) sets HdrHistogram precision, so higher precision means more memory. Each bucket is a separate backend time series, so buckets × dimensions drives cardinality and cost.

### Prometheus native histograms: not emitted by Micrometer (as of 1.16/1.17)
The underlying Prometheus client 1.x supports native histograms, but Micrometer's Prometheus registry does not wire them through. It emits classic fixed-bucket histograms, summaries, and GaugeHistograms only. Native support exists only on an unmerged feature branch. Native-histogram support for the Micrometer Prometheus registry is tracked as an open maintainer enhancement (candidate issue #5891, though you should verify the exact issue number and title before citing it, as the attribution is uncertain). The practical implication: if you want exponential or native-style histograms today, use the OTLP registry's exponential (base-2) histogram flavor, not the Prometheus registry.

### OTLP registry histogram flavors and temporality
`OtlpMeterRegistry` (config `OtlpConfig`) supports two histogram flavors when `publishPercentileHistogram` is set, explicit-bucket and base-2 exponential, selected via `histogramFlavor` / `histogramFlavorPerMeter`. Exponential adds `maxScale` (default 20), `maxBuckets` (default 160), and `maxBucketsPerMeter`. Because exponential histograms cannot carry custom SLOs, configuring `serviceLevelObjectives` forces a fallback to explicit-bucket histograms. OTLP also has aggregation temporality, DELTA vs CUMULATIVE, which must match your backend's expectation: Prometheus-style backends generally want cumulative, while many OTel pipelines prefer delta. `publishMaxGaugeForHistograms` (since 1.17) defaults based on temporality.

### The Observation API (the conceptual core)
An `Observation` is a single instrumentation point that, through registered `ObservationHandler`s, becomes both a metric and a span, and can enrich logs. The lifecycle callbacks on the handler are `onStart`, `onScopeOpened`, `onScopeClosed`, `onEvent`, `onError`, `onStop`, plus `supportsContext`. Key pieces: `ObservationRegistry`, `ObservationHandler`, `ObservationPredicate` (should this observation be created?), `ObservationFilter` (mutate context before stop), `ObservationConvention`/`GlobalObservationConvention` (naming and tags as configuration), and typed `Observation.Context`. `lowCardinalityKeyValues` become metric tags *and* span attributes; `highCardinalityKeyValues` become span attributes only, never metric tags, which is the cardinality firewall. `DefaultMeterObservationHandler` creates the timer or counter; the tracing handlers create spans.

### Context propagation is where distributed tracing breaks
`micrometer-context-propagation` (zero-dependency) defines `ThreadLocalAccessor`, `ContextRegistry`, `ContextSnapshot`, and the one that matters most here, `ObservationThreadLocalAccessor` (`KEY = "micrometer.observation"`). Failure modes and fixes:
- `@Async` and `AsyncTaskExecutor`: context is lost across threads. Fix it by registering a `ContextPropagatingTaskDecorator` bean, since Boot auto-installs `TaskDecorator` beans into the executor.
- Kotlin coroutines: Micrometer ships `ObservationRegistry.asContextElement()` (in `micrometer-core`'s Kotlin source, since 1.10) and `CoroutineContext.currentObservation()`. Spring Framework 7 adds first-party coroutine context propagation (spring-framework #35185). For MDC specifically, use `MDCContext` from `kotlinx-coroutines-slf4j`. Known gap: propagation into `Flow`-returning endpoints was still buggy on Boot 4.0.3 (spring-framework #36427).
- Reactor: use `Hooks.enableAutomaticContextPropagation()` (or `spring.reactor.context-propagation=auto`) plus `.tap(Micrometer.observation(registry))` / `contextWrite(ObservationThreadLocalAccessor.KEY, ...)`.
- Virtual threads and Kafka listeners: wrap executors with `ContextExecutorService`/`ContextSnapshotFactory::captureAll`, and for Kafka set observation-enabled (below).

### Micrometer Tracing (post-Sleuth)
Spring Cloud Sleuth was absorbed into Micrometer Tracing in Boot 3 and remains the model in Boot 4. Pick one bridge: `micrometer-tracing-bridge-otel` (OTel/OTLP, the Spring team's default recommendation for Boot 4) or `micrometer-tracing-bridge-brave` (Brave/Zipkin). Default propagation is W3C `traceparent` with 128-bit IDs; B3 is available. With B3, baggage is not auto-propagated, so use `management.tracing.baggage.remote-fields`. Boot adds trace and span IDs to the log pattern via MDC by default. The golden rule: never `new` a `RestClient`/`WebClient`/`RestTemplate`. Inject the auto-configured builder or context won't propagate.

### Virtual thread metrics (Java 21+)
`micrometer-java21` provides `VirtualThreadMetrics` (`io.micrometer.java21.instrument.binder.jdk`, author Artyom Gabeev, since 1.14). It is JFR-based, listening to `jdk.VirtualThreadPinned` and `jdk.VirtualThreadSubmitFailed`. Per Oracle's Java documentation, `jdk.VirtualThreadPinned` "indicates that a virtual thread was pinned... This event is enabled by default with a threshold of 20 ms." It exposes pinned-duration timers and submit-failed counts. Spring Boot auto-configures it (spring-boot #43852/#43122, from Boot 3.5). Limitation: it is JFR event-driven, so it measures pinning and submit-failure events, not a full live-thread census. Per Micrometer's JVM Metrics reference, richer mounted/queued/parallelism gauges are only added "If you are running your application with Java 24 or later on a JVM that has jdk.management.VirtualThreadSchedulerMXBean provided as a platform MXBean."

## Details: the phased plan

Each phase lists a time budget, a concrete deliverable that builds on the prior one, and named primary-source resources. The running project is an event-driven "orders" microservice (Kotlin, Spring Boot 4.1, Aurora MySQL/HikariCP, Kafka, EKS) so every phase instruments something real from your stack.

---

### Phase 0: Framing and the version map (½ week)
**Goal:** internalize where Micrometer sits, why a facade, and exactly what changed in Boot 4.

Read/watch:
- Spring blog, Moritz Halbritter, "OpenTelemetry with Spring Boot" (Nov 18, 2025): https://spring.io/blog/2025/11/18/opentelemetry-with-spring-boot/
- Spring blog, "Modularizing Spring Boot" (Oct 28, 2025): https://spring.io/blog/2025/10/28/modularizing-spring-boot/
- Micrometer docs home and Concepts: https://docs.micrometer.io/micrometer/reference/ and https://docs.micrometer.io/micrometer/reference/concepts
- The original framing, Spring blog "Observability with Spring Boot 3" (Oct 12, 2022), conceptually still valid: https://spring.io/blog/2022/10/12/observability-with-spring-boot-3/
- Talk: "Micrometer Mastery: Unleash Advanced Observability in your JVM Apps," Tommy Ludwig and Jonatan Ivanov, Spring I/O 2024: https://www.youtube.com/watch?v=Qyku6cR6ADY (slides: https://speakerdeck.com/jonatan_ivanov/2024-05-31-spring-io-micrometer-mastery-unleash-advanced-observability-in-your-jvm-apps)

**Deliverable:** a one-page Korean-blog-ready cheat sheet mapping Boot 3.x property and module names to their Boot 4 equivalents (`management.otlp.metrics.*` vs `management.opentelemetry.*`, old `spring-boot-actuator-autoconfigure` → new `org.springframework.boot.micrometer.metrics.autoconfigure.*`), with a decision note on Micrometer API plus OTLP export versus the OTel API or agent, and when each applies.

---

### Phase 1: End-to-end quick tour (1 week)
**Goal:** get every signal out of a Boot 4 Kotlin app by hand and read the raw output.

Do:
1. Generate a Boot 4.1 Kotlin project on start.spring.io with Actuator, "OpenTelemetry", and Web. Run the Grafana `otel-lgtm` container via `spring-boot-docker-compose`.
2. Compare two export paths: (a) `micrometer-registry-prometheus` scraped at `/actuator/prometheus`; (b) `micrometer-registry-otlp` pushing to `:4318/v1/metrics`. Curl both, then diff the representations.
3. Expose endpoints (`management.endpoints.web.exposure.include`), set a management port, and verify by hand.

Resources (primary):
- Spring Boot reference, Metrics: https://docs.spring.io/spring-boot/reference/actuator/metrics.html
- Spring Boot reference, Observability: https://docs.spring.io/spring-boot/reference/actuator/observability.html
- Micrometer OTLP registry: https://docs.micrometer.io/micrometer/reference/implementations/otlp.html
- Micrometer Prometheus registry: https://docs.micrometer.io/micrometer/reference/implementations/prometheus.html
- Sample to clone, Moritz Halbritter's `spring-boot-and-opentelemetry`: https://github.com/mhalbritter/spring-boot-and-opentelemetry
- Thomas Vitale's `spring-boot-opentelemetry` (resource-attributes, OTLP nuances): https://github.com/ThomasVitale/spring-boot-opentelemetry

**Deliverable:** the orders service emitting metrics, traces, and logs to local LGTM, with a README documenting each property and the hand-verified `/actuator/prometheus` name translation (e.g. `http.server.requests` → `http_server_requests_seconds_count`).

---

### Phase 2: Auto-configured meters plus first custom instrumentation (1.5 weeks)
**Goal:** know every free meter, where it comes from, and write your own.

Study the free meters and their autoconfig: `http.server.requests`, `http.client.requests`, `jvm.*` (memory, GC, threads, classloader, buffer pools), `system.*`/`process.*`, `tomcat.*`, `hikaricp.*`, `spring.data.repository.invocations`, Kafka client metrics, `executor.*`, cache metrics, `spring.batch.*`. Find each provider under `org.springframework.boot.micrometer.metrics.autoconfigure.*` (Boot 4.1 API: https://docs.spring.io/spring-boot/api/java/allpackages-index.html) and practice selectively disabling with `MeterFilter.denyNameStartsWith("jvm")`.

Write custom instrumentation covering all meter types: `Counter`, `Gauge`, `Timer`, `DistributionSummary`, `LongTaskTimer`, `TimeGauge`, `FunctionCounter`, `FunctionTimer`. Then the annotations `@Timed`, `@Counted`, `@Observed`, `@NewSpan`, `@SpanTag`, noting that they require `management.observations.annotations.enabled=true` plus the aspect beans (`TimedAspect`, `CountedAspect`, `ObservedAspect`) and AspectJ.

Kotlin ergonomics: use `Timer.record { }` (an inline lambda) and extension functions to wrap `MeterRegistry`. Note that `@Observed` and AOP require Spring-proxied beans, so self-invocation and `private`/`final` methods won't be intercepted. That's a real Kotlin gotcha, since Kotlin classes and methods are `final` by default; use the `all-open`/`kotlin-spring` plugin.

Resources:
- Micrometer Concepts (meter types): https://docs.micrometer.io/micrometer/reference/concepts
- Gauges, worth reading closely for the Phase-2 pitfalls: https://docs.micrometer.io/micrometer/reference/concepts/gauges.html
- Naming: https://docs.micrometer.io/micrometer/reference/concepts/naming.html

**Deliverable:** add a business `Counter` (orders placed), a `Gauge` (outbox backlog depth), and a `Timer` (order-processing latency) with idiomatic Kotlin wrappers; disable JVM buffer-pool metrics via MeterFilter and prove it in `/actuator/prometheus`.

---

### Phase 3: Naming, tags, gauges done right, and testing (1.5 weeks)
**Goal:** cardinality discipline plus a test harness you'll reuse all curriculum long.

Naming and tags: dot-delimited names, base units, the per-registry `NamingConvention` (why `http.server.requests` becomes `http_server_requests_seconds_count` in Prometheus), `MeterRegistryCustomizer` for common tags, and low- vs high-cardinality thinking.

Gauge pitfalls, which are critical: Micrometer holds a weak reference to the gauged object to avoid leaks, so if the object is GC'd the gauge reports `NaN` or vanishes. You cannot "set" a gauge, which is the "heisen-gauge" principle. Hold a strong reference to an `AtomicInteger`/`AtomicLong` or domain object, or use `Gauge.builder(...).strongReference(true)`. (`DiskSpaceMetrics` historically hit this, issue #1409.)

Testing:
- `SimpleMeterRegistry` for pure unit tests, with `meterRegistry.clear()` between tests.
- `micrometer-test` → `MeterRegistryAssert`; `micrometer-observation-test` → `TestObservationRegistry` + `TestObservationRegistryAssert`.
- Spring test slices plus `@AutoConfigureObservability`, since observability autoconfig is off in tests by default and needs re-enabling.
- Testcontainers with Podman (your stack): spin up an OTLP collector or Prometheus and assert end-to-end.

Resources:
- Meter filters: https://docs.micrometer.io/micrometer/reference/concepts/meter-filters.html
- Gauge NaN root cause (Baeldung): https://www.baeldung.com/java-prometheus-micrometer-gauge-nan-value
- Testing (Baeldung "Observability With Spring Boot"): https://www.baeldung.com/spring-boot-3-observability and https://www.baeldung.com/testing-micrometer-metrics
- `@AutoConfigureObservability` javadoc (Boot 4 API index): https://docs.spring.io/spring-boot/api/java/allpackages-index.html

**Deliverable:** a reusable Kotlin test module with `MeterRegistryAssert`-based unit tests, a `TestObservationRegistry` slice test asserting an `@Observed` method produces exactly one observation with the right low-cardinality tags, and one Podman/Testcontainers integration test scraping Prometheus output. Plus a deliberate "NaN gauge" reproduction and its fix.

---

### Phase 4: Registry model, MeterFilter, MeterBinder (2.5 weeks)
**Goal:** understand the machine, meaning how meters are created, filtered, and bound.

The registry model: `Meter`, `Meter.Id`, `Meter.Type`; the abstract `MeterRegistry` and its template methods `newCounter`/`newGauge`/`newTimer`; `MeterRegistry.Config`; `CompositeMeterRegistry` and the static `GlobalRegistry` (`Metrics.globalRegistry`); and push vs pull, which is `PushMeterRegistry`/`StepMeterRegistry` (step-based publishing, the publish scheduler, the `step` interval) versus pull (Prometheus scrape). Spring auto-configures a `CompositeMeterRegistry` and adds one child per `micrometer-registry-*` on the classpath.

MeterFilter in depth, as a policy engine: `accept`/`deny`/`denyUnless`, `map`, `configure`, `denyNameStartsWith`, `renameTag`, `replaceTagValues`, `ignoreTags`, `commonTags`, `maximumAllowableTags`, `maximumAllowableMetrics`; ordering and evaluation semantics; how Boot's `management.metrics.*` / `management.observations.*` are implemented as MeterFilters under the hood; and enforcing a cardinality budget with `maximumAllowableTags("http.server.requests", "uri", 100, MeterFilter.deny())`. Pair it with the HighCardinalityTagsDetector (https://docs.micrometer.io/micrometer/reference/concepts/high-cardinality-tags-detector.html).

MeterBinder in depth: the interface plus the built-ins `JvmMemoryMetrics`, `JvmGcMetrics`, `JvmThreadMetrics`, `JvmHeapPressureMetrics`, `JvmCompilationMetrics`, `JvmInfoMetrics`, `ClassLoaderMetrics`, `ProcessorMetrics`, `UptimeMetrics`, `FileDescriptorMetrics`, `DiskSpaceMetrics`, `ExecutorServiceMetrics`, `KafkaClientMetrics`/`KafkaStreamsMetrics`, `Log4j2Metrics`/`LogbackMetrics`, `OkHttpMetrics`, `PostgreSQLDatabaseMetrics`, and the cache binders, plus HikariCP's own `MicrometerMetricsTracker` (`hikaricp.connections.*`). Write your own binder, then see how Boot auto-configures them.

Virtual thread metrics: add `micrometer-java21`, wire `VirtualThreadMetrics`, force a pinning event, and observe `jdk.VirtualThreadPinned` surfacing.

The OTel semantic-convention wrinkle in Boot 4: to emit OTel-semantic names you must register convention beans (`OpenTelemetryServerRequestObservationConvention`, `OpenTelemetryJvmMemoryMeterConventions`, etc.) as shown in the Halbritter post. The ergonomics are expected to improve (spring-boot #47935).

Resources:
- JVM metrics and the Java 21 binder: https://docs.micrometer.io/micrometer/reference/reference/jvm.html
- `VirtualThreadMetrics` source: https://github.com/micrometer-metrics/micrometer/blob/main/micrometer-java21/src/main/java/io/micrometer/java21/instrument/binder/jdk/VirtualThreadMetrics.java
- HikariCP `MicrometerMetricsTracker`: https://github.com/brettwooldridge/HikariCP/blob/dev/src/main/java/com/zaxxer/hikari/metrics/micrometer/MicrometerMetricsTracker.java
- `MeterFilter` source: https://github.com/micrometer-metrics/micrometer/blob/main/micrometer-core/src/main/java/io/micrometer/core/instrument/config/MeterFilter.java

**Deliverable:** (a) a custom `MeterBinder` for the transactional-outbox poller, covering backlog age, poll duration, and publish successes and failures. (b) A global cardinality-budget MeterFilter plus HighCardinalityTagsDetector wired into your integration tests. (c) HikariCP dashboard notes correlating `hikaricp.connections.pending` and the `hikaricp.connections.acquire` timer with Aurora Performance Insights and CloudWatch.

---

### Phase 5: Distribution statistics plus histogram export flavors (2 weeks)
**Goal:** master percentiles vs histograms vs SLOs, and per-registry export.

Core: `DistributionStatisticConfig` (defaults above), client-side percentiles vs percentile histograms vs SLO boundaries, why client-side percentiles can't aggregate across instances, `HistogramGauges`, `TimeWindowPercentileHistogram` (HdrHistogram) vs `TimeWindowFixedBoundaryHistogram` (fixed buckets), `expiry`/`bufferLength`, `minimumExpectedValue`/`maximumExpectedValue` and bucket generation (~276 preset buckets clamped to range, ~73 for a default Timer), and histogram memory cost (`percentilePrecision`, buckets × dimensions).

Export flavors per registry: Prometheus classic histograms vs summaries; the fact that Micrometer's Prometheus registry does not emit native histograms (an open enhancement, so use OTLP exponential instead); `OtlpMeterRegistry` explicit vs base-2 exponential via `histogramFlavor`/`histogramFlavorPerMeter`, `maxScale`/`maxBuckets`; the SLO → explicit-bucket fallback; and delta vs cumulative temporality.

Given your queueing-theory background, connect this explicitly: histograms let you compute backend-aggregated tail latencies that Little's Law and Kingman's-formula reasoning actually need across a pod fleet, and client-side p99 averaging would corrupt that.

Resources:
- Histograms and percentiles: https://docs.micrometer.io/micrometer/reference/concepts/histogram-quantiles.html
- Distribution summaries: https://docs.micrometer.io/micrometer/reference/concepts/distribution-summaries.html
- `DistributionStatisticConfig` source: https://github.com/micrometer-metrics/micrometer/blob/main/micrometer-core/src/main/java/io/micrometer/core/instrument/distribution/DistributionStatisticConfig.java
- `OtlpConfig` source: https://github.com/micrometer-metrics/micrometer/blob/main/implementations/micrometer-registry-otlp/src/main/java/io/micrometer/registry/otlp/OtlpConfig.java
- Prometheus histograms and native background: https://prometheus.io/docs/practices/histograms/
- OTel metrics data model (exponential histograms): https://opentelemetry.io/docs/specs/otel/metrics/data-model/

**Deliverable:** instrument order-processing latency three ways, with client-side percentiles, Prometheus percentile-histogram buckets, and SLO boundaries, then write a short empirical note (Korean-blog-ready) showing that only the histogram and SLO variants aggregate correctly across two pods, plus a memory-footprint comparison of `percentilePrecision` 1 vs 2.

---

### Phase 6: Observation API, context propagation, tracing, and reading the source (3 weeks)
**Goal:** the unifying abstraction, propagation across every boundary in your stack, and source fluency.

Observation API: build a custom `ObservationConvention` for an "order" domain observation; register a logging `ObservationHandler` alongside the metric and tracing handlers; use `ObservationPredicate`/`ObservationFilter`; map low- vs high-cardinality key-values and observe exactly where each lands (metric tag vs span attribute).
- Introduction: https://docs.micrometer.io/micrometer/reference/observation/introduction.html
- Components: https://docs.micrometer.io/micrometer/reference/observation/components.html
- Source (docs adoc): https://github.com/micrometer-metrics/micrometer/blob/main/docs/modules/ROOT/pages/observation/introduction.adoc

Context propagation: exercise all five boundaries with tests proving context survives, namely `@Async` (`ContextPropagatingTaskDecorator`), Kotlin coroutines (`asContextElement`, Spring Framework 7 support, `MDCContext`), Reactor (`Hooks.enableAutomaticContextPropagation`), virtual threads (`ContextExecutorService`), and Kafka listeners.
- Usage examples: https://docs.micrometer.io/micrometer/reference/1.12/contextpropagation/usage.html
- spring-framework #35185 (coroutine propagation): https://github.com/spring-projects/spring-framework/issues/35185
- `AsContextElement.kt` source: https://github.com/micrometer-metrics/micrometer/blob/main/micrometer-core/src/main/kotlin/io/micrometer/core/instrument/kotlin/AsContextElement.kt

Tracing: choose the OTel bridge for Boot 4; configure sampling, W3C vs B3, baggage and remote-fields, and log correlation. Add the `X-Trace-Id` response-header filter from the Halbritter post.
- Spring Boot tracing reference: https://docs.spring.io/spring-boot/reference/actuator/tracing.html
- Sleuth→Micrometer Tracing migration: https://github.com/micrometer-metrics/tracing/wiki/Spring-Cloud-Sleuth-3.1-Migration-Guide

Kafka and outbox instrumentation: set `spring.kafka.listener.observation-enabled=true` and `spring.kafka.template.observation-enabled=true`; add `KafkaClientMetrics` and consumer-lag; write a `KafkaListenerObservationConvention`. Trap: with observation plus legacy Actuator Kafka metrics both on, Prometheus rejects the duplicate `spring.kafka.listener_seconds` with conflicting tag keys (spring-kafka #4104), so disable one.
- Spring Kafka monitoring: https://docs.spring.io/spring-kafka/reference/kafka/micrometer.html
- Consumer lag: https://www.baeldung.com/java-kafka-consumer-lag

Reading the source, in order:
1. `Meter`, `Meter.Id`, `MeterRegistry`, `AbstractMeterRegistry` (template methods), for the core contract.
2. `MeterFilter`, for how policy composes.
3. `AbstractDistributionSummary`/`AbstractTimer` → `TimeWindowPercentileHistogram`/`TimeWindowFixedBoundaryHistogram`, for histogram selection.
4. `PushMeterRegistry`/`StepMeterRegistry`, for the publishing model.
5. `micrometer-registry-prometheus` `PrometheusMeterRegistry` + `PrometheusNamingConvention`, for name translation.
6. `micrometer-registry-otlp` `OtlpMeterRegistry` + `OtlpConfig`, for flavor and temporality logic.
7. `micrometer-observation` `Observation`, `ObservationRegistry`, `ObservationHandler`.
8. `micrometer-tracing` bridges (`W3CPropagation`).
9. Boot 4 autoconfig: `spring-boot-micrometer`, `spring-boot-opentelemetry`, `spring-boot-micrometer-tracing-opentelemetry`, `spring-boot-actuator`. Use the DeepWiki index (https://deepwiki.com/spring-projects/spring-boot) as a map, then read the real source.

**Deliverable:** a single `Observation` at the order-service boundary that yields a metric, a span, and a correlated log, propagated end-to-end from HTTP → coroutine service → Kafka producer → Kafka consumer (in a second service) → outbox poller, with integration tests (Podman/Testcontainers) asserting the trace ID survives every hop.

---

### Phase 7: Capstone (2 weeks)
**Build:** a production-grade observability layer for a two-service Kotlin event-driven system on EKS (orders and fulfillment, Aurora MySQL/HikariCP, Kafka, virtual-thread executors), instrumented entirely via the Micrometer Observation API, exporting through the OTLP registry and OTel tracing bridge to a Grafana LGTM backend.

Requirements that force mastery:
- Custom `ObservationConvention`s for the order and outbox domains, with low/high-cardinality discipline enforced by a cardinality-budget MeterFilter plus HighCardinalityTagsDetector in CI.
- HikariCP, Kafka-lag, and virtual-thread-pinning dashboards; common tags for `pod`, `namespace`, `cluster` via `MeterRegistryCustomizer`, with a written note on per-pod aggregation and pod-churn metric identity.
- Histogram strategy documented: SLO buckets for latency, backend-aggregated rather than client-side p99.
- A k6 load test whose output is pushed into the same Prometheus, compared against Micrometer's `http.server.requests` histogram to validate the load test. This is your bridge to the separately-delivered platform/PromQL/SLO plan, so don't re-teach it here.
- A full context-propagation test suite covering coroutines, Kafka, and virtual threads.

**Deliverable:** the running system plus a Korean-language technical blog series (your existing practice) documenting the Boot 3→4 migration traps, the Observation API, and the histogram-aggregation finding.

## Common traps and misconceptions (Spring Boot 4 + Micrometer specific)
1. Following Boot 3.x tutorials verbatim. Module names (`org.springframework.boot.micrometer.metrics.autoconfigure.*`), the new OTel starter, and the metrics-vs-tracing property split all differ. Concepts transfer; wiring does not.
2. Confusing the two OTLP property namespaces. Metrics are `management.otlp.metrics.*` (Micrometer registry); traces are `management.opentelemetry.tracing.*`; logs are `management.opentelemetry.logging.*`. Different prefixes, different libraries.
3. Duplicate metrics when both Micrometer OTLP export and an OTel bridge are active. Disable `management.otlp.metrics.export.enabled`.
4. Gauge `NaN` or disappearing gauges from weak references. Hold a strong reference or use `.strongReference(true)`, and never try to "set" a gauge.
5. Averaging client-side p99s across pods, which is statistically invalid. Use percentile histograms or SLO buckets and aggregate in the backend.
6. Expecting native histograms from the Prometheus registry. Micrometer doesn't emit them (open issue, verify #5891), so use the OTLP exponential flavor instead.
7. `serviceLevelObjectives` silently disabling exponential OTLP histograms, because SLOs force the explicit-bucket fallback.
8. An OTLP delta-vs-cumulative mismatch with the backend, which produces silent data weirdness.
9. The Kafka observation vs legacy metrics name clash (`spring.kafka.listener_seconds`, spring-kafka #4104). Enable observation or legacy Actuator Kafka metrics, not both.
10. `new RestClient()`/`WebClient()` breaks trace propagation. Always inject the auto-configured builder.
11. `@Observed`/`@Timed` not firing. It needs `management.observations.annotations.enabled=true`, the aspect beans, AOP, and a Spring-proxied bean. Kotlin-specific: classes and methods are `final` by default, so without `kotlin-spring`/`all-open`, proxying fails silently. Self-invocation is never intercepted.
12. Observability autoconfig is disabled in tests. Add `@AutoConfigureObservability`.
13. `highCardinalityKeyValues` ≠ metric tags. They only reach spans, and putting a user ID in a low-cardinality key-value will blow up metric cardinality.
14. Prometheus client 0.x → 1.x (Micrometer ≥1.13, client 1.4.x in 1.16) changed some names and label handling, so dashboards and alerts can break. `micrometer-registry-prometheus-simpleclient` is a deprecated stopgap.
15. The `micrometer-java11`/`micrometer-java21` split. `MicrometerHttpClient` (Apache HttpClient 5 instrumentation) moved out of `micrometer-core`, so add the right module and fix imports.

## The reference shelf (curated)

**Official docs to read end-to-end**
- Micrometer reference (Concepts, Implementations, Observation, Context Propagation): https://docs.micrometer.io/micrometer/reference/
- Micrometer 1.16 and 1.17 migration guides plus release notes: https://github.com/micrometer-metrics/micrometer/releases (1.16.0: https://github.com/micrometer-metrics/micrometer/releases/tag/v1.16.0)
- Spring Boot reference, Actuator (Metrics, Observability, Tracing): https://docs.spring.io/spring-boot/reference/actuator/
- Spring Boot 4.1 API package index: https://docs.spring.io/spring-boot/api/java/allpackages-index.html
- Spring "Road to GA" series, especially modularization and OTel: https://spring.io/blog/2025/09/02/road_to_ga_introduction
- OpenTelemetry metrics data model and OTLP exporter spec: https://opentelemetry.io/docs/specs/otel/metrics/data-model/ and https://opentelemetry.io/docs/specs/otel/metrics/sdk_exporters/otlp/

**Talks** (verified maintainer attributions: Jonatan Ivanov, Tommy Ludwig, and Marcin Grzejszczak are all Micrometer maintainers at Broadcom)
- "Micrometer Mastery: Unleash Advanced Observability in your JVM Apps," Ludwig and Ivanov, Spring I/O 2024: https://www.youtube.com/watch?v=Qyku6cR6ADY
- "I Can See Clearly Now: Observability of JVM & Spring Boot 2-3-4 apps," Ivanov and Ludwig, Spring I/O 2026: https://2026.springio.net/sessions/i-can-see-clearly-now-observability-of-jvm-and-spring-boot-2-3-4-apps/
- "A Bootiful Podcast" episodes with Jonatan Ivanov (observability) and Tommy Ludwig: https://spring.io/blog/2024/08/01/a-bootiful-podcast-observability-legend-jonatan-ivanov-on-the-latest-and/
- Adrian Cole, "Observability 3 Ways" (the metrics/tracing/logging distinction; recommended by the Micrometer docs)
- Ludwig and Grzejszczak, "Observability of Your Application" (recommended in the Micrometer docs Concepts page)

**GitHub repos and samples to clone**
- `micrometer-metrics/micrometer` (read the source): https://github.com/micrometer-metrics/micrometer
- `micrometer-metrics/tracing`: https://github.com/micrometer-metrics/tracing
- `mhalbritter/spring-boot-and-opentelemetry`: https://github.com/mhalbritter/spring-boot-and-opentelemetry
- `ThomasVitale/spring-boot-opentelemetry`: https://github.com/ThomasVitale/spring-boot-opentelemetry
- Spring Boot source plus the DeepWiki map: https://github.com/spring-projects/spring-boot and https://deepwiki.com/spring-projects/spring-boot

**Source files worth reading (exact paths)**
- `micrometer-core`: `.../instrument/MeterRegistry.java`, `.../config/MeterFilter.java`, `.../distribution/DistributionStatisticConfig.java`, `.../distribution/TimeWindowPercentileHistogram.java`, `.../distribution/TimeWindowFixedBoundaryHistogram.java`, `.../push/PushMeterRegistry.java`
- `micrometer-registry-otlp`: `OtlpMeterRegistry.java`, `OtlpConfig.java`
- `micrometer-registry-prometheus`: `PrometheusMeterRegistry.java`, `PrometheusNamingConvention.java`
- `micrometer-observation`: `Observation.java`, `ObservationRegistry.java`, `ObservationHandler.java`
- `micrometer-java21`: `VirtualThreadMetrics.java`

**Books and longer references**
- No dedicated Micrometer book exists at the level you need, so treat the reference docs plus source as the "book." For breadth, *Cloud Native Spring in Action* (Thomas Vitale, Manning) covers Boot observability, though it's Boot 3-era, so adjust for Boot 4. For the metrics-theory framing you already have from queueing theory, pair histograms with your existing Kingman and Little's-Law intuition rather than a new text.

## Recommendations
1. Do Phases 0 to 3 in the first month, non-negotiably in this order, because they build the test harness and cardinality instincts every later phase reuses. If you're time-constrained, Phases 0 and 1 alone make you productive on Boot 4.
2. Front-load the version cheat sheet (the Phase 0 deliverable) and keep it open. It prevents the single most common failure mode, which is Boot 3.x tutorial drift.
3. Standardize on the Observation API for all new instrumentation, so you write metrics and spans once and export via OTLP. Only drop to raw `MeterRegistry` for pure metrics with no trace value, such as a cheap `Gauge`.
4. For histograms, default to SLO or percentile-histogram buckets rather than client-side percentiles, unless a metric is single-instance by construction. This is the decision with the biggest correctness payoff on EKS.
5. Choose the OTel tracing bridge (`micrometer-tracing-bridge-otel`) for Boot 4 unless you have an existing Zipkin or Brave investment.
6. Gate cardinality in CI using HighCardinalityTagsDetector plus a `maximumAllowableTags` MeterFilter. Make an accidental high-cardinality tag fail a test, not a production bill.

**Thresholds that change the plan:**
- If Micrometer ships Prometheus native-histogram support (watch the open issue), revisit Phase 5. You may prefer native histograms over OTLP exponential for a Prometheus or Mimir backend.
- If you standardize on Java 24+ across EKS, extend the virtual-thread binder with `VirtualThreadSchedulerMXBean` gauges (mounted, queued, parallelism), which the JFR-based `VirtualThreadMetrics` doesn't provide.
- If a new Micrometer 2.0 major release lands, re-verify the registry APIs and deprecations before trusting this plan's class names.
- If you adopt the OTel API directly, for instance because a third-party lib uses `MeterProvider`, remember that Spring exports only Micrometer metrics; those OTel-API metrics won't be exported without extra wiring.

## Caveats
- Fast-moving versions. Boot 4.0 GA'd Nov 20, 2025; 4.1.0 shipped June 10, 2026, and Micrometer 1.17.0 on June 8, 2026. Treat every property name and module path here as "verify against the reference docs for your exact patch version," especially the OTel-semantic-convention bean wiring, which the Spring team has flagged for change (spring-boot #47935).
- The native-histogram issue number is unverified. The candidate tracking issue (#5891) could not be definitively confirmed by title, so verify at https://github.com/micrometer-metrics/micrometer/issues before citing it. What is certain: the Micrometer Prometheus registry does not emit native histograms in 1.16/1.17.
- Some cited examples are Boot 3.x-era (Baeldung, SoftwareMill, several Medium posts). They're included where the *concept* is version-stable, such as gauge NaN, testing patterns, and the Observation lifecycle. Cross-check any wiring against the Boot 4 docs.
- Coroutine and `Flow` propagation has open bugs (spring-framework #36427 on Boot 4.0.3), so test your specific version rather than assuming it works.
- The downstream platform layer is intentionally out of scope, meaning Grafana LGTM operations, PromQL/LogQL/TraceQL, dashboards-as-code, and SLO/error-budget alerting. Those are covered by your separately delivered plan; this one stops at the application and Micrometer boundary and only references them as "where this leads."
- Blog-post sources are secondary. Where a maintainer talk, official doc, or source file was available, that is the citation of record; treat vendor blogs (base14, Uptrace, OneUptime, Last9) as orientation, not authority.
