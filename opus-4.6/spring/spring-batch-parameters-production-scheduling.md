---
title: "Spring Batch parameters and production scheduling"
category: "Spring"
description: "Seven mechanisms for passing JobParameters in Spring Batch 5.x and production orchestration patterns with Kubernetes CronJobs for Spring Boot 3.x"
---

# Spring Batch parameters and production scheduling

**Spring Batch 5.x offers seven distinct mechanisms for passing parameters into jobs, while Kubernetes CronJobs have emerged as the dominant production scheduling pattern.** The framework's parameter system underwent a fundamental redesign in version 5.0, replacing the rigid four-type model with generic `JobParameter<T>` supporting any Java type. Meanwhile, the production landscape shifted dramatically in April 2025 when Spring Cloud Data Flow moved to commercial-only licensing, pushing teams toward Kubernetes-native and cloud-provider scheduling solutions. This report covers every parameter-passing approach, all major production orchestration tools, and battle-tested best practices for Spring Batch 5.x / Spring Boot 3.x environments.

---

## Seven ways to pass parameters into Spring Batch jobs

Spring Batch provides multiple parameter-passing mechanisms that serve different use cases, from simple command-line arguments to event-driven triggers. Understanding the distinction between **JobParameters** (which participate in job instance identity and are persisted to the database) and **application configuration** (Spring Boot properties, environment variables) is foundational. JobParameters determine whether a job execution represents a new instance or a restart of a previous one.

### 1. Command-line arguments (JobParameters)

Spring Boot's `JobLauncherApplicationRunner` automatically converts bare `key=value` CLI arguments into JobParameters. The **Spring Batch 5.x syntax** uses a comma-delimited format: `key=value,type,identifying`.

```bash
java -jar myapp.jar schedule.date=2024-01-15,java.time.LocalDate,true vendor.id=123,java.lang.Long,false
```

The `type` field accepts any **fully qualified class name** (defaulting to `java.lang.String`), and `identifying` defaults to `true`. This replaced the v4 syntax of `key(type)=value` with `+`/`-` prefixes, which was shell-unfriendly. A critical gotcha: arguments starting with `--` become Spring Environment properties and are **not** passed as JobParameters. The properties `spring.batch.job.enabled` and `spring.batch.job.name` control auto-launch behavior.

### 2. JobParametersBuilder (programmatic construction)

When launching jobs via `JobLauncher.run()` — from REST controllers, schedulers, or integration flows — `JobParametersBuilder` provides a fluent API:

```java
JobParameters params = new JobParametersBuilder()
    .addString("fileName", "input.csv")
    .addLocalDate("reportDate", LocalDate.now())       // new in v5
    .addLong("batchSize", 500L, false)                 // non-identifying
    .addJobParameter("custom", new JobParameter<>(myObj, MyType.class, true))
    .toJobParameters();
jobLauncher.run(myJob, params);
```

Spring Batch 5.x added `addLocalDate`, `addLocalDateTime`, `addLocalTime`, and a generic `addJobParameter` method accepting any type convertible via Spring's `ConversionService`. The old `SimpleJobLauncher` was renamed to **`TaskExecutorJobLauncher`**.

### 3. Late binding with @StepScope and @JobScope

These custom bean scopes defer instantiation to execution time, enabling runtime parameter injection via SpEL. **`@StepScope`** creates a new bean instance per step execution and can access `jobParameters`, `jobExecutionContext`, and `stepExecutionContext`. **`@JobScope`** creates one instance per job execution and cannot access step-level context.

```java
@Bean @StepScope
public FlatFileItemReader<Foo> reader(
        @Value("#{jobParameters['input.file.name']}") String fileName) {
    return new FlatFileItemReaderBuilder<Foo>()
        .resource(new FileSystemResource(fileName)).build();
}
```

The `@Bean` method's return type matters: always return the **most specific implementation type** (e.g., `FlatFileItemReader<Foo>`, not `ItemReader<Foo>`) so the CGLIB proxy correctly implements all required interfaces like `ItemStream`. SpEL uses `#{}` syntax — not `${}`, which resolves Spring Environment properties.

### 4. Environment variables and application properties

Spring Boot's externalized configuration hierarchy — command-line args → environment variables → `application-{profile}.yml` → `application.yml` — provides configuration values accessible via `@Value("${property}")` or `@ConfigurationProperties`. These are **not** JobParameters: they don't participate in job instance identity and can't be accessed via `#{jobParameters[...]}` SpEL. A common pattern bridges them into JobParameters programmatically when needed:

```java
@Value("${batch.input-path}") private String inputPath;
// ... then add to JobParametersBuilder when launching
```

Spring Boot provides no built-in `spring.batch.job.parameters.*` property namespace — a feature request for this was explicitly declined.

### 5. REST API triggering

Disabling auto-launch with `spring.batch.job.enabled=false` and exposing a controller provides on-demand execution with request-derived parameters:

```java
@PostMapping("/batch/run")
public ResponseEntity<String> runJob(@RequestParam String fileName) {
    JobParameters params = new JobParametersBuilder()
        .addString("fileName", fileName)
        .addLong("timestamp", System.currentTimeMillis())
        .toJobParameters();
    JobExecution execution = jobLauncher.run(myJob, params);
    return ResponseEntity.ok("Job started: " + execution.getId());
}
```

For async execution, configure `TaskExecutorJobLauncher` with `SimpleAsyncTaskExecutor`.

### 6. Spring Integration (event-driven)

The `JobLaunchingGateway` enables event-driven job launches — for example, triggering a batch job when a file arrives in a directory. A transformer converts incoming messages into `JobLaunchRequest` objects containing the `Job` and constructed `JobParameters`. This pattern is ideal for file-processing pipelines where the filename and arrival time become job parameters.

### 7. Database or external configuration

Parameters can be loaded from a database table, Spring Cloud Config server, or message queue before launching. This suits environments where business users configure job runs through a UI that writes to a configuration table. The launcher reads the config, constructs `JobParameters`, and invokes `JobLauncher.run()`.

---

## The v4-to-v5 parameter system overhaul

Spring Batch 5.0 fundamentally redesigned parameter handling. The `JobParameter` class became **generic** (`JobParameter<T>`), supporting any type rather than just String, Long, Double, and Date. The `ParameterType` enum was removed entirely. The database schema consolidated the old `STRING_VAL`, `DATE_VAL`, `LONG_VAL`, and `DOUBLE_VAL` columns into a single `PARAMETER_VALUE VARCHAR(2500)` column alongside `PARAMETER_TYPE VARCHAR(100)` storing the fully qualified class name.

| Aspect | Spring Batch 4.x | Spring Batch 5.x |
|--------|------------------|------------------|
| CLI syntax | `key(type)=value` with `+`/`-` prefix | `key=value,fqcn,identifying` |
| Supported types | String, Long, Date, Double only | Any type via `ConversionService` |
| `JobParameter` class | Non-generic | Generic `JobParameter<T>` |
| DB storage | Separate typed columns | Unified `PARAMETER_TYPE` + `PARAMETER_VALUE` |
| New typed methods | N/A | `addLocalDate`, `addLocalDateTime`, `addLocalTime` |

Migration requires running DDL scripts from `org/springframework/batch/core/migration/5.0/`, and **all failed v4 job instances must be completed or abandoned before upgrading** because v5 cannot restart v4 instances due to incompatible parameter serialization. OpenRewrite recipes (`SpringBatch4To5Migration`) automate much of the code migration.

---

## Production scheduling tools ranked by adoption

The production landscape for Spring Batch scheduling has consolidated around Kubernetes-native approaches. Here is every major option, assessed for current relevance.

### Kubernetes CronJobs: the default choice

**Kubernetes CronJobs are the most widely adopted production pattern for Spring Batch in 2024–2026.** The architectural fit is natural: a Spring Batch job that runs to completion maps one-to-one to a Kubernetes Job. The application is packaged as a Docker container, scheduled via CronJob spec, and terminates after execution.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-report-job
spec:
  schedule: '0 2 * * *'
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      backoffLimit: 3
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: batch
            image: myregistry/batch-app:latest
            args: ["reportDate=2024-01-15,java.time.LocalDate"]
            env:
            - name: SPRING_DATASOURCE_URL
              valueFrom:
                secretKeyRef: { name: db-secret, key: url }
```

Parameters flow through container `args` (as Spring Boot CLI arguments → JobParameters), environment variables (from ConfigMaps and Secrets), or mounted configuration files. Kubernetes 1.27+ supports timezone-aware scheduling. Pair with **Spring Cloud Task** for execution metadata tracking and Prometheus/Grafana for observability.

### Quartz Scheduler: in-JVM clustering

When jobs need **clustered, run-once guarantees without external infrastructure** beyond a database, Quartz with JDBC JobStore is the standard. A bridge class extending `QuartzJobBean` converts Quartz's `JobDataMap` into Spring Batch `JobParameters`. Clustered mode (`isClustered=true`) ensures only one node executes each trigger, with automatic failover if a node crashes. Spring Boot 3.5+ added an Actuator endpoint for Quartz management. This pattern dominates in **financial services and insurance** where in-JVM scheduling with misfire handling is critical.

### Cloud-native schedulers

Each major cloud provider offers managed scheduling services:

- **AWS**: EventBridge Scheduler triggers Step Functions state machines that orchestrate ECS tasks or AWS Batch jobs. Step Functions provides visual workflow design, retry logic, and conditional branching. AWS Batch manages compute scaling with Spot instance support for cost optimization.
- **GCP**: Cloud Scheduler triggers Cloud Run Jobs via HTTP POST. Cloud Run Jobs support up to 10,000 parallel tasks with scale-to-zero economics.
- **Azure**: Azure Functions timer triggers invoke Azure Container Instances or Azure Batch. Azure Data Factory provides additional orchestration capabilities.

Parameters pass as JSON payloads, environment variable overrides, or container command arguments. All three platforms treat Spring Batch as a black-box container.

### Workflow orchestration platforms

**Apache Airflow** is the industry standard for DAG-based batch pipeline orchestration, using `KubernetesPodOperator` or `BashOperator` to run Spring Batch containers. It excels when Spring Batch jobs are part of larger multi-technology data pipelines. **Temporal.io** provides durable execution guarantees with a native Java SDK, wrapping Spring Batch execution as Activities within Workflows — ideal for complex multi-step business processes requiring exactly-once semantics. **Netflix Conductor** offers declarative JSON-based workflows with a polling worker model.

### Enterprise and legacy schedulers

**BMC Control-M** remains the market leader for enterprise workload automation, integrating with Spring Batch through agent-based execution (`java -jar` on managed agents), Kubernetes job plugins, or REST API triggers. **Broadcom AutoSys** and **HCL Workload Automation** (formerly IBM Tivoli) serve similar enterprise niches. These tools excel at **cross-application dependency chains** spanning mainframe, middleware, and cloud workloads — common in financial institutions managing 10,000–100,000+ jobs daily. They add centralized audit trails, SLA management, and compliance features.

**Jenkins** and **Linux cron** remain viable for simpler scenarios. Jenkins works well in organizations already using it for CI/CD that want to reuse infrastructure for batch scheduling, though it lacks native Spring Batch awareness. Linux cron suits single-server, low-frequency batch jobs but offers no clustering, HA, or centralized monitoring.

### Spring Cloud Data Flow: a cautionary note

As of **April 2025, Spring Cloud Data Flow is no longer maintained as open source** — future releases are commercial-only via Tanzu Spring. Spring Cloud Task remains open source and is recommended as a lightweight alternative for execution tracking, but new projects should not build on SCDF unless they are existing Tanzu customers.

---

## Best practices for production parameter management

### Validate early, validate always

Wire a `JobParametersValidator` into every job definition. The built-in `DefaultJobParametersValidator` enforces required and optional keys. Chain multiple validators with `CompositeJobParametersValidator` to combine structural validation (required keys) with business validation (date ranges, file extensions). Validation runs **before any steps execute**, catching errors early.

```java
return new JobBuilder("myJob", jobRepository)
    .validator(compositeValidator())
    .incrementer(new RunIdIncrementer())
    .start(step1)
    .build();
```

### Design identifying parameters for business identity

Only parameters representing the **logical identity of the work** should be identifying. A `reportDate` parameter is identifying because processing January data is fundamentally different work than processing February data. A `batchSize` or `threadCount` parameter should be **non-identifying** (`identifying=false`) because changing performance tuning shouldn't create a new job instance or prevent restarts. Use `RunIdIncrementer` for jobs that must be re-runnable regardless of parameters.

### Never pass secrets as JobParameters

JobParameters are persisted in **plain text** in `BATCH_JOB_EXECUTION_PARAMS` and logged at INFO level during job launch. Use external secret stores (HashiCorp Vault, AWS Secrets Manager, Kubernetes Secrets) and resolve credentials inside steps via `@Value("${db.password}")` from the Spring Environment. Add sanitization patterns to Actuator: `management.endpoint.env.additional-keys-to-sanitize=password,secret,token`.

### Keep ExecutionContext lean

The `ExecutionContext` — used to pass data between steps via `ExecutionContextPromotionListener` — is serialized to the database on every chunk commit. Store only **primitives, small value objects, and control flags**. For large datasets, write to a shared database table or file system and pass the reference (table name, file path) through the context. The `SHORT_CONTEXT` column is limited to VARCHAR(2500).

### Test with realistic parameters

Use `@SpringBatchTest` with `JobLauncherTestUtils.launchJob(params)` for end-to-end testing and `launchStep("stepName")` for isolated step testing. The `StepScopeTestExecutionListener` enables testing `@StepScope` beans by providing a synthetic `StepExecution` with configured parameters. Always clean up with `JobRepositoryTestUtils.removeJobExecutions()` between tests.

### Monitor parameter usage through observability

Spring Batch 5.x integrates with Micrometer's Observation API, automatically recording metrics under `spring.batch.job` and `spring.batch.step` timers with status tags. Implement a custom `JobExecutionListener` to log parameters in structured format (filtering out sensitive values). Query `BATCH_JOB_EXECUTION_PARAMS` for historical audit trails. Implement a retention policy for metadata tables to prevent unbounded growth that degrades query performance.

---

## Conclusion

Spring Batch's parameter system in 5.x is significantly more flexible than its predecessor, with generic typing, extensible conversion, and cleaner CLI syntax. The most effective production architecture for most teams combines **Kubernetes CronJobs for scheduling**, **Spring Cloud Task for execution tracking**, and **JobParametersBuilder for programmatic parameter construction** — with Quartz filling the niche for in-JVM clustered scheduling. The key architectural decisions are choosing identifying parameters that genuinely represent work identity, keeping secrets out of the JobParameters system entirely, and selecting a scheduling tool that matches your infrastructure reality rather than over-engineering with heavyweight enterprise schedulers when a CronJob will suffice.