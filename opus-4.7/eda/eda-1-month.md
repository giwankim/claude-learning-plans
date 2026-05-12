---
title: "One-Month Deep Dive into Event-Driven Architecture"
category: "Data & Messaging"
description: "Four-week intensive covering Fowler's EDA patterns, Kafka fundamentals, transactional outbox with Debezium, event sourcing and CQRS, and Kafka Streams, grounded in Kotlin/Spring Boot on AWS"
---

# A One-Month Deep Dive into Event-Driven Architecture for a Senior Backend Engineer

## TL;DR
- **Treat the month as three intellectual moves and four hands-on builds.** Move 1: collapse the word "event-driven" into Martin Fowler's four concrete patterns (Event Notification, Event-Carried State Transfer, Event Sourcing, CQRS) and Jay Kreps' log abstraction. Move 2: master Kafka as a *distributed, partitioned, append-only commit log* — not a queue. Move 3: internalize the operational tax (eventual consistency, outbox, sagas, schema evolution, DLQs). The four builds (Order pub/sub → Outbox+CDC → Event Sourcing wallet → Kafka Streams fraud) make every concept land in Kotlin/Spring Boot/MySQL.
- **Be opinionated:** Use Spring Kafka (not Spring Cloud Stream) for production-ish projects; use Avro + Confluent Schema Registry from week 2 onward; use Debezium for the outbox relay; use Testcontainers (not EmbeddedKafka) for integration tests. Treat Aurora MySQL's binlog as a first-class event source — it's the same primitive Airbnb's SpinalTap and Debezium ride on. On Kubernetes, plan around the Strimzi operator.
- **The right reading list is short and dense:** Kleppmann's *Designing Data-Intensive Applications* (chapters 3, 5, 7, 11), Bellemare's *Building Event-Driven Microservices* (2nd ed., 2025), the Kafka project's *Definitive Guide* (3rd ed.), Kreps' "The Log" essay, Fowler's "What do you mean by Event-Driven?", and three Confluent/InfoQ talks (Fowler GOTO 2017, Monal Daxini on Netflix Keystone, Yuto Kawamura's LINE talks). Everything else is supporting fire.

---

## Key Findings (what this plan asserts up front)

1. **"Event-driven" is four patterns in a trench coat.** When someone says "we're going event-driven," ask which: notification, ECST, event sourcing, or CQRS. Each has different tradeoffs and they compose in specific ways. Fowler's 2017 essay and GOTO Chicago talk are the canonical disambiguation.
2. **Kafka is conceptually a log, not a queue.** Reading Kreps' "The Log: What every software engineer should know about real-time data's unifying abstraction" (LinkedIn Engineering, 2013) before reading the Kafka docs collapses 80% of confusion. Partitions are append-only logs; consumer groups are independent readers tracking offsets; replication is just leader/follower log replication.
3. **Most production EDA pain comes from three places**: the dual-write problem (solved by the transactional outbox + Debezium CDC), schema evolution (solved by Avro/Protobuf + a Schema Registry with explicit compatibility rules), and operational visibility (solved by distributed tracing + consumer-lag monitoring + DLQs with replay tooling). Plan to invest in all three from day one.
4. **For Kotlin + Spring Boot + Aurora MySQL, the canonical path is**: Spring Kafka for producers/consumers, Spring Data JDBC/JPA for the outbox table, Debezium MySQL connector reading the binlog, Kafka Streams (not Flink) for stream processing inside microservices, Testcontainers for integration tests, Strimzi for Kubernetes deployment.
5. **The companies cited in case studies all converged on the same primitive**: an immutable, replayable, partitioned event log as the data backbone, with bounded contexts emitting *facts* and downstream services materializing their own read models. LinkedIn, Uber, Netflix, Airbnb, Shopify, LINE, Coupang, Kakao Games all instantiate this pattern with different details.
6. **Be deliberate about when *not* to use EDA.** For 5-endpoint CRUD APIs, simple admin tools, strongly-coupled request/response flows that need a synchronous answer (auth, payment authorization at the user-facing layer), and small teams without operational appetite for brokers, EDA is the wrong answer. The pattern is most valuable when (a) you have ≥5 services that need the same fact, (b) you need replay/audit, (c) you have spiky load that benefits from buffering, or (d) you need to evolve consumers independently of producers.

---

## Details

### Week 1 — Foundations and a First Hands-On Pipeline

**Learning objectives**
- Be able to define an event, distinguish it from a command and a message, and justify fact-based modeling.
- Recite Fowler's four patterns from memory and give one production example of each.
- Articulate when to choose async over sync, and pub/sub over point-to-point.
- Understand choreography vs. orchestration as a coordination axis, independent from the messaging axis.
- Run a first end-to-end Spring Boot + Kafka pipeline in Docker Compose.

**Key concepts to master**

| Concept | The one-sentence intuition |
|---|---|
| Event | An immutable, named, timestamped statement of fact in the past tense (`OrderPlaced`, `PaymentCaptured`). |
| Command | An imperative, addressed to a specific recipient, that may be rejected (`PlaceOrder`). |
| Message | The transport-level envelope carrying either. |
| Event Notification | "Something happened, here's an ID — call me if you care." Smallest payload, callers may need to fetch state. |
| Event-Carried State Transfer (ECST) | "Something happened, and here is enough state for you to do your job without calling me." Improves availability but introduces local replicas and eventual consistency. |
| Event Sourcing | The event log *is* the source of truth; current state is a fold over events. Confers audit, replay, time travel; costs complexity. |
| CQRS | Separate the write model (commands → events) from one or more read models (projections). Pairs naturally with event sourcing but is independent of it. |
| Choreography | No central conductor — each service reacts to events and emits new ones. Loosely coupled but globally opaque. |
| Orchestration | A central process (saga orchestrator, BPMN engine) sequences calls. Easier to reason about, easier to become a bottleneck. |
| Pub/sub vs. point-to-point | Pub/sub fans an event to N independent subscribers; point-to-point delivers to exactly one. Kafka consumer groups give you both depending on how you configure them. |

**Required reading**
- Martin Fowler, *"What do you mean by 'Event-Driven'?"* (martinfowler.com, 7 Feb 2017). The disambiguation essay.
- Martin Fowler, *"The Many Meanings of Event-Driven Architecture"*, GOTO Chicago 2017 keynote (video; ~50 min). Watch before Wednesday.
- Jay Kreps, *"The Log: What every software engineer should know about real-time data's unifying abstraction"*, LinkedIn Engineering blog, 16 Dec 2013. Read this slowly — it is the most important single document about the conceptual framework of Kafka and modern data infrastructure. Pair it with chapter 11 ("Stream Processing") of Kleppmann.
- Adam Bellemare, *Building Event-Driven Microservices* (O'Reilly, 2nd ed., 2025), chapters 1–4. Domain modeling, bounded contexts, communication structures, event design.
- Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly, 2017), chapter 11 ("Stream Processing"). Mathematically rigorous and the perfect register for a PhD reader.

**Hands-on Project 1: Order pub/sub with Spring Kafka + Aurora MySQL**

*Goal:* The simplest possible event-notification system in your real stack.

- Stack: Kotlin 2.x, Spring Boot 3.x, Spring Kafka, Spring Data JDBC, MySQL 8 (Aurora-compatible), Confluent Platform 7.x via Docker Compose, JSON serialization (Avro comes week 2).
- Topology: an `order-service` writes orders to MySQL and emits an `OrderPlaced` event to topic `orders.v1`. A `notification-service` and an `inventory-service` independently consume.
- Implement at least two consumers in different consumer groups to feel the difference between pub/sub (groups = "broadcast") and competing-consumers (multiple instances in the same group).
- Implement manual offset commits (`AckMode.MANUAL_IMMEDIATE`) and at-least-once semantics; deliberately throw an exception mid-handler and observe redelivery.
- Add idempotency: each event carries an `eventId` UUID; consumers maintain a `processed_events` table in MySQL with `eventId` as PK and skip duplicates inside the same transaction as the side-effect.

```kotlin
// build.gradle.kts dependencies (excerpt)
implementation("org.springframework.boot:spring-boot-starter-web")
implementation("org.springframework.kafka:spring-kafka")
implementation("org.springframework.boot:spring-boot-starter-data-jdbc")
runtimeOnly("com.mysql:mysql-connector-j")
testImplementation("org.testcontainers:kafka")
testImplementation("org.testcontainers:mysql")
testImplementation("org.springframework.kafka:spring-kafka-test")
```

```kotlin
// The event — note past tense, immutability, and self-describing metadata.
data class OrderPlaced(
    val eventId: UUID,
    val occurredAt: Instant,
    val orderId: UUID,
    val customerId: UUID,
    val totalCents: Long,
    val currency: String,
    val version: Int = 1, // schema version, even with JSON
)

@Service
class OrderService(
    private val orderRepository: OrderRepository,
    private val kafkaTemplate: KafkaTemplate<String, OrderPlaced>,
) {
    @Transactional // NOTE: this is the "dual-write problem" — solved properly in Project 2.
    fun placeOrder(cmd: PlaceOrderCommand): UUID {
        val order = orderRepository.save(Order.from(cmd))
        kafkaTemplate.send("orders.v1", order.id.toString(), OrderPlaced(
            eventId = UUID.randomUUID(),
            occurredAt = Instant.now(),
            orderId = order.id,
            customerId = order.customerId,
            totalCents = order.totalCents,
            currency = order.currency,
        ))
        return order.id
    }
}

@Component
class InventoryListener(private val inventory: InventoryService) {
    @KafkaListener(topics = ["orders.v1"], groupId = "inventory-service")
    fun on(event: OrderPlaced, ack: Acknowledgment) {
        inventory.reserve(event.orderId, event.totalCents) // must be idempotent
        ack.acknowledge()
    }
}
```

**Self-assessment questions (Friday of week 1)**
1. Explain to a non-EDA colleague why we *don't* call this an asynchronous RPC.
2. Where in your code did you violate the dual-write principle, and what concrete failure modes does that violation create?
3. Your `OrderPlaced` event was published successfully but the MySQL transaction rolled back. What state is the system in, and what bug will the customer see?
4. Why is the `orderId` a good Kafka partition key? What would happen if you partitioned by `customerId` instead?
5. Give one example from your own work where an Event-Carried State Transfer would be the *wrong* pattern.

### Week 2 — Kafka Deep Dive and the Transactional Outbox

**Learning objectives**
- Internalize Kafka's architecture: brokers, topics, partitions, replication, leader/follower, ISR, KRaft mode, consumer groups, offsets, retention, log compaction.
- Understand producer semantics: `acks`, idempotent producer, transactions, ordering guarantees.
- Understand consumer semantics: poll loop, rebalance protocols (cooperative-sticky), heartbeat vs. session timeout, max.poll.interval.ms.
- Implement the transactional outbox pattern with Debezium and Aurora MySQL binlog CDC.
- Adopt Avro + Schema Registry and exercise backward/forward compatibility.

**Key concepts to master**

- **Partitioning as the unit of parallelism and ordering.** Within a partition, order is total; across partitions, there is no order. Choose a partition key that aligns with the boundary you care about ordering by (typically the aggregate ID).
- **Replication and ISR.** Each partition has a leader and N–1 followers; only in-sync replicas count. `min.insync.replicas=2` + `acks=all` is the durability floor for anything money-shaped.
- **Log compaction.** Kafka can retain *the latest value per key* forever. This makes a topic act like a versioned key-value store — the foundation of Kafka Streams `KTable` and of "the database inside out."
- **Exactly-once semantics (EOS).** Kafka transactions + idempotent producer give you EOS within Kafka. End-to-end EOS across an external database requires either the outbox pattern or careful idempotency.
- **The dual-write problem.** Writing to MySQL and Kafka in the same business operation cannot be made atomic without a coordinator. The outbox pattern reduces it to a single local transaction.
- **Schema Registry compatibility modes.** `BACKWARD` (new schema can read old data — the default), `FORWARD`, `FULL`, `NONE`. Pick at the topic level.

**Required reading**
- Gwen Shapira, Todd Palino, Rajini Sivaram, Krit Petty, *Kafka: The Definitive Guide* (O'Reilly, 2nd ed., 2021), chapters 3–7 (producers, consumers, internals, reliable delivery, exactly-once).
- Gunnar Morling, *"Reliable Microservices Data Exchange With the Outbox Pattern"* (Debezium blog, 19 Feb 2019). The reference text.
- Gunnar Morling et al., *"Revisiting the Outbox Pattern"* (Decodable blog, 2023). The state-of-the-art update including backfill via DBLog watermarking.
- Bellemare, *Building Event-Driven Microservices*, chapters 5–8 (event broker, schemas, event design, integration).
- Kleppmann, *DDIA*, chapter 5 ("Replication") and chapter 9 ("Consistency and Consensus"). Read these to ground partitions/ISR in the broader theory of distributed log replication.
- Confluent Developer, *"Schema Registry compatibility types"* — short and authoritative.

**Hands-on Project 2: Transactional outbox + Debezium CDC**

*Goal:* Eliminate the dual-write problem in your Project 1 system using a log-based outbox relay.

- Add an `outbox_events` table in MySQL with columns: `id BINARY(16) PRIMARY KEY, aggregate_type VARCHAR, aggregate_id VARCHAR, event_type VARCHAR, payload JSON, created_at TIMESTAMP, headers JSON`.
- Modify `OrderService` to write the order row *and* an outbox row in the same `@Transactional` method. Remove the direct `kafkaTemplate.send`.
- Run **Debezium MySQL connector** in Kafka Connect as a Docker container, configured with the Debezium **outbox event router** SMT, so that the per-aggregate event type drives the destination topic (`outbox.event.order`).
- Switch serialization to **Avro with Confluent Schema Registry**. Define `OrderPlaced.avsc` and generate Kotlin classes via the `avro-tools` or `gradle-avro-plugin`.
- Demonstrate schema evolution: add an optional `discountCents` field with a default; verify the registry accepts it under `BACKWARD` compatibility and the old consumer continues to work.
- Introduce a **dead-letter topic** (`orders.v1.DLT`) using Spring Kafka's `DefaultErrorHandler` with a `DeadLetterPublishingRecoverer`, plus a `BackOff` policy with exponential retries.

```kotlin
// Outbox row — written atomically with the order in the same JDBC transaction.
@Table("outbox_events")
data class OutboxEvent(
    @Id val id: UUID,
    val aggregateType: String,      // "order"
    val aggregateId: String,         // orderId.toString()
    val eventType: String,           // "OrderPlaced"
    val payload: String,             // serialized JSON or Avro
    val createdAt: Instant = Instant.now(),
)

@Service
class OrderService(
    private val orderRepository: OrderRepository,
    private val outboxRepository: OutboxRepository,
    private val mapper: ObjectMapper,
) {
    @Transactional
    fun placeOrder(cmd: PlaceOrderCommand): UUID {
        val order = orderRepository.save(Order.from(cmd))
        val event = OrderPlacedV1(order.id, order.customerId, order.totalCents)
        outboxRepository.save(OutboxEvent(
            id = UUID.randomUUID(),
            aggregateType = "order",
            aggregateId = order.id.toString(),
            eventType = "OrderPlaced",
            payload = mapper.writeValueAsString(event),
        ))
        return order.id
    }
    // No kafkaTemplate.send. Debezium will tail the binlog and publish the
    // outbox row to Kafka with exactly-once semantics relative to the DB.
}
```

**Operational note for Aurora MySQL.** Aurora supports binlog-based replication in `ROW` format, which is exactly what Debezium needs. Set `binlog_format=ROW`, `binlog_row_image=FULL`, and the retention parameter `binlog retention hours` to at least 24. The Debezium MySQL connector needs `REPLICATION SLAVE` and `REPLICATION CLIENT` grants. Confirm that the writer instance's binlog is the one Debezium connects to.

**Self-assessment questions**
1. The outbox solves the *producer-side* atomicity problem. What still has to be true about *consumers* for end-to-end correctness?
2. Why is Debezium's binlog tailing strictly better than a polling publisher for a high-write system, and what is one operational situation where the polling publisher is actually simpler to run?
3. A teammate proposes "let's just use Kafka transactions across producer and the MySQL JDBC connection." Why does this not solve the dual-write problem?
4. You add a required (non-nullable) field to an Avro schema under `BACKWARD` compatibility. What does the Registry tell you, and why?
5. Compute the worst-case end-to-end latency for an event through your pipeline (commit → binlog → Debezium → Kafka → consumer → consumer commit). Where are the dominant terms?

### Week 3 — Event Sourcing, CQRS, and Sagas

**Learning objectives**
- Implement an event-sourced aggregate from scratch in Kotlin with MySQL as the event store.
- Build a CQRS read model (projection) updated asynchronously from the event stream.
- Understand snapshots, optimistic concurrency control on the event stream, and the rebuild-from-zero property.
- Implement both a choreographed and an orchestrated saga for a multi-service business process; understand compensating actions.
- Articulate when event sourcing is the wrong choice (most of the time, honestly).

**Key concepts to master**

- **Event store invariants.** Append-only; per-aggregate-stream total ordering via a `(aggregate_id, version)` unique constraint; rebuilding the aggregate is a left-fold of the event list.
- **Optimistic concurrency.** The write side reads the current version, applies a command to compute new events, and inserts them with `expected_version = current_version`; a unique constraint violation means a concurrent write happened — retry.
- **Snapshots.** A periodic snapshot of aggregate state avoids replaying millions of events on hot aggregates. Make the snapshot a derivative, never the source of truth.
- **Projections.** Stateless functions from event stream → read model. They should be idempotent and rebuildable from scratch.
- **Saga.** A sequence of local transactions stitched together with events (choreography) or with commands from a central coordinator (orchestration). Compensating transactions undo prior steps when a later step fails.
- **Eventual consistency, formally.** After the last write, in the absence of new updates, all replicas converge. This is *not* causal consistency — you must design your UI/API to tolerate read-your-writes anomalies (e.g., return a `Location` header that polls until visible, or return the writer's projection synchronously).

**Required reading**
- Greg Young, *"CQRS Documents"* (PDF, 2010) — the foundational essay. Short and brilliant.
- Chris Richardson, *Microservices Patterns* (Manning, 2018), chapters 4 (sagas), 6 (event sourcing), 7 (CQRS). The most pragmatic treatment.
- Bellemare, *Building Event-Driven Microservices*, chapters on workflow patterns and effectively-once processing.
- Albert Llousas, *"Exploring event sourcing: A scalable bank account"* (Medium, 2024). A modern Kotlin/Hexagonal example with SEPA transfer events.
- *Iconsolutions blog*, "CQRS & Event Sourcing in Financial Services" — for the regulatory framing of why banks adopt these patterns.
- Optional but excellent: Vaughn Vernon, *Implementing Domain-Driven Design* (Addison-Wesley, 2013), chapters on aggregates and domain events.

**Hands-on Project 3: Event-sourced wallet/account with MySQL projections**

*Goal:* Build a small but rigorous double-entry account/wallet domain with event sourcing on the write side and CQRS read models in MySQL.

- Domain: `Account` aggregate with commands `OpenAccount`, `Deposit`, `Withdraw`, `Transfer`. Events `AccountOpened`, `MoneyDeposited`, `MoneyWithdrawn`, `TransferInitiated`, `TransferCompleted`, `TransferFailed`. Enforce non-negative balance as an invariant inside the aggregate.
- Event store schema in MySQL:

```sql
CREATE TABLE event_store (
    aggregate_id BINARY(16) NOT NULL,
    version      INT        NOT NULL,
    event_type   VARCHAR(64) NOT NULL,
    payload      JSON       NOT NULL,
    occurred_at  TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (aggregate_id, version)
);
CREATE TABLE snapshots (
    aggregate_id BINARY(16) PRIMARY KEY,
    version      INT NOT NULL,
    state        JSON NOT NULL
);
```

- The aggregate is reconstructed by reading from snapshot (if any) then replaying events with version > snapshot.version.
- Use the outbox/CDC plumbing from Project 2 to publish each persisted event to Kafka. The event store table *is* effectively your outbox.
- Build two projections in separate services:
  - **Balance projection** (a MySQL table `account_balances`): maintains current balance per account.
  - **Statement projection** (MongoDB or a denormalized MySQL table): maintains transaction history for UI display.
- Implement a **money-transfer saga**, first as **choreography** (`TransferInitiated` triggers `MoneyWithdrawn`; success triggers `MoneyDeposited`; failure triggers compensating `MoneyDeposited` back to origin), then as **orchestration** using a small Spring Boot `TransferOrchestrator` service that explicitly sends commands and listens for replies. Compare reasoning effort, observability, and failure modes.
- Demonstrate a **full rebuild**: drop the projection tables, start the projection consumer from offset 0, verify it ends in the same state.

```kotlin
sealed interface AccountEvent { val occurredAt: Instant }
data class AccountOpened(val accountId: UUID, val owner: String, override val occurredAt: Instant) : AccountEvent
data class MoneyDeposited(val accountId: UUID, val amountCents: Long, override val occurredAt: Instant) : AccountEvent
data class MoneyWithdrawn(val accountId: UUID, val amountCents: Long, override val occurredAt: Instant) : AccountEvent

data class Account(val id: UUID, val owner: String, val balanceCents: Long, val version: Int) {
    fun apply(e: AccountEvent): Account = when (e) {
        is AccountOpened   -> copy(id = e.accountId, owner = e.owner, version = version + 1)
        is MoneyDeposited  -> copy(balanceCents = balanceCents + e.amountCents, version = version + 1)
        is MoneyWithdrawn  -> copy(balanceCents = balanceCents - e.amountCents, version = version + 1)
    }
    companion object {
        fun rehydrate(events: List<AccountEvent>): Account =
            events.fold(Account(UUID(0,0), "", 0L, 0)) { acc, e -> acc.apply(e) }
    }
}

fun withdraw(account: Account, amount: Long): Result<MoneyWithdrawn> =
    if (amount <= 0) Result.failure(IllegalArgumentException("non-positive"))
    else if (account.balanceCents < amount) Result.failure(InsufficientFunds())
    else Result.success(MoneyWithdrawn(account.id, amount, Instant.now()))
```

**Self-assessment questions**
1. Show why your aggregate-rebuild function `events.fold(empty, apply)` is a monoid homomorphism in the appropriate sense, and why this matters operationally.
2. Why is optimistic concurrency on the event-store insert *sufficient* to enforce the non-negative-balance invariant, even with concurrent withdrawals?
3. Choreography vs. orchestration for the transfer saga — when does the choreographed version stop being maintainable, and what does the failure mode of a missing orchestrator look like?
4. A regulator asks "what was the balance of account X at 14:32:07 on 2024-11-04?" How does event sourcing answer this, and how would a CRUD system answer it?
5. List three concrete cases in your day job where event sourcing would be *over-engineering*.

### Week 4 — Stream Processing, Schema Evolution, Operations, Kubernetes

**Learning objectives**
- Build a Kafka Streams application for real-time aggregation and anomaly detection.
- Understand stateful stream processing, windowing (tumbling, hopping, sliding, session), `KStream` vs. `KTable`, joins, and the rocksdb-backed state stores.
- Compare Kafka Streams with ksqlDB and Apache Flink and decide when to reach for each.
- Implement contract testing for events (consumer-driven contracts via Pact or schema-only contracts via the Registry).
- Plan a Kubernetes deployment of Kafka (Strimzi operator) and your services, with observability for consumer lag and DLQ depth.

**Key concepts to master**

- **`KStream` vs. `KTable`.** A `KStream` is an unbounded sequence of independent records; a `KTable` is a changelog where each key has a current value (last-write-wins). Internally, `KTable` is backed by a compacted topic.
- **Windowing.** Tumbling (non-overlapping, fixed), hopping (overlapping, fixed), sliding (event-time-driven), session (gap-based). Choose based on the question you're answering.
- **State stores and changelog topics.** Each Kafka Streams task has a local RocksDB store; changes are backed up to a compacted changelog topic so on restart/failure you can rebuild.
- **Exactly-once in Kafka Streams.** Enable with `processing.guarantee=exactly_once_v2`. Kafka Streams uses producer transactions internally for read-process-write atomicity.
- **Schema evolution playbook.** New optional fields = always safe. Removing fields, renaming, changing type = breaking. Plan for parallel versioned topics (`orders.v2`) when the change is breaking, with a dual-write period.

**Required reading**
- William Bejeck, *Kafka Streams in Action* (Manning, 2nd ed., 2021) — chapters on stateful operations, KTables, and processor API.
- Confluent Developer, *"Kafka Streams 101"* course (free, ~3 hours).
- Robin Moffatt, *"ATM Fraud Detection with Apache Kafka and KSQL"* (Confluent blog) — a clean walkthrough that maps directly to your Project 4.
- Kai Wähner, *"Fraud Detection with Apache Kafka, KSQL and Apache Flink"* (blog, Oct 2022) — surveys Paypal, Capital One, ING, Grab, and Kakao Games (the latter using 300+ ksqlDB patterns for in-game fraud).
- Monal Daxini, *"Netflix Keystone — Cloud Scale Event Processing Pipeline"* (O'Reilly Strata / SlideShare 2016) — read for the operational lessons at trillion-events/day scale.
- Bellemare, *Building Event-Driven Microservices*, chapter on FaaS and chapter on consistency.
- Strimzi documentation, "Deploying and Managing Strimzi" — for the Kubernetes operational model.

**Hands-on Project 4: Real-time fraud detection with Kafka Streams**

*Goal:* Apply stateful stream processing to detect suspicious patterns in your account events from Project 3.

- Topology: consume `account.events` (the projection-feeding topic), enrich with `customer.profile` from a `GlobalKTable`, and detect:
  - **Velocity rule:** more than 5 withdrawals in 1 minute from a single account (tumbling window).
  - **Amount-spike rule:** a single withdrawal more than 10× the rolling 24-hour average for that account (sliding window + aggregation).
  - **Geo-impossible rule (toy):** two transactions from different countries within 5 minutes (session window keyed by accountId).
- Emit a `FraudSuspected` event to a `fraud.alerts` topic; have a small `account-freezer` service consume and emit a `FreezeAccount` command back into the wallet domain.
- Implement the same detection logic in **ksqlDB** (a single `CREATE TABLE possible_fraud AS SELECT...` statement) and compare the experience.
- Add **Testcontainers**-based integration tests using `TopologyTestDriver` for stateless logic and a real KafkaContainer for the end-to-end pipeline.
- Deploy locally on **kind** with the Strimzi operator; instrument with Prometheus + Grafana to watch consumer lag and DLQ depth.

```kotlin
// Velocity detection in Kafka Streams (Kotlin sketch)
@Configuration
@EnableKafkaStreams
class FraudTopology {
    @Bean
    fun topology(builder: StreamsBuilder): KStream<String, MoneyWithdrawn> {
        val withdrawals: KStream<String, MoneyWithdrawn> =
            builder.stream("account.events", Consumed.with(Serdes.String(), withdrawnSerde))

        withdrawals
            .groupByKey()
            .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(1)))
            .count(Materialized.`as`("withdrawals-per-minute"))
            .toStream()
            .filter { _, count -> count != null && count > 5 }
            .map { windowedKey, count ->
                KeyValue(windowedKey.key(),
                    FraudSuspected(windowedKey.key(), "VELOCITY",
                                   "$count withdrawals in 1 min"))
            }
            .to("fraud.alerts", Produced.with(Serdes.String(), fraudSerde))

        return withdrawals
    }
}
```

**Operations on Kubernetes — opinionated checklist for week 4**
- Use **Strimzi** (CNCF, the de facto operator) on a kind/EKS cluster. KRaft mode (no ZooKeeper) since Strimzi 0.40+ and the default in Kafka 4.0.
- Define a `KafkaNodePool` for controllers (3 replicas) and one for brokers (3 replicas). Use JBOD `persistent-claim` storage on a fast SSD storage class.
- Set `min.insync.replicas=2`, `default.replication.factor=3` cluster-wide for any topic carrying domain events.
- Use rack awareness (`broker.rack`) mapped to availability zones via the operator's `topologyKey` for cross-AZ resilience.
- Expose Prometheus metrics via the bundled `kafka-exporter` and the JMX exporter; alert on (a) under-replicated partitions > 0, (b) consumer group lag > threshold, (c) DLQ depth > 0 for production topics.
- Run **Schema Registry** as its own deployment, persistent on a dedicated `_schemas` topic; treat schema changes as code review-able artifacts in a Git repo.
- For your Spring Boot services, use the `spring-cloud-kubernetes` config for graceful pod shutdown (drain consumer poll loop on `SIGTERM`) and set `terminationGracePeriodSeconds` large enough to commit offsets cleanly.

**Self-assessment questions**
1. Why is your velocity-rule topology fault-tolerant — what specifically rebuilds when a pod dies mid-window?
2. What is the trade-off between `exactly_once_v2` and the default at-least-once mode in Kafka Streams, in terms of latency and throughput?
3. The same fraud-detection question can be answered in Kafka Streams, ksqlDB, or Flink. Pick one each for: a Java/Kotlin shop with 5 engineers, a data-science team that wants SQL, a 100-engineer org with stateful ML scoring at sub-100ms p99. Justify.
4. You're paged because consumer lag on `account.events` is climbing during the daily 09:00 batch. List five hypotheses and the metric you'd check first for each.
5. Sketch the Kubernetes deployment topology for your four projects, naming each Pod, Service, PVC, and the network policy you'd put between them.

---

## Real-World Case Studies

Read these as you progress; they will recur in every interview about EDA.

**LinkedIn — the origin story.** Apache Kafka was developed at LinkedIn in 2010 by Jay Kreps, Neha Narkhede, and Jun Rao to solve a specific data-integration problem. In a Frontier Enterprise interview, co-founder Jun Rao described the context: "a multitude of data-driven applications and microservices—numbering around 300 to 400—had been developed by LinkedIn during that time," all needing access to the firehose of activity data (profile views, connections, ad impressions) plus a growing data warehouse stack (Hadoop, search, recommendations). Existing JMS brokers (ActiveMQ, RabbitMQ) had unacceptable per-message overhead and didn't scale out. The team designed Kafka around three principles stated in the original 2011 LinkedIn engineering blog post: a simple producer/consumer API, very low network and on-disk overhead, and horizontally scalable from day one. The architectural breakthrough was choosing the *append-only commit log* as the storage primitive, which mirrors how databases implement their write-ahead logs. By 2012 Kafka was open-sourced; by 2013 Kreps articulated the unifying conceptual frame in "The Log: What every software engineer should know about real-time data's unifying abstraction." LinkedIn's lesson for you: the canonical events are *facts about the business*, schemas are first-class artifacts, and a single uniform schema-on-write pipeline scales operationally where a fan-out of bespoke pipelines does not.

**Uber — multi-trillion-message ride-hailing platform.** Uber's Kafka deployment handles trillions of messages and multiple petabytes of data per day across federated clusters of approximately 150 nodes each (rather than one monolithic cluster). Trip lifecycle events (request → match → start → end → cancel) flow through Kafka topics typically partitioned by `tripId` or `driverId` to preserve per-entity ordering. Uber developed **uReplicator** for cross-cluster replication and disaster recovery, and in 2024–2026 open-sourced **uForwarder**, a push-based gRPC consumer proxy that mediates between Kafka and 1000+ downstream consumer services, providing context-aware routing, head-of-line blocking mitigation, adaptive rebalancing, and partition-level delay processing. Why this matters to you: Uber proves that Kafka does not stay vanilla at scale — you build platform abstractions on top of it. Their work also showcases the **choreography-at-scale** pattern: the matching service consumes both trip-request and driver-location streams and produces dispatch commands; billing/payment consume trip-end events; analytics topics mirror everything.

**Netflix — Keystone and the kappa architecture.** Keystone is Netflix's stream-processing-as-a-service platform built on Kafka and Flink. At peak it processes about 2 trillion messages per day (3 PB ingested, 7 PB output). Per Monal Daxini's AWS re:Invent 2017 slides (ABD320), the platform ran on "36+ Kafka & Zookeeper clusters · 4000+ brokers (EC2), 700+ topics · 3000+ d2.xl, 900+ i2.2xl · Highly available 99.99%+." Critically, Netflix deliberately chose **at-least-once** delivery, with this stated philosophy in Daxini's talk (per Sandeep Uttamchandani's summary on QuickBooks Engineering): "At scale, Keystone has less than 0.01% drop rate per day — Prefer dropping data rather than impacting a user-facing service application that is producing events." The same source notes the operational rule of thumb: "Through empirical iteration over years with various cluster sizes in AWS, the team follows the best practice of a max of 200 nodes (VMs) per Kafka cluster." Netflix also implemented a **Kafka Auditor** to track lag between producer and consumer. Every viewing event, search, scroll, and quality-change feeds into Keystone, which routes it to Iceberg (replay source), Elasticsearch, Cassandra, and other sinks. Lesson: think of your stream platform as a *product* with self-service onboarding, SLAs per tier, and explicit consistency choices documented up front.

**Airbnb — SpinalTap and CDC-driven SOA migration.** When Airbnb broke up its Ruby on Rails "Monorail" monolith, callback-based coupling between domains had to be replaced. Their solution, presented by Jessica Tai at QCon, was to make data mutations publish standard events via a Change Data Capture service called **SpinalTap** that tails MySQL binlogs (and DynamoDB streams) and publishes mutations to Kafka. SpinalTap powers cache invalidation, search indexing (re-indexing listings on data change), signaling (the Availability service blocks dates by subscribing to Reservation changes), and feeds the **Riverbed** distributed materialized-view framework. Per InfoQ's "Distributed Materialized Views: How Airbnb's Riverbed Processes 2.4 Billion Daily Events" (Oct 2023): "Riverbed currently processes 2.4 billion events and writes 350 million documents daily, powering over 50 materialized views across features such as payments, search, reviews, itineraries, and internal products." Lesson for you: the outbox pattern is one valid choice; CDC on the source tables directly is another. SpinalTap demonstrates the source-table-CDC approach, with the trade-off that you don't get explicit "events as first-class API" — you get database-table-shaped events.

**Shopify — flash-sale scale.** Shopify's runtime is a modular Ruby on Rails monolith plus React/TypeScript front-end, with Kafka as the messaging backbone. Per The Pragmatic Engineer's "How Shopify Built Its Live Globe for Black Friday" (BFCM 2024): "66M Kafka messages/sec at peak (!!)" and "$4.6M per minute: peak sales processed by the platform. This happened at midday EST on Black Friday (29 November)" and "284M edge requests per minute." Kafka serves: domain events (order created, product updated), ML inference workflows, search indexing, inventory tracking, customer notifications. Shopify's pattern is *event notification* combined with CDC-style state syncing — Kafka decouples producers from consumers so flash-sale traffic bursts don't synchronously block downstream services. Lesson: Kafka's value here is buffering and decoupling under spiky load, not stream processing per se.

**LINE / Naver — 150 billion messages per day at the messaging app scale.** LINE Corp (now LY Corporation after the 2023 Naver/Yahoo Japan merger) runs Kafka as the central event bus across 80+ internal services. Per Yuto Kawamura's "Building a company-wide data pipeline on Apache Kafka," Kafka Summit SF 2017 (SlideShare): slide 19 states "150 billion msgs / day (3 million msgs / sec)"; slide 7 states "Scale metric: Accumulated data (for analysis) 40PB." Their **Internal Message Flow (IMF)** project uses Kafka Streams to derive filtered downstream topics — consumers interested only in `ADD_CONTACT`/`BLOCK_CONTACT` events get a smaller stream — reducing network traffic. LINE also open-sourced **Decaton**, a high-throughput async task processing library on top of Kafka, used as their internal job queue. Lesson: the same Kafka primitive scales from your local docker-compose to messenger-app scale; the engineering investment shifts to broker tuning, custom client libraries, and topic filtering.

**Coupang — event-driven CQRS and tiered streaming for Korean e-commerce.** Per the Coupang Engineering blog post "Our backend strategy to handle massive traffic" (Gogi Du Hyeong Kim and Key Ki Hyeon Kim, Aug 2022), Coupang serves product detail pages to 18M+ customers via a **core serving layer** that fans events from microservices (Catalog, Pricing, Stock/Fulfillment) into a queue, materializing both a unified NoSQL store and a real-time cache; the post reports approximately 10× higher throughput from the cache layer and ~99.99% consistency between cache and storage on a minutes basis. The "Eats data platform: Empowering businesses with data" post describes **tiered pipelines** — batch, near-real-time (OLAP-engine on Kafka, 30 sec–1 hr cycles), and pure-real-time (Spark Streaming on Kafka) — used for flood detection and risk control. Lesson: the right consistency model depends on what data you're serving; mix tiers deliberately.

**Kakao Games — ksqlDB-based fraud detection.** Presented at Current 2022 in Austin and summarized in Kai Wähner's blog (Oct 2022), Kakao Games publishes MMORPGs from many third-party studios with heterogeneous log formats. Their Confluent-powered platform first standardizes those logs into uniform schemas via Kafka Connect, then runs **300+ ksqlDB patterns** for in-game fraud, including bonus abuse, multiple-account usage, account takeover, chargeback fraud, and affiliate fraud, with a ksqlDB UDF embedding a TensorFlow model for real-time fraud scoring. Lesson: ksqlDB is a sweet spot when the rules are SQL-shaped and you want to keep the rule catalog non-Java. Kakao Ads has separately published their **Genesis** platform (tech.kakao.com, April 2022) — a shared Kafka cluster with per-team Kafka Connect clusters — and open-sourced their kafka-sink-connector and kafka-connect-web management UI on GitHub.

**Banking/fintech — CQRS + Event Sourcing for regulatory auditability.** Banks like Barclays, Standard Chartered, and Société Générale have publicly adopted AxonIQ's Axon Framework for CQRS + event sourcing in transaction processing and account queries. The driver is regulatory: PCI DSS, PSD2, and audit/dispute resolution rules demand non-repudiable historical reconstruction of every state change. Albert Llousas's "Exploring event sourcing: A scalable bank account" (Medium, 2024) is a useful Kotlin/Hexagonal walkthrough specifically of a SEPA transfer event flow. Lesson: in regulated domains the audit/replay properties of event sourcing pay for the complexity; in unregulated domains they often don't.

---

## Anti-patterns to actively avoid (Kotlin/Spring Boot specific)

1. **Treating Kafka like a queue.** If you find yourself reaching for "ack-and-delete," "DLQ-then-retry-from-front," or per-message routing rules, you're fighting the log abstraction. Use SQS or RabbitMQ for true work-queue semantics.
2. **The passive-aggressive command.** An "event" whose name implies a recipient must do X (`SendWelcomeEmail`) is actually a command. Mislabeling it leaks coupling and breaks fan-out.
3. **Dual writes inside `@Transactional`.** A Spring `@Transactional` method that calls `kafkaTemplate.send()` does *not* roll back the Kafka publish on DB rollback. Use the outbox.
4. **Event spaghetti / distributed monolith.** When each event implicitly triggers a chain of 7 services and you can't reason about the global behavior, you've built a worse monolith. Document event flows; require service teams to publish AsyncAPI specs.
5. **Forgetting consumer idempotency.** At-least-once delivery + non-idempotent handlers = silent corruption. Always assume duplicates.
6. **Using `EmbeddedKafkaBroker` instead of Testcontainers.** The embedded broker has different config defaults and lifecycle quirks; you will catch fewer bugs. Use `org.testcontainers:kafka` with `KafkaContainer`.
7. **Letting Avro schemas drift via "let me just enable NONE compatibility for now."** Compatibility-NONE = no contract. Pick `BACKWARD` (the Registry default) and treat schema changes like API changes.
8. **One giant Kafka cluster for everything.** Netflix's ops team caps clusters at ~200 nodes; Uber federates around ~150-node clusters. As you grow, separate clusters by domain or by SLA tier (real-time-critical vs. analytics).
9. **Hiding behind Spring Cloud Stream's binder abstractions for production-critical paths.** Spring Cloud Stream is excellent for portability across brokers, but for a Kafka-committed shop you're hiding the very controls (partitioner, transactional producer, error handlers) you need to tune. Prefer Spring Kafka directly.
10. **Coroutines + `@KafkaListener` without thinking.** Spring Kafka's `@KafkaListener` runs on a dedicated thread; suspending in it without a bridge is a footgun. Use a `runBlocking` bridge or a coroutine adapter, and don't forget back-pressure.

## Testing strategies summary

- **Unit tests:** pure Kotlin tests of domain logic, event apply functions, and saga state machines. No Kafka.
- **Topology tests (Kafka Streams):** `TopologyTestDriver` for fast in-process testing of stream topologies.
- **Integration tests:** Testcontainers with `KafkaContainer` and `MySQLContainer` for end-to-end producer/consumer/projection tests. Use `Awaitility` for the async assertions.
- **Contract tests:** Schema Registry compatibility checks in CI on every PR (Confluent provides a Gradle/Maven plugin). For consumer-driven contracts, Pact has Kafka support; for simpler shops, schema-only contracts are often enough.
- **Chaos tests:** kill brokers / network-partition them with Toxiproxy or Chaos Mesh on Kubernetes to verify your consumers' rebalance behavior and your producers' retry/idempotence.

---

## Recommendations (staged, with the thresholds that change them)

**Now → next 4 weeks:** Execute the four projects exactly as scoped. Don't try to use Avro on Project 1 — the friction obscures the lesson. Add it deliberately on Project 2. Don't skip the outbox project: it is the single highest-ROI EDA pattern for your Aurora-MySQL stack and the one most likely to come up in your first real production migration.

**Week 5 / immediately after the month:** Pick one production-equivalent service at work and design the migration: identify the bounded context, the canonical events, the schema versioning policy, the read models, and the *consumer's* idempotency strategy. Document it as an ADR. If you don't have an obvious candidate, prototype the outbox pattern against your existing MySQL schema in a staging environment.

**Month 2:** Read Bellemare's 2nd edition end to end, Kleppmann's chapters 5/9/11, and pick **one** of Flink or Beam to spend a weekend on for context (most likely you won't deploy it, but knowing where Kafka Streams stops being enough is valuable). Skim *Streaming Systems* by Akidau/Chernyak/Lax for the theoretical underpinnings of watermarks and triggers.

**Month 3:** Stand up a Strimzi-based Kafka cluster on your team's Kubernetes environment with Schema Registry, Kafka Connect, and basic observability (Prometheus + Grafana, with alerts on under-replicated partitions and consumer lag). Run the four projects against it.

**Thresholds that change these recommendations:**
- If your domain is *not* high-throughput and *not* spiky and your services share a database, **don't migrate to EDA** — your reading list shifts to *Patterns of Enterprise Application Architecture* and modular monoliths (Spring Modulith).
- If you have hard real-time requirements with sub-100ms p99 and joins over multiple streams, **skip Kafka Streams and go straight to Flink**. The learning curve is steeper but the operational floor is higher.
- If your org is locked into AWS and ops capacity is the binding constraint, **MSK + Kinesis hybrid** (MSK for the event log, Kinesis Data Firehose for ingestion to S3) is a defensible choice; you'd swap Strimzi for MSK and most of the rest of the plan survives unchanged.
- If you find yourself implementing more than two saga orchestrators by hand, **adopt Axon Framework or Temporal** rather than continuing to hand-roll.

---

## "What to read next" — the post-month deep-dive shelf

1. Martin Kleppmann, *Designing Data-Intensive Applications* (full book, not just the chapters above). The single best book to grow into a distributed-systems architect.
2. Adam Bellemare, *Building an Event-Driven Data Mesh* (O'Reilly, 2023). The organizational extension once you have the technical pattern down.
3. Tyler Akidau, Slava Chernyak, Reuven Lax, *Streaming Systems* (O'Reilly, 2018). The theory of watermarks, triggers, and event-time correctness.
4. Bill Bejeck, *Kafka Streams in Action*, 2nd ed.
5. Vaughn Vernon, *Implementing Domain-Driven Design* and *Reactive Messaging Patterns with the Actor Model*.
6. Chris Richardson, *Microservices Patterns*. Sagas, outbox, and CQRS in pragmatic operational language.
7. Sam Newman, *Building Microservices*, 2nd ed. — for the surrounding organizational and process material.
8. Confluent's free "Event Sourcing and Event Storage with Apache Kafka" course on developer.confluent.io.
9. The Strimzi documentation end to end; the Debezium documentation, particularly the CDC and outbox sections.
10. Talks to bookmark: anything by Gunnar Morling (Debezium), Gwen Shapira (Confluent), Greg Young (event sourcing), Martin Kleppmann (turning the database inside out), and Yuto Kawamura (LINE Kafka at scale).

---

## Caveats

- **The case-study numbers come from public statements** by the named companies (Shopify's 66M msg/s peak per The Pragmatic Engineer BFCM 2024, Netflix's 2T msg/day and 4000+ brokers per Daxini's re:Invent 2017 slides, LINE's 150B msg/day and 40PB accumulated per Kawamura's Kafka Summit SF 2017 slides, Airbnb Riverbed's 2.4B events/350M docs daily per InfoQ Oct 2023). These are point-in-time peaks or averages reported in conference talks or engineering blog posts; treat them as orders-of-magnitude rather than current SLAs.
- **The Korean tech case studies vary in public disclosure.** Coupang and Kakao publish architectural patterns on their engineering blogs but rarely throughput numbers; LINE's Kawamura is the most detailed public source for Naver-group Kafka usage. A Kakao Pay public Cloudera case study mentions Apache NiFi rather than Kafka as the named streaming tool, so don't overgeneralize "Kafka everywhere in Korean fintech."
- **Spring Kafka vs. Spring Cloud Stream** is a religious debate in some shops. My opinionated recommendation is Spring Kafka for committed Kafka shops; Spring Cloud Stream is genuinely better when you need broker portability or for very simple producers/consumers.
- **The outbox pattern is not free.** It adds a table, a Debezium connector, and operational burden. For small systems with low write volume, polling the outbox in-app is simpler than running Debezium; for high write volume, log-based CDC dominates.
- **Event sourcing is over-engineering 80% of the time.** The default for most domains should be CRUD + domain events emitted via outbox, *not* a full event-sourced aggregate. Apply event sourcing where audit/replay/temporal queries are first-class requirements (finance, healthcare, multi-step workflows).
- **Kubernetes operationally is the hardest part of this plan.** If your team has not yet stabilized its k8s practice, run Kafka as a managed service (Confluent Cloud, AWS MSK, Aiven) for the first production rollout and revisit self-hosted Strimzi later.
- **The "exactly-once" claim in Kafka** holds *within* Kafka (between topics and processors using transactions). End-to-end EOS across an external sink (your MySQL projection, your email service) requires either the outbox/inbox pattern or robust idempotency keys. Don't believe marketing that elides this.