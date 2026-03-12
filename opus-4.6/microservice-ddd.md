---
title: Mastery-level microservices learning plan for Spring Boot engineers
category: Backend & Infrastructure
description: 24-week curriculum transforming mid-level Kotlin/Spring Boot engineers into microservices architects, covering DDD, bounded contexts, decomposition strategy, and distributed patterns on AWS EKS/ECS.
---

# Mastery-level microservices learning plan for Spring Boot engineers

**This 24-week curriculum transforms a mid-level Kotlin/Spring Boot engineer into a microservices architect** who can decompose monoliths with surgical precision, design bounded contexts that survive production, and implement distributed patterns that handle failure gracefully. The plan is sequenced so each phase builds directly on the last, with escalating milestone projects that accumulate into a full migration simulation by week 24. Every pattern targets your production stack: Kotlin, Spring Boot, Aurora MySQL/PostgreSQL, Redis, and Kafka on AWS EKS/ECS.

The single most important insight this plan embeds: **the hardest problem in microservices is not the technology — it is finding the right service boundaries**. That is why DDD and decomposition strategy occupy the first nine weeks before a single service is split.

---

## Phase 1: Strategic DDD — learning to see boundaries (Weeks 1–3)

The goal here is rewiring how you think about software systems. Before writing code, you must learn to see a business domain as a collection of subdomains with natural boundaries, not as a bag of database tables. Strategic DDD gives you the vocabulary and tools to do this.

**Week 1** focuses on subdomains and bounded contexts. Read Vlad Khononov's *Learning Domain-Driven Design* (O'Reilly, 2021) chapters 1–8 — it is the most accessible modern DDD book and deliberately written for engineers, not academics. Khononov's framing of **core, supporting, and generic subdomains** as an investment-allocation tool is immediately practical: core subdomains get custom-built microservices, generic subdomains get off-the-shelf solutions, and supporting subdomains sit somewhere in between. Follow this with Martin Fowler's canonical article on Bounded Context (martinfowler.com/bliki/BoundedContext.html) and Eric Evans' DDD Europe 2019 keynote "Defining Bounded Contexts" where he distinguishes four types of bounded contexts in microservice environments — service-internal, cluster API, interchange, and published language.

**Week 2** covers context mapping patterns. These patterns describe how bounded contexts relate to each other organizationally and technically: Shared Kernel, Customer-Supplier, Conformist, Anti-Corruption Layer (ACL), Open Host Service, and Published Language. Study Nick Tune's "Bounded Context Canvas V3" article and download the canvas template from github.com/ddd-crew/bounded-context-canvas. Watch Michael Plöd's "DDD Strategic Design with Spring Boot" (Spring I/O 2017) — it is the only major conference talk that demonstrates context mapping with live Spring Boot code. Read Khononov chapters 9–12 on context mapping and communication patterns.

**Week 3** is dedicated to Event Storming. Read Alberto Brandolini's online materials at eventstorming.com/resources and watch his "50,000 Orange Stickies Later" talk from Explore DDD 2017. Practice all three levels: Big Picture (discovering the entire business flow), Process Level (detailing a single business process), and Design Level (deriving aggregates and commands from events). Use the free Miro strategic DDD templates from github.com/ddd-crew/virtual-modelling-templates. Study the ddd-crew/ddd-starter-modelling-process repository (~3.3K GitHub stars) — it provides an 8-step guide from understanding the business domain through Event Storming to coding the domain model.

**Korean resources for this phase:** Kakao's engineering blog post "추천팀의 DDD 도입기" (DDD Adoption Story from the Recommendation Team, tech.kakao.com/posts/555) describes how a real Korean engineering team applied strategic DDD to a new platform. Kurly's "DDD와 MSA 기반으로 좋은 서비스 개발하기" (helloworld.kurly.com/blog/ddd-msa-service-development/) explains the relationship between bounded contexts and microservices from a Korean e-commerce perspective. The Inflearn course "도메인주도 설계로 시작하는 마이크로서비스 개발" covers DDD strategic design and Event Storming workshops in Korean. Also explore MSAEZ (msaez.io), a Korean-developed online Event Storming collaboration tool widely used in Korean MSA education.

### Milestone project: Event Storm a fictional e-commerce domain

Model a mid-complexity e-commerce platform (catalog, ordering, payment, shipping, inventory, customer management, promotions) using Miro. Produce: (1) a Big Picture Event Storm with domain events, commands, aggregates, and hotspots; (2) a subdomain classification chart labeling each subdomain as core, supporting, or generic; (3) a context map showing at least 6 bounded contexts with relationship patterns labeled (ACL, Customer-Supplier, etc.); (4) a Bounded Context Canvas for the "Ordering" context. This artifact set becomes the blueprint for every subsequent phase.

---

## Phase 2: Tactical DDD — modeling the domain in Kotlin (Weeks 4–6)

With boundaries identified, you now learn to model the internals of a single bounded context using tactical DDD patterns. The shift from "where to cut" to "how to build" happens here.

**Week 4** covers aggregates, entities, and value objects. Read Eric Evans' *Domain-Driven Design* (2003) Part II (chapters 5–7) on the building blocks. Then read Vaughn Vernon's 3-part article series "Effective Aggregate Design" (kalele.io/effective-aggregate-design/) — it is the definitive guide on keeping aggregates small and correctly defining consistency boundaries. The critical rule: **each transaction should modify exactly one aggregate**. In Kotlin, value objects map naturally to `data class` with `val` properties, and aggregates enforce invariants through encapsulated methods. Study the GitHub repository ttulka/ddd-example-ecommerce-kotlin for a clean Kotlin + Spring Boot DDD implementation with hexagonal architecture.

**Week 5** introduces domain events, repositories, and domain services. Read Vernon's *Implementing Domain-Driven Design* chapters 8 (Domain Events), 12 (Repositories), and 7 (Services). Domain events are the bridge between tactical and strategic DDD — they represent facts that happened within an aggregate that other bounded contexts may care about. In Spring Boot, use `AbstractAggregateRoot` and `@DomainEventListener` for intra-process events, graduating to Kafka-backed events when crossing service boundaries. Study the paucls/runbook-ddd-kotlin repository for an OO-style domain layer where entities register domain events.

**Week 6** focuses on hexagonal (ports-and-adapters) architecture as the packaging structure for DDD. This architecture keeps domain logic independent of infrastructure — essential for future extraction into microservices. Study dustinsand/hex-arch-kotlin-spring-boot, a multi-module Gradle project using Kotlin's `internal` modifier and ArchUnit for enforcing boundaries. Watch Michael Plöd's "Implementing DDD with the Spring Ecosystem" (Spring I/O 2018) for Spring-specific implementation of aggregates, repositories, and domain events.

**Books to read during this phase:** Continue *Learning Domain-Driven Design* chapters 13–16 (covering microservice boundaries, event-driven architecture, and testing). Begin *Implementing Domain-Driven Design* by Vernon — focus on Part II (tactical building blocks) and Part IV (strategic design applied). For a deeper Kotlin-specific perspective, study the Creditas/kotlin-ddd-sample repository which demonstrates CQRS with Axon Framework in Kotlin.

### Milestone project: Build a single bounded context with full tactical DDD

Implement the "Ordering" bounded context from Phase 1 in Kotlin + Spring Boot. Requirements: (1) at least 3 aggregates (Order, Customer within ordering context, Promotion) with proper invariant enforcement; (2) value objects for Money, Address, OrderLineItem; (3) domain events published via Spring's `ApplicationEventPublisher` for OrderPlaced, OrderCancelled, PaymentConfirmed; (4) repository interfaces in the domain layer with Spring Data JPA implementations in the infrastructure layer; (5) hexagonal architecture with clear port/adapter separation across Gradle modules; (6) ArchUnit tests verifying no domain-to-infrastructure dependency leakage. Use Aurora PostgreSQL as the database.

---

## Phase 3: Monolith decomposition strategy — the art of incremental extraction (Weeks 7–10)

This is where your two existing books — Newman's *Monolith to Microservices* and Feathers' *Working Effectively with Legacy Code* — become central. The goal: learn every major decomposition pattern and practice the most critical one (Strangler Fig) alongside Spring Modulith as a stepping stone.

**Week 7:** Read Newman's *Monolith to Microservices* cover to cover. It is a short, dense book that provides a decision framework for when to decompose (and critically, **when NOT to**). Key chapters: Chapter 2 (Planning a Migration — defining clear goals), Chapter 3 (Splitting the Monolith — Strangler Fig, Branch by Abstraction, Parallel Run, Decorating Collaborator), and Chapter 4 (Decomposing the Database). Internalize Newman's principle that **the database is the hardest part to split** and that you should split the code first, data second. Study the AWS Prescriptive Guidance on the Strangler Fig pattern (docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler-fig.html), which is directly relevant to your AWS deployment context.

**Week 8:** Focus on Feathers' *Working Effectively with Legacy Code* techniques applied to decomposition. Key chapters: the Seam Model (finding natural cut points in existing code without rewriting), Sprout Method/Class (adding new behavior in new structures), and the dependency-breaking techniques. These are essential for real-world monolith work where you cannot redesign from scratch. Complement with the Shopify engineering case study "Deconstructing the Monolith" (shopify.engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity) and its follow-up "Under Deconstruction: The State of Shopify's Monolith." **Shopify chose a modular monolith over microservices** for their 2.8M-line codebase — understanding their reasoning is essential for making honest trade-off decisions.

**Weeks 9–10:** Deep dive into Spring Modulith. Read the official reference documentation (docs.spring.io/spring-modulith/reference/) and the JetBrains Kotlin Blog post "Building Modular Monoliths with Kotlin and Spring" (blog.jetbrains.com/kotlin/2026/02/building-modular-monoliths-with-kotlin-and-spring/). Spring Modulith lets you enforce module boundaries within a single deployable unit, verify dependencies via `ApplicationModules.of(...)`, test modules in isolation with `@ApplicationModuleTest`, and externalize events to Kafka when you later extract a module into a separate service. This is the most natural migration path for a Spring Boot engineer: **monolith → modular monolith (Spring Modulith) → microservices**. Study the Baeldung tutorial (baeldung.com/spring-modulith) for hands-on setup.

**Critical case studies for this phase:** Read Uber's "Introducing Domain-Oriented Microservice Architecture" (eng.uber.com/microservice-architecture/) — with ~2,200 critical microservices, Uber discovered that unconstrained microservices create a "distributed monolith" and introduced DOMA (domains, layers, gateways, extensions), achieving **25–50% decrease in feature onboarding time**. Read the Amazon Prime Video team's counter-example where they moved from microservices back to a monolith, cutting costs by 90%. These case studies inoculate you against cargo-cult microservices adoption.

**Korean resources:** Coupang's two-part engineering blog series on building their microservice architecture (medium.com/coupang-engineering) describes their 2013 "Vitamin Project" transitioning from a monolithic architecture to MSA. Woowahan Bros' WOOWACON 2020 presentation "배달의민족 마이크로서비스 여행기" by 김영한 is the seminal Korean-language presentation on monolith-to-microservices migration. 오늘의집's "MSA Phase 1: 백엔드 분리작업" (bucketplace.com) provides an exceptionally practical walkthrough covering DB separation, API Gateway with Aggregator pattern, BFF, and traffic shadowing for verification.

### Milestone project: Build a monolith, modularize it, then extract one service

Build a simplified e-commerce monolith (3–4 modules: Catalog, Ordering, Inventory, Notification) as a single Spring Boot application with a shared Aurora MySQL database. Then: (1) refactor it into a Spring Modulith application with enforced module boundaries and `@ApplicationModuleTest`-verified isolation; (2) introduce inter-module communication via Spring Modulith's event publication (replacing direct method calls); (3) extract the Notification module into a separate Spring Boot service using the Strangler Fig pattern — route requests through Spring Cloud Gateway, publish events to Kafka instead of in-process events, and verify correctness with parallel run (shadow traffic comparing old and new paths). Document every decision and trade-off.

---

## Phase 4: Data decomposition and inter-service communication (Weeks 11–14)

Splitting databases is the hardest part of microservice migration. This phase tackles database-per-service patterns, Change Data Capture, and the full spectrum of synchronous and asynchronous communication.

**Weeks 11–12** focus on data decomposition. Study Chapter 4 of Newman's *Monolith to Microservices* again, then read Chris Richardson's *Microservices Patterns* (O'Reilly, 2018) chapters 2 and 7, which cover database-per-service, API Composition for distributed queries, and CQRS. Learn three database decomposition patterns: (1) **shared database** (starting point — explicit, managed coupling), (2) **database-per-service** (target state — full autonomy), and (3) **database wrapping service** (intermediate — a thin service that owns and mediates all access to a shared schema). For CDC, study Debezium deeply. The official Debezium blog post "DDD Aggregates via CDC-CQRS Pipeline using Kafka & Debezium" (debezium.io/blog/2023/02/04/) is the single best resource connecting DDD, CDC, CQRS, and Kafka into a coherent pipeline. For hands-on practice, use the Spring Boot CDC example at github.com/BatuhanKucukali/spring-boot-cdc-example-with-debezium (PostgreSQL + Debezium + Kafka + Docker Compose). The article "Spring Boot-Debezium for CDC — Kafka-MySQL-Redis-Cacheable" directly matches your stack (MySQL + Redis + Kafka) and implements real-time cache invalidation.

**Weeks 13–14** cover inter-service communication patterns. For **synchronous** communication: implement REST (Spring WebClient for non-blocking calls, OpenFeign for declarative clients) and gRPC (using the official Spring gRPC 1.0 GA — see Piotr Minkowski's December 2025 guide at piotrminkowski.com/2025/12/15/grpc-spring/). For Kotlin-specific gRPC with coroutines, study the Baeldung guide (baeldung.com/kotlin/grpc). For **asynchronous** communication: implement Kafka-based event-driven patterns using Spring Cloud Stream (for abstraction) and native Kafka clients (for understanding internals first, per the learner's preference). Study Stéphane Maarek's Kafka Beginners course (Udemy, updated for Kafka 4.0) and Vinoth Selvaraj's "Kafka Event-Driven Microservices Part 1" for Spring-specific Kafka patterns. Implement both **choreography** (services react to events independently) and a basic **orchestration** (a coordinator service directs the flow). For the API Gateway, study Spring Cloud Gateway's official guide (spring.io/guides/gs/gateway/) and implement route-based traffic splitting, which you will need for Strangler Fig in production.

**Key concepts to internalize:** The CAP theorem's practical implications for your Aurora MySQL/PostgreSQL setup, **eventual consistency** as the default model across service boundaries, the difference between Event Notification (thin events triggering action) and Event-Carried State Transfer (fat events eliminating queries), and Martin Fowler's article "What do you mean by Event-Driven?" (martinfowler.com/articles/201701-event-driven.html) which distinguishes four patterns engineers constantly conflate.

### Milestone project: Split the database and implement multi-pattern communication

Take the extracted service from Phase 3 and go further: (1) give the Ordering service its own Aurora PostgreSQL database, separate from the monolith's Aurora MySQL; (2) implement Debezium CDC to capture changes from the monolith's Inventory table and replicate relevant data into the Ordering service's read model; (3) implement three communication patterns between services — REST (for synchronous queries), gRPC (for internal high-throughput calls between Ordering and Inventory), and Kafka events (for asynchronous notifications like OrderPlaced → Inventory reservation); (4) build an API Composition endpoint that aggregates data from Catalog + Ordering + Inventory via Spring Cloud Gateway; (5) implement a Redis cache layer in front of frequently-read Catalog data, invalidated via CDC events. Run everything with Docker Compose including Debezium, Kafka, Redis, and two Aurora-compatible PostgreSQL instances.

---

## Phase 5: Distributed transactions and event-driven architecture (Weeks 15–18)

This is the phase where you confront the fundamental challenge of microservices: **maintaining data consistency across service boundaries without distributed transactions**. The Saga pattern, Transactional Outbox, and idempotency are not optional — they are survival skills.

**Weeks 15–16** focus on the Saga pattern. Study Chris Richardson's canonical reference at microservices.io/patterns/data/saga.html. Implement both variants: **choreography-based sagas** (each service publishes events and listens for events — simpler but harder to debug) and **orchestration-based sagas** (a central saga orchestrator coordinates the workflow — more complex but more visible). The key learning: sagas require **compensating transactions** for every step that might need to be undone. An OrderCreated event that triggers inventory reservation must have a corresponding InventoryReservationCancelled compensation if payment fails. Study Piotr Minkowski's "Deep Dive into Saga Transactions with Kafka Streams and Spring Boot" (piotrminkowski.com/2022/02/07/) and the GitHub repository semotpan/saga-orchestration for a full implementation with Transactional Outbox + Debezium + Kafka Connect.

**Week 17** covers the Transactional Outbox pattern and idempotency. The outbox pattern solves the dual-write problem: instead of writing to the database AND publishing to Kafka (which can partially fail), you write both the business data and the outbox event in a single database transaction, then a separate process (Debezium or a polling publisher) reliably delivers events to Kafka. Study the InfoQ article "Saga Orchestration for Microservices Using the Outbox Pattern" (by the Debezium team) and Roman Kudryashov's "Event-Driven Architecture on the Modern Stack of Java Technologies" (romankudryashov.com/blog/2024/07/event-driven-architecture/) — this Kotlin + Spring Boot 3 + PostgreSQL + Kafka + Debezium implementation is the closest match to your production stack. For idempotency, implement the **Inbox pattern** (deduplicating incoming messages by storing processed message IDs) alongside idempotency keys for API endpoints.

**Week 18** explores frameworks and CQRS. Study Axon Framework via the Baeldung guide (baeldung.com/axon-cqrs-event-sourcing) and official docs (docs.axoniq.io). Then study Eventuate Tram (eventuate.io) — specifically the customers-and-orders examples for both choreography-based and orchestration-based sagas. The learner's preference is to implement abstractions from scratch before using libraries, so: **first build a hand-rolled saga orchestrator** with Kafka and PostgreSQL, then compare your implementation against Axon and Eventuate to understand what they abstract away. For CQRS, implement separate read and write models — write side with PostgreSQL, read side with Redis or a denormalized PostgreSQL table, synchronized via Kafka events.

**Essential Udemy courses for this phase:** Ali Gelenler's "Microservices: Clean Architecture, DDD, SAGA, Outbox & Kafka" is the gold-standard course for these patterns — it builds 4–5 microservices from scratch with Hexagonal Architecture, DDD, Saga (both variants), Outbox, CQRS, and Kafka. Vinoth Selvaraj's "Kafka Event-Driven Microservices Part 2" covers Saga Choreography & Orchestrator patterns plus Transactional Outbox with Kafka. Sergey Kargopolov's "Event-Driven Microservices, CQRS, SAGA, Axon 4, Spring Boot" provides Axon-specific implementation.

**Korean resources:** Toss's "은행 최초 코어뱅킹 MSA 전환기" (toss.tech/article/slash23-corebanking) describes migrating a core banking system to MSA with zero-downtime — a domain where distributed transaction correctness is literally required by regulation. Samsung SDS's article "당신의 MSA는 안녕하신가요? MSA를 보완하는 아키텍처: EDM" covers Event-Driven Microservice architecture as a complement to MSA.

### Milestone project: Implement a complete order processing saga with failure handling

Build a 4-service order processing system (Order, Payment, Inventory, Shipping) with: (1) an orchestration-based saga for the happy path (CreateOrder → ReserveInventory → ProcessPayment → ConfirmShipping → CompleteOrder); (2) compensating transactions for every failure scenario (payment fails → release inventory; shipping unavailable → refund payment + release inventory); (3) Transactional Outbox pattern using PostgreSQL + Debezium for reliable event delivery to Kafka; (4) Inbox pattern for message deduplication; (5) idempotency keys on all external-facing API endpoints; (6) a CQRS read model that aggregates order status from all services into a queryable Redis-backed view. **Critically, write chaos tests**: kill the Payment service mid-saga and verify the system eventually reaches a consistent state through compensating transactions. Document every failure mode you discover.

---

## Phase 6: Observability, resilience, and production hardening (Weeks 19–21)

A microservices system without observability is a distributed monolith you cannot debug. This phase adds the instrumentation, fault-tolerance patterns, and operational tooling that separate toy projects from production systems.

**Week 19** covers distributed tracing and centralized logging. Set up OpenTelemetry with Spring Boot 3 following the official Spring Blog guide (spring.io/blog/2025/11/18/opentelemetry-with-spring-boot/) — use the `spring-boot-starter-opentelemetry` approach for automatic instrumentation of HTTP, Kafka, and database calls. Export traces to Jaeger and metrics to Prometheus. Implement **correlation IDs** that propagate across all services via HTTP headers and Kafka message headers. For centralized logging, configure structured JSON logging with Logback, include trace IDs and span IDs in every log line, and aggregate with the ELK stack (Elasticsearch + Logstash + Kibana). Study the Baeldung guide "Observability With Spring Boot 3" (baeldung.com/spring-boot-3-observability) for the Micrometer Observation API that produces metrics and traces from a single instrumentation point.

**Week 20** focuses on resilience patterns with Resilience4j. Implement all five patterns: **Circuit Breaker** (prevent cascade failures when a downstream service is down), **Retry** (with exponential backoff for transient failures), **Timeout** (bound all external calls), **Bulkhead** (isolate thread pools per downstream service), and **Rate Limiter** (protect services from being overwhelmed). Use the official Resilience4j Spring Boot 3 integration (resilience4j.readme.io/docs/getting-started-3) with annotation-based configuration. Study the decorator composition pattern where you layer Circuit Breaker → Retry → Bulkhead on a single call. Connect all Resilience4j metrics to Micrometer for dashboard visibility. Read Netflix's architecture lessons summarized in the NGINX/F5 blog post "Adopting Microservices at Netflix: Lessons for Architectural Design" — Netflix's Chaos Monkey philosophy of proactively testing failure modes is the mindset to adopt.

**Week 21** covers Spring Boot Actuator deep dive and health management. Configure liveness and readiness probes for Kubernetes deployment (essential for your EKS/ECS stack). Implement custom health indicators that check downstream dependencies (database connectivity, Kafka broker availability, Redis connection). Study Spring Boot Actuator's `/metrics`, `/health`, `/env`, and `/info` endpoints. Build Grafana dashboards for service-level objectives (SLOs): request latency p50/p95/p99, error rates, throughput, and saga completion rates.

**Korean resources:** Toss's "은행 앱에도 Service Mesh 도입이 가능한가요?" (toss.im/slash-22) covers service mesh for MSA reliability in banking. Toss's "토스는 Gateway 이렇게 씁니다" explains their Netflix Passport-inspired API Gateway pattern for propagating authentication across microservices — a practical observability and security pattern.

### Milestone project: Add full observability and resilience to the Phase 5 system

Instrument the 4-service order processing system with: (1) OpenTelemetry traces exported to Jaeger, showing end-to-end saga flows across all services including Kafka hops; (2) structured JSON logging with ELK stack aggregation, searchable by correlation ID; (3) Resilience4j circuit breakers on all inter-service calls with Grafana dashboards showing circuit state transitions; (4) retry with exponential backoff on transient Kafka consumer failures; (5) bulkhead isolation between the Payment and Inventory call paths; (6) Kubernetes-ready liveness/readiness probes with custom health indicators; (7) a Grafana dashboard showing: saga success/failure rates, p99 latency per service, circuit breaker state, Kafka consumer lag, and database connection pool utilization. **Then simulate failures**: kill Kafka brokers, introduce artificial latency in the Payment service, exhaust database connections — and verify your system degrades gracefully rather than cascading.

---

## Phase 7: Capstone — full migration simulation (Weeks 22–24)

Everything converges. You build a realistic monolith from scratch, apply DDD to discover its boundaries, and execute a phased migration into microservices using every pattern learned.

**Week 22:** Build a monolithic e-commerce application in Kotlin + Spring Boot with a single Aurora PostgreSQL database. It should have meaningful complexity: user management, product catalog with search, shopping cart, order processing, payment integration (mock), inventory management, shipping tracking, and notification (email/push). Implement it as a well-structured modular monolith using Spring Modulith from the start, but with deliberate coupling between modules to simulate legacy code.

**Week 23:** Apply the full DDD decomposition process. Run Event Storming on your own system. Identify bounded contexts. Create a context map. Classify subdomains. Choose which contexts to extract first based on Newman's criteria (team autonomy needs, independent scalability, technology heterogeneity requirements). Execute the Strangler Fig extraction: route traffic through Spring Cloud Gateway, extract the highest-value bounded context into a separate service with its own database, implement CDC for data synchronization, Kafka events for async communication, and a saga for the order processing flow that now spans services.

**Week 24:** Add production-grade operational concerns. Deploy on Docker Compose (simulating EKS). Add the full observability stack. Implement chaos scenarios. Write a comprehensive Architecture Decision Record (ADR) document explaining every boundary decision, every pattern choice, and every trade-off. This document becomes your portfolio artifact.

### Capstone deliverables

- A modular monolith with Spring Modulith and at least 3 extracted microservices
- Database-per-service with Debezium CDC synchronization
- Saga-based distributed transaction for order processing
- gRPC for internal communication, REST for external APIs, Kafka for events
- Full OpenTelemetry + ELK + Grafana observability stack
- Resilience4j fault tolerance on all inter-service calls
- Redis caching with CDC-based invalidation
- Spring Cloud Gateway with route-based traffic splitting
- Architecture Decision Records documenting all trade-offs
- A chaos test suite proving graceful degradation

---

## Complete reading order and resource guide

### Books (sequenced for maximum learning efficiency)

| Order | Book | Why this position |
|-------|------|-------------------|
| 1 | *Learning Domain-Driven Design* — Vlad Khononov | Most accessible modern DDD introduction; covers strategic + tactical + microservices in one volume |
| 2 | *Monolith to Microservices* — Sam Newman (already owned) | Migration patterns and decision framework; pairs with Phase 3 |
| 3 | *Domain-Driven Design* — Eric Evans | The original — read Parts I–III for depth after Khononov provides the map |
| 4 | *Building Microservices* (2nd ed.) — Sam Newman | Comprehensive microservices architecture reference; covers communication, deployment, observability |
| 5 | *Implementing Domain-Driven Design* — Vaughn Vernon | Tactical implementation depth; read alongside Phase 2 coding |
| 6 | *Microservices Patterns* — Chris Richardson | Pattern catalog for Saga, CQRS, API Composition, Outbox; reference during Phases 4–6 |
| 7 | *Working Effectively with Legacy Code* — Michael Feathers (already owned) | Seam model and dependency-breaking techniques; reference during Phase 3 |
| 8 | *Cloud Native Spring in Action* — Thomas Vitale | Spring Boot + Docker + Kubernetes operational depth; reference during Phases 6–7 |

### Top Udemy courses (ranked by impact)

1. **"Microservices: Clean Architecture, DDD, SAGA, Outbox & Kafka"** by Ali Gelenler — The single most comprehensive course covering DDD, Hexagonal Architecture, Saga (both variants), Outbox, CQRS, and Kafka with Spring Boot. Start in Phase 5.
2. **"Kafka Event-Driven Microservices Parts 1 & 2"** by Vinoth Selvaraj — Part 1 covers Kafka fundamentals with reactive Spring; Part 2 covers Saga Choreography, Orchestrator, and Transactional Outbox. Your Kafka deep dive for Phase 4–5.
3. **"Apache Kafka for Beginners v3"** by Stéphane Maarek — Updated for Kafka 4.0. The definitive Kafka fundamentals course. Start in Phase 4.
4. **"gRPC Java: High-Performance Spring Boot Microservices"** by Vinoth Selvaraj — All 4 streaming patterns, load balancing, security. Essential for Phase 4 gRPC implementation.
5. **"Master Microservices with Spring Boot and Spring Cloud"** by in28minutes — The most popular Spring Cloud course (250K+ students). Good as a quick refresher if you need to solidify Spring Cloud basics.
6. **"The Complete Microservices & Event-Driven Architecture"** by Michael Pogrebinsky — Architecture/design focused with case studies from Google, Netflix, Uber. Good supplement for Phase 3.
7. **"Event-Driven Microservices, CQRS, SAGA, Axon 4, Spring Boot"** by Sergey Kargopolov — Axon Framework-specific implementation. Use in Phase 5 Week 18.

### Conference talks (curated top 10)

1. **Eric Evans** — "Defining Bounded Contexts" (DDD Europe 2019) — Four types of bounded contexts
2. **Alberto Brandolini** — "50,000 Orange Stickies Later" (Explore DDD 2017) — Event Storming overview
3. **Michael Plöd** — "DDD Strategic Design with Spring Boot" (Spring I/O 2017) — Context maps with live code
4. **Michael Plöd** — "Implementing DDD with the Spring Ecosystem" (Spring I/O 2018) — Tactical patterns in Spring
5. **Uber Engineering** — "Introducing DOMA" (blog post, functions as a talk) — Domain-oriented microservice architecture
6. **Vlad Khononov** — Tech Lead Journal Episode #76 — Strategic vs tactical DDD practical discussion
7. **Nick Tune** — "The Art of Discovering Bounded Contexts" — Practical boundary discovery process
8. **Vaughn Vernon** — CoRecursive Podcast Episode 18 — How bounded contexts map to microservices
9. **Eric Evans** — SE Radio Episode 226 — DDD at 10 years, strategic design evolution
10. **Jessica Tai** — "The Human Side of Airbnb's Microservice Architecture" (InfoQ) — Organizational challenges of migration

### Korean tech company case studies

| Company | Key Resource | Focus |
|---------|-------------|-------|
| 배달의민족 | WOOWACON 2020 "마이크로서비스 여행기" + techblog.woowahan.com/7835/ | Full monolith→MSA journey; event-driven member system |
| Toss | toss.tech/article/slash23-corebanking | Core banking MSA migration with zero downtime |
| Coupang | medium.com/coupang-engineering (2-part series) | 2013 Vitamin Project; API-adapter pattern at scale |
| Kurly | helloworld.kurly.com/blog/ddd-msa-service-development/ | DDD bounded contexts ↔ MSA mapping |
| Kurly | helloworld.kurly.com/blog/oms-msa-architecture-1/ | OMS microservice sizing decisions |
| Kakao | tech.kakao.com/posts/555 | DDD adoption in a recommendation platform |
| KakaoBank | tech.kakaobank.com/tags/msa/ | 30M daily traffic home service MSA separation |
| 오늘의집 | bucketplace.com MSA Phase 1 post | Practical backend separation with BFF and gRPC |
| LINE | engineering.linecorp.com — Armeria authentication microservice | Inter-service authentication in MSA |
| Toss | toss.tech/article/slash23-server | Netflix Passport-inspired API Gateway |

### Western company case studies

- **Uber DOMA** (eng.uber.com/microservice-architecture/) — Domain-oriented microservice architecture organizing ~2,200 services
- **Shopify Modular Monolith** (shopify.engineering/deconstructing-monolith + follow-up) — Why they chose NOT to go microservices
- **Airbnb SOA Migration** (InfoQ presentations by Selina Liu and Jessica Tai) — Human coordination challenges of migration
- **Netflix** (netflixtechblog.com/tagged/microservices) — Chaos engineering, bounded context discovery, federated GraphQL
- **Stripe** (blog.nelhage.com/post/stripe-dev-environment/) — Monorepo + selective extraction strategy
- **Amazon** (aws.amazon.com/executive-insights/content/amazon-two-pizza-team/) — Two-pizza teams and Conway's Law in action

### Essential GitHub repositories

| Repository | Stars | Use Case |
|-----------|-------|----------|
| ddd-crew/ddd-starter-modelling-process | ~3.3K | 8-step DDD process guide |
| ddd-crew/bounded-context-canvas | — | Boundary documentation template |
| heynickc/awesome-ddd | — | Curated mega-list of all DDD resources |
| ttulka/ddd-example-ecommerce-kotlin | — | Kotlin + Spring DDD hexagonal architecture |
| sqshq/piggymetrics | 12K+ | Canonical Spring Cloud microservices reference |
| piomin/sample-spring-microservices-new | — | Modern Spring Cloud patterns (continuously updated) |
| eventuate-tram/eventuate-tram-examples-customers-and-orders | — | Choreography-based saga example |
| eventuate-tram/eventuate-tram-sagas-examples-customers-and-orders | — | Orchestration-based saga example |
| semotpan/saga-orchestration | — | Saga + Outbox + Debezium + Kafka Connect |
| meysamhadeli/booking-microservices-java-spring-boot | — | CQRS + Outbox + Inbox + gRPC comprehensive reference |
| AleksK1NG/Kotlin-Spring-gRPC-Microservice | — | Kotlin gRPC + PostgreSQL + Zipkin + Kubernetes |

### Key blog posts and articles

- Martin Fowler: BoundedContext, CQRS, EventSourcing, DomainEvent, "What do you mean by Event-Driven?"
- Vaughn Vernon: "Effective Aggregate Design" 3-part series (kalele.io)
- Nick Tune: Bounded Context Canvas V3, Workshop Recipe, Strategic DDD Remote Toolkit (Medium)
- Debezium: "DDD Aggregates via CDC-CQRS Pipeline" (debezium.io/blog/2023/02/04/)
- Roman Kudryashov: "Event-Driven Architecture on Modern Java Stack" — Kotlin + Spring Boot 3 + Outbox + Saga (romankudryashov.com)

---

## When to resist the urge to decompose

No mastery-level plan is complete without encoding the discipline of restraint. Throughout this curriculum, keep these anti-patterns and decision criteria visible:

**Do not decompose when** your team is smaller than 8 engineers and does not experience deployment contention; when your domain boundaries are still unclear (premature splitting creates distributed monoliths that are worse than the original); when your organization lacks the operational maturity for distributed tracing, independent deployments, and on-call rotations per service; or when a modular monolith (Spring Modulith) provides the modularity benefits without the distributed systems tax. Samsung SDS's article "Do Not Use MSA — 마이크로서비스 아키텍처가 꼭 필요한가요?" provides a thoughtful enterprise-perspective critique worth reading early.

The Amazon Prime Video team's public reversal — moving from serverless microservices back to a monolith and cutting costs by 90% — demonstrates that **the goal is never microservices; the goal is sustainable software delivery velocity**. Every pattern in this curriculum is a tool. Mastery means knowing when not to use it.