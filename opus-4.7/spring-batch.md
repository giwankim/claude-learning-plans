---
title: "Spring Batch Mastery Curriculum"
category: "Spring & Spring Boot"
description: "16-week internals-first plan from Minella's book (Batch 4.x) to production Spring Batch 5.x mastery on Kotlin + Spring Boot 3.x + AWS, with Korean enterprise context (Jenkins, 망분리, SCDF licensing)"
---

# Spring Batch mastery curriculum for gwk

A 16-week, phase-by-phase plan to take you from the middle of Minella's *Definitive Guide to Spring Batch* (2nd ed., 4.x era) to production-grade Spring Batch 5.x mastery on Kotlin + Spring Boot 3.x + AWS. **The plan is internals-first by design** — you will understand JobRepository tables, chunk transaction boundaries, and skip/retry mechanics before you touch scaling, and you will build scaling patterns before you touch orchestration. Every phase has a concrete deliverable project, explicit Korean + global resources, and explicit "when not to use this" guidance. Spring Batch **6.0 GA** shipped Nov 19, 2025 alongside Spring Boot 4 — the plan targets 5.2 as the stable floor and flags 6.0 deltas inline.

**Three licensing/ecosystem realities to internalize before you start:**

- **Spring Cloud Data Flow is no longer open source** as of April 21, 2025 (Broadcom commercial only, per Michael Minella's own blog post). Treat SCDF as a paid Tanzu product — still in the curriculum for literacy, but not as a default recommendation.
- **Jenkins is dominant in Korean enterprises** for batch scheduling, not because it is technically best, but because of 망분리 (network-isolation) constraints, existing CI skillsets, and the post–Spring Batch Admin vacuum. You must be fluent in Jenkins+Spring Batch patterns to ship in Korean fintech/retail.
- **Coroutines are not a good fit with Spring Batch** — Batch's scope proxies, transaction synchronization, and security context all live in ThreadLocals that suspension destroys. Use virtual-thread TaskExecutors (5.1+) instead when you want cheap I/O fan-out.

---

## How to read this curriculum

Each phase lists: **objectives**, **core topics**, **resources** (official docs / Korean + global blogs / talks / GitHub / courses), a **deliverable project**, **enterprise scenarios it addresses**, and **"when NOT to use" notes** where applicable. Weekly budget assumes ~8–10 focused hours per week alongside your day job. If you have less time, stretch to 20 weeks rather than skipping the deliverables — the deliverables are where mastery happens.

Resource legend: 📘 book/reference · 🎥 talk · 🔗 blog · 💻 repo · 🧑‍🏫 course · 🇰🇷 Korean-language.

---

## Phase 0 — Bridge the book to Spring Batch 5.x (Week 1)

**Why this phase exists.** Minella's 2nd edition was written against Spring Batch 4.x. The jump to 5.0 (Nov 2022) was the biggest breaking change in Batch's history: Java 17 baseline, Jakarta EE namespace, `JobBuilderFactory` / `StepBuilderFactory` removed, `DefaultBatchConfigurer` removed, `JobParameters` redesigned with generic types, schema changes to `BATCH_JOB_EXECUTION_PARAMS`, `@EnableBatchProcessing` no longer required (and actually harmful with Spring Boot 3). Before you go further in the book, you must retranslate everything you have already read into 5.x.

**Core topics.**
- **Jakarta EE migration** (`javax.*` → `jakarta.*`) and Hibernate 6.1 knock-on effects for `JpaItemWriter`.
- **`@EnableBatchProcessing` deprecation in Spring Boot 3**: leaving it on your config class actually *disables* Spring Boot's auto-configuration. Remove it unless you explicitly need its attributes (`dataSourceRef`, `isolationLevelForCreate`, etc.).
- **Direct `JobBuilder` / `StepBuilder` usage** — `chunk(int, txManager)` now requires the transaction manager explicitly. Compile-error city if you miss this.
- **`JobParameters` overhaul** — generic `JobParameter<T>`, any type convertible by `ConversionService`, schema change to `PARAMETER_NAME / PARAMETER_TYPE / PARAMETER_VALUE`. Migration scripts in `org/springframework/batch/core/migration/5.0/`.
- **`DefaultBatchConfiguration` replaces `DefaultBatchConfigurer`** as the customization hook.
- **ExecutionContext serializer default changed** from Jackson to Base64 Java serialization (`DefaultExecutionContextSerializer`). To keep JSON, add `jackson-core` *and* wire `Jackson2ExecutionContextStringSerializer` explicitly.
- **Listener support classes deprecated** in favor of Java 8 default methods. `ItemWriter.write(List)` → `write(Chunk)`.
- **Virtual threads in 5.1+**: `VirtualThreadTaskExecutor` for multi-threaded / partitioned steps.
- **5.2 additions** you will use later: `CompositeItemReader`, `SupplierItemReader`/`ConsumerItemWriter`, `BlockingQueueItemReader/Writer` (SEDA), MongoDB `JobRepository`, `ResourcelessJobRepository`.
- **6.0 deltas (awareness only)**: `@EnableBatchProcessing` decoupled from JDBC; new `@EnableJdbcJobRepository` / `@EnableMongoJobRepository`; graceful shutdown; JSpecify null-safety; lambda-based builders.

**Resources.**
- 📘 [Spring Batch 5.0 Migration Guide (GitHub wiki)](https://github.com/spring-projects/spring-batch/wiki/Spring-Batch-5.0-Migration-Guide) — **the single most important document for this phase.** Read twice.
- 🎥 [Mahmoud Ben Hassine — "What's new in Spring Batch 5" (Spring I/O 2023)](https://www.youtube.com/watch?v=xoPPTawF_vY) — 1-hour overview from the current project lead.
- 🔗 [Spring Batch 5.0 GA](https://spring.io/blog/2022/11/24/spring-batch-5-0-goes-ga/) · [5.1 GA](https://spring.io/blog/2023/11/23/spring-batch-5-1-ga-5-0-4-and-4-3-10-available-now/) · [5.2 GA](https://spring.io/blog/2024/11/20/spring-batch-5-2-0-goes-ga/)
- 🔗 [OpenRewrite Batch 4→5 migration recipe](https://docs.openrewrite.org/recipes/java/spring/batch/springbatch4to5migration) — authoritative machine-checkable change list; use it to audit legacy code you inherit.
- 💻 [Michael Minella — `batch-kotlin-example`](https://github.com/mminella/batch-kotlin-example) — the author's own minimal Kotlin+Batch sample.

**Deliverable project: "Hello 5.x" retro-port.**
Take the CSV-to-DB example from Minella's Chapter 4 (or whatever you have most recently read) and port it to:
- Kotlin 2.x + Spring Boot 3.x + Spring Batch 5.2
- Gradle Kotlin DSL with `kotlin("plugin.spring")`, `kotlin("plugin.jpa")` and explicit `allOpen { annotation("jakarta.persistence.Entity") … }`
- Direct `JobBuilder` / `StepBuilder` wiring, **no** `@EnableBatchProcessing`
- PostgreSQL via Testcontainers for `BATCH_*` metadata
- Pass `businessDate` as a `LocalDate` JobParameter (impossible in 4.x)

Commit this repo as `spring-batch-mastery-p0-helloport`. You will reuse the skeleton.

**Enterprise scenario.** You have inherited 4.x jobs and must migrate the fleet. Output of this phase: a decision tree you can share with your team for "how to migrate a 4.x job."

---

## Phase 1 — Internals deep dive: JobRepository, transactions, skip/retry (Weeks 2–3)

**Why internals first.** Every difficult Spring Batch bug you will ever hit — restart failing with `UNKNOWN`, a chunk committing half its items, SkipListener not firing, deadlocks on `BATCH_JOB_EXECUTION_PARAMS` — traces back to misunderstanding the JobRepository schema, chunk transaction boundaries, or the skip/retry cache. You cannot reason your way out without this foundation.

**Core topics.**
- **JobRepository schema** (six tables): `BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION`, `BATCH_JOB_EXECUTION_PARAMS`, `BATCH_JOB_EXECUTION_CONTEXT`, `BATCH_STEP_EXECUTION`, `BATCH_STEP_EXECUTION_CONTEXT` + sequences. Understand **`JOB_KEY`** = hash of *identifying* parameters only.
- **Isolation level for create.** Default `ISOLATION_SERIALIZABLE` prevents concurrent launchers from creating the same JobInstance, but causes `CannotSerializeTransactionException` on Postgres/Oracle under concurrent launches. Override via `spring.batch.jdbc.isolation-level-for-create=READ_COMMITTED` when safe.
- **ExecutionContext persistence:** `SHORT_CONTEXT VARCHAR(2500)` preview + `SERIALIZED_CONTEXT TEXT/CLOB`. Rule: **store only primitives (ids, offsets, counts) in ExecutionContext**. If you see MySQL "Data too long for column SERIALIZED_CONTEXT", you are doing it wrong.
- **JobLauncher sync vs async.** The interface makes **no guarantee** — `TaskExecutorJobLauncher` with `SyncTaskExecutor` blocks, with a thread-pool executor returns immediately with `STARTING`. HTTP launches should always be async.
- **BatchStatus state machine:** `STARTING → STARTED → COMPLETED | FAILED | STOPPED | ABANDONED | UNKNOWN`. Learn when each happens, especially `UNKNOWN` (post-commit metadata write failed; not restartable) and `ABANDONED` (manual via `JobOperator.abandon`; step skipped on restart).
- **BatchStatus vs ExitStatus** — distinct. `ExitStatus` is a rich string used in flow transitions (`.on("COMPLETED WITH SKIPS").to(x)`).
- **Chunk transaction topology:** one transaction wraps the chunk loop `read*→process*→write(Chunk)`. Metadata update commits on the same transaction. Reads for non-transactional readers happen outside the TX.
- **Skip/retry mechanics** — the critical one to internalize:
  - On a skippable exception **during write**, the chunk TX rolls back, then Batch **replays items one-by-one** in mini-chunks of 1 to identify the offender. `processor-transactional=false` makes this cheap by caching processed outputs.
  - `readerIsTransactionalQueue()` tells Batch NOT to buffer items on rollback (use for JMS, *not* for DB cursors).
  - `SkipListener.onSkip*` is called **exactly once per skipped item, just before commit**, inside the would-commit chunk TX.
  - `noRollback(Exception.class)` disables rollback on write exception — dangerous.
- **Restart mechanics:** framework looks up last failed `StepExecution`, loads its ExecutionContext, calls `ItemStream#open(ctx)` on readers, which seek to saved position. `Step.setAllowStartIfComplete(true)` forces re-run of a completed step.
- **Tasklet vs ChunkOrientedTasklet.** Each tasklet iteration is its own TX.
- **ItemReader contract**: stateful, **return null to signal end-of-input**, not thread-safe by default. ItemProcessor returning null = filter. ItemWriter is always called with full chunk.
- **Listener lifecycle** — in particular, `ChunkListener.afterChunk()` is called even on rollback; use `afterChunkError` to distinguish.

**Resources.**
- 📘 [Spring Batch Reference — Transaction appendix](https://docs.spring.io/spring-batch/reference/5.1-SNAPSHOT/transaction-appendix.html) — nothing else explains skip/retry this precisely.
- 🔗 [Codecentric — Transactions in Spring Batch Part 3: Skip and Retry](https://www.codecentric.de/knowledge-hub/blog/transactions-in-spring-batch-part-3-skip-and-retry) — walks through exactly what rolls back and when.
- 🔗 [Codecentric — BatchStatus state transitions](https://www.codecentric.de/wissens-hub/blog/spring-batch-batchstatus-state-transitions)
- 📘 [Spring Batch Reference — Configuring the JobRepository](https://docs.spring.io/spring-batch/reference/job/configuring-repository.html)
- 🧑‍🏫 [Spring Academy — Building a Batch Application with Spring Batch (Ben Hassine)](https://spring.academy/courses/building-a-batch-application-with-spring-batch) — **free**, taught by the project lead on 5.x. Do this instead of old Udemy courses.
- 🇰🇷 🔗 [토스 — Spring JDBC 성능 문제, 네트워크 분석으로 파악하기](https://toss.tech/article/25029) — 18분→2분 개선 post-mortem; excellent "why you must know the internals" read.
- 🇰🇷 🔗 [우아한형제들 — 주소검색서버 개발기](https://techblog.woowahan.com/2575/) — 2천만+ rows 이 JobInstance 복구에 의존하는 실례.

**Kotlin-specific pitfalls to wire in this phase.**
- **`kotlin("plugin.spring")` is mandatory** for any `@Configuration` / `@Component`-bearing class or you will get `@Configuration class may not be final`. This is the #1 first-run crash for Kotlin+Batch.
- **Entity classes need explicit all-open for `jakarta.persistence.Entity`** — Kotlin Spring Initializr does NOT set this up. Without it Hibernate can't lazy-proxy, silently turning associations eager and causing N+1 in batch readers.
- **`@StepScope` on `@Bean fun x(): LocalDate`** will fail with CGLIB proxy error (`LocalDate` is final). Wrap in a scoped Kotlin class.
- **Null safety in readers.** `override fun read(): Customer?` — the `?` is not optional. Returning a non-null sentinel value creates a step that runs forever.

**Deliverable project: "Internals lab".**
Build a CLI tool (`spring-batch-mastery-p1-internals-lab`) that:
1. Takes a CSV of 100k rows, processes them, writes to Postgres.
2. Deliberately includes 10 rows that will fail validation. Configure `faultTolerant().skipLimit(15).skip(ValidationException::class.java)`.
3. Implements a `SkipListener` that writes to a `batch_dlt` table with `jobExecutionId`, the offending row, and exception class.
4. Has a `--crash-at N` mode that throws in the writer at chunk boundary N to force a FAILED JobExecution.
5. On restart, verifies exactly the remaining rows are processed; writes a markdown report of `BATCH_STEP_EXECUTION.READ_COUNT`, `WRITE_COUNT`, `SKIP_COUNT`, `ROLLBACK_COUNT` before and after.
6. Runs `EXPLAIN` on the actual queries Spring Batch issues against `BATCH_*` tables (enable JDBC SQL logging).

You will look at the six `BATCH_*` tables in pgAdmin and see exactly what changed after each failed/restarted/abandoned run. This is the phase where the abstraction becomes concrete.

**Enterprise scenarios addressed.** Dirty data ingestion with restart (retailers ingesting product catalogs), financial jobs that must resume from exact failure point, any job where silent skips would be a compliance issue.

---

## Phase 2 — Readers, writers, and the JPA-in-batch problem (Weeks 4–5)

**Objectives.** Build an internal taxonomy of every reader/writer, know which ones to avoid at scale, and internalize why JPA-in-batch is a footgun without care.

**Core topics.**
- **`JdbcCursorItemReader` vs `JdbcPagingItemReader`.** Cursor streams one resultset; paging issues fresh LIMIT/OFFSET queries.
  - **MySQL cursor streaming gotcha:** you MUST set `useCursorFetch=true` in the JDBC URL + `setFetchSize(N)`, OR use `Integer.MIN_VALUE` row-by-row mode. Otherwise the driver loads the entire table into memory — a 50 GB table OOMs your pod.
  - **PostgreSQL cursor streaming gotcha:** requires `autoCommit=false` on the connection. Hikari's `auto-commit: false` is the clean way.
- **`JpaPagingItemReader` / `RepositoryItemReader` at scale.** KakaoPay's 2022 post proves they fail: `LIMIT 50000000, 100` is terrible even with a perfect index because MySQL has to skip 50M rows. **Solution: no-offset / covering-index / seek-method pagination** using last-seen PK (`WHERE id > :lastId ORDER BY id LIMIT :chunk`).
- **Querydsl / Exposed custom readers.** Woowahan's `QuerydslPagingItemReader` and `QuerydslNoOffsetPagingItemReader` patterns, KakaoPay's `ZeroOffsetItemReader` and `ExposedCursorItemReader` — these are the canonical Korean patterns.
- **Composite readers/writers.** 5.2's new `CompositeItemReader` (sequential delegation). `ClassifierCompositeItemProcessor` / `ClassifierCompositeItemWriter` for per-type routing — common in real settlement pipelines.
- **Synchronized wrappers.** `SynchronizedItemStreamReader` / `SynchronizedItemStreamWriter`. Trade-off: makes a non-thread-safe reader usable on multi-threaded step but breaks restartability.
- **File-based readers.** `FlatFileItemReader` (CSV, TSV, fixed-width with `FixedLengthTokenizer`), `StaxEventItemReader` (XML, streaming), `JsonItemReader` (Jackson), `MultiResourceItemReader` for daily file drops.
- **Kafka readers/writers.** `KafkaItemReader` (manual offset commit at chunk boundary), `KafkaItemWriter` (batch produce). Chunk boundary = offset commit boundary, which is the batch↔streaming bridge.
- **Redis readers/writers** (5.1+) via Spring Data Redis. Useful for intermediate-state pipelines.
- **JpaItemWriter without pain.** Set `hibernate.jdbc.batch_size`, `hibernate.order_inserts`, `hibernate.order_updates` (all three, or batching silently doesn't happen). `GenerationType.IDENTITY` **disables** insert batching — use `SEQUENCE` on Postgres or compute IDs yourself. At chunk end, `flush(); clear()` to release first-level cache.
- **StatelessSession for pure batch writes.** No dirty checking, no first-level cache, supports batching and `INSERT … RETURNING` for generated IDs. This is the path Kurly and high-throughput settlement jobs take.
- **`LazyInitializationException` at step boundary.** The reader's persistence context closes when the chunk TX commits; processor/writer see detached entities. Fix: fetch-joins in the reader query, or project to DTOs in the reader. **Do not** reach for `OpenEntityManagerInView` — it holds sessions across threads, breaks virtual threads, and shows up as a connection leak in Hikari metrics.
- **Kotlin entity gotcha recap**: don't use `data class` as JPA entity — the generated `equals`/`hashCode` hashes a lazy proxy → `LazyInitializationException`. Use plain classes with ID-based equality.

**Resources.**
- 🇰🇷 🔗 [KakaoPay — Batch Performance를 고려한 최선의 Reader](https://tech.kakaopay.com/post/ifkakao2022-batch-performance-read/) · [Speaker deck](https://speakerdeck.com/kakao/batch-performance-geughaneuro-ggeuleoolrigi) — **the single best Korean internals read on readers at 1억 건 scale.**
- 🇰🇷 🔗 [KakaoPay — Batch Performance를 고려한 최선의 Aggregation](https://tech.kakaopay.com/post/ifkakao2022-batch-performance-aggregation/) — don't push aggregation into SQL.
- 🇰🇷 🔗 [우아한형제들 — Spring Batch와 Querydsl](https://techblog.woowahan.com/2662/)
- 🇰🇷 🔗 [Kurly — BULK 처리 Write에 집중해서 개선해보기](https://helloworld.kurly.com/blog/bulk-performance-tuning/) + [test code repo](https://github.com/thefarmersfront/bulk-performance-tuning/) — "JPA saveAll() ≠ bulk" demonstration.
- 🔗 [Vlad Mihalcea — MySQL ResultSet streaming](https://vladmihalcea.com/how-does-mysql-result-set-streaming-perform-vs-fetching-the-whole-jdbc-resultset-at-once/)
- 🔗 [Vlad Mihalcea — Hibernate StatelessSession](https://vladmihalcea.com/hibernate-statelesssession-jdbc-batching/)
- 💻 [Spring Batch official samples](https://github.com/spring-projects/spring-batch/tree/main/spring-batch-samples) — JDBC cursor/paging, JPA, AMQP, composite, skip/retry, restart.
- 💻 [Spring Batch Extensions](https://github.com/spring-projects/spring-batch-extensions) — bigquery, elasticsearch, excel (POI streaming), neo4j, notion, s3.
- 🔗 [Josh Long — Spring Tips: Spring Batch and Apache Kafka](https://spring.io/blog/2019/05/15/spring-tips-spring-batch-and-apache-kafka/)

**Deliverable project: "Reader zoo + reconciliation".**
`spring-batch-mastery-p2-reconciliation`: a two-source reconciliation job.
- **Source A:** 5M row MySQL table, read with no-offset paging (implement your own Kotlin `NoOffsetPagingItemReader<Order>` inspired by the Woowahan / KakaoPay patterns).
- **Source B:** daily CSV drop on S3, read via `MultiResourceItemReader` + `FlatFileItemReader`.
- **Step 1** loads A into staging via `StatelessSession` writer (measure: rows/sec vs a naive `JpaItemWriter` with IDENTITY — demonstrate the difference).
- **Step 2** loads B into staging via `JdbcBatchItemWriter`.
- **Step 3** reconciles with a `ClassifierCompositeItemWriter` routing matched/unmatched/conflicting rows to three separate tables.
- Measure chunk size sensitivity: run with 50, 500, 5000 and plot throughput.
- Include a restart test: kill the process at step 2, restart, assert only remaining items processed.

**Enterprise scenarios addressed.** Daily order reconciliation (delivery ↔ payment ↔ refund), CDC replay into analytics DB, file-and-DB merge for commerce catalogs.

---

## Phase 3 — Scaling I: multi-threaded, parallel, local partitioning (Week 6)

**Objectives.** Master single-JVM scaling and know exactly when to stop.

**Core topics.**
- **Multi-threaded step** via `.taskExecutor(taskExecutor)`. Thread-safety rules: `FlatFileItemReader`, `JdbcCursorItemReader`, `StaxEventItemReader` are **not** thread-safe; `JdbcPagingItemReader`, `JpaPagingItemReader`, `RepositoryItemReader` (paging) are. Synchronize explicitly when needed; accept the restartability trade-off.
- **Parallel steps** via `FlowBuilder.split(taskExecutor)`. For independent sub-phases, not for one big step over one big dataset.
- **Virtual-thread TaskExecutor (5.1+)** — `VirtualThreadTaskExecutor` can replace a `ThreadPoolTaskExecutor` in most places. Caveat: JDBC pinning on older drivers pins the carrier thread. Under load, verify via JFR.
- **Local partitioning** with `TaskExecutorPartitionHandler`. Grid-sizing rule of thumb: `gridSize ≈ 2 × vCPU` for CPU-bound; `≈ 1 × vCPU` for DB-bound. Must satisfy `gridSize × connectionsPerWorker < AuroraMaxConnections / 2`.
- **Skew kills partitioning.** Simple `id % N` partitioning defeats itself when data is skewed. Use histogram-based range partitioning.
- **Toss's modular-arithmetic anti-duplicate pattern.** Each thread owns a disjoint slice of transaction IDs — no synchronization overhead, no duplicate settlement.

**Resources.**
- 📘 [Spring Batch Reference — Scalability](https://docs.spring.io/spring-batch/reference/scalability.html)
- 💻 [Michael Minella — scaling-demos](https://github.com/mminella/scaling-demos) — side-by-side of every scaling mode.
- 🎥 [Minella + Ben Hassine — High Performance Batch Processing (InfoQ/SpringOne)](https://www.infoq.com/presentations/batch-performance-spring-4-1/) — depth from both project leads.
- 🇰🇷 🔗 [Toss — 레거시 정산 개편기](https://toss.tech/article/42671) — modular-arithmetic partitioning at 수조원 daily scale.
- 🇰🇷 🔗 [KakaoPay — Spring Batch 애플리케이션 성능 향상을 위한 주요 팁](https://tech.kakaopay.com/post/spring-batch-performance/) — Kotlin + Exposed + RxKotlin; chunk-size × I/O amplification.
- 🇰🇷 🔗 [우아한형제들 — 누구나 할 수 있는 10배 더 빠른 배치 만들기](https://techblog.woowahan.com/13569/) — **before reaching for threads, fix the N+1.** Knuth's premature-optimization warning.

**Deliverable project: "Settlement partition benchmark".**
Extend Phase 2's job: turn Step 1 (load A into staging) into a **locally-partitioned** step with `ColumnRangePartitioner` keyed on `order_id`. Run benchmarks at gridSize = 1, 2, 4, 8, 16. Produce a short markdown report:
- Wall-clock time vs grid size (is it linear? where does it break?)
- Aurora writer CPU vs grid size
- Hikari pool saturation per grid size
- Skew analysis: is partition 1 finishing 10× faster than partition 7?

This is how you learn grid-sizing by feel, not by folklore.

**When NOT to scale yet.** As Woowahan post #12 teaches: if your slow batch has a JPA N+1, or you're hitting the DB 5000 times when you could issue a single `UPDATE ... WHERE id IN (...)`, you are threading a broken design. Fix the design first.

---

## Phase 4 — Scaling II: remote chunking and remote partitioning (Weeks 7–8)

**Objectives.** Understand the two patterns at the Spring Integration message-flow level, build both with Kafka, and be able to choose between them in 30 seconds on a whiteboard.

**Decision framework.**
- **Remote chunking:** reader cheap, processor/writer expensive → master reads, serialized items cross wire to workers. Requires durable broker. I/O heavy (items on the wire).
- **Remote partitioning:** reader itself is expensive or data too big for one node → master assigns *metadata* partitions (min/max ID ranges, filenames) to workers, workers do their own reading and writing, workers need JobRepository access. I/O light (only metadata crosses wire). Broker durability optional.

**Core topics.**
- **`@EnableBatchIntegration`** registers `RemoteChunkingManagerStepBuilderFactory`, `RemoteChunkingWorkerBuilder`, `RemotePartitioningManagerStepBuilderFactory`, `RemotePartitioningWorkerStepBuilderFactory`.
- **ChunkMessageChannelItemWriter** — replaces the writer on the master; dispatches `ChunkRequest<T>` messages.
- **Worker-side `ChunkProcessorChunkHandler`** — executes real processor + writer; returns `ChunkResponse`.
- **Kafka vs RabbitMQ vs SQS as transport.** Kafka: partition-ordered, high throughput; RabbitMQ: richer routing, simpler DLQ; SQS: managed but no strict ordering on standard queues (FIFO exists).
- **Serialization formats.** JSON with type info, Avro, Protobuf. Kryo is brittle across versions — avoid.
- **Back-pressure and DLQ.** Manager can drown workers. Tune chunk size, broker partition count, `max.poll.records`, `ChunkMessageChannelItemWriter.setMaxWaitTimeouts()`. DLQ is mandatory for poison items.
- **Exactly-once is a lie.** XA across Kafka+JDBC is effectively unsupported; design idempotent writers instead (INSERT … ON CONFLICT, deterministic keys).
- **MessageChannelPartitionHandler** for messaging-based remote partitioning.
- **DeployerPartitionHandler (Spring Cloud Task)** — launches worker JVMs/pods on demand. **Caveat:** Spring Cloud Deployer Kubernetes is in the SCDF-commercial bucket as of April 2025; prefer messaging-based partitioning for new OSS projects.
- **K8s-native partitioning** where the manager uses the Kubernetes API to create worker Jobs. Watch for pod cleanup and startup cost (pod startup can dominate short partitions — prefer longer, fewer partitions).

**Resources.**
- 📘 [Spring Batch Reference — Spring Batch Integration](https://docs.spring.io/spring-batch/reference/spring-batch-integration.html)
- 🔗 [Arnold Galovics — Spring Batch remote partitioning with Kafka](https://arnoldgalovics.com/spring-batch-remote-partitioning-kafka/)
- 💻 [galovics/spring-batch-remote-partitioning](https://github.com/galovics/spring-batch-remote-partitioning) — clean example with both Kafka and SQS via docker-compose.
- 💻 [jchejarla/spring-batch-db-cluster-partitioning](https://github.com/jchejarla/spring-batch-db-cluster-partitioning) — DB-coordinated partitioning with heartbeats; for shops that can't use a broker (common in banks).
- 💻 [ddubson/spring-batch-examples](https://github.com/ddubson/spring-batch-examples) — Kotlin, local & remote partitioning (RabbitMQ), remote chunking.
- 🇰🇷 🔗 [Kurly — 컬리 검색이 카프카를 들여다본 이야기 1](https://helloworld.kurly.com/blog/search-system-with-kafka-1/) — batch-to-streaming mental model.

**Deliverable project: "Remote partitioning over Kafka on docker-compose".**
`spring-batch-mastery-p4-remote-partition`:
- Docker-compose with Kafka (Confluent 7.x), Postgres for shared JobRepository.
- One master Spring Boot app + three worker Spring Boot apps (same uber-jar, distinct `--spring.profiles.active`).
- Partitioner splits 50M rows by `customer_id` range into 32 partitions.
- Worker step includes a deliberate 5-second sleep per chunk to simulate CPU-heavy processing — you want to see the horizontal scaling payoff.
- Testcontainers integration test that spins up master + workers in a single JVM with distinct profiles, asserts `stepExecutions.size == 33` (32 partitions + 1 manager) and all complete.
- Document DLQ strategy and what happens if a worker crashes mid-partition (JobRepository lets manager re-run only the FAILED StepExecution on restart — demonstrate).

---

## Phase 5 — Deployment landscape & decision framework (Week 9)

**Objectives.** Be able to justify a scheduling choice to a skeptical TL in under two minutes. Deploy the Phase 4 job three different ways.

**The 15 options you must know (summary).**

| Option | When it wins | When it loses | License |
|---|---|---|---|
| Single-JVM Spring Batch | Fits one node, runtime < 1h | CPU-bound, big data | Apache 2.0 |
| Multi-threaded step | Thread-safe reader, CPU-bound | Non-thread-safe reader + restart needed | Apache 2.0 |
| Parallel steps (split flow) | Independent sub-phases | One big step on big data | Apache 2.0 |
| Remote chunking | Cheap read + heavy process | Read is the bottleneck | Apache 2.0 + broker |
| Local partitioning | Big step fits one big node | Need cross-node isolation | Apache 2.0 |
| Remote partitioning | Data too big for one node | Simple jobs | Apache 2.0 (+ deployer going commercial) |
| **K8s CronJob on EKS** | Standard K8s platform, simple cron | Complex DAGs, backfill | OSS |
| SCDF | Already pay for Tanzu | **Greenfield in 2026** (commercial only) | **Broadcom commercial** |
| **Jenkins** | **Korean enterprise, 망분리, existing skillset** | Complex DAGs | MIT / CloudBees commercial |
| AWS Batch | Thousands of jobs, Spot, auto-scale | Small job count | AWS managed |
| ECS Scheduled Tasks | 1–20 simple recurring jobs | DAG, Spot, priority | AWS managed |
| AWS Step Functions | Multi-step DAG, audit trail | Ultra-high-TPS fan-out | AWS managed |
| Quartz | Many short high-frequency jobs, complex cron | Short-lived container model | Apache 2.0 |
| Airflow | Cross-system DAGs, Python team | Pure Java shop, simple crons | Apache 2.0 (MWAA paid) |
| Linux cron | Never for new work | Basically anywhere else | OSS |

**Core K8s-on-EKS best practices** (you must internalize these before shipping):
1. One job per pod, exec-form ENTRYPOINT, `System.exit(SpringApplication.exit(SpringApplication.run(...)))` so SIGTERM yields a clean `FAILED` status.
2. `concurrencyPolicy: Forbid`, `parallelism: 1`, `completions: 1`, `backoffLimit: 0` or `1`.
3. `spec.timeZone: Asia/Seoul` on K8s 1.27+ — otherwise you're on UTC and your 새벽 2시 batch runs at 오전 11시.
4. `terminationGracePeriodSeconds` ≥ longest chunk commit (60–300s). Spring Boot `server.shutdown=graceful` + `spring.lifecycle.timeout-per-shutdown-phase=30s`.
5. **No liveness probe** for batch pods. Readiness if you need it, or disable web (`spring.main.web-application-type=none`).
6. Always add a unique `runId` or timestamp to identifying JobParameters.
7. Resource requests = limits. `-XX:MaxRAMPercentage=75` (default since JDK 10 under `UseContainerSupport`).
8. FluentBit DaemonSet for logs (pod dies, logs go with it otherwise).

**Jenkins patterns for Korean enterprise:**
- Separate Jenkins controller for batch vs CI/CD (이동욱's guidance from 우아한테크세미나).
- Parameterized builds; `${BUILD_TIMESTAMP}` or `${BUILD_NUMBER}` as identifying JobParameter; "Do not allow concurrent builds" ON.
- `withCredentials { }` for Aurora password; never `echo $PASSWORD`; `set +x` around credential use.
- Jenkins agents labelled `batch-runner`, dedicated, on stable nodes.
- HA via active/passive on shared `JENKINS_HOME` over EFS; or CloudBees CI.
- Spring Batch Admin is deprecated — build a custom Actuator-backed dashboard reading from `BATCH_*`, or use Woowahan's Jenkins-API pattern (post #16) for activation-aware monitoring.

**Idempotent launches — layered defense.**
1. App: identifying JobParameters include unique `runId`.
2. DB: unique `(JOB_NAME, JOB_KEY)` constraint enforced by Spring Batch; consider `pg_advisory_lock` around launch for critical jobs (issue #3966 edge case).
3. Scheduler: K8s `parallelism: 1`, Jenkins "no concurrent builds", Quartz `@DisallowConcurrentExecution`.
4. Recovery: a startup `CommandLineRunner` that marks stale `STARTED` executions `FAILED` (abandoned-pod detection).
5. ShedLock as extra belt-and-braces for cross-JVM exclusion.

**Resources.**
- 🔗 [Ben Hassine — Spring Batch on Kubernetes: Efficient batch processing at scale (2021)](https://spring.io/blog/2021/01/27/spring-batch-on-kubernetes-efficient-batch-processing-at-scale/) — **the canonical production K8s essay.**
- 🔗 [Minella — Spring Cloud Data Flow Commercial Transition (2025-04-21)](https://spring.io/blog/2025/04/21/spring-cloud-data-flow-commercial/) — read this once; do not start new SCDF projects unless you own Tanzu.
- 📘 [Spring Cloud Data Flow — Batch Developer Guides](https://dataflow.spring.io/docs/batch-developer-guides/batch/spring-batch/) (for context / existing-SCDF operators only).
- 💻 [srirajk — K8s deployment strategies gist](https://gist.github.com/srirajk/c7b5eca2b511bf20345c119e7d2dc950) — three strategies compared.
- 🇰🇷 🔗 [Toss Payments — 수천 개의 API/BATCH 서버를 하나의 설정 체계로 관리하기](https://toss.tech/article/payments-legacy-8) — **Jenkins-centric, declarative config generation, 50억 won 오타 교훈.**
- 🇰🇷 🔗 [우아한형제들 — 정산 신병들 (Jenkins + Beanstalk + Querydsl)](https://techblog.woowahan.com/2711/)
- 🇰🇷 🔗 [Bucketplace — Airflow 도입기](https://www.bucketplace.com/post/2021-04-13-버킷플레이스-airflow-도입기/) — "왜 Spring Batch 대신 Airflow" 관점.
- 🔗 [Spring Cloud Task 3.3+ reference](https://docs.spring.io/spring-cloud-task/reference/) — remains OSS, useful even without SCDF.
- 🎥 [KakaoPay — K8s SCDF 백업·정산 파이프라인](https://tv.kakao.com/channel/3693125/cliplink/414072537) — for SCDF literacy; now history, but the mental model transfers.

**Deliverable project: "Three ways to ship the same job".**
Take the Phase 4 remote-partitioning job and deploy it three ways:

1. **EKS CronJob** with proper signal handling, `spec.timeZone: Asia/Seoul`, IRSA for Aurora+MSK, FluentBit logs to CloudWatch.
2. **Jenkins pipeline** (Jenkinsfile) that `kubectl create job --from=cronjob/batch-template` with `BUILD_TIMESTAMP` as the unique JobParameter. Credentials via `withCredentials`. Separate controller node pool or label. Pipeline-as-code.
3. **AWS Step Functions** state machine (Standard workflow, CDK or SAM) that submits an AWS Batch Fargate job wrapping the same uber-jar. Use `.sync` integration to wait for completion; route failures to SNS.

Write a short comparison doc (you'll reuse it in interviews): startup time, operational burden, cost per run, Korean enterprise fit, failure-recovery behavior.

---

## Phase 6 — Observability and SRE-grade ops (Week 10)

**Objectives.** Wire metrics, tracing, MDC-correlated structured logs, and alerts so your batch SRE is not blind.

**Core topics.**
- **Spring Batch Micrometer metrics** (auto-exported in 5.x): `spring.batch.job` (timer), `spring.batch.job.active` (long-task-timer), `spring.batch.step`, `spring.batch.step.active`, `spring.batch.item.read`, `spring.batch.item.process`, `spring.batch.chunk.write`. Tags `name`, `status`, `job.name`, `step.name`.
- **The 5.x tag-renaming inconsistency.** `spring.batch.job` uses tag `spring.batch.job.name`; `spring.batch.step` uses `spring.batch.step.job.name`. For Grafana template variables to work, register `MeterFilter.renameTag` beans to normalize both to `job.name`. (Per Trifork blog — this gotcha is not in the official docs.)
- **No built-in `/actuator/batch` endpoint.** Use `/actuator/metrics`, `/actuator/prometheus`, `/actuator/health`, `/actuator/loggers` (hot log-level change for a stuck job), `/actuator/threaddump`, `/actuator/heapdump`.
- **OpenTelemetry via Micrometer Observation API** (5.x). Every job/step/chunk becomes a span; Kafka-based remote chunking/partitioning propagates W3C `traceparent` headers automatically via spring-kafka instrumentation. Wire `micrometer-tracing-bridge-otel` + `opentelemetry-exporter-otlp`.
- **Prometheus scraping for ephemeral pods.** Pull is fine if the pod lives longer than 2× scrape interval; otherwise push. **Pushgateway pitfalls** (memorize these):
  - Stale metrics are never expired — a last-success=1 sits forever.
  - Not for per-pod instance labels.
  - Single point of failure.
  - No built-in auth.
  - DELETE on job completion, or schedule cleanup by `push_time_seconds`.
- **Cleaner path:** push OTLP metrics from the pod to an OpenTelemetry Collector, Collector to Prometheus remote-write. No Pushgateway.
- **Custom skip-count metric.** Spring Batch does not expose `SKIP_COUNT` as a Micrometer meter by default. Register a `MeterBinder` that reads `StepExecution.skipCount` in `afterStep`.
- **HikariCP metrics** — `hikaricp.connections.active`, `hikaricp.connections.pending`, `hikaricp.connections.usage`, `hikaricp.connections.acquire`. Correlating pool saturation with chunk duration is how you find Aurora-proxy connection-timeout issues.
- **Structured logging with MDC.** Logback + `LogstashEncoder`. Inject `job.name`, `job.instanceId`, `job.executionId`, `step.name`, `step.executionId` via `JobExecutionListener` / `StepExecutionListener`. For multi-threaded / partitioned steps, wrap the `TaskExecutor` with an MDC-propagating decorator.
- **Alert rules worth having.**
  - SLA wall-clock breach: `spring_batch_job_active_duration_seconds{job_name="nightly_billing"} > 3600`.
  - Failure rate: `increase(spring_batch_job_seconds_count{status="FAILURE"}[10m]) > 0`.
  - Skip-threshold exceeded (from your custom meter).
  - **Zero-items-read silent failure**: `spring_batch_item_read_seconds_count{status="SUCCESS",job_name="daily_ingest"} == 0` after job end.
  - Stuck job: `BATCH_JOB_EXECUTION.status == STARTED` for > 2× expected runtime (sidecar that queries JobExplorer and exports a gauge).

**Resources.**
- 📘 [Spring Batch Reference — Monitoring and Metrics](https://docs.spring.io/spring-batch/reference/5.2/monitoring-and-metrics.html)
- 📘 [Spring Batch Reference — Micrometer Observability](https://docs.spring.io/spring-batch/reference/spring-batch-observability/micrometer.html)
- 🔗 [Trifork — Spring Boot observability for Spring Batch jobs](https://trifork.nl/blog/spring-boot-observability-spring-batch-jobs/) — **the tag-renaming post, indispensable.**
- 🔗 [Spring Blog — OpenTelemetry with Spring Boot (2025)](https://spring.io/blog/2025/11/18/opentelemetry-with-spring-boot/)
- 🔗 [Prometheus — Pushing metrics (Pushgateway pitfalls)](https://prometheus.io/docs/practices/pushing/)
- 📘 [SCDF monitoring guide](https://dataflow.spring.io/docs/feature-guides/batch/monitoring/) — RSocket proxy pattern for short-lived tasks.
- 🇰🇷 🔗 [우아한형제들 — Jenkins API 기반 배치 모니터링 대시보드](https://techblog.woowahan.com/2722/) — activation-aware (불포함된 빌드 감지).
- 🇰🇷 🔗 [Kurly — WMS 피킹팀 MDC + AOP Datadog 통합](https://helloworld.kurly.com/blog/squad-b-team-building/)
- 🇰🇷 🔗 [우아한형제들 — Config Checker](https://techblog.woowahan.com/7242/) — Hikari/Spring misconfig prevention at org level.

**Deliverable project: "Observability overlay".**
Add to the Phase 5 EKS deployment:
- Micrometer `MeterFilter` beans for the tag-renaming fix.
- OTLP tracing exporter → OpenTelemetry Collector (local in docker-compose, Tempo-compatible in staging).
- Logback JSON + MDC listeners (job, instance, execution, step, trace/span IDs).
- Grafana dashboard JSON committed to repo: 8 panels (throughput, duration p50/p95/p99, active jobs, failures, skip count, Hikari saturation, GC pause, job history table).
- 5 Prometheus alert rules committed as YAML.
- Demonstrate a tracing drill-down: one slow job, click span → see the offending chunk write, see the Hikari pool saturation at that minute.

**When this is overkill.** A once-a-week log-rotation job run by `systemd timer` does not need OTLP. Scope observability to the SLA.

---

## Phase 7 — Testing Spring Batch like a grown-up (Week 11)

**Objectives.** Write integration tests that are fast, deterministic, realistic (real DB via Testcontainers), and cover the nasty cases: restart, skip, partition, Kafka round-trip.

**Core topics.**
- **`@SpringBatchTest`** — registers `JobLauncherTestUtils`, `JobRepositoryTestUtils`, `StepScopeTestExecutionListener`, `JobScopeTestExecutionListener`. In 5.x, `JobOperatorTestUtils` is preferred for new tests.
- **Multiple-Job pitfall.** With multiple `Job` beans in context, the auto-wired `Job` in `JobLauncherTestUtils` breaks. Either keep one Job per test slice, or set `jobLauncherTestUtils.job = myJob` in `@BeforeEach`.
- **`StepScopeTestUtils.doInStepScope(stepExecution) { … }`** / `JobScopeTestUtils.doInJobScope`.
- **In-memory JobRepository — removed in 5.0.** Options:
  - `ResourcelessJobRepository` (5.2+) for fire-and-forget non-restartable tests.
  - Embedded H2 for cheap tests.
  - [marschall/spring-batch-inmemory](https://github.com/marschall/spring-batch-inmemory) community lib with `@ClearJobRepository(AFTER_TEST)`.
  - **Testcontainers Postgres with `@ServiceConnection`** — preferred for realistic tests.
- **Testcontainers patterns.**
  - Singleton container + per-test schema (`CREATE SCHEMA test_<random>`) is the fastest reliable isolation.
  - Enable reuse (`~/.testcontainers.properties: testcontainers.reuse.enable=true`).
  - Pin image tags, not `latest`.
  - Kafka tests: `ConfluentKafkaContainer` with `@ServiceConnection`.
- **Test data generation.**
  - **Fixture Monkey (Naver)** — Kotlin-first, controllable arbitrary data, seedable: `FixtureMonkey.builder().plugin(KotlinPlugin()).build()`. Common in Korean Kotlin codebases.
  - **Instancio** — Java-first alternative.
- **Flakiness prevention.** Inject `java.time.Clock` (fixed clock in tests); deterministic ORDER BY in readers; pin Testcontainers tags; seed RNG; Awaitility instead of sleep for async partition workers.
- **Restart test pattern.** Run with deliberate fail-on-item-N processor; assert BatchStatus=FAILED; clear the failure; rerun with same identifying params; assert resumed from saved position.
- **Remote chunking / partitioning E2E.** One JVM, two Spring profiles (`manager`, `worker`), Testcontainers Kafka, Awaitility on StepExecution status.

**Resources.**
- 📘 [Spring Batch Reference — Testing](https://docs.spring.io/spring-batch/reference/testing.html)
- 📘 [Spring Boot — Testcontainers reference](https://docs.spring.io/spring-boot/reference/testing/testcontainers.html)
- 🔗 [Baeldung — DB Integration Tests with Spring Boot and Testcontainers](https://www.baeldung.com/spring-boot-testcontainers-integration-test)
- 💻 [Fixture Monkey (Naver)](https://github.com/naver/fixture-monkey)
- 💻 [marschall/spring-batch-inmemory](https://github.com/marschall/spring-batch-inmemory)

**Deliverable project: "Reference test suite".**
Take your Phase 2 reconciliation job and write a test suite covering:
- Happy path (small dataset, assert counts, assert reconciliation table contents).
- Skip path (inject 3 invalid rows; assert `SKIP_COUNT=3`, DLT table has 3 rows with correct exception class).
- Restart path (force crash at chunk 5; assert restart completes and no row processed twice — check by computing a hash of the output set).
- Partition path (same job with 4 partitions; assert `stepExecutions.size == 5`).
- Kafka round-trip path (if you have remote chunking variant; Testcontainers Kafka).
- Fixture Monkey generates dirty realistic data (seeded for reproducibility).

Target: < 60 seconds for the full suite on a laptop. Measure it.

---

## Phase 8 — Performance tuning, HikariCP, JVM/container (Week 12)

**Objectives.** Make a slow batch fast, and know why every knob does what it does.

**Core topics.**
- **Chunk size tuning.** Larger = fewer commits, bigger rollback cost + memory; smaller = more commits + more granular retries. Start at 100–1000 for DB-to-DB; 500 is a safe middle. Align with `hibernate.jdbc.batch_size` and JDBC `fetchSize`.
- **Fetch size ≠ chunk size.** Fetch size is a driver/network buffer concern; chunk size is a transaction boundary concern. They are independent.
- **HikariCP sizing.** Formula: `connections = ((core_count * 2) + effective_spindle_count)` (1 for SSD). For Spring Batch: `min pool = JobRepo(1) + reader×partitions + writer×partitions + app + margin(2)`.
- **Dual-pool pattern.** Pool A (small, 2–4) for JobRepository metadata; Pool B sized to workers for business DB. Rationale: metadata commits must not be blocked by long-running business transactions — classic batch deadlock pattern, documented extensively in Korean blogs.
- **Aurora-specific.** `maxLifetime < wait_timeout` (and account for Aurora Proxy's shorter default). Use RDS Proxy for failover resilience. `connectionTimeout=20000`, `leak-detection-threshold=30000`.
- **JPA batching.** MUST set all three: `hibernate.jdbc.batch_size`, `hibernate.order_inserts`, `hibernate.order_updates`. `IDENTITY` generation **disables** insert batching — use `SEQUENCE`. MySQL: `rewriteBatchedStatements=true`. `flush(); clear()` at chunk end.
- **StatelessSession** for pure inserts/updates — no first-level cache, supports batching with `RETURNING`.
- **JdbcCursorItemReader MySQL cursor streaming** — `useCursorFetch=true` + fetchSize, OR `Integer.MIN_VALUE` row-by-row. Otherwise: OOM.
- **JdbcPagingItemReader no-offset** — for deep pagination, `WHERE id > :lastId ORDER BY id LIMIT :chunk`, not LIMIT/OFFSET.
- **GC tuning.** JDK 21 LTS + G1 (safe default) or Generational ZGC (sub-ms pauses, needs 4+ vCPU). Parallel GC for throughput-max small-pod batch. Watch humongous allocations in G1 (big JSON blobs / row arrays).
- **Container JVM.** `-XX:+UseContainerSupport` default since JDK 10. `-XX:MaxRAMPercentage=75.0`; never hard-code `-Xmx` in containers. Leave 25–30% for metaspace + thread stacks + direct buffers + JIT code cache. `-XX:ActiveProcessorCount` if fractional CPU limits confuse the JVM.
- **Native Memory Tracking** (`-XX:NativeMemoryTracking=summary` + `jcmd VM.native_memory summary`) when container OOMKills with heap at 60%.
- **Async-profiler for flamegraphs**; JFR for always-on sampling; Eclipse MAT for heap dumps.
- **Kotlin hot spot**: `DataClassRowMapper` beats reflective `BeanPropertyRowMapper` for Kotlin data classes.

**Resources.**
- 🔗 [HikariCP — About Pool Sizing wiki](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)
- 🔗 [Vlad Mihalcea — Optimal connection pool size](https://vladmihalcea.com/optimal-connection-pool-size/)
- 🔗 [Vlad Mihalcea — Hibernate StatelessSession JDBC batching](https://vladmihalcea.com/hibernate-statelesssession-jdbc-batching/)
- 🔗 [Vlad Mihalcea — MySQL cursor streaming](https://vladmihalcea.com/how-does-mysql-result-set-streaming-perform-vs-fetching-the-whole-jdbc-resultset-at-once/)
- 🔗 [Xebia — JVM Kubernetes integration guide](https://xebia.com/blog/guide-kubernetes-jvm-integration/)
- 🇰🇷 🔗 [Jaehun2841 — Spring Batch DB connection issue](https://jaehun2841.github.io/2020/08/09/2020-08-08-spring-batch-db-connection-issue/) — the canonical Korean write-up of the two-pool pattern.
- 🇰🇷 🔗 [우아한형제들 — 빌링 시스템 장애, 이러지 말란 Maria~](https://techblog.woowahan.com/2517/) — Hikari deadlock post-mortem.

**Deliverable project: "Performance hunt".**
Take the Phase 2 reconciliation job, provision a deliberately under-sized Aurora instance (db.t4g.medium) and a 1GB-memory pod. Without changing business logic, get the job 5× faster. Document in a markdown report exactly which change bought which speedup:

1. Chunk size sweep.
2. Switch `JpaItemWriter` → `StatelessSession` writer.
3. Fix IDENTITY → SEQUENCE (if applicable).
4. Enable `rewriteBatchedStatements` / proper fetchSize.
5. HikariCP pool split.
6. JVM flags: G1 or generational ZGC, `MaxRAMPercentage`.

Produce flamegraphs before/after. This is the deliverable that changes how you read any other team's batch code.

---

## Phase 9 — Kotlin-specific pitfalls consolidated (Week 13)

**Objectives.** A one-page cheat sheet you will actually refer back to, plus muscle memory for Kotlin+Batch idioms.

**The 14-item cheat sheet (memorize).**

| # | Pitfall | Failure mode | Fix |
|---|---|---|---|
| 1 | `@EnableBatchProcessing` copied from 4.x in Spring Boot 3 | Schema not init'd, auto-config silently off | Remove it |
| 2 | `chunk(100)` from 4.x | Compile error | `chunk(100, txManager)` |
| 3 | ExecutionContext v4 data + v5 default serializer | `SerializationException` on restart | Drain v4 or keep Jackson2 serializer |
| 4 | Kotlin entity without all-open for `@Entity` | N+1, LazyInitializationException | `allOpen { annotation("jakarta.persistence.Entity") }` |
| 5 | `@StepScope` on `@Bean fun d(): LocalDate` | CGLIB can't subclass final JDK class | Wrap in a Kotlin open class |
| 6 | `@Value("#{jobParameters['x']}")` on non-scoped bean | Null — resolved at context refresh, before run | Add `@StepScope` or `@JobScope` |
| 7 | `@JvmInline value class UserId` as JobParameter | Mangled accessor, Jackson breaks | Plain type at framework boundary |
| 8 | ItemReader returning non-null sentinel | Step never ends | Return `null` for end-of-input |
| 9 | Coroutines inside ItemProcessor/Writer | Lost TX, `@StepScope` proxy failure | Virtual-thread TaskExecutor instead |
| 10 | Missing `kotlin("plugin.spring")` | `@Configuration class may not be final` | Add the plugin |
| 11 | List<Entity> in ExecutionContext | MySQL "data too long for SERIALIZED_CONTEXT" | Store only primitives |
| 12 | Concurrent launches on Postgres w/ SERIALIZABLE | `CannotSerializeTransactionException` | `spring.batch.jdbc.isolation-level-for-create=READ_COMMITTED` |
| 13 | Jackson serializer w/ Kotlin data classes w/o module | No no-arg ctor / polymorphic typing | Add `jackson-module-kotlin` |
| 14 | Old `DefaultBatchConfigurer` pattern | Bean doesn't exist in 5.x | Extend `DefaultBatchConfiguration` |

**Why coroutines are a bad fit (nuanced).** Spring's `TransactionSynchronizationManager`, `SecurityContextHolder`, and Spring Batch's `StepSynchronizationManager`/`JobSynchronizationManager` (backing `@StepScope`/`@JobScope`) are all `ThreadLocal`. Suspension + resumption on a different thread loses all of them. Chunk transactions are thread-bound. There are no coroutine-aware `Item*` interfaces. Observability's current span is ThreadLocal-based for blocking code. **The only safe pattern** is `runBlocking { … }` inside a **pure I/O-fan-out Tasklet** with no DB writes in the coroutines — and even then, prefer a virtual-thread `TaskExecutor` which is thread-bound by design.

**Kotlin DSL for Spring Batch.**
- **No official DSL** (request #3984 declined).
- **Naver's spring-batch-plus** (`com.navercorp.spring:spring-boot-starter-batch-plus-kotlin`) provides a `BatchDsl`. Community-maintained; wraps (not replaces) the builders.
- **Recommended for mastery:** use plain `JobBuilder` / `StepBuilder` directly. The idiomatic Kotlin code is clean enough that a DSL layer is abstraction-for-abstraction's-sake.

**Typed JobParameters access in Kotlin.**
```kotlin
@Component
@StepScope
class ImportParams(
    @Value("#{jobParameters['file']}")    val file: String,
    @Value("#{jobParameters['runDate']}") val runDate: LocalDate,  // works in 5.x
)
```
Inject `ImportParams` anywhere in the step. Alternative: extension function `JobParameters.toImportParams()` for non-scoped typed access.

**Resources.**
- 💻 [Naver spring-batch-plus](https://github.com/naver/spring-batch-plus)
- 🔗 [Kotlin all-open plugin docs](https://kotlinlang.org/docs/all-open-plugin.html)
- 🔗 [Spring Guides — Spring Boot + Kotlin](https://spring.io/guides/tutorials/spring-boot-kotlin/)
- 🔗 [Xebia — Kotlin value-class gotchas](https://xebia.com/blog/kotlin-gems-features-i-wish-i-discovered-sooner/) — mangling.
- 🇰🇷 🔗 [Line Engineering — Kotlin JDSL (JPA Criteria with Kotlin)](https://engineering.linecorp.com/en/blog/kotlinjdsl-jpa-criteria-api-with-kotlin/) — not strictly batch but directly relevant for Kotlin batch queries.
- 🇰🇷 💻 [jojoldu's Spring Batch series (blog)](https://jojoldu.tistory.com) — the reference most Korean backend engineers learned from; widely cited in Toss/Woowahan/KakaoPay posts.

**Deliverable project: "Kotlin pitfall reproduction kit".**
Build `spring-batch-mastery-p9-pitfalls`: one integration test per cheat-sheet item that **reproduces the failure** and then **fixes it** in a following test. Use `@Nested` classes and descriptive test names (`given @StepScope bean returning LocalDate … when context starts … then throws CGLIB error`). You will paste this repo into team onboarding for every Kotlin+Batch hire after.

---

## Phase 10 — Enterprise problem patterns: financial, migration, warehouse, event (Weeks 14–15)

**Objectives.** You have the mechanics. Now see the patterns that pay the bills.

### 10.1 Financial batch — settlement, billing, daily close
- **Idempotency is the product.** Every job parameterized by `businessDate: LocalDate`. Re-running for the same date must produce identical output (delete partition, re-insert).
- **Deterministic keys**, not `IDENTITY`, for ledger rows, so replay is bit-identical.
- **Separate compute and publish steps.** Compute writes to `pending_*` table; publish flips a status flag atomically. Safely re-runnable.
- **UTC timestamps + explicit business date** parameter. DST and timezone bugs eat close processes alive.
- **Reconciliation step at end-of-job.** Compare source/destination row counts; fail loud if drift.
- **Dual-write consistency.** Toss Payments's 5-minute reconciliation batch filling async-dual-write gaps is the canonical pattern.
- **Rate-limited external calls** from within the writer — Resilience4j `RateLimiter(limitRefreshPeriod=1s, limitForPeriod=tps)` as Toss Securities does for broker fan-out.

### 10.2 Migration / backfill at 1B-row scale
- Drive by **key range**, not offset. `WHERE id > :lastId ORDER BY id LIMIT :chunk`. Checkpoint `lastId` in ExecutionContext.
- **Throttle** in `ChunkListener.afterChunk` to keep Aurora < 60% CPU; backfill windows run off-peak.
- Write to new column first; validation step compares; cutover last.
- Partitioning = 4–8 partitions over key-range buckets; avoid flooding primary.
- StatelessSession writer.
- Dry-run step counting affected rows.
- **For true TB-scale**: offload the copy to AWS DMS or Aurora logical replication; let Spring Batch be just the transformation stage.

### 10.3 Data warehouse loading (SCD Type 2, dim/fact ordering)
- Dimensions first, facts second.
- SCD Type 2: incoming row → find current active → no-op / close-old + insert-new. Inside one chunk tx with a `ClassifierCompositeItemWriter` (one delegate closes, one inserts).
- Simpler alternative: **daily dimension snapshot** (full copy per `snapshot_date`). Storage is cheap, backfill is trivial, SQL stays simple. Use this unless SCD-2 is mandated.
- Fact loading partitioned by date; upsert by (fact_pk, date). `DELETE WHERE partition = X; INSERT …` is the idempotent standard.

### 10.4 Event-driven integration (batch ↔ streaming)
- **Batch consuming Kafka** for CDC replay (Debezium `db.myschema.*` topics). `KafkaItemReader` with manual offset commit at chunk boundary.
- **Batch producing Kafka** via `KafkaItemWriter` or **transactional outbox** (write to DB outbox in chunk TX, CDC or poller ships to Kafka).
- **Replay pattern**: persist a ledger of original events (or their S3 URIs); a replay job re-reads ledger and republishes by business date for consumer bug recovery.
- **Rule of thumb**: if latency SLA is seconds, use streaming (Kafka Streams / Flink); if hours, batch is fine. The Netflix case study (Flink migration for personalization) and KakaoPay/Toss's batch-for-reconciliation coexist for that reason.

### 10.5 Deduplication at scale
- < 1B rows: DB-side `INSERT … ON CONFLICT DO NOTHING` with unique constraint on business key. Rock-solid.
- > 1B rows (warehouse): `ROW_NUMBER() OVER (PARTITION BY biz_key ORDER BY ingest_ts DESC) = 1` in SQL.
- In-Java: Guava `BloomFilter` pre-filter in processor, confirm positives in DB.

### 10.6 Dead-letter handling
- `SkipListener.onSkipInWrite` writes `{jobExecutionId, item-json, exception-class}` to `batch_dlt` table (or Kafka DLT topic).
- A separate **reconciliation job** reads DLT, applies a fix, re-submits to the main pipeline.
- Grafana panel on `batch_dlt` rate; alert on threshold breach.
- Never `skip(Exception.class)` — whitelist expected exceptions only. Catch-all skip hides bugs.

**Resources.**
- 🇰🇷 🔗 [Toss — 레거시 결제 원장을 확장 가능한 시스템으로](https://toss.tech/article/payments-legacy-5) — dual-write reconciliation.
- 🇰🇷 🔗 [Toss Securities — 해외주식 서비스 안정화](https://toss.tech/article/28738) — Kotlin Spring Batch + Resilience4j rate-limit; batch→streaming hybrid.
- 🇰🇷 🔗 [Toss — 레거시 정산 개편기 (series)](https://toss.tech/series/payments-legacy) — 8-part series; read all of it.
- 🇰🇷 🔗 [KakaoPay — Aggregation](https://tech.kakaopay.com/post/ifkakao2022-batch-performance-aggregation/)
- 🇰🇷 🔗 [우아한형제들 — 파일럿 프로젝트를 통한 배치경험기](https://techblog.woowahan.com/2623/) — 300만 건 reconciliation, CSV ↔ order history.
- 🇰🇷 🔗 [우아한형제들 — 결팀소 (결제시스템팀 소개)](https://woowabros.github.io/woowabros/2019/08/06/wooteamso.html) — "10억 개 중 9억9천만 번째에서 Exception은 어떻게" framing.
- 🇰🇷 🔗 [우아한형제들 — 가게노출 시스템 (Reactor + Spring Batch)](https://techblog.woowahan.com/2667/) — manual-recovery batch pattern.
- 🔗 [Netflix InfoQ — Migrating Batch ETL to Stream Processing](https://www.infoq.com/articles/netflix-migrating-stream-processing/) — "batch is not dead"; best global case study on the trade-off.
- 🔗 [CoreLogic SpringOne case study — Spring Batch + SCDF + CF + RabbitMQ + WebSockets](https://www.slideshare.net/Pivotal/case-study-of-batch-processing-with-spring-cloud-data-flow-server-in-cloud-foundry)
- 🔗 [Streamkap — Batch→Streaming Migration Playbook](https://streamkap.com/resources-and-guides/batch-to-streaming-migration)
- 📘 Kleppmann — *Designing Data-Intensive Applications* 2nd ed. Ch. 11 (batch) and Ch. 12 (stream) — the theory underneath all of the above.

**Deliverable project: "Mock settlement + reconciliation".**
`spring-batch-mastery-p10-settlement`: build a simplified 정산 pipeline.
- **Job 1 (hourly)**: read transactions from Kafka → stage into Aurora with idempotency key.
- **Job 2 (daily, parameterized by `businessDate`)**: compute per-merchant settlement amounts (partitioned over merchant_id ranges), write to `pending_settlement`. Emit Micrometer metrics per merchant class.
- **Job 3 (daily, after Job 2)**: publish `pending_settlement` → `settlement` atomically; emit settlement events to Kafka via transactional outbox.
- **Job 4 (every 5 min)**: reconcile Aurora staging vs an emulated upstream source; write to DLT on mismatch.
- Step Functions DAG: Job 1 (hourly) and (Job 2 → Job 3) daily; Job 4 runs via EKS CronJob.
- Full observability (Phase 6), full tests (Phase 7), performance-tuned (Phase 8).

This is the capstone-level deliverable. Commit with a postmortem-style README covering what you would do differently at 10× scale.

---

## Phase 11 — Security, secrets, audit, licensing (Week 15, alongside Phase 10)

**Core topics.**
- **JobParameters are persisted verbatim** to `BATCH_JOB_EXECUTION_PARAMS`. Never PII, never secrets, never API keys. Pass an opaque `runSpecId`; resolve via a `@JobScope` bean against Secrets Manager or a controlled `run_spec` table.
- **ExecutionContext is persisted** to `BATCH_*_EXECUTION_CONTEXT`. Same rule: ID references, not payloads.
- **Jackson ExecutionContextSerializer historical deserialization gadgets** — keep Jackson current, don't enable default typing on custom serializers, restrict DB write permissions on batch tables.
- **AWS Secrets Manager + Spring Cloud AWS** (`io.awspring.cloud:spring-cloud-aws-starter-secrets-manager`). Auto-rotation, KMS, per-secret IAM.
- **IRSA on EKS** — no long-lived keys; annotate ServiceAccount with `eks.amazonaws.com/role-arn`. Least-privilege role per batch job.
- **RDS Proxy + VPC endpoints** for Aurora; keep NAT egress off the batch path.
- **MSK IAM auth** (`aws-msk-iam-auth`) or mTLS; topic-level ACLs.
- **Audit logs** at `beforeJob`: `{ user, jobName, jobParametersFiltered, startTime }`. Separate CloudWatch log group with tight IAM.
- **Redaction filter** so `params.toString()` never leaks sensitive keys to stdout.
- **Spring ecosystem CVE discipline.** Monitor [spring.io/security](https://spring.io/security/). Notable recent CVEs affecting Boot apps (thus Batch apps): CVE-2025-41248/41249 (Spring Security authz bypass), CVE-2025-41254 (CSRF), CVE-2025-22235 (Actuator matcher), CVE-2025-22233 (DataBinder locale bypass). Dependabot or Renovate + Snyk/Trivy in CI.

**Licensing recap (pin this on the team wiki).**
- Spring Batch: Apache 2.0.
- Spring Cloud Task: Apache 2.0, actively maintained (3.3.x in 2025.0, 5.0.x for Spring Boot 4).
- **Spring Cloud Data Flow / Deployer / Statemachine: commercial only after April 2025 (Broadcom/Tanzu).**
- Jenkins: MIT. CloudBees CI: commercial.
- Quartz: Apache 2.0.
- Apache Airflow: Apache 2.0. MWAA/Astro/Cloud Composer: commercial hosted.
- AWS managed services: pay-per-use.

---

## Phase 12 — When NOT to use Spring Batch (Week 16, capstone reasoning)

**The six honest alternatives.**

- **Kafka Streams / Apache Flink** — continuous, low-latency, windowed. Exactly-once via Kafka transactions. State stores (RocksDB). Use when freshness is measured in seconds. Spring Batch is job-starts-job-ends; streams are always-on.
- **AWS Lambda + Step Functions** — small, event-driven, non-JVM. 15 minutes or less, no JDBC cursors. Step Functions for retry/backoff/DAG. Don't stand up a full Spring Batch context for a 30-second transform.
- **Airflow / Dagster / Prefect** — cross-system orchestration, 10+ heterogeneous systems, Python-heavy team. Don't loop item-by-item in Airflow; don't orchestrate 15 Glue jobs from Spring Batch. Complementary: Airflow triggers Spring Batch, then dbt.
- **dbt (Core or Cloud)** — SQL-centric warehouse transformations (Snowflake, Redshift, BigQuery, Databricks). Declarative models, built-in tests, lineage. Massive simplification over Spring Batch for pure ELT.
- **Apache Spark / AWS Glue / EMR** — > 100 GB to TB scale, columnar Parquet/Iceberg, vectorized execution, cluster shuffle. Single Aurora cluster + hours of processing ≈ Spring Batch. S3 Parquet + minutes ≈ Glue.
- **Shell scripts + cron (K8s CronJob + `psql` image)** — tiny, rarely-changing jobs (pg_dump to S3, daily count to Slack). The operational overhead of Spring Batch is disproportionate; 20 lines of bash is the right answer.

**Decision heuristic.** If you can answer yes to most of these, Spring Batch is right:
- Logic is imperative Java/Kotlin with business rules that are awkward in SQL.
- You need restart semantics, step ordering, skip/retry, per-item tracking.
- Data fits in a single DB cluster; processing runs in hours, not days.
- Team is JVM-heavy.
- You already deploy JARs/containers.

If instead latency < 10s matters, or data > 1TB, or the transformation is 90% SQL, or the team is Python-native, or the problem is "orchestrate 20 different systems" — pick the alternative above that fits.

**Resources.**
- 🎥 [Minella — "To Batch or Not To Batch" (Devnexus 2020)](https://www.youtube.com/watch?v=h911Ogbe2TI)
- 🔗 [Netflix — Migrating Batch ETL to Stream Processing](https://www.infoq.com/articles/netflix-migrating-stream-processing/)
- 🔗 [SaaSHub — Spring Batch vs Airflow](https://www.saashub.com/compare-spring-batch-vs-airflow)
- 🔗 [DZone — AWS Glue ETL vs AWS Batch](https://dzone.com/articles/comparing-glue-etl-and-aws-batch-optimal-tool-sele)
- 🇰🇷 🔗 [Bucketplace — Airflow 도입기](https://www.bucketplace.com/post/2021-04-13-버킷플레이스-airflow-도입기/)
- 🔗 [OSO — Tips for moving from Batch to Real Time streaming](https://oso.sh/blog/tips-for-moving-from-batch-to-real-time-data-streaming/)

**Final deliverable: "Decision doc".**
A 2-page internal doc titled "When to pick Spring Batch at \<yourCompany\>". Include a flowchart, three past projects from Phases 1–10 classified against the heuristic, and a list of three scenarios at your company where Spring Batch is the wrong answer. This is what a staff-level engineer writes, and it demonstrates you understand the tool's shape, not just its API.

---

## Ongoing references (keep bookmarked)

**Canonical official.**
- [Spring Batch reference (latest)](https://docs.spring.io/spring-batch/reference/)
- [Spring Batch GitHub (issues + discussions — StackOverflow deprecated Jan 2026)](https://github.com/spring-projects/spring-batch)
- [Spring Batch Samples (kept on main against latest)](https://github.com/spring-projects/spring-batch/tree/main/spring-batch-samples)
- [Spring Batch Extensions](https://github.com/spring-projects/spring-batch-extensions)
- [Spring Batch 5.0 Migration Guide](https://github.com/spring-projects/spring-batch/wiki/Spring-Batch-5.0-Migration-Guide)
- [Mahmoud Ben Hassine — author page with all release posts](https://spring.io/authors/fmbenhassine/)
- [Michael Minella — GitHub profile](https://github.com/mminella)

**Korean tech blog batch index (highest-signal 10 articles).**
1. [Toss Payments — 레거시 정산 개편기](https://toss.tech/article/42671)
2. [KakaoPay — Batch Performance Reader (if kakao 2022)](https://tech.kakaopay.com/post/ifkakao2022-batch-performance-read/)
3. [KakaoPay — Batch Performance Aggregation (if kakao 2022)](https://tech.kakaopay.com/post/ifkakao2022-batch-performance-aggregation/)
4. [KakaoPay — Spring Batch 성능 향상 팁 (Kotlin+Exposed+RxKotlin)](https://tech.kakaopay.com/post/spring-batch-performance/)
5. [Woowahan — Spring Batch + Querydsl](https://techblog.woowahan.com/2662/)
6. [Woowahan — 정산 신병들 (team conventions)](https://techblog.woowahan.com/2711/)
7. [Woowahan — 누구나 할 수 있는 10배 더 빠른 배치](https://techblog.woowahan.com/13569/)
8. [Woowahan — Jenkins API 기반 배치 모니터링](https://techblog.woowahan.com/2722/)
9. [Kurly — BULK 처리 Write 개선](https://helloworld.kurly.com/blog/bulk-performance-tuning/)
10. [Toss — JDBC 성능 네트워크 분석](https://toss.tech/article/25029)

**Global engineering blog batch index (core 5).**
1. [Ben Hassine — Spring Batch on Kubernetes (2021)](https://spring.io/blog/2021/01/27/spring-batch-on-kubernetes-efficient-batch-processing-at-scale/)
2. [Netflix InfoQ — Batch ETL to Stream Processing](https://www.infoq.com/articles/netflix-migrating-stream-processing/)
3. [CoreLogic SpringOne — Spring Batch + SCDF production case](https://www.slideshare.net/Pivotal/case-study-of-batch-processing-with-spring-cloud-data-flow-server-in-cloud-foundry)
4. [Arnold Galovics — Remote Partitioning with Kafka](https://arnoldgalovics.com/spring-batch-remote-partitioning-kafka/)
5. [Trifork — Spring Boot observability for Spring Batch](https://trifork.nl/blog/spring-boot-observability-spring-batch-jobs/)

**Books.**
- Martin Kleppmann — *Designing Data-Intensive Applications* 2nd ed. (Ch. 11 batch, Ch. 12 stream). Non-negotiable.
- Thomas Vitale — *Cloud Native Spring in Action* (Manning). K8s/GitOps substrate.
- Michael Minella — *The Definitive Guide to Spring Batch* 2nd ed. — you are finishing it; keep for reference but read with the 5.0 Migration Guide next to it.

**Courses.**
- [Spring Academy — Building a Batch Application with Spring Batch (Ben Hassine)](https://spring.academy/courses/building-a-batch-application-with-spring-batch) — free, project-lead-taught, 5.x.
- Udemy — pick only courses updated 2024+ that use `JobBuilder` directly (no `JobBuilderFactory`).

---

## Suggested weekly cadence at a glance

| Weeks | Phase | Deliverable |
|---|---|---|
| 1 | P0 Retro-port book to 5.x | `p0-helloport` repo |
| 2–3 | P1 Internals (JobRepo, TX, skip/retry) | `p1-internals-lab` |
| 4–5 | P2 Readers/Writers, JPA pitfalls | `p2-reconciliation` |
| 6 | P3 Scaling I (threads, partitioning) | Settlement partition benchmark |
| 7–8 | P4 Remote chunking + partitioning (Kafka) | `p4-remote-partition` |
| 9 | P5 Deployment landscape | Three deployments of P4 |
| 10 | P6 Observability | Observability overlay on EKS |
| 11 | P7 Testing | Reference test suite |
| 12 | P8 Performance tuning | Performance hunt report |
| 13 | P9 Kotlin pitfalls | `p9-pitfalls` kit |
| 14–15 | P10 Enterprise patterns + P11 Security | `p10-settlement` capstone |
| 16 | P12 When-not-to-use | Decision doc |

---

## Closing notes

The order above is opinionated. If you skip the internals of Phase 1, every later phase becomes folklore — you will partition and remote-chunk things without understanding what actually goes wrong when a pod is SIGKILLed mid-chunk. If you skip the deliverables, you will read a lot and ship nothing. The deliverables are the curriculum; the reading list is scaffolding.

Two cultural observations to carry into Korean fintech work: (1) the Toss, KakaoPay, Woowahan, and Kurly posts consistently emphasize **pragmatic pre-optimization fixes** (N+1, bulk writes, no-offset paging) before reaching for partitioning — Woowahan's "10배 빠른 배치" post is the clearest statement of this. (2) **Jenkins dominance is a feature, not a bug**, in the Korean enterprise batch landscape; the Toss "thousands of batch configs" post shows how you get the benefits of declarative orchestration without SCDF, and it's the mental model that will serve you best at a Korean fintech in 2026. Internalize both, and you will be indistinguishable from the engineers who wrote those blog posts.