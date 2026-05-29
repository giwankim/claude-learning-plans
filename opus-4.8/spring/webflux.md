---
title: "Spring WebFlux — Reactive Programming Curriculum"
category: "Spring & Spring Boot"
description: "Depth-first, resource-mapped curriculum for a Kotlin/Spring Boot 3.x backend engineer: rebuild the non-blocking mental model, master imperative Project Reactor, bridge to Kotlin coroutines, then build a production WebFlux service (R2DBC, reactive Redis, Reactor Kafka, reactive security, observability) — with clear guidance on when Java 21 virtual threads make reactive unnecessary."
---

# Mastering Reactive Programming with Spring WebFlux: A Depth-First, Resource-Mapped Curriculum for a Kotlin/Spring Boot 3.x Backend Engineer

## TL;DR
- **Follow a strict depth-first path:** rebuild the non-blocking mental model from scratch → master imperative Project Reactor (Mono/Flux, operators, schedulers, Context, StepVerifier) → only then bridge to Kotlin coroutines → then build a production WebFlux service (R2DBC + reactive Redis + Reactor Kafka + reactive security + full observability). The single biggest trap is treating WebFlux as "MVC with Mono" — every ThreadLocal-based mechanism (MDC, SecurityContextHolder, transactions) breaks and must be relearned.
- **Budget ~16 weeks across 8 phases (0–7)**, each with a concrete deliverable, culminating in a production-style service deployable to your EKS stack. Implement primitives from scratch first (a toy Publisher/Subscriber honoring the Reactive Streams spec) before leaning on Reactor.
- **Be clear-eyed about when NOT to use WebFlux:** with Java 21 virtual threads + Spring MVC, most CRUD apps no longer need reactive, and your existing Hibernate/JPA code is fundamentally blocking and incompatible with the reactive stack. Reactive pays off for high-fan-out API aggregation (BFF), streaming/SSE, and very high-concurrency I/O-bound gateways — exactly the use cases Korean firms (Kakao Pay BFF, 배민스토어, LG U+) adopted it for.

## Key Findings

1. **The mental model must be rebuilt, not ported.** Reactor's reference guide is explicit that subscribing triggers data flow, request signals propagate upstream, and backpressure is a feedback signal up the chain. Coming from blocking servlet MVC, the learner must internalize the event-loop (Netty) model versus thread-per-request before touching operators. The problem reactive solves is the C10k problem — coined by software engineer Dan Kegel in 1999, citing the Simtel FTP host cdrom.com "serving 10,000 clients at once over 1 gigabit-per-second Ethernet" — and the thread-pool exhaustion that the thread-per-request model hits under high I/O-bound concurrency.

2. **Imperative Reactor first is the right call.** Korean engineering blogs (LG U+, 배민광고리스팅) confirm coroutines are easier to *read*, but they also warn that to use WebFlux well you must deeply understand how Reactor and Reactive Streams work. Coroutines hide Reactor; you cannot debug what you don't understand. Master Reactor, then adopt coroutines as an ergonomic layer.

3. **JPA/Hibernate is blocking and incompatible.** Per the official Spring Data R2DBC reference, the framework does not use a full mapping-metadata/ORM model and "is not an ORM" — no lazy loading, no caching, and (per Hantsy/community guidance) it "does not yet offer any mechanism to manage entity relationships," so there is no @OneToMany/@ManyToMany and joins must be issued manually. An active transaction pins the connection, and savepoints arrived only in newer Spring versions. This is the single largest adoption cost for teams with large JPA codebases.

4. **ThreadLocal breaks everywhere.** SecurityContextHolder → ReactiveSecurityContextHolder (Reactor Context); MDC logging requires Micrometer Context Propagation + `Hooks.enableAutomaticContextPropagation()`; transactions use Reactor Context, not ThreadLocal. Trace-context propagation across reactive/coroutine boundaries is a known, sharp-edged problem with real open Spring Boot bugs — e.g. issue #38593, verbatim title "OpenTelemetry TraceContext does not propagate through reactive context properly in 3.1.6 / 3.2.0," which reports that "after updating to 3.1.6 (or 3.2.0) the traceId is lost within the controller at various spots," with companion issue #38624 ("Tracing missing in log statement before returning the Mono chain after boot 3.2 webflux upgrade").

5. **Virtual threads (Java 21) are a serious alternative.** For most CRUD-with-JDBC apps, Spring MVC + virtual threads delivers comparable scalability with simpler, debuggable, blocking-style code — making WebFlux adoption hard to justify unless you need streaming, backpressure, or extreme fan-out.

## Details: The Phased Curriculum

### Phase 0 — Orientation & Environment (Week 1)
**Objectives:** Understand *why* reactive exists; set up tooling; frame the whole journey.

**Topics:** thread-per-request vs event-loop; the C10k problem (Kegel, 1999); thread-pool exhaustion; what "non-blocking" buys you and what it costs; where WebFlux fits in your EKS/Aurora/Redis/Kafka stack.

**Resources:**
- Project Reactor reference, "Introduction to Reactive Programming" — projectreactor.io/docs/core/release/reference/reactiveProgramming.html (authoritative, current 3.6+/3.7+).
- Spring WebFlux reference, "Spring WebFlux" overview — docs.spring.io/spring-framework/reference/web/webflux.html.
- Dan Kegel, "The C10K problem" — kegel.com/c10k.html (the original framing of the scalability problem reactive addresses).
- Korean: 토리맘의 한글라이즈 프로젝트 (godekdls.github.io/Reactive Spring) and madplay.github.io — high-quality Korean translations/summaries of the WebFlux reference, useful for fast comprehension.
- Talk: Josh Long, "Reactive Spring" (InfoQ presentation, infoq.com/presentations/reactive-spring-sao-paulo-2019) — frames the problem ("how do I handle more users?") clearly.
- 우아한형제들: "3월 우아한 Tech 세미나 후기" (techblog.woowahan.com/2619/) — 토비(이일민)'s reactive seminar recap, plus the candid trade-off discussion (readability cost vs latency gains; "why not just Node?").

**Deliverable:** A one-page written decision memo: "For which of our services would WebFlux help, and why?" — naming specific candidate services (BFF/aggregation, SSE, high-fan-out gateways) and explicitly ruling out JPA-heavy CRUD.

### Phase 1 — Reactive Streams From Scratch (Weeks 2–3)
**Objectives:** Internalize the spec by implementing it. Build a toy Publisher/Subscriber/Subscription honoring backpressure before using Reactor.

**Topics:** Publisher, Subscriber, Subscription, Processor; the `request(n)` demand protocol; onSubscribe/onNext/onError/onComplete contract; cold vs hot publishers; backpressure strategies (buffer, drop, latest, error); the JDK 9 `java.util.concurrent.Flow` equivalence.

**Resources:**
- Reactive Streams spec (reactive-streams.org) and the `Flow` API.
- Reactor reference, "Introduction to Reactive Programming" (assembly-line analogy for backpressure).
- 토비의 봄 TV — "스프링 리액티브 프로그래밍 (1) Reactive Streams" (youtube.com/watch?v=8fenTR3KOJo) and subsequent episodes (2 = …v=DChIxy9g19o, 4 = …v=aSTuQiPB4Ns, 8, 12 WebFlux = …v=ScH7NZU_zvk); the canonical Korean-language deep dive into building reactive primitives from the ground up.
- Book: "Reactive Programming with RxJava" (Tomasz Nurkiewicz & Ben Christensen, O'Reilly) — best conceptual grounding in Observable/backpressure semantics even though it's RxJava; dated on APIs but excellent on concepts.

**Deliverable:** A from-scratch `Publisher<T>`/`Subscriber<T>` that emits N items honoring `request(n)`, signals completion/error, supports cancellation, and demonstrates one cold and one hot source. Validate manually against the spec rules.

### Phase 2 — Imperative Project Reactor Mastery (Weeks 4–7) — the core of the plan
**Objectives:** Achieve deep, fluent command of Reactor before any coroutines.

**Topics (depth-first):**
- Mono vs Flux; creation (just, defer, fromCallable, create, generate, fromFuture).
- Transforming/filtering: map, flatMap, concatMap, flatMapSequential, filter, switchIfEmpty, defaultIfEmpty.
- **flatMap vs concatMap vs flatMapSequential** (concurrency vs ordering vs ordered-concurrency) — a critical distinction.
- Combining: zip, merge, concat, combineLatest, then/thenMany.
- Error handling: onErrorResume, onErrorReturn, onErrorMap, retry, retryWhen (with exponential backoff).
- Schedulers and the threading model: subscribeOn vs publishOn; Schedulers.parallel/boundedElastic/single; why subscribeOn affects the source and only the first matters.
- Reactor Context (contextWrite / Context / ContextView) — the reactive replacement for ThreadLocal.
- Testing: StepVerifier (expectNext, expectError, verifyComplete), withVirtualTime for time-based tests, expectAccessibleContext, TestPublisher.
- Debugging: checkpoint(), Hooks.onOperatorDebug(), and the ReactorDebugAgent / reactor-tools (production-safe stack reconstruction).

**Resources:**
- **Reactor reference guide** (projectreactor.io/docs/core/release/reference) — the primary text; read "Reactor Core Features," "Handling Errors," "Schedulers," "Testing," "Context."
- Reactor Javadoc with marble diagrams (projectreactor.io/docs/core/release/api) — the "Which operator do I need?" appendix is invaluable.
- **Udemy: "Reactive Programming in Modern Java using Project Reactor"** by Vinoth Selvaraj — confirmed bestseller rated 4.6 out of 5 (3,280 ratings) per the Udemy reactive-programming topic page; pure hands-on Reactor; companion repo at github.com/souvik2805/Java-Reactive-Programming.
- Udemy: "Mastering Java Reactive Programming [From Scratch]" (covers building a custom Publisher/Subscriber, schedulers, sinks).
- Baeldung: "Testing Reactive Streams Using StepVerifier and TestPublisher" (baeldung.com/reactive-streams-step-verifier-test-publisher).
- GitHub: reactor/reactor-core (source + tests as reference); the "project-reactor from zero to hero" gist (gist.github.com/Lukas-Krickl/...) for internals.
- Book: Josh Long, "Reactive Spring" (Reactor chapters) — and the community-recommended "Unraveling Project Reactor" (Esteban Herrera) for Reactor-only focus before tackling Spring integration.

**Deliverable:** A console/CLI app that consumes 2–3 public APIs reactively with WebClient, combining results via zip/flatMap, with full error handling (retryWhen + exponential backoff, onErrorResume fallbacks), correct subscribeOn/publishOn placement, and a comprehensive StepVerifier test suite (including withVirtualTime). Add checkpoint() and turn on ReactorDebugAgent to see the difference in stack traces.

### Phase 3 — The Kotlin Coroutines Bridge (Weeks 8–9)
**Objectives:** *Only after Reactor mastery*, learn the coroutine interop and decide when to prefer coroutines vs raw Reactor.

**Topics:** suspend functions; structured concurrency (coroutineScope, async/await, launch); Flow (cold) and SharedFlow/StateFlow (hot); kotlinx-coroutines-reactor and kotlinx-coroutines-reactive; awaitSingle/awaitFirst/awaitFirstOrNull/awaitSingleOrNull; Publisher.asFlow / Flow.asFlux / mono { } / flux { } builders; ReactorContext ↔ CoroutineContext propagation; Dispatchers (and why blocking work goes on Dispatchers.IO / boundedElastic); coroutine cancellation vs Reactor cancellation; **coroutine exception handling** (try/catch around suspend vs Reactor's onError).

**Resources:**
- Spring blog: "Going Reactive with Spring, Coroutines and Kotlin Flow" (spring.io/blog/2019/04/12/going-reactive-with-spring-coroutines-and-kotlin-flow) — the canonical bridge reference.
- Kotlin docs: "Asynchronous Flow" (kotlinlang.org/docs/flow.html); kotlinx-coroutines-reactive/reactor READMEs and ReactorContext.kt source (github.com/Kotlin/kotlinx.coroutines).
- Baeldung on Kotlin: "Non-Blocking Spring Boot with Kotlin Coroutines" (baeldung.com/kotlin/spring-boot-kotlin-coroutines).
- Korean (high value, real production):
  - Kakao Pay: "WebFlux와 코루틴으로 BFF(Backend For Frontend) 구현하기" (tech.kakaopay.com/post/bff_webflux_coroutine/) — using coroutines to fan-out MSA calls in a BFF for the "내 주변 매장 찾기" service.
  - 우아한형제들: "배민광고리스팅 개발기(feat. 코프링과 DSL 그리고 코루틴)" (techblog.woowahan.com/7349/) — Reactor Mono→coroutine via awaitSingle, IO dispatcher for blocking code, latency reduction.
  - LG U+: "Spring WebFlux에서 Kotlin Coroutine으로 Reactive 프로그래밍 구현하기" (techblog.uplus.co.kr) — replacing Mono/Flux with Flow, with a WebMVC-vs-WebFlux load-test comparison on a high-traffic main-display API.
  - Kakao Pay: "코틀린 코루틴 예외 처리, 어떻게 해야 할까?" (tech.kakaopay.com/post/coroutine-exceptions-handling/) — structured concurrency, exception propagation/cancellation.

**Decision heuristic to internalize:** prefer coroutines for imperative-style business logic and readability (your Kotlin stack); drop to raw Reactor for complex stream orchestration (windowing, advanced backpressure, operator fusion) and when interop demands it. Korean teams converge on this exact split.

**Deliverable:** Re-implement the Phase 2 CLI aggregator in idiomatic Kotlin coroutines + Flow, with explicit dispatcher choices, structured-concurrency error handling, and a parallel comparison of the same logic in raw Reactor — write up which you'd choose and why.

### Phase 4 — Production WebFlux Service: Web Layer & Data (Weeks 10–12)
**Objectives:** Build the spine of a production service on your stack.

**Topics:**
- WebFlux architecture: annotated controllers vs functional routing (RouterFunction/HandlerFunction); WebFilter; ServerWebExchange; when to choose each.
- R2DBC against Aurora MySQL/PostgreSQL: spring-boot-starter-data-r2dbc, r2dbc-pool tuning (initial-size, max-size, max-acquire-time), ReactiveCrudRepository/CoroutineCrudRepository, DatabaseClient/R2dbcEntityTemplate.
- **Reactive transactions:** R2dbcTransactionManager (ReactiveTransactionManager), @Transactional on Publisher-returning/suspend methods, TransactionalOperator; connection pinning during a transaction; nested transactions via R2DBC savepoints (Spring 6.0.10+); schema management (Flyway/Liquibase, since R2DBC has no auto-DDL).
- **R2DBC vs JPA trade-offs:** no relation mapping, manual joins/SQL, the blocking-JPA incompatibility; honest break-even analysis (at low concurrency, MVC+JDBC can win).
- Reactive Redis with Lettuce (already non-blocking) via Spring Data Redis Reactive (ReactiveRedisTemplate) — caching, pub/sub.
- SSE/streaming endpoints (produces = text/event-stream, Flux<T>).

**Resources:**
- Spring docs: "Annotated Controllers" (docs.spring.io/spring-framework/reference/web/webflux/controller.html), "Functional Endpoints" (.../web/webflux-functional.html), "Data Access with R2DBC" (.../data-access/r2dbc.html).
- GitHub: r2dbc/r2dbc-pool (pool config reference); r2dbc.io spec.
- Nicolas Fränkel, "Reactive database access on the JVM" (blog.frankel.ch/reactive-database-access/) — R2DBC vs Hibernate Reactive vs jOOQ trade-offs; the "decide by what non-reactive flavor you already use" rule; Vlad Mihalcea's MULTISET note for nested collections.
- Benchmark: technology.amis.nl "Spring: Blocking vs non-blocking: R2DBC vs JDBC and WebFlux vs Web MVC" — concrete throughput/latency/memory data showing R2DBC+WebFlux wins at high concurrency, MVC+JDBC at low (with a break-even around a few hundred concurrent requests).
- Vinsguru "Spring Data R2DBC CRUD Example" (vinsguru.com/spring-data-r2dbc/); Baeldung "Guide to Spring WebFlux."
- Korean production:
  - 레진코믹스: "Kotlin과 Spring WebFlux 기반의 컨텐츠 인증 서비스 개발 후기" (tech.lezhin.com/2020/07/15/kotlin-webflux) — full reactive stack with R2DBC GA, WebClient.
  - 우아한형제들: "프로모션 시스템 엿보기: 파일럿 프로젝트" (techblog.woowahan.com/10795/) — WebFlux + R2DBC + WebClient, how @Transactional differs with R2DBC, R2DBC limitations.
  - Kakao Pay: "콘텐츠를 조립하는 결제탭 피드 서버의 코드 아키텍처" (tech.kakaopay.com/post/payment-feed-server/) — Kotlin + WebFlux + R2DBC + coroutine async fan-out with read-timeout handling.

**Deliverable:** A reactive CRUD service (annotated controllers + one functional-routing module) backed by R2DBC against a local Postgres/MySQL (docker-compose), with r2dbc-pool tuned, reactive transactions on a multi-write use case, a reactive Redis cache, and an SSE streaming endpoint. Run the AMIS-style load test to find *your* break-even concurrency.

### Phase 5 — Production Integrations: Kafka, WebClient, Security (Weeks 13–14)
**Objectives:** Wire the service into your event and service mesh, securely.

**Topics:**
- Reactive Kafka: Reactor Kafka (KafkaSender/KafkaReceiver) and Spring's ReactiveKafkaProducerTemplate/ReactiveKafkaConsumerTemplate; end-to-end backpressure; receiveExactlyOnce + transactions; reactiveAutoCommit; the Flux<Flux<ConsumerRecord>> shape; when a "partially reactive" binder gives no real end-to-end benefit.
- WebClient (the reactive RestTemplate replacement): connection pooling (ConnectionProvider maxConnections), the three timeouts (connect, response, read/write) and why responseTimeout must exceed connect + pool-acquire time, retry with retryWhen + exponentialBackoff, resilience with Resilience4j (circuit breaker, retry, bulkhead, time limiter) via the reactive operators (resilience4j-reactor).
- Reactive Spring Security: @EnableWebFluxSecurity, SecurityWebFilterChain/ServerHttpSecurity, ReactiveAuthenticationManager, ReactiveUserDetailsService, @EnableReactiveMethodSecurity, and **ReactiveSecurityContextHolder** (Reactor Context) — why ThreadLocal SecurityContextHolder cannot work; JWT WebFilter writing auth into Context via `contextWrite(ReactiveSecurityContextHolder.withAuthentication(...))`; the pitfall of forked streams losing the SecurityContext.

**Resources:**
- Reactor Kafka reference (docs.spring.io/projectreactor/reactor-kafka); reactor/reactor-kafka GitHub samples; ReactiveKafkaConsumerTemplate/ProducerTemplate Javadoc; Spring Cloud Stream reactive Kafka binder docs (partially-vs-fully reactive discussion).
- WebClient: Spring WebClient reference; dev.to "Webclient timeout and connection pool strategy" (yangbongsoo) — real PrematureCloseException/keepAlive case; dhaval-shah.com "Performant and optimal Spring WebClient"; Resilience4j docs (reactive support via resilience4j-reactor).
- Reactive Security: Spring Security reference (reactive); Baeldung "Spring Security for Reactive Applications" (baeldung.com/spring-security-5-reactive); hantsy/spring-reactive-jwt-sample (GitHub) for JWT; Medium "Webflux and the ReactiveSecurityContextHolder" (Thomas So) for the forked-stream pitfall.
- Josh Long, "Reactive Spring" (Ch. 10: Service Orchestration — client-side load balancing in WebClient, Resilience4j, hedging, scatter/gather, Spring Cloud Gateway).

**Deliverable:** Extend the Phase 4 service with: a Reactor Kafka consumer→transform→producer pipeline with backpressure; a WebClient calling an external API with tuned pool/timeouts + Resilience4j circuit breaker & retry; and JWT-based reactive security with method-level authorization, verified by tests using ReactiveSecurityContextHolder.

### Phase 6 — Observability, Pitfalls & Production Hardening (Week 15)
**Objectives:** Make it debuggable and safe in production — the learner's non-negotiable section.

**Topics:**
- **Why ThreadLocal mechanisms break:** MDC logging, SecurityContext, transaction context all lose data across operator/thread hops.
- **Micrometer Context Propagation** (github.com/micrometer-metrics/context-propagation): ContextRegistry, ThreadLocalAccessor, ContextSnapshot; bridging Reactor Context ↔ ThreadLocal; `Hooks.enableAutomaticContextPropagation()` (available since reactor-core 3.5.3; per the Reactor reference it "can be called upon application start to enable the automatic mode … this mode applies only to new subscriptions, so it is recommended to enable this hook when the application starts") and the Spring Boot 3.2 property `spring.reactor.context-propagation=auto` (Spring Boot issue #34201).
- **MDC in reactive/coroutine code:** writing trace/correlation IDs into Reactor Context and bridging to SLF4J MDC; the coroutine MDCContext element.
- **Tracing across reactive & coroutine boundaries:** Micrometer Tracing (formerly Spring Cloud Sleuth) + micrometer-tracing-bridge-otel/brave; reactor-core-micrometer; W3C traceparent propagation; **known sharp edges** — Spring Boot issue #38593 ("OpenTelemetry TraceContext does not propagate through reactive context properly in 3.1.6 / 3.2.0") and companion #38624 (tracing missing in a log statement before returning the Mono chain), plus an OTel memory-leak issue (#8749) with R2DBC pool + context propagation. Datadog/OTel: the Java agent auto-instruments WebFlux/Netty/WebClient, but verify context actually flows.
- **@Timed + suspend incompatibility** and metric/AOP gaps with suspend functions — use the Observation API / manual timing where annotations fail.
- **BlockHound** (github.com/reactor/BlockHound): a Java agent that throws when a blocking call runs on a non-blocking (Netty/parallel) thread; built-in Reactor integration since reactor-core 3.3; run it in tests (and "soft mode" callback that prints instead of throwing) to catch accidental event-loop blocking.
- **The danger of blocking the event loop:** never call .block(), blocking JDBC, or Thread.sleep on event-loop threads; offload unavoidable blocking to boundedElastic.

**Resources:**
- Spring blog 3-part series "Context Propagation with Project Reactor" (spring.io/blog/2023/03/30/... part 3, and /03/29 parts 1–2) — the definitive explanation.
- Micrometer Context Propagation docs (docs.micrometer.io/context-propagation) + GitHub.
- dev.to "About Micrometer Context Propagation" (be-hase) — MDC/Trace ThreadLocalAccessor examples; chemicL's gist on automatic MDC propagation with Project Reactor.
- Medium "Trace ID propagation in Spring WebFlux using MDC, ContextRegistry, and Micrometer Tracing."
- BlockHound README + docs (how_it_works, customization, tips).
- Better Programming "Tracing in Spring Boot 3 WebFlux" (Jonas TM; Kotlin + coroutines example; known issues + fixes).
- Datadog blog "Trace your applications end to end with Datadog and OpenTelemetry."
- Kakao Pay: "피처 플래그 개발기: 실시간 데이터 동기화를 향한 여정" (tech.kakaopay.com/post/feature-flag/) — Netty + WebFlux + coroutines non-blocking serving with Redis pub/sub.

**Deliverable:** Add to the service: Actuator + Micrometer → Prometheus metrics; Micrometer Tracing → OTLP with traceId/spanId flowing into logs via MDC across coroutine boundaries (verify in Grafana/Datadog); BlockHound enabled in the test profile with a deliberately-introduced blocking call to prove detection; and a custom WebFilter that seeds a correlation ID into Reactor Context and MDC.

### Phase 7 — Trade-offs, Virtual Threads & "When NOT to" (Week 16)
**Objectives:** Develop senior judgment about reactive adoption.

**Topics:**
- The complexity cost: harder debugging, steeper learning curve, smaller talent pool, library compatibility.
- **Loom / virtual threads (Java 21) vs WebFlux:** Spring MVC + virtual threads (`spring.threads.virtual.enabled=true`, Spring Boot 3.2+) gives thread-per-request scalability with blocking-style code; benchmarks show comparable throughput for typical microservices, with WebFlux retaining the edge at extreme concurrency and for streaming/backpressure. Virtual-thread pitfalls: pinning on `synchronized` (use ReentrantLock), ThreadLocal heap pollution (use Scoped Values, JEP 429), and the DB connection pool becoming the new bottleneck.
- **The JPA-is-blocking problem:** for teams with large JPA/Hibernate codebases, WebFlux means rewriting the entire data layer to R2DBC (losing ORM features) — often not worth it; virtual threads let you keep JPA/JDBC and still scale.
- A decision matrix: choose WebFlux for high-fan-out aggregation/BFF, SSE/streaming, very high-concurrency I/O gateways, fully-reactive stacks; choose MVC + virtual threads for CRUD, JPA-heavy services, and teams prioritizing maintainability.

**Resources:**
- Korean migration/decision stories (primary):
  - 우아한형제들 "[배민스토어] 우리만의 자유로운 WebFlux Practices" (techblog.woowahan.com/12903/) — why they adopted WebFlux (external API fan-out, non-blocking Redis/DynamoDB), and the "you could also just split APIs" honesty.
  - Hancom "WebFlux & Project Reactor 기반 … 웹한글 문서 편집 시스템 전환기" (tech.hancom.com/webflux-project-reactor-webhwp/) — why WebFlux over MVC and an explicit "when NOT to migrate (JPA/JDBC blocking)" section.
  - SSG TECH "Kotlin Coroutine으로 구현한 비동기 제휴 연동 시스템 구축기" (medium.com/ssgtech) — coroutine async over batch, GC/CPU effects.
  - Kakao Pay "코루틴과 Virtual Thread 비교와 사용" (tech.kakaopay.com/post/coroutine_virtual_thread_wayne/) — coroutines vs virtual threads with the author's own perf tests.
- Global: chrisgleissner/loom-webflux-benchmarks and hpoettker/project-loom-comparison (GitHub) for reproducible Loom-vs-WebFlux numbers; vincenzoracca.com "Virtual Threads vs WebFlux: who wins?" for a concrete head-to-head; the "WebFlux vs Virtual Threads Decision Matrix" articles for the pinning/Scoped Values/pool-exhaustion pitfalls.
- Conference: SpringOne / Devoxx talks on virtual threads vs reactive; Josh Long's reactive talks.

**Deliverable (capstone):** Take one Phase-4 endpoint and implement it three ways — WebFlux+R2DBC, MVC+JDBC (platform threads), MVC+JDBC+virtual threads — load-test all three, and write a decision memo with your recommendation for your team's actual services, including the JPA-migration cost.

## Recommendations

1. **Do not skip Phases 1–2 to "get to WebFlux faster."** The learner's instinct to build primitives from scratch and master imperative Reactor before coroutines is correct and is corroborated by Korean practitioners who warn that coroutines hide Reactor you'll still need to debug. Spend the most time (4 weeks) in Phase 2.
2. **Stand up the observability story early (don't defer to Phase 6 in practice).** Add Micrometer Context Propagation, MDC bridging, and BlockHound to your project skeleton as soon as you start Phase 4 — context-propagation bugs are far cheaper to catch before business logic piles up. Enable `Hooks.enableAutomaticContextPropagation()` (or `spring.reactor.context-propagation=auto`) and verify traceId-in-logs on day one of the service build.
3. **Make the JPA decision explicitly, per service.** Before migrating anything real, run the Phase-7 three-way benchmark on a representative endpoint. **Threshold to change course:** if your target service is JPA-heavy and runs below roughly a few hundred concurrent in-flight requests (the break-even region reported in the AMIS benchmark), prefer Spring MVC + virtual threads and keep JPA. Adopt WebFlux only where you have (a) high fan-out aggregation, (b) streaming/SSE, or (c) sustained very high concurrency on I/O-bound paths.
4. **Use Korean blogs for "how it really feels" and global docs/books for correctness.** Pair each phase's official reference (Reactor/Spring docs) with the mapped Korean production write-up — the combination of authoritative spec + real incident/trade-off narrative is exactly the learner's stated preference.
5. **Treat resilience and security as reactive-native from the start.** Wire Resilience4j (reactive operators) and ReactiveSecurityContextHolder-based security in Phase 5 rather than retrofitting; the ThreadLocal assumptions in blocking code do not survive translation.

## Caveats
- **Some sources are dated.** "Reactive Programming with RxJava" (Nurkiewicz) and "Hands-On Reactive Programming in Spring 5" predate Spring Boot 3.x/Reactor 3.6+ and Java 21 virtual threads — use them for concepts, not current APIs. Josh Long's "Reactive Spring" is excellent but, per reader reviews, light on standalone Reactor depth (it spends ~2 chapters on Reactor before jumping to Spring integration) — pair it with a Reactor-focused course/book. Several reactive Spring Security snippets online still use the deprecated `subscriberContext()`/`.and()`-style chaining; prefer current `contextWrite()` and the lambda DSL.
- **Tracing across reactive/coroutine boundaries is genuinely unstable across versions.** The cited Spring Boot issues (#38593/#38624 traceId loss; OTel issue #8749 memory leak with R2DBC pool + context propagation) show this is an evolving area — pin and test your exact Spring Boot/Micrometer/OTel versions and verify trace continuity in staging rather than trusting it works.
- **Virtual-thread-vs-WebFlux benchmarks are workload-dependent and contested.** The numbers from third-party blogs/repos vary with delay model, client, and JDK; treat them as directional and run your own tests on your EKS hardware.
- **Korean source availability is uneven.** Strong, verified production content exists from Kakao Pay, 우아한형제들/배민, LG U+, 레진, SSG, and Hancom. I could not verify dedicated backend WebFlux/coroutine articles from Coupang or Kurly, nor a specific Naver DEVIEW/NHN FORWARD reactive session URL. Toss confirmably uses Kotlin coroutines + WebFlux in production (and built a custom Pinpoint APM plugin because Pinpoint didn't support coroutines), but I could not confirm a single dedicated toss.tech WebFlux/R2DBC article — browse the SLASH session archives (toss.im/slash-21 … slash-24) directly.
- **R2DBC maturity varies by driver.** Confirm the current state of the MySQL/PostgreSQL R2DBC drivers and r2dbc-pool against your Aurora requirements before committing; some advanced features (savepoints, certain type mappings, relation handling) lag JPA. Note also that 2026-dated "WebFlux vs Virtual Threads" articles cited here are forward-looking opinion pieces — weigh their predictions accordingly and rely on the reproducible benchmark repos for hard numbers.