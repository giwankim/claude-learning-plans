---
title: "Spring Task Execution and Scheduling: Six Projects and an Annotated Resource List (Aug 2026)"
category: "Spring & Spring Boot"
description: "Six build-it-yourself projects across Spring's task execution and scheduling stack, each with milestones, the concepts it exercises, the pitfalls it surfaces, and an annotated resource list, validated against the Spring Boot and Spring Framework references in August 2026. Project 1 compares four executor strategies under I/O-bound and CPU-bound load with ExecutorServiceMetrics and k6, including why an unbounded queue means max-size is never reached. Project 2 builds an @Async webhook dispatcher with per-partner bulkheads, covering self-invocation, void versus CompletableFuture exception routing, and the trace hole that opens under virtual threads with Resilience4j. Project 3 registers user-defined cron jobs at runtime through TaskScheduler and a custom Trigger. Project 4 reproduces scheduled-task starvation on the default single-thread scheduler and contrasts fixedRate, fixedDelay, and cron under slow executions. Project 5 deduplicates scheduled work across three EKS replicas with ShedLock and usingDbTime(), weighed against a Kubernetes CronJob and against real distributed schedulers such as db-scheduler and JobRunr. Project 6 covers graceful shutdown across SmartLifecycle phases, preStop hooks, and terminationGracePeriodSeconds, including the Kubernetes endpoint-removal race. A Kafka-fed digest capstone combines all six. The 3.x to 4.x notes cover JEP 491 pinning changes on JDK 24, the removal of -Djdk.tracePinnedThreads in favor of the jdk.VirtualThreadPinned JFR event, Boot 4.0's autoconfig renames and CompositeTaskDecorator, and the DefaultLifecycleProcessor per-phase timeout dropping from 30 s to 10 s in Framework 6.2."
---

# Spring Task Execution and Scheduling: Six Projects and an Annotated Resource List (Aug 2026)

## TL;DR
- All six projects check out against the current docs. The live reference URLs are `docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html` for Boot and `docs.spring.io/spring-framework/reference/integration/scheduling.html` for Framework, and `docs/current/javadoc-api/` currently resolves to the Spring Framework 7.0.x Javadoc.
- The 3.x to 4.x change most likely to invalidate older material is the pinning story. On JDK 24+ virtual threads no longer pin on `synchronized` (JEP 491), the `-Djdk.tracePinnedThreads` flag is gone (JEP 491, verbatim: "This option has proven very problematic and no longer useful"), and the `jdk.VirtualThreadPinned` JFR event, enabled by default at a roughly 20 ms threshold, is now the source of truth. Separately, Boot 4.0 renamed the scheduled-task observability autoconfig and added `CompositeTaskDecorator` so multiple `TaskDecorator` beans compose.
- Pitfalls worth designing around from the start: `@Async` self-invocation, void versus `CompletableFuture` exception routing, the default single-thread scheduler (`spring.task.scheduling.pool.size=1`), MDC and trace loss across executors, ShedLock's `lockAtMostFor` against the risk of a pod dying mid-job, and the ordering of executor shutdown against web-server shutdown.

## Key findings
- Boot auto-configures a `ThreadPoolTaskExecutor` with 8 core threads. The Spring Boot reference puts it this way: "the thread pool uses 8 core threads that can grow and shrink according to the load". `maxPoolSize` and `queueCapacity` are effectively `Integer.MAX_VALUE` by default, and both tune through `spring.task.execution.*`. Set `spring.threads.virtual.enabled=true` on JDK 21+ and the auto-configured `AsyncTaskExecutor` becomes a `SimpleAsyncTaskExecutor` on virtual threads instead.
- The default scheduler is single-threaded. From the Spring Boot reference: "The `ThreadPoolTaskScheduler` uses one thread by default" (`spring.task.scheduling.pool.size=1`). That one thread is the root cause of Project 4's starvation demo.
- Spring Framework 6.1 and Boot 3.2 added `ContextPropagatingTaskDecorator` and observability for `@Scheduled`. Boot 4.0 keeps both, with autoconfig renames.
- Distributed dedup (Project 5) is a lock, not a scheduler. ShedLock's own README says so verbatim: "Please note that ShedLock is not and will never be full-fledged scheduler, it's just a lock. If you need a distributed scheduler, please use another project (db-scheduler, JobRunr)."

---

## Project 1: executor comparison lab

One Spring Boot service exposing two endpoint families: an I/O-bound endpoint (simulate a 200 ms to 2 s downstream with `Thread.sleep` or a Testcontainers-backed slow dependency) and a CPU-bound one (hashing, or a prime sieve). Route each through four execution strategies, selectable by profile or by path: a `ThreadPoolTaskExecutor` with explicit core, queue, and max settings; a `SimpleAsyncTaskExecutor` backed by virtual threads; a raw `java.util.concurrent.ExecutorService` you wrap yourself; and Boot's auto-configured `applicationTaskExecutor`.

**Milestones:** (a) baseline with the default 8-core pool and unbounded queue; (b) bind `ExecutorServiceMetrics` for each executor to Micrometer and scrape into Prometheus; (c) run k6 with ramping VUs, exporting through `experimental-prometheus-rw`; (d) flip `spring.threads.virtual.enabled=true` and watch the auto-config swap; (e) bound the queue deliberately and trigger each `RejectedExecutionHandler` policy.

**Concepts:** the core, queue, max growth ordering (Java's `ThreadPoolExecutor` only grows past core size once the queue is full, which is the part most people get wrong), the rejection policies (`AbortPolicy`, `CallerRunsPolicy`, `DiscardPolicy`, `DiscardOldestPolicy`), and why virtual threads help I/O-bound work but not CPU-bound work.

**Pitfalls:** (1) With an unbounded queue (the default `queue-capacity` is effectively `Integer.MAX_VALUE`), `max-size` is never reached. The pool never grows past core size, and instead of backpressure you get latent memory growth. (2) `CallerRunsPolicy` throttles silently by running the task on the request thread, which is good for backpressure and bad if it blocks Tomcat's acceptor. (3) Virtual threads give no CPU-bound benefit and can make things worse through oversubscription. (4) `ExecutorServiceMetrics` emits different time series for `ThreadPoolExecutor` and `ForkJoinPool` (`executor_active_threads` versus `executor_active`), so dashboards break when you swap pool types. (5) Pinning: before JDK 24, `synchronized` around blocking I/O pins the carrier thread.

### Resources
- **Task Execution and Scheduling :: Spring Boot** (https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html): the auto-config reference, covering the "8 core threads" defaults, `spring.task.execution.*`, and the virtual-thread `SimpleAsyncTaskExecutor` swap. Start here.
- **JVM Metrics :: Micrometer** (https://docs.micrometer.io/micrometer/reference/reference/jvm.html): the exact `ExecutorServiceMetrics` binder metric list (`executor`, `executor.idle`, `executor.active`, `executor.queued`, `executor.pool.size`, `executor.queue.remaining`). The `ExecutorServiceMetrics.monitor(...)` section is the one you will wire.
- **Micrometer issue #7089, ThreadPoolExecutor versus ForkJoinPool metrics** (https://github.com/micrometer-metrics/micrometer/issues/7089): documents the metric-name divergence between pool types. Read it before building Grafana panels.
- **Spring Boot Metrics :: Actuator** (https://docs.spring.io/spring-boot/reference/actuator/metrics.html): confirms that every `ThreadPoolTaskExecutor` and `ThreadPoolTaskScheduler` bean is auto-instrumented and tagged by bean name when the underlying `ThreadPoolExecutor` is available.
- **Prometheus remote write :: Grafana k6** (https://grafana.com/docs/k6/latest/results-output/real-time/prometheus-remote-write/): `-o experimental-prometheus-rw`, `K6_PROMETHEUS_RW_SERVER_URL`, and the native-histogram option. Needs Prometheus started with `--web.enable-remote-write-receiver`.
- **JEP 491: Synchronize Virtual Threads without Pinning** (https://openjdk.org/jeps/491): the source for JDK 24 removing `synchronized` pinning and dropping `jdk.tracePinnedThreads`, plus the enhanced `jdk.VirtualThreadPinned` JFR event.
- **Mike's Bytes, Java 24: Thread pinning revisited** (https://mikemybytes.com/2025/04/09/java24-thread-pinning-revisited/): a practical how-to for detecting pinning through the `jdk.VirtualThreadPinned` JFR event now that the system property is gone.
- **"Virtual Threads After JEP 491: The Bottleneck Moved"** (https://tiarebalbi.com/en/blog/virtual-threads-after-jep-491-bottleneck-moved): load-test methodology (JFR plus p99 drift) and the argument, via Little's Law, that the bottleneck moves to your connection pool.
- **Baeldung, Working with Virtual Threads in Spring** (https://www.baeldung.com/spring-6-virtual-threads): an end-to-end enable-and-benchmark walkthrough.
- **bell-sw, A Guide to Using Virtual Threads with Spring Boot** (https://bell-sw.com/blog/a-guide-to-using-virtual-threads-with-spring-boot/): a JDK vendor's deep dive, with measurements.

---

## Project 2: webhook dispatcher with bulkheads

An `@Async` fan-out dispatcher that POSTs to several third-party partner endpoints when a domain event fires. Give each downstream its own named executor (`@Async("partnerAExecutor")`) so one slow partner cannot exhaust the threads the others need. That is the bulkhead pattern, implemented with dedicated pools. Add retries, an `AsyncUncaughtExceptionHandler`, and a `TaskDecorator` that copies MDC plus Micrometer trace context so spans stay connected in Tempo and Grafana.

**Milestones:** (a) define the per-partner `ThreadPoolTaskExecutor` beans and an `AsyncConfigurer`; (b) contrast a `void` `@Async` method, where the exception disappears from the caller and is routed to `AsyncUncaughtExceptionHandler`, with a `CompletableFuture`-returning one, where it completes the future; (c) add `ContextPropagatingTaskDecorator` and verify the spans connect; (d) replace the hand-rolled pools with Resilience4j bulkheads and compare; (e) add retries and test that redelivery is idempotent.

**Concepts:** proxy-based AOP for `@Async`, executor selection by qualifier, exception-routing semantics, context propagation, and bulkhead isolation (semaphore versus thread pool).

**Pitfalls:** (1) Self-invocation. Calling an `@Async` method from inside the same bean bypasses the proxy and runs it synchronously; it is the most common `@Async` bug. (2) Void methods swallow exceptions unless you register an `AsyncUncaughtExceptionHandler` through `AsyncConfigurer`. (3) MDC and trace IDs vanish on the async thread without a `TaskDecorator`. Under virtual threads, Resilience4j's internal executors are not wired by Spring, so the trace develops a hole exactly at the resilient call. (4) `ThreadPoolBulkhead` is the wrong tool under virtual threads, since Oracle's guidance is not to pool virtual threads. Use the semaphore bulkhead instead. (5) `AsyncConfigurer` classes initialize very early in bootstrap, so declare their dependencies lazy.

### Resources
- **EnableAsync (Spring Framework Javadoc)** (https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/scheduling/annotation/EnableAsync.html): documents the executor resolution order (`taskExecutor` bean, then a `SimpleAsyncTaskExecutor` fallback), the void-return exception logging, and the `AsyncConfigurer` early-init caveat.
- **Spring Framework, Task Execution and Scheduling (reference)** (https://docs.spring.io/spring-framework/reference/integration/scheduling.html): the `@Async`, `@EnableAsync`, and `AsyncConfigurer` sections.
- **Baeldung, How To Do @Async in Spring** (https://www.baeldung.com/spring-async): `AsyncConfigurer`, `CompletableFuture` versus void exception handling, and custom executors, with GitHub code included.
- **ContextPropagatingTaskDecorator (Javadoc)** (https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/core/task/support/ContextPropagatingTaskDecorator.html): since 6.1. Wraps tasks to restore logging and observation context. Note the overhead warning for large numbers of tiny tasks.
- **Spring Framework issue #31130, Introduce TaskDecorator variant for Context Propagation** (https://github.com/spring-projects/spring-framework/issues/31130): the design rationale, including why `@Async` and `@EventListener` are not auto-instrumented and how the Micrometer Context Propagation library fills the gap.
- **"Micrometer Tracing in Spring Boot: Context Propagation for @Async, @Scheduled…"** (https://amithkumarg.medium.com/micrometer-tracing-in-spring-boot-context-propagation-for-async-scheduled-newspan-b80f4f4b2c9f): the two approaches (`AsyncConfigurer` versus `TaskDecorator`) for a single pool versus several, plus `@NewSpan`, `@ContinueSpan`, and `@SpanTag`.
- **"Spring Virtual Threads Break Trace IDs" (CodeToDeploy)** (https://medium.com/codetodeploy/spring-virtual-threads-mdc-trace-ids-a8c005ca8c02): the exact Resilience4j plus virtual-threads trace-hole trap and the semaphore-bulkhead fix. Notes that Boot 4.1 auto-propagates Micrometer context across `@Async`.
- **Resilience4j Bulkhead docs** (https://resilience4j.readme.io/docs/bulkhead): semaphore `Bulkhead` versus `FixedThreadPoolBulkhead`, `maxConcurrentCalls`, `maxWaitDuration`, `queueCapacity`.
- **Spring Cloud CircuitBreaker, Bulkhead properties** (https://docs.spring.io/spring-cloud-circuitbreaker/reference/spring-cloud-circuitbreaker-resilience4j/bulkhead-properties-configuration.html): `resilience4j.thread-pool-bulkhead.*` versus `resilience4j.bulkhead.*` and their config precedence.
- **reflectoring, Implementing Bulkhead with Resilience4j** (https://reflectoring.io/bulkhead-with-resilience4j/): a worked example of both bulkhead types, and the easiest one to follow.
- **Spring Retry versus Resilience4j Retry (BetterJavaCode)** (https://betterjavacode.com/programming/spring-retry-vs-resilience4j-retry/): a decision guide. Resilience4j's retry pairs naturally with its circuit breaker.
- **Webhook Retries and Idempotency: A Practical Guide** (https://100plus.tools/guides/webhook-retries-and-idempotency): sender-retry semantics and the idempotency-key design your dispatcher's receivers should assume.

---

## Project 3: dynamic scheduling service

Store user-defined cron jobs in Aurora MySQL and register them at runtime through `TaskScheduler.schedule(Runnable, Trigger)`, keeping a `Map<String, ScheduledFuture<?>>` so you can pause, resume, and reschedule by cancelling and re-registering. Implement a custom `Trigger` by overriding `nextExecution(TriggerContext)`, run it alongside the built-in `CronTrigger` and `PeriodicTrigger`, and compare a `ThreadPoolTaskScheduler` backing against `SimpleAsyncTaskScheduler`.

**Milestones:** (a) a schema for job definitions (id, cron, enabled, payload); (b) a `SchedulingService` with `scheduleATask` and `removeScheduledTask`; (c) a DB poll or an event to pick up changes at runtime; (d) a custom `Trigger` that reads the next run time from the DB; (e) swap the scheduler backing and observe the shutdown and pool differences.

**Concepts:** `Trigger` and `TriggerContext`, `CronExpression` parsing with the Quartz-style macros, the `ScheduledFuture` lifecycle, and `SchedulingConfigurer` for programmatic registration.

**Pitfalls:** (1) The default scheduler is single-threaded, so give your dynamic scheduler its own pool or the jobs serialize. (2) `SimpleAsyncTaskScheduler` has "no real pool": a single scheduler thread fires a new thread per execution, and its shutdown semantics differ. With virtual threads enabled, separate fixed-delay tasks cannot run concurrently on it (framework issue #31900). (3) `TriggerContext` exposes `lastActualExecution` and `lastCompletion`; misreading which is which produces drift. (4) Cancelling a `ScheduledFuture` with `mayInterruptIfRunning=true` interrupts work already in flight.

### Resources
- **Spring Framework, TaskScheduler and Trigger (reference child page)** (https://docs.spring.io/spring-framework/reference/integration/scheduling/task-scheduler.html): the `TaskScheduler` interface, `Trigger`, `CronTrigger`, and `PeriodicTrigger`.
- **Spring Framework, annotation support and SchedulingConfigurer (reference child page)** (https://docs.spring.io/spring-framework/reference/integration/scheduling/annotation-support.html): using `SchedulingConfigurer` to register `Trigger`-based tasks that `@Scheduled` cannot express.
- **SchedulingConfigurer (Javadoc)** (https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/scheduling/annotation/SchedulingConfigurer.html)
- **TaskScheduler (Javadoc)** (https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/scheduling/TaskScheduler.html)
- **CronExpression (Javadoc)** (https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/scheduling/support/CronExpression.html): 6-field expressions; the macros `@yearly`/`@annually`, `@monthly`, `@weekly`, `@daily`/`@midnight`, and `@hourly`; `L` and `W` support.
- **spring.io blog, New in Spring 5.3: Improved Cron Expressions** (https://spring.io/blog/2020/11/10/new-in-spring-5-3-improved-cron-expressions/): background on `CronExpression` replacing `CronSequenceGenerator`.
- **Baeldung, The @Scheduled Annotation in Spring** (https://www.baeldung.com/spring-scheduled-tasks): `SchedulingConfigurer` with `addTriggerTask` for dynamic delay and rate, and a note on the default single-threaded scheduler.
- **Ritesh Shergill, Dynamic Task Scheduling with Spring Boot** (https://riteshshergill.medium.com/dynamic-task-scheduling-with-spring-boot-6197e66fec42): the `Map<String,ScheduledFuture>` register-and-cancel pattern with `CronTrigger`, in Java and easily ported to Kotlin.
- **DZone, Dynamically Schedule the Same Task with Multiple Cron Expressions** (https://dzone.com/articles/multiple-cron-task-with-spring-boot-scheduler): `ScheduledTaskRegistrar.addTriggerTask` for runtime reconfiguration.

---

## Project 4: scheduled-task starvation demo

Reproduce the classic stall: several `@Scheduled` methods on the default single-thread scheduler, where one slow task blocks all the others. Then demonstrate `fixedRate` against `fixedDelay` against `cron` when executions run long and overlap, and fix it by sizing the pool (`spring.task.scheduling.pool.size`), switching to a virtual-thread scheduler, or offloading the method body to a separate executor.

**Milestones:** (a) two `@Scheduled` tasks, one sleeping longer than its interval, and watch the other starve; (b) show `fixedRate` queuing executions back to back while `fixedDelay` waits; (c) bump the pool size and re-observe; (d) enable `@Scheduled` observability (Framework 6.1+ and Boot 3.2+) and chart the execution timers; (e) try `SimpleAsyncTaskScheduler` and note the virtual-thread fixed-delay serialization gotcha.

**Concepts:** `ScheduledAnnotationBeanPostProcessor` wiring, `spring.task.scheduling.*`, overlapping-execution semantics, and `@Scheduled` observability.

**Pitfalls:** (1) The default `pool.size=1`, which is the entire demo. (2) `fixedRate` does not prevent overlap on a multi-thread pool: two executions of the same task can run concurrently unless you guard against it. (3) Co-located cron schedules can overlap, as the reference warns. (4) With virtual threads, `@Scheduled(fixedDelay)` tasks all run on one virtual thread and cannot parallelize (issue #31900).

### Resources
- **Spring Boot, Task Execution and Scheduling** (https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html): `spring.task.scheduling.*` (pool size, thread-name-prefix), and the scheduler using one thread by default.
- **Spring Framework, scheduling reference** (https://docs.spring.io/spring-framework/reference/integration/scheduling.html): the overlap warning ("co-located schedules may overlap"), the `fixedRate`, `fixedDelay`, and `cron` semantics, and reactive `@Scheduled` (6.1).
- **Framework issue #31900, virtual threads plus fixed-delay cannot run concurrently** (https://github.com/spring-projects/spring-framework/issues/31900): the exact `SimpleAsyncTaskScheduler` plus virtual-thread serialization behavior, quoting the doc line about a single scheduler thread.
- **Framework issue #29883, Instrument @Scheduled methods for observability** (https://github.com/spring-projects/spring-framework/issues/29883): the feature that added `@Scheduled` metrics and traces in 6.1.
- **Spring Framework, Observability Support** (https://docs.spring.io/spring-framework/reference/integration/observability.html): how scheduled and async observations are produced, and the `ContextPropagatingTaskDecorator` recommendation.
- **Baeldung, The @Scheduled Annotation in Spring** (https://www.baeldung.com/spring-scheduled-tasks): explicitly, "By default, Spring uses a local single-threaded scheduler," and how to parallelize it.

---

## Project 5: distributed scheduling on EKS

Deploy 3 replicas and watch a `@Scheduled` job fire three times. Fix it with ShedLock and a `JdbcTemplateLockProvider` on Aurora (a lock table plus `@SchedulerLock`). Compare that against moving the job out to a Kubernetes `CronJob`, then work the trade-offs: tuning `lockAtMostFor` against pod eviction mid-execution, clock skew, and rolling deploys.

**Milestones:** (a) reproduce the triplicate firing; (b) add ShedLock, create the `shedlock` table, `@EnableSchedulerLock`, and `usingDbTime()`; (c) tune `lockAtMostFor` and `lockAtLeastFor`, then simulate a pod kill to see how the lock expires; (d) build the K8s `CronJob` equivalent with `concurrencyPolicy: Forbid` and `startingDeadlineSeconds`; (e) evaluate a true distributed scheduler (db-scheduler or JobRunr) for work distribution.

**Concepts:** distributed locking versus distributed scheduling, DB time versus app time clocks, Kubernetes Job semantics, and leader election.

**Pitfalls:** (1) Set `lockAtMostFor` too short and a long job's lock expires while it is still running, so another node double-fires it. Set it too long and a hard pod kill blocks the job until expiry. Use `usingDbTime()` to avoid clock skew between nodes; it is strongly recommended, and it uses DB-engine SQL that prevents INSERT conflicts. (2) ShedLock caches lock rows in memory, so never delete a row by hand. (3) ShedLock is a lock, not a scheduler: every node still keeps its own timer, and a skipped run is not a queued run. (4) Kubernetes CronJob overlap needs `concurrencyPolicy: Forbid`, and schedules missed during controller downtime need `startingDeadlineSeconds`.

### Resources
- **ShedLock (GitHub README)** (https://github.com/lukas-krecan/ShedLock): the primary source. `JdbcTemplateLockProvider` config, `usingDbTime()`, the lock table DDL per database, and the explicit "not and will never be a full-fledged scheduler, use db-scheduler or JobRunr" caveat.
- **ShedLock example (official)** (https://github.com/lukas-krecan/shedlock-example): a minimal runnable `@SchedulerLock` plus `JdbcTemplateLockProvider`.
- **Baeldung, Guide to ShedLock with Spring** (https://www.baeldung.com/shedlock-spring): `@EnableSchedulerLock(defaultLockAtMostFor=...)`, `@SchedulerLock` naming, and the `LockProvider` bean.
- **Kubernetes, CronJob (official docs)** (https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/): `concurrencyPolicy` (Allow, Forbid, Replace), `startingDeadlineSeconds`, history limits, and `timeZone` (1.27+).
- **Kubernetes Recipes, CronJob Best Practices** (https://kubernetes.recipes/recipes/deployments/kubernetes-cronjob-best-practices/): production defaults, namely `Forbid` plus `startingDeadlineSeconds` plus `activeDeadlineSeconds` plus resource limits.
- **foojay, Task schedulers in Java: modern alternatives to Quartz** (https://foojay.io/today/task-schedulers-in-java-modern-alternatives-to-quartz-scheduler/): ShedLock versus clustered Quartz versus db-scheduler versus JobRunr, on performance and UI trade-offs.
- **Redisson, Distributed Task Scheduling in Java: Quartz, ShedLock, and Redisson** (https://redisson.pro/blog/distributed-task-scheduling-in-java-quartz-shedlock-redisson.html): a clear framing of dedupe (a lock) versus distribute (a worker). Vendor blog, so treat the comparative claims with mild skepticism.
- **db-scheduler (GitHub)** (https://github.com/kagkarlsson/db-scheduler): a cluster-friendly persistent scheduler on a single table. From the README: "High throughput. Tested to handle 2k - 10k executions / second."
- **JobRunr, alternatives comparison** (https://www.jobrunr.io/en/documentation/alternatives/): dashboard, and Spring Boot, Micronaut, and Quarkus integration. Vendor comparison.
- **Spring Cloud Kubernetes, Leadership Election** (https://docs.spring.io/spring-cloud-kubernetes/reference/leader-election.html): ConfigMap and Lease-based leader election (`OnGrantedEvent`, `OnRevokedEvent`) as a ShedLock alternative.
- **Spring Integration, Distributed Locks and JDBC Lock Registry** (https://docs.spring.io/spring-integration/reference/distributed-locks.html and https://docs.spring.io/spring-integration/reference/jdbc/lock-registry.html): `LockRegistry` and `JdbcLockRegistry` (the INT_LOCK table, `renewLock()`), another coordination option.

---

## Project 6: graceful shutdown and lifecycle lab

Make long-running scheduled and async tasks survive pod termination cleanly. Combine Spring's `server.shutdown=graceful` and `spring.lifecycle.timeout-per-shutdown-phase`, executor `setWaitForTasksToCompleteOnShutdown(true)` with `setAwaitTerminationSeconds(...)`, a Kubernetes `preStop` hook with `terminationGracePeriodSeconds`, and readiness-probe draining so no new traffic arrives during shutdown.

**Milestones:** (a) enable graceful web shutdown and watch in-flight requests drain; (b) configure the executors to await task completion; (c) add a `preStop` sleep so endpoint deregistration finishes before SIGTERM; (d) order executor shutdown against web-server shutdown with `SmartLifecycle` phases; (e) simulate a rolling deploy and confirm no work is dropped.

**Concepts:** `SmartLifecycle` phases, `isAutoStartup`, and `stop(Runnable)`; the lifecycle-processor timeout; the Kubernetes pod termination sequence; and how readiness and liveness interact.

**Pitfalls:** (1) Graceful shutdown happens in the earliest `SmartLifecycle` stop phase, so if your executor stops before the web layer drains, in-flight requests that submit async work fail. (2) The Kubernetes endpoint-removal race: SIGTERM and endpoint deregistration run in parallel, so without a `preStop` sleep the pod still gets traffic after it has started shutting down (KEP-1669 mitigates this but does not eliminate it). (3) `terminationGracePeriodSeconds` has to exceed `timeout-per-shutdown-phase` plus the preStop sleep, or Kubernetes SIGKILLs the pod mid-drain. (4) The `DefaultLifecycleProcessor` per-phase timeout defaults to 10 s as of Framework 6.2 (the Javadoc: "the default timeout per shutdown phase will apply: 10000 milliseconds (10 seconds) as of 6.2"; it was 30 s in 5.3). That default is independent of `spring.lifecycle.timeout-per-shutdown-phase`, which can override it. (5) IDEs often send a non-graceful kill, so test this in a real container.

### Resources
- **Spring Boot, Graceful Shutdown** (https://docs.spring.io/spring-boot/reference/web/graceful-shutdown.html): `server.shutdown=graceful`, `spring.lifecycle.timeout-per-shutdown-phase`, per-web-server drain behavior, and the IDE caveat.
- **Spring Framework, Lifecycle and SmartLifecycle (reference)** (https://docs.spring.io/spring-framework/reference/core/beans/factory-nature.html#beans-factory-lifecycle-processor): `Lifecycle` and `SmartLifecycle`, phases, `isAutoStartup()`, and `stop(Runnable)`.
- **SmartLifecycle (Javadoc)** (https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/context/SmartLifecycle.html): phase ordering, and the `DefaultLifecycleProcessor` per-phase shutdown timeout default now being 10 s (6.2).
- **Baeldung, Web Server Graceful Shutdown in Spring Boot** (https://www.baeldung.com/spring-boot-web-server-shutdown): concise config plus the 30 s default explained.
- **Kubernetes, Pod Lifecycle (official)** (https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/): SIGTERM, then grace period, then SIGKILL, with endpoint removal happening in parallel.
- **Kubernetes, Container Lifecycle Hooks** (https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/): `preStop` semantics, and the fact that the grace-period countdown starts before preStop.
- **"Kubernetes graceful shutdown: handling SIGTERM and pod termination" (Jorijn)** (https://jorijn.com/en/knowledge-base/kubernetes/troubleshooting/kubernetes-graceful-shutdown-sigterm-pod-termination/): the endpoint-removal race, a KEP-1669 note, and native `preStop.sleep` (K8s 1.30+).
- **Carlos Becker, Kubernetes pod shutdown lifecycle** (https://carlosbecker.com/posts/k8s-pod-shutdown-lifecycle/): a hands-on terminal walkthrough tying preStop, readiness failures, and SIGKILL timing together.
- **"Graceful Shutdown in Spring Boot with sync and async tasks"** (https://medium.com/@office.yeon/graceful-shutdown-in-spring-boot-with-sync-and-async-tasks-a8f8d89ee252): shows the executor shutdown log ordering (`applicationTaskExecutor` after the web drain) with source excerpts. Korean author, written in English.

---

## Capstone: Kafka-fed digest service

Combine everything. A Kafka listener aggregates events into per-user digests. A `@Scheduled` job, ShedLock-guarded so only one replica aggregates, flushes those aggregates periodically. An `@Async` fan-out dispatches the digest webhooks with per-partner bulkheads and trace propagation. Graceful shutdown drains both Kafka consumption and in-flight dispatch on rolling deploys. Scheduled aggregation, async dispatch, distributed locking, trace propagation, and lifecycle management all have to hold up together in one system.

**Reference architectures and repos:**
- **ShedLock example (official)** (https://github.com/lukas-krecan/shedlock-example): a minimal working `@SchedulerLock` plus `JdbcTemplateLockProvider` to graft onto the scheduled aggregator.
- **Spring Framework Observability Support** (https://docs.spring.io/spring-framework/reference/integration/observability.html): keeping the Kafka, scheduled, and async spans connected with `ContextPropagatingTaskDecorator`. It explicitly covers propagating context for events dispatched on a different thread.
- **Spring Boot 4.0 Release Notes (wiki)** (https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes): the scheduled-task observation autoconfig rename, `CompositeTaskDecorator` for multiple `TaskDecorator` beans, and the tracing property rename.

---

## Details: Spring Boot 3.x versus 4.x flags to watch
- **Virtual-thread defaults.** `spring.threads.virtual.enabled=true` on JDK 21+ swaps the auto-configured `AsyncTaskExecutor` and `taskScheduler` for virtual-thread-backed `SimpleAsync*` beans. Documented since Boot 3.2 (Dec 2023), and the same property carries into Boot 4.x. Boot strongly recommends JDK 24+ for virtual threads, per the `SpringApplication` reference.
- **SimpleAsyncTaskScheduler behavior.** With virtual threads enabled, only `spring.task.scheduling.thread-name-prefix` and `spring.task.scheduling.simple.*` apply; the pool-specific `spring.task.scheduling.pool.*` properties are ignored, per the Boot 3.2 release notes. Separate fixed-delay `@Scheduled` tasks cannot run concurrently on it (issue #31900).
- **Pinning and the JDK.** On JDK 24+ (JEP 491) `synchronized` no longer pins, and `-Djdk.tracePinnedThreads` is removed. Use the `jdk.VirtualThreadPinned` JFR event instead, which is enabled by default at a roughly 20 ms threshold. On JDK 21 to 23 the old advice still holds, so migrate hot `synchronized` blocks to `ReentrantLock`, and the property still works there.
- **Boot 4.0 renames.** `ScheduledTasksObservabilityAutoConfiguration` becomes `ScheduledTasksObservationAutoConfiguration`, `management.tracing.enabled` becomes `management.tracing.export.enabled`, and multiple `TaskDecorator` beans are now composed through `CompositeTaskDecorator`. There is no task-execution property rename beyond these, so don't over-claim one.
- **Lifecycle timeout default.** The `DefaultLifecycleProcessor` per-phase shutdown timeout defaults to 10 s as of Framework 6.2, down from 30 s in 5.3, independent of the `spring.lifecycle.timeout-per-shutdown-phase` value Boot sets.

## Recommendations
1. **Work through them in dependency order: 1, 4, 3, 2, 5, 6, then the capstone.** Projects 1 and 4 build the mental model (pools, queues, the single-thread scheduler) cheaply. Projects 3 and 2 add runtime control and fan-out. Projects 5 and 6 add the distributed and operational concerns, and the capstone integrates all of it.
2. **Pin the JDK deliberately per project.** Run Project 1's pinning experiments on both JDK 21 and JDK 24/25 to see JEP 491 in action. Everything else can default to JDK 24+.
3. **Set up observability before the load tests, not after.** Bind `ExecutorServiceMetrics` and enable `@Scheduled` observations first, so every experiment produces Grafana evidence. The threshold that should change your approach: if `executor_queued_tasks` grows without bound under k6, your queue is unbounded, so switch to a bounded queue with an explicit `RejectedExecutionHandler`.
4. **For distributed scheduling, default to ShedLock with `usingDbTime()` on Aurora** unless you need work distribution, in which case adopt db-scheduler or JobRunr. The benchmark that should change that decision: if a single node cannot finish the job comfortably inside `lockAtMostFor`, using under 50% of the window, you need real distribution rather than a lock.
5. **Always set `terminationGracePeriodSeconds` higher than the preStop sleep plus `timeout-per-shutdown-phase`,** and fail readiness in `preStop`. If 5xx responses still show up during rolling deploys after that, add the native `preStop.sleep` (K8s 1.30+) to cover endpoint-propagation latency.

## Caveats
- Several of the linked deep dives are personal blogs and Medium posts (CodeToDeploy, tiarebalbi, Alexander Obregón, office.yeon). They are technically sound and current, but they are secondary sources, so verify the specifics against the official docs and Javadoc cited alongside them. Vendor comparisons (Redisson, JobRunr) are inevitably self-favorable.
- The `docs.spring.io/.../reference/` URLs are version-less and auto-redirect to the latest GA. If you need a pinned version, insert it (for example `/3.5.x/`). The `docs/current/javadoc-api/` links currently resolve to Spring Framework 7.0.x.
- The two Framework reference child pages for TaskScheduler/Trigger and SchedulingConfigurer were not individually HTTP-verified this session. Confidence is high from the search results and the parent `scheduling.html` was confirmed live, but click through once. The corresponding Javadoc links were verified.
- No genuinely high-quality Korean-language resource surfaced that adds anything beyond the English and official sources on these specific topics. The official docs plus the cited deep dives are the strongest path. (The `office.yeon` post is by a Korean author but written in English.)
