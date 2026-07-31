---
title: "From Fundamentals to Fluency: A Project-Based Guide to Event-Driven Architecture with Apache Kafka (for a Kotlin/Spring Boot Senior Engineer)"
category: "Data & Messaging"
description: "An 8-phase, 12-14 week project-based path built around one food-delivery capstone (orders → payment → restaurant acceptance → rider dispatch → tracking → notifications) that starts as a synchronous monolith and is deliberately broken apart so every EDA concept and failure mode is met firsthand. It answers the WHEN question head-on, covering temporal decoupling, fan-out, replayable history, and load buffering against staying synchronous for request-scoped answers and read-after-write consistency. It prioritizes primary sources (Fowler's taxonomy, Kreps's 'The Log,' KIP-98/KIP-429, DDIA, the Debezium outbox blog, Spring/Confluent docs) alongside the best Korean engineering blogs (Woowahan, Toss, Kakao Pay) and courses."
---

# From Fundamentals to Fluency: A Project-Based Guide to Event-Driven Architecture with Apache Kafka (for a Kotlin/Spring Boot Senior Engineer)

## TL;DR
- Build one capstone, a food-delivery domain (orders → payment → restaurant acceptance → rider dispatch → tracking → notifications), in 8 phases over 12-14 weeks. Start from a synchronous monolith and deliberately break it, so you meet every EDA concept and failure mode firsthand. This domain is confirmed as the single most instructive choice: it is exactly what Chris Richardson's canonical FTGO reference app and Woowahan's 배민 delivery systems both model.
- The "WHEN" answer: use Kafka and EDA when you need temporal decoupling, fan-out to many independent consumers, replayable audit history, or buffering against load spikes. Stay synchronous (REST or gRPC) when you need a request-scoped answer, strong read-after-write consistency, or when your team and system are small. EDA trades latency and coupling for eventual consistency, duplicate-handling burden, schema governance, and much harder debugging.
- Prioritize primary sources: Martin Fowler's taxonomy, Jay Kreps's "The Log," KIP-98 and KIP-429, Kleppmann's DDIA, the Debezium outbox blog, and the Spring and Confluent official docs. Supplement them with the best Korean engineering blogs (Woowahan, Toss, Kakao Pay) and courses (데브원영, 최원영's book). Most core books and courses here are free.

---

## 1. Conceptual Roadmap / Overview

You already have the mathematical maturity for the hard parts (distributed consensus, ordering as a partial order, idempotence as an algebraic property). What you lack is the *vocabulary map* and the *earned intuition* for the failure modes. This guide front-loads the vocabulary, then forces the intuition through deliberate breakage.

**The four "event-driven" meanings (Fowler's taxonomy, read this first).** Martin Fowler's 2017 article "What do you mean by 'Event-Driven'?" (and the companion GOTO 2017 keynote "The Many Meanings of Event-Driven Architecture") identifies four distinct patterns people conflate:
1. Event notification: a thin message ("something changed"), often just an ID plus a link back. Coupling is low, but the business flow becomes invisible in code, what Fowler calls "the dark side," with no statement of overall behavior. Watch for the anti-pattern of an event used as a "passive-aggressive command."
2. Event-carried state transfer (ECST): the event carries all the data a consumer needs, so consumers keep local replicas and never call back. It improves availability and decoupling at the cost of data duplication and eventual consistency.
3. Event sourcing: the event log is the source of truth, and application state is a derived, rebuildable projection. The test is whether "at any time we can blow away application state and rebuild it from the log." Git and double-entry accounting are examples.
4. CQRS: separate the write model (commands) from the read models (queries).

These are orthogonal building blocks, and a real system mixes them. You should be able to name which one is in play at every phase of the project.

**The unifying abstraction: the log.** Jay Kreps's "The Log: What every software engineer should know about real-time data's unifying abstraction" (LinkedIn Engineering) is the conceptual keystone. A log is an append-only, totally-ordered sequence. Kreps's key insight is the log/table duality and the reduction of N² point-to-point integrations to 2N via a central log. This is why Kafka exists, and why it is a log rather than a queue.

**Messaging fundamentals: queues vs. logs.** A traditional broker (RabbitMQ, ActiveMQ, SQS) deletes a message once consumed (point-to-point) or fans out via exchanges and topics (pub-sub). Kafka retains messages on disk for a configured retention period and lets many independent consumer groups read at their own offset. This retention and replayability is the single most important mental distinction. As a rule of thumb:
- RabbitMQ and SQS: per-message routing, complex delivery semantics, TTLs, priority, competing-consumer work queues, low-to-moderate throughput.
- Kafka: high-throughput, ordered, replayable event streams; multiple independent consumers; stream processing; an event-sourcing backbone.

**Kafka core concepts** (topics, partitions, offsets, consumer groups, brokers, replication, ISR, KRaft, retention, compaction) are best covered via *Kafka: The Definitive Guide* 2nd ed. (free from Confluent) and Confluent Developer's Kafka 101. The rigor points that matter: ordering is guaranteed only within a partition; the partition key determines the ordering domain; a partition is consumed by at most one consumer in a group, so parallelism is capped at the partition count; and compaction retains the latest value per key, which is a materialized log/table.

**Delivery semantics.** At-most-once (fire and forget), at-least-once (the default, where retries cause duplicates), and exactly-once. The primary sources are KIP-98 (the idempotent producer via PID plus sequence number, and transactions for atomic multi-partition writes) and KIP-185 (idempotence and EOS defaults). One critical nuance from KIP-98's own text: durability guarantees only hold for replication-factor 2 or higher and in the absence of concurrent hard failures. "Exactly-once" is really "effectively-once," and only end-to-end within Kafka (consume-transform-produce with `read_committed`). Writes to an external DB inside a consumer are not covered, which is why the outbox and idempotent-consumer patterns exist.

**Ordering, partitioning, rebalancing, lag.** Cover cooperative and incremental rebalancing (KIP-429, `CooperativeStickyAssignor`, Kafka 2.4+) against the old eager "stop-the-world" protocol, plus static membership (KIP-345) and consumer lag as the core health metric. The next-generation server-side protocol, KIP-848, first appeared as early access in Kafka 3.7; note it, but don't build on it yet.

**Schema and evolution.** Avro, Protobuf, or JSON Schema with the Confluent Schema Registry, plus compatibility modes (BACKWARD, FORWARD, FULL). Avro is the default in the Kafka ecosystem.

**Reliability patterns.** Idempotent consumers (an inbox or dedup table), retries with backoff, dead-letter topics, poison pills, the dual-write problem, the transactional outbox with Debezium CDC (the Outbox Event Router SMT), and the inbox pattern.

**Distributed data patterns.** Sagas (choreography vs. orchestration, plus compensating transactions), CQRS, event sourcing, and eventual consistency. Primary source: Chris Richardson's microservices.io catalog and his *Microservices Patterns* book.

**Spring-specific ladder.** In-process `ApplicationEventPublisher` with `@TransactionalEventListener(phase = AFTER_COMMIT)` → Spring Modulith externalized events (`@Externalized`, where the Event Publication Registry is a built-in outbox) → Spring for Apache Kafka (`KafkaTemplate`, `@KafkaListener`, `DefaultErrorHandler`, `DeadLetterPublishingRecoverer`, `@RetryableTopic` non-blocking retries) → Spring Cloud Stream (the binder abstraction, with its own tradeoffs).

---

## 2. The "WHEN" Decision Framework (with Case Studies)

This is the crux of the request. EDA is a tool with a specific cost/benefit profile, not a maturity level to graduate to.

### 2.1 Decision criteria: use EDA and Kafka when the answer is "yes" to several

| Dimension | Favors EDA/Kafka | Favors synchronous REST/gRPC |
|---|---|---|
| Temporal coupling | Producer must not block on consumer availability; consumer can be down and catch up | Caller needs the result *now* to proceed |
| Behavioral coupling | Producer shouldn't know who reacts; new consumers added without touching producer | Fixed, known collaborator; simple call |
| Fan-out | One event → many independent reactions (notify, analytics, projection, audit) | One request → one response |
| Scalability / load buffering | Spiky load; want a durable buffer to smooth bursts | Steady, low volume |
| Audit / replay | Need immutable history; ability to rebuild state or reprocess | No audit need |
| Workflow complexity | Long-running, multi-step business processes (sagas) | Single atomic operation |
| Consistency | Eventual consistency acceptable | Strong read-after-write required |

### 2.2 When not to use Kafka or EDA
- Request-response needs, where a user is waiting for a synchronous answer such as pricing, an auth check, or validation.
- Small systems and small teams. Kafka's operational and cognitive overhead (schema governance, lag monitoring, duplicate handling, partition sizing) is not worth it for a handful of services. Note Kai Waehner's advice via Uber and Wix: "Don't (try to) solve a problem that you do NOT have yet."
- Strong consistency requirements, such as financial invariants that must hold synchronously within one transaction boundary.
- Team maturity cost. Debugging async flows requires distributed tracing across broker hops, which most teams underestimate.

### 2.3 The tradeoffs you are buying
Eventual consistency; debugging and observability complexity (Fowler's "no statement of overall behavior"); duplicate-handling burden, since at-least-once is the realistic default; schema governance overhead; out-of-order delivery.

### 2.4 Case studies: adoption stories (concrete, sourced)

**Woowa Brothers (배달의민족 / Woowahan), the anchor case for this learner.** Their monolith hit "the great outage era" (대장애 시대) as order volume grew on a J-curve, and they completed a full microservices split on November 1, 2019, adopting event-driven architecture. Two must-read posts:
- *"회원시스템 이벤트기반 아키텍처 구축하기"* (Building the member system's event-based architecture, techblog.woowahan.com/7835) shows the event-notification-versus-command distinction, the SNS-SQS layering, and, crucially, the honest admission that the app-to-SNS hop over HTTP inside a transaction means a messaging-system failure becomes a system failure. That is the dual-write problem, unsolved at that stage.
- *"우리 팀은 카프카를 어떻게 사용하고 있을까"* (How our team uses Kafka, techblog.woowahan.com/17386) covers the delivery domain (100만+ deliveries/day) using Kafka as an event broker, with a Transactional Outbox Pattern via MySQL source connector to guarantee ordering and no message loss. That is essentially your Phase 3-4 target, from a Korean company in your exact domain. It explicitly motivates ordering with the "배차완료 vs. 픽업준비요청 arriving out of order" scenario.

**Toss / 토스증권 (SLASH conference and toss.tech).** Two concrete stories. First, SLASH 22's "애플 한 주가 고객에게 전달되기까지" explains how a broker-mediated overseas stock order is processed safely: a 체결 수신 서버 persists broker receipts to the DB before producing to Kafka, which enables failover to polling mode with no message loss, and it issues a global unique ID for dedup across broker partners. Second, toss.tech's 3-part "토스증권 Apache Kafka 데이터센터 이중화" and SLASH23's "Kafka 이중화로 다양한 장애 상황 완벽 대처하기" cover Active-Active multi-IDC Kafka, bidirectional data mirroring, and consumer-group offset sync. They rejected stretch clusters because of split-brain risk on network partition and cross-DC latency.

**Kakao Pay (if(kakao) 2024, tech.kakaopay.com).** "지연이체 서비스 개발기" (delayed transfer) is a great "when to migrate brokers" story. They were forced from RabbitMQ to company-standard Kafka and had to solve duplicate execution (the same transfer produced twice) with state-checking and idempotency. It illustrates that Kafka is not always the natural fit for delay-queue semantics, since RabbitMQ's native delay and requeue was easier. Their initial config: one `transfer-delay` topic, 3 partitions, 2 consumers.

**International (figures corrected against primary sources):**
- LinkedIn, Kafka's birthplace, moved from N×N end-to-end integration to a central log. Per the LinkedIn Engineering post "How LinkedIn customizes Apache Kafka for 7 trillion messages per day": "more than 100 Kafka clusters with more than 4,000 servers (called brokers), handling over 100,000 topics and 7 million partitions … more than 7 trillion messages every day," with "each message … consumed by approximately four applications on average." That is a direct empirical illustration of Kreps's N²→2N argument.
- Uber adopted Kafka in early 2015. Per Uber Engineering, "Uber has one of the largest deployments of Apache Kafka in the world, processing trillions of messages and multiple petabytes of data per day … we position Apache Kafka as a cornerstone of our technology stack." Throughput grew "from roughly one million to twelve million messages per second over five years." They built uReplicator, Chaperone, and uForwarder, a push-based consumer proxy that per Uber's "Introducing uForwarder" has "over 1,000 consumer services onboarded" and is "the primary option for reading data from Kafka in pub-sub use cases at Uber," plus tiered storage (KIP-405). Uber's "Building Reliable Reprocessing and Dead Letter Queues with Apache Kafka" is the canonical primary reference for Phase 4's retry and DLT design.
- Wix, per Natan Silnitsky (Wix, Kafka Summit London, April 2022): "2,200+ services, 50,000 topics, and 500,000+ partitions, handling 15 billion business events per day" (roughly 66 billion total daily messages including infra traffic). His more recent figures (natansil.com, GOTO 2023) cite roughly 4,000 microservices in production and about 70 billion Kafka messages per day. His talks and posts ("6 Event-Driven Architecture Patterns" parts 1 and 2, "Lessons Learned from 2000 Event-Driven Microservices") are the best catalog of practical patterns and of pitfalls: producing-message failure, fixed by making the DB update and event atomic; out-of-order and duplicate processing; large payloads, fixed by producing to S3 and passing a reference. Their open-source Greyhound wraps Kafka clients with retry policies.

The pattern across all of them: they adopted EDA to break temporal and behavioral coupling at scale and to get replayable buffers, and every one of them independently had to solve the dual-write problem (outbox/CDC), duplicate handling (idempotency), and retry/DLT.

---

## 3. The Capstone Project: "DeliverEDA", a food-delivery platform in 8 phases

**Domain (confirmed as most instructive):** orders, payments, restaurant acceptance, rider dispatch, delivery tracking, notifications. Both FTGO (Richardson's book reference app) and Woowahan's real delivery systems validate this choice, and it naturally forces every concept: a multi-step workflow (saga), fan-out (notifications, analytics, tracking), ordering (delivery state transitions), state projection (the tracking read model), and money, which is a place where duplicates and consistency actually hurt and where the lessons therefore land.

**Stack:** Kotlin, Spring Boot 3.x, Aurora MySQL, Apache Kafka, Testcontainers, EKS. Deploy Kafka via Strimzi (self-managed on EKS) and/or AWS MSK in Phase 7.

**Overall timeline (senior engineer, part-time at roughly 8-10 hrs/week): 12-14 weeks.** Phases scale in difficulty, and Phases 3 through 5 are the heart of it and deserve the most time.

---

### Phase 0: the synchronous monolith (week 1)
**Objective:** feel the pain of temporal coupling firsthand before "fixing" anything.
**Build:** a modular monolith (or a few services) where `OrderService` synchronously REST-calls `PaymentService` → `RestaurantService` → `DispatchService` → `NotificationService` in one request thread. Aurora MySQL, single transaction where possible.
**Failure experiments:**
- Add 2s latency to `NotificationService` and observe the entire order-placement p99 balloon (latency chains).
- Kill `DispatchService` and observe the whole order flow fail even though the order and payment are logically fine (cascading failure, temporal coupling).
- Measure what percentage of the critical path is actually critical.
**Deliverable:** a latency and coupling write-up quantifying the pain. **Resources:** Fowler's taxonomy, Richardson's "coupling" articles, DDIA ch. 1.
**Time:** ~1 week.

### Phase 1: in-process decoupling with Spring application events (week 2)
**Objective:** learn that "events" start in-process, and meet the `AFTER_COMMIT` pitfall.
**Build:** replace the synchronous notification and analytics calls with `ApplicationEventPublisher` plus `@TransactionalEventListener(phase = AFTER_COMMIT)`. Keep payment synchronous, since it's on the critical path.
**Failure experiments:**
- Use the default `@EventListener` (which runs inside the transaction) and throw in the listener, then watch it roll back the order. Then switch to `AFTER_COMMIT`.
- With `AFTER_COMMIT`, crash the JVM between commit and listener execution, and observe that the event is lost, since there is no durability. This is the motivating failure for the outbox pattern.
**Deliverable:** notes on synchronous vs. AFTER_COMMIT vs. AFTER_COMPLETION semantics and why in-process events don't survive crashes.
**Resources:** Spring docs on `@TransactionalEventListener`; the Spring Modulith intro. **Time:** ~1 week.

### Phase 2: extract to Kafka with a naïve dual-write (weeks 3-4)
**Objective:** deliberately experience the dual-write problem and message loss.
**Build:** introduce Kafka (locally via Testcontainers or Docker Compose). In `OrderService`, after committing to Aurora, call `kafkaTemplate.send(...)`. Stand up separate consumer services (payment, notification) with `@KafkaListener`.
**Failure experiments (the whole point):**
- Kill the app between the DB commit and the Kafka send. The order exists in the DB, no event lands on the topic, and downstream never happens. This is the dual-write problem, made real.
- Reverse the order (send to Kafka first, then commit) and roll back the DB, producing a phantom event where downstream acts on an order that doesn't exist.
- Set `acks=0` and induce a broker blip to get silent message loss. Then set `acks=all` with `enable.idempotence=true` and compare.
**Deliverable:** a reproduction of both dual-write failure directions with logs.
**Resources:** KIP-98 (delivery semantics); the Confluent "Message Delivery Guarantees" doc; the Woowahan 회원시스템 post, since they hit exactly this. **Time:** ~2 weeks.

### Phase 3: transactional outbox, Debezium CDC, and Schema Registry (weeks 5-6)
**Objective:** solve the dual-write problem correctly, and introduce schemas.
**Build:** add an `outbox` table written in the same Aurora transaction as the business change. Run Debezium (Kafka Connect) against the Aurora binlog with the Outbox Event Router SMT to route rows to per-aggregate topics, where the aggregate ID becomes the Kafka key and preserves per-entity ordering. Introduce Confluent Schema Registry with Avro, and set BACKWARD compatibility.
**Alternative to compare:** Spring Modulith's Event Publication Registry (`@Externalized`) as an application-level outbox. Implement one event both ways and contrast CDC/log-tailing against polling-publisher.
**Failure experiments:**
- Repeat Phase 2's kill-between-commit-and-send experiment. Now the event survives, because it's in the DB, and Debezium publishes after the commit. Confirm zero loss.
- Make a breaking schema change (remove a required field) and watch Schema Registry reject it under BACKWARD compatibility.
**Deliverable:** a working outbox and CDC pipeline, plus a short proof of why it eliminates the dual-write, since the event and business row commit atomically.
**Resources:** Debezium's "Reliable Microservices Data Exchange With the Outbox Pattern" (Gunnar Morling) and the Outbox Event Router docs; debezium-examples/outbox; the Woowahan 카프카 post (MySQL source connector outbox); rkudryashov/event-driven-architecture (Kotlin, Spring Boot 3, outbox + inbox + Debezium). **Time:** ~2 weeks.

### Phase 4: consumer-side reliability, meaning idempotency, retries, DLT, rebalancing (weeks 7-8)
**Objective:** survive at-least-once delivery and consumer failures.
**Build:**
- Make consumers idempotent via an inbox or dedup table keyed on event ID, since payment must never double-charge.
- Configure `DefaultErrorHandler` with `DeadLetterPublishingRecoverer`, then switch to non-blocking retries with `@RetryableTopic` (retry topics with exponential backoff plus a DLT). Add a `@DltHandler`.
- Configure `CooperativeStickyAssignor`.
**Failure experiments:**
- Publish a poison pill (undeserializable or business-invalid) and observe blocking retry stalling the partition, then fix it with non-blocking retry topics.
- Replay the same event three times to prove idempotency prevents double side-effects.
- Scale consumers from 2 to 4 under load and kill one mid-batch. Observe the rebalance, and contrast eager against cooperative-sticky pause time and duplicate reprocessing of the in-flight batch.
- Measure consumer lag during the storm.
**Deliverable:** idempotent, retrying, DLT-backed consumers plus a rebalancing observation log.
**Resources:** Spring Kafka non-blocking retries and error-handling docs; Uber's "Reliable Reprocessing and Dead Letter Queues"; KIP-429; Confluent's "Incremental Cooperative Rebalancing." **Time:** ~2 weeks.

### Phase 5: sagas for the order/payment workflow (weeks 9-10)
**Objective:** coordinate a long-running, multi-step transaction with compensations, and compare choreography with orchestration.
**Build:** implement the Create-Order saga: reserve payment → restaurant accept → assign rider → confirm. Implement both styles:
- Choreography, where services react to each other's events. Feel the "no statement of overall behavior" problem when you try to answer "why is this order stuck?"
- Orchestration, where a central `OrderSaga` orchestrator issues commands and tracks state. Feel both the clarity and the central-coupling cost.
Add compensating transactions: refund the payment if the restaurant rejects, and cancel dispatch if payment fails.
**Failure experiments:**
- Fail restaurant acceptance after payment is reserved, trigger compensation (refund), and verify no money is stuck.
- Introduce a duplicate command and verify saga idempotency and countermeasures, given the lack of isolation between saga steps.
**Deliverable:** both saga styles plus a decision memo on when you'd choose each.
**Resources:** Richardson's microservices.io saga pattern and "A tour of two sagas" (2024); *Microservices Patterns* ch. 4-5; FTGO (orchestration) and eventuate-tram examples (both styles); idugalic/digital-restaurant (Kotlin/Axon, saga + ES + CQRS). **Time:** ~2 weeks.

### Phase 6: CQRS read model and ECST for delivery tracking (week 11)
**Objective:** build a query-optimized projection from the event stream.
**Build:** a `DeliveryTracking` read model updated by a projector consuming delivery events, using ECST so the events carry state. Optionally use Kafka Streams (or a simple Kotlin projector) to build a materialized view of live delivery status. Expose a fast read API that never calls the write services.
**Failure experiments:**
- Kill the projector, let events pile up, and restart it to watch it catch up (replay). Then blow away the read store entirely and rebuild from the log, which is the event-sourcing test.
- Introduce an out-of-order delivery-state event, observe an incorrect projected state, and fix it with ordering-by-key or version checks.
**Deliverable:** a rebuildable read model plus a demonstration of replay.
**Resources:** Fowler on CQRS and ECST; Stopford's *Designing Event-Driven Systems* (free); the Wix "consume and project" pattern; the Confluent Kafka Streams course. **Time:** ~1 week.

### Phase 7: operations, meaning Kubernetes, observability, chaos, and load (weeks 12-13)
**Objective:** run it like production.
**Build:**
- Deploy Kafka on EKS via Strimzi (KRaft mode, node pools), then stand up an AWS MSK cluster and compare operational models. Cookpad's "Managing Kafka with Strimzi" documents a real migration from Confluent Cloud to Strimzi on EKS and the "more control vs. more ops burden" tradeoff.
- Observability: consumer-lag monitoring (Kafka exporter plus Prometheus plus Grafana, or Burrow), and distributed tracing across async hops with OpenTelemetry, propagating trace context through Kafka headers.
- Schema Registry in-cluster.
**Failure and chaos experiments:**
- Kill a broker and observe ISR shrink, leader election, and producer behavior with `acks=all` against `acks=1`.
- Kill a consumer mid-processing to see rebalance plus at-least-once redelivery.
- Load-test to find the partition-count ceiling, then resize partitions and observe the key-ordering implications.
**Deliverable:** a running EKS deployment, dashboards, a chaos and load report, and an MSK-versus-Strimzi decision memo.
**Resources:** Strimzi docs; AWS MSK vs self-managed comparisons; *Kafka: The Definitive Guide* ch. 9-10 (admin and monitoring); Toss's "Apache Kafka 데이터센터 이중화" (multi-IDC ops); Cookpad's "Managing Kafka with Strimzi." **Time:** ~2 weeks.

### Phase 8 (capstone wrap): write the architecture decision records (week 14)
For each phase, document the ADR: what the problem was, what you tried, what broke, what you chose, and the threshold that would change the decision. This is the artifact that proves you understand *when*, not just *how*.

---

## 4. Curated Resource Library

*Free = no cost; Paid = purchase; language marked EN/KO.*

### 4.1 Foundational articles and papers (all free, EN)
- Martin Fowler, "What do you mean by 'Event-Driven'?" (martinfowler.com, 2017), the taxonomy. Start here, and pair it with the GOTO 2017 keynote video "The Many Meanings of Event-Driven Architecture."
- Jay Kreps, "The Log: What every software engineer should know…" (LinkedIn Engineering), the conceptual keystone, covering the log/table duality and the N²→2N argument.
- KIP-98 (Exactly-Once Delivery and Transactional Messaging), the primary source for the idempotent producer and transactions. Pair it with KIP-185 (EOS defaults) and Confluent's "Message Delivery Guarantees" doc.
- KIP-429 (Consumer Incremental Rebalance Protocol) plus the Confluent blog post "Incremental Cooperative Rebalancing in Apache Kafka", for rebalancing rigor.
- The Debezium blog post "Reliable Microservices Data Exchange With the Outbox Pattern" (Gunnar Morling, 2019), the outbox primary source.
- Chris Richardson, microservices.io, a pattern catalog covering Saga, Transactional Outbox, CQRS, API Composition, and Transaction Log Tailing, plus "A tour of two sagas" (2024).

### 4.2 Books
- *Designing Data-Intensive Applications*, Kleppmann (O'Reilly). Paid, EN. The rigorous foundation covering replication, consistency, logs, and stream processing. It is the best match for a mathematician, and ch. 11 (stream processing) is essential. A Korean translation exists: *데이터 중심 애플리케이션 설계*.
- *Kafka: The Definitive Guide*, 2nd ed., Shapira/Palino/Sivaram/Petty. Free from Confluent as a PDF, EN. The Kafka reference, covering internals, reliability, admin, and monitoring.
- *Designing Event-Driven Systems*, Ben Stopford. Free from Confluent as a PDF, EN. Concise EDA and Kafka patterns (event sourcing, CQRS, the "inside-out database").
- *Microservices Patterns*, Chris Richardson (Manning). Paid, EN. Saga, outbox, and CQRS with FTGO. Korean translation: *마이크로서비스 패턴*.
- *Building Event-Driven Microservices*, Adam Bellemare (O'Reilly). Paid, EN. Event-first data, schemas, and streams.
- *Enterprise Integration Patterns*, Hohpe & Woolf. Paid, EN. The messaging-patterns canon, and still the vocabulary source.
- Korean books: *카프카 핵심 가이드* (the Korean translation of Kafka: The Definitive Guide, 제이펍); *아파치 카프카 애플리케이션 프로그래밍 with 자바*, 최원영/데브원영, the standard Korean Kafka dev book; *실전 카프카 개발부터 운영까지*; *실시간 데이터 파이프라인 아키텍처* (데브원영). Paid, KO.

### 4.3 Video courses
- Confluent Developer (developer.confluent.io/courses). Free, EN. Kafka 101, Spring Framework and Apache Kafka (hands-on with Spring Boot), Event Sourcing, Schema Registry, Kafka Streams, Microservices. The best free structured path, and it maps directly onto Phases 3 through 6.
- Stephane Maarek's Kafka series (Udemy). Paid, EN. "Apache Kafka for Beginners," plus consumer/producer, Connect, Streams, and CCDAK exam prep. A comprehensive practical baseline.
- 데브원영 (인프런): "[데브원영] 아파치 카프카 for beginners". Free, KO, the same as his YouTube material. Then "[아파치 카프카 애플리케이션 프로그래밍] 개념부터 컨슈머, 프로듀서, 커넥트, 스트림즈까지!". Paid (₩165,000), KO, 13h13m, 105 lessons; good CCDAK prep.
- 권철민 (인프런) "카프카 완벽 가이드" series (Core, ksqlDB, Connect). Paid, KO. Deep operational coverage.
- The 데브원영 YouTube channel. Free, KO. Ongoing Kafka content.

### 4.4 Conference talks
- Martin Fowler, GOTO 2017, "The Many Meanings of Event-Driven Architecture". Free, EN.
- Natan Silnitsky (Wix): "Lessons Learned from 2000 Event-Driven Microservices" (DevSum and others) plus the Confluent podcast "Using Kafka as the Event-Driven System for 1,500 Microservices at Wix". Free, EN. The best pitfalls catalog.
- Kafka Summit and Current talks (Confluent). Free, EN. Exactly-once, sagas, and outbox at scale.
- 우아콘 (WOOWACON): 김영한's "배달의민족 마이크로서비스 여행기" (우아콘2020). Free, KO. The MSA migration story, plus Woowahan sessions on 정산 and 이벤트 아키텍처.
- Toss SLASH: SLASH22's "애플 한 주가 고객에게 전달되기까지" and SLASH23's "Kafka 이중화로 다양한 장애 상황 완벽 대처하기". Free, KO.
- if(kakao): the Kakao Pay 지연이체 (2024) session. Free, KO.
- DEVIEW (Naver/LINE) Kafka sessions. Free, KO.

### 4.5 Key engineering blog posts
- Woowahan (KO): "회원시스템 이벤트기반 아키텍처 구축하기" (/7835) and "우리 팀은 카프카를 어떻게 사용하고 있을까" (/17386, delivery plus outbox via MySQL source connector). These are the anchor posts for your domain.
- Toss (KO): toss.tech's "토스증권 Apache Kafka 데이터센터 이중화" (3-part, Active-Active mirroring plus offset sync).
- Kakao Pay (KO): tech.kakaopay.com's "지연이체 서비스 개발기" (if(kakao)2024).
- 여기어때 (KO): "Apache Kafka를 사용하여 EDA 적용하기."
- 29CM / Greg Lee (KO): "Apache Kafka 간략하게 살펴보기", based on 카프카 핵심 가이드, which notes that 29CM has used Kafka actively since 2021.
- Uber (EN): "Building Reliable Reprocessing and Dead Letter Queues with Apache Kafka", plus the uForwarder and tiered-storage posts.
- Wix (EN): Natan Silnitsky's "6 Event-Driven Architecture Patterns" parts 1 and 2.
- Confluent (EN): Jay Kreps's exactly-once posts, and "Incremental Cooperative Rebalancing."
- Spring (EN): "Simplified Event Externalization with Spring Modulith" (spring.io/blog).

### 4.6 GitHub reference repositories (all verified reachable, July 2026)
- microservices-patterns/ftgo-application (Java). The canonical food-delivery reference from *Microservices Patterns*, with orchestration sagas, CQRS, and outbox on MySQL plus Kafka. Actively maintained, and the twin of your domain.
- eventuate-tram/eventuate-tram-sagas-examples-customers-and-orders (~564★, Java). Orchestration sagas via Eventuate Tram CDC. Companion repo: eventuate-tram-examples-customers-and-orders (choreography plus CQRS).
- debezium/debezium-examples, the `/outbox` directory (Java/Quarkus). The authoritative transactional-outbox-via-CDC demo with an idempotent consumer and OpenTelemetry. Actively maintained.
- spring-projects/spring-modulith, `/spring-modulith-examples` including `spring-modulith-example-kafka` (Java). Event externalization to Kafka via `@Externalized`, and the built-in outbox (Event Publication Registry). Very active.
- spring-projects/spring-kafka, the `samples` module (Java). Canonical Spring for Apache Kafka usage. Active.
- rkudryashov/event-driven-architecture (Kotlin, Spring Boot 3, JDK 21). The best modern Kotlin match: Transactional Outbox plus Inbox plus Saga with Kafka Connect/Debezium, CloudEvents, and PostgreSQL. Documented in a 2024 blog post. Start here for Kotlin idioms.
- idugalic/digital-restaurant (319★, Kotlin/Axon). DDD, event sourcing, CQRS, and sagas across monolith and microservices. Architecturally excellent but dependency-dated, since the last major work was around 2018.
- thecodemonkey/kafka-microservices (Kotlin and Java). Incremental examples covering pub/sub, Streams, CQRS, event sourcing, and a minimal saga. Good step by step.
- confluentinc/cp-demo, an end-to-end Confluent Platform demo (Kafka, ksqlDB, Schema Registry, security). Active.
- Java pattern references: piomin/sample-spring-kafka-microservices (saga via Kafka Streams) and uuhnaut69/saga-pattern-microservices (saga plus outbox via Debezium). Both are Java, not Kotlin.
- One flag: confluentinc/kafka-streams-examples is now in maintenance and superseded mode, replaced by "Confluent Tutorials for Apache Kafka", though it is still reachable.

---

## 5. Realistic Timeline and Study Cadence

| Phase | Focus | Weeks | Cumulative |
|---|---|---|---|
| 0 | Synchronous monolith + pain | 1 | Wk 1 |
| 1 | In-process events, AFTER_COMMIT | 1 | Wk 2 |
| 2 | Naïve dual-write + loss | 2 | Wk 4 |
| 3 | Outbox + Debezium CDC + Avro/Registry | 2 | Wk 6 |
| 4 | Idempotency, retries, DLT, rebalancing | 2 | Wk 8 |
| 5 | Sagas (choreography vs. orchestration) | 2 | Wk 10 |
| 6 | CQRS read model / ECST + Streams | 1 | Wk 11 |
| 7 | K8s (Strimzi/MSK), observability, chaos | 2 | Wk 13 |
| 8 | ADR write-up | 1 | Wk 14 |

**Total: 12-14 weeks part-time**, which compresses to roughly 7-8 weeks full-time. Phases 3 through 5 are the intellectual core, so do not rush them.

**Suggested weekly rhythm:** about 2 hrs reading primary sources, about 5 hrs building and breaking, and about 1 hr writing the phase ADR. The writing is not optional, because it's where "when" intuition consolidates.

---

## 6. Recommendations (staged, with thresholds)

1. Weeks 1-2 (foundation), read before you build. Fowler's taxonomy, Kreps's "The Log," and DDIA ch. 11. Do Confluent's Kafka 101 and 데브원영's free course in parallel for bilingual reinforcement. *Threshold to proceed:* you can, unprompted, classify any messaging design as notification, ECST, event sourcing, or CQRS, and state its coupling tradeoff.

2. Weeks 3-8 (the core loop), build the failures rather than just the features. The single highest-leverage activity is Phase 2 into Phase 3: reproduce the dual-write loss, then fix it with the outbox. If you only had 3 weeks total, do Phases 0, 2, and 3. *Threshold:* you can prove, on a whiteboard, why the outbox eliminates the dual-write and why "exactly-once" is really "effectively-once within Kafka."

3. Weeks 9-11 (distributed data), implement both saga styles. Reading about choreography versus orchestration isn't enough; feel the "where is my flow?" pain of choreography and the central-coupling cost of orchestration. *Threshold:* you can write the decision memo on which to use and when, and you've triggered a real compensating transaction.

4. Weeks 12-14 (production reality), run it on EKS and break the brokers. *Threshold:* you can read a consumer-lag dashboard, trace an event across an async hop, and articulate the MSK-versus-Strimzi tradeoffs for your team.

5. Throughout, apply the "WHEN" gate ruthlessly. For every event you introduce, ask whether this needs decoupling, fan-out, replay, or buffering, or whether you are adding eventual consistency and duplicate-handling for nothing. Keep payment authorization synchronous deliberately, to internalize that EDA is a tool rather than a religion.

**Metrics that should change your decisions:**
- If duplicate-handling and schema-governance overhead exceed the coupling pain they solve, you over-adopted EDA; pull some flows back to synchronous.
- If a single consumer group can't keep up and lag grows unbounded, revisit partition count and key design (parallelism is capped at partitions) before adding more consumers.
- If you can't answer "why is this order stuck?" quickly, invest in orchestration and tracing before adding more choreographed events.

---

## 7. Caveats

- "Exactly-once" is narrow. Kafka's EOS (KIP-98) covers consume-transform-produce within Kafka with `read_committed`. It does not magically make a consumer's write to Aurora atomic with the offset commit. That gap is exactly why the outbox and idempotent-consumer patterns exist, so don't let marketing language ("exactly-once!") lull you.
- Durability has preconditions. KIP-98's own text notes that guarantees hold only for replication-factor 2 or higher and in the absence of concurrent hard failures, since async flush to disk means a simultaneous multi-broker power loss can still lose acknowledged messages. Treat "no data loss" as conditional.
- Vendor and marketing sources versus primary sources. Many blog posts, and some vendor pages, overstate guarantees or present roadmap features as shipped. Prefer KIPs, the Apache, Confluent, Spring, and Debezium official docs, and the named engineering blogs cited here. Where a third-party post is the only source (some Uber-scale figures reported secondhand, for instance), treat the numbers as approximate. The LinkedIn, Uber, and Wix figures in this report are anchored to their primary engineering posts.
- Korean company posts describe *their* context. Woowahan's SNS/SQS layering and Toss's Active-Active IDC design are shaped by their scale and constraints, so adopt the patterns rather than the exact topology.
- Currency of resources. Kafka is moving to KRaft (ZooKeeper removal) and to the next-generation consumer rebalance protocol (KIP-848, early access in Kafka 3.7+), and some older courses and books still teach ZooKeeper-centric ops. Cross-check version-specific details against the current Apache Kafka docs.
- Some example repos are dated. idugalic/digital-restaurant (2018-era deps) and confluentinc/kafka-streams-examples (maintenance mode) are architecturally instructive but should not be copied verbatim for dependency versions. Prefer FTGO, debezium-examples, spring-modulith, spring-kafka, and rkudryashov/event-driven-architecture for current code.
