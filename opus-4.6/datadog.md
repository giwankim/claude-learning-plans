# Mastering Datadog: a complete learning curriculum for backend engineers

**Datadog is the leading commercial observability platform, and this curriculum will take you from zero to production-grade mastery across infrastructure monitoring, APM, log management, dashboards, alerting, and infrastructure-as-code — all tailored to your Kotlin/Spring Boot stack on AWS EKS/ECS with MySQL/PostgreSQL, Redis, and Kafka.** The plan is structured in six phases over roughly 12 weeks, each building on the last. Every phase includes specific resources, hands-on projects, and architectural context so you understand not just *how* but *why* each piece works the way it does.

Before diving in, understand three foundational concepts. First, Datadog's **Unified Service Tagging** convention (`env`, `service`, `version`) is the single most important architectural decision you'll make — it ties metrics, traces, and logs together across all three pillars of observability. Second, Datadog bills per host, per ingested GB, and per indexed span/log event, so every configuration choice has cost implications. Third, the **14-day free trial** gives you full access to every feature, after which the account drops to a permanent Free tier (5 hosts, 1-day metric retention) — plan your hands-on projects to maximize this window.

---

## Phase 1: Foundations and platform orientation (weeks 1–2)

Start by building a mental model of Datadog's architecture before touching any configuration. The platform has three core pillars — metrics, traces, and logs — unified by tags and correlated through shared identifiers like `trace_id`. Every piece of telemetry flows through the **Datadog Agent**, an open-source daemon that runs on each host (or as a DaemonSet pod on each Kubernetes node). The Agent collects data locally and ships it to Datadog's SaaS backend, where it's processed, stored, and visualized.

**Key terminology to internalize first.** A **host** is any OS instance running the Agent (EC2 instance, EKS node). A **service** is a logical application component tracked by APM (your Spring Boot microservice). A **resource** is a specific operation within a service (a REST endpoint like `GET /api/orders`). **Integrations** are pre-built connectors for 1,000+ technologies. **Tags** are key-value pairs (`env:production`, `kube_namespace:checkout`) that enable filtering, grouping, and correlation across all telemetry. **Monitors** are alerting rules. **Dashboards** combine widgets visualizing metrics, logs, traces, and more.

**Account setup steps.** Sign up at datadoghq.com/free-datadog-trial for the 14-day trial. Choose the **US1** site (default) unless your organization requires EU residency. Generate an **API key** (for Agent data submission) and an **Application key** (for API/Terraform management) from Organization Settings → API Keys. Install the Datadog browser extension for quick access.

**UI navigation architecture.** The left sidebar organizes everything by domain: Infrastructure (hosts, containers, Kubernetes Explorer), APM (services, traces, service map), Logs (Log Explorer, pipelines, indexes), Dashboards, Monitors, and Security. The **Kubernetes Explorer** under Infrastructure → Kubernetes provides cluster, node, pod, and workload views. The **Service Catalog** under APM → Service Catalog is your central registry of all instrumented services with ownership metadata.

### Learning resources for Phase 1

Complete these Datadog Learning Center courses in order (all free, self-paced, with hands-on labs at learn.datadoghq.com):

- **Introduction to Observability** — establishes the three pillars framework and why correlation matters
- **Datadog Foundation** — covers core products, integrations, the Software Catalog, metrics, monitors, SLOs, and dashboards in a single comprehensive course
- **Getting Started with Datadog** learning path — Agent installation on hosts and Docker, integration setup, Unified Service Tagging

Read these documentation pages (docs.datadoghq.com):

- Getting Started → Application (UI overview)
- Getting Started → Datadog Sites (understand site selection)
- Getting Started → Tagging → Unified Service Tagging (critical architectural pattern)
- Agent → Basic Agent Usage (architecture, configuration, commands)

**Estimated time:** 10–15 hours of coursework plus 3–5 hours of documentation reading.

---

## Phase 2: Infrastructure monitoring on AWS EKS and ECS (weeks 3–4)

This phase establishes the monitoring foundation for your container infrastructure. The Datadog Agent on Kubernetes runs as a **DaemonSet** (one pod per node) collecting host, container, and pod metrics, plus a singleton **Cluster Agent Deployment** that handles cluster-level data like Kubernetes events and kube-state-metrics.

### EKS Agent installation via Helm

The Helm chart is the standard deployment method. Add the Datadog repo (`helm repo add datadog https://helm.datadoghq.com`), create a Kubernetes Secret with your API and App keys, then install with a values file. The critical Helm values to configure are:

```yaml
datadog:
  clusterName: <your-cluster>
  site: datadoghq.com
  kubeStateMetricsCore:
    enabled: true        # Cluster-state metrics via Cluster Agent
  logs:
    enabled: true
    containerCollectAll: true  # Collect all container stdout/stderr
  apm:
    socketEnabled: true  # APM via Unix Domain Socket (default)
  processAgent:
    enabled: true
    processCollection: true  # Live Processes view
clusterAgent:
  enabled: true          # Enabled by default since chart v2.7.0
```

The DaemonSet pods collect node-level metrics (CPU, memory, disk, network), container metrics (per-container CPU/memory/network via kubelet), and pod metrics (phase, restart counts, resource requests vs actual usage). The Cluster Agent collects cluster-state metrics from the Kubernetes API server — deployment replica counts, DaemonSet status, node conditions like `MemoryPressure` and `DiskPressure`. **Autodiscovery** is the mechanism by which the Agent automatically detects services running in containers and applies the appropriate integration configuration, triggered by pod annotations like `ad.datadoghq.com/<container>.check_names`.

### ECS integration strategies

For **ECS on EC2**, deploy the Agent as a **daemon service** (one Agent container per EC2 instance) using an ECS task definition with `DD_LOGS_ENABLED=true`, `DD_APM_ENABLED=true`, and `DD_APM_NON_LOCAL_TRAFFIC=true`. The Agent accesses the Docker socket to discover and monitor all other containers on the instance. For **ECS on Fargate**, you must use the **sidecar pattern** — the Agent container runs alongside your application container within the same task definition, collecting metrics via the ECS Metadata API endpoint since there's no Docker socket access. Trace data reaches the sidecar Agent on `localhost:8126`. Logs on Fargate are best collected via **FireLens** (Fluent Bit) forwarding to Datadog's log intake.

### AWS CloudWatch integration

Set up the AWS integration tile in Datadog, which provisions an IAM role with cross-account read access. This automatically ingests CloudWatch metrics from EC2, RDS, ElastiCache, MSK, ELB, and other AWS services. Tags from AWS (instance type, availability zone, Auto Scaling group) are imported automatically. For RDS/Aurora monitoring, also enable **Database Monitoring** by creating a `datadog` database user with `performance_schema` access and setting `dbm: true` in the integration configuration.

### Database and cache integration setup

**MySQL:** Create a read-only `datadog` user with `REPLICATION CLIENT` and `PROCESS` privileges. Configure `mysql.d/conf.yaml` on the Agent. With DBM enabled, you get query-level metrics, live query snapshots, and explain plans. **PostgreSQL:** Create a `datadog` user, grant `pg_monitor`, enable `pg_stat_statements` extension, and configure `postgres.d/conf.yaml`. **Redis:** Configure `redisdb.d/conf.yaml` with host, port, and password — metrics include connected clients, memory usage, hit/miss rates, eviction counts, and commands per second.

### Learning resources for Phase 2

- Learning Center: **Installing the Datadog Agent on Kubernetes** course, **AWS Integration** course
- Documentation: Infrastructure → Containers → Kubernetes, Infrastructure → Containers → Amazon ECS, Integrations → AWS, Integrations → MySQL/PostgreSQL/Redis
- Datadog blog: "Monitor Amazon EKS with Datadog", "Monitoring ECS with Datadog"
- GitHub: `DataDog/helm-charts` repository for Helm chart values reference

---

## Phase 3: APM and distributed tracing for Spring Boot/Kotlin (weeks 5–6)

APM is where Datadog delivers the most differentiated value for application developers. The **dd-java-agent.jar** uses Java's `-javaagent` instrumentation mechanism to modify class bytecode at load time, automatically wrapping framework calls with trace spans. No code changes are required for the vast majority of your stack.

### Agent setup and auto-instrumentation

Download the agent (`curl -Lo dd-java-agent.jar https://dtdg.co/latest-java-tracer`) and add it to your Dockerfile:

```dockerfile
ADD 'https://dtdg.co/latest-java-tracer' /opt/dd-java-agent.jar
ENTRYPOINT ["java", "-javaagent:/opt/dd-java-agent.jar",
  "-Ddd.service=order-service", "-Ddd.env=production", "-Ddd.version=1.2.0",
  "-Ddd.profiling.enabled=true", "-Ddd.logs.injection=true",
  "-jar", "/app/my-app.jar"]
```

**Everything in your stack is auto-instrumented out of the box.** Spring Boot (MVC and WebFlux), all JDBC drivers (MySQL, PostgreSQL), Jedis and Lettuce (Redis clients), Kafka producer and consumer (0.11+ with header-based context propagation), Spring RestTemplate and WebClient, OkHttp, and gRPC all get automatic span creation. Each database query appears as a child span in the trace with the full SQL text, duration, and row count. Redis commands show as spans tagged with `db.type: redis`. Kafka producer spans link to consumer spans via message headers, enabling **end-to-end distributed trace continuity across asynchronous boundaries** — this is critical for event-driven architectures.

### Custom instrumentation for Kotlin

For business logic that isn't covered by auto-instrumentation, use the `dd-trace-api` library (add `com.datadoghq:dd-trace-api` as a Maven/Gradle dependency). The simplest approach is the `@Trace` annotation:

```kotlin
@Trace(operationName = "processOrder", resourceName = "OrderService.processOrder")
fun processOrder(orderId: String) { /* business logic */ }
```

For more control, use the OpenTracing API to manually create spans with custom tags, error handling, and parent-child relationships. Datadog also supports **Dynamic Instrumentation**, which lets you create custom spans from the Datadog UI without redeploying — invaluable for debugging production issues.

### Continuous Profiler

Enable with `-Ddd.profiling.enabled=true`. The profiler uses an async-profiler-based engine (lower overhead than JFR) to collect CPU profiles, allocation profiles, heap analysis, lock contention, and exception profiling. The **Code Hotspots** feature links profiling data directly to APM traces, so you can identify exactly which method in which endpoint is consuming the most CPU or allocating the most memory. Profiles are retained for 7 days; derived metrics for 1 month.

### Trace sampling architecture

Understanding sampling is essential for both cost control and data quality. Datadog uses **head-based sampling** by default, with the Agent targeting **10 complete traces per second per Agent**. Low-traffic services get 100% sampling; high-traffic services get proportionally lower rates. Three additional mechanisms ensure visibility: the **error sampler** captures error traces at 10/second, the **rare sampler** captures at least some traces for every unique service/resource combination, and **retention filters** determine which spans are indexed for long-term storage beyond the 15-minute live window. You can override rates with `-Ddd.trace.sample.rate=0.5` or per-service rules via `DD_TRACE_SAMPLING_RULES`. **Adaptive sampling** (configurable in the UI) lets you set a monthly ingestion budget and Datadog auto-adjusts rates every 10 minutes.

### Learning resources for Phase 3

- Learning Center: **Introduction to APM** course, **APM & Distributed Tracing** learning path, **Troubleshooting APM** course
- Documentation: APM → Trace Collection → Java, APM → Continuous Profiler → Java, APM → Trace Pipeline → Ingestion Controls
- GitHub: `DataDog/dd-trace-java` (the tracer source), `DataDog/apm-tutorial-java-host`, `DataDog/springblog` (Spring Boot + K8s + Datadog APM example)
- Datadog blog: "Monitoring Spring Boot applications with Datadog"

---

## Phase 4: Log management and trace-log correlation (weeks 7–8)

Log management transforms raw container output into structured, searchable, correlated observability data. The key architectural insight is that Datadog processes logs through a **pipeline**: ingestion → processing (parsing, enrichment) → indexing (searchable storage) → archiving (long-term cold storage). You pay separately for ingestion ($0.10/GB) and indexing ($1.70/million events for 15-day retention), so controlling what gets indexed is the primary cost lever.

### Structured logging with logstash-logback-encoder

For Spring Boot applications, use `logstash-logback-encoder` to emit JSON-structured logs to stdout (which the Agent DaemonSet collects from `/var/log/pods`). Add the dependency and configure `logback-spring.xml` with `LogstashEncoder` for automatic JSON formatting. With `-Ddd.logs.injection=true` on the Java agent, `dd.trace_id`, `dd.span_id`, `dd.service`, `dd.env`, and `dd.version` are automatically injected into the SLF4J MDC and appear in every log line — **enabling one-click navigation between any trace and its correlated logs in the Datadog UI**. Spring Boot 3.4.0+ also offers native JSON structured logging without logstash-logback-encoder via `logging.structured.format.console=ecs` in application.properties.

Set the Autodiscovery annotation on your pod: `ad.datadoghq.com/<container>.logs: '[{"source":"java","service":"order-service"}]'`. The `source: java` tag activates Datadog's **out-of-the-box Java integration pipeline**, which automatically parses common Java log patterns, remaps severity levels, and handles stack traces.

### Log pipelines and processing

Pipelines are ordered sequences of processors that transform raw logs into structured, enriched events. Each incoming log is matched against pipeline filters (based on `source`, `service`, or custom queries); the first matching pipeline applies. Key processors include the **Grok Parser** (extracts attributes from semi-structured text), **JSON Parser**, **Date Remapper** (maps an attribute to the official timestamp), **Status Remapper** (maps to severity), **Category Processor** (categorizes logs by rules, e.g., HTTP status code ranges), and **Trace Remapper** (associates logs with traces via `trace_id`). You can nest pipelines for multi-level filtering — for instance, a team-level pipeline containing service-specific sub-pipelines.

### Log-based metrics and anomaly detection

**Log-based metrics** let you generate time-series metrics from log data without indexing the underlying logs. For example, create a count metric for `service:order-service AND status:error` grouped by `@http.status_code` — this metric persists for **15 months** (far longer than typical log retention) and costs nothing beyond the initial ingestion. This is a powerful cost optimization: ingest logs, generate metrics for dashboards and monitors, then exclude the raw logs from indexing.

**Watchdog Log Anomaly Detection** requires no configuration. It automatically identifies new error patterns, sudden volume spikes, and novel log text structures, surfacing them as Watchdog Insights in the Log Explorer. Severe anomalies appear in the Watchdog alerts feed and can trigger monitors.

### Log indexes, exclusion filters, and archives

Create **multiple indexes** with different retention periods: a "critical" index (30-day retention) filtered to `status:(error OR critical)`, and a "general" index (7-day retention) for everything else. Apply **exclusion filters** to the general index — for example, exclude 95% of health check logs (`@http.url:/health*`) and 90% of successful 2xx response logs. Excluded logs still flow through Live Tail, still generate log-based metrics, and are still archived. Set **daily quotas** on each index as a budget guardrail.

Configure **log archives** to forward all ingested logs to Amazon S3 for long-term compliance retention (free, aside from S3 storage costs). Use S3 lifecycle policies to transition older archives to Glacier. **Rehydration** lets you pull archived logs back into the Log Explorer for investigation at $0.10/compressed GB scanned — useful for post-incident analysis or compliance audits.

### Learning resources for Phase 4

- Learning Center: **Going Deeper with Logs** course, **Log Management** learning path, **Log Configuration** learning path
- Documentation: Log Management → Log Collection → Containers, Log Management → Log Configuration → Pipelines, Log Management → Log Configuration → Indexes
- Datadog blog: "Best practices for log management", "Correlate logs and traces"

---

## Phase 5: Dashboards, alerting, SLOs, and incident analysis (weeks 9–10)

This phase transforms raw observability data into actionable operational intelligence. The goal is not just to visualize data but to build a monitoring system that reduces mean time to detection (MTTD) and mean time to resolution (MTTR).

### Building effective dashboards

Start with Datadog's **out-of-the-box dashboards** for Kubernetes, JVM, PostgreSQL, MySQL, Redis, and ECS — these provide immediate value and serve as templates for custom dashboards. When building custom dashboards, use **template variables** (`env`, `service`, `kube_cluster_name`, `kube_namespace`) as dropdown filters at the top, enabling a single dashboard to serve multiple environments and teams.

The most useful widgets for your stack: **Timeseries** for trend analysis (p99 latency, error rates, throughput), **Query Value** for current state (active connections, queue depth), **Top List** for ranked views (slowest endpoints, busiest services), **Service Map** for dependency visualization, **Log Stream** for live log tailing filtered by the dashboard's template variables, and **SLO widgets** for error budget status. Use **formulas and functions** to create derived metrics — for example, `(errors / total_requests) * 100` for error rate, or `anomalies(avg:jvm.heap_memory{service:order-service})` for visual anomaly bands. The `week_before()` timeshift function overlays last week's data for quick comparison.

Limit dashboards to roughly **20 widgets** for performance. Group related widgets with color-coded headers. Use **Powerpacks** (reusable widget groups) for patterns you repeat across service dashboards.

### Monitor types and when to use each

**Metric monitors** are your bread-and-butter — alert when a metric crosses a threshold (static or anomaly-based). Use **anomaly monitors** (with the Robust algorithm for stable seasonal metrics, Agile for metrics that may shift baseline) instead of static thresholds for metrics with natural variation like request volume or latency. **Forecast monitors** predict future values and alert when a metric will cross a threshold within a configurable window — ideal for disk usage and memory capacity planning. **APM monitors** track trace-derived metrics (p99 latency, error rate, throughput) per service. **Log monitors** alert on log volume or patterns matching a query. **Composite monitors** combine multiple monitors with boolean logic (e.g., alert only when `high_cpu AND high_error_rate`, filtering out normal CPU spikes during deployments).

**Critical alerting best practices:** Set **recovery thresholds** lower than alert thresholds to prevent flapping. Use an **evaluation delay of 300+ seconds** for CloudWatch-sourced metrics to avoid alerting on incomplete data. Include links to relevant dashboards, runbooks, and the Service Catalog page in alert messages. Route critical alerts through PagerDuty for on-call escalation; use Slack for informational alerts. Use **downtime scheduling** to suppress alerts during planned maintenance windows.

### SLOs and error budgets

Create **metric-based SLOs** using APM trace metrics — for example, define the SLI as `trace.http.request.hits{service:order-service,http.status_code:2*} / trace.http.request.hits{service:order-service}` with a target of **99.9% over 30 days** (which allows 43.2 minutes of downtime). Set up two types of SLO alerts: an **error budget alert** (triggers when >75% of budget consumed) for proactive response, and a **burn rate alert** (triggers when consumption rate exceeds 14x baseline over 1 hour) for active incidents. Never set a 100% target — it creates zero error budget and breaks alert evaluation.

**Datadog Notebooks** serve as living postmortem documents. When an incident resolves, click "Generate Postmortem" to auto-create a Notebook with the incident timeline, affected resources, severity changes, and responder actions. Notebooks contain live Datadog graphs (not static screenshots), so you can adjust timeframes and pivot to related data during the analysis.

### Learning resources for Phase 5

- Learning Center: **Building Dashboards** course, **Creating Monitors & Notifications** course
- Documentation: Dashboards → Widgets, Monitors → Monitor Types, Service Management → SLOs
- Datadog blog: "Best practices for creating dashboards", "SLO monitoring and alerting best practices"

---

## Phase 6: Production mastery — cost control, IaC, and ecosystem integration (weeks 11–12)

### Understanding the pricing model

Datadog pricing has multiple dimensions that compound. **Infrastructure monitoring** costs **$15/host/month** (Pro, annual billing) or **$23/host/month** (Enterprise). **APM** adds **$31/host/month** per APM-enabled host, including 150 GB span ingestion and 1 million indexed spans with 15-day retention. **Log management** charges **$0.10/GB ingested** plus **$1.70/million events indexed** (15-day retention). **Custom metrics** include 100 per host on Pro; overages cost **$5/100 metrics/month**. Containers beyond 10 per host cost **$0.002/container/hour**. Database Monitoring is **$70/database host/month**.

For a concrete estimate: a team running 20 EKS nodes with APM, logs, and Database Monitoring on 4 RDS instances might pay roughly $920/month for infrastructure + $620/month for APM + variable log costs + $280/month for DBM = **$1,800+/month minimum** before log ingestion. This is why cost optimization matters from day one.

### Cost optimization strategies

The highest-impact cost lever is **log management**. Use exclusion filters to drop 90%+ of high-volume, low-value logs (health checks, debug logs, successful requests) from indexing while keeping them in archives. Create **log-based metrics** for aggregate trends before excluding the raw logs. Use **Flex Storage** ($0.05/million events) instead of standard indexing for logs you rarely search. Set **daily quotas** on indexes as hard spending limits.

For APM, use **head-based sampling** at 10–20% for high-traffic services while capturing 100% of errors and rare traces. Stay within the 150 GB/host ingestion allotment by adjusting sampling rates. For **custom metrics**, avoid unbounded tags (user IDs, session IDs, request IDs) — each unique tag combination creates a separate billable metric. Use **Metrics without Limits** to control which tag combinations are indexed while still ingesting all data.

### Terraform provider for Datadog (infrastructure-as-code)

The `DataDog/datadog` Terraform provider (v3.88.0+) supports monitors, dashboards, SLOs, log pipelines, log indexes, log archives, log-based metrics, downtime schedules, synthetics, AWS integration configuration, and more. Store all Datadog configuration in Git alongside your infrastructure code. Key resources: `datadog_monitor` for alerts, `datadog_dashboard` or `datadog_dashboard_json` for dashboards, `datadog_service_level_objective` for SLOs, `datadog_logs_index` and `datadog_logs_custom_pipeline` for log configuration, and `datadog_integration_aws` for AWS integration setup. Use `terraform plan` to detect configuration drift from manual UI changes.

### How Datadog compares to Prometheus and Grafana

The Prometheus/Grafana stack is open-source and free to run, but you bear the full operational burden — managing Prometheus scaling (requiring Thanos or Cortex/Mimir for high availability), Loki for logs, Tempo for traces, storage backends, upgrades, and capacity planning. Datadog eliminates this operational overhead but costs significantly more at scale and creates vendor lock-in. The key architectural trade-off is **operational complexity vs. financial cost**. Many organizations use both: Prometheus for high-cardinality internal metrics and real-time alerting within clusters, Datadog for cross-team visibility, log management, APM, and ML-based alerting.

Datadog's **OpenMetrics integration** (Agent v6.5.0+) can scrape any Prometheus `/metrics` endpoint, making migration incremental — but every scraped metric counts as a custom metric in Datadog billing. A common pattern is to pre-aggregate metrics in Prometheus and forward only essential aggregated metrics to Datadog via the OpenMetrics check or remote write.

### Learning resources for Phase 6

- Learning Center: **Datadog API** course, **Custom Metrics with DogStatsD** course
- Documentation: Getting Started → Terraform, Account Management → Billing, APM → Trace Pipeline → Ingestion Controls
- Datadog blog: "Managing Datadog with Terraform", "Monitor Prometheus metrics with Datadog"
- Terraform Registry: `DataDog/datadog` provider documentation
- HashiCorp tutorial: "Use Terraform to Manage Datadog Monitors and Dashboards"

---

## Six progressive hands-on projects

These projects build sequentially. Start each during the corresponding phase; revisit and extend during later phases.

**Project 1 — Agent deployment and infrastructure baseline (Phase 2).** Deploy the Datadog Agent via Helm on a local or dev EKS cluster running a single Spring Boot/Kotlin application with a PostgreSQL database and Redis cache. Configure Unified Service Tagging. Verify host metrics, container metrics, and pod metrics appear in the Kubernetes Explorer. Set up the AWS integration for CloudWatch metrics. Enable Live Processes. Deliverable: a working Agent deployment with complete infrastructure visibility.

**Project 2 — Full-stack APM with distributed tracing (Phase 3).** Add the `dd-java-agent.jar` to your Spring Boot application's Dockerfile. Verify auto-instrumented traces for HTTP endpoints, JDBC queries (PostgreSQL), Redis commands, and Kafka producer/consumer operations. Add custom `@Trace` annotations to 2–3 business-critical methods. Enable the Continuous Profiler and use Code Hotspots to identify the slowest code path in a specific endpoint. Explore the Service Map to verify all dependencies are correctly visualized. Deliverable: end-to-end distributed traces spanning HTTP → business logic → database → cache → message queue.

**Project 3 — Structured logging with trace correlation (Phase 4).** Configure `logstash-logback-encoder` for JSON-structured logging. Verify `dd.trace_id` and `dd.span_id` appear in every log line. Create a custom log pipeline with a Grok parser for any non-standard log formats. Create two log-based metrics: error rate by endpoint and p95 request duration. Set up exclusion filters to drop health check logs and sample 90% of successful request logs. Configure an S3 log archive. Deliverable: correlated logs and traces with cost-optimized indexing.

**Project 4 — Production-grade dashboards and alerting (Phase 5).** Build a custom service dashboard with template variables for `env` and `service`, including timeseries widgets for p50/p95/p99 latency, error rate, throughput, JVM heap usage, database connection pool utilization, Redis hit rate, and Kafka consumer lag. Create five monitors: an anomaly monitor on request latency, a threshold monitor on error rate, a forecast monitor on disk usage, a composite monitor combining high CPU with high error rate, and a log monitor for specific error patterns. Set up a **99.9% SLO** on request success rate with both error budget and burn rate alerts. Configure PagerDuty and Slack notification channels. Deliverable: a complete monitoring stack with intelligent alerting and SLO tracking.

**Project 5 — Multi-service observability with Kafka event flows (Phases 3–5).** Extend to a three-service architecture: an API gateway service, an order processing service, and a notification service, communicating via Kafka topics. Instrument all three services with APM. Verify that distributed traces flow correctly across Kafka message boundaries. Enable **Data Streams Monitoring** to visualize end-to-end pipeline topology and per-topic latency. Build a cross-service dashboard showing the full request lifecycle. Create an SLO on end-to-end order processing time. Deliverable: production-grade observability for an event-driven microservice architecture.

**Project 6 — Infrastructure-as-code and cost governance (Phase 6).** Codify all monitors, dashboards, SLOs, log indexes, and log pipelines from the previous projects using the Datadog Terraform provider. Store in a Git repository with CI/CD pipeline that runs `terraform plan` on PRs and `terraform apply` on merge. Implement cost governance: set daily log index quotas, configure adaptive trace sampling with a monthly ingestion budget, review the Estimated Usage dashboard, and create a cost monitor that alerts when daily log ingestion exceeds a threshold. If your environment currently runs Prometheus, configure the OpenMetrics integration to scrape Prometheus endpoints and compare the data in Datadog. Deliverable: a fully version-controlled, reproducible Datadog configuration with cost guardrails.

---

## Certifications and the path to validation

Datadog offers three certifications, all administered via PSI/Kryterion proctoring at **$100 per exam** (90 multiple-choice questions, 2 hours). Pursue them in this order after completing the curriculum:

1. **Datadog Fundamentals** — covers Agent deployment, data collection, tagging, visualization, and troubleshooting across 6 exam domains. Prepare with the free Fundamentals Certification Learning Path and 25-question practice exam on the Learning Center. This is accessible after completing Phases 1–2.
2. **Log Management Fundamentals** — covers log collection, parsing, searching, analysis, and troubleshooting. Target this after completing Phase 4.
3. **APM & Distributed Tracing Fundamentals** — covers instrumentation, insight discovery, visualization, and troubleshooting. Datadog recommends 6+ months of hands-on APM experience. Target this after completing Phase 5.

A fourth certification, **Cloud SIEM for AWS Fundamentals**, was piloted in late 2025 and may become generally available in 2026. All certifications award Credly-verified digital badges. You get up to 3 attempts within 180 days.

---

## Complete resource reference by category

**Official free learning (highest priority):** The Datadog Learning Center at learn.datadoghq.com provides hands-on lab environments for every major product area. Complete the **Developer learning path** (APM, Log Explorer, Infrastructure) as your primary structured curriculum. All courses are free with 30-day enrollment windows (re-enrollable anytime).

**Documentation deep-reads:** Prioritize these docs.datadoghq.com sections: Getting Started (entire section), Agent → Kubernetes, APM → Trace Collection → Java, Log Management → Log Collection → Containers, Log Management → Log Configuration (Pipelines, Indexes, Archives), Dashboards → Widgets, Monitors → Monitor Types, Service Management → SLOs, and the Guides section (docs.datadoghq.com/all_guides/) for advanced workflow walkthroughs.

**Books:** *Applied Observability with Datadog: Building Resilient Monitoring, Alerts, and Dashboards for Production Systems* (2025) covers Agent deployment, log pipelines, anomaly detection, RBAC, and infrastructure-as-code. *Datadog Cloud Monitoring Quick Start Guide* (Packt) provides a lighter introduction.

**Third-party courses:** Udemy hosts several Datadog courses — "Datadog Monitoring - A Full Basic to ADVANCE Datadog guide" (highest rated) and "FREE Datadog Observability (Monitoring/Logging/Alerting)" for a no-cost introduction. Whizlabs offers Datadog Fundamentals certification practice exams.

**GitHub repositories:** `DataDog/springblog` (Spring Boot + Kubernetes + Datadog APM example), `DataDog/apm-tutorial-java-host` (official Java APM tutorial), `ziquanmiao/kubernetes_datadog` (K8s cluster with Flask + Spring Boot + Postgres + Datadog), and `DataDog/helm-charts` for Helm configuration reference.

**Community:** Join the Datadog Community Slack at chat.datadoghq.com (including a `#learning-center` channel). The Datadog blog at datadoghq.com/blog publishes detailed technical guides on monitoring best practices for every supported technology. The DASH conference (June 9–10, 2026 in NYC) offers 80+ breakout sessions, 20+ hands-on workshops, and in-person certification exams included in the ticket price. All past DASH sessions are available on the Datadog YouTube channel.

---

## Conclusion

The single most important thing to get right early is **Unified Service Tagging** — applying consistent `env`, `service`, and `version` tags to every metric, trace, and log from day one. This one decision determines whether your three pillars of observability are correlated or siloed. The second most important decision is your **log indexing strategy**: ingest broadly, index selectively, archive everything, and generate log-based metrics for long-term trends. These two architectural choices together deliver 80% of Datadog's value while keeping costs manageable.

This curriculum is designed for depth-first learning — each phase establishes deep understanding before moving forward, and each hands-on project extends previous work rather than starting from scratch. By the end of 12 weeks, you'll have a production-grade observability platform covering infrastructure, APM, logs, dashboards, alerting, and SLOs, fully codified in Terraform and optimized for cost — plus the foundation to pass all three Datadog certifications.