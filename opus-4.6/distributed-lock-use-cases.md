---
title: "Distributed Lock Use Cases"
category: "Backend Engineering"
description: "Catalog of distributed concurrency scenarios across e-commerce, fintech, and ticketing with production case studies and a decision framework for Redis, pessimistic, and optimistic locking"
---

# Distributed concurrency scenarios every backend engineer will face

**Every production system running on multiple instances will eventually encounter a race condition that corrupts data, costs money, or both.** This report catalogs the most common distributed concurrency scenarios across e-commerce, fintech, ticketing, and infrastructure domains, documents how Korean and global tech companies actually solved them in production, and provides a decision framework for choosing between Redis distributed locks (Redisson), database pessimistic locks (`SELECT FOR UPDATE`), and optimistic locking (`@Version`) in Kotlin/Spring Boot on AWS.

The core insight across dozens of real case studies is this: the right locking strategy depends on three factors — **contention level** (how many concurrent writers target the same resource), **correctness requirements** (financial systems demand stronger guarantees than inventory), and **operation complexity** (simple decrement vs. multi-step business logic). Redis distributed locks dominate in Korean production systems (Woowahan, SSG, Kurly, HyperConnect all use Redisson), but database-level solutions remain essential as safety nets and are often simpler when the source of truth is already a relational database.

---

## E-commerce: the four classic race conditions

### Inventory overselling — the canonical distributed concurrency bug

Two users purchase the last item simultaneously. Thread A reads stock = 1, Thread B reads stock = 1, both pass validation, both deduct. Stock becomes **-1**. This Time-of-Check-Time-of-Use (TOCTOU) vulnerability is the single most common distributed concurrency bug in e-commerce. Sylius (GitHub Issue #2776) confirmed inventory deducted twice at the exact same second. WooCommerce (Issue #44273) confirmed race conditions allowing negative inventory on non-backorder items.

The simplest and most effective fix is an **atomic conditional UPDATE**: `UPDATE inventory SET stock = stock - 1 WHERE product_id = ? AND stock > 0`. If affected rows = 0, the purchase is rejected. No separate read needed, no lock needed — the database handles atomicity. When the business logic between check and update is complex (price calculation, coupon application, multi-table operations), a **Redis distributed lock keyed on the SKU** wraps the entire flow. Lock granularity matters: lock per SKU, never globally, so purchases of different products proceed concurrently.

For flash sales with extreme contention (Alibaba's Singles' Day: **583,000 orders/second**), the architecture shifts entirely. Pre-load inventory into Redis, use a Lua script for atomic check-and-decrement (`if redis.call('get', key) > 0 then redis.call('decr', key); return 1 else return 0 end`), shard inventory across multiple Redis keys for throughput, and enqueue successful decrements via Kafka for asynchronous database writes. **99%+ of requests fail fast** at the Redis layer without ever touching the database.

### Coupon issuance and point deduction — the twin balance problems

Limited-count coupon redemption races identically to inventory: coupon "SAVE50" has 10 available, two concurrent users both see 9 used, both redeem, and the coupon is overissued to 11. Yeogiotte (여기어때) documented this exact scenario in their "네고왕" flash coupon events, where the legacy RDB-dependent stock check caused over-issuance. Their solution: **Redis `INCR` for atomic usage counting** — the increment IS the check, eliminating the TOCTOU gap entirely — with Kafka for asynchronous persistent storage writes.

Point/credit deduction is subtly different because it involves per-user balances rather than global inventory. A user with 500 points places two orders simultaneously from phone and laptop — Order A wants 300 points, Order B wants 400. Both read 500, both pass validation, and 700 points are spent from a 500-point balance. The best strategy here is **pessimistic DB locking** (`SELECT balance FROM user_points WHERE user_id = ? FOR UPDATE`) because contention is inherently limited (only concurrent requests from the same user), and the database is already the source of truth. The alternative — `UPDATE user_points SET balance = balance - 300 WHERE user_id = ? AND balance >= 300` — is even simpler when the logic is straightforward.

### Order status transitions — a state machine problem, not a locking problem

When a customer cancels an order at the exact moment the warehouse marks it as shipped, both transitions pass their state validation (both check current status = "CONFIRMED") and the last write wins. Adobe Commerce (Magento) patch ACSD-51036 specifically fixes race conditions during concurrent REST API calls overwriting shipping status. The correct solution combines a **strict state machine** with **optimistic locking**: `UPDATE orders SET status = 'SHIPPED', version = version + 1 WHERE id = 123 AND version = 5 AND status = 'CONFIRMED'`. If 0 rows affected, the state already changed. Optimistic locking excels here because order status conflicts are rare (most orders follow the happy path). For payment gateway webhooks specifically, switch to pessimistic locking — callbacks arrive in rapid succession and must be serialized.

---

## Fintech: where correctness is non-negotiable

The double-debit race — two concurrent transfers of $80 from a $100 account, both reading the balance as $100, both passing validation — is the financial version of inventory overselling. Doyensec's security research demonstrated this with PostgreSQL under READ COMMITTED isolation: sending 10 concurrent $50 transfers from a $100 account resulted in **nearly all succeeding**, creating a deeply negative balance. Real AWS Fargate deployments confirmed the race window is easily exploitable.

Financial systems use **defense-in-depth**: a Redis distributed lock on the transfer key (to prevent even reaching the database concurrently) plus `SELECT FOR UPDATE` within the transaction as the authoritative safety net. The critical implementation detail: **always acquire locks in consistent order** (lower account ID first) to prevent deadlocks when transfers involve the same accounts in different directions.

**Double-spend prevention** (same payment processed twice) requires a fundamentally different approach — **idempotency keys**. Stripe's implementation, documented by engineer Brandur Leach, is the industry gold standard. Clients send an `Idempotency-Key: <UUID>` header. The server tracks progress through "atomic phases" using a database-backed state machine with named checkpoints (`started`, `charge_created`, `finished`). On retry, the server resumes from the last checkpoint. A `locked_at` field prevents concurrent processing of the same key, and a reaper process cleans up keys after 24 hours. The key insight: **use the database as the coordination layer**, not distributed consensus protocols. Separate retryable operations (local ACID) from non-retryable ones (external API calls like charging a card).

---

## Ticketing and reservations: extreme concurrency under time pressure

Seat booking for high-demand events represents the most extreme distributed concurrency scenario. Ticketmaster's Taylor Swift Eras Tour meltdown in November 2022 — **14 million concurrent users** — collapsed the system and triggered Congressional hearings. BookMyShow handles **100x traffic spikes** during blockbuster releases using Redis distributed locks with TTL. The architecture: `SET seat:show123:A7 user1_session EX 300 NX` — Redis's single-threaded execution guarantees only one `SET NX` succeeds, and the 5-minute TTL auto-releases if the user abandons checkout.

For concert flash sales, the multi-layer architecture mirrors flash sale e-commerce: **virtual queue** (rate-limit entry to N users/second) → **Redis Lua atomic deduction** (pre-loaded ticket tokens, `LPOP` guarantees no overselling at 100K ops/sec) → **async order processing** via message queue → **database as eventual record**. Only valid orders reach the database, dropping effective concurrency from 100K to manageable levels.

Hotel reservations and restaurant bookings have lower contention but add complexity through overlapping date ranges and multi-channel distribution (Booking.com, Expedia, direct website each with potentially stale availability). Optimistic locking with version columns is typically sufficient, backed by database-level unique constraints or PostgreSQL exclusion constraints for bulletproof overlap prevention.

---

## Production case studies from Korean tech companies

Korean tech companies have published remarkably detailed accounts of real distributed concurrency bugs and their solutions.

**Woowahan (Baemin)** documented two major cases. Their WMS inventory transfer system had a race condition where allocation and cancellation requests for the same transfer document ran concurrently — the cancel checked status before allocation had updated it, creating orphaned inventory allocations. The fix: Redisson distributed lock with **the same lock key for both allocation and cancellation**, scoped per transfer-request-document. They also introduced a state key mechanism enabling selective parallelism (multiple allocations for different SKUs proceed concurrently) while blocking conflicting operations. In their advertising system, they used **MySQL `GET_LOCK()`** for distributed locking without additional infrastructure — but discovered a critical connection management bug: JdbcTemplate returned connections to the pool after `GET_LOCK()`, so another thread could acquire that connection and inadvertently release or acquire the wrong lock. The fix required using `DataSource` directly and maintaining the same connection for lock/unlock.

**SSG (Shinsegae)** documented their ECMS automation center, where the legacy concurrency control used a separate DB table (SELECT to check → INSERT as lock). Simultaneous requests both passed the SELECT check before either INSERT completed, causing unique constraint violations and leaving inventory unreflected. They migrated to **Redis distributed lock with Spring AOP (Redisson)** and a custom `@DistributedLock` annotation, critically using `Propagation.REQUIRES_NEW` to ensure the **transaction commits before the lock releases**.

**Kurly** validated their Redisson distributed lock by testing 100 concurrent coupon requests for 100 coupons — exactly 100 issued, zero over-issuance. They explicitly documented the lock-transaction ordering pitfall: if Client 1 deducts stock (10→9), releases the lock, but hasn't committed the transaction, Client 2 acquires the lock and reads stock as 10 (uncommitted). Two deductions occur, but only one is reflected.

**HyperConnect** published a detailed two-part series on their Azar service, documenting three failure modes of naive Redis distributed locks: no lock timeout (crashed app → permanent deadlock → full outage), tryLock inside try-finally (failed acquisition → finally releases someone else's lock), and **spin lock causing massive Redis load** (~2,000 requests/second under 100 concurrent users). All solved by migrating to Redisson's pub/sub mechanism.

---

## Global case studies: Stripe, Uber, and the Kleppmann critique

**Stripe** designed its idempotency system to handle the fundamental problem of payment APIs: network failures leaving clients uncertain whether a charge was created. Their solution uses database-backed state machines tracking progress through atomic phases, with recovery points, a completer process for abandoned requests, and transactionally-staged job drains. Processing over **$1 trillion annually** with **99.999% uptime**, Stripe demonstrates that serializable transaction isolation limits concurrency but guarantees correctness — an acceptable trade-off for payments.

**Uber** deployed a continuous dynamic race detection system across **46 million lines of Go code** in **2,100+ microservices**, discovering **~2,000 data races** in 6 months. Their direct admission: *"Outages caused by data races in Go programs are a recurring and painful problem... These issues have brought down our critical, customer-facing services for hours in total."* Key patterns found included closure variable capture in goroutines, concurrent map access (Go maps are NOT thread-safe), and mutex copy bugs from pointer/value receiver confusion.

**Martin Kleppmann's critique of Redlock** remains the most influential analysis of distributed locking safety. He demonstrates that Redis's Redlock algorithm fails under three realistic scenarios: JVM GC pauses (HBase had this exact production bug), network packet delays (GitHub's 90-second packet delay incident in 2012), and NTP clock drift. His recommendation: use a single Redis instance for **efficiency locks** (preventing duplicate work — it's okay if they occasionally fail) and proper consensus systems (ZooKeeper, etcd) for **correctness locks** (preventing data corruption). Always use **fencing tokens** — monotonically increasing identifiers that allow the resource server to reject stale writes.

---

## Infrastructure patterns requiring distributed coordination

Beyond business logic, several infrastructure patterns demand distributed locking. **Scheduled job deduplication** is best solved with **ShedLock**, the de facto standard for Spring Boot. It creates a lock record in a shared store (JDBC, Redis, Mongo) before executing a `@Scheduled` task — first instance wins, others skip. Configuration is minimal:

```kotlin
@Scheduled(cron = "0 */5 * * * *")
@SchedulerLock(name = "myTask", lockAtMostFor = "4m", lockAtLeastFor = "2m")
fun execute() { /* task logic */ }
```

**Cache stampede prevention** uses distributed locking to ensure only one instance rebuilds an expired cache key while others wait. Toss documented this approach in their cache strategy guide, recommending distributed locks on cache miss combined with **TTL jitter** (random 0-10 second offsets) to prevent synchronized mass expiration. Facebook's Memcache paper formalized this as "leases for thundering herd prevention." For single-instance coalescing, the Go `singleflight` pattern (Java equivalent: `ConcurrentHashMap<String, CompletableFuture<V>>`) deduplicates concurrent cache-miss queries.

**Kafka consumer deduplication** addresses the fact that Kafka's default guarantee is at-least-once. Consumer crashes before offset commit, producer retries on lost ACKs, and rebalance-triggered reprocessing all cause duplicate message processing. The gold standard: idempotent consumer pattern with a `processed_messages` table (unique constraint on message ID), where processing and dedup record insertion happen in the **same database transaction**. For highest reliability, combine with the transactional outbox pattern and Debezium CDC.

**Distributed rate limiting** across multiple instances uses Redis-based sliding window counters with Lua scripts for atomicity. Spring Cloud Gateway has built-in Redis rate limiting via the `RequestRateLimiter` filter, or implement custom sliding window counters using Redis sorted sets (ZADD with timestamp scores, ZREMRANGEBYSCORE to prune, ZCARD to count).

---

## The critical pitfall: lock release must happen after transaction commit

Every Korean tech blog post mentioning distributed locks warns about the same pitfall, and it deserves emphasis. When using a Redis distributed lock with `@Transactional`, **the lock must wrap the transaction, not the other way around**. If the lock is acquired inside a transactional method, Spring's proxy hasn't committed the transaction when the lock releases in the `finally` block. Another thread immediately acquires the lock and reads stale, uncommitted data.

The fix in Spring Boot/Kotlin uses either AOP ordering or programmatic transaction management:

```kotlin
// Lock wraps transaction via TransactionTemplate
fun createOrder(productId: Long) {
    val lock = redissonClient.getLock("lock:product:$productId")
    if (!lock.tryLock(3, 10, TimeUnit.SECONDS)) throw LockException()
    try {
        transactionTemplate.execute {
            val product = productRepository.findById(productId).get()
            product.stock -= 1
            productRepository.save(product)
        }
        // Transaction committed BEFORE lock released ✅
    } finally {
        if (lock.isLocked && lock.isHeldByCurrentThread()) lock.unlock()
    }
}
```

For the annotation-based approach, the `@DistributedLock` AOP aspect must have **higher priority** (lower `@Order` number) than `@Transactional` so it executes first (acquires lock) and completes last (releases lock after transaction commit). The SSG and Kurly engineering teams both use `Propagation.REQUIRES_NEW` on the inner transactional method to ensure commit before unlock.

A second critical Kotlin-specific pitfall: **Redisson's `RLock` is reentrant based on thread ID**, which breaks with Kotlin coroutines. Multiple coroutines sharing the same thread bypass the lock entirely (reentrant behavior), and coroutines switching threads at suspension points cause `IllegalMonitorStateException` on unlock. Use `Dispatchers.IO` with blocking calls around Redisson operations, or use `RSemaphore` (non-reentrant) instead of `RLock`.

---

## Decision framework for choosing a locking strategy

| Scenario | Best Strategy | Why |
|---|---|---|
| Inventory deduction (normal) | Atomic conditional UPDATE | Eliminates TOCTOU gap, no lock needed |
| Inventory deduction (flash sale) | Redis Lua script + sharding | 100K+ ops/sec, DB can't handle it |
| Coupon stock (first-come-first-served) | Redis INCR/DECR | Atomic counter, simpler than distributed lock |
| Point/credit balance deduction | `SELECT FOR UPDATE` | Per-user contention is low, DB is source of truth |
| Order status transition | Optimistic lock (`@Version`) | Conflicts rare, no blocking |
| Financial transfer | Redis lock + `SELECT FOR UPDATE` | Defense-in-depth for correctness |
| Double-spend prevention | Idempotency key + DB unique constraint | Design pattern, not a lock |
| Seat booking (high demand) | Redis distributed lock with TTL | Sub-millisecond, auto-expiry |
| Scheduled job dedup | ShedLock (JDBC or Redis) | De facto standard, minimal config |
| Cache stampede | Redis lock on cache miss + TTL jitter | Single rebuilder, others wait |
| Kafka consumer dedup | DB unique constraint in same transaction | Strongest guarantee |
| Cross-service coordination | Redis distributed lock (Redisson) | Only option spanning multiple DBs |

The three decision axes are contention level, correctness requirements, and whether you already have Redis in your stack. If contention is low and the database is the source of truth, pessimistic or optimistic DB locks avoid adding infrastructure. If contention is high or coordination spans multiple services, Redis is the only practical option at scale. For financial correctness, always layer a database-level safety net (unique constraint, CHECK constraint, or `SELECT FOR UPDATE`) underneath any Redis-based solution — Redis is excellent for approximate, transient coordination but should not be the sole guardian of financial data integrity.

## Conclusion

The landscape of distributed concurrency solutions is not a matter of choosing one "best" lock — it's about matching the right mechanism to each scenario's contention profile, correctness requirements, and operational complexity. Three insights stand out from the production case studies surveyed. First, the simplest solutions are often the best: atomic conditional UPDATEs and Redis `INCR` eliminate entire categories of race conditions without any explicit locking. Second, the transaction-lock ordering pitfall (lock must wrap transaction, never the reverse) is the **single most documented bug** across Korean engineering blogs — it appears in posts from Woowahan, SSG, Kurly, and multiple tutorial series. Third, Martin Kleppmann's distinction between efficiency locks and correctness locks should guide every architectural decision: if a lock failure means duplicate work, use Redis; if it means data corruption, use database constraints or consensus-based systems as the authoritative safety net.