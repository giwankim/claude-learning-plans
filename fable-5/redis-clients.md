---
title: "Mastering JVM Redis Clients with Spring Boot: A Rigorous Learning Plan (Lettuce, Jedis, Redisson)"
category: "Data & Messaging"
description: "An 8-week, part-time (~8–10 h/week) five-phase plan for mastering JVM Redis clients on a Kotlin/Spring Boot/EKS stack: Lettuce as the production default (Netty-based multiplexing, thread-safe shared connection, Spring Data Redis default), Redisson only where distributed primitives (locks, semaphores, rate limiters, leader election) are needed, and Jedis as a study/comparison tool — with ElastiCache/MemoryDB for Valkey recommended for new AWS work. Centers on the Kleppmann-vs-antirez distributed-lock debate (efficiency vs correctness locks, why Redlock/RLock needs fencing tokens for correctness), and pairs every phase with primary-source reading, a Kotlin/Testcontainers project, and a self-assessment checkpoint through protocol/threading theory, Spring Data Redis caching, pooling models, and benchmarking."
---

# Mastering JVM Redis Clients with Spring Boot: A Rigorous Learning Plan (Lettuce, Jedis, Redisson)

## TL;DR
- **Lettuce is the correct default** for your Kotlin/Spring Boot/EKS stack (Netty-based multiplexing, thread-safe shared connection, Spring Data Redis default); add **Redisson** only where you need distributed primitives (locks, semaphores, rate limiters, leader election) and treat **Jedis** as a study/comparison tool rather than your production driver. On AWS, prefer **ElastiCache/MemoryDB for Valkey** for new work — AWS prices it **20% lower on nodes and 33% lower on Serverless than Redis OSS** (Oct 2024 launch), it is BSD-licensed under the Linux Foundation, and it is drop-in compatible with Lettuce/Jedis/Redisson.
- The single most important theoretical lesson: **distributed locks split into "efficiency" locks (Redlock/Redisson are fine) and "correctness" locks (they are NOT sufficient without fencing tokens)** — the Kleppmann vs antirez debate is the primary source you must read closely, and it should reshape how you use `RLock` for inventory or money.
- The plan is **8 weeks, part-time (~8–10 h/week)**, in 5 phases: (1) protocol/threading theory, (2) Lettuce + Spring Data Redis caching, (3) Jedis pooling/blocking model, (4) Redisson + distributed-lock correctness, (5) AWS/Valkey + benchmarking — each with primary-source reading, a Kotlin/Testcontainers project, and a self-assessment checkpoint.

## Key Findings

### Current state of the ecosystem (verified 2025–2026)
- **Lettuce** moved under the Redis org and became an official client with the Redis 7.2 release; it was **relicensed from Apache 2.0 to MIT**. The 7.x line (7.6.0 tested against Redis 8.8, works on Java 8–24, built on Netty 4.2) is current. Lettuce remains the Spring Boot default.
- **Jedis** is on the 7.x line (7.2.0 current-stable, 8.0.0-beta introducing RESP3 auto-negotiation by default). Jedis 7.0 introduced a new client family — `RedisClient`, `RedisClusterClient`, `RedisSentinelClient` — replacing `JedisPooled`/`JedisCluster`/`JedisSentineled`, all built on the `UnifiedJedis` base. Client-side caching (RESP3, Redis ≥ 7.4) is supported in `UnifiedJedis`/`JedisPooled`/`JedisCluster`.
- **Redisson** is actively maintained (Valkey + Redis client, 50+ distributed objects). It has a sharp **open-source vs PRO split**: the "ultra-fast client engine," data partitioning across cluster masters, local-cache variants, and reliable messaging are PRO-only. Community discussion questions whether raw performance optimizations should be paywalled — factor this into adoption.
- **Redis licensing rollercoaster**: BSD → RSALv2/SSPLv1 (March 2024) → Valkey fork under Linux Foundation → **Redis 8.0 re-added AGPLv3 on May 1, 2025** after antirez rejoined, confirmed by CEO Rowan Trollope's post "Redis is now available under the AGPLv3 open source license" and antirez's own words: *"I'm happy that Redis is open source software again, under the terms of the AGPLv3 license"* (antirez.com/news/151). Redis 8 is tri-licensed (AGPLv3, RSALv2, SSPLv1) and folds former Redis Stack modules (JSON, Time Series, probabilistic types, Query Engine) into core. AGPLv3's network-copyleft matters only if you modify Redis and offer it as a service; for internal use it changes little.
- **Spring Boot 4.x** is current (4.0 Nov 2025, 4.1 June 2026); Spring Boot 3.5 reached EOL June 30, 2026. **Spring Data Redis 4.x** still defaults to **Lettuce**. Critically, Spring Data Redis 4.0 **deprecated the Jackson 2 serializers** (`GenericJackson2JsonRedisSerializer`, `Jackson2JsonRedisSerializer`, `Jackson2HashMapper`, all `@Deprecated(since="4.0", forRemoval=true)`) in favor of Jackson 3 equivalents (`GenericJacksonJsonRedisSerializer`, etc.), tracking Spring Framework 7 / Boot 4's move to Jackson 3 (`tools.jackson.databind`). The property namespace moved from `spring.redis.*` to `spring.data.redis.*` back in **Spring Boot 3.0** (per the official migration guide: *"Configuration Properties for Redis have moved from `spring.redis.` to `spring.data.redis.`"*).
- **Valkey clients**: Both Lettuce and Jedis connect to Valkey **unchanged** — Valkey is a fork of Redis 7.2.4 speaking byte-identical RESP2/RESP3 (its `INFO` even reports `redis_version:7.2.4` for compatibility). There are two official Valkey Java clients: **valkey-glide** (`io.valkey:valkey-glide`, AWS-sponsored, Rust core with Java bindings, GA) and **valkey-java** (Jedis-derived). Redisson also officially supports Valkey (`RMap`/`RLock`/`RBucket` work unchanged). Note: proprietary Redis modules (RediSearch, RedisJSON) are not in Valkey core.

### The three clients, compared

| Dimension | Lettuce | Jedis | Redisson |
|---|---|---|---|
| Transport | Netty NIO, non-blocking | BIO (blocking socket) | Netty NIO, non-blocking |
| Thread model | One thread-safe connection multiplexes many threads | One connection = one thread; needs a pool | Connection pool + async engine |
| Pooling | **Not needed** for normal use (shared connection); pool only for blocking cmds & MULTI/EXEC | **Required** (`JedisPool`/commons-pool2) | Managed internally |
| API | sync / async (`RedisFuture`) / reactive / Kotlin coroutines | synchronous | data-structure & service abstractions (`RMap`, `RLock`, …) |
| Best for | Default Spring driver; async/reactive; Spring integration | Simple synchronous apps; feeling the pooling model | Distributed locks, collections, rate limiters, leader election |
| License | MIT | MIT | Apache 2.0 (OSS) / commercial PRO |
| Spring Boot default | ✅ | alternative | via `redisson-spring-boot-starter` |

**Why Lettuce is Spring's default and why pooling is usually unnecessary:** Lettuce multiplexes commands over a single Netty connection using TCP's ordered send/receive; multiple threads may share one connection *as long as they avoid blocking (`BLPOP`) and transactional (`MULTI`/`EXEC`) operations*, which would otherwise cause head-of-line blocking for other users of the connection. A single thread-safe shared Lettuce connection scales far beyond naive expectations — maintainer benchmarks show roughly **100k QPS** under ~200 concurrent threads on an 8-core machine (localhost, Lettuce 6.x); the low-thousands QPS figure people quote really describes a *single blocking/synchronous caller*, not the multiplexed connection. Pooling (via commons-pool2 + `LettucePoolingClientConfiguration`, or `shareNativeConnection=false`) is only genuinely needed for blocking/transactional cases. By contrast **Jedis** uses blocking I/O — one connection serves one thread at a time, so a `JedisPool` is mandatory under concurrency.

### Distributed locking: the core theory you must internalize
- **Redisson `RLock`** uses a Redis **HASH + Lua scripts** for atomic acquire/release, a **pub/sub channel** to notify waiters (avoiding busy spin), reentrancy via a counter, and a **watchdog** (Netty `HashedWheelTimer`) that renews the lease every ~10s (default `lockWatchdogTimeout` 30s) *only when no explicit `leaseTime` is set*. If you pass a `leaseTime` (e.g., `tryLock(10, 30, SECONDS)`), the watchdog is disabled and the lock auto-releases. There is also a `SpinLock` variant (exponential backoff, no pub/sub) to avoid pub/sub fan-out storms in clusters.
- **Lettuce-style hand-rolled lock** = `SET key val NX PX ttl` + Lua compare-and-delete release, driven by a client-side **spin loop**. This hammers Redis with repeated `SETNX` attempts — Korean engineering write-ups (Hyperconnect, S-Core) measure ~1,980 lock attempts/sec while one client waits. Reach for this only when you fail-fast (no retries).
- **The Kleppmann vs antirez debate (required primary reading):** Martin Kleppmann's "How to do distributed locking" (Feb 8, 2016) argues Redlock is unsafe for correctness because its safety rests on timing assumptions (bounded clock drift, network delay, GC pauses); a stop-the-world GC pause or clock jump can let two clients both believe they hold the lock. His prescription is **fencing tokens** — in his words, *"a fencing token is simply a number that increases (e.g. incremented by the lock service) every time a client acquires the lock… this leads us to the first big problem with Redlock: it does not have any facility for generating fencing tokens."* antirez's rebuttal "Is Redlock safe?" (antirez.com/news/101) argues Redlock re-checks elapsed time after acquisition (immunizing it against acquisition-phase delays) and that random tokens with check-and-set give equivalent safety. **The synthesis:** both are right for different goals — Redlock/Redisson are fine for *efficiency* locks (dedup cron jobs, reduce duplicate work) but insufficient for *correctness* locks (money, inventory) without end-to-end fencing tokens. Redisson now ships a **fenced lock** (`getFencedLock`, `tryLockAndGetToken`) precisely for this. For hard correctness, ZooKeeper/etcd (linearizable, sequential znodes) or a DB conditional/optimistic write is the stronger tool.

### Spring Data Redis integration essentials
- **Templates**: `RedisTemplate` (Java serializer by default) vs `StringRedisTemplate` (`StringRedisSerializer`, human-readable). Configure key/value/hash serializers explicitly — a very common Kotlin pitfall.
- **Serializers & Kotlin**: `GenericJackson2JsonRedisSerializer` (now `GenericJacksonJsonRedisSerializer` in SDR 4.0) embeds `@class` type hints via Jackson **default typing**, which requires `NON_FINAL`/`activateDefaultTyping` and **breaks on `int[]`/primitive arrays and Kotlin `data class` edge cases**; default typing is also a known **deserialization-security risk** (must use a `PolymorphicTypeValidator`). For Kotlin, register the Jackson Kotlin module and prefer per-type `Jackson2JsonRedisSerializer` or a locked-down `ObjectMapper`. Beware **serialization version drift** — changing a data class shape silently breaks cached payloads.
- **Spring Cache**: `@Cacheable`/`@CachePut`/`@CacheEvict`/`@Caching`, `RedisCacheManager` with **per-cache TTL** via `RedisCacheConfiguration`, SpEL key generation. Enable statistics for Micrometer hit-ratio metrics.
- **Autoconfiguration**: `spring.data.redis.*` (host, port, ssl, client-name, timeout, `lettuce.pool.*`). Lettuce pooling requires the `commons-pool2` dependency; `LettuceConnectionFactory` uses a shared native connection by default (min 8 / max 8 pool when enabled).
- **Transactions**: Redis `MULTI/EXEC` is **not** an RDBMS transaction — no rollback, no isolation in the ACID sense; commands are queued and executed atomically but a logic error mid-transaction is not undone. Use `SessionCallback` + `enableTransactionSupport`, or prefer **Lua scripts / Redis Functions** for true server-side atomicity. This is a key conceptual difference to teach explicitly.
- **`@RedisHash` / repositories**: secondary indexes and `@RedisHash` exist but have real limitations (no rich querying, index maintenance overhead, easy to misuse in production) — fine for simple session-like objects, not a general ORM.
- **Production pitfalls**: `KEYS` in production (O(N), blocks the single thread — use `SCAN`), hot keys, big keys, cache **stampede/thundering herd**, cache **penetration** (null caching / Bloom filter), cache **avalanche** (TTL jitter ±10%), and Redis `DEL` vs `UNLINK`.

### Underlying theory connecting to implementation
- **Redis threading**: Redis executes commands on a **single thread** (an event loop), which is *why* it gives atomicity for individual commands and Lua scripts without locks — and why O(N) commands (`KEYS`, big `SMEMBERS`) are dangerous. Redis 6+ added **I/O threads** for network read/write parsing only; command execution stays single-threaded. Valkey pushed further with asynchronous I/O threading: Valkey 8.0 (Linux Foundation, Sept 2024) reports throughput **up to 1.2 million requests/sec on AWS r7g instances, over 3× the previous version (~380K)**, and AWS/valkey.io cite **up to ~230% higher throughput and ~70% lower latency** (measured rising from 360K to 1.19M req/s vs Valkey 7.2 with 8 I/O threads on C7g.16xlarge). This single-threaded-command model is the root cause that shapes all three clients' designs — multiplexing works precisely because the server serializes anyway.
- **RESP2 vs RESP3**: RESP3 (Redis 6) adds typed replies and **push messages**, enabling invalidation messages and client-side caching on the *same* connection. Lettuce 6+ and Jedis 8 default to/negotiate RESP3; you may need to pin RESP2 (`ClientOptions.protocolVersion(RESP2)`) against older Redis Stack.
- **Server-assisted client-side caching** (`CLIENT TRACKING`): default mode (server remembers read keys) vs **broadcasting** mode (subscribe to prefixes, zero server memory). **Lettuce** ships a `CacheFrontend`/`ClientSideCaching` API — but only for **Standalone** (not Cluster/Master-Replica, since push messages are node-local). **Jedis** supports it (RESP3, Redis ≥ 7.4) in beta. Redisson offers local-cache maps (some PRO).
- **Pipelining vs transactions vs Lua vs Functions**: pipelining batches commands to cut RTTs (no atomicity guarantee); `MULTI/EXEC` queues + executes atomically (no rollback, `WATCH` for optimistic CAS); Lua scripts and Redis Functions run atomically server-side and are the right tool for read-modify-write. Error-handling semantics differ across the three clients (e.g., how a mid-pipeline error surfaces).
- **Connection management theory**: multiplexing (Lettuce) vs pooling (Jedis) — the tradeoff is head-of-line blocking (a slow/blocking command stalls a multiplexed connection) vs pool exhaustion and per-connection memory (each Lettuce pooled connection carries I/O + computation thread resources).

### AWS ElastiCache / Valkey context
- **Engine choice**: ElastiCache/MemoryDB offer **Redis OSS**, **Valkey**, and (MemoryDB) a durable primary store. Per AWS's Oct 2024 launch, **Valkey is priced 20% lower on nodes and 33% lower on Serverless** than Redis OSS, with a 100 MB serverless minimum (~$6/month) vs 1 GB for Redis OSS, BSD-licensed under the Linux Foundation, and a drop-in replacement. **MemoryDB** = durable (multi-AZ transaction log, no write loss on failover) at higher cost — use it only when Redis is your system of record, not a cache. ElastiCache Redis async replication can lose unreplicated writes on failover (~35s Multi-AZ promotion).
- **Cluster mode enabled vs disabled + Lettuce**: For **cluster mode enabled**, connect to the configuration endpoint and enable `ClusterTopologyRefreshOptions` (`enablePeriodicRefresh(30s)` + `enableAllAdaptiveRefreshTriggers()` + `dynamicRefreshSources`). For **cluster mode disabled**, ElastiCache is **not** compatible with Lettuce's dynamic discovery — use `StaticMasterReplicaTopologyProvider` with explicit read/write endpoints. Set a low **JVM DNS TTL (5–10s)** because ElastiCache node IPs change. Lettuce (unlike Jedis) supports `ReadFrom` replica-read preferences (stale-read caveat). AWS recommends Lettuce ≥ 6.2.2 and ≥ 3 shards with a replica for fast failover.
- **TLS/auth**: enable in-transit TLS (`withSsl`, possibly `startTls`), and IAM authentication where available.

## Details — the phased learning plan (8 weeks, ~8–10 h/week)

### Phase 0 — Setup & framing (½ week)
- **Objectives**: Stand up a Gradle Kotlin DSL Spring Boot 3.5/4.x project; add Testcontainers (`com.redis:testcontainers-redis` and/or the Valkey module), Aurora MySQL (or MySQL Testcontainer as stand-in), Micrometer.
- **Reading**: Redis docs landing + "Redis 8 GA / AGPL" posts; skim the library README/release pages for Lettuce, Jedis, Redisson.
- **Checkpoint**: A green Testcontainers test that `PING`s Redis and Valkey images via `@ServiceConnection`.

### Phase 1 — Protocol & threading theory (1 week)
- **Objectives**: Be able to explain, formally, why Redis's single-threaded event loop yields per-command atomicity; why multiplexing is safe; RESP2 vs RESP3.
- **Theory reading**: Redis docs on pipelining, transactions, Lua scripting, client-side caching reference, and the RESP3 spec; Lettuce reference "New & Noteworthy" + RESP3 section.
- **Hands-on**: In Kotlin, exercise Lettuce sync vs async (`RedisFuture`), do a pipelined batch, and a `MULTI/EXEC` block; observe ordering. Write a Lua script for an atomic read-modify-write.
- **Korean resource**: 우아한테크세미나 "우아한 레디스" (강대명) — YouTube + SlideShare deck (single-thread, O(N) commands, collection choice, sharding).
- **Checkpoint (self-assessment)**: Write a one-page proof-style note: "Why can two threads share one Lettuce connection but not during `MULTI/EXEC`?" and "What atomicity does a pipeline NOT give you?"

### Phase 2 — Lettuce + Spring Data Redis caching (2 weeks) — **Project A**
- **Project A — Cache-aside layer over Aurora MySQL**:
  - **Goal**: Read-through/cache-aside for a read-heavy domain (e.g., product catalog) backed by Aurora MySQL, using Spring Cache + `RedisCacheManager` on Lettuce.
  - **APIs**: `@Cacheable/@CacheEvict/@Caching`, per-cache TTL via `RedisCacheConfiguration`, SpEL keys, `StringRedisTemplate`.
  - **Measure/verify**: Micrometer **cache hit ratio**, p50/p99 latency with/without cache; compare `GenericJacksonJsonRedisSerializer` (JSON, `@class`) vs `StringRedisSerializer`/per-type serializer; reproduce the `int[]` default-typing failure and fix it; add **TTL jitter**, **null caching** (penetration), and **single-flight stampede protection** (lock-based) — then implement the **XFetch** probabilistic early-expiration algorithm (Vattani, Chierichetti, Lowenstein, VLDB 2015: `delta*beta*ln(rand())`) and compare against a distributed-lock approach.
  - **Testcontainers**: Redis + MySQL containers; test TTL expiry (`setex` + await), eviction, and that cache-miss falls back to DB. Add a Valkey container variant to prove drop-in compatibility.
- **Reading**: Spring Data Redis reference (template, drivers, serializers, cache); Lettuce reference (connection sharing, cluster).
- **Korean resources**: 카카오페이 "분산 시스템에서 로컬 캐시 활용하기"; SK DEVOCEAN "Spring Boot 성능 개선 사례 (1) Redis 및 Local 캐싱"; 우아한형제들 blog caching posts.
- **Checkpoint**: Hit ratio > 90% on a realistic workload; a written comparison table of serializer tradeoffs; a passing stampede test showing DB QPS collapses from N to ~1–5.

### Phase 3 — Jedis pooling & the blocking model (1 week) — **Project B**
- **Project B — Rate limiter, Jedis vs Lettuce**:
  - **Goal**: Implement a **fixed-window and sliding-window rate limiter** in Lua, once with Jedis (`JedisPool`/`UnifiedJedis`) and once with Lettuce, to *feel* pooling vs multiplexing.
  - **APIs**: `JedisPool`/commons-pool2 config, `eval`/`evalsha`, `UnifiedJedis`; Lettuce `scriptLoad`/`evalsha`.
  - **Measure/verify**: Under load, watch pool exhaustion (Jedis) vs connection multiplexing (Lettuce); tune `maxTotal`/`maxIdle`/`minIdle`/`maxWait`.
  - **Testcontainers**: assert limiter correctness at window boundaries; concurrency test with many virtual threads/coroutines.
- **Reading**: Jedis guide + `UnifiedJedis`/`RedisClient` migration notes; Spring Data Redis "Drivers" (Jedis section).
- **Checkpoint**: Explain in writing when Jedis is still a reasonable choice (simple synchronous services, team familiarity) and the migration path Jedis 4→7 (`UnifiedJedis`, builders).

### Phase 4 — Redisson & distributed-lock correctness (2 weeks) — **Project C**
- **Project C — Distributed lock protecting a critical section on EKS**:
  - **Goal**: Protect an **inventory decrement** and a **scheduled-job leader election** across pods with `RLock` (watchdog), `tryLock(wait, lease)` semantics, then compare with **ShedLock** (scheduled-job dedup) and a **hand-rolled `SET NX PX` + Lua release** spin lock.
  - **APIs**: `RedissonClient` config (single/cluster/replicated), `getLock`, `getFencedLock`/`tryLockAndGetToken`, `getReadWriteLock`, `getSemaphore`, `RAtomicLong`; AOP annotation-based lock (à la Kurly) with `REQUIRES_NEW` so the lock outlives the transaction commit.
  - **Measure/verify**: Correctness under concurrency (no oversell / no negative stock); Redis load of spin-lock vs pub/sub lock; **demonstrate the fencing-token gap** — simulate a GC pause/lease expiry and show two holders, then add a fencing token checked at the DB write to reject the stale writer.
  - **Testcontainers**: multi-instance simulation (run N app contexts against one Redis), inject delays; verify only one leader runs the scheduled job.
- **Primary reading (do this carefully)**: Kleppmann "How to do distributed locking"; antirez "Is Redlock safe?" (antirez.com/news/101); Redis docs "Distributed Locks with Redis" (fencing-token + Analysis-of-Redlock sections); Redisson locks doc.
- **Korean resources**: 컬리(Kurly) tech blog — "풀필먼트 입고 서비스팀에서 분산락을 사용하는 방법 - Spring Redisson" (helloworld.kurly.com/blog/distributed-redisson-lock/), the widely-cited reference for AOP-based Redisson locks: they chose Redisson over Lettuce because Lettuce forces you to hand-build `setnx` spin-locks that load Redis more as traffic rises, while Redisson's Lock interface uses pub/sub release-signals and built-in lease/timeout; Hyperconnect "레디스를 활용한 분산 락과 안전하고 빠른 락의 구현" (hyperconnect.github.io, 2019-11-15); S-Core "Redis를 활용한 안전하게 동시성 이슈 제어하기"; SSG TECH "AOP로 Redis 분산락 구현"; 우아한형제들 "선물하기 시스템의 상품 재고는 어떻게 관리되어질까?" (RDB+Redis Set sync pattern).
- **Checkpoint**: Write a rigorous safety/liveness argument: state the mutual-exclusion (safety) and deadlock-freedom (liveness) properties, identify exactly which timing assumptions each lock breaks, and justify when `RLock` is "safe enough" vs when you must use fencing tokens or ZooKeeper/etcd.

### Phase 5 — AWS/Valkey + benchmarking (1.5 weeks) — **Project D**
- **Project D — Pipelining/Lua benchmark + ElastiCache/Valkey config**:
  - **Goal**: Benchmark pipelining vs per-command vs Lua across Lettuce/Jedis/Redisson; deploy against a local cluster (Testcontainers) and reason about ElastiCache cluster-mode config.
  - **APIs**: Lettuce cluster `ClusterTopologyRefreshOptions`, `ReadFrom`; `StaticMasterReplicaTopologyProvider` (cluster-mode-disabled); TLS/IAM auth.
  - **Measure/verify**: JMH microbench for client throughput; k6/Gatling for end-to-end load; compare Redis vs Valkey images.
  - **Testcontainers**: cluster-mode test if feasible; Valkey image via the Testcontainers Valkey module; failover-behavior notes.
- **Reading**: AWS ElastiCache "Lettuce client configuration" best-practices; AWS Redis-clients blog (Jedis vs Lettuce failover); Valkey migration/protocol docs.
- **Checkpoint**: A benchmark report with numbers + a decision memo: "For our EKS microservices on ElastiCache, which engine/mode/client, and why."

### Capstone self-assessment
Produce a 2–3 page "architecture decision record" choosing clients per use case in your stack (cache layer, rate limiter, distributed lock, session store), citing the primary sources, with a fencing-token policy for correctness-critical locks.

## Resources

**Official docs**
- Lettuce reference (redis.github.io/lettuce), New & Noteworthy, HA-Sharding, Releases (GitHub redis/lettuce)
- Jedis guide (redis.io/docs/latest/develop/clients/jedis), GitHub redis/jedis releases, `UnifiedJedis` Javadoc
- Redisson reference (redisson.pro/docs), Locks-and-synchronizers, GitHub wiki "Distributed locks and synchronizers", PRO feature comparison
- Spring Data Redis reference (template, drivers, serializers), Spring Boot 3.0 migration guide (property rename), `LettucePoolingClientConfiguration` Javadoc
- Redis.io: transactions, pipelining, Lua scripting, `CLIENT TRACKING`, client-side-caching reference, Distributed Locks pattern page, RESP3 spec
- Testcontainers Redis module (com.redis:testcontainers-redis) and Valkey module; Valkey clients page (valkey.io/clients), valkey-glide (glide.valkey.io)

**Primary sources (locking + licensing)**
- Martin Kleppmann, "How to do distributed locking" (martin.kleppmann.com, 2016-02-08)
- antirez (Salvatore Sanfilippo), "Is Redlock safe?" (antirez.com/news/101)
- antirez, "Redis is open source again" (antirez.com/news/151) + Redis "AGPLv3" blog (redis.io/blog/agplv3/)
- Vattani, Chierichetti, Lowenstein, "Optimal Probabilistic Cache Stampede Prevention" (VLDB 2015; cseweb.ucsd.edu/~avattani/papers/cache_stampede.pdf) + Internet Archive XFetch (RedisConf17)

**Korean resources (한국어 자료)**
- 우아한테크세미나 "우아한 레디스" (강대명) — YouTube + SlideShare 196314086
- 컬리(Kurly) tech blog — "풀필먼트 입고 서비스팀에서 분산락을 사용하는 방법 - Spring Redisson" (helloworld.kurly.com/blog/distributed-redisson-lock/)
- 우아한형제들 기술블로그 — "선물하기 시스템의 상품 재고는 어떻게 관리되어질까?" (techblog.woowahan.com/2709/)
- 카카오페이 — "분산 시스템에서 로컬 캐시 활용하기" (tech.kakaopay.com)
- Hyperconnect — "레디스를 활용한 분산 락과 안전하고 빠른 락의 구현" (hyperconnect.github.io, 2019-11-15)
- S-Core — "Redis를 활용한 안전하게 동시성 이슈 제어하기"; SSG TECH — AOP Redis 분산락; SK DEVOCEAN — Spring Boot Redis 캐싱
- 레디스게이트 (redisgate.kr) — Korean Redis reference

**Tutorials / talks (with a quality note)**
- Baeldung: ShedLock with Spring, Redis Testcontainers, Spring Data Redis — good for hands-on scaffolding, but verify version currency (some predate SDR 4.0/Jackson 3).
- AWS Database Blog: "Best practices: Redis clients and Amazon ElastiCache"; jeroenreijn.com Jedis-vs-Lettuce-on-ElastiCache series.
- SpringOne / Devoxx talks on Spring Data Redis; RedisConf/Redis Day client-library talks (YouTube redisinc).

**GitHub examples worth studying**
- spring-projects/spring-data-examples (redis module)
- redisson/redisson examples; redis-field-engineering/testcontainers-redis
- internetarchive/xfetch (cache-stampede harness)

## Recommendations
1. **Adopt Lettuce as your default now**; do not add commons-pool2 pooling unless you profile head-of-line blocking from blocking/transactional commands. Trigger to revisit: measurable latency from blocking ops (`BLPOP`, `MULTI/EXEC`) sharing the multiplexed connection — remember a single shared connection already handles ~100k QPS in benchmarks, so raw throughput is rarely the reason to pool.
2. **Introduce Redisson only for distributed primitives** (locks, semaphores, rate limiters, leader election). For **correctness-critical** sections (money, inventory), require **fencing tokens** end-to-end (`getFencedLock`) or move coordination to Aurora (optimistic/conditional writes) — treat plain `RLock` as an *efficiency* lock. Trigger to escalate to ZooKeeper/etcd: any lock whose violation causes financial or data-integrity loss that cannot be fenced at the resource.
3. **For scheduled-job dedup on EKS, prefer ShedLock** over hand-rolling; it's simpler and purpose-built. Use Redisson `RLock` only when you need general-purpose locking beyond `@Scheduled`.
4. **On AWS, default new deployments to Valkey** (ElastiCache or MemoryDB) for the 20% node / 33% serverless savings and BSD licensing; only pick Redis 8 if you need a Redis-8-only feature (e.g., vector sets, bundled modules) and can accept AGPLv3 review. Use MemoryDB only when Redis is your system of record.
5. **In Spring Data Redis 4.x, migrate off the deprecated Jackson 2 serializers** to `GenericJacksonJsonRedisSerializer`/Jackson 3, and lock down default typing with a `PolymorphicTypeValidator`. Standardize a serialization-versioning convention to avoid cache-payload drift.
6. **Bake in cache-resilience defaults**: TTL jitter, null/negative caching with short TTL, and stampede protection (single-flight lock or XFetch). Target ≥ 90–95% hit ratio; below ~80%, re-examine the caching strategy.

## Caveats
- Some cited blog posts carry **future-dated timestamps (2026)** and secondhand benchmark numbers (e.g., specific ElastiCache/Valkey per-ECPU prices, Redlock false-positive rates); treat those figures as directional and re-verify against **official AWS pricing** and first-party benchmarks before making commitments. The Valkey throughput headline is **~230%/1.2M QPS** (Valkey 8 async I/O threading); the higher ~270% figure applies specifically to *experimental Valkey-over-RDMA*, not stock Valkey.
- The Redisson OSS-vs-PRO performance split is contested in community threads; benchmark on *your* workload before assuming OSS performance parity or before paying for PRO.
- Spring Data Redis has **no headline Valkey-compatibility statement**; compatibility is inferred from Lettuce/Jedis speaking Valkey's protocol unchanged. Verify against your exact server version.
- Client-side caching is **Standalone-only in Lettuce** and beta in Jedis — do not assume it works in ElastiCache cluster mode.
- Versions move fast: re-check the latest Lettuce 7.x, Jedis 7.x/8.x, Redisson, and Spring Boot 4.x/Spring Data Redis 4.x at the moment you start.