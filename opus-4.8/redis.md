---
title: "Redis Mastery for the Application Developer — A Source-Grounded Learning Plan"
category: "Data & Messaging"
description: "Source-grounded Redis curriculum for a senior Kotlin/Spring Boot engineer that teaches Redis as a data-modeling toolkit rather than a cache box — cache-aside with stampede protection (XFetch), rate limiting, leaderboards, counting (HyperLogLog/Bloom), feeds, queues/Streams, geospatial, and the Redis 8 Query Engine / vector search — anchoring each pattern's correctness in the single-threaded execution model plus Lua/Functions, and validating against the antirez llms.txt catalog and production write-ups (Stripe, Cloudflare, Reddit, Twitter). Includes client guidance (Lettuce vs. Redisson vs. Jedis) and a 2026 AWS decision framework for Valkey vs. Redis 8."
---

# Redis Mastery for the Application Developer: A Source-Grounded, Progressive Learning Plan

## TL;DR
- **Master Redis as a data-modeling toolkit, not a cache box.** The fastest path for a senior Spring Boot/Kotlin engineer is to learn Redis's data structures as primitives for application patterns — caching with stampede protection, rate limiting, leaderboards, feeds, queues/Streams, probabilistic counting, geospatial, search/vector — and to anchor each pattern's correctness in Redis's single-threaded execution model plus Lua/Functions for atomic compound operations. Use the antirez `llms.txt` pattern catalog as your spine and validate against real production write-ups (Stripe, Cloudflare, Reddit, Twitter, Pinterest, Uber, Instagram).
- **Use Lettuce; reach for Redisson only for high-level distributed primitives.** Lettuce is the Spring Boot default (Netty-based, async/reactive, thread-safe, first-class Kotlin coroutines), Jedis is the simple synchronous pool-based client, and Redisson is the high-level distributed-objects library (locks, semaphores, RLock watchdog, RedLock). For a Kotlin/coroutines stack the decision tree is: Lettuce by default, Redisson when you want batteries-included locks/collections.
- **On AWS in 2026, default to Valkey for pure cache/coordination workloads and choose Redis 8 when you need the integrated Query Engine / vector sets / JSON.** Valkey is the Linux Foundation BSD fork (from Redis 7.2.4), is AWS's *recommended* ElastiCache engine, and is priced 20% lower (node-based) / 33% lower (serverless). Redis 8 re-added an OSI license (AGPLv3) and pulls search, vector, JSON, time-series and probabilistic types into the core — those module-backed patterns are Redis-only and won't run on Valkey.

## Key Findings

1. **The antirez `llms.txt` is a curated pattern catalog, not API docs.** It organizes Redis usage into *fundamental* (cache-aside, stampede prevention, client-side caching, atomic updates, distributed locking, Redlock, reliable queue, delayed queue, Streams consumer groups, probabilistic structures, rate limiting, vector sets, write-through/behind), *community* (bitmaps, geospatial, leaderboards, pub/sub, sessions, vector/AI), and *production* (Pinterest task queue, Twitter internals, Uber resilience) patterns. It explicitly warns its guidance is Redis-specific and "may not apply to ... Valkey, KeyDB, Dragonfly."

2. **Cache stampede has three canonical mitigations, and probabilistic early expiration (XFetch) is the elegant lock-free one.** The XFetch algorithm (Vattani, Chierichetti, Lowenstein, "Optimal Probabilistic Cache Stampede Prevention," VLDB 2015) recomputes with probability rising as expiry approaches via `now - delta*beta*log(random()) >= expiry`. Benchmarks circulating online show X-Fetch cutting DB queries from 10,000 to 3–5 at expiry vs a distributed lock (1 query but added wait latency).

3. **Stripe and Cloudflare are the canonical rate-limiting references.** Stripe uses a token-bucket request limiter, a concurrent-request limiter (sorted set + ZCARD), and load shedders, all in Redis with Lua for atomicity, and explicitly fails open: per Stripe's "Scaling your API with rate limiters," *"if there were bugs in the rate limiting code (or if Redis were to go down), requests wouldn't be affected. This means catching exceptions at all levels so that any coding or operational errors would fail open and the API would still stay functional."* Cloudflare uses an approximated sliding-window counter; per their blog "How we built rate limiting capable of scaling to millions of domains," *"an analysis on 400 million requests from 270,000 distinct sources shown: 0.003% of requests have been wrongly allowed or rate limited [and] an average difference of 6% between real rate and the approximate rate."* Shopify uses leaky bucket (per ByteByteGo's "Design A Rate Limiter": *"Shopify, an ecommerce company, uses leaky buckets for rate-limiting"*).

4. **The Redlock debate maps cleanly to "efficiency vs correctness."** Kleppmann argues Redlock is unsafe for correctness (timing/clock assumptions, no fencing tokens) and recommends single-node SET NX for efficiency locks or ZooKeeper/etcd + fencing tokens for correctness. antirez rebuts that Redlock re-checks elapsed time after acquisition and that fencing-token arguments are often unrealistic. Verdict: for "don't run the cron twice" use single-instance `SET key val NX PX`; for "don't double-charge a customer," use a consensus system with fencing tokens.

5. **Redis Streams vs Kafka is a "scale and retention" decision.** Streams give consumer groups, PEL (pending entries list), XACK, XAUTOCLAIM, at-least-once. They lack partitions (so no partition-level parallel ordering — emulated via one stream/consumer per "partition"), automatic rebalancing, and infinite disk retention. Rule of thumb from practitioners: Streams under ~100K events/sec and bounded retention if you already run Redis; Kafka for durable, replayable, infinitely retained, partitioned streams. Arcjet, in "Replacing Kafka with Redis Streams," reported it could run *"a generic Redis cluster for much lower cost than managed Kafka services (on the order of $1k/yr vs 6 figure licensing fees for commercial Kafka services)."*

6. **Probabilistic structures are production-proven at scale.** Reddit's view counter (the "View Counting at Reddit" engineering post, 2017) uses HyperLogLog fed by Kafka and persisted to Cassandra; per the official Redis HyperLogLog docs, *"A Redis HyperLogLog consumes at most 12 kilobytes of memory and produces approximations with a standard error of 0.81%."* Twitter historically used Redis as the timeline cache (Raffi Krikorian, QCon 2012: each tweet fanned out into ~every follower's cached timeline). Bloom/Cuckoo/Count-Min Sketch/t-digest now ship in Redis 8 core (probabilistic types).

7. **Lettuce is the Spring Boot default; Redisson is the high-level distributed toolkit.** Spring Boot switched the `spring-boot-starter-data-redis` default driver from Jedis to Lettuce in 2.0 — per GitHub spring-projects/spring-boot issue #10480, *"Lettuce comes with a friendlier performance profile than Jedis. The arrangement with Jedis suffers from changes in the Jedis core development... Features of newer Redis versions are not supported."* Lettuce is Netty-based, thread-safe (one shared connection across threads), and supports a native Kotlin coroutines API (`connection.coroutines()` returning `RedisCoroutinesCommands`). Redisson provides 50+ distributed objects/services including RLock with a watchdog (default 30s lease auto-extension), RedLock, semaphores.

8. **Valkey has become the open-source center of gravity on AWS, but Redis 8 has the richer feature set.** Valkey: Linux Foundation, BSD-3, forked from Redis 7.2.4 (March 28, 2024), backed by 50+ companies, led by AWS's Madelyn Olson, #17 on DB-Engines key-value ranking (up from #24 a year prior), 100M+ Docker pulls by its 2nd anniversary. Redis remains #1 key-value store on DB-Engines (score ~150 vs Valkey ~2.5) and the `redis` Docker image has 1B+ pulls. Redis 8 (AGPLv3 added May 2025) integrates Query Engine, vector sets, JSON, time-series, probabilistic types into core.

## Details

### 1. Core data-structure modeling and application patterns

#### 1.1 Caching patterns
- **Cache-aside (lazy loading)** is the default for read-heavy workloads: on miss, load from Aurora MySQL, `SET` with TTL; on write, invalidate (delete) or update the key. The antirez catalog recommends invalidate-on-write over update-on-write to avoid stale races.
- **Read-through / write-through / write-behind**: write-through writes Redis+DB synchronously (consistency, higher write latency); write-behind (write-back) writes Redis then asynchronously flushes to DB (max throughput, durability risk on crash). In a Spring Boot stack write-through is naturally expressed via the Spring `@Cacheable`/`@CachePut`/`@CacheEvict` abstraction backed by `RedisCacheManager`.
- **Stampede / thundering-herd protection**: three approaches — (a) distributed lock so one worker recomputes (adds wait latency); (b) **probabilistic early expiration / XFetch** (Vattani et al., VLDB 2015) — store value + `delta` (recompute cost) + expiry, recompute when `now - delta*beta*ln(rand) >= expiry`, no coordination, lock-free; (c) request coalescing / single-flight in the app layer. Jim Nelson (Internet Archive) presented XFetch with Redis at RedisConf17.
- **TTL strategies**: jitter TTLs to avoid synchronized expiry; use shorter TTLs for volatile data; combine with XFetch for hot keys.
- **Client-side caching (RESP3 tracking)**: Redis 6+ `CLIENT TRACKING` makes the server push invalidation messages. Default mode tracks read keys; BCAST mode tracks prefixes; OPTIN/OPTOUT control per-command tracking via `CLIENT CACHING yes/no`. With RESP3 invalidations arrive as push messages on the same connection; with RESP2 you redirect to a second Pub/Sub connection subscribed to `__redis__:invalidate`. Best candidates: keys with high local-hit-to-invalidation ratio. Must flush local cache on connection loss and ping the invalidation channel. `tracking-table-max-keys` defaults to 1,000,000.

#### 1.2 Rate limiting
- **Algorithms**: fixed window (simplest, boundary-burst problem), sliding window log (exact, memory-heavy — sorted set of timestamps with ZREMRANGEBYSCORE+ZCARD), sliding window counter (Cloudflare's weighted approximation), token bucket (Stripe/Amazon — allows bursts), leaky bucket (Shopify — smooths to constant rate).
- **Atomic implementation**: a single Lua `EVAL` script does read-compute-write atomically in one round trip; this beats WATCH/MULTI/EXEC, which forces a retry loop under contention (worst behavior for a rate limiter). Use `redis.call("TIME")` (or pass `now` from the app deterministically) to avoid clock skew across pods.
- **Production references**: Stripe's engineering blog "Scaling your API with rate limiters" + public GitHub gist (ptarjan) ship the actual token-bucket Lua + concurrent-request limiter (sorted set, ZCARD) + load shedder; they emphasize fail-open and feature flags. Cloudflare "How we built rate limiting capable of scaling to millions of domains" details the sliding-window counter and the 0.003%/6% accuracy numbers above. GitHub's API uses a fixed-window limiter (5,000 req/hr authenticated). For the user's Kotlin stack, a clean capstone is a rate-limiter library exposing fixed/sliding/token/leaky behind one interface with scripts loaded via `SCRIPT LOAD`/`EVALSHA`.

#### 1.3 Leaderboards and ranking
- Sorted sets give O(log N) `ZADD`, O(log N) rank via `ZRANK`/`ZREVRANK`, and range queries `ZREVRANGE ... WITHSCORES` for top-N and "around me" (`ZREVRANGE rank-2 rank+2`). Lexicographic sorted sets (identical scores) build B-tree-like prefix indexes (`ZRANGEBYLEX`). This is the canonical Redis showcase pattern.

#### 1.4 Counting at scale
- **Plain counters**: `INCR`/`INCRBY`/`HINCRBY` atomic.
- **HyperLogLog**: `PFADD`/`PFCOUNT`/`PFMERGE`, 12KB fixed, 0.81% error, time-bucketed keys + `PFMERGE` for windowed uniques. Reddit's view counter is the canonical case (HLL + Kafka + Cassandra/DynamoDB tiering for cost).
- **Bloom/Cuckoo filters** (membership, e.g., "have we seen this user/URL"), **Count-Min Sketch** (frequency), **t-digest** (percentiles) — all in Redis 8 probabilistic types (formerly RedisBloom module). Twitter-style "have I shown this tweet" dedup is a classic Bloom use.
- **Bitmaps**: millions of boolean flags at 1 bit each (`SETBIT`/`BITCOUNT`/`BITOP`) for daily-active-user style analytics.

#### 1.5 Feeds / timelines (fan-out on write vs read)
- **Fan-out on write (push)**: on post, push post-id into each follower's sorted set/list (`ZADD`/`LPUSH` + `ZREMRANGEBYRANK`/`LTRIM` to cap, e.g., last 800–3000). Fast reads, expensive writes. Twitter's original Redis timeline cache (Krikorian, QCon 2012) is this.
- **Fan-out on read (pull)**: store post once, merge followees' recent posts at read. Cheap writes, expensive reads.
- **Hybrid (celebrity threshold)**: push for normal users, pull for high-follower accounts; threshold is an operationally tuned parameter (commonly cited ranges 10K–1M followers). Instagram/Twitter/Pinterest each tune differently. Pair with cursor-based pagination (offset breaks under live updates).

#### 1.6 Sessions and ephemeral state
- Hash (field-level access), string (serialized blob), or JSON (nested) with TTL. Spring Session Data Redis is the idiomatic Spring Boot integration; Lettuce is its default driver. Discord uses Redis to cache presence/read-state-style ephemeral data on the hot path.

#### 1.7 Queues and task processing
- **Lists**: `LPUSH`+`BRPOP` simple FIFO; **reliable queue**: `LMOVE` (formerly RPOPLPUSH) into a processing list so a crashed consumer's work is recoverable, then `LREM` on completion.
- **Delayed/scheduled jobs**: sorted set scored by run-at unix time; poller does `ZRANGEBYSCORE ... 0 now` then atomically moves due jobs.
- **Streams + consumer groups**: `XADD`/`XREADGROUP`/`XACK`/`XAUTOCLAIM`, PEL for in-flight tracking, DLQ via a separate stream, `MAXLEN ~`/`XTRIM` to bound memory, `XACKDEL` (Redis 8.2) to ack+delete with multi-group strategies. Pinterest's production pattern (in antirez catalog) uses list-based reliable queues with functional partitioning, scaled 1→1000+ instances.
- **Kafka comparison (for this user)**: keep Kafka as the durable system-of-record event backbone; use Redis Streams for hot-path, low-latency, bounded-retention work where you already run Redis. Common hybrid: Kafka → consumer → Redis materialized view.

#### 1.8 Pub/Sub and real-time messaging
- Pub/Sub is fire-and-forget at-most-once (lost if no subscriber, ~100K msg/sec/node, sub-ms). Streams add persistence, consumer groups, replay. Choose Streams when missed messages matter; Pub/Sub for ephemeral notifications/chat/live updates. Sharded Pub/Sub (`SPUBLISH`) scales in Cluster.

#### 1.9 Geospatial
- `GEOADD`/`GEOSEARCH`/`GEODIST` on geohash-encoded sorted sets for radius/box queries (ride-hailing, store locators). Uber-scale resilience patterns (staggered sharding, circuit breakers) are in the antirez production catalog (cited there at 150M+ ops/sec cache workloads).

#### 1.10 Secondary indexing and search (Redis 8 Query Engine)
- Redis 8 folds the Query Engine (formerly RediSearch) into core: secondary indexes on hashes/JSON, full-text (stemming, synonyms, fuzzy), aggregations, JSON (formerly RedisJSON), and **vector similarity search** (HNSW/flat, `FT.SEARCH` KNN; `FT.HYBRID` in 8.4 fuses text+vector with RRF or linear combination). **Vector sets** (8.0 beta, designed by antirez) extend sorted sets to vector embeddings for RAG/semantic search/recommendations. RedisVL is the AI-native Python client. **These are Redis-only and do not run on Valkey.**

#### 1.11 Distributed coordination primitives
- **Single-instance lock**: `SET resource token NX PX ttl` to acquire; delete-if-value-matches (Lua) to release. Safe and simple for efficiency locks.
- **Redlock**: acquire on majority (N/2+1) of N independent masters (typically 5), re-check elapsed time after acquisition, subtract clock drift. Tolerates node failures.
- **Fencing tokens**: monotonic counter passed to the protected resource, which rejects stale writes. Redlock does not natively generate them.
- **Kleppmann vs antirez**: efficiency vs correctness framing (see Key Finding 4). Redisson implements RLock (watchdog auto-extends lease, default 30s), RedLock, FairLock, MultiLock, ReadWriteLock, semaphores.

### 2. Concurrency and correctness (for a JVM-concurrency-literate reader)
- **Single-threaded command execution**: each command runs atomically; there is no intra-command interleaving. This is the bedrock that makes `INCR`, `SETNX`, sorted-set ops, and Lua scripts race-free without application locks — analogous to a single mutex serializing all mutations, but without the JVM's lost-update hazards.
- **Transactions (MULTI/EXEC/WATCH)**: optimistic locking — `WATCH` a key, build a queued transaction, `EXEC` aborts if the watched key changed. Good for compare-and-set; bad under high contention (retry storms).
- **Lua scripting**: the workhorse for atomic compound read-compute-write (rate limiters, conditional updates). Scripts block the event loop, so keep them short and avoid `KEYS`. In Cluster all keys a script touches must hash to one slot (use hash tags `{...}`).
- **Redis Functions** (Redis 7+): persisted, named server-side functions (FUNCTION LOAD) — a more maintainable evolution of EVAL scripts.
- **Persistence/durability tradeoffs**: RDB (point-in-time snapshots, fast restart, possible data loss between snapshots) vs AOF (append-only log, `everysec` fsync default, better durability, larger files). Replication is asynchronous → a failover can lose the last writes that hadn't replicated; this is precisely the window that breaks naive master-replica locks (the motivation for Redlock). Application code must treat Redis as potentially losing the most recent unreplicated writes under failover.
- **Idempotency patterns**: idempotency keys (`SET NX` on a request id), dedup via Bloom filter or a seen-set, and at-least-once + idempotent consumers for Streams.

### 3. Spring Boot + Kotlin integration
- **Spring Data Redis**: `RedisTemplate`/`StringRedisTemplate` (sync) and `ReactiveRedisTemplate` (reactive), `@RedisHash` repositories, `RedisConnectionFactory` (Lettuce or Jedis). Spring's Cache abstraction (`@EnableCaching` + `RedisCacheManager`) gives declarative cache-aside/write-through with a `CacheErrorHandler` (e.g., log-and-continue so cache failures don't break the request path).
- **Client tradeoffs**:
  - **Lettuce** — Netty-based, async + reactive + sync, thread-safe (share one connection), connection pooling optional, Cluster/Sentinel, pipelining, native Kotlin coroutines (`connection.coroutines()` → `RedisCoroutinesCommands`, suspend functions, `Flow`). **Spring Boot default since 2.0.**
  - **Jedis** — synchronous, blocking, not thread-safe (needs `JedisPool`), simple API, large community. Practitioners report response-time degradation past ~200 shared pooled connections.
  - **Redisson** — high-level distributed objects (RLock, RMap, RQueue, RateLimiter, Bloom filter, etc.), Spring Data/Spring Cache/Spring Session integration, reactive + RxJava. Note a reported coroutines-interop friction (issue #5667) when mixing Redisson reactive with suspend functions.
- **Industry adoption (which client is most used)**: Lettuce is the most widely used in Spring Boot because it is the auto-configured default of `spring-boot-starter-data-redis` and Spring Session; Jedis remains popular for its simplicity in non-reactive apps; Redisson is the go-to when you specifically want distributed primitives. For this user's Kotlin/coroutine/EKS stack: **Lettuce by default**, Redisson when locks/semaphores/collections justify the extra abstraction.
- **Kotlin coroutine integration**: Spring Data Redis exposes coroutine extensions (`awaitX`, `Flow` returns); reactive `ReactiveRedisTemplate` + `kotlinx-coroutines-reactor` bridges `Mono`/`Flux` to suspend/`Flow`. Lettuce's own coroutine API removes most reactive boilerplate.
- **Connection pooling / cluster / pipelining**: Lettuce multiplexes over one connection (pool only for blocking/transactional ops); Jedis requires `JedisPool`; both support Cluster/Sentinel; pipelining and batching reduce RTTs (use `pipeline`/`executePipelined`).

### 4. Redis vs Valkey (2026)
- **The license timeline**: March 2024 — Redis dropped BSD-3 for dual RSALv2/SSPLv1 (SSPL not OSI-approved), triggering the Valkey fork. March 28, 2024 — Linux Foundation launched Valkey, continuing from Redis 7.2.4 under BSD-3. May 2025 — Redis 8.0 added AGPLv3 as a third license option and integrated the Stack modules into core.
- **Adoption evidence (verified primary sources)**:
  - **AWS ElastiCache**: AWS calls Valkey its *recommended* engine (note: "recommended," not literally "default," is AWS's own wording; "default" appears only in third-party coverage). ElastiCache for Valkey launched Oct 8, 2024; per AWS's announcement, it is *"Serverless priced 33% lower and node-based priced 20% lower than other supported engines,"* you can *"get started as low as $6/month,"* and serverless minimum storage is *"100MB, 90% lower than ElastiCache Serverless for Redis OSS."* Stacked with memory efficiency, AWS markets up to 60% savings.
  - **DB-Engines (June 2026)**: Redis #1 key-value store (score ~150); Valkey #17 (score ~2.47), up from #24 a year earlier — fastest riser near the top but two orders of magnitude below Redis.
  - **Docker**: `redis` official image 1B+ pulls; Valkey 100M+ pulls by its 2nd anniversary (2026, per AWS's Valkey 9.0 ElastiCache blog).
  - **Governance**: Linux Foundation, BSD-3, from Redis 7.2.4, backed by 50+ companies (AWS, Google Cloud, Oracle, Ericsson, Snap, Aiven, Percona, ByteDance), led by AWS's Madelyn Olson with co-maintainers including Ericsson's Viktor Söderqvist; 150+ contributors from 50+ orgs, 1,000+ commits in year one.
  - **Verified migration ROI**: Alight Solutions reported 60%+ cost savings migrating to ElastiCache for Valkey (AWS-published, named, >150K ops/sec, sub-0.5ms); an anonymous AWS customer "powering millions of daily bookings" achieved 20% savings with zero downtime; Buildertrend migrated Google Cloud Memorystore Redis→Valkey. *Caveat: widely circulated claims that Snap cut Redis spend from $2.1M to $840K/yr and that Pinterest migrated its session/rate-limiter tier to Valkey trace to a single low-quality blog (tech-insider.org) and could not be verified against any primary source — do not rely on them.*
- **Feature divergence**: Valkey focuses on the core engine — multi-threaded I/O, memory efficiency, ~90% command compatibility, ~20% cheaper on AWS. Redis 8 has the integrated Query Engine, vector sets/search, JSON, time-series, probabilistic types. **Per-pattern portability**: caching, rate limiting, leaderboards, counters/HLL, bitmaps, feeds, sessions, lists/Streams queues, Pub/Sub, geospatial, locks — all work on both. **Search, vector similarity, JSON document indexing, time-series — Redis 8 only.**
- **Decision framework**: If you use Redis purely as cache/session/rate-limiter/Streams broker on AWS and your legal team flags SSPL → **Valkey** (cheaper, BSD, AWS-aligned, multi-threaded I/O). If your architecture depends on RediSearch/vector/JSON/time-series → **Redis 8** (migrating off would mean rearchitecting that component). Run `MODULE LIST` before assuming a Valkey migration is a drop-in.

## Recommendations

**Phased learning path** (≈8–12 weeks part-time; adjust to your pace):

- **Phase 0 — Foundations (week 1, ~6–8h).** Redis University "Get Started with Redis" (replaces RU101; free, covers all data structures + time complexity + Lua intro). Skim official docs data-types pages. Spin up Redis 8 + Valkey in Docker on your machine; connect from a Spring Boot 3 + Kotlin app via Lettuce. *Benchmark to advance: you can reach for the right structure by time-complexity reflex.*
- **Phase 1 — Core patterns (weeks 2–4, ~15h).** Work the antirez `llms.txt` fundamental + community patterns. Implement cache-aside + XFetch, a sorted-set leaderboard, HLL counting, a list/Streams queue. Read Stripe's "Scaling your API with rate limiters" + the ptarjan gist; Cloudflare's "How we built rate limiting…"; Reddit "View Counting at Reddit." Book: *Redis in Action* (Josiah L. Carlson, Manning, 2013) — excellent for patterns (caching, counters, locks, queues, ad targeting) **with the caveat that it predates Streams, Functions, RESP3 client-side caching, the Query Engine, and the Valkey split**, so pair every chapter with current docs.
- **Phase 2 — Concurrency & correctness (weeks 4–6, ~12h).** MULTI/EXEC/WATCH, Lua, Redis Functions, RDB vs AOF, replication/failover edge cases, idempotency. Read Kleppmann "How to do distributed locking" and antirez "Is Redlock safe?" back-to-back; if you want formal grounding, Kleppmann's *Designing Data-Intensive Applications* ch. 8–9. RU102J ("Redis for Java Developers") covers DAO design, pipelining, transactions, Lua from the JVM side. *Benchmark: you can state, for any feature, whether you need an efficiency lock or a correctness lock, and justify it.*
- **Phase 3 — Search & vector (weeks 6–8, ~12h).** Redis 8 Query Engine: secondary indexing on JSON, full-text, aggregations, KNN vector search, `FT.HYBRID`, vector sets. Build a RAG retrieval feature with embeddings. RedisVL docs/tutorials; Redis "Using Redis for real-time RAG" blog. (Redis-only — note the Valkey gap.)
- **Phase 4 — Production hardening (weeks 8–10, ~10h).** Cluster (hash tags, slot co-location), Sentinel, client-side caching (RESP3 tracking), pipelining/batching, memory optimization (listpack/intset encodings), kernel tuning. Study the antirez production patterns (Pinterest task queue, Uber resilience, Twitter internals). Course: "Running Redis at Scale."
- **Phase 5 — Mastery projects (weeks 10–12+).** Pick 2–3 capstones below.

**Capstone project ideas (Spring Boot + Kotlin):**
1. **Rate-limiter library** — one interface, four+ algorithms (fixed/sliding-counter/token/leaky), Lua via `EVALSHA`, fail-open, `Retry-After`/`X-RateLimit-*` headers; benchmark against the Stripe/Cloudflare designs.
2. **Leaderboard service** — sorted sets, top-N + around-me, time-windowed boards via key rotation + `ZUNIONSTORE`.
3. **Feed/timeline system** — hybrid fan-out with a tuned celebrity threshold, sorted-set feeds with `ZREMRANGEBYRANK` capping, cursor pagination; profile push vs pull write amplification.
4. **RAG / vector-search feature** — Redis 8 vector index + `FT.HYBRID`, semantic cache layer; measure recall vs latency.
5. **Reliable job queue** — Streams + consumer groups, PEL recovery, `XAUTOCLAIM`, DLQ, delayed jobs via sorted set; compare semantics to your Kafka stack.
6. **Distributed lock library with fencing tokens** — single-instance `SET NX PX` + Lua release, optional Redlock, a monotonic fencing-token issuer, and a resource that rejects stale tokens; write the "efficiency vs correctness" decision doc.

**Thresholds that change the recommendations:**
- If a workload needs durable, replayable, partitioned, infinitely retained streams → move it from Redis Streams to Kafka.
- If lock violation can corrupt data or double-charge → stop using Redis locks for that path; use a consensus system + fencing tokens.
- If you adopt RediSearch/vector/JSON/time-series → you are committed to Redis 8 (not Valkey) for that component.
- If you're on AWS, cache-only, and legal flags SSPL → migrate that tier to Valkey (run `MODULE LIST` first).

## Caveats
- *Redis in Action* (2013) is pattern-rich but pre-dates Streams, Functions, RESP3 client-side caching, the Query Engine, vector sets, and the Redis/Valkey license split — always cross-check with current docs.
- Many high-traffic numbers and "company X uses Redis for Y" claims circulate via system-design blogs and secondary aggregators; where I could anchor to a primary source (Stripe blog, Cloudflare blog, Reddit blog, antirez catalog, AWS/Linux Foundation/DB-Engines/Docker Hub) I did. Treat third-party "celebrity threshold = N" and migration-dollar figures as illustrative unless tied to a primary source.
- The widely repeated Snap ($2.1M→$840K) and Pinterest Valkey-migration figures could not be verified beyond a single low-quality blog and are excluded from the findings.
- XFetch benchmark figures (10,000→3–5 DB queries) come from practitioner blogs reproducing the VLDB 2015 result, not from a controlled study in your environment — validate with your own load tests.
- Valkey's DB-Engines score and Docker pull counts are growing fast; the specific 2026 figures here are point-in-time snapshots.
- Redis behavior under failover (loss of unreplicated writes) is configuration-dependent (AOF fsync policy, `min-replicas-to-write`, ElastiCache settings) — verify your cluster's actual durability guarantees before relying on them for correctness.