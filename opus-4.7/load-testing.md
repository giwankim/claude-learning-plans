---
title: "Load Testing for Spring Boot + Kotlin"
category: "Performance & Optimization"
description: "Load testing as a queueing-theory experiment for Spring Boot 3.5+ on the JVM — Gatling (Kotlin DSL) primary, k6 secondary, ghz for gRPC, vegeta for CLI, kafka-*-perf-test and xk6-kafka for Kafka, with deep coverage of percentile math, open-vs-closed loop, and coordinated omission"
---

# Load testing for the Spring Boot + Kotlin engineer

You are about to enter a field where the most common failure mode is not bad tools, but **measurements that look correct and aren't**. Before any tool comparison: a load test is an experiment in queueing theory whose four ingredients are a controlled arrival process, joint measurement of (latency, throughput, errors), the full latency *distribution* (not averages), and end‑to‑end observability of the system under test. Every antipattern in this guide violates one of those four. Every tool we will examine is a different choice in how to instrument them. For your specific stack — Spring Boot 3.5+ on the JVM with a Kotlin codebase, predominantly REST and gRPC, with WebSocket and Kafka in the mix — the answer at the end will be **Gatling (Kotlin DSL) as your primary, k6 as your secondary, ghz for gRPC smoke tests, vegeta for quick CLI experiments, and `kafka-*-perf-test` plus `xk6-kafka` for Kafka**. The rest of this document explains *why* in enough depth that you can defend the choice and revisit it when your context changes.

---

## 1. The conceptual landscape

### What the seven test types actually mean

The vocabulary is loose in the wild, but Grafana's k6 documentation has effectively standardised it. A **smoke test** is a one-to-five-VU run that takes seconds, executed every time the script or the system code changes; its purpose is twofold — verify the test script itself works, and produce a baseline against which future runs are diff'd. It does *not* measure capacity. A **load test** (also "average-load test") simulates the expected production traffic with deliberate ramp-up, steady-state, and ramp-down phases over five to sixty minutes; this is your regression baseline and your SLO gate. A **stress test** drives load 1.5× to 2× expected peak to characterise *how* the system degrades — which subsystem yields first (CPU, GC, DB pool, thread pool). A **spike test** jumps from low to extreme load in seconds with little ramp; it validates queueing, autoscaling latency, circuit breakers, and connection-storm handling. A **soak** or endurance test holds average load for hours or days to surface time-dependent failures invisible to short tests: memory leaks, file-descriptor exhaustion, connection-pool drift, slow GC degradation, certificate expiry. A **breakpoint test** ramps continuously toward unrealistic load until something breaks, yielding the empirical knee in the throughput-vs-latency curve. A **scalability test** holds a load profile constant while *varying infrastructure* (replicas, instance sizes) to derive the scalability law of the system — useful input to capacity planning models like the Universal Scalability Law.

In practice, you run smoke tests every PR, average-load tests on `main` nightly, soak and stress before major releases, and breakpoint tests rarely because they are destructive.

### Metrics, and why averages lie

Throughput (RPS, TPS) is the rate of *completed* work; SRE folklore distinguishes throughput from **goodput**, which excludes errored responses. A system "handling 10k RPS" while serving 503s is producing error throughput. Always quote throughput together with an error-rate caveat and a latency qualifier.

Latency is a random variable, not a number. The arithmetic mean is dominated by the tail in heavy-tailed distributions and is, on its own, useless. The median (p50) is robust but blind to the tail. The percentile family (p95, p99, p99.9, "the nines") is the user-experience signal. Modern systems are rarely unimodal: cache hit versus miss yields bimodal latency, GC pauses inject discrete jumps, autoscaling cold starts add a third mode, cross-region failover adds a fourth. Reporting only the mean — or worse, averaging percentiles across instances — destroys this structure. **Never average percentiles across instances.** Aggregate the histograms (HDR or t-digest) and recompute. This is why HDR Histogram (Gil Tene) and t-digest exist.

The math behind why p99 is a 40%-of-sessions problem is straightforward and worth internalising. If a single request has a 1% chance of being slow, and a user session makes 50 requests, the probability that the session sees at least one slow request is **1 − 0.99⁵⁰ ≈ 39.5%**. So a "1%" tail-latency problem affects roughly forty percent of sessions. For services with parallel fan-out across N backends, the front-end p99 approximately equals the **backend p99.9** plus the median of the rest as N grows — the central insight of Dean and Barroso's *Tail at Scale* (CACM 2013). This is why distributed systems chase p99.9 and p99.99, not just p99.

**Concurrent users**, **virtual users (VUs)**, and **request rate** are not interchangeable. A virtual user is a generator concept (a thread, goroutine, or coroutine) that executes scripted iterations; a concurrent user is a real human session with think time; a request rate is requests arriving per unit time at the SUT. Conflating them is the most common conceptual mistake in load-test reports.

**Apdex** condenses everything into a 0–1 score: with target T, satisfied = response ≤ T (weight 1), tolerating = T < response ≤ 4T (weight 0.5), frustrated > 4T (weight 0). It is digestible to non-engineers and a useful rolled-up KPI, but two systems with identical Apdex can have very different p99s, and the 4× constant is arbitrary. Modern SRE practice prefers explicit percentile-based SLOs.

### Open versus closed loop, and why this is the deepest issue in the field

A **closed system** has a fixed number N of users; a new request arrives only after a previous one completes (plus optional think time Z). Arrivals are *triggered by completions*. An **open system** has arrivals driven by an independent stochastic process (typically Poisson with rate λ), unaffected by what the SUT is doing. New work shows up whether or not the system is keeping up. A **partly-open** system has open-loop session arrivals with closed-loop request flow within a session; Schroeder, Wierman and Harchol-Balter (NSDI '06) showed this is the most realistic model for typical web workloads.

The feedback problem in closed-loop testing is that a slow server lengthens iterations, which reduces arrivals, which reduces load on the SUT — the SUT's poor performance reduces the load on itself. This is a negative feedback loop. Real users do not behave this way; if anything, frustrated users *retry more*. Closed-loop tests therefore systematically understate what production looks like under stress. Schroeder's empirical work showed mean response time differing by more than an order of magnitude between closed and open at the same offered load, and that closed-system results are insensitive to think time above moderate values.

Tool defaults split sharply on this axis. JMeter Thread Group, the original wrk, hey, ab, and bombardier are closed-loop. Locust is closed-loop by design. k6's `constant-vus` and `ramping-vus` are closed-loop; its `constant-arrival-rate` and `ramping-arrival-rate` are open. Gatling's `injectOpen` family is open; `injectClosed` is closed. wrk2, vegeta, Artillery, and NBomber are open by design. **For SLA validation of user-facing services, almost always use the open-loop executor.**

### Little's Law as the load-tester's compass

For any stable queueing system in steady state, regardless of arrival or service distribution: **L = λW**, where L is average concurrency, λ is throughput, and W is mean response time. The proof requires no distributional assumptions, only stationarity. The practical consequence is a one-line sanity check.

If you target 1000 RPS at p̄ = 200 ms latency with no think time, the required steady-state concurrency is L = 1000 × 0.2 = **200 in-flight requests**. Your generator must therefore sustain at least 200 VUs, or in k6's `constant-arrival-rate` executor you must `preAllocatedVUs ≥ 200`. If observed concurrency falls short, k6 emits `dropped_iterations` warnings — a direct empirical signature of Little's Law violated by the generator.

The inverse use: if a JMeter run reports 500 TPS at 5 s mean response with 30 s think time, Little gives expected concurrency = 500 × (5 + 30) = 17,500 users. If your script says 1000 users, *the throughput number is wrong* — likely because the script counted errors as completions. Run this check on every result.

Combined with M/M/1 queueing, W = 1/[μ(1−ρ)], so as utilisation ρ → 1, latency goes to infinity hyperbolically. Brendan Gregg's USE method warns that disks above 60% utilisation already show meaningful queue delay; at 80% the latency tail is exponential. Little's Law translates this directly: as W explodes, so does L, exactly the mechanism behind tail-induced concurrency pile-ups.

### Coordinated omission, the measurement bug that hides in plain sight

Coordinated omission, named by Gil Tene of Azul Systems in his "How NOT to Measure Latency" talk, is a methodology bug where the measuring system inadvertently coordinates with the system being measured in a way that *avoids measuring outliers*. The mechanism: a closed-loop generator with N threads sends one request per thread and waits for the response. If the server stalls for 5 seconds, each thread is blocked during the stall. The generator records *one* slow sample per thread. But during that 5 seconds, in a real open-loop world, hundreds or thousands of requests *should have been issued* and would have suffered queueing on top of the stall, producing a fan of latencies from 5 s down to 0.01 s as the system recovered. Those samples were *omitted*, in a way coordinated with the SUT's pause.

Mathematically, the generator measures only the **service time** of the requests it actually sent, not the **response time** = queue time + service time that a real user would see. Tene's quantitative evidence in the wrk2 README showed that even on a quiet run with 11 ms worst-case latency, p99 reported with versus without CO correction differed by ~2×; in runs with real stalls, the reported p99.99 was off by **35,000×** from reality, with the reported p99.9 looking *better than the true p99*. This is not a small effect — it is catastrophic, and it is the reason many production "we're under SLO" claims are false.

The fix exists in two forms. wrk2 implements the **intended-start-time trick**: latency is measured from when a request *should have* been sent according to the constant-throughput schedule, not when it was actually sent. k6's arrival-rate executors do the same in spirit — iterations are scheduled independent of response times, and if VUs cannot keep up, k6 records `dropped_iterations` (itself a useful signal). Gatling's `injectOpen` profiles dispatch on a fixed schedule via the actor scheduler; the engine's non-blocking I/O decouples injection from response handling. JMeter's default Thread Group, wrk, hey, ab, and bombardier suffer CO; Locust's docs acknowledge the problem; mitigations exist (JMeter's Throughput Shaping Timer, Concurrency Thread Group) but require expertise.

Practical defence: when percentiles matter, use a constant-rate tool (wrk2, vegeta, k6 arrival-rate, Gatling open). Always cross-check client-side latencies with **server-side histograms** from Prometheus — these don't suffer CO because they measure at the SUT.

### Where load testing fits in the SDLC

The strategy is graduated cost-versus-fidelity. **Local dev** is for script correctness and fast feedback at trivial load — zero infrastructure cost, zero fidelity, useful only to validate scripts. **CI/CD** runs abbreviated smoke tests with k6 thresholds or Gatling assertions as build gates; the constraint is that CI runs must finish in five to ten minutes, so you detect coarse regressions but not subtle ones. **Pre-prod / staging** runs the full average/stress/soak suite at production fidelity, weekly or pre-release, against staging environments that mirror production DB sizes, network paths, and dependencies. **Production** is where the frontier lives: traffic mirroring (Envoy `request_mirror_policy`, Istio `VirtualService.mirror`, AWS VPC Traffic Mirroring, GoReplay) duplicates real requests to a shadow target with responses discarded; dark launches deploy code behind feature flags and route internal traffic; canary releases incrementally route real users with automated rollback on metric regression. Production tests have the highest fidelity but the realest risk; they require excellent observability and disciplined data isolation (never double-charge customers from the shadow target).

### The challenges that determine whether your test is real

**Realistic test data** is the most common silent failure. The naive trap is 1000 VUs all hitting `GET /products/42`: the DB returns from buffer cache, but reality returns from spinning disk after a JOIN across cold pages. Mitigations include parameterisation with data pools sized to at least ten times the working set so cache hit rate matches production, distribution shape that follows the empirical Zipf/long-tail of real traffic, and synthesis via `datafaker` (the maintained successor to JavaFaker, currently at 2.5.4) when production data has PII constraints. Synthetic data must satisfy referential integrity, business invariants, and realistic value ranges.

**Environment fidelity** is invalidated by staging-versus-prod divergence: a 1 GB staging DB versus 1 TB production turns index seeks into table scans; staging in a single VPC versus production spanning regions adds 50–150 ms of cross-region latency; staging mocks downstream dependencies that respond in 1 ms while production hits real services with their own queues, retries, and GC pauses; TLS and proxy chains differ in hop count.

**Network constraints** matter because a generator in `us-east-1` testing a service in `eu-west-1` measures mostly the Atlantic, not your code. Use `tc netem` or chaos tooling to inject 100 ms RTT and 1% packet loss when you want to validate retry storms and timeout configuration.

**Distributed load generation** becomes necessary when a single host saturates. Symptoms include generator CPU above 70% before SUT shows load, NIC at line rate, ephemeral port exhaustion (Linux default ~28k ports), and TIME_WAIT pile-up. Always monitor the generator's USE metrics in parallel with the SUT's; if the generator is saturated, your test is invalid.

**Observability of the SUT** is non-negotiable. A test that produces only client-side metrics is half-blind. The required pairing is RED metrics (Rate, Errors, Duration) at every service boundary, USE metrics (Utilisation, Saturation, Errors) for every resource, distributed tracing to attribute tail latency to specific spans, and server-side latency histograms (Prometheus, HdrHistogram exporters) immune to client-side coordinated omission.

### A catalogue of antipatterns that will silently invalidate your results

The fifteen failure modes worth memorising: connection pool exhaustion masquerading as SUT slowness (queueing in HikariCP, not in the DB); localhost-only tests where loopback latency is 10 µs and there is no TLS, DNS, or real MTU; coordinated omission in JMeter or wrk where the numbers look fine; cache-hot versus cache-cold confusion where the first minutes populate caches and the SUT looks faster than reality; missing think time where a VU with zero pause is a request firehose, not a user; too few unique data items where 100 VUs share 10 product IDs and you measure cache hit rate not application latency; ignored DNS, TLS, and connection-establishment overhead where keepalive masks what mobile users actually experience; load generator saturating its own NIC or CPU before the SUT (always run a control test against a no-op SUT to find your generator ceiling); conflating load testing with chaos engineering as separate concerns; not warming up the JVM, where the first ten thousand iterations of a hot method run interpreted before C2 compilation produces a 5–10× throughput jump; reporting averages of percentiles across instances; setting timeouts shorter than the tail latency, so the histogram caps and the slow requests become errors; single-iteration scripts that cannot translate to user throughput; ignoring server-side queueing in nginx or Envoy where backed-up upstreams produce 502/504 that look like SUT errors; and testing only happy paths, which understates DB load (no error logging), CPU (no validation rejections), and network (no retries).

### Reading results: what the numbers actually mean

The single most useful visualisation is the **HDR-style log-percentile plot** with x-axis as percentile on a log scale of (1−p), y-axis as latency. This makes bimodality visible (clear "knees" between modes), the tail shape visible (clean Pareto versus a cliff at your timeout), and run comparison trivial (overlay two HDR plots). A flat-then-cliff curve signals a hard timeout cutting off the true tail; a multi-step curve signals modes that should be separated by endpoint or tenant; a smooth power-law tail signals classic queueing or GC.

SLOs should be expressed as "X% of requests faster than Y ms", not "average < Y ms"; this composes cleanly with error budgets — an SLO of 99.9% under 200 ms over thirty days yields a 0.1% error budget = 43.2 minutes out of SLO. Multi-grade SLOs ("90% of requests < 100 ms AND 99% < 400 ms") capture both typical and tail behaviour, where a single-percentile SLO can be gamed by improving the median while letting the tail rot.

The capacity diagram every load tester should be able to draw from memory: x-axis is offered load, left y-axis is latency, right y-axis is served throughput. Latency stays flat until ρ ≈ 0.7, then curves upward (M/M/1: hyperbolic asymptote at λ = μ); served throughput tracks offered until the knee, after which it plateaus or *decreases* due to retry storms, GC death spirals, or thrashing. The breakpoint is the knee. Production operating points should sit well below the knee — typically ρ ≤ 0.6 for I/O resources — to leave headroom for variance and bursts.

---

## 2. The tool landscape, categorised

The field divides into seven natural categories.

**Code-as-tests with a DSL** — k6 (JavaScript/TypeScript on a Go runtime), Gatling (Scala engine, Kotlin/Java/Scala/JS DSLs on the JVM), Locust (Python with gevent), Artillery (YAML and JS on Node.js), NBomber (.NET, C#/F#).

**GUI- and protocol-heavy** — Apache JMeter, the thirty-year incumbent, Java Swing GUI for authoring and a CLI for execution.

**CLI micro-benchmarkers** — wrk and wrk2 (C with LuaJIT scripting), hey (Go), vegeta (Go, CLI plus library), oha (Rust with Tokio and a TUI), bombardier (Go with fasthttp), ab (legacy Apache Bench).

**Browser-based and end-to-end** — k6's built-in `k6/browser` module driving Chromium via CDP, Artillery's Playwright integration, the legacy Selenium Grid which should not be used for load.

**Cloud and SaaS platforms** — Grafana Cloud k6, Gatling Enterprise, BlazeMeter (Perforce), LoadNinja (SmartBear), Loader.io (SendGrid), and OpenText Performance Engineering (formerly LoadRunner) for regulated enterprises.

**Specialised tools** — Tsung (Erlang, mostly historical), Drill (Rust, YAML-driven), Goose (Rust, Locust-inspired with strong async performance).

**Protocol specialists** — ghz for gRPC, the various Kafka tools (`kafka-producer-perf-test`, `kafka-consumer-perf-test`, `xk6-kafka`, JMeter with Pepper-Box), the WebSocket testers across most of the above.

The single mental frame that ties this taxonomy together is **how each tool generates load**. Closed-loop tools (JMeter default, Locust default, wrk, hey, ab, bombardier) measure service time and underestimate tail latency. Open-loop tools (wrk2, vegeta, k6 arrival-rate executors, Gatling `injectOpen`, Artillery, NBomber, oha with `--latency-correction`) measure response time correctly. For tail-latency claims to be trustworthy you almost always want the open-loop side. Make this the lens through which you evaluate any new tool you encounter.

---

## 3. Deep dives on the major tools

### Apache JMeter — the veteran

Started by Stefano Mazzocchi at Apache in 1998; current stable is **5.6.3** (November 2025), Java 8 minimum, Java 17 recommended. The codebase is steadily migrating from Groovy to Kotlin under maintainers Vladimir Sitnikov and Felix Schumacher. The philosophy is a tree of Thread Groups, Samplers, Logic Controllers, Listeners, Assertions, Config Elements, and Pre/Post-Processors, persisted as XML `.jmx` files. Strengths are vast protocol coverage out of the box (HTTP/S, JDBC, JMS, FTP, SMTP, LDAP, TCP, MQTT via plugin, Kafka via Pepper-Box), the `jmeter-plugins.org` ecosystem with thirty years of accumulated solutions, true distributed mode via Java RMI, a useful HTML dashboard report, and a recording proxy that makes capture-and-replay accessible to non-coders.

The weaknesses are equally well-known. The default Thread Group is closed-loop and so suffers coordinated omission; mitigations exist (Throughput Shaping Timer, Concurrency Thread Group) but require expertise. The JVM-thread-per-VU model tops out at a few thousand active threads per node. The Swing GUI is unergonomic and **must not be used to actually run load** — Apache itself documents this; CLI mode (`jmeter -n -t plan.jmx -l results.jtl -e -o report/`) is the only correct execution path. XML test plans diff badly in Git. For scripting, BeanShell is a legacy trap (interpreted on every invocation, terrible throughput); JSR223 with Groovy 4 and the "Cache compiled script if available" checkbox is roughly an order of magnitude faster and is the recommended path. JMeter's Kafka story via Pepper-Box still works but the upstream is essentially frozen, pinned to old `kafka-clients` JARs; for serious Kafka work you should reach for `xk6-kafka` instead. **Verdict: alive, maintained, still the de facto standard in enterprise QA and BlazeMeter shops, but the wrong choice for greenfield developer-driven testing.**

### Gatling — your primary tool

Gatling started as an open-source project in 2012 by Stéphane Landelle, with Gatling Corp founded in 2015 to commercialise it. As of April 2026 the current stable is **3.15.0** with the `io.gatling.gradle` plugin at **3.15.0.1**. There is **no Gatling 4.x** — the 4.0 rumours from 2024 blog posts never materialised, and the project has continued with the 3.x line. Engine is Scala on Netty with Apache Pekko for the actor model (Pekko 1.0 was forked from Akka 2.6 after Lightbend's BSL relicense in September 2022; Gatling migrated to Pekko in the 3.11 era to keep the OSS edition under Apache 2.0).

The DSL evolution that matters for your stack is precise: **Java DSL arrived in Gatling 3.7 (October 2021); Kotlin DSL became first-class in 3.10 (August 2023)**; documentation since then ships every example with Java/Kotlin/Scala/JS/TS tabs. The Kotlin DSL is a thin layer over the Java API (`io.gatling.javaapi.core` and `io.gatling.javaapi.http`), which means two specific Kotlin gotchas: `is` clashes with the Kotlin keyword, so use `status().shouldBe(200)` rather than `status().is(200)`; and `in` is reserved, so injection profile aliases like `during(...)` are used instead. The JS/TS SDK landed in 3.12 via GraalVM polyglot; 3.14 (May 2025) moved to `jakarta.jms`.

Strengths are decisive for a JVM team: a maintainable code-first DSL that treats simulations as production code, gorgeous static HTML reports out of the box (no Grafana required), excellent JVM resource density (single-machine simulations comfortably push 10k–40k concurrent users), native open-model injection (`constantUsersPerSec`, `rampUsersPerSec`, `stressPeakUsers`) that does not suffer coordinated omission, strong WebSocket and gRPC support as official plugins, a Recorder for HAR/Postman/browser-session bootstrapping, first-class Maven, Gradle, and sbt plugins, and — for your team specifically — the same toolchain, JVM, IDE refactoring, and CI Docker image as your production code, with simulations living in `src/gatling/kotlin` next to `src/test/kotlin`.

Weaknesses are real but manageable. Gatling is heavier than k6 in cold start and memory; the open-source distributed mode is bare-bones, requiring Gatling Enterprise for serious distributed runs; real-time reporting requires Enterprise or InfluxDB/Graphite integration, with the OSS HTML report being post-hoc only; there is no browser-automation story comparable to `k6/browser` or Playwright. Reddit feedback in 2024–2025 mentions Scala compilation slowness in IDEs and opaque Enterprise pricing.

Protocol support in OSS includes HTTP/HTTPS, HTTP/2 (with `httpConcurrentRequests` in 3.15 for parallel requests without a parent), WebSocket as a first-class DSL, Server-Sent Events, JMS, MQTT, JDBC, and **gRPC officially supported by Gatling Corp** through the `io.gatling:gatling-grpc` plugin documented under `docs.gatling.io/reference/script/grpc/...` — superseding the historical `phiSgr/gatling-grpc` community plugin. Community plugins exist for AMQP, Kafka, Cassandra, and Redis. Gatling Enterprise (formerly FrontLine, ~€69/month Basic on a credit-per-injector-minute model) adds web UI, run scheduling, trend reports, distributed injectors across AWS/Azure/GCP/Kubernetes, real-time cockpit during runs, RBAC, public REST APIs, Postman import, AWS S3 feeders and Secrets Manager integration, and an AI Assistant for VS Code/Cursor/IntelliJ.

### k6 — your secondary tool

Created by Load Impact in 2017 (Robin Gustafsson and team), acquired by Grafana Labs in June 2021 and rebranded Grafana k6. The big inflection point was **k6 v1.0 at GrafanaCON 2025 (May 2025)** which introduced semantic versioning with formal stability guarantees, first-class TypeScript with no transpilation step, and graduation of `k6/browser`, `k6/net/grpc`, and `k6/crypto` to stable. The current stable is **1.6.1 (16 February 2026)** with `k6/websockets` graduated to stable in 1.6.0, OpenTelemetry output graduated in 1.4.0, and an MCP server for AI assistants in 1.6.0.

The architecture is a single statically-linked Go binary; test scripts run in-process inside a **Sobek** runtime (Grafana's 2024 fork of `dop251/goja`, an ECMAScript implementation in pure Go) — k6 v0.52 in mid-2024 switched from goja to Sobek to accelerate ESM and TypeScript work. Each VU is a goroutine that owns its own Sobek runtime; per-VU state resets per iteration. **Critically, this is not Node.js** — there is no `fs`, `os`, `child_process`, `net`, `Buffer`, or DOM. Bundlers like Rollup or Webpack are used to ship npm dependencies as a self-contained file.

Strengths are developer ergonomics (ES modules, TypeScript types, IDE autocomplete, fast feedback), tiny resource footprint per VU (k6 routinely runs 30–40k VUs from one mid-sized box), native Grafana stack integration (Prometheus/Mimir, Loki, Tempo, OpenTelemetry), open-model arrival-rate executors that directly address coordinated omission, threshold-driven CI where the test process exits 99 on threshold breach, the xk6 extension model with **automatic extension resolution as of 1.2.1+** (import `k6/x/...` and k6 builds the right binary on demand), and a built-in browser module with a Playwright-style API.

Weaknesses include the not-Node-not-V8 reality where any npm package using `fs`, `Buffer`, or native add-ons won't work without bundling and shimming; CPU-heavy JavaScript in scripts will throttle the load generator before the network does; cross-VU mutable state is awkward (only read-only `SharedArray`); the default `constant-vus` and `ramping-vus` executors suffer coordinated omission and you must consciously choose the arrival-rate executors; OSS reporting is utilitarian, with nice dashboards requiring Grafana, Cloud k6, or InfluxDB; and Cloud only allows official extensions.

The seven executors split cleanly: `shared-iterations`, `per-vu-iterations`, `constant-vus`, `ramping-vus`, and `externally-controlled` are closed-loop; **`constant-arrival-rate` and `ramping-arrival-rate` are open-loop** and start iterations on a fixed schedule independent of SUT response time. If the SUT slows, k6 spins up more VUs from its pre-allocated pool to keep the rate, and drops iterations (which is itself a useful signal) if `maxVUs` is exhausted.

Cloud pricing is volume-based: a Free tier (500 VU-hours/month), Pro PAYG at $19/month base plus $0.15/VU-hour, Advanced/Enterprise at custom pricing with a $25k/year minimum commit. **Browser VUs are billed at 10×** the rate of protocol VUs. Locally-executed cloud tests via `k6 cloud run --local-execution` get a 25% discount. Beyond the OSS, Cloud k6 adds the test scheduler, trend dashboards, Private Load Zones (run inside your VPC via the k6 Operator on Kubernetes), up to 1M concurrent VUs / 5M RPS in fully-managed cloud, static IPs, multi-region load injection, audit logs, and SSO. The k6 Operator 1.0 shipped in 2025 with a Helm chart and a `PrivateLoadZone` CRD that registers a cluster as a private load zone in Grafana Cloud.

Important xk6 extensions to know about: `xk6-kafka` (now at 1.0, 2025), `k6/x/sql` for JDBC-style database load tests, `xk6-redis` (replacing the deprecated experimental module in 1.5.0), `xk6-amqp`, `xk6-mqtt`, `xk6-disruptor` for chaos injection, `xk6-distributed-tracing`, `xk6-faker`, and the now-official `xk6-dns` (1.4.0).

### Locust, Artillery, NBomber — the rest of the code-as-tests pack

**Locust** (Python, current 2.43.4 December 2025, MIT) shines for Python shops: tests are Python code with `@task(weight)`-decorated methods on `User` classes, gevent provides cooperative concurrency, master/worker over ZeroMQ enables distributed mode, and the web UI provides real-time charts and a "swarm" control. **`FastHttpUser`** (built on `geventhttpclient`) is roughly 5–10× faster than `HttpUser` (built on `requests`) and should be the default. The December 2025 release added official OpenTelemetry auto-instrumentation via `--otel`, pairing nicely with Tempo or Jaeger. Coordinated omission is acknowledged by the community; reporting is shallow versus k6 or Gatling. **Verdict: the default for Python shops, ML serving stacks, and quick-and-dirty tests; not the right choice when your codebase is JVM Kotlin.**

**Artillery** (Node.js, MPL-2.0, very active through 2025) is YAML-first with optional inline JS or TypeScript, organised into `config` and `scenarios`. Its phases are open-loop (`arrivalRate`, `rampTo`, `arrivalCount`), partially mitigating coordinated omission. The 2024–2025 differentiators are the AWS Fargate distributed runner, AWS Lambda Container Images for "100k RPS for less than a cup of coffee", and Playwright integration for browser-based load that reuses your existing Playwright `.spec.ts` files. Best-in-class for serverless distributed load and Node/TS shops.

**NBomber** (.NET, 5.8.2 February 2025 with v6.x preview through 2025) is the C#/F# equivalent — type-safe load tests, real debugger, reuses your application's HttpClient/EF Core/Kafka client code, beautiful interactive HTML reports, supports both open and closed models. Source-available rather than pure OSS: free for personal use, ~$99/user/month for team/cluster usage. The natural choice for a .NET shop.

### CLI micro-benchmarkers, ranked

**vegeta** (Go, 12.13.0 October 2025) is the most actively maintained and the right default. Constant-rate by default (open-loop and CO-correct), the `attack | encode | report | plot` Unix-pipeline composition is elegant, HDR histograms, JSON/CSV/text reports, a Prometheus exporter, and uPlot-based interactive plots. Available as both CLI and Go library — many Go services embed `vegeta/lib` for in-test load.

**oha** (Rust, 1.10.0 in 2025) is the modern Rust reimagining of `hey` with a delightful real-time TUI. Supports `--latency-correction` for coordinated omission, HDR histograms, JSON/CSV output, sqlite logging, experimental HTTP/3 via the `h3` feature flag. Best demo tool for screen-shares; quietly accurate when you set the right flags.

**wrk2** (C with LuaJIT, Gil Tene's fork) remains the canonical "show me my real p99.9" tool for HTTP. Adds `-R rate` (required), uses HDR histograms, measures latency from intended send time. Effectively unmaintained since ~2019 but the measurement methodology is correct in a way most successors still get wrong; cite it in teaching.

**wrk** (C, no tagged release ever, last meaningful commit March 2021) — 40k stars, fast, packaged everywhere, but avg/stddev-only latency reporting is its critical flaw. **hey** (Go, v0.1.4 January 2020) is effectively frozen but still in tutorials; no CO correction. **bombardier** (Go, master pseudo-version 2025-03-04) uses `valyala/fasthttp` and is extremely fast for raw throughput. **ab** is legacy — mention historically, never draw conclusions from its numbers. The right modern defaults are oha for screen-shares, vegeta for pipelines, wrk2 when you must have HDR-correct percentiles in a single binary.

### gRPC: ghz wins

**ghz** (Go, 0.120.x May 2024 with active dependency tracking through December 2025) is the de facto standard for gRPC load. All four call types (unary, client-streaming, server-streaming, bidi), proto reflection so `.proto` files are unnecessary if reflection is enabled, asynchronous request fan-out, configurable connections/concurrency/total/duration/rate, output formats including summary, csv, json, pretty, html, `influx-summary`, and `influx-details`. Available as both CLI and Go library (`ghz/runner`). It is generally faster per-core than `k6/net/grpc` because k6 pays the goja JS interpretation tax. **`grpc_cli` and `grpcurl`** are *debugging* tools, not load testers — no concurrency or rate control; do not confuse them with ghz.

### WebSocket and Kafka

WebSocket testing is awkward — stateful, long-lived, easy to get wrong (counting connection establishment as round-trip latency, for example). **k6 `k6/websockets`** (graduated from experimental to stable in late 2025/1.6.0) implements the W3C WebSocket living-standard API and supports multiple concurrent sockets per VU. The legacy `k6/ws` (synchronous, blocking) still works but is deprecated for new code. **Gatling's WebSocket DSL** is built-in, with the actor model mapping naturally onto persistent connections. **Artillery** has native WebSocket via the `ws` engine and Socket.IO v3+ via `artillery-engine-socketio-v3`. Specialised tools like Thor are mostly historical (last upstream commits ~2017, though forks remain useful).

For Kafka, the bundled scripts (`kafka-producer-perf-test.sh`, `kafka-consumer-perf-test.sh`) are the correct first thing to reach for when measuring broker capacity in isolation — they have no message templating or schema-registry awareness, but they give you raw producer/consumer throughput. **`xk6-kafka`** (mostafa, reached 1.0 in 2025) is the current best-in-class for development teams: String/JSON/ByteArray/Avro/JSON Schema, Schema Registry client, SASL PLAIN/SCRAM/AWS IAM, TLS, compression, scriptable in JavaScript. JMeter with Pepper-Box still works on JMeter 5.x but is barely maintained. Conduktor and Confluent Cloud have commercial dashboards. Always teach all three flavours: producer-only (broker write throughput), consumer-only (read throughput and consumer-group rebalancing on a pre-loaded topic), and end-to-end (producing and asserting in a separate consumer-group or downstream HTTP API) — the last is the only test that exposes broker → connector → DB → API pipelines correctly.

### Browser-based load: the cost reality

A single Chromium instance uses 200–500 MB of RAM and at least one CPU core. A single 8-core / 16 GB load generator realistically drives 10–30 concurrent browser users, versus 1,000–10,000 protocol-level VUs. Browser tests are 10–100× more expensive. The right pattern is small browser VU counts (validating UX, capturing Web Vitals like LCP/FCP/CLS) layered on top of a large protocol-level test that generates the actual traffic.

**`k6/browser`** originated as `xk6-browser`, was bundled into k6 core in v0.52 (mid-2024), and the standalone `grafana/xk6-browser` repo was archived January 30, 2025. It drives Chromium via Chrome DevTools Protocol with a Playwright-like API, captures Web Vitals as k6 metrics, and is supported in Grafana Cloud k6. **Artillery + Playwright** is currently the smoothest "use my existing Playwright tests for load" story in the OSS world. **Selenium Grid** predates everything else and was never designed for measurement-grade timing — use it for functional automation only.

### Cloud and SaaS

**Grafana Cloud k6** adds hosted distributed runners across 21+ AWS regions, web-based test builder, browser recorder, real-time dashboards, longer retention than OSS, integrations with Tempo/Loki/Pyroscope, AI-assisted Performance Insights, scheduled tests, and RBAC. **Gatling Enterprise** offers hosted multi-injector orchestration for Java/Scala/Kotlin/JS SDKs, real-time test cockpit, trend reporting, RBAC, and an on-premise self-hosted option for regulated industries (~€400/month entry). **BlazeMeter** (Perforce, after the 2021 acquisition) is JMeter-as-a-service primarily, with 56+ cloud locations, but has pivoted aggressively to "any script, any framework" supporting JMeter, Gatling, k6, Selenium, Playwright, Taurus, and a no-code recorder. **LoadNinja** (SmartBear) uses real Chrome browsers per VU — high cost per VU but real DOM rendering. **Loader.io** is the simplest SaaS, free tier with three test types, suitable for tutorials and hobby APIs. **OpenText Performance Engineering** (the rebrand of Micro Focus LoadRunner: Cloud → Core, Professional, Enterprise) covers 180+ protocols including SAP GUI, Oracle Forms, Citrix, RDP, and mainframe — the long tail no OSS tool will cover, used by banks, telcos, and governments.

---

## 4. Tool selection by use case

For each common load-testing question, here is the concrete recommendation.

**"Add a smoke test to CI for Spring Boot endpoints"** — k6 with a 30–60 second `constant-vus` scenario, three or four critical endpoints, hard thresholds (`p(95)<300`, `http_req_failed: rate<0.001`). Fast, JS-only, no JVM warmup hit, exits 99 on failure → fails the build cleanly. If you prefer to stay in the JVM, use Gatling with a brief `injectOpen(rampUsers(10).during(30))` and tight assertions; a JVM cold start adds ~5 seconds to CI but eliminates a second toolchain.

**"Find the breaking point of a service"** — k6 `ramping-arrival-rate` from low RPS to far above expected peak, or Gatling `incrementUsersPerSec(stepUsers).times(N).eachLevelLasting(2.minutes)`. The arrival-rate (open-loop) executor is essential here: closed-loop tests hide breakage because slowing-down VUs reduce offered load. Look for the inflection where p99 climbs faster than rate, and the onset of `dropped_iterations`.

**"Soak/endurance test to detect memory leaks"** — Gatling with `constantUsersPerSec` and `maxDuration(Duration.ofHours(12))`. The actual measurement is JVM-side (heap growth, GC pause distribution, file descriptor count, classes loaded); the load generator just drives steady traffic. Pair with Java Flight Recorder for the entire run (`-XX:StartFlightRecording=duration=43200s,filename=soak.jfr,settings=profile`).

**"Test gRPC services"** — ghz for raw benchmarking and CI gates (single binary, no scripting required); k6 with `k6/net/grpc` when you need scenario logic, mixed protocols (HTTP + gRPC in one test), or thresholds-as-code. Gatling has gRPC via the `gatling-grpc` plugin if your team is already standardised on Gatling, but the ghz + k6 combination is more idiomatic today.

**"Test WebSocket connections"** — k6 with `k6/websockets` (the now-stable module). Use `ramping-vus` to simulate long-lived connections — VUs map to sockets and the metric of interest is concurrent active sockets. Avoid `k6/ws` for new tests. If you are already using Gatling, its built-in WebSocket DSL is excellent and the actor model fits persistent connections naturally.

**"Load-test Kafka producers/consumers"** — start with `kafka-producer-perf-test.sh` and `kafka-consumer-perf-test.sh` for raw broker numbers. Move to `xk6-kafka` for development-team-friendly scenario tests with thresholds; or write a thin JVM driver using the Kafka client and call it from Gatling's custom protocol API for end-to-end testing. Evaluate consumer lag from Prometheus (`kafka_consumergroup_lag`) and producer queue depth on the client side. Avoid JMeter + Pepper-Box for new work.

**"Browser-based load tests for a React frontend talking to Spring Boot"** — k6's built-in `k6/browser` for full-page interactions: SPA hydration, JS-driven flows, real DOM assertions. Mix browser VUs (small numbers, ten to thirty) with HTTP scenarios (large numbers) in the same script for realistic cost-effective coverage. Capture LCP/FCP/CLS as k6 metrics and add thresholds against them.

**"Load-test from multiple geographic regions"** — Grafana Cloud k6 with `loadDistribution.distribution` per scenario across named regions (`{ region: 'amazon:us:ashburn', percent: 50 }, { region: 'amazon:eu:frankfurt', percent: 30 }, { region: 'amazon:ap:tokyo', percent: 20 }`). Self-hosted, deploy `k6-operator` to one Kubernetes cluster per region, attack a shared target, fan in metrics via Prometheus remote-write. Gatling Enterprise multi-zone is the equivalent for JVM-centric organisations.

**"Production traffic replay / shadow load testing"** — Istio `VirtualService.mirror` for service-mesh users (most idiomatic, protocol-agnostic at L7, mTLS preserved). GoReplay for L7 HTTP without a mesh. AWS VPC Traffic Mirroring for non-HTTP protocols where L4 capture is needed. Shadow before, not instead of, synthetic load tests — they answer different questions. For write traffic, point shadows at a separate idempotent sink and never replay POST/PUT to production write-side services without sanitisation.

---

## 5. The Spring Boot + Kotlin specifics

### Versions to pin today (April 2026)

For Gatling, **3.15.0** (the next-most-recent line was 3.14, May 2025; the official `gatling-gradle-plugin-demo-kotlin` repo currently pins `3.14.9.4`, which is also fine). The Gradle plugin is **`io.gatling.gradle:3.15.0.1`** (Gradle Plugin Portal, 19 March 2026). For Kotlin, **2.3.0**. For JDK, **21 LTS** (Gatling supports OpenJDK LTS 11–25 but JDK 21 is the sweet spot). For Spring Boot, **3.5.x** is the only 3.x line still in OSS support (until 30 June 2026); 3.4 went EOL 31 December 2025; **Spring Boot 4.0** went GA on 20 November 2025 and is at 4.0.5 as of late March 2026. For new projects pick 4.0.5; for an existing project being load-tested, stay on 3.5.x until at least Q2 2026, then migrate. For Datafaker, **2.5.4** (the maintained successor to JavaFaker, which has been stale since 2020).

### Why the Kotlin DSL is the right choice for a Kotlin shop

The team writes Kotlin daily — using the Kotlin DSL means tests share idioms (`val`, lambdas, extension functions), compile against your existing data classes (DTOs), and let you extract scenario fragments as top-level `val`s. The Scala DSL still exists and is officially supported, but new Kotlin code has zero reason to pull a Scala compiler into the build. The Java DSL works in Kotlin too (it's the same JVM types), but the Kotlin DSL gives you nicer interop with `Duration`, lambdas, and string templates.

### Project structure

The recommended layout for a service whose load tests are owned by the same team:

```
my-service/
├── settings.gradle.kts        # include("api", "domain", "load-tests")
├── api/                       # Spring Boot app
├── domain/                    # pure Kotlin DTOs, no Spring deps
└── load-tests/
    ├── build.gradle.kts       # applies io.gatling.gradle
    └── src/gatling/
        ├── kotlin/com/example/   # simulations
        └── resources/            # gatling.conf, logback.xml, feeders
```

`load-tests` depends on `domain` so DTOs are reused at compile time (renaming an endpoint field then fails to compile, not at runtime). It deliberately does *not* depend on `api`, because pulling Spring into the Gatling classpath causes class loading bloat and occasionally JMS conflicts (Gatling 3.14+ uses `jakarta.jms`). Same-repo, separate-Gradle-subproject is the sweet spot for a single service; only consider a separate repo when load tests cover multiple services or are owned by a separate SRE/QA team.

`build.gradle.kts` for the Gatling subproject:

```kotlin
plugins {
    kotlin("jvm") version "2.3.0"
    id("io.gatling.gradle") version "3.15.0.1"
}

repositories { mavenCentral() }

tasks.withType<JavaCompile> { options.release.set(21) }
kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_21)
    }
}

gatling {
    // -Xms == -Xmx removes resize pauses; Xss100M is gatling's classic recipe
    // because the DSL builds deep call chains.
    jvmArgs = listOf("-server", "-Xms1G", "-Xmx1G", "-Xss100M", "-XX:+UseG1GC")
    systemProperties = mapOf("file.encoding" to "UTF-8")
    logHttp = io.gatling.gradle.LogHttp.FAILURES
}

dependencies {
    gatlingImplementation(project(":domain"))                  // share DTOs
    gatlingImplementation("net.datafaker:datafaker:2.5.4")
}
```

Critically — and most teams miss this — `src/main` and `src/test` classes are added to the `gatlingImplementation` classpath automatically, so simulations can directly `import com.example.dto.OrderRequest` without copy-paste.

### Spring Boot Actuator integration during load tests

Without Actuator and Micrometer wired to Prometheus, a load test only tells you what the *client* observed. With it, you also see *why* — GC pauses, connection-pool starvation, thread-pool saturation, JIT compilation activity.

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, prometheus, threaddump, heapdump
  endpoint:
    health:
      probes: { enabled: true }
  metrics:
    tags:
      application: ${spring.application.name}
      env: ${ENV:dev}
    distribution:
      percentiles-histogram:
        http.server.requests: true
        http.client.requests: true
      percentiles:
        http.server.requests: 0.5, 0.95, 0.99
      slo:
        http.server.requests: 50ms, 100ms, 200ms, 500ms, 1s, 2s
      minimum-expected-value: { http.server.requests: 5ms }
      maximum-expected-value: { http.server.requests: 10s }

server:
  tomcat:
    mbeanregistry: { enabled: true }
    threads: { max: 200, min-spare: 20 }

spring:
  threads:
    virtual: { enabled: false }   # toggle for comparison runs
```

The meters that matter under load are `http.server.requests` (the server-side latency distribution; compare to Gatling client-side numbers and the delta is network plus queueing), `jvm.gc.pause` (stop-the-world time; if p99 spikes correlate with this, tune GC not application code), `jvm.memory.used` and `jvm.memory.committed` (heap growth shape reveals leaks and cache thrash), `tomcat.threads.busy` (thread-pool saturation; if `busy ≈ max`, requests are queueing in Tomcat's accept queue and you cannot tell from client metrics), `hikaricp.connections.pending` (sustained `pending > 0` means your bottleneck is the DB pool, not the DB itself), `jvm.classes.loaded` (sustained growth means dynamic class generation), `process.cpu.usage` versus `system.cpu.usage` (whether the JVM is the noisy neighbour), and `logback.events` by level (an ERROR rate spike under load is often the smoking gun).

Run Prometheus and Grafana via Docker Compose during the test with a 5-second scrape interval (the default 15-second interval aliases short load spikes; just remember to set it back in production). The most useful pre-built dashboards as starting points are JVM (Micrometer) `4701`, the modern Spring Boot 3.x replacement `17175`, and the K6 Prometheus dashboard `19665`. Note that Spring Boot 2.1 Statistics (`11378`/`12464`) shows "No data" panels on Boot 3.x because tag/metric names changed; either fork it or use 17175.

A subtle point worth understanding: Micrometer publishes either Prometheus *summaries* (client-side computed quantiles, cannot be aggregated across instances) or *histograms* (bucketed, aggregatable via `histogram_quantile()`). For a horizontally-scaled service you almost always want histograms — but enabling `percentiles-histogram` for `http.server.requests` adds ~70 buckets × URI × status series, so restrict it to the metrics you actually graph.

### Reproducible test data with Testcontainers

In-memory H2 lies — its query planner, isolation semantics, and lock timing diverge from PostgreSQL enough that "passes locally on H2" routinely hides production bugs. For load tests, always run against the real engine, with `withReuse(true)` plus `~/.testcontainers.properties` containing `testcontainers.reuse.enable=true` so the JVM crash/restart between Gatling runs doesn't tear down Postgres and re-run all your Flyway migrations.

```kotlin
object Infra {
    val postgres = PostgreSQLContainer("postgres:16-alpine")
        .withDatabaseName("loadtest").withReuse(true).also { it.start() }
    val kafka = KafkaContainer(DockerImageName.parse("apache/kafka:3.8.0"))
        .also { it.start() }
    val redis = GenericContainer("redis:7-alpine")
        .withExposedPorts(6379).also { it.start() }
}
```

For seeding, three layers each with a clear purpose: static reference data (e.g., country codes) as `src/gatling/resources/feeders/countries.csv` loaded with `csv("countries.csv").random()`; synthetic per-VU data via `Faker(Random(42L))` invoked inside a Kotlin `Iterator<Map<String,Any>>`; pre-loaded persistent fixtures via Flyway with a profile-gated seed migration `V900__load_test_seed.sql`. Reproducibility matters because regression detection is *comparative* — yesterday's p99 versus today's p99 only tells you something if the dataset is identical.

### JVM tuning during tests

For GC choice, **G1** is the default and the no-think choice for heaps 4–32 GB; tune the pause target with `-XX:MaxGCPauseMillis=100`. **Generational ZGC** (production in JDK 21, default in JDK 23+) gives concurrent sub-millisecond pauses at the cost of 5–15% throughput; it is now a defensible default for HTTP services with strict p99 SLOs. **Shenandoah** is in the same niche on Red Hat builds. **Parallel** is for batch workloads only.

Set `-Xms == -Xmx` to eliminate heap-resize pauses that show up as spurious latency spikes during your test, and add `-XX:+AlwaysPreTouch` to force the OS to commit pages at startup so the first GC after warmup doesn't pause while the kernel maps fresh pages.

JIT warmup is the trap that catches almost everyone the first time. The JVM starts in interpreter mode; methods become **C1**-compiled around 1,500–10,000 invocations (~30–50% of peak throughput, fast to compile) and **C2**-compiled around 10,000–100,000 invocations (deep optimisations, vectorisation, peak throughput). Tiered compilation runs both. The visible effect is throughput climbing over the first 30–120 seconds before plateauing; a naive 60-second test measures mostly the C1 phase and produces numbers ~30–50% worse than steady state. There is also a known second-order effect where compilation threads compete with application threads for CPU under tight Kubernetes CPU limits, slowing warm-up by 3–4×.

The two workable strategies, pick one and document it: a **dedicated warmup phase** of 60 seconds at low rate, results discarded, then ramp to target; or a **single-phase test with post-hoc filtering** dropping the first N seconds in analysis. For very strict measurements, run the warmup phase with `-XX:+PrintCompilation` and watch for "made not entrant" or deopts; if they're still flowing two minutes in, your warmup is too short. CDS and CRaC reduce startup time but do not replace JIT warmup. Native image (GraalVM) eliminates JIT warmup but has a different cold-start curve and ~70–90% of JIT peak throughput for steady-state.

For profiling during the steady-state phase, JFR (`-XX:StartFlightRecording=duration=600s,filename=run.jfr,settings=profile`) gives ~1–2% overhead and opens in JDK Mission Control; look at Method Profiling, Garbage Collections, Allocation in New TLAB, and Lock Instances. **async-profiler** produces sharper CPU flamegraphs because it uses perf_events / AsyncGetCallTrace; attach during the steady-state phase with `./profiler.sh start -e cpu -f cpu.html <pid>`. The first time you run async-profiler against an unoptimised Spring Boot app, expect Jackson serialisation and Hibernate proxy generation to dominate the flamegraph.

### Spring Boot 3.x specifics that change load test interpretation

**Virtual threads** (`spring.threads.virtual.enabled=true` in 3.2+ and 3.5+ and 4.0) replace Tomcat's per-request executor with `Executors.newVirtualThreadPerTaskExecutor()`. This single property changes load test interpretation in three ways. `tomcat.threads.busy` becomes meaningless as a saturation signal (with platform threads, busy ≈ max means "we're rejecting work soon"; with virtual threads it just tracks live in-flight requests). DB pool saturation becomes the dominant bottleneck, so Hikari's `connections.pending` and `connections.acquire` timer become the headline metrics. Pinning was a real concern on JDK 21 (a virtual thread inside a `synchronized` block pins its carrier thread) but **JDK 24 unpinned `synchronized` via JEP 491**, greatly reducing the pinning surface; if you are still on JDK 21, audit `synchronized` usage in hot paths and look for `jdk.tracePinnedThreads` warnings. For pure CPU-bound endpoints, virtual threads give you nothing — they shine for I/O-bound workloads, with empirical benchmarks showing ~2× throughput improvement on endpoints with significant I/O wait and ~0% on CPU-bound endpoints. The practical recipe: run the full simulation with `spring.threads.virtual.enabled=false` and again with `=true`, compare at high concurrency (≥1000 VUs) and on endpoints that hit a DB or external HTTP. The comparison itself is data.

**Native image** (GraalVM, `./gradlew nativeCompile`) eliminates JIT warmup but caps at 70–90% of JIT peak throughput for long-running services. Cold start is dramatically faster (tens of ms versus seconds), making it attractive for serverless. Memory footprint is roughly one-third of JVM RSS. GC choices are limited (Serial in the community edition; Oracle GraalVM ships G1). For load testing, native images do not need a warmup phase, but you should still pre-warm caches and JDBC pools.

**WebFlux** versus **MVC + virtual threads** is a different shape. MVC + virtual threads is "synchronous code, scaled by the runtime" — easier to reason about, easier to debug, easier to load-test (one request = one logical thread you can stack-trace). WebFlux is asynchronous reactive streams with a higher ceiling on raw concurrency per core, but a stack trace mid-request is meaningless and `ThreadLocal` (and therefore MDC, `SecurityContextHolder`, traditional tracing) requires `Context` propagation. `http.server.requests` works the same on both. Thread-pool metrics change: WebFlux has a small fixed-size event loop pool (Reactor Netty: 2× CPU cores), and saturation looks like rising event-loop latency, not "busy threads" — watch `reactor.netty.eventloop.pending.tasks`. WebFlux can apply backpressure end-to-end; MVC + virtual threads cannot, so a runaway upstream eventually exhausts DB connections or memory rather than throttling itself. For a Kotlin shop, Spring Boot 3.5 + virtual threads + coroutines (`suspend fun` controllers) is the most ergonomic combination today, and it load-tests like an MVC app.

---

## 6. Cross-cutting concerns

### Designing realistic load tests

A load test that drives uniform traffic at a single endpoint with a single body is, charitably, a stress test of a single code path; it does not predict production behaviour. Three sources should drive scenario design.

**Production traffic analysis.** Mine at least one week of nginx/ALB access logs or APM data. For each endpoint extract hit count, p50/p95/p99 latency, body-size distribution, and per-tenant skew. Compute the empirical traffic mix as proportions and reproduce it with weighted scenarios. Pareto's 80/20 — more accurately the heavy tail of a Zipf or log-normal distribution — almost always applies: typically 10–20% of endpoints carry 80%+ of traffic, and within an endpoint a handful of "hot" entities (tenant IDs, product SKUs) dominate. Sampling from the empirical distribution via a weighted CSV feeder is far more realistic than uniform random selection.

**Ramp patterns.** Linear ramps (`rampUsers(N).during(t)` in Gatling, `ramping-vus` in k6) are the default. Exponential ramps better simulate viral or social events. The most realistic option is to replay the actual production morning ramp — traffic doubling roughly every 30 minutes from 06:00 until 10:00, plateau, peak at 14:00 — codified as multiple `stages` derived from log percentiles.

**Think-time distributions.** A common mistake is fixed think time. Real users do not wait identical intervals. Uniform in `[a,b]` is cheap and acceptable when nothing better is known. Exponential with rate λ is appropriate if user arrivals are memoryless (Poisson) — closer to real internet traffic for stateless requests. **Log-normal** is the most empirically validated distribution for human session inter-arrival times: a long tail of slow readers, bulk near the mode. In Gatling: `pause(Duration.ofMillis(median), exponentialPause)` or compute log-normal samples in a custom `exec` step. In k6: `Math.exp(mu + sigma * gaussianRandom())`.

**Weighted scenarios.** Gatling: `randomSwitch().on(percent(70.0).then(browseScn), percent(20.0).then(searchScn), percent(10.0).then(checkoutScn))`. k6: model each journey as a separate scenario with different `rate` or `vus`. Critical: the proportion of write versus read traffic and the cardinality of cache keys must match production, otherwise hit-rate-dependent latency will be wildly wrong.

### Test data strategies

The cardinal failure mode is every VU pulling the same row: backend cache returns a hot record, measured latency is microseconds, production is milliseconds. Avoid this with **circular** (Gatling: `csv("ids.csv").circular()` — the default `queue` strategy crashes once exhausted) or **shared array** (k6: `SharedArray` allocates memory once across all VUs) feeders sized to at least ten times the working set.

Data sources in increasing sophistication: hand-curated CSV/JSON fixtures committed to the repo (fast, repeatable, but stale); pre-generated fixtures from a job that snapshots production IDs nightly with PII removed; on-the-fly synthesis using `datafaker` (JVM) or `@faker-js/faker` (k6 jslib) for create-flows; and the hybrid where you synthesise IDs for create endpoints and sample real IDs for read endpoints from a Redis-backed pool drained via a feeder API.

**Privacy is non-negotiable.** Never use real PII as load-test data. Production snapshots must pass through a deterministic anonymiser (hash plus shuffle) before they touch any non-prod system. GDPR and HIPAA exposure from "I just copied the customers table" is a recurring source of breaches.

### CI/CD integration

The failure plumbing matters. **k6 thresholds** violation produces exit code 99 (since v0.33.0). With `abortOnFail: true` the test stops as soon as the first window violates; otherwise it runs to completion and exits 99 at the end. Note that `check()` failures alone do *not* fail the test — combine with a `checks: ['rate>0.99']` threshold. **Gatling assertions** violation produces a non-zero exit on the Gatling task, and the plugin writes `build/reports/gatling/.../js/assertions.xml` in JUnit format for ingestion by Jenkins or GitLab.

A working GitHub Actions workflow for nightly k6:

```yaml
name: nightly-load
on:
  schedule: [{ cron: '0 2 * * *' }]
  workflow_dispatch:
jobs:
  load:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: grafana/setup-k6-action@v1
      - name: Run k6
        env:
          BASE_URL: https://staging.example.com
          K6_PROMETHEUS_RW_SERVER_URL: ${{ secrets.PROM_RW }}
        run: |
          k6 run -o experimental-prometheus-rw \
                 --tag commit=${{ github.sha }} \
                 --tag branch=${{ github.ref_name }} \
                 tests/rest-load.js
```

GitLab CI for Gatling on every merge:

```yaml
load_smoke:
  stage: test
  image: eclipse-temurin:21
  script: ./gradlew gatlingRun --simulation=com.example.SmokeSimulation
  artifacts:
    paths: [build/reports/gatling]
    reports: { junit: build/reports/gatling/**/js/assertions.xml }
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

The recommended cadence: **smoke tests** (1 VU, 30 s, hard SLOs) on every PR — protects basic integration, catches catastrophic regressions in under a minute. **Capacity tests** (5–10 min at target prod RPS) nightly on `main`. **Soak tests** (4–24 h) weekly. **Stress and breakpoint tests** pre-release.

For trend tracking, both Grafana Cloud k6 and Gatling Enterprise persist runs and overlay them; the OSS approach is to ship metrics to InfluxDB or Prometheus or Loki or Tempo via `--out experimental-prometheus-rw` (k6) or Gatling's JSON output post-processed by a script that writes to a time-series DB tagged by commit SHA.

### Observability during tests

If you run a load test without observing the system under test, you have measured nothing. The required dashboards are latency percentiles (p50/p95/p99 per endpoint, ideally as histograms not pre-aggregated averages), RPS and error rate per endpoint and per status class (4xx versus 5xx tell different stories), saturation (CPU, RSS, GC pause times, thread pool queue depth, DB pool usage and wait time, Kafka consumer lag, HTTP client connection pool exhaustion), and underlying infra (disk IOPS, network bytes, kernel TCP retransmits, conntrack table size).

Two complementary methodologies drive these dashboards: Brendan Gregg's **USE** for every resource (Utilisation, Saturation, Errors) is great for finding *where* saturation is; Tom Wilkie's **RED** for every service (Rate, Errors, Duration) is great for SLO-aligned views from the user's perspective.

**Distributed tracing during a test** is invaluable but the volumes can crush your tracing backend. Strategy: keep production sample rate (e.g., 1%) but enable head-based sampling on a per-request basis triggered by a load-test header. Inject `X-LoadTest-Trace: true` in the load generator; the OpenTelemetry sampler config recognises this and forces sampling. This gives you detailed traces on every load-test request without flooding Tempo or Jaeger with normal traffic.

**Correlation IDs** must flow from load generator into application logs and traces. In Gatling: `.header("X-Request-Id", "#{requestId}")` driven from a UUID feeder. In k6: use `__VU` plus `__ITER` plus `crypto.randomUUID()`. In ghz: `-m '{"x-request-id":"{{.RequestNumber}}"}'`. These IDs let you link a slow data point in the load report to the exact request log line.

### The antipattern checklist, condensed

When you read load-test results, mentally check off: was the load generator saturated before the SUT (run a no-op control test)? Was the test long enough to clear JIT warmup? Were percentile measurements done open-loop (CO-correct) or closed-loop (CO-prone)? Did the data pool exceed the working set so cache hit rates were realistic? Did connection pools have enough headroom that you measured the application, not pool queueing? Did timeouts exceed the expected p99 so the histogram wasn't truncated? Were percentile aggregations done from histograms, not by averaging? Did think time match the distribution shape of real users? Were write traffic and read traffic in production proportions? Were tests run against an environment with realistic network latency, not loopback? Each "no" reduces the validity of the conclusions you can draw.

---

## 7. Practical examples

### A complete Gatling Kotlin simulation testing a Spring Boot REST endpoint

```kotlin
package com.example.loadtest

import io.gatling.javaapi.core.*
import io.gatling.javaapi.core.CoreDsl.*
import io.gatling.javaapi.http.*
import io.gatling.javaapi.http.HttpDsl.*
import net.datafaker.Faker
import java.time.Duration
import java.util.Random

class OrderApiSimulation : Simulation() {

    private val faker = Faker(Random(42L))                  // reproducible

    private val httpProtocol: HttpProtocolBuilder = http
        .baseUrl(System.getProperty("baseUrl", "http://localhost:8080"))
        .acceptHeader("application/json")
        .contentTypeHeader("application/json")
        .userAgentHeader("Gatling/PerfTest")
        .shareConnections()                                  // reuse pool across VUs
        .warmUp("http://localhost:8080/actuator/health")

    private val orderFeeder = generateSequence {
        mapOf(
            "sku"       to faker.commerce().productName(),
            "qty"       to faker.number().numberBetween(1, 5),
            "customer"  to faker.internet().emailAddress(),
            "requestId" to java.util.UUID.randomUUID().toString()
        )
    }.iterator()

    private val createAndRead: ScenarioBuilder = scenario("create-and-read-order")
        .feed(orderFeeder)
        .exec(
            http("POST /api/orders")
                .post("/api/orders")
                .header("X-Request-Id", "#{requestId}")
                .body(StringBody(
                    """{"sku":"#{sku}","qty":#{qty},"customer":"#{customer}"}"""))
                .check(status().shouldBe(201))               // Kotlin: shouldBe, not is
                .check(jsonPath("$.id").saveAs("orderId"))
        )
        .pause(Duration.ofMillis(200), Duration.ofMillis(800))   // uniform think
        .exec(
            http("GET /api/orders/{id}")
                .get("/api/orders/#{orderId}")
                .check(status().shouldBe(200))
                .check(jsonPath("$.sku").shouldBe("#{sku}"))
        )

    init {
        setUp(
            createAndRead.injectOpen(
                nothingFor(Duration.ofSeconds(5)),                                    // settle
                rampUsersPerSec(1.0).to(50.0).during(Duration.ofMinutes(1)),          // warmup
                constantUsersPerSec(50.0).during(Duration.ofMinutes(5))               // steady
            )
        )
        .protocols(httpProtocol)
        .assertions(
            global().responseTime().percentile(95.0).lt(300),       // p95 < 300 ms
            global().responseTime().percentile(99.0).lt(800),       // p99 < 800 ms
            global().failedRequests().percent().lt(1.0),
            forAll().failedRequests().percent().lte(2.0)
        )
        .maxDuration(Duration.ofMinutes(10))
    }
}
```

Run with `./gradlew gatlingRun --simulation=com.example.loadtest.OrderApiSimulation` or `./gradlew gatlingRun -DbaseUrl=https://staging.example.com`. Reports land in `build/reports/gatling/<simulation>-<timestamp>/index.html`, self-contained and ready to copy as a CI artifact.

### A k6 script with thresholds for the same endpoint

```javascript
// orders.js — verified against k6 1.x
import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';
import { randomItem } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

const skus = new SharedArray('skus', () => JSON.parse(open('./skus.json')));

export const options = {
  scenarios: {
    warmup: {
      executor: 'ramping-arrival-rate',
      startRate: 1, timeUnit: '1s',
      preAllocatedVUs: 50,
      stages: [{ duration: '60s', target: 50 }],
    },
    steady: {
      executor: 'constant-arrival-rate',
      rate: 50, timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 100, maxVUs: 500,
      startTime: '60s',
    },
  },
  thresholds: {
    // Steady-state SLOs only — exclude warmup so JIT compilation time doesn't fail the build.
    'http_req_duration{scenario:steady}': ['p(95)<300', 'p(99)<800'],
    'http_req_failed{scenario:steady}':   ['rate<0.005'],
    'checks{scenario:steady}':            ['rate>0.999'],
    dropped_iterations:                   [{ threshold: 'rate<0.005', abortOnFail: true }],
  },
};

const BASE = __ENV.BASE_URL || 'http://localhost:8080';

export default function () {
  const body = JSON.stringify({
    sku: randomItem(skus),
    qty: Math.floor(Math.random() * 4) + 1,
    customer: `vu-${__VU}-iter-${__ITER}@example.com`,
  });
  const res = http.post(`${BASE}/api/orders`, body, {
    headers: { 'Content-Type': 'application/json' },
    tags: { endpoint: 'POST /api/orders' },
  });
  check(res, {
    'status 201': (r) => r.status === 201,
    'has id':     (r) => !!r.json('id'),
  });
  sleep(Math.random() * 0.6 + 0.2);
}
```

Run with `k6 run --out experimental-prometheus-rw=http://localhost:9090/api/v1/write orders.js`. With Prometheus remote-write enabled, k6 metrics show up in the same Grafana you're using for Spring Boot — single pane of glass.

### A k6 gRPC example using `k6/net/grpc` (stable in 1.0)

```javascript
import grpc from 'k6/net/grpc';
import { check, sleep } from 'k6';

const client = new grpc.Client();
client.load(['../proto'], 'hello.proto');                  // init context

export const options = {
  scenarios: {
    rpc_steady: {
      executor: 'constant-arrival-rate',
      rate: 500, timeUnit: '1s', duration: '2m',
      preAllocatedVUs: 50, maxVUs: 200,
    },
  },
  thresholds: {
    grpc_req_duration: ['p(95)<200', 'p(99)<500'],
    checks:            ['rate>0.999'],
  },
};

export default () => {
  if (__ITER === 0) {
    client.connect('localhost:50051', { plaintext: true /*, reflect: true */ });
  }
  const res = client.invoke('hello.HelloService/SayHello',
    { greeting: `vu-${__VU}-iter-${__ITER}` },
    { metadata: { 'x-trace-id': `${__VU}-${__ITER}` }, timeout: '2s' });
  check(res, {
    'status OK': (r) => r && r.status === grpc.StatusOK,
    'has reply': (r) => r.message && r.message.reply !== undefined,
  });
  sleep(0.05);
};

export function teardown() { client.close(); }
```

For streaming, import `Stream` from `k6/net/grpc` and attach `stream.on('data', ...)`, `stream.on('end', ...)`, `stream.on('error', ...)` handlers.

### A k6 WebSocket example using the stable `k6/websockets`

```javascript
import { WebSocket } from 'k6/websockets';
import { check } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const messagesReceived = new Counter('messages_received');
const e2eLatency       = new Trend('ws_e2e_latency_ms', true);

export const options = {
  scenarios: {
    chat_users: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 200 },
        { duration: '5m',  target: 200 },
        { duration: '30s', target: 0   },
      ],
    },
  },
  thresholds: {
    ws_e2e_latency_ms: ['p(95)<250'],
    checks:            ['rate>0.99'],
  },
};

export default function () {
  const ws = new WebSocket(__ENV.WS_URL || 'wss://echo.websocket.events');
  ws.binaryType = 'arraybuffer';

  ws.onopen = () => {
    ws.send(JSON.stringify({ type: 'subscribe', channel: 'orders' }));
    const heartbeat = setInterval(() => {
      ws.send(JSON.stringify({ type: 'ping', t0: Date.now() }));
    }, 1000);
    setTimeout(() => { clearInterval(heartbeat); ws.close(); }, 30000);
  };

  ws.onmessage = (event) => {
    messagesReceived.add(1);
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'pong' && msg.t0) e2eLatency.add(Date.now() - msg.t0);
      check(msg, { 'message has type': (m) => !!m.type });
    } catch (_) { /* binary frame */ }
  };

  ws.onerror = (e) => console.error(`ws error: ${e.error}`);
}
```

If you're stuck on a k6 binary older than 1.6, change the import to `from 'k6/experimental/websockets'`; the API is identical.

### A ghz example for gRPC

```bash
# Local plaintext, with a proto file, HTML report
ghz --insecure \
    --proto ./protos/hello.proto \
    --import-paths ./protos \
    --call hello.HelloService/SayHello \
    -d '{"greeting":"Bert"}' \
    -c 50 \                     # 50 concurrent goroutine workers
    -n 100000 \                 # total 100k requests
    --connections 10 \          # 10 underlying HTTP/2 connections
    --rps 2000 \                # rate-limit to 2k QPS (omit for max)
    --format html \
    -o ./reports/hello.html \
    localhost:50051

# Server reflection enabled → no proto file needed
ghz --insecure --call hello.HelloService/SayHello \
    -d '{"greeting":"Bert"}' -n 5000 -c 20 \
    localhost:50051
```

ghz does *not* have an `--enable-reflection` flag — reflection is automatic when neither `--proto` nor `--protoset` is given.

### A vegeta example for raw throughput

```bash
# Smoke
echo "GET https://api.example.com/health" | \
  vegeta attack -rate=1000 -duration=30s | vegeta report

# Save raw results, multiple report formats
echo "GET https://api.example.com/health" | \
  vegeta attack -name=baseline -rate=2000/s -duration=2m \
                -timeout=2s -max-workers=10000 -output=results.bin

vegeta report -type=text       results.bin
vegeta report -type=json       results.bin > metrics.json
vegeta report -type=hdrplot    results.bin > hdr.txt
vegeta report -type='hist[0,10ms,50ms,100ms,250ms,500ms,1s]' results.bin
vegeta plot -title='Baseline'  results.bin > plot.html
```

`-rate=0` plus `-max-workers=N` simulates closed-loop behaviour (N users sending serially); the default `-rate=R/Ts` is open-loop.

### Gradle integration showing `./gradlew gatlingRun`

The `build.gradle.kts` shown earlier produces three useful invocations:

```bash
./gradlew gatlingRun                                                          # all simulations
./gradlew gatlingRun --simulation=com.example.loadtest.OrderApiSimulation     # specific
./gradlew gatlingRun-com.example.loadtest.OrderApiSimulation                  # legacy syntax
./gradlew gatlingRun -DbaseUrl=https://staging.example.com                    # with system prop
```

Reports land in `build/reports/gatling/<simulation>-<timestamp>/index.html`. Failed assertions cause a non-zero exit, failing the Gradle build — the same way a failing unit test does.

---

## 8. The recommendation, defended

For your context — Spring Boot 3.5+ on Kotlin, predominantly REST and gRPC, with WebSocket and Kafka in the picture, working in Seoul on a 10+ year career and a math PhD — here is the opinionated answer.

**Make Gatling with the Kotlin DSL your primary tool.** The reasoning stacks up: same JVM, same Gradle, same IntelliJ refactoring, same CI Docker image as your production code; simulations live in `src/gatling/kotlin` next to `src/test/kotlin`; you can share DTOs by depending on a `domain` Gradle subproject so a renamed field fails to compile in your load test rather than at runtime; the HTML reports are stakeholder-ready out of the box without setting up Grafana; the open-model `injectOpen` family is the default for SLA testing and is coordinated-omission-correct; the actor model gives you excellent VU density on a single JVM (10k–40k VUs realistic) and maps naturally onto persistent connections for WebSocket; gRPC is now officially supported by Gatling Corp through the `gatling-grpc` plugin; and your Kotlin-PhD brain will appreciate that the DSL composes cleanly through `val` extraction and lambdas. The cost is JVM cold start in CI (~5 seconds versus k6's ~1 second) and the absence of a built-in browser story.

**Make k6 your secondary tool.** Three places where it beats Gatling for your stack: tight Grafana stack integration (single pane of glass when you're already running Prometheus, Loki, and Tempo for Spring Boot Actuator); first-class browser performance testing via `k6/browser` for your React frontend; and Kubernetes-native distributed runs via the k6 Operator and PrivateLoadZone. Use k6 for fast CI smoke tests where the JVM cold start matters, for browser-based tests against the React frontend, for tests that need to mix HTTP and gRPC and Kafka in a single scenario, and for any multi-region work via Grafana Cloud k6.

**Use ghz for gRPC smoke tests and one-off benchmarks** — it's a single binary, has every report format you could want, and outperforms k6 per-core on raw gRPC throughput because it doesn't pay the goja JS interpretation tax. Use **vegeta** for ad-hoc HTTP experiments where you want HDR percentiles in a Unix pipeline.

**For Kafka, layer three tools.** Start with `kafka-producer-perf-test.sh` and `kafka-consumer-perf-test.sh` for raw broker capacity numbers — they ship with every Kafka distribution and are the right zero-effort baseline. Move to `xk6-kafka` (now at 1.0 in 2025, supports Avro/JSON Schema, Schema Registry, SASL, mTLS) for development-team-friendly scenario tests with thresholds. For end-to-end testing — produce on one side, assert in a separate consumer-group or downstream HTTP API — write a thin JVM driver using the Kafka client and call it from Gatling's custom protocol API; this exposes broker → connector → DB → API pipelines, which is the only test that tells you what users actually experience.

**Reach for k6 over Gatling specifically** when you need browser-based testing of your React frontend, when you need multi-region load injection without paying for Gatling Enterprise, when you're already running Grafana Cloud and want zero-glue dashboards correlating load tests with server telemetry, when CI cold-start time is the dominant concern, or when the team writing the test is a frontend or platform team more comfortable in TypeScript than Kotlin.

**Use the OSS editions throughout your initial work.** Both Grafana Cloud k6 and Gatling Enterprise are excellent products, but neither is necessary until you genuinely need multi-region load, scheduled trend dashboards, or distributed runners across cloud zones. The OSS editions of both tools are production-grade and run thousands of VUs from one VM each.

**The version pins to commit to today**: Gatling 3.15.0 with `io.gatling.gradle:3.15.0.1`, Kotlin 2.3.0, JDK 21, Spring Boot 3.5.x (or 4.0.5 for greenfield), Datafaker 2.5.4, Testcontainers latest stable, k6 1.6.x. There is no Gatling 4.x as of April 2026 despite older blog posts hinting at one.

---

## 9. Conclusion: the changes in your understanding

The most important shift to internalise is that load testing is an instrumented experiment in queueing theory, not a "how fast is my server" measurement exercise. Three concrete consequences follow.

First, **open-loop arrival-rate testing is the default for any service with a real user-facing SLO**, because the alternative — closed-loop — measures service time and silently underestimates the latency a real user would see by factors that can reach 35,000× in the deep tail. This is not a question of preference; it's a question of whether your numbers are valid. Choose `injectOpen` in Gatling, `constant-arrival-rate` and `ramping-arrival-rate` in k6, by default. Reserve closed-loop for browser-session simulations and fixed-concurrency batch jobs.

Second, **the latency distribution is the answer, not the mean**. An HDR-style log-percentile plot showing the full curve from p50 through p99.9 is a fundamentally different artifact from a single number, and the difference matters because real production user-facing systems live or die in the deep tail. Build dashboards that show the curve. Read percentiles that compose properly with your SLO budgets. Treat any report that quotes only an average as untrustworthy.

Third, **observability of the SUT is half the test**. Client-side metrics tell you what users experience; server-side metrics tell you why. Without `tomcat.threads.busy`, `hikaricp.connections.pending`, `jvm.gc.pause`, and `histogram_quantile(0.99, http_server_requests_seconds_bucket)` graphed alongside your Gatling or k6 output, you can identify a regression but cannot diagnose it. Wire up Spring Boot Actuator with `percentiles-histogram` enabled, run Prometheus and Grafana alongside every load test, and keep a 5-second scrape interval during the test (reset to 15 s for production).

The novel insight that ties everything together for a mathematician: **load testing rewards Bayesian thinking**. Every measurement is conditional on the validity of an entire chain of assumptions — generator not saturated, JIT warmed up, data pool large enough, network realistic, percentiles computed from histograms not averages, arrivals open-loop, timeouts longer than tail latency, dependencies at production scale. The skill is not learning more tools; it is acquiring a habit of asking, after every load test result, *which of those assumptions is the weakest link in this particular run?* When you can answer that question reliably, you have moved from running load tests to producing trustworthy capacity intelligence — which is the actual job.