---
title: "Spring for Apache Kafka Curriculum — Senior Kotlin/Spring Boot Engineer"
category: "Spring & Spring Boot"
description: "A rigorous, resource-mapped curriculum for an engineer who already knows Kafka's broker model: focuses on the Spring abstractions (KafkaTemplate, @KafkaListener, listener-container/factory model, DefaultErrorHandler/@RetryableTopic non-blocking retries, KafkaTransactionManager EOS, Kafka Streams, Micrometer observation, spring-kafka-test/Testcontainers), pins versions against Spring for Apache Kafka 4.0 GA (Kafka client 4.0, Spring Boot 4, Framework 7) with 3.3.x fallback, and curates the best Java-only sources to transpose into Kotlin."
---

# A Rigorous Spring for Apache Kafka Curriculum for the Senior Kotlin/Spring Boot Engineer

## TL;DR
- The fastest path to productivity is the official **Spring for Apache Kafka reference docs** plus the free **Confluent Developer "Spring Framework and Apache Kafka" course** (instructor Viktor Gamov) and the **Apache Kafka + Spring Boot getting-started tutorial** — but every one of these is Java-only, so you must mentally transpose to Kotlin idioms (trivial for you).
- Because you already own Kafka's broker-level model, the entire payoff is in the *Spring abstractions*: `KafkaTemplate`, `@KafkaListener`, the listener-container/factory model, `DefaultErrorHandler`/`@RetryableTopic` non-blocking retries, `KafkaTransactionManager` for read-process-write EOS, the Kafka Streams `StreamsBuilderFactoryBean`, Micrometer observation, and `spring-kafka-test`/Testcontainers.
- Use the current GA line: **Spring for Apache Kafka 4.0**, which "reach[ed] general availability in November 2025" after an 8-month, five-milestone development cycle (Spring blog, Soby Chacko, Nov 18 2025), on Kafka client 4.0 / Spring Boot 4 / Spring Framework 7 — note the breaking changes (Spring Retry removed, Jackson 3 default, KRaft-only EmbeddedKafka, KIP-848 support). If you are on Spring Boot 3.x, stay on the **3.3.x** line.

## Key Findings
- **spring-kafka is a thin, opinionated façade.** Spring Boot autoconfiguration builds `ProducerFactory`, `ConsumerFactory`, `KafkaTemplate`, and a `ConcurrentKafkaListenerContainerFactory` from `spring.kafka.*` properties. Your learning is mostly about *which beans get built for you and how to override them*, not Kafka semantics.
- **Kotlin is a first-class citizen but unevenly documented.** The reference docs show Kotlin snippets in the Quick Tour, and spring-kafka 4.0 ships JSpecify null-safety + Kotlin 2.x support, and even fixed `DefaultErrorHandler` to work with Kotlin `suspend` listener methods (issue #3618). But nearly all courses, tutorials, and conference repos are Java. You will be translating constantly.
- **Version landscape matters.** spring-kafka 4.0 GA tracks Apache Kafka client 4.0.0 (ZooKeeper fully removed, KRaft-only), supports the KIP-848 next-gen consumer rebalance protocol, and brings KIP-932 "queues"/share consumers as early-access. The 4.1.x line continues: "Spring for Apache Kafka 4.1.0-M2 is the first release built on Apache Kafka client 4.2.0… including improvements to the share consumer (KIP-932: Queues for Kafka) support" (Spring blog, Mar 17 2026). 3.3.x remains the Boot 3.5 line.
- **The richest production-grade blog corpus** is Lydtech Consulting (Rob Golder), Piotr Minkowski, Confluent Developer/blog (incl. the Kotlin-specific "Spring (Kotlin) with Confluent" series by Sandon Jacobs), Baeldung's spring-kafka series, and Reflectoring. spring-kafka's own committers (Gary Russell — project lead since he "started the Spring for Apache Kafka project in 2016"; Artem Bilan) are best consulted via the reference docs and Stack Overflow.

## Details

### Versioning & environment baseline (read this first)
- **spring-kafka 4.0.0 GA** — integrated into Spring Boot 4.0. Built on Apache Kafka client 4.0.0; Spring Framework 7; Java 17+ baseline. Breaking changes you must know:
  - **Spring Retry dependency removed** in favor of Spring Framework 7 core retry. Per the reference "What's new": "the annotation has been moved to Spring Kafka as `@BackOff`… Harmonized naming: Uses `@BackOff` instead of `@Backoff`… Expression evaluation: All string attributes support SpEL expressions and property placeholders; Duration format support: String attributes accept `java.util.Duration` formats (e.g., '2s', '500ms')."
  - **Jackson 3** is auto-detected and preferred ("Jackson 3 is automatically detected and preferred when available… `JacksonJsonSerializer`/`Deserializer` replaces `JsonSerializer`/`Deserializer`"; RC1 upgraded to Jackson 3.0.0 GA). Jackson 2 classes deprecated but functional.
  - **EmbeddedKafka is KRaft-only**; `EmbeddedKafkaZKBroker`/`EmbeddedKafkaRule` removed, `@EmbeddedKafka` simplified.
  - **KIP-848** new consumer rebalance protocol supported.
  - **KIP-932 queues / share consumers** are early-access/experimental.
- If you remain on **Spring Boot 3.x**, use **spring-kafka 3.3.x** (3.3.x integrates into Boot 3.5). This keeps Spring Retry-based `@Backoff`, Jackson 2, and the classic rebalance protocol by default.
- For the curriculum below I assume Kotlin 2.x, Gradle Kotlin DSL, JDK 21, and Kafka running via Docker Compose or Testcontainers.

### 1) Quick Overview Path — "get productive fast"

Goal: a running Kotlin producer/consumer with JSON-serialized data classes inside an afternoon. Suggested order:

1. **Read the Quick Tour** of the reference docs: https://docs.spring.io/spring-kafka/reference/ — it already contains a Kotlin `@KafkaListener` example.
2. **Do the Confluent getting-started tutorial**: https://developer.confluent.io/get-started/spring-boot/ (Java, ~30 min; transpose to Kotlin). Free; new Confluent Cloud signups can use promo code `CONFLUENTDEV1` to skip the credit card, or run Kafka locally.
3. **Skim the Baeldung "Intro to Apache Kafka with Spring"**: https://www.baeldung.com/spring-kafka (Java; canonical reference for the bean wiring).
4. **Watch/skim the free Confluent course** "Spring Framework and Apache Kafka": https://developer.confluent.io/courses/spring/ (Viktor Gamov; 13 lessons covering autoconfig, KafkaTemplate, @KafkaListener, TopicBuilder, Kafka Streams, Schema Registry).

Core concepts and the minimal Kotlin code:

**`build.gradle.kts`**
```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter")
    implementation("org.springframework.kafka:spring-kafka")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    testImplementation("org.springframework.kafka:spring-kafka-test")
}
```

**`application.yml` essentials**
```yaml
spring:
  kafka:
    bootstrap-servers: localhost:9092
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.springframework.kafka.support.serializer.JsonSerializer
    consumer:
      group-id: orders
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.JsonDeserializer
      properties:
        spring.json.trusted.packages: "com.acme.events"
```

**Event as a Kotlin data class + producer + consumer**
```kotlin
data class OrderCreated(val orderId: String, val amount: BigDecimal, val sku: String)

@Component
class OrderProducer(private val template: KafkaTemplate<String, OrderCreated>) {
    fun emit(e: OrderCreated) = template.send("orders.created", e.orderId, e)
}

@Component
class OrderConsumer {
    @KafkaListener(id = "orders", topics = ["orders.created"])
    fun on(event: OrderCreated) { /* business logic */ }
}

@Configuration
class Topics {
    @Bean fun ordersTopic() = TopicBuilder.name("orders.created").partitions(6).replicas(3).build()
}
```

Key mental model: Spring Boot autoconfigures `ProducerFactory`/`ConsumerFactory`/`KafkaTemplate`/`ConcurrentKafkaListenerContainerFactory` from your `spring.kafka.*` properties. `KafkaTemplate.send()` returns a `CompletableFuture<SendResult<…>>`. A `@KafkaListener` method is adapted into a `MessageListener` running inside a listener container that owns the actual `KafkaConsumer` and the poll loop. `spring.json.trusted.packages` and Kotlin's null-safety are the two gotchas to internalize early.

### 2) Deep Dive Path — mastery curriculum (ordered)

**Module A — The container & factory model (the foundation).** Understand `ConcurrentKafkaListenerContainerFactory` vs `KafkaMessageListenerContainer`, the relationship between `concurrency` and partitions (each concurrent container = one consumer thread bound to a subset of partitions), and how Boot's autoconfig assembles them. Read: reference docs "Message Listener Containers"; Piotr Minkowski's "Concurrency with Kafka and Spring Boot" (https://piotrminkowski.com/2023/04/30/concurrency-with-kafka-and-spring-boot/).

**Module B — Offsets & acknowledgment modes.** spring-kafka sets `enable.auto.commit=false` by default — *the framework, not Kafka, commits*. Learn the seven `AckMode`s (BATCH default, RECORD, MANUAL, MANUAL_IMMEDIATE, TIME, COUNT, COUNT_TIME) via `spring.kafka.listener.ack-mode`, and when to inject `Acknowledgment` for manual commits. Read: Piotr Minkowski "Kafka Offset with Spring Boot" (https://piotrminkowski.com/2024/03/11/kafka-offset-with-spring-boot/) and his Mar 2026 "Deep Dive into Kafka Offset Commit."

**Module C — Error handling & retries.** Master `DefaultErrorHandler` (blocking retry with `FixedBackOff`/`ExponentialBackOff` + `DeadLetterPublishingRecoverer`), retryable vs non-retryable exceptions (`addNotRetryableExceptions`, the global fatal-exceptions list), and **non-blocking retries** via `@RetryableTopic`/`RetryTopicConfiguration` (auto-created retry topics + `.DLT`, `@DltHandler`, `DltStrategy`, exception-based DLT routing since 3.2). Critical broker interaction: blocking retries pause the consumer thread, so total retry time must stay under `max.poll.interval.ms` or the consumer is evicted. On spring-kafka 4.0 remember `@BackOff` replaces `@Backoff`. Read: reference "Handling Exceptions"; Baeldung DLQ (https://www.baeldung.com/kafka-spring-dead-letter-queue) and retry (https://www.baeldung.com/spring-retry-kafka-consumer).

**Kotlin `@RetryableTopic` example**
```kotlin
@RetryableTopic(
    attempts = "4",
    backoff = Backoff(delay = 1000, multiplier = 2.0, maxDelay = 10000),
    dltStrategy = DltStrategy.FAIL_ON_ERROR,
    exclude = [IllegalArgumentException::class]
)
@KafkaListener(topics = ["orders.created"], groupId = "orders")
fun handle(order: OrderCreated) { /* throws RetryableException -> retried; IllegalArgumentException -> straight to DLT */ }

@DltHandler
fun dlt(order: OrderCreated, @Header(KafkaHeaders.RECEIVED_TOPIC) topic: String) { /* park/inspect */ }
```
(On spring-kafka 4.0, the `Backoff(...)` here is the relocated `@BackOff`, which also accepts `Duration` strings like `"1s"`.)

**Module D — Transactions & exactly-once.** Set `spring.kafka.producer.transaction-id-prefix` → Boot auto-configures `KafkaTransactionManager` and wires it to the container, which begins a transaction before the listener, and the container sends offsets via `producer.sendOffsetsToTransaction()` before commit — giving exactly-once for the **read→process→write** sequence (read+process remain at-least-once). Learn `executeInTransaction`, `@Transactional`, the `AfterRollbackProcessor`, and that downstream consumers must set `isolation.level=read_committed`. Crucial caveat to internalize: Kafka transactions are NOT atomic with DB transactions — chaining them is a distributed-transaction antipattern; prefer outbox + idempotent consumer. Read: reference "Transactions"/"Exactly Once Semantics"; Lydtech "Kafka Transactions Part 1 & 2" (https://www.lydtechconsulting.com/blog-kafka-transactions-part2.html); Piotr Minkowski "Kafka Transactions with Spring Boot."

**Module E — Serialization deep dive.** Progress JSON (`JsonSerializer`/`JsonDeserializer`, type headers, `JsonDeserializer.TRUSTED_PACKAGES`, `ErrorHandlingDeserializer` wrapper to survive poison pills) → **Avro + Confluent Schema Registry** (`KafkaAvroSerializer`/`KafkaAvroDeserializer`, `schema.registry.url`, `specific.avro.reader`, the davidmc24 Gradle Avro plugin for codegen) → JSON Schema / Protobuf serdes → **schema evolution** (BACKWARD default, FORWARD, FULL; add fields with defaults). Note: generated Avro classes are Java but interoperate fine from Kotlin. Read: Confluent "Apache Avro for Kafka" docs; Sylhare's "How to Kafka with an Avro schema registry" (Kotlin: https://sylhare.github.io/2023/10/20/Avro-schema-registry.html); Baeldung Avro/Confluent guide.

**Module F — Advanced listener features.** Batch listeners (`spring.kafka.listener.type=batch`, `List<T>` parameters, `BatchMessageListener`, batch error handling/`BatchRecoverAfterRollback`), record filtering (`RecordFilterStrategy`), message conversion, **class-level `@KafkaListener` + `@KafkaHandler`** for multi-type topics, `ConsumerSeekAware` for arbitrary seeking, and pause/resume via the container. Read: reference "Receiving Messages."

**Module G — Kafka Streams integration.** `@EnableKafkaStreams` + `KafkaStreamsConfiguration` + `StreamsBuilderFactoryBean`; build `KStream`/`KTable` topologies; windowed aggregations; **interactive queries** (4.0's `KafkaStreamsInteractiveQuerySupport`). Note topics are NOT auto-created for Streams. Read: Confluent "Spring (Kotlin) with Confluent Pt. 2: Kafka Streams Topologies" (https://www.confluent.io/blog/spring-into-confluent-cloud-with-kotlin-part-2-kafka-streams/ — genuinely Kotlin); Piotr Minkowski "Kafka Streams with Spring Boot" (SAGA); *Kafka Streams in Action 2e* ch. 12 covers spring-kafka specifically.

**Kotlin topology sketch**
```kotlin
@Bean
fun topology(builder: StreamsBuilder): KStream<String, OrderCreated> {
    val stream = builder.stream<String, OrderCreated>("orders.created")
    stream.groupBy { _, v -> v.sku }
        .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(1)))
        .count()
        .toStream()
        .to("orders.per-sku.1m")
    return stream
}
```

**Module H — Testing.** `@EmbeddedKafka` (now KRaft-only in 4.0) for fast in-process integration tests; `KafkaTestUtils`; **Testcontainers Kafka** for production-fidelity (and for Schema Registry/multi-broker); **Awaitility** for asserting async outcomes instead of `Thread.sleep`; Kafka Streams `TopologyTestDriver` for pure-topology unit tests. Use the test pyramid: `MockProducer`/`MockConsumer` for logic, EmbeddedKafka for wiring, Testcontainers for black-box. Read: Testcontainers Spring Boot Kafka guide (https://testcontainers.com/guides/testing-spring-boot-kafka-listener-using-testcontainers/); Fabian Gotzen's Kotlin+Testcontainers post (https://fabiangotzen.net/2023/02/07/easy-integration-testing-for-kafka-using-kotlin-spring-boot-testcontainers/).

**Module I — Observability.** Since 3.0, set `observationEnabled=true` on `KafkaTemplate` and container properties (or `spring.kafka.template.observation-enabled` / `spring.kafka.listener.observation-enabled`) for Micrometer Observation → metrics (`spring.kafka.template`, `spring.kafka.listener` timers) + tracing (traceparent header propagation). Bind native client metrics via `MicrometerConsumerListener`/`MicrometerProducerListener`. Monitor consumer lag (`kafka.consumer.fetch.manager.records.lag`). Read: reference "Monitoring"; Baeldung "Micrometer Observation and Spring Kafka" (https://www.baeldung.com/spring-kafka-micrometer); Piotr Minkowski "Kafka Tracing with Spring Boot and OpenTelemetry."

**Module J — Security.** Configure SSL/SASL via `spring.kafka.properties.security.protocol` (SASL_SSL), `sasl.mechanism` (PLAIN/SCRAM-SHA-256/512), `sasl.jaas.config`, and SSL truststore/keystore properties. Read: Confluent Cloud Spring config examples.

**Module K — Patterns (connect mechanics to patterns you already know).**
- **Transactional outbox + Debezium CDC**: write business row + outbox row in one local DB transaction; Debezium reads the WAL/binlog (Postgres logical decoding / **MySQL binlog — directly relevant to your Aurora MySQL background**) and the Outbox Event Router SMT routes to topics. Solves the dual-write problem without distributed transactions. Read: Lydtech "Kafka Connect: Transactional Outbox With Debezium" (https://www.lydtechconsulting.com/blog/kafka-connect-debezium-demo) + repo.
- **Idempotent consumer**: dedup table written in the same transaction as side effects, for effective EOS over at-least-once delivery.
- **CQRS/event sourcing**: map command→event publication, projections via Kafka Streams KTables/interactive queries.

**Module L — Reactive option.** Use **Reactor Kafka** (`KafkaReceiver`/`KafkaSender`, `ReactiveKafkaConsumerTemplate`) only when the whole pipeline is reactive (WebFlux, non-blocking I/O end-to-end); it gives backpressure and functional composition but you manage acknowledgment/commit semantics yourself (out-of-order commit hazards with `flatMap`). For the vast majority of imperative Spring Boot services, classic spring-kafka `@KafkaListener` is the right default. Spring Cloud Stream's reactive Kafka binder is a higher-level alternative. Read: reference for Reactor Kafka; DZone "Reactive Kafka With Spring Boot" (Kotlin example).

**Module M — KIP-848 & 4.x specifics.** KIP-848 moves rebalance/assignment logic from client to broker (the unified `ConsumerGroupHeartbeat` API), giving incremental, non-stop-the-world rebalances — most valuable for large groups and frequent autoscaling (e.g., K8s pod churn). The performance delta is dramatic: per Karafka's framework docs, "a group with 10 consumers adding 900 partitions completes rebalancing in 5 seconds instead of 103 seconds." In spring-kafka you *opt in* via the consumer `group.protocol=consumer` property; on Kafka 4.0 the protocol "is automatically enabled on the server," with broker-controlled timers (defaults: `group.consumer.heartbeat.interval.ms`=5s, `group.consumer.session.timeout.ms`=45s) — so it is broker-side config plus a client property change, with no listener code changes. Per Confluent's KIP-848 blog, "the new KIP-848 protocol will become the default rebalance protocol in a future Apache Kafka release, likely version 5.0." Caveat: in 3.x/early support it required real brokers (not EmbeddedKafka in some modes) and was test-only; it is GA in Apache Kafka 4.0 and supported in spring-kafka 4.0. Read: Confluent "KIP-848" blog (https://www.confluent.io/blog/kip-848-consumer-rebalance-protocol/); reference "New Consumer Rebalance Protocol."

### 3) Curated Resources by type

**Company / engineering blogs (depth-ranked):**
- **Official spring-kafka reference docs** — https://docs.spring.io/spring-kafka/reference/ — authoritative; authors include project lead Gary Russell and Artem Bilan. "What's new" page tracks 4.x: https://docs.spring.io/spring-kafka/reference/whats-new.html
- **Spring.io blog** — release notes + the multi-part "Transactions/Exactly-once in Spring Cloud Stream Kafka" series by Soby Chacko (https://spring.io/blog/2023/10/16/apache-kafkas-exactly-once-semantics-in-spring-cloud-stream-kafka/).
- **Lydtech Consulting (Rob Golder)** — the best free production-grade spring-kafka series with companion GitHub repos: transactions, DLT, Kafka Streams, idempotent consumer, Debezium outbox. https://www.lydtechconsulting.com/
- **Piotr Minkowski** — https://piotrminkowski.com/tag/apache-kafka/ — concurrency, offset commit, transactions, tracing, SAGA with Kafka Streams; some Kotlin content.
- **Confluent Developer / Confluent blog** — including the **Kotlin-specific** "Spring (Kotlin) with Confluent" series by Sandon Jacobs (Pt. 2 Kafka Streams: https://www.confluent.io/blog/spring-into-confluent-cloud-with-kotlin-part-2-kafka-streams/).
- **Baeldung spring-kafka series** — broad, current, Java: intro, DLQ, retry, testing, Micrometer, Avro/Confluent. https://www.baeldung.com/spring-kafka
- **Reflectoring (Tom Hombergs et al.)** — https://reflectoring.io/spring-boot-kafka/ — clear producer/consumer config walkthrough.
- **Conference talks — Tim van Baarsen (ING Bank):** "Spring Kafka beyond the basics" (Spring I/O 2022, repo https://github.com/j-tim/spring-io-barcelona-2022-spring-kafka-beyond-the-basics), "Spring for Apache Kafka — the advanced features" (Spring I/O 2025, https://www.youtube.com/watch?v=Z0Jcr5Q7FaI), and "What's new in Spring for Apache Kafka 4?" (Spring I/O 2026, https://www.youtube.com/watch?v=742i_bpOEa8). Java repos; no paid course.
- **Committers as references:** Gary Russell (project lead, started spring-kafka in 2016, now retired) and Artem Bilan answer authoritatively on Stack Overflow (tag `spring-kafka`).

**Courses:**
- **Confluent Developer "Spring Framework and Apache Kafka"** — FREE, https://developer.confluent.io/courses/spring/ — instructor Viktor Gamov; 13 lessons (autoconfig, KafkaTemplate, @KafkaListener, TopicBuilder, Kafka Streams, Schema Registry). **Java only** (uses Lombok/Java 11); Kotlin mentioned only in passing. Pair it with the Confluent podcast "Joining Forces with Spring Boot, Apache Kafka, and Kotlin ft. Josh Long" for the Kotlin angle.
- **Confluent getting-started** — FREE, https://developer.confluent.io/get-started/spring-boot/ — Java.
- **Udemy: "Apache Kafka for Developers using Spring Boot" (Dilip Sundarraj/Pragmatic Code School)** — https://www.udemy.com/course/apache-kafka-for-developers-using-springboot/ — strong on producer/consumer, EmbeddedKafka testing. **Java.**
- **Udemy: "Introduction to Kafka with Spring Boot" (John Thompson, Dan Edwards, et al.)** — https://www.udemy.com/course/introduction-to-kafka-with-spring-boot/ — updated 8/2025; retries, DLT, EmbeddedKafka. **Java.**
- **Udemy: "Apache Kafka with Spring Boot" / "Kafka Event-Driven Microservices" (Vinoth Selvaraj)** — https://www.udemy.com/course/spring-kafka-reactive/ — covers reactive Kafka, security, testing; aimed at senior/staff engineers. **Java.**
- **Manning liveProject / O'Reilly learning platform** — video + sandbox; mostly Java.
- No high-quality **Kotlin-native** spring-kafka video course currently exists — flag this clearly.

**Books (relevance to spring-kafka noted):**
- **Kafka Streams in Action, 2nd ed.** — Bill Bejeck, Manning 2024 (ISBN 9781617298684). *Most spring-kafka-relevant book*: ch. 12 is "Spring kafka," plus KTable, windowing, Processor API, interactive queries, testing, Schema Registry. Java.
- **Kafka: The Definitive Guide, 2nd ed.** — Shapira, Palino, Sivaram, Narkhede, O'Reilly (©2022). The canonical *core-Kafka* reference (producers, consumers, EOS, admin, security) — NOT Spring-specific but deepens the broker model you'll configure through Spring. (Note: 2nd ed. added Rajini Sivaram as author vs. the 1st ed.'s Narkhede/Shapira/Palino.)
- **Building Event-Driven Microservices, 2nd ed.** — Adam Bellemare, O'Reilly (2nd ed. 2025; 1st ed. 2020). Patterns, schemas/evolution, microservice topologies — connects spring-kafka mechanics to architecture. Not Spring-specific.
- **Designing Event-Driven Systems** — Ben Stopford, O'Reilly (free Confluent ebook). Conceptual foundation for event-driven architecture; not Spring-specific.
- **Kafka in Action** — Scott, Gamov, Klein, Manning 2022 (ISBN 9781617295232). Solid core-Kafka-with-Java book; **no meaningful Spring chapter**.
- **Spring Microservices in Action, 2nd ed.** — Carnell & Sánchez, Manning. Broader Spring Cloud microservices; light on spring-kafka specifics.

### 4) Progressive Project-Guided Learning Plan — "Acme Commerce" event-driven system

Domain: **order → payment → inventory → shipping → notification**, coordinated via Kafka events. One multi-module Gradle (Kotlin DSL) repo; each stage adds one bounded service and exercises specific spring-kafka features.

- **Stage 0 — Setup.** Multi-module Gradle Kotlin DSL; Spring Boot 4 (or 3.5) + Kotlin 2.x; `docker-compose.yml` with Kafka (KRaft) + Schema Registry + Kafka UI + MySQL; shared `events` module with data classes. *Concepts:* autoconfig, `spring.kafka.*`, `TopicBuilder`. *Read:* Quick Tour; Confluent getting-started.
- **Stage 1 — Order service produces `orders.created`; a logging consumer reads it.** *Concepts:* `KafkaTemplate`, `@KafkaListener`, `ProducerFactory`/`ConsumerFactory`, keys/partitions. *Read:* Baeldung intro; Reflectoring.
- **Stage 2 — JSON with Kotlin data classes; payment + inventory services as separate consumer groups.** *Concepts:* `JsonSerializer`/`JsonDeserializer`, trusted packages, `ErrorHandlingDeserializer`, multiple groups, `concurrency`. *Read:* Piotr "Concurrency."
- **Stage 3 — Error handling/retries/DLT in payment service.** *Concepts:* `DefaultErrorHandler` + `DeadLetterPublishingRecoverer`, `@RetryableTopic`/`@DltHandler`, retryable vs non-retryable, `max.poll.interval.ms`. *Read:* reference "Handling Exceptions"; Baeldung DLQ/retry.
- **Stage 4 — Schema Registry + Avro for `orders.created`; evolve the schema.** *Concepts:* `KafkaAvroSerializer`/`Deserializer`, Gradle Avro codegen, BACKWARD/FORWARD compatibility. *Read:* Sylhare Kotlin Avro; Confluent Avro docs.
- **Stage 5 — Exactly-once payment processing (read `orders.created` → write `payments.completed`).** *Concepts:* `transaction-id-prefix`, `KafkaTransactionManager`, `read_committed`, `AfterRollbackProcessor`. *Read:* reference EOS; Lydtech transactions.
- **Stage 6 — Transactional outbox + Debezium CDC from Aurora MySQL.** *Concepts:* outbox table + business write in one DB tx, Debezium MySQL connector (binlog), Outbox Event Router SMT, idempotent consumer dedup. *Read:* Lydtech Debezium outbox + idempotent-consumer repos.
- **Stage 7 — Kafka Streams real-time analytics (windowed orders-per-SKU, revenue).** *Concepts:* `@EnableKafkaStreams`, `StreamsBuilderFactoryBean`, `KStream`/`KTable`, windowing, interactive queries. *Read:* Confluent Kotlin Streams blog; *KS in Action 2e* ch. 12.
- **Stage 8 — Full testing strategy.** *Concepts:* `@EmbeddedKafka` (KRaft) integration tests, Testcontainers (with Schema Registry), Awaitility, `TopologyTestDriver` for the Streams topology. *Read:* Testcontainers guide; Fabian Gotzen Kotlin post.
- **Stage 9 — Observability.** *Concepts:* Micrometer Observation (`observationEnabled`), tracing via traceparent, consumer-lag metrics, Prometheus/Grafana. *Read:* Baeldung Micrometer; Piotr tracing.
- **Stage 10 — Production hardening.** *Concepts:* SASL_SSL/SCRAM security, concurrency tuning vs partition count, graceful shutdown, container deployment on Kubernetes, and **opting into KIP-848** (`group.protocol=consumer`) to smooth rebalances during pod autoscaling. *Read:* Confluent KIP-848; reference security/containers.

### 5) The generic, domain-agnostic skeleton underneath

Strip away "orders/payments/inventory" and Acme Commerce is an instance of a reusable reference architecture. The transferable skeleton:

- **Event contract module** — versioned domain events (Kotlin data classes for JSON, or Avro/Protobuf `.avsc`/`.proto` with generated types) shared across services; schema-evolution rules enforced by Schema Registry. *Generic role:* the typed boundary between services.
- **Producer/edge service** — accepts external input (REST), persists state, and emits domain events. *spring-kafka:* `KafkaTemplate` (+ `transaction-id-prefix` when atomic multi-topic writes are needed) and `TopicBuilder`.
- **One or more consumer/reactor services** — each its own consumer group, reacting to events and emitting downstream events. *spring-kafka:* `@KafkaListener` containers with tuned `concurrency` and `AckMode`.
- **Retry/DLT layer** — a cross-cutting reliability tier: blocking retry (`DefaultErrorHandler`) for transient faults, non-blocking `@RetryableTopic` + `.DLT` for poison/long-failure messages, with a DLT inspection/replay tool.
- **Streams/aggregation layer** — stateful projections and windowed analytics (`StreamsBuilderFactoryBean`, KTables, interactive queries) materializing read models.
- **Outbox + CDC layer** — local-transaction outbox table + Debezium connector (binlog/WAL) to eliminate dual writes; pairs with an idempotent-consumer dedup table for effective EOS. *Database-agnostic:* swap Aurora MySQL for Postgres by changing the connector.
- **Testing harness** — EmbeddedKafka for fast wiring tests, Testcontainers for fidelity, `TopologyTestDriver` for topologies, Awaitility for async assertions.
- **Observability layer** — Micrometer Observation metrics + distributed tracing + consumer-lag dashboards, identical regardless of domain.

The contrast worth holding in mind: the **realistic project** teaches you *why* each piece exists (a payment must not be double-charged → EOS + idempotency; an order must never be silently lost → outbox + DLT); the **generic skeleton** is what you actually carry to the next system — a producer tier, a reactor tier, a reliability (retry/DLT) tier, a streams/projection tier, an outbox/CDC integration tier, a test harness, and an observability tier, all wired through spring-kafka's container/template/factory model. Every future Kafka service you build in Spring is a re-instantiation of these seven layers with a different event vocabulary.

## Recommendations
- **Week 1 (productivity):** Do the Quick Overview Path and build Stages 0–2 in Kotlin. Readiness benchmark: you can explain, without docs, which beans Boot autoconfigures and why `enable.auto.commit` is false by default.
- **Weeks 2–4 (reliability core):** Stages 3–5 (error handling/DLT, then transactions/EOS). This is the highest-leverage spring-kafka knowledge for a senior backend role. Threshold to advance: you can articulate why blocking retry risks consumer eviction (it pauses the poll thread past `max.poll.interval.ms`) and when EOS does *not* protect a DB side effect.
- **Weeks 5–7 (integration & streams):** Stages 6–7 (outbox/Debezium on your Aurora MySQL strength, then Kafka Streams). Threshold: you can defend outbox+CDC over a chained Kafka/DB transaction.
- **Weeks 8–9 (quality & ops):** Stages 8–10. Threshold: a green Testcontainers suite plus a Grafana lag dashboard, and a documented decision on classic vs KIP-848 rebalancing for your deployment.
- **Version decision rule:** if your platform is Spring Boot 4 / Kafka 4 brokers, start on spring-kafka 4.0 and adopt `@BackOff`, Jackson 3, KRaft EmbeddedKafka, and opt into KIP-848 once brokers are 4.0+. If you're on Boot 3.x, stay on spring-kafka 3.3.x and migrate later. Re-evaluate when your brokers reach Kafka 4.0 and when KIP-848 becomes the broker default (~Kafka 5.0, per Confluent).
- **Reactive decision rule:** default to classic `@KafkaListener`; adopt Reactor Kafka only if the entire service is WebFlux/non-blocking end-to-end.
- **Kotlin tax:** since courses/tutorials are Java, keep the reference docs' Kotlin Quick Tour and the Confluent Kotlin Streams blog as your two "this is how it looks in Kotlin" anchors, and lean on data classes for events, null-safety for deserialization contracts, and the Gradle Kotlin DSL.

## Caveats
- **Java-only resource bias:** essentially all courses and most blogs/repos (Confluent course, Tim van Baarsen's repos, Baeldung, Udemy) are Java. The transposition is mechanical for you but means no turnkey Kotlin curriculum exists.
- **Version churn:** spring-kafka 4.0 GA'd Nov 2025 with breaking changes (Spring Retry removal → `@BackOff`, Jackson 3, KRaft-only EmbeddedKafka). Some popular blog code targets 2.x/3.x APIs (e.g., old `@Backoff`, ZK-based EmbeddedKafka) — verify each snippet against your version.
- **KIP-932 share consumers / "queues"** support in spring-kafka 4.0/4.1 is explicitly early-access/experimental — don't build production on it yet.
- **KIP-848** is GA at the broker in Kafka 4.0 but support across non-Apache implementations varies — per Karafka's docs, "At the time of writing, KIP-848 is not supported by Redpanda or other alternative Kafka protocol implementations. This feature requires Apache Kafka 4.0+ brokers." Confirm your broker supports it before opting in.
- **EOS scope:** Kafka transactions guarantee the read→process→write message sequence only; external side effects (DB writes, REST calls) can still repeat on redelivery — hence idempotency/outbox.
- **Confluent course currency:** the free Confluent course uses Java 11 and an older Spring Boot; concepts are current but versions/syntax lag — cross-check with the reference docs.