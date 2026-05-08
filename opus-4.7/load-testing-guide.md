---
title: "Senior Engineer's Guide to Load Testing as a Performance Discipline"
category: "Performance & Optimization"
description: "Twelve-section narrative guide for Kotlin/Spring Boot on AWS (Aurora, Kafka) covering methodology, percentile math, open-vs-closed loop, JVM tuning, AWS observability, scenarios, tooling, and a learning path."
---

# Senior Engineer's Guide to Load Testing as a Performance Discipline

> **Audience:** senior backend engineer, Kotlin + Spring Boot on AWS (Aurora MySQL, Kafka).
> **Approach:** narrative-first teaching, with code examples inline and bulleted summaries at the end of each section. Twelve sections covering methodology, measurement, tooling, JVM, AWS observability, scenarios, a resource index, and a learning path.
> **Conventions:** ★ = "must read/watch", ☆ = "high-signal supporting material".

---

## Part 1 — Methodology

The methodology layer is where most engineers' load-testing practice goes wrong, and it goes wrong in a specific way: people pick up a tool, point it at a service, and look at the numbers it produces, without first having articulated what question those numbers are supposed to answer. Methodology is the discipline of making that question explicit before you generate a single request.

### 1.1 Types of performance tests — when to use each

The taxonomy of performance tests matters because the names map to actual decisions about test shape and duration. They are not synonyms. A **load test** sustains expected production traffic for long enough to verify that the system meets its SLOs at that level — its question is "does this work at the level we think we'll see?" A **stress test** ramps past expected load to find the breaking point and observe what kind of breakage you get; the question is "where is the cliff, and is the cliff vertical or sloped?" A **spike test** jumps from low to very high traffic suddenly, exercising autoscaling, cold caches, JIT warmup, and connection-pool ramp; the question is "what happens when traffic doubles in thirty seconds?" A **soak test** (sometimes called endurance) runs at moderate load for hours or days to expose the slow-burning failures: memory leaks, file descriptor leaks, log volume issues, certificate refreshes, slow GC drift, Kafka consumer lag accumulation. Its question is "what fails on day two?" A **capacity test** sweeps traffic gradually upward, measuring latency at each step, to map the relationship between throughput and latency — the output is a curve, not a number, and the question is "what is our latency-vs-throughput shape?" Finally a **breakpoint test** is a stress test taken to actual failure to characterize the failure mode itself; the question is "does this fail gracefully or catastrophically?"

Production-realistic load testing usually means running several of these in sequence on the same scenario. The mistake is to call any of them simply "a load test" and conflate them.

**Summary:**
- Six distinct test types: load, stress, spike, soak, capacity, breakpoint — each answers a different question.
- Action: name the test type before running it; a service should ideally have all six in its testing playbook.

### 1.2 SLOs/SLIs as prerequisite

Before any meaningful test, you need a target — a concrete claim about what acceptable performance looks like. The standard formulation is the **service level indicator (SLI)**, which is a measurable quantity (typically a ratio of "good" events to "all events"), and the **service level objective (SLO)**, which is the target value of that SLI over a window. "P99 latency under 300 ms at 5,000 RPS with error rate below 0.1%" is a testable claim. "It should be fast" is not.

The SLO is what makes a test pass or fail. Without it, you're collecting numbers; with it, you're verifying a hypothesis. Modern load testing tools like k6 let you express SLOs directly as test thresholds — the test exits non-zero if the SLO is violated, which means SLO drift is caught in CI rather than in production. A k6 example:

```javascript
// k6 thresholds map directly to SLOs.
// The test fails if any threshold is violated, returning a non-zero exit code,
// which makes SLO regression a CI-time failure rather than a runtime surprise.
export const options = {
  thresholds: {
    // p95 latency for the orders read endpoint must stay under 300ms
    'http_req_duration{endpoint:orders_read}': ['p(95)<300'],
    // p99 latency budget — slightly more generous, but still bounded
    'http_req_duration{endpoint:orders_read}': ['p(99)<800'],
    // error rate budget: 0.1% of requests may fail
    'http_req_failed': ['rate<0.001'],
  },
  scenarios: { /* ... see Section 1.4 ... */ },
};
```

The Google SRE book's *Service Level Objectives* chapter (free at https://sre.google/sre-book/service-level-objectives/) is the canonical reference. The companion SRE Workbook chapter on implementing SLOs is the practical follow-up, and Google CRE's "Art of SLOs" workshop materials at https://sre.google/resources/practices-and-processes/art-of-slos/ are excellent for running a workshop with your own team. Coursera's *Site Reliability Engineering: Measuring and Managing Reliability* (Google Cloud) is a structured course covering the same ground.

**Summary:**
- An SLI is a measurable ratio; an SLO is a target value over a window.
- Action: write the SLI/SLO before any test; encode SLOs as k6 thresholds so CI fails on regression.
- Resources: Google SRE Book Ch. 4, SRE Workbook Ch. 2, Art of SLOs workshop, Coursera Google SRE specialization.

### 1.3 Workload modeling from production data

The next methodological move is workload modeling: deciding what traffic to generate. The naive approach is to hit one endpoint at a constant rate, which almost never matches production. Real production traffic is a *mixture* — multiple endpoints in some ratio, with arrival rates that follow a temporal pattern, with parameter distributions that are skewed, with a mix of cache-warm and cache-cold requests, with realistic sequencing. The closer your model matches production, the more your test predicts production behavior.

The two practical sources for a workload model are production access logs (sample a representative period, extract the endpoint mix and rate) and product analytics (which endpoints matter, which are growth areas). For a Spring Boot service behind an ALB on AWS, the ALB access logs in S3 are the cleanest source; one week of data, processed in a Polars or Pandas notebook, will produce the per-endpoint RPS table and payload-size histograms you need.

A few attributes worth modeling explicitly:

```python
# Sketch of what a workload model summary looks like, derived from ALB logs.
# This is the input you'd feed into k6 scenario weights or Gatling injection profiles.
workload = {
    'endpoint_mix': {
        'GET /api/v1/users/{id}':  0.42,   # 42% of traffic
        'GET /api/v1/orders':      0.28,
        'POST /api/v1/orders':     0.15,
        'GET /api/v1/products':    0.10,
        'POST /api/v1/auth/login': 0.05,
    },
    'arrival_pattern': 'poisson',          # exponential inter-arrival; bursty alternative is pareto
    'peak_rps': 4200,                      # observed peak from ALB metrics
    'parameter_skew': 'pareto(alpha=1.16)', # 80/20 hot-key distribution
    'payload_sizes_p99': 12_400,           # bytes, from access logs
}
```

Tyler Treat's *Benchmarking Message Queue Latency* on bravenewgeek.com is worth reading for what *not* to do; it's a first-person account of getting workload modeling wrong, then right. Artillery's blog post "Understanding workload models" covers the open-vs-closed distinction in workload terms with practical examples.

**Summary:**
- Workload model = endpoint mix + arrival pattern + parameter distribution + payload sizes.
- Action: build a one-week notebook from ALB logs that emits these as structured data, feed directly into k6 scenarios.
- Always model arrival rate, not concurrency, when reproducing user-facing traffic.

### 1.4 Open-model vs closed-model load generation

This is the single most important conceptual choice in load testing, and it's the one that separates tools that produce trustworthy results from tools that quietly lie to you.

A **closed-model** load generator runs a fixed pool of "users," each in a request-then-wait loop. The next request fires only after the previous one returns. Throughput is therefore bounded by latency: if the system slows down, the generator slows down with it.

An **open-model** load generator schedules requests to *arrive* at a fixed rate, regardless of how fast the system is responding. If the system stalls, requests pile up — exactly as they would in production with real users who arrive whether or not previous users are still waiting.

For user-facing services, you almost always want open-model. Real users don't politely wait for the previous user to finish before showing up. The 2006 NSDI paper *Open versus Closed: A Cautionary Tale* by Schroeder, Wierman, and Harchol-Balter is the foundational reference here.

In k6, the executors that give you proper open-model generation are `constant-arrival-rate` and `ramping-arrival-rate`. The contrast looks like this:

```javascript
// CLOSED MODEL — 50 VUs each in a loop. Throughput is whatever this manages
// to achieve given current latency. Hides queueing under saturation.
export const options = {
  scenarios: {
    closed_example: {
      executor: 'constant-vus',
      vus: 50,
      duration: '5m',
    },
  },
};

// OPEN MODEL — 1000 requests/second, regardless of system response time.
// Under saturation, in-flight count grows; this is what you want to see.
export const options = {
  scenarios: {
    open_example: {
      executor: 'constant-arrival-rate',
      rate: 1000,
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 200,   // initial worker pool
      maxVUs: 5000,           // ceiling if rate cannot be sustained with 200
    },
  },
};
```

In Gatling, the equivalent is `injectOpen(constantUsersPerSec(...))` versus `injectClosed(constantConcurrentUsers(...))`.

The closed model isn't useless — it correctly models internal consumer pools and worker fleets. But for HTTP APIs serving end users, default to open-model.

**Summary:**
- Closed model: fixed workers in a loop; hides queueing.
- Open model: requests arrive at a target rate; reveals queueing under load.
- Action: in k6 default to `constant-arrival-rate` / `ramping-arrival-rate`; in Gatling use `injectOpen`.
- Resources: k6 docs "Open and closed models" (https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/); Schroeder et al. NSDI 2006.

### 1.5 Coordinated omission — the core measurement bug

Coordinated omission is the most important measurement concept most people miss, and it's worth a careful walkthrough. The phrase comes from Gil Tene and describes a measurement bug that pervades naive load testing.

Imagine a closed-model test with a fixed pool of virtual users, each running a request-then-wait loop. The system stalls for one second. A user who would have made ten requests during that second instead makes one. When you compute the latency distribution from completed requests, the nine "missing" requests — which would have had latencies of roughly 1000ms, 900ms, 800ms, and so on — never appear in your data. You report a clean tail. Real users, who arrive at the system regardless of whether previous users are still waiting, would have seen those latencies. Your measurement has *coordinated* with the system to *omit* the data that mattered most.

The fix has two parts. First, generate load with an open model (Section 1.4). Second, when recording latencies, use a histogram that supports CO correction. HdrHistogram's `recordValueWithExpectedInterval()` and `copyCorrectedForCoordinatedOmission()` APIs do exactly this — they synthesize the missed samples that *should* have been recorded had the system not stalled, using the expected inter-arrival interval.

```kotlin
// Kotlin example using HdrHistogram with CO correction.
// Without correction, a stall of 1 second hides ~10 implicit "missed" requests
// at 10 req/s; the corrected histogram includes them with synthesized latencies.
import org.HdrHistogram.Histogram

val expectedIntervalMicros = 100_000L  // 10 req/s = 100ms inter-arrival
val histogram = Histogram(3600_000_000L, 3)  // 1-hour max, 3 sig figs

fun recordLatency(latencyMicros: Long) {
    // recordValueWithExpectedInterval automatically synthesizes
    // missed samples if latency exceeds the expected interval
    histogram.recordValueWithExpectedInterval(latencyMicros, expectedIntervalMicros)
}

// After the test:
println("p50: ${histogram.getValueAtPercentile(50.0)} µs")
println("p99: ${histogram.getValueAtPercentile(99.0)} µs")
println("p99.99: ${histogram.getValueAtPercentile(99.99)} µs")
```

Gil Tene's talk *How NOT to Measure Latency* is the canonical introduction; it's been delivered at Strange Loop, QCon, JavaOne, and elsewhere — the Strange Loop 2015 recording at https://www.youtube.com/watch?v=lJ8ydIuPFeU is the most-cited. About forty-five minutes; watch it twice. The HdrHistogram repository at https://github.com/HdrHistogram/HdrHistogram is the reference implementation, with ports for Go, JavaScript, Python, C, and Rust. ScyllaDB's blog post *On Coordinated Omission* (https://www.scylladb.com/2021/04/22/on-coordinated-omission/) is a clear walkthrough with code if you want a written companion to Tene's talk.

When choosing a tool, verify CO behavior: wrk2, Vegeta, k6 with open-model executors, and Gatling with open injection profiles are all CO-safe. Apache Bench, classic wrk, and naive loop scripts are not.

**Summary:**
- Coordinated omission: closed-model generators "skip" sending requests during stalls, hiding the worst latencies from your histogram.
- Fix: open-model generation + CO-correcting histograms (HdrHistogram).
- Action: watch Tene's talk; verify your tool is CO-safe; use HdrHistogram's `recordValueWithExpectedInterval` if you build custom instrumentation.
- Resources: Tene "How NOT to Measure Latency" (Strange Loop 2015); HdrHistogram repo; ScyllaDB blog post.

### 1.6 Little's Law — the only formula you really need

Little's Law states that in any stable queueing system, the average number of items in the system equals the arrival rate times the average time each item spends in the system: **L = λ · W**. In load-testing terms: average concurrency equals throughput times average latency.

This is useful in three concrete ways. First, it lets you size pools: if you serve 200 RPS and your DB query p99 is 50ms, you need at least `200 × 0.050 = 10` in-flight DB operations on average — your connection pool needs to be at least 10, plus headroom for variance. Second, it lets you sanity-check benchmarks: if you measure 1000 RPS and 200ms average latency, you should see roughly 200 in-flight requests; if you see something wildly different, your measurement is wrong somewhere. Third, it constrains the tradeoff space when tuning: you cannot increase throughput without either decreasing latency or accepting more concurrent work.

Martin Thompson's *Software Engineering Radio* episode 201 *Mechanical Sympathy* (2014) at https://se-radio.net/2014/02/episode-201-martin-thompson-on-mechanical-sympathy/ covers Little's Law, Amdahl's Law, and queueing intuitions in a digestible podcast format. Marc Brooker (AWS Distinguished Engineer) writes about queueing theory and capacity at https://brooker.co.za/blog/.

**Summary:**
- L = λ · W: concurrency = throughput × latency.
- Use to size pools, sanity-check benchmarks, reason about throughput-latency tradeoffs.
- Resources: Martin Thompson SE Radio Ep. 201; Marc Brooker's blog.

### 1.7 The latency–throughput curve and the "knee"

When you sweep throughput upward in a capacity test, latency stays roughly flat for a while, then starts climbing, then exhibits a sharp inflection — the **knee** — beyond which latency rises near-vertically and queues grow without bound. Past the knee, the system is saturated; below it, it's responsive.

The knee is your *capacity*. Production should run well below it; the gap between current load and the knee is your headroom. Operating at fifty to seventy percent of the knee is a common rule of thumb. A capacity test that doesn't reach the knee hasn't actually told you where it is.

A useful exercise: before you run the test, predict where you think the knee will be based on your understanding of the bottleneck (database, CPU, thread pool, network). Then run it and see how far off you were. This is how you build intuition about your services.

When plotting results, plot percentiles versus *offered* load, not *achieved* load — achieved-load plots hide the knee because at saturation the offered and achieved diverge.

**Summary:**
- The knee is where p99 begins diverging sharply from p50 — that's your capacity.
- Operate at 50–70% of the knee for headroom.
- Action: in capacity tests use ramping-arrival-rate; plot percentiles vs offered RPS; predict the knee before running.

### 1.8 USE / RED / Four Golden Signals

These three frameworks are checklists for what to look at during analysis. They're complementary, not competing.

The **USE method** (Brendan Gregg) covers resources: for every resource (CPU, memory, disk, network, threads, connection pools, locks), check Utilization, Saturation, and Errors. The **RED method** (Tom Wilkie, Weaveworks/Grafana, ~2015) covers services: for every service or endpoint, track Rate (requests per second), Errors, and Duration. Google's **Four Golden Signals** (SRE book) — Latency, Traffic, Errors, Saturation — is a closely related distillation aimed at SRE-style monitoring.

In practice, layer all three: a Grafana dashboard for a service should have a RED row per endpoint, a USE row per host or container, and Four Golden Signals at the top as the executive summary. Each catches a different category of problem; missing one means missing a class of failure.

The USE method page at https://www.brendangregg.com/usemethod.html is the canonical reference, and Gregg's Linux USE checklist at https://www.brendangregg.com/USEmethod/use-linux.html maps the abstract method onto specific Linux tools.

**Summary:**
- USE = resource view; RED = service view; Four Golden Signals = SRE distillation.
- Layer all three in dashboards; each catches different failure classes.
- Resources: Gregg USE method page + Linux checklist; Wilkie RED method; SRE book Ch. 6.

### 1.9 The "tail at scale" problem

Jeff Dean and Luiz André Barroso's *The Tail at Scale* (CACM 2013, free PDF at https://www.barroso.org/publications/TheTailAtScale.pdf) is the paper that named one of the most important phenomena in distributed performance: when a request fans out to N parallel calls, the user-perceived latency is dominated not by the *average* of those calls but by the worst of them. With N=100 fanout calls, the p63 latency of *each* individual dependency becomes the p99 of the *combined* response. Tail latency of dependencies dominates.

This has profound implications. It means that for any fanout endpoint — a Spring `WebClient` parallel call, a batch Kafka consumer, a microservice composing data from many backends — you need to measure p99.9 of dependencies, not p50. It means that improving the worst case is more valuable than improving the average. And it means that mitigations like hedged requests, tied requests, micro-partitioning, and selective replication (all discussed in the paper) become essential at scale, not optional.

**Summary:**
- Fanout amplifies tail latency: p99 of N parallel calls ≈ p(99^(1/N)) of each.
- Action: measure p99.9 of dependencies for fanout endpoints; consider hedged requests for idempotent reads.
- Resource: Dean & Barroso "The Tail at Scale" (CACM 2013).

### 1.10 Capacity planning fundamentals

Capacity planning is the discipline of translating load test results into infrastructure decisions. The core flow is: measure RPS-per-instance at the SLO-violation point (the knee), forecast peak RPS from product and marketing inputs, compute required instances as `ceil(peak_RPS / per-instance-knee-RPS) × redundancy_factor` (with `redundancy_factor` of at least 1.5 for failure tolerance), and re-validate quarterly because library upgrades, JIT changes, and dependency drift shift the knee over time.

John Allspaw's *The Art of Capacity Planning* (2nd ed, O'Reilly, 2017) is the canonical book. The AWS Well-Architected Performance Efficiency Pillar whitepaper at https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html is the AWS-native complement.

**Summary:**
- Required instances = ceil(peak_RPS / knee_RPS_per_instance) × redundancy.
- Re-measure the knee quarterly; it drifts.
- Resources: Allspaw *The Art of Capacity Planning*; AWS Well-Architected Performance Efficiency Pillar.

---

## Part 2 — Measurement

The measurement layer is where most engineers fool themselves. The methodology tells you what question to ask; measurement tells you whether your answers are honest. Three categories of error dominate: histograms versus samples, averages versus percentiles, and confusing the load generator with the system under test.

### 2.1 HdrHistogram and why histograms beat samples/averages

Sampling latency at one Hertz means you record at most sixty events per minute, and the rare one-in-ten-thousand outlier is invisible. Computing averages of latency loses the shape of the distribution: an average of 999 requests at 1ms and 1 request at 10s is about 11ms, which looks fine and hides a catastrophic outlier.

HdrHistogram (High Dynamic Range Histogram) solves both problems by recording every value into a fixed-precision log-linear bucket structure. Recording is constant-time, memory is fixed (a few hundred KB for microsecond precision over a one-hour range), and percentile queries are lossless up to the configured resolution. It's the right primitive for any latency measurement.

In Spring Boot with Micrometer, the integration is one configuration line:

```kotlin
// In application.yml, enable HdrHistogram-quality buckets for HTTP server requests.
// The buckets are exported to Prometheus/CloudWatch and let you query
// arbitrary percentiles (not just the canned ones) at query time.
management:
  metrics:
    distribution:
      percentiles-histogram:
        http.server.requests: true
      percentiles:
        http.server.requests: 0.5, 0.9, 0.95, 0.99, 0.999
      slo:
        http.server.requests: 100ms, 300ms, 500ms, 1s
```

The HdrHistogram repository at https://github.com/HdrHistogram/HdrHistogram is the reference; the JavaScript port HdrHistogramJS at https://github.com/HdrHistogram/HdrHistogramJS is what k6 uses internally.

**Summary:**
- Histograms (HdrHistogram) preserve distribution shape; samples and averages don't.
- Action: enable `percentiles-histogram` in Spring Boot Actuator config for `http.server.requests`.
- Never trust dashboards showing only "average response time."

### 2.2 Percentile thinking

Percentiles are the right summary of a latency distribution because they directly correspond to user experience. The p50 is the median user, the p95 is the unhappy ninety-fifth, the p99 is the unhappy one percent. Averages don't correspond to any user.

Useful percentiles to track: p50 for typical experience, p90 and p95 for the bulk of users, p99 for the unhappy minority, and p99.9 or p99.99 when capacity planning at scale or when fanout is involved (because as Section 1.9 explained, fanout amplifies tail latency). HdrHistogram is required for the deeper percentiles because samples or coarse buckets can't resolve them accurately.

A useful rule of thumb: in healthy systems, p99/p50 ratio is roughly three to five. Above ten times, something is wrong — contention, GC pauses, cache misses, or coordinated omission in your measurement.

**Summary:**
- Track a percentile spectrum (p50, p90, p95, p99, p99.9), never a single number.
- p99/p50 above 10× indicates contention, GC, cache effects, or measurement bugs.
- Resource: Brendan Gregg "Latency Heat Maps" (https://www.brendangregg.com/HeatMaps/latency.html) for visualization.

### 2.3 Open vs closed model — measurement implications

The choice from Section 1.4 has measurement consequences. Closed-model generators *cannot* report user-perceived latency under saturation: when the system slows, the generator slows, and the queue is hidden in the gap. Open-model generators under saturation produce *unbounded* measured latency — which is exactly the signal you want, because that's what real users would see.

**Summary:**
- Open model under saturation reports unbounded latency (correctly); closed model hides it.
- Action: open model for user-facing endpoints; closed model only for capacity-bounded internal flows.

### 2.4 Statistical thinking — variance, warmup, JIT

Three statistical concerns matter for trustworthy results. First, **run-to-run variance** on cloud VMs is large — typically ten to thirty percent — because of noisy neighbors, network jitter, and shared infrastructure. A single test run is a single sample, not a measurement; for decisions that matter, run five or more repetitions and report median plus interquartile range.

Second, **warmup** is unavoidable on the JVM. The first thirty to one hundred twenty seconds of any load test is unrepresentative due to JIT C1-to-C2 promotion (typically tens of thousands of invocations per hot method), class loading, HikariCP pool ramp, and downstream connection establishment. The first minute of data measures a different system than the one steady-state production runs.

Third, **measurement noise** versus **system noise** must be distinguished. If two test runs give wildly different results, is the measurement noisy or is the system actually behaving differently? Run a no-op control test against a static endpoint to characterize measurement noise.

In k6, warmup is handled by structuring scenarios with explicit phases:

```javascript
// Three scenarios run in sequence: warmup discards measurement, then steady-state
// measurement, then teardown. Only the steady-state scenario contributes to
// the final percentile data we'll act on.
export const options = {
  scenarios: {
    warmup: {
      executor: 'constant-arrival-rate',
      rate: 100, timeUnit: '1s', duration: '60s',
      preAllocatedVUs: 50,
      tags: { phase: 'warmup' },  // tag so we can filter in analysis
    },
    measurement: {
      executor: 'constant-arrival-rate',
      rate: 1000, timeUnit: '1s', duration: '5m',
      preAllocatedVUs: 200, maxVUs: 2000,
      startTime: '60s',  // start after warmup completes
      tags: { phase: 'measurement' },
    },
  },
  // Thresholds only apply to the measurement phase
  thresholds: {
    'http_req_duration{phase:measurement}': ['p(99)<300'],
  },
};
```

Aleksey Shipilëv's *JVM Anatomy Quarks* series at https://shipilev.net/jvm/anatomy-quarks/ is the most concentrated source of JIT and JVM internals knowledge; his blog at https://shipilev.net/ also includes "Arrays of Wisdom of the Ancients," which is the right reference for benchmark methodology generally. For per-method micro-benchmarks (not load tests, but related), Shipilëv's JMH is the only correct tool.

**Summary:**
- Run-to-run variance on cloud VMs is 10–30%; report median + IQR over 5+ runs.
- Always include a 60s warmup phase, tagged separately, that thresholds don't apply to.
- Resources: Shipilëv "JVM Anatomy Quarks"; Shipilëv's JMH for micro-benchmarks.

### 2.5 Detecting load-generator bottlenecks vs system bottlenecks

The mental check during every test: am I measuring the system or the load generator? If you increase the requested load and the achieved load doesn't follow, your generator is bottlenecked. If CPU on the generator is high, network is saturated, or file descriptors are exhausted, you're measuring the generator's limits, not the system's.

Practical checks: `top` and `htop` for CPU; `ss -s` for socket statistics and ephemeral-port exhaustion; `iftop` for bandwidth; AWS NAT gateway throughput limits (5 Gbps and 55,000 simultaneous connections per source IP) if you're testing through one. DNS can also bottleneck: if you don't pin the IP or set a long TTL, you're paying a DNS lookup per request.

A common technique is to run the generator at, say, 80% of its known capacity and verify the system doesn't reach saturation at that level; if it does, you know you have generator headroom for real tests. For loads above roughly 10K RPS, go distributed: k6-operator on Kubernetes, Gatling Enterprise, or Distributed Load Testing on AWS.

**Summary:**
- Always check generator-side metrics (CPU, network, sockets, ports).
- Run generator and target in the same AZ for baseline; cross-region as a separate test.
- Above ~10K RPS, distribute generation (k6-operator, Gatling Enterprise, AWS DLT).

### 2.6 Four-layer simultaneous instrumentation

The discipline that separates serious load testing from amateur load testing is observing all four layers simultaneously during a test, on the same timeline. The four layers are: **application** (Micrometer timers on endpoints and key methods, ideally via `@Observed` annotations), **framework** (Spring Boot Actuator: `http.server.requests`, `hikaricp.connections.*`, `tomcat.threads.*`), **JVM** (GC logs, JFR continuous recording, async-profiler on demand), and **OS/infrastructure** (CloudWatch agent or Node Exporter for hosts; ALB CloudWatch metrics; RDS Performance Insights for databases).

The discipline is to look at all four together when reading results, because the diagnosis depends on the correlation. A latency spike at the application layer that correlates with a major GC pause is a JVM problem. The same spike correlating with HikariCP pending count climbing is a connection pool problem. The same spike correlating with Aurora CPU pegged at 100% is a database problem. The same spike with no correlated infrastructure signal is probably logical contention — a hot lock, a synchronized block, a shared mutable resource. Without simultaneous observation, you're guessing.

```bash
# JVM startup flags that give you observability for free during load tests.
# These costs are negligible (~1% CPU for JFR at default settings) and pay off
# enormously when you need to diagnose a tail-latency event after the fact.
java \
  -Xlog:gc*,safepoint:file=gc.log:time,uptime,level,tags:filecount=10,filesize=100M \
  -XX:StartFlightRecording=duration=0,filename=continuous.jfr,settings=profile \
  -XX:FlightRecorderOptions=maxage=1h,maxsize=1g \
  -jar your-app.jar
```

**Summary:**
- Four layers: application, framework, JVM, OS/infra — observe simultaneously.
- Make all four queryable in the same Grafana stack so you can overlay timelines.
- Always run JFR continuously during tests (~1% overhead).

### 2.7 Profiling during load tests

Profiling turns a load test from a black-box pass/fail into a diagnostic instrument. The three tools to know are async-profiler, JFR, and flame graphs.

**async-profiler** (Andrei Pangin) is a sampling profiler with very low overhead, safe to run in production. It uses `AsyncGetCallTrace` rather than the safe-point-biased `getStackTrace`, which means it captures stacks accurately even during JVM internals. It supports four sampling modes: `cpu` for on-CPU time, `wall` for off-CPU/blocking time, `alloc` for allocation pressure, and `lock` for contention. It produces flame graphs as HTML, JFR for further analysis, or collapsed text format for differential comparison.

**JFR (Java Flight Recorder)** is built into the JDK since version 11 and records a much richer set of events than a sampling profiler — allocation, GC, lock contention, IO, JIT compilation, thread state — at default overhead around one percent. JMC (JDK Mission Control) at https://www.oracle.com/java/technologies/jdk-mission-control.html is the GUI for analyzing the recordings.

**Flame graphs** (Brendan Gregg) visualize sampled stack traces as a stacked bar where height represents stack depth and width represents sample count. Hot code paths become tall, wide plateaus. Differential flame graphs (red/blue overlay between two recordings) make it visually obvious where time moved between conditions.

```bash
# async-profiler invocation during a load test, all four modes in sequence.
# The JFR output is the most flexible — convertible to flame graph or analyzable in JMC.
PID=$(pgrep -f your-app.jar)

# CPU profile during steady-state measurement phase
asprof -d 60 -e cpu -f cpu.html $PID

# Wall-clock profile to find off-CPU hotspots (DB waits, lock contention, IO)
asprof -d 60 -e wall -f wall.html $PID

# Allocation profile to find GC pressure sources
asprof -d 60 -e alloc -f alloc.html $PID

# Lock contention profile
asprof -d 60 -e lock -f lock.html $PID

# Differential between baseline and saturated load — shows where time moved
asprof -d 60 -e cpu -o collapsed -f baseline.collapsed $PID
# ... run again under high load ...
asprof -d 60 -e cpu -o collapsed -f saturated.collapsed $PID
flamegraph.pl --diff <(diff -u baseline.collapsed saturated.collapsed) > diff.svg
```

The async-profiler README at https://github.com/async-profiler/async-profiler is good but terse; Krzysztof Slusarski's *async-profiler manual by use cases* at https://krzysztofslusarski.github.io/2022/12/12/async-manual.html is the most practical hands-on guide outside the official docs. Brendan Gregg's flame graph repository at https://github.com/brendangregg/FlameGraph and his ACM Queue paper at https://queue.acm.org/detail.cfm?id=2927301 cover flame graphs in depth; his USENIX ATC 2017 talk *Visualizing Performance with Flame Graphs* at https://www.usenix.org/conference/atc17/program/presentation/gregg-flame is the recorded version.

**Summary:**
- async-profiler: low-overhead sampling, four modes (cpu/wall/alloc/lock).
- JFR: richer events, ~1% overhead, JMC for analysis.
- Flame graphs: visualize sampled stacks; differential graphs compare conditions.
- Action: run async-profiler `cpu` for every test phase; compare with differential graphs.
- Resources: async-profiler repo; Slusarski's manual; Gregg's flame graph site.

---

## Part 3 — Tooling Tour

With methodology and measurement established, tools become much easier to evaluate. The three primary tools you'll actually use day-to-day are k6, Gatling, and Artillery. Beyond those, a handful of specialized tools earn their place for specific jobs.

### 3.1 k6 (Grafana Labs) — primary recommendation

k6 is currently the best default for HTTP and gRPC load testing in most contexts. It's a Go binary with a JavaScript scripting layer (Goja, a Go-native JS interpreter), which sounds odd for performance work but in practice is fine because the actual request execution happens in compiled Go and only your test logic runs in JS. The executor model is genuinely open-model from the start, with `constant-arrival-rate` and `ramping-arrival-rate` as first-class citizens. Threshold-as-SLO is built in. Output integrations to Prometheus remote-write, InfluxDB, CloudWatch, and JSON are first-class. k6-operator at https://github.com/grafana/k6-operator handles distributed execution on Kubernetes; Grafana Cloud k6 (formerly k6 Cloud) is the managed alternative.

A complete k6 scenario for a Spring Boot service looks like this:

```javascript
// Full example: warmup + capacity sweep + threshold validation + Prometheus output.
// Run: K6_PROMETHEUS_RW_SERVER_URL=http://prom:9090/api/v1/write \
//      k6 run -o experimental-prometheus-rw orders-test.js
import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

const ordersLatency = new Trend('orders_latency_ms', true);  // custom HdrHistogram-backed metric

export const options = {
  scenarios: {
    warmup: {
      executor: 'constant-arrival-rate',
      rate: 100, timeUnit: '1s', duration: '60s',
      preAllocatedVUs: 50,
      tags: { phase: 'warmup' },
    },
    sweep: {
      executor: 'ramping-arrival-rate',
      startRate: 100, timeUnit: '1s',
      preAllocatedVUs: 200, maxVUs: 5000,
      stages: [
        { target: 500, duration: '2m' },
        { target: 1000, duration: '2m' },
        { target: 2000, duration: '2m' },
        { target: 4000, duration: '2m' },   // expecting the knee somewhere here
      ],
      startTime: '60s',
      tags: { phase: 'sweep' },
    },
  },
  thresholds: {
    // SLO: p99 latency under 300ms during measurement phase only
    'http_req_duration{phase:sweep}': ['p(99)<300'],
    // Error budget: 0.1%
    'http_req_failed{phase:sweep}': ['rate<0.001'],
  },
};

export default function () {
  const customerId = Math.floor(Math.random() * 100000);  // hot-key skew comes later
  const res = http.get(`https://api.example.com/v1/orders?customerId=${customerId}`, {
    tags: { endpoint: 'orders_read' },
  });
  ordersLatency.add(res.timings.duration);
  check(res, { 'status is 200': (r) => r.status === 200 });
}
```

The k6 documentation at https://grafana.com/docs/k6/latest/ is high-quality; the Executors reference at https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/ and the Thresholds page at https://grafana.com/docs/k6/latest/using-k6/thresholds/ are worth reading end to end. Test Automation University's free course *Tools and Techniques for Performance and Load Testing* (Leandro Melendez, k6) at https://testautomationu.applitools.com/performance-and-load-testing/ is the structured-course option.

**Summary:**
- k6 = best default: Go core, JS scripting, open-model executors, threshold-as-SLO.
- Action: standardize on k6 for HTTP/REST/gRPC; export to Prometheus remote-write into your existing Grafana.
- Resources: k6 docs (Executors, Thresholds, Outputs); k6-operator; TAU course.

### 3.2 Gatling — second tool when JVM-native is needed

Gatling is the right choice when test code needs to import your Kotlin domain models, hit Aurora directly via JDBC for data setup, or share libraries with the system under test. It's JVM-native (Akka/Netty under the hood), supports Scala, Java, and Kotlin DSLs, and is open-model by default. The HTML reports it produces are the best in the category for stakeholder communication.

A Kotlin Gatling scenario, integrated into your Gradle build at `src/gatling/kotlin/`:

```kotlin
// build.gradle.kts:
//   plugins { id("io.gatling.gradle") version "3.13.0" }  // verify current version on Gradle Plugin Portal
// Run with: ./gradlew gatlingRun-com.example.OrdersSimulation

import io.gatling.javaapi.core.CoreDsl.*
import io.gatling.javaapi.http.HttpDsl.*
import io.gatling.javaapi.core.Simulation

class OrdersSimulation : Simulation() {

    private val httpProtocol = http
        .baseUrl("https://api.example.com")
        .acceptHeader("application/json")
        .userAgentHeader("gatling-load-test")

    private val readScenario = scenario("Orders read")
        .exec(
            http("orders_read")
                .get("/v1/orders?customerId=#{customerId}")
                .check(status().`is`(200))
        )

    private val customerIdFeeder = generateSequence {
        // Pareto distribution for hot-key skew — most traffic hits a small set of customers
        mapOf("customerId" to (Math.random().pow(1.16) * 100000).toInt())
    }.iterator()

    init {
        setUp(
            readScenario
                .feed(customerIdFeeder)
                .injectOpen(
                    // Open-model injection: arrivals scheduled regardless of response time
                    nothingFor(60),                              // warmup gap before measurement
                    rampUsersPerSec(100.0).to(4000.0).during(8 * 60),  // 8-minute capacity sweep
                )
        ).protocols(httpProtocol)
         .assertions(
             // Gatling's equivalent of k6 thresholds — SLO encoded in the test
             global().responseTime().percentile3().lt(300),  // p95 < 300ms
             global().failedRequests().percent().lt(0.1),
         )
    }
}
```

The Gatling docs at https://docs.gatling.io/ and the Gradle plugin docs at https://docs.gatling.io/integrations/build-tools/gradle-plugin/ are the canonical references. Philip Riecks's *Write Gatling Performance Tests with Java* at https://rieckpil.de/write-gatling-performance-tests-with-java/ shows a Spring Boot integration; the Kotlin demo project at https://github.com/gatling/gatling-gradle-plugin-demo-kotlin is the right starting template. Gatling Academy at https://gatling.io/academy/ is free.

**Summary:**
- Gatling = JVM-native option: Kotlin DSL, Gradle integration, open-model by default.
- Use when test code needs to import production code or hit Aurora for setup.
- Best HTML reports in the category — useful for stakeholder communication.
- Resources: Gatling docs; Riecks's Spring Boot example; Gatling Academy.

### 3.3 Artillery — third option, JS/YAML

Artillery (Node.js, YAML or JS scenarios) has stronger "scenario-as-YAML" ergonomics than k6 and a plugin ecosystem. Its `arrivalRate` phase is open-model; its constant-VU phases are closed. For a senior backend engineer in a Kotlin/Spring Boot shop, k6 wins on ergonomics, ecosystem, and threshold story — but Artillery is worth knowing if your test scenarios need to live as declarative YAML alongside infrastructure-as-code, or if your team is more comfortable in Node.js. The Artillery docs at https://www.artillery.io/docs and their blog post *Understanding workload models* at https://www.artillery.io/blog/load-testing-workload-models are honest about where Artillery sits on the open/closed spectrum.

**Summary:**
- Artillery = YAML-first; arrivalRate is open-model.
- Worth knowing but k6 is better default for JVM shops.
- Resources: Artillery docs; "Understanding workload models" blog post.

### 3.4 wrk2 — Gil Tene's CO-correct HTTP probe

wrk2 (https://github.com/giltene/wrk2) is a small specialized C tool by Gil Tene himself that generates a constant request rate against a single endpoint and produces coordinated-omission-corrected latency histograms. Use it as a sanity check against your full k6 or Gatling scenarios, or for the simplest possible "what is the true p99.9 of one endpoint at N RPS" experiments. Maintenance has been minimal in recent years, but it remains the reference implementation of CO correction.

**Summary:**
- wrk2 = single-endpoint, constant-throughput, CO-correct.
- Use as cross-check against k6/Gatling or for minimal capacity probes.

### 3.5 JMeter — older, still ubiquitous

Apache JMeter (https://jmeter.apache.org/) is the elder statesman of load testing — JVM-based, GUI-driven with XML test plans, large plugin ecosystem. It works, and a lot of enterprise tooling assumes it. Its weaknesses are an awkward GUI workflow that resists code review, an aging concurrency model that's closed-model by default, and verbose XML test definitions. If your organization already has JMeter expertise and CI integration, fine; otherwise prefer k6 or Gatling.

**Summary:**
- JMeter = ubiquitous in enterprises but ergonomically dated; closed-model by default.
- Use only if you inherit it.

### 3.6 Vegeta, hey, bombardier — simple Go HTTP probes

Three small Go tools cover the "I just want to hit one endpoint at N RPS from the command line" niche. **Vegeta** (https://github.com/tsenart/vegeta) is the most capable: open-model by default with `-rate`, HDR-aware reports, distributable via shell pipelines, and explicitly CO-aware. **hey** (https://github.com/rakyll/hey) is a simpler ab-replacement. **bombardier** (https://github.com/codesenberg/bombardier) is fast and uses fasthttp. Use these for quick capacity probes, smoke tests in CI, and producing baseline RPS numbers with one command.

**Summary:**
- Vegeta/hey/bombardier = single-endpoint, command-line, open-model.
- Use for smoke tests and quick capacity probes; not full scenarios.

### 3.7 Locust — Python

Locust (https://locust.io/) is gevent-based, distributed, with Python-native scenarios. Use it if your team is in Python and wants to call internal Python libraries from load scripts. Its open-model story is weaker than k6's; for a Kotlin/Spring Boot shop, stick with k6.

**Summary:**
- Locust = Python-native; weaker open-model story than k6.
- Use only if Python ecosystem is dominant.

### 3.8 Toxiproxy and AWS FIS — chaos and network conditions

Real production failures are rarely pure load — they're load combined with degraded dependencies. **Toxiproxy** (Shopify, https://github.com/Shopify/toxiproxy) is a TCP proxy with injectable "toxics": latency, bandwidth limit, slow_close, timeout, slicer, limit_data, reset_peer. It exposes an HTTP API so toxics can be enabled and disabled programmatically during tests, which makes it deterministic for integration testing. **AWS Fault Injection Service (FIS)** at https://aws.amazon.com/fis/ is the AWS-native equivalent for resource-level chaos: stop EC2 instances, throttle APIs, pause EBS IO, inject EKS pod CPU stress or network latency, fail over RDS.

```bash
# Toxiproxy example: inject 500ms latency between Spring Boot and Aurora
# during a sustained k6 load test, then verify the service stays within SLO.

# Create proxy in front of Aurora writer
curl -X POST http://toxiproxy:8474/proxies -d '{
  "name": "aurora-writer",
  "listen": "0.0.0.0:3306",
  "upstream": "myapp.cluster-abc123.ap-northeast-2.rds.amazonaws.com:3306"
}'

# Inject 500ms latency toxic
curl -X POST http://toxiproxy:8474/proxies/aurora-writer/toxics -d '{
  "name": "slow_db",
  "type": "latency",
  "attributes": {"latency": 500, "jitter": 50}
}'

# Now run k6 — observe how the service degrades
# (hopefully: timeouts trip, circuit breakers open, requests fail fast)
k6 run scenarios/orders-test.js

# Remove toxic and verify recovery
curl -X DELETE http://toxiproxy:8474/proxies/aurora-writer/toxics/slow_db
```

AWS publishes guidance on FIS for RDS at https://aws.amazon.com/blogs/devops/chaos-experiments-on-amazon-rds-using-aws-fault-injection-simulator/ and for EKS pods at https://aws.amazon.com/blogs/containers/aws-fault-injection-simulator-supports-chaos-engineering-experiments-on-amazon-eks-pods/.

**Summary:**
- Toxiproxy = TCP-level chaos: latency, packet loss, connection reset.
- AWS FIS = managed AWS-resource chaos: EC2 stop, EKS pod stress, RDS failover.
- Action: in dev, put Toxiproxy in front of Aurora and Redis; in staging, script FIS experiments paired with sustained load tests.

### 3.9 Distributed Load Testing on AWS

AWS publishes a reference solution at https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws/ (GitHub: https://github.com/aws-solutions/distributed-load-testing-on-aws) that orchestrates ECS Fargate runners, has a web console, scheduling, multi-region orchestration, and supports JMeter, k6, and Locust via Taurus. Worth reading the architecture even if you don't deploy it directly — the patterns transfer to a self-built k6-on-EKS setup. Less polished than Grafana Cloud k6 or Gatling Enterprise, but free and AWS-native.

**Summary:**
- AWS DLT = published reference solution: ECS Fargate, multi-region, JMeter/k6/Locust via Taurus.
- Read the architecture; deploy it if you want managed distributed runners without paying for SaaS.

---

## Part 4 — JVM Specifics

The JVM has performance characteristics that bite Spring Boot apps in predictable ways under load, and learning them turns mysterious latency spikes into recognizable signatures.

### 4.1 GC — choose for the workload

Garbage collection is the most common source of tail latency in Spring Boot services. The current generation of collectors offers a real choice for the first time, and the choice matters.

**G1GC**, the default since JDK 9, is generational and balances throughput against pause time, targeting around 200ms pauses by default. It's the right starting point for typical Spring Boot services with heaps in the 4–32 GB range and a pause SLO of 50ms or higher. Tuning is mostly `-XX:MaxGCPauseMillis`.

**ZGC** offers sub-millisecond pauses and scales to terabyte heaps. Generational ZGC is the default mode in JDK 23 and later (the non-generational variant has been deprecated and is being removed). The cost is roughly 5–15% more CPU and 15–30% more memory headroom compared to G1. Use ZGC when measured GC pauses cause p99 SLO violations, when heap is large, or when tail latency is non-negotiable.

**Shenandoah** (Red Hat) offers similar low-pause behavior with lower memory overhead than ZGC, and supports compressed oops. It became non-experimental in JDK 25 and is a reasonable middle-ground for moderate heaps.

**Parallel GC** is pure throughput with long pauses; only use for batch jobs and ETL where pause time doesn't matter.

A practical decision rule for a Spring Boot service: start with G1 and a 100ms pause target. If load tests show p99 violations correlated with GC events, switch to Generational ZGC. Always log GC.

```bash
# G1 baseline configuration
-XX:+UseG1GC
-XX:MaxGCPauseMillis=100
-Xlog:gc*,safepoint:file=gc.log:time,uptime,level,tags:filecount=10,filesize=100M

# Switch to ZGC when load tests show GC-correlated p99 violations
-XX:+UseZGC                       # generational ZGC default in JDK 23+
-XX:+UnlockExperimentalVMOptions  # may not be needed depending on JDK version
```

Aleksey Shipilëv's blog at https://shipilev.net/ remains the primary source on GC internals. Datadog's *A deep dive into Java garbage collectors* at https://www.datadoghq.com/blog/understanding-java-gc/ is a good practitioner-level overview.

**Summary:**
- G1 = default for typical workloads; tune `MaxGCPauseMillis`.
- ZGC = sub-ms pauses, large heaps; generational by default in JDK 23+.
- Shenandoah = ZGC alternative with lower memory overhead.
- Action: log GC always; switch from G1 to ZGC when GC pauses correlate with p99 violations.
- Resources: Shipilëv's blog; Datadog GC blog post.

### 4.2 JIT warmup and autoscaling

The JVM starts in interpreted mode, then C1 compiles, then C2 compiles hot methods. Inlining decisions stabilize after thousands of invocations. The first 30 to 120 seconds of any load test on a fresh JVM is measuring a different system than steady-state.

This matters enormously for autoscaling. When a new instance launches under spike load, it serves slowly for the first minute even though ALB health checks pass. The first 1% of traffic to that instance sees cold-JVM latency; under spike conditions where many new instances launch, that fraction becomes much larger.

Mitigations include CDS (Class Data Sharing) via `-XX:ArchiveClassesAtExit` and `-XX:SharedArchiveFile` to amortize class loading. CRaC (Coordinated Restore at Checkpoint) gives near-instant warm starts and is supported by AWS Lambda SnapStart for Java. A simpler approach is a synthetic warmup curl loop in the container entrypoint, hitting hot endpoints before the container joins the load balancer. Another simple measure is tuning tier compilation: `-XX:TieredStopAtLevel=1` for short-lived processes that won't benefit from C2.

The bottom line: don't run a 30-second load test and call it capacity. You measured warmup, not steady state.

**Summary:**
- JIT C1→C2 promotion takes 10K–100K invocations per hot method; 30s tests measure warmup.
- Action: include 60s+ warmup phase in tests; for autoscaling, measure cold-start separately.
- Mitigations: CDS, CRaC (Lambda SnapStart), entrypoint warmup curl, tier tuning.

### 4.3 HikariCP pool sizing

HikariCP pool sizing is the parameter that goes wrong most often. The intuitive approach — "more connections is better" — is wrong. Each connection consumes database resources (memory, file descriptors, lock state); above a threshold determined by database concurrency capacity, more connections increase contention and reduce throughput.

Brett Wooldridge's *About Pool Sizing* wiki page at https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing is required reading. The core formula for *deadlock avoidance* (a different concern from throughput optimization) is `pool ≥ Tn × (Cm − 1) + 1`, where `Tn` is the number of threads that may concurrently use the pool and `Cm` is the maximum simultaneous connections any one thread may hold. The throughput-optimal pool size is generally surprisingly small — often `cores × 2 + spindle_count` for the database side.

For Aurora MySQL specifically, the practical heuristic is: per-instance pool size ≈ `(db_cores × 2) / app_instance_count`. For a `db.r6g.large` (2 vCPU) and a fleet of four app instances, ten connections per app instance is plenty. Set `connectionTimeout` to 5–10 seconds to fail fast rather than queueing forever. Set `maxLifetime` shorter than Aurora's `wait_timeout` minus a safety margin (30 seconds). Enable `leakDetectionThreshold` of 60 seconds in non-production environments.

```kotlin
// Spring Boot HikariCP configuration for a Spring Boot service against Aurora MySQL.
// The numbers are starting points — load test, observe `hikaricp.connections.pending`,
// then adjust. Pending > 0 sustained = pool too small for this throughput.
@Configuration
class DataSourceConfig {

    @Bean
    fun dataSource(): HikariDataSource = HikariConfig().apply {
        jdbcUrl = "jdbc:mysql://aurora-cluster.cluster-xyz.ap-northeast-2.rds.amazonaws.com:3306/app"
        // Pool size — small is fast; tune from load tests, not intuition
        maximumPoolSize = 10
        minimumIdle = 10        // keep pool at fixed size to avoid ramp during spikes

        connectionTimeout = 5_000      // fail fast — 5s queue then exception
        maxLifetime = 1_770_000        // 29.5 min, less than Aurora wait_timeout (1800s default)
        idleTimeout = 600_000          // 10 min — irrelevant if minIdle == maxPool
        leakDetectionThreshold = 60_000 // log if a connection held > 60s

        // Performance Insights friendliness: tag connections so you can attribute load
        connectionInitSql = "SET session sql_mode='STRICT_TRANS_TABLES'"
    }.let(::HikariDataSource)
}
```

When you put Aurora behind RDS Proxy, you pool against the proxy rather than the database; the proxy gives you transaction-level multiplexing for MySQL with autocommit. AWS's Aurora MySQL DBA Handbook at https://docs.aws.amazon.com/whitepapers/latest/amazon-aurora-mysql-db-admin-handbook/welcome.html covers this in detail.

**Summary:**
- Smaller pools usually beat larger ones — past `cores × 2`, contention rises super-linearly.
- Action: start with `(db_cores × 2) / app_instances` per pool; tune based on `hikaricp.connections.pending`.
- Set `connectionTimeout` 5–10s, `maxLifetime` < Aurora `wait_timeout` − 30s.
- Resources: Wooldridge "About Pool Sizing" wiki; Aurora DBA Handbook.

### 4.4 Tomcat thread pool

Tomcat thread pool sizing follows similar logic to connection pools. The default `maxThreads` is 200. For a synchronous Spring Boot service backed by a database, total throughput is bounded by `min(thread_pool, db_pool) / avg_request_time`. Increasing `maxThreads` past the database pool just queues requests at the database — you've moved the queue but not shortened it.

In Tomcat's NIO connector (Spring Boot's default), `maxThreads` and `maxConnections` are decoupled: the thread pool services *processing*, while `maxConnections` (default 8192) caps *concurrently accepted* connections. For I/O-bound services with slow downstreams, you can have many more connections than threads, with threads servicing requests as they become ready. For CPU-bound services, `maxThreads ≈ cores × 1.5–2` is the sweet spot — more threads cause context-switching overhead.

```yaml
# Spring Boot application.yml — Tomcat tuning for a typical I/O-bound service
server:
  tomcat:
    threads:
      max: 100              # processing threads — match to typical concurrency
      min-spare: 20         # keep 20 warm to avoid ramp-up under spike
    max-connections: 5000   # accepted connections — much larger than threads for I/O-bound
    accept-count: 100       # OS-level queue when at maxConnections
    connection-timeout: 5s
```

Spring Boot 3.2 and later supports virtual threads via `spring.threads.virtual.enabled=true`, which radically changes the equation: threads are no longer the scarce resource, and you can return to a synchronous-style programming model without sacrificing concurrency. For new Spring Boot 3.2+ services, this is worth adopting; the load test becomes much easier because you're no longer tuning thread pool size.

**Summary:**
- I/O-bound: maxThreads 50–200, maxConnections 5K–10K (NIO decouples them).
- CPU-bound: maxThreads ≈ cores × 1.5–2.
- Action: in Spring Boot 3.2+, evaluate virtual threads (`spring.threads.virtual.enabled=true`).
- Resource: Datadog "Tomcat architecture and key performance metrics."

### 4.5 Reactive stack tuning (Spring WebFlux + Reactor Netty)

Reactive stacks have an entirely different tuning model. The Netty event loop has a small number of threads — typically 2× core count — and any blocking call on those threads kills throughput. The most common bug is a `Mono.fromCallable(jdbcCall)` without subscribing on a bounded elastic scheduler — every request blocks an event loop thread and concurrency collapses.

Diagnosing this requires watching event loop saturation during a load test and detecting blocking calls in development. **BlockHound** (Project Reactor, https://github.com/reactor/BlockHound) is a Java agent that throws `BlockingOperationError` when a blocking call (Thread.sleep, JDBC, blocking IO) runs on a non-blocking thread. Use it in test scope on every WebFlux service.

```kotlin
// In your test setup — installs once per JVM, catches blocking calls everywhere
class BlockHoundSetup {
    init {
        // Throws BlockingOperationError if any blocking call happens on a Reactor scheduler thread.
        // Catches the most common WebFlux bug: accidental JDBC/sleep on the event loop.
        BlockHound.install()
    }
}

// Tuning the outbound WebClient connection pool — usually the bottleneck after blocking calls
@Bean
fun webClient(): WebClient {
    val provider = ConnectionProvider.builder("custom")
        .maxConnections(500)                              // per-host max
        .pendingAcquireMaxCount(1000)                     // queue size when saturated
        .pendingAcquireTimeout(Duration.ofSeconds(2))     // fail fast under saturation
        .maxIdleTime(Duration.ofSeconds(30))
        .build()

    val httpClient = HttpClient.create(provider)
        .responseTimeout(Duration.ofSeconds(3))
        .option(ChannelOption.SO_BACKLOG, 1024)           // OS accept queue
        .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 2000)

    return WebClient.builder()
        .clientConnector(ReactorClientHttpConnector(httpClient))
        .build()
}
```

Piotr Mińkowski's *A Deep Dive Into Spring WebFlux Threading Model* at https://piotrminkowski.com/2020/03/30/a-deep-dive-into-spring-webflux-threading-model/ is the best practitioner deep-dive on the Reactor scheduler model.

**Summary:**
- WebFlux: any blocking call on the event loop kills concurrency.
- Action: BlockHound in test scope always; tune ConnectionProvider for outbound WebClient.
- Resources: BlockHound repo; Mińkowski "Deep Dive Into Spring WebFlux Threading Model."

### 4.6 Books on JVM performance

For depth, Scott Oaks's *Java Performance* (2nd ed, O'Reilly, 2020) is the best end-to-end JVM performance book. Brendan Gregg's *Systems Performance* (2nd ed, Pearson, 2020) covers methodology and OS-layer tools. Gregg's *BPF Performance Tools* (Pearson, 2019) is the eBPF reference for Linux deep-dives. Martin Kleppmann's *Designing Data-Intensive Applications* (O'Reilly, 2017) provides context for distributed performance reasoning. Alex Petrov's *Database Internals* (O'Reilly, 2019) explains what's actually happening under your queries. Silvia Botros and Jeremy Tinley's *High Performance MySQL* (4th ed, O'Reilly, 2021) is the current MySQL performance book. Michael Nygard's *Release It!* (2nd ed, Pragmatic, 2018) covers the failure-mode patterns: circuit breakers, bulkheads, stability.

**Summary:**
- Oaks "Java Performance" 2nd ed = JVM perf bible.
- Gregg "Systems Performance" 2nd ed = methodology + OS tools.
- Nygard "Release It!" = failure modes you're trying to expose.
- Kleppmann "Designing Data-Intensive Applications" = distributed context.
- Petrov "Database Internals" + Botros/Tinley "High Performance MySQL" 4th ed = DB layer.

---

## Part 5 — AWS CloudWatch + Spring Boot Observability

Connecting application instrumentation to AWS so you can read it during and after a load test is, in 2026, mostly a Micrometer story.

### 5.1 Micrometer as the foundation

Spring Boot 3 unified observability through the **Micrometer Observation API**, which emits metrics, traces, and contextual logs from a single instrumentation point. The `@Observed` annotation produces both a metric (timer) and a span (trace) from the same method. This is the right primitive for any new instrumentation.

```kotlin
// @Observed produces both a Micrometer Timer (for percentiles in Prometheus/CloudWatch)
// and an OpenTelemetry span (for distributed tracing in Tempo/Jaeger/X-Ray).
// Single source of truth — name, tags, and contextual data shared across signals.
@Service
class OrderService {

    @Observed(
        name = "orders.fetch",
        contextualName = "fetch-orders-by-customer",
        lowCardinalityKeyValues = ["operation", "fetch"]
    )
    fun fetchOrders(customerId: String): List<Order> {
        // ... business logic ...
        // Both a Micrometer Timer named "orders.fetch" and a tracing span are
        // produced automatically. Configure histogram buckets via application.yml.
    }
}
```

```yaml
# application.yml — emit HdrHistogram-quality buckets and tracing for the @Observed methods
management:
  metrics:
    distribution:
      percentiles-histogram:
        orders.fetch: true
        http.server.requests: true
      percentiles:
        orders.fetch: 0.5, 0.9, 0.95, 0.99, 0.999
  tracing:
    sampling:
      probability: 1.0   # full sampling during load tests; reduce in production
  prometheus:
    metrics:
      export:
        enabled: true
```

Spring Boot's observability documentation at https://docs.spring.io/spring-boot/reference/actuator/observability.html and the Spring Framework observability reference at https://docs.spring.io/spring-framework/reference/integration/observability.html are the canonical sources. The Spring Blog post *Observability with Spring Boot 3* at https://spring.io/blog/2022/10/12/observability-with-spring-boot-3/ is the original announcement and a good orientation.

**Summary:**
- Micrometer Observation API = single instrumentation, three signals (metrics, traces, logs).
- Action: use `@Observed` on important methods; enable `percentiles-histogram` in config.
- Resources: Spring Boot observability docs; Spring Framework observability reference; "Observability with Spring Boot 3" blog post.

### 5.2 Two architectures — pick consciously

There are two reasonable architectures for getting Spring Boot metrics into AWS observability.

**Architecture A** publishes Micrometer metrics directly to CloudWatch using `micrometer-registry-cloudwatch2`. Pros: no new infrastructure; metrics flow to CloudWatch every minute or so. Cons: CloudWatch's per-metric pricing makes it expensive at scale; high-cardinality dimensions multiply costs quickly; CloudWatch's 1-minute default granularity is too coarse for load test analysis.

**Architecture B** publishes metrics to Prometheus (Amazon Managed Prometheus) and visualizes through Grafana (Amazon Managed Grafana), with CloudWatch capturing only AWS-native infrastructure metrics (ALB, RDS, ECS). Pros: sub-second resolution, full label cardinality without per-label cost, PromQL, ecosystem of dashboards. Cons: more moving pieces; requires the ADOT (AWS Distro for OpenTelemetry) collector or Prometheus on EKS.

For serious load testing work, Architecture B is the right choice. Sub-second granularity matters enormously when you're trying to correlate a 200ms latency spike with a GC pause. AMP at https://aws.amazon.com/prometheus/ and AMG at https://aws.amazon.com/grafana/ remove the operational burden, and the ADOT collector at https://aws-otel.github.io/ is the standard scraping path.

**Summary:**
- Architecture A: Micrometer → CloudWatch direct. Simple but coarse and expensive at scale.
- Architecture B: Micrometer → AMP + AMG, CloudWatch for infra. Better for serious work.
- Action: standardize on Architecture B for load testing observability.

### 5.3 Tracing

Tracing complements metrics by showing the full path of a slow request — which downstream calls took how long, where the time actually went. Spring Boot 3's `@Observed` produces spans automatically; the question is where to send them.

**AWS X-Ray** is managed and integrates natively with ALB and Lambda, but its query expressiveness is limited. **Tempo** (Grafana) on AMG offers better correlation with Prometheus exemplars — clicking a slow request in a Grafana panel can drop you directly into the trace. **Jaeger** is fine but largely subsumed by Tempo in new deployments.

The recommendation: OpenTelemetry + Tempo on AMG when you want best-in-class correlation with metrics; X-Ray when you need ALB and Lambda end-to-end out of the box without deploying anything.

**Summary:**
- Spring Boot 3 @Observed → span automatically; pick your backend.
- Tempo on AMG = best metric-trace correlation.
- X-Ray = AWS-native, ALB/Lambda end-to-end.

### 5.4 ALB metrics that matter

When testing through an ALB, a specific subset of CloudWatch metrics tells you the story.

- `TargetResponseTime` — backend latency. Use percentile statistics (p50/p95/p99), not Average. CloudWatch supports percentile statistics for this metric since 2020.
- `RequestCount` — RPS, the offered load.
- `HTTPCode_Target_5XX_Count` versus `HTTPCode_ELB_5XX_Count` — distinguish backend errors from LB errors. The latter usually means targets are unhealthy or capacity is exhausted.
- `RejectedConnectionCount` — LB hit capacity. Should be zero; alarm if non-zero.
- `ActiveConnectionCount`, `NewConnectionCount` — connection churn pattern; sudden spikes often mean keep-alive isn't working.
- `TargetConnectionErrorCount` — backend refused or timed out. Climbs when targets are saturated before requests can be processed.
- `UnHealthyHostCount` — capacity below floor. Pin this on every dashboard.

The full reference is at https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html.

**Summary:**
- Pin TargetResponseTime (p50/p95/p99), RequestCount, 5xx counts, RejectedConnectionCount, UnHealthyHostCount on every dashboard.
- Action: alarm on RejectedConnectionCount > 0 and UnHealthyHostCount during tests.

### 5.5 RDS / Aurora MySQL observability

For Aurora MySQL specifically, **Performance Insights** (https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.html) is the primary tool. The headline metric is **DBLoad** — Average Active Sessions (AAS), the average number of sessions actively executing or waiting at any moment. AAS exceeding the vCPU count means sustained queue, which means CPU saturation; the dashboard's breakdown by wait events, top SQL, hosts, and users shows you the dominant cause.

The Aurora MySQL DBA Handbook at https://docs.aws.amazon.com/whitepapers/latest/amazon-aurora-mysql-db-admin-handbook/welcome.html is an essential read; the connection-management chapter alone is worth the time.

During every database-touching load test, screenshot the Performance Insights dashboard at peak. The top-10 SQL by AAS is your tuning backlog.

**Summary:**
- DBLoad / AAS is the single most important DB health metric. AAS > vCPU = sustained queue.
- Slice DBLoad by wait events and top SQL to find dominant contention.
- Action: enable slow query log, ship to CloudWatch Logs; screenshot PI dashboard at peak of every load test.
- Resource: Aurora MySQL DBA Handbook.

### 5.6 ECS/EKS Container Insights

Container Insights publishes per-task and per-pod CPU, memory, network, and storage metrics to CloudWatch. For EKS, the AMP-plus-node-exporter-plus-kube-state-metrics-plus-cAdvisor stack offers better cardinality and lower cost than Container Insights at scale, and integrates more cleanly with the Architecture B observability stack from Section 5.2.

**Summary:**
- ECS: Container Insights is fine.
- EKS: prefer AMP + node-exporter + kube-state-metrics + cAdvisor for better cardinality.

### 5.7 Observability authors to follow

A small set of authors produce essentially all the high-signal practitioner writing on observability. Charity Majors (Honeycomb co-founder/CTO) at https://charity.wtf and https://www.honeycomb.io/blog writes about observability 2.0, high-cardinality, and SLOs as APIs. Cindy Sridharan is the author of *Distributed Systems Observability* (free O'Reilly ebook, 2018) and continues to write at https://copyconstruct.medium.com/. Liz Fong-Jones (Honeycomb) is a frequent SREcon speaker and writes excellent SLO and error-budget posts. Ben Sigelman (Lightstep, OpenTelemetry origin) writes the foundational "three pillars" critique.

**Summary:**
- Follow: Charity Majors, Cindy Sridharan, Liz Fong-Jones, Ben Sigelman.
- Resource: Sridharan's free O'Reilly ebook *Distributed Systems Observability*.

---

## Part 6 — Realistic Spring Boot Scenarios

The previous sections gave you the discipline; this one gives you the practice. Five scenarios cover most of what you'll encounter in a Spring Boot service, plus deeper notes on Aurora and Kafka specifics.

### Scenario 1 — Synchronous read-heavy CRUD against MySQL (foundational)

The endpoint is `GET /api/v1/orders?customerId=...&page=...`, served by a `@RestController` calling a `JpaRepository`, hitting Aurora MySQL. The test design is a capacity sweep: ramp from 50 to 2000 RPS over 10 minutes, with realistic customer ID distribution (Pareto, not uniform — most queries hit the same hot accounts).

What to instrument: `tomcat.threads.busy`, `hikaricp.connections.active`, `hikaricp.connections.pending`, Aurora Performance Insights (AAS, top SQL, wait events), and HTTP request timer histograms.

The classical failure modes you'll find are predictable. **N+1 queries** show up as query count per request being far higher than expected — Hibernate's `org.hibernate.SQL` log or the slow query log will reveal them. Fix with `@EntityGraph` or `JOIN FETCH`. **Missing indexes** show up as Aurora CPU pegging at low RPS while query latency climbs; `EXPLAIN` confirms a table scan; add a covering index. **Pool starvation** shows up as `hikaricp.connections.pending` rising above zero for sustained windows while Aurora CPU is low — pool is too small. **Lock contention** on hot rows shows up as `synch/cond/sql/...` waits dominating in Performance Insights.

Each failure mode has a distinct signature; build your dashboards so each is independently visible.

**Summary:**
- Workload: capacity sweep 50→2000 RPS, Pareto customer IDs.
- Watch: Tomcat threads, Hikari pool, Aurora PI top SQL.
- Failure modes: N+1 queries, missing indexes, pool starvation, hot-row contention.

### Scenario 2 — Synchronous write-heavy with contention

The endpoint is `POST /api/v1/orders`, which inserts an order, decrements inventory, and writes an audit row, all within `@Transactional`. The test design is constant-rate at increasing levels (200, 500, 1000, 2000 RPS), each held for five minutes, with realistic product distribution (some products hotter than others, modeling Black Friday inventory behavior).

What to instrument: transaction commit time (Hibernate stats), Aurora `DBLoad` broken down by wait event, deadlock count from `SHOW ENGINE INNODB STATUS` or Performance Insights' lock analysis.

The failure modes are deadlocks (revealed by deadlock log entries and rollback exceptions), lock contention on hot rows (shown as row-lock-wait events dominating DBLoad), and transaction time inflating under contention. Remediation is application-level: narrower transactions, optimistic concurrency with retry-on-deadlock, the outbox pattern for event publishing, and consistent operation ordering to avoid deadlock cycles.

**Summary:**
- Workload: constant-rate writes at increasing levels with hot-product skew.
- Watch: deadlock count, InnoDB row-lock waits, transaction duration.
- Fixes: narrower transactions, optimistic concurrency with retry, outbox pattern.

### Scenario 3 — Cache-aside with Redis (cache stampede)

The endpoint is `GET /api/v1/products/{id}`, which checks Redis, falls back to MySQL on miss, and writes back to Redis. The test design is a steady-state load at the target rate with two variants: cache-warm (run a warmup phase first) and cache-cold (clear Redis right before the test).

The interesting failure mode is the **cache stampede** on cold start: 1000 concurrent requests for the same uncached item all miss simultaneously, all hit MySQL at once, and overwhelm the database. The cold-cache test reveals this dramatically — you'll see MySQL DBLoad spike and recover as cache fills.

The fixes are well-known: single-flight (per-key in-memory `ConcurrentHashMap<String, CompletableFuture>` to coalesce rebuilds within a JVM), distributed locking (Redisson `RLock` with watchdog for cross-instance coalescing), probabilistic early refresh (the XFetch algorithm), or stale-while-revalidate with TTL jitter to avoid synchronized expiry.

```kotlin
// Single-flight cache rebuild within a JVM. The first request to find a miss
// holds the rebuild lock; all subsequent requests for the same key wait on the
// same CompletableFuture. Prevents per-JVM stampede.
@Component
class StampedeSafeCache(private val redis: RedisTemplate<String, Product>, private val repo: ProductRepository) {
    private val inFlight = ConcurrentHashMap<String, CompletableFuture<Product>>()

    fun get(id: String): Product = redis.opsForValue().get("product:$id") ?: rebuild(id)

    private fun rebuild(id: String): Product {
        // computeIfAbsent guarantees only one thread per JVM rebuilds the same key
        return inFlight.computeIfAbsent(id) {
            CompletableFuture.supplyAsync {
                try {
                    val product = repo.findById(id).orElseThrow()
                    redis.opsForValue().set("product:$id", product, Duration.ofMinutes(5).plusJitter())
                    product
                } finally {
                    inFlight.remove(id)
                }
            }
        }.get()
    }

    private fun Duration.plusJitter(): Duration =
        this.plus(Duration.ofSeconds(Random.nextLong(0, 60)))  // avoid synchronized expiry
}
```

For cross-JVM coalescing, replace `ConcurrentHashMap` with a Redisson distributed lock. The Antirez post on cache stampede prevention at https://redis.antirez.com/fundamental/cache-stampede-prevention.html is the foundational reference.

**Summary:**
- Workload: cold-cache spike test.
- Watch: cache hit ratio, downstream MySQL DBLoad during stampede.
- Fixes: single-flight in-JVM, distributed lock cross-JVM, XFetch probabilistic refresh, TTL jitter.
- Resource: Antirez "Cache Stampede Prevention."

### Scenario 4 — Async fanout via Kafka

The endpoint is `POST /api/v1/events`, which validates the payload and produces a message to a Kafka topic, returning 202 Accepted. The synchronous part is fast; the load test must measure both producer-side latency (the API response time) and end-to-end latency (time from API call to consumer processing complete). The latter requires either a probe consumer that records timestamp differences, or distributed tracing with consistent trace IDs.

Test design: constant-rate at the planned ingestion rate, sustained long enough to fill batches and reach steady state — Kafka producers batch, so the first few seconds aren't representative of steady throughput.

What to instrument: producer metrics (`kafka.producer.record-send-rate`, `kafka.producer.batch-size-avg`, `kafka.producer.record-queue-time-avg`, `kafka.producer.outgoing-byte-rate`), broker-side metrics (request rate, request latency), and consumer lag (`records-lag-max` per partition, `commit-latency`).

The failure modes: producer queue saturation (revealed by `record-queue-time` climbing while broker is healthy — usually `linger.ms` and `batch.size` mistuned for the rate), broker partition imbalance (one broker hot, others idle — partition key distribution problem), consumer lag growing monotonically (not enough consumer parallelism or processing is CPU/IO-bound), and rebalance storms from too-short `session.timeout.ms`.

Confluent's *Kafka Performance, Latency, Throughput, Test Results* at https://developer.confluent.io/learn/kafka-performance/ and *Tuning the Apache Kafka Producer Client* at https://developer.confluent.io/courses/architecture/producer-hands-on/ are the canonical performance tuning references.

**Summary:**
- Workload: constant-rate produces; measure producer + end-to-end latency separately.
- Watch: producer record-queue-time, batch-size-avg; consumer records-lag-max.
- Failure modes: producer queue saturation, partition imbalance, consumer lag growth, rebalance storms.
- Resources: Confluent performance courses.

### Scenario 5 — Reactive WebFlux endpoint with downstream fanout

The endpoint is `GET /api/v1/dashboard`, which uses WebFlux to fan out three parallel calls to downstream services (user, orders, recommendations) via `WebClient`, combining results. The test design is high-concurrency — reactive shines at concurrency, so push to 10,000 concurrent in-flight requests — with controlled downstream latency. Use Toxiproxy or a stub server with configurable latency for the downstreams so you can characterize how the endpoint behaves when one downstream slows down.

What to instrument: event loop saturation (custom Micrometer gauge sampling `System.nanoTime()` lag from a `Schedulers.parallel()` task), per-downstream latency, BlockHound errors, ConnectionProvider pool exhaustion errors.

The failure modes: hidden blocking calls on the event loop (BlockHound catches them in tests; production code drifts), one slow downstream dragging the whole response (no per-call timeout — WebClient defaults are too generous), unbounded outbound connection pools that exhaust file descriptors, and tail-at-scale dominating the response when fanout grows.

**Summary:**
- Workload: high-concurrency fanout with controlled downstream latency (Toxiproxy).
- Watch: event loop lag, downstream p99, BlockHound errors, ConnectionProvider exhaustion.
- Failure modes: hidden blocking calls, no per-call timeouts, unbounded pools, tail-at-scale amplification.

### Aurora MySQL specific tuning under load

A few Aurora-specific notes worth knowing. Use **RDS Proxy** when your app fleet is large and connection churn is high (autoscaling tasks, Lambda), when you need transparent failover (~milliseconds versus ~30 seconds without), or when you want connection multiplexing. Note the pinning behavior: prepared statements, session variables, and locks pin the connection to a specific backend session, defeating multiplexing. The reference is at https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy.howitworks.html.

For read-heavy workloads, route reads to the cluster reader endpoint to use replica capacity; understand replica lag (typically sub-100ms but spikes happen) and decide your freshness tolerance. Enable Performance Insights, slow query log, and audit log via parameter group, ship to CloudWatch Logs.

**Summary:**
- RDS Proxy: use for high churn, fast failover, connection multiplexing — but watch for pinning.
- Cluster reader endpoint for read-heavy traffic; understand replica lag tolerance.
- Always: enable PI, slow query log, audit log via parameter group → CloudWatch Logs.

### Kafka consumer lag testing

Consumer lag is its own scenario shape. Run a separate "lag-only" test: pause the consumer for 60 seconds while producers continue at steady rate, then resume the consumer and measure recovery time and end-to-end latency during catch-up. This validates that your scaling story works — KEDA on EKS scaling on consumer lag, or ECS scaling on equivalent metrics.

**Summary:**
- Lag scenario: pause consumer 60s, resume, measure recovery time and catch-up latency.
- Validates autoscaling responsiveness (KEDA, ECS lag-based scaling).

---

## Part 7 — Resource Index

### 7.1 Books (canonical)

The shortlist of must-read books, in priority order. Brendan Gregg's *Systems Performance* (2nd ed, 2020) is the deepest single reference on performance work. His *BPF Performance Tools* (2019) is the eBPF reference. Scott Oaks's *Java Performance* (2nd ed, 2020) is the JVM bible. Michael Nygard's *Release It!* (2nd ed, 2018) covers the failure modes you're trying to expose. John Allspaw's *The Art of Capacity Planning* (2nd ed, 2017) is the canonical capacity planning text. The Google SRE Book and SRE Workbook are free at https://sre.google/books/. Martin Kleppmann's *Designing Data-Intensive Applications* (2017) is the distributed-systems context. Alex Petrov's *Database Internals* (2019) and Botros & Tinley's *High Performance MySQL* (4th ed, 2021) cover the database layer. Charity Majors et al.'s *Observability Engineering* (2022) and Cindy Sridharan's free *Distributed Systems Observability* (2018) cover observability.

**Summary:** Gregg ×2, Oaks, Nygard, Allspaw, SRE books, Kleppmann, Petrov, Botros/Tinley, Majors et al., Sridharan.

### 7.2 Conference talks (with rough dates)

Gil Tene, *How NOT to Measure Latency* — Strange Loop 2015 (also LJC, JavaOne, multiple QCons). Gil Tene, *Understanding Java Garbage Collection* — JavaOne 2012, repeated and updated since. Brendan Gregg's USE method talks — FISL13 (2012), USENIX LISA '12. Brendan Gregg, *Visualizing Performance with Flame Graphs* — USENIX ATC 2017. Brendan Gregg, *Blazing Performance with Flame Graphs* — USENIX LISA '13 plenary. Dean & Barroso, *Achieving Rapid Response Times in Large Online Services* — Berkeley AMPLab 2012, paper CACM 2013. Martin Thompson on mechanical sympathy — JAX London, GOTO Aarhus, multiple QCons 2011–2015. Kyle Kingsbury (Aphyr) Jepsen analyses — Strange Loop, RICON, !!Con 2013–present, archive at https://jepsen.io/analyses. Tyler Treat, *From the Ground Up: Reasoning About Distributed Systems* — multiple meetups 2015–2018. Aleksey Shipilëv's GeeCON and Hydra/Joker workshops on JCStress and JMM. Tom Wilkie's RED method talks — CloudNativeCon, KubeCon ~2017–2018. SpringOne's yearly observability tracks (search "SpringOne observability Marcin Grzejszczak"). KubeCon's yearly load testing tracks (search YouTube CNCF channel for "k6 KubeCon").

**Summary:** Tene ×2, Gregg ×4, Dean & Barroso, Thompson, Aphyr, Treat, Shipilëv, Wilkie; SpringOne and KubeCon yearly.

### 7.3 Blogs

Brendan Gregg at https://www.brendangregg.com/. HdrHistogram at https://github.com/HdrHistogram and https://hdrhistogram.org/. Tyler Treat at https://bravenewgeek.com/. HikariCP wiki at https://github.com/brettwooldridge/HikariCP/wiki. Aleksey Shipilëv at https://shipilev.net/. Mechanical Sympathy mailing list at https://groups.google.com/g/mechanical-sympathy. Marc Brooker (AWS) at https://brooker.co.za/blog/. Charity Majors at https://charity.wtf/ and Honeycomb at https://www.honeycomb.io/blog. Cindy Sridharan at https://copyconstruct.medium.com/. Netflix Tech Blog at https://netflixtechblog.com/. AWS Architecture Blog at https://aws.amazon.com/blogs/architecture/. Spring Blog at https://spring.io/blog. Grafana Labs blog at https://grafana.com/blog/. Gatling blog at https://gatling.io/blog. Artillery blog at https://www.artillery.io/blog. Baeldung at https://www.baeldung.com/. Krzysztof Slusarski at https://krzysztofslusarski.github.io/. Piotr Mińkowski at https://piotrminkowski.com/. Vlad Mihalcea at https://vladmihalcea.com/.

**Summary:** Follow Gregg, Treat, Wooldridge, Shipilëv, Brooker, Majors, Sridharan, Mińkowski, Mihalcea; check Spring, Grafana, Gatling, Artillery blogs regularly.

### 7.4 Courses (depth-oriented)

Coursera's *Site Reliability Engineering: Measuring and Managing Reliability* (Google Cloud) and *Developing a Google SRE Culture* are the structured SRE courses. Pluralsight has a Java Performance Tuning path with multiple authors. O'Reilly Learning has Scott Oaks's video editions of *Java Performance* and Brendan Gregg's Linux Performance video courses. Test Automation University's *Tools and Techniques for Performance and Load Testing* (Leandro Melendez, k6) is free at https://testautomationu.applitools.com/performance-and-load-testing/. Grafana University training at https://grafana.com/training/ has free k6 content. Gatling Academy at https://gatling.io/academy/ is free. AWS Skill Builder has an Observability on AWS learning plan at https://skillbuilder.aws/.

**Summary:** Coursera SRE specializations, Pluralsight Java Performance, O'Reilly Oaks/Gregg videos, free TAU/Grafana/Gatling/AWS courses.

### 7.5 Official documentation worth reading end-to-end

k6 docs (Executors, Thresholds, Outputs, Scenarios) at https://grafana.com/docs/k6/latest/. Gatling docs (Simulation Setup, Injection Profiles, Assertions) at https://docs.gatling.io/. Spring Boot Actuator + Observability at https://docs.spring.io/spring-boot/reference/actuator/. Micrometer at https://docs.micrometer.io/. HikariCP wiki at https://github.com/brettwooldridge/HikariCP/wiki. Aurora Performance Insights at https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_PerfInsights.html. AWS Well-Architected Performance Efficiency Pillar at https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html. Aurora MySQL DBA Handbook at https://docs.aws.amazon.com/whitepapers/latest/amazon-aurora-mysql-db-admin-handbook/welcome.html.

**Summary:** k6, Gatling, Spring Actuator, Micrometer, HikariCP wiki, Aurora PI, Well-Architected Performance Efficiency, Aurora DBA Handbook — read these end to end.

### 7.6 Open source projects worth studying

HdrHistogram source (Java) — algorithmic core in `AbstractHistogram`. async-profiler source — see `src/profiler.cpp` and `src/flightRecorder.cpp`. k6 source (Go) — read `lib/executor/` for arrival-rate logic. Gatling source (Scala) — `gatling-http/src/main/scala/io/gatling/http/`. wrk2 source (C) — small enough to read in an evening; CO correction in `src/stats.c`. spring-petclinic-microservices at https://github.com/spring-petclinic/spring-petclinic-microservices has Gatling load tests built in. Grafana Labs k6 examples at https://github.com/grafana/k6-example-scripts. Toxiproxy (Go) at https://github.com/Shopify/toxiproxy is a short codebase that teaches a lot about TCP toxics. Reactor BlockHound at https://github.com/reactor/BlockHound is fascinating bytecode-instrumentation reading.

**Summary:** Read source of HdrHistogram, async-profiler, k6 executors, wrk2, Toxiproxy, BlockHound — all small enough to study in days, not weeks.

---

## Part 8 — Suggested 12-Week Learning Path

The path that follows is designed to build the discipline incrementally. Each two-week block has a deliverable; producing the deliverable forces the concepts to land.

### Weeks 1–2 — Methodology foundation

Read Google SRE Book chapters 4 and 6 (SLOs, monitoring) and SRE Workbook chapter 2. Watch Gil Tene's *How NOT to Measure Latency* — twice. Read the Dean & Barroso *Tail at Scale* paper. Read Brendan Gregg's USE method page and Tom Wilkie's RED method talk.

**Deliverable:** a one-page SLO/SLI document for one of your Spring Boot services.

### Weeks 3–4 — Measurement and HdrHistogram

Read the HdrHistogram README and Javadoc. Write a 50-line Kotlin program that records latencies, applies CO correction, and prints the percentile spectrum. Read the top ten *JVM Anatomy Quarks* posts. Install async-profiler locally; profile a Spring Boot Petclinic instance in CPU, alloc, lock, and wall modes; produce four flame graphs.

**Deliverable:** a Grafana dashboard for one service showing p50/p95/p99/p99.9 of `http.server.requests` from Micrometer histogram buckets, plus HikariCP pool metrics, JVM heap, GC pause.

### Weeks 5–6 — k6 in depth

Walk through k6 docs Executors and Thresholds end to end. Build a k6 scenario for one Spring Boot CRUD endpoint with `ramping-arrival-rate`, SLO-aligned thresholds, and Prometheus remote-write output. Run on local Docker first, then in your AWS staging account against a single instance to find the knee.

**Deliverable:** a capacity report — "1 × t3.medium of service X serves N RPS at p99 < 300ms."

### Week 7 — Gatling for JVM-native parity

Add Gatling to one service via Gradle Kotlin DSL. Reproduce the same scenario you wrote in k6. Compare report ergonomics. Decide which tool to standardize on per service type.

**Deliverable:** a decision document on tool choice criteria.

### Weeks 8–9 — Spring Boot scenarios 1–3

Run Scenario 1 (read CRUD against Aurora MySQL) end to end, including async-profiler, Performance Insights screenshots, HikariCP tuning. Document findings. Run Scenario 2 (write contention) — induce a deadlock deliberately, capture in `SHOW ENGINE INNODB STATUS`, fix. Run Scenario 3 (cache stampede) — first reproduce the herd, then add single-flight with jittered TTL.

**Deliverable:** three scenario reports with before/after metrics.

### Week 10 — Kafka and reactive

Run Scenario 4 (Kafka) — measure consumer lag recovery and tune producer batching with at least three different `linger.ms` settings. Run Scenario 5 (WebFlux fanout) — wire BlockHound, deliberately introduce a `Thread.sleep`, confirm BlockHound throws.

**Deliverable:** Kafka producer tuning matrix and a WebFlux service with BlockHound in test scope.

### Week 11 — Chaos and FIS

Set up Toxiproxy in front of Aurora and Redis in dev. Write tests for "500ms latency," "30% packet loss," "connection reset." Configure one AWS FIS experiment template that fails over Aurora during a sustained k6 load test; measure failover SLO.

**Deliverable:** a chaos test suite for one service and an FIS experiment template.

### Week 12 — Capstone

Pick the service most critical to your team. Run the full battery: load, stress, spike, soak, capacity, breakpoint. Each test must use open-model load (arrival-rate), produce a Grafana dashboard snapshot covering all four instrumentation layers, include async-profiler flame graphs for steady state and saturation, and have SLO-aligned thresholds in CI.

**Deliverable:** a capacity-and-performance handbook for that service: per-instance RPS at SLO, recommended autoscaling thresholds, top-three known performance risks, runbook entry for tail-latency investigation.

---

## Caveats

A few things worth flagging because they may have shifted since this guide was assembled. JVM and GC ecosystem version specifics — "Generational ZGC default since JDK 23," "Shenandoah out of experimental in JDK 25" — should be verified against the OpenJDK release notes for your exact JDK version before relying on them in production decisions. AWS Performance Insights end-of-life and migration to CloudWatch Database Insights is a recent topic; check the official AWS announcement for current dates. Conference talk dates are best-effort; many of the canonical talks have been delivered multiple times across years and venues. Tool feature-set claims (k6 versus Artillery on coordinated omission, for instance) reflect current docs but the open- versus closed-model story for any tool depends on the executor or phase chosen — verify per scenario. k6 was acquired by Grafana Labs in 2021; some legacy URLs at k6.io still resolve but new content lives at grafana.com/docs/k6. Aurora MySQL specifics (max_connections defaults, RDS Proxy pinning behavior, write-forwarding quotas) vary by instance class, engine version, and global database configuration — always cross-check against the AWS docs for your exact setup. Finally, this guide does not cover front-end performance, Core Web Vitals (LCP, INP, CLS), or browser-side load testing; the k6 browser module exists but is a different discipline.
