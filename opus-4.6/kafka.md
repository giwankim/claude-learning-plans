---
title: "Mastering Apache Kafka"
category: "Distributed Systems / Messaging"
description: "6-month roadmap for Kotlin/Spring Boot developers covering Kafka architecture, Spring Kafka patterns, Kafka Streams, Schema Registry, monitoring, and CCDAK certification"
---

# The complete 6-month Apache Kafka mastery roadmap for Kotlin developers

**A senior Kotlin/Spring Boot developer can reach production-grade Kafka expertise in 24 weeks by following a structured progression from core architecture through stream processing and operational excellence.** This plan leverages your distributed systems background to accelerate past conceptual basics and focus on hands-on mastery. It prioritizes the resources with the highest signal-to-noise ratio — the majority of which are free — and builds toward the Confluent Certified Developer exam as a concrete milestone. Every phase includes a progressively complex project that you'll extend throughout the six months, culminating in a full event-driven microservice platform.

The Kafka ecosystem underwent a seismic shift in 2024–2025. **Kafka 4.0 (March 2025) fully removed ZooKeeper**, making KRaft the only metadata management mode. Tiered storage reached GA in Kafka 3.9. The KIP-848 consumer rebalance protocol — which eliminates stop-the-world pauses and delivers up to **20× faster rebalancing** — shipped as GA in 4.0. This plan incorporates all these changes and focuses on the current state of the art, not legacy patterns.

---

## Phase 1: Foundations and first production patterns (weeks 1–8)

This phase builds your mental model of Kafka's architecture while getting code running immediately. Your distributed systems background means you already understand consensus, replication, and partitioning conceptually — the goal here is to map those abstractions to Kafka's specific implementation and establish fluent Spring Kafka + Kotlin patterns.

### Weeks 1–2: Architecture and core concepts

**Learning objectives:** Understand brokers, topics, partitions, producers, consumers, consumer groups, offsets, and the commit log abstraction. Grasp KRaft mode (not ZooKeeper — skip all ZK material for new learning).

**Resources (in order):**
1. **Confluent Kafka 101** (free, 1h 16m at developer.confluent.io/courses/) — fast-paced overview taught by Confluent engineers. Complete all 16 modules including hands-on exercises.
2. **"Kafka: The Definitive Guide" 2nd edition**, chapters 1–6 — free from Confluent at confluent.io/resources/ebook/. Covers architecture, producers, consumers, and Kafka internals. Despite being published in 2021, the core architecture chapters remain accurate.
3. **"Designing Event-Driven Systems"** by Ben Stopford, chapters 1–5 — free from Confluent. Read for architectural philosophy; your distributed systems experience will make this fast.
4. **Confluent KRaft overview** at developer.confluent.io/learn/kraft/ — understand why ZooKeeper was removed and how KRaft's Raft-based consensus replaces it.

**Hands-on:** Install Kafka 4.0 locally using the official Docker image (`apache/kafka:4.0.0`). Use the CLI tools (`kafka-topics.sh`, `kafka-console-producer.sh`, `kafka-console-consumer.sh`) to create topics, produce messages, consume from different offsets, and observe consumer group behavior. Experiment with partition counts and observe how messages distribute.

### Weeks 3–4: Spring Kafka + Kotlin — your first producer and consumer

**Learning objectives:** Build idiomatic Kotlin producers and consumers with Spring Boot, understand `KafkaTemplate`, `@KafkaListener`, serialization/deserialization, and basic error handling.

**Resources:**
1. **Confluent's "Spring Framework and Apache Kafka"** course (free at developer.confluent.io/courses/) — covers Spring Kafka integration patterns.
2. **Spring Kafka official reference** (docs.spring.io/spring-kafka/reference/) — bookmark this; you'll reference it constantly. Read the Getting Started, Sending Messages, and Receiving Messages sections.
3. **Baeldung's "Apache Kafka with Kotlin"** (baeldung.com/kotlin/apache-kafka) and **Codersee's tutorial** (blog.codersee.com/apache-kafka-with-spring-boot-and-kotlin/) for Kotlin-specific patterns.

**Key Kotlin patterns to establish early:**

- Use `data class` for all message payloads with `jackson-module-kotlin` for JSON serialization (required — Jackson can't deserialize Kotlin data classes without it)
- Constructor injection for `KafkaTemplate` (avoid `lateinit var`)
- Configure `ErrorHandlingDeserializer` from day one to prevent poison-pill infinite loops
- Use Spring Boot 3.4+ with Spring Kafka 3.3.x (stable, supports Kafka 3.8/3.9 clients) or Spring Boot 4.0 with Spring Kafka 4.0.0 (supports Kafka 4.x clients)

**🔨 Project — Event-Driven Order System (Part 1):** Build a Spring Boot + Kotlin service with a REST API that accepts orders and publishes `OrderCreated` events to Kafka. Build a separate consumer service that reads these events and stores them in PostgreSQL. Use Kotlin data classes as message payloads, configure JSON serialization, and write your first integration test with Testcontainers.

### Weeks 5–6: Error handling, retries, and dead letter topics

**Learning objectives:** Master `DefaultErrorHandler`, `@RetryableTopic`, dead letter topics, and the combined blocking + non-blocking retry pattern.

**Resources:**
1. Spring Kafka error handling docs (docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html)
2. Spring Kafka non-blocking retries docs (docs.spring.io/spring-kafka/reference/retrytopic.html)

**Key patterns to implement:**

The `DefaultErrorHandler` is your primary mechanism. Configure it with a `DeadLetterPublishingRecoverer` and explicit non-retryable exception classification. For non-blocking retries, use `@RetryableTopic` with exponential backoff — this creates separate retry topics (`orders-retry-0`, `orders-retry-1`, `orders-dlt`) automatically. The most robust production pattern combines both: `DefaultErrorHandler` handles 2–3 fast blocking retries for transient failures, then `@RetryableTopic` handles longer non-blocking retries with backoff. Configure this via `RetryTopicConfigurationSupport.configureBlockingRetries()`. Since Spring Kafka 3.2, exception-based DLT routing lets you send different failure types to different dead letter topics.

**Common mistake to avoid:** Not classifying non-retryable exceptions. Validation errors, `DeserializationException`, and `MessageConversionException` should never be retried — they'll fail forever and waste resources. `DefaultErrorHandler` marks deserialization exceptions as non-retryable by default, but add your own domain-specific non-retryable exceptions explicitly.

**🔨 Project extension (Part 2):** Add retry and DLT handling to your Order System. Implement `@RetryableTopic` with 3 retry attempts and exponential backoff. Add a `@DltHandler` that logs failed messages and stores them in a `failed_orders` table for manual review. Simulate failures by throwing exceptions for specific order types.

### Weeks 7–8: Testing and transactions

**Learning objectives:** Write comprehensive tests with Testcontainers, understand Kafka transactions with `@Transactional`, and implement idempotent consumers.

**Testing approach:** Use **Testcontainers** (not EmbeddedKafka) for all integration tests. Testcontainers runs a real Kafka broker in Docker, eliminating subtle behavioral differences. Key setup patterns:

- Use `@ServiceConnection` (Spring Boot 3.1+) for automatic bootstrap server configuration
- Use the `apache/kafka-native` Docker image for faster startup
- Enable container reuse with `.withReuse(true)` to avoid restarting Kafka between test classes
- Always set `auto.offset.reset=earliest` in test consumer configuration
- Use Awaitility for async assertions: `await().atMost(10.seconds).until { ... }`

**Transactions:** The modern approach (post Spring Kafka 2.7) uses `KafkaTransactionManager` on the listener container and `@Transactional` for database operations — **do not use the deprecated `ChainedKafkaTransactionManager`**. Set `transactionIdPrefix` on `ProducerFactory` and ensure downstream consumers use `isolation.level=read_committed` (Spring Boot defaults to `read_uncommitted` — this is a common production bug).

**Idempotent consumers:** Since Kafka guarantees at-least-once delivery by default, your consumers must be idempotent. Use the record key + partition + offset as a deduplication key, store processed IDs in a database with `ON CONFLICT DO NOTHING`, and check before processing.

**🔨 Project extension (Part 3):** Add Testcontainers-based integration tests covering the happy path, retry scenarios, and DLT flow. Implement Kafka transactions so that order processing and database writes are atomic. Add idempotent consumer logic using a `processed_events` table with unique constraints on event IDs.

**Phase 1 milestone checklist:**
- ✅ Can explain Kafka architecture (brokers, partitions, replication, consumer groups, KRaft) from memory
- ✅ Built a working Spring Boot + Kotlin producer/consumer with JSON serialization
- ✅ Implemented retry topics, dead letter topics, and combined blocking/non-blocking retries
- ✅ Wrote integration tests with Testcontainers
- ✅ Implemented Kafka transactions and idempotent consumers
- ✅ Completed Confluent Kafka 101 course and read first 6 chapters of the Definitive Guide

---

## Phase 2: Internals, Streams, and operational foundations (weeks 9–16)

Phase 2 goes deep on Kafka internals, introduces Kafka Streams for stateful stream processing, and establishes operational monitoring. This is where your distributed systems background pays the largest dividends — you'll absorb replication protocols, consensus mechanisms, and exactly-once semantics faster than someone without that foundation.

### Weeks 9–10: Kafka internals deep dive

**Learning objectives:** Understand replication protocol (ISR, high watermark, leader epochs), log compaction, partition assignment, controller election in KRaft, and exactly-once semantics internals.

**Resources:**
1. **Confluent Kafka Internals course** (free, 2.5h at developer.confluent.io/courses/architecture/) — taught by Jun Rao (Kafka co-creator). Covers broker data plane, control plane, replication, compaction, transactions, and tiered storage. **This is the single most valuable resource for internals.**
2. **"Kafka: The Definitive Guide"**, chapters 7–11 — deep architecture, reliability guarantees, and exactly-once semantics.
3. **Confluent's "Exactly-once Semantics Are Possible"** blog post — explains how idempotent producers + transactions + consumer read-committed isolation achieve EOS.
4. **KIP-98 design document** (cwiki.apache.org) — the original exactly-once proposal. Dense but essential reading for understanding the transaction coordinator, producer IDs, and sequence numbers.
5. **faderskd's "Kafka replication deep dive"** (faderskd.github.io) — excellent walkthrough of ISR mechanics, high watermark advancement, and failure scenarios.

**Key concepts to internalize:**

**Replication and ISR:** Every partition has a leader and N-1 followers. The In-Sync Replica set (ISR) tracks followers that are caught up within `replica.lag.time.max.ms`. With `acks=all` and `min.insync.replicas=2` (on a replication factor of 3), a produce request succeeds only when 2 replicas acknowledge — guaranteeing data survives one broker failure. Kafka 4.0 introduces **Eligible Leader Replicas (ELR)** via KIP-966, a subset of ISR guaranteed to have complete data up to the high watermark, preventing data loss during leader election even further.

**Log compaction:** For compacted topics, Kafka retains the latest value per key rather than using time-based retention. The log cleaner thread periodically removes older records with duplicate keys while preserving the latest. Not supported with tiered storage. Use for changelog topics, state stores, and configuration topics.

**Exactly-once internals:** Three mechanisms work together: (1) idempotent producers use producer IDs + sequence numbers to deduplicate retries at the broker, (2) transactions group cross-partition writes into atomic units via a transaction coordinator, (3) consumers with `isolation.level=read_committed` only see committed transaction results. Kafka Streams wraps all this with `processing.guarantee=exactly_once_v2`.

### Weeks 11–12: Kafka Streams fundamentals

**Learning objectives:** Master KStream, KTable, GlobalKTable, stateless operations (filter, map, branch), stateful operations (aggregate, count, reduce), and windowing.

**Resources:**
1. **Confluent Kafka Streams 101** (free, 2h 17m) — covers all core abstractions with hands-on exercises.
2. **"Kafka Streams in Action" 2nd edition** by Bill Bejeck (Manning, May 2024) — the most current Kafka Streams book, written by an Apache Kafka committer. Covers Spring Kafka integration in Chapter 12, which is rare and valuable.
3. **"Mastering Kafka Streams and ksqlDB"** by Mitch Seymour (O'Reilly, 2021) — still relevant for core concepts. The GitHub repo (github.com/mitch-seymour/mastering-kafka-streams-and-ksqldb) has working code examples. Note: the ksqlDB content is increasingly outdated given Confluent's strategic shift to Flink.

**Core abstractions:**

- **KStream** — unbounded, append-only event stream. Each record is an independent event. Think of it as an infinite changelog.
- **KTable** — changelog stream representing current state per key. Each record is an upsert. Think of it as a materialized view.
- **GlobalKTable** — fully replicated KTable on every Streams instance. Use for small lookup datasets (e.g., country codes, configuration). Not partitioned.

**Windowing types** (critical for aggregation):

- **Tumbling:** Fixed-size, non-overlapping (e.g., every 5 minutes). Use for periodic reports.
- **Hopping:** Fixed-size, overlapping (e.g., 5-minute window advancing every 1 minute). Use for smoothed aggregations.
- **Session:** Dynamic windows grouped by activity with an inactivity gap. Use for user session analytics.
- **Sliding:** Time-difference based, used specifically for stream-stream joins.

**🔨 Project — Real-Time Analytics Dashboard (Part 1):** Build a Kafka Streams application in Kotlin that consumes `OrderCreated` events from your Phase 1 project. Implement: (1) a KTable counting orders per product category using tumbling windows, (2) a stream-table join enriching orders with customer data from a GlobalKTable, (3) output enriched and aggregated results to new topics. Use `TopologyTestDriver` for unit testing the topology without a running cluster.

### Weeks 13–14: Kafka Streams advanced — joins, state stores, and EOS

**Learning objectives:** Implement all join types (stream-stream, stream-table, table-table), understand RocksDB state stores and changelog topics, configure interactive queries, and enable exactly-once in Streams.

**Join types and when to use them:**

| Join type | Windowed? | Use case |
|-----------|-----------|----------|
| Stream-Stream | Yes (requires time window) | Correlating events from two streams within a time window (e.g., matching orders with payments) |
| Stream-Table | No | Enriching a stream with lookup data (e.g., joining orders with customer profiles) |
| Table-Table | No | Joining two slowly-changing datasets (e.g., user preferences with account settings) |

**State stores:** Kafka Streams uses **RocksDB** by default for local state. State is automatically backed up via changelog topics in Kafka. Key operational concern: large state stores take significant time to restore after crashes. Mitigate with `num.standby.replicas=1` to maintain hot standby copies on other instances.

**Interactive queries** turn your Streams app into a queryable microservice — expose local state store contents via REST endpoints using `KafkaStreams.store()`. In Spring, use `KafkaStreamsInteractiveQuerySupport` (available since Spring Kafka 3.2).

**🔨 Project extension (Part 2):** Add a stream-stream join to your analytics app that matches orders with payment events within a 30-minute window. Implement interactive queries exposing the running order count per category via a REST endpoint. Enable exactly-once with `processing.guarantee=exactly_once_v2`.

### Weeks 15–16: Operational foundations — monitoring and Schema Registry

**Learning objectives:** Set up Prometheus + Grafana monitoring, implement consumer lag alerting, and integrate Confluent Schema Registry with Avro serialization.

**Monitoring stack setup:**
Deploy JMX Exporter as a Java agent on each broker, configure Prometheus to scrape metrics every 15 seconds, and import Confluent's pre-built Grafana dashboards from the `confluentinc/jmx-monitoring-stacks` GitHub repo. The **15 critical metrics** to monitor from day one: `UnderReplicatedPartitions`, `OfflinePartitionsCount`, `ActiveControllerCount`, `MessagesInPerSec`, `BytesInPerSec/BytesOutPerSec`, `RequestLatencyMs` (Produce/Fetch), ISR shrink/expand rates, consumer lag per partition, JVM heap usage, and GC pause time.

For consumer lag specifically, deploy **Kafka Lag Exporter** (by seglo) which estimates lag in seconds rather than just offset difference — time-based lag is far more actionable for alerting.

**Schema Registry:** Switch from JSON to **Avro** serialization with Confluent Schema Registry. Use **BACKWARD compatibility** (the default) — this allows adding fields with defaults and removing fields, and lets consumers rewind to any point in the topic. Set `auto.register.schemas=false` in production and register schemas in your CI/CD pipeline to prevent accidental incompatible changes.

**🔨 Project extension (Part 3):** Migrate your Order System from JSON to Avro serialization with Schema Registry. Add a `v2` schema that adds an `orderSource` field with a default value and verify backward compatibility. Set up a Docker Compose stack with Prometheus, Grafana, and JMX Exporter monitoring your Kafka cluster. Create Grafana alerts for under-replicated partitions and consumer lag exceeding 60 seconds.

**Phase 2 milestone checklist:**
- ✅ Can whiteboard the replication protocol, ISR mechanics, and exactly-once semantics from memory
- ✅ Built a Kafka Streams application with windowed aggregations, joins, and interactive queries
- ✅ Set up Prometheus + Grafana monitoring with consumer lag alerting
- ✅ Integrated Schema Registry with Avro and tested schema evolution
- ✅ Completed Confluent Kafka Internals course and Kafka Streams 101
- ✅ Read "Kafka Streams in Action" 2nd edition

---

## Phase 3: Advanced mastery and certification (weeks 17–24)

Phase 3 pushes into production-grade operational excellence, advanced stream processing patterns, and certification. By now you have a solid mental model and working code — this phase stress-tests your knowledge against real production scenarios.

### Weeks 17–18: Advanced Spring Kafka patterns and Kotlin features

**Learning objectives:** Master batch listeners, concurrency tuning, Kotlin suspend functions with `@KafkaListener`, and advanced producer patterns.

**Batch listeners** process multiple records per `poll()` call, dramatically improving throughput for high-volume topics. Set `isBatchListener = true` on `ConcurrentKafkaListenerContainerFactory`, tune `max.poll.records` (default 500), and handle errors by throwing `BatchListenerFailedException` with the index of the failed record. Spring Kafka 4.0 adds per-record observations in batch listeners for fine-grained tracing.

**Concurrency tuning:** Set `concurrency` on `@KafkaListener` or `ConcurrentKafkaListenerContainerFactory` to control the number of consumer threads. **Concurrency should never exceed your partition count** — excess threads sit idle. Each concurrent thread creates one consumer in the consumer group. For most workloads under 100K messages/hour, 3–10 partitions with matching concurrency suffices. Prefer horizontal scaling (multiple instances) over very high per-instance concurrency.

**Kotlin suspend functions** (since Spring Kafka 3.2) allow `@KafkaListener` methods to be suspend functions, enabling coroutine-based async processing. The framework automatically sets AckMode to MANUAL and handles out-of-order commits. However, understand the limitation: suspend functions are bridged to `CompletableFuture` internally — this isn't true coroutine parallelism within the listener container. For truly non-blocking I/O, consider **virtual threads** (Project Loom on Java 21+) which Spring Boot 3.2+ supports natively.

**Spring Kafka 4.0 notable features:** Share consumer support via `@ShareKafkaListener` (KIP-932 queues, preview), Jackson 3 auto-detection, Spring Framework 7's core retry replacing Spring Retry dependency, and `EmbeddedKafkaKraftBroker` only (ZK broker removed from tests).

**🔨 Project — High-Throughput Event Pipeline:** Build a batch listener that processes clickstream events at 10K+ events/second. Implement concurrency tuning to maximize throughput. Add a Kotlin suspend function listener for a low-volume topic that performs async enrichment calls. Benchmark throughput with different `batch.size`, `linger.ms`, and `compression.type` settings.

### Weeks 19–20: Performance tuning and advanced operational patterns

**Learning objectives:** Tune producer, consumer, and broker configurations for production workloads. Master partition rebalancing strategies and cluster management.

**Producer tuning essentials:**

| Parameter | Default | Production recommendation |
|-----------|---------|--------------------------|
| `batch.size` | 16KB | 32–64KB for throughput |
| `linger.ms` | 0 | 5–50ms (trade latency for throughput) |
| `compression.type` | none | `lz4` (balanced) or `zstd` (best ratio) |
| `acks` | all | Keep `all` for durability |
| `buffer.memory` | 32MB | Increase for high-throughput producers |

**Consumer tuning:** Increase `fetch.min.bytes` (1KB–64KB) to reduce fetch requests. Set `max.poll.interval.ms` based on your actual processing time — the default 300 seconds is generous but setting it too low causes spurious rebalances during slow processing.

**Partition rebalancing:** Use **`CooperativeStickyAssignor`** for all deployments — it enables incremental rebalancing where only affected partitions are revoked, while all other consumers continue processing. The old eager protocols cause stop-the-world pauses. For Kubernetes deployments, combine with **static group membership** (set `group.instance.id` to the StatefulSet pod name) to eliminate rebalances during rolling restarts.

**The KIP-848 new consumer protocol** (GA in Kafka 4.0) moves coordination entirely to the broker, eliminating client-side assignment computation. Opt in with `group.protocol=consumer`. In benchmarks, adding 900 partitions to a 10-consumer group dropped from **~103 seconds to ~5 seconds**. This will become the default in Kafka 5.0.

### Weeks 21–22: Stream processing at scale and the Flink question

**Learning objectives:** Evaluate ksqlDB vs Flink for stream processing, implement complex streaming patterns, and understand tiered storage.

**The ksqlDB situation is important context.** ksqlDB is still available in Confluent Platform and Confluent Cloud, but Confluent acquired Immerok (a Flink company) in 2023 and has since positioned **Apache Flink as its strategic stream processing engine**. ksqlDB's GitHub activity has hit record lows. For new projects, the industry is moving toward Flink SQL. However, **Kafka Streams (the Java/Kotlin library)** remains excellent, fully Apache-licensed, and actively developed — KIP-1034 added native DLQ support, and KIP-1071 brings the new rebalance protocol to Streams.

**Recommendation:** Learn Kafka Streams deeply (it's part of the Kafka project and has no license concerns). Learn ksqlDB basics for awareness (1–2 days). Invest in Flink SQL if your organization needs managed stream processing beyond what Kafka Streams offers.

**Tiered storage** (GA in Kafka 3.9) separates hot data on local SSDs from cold data on object storage (S3, GCS, Azure Blob). Configure per-topic with `remote.storage.enable=true`, `local.retention.ms` for how long to keep data locally, and `retention.ms` for total retention. Real-time consumers read from local tier (millisecond latency); historical replays read from remote tier (second-level latency). Not supported for compacted topics.

**🔨 Project — Streaming Fraud Detection System:** Build a Kafka Streams application that detects potentially fraudulent patterns: (1) multiple failed payment attempts within a 5-minute session window, (2) orders from new accounts exceeding a threshold within 1 hour (tumbling window aggregation), (3) geographic anomalies by joining the order stream with a customer location GlobalKTable. Output fraud alerts to a dedicated topic. Implement a dead letter queue for records that fail processing (using KIP-1034 if on Kafka 4.1+ or manual implementation otherwise). Deploy with `exactly_once_v2` and standby replicas.

### Weeks 23–24: Certification prep and capstone

**Learning objectives:** Pass the Confluent Fundamentals Accreditation, prepare for CCDAK, and complete a production-grade capstone project.

**Certification path:**

1. **Confluent Fundamentals Accreditation** (FREE, 30 questions, 60 minutes, not proctored) — take this first as a confidence check. Available at confluent.io/certification/.
2. **Confluent Certified Developer for Apache Kafka (CCDAK)** — $150, 60 questions, 90 minutes, 70% passing score, proctored. Covers architecture, producers/consumers, Kafka Streams, Connect, Schema Registry, ksqlDB basics, and security. Valid for 2 years.

**CCDAK preparation resources:**

- Stéphane Maarek's CCDAK Practice Tests on Udemy (150 sample questions, ~$12 on sale)
- Review all Confluent free courses (Kafka 101, Streams 101, Connect 101, Schema Registry 101)
- Re-read key chapters of "Kafka: The Definitive Guide" focusing on configuration details
- Focus areas where developers commonly struggle: exact default values for producer/consumer configs, Kafka Streams exactly-once guarantees, Connect converter vs. serializer distinction, Schema Registry compatibility modes

**🔨 Capstone Project — Event-Driven Microservice Platform:** Integrate everything into a complete platform:

- **3+ microservices** communicating via Kafka events (Order Service, Payment Service, Notification Service)
- **Avro schemas** with Schema Registry and BACKWARD compatibility
- **Kafka Streams** analytics service with windowed aggregations, joins, and interactive queries
- **Full error handling** with combined blocking/non-blocking retries and dead letter topics
- **Exactly-once semantics** with Kafka transactions for the order→payment flow
- **Testcontainers** integration tests for all services
- **Prometheus + Grafana** monitoring with consumer lag alerting
- **CooperativeStickyAssignor** and static group membership configuration
- **Batch listeners** for the high-volume clickstream ingestion service
- **Docker Compose** for the complete stack including Kafka (KRaft mode), Schema Registry, Prometheus, and Grafana

**Phase 3 milestone checklist:**
- ✅ Passed Confluent Fundamentals Accreditation
- ✅ Prepared for and scheduled CCDAK exam
- ✅ Built and deployed a multi-service event-driven platform
- ✅ Can tune producer, consumer, and broker configurations for specific workload profiles
- ✅ Understands the Kafka Streams vs ksqlDB vs Flink landscape and can make informed architectural decisions
- ✅ Implemented monitoring, alerting, and schema evolution in a realistic environment

---

## Essential resource list, ranked by impact

**Books (read in this order):**

| Book | Author | Year | Cost | When to read |
|------|--------|------|------|-------------|
| "Kafka: The Definitive Guide" 2nd ed | Shapira, Palino, Sivaram, Petty | 2021 | **Free** from Confluent | Weeks 1–8 |
| "Designing Event-Driven Systems" | Ben Stopford | 2018 | **Free** from Confluent | Weeks 1–2 |
| "Kafka Streams in Action" 2nd ed | Bill Bejeck | 2024 | ~$45 | Weeks 11–14 |
| "Apache Kafka in Action" | Zelenin & Kropp | 2025 | ~$50 | Weeks 15–20 |

**Online courses (all recommended, in learning order):**

| Course | Platform | Cost | Duration |
|--------|----------|------|----------|
| Kafka 101 | Confluent Developer | **Free** | 1h 16m |
| Kafka Internals | Confluent Developer | **Free** | 2h 30m |
| Kafka Streams 101 | Confluent Developer | **Free** | 2h 17m |
| Schema Registry 101 | Confluent Developer | **Free** | 41m |
| Spring Framework and Apache Kafka | Confluent Developer | **Free** | ~1h |
| Apache Kafka for Beginners v3 | Udemy (Maarek) | ~$15 | 8h+ |
| Kafka Streams for Data Processing | Udemy (Maarek) | ~$15 | 5h+ |
| CCDAK Practice Tests | Udemy (Maarek) | ~$15 | 150 questions |

**Total cost for the entire plan: approximately $140–290** (1–2 books at full price + 2–3 Udemy courses on sale + $150 CCDAK exam). The free resources alone cover roughly 70% of the curriculum.

---

## Anti-patterns and mistakes to avoid at each phase

**Phase 1 mistakes** (the "getting started" traps):
Not configuring `ErrorHandlingDeserializer` leads to poison-pill infinite loops where a single malformed message blocks the entire partition. Not setting `min.insync.replicas=2` with `acks=all` means your "durable" writes only require one replica. Forgetting `jackson-module-kotlin` causes silent deserialization failures with Kotlin data classes. Using `auto.offset.reset=latest` in tests causes missed messages.

**Phase 2 mistakes** (the "intermediate" traps):
Treating Kafka as a database by disabling retention for permanent storage. Over-partitioning "just in case" — each partition adds metadata overhead, slows leader elections, and increases rebalance time. Sending messages larger than 1MB without using the claim-check pattern. Not making consumers idempotent and assuming exactly-once delivery at the application level. Setting `segment.ms` too low, causing excessive log segment rolling.

**Phase 3 mistakes** (the "production" traps):
Running the old eager rebalance protocol when CooperativeStickyAssignor is available. Not setting `group.instance.id` for Kubernetes deployments, causing unnecessary rebalances during rolling restarts. Using `isolation.level=read_uncommitted` (the default!) when consuming from topics written by transactional producers. Not monitoring ISR shrinkage and consumer lag trends before they become incidents. Setting `auto.register.schemas=true` in production, allowing any producer to push incompatible schema changes.

---

## What's next after six months

By week 24, you'll have production-grade Kafka expertise covering architecture, Spring Kafka + Kotlin patterns, Kafka Streams, and operational monitoring. The natural next steps are: **pass the CCDAK exam** (you'll be well-prepared), **explore Apache Flink SQL** through Confluent's free Flink 101 and Flink SQL courses (4+ hours each) if your team needs managed stream processing beyond Kafka Streams, and **contribute to or build an internal Kafka platform** at your organization incorporating the patterns from your capstone project. The "Apache Kafka in Action" (2025) book is particularly valuable for this stage as it covers production cluster management, disaster recovery, and reference architectures that map directly to real operational scenarios.