# Spring Batch mastery in Kotlin: a 6-month learning plan for AWS-containerized environments

**Spring Batch remains the gold standard for enterprise batch processing in the JVM ecosystem**, and learning it as a Kotlin/Spring Boot developer deploying on AWS EKS/ECS is a high-leverage investment. This plan takes you from zero to production mastery over **26+ weeks across six phases**, each building on the last. The current stable versions are **Spring Batch 5.2.x** (for Spring Boot 3.x) and **Spring Batch 6.0.x** (released November 2025 for Spring Boot 4). This curriculum targets 5.2.x as the production baseline, with notes on 6.0 features where relevant. Every phase includes specific resources and a hands-on milestone project.

---

## Phase 1: Foundations and your first batch job (weeks 1–4)

The goal of this phase is to internalize the core domain model and write your first chunk-oriented jobs in idiomatic Kotlin. Spring Batch's architecture is built on a handful of interlocking concepts: understanding them deeply now prevents every downstream mistake.

### Week 1: The mental model

Study the **Spring Batch domain language** before writing any code. The key abstractions form a hierarchy: a **Job** contains one or more **Steps**; each Step is either a **Tasklet** (single unit of work) or a **chunk-oriented step** (read-process-write in configurable batch sizes). The **JobRepository** persists all execution metadata to a relational database, enabling restart, monitoring, and auditability. The **JobLauncher** is the entry point that accepts a Job and JobParameters and kicks off execution.

Focus on understanding: **ExecutionContext** (key-value state per job/step, serialized to the DB), **JobInstance** vs. **JobExecution** (a JobInstance is unique per job name + identifying parameters; it can have multiple JobExecutions if restarted), and how **JobParameters** drive identity and restartability.

**Resources:**
- Spring Batch Reference Documentation, chapters 1–4 (Domain Language, Configuring a Job, Configuring a Step): https://docs.spring.io/spring-batch/reference/
- Spring Academy free course "Building a Batch Application with Spring Batch" by Mahmoud Ben Hassine (Spring Batch project lead) — **the single best starting resource**, free with interactive labs: https://spring.academy/courses
- "The Definitive Guide to Spring Batch" by Michael Minella, 2nd edition (Apress, 2019), chapters 1–4. Covers Spring Batch 4 but the conceptual architecture is identical in 5.x. **No newer book exists** — this remains the only comprehensive Spring Batch book.

### Week 2: Kotlin project setup and chunk-oriented processing

Create a new Spring Boot 3.x project with `spring-boot-starter-batch`, `spring-boot-starter-jdbc`, and an H2 or PostgreSQL dependency. Use Gradle Kotlin DSL (`build.gradle.kts`). Add the `kotlin-spring` compiler plugin (automatically opens `@Configuration` classes) and set `-Xjsr305=strict` for null-safety interop with Spring's annotations.

Build your first chunk-oriented step: an `ItemReader` that reads from a CSV file (`FlatFileItemReader`), an `ItemProcessor` that transforms records, and an `ItemWriter` that writes to a database (`JdbcBatchItemWriter`). In Spring Batch 5.x, **`JobBuilderFactory` and `StepBuilderFactory` are deprecated** — use `JobBuilder("name", jobRepository)` and `StepBuilder("name", jobRepository)` directly. You must also explicitly pass a `PlatformTransactionManager` to chunk and tasklet steps.

Key Kotlin idioms to apply: use **data classes** for batch domain objects, leverage **SAM conversions** (lambdas) for `Tasklet` and `ItemProcessor` interfaces, and use Kotlin's expression body syntax for concise `@Bean` definitions.

**Resources:**
- Spring Getting Started Guide "Creating a Batch Service": https://spring.io/guides/gs/batch-processing/
- Baeldung "Spring Boot With Spring Batch": https://www.baeldung.com/spring-boot-spring-batch
- Audensiel blog "Effortless Batchs with Spring Batch and Kotlin": https://www.audensiel.com/en/post/effortless-batchs-with-spring-batch-and-kotlin

### Week 3: Tasklet steps, listeners, and the Kotlin DSL

Build a Tasklet step (e.g., file cleanup or directory preparation) alongside your chunk step. Then add **listeners** at every level: `JobExecutionListener` for logging job start/end, `StepExecutionListener` for step metrics, and `ChunkListener` for chunk-level monitoring. Spring Batch supports both interface implementation and `@BeforeStep`/`@AfterStep` annotations.

Introduce **Naver's spring-batch-plus** library (`com.navercorp.spring:spring-boot-starter-batch-plus-kotlin`), which provides the only mature Kotlin DSL for Spring Batch. The `BatchDsl` builder eliminates verbose Java-style builder chains:

```kotlin
@Bean
fun myJob(batch: BatchDsl): Job = batch {
    job("myJob") {
        step("cleanup") { tasklet({ _, _ -> RepeatStatus.FINISHED }, txManager) }
        step("process") {
            chunk<InputRecord, OutputRecord>(500, txManager) {
                reader(csvReader)
                processor(transformProcessor)
                writer(jdbcWriter)
            }
        }
    }
}
```

Note: **Spring Batch has no official Kotlin DSL** (the proposal in GitHub issue #3984 was declined). The Naver library is the community standard with **126+ GitHub stars** and is tested against Spring Boot 3.0/Spring Batch 5.0.

**Resources:**
- Naver spring-batch-plus documentation and examples: https://github.com/naver/spring-batch-plus
- Spring Batch reference, "Configuring a Step" chapter: listeners section
- ddubson/spring-batch-examples (Kotlin): https://github.com/ddubson/spring-batch-examples — **30+ Kotlin examples** from simple to advanced

### Week 4: Job parameters, job repository schema, and testing

Study the **6 core metadata tables**: `BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION`, `BATCH_JOB_EXECUTION_PARAMS`, `BATCH_JOB_EXECUTION_CONTEXT`, `BATCH_STEP_EXECUTION`, `BATCH_STEP_EXECUTION_CONTEXT`, plus 3 sequence tables. Understand that in Spring Batch 5, the **map-based JobRepository was removed** — a `DataSource` is always required.

Set up testing with `@SpringBatchTest` (auto-registers `JobLauncherTestUtils` and `JobRepositoryTestUtils`). Write your first integration test:

```kotlin
@SpringBatchTest
@SpringBootTest
class MyBatchJobTest {
    @Autowired lateinit var jobLauncherTestUtils: JobLauncherTestUtils
    @Test
    fun `job completes successfully`() {
        val execution = jobLauncherTestUtils.launchJob()
        assertEquals(BatchStatus.COMPLETED, execution.status)
    }
}
```

Use **MockK** (Kotlin-native mocking) for unit testing individual `ItemProcessor` and `ItemWriter` components in isolation.

**Resources:**
- Spring Batch reference, "The Meta-Data Schema" and "Unit Testing" chapters
- Baeldung "Spring Batch Testing Job": https://www.baeldung.com/spring-batch-testing-job
- mminella/batch-kotlin-example: https://github.com/mminella/batch-kotlin-example (by the former Spring Batch project lead)

### 🏗️ Milestone Project 1: CSV-to-database ingestion pipeline

Build a complete Spring Batch job that reads a large CSV file of customer records (100K+ rows), validates and transforms each record via an `ItemProcessor`, and writes to a PostgreSQL database using `JdbcBatchItemWriter`. Include a pre-processing Tasklet step that archives the previous output table. Add `JobExecutionListener` and `StepExecutionListener` for logging. Write comprehensive tests with `@SpringBatchTest`. Configure chunk size of 500 and observe transaction behavior.

---

## Phase 2: Error handling, flow control, and scheduling (weeks 5–8)

This phase introduces resilience patterns and the many ways to trigger batch jobs — a critical decision for containerized deployments.

### Week 5: Skip, retry, and restart logic

Spring Batch's **fault tolerance** is one of its killer features. Configure skip logic (`.faultTolerant().skip(ParseException::class.java).skipLimit(100)`) to continue processing despite bad records. Add retry logic (`.retry(TransientDataAccessException::class.java).retryLimit(3)`) for transient failures. Implement a `SkipListener` to log or quarantine skipped items.

Study **restartability** deeply: when a job fails, Spring Batch persists the `ExecutionContext` (including the reader's position). Re-launching with the same `JobParameters` creates a new `JobExecution` for the existing `JobInstance` and resumes from the last committed chunk. Critical caveat: **multi-threaded steps are NOT restartable** because shared reader state becomes inconsistent. **Partitioned steps ARE restartable** — each partition maintains its own execution context.

**Resources:**
- Spring Batch reference, "Retry" and "Configuring Skip Logic" sections
- "The Definitive Guide to Spring Batch" chapters 7–8 (Error Handling, ItemReaders/Writers)
- NashTech blog "Spring Batch: A Comprehensive Guide": https://blog.nashtechglobal.com/spring-batch-a-comprehensive-guide/

### Week 6: Flow-based jobs and conditional transitions

Build jobs with **conditional flow**: use `.on("COMPLETED").to(stepB).from(stepA).on("FAILED").to(errorStep)` to create branching execution paths. Learn `FlowBuilder` for reusable flows, `JobExecutionDecider` for programmatic routing, and nested job patterns (a step that launches another job).

Also study **`ExitStatus` vs. `BatchStatus`**: `BatchStatus` is an enum (COMPLETED, FAILED, STOPPED, etc.) managed by the framework; `ExitStatus` is a string-based result that drives flow transitions and can be customized.

**Resources:**
- Spring Batch reference, "Configuring a Job — Conditional Flow" section
- Baeldung "Spring Batch Conditional Flow": https://www.baeldung.com/spring-batch-conditional-flow

### Week 7: Scheduling deep dive — all approaches compared

This is a critical week. Study **every scheduling approach** and understand which fits containerized EKS/ECS deployments:

**Spring @Scheduled**: Simplest approach — `@EnableScheduling` + `@Scheduled(cron = "...")` method that calls `jobLauncher.run()`. Limitations: **no cluster safety** (every pod fires every schedule), requires a 24/7 running JVM, no misfire handling if the app is down. Only suitable for single-instance development. Default is a **single-threaded** scheduler pool — configure `spring.task.scheduling.pool.size` to increase.

**Quartz Scheduler**: Enterprise-grade with `spring-boot-starter-quartz`. Supports **JDBC job store** (`spring.quartz.job-store-type=jdbc`) for persistent schedules and **clustering** (`org.quartz.jobStore.isClustered=true`) — only one node fires per trigger via row-level DB locking. Requires shared database tables (prefixed `QRTZ_`), NTP-synchronized clocks, and a bridging `QuartzJobBean`. Valuable when you need dynamic runtime schedule creation, but K8s-native scheduling is generally preferred in containerized environments.

**Kubernetes CronJobs** (recommended for EKS): Package the Spring Batch app as a run-to-completion container (set `spring.batch.job.enabled=true`, remove web dependencies). Define a K8s CronJob with `concurrencyPolicy: Forbid` for single-instance guarantee. **Zero idle resource cost** — pods spin up, run the job, and terminate. Key fields: `backoffLimit` (retry failed pods), `activeDeadlineSeconds` (kill if too long), `startingDeadlineSeconds` (grace for missed schedules), `successfulJobsHistoryLimit`.

**AWS EventBridge Scheduler → ECS RunTask** (recommended for ECS): Fully managed, serverless cron/rate scheduling that directly launches ECS Fargate tasks. Supports retries (up to 185), dead-letter queues, flexible time windows, and IAM-based security. No infrastructure to maintain. EventBridge doesn't natively trigger K8s jobs — for EKS, use K8s CronJobs instead or route through Lambda → K8s API.

**AWS Step Functions + ECS**: Visual, serverless workflow orchestration for complex multi-step batch pipelines. Native `ecs:runTask.sync` integration waits for task completion. Supports parallel execution (Map state for fan-out), retry with exponential backoff, error catching, and state passing between steps. Best for orchestrating multiple dependent batch jobs. Cost: **$0.025 per 1,000 state transitions**.

**Lambda → ECS/EKS triggers**: Lambda as a lightweight dispatcher for event-driven batch — S3 upload triggers Lambda, which calls `ecs:RunTask`. Lambda's 15-minute timeout and 10GB memory limit make it unsuitable for the batch work itself, but perfect as a trigger.

**Spring Cloud Data Flow (SCDF)**: Server-based orchestration platform that manages Spring Batch job lifecycle — registration, launching, scheduling (creates K8s CronJobs under the hood), composed task DAGs, and monitoring dashboard. Rich but heavy: requires running the SCDF server itself. **Note: the OSS version has moved to spring-attic** (maintenance mode) as of 2025. Consider carefully whether this operational overhead is justified vs. Kubernetes-native solutions.

**REST API triggering**: Disable auto-launch (`spring.batch.job.enabled=false`), expose a `@PostMapping` endpoint that calls `jobLauncher.run()`. For long-running jobs, configure an async `JobLauncher` with `SimpleAsyncTaskExecutor` so the HTTP response returns immediately with an execution ID. Use `JobExplorer` for a status-polling endpoint. The library `spring-batch-rest` (GitHub: chrisgleissner/spring-batch-rest) provides ready-made REST endpoints.

**Resources:**
- Kubernetes CronJob docs: https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/
- AWS EventBridge Scheduler docs: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/tasks-scheduled-eventbridge-scheduler.html
- Baeldung "Spring Batch Start Stop": https://www.baeldung.com/spring-batch-start-stop-job
- "What's New in Spring Batch 5" talk by Mahmoud Ben Hassine (Spring I/O 2023): https://speakerdeck.com/fmbenhassine/whats-new-in-spring-batch-5

### Week 8: Implement scheduling approaches hands-on

Implement at least three triggering methods for the same batch job: `@Scheduled` (for local dev), K8s CronJob (for EKS), and REST API (for on-demand). Write the Kubernetes CronJob YAML, Dockerfile, and test the run-to-completion pattern locally with Docker.

### 🏗️ Milestone Project 2: Database migration with error handling and scheduling

Build a job that migrates data from a legacy schema to a new schema across two PostgreSQL databases. Implement skip logic for malformed records (log to a quarantine table via `SkipListener`), retry logic for transient connection failures, and conditional flow (a validation step that routes to an error-reporting step on failure). Configure the job to be triggerable via REST API and K8s CronJob. Write tests that verify restart from failure.

---

## Phase 3: Scaling and advanced processing patterns (weeks 9–12)

This phase covers the four scaling strategies that make Spring Batch handle millions of records: multi-threaded steps, async processing, local partitioning, and remote partitioning/chunking.

### Week 9: Multi-threaded steps and async processing

**Multi-threaded steps** add a `TaskExecutor` to a step, enabling multiple threads to process chunks concurrently. Simple to configure but requires **thread-safe readers and writers**. Critical detail: `JdbcCursorItemReader` is **NOT thread-safe** — use `JdbcPagingItemReader` or wrap with `SynchronizedItemStreamReader`. Multi-threaded steps are **not restartable** because reader state is shared.

**AsyncItemProcessor / AsyncItemWriter**: Wraps your processor in a `Future`, enabling concurrent processing while maintaining read order. The `AsyncItemWriter` unwraps futures on write. Useful when processing (not I/O) is the bottleneck.

Configure a `ThreadPoolTaskExecutor` with a sensible pool size. Align your HikariCP connection pool: **pool size ≥ thread count + 1** (one extra for the JobRepository). With Java 21+ virtual threads, you can configure a virtual-thread-based TaskExecutor for excellent scalability without tuning thread pools.

**Resources:**
- Spring Batch reference, "Scaling and Parallel Processing" chapter
- "The Definitive Guide to Spring Batch" chapters 11–12 (Scaling)
- ddubson/spring-batch-examples: async processor and multi-threaded examples

### Week 10: Local partitioning

**Partitioned steps** split data into independent segments processed in parallel. A `Partitioner` creates `ExecutionContext` maps for each partition (e.g., ID ranges 1–10000, 10001–20000, ...). A `PartitionHandler` distributes partitions to threads. Each partition gets its **own `StepExecution`** with its own reader/writer — making partitioned steps **fully restartable**.

Build a `ColumnRangePartitioner` that splits data by ID ranges. Configure the master step with `gridSize` (number of partitions) and a `TaskExecutor`. This is the **recommended scaling strategy for most production use cases** because it combines parallelism with restartability.

```kotlin
@Bean
fun masterStep(jobRepository: JobRepository, workerStep: Step): Step =
    StepBuilder("masterStep", jobRepository)
        .partitioner(workerStep.name, rangePartitioner())
        .step(workerStep)
        .gridSize(10)
        .taskExecutor(SimpleAsyncTaskExecutor())
        .build()
```

**Resources:**
- Spring Batch reference, "Partitioning" section
- Baeldung "Spring Batch Partitioner": https://www.baeldung.com/spring-batch-partitioner

### Week 11: Remote chunking and remote partitioning

**Remote partitioning** distributes partition metadata (not data) to worker JVMs via messaging (Kafka, SQS, RabbitMQ). Workers have their own readers and process independently. Master coordinates via `MessageChannelPartitionHandler`. Best when data can be segmented and each segment independently processed — the typical production choice for distributing work across multiple EKS pods or ECS tasks.

**Remote chunking** sends actual item data from master to workers over the wire. The master reads items, sends chunks to workers for processing and writing. Best only when reading is cheap but processing is extremely expensive — less common because of network I/O overhead.

Both patterns use Spring Integration channels. For AWS, use **SQS** as the messaging middleware or **MSK (Managed Kafka)**.

**Resources:**
- Spring Batch reference, "Remote Chunking" and "Remote Partitioning" sections
- GitHub: galovics/spring-batch-remote-partitioning (Kafka and SQS examples)
- ddubson/spring-batch-examples: remote partitioning and remote chunking Kotlin examples

### Week 12: Memory management and performance tuning

Study the three reader strategies for large datasets:

- **`JdbcCursorItemReader`**: Streams row-by-row via JDBC cursor — most memory efficient, not thread-safe. Set `fetchSize` (JDBC hint) to 1000+ for network efficiency.
- **`JdbcPagingItemReader`**: Queries page-by-page — thread-safe, restartable, works with partitioning. Set `pageSize` aligned with `chunkSize`.
- **`JpaPagingItemReader`**: JPA-based pagination — persistence context must be cleared between chunks to prevent memory growth.

**Chunk size tuning**: typical range is **100–5,000** items. Smaller chunks = more transaction overhead but lower memory; larger chunks = fewer commits but higher memory and longer-running transactions. Benchmark systematically: test 100, 500, 1000, 5000 and measure throughput, memory, and commit latency.

For JPA-heavy workloads, **clear the EntityManager between chunks** to prevent first-level cache growth. Consider using JDBC readers for maximum performance.

### 🏗️ Milestone Project 3: Partitioned large-dataset processor

Build a job that processes **1M+ records** from a PostgreSQL table using local partitioning. Implement a `ColumnRangePartitioner` that splits by ID ranges into 8 partitions. Each partition reads with `JdbcPagingItemReader`, processes (applies business validation and enrichment via an `ItemProcessor`), and writes to an output table. Add chunk size tuning — parameterize via `JobParameters` so you can benchmark different sizes. Measure throughput and verify restartability by killing the job mid-execution and restarting.

---

## Phase 4: Observability and production hardening (weeks 13–16)

This phase transforms your batch jobs from "works on my machine" to production-grade with full monitoring, structured logging, and operational resilience.

### Week 13: Micrometer metrics and Prometheus/Grafana

Spring Batch automatically registers Micrometer metrics under the `spring.batch` prefix: `spring.batch.job` (timer), `spring.batch.step` (timer), `spring.batch.item.read`, `spring.batch.item.process`, `spring.batch.chunk.write`. Tags include `name`, `status` (SUCCESS/FAILURE), and `job.name`.

Add `micrometer-registry-prometheus` and expose `/actuator/prometheus`. For **ephemeral batch pods** (K8s CronJobs), metrics disappear when the pod terminates — use **Prometheus Pushgateway** to push metrics before exit, or keep the pod alive briefly after job completion.

Set up a Grafana dashboard showing: job execution duration (p50/p95/p99), success/failure counts, items read/written per step, and active job count. The **Spring Cloud Data Flow Tasks Prometheus dashboard** (Grafana ID: 11436) is a useful starting template.

**Custom metrics**: Add business-specific counters via `MeterRegistry` in listeners (e.g., records enriched, records quarantined).

**Resources:**
- Spring Batch Monitoring docs: https://docs.spring.io/spring-batch/reference/monitoring-and-metrics.html
- Trifork blog "Spring Boot Observability: Spring Batch Jobs": https://trifork.nl/blog/spring-boot-observability-spring-batch-jobs/
- Grafana dashboard 11436 (SCDF Tasks Prometheus): https://grafana.com/grafana/dashboards/11436

### Week 14: Structured logging and distributed tracing

Configure **structured JSON logging** with logstash-logback-encoder for CloudWatch/ELK ingestion. Add MDC context for batch jobs: `job.name`, `job.executionId`, `step.name`. Create a custom `JobExecutionListener` that sets MDC on job start and clears on completion. For multi-threaded steps, use a `TaskDecorator` to propagate MDC across threads.

**Distributed tracing**: Spring Batch 5.x integrates with **Micrometer Tracing** (the replacement for Spring Cloud Sleuth). It creates a trace per job execution and spans per step execution. Add `micrometer-tracing-bridge-otel` and `opentelemetry-exporter-otlp` to export to an OpenTelemetry collector. Configure sampling rate (`management.tracing.sampling.probability`) — use **1.0 in dev, 0.1 in production** for batch jobs. Alternatively, attach the OpenTelemetry Java Agent as a JVM arg for zero-code instrumentation.

Note: there is **no dedicated Spring Batch Actuator endpoint** (a proposal for `/actuator/batch` was declined). Build a custom health indicator using `JobExplorer` to expose last execution status for critical jobs.

### Week 15: Alerting strategies

Define five essential alerts for batch jobs:

- **Job failure**: `spring_batch_job_seconds_count{status="FAILURE"} > 0`
- **Long-running job**: `spring_batch_job_active_seconds_active_count > 0` sustained for longer than expected
- **Stuck job**: Job in STARTED state for more than `expected_max_duration`
- **High item error rate**: `rate(batch_errors_total[5m]) / rate(batch_processed_total[5m]) > 0.05`
- **Missing execution** (dead man's switch): No new job execution detected within the expected schedule window — use Prometheus `absent()` function or a Healthchecks.io-style monitoring service

Configure Prometheus Alertmanager for routing to Slack, PagerDuty, or AWS SNS. In AWS-native stacks, use CloudWatch Alarms on ECS task exit codes and CloudWatch Logs Metric Filters.

### Week 16: Database and connection pool hardening

**Job repository cleanup** is critical for production — the metadata tables grow unboundedly. Implement a scheduled cleanup job that deletes executions older than 30–90 days, respecting foreign key constraints (delete order: step execution context → step execution → job execution context → job execution params → job execution → orphaned job instances). Naver's spring-batch-plus provides a built-in `DeleteMetadataJob` for this.

**HikariCP tuning for batch**: Set `maximum-pool-size` based on the formula **(CPU cores × 2) + effective_spindle_count** (for SSDs, spindle count = 1). For partitioned steps, pool size ≥ partition count + 2. Set `minimum-idle` equal to `maximum-pool-size` for a fixed pool. Enable `leak-detection-threshold: 60000` (60s). Monitor with Micrometer's auto-exposed HikariCP metrics (`hikaricp.connections.active`, `.idle`, `.pending`).

Use the `@BatchDataSource` annotation to create a **dedicated connection pool for Spring Batch metadata** separate from your application's business data pool.

### 🏗️ Milestone Project 4: Observable API data ingestion pipeline

Build a job that ingests data from a paginated REST API (use a custom `ItemReader` that handles pagination and rate limiting), processes and normalizes the data, and writes to PostgreSQL. Add full observability: Micrometer metrics (custom counters for API calls, rate limit hits), structured JSON logging with MDC, distributed tracing with OpenTelemetry, and a Prometheus alert rule for job failure. Include a metadata cleanup Tasklet. Deploy as a Docker container with a Prometheus endpoint. Provide a Grafana dashboard JSON.

---

## Phase 5: AWS containerized deployment patterns (weeks 17–20)

This phase integrates everything into production deployment on AWS EKS/ECS with proper CI/CD, graceful shutdown, and infrastructure automation.

### Week 17: Containerized batch job patterns on EKS

There are three deployment strategies for Spring Batch on Kubernetes:

**Strategy 1 — K8s Job/CronJob per execution (recommended)**: Package as a run-to-completion container. Pod starts, runs batch job, exits. Zero idle cost, clean lifecycle, native K8s isolation. JVM startup overhead can be mitigated with CRaC (Coordinated Restore at Checkpoint) or GraalVM native image. Set `restartPolicy: Never` and use `backoffLimit` for pod-level retries.

**Strategy 2 — Long-running Deployment**: Pods always running, jobs triggered via REST API or internal scheduler. No JVM startup cost, metrics always scrapeable. But: wasted resources during idle periods, requires horizontal pod autoscaling to be useful.

**Strategy 3 — AWS Batch on EKS**: Fully managed batch scheduling that runs on your existing EKS cluster. AWS Batch handles queue management, job scheduling, and scaling. Useful if you have many different batch jobs with varying resource requirements.

For most teams, **Strategy 1 (CronJob) for scheduled work + REST endpoint (Strategy 2) for on-demand triggers** is the optimal combination.

### Week 18: Graceful shutdown and production Kubernetes configuration

**Graceful shutdown** is critical for batch jobs — you must complete the current chunk and persist state before termination. Configure Spring Boot: `server.shutdown=graceful` and `spring.lifecycle.timeout-per-shutdown-phase=60s`. On SIGTERM, Spring Batch finishes the current chunk, commits the transaction, and updates the JobRepository. The job can then be restarted from the last checkpoint.

**Critical Kubernetes setting**: `terminationGracePeriodSeconds` must be ≥ `timeout-per-shutdown-phase` + `preStop` hook duration. For batch jobs processing large chunks, set **300–600 seconds**. Add a `preStop` hook with `sleep 10` to allow endpoint removal propagation.

Spring Batch 6.0 added a **built-in graceful shutdown hook on SIGTERM** (#5028) that makes this even more reliable.

Configure resource requests/limits carefully: batch jobs are typically CPU-and-memory-intensive. Set `requests` to guaranteed minimums and `limits` high enough to handle peak processing. Use `ephemeral-storage` limits to prevent container eviction from temp file usage.

### Week 19: AWS-native scheduling implementation

Implement **EventBridge Scheduler → ECS Fargate RunTask** for an ECS-deployed batch job. Create the EventBridge schedule via Terraform (`aws_scheduler_schedule` resource), configure the ECS task definition, and set up IAM roles for `ecs:RunTask` and `iam:PassRole`. Add a dead-letter queue (SQS) for failed invocations.

Then implement a **Step Functions state machine** that orchestrates a multi-step batch workflow: validation → processing → reporting, with parallel fan-out for partitioned processing and error catching with fallback steps. Use the `ecs:runTask.sync` integration to wait for ECS task completion.

### Week 20: CI/CD and deployment strategies

Build a complete CI/CD pipeline:

- **Build**: Gradle build → Docker image via Spring Boot Buildpacks (`./gradlew bootBuildImage`) or Jib plugin
- **Test**: Run `@SpringBatchTest` integration tests with Testcontainers (PostgreSQL) in CI
- **Push**: Push image to ECR with Git SHA tag
- **Deploy**: Helm chart with parameterized CronJob definition (image tag, cron schedule, resource limits, environment variables)
- **GitOps**: ArgoCD or Flux syncs Helm charts from Git to EKS

**Deployment strategies for batch**: Traditional blue/green doesn't directly apply to one-shot batch jobs. Instead: deploy the new version, schedule the next execution to use it, and keep the previous version available for restarting any failed executions from the old run. For canary testing, run the new version against a **subset of data** (controlled via job parameters) before full rollout.

**Schema migration**: Use Flyway with `spring.batch.jdbc.initialize-schema=never` — manage both business schema and Spring Batch metadata tables through version-controlled migration scripts.

### 🏗️ Milestone Project 5: Multi-format report generator on EKS

Build a job that reads from multiple sources (PostgreSQL + S3 CSV files), aggregates and joins the data via composite readers, generates reports in multiple formats (CSV summary + JSON detail), and uploads results to S3. Deploy on EKS as a CronJob with Helm. Implement graceful shutdown handling. Add EventBridge Scheduler as an alternative trigger for ECS. Include a full CI/CD pipeline with GitHub Actions → ECR → ArgoCD → EKS. Configure Prometheus monitoring with Pushgateway for ephemeral pod metrics.

---

## Phase 6: Mastery, capstone, and advanced topics (weeks 21–26+)

### Week 21–22: Anti-patterns and knowing when NOT to use Spring Batch

Study these **critical anti-patterns**:

- **Overusing `@EnableBatchProcessing` in Spring Boot**: This annotation **disables batch auto-configuration**, including schema initialization. Spring Boot's auto-configuration alone is usually sufficient.
- **Storing large objects in ExecutionContext**: It's serialized to the database — large objects cause performance degradation and serialization failures.
- **Thread-unsafe components in multi-threaded steps**: `JdbcCursorItemReader` is not thread-safe; `FlatFileItemReader` must be synchronized or use `SynchronizedItemStreamReader`.
- **Ignoring metadata cleanup**: `BATCH_*` tables grow without bounds. Schedule regular purges.
- **Wrong chunk size**: Too small (10) = excessive transaction overhead; too large (100K) = memory pressure and long transactions. Benchmark systematically.
- **Monolithic steps**: Cramming all logic into a Tasklet instead of using the clean reader/processor/writer pattern makes testing and maintenance painful.
- **Using `@Scheduled` in multi-pod deployments**: Every pod fires every schedule. Use K8s CronJob or ShedLock instead.

**When Spring Batch is the wrong tool**: For simple scheduled tasks (use plain `@Scheduled`), big data at terabyte+ scale (use **Apache Spark** or **Flink**), workflow orchestration across systems (use **Apache Airflow** or **Temporal**), cloud-native serverless ETL (use **AWS Glue** or **AWS Batch**), simple background job queues (use **JobRunr** — simpler API, built-in dashboard), real-time streaming (use **Kafka Streams** or Flink), or one-off migrations (use plain SQL scripts or **Flyway**).

**When Spring Batch IS right**: You're in the Spring ecosystem, need auditable/restartable batch processing with metadata tracking, processing thousands to millions of records (not billions) with transactional guarantees, and need skip/retry/restart resilience.

**Resources:**
- JavaNexus "Common Spring Batch Pitfalls": https://javanexus.com/blog/common-spring-batch-pitfalls
- JobRunr comparison blog: https://www.jobrunr.io/en/blog/2023-04-11-java-batch-processing/

### Week 23–24: Advanced topics and Spring Batch 6.0 features

Explore cutting-edge features:

- **Spring Batch 6.0 highlights**: API to recover failed job executions, Java Flight Recorder observability, ability to externally stop any step, revised concurrency model, local chunking support, remote step executions, SEDA with Spring Integration MessageChannels, and a modern command-line batch operator. Review the migration guide: https://github.com/spring-projects/spring-batch/wiki/Spring-Batch-6.0-Migration-Guide
- **GraalVM native compilation**: Spring Batch supports GraalVM native image since 5.1 — dramatically reduces JVM startup time for CronJob-style ephemeral containers (from ~5s to ~100ms). Critical for short-running batch jobs.
- **MongoDB-backed JobRepository** (Spring Batch 5.2+): For high-concurrency environments where `OptimisticLockingFailureException` on JDBC repositories becomes a problem.
- **Kotlin coroutines considerations**: Spring Batch does NOT natively support coroutines. Its processing model is fundamentally synchronous. You can use `runBlocking {}` inside batch components to call suspend functions, but this negates coroutine benefits. With Java 21 **virtual threads**, you get similar benefits without coroutines — configure a virtual-thread-based `TaskExecutor` for multi-threaded steps.
- **Composed task orchestration**: Study complex DAG patterns — sequential, parallel, and conditional task composition for enterprise batch landscapes.

### Week 25–26+: Capstone project

### 🏗️ Milestone Project 6 (Capstone): Enterprise event-driven batch platform on AWS EKS

Build a production-grade batch processing platform that demonstrates mastery across all topics:

**Architecture**: An event-driven pipeline where S3 file uploads (via EventBridge → SQS) trigger a Spring Batch job running on EKS. The job processes financial transaction files (CSV/JSON) through a multi-step pipeline:

1. **Validation step**: Read and validate input files, quarantine invalid records with `SkipListener`
2. **Enrichment step**: Call an external API to enrich transaction records, with retry logic for transient failures
3. **Processing step**: Partitioned step (8 partitions by date range) that applies business rules and transformations using `JdbcPagingItemReader` for thread-safe, restartable processing
4. **Aggregation step**: Generate summary statistics and write aggregated reports to S3
5. **Notification step**: Tasklet that sends completion notification via SNS

**Scheduling**: K8s CronJob for nightly full reconciliation run + REST API endpoint for on-demand reprocessing + SQS-triggered execution for event-driven file processing.

**Observability**: Full Micrometer metrics exported to Prometheus via Pushgateway, structured JSON logging with MDC propagation to CloudWatch, distributed tracing via OpenTelemetry to Jaeger/Tempo, Grafana dashboard with job duration, throughput, error rates, and active job panels. Alerting rules for failures, stuck jobs, and missed schedules.

**Operations**: Helm chart deployment via ArgoCD, Flyway-managed schema migrations (business + batch metadata), HikariCP tuning with dedicated `@BatchDataSource`, graceful shutdown with `terminationGracePeriodSeconds: 300`, metadata cleanup job, idempotent writes with UPSERT.

**Testing**: Full test suite with `@SpringBatchTest`, Testcontainers (PostgreSQL, LocalStack for S3/SQS), end-to-end test of restart from failure.

This capstone should take **2–4 weeks** depending on your pace and serves as a portfolio piece demonstrating production-grade Spring Batch mastery.

---

## Complete resource reference by phase

| Phase | Key Resources |
|---|---|
| **Phase 1** | Spring Academy free course (Mahmoud Ben Hassine); Spring Batch reference docs ch. 1–4; "The Definitive Guide to Spring Batch" ch. 1–4; Naver spring-batch-plus; ddubson/spring-batch-examples |
| **Phase 2** | Spring Batch reference (error handling, flow); "Definitive Guide" ch. 7–8; Baeldung conditional flow; K8s CronJob docs; EventBridge Scheduler docs |
| **Phase 3** | Spring Batch reference (scaling chapter); "Definitive Guide" ch. 11–12; galovics/spring-batch-remote-partitioning |
| **Phase 4** | Trifork observability blog; Spring Batch monitoring docs; Grafana dashboard 11436; HikariCP wiki |
| **Phase 5** | AWS Batch on EKS blueprint; Spring Boot Buildpacks docs; Helm documentation; ArgoCD docs |
| **Phase 6** | Spring Batch 6.0 migration guide; GraalVM native docs; "Definitive Guide" ch. 13 (cloud native) |

**Community support**: As of January 2026, the Spring Batch team has moved all support to **GitHub Discussions** (https://github.com/spring-projects/spring-batch/discussions). Stack Overflow's `[spring-batch]` tag has a large archive but is no longer officially supported. Join the Kotlin Slack `#spring` channel for Kotlin-specific questions.

---

## Conclusion: The path from zero to production mastery

The six phases map a deliberate progression: **foundations → resilience → scale → observability → deployment → mastery**. The most important insight for a Kotlin developer on AWS is that Spring Batch's power lies not in any single feature but in the **composition** of chunk processing, transactional guarantees, metadata-driven restartability, and pluggable scaling — all orchestrated by Kubernetes-native scheduling on EKS. The Naver Kotlin DSL fills the gap the Spring team declined to address, and the run-to-completion CronJob pattern eliminates the resource waste of always-on schedulers. Resist the temptation to over-engineer early — start with single-threaded chunk processing in Phase 1, and you'll understand exactly *why* partitioning and remote chunking exist by the time you need them in Phase 3. The capstone project is intentionally ambitious: if you can build it, you can build any batch system a production environment demands.