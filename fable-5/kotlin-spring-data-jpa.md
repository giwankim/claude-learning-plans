---
title: "Spring Data JPA with Kotlin (mid-2026): A Senior Engineer's Guide + Annotated Resource List"
category: "Spring & Spring Boot"
description: "A mid-2026 guide and annotated resource list for Spring Data JPA on the Kotlin 2.2 / Spring Boot 4.x / Hibernate ORM 7.x stack: plain non-data classes for entities with kotlin('plugin.jpa') + an allOpen block on the jakarta.persistence annotations and -Xannotation-default-target=param-property, LINE's Kotlin JDSL as the Kotlin-first dynamic-query default (Querydsl surviving only via the OpenFeign KSP fork, jOOQ as the SQL-first complement, Jakarta Data still Kotlin-immature), why value classes as JPA IDs remain won't-fix (spring-data-jpa #2840), virtual threads over coroutines for blocking JPA, MySQL/Aurora specifics, and Testcontainers-based testing — closing with a team best-practices outline/review checklist and a six-tier annotated resource list including Korean-language sources."
---

# Spring Data JPA with Kotlin (mid‑2026): A Senior Engineer's Guide + Annotated Resource List

## TL;DR
- **Use plain (non‑data) Kotlin classes for entities**, apply `kotlin("plugin.jpa")` + `kotlin("plugin.spring")` with an `allOpen` block listing the **jakarta.persistence** annotations, add `-Xannotation-default-target=param-property` for Kotlin 2.2, and test against **real MySQL via Testcontainers** — this is the current consensus for Spring Boot 4.x / Hibernate ORM 7.x / Kotlin 2.2.
- **For dynamic queries in 2026, LINE's Kotlin JDSL is the Kotlin-first default** (no metamodel/kapt; v3.8.x supports Spring Boot 4, with 3.9.0 in the docs); Querydsl survives only via the community OpenFeign fork (KSP-based); jOOQ remains the SQL-first complement; Jakarta Data (Hibernate Data Repositories 7) is production-real for Java but Kotlin ergonomics are immature.
- **Kotlin value classes as JPA IDs still don't work** (spring-data-jpa #2840, closed won't-fix); prefer virtual threads over coroutines for blocking JPA; and drop legacy `javax.*` allOpen config — that advice is now outdated.

## Key Findings

**Version landscape (verified mid‑2026).** Spring Boot 4.0.0 GA was released on 20 November 2025 — Phil Webb's announcement reads: *"I'm extremely happy to announce that Spring Boot 4.0.0 has been released and is now available from Maven Central"* — built on Spring Framework 7.0 (GA 13 November 2025). Spring Boot 4.1.0 followed on **10 June 2026**, built on Spring Framework 7.0.8 and adding gRPC auto‑configuration and **Kotlin 2.3 support** (with Kotlin Serialization 1.11). The stack pulls in Jakarta EE 11 (Servlet 6.1, JPA 3.2, Bean Validation 3.1), Hibernate ORM 7.1/7.2 (implementing Jakarta Persistence 3.2), Jackson 3, and a Kotlin 2.2 baseline. Java 17 remains the floor — Spring co‑lead Juergen Hoeller framed it as *"the current industry consensus is clearly around a Java 17 baseline"* — while Java 21/25 are recommended and Java 25 gets first‑class support. Spring's roadmap keeps a Kotlin 2.2 *baseline* while riding newer compilers (Boot 4.1 = Kotlin 2.3, Boot 4.2 = Kotlin 2.4). This means most "Kotlin + JPA" articles written before late 2025 are subtly outdated on three axes: the `javax.*`→`jakarta.*` namespace, pre‑2.2 annotation use‑site behavior, and JSR‑305→JSpecify null-safety.

**The single most important entity rule is unchanged but reinforced:** don't use `data class` for JPA entities. Generated `equals()/hashCode()` include mutable/lazy fields and the id, breaking `HashSet` membership across the persist boundary and risking `LazyInitializationException` and `StackOverflowError` on bidirectional `toString()`. Use plain classes with proxy‑safe `equals/hashCode`.

## Details

### 1. Build & compiler setup

The canonical Gradle Kotlin DSL setup for Boot 4.x:

```kotlin
plugins {
    kotlin("jvm") version "2.2.20"
    kotlin("plugin.spring") version "2.2.20"   // all-open wrapper
    kotlin("plugin.jpa") version "2.2.20"      // no-arg wrapper
    id("org.springframework.boot") version "4.0.0"
    id("io.spring.dependency-management") version "1.1.6"
}

allOpen {
    annotation("jakarta.persistence.Entity")
    annotation("jakarta.persistence.MappedSuperclass")
    annotation("jakarta.persistence.Embeddable")
}

kotlin {
    compilerOptions {
        freeCompilerArgs.add("-Xannotation-default-target=param-property")
    }
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.jetbrains.kotlin:kotlin-reflect")   // required by Spring
    // ...
}
```

- **`kotlin("plugin.jpa")` (no‑arg)** generates the synthetic no‑argument constructor Hibernate needs for reflection‑based hydration; without it you get `InstantiationException`. It targets `@Entity`, `@MappedSuperclass`, `@Embeddable`.
- **`kotlin("plugin.spring")` (all‑open)** opens Spring‑annotated classes. **Critically, it does NOT open `@Entity` classes by default** — you must add the explicit `allOpen { annotation("jakarta.persistence.Entity") ... }` block. Kotlin classes are `final` by default, and a final entity silently disables Hibernate's runtime proxying: no proxies → no lazy loading → every `@ManyToOne`/`@OneToOne` becomes eagerly fetched, a major performance regression. Hibernate does *not* throw on a final entity, so this fails silently.
- **The `jakarta.*` (not `javax.*`) namespace is mandatory.** Any pre‑Boot‑3 article showing `annotation("javax.persistence.Entity")` is outdated; Spring Framework 7 removed `javax.*` support entirely.
- **`kotlin-reflect`** must be on the classpath — Spring Data uses it to introspect Kotlin nullability metadata and for parameter‑name discovery.
- **Annotation use‑site targets & Kotlin 2.2 (KT‑73255 / KEEP‑402).** Before 2.2, an annotation on a constructor property with no explicit target landed on the **parameter only** (`param`), so framework annotations that expect the field (`@Column`, Bean Validation `@Email`) were silently dropped — validation ran only at construction, not on hydration/update. Kotlin 2.2 changes the default so an annotation lands on **both `param` and the property/field** when applicable. Spring Boot 4 documentation recommends the `-Xannotation-default-target=param-property` flag to opt into this now and suppress the migration warning. The explicit alternative is to keep writing `@field:`/`@get:` targets. `@all:` is a new (preview) meta‑target that applies to every relevant site.

### 2. Entity class design

**The data‑class debate.** The near‑universal recommendation (JetBrains/Thorben Janssen 2026, JPA Buddy, Spoqa, Woowahan, Vlad Mihalcea) is: **plain class, not `data class`, for entities.** Reasons: (1) `data class` cannot be `open`/`abstract`, so it fights Hibernate proxying; (2) generated `equals/hashCode` use all constructor properties including the id and lazy associations, violating the "equality stable across all state transitions" rule and triggering lazy loads; (3) generated `toString()` walks bidirectional associations → `StackOverflowError` and/or `LazyInitializationException`; (4) `copy()` creates detached clones that confuse the persistence context. **Narrow exception:** a `data class` is defensible only when the id is an *application‑assigned, immutable, eagerly‑available* value set at construction (e.g., a client‑generated UUID) and there are no lazy associations in the primary constructor — then the generated methods are stable. Even then most teams avoid it for consistency.

**Recommended entity skeleton:**

```kotlin
@Entity
@Table(name = "orders")
class Order(
    @Column(nullable = false)
    var customerName: String,

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "customer_id", nullable = false)
    var customer: Customer,
) {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Long? = null

    @OneToMany(mappedBy = "order", cascade = [CascadeType.ALL], orphanRemoval = true)
    private val _items: MutableList<OrderItem> = mutableListOf()
    val items: List<OrderItem> get() = _items.toList()

    fun addItem(item: OrderItem) { _items.add(item); item.order = this }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other == null) return false
        if (this::class != org.hibernate.Hibernate.getClass(other)) return false
        other as Order
        return id != null && id == other.id
    }
    override fun hashCode(): Int = javaClass.hashCode()
    override fun toString(): String = "Order(id=$id, customerName=$customerName)"
}
```

- **Id strategy — nullable `var`/`val id: Long? = null` vs sentinel.** The `Long? = null` pattern is the mainstream choice: null means "not yet persisted," which is exactly what proxy‑safe `equals` needs. A non‑null sentinel (`id: Long = 0`) is what you get by accident with data classes and is a footgun. For application‑assigned keys, a non‑null immutable `val id: UUID` set at construction is preferred.
- **Proxy‑safe `equals/hashCode` (Vlad Mihalcea / JPA Buddy patterns).** Two rules: (a) compare classes with `Hibernate.getClass(other)` (or `instanceof`) — never `this.javaClass != other.javaClass`, because a lazy proxy's runtime class is `Order$HibernateProxy$xxxx` and a naive `getClass()` check returns false for the same row. (b) Use a **constant `hashCode()`** (e.g., `javaClass.hashCode()` or a literal) so the hash never changes when Hibernate assigns the id after `persist()`; JPA Buddy notes Vlad's per‑class constant is more correct than a shared constant because it avoids hash collisions between different entity types with equal ids. Equality is based only on a non‑null id (or an immutable business key when one exists).
- **`toString()` without associations** — include only basic, eagerly‑available fields (id, a name), never `@ManyToOne`/`@OneToMany` fields.
- **`lateinit var` for required to‑one associations** is an idiomatic alternative to a nullable type for a non‑optional `@ManyToOne` that is always set before use — it keeps the Kotlin type non‑null without a bogus default.
- **Bidirectional collection encapsulation** — back the collection with a private `MutableList`, expose a read‑only `List` view, and mutate only through helper methods that keep both sides in sync (as above). This is a common Woowahan/Spoqa pattern.
- **`@MappedSuperclass` base classes + Spring Data auditing** — put `createdAt`/`updatedAt`/`createdBy` on an `@MappedSuperclass` `abstract class` (also listed in `allOpen`) with `@EntityListeners(AuditingEntityListener::class)` and `@CreatedDate`/`@LastModifiedDate`; enable `@EnableJpaAuditing`.

### 3. Null‑safety

- **Align three layers:** the Kotlin type (`String` vs `String?`), the JPA mapping (`@Column(nullable = false)`), and the actual DDL. Keep them consistent; Flyway‑managed DDL should be the source of truth and `ddl-auto=validate` enforces the match at boot.
- **The hydration gotcha:** Hibernate populates fields via reflection, which **bypasses Kotlin's null checks**. A column that is NULL in the database can be injected into a non‑null Kotlin property, and the failure surfaces later as a confusing `NullPointerException` on access rather than at load. So a non‑null Kotlin type is *not* a guarantee — the DB constraint must actually enforce non‑null.
- **Nullable repository return types.** Spring Data supports Kotlin nullability: declare `fun findByEmail(email: String): User?` to allow null, or a non‑null return type to force a thrown `EmptyResultDataAccessException` on empty results. Use `findByIdOrNull(id)` (the Kotlin extension on `CrudRepository`, added in Spring Data Commons 2.1.4 / Spring Boot 2.1.2) instead of the Java `Optional<T>`‑returning `findById`. For `JpaSpecificationExecutor`, no such extension exists — teams commonly write their own `findOne`‑wrapping extension.
- **JSpecify in Spring Boot 4.** Spring Framework 7 migrated the whole portfolio from JSR‑305 to JSpecify annotations, which (unlike JSR‑305) express nullability of generic type arguments and array elements and are **automatically translated to Kotlin nullability**. Net effect: after upgrading you should see no unsafe platform types from Spring/Reactor/Micrometer APIs — just proper Kotlin nullable/non‑null types. This can require small refactors where a return type's nullability changed. Kotlin 2.1+ enforces strict handling of `org.jspecify.annotations`.

### 4. Repositories & query strategies

- **Derived queries** work identically to Java (`findByCustomerName`, `findByStatusAndCreatedAtAfter`).
- **`@Query` with triple‑quoted strings** is the clean Kotlin way to embed multi‑line JPQL: `@Query("""select o from Order o where o.status = :status order by o.createdAt desc""")`.
- **DTO projections are where data classes belong.** Interface projections and, especially, **constructor (class‑based) projections into Kotlin `data class`es** are idiomatic and safe (they're read‑only, detached, no proxies). A JPQL `select new com.acme.PersonWithCompany(p.firstName, p.lastName, c.name)` or a matching‑field `data class` maps cleanly.
- **Specifications / Criteria API** work in Kotlin but are verbose; note the Hibernate 7 tightening: addressing subtype attributes via Criteria now requires an explicit `cb.treat(...)` downcast.

**Dynamic‑query DSL landscape in 2026 (decision guide):**

| Option | 2026 status | When to use |
|---|---|---|
| **Kotlin JDSL (LINE/LY Corp)** | Actively maintained; latest 3.8.x (3.8.1 released 8 Apr 2026; 3.9.0 referenced in docs); no metamodel, no kapt/KSP; `spring-data-jpa-support` module; added `spring-data-jpa-boot4-support` for Spring Boot 4 / Spring Data JPA 4.0 | **Default Kotlin‑first choice** for type‑safe dynamic JPQL |
| **Querydsl (original)** | Effectively stalled; kapt‑only, kapt in maintenance mode and doesn't support Kotlin 2.0+ language version | Avoid for new Kotlin projects |
| **OpenFeign Querydsl fork** | The de‑facto maintained Querydsl; v6.x/7.x; added **KSP** codegen (`querydsl-ksp-codegen`), fixed CVE‑2024‑49203 | Migrating existing Querydsl codebases wanting minimal change |
| **jOOQ** | Mature; SQL‑first, typesafe, own codegen | Complex/reporting SQL, DB‑centric teams; complement to JPA |
| **Jakarta Data / Hibernate Data Repositories 7** | Real (Hibernate Processor generates impls over `StatelessSession`); reactive support in 7.x | Java‑centric, standards‑based; Kotlin ergonomics still immature |

Kotlin JDSL's key selling point (per LINE docs and the Spoqa migration writeup): it uses `KProperty` names (registered as constants at compile time, so no reflection cost and IDE‑refactor‑safe) instead of a generated metamodel, eliminating the kapt build step that motivated many teams to leave Querydsl. The Boot 4 module is confirmed by kotlin‑jdsl issue #997: *"spring-data-jpa-boot4-support: Assist to execute the query with Spring Data JPA (for Spring Boot 4)."*

**Korean‑engineering signal:** Spoqa migrated Querydsl→Kotlin JDSL (May 2024) citing kapt maintenance mode and Querydsl's slow release cadence; SKT and multiple velog authors document the `open`/kapt friction of Querydsl in Kotlin. This is a genuine, well‑documented industry trend in the Korean Spring community.

### 5. Kotlin value classes (`@JvmInline`) with JPA

**Current recommended stance: do not use `@JvmInline value class` as a JPA entity property type or repository ID type; use the underlying type and convert at the boundary.**

- **As a repository ID type — broken (spring‑data‑jpa issue #2840).** The issue (opened Mar 2023) is **CLOSED as won't‑fix** and was **not** resolved in Spring Data 2025.1 / Spring Boot 4.x / Spring Data JPA 4.0. Symptom: `save()` **succeeds** but `findById(ProjectId(...))` **fails** with the verbatim error *"Provided id of the wrong type for class com.mango.persistence.entity.ProjectJpa. Expected: class java.util.UUID, got class com.mango.business.model.value.ProjectId."* Root cause (per maintainer Mark Paluch): Kotlin inlines the value class to its underlying type (UUID) in the compiled entity, but the repository generic signature keeps the wrapper type, so the declared vs actual id type mismatch. His recommended workaround: declare `JpaRepository<ProjectJpa, UUID>` (underlying type), not the value class. His verdict: *"There's not much we can do here. Kotlin aims to provide a lot of value at the code frontend at the price of compatibility between components."*
- **As an entity property type — not first‑class in Hibernate.** Hibernate has no built‑in understanding of Kotlin value classes; you hit coercion errors (e.g., `CoercionException: Cannot coerce value 'UserId(value=1)' to Long`). `AttributeConverter`/`@Convert` is unreliable for value classes (community reports of `JpaSystemException`/`Could not convert`). Options that partially work: map the underlying type directly, or a Hibernate `UserType`/`@Type`.
- **Kotlin JDSL & Jackson caveats:** Kotlin JDSL requires unboxing the value class before passing to the `EntityManager`; Jackson also needs care serializing inline classes.
- **Note the contrast with Spring Data JDBC**, where Kotlin value classes map cleanly with `@JvmInline` and no boilerplate — a reason some teams prefer Spring Data JDBC when they want value‑class domain modeling.
- **Forward signal (not yet shipped):** Sébastien Deleuze's Dec 2025 post explicitly lists *"Better efficiency and performance when using Kotlin inline value classes"* among his (not‑yet‑finalized) 2026 Spring roadmap exploration areas — so treat this as an evolving space, not a solved one.

### 6. Transactions, lazy loading, concurrency

- **`@Transactional` self‑invocation** — a `@Transactional` method called from another method of the *same* bean bypasses the proxy and the transaction never starts. Same rule as Java; extract to another bean or use `TransactionTemplate`.
- **Open‑session‑in‑view (OSIV)** — Spring enables OSIV by default; the mainstream recommendation is to **disable it** (`spring.jpa.open-in-view=false`) and fetch what you need inside the transaction (join fetch / entity graphs), so lazy access doesn't leak into the view layer and hold connections.
- **N+1 / fetch strategies** — default all associations to `LAZY` (Kotlin's final‑by‑default already forces you to configure proxying; if you slipped and left entities final, `@ManyToOne` becomes eager — a hidden N+1 source). Solve N+1 with `join fetch`, `@EntityGraph`, or batch fetching.
- **Coroutines vs blocking JPA — they don't mix.** JPA/Hibernate ties the session and JDBC connection to a thread (ThreadLocal). A `suspend` function can resume on a *different* thread, breaking transaction/connection affinity — leading to `TransactionRequiredException`, connection leaks, or **deadlocks** when the coroutine pool and connection pool interact (documented in spring-data-jpa #3598 and the Micronaut Data deadlock issue). JPA has no reactive/coroutine repository support (`Flow` returns fail: "Reactive Repositories are not supported by JPA"). The bridging pattern is to wrap blocking calls in `withContext(Dispatchers.IO)` at the edges and keep the entire `@Transactional` unit on one thread — but this is "tedious and error‑prone" (the words of the Spring Data issue reporter).
- **Virtual threads are the better answer for blocking JPA.** Set `spring.threads.virtual.enabled=true` (Spring Boot 3.2+; requires Java 21+). Each request runs on its own virtual thread; blocking JDBC is fine because the carrier unmounts. **Pinning caveat:** on Java 21–23, `synchronized` blocks pin the carrier (watch `jdk.VirtualThreadPinned` via JFR); older MySQL Connector/J and some libraries used `synchronized`. **JDK 24 (JEP 491)** — whose stated goal is to *"eliminate nearly all cases of virtual threads being pinned to platform threads, which severely restricts the number of virtual threads available to handle an application's workload"* (only native/FFM calls remain a pin case) — makes virtual threads much safer for JPA workloads, a strong reason to run Boot 4 on Java 24/25.
- **Optimistic locking** — add `@Version` (a `var version: Long? = null` or `Int`) for concurrent‑update safety; Hibernate throws `OptimisticLockException` on stale writes.

### 7. MySQL / Aurora specifics

- **`GenerationType.IDENTITY` disables JDBC batch inserts.** With MySQL's auto‑increment, Hibernate must fire each `INSERT` immediately to obtain the generated key, so it cannot batch. MySQL has no `SEQUENCE`, so the classic `SEQUENCE` batching path is unavailable. Options: accept per‑row inserts, use client‑generated keys (below), or a `@SQLInsert`/pooled‑table workaround (Vlad Mihalcea documents these).
- **Client‑generated UUIDv7 keys** are the modern high‑throughput pattern: assign a time‑ordered UUIDv7 at construction so (a) inserts can batch (no DB round‑trip for the key), (b) equals/hashCode get a stable immutable key, and (c) UUIDv7's time‑ordering avoids the index fragmentation of random UUIDv4 on a clustered primary key. Store as `BINARY(16)` for space/index efficiency.
- **`rewriteBatchedStatements=true`** in the JDBC URL is essential — without it, even when Hibernate "batches," the MySQL driver still sends statements one‑by‑one; with it the driver rewrites them into a single multi‑row `INSERT`. This works for server‑side prepared statements as of **MySQL Connector/J 8.0.30** (2022‑07‑26), whose release notes state: *"The description for the connection property rewriteBatchedStatements has been corrected, removing the limitation that server-sided prepared statements could not take advantage of the rewrite option. (Bug #34022110)"* Pair with `hibernate.jdbc.batch_size`, `order_inserts`, `order_updates`.
- **Test against real MySQL via Testcontainers, not H2.** H2 compatibility modes diverge from MySQL (functions, DDL, SQL dialect); bugs slip through H2 tests. Use a `MySQLContainer` matching your Aurora MySQL major version.
- **Flyway + `ddl-auto=validate`** — never let Hibernate manage production schema. Flyway owns migrations; `spring.jpa.hibernate.ddl-auto=validate` fails fast at boot if entities and schema drift.

### 8. Testing

- **`@DataJpaTest` + Testcontainers `@ServiceConnection`.** The modern setup (Spring Boot 3.1+): a `@ServiceConnection`‑annotated `MySQLContainer` auto‑wires the datasource — no `@DynamicPropertySource` boilerplate. Add `@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)` so Boot doesn't swap in an embedded DB. In Kotlin the container is a `companion object` `@JvmStatic` field (or a `@TestConfiguration` `@Bean`). Note the known quirk: `@ServiceConnection` on a `@Bean` needs the container type to be inferable; a `GenericContainer` needs an explicit `name`.
- **Podman note:** Testcontainers works with Podman by pointing `DOCKER_HOST` at the Podman socket and setting `TESTCONTAINERS_RYUK_DISABLED` or configuring Ryuk for rootless Podman — relevant since the user runs Podman.
- **`TestEntityManager` flush/clear discipline** — after a write, call `flush()` then `clear()` to force SQL and detach the persistence context, so the subsequent read hits the DB (not the first‑level cache) and truly exercises the mapping.
- **Kotlin fixture functions with default arguments** — write test‑data builders as top‑level functions with default parameters (`fun order(customerName: String = "test", items: List<OrderItem> = emptyList()) = Order(...)`), a concise Kotlin alternative to Java builder classes.
- **Constructor injection in JUnit 5 tests** — JUnit 5 (JUnit 6 in Boot 4) instantiates the test class once and supports constructor injection, which pairs well with Kotlin's non‑null `val` dependencies; `@BeforeAll`/`@AfterAll` can be non‑static.

## Recommendations

**Stage 1 — Get the foundation current (do first).**
1. Set the build: `plugin.jpa` + `plugin.spring`, `allOpen` block with the three `jakarta.persistence.*` annotations, `kotlin-reflect`, and `-Xannotation-default-target=param-property`. Grep the codebase for `javax.persistence` and delete it.
2. Convert any `data class` entities to plain classes with proxy‑safe `equals` (`Hibernate.getClass`), constant `hashCode`, association‑free `toString`, nullable `Long? = null` id.
3. Set `spring.jpa.open-in-view=false` and `spring.jpa.hibernate.ddl-auto=validate`; put schema under Flyway.

**Stage 2 — Data access & performance.**
4. Default associations to `LAZY`; kill N+1 with `@EntityGraph`/join fetch. Adopt `findByIdOrNull` and nullable return types.
5. For dynamic queries, **adopt Kotlin JDSL** (`3.8.x`/`3.9.0`, `spring-data-jpa-boot4-support`) for new code; if you have legacy Querydsl, migrate to the **OpenFeign fork with KSP** rather than staying on kapt.
6. On MySQL/Aurora: put `rewriteBatchedStatements=true` in the URL, set batch size + ordered inserts, and move to **client‑generated UUIDv7** `BINARY(16)` keys where insert throughput matters.

**Stage 3 — Concurrency model.**
7. Prefer **virtual threads** (`spring.threads.virtual.enabled=true`) on **Java 24/25** over coroutines for blocking JPA. If you must call JPA from coroutines, wrap in `withContext(Dispatchers.IO)` and keep each transaction thread‑confined. Add `@Version` where concurrent updates occur.

**Stage 4 — Testing & guardrails.**
8. Replace H2 with **Testcontainers MySQL + `@ServiceConnection`** in `@DataJpaTest`; enforce `flush()/clear()` discipline; build Kotlin fixture functions.

**Benchmarks that change these calls:** If JFR shows frequent `jdk.VirtualThreadPinned` events you cannot fix (pinning library on Java <24), fall back to a bounded platform‑thread pool instead of virtual threads. If Kotlin value‑class support lands in a future Spring Data (watch #2840‑adjacent work and Deleuze's roadmap), revisit the "avoid value‑class IDs" rule. If Jakarta Data's Kotlin ergonomics mature, reconsider it against Kotlin JDSL.

## Suggested Outline + Review Checklist (for your team's own best‑practices guide)

**Suggested outline to adapt:**
1. *Versions & build baseline* — pinned Boot/Framework/Hibernate/Kotlin versions; the plugin + `allOpen` + compiler‑flag block as a copy‑paste snippet.
2. *Entity conventions* — plain‑class rule, id strategy, the mandated `equals/hashCode/toString`, association encapsulation, auditing base class.
3. *Null‑safety contract* — the three‑layer alignment rule and the hydration caveat.
4. *Repository & query conventions* — derived vs `@Query` vs DTO projections; the sanctioned dynamic‑DSL (Kotlin JDSL) and forbidden ones (raw Querydsl/kapt).
5. *Concurrency policy* — virtual threads on/off decision, coroutine+JPA prohibition, `@Version` policy.
6. *Persistence performance* — batching, key strategy, OSIV off, fetch discipline.
7. *Testing standard* — Testcontainers+Podman setup, `@DataJpaTest` template, flush/clear rule, fixtures.

**Review checklist (PR gate):**
- [ ] No `data class` on `@Entity`; entity is a plain class and appears (transitively) in `allOpen`.
- [ ] `equals` uses `Hibernate.getClass`/`instanceof`; `hashCode` is constant; `toString` excludes associations.
- [ ] Id is `Long? = null` (DB‑generated) or immutable `val` (app‑assigned); no `0` sentinel.
- [ ] Kotlin type nullability matches `@Column(nullable=…)` and the Flyway DDL.
- [ ] No `javax.persistence` imports; use‑site targets explicit or the param‑property flag set.
- [ ] Associations are `LAZY`; N+1 addressed with `@EntityGraph`/join fetch.
- [ ] No `@JvmInline value class` as an `@Id`/repository ID type.
- [ ] No JPA calls from `suspend` functions without a confined `Dispatchers.IO` + single‑thread transaction; `@Version` present where needed.
- [ ] `open-in-view=false`, `ddl-auto=validate`, Flyway migration added.
- [ ] Tests use Testcontainers MySQL (not H2) with `@ServiceConnection`; flush/clear discipline observed.

## Annotated Resource List

### Tier 1 — Official docs (authoritative, current)
- **Spring Data JPA — Kotlin support** — docs.spring.io/spring-data/jpa/reference/data-commons/kotlin.html — the canonical reference for nullable returns, coroutines, `findByIdOrNull`. *Fresh, versioned with Spring Data 2025.1.*
- **Null Handling of Repository Methods :: Spring Data JPA** — docs.spring.io/spring-data/jpa/reference/repositories/null-handling.html — exact rules for `EmptyResultDataAccessException`, `@Nullable`, Kotlin nullability + `kotlin-reflect`. *Current.*
- **Spring Boot — Kotlin support** — docs.spring.io/spring-boot/reference/features/kotlin.html — states the `-Xannotation-default-target=param-property` recommendation, `kotlin-spring`/`kotlin-reflect` requirements, value‑class limitations, JUnit 6 default. *Current (Boot 4).*
- **Spring Framework — Kotlin & Coroutines** — docs.spring.io/spring-framework/reference/languages/kotlin/coroutines.html — coroutine scope, `TransactionalOperator.executeAndAwait`. *Current (Framework 7).*
- **Kotlin no‑arg & all‑open plugin docs** — kotlinlang.org (kotlin-jpa / all-open) — why/how the compiler plugins work.
- **What's new in Kotlin 2.2** — kotlinlang.org/docs/whatsnew22.html — annotation defaulting rules, `@all:`, the two `-Xannotation-default-target` flags. *Primary source for the 2.2 behavior change.*
- **Hibernate ORM 7.0 Migration Guide** — docs.hibernate.org/orm/7.0/migration-guide/ — Jakarta Persistence 3.2 disruption, stricter annotation validation, `save`→`persist`, cascade=PERSIST removal, Java 17 baseline. *Essential for the "what broke" list.*
- **Hibernate Data Repositories (Jakarta Data impl)** — hibernate.org/repositories/ and docs.hibernate.org/orm/7.0/repositories/html_single/ — how Jakarta Data works on `StatelessSession`. *Current, 7.x.*
- **Spring Boot 4.0 Release Notes & Migration Guide** — github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes (+ Migration Guide) — modularization, Jackson 3, JSpecify, starter renames. *Authoritative.*
- **Spring Framework 7.0 Release Notes** — github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes — Jakarta EE 11, JSpecify, Hibernate ORM 7.1/7.2 as JPA provider, `orm.jpa.hibernate` package move. *Authoritative.*

### Tier 2 — Authoritative blogs/articles
- **Sébastien Deleuze, "Next level Kotlin support in Spring Boot 4"** — spring.io/blog/2025/12/18/... — the definitive statement of the Kotlin 2.2 baseline rationale, JSpecify auto‑translation, version roadmap, and value‑class future work. *Dec 2025, must‑read.*
- **JetBrains, "Using Spring Data JPA with Kotlin"** (Thorben Janssen co‑author) — blog.jetbrains.com/idea/2026/03/... — the current getting‑started with the exact `allOpen`/plugin config and DTO projection guidance. *Mar 2026.*
- **JetBrains, "How to Avoid Common Pitfalls With JPA and Kotlin"** — blog.jetbrains.com/idea/2026/01/... — entity requirements, data‑class/`val` warnings, IntelliJ 2026.1 inspections. *Jan 2026.*
- **JetBrains, "Spring Boot 4: Leaner, Safer Apps and a New Kotlin Baseline"** — blog.jetbrains.com/idea/2025/11/spring-boot-4/ — Kotlin‑2.2‑baseline framing, JSpecify examples. *Nov 2025.*
- **JetBrains, "Improved Annotation Handling in Kotlin 2.2"** — blog.jetbrains.com/idea/2025/09/... — the clearest explanation of KT‑73255 and the flags. *Sep 2025.*
- **JetBrains, "Using Spring Data JDBC with Kotlin"** — blog.jetbrains.com/idea/2026/04/... — the value‑class/data‑class contrast that explains why JDBC handles value classes cleanly where JPA does not. *Apr 2026.*
- **JPA Buddy, "Best Practices and Common Pitfalls of Using JPA (Hibernate) with Kotlin"** — jpa-buddy.com/blog/best-practices-and-common-pitfalls/ — the checklist (all‑open, no‑arg, equals/hashCode, when data classes are OK) + the `jpa-buddy/kotlin-entities` sample repo. *Evergreen, still accurate.*
- **JPA Buddy, "(Hopefully) the final article about equals and hashCode…"** — jpa-buddy.com/blog/hopefully-the-final-article-... — compares Vlad/Thorben/SO implementations; explains per‑class constant hashCode and the `@MappedSuperclass` subtlety. *Deep, current.*
- **Vlad Mihalcea** — vladmihalcea.com — "The best way to implement equals, hashCode, and toString with JPA and Hibernate," "…using the JPA entity identifier," "MySQL rewriteBatchedStatements," "How to batch INSERT with MySQL and Hibernate." *The authoritative primary source for entity identity and MySQL batching.*
- **Thorben Janssen** — thorben-janssen.com — Jakarta Data getting‑started and repository articles; long‑running Hibernate authority.
- **Julian Paul, "Hibernate 7 Migration"** — julianpaul.dev/en/blogs/hibernate-7-migration/ — practical "what silently breaks" list (cascade=PERSIST, `isXxx()` getters, `hibernate-scan-jandex`). *Good practitioner complement to the official guide.*

### Tier 3 — Query‑DSL resources
- **line/kotlin-jdsl** — github.com/line/kotlin-jdsl (+ kotlin-jdsl.gitbook.io/docs) — the library, releases (3.8.1, Apr 2026; 3.9.0 in docs), `spring-data-jpa-support` / `spring-data-jpa-boot4-support`, the "no metamodel" FAQ. *Actively maintained.*
- **kotlin-jdsl issue #997 "Support Spring Data JPA 4.0 for Spring Boot 4"** — github.com/line/kotlin-jdsl/issues/997 — documents the Boot‑4 adaptation and new modules. *Jan 2026.*
- **OpenFeign/querydsl** — github.com/OpenFeign/querydsl (releases) — the maintained Querydsl fork with KSP codegen and CVE‑2024‑49203 fix. *The path for legacy Querydsl.*
- **querydsl/querydsl #3284 "[Kotlin] Migrate kapt to ksp"** — closed `wontfix` on the original repo — evidence the original project stalled.

### Tier 4 — Korean‑language sources
- **Spoqa 기술 블로그, "Querydsl에서 Kotlin JDSL 으로"** — spoqa.github.io/2024/05/03/transfer-jdsl.html — the definitive Korean migration writeup: why (kapt maintenance mode, slow Querydsl cadence), how (task‑listing, base‑code approach), trade‑offs. *May 2024, high value.*
- **Spoqa 기술 블로그, "스포카에서 Kotlin으로 JPA Entity를 정의하는 방법"** — spoqa.github.io/2022/08/16/kotlin-jpa-entity.html — the best Korean treatment of entity encapsulation, why not data class, immutability vs entity lifecycle. *Aug 2022, still accurate.*
- **우아한형제들(Woowahan), "코틀린에서 하이버네이트를 사용할 수 있을까?"** — techblog.woowahan.com/2675/ — foundational Korean article: all‑open, no‑arg, data‑class lazy‑loading limits, `kassava` for equals/hashCode/toString. *Widely cited baseline (uses `javax.*`, dated config but sound reasoning).*
- **OpenFeign QueryDSL 마이그레이션 총정리** — medium.com/@rlaeorua369/... — Korean deep dive on the OpenFeign fork, KSP, CVE‑2024‑49203. *Recent.*
- **"Kapt 없는 QueryDSL 마이그레이션 (KSP + OpenFeign QueryDSL)"** — velog.io/@sumurf/... — hands‑on KSP + OpenFeign Querydsl migration with the jakarta/javax pitfall. *Practical.*
- **SKT Enterprise, "[Kotlin] QueryDSL JPA 프로젝트에서 TroubleShooting하기"** — sktenterprise.com/bizInsight/blogDetail/dev/9511 — the `open` keyword + `JPAQueryFactory` NPE gotcha. *Real‑world.*
- **VCNC, "Kotlin + Spring Data JPA"** — speakerdeck.com/vcnc/kotlin-plus-spring-data-jpa — Korean slide deck covering nullability, `findByIdOrNull`, lazy proxies. *Concise reference.*

### Tier 5 — Talks / videos
- **"Next level Kotlin support in Spring Boot 4"** — Sébastien Deleuze — Spring I/O 2025 (youtube watch?v=Ip1IFdlNPIY) and KotlinConf 2025. Slides on 2025.springio.net. *The single best talk on the current state.*
- **KotlinConf 2025 / Spring I/O 2025** sessions — 2025.kotlinconf.com and 2025.springio.net — broader Kotlin server‑side track.

### Tier 6 — Community signal / debates
- **spring-data-jpa #2840** (Kotlin value‑class ID) — CLOSED won't‑fix; the canonical evidence value classes don't work as IDs.
- **spring-data-jpa #3598** (`suspend` support in JpaRepository) and **micronaut-data #3246** (coroutine `@Transactional` deadlock) — the primary sources for "coroutines + JPA transactions don't mix."
- **spring-data-commons #1782** — the `findByIdOrNull` origin.
- **Kotlin Discussions "Value class + spring + JPA @Query"** — discuss.kotlinlang.org/t/24107 — value‑class query breakage.
- **Kotlin Slack #spring / #ksp threads** (slack-chats.kotlinlang.org) — kapt EOL / jpamodelgen pain, virtual‑thread pinning.
- **oshy.tech, "Spring Boot with Kotlin: the good, the awkward…"** — captures the data‑class/immutability debate from a practitioner, with the exact "works, then breaks in three weeks" data‑class failure narrative.

## Caveats
- **Version drift is fast.** Spring Boot 4.1 (Kotlin 2.3) shipped 10 June 2026 and 4.2/Kotlin 2.4 are on the roadmap; re‑verify exact plugin/library versions against Maven Central before pinning. The Kotlin 2.2 *baseline* is stable even as compilers advance.
- **Some cited blog code still shows `javax.*`, Kotlin 1.9, or H2** — treat any pre‑2025 sample's build config as illustrative of *concepts*, not copy‑paste‑ready for Boot 4. This especially affects the Korean posts (2022–2024) whose *reasoning* is excellent but whose `allOpen`/version blocks are dated.
- **Value‑class support is a moving target** — the "avoid" recommendation reflects mid‑2026 reality (issue #2840 closed, Hibernate coercion errors), but Spring has flagged inline‑value‑class efficiency as active 2026 work; recheck before building domain modeling around it.
- **Virtual‑thread pinning depends on your JDK and driver versions** — the JDK 24 fix (JEP 491) only helps if you're actually on Java 24+; on Java 21–23 audit `synchronized` usage in the MySQL driver and other libs via JFR before enabling virtual threads broadly.
- **Jakarta Data Kotlin maturity** — Hibernate Data Repositories is production‑real for Java, but Kotlin‑specific ergonomics (nullability, `StatelessSession` semantics with Kotlin idioms) are less battle‑tested than Spring Data JPA; pilot before committing.
- I did not independently benchmark the performance claims (batching, virtual threads); they are drawn from vendor docs and reputable practitioners (Vlad Mihalcea, Spring/JetBrains) and should be validated in your Aurora environment.