# Durable execution for Spring Boot: a practitioner's guide

**Temporal leads the durable execution space for JVM teams, but Restate is emerging as the most compelling alternative — especially for Kotlin developers.** For a mid-level engineer running Spring Boot on AWS EKS with PostgreSQL, Redis, and Kafka, the practical choice narrows to three serious contenders: Temporal for maximum ecosystem maturity, Restate for operational simplicity and native Kotlin coroutine support, or Conductor/Orkes if you want JSON-defined workflows with excellent visual debugging. Camunda remains relevant only if your organization requires BPMN modeling for compliance, and newer entrants like DBOS and Infinitic show promise but carry significant production risk. This guide evaluates every major tool, provides integration code, and offers a clear decision framework.

---

## The landscape: 12 tools across 4 distinct paradigms

Durable execution tools guarantee that code completes despite infrastructure failures by persisting workflow state at each step. If a process crashes mid-execution, another worker resumes from the last checkpoint with all state intact — call stack, local variables, and completed step results preserved. The JVM ecosystem has **four paradigms** worth understanding:

**Code-first durable execution** (Temporal, Cadence, Restate, Infinitic, DBOS) lets you write workflows as regular code. The engine intercepts execution, journals each step, and replays on failure. This is the most natural model for developers. **DSL/JSON-based orchestration** (Conductor/Orkes) defines workflows declaratively, with workers implementing individual tasks. **BPMN model-first** (Camunda/Zeebe, Flowable, jBPM) designs workflows as visual diagrams, then attaches code to tasks. **Simple state machines** (Spring State Machine) track state transitions but lack durability guarantees.

Tools that don't merit serious consideration for JVM backend work: **Apache Airflow** is Python-only and explicitly rejects JVM support — it's for data pipelines, not microservice orchestration. **Hatchet** and **Prefect** have no JVM SDKs. **Spring State Machine** handles simple state transitions but provides no durable execution, no distributed coordination, and no built-in retry/compensation — it's fundamentally a different tool. **jBPM/Kogito** is declining and overly complex. **Quartz Scheduler** is a job scheduler, not a workflow engine.

---

## Temporal: the industry standard with real trade-offs

Temporal is the most mature code-first durable execution platform, forked from Uber's Cadence in 2019. It powers hundreds of companies with **~15,900 GitHub stars**, an active Slack community, and the largest ecosystem of any tool in this category. Its Java SDK (v1.32.1 as of late 2025) is feature-complete, and an official Spring Boot starter (`io.temporal:temporal-spring-boot-starter`) moved from alpha to public preview in mid-2024.

**Architecture.** The Temporal server is written in Go and consists of four services — Frontend (API gateway), History (workflow state), Matching (task queue routing), and Worker (internal operations). It requires a persistence store (PostgreSQL, MySQL, or Cassandra) plus Elasticsearch for workflow visibility/search. Workers are your application processes that poll task queues and execute workflow/activity code via gRPC.

**Programming model.** You define deterministic workflow interfaces and non-deterministic activities. Workflows orchestrate activities through typed stubs, and the engine automatically handles retries, timeouts, and state persistence. The key constraint: **workflow code must be deterministic** — no random numbers, no system clock access, no I/O. All side effects go into activities.

**Spring Boot integration is solid.** The official starter auto-configures a `WorkflowClient` bean, auto-discovers workflow and activity implementations via package scanning, and supports declarative worker configuration in `application.yml`. Activity implementations are standard Spring `@Component` beans with full access to dependency injection, `@Transactional`, JPA repositories, and other Spring features. Workflow implementations, however, cannot be Spring beans — they're managed by Temporal's own lifecycle.

```kotlin
// build.gradle.kts
implementation("io.temporal:temporal-spring-boot-starter:1.32.1")
implementation("io.temporal:temporal-kotlin:1.32.1")
```

```yaml
# application.yml
spring:
  temporal:
    connection:
      target: localhost:7233
    namespace: default
    workers-auto-discovery:
      packages:
        - com.example.workflows
        - com.example.activities
```

**Kotlin works but has a ceiling.** Kotlin compiles to JVM bytecode, so the Java SDK works fine for standard workflows and activities. Data classes serialize correctly with `jackson-module-kotlin`. However, **Temporal does not support Kotlin coroutines** in workflows — there's an open issue (#1845) but no resolution. Workflows use Temporal's own threading model. This is the single biggest limitation for Kotlin developers who want idiomatic code.

**Operational complexity is the primary drawback for self-hosting.** Running Temporal in production requires deploying and managing four separate services, a database cluster, and Elasticsearch. The History Service alone recommends **4 CPU cores and 6+ GiB memory**. Teams report needing dedicated engineering effort for certificate rotation, configuration management, and monitoring. **Temporal Cloud** eliminates this burden at **~$50 per million actions** (consumption-based pricing), with $1,000 in free credits for new users and $6,000 for qualifying startups.

**Temporal's built-in Saga class** provides first-class compensation pattern support:

```kotlin
@io.temporal.spring.boot.WorkflowImpl(taskQueues = ["BookingTaskQueue"])
class TripBookingWorkflowImpl : TripBookingWorkflow {
    private val activities = Workflow.newActivityStub(
        BookingActivities::class.java,
        ActivityOptions.newBuilder()
            .setStartToCloseTimeout(Duration.ofMinutes(5))
            .build()
    )

    override fun bookTrip(info: BookingInfo) {
        val saga = Saga(Saga.Options.Builder().build())
        try {
            saga.addCompensation(activities::cancelHotel, info.clientId)
            activities.bookHotel(info)

            saga.addCompensation(activities::cancelFlight, info.clientId)
            activities.bookFlight(info)

            saga.addCompensation(activities::cancelCar, info.clientId)
            activities.bookCar(info)
        } catch (e: TemporalFailure) {
            saga.compensate() // Runs all compensations in reverse order
            throw e
        }
    }
}
```

A critical gotcha: register compensations *before* calling the activity, not after. Also, Temporal's default `ActivityCancellationType.TRY_CANCEL` may cause compensations to run before the main activity completes if a workflow cancel signal arrives — use `WAIT_CANCELLATION_COMPLETED` for correctness.

---

## Restate: the lightweight contender with best-in-class Kotlin support

Restate is the most technically compelling newcomer, founded in 2022 by the creators of Apache Flink. Backed by a **$7M seed round** (Redpoint Ventures, with angels including Datadog's founder and Kafka's creators), it reached v1.0 in June 2024 and is currently at **v1.6.2** with ~3,500 GitHub stars. The server is written in Rust, ships as a **single lightweight binary**, and requires no external database — state lives in an embedded RocksDB-based distributed log.

**What makes Restate different.** Rather than running a heavy multi-service cluster, Restate intercepts HTTP calls to your services, journals every step, and replays on failure. Your code runs as a normal HTTP service (or AWS Lambda function); Restate sits in front as a durable execution proxy. This means **dramatically lower operational overhead** compared to Temporal — you deploy a single binary and connect your services.

Restate offers three programming abstractions: **Services** (stateless handlers with durable execution), **Virtual Objects** (stateful entities with K/V state per key, exclusive access — similar to actors), and **Workflows** (durable workflows with a `run` handler). The Kotlin SDK supports **native coroutines** (`suspend` functions) and uses `kotlinx.serialization`, making it the most idiomatically Kotlin-friendly option available:

```kotlin
// build.gradle.kts
implementation("dev.restate:sdk-spring-boot-starter:2.6.0")
ksp("dev.restate:sdk-api-kotlin-gen:2.6.0")
```

```kotlin
@VirtualObject
class Greeter {
    companion object {
        private val COUNT = stateKey<Long>("total")
    }

    @Handler
    suspend fun greet(ctx: ObjectContext, name: String): String {
        val count = ctx.get(COUNT) ?: 0L
        ctx.set(COUNT, count + 1)
        return "Hello $name for the ${count + 1} time!"
    }
}
```

**Restate now has an official Spring Boot starter** (`dev.restate:sdk-spring-boot-starter:2.6.0`) that auto-discovers `@Service`, `@VirtualObject`, and `@Workflow` beans from the Spring context. This addresses what was previously its biggest Spring integration gap.

**The trade-offs are maturity-related.** Restate has limited production references compared to Temporal, a smaller community (~49 contributors vs. 200+), and the runtime uses a **Business Source License** (BSL) — source-available but not OSI-approved open source. The BSL converts to open source after a defined date, and the SDKs are MIT-licensed, but organizations with strict open-source policies should evaluate this. Cluster mode is newer, with some reported stability issues in v1.6.0 (fixed in 1.6.2).

---

## Conductor/Orkes: battle-tested Java-native orchestration

Netflix Conductor was open-sourced in 2016 and archived by Netflix in December 2023. The project lives on as **conductor-oss/conductor**, maintained by **Orkes** — a company founded by the original Conductor creators that raised $20M in February 2024. The server itself is a Java/Spring Boot application with ~18,000+ GitHub stars (including Netflix-era history), making it architecturally familiar to any Spring team.

**The dual DSL/code approach is Conductor's distinguishing feature.** Workflows can be defined as JSON documents (specifying task types, sequences, branches, forks/joins) or programmatically using Java/Kotlin SDKs. The JSON approach makes workflows accessible to non-developers and enables a powerful visual editor/debugger — Conductor's built-in UI for workflow visualization and step-by-step debugging is arguably the best in the category.

```kotlin
// build.gradle.kts
implementation("io.orkes.conductor:orkes-conductor-client-spring:4.0.8")
```

```properties
# application.properties
conductor.server.url=http://localhost:8080/api
```

Workers use the `@WorkerTask` annotation on Spring `@Component` beans:

```kotlin
@Component
class OrderWorkers(private val inventoryService: InventoryService) {
    @WorkerTask(value = "check-inventory", threadCount = 5, pollingInterval = 200)
    fun checkInventory(orderId: String): InventoryResult {
        return inventoryService.check(orderId)
    }
}
```

**Strengths**: the server is Java/Spring Boot (easy to understand and customize), workflow versioning is first-class, built-in system tasks handle HTTP calls and Lambda invocations without custom workers, and it's battle-tested at Netflix scale. **Weaknesses**: JSON DSL becomes unwieldy for complex logic, the worker polling model is less elegant than Temporal's activity stubs, and there's no Kotlin-specific module. The relationship between the open-source project and Orkes's commercial offering introduces open-core divergence risk.

---

## Camunda 8: BPMN standard with enterprise licensing concerns

Camunda 8, powered by the **Zeebe** distributed workflow engine, occupies a unique position as the **BPMN model-first** option. You design workflows as visual BPMN 2.0 diagrams, then implement job workers in code. This bridges technical and business stakeholders — critical for compliance-heavy industries like banking and insurance.

The Spring Boot integration is excellent. An official starter (`io.camunda:camunda-spring-boot-starter`) provides `@JobWorker` annotations, `@Deployment` for deploying BPMN resources at startup, auto-configured `CamundaClient` beans, and Micrometer metrics:

```kotlin
@Component
class PaymentWorker {
    @JobWorker(type = "charge-credit-card")
    fun chargeCreditCard(@Variable totalWithTax: Double): Map<String, Double> {
        // Process payment
        return mapOf("amountCharged" to totalWithTax)
    }
}
```

**The critical caveat is licensing.** As of **Camunda 8.6 (October 2024)**, an enterprise license is required for production use of Zeebe. The previous community license was replaced with the proprietary **Camunda License v1**. Free use is limited to non-commercial purposes (hobby, education, NGOs). Community reports suggest enterprise pricing starts around **$330K/year** for self-managed deployments. This pricing shift has significantly narrowed Camunda's appeal for startups and mid-size teams.

---

## The remaining contenders: niche but notable

**Cadence (Uber)** is still actively maintained (~8,800 GitHub stars, v1.0+ since August 2023) and powers 12 billion+ workflow executions per month at Uber. Its programming model is nearly identical to Temporal (they share lineage), and **NetApp Instaclustr** offers managed Cadence at reportedly **~78% lower cost** than Temporal Cloud. However, the smaller community, less active Java SDK development, and absence of a Spring Boot starter make it hard to recommend for new projects. Choose it only if cost is the primary concern and you're comfortable with a thinner ecosystem.

**Infinitic** is a **Kotlin-first** workflow engine built on Apache Pulsar (~356 GitHub stars, pre-1.0). Its programming model is clean — you define service interfaces and workflow classes that use service stubs, with calls dispatched as durable tasks through Pulsar. The Kotlin API with coroutines is elegant. But the **mandatory Apache Pulsar dependency** is a dealbreaker for most teams (Pulsar itself is complex to operate), and the project has essentially a single maintainer, creating serious bus-factor risk.

**DBOS** takes a radically simple approach: durable execution as a library backed only by PostgreSQL (~189 GitHub stars for Java SDK). No separate server, no additional infrastructure — just annotate methods with `@Workflow`, `@Step`, and `@Transaction`. It works naturally with Spring Boot. The concept is compelling for teams that want incremental durability without architectural changes, but the Java SDK is very early-stage (4 contributors) and throughput is limited by PostgreSQL capacity.

---

## When durable execution transforms your architecture

Durable execution shines in specific scenarios where traditional request-response patterns break down. **Long-running workflows** (order processing, subscription billing, data synchronization) are the canonical case — without durability, any process interruption during a multi-step operation loses all progress and requires manual recovery. Airbyte, for example, uses permanently running Temporal workflows for data sync operations that span hours.

**The saga pattern for distributed transactions** is where durable execution most dramatically reduces complexity. Sagas break distributed transactions into sequential local transactions with compensating actions. Without a durable execution engine, implementing saga orchestration requires building custom state machines, retry logic, compensation coordination, and failure recovery — hundreds of lines of infrastructure code per workflow. With Temporal or Restate, it's a try/catch block. The orchestrator manages all intermediate state, ensuring compensations run correctly even through process crashes.

**Human-in-the-loop workflows** benefit enormously because durable execution can pause indefinitely — hours, days, or months — without consuming compute resources. When approval arrives, the workflow resumes with full context. **Reliable scheduling** surpasses cron/Quartz by persisting the *context* of what happened before and after each scheduled run, enabling conditional scheduling logic. **Retry and compensation logic** becomes declarative rather than hand-coded, with completed steps never re-executed on retry.

### When you should NOT use durable execution

Not every problem warrants this complexity:

- **Simple CRUD operations** — a single database transaction needs no orchestration overhead
- **Low-latency hot paths** — state persistence adds latency per step (less so with Restate's Rust-based engine, but still present)
- **Fire-and-forget async tasks** — if a background job can safely retry from scratch, a message queue (SQS, RabbitMQ) suffices
- **When your team lacks distributed systems experience** — "The biggest predictor of success isn't the tool — it's whether your team understands eventual consistency and compensation logic"

**Critical production pitfalls** deserve attention. **Determinism constraints** prohibit using random numbers, system clocks, or UUID generation directly in workflow code — all must be wrapped in activities. **Versioning** is the #1 operational pain point at scale: every workflow code change requires careful version management, or replay will fail and cause incidents. **History growth** is bounded — Temporal enforces a 50K event / 50MB limit per execution, with performance degrading after ~10K events. Long-running workflows must use `ContinueAsNew`, which is notoriously difficult to implement correctly. **Payload size limits** (Temporal's 2MB per activity) catch teams off guard when they pass large objects through workflows.

---

## Comparison matrix: the top 6 tools at a glance

| Dimension | Temporal | Restate | Conductor/Orkes | Camunda 8 | Infinitic | DBOS |
|-----------|----------|---------|-----------------|-----------|-----------|------|
| **Paradigm** | Code-first | Code-first | JSON DSL + code | BPMN model-first | Code-first | Code-first (library) |
| **Spring Boot starter** | ✅ Official | ✅ Official | ✅ Orkes SDK | ✅ Official | ❌ Community only | ✅ Works OOTB |
| **Kotlin coroutines** | ❌ Not supported | ✅ Native suspend | ❌ Java interop | ❌ Java interop | ✅ Kotlin-first | ❌ Java interop |
| **Self-host complexity** | High (4 services + DB + ES) | Low (single binary) | Medium (Java app + Redis/DB) | Medium-high (cluster + ES) | High (Pulsar + DB) | Very low (just Postgres) |
| **Managed offering** | Temporal Cloud (~$50/M actions) | Restate Cloud (emerging) | Orkes (custom pricing) | Camunda SaaS (enterprise) | None | DBOS Conductor (free tier) |
| **GitHub stars** | ~15,900 | ~3,500 | ~18,000+ | ~2,800 | ~356 | ~189 (Java) |
| **Built-in saga support** | ✅ `Saga` class | Manual (via durable steps) | Via workflow definition | Via BPMN compensation | Manual try/catch | Manual |
| **License** | MIT / Apache 2.0 | BSL (runtime) / MIT (SDKs) | Apache 2.0 | Camunda License v1 (paid prod) | Commons Clause + MIT | MIT |
| **Scalability** | Excellent (billions of workflows) | Good (newer, less proven) | Excellent (Netflix-scale) | Good (partitioned) | Good (via Pulsar) | Limited (Postgres-bound) |
| **Persistence options** | Postgres, MySQL, Cassandra | Built-in (RocksDB) | Redis, Postgres, MySQL, Cassandra | Built-in (RocksDB) + ES | Pulsar + Postgres/Redis/MySQL | PostgreSQL |
| **Production maturity** | High (hundreds of companies) | Growing (post-1.0 since mid-2024) | High (Netflix heritage) | High (enterprise) | Low (pre-1.0, single maintainer) | Very early (Java SDK) |

---

## A complete Temporal workflow in Kotlin with Spring Boot

This end-to-end example demonstrates defining, starting, querying, and compensating a workflow:

```kotlin
// === Workflow Interface ===
@WorkflowInterface
interface OrderWorkflow {
    @WorkflowMethod
    fun processOrder(orderId: String): OrderResult

    @SignalMethod
    fun cancelOrder()

    @QueryMethod
    fun getStatus(): String
}

// === Activity Interface ===
@ActivityInterface
interface OrderActivities {
    @ActivityMethod fun validateOrder(orderId: String): Boolean
    @ActivityMethod fun processPayment(orderId: String): PaymentResult
    @ActivityMethod fun shipOrder(orderId: String): ShipmentResult
    @ActivityMethod fun refundPayment(orderId: String)
}

// === Activity Implementation (Spring bean with full DI) ===
@Component
@io.temporal.spring.boot.ActivityImpl(taskQueues = ["OrderTaskQueue"])
class OrderActivitiesImpl(
    private val paymentService: PaymentService,    // Spring-injected
    private val inventoryService: InventoryService  // Spring-injected
) : OrderActivities {
    @Transactional  // Works normally in activities
    override fun validateOrder(orderId: String) = inventoryService.checkAvailability(orderId)
    override fun processPayment(orderId: String) = paymentService.charge(orderId)
    override fun shipOrder(orderId: String) = inventoryService.ship(orderId)
    override fun refundPayment(orderId: String) = paymentService.refund(orderId)
}

// === Workflow Implementation ===
@io.temporal.spring.boot.WorkflowImpl(taskQueues = ["OrderTaskQueue"])
class OrderWorkflowImpl : OrderWorkflow {
    private val activities = Workflow.newActivityStub(
        OrderActivities::class.java,
        ActivityOptions.newBuilder()
            .setStartToCloseTimeout(Duration.ofSeconds(30))
            .setRetryOptions(RetryOptions.newBuilder().setMaximumAttempts(3).build())
            .build()
    )
    private var status = "PENDING"

    override fun processOrder(orderId: String): OrderResult {
        status = "VALIDATING"
        if (!activities.validateOrder(orderId))
            return OrderResult(false, "Validation failed")

        status = "PROCESSING_PAYMENT"
        val payment = activities.processPayment(orderId)

        status = "SHIPPING"
        val shipment = activities.shipOrder(orderId)

        status = "COMPLETED"
        return OrderResult(true, "Shipped: ${shipment.trackingId}")
    }

    override fun cancelOrder() { status = "CANCELLED" }
    override fun getStatus(): String = status
}

// === REST Controller (start + query workflows) ===
@RestController
@RequestMapping("/orders")
class OrderController(private val workflowClient: WorkflowClient) {
    @PostMapping("/{orderId}")
    fun startOrder(@PathVariable orderId: String): ResponseEntity<String> {
        val workflow = workflowClient.newWorkflowStub(
            OrderWorkflow::class.java,
            WorkflowOptions.newBuilder()
                .setTaskQueue("OrderTaskQueue")
                .setWorkflowId("order-$orderId")
                .build()
        )
        WorkflowClient.start(workflow::processOrder, orderId)
        return ResponseEntity.ok("Workflow started: order-$orderId")
    }

    @GetMapping("/{orderId}/status")
    fun getStatus(@PathVariable orderId: String): ResponseEntity<String> {
        val workflow = workflowClient.newWorkflowStub(OrderWorkflow::class.java, "order-$orderId")
        return ResponseEntity.ok(workflow.getStatus())
    }
}
```

**Key integration note**: `@Transactional` and Spring DI work normally in activity implementations. Never use `@Transactional` or any I/O in workflow implementations — workflows replay from event history and must produce identical results.

---

## A Restate virtual object in Kotlin with coroutines

Restate's Kotlin SDK demonstrates how different the programming model feels compared to Temporal:

```kotlin
// build.gradle.kts
implementation("dev.restate:sdk-spring-boot-starter:2.6.0")
ksp("dev.restate:sdk-api-kotlin-gen:2.6.0")

// === Virtual Object: stateful, single-writer per key ===
@VirtualObject
class ShoppingCart {
    companion object {
        private val ITEMS = stateKey<List<CartItem>>("items")
    }

    @Handler
    suspend fun addItem(ctx: ObjectContext, item: CartItem): String {
        val items = ctx.get(ITEMS) ?: emptyList()
        ctx.set(ITEMS, items + item)
        return "Added ${item.name} to cart ${ctx.key()}"
    }

    @Handler
    suspend fun checkout(ctx: ObjectContext): OrderConfirmation {
        val items = ctx.get(ITEMS) ?: throw IllegalStateException("Cart empty")

        // ctx.run() wraps non-deterministic operations for durability
        val paymentId = ctx.run { paymentGateway.charge(items.totalPrice()) }
        val shipmentId = ctx.run { shippingService.createShipment(items) }

        ctx.clear(ITEMS)
        return OrderConfirmation(paymentId, shipmentId)
    }

    @Shared  // Concurrent reads allowed
    suspend fun getItems(ctx: SharedObjectContext): List<CartItem> {
        return ctx.get(ITEMS) ?: emptyList()
    }
}
```

The `suspend` keyword, `kotlinx.serialization`, and the actor-like Virtual Object model make this feel native to Kotlin. State is managed entirely by the Restate server — no database configuration needed in your application.

---

## Practical decision framework for your stack

Given your stack (Kotlin/Spring Boot on AWS EKS/ECS with PostgreSQL, Redis, and Kafka), here is a concrete recommendation:

**Choose Temporal if** your team values ecosystem maturity, extensive documentation, and you're willing to either pay for Temporal Cloud or invest in self-hosting infrastructure. It's the safest bet for production and has the most Stack Overflow answers, tutorials, and third-party integrations. The lack of Kotlin coroutine support is annoying but not blocking.

**Choose Restate if** you prioritize operational simplicity, want native Kotlin coroutines, and are comfortable adopting a newer tool (post-1.0 since mid-2024). Its single-binary deployment on EKS is dramatically simpler than Temporal's multi-service cluster. The BSL license and smaller community are real risks to weigh.

**Choose Conductor/Orkes if** your workflows benefit from JSON definitions and visual debugging, or if your team includes non-developer stakeholders who need to understand and modify workflows. The Java-native server on Spring Boot makes it architecturally familiar.

**Avoid Camunda 8** unless you have specific BPMN compliance requirements — the enterprise licensing cost (~$330K/year self-managed) is prohibitive for most teams. **Avoid Infinitic** due to the mandatory Pulsar dependency and single-maintainer risk. **Consider DBOS** only as a lightweight experimentation — its "just PostgreSQL" approach is elegant for simple cases, but the Java SDK is too immature for production workloads.

For most Kotlin/Spring Boot teams starting fresh in 2025–2026, **Temporal with Temporal Cloud** provides the strongest combination of developer experience, operational simplicity (when managed), and production safety. If you're cost-sensitive or want to minimize infrastructure, **Restate** deserves serious evaluation — its trajectory suggests it may become the standard within a few years.