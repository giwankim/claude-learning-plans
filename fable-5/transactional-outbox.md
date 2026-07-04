---
title: "Mastering the Transactional Outbox Pattern with Kafka — A Sequenced Learning Path"
category: "Data & Messaging"
description: "A four-phase learning path (theory → interview depth → your stack → capstone, ~10–14 weeks part-time) treating the outbox pattern as the canonical solution to the dual-write problem and log-based CDC (Debezium) as the correct relay: delivery-semantics rigor (at-least-once with mandatory idempotent consumers, why Kafka EOS can't span DB↔broker), the polling-relay message-loss bug that commit-order log tailing structurally avoids, Aurora MySQL/MSK/EKS sharp edges, Korean and international production case studies (Woowahan, Gangnamunni, SeatGeek), and a SeatGeek-style multi-service capstone on Kotlin/Spring Boot + Debezium."
---

# Mastering the Transactional Outbox Pattern with Kafka — A Sequenced Learning Path

## TL;DR
- **This is a four-phase path (theory → interview depth → your stack → capstone), estimated at ~10–14 weeks of part-time study, that treats the outbox pattern as the canonical solution to the dual-write problem and log-based CDC (Debezium) as the correct relay for it.** Since you already know Kafka internals, Spring Kafka, and the `@TransactionalEventListener` phases, the path deliberately front-loads *correctness reasoning* and *tradeoffs*, then dives straight into Aurora MySQL/Debezium/EKS particulars.
- **The single most important formal insight** to anchor everything: the outbox pattern converts an impossible atomic dual-write (DB + broker) into a single local ACID transaction, giving *at-least-once delivery with eventual consistency* — never end-to-end exactly-once — so **idempotent consumers are mandatory, not optional**, and **polling relays have a subtle message-loss/ordering bug that log-based CDC structurally avoids** because the transaction log is in commit order.
- **Your capstone** is a multi-service commerce/ticketing domain (SeatGeek-style live-event inventory + orders + payments + notifications) on Kotlin/Spring Boot + Aurora MySQL + Debezium + MSK/EKS, built in progressive milestones from a single-service polling publisher up to a CDC-based, schema-governed, monitored, multi-aggregate system with saga choreography.

## Key Findings

1. **The pattern is well-canonized.** Chris Richardson's microservices.io defines the triad you should memorize: [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html), [Polling Publisher](https://microservices.io/patterns/data/polling-publisher.html), and [Transaction Log Tailing](https://microservices.io/patterns/data/transaction-log-tailing.html). Gunnar Morling's 2019 Debezium post [Reliable Microservices Data Exchange With the Outbox Pattern](https://debezium.io/blog/2019/02/19/reliable-microservices-data-exchange-with-the-outbox-pattern/) is the foundational engineering reference and the origin of the Debezium Outbox Event Router SMT.

2. **Delivery semantics are the theoretical core.** The outbox guarantees at-least-once; Kafka's exactly-once semantics (EOS) via idempotent producer + transactions is *Kafka-to-Kafka only* and does **not** solve DB↔broker atomicity. This distinction is the crux of many interview answers.

3. **Polling vs. CDC is not merely operational — it is a correctness difference.** A polling relay ordering by auto-increment ID or timestamp can *silently lose committed messages* because sequence values are assigned at insert time but rows become visible at commit time. Log-based CDC (Debezium) emits events in exact commit order and is structurally immune.

4. **Your stack has specific sharp edges:** Aurora MySQL binlog behavior (no global read lock → table-level locks for snapshots; binlog retention; the binlog-throughput history), MSK Connect's one-task-per-Debezium-connector limitation, and Spring's `@TransactionalEventListener(AFTER_COMMIT)` silently discarding DB writes made in the listener.

5. **Korean and international engineering blogs richly document real production usage** — Woowahan (배민), 강남언니 (Gangnamunni), RIDI, 29CM, Toss, and SK all have detailed writeups, alongside SeatGeek, Confluent, Red Hat/Debezium, and Decodable.

## Details

### Phase 0 — Baseline calibration (½ week)
You already have the Kafka internals, Spring Kafka, dual-write anti-pattern, `@TransactionalEventListener` phases, and some Woowahan delivery-architecture material. Skip Kafka basics. Use this half-week only to fix vocabulary and the mental model:
- Read microservices.io [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html), [Polling Publisher](https://microservices.io/patterns/data/polling-publisher.html), [Transaction Log Tailing](https://microservices.io/patterns/data/transaction-log-tailing.html) in one sitting. These three pages are short and define the shared language.
- Skim the AWS Prescriptive Guidance [Transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) page (also available in Korean) for the cloud-architecture framing you'll reuse on EKS.

### Phase 1 — Stack-agnostic theory & tradeoffs (2–3 weeks)

**1a. The dual-write problem & why the pattern exists.**
- Confluent, [Understanding the Dual-Write Problem and Its Solutions](https://www.confluent.io/blog/dual-write-problem/).
- Thorben Janssen, [Dual Writes — The Unknown Cause of Data Inconsistencies](https://thorben-janssen.com/dual-writes/).
- For a rigorous, engineer-level essay connecting it to distributed-transaction impossibility: [The Transactional Outbox Pattern: A Rigorous Examination for Distributed Systems Engineers](https://medium.com/@nustianrwp/the-transactional-outbox-pattern-a-rigorous-examination-for-distributed-systems-engineers-9c189836f470).

**1b. Delivery semantics — the formal spine (appeal to your rigor).**
- Oskar Dudycz, [Outbox, Inbox patterns and delivery guarantees explained](https://event-driven.io/en/outbox_inbox_patterns_and_delivery_guarantees_explained/): the clean at-most-once / at-least-once / exactly-once taxonomy.
- Kleppmann, *Designing Data-Intensive Applications*, **Ch. 11 (Stream Processing)** — message brokers, log-based vs. AMQP/JMS brokers, CDC, event sourcing, and the argument for deciding a single **total order** of writes and deriving all representations by processing in that order. This is the theoretical justification for preferring log-based CDC. ([O'Reilly](https://www.oreilly.com/library/view/designing-data-intensive-applications/9781491903063/ch11.html))
- Confluent EOS trilogy: [Exactly-once Semantics is Possible: Here's How](https://www.confluent.io/blog/exactly-once-semantics-are-possible-heres-how-apache-kafka-does-it/), [Transactions in Apache Kafka](https://www.confluent.io/blog/transactions-apache-kafka/), and the [Message Delivery Guarantees](https://docs.confluent.io/kafka/design/delivery-semantics.html) docs. **Key correctness invariant to internalize:** Kafka EOS covers the consume→process→produce loop *within Kafka*; it cannot make a MySQL commit and a Kafka publish atomic. The outbox is precisely the workaround for that gap.

**Correctness framing for the math-PhD learner.** State the invariant precisely: *Let S be the service's DB state and E the event stream. The outbox pattern guarantees that a state transition Tᵢ and its event Eᵢ are written in one local transaction, so `commit(Tᵢ) ⇔ durable(Eᵢ)`. The relay then guarantees `durable(Eᵢ) ⇒ eventually published(Eᵢ)` (at-least-once). Composed: `commit(Tᵢ) ⇒ eventually published(Eᵢ) ≥ 1 times`.* Exactly-once end-to-end is impossible without consumer-side idempotency because the "mark as published" step can fail after publish.

**1c. Polling publisher vs. transaction-log tailing (CDC) — with the ordering anomaly.**
This is the section to study most carefully; it is where formal reasoning pays off.
- **The anomaly (memorize this):** With a polling relay reading `WHERE position > last_processed ORDER BY position`, an auto-increment/sequence ID is *assigned at insert* but the row is *visible only at commit*. If Tx-C (id 13) commits before Tx-A (id 11) and Tx-B (id 12), the relay reads 13, advances its high-water mark to 13, and **never reads 11 and 12 after they commit** — silent message loss. Timestamps have the identical flaw.
- Primary source on the mechanism and a robust fix: Oskar Dudycz, [How Postgres sequences issues can impact your messaging guarantees](https://event-driven.io/en/ordering_in_postgres_outbox/). He explains that sequences "are evaluated before the transaction commit" and that "BIGSERIAL is just a syntactic sugar for the autogenerated Postgres sequence," so a rolled-back or still-in-flight transaction leaves gaps: "we may have messages out of order, we may have gaps in ordering." His fix adds a `transaction_id xid8` column and filters `AND transaction_id < pg_snapshot_xmin(pg_current_snapshot())` — an event is consumed only once no older transaction is still running, ordering/tracking by the gapless transaction id rather than the sequence position. (His general [Outbox/Inbox delivery-guarantees article](https://event-driven.io/en/outbox_inbox_patterns_and_delivery_guarantees_explained/) is the right intro but does *not* contain this specific anomaly — use the Postgres-ordering article for it.)
- **Why CDC is immune:** Morling/Decodable, [Revisiting the Outbox Pattern](https://www.decodable.co/blog/revisiting-the-outbox-pattern) (mirror: [morling.dev](https://www.morling.dev/blog/revisiting-the-outbox-pattern/)): "By tailing the database's transaction log … events are emitted in the exact same order as transactions were committed to the database, ensuring consistency between internal and external representation of the data." He also notes you "can't use a standard database sequence for creating that value, as you can't guarantee that it is going to be monotonically increasing for events created in multiple concurrent transactions" — use the log offset (Postgres LSN / MySQL binlog coordinates) instead. The Debezium blog [Five Advantages of Log-Based Change Data Capture](https://debezium.io/blog/2018/07/19/advantages-of-log-based-change-data-capture/) makes the same point: reading the log gives "the complete list of all data changes in their exact order of application," whereas polling "might miss intermediary data changes." Kleppmann is credited (in Morling's post) with first pointing out the outbox's poor ordering semantics.

**1d. CDC tool comparison.**
- Debezium (the de facto standard, Kafka Connect-based): [debezium.io docs](https://debezium.io/documentation/reference/stable/).
- Alternatives to know for interviews: **Maxwell** (MySQL-only, emits JSON to Kafka/Kinesis), **AWS DMS** (managed, broad sources, weaker event-shape control), **native / managed connectors** (Confluent Cloud MySQL CDC Source V2, which is Debezium under the hood), and **Debezium Server / Embedded Engine** (Debezium without a Kafka Connect cluster — can run inside a JVM app or stream to Kinesis/Pub/Sub/Pulsar). See the Debezium FAQ and connector docs; for the embedded/server modes see the Debezium docs and the Korean writeup at [hoing.io](https://hoing.io/archives/5285).

**1e. Alternatives to the outbox pattern (know when NOT to use it).**
- **Listen-to-yourself**: publish the event first, then consume your own event to mutate state. Confluent's [Listen to Yourself Pattern](https://developer.confluent.io/courses/microservices/the-listen-to-yourself-pattern/) course and [CodeOpinion's analysis](https://codeopinion.com/listen-to-yourself-pattern-is-it-an-alternative-to-the-outbox-pattern/). Oskar Dudycz argues it is mostly an anti-pattern for events (hard to get consistency; only workable for commands).
- **Event sourcing**: the event store *is* the source of truth, dissolving the dual write — but with big complexity (versioning, rehydration, read models). Debezium's [Event Sourcing vs. CDC](https://debezium.io/blog/2020/02/10/event-sourcing-vs-cdc/).
- **CDC directly on business tables** (no outbox table): simpler, but couples consumers to your internal schema and leaks deltas rather than domain events.
- **2PC/XA**: real but poorly supported by Kafka; kills availability/scalability. Note Kafka is gaining 2PC participation support — flagged as forward-looking in Morling's [Revisiting the Outbox Pattern](https://www.decodable.co/blog/revisiting-the-outbox-pattern).
- **Kafka transactions / "transactional messaging"**: Kafka-to-Kafka only, as above.
- Balanced tradeoff readings: [Stop overusing the outbox pattern](https://www.squer.io/blog/stop-overusing-the-outbox-pattern) (Squer) and [Outbox Pattern Survival Guide](https://medium.com/@tpierrain/outbox-pattern-survival-guide-6ad4b57ef189).

**1f. Idempotent consumers, ordering, and the inbox pattern.**
- Every source agrees: dedup on a stable event ID (UUID or per-producer monotonic sequence), typically via a processed-events/inbox table or an `ON CONFLICT DO NOTHING` upsert. The **inbox pattern** is the consumer-side mirror (see the Korean velog piece on 모놀리식→MSA and the Woowahan member-system post below).
- Per-aggregate ordering is preserved by using `aggregate_id` as the Kafka message key (same key → same partition). **Cross-aggregate ordering is deliberately not guaranteed** — this is correct, scalable behavior.

**Deliverable for Phase 1:** write a 2–3 page note proving the at-least-once invariant, the polling-loss anomaly, and why keying by `aggregate_id` gives per-entity order but not global order. This doubles as interview prep.

### Phase 2 — System-design & interview depth (1–2 weeks)

**Canonical references:**
- **Chris Richardson, *Microservices Patterns* (Manning)** — Ch. 3 (interprocess communication), the outbox/log-tailing patterns, and Saga. The 2nd edition MEAP is available. Pair with his [distributed data patterns bootcamp](https://microservices.io/).
- **Kleppmann, DDIA** — Ch. 7 (transactions), Ch. 11 (stream processing) as above.
- **Alex Xu, *System Design Interview* Vol. 1 & 2 / ByteByteGo** — for interview framing and the [framework for system design interviews](https://bytebytego.com/courses/system-design-interview/a-framework-for-system-design-interviews). Xu's material won't cover outbox deeply, but it teaches the *structure* (requirements → estimation → high-level → deep dive → wrap-up) into which you'll slot the pattern.

**How the pattern shows up in interviews & how to defend it.** When asked "how do you reliably publish an event when you write to the DB?", the expected arc is: (1) name the dual-write problem; (2) reject naive `save()` + `kafkaTemplate.send()`; (3) reject 2PC (unsupported by Kafka, availability cost); (4) propose the outbox; (5) choose the relay (polling vs. CDC) and *justify with the ordering argument*; (6) address at-least-once → idempotent consumers; (7) discuss table growth, ordering, and failure modes.

**Common follow-ups & edge cases to rehearse:**
- **Outbox table growth/cleanup**: TTL delete job, partition-by-date + drop partitions, or delete-on-publish. RIDI's two-part series is the best real account of the DB-performance consequences (deadlocks, lock waits, `SELECT ... FOR UPDATE` latency) — [part 1](https://ridicorp.com/story/transactional-outbox-pattern-ridi/), [part 2](https://ridicorp.com/story/transactional-outbox-message-relay-ridi/).
- **Duplicate handling**: idempotency keys, inbox table.
- **Ordering across partitions**: key by aggregate id; accept no global order.
- **Failure modes**: relay crash between publish and mark-published (→ redelivery); connector down (events buffered durably in the outbox/binlog); binlog purged before capture (→ forced re-snapshot).
- **Single-outbox-table hotspot**: SeatGeek's [Transactional Outbox Pattern](https://chairnerd.seatgeek.com/transactional-outbox-pattern/) documents lock contention and their per-aggregate/table-splitting mitigation. Uber's variant adds a global `sequence_number` for total ordering (with a latency cost).
- **7 hidden pitfalls**: the Medium "7 Hidden Pitfalls of Transaction Outbox" piece is a good checklist.

**Interview-defense blogs (int'l):** SeatGeek (above), [Streamkap outbox explainer](https://streamkap.com/resources-and-guides/outbox-pattern-explained), [Conduktor: Transactional Outbox](https://www.conduktor.io/blog/transactional-outbox-pattern-database-kafka). **InfoQ:** [Saga Orchestration for Microservices Using the Outbox Pattern](https://www.infoq.com/articles/saga-orchestration-outbox/) (Morling) ties outbox to Saga — a frequent senior-level follow-up.

**Deliverable:** a 45-minute mock answer to "Design a reliable order-placement pipeline across order/inventory/payment services," using the outbox + CDC, drawn on a whiteboard, with the tradeoff talk track.

### Phase 3 — Your stack: Kotlin + Spring Boot + Debezium + Aurora MySQL + EKS (3–4 weeks)

**3a. Kotlin + Spring Boot implementation & transactional boundaries.**
- **The `@TransactionalEventListener` trap** (you know the phases; here is the sharp edge): with the default `AFTER_COMMIT` phase, any DB write performed *inside the listener* is **silently discarded** unless you open a new transaction with `Propagation.REQUIRES_NEW`. Primary sources: Spring's own [javadoc warning](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/event/TransactionalEventListener.html) ("the transaction will have been committed already, but the transactional resources might still be active and accessible … changes will not be committed to the transactional resource"), the Spring Framework issue [#26974](https://github.com/spring-projects/spring-framework/issues/26974), and the deep mechanics writeup [Spring puzzler: the @TransactionalEventListener](https://softice.dev/posts/spring_puzzler_transactional_event_listener/). **Implication for outbox:** prefer writing the outbox row *synchronously within the same `@Transactional` service method* (not in an `AFTER_COMMIT` listener) so it shares the business transaction. If you use an event-listener approach, write the outbox row in `BEFORE_COMMIT`.
- Kotlin reference implementations to read and run:
  - [AleksK1NG/Transactional_Outbox_with_Spring_and_Kotlin](https://github.com/AleksK1NG/Transactional_Outbox_with_Spring_and_Kotlin) — Kotlin + WebFlux + R2DBC + Postgres/Mongo + Kafka + full observability (Grafana/Prometheus/Zipkin). Companion article: [DEV: Transactional Outbox step by step with Spring and Kotlin](https://dev.to/aleksk1ng/transactional-outbox-pattern-step-by-step-with-spring-and-kotlin-3gkd).
  - [nsteps/outbox](https://github.com/nsteps/outbox) — Kotlin + Kafka + Debezium Kafka Connect + Postgres, explicitly documenting transactional persistence + idempotent consumer guarantees.
  - [raedbh/spring-outbox](https://github.com/raedbh/spring-outbox) — Spring-native library with pre-built Debezium connectors for MySQL/Postgres/Mongo; good source-to-pay sample.
- Spring Kafka integration nuance: `KafkaTemplate` inside `@Transactional` is *not* rolled back with the DB transaction; `transactionIdPrefix` links Kafka's own transaction but still cannot make DB+Kafka atomic. This is exactly why you use the outbox. (See the Korean velog [트랜잭셔널 아웃박스 패턴](https://velog.io/@qwerty1434/%ED%8A%B8%EB%9E%9C%EC%9E%AD%EC%85%94%EB%84%90-%EC%95%84%EC%9B%83%EB%B0%95%EC%8A%A4-%ED%8C%A8%ED%84%B4) which demonstrates the rollback gap in code.)

**3b. Debezium Outbox Event Router SMT.**
- Official docs: [Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html). Key config: `transforms.outbox.type=io.debezium.transforms.outbox.EventRouter`, `route.by.field=aggregate_type`, `table.field.event.key=aggregate_id` (→ Kafka key → partition → per-aggregate order), `table.field.event.payload=payload`, `table.expand.json.payload=true`, `route.topic.replacement=${routedByValue}.events`.
- Confluent's [EventRouter SMT reference](https://docs.confluent.io/kafka-connectors/transforms/current/eventrouter.html).
- Runnable MySQL showcase: [kayroone/debezium-outbox-event-router-showcase](https://github.com/kayroone/debezium-outbox-event-router-showcase).
- If you were on Quarkus you'd use the [Outbox Quarkus Extension](https://debezium.io/documentation/reference/stable/integrations/outbox.html); on Spring, the equivalent ergonomics come from `raedbh/spring-outbox` or hand-rolling the outbox entity.

**3c. Debezium CDC on MySQL / Aurora MySQL — the specifics.**
- MySQL connector docs: [Debezium connector for MySQL](https://debezium.io/documentation/reference/stable/connectors/mysql.html). Requirements: `binlog_format=ROW`, a user with `SELECT, RELOAD, SHOW DATABASES, REPLICATION SLAVE, REPLICATION CLIENT`. The docs confirm the connector "completes different steps when it performs an initial snapshot that uses a global read lock or table-level locks" and provides a distinct "snapshot workflow for table-level locks … for environments that do not permit global read locks" — which is exactly Aurora's case, so you additionally grant `LOCK TABLES`.
- **Aurora-specific gotchas:**
  - Enable binlog via the DB cluster parameter group (`binlog_format=ROW`) and set a **binlog retention** of at least a few days (`mysql.rds_set_configuration('binlog retention hours', ...)`) — if the connector lags and the binlog is purged, you're forced into a fresh snapshot. See the [thedataguy Aurora snapshot writeup](https://thedataguy.in/debezium-mysql-snapshot-for-aws-rds-aurora-from-backup-snaphot/) and the Debezium MySQL troubleshooting notes at [sylhare.github.io](https://sylhare.github.io/2023/11/07/Debezium-configuration.html).
  - **Binlog throughput history**: Woowahan's CDC post warns that with **Aurora MySQL < 2.10.2**, the binlog dump thread briefly locks cluster storage and write-heavy workloads suffer. The relevant AWS fix is the **binlog I/O cache introduced in Aurora MySQL 2.10.0** (AWS release notes, 2021-05-25: "Introduced the binlog I/O cache to improve binlog performance by reducing contention between writer threads and dump threads"), which AWS's Database Blog reports "showed more than 5 times throughput improvement in a binlog-replicated setup"; the later **enhanced binlog in Aurora MySQL 3.03+** cut binlog overhead "which in certain cases can reach up to 50%, down to 13%." Primary Korean source on your exact stack: [CDC 너두 할 수 있어 (Woowahan)](https://techblog.woowahan.com/10000/) — also a Kotlin + Aurora MySQL + Debezium + Avro/Schema-Registry example.
  - Snapshot modes (`initial`, `when_needed`, `schema_only`, `never`) and Aurora snapshot-from-backup techniques matter for large tables.

**3d. Kafka Connect deployment on Kubernetes/EKS — three routes.**
- **MSK Connect (managed):** [AWS: Introducing Amazon MSK Connect](https://aws.amazon.com/blogs/aws/introducing-amazon-msk-connect-stream-data-to-and-from-your-apache-kafka-clusters-using-managed-connectors/) and the [Debezium source connector config-provider docs](https://docs.aws.amazon.com/msk/latest/developerguide/mkc-debeziumsource-connector-example.html). **Critical limitation, verbatim from AWS:** "The Debezium MySQL connector plugin supports only one task and does not work with autoscaled capacity mode for Amazon MSK Connect. You should instead use provisioned capacity mode and set workerCount equal to one." (The single-task constraint exists because MySQL binlog requires sequential processing; set both `workerCount=1` and `tasks.max=1`, or you'll hit `IllegalArgumentException: Only a single connector task may be started`.) Use AWS Secrets Manager config provider for DB creds. Sample: [aws-samples/aws-msk-cdc-data-pipeline-with-debezium](https://github.com/aws-samples/aws-msk-cdc-data-pipeline-with-debezium).
- **Self-managed Kafka Connect on EKS via Strimzi (recommended for iteration/control):** [Deploying Debezium on Kubernetes](https://debezium.io/documentation/reference/stable/operations/kubernetes.html), the Strimzi [KafkaConnector resource post](https://strimzi.io/blog/2020/01/27/deploying-debezium-with-kafkaconnector-resource/), and the GitOps writeup [InfoQ: Moving Kafka and Debezium to Kubernetes Using Strimzi](https://www.infoq.com/articles/strimzi-the-gitops-way/). Note Gary Stafford's practitioner opinion that MSK Connect is slow to iterate on during development and self-managed Connect on EKS is faster ([ITNEXT](https://itnext.io/building-data-lakes-on-aws-with-kafka-connect-debezium-apicurio-registry-and-apache-hudi-b4da0268dce)). A pragmatic pattern: self-managed Strimzi Connect in dev, MSK Connect in prod.
- **Debezium Embedded Engine / Debezium Server:** run the relay inside your Kotlin service (no Connect cluster) or as a standalone app. Good for avoiding a Connect cluster; you lose some Connect ecosystem tooling.

**3e. Schema management.**
- Confluent [Schema Registry](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html) supports Avro, Protobuf, JSON Schema. Learn the [compatibility modes](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html): the docs state "The Confluent Schema Registry default compatibility type is BACKWARD, not BACKWARD_TRANSITIVE … new schemas are checked for compatibility only against the latest schema." BACKWARD lets consumers on schema X read data written with X or X-1 but not necessarily X-2; **BACKWARD_TRANSITIVE** checks against *all* prior versions and is recommended with **Protobuf** since adding message types isn't forward-compatible. On AWS you can alternatively use **AWS Glue Schema Registry** (integrates with MSK Connect — see [AWS Big Data: end-to-end CDC with MSK Connect + Glue Schema Registry](https://aws.amazon.com/blogs/big-data/build-an-end-to-end-change-data-capture-with-amazon-msk-connect-and-aws-glue-schema-registry/)) or open-source **Apicurio**.
- The outbox `payload` can be JSON (with `table.expand.json.payload=true`) or Avro (serialize with `KafkaAvroSerializer`, use `ByteBufferConverter`). Morling's original post stresses that **the outbox event structure is part of your service's public API** and must evolve compatibly.

**3f. Monitoring & operations.**
- Debezium exposes JMX metrics; the critical one is **`MilliSecondsBehindSource`** (CDC lag). There's **no built-in dashboard** — you scrape JMX via the Prometheus JMX exporter and build Grafana dashboards. Primary: [Monitoring Debezium](https://debezium.io/documentation/reference/stable/operations/monitoring.html) and the [debezium-examples/monitoring](https://github.com/debezium/debezium-examples/blob/main/monitoring/README.md) stack. Honest limitations writeup: [Estuary: Debezium for CDC in Production — Pain Points](https://estuary.dev/blog/debezium-cdc-pain-points/) ("Debezium's 'MilliSecondsBehindSource' is a crucial metric … you must create a monitoring solution to utilize [the JMX metrics]").
- Snapshot vs. streaming metrics are separate MBeans; alert on lag, connector state (running/paused/failed), and outbox-table row count (RIDI monitors the time delta between message insert and processing and alerts via Slack/Datadog).
- Toss Securities' [large-scale CDC pipeline improvement post](https://www.velopers.kr/post/900) is an excellent ops-scaling case study, reporting that new-pipeline setup time was cut "from up to 12 hours to 1 hour, and scaling time to within 5 minutes."

### Korean engineering-blog reading list (production case studies)
- **우아한형제들 (Woowahan/배민):** [회원시스템 이벤트기반 아키텍처 구축하기](https://techblog.woowahan.com/7835/) (Spring application events + outbox + SNS/SQS) and [CDC 너두 할 수 있어](https://techblog.woowahan.com/10000/) (Kotlin + Aurora MySQL + Debezium + Avro).
- **강남언니 (Gangnamunni/힐링페이퍼):** [분산 시스템에서 메시지 안전하게 다루기](https://blog.gangnamunni.com/post/transactional-outbox) — clean at-least-once + exactly-once-processing framing.
- **RIDI:** two-part message-relay operations series (linked above) — the best Korean deep-dive on polling-relay DB performance tuning.
- **29CM (Greg Lee):** [트랜잭셔널 아웃박스 패턴의 실제 구현 사례](https://medium.com/@greg.shiny82/%ED%8A%B8%EB%9E%9C%EC%9E%AD%EC%85%94%EB%84%90-%EC%95%84%EC%9B%83%EB%B0%95%EC%8A%A4-%ED%8C%A8%ED%84%B4%EC%9D%98-%EC%8B%A4%EC%A0%9C-%EA%B5%AC%ED%98%84-%EC%82%AC%EB%A1%80-29cm-0f822fc23edb) — explicitly walks the four `@TransactionalEventListener` success/failure cases and why they chose outbox over CDC initially.
- **SK Devocean:** [SAGA, Transactional Outbox 패턴 활용하기](https://devocean.sk.com/blog/techBoardDetail.do?ID=165445).
- **Toss Securities:** CDC pipeline post (above).

### Phase 4 — Capstone: a fully fleshed-out complex domain (3–4 weeks)

**Domain:** a **live-event ticketing & commerce platform** ("SeatGeek-style"), chosen because it exercises the full stack, has real ordering/consistency stakes, and maps onto documented production usage. Services (each with its own Aurora MySQL schema + outbox table):
1. **Inventory/Catalog service** — events, sections, seat inventory; publishes `SeatHeld`, `SeatReleased`, `InventoryAdjusted`.
2. **Order service** — order lifecycle (`waiting → confirmed/cancelled`); publishes `OrderCreated`, `OrderConfirmed`, `OrderCancelled`.
3. **Payment service** — authorizes/captures; publishes `PaymentAuthorized`, `PaymentFailed`.
4. **Notification service** — pure consumer; demonstrates idempotent processing + inbox table.
5. **Read-model/search projection** — CQRS read side rebuilt from events.

Orchestrate order placement as a **choreographed saga** across order/inventory/payment (mirrors Richardson's Create-Order saga and Morling's InfoQ saga-via-outbox article), with compensation (release held seats on payment failure) — and use the outbox to make each local transition + its event atomic.

**Progressive milestones (each independently shippable):**
- **M0 — Single service, polling publisher.** Order service writes `orders` + `outbox` in one `@Transactional` method; a scheduled relay publishes and marks/deletes. Deliberately reproduce the ordering-loss anomaly under concurrent inserts, then fix it (transaction-id / snapshot-min approach). *Goal: feel the correctness bug yourself.*
- **M1 — Swap polling for Debezium CDC + Outbox Event Router.** Local docker-compose (Kafka in KRaft mode, MySQL, Kafka Connect). Verify per-aggregate ordering via `aggregate_id` keying. Reference: [YunusEmreNalbant/transactional-outbox-pattern-with-debezium](https://github.com/YunusEmreNalbant/transactional-outbox-pattern-with-debezium), [tugayesilyurt/spring-debezium-kafka-outbox-pattern](https://github.com/tugayesilyurt/spring-debezium-kafka-outbox-pattern).
- **M2 — Idempotent consumers + inbox.** Notification & inventory consumers dedup on event id; simulate redelivery and prove exactly-once *processing*.
- **M3 — Multi-service saga + compensation.** Add inventory/payment; choreograph; handle the out-of-order compensation timing issue (the "cancel before create" race documented in the SK Devocean and velog posts).
- **M4 — Schema governance.** Move payloads to Avro (or Protobuf) + Schema Registry; enforce BACKWARD compatibility; evolve one event schema without breaking consumers.
- **M5 — Move to Aurora MySQL + EKS.** Enable binlog on an Aurora cluster; deploy Kafka Connect via Strimzi on EKS (dev) and/or MSK Connect (prod, provisioned, `workerCount=1`, `tasks.max=1`, Secrets Manager); wire Prometheus/Grafana dashboards for `MilliSecondsBehindSource`, connector state, and outbox row count.
- **M6 — Operations & chaos.** Pause the connector and prove no event loss; purge/rotate binlog to force a re-snapshot and recover; add outbox cleanup (partition-drop or TTL); load-test and tune (RIDI-style lock-wait mitigation).

**Reference repos to model structure on:**
- Kotlin: [AleksK1NG/Transactional_Outbox_with_Spring_and_Kotlin](https://github.com/AleksK1NG/Transactional_Outbox_with_Spring_and_Kotlin), [nsteps/outbox](https://github.com/nsteps/outbox).
- Spring library: [raedbh/spring-outbox](https://github.com/raedbh/spring-outbox), [vincenzocorso/spring-outbox-example](https://github.com/vincenzocorso/spring-outbox-example).
- Debezium official [debezium-examples](https://github.com/debezium/debezium-examples) (outbox + monitoring).
- AWS: [aws-samples/aws-msk-cdc-data-pipeline-with-debezium](https://github.com/aws-samples/aws-msk-cdc-data-pipeline-with-debezium), [aws-msk-serverless-cdc-data-pipeline-with-debezium](https://github.com/aws-samples/aws-msk-serverless-cdc-data-pipeline-with-debezium).
- Browse [GitHub topic: outbox-pattern (Java/Kotlin)](https://github.com/topics/outbox-pattern?l=java) for more.

## Recommendations

**Sequence & effort (staged):**
1. **Weeks 1–3 (Theory):** Phase 0 + Phase 1. Benchmark to proceed: you can whiteboard the at-least-once invariant proof and explain the polling-loss anomaly and CDC's commit-order immunity from memory.
2. **Weeks 3–5 (Interview depth):** Phase 2. Benchmark: deliver a clean 45-min mock design of a reliable multi-service order pipeline, handling ≥5 follow-ups (growth, dedup, ordering, connector failure, saga compensation).
3. **Weeks 5–9 (Your stack):** Phase 3, reading the Kotlin repos and Woowahan/RIDI posts while standing up a local Debezium+MySQL+Kafka lab. Benchmark: a working single-service outbox with Debezium locally, per-aggregate ordering verified, `@TransactionalEventListener` pitfall consciously avoided.
4. **Weeks 9–14 (Capstone):** Phase 4 milestones M0→M6. Benchmark: M5 running on EKS/Aurora with lag dashboards; M6 chaos tests pass with zero event loss.

**Decision guidance you should adopt:**
- **Default to log-based CDC (Debezium), not polling**, unless operational simplicity strongly dominates and volume is low — and if you poll, implement the snapshot-min / transaction-id fix, never naive `ORDER BY id`.
- **Write the outbox row inside the business `@Transactional` method**, not in an `AFTER_COMMIT` listener, to avoid silent write loss.
- **Always ship idempotent consumers** (inbox/dedup) from day one; treat exactly-once-delivery as unattainable.
- **On AWS**: Strimzi-on-EKS for dev iteration, MSK Connect (provisioned, single worker, `tasks.max=1`) for prod; Aurora MySQL ≥ 2.10.2 (ideally 3.03+ enhanced binlog) with multi-day binlog retention.

**Thresholds that change the plan:**
- If your event volume is low and you have no other CDC need, a well-implemented polling relay (with the ordering fix) may be simpler than operating Debezium — revisit the CDC decision.
- If audit/history/time-travel is a first-class requirement, escalate from outbox to **event sourcing**.
- If the single outbox table becomes a write hotspot (lock contention, as SeatGeek hit), split per-aggregate or per-service and/or move cleanup to partition drops.

## Caveats
- **Version/pricing specifics drift.** MSK Connect's one-task Debezium limitation, Aurora's binlog-cache history (2.10.0 / 3.03 enhanced binlog), and Confluent/ByteByteGo course pricing are point-in-time facts (verified from 2021–2026 sources); re-check against current AWS/Confluent docs before committing architecture.
- **Two sources I flag as secondary/unverified:** Martin Kleppmann's original tweet on outbox ordering (attribution confirmed via Morling, tweet body not directly quoted here) and the exact DDIA Ch. 11 page wording (paraphrased from the chapter's total-order argument). Confirm against the originals if you need exact citations.
- **Some referenced posts are personal blogs / Medium** (e.g., the "rigorous examination," Florian Courouge's Netflix/Uber anecdotes). Their *architectural claims about specific companies* (e.g., "Netflix experienced 2h CDC lag," "Uber uses a global sequence_number") are secondhand and should be treated as illustrative, not authoritative — the primary SeatGeek and Woowahan/RIDI/Toss posts are first-party and more reliable.
- **Effort estimates assume part-time study** by a senior engineer already fluent in Kafka and Spring; full-time immersion compresses this to ~4–6 weeks.
- **The pattern is not free.** It adds a table, a relay, operational surface (connector lifecycle, lag, schema evolution), and latency. The consensus across sources: adopt it deliberately for mission-critical event publishing, not reflexively for every CRUD service.