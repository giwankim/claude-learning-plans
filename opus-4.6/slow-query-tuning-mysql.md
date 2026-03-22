---
title: "MySQL Slow Query Tuning on Aurora"
category: "Database"
description: "Production playbook for finding, analyzing, and fixing slow queries on Aurora MySQL 3.x and 2.x"
---

# Production playbook for MySQL query tuning on Aurora MySQL

**Aurora MySQL gives you a powerful but distinct set of knobs for finding, analyzing, and fixing slow queries.** This playbook is a practitioner's reference — covering every stage from discovering problematic queries through measuring the impact of your fixes. It targets Aurora MySQL 3.x (MySQL 8.0 compatible), with callouts for Aurora MySQL 2.x (MySQL 5.7 compatible) where behavior differs. Every recommendation here has been validated against Aurora's managed-service constraints, including the absence of `SUPER` privilege and the shared-storage replication model.

---

## 1. Finding slow queries: four complementary signals

You need multiple data sources because no single one tells the whole story. The slow query log captures individual query executions with timing. Performance Insights gives you aggregate load attribution. The `performance_schema` provides in-memory counters. CloudWatch gives you cluster-level trends.

### Slow query log configuration

The slow query log is **disabled by default**. Enable it through your DB cluster parameter group — all parameters below are dynamic and take effect without a reboot:

| Parameter | Default | Recommended | Notes |
|---|---|---|---|
| `slow_query_log` | `0` | `1` | Master switch |
| `long_query_time` | `10` | `1.0` (start here, tune to `0.1`–`0.5`) | Supports microsecond precision |
| `log_output` | `FILE` | `FILE` | Required for CloudWatch export; `TABLE` mode prevents `TRUNCATE` — must use `CALL mysql.rds_rotate_slow_log` |
| `log_queries_not_using_indexes` | `0` | `1` in staging; use cautiously in prod | Can generate enormous volume |
| `log_slow_extra` | `0` | `1` (Aurora MySQL 3.x only) | Adds `Rows_affected`, `Bytes_sent`, `Tmp_disk_tables` |

Enable CloudWatch Logs export for durable, queryable storage:

```bash
aws rds modify-db-cluster \
  --db-cluster-identifier my-cluster \
  --cloudwatch-logs-export-configuration '{"EnableLogTypes":["slowquery"]}'
```

Logs appear in `/aws/rds/cluster/<cluster-name>/slowquery`. **Aurora retains log files for only 24 hours on the instance** (or until 15% of local storage is consumed), so CloudWatch export is essential for any analysis beyond a day.

Download logs for offline analysis via the RDS API:

```bash
aws rds download-db-log-file-portion \
  --db-instance-identifier my-aurora-instance \
  --log-file-name slowquery/mysql-slowquery.log.2026-03-22.08 \
  --output text > slow.log
```

### Performance Insights: load-based query discovery

Performance Insights is the single most effective tool for identifying which queries consume the most database capacity. Its central metric is **DB Load**, measured in Average Active Sessions (AAS) — the number of sessions actively executing or waiting at any given second. When AAS exceeds your vCPU count, you have CPU contention.

PI is enabled by default on new Aurora instances. The free tier retains **7 days** of data; paid retention extends to 24 months. The key workflow: open PI, select a time range with elevated load, then examine the **Top SQL** tab to see queries ranked by their contribution to DB load.

The wait event breakdown tells you *why* queries are slow:

- **`cpu`** — sessions actively running or waiting for CPU. Optimize queries, scale up, or add read replicas.
- **`io/table/sql/handler`** — InnoDB reading/writing data pages. Check indexes, increase buffer pool.
- **`io/aurora_redo_log_flush`** — write durability flush to Aurora storage. Batch writes in transactions.
- **`io/aurora_respond_to_client`** — network transfer of results to the client. Reduce result set sizes.
- **`synch/cond/innodb/row_lock_wait`** — InnoDB row lock contention. Reduce transaction scope.
- **`synch/rwlock/innodb/index_tree_rw_lock`** — B-tree index contention from hot-spot writes.

For programmatic access, the PI API's `GetResourceMetrics` endpoint lets you pull top-SQL-by-load data into custom dashboards:

```bash
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier db-ABCDEFGHIJKLMNOP \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --period-in-seconds 300 \
  --metric-queries '[{
    "Metric": "db.load.avg",
    "GroupBy": {"Group": "db.sql_tokenized", "Limit": 10}
  }]'
```

### performance_schema and sys schema views

When Performance Insights is enabled, it **automatically enables and manages `performance_schema`** with optimal instrument configuration. If PI is off, `performance_schema` defaults to off and requires a reboot to toggle. Avoid enabling it on T-class instances — it can cause out-of-memory conditions.

The `sys` schema is pre-installed on both Aurora MySQL 2.x and 3.x. The most actionable views for query tuning:

```sql
-- Top queries by total latency
SELECT * FROM sys.statement_analysis ORDER BY total_latency DESC LIMIT 10\G

-- Queries doing full table scans
SELECT * FROM sys.statements_with_full_table_scans ORDER BY no_index_used_count DESC LIMIT 10\G

-- Queries in the 95th percentile of runtime
SELECT * FROM sys.statements_with_runtimes_in_95th_percentile\G

-- Unused indexes (candidates for removal — data valid only since last restart)
SELECT * FROM sys.schema_unused_indexes WHERE object_schema NOT IN ('mysql','sys','performance_schema');

-- Redundant indexes
SELECT * FROM sys.schema_redundant_indexes\G
```

### CloudWatch metrics for cluster-level trends

Aurora publishes query-specific CloudWatch metrics that standard RDS MySQL does not:

- **`SelectLatency` / `DMLLatency`** — average latency per query type (milliseconds)
- **`SelectThroughput` / `DMLThroughput`** — queries per second by type
- **`BufferCacheHitRatio`** — target **>99%**; below 95% indicates serious cache pressure
- **`Deadlocks`** / **`RowLockTime`** — contention indicators
- **`AuroraReplicaLag`** — keep below 100ms for read consistency

Set alarms on `SelectLatency` and `BufferCacheHitRatio` as early warning signals:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "AuroraHighSelectLatency" \
  --metric-name SelectLatency --namespace AWS/RDS \
  --statistic Average --period 300 --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:db-alerts \
  --dimensions Name=DBClusterIdentifier,Value=my-cluster
```

The **audit log** (`server_audit_logging`) records which queries ran and by whom, but **does not capture execution time, rows examined, or lock time**. It is useful for security and compliance, not performance tuning.

---

## 2. Analyzing slow queries with EXPLAIN and tooling

### EXPLAIN, EXPLAIN ANALYZE, and format options

Regular `EXPLAIN` shows the optimizer's *estimated* plan without executing the query. On Aurora MySQL 3.x, you also have **`EXPLAIN ANALYZE`**, which actually runs the query and reports real timing alongside estimates — invaluable for catching cases where the optimizer's row count guesses diverge wildly from reality.

```sql
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 42 AND created_at > '2025-01-01';
```

Output (TREE format, the only format EXPLAIN ANALYZE supports):

```
-> Filter: (orders.created_at > '2025-01-01')  (cost=4.55 rows=10)
   (actual time=0.464..22.767 rows=15 loops=1)
    -> Index lookup on orders using idx_customer (customer_id=42)
       (cost=4.55 rows=10)
       (actual time=0.450..19.988 rows=15 loops=1)
```

Each node shows **estimated cost and rows** alongside **actual time (first row..all rows in ms) and actual rows**. The `loops` count tells you how many times a nested-loop iterator was invoked.

**Caution**: EXPLAIN ANALYZE executes the query. Never use it on expensive DML against production writers. For estimation only, use `EXPLAIN FORMAT=TREE` (same tree output, no execution).

The traditional tabular EXPLAIN remains the most commonly referenced format. The columns that matter most for tuning:

- **`type`** — access method, ranked best to worst: `system` > `const` > `eq_ref` > `ref` > `range` > `index` > **`ALL`** (full table scan)
- **`key`** — which index the optimizer chose; `NULL` means no index
- **`key_len`** — bytes of composite index used; higher means more index columns participate
- **`rows`** — estimated rows to examine; compare against `rows_sent` for efficiency
- **`Extra`** — critical flags: **`Using index`** (covering index, best case), `Using index condition` (ICP pushdown), **`Using filesort`** (sort not resolved by index), **`Using temporary`** (temp table created)

### pt-query-digest: compatible with Aurora, with one critical workaround

**pt-query-digest is fully compatible with Aurora MySQL slow query logs**, but you must know about one bug. Aurora occasionally logs absurd values for `Query_time` and `Lock_time` — specifically **`18446744073709.550781` seconds** (an unsigned 64-bit integer underflow). Even a tiny fraction of corrupted entries (Percona documented 111 out of 5.13 million queries) will completely skew aggregate statistics.

**The fix is the `--attribute-value-limit` flag:**

```bash
pt-query-digest --group-by fingerprint --order-by Query_time:sum \
  --attribute-value-limit=4294967296 slow-query.log
```

This caps any attribute value at ~4.3 billion, discarding the corrupted entries. With this flag, pt-query-digest produces accurate profiles. The output is a ranked report showing each query fingerprint's total execution time, call count, average and 95th-percentile latency, rows examined, and rows sent. Use `--explain` with a DSN to automatically run EXPLAIN for each query:

```bash
pt-query-digest --explain h=aurora-writer.endpoint.rds.amazonaws.com,u=admin,p=pass \
  --attribute-value-limit=4294967296 --limit=20 slow-query.log > report.txt
```

Aurora's slow log format is standard MySQL — no parsing issues. One caveat: if you download logs from CloudWatch Logs rather than the RDS API, the export may prepend metadata to log lines; strip these before feeding to pt-query-digest.

### Other Percona Toolkit tools on Aurora

**pt-duplicate-key-checker**, **pt-index-usage**, and **pt-visual-explain** are **fully compatible** — they're read-only tools that require only SELECT privileges. pt-duplicate-key-checker is particularly useful: it detects exact-duplicate and left-prefix-redundant indexes and outputs ready-to-use `DROP INDEX` statements.

Tools that *modify* data face Aurora's lack of `SUPER` privilege. The key workarounds:

| Tool | Issue | Fix |
|---|---|---|
| pt-online-schema-change | Cannot create triggers with binlog enabled | Set `log_bin_trust_function_creators=1` in parameter group; use `--recursion-method none` |
| gh-ost | Cannot change `binlog_format` | Use `--assume-rbr --allow-on-master`; set `aurora_enable_repl_bin_log_filtering=0` |
| pt-table-checksum | Cannot set `binlog_format=STATEMENT` | Aurora 3: grant `SYSTEM_VARIABLES_ADMIN`; Aurora 2: set globally (requires reboot) |

---

## 3. Tuning: indexes, rewrites, and Aurora-specific features

### Index design that matters

**Composite index column order** is the highest-leverage tuning decision. The rule: **equality columns first, range columns last.** A composite index on `(customer_id, status, created_at)` is optimal for `WHERE customer_id = ? AND status = ? AND created_at BETWEEN ? AND ?` because both equality predicates narrow the B-tree before the range scan begins. Reversing the order (putting `created_at` first) would waste the index.

**Covering indexes** are especially valuable on Aurora because data pages live on network-attached storage across 3 AZs. Every table lookup that isn't satisfied from the buffer cache incurs a network round-trip to the storage layer. An `Extra: Using index` result in EXPLAIN means the query reads only from the index — zero data page fetches.

```sql
-- Covering index for a frequent query
CREATE INDEX idx_covering ON orders(customer_id, status, total);

-- This query reads only from the index:
SELECT customer_id, status, total FROM orders WHERE customer_id = 12345 AND status = 'completed';
```

**Prefix indexes** (`column(N)`) reduce index size for long VARCHAR columns but cannot be used for ORDER BY or as covering indexes. Determine optimal prefix length by comparing selectivity:

```sql
SELECT
  COUNT(DISTINCT LEFT(email, 10)) / COUNT(*) AS prefix_10,
  COUNT(DISTINCT LEFT(email, 20)) / COUNT(*) AS prefix_20,
  COUNT(DISTINCT email) / COUNT(*) AS full_selectivity
FROM users;
```

**Functional indexes** (Aurora MySQL 3 / MySQL 8.0+) let you index expressions directly — `CREATE INDEX idx ON users((LOWER(email)))` — eliminating the need to rewrite queries that apply functions to indexed columns.

### High-impact query rewriting patterns

**Keyset pagination instead of OFFSET.** `LIMIT 20 OFFSET 100000` forces MySQL to read and discard 100,000 rows. Replace with cursor-based pagination: `WHERE id > :last_seen_id ORDER BY id LIMIT 20`. This uses the primary key index to skip directly.

**Avoid functions on indexed columns in WHERE clauses.** `WHERE YEAR(created_at) = 2025` prevents index usage. Rewrite as `WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01'`.

**Replace UNION with UNION ALL** unless you explicitly need deduplication. UNION triggers a sort-and-dedup pass that can be extremely expensive on large result sets.

**Rewrite OR across different columns as UNION ALL.** `WHERE customer_id = 100 OR status = 'pending'` cannot use a single index efficiently. Two separate queries joined by UNION ALL each use their own optimal index.

**Use EXISTS over IN for correlated subqueries with large outer tables.** EXISTS short-circuits after finding the first match. MySQL 8.0's optimizer can auto-transform `IN (subquery)` into semi-joins, but explicit JOINs with derived tables give you more control over execution order.

### Aurora-specific optimizations

**Parallel Query** pushes filtering and aggregation down to Aurora's distributed storage nodes. It benefits analytical queries scanning millions of rows of cold data (not in buffer cache). Enable it with `aurora_parallel_query = ON` in the parameter group, and verify usage in EXPLAIN output: `Using parallel query (X columns, Y filters, Z exprs)`. It does not work with I/O-Optimized storage, T-class instances, or COMPRESSED/REDUNDANT row formats.

**Query cache is removed in Aurora MySQL 3.x**, following MySQL 8.0's deprecation. Aurora MySQL 2.x had a rewritten, improved query cache that avoided the mutex contention of community MySQL's version. If you're upgrading from 2.x to 3.x, plan to implement application-level caching (ElastiCache/Redis) and monitor `SelectLatency` after the upgrade.

**Read replicas** share the same storage volume, which means replica lag is typically **single-digit milliseconds** rather than the seconds-to-minutes common with binlog replication. Route read traffic to the `cluster-ro` reader endpoint. Create custom endpoints to isolate analytical workloads from OLTP reads. You can run up to **15 Aurora Replicas** per cluster.

### Safely adding indexes in production

For adding secondary indexes, you have four options on Aurora. Here's when to use each:

| Scenario | Recommended tool | Why |
|---|---|---|
| Add index, table < 10 GB | `ALTER TABLE ... ADD INDEX ..., ALGORITHM=INPLACE, LOCK=NONE` | Native online DDL; no external tooling needed |
| Add index, table > 10 GB, write-heavy | **gh-ost** | No triggers (unlike pt-osc); fully pausable and throttleable; lighter write amplification |
| Add index, table > 10 GB, moderate writes | **pt-online-schema-change** | Simpler setup; use `--recursion-method none` and `log_bin_trust_function_creators=1` |
| Add nullable column (Aurora 3.x) | `ALTER TABLE ... ADD COLUMN ..., ALGORITHM=INSTANT` | Metadata-only change; milliseconds regardless of table size |
| Change column type | gh-ost or pt-osc | Online DDL uses COPY algorithm for type changes; external tools are safer |

**Aurora Fast DDL** (Aurora 2.x only, required lab mode) is replaced by MySQL 8.0's `ALGORITHM=INSTANT` in Aurora 3.x. If upgrading from 2.x, resolve any pending Fast DDL operations with `OPTIMIZE TABLE` first.

Always **specify `ALGORITHM` and `LOCK` explicitly** in ALTER TABLE statements. If the requested level isn't supported, the statement fails rather than silently escalating:

```sql
ALTER TABLE orders ADD INDEX idx_customer_date (customer_id, created_at),
  ALGORITHM=INPLACE, LOCK=NONE;
```

For gh-ost on Aurora specifically:

```bash
gh-ost --alter="ADD INDEX idx_customer_date (customer_id, created_at)" \
  --database=mydb --table=orders \
  --host=writer-endpoint.rds.amazonaws.com \
  --assume-rbr --allow-on-master \
  --user=admin --ask-pass \
  --chunk-size=1000 --max-load=Threads_running=25 \
  --execute
```

**Before any production DDL**: create an Aurora clone (`restore-db-cluster-to-point-in-time` with `--restore-type copy-on-write`), run the DDL on the clone, and measure duration and impact. Always take a manual snapshot as your rollback safety net.

---

## 4. Measuring whether your changes actually worked

### Before/after EXPLAIN comparison

Capture EXPLAIN output before and after the change in a structured format. The metrics that demonstrate improvement:

| Metric | Before (bad) | After (good) | What it means |
|---|---|---|---|
| `type` | `ALL` | `ref` or `range` | Full table scan eliminated |
| `key` | `NULL` | `idx_customer_date` | Index now selected |
| `key_len` | `NULL` | `8` | Both composite index columns used |
| `rows` | `1,500,000` | `342` | 99.98% fewer rows examined |
| `Extra` | `Using where` | `Using where; Using index` | Covering index engaged |

### Handler_read_* variables: per-query proof

The most granular way to prove an index change works is to measure handler reads for a single query execution:

```sql
FLUSH STATUS;
SELECT * FROM orders WHERE customer_id = 12345 AND created_at > '2025-01-01';
SHOW SESSION STATUS LIKE 'Handler_read%';
```

The variables that tell the story:

- **`Handler_read_key`** — rows found via index lookup. **High = good.** This is what proper indexing produces.
- **`Handler_read_next`** — rows read in index order (range scan). Expected and normal for range queries.
- **`Handler_read_rnd_next`** — rows read by scanning the data file sequentially. **High = bad — full table scan.** When this equals your table's row count, you have no useful index.
- **`Handler_read_rnd`** — random-position reads after a sort. Indicates filesort operations.

A successful index addition looks like this: `Handler_read_rnd_next` drops from 1,500,001 (full scan of 1.5M rows) to 0, while `Handler_read_key = 1` and `Handler_read_next = 341` (342 rows via efficient range scan). These variables work identically on Aurora as on standard MySQL — they operate at the server layer above the storage engine.

### Performance Insights before/after comparison

PI groups queries by SQL digest, making it straightforward to compare the same query across time periods. Use the PI API to pull metrics for identical time windows (same day-of-week, same hour) before and after your change:

```bash
# Before: Monday 8-10 AM before index change
aws pi get-resource-metrics --service-type RDS \
  --identifier db-ABCDEFGHIJKLMNOP \
  --start-time 2026-03-16T08:00:00Z --end-time 2026-03-16T10:00:00Z \
  --period-in-seconds 300 \
  --metric-queries '[{"Metric":"db.load.avg","GroupBy":{"Group":"db.sql_tokenized","Limit":10},
    "Filter":{"db.sql_tokenized.id":"ABC123TOKENIZEDID"}}]'

# After: Monday 8-10 AM after index change (one week later)
aws pi get-resource-metrics --service-type RDS \
  --identifier db-ABCDEFGHIJKLMNOP \
  --start-time 2026-03-23T08:00:00Z --end-time 2026-03-23T10:00:00Z \
  --period-in-seconds 300 \
  --metric-queries '[{"Metric":"db.load.avg","GroupBy":{"Group":"db.sql_tokenized","Limit":10},
    "Filter":{"db.sql_tokenized.id":"ABC123TOKENIZEDID"}}]'
```

Compare the query's AAS contribution, per-call latency, and rows examined per call across the two windows.

### pt-query-digest before/after reports

Generate time-filtered reports and compare the same query fingerprint hash across both:

```bash
pt-query-digest --since '2026-03-16 08:00:00' --until '2026-03-16 10:00:00' \
  --attribute-value-limit=4294967296 slow_before.log > digest_before.txt

pt-query-digest --since '2026-03-23 08:00:00' --until '2026-03-23 10:00:00' \
  --attribute-value-limit=4294967296 slow_after.log > digest_after.txt
```

Match queries by their Query ID (fingerprint hash, e.g., `0x558CAEF5F387E929`) and compare: avg/95th-percentile execution time, rows examined per call, and the variance-to-mean ratio (V/M). There is no built-in diff mode — you compare manually or script it by parsing the text output.

### Statistical rigor in measurement

**Never rely on averages alone.** Use p50, p95, and p99 percentiles to understand the full latency distribution. pt-query-digest reports the 95th percentile by default; PI reports average per call.

**Compare same time-of-day, same day-of-week** to control for cyclical load patterns. Monday morning traffic looks nothing like Sunday midnight. Collect at least one full business cycle (one week) of data before declaring success.

**Run `ANALYZE TABLE` immediately after creating an index** to update cardinality statistics. MySQL 8.0 (Aurora 3.x) has no persistent query plan cache — each query is re-optimized from scratch — so the optimizer can use a new index immediately after creation, but only if it has accurate statistics to evaluate it.

**Wait 2–4 hours of representative production traffic** before concluding that an index helped. Ideally, compare a full week of before/after data to account for variance.

---

## 5. Operational best practices for continuous query health

### Building a monitoring pipeline

The most effective pipeline routes slow query logs to CloudWatch, with periodic pt-query-digest analysis for deeper insight:

1. Enable slow log export to CloudWatch (as described above)
2. Create a CloudWatch Logs metric filter to count slow queries:

```bash
aws logs put-metric-filter \
  --log-group-name /aws/rds/cluster/my-cluster/slowquery \
  --filter-name SlowQueryCount --filter-pattern "Query_time" \
  --metric-transformations metricName=SlowQueryCount,metricNamespace=Custom/Aurora,metricValue=1
```

3. Use CloudWatch Logs Insights for ad-hoc analysis:

```
parse @message /Query_time: (?<qt>[\d.]+)\s+Lock_time: (?<lt>[\d.]+)\s+Rows_sent: (?<rs>\d+)\s+Rows_examined: (?<re>\d+)/
| filter qt > 1
| stats count(*) as cnt, avg(qt) as avg_time, pct(qt, 95) as p95 by bin(1h)
```

4. Schedule a Lambda function to pull PI data via the API and push it to a Grafana dashboard or S3 for long-term trend analysis.

### Alerting on query regression

Set CloudWatch alarms on `SelectLatency` and `DMLLatency` at **baseline + 2× standard deviation**. Complement with alarms on:

- `BufferCacheHitRatio` < 95% (cache pressure)
- `CPUUtilization` > 80% sustained
- `Deadlocks` > 0 (spike detection)
- `AuroraReplicaLag` > 100ms (stale reads)
- `RollbackSegmentHistoryListLength` > 1,000,000 (long-running transactions blocking purge)

For per-query regression detection, a scheduled Lambda querying the PI API can track week-over-week latency changes for your top 20 queries and fire an SNS alert when any query's p95 latency increases by more than 50%.

### Index maintenance: detecting waste

**Unused indexes** waste write throughput — every INSERT, UPDATE, and DELETE must maintain every index. Detect them with `sys.schema_unused_indexes` after the instance has been running under representative load for at least one week (data resets on restart, so check uptime first).

**MySQL 8.0 invisible indexes** are the safest removal pattern:

```sql
-- Step 1: Make the index invisible (optimizer ignores it, but it's still maintained)
ALTER TABLE orders ALTER INDEX idx_suspect INVISIBLE;

-- Step 2: Monitor for 1-2 weeks for query regressions

-- Step 3: If no regressions, drop it
ALTER TABLE orders DROP INDEX idx_suspect;

-- Rollback if needed:
ALTER TABLE orders ALTER INDEX idx_suspect VISIBLE;
```

Run `pt-duplicate-key-checker` quarterly to catch left-prefix-redundant indexes (e.g., a standalone index on `(A)` when `(A, B, C)` already exists):

```bash
pt-duplicate-key-checker --host=aurora-writer.endpoint.rds.amazonaws.com \
  --user=admin --ask-pass --databases=mydb
```

Run `ANALYZE TABLE` after bulk loads, large deletes, index changes, or major version upgrades — and periodically (weekly) on volatile tables — to keep optimizer statistics fresh.

---

## Conclusion

The most impactful practices in this playbook are not the exotic ones. **Enabling the slow query log with CloudWatch export, using Performance Insights to identify top queries by load, and designing composite indexes with equality columns first and range columns last** will resolve the majority of Aurora MySQL performance issues. pt-query-digest works well with Aurora once you apply the `--attribute-value-limit` workaround for the timing overflow bug, and gh-ost is the preferred schema migration tool for large tables due to its trigger-free design. The operational discipline that separates good teams from great ones is continuous monitoring — tracking query digests week-over-week, using invisible indexes to safely prune waste, and running `ANALYZE TABLE` to keep the optimizer honest. Aurora's shared-storage architecture makes covering indexes and buffer cache hit ratios more consequential than on local-storage MySQL — every uncached data page fetch crosses the network to a remote storage node, making index-only scans disproportionately valuable.