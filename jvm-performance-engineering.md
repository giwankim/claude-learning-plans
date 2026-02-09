# Mastering JVM performance engineering for Spring Boot on Kubernetes

**You can go from zero JVM performance knowledge to production-ready expertise in 16 weeks.** This plan sequences eight interconnected domains—JVM internals, profiling, Spring Boot tuning, API optimization, memory/GC, containers, load testing, and observability—into five phases that build on each other. Each phase pairs foundational reading with hands-on labs so theory immediately converts to muscle memory. The plan assumes 10–15 hours per week, with heavier reading upfront and heavier lab work in later phases.

The core philosophy: **measure before you optimize, understand before you measure**. Weeks 1–6 build the mental model and tool fluency. Weeks 7–12 apply that knowledge to realistic Spring Boot workloads. Weeks 13–16 integrate everything into a production-grade performance engineering workflow you can carry into your team.

---

## Phase 1: JVM internals and profiling foundations (weeks 1–4)

This phase builds the mental model of how the JVM executes your Kotlin code and introduces the diagnostic tools you'll use throughout the rest of the plan. Without this foundation, later optimization work becomes guesswork.

### Week 1–2: How the JVM actually works

**Primary reading:**

Start with **"Java Performance" by Scott Oaks (2nd edition, 2020, O'Reilly)**—the single most important book in this plan. Read chapters 1–5 covering the JIT compiler (C1/C2 tiered compilation), garbage collection fundamentals, and the JVM's tooling ecosystem. Oaks writes for practitioners, not academics, making this ideal for someone with your Spring Boot background. Follow this with chapters on G1 GC and heap memory.

Supplement with **"JVM Performance Engineering" by Monica Beckwith (2024, Addison-Wesley)**. Beckwith is a Java Champion and former GC team lead at Oracle. Her book is the most current text available, covering Generational ZGC, unified GC logging, Project Leyden, and GraalVM. Use it as your reference throughout the entire 16 weeks—it's the only 2024-published book covering the full JVM performance stack.

For JVM internals at a deeper level, **"Optimizing Java" by Benjamin Evans, James Gough, and Chris Newland (2018, O'Reilly)** covers bytecode execution, threading internals, and memory representation. Newland created JITWatch, the JIT compilation visualizer you'll use in week 3.

**Essential online reading:**

Aleksey Shipilëv's **"JVM Anatomy Quarks"** series at shipilev.net is non-negotiable. These 30+ mini-essays each dissect a single JVM behavior—TLAB allocation, escape analysis, lock coarsening, compressed references, GC barriers. Start with Quarks #1 (Lock Coarsening and Elision), #10 (String Interning), #11 (Moving GC and Locality), and #24 (Object Alignment). Each takes 10–15 minutes and delivers more insight per word than any other resource.

**Course:** Take Matt Greecroft's **"Java Application Performance Tuning and Memory Management"** on Udemy. It's hands-on, covers GC algorithms with live demonstrations, and explicitly addresses Kotlin performance characteristics. Complete it within the first two weeks alongside the Oaks book.

**Hands-on exercises:**

Run your existing Spring Boot application with `-XX:+PrintFlagsFinal 2>&1 | grep -E "(UseG1|HeapSize|TieredCompilation)"` and study every default. Enable GC logging with `-Xlog:gc*:file=gc.log:time,level,tags` and upload the output to **GCEasy.io** for automated analysis. Then run the same application three times—once each with `-XX:+UseG1GC`, `-XX:+UseZGC -XX:+ZGenerational`, and `-XX:+UseShenandoahGC`—comparing pause times and throughput in GCEasy's comparison view.

**Milestone:** You can explain tiered compilation stages, draw the G1 heap region layout from memory, articulate why ZGC achieves sub-millisecond pauses, and read a GC log without tooling assistance.

### Week 3–4: Profiling tools that reveal the truth

**Primary resources:**

The **jvmperf.net workshop** by Carl Chesser is a free, self-paced online lab built around a deliberately suboptimal Java web service. It walks you through JDK Mission Control, JFR, Eclipse MAT, and VisualVM with progressive exercises. Complete the entire workshop—it's the single best hands-on introduction to Java profiling.

For JDK Flight Recorder specifically, work through **Marcus Hirt's JMC Tutorial** on GitHub (github.com/thegreystone/jmc-tutorial). Hirt created JMC and designed these labs to cover JFR recording, custom events, JOverflow heap analysis, and advanced rule configuration.

For async-profiler, follow Krzysztof Ślusarski's **"Async-profiler — manual by use cases"** (krzysztofslusarski.github.io, December 2022). This guide uses a Spring Boot application to demonstrate CPU, allocation, lock, and wall-clock profiling with real-world scenarios. Andrei Pangin (async-profiler's creator) personally reviewed it. Clone the companion repo at github.com/krzysztofslusarski/async-profiler-demos.

**Key tools to install and practice:**

- **async-profiler 3.0** (github.com/async-profiler/async-profiler) — generates flame graphs, supports allocation and lock profiling with near-zero overhead
- **JDK Mission Control** — GUI analysis of JFR recordings; install from adoptium.net or Oracle
- **Eclipse MAT** (eclipse.dev/mat) — heap dump analysis with dominator trees, leak suspect reports, OQL queries
- **JITWatch** (github.com/AdoptOpenJDK/jitwatch) — visualizes JIT compilation decisions, inlining, and deoptimizations
- **JOL** (Java Object Layout) by Shipilëv — reveals object memory footprint, padding, and alignment

**Flame graph mastery:**

Read Brendan Gregg's **flame graph page** at brendangregg.com/flamegraphs.html—he invented the visualization. Key interpretation rules: the y-axis is stack depth, the x-axis is sample population (not time), width represents the proportion of time a function was on-CPU, and you should look for the widest frames at the top (leaf methods). Generate flame graphs from async-profiler with `asprof -d 30 -f flamegraph.html <pid>` and practice identifying CPU hotspots in your Spring Boot application.

**Essential conference talks:**

Watch the **"Introduction to JDK Mission Control"** by Billy Korando (Inside.java, May 2024) and **"A Glance at the Java Performance Toolbox"** by Ana-Maria Mihalceanu (Devoxx 2023) for a survey of the full tooling landscape.

**Hands-on exercises:**

Trigger an OOM by setting `-Xmx64m` on a Spring Boot app with a deliberately leaking static list. Capture the heap dump with `-XX:+HeapDumpOnOutOfMemoryError` and analyze it in Eclipse MAT—find the leak via the Dominator Tree and trace the Path to GC Roots. Then install the **flight-recorder-starter** (github.com/mirkosertic/flight-recorder-starter) in your Spring Boot app to expose JFR as an Actuator endpoint. Record a 60-second profile under load and analyze it in JMC.

Learn the **jcmd Swiss Army knife**: `jcmd <pid> VM.flags` for active flags, `jcmd <pid> Thread.print` for thread dumps, `jcmd <pid> GC.heap_dump file.hprof` for heap dumps, `jcmd <pid> JFR.start name=profile settings=profile` for JFR, and `jcmd <pid> VM.native_memory summary` for off-heap tracking (requires `-XX:NativeMemoryTracking=summary`).

**Milestone:** You can attach async-profiler to a running Spring Boot container, generate a flame graph, identify the top 3 CPU hotspots, take a heap dump and find the largest retained objects in Eclipse MAT, and use jcmd for all common diagnostic tasks without looking up syntax.

---

## Phase 2: Spring Boot performance and memory optimization (weeks 5–8)

With tooling fluency established, this phase targets the performance characteristics specific to Spring Boot and dives deep into GC tuning.

### Week 5–6: Spring Boot startup and runtime tuning

**Connection pool tuning (HikariCP):**

Read the HikariCP wiki page **"About Pool Sizing"** on GitHub—it contains the famous formula `connections = (core_count × 2) + effective_spindle_count` and demonstrates how a pool of 10 connections can outperform a pool of 100. Follow with Vlad Mihalcea's blog post **"The best way to determine the optimal connection pool size"** which uses FlexyPool to dynamically discover optimal settings. For production Spring Boot configuration, target `maximumPoolSize` of **10–20**, set `connectionTimeout` to 10 seconds, and set `maxLifetime` to 5 minutes below your database's connection timeout.

**Startup optimization techniques:**

Enable `spring.main.lazy-initialization=true` (available since Spring Boot 2.2) and measure the startup time difference. Audit your auto-configurations with `@SpringBootApplication(exclude = {...})` to remove unused ones. Use Spring Boot Actuator's startup endpoint (`/actuator/startup`) with `FlightRecorderApplicationStartup` to identify which beans take longest to initialize. Read Baeldung's **"Speed up Spring Boot Startup Time"** for a comprehensive checklist.

**Caching strategies:**

Implement a two-level cache using **Caffeine** (local, sub-millisecond) backed by **Redis** (distributed). Baeldung's "Implement Two-Level Cache With Spring" tutorial walks through the custom `CacheManager` configuration. The GitHub project **SuppieRK/spring-boot-multilevel-cache-starter** provides a production-ready starter with randomized TTL to prevent thundering herd effects and Resilience4j circuit breakers for Redis failures.

**Reactive vs. servlet performance:**

The Spring Framework documentation states clearly: **"Reactive and non-blocking generally do not make applications run faster"** but they improve scalability under high concurrency with slow downstream services. Aleksandr Filichkin's benchmark shows WebFlux with WebClient is **4× faster** than blocking Servlet when downstream latency reaches 500ms. For CPU-bound workloads, stick with Servlet. For I/O-bound microservices making many outbound calls, consider Kotlin coroutines with WebFlux—read Sébastien Deleuze's **"Going Reactive with Spring, Coroutines and Kotlin Flow"** on the Spring blog.

**Books for this phase:**

**"High-Performance Java Persistence" by Vlad Mihalcea** is essential for anyone using JPA/Hibernate with Spring Boot. It covers N+1 query detection, batch processing, connection pooling, and caching strategies specific to the persistence layer.

**Hands-on exercises:**

Clone the **spring-boot-performance-analysis** repo (github.com/pbelathur/spring-boot-performance-analysis) and follow its cloud-focused HikariCP tuning guide. Instrument your application with Micrometer's `@Timed` annotation and expose metrics via `/actuator/prometheus`. Build a JMH benchmark comparing Caffeine cache hits, Redis cache hits, and uncached database calls to quantify your caching layer's value.

**Milestone:** Your Spring Boot application starts in under 3 seconds (JVM mode) with lazy initialization and excluded auto-configurations. You can explain HikariCP pool sizing rationale and demonstrate cache hit rates via Micrometer metrics.

### Week 7–8: GC deep dive and memory optimization

**GC algorithm selection framework:**

- **G1GC**: Default since JDK 9. Best general-purpose collector for heaps **2–32 GB**. Tune with `-XX:MaxGCPauseMillis` (default 200ms) and `-XX:InitiatingHeapOccupancyPercent`.
- **Generational ZGC** (`-XX:+UseZGC -XX:+ZGenerational`): Sub-millisecond pauses regardless of heap size. Netflix's March 2024 tech blog post **"Bending Pause Times to Your Will with Generational ZGC"** reports production results showing sub-millisecond pauses AND improved throughput versus G1—contradicting the expected throughput trade-off. Best for **latency-sensitive** services on JDK 21+.
- **Shenandoah**: Red Hat's low-pause collector, similar goals to ZGC. Read the Red Hat Developer guide **"A Beginner's Guide to the Shenandoah Garbage Collector"** (May 2024) for comparison with ZGC.

**Production GC tuning blog posts (essential reading):**

HubSpot's **"G1GC Fundamentals: Lessons from Taming Garbage Collection"** provides battle-tested advice from operating thousands of JVMs. Halodoc's **"Enhancing Java Performance: G1GC to ZGC"** (May 2024) documents migrating 60+ microservices from G1 to ZGC on JDK 17/21, including pitfalls around committed heap reaching max. Gunnar Morling's **"Lower Java Tail Latencies With ZGC"** (2025) provides reproducible benchmarks comparing ZGC and G1 for typical microservice deployments with small heaps.

**Memory analysis techniques:**

Enable Native Memory Tracking with `-XX:NativeMemoryTracking=detail` and inspect off-heap usage with `jcmd <pid> VM.native_memory detail`. This reveals Metaspace, Code Cache, thread stacks, and direct buffer consumption—critical for understanding why your container uses more memory than the heap alone. Use JOL to analyze your domain object layouts and identify padding waste.

**Tools:**

- **GCEasy.io** for automated GC log analysis with ML-powered problem detection
- **GCViewer** (github.com/chewiebug/GCViewer) for desktop GC log visualization
- **HeapHero.io** for online heap dump analysis

**Hands-on exercises:**

Run load tests (using the Gatling skills from Phase 3, or simple `wrk` commands) against your Spring Boot app with different heap sizes (1G, 2G, 4G) at fixed `-Xms` = `-Xmx`. Compare GC frequency, pause distributions (p50/p99), and application throughput for each size. Then migrate from G1 to Generational ZGC and compare tail latencies (p99, p99.9) under identical load. Use async-profiler's allocation profiling (`asprof -e alloc -d 30 -f alloc.html <pid>`) to identify your top allocation sites and determine which can be eliminated.

Clone the **java-gc-demo** repo (github.com/vishalendu/java-gc-demo)—it's a Spring Boot project comparing G1, Generational ZGC, and Shenandoah using Java 23 with integrated Prometheus/Grafana monitoring.

**Milestone:** You have GC log analysis for three collectors (G1, ZGC, Shenandoah) showing pause time distributions and throughput. You can articulate which collector suits which workload profile and justify your production GC choice with data.

---

## Phase 3: API optimization and load testing methodology (weeks 9–11)

This phase equips you to systematically measure and improve API performance using proper benchmarking methodology.

### Week 9: Micro-benchmarking with JMH and API-level tuning

**JMH (Java Microbenchmark Harness):**

JMH, created by Aleksey Shipilëv, is the only correct way to micro-benchmark JVM code. Start with the **JMH Samples** in the official repo (github.com/openjdk/jmh)—these are the definitive tutorial, covering benchmark modes, `@State`, `@Setup`, `Blackhole` (preventing dead-code elimination), `@Fork`, and `@Warmup`. Read Baeldung's **"Microbenchmarking with Java"** for Maven archetype setup and basic usage. Watch Shipilëv's **"Java Microbenchmark Harness (The Lesser of Two Evils)"** talk from Devoxx 2013 for the methodology and common pitfalls.

Oracle's **"Avoiding Benchmarking Pitfalls on the JVM"** technical article covers dead-code elimination, constant folding, and loop optimization—traps that invalidate naive benchmarks. Shipilëv's chapter **"Benchmarking Is Hard—JMH Helps"** in "97 Things Every Java Programmer Should Know" (O'Reilly) is a concise summary of these principles.

**API-level optimization:**

For **Tomcat thread pool tuning**, understand the defaults: `server.tomcat.threads.max=200`, `server.tomcat.accept-count=100`, `server.tomcat.max-connections=8192`. Read DZone's **"Thread Pool vs. Virtual Threads in Spring Boot"** by Aleksei Chaika for benchmarks comparing Tomcat ThreadPool, WebFlux, Coroutines, and Virtual Threads.

For **N+1 query detection**, use Vlad Mihalcea's **Hypersistence Utils** (formerly db-util) which automatically detects N+1 queries during tests. The GitHub project **spring-hibernate-query-utils** by Yann Briancon provides a Spring/Hibernate interceptor for runtime detection. Mihalcea's blog post **"How to Detect the N+1 Query Problem During Testing"** shows the `datasource-proxy` approach.

For **HTTP client tuning**, never create HTTP clients per-request. Use a shared singleton with connection pooling. OkHttp defaults to 5 idle connections evicted after 5 minutes. Apache HttpClient's `PoolingHttpClientConnectionManager` defaults to 5 per route and 25 total—tune both higher for microservice communication patterns.

**Hands-on exercises:**

Create a JMH project using `mvn archetype:generate -DarchetypeGroupId=org.openjdk.jmh` and benchmark: `ArrayList` vs `LinkedList` iteration, `String.format()` vs `StringBuilder`, and the cost of object allocation with vs. without escape analysis (verify with `-XX:+DoEscapeAnalysis` flag toggling). Use JMH's `@BenchmarkMode(Mode.AverageTime)` and `@OutputTimeUnit(TimeUnit.NANOSECONDS)` for precise measurement.

**Milestone:** You can write a correct JMH benchmark that avoids dead-code elimination and constant folding, explain why `@Fork(2)` matters, and have benchmark data proving at least one optimization in your codebase.

### Week 10–11: Load testing with Gatling and k6

**Gatling with Kotlin DSL:**

Gatling added Java/Kotlin DSL support alongside its traditional Scala DSL. The InfoQ article **"Gatling Supports Java DSL for Java and Kotlin-Based Performance Tests"** (September 2023) covers the release. Start with the official **Gatling tutorials** at docs.gatling.io/tutorials/ and clone **mdportnov/kotlin-gatling-tutorial** on GitHub—a complete Spring Boot + Gatling + Kotlin + Gradle example project.

Take the **"Gatling Fundamentals for Stress Testing APIs"** course on Udemy (updated August 2022 for Gatling v3.8) for structured learning. For advanced patterns, the **"Performance Testing Using Gatling — Advanced Level"** Udemy course covers session management, feeders, and Jenkins CI integration.

**k6 as an alternative:**

k6 (grafana/k6 on GitHub, 27k+ stars) uses JavaScript for test scripting with a Go execution engine, making it extremely resource-efficient. The **Better Stack guide "Introduction to Modern Load Testing with Grafana K6"** is the best beginner tutorial. k6 excels at CI/CD integration via its CLI-native design and threshold-based pass/fail gates. Use k6's `constant-arrival-rate` executor to avoid coordinated omission.

**The coordinated omission problem (critical concept):**

Watch Gil Tene's **"How NOT to Measure Latency"** talk (Strange Loop, available on YouTube)—this is mandatory viewing for anyone doing performance work. Coordinated omission occurs when your load testing tool waits for each response before sending the next request, hiding latency spikes that real users experience. Tyler Treat's blog post **"Everything You Know About Latency Is Wrong"** (Brave New Geek) summarizes the problem: CO can make the 99.99th percentile off by a factor of **35,000×**.

Key takeaway: always use **open-model workloads** (constant arrival rate) rather than closed-model (fixed virtual users) when simulating web traffic. Both Gatling (`constantUsersPerSec()`) and k6 (`constant-arrival-rate` executor) support this. Use **Gil Tene's HdrHistogram** (github.com/HdrHistogram/HdrHistogram) for accurate latency recording, and his **wrk2** tool (github.com/giltene/wrk2) for quick CO-corrected HTTP benchmarking.

**Designing realistic load test scenarios:**

Follow this test progression: **smoke test** (1–2 VUs, verify correctness) → **load test** (expected production load) → **stress test** (find breaking point) → **spike test** (sudden traffic surge) → **soak test** (sustained load for 4–8 hours, detect memory leaks). Always include think time (`pause()` in Gatling, `sleep()` in k6) and use CSV/JSON feeders for realistic test data variation.

**Performance regression testing in CI/CD:**

Integrate Gatling into your Gradle build using the official Gatling Gradle plugin. Define threshold assertions (e.g., p95 < 200ms, error rate < 1%) that fail the build on regression. k6 supports this natively via `thresholds` in the script configuration. The academic paper **"Automating Performance Testing in CI/CD"** (ICTSS 2025, Springer) evaluated JMeter, k6, Gatling, Locust, and Artillery in Jenkins pipelines and found **k6 demonstrated the highest resource efficiency**.

**Hands-on exercises:**

Write a Gatling simulation in Kotlin DSL that models a realistic user journey through your Spring Boot API: login → browse → search → checkout. Use `constantUsersPerSec(50).during(Duration.ofMinutes(5))` for open-model load. Run the simulation and analyze the HTML report, focusing on p95 and p99 latencies. Then write the equivalent test in k6 with `constant-arrival-rate` and compare the experience. Run the **"Ctrl+Z test"**: pause your server mid-test and observe whether your tool reports the queuing delay or hides it.

**Milestone:** You have Gatling tests in your CI/CD pipeline with automated p95/p99 threshold gates. You can explain coordinated omission and why open-model testing matters. You've identified and fixed at least one N+1 query and one connection pool misconfiguration through load testing.

---

## Phase 4: Containers, observability, and production readiness (weeks 12–14)

### Week 12: JVM in containers and startup optimization

**JVM container ergonomics:**

Since JDK 10, the JVM automatically detects container CPU and memory limits via `-XX:+UseContainerSupport` (on by default). However, several pitfalls remain. The Pretius guide **"JVM Kubernetes: Optimizing Kubernetes for Java Developers"** and Datadog's **"Java on containers"** blog post are the two most comprehensive references. Key flags for containers:

- Set `-Xms` equal to `-Xmx` for **predictable memory** in Kubernetes (prevents GC thrashing and simplifies resource planning)
- Use `-XX:MaxRAMPercentage=75.0` to reserve **25% for non-heap** (Metaspace, thread stacks, native memory, direct buffers, OS overhead)
- Add `-XX:+AlwaysActAsServerClassMachine` to prevent SerialGC fallback on small containers
- Override CPU detection with `-XX:ActiveProcessorCount=N` when container CPU limits don't align with available cores

The Xebia guide **"A Practical Guide to Kubernetes and JVM Integration"** covers `OOMKilled` troubleshooting—when Kubernetes kills your pod, it's usually because non-heap memory (thread stacks, Metaspace, direct buffers) exceeded the gap between your heap and the container limit.

**CDS and AppCDS for faster startup:**

Class Data Sharing pre-processes class metadata into a shared archive that the JVM memory-maps on startup, dramatically reducing class loading time. Read Sébastien Deleuze's Spring blog post **"CDS with Spring Framework 6.1"** for the official integration. BellSoft's tutorial **"How to use Class Data Sharing with Spring Boot"** provides step-by-step Dockerfile instructions and reports **40% startup improvement** on Spring Petclinic. Vladimir Plizga's Medium article on AppCDS shows **~7× Metaspace reduction** with application-level CDS.

**GraalVM native images:**

Spring Boot 3+ has first-class GraalVM support via Spring AOT processing. Start with the official **Spring Boot GraalVM Native Image Support** documentation and the **"Ahead Of Time and Native in Spring Boot 3.0"** talk by Stéphane Nicoll and Brian Clozel (Devoxx 2022, YouTube). Native images achieve **sub-200ms startup** and significantly reduced memory footprint, but with trade-offs: no runtime reflection without hints, longer build times, and debugging complexity. SoftwareMill's **"How to migrate a Spring Boot app to a native image?"** is the best real-world migration guide, covering a non-trivial application.

**Kubernetes probes for JVM applications:**

Configure **startup probes** with generous thresholds (`failureThreshold: 30, periodSeconds: 10`) to accommodate JVM warmup without triggering restarts. Use separate health groups for liveness and readiness—never use a full `/health` check for liveness, because a database outage shouldn't restart your pod. Read MobiLab's **"A Proper Kubernetes Readiness Probe with Spring Boot Actuator"** for the rationale.

**Hands-on exercises:**

Build a multi-stage Dockerfile that creates a CDS archive during the build phase and uses it at runtime. Measure startup time before and after CDS. Then build a GraalVM native image using `./gradlew nativeCompile` and compare startup time, memory footprint, and throughput against the JVM version. Deploy both to a local Kubernetes cluster (minikube or kind) with properly configured startup, liveness, and readiness probes.

**Milestone:** Your containerized Spring Boot application starts in under 2 seconds with AppCDS (JVM mode) or under 200ms (native image). You can articulate the memory model of a JVM in a container and explain why 75% MaxRAMPercentage is the standard recommendation.

### Week 13–14: Full-stack observability

**The observability stack for Spring Boot on AWS:**

The recommended architecture in 2025: **Micrometer** (metrics facade) → **OpenTelemetry Collector** (pipeline) → **Prometheus** (metrics storage) → **Grafana** (visualization) → **Tempo** (traces) → **Loki** (logs). Spring Boot recommends using Micrometer APIs over direct OpenTelemetry API usage, as Micrometer serves as the abstraction layer.

**Books for observability:**

**"Observability Engineering" by Charity Majors, Liz Fong-Jones, and George Miranda (O'Reilly, 2nd edition 2025)** is the defining text. It covers the shift from monitoring to observability, debugging from first principles, and SLO-based operations. Free PDF available from Honeycomb. **"Learning OpenTelemetry" by Ted Young and Austin Parker (O'Reilly, 2024)** is the practical OTel guide by a co-founder of the project. **"Prometheus: Up & Running" by Julien Pivotto and Brian Brazil (2nd edition, 2023)** covers PromQL, alerting, and Kubernetes service discovery.

**Spring Boot 3 integration:**

Read the official Spring blog post **"Observability with Spring Boot 3"** by Marcin Grzejszczak and Tommy Ludwig (October 2022) for the Micrometer Observation API architecture. The OpenTelemetry Spring Boot Starter became **stable in September 2024**—read the announcement at opentelemetry.io/blog/2024/spring-starter-stable/. For hands-on setup, follow Víctor Orozco's **"A Practical Guide to Implement OpenTelemetry in Spring Boot"** which includes a complete Docker Compose stack with OTel Collector, Grafana, Loki, and Tempo.

**Courses:**

Take **"OpenTelemetry Observability For Java Spring Boot Developers"** on Udemy—it covers OTel Collector pipeline configuration, manual span injection, log-trace correlation, and sampling strategies with a full Grafana/Prometheus/Tempo/Loki stack. For the Prometheus/Grafana stack itself, **"Observability with Grafana, Prometheus, Loki, Alloy and Tempo"** on Udemy is the best-selling course (7 consecutive years) and covers the entire LGTM stack.

**Grafana dashboards for JVM performance:**

Import dashboard **#4701 "JVM (Micrometer)"** from grafana.com—it's the most popular JVM dashboard for Micrometer-instrumented applications, showing heap usage, GC pauses, thread counts, and class loading. Dashboard **#20668 "JVM & DB Metrics"** adds HikariCP connection pool metrics. Build custom panels for your application-specific metrics: HTTP request latency histograms (`http_server_requests_seconds_bucket`), cache hit ratios, and queue depths.

**SLO-based alerting:**

Read Google's SRE Workbook **Chapter 5: "Alerting on SLOs"** (sre.google/workbook/alerting-on-slos/)—it presents six progressively sophisticated alerting approaches, arriving at **multi-window multi-burn-rate alerts** as the recommended production pattern. Use **Sloth** (github.com/slok/sloth, 3k+ stars) to generate Prometheus alerting rules from simple YAML SLO definitions. The free web tool at **prometheus-alert-generator.com** generates production-ready multi-window burn rate rules interactively.

**AWS-specific observability:**

AWS recommends migrating from X-Ray SDKs (entering maintenance mode February 2026) to **OpenTelemetry via ADOT** (AWS Distro for OpenTelemetry). The **AWS One Observability Workshop** at workshops.aws covers CloudWatch, X-Ray, Amazon Managed Prometheus, and Amazon Managed Grafana across EKS and ECS. The GitHub repo **aws-observability/application-signals-demo** is a modified Spring PetClinic showcasing Application Signals on EKS with ADOT.

**Key JVM metrics to monitor in production:**

- `jvm_memory_used_bytes` and `jvm_memory_max_bytes` (heap and non-heap)
- `jvm_gc_pause_seconds` (distribution summary for GC pause durations)
- `http_server_requests_seconds` (request latency by endpoint, method, status)
- HikariCP pool metrics (active connections, pending threads, connection timeout count)
- `process_cpu_usage` and `system_cpu_usage`
- `jvm_threads_live_threads` and `jvm_threads_states_threads`

**Hands-on exercises:**

Set up a complete observability stack using Docker Compose: Spring Boot app → Micrometer → OTel Collector → Prometheus + Tempo + Loki → Grafana. Instrument your application with `@Observed` annotations and custom `Timer` metrics. Create a dashboard that shows request rate, error rate, latency percentiles (p50/p95/p99), GC pause distribution, heap usage, and HikariCP pool utilization. Define an SLO (e.g., 99.9% of requests under 500ms) and configure multi-window burn rate alerts using Sloth.

Clone **spring-boot-observability-playground** (github.com/yashodhah/spring-boot-observability-playground) for a two-service example with HTTP and Kafka distributed tracing.

**Milestone:** You have a Grafana dashboard showing correlated metrics, traces, and logs for your Spring Boot application. Clicking a slow request in the trace view shows the exact database query and GC pause that caused the latency spike. Your SLO alerts fire correctly when you inject artificial latency.

---

## Phase 5: Integration and capstone project (weeks 15–16)

### Week 15–16: Putting it all together

Build a **performance engineering capstone project** that exercises every skill from the previous 14 weeks. Create a realistic Spring Boot + Kotlin microservice (e.g., an order processing service) deployed on Kubernetes with the following components:

**Infrastructure layer:** Containerized with AppCDS, deployed on Kubernetes (local or EKS) with properly configured startup/liveness/readiness probes, resource limits, and JVM flags (`-Xms` = `-Xmx`, `MaxRAMPercentage`, `AlwaysActAsServerClassMachine`, Generational ZGC or G1 based on your workload analysis).

**Application layer:** HikariCP tuned to optimal pool size, Caffeine + Redis two-level caching, N+1 query detection in tests via Hypersistence Utils, Kotlin coroutines for outbound HTTP calls, response compression enabled.

**Observability layer:** Micrometer + OTel Collector → Prometheus + Tempo + Loki → Grafana with JVM dashboard, application dashboard, and SLO-based alerting.

**Load testing layer:** Gatling simulation in Kotlin DSL with open-model workload, realistic user journeys, and CI/CD threshold gates. JMH benchmarks for critical code paths.

**Performance tuning workflow:** Profile under load with async-profiler → identify top CPU hotspots via flame graph → optimize → verify improvement with JMH → validate with Gatling → monitor regression in CI/CD.

**Milestone:** You deliver a documented performance engineering report covering: baseline measurements, identified bottlenecks (with flame graphs and heap analysis), optimizations applied (with before/after data), GC tuning rationale, container resource configuration, and an ongoing monitoring/alerting setup. This report serves as both proof of competence and a reusable template for future performance work.

---

## Essential resource reference by category

### Books (ranked by priority)

| # | Title | Author(s) | Year | Primary value |
|---|-------|-----------|------|---------------|
| 1 | Java Performance, 2nd Ed. | Scott Oaks | 2020 | Foundational JVM performance—JIT, GC, profiling, JMH |
| 2 | JVM Performance Engineering | Monica Beckwith | 2024 | Most current coverage—ZGC, unified logging, GraalVM |
| 3 | Optimizing Java | Evans, Gough, Newland | 2018 | Deep JVM internals—bytecode, threading, memory |
| 4 | High-Performance Java Persistence | Vlad Mihalcea | 2016+ | JPA/Hibernate optimization, connection pooling |
| 5 | Observability Engineering, 2nd Ed. | Majors, Fong-Jones, Miranda | 2025 | Observability philosophy, SLOs, production debugging |
| 6 | Learning OpenTelemetry | Ted Young, Austin Parker | 2024 | Practical OTel setup and operation |
| 7 | Prometheus: Up & Running, 2nd Ed. | Pivotto, Brazil | 2023 | PromQL, alerting, Kubernetes integration |
| 8 | The Garbage Collection Handbook, 2nd Ed. | Jones, Hosking, Moss | 2023 | Academic GC theory (reference, not cover-to-cover) |

### Online courses

- **Java Application Performance Tuning and Memory Management** — Matt Greecroft (Udemy): Best hands-on JVM performance course
- **Gatling Fundamentals for Stress Testing APIs** (Udemy): Structured Gatling learning
- **OpenTelemetry Observability For Java Spring Boot Developers** (Udemy): OTel + Spring Boot + full Grafana stack
- **Observability with Grafana, Prometheus, Loki, Alloy and Tempo** (Udemy): Complete LGTM stack course
- **Understanding the Java Virtual Machine** — Kevin Jones (Pluralsight, 3 parts): JVM memory, class loading, and internals

### Expert blogs and ongoing learning

- **Aleksey Shipilëv** (shipilev.net) — JVM Anatomy Quarks, JMH creator, OpenJDK engineer
- **Inside.java** (inside.java) — Official Oracle JVM team blog
- **Marcus Hirt** (hirt.se/blog) — JMC creator, JFR deep dives
- **Brendan Gregg** (brendangregg.com) — Flame graphs, systems performance
- **Vlad Mihalcea** (vladmihalcea.com) — JPA/Hibernate performance
- **Krzysztof Ślusarski** (krzysztofslusarski.github.io) — Practical async-profiler and JVM profiling
- **Martin Thompson** (mechanical-sympathy.blogspot.com) — Low-latency JVM programming
- **Netflix Tech Blog** — Production JVM engineering at scale
- **GCEasy Blog** (blog.gceasy.io) — Practical GC tuning guides

### Must-watch conference talks

- **"How NOT to Measure Latency"** — Gil Tene (Strange Loop): Coordinated omission, latency measurement
- **"Ahead Of Time and Native in Spring Boot 3.0"** — Nicoll & Clozel (Devoxx 2022): Spring AOT architecture
- **"Java Microbenchmark Harness"** — Aleksey Shipilëv (Devoxx 2013): JMH methodology
- **"Mastering GC: Tame the Beast"** — Jean-Philippe Bempel (Spring I/O 2023): GC tuning strategies
- **"Keeping Your Java Hot"** — Simon Ritter (Devoxx 2023): JIT warmup, CDS, AOT

### Key GitHub repositories

- **openjdk/jmh** — Official JMH with essential samples
- **async-profiler/async-profiler** — Low-overhead profiler with flame graph generation
- **grafana/k6** — Resource-efficient load testing tool
- **slok/sloth** — Prometheus SLO alert generator
- **open-telemetry/opentelemetry-java-examples** — Official OTel Java/Spring Boot examples
- **ionutbalosin/jvm-performance-benchmarks** — JMH benchmarks comparing JIT compilers across JDK versions
- **deephacks/awesome-jvm** — Curated list of JVM performance tools and articles
- **mdportnov/kotlin-gatling-tutorial** — Spring Boot + Gatling + Kotlin example
- **HdrHistogram/HdrHistogram** — Accurate latency recording library by Gil Tene

---

## Conclusion

The path from Spring Boot developer to JVM performance engineer is not about memorizing flags or tools—it's about building an **investigative mindset** where every optimization hypothesis is validated by measurement. The most impactful insight from this plan isn't any single technique; it's the workflow: **observe** (Grafana/Prometheus), **profile** (async-profiler/JFR), **hypothesize** (based on JVM internals knowledge), **benchmark** (JMH), **validate** (Gatling under realistic load), and **monitor** (SLO alerts catching regressions). Weeks 1–4 give you the mental model, weeks 5–8 give you Spring-specific leverage, weeks 9–11 give you measurement rigor, and weeks 12–16 wire everything into a production system. The capstone project in weeks 15–16 is where these skills compound—the flame graph that reveals a surprising hotspot, the GC log that explains a p99 spike, the load test that proves your optimization actually helped under concurrency. That's the moment the investment pays off.