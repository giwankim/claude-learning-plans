# Mastering JVM Concurrency: A 16-Week Curriculum

This curriculum transforms a Spring Boot/Kotlin developer into a concurrency expert across three paradigms—Java threading primitives, Kotlin coroutines, and virtual threads. The approach prioritizes deep theoretical understanding before practical application, building from foundational memory models to production-ready microservices patterns.

**Strategic framework**: Each paradigm addresses the same fundamental challenge—managing concurrent execution efficiently—but with distinct tradeoffs. Java's concurrency utilities provide explicit, low-level control essential for understanding what higher-level abstractions hide. Kotlin coroutines introduce structured concurrency with explicit suspension points and compile-time state machine transformation. Virtual threads offer implicit suspension with familiar blocking APIs, dramatically simplifying I/O-bound server code. Understanding all three enables informed architectural decisions for high-traffic microservices.

---

## Phase 1: Java concurrency foundations (Weeks 1-5)

### Week 1-2: Threads, synchronization, and the Java Memory Model

**Learning objectives**: Understand thread lifecycle, intrinsic locks, and why visibility guarantees require explicit synchronization. Master the happens-before relationships that define correct concurrent programs.

**Core resources**:
- **"Java Concurrency in Practice"** by Brian Goetz et al. (Chapters 1-3) — The canonical text. Chapter 2 on thread safety and Chapter 3 on sharing objects establish foundational vocabulary and mental models. Despite 2006 publication, concepts remain authoritative since the JMM hasn't changed.
- **Java Language Specification Chapter 17** (https://docs.oracle.com/javase/specs/jls/se8/html/jls-17.html) — The formal specification of happens-before, volatile semantics, and final field guarantees. Read after JCiP for formalization.
- **Jenkov's Java Memory Model tutorial** (https://jenkov.com/tutorials/java-concurrency/java-memory-model.html) — Visual diagrams explaining the gap between JVM abstraction and hardware reality with CPU caches and memory barriers.

**Supplementary material**:
- Oracle's Java Concurrency Tutorial (https://docs.oracle.com/javase/tutorial/essential/concurrency/)
- Doug Lea's "Concurrent Programming in Java" companion site (https://gee.cs.oswego.edu/dl/cpj/index.html) — Study the synchronizer framework design paper for deep understanding of lock implementation

**Hands-on project**: Build a thread-safe bounded buffer from scratch implementing producer-consumer semantics. First use only `synchronized` and `wait()/notify()`. Then refactor using `ReentrantLock` and `Condition`. Measure throughput differences.

**Milestone**: Can explain why double-checked locking was broken before Java 5, articulate three happens-before relationships from memory, and identify race conditions in code review exercises.

---

### Week 3: Synchronization primitives beyond locks

**Learning objectives**: Master coordination primitives—`CountDownLatch`, `CyclicBarrier`, `Semaphore`, `Phaser`, `Exchanger`—understanding when each applies and their performance characteristics.

**Core resources**:
- **JCiP Chapter 5** — Building blocks section covers synchronizers with practical patterns
- **Baeldung synchronizers series** (https://www.baeldung.com/java-util-concurrent) — Implementation examples for each primitive
- **Pluralsight: "Applying Concurrency and Multi-threading to Common Java 8 Patterns"** by José Paumard — Race conditions, synchronization patterns, and false sharing explained with CPU cache implications

**Hands-on project**: Implement a parallel web crawler that:
1. Uses `Semaphore` to limit concurrent HTTP connections to **10**
2. Uses `CyclicBarrier` to checkpoint progress every **100** URLs processed  
3. Uses `CountDownLatch` for graceful shutdown signaling

**Milestone**: Given a coordination problem, select the appropriate synchronizer and justify the choice. Implement a reusable barrier pattern without library primitives.

---

### Week 4: Concurrent collections and atomics

**Learning objectives**: Understand ConcurrentHashMap's segmented locking (Java 7) vs node-level locking (Java 8+), blocking queue variants, and lock-free algorithms via atomic classes.

**Core resources**:
- **JCiP Chapters 5 and 15** — Building blocks and atomic variables with compare-and-swap mechanics
- **Pluralsight: "Advanced Java 8 Concurrent Patterns"** by José Paumard — ConcurrentHashMap compute methods, parallel operations, LongAdder vs AtomicLong performance
- **GitHub exercises**: https://github.com/leticiamazzoportela/concurrent-programming — Atomic variables and synchronizer practice problems

**Key concepts to master**:
| Collection | Use Case | Key Characteristic |
|-----------|----------|-------------------|
| `ConcurrentHashMap` | Shared mutable state | Lock-free reads, segmented writes |
| `CopyOnWriteArrayList` | Read-heavy, rare writes | Snapshot iteration |
| `LinkedBlockingQueue` | Producer-consumer | Separate put/take locks |
| `ArrayBlockingQueue` | Bounded buffer | Single lock, fair option |
| `ConcurrentSkipListMap` | Sorted concurrent map | Lock-free, O(log n) |

**Hands-on project**: Build a rate limiter supporting **1000** requests/second using `AtomicLong` for counter, `ConcurrentHashMap` for per-client tracking, and sliding window algorithm. Compare with token bucket using `Semaphore`.

**Milestone**: Explain ConcurrentHashMap's compute methods and when computeIfAbsent outperforms get-then-put. Implement a lock-free stack using `AtomicReference.compareAndSet()`.

---

### Week 5: Executors, CompletableFuture, and Fork/Join

**Learning objectives**: Configure thread pools for different workload profiles. Compose asynchronous operations with CompletableFuture. Understand work-stealing in ForkJoinPool.

**Core resources**:
- **JCiP Chapters 6-8** — Task execution, cancellation, and thread pool configuration
- **Udemy: "Java Multithreading, Concurrency & Performance Optimization"** by Michael Pogrebinsky — Strong emphasis on performance with thread pool sizing formulas
- **CallICoder CompletableFuture Tutorial** (https://www.callicoder.com/java-8-completablefuture-tutorial/) — Comprehensive examples of chaining, combining, and exception handling
- **Baeldung Fork/Join Guide** (https://www.baeldung.com/java-fork-join) — Work-stealing algorithm visualization

**Critical formulas**:
```
CPU-bound pools: threads = N_cpu + 1
I/O-bound pools: threads = N_cpu × (1 + wait_time/compute_time)
```

**Hands-on project**: Build an image processing pipeline that:
1. Uses `ForkJoinPool` with `RecursiveAction` for parallel blur filter
2. Chains `CompletableFuture` stages: fetch → resize → filter → save
3. Implements proper cancellation propagation and timeout handling

**Milestone**: Configure ThreadPoolExecutor with custom rejection policy, bounded queue, and thread factory naming. Compose **5+** CompletableFuture operations including `allOf`, `anyOf`, and exception recovery.

---

## Phase 2: Kotlin coroutines deep dive (Weeks 6-10)

### Week 6: Coroutine fundamentals and structured concurrency

**Learning objectives**: Understand suspension semantics, coroutine builders, and why structured concurrency prevents resource leaks.

**Core resources**:
- **Kotlin Coroutines Official Guide** (https://kotlinlang.org/docs/coroutines-guide.html) — Complete all sections through exception handling
- **"Kotlin Coroutines: Deep Dive"** by Marcin Moskała — **THE** definitive book. Part 1 covers sequence builder and suspension mechanics. Part 2 covers library components.
- **Roman Elizarov's "Introduction to Coroutines"** (KotlinConf 2017, YouTube) — Foundational concepts from the coroutines architect

**Key mental model shift**: Unlike threads where any function can block, coroutines require explicit `suspend` marking. This enables compile-time verification of suspension points and prevents accidental blocking of shared dispatchers.

**Hands-on project**: Refactor Week 5's image pipeline to coroutines:
1. Replace CompletableFuture chains with `async/await`
2. Use `supervisorScope` for partial failure handling
3. Implement structured cancellation via `coroutineScope`

**Milestone**: Explain why `GlobalScope.launch` is discouraged. Demonstrate parent-child job relationships with cancellation propagation. Convert callback-based API to suspending function.

---

### Week 7: Dispatchers, context, and coroutine internals

**Learning objectives**: Master dispatcher selection, context propagation, and understand what the compiler generates from suspend functions.

**Core resources**:
- **"Kotlin Coroutines: Deep Dive" Part 1** — "Coroutines Under the Hood" chapter with state machine explanation
- **Roman Elizarov's "Deep Dive into Coroutines on JVM"** (KotlinConf 2017) — Essential for understanding CPS transformation and continuation mechanics at bytecode level
- **Kt.Academy "Coroutines Under the Hood"** (https://kt.academy/article/cc-under-the-hood) — Complete state machine walkthrough with code
- **KEEP Coroutines Design Document** (https://github.com/Kotlin/KEEP/blob/master/proposals/coroutines.md) — Authoritative design specification

**How suspend functions compile**: Every suspend function receives an implicit `Continuation<T>` parameter. The compiler generates a state machine where each suspension point becomes a `when` branch with a label. Local variables are stored in continuation fields before suspension. The return type becomes `Any?` to accommodate both results and `COROUTINE_SUSPENDED` marker.

**Hands-on exercise**: Use IntelliJ's "Show Kotlin Bytecode" → "Decompile" on your suspend functions. Trace the state machine labels and identify where `COROUTINE_SUSPENDED` is returned.

| Dispatcher | Thread Pool | Use Case |
|-----------|------------|----------|
| `Dispatchers.Default` | CommonPool (CPU cores) | CPU-intensive computation |
| `Dispatchers.IO` | Elastic (64+ threads) | Blocking I/O operations |
| `Dispatchers.Main` | UI thread | Android/Desktop UI updates |
| `Dispatchers.Unconfined` | Caller's thread | Testing, rare production use |

**Milestone**: Draw the state machine for a suspend function with **3** suspension points. Explain why `Dispatchers.IO` is sized at **64** threads minimum and when to create custom dispatchers.

---

### Week 8: Exception handling and testing

**Learning objectives**: Master exception propagation semantics across coroutine hierarchies. Write reliable coroutine tests.

**Core resources**:
- **Kotlin docs: Exception Handling** (https://kotlinlang.org/docs/exception-handling.html)
- **"Kotlin Coroutines: Deep Dive" Part 2** — Exception handling chapter with supervisor patterns
- **Lukas Lechner's GitHub** (https://github.com/LukasLechnerDev/Kotlin-Coroutines-and-Flow-UseCases-on-Android) — Unit testing patterns for coroutines

**Exception propagation rules**:
- In `coroutineScope`: first failure cancels siblings, exception propagates to parent
- In `supervisorScope`: failures don't cancel siblings, exceptions handled locally
- `CoroutineExceptionHandler` only works on root coroutines (not children)

**Hands-on project**: Build a resilient data aggregator that:
1. Fetches from **3** independent APIs concurrently
2. Uses `supervisorScope` so one API failure doesn't cancel others
3. Returns partial results with error indicators
4. Includes comprehensive tests using `runTest` and `TestDispatcher`

**Milestone**: Predict exception propagation path in nested coroutine hierarchies. Write tests that verify cancellation behavior and timeout handling.

---

### Week 9: Flows and channels

**Learning objectives**: Distinguish cold flows from hot SharedFlow/StateFlow. Implement channel-based patterns for complex coordination.

**Core resources**:
- **Kotlin docs: Asynchronous Flow** (https://kotlinlang.org/docs/flow.html)
- **Kotlin docs: Channels** (https://kotlinlang.org/docs/channels.html)
- **"Kotlin Coroutines: Deep Dive" Part 3** — Flow operators, StateFlow, SharedFlow internals
- **Roman Elizarov's "Kotlin Coroutines in Practice"** (KotlinConf 2018) — Production patterns and best practices

**Flow vs Channel comparison**:
| Aspect | Flow | Channel |
|--------|------|---------|
| Temperature | Cold (activates on collect) | Hot (always active) |
| Consumers | Single collector | Multiple receivers |
| Backpressure | Built-in suspension | Bounded buffer |
| Use case | Data transformation | Communication |

**Hands-on project**: Build a real-time stock ticker system:
1. `SharedFlow` for broadcasting price updates to multiple subscribers
2. `StateFlow` for current portfolio value
3. `Channel` for order submission queue with fan-out to **3** processors
4. Flow operators for moving average calculation

**Milestone**: Implement custom flow operator. Explain buffer, conflate, and collectLatest behavior differences. Debug flow collection with intermediate operators.

---

### Week 10: Spring Boot coroutine integration

**Learning objectives**: Build production Spring Boot services using coroutines for controllers, repositories, and service layers.

**Core resources**:
- **Spring Framework Coroutines Reference** (https://docs.spring.io/spring-framework/reference/languages/kotlin/coroutines.html)
- **Spring WebFlux/Kotlin Coroutines Tutorial** (https://spring.io/guides/tutorials/spring-webflux-kotlin-rsocket/)
- **Baeldung: Non-Blocking Spring Boot with Kotlin Coroutines** (https://www.baeldung.com/kotlin/spring-boot-kotlin-coroutines)

**Spring coroutine integration points**:
```kotlin
// Suspend controller function
@GetMapping("/users/{id}")
suspend fun getUser(@PathVariable id: Long): User = 
    userRepository.findById(id) ?: throw NotFoundException()

// Flow return type for streaming
@GetMapping("/users", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
fun getAllUsers(): Flow<User> = userRepository.findAll()

// Coroutine repository
interface UserRepository : CoroutineCrudRepository<User, Long>
```

**Hands-on project**: Build a microservice demonstrating:
1. Suspend controller endpoints with proper timeout handling
2. R2DBC coroutine repository integration
3. WebClient with `awaitBody()` extensions
4. Context propagation for tracing (MDC → coroutine context)

**Milestone**: Deploy coroutine-based service to AWS ECS. Demonstrate proper context propagation through async boundaries. Profile with `async-profiler` to identify coroutine-related hotspots.

---

## Phase 3: Virtual threads and Project Loom (Weeks 11-13)

### Week 11: Virtual threads fundamentals

**Learning objectives**: Understand virtual thread architecture, carrier thread mechanics, and when virtual threads outperform traditional approaches.

**Core resources**:
- **JEP 444: Virtual Threads** (https://openjdk.org/jeps/444) — The authoritative specification. Read completely.
- **Oracle Virtual Threads Guide** (https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html) — Official tutorial with examples
- **Java Almanac Virtual Threads Guide** (https://javaalmanac.io/features/virtual-threads/) — Cay Horstmann's comprehensive overview
- **Ron Pressler's InfoQ presentation** (https://www.infoq.com/presentations/virtual-threads-lightweight-concurrency/) — Design rationale from Project Loom lead

**Key architectural insight**: Virtual threads are scheduled by the JVM onto carrier threads (typically ForkJoinPool). When a virtual thread blocks on I/O, it unmounts from the carrier, freeing it for other virtual threads. This enables **millions** of concurrent virtual threads with minimal memory overhead (**200-300 bytes** initial vs **2-10 MB** for platform threads).

**Performance characteristics**:
| Aspect | Platform Threads | Virtual Threads |
|--------|-----------------|-----------------|
| Creation cost | ~1ms, thousands of CPU instructions | Sub-microsecond |
| Stack memory | 2-10 MB native memory | 200-300 bytes (grows on heap) |
| Context switch | 1-10 μs | Sub-microsecond |
| Max practical count | ~10,000 | Millions |

**Hands-on exercise**: Benchmark **100,000** concurrent HTTP calls comparing:
```java
// Platform thread pool
Executors.newFixedThreadPool(200)

// Virtual threads
Executors.newVirtualThreadPerTaskExecutor()
```

**Milestone**: Explain why virtual threads don't make code run faster—they make code wait faster. Articulate the mounting/unmounting lifecycle.

---

### Week 12: Pinning, structured concurrency, and scoped values

**Learning objectives**: Identify and resolve pinning scenarios. Use `StructuredTaskScope` for hierarchical task management. Replace `ThreadLocal` with `ScopedValue`.

**Core resources**:
- **JEP 453: Structured Concurrency** (https://openjdk.org/jeps/453) — Preview API for hierarchical task management
- **JEP 446/506: Scoped Values** (https://openjdk.org/jeps/446) — Modern ThreadLocal replacement
- **JEP 491: Synchronize Without Pinning** (https://openjdk.org/jeps/491) — Java 24+ improvement eliminating most pinning
- **Netflix Tech Blog: "Java 21 Virtual Threads - Dude, Where's My Lock?"** (https://netflixtechblog.com/java-21-virtual-threads-dude-wheres-my-lock-3052540e231d) — Real production pinning issues and solutions

**Pinning scenarios and solutions**:

| Scenario | Java 21-23 | Java 24+ |
|----------|-----------|----------|
| `synchronized` with blocking | Pinned (use ReentrantLock) | Fixed by JEP 491 |
| Native code (JNI) | Pinned | Still pinned |
| Class initialization | Pinned | Still pinned |

**Detection**: Use `-Djdk.tracePinnedThreads=full` or JFR event `jdk.VirtualThreadPinned`

**Hands-on project**: Implement a parallel task aggregator using:
```java
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    Subtask<User> user = scope.fork(() -> fetchUser(id));
    Subtask<Orders> orders = scope.fork(() -> fetchOrders(id));
    scope.join().throwIfFailed();
    return new UserProfile(user.get(), orders.get());
}
```

**Milestone**: Detect pinning in existing code using JFR. Refactor `synchronized` blocks causing pinning. Explain `ScopedValue` vs `ThreadLocal` semantics.

---

### Week 13: Spring Boot virtual threads integration

**Learning objectives**: Configure Spring Boot 3.2+ for virtual threads. Understand auto-configuration scope and performance implications.

**Core resources**:
- **Spring Boot 3.2 Release Notes** (https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.2-Release-Notes)
- **Baeldung: Working with Virtual Threads in Spring** (https://www.baeldung.com/spring-6-virtual-threads)
- **Bell Software: Guide to Using Virtual Threads with Spring Boot** (https://bell-sw.com/blog/a-guide-to-using-virtual-threads-with-spring-boot/)
- **Benchmarks**: https://github.com/chrisgleissner/loom-webflux-benchmarks

**Configuration (one property)**:
```properties
spring.threads.virtual.enabled=true
```

**Auto-configured components**:
- Tomcat/Jetty request handling
- `@Async` method execution
- `applicationTaskExecutor` bean
- RabbitMQ, Kafka, Redis, Pulsar listeners

**Production lessons from Netflix**:
- Adjust heap size (`-Xmx`)—virtual thread stacks live on heap
- Don't pool virtual threads—defeats their purpose
- Don't cache expensive objects in `ThreadLocal`—creates millions of copies
- Monitor for resource exhaustion (database connections, external API limits)

**Hands-on project**: Migrate a traditional Spring Boot service to virtual threads:
1. Enable virtual threads via property
2. Identify and resolve pinning (check JDBC drivers, caches)
3. Benchmark throughput before/after with JMeter
4. Profile memory with async-profiler

**Milestone**: Achieve **2x** throughput improvement on I/O-bound endpoint. Demonstrate proper HikariCP pool sizing with virtual threads.

---

## Phase 4: Integration and mastery (Weeks 14-16)

### Week 14: Comparative analysis and decision frameworks

**Learning objectives**: Develop systematic criteria for selecting concurrency models. Understand ecosystem compatibility and migration paths.

**Core resources**:
- **Xebia: Will Java Loom Beat Kotlin's Coroutines?** (https://xebia.com/blog/structured-concurrency-will-java-loom-beat-kotlins-coroutines-2/)
- **DEV.to: Java Virtual Threads vs Kotlin Coroutines** (https://dev.to/devsegur/java-virtual-threads-vs-kotlin-coroutines-4ma8)
- **Benchmarks**: https://github.com/gaplo917/coroutine-reactor-virtualthread-microbenchmark

**Decision framework**:

| Factor | Traditional Threads | Virtual Threads | Kotlin Coroutines |
|--------|-------------------|-----------------|-------------------|
| Best for | CPU-bound computation | I/O-bound blocking code | Async workflows, streaming |
| Code changes | Explicit pools | Minimal (same API) | Requires suspend/Flow |
| Debugging | Standard tools | Standard tools | Coroutine-aware debugger |
| Library support | Universal | Growing (check JDBC) | Kotlin ecosystem |
| Spring integration | Native | 3.2+ native | WebFlux-based |

**Where reactive streams fit**: Reactive programming (Project Reactor, RxJava) provides backpressure handling and declarative stream composition that neither virtual threads nor coroutines fully replicate. Use reactive streams when: data naturally streams, backpressure is architecturally critical, or you're building event-driven pipelines. Virtual threads and coroutines excel at request/response patterns where reactive's complexity isn't justified.

**Hands-on analysis**: Take your Week 10 coroutine service and Week 13 virtual thread service. Benchmark identical workloads:
- **1000** concurrent users, **100ms** simulated I/O latency
- Measure throughput, P50/P95/P99 latency, memory footprint
- Document when each approach wins

**Milestone**: Write a decision document for your team recommending concurrency approach for three different service profiles (CPU-intensive batch processor, high-throughput API gateway, real-time event processor).

---

### Week 15-16: Capstone project

**Objective**: Build a production-grade microservice demonstrating mastery across all three concurrency paradigms, deployed to AWS ECS.

**Project: Distributed Rate Limiter Service**

A centralized rate limiting service for microservices architecture supporting:
- **10,000+** requests/second
- Multiple rate limiting algorithms (token bucket, sliding window, leaky bucket)
- Per-client, per-endpoint, and global limits
- Real-time analytics dashboard

**Architecture requirements**:

**Component 1 - Core Rate Limiter (Java concurrency primitives)**:
- Custom `ConcurrentHashMap` with `compute()` for atomic counter updates
- `ReentrantReadWriteLock` for configuration hot-reload
- `CompletableFuture` for async Redis synchronization across instances

**Component 2 - Configuration Management (Kotlin coroutines)**:
- Flow-based configuration streaming from database
- Structured concurrency for configuration validation pipeline
- Coroutine-based REST API for admin interface

**Component 3 - Request Handler (Virtual threads)**:
- Spring Boot 3.2+ with virtual threads for HTTP handling
- Demonstrates scaling to **50,000** concurrent connections
- Proper pinning avoidance in rate limiting checks

**Component 4 - Analytics Pipeline (Choice)**:
- Select coroutines or virtual threads based on your Week 14 analysis
- Justify decision in documentation

**Deliverables**:
1. Working service deployed to AWS ECS (Fargate)
2. Load test results demonstrating **10,000** RPS
3. Comparison document: latency/throughput/resource usage per component
4. Architecture decision records for concurrency model choices
5. Production runbook covering monitoring, debugging, and scaling

**Success criteria**:
- P99 latency under **50ms** at **10,000** RPS
- Zero race conditions under concurrent load testing
- Clean shutdown with proper cancellation propagation
- Comprehensive logging with async-safe context propagation

---

## Debugging and monitoring toolkit

### Profiling tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **async-profiler** | CPU, allocation, lock profiling | Identifying hotspots, memory leaks |
| **IntelliJ Profiler** | Integrated JFR + async-profiler | Development-time profiling |
| **Java Flight Recorder** | Production-safe continuous profiling | Always-on production monitoring |
| **VisualVM** | Quick heap/thread analysis | Initial investigation |

### async-profiler commands
```bash
# CPU profiling for 30 seconds
./profiler.sh -e cpu -d 30 -f profile.html $PID

# Lock contention analysis
./profiler.sh -e lock -d 30 -f locks.html $PID

# Memory allocation profiling  
./profiler.sh -e alloc -d 30 -f alloc.html $PID
```

### JVM flags for debugging
```bash
# Virtual thread pinning detection
-Djdk.tracePinnedThreads=full

# Enhanced profiling accuracy
-XX:+UnlockDiagnosticVMOptions -XX:+DebugNonSafepoints
```

### IntelliJ coroutine debugging

Enable "Async Stack Traces" for debugging across suspension points. The debugger shows the logical call stack even when execution has crossed thread boundaries.

---

## Resource summary by category

### Essential books

1. **"Java Concurrency in Practice"** by Brian Goetz et al. — Non-negotiable foundation
2. **"Kotlin Coroutines: Deep Dive"** by Marcin Moskała — Definitive coroutines reference
3. **"Concurrent Programming in Java"** by Doug Lea — Academic depth on design patterns
4. **"Modern Concurrency in Java"** by A N M Bazlur Rahman — Java 21+ coverage including virtual threads

### Top online courses

1. **Udemy: "Java Multithreading, Concurrency & Performance Optimization"** by Michael Pogrebinsky — Best Java concurrency course
2. **Pluralsight: José Paumard's concurrency series** — Expert-level patterns
3. **Kt. Academy: Coroutines Mastery Workshop** — Official JetBrains-certified training
4. **Udemy: "Kotlin Coroutines and Flow"** by Lukas Lechner — Comprehensive with testing focus

### GitHub repositories for practice

| Repository | Focus |
|------------|-------|
| github.com/leticiamazzoportela/concurrent-programming | Java synchronization exercises |
| github.com/LukasLechnerDev/Kotlin-Coroutines-and-Flow-UseCases-on-Android | Coroutine patterns with tests |
| github.com/chrisgleissner/loom-webflux-benchmarks | Virtual threads vs WebFlux benchmarks |
| github.com/Kotlin/kotlinx.coroutines | Study the source for deep understanding |

### Conference talks (watch in order)

1. Roman Elizarov: "Introduction to Coroutines" (KotlinConf 2017)
2. Roman Elizarov: "Deep Dive into Coroutines on JVM" (KotlinConf 2017)
3. Roman Elizarov: "Kotlin Coroutines in Practice" (KotlinConf 2018)
4. Ron Pressler: "Virtual Threads for Lightweight Concurrency" (InfoQ)
5. José Paumard: "Virtual Threads and Structured Concurrency" (JetBrains livestream)

---

## Success indicators by phase

| Phase | Week | Milestone |
|-------|------|-----------|
| 1 | 2 | Explain JMM happens-before without notes |
| 1 | 5 | Configure ThreadPoolExecutor from scratch for specific workload |
| 2 | 7 | Draw state machine from suspend function bytecode |
| 2 | 10 | Production coroutine service on AWS |
| 3 | 12 | Detect and resolve pinning in existing codebase |
| 3 | 13 | 2x throughput improvement with virtual threads |
| 4 | 14 | Written decision framework for team |
| 4 | 16 | Capstone service at 10,000 RPS with P99 < 50ms |

This curriculum builds genuine mastery through progressive complexity, theoretical depth before implementation, and substantial hands-on projects that exercise understanding under production-like conditions.