---
title: "Kafka in Production — Application-Focused Reading List + Progressive EDA Practice Scenarios"
category: "Data & Messaging"
description: "A curated, application-focused (not infra-focused) Kafka and Spring Kafka reading list mapped to a Kotlin/Spring Boot + EKS + Aurora stack — Korean engineering blogs (Woowahan, 29CM, 오늘의집, Olive Young, KakaoPay 지연이체, LINE Decaton) plus the international canon (Uber reliable-reprocessing/DLQ, Wix 6 EDA patterns + 5 pitfalls, DoorDash, Shopify) — paired with eight progressive read-then-build EDA practice scenarios that climb from simple producer/consumer and partition-ordering through Transactional Outbox + Debezium CDC, choreography saga, CQRS read models, retry/DLQ idempotency, exactly-once transactions, and a Kafka Streams settlement capstone."
---

# Kafka & Spring Kafka in Production: A Curated Reading List + Progressive EDA Practice Scenarios

## TL;DR
- The strongest **application-focused** (not infra-focused) Kafka reading list maps cleanly to your Kotlin/Spring stack: Woowahan (배민) for outbox + ordering + CDC, 29CM and 우아한형제들 for Transactional Outbox, 오늘의집 and Woowahan for Kafka Streams settlement, Olive Young for dedup/loss handling, KakaoPay 지연이체 for payment-domain ordering/idempotency, plus Uber (DLQ/retry), Wix (6 EDA patterns + 5 pitfalls), DoorDash (event pipeline), Shopify (Inbox CDC), and LINE Decaton for JVM-native designs.
- The single best **"read-then-build" pairing** is Uber's reliable-reprocessing/DLQ post + Spring Kafka `@RetryableTopic`/`@DltHandler` (with the eugene-khyst reference repo as the bridge) — it is the canonical application-level error-handling pattern and directly buildable in Spring Boot.
- The **eight practice scenarios** below progress beginner→advanced (producer/consumer → partition-ordering → outbox+Debezium CDC → choreography saga → CQRS read model → retry/DLQ/idempotency → exactly-once → Kafka Streams settlement), each tied to a specific real company blog post so you can read the source then build the practice version.

## Key Findings

### What "application-focused" sources actually exist
There is a large, high-quality corpus of Korean-company application posts — far more than for most stacks — because Korean Spring Boot shops (Woowahan, 29CM, 오늘의집/버킷플레이스, Olive Young, Musinsa, Kurly) write detailed domain-event writeups. The strongest are JVM/Spring-based, which maps directly to your Kotlin + Spring Boot stack.

The international canon for *application-level* (not cluster-ops) Kafka is smaller but well-defined: Uber (reliable reprocessing & DLQ), Wix (6 EDA patterns, 5 pitfalls, schema management), DoorDash (Iguazu event pipeline), Robinhood (Faust — Python, less relevant to your stack), Shopify (CDC + Inbox buyer-signal pipeline). Many "big company + Kafka" posts are actually infra/ops (sizing, MirrorMaker, multi-DC) — e.g., much of Toss's published Kafka series is data-center duplication and CDC pipeline operations, so I've de-prioritized those and flagged them.

Spring-specific application material is strongest in the official Spring Kafka reference (`@RetryableTopic`, `@DltHandler`, non-blocking retries), plus high-quality engineering writeups (Lydtech, ManoMano, Baeldung) and the eugene-khyst reference implementation that explicitly rebuilds Uber's DLQ pattern in Spring Boot.

### Honest tradeoffs to keep in mind while reading
- **Outbox vs. CDC**: 29CM explicitly chose application-managed Transactional Outbox over Debezium CDC because the team wasn't ready to operate Debezium — a useful "build vs. adopt" data point. Woowahan (배민 배달) instead used a MySQL source connector (CDC) reading outbox tables, sharding outbox tables per topic for throughput. Both are valid; the choice is operational maturity, not correctness.
- **Non-blocking retries break ordering**: Spring's `@RetryableTopic` is excellent but every serious source (Spring docs, Lydtech, Baeldung) warns it sacrifices partition ordering and can duplicate — so idempotent consumers are mandatory, not optional.
- **Exactly-once is narrow**: Kafka EOS only holds for Kafka-to-Kafka flows (read-process-write within Kafka). The moment you touch an external DB/HTTP call, you're back to at-least-once + idempotency. Olive Young's post makes this explicit (default is at-least-once).

---

## Details

### (a) Korean company tech blogs (mostly Spring Boot / JVM — high relevance)

**우아한형제들 / 배달의민족 (Woowahan) — techblog.woowahan.com**
- **"우리 팀은 카프카를 어떻게 사용하고 있을까"** (techblog.woowahan.com/17386/). Delivery service team (딜리버리서비스팀) handling 1M+ daily 배민배달 deliveries. Demonstrates: domain events with Kafka as event broker for ordering guarantees; **Transactional Outbox via MySQL source connector**; outbox tables sharded (delivery-outbox1/2/3) per topic and by key for throughput while preserving per-key ordering; Kafka Streams for real-time delivery aggregation; separate service vs. analytics topics for failure isolation. **The single best Korean application post.** JVM/Spring.
- **"회원시스템 이벤트기반 아키텍처 구축하기"** (techblog.woowahan.com/7835/). Member/account domain EDA. Demonstrates: event layering, SNS-SQS-application reliable delivery, the dual-write problem (publishing inside a transaction makes broker outage a system outage), event store construction. Honest about remaining problems. JVM/Spring.
- **"CDC 너두 할 수 있어 (feat. B2B 알림 서비스에 Kafka CDC 적용하기)"** (techblog.woowahan.com/10000/). B2B notification service. Demonstrates: **Debezium MySQL Connector** reading Aurora MySQL binlog → Kafka; Avro + Schema Registry; Kotlin handler code (`CompleteHandler : NotificationHandler` with before/after CDC record comparison); the binlog-lock caveat on Aurora. Kotlin/Spring — directly on your stack.
- **"Kafka를 활용한 이벤트 기반 아키텍처 구축" (우아콘2023, YouTube)** — companion talk to 17386, event definition→implementation walkthrough.

**29CM — medium.com/@greg.shiny82**
- **"트랜잭셔널 아웃박스 패턴의 실제 구현 사례 (29CM)"**. Product domain service. Demonstrates: **Transactional Outbox** for atomic business-logic + event publishing (트랜잭셔널 메시징); explicit reasoning for choosing Outbox *over* Debezium CDC (team operational readiness); EDA migration from synchronous HTTP. JVM/Spring. Excellent "why we chose this" narrative.

**오늘의집 / 버킷플레이스 (bucketplace) — bucketplace.com/post**
- **"광고 정산 시스템에 Kafka Streams 도입하기"** (2022-05-20). Ad settlement/budget (정산) system. Demonstrates: **Kafka Streams exactly-once** for click-budget deduction; the duplicate-deduction problem when offset commit fails after RDB update; progression from RDB design → in-memory → Kafka Streams with state store; S3 sink connector + Spark for daily statistics. Directly relevant for ledger/settlement scenarios. JVM.

**Olive Young (CJ올리브영) — oliveyoung.tech**
- **"Kafka 메시지 중복 및 유실 케이스별 해결 방법"** (2024-10-16). OMS (Order Management System) / SCM WMS integration with 대한통운, on AWS MSK. Demonstrates: case-by-case analysis of message duplication and loss; at-least-once vs exactly-once delivery semantics in application logic. Per the post, the SCM squad "약 40 건의 EAI 와 Batch 를 제거하고 Kafka Topic 을 통해 데이터를 송수신할 수 있도록 변경" — the OMS project, built with 대한통운 and CJ올리브네트웍스, fully launched 2024년 8월 11일. Kotlin/Spring shop (their hiring explicitly lists Java/Kotlin/Spring/JPA). Highly relevant.

**Musinsa — medium.com/musinsa-tech**
- **"허튼짓은 그만: Kafka Streams를 활용한 실시간 이상 로그인 감지 시스템 도입하기"**. Fraud/anomaly detection (이상 로그인). Demonstrates: Kafka Streams topology (KStream/KTable/GlobalKTable), stateful stream processing for real-time abnormal-login detection. JVM.

**Toss / 토스증권 — toss.tech (flagged: mostly infra/ops, read selectively)**
- "토스증권 Apache Kafka 데이터센터 이중화 구성 #1/#2" and "대규모 CDC Pipeline 운영을 위한 Debezium 개선 여정" — these are **infrastructure/operations** (Active-Active duplication, MM2 alternatives, Debezium snapshot tuning), NOT application domain events. De-prioritized per your criteria, but the SLASH22 "애플 한 주가 고객에게 전달되기까지" talk (Toss Securities order/execution flow) IS application-level: broker isolation, idempotent global unique IDs, fail-over without message loss.

**KakaoPay / Kakao — tech.kakaopay.com, tech.kakao.com**
- **"지연이체 서비스 개발기: 은행 점검 시간 끝나면 송금해 드릴게요!"** (tech.kakaopay.com/post/ifkakao2024-delayed-transfer/, 2024). Scheduled money transfer that auto-executes after a bank's nightly maintenance window. Demonstrates: event-driven async execution on Kafka (migrated off RabbitMQ delay queues); **idempotency/dedup** via state-check + PREPARATION-state transition; **partition-key = userId** so one user's transfers stay ordered in one partition/consumer; user-lock for concurrency; batch + multithread throughput tuning. Per the post, after raising consumers 2→3, max.poll.records 1→20, and threads 1→10, "1분당 처리량은 800% 증가했고 실행 속도는 8배 가량 빨라졌습니다" (per-minute throughput rose 800%, execution ~8× faster). Spring/JVM. Excellent payment-domain ordering+idempotency case.
- **"신뢰성 있는 카프카 애플리케이션을 만드는 3가지 방법" (제3회 Kakao Tech Meet)** (tech.kakao.com/2023/09/22/techmeet-kafka/, 2023). Ad recommendation stream (impression/click/conversion). Demonstrates: exactly-once semantics, Kafka transactions, delivery-guarantee selection at the client/application level, with code from their Smart Message service.

**LINE / LY — engineering.linecorp.com**
- **"Kafka-based job queue library 'Decaton' examples"** (engineering.linecorp.com/en/blog/kafka-based-job-queue-library-decaton-examples/, 2020, Kazuki Matsushita). Smart Channel async content updates + event logging. Demonstrates: **Kafka-backed async job queue**; built-in retry via a dedicated retry topic; **deferred/delayed processing** (re-process impression events after 10 min to classify click/mute/no-action); concurrent multi-threaded processing of a single partition. Per the line/decaton GitHub README, the library "has been designed, optimized and being used for LINE's server system which produces over 1 million, I/O intensive tasks per second for each stream." JVM library — directly embeddable in Spring Boot.
- **"Applying Kafka Streams for internal message delivery pipeline"** (engineering.linecorp.com/en/blog/applying-kafka-streams-for-internal-message-delivery-pipeline/, ~2018, Yuto Kawamura). The IMF project that birthed Decaton — replacing "talk-dispatcher". Demonstrates: durable task queue on Kafka, process isolation so unrelated failures (e.g., HBase outage) don't block other processors, independent consumption of the same task.

### (b) International company engineering blogs (application-focused)

**Uber — uber.com/blog/reliable-reprocessing**
- **"Building Reliable Reprocessing and Dead Letter Queues with Apache Kafka"**. Driver Injury Protection (per-mile insurance premium per trip), Java service. Per the post, "This strategy helps our opt-in Driver Injury Protection program run reliably in more than 200 cities, deducting per-mile premiums per trip for enrolled drivers." **The canonical application-level DLQ/retry post.** Demonstrates: separate retry topics + DLQ topics; non-blocking reprocessing (failed message → retry topic, original offset committed so batch isn't blocked); "leaky bucket"/delayed-processing queues; per-consumer-group independent reprocessing. The post specifies a DLQ "should allow listing for viewing the contents of the queue, purging for clearing those contents, and merging for reprocessing the dead-lettered messages." Directly portable to Spring `@RetryableTopic`. **Start here.**

**Wix — medium.com/wix-engineering (Natan Silnitsky)**
- **"6 Event Driven Architecture Patterns" (Part 1 & 2)**. Scale figures vary by date in Wix's own material: the "6 EDA Patterns Part 2" Medium post (May 28, 2020) states "more than 1400 microservices," while Silnitsky's later decks cite 1,500 rising to 2,000+ microservices. Demonstrates: Consume-and-Project (data decoupling), End-to-end events (Kafka + websockets), in-memory KV stores, event transactions / exactly-once, key-based ordering, Kafka Streams aggregation (groupBy/reduce/count → webhook). The ecom flow example (Payments → Checkout → Delivery/Inventory/Invoices) is a perfect saga/choreography reference.
- **"Event Driven Architecture — 5 Pitfalls to Avoid"**. Demonstrates: the dual-write/atomicity problem and two mitigations (Greyhound resilient producer with S3 fallback; **Debezium CDC connector**); idempotency; event sourcing pitfalls; large-payload handling (claim-check pattern). Battle-tested, honest about production incidents.
- **"How Wix manages Schemas for Kafka (and gRPC) for 2000 microservices"**. Demonstrates: Protobuf + Confluent Schema Registry, schema evolution / poison-pill avoidance, compatibility checks. Read for the schema-evolution scenario.

**DoorDash — careersatdoordash.com/blog**
- **"Building scalable real time event processing with Kafka and Flink"** (Iguazu). Per the post, the team "built the real time events processing system and scaled it to process hundreds of billions of events per day with a 99.99% delivery rate," cutting end-to-end latency to Snowflake "from a day to just a few minutes." Demonstrates: unified event publishing API, Kafka REST proxy for producers (incl. mobile), schema registry integration, Flink for processing. Note: more platform than single-domain feature, but the unified-event-format and producer-abstraction lessons are application-level.

**Shopify — shopify.engineering**
- **"Building a Real-time Buyer Signal Data Pipeline for Shopify Inbox"** (2021). Merchant-customer messaging. Demonstrates: combining **Monorail (structured event abstraction with schema versioning) + CDC events**; stateful aggregation (Apache Beam, keyed by buyer) of cart/checkout/conversation events. Good event-carried-state + read-model reference.

**Robinhood — github.com/robinhood/faust (flagged: Python)**
- **Faust** — Python port of Kafka Streams used for fraud/risk/order-quality streaming. Conceptually excellent (agents, tables, RocksDB state, changelog topics) but **Python, not your stack** — read for ideas, not for code. Robinhood's `kafkahood` also implements a Postgres-backed DLQ.

### (c) Spring Kafka–specific application posts (directly on your stack)

- **Spring for Apache Kafka reference — "Non-Blocking Retries"** (docs.spring.io/spring-kafka/reference/retrytopic.html). The authoritative source for `@RetryableTopic`, `@DltHandler`, `RetryTopicConfiguration`, topic-naming/suffixing, exponential backoff, exception classification (include/exclude), `DltStrategy.FAIL_ON_ERROR`. Essential.
- **eugene-khyst/spring-kafka-non-blocking-retries-and-dlt** (GitHub). A working Spring Boot reference implementation explicitly rebuilding Uber's reliable-reprocessing/DLQ pattern. **The best read-then-build bridge** from Uber's post to your stack.
- **Lydtech Consulting — "Kafka Consumer Non-Blocking Retry: Spring Retry Topics"**. Walks a real `UpdateItemConsumer` use case (update-item event arrives before create-item, retried until item exists), with `@RetryableTopic` + `@DltHandler` and full config. Includes a from-scratch non-blocking retry design for non-Spring-Kafka apps.
- **ManoMano Tech — "Handle errors in Spring Kafka consumers like a bliss"**. Blocking vs async retries, Avro + business-service mapping, single vs multiple retry topics, the ordering tradeoff. Production team writeup.
- **Baeldung — "Dead Letter Queue for Kafka With Spring"** and **"Implementing Retry in Kafka Consumer"**. Payment-system DLT example with all three `DltStrategy` options and AckMode choices. Good for fundamentals.
- **Transactional Outbox in Spring**: 29CM post (above) plus the velog "트랜잭셔널 아웃박스 패턴" writeup showing why `@Transactional` + `KafkaTemplate.send()` is NOT atomic, and the `@TransactionalEventListener(phase = AFTER_COMMIT)` approach and its limits — read alongside building Scenario 3.

---

## Recommended reading order (mapped to your stack)
1. **Woowahan 17386** (Korean, application overview, Spring) — the mental model.
2. **Uber reliable reprocessing** (English, the DLQ canon) → then **eugene-khyst repo** + **Spring Kafka non-blocking retries docs** to build it.
3. **29CM outbox** + velog outbox writeup → build Scenario 3.
4. **Wix 6 patterns + 5 pitfalls** → choreography saga + dual-write understanding.
5. **오늘의집 Kafka Streams 정산** + **Woowahan Streams** → settlement/aggregation scenario.
6. **Olive Young dup/loss** + **KakaoPay 지연이체** → idempotency/ordering in payment domain.
7. **Shopify Inbox / Wix schema** → CQRS read model + schema evolution.

---

# Second Deliverable: Progressive EDA Practice Scenarios (Kotlin + Spring Boot + Spring Kafka)

Stack assumptions: Kotlin, Spring Boot 3.x, Spring for Apache Kafka, Aurora MySQL, AWS/EKS, Docker Compose for local Kafka + Schema Registry + Kafka Connect/Debezium. Each scenario lists domain, objective, concepts, topics/events, the key challenge, and the company post to read first.

### Scenario 1 — Order events: simple producer/consumer (Beginner)
- **Domain**: E-commerce order placement.
- **Learning objective**: Wire `KafkaTemplate` producer and `@KafkaListener` consumer end-to-end with JSON, then Avro + Schema Registry.
- **Concepts**: Spring Boot Kafka autoconfiguration, `KafkaTemplate`, `@KafkaListener`, `ConcurrentKafkaListenerContainerFactory`, serialization, manual vs auto offset commit (`AckMode`).
- **Topics/events**: `order.created` (key = orderId). Event: `OrderCreated{orderId, userId, items[], totalAmount, occurredAt}`.
- **Key challenge/edge case**: At-least-once delivery — observe a duplicate when you throw after processing but before commit. Sets up Scenario 6.
- **Read first**: Woowahan 17386 (overview); Baeldung retry/DLT for the consumer skeleton.

### Scenario 2 — Consumer groups, partitioning & ordering (Beginner→Intermediate)
- **Domain**: Per-user order status stream (CREATED→PAID→SHIPPED).
- **Learning objective**: Guarantee per-entity ordering while scaling horizontally.
- **Concepts**: partitioning by key, consumer-group rebalancing, partition assignment, `concurrency` on the listener container, why ordering only holds within a partition.
- **Topics/events**: `order.status` with key = orderId (and a variant keyed by userId to feel the difference). Events: `OrderPaid`, `OrderShipped`.
- **Key challenge/edge case**: Show out-of-order processing when you key by the wrong field or add a non-blocking retry; prove ordering with key = orderId. Run 3 partitions / 2→3 consumers and watch reassignment.
- **Read first**: KakaoPay 지연이체 (partition-key = userId for sequential per-user processing); Woowahan 17386 (per-key ordering via outbox).

### Scenario 3 — Transactional Outbox + Debezium CDC (Intermediate)
- **Domain**: Order service publishing reliable domain events to inventory/notification.
- **Learning objective**: Solve the dual-write problem — atomic DB write + event publication.
- **Concepts**: outbox table written in the same `@Transactional` unit as business data; a relay (start with a `@Scheduled` poller, then switch to **Debezium MySQL connector** on Aurora binlog → Kafka); aggregate-id as partition key for ordering; tombstones.
- **Topics/events**: `outbox` table → `order.events`. Event envelope: `{eventId, aggregateType, aggregateId, type, payload}`.
- **Key challenge/edge case**: Kill the app between DB commit and publish to prove the poller still delivers; then kill Kafka and prove no loss. Compare poller vs Debezium operationally.
- **Read first**: 29CM outbox (build-vs-adopt reasoning) and velog outbox post (why `@Transactional`+send isn't atomic); Woowahan CDC 10000 (Debezium on Aurora, Kotlin handler); Wix pitfall #1 (dual-write).

### Scenario 4 — Choreography saga across services (Intermediate→Advanced)
- **Domain**: Checkout spanning Order → Payment → Inventory → Delivery.
- **Learning objective**: Coordinate a distributed transaction with compensations, no central orchestrator.
- **Concepts**: event choreography, compensating transactions (PaymentFailed → release stock), correlation IDs, saga timeouts, choreography vs orchestration tradeoff.
- **Topics/events**: `order.created`, `payment.completed`/`payment.failed`, `inventory.reserved`/`inventory.failed`, `delivery.scheduled`. Key = orderId throughout.
- **Key challenge/edge case**: Inject a payment failure after stock reservation and verify stock is released (compensation); add a timeout so a never-responding Payment service doesn't wedge the saga (Wix/Conduktor failure mode). Build an orchestration variant for comparison.
- **Read first**: Wix 6 patterns (ecom Payments→Checkout→downstream flow); Wix 5 pitfalls (saga timeouts).

### Scenario 5 — CQRS read-model projection (Advanced)
- **Domain**: Order history / seller dashboard with different read shapes than the write model.
- **Learning objective**: Build a materialized read model fed by events, separate from the write store.
- **Concepts**: CQRS, event-carried state transfer, projection consumer, eventual consistency, read-your-writes mitigations (version-gated reads), upsert/idempotent projections, choosing a read store (MongoDB/Elasticsearch/Redis).
- **Topics/events**: consume `order.events` → project into `order_detail_view` (Mongo) and `seller_sales_view`.
- **Key challenge/edge case**: Handle consumer lag (stale reads) and duplicate events (idempotent upsert keyed by eventId); expose read-your-writes via an event-version check.
- **Read first**: Shopify Inbox buyer-signal pipeline (event aggregation read model); Wix Consume-and-Project; the nayoung CQRS Medium post (Command change via Kafka → MongoDB view).

### Scenario 6 — Retry topics, DLQ & idempotent consumers (Advanced)
- **Domain**: Notification/fulfillment consumer calling a flaky external API.
- **Learning objective**: Reliable error handling without blocking real-time traffic.
- **Concepts**: `@RetryableTopic` non-blocking retries, exponential backoff, exception classification (include/exclude — retry transient, DLT on validation errors), `@DltHandler`, DLQ inspection/replay, **idempotent consumer** (dedup table keyed by eventId, or Redis SETNX with TTL).
- **Topics/events**: `notification.requested` → `*-retry-0/1/2` → `*-dlt`.
- **Key challenge/edge case**: Because non-blocking retries break ordering and can duplicate, make the consumer idempotent; build a CLI/endpoint to replay from DLT (Uber's list/purge/merge; Robinhood's Postgres DLQ idea).
- **Read first**: Uber reliable reprocessing (the pattern); eugene-khyst repo + Spring Kafka non-blocking retries docs (build it); Olive Young dup/loss (idempotency cases).

### Scenario 7 — Exactly-once / Kafka transactions (Advanced)
- **Domain**: Ledger entry / fund transfer (debit one account, credit another).
- **Learning objective**: Understand where EOS actually applies and implement read-process-write transactions.
- **Concepts**: idempotent producer (`enable.idempotence=true`), Kafka transactions (`transactional.id`, `KafkaTemplate` with `transactionIdPrefix`), `isolation.level=read_committed`, EOS limited to Kafka-to-Kafka, the `@TransactionalEventListener(AFTER_COMMIT)` limits when an external DB is involved.
- **Topics/events**: `transfer.requested` → consume-process-produce `balance.debited` + `balance.credited` in one Kafka transaction.
- **Key challenge/edge case**: Reproduce the double-debit when a crash occurs before offset commit *without* transactions, then fix with transactions; show that adding an external DB write reintroduces at-least-once (needs idempotency).
- **Read first**: 오늘의집 Kafka Streams 정산 (double-deduction problem & EOS); KakaoPay/Kakao Tech Meet exactly-once; Olive Young (default is at-least-once).

### Scenario 8 — Kafka Streams aggregation / settlement (Advanced, capstone)
- **Domain**: Daily ad-click budget settlement / per-merchant sales aggregation.
- **Learning objective**: Stateful stream processing with windowing and exactly-once, no external scheduler.
- **Concepts**: Kafka Streams DSL (KStream/KTable, groupBy, reduce/count, windowing), state stores (RocksDB) + changelog topics, EOS in Streams, sink to S3/RDB for cold storage + Spark/Athena for history.
- **Topics/events**: `ad.click` → Streams app → `budget.updated` (KTable) + `settlement.daily` → S3 sink connector.
- **Key challenge/edge case**: Handle duplicate clicks (EOS), late events (windowing), and state recovery after a restart (changelog replay); separate service vs analytics topics for failure isolation.
- **Read first**: 오늘의집 광고 정산 Kafka Streams (the exact scenario); Woowahan Kafka Streams 삽질기; Musinsa Kafka Streams anomaly detection; Wix Streams aggregation.

## Caveats
- Several sources are **conference talks / recap posts** (Woowahan 우아콘 videos, Kakao Tech Meet) rather than long-form articles — the depth is in the talk, not always the page.
- I verified the KakaoPay 지연이체 and LINE Decaton-examples posts in full; the KakaoPay instant-insurance post, Kakao Tech Meet reliability post, and the two LINE posts were confirmed to exist on the companies' own domains but not all fetched in full, so treat their pattern lists as indicative.
- Toss's published Kafka series is **predominantly infrastructure/operations** (data-center duplication, Debezium snapshot tuning) and was de-prioritized per your application focus; the SLASH22 securities talk is the application-level exception.
- Robinhood/Faust is **Python**, not your stack — included for conceptual completeness only.
- Dates: some Korean posts lack explicit publication dates on-page; where given (e.g., Olive Young 2024-10-16, 오늘의집 2022-05-20) they are from the post itself. Verify the current URL if a blog has migrated (LINE → LY Corporation post-2023 rebrand; some content now at techblog.lycorp.co.jp).
- "Exactly-once" claims in vendor/blog material frequently overstate scope; always confirm whether a given post means Kafka-internal EOS or end-to-end (which, with external systems, it is not).