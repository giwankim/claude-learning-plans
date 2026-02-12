---
title: "Spring Batch Projects"
category: "Spring & Spring Boot"
description: "12 progressive Kotlin projects with Spring Batch"
---

# Spring Batch Learning Path: 12 Progressive Kotlin Projects

Spring Batch remains the gold standard for enterprise batch processing in the JVM ecosystem, and version **5.2.x** (requiring Java 17+ and Jakarta EE 9) brings cleaner APIs, better observability, and native Kotlin DSL support through libraries like Spring Batch Plus. This guide presents **12 hands-on projects** progressing from foundational concepts to production-ready distributed processing patterns, each designed around real-world data synchronization scenarios you'll encounter professionally.

The key architectural shift in Spring Batch 5.x eliminates `JobBuilderFactory` and `StepBuilderFactory` in favor of direct `JobBuilder` and `StepBuilder` with explicit `JobRepository` injection—a change that actually simplifies Kotlin configurations. Combined with Naver's **Spring Batch Plus** library, you'll write idiomatic Kotlin DSL instead of verbose Java-style builders.

---

## Foundation: project setup and tooling

Before diving into projects, establish your development environment with these dependencies in `build.gradle.kts`:

```kotlin
plugins {
    id("org.springframework.boot") version "3.4.0"
    kotlin("jvm") version "2.0.0"
    kotlin("plugin.spring") version "2.0.0"
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-batch")
    implementation("com.navercorp.spring:spring-boot-starter-batch-plus-kotlin:1.2.0")
    implementation("com.mysql:mysql-connector-j")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    testImplementation("org.springframework.batch:spring-batch-test")
    testImplementation("io.mockk:mockk:1.13.8")
}
```

Use Kotlin **data classes** for all batch items (automatic `equals()`, `hashCode()`, immutability), **extension functions** for reader/writer configuration, and **MockK** for testing. The Spring Batch Plus DSL replaces builder chains with a clean `batch { job("name") { step("name") { ... } } }` syntax.

---

## Beginner projects: mastering the fundamentals

### Project 1: CSV product catalog importer

**Description**: Build a job that reads product data from a CSV file, validates and transforms each record, then inserts products into a MySQL database. This foundational project teaches the entire chunk-oriented processing pipeline.

**Learning objectives**:
- Understand the **Job → Step → Chunk** hierarchy
- Configure `FlatFileItemReader` with Kotlin data classes
- Implement `ItemProcessor` for validation and transformation
- Use `JdbcBatchItemWriter` for efficient database inserts
- Set appropriate **chunk sizes** (commit intervals)

**Key Spring Batch concepts**: `Job`, `Step`, `ItemReader`, `ItemProcessor`, `ItemWriter`, chunk-based processing, `@StepScope` for late binding

**Implementation approach**:
```kotlin
data class ProductCsv(val sku: String, val name: String, val price: String)
data class Product(val sku: String, val name: String, val priceInCents: Long)

@Bean
fun productImportJob(batch: BatchDsl): Job = batch {
    job("productImportJob") {
        step("importStep") {
            chunk<ProductCsv, Product>(100, transactionManager) {
                reader(csvReader())
                processor { csv -> 
                    if (csv.price.toBigDecimalOrNull() == null) null  // Filter invalid
                    else Product(csv.sku, csv.name.trim(), (csv.price.toBigDecimal() * 100).toLong())
                }
                writer(jdbcWriter())
            }
        }
    }
}
```

**Practical use case**: E-commerce platforms regularly receive product feeds from vendors as CSV files. This pattern handles nightly catalog updates where **10,000-100,000 products** must be validated, normalized, and loaded before the site opens.

---

### Project 2: Database customer export to JSON

**Description**: Extract customer records from MySQL, transform them to a JSON-friendly format, and write to a JSON Lines file. This reverses the typical import pattern and introduces database readers.

**Learning objectives**:
- Configure `JdbcCursorItemReader` vs `JdbcPagingItemReader` (understand trade-offs)
- Use `JsonFileItemWriter` with Jackson Kotlin module
- Implement **job parameters** for dynamic file naming
- Handle nullable fields safely with Kotlin's null-safe operators

**Key Spring Batch concepts**: `JdbcCursorItemReader`, `FlatFileItemWriter`, `JobParameters`, `@Value("#{jobParameters['outputFile']}")`

**Implementation approach**: Use `JdbcPagingItemReader` with a sort key for restart capability. The processor transforms database entities into DTOs optimized for JSON output. Configure the writer with Jackson's `kotlinModule()` for proper Kotlin data class serialization.

**Practical use case**: Marketing teams need customer exports for email campaign tools like Mailchimp or HubSpot. The export job runs nightly, producing a JSON file uploaded to the marketing platform.

---

### Project 3: Tasklet-based file archival system

**Description**: Build a multi-step job where a tasklet moves processed files to an archive directory after the main processing step completes. Learn when tasklets are preferable to chunk processing.

**Learning objectives**:
- Understand **tasklet vs chunk** decision criteria
- Chain multiple steps sequentially with `.next()`
- Share data between steps using `ExecutionContext`
- Implement file system operations in tasklets

**Key Spring Batch concepts**: `Tasklet`, `RepeatStatus`, `ExecutionContext`, step chaining, `@BeforeStep` for accessing context

**Implementation approach**:
```kotlin
@Bean
fun archiveJob(batch: BatchDsl): Job = batch {
    job("archiveJob") {
        step("processFiles") { chunk<...>(...) { ... } }
        step("archiveFiles") {
            tasklet({ contribution, chunkContext ->
                val processedDir = File("/data/processed")
                val archiveDir = File("/data/archive/${LocalDate.now()}")
                processedDir.listFiles()?.forEach { it.renameTo(File(archiveDir, it.name)) }
                RepeatStatus.FINISHED
            }, transactionManager)
        }
    }
}
```

**Practical use case**: Financial institutions process daily transaction files, then must archive originals with timestamps for audit compliance. The tasklet pattern handles this non-iterative cleanup work.

---

### Project 4: Order validation with basic error handling

**Description**: Process order records where some contain invalid data. Implement skip logic to continue processing despite bad records, logging skipped items for later review.

**Learning objectives**:
- Configure **fault-tolerant steps** with `.faultTolerant()`
- Define skip policies with `skip()` and `skipLimit()`
- Distinguish skippable exceptions (data quality) from fatal exceptions
- Implement `SkipListener` to log skipped items

**Key Spring Batch concepts**: `faultTolerant()`, `skip()`, `skipLimit()`, `SkipListener`, exception classification

**Implementation approach**: Define custom exceptions like `InvalidOrderException` and `MissingCustomerException`. Configure the step to skip these up to a threshold while letting `DataAccessException` fail the job immediately. The `SkipListener` writes skipped records to a separate "error" table for manual review.

**Practical use case**: Order imports from partner systems often contain **2-5% invalid records** (missing customer IDs, invalid product SKUs). The business requires processing valid orders immediately while flagging invalid ones for customer service follow-up.

---

## Intermediate projects: building production-ready jobs

### Project 5: Multi-step order fulfillment pipeline

**Description**: Build a job with multiple steps: validate orders → reserve inventory → calculate shipping → generate invoices. Learn step orchestration and conditional flows.

**Learning objectives**:
- Design **multi-step job flows** with proper sequencing
- Implement `JobExecutionDecider` for branching logic
- Use conditional transitions (`.on("COMPLETED").to(stepB)`)
- Promote data between steps via `ExecutionContext`

**Key Spring Batch concepts**: `Flow`, `JobExecutionDecider`, conditional transitions, `FlowExecutionStatus`, `ExecutionContextPromotionListener`

**Implementation approach**:
```kotlin
@Bean
fun fulfillmentJob(batch: BatchDsl): Job = batch {
    job("orderFulfillmentJob") {
        step("validateOrders") { ... }
            .on("COMPLETED").to("checkInventory")
            .on("FAILED").fail()
        step("checkInventory") { ... }
        decider("shippingDecider") { _, stepExecution ->
            if (stepExecution.executionContext.getInt("oversizedCount") > 0)
                FlowExecutionStatus("FREIGHT")
            else FlowExecutionStatus("STANDARD")
        }
        .on("FREIGHT").to("calculateFreightShipping")
        .on("STANDARD").to("calculateStandardShipping")
        step("generateInvoices") { ... }
    }
}
```

**Practical use case**: E-commerce order processing requires sequential operations where each step depends on the previous. Inventory reservation must succeed before shipping calculation; oversized items route to freight carriers instead of standard shipping.

---

### Project 6: Customer data synchronization with retry logic

**Description**: Sync customer data from a source MySQL database to a target database, implementing retry for transient database failures (deadlocks, connection timeouts) and skip for data validation errors.

**Learning objectives**:
- Combine **skip and retry** in the same step
- Configure retry policies with `retry()`, `retryLimit()`, and backoff
- Use multiple data sources in Spring Batch
- Implement idempotent writes for safe restarts

**Key Spring Batch concepts**: `retry()`, `retryLimit()`, `BackOffPolicy`, `ExponentialBackOffPolicy`, combining skip and retry

**Implementation approach**: Configure two `DataSource` beans (source and target). The reader queries the source; the writer performs `UPSERT` (INSERT ON DUPLICATE KEY UPDATE) to the target. Retry `DeadlockLoserDataAccessException` up to 3 times with exponential backoff. Skip `DataIntegrityViolationException` for records that violate target constraints.

**Practical use case**: Microservices architectures often maintain denormalized copies of data across services. Nightly sync jobs reconcile customer records between the auth service database and the order service database, handling transient cluster issues gracefully.

---

### Project 7: Sales reporting with listeners and metrics

**Description**: Generate a daily sales summary report, using listeners to track processing statistics, execution time, and send Slack notifications on completion or failure.

**Learning objectives**:
- Implement `JobExecutionListener` and `StepExecutionListener`
- Use `ChunkListener` for progress tracking
- Integrate with external notification systems
- Leverage Micrometer metrics for observability

**Key Spring Batch concepts**: `JobExecutionListener`, `StepExecutionListener`, `ChunkListener`, `ItemReadListener`, `ItemWriteListener`

**Implementation approach**:
```kotlin
@Component
class SalesReportListener(private val slackClient: SlackClient) : JobExecutionListener {
    override fun beforeJob(execution: JobExecution) {
        MDC.put("jobId", execution.id.toString())
        log.info("Starting sales report generation")
    }
    
    override fun afterJob(execution: JobExecution) {
        val stats = """
            Job: ${execution.jobInstance.jobName}
            Status: ${execution.status}
            Duration: ${Duration.between(execution.startTime, execution.endTime)}
            Records processed: ${execution.stepExecutions.sumOf { it.writeCount }}
        """.trimIndent()
        
        if (execution.status == BatchStatus.FAILED)
            slackClient.sendAlert("#alerts", "❌ Sales report FAILED\n$stats")
        else
            slackClient.sendMessage("#reports", "✅ Sales report complete\n$stats")
    }
}
```

**Practical use case**: Finance teams require daily sales summaries with reliable notifications. Operations teams need visibility into job performance and immediate alerts when critical reports fail.

---

### Project 8: Restartable data migration with checkpoints

**Description**: Migrate 10 million legacy records to a new schema, supporting restarts from the exact point of failure without reprocessing completed chunks.

**Learning objectives**:
- Understand Spring Batch's **restart mechanism**
- Configure `JdbcPagingItemReader` with proper sort keys
- Test restart scenarios deliberately
- Manage `JobInstance` vs `JobExecution` concepts

**Key Spring Batch concepts**: `JobRepository` metadata, `ExecutionContext` checkpointing, `allowStartIfComplete()`, `startLimit()`, paging reader sort keys

**Implementation approach**: Use `JdbcPagingItemReader` with a unique, indexed sort key (like `id`). Spring Batch automatically stores the last processed page in `ExecutionContext`. On restart, it resumes from that page. Validate by processing 5 million records, simulating a failure, then restarting to confirm only remaining records process.

**Practical use case**: Large-scale migrations (millions of records) commonly encounter transient failures—network blips, database maintenance windows, or deployment interruptions. Restart capability prevents costly full reprocessing.

---

## Advanced projects: distributed and high-performance processing

### Project 9: Partitioned customer statement generation

**Description**: Generate monthly statements for 1 million customers using partitioned parallel processing. Divide customers by ID range across multiple threads for 10x throughput improvement.

**Learning objectives**:
- Implement `Partitioner` interface for work distribution
- Configure local partitioning with `TaskExecutor`
- Tune `gridSize` and thread pool for optimal performance
- Handle thread-safe readers and writers

**Key Spring Batch concepts**: `Partitioner`, `PartitionHandler`, `StepExecutionSplitter`, `gridSize`, `TaskExecutor`, thread safety

**Implementation approach**:
```kotlin
@Bean
fun statementPartitioner(): Partitioner = Partitioner { gridSize ->
    val min = customerRepository.findMinId()
    val max = customerRepository.findMaxId()
    val range = (max - min) / gridSize
    
    (0 until gridSize).associate { i ->
        "partition$i" to ExecutionContext().apply {
            putLong("minId", min + (i * range))
            putLong("maxId", min + ((i + 1) * range) - 1)
        }
    }
}

@Bean
fun statementJob(batch: BatchDsl): Job = batch {
    job("customerStatementJob") {
        step("partitionedStatements") {
            partitioner("workerStep", statementPartitioner())
            step(workerStep())
            gridSize(10)
            taskExecutor(Executors.newFixedThreadPool(10))
        }
    }
}
```

**Practical use case**: Banks and telecom companies generate millions of monthly statements. Sequential processing taking **8+ hours** becomes unacceptable. Partitioning across 10 threads reduces this to **under 1 hour** while maintaining restart capability per partition.

---

### Project 10: Real-time cache synchronization with Redis

**Description**: Sync product catalog changes from MySQL to Redis cache, supporting both full refreshes and incremental delta syncs based on modification timestamps.

**Learning objectives**:
- Integrate Redis with Spring Batch (`RedisTemplate`)
- Implement **delta sync patterns** using timestamp watermarks
- Design cache warming strategies
- Handle cache invalidation scenarios

**Key Spring Batch concepts**: Custom `ItemWriter` with Redis, job parameters for sync mode, timestamp-based reader filtering

**Implementation approach**: Create a `RedisCacheWriter` that serializes products to JSON and stores them with appropriate TTLs. For delta syncs, the reader queries `WHERE updated_at > :lastSyncTime`. Store the high-water mark timestamp in Redis itself. A scheduled job runs every 5 minutes for deltas; a separate weekly job performs full refresh.

```kotlin
@Component
class ProductCacheWriter(private val redisTemplate: RedisTemplate<String, String>) 
    : ItemWriter<Product> {
    override fun write(chunk: Chunk<out Product>) {
        val ops = redisTemplate.opsForValue()
        chunk.items.forEach { product ->
            ops.set("product:${product.sku}", objectMapper.writeValueAsString(product), 24, TimeUnit.HOURS)
        }
        redisTemplate.opsForValue().set("cache:lastSync", Instant.now().toString())
    }
}
```

**Practical use case**: High-traffic e-commerce sites cache product data in Redis to reduce database load. Batch sync jobs ensure cache consistency while avoiding the complexity of event-driven cache invalidation.

---

### Project 11: Event-driven order processing with Kafka

**Description**: Process order events from Kafka topics in configurable micro-batches, combining streaming ingestion with batch processing efficiency.

**Learning objectives**:
- Configure `KafkaItemReader` for topic consumption
- Implement **dead letter queue** patterns for failed messages
- Handle consumer group coordination
- Balance batch size with latency requirements

**Key Spring Batch concepts**: `KafkaItemReader`, custom `ItemWriter` for Kafka DLQ, commit interval tuning, consumer configuration

**Implementation approach**: Configure `KafkaItemReader` to read from the `orders` topic with a specific consumer group. The processor validates and enriches orders. Failed items route to a DLQ topic via a `SkipListener`. Successful orders write to MySQL. Schedule the job to run every minute with chunk size of 100.

**Practical use case**: Order processing systems often receive orders via Kafka for decoupling but require transactional batch processing with retry/skip capabilities. This hybrid approach combines Kafka's durability with Spring Batch's processing guarantees.

---

### Project 12: Distributed data sync with remote chunking

**Description**: Implement cross-system data synchronization where a manager node reads data and distributes processing across multiple worker nodes via Kafka, enabling horizontal scaling.

**Learning objectives**:
- Understand **remote chunking architecture** (manager reads, workers process/write)
- Configure `ChunkMessageChannelItemWriter` and worker integration flows
- Handle distributed transaction semantics
- Monitor distributed job execution

**Key Spring Batch concepts**: Remote chunking, `RemoteChunkingManagerStepBuilderFactory`, `RemoteChunkingWorkerBuilder`, Spring Integration channels

**Implementation approach**:
```kotlin
// Manager node - reads data, sends chunks to workers
@Bean
fun managerStep(managerStepBuilderFactory: RemoteChunkingManagerStepBuilderFactory<SourceRecord, TargetRecord>) =
    managerStepBuilderFactory.get("syncManagerStep")
        .chunk<SourceRecord, TargetRecord>(200)
        .reader(sourceSystemReader())
        .outputChannel(outgoingRequestsToKafka())
        .inputChannel(incomingRepliesFromKafka())
        .build()

// Worker nodes - process and write chunks
@Bean
fun workerFlow(workerBuilder: RemoteChunkingWorkerBuilder<SourceRecord, TargetRecord>) =
    workerBuilder
        .itemProcessor(transformProcessor())
        .itemWriter(targetSystemWriter())
        .inputChannel(incomingRequestsFromKafka())
        .outputChannel(outgoingRepliesToKafka())
        .build()
```

**Practical use case**: Enterprise data synchronization between ERP systems, where processing/transformation is the bottleneck. A single manager node reads from SAP, distributes work across 5 worker nodes that transform and write to Salesforce, achieving **5x throughput** over single-node processing.

---

## Data synchronization patterns reference

Since data sync is central to your professional use cases, here's a decision framework:

| Pattern | When to use | Spring Batch implementation |
|---------|-------------|----------------------------|
| **Full sync** | Initial loads, small datasets (<100K records), weekly reconciliation | Simple reader→writer, truncate-and-reload or upsert |
| **Delta sync** | Large datasets, frequent runs, minimal latency tolerance | Timestamp-based reader filter, watermark tracking in job parameters |
| **CDC-driven** | Near real-time requirements, complex change tracking | Kafka consumer reading Debezium events → Spring Batch processor |
| **Bidirectional** | Two-way synchronization, conflict resolution needed | Dual jobs with conflict detection in processor, last-write-wins or merge logic |

For delta syncs, always ensure source tables have indexed `updated_at` columns and handle clock skew between systems by using small overlap windows (e.g., `WHERE updated_at >= :lastSync - INTERVAL 1 MINUTE`).

---

## Conclusion

This progression builds competency systematically: **Projects 1-4** establish the mental model of chunk processing, data classes, and error handling that every subsequent project relies upon. **Projects 5-8** introduce the orchestration patterns (flows, listeners, restartability) that distinguish production jobs from tutorials. **Projects 9-12** tackle the performance and distribution challenges of enterprise-scale processing.

Start with the CSV importer, ensure your testing setup works with MockK and `spring-batch-test`, then progress sequentially. Each project reinforces previous concepts while introducing exactly one new complexity dimension. By project 12, you'll have implemented the same remote chunking pattern used by financial institutions processing millions of daily transactions.

The Kotlin advantage compounds throughout: data classes eliminate boilerplate, null safety prevents runtime surprises in processors, and the Spring Batch Plus DSL makes job configuration readable. Combined with MySQL for persistence, Redis for caching, and Kafka for distribution, this stack handles everything from simple file imports to enterprise data synchronization.