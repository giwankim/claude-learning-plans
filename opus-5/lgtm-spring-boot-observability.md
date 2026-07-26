---
title: "Observability with Spring Boot + the LGTM Stack — Learning Plan"
category: "Observability"
description: "A ~14-week, six-phase plan for operating Loki / Grafana / Tempo / Mimir (plus Pyroscope and Alloy) against Kotlin Spring Boot 4 services on EKS — starting where 'I have metrics' turns into 'I can operate a system.' Covers the Boot 4.1 OTLP wiring that finally gives exponential histograms and exemplars on one wire format, a written cardinality budget enforced by MeterFilter and Alloy relabel rules, PromQL/LogQL/TraceQL to real fluency with dashboards-as-code (Grafana 13 Git Sync, Foundation SDK), queueing-theory-driven performance work (Little's Law and Kingman's formula, saturation signals for Tomcat/HikariCP/HC5/Kafka/JVM/virtual threads/Aurora, span profiles down to the frame), SLO burn-rate alerting from the SRE Workbook with Sloth/Pyrra, the outages metrics won't see (absent alerts, meta-monitoring, blackbox probes, liveness-vs-readiness), and EKS collector pipelines on the k8s-monitoring Helm chart v4 after Promtail's EOL."
---

# Observability with Spring Boot + the LGTM Stack — Learning Plan

**Scope:** operating Loki / Grafana / Tempo / Mimir (+ Pyroscope, + Alloy) against Kotlin Spring Boot 4 services on EKS, and then using what comes out of it to (a) make things faster and (b) find out something is broken before your users tell you.

**Assumed starting point:** you already know Actuator, Micrometer meter types, the Observation API in outline, MDC/structured logging, and basic PromQL. This plan deliberately skips that ground and starts where "I have metrics" turns into "I can operate a system."

**Shape:** ~14 weeks at 5–6 h/week. Six phases, each with one deliverable. The deliverables matter more than the reading — the reading is what you do when a deliverable stalls.

---

## Phase 0 — Decide what each signal is *for* (3–4 days)

The single biggest failure mode in an LGTM rollout is collecting four signals and having no theory of which question each one answers. Fix that first, on paper.

The mental model to leave this phase with:

| Question | Signal | Cost of cardinality |
|---|---|---|
| Is it broken, and how badly? | metrics (SLI) | catastrophic — series explode |
| Which service / which hop is slow? | traces | manageable — sampled |
| What exactly happened to *this* request? | logs | moderate — labels vs metadata |
| Which line of code burns the CPU? | profiles | low — aggregated |

And the *diagnostic ladder*, which is the thing you are actually building:

```
SLO burn-rate alert fires
  → RED dashboard: which endpoint, error or latency?
    → exemplar on the latency histogram (a trace ID embedded in the metric)
      → Tempo trace: which span owns the time?
        → span profile (Pyroscope): which frames inside that span?
        → trace-to-logs: what did that request actually log?
```

Every design decision later in this plan is justified by whether it keeps that ladder intact. Broken rungs are the norm in real deployments.

**Read**
- Google SRE Book ch. 6 "Monitoring Distributed Systems" — <https://sre.google/sre-book/monitoring-distributed-systems/> (four golden signals; the *symptom vs cause* distinction is the load-bearing idea)
- Brendan Gregg, "The USE Method" — <https://www.brendangregg.com/usemethod.html>
- Tom Wilkie, "The RED Method" — <https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/>
- Dean & Barroso, *The Tail at Scale* (2013) — <https://research.google/pubs/the-tail-at-scale/>
- Gil Tene, "How NOT to Measure Latency" — <https://www.youtube.com/watch?v=lJ8ydIuPFeU> (you know coordinated omission from k6 work; watch it again with *dashboards* in mind — averaged p99s across pods are the same sin)

**Deliverable:** one page per candidate service listing: 2–3 SLIs, the RED metrics, the USE metrics for its saturating resource (HikariCP pool, consumer group, thread pool), and the ladder above filled in with the *actual* metric/label names you'd click through.

---

## Phase 1 — Make the local LGTM stack tell the truth (1.5 weeks)

You're already experimenting here, so the goal is not "get it running" but "prove all four signals correlate."

### The local backend

`grafana/otel-lgtm` bundles the OTel Collector, Grafana, Loki, Tempo, Mimir and Prometheus in one image. Two ways in:

- **Docker Compose** — put the image in `compose.yaml`, add `spring-boot-docker-compose`, and Boot auto-configures the OTLP exporters at the container's ports. Nothing to set by hand locally, which is a trap when you promote to prod and forget the properties are unset.
- **Testcontainers** — `LgtmStackContainer`, usable as a `@ServiceConnection`. Ports: Grafana 3000, Loki 3100, Tempo 3200, OTLP gRPC 4317, OTLP HTTP 4318. (The Javadoc has the gRPC/HTTP labels swapped; trust the numbers.) **Coordinate warning:** Boot 4 manages **Testcontainers 2.0**, where every module is prefixed `testcontainers-` and container classes were relocated to packages matching the module name. So the pre-2.0 `org.testcontainers:grafana` / `org.testcontainers.grafana.LgtmStackContainer` you'll find in every blog post is wrong on Boot 4 — check the Testcontainers 2.0 release notes for the current coordinates and package.

Docs: <https://grafana.com/docs/opentelemetry/docker-lgtm/> · <https://java.testcontainers.org/modules/grafana/> · repo <https://github.com/grafana/docker-otel-lgtm>

**Podman note (you'll hit this):** Ryuk misbehaves under Podman. Either point Testcontainers at the Podman socket (`DOCKER_HOST=unix://$XDG_RUNTIME_DIR/podman/podman.sock`, `TESTCONTAINERS_RYUK_DISABLED=true`) or run the LGTM container out-of-band via `podman compose` and connect to fixed ports. Don't spend three evenings on it — the image also runs fine as a long-lived local container you never restart.

### Boot 4 wiring — the properties that actually exist

Read the primary source once, carefully: **Moritz Halbritter, "OpenTelemetry with Spring Boot"** — <https://spring.io/blog/2025/11/18/opentelemetry-with-spring-boot/> — plus the sample repo <https://github.com/mhalbritter/spring-boot-and-opentelemetry>.

The three namespaces are *not* symmetric, and every third-party blog post gets at least one wrong:

```properties
# metrics go through Micrometer's OtlpMeterRegistry
management.otlp.metrics.export.url=http://collector:4318/v1/metrics
# traces go through the OTel SDK exporter (Micrometer Tracing OTel bridge)
management.opentelemetry.tracing.export.otlp.endpoint=http://collector:4318/v1/traces
# logs: the SDK is configured, but no appender is installed for you
management.opentelemetry.logging.export.otlp.endpoint=http://collector:4318/v1/logs
```

Then wire the Logback side yourself: `io.opentelemetry.instrumentation:opentelemetry-logback-appender-1.0` (alpha-versioned; there is no stable release), an `OTEL` appender in `logback-spring.xml`, and an `InitializingBean` calling `OpenTelemetryAppender.install(openTelemetry)`. Log export needed Actuator in 4.0.0 and no longer does from 4.0.1.

Also from that post, and worth internalizing now rather than during an incident:
- Never `new` a `RestClient`/`RestTemplate`/`WebClient`. Inject the builder or you silently lose W3C trace-context propagation.
- **Context propagation across threads.** On Boot 4.0 you had to register a `ContextPropagatingTaskDecorator` bean or `@Async` / `AsyncTaskExecutor` work silently lost the trace context (ThreadLocal doesn't cross threads). **Boot 4.1 does this automatically for the auto-configured executor** — but only that one. Custom `TaskExecutor` beans, manually created thread pools, and Kotlin coroutines are still on you: coroutines need `ObservationThreadLocalAccessor` plus `kotlinx-coroutines-slf4j`'s `MDCContext`. Test every boundary, don't assume.
- Return the trace ID in a response header (`X-Trace-Id`) from a `OncePerRequestFilter`. This turns every support ticket into a one-click trace lookup and costs ten lines.

### The naming decision you make once and regret forever

Micrometer's default meter names are Micrometer-flavoured (`http.server.requests`) — **not** OTel semantic conventions (`http.server.request.duration`). Boot ships `OpenTelemetry*ObservationConvention` / `OpenTelemetryJvm*MeterConventions` beans to switch. On 4.0 you had to wire each one by hand (the blog's verbose `OpenTelemetryConfiguration` snippet); **4.1 applies convention beans automatically** to the auto-configured JVM metrics — declare a `JvmMemoryMeterConventions`, `JvmThreadMeterConventions`, `JvmClassLoadingMeterConventions` or `JvmCpuMeterConventions` bean and Boot picks it up. Same for `KafkaTemplateObservationConvention` on `KafkaTemplate`, which is directly relevant to you. Either way, choose now:

- **Micrometer names** → community Spring dashboards work, OTel-ecosystem dashboards don't.
- **OTel semconv names** → the reverse, plus you can share dashboards with non-JVM services.

Whichever you pick, pick it for *all* services. Mixed naming across a microservice fleet is the observability equivalent of mixed line endings.

**Deliverable:** a three-service Kotlin sample (mirroring your real topology: HTTP edge → service → Kafka → service → Aurora) where you can start from a Loki line, jump to the Tempo trace, jump to the Mimir metric, and back — plus one Testcontainers integration test that asserts a specific span was exported. That test is the thing that stops instrumentation from silently rotting.

---

## Phase 2 — Cardinality is the whole game (2 weeks)

### Metrics

The Observation API's `lowCardinalityKeyValue` vs `highCardinalityKeyValue` split is not stylistic — low-cardinality keys become **metric tags**, high-cardinality keys become **span attributes only**. Getting this wrong is how you kill Mimir. Read the Observation section of the Micrometer reference properly: `ObservationRegistry`, `ObservationHandler`, `ObservationFilter`, `ObservationPredicate`, `ObservationConvention` — <https://docs.micrometer.io/micrometer/reference/observation/introduction.html>

Then learn `MeterFilter` as a *policy* mechanism, not a config detail: `deny`, `denyNameStartsWith`, `renameTag`, `replaceTagValues`, `maximumAllowableTags`, `maximumAllowableMetrics`. A `MeterFilter` bean is the only thing standing between a well-meaning colleague tagging by `userId` and a 2 a.m. Mimir OOM.

### Histograms — the part that's genuinely changed

- Client-side percentiles (`publishPercentiles`) **cannot be aggregated across instances**. A "p99" panel built by averaging per-pod p99s is a number with no meaning. Use histograms + `histogram_quantile`.
- `distribution.percentiles-histogram` + `distribution.slo` gives you Prometheus-side quantiles and SLO buckets, at the cost of one series per bucket per tag combination.
- **Native histograms are now stable** in Prometheus — since v3.8 (Nov 2025), no longer behind `--enable-feature`, but scraping still requires `scrape_native_histograms` explicitly; from v3.9 the old feature flag is a no-op. Spec: <https://prometheus.io/docs/specs/native_histograms/>
- **But** Micrometer's *Prometheus* registry doesn't emit them. The practical route from a JVM is OTLP: `OtlpMeterRegistry` supports exponential histograms via `histogramFlavor` / `histogramFlavorPerMeter`, with `maxScale` (default 20) and `maxBuckets` (default 160) — and it silently falls back to explicit-bucket histograms for any meter where you configured `serviceLevelObjectives`. Read <https://docs.micrometer.io/micrometer/reference/implementations/otlp.html> and then check Boot's config-props appendix for the exact `management.otlp.metrics.export.*` keys rather than trusting a blog post.

This used to be a painful fork — scrape `/actuator/prometheus` for exemplars, or push OTLP for exponential histograms, but not both. **Boot 4.1 added exemplar support to Micrometer's `OtlpRegistry`**, auto-configured when you're exporting metrics over OTLP with Micrometer Tracing present. So on 4.1+ the OTLP path is no longer a trade-off: you get exponential histograms, exemplars, and one wire format for all three signals. (4.1 also added SSL bundle support to the OTLP logging/metrics/trace exporters, which matters the moment you leave localhost.) Still test both paths in Phase 1's sample and document your choice — but the default answer is now OTLP.

### Exemplars

The rung that makes the whole ladder work. Requirements, from <https://docs.spring.io/spring-boot/reference/actuator/metrics.html>:
- an `ExemplarContextProvider` bean — auto-configured when Micrometer Tracing is present (older Prometheus simpleclient: `SpanContextSupplier`)
- **OpenMetrics** exposition format; exemplars do not appear in the Prometheus text format
- enabled on the Prometheus/Mimir side too
- `management.tracing.exemplars.include` controls which are kept; only sampled traces by default, and `all` is not supported for Prometheus

Verify by curling the actuator endpoint with `Accept: application/openmetrics-text` and looking for `# {trace_id="..."}` after a bucket value. If it's not there, nothing downstream will save you.

### Logs

Loki indexes labels, not content. Defaults cap you around 15 index labels.
- **Labels:** bounded sets only — `service_name`, `namespace`, `cluster`, `level`. That's roughly it.
- **Structured metadata** (Loki 3.0+): high-cardinality-but-queryable — `trace_id`, `span_id`, `pod`. Queryable without creating streams.
- **Parsed at query time** (`| json`, `| logfmt`, `| pattern`): everything else.

Read <https://grafana.com/docs/loki/latest/get-started/labels/> and the cardinality page. `trace_id` as a *label* is the classic million-stream mistake.

### Traces

- Head sampling (`management.tracing.sampling.probability`) is cheap and loses the interesting 0.1%. Tail sampling in the Collector/Alloy keeps errors and slow traces. Learn the tradeoff: tail sampling needs all spans of a trace to reach the same collector instance.
- Tempo's **metrics-generator** derives span metrics and service graphs from traces — a free RED dashboard and dependency map for services you haven't instrumented with metrics.
- Configure **trace↔logs** and **trace↔profiles** on the Tempo datasource: <https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/configure-trace-to-logs/>

**Deliverable:** a written *cardinality budget* — max series per service, max Loki streams, which tags are allowed on which meters — plus the `MeterFilter` and Alloy relabel rules that enforce it. Measure `count({__name__=~".+"})` before and after and put the numbers in the doc.

---

## Phase 3 — Query languages to actual fluency (2 weeks)

You cannot debug what you cannot query, and dashboards built by someone else are opinions you can't inspect.

**PromQL** — Brian Brazil, *Prometheus: Up & Running* (2nd ed., 2023) is still the book. Chapters on the query language, recording rules, and instrumentation best practices. Supplement with the Robust Perception blog archive (<https://www.robustperception.io/blog>) — short posts, most of them answer a question you will have.

Drill until automatic:
- `rate` vs `irate` vs `increase`; why the range must exceed ~4× the scrape interval; counter-reset handling; extrapolation at range edges
- `histogram_quantile(0.99, sum by (le, route) (rate(bucket[5m])))` — and why the `sum by (le)` must come *before* `histogram_quantile`
- staleness semantics, `absent()`, `absent_over_time()`
- `label_replace`, `label_join`, `topk`/`bottomk` with `by`
- recording rules: naming convention (`level:metric:operation`), and why SLO rules must be recorded rather than computed at query time
- the four classic errors: averaging quantiles, `rate()` on a gauge, aggregating away `le`, comparing `rate` windows of different lengths

**LogQL** — log-to-metric queries are underrated: `sum(rate({app="x"} |= "error" [5m]))` gives you an error SLI for a service that never got a counter. Learn `unwrap` for numeric fields and the `pattern` parser for semi-structured lines.

**TraceQL** — structural operators (`>>`, `~`) and TraceQL metrics (`rate()`, `quantile_over_time()` over spans) let you answer "which downstream call is slow only for requests that also touched Kafka" — a question metrics cannot express at all.

**Dashboards as code.** Stop clicking. Grafana 13 made **Git Sync** GA (dashboards in a Git repo, PRs opened from Grafana itself), and the **Foundation SDK** generates dashboard JSON from typed code in Go, TypeScript, Python, **Java**, or PHP — so you can define dashboards in a JVM language alongside the service. Start at <https://grafana.com/docs/grafana/latest/as-code/observability-as-code/> and the learning path at <https://grafana.com/docs/learning-paths/build-dashboard-sdk/>. Grafonnet remains the mature alternative if you'd rather not write Java for this.

**Deliverable:** one RED dashboard per service, generated from code, in version control, deployed by CI — plus a set of recording rules. Delete the hand-clicked versions.

---

## Phase 4 — Using metrics to make things faster (3 weeks)

This is where your queueing-theory background pays off, because most "performance dashboards" measure the wrong side of the queue.

### The framing

Latency is not a property of code; it's `queue time + service time`. Dashboards overwhelmingly show service time, alerts fire on total latency, and the fix almost always belongs to queue time. So instrument **utilization, saturation, and wait**, not just duration:

- **Little's Law** (`L = λW`) tells you the concurrency your pools must sustain — you've applied it to HikariCP and HC5 sizing; the observability move is to *plot the three quantities together* and watch the identity break during an incident.
- **Kingman's formula** — wait time grows as `ρ/(1−ρ)`. This is why 80% → 85% utilization is a bigger deal than 40% → 45%, and why a *utilization* panel with no *queue-time* panel next to it is misleading. Put them side by side on every saturation dashboard.

### Concrete saturation signals for your stack

| Resource | Watch | Why |
|---|---|---|
| Tomcat / servlet | `tomcat.threads.busy` vs `max`, accept-queue depth | the first queue a request meets |
| HikariCP | `hikaricp.connections.pending`, `hikaricp.connections.acquire` (timer!), `.timeout`, `.usage` | `pending > 0` is the DB pool queueing; acquire-time p99 is the wait |
| HTTP client (HC5) | pool leased/pending/available, connection-lease timer | the timeout everyone forgets is connection-request, not connect |
| Kafka consumer | `kafka.consumer.fetch.manager.records.lag`, commit latency, rebalance rate | lag *derivative* matters, not lag |
| Kafka producer | record-queue-time, batch-size, buffer-available | back-pressure before it becomes timeouts |
| JVM | `jvm.gc.pause`, allocation rate, `jvm.memory.used`/`committed` | allocation rate predicts pause frequency |
| Virtual threads | `jvm.threads.virtual.live{mounted,queued}`, pinned-event count/duration | auto-configured since Boot 3.5 with `micrometer-java21`; pinning is the silent killer, and note the live-count metric excludes *parked* threads — see micrometer#6504 |
| Aurora MySQL | Performance Insights `db.load` by wait event, connections vs `max_connections`, replica lag | CloudWatch/PI is a separate signal plane; wire it into Grafana or you'll keep two tabs open forever |

`micrometer-java21` JVM metrics reference: <https://docs.micrometer.io/micrometer/reference/reference/jvm.html>

### Profiles: the last rung

Traces tell you *which span*; profiles tell you *which frame*. Grafana **Pyroscope** (2.0 rearchitecture landed April 2026, OTLP-capable) plus **span profiles** links a specific span to the CPU profile captured during it — note that span profiles support CPU (or wall) profiles only.

- <https://grafana.com/docs/pyroscope/latest/configure-client/trace-span-profiles/java-span-profiles/>
- <https://grafana.com/docs/pyroscope/latest/view-and-analyze-profile-data/traces-to-profiles/>
- Pyroscope's Java agent wraps async-profiler; `PYROSCOPE_PROFILER_EVENT=wall` for wall-clock (usually what you want for latency work; CPU profiles hide time spent blocked)
- For deep dives, JFR + JDK Mission Control still beat everything for allocation and lock analysis. Read Gregg's *Systems Performance* (2nd ed.) ch. 2 for methodology and Monica Beckwith's *JVM Performance Engineering* (2024) for the JVM half.

### The loop

1. Pick one SLI with headroom problems. Baseline it — p50/p99/p99.9, with a k6 profile that mirrors production arrival patterns (constant-arrival-rate, not VU-based, to avoid coordinated omission).
2. Form a hypothesis in terms of a *specific queue*.
3. Confirm with trace breakdown (which span owns the p99?) then span profile (which frame?).
4. Change **one** thing.
5. Re-run identical load. Compare distributions, not means. Note the confidence you actually have.
6. Write it down.

Traps: comparing runs across JIT warmup states; measuring during a Grafana query storm you caused; per-pod averaging; forgetting the observer effect of `management.tracing.sampling.probability=1.0`; concluding from a single run.

**Deliverable:** one written performance investigation — baseline distribution, hypothesis, flame graph, one change, after-distribution, and an honest statement of what you can and can't conclude. This makes a strong blog post.

---

## Phase 5 — Detecting outages (3 weeks)

### SLOs and burn rates

The canonical text is the **SRE Workbook, ch. 5 "Alerting on SLOs"** — <https://sre.google/workbook/alerting-on-slos/>. Read all six iterations, not just the last one; the point of the chapter is *why* each naive version fails.

Then Alex Hidalgo, *Implementing Service Level Objectives* (O'Reilly, 2020) for the organizational side — how to pick targets, negotiate them, and handle the case where the SLO says "fine" and users say "broken."

The mechanics to get right:
- **SLI definition**: good events / valid events. The hard part is *valid* — do you count health checks? bot traffic? client-cancelled requests? 4xx? Write it down per SLI, because it changes the number by a lot.
- **Burn rate** = error rate ÷ (1 − SLO). Budget for 99.9% over 30 days is ~43 min.
- **Multi-window multi-burn-rate**: the standard tiers are ~14.4× over 1 h (2% of budget), 6× over 6 h (5%), 1× over 3 d (10%), each paired with a short confirmation window so alerts *reset* quickly. `for:` in Prometheus is **not** equivalent to a long window — `for:` requires continuous violation, a long window integrates.
- **Detection time vs reset time vs precision vs recall** — the four quantities you're trading. Be able to state them for each of your alerts.

Generate the rules instead of hand-writing them:
- **Sloth** — <https://github.com/slok/sloth> — YAML/CRD → recording rules + MWMBR alerts, with published Grafana dashboards
- **Pyrra** — <https://github.com/pyrra-dev/pyrra> — same plus a UI; supports `latencyNative` for native-histogram-backed SLOs
- **OpenSLO** — a vendor-neutral spec if you want portability

### Symptom-based alerting, and the few cause-based exceptions

Page on symptoms (SLO burn). But keep a *small* set of cause-based alerts for things that are certain to become outages and where lead time is everything: pool saturation approaching 100%, disk filling (`predict_linear(node_filesystem_avail_bytes[6h], 4*3600) < 0`), certificate expiry, Kafka consumer lag *growth* sustained above consumption capacity, outbox/DLQ backlog age. Every one of these should have a runbook or it shouldn't page.

### The outages your metrics won't see

This is the section people skip and then get an incident from.

- **No-data / absent alerts.** A crashlooping pod emits no error rate. `absent_over_time(up{job="x"}[10m])`, `absent()` on your key SLI series, and Grafana's no-data state handling.
- **Meta-monitoring.** Who watches Alloy, the Collector, Mimir's ingesters? Scrape the collectors, alert on their queue depth and drop counters, and keep one alert path that does not traverse your own stack (a dead man's switch — a rule that always fires, routed to an external heartbeat check, so silence means the pipeline is dead).
- **Blackbox / synthetic probes.** Metrics from inside the pod can't detect a broken ingress, a bad DNS record, or an expired cert on the LB. `blackbox_exporter` or Grafana Synthetic Monitoring (k6-based) from outside the cluster.
- **Kubernetes probes done properly.** Actuator health groups map to liveness/readiness (`/actuator/health/liveness`, `/actuator/health/readiness`). **Do not put database or downstream checks in liveness** — a slow Aurora failover then restarts every pod simultaneously and turns a degradation into an outage. Readiness may check dependencies; liveness checks only "is this JVM wedged." Pair with graceful shutdown (`server.shutdown=graceful`) and `AvailabilityChangeEvent` so in-flight requests drain.
- **Alerting on the derivative, not the level.** Consumer lag of 50k is fine after a deploy and catastrophic if it's growing. Alert on `deriv()` or on projected time-to-drain.

### Alertmanager and routing

Grouping, inhibition (don't page for 40 pods when the cluster is down), `keep_firing_for`, silences with expiry, and routing severity → page vs ticket. Keep alert rules in Git alongside dashboards. Then read Mike Julian's *Practical Monitoring* (2017) — dated tooling, still the best short treatment of monitoring *anti-patterns* and alert fatigue.

**Deliverable:** SLOs + generated burn-rate rules for one real service, in Git, with a runbook per paging alert. Then run a **game day**: inject a fault (Toxiproxy latency on Aurora, a partition on Kafka, kill a pod's readiness), and measure how long detection actually took. Compare to what the SLO math predicted. Fix the gap.

---

## Phase 6 — Running it on EKS (2 weeks)

- **Alloy** is the collector now. Promtail reached **end of life on 2 March 2026** — if any of your notes or copied configs use it, they're stale. Alloy docs: <https://grafana.com/docs/alloy/latest/>
- **k8s-monitoring Helm chart v4** (April 2026) is a significant break from v3: destinations are a map instead of a list, named Alloy instances replaced by a `collectors` map, and Prometheus Operator CRDs (ServiceMonitor/PodMonitor/Probe) are **no longer bundled** — install `prometheus-operator-crds` separately. There's a migration utility. <https://github.com/grafana/k8s-monitoring-helm>
- **Collector pipeline design**: `k8sattributes` and resource-detection processors (so `service.name`/`namespace`/`pod` are consistent across all three signals — correlation depends on it), `memory_limiter`, `batch`, tail sampling, and the routing/failover exporters.
- **Prometheus vs Mimir**: Prometheus 3 can ingest OTLP directly (receiver is **off by default** — no auth layer, so it's opt-in) and Remote Write 2.0 carries native histograms, exemplars and metadata. Decide whether you need Mimir's long-term storage and multi-tenancy or whether Prometheus + object-storage is enough. Announcement: <https://prometheus.io/blog/2024/11/14/prometheus-3-0/>
- **Cost control**: relabel-drop at the collector, recording rules for anything a dashboard queries repeatedly, per-tenant limits and retention tiers (keep error logs longer than info), and a periodic cardinality review as an actual calendar item.

**Deliverable:** Alloy config + Helm values in Git, with a comment on every drop rule explaining what it removes and why, plus meta-monitoring alerts for the pipeline itself.

---

## Reference shelf

**Read end to end (docs)**
- Spring Boot Actuator: [Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html), [Tracing](https://docs.spring.io/spring-boot/reference/actuator/tracing.html), [Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html)
- Micrometer reference, Observation section first: <https://docs.micrometer.io/micrometer/reference/>
- Grafana OpenTelemetry docs: <https://grafana.com/docs/opentelemetry/>
- Loki, Tempo, Mimir, Pyroscope, Alloy docs (Grafana publishes Markdown versions — append `.md` to any docs URL, and <https://grafana.com/llms.txt> indexes them)
- OpenTelemetry semantic conventions: <https://opentelemetry.io/docs/specs/semconv/>

**Books**
- Brian Brazil, *Prometheus: Up & Running*, 2nd ed. (2023) — the PromQL/Prometheus reference
- Betsy Beyer et al., *Site Reliability Engineering* + *The Site Reliability Workbook* — free at <https://sre.google/books/>
- Alex Hidalgo, *Implementing Service Level Objectives* (2020)
- Daniel Gomez Blanco, *Practical OpenTelemetry* (Apress, 2023) — **Java examples**, the most directly applicable OTel book for you
- Charity Majors, Liz Fong-Jones, George Miranda, *Observability Engineering* (2022) — the high-cardinality-events worldview; useful as an argument even where it conflicts with a metrics-first stack
- Brendan Gregg, *Systems Performance*, 2nd ed. (2020) — methodology chapters especially
- Monica Beckwith, *JVM Performance Engineering* (2024)
- Mike Julian, *Practical Monitoring* (2017) — anti-patterns
- Ted Young & Austin Parker, *Learning OpenTelemetry* (2024) — short, opinionated, mixed reviews; skim rather than buy

**Talks**
- Jonatan Ivanov and Marcin Grzejszczak on Micrometer / the Observation API (SpringOne, Devoxx, GOTO) — the Micrometer maintainers' talks are the closest thing to design-rationale documentation
- Gil Tene, *How NOT to Measure Latency*
- Tom Wilkie on RED and on Prometheus monitoring mixins
- PromCon and GrafanaCON archives on YouTube — PromCon EU 2026 is Oct 7–8 in Munich if you want a target

**Blogs worth subscribing to**
- Grafana Labs blog (LGTM release notes are genuinely informative)
- Robust Perception (<https://www.robustperception.io/blog>)
- Spring blog, "Road to GA" series
- Prometheus blog — the 2026 posts on composite samples and OpenMetrics 2.0 are where the model is heading

**Code to read**
- `micrometer-core`: `MeterFilter`, `DistributionStatisticConfig`, `Observation`/`ObservationHandler` — small, readable, and clarifies what the properties actually do
- `micrometer-registry-otlp`: `OtlpMeterRegistry` histogram handling
- Spring Boot's `spring-boot-micrometer` / `spring-boot-opentelemetry` auto-configurations
- `grafana/docker-otel-lgtm` — the shell scripts show exactly how the components wire together
- `LgtmStackContainer` in testcontainers-java — 100 lines

---

## Traps I'd bet money on

1. **Trace context lost across threads** — coroutines, `@Async`, Kafka listeners, `CompletableFuture`. Write a test that asserts a trace ID survives each boundary. This breaks silently on every refactor.
2. **Exemplars configured but not visible** because you're serving the Prometheus text format instead of OpenMetrics.
3. **`trace_id` as a Loki label.** Million streams, dead ingesters.
4. **Mixed metric naming** (Micrometer vs OTel semconv) across services, discovered when you try to build a fleet-wide dashboard.
5. **Averaged percentiles.** Someone will build the panel. Review dashboards like you review code.
6. **`for: 5m` mistaken for a 5-minute burn window.**
7. **Liveness probes that check the database.** One Aurora failover, full-fleet restart.
8. **Local `spring-boot-docker-compose` magic hiding the fact that production OTLP properties were never set.** Assert them in a startup check.
9. **Alerting on absolute Kafka lag** rather than its growth rate.
10. **No dead man's switch**, so a broken pipeline looks exactly like a healthy system.

---

## Capstone

Two artifacts, both of which force the knowledge to consolidate:

1. **An internal observability standard** for your Kubernetes migration: required meters and naming convention, cardinality budget with enforcement, log label/metadata policy, sampling policy, the SLO template, the dashboard template as code, and the probe/health-group contract. Ten pages, opinionated, with the rationale for each rule. This is the highest-leverage document you can write during a microservices migration, because it's much cheaper to set conventions before forty services exist than after.

2. **A Korean-language blog series** — three posts is a natural shape: (i) Spring Boot 4 + LGTM 연결하기 (the correlation ladder, with the property-namespace gotchas, since almost nothing accurate exists in Korean on Boot 4's OTel starter yet); (ii) 카디널리티와 히스토그램 (the native-histogram/OTLP fork, exemplars, MeterFilter as policy); (iii) SLO와 번레이트 알럼 (MWMBR with real Aurora/Kafka examples). Teaching it in a second language is a brutal test of whether you understand it.
