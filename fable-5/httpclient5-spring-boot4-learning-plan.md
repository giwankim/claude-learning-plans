---
title: "Apache HttpClient 5 + Spring Boot 4 Learning Plan"
category: "Spring & Spring Boot"
description: "A ~4-week hands-on learning plan for mastering HTTP client customization in Spring Boot 4 with Apache HttpClient 5 as the engine: the RestClient → HttpComponentsClientHttpRequestFactory → PoolingHttpClientConnectionManager layering, route-based connection pool tuning beyond the 5-per-route/25-total defaults, the connect/response/connection-request timeout trio, TLS configuration, Micrometer/Prometheus observability, and k6 load validation — with phase-end labs that build into one reference project."
---

# Apache HttpClient 5 + Spring Boot 4 Learning Plan

**Goal:** Master HTTP client customization in Spring Boot 4 — connection pool tuning, timeouts, TLS, observability — with Apache HttpClient 5 as the underlying engine.

**Target stack:** Spring Boot 4.x / Spring Framework 7, Kotlin, `httpclient5`, Micrometer/Prometheus, k6 for load validation.

**Suggested pace:** ~4 weeks at a few evenings per week. Each phase ends with a hands-on lab; the labs build on each other into one small reference project.

---

## Mental model (read this first)

Three layers, tuned at three different places:

```
@HttpExchange interfaces / HTTP Service Registry   ← per-downstream-service config (Boot 4)
        │
   RestClient  ←  HttpComponentsClientHttpRequestFactory   ← Spring's adapter layer
        │
   CloseableHttpClient + PoolingHttpClientConnectionManager ← where the real tuning lives (HC5)
```

The pool is **route-based**: limits apply per target host (`maxPerRoute`) and globally (`maxTotal`). Defaults are **5 per route / 25 total** — fine for a demo, a silent bottleneck in production.

The three timeouts to internalize on day one:

| Timeout | HC5 API | What it bounds |
|---|---|---|
| Connect | `RequestConfig.setConnectTimeout` / `ConnectionConfig.setConnectTimeout` | TCP + TLS handshake to the peer |
| Response (socket) | `RequestConfig.setResponseTimeout` | Waiting for data on an established connection |
| Connection request (lease) | `RequestConfig.setConnectionRequestTimeout` | **Waiting for a free connection from the pool** — the one people forget; shows up as "mystery latency" when the pool is undersized |

---

## Phase 0 — Motivation & failure modes (half a day)

Build intuition for *why* defaults hurt before touching config.

- **"RestTemplate & Connection Pool" — Yannic Luyckx**
  https://medium.com/@yannic.luyckx/resttemplate-and-connection-pool-617ebd924f68
  Load-test war story: hidden `defaultMaxPerRoute=5` + 500 ms backend = hard 10 RPS ceiling. Derives pool sizing from Little's law (λ = L / W). Use this formula later when sizing your own pools.
- **"Never Use Spring RestClient Default Implementation in Production" — DEV**
  https://dev.to/akdevcraft/never-use-spring-restclient-default-implementation-in-production-100g
  Defaults recap (RestClient = 5 per host), plus the checklist: pool size + all three timeouts, always.
- **"Optimize Spring RestClient to avoid production bottlenecks" — Medium**
  https://medium.com/@ahmansour19/optimize-spring-restclient-to-avoid-production-bottlenecks-038f14c085ce
  Why the default `SimpleClientHttpRequestFactory` (new TCP+TLS handshake per request, no reuse) degrades under load; full pooled config with `validateAfterInactivity` and `evictIdleConnections`.

**Checkpoint questions:** Given target 200 RPS to a service with p99 = 300 ms, what `maxPerRoute` do you need? What symptom appears if `connectionRequestTimeout` is unset and the pool saturates?

---

## Phase 1 — Apache HttpClient 5 core (week 1)

The Spring version doesn't matter here; this layer is pure HC5 and everything transfers.

### Reading

1. **HC5 Connection Management (official, 5.6.x)** — *the* pool-tuning reference
   https://hc.apache.org/httpcomponents-client-5.6.x/connection-management.html
   - `PoolingHttpClientConnectionManagerBuilder`: `setMaxConnTotal`, `setMaxConnPerRoute`
   - `ConnectionConfig`: `setTimeToLive` (TTL) vs `setIdleTimeout` — know the difference
   - Background eviction of idle/expired connections (`evictIdleConnections`, `evictExpiredConnections`)
   - Stale-connection validation before reuse (`validateAfterInactivity`)
2. **HC5 Examples (classic)** — runnable samples for every customization axis
   https://hc.apache.org/httpcomponents-client-5.6.x/examples.html
   Focus on: request/execution interceptors, per-route `ConnectionConfig`, custom SSL context, multi-threaded execution, response handlers (automatic connection release).
3. **Migration guide 4.x → 5.x (classic APIs)** — read even though you're greenfield; most blog content is HC4-flavored and this maps old→new
   https://hc.apache.org/httpcomponents-client-5.6.x/migration-guide/migration-to-classic.html
   - Pool **concurrency policy**: `STRICT` vs `LAX` (LAX can exceed per-route limits and skips the total cap)
   - Pool **reuse policy**: `LIFO` (few hot connections, rest expire) vs `FIFO` (even reuse, connections stay warm)
   - `DefaultClientTlsStrategy` / TLS 1.3 configuration
4. **Baeldung — HttpClient Connection Management**
   https://www.baeldung.com/httpclient-connection-management
   Key gotcha: without a `Keep-Alive` response header, HC 5.2+ assumes connections stay alive for **3 minutes** — a custom `ConnectionKeepAliveStrategy` is how you handle intermediaries that kill idle connections sooner.

### Lab 1 — Standalone HC5 playground (Kotlin, no Spring)

- Spin up WireMock via Testcontainers (your Podman setup works) with a stub that sleeps 500 ms.
- Build a `CloseableHttpClient` by hand with `PoolingHttpClientConnectionManagerBuilder`. Hammer it with 50 coroutines.
- Experiment matrix: `maxPerRoute` ∈ {5, 20, 50} × `connectionRequestTimeout` ∈ {unset, 1s}. Observe throughput and failure modes.
- Enable `org.apache.hc.client5.http` DEBUG logging and read the lease log lines (`total available / route allocated / total allocated`) until they feel familiar — this is your production debugging vocabulary.

---

## Phase 2 — Wiring into Spring Boot 4 (week 2)

### What changed in Boot 4 (unlearn the Boot 3 blog posts)

- **Property namespace renamed:** `spring.http.client.*` → `spring.http.clients.*`; the reactive namespace merged in.
  - `spring.http.clients.imperative.factory=http-components`
  - `spring.http.clients.connect-timeout`, `spring.http.clients.read-timeout`, `spring.http.clients.redirects`, `spring.http.clients.ssl.bundle`
  - Authoritative list: **Spring Boot 4.0 Configuration Changelog**
    https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Configuration-Changelog
- **Modularization:** RestClient auto-config lives in the `spring-boot-restclient` module (`HttpServiceClientAutoConfiguration` et al.) — relevant if you manage dependencies selectively.
- **Settings API:** builders now take `HttpClientSettings` (replaces Boot 3.4's `ClientHttpRequestFactorySettings`).

### Reading

1. **Spring Boot reference — "Calling REST Services"** (current docs = Boot 4)
   https://docs.spring.io/spring-boot/reference/io/rest-client.html
   Client auto-detection order, injecting the pre-configured `RestClient.Builder`, overriding the factory via properties.
2. **`HttpComponentsClientHttpRequestFactoryBuilder` Javadoc** — the idiomatic customization hook
   https://docs.spring.io/spring-boot/api/java/org/springframework/boot/http/client/HttpComponentsClientHttpRequestFactoryBuilder.html
   - `withConnectionManagerCustomizer { … }` → hands you the `PoolingHttpClientConnectionManagerBuilder` from Phase 1
   - `withHttpClientCustomizer`, `withDefaultRequestConfigCustomizer`
3. **`org.springframework.boot.http.client` package overview** — new in this generation
   https://docs.spring.io/spring-boot/api/java/org/springframework/boot/http/client/package-summary.html
   Note `HttpComponentsHttpClientBuilder` (builds the Apache client directly) and `TlsSocketStrategyFactory` — the clean bridge from Boot **SSL bundles** to HC5's TLS strategy. Prefer this over hand-rolling `SSLContext` code.
4. **asimio recipe — RestClient + HC5 connection pool** (written for Boot 3; adapt property names)
   https://tech.asimio.net/resources/code-snippets/restclient-httpclient5-connection-pool-configuration/
   Good shape for production config: `@ConfigurationProperties`-driven pool/timeout settings → connection manager → `RequestConfig` → client → factory → `RestClient`.
5. **Boot GitHub issue #48479** — real-world discussion of the customizer pattern and multi-client setups
   https://github.com/spring-projects/spring-boot/issues/48479

### Lab 2 — One production-grade RestClient bean

- New Boot 4 + Kotlin project. Add `httpclient5`; verify via startup debug that `http-components` is the detected factory.
- Implement a `ClientHttpRequestFactoryBuilderCustomizer<HttpComponentsClientHttpRequestFactoryBuilder>` bean that sets pool sizes, all three timeouts, `validateAfterInactivity`, TTL, and idle eviction — all values sourced from `@ConfigurationProperties`.
- Add a `ClientHttpRequestInterceptor` for structured request logging (comparable to your Spring Kafka interceptor patterns).
- Wire TLS via an SSL bundle + `TlsSocketStrategyFactory` against a self-signed WireMock HTTPS stub.
- Re-run the Lab 1 experiment matrix through the Spring stack; results should match.

---

## Phase 2.5 — RestClient API surface deep dive (2–3 evenings, alongside week 2/3)

You've read the Framework and Boot reference docs; this phase goes one level deeper on the `RestClient` layer itself — the middle box in the mental model. Key reframing first: **RestClient reuses RestTemplate's infrastructure** (message converters, request factories, `ClientHttpRequestInterceptor`), *not* WebClient's. This means the large body of RestTemplate-era customization content transfers almost directly — you just register things on `RestClient.Builder` instead.

### Reading, by customization axis

**Full builder surface**
1. **Baeldung — "A Guide to RestClient in Spring Boot"** (kept current)
   https://www.baeldung.com/spring-boot-restclient
   Beyond the docs: chaining multiple `onStatus()` handlers into domain exceptions, API versioning config, request attributes, custom message converters (note `registerDefaults()` to keep standard converters alongside yours), and `exchange()` — where no default handlers apply and you own status/body processing.
2. **Spring blog — "New in Spring 6.1: RestClient"** (design rationale; the RestTemplate-infrastructure insight; `RestClient.create(RestTemplate)` migration path)
   https://spring.io/blog/2023/07/13/new-in-spring-6-1-restclient/
3. **foojay.io — "Internals of RestClient"** — builder walkthrough with code: HTTP library selection, explicit converter registration, default URI/headers/path variables, `UriBuilderFactory`, interceptors vs initializers
   https://foojay.io/today/spring-internals-of-restclient/
4. **`RestClient.Builder` Javadoc** — the densest "advanced config" document available. Pay attention to:
   https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/client/RestClient.Builder.html
   - `observationRegistry()` / `observationConvention()` (default: `DefaultClientRequestObservationConvention`)
   - `requestInitializer()` vs `requestInterceptor()` — initializers run once per request build, interceptors wrap the execution chain
   - `apply(Consumer<Builder>)` — build reusable config bundles ("standard timeouts + logging + observability") and apply across clients
   - `defaultRequest()` — mutates every request spec before it's sent

**Interceptors & logging**
5. **DEV — "Implementing an Interceptor for RestClient"** — minimal correct `ClientHttpRequestInterceptor` + `ClientHttpRequestExecution` chain
   https://dev.to/felipejansendeveloper/implementing-an-interceptor-for-restclient-java-spring-boot-3h75
6. **Baeldung — "Spring RestTemplate Request/Response Logging"** (applies to RestClient; same factory abstraction)
   https://www.baeldung.com/spring-resttemplate-logging
   The trap: response bodies are one-shot streams; body logging needs `BufferingClientHttpRequestFactory`, which **undoes streaming, buffers whole bodies in memory, and can OOM** — gate it behind a debug flag, never enable unconditionally in production. Cautionary tale (Boot's metrics customizer silently adding buffering → recurring OOM): https://dev.to/btruhand/request-body-buffering-with-spring-s-resttemplate-1958

**Boot-idiomatic customization**
7. **`RestClientCustomizer`** — the RestClient-layer sibling of the `ClientHttpRequestFactoryBuilderCustomizer` from Phase 2: a bean that configures every auto-configured `RestClient.Builder` in one place. Canonical example (observability wiring, and the discussion that led to Boot auto-configuring it): Spring Boot issue #38500
   https://github.com/spring-projects/spring-boot/issues/38500
   Mental model of the two customizer layers: factory-builder customizer = transport/pool concerns (HC5); `RestClientCustomizer` = API-level concerns (converters, status handlers, observation, default headers).

**Auth axis**
8. **stevenpg.com — "The Ultimate Guide to Spring Web Clients with OAuth2"** (Boot 4-era) — status-specific error handling, correlation-ID interceptors, and Spring Security 7's `@ClientRegistrationId` for declarative OAuth2 on HTTP interfaces, composing with `@ImportHttpServices` groups
   https://stevenpg.com/posts/ultimate-guide-spring-web-clients-oauth2/

**Source (the final level of detail)**
9. Read `DefaultRestClientBuilder` and `DefaultRestClient` in `spring-web`, plus the auto-configuration classes in Boot's `spring-boot-restclient` module. They're short, and they answer what no guide does: the exact wrapping order (observation → interceptors → initializers → request factory → HC5 exec chain), what `defaultRequest()` actually mutates, and precisely what Boot applies to the injected builder before your code runs.

### Lab 2.5 — Exercise the API surface (extends the Lab 2 client)

- Add chained `onStatus()` handlers mapping 404 and 5xx to your own domain exceptions; add one `exchange()` call against a WireMock stub with nonstandard behavior (e.g. 204 with meaning) and handle the raw response.
- Register a customized Jackson message converter with `registerDefaults()`; verify standard converters still work.
- Package your interceptor + observation + default-header setup as an `apply { }` bundle; apply it to two different clients.
- Move observability wiring into a `RestClientCustomizer` bean; confirm via Actuator that `http.client.requests` metrics appear with your convention's tags.
- Add debug-gated body logging with `BufferingClientHttpRequestFactory`; load-test with it on vs off and observe the memory difference (ties into Lab 4).
- **Breakpoint exercise:** set a breakpoint inside your interceptor, walk the stack once, and sketch the execution chain from `retrieve()` down to the HC5 connection lease. Ten minutes, permanent clarity.

---

## Phase 3 — HTTP Service Clients & the Service Registry (week 3)

Boot 4's headline client feature, and the natural fit for a microservices codebase: declarative interfaces per downstream service, with per-group configuration layered on top of your tuned HC5 factory.

### Reading

1. **Spring blog — "HTTP Service Client Enhancements"** (official rationale + group properties)
   https://spring.io/blog/2025/09/23/http-service-client-enhancements/
2. **Dan Vega — "HTTP Interfaces in Spring Boot 4"**
   https://www.danvega.dev/blog/http-interfaces-spring-boot-4
   `@ImportHttpServices`, `RestClientHttpServiceGroupConfigurer`, how the registry removes the old `HttpServiceProxyFactory` boilerplate.
3. **ankurm.com — "Spring Boot 4 HTTP Service Clients"** (most complete walkthrough)
   https://ankurm.com/spring-boot-4-http-service-clients/
   Multi-API groups, per-group `application.properties` config, error handling, `@RestClientTest`, migration path off OpenFeign.
4. **Spring Framework reference — REST Clients** (framework-level view: groups, adapters, `RestClient` API)
   https://docs.spring.io/spring-framework/reference/integration/rest-clients.html

### Lab 3 — Two downstream services, one tuned engine

- Model two fake downstreams (WireMock: `orders`, `payments`) as `@HttpExchange` interfaces in two service groups.
- Per-group base URLs and read timeouts via properties; shared HC5 pool tuning from Lab 2 underneath.
- Decide deliberately: one shared connection manager vs per-group managers. (Rule of thumb: shared manager + per-route limits is usually right; separate managers when downstreams need different TLS, proxies, or isolation guarantees.)
- Write `@RestClientTest` slice tests for one interface.

---

## Phase 4 — Observability & load validation (week 4)

Tuning without measurement is guessing. This phase closes the loop with your existing k6 + Prometheus/Grafana experience.

### Reading

1. **Micrometer reference — Apache HttpComponents instrumentation**
   https://docs.micrometer.io/micrometer/reference/reference/httpcomponents.html
   `ObservationExecChainHandler` in the exec chain; placement relative to the built-in `RETRY` handler decides whether you observe individual retries or only final outcomes.
2. **Micrometer `PoolingHttpClientConnectionManagerMetricsBinder`** — use the **`httpcomponents.hc5`** package (the old `httpcomponents` one is deprecated). Gauges: leased / pending / available / max.
3. **"Adding observability for web client" — Medium (Duda)**
   https://medium.com/duda/adding-observability-for-web-client-657c25751d99
   End-to-end Actuator + Micrometer walkthrough for client metrics (HC4-era code, concepts transfer).

### Lab 4 — Saturate the pool on purpose

- Bind the pool metrics binder to your Lab 3 client; export to Prometheus; Grafana panel: leased/pending/available vs request latency.
- k6 scenario ramping past the pool capacity. Watch `pending` climb, then `connectionRequestTimeout` errors fire. Correlate with HdrHistogram-style latency percentiles — pool saturation manifests as a latency cliff, not gradual degradation (coordinated-omission caveats apply, as in your load-testing work).
- Fix by resizing, re-run, confirm. Keep the before/after dashboards — ideal blog post material.
- Case study to read alongside: Spring Framework issue #35784 (RestTestClient hanging after exactly 5 requests — the default per-route limit caught in the wild, diagnosed via the pool's lease debug logs): https://github.com/spring-projects/spring-framework/issues/35784

---

## Phase 5 — Production hardening & advanced topics (ongoing)

- **Align lifetimes with intermediaries.** Set connection TTL / idle timeout *below* the idle timeout of anything in the path (AWS ALB/NLB, Envoy/Istio sidecars on EKS, NAT). Combine `evictIdleConnections` + `validateAfterInactivity` as a two-layer defense against stale connections. The Baeldung keep-alive section (Phase 1) is the base; verify against your actual LB settings.
- **Pool policies under load.** Revisit `STRICT` vs `LAX` and `LIFO` vs `FIFO` from the migration guide, now with your Lab 4 harness — measure, don't assume. `LIFO` + eviction suits spiky traffic; `FIFO` keeps connections warm under steady load.
- **Retries.** HC5's built-in `HttpRequestRetryStrategy` vs Resilience4j at the Spring layer. Decide which layer owns retries and make the Micrometer observation placement (Phase 4) consistent with that choice.
- **Async client & HTTP/2 (optional).** `CloseableHttpAsyncClient` + `PoolingAsyncClientConnectionManager`, ALPN negotiation:
  https://hc.apache.org/httpcomponents-client-5.6.x/migration-guide/migration-to-async-simple.html
  Mostly relevant if you later back `WebClient` with HC5 or need HTTP/2 multiplexing to a gateway.
- **Interception deep dive.** HC5 exec-chain interceptors (`addExecInterceptorAfter`) vs Spring's `ClientHttpRequestInterceptor` — know which layer sees retries, redirects, and connection reuse.

---

## Capstone (optional, ties into your interests)

Write a Korean-language blog post: *"Spring Boot 4에서 Apache HttpClient 5 커넥션 풀 튜닝"* — defaults, the three timeouts, Little's-law sizing, Boot 4 property changes, and your Grafana before/after from Lab 4. It fills a real gap: almost all Korean-language material on this topic is still RestTemplate + HttpClient 4.

## Quick-reference: the production checklist

- [ ] `maxPerRoute` sized from Little's law per downstream; `maxTotal` ≥ sum of expected concurrent routes
- [ ] Connect, response, and **connection-request** timeouts all set explicitly
- [ ] `validateAfterInactivity` on; TTL + idle timeout below infrastructure idle timeouts
- [ ] Idle/expired eviction enabled
- [ ] Pool metrics (leased/pending/available) exported and alerted on `pending > 0` sustained
- [ ] DEBUG logging recipe for `org.apache.hc.client5.http` documented in your runbook
- [ ] Config externalized via `@ConfigurationProperties`, not hardcoded
