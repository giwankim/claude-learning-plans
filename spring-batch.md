# 16-week Spring Batch mastery plan for Kotlin developers

Spring Batch 5.x represents a significant evolution in Java batch processing, requiring Java 17+ and introducing breaking API changes that demand intentional study. This structured plan transforms foundational documentation knowledge into production-ready expertise through **160-200 hours** of focused learning, building progressively from architecture reinforcement through advanced Kafka integration and Kubernetes deployment.

The curriculum assumes Spring Boot 3.x proficiency and existing familiarity with basic concepts (Job, Step, ItemReader/Processor/Writer) from the official documentation. Each week combines theory, hands-on coding, and practical projects using MySQL as the primary database.

## Phase 1: Foundational reinforcement (Weeks 1-4)

### Week 1: Architecture deep dive and Spring Batch 5.x migration patterns
**Time commitment: 10-12 hours**

The most critical architectural change in Spring Batch 5.x is the removal of `JobBuilderFactory` and `StepBuilderFactory`. You now inject `JobRepository` directly and construct builders explicitly:

```kotlin
@Configuration
class BatchConfig(
    private val jobRepository: JobRepository,
    private val transactionManager: PlatformTransactionManager
) {
    @Bean
    fun importJob(): Job = JobBuilder("importJob", jobRepository)
        .incrementer(RunIdIncrementer())
        .start(processStep())
        .build()

    @Bean
    fun processStep(): Step = StepBuilder("processStep", jobRepository)
        .chunk<Person, Person>(100, transactionManager)
        .reader(reader())
        .processor(processor())
        .writer(writer())
        .build()
}
```

**Study materials:**
- Spring Batch 5.0 Migration Guide on GitHub Wiki (essential reading)
- Official Reference Documentation: Domain Language of Batch chapter
- Baeldung: "Introduction to Spring Batch" (updated for 5.2.0)

**Hands-on exercises:**
1. Set up a Spring Boot 3.x + Kotlin project with Spring Batch 5.x
2. Configure MySQL JobRepository with schema initialization
3. Implement a simple Job demonstrating the new builder patterns
4. Explore metadata tables using MySQL Workbench to understand state tracking

**MySQL Schema Setup:**
```properties
spring.datasource.url=jdbc:mysql://localhost:3306/batchdb
spring.datasource.username=batch_user
spring.datasource.password=secure_password
spring.batch.jdbc.initialize-schema=always
spring.batch.jdbc.table-prefix=BATCH_
```

---

### Week 2: Job instance lifecycle and execution context mastery
**Time commitment: 10-12 hours**

Understanding the distinction between **JobInstance** and **JobExecution** is fundamental. A JobInstance represents a logical run uniquely identified by job name plus identifying parameters. Multiple JobExecutions can belong to one JobInstance (when retrying failures), but a completed JobInstance cannot be re-run with identical parameters.

**Key concepts to master:**
- Job parameters: identifying vs non-identifying, new type support in 5.x
- ExecutionContext serialization (changed from Jackson to Base64 by default)
- Step vs Job ExecutionContext scope and data sharing patterns
- How Spring Batch persists state in the **9 metadata tables**

**Study materials:**
- Reference Documentation: Configuring and Running a Job
- Reference Documentation: The Meta-Data Schema (Appendix)
- LinkedIn Learning: "Spring: Spring Batch" by Kevin Bowersox (Chapter 2)

**Project: State-aware file processor**
Build a job that processes a large CSV file, stores progress in ExecutionContext, and demonstrates restart capability:
```kotlin
class StatefulFileReader : ItemStreamReader<Record> {
    private var currentLine = 0
    
    override fun open(executionContext: ExecutionContext) {
        if (executionContext.containsKey("currentLine")) {
            currentLine = executionContext.getInt("currentLine")
        }
    }
    
    override fun update(executionContext: ExecutionContext) {
        executionContext.putInt("currentLine", currentLine)
    }
}
```

---

### Week 3: Chunk-oriented processing vs tasklet patterns
**Time commitment: 10-12 hours**

Chunk processing reads items individually, processes them, then writes in batches within a single transaction. This provides automatic checkpoint/restart semantics. Tasklets execute as single units—ideal for setup/cleanup operations, stored procedures, or file management tasks.

**Decision matrix:**
| Use Chunk Processing | Use Tasklets |
|---------------------|--------------|
| Processing millions of records | File cleanup/archival |
| Need intermediate commits | Running stored procedures |
| Memory constraints | Pre/post processing steps |
| Restart from failure point | Single SQL operations |

**Study materials:**
- Baeldung: "Tasklet vs Chunk in Spring Batch"
- Reference Documentation: Chunk-oriented Processing
- ddubson/spring-batch-examples: Examples 01-07 (Kotlin)

**Project: Hybrid job architecture**
Create a job with:
1. Tasklet step: Validate input file existence and format
2. Chunk step: Process records with configurable chunk size
3. Tasklet step: Archive processed file and send notification

---

### Week 4: ItemReader, ItemProcessor, ItemWriter contracts
**Time commitment: 10-12 hours**

These three interfaces form the core of chunk processing. Understanding their contracts—especially around null handling and lifecycle methods—prevents subtle bugs.

**Critical Kotlin considerations:**
```kotlin
// ItemProcessor returning null filters the item (skips writing)
@Bean
fun processor(): ItemProcessor<RawData, ProcessedData?> = ItemProcessor { raw ->
    if (raw.isValid()) ProcessedData(raw) else null  // null = skip
}

// SAM conversion works cleanly with lambdas
@Bean
fun simpleProcessor(): ItemProcessor<String, String> = ItemProcessor { 
    it.uppercase()
}
```

**Lifecycle methods to implement:**
- `ItemStream.open()` - Initialize resources
- `ItemStream.update()` - Save state for restartability
- `ItemStream.close()` - Release resources

**Study materials:**
- Reference Documentation: ItemReader and ItemWriter
- Spring Academy Course: Building a Batch Application (FREE, official)
- ddubson/spring-batch-examples: Examples 08-22

**Project: Multi-format data pipeline**
Build readers/writers for CSV, JSON, and database sources demonstrating the adapter pattern and composite patterns.

---

## Phase 2: Core patterns and techniques (Weeks 5-8)

### Week 5: Error handling with skip and retry policies
**Time commitment: 10-12 hours**

Production batch jobs must handle bad data gracefully. Spring Batch's fault-tolerant step configuration provides declarative skip and retry policies:

```kotlin
@Bean
fun faultTolerantStep(): Step = StepBuilder("faultTolerantStep", jobRepository)
    .chunk<Order, ProcessedOrder>(100, transactionManager)
    .reader(orderReader())
    .processor(orderProcessor())
    .writer(orderWriter())
    .faultTolerant()
    .skipLimit(100)
    .skip(ValidationException::class.java)
    .skip(MalformedDataException::class.java)
    .noSkip(DatabaseException::class.java)
    .retryLimit(3)
    .retry(TransientDataAccessException::class.java)
    .listener(skipListener())
    .build()
```

**Study materials:**
- Reference Documentation: Configuring Skip Logic
- Baeldung: "Skip Logic in Spring Batch"
- ddubson/spring-batch-examples: Examples 23-26 (Error Handling)

**Project: Resilient data importer**
Process a dataset with intentionally corrupted records. Implement skip listeners to log failures to a dead-letter table for later analysis.

---

### Week 6: Listeners and job flow control
**Time commitment: 10-12 hours**

Listeners provide hooks into every phase of batch execution. Spring Batch 5.x supports both interface implementation and annotation-based listeners:

```kotlin
@Component
class AuditListener : StepExecutionListener, ChunkListener {
    override fun beforeStep(stepExecution: StepExecution) {
        logger.info("Starting ${stepExecution.stepName}")
    }
    
    override fun afterStep(stepExecution: StepExecution): ExitStatus {
        logger.info("Completed: ${stepExecution.readCount} read, ${stepExecution.writeCount} written")
        return stepExecution.exitStatus
    }
    
    override fun afterChunk(context: ChunkContext) {
        // Emit metrics after each chunk
    }
}
```

**Conditional flow with deciders:**
```kotlin
@Bean
fun conditionalJob(): Job = JobBuilder("conditionalJob", jobRepository)
    .start(validationStep())
    .on("VALID").to(processStep())
    .from(validationStep())
    .on("INVALID").to(errorHandlingStep())
    .from(validationStep())
    .on("*").fail()
    .end()
    .build()

@Bean
fun decider() = JobExecutionDecider { jobExecution, stepExecution ->
    when {
        stepExecution?.exitStatus?.exitCode == "COMPLETED_WITH_SKIPS" -> 
            FlowExecutionStatus("NEEDS_REVIEW")
        else -> FlowExecutionStatus.COMPLETED
    }
}
```

**Study materials:**
- Reference Documentation: Intercepting Step Execution
- Reference Documentation: Conditional Flow
- Udemy: "Spring Batch Mastery" (Listeners module)

**Project: Audit trail system**
Implement comprehensive logging and metrics collection using listeners at job, step, chunk, and item levels.

---

### Week 7: Parallel processing strategies
**Time commitment: 12-14 hours**

Spring Batch offers four scaling models, each with distinct trade-offs:

| Strategy | Use Case | Restartability | Complexity |
|----------|----------|----------------|------------|
| Multi-threaded step | CPU-bound processing | Lost | Low |
| Parallel steps | Independent data flows | Preserved | Low |
| Partitioning | Database ranges, file splits | Preserved | Medium |
| Remote chunking | Distributed processing | Complex | High |

**Multi-threaded step (simplest, loses restartability):**
```kotlin
@Bean
fun multithreadedStep(): Step = StepBuilder("step", jobRepository)
    .chunk<Data, Data>(100, transactionManager)
    .reader(SynchronizedItemStreamReader(fileReader())) // Thread-safe wrapper
    .processor(processor())
    .writer(writer())
    .taskExecutor(threadPoolTaskExecutor())
    .throttleLimit(4)
    .build()

@Bean
fun threadPoolTaskExecutor(): TaskExecutor = ThreadPoolTaskExecutor().apply {
    corePoolSize = 4
    maxPoolSize = 8
    setThreadNamePrefix("batch-")
}
```

**Local partitioning (preserves restartability):**
```kotlin
@Bean
fun partitionedStep(): Step = StepBuilder("partitionedStep", jobRepository)
    .partitioner("workerStep", columnRangePartitioner())
    .step(workerStep())
    .gridSize(10)
    .taskExecutor(taskExecutor())
    .build()

class ColumnRangePartitioner(private val jdbcTemplate: JdbcTemplate) : Partitioner {
    override fun partition(gridSize: Int): Map<String, ExecutionContext> {
        val min = jdbcTemplate.queryForObject("SELECT MIN(id) FROM orders", Long::class.java)!!
        val max = jdbcTemplate.queryForObject("SELECT MAX(id) FROM orders", Long::class.java)!!
        val range = (max - min) / gridSize + 1
        
        return (0 until gridSize).associate { i ->
            "partition$i" to ExecutionContext().apply {
                putLong("minId", min + (i * range))
                putLong("maxId", min + ((i + 1) * range) - 1)
            }
        }
    }
}
```

**Study materials:**
- Reference Documentation: Scaling and Parallel Processing
- ddubson/spring-batch-examples: Examples 27-31 (Scaling)
- YouTube: "High Performance Batch Processing" by Michael Minella

**Project: Partitioned database migration**
Migrate **1 million records** between MySQL tables using partitioning. Benchmark against single-threaded baseline.

---

### Week 8: Chunk size tuning and performance optimization
**Time commitment: 10-12 hours**

Chunk size dramatically affects performance. Too small increases transaction overhead; too large risks memory pressure and long rollbacks on failure.

**Tuning guidelines:**
- Start with chunk size = 100-500 for most workloads
- Increase for simple transformations with fast writers
- Decrease for complex processing or slow external calls
- Monitor commit frequency vs throughput trade-off

**Performance optimization techniques:**
1. Use `JdbcBatchItemWriter` with `batchSize` matching chunk size
2. Enable MySQL batch inserts: `rewriteBatchedStatements=true`
3. Use cursor-based readers for large datasets
4. Configure appropriate fetch sizes

```kotlin
@Bean
fun optimizedReader(): JdbcCursorItemReader<Order> = JdbcCursorItemReaderBuilder<Order>()
    .dataSource(dataSource)
    .sql("SELECT * FROM orders WHERE status = 'PENDING'")
    .rowMapper(OrderRowMapper())
    .fetchSize(1000)  // Match or exceed chunk size
    .build()

@Bean
fun optimizedWriter(): JdbcBatchItemWriter<Order> = JdbcBatchItemWriterBuilder<Order>()
    .dataSource(dataSource)
    .sql("INSERT INTO processed_orders VALUES (:id, :amount, :status)")
    .beanMapped()
    .build()
```

**MySQL connection string optimization:**
```
jdbc:mysql://localhost:3306/batch?rewriteBatchedStatements=true&cachePrepStmts=true&useServerPrepStmts=true
```

**Study materials:**
- YouTube: "Spring Batch Performance Tuning" (Spring I/O conference)
- Reference Documentation: Configuring a Step (chunk-size section)
- Baeldung: "Spring Batch Performance Tips"

**Project: Performance benchmark suite**
Create a benchmarking framework that measures throughput at different chunk sizes, thread counts, and batch configurations.

---

## Phase 3: Common use cases implementation (Weeks 9-11)

### Week 9: File processing mastery (CSV, Excel, XML, JSON)
**Time commitment: 12-14 hours**

**FlatFileItemReader for CSV:**
```kotlin
@Bean
@StepScope
fun csvReader(@Value("#{jobParameters['inputFile']}") resource: Resource): FlatFileItemReader<Person> =
    FlatFileItemReaderBuilder<Person>()
        .name("personReader")
        .resource(resource)
        .delimited()
        .names("firstName", "lastName", "email", "birthDate")
        .fieldSetMapper(PersonFieldSetMapper())
        .linesToSkip(1)  // Skip header
        .build()
```

**Excel processing with Apache POI:**
```kotlin
class ExcelItemReader(private val resource: Resource) : ItemStreamReader<Row> {
    private lateinit var workbook: Workbook
    private lateinit var rowIterator: Iterator<Row>
    
    override fun open(executionContext: ExecutionContext) {
        workbook = WorkbookFactory.create(resource.inputStream)
        val sheet = workbook.getSheetAt(0)
        rowIterator = sheet.iterator()
        if (rowIterator.hasNext()) rowIterator.next() // Skip header
    }
    
    override fun read(): Row? = if (rowIterator.hasNext()) rowIterator.next() else null
    
    override fun close() = workbook.close()
}
```

**JSON processing with JsonItemReader:**
```kotlin
@Bean
fun jsonReader(): JsonItemReader<Customer> = JsonItemReaderBuilder<Customer>()
    .jsonObjectReader(JacksonJsonObjectReader(Customer::class.java))
    .resource(ClassPathResource("customers.json"))
    .name("customerJsonReader")
    .build()
```

**Study materials:**
- Reference Documentation: ItemReaders and ItemWriters (comprehensive)
- Baeldung: "Spring Batch: Reading from Files"
- GitHub: spring-batch-samples repository

**Project: Multi-format data consolidator**
Build a job that reads from CSV, Excel, and JSON sources, normalizes the data, and writes to a unified MySQL schema.

---

### Week 10: Database-to-database ETL patterns
**Time commitment: 12-14 hours**

**JdbcPagingItemReader for large datasets:**
```kotlin
@Bean
@StepScope
fun pagingReader(): JdbcPagingItemReader<Order> = JdbcPagingItemReaderBuilder<Order>()
    .dataSource(sourceDataSource)
    .selectClause("SELECT id, customer_id, amount, created_at")
    .fromClause("FROM orders")
    .whereClause("WHERE status = :status")
    .sortKeys(mapOf("id" to Order.ASCENDING))
    .rowMapper(OrderRowMapper())
    .pageSize(1000)
    .parameterValues(mapOf("status" to "PENDING"))
    .build()
```

**JpaPagingItemReader for entity-based processing:**
```kotlin
@Bean
@StepScope
fun jpaReader(entityManagerFactory: EntityManagerFactory): JpaPagingItemReader<OrderEntity> =
    JpaPagingItemReaderBuilder<OrderEntity>()
        .entityManagerFactory(entityManagerFactory)
        .queryString("SELECT o FROM OrderEntity o WHERE o.status = 'PENDING'")
        .pageSize(500)
        .build()
```

**Data migration pattern with transformation:**
```kotlin
@Bean
fun migrationJob(): Job = JobBuilder("dataMigration", jobRepository)
    .incrementer(RunIdIncrementer())
    .start(extractStep())
    .next(transformStep())
    .next(loadStep())
    .next(validationStep())
    .build()
```

**Study materials:**
- Reference Documentation: Database ItemReaders
- Baeldung: "Spring Batch with JPA"
- DZone: "Spring Batch ETL Patterns"

**Project: Legacy system migration**
Migrate data from a legacy MySQL schema to a new normalized schema with data transformation, validation, and reconciliation.

---

### Week 11: Aggregation, cleanup, and reporting jobs
**Time commitment: 10-12 hours**

**Data cleanup with process indicator pattern:**
```kotlin
@Bean
fun archivalStep(): Step = StepBuilder("archival", jobRepository)
    .chunk<OldRecord, ArchivedRecord>(500, transactionManager)
    .reader(oldRecordsReader())
    .processor { record -> ArchivedRecord(record, LocalDateTime.now()) }
    .writer(compositeWriter())  // Write to archive + mark as processed
    .build()

@Bean
fun compositeWriter(): CompositeItemWriter<ArchivedRecord> = CompositeItemWriter<ArchivedRecord>().apply {
    setDelegates(listOf(archiveWriter(), processIndicatorWriter()))
}
```

**Report generation with custom aggregation:**
```kotlin
class ReportAggregator : ItemWriter<Transaction>, StepExecutionListener {
    private val totals = mutableMapOf<String, BigDecimal>()
    
    override fun write(chunk: Chunk<out Transaction>) {
        chunk.items.forEach { tx ->
            totals.merge(tx.category, tx.amount, BigDecimal::add)
        }
    }
    
    override fun afterStep(stepExecution: StepExecution): ExitStatus {
        // Generate report from aggregated totals
        reportService.generate(totals)
        return ExitStatus.COMPLETED
    }
}
```

**Study materials:**
- Reference Documentation: Job and Step Attributes
- ddubson/spring-batch-examples: Custom patterns
- Medium: "Data Aggregation with Spring Batch"

**Project: Monthly analytics pipeline**
Create a job that aggregates daily transaction data into monthly summaries with report generation and data archival.

---

## Phase 4: Integrations (Weeks 12-14)

### Week 12: Kafka integration for event-driven batch processing
**Time commitment: 14-16 hours**

**KafkaItemReader configuration:**
```kotlin
@Bean
@StepScope
fun kafkaReader(): KafkaItemReader<String, CustomerEvent> {
    val props = Properties().apply {
        put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092")
        put(ConsumerConfig.GROUP_ID_CONFIG, "batch-consumer")
        put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer::class.java)
        put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, JsonDeserializer::class.java)
        put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 500)
    }
    
    return KafkaItemReaderBuilder<String, CustomerEvent>()
        .consumerProperties(props)
        .topic("customer-events")
        .partitions(0, 1, 2, 3)
        .pollTimeout(Duration.ofSeconds(30))
        .saveState(true)  // Enable restart from last offset
        .name("kafkaEventReader")
        .build()
}
```

**KafkaItemWriter configuration:**
```kotlin
@Bean
fun kafkaWriter(kafkaTemplate: KafkaTemplate<String, ProcessedEvent>): KafkaItemWriter<String, ProcessedEvent> =
    KafkaItemWriterBuilder<String, ProcessedEvent>()
        .kafkaTemplate(kafkaTemplate)
        .itemKeyMapper { it.eventId }
        .build()
```

**Event-driven job triggering:**
```kotlin
@Component
class BatchJobTrigger(
    private val jobLauncher: JobLauncher,
    private val job: Job
) {
    @KafkaListener(topics = ["batch-triggers"], groupId = "batch-control")
    fun onTrigger(event: BatchTriggerEvent) {
        val params = JobParametersBuilder()
            .addString("triggerId", event.id)
            .addLong("timestamp", System.currentTimeMillis())
            .toJobParameters()
        jobLauncher.run(job, params)
    }
}
```

**Study materials:**
- Spring Batch Reference: KafkaItemReader/Writer sections
- Spring for Apache Kafka documentation
- Baeldung: "Spring Batch with Kafka"

**Project: Real-time event processor**
Build a batch job that consumes events from Kafka, enriches them with MySQL data, and publishes results to a different Kafka topic.

---

### Week 13: Scheduling and REST API triggers
**Time commitment: 10-12 hours**

**@Scheduled for simple cron execution:**
```kotlin
@Component
class ScheduledJobLauncher(
    private val jobLauncher: JobLauncher,
    private val dailyReportJob: Job
) {
    @Scheduled(cron = "0 0 2 * * *")  // Daily at 2 AM
    fun runDailyReport() {
        val params = JobParametersBuilder()
            .addLocalDateTime("runDate", LocalDateTime.now())
            .toJobParameters()
        jobLauncher.run(dailyReportJob, params)
    }
}
```

**REST API for job management:**
```kotlin
@RestController
@RequestMapping("/api/jobs")
class JobController(
    private val jobLauncher: JobLauncher,
    private val jobExplorer: JobExplorer,
    private val jobOperator: JobOperator,
    private val jobRegistry: JobRegistry
) {
    @PostMapping("/{jobName}/start")
    fun startJob(@PathVariable jobName: String, @RequestBody params: Map<String, String>): ResponseEntity<Long> {
        val job = jobRegistry.getJob(jobName)
        val jobParams = JobParametersBuilder().apply {
            params.forEach { (k, v) -> addString(k, v) }
            addLong("timestamp", System.currentTimeMillis())
        }.toJobParameters()
        
        val execution = jobLauncher.run(job, jobParams)
        return ResponseEntity.ok(execution.id)
    }
    
    @GetMapping("/{executionId}/status")
    fun getStatus(@PathVariable executionId: Long): ResponseEntity<JobExecution> {
        val execution = jobExplorer.getJobExecution(executionId)
        return ResponseEntity.ok(execution)
    }
    
    @PostMapping("/{executionId}/restart")
    fun restartJob(@PathVariable executionId: Long): ResponseEntity<Long> {
        val newExecutionId = jobOperator.restart(executionId)
        return ResponseEntity.ok(newExecutionId)
    }
}
```

**Quartz integration for clustered scheduling:**
```kotlin
@Configuration
class QuartzBatchConfig {
    @Bean
    fun batchJobDetail(): JobDetail = JobBuilder.newJob(SpringBatchQuartzJob::class.java)
        .withIdentity("batchJob")
        .storeDurably()
        .build()
    
    @Bean
    fun batchTrigger(): Trigger = TriggerBuilder.newTrigger()
        .forJob(batchJobDetail())
        .withSchedule(CronScheduleBuilder.cronSchedule("0 */15 * * * ?"))
        .build()
}
```

**Study materials:**
- Reference Documentation: Job Repository and Operator
- Baeldung: "Spring Batch with Quartz"
- Baeldung: "Trigger Spring Batch Jobs from REST"

**Project: Job management dashboard backend**
Build a REST API that supports starting jobs, viewing status, restarting failed jobs, and querying execution history.

---

### Week 14: Monitoring, observability, and Spring Cloud Data Flow
**Time commitment: 10-12 hours**

**Micrometer metrics are automatic with Spring Batch 5.x:**
```kotlin
// Key metrics available:
// spring.batch.job - Timer for job executions
// spring.batch.job.active - Active jobs gauge
// spring.batch.step - Timer for step executions
// spring.batch.item.read - Item read timer
// spring.batch.chunk.write - Chunk write timer
```

**Prometheus configuration for batch jobs:**
```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: health,prometheus,metrics
  metrics:
    tags:
      application: batch-service
    export:
      prometheus:
        pushgateway:
          enabled: true
          base-url: http://pushgateway:9091
          push-rate: 30s
```

**Custom business metrics:**
```kotlin
@Component
class BatchMetrics(private val meterRegistry: MeterRegistry) : ItemWriteListener<Order> {
    
    private val orderTotal = meterRegistry.counter("batch.orders.total")
    private val orderValue = meterRegistry.gauge("batch.orders.value", AtomicDouble(0.0))
    
    override fun afterWrite(chunk: Chunk<out Order>) {
        orderTotal.increment(chunk.size().toDouble())
        val total = chunk.items.sumOf { it.amount.toDouble() }
        orderValue?.set(total)
    }
}
```

**Spring Cloud Data Flow overview:**
Spring Cloud Data Flow orchestrates batch jobs as "tasks" with scheduling, monitoring, and stream integration. Key concepts:
- Tasks = single execution batch jobs
- Composed tasks = job orchestration pipelines
- Task scheduler integration

**Study materials:**
- Reference Documentation: Micrometer Support
- Spring Cloud Data Flow documentation
- YouTube: "Observability with Spring Batch" (Spring I/O)

**Project: Observable batch pipeline**
Integrate Prometheus + Grafana dashboards showing job metrics, success rates, and processing throughput.

---

## Phase 5: Testing and production readiness (Weeks 15-16)

### Week 15: Comprehensive testing strategies
**Time commitment: 12-14 hours**

**@SpringBatchTest provides auto-configured test utilities:**
```kotlin
@SpringBatchTest
@SpringBootTest
class ImportJobTest {
    
    @Autowired
    private lateinit var jobLauncherTestUtils: JobLauncherTestUtils
    
    @Autowired
    private lateinit var jobRepositoryTestUtils: JobRepositoryTestUtils
    
    @BeforeEach
    fun setup(@Autowired job: Job) {
        jobLauncherTestUtils.job = job
        jobRepositoryTestUtils.removeJobExecutions()
    }
    
    @Test
    fun `should complete import job successfully`() {
        val params = JobParametersBuilder()
            .addString("inputFile", "classpath:test-data.csv")
            .toJobParameters()
        
        val execution = jobLauncherTestUtils.launchJob(params)
        
        assertThat(execution.exitStatus).isEqualTo(ExitStatus.COMPLETED)
        assertThat(execution.stepExecutions.first().readCount).isEqualTo(100)
    }
    
    @Test
    fun `should process step correctly`() {
        val stepExecution = jobLauncherTestUtils.launchStep("processStep")
        
        assertThat(stepExecution.readCount).isEqualTo(100)
        assertThat(stepExecution.writeCount).isEqualTo(95)
        assertThat(stepExecution.skipCount).isEqualTo(5)
    }
}
```

**Unit testing with MockK (Kotlin-preferred):**
```kotlin
class OrderProcessorTest {
    
    private val enrichmentService = mockk<EnrichmentService>()
    private val processor = OrderProcessor(enrichmentService)
    
    @Test
    fun `should enrich valid orders`() {
        every { enrichmentService.enrich(any()) } returns EnrichedData("premium")
        
        val result = processor.process(Order(id = 1, amount = 100.0))
        
        assertThat(result?.tier).isEqualTo("premium")
        verify(exactly = 1) { enrichmentService.enrich(any()) }
    }
    
    @Test
    fun `should filter invalid orders`() {
        val result = processor.process(Order(id = 1, amount = -50.0))
        
        assertThat(result).isNull()  // null = filtered
    }
}
```

**Testing with H2 in-memory database:**
```kotlin
@TestConfiguration
class TestBatchConfig {
    @Bean
    @Primary
    fun testDataSource(): DataSource = EmbeddedDatabaseBuilder()
        .setType(EmbeddedDatabaseType.H2)
        .addScript("classpath:org/springframework/batch/core/schema-h2.sql")
        .addScript("classpath:test-data.sql")
        .build()
}
```

**Study materials:**
- Reference Documentation: Unit Testing
- SpringMockK documentation
- Baeldung: "Testing Spring Batch Jobs"

**Project: Test suite for complete batch application**
Achieve **>80% test coverage** with unit tests, integration tests, and end-to-end tests.

---

### Week 16: Production deployment and Kubernetes patterns
**Time commitment: 12-14 hours**

**Idempotency pattern implementation:**
```kotlin
// Process indicator table
@Entity
data class ProcessedRecord(
    @Id val recordId: String,
    val processedAt: LocalDateTime,
    val jobExecutionId: Long
)

class IdempotentProcessor(
    private val processedRepository: ProcessedRecordRepository
) : ItemProcessor<Record, ProcessedRecord?> {
    
    override fun process(item: Record): ProcessedRecord? {
        if (processedRepository.existsById(item.id)) {
            return null  // Already processed, skip
        }
        return ProcessedRecord(item.id, LocalDateTime.now(), getCurrentJobExecutionId())
    }
}
```

**Kubernetes Job manifest:**
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: spring-batch-import
spec:
  backoffLimit: 3
  activeDeadlineSeconds: 3600
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: batch
          image: myregistry/batch-app:latest
          args: ["--inputFile=s3://bucket/data.csv"]
          env:
            - name: SPRING_DATASOURCE_URL
              value: jdbc:mysql://mysql-service:3306/batchdb
            - name: SPRING_PROFILES_ACTIVE
              value: kubernetes
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
```

**CronJob for scheduled execution:**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-report
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 10
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: batch
              image: myregistry/batch-app:latest
```

**Graceful shutdown handling:**
```kotlin
@SpringBootApplication
class BatchApplication

fun main(args: Array<String>) {
    System.exit(SpringApplication.exit(
        SpringApplication.run(BatchApplication::class.java, *args)
    ))
}
```

**Production checklist:**
- [ ] Persistent JobRepository (MySQL with proper connection pooling)
- [ ] Idempotent job design for safe restarts
- [ ] Skip/retry policies for transient failures
- [ ] Prometheus metrics with Pushgateway for short-lived jobs
- [ ] Proper logging with correlation IDs
- [ ] Alerting on job failures
- [ ] Regular metadata table cleanup

**Study materials:**
- Spring.io: "Running Spring Batch on Kubernetes" (official guide)
- Reference Documentation: Deployment Patterns
- YouTube: "Cloud-Native Batch Processing"

**Capstone project: Production-ready batch system**
Deploy a complete batch application to Kubernetes with:
1. MySQL JobRepository with HA configuration
2. Kafka integration for event-driven triggers
3. Prometheus/Grafana monitoring
4. REST API for manual intervention
5. Comprehensive test suite

---

## Recommended resources by category

### Essential reading (prioritized)
1. **Spring Academy Course** (FREE) — Official course by Mahmoud Ben Hassine, Spring Batch project lead
2. **Spring Batch 5.0 Migration Guide** — GitHub Wiki, essential for correct 5.x patterns
3. **Baeldung Spring Batch tutorials** — Updated for 5.2.0, practical code examples
4. **"The Definitive Guide to Spring Batch"** by Michael Minella — Most comprehensive book (concepts apply, update code patterns for 5.x)

### Video courses
| Course | Platform | Spring Batch 5.x | Best For |
|--------|----------|------------------|----------|
| Spring Academy | spring.academy | ✅ | Official, free, hands-on |
| Spring: Spring Batch | LinkedIn Learning | ⚠️ 4.x | Comprehensive video coverage |
| Spring Batch Mastery | Udemy | Varies | Advanced scaling patterns |
| Getting Started | Pluralsight | ⚠️ 4.x | Quick introduction |

### Kotlin-specific resources
- **ddubson/spring-batch-examples** (GitHub, 36 examples, 100% Kotlin) — Essential reference
- **SpringMockK library** — Kotlin-native mocking for tests
- **Jackson Kotlin Module** — Required for proper data class serialization

### GitHub repositories for reference
1. `spring-projects/spring-batch` — Official source and samples
2. `spring-guides/gs-batch-processing` — Getting started code
3. `ddubson/spring-batch-examples` — Comprehensive Kotlin examples
4. `eugenp/tutorials/spring-batch` — Baeldung code samples

---

## Weekly time summary

| Phase | Weeks | Hours/Week | Total Hours | Focus |
|-------|-------|------------|-------------|-------|
| Foundation | 1-4 | 10-12 | 40-48 | Architecture, lifecycle, contracts |
| Core Patterns | 5-8 | 10-14 | 42-50 | Error handling, parallelism, performance |
| Use Cases | 9-11 | 10-14 | 32-40 | File processing, ETL, aggregation |
| Integrations | 12-14 | 10-16 | 34-44 | Kafka, scheduling, monitoring |
| Production | 15-16 | 12-14 | 24-28 | Testing, Kubernetes, deployment |
| **Total** | **16** | **~11** | **172-210** | |

This plan emphasizes practical application over passive reading. Each week's project builds skills that compound into the capstone production system. The investment of **~175 hours** over 16 weeks delivers not just knowledge of Spring Batch APIs, but the judgment to architect robust batch systems for real-world data processing challenges.