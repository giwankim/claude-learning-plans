---
title: "@Async in Spring Boot 3.x and 4.x: Where It Fits, Where It Breaks (Kotlin-first)"
category: "Spring & Spring Boot"
description: "A scoping guide to @Async on Spring Boot 3.2+ and 4.x from a Kotlin and EKS perspective. Covers what the annotation actually is (proxy-based AOP registered by AsyncAnnotationBeanPostProcessor), the five-step executor resolution order, and why Boot's auto-configured ThreadPoolTaskExecutor differs from raw Spring Framework's SimpleAsyncTaskExecutor. The bulk of the guide is the failure modes that come from crossing a thread boundary: transactions and lazy JPA associations do not propagate, SecurityContext and MDC and trace context are lost without a ContextPropagatingTaskDecorator, an unbounded default queue defeats max-size, and in-flight tasks die on Kubernetes SIGTERM. Also documents the version changes that invalidate older tutorials (Boot 3.4's spring.task.execution.mode=force, Boot 3.5's removal of the taskExecutor bean alias, Boot 4.0's CompositeTaskDecorator, Boot 4.1's spring.task.execution.propagate-context), the Kotlin specifics of allOpen and why @Async does not compose with suspend functions, and HikariCP saturation once virtual threads remove the thread pool as the limiting resource. Ends with a four-phase lab plan, an annotated resource list with currency flags on dated material, and interview-style self-checks."
---

# `@Async` in Spring Boot 3.x and 4.x: Where It Fits, Where It Breaks (Kotlin-first)

## TL;DR
- In the Spring Boot 3.2+/4.x era, `@Async` is a narrow tool: fire-and-forget in-process side effects, plus parallel I/O fan-out. It is not a general concurrency mechanism. Use Kafka for durable work, Kotlin coroutines for structured parallelism, and virtual threads to scale blocking I/O.
- The biggest traps all come from context and lifecycle crossing a thread boundary. Transactions don't propagate, so `@Async` plus `@Transactional` plus lazy JPA gets you a `LazyInitializationException`. Trace and MDC context is lost unless you install `ContextPropagatingTaskDecorator`. Kubernetes drops in-flight tasks on SIGTERM without a word.
- Version behavior changed materially. The auto-configured default executor is a real `ThreadPoolTaskExecutor`, not raw Spring's `SimpleAsyncTaskExecutor`. Setting `spring.threads.virtual.enabled=true` swaps it for a virtual-thread `SimpleAsyncTaskExecutor`. Boot 3.5 dropped the `taskExecutor` bean alias. Observability context propagation only becomes a one-line property (`spring.task.execution.propagate-context`) in Boot 4.1; before that you register a bean yourself.

## Key findings

1. **`@Async` is proxy-based AOP.** `@EnableAsync` registers an `AsyncAnnotationBeanPostProcessor` that wraps beans carrying `@Async` with an `AsyncAnnotationAdvisor` and `AsyncExecutionInterceptor`. Self-invocation, `private` methods, and `final` methods all break it, which matters in Kotlin where methods are final by default.
2. **The default executor is a trap that got better.** Raw Spring Framework falls back to `SimpleAsyncTaskExecutor`, a new thread per task with no pooling. Spring Boot auto-configures a real `ThreadPoolTaskExecutor` instead, though its queue-before-max-pool semantics still surprise people.
3. **Virtual threads change the calculus.** With `spring.threads.virtual.enabled=true` on Java 21+, Boot auto-configures a virtual-thread `SimpleAsyncTaskExecutor` as the default. `@Async` methods then run on virtual threads with effectively unbounded concurrency, which moves the bottleneck to HikariCP.
4. **Transactions do not cross the boundary.** A new thread means a new transaction, or none at all. The correct pattern for "do X after the DB commit" is `@TransactionalEventListener(phase = AFTER_COMMIT)`, optionally combined with `@Async`.
5. **Observability context is lost by default.** Trace, span, and MDC data live in `ThreadLocal`s, so you must install `ContextPropagatingTaskDecorator`. That is manual work in Boot 3.2 through 4.0 and becomes an opt-in property only in Boot 4.1.
6. **Kubernetes SIGTERM drops in-flight `@Async` work** unless you configure graceful shutdown. Even then it is best effort, which is the core argument for durable queues.

## Details

### Decision tree: when to use what (read this first)

Ask, in order:

1. Does the work need to survive a pod restart? If it must not be lost, do not use `@Async`. Use Kafka, or a transactional outbox with CDC. `@Async` tasks live only in a JVM heap queue and are lost on SIGTERM or crash. This is the single most important rule for your EKS microservice stack.
2. Is it a request/response that needs to scale under many concurrent blocking I/O calls? Don't reach for `@Async` per call. Enable virtual threads (`spring.threads.virtual.enabled=true`), keep writing straight-line blocking code, and let the platform scale it.
3. Are you in Kotlin and want structured concurrency, or parallel calls with cancellation and a result? Use coroutines (`coroutineScope { async { } }` with `awaitAll()`). Coroutines give you structured concurrency, cancellation, and `suspend` all the way down. `@Async` gives you none of these and doesn't compose with `suspend`.
4. Is it a genuinely reactive pipeline end to end? Use WebFlux and Reactor.
5. Is it "after this transaction commits, fire a side effect," such as sending a notification or publishing an event? Use `@TransactionalEventListener(AFTER_COMMIT)`, optionally with `@Async` on the listener.
6. Is it scheduled, periodic, or batch work? Use `@Scheduled` or Spring Batch.
7. What's left is the legitimate `@Async` territory: in-process fire-and-forget side effects where loss on crash is acceptable (audit logging, cache warming, non-critical metrics), parallel I/O fan-out within a single request when you don't want to adopt coroutines (return `CompletableFuture<T>` and combine), and non-blocking notifications where best-effort delivery is fine.

In a modern Kotlin codebase on Boot 3.2+/4.x, that leaves `@Async` with a small footprint. Coroutines cover parallel work with a result, Kafka covers work that must not be lost, and virtual threads cover scaling blocking I/O. What remains is best-effort, in-process, fire-and-forget work.

### How it works under the hood

**Activation and proxying.** `@EnableAsync` imports configuration that registers the `AsyncAnnotationBeanPostProcessor`. At bean creation, any bean with `@Async` at class or method level gets an `AsyncAnnotationAdvisor` added to its proxy. At call time, `AsyncExecutionInterceptor` (specifically `AnnotationAsyncExecutionInterceptor`) submits the invocation to a `TaskExecutor`.

**Proxy type.** If the target implements interfaces, Spring uses a JDK dynamic proxy by default; otherwise it builds a CGLIB subclass proxy. `@EnableAsync(proxyTargetClass = true)` forces CGLIB. A classic failure is injecting the concrete type when a JDK proxy was created (`... is a JDK dynamic proxy that implements: ...`); the fix is to inject the interface or set `proxyTargetClass = true`.

**The self-invocation problem.** Because interception happens at the proxy, a call from one method to another `@Async` method *in the same class* bypasses the proxy and runs synchronously. Move the async method to a separate bean.

**`private` and `final` methods are not intercepted.** JDK proxies only see interface (public) methods, and CGLIB cannot override `final` methods. `@Async` must sit on a public, non-final, overridable method.

**The AspectJ escape hatch.** `@EnableAsync(mode = AdviceMode.ASPECTJ)` uses compile-time or load-time weaving instead of proxies. There is no proxy, so self-invocation, `private` and `protected` methods, and internal calls all get intercepted. It requires `spring-aspects` on the classpath, and when ASPECTJ mode is set, `proxyTargetClass` is ignored. One Spring Framework 7 note: as of 7.0, `@EnableAsync` participates in the unified global auto-proxy settings alongside `@EnableTransactionManagement` and friends, so other annotations and Boot's global proxy configuration can influence the effective proxy type.

**Return types.**
- `void` is fire-and-forget. Exceptions are swallowed and only reach an `AsyncUncaughtExceptionHandler`.
- `Future<T>` is a basic handle.
- `CompletableFuture<T>` is the recommended type in Spring 6+. You get rich composition (`thenCompose`, `thenCombine`, `exceptionally`), and exceptions surface via `get()` or `join()` as `ExecutionException` or `CompletionException`.
- `ListenableFuture<T>` has been deprecated since Spring Framework 6.0 and is marked for removal, in favor of `CompletableFuture`. Any tutorial recommending it is dated. The `@Async` javadoc itself was corrected (spring-framework #33805) because it used to suggest the now-deprecated `ListenableFuture` and `AsyncResult`.

The target method must return a completed placeholder to satisfy the compiler, such as `CompletableFuture.completedFuture(value)`, which Spring replaces with the real async future.

**Executor resolution order.** When `@Async` fires, the executor is chosen as:
1. The qualifier on the annotation: `@Async("myExecutor")` looks up that bean by name.
2. Otherwise, `AsyncConfigurer.getAsyncExecutor()` if a bean implements `AsyncConfigurer`.
3. Otherwise, a unique `TaskExecutor` bean in the context.
4. Otherwise, a bean named `taskExecutor` of type `Executor`.
5. Otherwise, a local default `SimpleAsyncTaskExecutor`, which is raw Spring behavior.

Step 5 is where Boot differs from raw Spring. In raw Spring Framework, the fallback `SimpleAsyncTaskExecutor` does no pooling, spawns a new thread per task, and risks OOM under load. In Spring Boot, `TaskExecutionAutoConfiguration` provides an `applicationTaskExecutor` that is also registered under `AsyncAnnotationBeanPostProcessor.DEFAULT_TASK_EXECUTOR_BEAN_NAME`, so `@Async` uses a real pool out of the box. Per the Spring Boot Reference (Task Execution and Scheduling): *"In the absence of an `Executor` bean in the context, Spring Boot auto-configures a `ThreadPoolTaskExecutor` with sensible defaults... The thread pool uses 8 core threads that can grow and shrink according to the load."* The documentation was ambiguous enough here that spring-boot #41334 was filed to clarify that Boot's default is `ThreadPoolTaskExecutor`, not raw Spring's `SimpleAsyncTaskExecutor`.

**Version-specific bean-name changes**, which are easy to trip on:
- Through Boot 3.4, the auto-configured executor is registered under both `applicationTaskExecutor` and `taskExecutor`.
- Boot 3.5 removed the `taskExecutor` alias, leaving only `applicationTaskExecutor`. Per the Spring Boot 3.5.0 Release Notes: *"Previously Spring Boot auto-configured a TaskExecutor with the `taskExecutor` and `applicationTaskExecutor` bean names. As of this release, only the `applicationTaskExecutor` bean name is provided."* Code or `AsyncConfigurer` lookups relying on the `taskExecutor` name must be adapted, or you re-add the alias via a `BeanFactoryPostProcessor` (`beanFactory.registerAlias("applicationTaskExecutor", "taskExecutor")`). This interacts with a known regression (spring-boot #47897) where a custom `AsyncConfigurer` bean stopped picking up the application executor because `AsyncExecutionAspectSupport` still looked for the name `taskExecutor`.
- Boot 3.4 added `spring.task.execution.mode=force`. If you register your own `Executor` bean, Boot normally backs off its auto-configured `AsyncTaskExecutor`; `force` makes Boot keep auto-configuring the `AsyncTaskExecutor` for all integrations (MVC, WebFlux, GraphQL, WebSocket, JPA, and `@Async` unless an `AsyncConfigurer` is present).
- Boot 4.0 added support for multiple `TaskDecorator` beans, combined into a `CompositeTaskDecorator` ordered by `@Order`.

**`spring.task.execution.*` properties** map to `ThreadPoolTaskExecutor`:
- `pool.core-size` (default 8), `pool.max-size`, `pool.queue-capacity`, `pool.keep-alive`, `pool.allow-core-thread-timeout`
- `thread-name-prefix`
- `shutdown.await-termination`, `shutdown.await-termination-period`

**The queue-before-max-pool surprise.** `ThreadPoolTaskExecutor` wraps a JDK `ThreadPoolExecutor`, which grows to `max-size` only after the queue is full. Spring Boot's defaults are `corePoolSize=8`, `maxPoolSize=Integer.MAX_VALUE`, and `queueCapacity=Integer.MAX_VALUE`, so in practice *"Spring Boot will use 8 threads and queue everything after the first 8 tasks are running."* Because the queue is effectively unbounded, the pool never grows past core size and tasks just pile up in memory. Set a bounded `queue-capacity` if you actually want `max-size` threads to be used and want backpressure.

**Virtual threads and the newer executors.** With `spring.threads.virtual.enabled=true` on Java 21+, Boot's `TaskExecutionAutoConfiguration` swaps the default for a `SimpleAsyncTaskExecutor` configured with `setVirtualThreads(true)`. Here `SimpleAsyncTaskExecutor` is a good thing, because each "thread" is a cheap virtual thread. Pooling properties are ignored. Similarly, `@Scheduled` uses a virtual-thread `SimpleAsyncTaskScheduler`, which also ignores pooling properties. `AsyncTaskExecutor` is the interface type Boot exposes, and `SimpleAsyncTaskExecutorBuilder` and `ThreadPoolTaskExecutorBuilder` are provided for building custom executors that replicate auto-config behavior (the `SimpleAsync*` builders auto-configure virtual threads when enabled).

### Pitfalls and failure modes

**1. Exception handling.** For `CompletableFuture<T>`, exceptions complete the future exceptionally, so handle them via `exceptionally` or `handle` or they surface on `join()`. For `void`, the exception is silently swallowed unless you provide an `AsyncUncaughtExceptionHandler` via `AsyncConfigurer.getAsyncUncaughtExceptionHandler()`. Without it, failures simply vanish. This handler, available since Spring 4.1, only fires for `void` returns; `Future`-returning methods carry the exception in the future.

**2. `@Async` plus `@Transactional` is a trap.** Because the async method runs on a different thread, the thread-bound transaction in `TransactionSynchronizationManager` and the JPA `EntityManager` do not propagate. Two consequences follow. Passing a JPA entity into an `@Async` method and touching a lazy association throws `LazyInitializationException`, since the persistence context is closed and the entity is detached. And if you annotate the async method `@Transactional`, it starts its own independent transaction with its own commit and rollback, so the caller's rollback won't roll it back and vice versa. That is silent data divergence, demonstrated cleanly in Korean write-ups such as the dlswns2480 velog experiment, where the two transactions roll back independently.

The correct pattern is to publish a domain event inside the transaction and consume it with `@TransactionalEventListener(phase = AFTER_COMMIT)`. Add `@Async` to the listener to run it off-thread after the commit. Note the AFTER_COMMIT warning in the Javadoc: the transaction is already committed, so any new data access "participates" in the original transaction but won't be committed unless you use `@Transactional(propagation = REQUIRES_NEW)`. If that listener is also `@Async`, the new thread opens a fresh transaction anyway. Pass IDs into async work, never entities.

**3. ThreadLocal context loss.** Everything stored in `ThreadLocal` is gone on the new thread.

`SecurityContextHolder` returns a null authenticated principal. Fix it by wrapping the executor in `DelegatingSecurityContextAsyncTaskExecutor`, which wraps each `Runnable` or `Callable` in a `DelegatingSecurityContextRunnable` or `Callable`, or by setting `MODE_INHERITABLETHREADLOCAL`. Be careful with pooled and reused threads, though: inheritable ThreadLocals only copy at thread *creation*, so a pooled thread keeps stale context on reuse. The delegating executor is the robust choice.

`RequestContextHolder` gives you a null `ServletRequestAttributes` in async threads, and Tomcat's `discardFacade` can recycle the request facade. Don't rely on request scope in async work. MDC logging context goes the same way, so correlation IDs disappear from async log lines, and `TransactionSynchronizationManager` behaves as described above.

**4. Observability context propagation, which is critical for your LGTM stack.** Micrometer trace and span context and MDC are `ThreadLocal`-backed, so `@Async` breaks trace continuity. Spans created inside the async method are not children of the caller span, and logs lose the trace ID; this is documented in spring-boot #34622. The framework's position (spring-framework #30089, #29977, #31130) is that it will not create observations for `@Async` or `@EventListener` out of the box, but it will help you propagate context. The fix is a `TaskDecorator` that snapshots and restores context.

`ContextPropagatingTaskDecorator` lives in `org.springframework.core.task.support`. Per its Javadoc: *"Since: 6.1, Author: Brian Clozel; TaskDecorator that wraps the execution of tasks, assisting with context propagation... particularly useful for restoring a logging context or an observation context for the task execution."* It uses Micrometer's Context Propagation API (`ContextSnapshotFactory` and `ContextSnapshot`) to carry all registered `ThreadLocalAccessor` context, including trace and MDC, across the boundary. Note the Javadoc caveat that it adds per-task overhead and is *not recommended for applications that run lots of very small tasks.* The dependency `io.micrometer:context-propagation` must be on the classpath, usually transitively via Micrometer Tracing or the observability starters (actuator plus tracing, or Boot 4's `spring-boot-starter-opentelemetry`).

What's automatic depends on the version, verified against Spring team sources:
- Boot 3.2, 3.4, 3.5, and 4.0 do not auto-configure it. You must declare a `ContextPropagatingTaskDecorator` `@Bean`. Boot's `TaskExecutionAutoConfiguration` then detects the single `TaskDecorator` bean and installs it onto `applicationTaskExecutor`. Boot 4.0 additionally composes multiple `TaskDecorator` beans via `CompositeTaskDecorator`. The Nov 2025 Spring blog "OpenTelemetry with Spring Boot" states it plainly: *"Spring Boot's auto-configuration looks for `TaskDecorator` beans and installs them into the `AsyncTaskExecutor`,"* and shows the manual `@Bean` you must add. Issue #47893 confirms there was *"no mention... in the Boot documentation... no configuration property to enable that easily."*
- Boot 4.1 adds an opt-in property, `spring.task.execution.propagate-context=true` (default `false`), that registers the decorator onto the auto-configured executor for you. It is tracked as spring-boot #48033 and shipped in the 4.1 line; the default is `false` because of uncertainty about overhead for apps handling many async events. If you build your own `AsyncTaskExecutor`, you still register the `ContextPropagatingTaskDecorator` bean and wire it yourself, since the property only affects the auto-configured executor.

Minimal bean (Kotlin):
```kotlin
@Configuration(proxyBeanMethods = false)
class ContextPropagationConfiguration {
    @Bean
    fun contextPropagatingTaskDecorator() = ContextPropagatingTaskDecorator()
}
```

The practical rule for your services today, on Boot 3.x and 4.0: add the `ContextPropagatingTaskDecorator` bean explicitly, or your Grafana and Tempo traces will show broken chains across `@Async`.

**5. Connection pool exhaustion on Aurora MySQL with HikariCP.** This takes two shapes. With a platform-thread `@Async` pool, if async tasks do JDBC, your effective DB concurrency is bounded by whichever is smaller, the `@Async` pool or the HikariCP pool. Oversizing the `@Async` pool relative to Hikari just makes threads block on `getConnection()`, and you can deadlock if a request holds one connection while awaiting an `@Async` task that needs another.

With virtual threads, concurrency can explode to thousands while HikariCP still defaults to a maximum pool size of 10 (`HikariConfig`'s `DEFAULT_POOL_SIZE = 10`, confirmed across HikariCP 5.0.1 with Boot 3.2 and HikariCP 6.3.0 with Boot 3.5). The wait moves from "waiting for a thread" to "waiting for a connection," and everything looks healthy until latency spikes. Tune Hikari `maximum-pool-size` deliberately to your Aurora instance's capacity, set a fail-fast `connection-timeout`, and consider a semaphore to bound concurrent DB access. Virtual threads do not create free DB capacity.

**6. Rejected execution and unbounded queue growth.** With an unbounded queue you get memory growth and OOM instead of rejection. With a bounded queue, once it is full and the pool is at `max-size`, the `RejectedExecutionHandler` fires. The default is `AbortPolicy`, which throws `RejectedExecutionException`. Your options are `CallerRunsPolicy` for backpressure (it runs the task on the caller thread, slowing intake), `DiscardPolicy` or `DiscardOldestPolicy` to drop work, or a custom handler that blocks by re-queuing via `getQueue().put(r)`. Choose based on whether the work is droppable.

**7. Graceful shutdown in Kubernetes.** On SIGTERM, if the executor isn't configured to wait, queued and in-flight `@Async` tasks are lost. Configure `ThreadPoolTaskExecutor.setWaitForTasksToCompleteOnShutdown(true)` and `setAwaitTerminationSeconds(N)`, or the equivalent `spring.task.execution.shutdown.await-termination` and `await-termination-period` properties. Add `spring.lifecycle.timeout-per-shutdown-phase` and `server.shutdown=graceful` for request draining, where the default drain timeout is 30s. Kubernetes `terminationGracePeriodSeconds` must exceed your Spring await timeouts plus any `preStop` sleep, or the kubelet SIGKILLs the pod mid-drain (spring-boot #26469).

There is a virtual-thread caveat here. The virtual-thread `SimpleAsyncTaskExecutor` historically did not implement lifecycle and graceful-shutdown awareness the way `ThreadPoolTaskExecutor` does as a `SmartLifecycle` (spring-framework #33780). In-flight virtual-thread tasks, such as producing to Kafka, can therefore be cut off before completion, possibly before dependent beans like Kafka producers finish. This is a concrete reason durable work belongs in Kafka rather than `@Async`.

**8. Testing `@Async` code.** Tests are flaky because assertions run before the async task finishes. Override the executor with a synchronous one in test config, an inline executor that runs the task on the calling thread, so behavior is deterministic. For genuinely async assertions, use Awaitility (`await().atMost(...).pollInterval(...).until(...)`) instead of `Thread.sleep`, and note Awaitility's `dontCatchUncaughtExceptions()` when asserting on exceptions thrown in other threads. One `@SpringBootTest` gotcha: `@EnableAsync` in the loaded context makes methods truly async, so provide a test `@Configuration` that supplies a synchronous `taskExecutor` or `applicationTaskExecutor`, minding the 3.5 name change.

### Kotlin-specific concerns

**Final by default versus proxies.** Kotlin classes and methods are `final` unless declared `open`. Spring AOP proxies need overridable methods, so a naive `@Async fun` won't be intercepted, because CGLIB can't subclass a final method. The `kotlin-spring` compiler plugin (allOpen) automatically opens classes and methods annotated with `@Component`, `@Async`, `@Transactional`, `@Cacheable`, `@Configuration`, and similar. Confirm the plugin is applied, which it is by default in Spring Initializr Kotlin projects; otherwise mark the method `open` manually.

**`@Async` and `suspend` functions don't mix.** A `suspend` function compiles to a method with an extra `Continuation` parameter and coroutine state-machine semantics. Spring's `@Async` interceptor doesn't understand this and will submit the raw call to an executor, breaking suspension and cancellation. The mismatch is fundamental: AOP proxies operate at the method-call level, coroutines at the compiler and language level. Don't put `@Async` on `suspend` functions. Spring supports `suspend` in `@Controller` and WebFlux, but not as an `@Async` target.

**Coroutine and `CompletableFuture` interop.** To bridge to Java and Spring APIs that return `CompletableFuture`, use `future { ... }` (from `kotlinx-coroutines-jdk8`, now folded into core) to launch a coroutine returning a `CompletableFuture`, and `CompletionStage.await()` to suspend on an incoming future without blocking. That second one is cancellable and cancels the underlying future on coroutine cancellation. The JetBrains docs explicitly warn against writing pure-Kotlin APIs around `CompletableFuture`, since it exposes a blocking `get()`; use these only for interop.

**When to just use coroutines.** For parallel I/O fan-out with a result, structured cancellation, and timeouts, `coroutineScope { val a = async { }; val b = async { }; a.await() + b.await() }` is strictly better than `@Async` with `CompletableFuture`. Structured concurrency cancels siblings on failure, exceptions propagate normally, and there's no proxy or self-invocation footgun. Reserve `@Async` for fire-and-forget work where you're not already in a coroutine context.

### Production and EKS concerns

**Thread-pool sizing under K8s CPU limits.** For CPU-bound async work, core size should be roughly the available cores, respecting the container's CPU limit and request, since modern JDKs size `availableProcessors()` from cgroup limits. Oversizing just adds context switching. For I/O-bound platform-thread pools, size relative to downstream capacity such as the DB pool or external API concurrency, not CPU, and always bound the queue for backpressure.

Virtual threads largely remove pool sizing as a knob for I/O-bound work. You stop sizing an `@Async` pool and instead size the real constrained resource: HikariCP, downstream rate limits. This is the recommended default for blocking I/O at scale on your stack. Benchmarks consistently show virtual threads don't speed up individual requests; they prevent degradation under high concurrency where platform-thread pools would exhaust.

**Monitoring async executors with Micrometer.** Boot can bind `ThreadPoolTaskExecutor` metrics, support for which arrived in Boot 2.6 per spring-boot #23818, and you can also wrap with `ExecutorServiceMetrics.monitor(registry, executor, "name", tags)`. The metrics worth watching on a `ThreadPoolExecutor`:
- `executor.active`, a gauge of threads actively executing
- `executor.queued`, a gauge of tasks waiting, and `executor.queue.remaining`
- `executor.pool.size`, `executor.pool.core`, `executor.pool.max`
- `executor.completed` (counter), `executor` (timer of execution duration), `executor.idle` (timer of queue wait)
- `executor.rejected` where the binder exposes it

Tag each executor distinctly. For Grafana panels and alerts, graph `executor.queued` and the saturation ratio `executor.active / executor.pool.max`, then alert when `executor.queued` stays above a threshold, when `queue.remaining` approaches 0, and on any increase in rejected tasks. For virtual-thread executors the pool gauges are meaningless, so track task throughput and latency plus the downstream resource instead: Hikari `hikaricp.connections.pending` and `hikaricp.connections.acquire`.

**Backpressure when the queue fills.** In rough order of preference for best-effort in-process work: `CallerRunsPolicy` gives natural backpressure by slowing the producer; a bounded queue with an explicit rejection metric and alert is next; shedding load by discarding is fine if the work is truly optional. If you find yourself needing durability or guaranteed delivery under backpressure, that's the signal to move the work to Kafka.

### Version behavior cheat-sheet
- Boot 2.x: default `@Async` executor auto-configured as `ThreadPoolTaskExecutor`, where raw Spring would use `SimpleAsyncTaskExecutor`. Executor metrics binding from 2.6. No `spring.threads.virtual` property.
- Boot 3.2 (Framework 6.1): virtual-thread support via `spring.threads.virtual.enabled=true`, and the default `@Async` executor becomes a virtual-thread `SimpleAsyncTaskExecutor` when enabled. `ContextPropagatingTaskDecorator` is available from Framework 6.1 but must be wired manually.
- Boot 3.4: `spring.task.execution.mode=force` added, plus `bootstrapExecutor` for background bean init.
- Boot 3.5 (Framework 6.2): `taskExecutor` bean alias removed, leaving only `applicationTaskExecutor`.
- Boot 4.0 (Framework 7.0): multiple `TaskDecorator` beans composed via `CompositeTaskDecorator`, and `@EnableAsync` joins the unified global auto-proxy settings. Context propagation is still manual.
- Boot 4.1 (Framework 7.0): opt-in `spring.task.execution.propagate-context=true` auto-registers `ContextPropagatingTaskDecorator` on the auto-configured executor, defaulting to off.

## A phased learning plan (roughly three to four weeks)

### Phase 1, week 1: mechanics and the proxy model
**Objectives:** Internalize how `@Async` is wired and why it silently no-ops.
**Concepts:** `@EnableAsync`, `AsyncAnnotationBeanPostProcessor`, `AsyncAnnotationAdvisor`, `AsyncExecutionInterceptor`; JDK versus CGLIB proxies; self-invocation; `proxyTargetClass`; `AdviceMode.ASPECTJ`; return types (`void`, `Future`, `CompletableFuture`); Kotlin allOpen.
**Lab:** In a Kotlin Boot 4.x service, add `@Async` to a same-class self-invoked method, a final or non-open method, a `private` method, and a proper public open method on a separate bean. Log `Thread.currentThread().name` to observe which ones actually run async. Then flip `mode = ASPECTJ` with `spring-aspects` and show self-invocation now works. Verify the executor via thread-name prefix.
**Resources:** Spring Framework reference "Task Execution and Scheduling" and "Proxying Mechanisms"; `@EnableAsync` and `Async` Javadoc (Framework 7.0); Baeldung "How To Do @Async in Spring," updated for Spring 7 and Boot 4.

### Phase 2, week 2: executors, virtual threads, HikariCP
**Objectives:** Master executor resolution and sizing, and understand the virtual-thread swap.
**Concepts:** resolution order; `AsyncConfigurer`; `spring.task.execution.*`; queue-before-max-pool; `SimpleAsyncTaskExecutor` versus `ThreadPoolTaskExecutor`; the virtual-thread executor; the 3.5 bean-name change; `spring.task.execution.mode=force`.
**Lab (Testcontainers and Podman, real MySQL):** Build an endpoint that fans out N parallel JDBC calls via `@Async` and `CompletableFuture`. Set core=2 with an unbounded queue and observe only 2 threads with a growing queue. Add a bounded `queue-capacity` and observe growth to `max-size` followed by rejections. Then set `spring.threads.virtual.enabled=true` with a small Hikari pool (the default 10) to reproduce connection-pool starvation, watching `hikaricp.connections.pending` climb. Tune Hikari to fix it.
**Resources:** Spring Boot reference "Task Execution and Scheduling" (Boot 4.1); Spring Boot 3.5 release notes for the taskExecutor alias removal; the official Spring Boot virtual-threads guidance and the "Embracing Virtual Threads" material.

### Phase 3, week 3: failure modes across transactions, context, and exceptions
**Objectives:** Reproduce and fix every major trap.
**Concepts:** transaction non-propagation; `LazyInitializationException`; `@TransactionalEventListener(AFTER_COMMIT)`; `AsyncUncaughtExceptionHandler`; Security, MDC, and Request context loss; `DelegatingSecurityContextAsyncTaskExecutor`; `ContextPropagatingTaskDecorator`.
**Lab (Testcontainers MySQL and Kafka via Podman, full LGTM):** Pass a JPA entity into an `@Async` method and trigger `LazyInitializationException`, then fix it by passing an ID and reloading, and again by moving to `@TransactionalEventListener(AFTER_COMMIT)`. Throw from a `void @Async` method to confirm the exception vanishes, then add an `AsyncUncaughtExceptionHandler`. Wire up Micrometer Tracing with OTel, confirm the trace breaks across `@Async` (spans not nested, missing trace ID in logs), then add a `ContextPropagatingTaskDecorator` bean and confirm continuity in Grafana and Tempo. On Boot 4.1, compare against `spring.task.execution.propagate-context=true`.
**Resources:** `TransactionalEventListener` Javadoc; the Spring blog "OpenTelemetry with Spring Boot" (Nov 2025); spring-boot issues #34622, #47893, #48033; Micrometer context-propagation docs; Baeldung "Spring Security Context Propagation with @Async."

### Phase 4, week 4: production shutdown, monitoring, and choosing alternatives
**Objectives:** Make it safe on EKS and know when to abandon `@Async`.
**Concepts:** graceful shutdown (`setWaitForTasksToCompleteOnShutdown`, `setAwaitTerminationSeconds`, `spring.lifecycle.timeout-per-shutdown-phase`, `terminationGracePeriodSeconds`); executor metrics; backpressure; Kafka versus `@Async` for durability; coroutines versus `@Async`.
**Lab:** Queue several long `@Async` tasks, send SIGTERM to the pod or container, and confirm task loss with the default config; then configure graceful shutdown and confirm completion, and repeat with virtual threads to observe the lifecycle gap from #33780. Bind `ExecutorServiceMetrics` and build a Grafana panel for `executor.queued` and saturation, with an alert on rejections. Finally, rewrite one `@Async` and `CompletableFuture` fan-out as Kotlin coroutines using `coroutineScope` and `awaitAll`, rewrite one fire-and-forget durable task as a Kafka produce and consume, and compare the failure semantics on crash.
**Resources:** Baeldung "Graceful Shutdown of a Spring Boot Application"; spring-boot #26469 on terminationGracePeriodSeconds and #33780; Micrometer JVM and Executor metrics docs; Spring for Apache Kafka reference; Spring Framework Kotlin coroutines reference.

## Annotated resource list

**Official Spring reference docs**
- *Spring Boot Reference, Task Execution and Scheduling* (`docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html`; select the version matching your Boot line, since 4.1 is shown by default). Current and authoritative on executor auto-config, `spring.task.execution.*`, virtual threads, and `force` mode.
- *Spring Framework Reference, Proxying Mechanisms* (`docs.spring.io/spring-framework/reference/core/aop/proxying.html`). Current; JDK versus CGLIB and the final-method limitation.
- *Spring Framework Reference, Kotlin Coroutines* (`docs.spring.io/spring-framework/reference/languages/kotlin/coroutines.html`). Current; what Spring supports for `suspend`, `Deferred`, and `Flow`, and note that `@Async` isn't on that list.
- *Spring Boot Reference, Observability (Actuator)* (`docs.spring.io/spring-boot/reference/actuator/observability.html`). In 4.1 it documents `spring.task.execution.propagate-context` and the manual `ContextPropagatingTaskDecorator` bean.

**Official Javadoc (Framework 7.0, current)**
- `EnableAsync`, `Async`, `AsyncConfigurer`, `AsyncAnnotationBeanPostProcessor`, `AsyncExecutionInterceptor`, `AsyncUncaughtExceptionHandler` for precise contracts, including resolution order and the ASPECTJ notes.
- `ContextPropagatingTaskDecorator` and `CompositeTaskDecorator` (`core.task.support`), since 6.1, the trace and MDC propagation mechanism. Note the "not for lots of tiny tasks" overhead warning.
- `TransactionalEventListener` for AFTER_COMMIT semantics and the resource-access warning.
- `ThreadPoolTaskExecutor`, `SimpleAsyncTaskExecutor`, `SimpleAsyncTaskScheduler`, `AsyncTaskExecutor` for executor behavior and virtual-thread flags.
- `ListenableFuture`, marked deprecated in 6.0 and for removal, which confirms you shouldn't use it.

**Spring team blog and release notes**
- *"OpenTelemetry with Spring Boot"* (`spring.io/blog/2025/11/18/opentelemetry-with-spring-boot`, Moritz Halbritter). Current, and the definitive statement that `@Async` loses context, that you install `ContextPropagatingTaskDecorator` manually in 4.0, and that Boot installs `TaskDecorator` beans into the `AsyncTaskExecutor`.
- *Spring Boot 3.5 Release Notes* (GitHub wiki). Current; the `taskExecutor` alias removal.
- *Spring Boot 3.5.0-RC1 Release Notes* for `spring.task.execution.mode=force` and the background-init `bootstrapExecutor`.
- *Spring Boot 4.0 Release Notes* for multiple `TaskDecorator` beans and `CompositeTaskDecorator`.

**GitHub issues and PRs, the primary sources for behavior changes**
- spring-boot #41334 clarifies that Boot's default executor is `ThreadPoolTaskExecutor`, not raw Spring's `SimpleAsyncTaskExecutor`.
- spring-boot #47897: `applicationTaskExecutor` not used when a custom `AsyncConfigurer` is defined, the fallout from the 3.5 name change.
- spring-boot #34622: `@Async` breaks trace continuity.
- spring-boot #47893 and #48033: documenting and then adding automatic context propagation, which became the 4.1 property.
- spring-boot #23818: executor metrics support for `ThreadPoolTaskExecutor`.
- spring-framework #31130: the introduction of `ContextPropagatingTaskDecorator` in 6.1.
- spring-framework #33780: the virtual-thread `SimpleAsyncTaskExecutor` lifecycle and graceful-shutdown gap.
- spring-framework #33805: `@Async` docs should stop suggesting the deprecated `ListenableFuture`.

**Blogs and tutorials, with currency flags**
- *Baeldung, "How To Do @Async in Spring"* is current, updated for Spring 7 and Boot 4, and uses `CompletableFuture`. A good intro to config and exception handling.
- *Baeldung, "Spring Security Context Propagation with @Async"* is good for `DelegatingSecurityContextAsyncTaskExecutor` and conceptually current.
- *Baeldung, "Graceful Shutdown of a Spring Boot Application"* is current on `setWaitForTasksToCompleteOnShutdown`.
- *Reflectoring* and *Spring Academy* have solid conceptual pieces, but verify the examples aren't pre-virtual-thread.
- Treat with caution any tutorial that recommends `ListenableFuture`, claims the default executor is always `SimpleAsyncTaskExecutor` in Boot, or omits virtual threads. Those reflect a pre-2023 mental model.

**Conference talks and video**
- SpringOne and Devoxx sessions on virtual threads in Spring Boot (2023 to 2025) and on observability and context propagation with Micrometer. Search the SpringDeveloper YouTube channel for "virtual threads Spring Boot" and "Micrometer observability." Roman Elizarov's KotlinConf talks, "Introduction to Coroutines" and "Deep dive into Coroutines," are the canonical coroutines background.

**Korean-language resources**
- *velog, "Spring @Async로 비동기 처리"* (chanyoung1998): clear on self-invocation and why `SimpleAsyncTaskExecutor` is not a real pool.
- *velog, "@Async 적용 시 트랜잭션 간의 예외 경계 실험"* (dlswns2480): a hands-on experiment showing `@Async` transactions are independent, with separate rollbacks.
- *렌딧 기술 블로그, "예외 먹는 @TransactionalEventListener"* (lenditkr.github.io): an excellent deep dive on AFTER_COMMIT with `@Async` and thread-bound transactions.
- *brunch, "Spring Boot @Async 어떻게 동작하는가?"* (springboot/401): AOP and AutoConfiguration mechanics.
- *velog, "[Spring] @Async로 비동기 처리하기"* (think2wice): proxy mechanics and the private and self-invocation rules.
- Most Korean posts predate Boot 3.5 and 4.x, so check version-specific details such as bean names and virtual threads against the official docs.

## Self-check and interview questions
1. Why does `@Async` silently run synchronously when called from another method in the same class, and what are two ways to fix it?
2. Why don't `@Async` and `@Transactional` on the same method give you "async work inside the caller's transaction"? What's the correct pattern?
3. What exactly happens to an exception thrown by a `void @Async` method, and how do you capture it?
4. In Spring Boot, what executor backs `@Async` by default, and how does that differ from raw Spring Framework? What changes with `spring.threads.virtual.enabled=true`?
5. Walk through the executor resolution order for `@Async`.
6. Explain the `ThreadPoolExecutor` queue-before-max-pool behavior, and why an unbounded queue (Spring Boot's default `queueCapacity=Integer.MAX_VALUE`) can defeat your `max-size`.
7. Why does a Micrometer trace break across an `@Async` boundary, and what's the minimal fix in Boot 3.x versus Boot 4.1?
8. Your pod is being rolled in EKS. Which settings ensure in-flight `@Async` work completes, and why is this still not a substitute for Kafka?
9. In Kotlin, why is `@Async` on a `suspend fun` a mistake, and what should you use instead?
10. How does the virtual-thread `SimpleAsyncTaskExecutor` complicate graceful shutdown compared to `ThreadPoolTaskExecutor`?

## Recommendations
1. Adopt a default posture: enable virtual threads for blocking I/O scaling, use coroutines for structured parallel work with results, use Kafka for anything that must not be lost, and reserve `@Async` for best-effort in-process fire-and-forget. Write this into your team's coding guidelines.
2. If you keep `@Async`, always declare a custom `ThreadPoolTaskExecutor` with a bounded queue, named threads, and either `CallerRunsPolicy` or explicit rejection metrics. Add an `AsyncUncaughtExceptionHandler` and a `ContextPropagatingTaskDecorator` bean, or set `spring.task.execution.propagate-context=true` on Boot 4.1. Configure graceful shutdown and align `terminationGracePeriodSeconds`.
3. Never pass JPA entities into `@Async`. Pass IDs and reload, or use `@TransactionalEventListener(AFTER_COMMIT)`.
4. Instrument every executor with Micrometer, and add Grafana alerts on queue saturation and rejections before you ship.
5. When upgrading Boot, re-check the `taskExecutor` to `applicationTaskExecutor` name change in 3.5 and the context-propagation property in 4.1.

**Thresholds that change these recommendations:** migrate the work to Kafka or an outbox if async tasks begin doing DB writes that must be consistent with the request, if delivery must be guaranteed, or if queue depth and rejections are non-trivial under normal load. If you're adopting coroutines broadly, drop `@Async` for parallel fan-out entirely.

## Caveats
- Verify version-specific details against the reference docs for your exact Boot patch version. The 3.5 bean-name change and the 4.1 context-propagation property are recent and easy to get wrong.
- The Boot 4.0 blog phrasing about a "more seamless experience" for context propagation is explicitly forward-looking, pointing at the #48033 work. As of Boot 4.0 the decorator is manual.
- Many popular tutorials predate virtual threads and still recommend `ListenableFuture` or describe `SimpleAsyncTaskExecutor` as the Boot default, so cross-check against official sources.
- Korean-language resources are excellent for mechanics and pitfalls but generally predate Boot 3.5 and 4.x. Don't trust their version-specific specifics.
- HikariCP's default max pool size of 10 and Spring's default `corePoolSize=8` are current as of the versions checked, but they are configurable and your platform defaults may override them. Always confirm against your running config via Actuator.
