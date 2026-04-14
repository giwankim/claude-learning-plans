---
title: "Flyway Database Migrations"
category: "Data & Messaging"
description: "Production Flyway migrations with Spring Boot, Kotlin, and Aurora MySQL"
---

# Flyway database migrations with Spring Boot, Kotlin, and Aurora MySQL

**Flyway combined with Spring Boot's auto-configuration provides a robust, version-controlled approach to managing Aurora MySQL schema evolution—but safe production usage demands careful attention to migration design, deployment strategy, and zero-downtime patterns.** This guide covers the full lifecycle: from initial Kotlin/Gradle setup through CI/CD integration and battle-tested patterns for modifying live tables with millions of rows. The core principle threading through every section is the expand-and-contract pattern—making only additive changes at deploy time, deferring destructive changes, and ensuring the schema always supports both the current and previous application version simultaneously.

---

## How Flyway works under the hood

Flyway manages database evolution through **versioned migration scripts applied in strict order**, tracked via a metadata table called `flyway_schema_history`. On each application startup (or CLI invocation), Flyway scans configured locations for migration files, compares them against the history table, validates checksums of already-applied migrations, and applies any pending ones in version order.

Three migration types exist. **Versioned migrations** (`V1__Create_users_table.sql`) run exactly once, in version order. **Repeatable migrations** (`R__Refresh_views.sql`) re-apply whenever their checksum changes, running after all versioned migrations. **Undo migrations** (`U1__Undo_create_users.sql`) reverse a versioned migration but require the paid Flyway Teams edition.

The naming convention is strict:

```
V2.1__Add_users_table.sql
│ │   │              │
│ │   └──────────────── Description (double underscore __ separator)
│ └──────────────────── Version (dots or underscores as separators)
└────────────────────── Prefix: V = versioned, R = repeatable, U = undo
```

The `flyway_schema_history` table stores each migration's version, description, CRC32 checksum, execution time, and success status. **Checksum validation is critical**: if someone modifies an already-applied migration file, Flyway detects the mismatch and refuses to proceed, forcing an explicit `flyway repair` to realign. This prevents silent schema drift.

Spring Boot auto-configures Flyway when `flyway-core` appears on the classpath. The `FlywayAutoConfiguration` runs after DataSource configuration but before JPA/Hibernate initialization, ensuring the schema is ready before any entity manager touches the database. **Always set `spring.jpa.hibernate.ddl-auto=none`** when using Flyway—never let Hibernate manage schema alongside Flyway.

---

## Kotlin and Gradle setup for Spring Boot

The essential `build.gradle.kts` configuration requires both `flyway-core` and `flyway-mysql`—the latter is mandatory for MySQL 8+ and Aurora MySQL, and omitting it produces the cryptic error "No Flyway database plugin found to handle jdbc:mysql":

```kotlin
plugins {
    id("org.springframework.boot") version "3.4.0"
    id("io.spring.dependency-management") version "1.1.6"
    kotlin("jvm") version "1.9.25"
    kotlin("plugin.spring") version "1.9.25"
    id("org.flywaydb.flyway") version "12.1.0" // Optional: Gradle plugin
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.flywaydb:flyway-core")
    implementation("org.flywaydb:flyway-mysql") // Required for Aurora MySQL
    runtimeOnly("com.mysql:mysql-connector-j")
    testImplementation("org.testcontainers:mysql:1.19.8")
}
```

SQL migrations go in `src/main/resources/db/migration/`. For complex data transformations, Kotlin-based migrations extend `BaseJavaMigration` and live in the `db.migration` package under `src/main/kotlin`:

```kotlin
package db.migration

import org.flywaydb.core.api.migration.BaseJavaMigration
import org.flywaydb.core.api.migration.Context

class V3__Migrate_legacy_data : BaseJavaMigration() {
    override fun migrate(context: Context) {
        val stmt = context.connection.createStatement()
        // Complex transformation logic with full JDBC access
        stmt.execute("UPDATE users SET display_name = full_name WHERE display_name IS NULL")
    }
}
```

**Use SQL migrations for ~90% of cases** (DDL, simple DML, indexes). Reserve Kotlin migrations for conditional logic, batch processing, BLOB handling, or transformations requiring programmatic control. Airbyte's engineering team writes all migrations in Java for testability—a valid approach when data transformations dominate schema changes.

### Versioning strategies that prevent team conflicts

For teams larger than 3-4 developers, **timestamp-based versioning** virtually eliminates merge conflicts: `V20260317_1030__Add_users_table.sql`. This requires `out-of-order: true` since timestamps from feature branches interleave. An alternative is reserved version blocks per team (`V1000-1099` for Team A, `V1100-1199` for Team B). A shell script automates timestamp generation:

```bash
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d%H%M%S)
echo "-- Migration: $1" > "src/main/resources/db/migration/V${TIMESTAMP}__${1}.sql"
```

---

## Local development versus production configuration

The divergence between environments is significant. Local development prioritizes speed and flexibility; production demands safety and control.

**Local configuration** (`application-local.yml`):
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/myapp?useSSL=false&allowPublicKeyRetrieval=true
    username: root
    password: localpassword
  flyway:
    enabled: true
    baseline-on-migrate: true
    out-of-order: true          # Essential for team development
    clean-disabled: false        # Allow clean in local dev
```

**Production configuration** (`application-prod.yml`):
```yaml
spring:
  datasource:
    url: jdbc:mysql://aurora-cluster.cluster-xxxx.us-east-1.rds.amazonaws.com:3306/myapp
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
  flyway:
    enabled: false               # Migrations run externally, not on startup
    out-of-order: false          # Strict ordering
    clean-disabled: true         # NEVER allow clean in production
    validate-on-migrate: true
```

### Should Flyway run on application startup in production?

This is heavily debated. **Running on startup** is simpler—Flyway's built-in locking prevents concurrent execution, and code-schema sync is guaranteed. However, the arguments against are compelling for Kubernetes environments: multiple replicas race for the migration lock, causing cascading startup delays; a long-running ALTER TABLE blocks all pods from starting; failed migrations produce failed deployments with no easy recovery; and MySQL's lack of transactional DDL means partial states are possible.

**The recommended production pattern separates migration from deployment.** Run Flyway validate on startup (to confirm schema matches expectations) and execute migrations as a dedicated pre-deployment step. A Spring Boot configuration achieves this:

```kotlin
@Configuration
class FlywayConfig {
    @Bean
    @Profile("!prod")
    fun migrateStrategy(): FlywayMigrationStrategy = FlywayMigrationStrategy { it.migrate() }
    
    @Bean
    @Profile("prod")
    fun validateStrategy(): FlywayMigrationStrategy = FlywayMigrationStrategy { it.validate() }
}
```

### Kubernetes deployment patterns for EKS

The most robust approach uses **Helm pre-upgrade hooks** to run a Kubernetes Job before the rolling update begins:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: "{{ .Release.Name }}-db-migrate-{{ .Release.Revision }}"
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: flyway
        image: your-ecr/myapp-migrations:latest
        env:
        - name: FLYWAY_URL
          value: "jdbc:mysql://aurora-writer:3306/mydb"
        - name: FLYWAY_USER
          valueFrom:
            secretKeyRef: { name: db-credentials, key: username }
        - name: FLYWAY_PASSWORD
          valueFrom:
            secretKeyRef: { name: db-credentials, key: password }
```

This guarantees: migrations run exactly once (single Job, `parallelism=1`); old pods serve traffic during migration; new pods start only after the Job succeeds; if migration fails, Helm upgrade fails and no new pods deploy. The init container alternative works but causes N-1 replicas to wait on Flyway's lock—less efficient than the Job approach.

For local development, **Docker Compose with MySQL 8.0** provides the fastest feedback loop, while **Testcontainers** ensures integration tests run against the same engine as production. Always connect Flyway to Aurora's **writer endpoint**—using reader endpoints will cause migration failures.

---

## Zero-downtime schema changes on live Aurora MySQL tables

The expand-and-contract pattern is the foundation of every safe schema change. It decomposes potentially destructive changes into backward-compatible steps across multiple deployments.

### The four phases in practice

**Phase 1 — Expand (add new structure):**
```sql
-- V10.0__expand_add_display_name.sql
ALTER TABLE users ADD COLUMN display_name VARCHAR(255) NULL, ALGORITHM=INSTANT;
```
The old application ignores the new column. Both versions function.

**Phase 2 — Dual-write and backfill:**
Application code writes to both old and new columns. Historical data is backfilled in batches:
```sql
UPDATE users SET display_name = full_name 
WHERE display_name IS NULL AND id BETWEEN 1 AND 10000;
-- Repeat with SLEEP(0.1) between batches
```

**Phase 3 — Switch reads:** Deploy the version that reads exclusively from the new column. Monitor for a confidence window (1-2 weeks).

**Phase 4 — Contract (drop old column):**
```sql
-- V11.0__contract_drop_full_name.sql
ALTER TABLE users DROP COLUMN full_name, ALGORITHM=INSTANT;
```

Each phase is independently deployable and rollback-safe. The schema supports both N and N+1 application versions at every point.

### Aurora MySQL DDL algorithms

Aurora MySQL v3 (MySQL 8.0-compatible) supports three DDL algorithms, and **always specifying ALGORITHM explicitly** prevents MySQL from silently falling back to the expensive COPY algorithm:

| Operation | INSTANT | INPLACE | Requires Table Rebuild |
|---|---|---|---|
| ADD COLUMN (any position) | ✅ | ✅ | No |
| DROP COLUMN | ✅ (8.0.29+) | No | No |
| SET/DROP column DEFAULT | ✅ | ✅ | No |
| ADD/CREATE INDEX | ❌ | ✅ | No |
| CHANGE column data type | ❌ | ❌ (COPY) | Yes |
| Add NOT NULL constraint | ❌ | ✅ | Yes |

**ALGORITHM=INSTANT** modifies only metadata—truly instantaneous with no locks. A critical limit: **maximum 64 instant column changes per table** (`TOTAL_ROW_VERSIONS`), after which you must rebuild with `OPTIMIZE TABLE`. Monitor with:
```sql
SELECT NAME, TOTAL_ROW_VERSIONS FROM INFORMATION_SCHEMA.INNODB_TABLES 
WHERE TOTAL_ROW_VERSIONS > 0;
```

**ALGORITHM=INPLACE with LOCK=NONE** allows concurrent reads and writes during index creation. Percona's testing confirmed **zero impact on Aurora read replicas** due to the shared storage architecture—a significant advantage over standard MySQL replication where index creation causes replica lag.

### Dangerous operations that lock tables

**Changing column data types** (INT→BIGINT, VARCHAR(255)→VARCHAR(256) crossing length-encoding boundaries) forces a full table copy with ALGORITHM=COPY. On a multi-million-row table, this can take hours and lock the table entirely. **Never run these directly**—use gh-ost or pt-online-schema-change instead.

**Adding NOT NULL constraints** to existing columns without a default requires a table scan and rebuild. The safe pattern: add the column as nullable with a default, backfill, then add the NOT NULL constraint in a separate migration (or use gh-ost for large tables).

**Multiple DDL operations in a single ALTER TABLE** where one requires COPY forces the entire statement to COPY—always separate them into individual ALTER TABLE statements.

### gh-ost versus pt-online-schema-change on Aurora

**gh-ost (GitHub's Online Schema Transmogrifier) is generally preferred for Aurora MySQL.** It reads binary logs instead of using triggers, producing lower overhead and enabling true pause capability—when throttled, all writes cease entirely. Configuration for Aurora requires specific flags:

```bash
gh-ost \
  --host=aurora-writer.cluster-xxxxx.region.rds.amazonaws.com \
  --database="mydb" --table="users" \
  --alter="ADD COLUMN status VARCHAR(20) DEFAULT 'active'" \
  --assume-rbr \           # Required: can't change binlog_format without SUPER privilege
  --allow-on-master \      # Required: Aurora replicas share storage
  --chunk-size=2000 \
  --max-load=Threads_running=25 \
  --postpone-cut-over-flag-file=/tmp/ghost.postpone.flag \
  --execute
```

Dynamic reconfiguration at runtime (`echo "chunk-size=500" | nc -U /tmp/gh-ost.mydb.users.sock`) and postponable cut-over make gh-ost operationally superior. However, **gh-ost cannot handle tables with foreign keys or existing triggers**—pt-online-schema-change is the fallback for those cases. Kakao's database team uses pt-osc but notes deadlock risk increases significantly above **1,500 DML/sec**, requiring custom sleep parameter tuning. Sendbird built their own tool, **SB-OSC**, specifically for TB-scale tables where existing tools took weeks; it adds resumability and multithreaded binlog parsing.

---

## Rollback strategies and handling failures

### The forward-only philosophy

Most production teams adopt **forward-only migrations**: if something goes wrong, fix it with a new migration rather than reversing the old one. The reasoning is sound—database rollbacks are fundamentally harder than code rollbacks because new data may have been written since the migration, undo scripts must handle every possible partial failure state, and destructive changes (DROP TABLE, DROP COLUMN) cannot restore lost data.

Flyway's undo migrations (`U__` prefix, Teams edition only) assume the entire forward migration succeeded. But MySQL does **not support transactional DDL**—each DDL statement auto-commits immediately. If a migration with three DDL statements fails on statement two, the first statement is permanently applied while the undo script tries to reverse all three, potentially causing additional errors.

**The practical rollback plan: rollback = deploy previous application code.** This works when migrations follow the backward-compatibility principle:

- New nullable columns are ignored by old code
- New indexes don't affect old code
- New tables don't affect old code
- Old columns haven't been dropped yet (deferred to cleanup phase)

### Recovering from failed migrations on Aurora MySQL

When a migration fails partway through on MySQL/Aurora, partial state is the norm. The recovery procedure:

1. **Assess which statements succeeded** by inspecting the actual table structure
2. **Manually clean up partial changes** if necessary (or adjust the migration to be idempotent)
3. **Run `flyway repair`** to remove the failed entry from `flyway_schema_history`
4. **Fix the migration script** to handle the partial state
5. **Re-run `flyway migrate`**

Writing idempotent migrations prevents most recovery headaches. For MySQL (which lacks `ADD COLUMN IF NOT EXISTS`), use stored procedure wrappers:

```sql
DELIMITER $$
CREATE PROCEDURE safe_add_column()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'status'
    ) THEN
        ALTER TABLE users ADD COLUMN status VARCHAR(50) DEFAULT 'ACTIVE';
    END IF;
END$$
DELIMITER ;
CALL safe_add_column();
DROP PROCEDURE IF EXISTS safe_add_column;
```

**For catastrophic failures, Aurora cluster snapshots are the ultimate safety net.** Create a snapshot before applying risky migrations—Aurora snapshots are fast and AWS recommends this as the "nuclear option." Keep one statement per migration file so partial failures affect only one operation.

---

## Data migrations and batch processing patterns

### Separating schema from data migrations

Use sub-version numbering to group logical changes: `V5.0__DDL_add_status_column.sql` (schema) followed by `V5.1__DML_backfill_status.sql` (data). Alternatively, configure multiple Flyway locations to physically separate them: `locations: classpath:db/schema,classpath:db/data`.

For large table backfills, **never run a single UPDATE on millions of rows**. The transaction holds locks, blocks other queries, and risks timeouts. Instead, process in batches using primary key ranges (not LIMIT/OFFSET, which degrades linearly):

```kotlin
class V5__Backfill_user_status : BaseJavaMigration() {
    override fun migrate(context: Context) {
        val conn = context.connection
        conn.autoCommit = false
        val maxId = conn.createStatement()
            .executeQuery("SELECT MAX(id) FROM users")
            .apply { next() }.getLong(1)
        
        var start = 0L
        while (start < maxId) {
            conn.prepareStatement(
                "UPDATE users SET status = 'ACTIVE' WHERE id > ? AND id <= ? AND status IS NULL"
            ).apply {
                setLong(1, start)
                setLong(2, start + 10_000)
                executeUpdate()
            }
            conn.commit()
            Thread.sleep(100) // Throttle to reduce load
            start += 10_000
        }
    }
}
```

For very large tables, consider running backfills as **application-level background jobs** rather than Flyway migrations. This provides better control over throttling, progress tracking, and resumability—Sendbird's SB-OSC tool exists precisely because migration-level backfills on TB-scale tables are operationally unwieldy.

### Idempotent patterns for MySQL

Repeatable migrations (`R__` prefix) must be idempotent by design. For versioned migrations, defensive patterns include `CREATE TABLE IF NOT EXISTS`, `INSERT ... ON DUPLICATE KEY UPDATE`, and the stored procedure wrapper shown above. Always use `DROP PROCEDURE IF EXISTS` when creating temporary stored procedures for migration logic.

---

## CI/CD pipeline integration

### GitHub Actions workflow

A production-grade pipeline validates migrations on every PR, tests them against a real MySQL instance, and applies them to production as a separate step before application deployment:

```yaml
name: Database Migration Pipeline
on:
  push:
    branches: [main]
    paths: ['src/main/resources/db/migration/**']
  pull_request:
    paths: ['src/main/resources/db/migration/**']

jobs:
  validate:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env: { MYSQL_ROOT_PASSWORD: testpass, MYSQL_DATABASE: testdb }
        ports: ['3306:3306']
        options: --health-cmd="mysqladmin ping" --health-interval=10s --health-retries=5
    steps:
      - uses: actions/checkout@v4
      - uses: red-gate/setup-flyway@v3
        with: { edition: community, i-agree-to-the-eula: true }
      - name: Validate and test migrations
        run: |
          flyway migrate -url="jdbc:mysql://localhost:3306/testdb" \
            -user=root -password=testpass \
            -locations="filesystem:src/main/resources/db/migration"
          flyway validate -url="jdbc:mysql://localhost:3306/testdb" \
            -user=root -password=testpass \
            -locations="filesystem:src/main/resources/db/migration"

  deploy-migrations:
    needs: validate
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: red-gate/setup-flyway@v3
        with: { edition: community, i-agree-to-the-eula: true }
      - name: Apply production migrations
        run: |
          flyway migrate \
            -url="${{ secrets.PROD_DB_URL }}" \
            -user="${{ secrets.PROD_DB_USER }}" \
            -password="${{ secrets.PROD_DB_PASSWORD }}" \
            -locations="filesystem:src/main/resources/db/migration"
```

The pipeline flow is: **Build → Validate Migrations → Apply Migrations → Deploy App → Smoke Tests.** This ensures migrations succeed before any new code touches the database.

### Migration locking and concurrent instances

Flyway acquires a `SELECT ... FOR UPDATE` lock on the `flyway_schema_history` table. When multiple instances attempt migrations simultaneously, only one proceeds while others block. Once the first completes, subsequent instances find no pending migrations and release immediately. This is safe but can cause startup delays in Kubernetes—another reason to prefer the Helm pre-upgrade Job pattern over init containers or startup-time migration.

For blue-green deployments on EKS, the expand-contract pattern is essential. During the transition, **both the blue (old) and green (new) application versions must work with the current schema.** This means migrations applied before the green deployment must be purely additive, and the contract phase (dropping old columns) only runs after the blue environment is decommissioned.

---

## Seven practice scenarios for mid-level engineers

### Scenario 1: Adding a non-nullable column to a table with 10 million rows

The naive approach—`ALTER TABLE orders ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'`—works instantly on Aurora MySQL 3 thanks to INSTANT DDL for ADD COLUMN with default. But **adding the NOT NULL constraint afterward requires INPLACE + table rebuild**. The safe multi-step approach:

1. `V20__add_status_nullable.sql`: `ALTER TABLE orders ADD COLUMN status VARCHAR(20) DEFAULT 'pending', ALGORITHM=INSTANT;`
2. Deploy code that always writes a status value
3. `V21__backfill_status.sql`: Batch update any NULL rows (likely none if default was set)
4. `V22__enforce_not_null.sql`: For large tables, use gh-ost: `gh-ost --alter="MODIFY COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'" ...`

### Scenario 2: Splitting a table into two tables

A `users` table with both profile and billing fields needs separation:

1. `V30__create_billing_profiles.sql`: Create the new `billing_profiles` table
2. Deploy dual-write code: writes to both `users.billing_*` columns and `billing_profiles`
3. `V31__backfill_billing_profiles.sql`: Copy historical data in batches
4. Verify data consistency (compare counts, checksums)
5. Deploy read-switch: application reads from `billing_profiles`
6. `V32__drop_billing_columns.sql`: Remove old columns after confidence window

### Scenario 3: Renaming a column without downtime

Never use `RENAME COLUMN` directly. Instead:

1. `V40__add_display_name.sql`: `ALTER TABLE users ADD COLUMN display_name VARCHAR(255), ALGORITHM=INSTANT;`
2. Deploy dual-write code: `user.display_name = value; user.full_name = value;`
3. `V41__backfill_display_name.sql`: `UPDATE users SET display_name = full_name WHERE display_name IS NULL` (in batches)
4. Deploy read-switch: read from `display_name`, stop writing `full_name`
5. `V42__drop_full_name.sql`: `ALTER TABLE users DROP COLUMN full_name, ALGORITHM=INSTANT;`

### Scenario 4: Migrating JSON data from one format to another

A `settings` JSON column needs restructuring (flat → nested):

1. Add new `settings_v2` JSON column (INSTANT)
2. Deploy code that writes both formats simultaneously
3. Kotlin-based migration backfills `settings_v2` using programmatic transformation logic:
```kotlin
class V50__Transform_settings : BaseJavaMigration() {
    override fun migrate(context: Context) {
        // Read each row's settings JSON, transform structure, write to settings_v2
        // Process in batches of 5,000 using PK range scanning
    }
}
```
4. Use GitHub's Scientist pattern: read both, compare, alert on inconsistencies
5. Switch reads, then drop old column

### Scenario 5: Handling a failed migration in production

A migration with two ALTER TABLE statements fails on the second. Recovery:

1. Check which statements succeeded: `DESCRIBE affected_table;`
2. Note the partial state—first ALTER applied, second did not
3. Run `flyway repair` to remove the failed entry from `flyway_schema_history`
4. Edit the migration to make it idempotent (wrap in IF NOT EXISTS checks)
5. Re-run `flyway migrate`
6. Conduct a postmortem: should this have been two separate migration files?

### Scenario 6: Setting up Flyway in an existing project with a live database

1. Generate a baseline SQL script capturing the current production schema: `mysqldump --no-data mydb > V1__baseline.sql`
2. Run `flyway baseline -baselineVersion=1 -baselineDescription="Initial baseline"` against production—this creates the `flyway_schema_history` table with a single BASELINE entry
3. Place new migrations starting at V2: `V2__add_email_index.sql`
4. `flyway migrate` will skip everything ≤ V1 and apply V2+
5. For development environments: run V1 (baseline) to create the full schema from scratch, then apply subsequent migrations normally

### Scenario 7: Changing a column type from INT to BIGINT on a large table

This is one of the most dangerous operations—it requires ALGORITHM=COPY on standard ALTER TABLE:

1. **Use gh-ost** instead of direct ALTER: `gh-ost --alter="MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT" --assume-rbr --allow-on-master --execute`
2. Alternatively, use expand-contract: add `new_id BIGINT`, dual-write, backfill, switch primary key—but this is extremely complex for a PK column
3. Always test on a staging Aurora cluster first
4. Schedule for low-traffic windows even with gh-ost
5. Create an Aurora snapshot before starting

---

## Lessons from Korean tech companies and real-world incidents

**Toss Bank's architecture** represents the most prominent Korean Flyway adoption. Their SLASH 22 conference talk revealed they use **Flyway + `hibernate.ddl-auto=validate`** from system inception, with each microservice maintaining an independently version-controlled schema. This combination ensures entity-schema consistency at startup while Flyway manages the actual DDL lifecycle.

**Baemin (배달의민족) learned the hard way** about `hibernate.hbm2ddl.auto`—a developer accidentally deleted a production database using auto-DDL, leading the team to permanently remove all DDL permissions and adopt proper migration tooling. Their monolithic MSSQL-to-100-databases-on-AWS migration took months and relied on dual-write patterns, gradual traffic switching, and extensive dependency mapping. A critical discovery: teams claimed "we don't use the main DB" while still maintaining live connections "just in case."

**Kakao's database team** uses Percona pt-online-schema-change for KakaoTalk's MySQL infrastructure, where maintenance windows are impossible. Their key finding: **deadlock risk increases significantly above 1,500 DML/sec**, requiring custom sleep parameter modifications in the Percona tool's source code.

**Sendbird built SB-OSC**, an open-source multithreaded online schema change tool, after suffering repeated production outages from pt-osc trigger creation on their 40+ chat database clusters. For TB-scale tables, existing tools took weeks to months; SB-OSC adds resumability (progress saved to DB + Redis) and parallel binlog parsing.

### Incident patterns worth studying

**Resend (February 2024)** dropped their entire production database when a developer's local migration command accidentally targeted production. Their first restore attempt failed due to wrong timestamp selection—6 hours wasted. Remediation: removed write privileges from user roles, isolated local dev environments.

**GitLab (January 2017)** lost production data when **5 out of 5 backup/restore mechanisms** were misconfigured or failing silently. The lesson: test your backups regularly—untested backups are not backups.

**Cleo** experienced a 10-minute full outage when a long-running migration blocked by existing queries prevented updates to a busy table. Fix: lock timeouts and statement timeouts on all migrations.

These incidents reinforce the authoritative guidance from Fowler and Sadalage's Evolutionary Database Design, Kleppmann's emphasis on backward/forward compatibility in Designing Data-Intensive Applications, and Nygard's Release It! warnings about cascading failures from blocked threads at integration points. **The universal lesson: never make a schema change that can't coexist with both the current and previous application version.**

---

## Conclusion

Three principles emerge as non-negotiable for production Flyway usage with Aurora MySQL. First, **decouple migration execution from application startup** using Kubernetes Jobs or CI/CD pipeline steps—the coupling creates unacceptable failure modes in replicated environments. Second, **every migration must be backward-compatible** with the currently running code, achieved through the expand-and-contract pattern that separates additive changes from destructive cleanup. Third, **always specify DDL algorithms explicitly** (`ALGORITHM=INSTANT` or `ALGORITHM=INPLACE, LOCK=NONE`) to prevent MySQL from silently choosing the expensive COPY path.

For tables exceeding a few million rows, gh-ost is the preferred online schema change tool on Aurora, with pt-online-schema-change as a fallback for tables with foreign keys. Forward-only migrations beat undo migrations on MySQL because the lack of transactional DDL makes rollbacks fundamentally unreliable. And the single most impactful operational practice—validated by incidents at Resend, GitLab, Baemin, and others—is to **never allow direct DDL access to production databases from developer machines**. Migrations flow through version control, CI validation, and automated deployment, or they don't flow at all.