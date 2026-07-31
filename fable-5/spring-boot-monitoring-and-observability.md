---
title: "A Graduated Mastery Curriculum for Spring Boot Monitoring & Observability (2026 Edition)"
category: "Spring & Spring Boot"
description: "A 6-stage, roughly 4-6 month graduated curriculum from a Docker-Compose quick tour (Actuator, Prometheus, Grafana) to source-level Actuator and Micrometer understanding and org-wide SLO-driven observability, anchored on the unifying Micrometer Observation API ('instrument once, get metrics + traces + logs'). It covers the Spring Boot 4.x era (GA Nov 2025, Micrometer 2, the OpenTelemetry starter, 3.5 EOL June 2026), built-in structured logging since 3.4, cardinality as the recurring failure mode, and Promtail's EOL in favor of Grafana Alloy. It is tailored to a Kotlin stack with Kafka trace propagation, Aurora MySQL and HikariCP metrics, and EKS via kube-prometheus-stack with Loki and Tempo, sourced from the Actuator and Micrometer references, the Google SRE books, Prometheus: Up & Running 2nd ed., and Observability Engineering 2nd ed."
---

# A Graduated Mastery Curriculum for Spring Boot Monitoring & Observability (2026 Edition)

**TL;DR**
- Build mastery in about 6 stages over 4-6 months, moving from a Docker-Compose quick tour (Actuator, Prometheus, Grafana) to source-code-level understanding of Actuator and Micrometer and then to org-wide SLO-driven observability, anchored throughout on the unifying Micrometer Observation API ("instrument once, get metrics + traces + logs").
- Prioritize primary sources: the Spring Boot Actuator reference, the Micrometer and Micrometer-Tracing docs, the Prometheus, Grafana, and OpenTelemetry docs, the Google SRE books (free at sre.google), *Prometheus: Up & Running* 2nd ed., and *Observability Engineering* 2nd ed., supplemented by Spring team talks from Jonatan Ivanov, Tommy Ludwig, and Marcin Grzejszczak.
- Tailor every stage to your stack: Kotlin with Spring Boot 3.x/4.x, Kafka producer and consumer trace propagation, Aurora MySQL and HikariCP metrics, and EKS deployment via kube-prometheus-stack (ServiceMonitor, PodMonitor) with Loki and Tempo for logs and traces.

## Key Findings

**The version landscape you are learning against (July 2026).** Spring Boot 4.0 went GA on November 20, 2025, per Phil Webb's Spring blog announcement "Spring Boot 4.0.0 available now", built on Spring Framework 7, Jakarta EE 11, and Micrometer 2, with an OpenTelemetry starter. Spring Boot 4.1.0 is the latest stable release, published to Maven Central on June 10, 2026 (per the HeroDevs release tracker), and is the recommended target for new projects. Note that the 3.5 line hit open-source EOL on June 30, 2026. Spring Boot 3.4 (November 2024) introduced built-in structured logging (ECS, Logstash, GELF) with no extra dependencies. Your curriculum must therefore treat two eras: 3.x resources are still overwhelmingly valid, but Micrometer moved to 2.x and Actuator's legacy JMX-oriented pieces were modernized in 4.x. Promtail reached end of life on March 2, 2026, so new log-collection work should use Grafana Alloy rather than Promtail.

**The conceptual spine is the Observation API.** Since Spring Boot 3 and Micrometer 1.10, the Observation API lets you instrument code once and emit metrics, traces, and logs from a single instrumentation point via `ObservationHandler`s. This is the single most important idea to internalize, because it unifies all five of your required topics. Marcin Grzejszczak's "The Story of Micrometer Observation" (Dec 2025) documents how and why it was built.

**Cardinality is the recurring failure mode.** Across metrics (Micrometer tags), logs (Loki labels), and long-term storage costs, unbounded label and tag values are the number-one production hazard. Micrometer ships a `HighCardinalityTagsDetector`, and the discipline of low-cardinality metric tags against high-cardinality trace attributes is a mastery-level skill.

## Details: the curriculum

### Stage 0: quick tour, get a stack running (~1 week, 8-12 hrs)
**Objectives:** stand up a working Kotlin and Spring Boot service exposing `/actuator/prometheus`, scraped by Prometheus and visualized in Grafana, all via Docker Compose, so you have a sandbox for every later stage.

**Key concepts:** the `spring-boot-starter-actuator` plus `micrometer-registry-prometheus` dependency pair, `management.endpoints.web.exposure.include`, the Prometheus scrape model, and importing a community Grafana dashboard.

**Hands-on:**
1. Generate a Kotlin Spring Boot 3.4+ or 4.x project on start.spring.io with Actuator, Web, and the Prometheus registry.
2. Write a Docker Compose file with your app plus Prometheus plus Grafana, and point Prometheus at `/actuator/prometheus`.
3. Import Grafana dashboard 4701 (JVM Micrometer). For Spring Boot 3.x also try 19004 (Spring Boot 3.x Statistics) and 17175 (Spring Boot Observability). Note that the older 10280 and 12464 dashboards were built for Spring Boot 2.x, and some HTTP panels show "No data" on 3.x because of renamed metrics.
4. Set `management.metrics.tags.application=${spring.application.name}` so the 4701 dashboard's `application` variable works.

**Resources (canonical):** the Spring Boot Actuator reference "Endpoints" page, and the Grafana Labs "JVM (Micrometer)" dashboard page (4701). Supplementary: any current "Spring Boot + Prometheus + Grafana in 15 minutes" walkthrough (Baris.io, Tutorial Works), used only for the Compose wiring rather than for concepts.

### Stage 1: Actuator deep dive (~2 weeks, 15-20 hrs)
**Objectives:** master every production-relevant endpoint, health indicators and groups, Kubernetes probes, custom endpoints and indicators, security and exposure, and the management port and context.

**Key concepts:**
- Endpoints: `health`, `info`, `metrics`, `env`, `configprops`, `loggers` (runtime log-level changes), `threaddump`, `heapdump`, `prometheus`, `beans`, `conditions`, `scheduledtasks`, `sbom`. By default only `health` is exposed over HTTP, `shutdown` is disabled, and `/env`, `/configprops`, and `/quartz` values are sanitized.
- Health indicators and health groups: configure `management.endpoint.health.group.readiness.include=...`. Actuator auto-configures `LivenessStateHealthIndicator` and `ReadinessStateHealthIndicator` from the `ApplicationAvailability` interface when running in Kubernetes. The critical rule: the liveness probe must not depend on external systems (DB, Kafka, cache), or a dependency outage triggers mass pod restarts and cascading failure. Readiness checks of external systems must be chosen deliberately.
- Custom endpoints (`@Endpoint`, `@ReadOperation`/`@WriteOperation`/`@DeleteOperation`, `@WebEndpoint`, `@EndpointWebExtension`) and a custom `HealthIndicator` or `ReactiveHealthIndicator`.
- Security: exposure against access; `EndpointRequest.toAnyEndpoint()` with Spring Security; CSRF interaction with POST endpoints; and a separate management port (`management.server.port`) and base path (`management.endpoints.web.base-path`). This matters for EKS: expose Actuator on a management port that your public Ingress does not route.
- Internals: endpoints are auto-configured only when "available," meaning enabled and exposed, and operations auto-expose over Spring MVC, WebFlux, or Jersey.

**Hands-on (on your Kafka microservice):** add a custom `HealthIndicator` for Kafka consumer lag or Aurora connectivity, but keep it out of the liveness group. Wire liveness and readiness probes into your EKS Deployment manifest, move Actuator to a dedicated management port, lock down exposure with Spring Security, and use `loggers` to flip a package to DEBUG at runtime.

**A security caveat worth internalizing:** the December 2024 "We know where your car is" 38C3 talk about Volkswagen used an exposed Actuator as a gateway. Treat Actuator exposure as a real attack surface.

**Resources (canonical):** the Spring Boot Actuator reference, specifically "Endpoints," "Health," and the Actuator REST API docs (versioned for 3.3, 3.4, 3.5, 4.0, and 4.1), plus the InnoQ deep-dive series "Spring Boot Actuator Endpoints: What does 'production-ready' mean?" (2025). Supplementary: Baeldung's "Spring Boot Actuator."

### Stage 2: logging and MDC (~2 weeks, 15-20 hrs)
**Objectives:** master SLF4J and Logback MDC, structured JSON logging, correlation and trace-ID propagation into logs, the thread-pool, async, coroutine, and reactive pitfalls specific to your Kotlin stack, and a Kubernetes log pipeline.

**Key concepts:**
- MDC fundamentals: the SLF4J `MDC` and the Logback `%X{...}` pattern conversion.
- Structured logging in Spring Boot 3.4+: `logging.structured.format.console=ecs|logstash|gelf`, service metadata properties, `StructuredLogFormatter` custom formats, the `JsonWriter` utility, and the fluent `LOGGER.atInfo().addKeyValue(...)` API. For pre-3.4 versions or advanced needs, `logstash-logback-encoder` remains the reference.
- Correlation IDs: when Micrometer Tracing is on the classpath, Spring Boot auto-populates `traceId` and `spanId` into MDC. Use `logging.pattern.level`, or a `logback-spring.xml` pattern with `%X{traceId:-} %X{spanId:-}`. One migration detail: Sleuth used `%X{X-B3-TraceId}`, while Micrometer Tracing uses `traceId` and `spanId`.
- Pitfalls, which is where your stack bites: MDC is thread-local, so it is lost across thread-pool handoffs, `@Async`, `CompletableFuture`, reactive operators, and coroutine suspensions.
  - Kotlin coroutines: use `kotlinx-coroutines-slf4j`'s `MDCContext` element (`launch(MDCContext())`). A crucial gotcha from the official docs: you cannot mutate MDC inside a coroutine with `MDC.put` and expect it to survive suspension, because updates are lost on the next suspension and resumption unless captured with `withContext(MDCContext())`.
  - Reactive (WebFlux): thread-locals don't follow the reactive chain, so use Micrometer Context Propagation (`ContextRegistry`, `ContextSnapshot`) and Reactor's automatic context propagation. Spring Boot 4.1 also adds async context propagation for `@Async`.
- The log pipeline on Kubernetes: JSON to stdout, then a node agent, then a store. Prefer Grafana Loki, which indexes labels rather than full text and is 10 to 100 times cheaper than Elasticsearch, with Grafana Alloy as the agent, since Promtail is EOL as of March 2, 2026. The ELK or EFK stack is the alternative. The golden rule mirrors metrics: keep high-cardinality values (request IDs, user IDs) in the log body, not in Loki labels.

**Hands-on:** enable ECS JSON logging. Add a `OncePerRequestFilter`, and a Kafka `RecordInterceptor` or consumer wrapper, that seeds a correlation ID into MDC. Write a coroutine-based flow that correctly propagates MDC via `MDCContext`. Deploy Loki and Alloy on EKS, and confirm you can pivot from a Grafana log line's `traceId` to a trace.

**Resources (canonical):** the Spring Boot reference "Structured logging" page plus the Spring Blog's "Structured logging in Spring Boot 3.4"; the `kotlinx-coroutines-slf4j` `MDCContext` API docs and source; and the Grafana Loki "Get started" and Alloy migration docs. Supplementary: Baeldung's structured-logging article, and the logstash-logback-encoder GitHub repo.

### Stage 3: metrics with Micrometer (~3 weeks, 20-25 hrs)
**Objectives:** master Micrometer as the metrics facade, covering meter types, tags and cardinality, `MeterRegistry`, percentiles against histograms, built-in instrumentation, custom metrics, and the Observation API that unifies everything.

**Key concepts:**
- Meter types: `Counter`, `Gauge`, `Timer`, `DistributionSummary`, `LongTaskTimer`, `FunctionCounter`, and `FunctionTimer`.
- The `MeterRegistry` model: `SimpleMeterRegistry`, `CompositeMeterRegistry`, `Metrics.globalRegistry`, `MeterRegistryCustomizer` for common tags, and `MeterFilter` (deny and accept, transform IDs, configure distribution statistics, and `ignoreTags` or `renameTag` to defuse cardinality).
- Tags and cardinality: dimensional tags become Prometheus labels, and every distinct combination is a new time series. Store `Meter` instances in fields, and never put unbounded values (user IDs, request IDs, raw URLs) in tags. Use the `HighCardinalityTagsDetector`.
- Percentiles against histograms: client-side pre-computed percentiles (`percentiles = {0.5,0.95,0.99}`) cannot be aggregated across instances, while percentile histograms (`percentiles-histogram`, which emit `_bucket` series) can be aggregated server-side via `histogram_quantile()` in PromQL. Prefer histograms for SLOs and multi-instance services, and configure per-meter `slo` and service-level boundaries.
- Built-in instrumentation to study: the JVM (memory, GC, threads), `process_*`, HikariCP (the Aurora connection pool), Tomcat and Netty, Spring MVC and WebFlux (`http.server.requests`), Spring Kafka (`KafkaTemplate` and listener containers with `setObservationEnabled(true)`), Lettuce and Redis, and JPA and Hibernate.
- The Observation API: `ObservationRegistry`, `Observation`, `@Observed` (which needs `aspectjweaver` and `management.observations.annotations.enabled=true`), `ObservationConvention`, `ObservationPredicate` and `ObservationFilter`, low-cardinality against high-cardinality key-values, and `DefaultMeterObservationHandler`. Spring Boot 4.0 added `@MeterTag` on `@Counted` and `@Timed`, plus `@ObservationKeyValue` support.

**Hands-on:** instrument an order and payment flow with a `Counter` (orders by status and region, with bounded tags) and a `Timer` with a percentile histogram. Add a `Gauge` for queue depth. Convert one hand-rolled `Timer` to `@Observed` and observe metrics, spans, and logs coming from that single instrumentation point. Enable Spring Kafka observation, add a `MeterFilter` that caps cardinality, and write a unit test with `SimpleMeterRegistry`.

**Resources (canonical):** the Micrometer reference docs (Concepts: Registry, Meter Filters, High Cardinality Tags Detector) and the Spring Boot reference "Metrics" and "Observability" pages, plus the founding Spring Blog post "Micrometer: Spring Boot 2's new application metrics collector" (2018, still the best conceptual origin story) and "Observability with Spring Boot 3" (Spring Blog, 2022). Talks: Ivanov and Ludwig's "Micrometer Mastery: Unleash Advanced Observability in your JVM Apps" (Spring I/O 2024, with slides on Speaker Deck and video on YouTube). Supplementary: Baeldung's "Observability with Spring Boot", and the Reflectoring and Tutorial Works custom-metrics articles.

### Stage 4: Prometheus and PromQL (~3 weeks, 20-30 hrs)
**Objectives:** master the exposition format, the scrape model, PromQL from basics to advanced, Prometheus on Kubernetes via the Operator, alerting, and long-term storage.

**Key concepts:**
- The exposition and OpenMetrics format, the pull model and scrape config, and `Pushgateway` for batch jobs (and why push is the exception).
- PromQL: instant against range vectors; selectors and matchers; `rate`, `irate`, and `increase`; aggregation operators (`sum`, `avg`, `max`, `by`, `without`); `histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket[5m])) by (le))`; binary operators and `group_left`; recording rules; and native histograms, which are newer and use sparse exponential buckets.
- Prometheus on Kubernetes: the Prometheus Operator and the kube-prometheus-stack Helm chart (Prometheus, Alertmanager, Grafana, node-exporter, kube-state-metrics), with the CRDs `ServiceMonitor`, `PodMonitor`, `Probe`, `ScrapeConfig`, and `PrometheusRule`. A critical gotcha: the operator's `serviceMonitorSelector` defaults to matching the `release: <helm-name>` label, so a `ServiceMonitor` without the matching label is silently ignored, and `serviceMonitorSelectorNilUsesHelmValues=false` is often needed to pick up all monitors.
- Alerting: `PrometheusRule` alerting rules plus Alertmanager (routing, grouping, silencing, receivers). Alert on symptoms (RED metrics), not on causes.
- Long-term storage: the Prometheus TSDB defaults to 15-day retention. Per the official Prometheus "Storage" docs, if neither `--storage.tsdb.retention.time` nor `storage.tsdb.retention.size` is set, retention defaults to `15d`. The options: Thanos, whose sidecar keeps Prometheus as the source of truth and is the lowest-friction add-on; Grafana Mimir, a horizontally scalable, multi-tenant remote-write backend, where Mimir 3.0 added Kafka-based ingestion; and Amazon Managed Service for Prometheus (AMP), the natural EKS choice via remote-write. VictoriaMetrics is a common simplicity and compression alternative.

**Hands-on (on EKS):** install kube-prometheus-stack via Helm. Write a `ServiceMonitor` targeting `/actuator/prometheus` with the correct labels. Write PromQL for RED metrics on `http_server_requests_seconds`. Create a recording rule and a burn-rate alert. Wire remote-write to Amazon Managed Prometheus and confirm cross-cluster query.

**Resources (canonical):** the official Prometheus docs, specifically the querying overview (`/docs/prometheus/latest/querying/`), PromQL basics (`/querying/basics/`), operators (`/querying/operators/`), and functions (`/querying/functions/`), plus the practices pages on naming (`/docs/practices/naming/`), histograms and summaries (`/docs/practices/histograms/`), and instrumentation (`/docs/practices/instrumentation/`); and the Prometheus Operator docs (getting started, ServiceMonitor and PodMonitor) with the kube-prometheus-stack chart. Book: *Prometheus: Up & Running*, 2nd ed. (Julien Pivotto and Brian Brazil, O'Reilly, 2023), the canonical text, where the 2nd edition adds new PromQL functions, service discovery providers, a dedicated TLS and security chapter, and new Alertmanager receivers. For learning PromQL: the PromLabs PromQL Cheat Sheet (promlabs.com/promql-cheat-sheet, free, by PromQL creator Julius Volz), the PromLabs "Understanding PromQL" and "Introduction to Prometheus" training courses (training.promlabs.com), and Brian Brazil's Robust Perception "Reliable Insights" blog (robustperception.io/blog), which is canonical though not actively updated since around 2020. AWS: the Amazon Managed Service for Prometheus docs.

### Stage 5: Grafana, dashboards, and visualization (~2 weeks, 15 hrs)
**Objectives:** build and provision dashboards for Spring Boot, JVM, and Kafka services, apply the RED, USE, and golden-signals design methods, use variables and templating, and set up Grafana alerting.

**Key concepts:**
- Design methods: RED (rate, errors, duration), which is service- and request-centric and good for alerting and SLAs, popularized by Tom Wilkie of Grafana Labs; USE (utilization, saturation, errors), which is resource-centric, from Brendan Gregg; and Google's Four Golden Signals (RED plus saturation). "USE tells you how happy your machines are; RED tells you how happy your users are."
- Grafana best practices: dashboards with a purpose and a narrative (general to specific, in a Z-pattern layout); consistent color semantics; normalized axes; variables and templating (`$application`, `$instance`); avoiding over-frequent refresh; documenting panels; and no editing in the browser, since you should test in a separate instance.
- Dashboards as code, and provisioning: provision dashboards and data sources via config files or ConfigMaps, with GitOps through ArgoCD or Flux, and generate dashboards programmatically (Grafonnet, grafanalib) for consistency at scale.
- Grafana alerting: unified alerting, contact points, and notification policies.

**Hands-on:** import 4701 as a baseline, then build a hand-crafted RED dashboard for one Kafka microservice (request rate, error percentage, and p50/p95/p99 from histograms) plus a HikariCP and Aurora pool row and a Kafka consumer-lag row. Templatize by `application` and `instance`, provision the dashboard as a ConfigMap in your EKS monitoring namespace, and add a Grafana alert on p99 latency.

**Resources (canonical):** the Grafana docs, specifically "Best practices for dashboards," "Getting started… best practices to design your first dashboard," provisioning, and variables and templating; plus Tom Wilkie's "The RED Method" (the Grafana blog post and the GrafanaCon slides). Supplementary: the "JVM (Micrometer)" (4701) and "Spring Boot Observability" (25359) dashboard pages.

### Stage 6: advanced tracing, the three pillars, SLOs, and production operations (~4 weeks, 25-35 hrs)
**Objectives:** add distributed tracing across HTTP and Kafka, unify the three pillars, adopt SLO and error-budget-driven alerting, understand exemplars, and reason about the OpenTelemetry-versus-Micrometer tradeoff and about instrumentation cost.

**Key concepts:**
- Micrometer Tracing with OpenTelemetry: add `micrometer-tracing-bridge-otel` and `opentelemetry-exporter-otlp`, or the Spring Boot 4 `spring-boot-starter-opentelemetry`, and export via OTLP to Tempo, Jaeger, or Zipkin. W3C Trace Context (`traceparent`) is the default propagation. Per the Spring Boot reference "Tracing" doc, Spring Boot by default samples only 10% of requests to avoid overwhelming the backend; configure this with `management.tracing.sampling.probability`, and set it to `1.0` in dev.
- Kafka context propagation: Spring Kafka injects and extracts trace context in record headers when observation is enabled (`KafkaTemplate.setObservationEnabled(true)` and `containerProperties.setObservationEnabled(true)`), producing linked PRODUCER and CONSUMER spans. Watch the async gotcha: when you hand off to `CompletableFuture.runAsync`, capture context with `ContextSnapshot.captureAll()` and restore it via `setThreadLocals()`.
- The three pillars and their unification: logs tell you what, metrics tell you context and how much, and traces tell you why, all unified under Observations.
- Exemplars: attach a representative `traceId` to histogram buckets so you can jump from a p99 latency spike in Grafana straight to the exact trace in Tempo. This requires exemplar storage enabled in Prometheus (`--enable-feature=exemplar-storage`) and OpenMetrics exposition. Tempo's metrics-generator can also produce RED span metrics and exemplars via remote-write.
- SLOs and error budgets (SRE): SLI against target, an error budget of 1 minus the SLO, and multi-window multi-burn-rate alerting (paging at a 14.4x burn rate, roughly 2 days, and ticketing at 6x, roughly 5 days) from SRE Workbook chapter 5, with an error-budget policy gating releases. This is the philosophy that should drive your alerting, replacing threshold spam.
- The OTel versus Micrometer tradeoff: in the Spring ecosystem, Micrometer is the recommended metrics path (export via `OtlpMeterRegistry` if you want OTLP, since Spring Boot does not provide an OpenTelemetry `SdkMeterProvider`), while tracing bridges to OTel. Instrument once with Observations and stay backend-neutral. Alternatively the OTel Java agent auto-instruments with zero code, so understand the tradeoffs between the agent's breadth and overhead and Micrometer's first-class Spring integration.
- Cost and performance of instrumentation: cardinality explosions, sampling strategy (head against tail), histogram bucket counts, and telemetry volume all have real CPU and storage cost.

**Hands-on:** enable end-to-end tracing across your order-service (HTTP) → Kafka → payment-service (consumer) → Aurora, viewed in Tempo. Turn on exemplars and pivot from a metric to a trace in Grafana. Define an SLO and error-budget policy for one service and implement multi-window burn-rate alerts. Run the OTel Java agent against one service and compare it with the Micrometer-native service.

**Resources (canonical):** the Spring Boot reference "Observability" and "Tracing" pages; the Micrometer Tracing reference; the OpenTelemetry docs (OTLP, Java); the Grafana Tempo docs (metrics from traces, exemplars); and the Google SRE Book (2016) and SRE Workbook (2018), free at sre.google/books, especially "Service Level Objectives," "Embracing Risk," and Workbook chapters 2 and 5. Talks and posts: the Spring Blog's "Observability with Spring Boot 3"; Marcin Grzejszczak's "The Story of Micrometer Observation"; and Piotr Minkowski's "Kafka Tracing with Spring Boot and OpenTelemetry." Advanced books: *Observability Engineering* 2nd ed. (Majors, Fong-Jones, and Miranda with Austin Parker, O'Reilly, released June 2026, nearly a full rewrite at around 600 pages); *Learning OpenTelemetry* (Ted Young and Austin Parker, O'Reilly, 2024); *Mastering Distributed Tracing* (Yuri Shkuro, creator of Jaeger, Packt, 2019); *Cloud-Native Observability with OpenTelemetry* (Alex Boten, Packt, 2022); and *Cloud Observability in Action* (Michael Hausenblas, Manning, 2023).

### Mastery capstone and going deeper (ongoing)
**Objectives:** source-code-level understanding, contribution, and org-wide standards.

- Source reading: Actuator auto-configuration (`spring-boot-actuate-autoconfigure`), `MeterRegistry` and `HighCardinalityTagsDetector`, and the `micrometer-observation` module, which is small and near-zero-dependency by design. Read Grzejszczak's article on why it was kept dependency-light so Spring Framework could put it on the classpath. Study the `spring-projects/spring-boot` docs source on GitHub for versioned Actuator behavior.
- Contribution: file or fix issues against Micrometer or its sample repos, and write an `ObservationDocumentation` enum and generate docs with the Micrometer Docs Generator.
- Org-wide standards: define naming conventions, common tags, `ObservationConvention`s, dashboard templates as code, and an error-budget policy, all as shared libraries, and drive SLO-based alerting across teams.
- Deeper theory: PromQL internals and TSDB storage (*Prometheus: Up & Running* 2nd ed. plus the Prometheus docs on native histograms and storage); *Observability Engineering*'s chapters on high-cardinality data stores, such as the Honeycomb Retriever and ClickHouse chapters; and distributed tracing internals (Shkuro). The Google SRE resources page (sre.google/resources) links the canonical SLO reading list.

## Recommendations

1. Do Stage 0 this week and keep that Compose stack forever as your experimentation sandbox, since every later exercise plugs into it. Do not skip it even though it feels trivial.
2. Sequence bottom-up, but let the Observation API be your through-line. When you reach Stage 3, refactor earlier hand-rolled metrics into `@Observed` and Observations so metrics, logs, and traces converge. This is the highest-leverage conceptual investment in the curriculum.
3. Treat cardinality as a first-class discipline from Stage 3 onward. Adopt the rule "low-cardinality on metrics and labels, high-cardinality on trace attributes and log bodies," and turn on the `HighCardinalityTagsDetector` in non-prod.
4. Buy two books and read the rest free. Purchase *Prometheus: Up & Running* 2nd ed. and *Observability Engineering* 2nd ed., and read the Google SRE books free at sre.google. Everything else (the Spring, Micrometer, Prometheus, Grafana, and OTel docs, plus the PromLabs cheat sheet) is primary and free.
5. Anchor advanced alerting on SLOs rather than thresholds. Implement one real multi-window burn-rate alert (Stage 6) before rolling standards out to other teams.
6. Version hygiene: target Spring Boot 4.1 for new work but keep your 3.x knowledge, prefer Grafana Alloy over the EOL Promtail, and confirm any older blog's metric names against current Micrometer (`http.server.requests` and so on).

**Benchmarks that change the plan:**
- If you're already fluent with Actuator and Micrometer, compress Stages 1 through 3 into about 3 weeks and spend the surplus on Stage 6 tracing and SLOs.
- If your org lacks any centralized metrics backend, prioritize Stage 4 (kube-prometheus-stack or Amazon Managed Prometheus) before deep PromQL.
- If Kafka trace continuity is your acute pain, pull the Kafka-propagation exercises from Stage 6 forward, right after Stage 3.

## Caveats
- This is a rapidly moving ecosystem. Spring Boot 4.x and Micrometer 2 are new (4.0 GA on Nov 20, 2025, and 4.1 on Jun 10, 2026), and some third-party dashboards and blog posts still assume 3.x and Micrometer 1.x metric names and property paths. Always cross-check against the versioned reference docs.
- Promtail is EOL as of March 2, 2026. Treat any Promtail-based tutorial as legacy and use Grafana Alloy, since the Grafana Loki docs explicitly state that all future log-collection development moves to Alloy.
- Community dashboards drift. 4701 (JVM Micrometer) is reliable, but the Spring Boot 2.x dashboards (10280 and 12464) partially break on 3.x. Verify panels against your actual metric names.
- Some cited third-party posts are vendor blogs (OneUptime, Last9, Grafana Labs, Honeycomb). They are excellent for patterns, but read them with awareness of product framing, and prefer the primary docs and books for canonical behavior.
- The Robust Perception blog, while canonical, has not been actively updated since around 2020. Its PromQL fundamentals remain valid, but check newer functions such as native histograms against the current Prometheus docs.
- A book-metadata caveat: some retailers erroneously list Charity Majors as a co-author of *Cloud-Native Observability with OpenTelemetry*, but the sole author is Alex Boten. *Learning OpenTelemetry* is variously dated 2023 or 2024 in metadata; the print edition is 2024.
