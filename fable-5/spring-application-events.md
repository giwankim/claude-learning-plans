---
title: "Spring Framework Application Events: A Rigorous Guide for Event-Driven Backends"
category: "Spring & Spring Boot"
description: "A rigorous guide to Spring's application-event subsystem as a synchronous, in-process, same-thread, same-transaction pub/sub bus. It explains why @TransactionalEventListener(AFTER_COMMIT) fires from afterCompletion (so DB writes need REQUIRES_NEW), why events published outside a transaction are silently dropped without fallbackExecution=true, why bridging in-process events to Kafka in AFTER_COMMIT is the classic at-most-once dual-write failure, and how the transactional outbox (hand-rolled with Debezium CDC, or Spring Modulith's Event Publication Registry with @Externalized) delivers at-least-once with resubmission. It draws the line between in-process events for module decoupling inside one deployable and Kafka for cross-service durable streams."
---

# Spring Framework Application Events: A Rigorous Guide for Event-Driven Backends

## TL;DR
- Spring's application-event subsystem is a synchronous, in-process, same-thread, same-transaction publish/subscribe bus by default. `@TransactionalEventListener(AFTER_COMMIT)` defers a listener until commit but is fired from `TransactionSynchronization.afterCompletion(int)` rather than `afterCommit()`, which is why DB writes in an AFTER_COMMIT listener need `Propagation.REQUIRES_NEW` to actually persist, and why events published outside a transaction are silently dropped unless `fallbackExecution=true`.
- For durability, replay, and crash-safety, do not rely on in-process events bridged to Kafka in AFTER_COMMIT, which is the classic at-most-once dual-write failure. Use a transactional outbox: either hand-rolled with Debezium CDC, or Spring Modulith's Event Publication Registry (the `event_publication` table) with `@Externalized` and `@ApplicationModuleListener`, which gives at-least-once with resubmission.
- Use in-process Spring events to decouple modules inside a single deployable (a modular monolith, or Spring Modulith). Use Kafka for cross-service, durable, replayable, high-throughput streams, and bridge selected internal events to Kafka through the outbox rather than publishing directly.

## Key Findings
1. Since Spring 4.2, events are POJOs, and extending `ApplicationEvent` is legacy. `ApplicationEventPublisher.publishEvent(Object)` wraps a non-`ApplicationEvent` in a `PayloadApplicationEvent`.
2. `@EventListener` runs synchronously in the caller's thread and transaction. `@TransactionalEventListener` binds to a `TransactionPhase` (BEFORE_COMMIT, AFTER_COMMIT by default, AFTER_ROLLBACK, AFTER_COMPLETION).
3. The single biggest correctness trap: in AFTER_COMMIT the original transaction is already committed but resources are still bound, so new data access "participates" in a completed transaction and is never flushed or committed. You must open a new transaction with `REQUIRES_NEW`.
4. Events published without an active transaction and without `fallbackExecution` are discarded, with only a DEBUG log. This is a frequent silent failure in tests and in code paths that forget `@Transactional`.
5. `@Async` combined with `@TransactionalEventListener` moves the listener off the publisher's thread, which loses the thread-bound transaction context. Combine them deliberately and use `REQUIRES_NEW`. Spring Modulith's `@ApplicationModuleListener` bundles `@Async`, `@TransactionalEventListener(AFTER_COMMIT)`, and `@Transactional(REQUIRES_NEW)` correctly.
6. Testing: `@RecordApplicationEvents` and `ApplicationEvents` (Spring Framework 5.3.3+) capture published events. AFTER_COMMIT `@TransactionalEventListener` phases never fire under a test method's default-rollback transaction, so use `TestTransaction.flagForCommit()`/`end()`, `@Commit`, or a `TransactionTemplate`. Async listeners need Awaitility.
7. Spring Modulith gives you a built-in outbox: the Event Publication Registry writes a row per transactional listener into `event_publication` inside the business transaction, marks it complete on listener success, resubmits incomplete ones, and can externalize to Kafka via `@Externalized`.

## Details

### Part 1: practical usage patterns and best practices

**Publishing.** Inject `ApplicationEventPublisher` (the `ApplicationContext` implements it) and call `publishEvent`. Since Spring 4.2 the event can be any object; if it does not extend `ApplicationEvent`, Spring wraps it in a `PayloadApplicationEvent<T>` internally, and a listener declared for `T` still matches. Prefer immutable event types (a Kotlin `data class` or a Java `record`) carrying exactly the data the listener needs, so listeners don't re-query the DB.

```kotlin
@Service
class OrderService(private val events: ApplicationEventPublisher,
                   private val repo: OrderRepository) {
    @Transactional
    fun place(cmd: PlaceOrder): Order {
        val order = repo.save(Order.from(cmd))
        events.publishEvent(OrderCompleted(order.id, order.customerId))
        return order
    }
}
data class OrderCompleted(val orderId: Long, val customerId: Long)
```

**Plain object versus `ApplicationEvent`.** Extending `ApplicationEvent` is only needed on pre-4.2 versions, or when you want the `getTimestamp()` and `getSource()` scaffolding. Modern guidance (Baeldung, and the Spring blog post "Better application events in Spring Framework 4.2") is to use POJOs so domain events aren't coupled to framework types.

**`@EventListener`.** Marks any bean method as a listener, with the event type taken from the method parameter. It is a core annotation processed transparently, with no extra config. Non-void return values are re-published as new events, and arrays and collections publish each element. Async listeners cannot do this and must inject the publisher to emit follow-ups.

**`@TransactionalEventListener` and phases.** The phases are `BEFORE_COMMIT`, `AFTER_COMMIT` (the default), `AFTER_ROLLBACK`, and `AFTER_COMPLETION` (commit or rollback). Semantics per the reference docs: "If no transaction is running, the listener is not invoked at all, since we cannot honor the required semantics. You can, however, override that behavior by setting the fallbackExecution attribute of the annotation to true."

**Pitfalls with `@TransactionalEventListener`:**
- *Silent drop with no active transaction.* If publishing happens outside a transaction and `fallbackExecution=false`, the event is discarded with only a DEBUG log (`"No transaction is active - skipping <event>"`). This is very common in unit tests without a transaction, and in service methods missing `@Transactional`.
- *Writes in AFTER_COMMIT lost without `REQUIRES_NEW`.* The reference docs warn: "if the TransactionPhase is set to AFTER_COMMIT (the default), AFTER_ROLLBACK, or AFTER_COMPLETION, the transaction will have been committed or rolled back already, but the transactional resources might still be active and accessible. As a consequence, any data access code triggered at this point will still 'participate' in the original transaction, but changes will not be committed." Andrei Roșca's "Spring puzzler" walkthrough shows that Hibernate inserts issued in an AFTER_COMMIT listener are silently lost, because the flush happens at a commit that already passed: the listener finds thread-local data of the already-committed transaction and joins it, so nothing is flushed. The fix is to annotate the listener, or the collaborator it calls, with `@Transactional(propagation = REQUIRES_NEW)`.
- *`fallbackExecution` semantics.* It enables running the listener when there is no transaction, and for AFTER_ROLLBACK it logs a WARN. Use it for code paths that may or may not run transactionally.

**Async event handling.** Add `@Async` (with `@EnableAsync`) to a listener, or set a task executor on the multicaster globally. Spring binds transactions to the thread, so an async listener runs on another thread and cannot see the publisher's transaction. Do not rely on lazy-loaded entities or on the original transaction's rollback. If the async listener needs a transaction, it gets a fresh one. Bartłomiej Słota's article notes that async listeners get a new transaction anyway, so the autonomous-transaction concerns of the sync case disappear.

**Ordering.** Add `@Order` to fix the invocation order among listeners of the same event, where a lower value means higher priority.

**Conditional listening (SpEL).** `@EventListener(condition = "#event.success")` or `"#creationEvent.awesome"` evaluates a boolean SpEL expression against the event. The root variables are the event and its properties, and `#root` plus bean references such as `@beanName.method()` have been supported since 4.3.

**Generics and `ResolvableType`.** A listener for `EntityCreatedEvent<Order>` matches only that parameterization. Because of type erasure, either publish a concrete subclass (`class OrderCreatedEvent extends EntityCreatedEvent<Order>`) or have the event implement `ResolvableTypeProvider`:
```java
class GenericEvent<T> implements ResolvableTypeProvider {
    public ResolvableType getResolvableType() {
        return ResolvableType.forClassWithGenerics(getClass(), ResolvableType.forInstance(payload));
    }
}
```

**Error handling.** For synchronous listeners, an exception propagates to the publisher and, for an `@EventListener` inside the publisher's transaction, rolls it back; checked exceptions are wrapped in `UndeclaredThrowableException`. You can register an `ErrorHandler` on `SimpleApplicationEventMulticaster` (`setErrorHandler`, for instance `TaskUtils.LOG_AND_PROPAGATE_ERROR_HANDLER`) to intercept listener exceptions. For async listeners, exceptions are not propagated to the caller: a void `@Async` method routes uncaught exceptions to an `AsyncUncaughtExceptionHandler`, configured via `AsyncConfigurer`.

**Events versus direct method calls.** Use a direct call when the caller asserts the callee must run and cares about the result or consistency. Use events when you want to announce a fact and stay agnostic about who reacts, which is ideal for decoupling bounded contexts inside a modular monolith, passing work to another thread, and TDD. This is precisely Spring Modulith's model: modules communicate through application events instead of bean references, which breaks cyclic dependencies while keeping synchronous transactional semantics.

### Part 2: internals and mechanics

**Publisher to multicaster.** `ApplicationContext` delegates publication to an `ApplicationEventMulticaster`, and the default bean is `SimpleApplicationEventMulticaster` (bean name `applicationEventMulticaster`). `publishEvent` validates the event, wraps non-events in `PayloadApplicationEvent`, resolves the event type as a `ResolvableType`, and calls `multicastEvent(event, type)`. `SimpleApplicationEventMulticaster` "Multicasts all events to all registered listeners... By default, all listeners are invoked in the calling thread. This allows the danger of a rogue listener blocking the entire application, but adds minimal overhead."

**Async multicasting config.** Set an `Executor` via `SimpleApplicationEventMulticaster.setTaskExecutor(...)`; note that "asynchronous execution will not participate in the caller's thread context (class loader, transaction context) unless the TaskExecutor explicitly supports this." Listeners declaring no async support (`supportsAsyncExecution()` returning false), notably the transaction-synchronized `TransactionalApplicationListener`, always run in the original publishing thread. Redefining the `applicationEventMulticaster` bean with a `SimpleAsyncTaskExecutor` makes all events async globally, so prefer `@Async` on specific listeners for selectivity.

**Listener discovery.** `EventListenerMethodProcessor` (both a `SmartInitializingSingleton` and a `BeanFactoryPostProcessor`) runs at the end of singleton pre-instantiation (`afterSingletonsInstantiated()`), scans every bean for `@EventListener` methods, and delegates each to an ordered list of `EventListenerFactory` beans. The first factory whose `supportsMethod` matches creates an `ApplicationListener`; `DefaultEventListenerFactory`, which has the lowest precedence, produces an `ApplicationListenerMethodAdapter`, a `GenericApplicationListener` that delegates to the annotated method and resolves event type, condition, and order. The listener is then registered with the context and multicaster.

**Transaction hook (source-level).** `@TransactionalEventListener` is handled by `TransactionalEventListenerFactory`, introduced in Spring 4.2 by Stéphane Nicoll. Its `supportsMethod` returns true when a method is meta-annotated with `@TransactionalEventListener`, and `createApplicationListener` returns a `TransactionalApplicationListenerMethodAdapter` implementing `TransactionalApplicationListener`. The factory is registered by `ProxyTransactionManagementConfiguration` under bean name `org.springframework.transaction.config.internalTransactionalEventListenerFactory` (the constant `TransactionManagementConfigUtils.TRANSACTIONAL_EVENT_LISTENER_FACTORY_BEAN_NAME`), activated by `@EnableTransactionManagement`, which Spring Boot auto-configures when a data-access technology is present. One important nuance: if transaction management is not active, this factory is absent and `@TransactionalEventListener` degrades to a plain immediate listener. Spring 6.2 added `RestrictedTransactionalEventListenerFactory` to make that failure explicit.

When the adapter's `onApplicationEvent` runs, it checks `TransactionSynchronizationManager.isSynchronizationActive() && isActualTransactionActive()`. If true, it registers a `TransactionSynchronization` (the package-private `TransactionalApplicationListenerSynchronization`) via `TransactionSynchronizationManager.registerSynchronization(...)`, and the real user method runs later via `processEvent()`. If false and `fallbackExecution` is true, it calls `processEvent(event)` immediately; otherwise it logs `"No transaction is active - skipping <event>"` at DEBUG and does nothing. The phase-to-callback mapping:
- `BEFORE_COMMIT` → `TransactionSynchronization.beforeCommit(boolean)`
- `AFTER_COMMIT` → `afterCompletion(STATUS_COMMITTED)`, not `afterCommit()`
- `AFTER_ROLLBACK` → `afterCompletion(STATUS_ROLLED_BACK)`
- `AFTER_COMPLETION` → `afterCompletion(any status)`

The `TransactionPhase.AFTER_COMMIT` Javadoc states it "executes in the same sequence of events as AFTER_COMPLETION (and not in TransactionSynchronization.afterCommit())... Interactions with the underlying transactional resource will not be committed in this phase." Reactive support was added in 6.1, via the Reactor context and `TransactionalEventPublisher`, since thread-locals don't apply to `ReactiveTransactionManager`.

**Built-in framework events.** `ContextRefreshedEvent`, `ContextStartedEvent`, `ContextStoppedEvent`, and `ContextClosedEvent` are raised by `ApplicationContext`. `ServletRequestHandledEvent` fires per request in Spring MVC, and `WebServerInitializedEvent` covers `ServletWebServerInitializedEvent` and `ReactiveWebServerInitializedEvent`.

**Spring Boot startup event ordering** (from the `SpringApplication` docs): `ApplicationStartingEvent` → `ApplicationEnvironmentPreparedEvent` → `ApplicationContextInitializedEvent` → `ApplicationPreparedEvent` → context refresh, which raises `ContextRefreshedEvent` → `ApplicationStartedEvent` → `AvailabilityChangeEvent(LivenessState.CORRECT)` → runners → `ApplicationReadyEvent` → `AvailabilityChangeEvent(ReadinessState.ACCEPTING_TRAFFIC)`, with `ApplicationFailedEvent` on a startup exception. `ApplicationStartedEvent` fires after refresh but before `CommandLineRunner` and `ApplicationRunner`, and `ApplicationReadyEvent` fires after them. Note that `ContextRefreshedEvent` comes from Spring core and does not extend `SpringApplicationEvent`.

### Part 3: testing event-driven code

**`@RecordApplicationEvents` and `ApplicationEvents`.** Per the Spring Framework reference section "Application Events": "Since Spring Framework 5.3.3, the TestContext framework provides support for recording application events..." The `RecordApplicationEvents` Javadoc records "Since: 5.3.3, Author: Sam Brannen" (Spring Boot 2.4.2+, per rieckpil). Annotate the test class, inject `ApplicationEvents` as a field or method param via `SpringExtension`, and query with `events.stream(OrderSubmitted.class).count()`. It requires a `TestContext`, specifically the `ApplicationEventsTestExecutionListener`, which is registered by default. rieckpil cautions that this is behavior testing: prefer asserting outcomes and state to keep refactors cheap, since verifying "an event was published" over-specifies the implementation.

```kotlin
@SpringBootTest
@RecordApplicationEvents
class UserServiceTest(@Autowired val userService: UserService,
                      @Autowired val events: ApplicationEvents) {
    @Test fun publishesEvent() {
        userService.register("a@b.com")
        assertThat(events.stream(UserRegisteredEvent::class.java).count()).isEqualTo(1)
    }
}
```

**Testing `@TransactionalEventListener`.** A `@Transactional` test method rolls back by default, so AFTER_COMMIT listeners never fire. The options: (a) `TestTransaction.flagForCommit(); TestTransaction.end();` to force a commit mid-test, available whenever `TransactionalTestExecutionListener` is enabled; (b) `@Commit` on the method, which starts it flagged for commit; (c) do the publish inside a `TransactionTemplate` or `TransactionOperations` so the phase callbacks fire deterministically; (d) don't make the test transactional, and manage the transaction explicitly. `TestTransaction.flagForCommit()` and `flagForRollback()` merely set the flag, and the commit or rollback occurs at `end()` or method exit.

**Testing async listeners.** Use Awaitility to poll for the state change or captured event (`await().atMost(...).until(() -> ...)`), since the listener runs on another thread.

**Mock versus integration.** In a unit test, mock `ApplicationEventPublisher` and assert `publishEvent` was called with the right event. That's fast, but it couples the test to the "we publish" implementation detail. In an integration test, wire publisher and listener together and assert the observable outcome, which is best for verifying the use case. Choose based on whether the event is an internal detail or a contract.

**Spring Modulith test support.** `@ApplicationModuleTest` bootstraps only the module's packages and can inject `PublishedEvents` or `AssertablePublishedEvents`:
```java
@ApplicationModuleTest
class OrderIntegrationTests {
  @Test void publishesCompletion(PublishedEvents events) {
    // ...
    assertThat(events.ofType(OrderCompleted.class)
                     .matching(OrderCompleted::getOrderId, ref.getId())).hasSize(1);
  }
}
```
The `Scenario` DSL (`scenario.publish(...).andWaitForStateChange(...).andVerify(...)` and `.andWaitForEventOfType(...).toArriveAndVerify(...)`) drives event and bean stimuli inside a transaction and uses Awaitility under the hood. The Modulith team recommends `Scenario` over raw `AssertablePublishedEvents` for cascading async events. Per the Spring Modulith 2.1 GA notes (2026-06-11), "Open up PublishedEvents and Scenario to see events from all threads by default #1564", where previously they were thread-bound, as documented in the 2.1 M2 release of 2026-02-19.

### Part 4: relationship to the transactional outbox pattern

**The dual-write problem.** Saving to the DB and publishing to Kafka are two systems with no shared transaction. A `@TransactionalEventListener(AFTER_COMMIT)` that calls `kafkaTemplate.send(...)` is at-most-once: if the app crashes, or Kafka is down, after the DB commit but around the send, the event is lost. The DB has the order and downstream never hears about it. Publishing in BEFORE_COMMIT or in a plain `@EventListener` is the opposite failure, since the message can go out and then the transaction rolls back, so consumers see a phantom event.

**BEFORE_COMMIT outbox write.** A robust hand-rolled outbox writes the message row inside the same transaction, so it's atomic with the business data, and then a relay ships it. `@TransactionalEventListener(phase = BEFORE_COMMIT)` is a natural place to insert the outbox row, because it runs in the still-open transaction, so the outbox INSERT commits atomically with the aggregate. A separate relay then publishes to Kafka and marks or removes the row.

**Relay: polling versus CDC.** A polling publisher runs `SELECT ... WHERE published=false ... FOR UPDATE SKIP LOCKED` on an interval, which is simple and DB-agnostic but adds latency and continuous DB load. CDC (Debezium) tails the transaction log (a MySQL binlog or Postgres WAL) and streams outbox inserts to Kafka with near-real-time latency, low OLTP impact, and commit-order guarantees, at the cost of operating Kafka Connect and Debezium and managing WAL or binlog retention. Both are at-least-once, so consumers must be idempotent. The pragmatic rule, per multiple practitioner writeups: polling for simple stacks and moderate volume, CDC when latency is tight and you already run Kafka. For Aurora MySQL specifically, Debezium consumes the binlog.

**Spring Modulith's Event Publication Registry (a built-in outbox equivalent).** On publication, the registry "finds out about the transactional event listeners that will get the event delivered and writes entries for each of them into an event publication log as part of the original business transaction." Each transactional listener is wrapped in an aspect that marks its `event_publication` row complete on success; on failure the row stays incomplete for later resubmission (`IncompleteEventPublications`, `resubmitIncompletePublications`, and `spring.modulith.events.republish-outstanding-events-on-restart=true` to retry at startup). It persists via an `EventPublicationRepository` SPI, with JPA, JDBC, MongoDB, and Neo4j implementations. Completion modes since 1.3 are `UPDATE` (the default, which sets a completion date and needs purging), `DELETE`, and `ARCHIVE`. `@ApplicationModuleListener` combines `@Async`, `@TransactionalEventListener(AFTER_COMMIT)`, and `@Transactional(REQUIRES_NEW)`, and it is the recommended, correctly-configured integration listener.

**Externalizing to Kafka with `@Externalized`.** Annotate the event: `@Externalized("orders.OrderCompleted::#{customerId()}")`, where the value before `::` is the routing target (the Kafka topic) and the SpEL after `::` produces the routing key for partitioning. Add `spring-modulith-events-api` and `spring-modulith-events-kafka`, and a transactional listener marshals and sends. Because externalization is itself a transactional listener guarded by the registry, a failed Kafka send leaves the publication incomplete and resubmittable, which gives at-least-once end to end. One historical caveat: spring-modulith issue #395, "the entry in the registration for externalize listener is marked completed even when the message fails to be produced to Kafka," was resolved by Oliver Drotbohm, and per Axual's blog, "The fix will be available in the upcoming 1.1.1 release." Spring Modulith 2.1 GA, released June 11, 2026 per spring.io, adds "Support for an event externalization outbox with Namastack and JobRunr" (GH-1517, GH-1637), an alternative to the built-in asynchronous listener-based externalization that supports multi-instance, order-preserving publication. It is activated via the `spring-modulith-starter-namastack` artifact, and Drotbohm credits Roland Beisel and Ronald Dehuysser for the contribution.

**Hand-rolled with Debezium versus Modulith.** A Debezium CDC outbox is language- and framework-agnostic, has the lowest OLTP impact, and gives the best throughput and ordering, but it carries the heaviest infrastructure and DBA involvement (binlog and WAL retention, Kafka Connect). The Modulith registry needs no extra infrastructure beyond your DB, is transactionally correct by design, works well for a modular monolith, and integrates with Micrometer. Its downsides: it tracks both `@TransactionalEventListener` and `@ApplicationModuleListener`, which makes incremental migration hard; retries can run concurrently, so ordering is not guaranteed; and multi-instance `@Scheduled` resubmission needs a lock (ShedLock) unless you use the 2.1 outbox integration. Korean engineering writeups, such as 29CM's on Medium, chose a hand-rolled outbox with `@TransactionalEventListener` over Debezium mainly for operational readiness rather than because CDC is technically inferior.

### Part 5: in-process events versus Kafka

| Dimension | In-process Spring events (plus Modulith) | Kafka |
|---|---|---|
| Scope | Within one deployable / modular monolith | Cross-service, cross-language |
| Coupling | Decouples modules; no infra beyond DB | Decouples services; broker infra |
| Durability | Transient (plain events) / DB-backed (Modulith registry) | Durable, replicated, disk-persisted |
| Replay | None (plain); resubmission (Modulith) | Full replay from retained offsets |
| Latency | In-JVM, no network hop | Network hop; high throughput |
| Transactions | Same DB transaction (sync) / outbox (Modulith) | Needs outbox/idempotency for atomicity |
| Ordering | Deterministic (sync) | Per-partition |
| Observability | Micrometer plus custom | Mature tooling (lag, dashboards) |

Plain Spring events are in-memory and transient, so on their own they are unsuitable where reliability and replay matter. The recommended pattern: use Spring events internally to keep modules loosely coupled and testable, and bridge only the selected events other services need onto Kafka, through the outbox (Modulith `@Externalized` or Debezium) rather than a direct AFTER_COMMIT send. This is also the cleanest microservice-extraction path: when a module graduates to a service, you swap `ApplicationEventPublisher` for a Kafka producer while the consumer side, already using `@ApplicationModuleListener` semantics, barely changes.

## Recommendations
1. Default to POJO events with `@TransactionalEventListener`. For same-transaction side effects use a plain `@EventListener`; for post-commit side effects use `@TransactionalEventListener` (AFTER_COMMIT). Always ask whether this runs inside a transaction, because if it doesn't, the listener silently won't fire.
2. Whenever an AFTER_COMMIT or AFTER_COMPLETION listener writes to the DB, add `@Transactional(propagation = REQUIRES_NEW)` on the listener or its collaborator, or the writes vanish.
3. Never bridge to Kafka with a bare AFTER_COMMIT `kafkaTemplate.send`. Use an outbox. In a modular monolith on Aurora MySQL and Kafka, adopt Spring Modulith's Event Publication Registry (`spring-modulith-starter-jdbc` or `-jpa`) with `@ApplicationModuleListener` for internal handling and `@Externalized` for the events other services consume. If you need the lowest latency, the highest throughput, or strict ordering, and you can operate Kafka Connect, use Debezium CDC on the binlog against a dedicated outbox table.
4. Make all consumers idempotent by deduplicating on event ID, since every outbox variant is at-least-once.
5. Testing: unit-test listeners directly for logic; use `@RecordApplicationEvents` sparingly for "was it published"; for `@TransactionalEventListener` use `TestTransaction.flagForCommit()` or `@Commit` or a `TransactionTemplate`; for async use Awaitility or Modulith's `Scenario`. Prefer state assertions over event-count assertions.
6. Ordering and async: use `@Order` for deterministic sync ordering, and adopt `@ApplicationModuleListener` rather than hand-wiring `@Async` with `@TransactionalEventListener`, so `REQUIRES_NEW` is applied correctly.
7. Purge and monitor the `event_publication` table (choose the `DELETE` or `ARCHIVE` completion mode, or a scheduled purge), and if you run multiple instances, guard `@Scheduled` resubmission with ShedLock, or move to Modulith 2.1's outbox externalization.

**Thresholds that change the recommendation:** move from the Modulith registry to Debezium CDC when event latency requirements drop below roughly 100ms, when throughput saturates the DB, or when you need strict cross-table ordering. Keep polling and the registry when volume is moderate and infrastructure simplicity matters. Split a module into a microservice, and rely fully on Kafka, when it needs independent scaling or deployment, and not before.

## Caveats
- Version drift: `@RecordApplicationEvents` requires Spring Framework 5.3.3 or later, reactive `@TransactionalEventListener` requires 6.1 or later, and `RestrictedTransactionalEventListenerFactory` is 6.2. Spring Modulith 2.0 GA (released Nov 21, 2025, per spring.io's "Spring Modulith 2.0 GA, 1.4.5, and 1.3.11 released") rebuilt the registry ("Overhaul event publication lifecycle #796") and is built on Spring Boot 4 and Framework 7, while Modulith 1.4.x pairs with Boot 3.5.x. Verify your matrix.
- Several cited posts are secondary (Medium, DEV) and, for CDC "99.999%"-style claims, marketing-tinged. Treat vendor numbers skeptically, including Namastack's advertised partition and throughput figures. The primary correctness claims here are anchored to Spring reference docs, Javadoc, and Spring source.
- Modulith's registry currently tracks both `@TransactionalEventListener` and `@ApplicationModuleListener`, so adding it to an event-heavy app persists publications for all such listeners at once. Plan a big-bang migration rather than an incremental one.
- The exact `onApplicationEvent` gating code described here is from 5.2/5.3-era source; current `main` refactored it into `TransactionalApplicationListenerSynchronization.register(...)`. The semantics are unchanged, but individual method bodies were not read verbatim from current source.

## Curated Resource List

**Official documentation**
- Spring Framework Reference, "Transaction-bound Events" (phases, `fallbackExecution`, the reactive note). A concise primary source.
- Spring Framework Reference, "Application Events" under TestContext (`@RecordApplicationEvents`, the `ApplicationEvents` API). Primary.
- Spring Framework Reference, "Transaction Management" testing (`TestTransaction`, `@Commit`/`@Rollback`, `@BeforeTransaction`). Primary.
- Javadoc: `TransactionalEventListener`, `TransactionPhase`, `TransactionalApplicationListener(MethodAdapter)`, `SimpleApplicationEventMulticaster`, `EventListenerMethodProcessor`, `ApplicationListenerMethodAdapter`, `AsyncUncaughtExceptionHandler`. The source of truth for exact semantics.
- Spring Modulith Reference, "Working with Application Events" and "Integration Testing Application Modules" (the Event Publication Registry, `@ApplicationModuleListener`, `@Externalized`, completion modes, `Scenario` and `PublishedEvents`). Primary.
- Spring Boot Reference, "SpringApplication" (startup event order, availability events). Primary.

**Blog posts**
- Spring Blog, "Better application events in Spring Framework 4.2" (Stéphane Nicoll): the design rationale for POJO events, `@EventListener`, and `@TransactionalEventListener`. Authoritative and foundational.
- Spring Blog, "Simplified Event Externalization with Spring Modulith" (Oliver Drotbohm, 2023-09-22): outbox and externalization design straight from the project lead. Authoritative.
- Baeldung: "Spring Events", "How to Test Spring Application Events", "Event Externalization with Spring Modulith", "Programmatic Transactions in the TestContext Framework". Broad, example-rich, intermediate.
- Reflectoring, "Spring Boot Application Events Explained": events versus method calls, and built-in events. Clear and intermediate.
- rieckpil, "Record Spring Events When Testing Spring Boot Applications": `@RecordApplicationEvents` with testing-philosophy caveats. Practical.
- Andrei Roșca (softice.dev), "Spring puzzler: the @TransactionalEventListener": a source-level walkthrough of why AFTER_COMMIT DB writes are lost. Deep and rigorous.
- Bartłomiej Słota (bartslota.com), with a DZone mirror, "Transaction synchronization and Spring application events": phases, autonomous transactions, `REQUIRES_NEW`. Deep.
- Wim Deblauwe, "Transactional Outbox pattern with Spring Boot": Spring Integration versus Spring Modulith outbox, plus ordering and multi-instance caveats (ShedLock). Practical, senior-level.
- Axual, "Outbox Pattern with Apache Kafka" (Spring Modulith): an end-to-end Order and Notification example that documents the #395 bug. Practical.
- 29CM engineering (Medium, Korean), "트랜잭셔널 아웃박스 패턴의 실제 구현 사례": the production rationale for a hand-rolled outbox with `@TransactionalEventListener` over Debezium. A case study.
- cheese10yun (GitHub blog, Korean), "ApplicationEventPublisher 이벤트 기반 트랜잭션 처리": `@EventListener` versus `@TransactionalEventListener`, with SQS and RabbitMQ notes. Practical.

**Books**
- *Cloud Native Spring in Action* (Thomas Vitale, Manning), Ch. 10 "Event-driven applications and functions" (Spring Cloud Stream plus a broker). Intermediate, with cloud-native framing.
- *Modulithic Applications with Spring* (Oliver Drotbohm, Leanpub, in progress), the definitive Modulith treatment by the project lead.
- *Microservices Patterns* (Chris Richardson), the canonical transactional outbox, CDC, and saga reference, though not Spring-specific.
- *Spring in Action* and *Spring Start Here* (Craig Walls, Manning), for general Spring events coverage. Introductory.

**Talks and videos**
- Oliver Drotbohm, "A Deep Dive into Spring Application Events" (SpeakerDeck): the internals of the event subsystem. Advanced.
- Oliver Drotbohm, "Spring Modulith: A Deep Dive" (a SpringOne and Devoxx workshop, slides on SpeakerDeck): modules, events, the Event Publication Registry, externalization. Advanced.
- Oliver Drotbohm, "Spring Modulith: Spring for the Architecturally Curious Developer" (Devoxx, on YouTube via Class Central) and "What's new in Spring Modulith?". Intermediate to advanced.
- A Bootiful Podcast, "Oliver Drotbohm on Spring Modulith 2.0" (spring.io, Aug 2025): the roadmap and registry revamp.

**Courses**
- Spring Academy (spring.io / Broadcom) has the official Spring courses, and the transactions and testing modules touch these APIs. There is no single dedicated "application events" course of note; the reference docs plus the Drotbohm talks are the higher-signal path for this specific topic.
