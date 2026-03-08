---
title: "Mastering Spring WebFlux"
category: "Spring / Reactive"
description: "14-week learning plan for Kotlin engineers covering Project Reactor, Spring WebFlux, R2DBC, reactive Redis/Kafka, and production observability"
---

# Mastering Spring WebFlux: a 14-week learning plan for Kotlin engineers

**Spring WebFlux demands a genuine mental model shift—not just new APIs—and this plan builds that foundation systematically.** For a mid-level engineer fluent in Spring MVC and Kotlin, the fastest path to production-ready WebFlux runs through four phases: grasping reactive streams theory, building fluency with Project Reactor operators, integrating your real infrastructure (Aurora via R2DBC, Redis, Kafka), and finally mastering the observability, debugging, and performance-tuning skills that separate toy projects from production systems. The resources below are curated for quality and recency, favoring materials that explain the *why* behind reactive programming over syntax-only tutorials. Each phase ends with a concrete milestone project that mirrors your actual AWS/EKS stack.

---

## Phase 1: Reactive foundations (weeks 1–3)

The single biggest mistake engineers make when adopting WebFlux is jumping straight into Spring annotations without understanding the reactive programming model underneath. These three weeks are exclusively about **Project Reactor, Reactive Streams, and the Kotlin coroutines bridge**—no Spring WebFlux yet.

### Week 1: Reactive Streams specification and mental model shift

Start by understanding *why* reactive programming exists. Read the **Project Reactor Reference Guide's "Introduction to Reactive Programming"** section at projectreactor.io—it is genuinely one of the best explanations available anywhere, covering callback hell, Future limitations, and the composability advantage. Follow this with Dave Syer's three-part **"Notes on Reactive Programming"** series on spring.io (2016), which maps the reactive landscape and builds a simple HTTP server. Despite its age, it remains the gold-standard conceptual introduction written by a Spring team member.

Watch Venkat Subramaniam's **"Reactive Programming"** talk from Devoxx (~2.5 hours). Venkat's signature teaching style makes function composition, resilience, and backpressure viscerally intuitive. Then watch Simon Baslé's **"Flight of the Flux: A Look at Reactor Execution Model"** from Spring I/O 2018 to understand assembly time versus subscription time—a distinction that prevents 80% of beginner bugs.

Begin reading **"Unraveling Project Reactor"** by Esteban Herrera, freely available at eherrera.net/project-reactor-course. This is the best dedicated Reactor resource for building operator fluency before touching Spring.

### Week 2: Mono, Flux, operators, and error handling

Work through the core chapters of "Unraveling Project Reactor," completing all exercises. Simultaneously take Dilip Sundarraj's **"Reactive Programming in Modern Java using Project Reactor"** on Udemy (~4.5/5 rating), which covers Flux/Mono operators, cold versus hot streams, Schedulers, `publishOn`/`subscribeOn`, Sinks, and debugging with hooks/checkpoints. This course is the community's most-recommended Reactor-specific training.

The **Reactor Core Reference Guide** at projectreactor.io becomes your daily companion from this point forward. Bookmark the **"Which operator do I need?"** appendix—it is invaluable when you know what transformation you want but not which operator provides it.

### Week 3: Kotlin coroutines, Flow, and the Reactor bridge

Since you use Kotlin, understanding coroutines is non-negotiable. Spring WebFlux natively supports `suspend` functions and `Flow` return types, giving you imperative-looking code that runs on the reactive runtime. Read Sébastien Deleuze's **"Going Reactive with Spring, Coroutines and Kotlin Flow"** on spring.io (April 2019)—the definitive post on this integration.

Begin **"Kotlin Coroutines: Deep Dive"** by Marcin Moskała (Kt. Academy, updated 2023). Community reception is exceptional: reviewers call it "one of the best programming books I've read" and "explains things way better than the official docs." Focus on Parts 1–3 (suspension mechanics, structured concurrency, Flow). For reinforcement, the coroutines chapters (14–18) in **"Kotlin in Action, 2nd Edition"** (May 2024, written by Kotlin's lead language designer Roman Elizarov) provide authoritative coverage of structured concurrency and Flow operators.

### Phase 1 milestone project

Build a CLI data-processing pipeline using pure Project Reactor (no Spring). Ingest a CSV file as a `Flux<String>`, parse rows, apply transformations with `map`/`flatMap`, handle malformed rows with `onErrorResume`, implement backpressure with `limitRate()`, and write results to stdout. Then rewrite it using Kotlin `Flow` and coroutines. Compare the two approaches in a short write-up. This cements operator fluency without Spring's abstractions obscuring the learning.

---

## Phase 2: Spring WebFlux core (weeks 4–7)

With Reactor fluency established, you can now layer Spring WebFlux on top without confusing framework behavior with reactive primitives.

### Week 4–5: WebFlux fundamentals and WebClient

Take Dilip Sundarraj's **"Build Reactive MicroServices using Spring WebFlux/SpringBoot"** on Udemy (consistently rated the #1 WebFlux course). It covers annotated controllers, functional endpoints (`RouterFunction`/`HandlerFunction`), exception handling, WebClient, Server-Sent Events, and Netty internals. For a more up-to-date option, Vinoth Selvaraj's **"Spring WebFlux Masterclass"** has been updated to **Spring Boot 4.0** and emphasizes production concerns like HTTP/2, connection pooling, and compression.

Read the **official Spring WebFlux reference** at docs.spring.io/spring-framework/reference/web/webflux.html. Section 1.1.4 specifically addresses when to use (and not use) WebFlux—required reading. Complement with Baeldung's **"Guide to Spring WebFlux"** and **"Introduction to the Functional Web Framework"** for annotated versus functional endpoint patterns.

For WebClient specifically, Baeldung's **"Spring WebClient"** guide and **"Guide to Retry in Spring WebFlux"** (covering `retryWhen` with backoff strategies) are essential. The spring.io post **"The State of HTTP Clients in Spring"** (September 2025) clarifies WebClient's evolving role alongside RestClient in Spring Boot 4.x.

### Week 5–6: R2DBC with Aurora (PostgreSQL/MySQL)

This is where your AWS stack enters the picture. **Spring Data R2DBC** supports both MySQL and PostgreSQL drivers, making it compatible with Aurora. Read the **Spring Data R2DBC Reference Documentation** (docs.spring.io/spring-data/r2dbc), focusing on `ReactiveCrudRepository`, `R2dbcEntityTemplate`, query derivation, and Kotlin coroutines support.

Baeldung's **"R2DBC – Reactive Relational Database Connectivity"** covers low-level operations, while **"Spring R2DBC Migrations Using Flyway"** addresses the common pain point of schema management in reactive apps. The GitHub repository **martishin/spring-webflux-kotlin-coroutines-example** demonstrates a modern Kotlin stack with PostgreSQL R2DBC, Flyway, Jooq, and Micrometer—close to your production architecture.

Key caveat: R2DBC does not support all features that JDBC does. **Pagination behaves differently** (no `Page` support in reactive repositories), and complex joins require `R2dbcEntityTemplate` or integration with jOOQ. Baeldung's **"Pagination in Spring WebFlux and Spring Data Reactive"** covers workarounds.

### Week 6–7: Testing reactive code

Testing is where reactive complexity bites hardest if you're unprepared. Master **StepVerifier** from reactor-test: Baeldung's **"Testing Reactive Streams Using StepVerifier and TestPublisher"** is the essential guide, covering assertion patterns, virtual time testing, and `TestPublisher` for simulating misbehaving publishers. Spring's **WebTestClient** replaces MockMvc for reactive endpoints.

Watch Sergei Egorov's **"Do's and Don'ts: Avoiding First-Time Reactive Programmer Mines"** from SpringOne 2019—it identifies the exact mistakes you'll make and how to prevent them. Then read Simon Baslé's "Flight of the Flux" blog series on spring.io (Part 2: Debugging Caveats) for understanding why stack traces look bizarre in reactive code and how checkpoints, `Hooks.onOperatorDebug()`, and ReactorDebugAgent help.

### Phase 2 milestone project

Build a reactive REST API for a simple domain (e.g., product catalog) using **Spring WebFlux + Kotlin coroutines + R2DBC with PostgreSQL** (use a local Docker PostgreSQL as Aurora stand-in). Implement both annotated controllers and one functional endpoint. Use WebClient to call an external API. Include comprehensive tests with StepVerifier and WebTestClient. Deploy in a Docker container. This mirrors your real production patterns without yet adding Kafka or Redis complexity.

---

## Phase 3: Infrastructure integration (weeks 8–11)

Now expand to your full AWS stack: reactive Redis, reactive Kafka, security, and the operational concerns that distinguish development from production.

### Week 8: Reactive Redis with Lettuce

Spring Data Redis Reactive uses Lettuce under the hood (already non-blocking). Read the **Spring Data Redis Reactive documentation** at docs.spring.io/spring-data/redis/reference/redis/reactive.html, covering `ReactiveRedisTemplate` and reactive operations. The GitHub repository **RawSanj/spring-redis-websocket** demonstrates a production-quality Spring Boot 3.x application with reactive Redis Pub/Sub, WebSocket, Kubernetes deployment, and Testcontainers.

Vinoth Selvaraj's **"Reactive Redis Masterclass"** on Udemy specifically covers WebFlux + Redis patterns: caching, pub/sub, geospatial operations, and WebSocket chat. Baeldung's **"Spring Webflux and @Cacheable Annotation"** addresses the tricky interaction between Spring's caching abstraction and reactive types (you cache `Mono`/`Flux` wrappers, not resolved values).

### Week 9: Reactive Kafka with reactor-kafka

The **Reactor Kafka Reference Guide** at projectreactor.io/docs/kafka covers `KafkaReceiver`, `KafkaSender`, transactional sends, and non-blocking backpressure. The official **reactor/reactor-kafka** GitHub repository (613+ stars) includes `SampleProducer.java` and `SampleConsumer.java`. For Kotlin integration, the repository **meong1234/reactive-kafka** demonstrates Spring Boot + Kotlin + WebFlux functional endpoints + Reactor Kafka.

Key architectural decision: reactor-kafka provides fine-grained backpressure control over Kafka consumers, but for many use cases **Spring Cloud Stream with reactive binder** offers a higher-level abstraction. Evaluate both approaches against your team's needs.

### Week 10: Spring Security Reactive

Reactive security differs significantly from servlet security. The **spring-projects/spring-security-samples** GitHub repository includes dedicated WebFlux and Kotlin WebFlux security examples. Sergey Kargopolov's Udemy course **"Reactive Applications with Spring WebFlux Framework"** is one of the few courses that covers JWT authentication and method-level security in reactive contexts.

### Week 11: Observability—tracing, metrics, and logging

This is the hardest operational problem in reactive systems. **ThreadLocal doesn't work** with Reactor's thread-hopping execution model, breaking MDC logging, distributed tracing, and metrics context. The Spring blog post **"Context Propagation with Project Reactor 3"** (March 2023) is critical reading—it explains how Micrometer's context-propagation library bridges ThreadLocal with Reactor Context, enabling SLF4J MDC population and trace propagation.

Read the **Micrometer Context Propagation documentation** at micrometer.io/docs/contextPropagation. The DEV Community article **"Kotlin Spring WebFlux, R2DBC and Redisson microservice in k8s"** demonstrates a full implementation with Zipkin tracing, Prometheus/Grafana monitoring, and Kubernetes deployment—closely matching your EKS target environment.

### Phase 3 milestone project

Extend your Phase 2 product catalog into a **reactive microservice** with all infrastructure integrated: R2DBC for Aurora PostgreSQL, reactive Redis for caching (with TTL-based invalidation), reactor-kafka for publishing domain events and consuming commands, Spring Security with JWT, and Micrometer metrics with distributed tracing propagated through reactive context. Deploy on Docker Compose with all dependencies. Write integration tests using Testcontainers for PostgreSQL, Redis, and Kafka.

---

## Phase 4: Production mastery (weeks 12–14)

The final phase focuses on the skills that separate working code from production-grade systems: performance tuning, migration strategy, and knowing when *not* to use WebFlux.

### When NOT to use WebFlux

This is arguably the most important topic in this entire plan. Read these resources carefully:

- **Netflix's migration away from reactive**: The ByteByteGo analysis **"Evolution of Java Usage at Netflix"** reveals that Netflix—the company that pioneered reactive Java with RxJava—moved to virtual threads for most services. They found that mixing thread-per-request with reactive HTTP clients created "complex failure modes and resource contention." Reactive is now reserved for streaming workloads and long I/O chains.
- **Allegro's migration case study** at blog.allegro.tech (July 2019) is the best honest production migration write-up. It documents decreased thread usage and fewer GCs, but also testing pitfalls (stubs returning null cause Mono to hang silently) and the "reactive tax" of complexity.
- The Medium post **"The Day Our Reactive WebFlux Migration Almost Took Production Down"** (February 2026) is a cautionary tale: a team made their application "look reactive without making it actually reactive" by accidentally blocking event-loop threads, causing latency to spike from 120ms to 900–1500ms.
- The Korean developer blog post **"나는 왜 Reactive Streams와 친해지지 않는가?"** provides a thoughtful counterpoint arguing that most services don't face the C10K problem and should wait for virtual threads.

**The honest assessment**: WebFlux shines when your service has **high concurrency with I/O-bound operations** (many simultaneous external API calls, database queries, message broker interactions). It does not help—and actively hurts—with **CPU-bound work, blocking libraries without reactive drivers, or teams unfamiliar with the paradigm**. For your stack specifically, Aurora R2DBC support, Lettuce (already non-blocking), and reactor-kafka make the reactive path viable, but only if the concurrency characteristics of your services justify the complexity.

### Performance tuning and thread model

Understanding the **Netty event-loop model** is essential. Baeldung's **"Concurrency in Spring WebFlux"** explains EventLoopGroup, thread management, and why blocking an event-loop thread is catastrophic. Read Simon Baslé's "Flight of the Flux" Part 3 on thread hopping and Schedulers. Watch Oleh Dokuka's **"Reactive Performance"** from SpringOne 2019 for benchmarks and tuning guidance.

Key production tools: **BlockHound** detects blocking calls in reactive threads at test time. The benchmark article **"Microservice Performance Battle: Spring MVC vs WebFlux"** demonstrates that WebFlux with WebClient is **4× faster than blocking Servlet** when downstream services are slow (500ms latency), while using **20 threads versus 220**.

### Migration strategies from Servlet to WebFlux

**"Pro Spring MVC with WebFlux"** by Marten Deinum and Iuliana Cosmina (Apress, 2021) covers both frameworks side-by-side and shows migration paths. The book received praise specifically for "showing how to get the benefits of reactive, and watch out for the remaining blocking calls." A practical migration strategy for your team:

1. Start with WebClient in your existing MVC services (it works in both stacks)
2. Build new greenfield services in WebFlux
3. Migrate high-concurrency services first, measuring before/after
4. Keep CPU-bound and simple CRUD services on MVC

The Woowahan (배달의민족) tech blog case study documents how Korea's largest food delivery platform rewrote their highest-traffic **"Store Display" system** in WebFlux/Reactor, deploying in April 2019 with 1,300+ tests. Notably, their Spring Batch components still use blocking `.block()` calls—a pragmatic choice.

### Phase 4 milestone project

Take your Phase 3 microservice and make it production-ready: add **BlockHound** to your test suite to catch blocking calls, implement **circuit breakers** with Resilience4j for WebClient calls, add structured logging with MDC context propagation, configure Micrometer metrics (histogram buckets for latency, counter for Kafka consumer lag), write a **Gatling or k6 load test** comparing throughput under high concurrency, and create a Kubernetes deployment manifest targeting EKS. Document your performance findings and the specific scenarios where your service benefits from reactive versus where it doesn't.

---

## Complete resource reference

### Books (in recommended reading order)

| Book | Author(s) | Year | Why it matters |
|---|---|---|---|
| *Unraveling Project Reactor* | Esteban Herrera | 2023 | **Free online.** Best Reactor-only foundation. Start here. |
| *Kotlin Coroutines: Deep Dive* | Marcin Moskała | 2022 (updated 2023) | The definitive coroutines reference. Essential for Kotlin + WebFlux. |
| *Hands-On Reactive Programming in Spring 5* | Oleh Dokuka, Igor Lozynskyi | 2018 | By a Reactor committer. Most comprehensive Spring reactive book. |
| *Kotlin in Action, 2nd Ed.* | Aigner, Elizarov, Isakova, Jemerov | May 2024 | Five new coroutines chapters by Kotlin's lead designer. |
| *Spring in Action, 6th Ed.* | Craig Walls | 2022 | Gold-standard Spring reference. Strong WebFlux chapters. |
| *Reactive Spring* | Josh Long | 2020 | End-to-end reactive Spring ecosystem from the Spring Developer Advocate. |
| *Pro Spring MVC with WebFlux* | Deinum, Cosmina | 2021 | Best for MVC→WebFlux migration. Covers both side-by-side. |
| *Release It!, 2nd Ed.* | Michael Nygard | 2018 | Production patterns (circuit breakers, bulkheads) every reactive engineer needs. |

### Top online courses

| Course | Instructor | Platform | Rating | Notes |
|---|---|---|---|---|
| Reactive Programming in Modern Java using Project Reactor | Dilip Sundarraj | Udemy | ~4.5/5 | **Take first.** Deep Reactor fundamentals. |
| Build Reactive MicroServices using Spring WebFlux | Dilip Sundarraj | Udemy | ~4.5/5 | **Take second.** #1 community-recommended WebFlux course. |
| Spring WebFlux Masterclass | Vinoth Selvaraj | Udemy | High | Updated to Spring Boot 4.0. Production performance focus. |
| Mastering Java Reactive Programming | Vinoth Selvaraj | Udemy | High | Builds custom publishers. Deepest Reactor internals course. |
| Reactive Redis Masterclass | Vinoth Selvaraj | Udemy | High | WebFlux + Redis patterns. Directly relevant to your stack. |
| Spring WebFlux: Getting Started | Esteban Herrera | Pluralsight | Good | Concise 2–3 hour introduction. |
| Reactive Spring Boot with Kotlin Coroutines | Xebia Academy | Instructor-led | Premium | **Only dedicated Kotlin + WebFlux training** found. |
| Spring Academy | Spring Team | spring.academy | Free | Official. Best for certification prep. |

### Essential blog posts and articles

- **Reactor execution model**: Simon Baslé's "Flight of the Flux" blog series on spring.io (3 parts, 2019)
- **Kotlin integration**: Sébastien Deleuze's "Going Reactive with Spring, Coroutines and Kotlin Flow" (spring.io, 2019)
- **Context propagation**: "Context Propagation with Project Reactor 3" (spring.io, March 2023)
- **Production migration**: Allegro's "Migrating a microservice to Spring WebFlux" (blog.allegro.tech, 2019)
- **Korean case study**: Woowahan's "가게노출 시스템을 소개합니다" (techblog.woowahan.com, 2020)
- **When NOT to go reactive**: Netflix's evolution from RxJava to virtual threads (blog.bytebytego.com)
- **Performance benchmarks**: "Microservice Performance Battle: Spring MVC vs WebFlux" (filia-aleks, Medium)
- **Anti-patterns**: "Lessons Learned: My Spring WebFlux Experience and Key Anti-Patterns to Avoid" (Kiarash Shamaii, Medium)
- **HTTP clients in Spring**: "The State of HTTP Clients in Spring" (spring.io, September 2025)

### Must-watch conference talks

- **Venkat Subramaniam** — "Reactive Programming" (Devoxx, ~2.5 hrs). Legendary foundational talk.
- **Simon Baslé** — "Flight of the Flux" (Spring I/O 2018, ~55 min). Assembly vs subscription time.
- **Sergei Egorov** — "Do's and Don'ts: Avoiding First-Time Reactive Programmer Mines" (SpringOne 2019). The mistakes you'll make.
- **Oleh Dokuka** — "Reactive Hardcore" (Devoxx 2019). Build a Publisher from scratch.
- **Oleh Dokuka** — "Reactive Performance" (SpringOne 2019). Benchmarks and tuning.
- **Phil Clay** — "Avoiding Reactor Meltdown" (SpringOne 2019). Production pitfalls.
- **Josh Long** — "Reactive Spring" (multiple events, 2018–2024). Full ecosystem live coding.
- **Rossen Stoyanchev** — WebFlux creator's talks on InfoQ and QCon (2017). Servlet vs reactive architecture comparison.

### Key GitHub repositories

| Repository | What it demonstrates |
|---|---|
| **hantsy/spring-reactive-sample** | 50+ sub-projects covering every WebFlux pattern. Updated to Spring 6/Boot 3. |
| **martishin/spring-webflux-kotlin-coroutines-example** | Kotlin + PostgreSQL R2DBC + Flyway + Micrometer. Closest to your stack. |
| **reactor/reactor-kafka** | Official reactor-kafka with sample producer/consumer. |
| **RawSanj/spring-redis-websocket** | Production-quality reactive Redis + WebSocket + Kubernetes. Spring Boot 3.x. |
| **spring-projects/spring-security-samples** | Official security samples including WebFlux + Kotlin. |
| **Kevded/example-reactive-spring-kafka-consumer-and-producer** | Clean reactor-kafka integration with tests. |
| **PacktPublishing/Hands-On-Reactive-Programming-in-Spring-5** | Book companion: Redis, Cassandra, MongoDB reactive, Prometheus/Grafana/Zipkin. |
| **MasterCloudApps-Projects/AsyncReactiveProgramming** | Curated table of must-watch videos and MVC vs WebFlux comparison projects. |

### Official documentation bookmarks

- **Project Reactor Reference**: projectreactor.io/docs/core/release/reference
- **Spring WebFlux Reference**: docs.spring.io/spring-framework/reference/web/webflux.html
- **Spring Data R2DBC**: docs.spring.io/spring-data/r2dbc/docs/current-SNAPSHOT/reference/html
- **Reactor Kafka**: projectreactor.io/docs/kafka/snapshot/reference
- **Spring Data Redis Reactive**: docs.spring.io/spring-data/redis/reference/redis/reactive.html
- **Micrometer Context Propagation**: micrometer.io/docs/contextPropagation
- **R2DBC Specification**: r2dbc.io

---

## Curriculum topic checklist

This table maps every required topic to the phase where it's covered and the primary resource for learning it.

| Topic | Phase | Primary resource |
|---|---|---|
| Reactive Streams specification | 1 | Reactor Reference Guide, "Introduction to Reactive Programming" |
| Mono, Flux, operators, error handling | 1 | Esteban Herrera's "Unraveling Project Reactor" + Dilip's Reactor course |
| Backpressure | 1–4 | Baeldung's "Backpressure Mechanism in Spring WebFlux" |
| Kotlin coroutines and Flow bridge | 1 | Moskała's "Kotlin Coroutines: Deep Dive" + Deleuze's spring.io post |
| Annotated controllers vs functional endpoints | 2 | Dilip's WebFlux course + Baeldung guides |
| WebClient replacing RestTemplate | 2 | Baeldung's "Spring WebClient" + "Guide to Retry in Spring WebFlux" |
| R2DBC with Aurora (MySQL/PostgreSQL) | 2 | Spring Data R2DBC docs + martishin's GitHub example |
| Testing with StepVerifier and WebTestClient | 2 | Baeldung's StepVerifier guide + Sergei Egorov's "Do's and Don'ts" talk |
| Reactive Redis with Lettuce | 3 | Spring Data Redis Reactive docs + Vinoth's Redis Masterclass |
| Reactive Kafka (reactor-kafka) | 3 | Reactor Kafka Reference Guide + reactor/reactor-kafka samples |
| Spring Security Reactive | 3 | spring-security-samples repo + Kargopolov's Udemy course |
| Observability and context propagation | 3 | Spring blog on context propagation + Micrometer docs |
| Debugging reactive streams | 2–4 | Simon Baslé's "Flight of the Flux" blog Part 2 + BlockHound |
| Event loop, Schedulers, thread model | 4 | Baeldung's "Concurrency in Spring WebFlux" + Dokuka's performance talk |
| When NOT to use WebFlux | 4 | Netflix virtual threads story + Allegro case study + Korean dev blog |
| Migration strategies (Servlet → WebFlux) | 4 | "Pro Spring MVC with WebFlux" book + Woowahan case study |

## Conclusion

The reactive learning curve is real but manageable when structured correctly. **Spend weeks 1–3 exclusively on Reactor and coroutines before touching Spring WebFlux**—this is the single highest-leverage investment. The fact that Netflix has since moved away from reactive for most services doesn't invalidate WebFlux; it clarifies its sweet spot: high-concurrency, I/O-bound services with fully non-blocking dependency chains. Your stack (Aurora R2DBC, Lettuce Redis, reactor-kafka) aligns well with that sweet spot, but evaluate each service individually rather than adopting WebFlux as a blanket organizational standard. The Kotlin coroutines bridge is your secret weapon—it lets you write imperative-looking `suspend` functions while running on the reactive runtime, significantly reducing the "reactive tax" that pure Reactor chains impose on code readability and debugging.