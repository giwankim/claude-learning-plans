---
title: "The Definitive Guide to InnoDB Deadlocks"
category: "Data & Messaging"
description: "Comprehensive guide to InnoDB deadlock internals, six reproducible scenarios, detection tooling for MySQL 8.0 and Aurora, prevention strategies, and Spring Boot/Kotlin resilience patterns."
---

# The definitive guide to InnoDB deadlocks

**InnoDB deadlocks are not bugs — they are an inevitable consequence of concurrent transactional access, and every production MySQL system encounters them.** The key differentiator between teams that suffer from deadlocks and those that don't is understanding *why* they happen and building systematic defenses. This guide covers the lock internals that cause deadlocks, six reproducible scenarios with runnable SQL, detection tooling for MySQL 8.0 and Aurora, prevention strategies, and Spring Boot/Kotlin patterns for building resilient applications. Everything here applies equally to standard MySQL 8.0+ and AWS Aurora MySQL.

---

## How InnoDB locking actually works

InnoDB implements row-level locking on **index records**, not on rows themselves. Even tables without explicit indexes get a hidden clustered index (`GEN_CLUST_INDEX`). This architectural detail is the single most important thing to understand: if your query lacks a suitable index, InnoDB scans and locks *every record in the clustered index*, effectively locking the entire table through thousands of individual row locks.

### Shared, exclusive, and intention locks

Two fundamental lock modes exist at the row level. **Shared (S) locks** permit concurrent reads — multiple transactions can hold S locks on the same record. **Exclusive (X) locks** permit modification — only one transaction can hold an X lock, and it blocks both S and X requests from others. The compatibility matrix is simple: S–S compatible, everything else conflicts.

At the table level, **intention locks** (IS and IX) signal what row-level locks a transaction plans to acquire. A transaction acquires IS before taking an S row lock, IX before an X row lock. The critical property: **IX is compatible with IX**, which is what allows concurrent row-level writes on different rows in the same table. Intention locks only block full-table `LOCK TABLES ... WRITE` requests.

| Requested ↓ / Held → | **S** | **X** | **IS** | **IX** |
|---|---|---|---|---|
| **S** | ✅ | ❌ | ✅ | ❌ |
| **X** | ❌ | ❌ | ❌ | ❌ |
| **IS** | ✅ | ❌ | ✅ | ✅ |
| **IX** | ❌ | ❌ | ✅ | ✅ |

Plain `SELECT` acquires **no locks at all** in READ COMMITTED and REPEATABLE READ — it uses an MVCC snapshot. Only `SELECT ... FOR UPDATE` (X locks), `SELECT ... FOR SHARE` (S locks), `UPDATE`, `DELETE`, and `INSERT` acquire row-level locks.

### Gap locks and next-key locks: the deadlock factory

A **next-key lock** combines a record lock with a **gap lock** on the gap *before* that record in index order. For an index containing values 10, 11, 13, 20, the next-key lock intervals are `(−∞, 10]`, `(10, 11]`, `(11, 13]`, `(13, 20]`, `(20, +∞)`. This is InnoDB's default locking mechanism in REPEATABLE READ, designed to prevent phantom reads.

**The most confusing property of gap locks — and the #1 source of unexpected deadlocks — is that gap locks do not conflict with each other.** The MySQL manual states it plainly: "There is no difference between shared and exclusive gap locks. They do not conflict with each other, and they perform the same function." Gap locks are purely inhibitive: they exist only to prevent insertions.

However, an **insert intention lock** (a special gap lock acquired by `INSERT`) *is* blocked by an existing gap lock from another transaction. This asymmetry is what creates the classic gap-lock deadlock pattern: two transactions each acquire compatible gap locks on the same gap, then both try to insert — each blocked by the other's gap lock.

**Exception**: For unique index lookups with an exact match (`WHERE id = 100` on a primary key), InnoDB uses only a record lock with no gap. Gap locking is unnecessary because the uniqueness constraint already prevents duplicates.

### Auto-increment locks and lock escalation

The `innodb_autoinc_lock_mode` parameter controls auto-increment locking. **Mode 2 ("interleaved")**, the default since MySQL 8.0, uses a lightweight mutex instead of a table-level lock, eliminating AUTO-INC lock contention entirely. Modes 0 and 1 use table-level locks that can deadlock with row-level locks when combined in the same transaction. Use mode 2 with row-based replication (the MySQL 8.0 default).

A critical architectural note: **InnoDB never performs lock escalation.** Unlike SQL Server, which escalates row locks to table locks after ~5,000 row locks, InnoDB maintains individual row-level locks indefinitely. This is excellent for concurrency but means a full table scan on an unindexed column acquires thousands of individual row locks — functionally equivalent to a table lock but without the system ever recognizing it as such.

### MVCC isolation levels dramatically change deadlock behavior

The choice between REPEATABLE READ and READ COMMITTED has a profound effect on deadlock frequency:

| Behavior | REPEATABLE READ | READ COMMITTED |
|---|---|---|
| Gap locks | Active (next-key locks) | **Disabled** (except FK/duplicate checks) |
| Non-matching row locks | Held until transaction end | **Released after WHERE eval** |
| Semi-consistent UPDATE reads | No | **Yes** |
| Lock surface area | Larger | **Smaller** |
| Deadlock frequency | Higher | **Significantly lower** |

**READ COMMITTED eliminates the entire class of gap-lock deadlocks** (Scenario 2 below) and releases locks on non-matching rows immediately. The trade-off is allowing phantom reads and non-repeatable reads. For most web application workloads, this trade-off is worthwhile.

---

## Scenario 1: the classic row-ordering deadlock

Two transactions update the same rows in opposite order. This is the textbook case.

```sql
CREATE TABLE accounts (
    id      INT NOT NULL PRIMARY KEY,
    balance DECIMAL(10,2) NOT NULL DEFAULT 0.00
) ENGINE=InnoDB;

INSERT INTO accounts (id, balance) VALUES (1, 1000.00), (2, 2000.00);
```

```sql
-- Session 1, Step 1:
START TRANSACTION;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
-- ✅ Acquires X record lock on id=1

-- Session 2, Step 1:
START TRANSACTION;
UPDATE accounts SET balance = balance - 200 WHERE id = 2;
-- ✅ Acquires X record lock on id=2

-- Session 1, Step 2:
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
-- ⏳ BLOCKED: needs X on id=2, held by Session 2

-- Session 2, Step 2:
UPDATE accounts SET balance = balance + 200 WHERE id = 1;
-- 💀 DEADLOCK: needs X on id=1, held by Session 1
-- ERROR 1213 (40001): Deadlock found when trying to get lock
```

The deadlock graph shows both transactions holding `lock_mode X locks rec but not gap` on one row and waiting for the same lock type on the other. **Fix**: always lock rows in ascending primary key order. For a funds transfer, lock `LEAST(from_id, to_id)` first.

## Scenario 2: gap lock deadlock during concurrent inserts

This is the most insidious pattern because both sessions execute the *exact same code path* in the *exact same order*.

```sql
CREATE TABLE registrations (
    id     INT NOT NULL PRIMARY KEY,
    email  VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
) ENGINE=InnoDB;

INSERT INTO registrations (id, email, status) VALUES
    (3, 'alice@example.com', 'active'),
    (7, 'bob@example.com',   'active');
-- Creates gap (3, 7) in the index
```

```sql
-- Session 1, Step 1: Check-then-insert pattern
START TRANSACTION;
SELECT * FROM registrations WHERE id = 4 FOR UPDATE;
-- Empty set. Acquires GAP LOCK on (3, 7)

-- Session 2, Step 1:
START TRANSACTION;
SELECT * FROM registrations WHERE id = 5 FOR UPDATE;
-- Empty set. ALSO acquires GAP LOCK on (3, 7)
-- ✅ Succeeds because gap locks don't conflict with each other!

-- Session 1, Step 2:
INSERT INTO registrations (id, email, status) VALUES (4, 'carol@example.com', 'pending');
-- ⏳ BLOCKED: insert intention lock conflicts with Session 2's gap lock

-- Session 2, Step 2:
INSERT INTO registrations (id, email, status) VALUES (5, 'dave@example.com', 'pending');
-- 💀 DEADLOCK: insert intention lock conflicts with Session 1's gap lock
```

The deadlock output shows `lock_mode X locks gap before rec` (held) and `lock_mode X locks gap before rec insert intention waiting` (waited). **Fix**: use `INSERT ... ON DUPLICATE KEY UPDATE` instead of the SELECT-then-INSERT pattern, or switch to **READ COMMITTED** which eliminates gap locks entirely.

## Scenario 3: cross-table lock ordering with SELECT FOR UPDATE

A realistic order-processing deadlock between a fulfillment service and an inventory service.

```sql
CREATE TABLE orders (
    order_id INT NOT NULL PRIMARY KEY,
    status   VARCHAR(20) NOT NULL DEFAULT 'pending',
    total    DECIMAL(10,2) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE inventory (
    product_id INT NOT NULL PRIMARY KEY,
    quantity   INT NOT NULL DEFAULT 0,
    reserved   INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

INSERT INTO orders VALUES (1001, 'pending', 149.99);
INSERT INTO inventory VALUES (501, 100, 5);
```

```sql
-- Session 1 (Fulfillment): lock order, then update inventory
START TRANSACTION;
SELECT * FROM orders WHERE order_id = 1001 FOR UPDATE;
-- ✅ X lock on orders PK 1001

-- Session 2 (Restock): update inventory, then update order
START TRANSACTION;
UPDATE inventory SET quantity = quantity + 50 WHERE product_id = 501;
-- ✅ X lock on inventory PK 501

-- Session 1:
UPDATE inventory SET quantity = quantity - 1, reserved = reserved + 1
WHERE product_id = 501;
-- ⏳ BLOCKED: X on inventory 501 held by Session 2

-- Session 2:
UPDATE orders SET status = 'ready_to_ship' WHERE order_id = 1001;
-- 💀 DEADLOCK: X on orders 1001 held by Session 1
```

**Fix**: establish a canonical table ordering (e.g., always `orders` → `inventory`) enforced across all services.

## Scenario 4: foreign key constraints create implicit shared locks

When inserting into a child table, InnoDB acquires a **shared lock on the referenced parent row** to verify the foreign key constraint.

```sql
CREATE TABLE parents (
    id   INT NOT NULL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE children (
    id        INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    parent_id INT NOT NULL,
    name      VARCHAR(50) NOT NULL,
    KEY idx_parent_id (parent_id),
    CONSTRAINT fk_parent FOREIGN KEY (parent_id) REFERENCES parents(id)
) ENGINE=InnoDB;

INSERT INTO parents VALUES (1, 'Alice'), (2, 'Bob');
```

```sql
-- Session 1:
START TRANSACTION;
INSERT INTO children (parent_id, name) VALUES (1, 'Child_A');
-- ✅ S lock on parents PK id=1 (FK check), X lock on new children row

-- Session 2:
START TRANSACTION;
INSERT INTO children (parent_id, name) VALUES (2, 'Child_B');
-- ✅ S lock on parents PK id=2 (FK check), X lock on new children row

-- Session 1:
UPDATE parents SET name = 'Alice_Updated' WHERE id = 2;
-- ⏳ BLOCKED: needs X on parents id=2, Session 2 holds S

-- Session 2:
UPDATE parents SET name = 'Bob_Updated' WHERE id = 1;
-- 💀 DEADLOCK: needs X on parents id=1, Session 1 holds S
```

The deadlock output shows `lock mode S locks rec but not gap` (held) conflicting with `lock_mode X locks rec but not gap waiting`. **Fix**: update the parent row *before* inserting children, or batch the parent updates into a separate transaction.

## Scenario 5: missing index turns a targeted update into a table lock

Without an index on the `status` column, every UPDATE with `WHERE status = ...` scans and locks **every row** in the clustered index.

```sql
CREATE TABLE orders (
    id     INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    status VARCHAR(20) NOT NULL,
    amount DECIMAL(10,2) NOT NULL
    -- NOTE: No index on status!
) ENGINE=InnoDB;

INSERT INTO orders (status, amount) VALUES
    ('pending', 10), ('shipped', 20), ('pending', 30),
    ('delivered', 40), ('shipped', 50), ('cancelled', 60),
    ('pending', 70), ('shipped', 80), ('delivered', 90),
    ('pending', 100), ('shipped', 110), ('cancelled', 120);
```

```sql
-- Session 1:
START TRANSACTION;
UPDATE orders SET amount = amount + 1 WHERE id = 3;
-- ✅ X lock on PK id=3

-- Session 2:
START TRANSACTION;
UPDATE orders SET amount = amount + 1 WHERE id = 7;
-- ✅ X lock on PK id=7

-- Session 1: full table scan — locks ALL 12 rows
UPDATE orders SET amount = 999.99 WHERE status = 'pending';
-- ⏳ BLOCKED at id=7 (held by Session 2)

-- Session 2: full table scan — locks ALL 12 rows
UPDATE orders SET amount = 888.88 WHERE status = 'shipped';
-- 💀 DEADLOCK at id=3 (held by Session 1)
```

**Fix**: `ALTER TABLE orders ADD INDEX idx_status (status)`. With the index, Session 1 locks only 'pending' rows and Session 2 locks only 'shipped' rows — zero overlap, zero contention.

## Scenario 6: secondary index versus primary key lock ordering

When InnoDB uses a secondary index, it locks the secondary index record first, then the primary key record. A query using the primary key directly reverses this order.

```sql
CREATE TABLE employees (
    id     INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email  VARCHAR(100) NOT NULL,
    salary INT NOT NULL DEFAULT 0,
    UNIQUE KEY idx_email (email)
) ENGINE=InnoDB;

INSERT INTO employees (id, email, salary) VALUES
    (1, 'bob@co.com', 50000), (5, 'alice@co.com', 70000);
```

```sql
-- Session 1: UPDATE via secondary index
START TRANSACTION;
UPDATE employees SET salary = 100000 WHERE email = 'alice@co.com';
-- Lock order: idx_email('alice@co.com') → PRIMARY(id=5)

-- Session 2: UPDATE via secondary index
START TRANSACTION;
UPDATE employees SET salary = 200000 WHERE email = 'bob@co.com';
-- Lock order: idx_email('bob@co.com') → PRIMARY(id=1)

-- Session 1: UPDATE via primary key (reverses order)
UPDATE employees SET email = 'newbob@co.com' WHERE id = 1;
-- ⏳ BLOCKED: needs X on PRIMARY id=1 (held by Session 2)

-- Session 2: UPDATE via primary key (reverses order)
UPDATE employees SET email = 'newalice@co.com' WHERE id = 5;
-- 💀 DEADLOCK: needs X on PRIMARY id=5 (held by Session 1)
```

The deadlock output reveals locks on both `index idx_email` and `index PRIMARY`. **Fix**: access the same rows through a consistent index path in concurrent transactions, or serialize the operations.

---

## Detecting deadlocks in production

### Reading SHOW ENGINE INNODB STATUS

The `LATEST DETECTED DEADLOCK` section is your primary diagnostic tool. Key elements to parse:

```sql
SHOW ENGINE INNODB STATUS\G
```

Each deadlock entry shows two transactions with their held locks (`*** (1) HOLDS THE LOCK(S)`) and waited locks (`*** (1) WAITING FOR THIS LOCK TO BE GRANTED`). **Lock mode strings decode as follows**: `lock_mode X locks rec but not gap` = exclusive record lock only, `lock_mode X locks gap before rec` = gap lock, `lock_mode X locks gap before rec insert intention waiting` = blocked insert intention lock. The `*** WE ROLL BACK TRANSACTION (2)` line identifies the victim — InnoDB typically rolls back the transaction with fewer modifications (smallest undo log).

The critical limitation: this only shows the **most recent** deadlock. Enable persistent logging:

```sql
SET GLOBAL innodb_print_all_deadlocks = ON;
-- On MySQL 8.0+, also ensure full output:
SET GLOBAL log_error_verbosity = 3;
```

All deadlocks then appear in the MySQL error log with full detail.

### Real-time lock diagnostics with performance_schema (MySQL 8.0+)

The `performance_schema.data_locks` table shows **all currently held and pending locks** — not just those involved in waits. This replaced the deprecated `INFORMATION_SCHEMA.INNODB_LOCKS`.

```sql
-- See all current locks on a specific table
SELECT ENGINE_TRANSACTION_ID, OBJECT_NAME, INDEX_NAME,
       LOCK_TYPE, LOCK_MODE, LOCK_STATUS, LOCK_DATA
FROM performance_schema.data_locks
WHERE OBJECT_NAME = 'accounts';

-- Find who is blocking whom (the most useful diagnostic query)
SELECT r.trx_id AS waiting_trx, r.trx_query AS waiting_query,
       b.trx_id AS blocking_trx, b.trx_query AS blocking_query
FROM performance_schema.data_lock_waits w
JOIN information_schema.innodb_trx b
  ON b.trx_id = w.BLOCKING_ENGINE_TRANSACTION_ID
JOIN information_schema.innodb_trx r
  ON r.trx_id = w.REQUESTING_ENGINE_TRANSACTION_ID;

-- Or use the built-in sys schema shortcut:
SELECT * FROM sys.innodb_lock_waits\G
```

**Performance warning**: on MySQL versions prior to **8.0.40**, querying `data_locks` acquires a global mutex that can stall all transactions under high throughput. This was fixed in 8.0.40 with shard-level latching.

### Aurora MySQL monitoring

Aurora exposes a native **`Deadlocks` CloudWatch metric** (namespace `AWS/RDS`) showing average deadlocks per second. Set up a CloudWatch alarm on this metric with threshold > 0 and an SNS notification for immediate awareness.

For deeper analysis, enable `innodb_print_all_deadlocks` in the Aurora parameter group and export error logs to CloudWatch Logs (`/aws/rds/cluster/<name>/error`). Create a metric filter on the pattern `deadlock` to track frequency over time. **Performance Insights** surfaces `innodb_deadlocks` as a counter metric and correlates lock waits with specific SQL statements in the Database Load chart.

Aurora-specific behavior to watch for: concurrent `INSERT ... ON DUPLICATE KEY UPDATE` and `REPLACE INTO` operations on tables with unique secondary indexes can produce **increased deadlocks** due to additional serializability locking introduced in Aurora MySQL 2.10.3+.

### Percona Toolkit for persistent deadlock history

`pt-deadlock-logger` polls `SHOW ENGINE INNODB STATUS` on an interval and stores new deadlocks in a queryable table:

```bash
pt-deadlock-logger h=your-host \
  --dest D=percona_schema,t=deadlocks \
  --create-dest-table \
  --daemonize \
  --interval 30
```

This creates a structured `deadlocks` table with columns for server, timestamp, thread ID, user, database, table, index, lock type, lock mode, victim status, and the full query text. Query this table to identify patterns: which tables deadlock most, which queries are involved, and what time of day deadlocks cluster.

---

## Preventing deadlocks systematically

### Enforce consistent lock ordering everywhere

The most effective prevention. If all transactions acquire locks in the same global order, circular waits become impossible. For single-table operations, sort by ascending primary key before batch updates:

```sql
-- Always lock lower ID first for transfers
UPDATE accounts SET balance = balance - 100 WHERE id = LEAST(@from, @to);
UPDATE accounts SET balance = balance + 100 WHERE id = GREATEST(@from, @to);
```

For cross-table operations, establish a canonical table ordering (e.g., `orders` → `inventory` → `customers`) and enforce it in code review.

### Switch to READ COMMITTED isolation

This single configuration change eliminates the entire class of gap-lock deadlocks and dramatically reduces overall deadlock frequency:

```yaml
# application.yml
spring:
  jpa:
    properties:
      hibernate:
        connection:
          isolation: 2  # TRANSACTION_READ_COMMITTED
```

Or globally in MySQL: `SET GLOBAL transaction_isolation = 'READ-COMMITTED'`. The trade-off — phantom reads and non-repeatable reads — rarely matters for web application workloads. Facebook, Uber, and most large-scale MySQL deployments use READ COMMITTED as their default.

### Reduce transaction scope and add proper indexes

Keep transactions as short as possible. **Never make HTTP calls, queue publishes, or external service calls inside a transaction** — these add unpredictable latency during which locks are held. For bulk operations, process in chunks of 100–500 rows per transaction rather than locking thousands of rows at once.

Adding the right indexes reduces lock scope from "every row in the table" to "only matching rows." A single missing index can cause an UPDATE targeting 1 row to acquire **218,000+ row locks** via a full table scan (documented by Percona). Run `EXPLAIN` on every query involved in a deadlock and verify index usage.

### Use SKIP LOCKED for queue-like patterns (MySQL 8.0+)

For job/task processing where multiple workers grab the next available item, `SKIP LOCKED` eliminates contention entirely:

```sql
START TRANSACTION;
SELECT * FROM tasks WHERE status = 'pending'
ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED;
-- Process the task
UPDATE tasks SET status = 'processing' WHERE id = ?;
COMMIT;
```

Each worker silently skips rows locked by other workers and grabs the next available one. `NOWAIT` is the complementary option for fast-fail scenarios (e.g., reservation systems): it returns an error immediately if the requested row is locked rather than waiting.

### When to disable deadlock detection

The `innodb_deadlock_detect` parameter controls InnoDB's active wait-for-graph traversal. Under extreme concurrency (thousands of simultaneous short transactions), this detection overhead itself becomes a bottleneck. Disable it **only** if you are at Facebook-scale concurrency, and set `innodb_lock_wait_timeout` to a low value (1–5 seconds) as the fallback. For most systems, leave detection enabled — disabling it causes locks to pile up for the full timeout duration.

---

## Spring Boot and Kotlin patterns for deadlock resilience

### Transaction scope determines deadlock surface area

The `@Transactional` annotation's placement directly controls how long locks are held. The most dangerous anti-pattern is wrapping external service calls inside a transaction:

```kotlin
// ❌ Holds DB locks for the duration of HTTP calls
@Transactional
fun processOrder(orderId: Long) {
    val order = orderRepository.findById(orderId).orElseThrow()
    order.status = OrderStatus.PROCESSING
    orderRepository.save(order)          // lock acquired here
    paymentService.chargeCustomer(order) // 2+ seconds of HTTP latency
    notificationService.sendEmail(order) // another HTTP call
    order.status = OrderStatus.COMPLETED
}
```

**Fix**: extract DB operations into a separate bean with tight transactional boundaries:

```kotlin
@Service
class OrderService(
    private val txHelper: OrderTxHelper,
    private val paymentService: PaymentService
) {
    fun processOrder(orderId: Long) {
        txHelper.markProcessing(orderId)             // short tx
        paymentService.chargeCustomer(orderId)       // outside tx
        txHelper.markCompleted(orderId)              // short tx
    }
}

@Service
class OrderTxHelper(private val orderRepository: OrderRepository) {
    @Transactional
    fun markProcessing(orderId: Long) {
        val order = orderRepository.findById(orderId).orElseThrow()
        order.status = OrderStatus.PROCESSING
    }

    @Transactional
    fun markCompleted(orderId: Long) {
        val order = orderRepository.findById(orderId).orElseThrow()
        order.status = OrderStatus.COMPLETED
    }
}
```

A subtle pitfall: `Propagation.REQUIRES_NEW` acquires a **second database connection**. If the inner transaction references uncommitted data from the outer transaction via a foreign key, the database blocks — creating an application-level deadlock where the outer method waits for the inner to return, but the inner waits for the outer to commit.

### Retry patterns with Spring Retry

MySQL deadlock error 1213 surfaces in Spring as `DeadlockLoserDataAccessException` (a subclass of `CannotAcquireLockException`). The retry mechanism **must wrap outside** the transaction so each retry gets a fresh transaction:

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-aop")
    implementation("org.springframework.retry:spring-retry")
}
```

```kotlin
@Configuration
@EnableRetry
class RetryConfig : RetryConfiguration() {
    override fun getOrder(): Int = Ordered.HIGHEST_PRECEDENCE
    // Ensures retry AOP wraps OUTSIDE transaction AOP
}
```

```kotlin
@Service
class AccountService(private val accountRepository: AccountRepository) {

    @Retryable(
        retryFor = [
            DeadlockLoserDataAccessException::class,
            CannotAcquireLockException::class
        ],
        maxAttempts = 4,
        backoff = Backoff(
            delay = 100, multiplier = 2.0,
            maxDelay = 2000, random = true  // jitter prevents thundering herd
        )
    )
    @Transactional(isolation = Isolation.READ_COMMITTED)
    fun transfer(fromId: Long, toId: Long, amount: BigDecimal) {
        // Consistent lock ordering: always lock lower ID first
        val (firstId, secondId) =
            if (fromId < toId) fromId to toId else toId to fromId

        val first = accountRepository.findByIdForUpdate(firstId)
            ?: throw IllegalArgumentException("Account $firstId not found")
        val second = accountRepository.findByIdForUpdate(secondId)
            ?: throw IllegalArgumentException("Account $secondId not found")

        val (from, to) =
            if (fromId < toId) first to second else second to first

        require(from.balance >= amount) { "Insufficient funds" }
        from.balance -= amount
        to.balance += amount
    }

    @Recover
    fun transferRecover(
        ex: CannotAcquireLockException,
        fromId: Long, toId: Long, amount: BigDecimal
    ) {
        throw RuntimeException(
            "Transfer $fromId→$toId failed after all retries", ex
        )
    }
}
```

```kotlin
@Repository
interface AccountRepository : JpaRepository<Account, Long> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT a FROM Account a WHERE a.id = :id")
    fun findByIdForUpdate(id: Long): Account?
}
```

For programmatic control, use `RetryTemplate` with `ExponentialRandomBackOffPolicy` and `SimpleRetryPolicy` configured to traverse exception causes (`traverseCauses = true`).

### Hibernate flush ordering can silently reorder your locks

**Hibernate does not execute SQL in the order you write entity operations.** The `ActionQueue` flushes DML in a fixed order: **inserts → updates → collection removes → collection updates → deletes**. If your code does `remove(entityA)` then `persist(entityB)` then `save(entityC)`, Hibernate executes it as INSERT → UPDATE → DELETE. This means the **lock acquisition order at the database level can differ from what your code implies**, and two threads running the same code path may acquire locks in different effective orders if they trigger flushes at different points.

Flush triggers include transaction commit, JPQL/HQL queries (if AUTO flush mode detects overlap with pending changes), and native SQL queries. A JPQL query in the middle of a method can cause unexpected SQL execution that acquires locks prematurely.

**Mitigation**: call `entityManager.flush()` explicitly between operations when lock ordering matters. For operations with unique constraint dependencies (delete-then-insert with the same unique value), flush between them to force the DELETE to execute before the INSERT.

### Optimistic locking with @Version as the deadlock-free alternative

For workloads with low write contention (the majority of web applications), optimistic locking eliminates physical lock waits entirely:

```kotlin
@Entity
@Table(name = "products")
class Product(
    @Id @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,

    @Column(nullable = false)
    var name: String,

    @Column(nullable = false)
    var price: BigDecimal,

    @Column(nullable = false)
    var stock: Int,

    @Version
    var version: Long? = null
)
```

Hibernate generates `UPDATE products SET stock=?, version=6 WHERE id=? AND version=5`. If another transaction modified the row (incrementing the version), zero rows match and Spring throws `OptimisticLockingFailureException`. Pair this with `@Retryable` for automatic retry:

```kotlin
@Retryable(
    retryFor = [OptimisticLockingFailureException::class],
    maxAttempts = 3,
    backoff = Backoff(delay = 50, multiplier = 2.0, random = true)
)
@Transactional
fun decrementStock(productId: UUID, quantity: Int) {
    val product = productRepository.findById(productId).orElseThrow()
    require(product.stock >= quantity) { "Insufficient stock" }
    product.stock -= quantity
    // On save: UPDATE ... WHERE id=? AND version=? → exception if stale
}
```

**Choose optimistic locking when** conflicts are rare, read-to-write ratios are high, or transactions span user think time. **Choose pessimistic locking when** conflicts are frequent and short transactions can absorb the lock wait cost.

---

## Conclusion

Deadlocks are a structural consequence of concurrent access, not a sign of broken code. The most impactful interventions are, in order: **switching to READ COMMITTED** (eliminates gap-lock deadlocks and reduces lock surface area by ~50%), **adding proper indexes** (prevents full-table-scan locking), and **enforcing consistent lock ordering** (eliminates circular waits for record locks). Layer retry logic with exponential backoff and jitter as a safety net — MySQL explicitly recommends retrying deadlocked transactions.

The Hibernate flush ordering gotcha deserves special attention: the database sees a different SQL execution order than your Kotlin code implies, which can create lock ordering conflicts invisible at the application layer. Explicit `flush()` calls and awareness of the insert-update-delete execution order are essential for reasoning about lock behavior in JPA applications.

For Aurora MySQL, enable `innodb_print_all_deadlocks` in the parameter group with CloudWatch Logs export, set up an alarm on the native `Deadlocks` metric, and watch for the Aurora-specific increased locking behavior on upsert operations with unique secondary indexes. The combination of these monitoring signals with the prevention patterns above builds a system where deadlocks are detected instantly, retried transparently, and systematically driven toward zero.