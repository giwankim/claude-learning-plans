---
title: "MySQL & Aurora Performance"
category: "Data & Messaging"
description: "Deep dive into MySQL/Aurora performance engineering covering InnoDB internals, query optimization, and PostgreSQL architectural comparison for Spring Boot developers"
---

# SQL mastery for the Aurora developer who wants the full picture

**Two books will transform your MySQL performance work, and understanding PostgreSQL's architectural differences will make you a sharper engineer regardless of which database you run.** The most critical insight from this research is that MySQL and PostgreSQL make fundamentally different MVCC and locking trade-offs — identical Spring Boot `@Transactional` code behaves differently on each engine, and understanding *why* separates productive developers from those debugging mysterious production issues. The good news: the MySQL learning ecosystem, while smaller than PostgreSQL's, has produced two exceptional books since 2021 specifically targeting application developers. The broader news: PostgreSQL's extension-driven ecosystem has exploded since 2023, and staying current on both engines is now a genuine career advantage.

---

## The two MySQL books that replace a decade of tribal knowledge

The MySQL learning ecosystem has fewer resources than PostgreSQL's, but two recent books stand above everything else for application developers on Aurora.

**"Efficient MySQL Performance" by Daniel Nichter** (O'Reilly, 2021) is the single most important MySQL book for someone writing Kotlin/Spring Boot against Aurora. Nichter spent eight years at Percona building tools used at the largest MySQL deployments in the world, and now works as a DBA/SWE at Block (Square/Cash App) managing thousands of MySQL servers. The book is explicitly written for *software engineers using MySQL, not managing it* — covering query response time analysis, indexing for common SQL clauses and joins, the InnoDB buffer pool, transactions, row locking, and replication. Its chapter on InnoDB internals — explaining that **InnoDB tables are themselves clustered indexes** (B+ trees organized by primary key) and that secondary indexes store primary key values requiring bookmark lookups — makes the performance implications of UUID vs sequential primary keys viscerally clear.

**"High Performance MySQL, 4th Edition" by Silvia Botros and Jeremy Tinley** (O'Reilly, 2022) is the operational bible, updated for MySQL 8.x and the cloud era. The fourth edition adds a dedicated chapter on Amazon Aurora covering its storage architecture, replication model, and operational specifics. It covers schema design, query optimization, replication topologies, scaling with Vitess and ProxySQL, and backup strategies with XtraBackup. Between these two books, you get both the developer-facing query optimization knowledge and the production operations understanding.

Beyond books, the **Percona Database Performance Blog** is the single best ongoing MySQL resource — authored by experts like Marco Tusa and Vadim Tkachenko, covering benchmarks, troubleshooting, and deep InnoDB analysis. Daniel Nichter's own **HackMySQL** blog provides concentrated performance insights. For Aurora specifically, the AWS Database Blog and the original **Aurora SIGMOD '17 paper** ("Amazon Aurora: Design Considerations for High Throughput Cloud-Native Relational Databases") explain the quorum-write, log-as-database architecture that makes Aurora fundamentally different from vanilla MySQL.

For MySQL 8.x features that matter daily: **window functions** and **CTEs** (eliminating complex subquery patterns), **EXPLAIN ANALYZE** with tree-format output (MySQL 8.0.18+), **invisible indexes** for zero-risk index cleanup testing, **NOWAIT/SKIP LOCKED** for queue-like patterns, **functional indexes** on expressions, and **instant DDL** for adding columns as metadata-only operations.

---

## PostgreSQL's extension ecosystem and why the "Just Use Postgres" movement matters to MySQL developers

Even as a MySQL/Aurora developer, understanding PostgreSQL developments is essential because **PostgreSQL became the #1 most-used database among professional developers** in Stack Overflow's 2024 survey (49%) and extended that lead to 55.6% in 2025. The community momentum has concrete implications for tooling, hiring, and architectural decisions.

The "Just Use Postgres" movement — crystallized by Denis Magda's 2025 Manning book *"Just Use Postgres!"* — argues that PostgreSQL's extension system can replace an entire polyglot persistence stack. Instead of managing Elasticsearch, Redis, MongoDB, Kafka, InfluxDB, and Pinecone separately, you use PostgreSQL with pgvector (vector search for AI/ML, **19K+ GitHub stars**), TimescaleDB (time-series, **21K+ stars**), PostGIS (geospatial, the industry standard since 2001), ParadeDB (BM25 full-text search + hybrid vector search), and pgmq (lightweight message queues). The operational argument is compelling: one database means one backup strategy, one monitoring dashboard, one security model, and one on-call runbook. Three systems at 99.9% uptime each yield only 99.7% combined — **26 hours of downtime per year versus 8.7**.

The counter-arguments deserve equal weight. At high scale, the CAPEX and OPEX to make PostgreSQL handle workloads it wasn't designed for can exceed the cost of purpose-built systems. Extension maintenance comes from small (often solo) development teams with varying reliability bars. And companies with tens of millions of users and large engineering teams may genuinely need specialized databases. Denis Magda himself discusses "when NOT to use Postgres" in his book.

For PostgreSQL books, **"The Art of PostgreSQL"** by Dimitri Fontaine (a PostgreSQL Major Contributor who authored the `CREATE EXTENSION` command itself) teaches SQL-as-code philosophy across 438 pages of data modeling, window functions, and extension development. For internals, **"PostgreSQL 14 Internals"** by Egor Rogov (free from Postgres Professional) and Hironobu Suzuki's **"The Internals of PostgreSQL"** (free at interdb.jp/pg) provide the depth equivalent that MySQL lacks in a single resource. Aaron Francis's **"Mastering Postgres"** video course at masteringpostgres.com is the most acclaimed recent course — information-dense, well-produced, and covering schema design through advanced indexing.

PostgreSQL 17 (released September 2024) added **JSON_TABLE** for converting JSON to relational tables, **MERGE with RETURNING clauses**, vacuum improvements using **20x less memory**, doubled WAL write throughput, and built-in incremental backups. PostgreSQL 16 brought SQL/JSON constructors, **300% COPY performance improvements**, and parallel FULL/RIGHT joins.

---

## How MySQL and PostgreSQL diverge under the hood — and why your Spring code cares

The most consequential differences between MySQL InnoDB and PostgreSQL are invisible in SQL syntax but profoundly affect application behavior.

**MVCC implementation** is the deepest divergence. InnoDB stores the latest row version in the clustered index and reconstructs old versions on-demand from **undo logs** — a separate rollback segment. Background purge threads automatically clean up old versions with zero maintenance. PostgreSQL creates a **complete new copy of the entire row** on every UPDATE, stored in the same heap table, with dead tuples requiring VACUUM to reclaim space. Every index on the table must be updated on every row update (since the new tuple has a different physical location), except in HOT update cases. This means PostgreSQL has inherent **write amplification** — a single-column update on a 1KB row creates a full new 1KB tuple. For MySQL Aurora developers, this explains why PostgreSQL requires aggressive autovacuum tuning that has no MySQL equivalent.

**Default isolation levels** create a behavioral trap. MySQL defaults to REPEATABLE READ; PostgreSQL defaults to READ COMMITTED. Identical `@Transactional` Spring code behaves differently on each engine without any annotation changes. Worse, even when explicitly set to the same isolation level, the *mechanisms* differ. At REPEATABLE READ, MySQL uses **gap locks and next-key locks** to physically block inserts into ranges being read — reads can block writes. PostgreSQL uses snapshot isolation where reads never block writes. A concrete example: two concurrent transactions each doing `INSERT INTO a SELECT count(*) FROM b` and `INSERT INTO b SELECT count(*) FROM a` at REPEATABLE READ produce different results — PostgreSQL returns (0, 0) via snapshots while MySQL returns (0, 1) because the second transaction blocks on the first's gap lock.

At SERIALIZABLE level, the approaches diverge further. MySQL uses **two-phase locking** (2PL), converting all SELECTs to `SELECT ... FOR SHARE` — higher blocking but predictable. PostgreSQL uses **Serializable Snapshot Isolation** (SSI) — optimistic execution with conflict detection at commit time. This means PostgreSQL SERIALIZABLE requires retry logic in your application (`@Retryable` in Spring) for serialization failures, while MySQL's SERIALIZABLE causes more deadlocks but fewer application-level retries.

**JSON handling** represents PostgreSQL's clearest technical advantage. PostgreSQL's JSONB type supports **GIN indexes** on entire columns for fast containment and existence queries, plus jsonpath expressions for complex filtering. MySQL cannot directly index JSON columns — you must create generated virtual columns extracting specific paths, then index those columns separately. If your application queries JSON documents by arbitrary keys, PostgreSQL is dramatically faster without schema-level workarounds.

**Locking** patterns differ in ways that cause production incidents. InnoDB's gap locks — which lock the "gap" between index records — create a classic deadlock pattern: `SELECT ... FOR UPDATE` on a non-existent row acquires a gap lock, and concurrent transactions with the same pattern deadlock when both try to INSERT into the locked gap. PostgreSQL has no gap locks, producing fewer surprise deadlocks, but offers **advisory locks** (`pg_advisory_lock`) for application-level coordination with no MySQL equivalent.

| Dimension | MySQL InnoDB | PostgreSQL |
|-----------|-------------|------------|
| MVCC cleanup | Automatic purge threads | Requires VACUUM (autovacuum) |
| Default isolation | REPEATABLE READ | READ COMMITTED |
| Phantom prevention | Gap locks (blocking) | Snapshot isolation (non-blocking) |
| SERIALIZABLE | 2PL (pessimistic) | SSI (optimistic, needs retry logic) |
| JSON indexing | Generated columns + B-tree | Native GIN indexes on JSONB |
| Extension ecosystem | Limited plugin architecture | Rich extension model (pgvector, PostGIS, TimescaleDB) |
| Stored procedures | SQL-only language | PL/pgSQL + PL/Python, PL/Perl, PL/v8 |
| Gap locks | Yes (prevents phantom reads, causes deadlocks) | No (advisory locks available instead) |

---

## From EXPLAIN plans to window functions: the technical skills that compound

**Reading EXPLAIN output** is the single highest-leverage skill for query optimization. MySQL 8.0.18+ supports `EXPLAIN ANALYZE` with tree-format output showing actual execution times and row counts — a major upgrade from the traditional tabular format. The key access types to watch, from best to worst: `const` > `eq_ref` > `ref` > `range` > `index` > `ALL` (full table scan). In PostgreSQL, `EXPLAIN (ANALYZE, BUFFERS)` is the gold standard, showing actual timing, row counts, loop multipliers, and buffer hit/read statistics. The critical diagnostic pattern for both engines: when estimated rows diverge significantly from actual rows, statistics are stale — run `ANALYZE TABLE` (MySQL) or `ANALYZE` (PostgreSQL) immediately.

**Indexing strategy** deserves deep study because it determines whether your queries touch hundreds or millions of rows. The **leftmost prefix rule** for composite indexes — an index on `(A, B, C)` supports queries on `A`, `A+B`, or `A+B+C` but not `B` alone — is the most commonly misunderstood indexing concept. **Covering indexes** that contain all columns needed by a query enable index-only scans, avoiding table lookups entirely. PostgreSQL 11+ supports `INCLUDE` clauses to add non-key columns to leaf nodes for covering without affecting sort order. PostgreSQL's **partial indexes** (`CREATE INDEX ... WHERE status = 'active'`) index only matching rows — smaller, faster, less write overhead — and have no MySQL equivalent. Markus Winand's **Use The Index, Luke** (use-the-index-luke.com) remains the definitive free resource on indexing across both engines.

**Window functions** eliminate entire classes of complex subqueries. The practical use cases for backend developers include pagination with total count (`ROW_NUMBER()` with `COUNT(*) OVER()`), deduplication (`ROW_NUMBER()` partitioned by duplicate key), gap detection (`LAG()` comparing consecutive rows), running totals (`SUM() OVER (ORDER BY ...)`), and top-N per group (`RANK() OVER (PARTITION BY category ORDER BY score DESC)`). Both MySQL 8.0+ and PostgreSQL support the full window function specification.

**CTE materialization** behaves differently across engines in a way that affects performance. MySQL always inlines non-recursive CTEs into the outer query (optimizer-friendly). PostgreSQL materialized CTEs by default before version 12, acting as optimization fences; PostgreSQL 12+ allows the optimizer to inline them, with explicit `MATERIALIZED` / `NOT MATERIALIZED` hints for control. Recursive CTEs — essential for hierarchy traversal, category trees, and bill-of-materials queries — always materialize in both engines. Always add a depth limit (`WHERE depth < N`) since neither engine has a built-in recursion cap.

---

## Running databases in production: connection pooling through disaster recovery

**Connection pooling** configuration is where most Spring Boot developers first encounter production database issues. HikariCP (Spring Boot's default since 2.0) should start with a pool size of **10-20 connections** — counterintuitively small, since a pool of 10 can handle thousands of concurrent users if queries are fast. The formula `(2 × CPU_cores) + effective_spindles` is a solid starting point. Set `max-lifetime` shorter than your database's `wait_timeout` to prevent stale connections. For Aurora specifically, the aggregate pool sizes across all application instances must not exceed Aurora's `max_connections` (tied to instance memory class) — with Kubernetes pod autoscaling, this means **RDS Proxy or PgBouncer becomes essential** to prevent connection exhaustion.

**Aurora's storage-level replication** is fundamentally different from traditional MySQL replication. All instances share a distributed storage volume with data replicated six ways across three Availability Zones. Only redo log records cross the network — no page writes from compute to storage. Typical replica lag is **under 100ms** (often 10-20ms) compared to seconds or minutes with traditional binlog replication. However, even 20ms lag means immediately reading your own write from a replica may return stale data — direct critical read-after-write queries to the writer endpoint using separate DataSource beans.

**Schema migrations** for Aurora require specific patterns. Flyway (simpler, SQL-file-based) integrates cleanly with Spring Boot and is sufficient for most startups. For large table alterations, **gh-ost** (GitHub's binlog-based online schema migration tool) and Percona's **pt-online-schema-change** avoid table locks. MySQL 8.0+ supports instant DDL for adding columns (`ALGORITHM=INSTANT`), and PostgreSQL 11+ makes `ADD COLUMN` with a default value instant. For zero-downtime rolling deployments, all migrations must be backward-compatible — renaming a column requires four deployments (add new → dual-write → read new → drop old).

**Monitoring** centers on different tools per engine. MySQL's Performance Schema surfaces query statistics through `events_statements_summary_by_digest`, while PostgreSQL's `pg_stat_statements` extension (must be explicitly enabled) provides equivalent query-level metrics. AWS **Performance Insights** (free tier: 7-day retention) provides the fastest path to identifying slow queries on Aurora. For deeper analysis, Percona's **PMM (Percona Monitoring and Management)** is open-source with excellent Query Analytics, while **pganalyze** provides PostgreSQL-specific EXPLAIN plan analysis and automated index recommendations.

For PostgreSQL maintenance, **autovacuum** is the most critical operational concern without a MySQL equivalent. Dead tuples from PostgreSQL's tuple-versioning MVCC accumulate and must be reclaimed. Autovacuum triggers by default when dead tuples exceed 20% of a table's size — for high-write tables, lower `autovacuum_vacuum_scale_factor` to 0.01. Failure to vacuum not only causes table bloat but risks **transaction ID wraparound**, a catastrophic failure mode that forces PostgreSQL into single-user mode. MySQL's InnoDB purge threads handle equivalent cleanup automatically with zero configuration.

---

## Engineering blogs that show what actually matters at scale

The most valuable learning comes from companies running these databases under real pressure. These posts reveal trade-offs that no textbook covers.

**Uber's PostgreSQL-to-MySQL migration post** (2016) remains the most famous database engineering blog post ever written. It analyzes InnoDB vs PostgreSQL on-disk formats, write amplification from PostgreSQL's tuple versioning with many secondary indexes, and replication architecture differences. The rebuttals from PostgreSQL experts (Markus Winand, Robert Haas) are equally essential reading — they contextualize Uber's issues as specific to their workload (heavy updates with reportedly up to 700 indexes per table). **GitHub** runs **1,200+ MySQL hosts** serving **5.5 million queries per second** across 300+ TB, using Vitess for horizontal sharding, gh-ost for online schema changes, and Orchestrator for high availability. **Shopify** manages petabyte-scale MySQL with Vitess pod architecture, handling **19 million QPS during Black Friday 2023**. Their backup blog post details GCP Persistent Disk snapshots achieving RTO under 30 minutes.

On the PostgreSQL side, **OpenAI scaled PostgreSQL to serve 800 million ChatGPT users** (2025 blog post) using a single-primary Azure PostgreSQL setup with ~50 read replicas globally, handling millions of QPS. Key lessons: avoid complex multi-table joins in OLTP, break joins into application-layer logic, carefully review ORM-generated SQL, and tune autovacuum aggressively. **Notion** sharded PostgreSQL into 480 logical shards across 32 physical databases using workspace_id as the partition key, later tripling to 96 machines with zero-downtime re-sharding. Their pganalyze case study showed GIN index optimization yielding a **733% performance improvement**.

The foundational book underlying all of these engineering decisions is **"Designing Data-Intensive Applications" by Martin Kleppmann** (O'Reilly, 2017) — universally recommended across every engineering blog surveyed. Chapters 3 (Storage & Retrieval), 5 (Replication), 6 (Partitioning), and 7 (Transactions) directly map to the trade-offs these companies navigate. **"Database Internals" by Alex Petrov** (O'Reilly, 2019) goes deeper into storage engine architecture — B-tree variants, LSM trees, buffer management — providing the mechanical understanding to evaluate decisions like Meta's MyRocks (LSM-tree storage for MySQL, achieving **50% storage reduction** vs compressed InnoDB).

---

## A 26-week curriculum from intermediate SQL to architecture decisions

This learning path is designed for a backend developer already writing Spring Boot/Kotlin against MySQL Aurora, progressing from immediate productivity gains to deep architectural understanding.

**Weeks 1-4: Intermediate foundations.** Start with "Use The Index, Luke" (full read-through) to build indexing intuition. Read "Efficient MySQL Performance" chapters on indexing and EXPLAIN. Practice `EXPLAIN ANALYZE` on your actual production queries. Study transaction isolation levels in DDIA Chapter 7 and MySQL's InnoDB transaction model documentation. Practice window functions at windowfunctions.com. Review your JPA-generated SQL with `spring.jpa.show-sql=true` and identify N+1 query problems.

**Weeks 5-8: Advanced SQL patterns.** Master CTEs and recursive queries for hierarchical data (MySQL 8.0 CTE documentation + pgexercises.com). Study table partitioning (MySQL docs + Shopify's shard-balancing blog). Explore JSON column patterns and MySQL's `JSON_TABLE()` function. Learn `NOWAIT`/`SKIP LOCKED` for queue patterns. Deep-dive composite index design — column ordering strategy of equality columns first, range columns last.

**Weeks 9-14: Production operations.** Configure HikariCP properly for Aurora (start pool size at 10, set `max-lifetime` below `wait_timeout`, enable leak detection). Implement read/write splitting with Spring's `AbstractRoutingDataSource`. Set up Performance Insights and slow query log analysis. Study Aurora's backup/failover behavior. Master Flyway migrations with backward-compatible patterns. Read GitHub's MySQL HA blog and Shopify's backup strategy post.

**Weeks 15-20: Engine internals.** Read "Database Internals" by Petrov for storage engine fundamentals. Study the Aurora SIGMOD paper for shared-storage architecture. Read "High Performance MySQL" Chapter 1 (architecture) and Chapter 6 (query optimization). Understand PostgreSQL's MVCC via interdb.jp/pg and compare with InnoDB's undo log approach. Re-read Uber's migration post with this deeper context.

**Weeks 21-26: Architecture decisions.** Study DDIA Chapters 5-6 on replication and partitioning. Read Notion's sharding blog, Figma's vertical partitioning approach, and OpenAI's PostgreSQL scaling post. Evaluate when to introduce read replicas, caching layers, or purpose-built databases. Understand Vitess for MySQL sharding. Design a data architecture for a hypothetical high-scale application, documenting trade-offs with references to the engineering blogs studied.

| Stage | Key Resources | Engine Focus |
|-------|--------------|-------------|
| Foundations (wk 1-4) | Use The Index Luke, Efficient MySQL Performance, DDIA Ch.7, windowfunctions.com | Both (MySQL primary) |
| Advanced SQL (wk 5-8) | MySQL 8.0 docs, pgexercises.com, Shopify blog | Both |
| Production Ops (wk 9-14) | Aurora docs, Performance Insights, GitHub/Shopify blogs, Flyway docs | MySQL/Aurora |
| Engine Internals (wk 15-20) | Database Internals (Petrov), interdb.jp/pg, Aurora SIGMOD paper | Both (deep comparison) |
| Architecture (wk 21-26) | DDIA Ch.5-6, Notion/OpenAI/Figma blogs, Vitess docs | Both (decision framework) |

For ongoing learning, subscribe to **DB Weekly** (dbweekly.com) for cross-database coverage, **PostgreSQL Weekly** (postgresweekly.com) for PostgreSQL developments, and **SQL for Devs** (sqlfordevs.com) for practical weekly tips. The **Postgres FM** podcast (weekly, highly technical) and **Talking Postgres** podcast (monthly, featuring core contributors) keep you current on PostgreSQL. For MySQL, the **Percona blog** and **Planet MySQL** aggregator remain the best ongoing sources.

---

## Conclusion

The MySQL learning ecosystem is narrower but has produced two exceptional modern books — Nichter's developer-focused "Efficient MySQL Performance" and the operations-oriented "High Performance MySQL" 4th edition — that together cover what Aurora application developers need. PostgreSQL's advantages in extensions, JSON handling, and community momentum make it essential knowledge even for MySQL-primary developers; the "Just Use Postgres" movement reflects real architectural simplification that affects startup technology decisions. The deepest insight from studying both engines is that **their MVCC and locking implementations create fundamentally different behavioral contracts** — MySQL's gap locks prevent phantoms but cause deadlocks that PostgreSQL's snapshot isolation avoids, while PostgreSQL's tuple versioning creates maintenance burdens (VACUUM) that MySQL's undo logs handle automatically. Understanding these trade-offs, rather than memorizing syntax, is what separates developers who debug production incidents in minutes from those who struggle for hours. The 26-week curriculum prioritizes this "why" understanding at every stage, anchored by engineering blogs from GitHub, Shopify, Uber, Notion, and OpenAI that demonstrate how these trade-offs play out at real scale.