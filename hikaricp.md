# Mastering HikariCP: a 16-week learning plan for Spring Boot Kotlin developers

**This plan takes you from "using Spring Boot defaults" to production-grade mastery of JDBC connection pooling.** It's organized into six phases, each building on the last, with specific readings, hands-on labs, and milestone deliverables. The plan assumes roughly 6–10 hours per week of study and practice. Every resource listed below has been verified as available and relevant; start with the starred (⭐) items if time is tight in any given week.

---

## Phase 1: Foundations — why connections cost what they cost (Weeks 1–3)

The goal here is to build a mental model of what happens at the network and protocol level when your Kotlin service talks to MySQL or PostgreSQL. Without this foundation, tuning HikariCP parameters is guesswork.

### Week 1: TCP connections and the real cost of "just connecting"

**Objective:** Understand the full lifecycle of a database connection from TCP handshake through authentication to query execution and teardown.

**Core study:**
- Read Vlad Mihalcea's "The Anatomy of Connection Pooling" (https://vladmihalcea.com/the-anatomy-of-connection-pooling/) — this demonstrates with benchmarks that **creating 1,000 unpooled connections takes orders of magnitude longer** than using a pool. ⭐
- Study the MySQL client/server protocol: a connection involves TCP 3-way handshake → TLS negotiation (50–100ms over TLS) → MySQL handshake packet → authentication exchange → session initialization. Each new connection allocates a server thread (MySQL) or forks an OS process consuming **~10MB RAM** (PostgreSQL).
- Read the "Connection Pooling: Fundamentals, Challenges and Trade-offs" article (https://engineeringatscale.substack.com/p/database-connection-pooling-guide) for an excellent overview of why pooling exists across the industry. ⭐

**Hands-on lab:** Use `tcpdump` or Wireshark to capture the TCP/TLS handshake of a JDBC connection to your local MySQL instance. Measure the time from SYN to first query result. Then write a Kotlin script that opens and closes 100 connections sequentially (no pool) and measure total elapsed time. Compare this against 100 queries through a single pooled HikariDataSource. Record the difference — it's typically **20–50x**.

**Supplementary reading:**
- Baeldung's "A Simple Guide to Connection Pooling in Java" (https://www.baeldung.com/java-connection-pooling) — covers building a naive pool from scratch, which clarifies the core abstraction
- PostgreSQL's process-per-connection model documentation — explains why PostgreSQL's default `max_connections` of **100** is much lower than MySQL's 151

### Week 2: Connection lifecycle and the pool as a bounded buffer

**Objective:** Map the complete lifecycle of a pooled connection — creation, validation, borrowing, return, idle management, eviction, and leak detection.

**Core study:**
- Read HikariCP's README configuration section (https://github.com/brettwooldridge/HikariCP) — focus on understanding what each timeout parameter controls in the lifecycle. ⭐
- Study the connection lifecycle as implemented in HikariCP:
  1. **Creation**: `PoolBase` creates connections asynchronously via `addConnectionExecutor`, wraps each in a `PoolEntry`, and adds it to the `ConcurrentBag`
  2. **Validation on borrow**: If a connection has been idle longer than `aliveBypassWindowMs` (default 500ms), HikariCP calls `isConnectionDead()` — either `Connection.isValid()` (JDBC4, preferred) or `connectionTestQuery` (legacy fallback like `SELECT 1`)
  3. **In-use tracking**: `ProxyConnection` tracks dirty bits (autoCommit, readOnly, isolation level, catalog, schema, networkTimeout) as a bitfield, and maintains a `FastList<Statement>` of open statements
  4. **Return**: On `connection.close()`, HikariCP closes open statements, rolls back uncommitted work if dirty, resets only changed properties (via dirty bit tracking), cancels the leak detection task, and returns the `PoolEntry` to the `ConcurrentBag`
  5. **Idle/eviction**: The `HouseKeeper` thread runs every 30 seconds, retiring connections that exceed `idleTimeout` or `maxLifetime`. HikariCP applies **±2.5% variance** to `maxLifetime` to prevent mass eviction storms
  6. **Keepalive**: The `KeepaliveTask` pings idle connections at `keepaliveTime` intervals (default 2 min) to prevent database/network timeouts
  7. **Leak detection**: `ProxyLeakTask` fires if a connection is held beyond `leakDetectionThreshold`, logging a WARNING with the full stack trace of where the connection was acquired

**Hands-on lab:** Enable HikariCP DEBUG logging (`logging.level.com.zaxxer.hikari=DEBUG`) in a Spring Boot Kotlin app. Watch the log output as you: (a) start the app and see pool fill, (b) execute queries and see borrow/return, (c) let the app sit idle and see housekeeping, (d) set `maxLifetime` to 60 seconds and watch connections rotate. Set `leakDetectionThreshold=5000` and write a controller that holds a connection for 10 seconds — observe the leak warning with stack trace.

### Week 3: Why Spring Boot chose HikariCP — and what came before

**Objective:** Understand how HikariCP compares to C3P0, DBCP2, and Tomcat JDBC pool, and why it became the Spring Boot default in 2.0.

**Core study:**
- Read the Wix Engineering benchmark comparison: "How Does HikariCP Compare to Other Connection Pools?" (https://www.wix.engineering/post/how-does-hikaricp-compare-to-other-connection-pools) ⭐
- Read Brett Wooldridge's jOOQ Tuesday interview (https://blog.jooq.org/jooq-tuesdays-brett-wooldridge-shows-what-it-takes-to-write-the-fastest-java-connection-pool/) — this covers the origin story, design philosophy, and why existing pools were broken. Key quote: **"Really? This is the state of connection pools after 20 years of Java?"** ⭐
- Study the key architectural differences:

| Feature | HikariCP | C3P0 | DBCP2 | Tomcat Pool |
|---------|----------|------|-------|-------------|
| Lock strategy | Lock-free CAS via `ConcurrentBag` | Nested synchronized locks | ReentrantLock | FairBlockingQueue |
| PreparedStatement caching | Delegates to JDBC driver (correct approach) | Pool-level cache (250 stmts × pool_size connections) | Pool-level cache | Pool-level cache |
| Connection return cleanup | Rolls back dirty transactions, resets only changed properties via dirty bits | Inconsistent cleanup | Doesn't auto-close Statements | Doesn't reset isolation level |
| Proxy generation | Javassist bytecode generation at build time | java.lang.reflect.Proxy (runtime) | Runtime reflection | Runtime reflection |
| Codebase size | ~165KB, minimal surface area | Thousands of LOC, complex | Large, configurable | Moderate |

**Supplementary reading:**
- HikariCP's "Pool Analysis" wiki page (https://github.com/brettwooldridge/HikariCP/wiki/Pool-Analysis) — shows spike demand handling where HikariCP creates **85–90% fewer connections** and completes spikes **8–9x faster** than alternatives
- Baeldung's "Introduction to HikariCP" (https://www.baeldung.com/hikaricp)

**Phase 1 milestone:** Write a 1-page internal document explaining to a teammate why connection pooling matters, what the cost of unpooled connections is, and why HikariCP specifically was chosen over alternatives.

---

## Phase 2: HikariCP deep dive — configuration, sizing, and internals (Weeks 4–6)

### Week 4: Every configuration parameter, explained and justified

**Objective:** Develop a working understanding of every HikariCP parameter and how they interact.

**Core study — the parameter map:**

| Parameter | Default | What it controls | Tuning guidance |
|-----------|---------|------------------|-----------------|
| `maximumPoolSize` | 10 | Hard ceiling on idle + in-use connections | Start with the pool sizing formula (Week 5); almost never above 20 for a single service |
| `minimumIdle` | = maximumPoolSize | Floor for idle connections; HikariCP recommends NOT setting this (fixed-size pool) | Only set below max if you have highly variable load AND want to reduce idle DB connections |
| `connectionTimeout` | 30,000ms | Max wait for a connection from pool before throwing `SQLException` | 30s is generous; reduce to 5–10s in latency-sensitive services to fail fast |
| `idleTimeout` | 600,000ms (10min) | How long an idle connection lives before retirement (only when minimumIdle < maximumPoolSize) | Must be ≤ MySQL `wait_timeout` minus a buffer |
| `maxLifetime` | 1,800,000ms (30min) | Absolute maximum lifetime of any connection; HikariCP applies ±2.5% jitter | **Must be several seconds shorter than database `wait_timeout`**; for Aurora, consider 5–10 min to improve failover response |
| `keepaliveTime` | 120,000ms (2min) | Interval for pinging idle connections to prevent server-side timeout | Must be < `maxLifetime`; minimum 30,000ms |
| `validationTimeout` | 5,000ms | Timeout for `isValid()` check on borrow | Must be < `connectionTimeout` |
| `leakDetectionThreshold` | 0 (disabled) | Time before logging a leak warning for unreturned connections | Enable in dev/staging at 30–60s; minimum 2,000ms |
| `connectionTestQuery` | none | Legacy alive-test SQL for pre-JDBC4 drivers | **Don't set this** — modern MySQL Connector/J and PostgreSQL JDBC support `isValid()`, which is faster and more reliable |
| `autoCommit` | true | Default auto-commit mode for connections | Set to `false` when using Hibernate with `provider_disables_autocommit=true` for delayed connection acquisition |

**Hands-on lab:** Create a Kotlin configuration file that explicitly sets every parameter with comments explaining each choice. Deploy it against your MySQL RDS instance and verify the settings are applied by checking HikariCP's JMX MBeans (`spring.datasource.hikari.register-mbeans=true`) via JConsole or VisualVM.

**Reading:**
- HikariCP FAQ (https://github.com/brettwooldridge/HikariCP/wiki/FAQ) — covers the critical `maxLifetime` vs `wait_timeout` coordination ⭐
- HikariCP MySQL Configuration wiki (https://github.com/brettwooldridge/HikariCP/wiki/MySQL-Configuration) — driver-level tuning properties ⭐

### Week 5: Pool sizing — the formula, the math, the counterintuitive truth

**Objective:** Learn why smaller pools outperform larger ones and how to calculate your optimal size.

**Core study:**
- Read HikariCP's "About Pool Sizing" wiki page in full (https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing) — this is the single most important resource in this entire plan. ⭐⭐⭐

The key insights:

**The PostgreSQL formula** (applicable to MySQL too):
```
connections = (core_count × 2) + effective_spindle_count
```
Where `core_count` is physical cores (not HyperThreading virtual cores), and `effective_spindle_count` approaches 0 for fully cached data or SSDs. A **4-core server with SSD yields an optimal pool of ~9–10 connections**.

**The Oracle proof:** Reducing a connection pool from 2,048 to 96 connections decreased response times from ~100ms to ~2ms — a **50x improvement**. More connections means more context switching, more lock contention, more cache-line invalidation.

**The deadlock-avoidance formula** (for applications that hold multiple connections simultaneously):
```
pool_size = Tn × (Cm - 1) + 1
```
Where `Tn` = max concurrent threads and `Cm` = max simultaneous connections per thread.

**Relationship to `max_connections`:** Your total connections across all application instances must fit within the database's `max_connections`. The formula is: `per_pod_pool_size = total_db_connections / (num_pods × num_pools_per_pod)`. For Aurora, leave headroom for monitoring connections, admin access, and RDS internal processes.

**Reading:**
- Vlad Mihalcea's "The Best Way to Determine the Optimal Connection Pool Size" (https://vladmihalcea.com/optimal-connection-pool-size/) — demonstrates empirically that **4 connections can outperform 64** ⭐
- The Oracle Real-World Performance video referenced in the HikariCP wiki

**Hands-on lab:** Calculate the optimal pool size for your production Aurora instance. Find the instance class, determine its vCPU count (divide by 2 for physical cores), apply the formula. Compare this number against your current `maximumPoolSize` setting. If you're running on EKS with N pod replicas, calculate: `per_pod_max = aurora_max_connections / (N × num_datasources) × 0.8` (80% to leave headroom).

### Week 6: HikariCP source code walkthrough — the internals that make it fast

**Objective:** Read and understand the key source classes that implement HikariCP's "zero overhead" design.

**Core study:**
- Read HikariCP's "Down the Rabbit Hole" wiki page (https://github.com/brettwooldridge/HikariCP/wiki/Down-the-Rabbit-Hole) ⭐
- Study these source files on GitHub (https://github.com/brettwooldridge/HikariCP/tree/dev/src/main/java/com/zaxxer/hikari):

**Priority 1 — the performance core:**
- **`ConcurrentBag.java`** (~250 lines): The heart of HikariCP. Uses ThreadLocal caching for previously-used connections (avoiding shared-list contention), `CopyOnWriteArrayList` as fallback, and `SynchronousQueue<T>(true)` for direct handoff from returning threads to waiting threads. State transitions use `compareAndSet()` via `AtomicIntegerFieldUpdater` — completely lock-free. Connection states: `NOT_IN_USE → IN_USE → NOT_IN_USE` (normal), `NOT_IN_USE → RESERVED → REMOVED` (eviction).
- **`FastList.java`** (~80 lines): Replaces `ArrayList<Statement>`. Eliminates range checking on `get()` and scans from tail-to-head on `remove()`, matching JDBC's pattern where the last-opened Statement is first-closed.

**Priority 2 — the pool lifecycle:**
- **`HikariPool.java`**: Manages the `ConcurrentBag`, runs `HouseKeeper` (idle/lifetime eviction), handles `getConnection()` with timeout, triggers async connection creation via `addConnectionExecutor`.
- **`PoolBase.java`**: Connection creation, validation (`isConnectionDead()`), state reset. Tracks dirty bits as a bitfield for efficient reset — only properties that were actually changed get reset on return.
- **`PoolEntry.java`**: Wraps raw `Connection` with state tracking (`lastAccessed`, eviction mark), implements `IConcurrentBagEntry`.

**Priority 3 — the proxy layer:**
- **`ProxyConnection.java`**: Intercepts all JDBC calls. On `close()`: closes statements, rolls back dirty transactions, resets changed properties, cancels leak task, returns to `ConcurrentBag`.
- **`ProxyFactory.java`**: Static factory methods with bodies generated at build time by `JavassistProxyFactory` — eliminates runtime reflection overhead.

**Key micro-optimizations to note:**
- Bytecode output of javac was studied to keep critical paths under the JIT inline threshold
- Inheritance hierarchies were flattened to reduce `invokevirtual` overhead
- Singleton factory pattern was replaced with static methods (`invokestatic`) to eliminate `getstatic` calls and reduce stack frame size

**Hands-on lab:** Clone the HikariCP repository. Set breakpoints in `ConcurrentBag.borrow()` and `ConcurrentBag.requite()`. Run a simple test and step through the ThreadLocal check → shared list scan → SynchronousQueue handoff path. Observe how state transitions happen via CAS operations.

**Phase 2 milestone:** Create a HikariCP configuration cheat sheet for your team that maps each parameter to your production requirements, documents your pool sizing calculation, and explains the key internal mechanisms.

---

## Phase 3: Spring Boot integration and Hibernate connection management (Weeks 7–9)

### Week 7: How Spring Boot auto-configures HikariCP

**Objective:** Understand the auto-configuration chain from classpath detection through property binding to DataSource creation.

**Core study:**
- Read Spring Boot's data access documentation (https://docs.spring.io/spring-boot/reference/data/sql.html) ⭐
- Read the how-to guide on data access (https://docs.spring.io/spring-boot/how-to/data-access.html) ⭐

The auto-configuration chain works as follows: `DataSourceAutoConfiguration` detects `DataSource.class` on the classpath and checks for a connection pool in priority order: **HikariCP → Tomcat Pooling → Commons DBCP2 → Oracle UCP**. Since `spring-boot-starter-data-jpa` transitively includes HikariCP, it's always selected. Properties under `spring.datasource.hikari.*` are bound to `HikariDataSource` via `@ConfigurationProperties`. If you define your own `DataSource` `@Bean`, auto-configuration backs off entirely.

**Programmatic configuration in Kotlin** (the idiomatic pattern):
```kotlin
@Configuration
class DataSourceConfig {
    @Bean
    fun dataSource(): HikariDataSource {
        return HikariDataSource(HikariConfig().apply {
            jdbcUrl = "jdbc:mysql://aurora-writer:3306/mydb"
            username = "app_user"
            password = "secret"
            maximumPoolSize = 10
            isAutoCommit = false
            poolName = "writer-pool"
            addDataSourceProperty("cachePrepStmts", "true")
            addDataSourceProperty("prepStmtCacheSize", "250")
            addDataSourceProperty("prepStmtCacheSqlLimit", "2048")
        })
    }
}
```

**Reading:**
- Baeldung's "Configuring Hikari Connection Pool with Spring Boot" (https://www.baeldung.com/spring-boot-hikari) ⭐
- Spring Boot application properties appendix (https://docs.spring.io/spring-boot/appendix/application-properties/index.html) — search for `spring.datasource.hikari` for the complete property list
- Baeldung's "Configuring DataSource Programmatically" (https://www.baeldung.com/spring-boot-configure-data-source-programmatic)

**Hands-on lab:** In your Kotlin project, switch from `application.yml` configuration to a programmatic `@Bean` using `HikariConfig().apply { }`. Verify via actuator endpoint `/actuator/metrics/hikaricp.connections` that the pool is correctly initialized. Then switch back to YAML — understand both approaches and when each is appropriate (YAML for simple cases, `@Bean` for multi-datasource or conditional logic).

### Week 8: Hibernate's connection acquisition — the hidden performance trap

**Objective:** Master how Hibernate acquires and releases connections, and configure optimal connection handling for your stack.

**Core study:**
- Read Vlad Mihalcea's "Spring Transaction and Connection Management" (https://vladmihalcea.com/spring-transaction-connection-management/) ⭐
- Read "Why You Should Always Use hibernate.connection.provider_disables_autocommit" (https://vladmihalcea.com/why-you-should-always-use-hibernate-connection-provider_disables_autocommit-for-resource-local-jpa-transactions/) ⭐

**The core problem:** When `JpaTransactionManager.begin()` starts a read-write transaction, Hibernate acquires the JDBC connection **eagerly** — before any SQL executes — to check and disable auto-commit mode. This means if your `@Transactional` method does computation or calls external APIs before its first query, it's holding a pooled connection doing nothing.

**The fix:** Set `spring.datasource.hikari.auto-commit=false` AND `spring.jpa.properties.hibernate.connection.provider_disables_autocommit=true`. This tells Hibernate the pool already disabled auto-commit, so **connection acquisition is delayed until the first SQL statement**.

**Critical caveat:** For `@Transactional(readOnly = true)`, Spring's `HibernateJpaDialect.beginTransaction()` forces eager connection acquisition regardless — it needs the connection to set the JDBC read-only flag. This matters for read/write routing (Week 10).

**Connection release modes** (`hibernate.connection.handling_mode`):
- `DELAYED_ACQUISITION_AND_RELEASE_AFTER_TRANSACTION` — connection released on commit/rollback (default for resource-local, correct for most apps)
- `DELAYED_ACQUISITION_AND_RELEASE_AFTER_STATEMENT` — released after each statement (JTA environments)
- `DELAYED_ACQUISITION_AND_HOLD` — held until Session close (dangerous with OSIV)

**Historical bug to know about:** Spring Framework issue SPR-14548 (https://github.com/spring-projects/spring-framework/issues/19116) — upgrading from Hibernate 5.1 to 5.2 silently changed the default release mode from `AFTER_TRANSACTION` to `ON_CLOSE`, causing pool exhaustion in production.

**Reading:**
- "How Does Aggressive Connection Release Work in Hibernate" (https://vladmihalcea.com/hibernate-aggressive-connection-release/)
- "High-Performance Java Persistence" by Vlad Mihalcea — Chapter 9 covers Hibernate connection management in depth

### Week 9: OSIV, @Transactional scope, and connection holding time

**Objective:** Understand how transaction boundaries and OSIV affect how long connections are held — the single biggest determinant of pool pressure.

**Core study:**
- Read Vlad Mihalcea's "The Open Session In View Anti-Pattern" (https://vladmihalcea.com/the-open-session-in-view-anti-pattern/) ⭐
- Read Baeldung's OSIV guide (https://www.baeldung.com/spring-open-session-in-view) ⭐

**OSIV (Open Session In View)** is enabled by default in Spring Boot (`spring.jpa.open-in-view=true`). The `OpenEntityManagerInViewInterceptor` keeps the Hibernate Session open for the **entire HTTP request lifecycle** — from filter invocation through controller execution through JSON serialization. Once any database query executes, the JDBC connection is borrowed from HikariCP and **held until the HTTP response is fully written**. This means if your controller calls an external API after querying the database, the connection sits idle during that entire HTTP call. Under load, this causes pool exhaustion.

**The fix:** Set `spring.jpa.open-in-view=false`. Use explicit `@Transactional` boundaries and eager fetching or DTOs. This is a **non-negotiable production recommendation**.

**@Transactional scope best practices:**
- Push `@Transactional` as close to the data access layer as possible
- Never wrap external API calls, message queue publishes, or heavy computation in `@Transactional`
- Use `@Transactional(readOnly = true)` at the service class level, override with `@Transactional` on write methods
- Remember: the connection is held for the entire duration of the `@Transactional` method

**Hands-on lab:** Enable HikariCP metrics via Micrometer. Create two endpoints: one with OSIV enabled that lazy-loads a collection during JSON serialization after a `Thread.sleep(2000)`, and one with OSIV disabled using a DTO projection. Load test both with 50 concurrent requests and compare `hikaricp.connections.active` and `hikaricp.connections.usage` metrics. The OSIV endpoint will show connections held **2+ seconds longer**.

**Phase 3 milestone:** Apply these three critical settings to your production configuration and measure the before/after impact on connection hold times:
```yaml
spring:
  datasource:
    hikari:
      auto-commit: false
  jpa:
    open-in-view: false
    properties:
      hibernate.connection.provider_disables_autocommit: true
```

---

## Phase 4: Multi-datasource patterns for AWS Aurora (Weeks 10–11)

### Week 10: Read/write routing with AbstractRoutingDataSource

**Objective:** Implement separate HikariCP pools for Aurora writer and reader endpoints with automatic routing based on `@Transactional(readOnly)`.

**Core study:**
- Read Baeldung's "Spring AbstractRoutingDatasource Guide" (https://www.baeldung.com/spring-abstract-routing-data-source) ⭐
- Read Baeldung's "Configure and Use Multiple DataSources" (https://www.baeldung.com/spring-boot-configure-multiple-datasources) ⭐
- Study the Help Scout per-module connection pools Kotlin example (https://github.com/helpscout/connection-pool-per-module) ⭐

**The implementation pattern in Kotlin:**

Step 1 — Define separate pools in YAML:
```yaml
app:
  datasource:
    writer:
      jdbc-url: jdbc:mysql://my-cluster.cluster-xxx.us-east-1.rds.amazonaws.com:3306/mydb
      hikari:
        pool-name: writer-pool
        maximum-pool-size: 10
        auto-commit: false
    reader:
      jdbc-url: jdbc:mysql://my-cluster.cluster-ro-xxx.us-east-1.rds.amazonaws.com:3306/mydb
      hikari:
        pool-name: reader-pool
        maximum-pool-size: 20
        auto-commit: false
        read-only: true
```

Step 2 — Create the routing DataSource:
```kotlin
enum class DataSourceType { WRITER, READER }

class ReadWriteRoutingDataSource : AbstractRoutingDataSource() {
    override fun determineCurrentLookupKey(): DataSourceType {
        return if (TransactionSynchronizationManager
                .isCurrentTransactionReadOnly()) 
            DataSourceType.READER 
        else 
            DataSourceType.WRITER
    }
}
```

Step 3 — **Wrap with `LazyConnectionDataSourceProxy`** — this is the critical detail most tutorials miss. Without it, `AbstractRoutingDataSource` resolves the target DataSource before `@Transactional` sets the readOnly flag, so all queries route to the writer:
```kotlin
@Bean
@Primary
fun dataSource(): DataSource = 
    LazyConnectionDataSourceProxy(routingDataSource())
```

**Pool sizing strategy for writer + replicas:**
- Writer pool: Sized for write workload (typically smaller — writes are fewer but more critical)
- Reader pool: Sized for read workload (typically larger — reads are the majority); connects to the Aurora reader endpoint, which DNS round-robins across replicas
- Both pools combined across all pods must fit within Aurora's `max_connections`

**GitHub examples to study:**
- Replication DataSource Boot (https://github.com/kwon37xi/replication-datasource-boot) — clean `LazyConnectionDataSourceProxy` + `AbstractRoutingDataSource` pattern
- Spring Boot Multi Data Source (https://github.com/ehsaniara/spring-boot-multi-data-source) — HikariCP read/write split with separate EntityManagers

### Week 11: Aurora drivers, failover, and connection pinning

**Objective:** Choose the right JDBC driver for Aurora and configure HikariCP to handle failover gracefully.

**Core study:**
- Read the AWS Advanced JDBC Wrapper documentation (https://github.com/aws/aws-advanced-jdbc-wrapper) ⭐
- Read the AWS blog post introducing the wrapper (https://aws.amazon.com/blogs/database/introducing-the-advanced-jdbc-wrapper-driver-for-amazon-aurora/) ⭐
- Read Aurora PostgreSQL fast failover best practices (https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.BestPractices.FastFailover.html)

**Driver comparison and recommendation:**

| Driver | Aurora failover time | Read/write splitting | IAM auth | Status |
|--------|---------------------|---------------------|----------|--------|
| **AWS Advanced JDBC Wrapper** | ~6 seconds (bypasses DNS) | Built-in plugin | Yes | ✅ Active, recommended |
| MariaDB Connector/J | Was Aurora-aware | N/A | No | ❌ Dropped Aurora support in v3.0.3 |
| MySQL Connector/J (community) | ~30+ seconds (DNS propagation) | No | No | ⚠️ Works but slow failover |

The AWS wrapper uses a **plugin architecture** with default plugins for `auroraConnectionTracker`, `failover`, and `efm` (Enhanced Failure Monitoring). On initial connection, it queries Aurora's topology table to discover all instances. During failover, it bypasses DNS propagation by connecting directly to known instance IPs.

**Failover and HikariCP interaction — known issues:**
- **Mass extinction problem** (HikariCP issue #1247): When `maxLifetime` causes synchronized connection recycling, all new connections land on the same Aurora replica. Fix: HikariCP's ±2.5% jitter on `maxLifetime` partially addresses this, but consider using shorter `maxLifetime` values (5–10 minutes) for Aurora.
- **`SQLExceptionOverride`** (HikariCP PR #2045): Prevents unnecessary eviction of connections that have successfully failed over via the AWS driver.
- Set `networkaddress.cache.ttl=1` in your JVM to minimize DNS caching during failover.

**Aurora connection pinning** (relevant when using RDS Proxy):
- RDS Proxy pins connections (defeating multiplexing) when: `SET` session variables, temporary tables, `LOCK TABLE`, named locks, user variables (`@var`), or text > 16KB are used
- HikariCP's `connectionInitSql` with `DISCARD ALL` will cause pinning — use the proxy's initialization query instead
- Documentation: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy-pinning.html

**Hands-on lab:** Set up a Spring Boot Kotlin app with the AWS Advanced JDBC Wrapper connecting to an Aurora cluster. Configure read/write splitting using either the wrapper's built-in plugin or `AbstractRoutingDataSource` with separate pools. Trigger a manual Aurora failover from the RDS console and observe connection behavior in your HikariCP metrics.

**Phase 4 milestone:** Deploy a working multi-datasource configuration to your staging EKS cluster with separate writer and reader pools, verify correct read/write routing via CloudWatch query logs, and document your Aurora-specific HikariCP settings.

---

## Phase 5: Database-specific tuning and production monitoring (Weeks 12–13)

### Week 12: MySQL and PostgreSQL tuning for HikariCP

**Objective:** Configure database-specific driver properties and align server timeouts with pool configuration.

**MySQL tuning:**

The critical timeout alignment: **`maxLifetime` must be shorter than MySQL's `wait_timeout`**. If `wait_timeout=600` (10 min), set `maxLifetime=540000` (9 min). The HikariCP FAQ recommends a gap of at least one minute. If you don't, MySQL closes the connection server-side while HikariCP still considers it valid, causing `CommunicationsException`.

MySQL Connector/J driver properties (from HikariCP's MySQL Configuration wiki):
```yaml
spring:
  datasource:
    hikari:
      data-source-properties:
        cachePrepStmts: true          # Must enable for cache settings to work
        prepStmtCacheSize: 250        # Default 25 is too low
        prepStmtCacheSqlLimit: 2048   # Default 256 truncates Hibernate's long SQL
        useServerPrepStmts: true      # Server-side prepared stmts — significant perf boost
        useLocalSessionState: true    # Avoids redundant server roundtrips
        rewriteBatchedStatements: true # Rewrites batch inserts into multi-value
        cacheResultSetMetadata: true
        cacheServerConfiguration: true
        elideSetAutoCommits: true     # Skips unnecessary SET autocommit calls
```

HikariCP deliberately does **not** cache PreparedStatements at the pool level. It delegates to driver-level caching, which is more efficient because drivers can share execution plans across connections. With pool-level caching (C3P0/DBCP style), 250 statements × 10 connections = 2,500 cached plans. With driver-level caching, it's just 250.

**PostgreSQL tuning:**

PostgreSQL's process-per-connection model means each connection costs ~10MB RAM. The default `max_connections` of **100** is a hard constraint. Aurora PostgreSQL scales this with instance class (e.g., db.r5.large ≈ 1,600, db.r5.xlarge ≈ 3,200).

**When you need PgBouncer in addition to HikariCP:**
- Multiple microservices accessing the same database (20 services × 10 connections = 200 connections, exceeding `max_connections`)
- Large number of pod replicas (50 pods × 10 = 500 connections)
- Short-lived or serverless workloads

When using both HikariCP and PgBouncer, reduce HikariCP's `maximumPoolSize` to 2–5 per pod (PgBouncer handles the multiplexing). Use PgBouncer in **transaction pooling mode** (`pool_mode = transaction`), which assigns backend connections only during transactions. Enable `max_prepared_statements` in PgBouncer for prepared statement support in transaction mode.

**Reading:**
- HikariCP MySQL Configuration wiki (https://github.com/brettwooldridge/HikariCP/wiki/MySQL-Configuration) ⭐
- Aurora PostgreSQL connection pooling best practices (https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.BestPractices.connection_pooling.html)

### Week 13: Monitoring, dashboards, and diagnosing production issues

**Objective:** Set up comprehensive HikariCP monitoring and learn to diagnose the most common production failures.

**Monitoring setup — Micrometer → Prometheus → Grafana:**

Spring Boot with Micrometer automatically exposes HikariCP metrics when `spring-boot-starter-actuator` is on the classpath. The key metrics:

| Metric | What it tells you | Alert threshold |
|--------|-------------------|-----------------|
| `hikaricp.connections.active` | Currently borrowed connections | Alert if sustained at `maximumPoolSize` |
| `hikaricp.connections.idle` | Available connections in pool | Alert if consistently 0 |
| `hikaricp.connections.pending` | Threads waiting for a connection | **Alert if > 0 for > 5 seconds** — this is your earliest warning of pool pressure |
| `hikaricp.connections.acquire` | Time to borrow a connection (histogram) | Alert if p99 > 1 second |
| `hikaricp.connections.creation` | Time to create a new connection | Alert if > 5 seconds (network/DNS issue) |
| `hikaricp.connections.usage` | How long connections are held (histogram) | Track p99 — long hold times indicate scope problems |
| `hikaricp.connections.timeout` | Connection acquisition timeout count | Alert if > 0 — means requests are failing |

**Grafana dashboards to import:**
- **Dashboard 20729** — "Spring Boot JDBC & HikariCP" (for Spring Boot 3.x/Micrometer): https://grafana.com/grafana/dashboards/20729-spring-boot-jdbc-hikaricp/
- **Dashboard 6083** — "Spring Boot HikariCP/JDBC": https://grafana.com/grafana/dashboards/6083-spring-boot-hikaricp-jdbc/
- **Dashboard 17313** — "HikariCP Connection Pools" (native Prometheus): https://grafana.com/grafana/dashboards/17313-hikaricp-connection-pools/

**Diagnosing the four most common production issues:**

1. **Pool exhaustion** (`pending > 0`, `active = maximumPoolSize`): Connections held too long. Check: OSIV enabled? Large `@Transactional` scope? Slow queries? External API calls inside transactions? Use `hikaricp.connections.usage` histogram to find the culprit.

2. **Connection leaks** (active count grows monotonically, never returns to idle): Set `leakDetectionThreshold=60000` (1 minute). The stack trace in the leak warning shows exactly where the unreturned connection was acquired. Common cause: manual `DataSource.getConnection()` without try-with-resources.

3. **Connection storms after deployment**: All pods start simultaneously, each trying to fill their pool. Mitigation: use rolling deployments with `maxSurge=1`, set `initializationFailTimeout=0` (attempt but don't block startup), consider `minimumIdle < maximumPoolSize` temporarily.

4. **Stale connections after Aurora failover**: Connections pointing to old writer. Mitigation: shorter `maxLifetime` (5–10 min), use AWS Advanced JDBC Wrapper, set `networkaddress.cache.ttl=1`.

**Hands-on lab:** Import Grafana dashboard 20729. Run a Gatling load test (search "Gatling Spring Boot" on https://gatling.io/) that ramps from 10 to 200 concurrent users against a database-backed endpoint. Observe how `pending`, `active`, and `acquire` metrics change. Intentionally misconfigure `maximumPoolSize=2` and watch the pool exhaust. Then restore to optimal size and compare.

**Reading:**
- "HikariCP Prometheus Metrics Explained" (https://medium.com/@ashah.dev.in/hikaricp-prometheus-metrics-explained-c16c960871ef) ⭐
- "Navigating HikariCP Connection Pool Issues" (https://medium.com/@raphy.26.007/navigating-hikaricp-connection-pool-issues-when-your-database-says-no-more-connections-3203217a14a0)
- HikariCP "Bad Behavior: Handling Database Down" wiki (https://github.com/brettwooldridge/HikariCP/wiki/Bad-Behavior:-Handling-Database-Down)
- "How to Deal with HikariCP Connection Leaks" (https://medium.com/@eremeykin/how-to-deal-with-hikaricp-connection-leaks-part-1-1eddc135b464)

**Phase 5 milestone:** Have a working Grafana dashboard monitoring all HikariCP pools in your staging environment, with alerts configured for `pending > 0` and `timeout > 0`. Run a load test report showing pool behavior under 2x expected production load.

---

## Phase 6: Advanced topics and capstone (Weeks 14–16)

### Week 14: Connection pooling in EKS and external poolers

**Objective:** Understand the unique challenges of connection pooling in containerized, autoscaling environments.

**EKS-specific considerations:**

The central tension: Kubernetes scales pods horizontally, but each pod opens its own HikariCP pool. With HPA autoscaling, total connections = `num_pods × maximumPoolSize × num_pools_per_pod`. During rolling deployments, old and new pods coexist, **temporarily doubling total connections**.

Design formula:
```
per_pod_pool_size = aurora_max_connections / 
    (max_pod_count × num_datasources × 2) 
    # ×2 for rolling deployment headroom
```

**Graceful shutdown configuration:**
```yaml
# Kubernetes deployment
terminationGracePeriodSeconds: 60
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 15"]
# Spring Boot
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

The `preStop` sleep gives the load balancer time to deregister the pod before Spring Boot begins shutdown. `HikariDataSource.close()` then waits for active connections to be returned before closing them.

**When HikariCP alone isn't enough — external poolers:**
- **ProxySQL** (MySQL): Server-side connection multiplexing, query routing, query caching. Use when many diverse services share one MySQL cluster.
- **PgBouncer** (PostgreSQL): Server-side multiplexing in transaction mode. Use when pod_count × pool_size exceeds `max_connections`.
- **RDS Proxy** (AWS managed): Fully managed, supports IAM auth. Good for Lambda/serverless. Watch for connection pinning issues.

Architecture decision guide: Use HikariCP alone when `total_pods × pool_size < 50% of max_connections`. Add an external pooler when you're approaching that limit or have more than ~10 distinct services accessing the same database.

**Reading:**
- HikariCP issue #1448 — real-world example: 10 microservices × 4 containers × 25 pool = 1,000 connections
- ProxySQL multiplexing documentation (https://proxysql.com/documentation/multiplexing/)
- PgBouncer configuration (https://www.pgbouncer.org/config.html)

### Week 15: R2DBC pooling and multi-tenant patterns

**Objective:** Understand reactive connection pooling as a contrast to JDBC pooling, and learn connection management patterns for multi-tenant architectures.

**R2DBC connection pooling overview:**
- **r2dbc-pool** (https://github.com/r2dbc/r2dbc-pool) is the standard reactive pool, built on Reactor Pool
- Key difference from HikariCP: R2DBC uses Netty EventLoops (non-blocking) vs JDBC's thread-per-connection model. Connections aren't "held" by a blocked thread — they're acquired, used for an async operation, and returned when the reactive chain completes
- Pool sizing rationale differs: JDBC needs `(cores × 2) + spindle_count` because threads block on I/O. R2DBC can support more concurrent operations with fewer connections since threads aren't blocked
- **Performance caveat** (https://piotrd.hashnode.dev/javas-reactive-connection-pooling-performance-caveat): Multiple R2DBC connections sharing the same Netty EventLoop can interfere — a data-heavy query on one connection can starve others on the same thread
- **When reactive pooling makes sense:** High-concurrency scenarios with many simultaneous I/O operations, streaming workloads, services using WebFlux end-to-end. Not worth the complexity for standard CRUD or CPU-bound workloads

**Multi-tenant connection management:**
- **Database-per-tenant**: Each tenant gets its own `HikariDataSource`. Risk: 100 tenants × 10 connections = 1,000 connections. Use `AbstractRoutingDataSource` with tenant context from request header.
- **Schema-per-tenant**: Single pool, switch schema via `connectionInitSql` or Hibernate's `MultiTenantConnectionProvider`. More connection-efficient.
- **Shared database**: Single pool, tenant discriminator column. Most connection-efficient but least isolated.

**Reading:**
- "R2DBC vs JDBC vs Vert.x Benchmark" (https://medium.com/@temanovikov/r2dbc-vs-jdbc-vs-vert-x-not-so-fast-benchmark-c0a9fcabb274) ⭐
- Callista's multi-tenancy with Spring Boot series (https://callistaenterprise.se/blogg/teknik/2020/09/19/multi-tenancy-with-spring-boot-part1/)

### Week 16: Capstone project

**Objective:** Build a production-ready, multi-datasource Spring Boot Kotlin application that demonstrates mastery of everything in this plan.

**Project specification:**
1. Spring Boot 3.x Kotlin application deployed on EKS
2. Two HikariCP pools: writer (Aurora cluster endpoint) and reader (Aurora reader endpoint)
3. `AbstractRoutingDataSource` with `LazyConnectionDataSourceProxy` routing reads to the replica pool via `@Transactional(readOnly = true)`
4. AWS Advanced JDBC Wrapper configured for both pools
5. Optimal pool sizing calculated from your Aurora instance class
6. MySQL Connector/J driver properties tuned per HikariCP wiki recommendations
7. OSIV disabled, `provider_disables_autocommit` enabled
8. Full Micrometer → Prometheus → Grafana monitoring with dashboard 20729
9. Leak detection enabled at 60 seconds
10. Graceful shutdown configured for Kubernetes
11. Gatling load test suite that validates pool behavior under 3x expected load
12. Documentation covering all configuration decisions with rationale

**Deliverable:** A working repository, a Grafana dashboard screenshot under load, and a written architecture decision record (ADR) explaining each HikariCP configuration choice.

---

## Essential reading list — prioritized

For time-constrained weeks, these are the resources that deliver the highest insight per hour invested, ranked by priority:

1. **HikariCP "About Pool Sizing" wiki** (https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing) — the single most impactful concept in this entire plan
2. **Vlad Mihalcea's "The Anatomy of Connection Pooling"** (https://vladmihalcea.com/the-anatomy-of-connection-pooling/) — foundational mental model
3. **HikariCP "Down the Rabbit Hole" wiki** (https://github.com/brettwooldridge/HikariCP/wiki/Down-the-Rabbit-Hole) — understanding the engineering
4. **Vlad Mihalcea's "Spring Transaction and Connection Management"** (https://vladmihalcea.com/spring-transaction-connection-management/) — the Spring/Hibernate connection lifecycle
5. **Brett Wooldridge's jOOQ interview** (https://blog.jooq.org/jooq-tuesdays-brett-wooldridge-shows-what-it-takes-to-write-the-fastest-java-connection-pool/) — design philosophy and origin story
6. **"High-Performance Java Persistence"** by Vlad Mihalcea — Chapters 2 and 9 cover JDBC and Hibernate connection management comprehensively
7. **HikariCP MySQL Configuration wiki** (https://github.com/brettwooldridge/HikariCP/wiki/MySQL-Configuration) — driver-level tuning
8. **AWS Advanced JDBC Wrapper documentation** (https://github.com/aws/aws-advanced-jdbc-wrapper) — Aurora-specific driver capabilities
9. **FlexyPool** (https://github.com/vladmihalcea/flexy-pool) — adaptive pool sizing and metrics overlay for HikariCP
10. **"Connection Pooling: Fundamentals, Challenges and Trade-offs"** (https://engineeringatscale.substack.com/p/database-connection-pooling-guide) — industry-wide perspective on pooling at scale

## Conclusion: the three insights that matter most

After 16 weeks, three principles should guide every connection pooling decision you make. First, **smaller pools are faster pools** — the formula `(cores × 2) + spindle_count` yields single-digit connection counts, and increasing beyond that adds context-switching overhead that measurably degrades throughput. Second, **connection hold time is the only metric that truly matters** — every configuration decision (disabling OSIV, narrowing `@Transactional` scope, enabling `provider_disables_autocommit`) ultimately reduces how long each connection is held, which is what determines whether your pool can serve your load. Third, **the pool is not the problem you think it is** — most "connection pool" issues in production are actually transaction scope issues, missing indexes causing slow queries, or architectural problems like too many microservices sharing one database. HikariCP's pool sizing formula, combined with its monitoring metrics, gives you the diagnostic tools to distinguish pool configuration problems from the application and architecture problems that masquerade as them.