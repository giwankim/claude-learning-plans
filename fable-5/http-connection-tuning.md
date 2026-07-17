---
title: "Tuning HTTP Connection Pool Sizes on the JVM: A Curated Resource Guide for Kotlin + Spring Boot"
category: "Performance & Optimization"
description: "A curated resource guide to HTTP client pool tuning on the JVM: Apache HttpClient 5 (25 total / 5 per-route defaults confirmed in source, ClientHttpRequestFactoryBuilderCustomizer + withConnectionManagerCustomizer as the only supported Spring Boot path to pool sizing) and Reactor Netty/WebClient (2 × processors min-16 default, 45 s acquire timeout, PrematureCloseException from client idle/TTL outliving server or ALB idle timeouts). Covers sizing with Little's Law (p99, not mean) and Kingman's formula, why HikariCP's 'smaller is better' only partially transfers to wait-dominated HTTP pools, aggregating connection counts across Kubernetes replicas, and empirical tuning via k6/Gatling sweeps watched through Micrometer pool gauges."
---

# Tuning HTTP Connection Pool Sizes on the JVM: A Curated Resource Guide for Kotlin + Spring Boot

## TL;DR
- For **Apache HttpClient 5**, the authoritative starting points are the official HttpComponents 5.x "Connection management" and "Connection pooling" pages plus Spring Boot's `ClientHttpRequestFactoryBuilderCustomizer` / `withConnectionManagerCustomizer` — the *only* supported way to set pool size, since `spring.http.client.*` properties cover timeouts and factory type but not pool sizing. Defaults are confirmed in the Apache source (`PoolingHttpClientConnectionManager.java`): `DEFAULT_MAX_TOTAL_CONNECTIONS = 25`, `DEFAULT_MAX_CONNECTIONS_PER_ROUTE = 5`.
- For **Reactor Netty / WebClient**, the Reactor Netty reference guide (HTTP Client + FAQ) and `ConnectionProvider` Javadoc are canonical. Per the Reactor Netty 1.3.5 `ConnectionProvider` Javadoc, the default is "2 * available number of processors (but with a minimum value of 16)" with a 45-second acquire timeout and a pending queue of `2 × maxConnections`. The flagship production failure is `PrematureCloseException` ("Connection prematurely closed BEFORE response"), almost always caused by a client-side idle/TTL longer than the server or load-balancer idle timeout.
- Size pools with **Little's Law** (concurrency = throughput × latency, using p99 not mean), respect queueing-theory saturation (Kingman's formula), aggregate connection counts across Kubernetes replicas, and tune empirically via k6/Gatling sweeps while watching Micrometer pool metrics (`PoolingHttpClientConnectionManagerMetricsBinder` for HC5; `reactor.netty.connection.provider.*` for Netty).

## Key Findings
- **Pool size is not a Spring Boot property.** Spring Boot 3.4/3.5's `spring.http.client.*` namespace configures connect/read timeouts and the factory type, but there is no property for max connections; you must supply a `ClientHttpRequestFactoryBuilderCustomizer` and call `withConnectionManagerCustomizer` to reach `PoolingHttpClientConnectionManagerBuilder.setMaxConnTotal/setMaxConnPerRoute`.
- **Defaults are too small for real services.** HttpClient 5 defaults to 25 total / 5 per route; Reactor Netty defaults to `2 × processors` (min 16) connections with a pending-acquire queue of `2 × maxConnections` and a 45s acquire timeout.
- **The dominant Reactor Netty production issue is idle-timeout mismatch.** Client TTL/maxIdleTime must be shorter than the downstream idle timeout (AWS ALB default 60s), and `evictInBackground` + LIFO leasing dramatically reduce the race that produces `PrematureCloseException`.
- **HTTP pools are wait-dominated, so HikariCP's "smaller is better" logic only partially transfers.** For DB pools the CPU is the bottleneck; for HTTP calls the client mostly waits on the network, so the optimal pool is larger — but still bounded by downstream capacity and by aggregate replica count.
- **Observability is the tuning feedback loop.** Both clients expose leased/available/pending/max gauges through Micrometer; sustained pending > 0 and leased ≈ max are the signals that the pool (or downstream) is saturated.

## Details

### 1. Apache HttpClient 5 pool tuning

**Official Apache HttpComponents documentation**
- **Connection management** — https://hc.apache.org/httpcomponents-client-5.6.x/connection-management.html — The primary reference: covers `ConnectionConfig` (`setTimeToLive`, `setIdleTimeout`, `validateAfterInactivity`), per-route vs total limits, background eviction of idle/expired connections, and keep-alive strategy. Explicitly advises: "Start with the default STRICT policy and conservative limits… Always run periodic eviction of idle and expired connections in long-lived applications."
- **Connection pooling** — https://hc.apache.org/httpcomponents-client-5.6.x/connection-pooling.html — Explains `PoolConcurrencyPolicy`: STRICT (default, per-route FIFO queues, strong fairness), LAX (relaxed fairness, higher throughput), and OFFLOCK (experimental, route-segmented to reduce lock contention). Also documents `setOffLockDisposalEnabled` for moving slow graceful TLS closes off the hot pool lock.
- **`PoolingHttpClientConnectionManager` Javadoc (5.6)** — https://hc.apache.org/httpcomponents-client-5.6.x/current/httpclient5/apidocs/org/apache/hc/client5/http/impl/io/PoolingHttpClientConnectionManager.html — Authoritative on defaults and TTL semantics ("No persistent connection will be re-used past its TTL value") and `validateAfterInactivity` for detecting half-closed stale connections. The default constants (`DEFAULT_MAX_TOTAL_CONNECTIONS = 25`, `DEFAULT_MAX_CONNECTIONS_PER_ROUTE = 5`) are visible directly in the class source at https://github.com/apache/httpcomponents-client/blob/master/httpclient5/src/main/java/org/apache/hc/client5/http/impl/io/PoolingHttpClientConnectionManager.java.
- **Observability (Micrometer / OpenTelemetry)** — https://hc.apache.org/httpcomponents-client-5.6.x/observation.html — Documents the new optional `httpclient5-observation` module (since 5.6) that plugs into Micrometer and can bridge to OpenTelemetry, including pool gauges, DNS, and TLS meters.

**Sizing & timeout mechanics**
- `connectionRequestTimeout` (the timeout to lease a connection from the pool) is the effective backpressure signal: when all connections for a route are leased, requests block until one is released or this timeout throws. Treat it as a fail-fast knob, not a value to raise indefinitely.
- Keep-alive: `DefaultConnectionKeepAliveStrategy` keeps connections alive indefinitely unless a `Keep-Alive` response header is present; Baeldung notes that in HttpClient 5.2 the client assumes a 3-minute keep-alive when the header is absent — a custom strategy is needed to cap this below downstream idle timeouts.

**Spring Boot integration**
- **Calling REST Services (Spring Boot reference)** — https://docs.spring.io/spring-boot/reference/io/rest-client.html — Covers RestClient/RestTemplate auto-configuration, `spring.http.client` properties, and the request-factory abstraction.
- **`HttpComponentsClientHttpRequestFactoryBuilder` / `HttpComponentsHttpClientBuilder` Javadoc** — https://docs.spring.io/spring-boot/3.5/api/java/org/springframework/boot/http/client/HttpComponentsHttpClientBuilder.html — Documents `withConnectionManagerCustomizer(Consumer<PoolingHttpClientConnectionManagerBuilder>)`, the supported path to set pool size.
- **GitHub issue #48479 (RestClient advanced configuration)** — https://github.com/spring-projects/spring-boot/issues/48479 — Contains a concrete, canonical example showing exactly how to size the pool while keeping auto-configuration:
  ```java
  @Bean
  ClientHttpRequestFactoryBuilderCustomizer<HttpComponentsClientHttpRequestFactoryBuilder> customizer() {
      return builder -> builder.withConnectionManagerCustomizer(pool -> {
          pool.setMaxConnPerRoute(100);
          pool.setMaxConnTotal(400);
      });
  }
  ```
- **Baeldung – Apache HttpClient Connection Management** — https://www.baeldung.com/httpclient-connection-management — Practical walkthrough of `BasicHttpClientConnectionManager` vs `PoolingHttpClientConnectionManager`, leasing, and keep-alive strategy.

### 2. Reactor Netty / WebClient pool tuning

**Official Reactor Netty documentation**
- **HTTP Client reference** — https://projectreactor.io/docs/netty/release/reference/http-client.html (snapshot equivalent: https://projectreactor.io/docs/netty/snapshot/reference/http-client.html) — Canonical `ConnectionProvider` builder example with `maxConnections`, `maxIdleTime`, `maxLifeTime`, `maxLifeTimeVariance` (jitter to prevent simultaneous expiry), `pendingAcquireTimeout`, and `evictInBackground`. Also documents the HTTP/2 `Http2AllocationStrategy` (`maxConnections`, `minConnections`, `maxConcurrentStreams`, `strictConnectionReuse`).
- **FAQ / troubleshooting** — https://projectreactor.io/docs/netty/release/reference/faq.html — The definitive checklist for "Connection prematurely closed BEFORE response": obtain a TCP dump to see which peer sends FIN/RST, check proxies/load balancers for idle timeouts, check the target server's idle timeout and max-keep-alive-requests. States connections are validated on acquire but "can be closed at any time after the acquisition."
- **`ConnectionProvider.ConnectionPoolSpec` Javadoc** — https://projectreactor.io/docs/netty/release/api/reactor/netty/resources/ConnectionProvider.ConnectionPoolSpec.html — Authoritative on `pendingAcquireMaxCount` (default `2 × maxConnections`; `0` = fail-fast, `-1` = unbounded), FIFO (default) vs LIFO leasing, `metrics(true)`, and `maxLifeTimeVariance`.
- **`ConnectionProvider` Javadoc** — https://projectreactor.io/docs/netty/release/api/reactor/netty/resources/ConnectionProvider.html — Per the 1.3.5 Javadoc, the default max connections is "2 * available number of processors (but with a minimum value of 16)" and the default acquisition timeout is "Fallback 45 seconds." (Version note below.)

**Defaults to internalize**
- Default `maxConnections` = `2 × availableProcessors` (min 16); default pending queue = `2 × maxConnections`; default acquire timeout = 45s. Note the TCP-level default pool is 500 max / 1000 pending — different from the HTTP client default.
- FIFO (Least Recently Used) is the default leasing strategy; LIFO (Most Recently Used) keeps the freshest connection in use and reduces the chance of grabbing a connection the server is about to close.

**Failure modes**
- `PoolAcquireTimeoutException` / pending-acquire timeout: pool exhausted, requests waited longer than `pendingAcquireTimeout`. Reactor Netty issue #2985 (https://github.com/reactor/reactor-netty/issues/2985) warns that setting `maxConnections` too high can itself trigger `PrematureCloseException` with a "Connect Timeout" root cause from too many concurrent connections.
- `PrematureCloseException: Connection prematurely closed BEFORE response` — the flagship issue, documented across reactor-netty issues #1764 (https://github.com/reactor/reactor-netty/issues/1764), #1502, #1296, and #2825. Root cause is almost always a zombie/half-closed connection: the client's idle timeout is longer than the server/LB idle timeout, so the server sends FIN/RST while the client is reusing the connection. Fixes: set `maxIdleTime` shorter than the downstream idle timeout, enable `evictInBackground`, and/or switch to LIFO leasing.

**Configuring a custom ConnectionProvider on WebClient**
- Build a `ConnectionProvider`, wrap in `HttpClient.create(provider)`, and attach via `new ReactorClientHttpConnector(httpClient)` on `WebClient.builder().clientConnector(...)`:
  ```java
  ConnectionProvider provider = ConnectionProvider.builder("my-pool")
      .maxConnections(50)
      .pendingAcquireMaxCount(-1)          // or bounded for fail-fast
      .pendingAcquireTimeout(Duration.ofSeconds(5))
      .maxIdleTime(Duration.ofSeconds(20)) // < downstream idle timeout
      .maxLifeTime(Duration.ofSeconds(55))
      .evictInBackground(Duration.ofSeconds(30))
      .metrics(true)
      .build();
  WebClient webClient = WebClient.builder()
      .clientConnector(new ReactorClientHttpConnector(HttpClient.create(provider)))
      .build();
  ```
- **Spring Boot – Calling REST Services (WebClient section)** — same reference URL as above — Spring Boot pre-configures a `WebClient.Builder` that shares HTTP resources; inject that builder rather than creating clients ad hoc.
- **`ReactorClientHttpConnector` Javadoc** — https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/http/client/reactive/ReactorClientHttpConnector.html — Notes WebClient participates in `HttpResources` global resources by default; consider a `ReactorResourceFactory` bean with `globalResources=true` for proper lifecycle in Spring apps.

### 3. Sizing methodology

- **HikariCP "About Pool Sizing"** — https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing — The canonical essay showing a smaller pool can improve response times ~50x for CPU-bound DB work. **Caveat for HTTP:** DB pools are CPU/execution-bound, so smaller is faster; HTTP client pools are wait-dominated (the thread spends most time on the network), so the optimal size is larger and governed by concurrency (Little's Law) and downstream capacity, not core count. Cite Hikari for the *methodology and the "bigger isn't better past a point" intuition*, not for the exact numeric formula.
- **HikariCP microservices sizing (issue #1023)** — https://github.com/brettwooldridge/HikariCP/issues/1023 — Directly addresses the Kubernetes trap: N replicas × per-pod pool = the total the downstream sees; the DB/service can end up with the same connection count you tried to reduce. Essential reading for EKS deployments.
- **Little's Law for capacity** — https://systemdr.systemdrd.com/p/capacity-planning-modeling-using — Explains L = λW: concurrency = arrival rate × time-in-system. "Latency is a multiplier on concurrency" — a 2× latency spike doubles required concurrent slots without any change in RPS. Size pools to sustained concurrency at **p99**, not mean.
- **Queueing theory / Kingman's formula** — https://hongyuhe.github.io/queuing/ — Excellent practitioner writeup: the VUT approximation `E[Wq] ≈ (ρ/(1−ρ)) × ((ca²+cs²)/2) × τ` shows waiting time explodes as utilization ρ → 1, and that variability (bursts, GC, slow paths) inflates the tail. "Utilization is destiny." Confirms why you must leave headroom and never run pools at ~95–100% utilization.
- **Kingman's formula (Wikipedia)** — https://en.wikipedia.org/wiki/Kingman%27s_formula — Reference for the G/G/1 mean-wait approximation; notes going from 80% → 90% utilization more than doubles waiting time.
- **Empirical tuning with k6** — https://grafana.com/docs/k6/latest/examples/get-started-with-k6/test-for-performance/ plus the ramping-arrival-rate capacity pattern (https://medium.com/codetodeploy/finding-your-apis-breaking-point-a-baseline-capacity-test-with-k6-grafana-834a676aa297) — Use `ramping-arrival-rate` to sweep load, set p99 thresholds (`http_req_duration: ['p(99)<1000']`), and find the "knee" where throughput plateaus and latency climbs. Plot p99 latency and pool-pending metrics against pool size; the knee is your real capacity.
- **Gatling vs k6** — https://qaskills.sh/blog/gatling-vs-k6-load-testing-2026 — Both are JVM-friendly (Gatling runs on the JVM with Java/Kotlin/Scala DSL); use for choosing a load tool. Gatling gives a polished HTML report per run; k6 streams to Grafana/Prometheus.

### 4. Monitoring and observability

- **Micrometer HC5 binder** — `io.micrometer.core.instrument.binder.httpcomponents.hc5.PoolingHttpClientConnectionManagerMetricsBinder` — package summary at https://www.javadoc.io/static/io.micrometer/micrometer-core/1.11.0/io/micrometer/core/instrument/binder/httpcomponents/package-summary.html — Bind it to your registry: `new PoolingHttpClientConnectionManagerMetricsBinder(connMgr, "my-pool").bindTo(registry)`. Exposes leased/available/pending/max gauges. Note the non-`hc5` package (for HttpClient 4) is deprecated in favor of the `.hc5` package.
- **Reactor Netty metrics** — enable with `ConnectionProvider.builder(...).metrics(true)`; metrics are prefixed `reactor.netty.connection.provider.*`: `total.connections`, `active.connections`, `idle.connections`, `pending.connections`, `pending.connections.time` (timer), `max.connections`, `max.pending.connections`. Documented in the Reactor Netty Observability reference — https://docs.spring.io/projectreactor/reactor-netty/docs/1.2.0-M2/reference/html/observability.html.
- **Signals to alert/tune on:** sustained `pending > 0` (pool saturated — requests queueing to lease); `leased`/`active ≈ max` (pool is the bottleneck); rising acquisition/pending-acquire time. If latency is fine but pending is high, grow the pool; if downstream latency is climbing, growing the pool will only push the queue downstream.
- **Spring Boot Actuator** exposes these via `/actuator/metrics` and Micrometer registries (Prometheus, OTLP). Reactor Netty issue #986 (https://github.com/reactor/reactor-netty/issues/986) notes early versions embedded the pool name in the metric name rather than as a tag — use recent versions for dimensional (tag-based) metrics.

### 5. Timeout interactions relevant to pool sizing

- The four relevant timeouts: **connect timeout** (TCP/TLS establishment), **response/read timeout** (waiting for response), **connection-request/acquire timeout** (leasing from the pool — the backpressure knob), and **keep-alive/TTL** (how long a pooled connection lives).
- **The golden rule: client-side idle/TTL must be shorter than the downstream idle timeout.** Per the AWS Elastic Load Balancing docs (https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-load-balancer-attributes.html), "By default, Elastic Load Balancing sets the idle timeout value for your load balancer to 60 seconds" (valid range 1–4000s). AWS NLB, per the "Introducing NLB TCP configurable idle timeout" blog (https://aws.amazon.com/blogs/networking-and-content-delivery/introducing-nlb-tcp-configurable-idle-timeout/), defaults to "350 seconds" for TCP (and 120s for UDP), configurable 60–6000s since Sept 2024. If the client keeps a connection idle longer than the LB will, the LB silently closes it and the next reuse fails (`PrematureCloseException` / connection reset). Set HttpClient 5 `ConnectionConfig.setTimeToLive`/`setIdleTimeout` and Reactor Netty `maxIdleTime`/`maxLifeTime` below 60s for ALB-fronted services.
- AWS also added an "HTTP client keepalive duration" attribute (`client_keep_alive.seconds`) in March 2024 that caps total connection lifetime independently of the idle timeout; per AWS it defaults to 3600 seconds (1 hour) and can be set between 60 seconds and 7 days, and cannot be set below 60s. This is relevant to setting client `maxLifeTime`.
- **Stale connection checks:** HttpClient 5's `validateAfterInactivity` re-validates connections idle beyond a threshold before leasing; Reactor Netty validates on acquire but recommends `evictInBackground` for proactive cleanup.

### 6. Kotlin-specific notes

- **Spring Framework Coroutines reference** — https://docs.spring.io/spring-framework/reference/languages/kotlin/coroutines.html — Coroutine support activates when `kotlinx-coroutines-core` and `kotlinx-coroutines-reactor` are on the classpath; shows WebClient consumed from `suspend` functions via `.retrieve().awaitBody<T>()` and `.awaitExchange { it.awaitBody<T>() }`, plus the `coroutineScope { async { … } }` pattern for parallel fan-out (which directly multiplies connection concurrency — each concurrent `async` leg leases a connection).
- **`awaitBody` KDoc** — https://docs.spring.io/spring-framework/docs/current/kdoc-api/spring-webflux/org.springframework.web.reactive.function.client/await-body.html — The "Coroutines variant of `WebClient.ResponseSpec.bodyToMono`"; it is a thin wrapper over reactor's `Mono.awaitSingle()` (https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-reactor/kotlinx.coroutines.reactor/await-single.html), which awaits without blocking the event-loop thread. Because WebClient/Netty is non-blocking, coroutine concurrency is bounded by `maxConnections`, not by threads.
- **Blocking HttpClient 5 from a `suspend` function** — wrap blocking calls in `withContext(Dispatchers.IO)`. Per the official kotlinx.coroutines `Dispatchers.IO` docs (https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html), the number of threads "is limited by the value of the 'kotlinx.coroutines.io.parallelism' … system property. It defaults to the limit of 64 threads or the number of cores (whichever is larger)." **Sizing implication:** the dispatcher's thread limit and the connection pool's max-total size bound each other — if the pool is bigger than the dispatcher, connections sit idle; if the dispatcher is bigger than the pool, threads block waiting to lease. Best practice: use `Dispatchers.IO.limitedParallelism(n)` with `n` aligned to `maxConnTotal`.
- **KT Academy – network client threads** — https://kt.academy/article/network_client_threads — Explains that many "coroutine-friendly" clients still block a thread per active request under the hood, so the thread pool running blocking calls effectively caps concurrency and must be sized in relation to the connection pool. Companion: https://kt.academy/article/cc-dispatchers restates "The limit of Dispatchers.IO is 64 (or the number of cores if there are more)" and demonstrates `limitedParallelism`.

**Korean-language resources (high quality)**
- **Hyperconnect Tech Blog – "Spring WebClient에서 새어나가는 메모리 잡기"** — https://hyperconnect.github.io/2022/10/07/troubleshoot-webclient-oom.html — A strong production case study: an old OpenTelemetry agent caused WebClient to create a new connection pool per request (file-descriptor leak), fixed by upgrading the agent. Excellent for understanding how connection-pool reuse and observability agents interact.
- **DEV.to – yangbongsoo, "WebClient timeout and connection pool Strategy"** — https://dev.to/yangbongsoo/webclient-timeout-and-connection-pool-strategy-2gpn — Bilingual-friendly deep dive (by a Korean engineer) on `PrematureCloseException`, the TCP RST mechanism, FIFO vs LIFO leasing, and the `keepAlive(false)` fix. One of the clearest treatments of the idle-timeout race.
- **토리맘의 한글라이즈 프로젝트 (godekdls) – Reactor Netty Korean translation** — https://godekdls.github.io/Reactor%20Netty/tcpclient/ — A faithful Korean translation of the official Reactor Netty reference, useful for reading the connection-pool and metrics sections in Korean.
- **Klarciel – "Netty PrematureCloseException"** — https://klarciel.net/wiki/troubleshooting/troubleshooting-webclientrequestexception/ — Concise Korean troubleshooting note explaining the KeepAliveTimeout vs client idleTimeout crossing scenario and FIFO/LIFO + `evictInBackground` validation behavior.

## Recommendations

**Stage 1 — Establish a baseline (before touching pool size).**
1. Turn on metrics for both clients (`metrics(true)` for Netty; bind `PoolingHttpClientConnectionManagerMetricsBinder` for HC5) and surface leased/pending/max in Grafana via Actuator + Micrometer.
2. Set explicit timeouts: connect (1–2s), response/read (per SLA), connection-request/acquire (fail-fast, e.g. 1–5s), and — critically — client idle/TTL shorter than 60s for ALB-fronted downstreams.
3. Leave `PoolConcurrencyPolicy` at STRICT (HC5) and switch leasing to LIFO if you see `PrematureCloseException`; enable `evictInBackground` (Netty) / periodic eviction (HC5).

**Stage 2 — Size with Little's Law, then validate empirically.**
4. Compute target concurrency = peak throughput (req/s to that route) × **p99** latency (s). Set `maxConnPerRoute` (HC5) / `maxConnections` (Netty) at or slightly above that per pod.
5. Divide by expected replica count and confirm the *aggregate* (replicas × per-pod pool) is within downstream/LB capacity (the issue #1023 trap).
6. Run a k6 `ramping-arrival-rate` sweep, plotting p99 and pool-pending against pool size. Adopt the size at the knee of the curve; stop increasing once pending stays near 0 and p99 is flat.

**Stage 3 — Operationalize.**
7. Alert on sustained `pending > 0` and `leased ≈ max`. If both fire but downstream latency is healthy, grow the pool; if downstream latency is climbing, a bigger pool just moves the queue — scale the downstream or add backpressure instead.
8. Re-tune whenever you change replica count, downstream capacity, or observe latency regressions.

**Thresholds that change the recommendation:**
- If p99 latency climbs while throughput is flat during the sweep → you're past the knee; reduce pool size or scale downstream.
- If `pending` is persistently high but downstream is fast → pool is undersized; grow it.
- If `PrematureCloseException` appears → idle/TTL mismatch; shorten client idle time below the LB/server idle timeout before anything else.
- If Kotlin `Dispatchers.IO` saturates (blocking HC5 path) before the pool does → raise `limitedParallelism` or `kotlinx.coroutines.io.parallelism`, or move to the non-blocking WebClient path.

## Caveats
- **Version drift on defaults:** Reactor Netty's documented default `maxConnections` fallback text varies between versions — the 1.3.5 Javadoc reads "2 * available number of processors (but with a minimum value of 16)," while some 1.0.x Javadocs read "available number of processors … minimum value of 16" (without the ×2). The HttpClient 5 defaults (25/5) are stable across 5.x. Always confirm against the exact library version on your classpath.
- **The HikariCP formula does not transfer directly.** Its `(cores × 2) + spindles` formula is for CPU-bound DB pools; HTTP client pools are wait-dominated and are sized by concurrency and downstream capacity instead. Use Hikari for the *reasoning*, not the number.
- **Kingman/Little's Law are models, not guarantees.** Retries, correlated bursts, and heavy-tailed service times break the assumptions; always validate the predicted knee against a real load test.
- **Some cited engineering blogs (Medium, DEV, personal blogs) are secondary sources.** They illustrate patterns well but defer to the official Apache, Reactor Netty, Spring, Micrometer, and AWS docs for authoritative behavior.
- **The "64 threads" for `Dispatchers.IO` is a documented default, not an immutable constant** — it is `max(64, cores)` and tunable via `kotlinx.coroutines.io.parallelism`; don't hard-code assumptions around it.
- **AWS timeout figures are defaults on standard configurations** — ALB idle timeout (60s), NLB TCP idle timeout (350s), and ALB HTTP client keepalive duration (3600s) are all adjustable, and internal/self-managed load balancers or proxies (NGINX, Envoy) will have their own values; always verify the actual idle timeout on the specific hop in front of your service.