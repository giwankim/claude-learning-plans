---
title: "Spring Kafka 4.0 / Spring Boot 4.0 Learning Curriculum — Kotlin Backend Engineer Edition (2026 Refresh)"
category: "Spring & Spring Boot"
description: "Research-grade learning curriculum for Spring for Apache Kafka 4.0 + Spring Boot 4.0 on Kotlin 2.x — covers version pinning vs 3.5 LTS, Spring Retry → Framework 7 core retry migration, KRaft-only embedded broker, Jackson 3 + JSpecify nullability, Share Groups (KIP-932), MSK IAM, and curated Korean and English sources with a phased study path."
---

# Spring Kafka 4.0 / Spring Boot 4.0 Learning Curriculum — Kotlin Backend Engineer Edition (2026 Refresh)

**BLUF:** Target Spring Boot **4.0.x** + Spring for Apache Kafka **4.0.x** (Soby Chacko, "Spring for Apache Kafka 4.0.0 goes GA," spring.io, 18 Nov 2025) as your primary stack — built on Spring Framework 7, Apache Kafka client 4.0/4.1, KRaft-only, JSpecify nullability, Jackson 3, and the new Spring-Framework-core retry — but **start learning on Spring Boot 3.5.x / Spring Kafka 3.3.x for the first three weeks** because the breadth and depth of community material (Baeldung, Korean tech blogs, Stack Overflow, books) is still concentrated there, and then "rebase" your project to 4.0 entering Stage 2.

## TL;DR

- **Pin 4.0 as the primary target, 3.3.x as the LTS escape hatch.** Spring Kafka 4.0.0 went GA on 18 Nov 2025 (Soby Chacko's GA blog) alongside Spring Boot 4.0.0, which Phil Webb announced on 20 Nov 2025 as "the beginning of a new Spring Boot generation providing solid foundations for coming years." Spring Boot 3.5 is supported through 30 Jun 2026 (OSS) and remains the right answer for shops that can't yet absorb Jackson 3 + Spring Framework 7 + Jakarta EE 11 in one swing.
- **Three things actually break for Kotlin/Spring Kafka users on 4.0:** (1) Spring Retry is removed and replaced by `org.springframework.core.retry` — `@Backoff` becomes `@BackOff`, `BackOffPolicy` becomes `BackOff`, and `spring.kafka.retry.topic.backoff.random` is renamed to `spring.kafka.retry.topic.backoff.jitter`; (2) embedded broker is **KRaft-only** — `EmbeddedKafkaZKBroker`, `EmbeddedKafkaRule`, and the `kraft=true` flag on `@EmbeddedKafka` are all removed; (3) Jackson 3 (`tools.jackson.*`) becomes preferred while Jackson 2 (`com.fasterxml.jackson.*`) is deprecated-but-functional — for Kotlin users this also means swapping `com.fasterxml.jackson.module:jackson-module-kotlin` for `tools.jackson.module:jackson-module-kotlin` (3.0.0+).
- **Add one new week (Week 11.5) for Kafka Share Groups (KIP-932)** — preview in Kafka 4.1, GA in Kafka 4.2 per the Apache Kafka 4.2.0 Release Announcement (kafka.apache.org, 17 Feb 2026): "Kafka Queues (Share Groups) is now production-ready with new features like the RENEW acknowledgement type for extended processing times, adaptive batching for share coordinators, soft and strict enforcements of quantity of fetched records, and comprehensive lag metrics." Spring Kafka 4.0 exposes it via a `ShareConsumerFactory` + `@KafkaListener` integration with `ShareAcknowledgment` (`acknowledge()` / `release()` / `reject()`). Use it where you'd previously over-partition for parallelism (notification fan-out, image processing, idempotent job queues), **not** where order matters (payments, ledger updates).

## Key Findings

### 1. Version compatibility (what to pin)

Spring for Apache Kafka 4.0.0 GA was released **18 Nov 2025**. Per Soby Chacko's announcement blog: "On behalf of the team and everyone who contributed, we are pleased to announce that Spring for Apache Kafka 4.0.0 is now generally available... progressed through five milestone releases and one release candidate over an 8-month development cycle before reaching general availability in November 2025." Spring Boot 4.0.0 followed on **20 Nov 2025**, framed by Phil Webb as "the beginning of a new Spring Boot generation providing solid foundations for coming years." The Spring Kafka 4.0 line is wired to Apache Kafka client **4.0.0** (in M2) and bumped to **4.1.0** in M5 ("Kafka 4.1.0 Upgrade: Updated to Apache Kafka 4.1.0 client with improved share consumer handling"). Spring Framework 7's retry is the new substrate, JSpecify is the nullability standard, and Jackson 3 is the preferred mapper with Jackson 2 still working but deprecated.

### 2. Spring Retry removal — what actually changes in your code

Per the official "What's new?" doc and the Spring Kafka 4.0.0 GA blog: "Spring for Apache Kafka has removed its dependency on Spring Retry in favor of the core retry support introduced in Spring Framework 7. This is a breaking change that affects retry configuration and APIs throughout the framework. `BackOffValuesGenerator` that generates the required BackOff values upfront, now works directly with Spring Framework's `BackOff` interface instead of `BackOffPolicy`." `@Backoff` (from Spring Retry) becomes `@BackOff` (re-homed in spring-kafka with SpEL/placeholder support on every string attribute and new `delayString` / `maxDelayString` duration parsing). Spring Boot's autoconfig issue #47125 captures the property rename: `spring.kafka.retry.topic.backoff.random` is removed in favor of `spring.kafka.retry.topic.backoff.jitter`, "which provides more flexibility over the former."

Spring Framework 7's core retry (the new substrate) lives in `org.springframework.core.retry` — `RetryTemplate`, `RetryPolicy`, `BackOff`, `RetryListener`. The annotation-level entry points are `@Retryable` (in `org.springframework.resilience.annotation`) and `@EnableResilientMethods` instead of `@EnableRetry`. Note `maxAttempts` (Spring Retry) is replaced by `maxRetries` (Spring Framework 7) — semantics differ slightly (`maxRetries=4` means "1 initial attempt + 4 retries = 5 total"). Reactive return types are auto-decorated with Reactor's retry spec.

### 3. KRaft-only embedded broker

"All ZooKeeper-based functionality has been removed as Kafka 4.0 fully transitions to KRaft mode... The `EmbeddedKafkaZKBroker` class has been removed... The `EmbeddedKafkaRule` JUnit 4 rule has been removed... The `kraft` property has been removed as KRaft mode is now the only option... ZooKeeper-specific properties like `zookeeperPort`, `zkConnectionTimeout`, and `zkSessionTimeout` have been removed." The 3.x-era guidance to set `kraft = false` to work around port-binding/race issues (issue #39055) is gone — KRaft is the only path. Your `@EmbeddedKafka(partitions = 3, topics = ["orders"], bootstrapServersProperty = "spring.kafka.bootstrap-servers")` annotation still works; just delete any ZK or `kraft=` attributes.

### 4. Jackson 3 + Kotlin

`tools.jackson.module:jackson-module-kotlin` 3.0+ is available. Coordinates change from `com.fasterxml.jackson.module` → `tools.jackson.module`. Spring Kafka 4.0's `JsonSerializer`/`JsonDeserializer`/`JsonMessageConverter` auto-detect Jackson 3 on the classpath and prefer it; the Jackson 2 equivalents still ship but are deprecated. **Mixed classpaths cause runtime ClassCastExceptions** — see Spring Cloud Function issue #1319 ("Jackson 2 KotlinModule cannot be cast to Jackson 3 JacksonModule") — so when you migrate, migrate all of your Kotlin modules at once and add `tools.jackson.core:jackson-databind` + `tools.jackson.module:jackson-module-kotlin` explicitly.

### 5. JSpecify + Kotlin — the win

Spring Framework 7 has migrated the entire portfolio from `org.springframework.lang.@Nullable`/`@NonNull` to JSpecify-based annotations. Per Sébastien Deleuze, "Null-safe applications with Spring Boot 4," spring.io, 12 Nov 2025: "Kotlin 2, the new baseline for Spring Framework 7 and Spring Boot 4, automatically translates JSpecify annotations to Kotlin nullability. Goodbye platform types, including for generics, Spring APIs now look like if they were natively written in Kotlin!" In practice this means every `KafkaTemplate<K,V>.send(...)`, `ConsumerRecord<K,V>.value()`, header accessor, etc. now exposes proper nullable/non-null types to your Kotlin code without `!!` punctuation.

### 6. Kotlin baseline + open issues

Per Soby Chacko's "Spring for Apache Kafka 4.0.0-M1, 3.3.4, and 3.2.8 are Available Now" (spring.io, 18 Mar 2025): "Several other dependencies are updated to their respective next major versions, such as Kotlin support, which is updated to version 2.1.10." Spring Framework 7 itself targets Kotlin 2.2 as the new baseline. Issue **#3277** ("On kotlin application, Spring kafka 3.2.0 doesn't take the message conversion logic, because of the wrong coroutine detection on `MessagingMessageListenerAdapter`") was fixed in Spring Kafka **3.3.0-M1** and inherited by the 4.0.x line — so plain Kotlin data class payloads in `@KafkaListener fun listen(message: MyMessage)` now route through the configured message converter correctly. Issue **#3618** ("DefaultErrorHandler and suspend methods") landed in **Spring Kafka 4.0.4** (released 16 March 2026), per the spring.io blog "Spring for Apache Kafka 4.1.0-M2, 4.0.4, and 3.3.14 Available" (17 Mar 2026). Suspend functions remain a supported async return type — "The `suspend` is turned to `Mono` which is subscribed from the consumer thread. So, that guarantees an order according to Kafka recommendations" (Artem Bilan, spring-kafka discussion #3805) — but be careful with ordering when you do non-trivial async work inside the body.

### 7. Kafka Share Groups (KIP-932)

Spring Kafka 4.0 added first-class Share Consumer support. Matej Marconak's article *"[MM's] Boot Notes — Spring Boot 4.0 and Kafka: Rethinking Message Consumption with Share Groups"* (Medium, November 2025) summarizes the trade-off: "Share Groups distribute records, not partitions, enabling queue-like consumption patterns... You no longer need to over-partition topics just to scale consumers." Acknowledgment modes: `ACCEPT` (success), `RELEASE` (transient failure — broker redelivers), `REJECT` (permanent — broker archives after `group.share.delivery.count.limit`). Configure via a `ShareConsumerFactory` + a `KafkaListenerContainerFactory` and use existing `@KafkaListener` with the `ShareAcknowledgment` parameter. **Limitations right now:** no message converters, no batch listeners, unacknowledged records block polls per-thread. **Status timeline:** Early Access in Kafka 4.0 (March 2025), Preview in Kafka 4.1, GA in Kafka 4.2 (Apache Kafka 4.2.0 Release Announcement, 17 Feb 2026). Andrew Schofield (Apache committer, KIP-932 author): if you enable KIP-932 in 4.0 you can't upgrade to 4.1 — record formats are still evolving — so use a throwaway cluster for 4.0 experimentation.

### 8. Tooling and dependency floor

- **JDK**: Java 17 minimum, Java 25 first-class. Multiple practitioners (Steven Pegoraro, Ankit Verma) recommend Java 21 minimum in practice for Virtual Threads + Scoped Values + Project Leyden gains. Apache Kafka 4.0 brokers/tools require Java 17, clients/Streams require Java 11.
- **Gradle**: Per the Spring Boot 4.0 Release Notes wiki: "Gradle 9 is now supported for building Spring Boot applications. Support for Gradle 8.x (8.14 or later) remains." Pegoraro: "Gradle 9 removed APIs that have been deprecated since Gradle 7 or earlier... the convention API is gone."
- **Kotlin**: 2.2 baseline in Spring Framework 7; spring-kafka 4.0-M1 uses 2.1.10. Pin Kotlin 2.1.10+ minimum, 2.2.x recommended.
- **Testcontainers**: Works with KRaft Kafka; use `org.testcontainers:kafka` with a 4.x image such as `apache/kafka:4.0.0` or `bitnami/kafka:latest`.
- **AWS MSK IAM auth (`software.amazon.msk:aws-msk-iam-auth`)**: Latest is **2.3.6 (released 6 May 2026)**. The library is compiled `compileOnly` against `kafka-clients:2.8.1` and tested against `kafka-clients:2.2.1` — AWS has not published a Kafka 4.x compatibility statement. Because the integration is at the SASL `LoginModule` / `AuthenticateCallbackHandler` extension points, it loads under kafka-clients 4.0/4.1 in practice, but verify in a staging MSK cluster before assuming production readiness.
- **AWS MSK service**: Per AWS "What's New" pages for Kafka 4.0 (May 2025) and Kafka 4.1 (October 2025): "You can also upgrade existing MSK provisioned clusters with an in-place rolling update. Amazon MSK orchestrates broker restarts to maintain availability and protect your data during the upgrade."

### 9. Korean tech blog coverage

The Korean ecosystem is rich on Kafka operations and 3.x Spring Kafka, but coverage of Spring Boot 4 / Spring Kafka 4 is still nascent (the GA is only ~6 months old). Worth-reading 2024–2026 Korean references:

- **Toss / 토스 — "토스증권 Apache Kafka 데이터센터 이중화 구성 #1/#2/#3"** (toss.tech, 3-part series): Active-Active vs Stretched Cluster, custom MM2-replacement Sink Connector with DC source headers in record headers, and Confluent-style Consumer Offset Sync without buying Confluent Platform. The clearest production-grade Korean reference for multi-DC Kafka.
- **Woowahan / 우아한형제들 — "카프카 컨슈머에 동적 쓰로틀링 적용하기"** (techblog.woowahan.com/20156/): dynamic throttling with `Thread.sleep` vs `ConsumerSeekAware.pause/resume` so you don't trigger rebalances.
- **Woowahan — "우리 팀은 카프카를 어떻게 사용하고 있을까"** (techblog.woowahan.com/17386/): consumer group ordering, key-based partitioning, transactional outbox pattern at Baemin Delivery.
- **Woowahan — "장시간 비동기 작업, Kafka 대신 RDB 기반 Task Queue로 해결하기"** (techblog.woowahan.com/23625/): a *cautionary* case of when **not** to use Kafka (long-running excel generation triggering Kafka rebalances and duplicate processing) — pair this with the Share Groups week as a counterpoint, because share groups would actually have helped here.
- **Kurly / 컬리 — "Kafka Streams 윈도우 도입기"** (helloworld.kurly.com/blog/2025-kafka-streams-window/, Dec 2025) and **"컬리 검색이 카프카를 들여다본 이야기 1"** (Spring Kafka @KafkaListener + Record vs Batch listener internals, rebalance root-cause analysis).
- **Kurly — "Kafka Connect로 DB 데이터 쉽게 연동하기"** (helloworld.kurly.com/blog/kafka-connect-pipeline/): JDBC source connector + log-based (Debezium) vs query-based CDC trade-offs.
- **LINE — "Applying Kafka Streams for internal message delivery pipeline"** (engineering.linecorp.com): why LINE built **Decaton** (open-sourced Kafka-based async job queue) instead of using Kafka Streams or another framework. Very useful reference for the Share Groups week — Decaton's design rationale (per-record ack, deferred delivery, head-of-line-blocking mitigation) is exactly what KIP-932 standardizes inside the broker.
- **Korean Spring Boot 4 migration guides** (general, not Kafka-specific): "Spring Boot 4.0 마이그레이션 완벽 가이드" on dev-post.com (Mar 2026) and "Spring Boot 4 모듈화" on blog.igooo.org (Jan 2026) cover Jackson 3 transition, starter renames, and `spring-boot-properties-migrator` usage.

There is, as of May 2026, **no major Korean tech blog post dedicated to Spring Kafka 4 or Share Groups specifically** — this is a gap, and a good opportunity for a writeup if you publish.

---

## Version Compatibility Pin Table

| Layer | Primary target (2026) | LTS fallback | Notes |
|---|---|---|---|
| Spring Boot | **4.0.5** (GA 26 Mar 2026; line started 4.0.0 on 20 Nov 2025) | 3.5.x (OSS support until 30 Jun 2026) | Use `spring-boot-starter-classic` to keep monolithic starters during incremental migration |
| Spring Framework | **7.0.7** | 6.2.x | `org.springframework.core.retry` and `org.springframework.resilience.annotation` are new |
| Spring for Apache Kafka | **4.0.4 / 4.0.5** | 3.3.14+ | 3.3.x continues to receive patches alongside 4.0.x |
| Apache Kafka client | **4.1.0** (pulled by Spring Kafka 4.0 M5+); 4.2.0 with Spring Kafka 4.1.0-M2 | 3.9.x bridge | KRaft only from 4.0 |
| Apache Kafka broker (AWS MSK) | **MSK 4.1.x** or **4.0.x** | MSK 3.9.x (recommended bridge) | Pre-3.3.x ZK clusters must migrate to KRaft on 3.9.x first |
| JDK | **21** (recommended) / 25 (first-class) | 17 (floor) | Kafka 4 broker tools require Java 17 |
| Kotlin | **2.2.x** | 2.1.10 (spring-kafka 4.0 floor) | JSpecify nullness translates to Kotlin types automatically |
| Gradle | **9.x** | 8.14+ | Convention API removed in Gradle 9 |
| Jackson | **3.x** (`tools.jackson.*`) | 2.x (`com.fasterxml.jackson.*`, deprecated) | Mixed classpath = CastException; migrate Kotlin modules together |
| jackson-module-kotlin | **`tools.jackson.module:jackson-module-kotlin:3.x`** | 2.x | Use `tools.jackson.module.kotlin.jacksonObjectMapper` |
| Spring Retry library | **Removed** (do not depend on `org.springframework.retry`) | n/a | Use `org.springframework.core.retry.*` and `@BackOff` |
| Testcontainers | latest stable; `apache/kafka:4.0.0` or `4.1.0` image | confluent-platform 7.6+ | KRaft only |
| aws-msk-iam-auth | **2.3.6** (6 May 2026) | 2.3.0 | Compiled against kafka-clients 2.8.1; works at SASL extension level with 4.x in practice but not formally certified |
| Micrometer | 1.16.x (bundled by Spring Boot 4) | 1.14.x | Per-record observations now available for batch listeners |
| Spring Kafka Share Groups (KIP-932) | Preview in Kafka 4.1; GA in Kafka 4.2.0 (17 Feb 2026) | n/a | Use throwaway clusters for 4.0 experimentation; record formats unstable until 4.1 |

---

## Why I still recommend starting on 3.5/3.3.x for Stage 1

Spring Kafka 4.0 is GA-stable but the **learning material density is 10x higher on the 3.x line** (Baeldung, Lydtech, the entire 2022–2025 Korean blog corpus, books like *Spring Microservices in Action* 2e, Spring's own reference history-of-changes section, every Stack Overflow answer). Stage 1 is "learn how Kafka and Spring Kafka fit together" — there is no value in fighting Jackson 3 ClassCastExceptions and `@BackOff` rename pain while you're trying to internalize what `ConsumerRebalanceListener` actually does. Start your sandbox on Spring Boot **3.5.x** + Spring Kafka **3.3.x** + KRaft Kafka 4.0 broker (the broker side is upgradable independently). At the end of Week 3, **rebase to Spring Boot 4.0.x + Spring Kafka 4.0.x** as Stage 2 begins; you'll then experience the migration deltas as concrete, named diffs rather than abstract warnings.

---

# Stage 1 — Foundations (3 weeks)

> **Stack for Stage 1:** Spring Boot 3.5.x, Spring Kafka 3.3.x, Apache Kafka broker 4.0.x (KRaft), Kotlin 2.1+, Gradle 8.14+, JDK 21, jackson-module-kotlin 2.18+. Switch to 4.0 starting Week 4.

## Week 1 — Kafka mental model + producer/consumer internals

**Topics**
- Log-structured storage, segments, offsets, partition as the unit of ordering and parallelism.
- KRaft architecture (post-ZooKeeper): controllers, metadata topic, KIP-848 next-gen rebalance protocol GA in Kafka 4.0.
- Producer record path: serializer → partitioner (default sticky → key-hashing) → accumulator → sender thread; `acks`, `linger.ms`, `batch.size`, `compression.type` (`zstd` default for new topics in 4.x), idempotence (`enable.idempotence=true` is now default).
- Consumer record path: fetcher → coordinator → poll loop → assignor; the new **KIP-848 consumer protocol** is GA in Kafka 4.0 — broker drives assignment, no more stop-the-world rebalances. Opt in via `group.protocol=consumer` on the client.
- Why Kotlin matters: data classes serialize cleanly with `jackson-module-kotlin`; `companion object` for topic name constants; `suspend` ergonomics overlap awkwardly with poll loop ordering.

**Deliverable**
A Gradle Kotlin DSL project (Spring Boot 3.5.x) with a single Kotlin `KafkaProducer` and `KafkaConsumer` (raw clients, not Spring) sending JSON messages to a local Docker Compose Kafka 4.0 KRaft cluster, printing partition/offset assignment as records flow.

**Korean blog readings**
- 우아한형제들 — "우리 팀은 카프카를 어떻게 사용하고 있을까" (key-based partitioning for ordering)
- Toss — "토스증권 Apache Kafka 데이터센터 이중화 구성 #1" (architecture-level perspective)

**Trade-off reasoning**
*When not to use Kafka:* low-throughput request/reply (use HTTP/gRPC), long-running unit-of-work jobs (see the Woowahan "RDB-based Task Queue" article — they ripped Kafka out because rebalance + 30-min-per-message caused double-fires), strict-ordered single-stream data <100/sec (a database table works fine).

---

## Week 2 — Spring Kafka basics: `KafkaTemplate`, `@KafkaListener`, serialization

**Topics**
- `KafkaTemplate<K,V>` auto-config, async-by-default `send()` returning `CompletableFuture<SendResult<...>>`, callback patterns in Kotlin.
- `@EnableKafka`, `ConcurrentKafkaListenerContainerFactory`, `ConsumerFactory`/`ProducerFactory`, `ContainerProperties`.
- `@KafkaListener` deep dive: `id` (used as `client.id` prefix), `groupId`, `concurrency`, `topics`/`topicPattern`/`topicPartitions`, container vs. listener properties precedence.
- `JsonSerializer`/`JsonDeserializer` and the `TYPE_MAPPINGS` header trick; `ErrorHandlingDeserializer` to wrap a failing deserializer.
- **Kotlin gotcha (3.x):** message conversion bug #3277 ("On kotlin application, Spring kafka 3.2.0 doesn't take the message conversion logic, because of the wrong coroutine detection") — fixed in 3.3.0-M1; ensure your pin is ≥ 3.3.0.
- Async return types from `@KafkaListener`: `CompletableFuture<?>`, `Mono<?>`, and Kotlin `suspend` functions — "The `suspend` is turned to `Mono` which is subscribed from the consumer thread."

**Deliverable**
Two Spring Boot 3.5 services (Kotlin) — `order-producer` sends `OrderEvent` data class to topic `orders`, `order-consumer` consumes and logs. Both wired via Gradle Kotlin DSL. Add a `RoutingKafkaTemplate` for sending two payload types on the same template.

**Trade-off reasoning**
*When not to use `@KafkaListener`:* when you need to drive consumer lifecycle from external state (start/stop based on feature flag, leader election) — `KafkaListenerEndpointRegistry.getListenerContainer(id).start()/stop()` is correct, but in some cases plain `KafkaConsumer` in a managed thread is simpler.

---

## Week 3 — Error handling basics + testing (Embedded Broker)

**Topics**
- `DefaultErrorHandler`, `CommonErrorHandler` SPI, `BackOff` (`FixedBackOff`, `ExponentialBackOff`), `addRetryableExceptions` / `addNotRetryableExceptions`.
- `DeadLetterPublishingRecoverer` end-to-end: how partitions are preserved by default, how to override with `BiFunction<ConsumerRecord<?,?>, Exception, TopicPartition>`.
- `RecordInterceptor` (3.x) and the new listener-container customization in 4.x.
- **Testing**: `@EmbeddedKafka` (note: from `org.springframework.kafka.test.context`), `spring-kafka-test`, `KafkaTestUtils.consumerProps()`, `bootstrapServersProperty = "spring.kafka.bootstrap-servers"` so Spring Boot auto-config picks up the embedded broker.
- **At end of Week 3, rebase to 4.0:** bump Spring Boot to 4.0.x, Spring Kafka to 4.0.x, switch jackson modules to `tools.jackson.*`, delete `kraft=true` and any ZK properties from `@EmbeddedKafka`, install `spring-boot-properties-migrator` runtime dep to catch property renames.

**Deliverable**
Integration test suite using `@EmbeddedKafka(partitions = 3, topics = ["orders","orders-dlt"], bootstrapServersProperty = "spring.kafka.bootstrap-servers")` exercising successful send/receive, a deserialization failure path going to DLT, and a transient retryable exception with `ExponentialBackOff(initialInterval=500, multiplier=2.0, maxInterval=10_000)`. Include the 3.5 → 4.0 rebase commit at week's end.

**Korean blog readings**
- 컬리 — "컬리 검색이 카프카를 들여다본 이야기 1" (Record vs Batch listener, why rebalances happen during long indexing)

**Trade-off reasoning**
*When not to use embedded broker:* if your test fans out >5 listeners or exercises real broker behavior (compaction, transactional fencing, KRaft controller failover), Testcontainers + a real KRaft image gives more fidelity at ~3-5s startup cost.

---

# Stage 2 — Production Mastery (10 weeks + 1 Share Groups week)

> **Stack for Stage 2:** Spring Boot **4.0.x**, Spring Kafka **4.0.x**, Apache Kafka broker 4.1.x KRaft, Spring Framework 7, Kotlin 2.2.x, Gradle 9, JDK 21, jackson-module-kotlin 3.x.

## Week 4 — Containers, threading model, concurrency internals

**Topics**
- `MessageListenerContainer` interface, `KafkaMessageListenerContainer` (single-threaded poll loop), `ConcurrentMessageListenerContainer` (N consumers in N threads, each owning its own `KafkaConsumer`).
- Internals: `ListenerConsumer` inner class, the poll-then-invoke loop, commit semantics (`AckMode.RECORD`, `BATCH`, `MANUAL`, `MANUAL_IMMEDIATE`, `TIME`, `COUNT`, `COUNT_TIME`).
- `pause()` / `resume()` / `pausePartition()` for back-pressure.
- KIP-848 next-gen consumer protocol: client-side `group.protocol=consumer`; broker-side incremental assignment; no more "stop the world" — but rolling-restart behavior changes (test it).
- **Kotlin gotcha (4.x):** `DefaultErrorHandler` + `suspend` listener — fixed in spring-kafka 4.0.4 (issue #3618). Pin ≥ 4.0.4.
- JSpecify benefit: `ConsumerRecord<K,V>.key()` and `.value()` now expose nullness to Kotlin natively.

**Deliverable**
Build a `ConcurrentMessageListenerContainer` with `concurrency=4` against a 12-partition topic, then bind container-level `setRecordInterceptor` to log thread-name → partition mapping. Demonstrate `pause()` on a single partition based on Redis (Lettuce) signal.

---

## Week 5 — Consumer groups, partition assignment, rebalancing in depth

**Topics**
- Group coordinator, heartbeat thread vs poll thread, `session.timeout.ms` / `heartbeat.interval.ms` / `max.poll.interval.ms` — old protocol vs KIP-848 differences.
- `RangeAssignor`, `RoundRobinAssignor`, `StickyAssignor`, `CooperativeStickyAssignor` (default for the new protocol).
- `ConsumerRebalanceListener` vs `ConsumerAwareRebalanceListener` vs `ConsumerSeekAware` for offset manipulation on assignment.
- Static membership (`group.instance.id`) for predictable assignment in K8s deployments (relevant on EKS/ECS).
- The new `kafka-consumer-groups.sh` describe output under KIP-848.

**Deliverable**
Run 3 consumer pods on EKS (or local k3d) consuming a 6-partition topic; force a rolling restart and measure rebalance pause with the old protocol (`group.protocol=classic`) vs new (`group.protocol=consumer`). Document the latency delta.

**Korean blog readings**
- 우아한형제들 — "카프카 컨슈머에 동적 쓰로틀링 적용하기" (consumer scaling without rebalances)

---

## Week 6 — Transactions & exactly-once semantics

**Topics**
- Producer transactions, `transactional.id`, `transaction.timeout.ms`, idempotence guarantees.
- Spring's `KafkaTransactionManager`, the `@Transactional` boundary, chaining JPA + Kafka transactions via `ChainedTransactionManager` (deprecated in Spring 6+ but pattern still useful with `JpaTransactionManager` outer + Kafka inner).
- `read_committed` isolation level on the consumer side.
- `TransactionIdSuffixStrategy` (3.2+ API still relevant in 4.x) for managing `transactional.id` cardinality under high concurrency.
- The **transactional outbox pattern** as the production-safe alternative when you have to atomically update DB and publish — referenced in Woowahan blog above.

**Deliverable**
Implement a payment-processing service: receive `PaymentRequested` → write to Aurora MySQL → publish `PaymentCompleted` on Kafka, all in one transaction. Test the failure-after-DB-commit-before-Kafka-send case with chaos.

**Trade-off reasoning**
*When not to use Kafka transactions:* if you can tolerate at-least-once semantics + downstream idempotency, the throughput overhead (transactions add a 2-PC-style coordinator dance) isn't worth it.

---

## Week 7 — DLT, non-blocking retries (the major 4.0 delta)

**Topics**
- The blocking retry path (`DefaultErrorHandler` + `BackOff`) vs the non-blocking retry-topic pattern (`@RetryableTopic`).
- **Spring Kafka 4.0 changes (breaking):**
  - Spring Retry dependency removed. The new substrate is `org.springframework.core.retry.RetryTemplate` / `RetryPolicy` and `org.springframework.util.backoff.BackOff`.
  - `@Backoff` → `@BackOff` (rehomed in spring-kafka with SpEL/placeholder support and new `delayString`/`maxDelayString`). Code diff: `@RetryableTopic(backoff = @Backoff(delay = 2000, multiplier = 2))` → `@RetryableTopic(backOff = @BackOff(delayString = "2s", multiplier = 2))`.
  - Property rename: `spring.kafka.retry.topic.backoff.random` → `spring.kafka.retry.topic.backoff.jitter`.
  - `BackOffPolicy` → `BackOff` interface; `BackOffValuesGenerator` now generates values against `BackOff`.
  - `RetryingDeserializer.setRecoveryCallback(context -> ...)` → `setRecoveryCallback(retryException -> ...)` (now takes `RetryException`).
  - `BinaryExceptionClassifier` → new `ExceptionMatcher`.
  - `RetryTopicConfigurationBuilder.uniformRandomBackoff(...)` deprecated in favor of jitter.
- Topic naming strategies: `SUFFIX_WITH_INDEX_VALUE` vs `SUFFIX_WITH_DELAY_VALUE`, single-topic vs multi-topic fixed delay.
- `@DltHandler` and DLT-specific listener strategies.
- Use `spring-boot-properties-migrator` runtime dependency during migration to surface the property renames.

**Deliverable**
Migrate Week 3's DLT/retry setup to the 4.0 syntax (rename `@Backoff` → `@BackOff`, update property names). Add a `RetryTopicConfigurationSupport` bean that configures both blocking retries (`BlockingRetriesConfigurer.retryOn(IOException::class.java).backOff(FixedBackOff(500, 3))`) and non-blocking retry topics with exception-based DLT routing (`@ExceptionBasedDltDestination`).

**Trade-off reasoning**
*When not to use non-blocking retries:* if you require strict per-partition ordering through the retry process (you'd be reordering records onto the retry topic). Blocking retries preserve order but block the whole partition.

---

## Week 8 — Kafka Streams in Spring

**Topics**
- `StreamsBuilderFactoryBean`, `StreamsBuilderFactoryBeanConfigurer` (note: Spring Boot 4.0 removed the old `StreamBuilderFactoryBeanCustomizer` in favor of this), `@EnableKafkaStreams`.
- `KStream`/`KTable`/`GlobalKTable`, stateful operators, windowing (tumbling/hopping/session), `KafkaStreamsInteractiveQuerySupport`.
- **Kafka Streams retry templates now use Spring Framework's retry support** (part of the 4.0 Spring Retry removal).
- Exactly-once Streams (`processing.guarantee = exactly_once_v2`).
- Kotlin DSL: use the Confluent kotlin DSL or write extension functions for `KStream<K,V>.mapValues { ... }`.

**Deliverable**
Build a windowed aggregation: stream `OrderEvent` → 5-minute tumbling window → `OrderRollup` table → expose via interactive query REST endpoint.

**Korean blog readings**
- 컬리 — "Kafka Streams 윈도우 도입기" (helloworld.kurly.com/blog/2025-kafka-streams-window/) — production lessons on tumbling windows, grace period, and remapping event time vs ingestion time.

**Trade-off reasoning**
*When not to use Kafka Streams:* small joins/lookups (cache-aside in Redis is simpler), low-volume aggregation (a SQL window function on Aurora is operationally simpler), or when you need cross-cluster joins (use Flink).

---

## Week 9 — Schema management

**Topics**
- JSON Schema, Avro, Protobuf, schema registry (Confluent or AWS Glue Schema Registry); BACKWARD/FORWARD/FULL compatibility modes.
- Spring Kafka serializers vs schema-aware serializers; `JsonSerializer` type-info headers, removal patterns.
- **Jackson 3 migration:** `tools.jackson.databind.json.JsonMapper`, `tools.jackson.module.kotlin.jacksonObjectMapper`, `kotlinModule()` builder. Spring Kafka 4.0's `JacksonJsonObjectMapper` and `Jackson3JsonMapper` for Spring components.
- Schema evolution scenarios: adding nullable field (safe), renaming field (use `@JsonProperty` aliases), changing required→optional.

**Deliverable**
Wire a Confluent Schema Registry (or local Apicurio) into the order service, switch from JSON to Avro. Demonstrate a forward-compatible field addition rollout.

---

## Week 10 — Performance tuning + AWS MSK

**Topics**
- Producer tuning: `linger.ms`, `batch.size`, `compression.type=zstd`, `max.in.flight.requests.per.connection=5` (default with idempotence), `buffer.memory`.
- Consumer tuning: `fetch.min.bytes`, `fetch.max.wait.ms`, `max.poll.records`, `max.partition.fetch.bytes`.
- MSK Provisioned vs MSK Serverless; MSK 4.0.x and 4.1.x service versions; in-place rolling upgrades per the AWS What's New post for MSK 4.1 (Oct 2025): "You can also upgrade existing MSK provisioned clusters with an in-place rolling update."
- IAM auth via SASL/OAUTHBEARER + `software.amazon.msk:aws-msk-iam-auth:2.3.6` (latest as of May 2026, includes a Route53 region provider and a configurable signing region via `awsMskRegionProvider` JAAS parameter for custom DNS endpoints).
- **Compatibility caveat:** aws-msk-iam-auth 2.3.6's `build.gradle` declares `compileOnly('org.apache.kafka:kafka-clients:2.8.1')` and test against 2.2.1 — no official statement of Kafka 4.x certification. It works in practice because it integrates via SASL extension points, but validate in a staging MSK 4.x cluster before promoting.
- Topic-level tuning: partition count, replication, `min.insync.replicas`, `unclean.leader.election.enable=false`.
- Network/EKS-specific: NLB-backed connectivity, VPC endpoints, multi-AZ broker placement, rack awareness (`broker.rack`, `client.rack`).

**Deliverable**
Deploy a Spring Boot 4.0 + Spring Kafka 4.0 service to EKS, connect to MSK Provisioned with IAM auth, run a 30-minute load test with k6 or JMH, measure p99 publish latency and consumer lag.

---

## Week 11 — Observability

**Topics**
- Micrometer KafkaTemplate observation and KafkaListener observation (already in 3.x, refined in 4.0: per-record observation now available for batch listeners).
- Tracing context propagation through Kafka headers (W3C TraceContext), `MicrometerProducerListener`, `MicrometerConsumerListener`, `KafkaStreamsMicrometerListener` — all configurable with a custom `TaskScheduler`.
- Lag metrics: `kafka.consumer.fetch-manager.records-lag-max`, Burrow, AWS CloudWatch MSK metrics, MSK Connect lag, `kafka-consumer-groups.sh --describe`.
- Reply tracing for `ReplyingKafkaTemplate` (improvement in 4.0).
- Container customization via `getRecordInterceptor()` (new in 4.0) for logging/metrics injection without overriding error handlers.
- Spring Boot 4 ships an OpenTelemetry starter; wire that for cross-service trace propagation.

**Deliverable**
Wire OTLP exporter, view consumer-group lag and publish latency in a Grafana dashboard, propagate trace IDs from an HTTP request through KafkaTemplate to a downstream consumer.

---

## Week 11.5 (NEW) — Kafka Share Groups / Queues for Kafka (KIP-932)

**Topics**
- Mental model: Share Groups distribute *records*, not partitions. Multiple consumers in the same share group can consume the same partition cooperatively. Membership uses the new KIP-848-derived consumer rebalance protocol.
- Acknowledgment model: 30-second default record-acquisition lock; consumer picks `ACCEPT` (success), `RELEASE` (transient — broker redelivers), `REJECT` (permanent — broker archives after `group.share.delivery.count.limit` reached). In Kafka 4.2 / Spring Kafka 4.1.0-M2 a fourth ack `RENEW` (KIP-1222) extends the acquisition lock for long-running processing.
- Spring Kafka 4.0 API:
  ```kotlin
  @KafkaListener(
      topics = ["notifications"],
      containerFactory = "explicitShareKafkaListenerContainerFactory",
      groupId = "notification-fan-out",
      concurrency = "10"
  )
  fun consume(record: ConsumerRecord<String, String>, ack: ShareAcknowledgment) {
      try {
          notificationService.send(record.value())
          ack.acknowledge()
      } catch (e: TransientException) {
          ack.release()
      } catch (e: ValidationException) {
          ack.reject()
      }
  }
  ```
- Implicit vs explicit acknowledgment modes; container-level (`containerProperties.setExplicitShareAcknowledgment(true)`) vs consumer-config-level (`ConsumerConfig.SHARE_ACKNOWLEDGEMENT_MODE_CONFIG`); precedence rules.
- Configuration via `DefaultShareConsumerFactory` + `ShareKafkaListenerContainerFactory`.
- **Status reality check:** Early Access in Kafka 4.0 (March 2025) — record formats unstable, cannot upgrade clusters that have used it. Preview in Kafka 4.1 — record formats stabilized, broker must be 4.1+. **GA in Kafka 4.2 (Apache Kafka 4.2.0 Release Announcement, 17 Feb 2026)**: "Kafka Queues (Share Groups) is now production-ready with new features like the RENEW acknowledgement type for extended processing times, adaptive batching for share coordinators, soft and strict enforcements of quantity of fetched records, and comprehensive lag metrics."
- **Current limitations:** no message converters, no batch listeners, unacknowledged records block polls per-thread.
- Share Groups and classic consumer groups coexist in the same cluster and even the same Spring Boot app (different container factories).

**When to use vs traditional consumer groups (trade-offs)**

| Use Share Group | Use Classic Consumer Group |
|---|---|
| Notification fan-out, push delivery, email/SMS dispatch | Payment events, ledger updates, anything needing per-key ordering |
| Image/video processing where each frame is independent | Kafka Streams stateful processing |
| Background job queue with per-record retry | CDC consumers maintaining partition-local materialized views |
| You routinely over-partition just to add consumer parallelism | You have <10 partitions and processing time is short |
| Variable processing time per record (head-of-line blocking is costly) | Bounded processing time and order matters |

**Deliverable**
Build a side-by-side: `PaymentEvent` flows through a **classic consumer group** (3 partitions, 3 consumers, key=customer_id for ordering); `NotificationEvent` flows through a **share group** (3 partitions, 10 consumers, no ordering). Use Testcontainers with Kafka 4.1 image, enable share groups via `kafka-features.sh upgrade --feature share.version=1`. Test poison message handling (force `RELEASE` 5 times → record gets archived).

**Practitioner readings**
- Matej Marconak — *"[MM's] Boot Notes — Spring Boot 4.0 and Kafka: Rethinking Message Consumption with Share Groups"* (Medium, November 2025)
- Spring blog — *"Introducing Share Consumer Support (Kafka Queues) in Spring for Apache Kafka"* (Soby Chacko, 14 October 2025)
- Gunnar Morling — *"Let's Take a Look at... KIP-932: Queues for Kafka!"* (morling.dev)
- Andrew Schofield (KIP-932 author) — *"Early access release of Queues for Kafka in Apache Kafka 4.0"* (Medium)
- Confluent — *"Kafka Queue Semantics Now GA with Share Consumer API"* (announcing 4.2 GA)
- LINE Engineering — "Applying Kafka Streams for internal message delivery pipeline" (Decaton's design rationale, which KIP-932 effectively standardizes inside the broker)

---

## Week 12 — Security: mTLS, SASL/SCRAM, IAM, ACLs

**Topics**
- SSL/TLS: keystore/truststore configuration, hostname verification.
- SASL mechanisms: PLAIN, SCRAM-SHA-256/512, GSSAPI (Kerberos), OAUTHBEARER.
- AWS MSK IAM: `AWS_MSK_IAM` SASL mechanism, `software.amazon.msk:aws-msk-iam-auth:2.3.6`, JAAS config, role assumption via `awsProfileName`, IRSA on EKS, IAM Roles Anywhere for off-cluster clients.
- Topic ACLs (still managed via `kafka-acls.sh`), MSK cluster-policy IAM access control, multi-VPC private connectivity.
- Encryption in transit + at rest on MSK.

**Deliverable**
Configure mTLS for a local Docker Kafka cluster; in parallel configure IAM auth for the EKS-deployed service against MSK with an IRSA-bound IAM role having scoped `kafka-cluster:Connect`/`WriteData`/`ReadData` on specific topic ARNs.

---

## Week 13 — Hardening, ops, migration paths

**Topics**
- Graceful shutdown: container `setStopImmediate(true)`, in-flight record completion, `KafkaListenerEndpointRegistry.stop()` ordering with HTTP server shutdown on K8s rolling deploys.
- Bootstrap order: producer pre-init, lazy listener start with `autoStartup=false` + `start()` after warmup checks.
- Migrating an existing 3.3.x service to 4.0.x — concrete checklist:
  1. Pin 3.5.x first, clear all deprecation warnings (Phil Webb's GA blog: "since this is a major release of Spring Boot, upgrading existing applications can be a little more involved than usual").
  2. Bump JDK to 21 if not already.
  3. Bump Gradle to 9.x — per the official Spring Boot 4.0 Release Notes wiki: "Gradle 9 is now supported for building Spring Boot applications. Support for Gradle 8.x (8.14 or later) remains." (expect convention API and other deprecation removals; see Steven Pegoraro, *"The Ultimate Guide to Spring Boot 4 Migration"*, stevenpg.com).
  4. Bump Spring Boot 3.5 → 4.0; add `spring-boot-properties-migrator` runtime dep.
  5. Migrate Jackson 2 → 3 (`com.fasterxml.jackson.*` → `tools.jackson.*`), including `jackson-module-kotlin` 2.x → 3.x. Migrate all modules in one PR — mixed classpath causes `ClassCastException`.
  6. Replace any `org.springframework.retry.*` direct usage with `org.springframework.core.retry.*`.
  7. Rename `@Backoff` → `@BackOff` on `@RetryableTopic`. Rename property `spring.kafka.retry.topic.backoff.random` → `...jitter`.
  8. Remove `@EmbeddedKafka(kraft = true)` and any ZK-related attributes; switch JUnit 4 `EmbeddedKafkaRule` users to `@EmbeddedKafka` + JUnit 5.
  9. If on Spring Cloud Stream Kafka binder, wait for `spring-cloud-stream` 2025.1.x line.
  10. Drop Undertow if present (removed in Spring Boot 4 due to Servlet 6.1 incompatibility).
- Operational runbook: lag alerting thresholds, partition rebalance forensics, broker upgrade sequencing (MSK in-place rolling).

**Deliverable**
Migration playbook PR on the Stage 1 codebase: each numbered step in a separate commit so the team can see the diff. Include a rollback plan.

---

# Capstone Project — "OrderHub" (4-6 weeks part-time)

**Scope.** Multi-service Kotlin/Spring Boot 4.0 system on EKS + MSK 4.1:

1. **`order-api`** — Spring Boot 4.0 + Spring Kafka 4.0 REST API; receives `POST /orders`, writes to Aurora PostgreSQL, publishes `OrderPlaced` via transactional outbox.
2. **`payment-processor`** — consumes `OrderPlaced` on a **classic consumer group** (key=order_id for ordering), calls a mocked payment gateway with `@Retryable` (Spring Framework 7 core retry, `maxRetries=4`, exponential backoff with jitter), publishes `PaymentSucceeded` / `PaymentFailed`. Uses `@RetryableTopic` for non-blocking retry with `@BackOff(delayString = "5s", multiplier = 2.0, maxDelayString = "60s")` and DLT.
3. **`notification-fan-out`** — consumes `OrderPlaced` and `PaymentSucceeded` via a **Kafka Share Group** (KIP-932) for parallel push notification / email / SMS dispatch with no ordering constraint. Demonstrates `ACCEPT`/`RELEASE`/`REJECT` correctly. Documents why the same workload would have been awkward as a classic consumer group (over-partitioning, head-of-line blocking).
4. **`order-rollup`** — Kafka Streams app aggregating orders into a 5-minute tumbling window `KTable`, exposed via interactive query REST endpoint.
5. **`audit-cdc`** — Debezium MySQL connector → Kafka → consumed and indexed into Elasticsearch.

**Cross-cutting requirements:**
- Observability: Micrometer + OTLP + trace ID propagation through Kafka headers, Grafana dashboards for consumer-group lag, publish p99, share-group archived-record count.
- Testing: Testcontainers with Apache Kafka 4.1 image (KRaft); ≥ 1 integration test per service exercising rebalance during processing.
- Security: IAM auth from EKS pods to MSK via IRSA; in-cluster mTLS for the local-dev Compose stack.
- Migration story: maintain a parallel `release/3.3.x` branch that uses Spring Boot 3.5.x + Spring Kafka 3.3.x + Jackson 2, kept in sync by recipe-based OpenRewrite migration, to demonstrate the migration delta.

**Korean blog cross-reference for the capstone writeup:**
- Toss DC redundancy series (toss.tech) — apply the same ideas to a multi-region MSK strategy.
- Woowahan throttling article (techblog.woowahan.com/20156) — implement the same `Thread.sleep`-free dynamic throttling using container `pause()/resume()`.
- Woowahan "Kafka 대신 RDB Task Queue" — analyze whether Share Groups would have actually solved their problem (yes — per-record `RELEASE` + bigger acquisition lock would have prevented the rebalance-driven duplicate sends).

---

## Recommendations

1. **Pin and freeze for the curriculum.** Spring Boot **4.0.5**, Spring Kafka **4.0.4** or **4.0.5**, Kotlin **2.2.0**, JDK **21**, Gradle **9.x**, Apache Kafka client **4.1.x**, MSK broker **4.1.x**. These are the May 2026 stable versions and they're internally consistent.
2. **Do Stage 1 on 3.5 / 3.3.x and rebase at end of Week 3.** The material density delta justifies it; you'll *learn* the deltas by doing the migration rather than by reading about them.
3. **For organizations that can't move yet, stay on 3.5.x until at least Q3 2026.** OSS support runs through 30 June 2026. Spring Boot 3.5.x receives Spring Kafka 3.3.x patches, and the 3.3.x line will continue to track Apache Kafka client compatibility for in-place broker upgrades. Use this window to clear Jackson 2 deprecation warnings.
4. **For Share Groups specifically: do not enable in production until Kafka 4.2 is the broker version.** GA happened in February 2026, but the safer path is to wait for one or two patch releases (4.2.1+) and validate your AWS MSK service version. Use throwaway local-Docker clusters for the Week 11.5 lab.
5. **Pin `software.amazon.msk:aws-msk-iam-auth:2.3.6` explicitly in your Gradle build** and verify in a staging MSK cluster — AWS has not formally certified the library against kafka-clients 4.x. If you hit auth failures, downgrade to kafka-clients 3.9.x via Spring Boot dependency override before opening an AWS ticket.
6. **Adopt JSpecify by package**, not file-by-file. Add `@NullMarked` at the package level on your domain packages first; let IDE/JSpecify find issues; then enable NullAway in CI for those packages only. Kotlin call sites get the benefits with zero code changes.
7. **Migrate Jackson 2 → 3 atomically.** Mixed classpath crashes are nasty. If your Kafka serializer is the only thing on Jackson 2 today, swap that, your `ObjectMapper` bean, and `jackson-module-kotlin` in one PR. Use Maven Central coordinates `tools.jackson.core:jackson-databind:3.x` + `tools.jackson.module:jackson-module-kotlin:3.x`.
8. **Benchmark thresholds that should change your recommendations:**
   - If KIP-848 new consumer protocol is *not* GA in your MSK version → keep `group.protocol=classic` and budget for rebalance pauses.
   - If your team can't reach Java 21 within 6 months → defer the 4.0 migration entirely and stay on 3.5.x.
   - If you have >50 services depending on `spring-retry` library → the migration is a quarter of work, not a sprint.
   - If your DLT records exceed 1 GB/day → reconsider whether non-blocking retry topics are the right pattern at all (you may want a Share Group with rejected-record archival instead).

## Caveats

- **Share Groups are a moving target.** All material on KIP-932 from before October 2025 (including some of the Confluent/Instaclustr posts referenced) describes APIs and limits that have already changed by Kafka 4.1 (preview). Treat the November 2025 Spring blog and Spring Kafka 4.0.x reference docs as the canonical APIs; everything else is context.
- **`aws-msk-iam-auth` compatibility statement is not from AWS.** The "works under kafka-clients 4.x because it integrates at the SASL extension level" claim is mine, based on inspecting the library's surface area (the `build.gradle` still declares `compileOnly('org.apache.kafka:kafka-clients:2.8.1')` as of v2.3.6, 6 May 2026). It is not a certified compatibility statement. Verify in your environment.
- **Korean Spring Boot 4 / Spring Kafka 4 articles are sparse.** Toss, Kakao, Woowahan, and Kurly have not (as of May 2026) published deep-dives on either. The Spring Boot 4 migration articles cited (dev-post.com, blog.igooo.org, dico.me) are personal/community blogs, not corporate engineering blogs — useful but not authoritative. The corporate Korean blog corpus is still 3.x-flavored; this is a publishing opportunity if you ship the capstone.
- **Spring Kafka 4.0 vs Spring Boot 4.0 release dates differ slightly across sources.** Spring's own blog says Spring Kafka 4.0.0 GA on 18 Nov 2025 (Soby Chacko) and Spring Boot 4.0.0 on 20 Nov 2025 (Phil Webb); OpenLogic's migration guide says "Spring Boot 4.0 was released on November 30, 2025." Trust the Spring blog (primary source).
- **The capstone uses Aurora PostgreSQL** in places where the original profile mentions MySQL/PostgreSQL — pick one based on your stack. The transactional outbox pattern works on both.
- **Avoid mixing `@Retryable` from Spring Retry library and `@Retryable` from Spring Framework 7** if you must keep both around during migration — they share a name but live in different packages (`org.springframework.retry.annotation.Retryable` vs `org.springframework.resilience.annotation.Retryable`). IDE auto-import will burn you. Add a checkstyle rule.
- **The new Spring Framework 7 `@Retryable` uses `maxRetries` (default 3); the legacy Spring Retry `@Retryable` used `maxAttempts` (default 3, where 3 meant "1 initial + 2 retries"). Semantics differ.** Be explicit in your migration.