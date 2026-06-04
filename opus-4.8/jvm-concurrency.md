---
title: "Concurrency Control on the JVM — From the JMM to Kotlin Coroutines"
category: "JVM Internals"
description: "Two-phase, project-based curriculum for the Kotlin/Spring engineer: master Java concurrency bottom-up (Java Memory Model → synchronized/volatile → java.util.concurrent → lock-free/CAS → mechanical sympathy → Loom virtual threads), then layer Kotlin coroutines on top (continuations → structured concurrency → dispatchers/cancellation → channels/flows). Verifies with jcstress and measures with JMH, and frames virtual threads as execution infrastructure vs. coroutines as the programming model."
---

# Concurrency Control on the JVM: A Rigorous, Project-Based Learning Plan
### From Java Memory Model Foundations to Kotlin Coroutines

## TL;DR
- **Follow a two-phase curriculum**: master the Java primitives bottom-up (JMM → `synchronized`/`volatile` → j.u.c. → lock-free/CAS → mechanical sympathy → Loom virtual threads), then layer Kotlin coroutines on top (CPS/continuations → structured concurrency → dispatchers/cancellation → channels/flows → Spring/Loom integration). The primitives are not legacy trivia — coroutines, virtual threads, and every concurrent collection are *built on* the JMM, so the foundation pays compounding dividends.
- **Anchor everything in verification and measurement**: use **jcstress** (Shipilëv's OpenJDK concurrency stress harness) to falsify your mental model of the JMM and **JMH** to measure contention/false sharing. For a math-PhD learner these tools convert "I think this is correct" into "I have evidence about the allowed outcome set."
- **Treat coroutines vs. virtual threads as complementary, not competing**: virtual threads are *execution infrastructure* (the JVM owns scheduling; write blocking code), coroutines are an *abstraction/programming model* (the library owns scheduling; structured concurrency, cancellation, flows). The decisive recommendation: on a Kotlin/Spring stack, keep coroutines as your concurrency model and let virtual threads replace blocking thread pools underneath.

## Key Findings

**1. The JEP landscape (verified as of June 2026).** Virtual threads were finalized in **JEP 444 (JDK 21, Sept 2023)**, after two previews (JEP 425/JDK 19, JEP 436/JDK 20). **Scoped Values are now FINAL in JDK 25 via JEP 506** (after incubation/preview as JEP 429→446→464→481→487). **Structured concurrency is still in preview** — it has gone through an unusually long incubation/preview chain (JEP 428→437 incubator; 453→462→480→499→505→525 preview) and reached its *fifth* preview as **JEP 505 in JDK 25**, with a significant API redesign (constructors replaced by static factory methods; a new `Joiner` abstraction). A learner must not present structured concurrency in Java as stable. Critically, **JEP 491 ("Synchronize Virtual Threads without Pinning") shipped in JDK 24 (March 2025)**, reimplementing the JVM so that monitors track ownership by virtual-thread identity rather than carrier-thread identity — removing the synchronized-pinning problem that plagued early adopters.

**2. The canonical books are stable and well-matched to this learner.** *Java Concurrency in Practice* (Goetz et al., 2006) remains the reference for fundamentals despite predating the Fork/Join framework, `CompletableFuture`, and Loom. *The Art of Multiprocessor Programming, 2nd ed.* (Herlihy, Shavit, Luchangco, Spear, 2020) is the rigorous, theory-first text — ideal for a pure-mathematician. *Kotlin Coroutines: Deep Dive* (Moskała) is the definitive coroutines book, now in its **3rd edition (2024)**.

**3. The best expert sources are primary and current.** Aleksey Shipilëv's JMM writing, Doug Lea's JSR-133 Cookbook, Roman Elizarov's structured-concurrency essays, and Ron Pressler's Loom performance analysis are all freely available and authoritative. Netflix's production post-mortem on virtual-thread pinning is the best real-world cautionary tale.

## Quick Overview — A Map of the Territory

Before the deep dive, here is the conceptual landscape, ordered as a progression of abstraction. Each layer is implemented in terms of the one below it; understanding the stack top-to-bottom is the entire point of this plan.

1. **Shared memory + the memory model (the substrate).** On a multicore machine, "what one thread writes" and "what another thread reads" are connected only by the *happens-before* relation defined in the Java Memory Model (JLS Ch. 17). Everything else is built to establish happens-before edges cheaply and correctly. This is where your formal-reasoning background is most directly useful: the JMM is a partial order with a precise (if subtle) axiomatic specification, and reasoning about it is reasoning about allowed *executions*, not about a single interleaving.

2. **Mutual exclusion (locks).** `synchronized`/monitors and `ReentrantLock` give you atomicity + visibility by serializing access. Correct but pessimistic; contention is the enemy.

3. **Lock-free / non-blocking (CAS).** `AtomicReference` + compare-and-swap let you build structures (Treiber stack, Michael–Scott queue) whose progress doesn't depend on any thread being scheduled. This is where linearizability (Herlihy–Shavit) becomes the correctness criterion — and it's exactly the same linearizability you've met in distributed-systems consistency.

4. **Higher-level abstractions (j.u.c.).** Executors, concurrent collections, synchronizers (latches, barriers, semaphores, phasers) — battle-tested compositions of the above, so you rarely hand-roll a lock.

5. **Lightweight concurrency (the modern frontier).** Both **virtual threads** (Loom: cheap threads, JVM-scheduled, write blocking code) and **Kotlin coroutines** (compiler-transformed suspendable computations, library-scheduled, structured concurrency + flows) let you express millions of concurrent tasks. They sit at the *top* of the stack but still rely on everything beneath them — a coroutine that touches shared mutable state still needs the JMM's guarantees.

A useful mental anchor: **threads → locks → lock-free → high-level library → lightweight concurrency**. Part 1 climbs steps 1–5 in Java; Part 2 re-climbs step 5 in Kotlin and connects back down.

---

## PART 1 — Java Concurrency Primitives (the foundation)

This is an ordered curriculum. Each module names the concepts to master and the specific resources to consult.

### Module 1.1 — The Java Memory Model (the bedrock)
**Concepts.** Sequential consistency as the idealized model; why real hardware + compilers don't give it for free; *data race* (precise definition: conflicting accesses, at least one write, not ordered by happens-before); the **happens-before** partial order; program order, synchronization order, synchronizes-with edges; visibility, atomicity (including word-tearing and the `long`/`double` non-atomicity caveat for non-volatile fields), and ordering as three distinct guarantees; the **DRF-SC theorem** (data-race-free programs appear sequentially consistent); out-of-thin-air values and why the JMM's causality requirements are hard to formalize; `final`-field semantics and safe publication; the "roach motel" reordering model.

**Why it matters to you.** The JMM is essentially an axiomatic theory of allowed executions. Your instinct to ask "what is the *set* of legal outcomes?" rather than "what happens when I run it?" is exactly the right instinct — and it's the instinct that jcstress mechanizes.

**Resources (all primary, all current):**
- **JLS, Chapter 17 — "Threads and Locks"** (`docs.oracle.com/javase/specs/jls/se21/html/jls-17.html`): §17.4 is the formal memory model. Dense but authoritative; read it like a specification.
- **JSR-133** (the 2004 spec that gave Java 5 its current memory model) and **Doug Lea's "JSR-133 Cookbook for Compiler Writers"** (`gee.cs.oswego.edu/dl/jmm/cookbook.html`) — the bridge from the abstract model to concrete memory barriers (LoadLoad/LoadStore/StoreStore/StoreLoad).
- **Aleksey Shipilëv, "Java Memory Model Pragmatics"** (`shipilev.net/blog/2014/jmm-pragmatics/`) — the single best pedagogical treatment; covers access atomicity, synchronization order, happens-before, DRF, "roach motel," out-of-thin-air, finals.
- **Aleksey Shipilëv, "Close Encounters of The Java Memory Model Kind"** (`shipilev.net/blog/2016/close-encounters-of-jmm-kind/`) — follow-up dismantling common misconceptions using runnable jcstress examples.
- **Shipilëv, "Safe Publication and Safe Initialization in Java"** (`shipilev.net/blog/2014/safe-public-construction/`) and **"All Fields Are Final"** (`shipilev.net/blog/2014/all-fields-are-final/`).
- John Rose's curated **"Java Memory Model Readings"** list (`cr.openjdk.org/~jrose/jvm/JMM-Readings.html`) for going deeper.

### Module 1.2 — Intrinsic locks, monitors, `volatile`
**Concepts.** `synchronized` blocks/methods; the monitor (every object is a monitor); reentrancy; `wait`/`notify`/`notifyAll` and the **guarded-wait pattern** (always wait in a loop re-checking the condition); the monitor pattern for encapsulation. `volatile`'s precise semantics: it gives visibility + ordering (a write happens-before every subsequent read) but **not** atomicity of compound actions (`v++` is still racy). The double-checked-locking idiom and why it was broken pre-JSR-133 and why `volatile` fixes it.

**Resources:** *Java Concurrency in Practice* (JCiP) Ch. 2–3 (thread safety, sharing objects) and Ch. 4 (composing objects); Shipilëv's safe-publication article above for the `volatile`/`final` interaction.

### Module 1.3 — `java.util.concurrent`: the Executor framework
**Concepts.** `Executor`/`ExecutorService`/`ScheduledExecutorService`; `ThreadPoolExecutor` and its parameters (core/max pool size, keep-alive, work queue choice, rejection policy); **thread-pool sizing** (Brian Goetz's formula: for a target CPU utilization, `N_threads ≈ N_cpu × U × (1 + W/C)` where W/C is the wait-to-compute ratio); `Future`, `Callable`; `CompletableFuture` for composable async pipelines (`thenCompose`/`thenCombine`/`exceptionally`), and its limitations (no built-in cancellation propagation, easy to leak threads, verbose error handling). Note explicitly that `CompletableFuture` postdates JCiP.

**Resources:** JCiP Ch. 6–8 (task execution, cancellation/shutdown, applying thread pools); the `java.util.concurrent` package Javadoc (written by Doug Lea — unusually rich); Doug Lea, *Concurrent Programming in Java*, 2nd ed. (1999) for the design rationale behind j.u.c.

### Module 1.4 — Explicit locks and conditions
**Concepts.** `ReentrantLock` (and why you'd choose it over `synchronized`: tryLock, timed/interruptible acquisition, fairness, multiple condition variables); `ReadWriteLock`/`ReentrantReadWriteLock`; `StampedLock` (optimistic reads — a major performance tool, but not reentrant, with subtle usage rules); `Condition` variables as the explicit-lock analog of wait/notify; the **AbstractQueuedSynchronizer (AQS)** — the CLH-queue-based framework underlying almost all j.u.c. synchronizers (worth reading Doug Lea's AQS paper).

**Resources:** JCiP Ch. 13 (explicit locks); Doug Lea, "The java.util.concurrent Synchronizer Framework" (the AQS paper); `StampedLock` Javadoc.

### Module 1.5 — Atomics and compare-and-swap
**Concepts.** `AtomicInteger`/`AtomicLong`/`AtomicReference`; CAS as the hardware primitive (x86 `CMPXCHG`); `getAndAdd`, `compareAndSet`, `updateAndGet`; `LongAdder`/`LongAccumulator` (striped counters that trade exact-read-consistency for write scalability — a mechanical-sympathy classic); the **ABA problem** and its mitigations (`AtomicStampedReference`, `AtomicMarkableReference`); `VarHandle` (Java 9+) and the access modes (plain/opaque/release-acquire/volatile) that finally let Java express the C/C++11-style ordering spectrum.

**Resources:** JCiP Ch. 15 (atomic variables and nonblocking synchronization); the `java.util.concurrent.atomic` package Javadoc; *The Art of Multiprocessor Programming* (TAMP) Ch. 10–11 for the theory; Shipilëv's writing on VarHandle access modes.

### Module 1.6 — Concurrent collections
**Concepts.** `ConcurrentHashMap` (lock-striping in Java 7, then the CAS+bin-level synchronization redesign in Java 8; `computeIfAbsent`/`merge` atomicity and the pinning caveat on pre-JDK-24 virtual threads); `CopyOnWriteArrayList` (read-mostly, snapshot iteration); `BlockingQueue` family (`ArrayBlockingQueue`, `LinkedBlockingQueue`, `SynchronousQueue`, `PriorityBlockingQueue`, `DelayQueue`) as the backbone of producer-consumer and thread pools; `ConcurrentLinkedQueue` (the lock-free Michael–Scott queue in the JDK); `ConcurrentSkipListMap` for sorted concurrent access.

**Resources:** JCiP Ch. 5 (building blocks); the collection Javadocs; TAMP Ch. 10 (queues) and Ch. 13 (concurrent hashing).

### Module 1.7 — Synchronizers
**Concepts.** `CountDownLatch` (one-shot gate), `CyclicBarrier` (reusable rendezvous with optional barrier action), `Semaphore` (permits; bounding/throttling — note that `Semaphore.acquire()` is a virtual-thread-friendly blocking point), `Phaser` (dynamic, multi-phase barrier), `Exchanger` (paired data hand-off). Map each to a real coordination problem.

**Resources:** JCiP Ch. 5.5; package Javadocs.

### Module 1.8 — Fork/Join and parallel streams
**Concepts.** `ForkJoinPool`, the **work-stealing** scheduler (each worker has a deque; idle workers steal from the tail of others), `RecursiveTask`/`RecursiveAction`, the fork/join "do work, then join" discipline; the common pool; parallel streams (built on the common ForkJoinPool) and when they help vs. hurt (splittability, per-element cost, boxing, the shared common-pool hazard). Note Fork/Join postdates JCiP (Java 7).

**Resources:** Doug Lea, "A Java Fork/Join Framework" (the original paper); the `ForkJoinPool` Javadoc; José Paumard's parallel-streams talks.

### Module 1.9 — Lock-free and wait-free programming
**Concepts.** Progress conditions formally: **wait-free** (every thread makes progress in bounded steps) ⊃ **lock-free** (some thread always makes progress) ⊃ **obstruction-free**; the **Treiber stack** (lock-free push/pop via CAS on a head pointer) and the **Michael–Scott queue** (lock-free FIFO); **linearizability** as the correctness condition (every operation appears to take effect atomically at some point between invocation and response) and its relationship to sequential consistency and to distributed-systems linearizability; the consensus hierarchy and **consensus number** (why CAS has consensus number ∞ while read/write registers have 1 — Herlihy's universality result). This module is the theoretical heart of the plan and where TAMP shines.

**Resources:** **TAMP 2nd ed.** Ch. 3 (concurrent objects/linearizability), Ch. 5 (consensus), Ch. 9–11 (linked lists, queues, stacks); the original Treiber and Michael–Scott papers; Shipilëv's lock-free talks.

### Module 1.10 — Mechanical sympathy: caches, false sharing, contention
**Concepts.** Cache lines (typically 64 bytes); the MESI cache-coherence protocol at an intuitive level; **false sharing** (two unrelated fields on the same line ping-ponging between cores) and its fixes (padding, `@Contended` / `jdk.internal.vm.annotation.Contended`); why `LongAdder` beats `AtomicLong` under contention; memory access patterns and prefetching; the single-writer principle; the LMAX Disruptor as the canonical mechanically-sympathetic design. This connects directly to your HFT/lock-free background.

**Resources:** **Martin Thompson's "Mechanical Sympathy" blog** (`mechanical-sympathy.blogspot.com`) — especially the two "False Sharing" posts (2011) and "Memory Barriers/Fences"; Martin Fowler's "The LMAX Architecture" and "Principles of Mechanical Sympathy"; JMH's `JMHSample_22_FalseSharing` (ships with JMH); Shipilëv's JOL (Java Object Layout) tool for inspecting field layout.

### Module 1.11 — Modern Java: Project Loom (virtual threads, structured concurrency, scoped values)
**Concepts.**
- **Virtual threads (JEP 444, final in JDK 21).** A virtual thread is a `java.lang.Thread` whose continuation is mounted on a *carrier* (platform) thread from a ForkJoinPool-based scheduler; on a blocking call it *unmounts*, freeing the carrier. This makes the **thread-per-request** model scale without the reactive-programming mental tax. They are genuinely cheap: per Heinz Kabutz (JavaSpecialists Newsletter #301, "Gazillion Virtual Threads"), *"Each virtual thread with a miniscule stack uses about 560 bytes. If we give the JVM four gigabytes of memory, we would expect to never be able to create more than 8 million virtual threads"* (in his experiment, with threads parked via `LockSupport.parkUntil(Long.MAX_VALUE)` the JVM became unresponsive at roughly 5.6 million). Implications for thread-pool design: **stop pooling virtual threads** — create one per task (`Executors.newVirtualThreadPerTaskExecutor()`); pools exist to amortize expensive resources, and virtual threads are cheap. Pools still matter for *limiting concurrency against a downstream* (use a `Semaphore` instead).
- **Pinning (critical real-world caveat).** Before JDK 24, a virtual thread that blocked inside a `synchronized` block was *pinned* to its carrier (couldn't unmount), risking carrier-pool exhaustion. **JEP 491 ("Synchronize Virtual Threads without Pinning"), shipped in JDK 24 (March 2025)**, reimplemented monitors to track ownership by virtual-thread identity rather than carrier-thread identity, so `synchronized` no longer pins in most cases. On JDK 21–23, the workaround was to replace `synchronized` with `ReentrantLock`.
- **Structured concurrency (JEP 505, fifth preview in JDK 25 — NOT final).** `StructuredTaskScope` makes the parent-child task hierarchy lexical: fork subtasks, join them as a unit, propagate errors and cancellation together. The JDK 25 redesign replaced public constructors with static factory methods and introduced a `Joiner` to express policy (all-succeed, any-succeed, etc.).
- **Scoped values (JEP 506, FINAL in JDK 25).** Immutable, lexically-scoped, inheritable-by-child-tasks replacement for `ThreadLocal`, designed for the million-virtual-thread world (no per-thread copying).

**Resources:** JEP 444, JEP 491, JEP 505, JEP 506 (all on `openjdk.org/jeps/<n>`); **Ron Pressler, "On the Performance of User-Mode Threads and Coroutines"** (`inside.java/2020/08/07/loom-performance/`); Pressler's talk "Virtual Threads for Lightweight Concurrency and Other JVM Enhancements" (InfoQ); José Paumard's "JEP Café" videos on virtual threads and "Are Virtual Threads Going to Make Reactive Programming Irrelevant?"; Nicolai Parlog's "Inside Java Newscast" + "Structured Concurrency in Action" (Devoxx 2025); the Oracle "Core Libraries: Virtual Threads" guide.

---

## PART 2 — Kotlin Coroutines (the modern path)

### Module 2.1 — The conceptual foundation: suspension, continuations, CPS
**Concepts.** A coroutine is a *suspendable computation*. The `suspend` modifier does **not** mean "asynchronous" or "non-blocking" — it means the function can suspend and resume (Elizarov's "Blocking threads, suspending coroutines" is essential to clear this up). Under the hood, the Kotlin compiler performs a **CPS (continuation-passing-style) transformation**: every `suspend fun foo(args): T` is compiled to `foo(args, Continuation<T>): Any?`, where `Continuation` carries the success/failure resumption. The function body becomes a **state machine** (a `switch` over a label field), with local variables that must survive suspension hoisted into the continuation object. Suspension points return the sentinel `COROUTINE_SUSPENDED`. This is why a million coroutines fit in memory: a suspended coroutine is just a heap object (a continuation), not a stack.

**Why it matters to you.** This is a compiler transformation with a precise operational semantics — exactly the kind of mechanism a formal thinker wants to see explicitly rather than treat as magic. The "there is no magic / CPS == callbacks" framing from Elizarov's deep-dive is the key.

**Resources:** **Roman Elizarov, "Blocking threads, suspending coroutines"** (`elizarov.medium.com/blocking-threads-suspending-coroutines-d33e11bf4761`); **"Deep Dive into Coroutines on JVM," KotlinConf 2017** (video: `youtube.com/watch?v=YrrUCSi72E8`; slides on JetBrains resources/SlideShare) — the CPS/state-machine derivation; the **KEEP coroutines design document** (`github.com/Kotlin/KEEP`, `kotlin-coroutines` proposal) — the authoritative spec of the language-level mechanism; *Kotlin Coroutines: Deep Dive* Part 1 ("Understanding Kotlin Coroutines": "How does suspension work?", "Coroutines under the hood").

### Module 2.2 — Structured concurrency in Kotlin
**Concepts.** `CoroutineScope` as the container that bounds coroutine lifetimes; the `coroutineScope { }` builder (suspends until all children complete; propagates failures); `Job` and the parent-child tree; **cancellation propagation** (cancelling a parent cancels all children; a failing child cancels its parent and siblings — unless under a `SupervisorJob`); the structured-concurrency principle: a function that launches concurrency does not return until that concurrency completes, so you never leak a coroutine. Contrast with `GlobalScope` (an anti-pattern for exactly this reason).

**Resources:** **Roman Elizarov, "Structured concurrency"** (`elizarov.medium.com/structured-concurrency-722d765aa952`, Sept 12 2018) — the foundational essay, which announced kotlinx.coroutines v0.26.0 and called structured concurrency *"more than just a feature — it marks an ideology shift so big that I'm writing this post to explain it,"* introducing the now-core requirement that `launch` be invoked on a `CoroutineScope`; **"Structured Concurrency Anniversary"** (`elizarov.medium.com/structured-concurrency-anniversary-f2cc748b2401`, 2019); **"Coroutine Context and Scope"** (`elizarov.medium.com/coroutine-context-and-scope-c8b255d59055`); **"Explicit concurrency"** (`elizarov.medium.com/explicit-concurrency-67a8e8fd9b25`); official guide "Coroutines basics" and "Composing suspending functions" (`kotlinlang.org/docs/`).

### Module 2.3 — Coroutine builders
**Concepts.** `launch` (fire-and-forget, returns a `Job`); `async`/`await` (returns a `Deferred<T>` for a result; structured parallel decomposition); `runBlocking` (bridges blocking and suspending worlds — for `main`/tests only, deliberately *not* a `CoroutineScope` extension); `withContext` (switch context without starting a new coroutine — the right tool for "run this block on Dispatchers.IO"). The deliberate API design: concurrency is *explicit* (you must call a builder), suspension is *not* concurrency.

**Resources:** *Deep Dive* "Starting coroutines" (3rd-ed. merged chapter); official "Coroutine basics."

### Module 2.4 — Coroutine context and dispatchers
**Concepts.** `CoroutineContext` as an **indexed set / persistent map** keyed by `CoroutineContext.Key` (a genuinely elegant data structure: it's both a set and a map, supporting `+` composition and typed lookup — appealing to an algebraist); the elements: `Job`, `CoroutineDispatcher`, `CoroutineName`, `CoroutineExceptionHandler`. Dispatchers: `Dispatchers.Default` (CPU-bound, sized to cores), `Dispatchers.IO` (blocking I/O, elastic up to a cap, backed by a shared pool), `Dispatchers.Main` (UI), `Dispatchers.Unconfined` (rarely used); **`limitedParallelism(n)`** for partitioning a dispatcher to bound concurrency against a resource (e.g. a connection pool) without spawning new threads.

**Resources:** Elizarov "Coroutine Context and Scope"; official "Coroutine context and dispatchers"; *Deep Dive* "Coroutine context" and "Dispatchers."

### Module 2.5 — Cancellation and timeouts
**Concepts.** Cancellation is **cooperative**: a coroutine must be suspending-and-cancellable (`isActive`, `ensureActive()`, `yield()`) or it won't stop; cancellation throws `CancellationException` at suspension points; `withTimeout`/`withTimeoutOrNull`; resource cleanup with `try/finally` and `use`; running cleanup that itself suspends under `withContext(NonCancellable)`; the subtlety that catching `CancellationException` and not rethrowing breaks structured concurrency.

**Resources:** official "Cancellation and timeouts"; *Deep Dive* "Cancellation" (substantially expanded in 3rd ed., including the catch-and-rethrow section).

### Module 2.6 — Exception handling
**Concepts.** How exceptions propagate up the job tree; `coroutineScope` (a failure cancels all siblings and rethrows) vs. `supervisorScope` (children fail independently); `SupervisorJob`; `CoroutineExceptionHandler` (a last-resort handler for *uncaught* exceptions in root coroutines launched with `launch` — it does **not** catch in `async`, where the exception is deferred to `await`). The asymmetry between `launch` and `async` error semantics is a common source of bugs.

**Resources:** official "Coroutine exceptions handling"; *Deep Dive* "Exception handling."

### Module 2.7 — Synchronization primitives in coroutines
**Concepts.** `Mutex` (a *suspending* lock — `withLock { }` — never block a thread to wait); `Semaphore` (suspending permits); but the idiomatic Kotlin preference is **confinement over locking**: confine mutable state to a single coroutine or a single-threaded dispatcher (`limitedParallelism(1)`), or use immutable data + atomic state, rather than sharing-and-locking. Compare to actor-style confinement.

**Resources:** official "Shared mutable state and concurrency"; *Deep Dive* "The problem with shared state" (rewritten in 3rd ed. to cover atomics, concurrent collections, single-thread dispatcher, and `Mutex` comparatively).

### Module 2.8 — Channels and the actor model
**Concepts.** A `Channel<T>` is the suspending analog of `BlockingQueue` (`send`/`receive` suspend instead of block). Channel types by capacity/overflow: **RENDEZVOUS** (capacity 0; sender and receiver must meet), **BUFFERED**, **CONFLATED** (keeps only the latest, `DROP_OLDEST`), **UNLIMITED**. The `produce { }` builder and `consumeEach`; **pipelines**, **fan-out** (multiple consumers, each element delivered once) and **fan-in** (multiple producers); the **`select` expression** for awaiting multiple channels; the (now largely superseded) `actor { }` builder for state confinement.

**Resources:** official "Channels" and "Coroutines and channels — tutorial" (`kotlinlang.org/docs/channels.html`, `coroutines-and-channels.html`); *Deep Dive* Part 3 "Channel" and "Select."

### Module 2.9 — Flows: cold streams, hot streams, backpressure
**Concepts.** `Flow<T>` is a **cold** asynchronous stream — nothing runs until `collect`; built with `flow { emit(...) }`; rich operator set (`map`, `filter`, `transform`, `flatMapConcat/Merge/Latest`, `retry`, `debounce`, `distinctUntilChanged`); **`flowOn`** to change the upstream dispatcher; **`buffer`/`conflate`** to decouple producer/consumer rates (this is how Flow expresses **backpressure**, conceptually matching Reactive Streams' demand-based model); **hot flows**: `StateFlow` (a conflated, always-has-a-value state holder — ideal for representing current state) and `SharedFlow` (a configurable broadcast hub with replay). `Flow` vs. `Channel`: a flow is a *cold recipe* (re-runs per collector); a channel is a *hot conduit* (each element consumed once). Relationship to Reactive Streams: kotlinx-coroutines-reactive provides interop adapters; Flow is the coroutine-native equivalent of `Flux`.

**Resources:** official "Asynchronous Flow"; **Elizarov, "Kotlin Flows and Reactive Streams"** and "Cold flows, hot channels"; *Deep Dive* Part 3 "Flow introduction," "Understanding Flow," "Flow building/lifecycle/processing," "SharedFlow and StateFlow"; "Going Reactive with Kotlin Flow" KotlinConf talk.

### Module 2.10 — Coroutines over threads, and JVM/Java interop
**Concepts.** How coroutines map onto threads: a dispatcher owns a thread pool; a coroutine runs on whatever thread the dispatcher gives it *between* suspension points (so it can resume on a different thread — hence the importance of not relying on thread identity); structured concurrency layered over thread pools. Interop: `CompletableFuture.await()` and `Deferred.asCompletableFuture()`; `Flow`↔`Publisher` adapters (kotlinx-coroutines-reactor/-rx); calling suspend functions from Java (they appear as `Continuation`-taking methods — awkward, so expose blocking or future-returning facades).

**Resources:** official "Guide to reactive streams with coroutines"; kotlinx.coroutines integration modules README.

### Module 2.11 — Coroutines in Spring
**Concepts.** Spring's first-class coroutine support (since Spring 5.2 / Spring Boot 2.2): **suspending `@Controller`/`@RestController` handler functions** in both WebFlux and (with caveats) Web MVC; `Flow<T>` return values map to `Flux` (streaming responses); `coRouter { }` functional DSL; `CoWebFilter`; coroutine-aware `WebClient` extensions (`awaitBody`, `awaitExchange`); `CoroutineCrudRepository` and R2DBC for non-blocking data access; transactional support via `TransactionalOperator.executeAndAwait`. The realistic backend pattern: `suspend fun` controller that does scatter-gather with `coroutineScope { val a = async{...}; val b = async{...}; combine(a.await(), b.await()) }`.

**Resources:** **Spring Framework reference, "Coroutines"** (`docs.spring.io/spring-framework/reference/languages/kotlin/coroutines.html`); the Spring guide "Spring Boot with Kotlin Coroutines and RSocket" (`spring.io/guides/tutorials/spring-webflux-kotlin-rsocket/`); "Going Reactive with Spring, Coroutines and Kotlin Flow."

---

## Curated Resources by Type

### Books
- **Brian Goetz et al., *Java Concurrency in Practice* (Addison-Wesley, 2006).** The canonical foundation. Rigor: practitioner-rigorous, example-driven, deeply correct on the JMM and j.u.c. Covers: thread safety, JMM, intrinsic locks, j.u.c. building blocks, executors, explicit locks, atomics, nonblocking algorithms. **Predates/misses:** Fork/Join (Java 7), `CompletableFuture` (Java 8), parallel streams, VarHandle, and all of Loom. Still the first book to read; the fundamentals are unchanged. (Authors include Goetz, Peierls, Bloch, Bowbeer, Holmes, and Doug Lea.)
- **Herlihy, Shavit, Luchangco & Spear, *The Art of Multiprocessor Programming*, 2nd ed. (Morgan Kaufmann, 2020; ISBN 9780124159501).** The theory-first text — **the best match for a pure-math PhD.** Rigor: high; formal treatment of linearizability, sequential consistency, the consensus hierarchy/consensus numbers, lock-free/wait-free progress, and concurrent data-structure design (locks, lists, queues, stacks, hashing, skiplists, transactional memory). Herlihy and Shavit are Dijkstra-Prize laureates; Herlihy has a math A.B. from Harvard. Examples in Java. Use it alongside the practical books for the "why is this correct?" layer.
- **Marcin Moskała, *Kotlin Coroutines: Deep Dive* (Kt. Academy).** The definitive coroutines book. **Now in its 3rd edition (2024)** (1st ed. 2021, 2nd ed. 2022/23 added a "Coroutines in practice" part; 3rd ed. restructured Part 2 and rewrote the shared-state and "Why coroutines?" chapters). Rigor: covers the under-the-hood CPS/state-machine mechanics *and* practical patterns; the strongest single resource for Part 2. Available on LeanPub (`leanpub.com/coroutines`) and Amazon.
- **Doug Lea, *Concurrent Programming in Java*, 2nd ed. (Addison-Wesley, 1999).** Dated but historically and conceptually valuable — the design rationale behind j.u.c. by its architect. Good follow-up reading for memory-fence and design-pattern depth.
- **Optional breadth:** Paul Butcher, *Seven Concurrency Models in Seven Weeks* (Pragmatic Bookshelf, 2014) — threads-and-locks, functional, actors, CSP, data parallelism, GPU, lambda architecture; good for seeing the JVM model in a wider landscape. For a Loom-era Java treatment, supplement JCiP with current online material (the JEPs, Inside Java, and Parlog/Paumard videos) rather than any single book, since print coverage of Loom is still maturing.

### Engineering & expert blogs
- **Aleksey Shipilëv — `shipilev.net/blog`.** JMM Pragmatics, Close Encounters of the JMM Kind, Safe Publication, plus JMH/JOL/jcstress material. The gold standard for JVM concurrency + benchmarking.
- **Doug Lea — `gee.cs.oswego.edu/dl/`.** The JSR-133 Cookbook for Compiler Writers; the AQS paper; the Fork/Join paper.
- **Roman Elizarov — `elizarov.medium.com`.** "Structured concurrency," "Structured Concurrency Anniversary," "Blocking threads, suspending coroutines," "Explicit concurrency," "Coroutine Context and Scope," "Kotlin Flows and Reactive Streams." The coroutine designer's own conceptual writing.
- **Inside Java — `inside.java`** (Oracle Java Platform Group): Ron Pressler's "On the Performance of User-Mode Threads and Coroutines"; the Loom tag; Nicolai Parlog's Newscasts; JDK-release deep dives.
- **Martin Thompson — `mechanical-sympathy.blogspot.com`** and Martin Fowler's "The LMAX Architecture": false sharing, memory barriers, cache-coherence, the single-writer principle. Directly relevant to your HFT/lock-free interest.
- **Netflix Technology Blog: "Java 21 Virtual Threads — Dude, Where's My Lock?"** (`netflixtechblog.com`, July 29 2024) — the best production post-mortem on virtual-thread pinning/deadlock. The team observed *"intermittent timeouts and hung instances"* on Java 21 + Spring Boot 3 + embedded Tomcat; the root cause was a classic deadlock variant where a `synchronized` block in a tracing library pinned virtual threads to all carrier threads in the ForkJoinPool while they contended for a `ReentrantLock`, so *"the newly created VT cannot be scheduled because all of the OS threads in the fork-join pool are pinned and never released."* (Independently corroborated by InfoQ, Aug 2024.)
- **InfoQ concurrency coverage** for news-level tracking of JEP status and production experience reports.

### Courses, videos & talks
- **Java/JMM:** Aleksey Shipilëv's JMM talks ("Java Memory Model Pragmatics," "Close Encounters") and his **jcstress workshop** (Hydra 2021/2022, on YouTube + slides at `shipilev.net/talks`); José Paumard's "JEP Café" series (virtual threads, "Launching 10 million virtual threads"); Brian Goetz's Loom/Java-evolution talks (Devoxx "Postcards from the Peak of Complexity"); Ron Pressler's Loom talks (Devoxx, JVMLS, P99 CONF, the InfoQ "Virtual Threads for Lightweight Concurrency" presentation); Venkat Subramaniam's concurrency talks.
- **Kotlin:** Roman Elizarov's KotlinConf talks — **"Introduction to Coroutines"** (2017), **"Deep Dive into Coroutines on JVM"** (2017), **"Kotlin Coroutines in Practice"** (2018), and **"Asynchronous Data Streams with Kotlin Flow."** Kt. Academy's Kotlin Coroutines workshops (Moskała).
- **Paid courses:** Rock the JVM has rigorous JVM/Scala/Kotlin concurrency content (including current Loom/structured-concurrency articles); O'Reilly and Pluralsight carry Java concurrency and Kotlin coroutines courses — check publication date for Loom/coroutine-1.7+ currency before committing.

### Official documentation & specs
- **JLS Ch. 17 (Threads and Locks / §17.4 Memory Model)** — `docs.oracle.com/javase/specs/jls/se21/html/jls-17.html`.
- **JSR-133** (Java Memory Model and Thread Specification, 2004).
- **Kotlin coroutines guide** — `kotlinlang.org/docs/coroutines-guide.html` (and the "Coroutines and channels" tutorial).
- **KEEP** (Kotlin Evolution and Enhancement Process), coroutines design document — `github.com/Kotlin/KEEP`.
- **kotlinx.coroutines** GitHub + API reference — `github.com/Kotlin/kotlinx.coroutines`, `kotlinlang.org/api/kotlinx.coroutines/`.
- **JEPs (verify status on `openjdk.org/jeps/<n>`):** Virtual Threads — 425 (preview, JDK 19), 436 (2nd preview, JDK 20), **444 (final, JDK 21)**; Structured Concurrency — 428/437 (incubator, JDK 19/20), 453/462/480/499 (previews, JDK 21–24), **505 (5th preview, JDK 25)**, 525 (6th preview, targeted JDK 26); Scoped Values — 429 (incubator), 446/464/481/487 (previews), **506 (final, JDK 25)**; pinning fix — **491 (JDK 24)**.

---

## Progressive Project-Based Learning Plan

Projects escalate in difficulty and mirror the two-part structure. Each names **what to build**, **what it exercises**, and **what to consult**. Tooling note: install **jcstress** and **JMH** early (both via the OpenJDK Maven archetypes) — you will use them throughout, not just at the end.

### Stage 0 — Tooling bootstrap
**Build:** a Maven/Gradle module wired for JMH (microbenchmarks) and jcstress (the `jcstress-java-test-archetype`), plus JOL for object-layout inspection. Run Shipilëv's bundled jcstress samples and one JMH sample end-to-end. **Exercises:** the toolchain. **Consult:** `openjdk.org/projects/code-tools/jcstress/`, the jcstress samples, JMH samples.

### Stage 1 — Bounded blocking queue, three ways (JMM + locks)
**Build:** a thread-safe bounded queue (a) from scratch with `synchronized` + `wait`/`notifyAll` (guarded-wait loops), then (b) re-implement with `ReentrantLock` + two `Condition`s (notFull/notEmpty), then (c) benchmark both against `ArrayBlockingQueue`/`LinkedBlockingQueue`. **Exercises:** monitors, condition queues, the guarded-wait pattern, fairness, JMH measurement. **Consult:** JCiP Ch. 5/13/14; `BlockingQueue` Javadoc.

### Stage 2 — A thread pool from scratch (Executor framework)
**Build:** a minimal `ThreadPoolExecutor` clone (worker threads draining a `BlockingQueue`, configurable core/max, a rejection policy, graceful shutdown). Then compare behavior/throughput to the JDK's. **Exercises:** executor internals, pool sizing, shutdown/interruption semantics. **Consult:** JCiP Ch. 6–8; `ThreadPoolExecutor` Javadoc.

### Stage 3 — Concurrent cache / Memoizer (composition + stampede)
**Build:** the JCiP `Memoizer` progression — naive `synchronized` map → `ConcurrentHashMap` of `Future` via `putIfAbsent` to prevent **cache stampede** (duplicate computation of the same key). Add TTL/eviction. **Exercises:** atomicity of compound actions, `computeIfAbsent`, safe publication, the difference between thread-safe and *efficiently* thread-safe. **Consult:** JCiP Ch. 5.6 (the canonical Memoizer example).

### Stage 4 — Lock-free Treiber stack and Michael–Scott queue (CAS + theory)
**Build:** a **Treiber stack** with `AtomicReference` + CAS, then a **Michael–Scott lock-free queue**. **Verify linearizability and the absence of lost updates with jcstress** (this is the rigor payoff — you'll empirically observe the allowed/forbidden outcome sets). Deliberately introduce and then fix an **ABA** scenario using `AtomicStampedReference`. **Exercises:** CAS, lock-free progress, ABA, linearizability as the correctness criterion, jcstress as a falsification tool. **Consult:** TAMP Ch. 9–11; the Treiber and Michael–Scott papers; JCiP Ch. 15; Shipilëv's jcstress workshop.

### Stage 5 — Rate limiter (token bucket + sliding window)
**Build:** a token-bucket and a sliding-window-log rate limiter, each implemented first with a lock and then lock-free with atomics/`LongAdder`; make them safe under high contention. **Exercises:** atomics under contention, time handling, choosing lock vs. lock-free, JMH contention measurement. **Consult:** JCiP Ch. 15; `LongAdder` Javadoc; your existing load-testing/HdrHistogram experience for measuring latency distributions of `acquire()`.

### Stage 6 — Connection pool (synchronizers + resource management)
**Build:** a bounded connection pool using a `Semaphore` to cap concurrency + a `BlockingQueue` of idle connections, with timed acquisition and correct release-on-exception. **Exercises:** semaphores, bounding, liveness (avoiding leaks/deadlock), fairness. **Consult:** JCiP Ch. 5.5/8; `Semaphore` Javadoc.

### Stage 7 — Benchmarking contention & false sharing (mechanical sympathy)
**Build:** a JMH harness that demonstrates **false sharing** (padded vs. unpadded counters, with/without `@Contended`), compares `AtomicLong` vs. `LongAdder` vs. `synchronized` counters under N-thread contention, and uses JOL to confirm field layout. Reproduce the classic order-of-magnitude false-sharing slowdown. **Exercises:** cache lines, false sharing, mechanical sympathy, rigorous benchmarking (warmup, fork, avoiding dead-code elimination). **Consult:** Thompson's false-sharing posts; `JMHSample_22_FalseSharing`; JOL.

### Stage 8 — Prove and fix a data race with jcstress (correctness verification)
**Build:** take a deliberately racy publication (e.g., unsafe lazy init / non-volatile flag) and use jcstress to *observe* the illegal outcomes; fix with `volatile`/`final`/safe publication and show the outcome set collapse. **Exercises:** the JMM in practice, visibility/ordering, the empirical meaning of happens-before. **Consult:** Shipilëv "Close Encounters"; jcstress samples.

### Stage 9 — Virtual-threads server (Loom)
**Build:** a small HTTP service in the **thread-per-request** style using `Executors.newVirtualThreadPerTaskExecutor()`; load-test it and compare scalability/latency to a fixed platform-thread pool under a workload with simulated downstream I/O latency. Deliberately **reproduce pinning** on JDK 21 (block inside `synchronized`) and observe carrier starvation; then fix it (ReentrantLock, or run on JDK 24+ to see JEP 491's effect). Add a `Semaphore` to bound concurrency against the "downstream." **Exercises:** virtual threads, mount/unmount, pinning, why you don't pool virtual threads, Little's-Law-style throughput reasoning. **Consult:** JEP 444/491; Pressler's performance article; the Netflix post-mortem; your coordinated-omission awareness when load-testing.

### Stage 10 — Re-implement earlier systems with coroutines
**Build:** rewrite the **rate limiter** and **producer-consumer queue** from Stages 1/5 using coroutines (`Mutex`/`Semaphore`, confinement via `limitedParallelism(1)`, `Channel`). Compare the structured-concurrency version's cancellation/error behavior to the Java version's. **Exercises:** suspending vs. blocking, confinement over locking, channels as suspending queues. **Consult:** *Deep Dive* "The problem with shared state"; official "Shared mutable state."

### Stage 11 — Structured-concurrency scraper/crawler with rate limiting
**Build:** a concurrent web crawler using `coroutineScope`/`async` for structured fan-out, a coroutine `Semaphore` for politeness/rate limiting, `Dispatchers.IO.limitedParallelism(n)` to bound concurrency, and proper cancellation/timeout (`withTimeout`) with cleanup. **Exercises:** structured concurrency, cancellation propagation, dispatcher tuning. **Consult:** Elizarov "Structured concurrency"; official cancellation/timeouts guide.

### Stage 12 — Producer-consumer pipeline with Channels
**Build:** a multi-stage pipeline (`produce` → transform stages → sink) with **fan-out** to parallel workers and **fan-in** to an aggregator; add a `select` to merge multiple sources; experiment with channel capacities (rendezvous/buffered/conflated) and observe backpressure. **Exercises:** channels, pipelines, fan-out/in, select, backpressure. **Consult:** official "Channels" + "Coroutines and channels" tutorial; *Deep Dive* "Channel"/"Select."

### Stage 13 — Real-time data pipeline with Flows (hot/cold)
**Build:** a stream-processing component: a cold `Flow` source with operators and `flowOn`; expose current state via `StateFlow` and events via `SharedFlow`; apply `buffer`/`conflate` and measure throughput under a fast producer/slow consumer. Bridge a Kafka consumer (your domain) into a Flow. **Exercises:** cold vs. hot flows, backpressure/conflation, StateFlow/SharedFlow, Reactive-Streams interop. **Consult:** official "Asynchronous Flow"; Elizarov "Kotlin Flows and Reactive Streams"; *Deep Dive* Part 3.

### Stage 14 — Scatter-gather microservice calls (the realistic backend pattern)
**Build:** a Spring Boot WebFlux service with a **suspending `@RestController`** that does scatter-gather: `coroutineScope { val a = async{ clientA.fetch() }; val b = async{ clientB.fetch() }; combine(a.await(), b.await()) }` over coroutine-aware `WebClient` calls, with a per-call timeout and aggregate cancellation. **Exercises:** Spring coroutine integration, structured parallel decomposition, cancellation across service calls. **Consult:** Spring "Coroutines" reference; the Spring WebFlux+Kotlin guide.

### Stage 15 — Capstone: coroutines vs. virtual threads, same workload
**Build:** implement *one* realistic workload (e.g., the Stage-14 scatter-gather aggregator, or an event-processing consumer) **twice** — once with Kotlin coroutines, once with Java virtual threads + structured concurrency (`StructuredTaskScope`) — and benchmark them on throughput, tail latency (use HdrHistogram, mind coordinated omission), and resource use. Then build the **hybrid**: coroutines as the model, comparing `Dispatchers.IO` reasoning to a virtual-thread dispatcher (`Dispatchers.IO` vs. `newVirtualThreadPerTaskExecutor().asCoroutineDispatcher()`). Write up the trade-offs. **Exercises:** synthesis of the entire plan; the comparison this learner specifically wants. **Consult:** the comparison section below; Pressler's performance article; Elizarov on coroutines vs. virtual threads.

---

## Correctness Verification & Testing of Concurrent Code

Concurrency bugs are **non-deterministic, schedule-dependent, and often invisible on the developer's machine** (strong x86 memory ordering hides bugs that surface on weakly-ordered ARM). Testing must therefore target the *space of allowed executions*, not a single run.

- **jcstress (Java Concurrency Stress)** — Shipilëv's OpenJDK harness. You annotate `@State`/`@Actor`/`@Arbiter` and declare which result tuples are `ACCEPTABLE`, `ACCEPTABLE_INTERESTING`, or `FORBIDDEN`; the harness runs billions of iterations across thread pairings and reports the observed outcome distribution. **This is the single best tool for a rigorous learner** because it operationalizes the JMM: you *see* which reorderings are legal. Use it in Stages 4 and 8. Requires JDK 17+ to build.
- **JMH (Java Microbenchmark Harness)** — the standard for measuring contention, false sharing, and lock-strategy trade-offs without falling into JIT/dead-code/warmup traps. Use it in Stages 1, 5, 7, 15.
- **JOL (Java Object Layout)** — inspect field layout/padding to reason about false sharing concretely.
- **Stress + property testing, fault injection, and `-Xint`/varying thread counts** to perturb schedules; thread dumps + JFR's `jdk.VirtualThreadPinned` event to catch pinning in production. Per Oracle's Java SE 21 "Virtual Threads" core-libraries docs: *"jdk.VirtualThreadPinned indicates that a virtual thread was pinned (and its carrier thread wasn't freed) for longer than the threshold duration. This event is enabled by default with a threshold of 20 ms."*
- **Coroutines:** `kotlinx-coroutines-test` (`runTest`, virtual time for `delay`), and **Turbine** for testing `Flow` emissions deterministically.
- **Formal angle (optional, but you'll enjoy it):** the Netflix virtual-thread deadlock was independently **reproduced in TLA+** — a reminder that model checking complements stress testing for liveness properties that stress tests rarely hit.

---

## Coroutines vs. Virtual Threads — A Clear-Eyed Comparison

Both are "lightweight concurrency," but they live at different layers, and the distinction is the crux of your stack decision.

| Dimension | Kotlin coroutines | Java virtual threads (Loom) |
|---|---|---|
| **Layer** | Abstraction / programming model (compiler + library) | Execution infrastructure (JVM runtime) |
| **Mechanism** | CPS transform → state machine; suspended coroutine = heap object | Continuation mounted on a carrier platform thread; unmounts on block |
| **Scheduling owner** | The library (dispatchers) — explicit, controllable | The JVM (a ForkJoinPool of carriers) — transparent |
| **Programming style** | Suspending functions; `suspend` colors the API | Plain blocking code; a virtual thread *is* a `Thread` |
| **Structured concurrency** | Mature, central, stable (since 2018) | Preview (JEP 505, JDK 25), still evolving |
| **Streams/backpressure** | First-class: `Flow`, `Channel`, `select`, conflation | Not provided; you'd use reactive libs or build it |
| **Cancellation** | Cooperative, built into the model | Via thread interruption (less ergonomic) |
| **Java interop** | Suspend functions are awkward from Java | Universal — every library that uses threads benefits |
| **Best at** | Rich async composition, cancellation, streaming, Android+backend | Scaling existing blocking/thread-per-request code with near-zero rewrite |

**Pressler's key insight** (from "On the Performance of User-Mode Threads and Coroutines," Inside Java, Aug 7 2020): *"in their most common, most useful use-case, the performance benefit of user-mode threads (or coroutines) has little to do with task-switching costs."* He names this dominant case "transaction processing" (a server handling many mostly-blocked requests) and explicitly treats user-mode threads and coroutines *interchangeably* for the analysis — the win comes from supporting a vast number of concurrent, mostly-waiting tasks, not from faster context switches.

**Elizarov's counterpoint** (from "Structured concurrency," Sept 12 2018): Kotlin's structured concurrency was designed into the model from the start — he called it *"more than just a feature — it marks an ideology shift,"* with the core requirement that `launch` run on a `CoroutineScope`. Java's structured concurrency, by contrast, is a newer API layered onto an existing thread model; and coroutines additionally provide the async-composition/streaming layer (Flow) that virtual threads do not.

**Can they coexist? Yes — and that's the recommendation.** Coroutines are by design engine-agnostic: a dispatcher can be backed by a virtual-thread executor. So on a Kotlin/Spring backend you keep coroutines as your *programming model* (for structured concurrency, cancellation, and Flow), and use virtual threads to *eliminate the blocking-pool bottleneck* underneath — e.g. wrapping blocking JDBC (Aurora MySQL!) calls. The historical weak point of coroutines is exactly the boundary with blocking code (which forces `Dispatchers.IO`'s bounded blocking pool); virtual threads relieve that pressure by making "blocking" cheap. Concretely, instead of dispatching blocking work to `Dispatchers.IO`'s capped thread pool, you can dispatch to `newVirtualThreadPerTaskExecutor().asCoroutineDispatcher()`, so each blocking call gets its own virtual thread and no carrier is wasted.

**Decision rule:**
- **Pure Java service, lots of existing blocking code, want scale with minimal rewrite →** virtual threads (thread-per-request).
- **Kotlin service needing rich async composition, cancellation, or streaming →** coroutines.
- **Kotlin/Spring service (your case) →** coroutines as the model; adopt virtual threads underneath for blocking integrations as your JDK reaches 24+ (where pinning is fixed). Don't pool virtual threads; bound downstream concurrency with a `Semaphore` or `limitedParallelism`.

---

## Recommendations — Sequencing & Schedule

A realistic cadence for a senior engineer studying part-time (~6–8 focused hours/week). Adjust by your prior exposure.

**Phase A — JMM & foundations (Weeks 1–3).** Modules 1.1–1.2 + Stages 0–1. Read JLS §17.4 alongside Shipilëv's JMM Pragmatics; do the bounded-queue project; run your first jcstress samples. **Benchmark to advance:** you can state the data-race definition precisely and predict a simple jcstress outcome set before running it.

**Phase B — j.u.c. mastery (Weeks 4–6).** Modules 1.3–1.8 + Stages 2–3, 6. JCiP Ch. 6–8, 13–15. **Advance when:** you can size a thread pool from a workload's wait/compute ratio and explain when `StampedLock` beats `ReadWriteLock`.

**Phase C — Lock-free theory + mechanical sympathy (Weeks 7–9).** Modules 1.9–1.10 + Stages 4, 5, 7, 8. This is your TAMP + jcstress + JMH intensive — the most rigorous and most enjoyable phase for you. **Advance when:** your lock-free queue passes jcstress and you've reproduced (and explained) a false-sharing slowdown with JMH/JOL.

**Phase D — Loom (Weeks 10–11).** Module 1.11 + Stage 9. Read the JEPs, Pressler, and the Netflix post-mortem. **Advance when:** you can explain pinning, why virtual threads aren't pooled, and what JEP 491 changed.

**Phase E — Coroutine internals & structured concurrency (Weeks 12–14).** Modules 2.1–2.6 + Stages 10–11. Elizarov's essays + *Deep Dive* Parts 1–2. **Advance when:** you can hand-derive the CPS/state-machine transform of a two-suspension-point function and explain `launch` vs. `async` exception semantics.

**Phase F — Channels, Flows, Spring (Weeks 15–17).** Modules 2.7–2.11 + Stages 12–14. *Deep Dive* Part 3 + Spring coroutines reference. **Advance when:** you can choose Flow vs. Channel correctly and wire a suspending scatter-gather controller.

**Phase G — Capstone & synthesis (Weeks 18–19).** Stage 15. Produce the coroutines-vs-virtual-threads write-up with HdrHistogram-based latency analysis.

**Thresholds that change the plan:**
- *If you're already fluent in j.u.c.:* compress Phases A–B to two weeks of targeted JMM/jcstress work and spend the savings on Phase C (TAMP) and Phase G.
- *If your production JDK is 21–23:* treat pinning as a live constraint (prefer `ReentrantLock`, audit libraries using `synchronized`); if you can move to JDK 24+/25, adopt virtual threads under coroutines more aggressively and use finalized Scoped Values.
- *If structured concurrency in Java is the deciding factor:* remember it's still preview (JEP 505) — don't build production architecture on its exact API until it finalizes; Kotlin's structured concurrency is stable today.

## Caveats
- **Status accuracy (verified June 2026):** virtual threads and scoped values are FINAL (JDK 21 and JDK 25 respectively); **structured concurrency in Java remains a preview feature** (JEP 505 in JDK 25, with a further preview JEP 525/JDK 26 targeted) and its API has changed materially between previews — code against it expecting churn. Kotlin's structured concurrency, by contrast, has been stable since kotlinx.coroutines 1.0 (2018).
- **Book currency:** *Java Concurrency in Practice* (2006) is foundational but predates Fork/Join, `CompletableFuture`, VarHandle, and Loom — pair it with the JEPs and current talks for the modern layer. *TAMP* 2nd ed. (2020) and *Kotlin Coroutines: Deep Dive* 3rd ed. (2024) are current.
- **Benchmark skepticism:** the casual "coroutines vs. virtual threads" microbenchmarks circulating online (e.g., spawning N sleeping tasks) measure spawn/park overhead, not realistic transaction-processing throughput; treat them as illustrative, not decisive. Pressler's impact-based analysis is the sounder framework.
- **Pinning history:** much online advice ("replace `synchronized` with `ReentrantLock`," "JDBC drivers pin") reflects the JDK 21–23 reality. JEP 491 (JDK 24, March 2025) changed this; verify against your runtime version before applying workarounds.
- **The hard truth about testing:** no tool *proves* concurrent correctness for arbitrary code; jcstress falsifies and stress-tests, JMH measures, TLA+ model-checks bounded models. Combine them, and lean on confinement/immutability to shrink the surface that needs verification at all.