---
title: "Mastering Spring for Apache Kafka: A Rigorous, Phased Learning Plan"
category: "Spring & Spring Boot"
description: "A ~12-week, part-time (6–8 hrs/week, ~85 hrs) four-phase plan — Quick Tour (2 wks) → Production Mastery (5 wks) → Framework Internals & Threading (3.5 wks) → Capstone (1.5 wks) — targeting Spring Kafka 3.3.x/4.1.x on the Spring Boot 3.5/4.x baseline, learned primarily from the official reference, the spring-projects/spring-kafka source, and Korean + international production blogs. Connects existing Kafka internals knowledge (EOS V2, transactional outbox, Debezium) to Spring's abstractions at their intersection points, flags Kotlin-specific pitfalls (suspend-function listeners, data-class deserialization, trusted packages), and covers DefaultErrorHandler/CommonErrorHandler, @RetryableTopic, observation, and the 2026 header-handling CVEs."
---

# Mastering Spring for Apache Kafka: A Rigorous, Phased Learning Plan

## TL;DR
- **A ~12-week, part-time (6–8 hrs/week, ~85 hrs total) plan in four phases** — Quick Tour (2 wks) → Production Mastery (5 wks) → Framework Internals & Threading (3.5 wks) → Capstone (1.5 wks) — targeting Spring Kafka 3.3.x / 4.1.x on the Spring Boot 3.5 / 4.x baseline, learned primarily from the official reference, the `spring-projects/spring-kafka` source, and Korean + international production blogs.
- **Target the current landscape (mid-2026):** per Soby Chacko's Spring team release blog (June 9, 2026), Spring Kafka 4.1.0 (Spring Boot 4.1.0, kafka-clients 4.2.1), 4.0.6, and 3.3.16 are the GA lines; `DefaultErrorHandler`/`CommonErrorHandler` have fully replaced `SeekToCurrentErrorHandler`, EOS is V2-only, and `@RetryableTopic` + `KafkaTemplate`/listener observation are mature.
- **Lean on your existing Kafka internals knowledge:** the plan connects EOS, transactional outbox, and Debezium to Spring's abstractions at their intersection points rather than re-teaching them, and it flags Kotlin-specific pitfalls (suspend-function listeners, data-class deserialization, trusted packages) throughout.

## Key Findings

**Version landscape (verify before you start).** Per the Spring team's release blog by Soby Chacko (June 9, 2026): "we are pleased to announce that Spring for Apache Kafka 4.1.0, 4.0.6, and 3.3.16 have been released… This is the first GA release of the 4.1.x generation." These integrate respectively into Spring Boot 4.1.0, 4.0.7, and 3.5.15, and 4.1.0 uses kafka-clients 4.2.1 ("Kafka client has been updated to 4.2.1, along with maintenance bumps for Jackson, Kotlin, and slf4j"). Spring Boot 4 requires the `spring-boot-starter-kafka` dependency explicitly. Since your production stack is Kotlin/Spring Boot on EKS, pick the generation matching your Boot version. Three CVEs disclosed in that same release are directly relevant to your security posture: CVE-2026-41726 ("unbounded delegate cache keyed on user-controlled, potentially malicious selector header"), CVE-2026-41727 ("forged retry topic headers subvert retry routing and backoff behavior"), and CVE-2026-41731 ("overly broad trusted-package matching in header mappers exposes JDK classes to deserialization").

**API currency matters for filtering old resources.** `SeekToCurrentErrorHandler` and `SeekToCurrentBatchErrorHandler` are gone, replaced by `DefaultErrorHandler` and the `CommonErrorHandler` interface. `ChainedKafkaTransactionManager` is deprecated. EOS supports only `EOSMode.V2` (KIP-447 fetch-offset-request fencing) since 3.0. `KafkaTemplate` returns `CompletableFuture` (not `ListenableFuture`) since 3.0. Any tutorial showing `SeekToCurrentErrorHandler`, per-partition `transactional.id` suffixing for zombie fencing, or `ListenableFuture` is pre-3.0 and partly outdated.

**Kotlin considerations are real and specific.** Per the official reference (Asynchronous @KafkaListener Return Types): "Starting with version 3.2, @KafkaListener (and @KafkaHandler) methods can be specified with asynchronous return types… return types include CompletableFuture<?>, Mono<?> and Kotlin suspend functions." The suspend function is adapted to a `Mono` subscribed on the consumer thread to preserve ordering. But there was a real bug (#3277, "Between 3.1.4 and 3.2.0") where Kotlin `suspend` listeners broke message conversion because `MessagingMessageListenerAdapter` used `KotlinDetector.isKotlinType` where it "should have to use KotlinDetector.isSuspendingFunction(Method method)… This occurs messageConverters not working normally." Separately, spring-kafka's release notes confirm issue #4465: "Suspend @KafkaListener re-delivers a failing record without bound after DefaultErrorHandler retries are exhausted." The framework's threading is Java-based; the project does not support coroutine-native listener containers. Gary Russell (project lead) in GitHub Discussion #2653: "the listener container would have to be written in Kotlin to support them (a new listener container would be required). This will require a huge effort. Given that project Loom (and virtual threads) is on the horizon, it is not clear that it worth the effort because supporting Loom is trivial (I already have tested it)." For rigorous ordering, prefer plain blocking `@KafkaListener` unless you accept out-of-order async processing.

## Details — The Phased Plan

### Assumptions & cadence
Part-time alongside a full-time job: **~6–8 hours/week for ~12 weeks (~85 total hours)**. Each phase lists objectives, topics, curated resources (with links), hands-on exercises, and self-assessment checkpoints. Use Podman for Testcontainers (point Testcontainers at the Podman socket via `DOCKER_HOST`, or use its native Podman support; only disable Ryuk via `TESTCONTAINERS_RYUK_DISABLED` as a last resort).

---

### PHASE 0 — Environment & version baseline (½ week, ~3 hrs)
**Objective:** Pin your versions and establish a reproducible local lab.
- Read the Spring Kafka project page and the current "Override Boot Dependencies" appendix to understand the client-compatibility matrix. Decide: Boot 3.5 + Spring Kafka 3.3.16, or Boot 4.x + Spring Kafka 4.1.x.
  - https://spring.io/projects/spring-kafka/
  - https://docs.spring.io/spring-kafka/reference/appendix/override-boot-dependencies.html
- Stand up a single-broker KRaft Kafka via Podman + a `compose.yaml` (you already know KRaft internals — this is just wiring). Add `kafka-ui` or Redpanda Console for topic inspection.
- **Checkpoint:** You can produce/consume with the CLI against your local broker and articulate which kafka-clients version your chosen Spring Kafka pulls in.

---

### PHASE 1 — QUICK TOUR: productive fast (2 weeks, ~14 hrs)
**Learning objectives:** Build a producing + consuming Spring Boot (Kotlin) service with autoconfiguration; understand `KafkaTemplate`, `@KafkaListener`, container factories, and basic consumer/producer config.

**Topics:**
- Spring Boot autoconfiguration for Kafka (`spring.kafka.*` properties): bootstrap-servers, consumer group-id, key/value serializers, `auto-offset-reset`, `enable-auto-commit`.
- `KafkaTemplate` as a thin wrapper over the `KafkaProducer` (thread-safe singleton producer); `send()` returning `CompletableFuture`; default topic.
- `@KafkaListener` and `@KafkaHandler`; `ConcurrentKafkaListenerContainerFactory` autoconfigured by Boot; `ConsumerRecord`/`@Payload`/`@Header` method signatures.
- `KafkaAdmin` + `TopicBuilder` for programmatic topic creation.

**Curated resources:**
- **Official 5-minute Quick Tour + "Using Spring for Apache Kafka":** https://docs.spring.io/spring-kafka/reference/index.html and https://docs.spring.io/spring-kafka/reference/kafka.html
- **Confluent Developer free course, "Spring Framework and Apache Kafka" (Viktor Gamov):** module-by-module hands-on (KafkaTemplate, @KafkaListener, TopicBuilder, Kafka Streams). https://developer.confluent.io/courses/spring/apache-kafka-intro/
- **Baeldung "Intro to Apache Kafka with Spring":** solid orientation to the container/factory class hierarchy. https://www.baeldung.com/spring-kafka
- **Baeldung "Apache Kafka with Kotlin"** for Kotlin idioms (data classes, `suspendCoroutine` producer wrapper). https://www.baeldung.com/kotlin/apache-kafka
- **Korean:** 박종훈 blog "Spring에서 Kafka를 통한 비동기 통신 구현" (https://jonghoonpark.com/2025/02/22/kafka-in-spring) and Parker Blog "Spring Boot에서 카프카 사용하기" (https://parker1609.github.io/post/spring-boot-kafka/) — clean, current Korean walk-throughs.

**Kotlin note:** Use `data class` payloads with `JsonDeserializer`/`JsonSerde`. Configure `spring.json.trusted.packages` to your DTO package (not `*`) — both a correctness and a security control (see Phase 2). Put the Jackson Kotlin module on the classpath for no-arg data-class construction.

**Hands-on — PROJECT A (build in week 2): IoT Sensor Telemetry Ingest.** A producer simulates temperature/humidity sensors emitting JSON to a `sensor.readings` topic; a consumer logs and aggregates. Exercises: autoconfiguration, `KafkaTemplate`, `@KafkaListener`, JSON serde, topic creation via `TopicBuilder`, `concurrency` basics. *Why this domain:* high-throughput, simple schema — ideal for a first end-to-end pass.

**Checkpoint:** Explain what beans Boot autoconfigures (ProducerFactory, ConsumerFactory, `kafkaListenerContainerFactory`, KafkaAdmin, KafkaTemplate) and where to override each.

---

### PHASE 2 — PRACTICAL PRODUCTION MASTERY (5 weeks, ~35 hrs)
**Learning objectives:** Handle errors, retries, and DLTs correctly; master serde including Schema Registry; understand ack modes, transactions/EOS wiring, testing, observability, and Kubernetes operational concerns.

#### 2.1 Error handling, retries & DLT (week 3)
**Topics:** `DefaultErrorHandler` (+ `FixedBackOff`/`ExponentialBackOff`), `DeadLetterPublishingRecoverer` (default `<topic>-dlt` / `.DLT` destination, needs ≥ as many partitions as source), `CommonDelegatingErrorHandler`, `CommonContainerStoppingErrorHandler`, `CommonLoggingErrorHandler`, `CommonMixedErrorHandler`; **blocking vs non-blocking retries**: `@RetryableTopic` / `RetryTopicConfiguration` (retry topics + `@DltHandler`); the global fatal-exceptions list (deserialization/conversion exceptions are non-retryable by default); `BatchListenerFailedException` for batch listeners.

**Connect to your knowledge:** Non-blocking retry topics are the framework's answer to the classic "one poison pill blocks the partition" problem. Blocking stateful/stateless retry maps to poll-timeout re-delivery semantics you already understand.

**Resources:**
- Official "Handling Exceptions": https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html and `@RetryableTopic` "Features": https://docs.spring.io/spring-kafka/reference/retrytopic/features.html
- **Lydtech Consulting blog series** (rigorous and thorough): "Kafka Consumer Retry" (stateless vs stateful, pitfalls), "Kafka Consumer Non-Blocking Retry: Spring Retry Topics", "Kafka Message Batch Consumer Retry", "Kafka Idempotent Consumer & Transactional Outbox" (with Debezium CDC demo). https://www.lydtechconsulting.com/blog-kafka-idempotent-consumer.html and https://www.lydtechconsulting.com/blog/kafka-spring-retry-topics
- **Korean production practice:** velog "Kafka 재시도, DLT 빌더 접근 방식으로 리팩토링" (moving from per-listener `@RetryableTopic` to a global `RetryTopicConfiguration` bean, matching `listenerFactory` to avoid `MessageConversionException`); "Kafka DLT 메시지를 원본 토픽으로 재전송하는 방법" (Kotlin/Spring Boot 3.x DLT replay via `KafkaListenerEndpointRegistry` pause/resume vs a replay API); JeDevlog "Kafka에서 처리에 실패한 메시지 재시도하기".
- ManoMano Tech and "Robust Kafka Consumer Error Handling on a Spring Boot 3 Application" (Medium) for concise DLT+backoff recipes.

**Kotlin note:** With `@RetryableTopic` on a `suspend` listener, prefer `AckMode.MANUAL_IMMEDIATE` (a Korean write-up documents that `commitRecovered()` is ignored under the container-managed `RECORD` ack mode, breaking retry). Watch issue #4465 (unbounded re-delivery on suspend listeners after retries exhausted).

#### 2.2 Serialization / deserialization & Schema Registry (week 4)
**Topics:** `JsonSerde`/`JsonDeserializer`, type mapping and `spring.json.trusted.packages`; **`ErrorHandlingDeserializer`** wrapping a delegate; Avro + Confluent Schema Registry via `KafkaAvroDeserializer`.

**Precise mechanics (from official docs + Confluent):** Configure the container's key/value deserializers as `ErrorHandlingDeserializer`, then set the delegates via `ErrorHandlingDeserializer.KEY_DESERIALIZER_CLASS` / `VALUE_DESERIALIZER_CLASS` (Boot property form: `spring.deserializer.key.delegate.class` / `spring.deserializer.value.delegate.class`), pointing the value delegate at `io.confluent.kafka.serializers.KafkaAvroDeserializer` with `schema.registry.url`. Per Confluent's blog, when the delegate fails on a poison pill, "the ErrorHandlingDeserializer returns a null value and adds a DeserializationException in a header containing the cause and the raw bytes. If the ConsumerRecord contains a DeserializationException header for either the key or the value, the container's ErrorHandler is called with the failed ConsumerRecord, and the record is not passed to the listener" — so failure happens *before* the listener and routes to the DLT. Per the official "Handling Exceptions" docs, the recoverer restores the original raw bytes: "when used in conjunction with an ErrorHandlingDeserializer, the publisher will restore the record value(), in the dead-letter producer record, to the original value that failed to be deserialized." Without the ErrorHandlingDeserializer you get `IllegalStateException: This error handler cannot process 'SerializationException's directly…` (e.g., Avro "Unknown magic byte!").

**Security (connect to CVEs):** `spring.json.trusted.packages` defaults to `java.util`,`java.lang`; `*` trusts all and is a deserialization risk. Per Baeldung's "Spring Kafka Trusted Packages Feature": "If trusted packages are configured, then Spring will make a lookup into the type headers of the incoming message… by preventing the deserialization of unwanted messages, Spring provides additional security measures to reduce security risks" (but it is not a defense against header spoofing). This ties directly to CVE-2026-41731 above. Note the 4.x rename `JsonDeserializer` → `JacksonJsonDeserializer` (old API deprecated for removal).

**Resources:**
- Official "Serialization, Deserialization, and Message Conversion": https://docs.spring.io/spring-kafka/reference/kafka/serdes.html
- Confluent blog "Spring Kafka Beyond the Basics – How to Handle Failed Kafka Consumers": https://www.confluent.io/blog/spring-kafka-can-your-kafka-consumers-handle-a-poison-pill/
- Baeldung "Spring Kafka Trusted Packages Feature": https://www.baeldung.com/spring-kafka-trusted-packages-feature

#### 2.3 Ack modes, containers, concurrency, rebalancing (week 5)
**Topics:** `ContainerProperties.AckMode` (RECORD, BATCH, TIME, COUNT, COUNT_TIME, MANUAL, MANUAL_IMMEDIATE); `enable.auto.commit` vs container-managed commits; `ConcurrentMessageListenerContainer.concurrency` mapping to partitions (concurrency ≤ partitions; each child container = one consumer thread = one `KafkaConsumer`); rebalancing behavior; `pause()`/`resume()` (container keeps polling but returns no records, avoiding rebalance); `idleBetweenPolls`; `RecordInterceptor`/`BatchInterceptor`; consumer group management. (Spring Kafka 4.1 also adds a per-listener `ackMode` attribute on `@KafkaListener`.)

**Resources:**
- Official "Message Listener Containers": https://docs.spring.io/spring-kafka/reference/kafka/receiving-messages/message-listener-container.html
- **Woowahan (우아한형제들) "카프카 컨슈머에 동적 쓰로틀링 적용하기"** — outstanding rigorous treatment of `pause()`/`resume()` vs rebalancing risk, `MessageListenerContainer`, and `@EmbeddedKafka` throttling tests. https://techblog.woowahan.com/20156/
- **Woowahan "우리 팀은 카프카를 어떻게 사용하고 있을까"** — production usage patterns (EventBus, Kafka Streams, transactional outbox). https://techblog.woowahan.com/17386/
- **fkwbc "Kafka 컨슈머 그룹의 리밸런싱 지연 문제 해결"** — `max.poll.interval.ms`, group-coordinator heartbeats, rebalancing-storm avoidance.

**Hands-on — PROJECT B: Real-time Fraud Detection (payments).** Consume a `transactions` topic; apply rules; emit `fraud.alerts`. Exercises: manual ack modes, concurrency tuning, non-blocking retry for transient enrichment-service failures, DLT for unprocessable records, idempotent consumer (dedupe store) connecting to your existing idempotency knowledge. *Build mid-Phase 2.*

#### 2.4 Transactions & EOS wiring (week 6)
**Topics:** `KafkaTransactionManager`, transactional `KafkaTemplate` (`transactionIdPrefix`), Boot's `spring.kafka.producer.transaction-id-prefix` (auto-wires a `KafkaTransactionManager`), `executeInTransaction`, `sendOffsetsToTransaction`, `AfterRollbackProcessor`, `read_committed` isolation, idempotent producer config.

**Light touch (you have separate EOS/outbox docs):** Spring's read→process→write EOS is `EOSMode.V2` only (KIP-447); per the official transactions docs, `transactionIdPrefix` "must be unique per instance." In Kubernetes derive it from the pod identity to avoid the "fencing avalanche"/`ProducerFencedException` loop described in the azguards deep-dive. For Kafka+DB atomicity, Spring cannot do XA across Kafka and Aurora MySQL — use `@Transactional` chaining (DB-first or Kafka-first via nested `@Transactional`) or the transactional outbox + Debezium pattern you already document. `ChainedKafkaTransactionManager` is deprecated.

**Resources:**
- Official "Transactions": https://docs.spring.io/spring-kafka/reference/kafka/transactions.html and "Exactly Once Semantics": https://docs.spring.io/spring-kafka/reference/kafka/exactly-once.html
- Soby Chacko / Spring team blog series on transactions in Spring Cloud Stream Kafka (outbox semantics, rollback strategies, EOS).
- azguards "Spring Kafka Exactly-Once: Mitigating the Fencing Avalanche & Zombie Producers" (K8s-aware `transactionIdPrefix`, timeout inequalities) — an opinionated deep-dive; corroborate against official docs.
- **Korean:** velog "[Kafka] 멱등적 프로듀서, 트랜잭션" and 토스 테크 "Apache Kafka 데이터센터 이중화" series (Active-Active consumer offset sync) for advanced production context.

#### 2.5 Testing (week 7, first half)
**Topics:** `spring-kafka-test` + `@EmbeddedKafka` (`EmbeddedKafkaBroker`, `KafkaTestUtils`); Testcontainers `KafkaContainer`; when to use which; `MockProducer`/`MockConsumer` for pure unit logic.

**Guidance (decision-ready):** Use `@EmbeddedKafka` for fast in-JVM Spring slice/integration tests (no image pull, no CI changes); use Testcontainers when you need Schema Registry, multi-broker, or production-parity images. KRaft mode is disabled by default in `@EmbeddedKafka` (KafkaClusterTestKit limitations), and the new consumer-group protocol (KIP-848) needs a real KRaft broker — so test that against Testcontainers, not EmbeddedKafka. For Podman, point Testcontainers at the Podman socket; a GraalVM native `@EmbeddedKafka` image can cut memory/time.

**Resources:**
- Official testing chapter (spring-kafka-test); Conduktor "Testing Kafka Applications: Testcontainers, Embedded Kafka, and Mocks" (https://www.conduktor.io/blog/testing-kafka-testcontainers-embedded-mocks); Baeldung "Testing Kafka and Spring Boot" (https://www.baeldung.com/spring-boot-kafka-testing); LimePoint "Exploring EmbeddedKafka and KafkaContainers."
- Lydtech's component-test-framework (Testcontainers-based) repos for realistic examples.

#### 2.6 Observability (week 7, second half)
**Topics:** Micrometer `Timer`s (`spring.kafka.listener`, `spring.kafka.template`); `observationEnabled=true` on `KafkaTemplate` + `ContainerProperties` (or `spring.kafka.listener.observation-enabled` / `spring.kafka.template.observation-enabled`) enabling Micrometer Tracing / OpenTelemetry with `traceparent` header propagation through Kafka; custom `KafkaTemplateObservationConvention` / `KafkaListenerObservationConvention`; `MicrometerConsumerListener`/`MicrometerProducerListener` for client metrics; consumer lag monitoring. Enabling observation *disables* the built-in Micrometer timers (managed per-observation instead) — know this trade-off.

**Resources:**
- Official "Monitoring": https://docs.spring.io/spring-kafka/reference/kafka/micrometer.html and Observation appendix: https://docs.spring.io/spring-kafka/reference/appendix/micrometer.html
- Baeldung "Micrometer Observation and Spring Kafka": https://www.baeldung.com/spring-kafka-micrometer
- Piotr Minkowski "Kafka Tracing with Spring Boot and Open Telemetry": https://piotrminkowski.com/2023/11/15/kafka-tracing-with-spring-boot-and-open-telemetry/
- **Lag monitoring:** Burrow (LinkedIn), `kafka_exporter` (danielqsj), KMinion, Kafka Lag Exporter, klag — all Prometheus/Grafana friendly.

#### 2.7 Spring Kafka in Kubernetes (woven into week 7)
**Topics:** Graceful shutdown (Boot `server.shutdown=graceful`; container stop honoring in-flight records; `preStop` hook + `terminationGracePeriodSeconds` ≥ worst-case processing time); health checks (Actuator `KafkaHealthIndicator`); consumer lag–based autoscaling with **KEDA** Kafka scaler (`lagThreshold`, `desiredReplicas = ceil(currentLag/lagThreshold)`, `maxReplicaCount ≤ partitions`); rebalancing cost on scale events.

**Resources:** Piotr Minkowski "Autoscaling on Kubernetes with KEDA and Kafka" (https://piotrminkowski.com/2022/01/18/autoscaling-on-kubernetes-with-keda-and-kafka/); k8s.guide KEDA page; Kedify on long-running jobs / ScaledJob.

**Hands-on — PROJECT C: Logistics/Shipping Tracking.** Track parcel state transitions across topics; deploy to your EKS cluster; add KEDA autoscaling on lag, graceful shutdown, tracing, and lag dashboards. *Exercises the full Phase 2 operational surface.*

**Phase 2 checkpoint:** You can (1) design a blocking vs non-blocking retry+DLT strategy and justify it; (2) wire `ErrorHandlingDeserializer` + Avro + DLT; (3) explain ack-mode commit timing; (4) configure EOS with per-pod `transactionIdPrefix`; (5) choose EmbeddedKafka vs Testcontainers; (6) propagate a trace through Kafka and alert on lag.

---

### PHASE 3 — FRAMEWORK INTERNALS & THREADING MODEL (3.5 weeks, ~25 hrs)
**Learning objectives:** Read the spring-kafka source fluently; explain the container hierarchy, threading, poll loop, offset-commit mechanics, lifecycle, annotation processing, and the relationship to the non-thread-safe `KafkaConsumer`.

#### 3.1 Container hierarchy & threading (week 8)
- `MessageListenerContainer` (interface) → `AbstractMessageListenerContainer` → `KafkaMessageListenerContainer` (single-threaded; receives all messages from all assigned topics/partitions on one thread) vs `ConcurrentMessageListenerContainer` (creates N `KafkaMessageListenerContainer` children; partitions distributed evenly across them). Concurrency > partitions ⇒ idle consumers.
- **The non-thread-safe `KafkaConsumer` rule:** each `KafkaMessageListenerContainer` has exactly one `ListenerConsumer` bound to one thread; all consumer operations (poll, commit, pause/resume, seek) execute on that single thread. `pause()`/`resume()` are documented as thread-safe requests "processed by the consumer thread" before the next poll.
- Source files: read `KafkaMessageListenerContainer.java` (inner class `ListenerConsumer`) and `ConcurrentMessageListenerContainer.java` on `main`.
  - https://github.com/spring-projects/spring-kafka/blob/main/spring-kafka/src/main/java/org/springframework/kafka/listener/KafkaMessageListenerContainer.java

#### 3.2 The poll loop, offset commits, lifecycle (week 9)
- `ListenerConsumer.run()`: the poll→invoke-listener→commit cycle; `idleBetweenPolls` (min of the property and `max.poll.interval.ms` minus current batch processing time); how `AckMode` translates to `commitSync`/`commitAsync` timing; `AssignmentCommitOption`; the `failedRecords` deque; how the `CommonErrorHandler` is invoked inside the loop (`handleOne`/`handleBatchAndReturnRemaining`) and how seeks rewind partitions.
- Container lifecycle: `start`/`stop`/`pause`/`resume`, `SmartLifecycle` phase, `ConsumerStartingEvent`/`ConsumerStartedEvent`/`ConsumerStoppingEvent`/`ConsumerStoppedEvent`, `enforceRebalance`.
- Transaction integration inside the loop: `invokeInTransaction`, `recordAfterRollback`, `sendOffsetsToTransaction`.

#### 3.3 Annotation processing & the adapter chain (week 10)
- `@EnableKafka` registers `KafkaListenerAnnotationBeanPostProcessor` (implements `BeanPostProcessor`, `SmartInitializingSingleton`); it detects `@KafkaListener`/`@KafkaHandler`, builds `MethodKafkaListenerEndpoint`s, and registers them in the `KafkaListenerEndpointRegistry`, which owns container lifecycle. Method-level ⇒ one container per method; class-level ⇒ one container serving `@KafkaHandler` methods.
- The listener adapter chain: `MessagingMessageListenerAdapter` (and record/batch variants), `MessageConverter`s, `HandlerAdapter`, argument resolvers. This is where the Kotlin `suspend`/coroutine detection lives (bug #3277 — `isKotlinType` vs `isSuspendingFunction`).
- Customization hook: override `processListener` in a custom `KafkaListenerAnnotationBeanPostProcessor` (register via `ImportBeanDefinitionRegistrar`) — see Mateusz Gajowski, "Using custom properties for listeners in Spring Kafka" (https://mateusz.gajow.ski/spring/kafka-custom-properties/).
- Source: `KafkaListenerAnnotationBeanPostProcessor.java` on `main` (authors incl. Gary Russell, Artem Bilan).
  - https://github.com/spring-projects/spring-kafka/blob/main/spring-kafka/src/main/java/org/springframework/kafka/annotation/KafkaListenerAnnotationBeanPostProcessor.java

#### 3.4 Source-reading guide & talks (week 11, first half)
**Suggested reading order in spring-projects/spring-kafka:**
1. `annotation/EnableKafka`, `KafkaListenerAnnotationBeanPostProcessor`, `config/KafkaListenerEndpointRegistry`
2. `listener/KafkaMessageListenerContainer` (`ListenerConsumer`) → `ConcurrentMessageListenerContainer`
3. `listener/adapter/MessagingMessageListenerAdapter` + converters
4. `listener/DefaultErrorHandler`, `FailedRecordProcessor`/`FailedBatchProcessor`, `DeadLetterPublishingRecoverer`
5. `core/DefaultKafkaProducerFactory`/`KafkaTemplate`, `transaction/KafkaTransactionManager`
6. `retrytopic/*` for the `@RetryableTopic` machinery.

**Talks/primary voices (note recency):** Gary Russell (project lead since 2016) — SpringOne 2016 replay (https://spring.io/blog/2017/02/06/springone-platform-2016-replay-spring-for-apache-kafka/), Tanzu Tuesdays 53 "What's New in Spring for Apache Kafka 2.7" (https://www.youtube.com/watch?v=mdX3JKJ-DeE), and the Bootiful Podcast episode; the SpringOne 2023 Spring + Kafka session with Viktor Gamov. These are older API-wise but excellent for design rationale — always cross-check specifics against the current reference. GitHub Discussions (#2653 coroutines, #3805 ordering) capture Russell's design reasoning verbatim.

**Checkpoint:** Sketch the full path of a record from `consumer.poll()` to your listener method and back to an offset commit, naming each class and the thread it runs on; explain exactly why you must never call a `KafkaConsumer` from another thread and how Spring enforces this.

---

### PHASE 4 — CAPSTONE + BROAD-DOMAIN PROJECTS (1.5 weeks, ~8 hrs, plus optional ongoing)
**Capstone options (pick one substantial build):**
- **Stock-market market-data processor:** high-throughput ingest, EOS read-process-write into derived topics, `read_committed` consumers, tracing, KEDA autoscaling — stresses transactions + performance.
- **Ad-tech clickstream pipeline:** Avro + Schema Registry, `ErrorHandlingDeserializer` → DLT, non-blocking retry topics, lag dashboards — stresses serde + resilience.
- **Healthcare event streaming:** strict ordering per patient (partition-key design), idempotent consumer + outbox/Debezium touchpoint, audit via tracing — stresses correctness + EOS.

**Additional short domain drills (for breadth, optional):** gaming leaderboard/matchmaking events (Kafka Streams + Spring), social-media activity feed (fan-out), library/inventory system (mirrors Dilip Sundarraj's course domain).

**Courses & books to accompany (reference, not sequential):**
- **Dilip Sundarraj, "Apache Kafka for Developers using Spring Boot" (Udemy)** — hands-on producers/consumers, error handling/retry/recovery, EmbeddedKafka testing; code repo `dilipsundarraj1/kafka-for-developers-using-spring-boot-v2` (updated to Spring Boot 4, Testcontainers, K8s). His "Kafka Streams API for Developers using Java/Spring Boot 3.x" (Packt) for streams.
- **John Thompson / Spring Framework Guru, "Introduction to Kafka with Spring Boot" (Udemy)** — retries, poison pills, DLTs, with companion PDFs.
- **Confluent Developer "Spring Framework and Apache Kafka" (free, Viktor Gamov)** — already used in Phase 1; revisit the Streams module.
- **Korean book:** 최원영, 『아파치 카프카 애플리케이션 프로그래밍 with 자바』 (비제이퍼블릭, 2021) — first Korean book to cover Spring Kafka + MirrorMaker2 + cloud Kafka; code at github.com/bjpublic/apache-kafka-with-java. (2021, so verify APIs against current docs.)
- **International company production blog:** Trendyol Tech (Umit Berber), "How to implement retry logic with Spring Kafka" (https://medium.com/trendyol-tech/how-to-implement-retry-logic-with-spring-kafka-710b51501ce2) — a production retry-topic design and a discussion of why they avoided the built-in `SeekToCurrentErrorHandler` + `DeadLetterPublishingRecoverer` (blocks the main consumer, no custom error-topic naming).
- **"Kafka in Action" (Manning; Scott, Gamov, Klein; 2022):** good for client-level Kafka and Schema Registry, but it does **not** cover Spring Kafka — use it only for internals reinforcement. (There is no separate "2nd edition" of this title; do not confuse it with *Kafka Streams in Action, 2e* by Bill Bejeck.)

---

## Recommendations (staged, with thresholds)

1. **Weeks 1–2 (now):** Pin versions (Boot 3.5 + Spring Kafka 3.3.16 if you're on Boot 3.x; Boot 4.x + 4.1.x if migrating), stand up the Podman KRaft lab, and complete Project A. *Threshold to advance:* you can explain every autoconfigured bean and override any of them.
2. **Weeks 3–7:** Work Phase 2 in order; build Projects B and C. *Threshold:* your fraud-detection service survives injected poison pills (routed to DLT), transient failures (non-blocking retry), and a rolling restart on EKS without message loss or duplicate side effects.
3. **Weeks 8–11:** Do the internals phase only after you're production-fluent — reading `ListenerConsumer` is far more valuable once you've hit real ack-mode and rebalancing behavior. *Threshold:* you can trace a record end-to-end through the source and defend the single-thread `KafkaConsumer` invariant.
4. **Weeks 11–12:** Capstone. *Threshold:* one hardened, observable, autoscaled service with a written correctness argument for its delivery guarantees.
5. **Ongoing signals that change the plan:** if you migrate to Spring Boot 4.x, re-read the "What's New in 4.1" and "Migration from 4.0" chapters (ack-mode enum changes, `spring-boot-starter-kafka` requirement, `JacksonJsonDeserializer` rename); if you adopt the new consumer-group protocol (KIP-848), shift all such tests to Testcontainers (EmbeddedKafka KRaft is still unstable for it); if you enable coroutine/suspend listeners, track issue #4465 and prefer blocking listeners where ordering is contractual.

## Caveats
- **Version drift:** exact patch numbers (4.1.0/4.0.6/3.3.16), the kafka-clients 4.2.1 pairing, and the CVE identifiers were current as of the June 9, 2026 Spring Kafka release announcement; confirm the latest patch and any newer CVEs before pinning.
- **Opinionated third-party posts** (the azguards fencing deep-dive, some Medium articles) contain strong claims and occasional forward-looking or non-primary assertions — always corroborate against docs.spring.io and the source.
- **Korean blog specifics** (e.g., `commitRecovered()` ignored under `RECORD` ack mode with `@RetryableTopic`) reflect specific author findings on specific versions; validate against your pinned version.
- **Coroutine support** remains partial by design; the project lead has stated a coroutine-native container is not planned ("This will require a huge effort"), and virtual threads (Loom) are the framework's preferred concurrency direction — factor this into Kotlin architecture decisions.
- **Time estimates assume prior Kafka fluency** (which you have); someone without your internals background would need substantially longer. The plan deliberately does not re-teach KRaft, RecordBatch v2, compression, zero-copy, EOS theory, or the outbox/Debezium patterns you already know — it links them to Spring's abstractions at the intersection points only.