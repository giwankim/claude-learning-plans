---
title: "Mastering JVM Redis Clients with Spring Boot: A Rigorous Learning Plan (Lettuce, Jedis, Redisson)"
category: "Data & Messaging"
description: "An 8-week, part-time (roughly 8-10 h/week) five-phase plan for mastering JVM Redis clients on a Kotlin/Spring Boot/EKS stack. Lettuce is the production default (Netty-based multiplexing, thread-safe shared connection, Spring Data Redis default), Redisson comes in only where distributed primitives (locks, semaphores, rate limiters, leader election) are needed, and Jedis stays a study and comparison tool, with ElastiCache/MemoryDB for Valkey recommended for new AWS work. The plan centers on the Kleppmann-versus-antirez distributed-lock debate (efficiency vs correctness locks, why Redlock/RLock needs fencing tokens for correctness), and pairs every phase with primary-source reading, a Kotlin/Testcontainers project, and a self-assessment checkpoint through protocol and threading theory, Spring Data Redis caching, pooling models, and benchmarking."
---

# Mastering JVM Redis Clients with Spring Boot: A Rigorous Learning Plan (Lettuce, Jedis, Redisson)

## TL;DR
- Lettuce is the correct default for your Kotlin/Spring Boot/EKS stack (Netty-based multiplexing, thread-safe shared connection, Spring Data Redis default). Add Redisson only where you need distributed primitives (locks, semaphores, rate limiters, leader election), and treat Jedis as a study and comparison tool rather than your production driver. On AWS, prefer ElastiCache or MemoryDB for Valkey for new work: AWS prices it 20% lower on nodes and 33% lower on Serverless than Redis OSS (Oct 2024 launch), it is BSD-licensed under the Linux Foundation, and it is drop-in compatible with Lettuce, Jedis, and Redisson.
- The single most important theoretical lesson is that distributed locks split into "efficiency" locks, where Redlock and Redisson are fine, and "correctness" locks, where they are not sufficient without fencing tokens. The Kleppmann versus antirez debate is the primary source you must read closely, and it should reshape how you use `RLock` for inventory or money.
- The plan runs 8 weeks part-time at roughly 8-10 h/week, in 5 phases: (1) protocol and threading theory, (2) Lettuce plus Spring Data Redis caching, (3) the Jedis pooling and blocking model, (4) Redisson and distributed-lock correctness, (5) AWS/Valkey plus benchmarking. Each phase has primary-source reading, a Kotlin/Testcontainers project, and a self-assessment checkpoint.

## Key Findings

### Current state of the ecosystem (verified 2025-2026)
- Lettuce moved under the Redis org and became an official client with the Redis 7.2 release, and it was relicensed from Apache 2.0 to MIT. The 7.x line (7.6.0, tested against Redis 8.8, works on Java 8 through 24, built on Netty 4.2) is current. Lettuce remains the Spring Boot default.
- Jedis is on the 7.x line (7.2.0 current-stable, with 8.0.0-beta introducing RESP3 auto-negotiation by default). Jedis 7.0 introduced a new client family, `RedisClient`, `RedisClusterClient`, and `RedisSentinelClient`, replacing `JedisPooled`, `JedisCluster`, and `JedisSentineled`, all built on the `UnifiedJedis` base. Client-side caching (RESP3, Redis 7.4 or later) is supported in `UnifiedJedis`, `JedisPooled`, and `JedisCluster`.
- Redisson is actively maintained, works as both a Valkey and Redis client, and offers 50+ distributed objects. It has a sharp open-source versus PRO split: the "ultra-fast client engine," data partitioning across cluster masters, local-cache variants, and reliable messaging are PRO-only. Community discussion questions whether raw performance optimizations should be paywalled, so factor that into adoption.
- Redis licensing has been a rollercoaster: BSD, then RSALv2/SSPLv1 (March 2024), then the Valkey fork under the Linux Foundation, then Redis 8.0 re-adding AGPLv3 on May 1, 2025 after antirez rejoined. That last step is confirmed by CEO Rowan Trollope's post "Redis is now available under the AGPLv3 open source license" and by antirez's own words: *"I'm happy that Redis is open source software again, under the terms of the AGPLv3 license"* (antirez.com/news/151). Redis 8 is tri-licensed (AGPLv3, RSALv2, SSPLv1) and folds the former Redis Stack modules (JSON, Time Series, probabilistic types, Query Engine) into core. AGPLv3's network-copyleft matters only if you modify Redis and offer it as a service; for internal use it changes little.
- Spring Boot 4.x is current (4.0 in Nov 2025, 4.1 in June 2026), and Spring Boot 3.5 reached EOL on June 30, 2026. Spring Data Redis 4.x still defaults to Lettuce. Critically, Spring Data Redis 4.0 deprecated the Jackson 2 serializers (`GenericJackson2JsonRedisSerializer`, `Jackson2JsonRedisSerializer`, `Jackson2HashMapper`, all `@Deprecated(since="4.0", forRemoval=true)`) in favor of Jackson 3 equivalents (`GenericJacksonJsonRedisSerializer` and friends), tracking Spring Framework 7 and Boot 4's move to Jackson 3 (`tools.jackson.databind`). The property namespace moved from `spring.redis.*` to `spring.data.redis.*` back in Spring Boot 3.0, per the official migration guide: *"Configuration Properties for Redis have moved from `spring.redis.` to `spring.data.redis.`"*.
- Valkey clients: both Lettuce and Jedis connect to Valkey unchanged, because Valkey is a fork of Redis 7.2.4 speaking byte-identical RESP2 and RESP3 (its `INFO` even reports `redis_version:7.2.4` for compatibility). There are two official Valkey Java clients: valkey-glide (`io.valkey:valkey-glide`, AWS-sponsored, a Rust core with Java bindings, GA) and valkey-java (Jedis-derived). Redisson also officially supports Valkey, where `RMap`, `RLock`, and `RBucket` work unchanged. One note: proprietary Redis modules such as RediSearch and RedisJSON are not in Valkey core.

### The three clients, compared

| Dimension | Lettuce | Jedis | Redisson |
|---|---|---|---|
| Transport | Netty NIO, non-blocking | BIO (blocking socket) | Netty NIO, non-blocking |
| Thread model | One thread-safe connection multiplexes many threads | One connection = one thread; needs a pool | Connection pool + async engine |
| Pooling | Not needed for normal use (shared connection); pool only for blocking cmds and MULTI/EXEC | Required (`JedisPool`/commons-pool2) | Managed internally |
| API | sync / async (`RedisFuture`) / reactive / Kotlin coroutines | synchronous | data-structure and service abstractions (`RMap`, `RLock`, …) |
| Best for | Default Spring driver; async/reactive; Spring integration | Simple synchronous apps; feeling the pooling model | Distributed locks, collections, rate limiters, leader election |
| License | MIT | MIT | Apache 2.0 (OSS) / commercial PRO |
| Spring Boot default | Yes | alternative | via `redisson-spring-boot-starter` |

Why Lettuce is Spring's default, and why pooling is usually unnecessary: Lettuce multiplexes commands over a single Netty connection using TCP's ordered send and receive, so multiple threads may share one connection as long as they avoid blocking (`BLPOP`) and transactional (`MULTI`/`EXEC`) operations, which would otherwise cause head-of-line blocking for other users of the connection. A single thread-safe shared Lettuce connection scales far beyond naive expectations: maintainer benchmarks show roughly 100k QPS under about 200 concurrent threads on an 8-core machine (localhost, Lettuce 6.x). The low-thousands QPS figure people quote really describes a single blocking synchronous caller, not the multiplexed connection. Pooling (via commons-pool2 with `LettucePoolingClientConfiguration`, or `shareNativeConnection=false`) is only genuinely needed for blocking and transactional cases. Jedis, by contrast, uses blocking I/O, so one connection serves one thread at a time and a `JedisPool` is mandatory under concurrency.

### Distributed locking: the core theory you must internalize
- Redisson `RLock` uses a Redis HASH plus Lua scripts for atomic acquire and release, a pub/sub channel to notify waiters (avoiding busy spin), reentrancy via a counter, and a watchdog (a Netty `HashedWheelTimer`) that renews the lease every 10s or so (the default `lockWatchdogTimeout` is 30s), but only when no explicit `leaseTime` is set. If you pass a `leaseTime`, for instance `tryLock(10, 30, SECONDS)`, the watchdog is disabled and the lock auto-releases. There is also a `SpinLock` variant (exponential backoff, no pub/sub) to avoid pub/sub fan-out storms in clusters.
- A Lettuce-style hand-rolled lock is `SET key val NX PX ttl` plus a Lua compare-and-delete release, driven by a client-side spin loop. This hammers Redis with repeated `SETNX` attempts: Korean engineering write-ups (Hyperconnect, S-Core) measure roughly 1,980 lock attempts per second while one client waits. Reach for this only when you fail fast, with no retries.
- The Kleppmann versus antirez debate is required primary reading. Martin Kleppmann's "How to do distributed locking" (Feb 8, 2016) argues Redlock is unsafe for correctness because its safety rests on timing assumptions (bounded clock drift, network delay, GC pauses), so a stop-the-world GC pause or clock jump can let two clients both believe they hold the lock. His prescription is fencing tokens, in his words: *"a fencing token is simply a number that increases (e.g. incremented by the lock service) every time a client acquires the lock… this leads us to the first big problem with Redlock: it does not have any facility for generating fencing tokens."* antirez's rebuttal, "Is Redlock safe?" (antirez.com/news/101), argues that Redlock re-checks elapsed time after acquisition, which immunizes it against acquisition-phase delays, and that random tokens with check-and-set give equivalent safety. The synthesis: both are right for different goals. Redlock and Redisson are fine for efficiency locks (deduplicating cron jobs, reducing duplicate work) but insufficient for correctness locks (money, inventory) without end-to-end fencing tokens. Redisson now ships a fenced lock (`getFencedLock`, `tryLockAndGetToken`) precisely for this. For hard correctness, ZooKeeper or etcd (linearizable, sequential znodes) or a DB conditional or optimistic write is the stronger tool.

### Spring Data Redis integration essentials
- Templates: `RedisTemplate` (Java serializer by default) versus `StringRedisTemplate` (`StringRedisSerializer`, human-readable). Configure key, value, and hash serializers explicitly, which is a very common Kotlin pitfall.
- Serializers and Kotlin: `GenericJackson2JsonRedisSerializer` (now `GenericJacksonJsonRedisSerializer` in SDR 4.0) embeds `@class` type hints via Jackson default typing, which requires `NON_FINAL` or `activateDefaultTyping` and breaks on `int[]` and other primitive arrays and on Kotlin `data class` edge cases. Default typing is also a known deserialization-security risk, so you must use a `PolymorphicTypeValidator`. For Kotlin, register the Jackson Kotlin module and prefer a per-type `Jackson2JsonRedisSerializer` or a locked-down `ObjectMapper`. Beware serialization version drift, since changing a data class shape silently breaks cached payloads.
- Spring Cache: `@Cacheable`, `@CachePut`, `@CacheEvict`, and `@Caching`, with `RedisCacheManager` for per-cache TTL via `RedisCacheConfiguration` and SpEL key generation. Enable statistics for Micrometer hit-ratio metrics.
- Autoconfiguration: `spring.data.redis.*` (host, port, ssl, client-name, timeout, `lettuce.pool.*`). Lettuce pooling requires the `commons-pool2` dependency, and `LettuceConnectionFactory` uses a shared native connection by default (min 8, max 8 pool when enabled).
- Transactions: Redis `MULTI`/`EXEC` is not an RDBMS transaction. There is no rollback and no isolation in the ACID sense; commands are queued and executed atomically, but a logic error mid-transaction is not undone. Use `SessionCallback` with `enableTransactionSupport`, or prefer Lua scripts and Redis Functions for true server-side atomicity. This is a key conceptual difference worth teaching explicitly.
- `@RedisHash` and repositories: secondary indexes and `@RedisHash` exist but have real limitations (no rich querying, index maintenance overhead, easy to misuse in production). They are fine for simple session-like objects, not as a general ORM.
- Production pitfalls: `KEYS` in production (O(N), and it blocks the single thread, so use `SCAN`), hot keys, big keys, cache stampede or thundering herd, cache penetration (null caching or a Bloom filter), cache avalanche (TTL jitter of about ±10%), and Redis `DEL` versus `UNLINK`.

### Underlying theory connecting to implementation
- Redis threading: Redis executes commands on a single thread (an event loop), which is why it gives atomicity for individual commands and Lua scripts without locks, and why O(N) commands (`KEYS`, a big `SMEMBERS`) are dangerous. Redis 6+ added I/O threads for network read/write parsing only, so command execution stays single-threaded. Valkey pushed further with asynchronous I/O threading: Valkey 8.0 (Linux Foundation, Sept 2024) reports throughput up to 1.2 million requests per second on AWS r7g instances, over 3x the previous version's roughly 380K, and AWS and valkey.io cite up to about 230% higher throughput and about 70% lower latency (measured rising from 360K to 1.19M req/s against Valkey 7.2 with 8 I/O threads on C7g.16xlarge). This single-threaded command model is the root cause that shapes all three clients' designs, since multiplexing works precisely because the server serializes anyway.
- RESP2 versus RESP3: RESP3 (Redis 6) adds typed replies and push messages, which enable invalidation messages and client-side caching on the same connection. Lettuce 6+ and Jedis 8 default to or negotiate RESP3, and you may need to pin RESP2 (`ClientOptions.protocolVersion(RESP2)`) against older Redis Stack.
- Server-assisted client-side caching (`CLIENT TRACKING`): the default mode, where the server remembers read keys, versus broadcasting mode, where you subscribe to prefixes with zero server memory. Lettuce ships a `CacheFrontend`/`ClientSideCaching` API, but only for Standalone, not for Cluster or Master-Replica, since push messages are node-local. Jedis supports it in beta (RESP3, Redis 7.4 or later). Redisson offers local-cache maps, some of them PRO.
- Pipelining versus transactions versus Lua versus Functions: pipelining batches commands to cut RTTs with no atomicity guarantee; `MULTI`/`EXEC` queues and then executes atomically with no rollback, using `WATCH` for optimistic CAS; Lua scripts and Redis Functions run atomically server-side and are the right tool for read-modify-write. Error-handling semantics differ across the three clients, including how a mid-pipeline error surfaces.
- Connection management theory: multiplexing (Lettuce) versus pooling (Jedis). The tradeoff is head-of-line blocking, where a slow or blocking command stalls a multiplexed connection, against pool exhaustion and per-connection memory, since each Lettuce pooled connection carries I/O and computation thread resources.

### AWS ElastiCache and Valkey context
- Engine choice: ElastiCache and MemoryDB offer Redis OSS, Valkey, and (in MemoryDB) a durable primary store. Per AWS's Oct 2024 launch, Valkey is priced 20% lower on nodes and 33% lower on Serverless than Redis OSS, with a 100 MB serverless minimum (about $6/month) against 1 GB for Redis OSS, BSD-licensed under the Linux Foundation, and it is a drop-in replacement. MemoryDB is durable (a multi-AZ transaction log, no write loss on failover) at higher cost, so use it only when Redis is your system of record rather than a cache. ElastiCache Redis async replication can lose unreplicated writes on failover, with roughly 35s Multi-AZ promotion.
- Cluster mode enabled versus disabled with Lettuce: for cluster mode enabled, connect to the configuration endpoint and enable `ClusterTopologyRefreshOptions` (`enablePeriodicRefresh(30s)`, `enableAllAdaptiveRefreshTriggers()`, `dynamicRefreshSources`). For cluster mode disabled, ElastiCache is not compatible with Lettuce's dynamic discovery, so use `StaticMasterReplicaTopologyProvider` with explicit read and write endpoints. Set a low JVM DNS TTL (5-10s) because ElastiCache node IPs change. Lettuce, unlike Jedis, supports `ReadFrom` replica-read preferences, with the usual stale-read caveat. AWS recommends Lettuce 6.2.2 or later and at least 3 shards with a replica for fast failover.
- TLS and auth: enable in-transit TLS (`withSsl`, possibly `startTls`), and IAM authentication where available.

## Details: the phased learning plan (8 weeks, ~8-10 h/week)

### Phase 0: setup and framing (half a week)
- Objectives: stand up a Gradle Kotlin DSL Spring Boot 3.5/4.x project, and add Testcontainers (`com.redis:testcontainers-redis` and/or the Valkey module), Aurora MySQL (or a MySQL Testcontainer as a stand-in), and Micrometer.
- Reading: the Redis docs landing page plus the "Redis 8 GA / AGPL" posts, and a skim of the library README and release pages for Lettuce, Jedis, and Redisson.
- Checkpoint: a green Testcontainers test that `PING`s Redis and Valkey images via `@ServiceConnection`.

### Phase 1: protocol and threading theory (1 week)
- Objectives: be able to explain formally why Redis's single-threaded event loop yields per-command atomicity, why multiplexing is safe, and how RESP2 differs from RESP3.
- Theory reading: the Redis docs on pipelining, transactions, Lua scripting, and the client-side caching reference, plus the RESP3 spec; the Lettuce reference "New & Noteworthy" and RESP3 section.
- Hands-on: in Kotlin, exercise Lettuce sync against async (`RedisFuture`), do a pipelined batch and a `MULTI`/`EXEC` block, and observe ordering. Write a Lua script for an atomic read-modify-write.
- Korean resource: 우아한테크세미나 "우아한 레디스" (강대명), on YouTube and as a SlideShare deck, covering single-thread behavior, O(N) commands, collection choice, and sharding.
- Checkpoint (self-assessment): write a one-page proof-style note answering "Why can two threads share one Lettuce connection but not during `MULTI`/`EXEC`?" and "What atomicity does a pipeline not give you?"

### Phase 2: Lettuce and Spring Data Redis caching (2 weeks), Project A
- Project A, a cache-aside layer over Aurora MySQL:
  - Goal: read-through and cache-aside for a read-heavy domain such as a product catalog backed by Aurora MySQL, using Spring Cache and `RedisCacheManager` on Lettuce.
  - APIs: `@Cacheable`/`@CacheEvict`/`@Caching`, per-cache TTL via `RedisCacheConfiguration`, SpEL keys, `StringRedisTemplate`.
  - Measure and verify: Micrometer cache hit ratio, and p50/p99 latency with and without the cache. Compare `GenericJacksonJsonRedisSerializer` (JSON with `@class`) against `StringRedisSerializer` and a per-type serializer. Reproduce the `int[]` default-typing failure and fix it. Add TTL jitter, null caching (penetration), and single-flight stampede protection (lock-based), then implement the XFetch probabilistic early-expiration algorithm (Vattani, Chierichetti, Lowenstein, VLDB 2015: `delta*beta*ln(rand())`) and compare it against a distributed-lock approach.
  - Testcontainers: Redis and MySQL containers. Test TTL expiry (`setex` plus await), eviction, and that a cache miss falls back to the DB. Add a Valkey container variant to prove drop-in compatibility.
- Reading: the Spring Data Redis reference (template, drivers, serializers, cache) and the Lettuce reference (connection sharing, cluster).
- Korean resources: 카카오페이 "분산 시스템에서 로컬 캐시 활용하기"; SK DEVOCEAN "Spring Boot 성능 개선 사례 (1) Redis 및 Local 캐싱"; the 우아한형제들 blog caching posts.
- Checkpoint: a hit ratio above 90% on a realistic workload, a written comparison table of serializer tradeoffs, and a passing stampede test showing DB QPS collapse from N to roughly 1-5.

### Phase 3: Jedis pooling and the blocking model (1 week), Project B
- Project B, a rate limiter in Jedis versus Lettuce:
  - Goal: implement a fixed-window and a sliding-window rate limiter in Lua, once with Jedis (`JedisPool`/`UnifiedJedis`) and once with Lettuce, so you feel pooling against multiplexing.
  - APIs: `JedisPool` and commons-pool2 config, `eval`/`evalsha`, `UnifiedJedis`; on the Lettuce side, `scriptLoad`/`evalsha`.
  - Measure and verify: under load, watch pool exhaustion with Jedis against connection multiplexing with Lettuce, and tune `maxTotal`, `maxIdle`, `minIdle`, and `maxWait`.
  - Testcontainers: assert limiter correctness at window boundaries, with a concurrency test using many virtual threads or coroutines.
- Reading: the Jedis guide plus the `UnifiedJedis`/`RedisClient` migration notes, and the Spring Data Redis "Drivers" (Jedis section).
- Checkpoint: explain in writing when Jedis is still a reasonable choice (simple synchronous services, team familiarity) and what the Jedis 4-to-7 migration path looks like (`UnifiedJedis`, builders).

### Phase 4: Redisson and distributed-lock correctness (2 weeks), Project C
- Project C, a distributed lock protecting a critical section on EKS:
  - Goal: protect an inventory decrement and a scheduled-job leader election across pods with `RLock` (watchdog) and `tryLock(wait, lease)` semantics, then compare with ShedLock (scheduled-job dedup) and a hand-rolled `SET NX PX` plus Lua release spin lock.
  - APIs: `RedissonClient` config (single, cluster, replicated), `getLock`, `getFencedLock`/`tryLockAndGetToken`, `getReadWriteLock`, `getSemaphore`, `RAtomicLong`, and an AOP annotation-based lock in the style of Kurly's, with `REQUIRES_NEW` so the lock outlives the transaction commit.
  - Measure and verify: correctness under concurrency (no oversell, no negative stock); the Redis load of a spin lock against a pub/sub lock; and a demonstration of the fencing-token gap, by simulating a GC pause or lease expiry to show two holders, then adding a fencing token checked at the DB write to reject the stale writer.
  - Testcontainers: a multi-instance simulation (run N app contexts against one Redis), inject delays, and verify only one leader runs the scheduled job.
- Primary reading (do this carefully): Kleppmann's "How to do distributed locking"; antirez's "Is Redlock safe?" (antirez.com/news/101); the Redis docs "Distributed Locks with Redis" (the fencing-token and Analysis-of-Redlock sections); the Redisson locks doc.
- Korean resources: 컬리(Kurly) tech blog, "풀필먼트 입고 서비스팀에서 분산락을 사용하는 방법 - Spring Redisson" (helloworld.kurly.com/blog/distributed-redisson-lock/), the widely-cited reference for AOP-based Redisson locks. They chose Redisson over Lettuce because Lettuce forces you to hand-build `setnx` spin locks that load Redis more as traffic rises, while Redisson's Lock interface uses pub/sub release signals and built-in lease and timeout. Also Hyperconnect's "레디스를 활용한 분산 락과 안전하고 빠른 락의 구현" (hyperconnect.github.io, 2019-11-15); S-Core's "Redis를 활용한 안전하게 동시성 이슈 제어하기"; SSG TECH's "AOP로 Redis 분산락 구현"; 우아한형제들's "선물하기 시스템의 상품 재고는 어떻게 관리되어질까?" (the RDB plus Redis Set sync pattern).
- Checkpoint: write a rigorous safety and liveness argument. State the mutual-exclusion (safety) and deadlock-freedom (liveness) properties, identify exactly which timing assumptions each lock breaks, and justify when `RLock` is "safe enough" against when you must use fencing tokens or ZooKeeper/etcd.

### Phase 5: AWS/Valkey and benchmarking (1.5 weeks), Project D
- Project D, a pipelining and Lua benchmark plus ElastiCache/Valkey config:
  - Goal: benchmark pipelining against per-command against Lua across Lettuce, Jedis, and Redisson; deploy against a local cluster (Testcontainers) and reason about ElastiCache cluster-mode config.
  - APIs: Lettuce cluster `ClusterTopologyRefreshOptions` and `ReadFrom`; `StaticMasterReplicaTopologyProvider` for cluster-mode-disabled; TLS and IAM auth.
  - Measure and verify: a JMH microbenchmark for client throughput, k6 or Gatling for end-to-end load, and a comparison of Redis against Valkey images.
  - Testcontainers: a cluster-mode test if feasible, the Valkey image via the Testcontainers Valkey module, and failover-behavior notes.
- Reading: the AWS ElastiCache "Lettuce client configuration" best practices; the AWS Redis-clients blog (Jedis vs Lettuce failover); the Valkey migration and protocol docs.
- Checkpoint: a benchmark report with numbers plus a decision memo answering "For our EKS microservices on ElastiCache, which engine, mode, and client, and why."

### Capstone self-assessment
Produce a 2-3 page architecture decision record choosing clients per use case in your stack (cache layer, rate limiter, distributed lock, session store), citing the primary sources, with a fencing-token policy for correctness-critical locks.

## Resources

**Official docs**
- Lettuce reference (redis.github.io/lettuce), New & Noteworthy, HA-Sharding, Releases (GitHub redis/lettuce)
- Jedis guide (redis.io/docs/latest/develop/clients/jedis), GitHub redis/jedis releases, `UnifiedJedis` Javadoc
- Redisson reference (redisson.pro/docs), Locks-and-synchronizers, the GitHub wiki "Distributed locks and synchronizers", PRO feature comparison
- Spring Data Redis reference (template, drivers, serializers), the Spring Boot 3.0 migration guide (property rename), `LettucePoolingClientConfiguration` Javadoc
- Redis.io: transactions, pipelining, Lua scripting, `CLIENT TRACKING`, the client-side-caching reference, the Distributed Locks pattern page, the RESP3 spec
- Testcontainers Redis module (com.redis:testcontainers-redis) and Valkey module; the Valkey clients page (valkey.io/clients), valkey-glide (glide.valkey.io)

**Primary sources (locking and licensing)**
- Martin Kleppmann, "How to do distributed locking" (martin.kleppmann.com, 2016-02-08)
- antirez (Salvatore Sanfilippo), "Is Redlock safe?" (antirez.com/news/101)
- antirez, "Redis is open source again" (antirez.com/news/151), plus the Redis "AGPLv3" blog (redis.io/blog/agplv3/)
- Vattani, Chierichetti, Lowenstein, "Optimal Probabilistic Cache Stampede Prevention" (VLDB 2015; cseweb.ucsd.edu/~avattani/papers/cache_stampede.pdf), plus the Internet Archive XFetch talk (RedisConf17)

**Korean resources (한국어 자료)**
- 우아한테크세미나 "우아한 레디스" (강대명), on YouTube and SlideShare 196314086
- 컬리(Kurly) tech blog, "풀필먼트 입고 서비스팀에서 분산락을 사용하는 방법 - Spring Redisson" (helloworld.kurly.com/blog/distributed-redisson-lock/)
- 우아한형제들 기술블로그, "선물하기 시스템의 상품 재고는 어떻게 관리되어질까?" (techblog.woowahan.com/2709/)
- 카카오페이, "분산 시스템에서 로컬 캐시 활용하기" (tech.kakaopay.com)
- Hyperconnect, "레디스를 활용한 분산 락과 안전하고 빠른 락의 구현" (hyperconnect.github.io, 2019-11-15)
- S-Core, "Redis를 활용한 안전하게 동시성 이슈 제어하기"; SSG TECH, AOP Redis 분산락; SK DEVOCEAN, Spring Boot Redis 캐싱
- 레디스게이트 (redisgate.kr), a Korean Redis reference

**Tutorials and talks (with a quality note)**
- Baeldung: ShedLock with Spring, Redis Testcontainers, Spring Data Redis. Good for hands-on scaffolding, but verify version currency, since some predate SDR 4.0 and Jackson 3.
- AWS Database Blog: "Best practices: Redis clients and Amazon ElastiCache"; the jeroenreijn.com Jedis-versus-Lettuce-on-ElastiCache series.
- SpringOne and Devoxx talks on Spring Data Redis; RedisConf and Redis Day client-library talks (YouTube redisinc).

**GitHub examples worth studying**
- spring-projects/spring-data-examples (redis module)
- redisson/redisson examples; redis-field-engineering/testcontainers-redis
- internetarchive/xfetch (cache-stampede harness)

## Recommendations
1. Adopt Lettuce as your default now, and do not add commons-pool2 pooling unless you profile head-of-line blocking from blocking or transactional commands. The trigger to revisit: measurable latency from blocking ops (`BLPOP`, `MULTI`/`EXEC`) sharing the multiplexed connection. Remember that a single shared connection already handles about 100k QPS in benchmarks, so raw throughput is rarely the reason to pool.
2. Introduce Redisson only for distributed primitives (locks, semaphores, rate limiters, leader election). For correctness-critical sections (money, inventory), require fencing tokens end to end (`getFencedLock`) or move coordination to Aurora with optimistic or conditional writes, and treat plain `RLock` as an efficiency lock. The trigger to escalate to ZooKeeper or etcd: any lock whose violation causes financial or data-integrity loss that cannot be fenced at the resource.
3. For scheduled-job dedup on EKS, prefer ShedLock over hand-rolling, since it's simpler and purpose-built. Use Redisson `RLock` only when you need general-purpose locking beyond `@Scheduled`.
4. On AWS, default new deployments to Valkey (ElastiCache or MemoryDB) for the 20% node and 33% serverless savings and the BSD licensing. Pick Redis 8 only if you need a Redis-8-only feature such as vector sets or the bundled modules, and can accept AGPLv3 review. Use MemoryDB only when Redis is your system of record.
5. In Spring Data Redis 4.x, migrate off the deprecated Jackson 2 serializers to `GenericJacksonJsonRedisSerializer` and Jackson 3, and lock down default typing with a `PolymorphicTypeValidator`. Standardize a serialization-versioning convention to avoid cache-payload drift.
6. Bake in cache-resilience defaults: TTL jitter, null and negative caching with a short TTL, and stampede protection (a single-flight lock or XFetch). Target a hit ratio of 90-95% or better, and re-examine the caching strategy below about 80%.

## Caveats
- Some cited blog posts carry future-dated timestamps (2026) and secondhand benchmark numbers, such as specific ElastiCache and Valkey per-ECPU prices and Redlock false-positive rates. Treat those figures as directional and re-verify against official AWS pricing and first-party benchmarks before making commitments. The Valkey throughput headline is roughly 230% and 1.2M QPS (Valkey 8 async I/O threading); the higher figure of about 270% applies specifically to experimental Valkey-over-RDMA, not to stock Valkey.
- The Redisson OSS-versus-PRO performance split is contested in community threads, so benchmark on your own workload before assuming OSS performance parity or before paying for PRO.
- Spring Data Redis has no headline Valkey-compatibility statement. Compatibility is inferred from Lettuce and Jedis speaking Valkey's protocol unchanged, so verify against your exact server version.
- Client-side caching is Standalone-only in Lettuce and beta in Jedis, so do not assume it works in ElastiCache cluster mode.
- Versions move fast. Re-check the latest Lettuce 7.x, Jedis 7.x/8.x, Redisson, and Spring Boot 4.x and Spring Data Redis 4.x at the moment you start.
