---
title: "GraphQL"
category: "APIs & Protocols"
description: "GraphQL schema design and implementation in Spring Boot"
---

# GraphQL mastery plan for Kotlin Spring Boot developers

**Start with DGS on top of Spring for GraphQL — they merged in 2024, and this combination gives you Netflix's battle-tested tooling with Spring's native foundation.** The GraphQL ecosystem in Spring Boot underwent a tectonic shift: Netflix DGS v10 (early 2025) removed all legacy code and now runs entirely on Spring for GraphQL underneath. This means you learn one unified platform, not two competing frameworks. The plan below takes you from zero to production-grade federated GraphQL in roughly 16 weeks, structured for depth-first mastery with milestone projects at each phase.

The landscape is simpler than it appears. Spring for GraphQL provides the engine (transport, execution, security, observability). Netflix DGS adds an opinionated developer experience layer (code generation, annotations, testing utilities, federation). Both are schema-first. Both work with Kotlin. You'll learn both programming models because they coexist in the same application.

---

## Phase 1: Foundations and rapid productivity (weeks 1–3)

**Goal:** Understand GraphQL's type system deeply, build a working API, and establish the mental model that replaces REST thinking.

### Week 1 — GraphQL concepts without any framework

Before touching Spring Boot, internalize GraphQL's core ideas. The type system is GraphQL's backbone — **SDL (Schema Definition Language), scalar types, object types, input types, enums, interfaces, unions, and the nullability model** all deserve focused study. Key concepts to nail: queries vs mutations vs subscriptions, arguments and variables, fragments (named and inline), directives (`@skip`, `@include`, `@deprecated`), and introspection.

The critical mental shift from REST: GraphQL has no endpoint-per-resource. One endpoint serves all operations. Clients request exactly the fields they need. Errors return alongside partial data in a 200 response. There is no API versioning — schemas evolve through deprecation and additive changes.

**Resources for Week 1:**
- **graphql.org/learn** — Work through every page of the official tutorial. It covers queries, schemas, validation, execution, and best practices in ~2 hours of focused reading
- **"GraphQL with Java and Spring"** by Andreas Marek and Donna Zhou (Leanpub/Amazon, 2023) — Written by the creator of GraphQL Java and a co-author of Spring for GraphQL. This is the single best book for JVM developers
- **"Production Ready GraphQL"** by Marc-André Giroux (self-published, 2020) — The definitive guide to schema design and GraphQL architecture, written by a Netflix GraphQL platform engineer (previously GitHub and Shopify). Language-agnostic, pattern-focused. Read chapters 1–4 in week 1, save the rest for Phase 2
- **GraphQL specification** at spec.graphql.org — Skim for reference; return to specific sections as questions arise

**Schema design conventions to adopt immediately:** camelCase for fields and arguments, PascalCase for types, SCREAMING_SNAKE_CASE for enum values, `Input` suffix for input types (e.g., `CreateBookInput`), `Payload` suffix for mutation responses. Make fields nullable by default — only use `!` (non-null) when the server can guarantee a value. These conventions match what Netflix, GitHub, and Shopify use in production.

### Week 2 — Spring for GraphQL with Kotlin: first working API

Set up a Spring Boot 3.x project using Spring Initializr with **Spring for GraphQL** + **Spring Web** + **Kotlin**. Dependencies are minimal:

```kotlin
implementation("org.springframework.boot:spring-boot-starter-graphql")
implementation("org.springframework.boot:spring-boot-starter-web")
implementation("org.jetbrains.kotlinx:kotlinx-coroutines-reactor")
```

Place `.graphqls` schema files in `src/main/resources/graphql/`. Spring for GraphQL's annotation model mirrors REST controllers — `@QueryMapping`, `@MutationMapping`, `@SchemaMapping`, and `@SubscriptionMapping` on `@Controller` classes. **Kotlin coroutine support is first-class**: annotate handlers as `suspend` functions and Spring adapts them to `Mono` automatically. Return `Flow<T>` for subscriptions and it adapts to `Flux<T>`.

Build a simple domain: a book catalog with authors. Implement queries (`books`, `bookById`), a mutation (`createBook`), and nested field resolution (`Book.author` via `@SchemaMapping`). Enable GraphiQL (`spring.graphql.graphiql.enabled=true`) and explore your schema interactively.

**Key Spring for GraphQL features to use in week 2:**
- `@Argument` for binding GraphQL arguments to Kotlin parameters
- `@SchemaMapping` for nested type resolution (this is where N+1 problems live — note it for now, solve in Phase 2)
- Schema mapping inspection at startup — Spring validates that every schema field has a resolver or matching property, catching mismatches early
- Null-safety alignment — Spring checks that Kotlin nullable types (`String?`) match GraphQL nullable fields

**Resources:** Spring for GraphQL reference docs (docs.spring.io/spring-graphql/reference), Spring Boot GraphQL auto-configuration docs, and the Baeldung tutorial at baeldung.com/spring-graphql.

### Week 3 — Add Netflix DGS and code generation

Now layer DGS on top. Replace the starter with DGS's integrated starter:

```kotlin
implementation(platform("com.netflix.graphql.dgs:graphql-dgs-platform-dependencies:LATEST"))
implementation("com.netflix.graphql.dgs:dgs-starter")
```

Add the DGS codegen Gradle plugin (`com.netflix.dgs.codegen`). Configure it to generate Kotlin data classes from your schema. This is DGS's killer feature — **run `./gradlew generateJava` and get type-safe Kotlin data classes, constants, and client query builders** generated from your `.graphqls` files. Set `generateKotlinNullableClasses = true` for proper nullable type alignment.

Rewrite your book catalog using DGS annotations: `@DgsComponent` on resolver classes, `@DgsQuery`, `@DgsMutation`, `@DgsData` for field resolution. Note the difference in feel — DGS annotations are more explicit about parent types. The DGS IntelliJ plugin (install it) provides schema-to-code navigation that dramatically improves the development experience.

**Critical insight:** Since DGS v10, you can mix `@QueryMapping` (Spring for GraphQL) and `@DgsQuery` (DGS) in the same application. They compile to the same execution engine. Netflix recommends consistency within a project, but understanding both models is valuable.

### Milestone project: Book catalog API

Build a complete book management API with authors, categories, and reviews. Requirements: 5+ query fields, 3+ mutations, enum types, input types, at least one interface or union type, error handling for not-found cases. Write tests using both `GraphQlTester` (Spring) and `DgsQueryExecutor` (DGS) to understand each testing approach.

**Success indicators:** You can write a GraphQL schema from scratch, implement all resolvers in Kotlin, use codegen to generate types, explain the difference between Spring for GraphQL and DGS annotations, and run queries in GraphiQL with variables and fragments.

---

## Phase 2: Intermediate patterns that prevent production pain (weeks 4–7)

**Goal:** Solve the N+1 problem with DataLoaders, implement proper pagination, integrate Spring Security, handle errors gracefully, and migrate an existing REST endpoint.

### DataLoaders are the single most important optimization

Every nested field resolver in GraphQL independently fetches data. Query 20 books, each resolving an `author` field — that's 21 database queries (1 + N). **DataLoader batches these into 2 queries** by deferring individual loads and dispatching them together at each execution level.

Spring for GraphQL offers two approaches. The declarative `@BatchMapping` is elegant — a method accepts `List<Book>` and returns `Map<Book, Author>`, and Spring handles all DataLoader wiring:

```kotlin
@BatchMapping
suspend fun author(books: List<Book>): Map<Book, Author> {
    return authorService.findByBookIds(books.map { it.authorId })
        .associateBy { author -> books.first { it.authorId == author.id } }
}
```

The programmatic `BatchLoaderRegistry` gives more control — register batch loading functions as Spring beans, then inject `DataLoader<K, V>` into `@SchemaMapping` methods.

DGS uses `@DgsDataLoader` on classes implementing `BatchLoader<K,V>` or `MappedBatchLoader<K,V>`, accessed via `DgsDataFetchingEnvironment.getDataLoader()`. DGS also offers **ticker mode** (`dgs.graphql.dataloader.ticker-mode-enabled=true`) that auto-dispatches every 10ms — useful for deeply nested DataLoader chains where manual dispatch timing is tricky.

**Critical pitfall:** Always create a new DataLoaderRegistry per request to prevent cross-request data leakage. Both frameworks handle this automatically, but understand why. Also, DataLoader batch functions must return results in the **same order** as input keys — violating this contract causes silent data corruption.

### Pagination: adopt cursor-based from the start

Implement three patterns to understand tradeoffs, then default to cursor-based:

**Offset-based** (`books(limit: 10, offset: 20)`) is simple but breaks under concurrent writes and degrades at high offsets. Use only for admin UIs with page numbers.

**Cursor-based** with the **Relay Connection specification** is the industry standard. The schema pattern uses Connection, Edge, and PageInfo types. Spring for GraphQL has built-in support via `ScrollSubrange` and `CursorStrategy` integrating with Spring Data's `Window<T>`. DGS provides `graphql.relay` types and auto-generates connection types from schema.

**Spring Data integration** (Spring for GraphQL only) is powerful here: `@GraphQlRepository` auto-registers repository query methods as data fetchers, and QueryDSL/Query by Example support eliminates boilerplate for filtering and sorting.

### Security integration with Spring Security

Standard Spring Security works seamlessly — this is where Spring for GraphQL's native integration shines. Protect the `/graphql` endpoint with a `SecurityFilterChain`, then use `@PreAuthorize` directly on resolver methods for field-level authorization:

```kotlin
@PreAuthorize("hasRole('ADMIN') or #user.id == authentication.principal.id")
@SchemaMapping
fun email(user: User): String = user.email
```

`SecurityContext` propagates automatically to resolvers in both WebMVC (ThreadLocal) and WebFlux (Reactor Context). For DataLoader threads, ensure propagation via `DelegatingSecurityContextExecutorService`. DGS supports the same annotations on `@DgsData` methods.

**WebSocket security** for subscriptions requires attention — session cookies propagate automatically, but Bearer tokens need explicit handling in the initial WebSocket connection message.

### Error handling patterns

GraphQL's error model is fundamentally different from REST. Responses always return HTTP 200. The `errors` array coexists with `data` — a single response can contain both partial results and errors. **Non-null field errors propagate upward**: if a non-null field fails, null cascades to the nearest nullable parent, potentially nullifying the entire response branch. Design root query fields as nullable to prevent this.

Spring for GraphQL uses `DataFetcherExceptionResolverAdapter` or the newer `@GraphQlExceptionHandler` (1.3+) in `@ControllerAdvice` classes. DGS integrates with this same mechanism since v10. Netflix advocates a dual approach: **unexpected errors** go in the `errors` array, while **business errors** (user not found, validation failures) are modeled as schema types using unions: `union UserResult = User | UserNotFound`.

### Deployment scenario: REST-to-GraphQL migration

Practice the hybrid approach. Take an existing REST controller and add GraphQL alongside it:

```kotlin
// Shared service layer — unchanged
@Service
class UserService(private val repo: UserRepository) {
    fun findById(id: String): User = repo.findById(id).orElseThrow()
}

// Existing REST controller — still works
@RestController
@RequestMapping("/api/v1/users")
class UserRestController(private val userService: UserService) { ... }

// New GraphQL resolver — wraps same service
@DgsComponent
class UserDataFetcher(private val userService: UserService) {
    @DgsQuery
    fun user(@InputArgument id: String): User = userService.findById(id)
}
```

Both endpoints coexist. Migrate clients incrementally. The service layer requires no changes — GraphQL resolvers are thin wrappers. Configure `application.yml` to serve REST at `/api/v1/*`, GraphQL at `/graphql`, and management at `/actuator/*`.

### Milestone project: E-commerce API with migration

Extend your book catalog into an e-commerce platform. Start with REST endpoints for orders and customers, then migrate to GraphQL while keeping REST operational. Requirements: DataLoaders for all N+1 relationships, cursor-based pagination on product listings, Spring Security with role-based field access (admins see revenue data, customers see only their orders), proper error handling with both error-array and errors-as-data patterns, comprehensive test suite.

**Success indicators:** You can explain and implement DataLoader batching, design Relay-compliant pagination, secure individual fields with Spring Security, handle errors without leaking implementation details, and run REST and GraphQL side by side in one application.

**Additional resources for Phase 2:**
- Finish "Production Ready GraphQL" chapters 5–10 (pagination, security, performance)
- Udemy course "Code GraphQL Application: Java Spring Boot 3 & Netflix DGS" by Timotius Pamungkas (4.6 stars, updated November 2024) — covers query, mutation, subscription, and PostgreSQL integration
- Netflix DGS examples in Kotlin: github.com/Netflix/dgs-examples-kotlin — study the DataLoader and testing patterns
- OWASP GraphQL Cheat Sheet: cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html

---

## Phase 3: Advanced topics and federation architecture (weeks 8–12)

**Goal:** Master GraphQL federation for microservices, implement subscriptions, optimize performance, and understand schema evolution strategies.

### Federation transforms GraphQL from monolith to distributed graph

GraphQL federation allows multiple microservices (subgraphs) to expose portions of a unified schema, composed at a gateway/router layer. This is how Netflix runs GraphQL at scale — **~70+ Domain Graph Services, hundreds of developers, billions of requests daily**.

**Apollo Federation v2** (the current standard) uses key directives: `@key` identifies entity types with unique keys, `@shareable` allows multiple subgraphs to resolve the same field, `@inaccessible` hides internal fields from the public API, `@override` enables progressive field migration between subgraphs, and `@external`/`@requires`/`@provides` control cross-subgraph data dependencies. The `@link` directive opt-in distinguishes v2 from v1.

**DGS has first-class federation support** — this is its primary differentiator over plain Spring for GraphQL. Use `@DgsEntityFetcher` for entity resolution:

```kotlin
@DgsComponent
class ShowEntityFetcher(private val showService: ShowService) {
    @DgsEntityFetcher(name = "Show")
    fun show(values: Map<String, Any>): Show {
        return showService.findById(values["id"] as String)
    }
}
```

Spring for GraphQL added `@EntityMapping` support in v1.3 (2024) using the `federation-jvm` library (v5.3.0). It supports `@Argument` for entity IDs, batch resolution via `List<ID> → List<T>`, and DataLoader integration. Both approaches work; DGS's is more mature and better documented for federation specifically.

**Gateway/router options matter.** Apollo Router (Rust-based, high performance) is the dominant choice but has enterprise features behind a GraphOS license. **Cosmo Router by WunderGraph** is fully open-source (Apache 2.0), Go-based, and offers a drop-in Apollo replacement with built-in OpenTelemetry, Prometheus metrics, and advanced batching. Netflix built their own gateway in Kotlin — query planning overhead stays under 10ms. For learning and most production scenarios, Apollo Router or Cosmo Router is the practical choice.

### How Netflix designs their federated graph

Netflix's journey from a monolithic Studio API to a federated architecture offers key lessons. Their biggest challenge was organizational, not technical — getting dozens of teams to agree on schema ownership boundaries. They solved this with clear domain boundaries: each DGS team owns their portion of the graph. Authorization is delegated to DGS owners, ensuring consistency. Five infrastructure components support the architecture: DGS services (subgraphs), federated gateway, schema registry, developer tooling, and observability (Zipkin, Edgar, TellTale).

**Schema composition and validation** happen in CI. Tools like Apollo's Rover CLI (`rover subgraph check`), GraphQL Inspector (open-source, by The Guild), or WunderGraph's `wgc` CLI detect breaking changes before deployment. **Managed federation** (Apollo GraphOS or Cosmo Cloud) stores and composes schemas centrally, delivers supergraph config via CDN, and tracks per-field usage analytics. **Unmanaged federation** composes schemas locally or in CI.

### Subscriptions for real-time data

Spring for GraphQL supports three transports: **WebSocket** (using the modern `graphql-ws` protocol from The Guild), **Server-Sent Events** (simpler operationally, works with standard HTTP load balancers), and **RSocket** (for request-stream patterns). Enable WebSocket via `spring.graphql.websocket.path=/ws/graphql`. SSE works on the standard `/graphql` endpoint with `text/event-stream` — no extra configuration.

Kotlin `Flow<T>` works directly with `@SubscriptionMapping` — Spring adapts it to `Flux<T>` automatically. For scaling subscriptions in production, use **Redis Pub/Sub** or Kafka as a message broker between service instances. SSE is simpler to operate (no connection state, standard HTTP load balancers work without sticky sessions) and is increasingly preferred over WebSocket.

### Performance optimization beyond DataLoaders

**Persisted queries** are the strongest performance and security measure. Automatic Persisted Queries (APQ) have the client send a query hash first; the server looks up the full query from cache. **Trusted documents** go further — pre-register all allowed queries at build time and reject anything not on the allowlist. This eliminates parsing/validation overhead and prevents arbitrary query attacks entirely.

**Query complexity and depth limiting** use GraphQL Java's built-in instrumentations. Register `MaxQueryComplexityInstrumentation(200)` and `MaxQueryDepthInstrumentation(10)` as Spring beans — Spring for GraphQL auto-wires them. Apollo Federation v2.9 adds `@cost` and `@listSize` directives for fine-grained demand control at the schema level.

**`@defer` and `@stream` directives** (experimental in GraphQL Java 22 and Spring for GraphQL 1.3) allow streaming partial responses — the server returns immediately available data first, then streams deferred fragments. This dramatically improves perceived latency for complex queries.

**Caching strategies** differ from REST. Response-level caching works with APQ + GET requests for queries. Entity-level caching (Redis) at the DataLoader layer is more granular. CDN caching is challenging since GraphQL defaults to POST, but persisted queries with GET overcome this.

### Schema evolution without versioning

GraphQL's philosophy: one versionless, continuously evolving API. **Add → Deprecate → Monitor → Remove.** New fields never break existing clients (they simply don't request them). Mark deprecated fields with `@deprecated(reason: "Use fullName instead")`. Monitor usage analytics in Apollo Studio, GraphQL Hive, or Cosmo analytics. Remove fields only when usage reaches zero. Netflix uses "API brownouts" — temporarily disabling deprecated fields to surface remaining consumers.

**Breaking change detection** in CI is essential. GraphQL Inspector (`npx graphql-inspector diff old.graphqls new.graphqls`) categorizes changes as Breaking, Dangerous, or Safe. Apollo's `rover subgraph check` validates against actual client operation usage data.

### Milestone project: Federated microservices

Build three DGS subgraphs (Products, Reviews, Users) with Apollo Federation v2. Products owns the `Product` entity, Reviews extends it with a `reviews` field, Users extends it with a `createdBy` field. Set up Apollo Router or Cosmo Router as the gateway. Implement entity resolution with batch loading, subscriptions for real-time review notifications (via WebSocket or SSE), query complexity limiting, and schema validation in a CI pipeline using GraphQL Inspector.

**Success indicators:** You can design entity boundaries across subgraphs, implement `@DgsEntityFetcher` with batch resolution, configure and run a federation gateway, explain the difference between managed and unmanaged federation, implement subscriptions with Kotlin Flow, and enforce query complexity limits.

**Resources for Phase 3:**
- Netflix DGS federation example: github.com/Netflix/dgs-federation-example
- Netflix Tech Blog: "How Netflix Scales its API with GraphQL Federation" series
- Apollo Federation docs: apollographql.com/docs/federation
- WunderGraph Cosmo docs: cosmo-docs.wundergraph.com
- Spring for GraphQL federation reference: docs.spring.io/spring-graphql/reference/federation.html
- "A Tale of Two Frameworks" — Netflix blog on the DGS/Spring GraphQL merger: netflixtechblog.medium.com
- Conference talks: Spring I/O 2024 "GraphQL Java and Spring: The Latest Features," DGS video series at netflix.github.io/dgs/videos/

---

## Phase 4: Production mastery on AWS EKS (weeks 13–16)

**Goal:** Deploy a production-grade GraphQL API with full observability, comprehensive testing, CI/CD schema governance, and operational hardening.

### Observability requires GraphQL-aware instrumentation

Traditional HTTP monitoring is useless for GraphQL — every request hits `POST /graphql`. You must instrument at the **operation level**. Spring for GraphQL provides three built-in Micrometer observations: `graphql.request` (per-operation latency tagged by operation type and name), `graphql.datafetcher` (per-resolver timing), and `graphql.dataloader` (batch sizes and timing, added in 1.3). DGS adds `graphql-dgs-spring-boot-micrometer` with query complexity scoring, error counting by type, and per-resolver timers with cardinality limiting.

**OpenTelemetry integration** is straightforward. On Spring Boot 3.x, use `micrometer-tracing-bridge-otel` with an OTLP exporter. On Spring Boot 4.x, the new single `spring-boot-starter-opentelemetry` dependency auto-configures traces, metrics, and OTLP export. The zero-code option: attach the OpenTelemetry Java Agent (`-javaagent:opentelemetry-javaagent.jar`) for automatic instrumentation of Spring MVC, JDBC, HTTP clients, and GraphQL operations. GraphQL spans automatically include operation name, type, and field paths.

Build a **Grafana dashboard stack** (Prometheus for metrics, Tempo for traces, Loki for logs) with key panels: request rate by operation, p99 latency by operation, error rate by classification, DataLoader batch efficiency, and JVM heap usage. Use exemplars to drill from a metric spike to a specific trace to correlated logs. Datadog and New Relic both support GraphQL via OTel Agent export.

**Logging best practices:** Log operation name and execution ID on every request via MDC. In development, log full queries. In production, log operation names only — query bodies are a security risk. Use structured JSON logging (Logback JSON encoder) with traceId in every log line for correlation.

### Testing strategy spans four layers

**Unit tests** with `@GraphQlTest` (Spring) or `@EnableDgsTest` (DGS) are slice tests — they load only GraphQL infrastructure, mock the service layer, and execute queries without HTTP transport. DGS's `DgsQueryExecutor` supports JsonPath extraction for concise assertions.

**Integration tests** with `@SpringBootTest` use `HttpGraphQlTester` (MockMvc-backed) or full `WebEnvironment.RANDOM_PORT` with Testcontainers for database integration. Store test queries in `src/test/resources/graphql-test/*.graphql` files and reference them by name.

**Contract tests** treat the `.graphqls` schema as the contract. Run `graphql-inspector diff` in CI against the production schema to catch breaking changes. For consumer-driven contracts, Apollo Studio and GraphQL Hive track which fields clients actually use, enabling safe removal of unused fields.

**Performance tests** with k6 target the `/graphql` endpoint with realistic query payloads. Tag requests by operation name for per-operation metrics. Test different query complexities separately — a simple `{ user(id: "1") { name } }` and a deeply nested aggregation query stress very different code paths. Set thresholds: p95 latency under 500ms, error rate under 1%.

### AWS EKS deployment architecture

Deploy Spring Boot GraphQL on EKS with **3+ replicas**, health probes against `/actuator/health/liveness` and `/actuator/health/readiness`, and resource limits tuned for GraphQL workloads (start with 512Mi–1Gi memory, 250m–1000m CPU). JVM flags: `-XX:MaxRAMPercentage=75.0 -XX:+UseG1GC -XX:MaxGCPauseMillis=200`. Enable virtual threads with `spring.threads.virtual.enabled=true` on Java 21+.

**AWS ALB** handles HTTP and WebSocket routing. Set `alb.ingress.kubernetes.io/idle-timeout` to 120+ seconds for complex queries. ALB supports WebSocket natively for subscriptions. Use NLB only if you need extreme WebSocket throughput.

**HPA scaling** based on CPU utilization (target 60%) works for most cases. Add custom metrics (graphql_request_duration_p95) via Prometheus Adapter for more sophisticated scaling. CDN (CloudFront) challenges: GraphQL uses POST, which CloudFront doesn't cache by default. Use GET with persisted query hashes for cacheable read operations, or treat CDN as static-asset-only.

**Self-hosted on EKS vs AWS AppSync:** For a Spring Boot/Kotlin team with complex domain logic, self-hosted wins decisively. AppSync limits you to VTL/JS resolvers and Lambda, has limited federation support, and lacks the Kotlin ecosystem integration. AppSync is only appropriate for simple serverless prototypes.

### Production hardening checklist

Enforce these before going live: disable introspection in production (`spring.graphql.schema.introspection.enabled=false`), set query depth limit (**10–15 levels**), set query complexity limit (**200–500 points**), enable persisted queries or trusted documents for internal APIs, implement cost-based rate limiting (not request-count — one GraphQL request can vary 1000x in cost), configure request body size limits to prevent massive payloads, sanitize error responses (no stack traces), and configure CORS for the `/graphql` endpoint.

For federated architectures, add circuit breakers (`CircuitBreakerFactory` wrapping service calls in resolvers) for graceful degradation when subgraphs are unavailable. Configure gateway-level per-subgraph timeouts. Return partial data with errors rather than failing entire queries — this is GraphQL's superpower.

### Milestone project: Production-ready federated API

Take your Phase 3 federated architecture and harden it for production. Deploy to a local Kubernetes cluster (minikube or kind, or EKS if available). Requirements: full OpenTelemetry traces and metrics flowing to a Grafana stack, Prometheus alerts for p99 latency breaches, all four testing layers in a CI pipeline (GitHub Actions), schema breaking change detection blocking merges, DataLoader batch efficiency above 80%, query depth and complexity limits enforced, structured JSON logging with trace correlation, and HPA scaling under load (test with k6).

**Success indicators:** You can operate a GraphQL API in production with confidence. You can diagnose a slow query from a Grafana alert through to a specific DataLoader span. You can explain why a schema change is safe or breaking. You can tune JVM and DataLoader parameters based on observed metrics.

---

## Framework decision: when to choose what

| Scenario | Recommendation | Rationale |
|----------|---------------|-----------|
| New Kotlin project, small team | Spring for GraphQL | Simpler, fewer dependencies, excellent coroutine support, Spring Data integration |
| Federation required | DGS Framework | First-class federation support, battle-tested at Netflix across 70+ services |
| Large team, codegen important | DGS Framework | Codegen plugin generates Kotlin data classes, IntelliJ plugin aids navigation |
| Code-first schema preferred | Expedia graphql-kotlin | Pure Kotlin, generates schema from classes, Spring Boot integration |
| Already using DGS | Stay on DGS v10+ | It now runs on Spring for GraphQL internally — you get both |
| Maximum Spring ecosystem integration | Spring for GraphQL | QueryDSL, Spring Data, @GraphQlRepository, native observability |

The convergence is the key insight. **DGS v10+ is Spring for GraphQL with extras.** You can use `@QueryMapping` and `@DgsQuery` in the same app. The choice is more about team preference and whether you need codegen/federation than about fundamentally different platforms.

---

## Complete resource library

### Essential reading (priority order)

The **"GraphQL with Java and Spring"** book by Andreas Marek and Donna Zhou is the single highest-value resource for JVM developers — it covers fundamentals through production patterns with the authority of the GraphQL Java and Spring for GraphQL creators. Pair it with **"Production Ready GraphQL"** by Marc-André Giroux for schema design mastery and architectural thinking. The official **graphql.org/learn** tutorial is the best free starting point for concepts. For the latest patterns, **"GraphQL Best Practices"** by Artur Czemiel (Packt, October 2024) covers federation, security, and AI-assisted development.

### Documentation and tutorials

Official Spring for GraphQL reference at docs.spring.io/spring-graphql/reference covers annotated controllers, testing, security, and observability with both Java and Kotlin examples. Netflix DGS docs at netflix.github.io/dgs cover getting started, codegen, federation, and testing with Kotlin examples throughout. Baeldung maintains several tutorials: baeldung.com/spring-graphql (core setup), baeldung.com/spring-boot-domain-graph-service (DGS-specific). The OWASP GraphQL Cheat Sheet is essential for security hardening.

### Courses

The highest-rated Udemy course is **"Code GraphQL Application: Java Spring Boot 3 & Netflix DGS"** by Timotius Pamungkas (4.6 stars, 398 ratings, updated November 2024). The only Kotlin-specific course is **"Full Stack GraphQL With Spring Boot Kotlin and React Apollo"** on Udemy. For reactive patterns, the **"Reactive GraphQL Masterclass for Java Spring Boot Developers"** covers WebFlux integration.

### GitHub repositories to study

**Netflix/dgs-examples-kotlin** is the best Kotlin reference — a full DGS app with mutations, subscriptions, DataLoaders, file uploads, and testing. **ExpediaGroup/graphql-kotlin** is the premier pure-Kotlin GraphQL library for code-first development. **Netflix/dgs-federation-example** demonstrates multi-service federation. Spring for GraphQL's own samples live in the spring-projects/spring-graphql repository under the `samples` directory.

### Conference talks and videos

Spring I/O 2024 featured "GraphQL Java and Spring: The Latest Features" covering GraphQL Java 22, Spring for GraphQL 1.3, defer/stream, and the DGS integration. Netflix's DGS video series at netflix.github.io/dgs/videos includes framework introductions, federation walkthroughs, and the DGS/Spring GraphQL integration discussion with Josh Long. Dan Vega (Spring Developer Advocate) publishes regular Spring for GraphQL tutorials on YouTube at danvega.dev. GraphQL Conf 2024 (Linux Foundation) featured the Composite Schema Specification keynote and distributed GraphQL talks.

### Community

The official GraphQL Discord (discord.graphql.org) and Reactiflux Discord (#graphql channel, 230K+ members) are the most active communities. The #graphql-kotlin channel on kotlinlang.slack.com serves the Expedia graphql-kotlin community. Apollo's community forum (community.apollographql.com) covers federation and router questions. On Stack Overflow, use tags `spring-graphql`, `netflix-dgs`, and `graphql-java`.

---

## Timeline summary and calibration

| Phase | Weeks | Focus | Milestone |
|-------|-------|-------|-----------|
| 1: Foundations | 1–3 | GraphQL concepts, Spring for GraphQL, DGS setup, codegen | Book catalog API with both annotation models |
| 2: Intermediate | 4–7 | DataLoaders, pagination, security, errors, REST migration | E-commerce API with hybrid REST/GraphQL |
| 3: Advanced | 8–12 | Federation, subscriptions, performance, schema evolution | Federated microservices with gateway |
| 4: Production | 13–16 | Observability, testing pyramid, CI/CD, EKS deployment | Production-hardened federated API on Kubernetes |

This timeline assumes 10–15 hours per week of focused study and hands-on coding. The phases are front-loaded with concepts and increasingly weighted toward hands-on engineering. Each milestone project builds on the previous one, so you accumulate a single evolving codebase that grows from a simple API to a production-grade federated system. Adjust the pace to your schedule — the phase boundaries matter more than exact week counts.