---
title: "OrderFlow — A Spring Boot 4.x + Kotlin Implementation Curriculum for Apache Kafka Mastery"
category: "Spring & Spring Boot"
description: "Ten-stage Spring Boot 4.0 + Kotlin 2 + Spring for Apache Kafka 4.0 curriculum that grows one progressive system (OrderFlow) from a single producer/consumer to a full event-driven platform with Avro Schema Registry, KafkaAwareTransactionManager, @RetryableTopic + DLT, Debezium outbox, sagas, CQRS read models, share groups (KIP-932), and MSK IAM — paired with isolated lab projects at every stage."
---

# OrderFlow: A Spring Boot 4.x + Kotlin Implementation Curriculum for Apache Kafka Mastery

## TL;DR
- **Build one progressive Kotlin/Spring Boot 4.0 system called "OrderFlow"** that grows over ten stages from a single producer/consumer into a full event-driven e-commerce platform — `order-api`, `payment-orchestrator`, `inventory`, `fulfillment`, `notification`, `analytics`, and `read-model` services — wired with Schema Registry (Avro), Micrometer Observation tracing, non-blocking retries with DLT, transactional outbox via Debezium against Aurora MySQL, choreography and orchestration sagas, CQRS read sides, and MSK IAM authentication in production.
- **Supplement OrderFlow with 2–4 small "lab" projects per stage** that isolate a single concept (idempotent producer config, manual ack, Avro evolution, `KafkaAwareTransactionManager`, `@RetryableTopic`, share groups, etc.) so you internalize each Spring Kafka API in a sandbox before integrating it.
- **The plan is precisely calibrated for Spring Boot 4.0 GA (November 20, 2025) on Spring Framework 7 / Jakarta EE 11 / Jackson 3 / JUnit 6 / Kotlin 2, with Spring for Apache Kafka 4.0.x (GA November 18, 2025) targeting Apache Kafka 4.2 (released February 17, 2026) in KRaft-only mode** — every code snippet reflects the new `JacksonJsonSerializer`, the renamed `@BackOff` annotation, `setKafkaAwareTransactionManager`, KRaft-only `EmbeddedKafkaKraftBroker`, and the share-consumer (KIP-932) support that Apache Kafka's 4.2 upgrade guide explicitly calls "production-ready."

## Key Findings

This plan is deliberately *complementary* to a broker-internals/operations curriculum: it assumes you already understand the log, partitions, ISR, KRaft quorum, the rebalance protocol, and the operational surface. Its purpose is to make you fluent in writing *idiomatic* Spring Kafka and Spring Cloud Stream code in Kotlin for Spring Boot 4.x — knowing not just which annotations exist, but exactly when to reach for raw `spring-kafka` versus the Spring Cloud Stream functional binder, when `KafkaAwareTransactionManager` is the right answer versus the transactional outbox, why `@TransactionalEventListener(AFTER_COMMIT)` is *not* equivalent to outbox-with-Debezium, and how to design listeners that are idempotent, observable, and rebalance-safe.

A few facts about the target stack are worth stating upfront because they shape every code sample below. On the official Spring blog of November 20, 2025, Phil Webb wrote: "On behalf of the team and everyone who has contributed, I'm extremely happy to announce that Spring Boot 4.0.0 has been released and is now available from Maven Central." Spring Boot 4.0 sits on top of Spring Framework 7.0, Jakarta EE 11, Spring Security 7, Hibernate 7.1, and Spring Data 2025.1, with JDK 17 as the baseline and JDK 21+ recommended for virtual threads. The 4.x release line is fully modularized (smaller, more focused jars), uses JSpecify for null-safety portfolio-wide, ships first-class HTTP service clients via `@ImportHttpServices`, and pulls in **Jackson 3** as the default JSON stack.

Spring for Apache Kafka 4.0.0 GA was released on **November 18, 2025**, two days *before* Spring Boot 4.0; Soby Chacko's announcement on the Spring blog confirms: "we are pleased to announce that Spring for Apache Kafka 4.0.0 is now generally available." It is the first 4.x line built on Spring Framework 7 and Kafka client 4.0/4.1, and it brought three breaking changes that affect almost every existing codebase: the Spring Retry dependency was removed in favor of Spring Framework 7's core retry; all Jackson-2-based serializers (`JsonSerializer`, `JsonDeserializer`, `JsonSerde`, `Jackson2JavaTypeMapper`) were marked `@Deprecated(forRemoval=true, since="4.0")` in favor of `JacksonJsonSerializer`/`JacksonJsonDeserializer`/`JacksonJsonSerde` built on the new `tools.jackson.databind` package; and `@EmbeddedKafka`'s `kraft` flag was removed because Kafka 4.x is KRaft-only — the Spring Kafka 4.0 What's New page is explicit: "All ZooKeeper-based functionality has been removed... The `EmbeddedKafkaZKBroker` class has been removed, and all functionality is now handled by `EmbeddedKafkaKraftBroker`." Apache Kafka 4.2.0 (released **February 17, 2026**) is the matching broker line: per the official Kafka 4.2 upgrade guide on `kafka.apache.org`, "Queues for Kafka (KIP-932) is production-ready in Apache Kafka 4.2... This feature introduces a new kind of group called share groups, as an alternative to consumer groups," KIP-848 next-generation consumer rebalance is GA, KIP-1071 streams rebalance protocol is GA for its core feature set, and KIP-1034 brought first-class dead-letter-queue support inside Kafka Streams exception handlers. As of April 22, 2026, the current patch alignment per the Spring Kafka team is "Spring Kafka 4.0.5 will be integrated into Spring Boot 4.0.6. Spring Kafka 4.1.0-RC1 will be integrated into Spring Boot 4.1.0-RC1."

A second framing point: every stage below has the same internal structure — learning objectives in prose, a description of which OrderFlow service or capability is added or evolved, idiomatic Kotlin code, lab projects, dependencies, resources, and gotchas. The reason for this rhythm is pedagogical. You learn the API once in the lab (where it is isolated and the failure modes are easy to see), then again in OrderFlow (where you have to make it cohabit with the rest of the system), and after enough stages you stop thinking about the API and start thinking about the *patterns*.

Finally, two non-obvious decisions baked into this plan. First, we deliberately use **both** raw `spring-kafka` and **Spring Cloud Stream's Kafka binder** across different services in OrderFlow, because in real systems these coexist and you need to know when each is the right tool. Spring Cloud Stream's functional model (`Function<I,O>`, `Consumer<I>`, `Supplier<O>` beans with `spring.cloud.stream.bindings.*` configuration) is wonderful for portability and for the Kafka Streams binder, but raw `@KafkaListener` is more precise when you need fine-grained container properties, per-record acks, rebalance listeners, and the share-consumer (KIP-932). Second, we treat Aurora MySQL as the system-of-record everywhere and Postgres + Elasticsearch as read-side stores, because that mirrors your AWS-on-Seoul environment and lets us exercise both Debezium MySQL CDC and the Spring Data JPA outbox in idiomatic ways.

## Details

### Stage 1 — Spring Boot + Kafka "Hello World" with KRaft

The goal of Stage 1 is to get a Kotlin Spring Boot 4.0 application sending and receiving messages with `KafkaTemplate` and `@KafkaListener`, against a local KRaft cluster, with correct configuration, structured logging, and a Testcontainers-based integration test. Conceptually trivial, but every later stage builds on the choices made here, so we are deliberate.

The Gradle Kotlin DSL coordinates you want are these:

```kotlin
// build.gradle.kts (orderflow-order-api)
plugins {
    id("org.springframework.boot") version "4.0.6"
    id("io.spring.dependency-management") version "1.1.7"
    kotlin("jvm") version "2.1.20"
    kotlin("plugin.spring") version "2.1.20"
}

dependencies {
    // Spring Boot 4 made the Kafka *starter* mandatory for auto-configuration —
    // depending only on spring-kafka no longer activates auto-config (issue #4278 on spring-kafka).
    implementation("org.springframework.boot:spring-boot-starter-kafka")
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin") // still useful for Kotlin data classes
    implementation("org.jetbrains.kotlin:kotlin-reflect")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.kafka:spring-kafka-test")
    testImplementation("org.testcontainers:junit-jupiter")
    testImplementation("org.testcontainers:kafka")
}
```

Note the first gotcha: in Spring Boot 4.x, declaring only `org.springframework.kafka:spring-kafka` does **not** trigger Kafka auto-configuration; you must depend on `spring-boot-starter-kafka`. This is a frequent source of confusion when migrating 3.x code (Spring Initializr generates the starter correctly, but hand-written `build.gradle.kts` files often miss it). The starter brings in the spring-kafka jar plus the Boot auto-configuration metadata that ties `spring.kafka.*` properties to beans.

Your `application.yml` for local development is small but every line matters:

```yaml
# application.yml
spring:
  application:
    name: orderflow-order-api
  kafka:
    bootstrap-servers: localhost:9092
    client-id: ${spring.application.name}
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      # JacksonJsonSerializer is the *new* Jackson-3 class in spring-kafka 4.x.
      # The old `JsonSerializer` is @Deprecated(forRemoval=true, since="4.0").
      value-serializer: org.springframework.kafka.support.serializer.JacksonJsonSerializer
      acks: all
      properties:
        enable.idempotence: true       # we'll explain in Stage 2
        max.in.flight.requests.per.connection: 5
    consumer:
      group-id: order-api
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.JacksonJsonDeserializer
      properties:
        spring.json.trusted.packages: "com.orderflow.events"
        # Tell the new Jackson 3 deserializer the default type if no header is set:
        spring.json.value.default.type: "com.orderflow.events.OrderPlacedEvent"
    listener:
      observation-enabled: true        # Stage 2 will explain — enable now, cost is negligible
    template:
      observation-enabled: true

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus,kafka
  tracing:
    sampling:
      probability: 1.0                 # 100% in dev; tune in prod

logging:
  pattern:
    console: "%d{HH:mm:ss.SSS} [%t] [%X{traceId:-},%X{spanId:-}] %-5p %c{1} - %m%n"
```

The smallest possible OrderFlow Stage 1 producer/consumer pair in Kotlin:

```kotlin
// events.kt
package com.orderflow.events

import java.time.Instant
import java.util.UUID

data class OrderPlacedEvent(
    val orderId: UUID,
    val customerId: UUID,
    val totalKrw: Long,
    val placedAt: Instant
)

// OrderController.kt
@RestController
@RequestMapping("/orders")
class OrderController(
    private val kafkaTemplate: KafkaTemplate<String, OrderPlacedEvent>
) {
    @PostMapping
    fun place(@RequestBody req: PlaceOrderRequest): ResponseEntity<Unit> {
        val event = OrderPlacedEvent(
            orderId = UUID.randomUUID(),
            customerId = req.customerId,
            totalKrw = req.totalKrw,
            placedAt = Instant.now()
        )
        // Using the orderId as key guarantees per-order ordering on the partition.
        // The CompletableFuture returned lets us observe broker-side acks if we want.
        kafkaTemplate.send("orderflow.orders", event.orderId.toString(), event)
            .whenComplete { result, ex ->
                if (ex != null) log.error("Send failed for {}", event.orderId, ex)
                else log.info("Sent {} at offset {}", event.orderId, result.recordMetadata.offset())
            }
        return ResponseEntity.accepted().build()
    }
}

// FulfillmentListener.kt
@Component
class FulfillmentListener {
    @KafkaListener(topics = ["orderflow.orders"], groupId = "fulfillment")
    fun onOrder(event: OrderPlacedEvent,
                @Header(KafkaHeaders.RECEIVED_KEY) key: String) {
        log.info("Fulfilling order {} (key={})", event.orderId, key)
        // ... domain logic
    }
}
```

For the integration test we use Testcontainers' modern `KafkaContainer` with KRaft against the same Kafka image our production targets:

```kotlin
@SpringBootTest
@Testcontainers
class OrderFlowKafkaTest {
    companion object {
        @Container
        @JvmStatic
        val kafka = KafkaContainer(DockerImageName.parse("apache/kafka:4.2.0"))
            .withKraft()
        @JvmStatic
        @DynamicPropertySource
        fun props(reg: DynamicPropertyRegistry) {
            reg.add("spring.kafka.bootstrap-servers") { kafka.bootstrapServers }
        }
    }
}
```

The OrderFlow delta at Stage 1 is just one Boot service, `order-api`, with a single `POST /orders` endpoint that emits one event to one topic. The corresponding labs are deliberately tiny:

**Lab 1.1 — `hello-kafka-template`** — a one-class Boot app that uses `KafkaTemplate` to send 1 million records to a topic and prints throughput. Teaches how `acks`, `linger.ms`, and `batch.size` interact.

**Lab 1.2 — `hello-listener-ackmode`** — sets `spring.kafka.listener.ack-mode: MANUAL_IMMEDIATE` and shows how `Acknowledgment.acknowledge()` controls commits versus the default `BATCH` mode.

**Lab 1.3 — `kraft-vs-zk-embedded`** — uses `@EmbeddedKafka` to demonstrate that since Spring Kafka 4.x, only `EmbeddedKafkaKraftBroker` exists, the `kraft` flag is gone, and any old test that set `zookeeperPort`/`zkConnectionTimeout` won't compile.

The Stage 1 gotchas are also small but real: the deprecated `JsonSerializer` will still work but emit warnings — switch to `JacksonJsonSerializer`; `spring-kafka` alone no longer triggers auto-config in Boot 4 (Spring Kafka GitHub issue #4278 is the source of truth on this); and `@EmbeddedKafka` no longer talks to ZooKeeper. Resources: Spring Boot 4.0 reference [Messaging → Apache Kafka](https://docs.spring.io/spring-boot/reference/messaging/kafka.html), Spring for Apache Kafka 4.0 reference, and the Confluent Developer Spring + Kafka course.

### Stage 2 — Idempotent producers, manual acks, error handling, observability foundations

Stage 2 takes the Stage-1 plumbing and makes it production-correct. We turn on producer idempotence and explain why it gives at-least-once with no duplicates *on the broker side*; we move to manual ack mode so listener commits become a deliberate act; we wire a `DefaultErrorHandler` with a tuned `BackOff` and a `DeadLetterPublishingRecoverer`; we turn on Micrometer Observation for tracing across producer→broker→consumer; and we add structured logging with `traceId`/`spanId` in the MDC.

Idempotent producers in Spring Boot 4 take exactly three properties. Modern Kafka enables idempotence by default for new producers, but it is worth setting explicitly because `acks=all`, `enable.idempotence=true`, and `max.in.flight.requests.per.connection ≤ 5` interact, and seeing them together documents intent. With these settings, the producer assigns a producer ID and a per-partition sequence number; on retries the broker dedupes by sequence, so transient network failures no longer cause duplicates in the log. This is *not* exactly-once across read-process-write — for that you also need a `transactional.id` and a `KafkaAwareTransactionManager`, which is Stage 5.

```yaml
spring:
  kafka:
    producer:
      acks: all
      properties:
        enable.idempotence: true
        max.in.flight.requests.per.connection: 5
        delivery.timeout.ms: 120000
        retries: 2147483647            # let Kafka retry forever within delivery.timeout.ms
    consumer:
      enable-auto-commit: false        # listener container will commit explicitly
      isolation-level: read_committed  # important once we add transactions in Stage 5
    listener:
      ack-mode: MANUAL_IMMEDIATE       # commit only when you call Acknowledgment.acknowledge()
      concurrency: 3                   # 3 threads → up to 3 partitions per instance
      observation-enabled: true
```

The `DefaultErrorHandler` in Spring Kafka 4 takes a Spring Framework 7 `BackOff` (not a Spring Retry `BackOffPolicy` — that dependency was removed in 4.0) and a recoverer. The standard production wiring is exponential back-off with a max-retries cap, plus a `DeadLetterPublishingRecoverer` that publishes to a `.DLT` topic, plus a classifier that distinguishes retryable from non-retryable exceptions:

```kotlin
@Configuration
class KafkaErrorHandlingConfig {

    @Bean
    fun errorHandler(
        kafkaTemplate: KafkaTemplate<Any, Any>
    ): DefaultErrorHandler {
        val recoverer = DeadLetterPublishingRecoverer(kafkaTemplate) { rec, _ ->
            // Route to <original>.DLT, keeping the same partition.
            TopicPartition("${rec.topic()}.DLT", rec.partition())
        }
        // Spring Kafka's ExponentialBackOffWithMaxRetries (a subclass of Spring Framework's
        // ExponentialBackOff) lets you cap retries by count rather than by elapsed time.
        val backOff = ExponentialBackOffWithMaxRetries(5).apply {
            initialInterval = 500
            multiplier = 2.0
            maxInterval = 10_000
        }
        val handler = DefaultErrorHandler(recoverer, backOff)
        // Non-retryable: poison records, validation errors, anything code can't fix by retrying.
        handler.addNotRetryableExceptions(
            IllegalArgumentException::class.java,
            ValidationException::class.java,
            DeserializationException::class.java
        )
        handler.setRetryListeners(RetryListener { rec, ex, deliveryAttempt ->
            log.warn("Retry {} for record {}/{}@{}: {}",
                deliveryAttempt, rec.topic(), rec.partition(), rec.offset(), ex.message)
        })
        return handler
    }
}
```

Observability is where Spring Kafka 4 quietly shines. Setting `spring.kafka.listener.observation-enabled=true` and `spring.kafka.template.observation-enabled=true` activates the `KafkaTemplateObservation` and `KafkaListenerObservation` instruments (Micrometer 1.16, Reactor 2025.0 train), which produce timers `spring.kafka.template` / `spring.kafka.listener` *and* spans with W3C trace-context headers automatically propagated through producer→broker→consumer. Because Kafka headers carry the trace context, the consumer's span is a child of the producer's, and your Grafana/Jaeger UI shows the full end-to-end path. A `KafkaTemplateObservationConvention` lets you add per-record tags such as `tenant.id` or `aggregate.type`. Add a `micrometer-tracing-bridge-otel` plus `opentelemetry-exporter-otlp` to ship traces to your collector. Spring Kafka 4 also adds **per-record observations for batch listeners**, which 3.x did not have.

OrderFlow's Stage 2 delta: harden `order-api`'s producer with idempotence, switch `fulfillment` to manual ack, add the global `DefaultErrorHandler` and a `.DLT` topic, and enable observation everywhere. Add a Prometheus scrape endpoint via Actuator's `prometheus` endpoint.

Labs for Stage 2:

**Lab 2.1 — `idempotent-producer-demo`** — kills the broker mid-send and shows duplicates with `enable.idempotence=false` versus none with it on.

**Lab 2.2 — `dlt-and-replay`** — sends a poison record, observes it landing in `.DLT`, then writes a small admin endpoint (`POST /admin/dlt/replay`) that uses `KafkaTemplate` to re-publish a DLT record to the original topic after a "fix" is applied.

**Lab 2.3 — `manual-ack-rebalance`** — demonstrates that with `MANUAL_IMMEDIATE` and a slow listener, a rebalance during processing reassigns the partition and an unacked record gets reprocessed by the new owner — teaching why idempotent *consumers* are mandatory.

**Lab 2.4 — `micrometer-trace-end-to-end`** — Producer service, Kafka, Consumer service, plus a Jaeger container; you `curl` the producer and see a single trace spanning HTTP → producer → broker → consumer → DB write.

Gotchas: the new `JacksonJsonDeserializer` requires `spring.json.value.default.type` *or* `spring.json.use.type.headers` set to true (default), and a fresh consumer with no header will fail mysteriously without one or the other; `DefaultErrorHandler` does *not* automatically include `DeserializationException` as non-retryable (you need to add it — otherwise the broker will keep handing you the same bad bytes); `MANUAL_IMMEDIATE` plus `concurrency > 1` means commits are interleaved across threads, so you must not assume monotonic offset commits per topic-partition across threads.

### Stage 3 — Schema Registry with Avro, generated Kotlin data classes, schema evolution

Stage 3 introduces typed events. JSON with Jackson is fine for prototypes; for a multi-service system it is a footgun because there is no compile-time contract and no central place to enforce evolution rules. We pick **Avro** as the binary format and integrate with **Confluent Schema Registry** as the primary option, with **Apicurio Registry** documented as the open-source alternative for self-hosted environments (Apicurio also supports the Confluent wire format, so you can swap registries without rewriting clients).

Avro schemas live in `src/main/avro/*.avsc`. We use a Gradle plugin to generate Kotlin-friendly Java classes (Avro 1.12+ produces classes that interop cleanly with Kotlin data semantics). Note that the Confluent serializer version must align with your Kafka client version — Confluent Platform 8.2.0 (`kafka-avro-serializer:8.2.0`, released March 9, 2026) is the line aligned with Apache Kafka 4.2 per the official Confluent Platform release notes:

```kotlin
// build.gradle.kts
plugins {
    id("io.github.androa.gradle.plugin.avro") version "0.1.5"
}
repositories {
    mavenCentral()
    maven("https://packages.confluent.io/maven/")
}
dependencies {
    implementation("io.confluent:kafka-avro-serializer:8.2.0")
    implementation("org.apache.avro:avro:1.12.0")
}
```

`src/main/avro/OrderPlaced.avsc`:

```json
{
  "type": "record", "namespace": "com.orderflow.events", "name": "OrderPlaced",
  "fields": [
    {"name": "orderId",    "type": {"type": "string", "logicalType": "uuid"}},
    {"name": "customerId", "type": {"type": "string", "logicalType": "uuid"}},
    {"name": "totalKrw",   "type": "long"},
    {"name": "placedAt",   "type": {"type": "long",  "logicalType": "timestamp-millis"}}
  ]
}
```

Avro+Schema-Registry configuration in `application.yml`:

```yaml
spring:
  kafka:
    properties:
      schema.registry.url: http://schema-registry:8081
      # If using Confluent Cloud:
      basic.auth.credentials.source: USER_INFO
      basic.auth.user.info: ${SR_API_KEY}:${SR_API_SECRET}
      # Force the generated Avro class to be used on read instead of GenericRecord:
      specific.avro.reader: true
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: io.confluent.kafka.serializers.KafkaAvroSerializer
    consumer:
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: io.confluent.kafka.serializers.KafkaAvroDeserializer
```

The migration step in OrderFlow Stage 3: replace the `OrderPlacedEvent` Kotlin data class with the generated Avro class, change serializers, and register the schema in CI. Wrap CI with a `compatibility-check` job that calls the Schema Registry's compatibility endpoint with `BACKWARD` (the right default for consumer-first evolution) or `FULL_TRANSITIVE` (for multi-version coexistence). Add an `analytics` service stub that consumes `OrderPlaced` to demonstrate that two services can independently regenerate from the same `.avsc`.

Schema evolution rules to internalize: adding a field with a default is backward-compatible (consumers on the old schema can still read; consumers on the new schema get the default for old records); removing a field with a default is forward-compatible; renaming requires `aliases`; changing types is almost always incompatible. The `BACKWARD` strategy lets consumers be upgraded *before* producers; `FORWARD` is the inverse; `FULL` requires both; `FULL_TRANSITIVE` requires the new schema to be compatible with every prior version, which is what you want for a long-lived event store.

Labs for Stage 3:

**Lab 3.1 — `avro-generated-pojos`** — purely a Gradle build that generates Kotlin-friendly Java classes from `.avsc`; teaches `SpecificRecord` versus `GenericRecord`.

**Lab 3.2 — `schema-evolution-ci`** — a producer publishes `v1`, then you change the schema, run the Confluent Maven plugin's `test-compatibility` goal, see it pass for `BACKWARD` and fail for an incompatible change.

**Lab 3.3 — `apicurio-vs-confluent`** — same producer/consumer wired against Apicurio Registry instead of Confluent's, demonstrating the swap is a serializer-class change (`io.apicurio.registry.serde.avro.AvroKafkaSerializer`) plus a few `apicurio.registry.*` properties.

**Lab 3.4 — `multi-schema-on-one-topic`** — uses Apicurio's `RecordIdStrategy` / Confluent's `RecordNameStrategy` to publish two different event types to the same topic, decoded by the consumer.

Gotchas: the Spring Cloud Schema Registry project (with `@EnableSchemaRegistryClient`) is *different* from Confluent's Schema Registry — for new code prefer Confluent's `kafka-avro-serializer`, since it is the de facto standard and works directly with the Apache Kafka client without going through Spring Cloud Stream's message converters. With `JacksonJsonDeserializer` you had to set `trusted.packages`; with Avro you do not, because the wire format identifies the schema by ID, not by Java class name. Don't put Avro-generated classes in `kotlin/`; put them in `java/` (generated) — the Gradle plugin defaults to `build/generated-main-avro-java`.

### Stage 4 — Spring Cloud Stream with the functional model and Kafka binder

Stage 4 introduces **Spring Cloud Stream** alongside raw spring-kafka. The pedagogical point is not "SCS is better than spring-kafka" — it is that they solve different problems. Raw `@KafkaListener` gives you everything Spring Kafka exposes (rebalance listeners, manual partition assignment, share consumers, the AfterRollbackProcessor, fine-grained container properties). Spring Cloud Stream's functional model gives you portability across brokers (Kafka, RabbitMQ, Pulsar, Kinesis), declarative `Function<I,O>` beans, multi-binder support, and best-in-class integration with Kafka Streams.

The functional binding convention is the heart of it. A `@Bean` of type `java.util.function.Consumer<T>` named `myConsumer` automatically gets a binding `myConsumer-in-0`; a `Function<I,O>` gets both `-in-0` and `-out-0`; a `Supplier<T>` gets `-out-0`. You then map those binding names to actual Kafka topics via `spring.cloud.stream.bindings.*.destination`.

```kotlin
@SpringBootApplication
class AnalyticsApplication {
    /** Read OrderPlaced; emit OrderRevenue keyed by customerId. */
    @Bean
    fun computeRevenue(): Function<OrderPlaced, OrderRevenue> = Function { e ->
        OrderRevenue.newBuilder()
            .setCustomerId(e.customerId)
            .setRevenueKrw(e.totalKrw)
            .setAsOf(Instant.now().toEpochMilli())
            .build()
    }

    /** A purely consuming function (no output). */
    @Bean
    fun audit(): Consumer<OrderPlaced> = Consumer { e ->
        log.info("audit: {}", e.orderId)
    }

    /** Reactive variant (Project Reactor). Useful for back-pressure. */
    @Bean
    fun enrichReactive(): Function<Flux<OrderPlaced>, Flux<OrderEnriched>> = Function { flux ->
        flux.flatMap { e -> webClient.lookupCustomer(e.customerId).map { c -> enrich(e, c) } }
    }
}
```

```yaml
spring:
  cloud:
    function:
      definition: computeRevenue;audit;enrichReactive
    stream:
      kafka:
        binder:
          brokers: localhost:9092
          configuration:
            schema.registry.url: http://schema-registry:8081
            specific.avro.reader: true
      bindings:
        computeRevenue-in-0:
          destination: orderflow.orders
          group: analytics-revenue
          consumer:
            useNativeDecoding: true
            configuration:
              value.deserializer: io.confluent.kafka.serializers.KafkaAvroDeserializer
        computeRevenue-out-0:
          destination: orderflow.order-revenue
          producer:
            useNativeEncoding: true
            configuration:
              value.serializer: io.confluent.kafka.serializers.KafkaAvroSerializer
        audit-in-0:
          destination: orderflow.orders
          group: analytics-audit
        enrichReactive-in-0:
          destination: orderflow.orders
          group: analytics-enrich
```

Three SCS patterns to learn here: **function composition** via `|` in `spring.cloud.function.definition` (`validate|enrich|emit` becomes one pipeline); **`StreamBridge`** for ad-hoc publishing outside any binding (useful when an HTTP endpoint needs to publish without a `Supplier`); and **DLQ via binder** (`spring.cloud.stream.kafka.bindings.<name>.consumer.enableDlq: true` plus `dlqName`).

OrderFlow Stage 4 delta: introduce the `analytics` service as a Spring Cloud Stream app with `computeRevenue` and `audit` functions; keep `order-api` and `fulfillment` on raw spring-kafka. Add a `notification` service that uses `StreamBridge` for one-off "send SMS" events triggered by an HTTP webhook.

Labs:

**Lab 4.1 — `scs-functional-hello`** — single `Function<String,String>` bean, one input topic, one output topic.

**Lab 4.2 — `scs-function-composition`** — `validate|enrich|persist` chained via `spring.cloud.function.definition`.

**Lab 4.3 — `scs-multi-binder`** — same app binds Kafka *and* RabbitMQ, routing different functions to different brokers.

**Lab 4.4 — `streambridge-ad-hoc`** — `POST /publish/{topic}` endpoint that uses `StreamBridge.send(...)`.

Gotchas: SCS uses *message converters* by default which means JSON via Jackson — to use Avro natively you set `useNativeEncoding/Decoding: true` per binding, otherwise SCS will try to convert payloads into byte arrays via its converter chain. SCS function bindings consume one message at a time by default; if you want batch consumption use `spring.cloud.stream.bindings.<name>.consumer.batch-mode: true` and accept `List<T>`. KIP-932 share-consumer support is not yet in the Spring Cloud Stream Kafka binder (only in raw spring-kafka 4.x — there's an open GitHub issue #3145 tracking this on the spring-cloud-stream repo); if you need share groups today use `@KafkaListener`.

### Stage 5 — Transactional patterns: KafkaAwareTransactionManager, why DB+Kafka is hard, and the transactional outbox

Stage 5 is the conceptual hinge of the entire curriculum. The question is: if your listener reads from Kafka, updates Aurora MySQL, and writes another Kafka message, can you make that atomic? The honest answer is *no*, not across a database and Kafka. You can get exactly-once *within* Kafka (read-from-topic + write-to-topic + commit-offsets are atomic via a Kafka transaction), but the moment you add a JPA write, you have two independent transactional resources and no two-phase commit protocol between them — so any pretense of cross-system atomicity is wrong.

Spring Kafka 4 gives you two tools and one anti-pattern. The two tools are `KafkaAwareTransactionManager` (which the container uses to make read-process-write atomic on the Kafka side, the basis for exactly-once_v2) and the **transactional outbox** pattern. The anti-pattern is `ChainedKafkaTransactionManager`, deprecated since 2.7, which gives the *illusion* of cross-resource atomicity by best-effort ordering of commits — it cannot rescue you when one resource commits and the other crashes.

`KafkaAwareTransactionManager` setup in Spring Boot 4 is one property plus one bean. Setting `spring.kafka.producer.transaction-id-prefix` triggers auto-configuration of a `KafkaTransactionManager` and wires it into listener containers. The container then starts a Kafka transaction before invoking the listener; any `KafkaTemplate.send()` calls inside participate; on success, offsets are sent to the transaction via `sendOffsetsToTransaction()` and committed atomically. Note that `ContainerProperties.setTransactionManager(PlatformTransactionManager)` is `@Deprecated(forRemoval=true, since="4.0")` in favor of `setKafkaAwareTransactionManager(KafkaAwareTransactionManager)` — narrower type, clearer intent (this appears in the 4.0.5 deprecated-list and the `ContainerProperties` Javadoc).

```kotlin
@Configuration
class KafkaTxConfig {
    @Bean
    fun kafkaListenerContainerFactory(
        cf: ConsumerFactory<String, Any>,
        tm: KafkaAwareTransactionManager<String, Any>
    ): ConcurrentKafkaListenerContainerFactory<String, Any> {
        val factory = ConcurrentKafkaListenerContainerFactory<String, Any>()
        factory.consumerFactory = cf
        // New API in 4.0 — replaces the deprecated setTransactionManager(...)
        factory.containerProperties.setKafkaAwareTransactionManager(tm)
        return factory
    }
}

@Service
class PaymentProcessor(private val kafkaTemplate: KafkaTemplate<String, Any>) {
    @KafkaListener(topics = ["orderflow.payments-requested"], groupId = "payment-eos")
    fun process(event: PaymentRequested) {
        val approved = decide(event)
        kafkaTemplate.send("orderflow.payments-decided", event.orderId, approved)
        // Listener returns normally → container commits offsets to the same Kafka transaction.
        // Throws → container rolls back, AfterRollbackProcessor decides retry semantics.
    }
}
```

For *downstream* consumers to see only committed messages, they must set `isolation.level: read_committed`. Otherwise they'll read aborted-transaction records and you've undone your own work.

Now the database half. Suppose the same listener also has to update an Aurora MySQL row. You can annotate the listener with `@Transactional` (using your JPA transaction manager) — the call chain is: container starts Kafka tx → invokes listener → Spring's `@Transactional` interceptor starts JPA tx → listener body runs both `KafkaTemplate.send` and `repository.save` → JPA tx commits → container commits Kafka tx. If the JPA commit fails, the Kafka tx is rolled back. If the *Kafka* commit fails (e.g., broker crash after JPA commit), the DB has the row and Kafka does not — duplicate processing of the original record will retry the listener and write a *second* DB row unless your DB write is idempotent (e.g., upsert by `orderId`). This is "best-effort 1PC" and is the right pattern when DB writes are idempotent.

When DB writes are *not* idempotent (e.g., inserting an immutable event), the correct pattern is the **transactional outbox**. In Stage 5 of OrderFlow you implement it with Spring Data JPA against Aurora MySQL: every command handler does `orderRepository.save(order)` and `outboxRepository.save(OutboxEvent(...))` in the *same* JPA transaction. After commit, the events get to Kafka by one of three mechanisms:

**(a) Debezium MySQL source connector + Debezium's `EventRouter` SMT** reading the Aurora binlog and routing rows in the `outbox` table to Kafka topics. This is the gold standard: zero polling, near-real-time, fully decoupled from the application. You enable Aurora MySQL binlog (`binlog_format=ROW`, `binlog_row_image=FULL`) and deploy Debezium via Kafka Connect. The Debezium Outbox Event Router takes columns `aggregate_type`, `aggregate_id`, `type`, `payload` and routes to topics by aggregate type (`orders.events`, `payments.events`, ...).

**(b) Polling publisher** — a Spring `@Scheduled` job that selects `WHERE published_at IS NULL`, publishes to Kafka, and updates `published_at`. Simpler operationally, lower fan-out, but a polling lag.

**(c) `@TransactionalEventListener(phase = AFTER_COMMIT)`** for the simpler in-process variant — your service publishes a Spring application event inside the `@Transactional` method, and a `@TransactionalEventListener` bean publishes to Kafka *after* the JPA commit. The honest caveat to teach yourself is encoded directly in the Spring Framework Javadoc for `TransactionalEventListener`, which warns: "if the TransactionPhase is set to AFTER_COMMIT (the default), AFTER_ROLLBACK, or AFTER_COMPLETION, the transaction will have been committed or rolled back already, but the transactional resources might still be active and accessible." In practice this means: this is *at-least-once and not crash-safe* — if the JVM dies between the JPA commit and `KafkaTemplate.send()`, the event is lost. Use it when the cost of losing an event in a JVM crash is acceptable; use Debezium or the polling publisher when it is not.

```kotlin
// In-process variant, useful for low-stakes events:
@Service
class OrderService(
    private val orderRepo: OrderRepository,
    private val events: ApplicationEventPublisher
) {
    @Transactional
    fun placeOrder(req: PlaceOrderRequest): UUID {
        val order = orderRepo.save(Order(...))
        events.publishEvent(OrderPlacedDomainEvent(order.id, order.totalKrw))
        return order.id
    }
}

@Component
class OrderEventKafkaPublisher(private val kafka: KafkaTemplate<String, OrderPlaced>) {
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    fun publish(e: OrderPlacedDomainEvent) {
        // Runs *after* JPA commit. If the process dies here, the event is lost.
        kafka.send("orderflow.orders", e.orderId.toString(), e.toAvro())
    }
}
```

OrderFlow Stage 5 delta: convert `order-api` to write to an `outbox_event` table in Aurora MySQL alongside the `orders` table in the same JPA transaction; deploy Debezium connected to the Aurora binlog; configure the Outbox Event Router SMT (with `transforms.outbox.table.expand.json.payload=true`) to publish to `orderflow.orders` keyed by `aggregate_id`. Add a `payment-eos` service that exemplifies pure Kafka read-process-write with `KafkaAwareTransactionManager`. Note explicitly in the code comments that the two services use *different* mechanisms for *different* reasons.

Labs:

**Lab 5.1 — `kafka-tx-read-process-write`** — pure Kafka transactions, no DB. Shows that with `isolation.level=read_committed`, aborted transactions are invisible downstream.

**Lab 5.2 — `chained-tx-failure-modes`** — deliberately uses the deprecated chained transaction manager to surface its failure modes and explain why outbox is the proper alternative.

**Lab 5.3 — `outbox-with-debezium`** — Aurora-equivalent MySQL via Testcontainers, Debezium Connect container, outbox table with `EventRouter` SMT, demonstrate at-least-once after a Kafka outage with the DB still committing.

**Lab 5.4 — `outbox-after-commit-event`** — pure in-process `@TransactionalEventListener(AFTER_COMMIT)` variant, with a deliberately scripted JVM kill to show event loss.

Gotchas: `setKafkaAwareTransactionManager` replaces `setTransactionManager(PlatformTransactionManager)` in 4.0 — your IDE will flag it as terminally deprecated (the deprecated-list page at `docs.spring.io/spring-kafka/api/deprecated-list.html` lists it explicitly). With `read_committed`, consumers see records only after the transaction commits, which adds latency equal to your transaction duration plus broker propagation; for a noisy 10ms transactional producer this is fine, for batch-style transactions it may be hundreds of milliseconds. Debezium's MySQL connector requires `REPLICATION SLAVE` and `REPLICATION CLIENT` grants on the Aurora user and binlog enabled with row format — coordinate with your AWS team in Seoul on parameter groups. Debezium's `EventRouter` expands JSON payloads only if `transforms.outbox.table.expand.json.payload=true`.

### Stage 6 — Kafka Streams in Spring Boot: windows, joins, state stores, interactive queries

Stage 6 introduces the streams DSL. Two libraries matter: `spring-kafka`'s `@EnableKafkaStreams` plus `StreamsBuilderFactoryBean` (low-level, full Kafka Streams API), and `spring-cloud-stream-binder-kafka-streams` (the binder that lets you write `Function<KStream<...>, KStream<...>>` beans and treats KStream/KTable/GlobalKTable as first-class binding types).

Pick the binder for new code unless you need direct access to the `KafkaStreams` lifecycle. The binder example for OrderFlow's analytics service:

```kotlin
@SpringBootApplication
class AnalyticsStreamsApplication {

    /** Aggregate revenue per customer per 5-minute window. */
    @Bean
    fun revenuePerCustomer(): Function<KStream<String, OrderPlaced>, KStream<String, RevenueWindow>> =
        Function { stream ->
            stream
                .groupBy({ _, v -> v.customerId.toString() }, Grouped.with(Serdes.String(), avroSerde()))
                .windowedBy(TimeWindows.ofSizeAndGrace(Duration.ofMinutes(5), Duration.ofMinutes(1)))
                .aggregate(
                    { RevenueWindow(0L) },
                    { _, ord, agg -> RevenueWindow(agg.totalKrw + ord.totalKrw) },
                    Materialized.`as`<String, RevenueWindow, WindowStore<Bytes, ByteArray>>("revenue-store")
                )
                .toStream()
                .map { wk, v -> KeyValue(wk.key(), v) }
        }

    /** Join orders against a customer reference GlobalKTable. */
    @Bean
    fun enrich(): BiFunction<KStream<String, OrderPlaced>, GlobalKTable<String, Customer>, KStream<String, EnrichedOrder>> =
        BiFunction { orders, customers ->
            orders.join(customers, { _, ord -> ord.customerId.toString() }) { ord, cust -> enrich(ord, cust) }
        }
}
```

```yaml
spring:
  cloud:
    function:
      definition: revenuePerCustomer;enrich
    stream:
      kafka:
        streams:
          binder:
            applicationId: orderflow-analytics
            configuration:
              default.key.serde: org.apache.kafka.common.serialization.Serdes$StringSerde
              default.value.serde: io.confluent.kafka.streams.serdes.avro.SpecificAvroSerde
              schema.registry.url: http://schema-registry:8081
              processing.guarantee: exactly_once_v2
              # KIP-1071 server-side streams rebalance is GA in Kafka 4.2:
              group.protocol: streams
              application.server: ${HOSTNAME}:8080
      bindings:
        revenuePerCustomer-in-0:
          destination: orderflow.orders
        revenuePerCustomer-out-0:
          destination: orderflow.revenue-windows
        enrich-in-0: { destination: orderflow.orders }
        enrich-in-1: { destination: orderflow.customers }
        enrich-out-0: { destination: orderflow.enriched-orders }
```

Interactive Queries: every Streams instance has a local state store that is queryable from anywhere in the *same JVM* and discoverable across instances via `application.server`. Spring Cloud Stream's binder gives you `InteractiveQueryService` (and Spring Kafka's `KafkaStreamsInteractiveQueryService` as the lower-level variant), which finds the instance hosting a given key and either reads locally or delegates over HTTP:

```kotlin
@RestController
@RequestMapping("/revenue")
class RevenueQueryController(
    private val iq: InteractiveQueryService,
    private val restClient: RestClient
) {
    @GetMapping("/{customerId}")
    fun byCustomer(@PathVariable customerId: String): RevenueResponse {
        val host = iq.getHostInfo("revenue-store", customerId, Serdes.String().serializer())
        return if (host == iq.currentHostInfo) {
            // Local
            val store = iq.getQueryableStore("revenue-store", QueryableStoreTypes.keyValueStore<String, RevenueWindow>())
            RevenueResponse(customerId, store.get(customerId)?.totalKrw ?: 0L)
        } else {
            // Remote — call peer instance
            restClient.get().uri("http://${host.host()}:${host.port()}/revenue/$customerId")
                .retrieve().body(RevenueResponse::class.java)!!
        }
    }
}
```

OrderFlow Stage 6 delta: `analytics` service grows from a simple Function to a Kafka Streams topology with a 5-minute tumbling window per customer, a `GlobalKTable` of `Customer` reference data, and a `GET /revenue/{customerId}` REST endpoint that uses interactive queries. Add a health indicator (`KafkaStreamsHealthIndicator`) so Actuator's `/health` reports stream state.

Labs:

**Lab 6.1 — `streams-wordcount-spring`** — the canonical word-count topology with a state store materialized as `Materialized.as("counts")`.

**Lab 6.2 — `topology-test-driver-spring`** — uses Kafka Streams' `TopologyTestDriver` inside a Spring `@SpringBootTest` to unit-test the topology in milliseconds, without any broker.

**Lab 6.3 — `iq-multi-instance`** — runs two instances of a Spring Boot Streams app, sees state partitioned across them, demonstrates `application.server` discovery.

**Lab 6.4 — `streams-dlq-kip-1034`** — uses Kafka 4.2's new `Response` class with DLQ records in `DeserializationExceptionHandler` to route bad records to a DLT inside the topology itself (a Kafka 4.2 KIP-1034 feature now exposed through Spring Kafka's updated `RecoveringDeserializationExceptionHandler`, `RecoveringProcessingExceptionHandler`, and `RecoveringProductionExceptionHandler` per the 4.1.0-RC1 release notes).

Gotchas: `exactly_once_v2` requires `transactional.id` to be unique per instance — Spring Kafka derives it from `application.id` plus instance index, which works for autoscaling only if `application.server` is unique. `GlobalKTable` replicates *every* partition into *every* instance, which is fine for small reference data but ruinous for large topics; if your "global" data is big use a `KTable` with co-partitioning. Streams 4.2's new server-side rebalance protocol (KIP-1071) requires `group.protocol=streams` and a broker on Kafka 4.2+. Spring Cloud Stream binder for Kafka Streams sometimes lags raw Streams by a few releases; check the binder's compatibility matrix when adopting brand-new Streams features.

### Stage 7 — Event-driven microservices: choreography sagas, orchestration sagas, inbox, idempotent consumers

Stage 7 is the patterns chapter. You learn the two saga flavors, the inbox pattern, and concrete idempotency techniques. The OrderFlow system at the end of this stage already looks like a real distributed system: order placement triggers a payment, payment success triggers a fulfillment, fulfillment success triggers a notification, and any failure triggers compensating actions.

A **choreography saga** is a chain of services that each react to events and emit the next event with no central coordinator. The advantage is operational simplicity: no orchestrator to deploy. The disadvantages are tight coupling (downstream services have to know upstream event names), hidden cyclic dependencies, and difficulty reasoning about the global state. In OrderFlow choreography, `fulfillment` listens to `payment.approved` and emits `order.fulfilled`; `notification` listens to `order.fulfilled` and emits an SMS. Each service has its own `@KafkaListener` and its own outbox.

An **orchestration saga** uses a central coordinator that issues commands to participants and reacts to their replies, modeling the workflow as a state machine. The advantage is explicit, debuggable workflow; the disadvantage is that the orchestrator is a critical dependency and you must handle its own crash recovery. Spring State Machine is one option; rolling your own with a `saga_state` table in Aurora is often simpler and is what we recommend for OrderFlow's `payment-orchestrator` service. The orchestrator persists state transitions transactionally with the outbox pattern so its replies are durable.

Sketch of the orchestrator:

```kotlin
@Entity
data class PaymentSaga(
    @Id val orderId: UUID,
    @Enumerated(EnumType.STRING) var state: PaymentSagaState,
    val totalKrw: Long,
    var lastTransition: Instant
)

enum class PaymentSagaState { STARTED, RESERVE_REQUESTED, RESERVED, CHARGED, FAILED, COMPENSATED }

@Service
class PaymentOrchestrator(
    private val sagas: PaymentSagaRepository,
    private val outbox: OutboxRepository
) {
    @KafkaListener(topics = ["orderflow.orders"], groupId = "payment-orchestrator")
    @Transactional
    fun onOrderPlaced(e: OrderPlaced) {
        val saga = PaymentSaga(e.orderId, STARTED, e.totalKrw, Instant.now())
        sagas.save(saga)
        outbox.save(OutboxEvent("inventory.reserve-requested", e.orderId.toString(), ...))
        saga.state = RESERVE_REQUESTED
    }

    @KafkaListener(topics = ["orderflow.inventory.reserved"], groupId = "payment-orchestrator")
    @Transactional
    fun onReserved(e: InventoryReserved) {
        val saga = sagas.findById(e.orderId).orElseThrow()
        check(saga.state == RESERVE_REQUESTED) { "wrong state ${saga.state}" }
        saga.state = RESERVED
        outbox.save(OutboxEvent("payment.charge-requested", e.orderId.toString(), ...))
    }

    @KafkaListener(topics = ["orderflow.payment.failed"], groupId = "payment-orchestrator")
    @Transactional
    fun onPaymentFailed(e: PaymentFailed) {
        val saga = sagas.findById(e.orderId).orElseThrow()
        saga.state = FAILED
        // Compensating transaction: release the inventory reservation.
        outbox.save(OutboxEvent("inventory.release-requested", e.orderId.toString(), ...))
    }
}
```

The orchestrator and the participants must each implement the **inbox pattern** for idempotent consumption. Kafka delivers at-least-once, so any consumer will eventually see a duplicate (rebalance, retry, replay-from-DLT). The inbox is a `processed_messages(message_id PRIMARY KEY, processed_at)` table; the listener checks `WHERE message_id = ?` inside the same JPA transaction as its business write; if the row already exists, the message has been seen and the listener returns without effect. The `message_id` is whatever uniquely identifies the message — typically a producer-supplied UUID in a header (`messageId`) plus the topic name to avoid collisions across topics.

```kotlin
@Service
class NotificationListener(
    private val processed: ProcessedMessageRepository,
    private val sms: SmsClient
) {
    @KafkaListener(topics = ["orderflow.order.fulfilled"], groupId = "notification")
    @Transactional
    fun onFulfilled(event: OrderFulfilled, @Header("messageId") messageId: String) {
        if (processed.existsById(messageId)) return // idempotent: already processed
        processed.save(ProcessedMessage(messageId, Instant.now()))
        sms.send(event.customerId, "Your order ${event.orderId} has shipped")
    }
}
```

Non-blocking retries with `@RetryableTopic` plug into this nicely. Use **`@BackOff` (capital O)** — the new annotation in `org.springframework.kafka.annotation` that replaced Spring Retry's `@Backoff` in 4.0. The What's New page for Spring Kafka 4 documents the migration explicitly: "Spring for Apache Kafka has removed its dependency on Spring Retry... the annotation has been moved to Spring Kafka as `@BackOff` with the following improvements: Harmonized naming: Uses `@BackOff` instead of `@Backoff` for consistency; Expression evaluation: All string attributes support SpEL expressions and property placeholders; Duration format support: String attributes accept `java.util.Duration` formats (e.g., `\"2s\"`, `\"500ms\"`)":

```kotlin
@Component
class NotificationConsumer {
    @RetryableTopic(
        attempts = "5",
        backOff = BackOff(delayString = "2s", maxDelayString = "60s", multiplier = 2.0),
        include = [RetryableSmsException::class],
        topicSuffixingStrategy = TopicSuffixingStrategy.SUFFIX_WITH_INDEX_VALUE,
        dltStrategy = DltStrategy.FAIL_ON_ERROR,
        autoCreateTopics = "true"
    )
    @KafkaListener(topics = ["orderflow.order.fulfilled"], groupId = "notification")
    fun handle(event: OrderFulfilled) { sms.send(...) }

    @DltHandler
    fun dlt(event: OrderFulfilled, @Header(KafkaHeaders.EXCEPTION_FQCN) fqcn: String) {
        log.error("DLT for {}: {}", event.orderId, fqcn)
    }
}
```

OrderFlow Stage 7 delta: a full saga executes end-to-end. `order-api` emits `OrderPlaced` (via outbox/Debezium); `payment-orchestrator` (Aurora-backed state machine) issues commands to `inventory` and `payment`; `fulfillment` reacts choreographically to `payment.approved`; `notification` is the idempotent consumer with the inbox table. Every listener uses `@RetryableTopic` for transient failures and routes to per-service DLTs.

Labs:

**Lab 7.1 — `choreography-saga`** — three services, three topics, no orchestrator. Trace a happy path then a failure that needs a compensating event.

**Lab 7.2 — `orchestration-saga-hand-rolled`** — orchestrator with a Postgres `saga_state` table, no Spring State Machine.

**Lab 7.3 — `orchestration-saga-spring-state-machine`** — same business logic via Spring State Machine, comparing ergonomics and operational complexity.

**Lab 7.4 — `inbox-idempotent-consumer`** — a deliberately duplicating producer (`enable.idempotence=false`, ack timeout 1ms) feeding a consumer that uses the inbox table; observe exactly-one side-effect.

Gotchas: `@RetryableTopic` requires a `KafkaTemplate<String, Object>` bean to forward to retry topics — without it you'll see `NoSuchBeanDefinitionException` on startup. The DLT topic is named `<topic>-dlt` by default; configure `dltTopicSuffix` if you want `.DLT`. `@RetryableTopic` and `KafkaTransactionManager` interact in subtle ways — when the listener is transactional, the retry forward is *also* transactional, which may not be what you want; consult the Spring Kafka reference on Retry Topics with Transactions. Spring State Machine adds startup complexity (state machine persistence, event payloads as headers) — for most sagas a plain JPA entity is enough.

### Stage 8 — CQRS and Event Sourcing in Spring Boot

Stage 8 separates the write side from the read side. The write side accepts commands via REST, validates them, applies them to aggregates, and publishes events through the outbox (Stages 5–7). The read side maintains denormalized projections in stores optimized for queries — Postgres for transactional reads, Elasticsearch for full-text, Redis for hot caches.

OrderFlow Stage 8 delta: introduce the `read-model` service, which has a stack of `@KafkaListener` methods that subscribe to `orderflow.orders`, `orderflow.payments.decided`, `orderflow.order.fulfilled`, and project a denormalized `order_view` table in Postgres plus an `orders_search` index in Elasticsearch:

```kotlin
@Service
class OrderReadModelProjector(
    private val jdbc: JdbcTemplate,
    private val es: ElasticsearchClient,
    private val processed: ProcessedMessageRepository
) {
    @KafkaListener(topics = ["orderflow.orders"], groupId = "read-model")
    @Transactional("postgresTxManager")
    fun onPlaced(event: OrderPlaced, @Header("messageId") msgId: String) {
        if (!processed.markIfAbsent(msgId)) return
        jdbc.update("""
            INSERT INTO order_view(order_id, customer_id, status, total_krw, placed_at)
            VALUES (?, ?, 'PLACED', ?, ?)
            ON CONFLICT (order_id) DO NOTHING
        """, event.orderId, event.customerId, event.totalKrw, event.placedAt)
        es.index { it.index("orders").id(event.orderId.toString())
                     .document(OrderSearchDoc(event)) }
    }

    @KafkaListener(topics = ["orderflow.order.fulfilled"], groupId = "read-model")
    @Transactional("postgresTxManager")
    fun onFulfilled(event: OrderFulfilled, @Header("messageId") msgId: String) {
        if (!processed.markIfAbsent(msgId)) return
        jdbc.update("UPDATE order_view SET status='FULFILLED' WHERE order_id=?", event.orderId)
    }
}
```

The `inventory` service is the right place to introduce **event sourcing**: rather than storing the inventory's current state as a row, store the *sequence of events* (`StockReserved`, `StockReleased`, `StockShipped`) in an `inventory_events` table in Aurora, and rebuild current state by folding events. Snapshots accelerate startup — after every N events for a given aggregate ID, write a snapshot row capturing the folded state at that version; on load, find the latest snapshot and replay only the events after it.

```kotlin
@Entity
data class InventoryEvent(
    @Id val id: UUID = UUID.randomUUID(),
    val productId: UUID, val version: Long,
    @Enumerated(EnumType.STRING) val type: InventoryEventType,
    val quantity: Int, val occurredAt: Instant
)

@Service
class InventoryAggregateRepository(
    private val events: InventoryEventRepository,
    private val snapshots: InventorySnapshotRepository
) {
    fun load(productId: UUID): InventoryAggregate {
        val snap = snapshots.findLatestFor(productId)
        val baseline = snap?.toAggregate() ?: InventoryAggregate.zero(productId)
        val tail = events.findByProductIdAndVersionGreaterThan(productId, snap?.version ?: 0)
        return tail.fold(baseline) { agg, e -> agg.apply(e) }
    }

    @Transactional
    fun save(agg: InventoryAggregate) {
        agg.uncommittedEvents().forEach { events.save(it) }
        if (agg.version % 100 == 0L) snapshots.save(InventorySnapshot.from(agg))
    }
}
```

The read model for inventory is a much simpler `inventory_view(product_id, on_hand, reserved)` table fed by a `@KafkaListener` on the inventory event stream — same projection pattern as orders.

Labs:

**Lab 8.1 — `cqrs-read-model-postgres`** — Postgres-only projection, no ES, demonstrates that write side and read side can use different databases.

**Lab 8.2 — `event-sourced-aggregate`** — pure event sourcing with snapshots for one aggregate, no Kafka involvement; teaches the fold-events-to-rebuild pattern.

**Lab 8.3 — `replay-read-model`** — a `POST /admin/read-model/replay` endpoint that resets the consumer group offset to earliest and rebuilds the projection from scratch, showing the famous "throw away the projection and rebuild" power of event sourcing.

**Lab 8.4 — `event-carried-state-transfer`** — `inventory` publishes a compacted `inventory.snapshots` topic; other services maintain a local `GlobalKTable` of inventory state via Kafka Streams, avoiding cross-service synchronous calls.

Gotchas: projections must be idempotent because consumers see at-least-once delivery — use `ON CONFLICT DO NOTHING`/`DO UPDATE` and the inbox table. Replaying a projection requires careful coordination: pause writes to the read store, reset the consumer group, and let it catch up. Event-sourced aggregates can have ballooning event tables — set up snapshot policies and consider archival of old events. Spring Data JPA's `@Version` does *not* play well with event sourcing because the "version" is per aggregate, not per row; manage versions in domain code.

### Stage 9 — Production-grade: security, deployment, monitoring, runbooks

Stage 9 takes OrderFlow from "works on my machine and in CI with Testcontainers" to "deployed on AWS in Seoul with MSK". Three concrete focus areas: security, full-stack testing, and observability.

**Security against AWS MSK with IAM authentication.** MSK supports four authentication mechanisms: PLAINTEXT (don't), TLS mutual auth, SASL/SCRAM, and SASL/AWS_MSK_IAM. IAM is the recommended choice in AWS because it ties Kafka access to your existing IAM roles (via IRSA on EKS, or instance profiles on EC2). The `aws-msk-iam-auth` library provides the SASL callback. Pin to a recent version: as of May 2026 the latest release is **2.3.6** on the `aws/aws-msk-iam-auth` GitHub repository, which superseded the 2.3.5 release tagged "Latest" on November 5, 2025 that fixed CVE-2025-58056 and CVE-2025-58057; do not pin to the older 2.2.x line.

```kotlin
dependencies {
    implementation("software.amazon.msk:aws-msk-iam-auth:2.3.6")
}
```

```yaml
spring:
  kafka:
    bootstrap-servers: ${MSK_BOOTSTRAP_SERVERS}
    properties:
      security.protocol: SASL_SSL
      sasl.mechanism: AWS_MSK_IAM
      sasl.jaas.config: software.amazon.msk.auth.iam.IAMLoginModule required;
      sasl.client.callback.handler.class: software.amazon.msk.auth.iam.IAMClientCallbackHandler
      # On EKS with IRSA you do *not* set keys here — the SDK chain finds them via the pod's projected token.
```

For SASL/SCRAM (still useful when running outside AWS or for non-AWS clients):

```yaml
spring:
  kafka:
    properties:
      security.protocol: SASL_SSL
      sasl.mechanism: SCRAM-SHA-512
      sasl.jaas.config: |
        org.apache.kafka.common.security.scram.ScramLoginModule required
        username="${KAFKA_USER}" password="${KAFKA_PASS}";
      ssl.truststore.location: /etc/ssl/kafka.truststore.jks
      ssl.truststore.password: ${TRUSTSTORE_PASS}
```

For OAuth/OIDC against Confluent Cloud or an internal IdP, use `sasl.mechanism=OAUTHBEARER` and a JAAS module that fetches a token from your token endpoint. Spring Security's OAuth2 client can be wired through a custom `AuthenticateCallbackHandler` if you need token caching and refresh.

Secrets management: in EKS use AWS Secrets Manager via the Secrets Store CSI Driver, mounting secrets as files referenced from `application-prod.yml` via `${...}` placeholders; in Spring Cloud Config, encrypt secrets at rest with the Spring Cloud Config server's symmetric key.

**Advanced testing.** Beyond `@EmbeddedKafka` and Testcontainers (Stages 1–2), Stage 9 introduces:

- **Contract tests** with Spring Cloud Contract — define each event as a Groovy/YAML contract, generate stubs the producer must satisfy and the consumer's stub broker, and run them on every CI build to catch breaking schema/event changes *before* deployment.
- **`TopologyTestDriver`** for Kafka Streams unit tests inside a Spring context, asserting topology behavior in milliseconds.
- **Integration tests for `@RetryableTopic`** by counting attempts, verifying DLT delivery with a test consumer, and asserting the order of retry topic forwards.
- **Chaos tests** with Testcontainers' Toxiproxy module: inject network latency and broker disconnects, verify the producer retries and the consumer rebalances cleanly.

**Observability runbooks.** Prometheus scrapes `/actuator/prometheus` for both Spring's metrics and Kafka client metrics (the `KafkaClientMetrics` Factory Listener exposes the native Kafka producer/consumer metrics). Standard Grafana dashboards (the Confluent and Strimzi communities maintain Spring-friendly dashboards) cover: producer record-send-rate and -error-rate, consumer records-lag-max (alerts at SLA threshold), `spring.kafka.listener` p99 duration, `spring.kafka.template` p99 duration, transaction abort rate, DLT publish rate. Tracing: Micrometer Observation → OTLP → your collector → Jaeger or Tempo, with W3C trace-context headers on every message. Logging: JSON-structured logs via Logback's `logstash-encoder`, with `traceId`/`spanId`/`tenantId` in MDC pattern.

Runbooks for OrderFlow you should write at this stage:
- **DLT triage**: how to inspect DLT records, decide whether to fix and replay or drop, run the `POST /admin/dlt/replay` endpoint, audit-log every replay.
- **Schema rollback**: how to demote an incompatible schema in Confluent Schema Registry and redeploy the producer.
- **Rebalance storms**: how to use KIP-848's new consumer rebalance protocol (set `group.protocol=consumer` on consumers) to avoid stop-the-world rebalances.

Labs:

**Lab 9.1 — `msk-iam-localstack`** — Spring Boot app authenticating to LocalStack's MSK-IAM-emulating Kafka cluster, then deployed against a real MSK cluster from EKS.

**Lab 9.2 — `contract-test-orderflow-orders`** — producer contract for `OrderPlaced` defined in Groovy DSL; consumer test uses Stub Runner to fire the contract message and assert read-model projection.

**Lab 9.3 — `streams-topology-test-driver`** — drive the analytics topology with `TopologyTestDriver`, asserting that 10 input records yield exactly 2 windowed outputs.

**Lab 9.4 — `chaos-toxiproxy-broker`** — simulate broker outage; verify producer retries, consumer pause/resume, no lost messages, no duplicated DB writes.

Gotchas: MSK IAM with dynamic STS sessions (EKS Pod Identity) can hit re-authentication failures if the session name changes — there's a known issue in the `aws-msk-iam-auth` library to track. SASL/SSL truststore files must be present at the configured path in your container — a frequent source of "could not connect" errors that look like network issues but are TLS misconfigurations. Spring Cloud Contract for messaging is a bit awkward and requires implementing `MessageVerifierSender`/`MessageVerifierReceiver` against Kafka explicitly — budget time. Don't enable 100% trace sampling in prod; use `probability` of 0.1–1% and structured logging for the long tail.

### Stage 10 — Specialization deep dives

Stage 10 is a choose-your-own-adventure. By now OrderFlow is a working multi-service system; pick one or two of the following to go deep on. Each deep dive justifies a one-to-two-week study sprint and a corresponding capstone enhancement to OrderFlow.

**Streams performance tuning.** Topics for partitioning, RocksDB tuning (block cache size, write buffer size, compaction triggers), state-store sizing, Kafka Streams' new server-side rebalance protocol (KIP-1071), Streams DLQ support (KIP-1034), anchored wall-clock punctuation (Kafka 4.2). Add a `bench` profile to OrderFlow's analytics service that generates 1M records and reports end-to-end latency.

**Multi-region active-active.** Kafka MirrorMaker 2 versus Confluent Cluster Linking, Aurora MySQL global database, conflict resolution strategies for read models, regional service identifiers as topic prefixes. Add a Seoul-Tokyo replica to OrderFlow and demonstrate failover.

**Debezium for legacy DB integration.** Beyond outbox: directly capturing change streams from legacy MySQL/SQL Server tables, applying transformations, and feeding them into the OrderFlow event bus. Use Debezium Server (without Kafka Connect) for lighter deployments.

**Kafka 4.2 share groups (KIP-932) for queue-style workloads.** Spring Kafka 4 provides `ShareConsumerFactory` and `ShareKafkaMessageListenerContainer`. Convert OrderFlow's `notification` service to consume via a share group so multiple consumer threads can cooperatively consume a single partition's records — perfect for fan-out work that doesn't need ordering. Per the official Apache Kafka 4.2 upgrade guide, "Queues for Kafka (KIP-932) is production-ready in Apache Kafka 4.2."

```kotlin
@KafkaListener(
    topics = ["orderflow.notifications"],
    groupId = "notifications-share",
    containerFactory = "shareKafkaListenerContainerFactory"
)
fun notify(record: ConsumerRecord<String, NotificationEvent>, ack: ShareAcknowledgment) {
    try {
        sms.send(record.value())
        ack.acknowledge(AcknowledgeType.ACCEPT)
    } catch (e: RetryableException) {
        ack.acknowledge(AcknowledgeType.RELEASE)   // make it available to another consumer
    } catch (e: PermanentException) {
        ack.acknowledge(AcknowledgeType.REJECT)    // poison record — broker tracks delivery count
    } catch (e: LongRunningException) {
        // New in Kafka 4.2 / Spring Kafka 4.1: extend the lock without acknowledging yet.
        ack.renew()
    }
}
```

Note that the Spring Cloud Stream Kafka binder has not yet integrated KIP-932 share consumers (tracked in `spring-cloud-stream` GitHub issue #3145) — for now you must use raw spring-kafka. Spring Kafka 4.1.0-M2 also added the `RENEW` acknowledgment type exposed via `ShareAcknowledgment.renew()` for processing that may exceed `group.share.record.lock.duration.ms` (KIP-1222 in Kafka 4.2).

**Long-running workflows.** Compare hand-rolled sagas with Spring State Machine, Temporal, and Camunda for workflows that span hours or days (e.g., subscription renewals, multi-step KYC). Temporal in particular integrates cleanly with Kafka as an event source and gives you durable workflow execution semantics that sagas don't.

### The capstone OrderFlow system

After Stage 10, you have a Kotlin + Spring Boot 4.0 system organized as a Gradle multi-module build with these services:

- **order-api** — REST (`POST /orders`, `GET /orders/{id}`), Spring Data JPA against Aurora MySQL, transactional outbox → Debezium → Kafka, idempotency keys on the REST layer.
- **payment-orchestrator** — orchestration saga with state in Aurora, choreographs `inventory.reserve`, `payment.charge`, `inventory.release` (compensation). Idempotent via inbox.
- **inventory** — event-sourced aggregate with snapshots in Aurora; produces an `inventory.snapshots` compacted topic for downstream consumers.
- **fulfillment** — choreography consumer of `payment.approved`; writes a fulfillment record and emits `order.fulfilled`.
- **notification** — idempotent consumer with inbox + share-group consumption (Kafka 4.2 KIP-932) for parallel SMS dispatch.
- **analytics** — Spring Cloud Stream Kafka Streams binder; windowed revenue aggregations, GlobalKTable enrichment, interactive queries exposed via REST.
- **read-model** — CQRS read side that projects orders into Postgres and Elasticsearch.

All services share:
- Avro schemas registered in Confluent Schema Registry (with `FULL_TRANSITIVE` compatibility for the orders topic, `BACKWARD` for newer topics).
- Micrometer Observation tracing end-to-end with W3C headers.
- `@RetryableTopic` per service with topic-prefixed retry topics and DLTs.
- MSK IAM auth in prod, plaintext in dev (Testcontainers).
- Comprehensive Testcontainers-based integration tests, Spring Cloud Contract messaging contracts, and `TopologyTestDriver` unit tests.
- Actuator + Prometheus + Grafana dashboards; structured logs with `traceId`, `spanId`, `orderId`, `tenantId` in MDC.

## Recommendations

If you want a single concrete path from "Stage 1 today" to "OrderFlow capstone deployed to MSK," here is the cadence I would prescribe given your profile (PhD math, 10 years backend, Kotlin/Spring Boot/Aurora/AWS, Seoul):

**Weeks 1–2** (Stage 1–2): Build the OrderFlow skeleton with one service, `order-api`, on Spring Boot 4.0.6 + Spring Kafka 4.0.5 (the current alignment per the April 22, 2026 Spring blog). Get idempotent producer, manual ack, `DefaultErrorHandler`, DLT, and Micrometer Observation working with a Testcontainers integration test. Benchmark: 10K msgs/s on your laptop, end-to-end trace visible in Jaeger.

**Weeks 3–4** (Stage 3–4): Add Avro + Confluent Schema Registry; introduce the `analytics` service via Spring Cloud Stream's functional binder. Benchmark: a deliberate breaking schema change must fail CI's compatibility check.

**Weeks 5–7** (Stage 5): The transactional outbox stage is the most important and the one where most engineers go wrong. Spend a full week on it: implement the in-process `@TransactionalEventListener(AFTER_COMMIT)` variant, deliberately script a JVM kill to see event loss, then implement the Debezium variant and observe that the same kill no longer loses events. Benchmark: 99.999% delivery guarantee under chaos (kill -9 mid-transaction) with Debezium.

**Weeks 8–9** (Stage 6): Kafka Streams + interactive queries. Benchmark: query latency p99 < 20ms on a 100K-customer state store.

**Weeks 10–12** (Stage 7–8): The two saga flavors and CQRS. By the end of week 12 OrderFlow should be 6–7 services and indistinguishable from a real product.

**Weeks 13–14** (Stage 9): Production hardening. Deploy to an EKS cluster in `ap-northeast-2` against MSK with IAM auth, instrument Grafana dashboards, write the three runbooks above.

**Weeks 15+** (Stage 10): Pick one specialization and go deep — given your AWS environment and the KIP-932 GA, I would prioritize Kafka 4.2 share groups (which fit your future MSK upgrades neatly) or Debezium-for-legacy (which generalizes Stage 5's investment).

**Thresholds that would change the plan:** if you discover that your real production workload doesn't need exactly-once across DB and Kafka, simplify Stage 5 to just `@TransactionalEventListener(AFTER_COMMIT)` and skip Debezium — the operational cost of Debezium is real and worth avoiding when at-least-once-after-DB-commit is acceptable. If you find Spring Cloud Stream's overhead unhelpful for your team, drop it for everything except Kafka Streams (where the binder is genuinely better than wiring `StreamsBuilderFactoryBean` by hand). If your analytics aren't latency-critical, replace Kafka Streams with periodic Spark jobs reading from Kafka — Streams is wonderful but operationally heavy.

## Caveats

A few honest caveats to set expectations:

The Apache Kafka 4.2 share-consumer (KIP-932) and the Streams server-side rebalance protocol (KIP-1071) are explicitly marked production-ready in the Kafka 4.2 upgrade guide but the production track record is still measured in months, not years. Treat them as production-eligible for greenfield work but think twice before migrating mission-critical existing systems onto them in 2026. The Spring Cloud Stream Kafka binder integration of KIP-932 is not yet shipped (see `spring-cloud-stream` issue #3145), so adoption today requires raw `@KafkaListener`.

Spring Boot 4.0 has been GA for six months as of May 2026 (4.0.5/4.0.6 patches per the Spring blog); some ecosystem libraries (Spring Cloud Stream Kafka binder, Confluent's Spring Boot examples) lag the Boot 4 baseline by a release. Check each dependency's release notes; in some cases you may need to override Confluent's `kafka-avro-serializer` version (currently 8.2.0 for Kafka 4.2) to match the Kafka client 4.x your Spring Boot 4 pulls in.

The pace of Spring Kafka 4.x development is high — between November 2025 and April 2026, five patch releases (4.0.1–4.0.5) plus the 4.1.0 milestone train shipped. Pin to a specific patch version in your `build.gradle.kts` rather than depending on Spring Boot's transitive version to avoid surprise behavior changes.

The `aws-msk-iam-auth` library has had two CVEs in the recent past (CVE-2025-58056 and CVE-2025-58057, both fixed in 2.3.5 on November 5, 2025); always pin to the latest patch and watch the GitHub Releases page.

Finally, the line between "use the in-process `@TransactionalEventListener(AFTER_COMMIT)` outbox" and "use Debezium against the outbox table" is one of the most consequential architectural choices in this curriculum. The in-process variant is dramatically simpler operationally but is *not* crash-safe between JPA commit and Kafka send — this is documented in the Spring Framework Javadoc for `TransactionalEventListener` itself. If your team is not currently running Debezium and your use case can tolerate occasional event loss on a JVM crash (and downstream consumers can reconcile via periodic reconciliation jobs), prefer the simpler variant. If event loss is unacceptable, accept the operational cost of Debezium. Don't let the lab project for the simpler variant fool you into thinking it is production-equivalent.