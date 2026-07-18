---
title: "A Graduated Mastery Curriculum for Spring Boot Monitoring & Observability (2026 Edition)"
category: "Spring & Spring Boot"
description: "A 6-stage, ~4–6 month graduated curriculum from a Docker-Compose quick tour (Actuator + Prometheus + Grafana) to source-level Actuator/Micrometer understanding and org-wide SLO-driven observability, anchored on the unifying Micrometer Observation API ('instrument once, get metrics + traces + logs'). Covers the Spring Boot 4.x era (GA Nov 2025, Micrometer 2, OpenTelemetry starter; 3.5 EOL June 2026), built-in structured logging since 3.4, cardinality as the recurring failure mode, and Promtail's EOL in favor of Grafana Alloy — tailored to a Kotlin stack with Kafka trace propagation, Aurora MySQL/HikariCP metrics, and EKS via kube-prometheus-stack with Loki/Tempo, sourced from the Actuator/Micrometer references, Google SRE books, Prometheus: Up & Running 2nd ed., and Observability Engineering 2nd ed."
---

# A Graduated Mastery Curriculum for Spring Boot Monitoring & Observability (2026 Edition)

**TL;DR**
- Build mastery in ~6 stages over ~4–6 months, moving from a Docker-Compose "quick tour" (Actuator + Prometheus + Grafana) to source-code-level understanding of Actuator/Micrometer and org-wide SLO-driven observability, anchored throughout on the unifying **Micrometer Observation API** ("instrument once, get metrics + traces + logs").
- Prioritize primary sources: the Spring Boot Actuator reference, Micrometer/Micrometer-Tracing docs, Prometheus/Grafana/OpenTelemetry docs, the Google SRE books (free at sre.google), *Prometheus: Up & Running* 2nd ed., and *Observability Engineering* 2nd ed., supplemented by Spring team talks (Jonatan Ivanov, Tommy Ludwig, Marcin Grzejszczak).
- Tailor every stage to your stack: Kotlin + Spring Boot 3.x/4.x, Kafka producer/consumer trace propagation, Aurora MySQL/HikariCP metrics, and EKS deployment via kube-prometheus-stack (ServiceMonitor/PodMonitor) with Loki/Tempo for logs and traces.

## Key Findings

**The version landscape you are learning against (July 2026).** Spring Boot 4.0 went GA on **November 20, 2025** (per Phil Webb's Spring blog announcement, "Spring Boot 4.0.0 available now") — built on Spring Framework 7, Jakarta EE 11, Micrometer 2, with an OpenTelemetry starter. **Spring Boot 4.1.0 is the latest stable release, published to Maven Central on June 10, 2026** (HeroDevs release tracker), and is the recommended target for new projects; note that the 3.5 line hit open-source EOL on June 30, 2026. Spring Boot 3.4 (November 2024) introduced **built-in structured logging** (ECS, Logstash, GELF) with no extra dependencies. Your curriculum must therefore treat two eras: 3.x resources are still overwhelmingly valid, but note that Micrometer moved to 2.x and Actuator's legacy JMX-oriented pieces were modernized in 4.x. Promtail reached end-of-life on **March 2, 2026** — new log-collection work should use **Grafana Alloy**, not Promtail.

**The conceptual spine is the Observation API.** Since Spring Boot 3 / Micrometer 1.10, the Observation API lets you instrument code once and emit metrics, traces, and logs from a single instrumentation point via `ObservationHandler`s. This is the single most important idea to internalize because it unifies all five of your required topics. Marcin Grzejszczak's "The Story of Micrometer Observation" (Dec 2025) documents how and why it was built.

**Cardinality is the recurring failure mode.** Across metrics (Micrometer tags), logs (Loki labels), and long-term storage costs, unbounded label/tag values are the number-one production hazard. Micrometer ships a `HighCardinalityTagsDetector`; the discipline of low-cardinality metric tags vs. high-cardinality trace attributes is a mastery-level skill.

## Details — The Curriculum

### Stage 0 — Quick Tour (get a stack running) · ~1 week (8–12 hrs)
**Objectives:** Stand up a working Kotlin/Spring Boot service exposing `/actuator/prometheus`, scraped by Prometheus, visualized in Grafana — all via Docker Compose — so you have a sandbox for every later stage.

**Key concepts:** the `spring-boot-starter-actuator` + `micrometer-registry-prometheus` dependency pair; `management.endpoints.web.exposure.include`; the Prometheus scrape model; importing a community Grafana dashboard.

**Hands-on:**
1. Generate a Kotlin Spring Boot 3.4+/4.x project on start.spring.io (Actuator, Web, Prometheus registry).
2. Docker Compose: your app + Prometheus + Grafana. Point Prometheus at `/actuator/prometheus`.
3. Import **Grafana dashboard 4701 (JVM Micrometer)**; for Spring Boot 3.x also try **19004 (Spring Boot 3.x Statistics)** and **17175 (Spring Boot Observability)**. Note that the older 10280/12464 dashboards were built for Spring Boot 2.x and some HTTP panels show "No data" on 3.x due to renamed metrics.
4. Set `management.metrics.tags.application=${spring.application.name}` so the 4701 dashboard's `application` variable works.

**Resources (canonical):** Spring Boot Actuator reference "Endpoints" page; the Grafana Labs "JVM (Micrometer)" dashboard page (4701). **Supplementary:** any current "Spring Boot + Prometheus + Grafana in 15 minutes" walkthrough (Baris.io, Tutorial Works) — use only for the Compose wiring, not concepts.

### Stage 1 — Actuator Deep Dive · ~2 weeks (15–20 hrs)
**Objectives:** Master every production-relevant endpoint, health indicators/groups, Kubernetes probes, custom endpoints/indicators, security/exposure, and the management port/context.

**Key concepts:**
- Endpoints: `health`, `info`, `metrics`, `env`, `configprops`, `loggers` (runtime log-level changes), `threaddump`, `heapdump`, `prometheus`, `beans`, `conditions`, `scheduledtasks`, `sbom`. By default only `health` is exposed over HTTP; `shutdown` is disabled; `/env`, `/configprops`, `/quartz` values are sanitized by default.
- Health indicators and **health groups**: configure `management.endpoint.health.group.readiness.include=...`; Actuator auto-configures `LivenessStateHealthIndicator` and `ReadinessStateHealthIndicator` from the `ApplicationAvailability` interface when in Kubernetes. Critical rule: the **liveness probe must not depend on external systems** (DB, Kafka, cache) or a dependency outage triggers mass pod restarts and cascading failure; readiness checks of externals must be chosen deliberately.
- Custom endpoints (`@Endpoint`, `@ReadOperation`/`@WriteOperation`/`@DeleteOperation`, `@WebEndpoint`, `@EndpointWebExtension`) and custom `HealthIndicator`/`ReactiveHealthIndicator`.
- Security: exposure vs. access; `EndpointRequest.toAnyEndpoint()` with Spring Security; CSRF interaction with POST endpoints; a **separate management port** (`management.server.port`) and base path (`management.endpoints.web.base-path`). This matters for EKS: expose Actuator on a management port not routed by your public Ingress.
- Internals: endpoints are auto-configured only when "available" (enabled + exposed); operations auto-expose over Spring MVC/WebFlux/Jersey.

**Hands-on (on your Kafka microservice):** add a custom `HealthIndicator` for Kafka consumer lag or Aurora connectivity (but keep it out of the liveness group); wire liveness/readiness probes into your EKS Deployment manifest; move Actuator to a dedicated management port; lock down exposure with Spring Security; use `loggers` to flip a package to DEBUG at runtime.

**Security caveat worth internalizing:** the December 2024 "We know where your car is" 38C3 talk about Volkswagen used an exposed Actuator as a gateway — treat Actuator exposure as a real attack surface.

**Resources (canonical):** Spring Boot Actuator reference — "Endpoints," "Health," and the Actuator REST API docs (versioned for 3.3/3.4/3.5/4.0/4.1); the InnoQ deep-dive series "Spring Boot Actuator Endpoints — What does 'production-ready' mean?" (2025). **Supplementary:** Baeldung "Spring Boot Actuator."

### Stage 2 — Logging & MDC · ~2 weeks (15–20 hrs)
**Objectives:** Master SLF4J/Logback MDC, structured JSON logging, correlation/trace-ID propagation into logs, the thread-pool/async/coroutine/reactive pitfalls specific to your Kotlin stack, and a Kubernetes log pipeline.

**Key concepts:**
- MDC fundamentals (SLF4J `MDC`, Logback `%X{...}` pattern conversion).
- **Structured logging in Spring Boot 3.4+**: `logging.structured.format.console=ecs|logstash|gelf`, service metadata properties, `StructuredLogFormatter` custom formats, the `JsonWriter` utility, and the fluent `LOGGER.atInfo().addKeyValue(...)` API. For pre-3.4 or advanced needs, `logstash-logback-encoder` remains the reference.
- Correlation IDs: when Micrometer Tracing is on the classpath, Spring Boot auto-populates `traceId`/`spanId` into MDC; use `logging.pattern.level` or a `logback-spring.xml` pattern with `%X{traceId:-} %X{spanId:-}`. (Note the migration detail: Sleuth used `%X{X-B3-TraceId}`; Micrometer Tracing uses `traceId`/`spanId`.)
- **Pitfalls — this is where your stack bites:** MDC is thread-local, so it is lost across thread-pool handoffs, `@Async`, `CompletableFuture`, reactive operators, and coroutine suspensions.
  - **Kotlin coroutines:** use `kotlinx-coroutines-slf4j`'s `MDCContext` element (`launch(MDCContext())`). Crucial gotcha from the official docs: you cannot mutate MDC *inside* a coroutine with `MDC.put` and expect it to survive suspension — updates are lost on the next suspension/resumption unless captured with `withContext(MDCContext())`.
  - **Reactive (WebFlux):** thread-locals don't follow the reactive chain; use Micrometer Context Propagation (`ContextRegistry`/`ContextSnapshot`) and Reactor's automatic context propagation. Spring Boot 4.1 also adds async context propagation for `@Async`.
- Log pipeline on Kubernetes: JSON stdout → node agent → store. Prefer **Grafana Loki** (indexes labels, not full text — 10–100× cheaper than Elasticsearch) with **Grafana Alloy** as the agent (Promtail is EOL as of March 2, 2026), or the ELK/EFK stack. Golden rule mirrors metrics: keep high-cardinality values (request IDs, user IDs) in the log *body*, not in Loki labels.

**Hands-on:** enable ECS JSON logging; add a `OncePerRequestFilter` (and a Kafka `RecordInterceptor`/consumer wrapper) that seeds a correlation ID into MDC; write a coroutine-based flow that correctly propagates MDC via `MDCContext`; deploy Loki + Alloy on EKS and confirm you can pivot from a Grafana log line's `traceId` to a trace.

**Resources (canonical):** Spring Boot reference "Structured logging" + the Spring Blog "Structured logging in Spring Boot 3.4"; `kotlinx-coroutines-slf4j` `MDCContext` API docs and source; Grafana Loki "Get started" + Alloy migration docs. **Supplementary:** Baeldung structured-logging article; logstash-logback-encoder GitHub.

### Stage 3 — Metrics with Micrometer · ~3 weeks (20–25 hrs)
**Objectives:** Master Micrometer as the metrics facade — meter types, tags/cardinality, `MeterRegistry`, percentiles vs. histograms, built-in instrumentation, custom metrics, and the Observation API that unifies everything.

**Key concepts:**
- Meter types: `Counter`, `Gauge`, `Timer`, `DistributionSummary`, `LongTaskTimer`, `FunctionCounter`/`FunctionTimer`.
- `MeterRegistry` model: `SimpleMeterRegistry`, `CompositeMeterRegistry`, `Metrics.globalRegistry`; `MeterRegistryCustomizer` for common tags; **`MeterFilter`** (deny/accept, transform IDs, configure distribution statistics, `ignoreTags`/`renameTag` to defuse cardinality).
- **Tags & cardinality:** dimensional tags become Prometheus labels; every distinct combination is a new time series. Store `Meter` instances in fields; never put unbounded values (user IDs, request IDs, raw URLs) in tags. Use the `HighCardinalityTagsDetector`.
- **Percentiles vs. histograms:** client-side pre-computed percentiles (`percentiles = {0.5,0.95,0.99}`) cannot be aggregated across instances; **percentile histograms** (`percentiles-histogram`, emitting `_bucket` series) can be aggregated server-side via `histogram_quantile()` in PromQL — prefer histograms for SLOs and multi-instance services. Configure per-meter `slo`/service-level boundaries.
- Built-in instrumentation to study: JVM (memory/GC/threads), `process_*`, HikariCP (Aurora connection pool), Tomcat/Netty, Spring MVC/WebFlux (`http.server.requests`), **Spring Kafka** (`KafkaTemplate`/listener containers with `setObservationEnabled(true)`), Lettuce/Redis, JPA/Hibernate.
- **Observation API:** `ObservationRegistry`, `Observation`, `@Observed` (needs `aspectjweaver` + `management.observations.annotations.enabled=true`), `ObservationConvention`, `ObservationPredicate`/`ObservationFilter`, low- vs. high-cardinality key-values, `DefaultMeterObservationHandler`. Spring Boot 4.0 added `@MeterTag` on `@Counted`/`@Timed` and `@ObservationKeyValue` support.

**Hands-on:** instrument an order/payment flow with a `Counter` (orders by status/region — bounded tags) and a `Timer` with a percentile histogram; add a `Gauge` for a queue depth; convert one hand-rolled `Timer` to `@Observed` and observe metrics + spans + logs from the single instrumentation; enable Spring Kafka observation; add a `MeterFilter` that caps cardinality; write a unit test with `SimpleMeterRegistry`.

**Resources (canonical):** Micrometer reference docs (Concepts: Registry, Meter Filters, High Cardinality Tags Detector); Spring Boot reference "Metrics" + "Observability"; the founding Spring Blog "Micrometer: Spring Boot 2's new application metrics collector" (2018, still the best conceptual origin story); "Observability with Spring Boot 3" (Spring Blog, 2022). **Talks:** Ivanov & Ludwig "Micrometer Mastery: Unleash Advanced Observability in your JVM Apps" (Spring I/O 2024, slides on Speaker Deck + YouTube). **Supplementary:** Baeldung "Observability with Spring Boot"; Reflectoring/Tutorial Works custom-metrics articles.

### Stage 4 — Prometheus & PromQL · ~3 weeks (20–30 hrs)
**Objectives:** Master the exposition format, scrape model, PromQL from basics to advanced, Prometheus on Kubernetes via the Operator, alerting, and long-term storage.

**Key concepts:**
- Exposition/OpenMetrics format; pull model + scrape config; `Pushgateway` for batch jobs (and why push is the exception).
- **PromQL:** instant vs. range vectors; selectors and matchers; `rate`/`irate`/`increase`; aggregation operators (`sum`, `avg`, `max`, `by`/`without`); `histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket[5m])) by (le))`; binary operators, `group_left`; recording rules; native histograms (newer, sparse/exponential buckets).
- **Prometheus on Kubernetes:** the **Prometheus Operator** and **kube-prometheus-stack** Helm chart (Prometheus, Alertmanager, Grafana, node-exporter, kube-state-metrics). CRDs: `ServiceMonitor`, `PodMonitor`, `Probe`, `ScrapeConfig`, `PrometheusRule`. Critical gotcha: the operator's `serviceMonitorSelector` defaults to matching the `release: <helm-name>` label — a `ServiceMonitor` without the matching label is silently ignored; and `serviceMonitorSelectorNilUsesHelmValues=false` is often needed to pick up all monitors.
- Alerting: `PrometheusRule` alerting rules + **Alertmanager** (routing, grouping, silencing, receivers). Alert on **symptoms** (RED metrics), not causes.
- **Long-term storage:** Prometheus TSDB defaults to **15-day retention** (per the official Prometheus "Storage" docs: if neither `--storage.tsdb.retention.time` nor `storage.tsdb.retention.size` is set, retention defaults to `15d`). Options: **Thanos** (sidecar keeps Prometheus as source of truth — lowest-friction add-on), **Grafana Mimir** (horizontally scalable, multi-tenant, remote-write backend; Mimir 3.0 added Kafka-based ingestion), and **Amazon Managed Service for Prometheus (AMP)** — the natural EKS choice via remote-write. VictoriaMetrics is a common simplicity/compression alternative.

**Hands-on (on EKS):** install kube-prometheus-stack via Helm; write a `ServiceMonitor` targeting `/actuator/prometheus` with correct labels; write PromQL for RED metrics on `http_server_requests_seconds`; create a recording rule and a burn-rate alert; wire remote-write to Amazon Managed Prometheus and confirm cross-cluster query.

**Resources (canonical):** the official Prometheus docs — querying overview (`/docs/prometheus/latest/querying/`), PromQL basics (`/querying/basics/`), operators (`/querying/operators/`), functions (`/querying/functions/`); practices pages on naming (`/docs/practices/naming/`), histograms/summaries (`/docs/practices/histograms/`), and instrumentation (`/docs/practices/instrumentation/`); the Prometheus Operator docs (getting-started, ServiceMonitor/PodMonitor) and kube-prometheus-stack chart. **Book:** *Prometheus: Up & Running*, 2nd ed. (Julien Pivotto & Brian Brazil, O'Reilly, 2023) — the canonical text; the 2nd edition adds new PromQL functions, service discovery providers, a dedicated TLS/security chapter, and new Alertmanager receivers. **PromQL learning:** the **PromLabs PromQL Cheat Sheet** (promlabs.com/promql-cheat-sheet — free, by PromQL creator Julius Volz), the PromLabs "Understanding PromQL" / "Introduction to Prometheus" training courses (training.promlabs.com), and the **Robust Perception "Reliable Insights" blog** by Brian Brazil (robustperception.io/blog — canonical, though not actively updated since ~2020). **AWS:** Amazon Managed Service for Prometheus docs.

### Stage 5 — Grafana, Dashboards & Visualization · ~2 weeks (15 hrs)
**Objectives:** Build and provision dashboards for Spring Boot/JVM/Kafka services, apply RED/USE/golden-signals design methods, use variables/templating, and set up Grafana alerting.

**Key concepts:**
- **Design methods:** **RED** (Rate, Errors, Duration — service/request-centric, good for alerting/SLAs, popularized by Tom Wilkie of Grafana Labs), **USE** (Utilization, Saturation, Errors — resource-centric, from Brendan Gregg), and Google's **Four Golden Signals** (RED + Saturation). "USE tells you how happy your machines are; RED tells you how happy your users are."
- Grafana best practices: dashboards with a purpose and a narrative (general→specific, Z-pattern layout); consistent color semantics; normalized axes; variables/templating (`$application`, `$instance`); avoid over-frequent refresh; document panels; no editing in the browser — test in a separate instance.
- **Dashboards as code / provisioning:** provision dashboards + data sources via config files/ConfigMaps (GitOps with ArgoCD/Flux); generate dashboards programmatically (e.g., Grafonnet/grafanalib) for consistency at scale.
- Grafana alerting (unified alerting, contact points, notification policies).

**Hands-on:** import 4701 as a baseline, then build a hand-crafted RED dashboard for one Kafka microservice (request rate, error %, p50/p95/p99 from histograms) plus a HikariCP/Aurora pool row and a Kafka consumer-lag row; templatize by `application`/`instance`; provision the dashboard as a ConfigMap in your EKS monitoring namespace; add a Grafana alert on p99 latency.

**Resources (canonical):** Grafana docs — "Best practices for dashboards," "Getting started… best practices to design your first dashboard," provisioning, and variables/templating; Tom Wilkie "The RED Method" (Grafana blog + GrafanaCon slides). **Supplementary:** the "JVM (Micrometer)" (4701) and "Spring Boot Observability" (25359) dashboard pages.

### Stage 6 — Advanced: Tracing, the Three Pillars, SLOs, Production Operations · ~4 weeks (25–35 hrs)
**Objectives:** Add distributed tracing across HTTP and Kafka, unify the three pillars, adopt SLO/error-budget-driven alerting, understand exemplars, and reason about the OpenTelemetry-vs-Micrometer tradeoff and instrumentation cost.

**Key concepts:**
- **Micrometer Tracing + OpenTelemetry:** add `micrometer-tracing-bridge-otel` + `opentelemetry-exporter-otlp` (or the Spring Boot 4 `spring-boot-starter-opentelemetry`); export via OTLP to **Tempo/Jaeger/Zipkin**. W3C Trace Context (`traceparent`) is the default propagation. Per the Spring Boot reference "Tracing" doc, **Spring Boot by default samples only 10% of requests** to avoid overwhelming the backend; configure with `management.tracing.sampling.probability` (set `1.0` in dev).
- **Kafka context propagation:** Spring Kafka injects/extracts trace context in record headers when observation is enabled (`KafkaTemplate.setObservationEnabled(true)` and `containerProperties.setObservationEnabled(true)`), producing linked PRODUCER/CONSUMER spans. Watch the async gotcha: when you hand off to `CompletableFuture.runAsync`, capture context with `ContextSnapshot.captureAll()` and restore via `setThreadLocals()`.
- **Three pillars & unification:** logs (what), metrics (context/how much), traces (why) — unified under Observations.
- **Exemplars:** attach a representative `traceId` to histogram buckets so you can jump from a p99 latency spike in Grafana straight to the exact trace in Tempo. Requires exemplar storage enabled in Prometheus (`--enable-feature=exemplar-storage`) and OpenMetrics exposition; Tempo's metrics-generator can also produce RED span-metrics and exemplars via remote-write.
- **SLOs & error budgets (SRE):** SLI ≤ target; error budget = 1 − SLO; multi-window multi-burn-rate alerting (e.g., page at 14.4× burn / ~2 days, ticket at 6× / ~5 days) from SRE Workbook chapter 5; error-budget policy gates releases. This is the philosophy that should drive your alerting, replacing threshold-spam.
- **OTel vs. Micrometer tradeoff:** in the Spring ecosystem, Micrometer is the recommended metrics path (export via `OtlpMeterRegistry` if you want OTLP; Spring Boot does not provide an OpenTelemetry `SdkMeterProvider`), while tracing bridges to OTel. Instrument once with Observations and stay backend-neutral. Alternatively the OTel Java agent auto-instruments with zero code — understand the tradeoffs (agent breadth/overhead vs. Micrometer's first-class Spring integration).
- **Cost/performance of instrumentation:** cardinality explosions, sampling strategy (head vs. tail), histogram bucket counts, and telemetry volume all have real CPU/storage cost.

**Hands-on:** enable end-to-end tracing across your order-service (HTTP) → Kafka → payment-service (consumer) → Aurora, viewed in Tempo; turn on exemplars and pivot metric→trace in Grafana; define an SLO + error-budget policy for one service and implement multi-window burn-rate alerts; run the OTel Java agent against one service and compare with the Micrometer-native service.

**Resources (canonical):** Spring Boot reference "Observability" + "Tracing"; Micrometer Tracing reference; OpenTelemetry docs (OTLP, Java); Grafana Tempo docs (metrics-from-traces, exemplars); the Google **SRE Book** (2016) and **SRE Workbook** (2018) — free at sre.google/books — especially "Service Level Objectives," "Embracing Risk," and Workbook chapters 2 & 5. **Talks/posts:** Spring Blog "Observability with Spring Boot 3"; Marcin Grzejszczak "The Story of Micrometer Observation"; Piotr Minkowski "Kafka Tracing with Spring Boot and OpenTelemetry." **Books (advanced):** *Observability Engineering* 2nd ed. (Majors, Fong-Jones, Miranda with Austin Parker, O'Reilly, released June 2026 — nearly a full rewrite, ~600 pages); *Learning OpenTelemetry* (Ted Young & Austin Parker, O'Reilly, 2024); *Mastering Distributed Tracing* (Yuri Shkuro, creator of Jaeger, Packt, 2019); *Cloud-Native Observability with OpenTelemetry* (Alex Boten, Packt, 2022); *Cloud Observability in Action* (Michael Hausenblas, Manning, 2023).

### Mastery Capstone & "Going Deeper" · ongoing
**Objectives:** Source-code-level understanding, contribution, and org-wide standards.

- **Source reading:** Actuator auto-configuration (`spring-boot-actuate-autoconfigure`), `MeterRegistry`/`HighCardinalityTagsDetector`, and the `micrometer-observation` module (small, near-zero dependencies by design — read Grzejszczak's article on *why* it was kept dependency-light so Spring Framework could put it on the classpath). Study the `spring-projects/spring-boot` docs source on GitHub for versioned Actuator behavior.
- **Contribution:** file/fix issues against Micrometer or sample repos; write an `ObservationDocumentation` enum and generate docs with Micrometer Docs Generator.
- **Org-wide standards:** define naming conventions, common tags, `ObservationConvention`s, dashboard templates-as-code, and an error-budget policy as shared libraries; drive SLO-based alerting across teams.
- **Deeper theory:** PromQL internals and TSDB storage (*Prometheus: Up & Running* 2nd ed. + Prometheus docs on native histograms/storage); *Observability Engineering*'s chapters on high-cardinality data stores (e.g., the Honeycomb Retriever / ClickHouse chapters); distributed tracing internals (Shkuro). The Google SRE resources page (sre.google/resources) links the canonical SLO reading list.

## Recommendations

1. **Do Stage 0 this week and keep that Compose stack forever** as your experimentation sandbox — every later exercise plugs into it. Do not skip it even though it feels trivial.
2. **Sequence bottom-up but let the Observation API be your through-line.** When you reach Stage 3, refactor earlier hand-rolled metrics into `@Observed`/Observations so metrics, logs, and traces converge — this is the highest-leverage conceptual investment.
3. **Treat cardinality as a first-class discipline from Stage 3 onward.** Adopt the rule "low-cardinality on metrics/labels, high-cardinality on trace attributes/log bodies" and turn on the `HighCardinalityTagsDetector` in non-prod.
4. **Buy two books, read the rest free.** Purchase *Prometheus: Up & Running* 2nd ed. and *Observability Engineering* 2nd ed.; read the Google SRE books free at sre.google. Everything else (Spring/Micrometer/Prometheus/Grafana/OTel docs, PromLabs cheat sheet) is primary and free.
5. **Anchor advanced alerting on SLOs, not thresholds.** Implement one real multi-window burn-rate alert (Stage 6) before rolling standards to other teams.
6. **Version hygiene:** target Spring Boot 4.1 for new work but keep 3.x knowledge; prefer Grafana Alloy over Promtail (EOL); confirm any older blog's metric names against current Micrometer (`http.server.requests` etc.).

**Benchmarks that change the plan:**
- If you're already fluent with Actuator/Micrometer, compress Stages 1–3 into ~3 weeks and spend the surplus on Stage 6 tracing + SLOs.
- If your org lacks any centralized metrics backend, prioritize Stage 4 (kube-prometheus-stack or Amazon Managed Prometheus) before deep PromQL.
- If Kafka trace continuity is your acute pain, jump the Kafka-propagation exercises from Stage 6 forward right after Stage 3.

## Caveats
- **Rapidly moving ecosystem.** Spring Boot 4.x/Micrometer 2 are new (4.0 GA Nov 20, 2025; 4.1 Jun 10, 2026); some third-party dashboards and blog posts still assume 3.x/Micrometer 1.x metric names and property paths. Always cross-check against the versioned reference docs.
- **Promtail is EOL (March 2, 2026)** — treat any Promtail-based tutorial as legacy and use Grafana Alloy (the Grafana Loki docs explicitly state all future log-collection development moves to Alloy).
- **Community dashboards drift.** 4701 (JVM Micrometer) is reliable; Spring Boot 2.x dashboards (10280/12464) partially break on 3.x. Verify panels against your actual metric names.
- **Some cited third-party posts are vendor blogs** (OneUptime, Last9, Grafana Labs, Honeycomb) — excellent for patterns but read with awareness of product framing; prefer the primary docs and books for canonical behavior.
- **The Robust Perception blog, while canonical, has not been actively updated since ~2020** — its PromQL fundamentals remain valid but check newer functions (native histograms) against current Prometheus docs.
- **Book-metadata caveat:** some retailers erroneously list Charity Majors as a co-author of *Cloud-Native Observability with OpenTelemetry*; the sole author is Alex Boten. *Learning OpenTelemetry* is variously dated 2023/2024 in metadata — the print edition is 2024.