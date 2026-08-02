---
title: "The Spring Framework Event Subsystem: A Phased Curriculum for a Senior Kotlin/Spring Engineer"
category: "Spring & Spring Boot"
description: "An eight-week reading and lab plan for the Spring event subsystem, built around one fact: in-process events are synchronous, transaction-bound, and lost on JVM crash. Starts at source level with SimpleApplicationEventMulticaster, EventListenerMethodProcessor, ApplicationListenerMethodAdapter, and ResolvableType generic resolution, plus the Spring Boot startup event sequence published before the context exists. Then the sharp edges of @TransactionalEventListener, including why an AFTER_COMMIT write is silently discarded without REQUIRES_NEW (the listener fires from triggerAfterCommit before cleanupAfterCompletion). Covers async dispatch and the context loss that comes with it, Micrometer context propagation, virtual threads, and Boot 4.1's spring.task.execution.propagate-context. Then Spring Modulith 2.x: the Event Publication Registry as a broker-free outbox, the 2.0 status lifecycle, Kafka externalization and its ordering caveats, and the Namastack and JobRunr outbox backends. Ends with adjacent mechanisms and a staged Kafka migration path, @RecordApplicationEvents and Modulith Scenario testing, observability, eight escalating Kotlin projects, and verification exercises that make each failure mode reproduce on demand."
---

# The Spring Framework Event Subsystem: A Phased Curriculum for a Senior Kotlin/Spring Engineer

## TL;DR
- The plan runs about eight weeks over six phases plus a Phase 0 baseline. It starts with source-code internals (multicaster dispatch, `EventListenerMethodProcessor`, `ResolvableType`), moves through transactional and async semantics, then Spring Modulith and event externalization, and finishes on testing, observability, and production hardening. Everything is anchored on primary sources (Spring reference docs, Javadoc, GitHub source) and verified in your own Kotlin and Testcontainers labs.
- One behavior drives the rest: Spring in-process events are synchronous and transaction-bound by default, and they die with the JVM. Transactional listeners, `@Async`, Modulith's Event Publication Registry, and Kafka externalization all exist to manage some piece of that. Prioritize the experiments that make each of those three properties break in front of you.
- Community opinion is genuinely divided on whether in-process events belong in cross-module communication at all. This report flags exactly where the disagreement lands (Modulith leaking broker coupling into the consuming listener, and the "fat event" and CRUD-event anti-patterns) and gives concrete migration paths to Kafka. Bias: for a same-deployment modular monolith, prefer Spring Modulith over hand-rolled brokered events until you have a proven cross-service consumer.

## Key findings

1. **Dispatch is centralized and synchronous by default.** Event dispatch runs through `SimpleApplicationEventMulticaster.multicastEvent(...)`, and by default all listeners are invoked in the calling thread. Per the Spring Javadoc: "By default, all listeners are invoked in the calling thread. This allows the danger of a rogue listener blocking the entire application, but adds minimal overhead." You make it async by setting a `TaskExecutor` on the multicaster. Read this class first.
2. **`@EventListener` is registered at bean post-processing.** `EventListenerMethodProcessor` turns annotated methods into `ApplicationListener` instances, each wrapped in an `ApplicationListenerMethodAdapter` (a `GenericApplicationListener`), with the event type resolved via `ResolvableType`. Arbitrary non-`ApplicationEvent` payloads are wrapped in `PayloadApplicationEvent` and unwrapped before the method is called.
3. **Transactional listeners have sharp edges.** `@TransactionalEventListener` defaults to `AFTER_COMMIT`. Per the `TransactionalEventListener` Javadoc (Spring Framework 7.0.7 API): "The default phase is `TransactionPhase.AFTER_COMMIT`. If no transaction is in progress, the event is not processed at all unless `fallbackExecution()` has been enabled explicitly." Writes inside an `AFTER_COMMIT` listener are not persisted unless a new transaction is started (`@Transactional(propagation = REQUIRES_NEW)`). The listener fires from `triggerAfterCommit` before `cleanupAfterCompletion`, so a `REQUIRED` listener silently joins the already-committed transaction and its writes are lost.
4. **Spring Modulith gives you a broker-free outbox.** `@ApplicationModuleListener` is a meta-annotation combining `@Async`, `@Transactional(propagation = REQUIRES_NEW)`, and `@TransactionalEventListener`. The Event Publication Registry persists a log entry per listener inside the original business transaction and marks it complete on success, which buys you at-least-once semantics plus restart recovery.
5. **Framework 7 changed nothing in the event subsystem, and Boot 4.1 added opt-in async context propagation.** Spring Framework 7.0 went GA on November 13, 2025 (Juergen Hoeller: "I am pleased to announce that Spring Framework 7.0 is generally available now!") and ships no documented changes to `@EventListener`, `@TransactionalEventListener`, or `ApplicationEventMulticaster`. Spring Boot 4.1 adds opt-in async context propagation for `@Async` methods via the `spring.task.execution.propagate-context` property. Spring Modulith reached 2.1 GA on June 11, 2026 (Oliver Drotbohm).

## Details

### Phase 0: baseline and mental model (half a week)
**Objective:** nail the default semantics before touching internals.

Read the Spring Framework reference "Standard and Custom Events" section and Baeldung's ["Spring Events"](https://www.baeldung.com/spring-events). Confirm empirically that events are synchronous and single-threaded, that since Spring 4.2 any POJO can be an event (wrapped internally in `PayloadApplicationEvent`), and that listeners run in the publisher's transaction by default. For Korean framing, 토비의 스프링 6 - 이해와 원리 and 토비의 스프링 부트 - 이해와 원리 (Inflearn, instructor tobyilee / 이일민, KSUG founder) give you DI and bean-lifecycle grounding along with the "build-it-yourself to understand it" method that suits your source-reading preference. **Effort:** about 4h.

### Phase 1: core internals and source reading (1.5 weeks)
**Objective:** trace an event from `publishEvent` to listener invocation in the debugger, and explain generic type resolution.

Recommended `spring-context` source-reading order:

1. `ApplicationEventPublisher` (interface), then `AbstractApplicationContext.publishEvent(...)` for payload wrapping and multicaster delegation.
2. `ApplicationEventMulticaster` → `AbstractApplicationEventMulticaster` (listener retrieval and `ListenerRetriever` caching by event type) → `SimpleApplicationEventMulticaster.multicastEvent(ApplicationEvent, ResolvableType)` (dispatch loop, `ErrorHandler`, optional `TaskExecutor`). The generics-aware `multicastEvent(event, ResolvableType)` overload is the one to study.
3. `ApplicationListener` → `SmartApplicationListener` → `GenericApplicationListener` for full generic event-type handling. As of 5.3.5, `GenericApplicationListener` formally extends `SmartApplicationListener`.
4. `EventListenerMethodProcessor`, a `SmartInitializingSingleton` that registers listeners after singletons instantiate, then `ApplicationListenerMethodAdapter`. Study `resolveDeclaredEventTypes`, `supportsEventType(ResolvableType)`, `getResolvableType`, condition and SpEL handling via `EventExpressionEvaluator`, and `PayloadApplicationEvent` unwrapping. Source: `github.com/spring-projects/spring-framework/.../context/event/ApplicationListenerMethodAdapter.java`.
5. `ResolvableType` and `ResolvableTypeProvider`, the mechanism that lets a `PayloadApplicationEvent<T>` or a generic event such as `EntityCreatedEvent<Bid>` be matched despite type erasure. Understand the two escape hatches: a concrete subclass that fixes the type parameter, or implementing `ResolvableTypeProvider`.
6. `PayloadApplicationEvent`, plus `@Order` and `Ordered` for ordering among listeners of the same event.

Then work through the Spring Boot startup event sequence, which is unusual because early events are published *before the context exists*. A `SpringApplicationRunListener` (an SPI registered via `spring.factories` or `AutoConfiguration.imports`) is the entry point, and the single built-in `EventPublishingRunListener` bridges each lifecycle callback to an event broadcast through its own `SimpleApplicationEventMulticaster`. The order, per the Boot reference "SpringApplication" docs, is `ApplicationStartingEvent` → `ApplicationEnvironmentPreparedEvent` → `ApplicationContextInitializedEvent` → `ApplicationPreparedEvent` → (`WebServerInitializedEvent`, `ContextRefreshedEvent`) → `ApplicationStartedEvent` → `AvailabilityChangeEvent` (LivenessState and ReadinessState) → `ApplicationReadyEvent`, with `ApplicationFailedEvent` on startup exception. Note that `ContextRefreshedEvent` and `ContextClosedEvent` come from Framework, not Boot, and do not extend `SpringApplicationEvent`.

**Resources:** DeepWiki's "SpringApplication and Application Lifecycle" (a good source-line map), and reflectoring.io "Spring Boot Application Events Explained." **Effort:** about 12h.

### Phase 2: transactional events (1.5 weeks)
**Objective:** master `@TransactionalEventListener` and its failure modes end to end.

The phases are `BEFORE_COMMIT`, `AFTER_COMMIT` (default), `AFTER_ROLLBACK`, and `AFTER_COMPLETION`. Mechanically, the listener registers a `TransactionSynchronization` callback. `AFTER_COMMIT` fires from `triggerAfterCommit(status)`, which runs before `cleanupAfterCompletion(status)`, so `TransactionSynchronizationManager` still holds the `EntityManagerHolder` with `transactionActive=true`. A `Propagation.REQUIRED` listener therefore "joins" the committed transaction and its writes are silently discarded, because no flush or commit follows.

Pitfalls to reproduce:

1. Writes in `AFTER_COMMIT` are not persisted without `REQUIRES_NEW`.
2. The whole listener is a silent no-op when no transaction is active, unless `fallbackExecution=true`.
3. Reads succeed inside the listener via Hibernate's first-level cache, which masks the problem.
4. JPA flush and persistence-context lifecycle, including lazy loading after commit (`LazyInitializationException`) once the context closes.
5. Combining `@Async`, `@TransactionalEventListener`, and `REQUIRES_NEW` to get a genuinely separate transaction on a separate thread.

**Primary and authoritative sources:** the `@TransactionalEventListener` Javadoc; DZone's "Transaction Synchronization and Spring Application Events"; Andrei Roșca's "Spring puzzler: the @TransactionalEventListener," which is the best source-level explanation of the `triggerAfterCommit` and `cleanupAfterCompletion` ordering; and Zbigniew Artemiuk (Pragmatists), "Spring events and transactions, be cautious!" **Korean deep-dives, all high quality:** cheese10yun, "ApplicationEventPublisher 이벤트 기반 트랜잭션 처리"; findstar (Soo Story), "스프링 이벤트 기능을 사용할 때의 고려할 점"; and Tecoble (우아한테크코스), "스프링 이벤트 적용기," which covers the connection-pool-of-1 experiment that exposes synchronous cascades. **Effort:** about 12h.

### Phase 3: async and threading (1 week)
**Objective:** understand thread-boundary context loss and how to restore it.

There are two ways to go async: configure `SimpleApplicationEventMulticaster` globally with a `TaskExecutor`, which makes *all* listeners async, or annotate a single listener with `@Async` (plus `@EnableAsync`). Facts to verify for yourself:

- Async listener exceptions are not propagated to the caller. A `void` async listener's exception is only reachable via `AsyncUncaughtExceptionHandler`, wired through `AsyncConfigurer.getAsyncUncaughtExceptionHandler()`. Checked exceptions from any listener are wrapped in `UndeclaredThrowableException`.
- Async listeners cannot publish a follow-on event by returning a value. That only works for synchronous listeners.
- Transaction, `SecurityContext`, and MDC or tracing context are all lost across the thread boundary.
- The fix is Micrometer Context Propagation: register `ThreadLocalAccessor`s and decorate the executor with `ContextPropagatingTaskDecorator`, or use `@Async("propagatingContextExecutor")`. The Spring Framework reference "Observability Support" page documents this and explicitly notes that a custom async multicaster loses ThreadLocals and that the Context Propagation library is the remedy.
- Virtual threads (Boot 3.2+): `spring.threads.virtual.enabled=true` makes the auto-configured `applicationTaskExecutor` a `SimpleAsyncTaskExecutor` that starts one virtual thread per task, and that backs `@Async`. But Spring only swaps executors it owns, so a hand-defined `ThreadPoolTaskExecutor` for `@Async` keeps platform threads. Watch ThreadLocal memory pressure when you spawn tens of thousands of virtual threads.
- In-JVM events die with the process. That durability gap is the motivation for Phase 4.

**Boot 4.1 note, from targeted research:** Boot 4.1 adds opt-in async context propagation for `@Async` methods via `spring.task.execution.propagate-context`, and only when the `AsyncTaskExecutor` is auto-configured. It forwards the Micrometer observation and tracing context across the thread boundary. The docs scope this to `@Async` and reactive pipelines. Whether it automatically covers async `@EventListener` dispatch is not stated in primary sources, so treat it as unconfirmed and verify yourself. **Effort:** about 8h.

### Phase 4: Spring Modulith (1.5 weeks)
**Objective:** persistent, recoverable events and controlled externalization.

Core building blocks, from the Spring Modulith reference "Working with Application Events," v2.1:

- `@ApplicationModuleListener` is `@Async` plus `@Transactional(REQUIRES_NEW)` plus `@TransactionalEventListener` in one annotation.
- The Event Publication Registry writes a log entry per interested transactional listener on publication, inside the original business transaction. An aspect marks the entry completed only if the listener succeeds, and failed entries remain for retry. Persistence comes from `spring-modulith-starter-{jpa,jdbc,mongodb,neo4j}` (JDBC auto-creates the table unless disabled), and serialization from `spring-modulith-events-jackson`.
- The 2.0 lifecycle, since November 2025, adds an explicit `EventPublication.Status` of `PUBLISHED`, `PROCESSING`, `COMPLETED`, `FAILED`, or `RESUBMITTED`. A Staleness Monitor scheduled task can mark stuck publications `FAILED`. Recovery goes through `FailedEventPublications.resubmit(ResubmissionOptions)` and `IncompleteEventPublications`, with `republish-outstanding-events-on-restart` for crash recovery. Completion modes are `UPDATE` (default), `DELETE`, and `ARCHIVE`; in `UPDATE` mode you must purge completed rows yourself or the table grows unbounded.
- Externalization means annotating event types with `@Externalized("target::#{key}")` and adding a broker module (`spring-modulith-events-kafka`, `-amqp`, `-jms`, or `-messaging`). It is implemented as a transactional event listener guarded by the registry, so failed broker sends can be resubmitted. In other words, a transactional outbox without standing up Kafka on day one.
- On the outbox pattern and ordering: the registry *is* an outbox, but ordering is not guaranteed. Per Axual's analysis, "In error scenarios, it is possible to have Spring Modulith publish a previously incomplete event while events that came later are already published. Hence ordering is not guaranteed. If ordering is important for the use case, then CDC with Debezium is the best option as it guarantees ordering." Note also the known issue where a Kafka externalization entry can be marked completed even when the send failed (spring-modulith #395), so verify current behavior on your version.
- Advanced outbox backends (2.1): for multi-instance, order-preserving publication, delegate externalization to Namastack Outbox or JobRunr via `spring.modulith.events.externalization.mode=outbox` (`spring-modulith-starter-namastack` or `-jobrunr`). Namastack is relational-DB-only.

**Status:** Modulith 2.1 GA shipped June 11, 2026, built on Boot 4 and Framework 7; 2.0 GA was November 21, 2025. **Authoritative talks and writing:** Oliver Drotbohm's "Building better monoliths" (Spring I/O 2019, on YouTube) and "Spring Modulith: A Deep Dive" (speakerdeck.com/olivergierke), plus his book *Modulithic Applications with Spring* (announced, due 2026; treat it as not yet released). **Blogs:** spring.io, "Simplified Event Externalization with Spring Modulith" (September 22, 2023); Baeldung, "Event Externalization with Spring Modulith"; Dan Vega, "Spring Modulith Externalized Events." **Effort:** about 12h.

### Phase 5: adjacent mechanisms and when to use which (half a week)
**Objective:** place in-process events in the wider messaging landscape and know the migration path.

- In-process Spring events are same-JVM, transactional, and need no infrastructure. Best for decoupling modules within one deployment. Not durable, not cross-process.
- Spring Integration gives you in-JVM EIP message channels and flows. Heavier, and worth it when you need routers, transformers, or adapters.
- Project Reactor gives you reactive streams (`Sinks` and `Flux`) for backpressure-aware in-process event streams, under a different concurrency model.
- Spring Cloud Stream is a binder abstraction over Kafka and RabbitMQ for cross-service messaging with minimal broker-specific code. See spring.io, "A Use Case for Transactions: Outbox Pattern…Spring Cloud Stream Kafka Binder."
- Raw Kafka or Spring Kafka is durable, replayable, partitioned, and ordered within a partition. It is the target once consumers live in other services.

**A staged, low-risk migration path:** publish domain events in-process via `ApplicationEventPublisher` or `AbstractAggregateRoot`; keep events DTO-shaped so they are serialization-ready; add a `@TransactionalEventListener` or a Modulith `@Externalized` forwarder to Kafka; move the consumer out of process; and if strict ordering or consistency is required, replace the app-level forwarder with Debezium CDC on the outbox table.

**Divided-opinion flag:** Thomas Pierrain and others argue that Modulith's elegance leaks once you externalize. The consuming listener has to change annotation and becomes coupled to the broker, which resurfaces exactly the infrastructure Modulith hid. Weigh this before committing to in-process events as your cross-module contract. **Effort:** about 4h.

### Phase 6: testing, observability, and production concerns (1 week)
**Objective:** test event flows deterministically and instrument them in production.

- TestContext support: `@RecordApplicationEvents` plus an injected `ApplicationEvents` lets you stream and assert on published events. Per the Spring reference "Application Events," this has existed "Since Spring Framework 5.3.3" (Spring Boot 2.4.2), and the required `ApplicationEventsTestExecutionListener` "is registered by default and only needs to be manually registered if you have custom configuration via @TestExecutionListeners that does not include the default listeners." With JUnit Jupiter, declare an `ApplicationEvents` parameter on `@Test`, `@BeforeEach`, or `@AfterEach`.
- Modulith testing: `@ApplicationModuleTest` bootstraps a single module, and you inject `PublishedEvents` or `AssertablePublishedEvents`. The `Scenario` API (`scenario.stimulate(...).andWaitForEventOfType(...).matchingMappedValue(...).toArrive()`) makes async and transactional event tests deterministic. `spring-modulith-junit` (1.3+) skips tests unaffected by changes.
- Async determinism: use Awaitility to await state changes, use `spring.modulith` and `Scenario` timeouts, and for raw `@Async` await on a latch or on the registry.
- Testcontainers with Podman: run Aurora-compatible MySQL and Kafka or Redpanda containers for integration tests. Set `DOCKER_HOST` to the rootless Podman socket, or use Testcontainers' Podman support.
- Observability: instrument with the Micrometer Observation API. Per spring-framework #30089 and #31130, Spring deliberately does not auto-create observations for `@Async` or `@EventListener`, because "an event being processed…doesn't tell much about the use case." Prefer domain-specific custom observations plus context propagation across async boundaries, and verify trace continuity with and without the `ContextPropagatingTaskDecorator`.
- Debugging aid: set `logging.level.org.springframework.context.event.EventListenerMethodProcessor=TRACE` to print registered listeners at startup, and raise `org.springframework.context` logging to trace publications.

**Anti-patterns, with sources:** cascading or chained events that create hidden control flow and hard-to-debug ordering (CodeOpinion, martinrichards.me); "fat events" and CRUD-shaped events that leak schema and couple consumers (CodeOpinion, "Beware! Anti-patterns in EDA"; Martin Richards, "Event Design Patterns"); ordering assumptions in async or registry delivery; memory pressure from many virtual-thread listeners holding ThreadLocals; and treating commands as events. **Effort:** about 8h.

## Hands-on projects (Kotlin and Spring Boot, escalating difficulty)

1. **Minimal `ApplicationEventMulticaster` clone.** *Teaches:* the dispatch machinery, listener retrieval and caching, `@Order`, and sync-versus-executor dispatch. *APIs:* `ApplicationListener`, `ResolvableType`, `TaskExecutor`, `ErrorHandler`. *Done:* a test suite that mirrors `SimpleApplicationEventMulticaster` behavior (ordering, error isolation, executor dispatch) passes against your clone.
2. **Domain events in an aggregate.** *Teaches:* Spring Data's publication mechanism and its limits. *APIs:* `AbstractAggregateRoot.registerEvent`, `@DomainEvents`, `@AfterDomainEventPublication`, `@EventListener`. *Done:* you prove events fire only on `repository.save/delete` and demonstrate the flush-bypass gap, where a dirty-checking update publishes nothing.
3. **Order and payment saga with transactional events plus failure injection.** *Teaches:* phase semantics and the `REQUIRES_NEW` requirement. *APIs:* `@TransactionalEventListener(phase=…)`, `@Transactional(REQUIRES_NEW)`, `ApplicationEventPublisher`. *Done:* a test proves an `AFTER_COMMIT` write is lost without `REQUIRES_NEW`, that `AFTER_ROLLBACK` fires on rollback, and that with no transaction the listener is a no-op unless `fallbackExecution=true`.
4. **Hand-rolled transactional outbox versus the Modulith registry.** *Teaches:* the dual-write problem, the atomic outbox, and CDC. *APIs:* `@TransactionalEventListener(BEFORE_COMMIT)`, an `outbox` table on Aurora MySQL with HikariCP, Debezium into Kafka, then swap in Spring Modulith's Event Publication Registry. *Done:* both deliver at-least-once under injected broker failure, and you can articulate the ordering difference (Debezium preserves order, registry resubmission can reorder).
5. **Modulith monolith with Kafka externalization.** *Teaches:* module boundaries, durable internal events, and externalization. *APIs:* `ApplicationModules.verify()`, `@ApplicationModuleListener`, `@Externalized`, `spring-modulith-events-kafka`. *Done:* `verify()` passes, internal listeners run post-commit on a separate transaction, `OrderCompleted` lands on a Kafka topic, and killing the app mid-delivery still republishes on restart.
6. **Observability lab.** *Teaches:* trace propagation across async event boundaries. *APIs:* Micrometer Observation API, `ContextPropagatingTaskDecorator`, an OTLP exporter, MDC. *Done:* a distributed trace shows the publisher and the async listener in one trace *only* when the propagating decorator is enabled, and you can show the broken trace without it.
7. *(stretch)* **Generic-event resolution harness.** *Teaches:* `ResolvableType` and erasure. *Done:* you prove `EntityCreatedEvent<Bid>` is matched by a concrete subclass and by `ResolvableTypeProvider`, but not by a raw generic instance.
8. *(stretch)* **Virtual-thread throughput bench.** *Teaches:* the impact of the executor model. *Done:* JMH or wrk numbers comparing async listener throughput on `ThreadPoolTaskExecutor` versus a virtual-thread `SimpleAsyncTaskExecutor` under I/O-bound listeners.

## Empirical verification exercises

- **Prove the `AFTER_COMMIT` write loss.** Connection pool of 1, save an entity, publish, and have the listener write without `REQUIRES_NEW`. Assert the row is absent, add `REQUIRES_NEW`, assert it is present.
- **Prove generic resolution.** Publish a raw `EntityCreatedEvent<Bid>` and a `ResolvableTypeProvider` variant, then assert that only the resolvable one reaches an `EntityCreatedEvent<Bid>` listener.
- **Prove the no-op without a transaction.** Publish from a non-transactional method to an `AFTER_COMMIT` listener and assert it never runs. Flip `fallbackExecution=true` and assert it runs.
- **Prove exception swallowing.** Throw from an `@Async` listener, then assert the caller sees nothing and only `AsyncUncaughtExceptionHandler` observes it.
- **Measure async throughput.** Platform pool versus virtual threads, with an I/O-bound listener.
- **Demonstrate the crash durability gap.** A `kill -9` between commit and the in-JVM listener loses the event. Repeat with the Modulith registry and `republish-outstanding-events-on-restart`, and the event is recovered on restart.

## Recommendations

- **Weeks 1 to 3 (Phases 0 to 2):** internals and transactional events. **Gate to advance:** you can single-step in the debugger from `publishEvent` into `ApplicationListenerMethodAdapter`, and explain from the source *why* an `AFTER_COMMIT` write vanished.
- **Weeks 4 and 5 (Phases 3 and 4):** async and threading, then Modulith. **Gate:** the registry recovers incomplete events after a simulated crash, and you can show context propagation fixing a broken async trace.
- **Weeks 6 to 8 (Phases 5 and 6, plus projects 4 to 6):** adjacent mechanisms, testing, observability. **Gate:** a working outbox, both hand-rolled and Modulith, and a Modulith-to-Kafka externalization with end-to-end traces and deterministic tests.
- **Decision thresholds.** Stay with in-process or Modulith events while all consumers share the deployment and you don't need replay. Escalate to Kafka when a consumer moves to another service, when you need durable replay or audit, or when throughput or retention outgrows a DB outbox table. Escalate from Modulith externalization to Debezium CDC the moment strict cross-partition ordering or exactly-once-into-broker becomes a hard requirement. Introduce the Namastack or JobRunr outbox backends if you need multi-instance, order-preserving externalization from a relational DB.
- Given your Kafka, CDC, and outbox production background, spend proportionally *more* time in Phases 1 and 2, which are the parts you likely haven't read at source level, and treat Phase 4's registry as "the outbox you already understand, minus the broker."

## Caveats

- **No event-subsystem changes in Framework 7.0.** Confirmed against the 7.0 release notes, so don't expect new event APIs there. The only 7.0 change that indirectly touches events is the consistent CGLIB proxy defaulting applied to `@Async`, along with a new `@Proxyable` opt-out. Boot 4.1's `@Async` context propagation is opt-in (`spring.task.execution.propagate-context`), and its coverage of async `@EventListener` dispatch is unconfirmed in primary sources.
- **Modulith native externalization is deliberately simple.** The 2.1 reference docs themselves steer advanced needs elsewhere: "If advanced outbox features are required, the event externalization can be delegated to the Namastack Outbox." An earlier characterization that the native path "lacks critical features developers might expect from actual outbox implementations" is a paraphrase and was not found verbatim in the current docs, so rely on the Namastack and JobRunr guidance instead.
- **Ordering is not guaranteed** with registry resubmission, so use Debezium CDC when it matters. There are also open and known issues around completion marking on failed Kafka sends, which you should verify on your exact Modulith version.
- **Version targeting of resources.** Most Baeldung, Medium, and Korean posts target Spring Boot 2.x or 3.x and Framework 5.x or 6.x. The concepts hold, but check annotations and APIs against the Framework 7 and Boot 4 Javadoc before copying code. Oliver Drotbohm's *Modulithic Applications with Spring* was announced for 2026, but treat it as not yet shipped until you confirm availability.
- **Secondary-source caution.** DZone, Medium, and InfoQ items are used here for corroboration and dates. For anything you'll rely on in production, prefer the Spring reference docs, the Javadoc, and the GitHub source cited throughout.
