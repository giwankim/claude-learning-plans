---
title: "Spring Framework Application Events: A Rigorous Guide for Event-Driven Backends"
category: "Spring & Spring Boot"
description: "A rigorous guide to Spring's application-event subsystem as a synchronous, in-process, same-thread, same-transaction pub/sub bus: why @TransactionalEventListener(AFTER_COMMIT) fires from afterCompletion (so DB writes need REQUIRES_NEW), why events published outside a transaction are silently dropped without fallbackExecution=true, why bridging in-process events to Kafka in AFTER_COMMIT is the classic at-most-once dual-write failure, and how the transactional outbox (hand-rolled + Debezium CDC, or Spring Modulith's Event Publication Registry with @Externalized) delivers at-least-once with resubmission. Draws the line between in-process events for module decoupling inside one deployable and Kafka for cross-service durable streams."
---

# Spring Framework Application Events: A Rigorous Guide for Event-Driven Backends

## TL;DR
- Spring's application-event subsystem is a **synchronous, in-process, same-thread, same-transaction** publish/subscribe bus by default; `@TransactionalEventListener(AFTER_COMMIT)` defers a listener until commit but is fired from `TransactionSynchronization.afterCompletion(int)` — **not** `afterCommit()` — which is why DB writes in an AFTER_COMMIT listener need `Propagation.REQUIRES_NEW` to actually persist, and why events published outside a transaction are **silently dropped** unless `fallbackExecution=true`.
- For durability, replay, and crash-safety you must **not** rely on in-process events bridged to Kafka in AFTER_COMMIT (that is the classic at-most-once dual-write failure); use a transactional outbox — hand-rolled + Debezium CDC, or Spring Modulith's Event Publication Registry (`event_publication` table) with `@Externalized` and `@ApplicationModuleListener`, which gives at-least-once with resubmission.
- Use in-process Spring events to decouple modules inside a single deployable (modular monolith / Spring Modulith); use Kafka for cross-service, durable, replayable, high-throughput streams — and bridge selected internal events to Kafka **through the outbox** rather than publishing directly.

## Key Findings
1. Since Spring 4.2 events are POJOs; extending `ApplicationEvent` is legacy. `ApplicationEventPublisher.publishEvent(Object)` wraps a non-`ApplicationEvent` in a `PayloadApplicationEvent`.
2. `@EventListener` runs synchronously in the caller's thread and transaction; `@TransactionalEventListener` binds to a `TransactionPhase` (BEFORE_COMMIT, AFTER_COMMIT default, AFTER_ROLLBACK, AFTER_COMPLETION).
3. The single biggest correctness trap: in AFTER_COMMIT the original transaction is already committed but resources are still bound; new data-access "participates" in a completed transaction and is never flushed/committed — you must open a new transaction with `REQUIRES_NEW`.
4. Events published without an active transaction and no `fallbackExecution` are discarded (only a DEBUG log). This is a frequent silent-failure in tests and in code paths that forget `@Transactional`.
5. `@Async` + `@TransactionalEventListener` moves the listener off the publisher's thread, losing the thread-bound transaction context; combine deliberately and use `REQUIRES_NEW`. Spring Modulith's `@ApplicationModuleListener` bundles `@Async` + `@TransactionalEventListener(AFTER_COMMIT)` + `@Transactional(REQUIRES_NEW)` correctly.
6. Testing: `@RecordApplicationEvents` + `ApplicationEvents` (Spring Framework 5.3.3+) captures published events; `@TransactionalEventListener` AFTER_COMMIT phases never fire under a test method's default-rollback transaction — use `TestTransaction.flagForCommit()/end()`, `@Commit`, or a `TransactionTemplate`; async listeners need Awaitility.
7. Spring Modulith gives a built-in outbox: the Event Publication Registry writes a row per transactional listener into `event_publication` inside the business transaction, marks it complete on listener success, resubmits incomplete ones, and can externalize to Kafka via `@Externalized`.

## Details

### PART 1 — Practical Usage Patterns and Best Practices

**Publishing.** Inject `ApplicationEventPublisher` (the `ApplicationContext` implements it) and call `publishEvent`. Since Spring 4.2 the event can be any object; if it does not extend `ApplicationEvent`, Spring wraps it in a `PayloadApplicationEvent<T>` internally, and a listener declared for `T` still matches. Prefer immutable event types (Kotlin `data class` / Java `record`) carrying exactly the data the listener needs, so listeners don't re-query the DB.

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

**Plain object vs `ApplicationEvent`.** Extending `ApplicationEvent` is only needed on pre-4.2 or when you want the `getTimestamp()`/`getSource()` scaffolding. Modern guidance (Baeldung; Spring blog "Better application events in Spring Framework 4.2") is to use POJOs to avoid coupling domain events to framework types.

**`@EventListener`.** Marks any bean method as a listener; the event type is the method parameter. It is a core annotation processed transparently — no extra config. Non-void return values are re-published as new events (arrays/collections publish each element); async listeners cannot do this and must inject the publisher to emit follow-ups.

**`@TransactionalEventListener` and phases.** `BEFORE_COMMIT`, `AFTER_COMMIT` (default), `AFTER_ROLLBACK`, `AFTER_COMPLETION` (commit or rollback). Semantics per the reference docs: "If no transaction is running, the listener is not invoked at all, since we cannot honor the required semantics. You can, however, override that behavior by setting the fallbackExecution attribute of the annotation to true."

**Pitfalls with `@TransactionalEventListener`:**
- *Silent drop with no active transaction.* If publishing happens outside a transaction and `fallbackExecution=false`, the event is discarded with only a DEBUG log (`"No transaction is active - skipping <event>"`). Very common in unit tests without a transaction and in service methods missing `@Transactional`.
- *Writes in AFTER_COMMIT lost without `REQUIRES_NEW`.* The reference docs warn: "if the TransactionPhase is set to AFTER_COMMIT (the default), AFTER_ROLLBACK, or AFTER_COMPLETION, the transaction will have been committed or rolled back already, but the transactional resources might still be active and accessible. As a consequence, any data access code triggered at this point will still 'participate' in the original transaction, but changes will not be committed." Andrei Roșca's "Spring puzzler" walkthrough shows Hibernate inserts issued in an AFTER_COMMIT listener are silently lost because the flush happens at a commit that already passed — the listener finds thread-local data of the *already-committed* transaction and "joins" it, so nothing is flushed. Fix: annotate the listener (or the collaborator it calls) with `@Transactional(propagation = REQUIRES_NEW)`.
- *`fallbackExecution` semantics.* Enables running the listener when there is no transaction; for AFTER_ROLLBACK it logs a WARN. Use it for code paths that may or may not run transactionally.

**Async event handling.** Add `@Async` (with `@EnableAsync`) to a listener, or set a task executor on the multicaster (global). Spring binds transactions to the thread; an async listener runs on another thread and cannot see the publisher's transaction — do not rely on lazy-loaded entities or the original transaction's rollback. If the async listener needs a transaction, it gets a fresh one. Bartłomiej Słota's article notes async listeners get a new transaction anyway, so the autonomous-transaction concerns of the sync case disappear.

**Ordering.** Add `@Order` to fix invocation order among listeners of the same event (lower value = higher priority).

**Conditional listening (SpEL).** `@EventListener(condition = "#event.success")` / `"#creationEvent.awesome"` evaluate a boolean SpEL expression against the event (root variables are the event and its properties; `#root`, bean references `@beanName.method()` supported since 4.3).

**Generics and `ResolvableType`.** A listener for `EntityCreatedEvent<Order>` matches only that parameterization. Because of type erasure, either publish a concrete subclass (`class OrderCreatedEvent extends EntityCreatedEvent<Order>`) or have the event implement `ResolvableTypeProvider`:
```java
class GenericEvent<T> implements ResolvableTypeProvider {
    public ResolvableType getResolvableType() {
        return ResolvableType.forClassWithGenerics(getClass(), ResolvableType.forInstance(payload));
    }
}
```

**Error handling.** Synchronous listeners: an exception propagates to the publisher and (for `@EventListener` inside the publisher's transaction) rolls it back; checked exceptions are wrapped in `UndeclaredThrowableException`. You can register an `ErrorHandler` on `SimpleApplicationEventMulticaster` (`setErrorHandler`, e.g. `TaskUtils.LOG_AND_PROPAGATE_ERROR_HANDLER`) to intercept listener exceptions. Async listeners: exceptions are **not** propagated to the caller; a void `@Async` method routes uncaught exceptions to an `AsyncUncaughtExceptionHandler` (configured via `AsyncConfigurer`).

**Events vs direct method calls.** Use a direct call when the caller asserts the callee must run and cares about the result/consistency; use events when you want to announce a fact and stay agnostic about who reacts — ideal for decoupling bounded contexts inside a modular monolith, passing work to another thread, and TDD. This is precisely Spring Modulith's model: modules communicate through application events instead of bean references, breaking cyclic dependencies while keeping (synchronous) transactional semantics.

### PART 2 — Internals and Mechanics

**Publisher → multicaster.** `ApplicationContext` delegates publication to an `ApplicationEventMulticaster`; the default bean is `SimpleApplicationEventMulticaster` (bean name `applicationEventMulticaster`). `publishEvent` validates the event, wraps non-events in `PayloadApplicationEvent`, resolves the event type as a `ResolvableType`, and calls `multicastEvent(event, type)`. `SimpleApplicationEventMulticaster` "Multicasts all events to all registered listeners... By default, all listeners are invoked in the calling thread. This allows the danger of a rogue listener blocking the entire application, but adds minimal overhead."

**Async multicasting config.** Set an `Executor` via `SimpleApplicationEventMulticaster.setTaskExecutor(...)`; "asynchronous execution will not participate in the caller's thread context (class loader, transaction context) unless the TaskExecutor explicitly supports this." Listeners declaring no async support (`supportsAsyncExecution()` false) — notably the transaction-synchronized `TransactionalApplicationListener` — always run in the original publishing thread. Redefining the `applicationEventMulticaster` bean with a `SimpleAsyncTaskExecutor` makes **all** events async globally; prefer `@Async` on specific listeners for selectivity.

**Listener discovery.** `EventListenerMethodProcessor` (a `SmartInitializingSingleton` + `BeanFactoryPostProcessor`) runs at the end of singleton pre-instantiation (`afterSingletonsInstantiated()`), scans every bean for `@EventListener` methods, and for each delegates to an ordered list of `EventListenerFactory` beans. The first factory whose `supportsMethod` matches creates an `ApplicationListener`; `DefaultEventListenerFactory` (lowest precedence) produces an `ApplicationListenerMethodAdapter` (a `GenericApplicationListener` that delegates to the annotated method, resolving event type/condition/order). The listener is then registered with the context/multicaster.

**Transaction hook (source-level).** `@TransactionalEventListener` is handled by `TransactionalEventListenerFactory` (introduced in Spring 4.2, author Stéphane Nicoll). Its `supportsMethod` returns true when a method is meta-annotated with `@TransactionalEventListener`, and `createApplicationListener` returns a `TransactionalApplicationListenerMethodAdapter` (implementing `TransactionalApplicationListener`). The factory is registered by `ProxyTransactionManagementConfiguration` under bean name `org.springframework.transaction.config.internalTransactionalEventListenerFactory` (constant `TransactionManagementConfigUtils.TRANSACTIONAL_EVENT_LISTENER_FACTORY_BEAN_NAME`), activated by `@EnableTransactionManagement` (auto-configured by Spring Boot when a data-access technology is present). Important nuance: if transaction management is not active, this factory is absent and `@TransactionalEventListener` degrades to a plain immediate listener; Spring 6.2 added `RestrictedTransactionalEventListenerFactory` to make that failure explicit.

When the adapter's `onApplicationEvent` runs, it checks `TransactionSynchronizationManager.isSynchronizationActive() && isActualTransactionActive()`. If true, it registers a `TransactionSynchronization` (package-private `TransactionalApplicationListenerSynchronization`) via `TransactionSynchronizationManager.registerSynchronization(...)`; the real user method runs later via `processEvent()`. If false and `fallbackExecution` is true, it calls `processEvent(event)` immediately; otherwise it logs `"No transaction is active - skipping <event>"` at DEBUG and does nothing. Phase → callback mapping:
- `BEFORE_COMMIT` → `TransactionSynchronization.beforeCommit(boolean)`
- `AFTER_COMMIT` → `afterCompletion(STATUS_COMMITTED)` (**not** `afterCommit()`)
- `AFTER_ROLLBACK` → `afterCompletion(STATUS_ROLLED_BACK)`
- `AFTER_COMPLETION` → `afterCompletion(any status)`

The `TransactionPhase.AFTER_COMMIT` Javadoc states it "executes in the same sequence of events as AFTER_COMPLETION (and not in TransactionSynchronization.afterCommit())... Interactions with the underlying transactional resource will not be committed in this phase." Reactive support was added in 6.1 (via Reactor context + `TransactionalEventPublisher`), since thread-locals don't apply to `ReactiveTransactionManager`.

**Built-in framework events.** `ContextRefreshedEvent`, `ContextStartedEvent`, `ContextStoppedEvent`, `ContextClosedEvent` (raised by `ApplicationContext`); `ServletRequestHandledEvent` (per-request in Spring MVC); `WebServerInitializedEvent` (`ServletWebServerInitializedEvent` / `ReactiveWebServerInitializedEvent`).

**Spring Boot startup event ordering** (from `SpringApplication` docs): `ApplicationStartingEvent` → `ApplicationEnvironmentPreparedEvent` → `ApplicationContextInitializedEvent` → `ApplicationPreparedEvent` → (context refresh; `ContextRefreshedEvent`) → `ApplicationStartedEvent` → `AvailabilityChangeEvent(LivenessState.CORRECT)` → runners → `ApplicationReadyEvent` → `AvailabilityChangeEvent(ReadinessState.ACCEPTING_TRAFFIC)`; `ApplicationFailedEvent` on startup exception. `ApplicationStartedEvent` fires after refresh but before `CommandLineRunner`/`ApplicationRunner`; `ApplicationReadyEvent` after them. Note `ContextRefreshedEvent` comes from Spring core and does not extend `SpringApplicationEvent`.

### PART 3 — Testing Event-Driven Code

**`@RecordApplicationEvents` / `ApplicationEvents`.** Per the Spring Framework reference "Application Events": "Since Spring Framework 5.3.3, the TestContext framework provides support for recording application events..."; the `RecordApplicationEvents` Javadoc records "Since: 5.3.3, Author: Sam Brannen" (Spring Boot 2.4.2+, per rieckpil). Annotate the test class; inject `ApplicationEvents` (field or method param via `SpringExtension`) and query with `events.stream(OrderSubmitted.class).count()`. Requires a `TestContext` (the `ApplicationEventsTestExecutionListener`, registered by default). rieckpil cautions this is behavior testing — prefer asserting outcomes/state to keep refactors cheap; verifying "an event was published" over-specifies implementation.

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

**Testing `@TransactionalEventListener`.** A `@Transactional` test method rolls back by default, so AFTER_COMMIT listeners never fire. Options: (a) `TestTransaction.flagForCommit(); TestTransaction.end();` to force commit mid-test (available whenever `TransactionalTestExecutionListener` is enabled); (b) `@Commit` on the method (starts flagged-for-commit); (c) do the publish inside a `TransactionTemplate`/`TransactionOperations` so the phase callbacks fire deterministically; (d) don't make the test transactional and manage the transaction explicitly. `TestTransaction.flagForCommit()`/`flagForRollback()` merely set the flag; the commit/rollback occurs at `end()` or method exit.

**Testing async listeners.** Use Awaitility to poll for the state change / captured event (`await().atMost(...).until(() -> ...)`), since the listener runs on another thread.

**Mock vs integration.** Unit test: mock `ApplicationEventPublisher`, assert `publishEvent` was called with the right event (fast, but couples to the "we publish" implementation detail). Integration test: wire publisher + listener and assert the observable outcome (best for verifying the use case). Choose based on whether the event is an internal detail or a contract.

**Spring Modulith test support.** `@ApplicationModuleTest` bootstraps only the module's packages and can inject `PublishedEvents` / `AssertablePublishedEvents`:
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
The `Scenario` DSL (`scenario.publish(...).andWaitForStateChange(...).andVerify(...)` / `.andWaitForEventOfType(...).toArriveAndVerify(...)`) drives event/bean stimuli inside a transaction and uses Awaitility under the hood — the Modulith team recommends `Scenario` over raw `AssertablePublishedEvents` for cascading async events. Per the Spring Modulith 2.1 GA notes (2026-06-11), "Open up PublishedEvents and Scenario to see events from all threads by default #1564" (previously thread-bound, as documented in the 2.1 M2 release, 2026-02-19).

### PART 4 — Relationship to the Transactional Outbox Pattern

**The dual-write problem.** Saving to the DB and publishing to Kafka are two systems with no shared transaction. A `@TransactionalEventListener(AFTER_COMMIT)` that calls `kafkaTemplate.send(...)` is at-most-once: if the app crashes (or Kafka is down) after DB commit but before/around the send, the event is lost — the DB has the order, downstream never hears about it. Publishing BEFORE_COMMIT or in a plain `@EventListener` is the opposite failure: the message can go out and then the transaction rolls back, so consumers see a phantom event.

**BEFORE_COMMIT outbox write.** A robust hand-rolled outbox writes the message row inside the same transaction (so it's atomic with the business data), then a relay ships it. `@TransactionalEventListener(phase = BEFORE_COMMIT)` is a natural place to insert the outbox row: it runs in the still-open transaction, so the outbox INSERT commits atomically with the aggregate. A separate relay then publishes to Kafka and marks/removes the row.

**Relay: polling vs CDC.** A polling publisher runs `SELECT ... WHERE published=false ... FOR UPDATE SKIP LOCKED` on an interval — simple, DB-agnostic, but adds latency and continuous DB load. CDC (Debezium) tails the transaction log (MySQL binlog / Postgres WAL) and streams outbox inserts to Kafka with near-real-time latency, low OLTP impact, and commit-order guarantees — at the cost of operating Kafka Connect + Debezium and managing WAL/binlog retention. Both are at-least-once, so consumers **must** be idempotent. The pragmatic rule (per multiple practitioner writeups): polling for simple stacks / moderate volume; CDC when latency is tight and you already run Kafka. For Aurora MySQL specifically, Debezium consumes the binlog.

**Spring Modulith's Event Publication Registry (built-in outbox-like).** On publication, the registry "finds out about the transactional event listeners that will get the event delivered and writes entries for each of them into an event publication log as part of the original business transaction." Each transactional listener is wrapped in an aspect that marks its `event_publication` row complete on success; on failure the row stays incomplete for later resubmission (`IncompleteEventPublications`, `resubmitIncompletePublications`; `spring.modulith.events.republish-outstanding-events-on-restart=true` to retry at startup). It persists via an `EventPublicationRepository` SPI (JPA, JDBC, MongoDB, Neo4j). Completion modes (1.3+): `UPDATE` (default, sets completion date, needs purging), `DELETE`, `ARCHIVE`. `@ApplicationModuleListener` = `@Async` + `@TransactionalEventListener(AFTER_COMMIT)` + `@Transactional(REQUIRES_NEW)` — the recommended, correctly-configured integration listener.

**Externalizing to Kafka with `@Externalized`.** Annotate the event: `@Externalized("orders.OrderCompleted::#{customerId()}")` — the value before `::` is the routing target (Kafka topic), the SpEL after `::` produces the routing key (partitioning). Add `spring-modulith-events-api` + `spring-modulith-events-kafka`; a transactional listener marshals and sends. Because externalization is itself a transactional listener guarded by the registry, a failed Kafka send leaves the publication incomplete and resubmittable — giving at-least-once end-to-end. (Historical caveat: spring-modulith issue #395 — "the entry in the registration for externalize listener is marked completed even when the message fails to be produced to Kafka" — was resolved by Oliver Drotbohm; per Axual's blog, "The fix will be available in the upcoming 1.1.1 release.") Spring Modulith 2.1 GA (released June 11, 2026, per spring.io) adds "Support for an event externalization outbox with Namastack and JobRunr – GH-1517, GH-1637," an alternative to the built-in asynchronous listener-based externalization supporting multi-instance, order-preserving publication (activated via the `spring-modulith-starter-namastack` artifact; Drotbohm credits Roland Beisel and Ronald Dehuysser for the contribution).

**Hand-rolled + Debezium vs Modulith.** Debezium CDC outbox: language/framework-agnostic, lowest OLTP impact, best throughput and ordering, but heaviest infra and DBA involvement (binlog/WAL retention, Kafka Connect). Modulith registry: no extra infra beyond your DB, transactionally correct by design, great for a modular monolith, integrates with Micrometer; downsides — it tracks **both** `@TransactionalEventListener` and `@ApplicationModuleListener`, so incremental migration is hard; retries can run concurrently (ordering not guaranteed) and multi-instance `@Scheduled` resubmission needs a lock (ShedLock) unless using the 2.1 outbox integration. Korean engineering writeups (e.g. 29CM's on Medium) chose a hand-rolled outbox + `@TransactionalEventListener` over Debezium mainly for operational readiness, not because CDC is technically inferior.

### PART 5 — In-Process Events vs Kafka

| Dimension | In-process Spring events (+ Modulith) | Kafka |
|---|---|---|
| Scope | Within one deployable / modular monolith | Cross-service, cross-language |
| Coupling | Decouples modules; no infra beyond DB | Decouples services; broker infra |
| Durability | Transient (plain events) / DB-backed (Modulith registry) | Durable, replicated, disk-persisted |
| Replay | None (plain); resubmission (Modulith) | Full replay from retained offsets |
| Latency | In-JVM, no network hop | Network hop; high throughput |
| Transactions | Same DB transaction (sync) / outbox (Modulith) | Needs outbox/idempotency for atomicity |
| Ordering | Deterministic (sync) | Per-partition |
| Observability | Micrometer + custom | Mature tooling (lag, dashboards) |

Plain Spring events are in-memory and transient — unsuitable alone where reliability/replay matter. The recommended pattern: use Spring events internally to keep modules loosely coupled and testable, and bridge only the selected events that other services need onto Kafka — through the outbox (Modulith `@Externalized` or Debezium) rather than a direct AFTER_COMMIT send. This is also the cleanest microservice-extraction path: when a module graduates to a service, swap `ApplicationEventPublisher` for a Kafka producer while the consumer side (already using `@ApplicationModuleListener` semantics) barely changes.

## Recommendations
1. **Default to POJO events + `@TransactionalEventListener`.** For same-transaction side effects use plain `@EventListener`; for post-commit side effects use `@TransactionalEventListener` (AFTER_COMMIT). Always ask "does this run inside a transaction?" — if not, the listener silently won't fire.
2. **Whenever an AFTER_COMMIT/AFTER_COMPLETION listener writes to the DB, add `@Transactional(propagation = REQUIRES_NEW)`** on the listener or its collaborator, or the writes vanish.
3. **Never bridge to Kafka with a bare AFTER_COMMIT `kafkaTemplate.send`.** Use an outbox. In a modular monolith on Aurora MySQL + Kafka, adopt Spring Modulith's Event Publication Registry (`spring-modulith-starter-jdbc` or `-jpa`) with `@ApplicationModuleListener` for internal handling and `@Externalized` for the events other services consume. If you need lowest latency / highest throughput / strict ordering and can operate Kafka Connect, use Debezium CDC on the binlog against a dedicated outbox table.
4. **Make all consumers idempotent** (dedup on event ID) — every outbox variant is at-least-once.
5. **Testing:** unit-test listeners directly for logic; use `@RecordApplicationEvents` sparingly for "was it published"; for `@TransactionalEventListener` use `TestTransaction.flagForCommit()`/`@Commit` or a `TransactionTemplate`; for async use Awaitility or Modulith's `Scenario`. Prefer state assertions over event-count assertions.
6. **Ordering & async:** use `@Order` for deterministic sync ordering; adopt `@ApplicationModuleListener` (not hand-wired `@Async`+`@TransactionalEventListener`) so `REQUIRES_NEW` is applied correctly.
7. **Purge/monitor** the `event_publication` table (choose `DELETE`/`ARCHIVE` completion mode or a scheduled purge) and, if running multiple instances, guard `@Scheduled` resubmission with ShedLock — or move to Modulith 2.1's outbox externalization.

**Thresholds that change the recommendation:** move from the Modulith registry to Debezium CDC when event latency requirements drop below ~100ms, throughput saturates the DB, or you need strict cross-table ordering; keep polling/registry when volume is moderate and infra simplicity matters. Split a module into a microservice (and rely fully on Kafka) when it needs independent scaling/deployment — not before.

## Caveats
- **Version drift:** `@RecordApplicationEvents` requires Spring Framework ≥5.3.3; reactive `@TransactionalEventListener` requires ≥6.1; `RestrictedTransactionalEventListenerFactory` is 6.2. Spring Modulith 2.0 GA (released Nov 21, 2025, per spring.io "Spring Modulith 2.0 GA, 1.4.5, and 1.3.11 released") rebuilt the registry ("Overhaul event publication lifecycle #796") and is built on Spring Boot 4 / Framework 7, while Modulith 1.4.x pairs with Boot 3.5.x. Verify your matrix.
- Several cited posts are secondary (Medium/DEV) and, for CDC "99.999%"-style claims, marketing-tinged; treat vendor numbers (including Namastack's advertised partition/throughput figures) skeptically. Primary correctness claims here are anchored to Spring reference docs, Javadoc, and Spring source.
- Modulith's registry currently tracks both `@TransactionalEventListener` and `@ApplicationModuleListener`, so adding it to an event-heavy app persists publications for all such listeners at once — plan a big-bang rather than incremental migration.
- The exact `onApplicationEvent` gating code described is from 5.2/5.3-era source (current `main` refactored it into `TransactionalApplicationListenerSynchronization.register(...)`); semantics are unchanged but individual method bodies were not read verbatim from current source.

## Curated Resource List

**Official documentation**
- Spring Framework Reference — "Transaction-bound Events" (phases, `fallbackExecution`, reactive note). Primary source, concise.
- Spring Framework Reference — "Application Events" under TestContext (`@RecordApplicationEvents`, `ApplicationEvents` API). Primary.
- Spring Framework Reference — "Transaction Management" testing (`TestTransaction`, `@Commit`/`@Rollback`, `@BeforeTransaction`). Primary.
- Javadoc: `TransactionalEventListener`, `TransactionPhase`, `TransactionalApplicationListener(MethodAdapter)`, `SimpleApplicationEventMulticaster`, `EventListenerMethodProcessor`, `ApplicationListenerMethodAdapter`, `AsyncUncaughtExceptionHandler`. Source-of-truth for exact semantics.
- Spring Modulith Reference — "Working with Application Events" and "Integration Testing Application Modules" (Event Publication Registry, `@ApplicationModuleListener`, `@Externalized`, completion modes, `Scenario`/`PublishedEvents`). Primary.
- Spring Boot Reference — "SpringApplication" (startup event order, availability events). Primary.

**Blog posts**
- Spring Blog — "Better application events in Spring Framework 4.2" (Stéphane Nicoll): the design rationale for POJO events, `@EventListener`, `@TransactionalEventListener`. Authoritative, foundational.
- Spring Blog — "Simplified Event Externalization with Spring Modulith" (Oliver Drotbohm, 2023-09-22): outbox/externalization design straight from the project lead. Authoritative.
- Baeldung — "Spring Events", "How to Test Spring Application Events", "Event Externalization with Spring Modulith", "Programmatic Transactions in the TestContext Framework". Broad, example-rich, intermediate.
- Reflectoring — "Spring Boot Application Events Explained": events vs method calls, built-in events. Clear, intermediate.
- rieckpil — "Record Spring Events When Testing Spring Boot Applications": `@RecordApplicationEvents` with testing-philosophy caveats. Practical.
- Andrei Roșca (softice.dev) — "Spring puzzler: the @TransactionalEventListener": source-level walkthrough of why AFTER_COMMIT DB writes are lost. Deep, rigorous.
- Bartłomiej Słota (bartslota.com) / DZone mirror — "Transaction synchronization and Spring application events": phases, autonomous transactions, `REQUIRES_NEW`. Deep.
- Wim Deblauwe — "Transactional Outbox pattern with Spring Boot": Spring Integration vs Spring Modulith outbox, ordering & multi-instance caveats (ShedLock). Practical, senior-level.
- Axual — "Outbox Pattern with Apache Kafka" (Spring Modulith): end-to-end Order/Notification example; documents the #395 bug. Practical.
- 29CM engineering (Medium, Korean) — "트랜잭셔널 아웃박스 패턴의 실제 구현 사례": production rationale for hand-rolled outbox + `@TransactionalEventListener` over Debezium. Case study.
- cheese10yun (GitHub blog, Korean) — "ApplicationEventPublisher 이벤트 기반 트랜잭션 처리": `@EventListener` vs `@TransactionalEventListener`, SQS/RabbitMQ notes. Practical.

**Books**
- "Cloud Native Spring in Action" (Thomas Vitale, Manning) — Ch. 10 "Event-driven applications and functions" (Spring Cloud Stream + broker). Intermediate; cloud-native framing.
- "Modulithic Applications with Spring" (Oliver Drotbohm, Leanpub, in progress) — definitive Modulith treatment by the project lead.
- "Microservices Patterns" (Chris Richardson) — canonical transactional outbox / CDC / saga reference (not Spring-specific).
- "Spring in Action" / "Spring Start Here" (Craig Walls, Manning) — general Spring events coverage; introductory.

**Talks & videos**
- Oliver Drotbohm — "A Deep Dive into Spring Application Events" (SpeakerDeck): internals of the event subsystem. Advanced.
- Oliver Drotbohm — "Spring Modulith – A Deep Dive" (SpringOne / Devoxx workshop; slides on SpeakerDeck): modules, events, Event Publication Registry, externalization. Advanced.
- Oliver Drotbohm — "Spring Modulith – Spring for the Architecturally Curious Developer" (Devoxx; on YouTube via Class Central) and "What's new in Spring Modulith?". Intermediate/advanced.
- A Bootiful Podcast — "Oliver Drotbohm on Spring Modulith 2.0" (spring.io, Aug 2025): roadmap and registry revamp.

**Courses**
- Spring Academy (spring.io / Broadcom) — official Spring courses; transactions and testing modules touch these APIs. There is no single dedicated "application events" course of note; the reference docs + Drotbohm talks are the higher-signal path for this specific topic.