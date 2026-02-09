# Mastering SQL database optimization: a 16-week learning plan

**This plan takes a Spring Boot Kotlin developer from writing basic SQL to confidently optimizing queries, tuning databases, and scaling infrastructure on AWS RDS/Aurora.** It progresses through four tiers: understanding how databases execute queries (weeks 1–4), optimizing application-level data access (weeks 5–8), mastering engine-specific internals (weeks 9–12), and scaling infrastructure (weeks 13–16). MySQL is the primary focus throughout, with PostgreSQL as secondary coverage. Every week pairs reading with hands-on exercises so concepts become muscle memory rather than abstract knowledge.

---

## Phase 1: Query execution internals and EXPLAIN fundamentals (weeks 1–4)

### Week 1 — How query optimizers think

The first week builds a mental model of what happens between sending a SQL statement and receiving results. You need to understand the parsing → planning → optimization → execution pipeline before any tuning makes sense.

**Core reading.** Start with chapters 1–3 of *SQL Performance Explained* by Markus Winand (2012, self-published, **free at use-the-index-luke.com**). This slim book is the single most important resource in the entire plan — it teaches indexing and query optimization across MySQL and PostgreSQL with a developer-first perspective. Read the "Anatomy of an Index" chapter first to understand B-tree structure, leaf node traversal, and why "slow indexes" exist. Supplement with Morgan Tocker's free *Unofficial MySQL 8.0 Optimizer Guide* (unofficialmysqlguide.com), focusing on the server architecture, cost-based optimization, and optimizer trace chapters.

**Video.** Watch the first 5 lectures of CMU 15-445 (Fall 2024) by Andy Pavlo on YouTube — covering the relational model, storage, and buffer pools. These are university-grade lectures available completely free, and they build the theoretical foundation that most tutorials skip. Also watch Hussein Nasser's "How Databases Execute Queries" and "Database Indexing Explained" videos on his YouTube channel (The Backend Engineering Show, **109K+ Udemy students** for his database engineering course).

**Hands-on.** Install MySQL 8.0 and PostgreSQL 16 locally using Docker. Import the MySQL `employees` sample database and the PostgreSQL `pagila` database. Run simple SELECT queries and observe execution with `EXPLAIN` (don't worry about interpreting everything yet — just get comfortable with the tooling).

**Success indicator:** You can draw the query execution pipeline from memory and explain what cost-based optimization means in plain language.

### Week 2 — Reading MySQL EXPLAIN output

This week focuses exclusively on MySQL's EXPLAIN output — learning to read it fluently is the single highest-leverage skill for a MySQL-primary developer.

**Core reading.** Work through the MySQL EXPLAIN output format reference (dev.mysql.com/doc/en/explain-output.html), understanding each column: `type` (system → const → eq_ref → ref → range → index → ALL), `possible_keys`, `key`, `key_len`, `rows`, `filtered`, and the `Extra` column values. Read the SitePoint guide "Using EXPLAIN to Write Better MySQL Queries" (updated November 2024) for practical walkthrough examples. Then explore `EXPLAIN FORMAT=JSON` and `EXPLAIN ANALYZE` (introduced in MySQL 8.0.18) using the official documentation.

**Course.** Begin PlanetScale's **"MySQL for Developers"** by Aaron Francis — a free, **7-hour, 64-video course** widely considered the best intermediate MySQL course available. Complete the Schema and Indexes sections this week. Aaron's explanations of `key_len` interpretation and composite index behavior are exceptional.

**Tools.** Set up mysqlexplain.com (by Tobias Petry) as your go-to EXPLAIN visualizer. Paste real EXPLAIN output from your queries and learn to read the visual representation. Also install MySQL Workbench and use its Visual Explain feature.

**Hands-on.** Take 10 queries from the employees database, run `EXPLAIN`, `EXPLAIN FORMAT=JSON`, and `EXPLAIN ANALYZE` on each. For every query, write down: access type, rows examined vs. rows returned ratio, and whether an index was used. Identify which queries do full table scans.

**Success indicator:** Given any MySQL EXPLAIN output, you can identify the access type, whether indexes are being used effectively, and estimate relative query cost.

### Week 3 — Reading PostgreSQL EXPLAIN ANALYZE output

**Core reading.** Start with the official PostgreSQL documentation "Using EXPLAIN" (postgresql.org/docs/current/using-explain.html), then read Laurenz Albe's excellent "EXPLAIN ANALYZE in PostgreSQL and how to interpret it" on the CYBERTEC blog (updated July 2023). This covers all options including `BUFFERS`, `VERBOSE`, `SETTINGS`, and PostgreSQL 16's `GENERIC_PLAN`. Follow with Elizabeth Christensen's beginner-friendly "Get Started with EXPLAIN ANALYZE" from Crunchy Data and the Thoughtbot guide "Reading a Postgres EXPLAIN ANALYZE Query Plan" (updated January 2025).

**Key differences from MySQL to internalize:** PostgreSQL shows **startup cost and total cost** (two numbers separated by `..`), uses **actual time** in milliseconds, shows **loops** for nested operations, and the `BUFFERS` option reveals shared hits vs. reads (cache efficiency). PostgreSQL's planner is generally more sophisticated than MySQL's — it supports hash joins and merge joins natively, while MySQL gained hash joins only in 8.0.18.

**Tools.** Bookmark three EXPLAIN visualizers: **explain.dalibo.com** (open source, self-hostable), **explain.depesz.com** (by Hubert Lubaczewski, great for per-node timing), and **pgMustard** (commercial, provides scored optimization advice). Use pgAdmin's built-in graphical explain feature for daily work.

**Hands-on.** Run the same logical queries on both MySQL (employees) and PostgreSQL (pagila). Compare EXPLAIN outputs side by side. Document differences in join strategies chosen, cost estimation approaches, and output format. Create a personal cheat sheet comparing MySQL and PostgreSQL EXPLAIN columns.

**Success indicator:** You can interpret PostgreSQL EXPLAIN ANALYZE output including buffer statistics, identify sequential scans vs. index scans, and explain the difference between estimated and actual rows.

### Week 4 — Cost estimation, statistics, and join strategies

**Reading.** Read chapters 4–5 of *SQL Performance Explained* (join operations and clustering data). In the *Unofficial MySQL 8.0 Optimizer Guide*, read the cost-based optimization and join chapters. For PostgreSQL, read the official docs on "Planner/Optimizer" and "Statistics Used by the Planner."

**Deep dive into join strategies.** Understand the three fundamental join algorithms: **nested loop joins** (good for small result sets with indexes), **hash joins** (good for large unsorted datasets — MySQL added these in 8.0.18), and **merge joins** (good for pre-sorted data, PostgreSQL only). Study how the optimizer chooses between them based on table sizes, available indexes, and memory settings (`join_buffer_size` in MySQL, `work_mem` in PostgreSQL).

**Cardinality estimation.** Learn how MySQL histogram statistics (available since 8.0) and PostgreSQL's `pg_statistic` table feed into cost estimation. Practice running `ANALYZE` in PostgreSQL and `ANALYZE TABLE` in MySQL, then observe how EXPLAIN output changes.

**Hands-on mini-project.** Create a database with 3–4 tables, each containing 100K–1M rows of generated data. Write 10 queries involving JOINs, subqueries, and aggregations. For each query: run EXPLAIN, force different join orders using hints (`STRAIGHT_JOIN` in MySQL, `SET enable_hashjoin = off` in PostgreSQL), and compare costs. Document which join strategy the optimizer chooses and why.

**Success indicator:** You can predict which join strategy the optimizer will choose for a given query and explain how cardinality estimation errors lead to suboptimal plans.

---

## Phase 2: The indexing deep dive (weeks 5–6)

### Week 5 — B-tree indexes, composite indexes, and covering indexes

This is the most impactful week in the entire plan. **Indexing is responsible for 80%+ of query performance improvements** in real applications.

**Core reading.** Finish *SQL Performance Explained* (chapters 6–9 covering sorting, partial results, and DML impact). Then work through Rick James' MySQL Index Cookbook (mysql.rjweb.org/doc.php/index_cookbook_mysql) — one of the most referenced MySQL indexing guides in existence. For composite indexes specifically, study the PlanetScale "MySQL for Developers" composite indexes lesson, which explains the **leftmost prefix rule**, how `key_len` reveals index usage depth, and how range conditions stop index traversal.

**Key concepts to master:**

- **Composite index column ordering:** Equality columns first, then range columns, then sort columns (the ERS rule)
- **Covering indexes:** When an index contains all columns needed by a query, enabling index-only scans (`Using index` in MySQL EXPLAIN Extra, "Index Only Scan" in PostgreSQL)
- **Index selectivity and cardinality:** High-cardinality columns benefit more from indexing; the "20% rule" for when the optimizer switches from index scan to full table scan
- **When indexes hurt:** Write amplification on INSERT/UPDATE/DELETE, index bloat, memory consumption

**Hands-on.** Using your 1M-row test database: (1) identify the slowest queries using EXPLAIN, (2) design composite indexes following the ERS rule, (3) verify improvement with EXPLAIN ANALYZE, (4) measure the INSERT performance impact of each new index. Create both MySQL and PostgreSQL versions.

**Success indicator:** Given a slow query with its EXPLAIN output, you can design an optimal composite index, predict the new EXPLAIN output, and articulate the write-performance tradeoff.

### Week 6 — PostgreSQL-specific indexes, partial indexes, and index maintenance

**PostgreSQL index types.** Study the four specialized index types through the AWS blog post "Index Types Supported in Amazon Aurora/RDS PostgreSQL" (2023) and the official PostgreSQL documentation:

- **GIN indexes** for full-text search, JSONB, and array columns — use the DEV Community "PostgreSQL GIN Index Complete Guide" by Anto Zanini
- **GiST indexes** for geometric, range, and nearest-neighbor queries
- **BRIN indexes** for naturally ordered data (timestamps, sequential IDs) — dramatically smaller than B-tree for time-series tables
- **SP-GiST indexes** for non-balanced data structures (phone numbers, IP addresses)

**Partial indexes** (PostgreSQL only) are a powerful feature — an index with a WHERE clause that only indexes rows matching a condition. Example: `CREATE INDEX idx_active_orders ON orders(created_at) WHERE status = 'active'` indexes only active orders, keeping the index small and fast.

**Index maintenance.** Learn to identify unused indexes (MySQL: `sys.schema_unused_indexes`; PostgreSQL: `pg_stat_user_indexes` where `idx_scan = 0`), redundant indexes, and bloated indexes. Study MySQL's **invisible indexes** (8.0+) for safely testing index removal without dropping. Practice PostgreSQL's `REINDEX` and understand index bloat from MVCC.

**Book.** Begin reading *High Performance MySQL* 4th edition by Silvia Botros and Jeremy Tinley (O'Reilly, January 2022) — chapters on schema design and indexing. This is the definitive MySQL performance reference, **completely rewritten for the 4th edition** with modern cloud and self-hosted focus from engineers at Twilio and Etsy.

**Hands-on.** Audit your test database: find all unused indexes, identify missing indexes using slow query analysis, create partial indexes in PostgreSQL for filtered queries, and measure storage savings of BRIN vs. B-tree on a time-series table.

**Success indicator:** You can select the appropriate index type for any column/query pattern, design partial indexes, and perform a complete index audit identifying unused and redundant indexes.

---

## Phase 3: Query optimization and JPA/Hibernate performance (weeks 7–8)

### Week 7 — Query rewriting and optimization patterns

**Core reading.** Complete the Queries and Examples sections of Aaron Francis's "MySQL for Developers" course. Read chapters on query optimization from *High Performance MySQL* 4th edition. Study Markus Winand's modern-sql.com for advanced SQL features (window functions, CTEs, LATERAL joins) and their performance characteristics.

**Critical patterns to master:**

- **Subquery vs. JOIN performance:** MySQL historically handled subqueries poorly (materializing them into temporary tables); MySQL 8.0 improved this with semi-join optimizations, but JOINs remain generally faster for correlated subqueries
- **EXISTS vs. IN:** EXISTS short-circuits and performs better with large outer tables; IN can leverage indexes on the subquery
- **Pagination:** **Offset pagination degrades linearly** as offset grows (`LIMIT 1000000, 10` scans 1M rows). Keyset/cursor pagination (`WHERE id > last_seen_id ORDER BY id LIMIT 10`) maintains constant performance. This is critical for production APIs
- **CTE materialization:** PostgreSQL 12+ made CTEs non-materialized by default (the optimizer can push predicates into them). MySQL 8.0 CTEs are always materialized — a key performance difference
- **Window functions:** Generally more efficient than self-joins for running totals, rankings, and lag/lead comparisons

**MySQL optimizer hints.** Study `/*+ INDEX(t idx_name) */`, `/*+ NO_INDEX(t) */`, `/*+ JOIN_ORDER(t1, t2) */`, `/*+ SET_VAR(optimizer_switch='...') */`. These are useful escape hatches when the optimizer makes suboptimal choices.

**Hands-on.** Take 5 real queries from a production-like workload. For each: (1) rewrite using at least 2 alternative approaches (subquery → JOIN, offset → keyset, etc.), (2) benchmark all approaches with EXPLAIN ANALYZE, (3) document which approach wins and why. Build a keyset pagination endpoint in Spring Boot.

**Success indicator:** You can identify and fix the top 5 query anti-patterns (SELECT *, offset pagination, correlated subqueries, implicit type conversions, functions on indexed columns).

### Week 8 — JPA/Hibernate performance optimization

This is the most directly applicable week for your daily work as a Spring Boot Kotlin developer.

**Essential reading.** Begin with Vlad Mihalcea's blog post "Hibernate performance tuning tips" (vladmihalcea.com) as an overview, then deep-dive into these critical articles: "N+1 query problem with JPA and Hibernate," "The best way to map a projection query to a DTO," and "The best way to log SQL statements with Spring Boot." Follow with Thorben Janssen's "6 Performance Pitfalls when using Spring Data JPA" and his "Hibernate Performance Tuning — 2025 Edition."

**Book.** Read *High-Performance Java Persistence* by Vlad Mihalcea (2016, continuously updated via eBook). Focus on Part 2: JPA & Hibernate — particularly chapters on fetching, batching, and caching. Despite being from 2016, this remains **the only comprehensive resource bridging Java data access and database performance**, endorsed by multiple Java Champions.

**N+1 detection and prevention.** Set up datasource-proxy using gavlyukovskiy's `spring-boot-data-source-decorator` library for automatic SQL logging. This replaces `spring.jpa.show-sql=true` (which uses System.out and should never be used). Three fix strategies to implement:

- `JOIN FETCH` in JPQL: `@Query("SELECT a FROM Author a JOIN FETCH a.posts")`
- `@EntityGraph(attributePaths = ["books"])` on repository methods
- Batch fetching: `spring.jpa.properties.hibernate.default_batch_fetch_size=10`

**Batch operations.** Configure JDBC batching properly — this is where **most Spring Boot apps leave 10–100x performance on the table**:

```properties
spring.jpa.properties.hibernate.jdbc.batch_size=30
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true
# MySQL: rewriteBatchedStatements=true in connection URL
# PostgreSQL: reWriteBatchedInserts=true in datasource properties
```

Critical: `GenerationType.IDENTITY` **completely disables JDBC batching**. Use `SEQUENCE` strategy instead (both MySQL 8.0+ and PostgreSQL support sequences).

**DTO projections.** Always use DTO projections for read-only queries instead of fetching full entities. Spring Data JPA supports interface-based projections, class-based projections, and Kotlin data class projections. Vlad Mihalcea's benchmarks show **DTO projections can be 5–10x faster** than entity fetching for wide tables.

**Hands-on mini-project.** Build a Spring Boot Kotlin service with: (1) datasource-proxy logging enabled, (2) a repository with an N+1 problem and 3 different fixes, (3) batch insert of 10K records comparing IDENTITY vs. SEQUENCE generators (target: under 5 seconds), (4) a DTO projection for a complex read query. Use the Anghel Leonard **Hibernate-SpringBoot** GitHub repository (300+ best practices) as reference.

**Success indicator:** You can detect N+1 queries in logs, fix them using JOIN FETCH or EntityGraph, configure batch inserts achieving >1000 rows/second, and implement DTO projections for all read-only endpoints.

---

## Phase 4: Engine-specific internals (weeks 9–10)

### Week 9 — MySQL InnoDB internals and diagnostics

**Core reading.** Read the InnoDB chapters in *High Performance MySQL* 4th edition. Study the MySQLTutorial.org "MySQL InnoDB Architecture" guide for a visual overview of in-memory structures (buffer pool, change buffer, adaptive hash index, log buffer) and on-disk structures (tablespaces, redo log, undo logs, doublewrite buffer). Deep-dive into buffer pool tuning using the ScaleGrid guide "MySQL InnoDB Buffer Pool Size Configuration."

**Book.** Read *Efficient MySQL Performance* by Daniel Nichter (O'Reilly, 2021) — this is the **most practical modern book on MySQL performance for developers**. Nichter (15+ years MySQL experience, former Percona engineer) focuses on query response time as the "North Star" metric. The companion GitHub repository (github.com/efficient-mysql-performance/examples) provides reproducible exercises.

**Performance Schema and sys schema.** Work through the MySQL Performance Schema Quick Start (dev.mysql.com) and then practice with sys schema views: `sys.statements_with_full_table_scans`, `sys.schema_unused_indexes`, `sys.innodb_lock_waits`, `sys.schema_table_statistics`. These views make Performance Schema data human-readable.

**Slow query log.** Configure the slow query log (`long_query_time=1`, `log_slow_extra=ON` in MySQL 8.0.14+), then install Percona Toolkit and learn `pt-query-digest`. Jeff Geerling's quick tutorial "Analyzing a MySQL slow query log with pt-query-digest" is the fastest path to proficiency.

**MySQL 8.0+ features.** Practice with invisible indexes (test index removal safely), histogram statistics (`ANALYZE TABLE ... UPDATE HISTOGRAM ON column`), and descending indexes. Use Omar El Khatib's "MySQL 8 Query Performance Reference" as a comprehensive guide with practical SQL examples.

**Hands-on.** On your test database: (1) configure and analyze the slow query log with pt-query-digest, (2) use Performance Schema to find the top 10 queries by total execution time, (3) tune buffer pool size and measure hit ratio, (4) create histogram statistics and observe EXPLAIN changes. Use the MySQLTuner-perl script (github.com/major/MySQLTuner-perl) for a configuration audit.

**Success indicator:** You can configure slow query logging, analyze results with pt-query-digest, navigate Performance Schema/sys schema views, and tune core InnoDB parameters (buffer pool size, redo log size, change buffer).

### Week 10 — PostgreSQL MVCC, vacuum, and configuration tuning

**MVCC and vacuum.** This is PostgreSQL's most distinctive (and misunderstood) subsystem. Start with the AWS blog post "Understanding autovacuum in Amazon RDS for PostgreSQL" (2023) for clear MVCC diagrams, then read Laurenz Albe's "Tuning autovacuum for PostgreSQL" on CYBERTEC and the EDB guide "Autovacuum Tuning Basics." Key concepts: **dead tuples accumulate from UPDATE/DELETE operations, and autovacuum must clean them** to prevent table bloat and transaction ID wraparound. Understand `autovacuum_vacuum_scale_factor`, `autovacuum_vacuum_threshold`, `autovacuum_vacuum_cost_delay`, and per-table overrides.

**HOT updates** (Heap-Only Tuples) are a critical PostgreSQL optimization: when an UPDATE doesn't change any indexed columns, PostgreSQL can avoid creating new index entries, dramatically improving update performance. Use `fillfactor` (e.g., 80%) to leave room for HOT updates on frequently-updated tables.

**Configuration tuning.** Use **PGTune** (pgtune.leopard.in.ua) to generate a baseline configuration, then understand each parameter: **`shared_buffers`** (start at 25% of RAM), **`work_mem`** (per-operation sort/hash memory — `(Total RAM - shared_buffers) / (16 × CPU cores)` as a starting formula), **`effective_cache_size`** (set to ~50–75% of RAM, tells the planner how much cache to expect), and `maintenance_work_mem` (for VACUUM and CREATE INDEX). Read the Crunchy Data guide "Optimize PostgreSQL Server Performance Through Configuration" and the EDB memory tuning tutorial.

**pg_stat_statements.** Enable this extension (`shared_preload_libraries = 'pg_stat_statements'`) and learn to query it for top statements by `total_exec_time`, `mean_exec_time`, `calls`, and `shared_blks_hit / (shared_blks_hit + shared_blks_read)` (buffer cache hit ratio). The Crunchy Data blog post "Query Optimization in Postgres starts with pg_stat_statements" is the best practical guide.

**auto_explain extension.** Configure this to automatically log EXPLAIN plans for queries exceeding a threshold — invaluable for production debugging without running manual EXPLAIN.

**Parallel query.** Read the Crunchy Data guide "Parallel Queries in Postgres" showing **2.4 GB/s parallel scan rates** on 32-core servers. Understand configuration parameters: `max_parallel_workers_per_gather`, `parallel_tuple_cost`, `min_parallel_table_scan_size`.

**Book.** Begin *PostgreSQL Query Optimization* 2nd edition by Dombrovskaya, Novikov, and Bailliekova (Apress, **January 2024**). This uses a systematic 5-step methodology with a fictional airline database. The companion code is on GitHub (github.com/Apress/postgresql-query-optimization).

**Hands-on.** (1) Configure autovacuum monitoring and observe dead tuple accumulation during bulk updates, (2) tune shared_buffers/work_mem and benchmark query performance changes, (3) enable pg_stat_statements and identify your top 5 most expensive queries, (4) configure auto_explain with a 500ms threshold. Use the **postgresql-performance-essentials** Docker lab (github.com/eugene-khyst/postgresql-performance-essentials) for guided exercises.

**Success indicator:** You can tune autovacuum for a high-write workload, configure memory parameters using PGTune as a starting point, query pg_stat_statements to identify problematic queries, and explain how MVCC causes table bloat.

---

## Phase 5: AWS RDS/Aurora and monitoring (weeks 11–12)

### Week 11 — AWS RDS/Aurora architecture and Performance Insights

**Aurora architecture.** Read the Amazon Science blog post "A Decade of Database Innovation: The Amazon Aurora Story" for the architectural overview, then study the AWS documentation on Aurora MySQL and Aurora PostgreSQL best practices. Key insight: **Aurora separates compute from storage** — the storage layer is a distributed, fault-tolerant system with 6 copies across 3 AZs. This means many traditional MySQL/PostgreSQL tuning parameters (like redo log sizing) behave differently on Aurora.

**RDS Performance Insights.** This is your primary query analysis tool on AWS. Work through the official AWS documentation and the practical tutorial by Audun Persson "Understanding Amazon RDS Performance Insights for Postgres" (Medium). Focus on: Average Active Sessions (AAS) metric, wait event analysis (CPU, IO, Lock), and top SQL identification. Note: **AWS announced EOL for the Performance Insights console on June 30, 2026**, recommending migration to CloudWatch Database Insights Advanced mode — learn the new interface.

**Parameter groups.** Study the AWS blog "Best practices for Amazon Aurora MySQL database configuration" for parameter tuning guidance. Key Aurora-specific parameters: `aurora_use_key_prefetch` (enables Asynchronous Key Prefetch), `aurora_parallel_query` (offloads query processing to storage layer), and the fact that `innodb_buffer_pool_size` is auto-managed in Aurora.

**RDS Proxy.** Understand when and why to use it: connection pooling (especially for Lambda/serverless), failover acceleration, and IAM authentication. Read the real-world lessons blog from TO THE NEW: "RDS Proxy in Production: Real-World Lessons" covering **20–30 second reconnection during failover**. Important cost consideration: RDS Proxy for Aurora Serverless v2 incurs minimum charges for **8 ACUs (~$144/month)**.

**Aurora Serverless v2.** Study scaling behavior (0.5 ACU granularity, can scale to 0 from MySQL 3.08.0+), and when it makes sense vs. provisioned instances. Read the Strobes cost optimization case study "Cut RDS Costs by 50% with Aurora Serverless V2 Connections."

**re:Invent talks.** Watch **DAT312: "Boost Performance and Reduce Costs in Amazon Aurora and Amazon RDS"** (re:Invent 2025) covering Graviton right-sizing (**46% cost reduction**), I/O-Optimized storage (**23% savings**), and tiered cache (**90% cost reduction**). Also watch **DAT408: "Deep Dive into Amazon Aurora and its Innovations"** (re:Invent 2023).

**Hands-on.** (1) Create an Aurora MySQL cluster and an Aurora PostgreSQL cluster on AWS free tier or minimal instances, (2) enable Performance Insights and generate load with `sysbench` or `pgbench`, (3) identify top queries and wait events in Performance Insights, (4) configure a custom parameter group and test the impact of key parameter changes. Set up RDS Enhanced Monitoring to observe OS-level metrics.

**Success indicator:** You can navigate Performance Insights to identify slow queries and bottleneck wait events, configure Aurora parameter groups, and make informed decisions between Aurora vs. RDS, provisioned vs. serverless, and when RDS Proxy adds value.

### Week 12 — Database monitoring, diagnostics, and observability

**Slow query infrastructure.** Configure slow query logging on both MySQL (slow query log + pt-query-digest) and PostgreSQL (pg_stat_statements + auto_explain + pgBadger for log analysis). On RDS, slow query logs publish to CloudWatch Logs — set up log export and analysis.

**Lock contention and deadlocks.** Study the Percona guide "How to Deal with and Resolve MySQL Deadlocks" covering `SHOW ENGINE INNODB STATUS` analysis and `pt-deadlock-logger`. For PostgreSQL, read Laurenz Albe's "Debugging Deadlocks in PostgreSQL" on CYBERTEC and the pganalyze guide "Postgres Log Monitoring 101: Deadlocks, Checkpoint Tuning & Blocked Queries." Key technique: enable `log_lock_waits` in PostgreSQL and `innodb_print_all_deadlocks` in MySQL for production visibility.

**Grafana dashboards.** Set up Prometheus-based monitoring: use **mysqld_exporter** for MySQL and **postgres_exporter** for PostgreSQL. Import the Percona PMM dashboards (github.com/percona/grafana-dashboards) as a starting point. Key metrics to dashboard: queries per second, average query latency (p50/p95/p99), buffer pool hit ratio, connection pool utilization, replication lag, deadlock rate, and autovacuum activity.

**Spring Boot Actuator integration.** Configure Micrometer with Prometheus export for application-side database metrics:

- `hikaricp.connections.active` / `.idle` / `.pending` — connection pool health
- `hikaricp.connections.usage` — connection hold time (approximates query duration)
- `hibernate.query.executions` / `hibernate.entities.fetches` — ORM-level visibility

Add `io.micrometer:micrometer-registry-prometheus` and expose via `/actuator/prometheus`.

**Hands-on mini-project.** Build a complete monitoring stack: (1) Prometheus scraping MySQL, PostgreSQL, and Spring Boot metrics, (2) Grafana dashboards showing database health, (3) alerting on slow query rate, connection pool exhaustion, and replication lag. Generate deadlocks intentionally and practice diagnosing them.

**Success indicator:** You have a working Grafana dashboard showing real-time database health, can diagnose deadlocks from logs, and have alerting configured for the top 5 database failure modes.

---

## Phase 6: Infrastructure-level scaling (weeks 13–16)

### Week 13 — Read replicas and read/write splitting in Spring Boot

**Read/write splitting implementation.** This is the most common first scaling step for Spring Boot applications on Aurora. Study the Medium article "Read-Write Database Splitting in Spring Boot" by Sufiyan Salman, which uses `AbstractRoutingDataSource` + `LazyConnectionDataSourceProxy` + `@Transactional(readOnly = true)` for automatic routing. The Kotlin implementation is clean:

```kotlin
class TransactionRoutingDataSource : AbstractRoutingDataSource() {
    override fun determineCurrentLookupKey(): Any =
        if (TransactionSynchronizationManager.isCurrentTransactionReadOnly())
            DataSourceType.READ_ONLY
        else DataSourceType.READ_WRITE
}
```

**Aurora reader endpoints.** Understand that Aurora's reader endpoint performs **connection-level load balancing** (not query-level) across read replicas. For more granular control, RDS Proxy provides additional read-only endpoints. Study replication lag: Aurora replicas typically have **<20ms lag** due to shared storage, but it's non-zero — design for eventual consistency on read paths.

**Hands-on.** Implement read/write splitting in your Spring Boot Kotlin project: (1) configure two HikariCP pools (writer → cluster endpoint, reader → reader endpoint), (2) implement `TransactionRoutingDataSource`, (3) verify routing with datasource-proxy logging, (4) measure replication lag and implement a fallback strategy for lag-sensitive reads.

**Success indicator:** Your Spring Boot app routes `@Transactional(readOnly = true)` to read replicas and write transactions to the primary, verified by SQL logs showing different endpoints.

### Week 14 — Table partitioning and connection pooling

**Partitioning strategies.** Study when partitioning helps (tables >100M rows, time-series data with retention policies, multi-tenant databases) and when it doesn't (small tables, random access patterns). Read the PostgreSQL official documentation on declarative partitioning and the EDB tutorial "How to Use Table Partitioning to Scale PostgreSQL." For MySQL, read the High Performance MySQL chapters on partitioning.

Three partition types to understand: **range partitioning** (most common — partition by date for time-series), **list partitioning** (by category or tenant), and **hash partitioning** (for even data distribution). **Partition pruning** is the key performance benefit — the optimizer skips partitions that can't contain matching rows.

**JPA/Hibernate with partitioned tables.** Partitioning is transparent to JPA — no entity mapping changes needed. However, ensure your queries include the partition key in WHERE clauses to enable pruning. For range-partitioned time-series tables, use pg_partman (on RDS PostgreSQL) or manual `ALTER TABLE` for MySQL partition maintenance.

**Connection pooling from the database perspective.** You already know HikariCP from the application side. Now understand the database-side view: each connection consumes **~10MB of RAM in PostgreSQL** and ~1MB in MySQL. For PostgreSQL, PgBouncer in transaction mode enables hundreds of application connections to share a much smaller pool of database connections. On AWS, RDS Proxy serves this function for both MySQL and PostgreSQL. The pool sizing formula: `database_max_connections = (available_RAM - shared_buffers) / per_connection_memory`.

**Hands-on.** (1) Create a range-partitioned table by month in both MySQL and PostgreSQL, load 10M rows, and verify partition pruning in EXPLAIN, (2) set up PgBouncer in transaction mode locally and benchmark connection overhead reduction, (3) calculate optimal connection pool sizes for your application stack (HikariCP → RDS Proxy → Aurora).

**Success indicator:** You can design a partitioning strategy for a time-series workload, verify partition pruning in EXPLAIN, and calculate connection pool sizes across all layers.

### Week 15 — Caching strategies and Hibernate second-level cache

**Application-level caching.** Implement a two-tier caching strategy: **Caffeine** for local L1 cache (low-latency, limited size) and **Redis** for distributed L2 cache (shared across instances, larger capacity). Study the Baeldung guide "Implement Two-Level Cache With Spring" for the combined approach. Use Spring's `@Cacheable`, `@CacheEvict`, and `@CachePut` annotations with custom `CacheManager` configuration.

**Cache invalidation patterns.** The hardest problem in caching. Study three patterns: **TTL-based expiration** (simplest, eventual consistency), **event-driven invalidation** (publish cache-clear events on write), and **write-through caching** (update cache and database atomically). For most Spring Boot applications, TTL-based with short expiration (30–300 seconds) for frequently-read, infrequently-changed data is the pragmatic choice.

**Hibernate second-level cache with Redis.** Use Redisson as the Hibernate L2 cache provider (not Ehcache, which doesn't scale across instances). Follow the guide "Scaling Spring Boot with Hibernate 2nd Level Cache on Redis" by Mohammed Shahto. Configure with `CacheConcurrencyStrategy.READ_WRITE` for most entities, `READ_ONLY` for reference data. Key: L2 cache benefits **high read/write ratio, relatively static data** — don't cache frequently-updated entities.

**Hands-on.** (1) Implement Caffeine + Redis two-tier caching in your Spring Boot app, (2) configure Hibernate L2 cache with Redisson for reference data entities, (3) benchmark the database load reduction with caching enabled, (4) implement cache invalidation for a write endpoint.

**Success indicator:** Your application reduces database load by >50% for read-heavy endpoints through caching, with correct invalidation preventing stale data.

### Week 16 — Sharding patterns and capstone project

**When to shard.** Sharding is the scaling option of last resort — it adds enormous complexity. Study the decision framework: first try query optimization → indexing → read replicas → partitioning → caching → vertical scaling (bigger instance) → and **only then** consider sharding. Read the Red Gate Simple Talk guide "Database Sharding Strategies" and the Microsoft Azure architecture "Sharding Pattern" for comprehensive strategy coverage.

**Sharding tools.** For MySQL: **Vitess** (originally built for YouTube, now used by Slack and Block) provides transparent sharding with MySQL protocol compatibility. **Apache ShardingSphere-JDBC** integrates directly into Spring Boot applications via YAML configuration — study the Baeldung guide "A Guide to ShardingSphere." For PostgreSQL: **Citus** (now open-source from Microsoft) extends PostgreSQL with distributed tables and schema-based sharding (Citus 12+). Read the CYBERTEC guide "Citus: Sharding your first table."

**Shard key selection** is the critical design decision. The shard key must: (1) distribute data evenly, (2) be present in most queries to avoid cross-shard operations, and (3) be immutable. Common choices: tenant_id for multi-tenant apps, user_id for social platforms, geographic region for location-based services.

**Capstone project.** Build a complete demo application showcasing everything learned:

- Spring Boot Kotlin with JPA/Hibernate on Aurora MySQL
- datasource-proxy for SQL logging and N+1 detection
- DTO projections for all read endpoints
- Batch inserts with SEQUENCE generation
- Read/write splitting with AbstractRoutingDataSource
- Caffeine + Redis caching layer
- Grafana monitoring dashboard with Prometheus
- Documented query optimization report showing before/after EXPLAIN analysis for 5 key queries
- Load testing with Gatling or k6 showing throughput improvements at each optimization layer

**Success indicator:** You can present the capstone project with concrete performance numbers: query latency improvements, throughput gains from caching, and read replica utilization — demonstrating end-to-end mastery of the optimization pipeline.

---

## Essential reference library

The five books below form the core library for this plan, listed in recommended reading order. **Start with Winand's free online book and Nichter's developer-focused guide**, then expand to the engine-specific references and JPA optimization.

| Book | Author(s) | Year | Focus | When to read |
|------|-----------|------|-------|-------------|
| *SQL Performance Explained* | Markus Winand | 2012 (free at use-the-index-luke.com) | Indexing and query optimization across all databases | Weeks 1–5 |
| *Efficient MySQL Performance* | Daniel Nichter | 2021 (O'Reilly) | MySQL performance for developers, response-time focus | Weeks 5–9 |
| *High Performance MySQL* 4th ed. | Silvia Botros, Jeremy Tinley | 2022 (O'Reilly) | Complete MySQL at-scale reference | Weeks 6–16 |
| *PostgreSQL Query Optimization* 2nd ed. | Dombrovskaya, Novikov, Bailliekova | Jan 2024 (Apress) | Systematic PostgreSQL query optimization | Weeks 10–14 |
| *High-Performance Java Persistence* | Vlad Mihalcea | 2016, continuously updated | JPA/Hibernate performance from JDBC to caching | Weeks 8–15 |

**Supplementary free resources:** *Database Performance at Scale* (Apress Open Access, 2023, **free PDF**), *The Unofficial MySQL 8.0 Optimizer Guide* by Morgan Tocker (free online), and PlanetScale's "MySQL for Developers" course by Aaron Francis (free, 7 hours).

---

## Ongoing learning and community resources

After completing the 16-week plan, maintain your skills through these high-signal channels. Subscribe to the **pganalyze "5mins of Postgres"** series (100+ short episodes on specific optimization topics), the **Percona Blog** (percona.com/blog — the gold standard for MySQL/PostgreSQL performance content), and **Vlad Mihalcea's newsletter** for JPA/Hibernate updates. The **CYBERTEC blog** (by PostgreSQL core contributor Laurenz Albe) and **Crunchy Data blog** provide consistently excellent PostgreSQL content.

For conferences, **POSETTE** (formerly Citus Con, free virtual, 38 talks in 2024 with captions in 14 languages) and **Percona Live** cover practical database optimization. AWS **re:Invent** database track sessions (available on YouTube) are essential for RDS/Aurora-specific knowledge. For interactive practice, **LeetCode's database section** and **PGExercises** (pgexercises.com) keep SQL skills sharp.

The GitHub repositories **Hibernate-SpringBoot** by Anghel Leonard (300+ JPA best practices), **efficient-mysql-performance/examples** (companion to Nichter's book), and **awesome-mysql-performance** by Releem (curated resource list) serve as ongoing reference libraries for daily development work.