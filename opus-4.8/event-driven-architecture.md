---
title: "Event-Driven Architecture — A Practitioner's Guide"
category: "Data & Messaging"
description: "Rigorous, practitioner-focused guide to EDA for the Kotlin/Spring Boot + Kafka engineer: Fowler's four patterns, the dual-write problem and transactional outbox via CDC/Debezium, choreographed vs orchestrated sagas, and incremental (non-big-bang) adoption — through CQRS/event sourcing, with TLA+ for formally verifying protocol correctness."
---

# Event-Driven Architecture: A Rigorous, Practitioner's Guide for the Kotlin/Spring Boot + Kafka Engineer

## TL;DR
- **Adopt EDA to break temporal and design-time coupling, not for novelty.** Its core payoff is that producers stop knowing or waiting on consumers — enabling independent scaling, resilience to partial failure, and "free" extensibility (new consumers attach to existing event streams). You pay for this with eventual consistency, harder debugging, and real operational overhead, so adopt it where coupling and synchronous fan-out are actually hurting you.
- **Introduce it incrementally, never as a big-bang rewrite.** The proven path is: strangler fig around the monolith → transactional outbox (to kill the dual-write problem) → CDC with Debezium → a single event type → choreographed sagas → and only later CQRS/event sourcing. The running e-commerce order example below shows each step concretely.
- **Follow a staged learning path built on canonical sources.** Fowler's "What do you mean by Event-Driven?", Kleppmann's *Designing Data-Intensive Applications*, Richardson's *Microservices Patterns* + microservices.io, Hohpe & Woolf's *Enterprise Integration Patterns*, Bellemare's *Building Event-Driven Microservices*, and — given your math background — Lamport/Wayne's TLA+ for formally verifying the protocols you build.

---

## Key Findings

1. **"Event-driven" is four distinct patterns, not one.** Martin Fowler's taxonomy (Event Notification, Event-Carried State Transfer, Event Sourcing, CQRS) is the single most useful conceptual lens; most confusion in EDA discussions comes from conflating them. Decide which one you are actually doing.
2. **The dual-write problem is the central technical hazard of producing events**, and the transactional outbox pattern (Richardson) implemented via CDC/Debezium (Morling) is the canonical solution. For a Kotlin/Spring shop, Spring Modulith's event externalization gives you an outbox with at-least-once semantics almost for free.
3. **Choreographed sagas decouple but obscure flow; orchestrated sagas centralize and clarify.** This is the most important design-time tradeoff once you have more than ~3 steps in a distributed transaction.
4. **Real-world adoption is gradual and reversible.** Wix has been "gradually migrating our growing set of microservices (currently at 2300) from the request-reply pattern to event driven architecture over the last few years" (Natan Silnitsky, Wix Engineering); DoorDash "built the real time events processing system and scaled it to process hundreds of billions of events per day with a 99.99% delivery rate." Neither did a big-bang rewrite.
5. **Your mathematical background is a genuine asset.** EDA correctness questions (ordering, exactly-once, saga compensation, idempotency) are exactly the class of concurrent/distributed-protocol problems TLA+ was designed to model-check.

---

## Details

### PART 1 — MOTIVATION: Why adopt EDA?

#### The starting pain: synchronous, point-to-point coupling
In a conventional synchronous microservice (or distributed monolith) architecture, a service that needs work done calls another service directly and waits. Consider an order flow implemented as synchronous REST/gRPC calls: `OrderService` calls `PaymentService`, then `InventoryService`, then `ShippingService`, then `NotificationService`, in band, holding the user's HTTP request open. This design accretes several distinct problems:

- **Design-time (afferent) coupling.** `OrderService` must know the existence, location, API, and semantics of every downstream service. Sam Newman, in *Building Microservices* (2nd ed., O'Reilly, 2021), frames this through a coupling taxonomy — domain coupling, pass-through coupling, common coupling, content coupling — and argues that the goal of good microservice design is information hiding and low coupling. Synchronous call chains maximize exactly the couplings you want to minimize.
- **Temporal coupling.** All services in the chain must be simultaneously available. If `ShippingService` is down, the order fails — even though shipping is not actually needed at order-placement time. The synchronous request-response style makes availability *multiplicative*: a chain of five services each at 99.9% availability yields ~99.5% combined.
- **Synchronous fan-out bottlenecks and latency stacking.** End-to-end latency is the sum of the chain. Throughput is bounded by the slowest link. The calling thread is blocked, consuming resources.
- **Difficulty adding new consumers.** When a sixth concern appears (e.g., a fraud-analytics service that also cares about new orders), you must modify `OrderService` to add another call. Every new consumer is a code change to the producer — the antithesis of extensibility.
- **Lack of auditability.** The fact that "an order was placed" exists only as a transient state transition in a database row; there is no durable, replayable record of *what happened* and *when*.

Martin Fowler's article "What do you mean by 'Event-Driven'?" (martinfowler.com, 2017) is the foundational reference here. He decomposes "event-driven" into four patterns that are routinely conflated:

1. **Event Notification** — a system emits an event to notify others of a domain change, *not caring* who responds. This reverses the dependency: instead of `CustomerManagement` depending on `InsuranceQuoting`, `CustomerManagement` fires an `AddressChanged` event and quoting subscribes. Fowler explicitly notes the "dark side": *no statement of overall behavior* — the logical flow is no longer visible in any single piece of program text.
2. **Event-Carried State Transfer** — events carry enough state that consumers needn't call back to the source, improving availability and reducing load, at the cost of data replication and eventual consistency.
3. **Event Sourcing** — the event log is the system of record; state is rebuilt by replaying events (Fowler's analogy: git).
4. **CQRS** — separate models for reads and writes.

This taxonomy should anchor every design conversation: most teams begin wanting (1), drift into (2), and only some genuinely need (3) and (4).

#### The benefits EDA delivers
- **Loose coupling / dependency inversion.** The producer publishes a fact ("OrderPlaced") to a topic and is done. It has no compile-time or runtime dependency on consumers.
- **Independent scalability.** Consumers scale independently via Kafka partitions and consumer groups. A slow consumer doesn't back-pressure the producer.
- **Resilience to partial failure.** Because Kafka durably persists events and consumers process asynchronously, a downstream outage delays processing rather than failing the user-facing operation. Wix's engineering team describes precisely this motivation in "Wix's Journey Into Data Streams" (wix.engineering): in 2014 they were "reaching 60M site owners at a rate of +1M new registered site owners each month and ~300M monthly visitors. We had around 250 microservices running in production serving about 700M daily HTTP requests." As traffic scaled "to about 500 billion HTTP requests per day" across "over 2000 microservice clusters," in their words "the simple synchronous paradigm didn't hold up," prompting the move to Kafka (introduced in 2015; Wix now runs 6 clusters across GCP and AWS, each holding 10k+ topics, processing "more than 1.5 billion Kafka business events per day").
- **Extensibility.** New consumers subscribe to existing streams with zero changes to producers — Fowler's key advantage of event notification.
- **Real-time processing.** Events are processed as they occur (Confluent's framing in their Kafka 101 materials).
- **Auditability and replay.** A durable, ordered, immutable log is a natural audit trail; with retention/compaction or event sourcing you can rebuild state or reprocess history.

Authoritative sources to cite in any internal proposal: Fowler (above); Gregor Hohpe & Bobby Woolf, *Enterprise Integration Patterns* (Addison-Wesley, 2003) — the 65-pattern messaging canon (Event Message vs. Command Message, Publish-Subscribe Channel, Guaranteed Delivery, Dead Letter Channel); Chris Richardson, *Microservices Patterns* (Manning, 2018) and microservices.io; Sam Newman, *Building Microservices* (2nd ed., 2021); and Ben Stopford, *Designing Event-Driven Systems* (O'Reilly/Confluent, 2018, free).

#### The honest tradeoffs and costs
EDA is not free. Be balanced:

- **Eventual consistency.** Once you stop doing synchronous, transactional updates across services, you must accept that the system is only *eventually* consistent. Fowler and Bellemare both stress designing UIs and APIs to expose/absorb this. For an engineer coming from ACID Aurora MySQL transactions, this is the biggest mental shift.
- **Debugging and "no statement of overall behavior."** With choreography, the end-to-end business flow exists nowhere explicitly. Wix's "5 Pitfalls" post and Derek Comartin's analysis both highlight distributed tracing (OpenTelemetry) as essential to recover causal visibility.
- **Message ordering.** Kafka guarantees ordering only within a partition. Preserving per-aggregate order requires careful partition-key design (e.g., key by `orderId`).
- **Delivery semantics: at-least-once vs. exactly-once.** Most brokers, including Kafka by default, give at-least-once delivery — meaning duplicates are possible, so consumers must be idempotent. Kafka offers exactly-once semantics (EOS) via idempotent producers and transactions, but with cost and constraints.
- **Operational complexity / infrastructure overhead.** Running Kafka (or even managed MSK/Confluent Cloud), Kafka Connect, Debezium, schema registry, and the associated monitoring is a real platform investment.
- **Schema evolution.** Events are contracts. You need a schema registry and disciplined forward/backward compatibility.

---

### PART 2 — GRADUAL INTRODUCTION (one running example throughout)

**The running example: an e-commerce order system.** Initial synchronous design:

```
Client → OrderService.placeOrder()
            ├─(sync REST)→ PaymentService.charge()
            ├─(sync REST)→ InventoryService.reserve()
            ├─(sync REST)→ ShippingService.schedule()
            └─(sync REST)→ NotificationService.email()
```

All in one blocking call chain, with `OrderService` writing to its Aurora MySQL `orders` table. We'll evolve this incrementally — no big-bang rewrite, consistent with Newman's "incremental migration / the monolith is rarely the enemy" guidance.

#### Step 0 — Strangler Fig around the boundary
Per Newman's *Building Microservices* (Ch. 3, "Splitting the Monolith") and Fowler's strangler fig pattern, you place a facade so new event-driven behavior can grow alongside the existing synchronous behavior, routing a slice of functionality to the new path while the old path keeps running. You never stop the old system until the new one demonstrably works. This de-risks the migration and makes it reversible.

#### Step 1 — Emit ONE event, solving the dual-write problem first
Start with the *single* most valuable event: `OrderPlaced`. The naïve implementation — write the order row to MySQL, then call `kafkaTemplate.send(...)` — is the **dual-write problem**. As Gunnar Morling puts it in the canonical Debezium post "Reliable Microservices Data Exchange With the Outbox Pattern" (debezium.io, Feb 19, 2019): *"we cannot have one shared transaction that would span the service's database as well as Apache Kafka, as the latter doesn't support to be enlisted in distributed (XA) transactions."* If the process crashes between the DB commit and the Kafka send (or vice versa), you get silent inconsistency: an order exists with no event, or an event with no order.

The canonical fix is the **Transactional Outbox pattern** (Chris Richardson, microservices.io, and *Microservices Patterns*). Within the *same local ACID transaction* that inserts the order, you also insert a row into an `outbox` table. A separate relay then publishes outbox rows to Kafka. This makes the state change and the intent-to-publish atomic, because they share one MySQL transaction.

The two leading relay options:
- **Transaction log tailing / CDC** (Richardson's "Transaction Log Tailing" pattern): Debezium reads the MySQL binlog and publishes outbox inserts to Kafka. Debezium ships a purpose-built **Outbox Event Router** SMT (Single Message Transform) that routes outbox rows to topics like `outbox.event.order`, keyed by `aggregateid`. This is ideal for your Aurora MySQL + Kafka stack (Debezium's MySQL connector applies directly).
- **Polling publisher**: a scheduled job polls unpublished outbox rows. Simpler, but higher latency and more DB load.

**Kotlin/Spring-specific shortcut:** Spring Modulith's event externalization implements an outbox-backed `EventPublicationRegistry` that — per the Spring Modulith docs — guarantees at-least-once delivery even when broker interactions fail, persisting events to an `event_publication` table and resubmitting on failure. You annotate a domain event `@Externalized("orders.OrderPlaced::#{orderId()}")`, publish it via Spring's `ApplicationEventPublisher` inside the transaction, and Modulith forwards it to Kafka. This is the lowest-friction production-grade outbox for a Spring Boot team. (Add `spring-modulith-events-api` + `spring-modulith-events-kafka`.)

After Step 1, the order flow still does its synchronous calls — but now also reliably emits `OrderPlaced`. The fraud-analytics team can subscribe immediately, with zero changes to `OrderService`. That single capability often justifies the whole effort.

#### Step 2 — Why NOT dual writes (make the failure modes explicit)
State to the team exactly why "just send to Kafka after committing" is rejected: there is no atomicity, no ordering guarantee across the two systems, and crash windows produce lost or phantom events. Richardson's microservices.io calls the casual approach the "do you feel lucky today" anti-pattern. The outbox is not optional for reliable producers.

#### Step 3 — Convert downstream steps to event consumers
Now incrementally peel off downstream calls. Instead of `OrderService` synchronously calling `PaymentService`, `PaymentService` subscribes to `OrderPlaced` and emits `PaymentCompleted` (or `PaymentFailed`). Then `InventoryService` subscribes to `PaymentCompleted` and emits `InventoryReserved`; `ShippingService` subscribes to `InventoryReserved` and emits `OrderShipped`; `NotificationService` subscribes throughout. The user's `placeOrder` call now returns as soon as the order is durably recorded and `OrderPlaced` is emitted — latency drops dramatically and the flow tolerates downstream outages.

This is **choreography**: each service reacts to events and emits its own, with no central coordinator.

#### Step 4 — The Saga pattern for distributed transactions
The order flow is now a distributed transaction without 2PC. The **Saga pattern** (Richardson, microservices.io) models it as a sequence of local transactions, each emitting an event that triggers the next, with **compensating transactions** to roll back on failure (e.g., if `InventoryReserved` fails after `PaymentCompleted`, emit a compensation that refunds the payment).

**Choreography vs. Orchestration** — the key design choice:
- **Choreographed saga**: decentralized; each service listens and reacts. Pros: loose coupling, easy to add participants, natural for event-centric domains like e-commerce. Cons: Fowler's "no overall statement of behavior" — the flow is implicit and hard to follow; answering "is this order stuck?" is hard. Richardson notes you typically know a choreographed saga is done only because the last step published a terminal event (`OrderApproved`/`OrderRejected`).
- **Orchestrated saga**: a central `OrderSaga` orchestrator sends commands and awaits replies. Pros: explicit, centralized flow; simpler dependencies (the orchestrator drives everyone, so no cyclic dependencies); easier to reason about and monitor. Cons: the orchestrator is another component, and you risk concentrating business logic.

Practical recommendation: use **choreography for simple, few-step flows**; switch to **orchestration once the flow exceeds ~3–4 steps or needs rollback logic**. On the JVM you can implement orchestration with Eventuate Tram Sagas, or a workflow engine; Spring shops sometimes use a dedicated orchestrator service.

#### Step 5 — CQRS and Event Sourcing as LATER-stage adoptions
Only after the event backbone is solid should you consider these:
- **CQRS** separates the write model from read models. Now that `OrderPlaced`, `PaymentCompleted`, etc. flow through Kafka, you can build a denormalized read model (e.g., an order-status view) by consuming those events — without burdening the write side.
- **Event Sourcing** makes the event log the source of truth: instead of storing current order state, you store the sequence of events and replay them. This gives perfect audit and temporal queries, but is a significant commitment with real complexity (Fowler and Stopford both caution against adopting it casually). Bellemare and Wix both recommend CDC over full event sourcing for most teams as a less risky way to get data consistency.

On the JVM, **Axon Framework** provides first-class CQRS + event sourcing building blocks (aggregates, command/event handlers, projections) with a Spring Boot starter (`axon-spring-boot-starter`), and integrates with Kafka or its own Axon Server. It's the leading JVM/Kotlin option if you commit to full event sourcing.

**End state of the running example:** `placeOrder` durably records the order and emits `OrderPlaced`; payment, inventory, shipping, and notification proceed asynchronously via a saga; a CQRS read model serves order-status queries; and analytics/fraud/data-lake consumers attach freely. The system is loosely coupled, independently scalable, resilient to partial outages, and fully auditable — reached incrementally, with every step independently valuable and reversible.

---

### PART 3 — A GUIDED LEARNING PATH

Sequenced into four progressive stages. All resources verified for accurate title/author/year.

#### Stage 1 — Foundations: events, coupling, distributed-systems reality
- **Martin Fowler, "What do you mean by 'Event-Driven'?"** (martinfowler.com, 2017) + his GOTO 2017 talk "The Many Meanings of Event-Driven Architecture." *Start here.* Free.
- **Sam Newman, *Building Microservices*, 2nd ed.** (O'Reilly, 2021). Coupling/cohesion taxonomy, communication styles, splitting the monolith (strangler fig), workflow/sagas. The conceptual on-ramp.
- **Martin Kleppmann, *Designing Data-Intensive Applications*** (O'Reilly, 2017; **2nd ed. with Chris Riccomini, 2025**). The rigorous backbone — replication, partitioning, consistency models, "The Trouble with Distributed Systems," stream processing. Given your PhD, this is the book that will most reward deep reading.
- **Confluent Developer, "Apache Kafka 101"** (developer.confluent.io, free) for the events-vs-tables mental model.

#### Stage 2 — Messaging systems and Kafka mastery
- **Gwen Shapira, Todd Palino, Rajini Sivaram & Krit Petty, *Kafka: The Definitive Guide*, 2nd ed.** (O'Reilly, 2021). Authoritative: producers/consumers, reliability, exactly-once/transactions, replication protocol, AdminClient.
- **Gregor Hohpe & Bobby Woolf, *Enterprise Integration Patterns*** (Addison-Wesley, 2003). The 65-pattern messaging canon; still the vocabulary everyone uses. Companion site enterpriseintegrationpatterns.com.
- **Stéphane Maarek's Udemy "Apache Kafka Series"** — "Learn Apache Kafka for Beginners v3" (setup updated to Kafka 4.0 in Aug 2025), plus Kafka Streams, Kafka Connect, and Confluent Schema Registry courses. The most widely used hands-on Kafka video training (130,000+ students).
- **Confluent Developer free courses**: "Apache Kafka 101," "Kafka Streams 101," and **"Spring, Kafka, and Event-Driven Microservices"** (with Viktor Gamov — directly relevant to your Spring/Kotlin stack).
- **Spring tooling docs** (for your stack): Spring for Apache Kafka reference; Spring Cloud Stream; **Spring Modulith "Working with Application Events"** (event externalization / outbox).

#### Stage 3 — The patterns: outbox, saga, CQRS, event sourcing
- **Chris Richardson, *Microservices Patterns*** (Manning, 2018; 2nd ed. in MEAP) + **microservices.io** pattern catalog. The definitive reference for Transactional Outbox, Transaction Log Tailing, Saga (choreography & orchestration), API Composition, CQRS, Database-per-Service.
- **Adam Bellemare, *Building Event-Driven Microservices*** (O'Reilly; 1st ed. 2020, **2nd ed. 2025**). Event/stream design, schemas and evolution, state stores, "effectively once" processing, eventual-consistency strategies. Bellemare is a principal technologist at Confluent (formerly Shopify/Flipp).
- **Ben Stopford, *Designing Event-Driven Systems*** (O'Reilly/Confluent, 2018). **Free** from Confluent (confluent.io/resources/ebook/designing-event-driven-systems). Event sourcing, CQRS, "event streams as source of truth," "inside-out databases."
- **Gunnar Morling, "Reliable Microservices Data Exchange With the Outbox Pattern"** (Debezium blog, Feb 19, 2019) — the canonical outbox-via-CDC writeup.
- **Debezium documentation** — the Outbox Event Router SMT (MySQL connector applies directly to your Aurora MySQL).
- **Confluent Developer "Designing Event-Driven Microservices"** course (Wade) and **"Event Sourcing and Event Storage with Apache Kafka"** course (accompanies Stopford's book).
- **For JVM CQRS/ES:** Axon Framework reference docs + Baeldung's "A Guide to the Axon Framework."
- **Company engineering blogs** (real, specific):
  - **Wix Engineering** — Natan Silnitsky's "Event Driven Architecture — 5 Pitfalls to Avoid," "6 Event-Driven Architecture Patterns" (Parts 1 & 2), and "Wix's Journey Into Data Streams." Outstanding, battle-tested, gradual-migration content from a team running EDA across ~2,300 microservices.
  - **Uber Engineering** — "Disaster recovery for multi-region Kafka at Uber," "Building Reliable Reprocessing and Dead Letter Queues with Apache Kafka," and the uForwarder posts. Hard-won lessons at extreme scale (trillions of messages/day).
  - **DoorDash** — the Iguazu real-time event processing platform (Kafka + Flink). Per DoorDash Engineering, they "scaled it to process hundreds of billions of events per day with a 99.99% delivery rate"; architect Allen Wang (InfoQ, QCon Plus 2022) reports end-to-end latency to Snowflake "reduced from a day to just a few minutes."
  - **Netflix Tech Blog**, **LinkedIn Engineering** (Kafka's birthplace), **Confluent blog**.

#### Stage 4 — Advanced distributed-systems theory and formal methods (tailored to your math background)
- **Leslie Lamport's TLA+** — the natural fit for a pure mathematician. Use TLA+/PlusCal to *formally model-check* the very protocols this guide builds: saga compensation correctness, exactly-once vs. at-least-once consumer idempotency, message-ordering invariants, and eventual-consistency convergence.
  - **Hillel Wayne, *Practical TLA+: Planning Driven Development*** (Apress, 2018) — accessible, example-driven (the bank-transfer spec), PlusCal-focused.
  - **Hillel Wayne, learntla.com** — free, modern, comprehensive online guide.
  - **Leslie Lamport, *Specifying Systems*** (free PDF from his site) + his "TLA+ Video Course" — the rigorous primary source, including the underlying temporal logic of actions.
- **Foundational papers** worth reading directly given your background: Lamport's "Time, Clocks, and the Ordering of Events in a Distributed System" (1978); the CAP theorem (Gilbert & Lynch's proof); and the distributed-systems chapters of Kleppmann (DDIA) which cite the primary literature.

---

## Recommendations

**Stage your adoption against concrete thresholds:**

1. **Now (proof of value):** Pick the single highest-value event in your order/domain flow. Implement the **transactional outbox** using **Spring Modulith event externalization** (lowest friction for your stack) or **Debezium's Outbox Event Router** on Aurora MySQL → Kafka. Stand up a schema registry and adopt forward/backward-compatible schemas from day one. *Benchmark to advance:* the outbox reliably delivers with zero lost/phantom events under induced crash testing, and at least one new consumer is attached with no producer change.

2. **Next (decoupling):** Convert downstream synchronous calls (payment, inventory, shipping, notification) into event consumers using a **choreographed saga**. Add **OpenTelemetry distributed tracing before you need it** — this directly mitigates EDA's worst weakness (loss of end-to-end flow visibility). Make every consumer **idempotent** (dedup on event ID), since Kafka is at-least-once by default. *Threshold to change approach:* once the saga exceeds ~3–4 steps or requires non-trivial rollback, **switch that flow to orchestration** (explicit orchestrator) for debuggability.

3. **Later (read/write optimization):** Introduce **CQRS read models** built from the event streams where query load or read/write asymmetry justifies it. *Threshold:* reads materially outnumber writes, or read-model complexity is contaminating the write model.

4. **Only if warranted (event sourcing):** Adopt full event sourcing **only** where audit/temporal-replay requirements are first-class (finance, compliance). Prefer **CDC over event sourcing** otherwise (Wix's and Bellemare's explicit recommendation). On the JVM, evaluate **Axon Framework** before building your own.

5. **Continuous (rigor):** Given your background, **model-check your saga and consistency protocols in TLA+** before implementation. The cost is days; the payoff is catching ordering/compensation/idempotency bugs that are nearly impossible to find in production. This is the single highest-leverage practice available to you specifically.

**Do not:** do a big-bang rewrite; do dual writes; assume exactly-once for free; or adopt event sourcing/CQRS before the event backbone and outbox are solid.

---

## Caveats
- **Edition currency:** *Designing Data-Intensive Applications* and *Building Event-Driven Microservices* both have new 2nd editions (2025); *Microservices Patterns* has a 2nd edition in MEAP (in-progress). Verify which edition you buy.
- **Self-reported metrics, mixed measurement bases.** Company figures are self-reported in engineering-blog talks and mix different bases. DoorDash illustrates this directly: the headline "hundreds of billions of events per day" (raw analytical events, per Allen Wang/InfoQ 2022) is distinct from a later DoorDash post ("API-First Approach to Kafka Topic Creation") reporting the RTSP team "manages over 2,500 Kafka Topics across five clusters" where "Almost six billion messages are processed each day at an average rate of four million messages per minute" — a broker-message basis. Treat all such numbers as directional, not benchmark-grade, and cite the basis.
- **TLA+ scope:** TLA+/PlusCal model-checks *designs*, not your running Kotlin code; it finds logic/protocol bugs, not implementation bugs. It complements, not replaces, testing.
- **"Exactly-once" nuance:** Kafka EOS is exactly-once *within Kafka's processing boundaries* (transactions across topics/consumer offsets); end-to-end exactly-once including external systems still generally requires idempotent consumers. Don't over-promise EOS to stakeholders.
- **Marketing vs. substance:** Confluent's materials are excellent but vendor-produced; the conceptual content is sound, but cross-check product claims against your own (possibly self-managed MSK) constraints.