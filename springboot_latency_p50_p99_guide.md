# Measuring and Improving P50/P99 Latency in a JVM Spring Boot App (AWS ECS → EKS)

This guide explains how to **measure**, **monitor**, **troubleshoot**, and **improve** latency—especially **P50** (median) and **P99** (tail)—for a **production** Spring Boot service running on **AWS ECS**, with future migration to **EKS**.

---

## 1) Percentile latency basics (why P50 vs P99 matters)

Latency is rarely “normal-distributed” in production; it typically has a **long tail**.

- **P50 (median)**: 50% of requests are faster than this. Shows “typical” experience.
- **P95**: 95% of requests are faster than this. Good for “most users” and alerting.
- **P99**: 99% of requests are faster than this. Captures **rare but important outliers** (GC pauses, lock contention, slow queries, timeouts, cold caches).

**How to interpret changes**
- If **P50 and P99 rise together** → broad slowdown (CPU saturation, global regression, config issue).
- If **P50 stays steady but P99 spikes** → intermittent stalls/outliers (GC pauses, slow DB query plans, queueing, downstream latency).

---

## 2) Instrumentation: collecting request latency percentiles

### Option A — Spring Boot Actuator + Micrometer (recommended baseline)
Spring Boot + Actuator automatically records HTTP server timings (e.g., `http.server.requests`).

Enable percentiles/histograms (example):

```yaml
management:
  endpoints:
    web:
      exposure:
        include: "health,info,metrics,prometheus"
  metrics:
    distribution:
      percentiles:
        http.server.requests: 0.5, 0.95, 0.99
      percentiles-histogram:
        http.server.requests: true
```

What to measure beyond HTTP:
- **DB query duration** and **connection pool** usage (HikariCP metrics)
- **Outbound HTTP** call durations and error rates
- **Thread pool** saturation (active threads, queue depth)
- **JVM/GC** pause time and allocation rate

### Option B — OpenTelemetry (metrics + traces + logs)
- Use the **OpenTelemetry Java agent** (`-javaagent`) for auto-instrumentation.
- Export via **OTLP** to an OpenTelemetry Collector, then to Datadog/Prometheus/etc.
- Combine with Micrometer if desired (many teams use Micrometer for metrics and OTel for traces, or unify via OTel).

---

## 3) Monitoring & visualization stacks (ECS and EKS)

### Datadog (paid, strong “all-in-one”)
Best if you want:
- APM tracing + service maps
- Built-in latency percentiles per endpoint
- Logs + metrics + continuous profiling in one place

Typical setup:
- Run **Datadog Agent** as:
  - **ECS**: sidecar container in the same task (or daemon on EC2 launch type)
  - **EKS**: DaemonSet (Helm chart)
- Attach **Datadog Java agent** to your JVM for APM.

Dashboards to build:
- p50/p95/p99 latency (overall + per critical endpoint)
- throughput (RPS/QPS), errors
- JVM GC pause time, heap usage
- DB pool and downstream call latency

### Prometheus + Grafana (OSS)
- Expose `/actuator/prometheus`
- Prometheus scrapes metrics; Grafana visualizes
- In EKS, this is straightforward via Helm/Operator + ServiceMonitor.
- In ECS, it’s doable but you’ll manage more plumbing (scraping/networking).

Prometheus percentile query pattern:
- Use histogram buckets and `histogram_quantile()`.

### AWS CloudWatch (+ X-Ray)
- Works well if you’re already deep in AWS tooling.
- CloudWatch supports percentile statistics for suitable metrics.
- X-Ray (or ADOT → X-Ray) provides tracing.

---

## 4) Troubleshooting: how to find what drives P99

**Start from your “RED” signals**
- **Rate**: RPS
- **Errors**: 4xx/5xx
- **Duration**: p50/p95/p99

Then drill down:
1. **Which endpoints** have the worst p99?
2. **When** does it spike? (deployments, traffic peaks, batch jobs)
3. Correlate with:
   - **GC pause spikes**
   - **CPU throttling / saturation**
   - **Thread pool queue growth**
   - **DB slow queries / pool exhaustion**
   - **Downstream service latency**

### Common culprits (especially for tail latency)
- **Database issues**
  - slow queries, missing indexes, N+1 queries
  - connection pool too small → requests wait for a DB connection
- **Downstream dependency slowness**
  - no timeouts, retries gone wild, slow network, TLS handshake overhead
- **Thread contention / lock contention**
  - synchronized hotspots, blocking calls on request threads
- **GC pauses**
  - too-small heap, high allocation rate, poor GC choice for latency goals
- **Resource limits / container throttling**
  - CPU limits cause throttling → jitter → p99 spikes

### High-value tools
- **Datadog APM**: slow traces, breakdown by spans, DB query timing.
- **Java Flight Recorder (JFR)**: CPU, allocation, lock contention, GC pauses.
- **async-profiler**: CPU / allocation flame graphs.
- **Thread dumps** (`jstack`) during incident: detect BLOCKED/WATING patterns.

---

## 5) Improvements: what typically moves the needle

### Application-level (Spring Boot)
- Fix slow endpoints first (optimize critical paths)
- **DB optimization**
  - add indexes, eliminate N+1, reduce payloads, optimize queries
- Tune **HikariCP** pool size based on load and DB capacity
- Add **timeouts** and sane retry policies for outbound calls
- Use **connection pooling** for outbound HTTP clients
- Add **caching** (Caffeine/Redis) for expensive repeated reads
- Avoid blocking the request thread for long work; use async patterns when appropriate
- Reduce excessive logging in hot paths; prefer async appenders

### JVM / GC
- Ensure stable heap sizing (`-Xms` = `-Xmx`) for predictable behavior
- Use modern collectors (G1 is common; consider ZGC for strict tail goals)
- Monitor allocation rate and GC pause time; address memory churn

### Architecture / platform
- Reduce call-chain depth (tail latencies add)
- Consider async workflows / queues for long-running tasks
- Scale out (tasks/pods) when latency is load-driven
- Use bulkheads / isolation (separate thread pools) to prevent one dependency from tanking the whole service
- Load shedding / fail fast under overload to prevent runaway queueing

---

## 6) Production best practices (so you keep it fast)

- Define latency **SLOs** (e.g., “p95 < 300ms” for key endpoints)
- Alert on sustained p99 regressions and SLO burn rate (avoid alert noise)
- Do **canary deploys** and compare latency vs baseline before full rollout
- Run **load tests** (k6, Gatling, JMeter) and keep historical baselines
- Add **continuous profiling** if you can (Datadog profiler is convenient)
- Track dependency health (DB, caches, downstream services) with their own latency/error SLOs
- Make performance a CI/CD gate for critical operations when practical

---

## Suggested learning path (practical)

1. **Micrometer + Actuator**: timers, histograms, tags, percentiles  
2. **Dashboards & alerting**: p50/p95/p99 + traffic + errors  
3. **Tracing/APM**: identify slow spans (DB, HTTP clients)  
4. **JFR + async-profiler**: CPU, allocation, locks, GC  
5. **Load testing**: reproduce tail issues and verify improvements  
6. **JVM + GC tuning**: verify via metrics/logs, not guesswork  
7. **Reliability patterns**: timeouts, retries, circuit breakers, bulkheads  

---

## Notes for ECS → EKS migration
- EKS makes it easier to run collectors/agents as DaemonSets (Datadog, OTel Collector, Prometheus).
- Standardize on **OpenTelemetry** early if you want portability across vendors.
- Keep consistent tags/labels: `service`, `env`, `version`, `endpoint`.
