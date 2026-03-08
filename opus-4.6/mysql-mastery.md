---
title: "MySQL Mastery"
category: "Data & Messaging"
description: "Definitive MySQL mastery plan covering essential books, InnoDB internals, Aurora-specific operations, and deliberate practice for Kotlin/Spring Boot developers"
---

# The definitive MySQL mastery plan for backend developers

**For a Kotlin/Spring Boot developer on Aurora MySQL, the fastest path to performance and DBA expertise runs through five essential books, a handful of expert blogs, and deliberate practice with real tooling.** The MySQL ecosystem has a remarkably stable canon — a few dozen resources account for the vast majority of expert knowledge. This plan prioritizes depth over breadth, sequencing resources from foundational indexing concepts through InnoDB internals to Aurora-specific operational mastery. Every resource listed here is current for MySQL 8.x and Aurora MySQL 3.x unless explicitly noted otherwise.

---

## The essential bookshelf: six books that cover 90% of what you need

The MySQL book landscape consolidated significantly with the release of several MySQL 8.x-targeted titles between 2020 and 2022. Start with these in roughly this order:

**1. *Efficient MySQL Performance* by Daniel Nichter (O'Reilly, 2022).** This is the single best book for a backend developer who wants to dramatically improve MySQL performance without becoming a full-time DBA. Nichter — a 20-year MySQL veteran, former Percona engineer, and current DBA at Block (Square/Cash App) managing thousands of MySQL instances — frames everything around **query response time as the "North Star" metric**. Covers query metrics, effective indexing, data access patterns, InnoDB row locking, replication, and sharding. Endorsed by the Oracle MySQL blog and reviewed by Vadim Tkachenko. At ~335 pages, it's dense and practical. Start here.

**2. *SQL Performance Explained* by Markus Winand (self-published, 2012).** Available free online at **use-the-index-luke.com**. Despite its age, this is the timeless reference on B-tree index anatomy, multi-column index design, JOIN optimization, and EXPLAIN plan interpretation. Database-agnostic with MySQL-specific annotations throughout. The indexing fundamentals haven't changed and won't change. Read this concurrently with Nichter's book to build a rock-solid indexing mental model.

**3. *High Performance MySQL*, 4th Edition by Silvia Botros and Jeremy Tinley (O'Reilly, 2021).** The spiritual successor to the legendary 3rd edition by Schwartz, Zaitsev, and Tkachenko. Rewritten from scratch by practitioners who ran MySQL at scale at Twilio and Etsy. Covers schema design, indexing, query optimization, server configuration, replication, high availability, scaling (Vitess, ProxySQL, sharding), cloud-hosted MySQL, and backup strategies. At **386 pages** it's more operationally focused and SRE-oriented than the 800-page 3rd edition, which went deeper on internals. Both editions remain valuable — the 3rd edition (2012) is still worth reading for its exhaustive treatment of MySQL internals, though some specifics are outdated for 8.x.

**4. *MySQL 8 Query Performance Tuning* by Jesper Wisborg Krogh (Apress, 2020).** A **900+ page** systematic query tuning methodology from a former Oracle MySQL Support engineer. Covers EXPLAIN, EXPLAIN ANALYZE, Visual Explain, Performance Schema, sys schema, optimizer behavior, histograms, hash joins, and lock analysis across 27 chapters. This is your reference manual for the tuning process itself. Krogh's companion book, ***MySQL Concurrency: Locking and Transactions*** **(Apress, 2021)**, is the definitive deep dive on gap locks, record locks, isolation levels, and diagnosing lock contention — exactly what you need for your stated goal of mastering isolation levels.

**5. *Database Internals* by Alex Petrov (O'Reilly, 2019).** Not MySQL-specific, but provides the theoretical foundation for understanding why InnoDB works the way it does. Part I covers B+Tree variants, buffer management, page structure, and storage engine architecture — all directly mapping to InnoDB's design. Part II covers distributed systems concepts relevant to understanding Aurora's storage layer. Endorsed by Marc Brooker (AWS Distinguished Engineer).

**6. *SQL Antipatterns* by Bill Karwin (Pragmatic Bookshelf, 2010).** Timeless database-agnostic guide to avoiding common schema design and query mistakes. Karwin is a well-known MySQL community contributor. Read this early to avoid embedding bad patterns in your Kotlin/Spring Boot data layer.

Two supplementary references worth having on hand: the ***MySQL Cookbook*, 4th Edition** by Sveta Smirnova and Alkin Tezuysal (O'Reilly, 2022) — 200+ practical recipes updated for MySQL 8.0 — and ***Mastering MySQL Administration*** by Aravindan and Ayyalusamy (2024), which covers MySQL 8.2 administration including Aurora and cloud deployments.

---

## Online courses worth your time

The course landscape for advanced MySQL is thinner than you'd expect. Most platforms skew toward beginner SQL. These stand out for performance and DBA depth:

**Percona Training** is the gold standard. Their instructor-led courses — particularly **"MySQL Training for Developers"** (2 days) and **"MySQL Training for Database Operations Specialists"** (2 days) — cover query optimization with EXPLAIN, composite indexes, InnoDB internals (redo log, undo, MVCC, adaptive hash index, change buffer), backup/recovery with XtraBackup, GTID replication, and monitoring with PMM. Instructors include Matthew Boehm, a former eBay/PayPal DBA who managed one of the world's largest MySQL installations. Contact Percona directly for scheduling and pricing.

**On Udemy**, the **"MySQL High Performance Tuning Guide"** by Lucian Oprea (4.5/5, updated January 2025) covers query optimizer internals, EXPLAIN analysis, InnoDB buffer pool configuration, isolation levels, and benchmarking — well-aligned with your goals. **"Becoming a Production MySQL DBA"** covers architecture, GTID replication, XtraBackup, and AWS migration for operational knowledge.

**On Pluralsight**, Pinal Dave's four-course MySQL track progresses through **MySQL Administration → Indexing for Performance → Query Optimization and Performance Tuning → Monitoring with Performance Schema**. Dave is a well-known database educator with practical, real-world focus.

**CMU 15-445 (Introduction to Database Systems)** by Professor Andy Pavlo is freely available on YouTube and provides the deepest understanding of *why* databases work the way they do. Key lectures for MySQL developers: B+Trees (#08), Buffer Pools (#04), Query Optimization (#15-16), and MVCC concurrency control. Not MySQL-specific, but the concepts map directly to InnoDB internals.

**For Aurora specifically**, the **AWS Skill Builder** offers a free 8-course "Amazon Aurora MySQL and Amazon RDS MySQL" curriculum covering Aurora architecture, replication, and performance optimization with Aurora-specific features like asynchronous key prefetch and hash joins.

**Oracle University** offers the official **"MySQL 8.0 for Database Administrators"** course and the **Oracle Certified Professional: MySQL 8.0 Database Administrator (1Z0-908)** certification — the industry-standard MySQL DBA credential if you want formal certification.

---

## The blogs and experts that define the MySQL knowledge ecosystem

The MySQL expert community is remarkably concentrated. A handful of blogs and authors produce the vast majority of deep technical content:

**Percona Blog** (percona.com/blog) is the single most prolific source of MySQL performance content. Key authors include Peter Zaitsev (co-founder, co-author of High Performance MySQL 3rd ed.), Vadim Tkachenko (CTO, performance benchmarking), and Sveta Smirnova (principal support engineer, author of *MySQL Troubleshooting*). Percona also publishes a free eBook, **"MySQL Performance Tuning: Strategies, Best Practices, and Tips"**, that consolidates their best content.

**Jeremy Cole's InnoDB internals blog series** (blog.jcole.us/innodb/) is the definitive resource for understanding InnoDB's physical storage. Cole — MySQL AB employee #14, later at Twitter, Google, and Shopify — documented the binary-level structure of InnoDB space files, B+Tree index pages, record formats, undo logging, and MVCC implementation. His **innodb_ruby** tool lets you explore InnoDB data files directly. This is essential reading for anyone who wants to truly understand what happens beneath the SQL layer.

**Yoshinori Matsunobu** (yoshinorimatsunobu.blogspot.com) leads MySQL at Meta/Facebook. His blog covers MySQL at massive scale, semi-synchronous replication internals, and the **MyRocks** storage engine (RocksDB for MySQL) that he created. **Mark Callaghan** (smalldatum.blogspot.com), also at Meta, writes detailed benchmarking analysis comparing InnoDB and RocksDB performance characteristics.

**Frédéric Descamps (lefred)** is Oracle's MySQL Community Manager and one of the most prolific MySQL conference speakers. His blog (lefred.be) and talks cover InnoDB primary keys, indexes, histograms, and MySQL architecture design patterns. His **"15 Tips for MySQL Performance Tuning"** talk is a good starting point.

**The official MySQL blog** has moved to blogs.oracle.com/mysql/ (archived content at dev.mysql.com/blog-archive/). **Planet MySQL** (planet.mysql.com) remains an active aggregator surfacing content from across the ecosystem. **J-F Gagné's MySQL blog** (jfg-mysql.blogspot.com) provides deep technical posts on binary logging, replication lag, and performance regressions.

For systems-level performance investigation, **Brendan Gregg's** work is relevant when MySQL-level tools aren't sufficient. He created **mysqld_qslower** (a BPF tool for tracing slow queries at the kernel level), presented at Percona Live on MySQL latency analysis, and his flame graph methodology is widely used for profiling mysqld processes. His books *Systems Performance* and *BPF Performance Tools* complement MySQL-specific knowledge.

The MySQL 8.0 Reference Manual itself (dev.mysql.com/doc/refman/8.0/en/) deserves specific mention. The most valuable chapters for your goals are **Chapter 10 (Optimization)**, **Chapter 17 (InnoDB Storage Engine)**, **Chapter 29 (Performance Schema)**, and **Chapter 30 (sys Schema)**.

---

## Conference talks and YouTube channels that accelerate learning

**Percona's YouTube channel** (@PerconaDatabase) hosts hundreds of Percona Live conference talks spanning query tuning, InnoDB internals, replication, and operational MySQL. Notable talks include Peter Zaitsev on InnoDB architecture, Gabriel Ciciliani on query tuning, and Jaime Crespo's dense 3-hour workshops on query optimization with MySQL 8.0. **Percona Live 2026** is scheduled for May 27–29 at the Computer History Museum in Mountain View.

**AWS re:Invent talks** are essential for Aurora understanding. The must-watch is **DAT408 (re:Invent 2023): "Deep dive into Amazon Aurora and its innovations"** by Grant McAlister (Senior Principal Engineer), covering storage architecture, I/O-Optimized, failover mechanisms, and Serverless v2. The **re:Invent 2025 DAT456** security deep dive explains Aurora's "sawed-in-half" architecture — the head node (query parser, planner) versus the replaced storage layer. Search YouTube for DAT405 (re:Invent 2018) for the foundational Aurora write processing internals talk.

**CMU Database Group** (@CMUDatabaseGroup) provides university-quality database systems lectures free on YouTube. Professor Andy Pavlo's lectures on B+Trees, buffer management, and MVCC provide the theoretical underpinning for everything you'll encounter in InnoDB.

**Oracle's MySQL team** publishes webinars at videohub.oracle.com, including the **"Top 10 Tips for MySQL Performance Tuning"** from MySQL Summit 2024. The **Deep Dive MySQL** podcast (@mysqlz on YouTube) by Kedar covers replication, high availability, ProxySQL, and InnoDB Cluster with a practical production focus.

---

## Practice environments and hands-on exercises

**Start with Docker.** Run `docker run --name mysql-test -e MYSQL_ROOT_PASSWORD=password -d -p 3306:3306 mysql:8.0` for an instant MySQL 8.x environment. For pre-loaded test data, use the **genschsa/mysql-employees** or **ac0mz/mysql8.0-employees** Docker images (the latter works on ARM64/M1 Macs).

The two canonical sample databases are the **Sakila database** (DVD rental store — 16 tables, good for learning JOINs and query patterns) and the **employees database** (~300,000 employee records, 2.8 million salary entries, 167 MB — large enough to see real performance differences from indexing decisions). Both are available at dev.mysql.com/doc/index-other.html. The employees database on GitHub (github.com/datacharmer/test_db) includes an integrated test suite.

For benchmarking, **sysbench** is the industry-standard tool used by Percona, Meta, and Oracle for MySQL performance testing. It generates OLTP test data of arbitrary size and runs various workloads (point selects, range scans, updates, TPC-C-like). Use it to measure the impact of your indexing and configuration changes quantitatively.

**Giuseppe Maxia's dbdeployer** (github.com/datacharmer/dbdeployer) lets you deploy multiple MySQL versions side-by-side for testing — useful for comparing behavior across versions. For structured exercises, w3resource.com offers MySQL performance optimization exercises specifically focused on EXPLAIN analysis, composite indexes, and covering indexes. **LabEx** (labex.io) provides 83+ browser-based MySQL challenges including query optimization and index management with automated verification.

---

## Aurora MySQL: understanding the architecture that changes everything

Aurora MySQL shares MySQL's SQL layer but replaces the storage engine with a fundamentally different distributed architecture. Understanding these differences is critical for making correct performance decisions.

**Start with the SIGMOD 2017 paper**: "Amazon Aurora: Design Considerations for High Throughput Cloud-Native Relational Databases" by Verbitski et al. The key insight is that Aurora moved the bottleneck from compute/storage to the **network** — only redo log records cross the network, not data pages. The storage layer maintains **6 copies across 3 AZs** with a write quorum of 4/6 and read quorum of 3/6. Data is segmented into **10 GB Protection Groups** enabling ~10-second repair times. The follow-up SIGMOD 2018 paper explains how Aurora avoids distributed consensus for commits. Accessible summaries exist at blog.acolyer.org (The Morning Paper) and distributed-computing-musings.com.

**The Plaid engineering blog post** — "Exploring performance differences between Amazon Aurora and vanilla MySQL" — is essential reading. It reveals a critical architectural difference: **Aurora shares a single undo log between the writer and all readers**. Long-running reader transactions can negatively impact *writer* performance in Aurora, which doesn't happen in vanilla MySQL. Mitigations include using binlog replicas for long-running analytical reads or exporting data to Parquet for heavy analysis.

The **AWS documentation page comparing Aurora MySQL v3 and MySQL 8.0 Community Edition** lists features unavailable in Aurora: resource groups, user-defined undo tablespaces, X plugin, and multisource replication. Aurora uses the `rds_superuser_role` instead of SUPER privilege, defaults to `mysql_native_password` (not `caching_sha2_password`), and provides special AWS integration roles for Lambda, S3, Comprehend, SageMaker, and Bedrock access.

Key operational differences to internalize: Aurora disables the doublewrite buffer (unnecessary with 6-way replication), fixes `innodb_flush_log_at_trx_commit=1`, disables change buffering, auto-scales storage to 256 TiB, provides sub-10ms replica lag via storage-level replication, and manages configuration through Parameter Groups rather than my.cnf. **Aurora Backtrack** — the ability to rewind a cluster to a specific point in time in minutes without creating a new cluster — is unique to Aurora and must be enabled at cluster creation.

---

## DBA operations: the monitoring and tooling stack

**For slow query analysis**, the workflow is: enable the slow query log (`slow_query_log=1`, `long_query_time=1` or lower), download logs from the AWS Console or CloudWatch Logs, then analyze with **pt-query-digest** from Percona Toolkit. This groups queries by fingerprint and ranks them by total execution time — revealing which queries consume the most database resources. Jeff Geerling's practical pt-query-digest tutorial and Percona's blog post on identifying high-load spots are good starting guides.

**Percona Toolkit** (latest: v3.7.1, December 2025) is the Swiss Army knife for MySQL operations. The essential tools for an Aurora MySQL developer are pt-query-digest (slow query analysis), pt-online-schema-change (non-blocking ALTER TABLE when Aurora's online DDL is insufficient), pt-duplicate-key-checker (finding redundant indexes), and pt-kill (automated query management). Install it early and practice with each tool.

**Performance Schema and sys schema** provide real-time instrumentation of MySQL internals. Performance Schema (Chapter 29 of the MySQL manual) captures statement execution statistics, wait events, and I/O metrics. The sys schema (Chapter 30) provides human-readable views on top of Performance Schema data. In Aurora, **Performance Schema is disabled by default** due to overhead — enable it via Parameter Groups when you need deep diagnostics. Note that AWS **Performance Insights is reaching end-of-life on June 30, 2026**, being replaced by **CloudWatch Database Insights** (Advanced mode with 15-month retention and execution plan support).

**Percona Monitoring and Management (PMM)** is an open-source Grafana-based observability platform with dedicated Aurora MySQL dashboards and Query Analytics (QAN) comparable to Performance Insights. It supports both slow query log and Performance Schema as metric sources. For teams wanting deeper analytics than the AWS Console provides, PMM is the standard open-source choice. The Remitly engineering blog post "Tuning Aurora MySQL for real-world workloads — Part 1: Making it observable" (February 2026) provides an excellent practical guide to combining CloudWatch, Performance Insights, slow query log, and Performance Schema for comprehensive Aurora observability — including query tagging via SQL comments for traceability.

For **backup and recovery** in Aurora, understand the layered options: continuous incremental backups (1–35 day retention, no performance impact), point-in-time recovery (within 5 minutes of latest restorable time), manual snapshots (up to 100, don't expire), database cloning (copy-on-write, faster than snapshot restore), Aurora Backtrack (rewind without new cluster), and Aurora Global Database for cross-region DR. The AWS Database Blog post "How to choose the best disaster recovery option for your Amazon Aurora MySQL cluster" (updated August 2025) covers all options with RTO/RPO tradeoffs.

For **user management**, MySQL 8.0 introduced proper roles (`CREATE ROLE`, `GRANT role TO user`, `SET DEFAULT ROLE`). Aurora MySQL 3.x adds the `rds_superuser_role` and restricts direct modification of mysql schema tables. Percona's "Deep dive into roles in MySQL 8.0" blog post covers the role system comprehensively.

## Conclusion

The path from beginner to mastery follows a clear progression: **indexing fundamentals** (Winand's *Use The Index, Luke*) → **developer-focused performance** (Nichter's *Efficient MySQL Performance*) → **systematic query tuning** (Krogh's 900-page tuning methodology) → **operational MySQL at scale** (Botros/Tinley's *High Performance MySQL* 4th ed.) → **InnoDB internals** (Jeremy Cole's blog series) → **Aurora architecture** (the SIGMOD papers and Plaid's blog). Layer in Percona Toolkit practice, Performance Schema fluency, and Aurora-specific operational knowledge throughout.

The MySQL expert community is small enough that you can realistically follow every major voice — Percona's blog, Jeremy Cole, Yoshinori Matsunobu, Frédéric Descamps, and the official MySQL blog cover nearly all significant developments. The most underappreciated resource is the MySQL 8.0 Reference Manual itself, particularly the Optimization and InnoDB chapters, which contain depth that no third-party resource fully replicates.