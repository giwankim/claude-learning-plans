---
title: "OpenTelemetry for Spring Boot in Kotlin"
category: "Observability"
description: "12-16 week mastery plan for OpenTelemetry with Spring Boot covering metrics, traces, logs, OTel Collector, Datadog, and Grafana stack on EKS"
---

# Mastery learning plan: OpenTelemetry for Spring Boot in Kotlin

**OpenTelemetry transforms your Spring Boot microservices from opaque black boxes into fully transparent systems** by unifying metrics, distributed traces, and structured logs under a single vendor-neutral framework. This guide takes you from zero observability knowledge to production-grade implementations across Datadog, the Grafana stack, and backend-agnostic OTel Collector architectures — all tailored to your Kotlin/Spring Boot/EKS stack. The learning path is structured in seven phases, each building on the last, with milestone projects that produce deployable artifacts. Expect roughly **12–16 weeks** at 8–10 hours per week to reach production readiness.

---

## Phase 1: Foundations — understanding what you're building and why

Before touching any code, you need a mental model of observability that goes beyond "add logging." This phase builds the conceptual architecture that every subsequent phase depends on.

### The three signals, not three pillars

The traditional framing calls metrics, traces, and logs the "three pillars of observability." Modern thinking — championed by OpenTelemetry's own documentation and Honeycomb's engineering team — reframes these as **three signals** that must be correlated, not treated as independent silos. The real value emerges when a latency spike in your metrics links directly to a specific trace, which links to the exact log lines from that request.

**Metrics** are numerical measurements captured at intervals — CPU usage, request latency histograms, error rates. They're optimized for aggregation, alerting, and trend analysis. They answer "what is happening right now?" **Distributed traces** record the full journey of a request across your microservices as a tree of **spans**, each representing a unit of work with timestamps, attributes, and parent-child relationships. They answer "where is this request slow, and why?" **Structured logs** are timestamped event records — and when enriched with trace IDs, they become searchable context for specific spans. They answer "what happened during this operation?"

OpenTelemetry adds a fourth emerging signal: **continuous profiling** (contributed by Elastic), which provides stack-trace-level performance analysis. This is still in development in the OTel Java SDK and not production-critical yet, but worth knowing about.

### OpenTelemetry architecture

OpenTelemetry is a **CNCF incubating project** born from the 2019 merger of OpenTracing (a tracing-only API specification) and OpenCensus (Google's tracing + metrics library). This merger resolved the ecosystem fragmentation that plagued distributed tracing adoption. OpenCensus was archived in July 2023; OpenTracing is in maintenance mode.

The architecture has four core components you'll work with directly:

- **API** (`io.opentelemetry:opentelemetry-api`): Interfaces for recording telemetry. Libraries and frameworks depend on this — it has zero transitive dependencies and strong backward compatibility. Provides `TracerProvider`, `MeterProvider`, and `LoggerProvider`.
- **SDK** (`io.opentelemetry:opentelemetry-sdk`): The reference implementation that processes and exports telemetry. Contains samplers, span processors, metric readers, and exporters. This is where configuration happens.
- **OTLP protocol**: The standard wire format for telemetry data. Stable for all three signals. Supports gRPC (port **4317**) and HTTP/protobuf (port **4318**). Every major backend now accepts OTLP natively.
- **Collector**: A standalone service that receives, processes, and exports telemetry. It acts as a central routing hub with receivers, processors, and exporters — enabling vendor-agnostic pipelines.

As of March 2026, the **OTel Java SDK is at v1.60.1** with all three signals (traces, metrics, logs) fully stable. The Java auto-instrumentation agent covers **150+ libraries** out of the box.

### How Spring Boot 3.x connects to OpenTelemetry

This is where many developers get confused, because Spring Boot doesn't use OTel directly — it uses **Micrometer** as its observability abstraction layer. Understanding this layering is critical:

```
Your Kotlin Code → Micrometer Observation API → ObservationHandler (Tracing) → micrometer-tracing-bridge-otel → OTel SDK → OTLP → Backend
                                               → ObservationHandler (Metrics) → Micrometer Registry → Prometheus/OTLP → Backend
                                               → ObservationHandler (Logging) → SLF4J/Logback → Backend
```

Spring Boot 3.x deprecated Spring Cloud Sleuth and migrated its tracing to **Micrometer Tracing**. The **Micrometer Observation API** is a higher-level abstraction that produces both metrics and traces from a single instrumentation point. A single `@Observed` annotation on your Kotlin method automatically creates a timer metric and a trace span. The `micrometer-tracing-bridge-otel` dependency bridges Micrometer's tracer facade to the OTel SDK, which exports via OTLP.

Spring Boot 4.0 (GA November 2025) introduced `spring-boot-starter-opentelemetry` as a single dependency that bundles this entire stack. If you're on Spring Boot 3.x, you'll configure these dependencies individually — the learning plan covers both paths.

### Three instrumentation approaches compared

You have three paths to instrument your Spring Boot services, and understanding when to use each is essential:

**OTel Java Agent** (`-javaagent:opentelemetry-javaagent.jar`): Zero code changes. Bytecode instrumentation at JVM startup covers HTTP, JDBC, Kafka, Redis, and 150+ other libraries automatically. Configuration via `OTEL_*` environment variables. Broadest coverage but incompatible with GraalVM native images and adds **2–5% CPU overhead** with **50–100MB additional heap**. The v2 agent no longer auto-traces Spring-annotated methods — you must use `@WithSpan` explicitly.

**Micrometer Observation API with OTel bridge** (Spring Boot's recommended approach): Uses Spring's native observability. Single observation produces both metrics and traces. Works with GraalVM. Configuration via `application.yml` using `management.*` properties. Narrower automatic scope than the agent but deeply integrated with Spring's ecosystem.

**OTel Spring Boot Starter** (`io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter`): A third-party starter from the OTel project. More instrumentation than Micrometer-only, less than the agent. Uses `otel.*` property prefix. Recommended by the OTel project when the agent can't be used.

For production microservices, **the Java Agent is often the pragmatic choice** for initial adoption because it requires zero code changes and covers your entire library stack including Kafka, Redis, and JDBC immediately. As you mature, supplement with Micrometer Observation API for custom business metrics and spans.

### Milestone project 1

Set up a local development environment with a single Spring Boot Kotlin service. Instrument it using the OTel Java Agent, export traces to a local Jaeger instance via Docker, and explore the Jaeger UI to see your first traces. Then switch to the Micrometer bridge approach and compare the differences.

### Phase 1 resources

| Resource | Type | Why it matters |
|----------|------|----------------|
| *Learning OpenTelemetry* by Ted Young & Austin Parker (O'Reilly, 2024) | Book | **The** definitive OTel book, written by project co-founders. Covers architecture, Collector pipelines, and organizational adoption. |
| *Observability Engineering* by Charity Majors, Liz Fong-Jones, George Miranda (O'Reilly, 2022; 2nd ed. coming 2026) | Book | Foundational text on observability philosophy, SLOs, and debugging methodology. Free download at honeycomb.io. |
| Linux Foundation LFS148: Getting Started with OpenTelemetry | Free course (~10h) | Official CNCF course with Java labs. Best free starting point. https://training.linuxfoundation.org/training/getting-started-with-opentelemetry-lfs148/ |
| Spring Blog: "OpenTelemetry with Spring Boot" (Nov 2025) | Blog post | Official Spring team post covering all three integration paths. https://spring.io/blog/2025/11/18/opentelemetry-with-spring-boot/ |
| OTel Java docs | Documentation | https://opentelemetry.io/docs/languages/java/ |
| Spring Boot Observability docs | Documentation | https://docs.spring.io/spring-boot/reference/actuator/observability.html |

---

## Phase 2: Metrics — measuring everything that matters

Metrics are the most immediately useful signal because they power dashboards and alerting. You already have Spring Boot Actuator exposing JVM metrics; this phase teaches you to export them via OTel and create custom business metrics.

### Micrometer fundamentals for Kotlin

Micrometer is to metrics what SLF4J is to logging — a facade with pluggable backends. Spring Boot auto-configures a `MeterRegistry` bean. The four core instrument types you'll use daily:

**Counter** for monotonically increasing values (orders placed, errors). **Gauge** for point-in-time values (queue depth, active connections). **Timer** for latency distributions (request duration, query time). **DistributionSummary** for value distributions (payload sizes, batch sizes).

In Kotlin, custom metrics look natural:

```kotlin
@Service
class OrderService(private val meterRegistry: MeterRegistry) {
    private val orderCounter = Counter.builder("orders.placed")
        .description("Total orders placed")
        .tag("channel", "api")
        .register(meterRegistry)

    private val processingTimer = Timer.builder("order.processing.duration")
        .description("Order processing time")
        .publishPercentiles(0.5, 0.95, 0.99)
        .register(meterRegistry)

    fun placeOrder(order: Order): OrderResult = processingTimer.record {
        orderCounter.increment()
        // business logic
    }!!
}
```

### Exporting to three backends

**Prometheus** (pull model): Add `micrometer-registry-prometheus`, expose `/actuator/prometheus`, and configure Prometheus to scrape your service. This is the simplest path and works immediately with Grafana.

**Datadog** (push model): Add `micrometer-registry-datadog` with your API key. Be aware that **all Micrometer custom metrics count as custom metrics in Datadog**, which directly affects billing at $0.05/metric/month. High-cardinality tags (user IDs, session IDs) multiply this explosively.

**OTLP** (push model, backend-agnostic): Add `micrometer-registry-otlp` and point to your OTel Collector at `http://collector:4318/v1/metrics`. This is the vendor-neutral approach — the Collector then routes to any backend.

```yaml
# application.yml — OTLP metrics export
management:
  otlp:
    metrics:
      export:
        url: http://localhost:4318/v1/metrics
        step: 30s
  endpoints:
    web:
      exposure:
        include: health,prometheus,metrics
```

### Milestone project 2

Extend your service with three custom business metrics (a counter, timer, and gauge). Export metrics via the Prometheus endpoint and build a basic Grafana dashboard showing RED metrics (Rate, Errors, Duration) plus JVM health. Grafana dashboard ID **17175** (Spring Boot Observability) is an excellent starting template.

---

## Phase 3: Distributed tracing — following requests across services

Tracing is where observability becomes transformational for microservices debugging. A single trace shows you exactly which service in your chain added 200ms of latency.

### Core concepts

A **trace** is the end-to-end journey of a request, identified by a unique **trace ID** (128-bit hex string). Each service creates one or more **spans** — atomic units of work with a name, start/end timestamps, attributes (key-value metadata), events, and status. Spans form parent-child trees. **Context propagation** carries trace/span IDs across service boundaries via HTTP headers (W3C `traceparent` by default) or Kafka message headers.

### Auto-instrumentation coverage for your stack

The OTel Java Agent automatically instruments every technology in your architecture:

| Technology | What's captured | Notes |
|-----------|----------------|-------|
| Spring Web/WebFlux | Inbound HTTP spans with route, method, status | Automatic with agent |
| RestClient/RestTemplate | Outbound HTTP spans | Must use Spring-managed builder for Micrometer approach |
| JDBC (Aurora MySQL/PostgreSQL) | Database query spans with SQL statement, operation | Via `opentelemetry-jdbc` |
| Redis (Lettuce) | Command spans with operation type | Auto-detected |
| Kafka producer/consumer | PRODUCER and CONSUMER spans with topic, partition | Context propagated via message headers |
| R2DBC | Reactive database query spans | Supported since OTel Agent 2.x |

For Kafka, context propagation works by injecting W3C `traceparent` into Kafka record headers on the producer side and extracting on the consumer side. **Important**: Kafka consumer spans link to producer spans rather than creating parent-child relationships, since the operations are asynchronous. Enable observation in Spring Kafka:

```yaml
spring:
  kafka:
    listener:
      observation-enabled: true
    template:
      observation-enabled: true
```

### Custom spans in Kotlin

For business logic that isn't auto-instrumented, use the `@WithSpan` annotation or the Tracer API:

```kotlin
@Service
class PaymentService {
    @WithSpan("payment.process")
    fun processPayment(
        @SpanAttribute("payment.id") paymentId: String,
        @SpanAttribute("payment.amount") amount: Double
    ): PaymentResult {
        val currentSpan = Span.current()
        currentSpan.addEvent("Validation started")
        currentSpan.setAttribute("payment.method", "credit_card")
        return executePayment(paymentId, amount)
    }
}
```

For **Kotlin coroutines**, you must explicitly propagate OTel context across coroutine boundaries since context is thread-local by default. Use a custom `CoroutineContext` element or the `kotlinx-coroutines-extensions` from the OTel SDK to bridge OTel context into the coroutine dispatcher.

### Trace exporters

Jaeger now accepts OTLP natively — no Jaeger-specific libraries needed. Grafana Tempo accepts OTLP on ports 4317/4318. Datadog accepts traces via the OTel Collector with the Datadog exporter or via the Datadog Agent's OTLP ingestion mode (agents 6.48.0+/7.48.0+).

### Milestone project 3

Build a three-service chain (Order → Payment → Notification) communicating via REST and Kafka. Instrument with the OTel Java Agent. Export traces to Tempo and view the full distributed trace in Grafana. Add custom `@WithSpan` annotations to key business methods and verify they appear as child spans.

---

## Phase 4: Structured logging — connecting logs to traces

Logs become dramatically more useful when every log line carries the trace ID of the request that generated it. This phase adds JSON-structured logging with automatic trace correlation.

### Logback structured logging setup

Replace default console logging with JSON output using `logstash-logback-encoder`. When Micrometer Tracing is on the classpath, Spring Boot automatically injects `trace_id` and `span_id` into the MDC (Mapped Diagnostic Context), which means every log line automatically carries trace context.

```xml
<!-- logback-spring.xml -->
<configuration>
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <includeMdcKeyName>trace_id</includeMdcKeyName>
            <includeMdcKeyName>span_id</includeMdcKeyName>
            <includeMdcKeyName>trace_flags</includeMdcKeyName>
        </encoder>
    </appender>
    <root level="INFO">
        <appender-ref ref="CONSOLE"/>
    </root>
</configuration>
```

This produces log lines like:
```json
{"@timestamp":"2026-03-12T10:15:30.123Z","level":"INFO","message":"Order created","trace_id":"abc123...","span_id":"def456...","service":"order-service"}
```

### Shipping logs via OTel

You have two paths for log export. The first is the **OTel Logback Appender** (`opentelemetry-logback-appender-1.0`), which sends logs directly to the OTel Collector via OTLP. The second is the traditional approach of writing JSON logs to stdout and having the OTel Collector's `filelog` receiver tail them — this is more common in Kubernetes where container logs are already collected.

For the OTel appender approach, add it to your `logback-spring.xml` and wire it to the `OpenTelemetry` bean:

```kotlin
@Component
class InstallOpenTelemetryAppender(
    private val openTelemetry: OpenTelemetry
) : InitializingBean {
    override fun afterPropertiesSet() {
        OpenTelemetryAppender.install(openTelemetry)
    }
}
```

Grafana Loki accepts OTLP natively at `http://loki:3100/otlp`. In Grafana, configure the Loki data source with a derived field that links `trace_id` labels to Tempo — enabling one-click navigation from a log line to its full distributed trace.

### Milestone project 4

Add structured JSON logging to all three services. Configure Grafana Loki to receive logs and set up cross-signal correlation: click a trace in Tempo → see associated logs in Loki; click a metric exemplar in Prometheus → jump to the trace. This cross-signal linking is the moment observability "clicks."

---

## Phase 5: The OTel Collector — your telemetry control plane

The Collector is the most important operational component in your observability architecture. It decouples your applications from backends, enabling filtering, sampling, enrichment, and routing without any application changes.

### Architecture

The Collector pipeline has four component types: **Receivers** ingest data (OTLP, Prometheus scrape, filelog, hostmetrics). **Processors** transform data (batch, memory_limiter, filter, attributes, tail_sampling, k8sattributes). **Exporters** send data to backends (OTLP, Prometheus, Datadog, Loki). **Connectors** bridge pipelines — the `spanmetrics` connector generates RED metrics from traces automatically.

Use the `otel/opentelemetry-collector-contrib` image for access to all community exporters including Datadog, Loki, and Prometheus.

### Multi-backend routing configuration

This is where the Collector's power becomes clear — a single configuration file routes all signals to every backend simultaneously:

```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: "0.0.0.0:4317" }
      http: { endpoint: "0.0.0.0:4318" }

processors:
  batch: { timeout: 5s, send_batch_size: 512 }
  memory_limiter: { check_interval: 5s, limit_percentage: 80, spike_limit_percentage: 25 }
  filter/healthchecks:
    traces:
      span:
        - 'attributes["http.route"] == "/health"'
        - 'attributes["http.route"] == "/ready"'

exporters:
  otlp/tempo: { endpoint: "tempo:4317", tls: { insecure: true } }
  otlphttp/loki: { endpoint: "http://loki:3100/otlp" }
  prometheus: { endpoint: "0.0.0.0:8889" }
  datadog: { api: { key: "${DD_API_KEY}", site: datadoghq.com } }

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, filter/healthchecks, batch]
      exporters: [otlp/tempo, datadog]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus, datadog]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp/loki, datadog]
```

The `type/name` format (e.g., `otlp/tempo`) enables multiple instances of the same exporter type. You can export traces to both Tempo and Datadog simultaneously while keeping logs only in Loki.

### Kubernetes deployment patterns

On EKS, deploy Collectors in a **two-tier architecture**: DaemonSet agents on every node (collecting pod telemetry, kubelet metrics, and container logs) forward to a Deployment-mode gateway (performing tail-based sampling, enrichment, and export to backends). Install via the official Helm chart:

```bash
helm install otel-collector open-telemetry/opentelemetry-collector \
  --set mode=daemonset \
  --set presets.kubernetesAttributes.enabled=true \
  --set presets.kubeletMetrics.enabled=true
```

The **OpenTelemetry Operator** manages Collector lifecycle and can inject auto-instrumentation into your pods via annotations — no Dockerfile changes needed:

```yaml
metadata:
  annotations:
    instrumentation.opentelemetry.io/inject-java: "true"
```

### Milestone project 5

Deploy the OTel Collector locally via Docker Compose, configured to receive OTLP from your three services and export simultaneously to Prometheus, Tempo, Loki, and (optionally) Datadog. Add the `filter` processor to drop health-check spans. Add the `spanmetrics` connector to generate RED metrics from traces.

---

## Phase 6: Backend integration — three production stacks

### The Grafana stack (Prometheus + Grafana + Tempo + Loki)

This is the open-source, cost-effective approach. Prometheus stores metrics, Tempo stores traces, Loki stores logs, and Grafana provides unified visualization with cross-signal correlation.

The critical configuration is Grafana's **data source provisioning** that links the three backends: Prometheus metrics include **exemplars** pointing to Tempo trace IDs; Loki log queries have **derived fields** linking `trace_id` to Tempo; Tempo traces link back to Loki logs and Prometheus service graphs. This creates the seamless correlation that makes observability work.

Grafana Tempo's **metrics-generator** creates RED metrics from incoming traces with automatic exemplar linkage — you can click from an aggregate latency percentile directly into a representative trace.

For production on EKS, consider **Grafana Cloud** (free tier: 10K metric series, 50GB logs, 50GB traces) or self-hosted using the **Grafana LGTM stack** (Loki + Grafana + Tempo + Mimir). Mimir replaces Prometheus for horizontally scalable, long-term metric storage.

### Datadog integration

Datadog offers three OTel integration paths, ranked by their recommendation:

The **DDOT Collector** (Datadog Distribution of OpenTelemetry) is built into the Datadog Agent and provides the richest integration including Fleet Automation and Network Monitoring. The **standalone OTel Collector** with the Datadog exporter from `collector-contrib` works well but requires separate management. The **Datadog Agent OTLP mode** (agents 6.48.0+) accepts OTLP directly.

Datadog uses **unified service tagging** (`service`, `env`, `version`) to correlate logs, traces, and metrics. Set these as resource attributes in your OTel configuration. Critical cost awareness: Datadog requires **delta aggregation temporality** for metrics (set `aggregationTemporality: delta`) and bills all OTel metrics as custom metrics.

### Backend-agnostic approach

The OTel Collector as universal hub is the most flexible architecture. Your applications export exclusively via OTLP to the Collector. Backend changes (migrating from Datadog to Grafana, or adding a second backend) require only Collector configuration changes — zero application modifications. This is the approach that pays dividends at organizational scale.

### Milestone project 6

Deploy your three-service system on a local Kubernetes cluster (kind or minikube). Set up the full Grafana stack with Helm. Build production-quality Grafana dashboards covering RED metrics per service, JVM health, Kafka consumer lag, and database query latency. Configure alerting rules for error rate > 1% and p99 latency > 2s. If you have Datadog access, configure dual export to both Grafana and Datadog simultaneously.

---

## Phase 7: Production operations — running observability at scale

### Sampling strategies that preserve signal

**Head-based sampling** (at the SDK level) makes the sampling decision before the trace completes. Use `ParentBased(TraceIdRatioBased(0.1))` as the production default — this samples 10% of root traces and respects parent decisions for consistency. **Tail-based sampling** (at the Collector level) waits for complete traces and keeps all errors and slow requests regardless of the probabilistic rate.

The production pattern is combining both: head-sample at 10–20% to protect your pipeline, then tail-sample at the Collector to retain 100% of error traces and latency outliers:

```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors-always
        type: status_code
        status_code: { status_codes: ["ERROR"] }
      - name: slow-traces
        type: latency
        latency: { threshold_ms: 2000 }
      - name: baseline
        type: probabilistic
        probabilistic: { sampling_percentage: 5 }
```

**Critical constraint**: all spans for a given trace must arrive at the same Collector instance for tail-based sampling. Use a load-balancing exporter (routing by trace ID) in front of the tail-sampling tier.

### Generating span metrics before sampling preserves accuracy

Generate RED metrics from **all** traces before sampling, not after. Sampled data produces skewed aggregate metrics. The OTel Collector's `spanmetrics` connector or Tempo's metrics-generator handles this — place it in the pipeline before the tail-sampling processor.

### Cost management

Observability costs can spiral without controls. The OTel Collector is your cost firewall — use `filter` processors to drop health-check and readiness-probe spans, `transform` processors to remove high-cardinality attributes (full URLs with query strings, user IDs in tags), and attribute trimming to remove verbose SQL statements from span attributes.

A mid-sized platform case study showed reduction from **$25K/month to $6.5K/month** by routing through the OTel Collector with aggressive filtering before Datadog export. For Grafana Cloud, **Adaptive Metrics** automatically eliminates unused time series through aggregation.

### SLIs, SLOs, and alerting

Define SLIs using the **RED method** for every service: **Rate** (requests/second), **Errors** (error percentage), and **Duration** (latency percentiles). These map directly to Micrometer's `http_server_requests_seconds_*` metrics.

A practical SLO example: "99.5% of requests complete within 2 seconds over a 30-day rolling window." Grafana's SLO application creates multi-window, multi-burn-rate alerting rules automatically — fast-burn alerts for immediate response, slow-burn for trend detection. This is far more actionable than naive threshold alerts.

### Infrastructure observability for your stack

Your EKS cluster needs three layers of Kubernetes metrics: **kubelet/cAdvisor** for container resource utilization (collected via OTel Collector's `kubeletstatsreceiver`), **kube-state-metrics** for desired-vs-actual state of Kubernetes objects, and **metrics-server** for HPA/VPA real-time scaling decisions.

For Aurora MySQL/PostgreSQL, the OTel Collector's `postgresqlreceiver` and `mysqlreceiver` scrape connection counts, query throughput, deadlocks, and replication lag directly. Redis observability comes from the `redisreceiver` (memory, connected clients, keyspace hits/misses) combined with auto-instrumented Lettuce command spans. Kafka observability requires the `kafkametricsreceiver` for consumer lag and broker health, plus the auto-instrumented producer/consumer spans that carry trace context across message boundaries.

Consider using **Kafka as a buffer** in your telemetry pipeline itself: OTel Collector exports to a Kafka topic, a downstream Collector reads via `kafkareceiver`. This decouples telemetry production from backend ingestion and handles traffic bursts gracefully.

### Milestone project 7

Configure tail-based sampling in the OTel Collector that retains 100% of errors and slow traces while sampling 5% of normal traffic. Define SLOs for your three services in Grafana (availability > 99.9%, latency p99 < 2s). Set up multi-burn-rate alerts that fire to a Slack channel. Add OTel Collector receivers for your Redis and database instances. Build a cluster-level Grafana dashboard showing pod resource utilization, Kafka consumer lag, and database connection pool health. Document the full architecture as a runbook for your team.

---

## Complete resource library

### Books (prioritized reading order)

| Book | Authors | Year | Best for |
|------|---------|------|----------|
| *Learning OpenTelemetry* | Ted Young & Austin Parker | 2024 | Definitive OTel architecture guide, by project co-founders |
| *Observability Engineering* (2nd ed.) | Charity Majors, Liz Fong-Jones, George Miranda | 2022/2026 | Philosophy, SLOs, organizational adoption. Free 1st ed. at honeycomb.io |
| *Practical OpenTelemetry* | Daniel Gomez Blanco | 2024 | Java-focused examples, closest to Spring Boot use case |
| *Mastering OpenTelemetry and Observability* | Steve Flanders | 2024 | Enterprise adoption, brownfield deployments |
| *Cloud-Native Observability with OpenTelemetry* | Alex Boten | 2022 | Solid conceptual foundation (Python examples, not Java) |
| *Distributed Tracing in Practice* | Austin Parker et al. | 2020 | Deep tracing concepts (pre-OTel maturity but still relevant) |

### Courses

| Course | Provider | Format | Notes |
|--------|----------|--------|-------|
| Getting Started with OpenTelemetry (LFS148) | Linux Foundation | Free, ~10h self-paced | Official CNCF course with Java labs. Best starting point. |
| OpenTelemetry Certified Associate (OTCA) | Linux Foundation / CNCF | $250 proctored exam | Industry certification covering all OTel concepts |
| OpenTelemetry Observability for Java Spring Boot Developers | Udemy | Paid | Most directly relevant to this learning plan |
| Getting Started with OpenTelemetry: Metrics, Logs & Traces | Udemy | Paid | Covers Java instrumentation with Prometheus + Grafana |

### Essential blog posts and tutorials

The Spring blog post **"OpenTelemetry with Spring Boot"** (November 2025) is the single most important article — it's the official Spring team's guide covering all three integration paths. Baeldung's **"OpenTelemetry Setup in Spring Boot Application"** and **"Observability with Spring Boot 3"** provide excellent step-by-step walkthroughs with code. Dan Vega's guide on Spring Boot 4's new OTel starter is a well-written practical walkthrough. The Foojay article **"Spring Boot 4 - OpenTelemetry Explained"** covers migration from the multi-dependency setup to the unified starter.

For Korean-language resources, the KT Cloud tech blog published a detailed guide on **unifying metrics, logs, and traces with OTel Collector on Kubernetes** — directly applicable to EKS deployments. The blog at `kouzie.github.io` covers OTel Java Agent vs manual instrumentation for Spring Boot with detailed Korean-language code walkthroughs.

### Conference talks worth watching

Patrick Baumgartner's **"Spring Boot Observability in Practice"** (Voxxed Days CERN 2026) covers Actuator + Micrometer + OTel integration for local and Kubernetes scenarios. Cees Bos's **"How I Solved Production Issues with OpenTelemetry"** (Devoxx Belgium 2025) demonstrates real-world debugging with the Grafana stack — companion code at `github.com/cbos/solving-problems-with-opentelemetry`. KubeCon EU 2025 featured DigitalOcean's talk on rebuilding their entire observability stack with OTel, and Delivery Hero's real-world adoption story.

### GitHub repositories for hands-on learning

| Repository | What it provides |
|-----------|-----------------|
| `open-telemetry/opentelemetry-java-examples` | Official examples: `spring-boot-agent/`, `spring-native/`, `logback-appender/`, `micrometer-shim/` |
| `blueswen/spring-boot-observability` | Complete Spring Boot + Grafana LGTM demo with pre-built dashboards. Docker Compose ready. |
| `open-telemetry/opentelemetry-demo` | Multi-language microservices app (includes Kotlin Fraud Detection service) with full OTel instrumentation |
| `open-telemetry/opentelemetry-java-instrumentation` | Agent source + Spring Boot Starter. Study `instrumentation/spring/spring-boot-autoconfigure/` |
| `open-telemetry/opentelemetry-collector-contrib` | 100+ receivers, processors, exporters. Study configs in `examples/` |
| `cbos/observability-toolkit` | Devoxx companion — production OTel Collector + Grafana stack patterns |

### Official documentation bookmarks

| Resource | URL |
|----------|-----|
| OTel Java docs | https://opentelemetry.io/docs/languages/java/ |
| OTel Spring Boot Starter docs | https://opentelemetry.io/docs/zero-code/java/spring-boot-starter/ |
| OTel Collector docs | https://opentelemetry.io/docs/collector/ |
| Spring Boot Observability docs | https://docs.spring.io/spring-boot/reference/actuator/observability.html |
| Micrometer docs | https://micrometer.io/docs |
| Grafana Tempo docs | https://grafana.com/docs/tempo/latest/ |
| Grafana Loki docs | https://grafana.com/docs/loki/latest/ |
| Datadog OTel integration | https://docs.datadoghq.com/getting_started/opentelemetry/ |

---

## Conclusion: the architecture to target

The learning path builds toward a specific production architecture: your Kotlin Spring Boot services instrumented via the **OTel Java Agent** (for broad auto-instrumentation) plus **Micrometer Observation API** (for custom business metrics and spans), exporting all three signals via **OTLP** to an **OTel Collector** deployed as a DaemonSet + Gateway on EKS. The Collector performs enrichment with Kubernetes metadata, tail-based sampling, cost filtering, and simultaneous export to your chosen backends. This architecture is **completely vendor-neutral** at the application layer — switching or adding backends is a Collector configuration change, not a code change.

The single most important insight for a mid-level engineer entering observability: **start with the Java Agent and a local Grafana LGTM stack in Docker Compose**. You'll have distributed tracing across your services in under an hour, and that first trace visualization — seeing exactly where latency hides across service boundaries — is the moment that motivates everything else. The sophistication (custom spans, SLOs, tail sampling, cost optimization) comes naturally once you've experienced the debugging power of correlated signals.