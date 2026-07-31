---
title: "Performance Testing → Performance Tuning"
category: "Performance & Optimization"
description: "A learning roadmap and working playbook for load-testing and tuning JVM services that sit in front of a busy relational database, written for someone who has never run a structured load test and verified against primary sources in July 2026. It starts from the idea that a load test is a controlled experiment to locate a bottleneck rather than a way to produce a number, then covers the five things to internalize before the first test (coordinated omission, open versus closed workload models, how percentiles compose across fan-out, the knee of the utilization curve, and Little's Law alongside Amdahl's Law). From there it lays out a seven-phase measure-and-change loop, a triage tree for a bad p99 that runs from generator saturation through CPU throttling and connection-pool waits into PostgreSQL wait events, a minimum viable toolchain built on k6, Micrometer, async-profiler and pg_stat_statements, and the fourteen findings you will actually get, from N+1 selects and oversized pools to container CPU throttling and generic plan flips. It closes with test-data realism, an eight-week study plan, a ranked resource library, a desk checklist, and a copy-paste kit of k6, profiling, and SQL snippets."
---

# Performance Testing → Performance Tuning

A learning roadmap and working playbook for JVM services with a heavy relational database.
Written for someone who has never run a structured load test. Verified July 2026.

---

## 0. The one idea everything else hangs off

A load test is a controlled experiment to locate a bottleneck. Producing a number is not the point.

The number ("we did 800 rps at 240 ms p99") is a byproduct. What you want out of a run is *"the limiter is X, here is the evidence, here is the predicted effect of changing it."* Brendan Gregg has a name for testing without that discipline, casual benchmarking, and a one-line summary of how it fails:

> "casual benchmarking: you benchmark A, but actually measure B, and conclude you've measured C."

(His related anti-method, passive benchmarking, is the organizational version: run a tool with a variety of options, make a slide deck, hand the slides to management, analyze nothing.)

So the shape of everything below is: form a hypothesis, predict a number, change one thing, re-measure identically, then keep or revert. If you take one thing from this document, take the phrase *"what number do I predict, and what would falsify it?"*

Two consequences worth stating up front, because they save months:

- **Latency is a function of utilization, not of code speed.** Make the code 30% faster and latency drops. Then traffic grows, utilization returns to where it was, and latency creeps back with no code change. Track efficiency work by *mean* latency or CPU-seconds/request; p99 is your *saturation* early-warning signal. Don't conflate the two. ([Marc Brooker, *Latency Sneaks Up On You*](https://brooker.co.za/blog/2021/08/05/utilization.html))
- **For a JVM service in front of a busy database, a CPU profile shows you a small fraction of the story.** Your wall-clock time goes to *Sleeping* (blocked on the DB socket) and *Lock* (blocked on the connection pool). Reaching for a CPU flame graph first is the most common beginner misstep in this situation.

---

## 1. Five things to internalize before your first test

These are non-negotiable. Skip them and your numbers will be fiction, optimistic by one to three orders of magnitude at the tail, and you will spend weeks "fixing" things that were never broken.

### 1.1 Coordinated omission: your load generator is probably lying

If the generator pauses while the system is slow, the slow period contributes almost no samples. The bias is not noise. It runs systematically toward good outcomes, because the omission is *caused by* the badness. Averages come out mildly wrong. Percentiles come out catastrophically wrong.

Gil Tene's canonical example is a 200-second test: 100 s of 10,000 requests at 1 ms, then 100 s where the system is completely frozen.

| | Average | 99.99th percentile |
|---|---|---|
| Honest accounting | ~25 s | ~100 s |
| What a typical load generator reports | 10.9 ms | 1 ms |

Half the test duration produced 1/10,000th of the data. Tene's rule:

> "The number one indicator you should never get rid of is the maximum value. That is not noise, that is the signal."

Your smell test: a `max` of 30 s next to a `p99.99` of 3 ms. That is suggestive rather than conclusive, since with 10M samples a single genuine outlier (a long safepoint, a TCP retransmit) can produce it honestly. Confirm with the two decisive checks. Does offered rate equal achieved rate? Is there a gap in the sample timeline during the bad window?

Watch [How NOT to Measure Latency, QCon SF 2015](https://www.infoq.com/presentations/latency-response-time/) (54 min; the 2015 recording is the more polished one). Written summary: [Everything You Know About Latency Is Wrong](https://bravenewgeek.com/everything-you-know-about-latency-is-wrong/).

### 1.2 Open vs closed workload models

- **Closed:** new requests are triggered by *completions* (a fixed population of virtual users, optionally with think time).
- **Open:** new requests arrive at a *rate*, independent of whether prior ones finished.

Why this matters so much: a closed test has built-in negative feedback. System slows → fewer requests → less pressure → system recovers. That is not how the internet works. Real users and upstream services keep sending.

Quantified: k6's own example puts a 6-second request in a 60-second test at roughly 10 iterations closed versus 60 open, a 6× difference in delivered load. Brooker's simulation of a bimodal service found the closed benchmark underestimated p99 by a factor of at least 25, reporting under 1 ms where the open model reported over 25 ms.

There is a second, subtler penalty. Closed systems really do have tamer latency distributions, because they cannot build unbounded queues. So closed results are optimistic twice over: once from the measurement artifact, once from the model itself.

**Practical rule: use arrival-rate (open) executors for anything modelling internet traffic.** Use closed-with-think-time only when you are modelling a fixed population, like 500 kiosks or a device fleet.

Read: [k6, Open vs closed models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/) and [Brooker, Open and Closed, Omission and Collapse](https://brooker.co.za/blog/2023/05/10/open-closed.html).

### 1.3 Percentiles compose brutally, and p95 is not enough

Across a session loading ~200 resources, only 0.0035% of users experience *solely* p95-or-better latency. Restated: **99.997% of users hit something worse than your p95.** If a page needs 40 independent calls each p95-good, the chance all 40 are good is 0.95⁴⁰ ≈ 13%.

And fan-out multiplies the tail. From Dean & Barroso, [*The Tail at Scale*](https://cacm.acm.org/research/the-tail-at-scale/):

> "If a user request must collect responses from 100 such servers in parallel, then 63% of user requests will take more than one second."

(servers that normally answer in 10 ms but have a 1-second p99)

What that means for your situation: an N+1 query problem costs you far more than N extra round trips. It is N independent draws from the database's tail distribution, per user request.

Rules that follow:

- Report `p50 / p90 / p99 / p99.9 / max`. Always include max.
- **You cannot average percentiles** across instances or time buckets. Aggregate *histograms*, then compute percentiles. This is a real trap in Micrometer (see §2 Phase A): `percentiles:` computes them inside each JVM and exports gauges you cannot correctly combine, while `percentiles-histogram:` exports buckets you can.
- Record every sample, not a sample of samples: [HdrHistogram](https://github.com/HdrHistogram/HdrHistogram) does this in constant time with fixed memory, and its histograms are losslessly mergeable.

### 1.4 The knee of the curve

For an M/M/1 queue, expected number in system is `E[N] = ρ/(1-ρ)` where ρ is utilization:

| ρ | 0.5 | 0.8 | 0.9 | 0.95 | 0.99 |
|---|---|---|---|---|---|
| E[N] | 1 | 4 | 9 | 19 | 99 |

Going 50% → 80% utilization *quadruples* the number of requests in the system, and therefore the latency multiplier. 80% → 95% nearly quintuples it again (4.75×). Nobody chose the "knee" as a threshold; it is a hyperbola with a pole at ρ=1. (Note `E[N]` is requests *in the system*, queue plus in-service; expected number *queued* is `ρ²/(1−ρ)`.)

Consequence for test design: "peak rps at 30 s p99" is a useless number. **The number you want is the knee**, the load at which latency starts rising faster than throughput. That is your real capacity.

### 1.5 Two formulas that decide where you spend your week

**Little's Law**, `L = λW`, or in load-testing terms:

> **Concurrency = Throughput × Response time**

Three uses:

1. **Size the test.** 500 rps at an expected 200 ms needs ~100 in-flight requests.
2. **Validate the result.** After a run, check `concurrency ≈ throughput × latency`. If it doesn't hold, the test is broken (dropped iterations, generator saturation, coordinated omission).
3. **Find hard ceilings.** A 20-connection pool with 10 ms mean DB service time caps you at `20/0.010 = 2000 queries/sec`. No JVM tuning moves that number.

**Amdahl's Law**, `S = 1/((1-p) + p/s)`, and in the limit `S_max = 1/(1-p)`.

If a component is 5% of latency, then even a *perfect* fix caps you at a 5.3% improvement. **Get `p` from a profile before you touch anything.** This is the arithmetic that turns "profile first" from a slogan into a rule, and it lets you say *no* to speculative optimization without saying no to optimization. Knuth's full quote licenses exactly this:

> "We should forget about small efficiencies, say about 97% of the time: premature optimization is the root of all evil. **Yet we should not pass up our opportunities in that critical 3%.**"

*(Worth knowing but not on the critical path: the [Universal Scalability Law](https://www.perfdynamics.com/Manifesto/USLscalability.html), `X(N) = γN / (1 + α(N-1) + βN(N-1))`. Its β term predicts retrograde scaling, meaning throughput that peaks and then falls as you add load or nodes. That is precisely what over-concurrent database access looks like, and it is why a pool of 10 often beats a pool of 100. Amdahl can only flatten; USL can go down.)*

---

## 2. The loop

This is the playbook. Seven phases; phases D through F repeat.

### Phase A: instrument *before* you generate load

A load test without server-side telemetry produces a number and no explanation. You'll learn "p99 is 1.8 s" and have no idea why. Wire this first; it is the difference between a week of work and a month.

App side (JVM):

```yaml
# Micrometer / Spring Boot Actuator
management:
  metrics:
    distribution:
      percentiles-histogram:
        http.server.requests: true        # exports BUCKETS, aggregatable
      minimum-expected-value: { http.server.requests: 1ms }
      maximum-expected-value: { http.server.requests: 10s }
spring:
  datasource:
    name: orders-primary                  # makes the `pool` tag meaningful
    hikari:
      maximum-pool-size: 20
      connection-timeout: 2000            # NOT the 30s default
      leak-detection-threshold: 20000
  jpa:
    open-in-view: false                   # Spring defaults this to true. Turn it off.
```

- JFR always on: `-XX:StartFlightRecording:name=continuous,settings=default.jfc,disk=true,maxage=1h,maxsize=512m,dumponexit=true` (Oracle documents `default.jfc` at under 1% overhead, so leave it running in production).
- GC + safepoint logging: `-Xlog:gc*,safepoint:file=/var/log/app/gc.log:time,uptime,level,tags:filecount=5,filesize=100M`
- OpenTelemetry Java agent with **sampling at 1.0 during the test window**. Head-based 1% sampling systematically misses your p99, because the traces you need are by definition rare.

DB side (PostgreSQL):

```conf
shared_preload_libraries = 'pg_stat_statements,auto_explain'
compute_query_id = on
track_io_timing = on
pg_stat_statements.max = 10000

auto_explain.log_min_duration = '200ms'
auto_explain.log_analyze = on      # real row counts
auto_explain.log_buffers = on
auto_explain.log_timing = off      # <-- keeps overhead sane; see note
auto_explain.log_settings = on

log_min_duration_statement = '200ms'
log_lock_waits = on
log_temp_files = 0                 # logs every work_mem spill
log_checkpoints = on
log_autovacuum_min_duration = 0
```

> The docs warn that `log_analyze = on` does per-node timing for every statement, logged or not, and "can have an extremely negative impact on performance." Turning `log_timing = off` fixes that while keeping per-node rows and buffers, which is where the diagnosis lives.

The dashboard, in priority order. If you build only five panels, build these:

| Metric | Why it's here |
|---|---|
| `http_server_requests_seconds_bucket` by uri/status | Your SLO, via `histogram_quantile()` |
| `hikaricp_connections_pending` | The best single DB-saturation signal. Sustained > 0 means threads are queueing for a connection |
| `hikaricp_connections_usage_seconds` | How long you *hold* connections, usually the root cause |
| `jvm_gc_pause_seconds` (max) + allocation rate | GC's contribution to the tail |
| `container_cpu_cfs_throttled_periods_total / ..._periods_total` | CPU throttling, which looks *exactly* like GC and appears in no GC log |

### Phase B: establish the floor and the ceiling

Before you test your application, find out what the environment can do at all.

1. **Latency floor.** `ping` the SUT, and `curl -w 'conn=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer}\n'`. You need to know what you're adding to.
2. **Database ceiling.** This is the most valuable exercise in the whole document. Run a `pgbench` sweep at a scale that *exceeds* `shared_buffers`, across concurrency levels, and plot TPS and latency:

   ```bash
   pgbench -i -s 1000 mydb                      # ~100M rows, ~15GB
   for c in 1 2 4 8 16 32 64 128; do
     j=$(( c < 8 ? c : 8 ))                     # scale threads with clients, cap at cores
     pgbench -c $c -j $j -T 300 -P 10 -M prepared mydb
   done
   ```

   **You will see the knee.** TPS flattens and latency starts climbing linearly. That number is an empirical upper bound on your total connection pool size across all app instances, derived on *your* hardware. This is the exact experiment behind HikariCP's pool-sizing advice.

   Yes, plain `pgbench` is a closed-loop generator with no think time, precisely the model §1.2 argues against. That's fine *here*, because the point of this experiment is to vary concurrency and watch what breaks; you are not modelling internet traffic. If you want the open-model variant, `-R <rate>` drives a fixed arrival rate and `-L <ms>` reports late transactions.

3. **Prove the generator isn't the bottleneck.** Every run: check generator CPU (any saturated core means garbage results) and its own error counters. The definitive test is to run the same scenario from 2× the generators and confirm the results scale linearly. If p99 *improves* when you add generators, every prior number was generator-bound.

### Phase C: build the workload model

Gregg's Workload Characterization Method asks four questions: **who** is causing the load, **why** it's being called, **what** the load is (rps, read/write ratio, payload sizes), and **how** it changes over time. Do this *before* you write a script, or you'll load-test the wrong thing.

Concretely:

- Derive your target rate from **peak-hour production data, never a monthly average.** k6's worked example: 990 sessions × 92 s ÷ 3600 = 25.3 concurrent users at peak, versus 0.08 on a 30-day average.
- Weight endpoints by real traffic share, not by how interesting they are.
- **Parameterize so each virtual user hits different rows.** 100 VUs all doing `GET /orders/1` measures your caches, not your database.
- Model **skewed** key access (Zipf/Pareto), not `random()`. Real traffic has 1% of rows taking 50% of the traffic. That's where your hot-row lock contention lives, and uniform access will never find it.

### Phase D: baseline

Run the average-load test: ramp → warm-up → measured steady window.

Warm-up is not optional on the JVM. C2 needs thousands of executions per hot path, and a cold JVM runs 10 to 100× slower. For a DB-heavy service the *other* caches dominate anyway: JDBC statement cache, DB buffer pool, plan cache, second-level cache, TLS session tickets. **Your first five minutes measure disk, not code.**

Shape: ramp 2 to 5 min → steady warm-up 5+ min (discarded) → measurement window 10 to 30 min (asserted).

Record and keep, for every run: the full latency distribution, USE metrics for every resource, a CPU flame graph, a wall-clock flame graph, the GC log, and a DB stats dump. Keep the provenance too, meaning git SHA, full JVM flags, JDK build, dataset snapshot ID, generator version, and the generator's own resource graphs. Without provenance you can't compare next month's run, and comparison is the entire point.

### Phase E: locate, don't guess

Use Thread State Analysis: for each thread of interest, measure total time in each state, and investigate the biggest bucket first.

| State | What it means | Where to look |
|---|---|---|
| Executing | On-CPU | CPU flame graph |
| Runnable | Waiting for a CPU turn | CPU saturation, cgroup throttling |
| Sleeping | Blocked on I/O | Your DB calls live here |
| Lock | Waiting on a monitor or pool | Connection pool waits live here |

The tool for the last two on the JVM is `async-profiler -e wall`. A CPU profile shows you an idle-looking flame graph while wall-clock shows the real stall.

Then compute `p` for your candidate (Amdahl). **If it's under 10% of total time, stop and find a bigger target.**

### Phase F: one change, with a predicted number

Write the hypothesis down *with a number*: *"the pool saturates at 20; going to 40 will lift throughput 800 → ~1400 rps and drop p99 900 → ~300 ms."* A hypothesis without a predicted number can't be falsified.

Then **change exactly one thing.** Re-measure identically: same script, same data, same environment, same duration, same warm-up. Compare with a differential flame graph (async-profiler 4.4+ generates these directly) and a percentile-distribution overlay.

**Revert is the default.** And if the measured result doesn't match the prediction, *even when it improved*, you don't understand the system yet. Investigate before keeping it.

Then repeat, because the bottleneck has now moved.

### Phase G: institutionalize

- Encode the SLO as a threshold in the test so CI fails on regression (k6 exits 99 on a threshold breach).
- Run smoke on every commit, average-load nightly, soak weekly, breakpoint quarterly.
- Compare like with like. k6's docs put it plainly: *"It's critical to compare test run results of the same test. Otherwise, you're comparing apples with oranges."* Run each configuration twice consecutively to filter flukes.
- Set the SLO from what users need, not from what you currently do. Google SRE Ch. 4 says *"Don't pick a target based on current performance"*, because that locks you into heroics.

Test types, and where each belongs in the cycle:

```
smoke (CI, every commit: validates the SCRIPT, not the system)
  └─> average-load  ← BASELINE. re-run after every single change.
        └─> stress            (which resource saturates first, and how it degrades)
              └─> scalability sweep (N = 1,2,4,8,16,32: contention or coherency?)
                    └─> spike       (cold caches, JIT warmup, autoscale lag, recovery)
                          └─> soak  (overnight: leaks, heap creep, index bloat, log disk)
                                └─> breakpoint (quarterly: where is the wall?)
```

Two warnings on breakpoint tests, from k6's own docs. Disable autoscaling first, otherwise "the elastic environment may grow as the test moves further, finding only the limit of your cloud account bill". And only run them once the other types pass, or what you find is a bug rather than a limit.

---

## 3. The triage tree

This is the page to pin above your desk. p99 is bad. Now what?

```
p99 bad
├── 0a. Is the load generator saturated, or reporting dropped iterations?
│         → YES: every number is invalid. Fix the harness first. (§2 Phase B)
│
├── 0b. Is the ERROR rate up, and what KIND of error?
│         → a 503 returned in 2 ms makes p99 look great while users see failures.
│         → and client timeouts + retries turn a healthy closed system into an
│           open one at the worst moment: retries raise arrival rate, which raises
│           latency, which triggers more retries. That's congestive collapse.
│
├── 0c. Is it ALL instances, or one?  (disaggregate p99 by pod/instance first)
│         → one cold pod, one rebalancing node, one noisy neighbour skews the aggregate.
│           Cheapest possible cut, and people skip it.
│
├── 1. Is CPU throttling happening?  (container_cpu_cfs_throttled_*)
│         → YES: multi-hundred-ms stalls that look exactly like GC and appear in NO GC log.
│
├── 2. Is the GC log clean in the bad window?  (-Xlog:gc*,safepoint)
│         → NO: GC or a non-GC safepoint. Check allocation rate before switching collectors.
│
├── 3. Is the request even ON a worker thread yet?
│         → tomcat_threads_busy vs tomcat_threads_config_max, and the accept backlog.
│           A request queued at the HTTP layer is INVISIBLE to a profile of worker
│           threads, since it hasn't got one. Distinct from the DB pool, and the 2nd most
│           common "app slow, DB fine" cause after transaction scope.
│
├── 4. Is a connection LEAKING?  (usage timer very high on a few, pending ~0, active < max)
│         → turn on leakDetectionThreshold; it logs the borrowing thread's stack.
│
├── 5. Run async-profiler in WALL-CLOCK mode. Where is the thread parked?
│   │
│   ├── HikariPool.getConnection  →  POOL problem, not a DB problem
│   │     └── hikaricp_connections_pending > 0 sustained?
│   │         ├── usage timer HIGH  → queries slow / transactions too wide.
│   │         │                       Enlarging the pool makes it WORSE.
│   │         └── usage timer LOW   → genuinely too few connections.
│   │                                 The ONLY case where enlarging is right.
│   │
│   ├── SocketRead / JDBC             →  the DB is actually working. Go to the DB tree.
│   ├── Application code on-CPU       →  CPU flame graph, then Amdahl before you optimize.
│   └── Monitor / lock contention     →  asprof -e lock
│
└── 6. DB tree (in descending order of "this is usually the answer"):
    a. Query COUNT per request  (pg_stat_statements.calls ÷ requests)
          → a small explainable integer? If a "list 20" endpoint issues 61 queries: N+1.
    b. Wait-event histogram (sample pg_stat_activity at 1 Hz)
          → Lock    = app-level contention (hot rows, FOR UPDATE, lock ordering)
          → LWLock  = internal contention, but WHICH lock matters:
                        LockManager / ProcArray     → too many connections
                        WALWrite / WALInsert        → WAL fsync + commit rate
                        BufferMapping / BufferContent → working set > RAM
                        MultiXact* / Subtrans* SLRU → long-running transactions
          → IO      = storage, or a checkpoint storm
          → NULL    = on CPU → bad plans
    c. pg_stat_statements by total_exec_time, then by (blks_hit+blks_read)/calls
          → buffers-per-call in the hundreds for a point lookup = missing index
    d. auto_explain plans for those queries
          → estimated vs actual rows (× loops!), Rows Removed by Filter, spills
    e. n_dead_tup climbing / stale last_autovacuum / "idle in transaction"
    f. checkpoints: num_requested >> num_timed  → periodic p99 sawtooth
```

Two heuristics worth having in your head:

1. **App p99 exploding + DB latency flat + DB CPU idle = the database is fine.** It's your pool, your transaction scope, or your HTTP thread pool.
2. **If the pool metrics are ambiguous, halve `maximumPoolSize` in a load test and see what happens.** It's a fast, cheap probe of whether you're past the knee, and Little's Law is the discipline behind it: if adding concurrency doesn't add throughput, concurrency is only adding latency. Two caveats. Read `pending` and `usage` first, because they usually answer the question deterministically without perturbing anything. And don't ship a halved pool below the deadlock floor `Tn × (Cm − 1) + 1` (§5.2), or below what an already-undersized pool needs; there, halving just converts latency into `connectionTimeout` exceptions, meaning user-visible 500s.

---

## 4. The minimum viable toolchain

You do not need all of this. You need a load generator, metrics, one profiler, and `pg_stat_statements`.

| Layer | Pick | Why |
|---|---|---|
| **Load generator** | **Grafana k6** (2.x) | Two reasons matter for a beginner. `dropped_iterations` is a first-class metric, so offered-vs-achieved load is impossible to ignore, and that is the concept people get wrong. Thresholds map to exit code 99, which gives you a one-block CI gate with no assertion DSL and no report parsing. Secondary: it isn't a JVM, so the generator's own GC can't contaminate client-side timings, and Prometheus remote-write puts load-test and service metrics on one dashboard. |
| Runner-up | **Gatling** (3.x; Java/Kotlin/Scala DSL, and now JS/TS) | A closer call than most write-ups admit. Gatling has had open-model arrival-rate injection (`constantUsersPerSec`, `rampUsersPerSec`) for years and reports full percentile distributions, so it satisfies §1.2, this document's most important requirement, just as well as k6. Pick it *first* if your setup needs your domain code (complex auth minting, protobuf from your own schemas, JDBC fixtures) or typed tests matter to your team. Honest trade: the generator is a JVM, so you must warm it, size its heap deliberately, and log *its* GC too. Neither tool has built-in distributed injection in OSS. k6 needs k6-operator/Kubernetes or Grafana Cloud, Gatling needs hand-rolled multi-injector orchestration. And k6's per-VU JS interpreter is comparatively CPU-expensive per iteration, so a k6 generator often saturates its cores at *lower* rps than Gatling's Netty pipeline. Check generator CPU either way. |
| Metrics | Micrometer + Actuator → Prometheus + Grafana | |
| Tracing | OpenTelemetry Java agent | Auto-instruments JDBC/Hikari/Hibernate. The N+1 is visually obvious in a waterfall: 200 sibling spans with an identical statement. |
| Always-on | JFR (`default.jfc`) + JDK Mission Control | Start with JMC's Automated Analysis page. It reads a recording and writes prose ("this app spent 12% of its time in GC pauses"). |
| On-demand profiler | **async-profiler** (4.5) | No safepoint bias, and `-e wall` is your off-CPU tool. |
| DB | `pg_stat_statements` + `auto_explain` + pgBadger | Ships with Postgres, and there is no good reason to run without it. |
| Later | Grafana Pyroscope (async-profiler-based), `pg_stat_kcache`, `pg_stat_monitor` | |

Don't start with JMeter (last release Jan 2024; closed-loop by default, so its default p99 is optimistic; and running it from the GUI with listeners attached bottlenecks the *generator*). Or Locust, which is a third language for no gain in a JVM shop. Or `ab`, which is single-threaded, HTTP/1.0, and has keep-alive off by default, so you'll be benchmarking `ab`.

Worth adding later, cheaply: `vegeta` for 60-second single-endpoint sanity checks. It is constant-rate by design with HdrHistogram output, so unlike `wrk` its percentiles survive saturation. (`wrk2` is Gil Tene's coordinated-omission-correcting fork of `wrk` and is the canonical teaching tool, but it's unmaintained with no releases. Use `vegeta` or `oha --latency-correction` in practice.)

On JMH: it's the only correct way to microbenchmark on the JVM, and it is rarely your first answer. Microbenchmarks are for pure, CPU-bound, sub-millisecond units you fully control. The cost that dominates your service is *queueing*, for a connection, a lock, or a CPU slice. That cost emerges from concurrency and load, which a microbenchmark by construction does not have. A JMH benchmark of your DAO on a warm single connection will report 40 µs and tell you nothing about why p99 is 2 s at 800 rps. **Load test and profile first; reach for JMH once a profile has already named a specific on-CPU frame.** When that happens it's usually JSON serialization of large response payloads (frequently the top on-CPU frame in a Spring service), entity→DTO mapping, a password KDF, or regex/validation on a hot path.

---

## 5. The findings you will actually get

Roughly in order of how often they turn out to be the answer for a JVM + RDBMS service. Each is *symptom in a load test → detection → fix*.

**1. N+1 selects.** Cheap query (0.2 ms mean) with an enormous `calls` count and `rows/calls ≈ 1`. DB CPU low, DB per-query p99 fine, app p99 terrible and proportional to result-set size. Throughput plateaus and **no amount of DB tuning helps**, because the bottleneck is round-trips × RTT.
→ Detect: `calls ÷ requests`; a trace waterfall; `SQLStatementCountValidator.assertSelectCount(1)` in a test to fail the build on regression (now in [Hypersistence Utils](https://github.com/vladmihalcea/hypersistence-utils), not the archived `db-util`).
→ Fix, best first: **DTO projections** > `JOIN FETCH` / `@EntityGraph` > `@BatchSize` / `hibernate.default_batch_fetch_size` (turns 200 queries into 4 with one config line). Never `FetchType.EAGER`. And set `spring.jpa.open-in-view=false`. Spring Boot enables OSIV by default, which both hides N+1 from service-layer tests and holds a DB connection for the entire request, serialization included.

**2. Oversized connection pool.** DB latency high, LWLock waits climbing, `hikaricp_connections_pending` reads 0 so the pool "looks healthy" while p99 triples.
→ The mechanism: requests must queue *somewhere*. With a small pool they queue in the app, where the queue is visible (`pending`), bounded (`connectionTimeout`), FIFO-ish, and cheap (a parked Java thread). With a large pool the queue moves inside the database, where it is invisible to your app metrics, unbounded, unfair (everyone slows proportionally, the convoy effect), and more expensive per unit of work. In Postgres each connection is an OS *process* costing several MB of private memory, plus `work_mem` per sort/hash node per backend, plus ProcArray/LockManager contention.
→ Formula, from [HikariCP's *About Pool Sizing*](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing): **`connections = ((core_count * 2) + effective_spindle_count)`**, where `core_count` is physical cores **on the database**. It is your *total* budget across all app instances, not per instance. The wiki's axiom: *"You want a small pool, saturated with threads waiting for connections."* Its evidence: an Oracle Real-World Performance demo where cutting the pool from ~2048 to ~96 took response times from ~100 ms to ~2 ms with no other change, and a Postgres chart where TPS flattens around 50 connections while latency keeps climbing.
→ Separately: if one thread can ever hold two connections, the pool can deadlock. Minimum safe size is `Tn × (Cm − 1) + 1`. The real fix is to stop doing that.

**3. Transaction scope too wide.** `hikaricp_connections_usage_seconds` p99 ≫ sum of your query times (800 ms of connection occupancy for a 5 ms query). `pg_stat_activity` full of `idle in transaction` / `ClientRead`. Pool exhaustion at modest rps. And, less obviously, `n_dead_tup` grows across the *whole* database, because one long-lived transaction pins the global xmin horizon and `VACUUM` can't remove any newer tuple anywhere.
→ Fix: never make an HTTP/gRPC/Kafka call inside `@Transactional`. Compute before you open the transaction. `@Transactional(readOnly = true)` on read paths. And set server-side guardrails so pile-ups become fast, loud, countable errors: `statement_timeout`, `lock_timeout`, `idle_in_transaction_session_timeout`.

**4. Missing or wrong index.** DB CPU pegged; buffers-per-call in the hundreds; `Seq Scan` + `Rows Removed by Filter: 4,900,000` for 100 returned rows.
→ The distinction to learn: `Index Cond:` is evaluated *inside* the index, which is what you want, while `Filter:` is evaluated *after* fetching a heap row you have already paid for. Moving a predicate from `Filter` to `Index Cond` by extending the index is the most common concrete fix there is.
→ Composite index column order: equality columns first, then range/sort. Partial indexes for the skewed case (`WHERE status='PENDING'` on a queue table with 50M done rows). Watch sargability, because Hibernate happily emits non-sargable SQL when entity types mismatch column types.
→ Over-indexing is real too. Every index multiplies write cost, inflates WAL, and defeats HOT updates. Find dead ones with `pg_stat_user_indexes WHERE idx_scan = 0`, but only *after* a representative full test, or you'll drop the index a nightly job needs.

**5. No JDBC batching.** An endpoint inserting 500 rows takes 500 × RTT; DB nearly idle.
→ Fix: `hibernate.jdbc.batch_size=50` + `order_inserts=true` + `order_updates=true`, and `reWriteBatchedInserts=true` in the pgjdbc URL (docs cite 2 to 3×).
→ The most commonly missed prerequisite: `IDENTITY`/`SERIAL` generation **disables Hibernate batching entirely**, because Hibernate needs each generated key back immediately. Use a `SEQUENCE` with `allocationSize` matching the DB's `INCREMENT BY`.

**6. Unbounded result sets and OFFSET pagination.** Heap pressure and GC pauses under load; `rows/calls` in the thousands; latency degrading *as the test progresses*. That last one is the OFFSET signature: page 1 is fast, page 5000 is a table scan.
→ pgjdbc's `defaultRowFetchSize` is **0 by default, meaning the entire result set is materialized in JVM heap.** Set it, and enforce a hard server-side `LIMIT`. Then switch to keyset pagination (`WHERE (created_at, id) < ($1,$2) ORDER BY ... LIMIT 20`), which Markus Winand covers for free at [use-the-index-luke.com/no-offset](https://use-the-index-luke.com/no-offset).

**7. Container CPU throttling**, the biggest 2026 JVM footgun. Multi-hundred-millisecond p99 spikes that look *exactly* like GC pauses and appear nowhere in the GC log.
→ `Runtime.availableProcessors()` returns ≈ `ceil(cpu.max quota / period)`, and that one integer sizes GC worker threads, `ForkJoinPool.commonPool` parallelism, the virtual-thread carrier pool, and Netty event loops. Common-pool parallelism is n−1, so a 1-CPU limit gives you parallelism 1, silently serializing every parallel stream and `supplyAsync`. (Tomcat's `maxThreads` is *not* in this list. It defaults to 200 regardless of CPU count, which is its own separate problem.) Exceeding the quota within any 100 ms CFS period parks **all** your threads until the next period. A JVM running 8 GC threads against a 1-core quota throttles itself into a stall during every young GC.
→ Since 11.0.17+/17.0.5+/18.0.2+ the JVM ignores `cpu.shares` and uses quota only, so a pod with `requests.cpu` but **no `limits.cpu`** sees the *whole node's* CPU count and builds absurd thread pools. This is the most common JVM-in-Kubernetes misconfiguration going.
→ Check `/sys/fs/cgroup/cpu.stat` (`nr_throttled`, `throttled_usec`). Give ≥2 vCPU. Set `-XX:MaxRAMPercentage=75`, since the default of 25% wastes three quarters of your container. Consider pinning `-XX:ActiveProcessorCount`.

**8. `work_mem` spills.** `temp_blks_written > 0`; `Sort Method: external merge Disk: 248432kB`; `Batches: 32` on a hash node; `lossy=48000` heap blocks on a bitmap scan.
→ `work_mem` is **per node, per backend, per parallel worker**, not per query and not per connection. The docs say *"the total memory used could be many times the value of work_mem."* Set it modestly globally (16 to 64 MB) and raise it per-statement (`SET LOCAL work_mem`) for the few queries that need it. If the spills are *hash* spills, raise `hash_mem_multiplier` (default 2.0) instead.

**9. Checkpoint sawtooth.** A p99 sawtooth with a period of a few minutes.
→ `pg_stat_checkpointer.num_requested` materially greater than `num_timed` means you blew through `max_wal_size` before `checkpoint_timeout`, so checkpoints fire too often and force WAL full-page images (visible as `wal_fpi`). Raise `max_wal_size` (4 to 32 GB is normal for write-heavy) and `checkpoint_timeout` (15 to 30 min).

**10. Generic plan flip.** Fast for the first several executions of a prepared statement, then suddenly terrible. This is a load-test-only bug that no unit test will ever show you. Two thresholds compose: pgjdbc's `prepareThreshold` (default 5) decides when the *driver* switches to a server-side named statement, and then PostgreSQL's own `plan_cache_mode=auto` logic wants 5 custom-plan executions of that statement before it will consider a generic plan. So the flip typically appears **around the 10th execution**, not the 6th. If you watch for a change at 6 and see none, don't conclude the bug isn't there. A generic plan ignores actual parameter values, so on a skewed column (`status='PENDING'` vs `'DONE'`) it can be catastrophic. Control with `plan_cache_mode = force_custom_plan` per session or role.

**11. Postgres JIT eating an OLTP query.** `JIT: ... Total 44.5ms` on a query whose execution is 3 ms, and it is per execution, not cached. JIT triggers on estimated *cost*, not estimated duration, so a query over many partitions or with a big `IN` list trips it. Symptom: bimodal latency, `stddev_exec_time >> mean_exec_time`. **For an OLTP service, set `jit = off`.** PG19 makes that the default, with the release notes conceding the costing "has been determined to be unreliable."

**12. Autovacuum can't keep up.** At the default `autovacuum_vacuum_scale_factor = 0.2`, a 100M-row table waits for **20 million** dead tuples before autovacuum fires. Override per-table on your big hot tables (0.01 to 0.05), and raise `autovacuum_vacuum_cost_limit`. Its effective default of 200 was calibrated for 2005 hardware, and it is the reason for "autovacuum is running but never finishing". Note the cost limit is *divided among* workers, so raising `max_workers` without raising the limit slows each one down.

**13. Deadlocks.** Any `pg_stat_database.deadlocks > 0` during a load test is a **correctness bug** (inconsistent lock ordering), not a tuning issue. Hibernate reorders statements at flush time, which is a common culprit; `hibernate.order_updates=true` / `order_inserts=true` makes it deterministic, and is also required for batching.

**14. Cache masking rather than fixing.** If your test uses a small key space, hit rate is ~100% and you measured your cache. **This is the most common way load tests lie.** Caching to hide an N+1 or a missing index means your cold-start and post-deploy behaviour is catastrophic. Run at least one test with the cache disabled to see the true DB load you'd face on a cold start.

---

## 6. Test data, the thing that decides whether any of this is real

A performance test on a tiny dataset doesn't merely lose accuracy. It actively misleads, because it produces *different query plans*:

1. **Plans flip on volume.** At 1000 rows everything fits in `shared_buffers` and a seq scan really is optimal, so the planner picks one, and you ship the missing index.
2. **Plans flip on statistics.** The planner reads n_distinct, MCVs, histograms, correlation. Small synthetic data has uniform distributions and perfect physical correlation. Real data has neither.
3. **Nested loops look free** at 100 outer rows and are a disaster at 100,000.
4. **`work_mem` spills never happen**, until production.
5. **No bloat, no vacuum pressure, shallower B-trees.**
6. **Uniform key access ⇒ ~100% cache hit rate.**
7. **Lock contention is absent**, because contention is collisions on the *same rows*.

What to match, in order of how often it's skipped:

- Row counts within an order of magnitude, for the tables in your hot queries.
- **Cardinality, not just volume**, and be sure to include the whale tenant. 50M rows spread evenly across 50,000 tenants gives you the wrong plans for both the median tenant and the big one.
- **Skew in the access pattern**, in the generator (Zipf, not uniform). As important as the data itself, and much more often skipped.
- Physical correlation. A table built by `generate_series` is perfectly clustered on its PK; a real one that's been updated for two years isn't, and `pg_stats.correlation` drives index-scan costing. Run some representative UPDATE churn, then `ANALYZE`.
- String widths / TOAST behaviour. `repeat('x',10)` in every text column understates page counts, buffer reads, and network transfer.
- Then **`ANALYZE` everything.** Measuring against un-analyzed data is measuring nothing.

The best source of realistic data is a production snapshot run through a *deterministic* anonymizer. Deterministic pseudonymization (same input → same fake value) preserves join cardinality; random per-row replacement destroys it and makes the test meaningless. [PostgreSQL Anonymizer](https://postgresql-anonymizer.readthedocs.io/) does this declaratively via column security labels. Preserve string lengths and uniqueness, or you've removed all the TOAST reads and changed `n_distinct`.

One PostgreSQL 18 shortcut is worth knowing about. You can now export *optimizer statistics* from production and inject them into a small test database, so the planner produces production plans without production data:

```bash
pg_dump --statistics-only -d production_db > stats.sql
psql -d test_db -f stats.sql
# then stop autoanalyze from overwriting what you just injected:
#   ALTER TABLE orders SET (autovacuum_enabled = false);
```

This catches "the planner will choose differently in production" in CI, which is most plan bugs. Two limits to know. It does not give you production *execution*: buffer counts, I/O, lock contention and vacuum behaviour still need real volume, and for those you want thin clones or copy-on-write database branching. And `pg_dump --statistics` explicitly excludes extended statistics created with `CREATE STATISTICS`, which is exactly what you'll have created for correlated columns, so recreate those in the test database by hand.

---

## 7. A phased study plan

Roughly 8 weeks at a few hours a week, each phase ending in something that exists rather than something you've read.

### Weeks 1 and 2: measurement literacy (before touching a tool)

Read and watch, in this order:

1. Gregg, [methodology.html](https://www.brendangregg.com/methodology.html) + [usemethod.html](https://www.brendangregg.com/usemethod.html) + the [USE Linux checklist](https://www.brendangregg.com/USEmethod/use-linux.html). One afternoon. Read the anti-methods list first; you will recognise yourself.
2. Gil Tene, [How NOT to Measure Latency](https://www.infoq.com/presentations/latency-response-time/), before you run a single test.
3. k6 docs: [test types](https://grafana.com/docs/k6/latest/testing-guides/test-types/) + [open vs closed](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/). Thirty minutes, authoritative, free.
4. Brooker, [Latency Sneaks Up On You](https://brooker.co.za/blog/2021/08/05/utilization.html) + [Open and Closed, Omission and Collapse](https://brooker.co.za/blog/2023/05/10/open-closed.html). Both short, and the queueing intuition sticks.
5. Google SRE [Ch. 4 (SLOs)](https://sre.google/sre-book/service-level-objectives/) and [Ch. 6 (Monitoring)](https://sre.google/sre-book/monitoring-distributed-systems/), so your test has a pass/fail criterion at all.
6. Gregg's [benchmarking checklist](https://www.brendangregg.com/blog/2018-06-30/benchmarking-checklist.html). Print it and keep it nearby.

Deliverable: a one-page written SLO for one endpoint (SLI definition, target percentile, target value, and *why that value*), plus a written workload characterization from real production traffic.

### Weeks 3 and 4: first honest test

Install k6. Wire Micrometer + Prometheus + Grafana and the five panels from §2 Phase A. Turn on `pg_stat_statements` and `auto_explain`.

Deliverable: an average-load test against a staging service with production-like data, using an arrival-rate executor, with a warm-up scenario excluded from thresholds, a `dropped_iterations` threshold, and a Grafana dashboard showing app p99 next to `hikaricp_connections_pending` on the same time axis. Plus the pgbench sweep from Phase B, with the knee identified and written down.

Work through [k6-learn Module I](https://github.com/grafana-cold-storage/k6-learn). The repo has been moved to Grafana's cold-storage org and is read-only, but its tool-agnostic *performance testing principles* module is still the best free structured intro, and principles don't rot. Cross-check k6 API specifics against the current docs.

### Weeks 5 and 6: profiling and the DB side

- Learn `async-profiler`: CPU mode, then **wall-clock mode**, then alloc, then lock. Read flame graphs correctly: the x-axis is *sorted stacks* rather than a timeline, and width means frequency.
- Learn JFR: `jcmd <pid> JFR.dump name=continuous begin=-30m end=-15m` to extract exactly the bad window from a continuous recording. It is the most useful JFR habit to build.
- Read [PostgreSQL docs, Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html) start to finish once. Then keep the [pgMustard EXPLAIN Glossary](https://www.pgmustard.com/docs/explain) open next to your terminal.
- Work through [use-the-index-luke.com](https://use-the-index-luke.com/): [Anatomy of an index](https://use-the-index-luke.com/sql/anatomy) → [Two ingredients make the index slow](https://use-the-index-luke.com/sql/anatomy/slow-indexes) → the Where Clause chapter → keyset pagination.
- Paste plans into [explain.depesz.com](https://explain.depesz.com/) (colour-codes estimate-vs-actual row ratios) or self-hosted [PEV2](https://explain.dalibo.com/) if your SQL is sensitive.

Deliverable: one bottleneck found, fixed, and *verified*, with a before/after distribution plot, a differential flame graph, and a written note on whether the measured result matched your prediction.

### Weeks 7 and 8: make it a habit, not a project

- Smoke test in CI on every commit; nightly average-load with thresholds as the gate.
- An overnight soak. Only a soak finds leaks, unbounded caches, connection-pool leakage, log/disk growth, index bloat, and heap creep.
- A scalability sweep (N = 1,2,4,8,16,32) and a look at whether throughput *flattens* (contention) or *falls* (coherency). If it falls, stop adding concurrency.
- Write the runbook: how to run each test, where results live, what the thresholds are, what to check first when one fails.

Deliverable: a merged CI job and a one-page team runbook.

### Month 3 and beyond

Buy two books and read them properly. **Gregg, *Systems Performance* 2e** earns its place on chapters 2 and 12 alone, which are the best written treatment anywhere of *how to think about* a performance investigation. **Mihalcea, *High-Performance Java Persistence*** covers most of §5 above in Part I, on connection pooling, batching, statement caching and fetch sizes. Then subscribe to [Postgres FM](https://postgres.fm/); 40 minutes a week is the most efficient way to stay current on everything in §5 and §6.

---

## 8. Resource library

### Tier 0: free, and you should read all of it

| What | Where | Note |
|---|---|---|
| Gregg's methodology hub | [brendangregg.com/linuxperf.html](https://www.brendangregg.com/linuxperf.html) | Indexes USE, TSA, off-CPU analysis, active benchmarking, flame graphs, FlameScope, heat maps |
| USE Method | [usemethod.html](https://www.brendangregg.com/usemethod.html) | *"For every resource, check utilization, saturation, and errors."* Extends to software resources too: locks, thread pools, FD limits. That's where your Hikari pool lives, and plain hardware-USE misses it entirely |
| Thread State Analysis | [tsamethod.html](https://www.brendangregg.com/tsamethod.html) | The highest-leverage method for this particular situation |
| Active Benchmarking | [activebenchmarking.html](https://www.brendangregg.com/activebenchmarking.html) | Analyze the system *while the benchmark runs* |
| Benchmarking checklist | [7 questions](https://www.brendangregg.com/blog/2018-06-30/benchmarking-checklist.html) | Why not double? Was it tuned? Did it break limits? Did it error? Does it reproduce? Does it matter? Did it even happen? |
| Gil Tene, How NOT to Measure Latency | [QCon SF 2015](https://www.infoq.com/presentations/latency-response-time/) · [QCon London 2013](https://www.infoq.com/presentations/latency-pitfalls/) | Watch before your first test |
| k6 testing guides | [grafana.com/docs/k6/latest/testing-guides/](https://grafana.com/docs/k6/latest/testing-guides/) | Effectively a free course, and the most current authoritative free material on load-test *design* |
| Google SRE book + Workbook | [sre.google/sre-book](https://sre.google/sre-book/table-of-contents/) · [workbook](https://sre.google/workbook/table-of-contents/) | Book Ch. 4, 6, 22; Workbook Ch. 2, 11, 17 |
| The Tail at Scale | [CACM, free full text](https://cacm.acm.org/research/the-tail-at-scale/) | Dean & Barroso, 2013. The paper that made "p99 matters" a discipline |
| use-the-index-luke.com | [use-the-index-luke.com](https://use-the-index-luke.com/) | Markus Winand's *SQL Performance Explained*, free web edition. Vendor-neutral. **Highest ratio of "changes how you write SQL tomorrow" to time invested** |
| PostgreSQL docs: Using EXPLAIN | [docs](https://www.postgresql.org/docs/current/using-explain.html) | Better written than most books |
| pgMustard EXPLAIN Glossary | [pgmustard.com/docs/explain](https://www.pgmustard.com/docs/explain) | Every node type and EXPLAIN option in plain English. Covers PG18. Bookmark it |
| PostgreSQL 14 Internals | [free PDF](https://edu.postgrespro.com/postgresql_internals-14_en.pdf) | Egor Rogov. The best explanation anywhere of MVCC, vacuum, buffer cache, WAL, locks, planner. **Note: the English edition is PostgreSQL 14 only, with no English 17/18 edition as of July 2026** (the Russian edition is at 18). Costs you almost nothing for these fundamentals |
| Vlad Mihalcea's blog | [14 High-Performance Java Persistence Tips](https://vladmihalcea.com/14-high-performance-java-persistence-tips/) | The definitive free reference for JPA/Hibernate performance |
| Aleksey Shipilëv | [JVM Anatomy Quarks](https://shipilev.net/jvm/anatomy-quarks/) · [Nanotrusting the Nanotime](https://shipilev.net/blog/2014/nanotrusting-nanotime/) | The best free JVM performance writing. Read *Nanotrusting* before you write any timing code. On the Linux/x86 boxes he measures, `System.nanoTime()` costs ~26 ns per call with ~26 ns granularity, and is materially worse elsewhere, hence his conclusion: *"you are unable to get a direct measurement of anything shorter than 30 ns"* |
| Marc Brooker | [brooker.co.za/blog](https://brooker.co.za/blog/) | The best blog at the queueing/load-testing intersection |
| Postgres FM | [postgres.fm](https://postgres.fm/) | ~40 min, transcripts. Start with *Getting started with benchmarking*, *Buffers by default*, *Row estimates*, *Plan flips*, *Long-running transactions*, *Connections*, *work_mem*, *WAL and checkpoint tuning* |

### Books, ranked by what to buy first

| Book | Verdict |
|---|---|
| **Gregg, *Systems Performance*, 2nd ed. (2020)** | **The one book to buy.** The 2nd edition is still current, with no 3rd announced. Ch. 2 (Methodology) and Ch. 12 (Benchmarking) are the best written treatment of how to think about a performance investigation, and nothing else combines the methodology catalogue with real per-subsystem depth |
| **Mihalcea, *High-Performance Java Persistence*** | **The most directly applicable book here.** Every chapter backed by benchmarks against real databases. *Currency flag: self-published and continuously revised, with no visible edition number, so verify which Hibernate generation the current text targets before buying, and prefer the ebook* |
| **Oaks, *Java Performance*, 2nd ed. (2020)** | Still the best practical JVM tuning book, with an unusually good JDBC/JPA chapter. But it predates ZGC/Shenandoah maturity, generational ZGC, and virtual threads. Method holds; re-check GC flag advice |
| **Beckwith, *JVM Performance Engineering* (2024)** | The most current JVM performance book, by a long-time OpenJDK/HotSpot performance engineer. Covers JDK 17 through 21: modern GCs including generational ZGC, unified logging, virtual threads and their performance implications. Fills Oaks's gap |
| **Nygard, *Release It!*, 2nd ed. (2018)** | **Belongs on a load-testing list because it gives you the hypothesis list.** When your stress test degrades, its antipattern catalogue tells you what to look for. *Unbounded Result Sets* and *Blocked Threads* are the two most common JVM+RDBMS failure modes, and neither shows up in a CPU profile. [Free antipatterns chapter](https://media.pragprog.com/titles/mnee2/antipatterns.pdf) |
| **Kleppmann & Riccomini, *Designing Data-Intensive Applications*, 2nd ed. (March 2026)** | **The 2nd edition shipped March 2026** with a new co-author; the widely-recommended 1st edition is superseded. Its Ch. 2 ("Defining Nonfunctional Requirements") treatment of response time, averages and percentiles is one of the best short introductions to §1 here. Note this material was Ch. 1 in the 1st edition |
| **Evans, Gough & Newland, *Optimizing Java* (2018)** | Dated on specifics, **excellent on method.** Its chapters on benchmarking pitfalls and JVM measurement methodology are the best in any Java book. Read for discipline, not for flags |
| **Petrov, *Database Internals* (2019)** | Converts "the DB is slow" into a mechanism: B-tree page splits, buffer-pool eviction, latch vs lock, WAL/fsync as the serial bottleneck. The storage-engine half is timeless. Deprioritize until after the two starters |
| **Atkinson, *High Performance PostgreSQL for Rails* (2024)** | ~70% framework-independent Postgres, and the most *operationally practical* book on this list. Skip the ActiveRecord code; the pooling and safe-migration material maps straight onto HikariCP + Flyway |
| **Fontaine, *The Art of PostgreSQL*, 2nd ed.** | Read when you realize the fix is to stop pulling rows into the JVM. Complements Mihalcea: Mihalcea makes your ORM efficient, Fontaine makes you need less ORM |
| **Gunther, *Guerrilla Capacity Planning* (2007)** | Dated presentation, un-superseded substance: the USL from the source, and how to fit α and β from real data. The only model that predicts retrograde scaling |
| **Harchol-Balter, *Performance Modeling and Design of Computer Systems* (2013)** | If you want to *derive* rather than cite. Not on the critical path. [Free sample chapter](https://assets.cambridge.org/97811070/27503/excerpt/9781107027503_excerpt.pdf) |

Skip these. *Java Performance* (Hunt & John, 2011) is obsolete, pre-Java-8. *Java Performance Companion* (2016) has G1 material that predates JDK 9 and JFR material that predates OpenJDK 11; Beckwith supersedes it. Kirk Pepperdine's jClarity tools (Censum, Illuminate) were discontinued after Microsoft's 2019 acquisition, so ignore any tutorial recommending them and use JDK Mission Control or GCeasy instead. His underlying thesis, that *GC logs are the cheapest, highest-signal always-on production data you have, and nobody reads them*, is still true and still under-practiced.

### Hands-on

- **[JMH samples](https://github.com/openjdk/jmh)**: 36 progressively-numbered samples (numbered up to 39, with gaps), each teaching exactly one benchmarking pitfall: dead-code elimination, constant folding, state scopes, blackholes, false sharing, JIT warmup, fork isolation. This is your microbenchmarking curriculum; work through them in order. (Note JMH is at 1.37 with no release since 2023, which reads as *mature* rather than abandoned.)
- **[perf-ninja](https://github.com/dendibakh/perf-ninja)**: 26+ lab assignments with automated benchmarking and CI verification. C/C++, so second-order for you, but it's the only rigorous free hands-on profiling course out there. Pairs with the free CC0 book [*Performance Analysis and Tuning on Modern CPUs* 2e](https://github.com/dendibakh/perf-book) (Dec 2024).
- **[HdrHistogram plotter](http://hdrhistogram.github.io/HdrHistogram/plotFiles.html)**: paste histogram logs, get percentile-distribution overlays. This is how you show a before/after honestly.

*A note on paid "load testing certification" courses: the Udemy/Simplilearn tier is largely marketing funnels, and several teach the default closed-model JMeter thread-group pattern, meaning they will actively teach you to produce coordinated omission. Use k6's docs and the JMH samples instead.*

---

## 9. The checklist to pin above your desk

Gregg's seven questions, verbatim:

1. **Why not double?** What limits it?
2. **Was it tuned?** Were *both* client and target configured like production?
3. **Did it break limits?** Sanity-check against physical ceilings. If you "achieved" more than the wire allows, you measured a cache.
4. **Did it error?** Errors take faster code paths and silently inflate throughput. *A 503 returned in 2 ms will make your p99 look fantastic.*
5. **Does it reproduce?** Run it repeatedly.
6. **Does it matter?** Does the benchmark resemble real usage?
7. **Did it even happen?** Gregg's example: a firewall silently blocked the traffic, so "latency was the time it took the client to time out."

Plus, for this stack specifically:

- [ ] Load generator on a **different host** from the SUT, in the same region as real clients. Never localhost.
- [ ] **Keep-alive on.** Without it you're measuring TCP+TLS handshakes and burning ephemeral ports (~28,000 per src→dst tuple, held ~60 s by TIME_WAIT).
- [ ] `ulimit -n` raised on **both** sides. The 1024 default is the first wall you'll hit, and it presents as a silent plateau.
- [ ] Bandwidth arithmetic done in advance. 10k rps × 20 KB = 1.6 Gbps, which saturates a 1 Gbps link. (And many cloud instance types burst-then-throttle, producing an unexplained cliff several minutes in.)
- [ ] **Autoscaling and cron jobs disabled.** Otherwise you're measuring the scaler's reaction time.
- [ ] Warm-up excluded from assertions; warm-up completion *verified* (JIT compilation time flattening, C2 queue drained) rather than assumed.
- [ ] Offered rate reported alongside achieved rate. If they differ, the run is invalid.
- [ ] `dropped_iterations` thresholded at zero.
- [ ] Error rate **and error type** tracked, plus retry behaviour understood, because client retries convert a well-behaved closed system into an open one exactly when you least want it.
- [ ] p99 disaggregated **per instance**, not just in aggregate.
- [ ] HTTP thread pool and accept backlog on the dashboard, not just the DB pool.
- [ ] Percentiles from histograms, never averaged across instances.
- [ ] `max` reported, always.
- [ ] `pg_stat_statements_reset()` before each run.
- [ ] Full provenance recorded: git SHA, JVM flags, JDK build, dataset snapshot, generator version.
- [ ] Exactly **one** change per iteration.

---

## Appendix: copy-paste kit

### k6: arrival-rate scenario with warm-up separated and a CI gate

```javascript
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  discardResponseBodies: true,
  scenarios: {
    warmup: {                          // JIT + buffer pool + statement cache; NOT asserted
      executor: 'constant-arrival-rate',
      rate: 200, timeUnit: '1s', duration: '5m',
      preAllocatedVUs: 100, maxVUs: 400,
      tags: { phase: 'warmup' },
    },
    steady: {                          // the measured window
      executor: 'constant-arrival-rate',
      rate: 800, timeUnit: '1s', duration: '15m', startTime: '5m',
      preAllocatedVUs: 300, maxVUs: 1200,
      tags: { phase: 'steady' },
    },
  },
  thresholds: {
    'http_req_failed{phase:steady}':   ['rate<0.001'],
    'http_req_duration{phase:steady}': ['p(95)<250', 'p(99)<800'],
    'dropped_iterations':              ['count<1'],   // generator kept up, or run is invalid
  },
};

export default function () {
  // spread across the table, and skew it (Zipf-ish) rather than uniform
  const id = 1 + Math.floor(5_000_000 * Math.pow(Math.random(), 4));
  const res = http.get(`https://orders.svc.internal/api/orders/${id}`, {
    tags: { name: 'GET /api/orders/:id' },   // avoids URL cardinality blowup
  });
  check(res, { 'status 200': (r) => r.status === 200 });
}
```

```bash
K6_PROMETHEUS_RW_SERVER_URL=http://prom:9090/api/v1/write \
K6_PROMETHEUS_RW_TREND_STATS='p(95),p(99),p(99.9),max' \
k6 run -o experimental-prometheus-rw orders-load.js
# exit 0 = pass, 99 = threshold breach
```

Preallocated VUs follow Little's Law: `preAllocatedVUs ≈ rate × median_iteration_duration + headroom`.

### Profiling

```bash
# The one to run when p99 is bad but CPU looks idle: off-CPU analysis for the JVM
asprof -e wall -t -i 50ms -d 60 -f /tmp/wall.html <pid>

asprof -d 30 -f /tmp/cpu.html <pid>                        # CPU flame graph
asprof -e alloc --alloc 512k -d 60 -f /tmp/alloc.html <pid> # allocation churn
asprof -e lock --lock 10ms -d 60 -f /tmp/lock.jfr <pid>     # contention
asprof -e ctimer -d 30 -f /tmp/cpu.html <pid>               # container without perf access

# JFR: keep a continuous recording, then extract exactly the bad window afterwards
jcmd <pid> JFR.dump name=continuous begin=-30m end=-15m filename=/tmp/window.jfr
jcmd <pid> JFR.start name=diag settings=profile duration=120s filename=/tmp/diag.jfr
```

Know which heap problem you have: **retention** (heap grows and doesn't come back) → heap dump + Eclipse MAT. **Churn** (heap fine, GC burns 20% of CPU) → allocation profiling. Churn is the far more common load-test finding, and a heap dump is nearly useless for it because the garbage is already collected.

### Postgres: the three queries you'll run most

```sql
-- 1. Top queries. Run it three times: by total_exec_time, by calls, by temp_blks_written.
SELECT round(100.0 * total_exec_time / sum(total_exec_time) OVER (), 1)   AS pct_total,
       round(total_exec_time)                                            AS total_ms,
       calls,
       round(mean_exec_time::numeric, 3)                                 AS mean_ms,
       round(stddev_exec_time::numeric, 3)                               AS stddev_ms,
       round(rows::numeric / nullif(calls,0), 1)                         AS rows_per_call,
       round((shared_blks_hit + shared_blks_read)::numeric
             / nullif(calls,0), 1)                                       AS blks_per_call,
       temp_blks_written,
       left(regexp_replace(query, '\s+', ' ', 'g'), 120)                 AS query
FROM pg_stat_statements
WHERE query NOT ILIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC LIMIT 25;
```

`blks_per_call` is the money column: it's a property of the *plan*, stable across cache states and machine sizes, unlike timing. A point lookup should touch roughly 5 to 15 buffers. Hundreds means a missing index or a bad plan.

```sql
-- 2. Wait-event histogram. Run in a loop at 1 Hz during the test.
--    The resulting histogram IS your bottleneck diagnosis.
SELECT clock_timestamp() AS ts,
       coalesce(wait_event_type, 'CPU') AS wait_type,
       coalesce(wait_event, '-')        AS wait_event,
       state, count(*)
FROM pg_stat_activity
WHERE backend_type = 'client backend' AND pid <> pg_backend_pid()
  AND state <> 'idle'          -- keeps active + 'idle in transaction'
GROUP BY 1,2,3,4 ORDER BY 5 DESC;
```

Note the filter: excluding `state = 'idle'` is what keeps parked pool connections (which sit in `Client`/`ClientRead` forever) from drowning out the signal. `ClientRead` on a backend that is `idle in transaction` is a *different* thing entirely. That's finding #3 in §5, and it survives this filter.

```sql
-- 3. Who is blocking whom, and who is holding a transaction open
SELECT a.pid, a.state, a.wait_event_type, a.wait_event,
       pg_blocking_pids(a.pid) AS blocked_by,
       now() - a.xact_start    AS xact_age,
       left(a.query, 90)       AS query
FROM pg_stat_activity a
WHERE cardinality(pg_blocking_pids(a.pid)) > 0
   OR (a.state = 'idle in transaction' AND now() - a.xact_start > interval '200ms')
ORDER BY xact_age DESC;
```

```sql
-- Guardrails: turn invisible pile-ups into fast, loud, countable errors
ALTER ROLE app_user SET statement_timeout = '5s';
ALTER ROLE app_user SET lock_timeout = '2s';
ALTER ROLE app_user SET idle_in_transaction_session_timeout = '10s';
```

### The EXPLAIN habit

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS) <query>;
-- PG18+ enables BUFFERS implicitly with ANALYZE
```

Read it **bottom-up**, and find the *deepest* node where the row estimate first goes wrong. Everything above inherits that error, so fixing the leaf fixes the plan. Four things to look at:

1. **actual rows × `loops`.** `(actual time=0.003..0.003 rows=1 loops=10000)` is not 0.003 ms of work. It's 30 ms and 10,000 index descents. This is the #1 beginner error.
2. **Buffers per row returned.** 50,000 buffers for 10 rows means you read a table to throw it away.
3. **Planning vs execution time.** `Planning: 12 ms / Execution: 0.4 ms` is a planning problem (wide partitioning, huge `IN` lists, many joins).
4. **`Rows Removed by Filter`.** Pure wasted work, and the fix is usually to move that predicate from `Filter:` into `Index Cond:`.

For bad estimates on correlated columns, raising `default_statistics_target` won't help. Given `WHERE city='Seoul' AND country='KR'`, the planner multiplies selectivities assuming independence and can underestimate by 100×. Extended statistics fix that:

```sql
CREATE STATISTICS s (dependencies, ndistinct, mcv) ON city, country FROM t;
ANALYZE t;
```

---

## Notes on currency and things to verify yourself

Everything above was checked against primary sources in July 2026, but a few points are version-sensitive or were not fully verifiable, and you should confirm them against your own environment rather than trusting this document:

- **Tool versions move.** At time of writing: k6 2.1.x, Gatling OSS 3.15.x, async-profiler 4.5, JMeter 5.6.3 (Jan 2024, with 6.0 long delayed), JMH 1.37, HikariCP 7.x, PostgreSQL 18 stable with 19 in beta. Check before you pin anything.
- **PostgreSQL version changes the advice**, not just the syntax. PG17 introduced `pg_stat_checkpointer` (moving counters out of `pg_stat_bgwriter`) and renamed `pg_stat_statements`' I/O timing columns, so dashboards break silently on upgrade. PG18 makes `BUFFERS` implicit with `ANALYZE`, adds async I/O and B-tree skip scan, and adds portable optimizer statistics. PG19 (beta) turns **JIT off by default**.
- **JDK version matters more than usual here.** Virtual threads were final in JDK 21, but until JDK 24 a `synchronized` block around a blocking call pinned the carrier thread, and JDBC drivers use `synchronized` heavily. On JDK 21, virtual threads plus a relational database can pin and produce a mysterious throughput cliff. If you plan to load-test virtual threads against a database, be on JDK 25 (current LTS).
- **Verification done:** every formula here was recomputed, every blockquote was fetched against its primary source, and 46 of the linked URLs were retrieved. No dead links. The only non-200 responses were bot-blocking from `github.com`, `cacm.acm.org` and `oreilly.com`, each confirmed alive by another route. Those pages load fine in a browser.
- **Not verified:** *High-Performance Java Persistence* carries no visible edition number, so which Hibernate generation the current revision targets is unknown. Check before buying, and prefer the ebook. Several YouTube links for the canonical Gregg and Martin Thompson talks could not be confirmed to play (rate-limited fetcher); the InfoQ links for Gil Tene are verified and are a safe substitute.
- **Deliberately opinionated:** the k6-over-Gatling recommendation and the "halve the pool as a probe" heuristic are judgment calls, not facts. Both are argued with their trade-offs stated above; a knowledgeable colleague may reasonably land elsewhere on either.
