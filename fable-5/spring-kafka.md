---
title: "Mastering Spring for Apache Kafka: A Rigorous, Phased Learning Plan"
category: "Spring & Spring Boot"
description: "A roughly 12-week, part-time plan (6-8 hrs/week, about 85 hrs) in four phases: Quick Tour (2 wks), Production Mastery (5 wks), Framework Internals and Threading (3.5 wks), and Capstone (1.5 wks). It targets Spring Kafka 3.3.x/4.1.x on the Spring Boot 3.5/4.x baseline, learned primarily from the official reference, the spring-projects/spring-kafka source, and Korean and international production blogs. It connects existing Kafka internals knowledge (EOS V2, transactional outbox, Debezium) to Spring's abstractions at their intersection points, flags Kotlin-specific pitfalls (suspend-function listeners, data-class deserialization, trusted packages), and covers DefaultErrorHandler/CommonErrorHandler, @RetryableTopic, observation, and the 2026 header-handling CVEs."
---

# Mastering Spring for Apache Kafka: A Rigorous, Phased Learning Plan

## TL;DR
- This is a roughly 12-week, part-time plan (6-8 hrs/week, about 85 hours total) in four phases: Quick Tour (2 wks), Production Mastery (5 wks), Framework Internals and Threading (3.5 wks), and Capstone (1.5 wks). It targets Spring Kafka 3.3.x / 4.1.x on the Spring Boot 3.5 / 4.x baseline, learned primarily from the official reference, the `spring-projects/spring-kafka` source, and Korean and international production blogs.
- Target the current landscape (mid-2026): per Soby Chacko's Spring team release blog of June 9, 2026, Spring Kafka 4.1.0 (Spring Boot 4.1.0, kafka-clients 4.2.1), 4.0.6, and 3.3.16 are the GA lines. `DefaultErrorHandler` and `CommonErrorHandler` have fully replaced `SeekToCurrentErrorHandler`, EOS is V2-only, and `@RetryableTopic` plus `KafkaTemplate` and listener observation are mature.
- Lean on your existing Kafka internals knowledge. The plan connects EOS, the transactional outbox, and Debezium to Spring's abstractions at their intersection points rather than re-teaching them, and it flags Kotlin-specific pitfalls (suspend-function listeners, data-class deserialization, trusted packages) throughout.

## Key Findings

**Version landscape (verify before you start).** Per the Spring team's release blog by Soby Chacko (June 9, 2026): "we are pleased to announce that Spring for Apache Kafka 4.1.0, 4.0.6, and 3.3.16 have been released… This is the first GA release of the 4.1.x generation." These integrate respectively into Spring Boot 4.1.0, 4.0.7, and 3.5.15, and 4.1.0 uses kafka-clients 4.2.1 ("Kafka client has been updated to 4.2.1, along with maintenance bumps for Jackson, Kotlin, and slf4j"). Spring Boot 4 requires the `spring-boot-starter-kafka` dependency explicitly. Since your production stack is Kotlin and Spring Boot on EKS, pick the generation matching your Boot version. Three CVEs disclosed in that same release are directly relevant to your security posture: CVE-2026-41726 ("unbounded delegate cache keyed on user-controlled, potentially malicious selector header"), CVE-2026-41727 ("forged retry topic headers subvert retry routing and backoff behavior"), and CVE-2026-41731 ("overly broad trusted-package matching in header mappers exposes JDK classes to deserialization").

**API currency matters for filtering old resources.** `SeekToCurrentErrorHandler` and `SeekToCurrentBatchErrorHandler` are gone, replaced by `DefaultErrorHandler` and the `CommonErrorHandler` interface. `ChainedKafkaTransactionManager` is deprecated. EOS supports only `EOSMode.V2` (KIP-447 fetch-offset-request fencing) since 3.0. `KafkaTemplate` returns `CompletableFuture` rather than `ListenableFuture` since 3.0. Any tutorial showing `SeekToCurrentErrorHandler`, per-partition `transactional.id` suffixing for zombie fencing, or `ListenableFuture` is pre-3.0 and partly outdated.

**Kotlin considerations are real and specific.** Per the official reference (Asynchronous @KafkaListener Return Types): "Starting with version 3.2, @KafkaListener (and @KafkaHandler) methods can be specified with asynchronous return types… return types include CompletableFuture<?>, Mono<?> and Kotlin suspend functions." The suspend function is adapted to a `Mono` subscribed on the consumer thread to preserve ordering. But there was a real bug (#3277, "Between 3.1.4 and 3.2.0") where Kotlin `suspend` listeners broke message conversion because `MessagingMessageListenerAdapter` used `KotlinDetector.isKotlinType` where it "should have to use KotlinDetector.isSuspendingFunction(Method method)… This occurs messageConverters not working normally." Separately, spring-kafka's release notes confirm issue #4465: "Suspend @KafkaListener re-delivers a failing record without bound after DefaultErrorHandler retries are exhausted." The framework's threading is Java-based, and the project does not support coroutine-native listener containers. Gary Russell, the project lead, in GitHub Discussion #2653: "the listener container would have to be written in Kotlin to support them (a new listener container would be required). This will require a huge effort. Given that project Loom (and virtual threads) is on the horizon, it is not clear that it worth the effort because supporting Loom is trivial (I already have tested it)." For rigorous ordering, prefer a plain blocking `@KafkaListener` unless you accept out-of-order async processing.

## Details: the phased plan

### Assumptions and cadence
This is part-time alongside a full-time job: roughly 6-8 hours per week for about 12 weeks, or around 85 hours total. Each phase lists objectives, topics, curated resources with links, hands-on exercises, and self-assessment checkpoints. Use Podman for Testcontainers, pointing Testcontainers at the Podman socket via `DOCKER_HOST` or using its native Podman support, and only disable Ryuk via `TESTCONTAINERS_RYUK_DISABLED` as a last resort.

---

### Phase 0: environment and version baseline (half a week, ~3 hrs)
**Objective:** pin your versions and establish a reproducible local lab.
- Read the Spring Kafka project page and the current "Override Boot Dependencies" appendix to understand the client-compatibility matrix. Decide between Boot 3.5 with Spring Kafka 3.3.16, and Boot 4.x with Spring Kafka 4.1.x.
  - https://spring.io/projects/spring-kafka/
  - https://docs.spring.io/spring-kafka/reference/appendix/override-boot-dependencies.html
- Stand up a single-broker KRaft Kafka via Podman and a `compose.yaml`. You already know KRaft internals, so this is just wiring. Add `kafka-ui` or Redpanda Console for topic inspection.
- Checkpoint: you can produce and consume with the CLI against your local broker, and you can articulate which kafka-clients version your chosen Spring Kafka pulls in.

---

### Phase 1: quick tour, productive fast (2 weeks, ~14 hrs)
**Learning objectives:** build a producing and consuming Spring Boot (Kotlin) service with autoconfiguration, and understand `KafkaTemplate`, `@KafkaListener`, container factories, and basic consumer and producer config.

**Topics:**
- Spring Boot autoconfiguration for Kafka (`spring.kafka.*` properties): bootstrap-servers, consumer group-id, key and value serializers, `auto-offset-reset`, `enable-auto-commit`.
- `KafkaTemplate` as a thin wrapper over the `KafkaProducer` (a thread-safe singleton producer), `send()` returning `CompletableFuture`, and the default topic.
- `@KafkaListener` and `@KafkaHandler`, the `ConcurrentKafkaListenerContainerFactory` autoconfigured by Boot, and the `ConsumerRecord`, `@Payload`, and `@Header` method signatures.
- `KafkaAdmin` with `TopicBuilder` for programmatic topic creation.

**Curated resources:**
- The official 5-minute Quick Tour and "Using Spring for Apache Kafka": https://docs.spring.io/spring-kafka/reference/index.html and https://docs.spring.io/spring-kafka/reference/kafka.html
- The free Confluent Developer course "Spring Framework and Apache Kafka" (Viktor Gamov), module by module and hands-on, covering KafkaTemplate, @KafkaListener, TopicBuilder, and Kafka Streams: https://developer.confluent.io/courses/spring/apache-kafka-intro/
- Baeldung's "Intro to Apache Kafka with Spring", a solid orientation to the container and factory class hierarchy: https://www.baeldung.com/spring-kafka
- Baeldung's "Apache Kafka with Kotlin" for Kotlin idioms such as data classes and a `suspendCoroutine` producer wrapper: https://www.baeldung.com/kotlin/apache-kafka
- Korean: 박종훈's blog post "Spring에서 Kafka를 통한 비동기 통신 구현" (https://jonghoonpark.com/2025/02/22/kafka-in-spring) and Parker Blog's "Spring Boot에서 카프카 사용하기" (https://parker1609.github.io/post/spring-boot-kafka/), both clean and current Korean walkthroughs.

**Kotlin note:** use `data class` payloads with `JsonDeserializer` or `JsonSerde`. Configure `spring.json.trusted.packages` to your DTO package rather than `*`, which is both a correctness and a security control (see Phase 2). Put the Jackson Kotlin module on the classpath for no-arg data-class construction.

**Hands-on, Project A (build in week 2): IoT sensor telemetry ingest.** A producer simulates temperature and humidity sensors emitting JSON to a `sensor.readings` topic, and a consumer logs and aggregates. The exercises cover autoconfiguration, `KafkaTemplate`, `@KafkaListener`, the JSON serde, topic creation via `TopicBuilder`, and `concurrency` basics. This domain is high-throughput with a simple schema, which makes it ideal for a first end-to-end pass.

**Checkpoint:** explain what beans Boot autoconfigures (ProducerFactory, ConsumerFactory, `kafkaListenerContainerFactory`, KafkaAdmin, KafkaTemplate) and where to override each.

---

### Phase 2: practical production mastery (5 weeks, ~35 hrs)
**Learning objectives:** handle errors, retries, and DLTs correctly; master serde including Schema Registry; and understand ack modes, transaction and EOS wiring, testing, observability, and Kubernetes operational concerns.

#### 2.1 Error handling, retries, and DLT (week 3)
**Topics:** `DefaultErrorHandler` (with `FixedBackOff` or `ExponentialBackOff`), `DeadLetterPublishingRecoverer` (with the default `<topic>-dlt` or `.DLT` destination, which needs at least as many partitions as the source), `CommonDelegatingErrorHandler`, `CommonContainerStoppingErrorHandler`, `CommonLoggingErrorHandler`, and `CommonMixedErrorHandler`. Then blocking against non-blocking retries: `@RetryableTopic` and `RetryTopicConfiguration` (retry topics plus `@DltHandler`), the global fatal-exceptions list (deserialization and conversion exceptions are non-retryable by default), and `BatchListenerFailedException` for batch listeners.

**Connect to your knowledge:** non-blocking retry topics are the framework's answer to the classic "one poison pill blocks the partition" problem. Blocking stateful and stateless retry maps to the poll-timeout re-delivery semantics you already understand.

**Resources:**
- The official "Handling Exceptions" chapter: https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html, and the `@RetryableTopic` "Features" page: https://docs.spring.io/spring-kafka/reference/retrytopic/features.html
- The Lydtech Consulting blog series, which is rigorous and thorough: "Kafka Consumer Retry" (stateless against stateful, plus pitfalls), "Kafka Consumer Non-Blocking Retry: Spring Retry Topics", "Kafka Message Batch Consumer Retry", and "Kafka Idempotent Consumer & Transactional Outbox" (with a Debezium CDC demo). https://www.lydtechconsulting.com/blog-kafka-idempotent-consumer.html and https://www.lydtechconsulting.com/blog/kafka-spring-retry-topics
- Korean production practice: the velog post "Kafka 재시도, DLT 빌더 접근 방식으로 리팩토링" (moving from per-listener `@RetryableTopic` to a global `RetryTopicConfiguration` bean, matching `listenerFactory` to avoid `MessageConversionException`); "Kafka DLT 메시지를 원본 토픽으로 재전송하는 방법" (Kotlin and Spring Boot 3.x DLT replay via `KafkaListenerEndpointRegistry` pause and resume, against a replay API); and JeDevlog's "Kafka에서 처리에 실패한 메시지 재시도하기".
- ManoMano Tech, and "Robust Kafka Consumer Error Handling on a Spring Boot 3 Application" (Medium), for concise DLT and backoff recipes.

**Kotlin note:** with `@RetryableTopic` on a `suspend` listener, prefer `AckMode.MANUAL_IMMEDIATE`. A Korean write-up documents that `commitRecovered()` is ignored under the container-managed `RECORD` ack mode, which breaks retry. Also watch issue #4465, on unbounded re-delivery for suspend listeners after retries are exhausted.

#### 2.2 Serialization, deserialization, and Schema Registry (week 4)
**Topics:** `JsonSerde` and `JsonDeserializer`, type mapping and `spring.json.trusted.packages`, `ErrorHandlingDeserializer` wrapping a delegate, and Avro with the Confluent Schema Registry via `KafkaAvroDeserializer`.

**Precise mechanics (from the official docs plus Confluent):** configure the container's key and value deserializers as `ErrorHandlingDeserializer`, then set the delegates via `ErrorHandlingDeserializer.KEY_DESERIALIZER_CLASS` and `VALUE_DESERIALIZER_CLASS` (in Boot property form, `spring.deserializer.key.delegate.class` and `spring.deserializer.value.delegate.class`), pointing the value delegate at `io.confluent.kafka.serializers.KafkaAvroDeserializer` with `schema.registry.url`. Per Confluent's blog, when the delegate fails on a poison pill, "the ErrorHandlingDeserializer returns a null value and adds a DeserializationException in a header containing the cause and the raw bytes. If the ConsumerRecord contains a DeserializationException header for either the key or the value, the container's ErrorHandler is called with the failed ConsumerRecord, and the record is not passed to the listener", so failure happens before the listener and routes to the DLT. Per the official "Handling Exceptions" docs, the recoverer restores the original raw bytes: "when used in conjunction with an ErrorHandlingDeserializer, the publisher will restore the record value(), in the dead-letter producer record, to the original value that failed to be deserialized." Without the ErrorHandlingDeserializer you get `IllegalStateException: This error handler cannot process 'SerializationException's directly…`, for instance on an Avro "Unknown magic byte!".

**Security (connect this to the CVEs):** `spring.json.trusted.packages` defaults to `java.util` and `java.lang`, and `*` trusts all and is a deserialization risk. Per Baeldung's "Spring Kafka Trusted Packages Feature": "If trusted packages are configured, then Spring will make a lookup into the type headers of the incoming message… by preventing the deserialization of unwanted messages, Spring provides additional security measures to reduce security risks". It is not a defense against header spoofing. This ties directly to CVE-2026-41731 above. Note the 4.x rename of `JsonDeserializer` to `JacksonJsonDeserializer`, with the old API deprecated for removal.

**Resources:**
- The official "Serialization, Deserialization, and Message Conversion" chapter: https://docs.spring.io/spring-kafka/reference/kafka/serdes.html
- The Confluent blog post "Spring Kafka Beyond the Basics: How to Handle Failed Kafka Consumers": https://www.confluent.io/blog/spring-kafka-can-your-kafka-consumers-handle-a-poison-pill/
- Baeldung's "Spring Kafka Trusted Packages Feature": https://www.baeldung.com/spring-kafka-trusted-packages-feature

#### 2.3 Ack modes, containers, concurrency, rebalancing (week 5)
**Topics:** `ContainerProperties.AckMode` (RECORD, BATCH, TIME, COUNT, COUNT_TIME, MANUAL, MANUAL_IMMEDIATE); `enable.auto.commit` against container-managed commits; `ConcurrentMessageListenerContainer.concurrency` mapping to partitions, where concurrency must not exceed partitions and each child container is one consumer thread with one `KafkaConsumer`; rebalancing behavior; `pause()` and `resume()`, where the container keeps polling but returns no records, avoiding a rebalance; `idleBetweenPolls`; `RecordInterceptor` and `BatchInterceptor`; and consumer group management. Spring Kafka 4.1 also adds a per-listener `ackMode` attribute on `@KafkaListener`.

**Resources:**
- The official "Message Listener Containers" chapter: https://docs.spring.io/spring-kafka/reference/kafka/receiving-messages/message-listener-container.html
- Woowahan (우아한형제들), "카프카 컨슈머에 동적 쓰로틀링 적용하기", an outstanding rigorous treatment of `pause()` and `resume()` against rebalancing risk, `MessageListenerContainer`, and `@EmbeddedKafka` throttling tests: https://techblog.woowahan.com/20156/
- Woowahan, "우리 팀은 카프카를 어떻게 사용하고 있을까", on production usage patterns (EventBus, Kafka Streams, transactional outbox): https://techblog.woowahan.com/17386/
- fkwbc, "Kafka 컨슈머 그룹의 리밸런싱 지연 문제 해결", on `max.poll.interval.ms`, group-coordinator heartbeats, and rebalancing-storm avoidance.

**Hands-on, Project B: real-time fraud detection (payments).** Consume a `transactions` topic, apply rules, and emit `fraud.alerts`. The exercises cover manual ack modes, concurrency tuning, non-blocking retry for transient enrichment-service failures, DLT for unprocessable records, and an idempotent consumer with a dedupe store, which connects to your existing idempotency knowledge. Build this mid-Phase 2.

#### 2.4 Transactions and EOS wiring (week 6)
**Topics:** `KafkaTransactionManager`, a transactional `KafkaTemplate` (`transactionIdPrefix`), Boot's `spring.kafka.producer.transaction-id-prefix` (which auto-wires a `KafkaTransactionManager`), `executeInTransaction`, `sendOffsetsToTransaction`, `AfterRollbackProcessor`, `read_committed` isolation, and idempotent producer config.

**A light touch here, since you have separate EOS and outbox docs:** Spring's read-process-write EOS is `EOSMode.V2` only (KIP-447), and per the official transactions docs, `transactionIdPrefix` "must be unique per instance." In Kubernetes, derive it from the pod identity to avoid the fencing-avalanche and `ProducerFencedException` loop described in the azguards deep-dive. For Kafka-plus-DB atomicity, Spring cannot do XA across Kafka and Aurora MySQL, so use `@Transactional` chaining (DB-first or Kafka-first via nested `@Transactional`), or the transactional outbox with Debezium that you already document. `ChainedKafkaTransactionManager` is deprecated.

**Resources:**
- The official "Transactions" chapter: https://docs.spring.io/spring-kafka/reference/kafka/transactions.html, and "Exactly Once Semantics": https://docs.spring.io/spring-kafka/reference/kafka/exactly-once.html
- Soby Chacko and the Spring team's blog series on transactions in Spring Cloud Stream Kafka (outbox semantics, rollback strategies, EOS).
- azguards, "Spring Kafka Exactly-Once: Mitigating the Fencing Avalanche & Zombie Producers" (a Kubernetes-aware `transactionIdPrefix`, timeout inequalities). It is an opinionated deep-dive, so corroborate it against the official docs.
- Korean: the velog post "[Kafka] 멱등적 프로듀서, 트랜잭션", and the 토스 테크 "Apache Kafka 데이터센터 이중화" series (Active-Active consumer offset sync) for advanced production context.

#### 2.5 Testing (week 7, first half)
**Topics:** `spring-kafka-test` with `@EmbeddedKafka` (`EmbeddedKafkaBroker`, `KafkaTestUtils`), Testcontainers `KafkaContainer`, when to use which, and `MockProducer` and `MockConsumer` for pure unit logic.

**Decision-ready guidance:** use `@EmbeddedKafka` for fast in-JVM Spring slice and integration tests, since there is no image pull and no CI changes. Use Testcontainers when you need Schema Registry, multiple brokers, or production-parity images. KRaft mode is disabled by default in `@EmbeddedKafka` because of KafkaClusterTestKit limitations, and the new consumer-group protocol (KIP-848) needs a real KRaft broker, so test that against Testcontainers rather than EmbeddedKafka. For Podman, point Testcontainers at the Podman socket, and note that a GraalVM native `@EmbeddedKafka` image can cut memory and time.

**Resources:**
- The official testing chapter (spring-kafka-test); Conduktor's "Testing Kafka Applications: Testcontainers, Embedded Kafka, and Mocks" (https://www.conduktor.io/blog/testing-kafka-testcontainers-embedded-mocks); Baeldung's "Testing Kafka and Spring Boot" (https://www.baeldung.com/spring-boot-kafka-testing); and LimePoint's "Exploring EmbeddedKafka and KafkaContainers."
- Lydtech's component-test-framework repos, which are Testcontainers-based, for realistic examples.

#### 2.6 Observability (week 7, second half)
**Topics:** Micrometer `Timer`s (`spring.kafka.listener`, `spring.kafka.template`); `observationEnabled=true` on `KafkaTemplate` and `ContainerProperties` (or `spring.kafka.listener.observation-enabled` and `spring.kafka.template.observation-enabled`), which enables Micrometer Tracing and OpenTelemetry with `traceparent` header propagation through Kafka; a custom `KafkaTemplateObservationConvention` or `KafkaListenerObservationConvention`; `MicrometerConsumerListener` and `MicrometerProducerListener` for client metrics; and consumer lag monitoring. Note that enabling observation disables the built-in Micrometer timers, since they are managed per observation instead. Know that trade-off.

**Resources:**
- The official "Monitoring" chapter: https://docs.spring.io/spring-kafka/reference/kafka/micrometer.html, and the Observation appendix: https://docs.spring.io/spring-kafka/reference/appendix/micrometer.html
- Baeldung's "Micrometer Observation and Spring Kafka": https://www.baeldung.com/spring-kafka-micrometer
- Piotr Minkowski's "Kafka Tracing with Spring Boot and Open Telemetry": https://piotrminkowski.com/2023/11/15/kafka-tracing-with-spring-boot-and-open-telemetry/
- Lag monitoring: Burrow (LinkedIn), `kafka_exporter` (danielqsj), KMinion, Kafka Lag Exporter, and klag, all of which are Prometheus and Grafana friendly.

#### 2.7 Spring Kafka in Kubernetes (woven into week 7)
**Topics:** graceful shutdown (Boot's `server.shutdown=graceful`, the container stop honoring in-flight records, and a `preStop` hook with `terminationGracePeriodSeconds` at least as long as worst-case processing time); health checks (the Actuator `KafkaHealthIndicator`); consumer-lag-based autoscaling with the KEDA Kafka scaler (`lagThreshold`, `desiredReplicas = ceil(currentLag/lagThreshold)`, `maxReplicaCount` no greater than the partition count); and the rebalancing cost of scale events.

**Resources:** Piotr Minkowski's "Autoscaling on Kubernetes with KEDA and Kafka" (https://piotrminkowski.com/2022/01/18/autoscaling-on-kubernetes-with-keda-and-kafka/), the k8s.guide KEDA page, and Kedify on long-running jobs and ScaledJob.

**Hands-on, Project C: logistics and shipping tracking.** Track parcel state transitions across topics, deploy to your EKS cluster, and add KEDA autoscaling on lag, graceful shutdown, tracing, and lag dashboards. This exercises the full Phase 2 operational surface.

**Phase 2 checkpoint:** you can (1) design a blocking against non-blocking retry and DLT strategy and justify it; (2) wire `ErrorHandlingDeserializer` with Avro and a DLT; (3) explain ack-mode commit timing; (4) configure EOS with a per-pod `transactionIdPrefix`; (5) choose between EmbeddedKafka and Testcontainers; and (6) propagate a trace through Kafka and alert on lag.

---

### Phase 3: framework internals and threading model (3.5 weeks, ~25 hrs)
**Learning objectives:** read the spring-kafka source fluently, and explain the container hierarchy, threading, the poll loop, offset-commit mechanics, lifecycle, annotation processing, and the relationship to the non-thread-safe `KafkaConsumer`.

#### 3.1 Container hierarchy and threading (week 8)
- `MessageListenerContainer` (the interface) leads to `AbstractMessageListenerContainer`, then to `KafkaMessageListenerContainer` (single-threaded, receiving all messages from all assigned topics and partitions on one thread) against `ConcurrentMessageListenerContainer` (which creates N `KafkaMessageListenerContainer` children, with partitions distributed evenly across them). Concurrency greater than the partition count leaves consumers idle.
- The non-thread-safe `KafkaConsumer` rule: each `KafkaMessageListenerContainer` has exactly one `ListenerConsumer` bound to one thread, and all consumer operations (poll, commit, pause and resume, seek) execute on that single thread. `pause()` and `resume()` are documented as thread-safe requests "processed by the consumer thread" before the next poll.
- Source files: read `KafkaMessageListenerContainer.java`, especially the inner class `ListenerConsumer`, and `ConcurrentMessageListenerContainer.java` on `main`.
  - https://github.com/spring-projects/spring-kafka/blob/main/spring-kafka/src/main/java/org/springframework/kafka/listener/KafkaMessageListenerContainer.java

#### 3.2 The poll loop, offset commits, lifecycle (week 9)
- `ListenerConsumer.run()`: the poll, invoke-listener, and commit cycle; `idleBetweenPolls` (the minimum of the property and `max.poll.interval.ms` minus the current batch processing time); how `AckMode` translates to `commitSync` and `commitAsync` timing; `AssignmentCommitOption`; the `failedRecords` deque; how the `CommonErrorHandler` is invoked inside the loop (`handleOne`, `handleBatchAndReturnRemaining`); and how seeks rewind partitions.
- Container lifecycle: `start`, `stop`, `pause`, and `resume`; the `SmartLifecycle` phase; `ConsumerStartingEvent`, `ConsumerStartedEvent`, `ConsumerStoppingEvent`, and `ConsumerStoppedEvent`; and `enforceRebalance`.
- Transaction integration inside the loop: `invokeInTransaction`, `recordAfterRollback`, and `sendOffsetsToTransaction`.

#### 3.3 Annotation processing and the adapter chain (week 10)
- `@EnableKafka` registers `KafkaListenerAnnotationBeanPostProcessor`, which implements `BeanPostProcessor` and `SmartInitializingSingleton`. It detects `@KafkaListener` and `@KafkaHandler`, builds `MethodKafkaListenerEndpoint`s, and registers them in the `KafkaListenerEndpointRegistry`, which owns container lifecycle. Method-level annotation gives one container per method, and class-level gives one container serving the `@KafkaHandler` methods.
- The listener adapter chain: `MessagingMessageListenerAdapter` and its record and batch variants, the `MessageConverter`s, `HandlerAdapter`, and argument resolvers. This is where the Kotlin `suspend` and coroutine detection lives, and where bug #3277 (`isKotlinType` against `isSuspendingFunction`) sat.
- A customization hook: override `processListener` in a custom `KafkaListenerAnnotationBeanPostProcessor`, registered via an `ImportBeanDefinitionRegistrar`. See Mateusz Gajowski's "Using custom properties for listeners in Spring Kafka" (https://mateusz.gajow.ski/spring/kafka-custom-properties/).
- Source: `KafkaListenerAnnotationBeanPostProcessor.java` on `main`, whose authors include Gary Russell and Artem Bilan.
  - https://github.com/spring-projects/spring-kafka/blob/main/spring-kafka/src/main/java/org/springframework/kafka/annotation/KafkaListenerAnnotationBeanPostProcessor.java

#### 3.4 Source-reading guide and talks (week 11, first half)
**A suggested reading order in spring-projects/spring-kafka:**
1. `annotation/EnableKafka`, `KafkaListenerAnnotationBeanPostProcessor`, `config/KafkaListenerEndpointRegistry`
2. `listener/KafkaMessageListenerContainer` (`ListenerConsumer`), then `ConcurrentMessageListenerContainer`
3. `listener/adapter/MessagingMessageListenerAdapter` plus the converters
4. `listener/DefaultErrorHandler`, `FailedRecordProcessor` and `FailedBatchProcessor`, `DeadLetterPublishingRecoverer`
5. `core/DefaultKafkaProducerFactory` and `KafkaTemplate`, plus `transaction/KafkaTransactionManager`
6. `retrytopic/*` for the `@RetryableTopic` machinery.

**Talks and primary voices (note their recency):** Gary Russell, project lead since 2016, in the SpringOne 2016 replay (https://spring.io/blog/2017/02/06/springone-platform-2016-replay-spring-for-apache-kafka/), Tanzu Tuesdays 53 "What's New in Spring for Apache Kafka 2.7" (https://www.youtube.com/watch?v=mdX3JKJ-DeE), and the Bootiful Podcast episode; plus the SpringOne 2023 Spring and Kafka session with Viktor Gamov. These are older API-wise but excellent for design rationale, so always cross-check specifics against the current reference. GitHub Discussions (#2653 on coroutines, #3805 on ordering) capture Russell's design reasoning verbatim.

**Checkpoint:** sketch the full path of a record from `consumer.poll()` to your listener method and back to an offset commit, naming each class and the thread it runs on, and explain exactly why you must never call a `KafkaConsumer` from another thread and how Spring enforces this.

---

### Phase 4: capstone and broad-domain projects (1.5 weeks, ~8 hrs, plus optional ongoing work)
**Capstone options (pick one substantial build):**
- A stock-market market-data processor: high-throughput ingest, EOS read-process-write into derived topics, `read_committed` consumers, tracing, and KEDA autoscaling. This stresses transactions and performance.
- An ad-tech clickstream pipeline: Avro with Schema Registry, `ErrorHandlingDeserializer` routing to a DLT, non-blocking retry topics, and lag dashboards. This stresses serde and resilience.
- Healthcare event streaming: strict ordering per patient via partition-key design, an idempotent consumer with an outbox and Debezium touchpoint, and auditing via tracing. This stresses correctness and EOS.

**Additional short domain drills (for breadth, optional):** gaming leaderboard and matchmaking events (Kafka Streams with Spring), a social-media activity feed (fan-out), and a library or inventory system, which mirrors Dilip Sundarraj's course domain.

**Courses and books to accompany this (reference, not sequential):**
- Dilip Sundarraj, "Apache Kafka for Developers using Spring Boot" (Udemy), hands-on with producers and consumers, error handling, retry and recovery, and EmbeddedKafka testing. The code repo is `dilipsundarraj1/kafka-for-developers-using-spring-boot-v2`, updated to Spring Boot 4, Testcontainers, and Kubernetes. His "Kafka Streams API for Developers using Java/Spring Boot 3.x" (Packt) covers streams.
- John Thompson / Spring Framework Guru, "Introduction to Kafka with Spring Boot" (Udemy), covering retries, poison pills, and DLTs, with companion PDFs.
- Confluent Developer's "Spring Framework and Apache Kafka" (free, Viktor Gamov), already used in Phase 1. Revisit the Streams module.
- Korean book: 최원영, 『아파치 카프카 애플리케이션 프로그래밍 with 자바』 (비제이퍼블릭, 2021), the first Korean book to cover Spring Kafka, MirrorMaker2, and cloud Kafka, with code at github.com/bjpublic/apache-kafka-with-java. It is from 2021, so verify APIs against the current docs.
- An international company production blog: Trendyol Tech (Umit Berber), "How to implement retry logic with Spring Kafka" (https://medium.com/trendyol-tech/how-to-implement-retry-logic-with-spring-kafka-710b51501ce2), a production retry-topic design plus a discussion of why they avoided the built-in `SeekToCurrentErrorHandler` with `DeadLetterPublishingRecoverer`, which blocks the main consumer and gives no custom error-topic naming.
- *Kafka in Action* (Manning; Scott, Gamov, Klein; 2022) is good for client-level Kafka and Schema Registry, but it does not cover Spring Kafka, so use it only for internals reinforcement. There is no separate 2nd edition of this title, so do not confuse it with *Kafka Streams in Action, 2e* by Bill Bejeck.

---

## Recommendations (staged, with thresholds)

1. Weeks 1-2 (now): pin versions (Boot 3.5 with Spring Kafka 3.3.16 if you're on Boot 3.x, or Boot 4.x with 4.1.x if migrating), stand up the Podman KRaft lab, and complete Project A. *Threshold to advance:* you can explain every autoconfigured bean and override any of them.
2. Weeks 3-7: work Phase 2 in order, and build Projects B and C. *Threshold:* your fraud-detection service survives injected poison pills (routed to the DLT), transient failures (non-blocking retry), and a rolling restart on EKS without message loss or duplicate side effects.
3. Weeks 8-11: do the internals phase only after you're production-fluent, because reading `ListenerConsumer` is far more valuable once you've hit real ack-mode and rebalancing behavior. *Threshold:* you can trace a record end to end through the source and defend the single-thread `KafkaConsumer` invariant.
4. Weeks 11-12: the capstone. *Threshold:* one hardened, observable, autoscaled service with a written correctness argument for its delivery guarantees.
5. Ongoing signals that change the plan: if you migrate to Spring Boot 4.x, re-read the "What's New in 4.1" and "Migration from 4.0" chapters (the ack-mode enum changes, the `spring-boot-starter-kafka` requirement, the `JacksonJsonDeserializer` rename). If you adopt the new consumer-group protocol (KIP-848), shift all such tests to Testcontainers, since EmbeddedKafka KRaft is still unstable for it. If you enable coroutine or suspend listeners, track issue #4465 and prefer blocking listeners where ordering is contractual.

## Caveats
- Version drift: the exact patch numbers (4.1.0, 4.0.6, 3.3.16), the kafka-clients 4.2.1 pairing, and the CVE identifiers were current as of the June 9, 2026 Spring Kafka release announcement. Confirm the latest patch and any newer CVEs before pinning.
- Opinionated third-party posts, including the azguards fencing deep-dive and some Medium articles, contain strong claims and occasional forward-looking or non-primary assertions. Always corroborate against docs.spring.io and the source.
- Korean blog specifics, such as `commitRecovered()` being ignored under the `RECORD` ack mode with `@RetryableTopic`, reflect specific author findings on specific versions. Validate against your pinned version.
- Coroutine support remains partial by design. The project lead has stated that a coroutine-native container is not planned ("This will require a huge effort"), and virtual threads (Loom) are the framework's preferred concurrency direction. Factor this into Kotlin architecture decisions.
- Time estimates assume prior Kafka fluency, which you have. Someone without your internals background would need substantially longer. The plan deliberately does not re-teach KRaft, RecordBatch v2, compression, zero-copy, EOS theory, or the outbox and Debezium patterns you already know; it links them to Spring's abstractions at the intersection points only.
