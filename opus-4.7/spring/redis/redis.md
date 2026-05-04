---
title: "Redis Learning Roadmap for a Senior Kotlin / Spring Boot Engineer"
category: "Spring & Spring Boot"
description: "Comprehensive Redis curriculum for a Spring Boot 3 / Kotlin engineer — data structures, persistence, replication, Cluster, Sentinel, and integration patterns with Lettuce/Redisson and the Spring cache abstraction."
---

# A Comprehensive Redis Learning Roadmap for a Senior Kotlin / Spring Boot Engineer

## TL;DR

- **Plan to invest 10–12 weeks** moving from a refresher on data types and Spring Data Redis through deep production topics (clustering, Sentinel, ElastiCache, observability) into advanced patterns (distributed locks with Redisson, Lua-driven rate limiters, Streams-based event sourcing, Redis Stack modules), with each week pairing an authoritative reading set with a concrete Kotlin + Spring Boot mini-project so concepts are reinforced through code, not just notes.
- **Anchor the curriculum on a small set of canonical sources** — the official `redis.io/docs` pages, the free Redis University tracks ("Get Started with Redis", "Running Redis at Scale", "Redis Streams", "RediSearch", "Redis for Java Developers"), Josiah Carlson's *Redis in Action* (Manning), the Spring Data Redis reference, Baeldung's Redis catalogue, the Redis blog (especially "7 Redis Worst Practices" and "Jedis vs. Lettuce"), Martin Kleppmann's distributed-locking critique, and AWS ElastiCache best-practices whitepapers — and treat everything else as supplementary.
- **Lean into your Kafka and Aurora MySQL background as comparison anchors**: study Redis Streams against Kafka consumer groups, Pub/Sub against Kafka topics, Redis transactions/WATCH against MySQL optimistic locking, and Redis as a cache-aside layer in front of Aurora — and explicitly practice the Kotlin-coroutine idioms (Lettuce reactive + `kotlinx-coroutines-reactor`, suspend repositories, Redisson + coroutines pitfalls) that turn this knowledge into idiomatic production code on your stack.

---

## Key Findings

**The Redis ecosystem you are targeting in 2026.** Redis 7.x mainstreamed hash-field TTLs (HEXPIRE / HPEXPIRE), client-side caching, sharded pub/sub, and the Functions/Lua improvements; Redis 8 (released 2025) folds the formerly-separate Redis Stack modules — RediSearch, RedisJSON, RedisTimeSeries, RedisBloom, plus a new beta Vector Set type — into the default Redis Open Source distribution and renames "Community Edition" to "Redis Open Source." This means a modern roadmap must cover both core Redis primitives and the module-driven multi-model capabilities that ship by default. (Note: RedisGraph reached end-of-life and should be skipped.) AWS ElastiCache and the AWS-compatible Valkey fork are operationally relevant for Korea-based teams running on AWS Aurora, since ElastiCache Serverless and ElastiCache for Redis 7.x are common production targets.

**Spring Boot defaults you should standardize on.** Spring Boot ships with Lettuce as the default Redis client; Lettuce is Netty-based, thread-safe, non-blocking, and is the right default for reactive WebFlux and coroutines codepaths. Jedis remains synchronous and connection-pooled and is still worth knowing for legacy code. Redisson is a higher-level "data grid" client whose distinguishing value is its *distributed objects* — `RLock`, `RSemaphore`, `RMapCache`, `RBucket`, distributed `ExecutorService`, Redlock — rather than raw command coverage. A senior engineer should be fluent in choosing among the three on a per-feature basis: Lettuce for default connectivity and reactive flows, Jedis only when an existing codebase mandates it, Redisson for distributed primitives. Redis OM Spring is the current object-mapping abstraction layered on Spring Data Redis, exposing `@Document`/`@RedisHash` plus search and vector indexing, and is the right choice for non-trivial domain modeling on top of RediSearch and RedisJSON.

**Distributed locking is the most "opinion-rich" topic.** The canonical Redlock algorithm (described at `redis.io/docs/latest/develop/clients/patterns/distributed-locks/`) and Martin Kleppmann's well-known critique ("How to do distributed locking", 2016) frame the unresolved debate: Redlock does not produce monotonic fencing tokens, depends on timing assumptions, and per Kleppmann is unsafe when correctness depends on the lock; antirez's response argues that for many practical workloads it is acceptable. Practical guidance for your stack: use Redisson's `RLock` for general mutual exclusion when *efficiency* (avoiding duplicate work) is the goal, but if correctness is required (financial operations, inventory sold-out scenarios), pair the lock with a fencing token written into a sequencer (e.g. an Aurora row, INCR'd in Redis) that the protected resource validates. Be especially careful when mixing Redisson with Kotlin coroutines — Redisson locks are reentrant and they key reentrancy on the JVM thread, which means multiple coroutines running on the same dispatcher thread can all "acquire" the same lock unintentionally; either dispatch lock-protected work onto distinct threads, use coroutine-aware lock context elements, or avoid Redisson reentrant locks for that path.

**Cache stampede and hot-key prevention are operationally critical.** The canonical antirez note on cache stampedes recommends mutex (single-flight) regeneration via SETNX with a Lua-guarded release, or probabilistic early refresh ("XFetch") for very hot keys. In Spring this maps cleanly to `@Cacheable(sync = true)`, plus a Caffeine L1 / Redis L2 multi-level cache (the open-source `spring-boot-multilevel-cache-starter` and equivalents combine Caffeine + Redis with randomized local TTLs and a Resilience4j circuit breaker). Hot-key issues — a single key receiving disproportionate traffic — require detection (`redis-cli --hotkeys`, MONITOR sampling, ElastiCache `EngineCPUUtilization`) and mitigation through key splitting (sharding by suffix), per-instance local caching, replica routing for reads, or Redis 7's client-side caching (RESP3 tracking). Big-key issues require detection via `redis-cli --bigkeys`, `MEMORY USAGE`, and the type-specific `STRLEN`/`HLEN`/`SCARD`/`ZCARD`/`LLEN`/`XLEN` commands; remediation is structural (split keys, use Streams instead of unbounded Lists, avoid `LRANGE 0 -1` style scans).

**Streams vs Kafka — the most important comparison for your background.** Both are append-only logs with consumer groups, but the operational models diverge: Kafka has true partitions with rebalancing and broker-managed durability; a single Redis Stream is effectively one partition with job-queue-style consumer groups. Redis Streams give XADD / XREADGROUP / XACK / XPENDING / XAUTOCLAIM, support MAXLEN trimming, and require *you* to manually shard streams if you want Kafka-like partitioning. They shine when message volume is moderate (the rule of thumb in community write-ups is under a few hundred million messages/day), retention is bounded, latency is critical, and you already operate Redis. Pick Kafka when you need infinite retention, true multi-partition ordering, broker-managed exactly-once semantics, or massive scale — exactly the workloads your team is presumably already running on Kafka. Redis Streams are an excellent fit for *intra-service* event-sourcing read models, idempotency stores, dead-letter queues for short-lived workflows, and tightly-coupled microservice handoffs. Redis 8.2 introduced `XACKDEL` to make multi-group acknowledgement-and-delete cleanly handleable.

**Kotlin coroutines + Spring Data Redis** are well supported. Spring Data Redis exposes coroutine-friendly extensions (`awaitSingle`, `awaitFirstOrNull`, `Flow<T>` for streams) by depending on `kotlinx-coroutines-reactor`, and `CoroutineCrudRepository`-style suspend repositories work with the reactive Redis stack. The official Spring blog post "Going Reactive with Spring, Coroutines and Kotlin Flow" and Todd Ginsberg's coroutine-based reactive counter on GitHub are good starting templates.

---

## Details

### Phase 0 — Setup and Refresher (Week 0, ~3 days)

Before the structured weeks begin, install the toolchain you'll use throughout: Docker (for `redis/redis-stack:latest`, which bundles Redis 8 with all modules and RedisInsight on port 8001); a Kotlin 2.x / Spring Boot 3.x project skeleton with `spring-boot-starter-data-redis`, `spring-boot-starter-cache`, `caffeine`, `redisson-spring-boot-starter`, and `kotlinx-coroutines-reactor`; the `redis-cli` CLI; RedisInsight desktop app for visualization; and `testcontainers-redis-junit-jupiter` for integration tests. Skim the Redis "Introduction to Redis" docs page and the *Redis in Action* foreword to refresh the mental model: Redis is a single-threaded, in-memory data structure server that you treat as a remote data structure library, not as a generic NoSQL database.

**Self-assessment milestone:** be able to start a Redis Stack container, connect from `redis-cli`, run `SET / GET / INCR / EXPIRE / KEYS *` against ten test keys, and connect a Spring Boot Kotlin app via `RedisTemplate<String, String>` and `StringRedisTemplate`.

---

### Phase 1 — Fundamentals & Data Types (Weeks 1–2)

**Week 1: Core data types and key design.** Re-learn Strings, Lists, Hashes, Sets, Sorted Sets, Bitmaps, HyperLogLog, Streams, and Geospatial indexes with the `redis.io/docs/latest/develop/data-types/` documentation. Pay particular attention to: Hash field expiration (HEXPIRE) introduced in Redis 7.4; Sorted Set range commands (ZRANGEBYSCORE, ZRANGEBYLEX, ZADD with XX/NX/GT/LT flags); Bitmap counting tricks for daily-active-user analytics; HyperLogLog's probabilistic cardinality with PFADD/PFCOUNT/PFMERGE; Stream commands XADD/XREAD/XREADGROUP/XACK/XPENDING/XAUTOCLAIM; and Geospatial GEOADD / GEOSEARCH (which superseded the deprecated GEORADIUS family). Read Chapter 1–3 of *Redis in Action* by Josiah Carlson for the canonical narrative use-cases (article voting, inventory, ad targeting). Read the Redis docs page on key naming conventions (colon-separated namespaces like `user:1:profile`) and the importance of hash tags `{user123}:cart` when designing keys for Redis Cluster co-location.

*Hands-on:* build a **URL shortener** in Kotlin/Spring Boot. Use a String key per short code, an INCR counter for ID generation, a Hash for click-stat metadata, and a Sorted Set ranking codes by click count. Add TTLs of 30 days on inactive codes. Write integration tests with Testcontainers.

**Week 2: Memory model, persistence, replication, eviction.** Read the official Redis docs on persistence (RDB vs AOF, the everysec fsync default, hybrid persistence), key eviction (`maxmemory`, the eight policies — `noeviction`, `allkeys-lru`, `allkeys-lfu`, `volatile-lru`, `volatile-lfu`, `allkeys-random`, `volatile-random`, `volatile-ttl`), and replication (asynchronous, primary–replica, partial resynchronization, replication backlog). Read the Redis University "Running Redis at Scale" course units on persistence and replication. Understand active vs lazy expiration and why neither guarantees that an "expired" key is gone the moment its TTL elapses. Read the Spring Data Redis reference's "Drivers" page on Lettuce vs Jedis and the `LettuceConnectionFactory` configuration, including `commons-pool2` pool tuning and `shareNativeConnection`.

*Hands-on:* write a small Kotlin tool that uses Spring Data Redis to insert 1M keys, measures `INFO memory`, then experimentally swaps `maxmemory-policy` between `allkeys-lru` and `allkeys-lfu` while running a Zipfian-distributed read workload and observes how `evicted_keys` and hit ratios differ. Configure Lettuce with a `GenericObjectPoolConfig` (max-active 50, max-idle 25, min-idle 10, max-wait 2000ms) and verify pool behavior under load.

*Self-assessment for Phase 1:* explain when a Hash beats a JSON-serialized String, when a Sorted Set beats a Hash for "top-N", when AOF everysec is unsafe, and when `noeviction` is the right policy.

---

### Phase 2 — Spring Data Redis & Caching Patterns (Weeks 3–4)

**Week 3: Spring Data Redis and Spring Cache abstraction.** Read the Spring Data Redis reference (`docs.spring.io/spring-data/redis/reference/`) end-to-end, focusing on `RedisTemplate` vs `StringRedisTemplate`, Jackson and Kryo serializers (and why the default JdkSerializationRedisSerializer is rarely what you want), `@RedisHash` repositories, Spring Cache `@Cacheable` / `@CachePut` / `@CacheEvict` / `@Caching`, the `CacheManager` and `RedisCacheManager.RedisCacheManagerBuilder`, per-cache TTLs, and key prefixes. Read the Baeldung article "An Introduction to Spring Data Redis." Read the Spring Blog post "Going Reactive with Spring, Coroutines and Kotlin Flow" and the Spring Data Redis "Coroutines" reference page to wire up `ReactiveRedisTemplate`, `ReactiveRedisOperations`, and suspend extensions.

*Hands-on:* take a representative read-heavy REST endpoint backed by Aurora MySQL in your codebase (or simulate one) and add a Redis cache layer with `@Cacheable(sync = true)` to prevent stampedes. Configure Jackson with `GenericJackson2JsonRedisSerializer` so the cached payloads are human-readable in RedisInsight, then add a custom `RedisCacheConfiguration` per cache name with distinct TTLs.

**Week 4: Caching patterns, stampedes, multi-level caching.** Read antirez's note on cache stampede prevention (mutex with SETNX-NX-PX and Lua release; probabilistic early refresh / XFetch). Read the Redis blog post "7 Redis Worst Practices" and the Redis Anti-Patterns tutorial. Study the patterns side by side: cache-aside (the Spring `@Cacheable` default), read-through, write-through, write-behind, refresh-ahead, and negative caching for "known absent" keys. Read the `spring-boot-multilevel-cache-starter` README on combining Caffeine (L1) with Redis (L2) under a Resilience4j circuit breaker, with randomized local TTLs to spread stampede pressure.

*Hands-on:* extend the Phase 1 cache layer into a **multi-level cache (Caffeine L1 + Redis L2)** with single-flight stampede protection. Implement: (a) a randomized local TTL (50%–150% of the configured value) so app instances don't expire entries in lockstep; (b) a Lua-based mutex using SET NX EX to ensure a single instance regenerates a cold key; (c) a fallback path that serves stale data while a refresh is in flight; (d) a Resilience4j circuit breaker so Redis outages degrade to Caffeine instead of cascading. Add metrics: cache hit ratio per tier, stampede mutex acquisition counts, regeneration latency.

*Self-assessment for Phase 2:* be able to explain when `@Cacheable(sync=true)` is sufficient and when you need an external Lua mutex; explain how a multi-region ElastiCache deployment makes invalidation harder and what versioned-key strategies look like.

---

### Phase 3 — Concurrency Primitives: Locks, Pipelines, Transactions, Lua (Weeks 5–6)

**Week 5: Pipelines, MULTI/EXEC/WATCH, Lua scripting.** Read the Redis docs on Transactions and Pipelining, the Percona blog "Pipelining and Transactions in Redis and Valkey", and the Redis docs on Lua scripting (`redis.io/docs/latest/develop/programmability/eval-intro/`). Internalize the key distinctions: pipelining batches commands for *latency* (no atomicity, commands from other clients can interleave); MULTI/EXEC provides atomic *queued* execution but cannot branch on intermediate values; WATCH adds optimistic concurrency for read-modify-write but retries are expensive under contention; Lua scripts (EVAL / EVALSHA / SCRIPT LOAD; Functions / FCALL in Redis 7+) are atomic, support branching, run in a single round trip, and survive failover via replication. Read the LINE Engineering blog post "Redis Lua script for atomic operations and cache stampede" — particularly relevant since LINE is a major Korean-engineering shop solving real stampede problems.

*Hands-on:* implement a **distributed rate-limiter library** in Kotlin/Spring Boot exposing five algorithms — fixed window (INCR + EXPIRE in Lua), sliding window log (Sorted Set with timestamps + ZREMRANGEBYSCORE + ZCARD in Lua), sliding window counter, token bucket (Hash with `tokens` and `last_refill` fields, `redis.call('TIME')` to avoid client clock drift, in Lua), and leaky bucket. Each algorithm should be wrapped in a single Lua script registered at startup with SCRIPT LOAD and called with EVALSHA. Wire it into a Spring Boot filter as `RateLimitInterceptor`. Use the redis.io tutorial "Build 5 Rate Limiters with Redis" as a reference.

**Week 6: Distributed locks — SETNX, Redlock, Redisson, fencing tokens.** Read in this order: (1) the Redis docs page "Distributed Locks with Redis" describing SETNX-NX-PX with random tokens and Lua-based safe release; (2) Martin Kleppmann's "How to do distributed locking" essay; (3) antirez's response in the Redis docs / blog; (4) the Redisson wiki pages on `RLock`, `RFairLock`, `RReadWriteLock`, `RSemaphore`, and the Redlock implementation; (5) Minsoo Cheong's "Don't Use Java RedissonClient With Kotlin Coroutines for Distributed Redis Locks" on the reentrancy + coroutine pitfall. Understand fencing tokens: a monotonically increasing number that the protected resource validates so a paused / GC'd lock-holder cannot corrupt state with a stale lock.

*Hands-on:* (a) Implement a **manual SETNX-based lock** in Kotlin using Lettuce (acquire with `SET key token NX PX ttl`, release with a Lua compare-and-delete script) and write a deliberate test where two processes race and one is "paused" with `Thread.sleep` past the TTL — observe the failure mode. (b) Replace it with `Redisson.getLock("lock-name")` and rerun. (c) Add a fencing token: store an INCR'd sequence number in Redis on lock acquisition and have your "protected" operation reject any token less than the highest token it has seen. (d) Add a coroutine-based lock helper that handles Redisson's reentrancy correctly by using a `CoroutineContext` element to mark coroutine identity, or use a non-reentrant SETNX implementation under coroutines.

*Self-assessment for Phase 3:* explain why `WATCH ... MULTI ... EXEC` retries badly under high contention and a Lua script does not; explain why Redlock cannot generate fencing tokens; explain why `lock.lock()` from Redisson behaves "wrong" under coroutines.

---

### Phase 4 — Messaging: Pub/Sub and Streams (Weeks 7–8, with Kafka comparisons)

**Week 7: Pub/Sub and the basics of Streams.** Read the Redis docs on Pub/Sub (and the new sharded Pub/Sub from Redis 7+, which avoids the cluster-wide broadcast problem). Read the Redis Streams introduction and the "Redis Streams" course on Redis University. Read at least three comparison articles between Redis Streams and Kafka — Matt Westcott's "Redis streams vs. Kafka", the AutoMQ wiki "Apache Kafka vs. Redis Streams", and Arcjet's "Replacing Kafka with Redis Streams" — to triangulate the trade-offs. Note the operational gotchas: messages are not deleted on XACK, you need MAXLEN trimming or XACKDEL (Redis 8.2+); `maxmemory-policy` does not work intuitively on stream keys (the stream key is one Redis key regardless of stream length); consumer-group rebalancing is manual via XAUTOCLAIM and XPENDING.

*Hands-on:* build a **pub/sub-based real-time notifications service** in Kotlin/Spring Boot with `ReactiveRedisMessageListenerContainer`, subscribing as a `Flow<Notification>`. Then build a parallel implementation using Redis Streams + consumer groups, and write a comparison doc covering: at-least-once semantics, message persistence, consumer group rebalancing, and DLQ handling. Explicitly compare each behavior to the Kafka equivalent.

**Week 8: Streams in depth — consumer groups, idempotency, DLQs, event sourcing.** Read the Redis docs Streams reference for XAUTOCLAIM, XINFO STREAM/GROUPS/CONSUMERS, XTRIM, and XADD with MAXLEN. Re-read the relevant *Redis in Action* chapters on queueing and read mtk3d's "Beyond the Hype: Why We Chose Redis Streams Over Kafka for Microservices Communication." Understand the standard production patterns: store metadata in the stream and large payloads in S3 (hybrid pattern); use a unique consumer ID per pod (e.g., the Kubernetes pod name); always have a reaper that calls XAUTOCLAIM on entries idle longer than the SLA; route unprocessable messages to a DLQ stream and XACK the original.

*Hands-on:* build an **event-sourcing experiment** in Kotlin/Spring Boot. Domain: a tiny order-management service. Each command (CreateOrder, AddItem, CompleteOrder) appends an event to `events:order:{id}` via XADD; a projector consumer group reads via XREADGROUP and materializes a CQRS read model into Redis Hashes; a second consumer group projects to a different read model (e.g., per-customer order list as a Sorted Set). Add idempotency: each event ID is the XADD-generated stream ID; the projector stores `processed:{streamId}` for deduplication. Add a DLQ: any projector exception XADDs to `events:order:dlq` and XACKs the original. Compare the resulting code to what you would have written with Kafka + Kafka Streams.

*Self-assessment for Phase 4:* explain when you would still pick Kafka over Streams on your team, and when Streams is genuinely the right fit; explain the lifecycle of a message in a consumer group from XADD through XACK, including XPENDING and XAUTOCLAIM.

---

### Phase 5 — Operations, Topologies, and Production Hardening (Week 9)

Read the Redis docs on Replication, Sentinel, and Redis Cluster, and the Baeldung "Redis Sentinel vs Clustering" article. Read the AWS ElastiCache best-practices documentation: the "Overall best practices" page (cluster-mode-enabled, long-lived connections, read-from-replica on port 6380, SCAN over KEYS, sharded pub/sub, declared keys in Lua), the AWS Database Blog post "Best practices for sizing your Amazon ElastiCache for Redis clusters" (instance families, Auto Scaling, Enhanced I/O Multiplexing on Redis 7+), and "Monitoring best practices with Amazon ElastiCache for Redis using Amazon CloudWatch" (`EngineCPUUtilization` < 90%, `DatabaseMemoryUsagePercentage` < 80%, `Evictions`, `ReplicationLag`). Read the AWS whitepaper "Performance at Scale with Amazon ElastiCache." Understand the security surface: Redis 6 ACLs, `requirepass`, in-transit TLS, at-rest encryption with KMS, IAM authentication on ElastiCache, VPC isolation. For a Korea-based team, ElastiCache's Seoul (`ap-northeast-2`) region with multi-AZ replication groups and Global Datastore for cross-region read scaling is the relevant deployment pattern.

Internalize the canonical anti-patterns from the Redis blog post "7 Redis Worst Practices" and `redis.io/tutorials/redis-anti-patterns-every-developer-should-avoid/`: never use KEYS in production (use SCAN); avoid hot keys (split or replica-route); avoid big keys; do not rely on multi-database SELECT; do not run a giant single-shard cluster; do not run scripts that block the event loop; tune client connection lifetimes. Learn the diagnostic toolkit: `INFO` (especially `INFO memory`, `INFO replication`, `INFO clients`, `INFO commandstats`), `MONITOR` (only for short debug windows), `SLOWLOG GET`, `LATENCY DOCTOR`, `CLIENT LIST`, `redis-cli --bigkeys`, `redis-cli --hotkeys`, `redis-cli --latency`, `MEMORY USAGE`, `MEMORY STATS`, RedisInsight for visualization, the Redis Software Developer Observability Playbook.

*Hands-on:* spin up a Sentinel-managed primary + 2-replica + 3-Sentinel topology with `docker-compose`, point a Spring Boot Kotlin client at it via `RedisSentinelConfiguration`, kill the primary, observe the failover, measure how the Lettuce client reconnects, and ensure no in-flight writes are silently lost. Then provision a 3-shard 2-replica Redis Cluster, repeat. Finally, provision an ElastiCache replication group in `ap-northeast-2` (cluster-mode-enabled, encryption at rest + in transit, `cache.r7g.large`) via Terraform and connect the same Spring Boot service.

---

### Phase 6 — Advanced Patterns and Redis Stack Modules (Weeks 10–11)

**Week 10: Domain patterns at scale.** Combine the data-type knowledge from Phase 1 with the operations knowledge from Phase 5 to build production-grade implementations of: a **real-time leaderboard** (ZADD with score updates, ZREVRANGE WITHSCORES for top-N, ZRANK for "your rank" queries, periodic snapshotting); **session storage for microservices** (Spring Session Data Redis, sliding-expiry strategies, multi-region replication considerations); **real-time analytics counters** with Bitmaps (daily/monthly active users via SETBIT + BITCOUNT + BITOP) and HyperLogLog (PFADD per visitor, PFCOUNT for cardinality, PFMERGE across days); **deduplication and idempotency-key middleware** (SET NX with the request hash, returning the cached response on duplicate; reference Stripe's 24-hour idempotency-key TTL); **a geospatial nearby-search service** using GEOADD / GEOSEARCH (with `BYRADIUS` and `BYBOX` modes, optionally combined with RediSearch for tag/text filters).

*Hands-on:* pick **two** of the projects above to build end-to-end. The leaderboard and the geospatial nearby-search service are the highest-value choices because they exercise Sorted Sets and the GEO API respectively, both of which appear in interview questions and real product features (e.g., delivery / kickboard / restaurant apps common in Korea).

**Week 11: Redis Stack modules — RediSearch, RedisJSON, RedisTimeSeries, RedisBloom, Vector Sets.** With Redis 8 making these modules part of the default distribution, modern usage increasingly assumes they are available. Read the Redis docs landing pages for each module, plus the "Redis OM Spring Tutorial" and `redis-om-spring` GitHub README. Understand the use cases: RediSearch for secondary indexes / full-text / aggregations / hybrid search over Hashes and JSON documents; RedisJSON for nested document storage with JSONPath; RedisTimeSeries for IoT and metrics with downsampling, compaction rules, and `TS.MRANGE` aggregation; RedisBloom for Bloom filters (deduplication at scale), Cuckoo filters, Top-K, Count-Min Sketch; Vector Sets / RediSearch HNSW for AI use cases (semantic caching, RAG).

*Hands-on:* refactor one previous project to use **Redis OM Spring** with `@Document` annotations, secondary indexes via `@Indexed` / `@Searchable`, and repository-style queries that compile down to FT.SEARCH. As a stretch goal, add a vector-search endpoint that takes a text query, embeds it using a local model, and uses RediSearch's KNN operator for nearest-neighbor lookup — this is increasingly relevant for AI features layered on existing Spring services.

---

### Phase 7 — Capstone (Week 12)

Pick **one** capstone project that exercises everything: I recommend a **distributed job scheduler with Redis Streams** that includes (a) a Redis Stream as the job intake; (b) consumer groups across pod replicas with XAUTOCLAIM-based reaper; (c) Redisson `RLock` to ensure only one scheduler instance assigns work at a time, fenced by an INCR'd token; (d) a multi-level cache (Caffeine + Redis) for job-config lookups; (e) a Lua-based rate limiter on per-tenant submission; (f) a Sorted Set-backed delayed-job queue (score = scheduled epoch); (g) a real-time dashboard reading from RedisTimeSeries metrics that the workers emit; (h) a DLQ stream and operator runbook; (i) Sentinel-or-Cluster topology in the integration test profile via Testcontainers; (j) ElastiCache deployment via Terraform for staging. Write up the design doc explicitly contrasting the Redis approach with how you would have built the same thing on Kafka + Aurora.

---

### Resource Catalog (curated, ordered by priority)

**Official documentation (read first, return to often)**
- `redis.io/docs` — the primary source. Specifically: Data types, Persistence, Replication, Sentinel, Cluster, Eviction, Scripting/EVAL, Streams, Pub/Sub, Distributed Locks, Anti-patterns, Performance Tuning, RediSearch / RedisJSON / RedisTimeSeries / RedisBloom module pages.
- `redis.io/blog/whats-new-in-redis-8` and the Redis 7.4 release-notes pages — keep an eye on hash-field TTLs, sharded pub/sub, client-side caching, Vector Sets.
- Spring Data Redis reference (`docs.spring.io/spring-data/redis/reference/`), Spring Cache abstraction reference, Spring Session Data Redis reference.
- AWS ElastiCache user guide, the "Overall best practices" page, the AWS Database Blog ElastiCache series (sizing, monitoring, sharded pub/sub), and the "Performance at Scale with Amazon ElastiCache" whitepaper.

**Books**
- *Redis in Action* by Josiah L. Carlson (Manning, 2013) — still the canonical book for understanding *why* particular Redis data structures fit particular problems; chapters on caching, distributed task queues, ad targeting, search, and scripting are evergreen even though the Python examples predate Streams. Note: published before Streams, Cluster maturity, and Stack modules — supplement with the official docs for those.
- *Designing Data-Intensive Applications* by Martin Kleppmann (O'Reilly) — for the chapter on consistency, leases, and the distributed-locking discussion that frames the Redlock debate.
- *Spring Data: Modern Data Access for Enterprise Java* (O'Reilly) — older but still useful for the philosophy of Spring Data abstractions; pair with the live online reference for Spring Data Redis.
- The redis-stack documentation site itself functions as a free e-book on the modules.

**Courses (free)**
- Redis University (`university.redis.io`): "Get Started with Redis" (replaces RU101), "Redis for Java Developers" (RU102J, Jedis-focused but the patterns transfer to Kotlin/Lettuce), "Redis Streams", "Querying, indexing, and full-text search" (RediSearch), "Storing, querying, and indexing JSON at speed" (RedisJSON), "Running Redis at Scale", and "Redis as a vector database." All free, all taught by Redis engineers. The "Running Redis at Scale" track is the highest-yield content for production engineers.

**Courses (paid, optional)**
- Stephen Grider's "Redis: The Complete Developer's Guide" on Udemy — the most consistently recommended end-to-end Redis course on Udemy, with a substantial e-commerce project including transactions, locks, RediSearch, and Streams. Useful if you prefer a single linear video path.

**High-signal blogs and articles**
- Redis blog: "7 Redis Worst Practices", "Jedis vs. Lettuce: An Exploration", "Announcing Redis Community Edition and Redis Stack 7.4", "What is idempotency in Redis?".
- antirez (Salvatore Sanfilippo) blog and the antirez-mirrored "Redis Patterns" pages — especially "Cache Stampede Prevention" and "The Redlock Algorithm."
- Martin Kleppmann, "How to do distributed locking" (2016) — required reading.
- Baeldung's Redis index — short, practical Spring Data Redis recipes.
- Spring Blog: "Going Reactive with Spring, Coroutines and Kotlin Flow" (Sébastien Deleuze).
- LINE Engineering blog: "Redis Lua script for atomic operations and cache stampede" — extra valuable since LINE operates Redis at scale on Korean infrastructure.
- Foojay / Halodoc: rate-limiting walkthroughs in Java/Spring with Lua.
- AutoMQ wiki and Matt Westcott on Redis Streams vs Kafka.

**GitHub repos to study (and consider contributing to)**
- `spring-projects/spring-data-redis` — the source of truth for `RedisTemplate` and reactive operations; reading the issues backlog teaches edge cases.
- `lettuce-io/lettuce-core` — Netty-based, reactive, the default Spring client; good Java code to learn from.
- `redis/redis-om-spring` — modern object-mapping abstraction; the demos folder includes vector-search and AI examples.
- `redisson/redisson` — distributed objects, locks, Redlock; the wiki is the de-facto guide for distributed-primitive patterns.
- `redis/jedis` — synchronous client, useful baseline.
- `tginsberg/springboot-reactive-kotlin-coroutines` — concise, current example of Redis pub/sub with Spring WebFlux + Kotlin coroutines.
- `kasramp/spring-data-redis-example-kotlin` — Kotlin CRUD + pub/sub on Spring Data Redis.
- `SuppieRK/spring-boot-multilevel-cache-starter` — opinionated Caffeine + Redis multi-level cache with Resilience4j; great study material for cache-stampede mitigation.
- `redis-developer/redis-microservices-ecommerce-solutions` — Redis-developer-maintained examples spanning RediSearch, geo, JSON, and Streams.
- `redis-stack/redis-stack` — the canonical Docker image and module-bundling repo.

**Conference talks / videos (search these on YouTube)**
- RedisDays / Redis Released talks on Streams architecture, RediSearch internals, and ElastiCache scaling.
- SpringOne talks on Spring Data Redis reactive support, Spring Session Redis, and "Caching Strategies with Spring Boot."
- Strange Loop / QCon talks on "Distributed Locking" (Kleppmann's recorded variants of the linked essay).

### Kotlin/Spring Boot-specific guidance

Throughout the roadmap, prefer `ReactiveRedisTemplate<String, X>` plus `kotlinx-coroutines-reactor`'s `awaitSingle()` / `awaitFirstOrNull()` extensions for an idiomatic suspend-based API; avoid mixing blocking `RedisTemplate` calls inside coroutines on the WebFlux event loop. Use Kotlin DSL for Spring configuration (`beans { bean<LettuceConnectionFactory>() ... }`) where it improves readability, and prefer data classes plus `GenericJackson2JsonRedisSerializer` configured with the Kotlin Jackson module (`registerModule(KotlinModule.Builder().build())`). For Redisson + coroutines, either dispatch lock-protected blocks onto a bounded `Dispatchers.IO` and treat each coroutine's lock-acquire as a thread-local reentrant lock, or implement a small SETNX-based non-reentrant lock helper. Use suspend `CoroutineCrudRepository`-style repositories for simple CRUD, fall back to explicit `ReactiveRedisOperations` for fine-grained pipelining.

### Comparing Redis with Kafka (your strongest leverage point)

Treat the comparison explicitly during Weeks 7–8 and again in the Capstone. The mental model: Kafka is a *distributed log* with broker-managed partitions, infinite retention, and a strong client SDK; Redis is an *in-memory data structure server* whose Streams type happens to be log-shaped. Kafka's strengths — partition-level ordering, infinite retention, exactly-once with transactions, broker-side rebalancing — are exactly the things Redis Streams either don't provide or require you to build manually. Redis Streams' strengths — sub-millisecond latency, embedding in an existing Redis you already operate, simple operational footprint — are exactly what Kafka is overkill for. For your existing Kafka workloads, do not migrate; for *new* per-service event-sourcing read models, idempotency stores, ephemeral job queues, and rate limiters, Streams is often the better choice. Pub/Sub (Redis) ↔ Kafka topics-without-consumer-groups: fire-and-forget, no persistence; sharded pub/sub fixes the cluster broadcast problem. Redis transactions/WATCH ↔ MySQL `SELECT ... FOR UPDATE` vs OCC: WATCH is OCC and behaves badly under contention, while a Lua script is closer to a stored procedure executed atomically inside the data store.

### Korea-specific notes

The closest ElastiCache region is `ap-northeast-2` (Seoul); take advantage of multi-AZ replication groups and consider Global Datastore only if you have a real cross-region read pattern (Tokyo or Singapore secondaries). Korean engineering blogs at LINE, Naver, Kakao, Coupang, and Toss have publicly discussed Redis at scale — the LINE Engineering post on Lua-based stampede protection cited above is especially useful. Korean-language Redis books (e.g., "Redis 운영과 활용" / Redis 실전) exist on YES24 and Kyobo Bookstore but most rigorous Redis material remains in English; treat Korean-language content as supplementary commentary rather than primary source.

### Common pitfalls — checklist to internalize before going to production

- Never run `KEYS` (or `FLUSHALL`) in production; use `SCAN` with a small COUNT.
- Never run `MONITOR` in production for more than a few seconds; it serializes all command output and degrades performance.
- Avoid storing large blobs in Redis values; store the metadata in Redis and the blob in S3.
- Do not rely on numbered databases (SELECT) — single Redis Cluster does not support them and they aren't isolation boundaries.
- Avoid blocking commands (BRPOP, BLPOP, BLMOVE, XREAD with BLOCK) on connection-pool-shared connections in Lettuce/Jedis; dedicate separate connections.
- Lua scripts block the event loop; keep them short, declare all KEYS up front (required by Cluster), and never call expensive commands inside.
- Pub/Sub delivers at-most-once; no replay. Use Streams when persistence is required.
- Eviction policies do not free a single Stream key just because the stream is large — the stream is one key.
- AOF everysec can lose up to one second of data; always-fsync hurts throughput severely.
- ElastiCache failovers can take seconds; clients must reconnect and re-authenticate.
- Big keys block the event loop on commands that scan the whole structure (HGETALL, SMEMBERS, ZRANGE 0 -1); always prefer bounded ranges.
- Hot keys defeat sharding; mitigate with key splitting, replica routing, or local in-process caching.
- Lettuce shares a single connection by default, which is great for performance but disastrous for blocking commands or transactions; configure `shareNativeConnection = false` for those paths.
- Redisson reentrant locks plus Kotlin coroutines is a known footgun.
- Redlock does not generate fencing tokens; do not rely on it alone for correctness-critical locks.

---

## Caveats

- **Versions and APIs move quickly.** Several sources cited above describe Redis 6.x or 7.x behavior; Redis 8 (2025) folds the modules into the core distribution and renames the open-source line to "Redis Open Source." A few code snippets in older blog posts (and in *Redis in Action*, published 2013) predate Streams, Cluster maturity, ACLs, and the Redis 7+ commands; verify command-level details against `redis.io/docs` before adopting them. Spring Boot 3.x property names changed (`spring.redis.*` → `spring.data.redis.*`); Spring Boot 4 (referenced in some Redis OM Spring 2.0 migration notes) is still emerging — pin versions deliberately.
- **The Redlock controversy is unresolved.** Both antirez and Kleppmann have valid points, and there is no single "right answer." Treat the recommendation in this roadmap (use Redisson for efficiency locks, add fencing tokens for correctness locks) as a pragmatic default, not a theorem.
- **Redis Streams vs Kafka throughput numbers vary widely** by hardware, payload size, and persistence configuration; community claims of "X messages/day" thresholds (a few hundred million/day for Streams) are rules of thumb, not benchmarks for your workload. Run your own tests before deciding.
- **Some referenced courses, books, and modules are evolving.** RedisGraph reached end-of-life and should not be invested in. Redis University deprecated several certifications in 2024 and the platform migrated in September 2024 — certificates from before then may have been lost. The `redis-stack` distribution is being merged into Redis 8 Open Source and standalone Redis Stack maintenance releases are scheduled to stop in December 2025. Plan around these transitions.
- **The roadmap assumes 8–12 hours per week of dedicated study and lab time.** A senior engineer with full-time production responsibilities may need to extend Phases 3, 5, and 6 by an extra week each. The phasing is a guideline, not a contract.
- **Some of the blog posts cited (OneUptime, Codepressacademy, Mindful Chase, etc.) are SEO-style summaries of community knowledge** rather than primary sources. They are accurate enough for orientation but should not be cited in design documents — when you cite anything publicly, prefer the official Redis docs, the Spring documentation, the AWS whitepapers, antirez/Kleppmann original posts, and Redis-employee-authored content on the Redis blog.