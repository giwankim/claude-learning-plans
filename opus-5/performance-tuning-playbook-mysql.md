---
title: "Performance Testing → Performance Tuning (MySQL Edition)"
category: "Performance & Optimization"
description: "The MySQL companion to the performance tuning playbook: a learning roadmap and working playbook for load-testing and tuning JVM services that sit in front of a busy MySQL database, written for someone who has never run a structured load test and verified in July 2026 against a running MySQL 8.4.11 instance rather than against documentation (several widely repeated defaults turned out to be wrong). It starts from the same core idea, that a load test is a controlled experiment to locate a bottleneck rather than a way to produce a number, then covers the five things to internalize before the first test (coordinated omission, open versus closed workload models, percentile composition across fan-out, the knee of the utilization curve, and Little's Law alongside Amdahl's Law). From there it lays out the measure-and-change loop, a triage tree for a bad p99 that runs from generator saturation through CPU throttling and connection-pool waits into InnoDB, a minimum viable toolchain, and the MySQL findings you will actually get. It closes with an anatomy of pools and queues where requests actually wait, test-data realism, a phased study plan, a ranked resource library, a desk checklist, a copy-paste kit, and notes on which claims could not be verified."
---

# Performance Testing → Performance Tuning

**A learning roadmap and working playbook for JVM services with a heavy MySQL database.**
Written for someone who has never run a structured load test. Verified July 2026 against MySQL 8.4.11.

> **MySQL edition.** Defaults marked **[verified 8.4.11]** were read from a running MySQL 8.4.11 instance, not from documentation — several widely-repeated "facts" turned out to be wrong (see §11). Where 8.4 and 9.7 differ, it's flagged.

---

## 0. The one idea everything else hangs off

A load test is **not** a way to produce a number. It is a **controlled experiment to locate a bottleneck.**

The number ("we did 800 rps at 240 ms p99") is a byproduct. The output you actually want is *"the limiter is X, here is the evidence, here is the predicted effect of changing it."* Brendan Gregg has a name for testing without that discipline — **Casual Benchmarking** — and a one-line summary of how it fails:

> "casual benchmarking: you benchmark A, but actually measure B, and conclude you've measured C."

(His related anti-method, **Passive Benchmarking**, is the organizational version: run a tool with a variety of options, make a slide deck, hand the slides to management, analyze nothing.)

So the shape of everything below is: **hypothesis → prediction with a number → one change → re-measure identically → keep or revert.** If you take one thing from this document, take the phrase *"what number do I predict, and what would falsify it?"*

Three framing consequences worth stating up front, because they save months:

- **Latency is a function of utilization, not of code speed.** Make the code 30% faster and latency drops — then traffic grows, utilization returns to where it was, and latency creeps back with no code change. Efficiency work should be tracked by *mean* latency or CPU-seconds/request; p99 is your *saturation* early-warning signal. Don't conflate the two. ([Marc Brooker, *Latency Sneaks Up On You*](https://brooker.co.za/blog/2021/08/05/utilization.html))
- **For a JVM service in front of a busy database, a CPU profile shows you a small fraction of the story.** Your wall-clock time is spent *Sleeping* (blocked on a socket) and in *Lock* (blocked waiting to borrow from a pool). The reflex to open a CPU flame graph is the single most common beginner misstep in your exact situation.
- **Requests queue in more places than you think, and most of them are invisible.** A request can be waiting in the kernel accept queue, in Tomcat's connection limiter, in the worker-thread queue, in the HikariCP borrow queue, in an outbound HTTP pool's lease queue, or inside InnoDB on a row lock. **Only the last stage of that journey has a thread you can profile.** §6 is entirely about this.

---

## 1. Five things to internalize before your first test

These are non-negotiable. Skip them and your numbers will be fiction — optimistic by one to three orders of magnitude at the tail — and you will spend weeks "fixing" things that were never broken.

### 1.1 Coordinated omission: your load generator is probably lying

If the generator pauses while the system is slow, the slow period contributes almost no samples. The bias isn't noise — it's **systematically toward good outcomes**, because the omission is *caused by* the badness. Averages get mildly wrong; **percentiles get catastrophically wrong.**

Gil Tene's canonical example. A 200-second test: 100 s of 10,000 requests at 1 ms, then 100 s where the system is completely frozen.

| | Average | 99.99th percentile |
|---|---|---|
| Honest accounting | **~25 s** | ~100 s |
| What a typical load generator reports | **10.9 ms** | **1 ms** |

Half the test duration produced 1/10,000th of the data. Tene's rule:

> "The number one indicator you should never get rid of is the maximum value. That is not noise, that is the signal."

**Your smell test:** a `max` of 30 s next to a `p99.99` of 3 ms. That's suggestive rather than conclusive — with 10M samples, one genuine outlier (a long safepoint, a TCP retransmit) can produce it honestly. Confirm with the two decisive checks: **does offered rate equal achieved rate**, and **is there a gap in the sample timeline** during the bad window?

**Watch:** [How NOT to Measure Latency — QCon SF 2015](https://www.infoq.com/presentations/latency-response-time/) (54 min). Written summary: [Everything You Know About Latency Is Wrong](https://bravenewgeek.com/everything-you-know-about-latency-is-wrong/).

### 1.2 Open vs closed workload models

- **Closed:** new requests are triggered by *completions* (a fixed population of virtual users, optionally with think time).
- **Open:** new requests arrive at a *rate*, independent of whether prior ones finished.

Why this is load-bearing: a closed test has **built-in negative feedback**. System slows → fewer requests → less pressure → system recovers. That is not how the internet works.

Quantified: k6's own example puts a 6-second request in a 60-second test at **~10 iterations closed vs 60 open** — a 6× difference in delivered load. Brooker's simulation of a bimodal service found the closed benchmark **underestimated p99 by a factor of at least 25** — closed reported under 1 ms where open reported over 25 ms.

And there's a second, subtler penalty: closed systems genuinely *have* tamer latency distributions (they can't build unbounded queues). So closed results are optimistic twice over — once from measurement artifact, once from the model itself.

**Practical rule: use arrival-rate (open) executors for anything modelling internet traffic.** Use closed-with-think-time only when you're genuinely modelling a fixed population (500 kiosks, a device fleet).

Read: [k6, Open vs closed models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/) and [Brooker, Open and Closed, Omission and Collapse](https://brooker.co.za/blog/2023/05/10/open-closed.html).

### 1.3 Percentiles compose brutally — and p95 is not enough

Across a session loading ~200 resources, only **0.0035%** of users experience *solely* p95-or-better latency. Restated: **99.997% of users hit something worse than your p95.** If a page needs 40 independent calls each p95-good, the chance all 40 are good is 0.95⁴⁰ ≈ 13%.

And fan-out multiplies the tail. From Dean & Barroso, [*The Tail at Scale*](https://cacm.acm.org/research/the-tail-at-scale/):

> "If a user request must collect responses from 100 such servers in parallel, then 63% of user requests will take more than one second."

(servers that normally answer in 10 ms but have a 1-second p99)

**The reading for your situation:** an N+1 query problem is not just N extra round trips — it's **N independent draws from the database's tail distribution per user request.**

Rules that follow:

- Report `p50 / p90 / p99 / p99.9 / max`. Always include max.
- **You cannot average percentiles** across instances or time buckets. Aggregate *histograms*, then compute percentiles. This is a live trap in Micrometer: the `percentiles:` property computes percentiles **inside each JVM** and exports them as gauges you cannot correctly combine, while `percentiles-histogram:` exports bucket counts you *can* aggregate with `histogram_quantile()`. **For any multi-instance service, use `percentiles-histogram`** — and bound it with `minimum-expected-value`/`maximum-expected-value` or you'll generate an absurd number of buckets and blow up Prometheus cardinality (§2 Phase A).
- Record every sample, not a sample of samples: [HdrHistogram](https://github.com/HdrHistogram/HdrHistogram) does this in constant time with fixed memory, and its histograms are losslessly mergeable.
- **MySQL-specific caveat:** `performance_schema`'s `QUANTILE_95` / `QUANTILE_99` / `QUANTILE_999` columns are, per the docs, *"a high estimate, computed from the histogram data collected"* — the upper edge of the containing bucket. Never present them as exact percentiles.

### 1.4 The knee of the curve

For an M/M/1 queue, expected number in system is `E[N] = ρ/(1-ρ)` where ρ is utilization:

| ρ | 0.5 | 0.8 | 0.9 | 0.95 | 0.99 |
|---|---|---|---|---|---|
| E[N] | 1 | 4 | 9 | 19 | 99 |

Going 50% → 80% utilization *quadruples* the number of requests in the system, and raises response time **2.5×**. 80% → 95% multiplies response time a further **4×**. The "knee" isn't a threshold anyone chose; it's a hyperbola with a pole at ρ=1.

> **Don't read the `E[N]` ratio as the latency ratio** — it overstates it, because arrival rate rose too. For M/M/1, `W = 1/(μ(1−ρ))`, so the response-time multiplier between two utilizations is `(1−ρ₁)/(1−ρ₂)`: 0.5→0.8 is ×2.5 (not ×4), and 0.8→0.95 is ×4 (not ×4.75). Note also that `E[N]` counts requests *in the system*, queue plus in-service; expected number *queued* is `ρ²/(1−ρ)`.

**Consequence for test design:** "peak rps at 30 s p99" is a useless number. **The number you want is the knee** — the load at which latency starts rising faster than throughput. That is your real capacity.

**In MySQL, the knee has a name you can watch directly: `Threads_running`.** More on this in §6.4.

### 1.5 Two formulas that decide where you spend your week

**Little's Law** — `L = λW`, or in load-testing terms:

> **Concurrency = Throughput × Response time**

Three uses:

1. **Size the test.** 500 rps at an expected 200 ms needs ~100 in-flight requests.
2. **Validate the result.** After a run, check `concurrency ≈ throughput × latency`. If it doesn't hold, the test is broken (dropped iterations, generator saturation, coordinated omission).
3. **Find hard ceilings.** A 20-connection pool with 10 ms mean DB service time caps you at `20/0.010 = 2000 queries/sec`. No JVM tuning moves that number.

That third use is the most valuable thing in this document, and §6 applies it to all four of your pools.

**Amdahl's Law** — `S = 1/((1-p) + p/s)`, and in the limit `S_max = 1/(1-p)`.

If a component is 5% of latency, your absolute ceiling — with a *perfect* fix — is a 5.3% improvement. **Get `p` from a profile before you touch anything.** This is the arithmetic that turns "profile first" from a slogan into a rule, and it's how you say *no* to speculative optimization without saying no to optimization. Knuth's full quote licenses exactly this:

> "We should forget about small efficiencies, say about 97% of the time: premature optimization is the root of all evil. **Yet we should not pass up our opportunities in that critical 3%.**"

*(Worth knowing but not on the critical path: the [Universal Scalability Law](https://www.perfdynamics.com/Manifesto/USLscalability.html), `X(N) = γN / (1 + α(N-1) + βN(N-1))`. Its β term predicts **retrograde scaling** — throughput that peaks then falls as you add load. That is precisely what an oversized MySQL connection pool looks like: past the knee, `Threads_running` climbs and throughput *decreases*. Amdahl can only flatten; USL can go down.)*

---

## 2. The loop

This is the playbook. Seven phases; phases D–F repeat.

### Phase A — Instrument *before* you generate load

**A load test without server-side telemetry produces a number and no explanation.** You'll learn "p99 is 1.8 s" and have no idea why. Wire this first; it is the difference between a week of work and a month.

#### App side (JVM)

```yaml
management:
  metrics:
    distribution:
      percentiles-histogram:
        http.server.requests: true        # exports BUCKETS — aggregatable
      minimum-expected-value: { http.server.requests: 1ms }
      maximum-expected-value: { http.server.requests: 10s }
server:
  tomcat:
    mbeanregistry:
      enabled: true                       # ← without this, Tomcat thread metrics are SILENTLY ABSENT
spring:
  datasource:
    name: orders-primary                  # makes the `pool` tag meaningful
    hikari:
      maximum-pool-size: 20
      connection-timeout: 2000            # NOT the 30s default
      max-lifetime: 280000                # < the smallest idle timeout in the path — see §6.4
      leak-detection-threshold: 20000
  jpa:
    open-in-view: false                   # Spring defaults this to true. Turn it off.
```

- JFR always on: `-XX:StartFlightRecording:name=continuous,settings=default.jfc,disk=true,maxage=1h,maxsize=512m,dumponexit=true` (Oracle documents `default.jfc` at **<1% overhead** — leave it running in production).
- GC + safepoint logging: `-Xlog:gc*,safepoint:file=/var/log/app/gc.log:time,uptime,level,tags:filecount=5,filesize=100M`
- OpenTelemetry Java agent with **sampling at 1.0 during the test window** (head-based 1% sampling systematically misses your p99 — the traces you need are by definition rare).
- **`ApplicationName` in the JDBC URL.** Free, and it's how you attribute a rogue query to a service in `performance_schema`.

#### MySQL side

Two things you must know before you configure anything:

1. **`performance_schema` is ON by default, but every `events_waits_*` consumer is OFF, and *zero* `wait/synch` instruments are enabled** [verified 8.4.11 — 54 of 373 wait instruments enabled, all of them `wait/io` or `wait/lock`]. **Mutex and rwlock contention — exactly what you hit at high concurrency — is invisible at default settings.**
2. **You still get wait *summaries* for free**, because `global_instrumentation=YES`. The per-thread, per-event tables are what need the consumers.

```sql
-- Before the test: turn on what you'll need
UPDATE performance_schema.setup_consumers SET ENABLED='YES'
 WHERE NAME IN ('events_statements_history_long','events_waits_current',
                'events_waits_history','events_transactions_history_long',
                'events_statements_cpu');

CALL sys.ps_setup_enable_instrument('wait/synch');   -- the high-concurrency blind spot
                                                     -- ("Enabled 316 instruments")

-- Enable the InnoDB metrics you'll actually read. THIS ONE MATTERS: 240 of 314
-- INNODB_METRICS rows are DISABLED by default, including almost the whole `log`
-- module — and a disabled metric returns COUNT=0, not an error. See the warning below.
SET GLOBAL innodb_monitor_enable = 'module_log';

-- Reset so numbers are per-run
CALL sys.ps_truncate_all_tables(FALSE);
TRUNCATE performance_schema.events_statements_summary_by_digest;
```

> ⚠️ **The silent-zero trap, and it's the nastiest thing in this document.** `INNODB_METRICS.log_lsn_checkpoint_age` — which §5.12 and the triage tree both tell you to watch — is **disabled by default and returns `COUNT = 0`**. You run the query, see 0, and conclude checkpoint age is nowhere near the threshold. After `innodb_monitor_enable` plus write activity, the same query returned **579334**. **Always select `STATUS` alongside `COUNT`** so a disabled metric can't masquerade as a healthy reading. `sys.metrics` exposes the same thing as an `Enabled` column — read it.
>
> (`trx_rseg_history_len`, happily, *is* enabled by default.)

```ini
# my.cnf for a load-test environment
slow_query_log            = ON
long_query_time           = 0        # log EVERYTHING for a bounded window
log_slow_extra            = ON       # ← the closest thing MySQL has to auto_explain
log_slow_admin_statements = ON
log_output                = FILE     # never TABLE: it serializes on a lock,
                                     # pt-query-digest can't read it, and
                                     # log_slow_extra is ignored for TABLE

innodb_print_all_deadlocks = ON      # ← the single highest-value one-line change
performance_schema_max_digest_length = 4096   # else long ORM SQL truncates and
max_digest_length                    = 4096   # distinct queries collapse into one row
                                              # ⚠️ both are READ-ONLY: my.cnf + restart,
                                              #    SET GLOBAL fails with ERROR 1238
```

> ⚠️ **A JVM-specific trap:** `long_query_time` is **session-scoped**. HikariCP holds connections for hours, so `SET GLOBAL long_query_time=0` will **not** affect already-established pool connections. Bounce the pool (temporarily shorten `maxLifetime`) or, on Percona Server, use `slow_query_log_use_global_control`.

**Why `log_slow_extra` matters so much.** MySQL has **no `auto_explain` equivalent** — there is no way to make the server record an execution plan alongside a slow query. This is a genuine gap versus PostgreSQL. `log_slow_extra` is the substitute: it writes per-statement **plan symptoms** without the plan, and the two fields that matter most are `Sort_merge_passes` (non-zero = a filesort spilled to disk) and `Created_tmp_disk_tables` (a temp table went to disk). Together with `Read_rnd_next` (scanning) and `Read_key` (index use), you can infer most of what a plan would tell you.

#### The dashboard, in priority order

If you build only six panels, build these:

| Metric | Why it's here |
|---|---|
| `http_server_requests_seconds_bucket` by uri/status | your SLO, via `histogram_quantile()` |
| **`hikaricp_connections_pending`** | **the best DB-saturation signal.** Sustained > 0 = threads queueing for a connection |
| `hikaricp_connections_usage_seconds` | how long you *hold* connections — usually the root cause |
| **`mysql_global_status_threads_running`** | **MySQL's run queue.** The knee lives here (§6.4) |
| `tomcat_threads_busy_threads / tomcat_threads_config_max_threads` | inbound saturation (§6.2) |
| `httpcomponents_httpclient_pool_total_pending` (or the Reactor Netty equivalent) | outbound pool queue (§6.3) — **you must register this binder yourself** |
| `jvm_gc_pause_seconds` (max) + allocation rate | GC's contribution to the tail |
| `container_cpu_cfs_throttled_periods_total / ..._periods_total` | CPU throttling, which looks *exactly* like GC and appears in no GC log |
| `rate(node_netstat_TcpExt_ListenOverflows[1m])` | **the accept queue, which has no Micrometer metric at all** (§6.2) |

### Phase B — Establish the floor and the ceiling

Before you test your application, find out what the environment can do at all.

1. **Latency floor.** `ping` the SUT, and `curl -w 'conn=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer}\n'`. You need to know what you're adding to.

2. **Storage ceiling — do this first, always.** The single-threaded fsync rate is a hard ceiling on durable commits per second, and no MySQL tuning moves it:

   ```bash
   sysbench fileio --file-total-size=32G --file-num=64 prepare
   # random reads, 16 KB = InnoDB's page size, O_DIRECT to match innodb_flush_method
   sysbench fileio --file-total-size=32G --file-test-mode=rndrd \
     --file-extra-flags=direct --file-block-size=16384 --time=300 --threads=16 run
   # random writes WITH fsync — this is your commit-rate ceiling
   sysbench fileio --file-total-size=32G --file-test-mode=rndwr \
     --file-extra-flags=direct --file-block-size=16384 \
     --file-fsync-all=on --time=300 --threads=1 run
   sysbench fileio --file-total-size=32G cleanup
   ```

   If that last number is 800/s, then at `innodb_flush_log_at_trx_commit=1` **you cannot durably do 5,000 commits/s**, full stop. Knowing this before the load test saves days of tuning the wrong layer. It also tells you whether 8.4's `innodb_io_capacity=10000` default is a fantasy on your cloud volume.

3. **Database ceiling — the concurrency sweep.** This is the single most valuable exercise in this document.

   ```bash
   COMMON="--db-driver=mysql --mysql-host=db --mysql-user=bench --mysql-password=... \
           --mysql-db=bench --tables=16 --table-size=10000000 --rand-type=zipfian"

   sysbench oltp_read_write $COMMON prepare
   for T in 1 2 4 8 16 32 64 128 256; do
     sysbench oltp_read_write $COMMON --threads=$T --time=300 --warmup-time=60 \
       --report-interval=10 --percentile=99 --histogram=on run | tee sweep-$T.txt
   done
   ```

   Plot throughput and p99 against thread count. **You will see the knee** — throughput flattens, then *falls*, while p99 inflects sharply. That peak is an empirical upper bound on your total connection pool size across all app instances, derived on *your* hardware.

   Two things to get right, or the sweep lies to you:
   - **Table size must exceed `innodb_buffer_pool_size`.** Otherwise you're measuring RAM.
   - **`--rand-type` defaults to `special`**, which concentrates access on a small hot region. That can flatter your I/O results *or* exaggerate lock contention. Run at least `uniform` (worst-case I/O) and `zipfian` (realistic skew) to bracket reality, and **always state which you used** when reporting a number.

   And correlate every sweep point with server-side metrics, or you learn a number without a reason:

   ```bash
   mysqladmin -i10 extended-status | grep -E \
     'Threads_running|Innodb_buffer_pool_reads|Innodb_buffer_pool_wait_free|Innodb_row_lock_waits|Innodb_log_waits'
   ```

   | Reading at the knee | Diagnosis |
   |---|---|
   | Throughput flat, CPU ~100% | CPU bound — optimize queries, more concurrency won't help |
   | Throughput flat, CPU low, `Innodb_buffer_pool_reads` high | I/O bound — bigger buffer pool |
   | Throughput **falls** past the knee, `wait/synch` in the top waits | internal contention — **reduce pool size** |
   | `Innodb_row_lock_waits` climbing | application lock contention — shorten transactions, consider READ COMMITTED (§5.9) |
   | `Innodb_log_waits` / redo-file waits | durability bound — `innodb_redo_log_capacity`, `flush_log_at_trx_commit`, `sync_binlog` |

   Yes, plain `sysbench` is a closed-loop generator — precisely the model §1.2 argues against. That's fine *here*, because the point of this experiment is to vary concurrency and watch what breaks; you are not modelling internet traffic.

4. **Prove the generator isn't the bottleneck.** Every run: check generator CPU (any saturated core = garbage results) and its own error counters. The definitive test — **run the same scenario from 2× the generators and confirm results scale linearly.** If p99 *improves* when you add generators, every prior number was generator-bound.

### Phase C — Build the workload model

Gregg's Workload Characterization Method: **who** is causing the load, **why** it's being called, **what** the load is (rps, read/write ratio, payload sizes), **how** it changes over time. Do this *before* you write a script, or you'll load-test the wrong thing.

Concretely:

- Derive your target rate from **peak-hour production data, never a monthly average.** k6's worked example does the Little's Law arithmetic on peak-hour data — 990 sessions × 92 s ÷ 3600 = **25.3 concurrent users** — and then contrasts it with the far smaller figure you'd get by spreading the same traffic across a month. The point isn't the second number; it's that sizing from an average under-provisions you by orders of magnitude.
- Weight endpoints by real traffic share, not by how interesting they are.
- **Parameterize so each virtual user hits different rows.** 100 VUs all doing `GET /orders/1` measures your caches, not your database.
- Model **skewed** key access (Zipf/Pareto), not `random()`. Real traffic has 1% of rows taking 50% of the traffic — that's where your hot-row lock contention lives, and in MySQL under the default `REPEATABLE READ` that contention is *worse* than you'd expect because of gap locks (§5.9). Uniform access will never find it.

### Phase D — Baseline

Run the **average-load** test: ramp → warm-up → measured steady window.

Warm-up is not optional on the JVM. C2 needs thousands of executions per hot path; a cold JVM runs 10–100× slower. And for a DB-heavy service the *other* caches dominate anyway: the InnoDB buffer pool, Connector/J's client-side statement cache, any Caffeine/Redis layer, TLS session tickets.

Shape: **ramp 2–5 min → steady warm-up 5+ min (discarded) → measurement window 10–30 min (asserted).**

**A MySQL-specific warm-up note:** run long enough to cross at least two checkpoint intervals, or you measure the pre-checkpoint honeymoon. Watch `INNODB_METRICS.log_lsn_checkpoint_age` against `innodb_redo_log_capacity` — if the age never approaches ~75% of capacity during your run, you haven't yet seen the flush behaviour production will see.

Record and keep, for every run: the full latency distribution, a CPU flame graph, a **wall-clock** flame graph, the GC log, a `performance_schema` digest dump, `SHOW ENGINE INNODB STATUS` — plus provenance: git SHA, full JVM flags, JDK build, **MySQL version and the full non-default variable set**, dataset snapshot ID, generator version and `--rand-type`, and the generator's own resource graphs. Without provenance you cannot compare next month's run, and comparison is the entire point.

> Grab the non-default server config with:
> ```sql
> SELECT VARIABLE_NAME, VARIABLE_VALUE FROM performance_schema.global_variables
> ORDER BY VARIABLE_NAME;   -- diff this against a stock 8.4 instance
> ```

### Phase E — Locate, don't guess

Use **Thread State Analysis**: for each thread of interest, measure total time in each state, and investigate the biggest bucket first.

| State | What it means | Where to look |
|---|---|---|
| Executing | on-CPU | CPU flame graph |
| Runnable | waiting for a CPU turn | CPU saturation, **cgroup throttling** |
| Sleeping | blocked on I/O | **your DB and HTTP calls live here** |
| Lock | waiting on a monitor or pool | **all four of your pools live here** |

The tool for the last two on the JVM is **`async-profiler -e wall`**. A CPU profile will show you an idle-looking flame graph while wall-clock shows the actual stall. §6.5 gives you the frame-by-frame decoder ring.

Then compute `p` for your candidate (Amdahl). **If it's under 10% of total time, stop and find a bigger target.**

### Phase F — One change, with a predicted number

Write the hypothesis down *with a number*: *"the outbound HTTP pool is capped at 5 per route; at 60 ms mean that's an 83 rps ceiling. Raising it to 96 will lift throughput from 83 to ~800 rps and drop p99 from 1200 ms to ~150 ms."* A hypothesis without a predicted number can't be falsified.

Then: **change exactly one thing.** Re-measure identically — same script, same data, same environment, same duration, same warm-up. Compare with a differential flame graph (async-profiler 4.4+ generates these directly) and a percentile-distribution overlay.

**Revert is the default.** And critically: if the measured result doesn't match the prediction — *even if it improved* — you don't understand the system yet. Investigate before keeping it.

Then repeat, because the bottleneck has now moved.

### Phase G — Institutionalize

- Encode the SLO as a **threshold** in the test so CI fails on regression (k6 exits 99 on a threshold breach).
- Run **smoke** on every commit, **average-load** nightly, **soak** weekly, **breakpoint** quarterly.
- Compare like with like: k6's docs put it plainly — *"It's critical to compare test run results of the same test. Otherwise, you're comparing apples with oranges."* Run each configuration twice consecutively to filter flukes.
- Set the SLO from what users need, not from what you currently do. Google SRE Ch. 4: **"Don't pick a target based on current performance"** — that locks you into heroics.
- **Add a query-count budget per endpoint as a CI assertion.** This is the cheapest, highest-value regression gate in a DB-heavy service, and almost nobody has it (§5.1).

**Test types, and where each belongs in the cycle:**

```
smoke (CI, every commit — validates the SCRIPT, not the system)
  └─> average-load  ← BASELINE. re-run after every single change.
        └─> stress            (which resource saturates first, and how it degrades)
              └─> scalability sweep (N = 1,2,4,8,16,32 — contention or coherency?)
                    └─> spike       (cold caches, JIT warmup, autoscale lag, recovery)
                          └─> soak  (overnight: leaks, heap creep, history list growth,
                                     idle-timeout connection resets — see §6.6)
                                └─> breakpoint (quarterly: where is the wall?)
```

Two warnings on breakpoint tests, from k6's own docs: **disable autoscaling first** (otherwise "the elastic environment may grow as the test moves further, finding only the limit of your cloud account bill"), and only run them after the other types pass — otherwise you're finding a bug, not a limit.

**And one MySQL-specific reason the soak test matters more than you'd think:** the idle-timeout connection-reset bug (§6.6) is an *idle*-time bug. It gets *worse* at 3 a.m. and in staging, and it never reproduces in a spike test. Only a long soak with quiet periods finds it.

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
│         → client timeouts + retries turn a healthy closed system into an open one at
│           the worst moment: retries raise arrival rate → raise latency → more retries.
│           That's congestive collapse. (§6.7)
│
├── 0c. Is it ALL instances, or one?  (disaggregate p99 by pod first)
│         → one cold pod, one rebalancing node, one noisy neighbour skews the aggregate.
│           Cheapest possible cut, and people skip it.
│
├── 1. Is CPU throttling happening?  (container_cpu_cfs_throttled_*)
│         → YES: multi-hundred-ms stalls that look exactly like GC and appear in NO GC log.
│
├── 2. Is the GC log clean in the bad window?  (-Xlog:gc*,safepoint)
│         → NO: GC or a non-GC safepoint. Check allocation rate before switching collectors.
│
├── 3. Is the request even ON a worker thread yet?     ← THE BLIND SPOT
│         → ss -lnt 'sport = :8080'  →  Recv-Q non-zero means the accept queue is backing up
│         → nstat TcpExtListenOverflows  →  non-zero means you are DROPPING connections
│         → tomcat_threads_busy / config_max → 1.0, and connections_current → 8192
│           A request queued below the worker thread has NO thread, NO span, NO trace.
│           A profiler cannot see it. Only the client's latency and kernel counters can. (§6.2)
│
├── 4. Run async-profiler in WALL-CLOCK mode. Where is the thread parked?  (§6.5)
│   │
│   ├── StrictConnPool.lease / InstrumentedPool.acquire
│   │        → OUTBOUND HTTP POOL exhaustion. Check pool `pending` gauge. (§6.3)
│   │        → the downstream service's own latency will look perfectly healthy.
│   │
│   ├── HikariPool.getConnection / ConcurrentBag.borrow
│   │        → DB POOL problem, not a DB problem. (§6.4)
│   │        └── hikaricp_connections_pending > 0 sustained?
│   │            ├── usage timer HIGH → queries slow / transactions too wide.
│   │            │                      Enlarging the pool makes it WORSE.
│   │            └── usage timer LOW  → genuinely too few connections.
│   │                                   The ONLY case where enlarging is right.
│   │        └── pending ~0 but a few connections held for ages → LEAK.
│   │            Turn on leakDetectionThreshold.
│   │
│   ├── SocketInputStream.read / NioSocketImpl.read / SSLSocketImpl.readApplicationRecord
│   │        → genuinely waiting on the wire. The peer really is slow. Go to the DB tree
│   │          or to the downstream service's own dashboard.
│   │
│   ├── Dispatcher.promoteAndExecute  →  OkHttp maxRequestsPerHost throttling (default 5!)
│   ├── Application code on-CPU       →  CPU flame graph, then Amdahl before you optimize.
│   └── Monitor contention            →  asprof -e lock
│
└── 5. MySQL tree (in descending order of "this is usually the answer"):
    a. Queries per request  =  SUM(COUNT_STAR) ÷ number of requests
          → a small explainable integer? If a "list 20" endpoint issues 61 queries: N+1.
            Almost nobody computes this number. It is the most useful figure you have.
    b. Threads_running vs cores
          → ≈ cores          : fully utilized, at peak. Target.
          → 2–4 × cores      : queueing. Latency rising, throughput flat.
          → > ~4 × cores     : THRASHING. Throughput FALLS as you add load. Shrink the pool.
          → spiking to 50-100+ while throughput craters → lock convoy or one bad plan.
                               Go straight to (d).
    c. Wait-class histogram:  SELECT * FROM sys.wait_classes_global_by_latency;
          → wait/synch/*  = internal contention → YOUR POOL IS TOO BIG
                            (invisible unless you enabled wait/synch — Phase A)
          → wait/io/file/innodb/innodb_log_file = redo / sync_binlog bound
          → wait/lock/*   = app-level contention (hot rows, gap locks, FK checks)
          → wait/io/table = handler I/O; check max_latency for hidden row-lock waits
    d. Locks:  SELECT * FROM sys.innodb_lock_waits ORDER BY wait_age DESC;
          → follow the chain: the true root is the row whose blocking_state is RUNNING
          → and read the deadlock log (innodb_print_all_deadlocks) for a POPULATION,
            not the single anecdote SHOW ENGINE INNODB STATUS gives you
    e. Digest table ranked by SUM_TIMER_WAIT, then by rows_examined/rows_sent
          → SUM_NO_INDEX_USED = COUNT_STAR  → missing index, guaranteed
          → SUM_SELECT_FULL_JOIN > 0        → any non-zero is catastrophic
          → SUM_SORT_MERGE_PASSES > 0       → filesort spilled to disk
          → SUM_CREATED_TMP_DISK_TABLES     → temp table on disk
    f. EXPLAIN ANALYZE the top offenders — and multiply `actual time × loops`
          → for a query you can't reproduce: EXPLAIN FORMAT=TREE FOR CONNECTION <id>
            while the load test is running. This is the only way to catch a plan flip.
    g. History list length  (INNODB_METRICS.trx_rseg_history_len)
          → climbing and never draining = a long/idle transaction is blocking purge,
            and EVERY reader now walks longer version chains. Global degradation. (§5.8)
    h. Checkpoint age vs innodb_redo_log_capacity (default 100 MiB — far too small)
          → age > ~75% of capacity → aggressive flush, latency spikes
          → ⚠️ log_lsn_checkpoint_age is DISABLED by default and reads 0.
            Enable it first (§2 Phase A) and always select STATUS alongside COUNT.
```

**Two heuristics worth having in your head:**

1. **App p99 exploding + peer latency flat + peer CPU idle = the peer is fine.** It's your pool. This applies identically to MySQL and to a downstream HTTP service, and it is the single most misdiagnosed failure mode in JVM services.
2. **If the pool metrics are ambiguous, halve the pool in a load test and see what happens.** It's a fast, cheap probe of whether you're past the knee. Two caveats: read `pending` and `usage` first, because they usually answer it deterministically without perturbing anything; and don't ship a halved pool below the deadlock floor `Tn × (Cm − 1) + 1`, or below what an already-undersized pool needs — there, halving just converts latency into `connectionTimeout` exceptions, i.e. user-visible 500s.

---

## 4. The minimum viable toolchain

You do not need all of this. You need a load generator, metrics, one profiler, and `performance_schema`.

| Layer | Pick | Why |
|---|---|---|
| **Load generator** | **Grafana k6** (2.x) | Two reasons that actually matter for a beginner: **`dropped_iterations` is a first-class metric**, so offered-vs-achieved load is impossible to ignore — that's the concept people get wrong; and **thresholds → exit code 99** is a one-block CI gate. Secondary: not a JVM, so the generator's own GC can't contaminate client-side timings; and Prometheus remote-write puts load-test and service metrics on one dashboard. |
| Runner-up | **Gatling** (3.x; Java/Kotlin/Scala DSL, and now JS/TS) | A closer call than most write-ups admit. Gatling has had **open-model arrival-rate injection** for years and reports full percentile distributions — so it satisfies §1.2, this document's most load-bearing requirement, just as well as k6. Pick it *first* if your setup needs your domain code (complex auth minting, protobuf from your own schemas, JDBC fixtures). Honest trade: the generator is a JVM, so warm it and size its heap deliberately, and log *its* GC too. Note neither tool has built-in distributed injection in OSS; and k6's per-VU JS interpreter is comparatively CPU-expensive per iteration, so a k6 generator often saturates its cores at *lower* rps than Gatling's Netty pipeline. Check generator CPU either way. |
| Metrics | Micrometer + Actuator → Prometheus + Grafana, plus **mysqld_exporter** | |
| Tracing | OpenTelemetry Java agent | Auto-instruments JDBC/Hikari/Hibernate. **The N+1 is visually obvious in a waterfall** — 200 sibling spans with an identical statement. |
| Always-on | JFR (`default.jfc`) + JDK Mission Control | Start with JMC's **Automated Analysis** page: it reads a recording and writes prose. |
| On-demand profiler | **async-profiler** (4.5) | No safepoint bias, and `-e wall` is your off-CPU tool. §6.5 is the decoder ring. |
| **MySQL: tier 1** | **the `sys` schema** | Already installed (100 views, 48 routines) [verified 8.4.11]. Zero setup. `sys.session`, `sys.innodb_lock_waits`, `sys.wait_classes_global_by_latency`, `sys.statements_with_full_table_scans`, `sys.schema_unused_indexes`. **Highest payoff-per-effort of anything here, and most engineers don't know it exists.** |
| **MySQL: tier 1** | **slow log + `pt-query-digest`** (Percona Toolkit 3.7.x) | Read the **Profile** section first: it ranks by *total* time, which correctly surfaces the 2 ms query called 500,000 times over the 8-second query called twice. |
| MySQL: tier 2 | **`pt-stalk`** | Watches a condition and dumps a full diagnostic bundle when it trips. **Purpose-built for the intermittent stall you can never reproduce.** 5-minute setup, badly underused: `pt-stalk --function status --variable Threads_running --threshold 50 --cycles 2 --daemonize` |
| MySQL: tier 2 | **Percona PMM v3** | Query Analytics + InnoDB/OS dashboards on one timeline. The best investment if you'll load-test repeatedly — the closest MySQL has to hosted ASH. Free and open source. |
| Outbound HTTP | **Register the Micrometer pool binder yourself** | Spring Boot does **not** auto-register it, so by default you are flying blind on the pool most likely to be your bottleneck (§6.3). |

**Don't start with:** JMeter (last release Jan 2024; closed-loop by default; the GUI-with-listeners trap bottlenecks the *generator*). Locust (a third language for no gain in a JVM shop). `ab` (single-threaded, HTTP/1.0, keep-alive off by default — you'll be benchmarking `ab`). `mysqlslap` (no transactional mix, no think time, no key distribution, no percentiles — fine as a 30-second smoke test, useless for a decision). **`mysqltuner`** — and it's worth knowing *why*: it reasons from cumulative-since-boot counters (so on a server up 200 days its advice is dominated by ancient history), it recommends raising **per-session** buffers based on global ratios (the §5.12 multiplication trap — this has OOM'd real servers), its rules lag MySQL versions badly, and it has no idea what your queries are. The criticism is deserved.

**Add later, cheaply:** `vegeta` for 60-second single-endpoint sanity checks. Constant-rate by design with HdrHistogram output, so unlike `wrk` its percentiles survive saturation.

**On JMH:** it's the only correct way to microbenchmark on the JVM, and it is **rarely your first answer.** The cost that dominates your service is *queueing* — for a connection, a lock, a CPU slice — which is emergent from concurrency and load, and which a microbenchmark by construction does not have. **Load test and profile first; reach for JMH once a profile has already named a specific on-CPU frame.** When that happens it's usually JSON serialization of large payloads, entity→DTO mapping, a password KDF, or regex on a hot path.

**On plan visualizers:** there is **no MySQL equivalent of explain.depesz.com or pgMustard.** The Postgres tooling here is years ahead, and pretending otherwise wastes your time. MySQL Workbench's Visual Explain is the only first-party option — worth one session to build plan intuition, then leave. The practical MySQL workflow is text-based and that's fine: `EXPLAIN ANALYZE` → read bottom-up → **multiply `actual time × loops`** → find where estimate and actual diverge. Teach the multiplication and you've replaced 80% of what a visualizer would give you.

---

## 5. The MySQL findings you will actually get

Roughly in order of how often they turn out to be the answer. Each is *symptom in a load test → detection → fix*. Pool-related findings live in §6.

### 5.1 N+1 selects — still number one

**Symptom:** throughput scales inversely with collection size; latency dominated by *count* of queries, not per-query cost. DB CPU low, `Threads_running` low, app threads all parked in `SocketInputStream.read`. Total time ≈ N × RTT — so **N+1 looks fine on a laptop with a 0.05 ms loopback RTT and catastrophic at 0.5 ms in-AZ.** That's why it escapes local testing and appears in the load test.

**Detect — the best trick in this whole document:**

```sql
TRUNCATE performance_schema.events_statements_summary_by_digest;
-- run a known number of requests, e.g. 1000
SELECT SUM(COUNT_STAR) AS stmts, SUM(COUNT_STAR)/1000 AS stmts_per_request
FROM performance_schema.events_statements_summary_by_digest;
```

**A queries-per-request number is the single most useful figure in a JVM/DB load test, and almost nobody computes it.** Then find the offender: the digest whose `COUNT_STAR` is a suspicious multiple of your request count.

Also: `hibernate.generate_statistics=true` (test profile only), [datasource-proxy](https://github.com/jdbc-observations/datasource-proxy) or p6spy for per-request counts, and — the real fix for the future — **assert a query-count budget in an integration test so N+1 regressions fail CI.**

**Fix, best first:** **DTO projections** > `JOIN FETCH` / `@EntityGraph` > `@BatchSize` / `hibernate.default_batch_fetch_size` (turns 200 queries into 4 with one config line). Never `FetchType.EAGER`. And set **`spring.jpa.open-in-view=false`** — Spring Boot enables OSIV by default, which both hides N+1 from service-layer tests and holds a DB connection for the entire request including serialization.

> ⚠️ **A MySQL-specific trap with `@BatchSize`:** `eq_range_index_dive_limit` defaults to **200** [verified 8.4.11]. At ≤200 values in an `IN (...)` list the optimizer performs accurate **index dives**; at 201 it silently falls back to coarse index statistics and **the plan can flip**. A `@BatchSize(200)` and a `@BatchSize(256)` are not the same decision. Keep ORM-generated `IN` lists under 200, or set `eq_range_index_dive_limit=0` to force dives always.

### 5.2 Missing index — which in MySQL is also a *locking* bug

**Symptom:** DB CPU pegged; `rows_examined/rows_sent` in the hundreds or thousands; `SUM_NO_INDEX_USED = COUNT_STAR`; `type: ALL` with a huge `rows`.

**But here is the part that has no PostgreSQL analogue.** From [Locks Set by Different SQL Statements](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html): `UPDATE ... WHERE` and `DELETE ... WHERE` set *"an exclusive next-key lock on every record the search encounters."*

**"Encounters", not "matches."** So under the default `REPEATABLE READ`, a `DELETE FROM orders WHERE tenant_id=? AND status='X'` with no index on `(tenant_id, status)` locks a range that can be *the whole table*. **A missing index is not just a slow query in MySQL; it is a table-wide lock.** The first symptom you see may be deadlocks, not latency. The docs' own deadlock-avoidance list says it outright: *"Create indexes on columns used in `SELECT ... FOR UPDATE` and `UPDATE ... WHERE` statements."*

**The carve-out that bounds this, and it's worth knowing because it covers most OLTP writes:** the same doc sentence continues — *"However, only an index record lock is required for statements that lock rows using a unique index to search for a unique row."* So an `UPDATE ... WHERE id = ?` on the primary key takes a plain record lock and **no gap lock**. The danger is specifically in *non-unique* or *unindexed* predicates.

**Detect.** `EXPLAIN` first, then read it properly:

- **`possible_keys` non-empty but `key: NULL` is the loudest signal in EXPLAIN** — an index existed and was rejected. Cause is almost always statistics, a type/collation mismatch (§5.3), or low selectivity.
- `possible_keys: NULL` means the index isn't even *eligible* — the predicate isn't sargable.
- **Learn the `index` vs `Using index` distinction.** `type: index` (in the **type** column) means "scanned the whole index" and is **bad**. `Using index` (in the **Extra** column) means "covering index, never touched row data" and is **good**. They frequently appear together.
- **`Using where` with low `filtered` and high `rows`** is the canonical "fetched 50,000 rows to keep 5,000" signature.
- `Using join buffer (hash join)` where you expected `eq_ref`/`ref` means no index was usable on the inner table.

**Fix:** composite index in equality-then-range order (`WHERE tenant_id=? AND status=? ORDER BY created_at DESC` wants `(tenant_id, status, created_at)`). Covering indexes pay off **more** on MySQL than on a heap-based engine, because a secondary-index lookup is a two-step (secondary → PK → clustered index); adding the one column that avoids the clustered probe is often a bigger win than expected. Find dead indexes with `sys.schema_unused_indexes` — but only *after* a representative full test.

### 5.3 Silent index loss from type conversion — the MySQL footgun that bites JVM services

This is the finding most specific to your stack, and it is worth reading carefully because **the commonly-repeated version of it is wrong.**

**What is NOT silent:** joining `utf8mb4_general_ci` to `utf8mb4_0900_ai_ci` raises `ERROR 1267 (HY000): Illegal mix of collations` [verified 8.4.11]. Both sides are IMPLICIT coercibility, so MySQL refuses rather than degrading. Your app throws and you find it immediately. Bad, but loud.

**What IS silent, verified by testing on 8.4.11:**

**(a) A string column compared to a number.** This is the one that actually bites. Verbatim from [Type Conversion](https://dev.mysql.com/doc/refman/8.4/en/type-conversion.html):

> "For comparisons of a string column with a number, MySQL cannot use an index on the column to look up the value quickly. If `str_col` is an indexed string column, the index cannot be used when performing the lookup in the following statement: `SELECT * FROM tbl_name WHERE str_col=1;` The reason for this is that there are many different strings that may convert to the value 1, such as '1', ' 1', or '1a'."

Measured on a 50,000-row table:

```sql
EXPLAIN SELECT * FROM t.n WHERE k = 500;    -- k is VARCHAR
-- type=index, key=k, rows=50323, filtered=10.00   ← SILENT full index scan
EXPLAIN SELECT * FROM t.n WHERE k = '500';
-- type=ref,   key=k, rows=1, filtered=100.00      ← GOOD
```

**The JVM trigger is your ORM's parameter binding.** A `VARCHAR` column (external ID, phone, postcode, account number, SKU) mapped to a `Long` or `Integer` field makes Hibernate emit `setLong()`, which produces exactly this. No error, no warning — just a full scan, plus (under `REPEATABLE READ`, per §5.2) a table-wide lock footprint if it's an `UPDATE`. And it's a **correctness** bug too: the docs' own examples include `SELECT 0 = 'x6'` returning **1**.

**Audit every `VARCHAR` id/code column your entities touch.**

**(b) Cross-*charset* joins — silent, and the optimizer hides it until it doesn't.** Joining `utf8mb4` to `latin1` produces no error. MySQL reorders the join so the `latin1` side drives and the `utf8mb4` index is usable, and it looks fine. Force the other order with `STRAIGHT_JOIN` and you get `Using join buffer (hash join)` — the index is unusable for lookup. **The loss is real; the optimizer was papering over it by constraining join order.** It works until a plan change forces the other order, and then it falls off a cliff.

Percona's measurement of the same mechanism (utf8 joined to latin1): `key_len` 6 vs 18, runtime **4.33 s → 3.12 s** after aligning charsets.

**Why this is endemic in JVM shops:** tables created across a 5.7→8.0 migration mix `utf8mb3`/`latin1` with `utf8mb4`, while Hibernate's auto-DDL creates *new* tables with the server default (`utf8mb4_0900_ai_ci`). Join across the boundary and the index quietly stops being used.

**(c) An explicit `COLLATE` in a predicate** — silent. On a single-table predicate it degrades to `type: index` (a full index scan). **On a join it's catastrophic:** `type: ALL` with `Range checked for each record` on the inner table of a nested loop — i.e. 50,000 × 50,000.

**(d) A function on the indexed column** — `WHERE UPPER(k) = ?` gives **`possible_keys: NULL`**: not even eligible. ⚠️ Note the optimizer may still report `type: index, key: k` for a covering scan, so **`possible_keys` is the column to read here**, not `key`. Fix with a generated column plus an index, or a functional index.

**Detect:**

```sql
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA NOT IN ('mysql','sys','performance_schema','information_schema')
  AND COLLATION_NAME IS NOT NULL
  AND COLLATION_NAME <> @@collation_server
ORDER BY 1,2,3;
```

Then look for `convert(...)` or any function wrapping a column in `EXPLAIN FORMAT=JSON`, and for a `key_len` smaller than you expect.

**Fix:** align charset *and* collation on join columns; make the Java type match the SQL type; and take Vadim Tkachenko's advice — *"Using a string column to join tables is rarely a good idea in general."*

### 5.4 No batching — and MySQL makes this harder than Postgres

**Symptom:** an endpoint inserting 500 rows takes 500 × RTT. The DB is nearly idle; the network is the bottleneck. `Com_insert` equals your row count rather than your batch count.

**Two MySQL-specific facts combine into a genuine dilemma:**

1. **`rewriteBatchedStatements` defaults to `false`** in Connector/J, and it is the single biggest available win. For `INSERT`/`REPLACE` it collapses a batch into one multi-`VALUES` statement — one round trip, one parse. Vlad Mihalcea's measurement: 5,000 records at batch size 100 went from **55 batches to 441 batches in 60 s (≈8× throughput, ~10× lower per-batch latency)**.
   > ⚠️ **`UPDATE` rewriting is categorically weaker** and widely misreported. Verified against `ClientPreparedStatement.java`: non-`INSERT` batches become a **multi-query** (`UPDATE ...; UPDATE ...;`), which saves round trips but **not** parses, and only triggers when the batch has **more than 3** statements. Expect a modest gain for `UPDATE`, not an order of magnitude. Multi-query UPDATE batches also can't be server-prepared, so the driver silently falls back to client-side emulation.
2. **MySQL has no `SEQUENCE` object.** Hibernate's `MySQLDialect` states it plainly: *"No support for sequences."* And `GenerationType.IDENTITY` (AUTO_INCREMENT) **disables JDBC insert batching entirely**, because Hibernate needs each generated key back at `persist()` time.

So the batching-friendly generator doesn't exist, and the only native generator kills batching. Options, honestly:

- **`BIGINT IDENTITY`, accept no insert batching.** The right default for most tables: 8-byte PK, monotonically increasing, perfect B-tree insert locality, no AUTO-INC table lock (mode 2 is the 8.4 default). For request-scoped work inserting 1–5 rows, batching was worth nothing anyway. **Don't trade PK quality for batching you don't need.**
- **`TABLE` generator — don't.** It turns ID generation into a row-level write hotspot with its own transaction, serialising all inserts on one row.
- **An assigned, time-sortable ID when you genuinely need batching.** Assign in the JVM → no round trip → inserts batch normally. **Never UUIDv4, never `CHAR(36)`.** UUIDv7 or ULID stored as **`BINARY(16)`**, or a TSID as `BIGINT` (8 bytes — Vlad's preference, and the 8-vs-16 difference compounds through every secondary index). Hibernate 7.2+ ships `UuidVersion7Strategy`; on 6.x, `@UuidGenerator(style = TIME)` is *not* interoperable UUIDv7.
- **Keep `IDENTITY` and bypass Hibernate for bulk paths** — a `StatelessSession` with a `NoOpGenerator`. Clean `BIGINT` PKs for the OLTP path, batching complexity confined to the importer.

**Working config:**

```properties
spring.jpa.properties.hibernate.jdbc.batch_size=50
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true
spring.jpa.properties.hibernate.jdbc.batch_versioned_data=true
spring.datasource.hikari.data-source-properties.rewriteBatchedStatements=true
```

`hibernate.jdbc.batch_size` **defaults to 0 — batching is off until you set it.** And `order_inserts`/`order_updates` do double duty: they group statements so batches actually form, **and** they impose consistent PK ordering, which is deadlock-avoidance rule #3 from the MySQL docs. They are a locking fix as much as a throughput fix.

> ⚠️ **The combination to test explicitly:** `rewriteBatchedStatements=true` + `batch_versioned_data=true` + `@Version`. Rewriting changes update-count semantics, and `batch_versioned_data` relies on those counts to detect optimistic-lock failures. A silently-missed optimistic lock failure is a data-corruption bug, not a performance bug.

**And the most common false-confidence finding in a MySQL/Hibernate load test:** batching fully configured, `IDENTITY` in use, and no batching happening at all.

### 5.5 Connector/J uses *client-side* prepared statements by default

`useServerPrepStmts` defaults to **`false`** — unlike pgjdbc. This surprises almost everyone, and it changes what you should measure.

What client-side means concretely: `prepareStatement(sql)` never talks to the server. The driver interpolates bind values into the SQL string and sends a plain `COM_QUERY`. Consequences:

- **The server parses and optimizes every single execution.** There's no server-side handle, so no server-side caching is engaged. (MySQL has no plan cache like Oracle's shared pool, and the query cache was removed in 8.0.)
- `cachePrepStmts=true` with `useServerPrepStmts=false` caches only the *client-side parse artefact* — it saves **JVM CPU, not database CPU**.

**Symptom when this is your bottleneck:** high `Com_query`, near-zero `Com_stmt_execute`, and server CPU dominated by parse/optimize, with digests showing high `COUNT_STAR` and low `SUM_ROWS_EXAMINED` — lots of cheap queries that are expensive only because they're re-planned.

**Two "recommended settings" blocks exist and they disagree.** The [HikariCP wiki's MySQL block](https://github.com/brettwooldridge/HikariCP/wiki/MySQL-Configuration) sets `useServerPrepStmts=true`; Oracle's own `maxPerformance-8-0` bundle shipped inside the driver jar **does not** — and neither does Vlad Mihalcea, who notes the server-side gains on MySQL are "not as significant as with other database systems."

**My read:** start at `useServerPrepStmts=false` + `cachePrepStmts=true` + raised cache sizes. It's the safe default, it interacts correctly with `rewriteBatchedStatements`, and it doesn't consume `max_prepared_stmt_count`.

> ⚠️ **Do the arithmetic before flipping `useServerPrepStmts=true`.** Server-side handles count against `max_prepared_stmt_count`, whose default is **16382** [verified 8.4.11], and the consumption is `prepStmtCacheSize × maximumPoolSize × instances`. `250 × 20 × 8 = 40,000` → you *will* hit the ceiling, and it will present as intermittent `ER_MAX_PREPARED_STMT_COUNT_REACHED` only after the pool has fully warmed.

### 5.6 Unbounded result sets — an OOM, not a slow query

**This fails differently on MySQL than on Postgres.** Connector/J's default is *"ResultSets are completely retrieved and stored in memory."* So a repository method with no `Pageable` doesn't produce a slow query — it produces heap pressure, long GC pauses, and eventually `OutOfMemoryError`, **while the database looks perfectly healthy.** That sends everyone hunting in the wrong place.

**Detect:** `SUM_ROWS_SENT` per digest wildly larger than any page size; a heap dump retaining `com.mysql.cj.protocol.a.result.*` / `ResultSetImpl`.

**Fix.** Know the three fetch modes and pick deliberately:

1. **All-at-once (default).** Correct for a bounded page. Enforce a hard server-side `LIMIT`.
2. **Cursor-based** (`useCursorFetch=true` + a positive fetch size). **The sharp edge nobody mentions:** server-side cursors *"are materialized into an internal temporary table"* — so this bounds **client** memory by spending **server** memory and disk. It is *not* streaming, and the docs warn *"for a large result set, retrieving its rows through a cursor might be slow."*
3. **Row-by-row streaming** (`setFetchSize(Integer.MIN_VALUE)` on a forward-only, read-only statement). Genuinely streams — but **the connection is unusable until you finish reading it**, so no lazy-loading, no secondary query inside the row loop, no Hibernate association traversal while streaming. And locks are held until the statement completes.

For a long-running report, use none of these: use keyset pagination in separate short transactions.

### 5.7 OFFSET pagination — with a MySQL twist that isn't on the canonical page

The general argument is Markus Winand's: `LIMIT 20 OFFSET 100000` makes the database produce and discard 100,020 rows, and it isn't even stable — concurrent inserts shift rows between pages. Symptom in a load test: latency degrades *as the test progresses*, because later pages are slower.

Keyset (seek) pagination is the fix. **But the elegant tuple form does not use the full index in MySQL.** From [Row Constructor Expression Optimization](https://dev.mysql.com/doc/refman/8.4/en/row-constructor-optimization.html), with `PRIMARY KEY (c1, c2, c3)`:

```sql
-- Elegant, but only uses c1   (key_len=4)
WHERE c1 = 1 AND (c2, c3) > (1, 1)

-- Ugly, but uses all three    (key_len=12)
WHERE c1 = 1 AND (c2 > 1 OR (c2 = 1 AND c3 > 1))
```

The manual explicitly recommends the expanded `OR` rewrite. **So on MySQL, write the ugly form.** If you use Blaze-Persistence or Spring Data's keyset support, check the SQL it emits — a tuple comparison silently loses most of your index. (This is also a quiet argument for single-column time-sortable PKs: keyset pagination becomes a one-column comparison and the whole issue disappears.)

Also: **`SQL_CALC_FOUND_ROWS` is deprecated**, forces full materialization, and permanently disables ProxySQL multiplexing on that connection. Don't.

### 5.8 Long transactions, the history list, and purge lag

**This is MySQL's version of PostgreSQL dead-tuple bloat, and it's the single most common way a JVM service destroys a MySQL server.**

**Mechanism.** InnoDB is MVCC. Under the default `REPEATABLE READ`, a transaction's read view is created at its **first read** and held until commit. One idle-in-transaction connection therefore pins the entire undo history from that moment. The undo log grows, the **history list length** grows, and — critically — *every* subsequent read of a hot row must walk a longer version chain. **Throughput degrades globally, not just for the offending session.** The docs name your exact failure mode: *"SELECT query after disabling autocommit without issuing an explicit COMMIT or ROLLBACK."* That is the classic Spring bug: a `@Transactional` method that makes an HTTP call, or open-session-in-view holding a transaction across view rendering.

It's arguably more punishing than the Postgres analogue in one respect: there's no autovacuum-style backlog metric that ops teams already watch, so it goes unnoticed until reads mysteriously slow down.

> ⚠️ **`SHOW GLOBAL STATUS LIKE 'Innodb_history_list_length'` returns ZERO ROWS on upstream 8.4.11** [verified]. There is no such status variable, despite what many blog posts say. Use:
> ```sql
> SELECT NAME, COUNT, STATUS FROM information_schema.INNODB_METRICS
>  WHERE NAME = 'trx_rseg_history_len';          -- enabled by default ✓
>
> -- Checkpoint age also has no status variable — and unlike the above it is
> -- DISABLED by default, so it returns 0 until you enable it (§2 Phase A):
> SELECT Variable_name, Variable_value, Enabled FROM sys.metrics
>  WHERE Variable_name IN ('trx_rseg_history_len','log_lsn_checkpoint_age');
> ```
> **Always select `STATUS`/`Enabled`.** A disabled metric reads as a healthy zero.

**Find the culprit:**

```sql
SELECT trx.trx_id, trx.trx_state, trx.trx_mysql_thread_id AS conn_id,
       TIMESTAMPDIFF(SECOND, trx.trx_started, NOW()) AS trx_age_s,
       trx.trx_rows_locked, trx.trx_rows_modified, trx.trx_isolation_level,
       th.PROCESSLIST_COMMAND AS cmd, th.PROCESSLIST_TIME AS cmd_time_s,
       COALESCE(trx.trx_query, '<<IDLE IN TRANSACTION>>') AS query,
       CONCAT('KILL ', trx.trx_mysql_thread_id) AS remedy
FROM information_schema.INNODB_TRX trx
JOIN performance_schema.threads th ON th.PROCESSLIST_ID = trx.trx_mysql_thread_id
ORDER BY trx_age_s DESC;
```

**The idle-in-transaction signature is `trx_state = RUNNING` with `cmd = Sleep`.** The transaction is open; the connection is doing nothing. `trx_age_s ≫ cmd_time_s` is the same smell.

**Bad readings:** `trx_age_s > 60` in an OLTP app is a bug in your pool or a missing `finally`. `trx_rseg_history_len` climbing monotonically and never draining means purge can't keep up. Above ~1,000,000 is an emergency, and the tablespace growth will not shrink.

**Fix:** never make an HTTP/gRPC/Kafka call inside `@Transactional`. Compute before you open the transaction. `spring.jpa.open-in-view=false`. Chunk batch jobs. Leave Hikari's `autoCommit` at its default (`true`) unless you truly need otherwise. And consider `READ COMMITTED` (§5.9), which refreshes the read view **per statement** and so hugely reduces this class of damage.

### 5.9 Gap locks, and why Postgres-safe code deadlocks on MySQL

MySQL defaults to `REPEATABLE READ` **with gap and next-key locks**. Postgres defaults to `READ COMMITTED` and takes row locks only. This is the single largest behavioural difference between the two for an application developer, and it produces deadlocks in code that is fine on Postgres.

**A gap lock** is *"a lock on a gap between index records, or a lock on the gap before the first or after the last index record."* A **next-key lock** is a record lock plus a gap lock on the gap before it. `UPDATE`/`DELETE` take a next-key lock on **every record the search encounters** — hence §5.2.

**Canonical failure 1 — `SELECT ... FOR UPDATE` on a non-existent row blocks an unrelated INSERT.** Straight from the docs:

```sql
INSERT INTO child (id) VALUES (90),(102);
-- Client A
START TRANSACTION;
SELECT * FROM child WHERE id > 100 FOR UPDATE;   -- returns 102, locks (102, +inf)
-- Client B
START TRANSACTION;
INSERT INTO child (id) VALUES (101);             -- BLOCKS
```

`SHOW ENGINE INNODB STATUS` shows `lock_mode X locks gap before rec insert intention waiting`.

**This is *the* upsert anti-pattern.** "`SELECT ... FOR UPDATE`; if empty then `INSERT`" is safe-ish on Postgres and a deadlock factory on MySQL, because the *failed* lookup still takes a gap lock, and two sessions doing it for two *different* keys in the same gap deadlock as soon as each tries to insert. **Use `INSERT ... ON DUPLICATE KEY UPDATE` or `INSERT IGNORE` instead of read-then-write.**

**Canonical failure 2 — duplicate-key insert takes a *shared* lock, and rollback triggers a deadlock.** Verbatim: *"If a duplicate-key error occurs, a shared lock on the duplicate index record is set. This use of a shared lock can result in deadlock should there be multiple sessions trying to insert the same row **if another session already has an exclusive lock**."* That final clause is the precondition for the whole scenario. Three sessions inserting the same PK: session 1 holds X, sessions 2 and 3 get dup-key errors and acquire S locks, session 1 rolls back — and 2 and 3 both hold S and both want X. **Deadlock.** This is why a naive "insert and catch `DataIntegrityViolationException`" retry loop produces deadlocks rather than clean constraint violations under concurrency.

Note the asymmetry: `INSERT ... ON DUPLICATE KEY UPDATE` takes an **exclusive** lock instead — but on a duplicate **unique secondary key** it takes an exclusive **next-key** lock. So deduping on a unique `email`/`slug` column is materially more contended than on the PK.

**Foreign keys make it worse, and READ COMMITTED does not fix that part.** FK checks *"set shared record-level locks on the records that [they look] at"* — so **every `INSERT` into a child table takes an S lock on the parent row.** A high-write child table with an FK to a low-cardinality parent (`tenant`, `currency`, `status`) makes that parent row a contention hotspot shared by every writer, and any transaction that *updates* the parent queues behind all of them. This is one of the most common "why is this deadlocking, we only ever insert" findings in a JVM app — especially where an ORM bumps a `@Version` on the parent alongside child inserts. And under `READ COMMITTED`, gap locking *"is used only for foreign-key constraint checking and duplicate-key checking"* — so FK-heavy schemas keep some gap locks regardless.

**Diagnosis. Turn on the log — this is the highest-value one-line change for load-testing a JVM app against MySQL:**

```sql
SET GLOBAL innodb_print_all_deadlocks = ON;   -- default OFF
```

`SHOW ENGINE INNODB STATUS` shows only the **latest** deadlock, in a single-slot buffer that doesn't survive restart. It is fundamentally unsuited to diagnosing a deadlock storm. The log gives you a *population*.

Reading lock modes in the output:

| Mode string | Meaning |
|---|---|
| `lock_mode X locks rec but not gap` | plain record lock — a unique-index point lookup. Good. |
| `lock_mode X` (no qualifier) | **next-key lock** (record + preceding gap) |
| `lock_mode X locks gap before rec` | pure gap lock |
| `lock_mode X locks gap before rec insert intention waiting` | an INSERT blocked by someone's gap lock — **the failure-1 signature** |
| `lock mode S` on an insert path | the duplicate-key shared lock — **the failure-2 signature** |

Also note the victim rule, verbatim: *"InnoDB tries to pick small transactions to roll back, where the size of a transaction is determined by the number of rows inserted, updated, or deleted."* Read that second clause carefully — **a read-only transaction that has only taken `SELECT ... FOR UPDATE` locks has modified zero rows, so it is always the smallest, so it is always the victim.** Your small, correct transaction gets sacrificed to preserve a big batch job. Two implications: **all** application code must treat deadlock (error 1213 / SQLState 40001 → Spring's `CannotAcquireLockException`) as retryable; and mixing batch jobs with OLTP traffic on the same tables makes your OLTP path the loser by construction.

**The case for `READ COMMITTED`.** Three documented wins:

1. **No gap locks** for searches and index scans → both canonical failures largely evaporate.
2. **Record locks for non-matching rows are released after the `WHERE` is evaluated** — arguably bigger than #1. It converts "missing index = table-wide lock" into "missing index = slow query."
3. **Semi-consistent reads for `UPDATE`** → an `UPDATE` can skip rows already locked by another transaction that wouldn't have matched anyway.

Plus §5.8: read views refresh per statement, so an idle transaction pins far less undo history.

Costs: phantom rows become possible, and two `SELECT`s in one transaction can disagree. For a request-scoped web transaction that reads what it needs once, usually a non-issue; for a multi-step invariant check, it isn't.

**The historical objection is obsolete.** RC requires row-based binary logging — and `binlog_format=ROW` has been the default since 8.0 and the variable is now deprecated in favour of ROW-only. Just confirm nobody set `STATEMENT`.

Peter Zaitsev's position: *"good practice is to use READ COMMITTED isolation mode as default and change to REPEATABLE READ for those applications or transactions which require it."*

**But include the counter-argument**, from Percona's own blog: Marco Tusa's worked phantom-read example (a `SELECT` returns 21 customers, the follow-up `UPDATE` hits **31**, costing ~$133 more than intended) ranks **explicit `SELECT ... FOR UPDATE` above switching to RC**, because locking prevents the anomaly outright whereas *"READ COMMITTED... requires additional application logic to handle race conditions."*

**So it's a decision, not a tuning knob.** For a new OLTP service on ROW binlog, default to RC. For an existing service, change it per-session first and load-test both.

```ini
transaction_isolation = READ-COMMITTED       # server-side, so every client agrees
```
```properties
spring.jpa.properties.hibernate.connection.isolation=2   # TRANSACTION_READ_COMMITTED
```

> ⚠️ Don't set it via `sessionVariables=` if you also set `useLocalSessionState=true` — that's exactly the "app sets session state outside Connection methods" case Oracle warns about.

**And the queue-table pattern.** The worst pattern in Spring Boot workers is `SELECT ... FOR UPDATE LIMIT 1` with all N workers serialising on the head row. The fix:

```sql
START TRANSACTION;
SELECT id FROM job WHERE status='READY' ORDER BY id LIMIT 10 FOR UPDATE SKIP LOCKED;
UPDATE job SET status='RUNNING', worker=? WHERE id IN (...);
COMMIT;
```

Requires an index making `WHERE status ORDER BY id` a range scan, and a short transaction. **`SKIP LOCKED` + `READ COMMITTED` is the combination you want** — under `REPEATABLE READ` that same query takes gap locks on the scanned range, reintroducing the contention `SKIP LOCKED` was meant to remove.

### 5.10 `innodb_lock_wait_timeout` is 50 seconds

[verified 8.4.11]. That is far too long for a web request, and the reason is the *ordering* of your timeouts, not the number itself.

A lock wait is invisible to every other timeout you have — it isn't a slow query the optimizer knows about, it's a thread parked in the server. So one hot-row contention event does this:

- 50 s × N parked requests → **your HikariCP pool is fully checked out** → `connectionTimeout` starts failing *unrelated* endpoints → cascading failure well beyond the contended table.
- Your HTTP client and gateway time out first, so **the user is gone but the transaction still holds locks** — you've converted a contention blip into amplified load.
- It's longer than Hikari's 30 s default `connectionTimeout`, so the pool queue drains into errors before a single lock wait resolves. The timeouts are ordered wrong.

**Fix per session, not globally**, and keep a longer value on a separate DataSource for batch jobs:

```properties
jdbc:mysql://host/db?sessionVariables=innodb_lock_wait_timeout=3
```

**The invariant:** `innodb_lock_wait_timeout` < your HTTP request budget, and comfortably < `socketTimeout`.

**And a related default that surprises people:** `innodb_rollback_on_timeout` is **OFF** [verified 8.4.11], meaning a lock-wait timeout rolls back only the **last statement**, not the transaction. So a caught `ER_LOCK_WAIT_TIMEOUT` leaves you inside a still-open transaction holding whatever locks it had already acquired. If your error handler doesn't explicitly roll back, you have just created a §5.8 long transaction out of a timeout.

**On disabling deadlock detection:** this is real advice, but it's a two-variable change or nothing. The docs note detection *"can cause a slowdown when numerous threads wait for the same lock"* — it's a wait-for-graph search, superlinear in queue depth. But with `innodb_deadlock_detect=OFF`, a real deadlock is resolved by **waiting out `innodb_lock_wait_timeout`**. At 50 s that's catastrophic. Only sane with the timeout at 1–2 s, and only for an extreme, well-characterised hot-row workload.

### 5.11 `COUNT(*)` has no fast path in InnoDB

Verbatim: *"InnoDB does not keep an internal count of rows in a table because concurrent transactions might 'see' different numbers of rows at the same time."* It is an **O(rows) index scan, always** — MVCC makes a stored count impossible. And the caveats stack against you: the "optimized" path applies to **single-threaded** workloads with **no `WHERE`** — i.e. precisely not your paginated, filtered admin screen.

Also, kill this code-review argument with the doc quote: *"InnoDB handles `SELECT COUNT(*)` and `SELECT COUNT(1)` operations in the same way. There is no performance difference."*

**Alternatives, ranked:** (1) **don't count** — "next page" UX, or "showing 1–20 of many"; (2) approximate via `SHOW TABLE STATUS` / `information_schema.TABLES.TABLE_ROWS` (doc-endorsed, whole-table only, can be well off); (3) a counter table — doc-endorsed *with* its own warning that it *"may not scale well… when thousands of concurrent transactions are initiating updates to the same counter table"*, and per §5.9 that single hot row is a deadlock magnet, so shard it across N rows or update it asynchronously; (4) a bounded count: `SELECT COUNT(*) FROM (SELECT 1 FROM t WHERE ... LIMIT 1001) x` → "1000+".

### 5.12 Server config: the four defaults that will dominate your first load test

All [verified 8.4.11] on a 2-core / 7 GiB box.

| Variable | Default | Why it matters |
|---|---|---|
| **`innodb_buffer_pool_size`** | **134217728 (128 MiB)** | ⚠️ **NOT auto-sized.** Auto-sizing happens only with `innodb_dedicated_server=ON`, which is **OFF** by default. **A load test on the 128 MiB default measures your disk, not your database.** Set 50–75% of RAM, or turn on `innodb_dedicated_server`. |
| **`innodb_redo_log_capacity`** | **104857600 (100 MiB)** | Far too small for a write-heavy service — **the #1 under-set variable in 8.4.** Symptom: write stalls, a latency sawtooth, checkpoint age at ~75% of capacity, `Innodb_log_waits > 0`. Raise to 2–16 GiB. Dynamic, no restart. (On the deprecated `innodb_log_file_size`: **`innodb_redo_log_capacity` wins when both are set** — the server logs `MY-013869 "Ignored deprecated configuration parameter innodb_log_file_size. Used innodb_redo_log_capacity instead."` If only the old one is set, it's used to *compute* capacity, with warning `MY-013907`. Either way it's logged, not silent. So a stale `innodb_log_file_size` in your my.cnf is not what's blocking you — set the new variable and it takes precedence.) |
| **`sort_buffer_size` / `join_buffer_size`** | **262144 (256 KiB) each** | The **per-session multiplication trap** — the same shape as Postgres's `work_mem`. These are allocated **per session, per operation**; a 4-table join with no usable indexes allocates *three* join buffers simultaneously in one session. Set `join_buffer_size=256M` "to make joins fast" and, at the default `max_connections=151`, you have provisioned **~38 GB** of potential allocation from one config line if each session buffers one join — and ~113 GB if they buffer three. Either way it's memory that competes with your buffer pool. **This is the most common way people OOM a MySQL server while trying to speed it up.** Raise per-statement instead: `SELECT /*+ SET_VAR(sort_buffer_size=8M) */ ...`. And a non-zero `join_buffer_size` requirement is a **missing index**, not a memory problem. |
| **`tmp_table_size`** | **16777216 (16 MiB)** | Governs in-memory internal temp tables. ⚠️ **The widely-repeated "effective limit is `MIN(tmp_table_size, max_heap_table_size)`" rule is the MEMORY engine's, and MEMORY is not the default.** Under `internal_tmp_mem_storage_engine=TempTable` (the 8.4 default), **`tmp_table_size` alone governs** and `max_heap_table_size` is irrelevant to internal temp tables — verified by sweeping each independently. So raising `tmp_table_size` on its own *does* work. `max_heap_table_size` applies to user-created `ENGINE=MEMORY` tables, and to internal ones only if you switch the engine back to MEMORY. There is also a **server-wide** `temptable_max_ram` cap, so one greedy query can push everyone else's temp tables to disk. |

**And two 8.4 changes that invalidate most pre-2024 tuning guides:** `innodb_adaptive_hash_index` went **ON → OFF** (its global latch is a contention point at high concurrency) and `innodb_io_capacity` went **200 → 10000**. Percona says the upgrade risk directly: *"an in-place upgrade that blindly reuses an 8.0-era my.cnf may miss out on these improvements or cause unexpected performance behaviors."* **Audit your config against the new defaults and delete every line that just restates an old one.**

Other things worth knowing: `innodb_thread_concurrency` should stay at **0** (a legacy 5.x throttle). `max_parallel...` — not a thing in MySQL, which is a simplification versus Postgres. `lock_wait_timeout` (the **metadata** lock timeout, distinct from `innodb_lock_wait_timeout`) defaults to **31536000 seconds — 365 days**; lower it before running migrations under load. And `information_schema_stats_expiry` defaults to **86400** — `I_S.TABLES.TABLE_ROWS` is cached for a full day, which surprises everyone; set it to 0 for live reads.

### 5.13 Temp tables and filesorts spilling to disk

**Detection is subtle in MySQL, so spell it out.** `EXPLAIN` says `Using filesort` but never tells you whether it *spilled*. In order of preference:

1. **`SUM_SORT_MERGE_PASSES` per digest** (or per statement via `log_slow_extra`). **Non-zero = it spilled.** This is the definitive signal.
2. Global `Sort_merge_passes` delta over the window.
3. Percona Server's `Filesort_on_disk` / `Merge_passes` slow-log flags.

> ⚠️ **A caveat on `Created_tmp_disk_tables`, correctly scoped.** The manual warns: *"Due to a known limitation, `Created_tmp_disk_tables` does not count on-disk temporary tables created in memory-mapped files (the default TempTable overflow mechanism)."* **But at 8.4 defaults this cannot bite**, because `temptable_max_mmap = 0` — mmap overflow is *disabled*, and the counter is accurate (verified: it correctly counted spills at stock settings, and no under-reporting case could be constructed). The manual page contradicts itself by calling mmap "the default overflow mechanism" while documenting the variable's default as 0. **So: trust the counter unless you have set `temptable_max_mmap > 0`** — and prefer `SUM_CREATED_TMP_DISK_TABLES` per digest anyway, because it attributes the spill to a query.

**What forces temp tables to disk regardless of size:** for `UNION`/`UNION ALL`, any string column whose maximum length exceeds **512** bytes in the select list.

> ⚠️ **The `BLOB`/`TEXT` rule you may have read is obsolete.** It was true of the MEMORY engine. The manual is explicit for 8.4: *"The `TempTable` storage engine, which is the default storage engine for in-memory internal temporary tables in MySQL 8.4, supports binary large object types."* Verified: `GROUP BY` on a `TEXT` column with a generous `tmp_table_size` produced **zero** disk temp tables. If you've inherited advice to strip `TEXT` columns from grouped queries *for temp-table reasons*, that reason is gone — but read on, because there's a better reason.

That connects to a related finding: on the default **DYNAMIC** row format, a long `TEXT` lives on overflow pages with only a **20-byte pointer** in the clustered record. So **`SELECT *` on a table with a big `TEXT` column costs an extra random read per row** even when your code never reads that field — and it washes your buffer pool. JPA entities map every column by default, so `findAll()` *is* `SELECT *`. And `FetchType.LAZY` on a basic/`@Lob` attribute is **silently ignored without bytecode enhancement** — one of the most under-known Hibernate facts.

**Fix order:** index the `GROUP BY`/`ORDER BY` so MySQL streams in index order (`Using index` instead of `Using temporary; Using filesort`); make `ORDER BY` match `GROUP BY`; **stop selecting `TEXT`/`BLOB` columns you don't use** — not for temp-table reasons (see above) but for the off-page random-read and buffer-pool-eviction reasons, which are real and are the strongest argument for DTO projections; reduce the intermediate set before aggregating; reduce the row *width* being sorted (MySQL may pack whole rows into the sort buffer); and raise `tmp_table_size` / `sort_buffer_size` **per statement** only as a stopgap.

### 5.14 Container CPU throttling — the biggest 2026 JVM footgun

Unchanged from any database: multi-hundred-millisecond p99 spikes that look *exactly* like GC pauses and appear nowhere in the GC log.

`Runtime.availableProcessors()` returns ≈ `ceil(cpu.max quota / period)`, and that one integer sizes GC worker threads, `ForkJoinPool.commonPool` parallelism (**= n−1, so a 1-CPU limit gives you parallelism 1, silently serializing every parallel stream and `supplyAsync`**), the virtual-thread carrier pool, and Netty event loops. (Tomcat's `maxThreads` is *not* in this list — it's 200 regardless of CPU count, which is its own separate problem.) Exceeding the quota within any 100 ms CFS period parks **all** your threads until the next period. A JVM running 8 GC threads against a 1-core quota throttles itself into a stall during every young GC.

Also: since 11.0.17+/17.0.5+/18.0.2+ the JVM **ignores `cpu.shares`** and uses quota only — so a pod with `requests.cpu` but **no `limits.cpu`** sees the *whole node's* CPU count and builds absurd thread pools. This is the most common JVM-in-Kubernetes misconfiguration going.

Check `/sys/fs/cgroup/cpu.stat` (`nr_throttled`, `throttled_usec`). Give ≥2 vCPU. Set `-XX:MaxRAMPercentage=75` (the default is 25% — you're wasting three quarters of your container). Consider pinning `-XX:ActiveProcessorCount`.

### 5.15 The InnoDB clustered index — why a bad primary key costs you twice

Two structural facts with no Postgres equivalent:

1. **The PK *is* the table.** InnoDB's clustered index stores the full row in PK order. There is no separate heap. So PK order dictates physical insert order.
2. **Every secondary index entry stores the full PK** as its row pointer.

"Expensive twice over" is precise: a **wide** PK inflates the clustered index *and* every secondary index; a **random** PK destroys insert locality *and* dirties pages all over the buffer pool. Both then multiply by your number of secondary indexes — and MySQL auto-creates an index on every FK column, so you have more than you think.

Practical guidance: PK narrow and monotonic (`BIGINT AUTO_INCREMENT`, or a time-sortable ID). **Never a natural composite/string PK on a table with several secondary indexes** — `PRIMARY KEY (tenant_id, email)` pushes that whole tuple into every one. **Always declare a PK** (without one InnoDB uses a hidden 6-byte global counter — a cross-table contention point). And you can **exploit** clustering deliberately: `PRIMARY KEY (tenant_id, id)` physically co-locates a tenant's rows, turning a tenant-scoped range scan into sequential I/O. That's a genuine MySQL-specific optimization — weigh it against the PK-in-every-secondary-index cost.

Jeremy Cole's [Visualizing the impact of ordered vs. random index insertion in InnoDB](https://blog.jcole.us/2013/10/02/visualizing-the-impact-of-ordered-versus-random-index-insertion-in-innodb/) is the artefact to show anyone defending UUIDv4 PKs.

### 5.16 Replication lag, and why `Seconds_Behind_Source` lies

Verbatim from the docs — quote this at anyone who alerts on it:

> "If the network is slow, this is not a good approximation; the replication applier thread may quite often be caught up with the slow-reading replication receiver thread, so `Seconds_Behind_Source` often shows a value of 0, even if the replication receiver thread is late compared to the source. **In other words, this column is useful only for fast networks.**"

Three more documented failure modes: clock skew (including NTP updates); **the NULL semantics changed in 8.4** (so old alerting logic breaks); and with multithreaded appliers — now the default — the value *"is based on `Exec_Source_Log_Pos`, and so may not reflect the position of the most recently committed transaction."*

**So it reads 0 while arbitrarily far behind, in exactly the failure mode where you most need it honest. Never gate read-after-write routing on it.**

**Better:** commit-timestamp-based lag from `performance_schema.replication_applier_status_by_worker`:

```sql
SELECT WORKER_ID, SERVICE_STATE,
       TIMESTAMPDIFF(MICROSECOND, LAST_APPLIED_TRANSACTION_ORIGINAL_COMMIT_TIMESTAMP,
                     LAST_APPLIED_TRANSACTION_END_APPLY_TIMESTAMP)/1e6 AS e2e_lag_s,
       TIMESTAMPDIFF(MICROSECOND, APPLYING_TRANSACTION_ORIGINAL_COMMIT_TIMESTAMP,
                     NOW(6))/1e6                                       AS in_flight_lag_s
FROM performance_schema.replication_applier_status_by_worker;
```

`in_flight` high but `e2e` low → one big transaction applying. Both high with all workers busy → genuinely applier-bound. Coordinator busy, workers idle → dependency-tracking serialization. And `pt-heartbeat` remains the gold standard for one trustworthy number, because it measures the **whole pipeline** against one clock.

**App-side, the actual fix:** route by intent, not by lag. For genuine read-after-write, capture the write's GTID and `SELECT WAIT_FOR_EXECUTED_GTID_SET(gtid, timeout)` on the replica — that's the only correct mechanism. Or pin the session to the primary for a short window after any write (coarse, simple, effective). And note `@Transactional(readOnly=true)` is a *routing hint*; it does not make the read safe from staleness.

> ⚠️ **`SHOW SLAVE STATUS` is removed in 8.4.** Any health-check or monitoring code parsing it is now broken. Use `SHOW REPLICA STATUS`.

---

## 6. Pools and queues: where requests actually wait

**This section is the one most likely to find your bottleneck**, and it is the one most often skipped, because every pool in a JVM service ships with a default that is wrong for a service under load — and none of them warn you.

The unifying idea: **a bounded pool is a semaphore with an acquire timeout.** Requests beyond the bound queue. The only questions that matter are *how big is the bound*, *how long will you wait*, and *can you see the queue*. Little's Law sizes all of them:

> **pool size = target_rps × mean_hold_time × headroom**

You have four queues in front of a typical request. Here they are, with their real defaults:

| Tier | Bound | Default | Wait before failing | Visible? |
|---|---|---|---|---|
| Kernel accept queue | `min(accept-count, somaxconn)` | 100 / 4096 | silent drop → client SYN retry (~1 s, 3 s…) | **no Micrometer metric at all** |
| Tomcat connection limiter | `server.tomcat.max-connections` | **8192** | until a worker frees up | `tomcat.connections.current` (proxy) |
| Tomcat worker threads | `server.tomcat.threads.max` | **200** | queue is effectively unbounded | `tomcat.threads.busy` |
| Outbound HTTP pool | `maxPerRoute` (Apache HC5) | **5** | `connectionRequestTimeout` = **3 minutes** | only if you register the binder |
| DB pool | `maximumPoolSize` | **10** | `connectionTimeout` = **30 s** | `hikaricp.connections.pending` ✅ |

Read that table again. **The outbound HTTP defaults are the worst numbers in the JVM ecosystem**, and §6.3 explains why.

### 6.1 Sizing: Little's Law, and the two caveats people miss

**Worked example.** A checkout service handles 800 rps. Each request makes one call to `payments`, whose mean response time is 60 ms (p99 = 400 ms).

```
mean concurrency = 800 rps × 0.060 s = 48 connections in flight on average
```

48 is the *average*. Sizing to the average means you queue half the time. Add **1.5–2× headroom for variance** (Poisson bursts, upstream retries, cron alignment) → **72–96**.

Then sanity-check against the tail: if a latency excursion pushes mean response time to the p99 (400 ms), required concurrency becomes `800 × 0.4 = 320`. You cannot size for that and shouldn't — that's what a circuit breaker is for. But **know** that at 96 connections, your throughput ceiling during a 400 ms excursion is `96 / 0.4 = 240 rps`, i.e. you shed 70% of traffic. Decide deliberately.

**Now run the same arithmetic on the default.** `maxPerRoute = 5` at 60 ms mean:

```
max throughput = 5 / 0.060 s ≈ 83 rps
```

**83 rps.** Against a target of 800. Your 200 Tomcat threads, your 40 Hikari connections, your 16-core box — all irrelevant. 90% of every request's latency is spent parked in `PoolingHttpClientConnectionManager.lease()`, and the payments service reports a flat, healthy 60 ms the entire time. **That is the whole failure mode in one line of arithmetic.**

**Caveat 1 — size for the *downstream's* capacity, not yours.** Little's Law tells you the pool *you* need to hit *your* target. It says nothing about whether the dependency can serve it. If `payments` runs 4 pods × 200 threads = 800 concurrent slots and has nine callers, your fair share is ~89 — and if all nine callers independently "size for their own target with 2× headroom," you have collectively provisioned 1,700 concurrent requests against 800 slots. **An oversized client pool is a DDoS on your dependency, and it arrives precisely when the dependency is already struggling** (slow responses raise your in-flight count, which is exactly when your pool expands to max). The bounded pool is what stops you doing this. Negotiate a concurrency budget with the owning team and encode it as `maxPerRoute`.

**Caveat 2 — per-route vs total.** `maxTotal` is a shared ceiling; `maxPerRoute` is per `(scheme, host, port)`. Two mistakes: `maxTotal` too low relative to the sum of per-route limits, so one noisy dependency starves the others; and forgetting that **DNS round-robin still shares one route** (route is keyed by hostname, not resolved IP) while a proxy or a different port changes the route key.

```java
cm.setMaxTotal(300);
cm.setDefaultMaxPerRoute(20);
cm.setMaxPerRoute(new HttpRoute(new HttpHost("https","payments.internal",443)), 96);
```

**Caveat 3 — with virtual threads the formula still holds, but for the *resource*, not the thread.** Little's Law never applied to threads specifically; it applies to whatever is scarce. Virtual threads remove threads from the scarce list. Apply the formula to what's left — and add explicit admission control (§6.2).

### 6.2 Inbound: the five places a request waits before it has a thread

```
client SYN
   ├─(1) SYN queue          net.ipv4.tcp_max_syn_backlog          ← half-open
   ├─(2) ACCEPT queue       min(accept-count, net.core.somaxconn)  ← INVISIBLE TO THE JVM
   ├─(3) Tomcat acceptor    blocked on a LimitLatch = maxConnections  ← invisible to profiling
   ├─(4) Poller             socket registered, no readable data (idle keep-alive; 0 threads)
   ├─(5) Executor queue     TaskQueue (only once poolSize == maxThreads)
   └─(6) Worker thread      ← the ONLY stage a thread dump or profiler can see
```

**Exact Spring Boot / Tomcat defaults** (source-verified from `TomcatServerProperties` and `AbstractEndpoint`):

| Property | Default |
|---|---|
| `server.tomcat.threads.max` | **200** |
| `server.tomcat.threads.min-spare` | 10 |
| `server.tomcat.max-connections` | **8192** |
| `server.tomcat.accept-count` | **100** |
| `server.tomcat.connection-timeout` | **60 s** — and there's a cautionary tale here. `SocketProperties` initialises `soTimeout` to 20000, which makes a source-reading say "20 s"; but `AbstractHttp11Protocol`'s constructor then calls `setConnectionTimeout(60000)`, overwriting it. A bare `Http11NioProtocol` reports **60000**. *Reading the source is right; stopping one call short of the constructor is not.* |
| `server.tomcat.max-keep-alive-requests` | 100 |

**Stage (3) is the important one.** `AbstractEndpoint` holds a `LimitLatch` sized to `maxConnections`, and the acceptor thread calls `countUpOrAwaitConnection()` **before** `accept()`. At the limit, the acceptor blocks and stops accepting; connections pile up in the kernel accept queue, and when *that* fills, the kernel silently drops the SYN-ACK. The client sees a slow connect, a retry, then a timeout.

**Do the arithmetic on the defaults.** `maxConnections` (8192) is **40×** `maxThreads` (200). At 200 threads and 100 ms service time (2,000 rps), a full backlog implies **~4 seconds of pure queue delay before the request is even seen.** If your upstream timeout is 2 s, you are doing 100% wasted work. **Lowering `max-connections` toward a small multiple of `threads.max` converts invisible latency into fast, visible connection failures** — which is usually what you want.

**Little's Law on the inbound side.** With blocking I/O, a thread is held for the entire wall-clock duration including network wait, so a thread *is* a unit of concurrency:

- Required threads = `rps × mean_response_time`. 1,000 rps at 200 ms → 200 threads. **The Tomcat default is calibrated to exactly that, with zero headroom.**
- Conversely `maxThreads=200` is a hard ceiling of `200 / mean_response_time`. At 500 ms mean that's **400 rps, full stop** — no amount of CPU helps.
- **The nasty coupling:** response time includes downstream wait. If a dependency degrades 50 ms → 500 ms, your required thread count rises 10× at constant rps. **Thread pools convert *downstream* latency into *local* saturation.** This is why a slow dependency takes down a service with idle CPU.

**The observability gap, and how to close it.** Micrometer's `TomcatMetrics` has **no gauge for accept-queue occupancy, no gauge for the `LimitLatch` wait count, and no counter for kernel drops** (source-verified). Two things to do:

First, **enable the metrics at all** — Spring Boot: *"Auto-configuration enables the instrumentation of Tomcat only when an MBean Registry is enabled. By default, the MBean registry is disabled."* Without `server.tomcat.mbeanregistry.enabled=true` the thread gauges you most need are silently absent.

Second, **read the kernel directly.** This is the single most valuable command in this section:

```bash
ss -lnt 'sport = :8080'
# State   Recv-Q  Send-Q  Local Address:Port
# LISTEN  0       100     *:8080
#         ▲       ▲
#         │       └── capacity: min(accept-count, somaxconn)
#         └────────── current accept-queue depth
```

For a **LISTEN** socket, `Recv-Q` is the current accept-queue occupancy and `Send-Q` is the limit (verified against `net/ipv4/tcp_diag.c`). For an ESTABLISHED socket the same columns mean unread/unacked **bytes** — completely different semantics, which is why this is so widely misread. ⚠️ The `ss(8)` man page doesn't document these columns at all, and older versions described them wrongly as the SYN backlog.

**Rule: `Recv-Q` on a listener should be 0 or near 0 at all times.** `Recv-Q == Send-Q` means you are actively dropping.

```bash
nstat -az TcpExtListenOverflows TcpExtListenDrops   # cumulative; deltas are what matter
nstat                                              # deltas since last run — best for load tests
netstat -s | grep -iE 'listen|overflow'
```

- **`ListenOverflows` rising** ⇒ the accept queue was full when a handshake completed. Unambiguous. Raise `accept-count` **and** `somaxconn`, and/or fix why the app isn't accepting.
- **`ListenDrops − ListenOverflows > 0`** ⇒ resource exhaustion rather than backlog sizing.

In Prometheus, node_exporter does export these even though Micrometer doesn't:

```promql
rate(node_netstat_TcpExt_ListenOverflows[1m])   # > 0 == dropping connections. Page on this.
```

**OS defaults worth knowing:** `net.core.somaxconn` is **4096** since Linux 5.4 (it was 128 before — most blog posts are pre-5.4). And `listen(2)`: *"If the backlog argument is greater than the value in `/proc/sys/net/core/somaxconn`, then it is silently capped to that value."* So `accept-count=4096` on a container with `somaxconn=128` silently becomes 128. **Set both.** With `tcp_abort_on_overflow=0` (the default) overflow is a **silent drop**, not a reset — which is precisely why accept-queue overflow presents as *"random 1-second and 3-second latency spikes with no server-side trace."*

**A sensible inbound baseline:**

```properties
server.tomcat.threads.max=400
server.tomcat.threads.min-spare=40
server.tomcat.max-connections=1000      # admission control: small and bounded
server.tomcat.accept-count=100
server.tomcat.keep-alive-timeout=20s
server.tomcat.mbeanregistry.enabled=true
```

**Event-loop servers fail differently — this is worth internalizing.** A thread-per-request server that runs out of threads gets *slower*: requests queue, latency rises, throughput plateaus, and it degrades monotonically. An event-loop server (WebFlux/Reactor Netty, default `max(cores, 4)` loops) that **blocks on a loop thread stops processing every other connection assigned to that loop.** One blocking JDBC call inside a `map()` on a 4-core box freezes 25% of your server's I/O — including health checks, including responses for requests that already finished their work. There's no queue to observe and no thread count to alarm on; the symptom is bimodal latency and inexplicable timeouts on unrelated endpoints. This is why `BlockHound` exists and why `publishOn(Schedulers.boundedElastic())` is mandatory around anything blocking. **Sizing an event-loop pool larger to "handle load" is a category error** — size loops to cores and keep them non-blocking.

> ⚠️ **Spring Boot 4 dropped Undertow** (Servlet 6.1 baseline incompatibility). Don't write a Boot 4 tuning guide with `server.undertow.*` in it.

**Virtual threads: the bottleneck moves, and gets worse.** `spring.threads.virtual.enabled=true` replaces Tomcat's bounded executor outright with one that starts a fresh virtual thread per task. Spring Boot's docs: *"If virtual threads are enabled, properties which configure thread pools don't have an effect anymore."*

Before, 200 threads was simultaneously your concurrency limit *and* your admission control, and excess work waited **without holding any downstream resource**. After, the only inbound limits left are `maxConnections` (8192) and `acceptCount` (100). Up to 8,192 requests now run *concurrently*, each arriving at your Hikari pool (default 10) or your HTTP pool (default 5 per route). **The queue did not disappear. It moved, and it got worse in three ways:**

1. **Bigger** — 8,192 waiters instead of 200, each holding a stack chunk, request object, parsed headers, `SecurityContext`, socket, and trace context. You can OOM at a load level that previously just got slow.
2. **Resource-holding** — a request queued in Tomcat's executor held nothing; a request parked in `HikariPool.getConnection()` holds a socket, a virtual thread, and its whole request state.
3. **A timeout bomb** — 8,192 requests contending for 10 DB connections all wait up to Hikari's 30 s default, then **fail simultaneously**. Under platform threads you'd have shed load earlier and more gracefully.

Oracle's own virtual-threads guide prescribes the fix — a `Semaphore` — and explains why it's equivalent: *"the semaphore internally … creates a queue of threads that are blocked on it that mirrors the queue of tasks waiting for a pooled thread."*

```properties
server.tomcat.max-connections=2000         # ← with virtual threads, THIS is your admission control
spring.threads.virtual.enabled=true
spring.main.keep-alive=true                # virtual threads are daemon threads; the JVM would exit
spring.datasource.hikari.maximum-pool-size=40
spring.datasource.hikari.connection-timeout=2000   # NOT 30s. Fail fast.
```

**The design rule: a bounded queue with a short timeout and fast rejection is strictly better than an unbounded queue with a long timeout.** Virtual threads remove the accidental bound, so you must supply an intentional one.

**On pinning:** [JEP 491](https://openjdk.org/jeps/491) removed `synchronized` pinning in **JDK 24**. This mattered enormously for JDBC — pre-24, a virtual thread entering a `synchronized` block and then blocking on socket I/O pinned its carrier, and on an 8-core box 8 concurrent pinned queries could deadlock the whole application (hung app, idle CPU). **Connector/J 9.0.0 also replaced its own `synchronized` blocks with `ReentrantLock`s specifically for virtual threads** — which is the single biggest reason a Spring Boot service on virtual threads should be on Connector/J 9.x, not 8.0.x. What still pins is native/JNI frames. Detect with `jfr print --events jdk.VirtualThreadPinned` and `jcmd <pid> Thread.dump_to_file -format=json`.

### 6.3 Outbound: the worst defaults in the ecosystem

**The headline finding, verified by reading Spring Boot 4.1's source:** `HttpComponentsHttpClientBuilder.createConnectionManager()` **never calls `setMaxConnTotal` or `setMaxConnPerRoute`.**

> **A Spring Boot 4.1 app with `httpclient5` on the classpath and a `RestClient` gets `maxTotal = 25`, `maxPerRoute = 5`. Five concurrent requests per host. Against 200 Tomcat threads. That is the default, and nothing warns you.**

And `HttpClientSettings.defaults()` is all nulls, so unless you set `spring.http.clients.connect-timeout` / `read-timeout`, **Boot applies no timeouts of its own.**

**Exact defaults, source-verified:**

| Client | Max total | Max per host | Connect | Read | **Pool borrow wait** | End-to-end |
|---|---|---|---|---|---|---|
| **Apache HttpClient 5** (5.6.x) | **25** | **5** | 3 min | 3 min | **3 min** ⚠️ | none |
| **OkHttp** (5.x) | unbounded (5 *idle*) | **5** (`maxRequestsPerHost`) | 10 s | 10 s | n/a | **`callTimeout = 0` = none** ⚠️ |
| **Reactor Netty** (1.3.x) | `max(cores,8) × 2` — so ≥16 | same | OS default | **none** | **45 s** ⚠️ | none |
| **JDK `HttpClient`** | **unbounded** | unbounded | **undocumented / ~OS ~130 s** ⚠️ | **infinite** ⚠️ | n/a | **infinite** ⚠️ |
| HikariCP (for contrast) | 10 | — | — | — | 30 s | — |

**`connectionRequestTimeout` is the number that matters, and its default is 3 minutes.** It is the time spent **waiting to borrow a connection from the pool** — pure queue wait, before a single byte hits the network:

```
total = [connectionRequestTimeout window] + [connectTimeout] + [TLS] + [socketTimeout]
         ─────── pool queue wait ───────    ──────── actual work on the wire ────────
```

So by default, when your 5-per-route pool is exhausted, requests silently park for up to **180 seconds** and then fail with `ConnectionRequestTimeoutException`. Every one of those seconds is invisible unless you go looking.

**Set it to ~200 ms and the most-misdiagnosed HTTP failure becomes self-diagnosing.** This is the highest-leverage one-line change in this document. Same logic for Reactor Netty's `pendingAcquireTimeout` (45 s → 200 ms) and Hikari's `connectionTimeout` (30 s → 2 s).

```java
@Bean
RestClient paymentsClient(RestClient.Builder builder) {
    PoolingHttpClientConnectionManager cm = PoolingHttpClientConnectionManagerBuilder.create()
        .setMaxConnTotal(200)
        .setMaxConnPerRoute(96)                        // ← 5 by default
        .setDefaultConnectionConfig(ConnectionConfig.custom()
            .setConnectTimeout(Timeout.ofMilliseconds(500))
            .setSocketTimeout(Timeout.ofSeconds(2))
            .setValidateAfterInactivity(TimeValue.ofSeconds(5))
            .setTimeToLive(TimeValue.ofMinutes(5))     // hard age cap — helps LB rebalancing
            .build())
        .build();

    CloseableHttpClient hc = HttpClients.custom()
        .setConnectionManager(cm)
        .setDefaultRequestConfig(RequestConfig.custom()
            .setConnectionRequestTimeout(Timeout.ofMilliseconds(200))  // ← 3 MINUTES by default
            .setResponseTimeout(Timeout.ofSeconds(2))
            .build())
        .evictIdleConnections(TimeValue.ofSeconds(30))  // ← OFF by default. See §6.6.
        .evictExpiredConnections()
        .build();

    // ← Spring Boot does NOT do this for you
    new PoolingHttpClientConnectionManagerMetricsBinder(cm, "payments").bindTo(registry);

    return builder.requestFactory(new HttpComponentsClientHttpRequestFactory(hc)).build();
}
```

**Client-specific gotchas worth knowing:**

- **OkHttp's `maxRequestsPerHost = 5`** — the same magic number, the same effect. `maxRequests = 64` is irrelevant if you only call one host. And `maxIdleConnections = 5` caps *idle* connections only, not total, so bursty traffic produces connection churn even though nothing looks "exhausted." **`callTimeout = 0`** means the only end-to-end timeout is off: connect/read/write are each 10 s, but a response that trickles bytes forever satisfies all three indefinitely. ⚠️ Note Spring has **no OkHttp `ClientHttpRequestFactory` any more** — using OkHttp with Spring now means wiring it yourself.
- **Reactor Netty's `maxIdleTime` defaults to `-1` — never evict.** This is the #1 cause of WebClient "connection reset by peer" in production (§6.6). You **must** set it. Its two failure modes are usefully distinguishable: `PoolAcquirePendingLimitException` is the *good* one (fast, unambiguous — the pending queue overflowed at `2 × maxConnections`); `PoolAcquireTimeoutException` is the *bad* one (45 seconds of latency attributed to nothing). And a trap in Spring's `ReactorResourceFactory`: `useGlobalResources` defaults to `true` → `2×cores (min 16)`, but set it to `false` without supplying a provider and the fallback is `ConnectionProvider.create("webflux", 500)` — **500 connections.** Two very different numbers depending on a boolean.
- **The JDK `HttpClient` has no pool sizing API and an unbounded keep-alive cache** (`jdk.httpclient.connectionPoolSize=0` = unbounded). So you *cannot* undersize it — that's the good news. The bad news is timeouts: there is **no read timeout on the client at all**. The only response timeout is per-request `HttpRequest.Builder.timeout(Duration)`, whose javadoc says *"The effect of not setting a timeout is the same as setting an infinite Duration, i.e. block forever."* And `HttpClient.Builder.connectTimeout()` doesn't document its default when unset — empirically you fall through to the OS TCP connect timeout (~130 s on Linux). **Treat both as infinite and always set both.** Also: **there are no pool metrics of any kind** — no stats API, no Micrometer binder, no JMX.
  > ⚠️ And `jdk.httpclient.maxstreams` is widely misreported: it governs **push** streams the client permits *servers* to open. It does **not** limit your own HTTP/2 request concurrency, which comes from the server's `SETTINGS_MAX_CONCURRENT_STREAMS`.
- **`-Dhttp.maxConnections` does not work with HttpClient 5.** `PoolingHttpClientConnectionManagerBuilder.useSystemProperties()` has **no effect on pool sizing** — it only selects the system-default TLS strategy. Verified empirically: with `-Dhttp.maxConnections=77`, `maxTotal` stayed 25 and `maxPerRoute` stayed 5. The 4.x trick is dead; don't repeat that advice.

**Which client you actually get in Boot 4.x**, in `detect()` order: `httpComponents()` → `jetty()` → `reactor()` → `jdk()` → `simple()`. Since `java.net.http` is always present, `jdk()` always succeeds and `SimpleClientHttpRequestFactory` is unreachable — so the old "no pooling, no timeouts" hazard is gone, replaced by a different one: **the JDK client's unbounded pool and infinite read timeout.**

> ⚠️ Note the property rename: `spring.http.client.*` (Boot 3.4/3.5, singular) → **`spring.http.clients.*`** (Boot 4.x, plural, with `imperative`/`reactive` sub-namespaces).

**Bottom line: whichever client you get, the defaults are not production-safe and Boot will not warn you.** Add `httpclient5` and you must raise 25/5 and shorten the 3-minute borrow wait. Add nothing and you must set timeouts.

**HTTP/2 changes the model.** Under HTTP/1.1, `maxPerRoute` *is* your concurrency limit. Under HTTP/2 one connection carries many streams, so `maxPerRoute = 5` against a server allowing 100 streams each is 500 concurrent requests. Consequences: **size for streams, keep connections small** (1–4 per host is often plenty; oversizing is now pure waste); watch for **TCP head-of-line blocking** (one connection = one congestion window, so `minConnections ≥ 2` is a reasonable hedge on lossy networks); and beware **load balancer stickiness** — one long-lived H2 connection pins to one backend pod and does not rebalance on scale-out. That last one is the most common HTTP/2 surprise in Kubernetes; the fix is a `maxLifeTime` on the client pool to force periodic reconnect. Server-side, Tomcat 11 allows `maxConcurrentStreams=100` but `maxConcurrentStreamExecution=20` — **one HTTP/2 client connection can consume 20 of your 200 Tomcat threads**, so ten aggressive clients can consume all of them.

### 6.4 The DB pool, and what MySQL specifically changes

**The formula**, from [HikariCP's *About Pool Sizing*](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing):

> **`connections = ((core_count * 2) + effective_spindle_count)`**

`core_count` is physical cores **on the database** (not hyperthreads, not your app server), and it's your **total** budget across all app instances, not per instance. The wiki's axiom: *"You want a small pool, saturated with threads waiting for connections."* Its evidence: an Oracle Real-World Performance demo where cutting the pool from ~2048 to ~96 took response times from ~100 ms to ~2 ms with no other change.

> ⚠️ **The HikariCP wiki contains no MySQL-specific pool guidance** — the formula is Postgres-derived. Anyone citing it as "the MySQL formula" is over-reading it.

**Why an oversized pool makes latency worse** — requests must queue *somewhere*:

- **Small pool:** they queue in your app, where the queue is **visible** (`hikaricp_connections_pending`), **bounded** (`connectionTimeout` fails fast), FIFO-ish, and cheap (a parked Java thread).
- **Large pool:** the queue moves **inside MySQL**, where it's **invisible to your app metrics** (`pending` reads 0 and the pool "looks healthy" while p99 triples), **unbounded and unfair** (everyone slows proportionally — the convoy effect), and **more expensive per unit of work** (more context switching, more contention on InnoDB's internal latches, and — crucially per §5.9 — **more lock contention and more deadlocks**).

**Here is where MySQL genuinely differs from Postgres, stated precisely because it's usually stated wrongly:**

MySQL is **thread-per-connection**; Postgres is **process-per-connection**. So separate *idle* from *running*:

- **Idle connections are genuinely cheaper on MySQL.** A parked thread costs a stack plus net buffers; a parked Postgres backend costs a process plus its share of snapshot work that scales with backend count. MySQL tolerates a much higher `max_connections` — thousands is unremarkable, where Postgres past a few hundred wants PgBouncer.
- **Running concurrency is bounded by the same physics.** MySQL's own docs are candid about the model's downside: *"thread creation and disposal becomes expensive. Also, each thread requires server and kernel resources, such as stack space… scheduling overhead can become significant."*

**So: yes, MySQL lets you be sloppier about pool size than Postgres does — but the optimum is roughly the same, and "can survive" ≠ "goes faster."**

**`Threads_running` is the number to watch, and it's the best thing MySQL gives you here.** `Threads_connected` counts open sockets, which with a JVM pool is just `poolSize × instances` — a constant that tells you nothing. `max_connections` (default **151** [verified 8.4.11]) is a ceiling you hope never to touch. **`Threads_running` counts threads not idle — threads actually competing for CPU, locks, and buffer pool. It is MySQL's run queue.**

| `Threads_running` | Meaning |
|---|---|
| ≈ cores | fully utilized, near peak throughput. **This is the target.** |
| cores → 2–4 × cores | queueing. Latency rising, throughput flat. |
| > ~4 × cores sustained | **thrashing.** Throughput *falls* as you add load. Classic MySQL collapse curve. |
| spiking to 50–100+ while throughput craters | almost always a lock convoy or one bad plan, **not capacity**. Go to §5.9. |

**The counterintuitive action:** when `Threads_running` is too high, **shrink the JVM pool.** A pool of 20 per instance × 10 instances = 200 concurrent threads on a 16-core box is a guaranteed collapse. Target `Threads_running ≈ cores`, which usually means a *much* smaller pool than people expect.

> ⚠️ **The specific threshold above is received wisdom, not documented.** `Threads_running` is unambiguously the right *metric*; the multiple of cores is yours to establish empirically with the Phase B sweep. Don't publish it as a MySQL-documented number.

**MySQL-specific Hikari settings:**

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20
      connection-timeout: 2000        # not the 30000 default
      max-lifetime: 280000            # ← see below. NOT the 1800000 default.
      keepalive-time: 120000          # already the default on HikariCP 6.x/7.x;
                                      #   but it was 0 (DISABLED) on 5.1.x and earlier,
                                      #   so set it explicitly and state your version
      leak-detection-threshold: 20000
      # DO NOT set connection-test-query — see below
```

**Delete `connectionTestQuery=SELECT 1`.** HikariCP is explicit: *"If your driver supports JDBC4 we strongly recommend not setting this property."* Connector/J 9.x is JDBC 4.2, so `isValid()` uses a lightweight protocol-level ping instead of a full parse+execute+resultset cycle. Beyond the cost, **every `SELECT 1` pollutes `events_statements_summary_by_digest`** — I've seen `SELECT ?` be the #1 statement by `COUNT_STAR` purely from health checks, which actively obscures your §5.1 analysis.

**`maxLifetime` vs MySQL's `wait_timeout` — the classic bug.** MySQL's `wait_timeout` is **28800 s (8 h)** by default. Note that `interactive_timeout` is the sibling applied to clients setting `CLIENT_INTERACTIVE` — **the JDBC driver is not interactive, so `wait_timeout` is the one that governs your pool.** People get this wrong constantly, which is why raising `interactive_timeout` "doesn't fix it."

But **the effective limit is usually not `wait_timeout`.** It's whichever of these is smallest — and the last three are invisible from inside MySQL:

- `wait_timeout` (28800 default, but managed services and ops teams routinely set 60–600)
- **AWS NLB idle timeout: 350 s, historically not configurable** (an ALB is L7 and can't front MySQL, so it isn't in this list — it *is* in §6.6, where the traffic is HTTP)
- ProxySQL / RDS Proxy / Vitess connection lifetimes
- conntrack/NAT gateway idle eviction (often 300–350 s)

HikariCP's rule: *"We strongly recommend setting this value, and it should be several seconds shorter than any database or infrastructure imposed connection time limit."* **A defensible default for cloud MySQL is `maxLifetime=280000` (280 s)** — under the 350 s NLB/NAT floor. And `keepaliveTime` (120 s) is the belt to `maxLifetime`'s braces.

Counter-tension worth naming: a short `maxLifetime` means more connection churn, hence more TLS handshakes and more `SHOW VARIABLES`/`SHOW COLLATION` round trips on each new connection. **That's exactly why `cacheServerConfiguration=true` matters more on MySQL than people assume.**

**On ProxySQL as the PgBouncer analogue** — you need it less often than in Postgres-land, and for different reasons. Its **multiplexing** is the transaction-pooling equivalent, but the conditions that disable it are fatal for a Spring/Hibernate app: **active transactions** disable it until commit; **any query containing `@`** (session/user variables) disables it; `CREATE TEMPORARY TABLE`, `GET_LOCK()`, and `SQL_CALC_FOUND_ROWS` disable it **permanently** on that connection. Since you spend nearly all your time inside `@Transactional`, **multiplexing is off for nearly all of your useful work.** ProxySQL's real value for a JVM app is connection admission control, routing, and failover — not the connection amplification it gives a PHP/serverless fleet. **Fix `maximumPoolSize × instances` first.**

### 6.5 Telling "my pool" apart from "their service" — the decoder ring

This is the practical skill, because **every metric you'd naturally look at exonerates the actual culprit:**

| Signal | Undersized *client pool* | Genuinely *slow peer* |
|---|---|---|
| Your endpoint latency | ⬆️ rises sharply, often 10× | ⬆️ rises |
| **The peer's own server-side latency** | **flat, healthy** | ⬆️ rises, and matches yours |
| Requests/sec to the peer | **hard plateau at `max / latency`** | falls |
| Peer CPU / thread-busy | **flat or low** | ⬆️ high |
| Pool `pending` gauge | **⬆️⬆️ climbs and stays up** | ~0 |
| Pool `leased` gauge | **pinned at `max`, dead flat** | below max, fluctuating |
| Errors | `ConnectionRequestTimeoutException` / `PoolAcquireTimeoutException` / `SQLTransientConnectionException` | `SocketTimeoutException` / 503 / 504 |
| Latency histogram shape | **bimodal or cliff-edged** — fast when a connection is free, `≈ borrow timeout` when not | smooth rightward shift |
| Scaling out your own pods | **no per-pod improvement, total throughput rises linearly** (each pod gets its own 5) | no improvement |
| Raising the pool bound | **immediate fix** | no effect |

**Four techniques, cheapest first:**

**(1) Pool metrics.** `leased == max` with `pending > 0` is decisive. There is no ambiguity.

```promql
httpcomponents_httpclient_pool_total_pending                              # alert > 0
httpcomponents_httpclient_pool_total_connections{state="leased"}
  / httpcomponents_httpclient_pool_total_max                              # alert > 0.8
reactor_netty_connection_provider_pending_connections                     # alert > 0
histogram_quantile(0.99, rate(
  reactor_netty_connection_provider_pending_connections_time_seconds_bucket[5m]))
hikaricp_connections_pending                                              # alert > 0
histogram_quantile(0.99, rate(hikaricp_connections_acquire_seconds_bucket[5m]))
```

Reactor Netty's `pending.connections.time` is the gold standard — a direct histogram of borrow wait. **If p99 acquire time is 300 ms and the downstream p99 is 40 ms, you are done diagnosing in one panel.** (Remember: `.metrics(true)` is off by default, and the Apache binder isn't auto-registered.)

**(2) Make the pool name itself in your logs.** With a 3-minute borrow timeout, exhaustion looks like generic slowness. At 200 ms it looks like `ConnectionRequestTimeoutException: Timeout deadline: 200 MILLISECONDS`.

**(3) Attach pool state as span attributes.** Cheap, and it means every slow trace carries its own explanation:

```java
PoolStats s = cm.getTotalStats();
span.tag("pool.leased",  String.valueOf(s.getLeased()));
span.tag("pool.pending", String.valueOf(s.getPending()));
span.tag("pool.max",     String.valueOf(s.getMax()));
```

Then "show me spans over 1 s" comes back with `pool.pending=87, pool.leased=5, pool.max=5` attached.

**(4) async-profiler in wall-clock mode.** CPU profiling shows nothing — the thread is parked, consuming zero CPU. This is why *"we profiled it and found nothing"* is the standard prelude to this bug.

```bash
asprof -e wall -t -i 10ms -d 60 -f /tmp/wall.html <PID>
```

**The decoder ring — read the flame graph for parked frames:**

| Frame | Diagnosis |
|---|---|
| `StrictConnPool.lease` → `Future.get` → `park` | **Apache HttpClient 5 pool exhaustion** |
| `InstrumentedPool.acquire` / `SimpleChannelPool` | Reactor Netty pool exhaustion |
| `Dispatcher.promoteAndExecute` / `readyAsyncCalls` | OkHttp `maxRequestsPerHost` throttling |
| `HikariPool.getConnection` → `ConcurrentBag.borrow` → `park` | DB pool exhaustion |
| `SocketInputStream.socketRead0` / `NioSocketImpl.read` / `SSLSocketImpl.readApplicationRecord` | **genuinely waiting on the wire — the peer really is slow** |

**That table is the crisp answer: `lease`/`borrow`/`acquire` frames mean your pool; `socketRead`/`readApplicationRecord` frames mean their service.** Wall-clock profiling is the only tool that shows you both in one picture with correct proportions.

With virtual threads, wall-clock sampling of every virtual thread is impractical — use JFR plus `jcmd <PID> Thread.dump_to_file -format=json` and grep the JSON for parked stacks containing `lease` or `getConnection`.

### 6.6 Keep-alive, churn, and the idle-timeout mismatch bug

**Why churn costs you.** A full TLS handshake is ~1 ms of CPU and multiple round trips; at 1,000 rps with zero reuse that's 1,000 handshakes/s, often **10–30% of a service's CPU** spent entirely on setup. It shows up in profiles as `sun.security.ssl.*` / `SSLSocketImpl.startHandshake`. Symptom: **CPU scales with request rate rather than with work.** Latency-wise, TCP (1 RTT) + TLS 1.3 (1 RTT) = 2 extra RTTs per request — ~2 ms in-AZ, ~60 ms cross-region.

**Ephemeral port exhaustion.** `net.ipv4.ip_local_port_range` default `32768 60999` = **28,232 ports**, held in `TIME_WAIT` for **60 s on Linux (fixed, not tunable)** after an active close. So:

```
28232 ports / 60 s ≈ 470 new connections/second, per destination (ip:port)
```

Above that you get `java.net.NoRouteToHostException: Cannot assign requested address` — **an error message that names the wrong problem**, which is why this takes people days. Observe with `ss -s` and `ss -tan state time-wait | wc -l`. Mitigations in order: **reuse connections** (the actual fix); widen the range to `10240 65535` (~900/s); `net.ipv4.tcp_tw_reuse=1` (safe with timestamps, outbound only); add destination IPs. **Never `tcp_tw_recycle`** — removed in Linux 4.12 and actively harmful behind NAT.

**The idle-timeout mismatch bug. This is the one that eats weeks.**

```
t=0     client borrows conn C, request OK, returns C to the pool as idle
t=60s   the LB's idle timeout fires. LB sends FIN on C.
        ── the client's pool does not notice: nothing is reading the socket ──
t=61s   client borrows C, writes a request onto a half-closed connection
t=61s   LB responds RST
t=61s   java.net.SocketException: Connection reset   (or "Broken pipe", or a truncated response)
```

Properties that make it maddening: the error rate is **low** (only requests landing in the window between the peer's FIN and the client's next validation); it is **proportional to idleness**, so it's *worse* in staging and at 3 a.m. than under load; it appears on **non-idempotent POSTs** so you cannot blindly retry; and **it never reproduces in a load test**, because connections are never idle long enough. The classic report is *"about 0.05% connection resets, always the first request after a quiet period."*

**The fix, as an invariant:**

> **client idle timeout < server / load-balancer idle timeout**, with real margin (aim for 0.5×).

Whoever closes first must be the client, because the client is the only party that can close a *pooled* connection cleanly without a request in flight.

Peer timeouts to check: AWS ALB **60 s**, AWS NLB **350 s (not configurable)**, GCP LB **600 s**, nginx `keepalive_timeout` **75 s**, Envoy `idle_timeout` **1 h**, and **embedded Tomcat 60 s** — note that last one *ties* an ALB's 60 s and undercuts several client defaults (OkHttp's pool keeps connections 5 minutes), so **a Boot-to-Boot call still needs an explicit client-side idle timeout with margin.** A tie is not margin.

```java
// Apache HttpClient 5 — none of this is on by default
HttpClients.custom()
    .evictIdleConnections(TimeValue.ofSeconds(30))   // ← 30s < ALB 60s. OFF BY DEFAULT.
    .evictExpiredConnections()
    .build();

// Reactor Netty — maxIdleTime is -1 (NEVER evict) by default.
// This is the #1 cause of WebClient "connection reset by peer" in production.
ConnectionProvider.builder("payments")
    .maxIdleTime(Duration.ofSeconds(20))             // ← MUST set
    .maxLifeTime(Duration.ofMinutes(5))
    .evictInBackground(Duration.ofSeconds(30))
    .build();

// OkHttp — 5 minutes by default, LONGER than an ALB's 60s. Lower it.
new ConnectionPool(50, 30, TimeUnit.SECONDS);
```

```bash
# JDK HttpClient — 30s default, usually fine for a 60s ALB, but be explicit
-Djdk.httpclient.keepalive.timeout=25
```

**And the MySQL version of exactly the same bug** is §6.4's `maxLifetime` vs the NLB's 350 s. It's the same mechanism, one tier down.

### 6.7 Timeout discipline, retries, and admission control

**Rule 1 — every timeout must be set, because many defaults are effectively infinite.** See the table in §6.3, and note that Connector/J's `connectTimeout` and `socketTimeout` **both default to 0 = no timeout.**

**Always set `socketTimeout` on your JDBC connection.** TCP gives you no timely notification when a peer *vanishes* rather than closes — a hard-killed DB node, a NAT dropping an idle flow, an OOM-killed mysqld. With `socketTimeout=0`, a `read()` on that socket blocks until the OS TCP retransmit budget expires: **on the order of 15 minutes.** Meanwhile the worker thread is pinned; Hikari's `connectionTimeout` does **not** help (the connection was already handed out, so nothing is waiting to borrow); and your circuit breaker never trips, because nothing has failed yet. In a load test it presents as a cliff: p99 goes to the ceiling and *stays*, the thread pool exhausts, health checks fail, and the incident outlives the actual database outage by many minutes.

Rule of thumb: `socketTimeout ≈ 2 × p999_query_time`, floor a few seconds; `connectTimeout` single-digit seconds. Note `socketTimeout` kills the *connection*, not the query — which is why you also want per-statement limits (`MAX_EXECUTION_TIME(n)` as an optimizer hint, or `Statement.setQueryTimeout()`).

**Rule 2 — the timeout budget must decrease down the call graph.**

```
your SLO                                      1000 ms
├── inbound queue + framework overhead          50 ms
├── MySQL call (borrow 100 + query 200)         300 ms
├── payments call (borrow 100 + resp 300)       400 ms
└── slack / GC / serialization                  250 ms
                                              ───────
                      Σ downstream ≤ 750 ms < 1000 ms SLO ✓
```

**The invariant:** `Σ (worst-case downstream timeouts on the critical path) < your own timeout < your caller's timeout`. Violations produce the worst possible behaviour — your caller gives up at 1 s while you keep working for 3 minutes, holding a thread, a connection, and an open transaction, producing a result nobody will read. **At scale this is how one slow dependency consumes a whole fleet: every layer doing 3 minutes of work for callers who left after 1 second.**

Better still, **propagate the remaining budget rather than re-deriving it.** Pass a deadline header and compute each call's timeout as `min(configured, deadline − now − reserve)`. **If the remaining budget is already negative, fail immediately without making the call.** A request that cannot possibly succeed in time should consume zero downstream capacity.

**Rule 3 — retries need backoff, jitter, *and* a budget.** From the [AWS Builders' Library](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/):

- On choosing a timeout: *"Choose an acceptable rate of false timeouts (such as 0.1%). Then, we look at the corresponding latency percentile on the downstream service (p99.9 in this example)"* — **timeouts come from the dependency's latency histogram, not from a round number you like.**
- On the danger: retries are *"selfish"*, and *"retries that increase load can make matters significantly worse. They can even delay recovery by keeping the load high long after the original issue is resolved."*
- On jitter: *"If all the failed calls back off to the same time, they cause contention or overload again when they are retried."*
- AWS prefers **token-bucket retry throttling** over circuit breakers: *"This allows all calls to retry as long as there are tokens, and then retry at a fixed rate when the tokens are exhausted."*

**The congestive-collapse mechanism, concretely.** A dependency degrades; 20% of calls time out; you retry 3× with no budget → offered load becomes 1.6× baseline at exactly the moment capacity dropped. More timeouts → more retries → 2.5× → 4×. Each retry also **holds a pool connection for the full timeout**, so your own pool saturates and *your* callers start timing out and retrying. The system now has a stable equilibrium at 100% failure **that persists after the original fault is fixed**, because the retry load alone exceeds capacity. Recovery requires shedding load, not adding capacity.

```java
RetryConfig cfg = RetryConfig.custom()
    .maxAttempts(3)                                   // total, not additional
    .intervalFunction(IntervalFunction.ofExponentialRandomBackoff(
        Duration.ofMillis(50), 2.0, /* randomizationFactor */ 0.5))
    .retryOnException(e -> e instanceof IOException)
    .build();
```

Non-negotiables: retry only idempotent operations (or use an idempotency key); never retry a 4xx; never retry when the remaining deadline is less than the expected latency; put the retry budget *outside* the retry loop so all callers share it. **And in MySQL, deadlock (error 1213 / SQLState 40001) *is* a retryable outcome and must be handled** — see §5.9.

**"A bounded pool IS a bulkhead."** A bulkhead caps the resources one dependency can consume so its failure can't sink the ship. A pool with `maxPerRoute = N` and `connectionRequestTimeout = T` does exactly that: at most N in-flight calls, and callers beyond that rejected within T. It is a semaphore of size N with an acquire timeout of T, wearing a different name. So:

- **You already have per-dependency bulkheads. Configure them before reaching for a library.** A separate `@Bulkhead` on top of a per-route limit is usually redundant and adds a second queue to reason about.
- **It breaks in exactly two cases**, and these are when you need Resilience4j: *shared* pools (`maxTotal` alone lets one slow dependency eat the whole budget — use per-route limits or separate clients), and *unbounded* pools (the JDK `HttpClient`, and virtual-thread executors, have no bound at all, so an explicit semaphore is the only bulkhead available).
- **A pool is a bulkhead but not a circuit breaker.** It caps concurrency; it doesn't stop you sending doomed requests. When a dependency is hard-down you still spend `connectTimeout` per attempt. That's what a breaker adds.

If you do reach for Resilience4j (2.4.0), prefer **`SemaphoreBulkhead`** (`maxConcurrentCalls=25`, `maxWaitDuration=0` — fail-fast load shedding for free, and it's the `Semaphore` pattern Oracle recommends for virtual threads) over `ThreadPoolBulkhead`, whose 100-deep queue reintroduces exactly the unbounded-queue problem.

**And admission control is the layer people skip.** Bulkheads protect *dependencies*; admission control protects *you*. Minimum viable version: cap concurrent in-flight requests at the edge, **reject with 503 + `Retry-After` rather than queueing**, and prioritise — shed batch, retry, and prefetch traffic before user-facing traffic. Under virtual threads this stops being optional.

Nygard's vocabulary is worth learning because it gives you the hypothesis list: **Integration Points**, **Cascading Failure**, **Blocked Threads** (the actual killer), **Slow Responses**, **Unbounded Result Sets**, **Dogpile** — countered by **Timeouts**, **Circuit Breaker**, **Bulkhead**, **Fail Fast**, **Shed Load**, **Back Pressure**. The through-line: ***slow responses are worse than no response.*** Every default in §6.3 — 3-minute borrow waits, 45-second acquires, infinite JDK reads — converts a fast failure into a slow response. Fixing them is applying **Fail Fast**.

### 6.8 The three panels that would catch every failure in this section

1. **`pending` for every pool** (inbound-adjacent, outbound HTTP, DB) on one graph, log scale. **Any non-zero sustained value is a sizing bug.**
2. **`busy/max` and `leased/max` for every pool**, on one graph, as ratios. **Anything above 0.8 is your next incident.**
3. **Your client p99 overlaid with the peer's own reported p99.** **A widening gap between them is, by definition, queue time on your side** — and it's the one comparison that distinguishes "their service is slow" from "my pool is too small."

Plus, because Micrometer cannot see it: `rate(node_netstat_TcpExt_ListenOverflows[1m])`.

---

## 7. Test data — the thing that decides whether any of this is real

A performance test on a tiny dataset isn't *less accurate*; it's **actively misleading**, because it produces *different query plans*. MySQL has three distinct mechanisms for this, and they fail in different directions:

1. **Index dives read your actual data.** For equality/range predicates with ≤`eq_range_index_dive_limit` (200) values, the optimizer physically dives into the index and counts. On a 1,000-row test table that returns a *correct, tiny* estimate — so the plan is correct for 1,000 rows and wrong for 100 million. **This is a sharper problem than in Postgres**, where estimates come from stored statistics you can transplant wholesale.
2. **Cardinality comes from sampled pages.** `innodb_stats_persistent_sample_pages` defaults to **20** [verified] — index cardinality is estimated from 20 random leaf pages. Fine on a small table; a guess on a large, skewed, or fragmented index. Raise to 100–1000 for big tables.
3. **Histograms don't exist unless you make them.** There is no auto-generation, ever. Small test data → no histograms → the optimizer assumes uniform distribution. If production has a histogram on a skewed column and test doesn't, plans differ by construction.

Plus the mundane one: **the buffer pool.** A 1 GB test dataset is 100% cached; a 500 GB production dataset is not. **Sizing the test buffer pool to the same *ratio* of dataset size as production matters more than the absolute number.**

What to match, in order of how often it's skipped:

- Row counts within an order of magnitude, for the tables in your hot queries.
- **Cardinality, not just volume** — and **include the whale tenant**. 50M rows spread evenly across 50,000 tenants gives wrong plans for both the median tenant and the big one.
- **Skew in the access pattern**, in the generator (Zipf, not uniform). As important as the data itself, and much more often skipped — and in MySQL it's where your gap-lock contention lives.
- Physical correlation. A table built by `generate_series`-style inserts is perfectly clustered on its PK; a real one that's been updated for two years isn't. Run representative UPDATE churn, then `ANALYZE TABLE`.
- String widths / off-page `TEXT` behaviour (§5.13).
- Then **`ANALYZE TABLE` everything.** Measuring against un-analyzed data is measuring nothing. And for skewed non-indexed filter columns, `ANALYZE TABLE t UPDATE HISTOGRAM ON col WITH 64 BUCKETS`.

> **On histograms, the docs are unusually blunt and worth quoting:** *"Histogram statistics are useful primarily for **nonindexed** columns."* And: *"The optimizer prefers range optimizer row estimates to those obtained from histogram statistics."* So histograms are for skewed, **non-indexed** columns used as filter predicates — `status`, `type`, soft-delete flags. The classic win is `WHERE status='PENDING'` where 0.1% are pending. They are **not** a substitute for an index, and on indexed columns they're mostly ignored. They also **do not auto-update** — re-run after significant data change.

### Can you transplant production statistics? Partially — and the caveats are the point

MySQL's analogue of PostgreSQL 18's `pg_dump --statistics-only` is copying `mysql.innodb_table_stats` and `mysql.innodb_index_stats`. **The docs explicitly bless it:**

> "The `innodb_table_stats` and `innodb_index_stats` tables can be updated manually, which makes it possible to force a specific query optimization plan or test alternative plans without modifying the database. If you manually update statistics, use the `FLUSH TABLE tbl_name` statement to load the updated statistics."

```sql
-- 0. CRITICAL: stop auto-recalc from silently reverting your work
SET GLOBAL innodb_stats_auto_recalc = OFF;
ALTER TABLE orders STATS_AUTO_RECALC=0;
SET GLOBAL information_schema_stats_expiry = 0;    -- else I_S is cached 24h

-- 1. On PROD:
--    mysqldump --no-create-info mysql innodb_table_stats innodb_index_stats \
--      --where="database_name='app'" > prodstats.sql
-- 2. On TEST: load, then
FLUSH TABLE orders;                                 -- required
```

**Tested end to end on 8.4.11. What it does change:** `SHOW INDEX` cardinality and `I_S.TABLES.TABLE_ROWS` update correctly, and **the plan genuinely changes** — in my test the join order flipped, and the optimizer correctly refused to drive from a table it now believed held 50M rows.

**What it does NOT change — the decisive caveat:** with default settings, **equality and range predicates still get their estimates from index dives into the actual (tiny) data.** So the most common OLTP predicate shape — `WHERE indexed_col = ?` — is *unaffected* by your injected statistics.

Four caveats, all verified:

1. **`innodb_stats_auto_recalc=ON` silently reverts your work.** My first attempt appeared to fail entirely; a background recalc had overwritten it. **This is not mentioned in the doc's paragraph.** Verify with `SELECT n_rows, last_update FROM mysql.innodb_table_stats` *after* the `FLUSH`.
2. **Index dives bypass the injection** for range/equality predicates. Partial mitigation is `SET eq_range_index_dive_limit=1` — but that itself changes optimizer behaviour, so you're now testing a third configuration.
3. **Histograms cannot be copied.** They live in the data dictionary, exposed **read-only** via `I_S.COLUMN_STATISTICS` (I confirmed `UPDATE` is denied). **So for skewed columns, statistics transplant cannot work at all.**
4. **`information_schema_stats_expiry=86400`** caches `I_S.TABLES`/`STATISTICS` for 24 hours, so your injection may appear not to have taken.

**Honest verdict: this is a weaker analogue than Postgres 18's.** It reproduces production **join planning** — genuinely useful, and officially sanctioned — but not predicate selectivity, and it cannot reproduce skew. **Don't tell your team it reproduces production plans.** For selectivity you need real data volume.

### Anonymization: an honest gap

**There is no mature open-source equivalent of PostgreSQL Anonymizer for MySQL.** MySQL Enterprise Data Masking is capable but **Enterprise Edition only** (and Oracle's own 9.7 announcement keeps Dynamic Data Masking in Enterprise, contrary to some coverage). **Percona Toolkit has no anonymization tool** — a common misconception; the `pt-` tools do schema change, query digest, checksums, archiving. Greenmask, the credible open-source option, is **PostgreSQL-only**.

So what most teams actually do — and it's fine — is a scripted, idempotent, version-controlled anonymization SQL file run as a mandatory step after every production restore, with a CI check asserting no real email/phone patterns survive. **Two things to get right or the exercise is worthless:** use **consistent pseudonymization** (same input → same output, e.g. `SHA2(col,256)`) so **join cardinality survives** — replacing every value with a fresh random destroys `n_distinct` and changes your plans; and **preserve string lengths**, or you remove all your off-page `TEXT` reads and shrink the table.

**And the highest-fidelity option, which people forget:** capture a real slow log with `long_query_time=0` and **replay your own traffic** against a restored snapshot (`pt-upgrade`, or a custom JDBC harness). sysbench measures the *server*; your own queries measure *your application*. Do both.

---

## 8. A phased study plan

Roughly 8 weeks at a few hours a week, each phase ending in something that exists rather than something you've read.

### Weeks 1–2 — Measurement literacy (before touching a tool)

1. Gregg, [methodology.html](https://www.brendangregg.com/methodology.html) + [usemethod.html](https://www.brendangregg.com/usemethod.html) + the [USE Linux checklist](https://www.brendangregg.com/USEmethod/use-linux.html) — one afternoon. Read the **anti-methods** first; you will recognise yourself.
2. Gil Tene, [How NOT to Measure Latency](https://www.infoq.com/presentations/latency-response-time/) — before you run a single test.
3. k6 docs: [test types](https://grafana.com/docs/k6/latest/testing-guides/test-types/) + [open vs closed](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/) — 30 minutes, authoritative, free.
4. Brooker, [Latency Sneaks Up On You](https://brooker.co.za/blog/2021/08/05/utilization.html) + [Open and Closed, Omission and Collapse](https://brooker.co.za/blog/2023/05/10/open-closed.html).
5. Google SRE [Ch. 4 (SLOs)](https://sre.google/sre-book/service-level-objectives/) and [Ch. 6 (Monitoring)](https://sre.google/sre-book/monitoring-distributed-systems/) — so your test has a pass/fail criterion at all.
6. Gregg's [benchmarking checklist](https://www.brendangregg.com/blog/2018-06-30/benchmarking-checklist.html) — print it.

**Deliverable:** a one-page written SLO for one endpoint (SLI, target percentile, target value, and *why that value*), plus a workload characterization from real production traffic.

### Weeks 3–4 — First honest test, and an audit of your defaults

Install k6. Wire Micrometer + Prometheus + Grafana and the panels from §2 Phase A. Turn on `performance_schema` consumers, the slow log with `log_slow_extra`, and `innodb_print_all_deadlocks`.

Then do the thing that takes an hour and often finds the biggest win in the whole exercise: **audit your pool defaults against §6.** Write down, for your actual service: `maxPerRoute` on every outbound client, `connectionRequestTimeout`, `maximumPoolSize`, `maxLifetime` versus the smallest idle timeout in your network path, `innodb_buffer_pool_size`, and `innodb_redo_log_capacity`. In my experience most services have at least three of these badly wrong, and they're config-line fixes.

**Deliverable:** an average-load test against staging with production-like data, using an **arrival-rate** executor, with a warm-up scenario excluded from thresholds, a `dropped_iterations` threshold, and a Grafana dashboard showing app p99 next to `hikaricp_connections_pending`, the HTTP pool's `pending`, and `Threads_running` on the same time axis. Plus the Phase B sysbench sweeps — `fileio` for the fsync ceiling, `oltp_read_write` for the knee — with both numbers written down.

Work through [k6-learn Module I](https://github.com/grafana-cold-storage/k6-learn) — read-only now, but its tool-agnostic *performance testing principles* module is still the best free structured intro, and principles don't rot.

### Weeks 5–6 — Profiling and the MySQL side

- Learn `async-profiler`: CPU, then **wall-clock**, then alloc, then lock. Memorize the §6.5 decoder ring. Read flame graphs correctly (x-axis is *sorted stacks*, **not** a timeline; width = frequency).
- Learn JFR: `jcmd <pid> JFR.dump name=continuous begin=-30m end=-15m` to extract exactly the bad window from a continuous recording. The single highest-leverage JFR habit.
- Learn **`EXPLAIN ANALYZE`** properly, and specifically: read bottom-up, and **multiply `actual time × loops`.** `(actual time=0.003..0.003 rows=1 loops=10000)` is not 0.003 ms — it's 30 ms and 10,000 index descents. This is the #1 misreading.
  > ⚠️ Two limits to know: `EXPLAIN ANALYZE` **does not support single-table `UPDATE`/`DELETE`** — it returns `-> <not executable by iterator executor>` rather than erroring, so you cannot get actuals for your most common write statements. And it only works with `FORMAT=TREE`.
- Learn **`EXPLAIN FORMAT=TREE FOR CONNECTION <id>`**, which explains a *running* query on a live connection. **This is the closest MySQL gets to catching a plan in the act**, and the only way to see a plan flip under load:
  ```bash
  while true; do
    mysql -N -e "SELECT ID FROM information_schema.PROCESSLIST
                 WHERE COMMAND='Query' AND TIME>2 AND ID<>CONNECTION_ID();" |
    while read id; do
      echo "=== conn $id @ $(date -Is) ==="
      mysql -e "EXPLAIN FORMAT=TREE FOR CONNECTION $id\G" 2>/dev/null
    done
    sleep 1
  done | tee /tmp/live-plans.log
  ```
- Work through [use-the-index-luke.com](https://use-the-index-luke.com/) for indexing fundamentals — but note honestly that **MySQL appears there as side notes, not first-class treatment** (the book primarily uses Oracle terminology). It's still the best explanation of *why* an index works, which is upstream of everything in §5.
- Build the ASH sampler from the appendix and histogram a real load test's waits.

**Deliverable:** one bottleneck found, fixed, and *verified* — with a before/after distribution plot, a differential flame graph, and a written note on whether the measured result matched your prediction.

### Weeks 7–8 — Make it a habit

- Smoke test in CI on every commit; nightly average-load with thresholds as the gate.
- **A query-count-per-endpoint assertion in CI.** Cheapest high-value regression gate you will ever add.
- An overnight soak. Only a soak finds leaks, heap creep, history-list growth, and — crucially — **the idle-timeout connection resets from §6.6**, which get *worse* when traffic is quiet and never appear in a spike test.
- A scalability sweep and a look at whether throughput *flattens* (contention) or *falls* (past the knee). If it falls, stop adding concurrency.
- Write the runbook: how to run each test, where results live, what the thresholds are, what to check first when one fails.

**Deliverable:** a merged CI job and a one-page team runbook.

### Month 3 and beyond

Buy two books and read them properly: **Nichter, *Efficient MySQL Performance*** (explicitly written for *application* engineers — chapters 1, 2, 4, 7 and 8 map almost one-to-one onto §5) and **Gregg, *Systems Performance* 2e** (chapters 2 and 12 alone justify it — the best written treatment anywhere of *how to think about* a performance investigation).

Then subscribe to the **Percona blog RSS** and the **[MySQL 8.4 release notes](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/)**. With quarterly patches, the release notes are the most reliable signal of what changed — and as §5.12 shows, changed defaults invalidate advice.

---

## 9. Resource library

### Tier 0 — free, and you should read all of it

| What | Where | Note |
|---|---|---|
| Gregg's methodology hub | [brendangregg.com/linuxperf.html](https://www.brendangregg.com/linuxperf.html) | Indexes USE, TSA, off-CPU analysis, active benchmarking, flame graphs |
| USE Method | [usemethod.html](https://www.brendangregg.com/usemethod.html) | *"For every resource, check utilization, saturation, and errors."* Extends to **software** resources — locks, thread pools, FD limits. That's where all four of your pools live |
| Thread State Analysis | [tsamethod.html](https://www.brendangregg.com/tsamethod.html) | **The highest-leverage method for your exact situation** |
| Benchmarking checklist | [7 questions](https://www.brendangregg.com/blog/2018-06-30/benchmarking-checklist.html) | Why not double? Was it tuned? Did it break limits? Did it error? Does it reproduce? Does it matter? Did it even happen? |
| Gil Tene, How NOT to Measure Latency | [QCon SF 2015](https://www.infoq.com/presentations/latency-response-time/) | Watch before your first test |
| k6 testing guides | [grafana.com/docs/k6/latest/testing-guides/](https://grafana.com/docs/k6/latest/testing-guides/) | Effectively a free course, and the most current authoritative free material on load-test *design* |
| Google SRE book + Workbook | [sre.google/sre-book](https://sre.google/sre-book/table-of-contents/) · [workbook](https://sre.google/workbook/table-of-contents/) | Book Ch. 4, 6, 22; Workbook Ch. 2, 11, 17 |
| The Tail at Scale | [CACM, free full text](https://cacm.acm.org/research/the-tail-at-scale/) | Dean & Barroso. The paper that made "p99 matters" a discipline |
| **AWS Builders' Library** | [Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) | **Read this before you write a retry.** The whole library is free and several articles cover load shedding and fairness |
| MySQL: `sys` schema | [dev.mysql.com/.../sys-schema.html](https://dev.mysql.com/doc/refman/8.4/en/sys-schema.html) | Already installed. Highest payoff-per-effort of anything here |
| MySQL: EXPLAIN output reference | [explain-output.html](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html) | Read once, start to finish. The `type` ranking and the `Extra` values are the vocabulary |
| MySQL: InnoDB Locking | [innodb-locking.html](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html) + [Locks Set by Different SQL Statements](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html) | **The single most important MySQL page for a JVM developer.** Gap locks, next-key locks, and the "every record the search *encounters*" rule that turns a missing index into a locking bug |
| MySQL: Deadlocks in InnoDB | [innodb-deadlocks.html](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks.html) | The minimization list reads as a code-review checklist |
| Jeremy Cole, InnoDB internals | [blog.jcole.us/innodb/](https://blog.jcole.us/innodb/) | **Live but dormant since Oct 2014** — and still the best explanation of InnoDB's on-disk structures anywhere. The four to read: *B+Tree index structures*, *How does InnoDB behave without a Primary Key?*, *The basics of the InnoDB undo logging and history system*, *Visualizing the impact of ordered vs. random index insertion*. Concepts haven't changed; don't read it for anything version-specific |
| Percona blog | [percona.com/blog](https://www.percona.com/blog/) | **The highest-volume source of substantive MySQL performance writing, period.** Uneven, but the deep posts are often the only public source on a topic |
| Daniel Nichter | [hackmysql.com](https://hackmysql.com/) | Companion to *Efficient MySQL Performance*, with free chapters including the replication-heartbeat material |
| Marco Tusa | [tusacentral.net](https://www.tusacentral.net/joomla/index.php/mysql-blogs) | Rigorous, benchmark-heavy. A good model for *how* to run a load test |
| Vlad Mihalcea | [MySQL category](https://vladmihalcea.com/category/mysql/) | The JPA/Hibernate performance reference. His [rewriteBatchedStatements](https://vladmihalcea.com/mysql-rewritebatchedstatements/), [MySQL JDBC statement caching](https://vladmihalcea.com/mysql-jdbc-statement-caching/), [batching with MySQL](https://vladmihalcea.com/batch-insert-mysql-hibernate/) and [best UUID type for a PK](https://vladmihalcea.com/uuid-database-primary-key/) posts are all directly load-bearing for §5.4 |
| Aleksey Shipilëv | [JVM Anatomy Quarks](https://shipilev.net/jvm/anatomy-quarks/) · [Nanotrusting the Nanotime](https://shipilev.net/blog/2014/nanotrusting-nanotime/) | The best free JVM performance writing. Read *Nanotrusting* before you write any timing code — on the Linux/x86 boxes he measures, `System.nanoTime()` costs ~26 ns with ~26 ns granularity, so his conclusion: **"you are unable to get a direct measurement of anything shorter than 30 ns"** |
| Marc Brooker | [brooker.co.za/blog](https://brooker.co.za/blog/) | The best blog at the queueing/load-testing intersection |

> ⚠️ **Two currency notes.** **lefred.be** is live but **is no longer a MySQL blog** — Frédéric Descamps moved to MariaDB and the site now self-describes as *"tribulations of a MariaDB Community Advocate."* The 434-post MySQL archive stays valuable; don't treat it as a current MySQL 8.4 source. And the **MySQL Server Team blog moved**: `dev.mysql.com/blog-archive/` is now historical; current first-party engineering content is at [blogs.oracle.com/mysql](https://blogs.oracle.com/mysql/). Update your feeds.

### Books, ranked by what to buy first

| Book | Verdict |
|---|---|
| **Nichter, *Efficient MySQL Performance* (O'Reilly, 2021)** | ⭐ **Start here, and it isn't close.** Explicitly written for *application engineers*, not DBAs — the framing is "you have a query and an access pattern, what do you do." Chapters: Query Response Time, Indexes and Indexing, Data, Access Patterns, Sharding, Server Metrics, Replication Lag, Transactions. Its opening thesis — *performance is query response time* — is exactly the mental model you need. No 2nd edition exists |
| **Gregg, *Systems Performance*, 2nd ed. (2020)** | **The one general-purpose book to buy.** Still current; no 3rd edition. Ch. 2 (Methodology) and Ch. 12 (Benchmarking) are the best written treatment of how to think about a performance investigation, and nothing else combines the methodology catalogue with real per-subsystem depth |
| **Krogh, *MySQL 8 Query Performance Tuning* (Apress, 2020)** | ⭐ **The most directly on-topic book for §2–§5.** The deepest available treatment of Performance Schema, sys schema, `EXPLAIN`/`EXPLAIN ANALYZE`, optimizer trace, histograms, and index statistics. Written against 8.0, so it predates 8.4's changed defaults — the *methods* transfer, the *defaults* don't |
| **Krogh, *MySQL Concurrency* (Apress, 2021)** | Excellent and narrow: locks, transactions, isolation levels, deadlock analysis, metadata locks. **Buy it when §5.9 stops being enough**, which for a database-heavy service is a matter of time |
| **Botros & Tinley, *High Performance MySQL*, 4th ed. (2021)** | Second general MySQL purchase. **It has a dedicated Performance Schema chapter, which the 3rd edition entirely lacked** — that alone justifies it. More operational/SRE-flavoured than its predecessor |
| **Schwartz, Zaitsev & Tkachenko, *High Performance MySQL*, 3rd ed. (2012)** | **Yes — still worth owning, and here's the verified reason.** The 4th edition is a substantially *different* book that shares a title. TOC diff: the 4th **dropped** ch. 2 *Benchmarking MySQL*, ch. 3 *Profiling Server Performance*, ch. 7 *Advanced MySQL Features*, ch. 14 *Application-Level Optimization*, and appendices **D *Using EXPLAIN*** and **E *Debugging Locks***. So the 3rd has unique content the 4th does not — an entire chapter on benchmarking methodology, one on profiling, and an EXPLAIN appendix. Caveat: it's MySQL 5.5-era, so **buy it for the reasoning and never trust a number in it** |
| **Nygard, *Release It!*, 2nd ed. (2018)** | **Belongs on a load-testing list because it gives you the hypothesis list.** When your stress test degrades, its antipattern catalogue tells you what to look for — and **Blocked Threads** and **Unbounded Result Sets** are exactly §6 and §5.6, neither of which shows up in a CPU profile. [Free antipatterns chapter](https://media.pragprog.com/titles/mnee2/antipatterns.pdf) |
| **Kleppmann & Riccomini, *Designing Data-Intensive Applications*, 2nd ed. (March 2026)** | The 2nd edition shipped March 2026 with a new co-author; the 1st is superseded. Its Ch. 2 ("Defining Nonfunctional Requirements") treatment of response time and percentiles is one of the best short introductions to §1 here |
| **Beckwith, *JVM Performance Engineering* (2024)** | The most current JVM performance book, by a long-time OpenJDK performance engineer. Modern GCs including generational ZGC, unified logging, virtual threads and their performance implications |
| **Petrov, *Database Internals* (2019)** | Not MySQL-specific and not about tuning, but it's what converts "the DB is slow" into a mechanism — B-tree page splits, buffer-pool eviction, latch vs lock, WAL/fsync as the serial bottleneck. Deprioritize until after the two starters |

> ⚠️ **A correction worth making explicitly, since it circulates:** there is no Krogh book titled *MySQL Performance Schema in Action*. His page lists four books and none by that name. And **MySQL Cookbook** is not his — I believe the current edition is by Smirnova and Tezuysal, but I did not verify that attribution, so check before citing it.

### Hands-on

- **[JMH samples](https://github.com/openjdk/jmh)** — 36 progressively-numbered samples (up to 39, with gaps), each teaching exactly one benchmarking pitfall: dead-code elimination, constant folding, state scopes, blackholes, false sharing, JIT warmup, fork isolation.
- **[HdrHistogram plotter](http://hdrhistogram.github.io/HdrHistogram/plotFiles.html)** — paste histogram logs, get percentile-distribution overlays. This is how you show a before/after honestly.
- **Boot the actual MySQL version and ask it.** Every `[verified 8.4.11]` fact in this document came from ~15 minutes of work, and it caught three errors in a well-researched brief:
  ```bash
  curl -sLO https://dev.mysql.com/get/Downloads/MySQL-8.4/mysql-8.4.11-linux-glibc2.28-x86_64-minimal.tar.xz
  tar -xJf mysql-8.4.11-*.tar.xz && cd mysql-8.4.11-*/
  ./bin/mysqld --no-defaults --verbose --help | less     # every compiled default
  ./bin/mysqld --no-defaults --initialize-insecure --datadir=/tmp/d --basedir=$PWD
  ./bin/mysqld --no-defaults --user=$(whoami) --datadir=/tmp/d --basedir=$PWD --socket=/tmp/m.sock &
  mysql --socket=/tmp/m.sock -uroot                      # now test your own claims
  ```
  **Make this a habit.** For any default or behavioural claim, ask the version you actually run — including the claims in this document.

### The honest gaps in the MySQL ecosystem

Worth naming, because pretending otherwise wastes your time:

1. **No `auto_explain`.** No way to have the server record a plan alongside a slow query. Substitute: `log_slow_extra` + `pt-query-digest` + `EXPLAIN FOR CONNECTION`. Percona Server's `log_slow_verbosity=query_plan` (per-query `Full_scan`/`Filesort_on_disk`/`Merge_passes` flags) and `=innodb` (**`InnoDB_pages_distinct`** — the only real buffers-touched-per-query metric that exists in the MySQL family) get materially closer. **If plan capture matters to your team, that's the strongest argument for Percona Server.**
2. **No plan visualizer or critique tool** comparable to explain.depesz.com or pgMustard.
3. **No Active Session History.** You build the 1 Hz sampler yourself (appendix). Percona PMM is the closest hosted equivalent.
4. **No real buffers-per-query metric upstream.** `rows_examined/rows_sent` is the right *first* metric and catches the dominant failure mode, but it's **row-level, not page-level**: 1,000 lookups on 3 hot pages and 1,000 lookups across 1,000 pages both report `rows_examined=1000`, which in Postgres would be wildly different buffer counts. And `rows_sent` is a bad denominator for aggregates. **Always read it alongside `SUM_SELECT_SCAN` and `SUM_NO_INDEX_USED`, never alone.**
5. **No podcast or newsletter equivalent to Postgres FM.** This asymmetry is real and worth naming — the Postgres community has invested far more in accessible, current, practitioner-oriented content. The substitute is: Percona blog RSS, Percona Live talks on YouTube, the two Krogh books, and reading `dev.mysql.com` release notes directly.
6. **No mature open-source anonymizer** (§7).

---

## 10. The checklist to pin above your desk

**Gregg's seven questions, verbatim:**

1. **Why not double?** — What limits it?
2. **Was it tuned?** — Were *both* client and target configured like production?
3. **Did it break limits?** — Sanity-check against physical ceilings. If you "achieved" more than the wire allows, you measured a cache.
4. **Did it error?** — Errors take faster code paths and silently inflate throughput. *A 503 returned in 2 ms will make your p99 look fantastic.*
5. **Does it reproduce?** — Run it repeatedly.
6. **Does it matter?** — Does the benchmark resemble real usage?
7. **Did it even happen?** — Gregg's example: a firewall silently blocked the traffic, so "latency was the time it took the client to time out."

**Harness hygiene:**

- [ ] Load generator on a **different host** from the SUT, in the same region as real clients. Never localhost.
- [ ] **Keep-alive on.** Without it you're measuring TCP+TLS handshakes and burning ephemeral ports (~28,000 per src→dst tuple, held 60 s by TIME_WAIT).
- [ ] `ulimit -n` raised on **both** sides. The 1024 default presents as a silent plateau.
- [ ] `net.core.somaxconn` **and** `accept-count` both set — the smaller silently wins.
- [ ] Bandwidth arithmetic done in advance. 10k rps × 20 KB = 1.6 Gbps saturates a 1 Gbps link. (And many cloud instance types burst-then-throttle.)
- [ ] **Autoscaling and cron jobs disabled.**
- [ ] Warm-up excluded from assertions, and warm-up completion *verified* — including crossing two checkpoint intervals.
- [ ] Offered rate reported alongside achieved rate. If they differ, the run is invalid.
- [ ] `dropped_iterations` thresholded at zero.
- [ ] Error rate **and error type** tracked — and retry behaviour understood.
- [ ] p99 disaggregated **per instance**, not just in aggregate.
- [ ] `max` reported, always. Percentiles from histograms, never averaged across instances.
- [ ] `--rand-type` recorded for any sysbench number you quote.
- [ ] Full provenance: git SHA, JVM flags, JDK build, **MySQL version + full non-default variable set**, dataset snapshot, generator version.
- [ ] Exactly **one** change per iteration.

**MySQL pre-flight:**

- [ ] `innodb_buffer_pool_size` is **not** 128 MiB.
- [ ] `innodb_redo_log_capacity` is **not** 100 MiB.
- [ ] `innodb_print_all_deadlocks = ON`.
- [ ] `performance_schema` wait consumers, `wait/synch` instruments, **and `events_statements_cpu`** enabled for the run.
- [ ] **`SET GLOBAL innodb_monitor_enable='module_log'`** — otherwise checkpoint age reads a healthy-looking 0.
- [ ] Any `INNODB_METRICS` query selects `STATUS` alongside `COUNT`.
- [ ] Slow log on with `long_query_time=0` and `log_slow_extra=ON`, output to **FILE**.
- [ ] `pg_stat`-equivalent reset done: `CALL sys.ps_truncate_all_tables(FALSE)` and `TRUNCATE ...summary_by_digest`.
- [ ] `ANALYZE TABLE` run after loading data; histograms created on skewed non-indexed filter columns.
- [ ] `innodb_lock_wait_timeout` lowered for the web-facing DataSource.
- [ ] `max_digest_length` raised if your ORM emits long SQL — **read-only, so my.cnf plus a restart.**
- [ ] ASH sampler sanity-checked: one slow query in one session should read AAS = 1.
- [ ] No `SELECT 1` health-check query polluting the digest table.

**Pool pre-flight (§6) — the one most people skip:**

- [ ] Outbound `maxPerRoute` raised from **5**, and sized by Little's Law against the *downstream's* capacity.
- [ ] `connectionRequestTimeout` / `pendingAcquireTimeout` lowered from **3 min / 45 s** to ~200 ms.
- [ ] Reactor Netty `maxIdleTime` set (it is **-1 = never** by default).
- [ ] Idle eviction enabled on Apache HC5 (**off** by default).
- [ ] **Client idle timeout < LB/server idle timeout**, everywhere, with margin.
- [ ] Hikari `maxLifetime` below the smallest idle timeout in the path (NLB's 350 s, not `wait_timeout`'s 8 h).
- [ ] Hikari `connectionTimeout` lowered from 30 s.
- [ ] `connectionTestQuery` **deleted**.
- [ ] Connector/J `socketTimeout` and `connectTimeout` set (both default to **0 = infinite**).
- [ ] `server.tomcat.mbeanregistry.enabled=true`, or your Tomcat thread metrics are silently absent.
- [ ] `server.tomcat.max-connections` reduced from 8192 to a small multiple of `threads.max`.
- [ ] Pool metric binders **registered** — Spring Boot does not do it for you.
- [ ] `ListenOverflows` on the dashboard, from node_exporter.

---

## Appendix — copy-paste kit

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
  // spread across the table, and SKEW it (Zipf-ish) rather than uniform
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
# The one to run when p99 is bad but CPU looks idle — off-CPU analysis for the JVM.
# Then use the §6.5 decoder ring on the parked frames.
asprof -e wall -t -i 50ms -d 60 -f /tmp/wall.html <pid>

asprof -d 30 -f /tmp/cpu.html <pid>                         # CPU flame graph
asprof -e alloc --alloc 512k -d 60 -f /tmp/alloc.html <pid> # allocation churn
asprof -e lock --lock 10ms -d 60 -f /tmp/lock.jfr <pid>     # contention
asprof -e ctimer -d 30 -f /tmp/cpu.html <pid>               # container without perf access

# JFR: keep a continuous recording, extract exactly the bad window afterwards
jcmd <pid> JFR.dump name=continuous begin=-30m end=-15m filename=/tmp/window.jfr
```

Know which heap problem you have: **retention** (heap grows and doesn't come back) → heap dump + Eclipse MAT. **Churn** (heap fine, GC burns 20% of CPU) → allocation profiling. Churn is the far more common load-test finding, and a heap dump is nearly useless for it because the garbage is already collected.

### MySQL: the four queries you'll run most

```sql
-- 1. Top statements. Run it three times: by SUM_TIMER_WAIT, by COUNT_STAR, by tmp_DISK.
--    NOTE: all TIMER columns are in PICOSECONDS. /1e9 = ms, /1e12 = s.
SELECT SCHEMA_NAME                                            AS db,
       COUNT_STAR                                             AS calls,
       ROUND(SUM_TIMER_WAIT/1e9, 1)                           AS total_ms,
       ROUND(AVG_TIMER_WAIT/1e6, 1)                           AS avg_us,
       ROUND(QUANTILE_99/1e6, 1)                              AS p99_us_est,
       ROUND(SUM_CPU_TIME/1e9, 1)                             AS cpu_ms,
       ROUND(SUM_LOCK_TIME/1e9, 1)                            AS lock_ms,
       SUM_ROWS_SENT, SUM_ROWS_EXAMINED,
       ROUND(SUM_ROWS_EXAMINED/GREATEST(SUM_ROWS_SENT,1), 1)  AS exam_per_sent,
       SUM_NO_INDEX_USED                                      AS no_index,
       SUM_SELECT_SCAN                                        AS full_scans,
       SUM_SELECT_FULL_JOIN                                   AS full_joins,
       SUM_CREATED_TMP_DISK_TABLES                            AS tmp_DISK,
       SUM_SORT_MERGE_PASSES                                  AS merge_passes,
       LEFT(DIGEST_TEXT, 120)                                 AS query
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME IS NOT NULL
ORDER BY SUM_TIMER_WAIT DESC LIMIT 20;
```

What BAD looks like: `exam_per_sent > ~100` (scanning 100 rows to return 1); `no_index = calls` (every execution used no index — missing index, guaranteed); **`full_joins` non-zero at all** (a join with no usable index on the inner table — O(n·m)); **`merge_passes` non-zero** (a filesort spilled to disk — the only reliable per-query signal upstream MySQL gives you); `lock_ms > 20% of total_ms` (contention, not query cost); `p99/avg > 10` (bimodal — cache miss, lock wait, or plan flip); `cpu_ms ≪ total_ms` (waiting, not computing).

> ⚠️ Three caveats on that query, all verified:
> - **`QUANTILE_99` is documented as *"a high estimate, computed from the histogram data"*** — the upper edge of a bucket. Don't present it as an exact p99.
> - **`cpu_ms` is 0 for every row unless the `events_statements_cpu` consumer is enabled**, and it is **OFF by default**. On a stock server the "`cpu_ms ≪ total_ms` = waiting, not computing" reading is a guaranteed false positive — *every* query looks like it's waiting. Enable it in Phase A first. (The units aren't documented; picoseconds is verified empirically, so `/1e9` is right.)
> - **`WHERE SCHEMA_NAME IS NOT NULL` silently drops statements issued with no default schema.** Usually that's the admin noise you want gone, but if a service connects without a database in the URL, its queries vanish from this list.

```sql
-- 2. Wait classes. A 5-row answer that usually tells you which subsystem to blame.
SELECT * FROM sys.wait_classes_global_by_latency;
-- then drill in:
SELECT * FROM sys.waits_global_by_latency LIMIT 20;
```

`wait/synch/*` in the top three = internal contention → **more concurrency will not help; reduce the pool.** (Invisible unless you enabled `wait/synch` — §2 Phase A.)

```sql
-- 3. Who is blocking whom. Read `blocking_state`: if it's LOCK WAIT, that transaction
--    is itself blocked — follow the chain to the row whose state is RUNNING.
SELECT r.trx_id AS waiting_trx, r.trx_mysql_thread_id AS waiting_conn,
       TIMESTAMPDIFF(SECOND, r.trx_wait_started, NOW()) AS wait_s,
       SUBSTRING(r.trx_query, 1, 60)                    AS waiting_query,
       b.trx_id AS blocking_trx, b.trx_mysql_thread_id AS blocking_conn,
       b.trx_state AS blocking_state,
       TIMESTAMPDIFF(SECOND, b.trx_started, NOW())      AS blocking_trx_age_s,
       COALESCE(SUBSTRING(b.trx_query,1,60), '<<IDLE IN TRANSACTION>>') AS blocking_query,
       bl.OBJECT_NAME, bl.INDEX_NAME, bl.LOCK_TYPE, bl.LOCK_MODE, bl.LOCK_DATA,
       CONCAT('KILL ', b.trx_mysql_thread_id)           AS remedy
FROM performance_schema.data_lock_waits w
JOIN performance_schema.data_locks  bl ON bl.ENGINE_LOCK_ID = w.BLOCKING_ENGINE_LOCK_ID
JOIN information_schema.INNODB_TRX  r  ON r.trx_id = w.REQUESTING_ENGINE_TRANSACTION_ID
JOIN information_schema.INNODB_TRX  b  ON b.trx_id = w.BLOCKING_ENGINE_TRANSACTION_ID
ORDER BY wait_s DESC;

-- The one-liner version, which generates its own KILL statements:
SELECT wait_age, locked_table, locked_index, locked_type, waiting_query,
       sql_kill_blocking_query FROM sys.innodb_lock_waits ORDER BY wait_age DESC;
```

> ⚠️ `data_lock_waits` has **no** `OBJECT_SCHEMA`/`OBJECT_NAME`/`LOCK_MODE` columns — you must join to `data_locks` for those. And in `LOCK_MODE`, `,GAP` means a gap lock and `,REC_NOT_GAP` means record-only (what you want). **Seeing `,GAP` a lot is the empirical argument for READ COMMITTED** (§5.9).

```sql
-- 4. Saturation, in one shot
SHOW GLOBAL STATUS WHERE Variable_name IN
 ('Threads_running','Threads_connected','Threads_created','Aborted_clients',
  'Innodb_buffer_pool_reads','Innodb_buffer_pool_wait_free','Innodb_log_waits',
  'Innodb_row_lock_waits','Innodb_row_lock_time_avg','Innodb_row_lock_current_waits',
  'Created_tmp_tables','Created_tmp_disk_tables','Select_scan','Select_full_join',
  'Sort_merge_passes','Handler_read_rnd_next','Handler_read_key');

-- NOTE the STATUS column. 240 of 314 INNODB_METRICS are DISABLED by default and
-- return COUNT=0 rather than erroring. log_lsn_checkpoint_age is one of them.
SELECT NAME, COUNT, STATUS FROM information_schema.INNODB_METRICS
 WHERE NAME IN ('trx_rseg_history_len','log_lsn_checkpoint_age');
-- if STATUS='disabled':  SET GLOBAL innodb_monitor_enable = 'module_log';
```

Key readings: **`Innodb_buffer_pool_wait_free` rising at all** is the best "buffer pool too small / flushing can't keep up" signal. **`Innodb_log_waits` non-zero** means raise `innodb_log_buffer_size`. **`Handler_read_rnd_next` within an order of magnitude of `Handler_read_key`** means you're scanning. And **don't use the buffer-pool hit ratio** — it's cumulative since boot, asymptotically approaches 100% no matter what happens now, and 99.9% of 500k requests/s is still 500 physical reads/s. Use `Innodb_buffer_pool_reads` **per second** against your measured disk ceiling instead.

### MySQL: build your own Active Session History

MySQL has no ASH. This is the direct equivalent of sampling `pg_stat_activity`, and it's worth the 20 minutes.

> ⚠️ **Prerequisite:** the `events_waits_current` consumer must be ON, or `wait_event` is `NULL` on every single row and the histogram below returns nothing but `[state] …` buckets. Enable it per §2 Phase A first.

```sql
CREATE TABLE perf.ash (
  ts TIMESTAMP(3) NOT NULL, thd_id BIGINT UNSIGNED, conn_id BIGINT UNSIGNED,
  user VARCHAR(128), db VARCHAR(64), command VARCHAR(32), state VARCHAR(64),
  trx_state VARCHAR(32), wait_event VARCHAR(128), digest VARCHAR(64), sql_text TEXT,
  KEY (ts), KEY (wait_event), KEY (digest)
) ENGINE=InnoDB;
```

```sql
-- ash_sample.sql — only rows actually doing something.
-- NOTE the two guards, both of which I got wrong the first time:
--   (a) events_waits_current holds a NESTED STACK of rows per thread, so a naive
--       LEFT JOIN emits 2+ rows per session and inflates every count. Take the
--       innermost (highest EVENT_ID) wait only.
--   (b) exclude background 'Daemon' threads, or they count as active sessions.
INSERT INTO perf.ash
SELECT NOW(3), t.THREAD_ID, t.PROCESSLIST_ID, t.PROCESSLIST_USER, t.PROCESSLIST_DB,
       t.PROCESSLIST_COMMAND, t.PROCESSLIST_STATE, trx.STATE, w.EVENT_NAME, st.DIGEST,
       LEFT(t.PROCESSLIST_INFO, 512)
FROM performance_schema.threads t
LEFT JOIN performance_schema.events_waits_current w
       ON w.THREAD_ID = t.THREAD_ID
      AND w.EVENT_ID = (SELECT MAX(w2.EVENT_ID)                        -- ← (a)
                          FROM performance_schema.events_waits_current w2
                         WHERE w2.THREAD_ID = t.THREAD_ID)
LEFT JOIN performance_schema.events_transactions_current trx ON trx.THREAD_ID = t.THREAD_ID
LEFT JOIN performance_schema.events_statements_current  st  ON st.THREAD_ID = t.THREAD_ID
WHERE t.PROCESSLIST_ID IS NOT NULL
  AND t.PROCESSLIST_ID <> CONNECTION_ID()
  AND t.PROCESSLIST_COMMAND <> 'Daemon'                                -- ← (b)
  AND (t.PROCESSLIST_COMMAND <> 'Sleep' OR trx.STATE = 'ACTIVE');
```

```bash
# Drive it from the shell, not an EVENT — you want it outside the server's scheduler
end=$((SECONDS+900))
while [ $SECONDS -lt $end ]; do
  mysql -h db -e "SOURCE /opt/ash_sample.sql" 2>/dev/null
  sleep 1
done
```

```sql
-- The payoff: a wait histogram for your load-test window
SELECT COALESCE(wait_event, CONCAT('[state] ', COALESCE(state,'?'))) AS waited_on,
       COUNT(*) AS samples,
       ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (), 1) AS pct,
       COUNT(DISTINCT digest) AS distinct_queries
FROM perf.ash WHERE ts BETWEEN ? AND ?
GROUP BY waited_on ORDER BY samples DESC LIMIT 25;

-- Average Active Sessions — the best single saturation number, directly comparable
-- to cores. COUNT(DISTINCT conn_id), not COUNT(*): see guard (a) above.
SELECT DATE_FORMAT(ts,'%Y-%m-%d %H:%i:%s') AS sec,
       COUNT(DISTINCT conn_id) AS active_sessions
FROM perf.ash GROUP BY sec ORDER BY sec;
-- AAS sustained > cores  =>  saturated
```

**Sanity-check the sampler before you trust it:** run one deliberately slow query in a single session and confirm AAS reads **1**, not 3 or 4. If it's inflated, one of the two guards above is missing.

### MySQL: the EXPLAIN habit

```sql
EXPLAIN ANALYZE SELECT ...;                    -- TREE format only; no single-table UPDATE/DELETE
EXPLAIN FORMAT=TREE  SELECT ...;               -- the only format that shows hash join usage
EXPLAIN FORMAT=JSON  SELECT ...;               -- cost_info, used_columns, attached_condition
EXPLAIN FORMAT=TREE FOR CONNECTION 44;         -- a LIVE query. Your plan-flip catcher.
```

Four things to look at:

1. **`actual time` × `loops`.** `actual time=A..B` is *first-row..last-row*, in ms, and it is the **average per loop**, not the total. `(actual time=0.002..0.003 rows=1 loops=50000)` is ~133 ms, not 0.003 ms. **This is the #1 misreading.** Times are cumulative and inclusive of children, so subtract children for a node's own cost.
2. **`rows` (estimate) vs `actual rows`.** A 10×+ divergence means bad statistics. Read **bottom-up** and find the *deepest* node where the estimate first goes wrong — everything above inherits the error.
3. **`possible_keys` non-empty with `key: NULL`** — an index existed and was rejected. Usually statistics, a type/collation mismatch (§5.3), or low selectivity.
4. **`Extra`**: `Using index` and `Using index condition` are **good**. `Using filesort`, `Using temporary`, and especially `Using join buffer (hash join)` and `Range checked for each record` are trouble.

When `EXPLAIN` won't tell you *why* an index was rejected, the optimizer trace will — and it's a last resort, not a routine tool:

```sql
SET SESSION optimizer_trace = 'enabled=on';
SET SESSION optimizer_trace_max_mem_size = 1048576;   -- ⚠️ this IS the default (not 16384)
SELECT /* your query */ ...;
SELECT TRACE, MISSING_BYTES_BEYOND_MAX_MEM_SIZE FROM information_schema.OPTIMIZER_TRACE\G
SET SESSION optimizer_trace = 'enabled=off';
```

**Always check `MISSING_BYTES_BEYOND_MAX_MEM_SIZE` — non-zero means your trace is truncated and possibly misleading.** Look at `rows_estimation` and `considered_execution_plans` for the rejection reason (`"cause": "cost"`, `"chosen": false`, `"usable": false`).

### Connector/J: a defensible starting URL

```
jdbc:mysql://db.internal:3306/app
  ?connectTimeout=3000
  &socketTimeout=10000                  # ← BOTH default to 0 = INFINITE. Always set them.
  &cachePrepStmts=true
  &prepStmtCacheSize=500                # default 25
  &prepStmtCacheSqlLimit=2048           # default 256 — well below ORM statement lengths
  &useServerPrepStmts=false             # the default; see §5.5 before flipping it
  &rewriteBatchedStatements=true        # default false; the 8x win for INSERT
  &useLocalSessionState=true            # fewer round trips; safe IF you never set session
                                        #   state via raw SQL
  &cacheServerConfiguration=true        # saves 2 queries per NEW connection
  &maintainTimeStats=false              # default is true, and true is the wrong choice
  &ApplicationName=orders-api           # shows up in pg_stat_activity's equivalent. Free.
  &sslMode=VERIFY_IDENTITY
  &sessionVariables=innodb_lock_wait_timeout=3
```

> ⚠️ **`useLocalTransactionState` is not in this list on purpose.** It's in neither HikariCP's nor Oracle's recommended block. It uses a protocol flag to decide whether to actually send `COMMIT`/`ROLLBACK` — and when the flag is wrong (a known class of bug, and any proxy in the path), a commit is **silently skipped**. Saving one round trip is not worth "sometimes doesn't commit."
>
> ⚠️ **`elideSetAutoCommits`** is in both recommended blocks and is generally worth setting — **but** [MySQL Bug #66884](https://bugs.mysql.com/bug.php?id=66884) (Verified, still open) reports the underlying server flag isn't initialised correctly when mysqld starts with `autocommit=0`. If your server does that, leave it off.

### The pool config that fixes the defaults

```properties
# ── Inbound ─────────────────────────────────────────────────────────────
server.tomcat.threads.max=400
server.tomcat.max-connections=1000            # from 8192
server.tomcat.accept-count=100
server.tomcat.mbeanregistry.enabled=true      # or Tomcat metrics are silently absent

# ── DB pool ─────────────────────────────────────────────────────────────
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.connection-timeout=2000       # from 30000
spring.datasource.hikari.max-lifetime=280000           # < NLB's 350s, not wait_timeout's 8h
spring.datasource.hikari.keepalive-time=120000
spring.datasource.hikari.leak-detection-threshold=20000
# and NO connection-test-query

# ── Outbound (Boot 4.x property names; 3.4/3.5 use spring.http.client.* singular) ──
spring.http.clients.connect-timeout=500ms
spring.http.clients.read-timeout=2s
```

```bash
# ── OS ──────────────────────────────────────────────────────────────────
cat >/etc/sysctl.d/99-http.conf <<'EOF'
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.ip_local_port_range = 10240 65535
net.ipv4.tcp_tw_reuse = 1        # note: modern kernels default to 2 (loopback only),
                                 # so this is a widening, not a change from 0
EOF
sysctl --system
# K8s note: somaxconn is a "safe" sysctl on modern kubelets;
#           tcp_max_syn_backlog is NOT namespaced and must be set on the node.
```

```bash
# ── The invisible-queue sampler. Run this alongside every load test. ────
while :; do
  printf '%s ' "$(date +%T)"
  ss -lnt 'sport = :8080' | awk 'NR==2{printf "acceptq=%s/%s ", $2, $3}'
  nstat -az TcpExtListenOverflows | awk 'NR==2{printf "overflows=%s\n", $2}'
  sleep 1
done
```

---

## 11. Notes on currency, and what I could not verify

Everything above was checked against primary sources in July 2026, and the MySQL defaults were read from a live 8.4.11 instance. A few points are version-sensitive or unverifiable, and you should confirm them against your own environment rather than trusting this document.

**Seven claims that circulate widely and are wrong.** Each was tested on a live 8.4.11 instance (or, for the Java ones, read out of the actual jar), and each was in an earlier draft of this document before testing killed it. They are listed here because you will meet all seven in blog posts.

1. **`innodb_buffer_pool_size` does not auto-size in 8.4.** It's still 128 MiB. Auto-sizing requires `innodb_dedicated_server=ON`, which is **OFF** by default.
2. **`utf8mb4_general_ci` vs `utf8mb4_0900_ai_ci` is a hard error**, not silent index loss — `ERROR 1267: Illegal mix of collations`. The genuinely silent killers are cross-*charset* joins, explicit `COLLATE` in predicates, and above all **string↔number implicit conversion** (§5.3).
3. **`Innodb_history_list_length` is not a status variable** on upstream MySQL. `SHOW GLOBAL STATUS LIKE 'Innodb_history_list_length'` returns zero rows. Use `INNODB_METRICS.trx_rseg_history_len`.
4. **The effective internal-temp-table limit is not `MIN(tmp_table_size, max_heap_table_size)`.** That's the MEMORY engine's rule, and MEMORY is not the default. Under `TempTable`, **`tmp_table_size` alone governs** (§5.12).
5. **`BLOB`/`TEXT` columns do not force internal temp tables to disk** on 8.4 — `TempTable` supports them, and the manual says so explicitly. Another MEMORY-era fact (§5.13).
6. **`Created_tmp_disk_tables` does not under-report at 8.4 defaults** — the documented mmap limitation can't bite because `temptable_max_mmap = 0`. The manual page contradicts itself on this (§5.13).
7. **Embedded Tomcat's `connectionTimeout` is 60 s, not 20 s.** `SocketProperties` initialises the field to 20000, so reading only that file gives the wrong answer; `AbstractHttp11Protocol`'s constructor then overwrites it with 60000 (§6.2).

**And one failure mode worth its own line, because it produces a confident wrong reading rather than an error:** **240 of 314 `INNODB_METRICS` rows are disabled by default and return `COUNT = 0`**, including `log_lsn_checkpoint_age`. Enable `module_log` and always select `STATUS`. This is the exact shape of mistake this document is otherwise about avoiding.

**Version landscape, mid-2026:** **8.4 LTS is current** (8.4.11, released 2026-07-28; premier support to 2029-04-30). **MySQL 8.0 is EOL as of 2026-04-30** — any 8.0-specific advice is now legacy. **9.7 is a new LTS** (9.7.0 GA **2026-04-21** per MySQL's own release notes; 9.7.2 is current, released the same day as 8.4.11). Its headline performance feature is the **Hypergraph Optimizer** in Community Edition — cost-based join enumeration with bushy plans, off by default, with Oracle reporting ~4× on their example while cautioning that *"some workloads will see dramatic improvements, others will see little or no difference."* If you have complex multi-table joins that's the strongest reason to plan a 9.7 move; for simple OLTP point queries it will do nothing.

**Two 8.4 upgrade traps** worth checking before you load-test anything: `mysql_native_password` is **disabled by default**, which breaks old Connector/J and some proxies; and if your `my.cnf` sets `transaction_write_set_extraction` or `binlog_transaction_dependency_tracking` (both **removed**), **8.4 will refuse to start.**

**Autosized values depend on the machine.** My verification box was 2 cores / 7 GiB / `open_files_limit=4096`. Values that will differ on yours: `innodb_buffer_pool_instances`, `innodb_purge_threads`, `innodb_page_cleaners`, `thread_cache_size`, and `table_open_cache` / `table_definition_cache` (both **clamped by `open_files_limit`** — grep your error log for `MY-010142`/`MY-010139`; in containers this bites constantly, and the fix is the container's `nofile` ulimit, not the MySQL variable). Always confirm on your own instance.

**Could not verify — close these before relying on them:**

- **Exact doc wording for the `sort_buffer_size` / `join_buffer_size` per-session warnings.** The defaults (262144 each) and the allocation semantics in §5.12 are correct; but `server-system-variables.html` is ~2 MB and truncated on every fetch, so **don't put quotation marks around a doc sentence for those two** without re-reading the page.
- **Whether MariaDB has a true `auto_explain` analogue** via `log_slow_verbosity`. My claim that *upstream MySQL* has none is solid; MariaDB is unchecked, and if it does, that's a notable point in its favour.
- **Percona Server's `Innodb_history_list_length` status variable** — widely reported, no Percona binary available to test.
- **The `Threads_running` ≈ 2–4× cores saturation threshold** (§6.4) is received wisdom, not documented. The *metric* is right; establish the *threshold* empirically.
- **Resilience4j 2.4.0's release date** — its GitHub releases page rendered "March 14, 2024" alongside a Spring Boot 4 support note, which cannot both be true. Version verified; date not.
- **OkHttp's precise sync-vs-async `maxRequestsPerHost` gating semantics** — worth re-reading `Dispatcher.kt` before making a strong claim.
- **`MySQL Cookbook` authorship** (§9) — I believe the current edition is Smirnova & Tezuysal, not Krogh, but did not confirm it.
- **Performance Schema overhead percentages.** No authoritative figure exists that I could find. Any specific number you see online is unsourced.
- **`setup_instruments` per-class counts** in §2 Phase A are empirical from 8.4.11 on a 2-core box and can drift by patch release.

**Deliberately opinionated, and argued rather than asserted:** the k6-over-Gatling recommendation; the "halve the pool as a probe" heuristic; the `useServerPrepStmts=false` default; and the READ COMMITTED recommendation — which I've deliberately presented alongside Marco Tusa's counter-argument that explicit locking beats loosening isolation. A knowledgeable colleague may reasonably land elsewhere on any of them.

**And the habit that matters most:** for any default or behavioural claim — including the ones in this document — **boot the version you actually run and ask it.** It takes fifteen minutes, and it caught three errors here.

