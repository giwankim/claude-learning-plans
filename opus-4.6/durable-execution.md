---
title: "Mastering Durable Execution on the JVM"
category: "Backend Engineering"
description: "8–10 week roadmap covering Temporal, Restate, saga patterns, workflow versioning, and production-grade durable execution with Kotlin and Spring Boot"
---

# Mastery roadmap for durable execution on the JVM

Durable execution has no single canonical textbook — the field is too young. **Your learning path will be 70% official docs and courses, 20% high-signal blog posts and talks, and 10% books** that cover adjacent patterns. The good news: Temporal's free academy courses with Java SDK support, Restate's first-class Kotlin SDK with coroutine support, and a rich ecosystem of production case studies make self-directed mastery entirely achievable in 8–10 weeks of focused evening/weekend work.

This plan targets your exact profile: senior Kotlin + Spring Boot developer, strong distributed systems foundation, familiar with the framework landscape but needing structured depth. Every resource below was verified for current availability and JVM relevance.

---

## Phase 1: Conceptual foundations and first workflows (weeks 1–2, ~25 hours)

The goal here is to build a precise mental model of *how* durable execution works — event history, replay, determinism constraints — and get your first Spring Boot + Temporal workflow running. You already understand the "what" and "why," so skip introductory blog posts and go straight to the mechanics.

**Start with these three resources in order:**

Jack Vanlightly's "Demystifying Determinism in Durable Execution" (November 2025, jack-vanlightly.com) is the single best technical explanation of why determinism matters. It's framework-agnostic, separates control flow determinism from side-effect idempotency, and uses a concrete double-charge bug example that will immediately sharpen your intuition. Follow it with his two-part "Durable Function Tree" series (December 2025), which formalizes how workflows form trees of durable function calls based on durable promises. These three posts together (~2 hours reading) give you a conceptual framework that no course provides.

Next, complete **Temporal 101 with Java** (learn.temporal.io/courses/temporal_101/java/, ~2 hours) and **Temporal 102: Exploring Durable Execution** (~4 hours). These are free, self-paced, and hands-on. The Java SDK works seamlessly from Kotlin. Course 101 covers workflows, activities, workers, and the web UI. Course 102 dives into testing, debugging, history replay, and common developer pitfalls. Together they give you the mechanical foundation everything else builds on.

Then run the **Temporal Spring Boot demo** (github.com/temporalio/spring-boot-demo) and explore the official Spring Boot integration docs (docs.temporal.io/develop/java/spring-boot-integration). The official starter artifact `io.temporal:temporal-spring-boot-starter:1.32.1` provides auto-configured `WorkflowClient`, annotation-based worker registration via `@WorkflowImpl` and `@ActivityImpl`, Actuator metrics, and OpenTelemetry tracing out of the box. Add `io.temporal:temporal-kotlin:1.32.1` for Kotlin-specific extensions.

**Phase 1 hands-on project — Hello Temporal with Kotlin + Spring Boot:** Build a minimal REST API that starts a greeting workflow. Define a `GreetingWorkflow` interface with `@WorkflowMethod`, implement activities as Spring `@Service` beans, and trigger everything from a controller. Run `temporal server start-dev` locally and observe event history in the web UI at localhost:8233. This should take about 2 hours and teaches task queues, worker auto-discovery, and the Spring Boot integration lifecycle.

**Supporting resources for Phase 1:**

| Resource | Type | Time | Priority |
|----------|------|------|----------|
| Temporal "What is Durable Execution" blog post | Concept | 20 min | High |
| swyx "Temporal — the iPhone of System Design" (swyx.io/why-temporal) | Concept | 30 min | High |
| Maxim Fateev, WeAreDevelopers keynote: "Durable Execution: A Revolutionary Abstraction" | Talk | 45 min | High |
| SE Radio 596: Fateev on Durable Execution with Temporal | Podcast | 69 min | Medium |
| *Think Distributed Systems* by Dominik Tornow (Manning, 2025) — Chapter 11 | Book | 2 hr | Medium |

Tornow's book is the **only published book with a full chapter titled "Durable Executions."** Chapter 11 covers failure-free definitions, failure-tolerant executions, restart vs. resume recovery strategies, and explicitly contrasts sagas with durable executions. The rest of the book (chapters 5–6 on transactions, chapter 10 on consensus) provides excellent mental models. It uses pseudocode rather than JVM code, but at your level, that's a feature — it forces conceptual rather than copy-paste learning.

---

## Phase 2: Production patterns and the saga deep dive (weeks 3–5, ~30 hours)

Now you build fluency with the patterns you'll actually use in production: sagas, signals, queries, long-running workflows, human-in-the-loop, error handling strategies, and versioning. This phase also introduces Restate as a contrasting approach.

**Complete these Temporal Academy courses:**

- **Crafting an Error Handling Strategy** (~2.5 hours) — covers idempotence, heartbeating, and the **saga pattern** implementation using Temporal's `Saga` utility class. This is the most directly relevant course for your Kafka + microservices background.
- **Interacting with Workflows** (~3 hours) — signals, queries, search attributes, async activity completion. These are the building blocks for human-in-the-loop and event-driven integration.
- **Versioning Workflows** (~1.5 hours) — safely evolving workflow code in production. This is the single hardest operational challenge in durable execution, and this course covers both patching APIs and worker versioning.
- **Securing Application Data** (~2 hours) — custom data converters, codec servers, encryption. Important for any production deployment handling PII or financial data.

**Simultaneously, explore Restate's Kotlin SDK.** Start with the Kotlin quickstart at docs.restate.dev/quickstart#kotlin (~30 minutes), then work through the SDK documentation sections on durable steps, service communication, state management, and concurrent tasks (~4–6 hours total). Restate's Kotlin SDK is the **most Kotlin-idiomatic durable execution experience available** — it has native coroutine/suspend function support, `DurablePromise` as a durable analog to Kotlin's `Deferred`, and `awaitAll` that mirrors `kotlinx.coroutines.awaitAll`. The dependency is `dev.restate:sdk-kotlin-http:2.4.1` with `dev.restate:sdk-api-kotlin-gen:2.4.1` for KSP annotation processing.

**Critical blog posts for this phase:**

Chris Gillum's "Common Pitfalls with Durable Execution Frameworks" (Medium, ~September 2022) is **essential reading before writing production code.** As the creator of Azure Durable Functions, Gillum catalogs the biggest gotchas: non-determinism bugs, versioning complexity, payload size limits, idempotency requirements, and schema evolution. This post is widely referenced by Riccomini, Vanlightly, and others as the definitive pitfalls guide.

Read Restate's "Why We Built Restate" (restate.dev/blog) to understand their log-centric architecture and how it differs from Temporal's external orchestration approach. Follow with "Every System is a Log" and "Building a Modern Durable Execution Engine from First Principles" by Stephan Ewen — the latter includes benchmarks (**94K actions/second, p50 of 10ms per step**) and explains the virtual log abstraction. These posts are technically dense and reward careful reading.

DBOS's "Why Durable Execution Should Be Lightweight" (dbos.dev/blog) articulates the library-vs-service debate. DBOS implements durable execution as a Postgres-backed library rather than an external orchestrator. Even if you choose Temporal or Restate, understanding this alternative sharpens your architecture thinking.

**Phase 2 hands-on projects:**

**Project A — Money transfer with saga compensation:** Build a transfer service with `withdraw`, `deposit`, and `refund` activities. Use Temporal's `Saga` class to register compensations. Simulate deposit failures and observe compensation execution in the UI. Reference: `temporalio/samples-java` → `bookingsaga/` and `money/` samples. (~4 hours)

**Project B — Email drip campaign (official tutorial):** Follow Temporal's "Build an Email Drip Campaign with Java and Spring Boot" tutorial (learn.temporal.io/tutorials/java/build-an-email-drip-campaign/). This is a complete project with REST endpoints, signals for unsubscribe, queries for subscription status, and durable `Workflow.sleep()` for intervals. Source code at github.com/temporalio/email-drip-campaign-project-java. (~3–4 hours)

**Project C — Human-in-the-loop approval workflow:** Build a purchase order system where orders above a threshold wait (potentially days) for manager approval via signals. Use `Workflow.await(Duration.ofDays(3)) { approvalDecision != null }` for conditional waits with timeout escalation. Add `@UpdateMethod` for synchronous approval responses. This teaches the workflow-as-entity pattern. (~4 hours)

**Books for this phase:**

*Microservices Patterns* by Chris Richardson (Manning, 2018; 2nd edition in MEAP) has the most comprehensive published treatment of the saga pattern. **Chapter 4 ("Managing Transactions with Sagas")** covers choreography-based and orchestration-based sagas, isolation countermeasures, and the semantic challenges of distributed transactions. All examples use Java with the Eventuate Tram framework. Chapter 6 covers event sourcing combined with sagas. If you own only one patterns book, this is it.

*Practical Process Automation* by Bernd Ruecker (O'Reilly, 2021) provides the BPMN-based workflow engine perspective. It uses Camunda 7 with Java/Spring Boot examples. While it takes a different approach (visual process models vs. code-first), chapters 4 ("Orchestrate Anything") and 6–8 (orchestration vs. choreography, architecture patterns) contain transferable architectural insights. Read selectively rather than cover-to-cover.

---

## Phase 3: Advanced mastery and production readiness (weeks 6–8, ~30 hours)

This phase targets the hard problems: multi-service orchestration with Kafka, workflow versioning at scale, observability, ContinueAsNew for unbounded workflows, and the architectural decision framework for when durable execution is (and isn't) the right choice.

**Deep-dive talks and conference content:**

Watch the **Temporal Java SDK Workshop playlist** on YouTube (youtube.com/playlist?list=PLl9kRkvFJrlSNuTvL0dl3VE5GEe1HFtjf). This multi-session series led by Temporal's Tihomir Surdilovic covers advanced Java SDK topics: dynamic workflows/activities, typed vs. untyped stubs, parallel activity execution, ContinueAsNew, SSL/mTLS, and workflow constraints (e.g., never use native Java threads). This is the most directly relevant video resource for JVM developers.

Giselle van Dongen's talks are exceptionally relevant to your profile. Her **KotlinConf 2024** presentation on durable execution with Restate is the only major conference talk specifically targeting Kotlin developers. Her **Devoxx Belgium 2024 deep-dive lab** is a hands-on Java session building an e-commerce backend with Restate — exactly transferable to Kotlin. Her **Devoxx Poland 2024** talk covers the three durable building blocks (communication, execution, state) with Java examples.

Stephan Ewen's **Devoxx Poland 2024** talk, "Event-Driven Applications vs. Durable Execution in Practice," directly compares when to use each approach — critical for someone with your Kafka background. Sergey Bykov's **QCon SF 2023** talk (available on InfoQ with full transcript) covers how Temporal built its own cloud control plane using durable execution, including cell architecture and deployment rings.

**The Changelog podcast episode #636** with Stephan Ewen is the best audio comparison of Restate vs. Temporal architectures and the broader durable execution landscape.

**Advanced blog posts:**

Jack Vanlightly's **"Coordinated Progress" four-part series** (June–July 2025) provides the architectural decision framework you need. It models how event-driven architecture, stream processing, and durable execution fit together, and Part 4 delivers a practical decision framework for choosing between approaches. Combined with Kai Waehner's "The Rise of the Durable Execution Engine in an Event-Driven Architecture (Apache Kafka)" (June 2025, kai-waehner.de), you'll have a clear mental model for where durable execution complements your existing Kafka infrastructure.

Chris Riccomini's "Durable Execution: Justifying the Bubble" (materializedview.io, November 2023) is the best critical market analysis — it argues the space is overcrowded and that second-generation frameworks need to unify stream processing with durable execution. Given Riccomini is co-authoring the **2nd edition of *Designing Data-Intensive Applications*** with Kleppmann (which explicitly adds a "Durable Execution and Workflows" section), his perspective carries significant weight.

The Netflix Tech Blog post "How Temporal Powers Reliable Cloud Operations at Netflix" (December 2025) is the most compelling enterprise case study: Netflix reduced transient deployment failures from **4% to 0.0001%** using Temporal for Spinnaker operations, with adoption doubling year-over-year since 2021. Uber's engineering posts on Cadence provide historical scale context — **12 billion executions and 270 billion actions per month** across 1,000+ services.

**Phase 3 hands-on projects:**

**Project A — Multi-service saga with Kafka integration:** Build a complete e-commerce order processing system as a Spring Boot multi-module project. The orchestrator uses Temporal workflows; individual services (order, inventory, payment, shipping) are separate Spring Boot apps. Activities call services via REST, and each successful step publishes events to Kafka for downstream consumers (CQRS projections, analytics). Use Temporal's Kafka Request/Reply sample from `temporalio/samples-java` → `springboot/kafka/` as a starting point. Add Prometheus metrics via Actuator and Jaeger tracing via OpenTelemetry. (~10–15 hours)

**Project B — Choreography-to-orchestration migration:** Start with three services communicating via Kafka events (pure choreography). Then introduce Temporal as orchestrator for new order types using a strangler fig pattern. Finally, migrate all flows. This exercise produces visceral understanding of why orchestration improves observability and error handling — and where choreography remains appropriate. (~8–10 hours)

**Project C — Long-running subscription manager with ContinueAsNew:** Build a subscription lifecycle workflow (trial → active → renewal → cancellation) that runs for months. Use `ContinueAsNew` to bound event history growth, child workflows for billing cycles, and search attributes for querying subscriptions by plan and status. This teaches the workflow-as-entity pattern at production scale. (~6–8 hours)

---

## The books shelf: what to read and what to skip

No full-length book exists specifically about Temporal, Cadence, or durable execution. Here's the prioritized reading list:

| Book | Author | Why it matters | JVM code? |
|------|--------|---------------|-----------|
| *Think Distributed Systems* (Manning, 2025) | Dominik Tornow | Only book with a dedicated durable execution chapter | Pseudocode |
| *Microservices Patterns* (Manning, 2018/2025) | Chris Richardson | Best saga pattern coverage; Ch. 4 essential | Java |
| *Designing Data-Intensive Applications* 2nd ed (O'Reilly, in progress) | Kleppmann & Riccomini | Adds "Durable Execution and Workflows" section | No |
| *Practical Process Automation* (O'Reilly, 2021) | Bernd Ruecker | Workflow engine perspective; Java/Spring Boot | Java |
| *Implementing Domain-Driven Design* (Addison-Wesley, 2013) | Vaughn Vernon | Event sourcing + sagas in Ch. 4 and Appendix A | Java |
| *Enterprise Integration Patterns* (Addison-Wesley, 2003) | Hohpe & Woolf | Process Manager pattern = saga orchestrator ancestor | Java/JMS |

Skip *Flow Architectures* (Urquhart) — too strategic, mixed reviews. Skip the Greg Young CQRS book — it was never published. The *DDIA* 2nd edition is the most anticipated: Riccomini built durable execution systems at WePay for payments processing, so his additions will carry production authority.

Temporal also publishes a free PDF, "Building Reliable Applications with Durable Execution" (assets.temporal.io), which functions as a short book covering consistency in distributed systems, writing durable code, and practical examples.

---

## Community and continuous learning infrastructure

**Daily/weekly engagement points:**

Join the **Temporal Slack** (t.mp/slack) and the **Temporal Community Forum** (community.temporal.io) — the forum is Discourse-based and fully searchable, making it better for reference than Slack's ephemeral threads. Join the **Restate Discord** (discord.com/invite/skW3AZ6uGd, ~1,200+ members) for a smaller but highly technical community where the founders are active.

Clone **temporalio/samples-java** (234 stars) immediately — the SpringBoot section includes Hello World, Booking Saga, Money Transfer, Money Batch, Kafka Request/Reply, and Apache Camel integration samples. Clone **restatedev/examples** for Java/Kotlin examples covering AI agents, workflows, microservice orchestration, and event processing.

Subscribe to **Temporal's monthly community newsletter** (temporal.io/blog) for SDK updates, meetup announcements, and user stories. Follow Kai Waehner's blog (kai-waehner.de) for Kafka + durable execution integration analysis. Watch the **Replay conference recordings** (temporal.io/resources) from 2023–2025 — they include production talks from Netflix, Stripe, Datadog, Instacart, and Yum! Brands.

**Key GitHub repositories to star and study:**

- `temporalio/sdk-java` — includes `temporal-spring-boot-starter`, `temporal-spring-boot-autoconfigure`, and `temporal-kotlin` modules
- `temporalio/samples-java` — your primary code reference for patterns
- `temporalio/spring-boot-demo` — reference implementation with metrics, tracing, and embedded web UI
- `restatedev/sdk-java` — JVM SDK with dedicated Kotlin coroutine support
- `restatedev/examples` — multi-language examples catalog
- `applicaai/spring-boot-starter-temporal` — community Spring Boot starter with `@ActivityStub` annotations (alternative to official starter)

---

## Conclusion

The fastest path to durable execution mastery for a JVM developer runs through **Temporal's free academy courses (Java SDK) → official Spring Boot integration → saga and versioning patterns → Restate's Kotlin SDK for architectural contrast**. The conceptual backbone comes from Vanlightly's determinism and durable function tree posts, Gillum's pitfalls guide, and Tornow's book chapter — not from any single comprehensive textbook, because one doesn't exist yet.

The field is converging on a key tension that your Kafka background positions you to navigate: **durable execution engines are moving down the stack toward lightweight libraries (DBOS, Restate) while workflow orchestrators are moving up toward general-purpose platforms (Temporal)**. Vanlightly's Coordinated Progress series and Riccomini's market analysis provide the decision framework. The practical answer for most Spring Boot shops today is Temporal (largest ecosystem, strongest Java SDK, most production case studies) with Restate as a compelling alternative for greenfield Kotlin services that prize developer ergonomics and low latency.

Budget **8–10 weeks at 8–10 hours per week**. Prioritize hands-on projects over passive consumption — the saga money transfer and email drip campaign tutorials alone will teach more than hours of reading. The determinism constraints and versioning challenges only become real when you hit them in code.