---
title: "Apache HttpClient 5 + Spring Boot 4 Learning Plan"
category: "Spring & Spring Boot"
description: "A roughly 4-week hands-on learning plan for mastering HTTP client customization in Spring Boot 4 with Apache HttpClient 5 as the engine. It covers the RestClient → HttpComponentsClientHttpRequestFactory → PoolingHttpClientConnectionManager layering, route-based connection pool tuning beyond the 5-per-route and 25-total defaults, the connect/response/connection-request timeout trio, TLS configuration, Micrometer and Prometheus observability, and k6 load validation, with phase-end labs that build into one reference project."
---

# Apache HttpClient 5 + Spring Boot 4 Learning Plan

**Goal:** master HTTP client customization in Spring Boot 4, covering connection pool tuning, timeouts, TLS, and observability, with Apache HttpClient 5 as the underlying engine.

**Target stack:** Spring Boot 4.x / Spring Framework 7, Kotlin, `httpclient5`, Micrometer and Prometheus, and k6 for load validation.

**Suggested pace:** about 4 weeks at a few evenings per week. Each phase ends with a hands-on lab, and the labs build on each other into one small reference project.

---

## Mental model (read this first)

Three layers, tuned in three different places:

```
@HttpExchange interfaces / HTTP Service Registry   ← per-downstream-service config (Boot 4)
        │
   RestClient  ←  HttpComponentsClientHttpRequestFactory   ← Spring's adapter layer
        │
   CloseableHttpClient + PoolingHttpClientConnectionManager ← where the real tuning lives (HC5)
```

The pool is route-based: limits apply per target host (`maxPerRoute`) and globally (`maxTotal`). The defaults are 5 per route and 25 total, which is fine for a demo and a silent bottleneck in production.

The three timeouts to internalize on day one:

| Timeout | HC5 API | What it bounds |
|---|---|---|
| Connect | `RequestConfig.setConnectTimeout` / `ConnectionConfig.setConnectTimeout` | TCP and TLS handshake to the peer |
| Response (socket) | `RequestConfig.setResponseTimeout` | Waiting for data on an established connection |
| Connection request (lease) | `RequestConfig.setConnectionRequestTimeout` | Waiting for a free connection from the pool. This is the one people forget, and it shows up as "mystery latency" when the pool is undersized |

---

## Phase 0: motivation and failure modes (half a day)

Build intuition for why the defaults hurt before touching any config.

- "RestTemplate & Connection Pool", Yannic Luyckx
  https://medium.com/@yannic.luyckx/resttemplate-and-connection-pool-617ebd924f68
  A load-test war story: a hidden `defaultMaxPerRoute=5` plus a 500 ms backend gives a hard 10 RPS ceiling. It derives pool sizing from Little's law (λ = L / W). Use this formula later when sizing your own pools.
- "Never Use Spring RestClient Default Implementation in Production", DEV
  https://dev.to/akdevcraft/never-use-spring-restclient-default-implementation-in-production-100g
  A defaults recap (RestClient allows 5 per host), plus the checklist: pool size and all three timeouts, always.
- "Optimize Spring RestClient to avoid production bottlenecks", Medium
  https://medium.com/@ahmansour19/optimize-spring-restclient-to-avoid-production-bottlenecks-038f14c085ce
  Why the default `SimpleClientHttpRequestFactory`, which does a new TCP and TLS handshake per request with no reuse, degrades under load, plus a full pooled config with `validateAfterInactivity` and `evictIdleConnections`.

**Checkpoint questions:** given a target of 200 RPS to a service with p99 = 300 ms, what `maxPerRoute` do you need? And what symptom appears if `connectionRequestTimeout` is unset and the pool saturates?

---

## Phase 1: Apache HttpClient 5 core (week 1)

The Spring version doesn't matter here. This layer is pure HC5, and everything transfers.

### Reading

1. HC5 Connection Management (official, 5.6.x), the pool-tuning reference
   https://hc.apache.org/httpcomponents-client-5.6.x/connection-management.html
   - `PoolingHttpClientConnectionManagerBuilder`: `setMaxConnTotal`, `setMaxConnPerRoute`
   - `ConnectionConfig`: `setTimeToLive` (TTL) against `setIdleTimeout`. Know the difference.
   - Background eviction of idle and expired connections (`evictIdleConnections`, `evictExpiredConnections`)
   - Stale-connection validation before reuse (`validateAfterInactivity`)
2. HC5 Examples (classic), runnable samples for every customization axis
   https://hc.apache.org/httpcomponents-client-5.6.x/examples.html
   Focus on request and execution interceptors, per-route `ConnectionConfig`, a custom SSL context, multi-threaded execution, and response handlers with their automatic connection release.
3. The migration guide from 4.x to 5.x (classic APIs). Read it even though you're greenfield, because most blog content is HC4-flavored and this maps old to new.
   https://hc.apache.org/httpcomponents-client-5.6.x/migration-guide/migration-to-classic.html
   - Pool concurrency policy: `STRICT` against `LAX`, where LAX can exceed per-route limits and skips the total cap
   - Pool reuse policy: `LIFO` (a few hot connections, with the rest expiring) against `FIFO` (even reuse, connections stay warm)
   - `DefaultClientTlsStrategy` and TLS 1.3 configuration
4. Baeldung, "HttpClient Connection Management"
   https://www.baeldung.com/httpclient-connection-management
   The key gotcha: without a `Keep-Alive` response header, HC 5.2+ assumes connections stay alive for 3 minutes, so a custom `ConnectionKeepAliveStrategy` is how you handle intermediaries that kill idle connections sooner.

### Lab 1: a standalone HC5 playground (Kotlin, no Spring)

- Spin up WireMock via Testcontainers (your Podman setup works) with a stub that sleeps 500 ms.
- Build a `CloseableHttpClient` by hand with `PoolingHttpClientConnectionManagerBuilder`, and hammer it with 50 coroutines.
- Experiment matrix: `maxPerRoute` ∈ {5, 20, 50} × `connectionRequestTimeout` ∈ {unset, 1s}. Observe throughput and failure modes.
- Enable `org.apache.hc.client5.http` DEBUG logging and read the lease log lines (`total available / route allocated / total allocated`) until they feel familiar. This is your production debugging vocabulary.

---

## Phase 2: wiring into Spring Boot 4 (week 2)

### What changed in Boot 4 (unlearn the Boot 3 blog posts)

- The property namespace was renamed from `spring.http.client.*` to `spring.http.clients.*`, and the reactive namespace merged in.
  - `spring.http.clients.imperative.factory=http-components`
  - `spring.http.clients.connect-timeout`, `spring.http.clients.read-timeout`, `spring.http.clients.redirects`, `spring.http.clients.ssl.bundle`
  - The authoritative list is the Spring Boot 4.0 Configuration Changelog:
    https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Configuration-Changelog
- Modularization: RestClient auto-config now lives in the `spring-boot-restclient` module (`HttpServiceClientAutoConfiguration` and friends), which is relevant if you manage dependencies selectively.
- The Settings API: builders now take `HttpClientSettings`, replacing Boot 3.4's `ClientHttpRequestFactorySettings`.

### Reading

1. The Spring Boot reference, "Calling REST Services" (the current docs are Boot 4)
   https://docs.spring.io/spring-boot/reference/io/rest-client.html
   Client auto-detection order, injecting the pre-configured `RestClient.Builder`, and overriding the factory via properties.
2. `HttpComponentsClientHttpRequestFactoryBuilder` Javadoc, the idiomatic customization hook
   https://docs.spring.io/spring-boot/api/java/org/springframework/boot/http/client/HttpComponentsClientHttpRequestFactoryBuilder.html
   - `withConnectionManagerCustomizer { … }` hands you the `PoolingHttpClientConnectionManagerBuilder` from Phase 1
   - `withHttpClientCustomizer` and `withDefaultRequestConfigCustomizer`
3. The `org.springframework.boot.http.client` package overview, new in this generation
   https://docs.spring.io/spring-boot/api/java/org/springframework/boot/http/client/package-summary.html
   Note `HttpComponentsHttpClientBuilder`, which builds the Apache client directly, and `TlsSocketStrategyFactory`, the clean bridge from Boot SSL bundles to HC5's TLS strategy. Prefer this over hand-rolling `SSLContext` code.
4. The asimio recipe for RestClient with an HC5 connection pool. It was written for Boot 3, so adapt the property names.
   https://tech.asimio.net/resources/code-snippets/restclient-httpclient5-connection-pool-configuration/
   A good shape for production config: `@ConfigurationProperties`-driven pool and timeout settings feeding the connection manager, then `RequestConfig`, then the client, then the factory, then `RestClient`.
5. Boot GitHub issue #48479, a real-world discussion of the customizer pattern and multi-client setups
   https://github.com/spring-projects/spring-boot/issues/48479

### Lab 2: one production-grade RestClient bean

- Start a new Boot 4 and Kotlin project. Add `httpclient5`, and verify via startup debug output that `http-components` is the detected factory.
- Implement a `ClientHttpRequestFactoryBuilderCustomizer<HttpComponentsClientHttpRequestFactoryBuilder>` bean that sets pool sizes, all three timeouts, `validateAfterInactivity`, TTL, and idle eviction, with all values sourced from `@ConfigurationProperties`.
- Add a `ClientHttpRequestInterceptor` for structured request logging, comparable to your Spring Kafka interceptor patterns.
- Wire TLS via an SSL bundle plus `TlsSocketStrategyFactory` against a self-signed WireMock HTTPS stub.
- Re-run the Lab 1 experiment matrix through the Spring stack; the results should match.

---

## Phase 2.5: RestClient API surface deep dive (2-3 evenings, alongside week 2 or 3)

You've read the Framework and Boot reference docs, so this phase goes one level deeper on the `RestClient` layer itself, the middle box in the mental model. One key reframing first: RestClient reuses RestTemplate's infrastructure (message converters, request factories, `ClientHttpRequestInterceptor`), not WebClient's. That means the large body of RestTemplate-era customization content transfers almost directly, and you just register things on `RestClient.Builder` instead.

### Reading, by customization axis

**Full builder surface**
1. Baeldung, "A Guide to RestClient in Spring Boot" (kept current)
   https://www.baeldung.com/spring-boot-restclient
   It goes beyond the docs: chaining multiple `onStatus()` handlers into domain exceptions, API versioning config, request attributes, custom message converters (note `registerDefaults()` to keep the standard converters alongside yours), and `exchange()`, where no default handlers apply and you own status and body processing.
2. The Spring blog, "New in Spring 6.1: RestClient", for the design rationale, the RestTemplate-infrastructure insight, and the `RestClient.create(RestTemplate)` migration path
   https://spring.io/blog/2023/07/13/new-in-spring-6-1-restclient/
3. foojay.io, "Internals of RestClient", a builder walkthrough with code: HTTP library selection, explicit converter registration, default URI, headers, and path variables, `UriBuilderFactory`, and interceptors against initializers
   https://foojay.io/today/spring-internals-of-restclient/
4. The `RestClient.Builder` Javadoc, the densest "advanced config" document available
   https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/client/RestClient.Builder.html
   Pay attention to:
   - `observationRegistry()` and `observationConvention()` (the default is `DefaultClientRequestObservationConvention`)
   - `requestInitializer()` against `requestInterceptor()`: initializers run once per request build, while interceptors wrap the execution chain
   - `apply(Consumer<Builder>)`, for building reusable config bundles ("standard timeouts plus logging plus observability") and applying them across clients
   - `defaultRequest()`, which mutates every request spec before it's sent

**Interceptors and logging**
5. DEV, "Implementing an Interceptor for RestClient", a minimal correct `ClientHttpRequestInterceptor` plus `ClientHttpRequestExecution` chain
   https://dev.to/felipejansendeveloper/implementing-an-interceptor-for-restclient-java-spring-boot-3h75
6. Baeldung, "Spring RestTemplate Request/Response Logging", which applies to RestClient too since they share the factory abstraction
   https://www.baeldung.com/spring-resttemplate-logging
   The trap: response bodies are one-shot streams, so body logging needs `BufferingClientHttpRequestFactory`, which undoes streaming, buffers whole bodies in memory, and can OOM. Gate it behind a debug flag, and never enable it unconditionally in production. A cautionary tale, where Boot's metrics customizer silently added buffering and caused recurring OOM: https://dev.to/btruhand/request-body-buffering-with-spring-s-resttemplate-1958

**Boot-idiomatic customization**
7. `RestClientCustomizer` is the RestClient-layer sibling of the `ClientHttpRequestFactoryBuilderCustomizer` from Phase 2: a bean that configures every auto-configured `RestClient.Builder` in one place. The canonical example, covering observability wiring and the discussion that led to Boot auto-configuring it, is Spring Boot issue #38500:
   https://github.com/spring-projects/spring-boot/issues/38500
   A mental model of the two customizer layers: the factory-builder customizer handles transport and pool concerns (HC5), while `RestClientCustomizer` handles API-level concerns (converters, status handlers, observation, default headers).

**Auth axis**
8. stevenpg.com, "The Ultimate Guide to Spring Web Clients with OAuth2" (Boot 4-era): status-specific error handling, correlation-ID interceptors, and Spring Security 7's `@ClientRegistrationId` for declarative OAuth2 on HTTP interfaces, composing with `@ImportHttpServices` groups
   https://stevenpg.com/posts/ultimate-guide-spring-web-clients-oauth2/

**Source (the final level of detail)**
9. Read `DefaultRestClientBuilder` and `DefaultRestClient` in `spring-web`, plus the auto-configuration classes in Boot's `spring-boot-restclient` module. They're short, and they answer what no guide does: the exact wrapping order (observation, then interceptors, then initializers, then the request factory, then the HC5 exec chain), what `defaultRequest()` actually mutates, and precisely what Boot applies to the injected builder before your code runs.

### Lab 2.5: exercise the API surface (extends the Lab 2 client)

- Add chained `onStatus()` handlers mapping 404 and 5xx to your own domain exceptions, and add one `exchange()` call against a WireMock stub with nonstandard behavior (a meaningful 204, say) and handle the raw response.
- Register a customized Jackson message converter with `registerDefaults()`, and verify the standard converters still work.
- Package your interceptor, observation, and default-header setup as an `apply { }` bundle, and apply it to two different clients.
- Move observability wiring into a `RestClientCustomizer` bean, and confirm via Actuator that `http.client.requests` metrics appear with your convention's tags.
- Add debug-gated body logging with `BufferingClientHttpRequestFactory`, then load-test with it on and off and observe the memory difference. This ties into Lab 4.
- Breakpoint exercise: set a breakpoint inside your interceptor, walk the stack once, and sketch the execution chain from `retrieve()` down to the HC5 connection lease. Ten minutes, permanent clarity.

---

## Phase 3: HTTP service clients and the service registry (week 3)

This is Boot 4's headline client feature, and the natural fit for a microservices codebase: declarative interfaces per downstream service, with per-group configuration layered on top of your tuned HC5 factory.

### Reading

1. The Spring blog, "HTTP Service Client Enhancements", for the official rationale and the group properties
   https://spring.io/blog/2025/09/23/http-service-client-enhancements/
2. Dan Vega, "HTTP Interfaces in Spring Boot 4"
   https://www.danvega.dev/blog/http-interfaces-spring-boot-4
   Covers `@ImportHttpServices`, `RestClientHttpServiceGroupConfigurer`, and how the registry removes the old `HttpServiceProxyFactory` boilerplate.
3. ankurm.com, "Spring Boot 4 HTTP Service Clients", the most complete walkthrough
   https://ankurm.com/spring-boot-4-http-service-clients/
   Multi-API groups, per-group `application.properties` config, error handling, `@RestClientTest`, and the migration path off OpenFeign.
4. The Spring Framework reference, "REST Clients", for the framework-level view of groups, adapters, and the `RestClient` API
   https://docs.spring.io/spring-framework/reference/integration/rest-clients.html

### Lab 3: two downstream services, one tuned engine

- Model two fake downstreams in WireMock, `orders` and `payments`, as `@HttpExchange` interfaces in two service groups.
- Set per-group base URLs and read timeouts via properties, with the shared HC5 pool tuning from Lab 2 underneath.
- Decide deliberately between one shared connection manager and per-group managers. Rule of thumb: a shared manager with per-route limits is usually right, and separate managers are for when downstreams need different TLS, proxies, or isolation guarantees.
- Write `@RestClientTest` slice tests for one interface.

---

## Phase 4: observability and load validation (week 4)

Tuning without measurement is guessing. This phase closes the loop with your existing k6 and Prometheus/Grafana experience.

### Reading

1. The Micrometer reference on Apache HttpComponents instrumentation
   https://docs.micrometer.io/micrometer/reference/reference/httpcomponents.html
   `ObservationExecChainHandler` goes in the exec chain, and its placement relative to the built-in `RETRY` handler decides whether you observe individual retries or only final outcomes.
2. Micrometer's `PoolingHttpClientConnectionManagerMetricsBinder`. Use the `httpcomponents.hc5` package, since the old `httpcomponents` one is deprecated. The gauges are leased, pending, available, and max.
3. "Adding observability for web client", Medium (Duda)
   https://medium.com/duda/adding-observability-for-web-client-657c25751d99
   An end-to-end Actuator and Micrometer walkthrough for client metrics. The code is HC4-era, but the concepts transfer.

### Lab 4: saturate the pool on purpose

- Bind the pool metrics binder to your Lab 3 client, export to Prometheus, and build a Grafana panel showing leased, pending, and available against request latency.
- Write a k6 scenario ramping past the pool capacity. Watch `pending` climb, then watch `connectionRequestTimeout` errors fire. Correlate with HdrHistogram-style latency percentiles: pool saturation manifests as a latency cliff rather than gradual degradation, and the usual coordinated-omission caveats apply, as in your load-testing work.
- Fix it by resizing, re-run, and confirm. Keep the before and after dashboards, which are ideal blog post material.
- A case study to read alongside this: Spring Framework issue #35784, where RestTestClient hung after exactly 5 requests. That is the default per-route limit caught in the wild, diagnosed via the pool's lease debug logs: https://github.com/spring-projects/spring-framework/issues/35784

---

## Phase 5: production hardening and advanced topics (ongoing)

- Align lifetimes with intermediaries. Set the connection TTL and idle timeout below the idle timeout of anything in the path (AWS ALB or NLB, Envoy or Istio sidecars on EKS, NAT). Combine `evictIdleConnections` with `validateAfterInactivity` as a two-layer defense against stale connections. The Baeldung keep-alive section from Phase 1 is the base; verify against your actual LB settings.
- Pool policies under load. Revisit `STRICT` against `LAX` and `LIFO` against `FIFO` from the migration guide, now with your Lab 4 harness. Measure rather than assume. `LIFO` plus eviction suits spiky traffic, and `FIFO` keeps connections warm under steady load.
- Retries. HC5's built-in `HttpRequestRetryStrategy` against Resilience4j at the Spring layer. Decide which layer owns retries, and make the Micrometer observation placement from Phase 4 consistent with that choice.
- The async client and HTTP/2 (optional). `CloseableHttpAsyncClient` with `PoolingAsyncClientConnectionManager`, and ALPN negotiation:
  https://hc.apache.org/httpcomponents-client-5.6.x/migration-guide/migration-to-async-simple.html
  This is mostly relevant if you later back `WebClient` with HC5 or need HTTP/2 multiplexing to a gateway.
- Interception deep dive. HC5 exec-chain interceptors (`addExecInterceptorAfter`) against Spring's `ClientHttpRequestInterceptor`. Know which layer sees retries, redirects, and connection reuse.

---

## Capstone (optional, ties into your interests)

Write a Korean-language blog post, *"Spring Boot 4에서 Apache HttpClient 5 커넥션 풀 튜닝"*, covering the defaults, the three timeouts, Little's-law sizing, the Boot 4 property changes, and your Grafana before and after from Lab 4. It fills a real gap, since almost all Korean-language material on this topic is still RestTemplate plus HttpClient 4.

## Quick reference: the production checklist

- [ ] `maxPerRoute` sized from Little's law per downstream; `maxTotal` at least the sum of expected concurrent routes
- [ ] Connect, response, and connection-request timeouts all set explicitly
- [ ] `validateAfterInactivity` on; TTL and idle timeout below the infrastructure idle timeouts
- [ ] Idle and expired eviction enabled
- [ ] Pool metrics (leased, pending, available) exported, with an alert on sustained `pending > 0`
- [ ] A DEBUG logging recipe for `org.apache.hc.client5.http` documented in your runbook
- [ ] Config externalized via `@ConfigurationProperties`, not hardcoded
