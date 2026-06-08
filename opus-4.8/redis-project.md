---
title: "Redis Mastery — A Phased, Project-Based Implementation Plan"
category: "Data & Messaging"
description: "Hands-on companion to the Redis research plan: a six-phase (P0–P5), ~8–12-week project-based curriculum for a senior Spring Boot + Kotlin engineer that turns the roadmap into buildable toy projects — foundations and data-structure selection, core patterns (caching/XFetch, four rate limiters, leaderboards, HyperLogLog, reliable queues upgraded to Streams), concurrency & correctness (Lua/Functions, efficiency vs. correctness locks, failover), Redis 8 search/vector, and production hardening (Cluster, client-side caching, ElastiCache/Valkey ops) — with active-recall gates, spaced repetition, and explicit interleaving with the reader's Kafka/JVM/Aurora/EKS background."
---

# Redis Mastery — Detailed Phased Learning Plan
### For a senior Spring Boot + Kotlin engineer (AWS / EKS / Aurora / Kafka background)

This expands the six-phase roadmap from the research report into something you can actually run over ~8–12 weeks part-time. It is built as a study artifact, not a reading list.

---

## How to use this plan

- **Build, don't read (~60% hands-on).** Read a pattern, then immediately build the matching toy project. Reading about a sorted-set leaderboard teaches you nothing; implementing "around-me" ranking does.
- **Active-recall gates.** Each phase ends with questions to answer *from memory, out loud or in writing*. If you can't, you haven't finished the phase — go back. Recall is the thing that builds durable knowledge, not re-reading.
- **Spaced repetition.** Revisit earlier gates on a roughly 1 / 3 / 7-day cadence. The schedule at the bottom interleaves this for you.
- **Interleaving.** Every phase's toy projects deliberately pull in patterns from earlier phases, and every phase has a hook into what you already know (Kafka, JVM concurrency, Aurora, EKS). New Redis knowledge sticks when it attaches to existing mental models.
- **The plan is a map.** For any concept here, you can switch from "follow the map" to "teach me this" — a worked example, a derivation, or guided discovery. The plan tells you *what*; ask when you want the *why* worked through with you.

**A note on references:** Redis University course names and numbers have shifted over the years (RU101 → "Get Started with Redis", etc.), and some module-backed features were renamed in Redis 8. Where a course/number may have drifted I've flagged it. Check the live catalog at `university.redis.io`, and ask if you want me to pull the current catalog or specific conference talks for any single phase.

---

## The shape of the path

```
            ┌─────────────────────────────────────────────────────────┐
            │  P0 Foundations (data structures, client, Redis≠Valkey)  │
            └───────────────────────────┬─────────────────────────────┘
                                         │
            ┌────────────────────────────▼────────────────────────────┐
            │  P1 Core patterns (cache, rate-limit, leaderboard,       │
            │     counting, feeds, queues, pub/sub, geo)               │
            └───────────────┬───────────────────────┬──────────────────┘
                            │                       │
        ┌───────────────────▼──────────┐   ┌────────▼─────────────────┐
        │ P2 Concurrency & correctness │   │ P3 Search / vector (R8)  │
        │ (Lua, Functions, locks,      │   │ (Query Engine, JSON,     │
        │  fencing, failover, MULTI)   │   │  KNN, hybrid, RAG)       │
        └───────────────────┬──────────┘   └────────┬─────────────────┘
                            │                       │
            ┌────────────────▼───────────────────────▼─────────────────┐
            │  P4 Production hardening (cluster, client-side cache,     │
            │     pipelining, memory encodings, ElastiCache/Valkey ops) │
            └───────────────────────────┬─────────────────────────────┘
                                         │
            ┌────────────────────────────▼────────────────────────────┐
            │  P5 Mastery — integrative capstones + teach-it-back       │
            └─────────────────────────────────────────────────────────┘
```
P2 and P3 are independent of each other; do them in either order (or interleave). Everything else is linear.

---

## Phase 0 — Foundations
**~1 week, ~6–8h**

**What mastery looks like:** you reach for the right data structure by reflex, can state the time complexity of the commands you use, can stand up Redis 8 and Valkey locally and articulate the boundary between them, and have a Spring Boot 3 + Kotlin app talking to Redis through Lettuce (sync, coroutine, and reactive).

**Core topics**
- The structures: string, hash, list, set, sorted set, bitmap, HyperLogLog, stream, geo; plus JSON and vector (Redis 8 only).
- Key design and namespacing (`user:123:profile`), TTL/expiration semantics, `OBJECT ENCODING` and `MEMORY USAGE`.
- Time complexity per command (the Big-O is printed in each command's doc page — read it).
- RESP2 vs RESP3 at a high level; `redis-cli` fluency.

**References**
- Redis University — **"Get Started with Redis"** (free; the RU101 successor). Covers every structure + complexity.
- Official docs — **"Understand Redis data types"** tutorial, and the per-command reference (note the complexity line on each).
- Josiah L. Carlson, ***Redis in Action*** (Manning, 2013) — **ch. 1–3** (intro; a simple web app with sessions and carts; command overview). Pattern-rich; pre-dates Streams/Functions/RESP3, so pair with current docs.
- antirez pattern catalog (`redis.antirez.com/llms.txt`) — read the *index/taxonomy* now so you know what's coming.
- Spring — **Spring Data Redis reference** (Getting Started) and the **Lettuce reference guide**.

**Toy projects**
1. **Four-ways modeling kata.** Model one `User` profile four ways: a JSON string, a hash, several flat keys, and (on R8) a JSON document. Reason about access pattern and memory for each. *Teaches:* structure selection. *Stretch:* compare `MEMORY USAGE` and `OBJECT ENCODING` across all four.
2. **Hello Lettuce coroutines.** Spring Boot 3 + Kotlin; a `/ping` endpoint that does `SET`/`GET` via `RedisCoroutinesCommands`, and the same via `RedisTemplate`. *Teaches:* client wiring + the coroutine API. *Stretch:* add `ReactiveRedisTemplate` and compare the three styles.
3. **Redis-vs-Valkey diff.** Run both in Docker. `MODULE LIST`, `INFO server`, then try `FT.CREATE` (works on R8, errors on Valkey). *Teaches:* the fork's practical boundary. *Stretch:* write a one-paragraph "which engine for our cache tier" recommendation.

**Active-recall gate**
- From memory: give the Big-O and one use case for `ZADD`, `LPUSH`, `SADD`, `HSET`, `PFADD`, `XADD`.
- Why is `SET key val NX` atomic without an application lock?
- Name one feature that lives in Redis 8 but not Valkey, and why.

**Interleave / your stack:** hash field access ≈ column access in Aurora; the TTL you set here is the eviction primitive you'll formalize in Phase 1.

---

## Phase 1 — Core application patterns
**~2–3 weeks, ~15h**

**What mastery looks like:** you can implement cache-aside with stampede protection, build a leaderboard with "around-me" ranking, do cardinality and frequency counting with bounded memory, build both list- and Stream-based queues, and choose a feed fan-out strategy with a defensible threshold.

**Core topics**
- Caching: cache-aside vs read-through / write-through / write-behind; invalidate-on-write vs update-on-write; TTL jitter.
- Stampede mitigation: distributed lock, **probabilistic early expiration (XFetch)**, single-flight/request coalescing.
- Rate limiting: fixed window, sliding-window log, sliding-window counter, token bucket, leaky bucket.
- Leaderboards (sorted sets), counting (counters, HyperLogLog, Bloom/Count-Min, bitmaps).
- Feeds/timelines: fan-out on write vs read vs hybrid.
- Queues: list FIFO, reliable queue (`LMOVE`), Streams + consumer groups; Pub/Sub vs Streams; geospatial.

**References**
- antirez catalog — *cache-aside, stampede prevention, atomic updates, reliable queue, delayed queue, streams consumer groups, rate limiting, probabilistic*.
- **Stripe**, "Scaling your API with rate limiters" + the companion **ptarjan GitHub gist** (token bucket, concurrent-request limiter, load shedder, all Lua; note their fail-open stance).
- **Cloudflare**, "How we built rate limiting capable of scaling to millions of domains" (the approximated sliding-window counter, with its accuracy numbers).
- **ByteByteGo**, "Design a Rate Limiter" (algorithm taxonomy; Shopify's leaky bucket).
- **Reddit Engineering**, "View Counting at Reddit" (HyperLogLog + Kafka + persistence tiering).
- Vattani, Chierichetti, Lowenstein, **"Optimal Probabilistic Cache Stampede Prevention," VLDB 2015** (the XFetch math: recompute when `now − delta·beta·ln(rand) ≥ expiry`).
- Carlson, *Redis in Action* — **ch. 5** (counters/stats), **ch. 6** (autocomplete, delayed tasks, pull messaging), **ch. 7** (search-based apps), **ch. 8** (Twitter-style timelines).
- Docs — Streams intro, Pub/Sub, Geospatial. Redis University **"Redis Streams"** course (historically RU202).
- Raffi Krikorian, **"Timelines at Scale" (QCon 2012)** — the canonical fan-out-on-write talk.

**Toy projects** (escalating)
1. **Cache-aside over Aurora.** Wrap a deliberately slow MySQL read with cache-aside + jittered TTL. *Teaches:* the baseline. *Stretch:* expose a hit-ratio metric.
2. **Stampede lab.** Fire 1,000 concurrent misses at one hot key; implement (a) lock-based, (b) XFetch, (c) single-flight; measure DB hits and tail latency for each. *Teaches:* the three mitigations and their tradeoffs. *Stretch:* implement the actual XFetch `beta` formula and tune it.
3. **Four rate limiters, one interface.** Fixed window, sliding-window counter, token bucket, leaky bucket — each a Lua script behind one Kotlin interface, with `now` passed in deterministically. *Teaches:* atomicity + algorithm tradeoffs. *Stretch:* emit `X-RateLimit-*` / `Retry-After` headers and make it fail open.
4. **Leaderboard with around-me.** `ZADD` / `ZREVRANK` / `ZREVRANGE`; time-windowed boards via key rotation + `ZUNIONSTORE`. *Teaches:* sorted-set fluency.
5. **Unique visitors with HLL.** `PFADD` per day, `PFMERGE` for a 7-day rolling unique; compare memory to a plain `SET`. *Teaches:* probabilistic counting and the error budget.
6. **Reliable list queue → Streams upgrade.** Start with an `LMOVE` reliable queue; reimplement with Streams + consumer group + PEL + `XAUTOCLAIM` + a dead-letter stream. *Teaches:* queue semantics and the Streams model. *Stretch:* add delayed jobs via a sorted set scored by run-at time.

**Active-recall gate**
- For a feed: when push vs pull, and where does the "celebrity threshold" come from?
- Why does a `WATCH`/`MULTI` rate limiter behave badly under contention, while a Lua one doesn't?
- HyperLogLog: what's the memory and the standard error, and when is that error unacceptable?

**Interleave / your stack:** this is where your Kafka depth pays — for each queue/stream toy, articulate when you'd keep it in Redis Streams vs reach for Kafka (durability, replay, partitioned ordering, retention). Relate reliable-queue recovery (`LMOVE` + crash) to Kafka consumer-group rebalancing.

---

## Phase 2 — Concurrency & correctness
**~2 weeks, ~12h** *(independent of Phase 3)*

**What mastery looks like:** for any feature you can state whether it needs an *efficiency* lock or a *correctness* lock and justify it; you write atomic compound operations with Lua and Functions; and you can reason precisely about what a failover can lose.

**Core topics**
- The single-threaded execution model (why commands are atomic with no intra-command interleaving).
- Transactions: `MULTI`/`EXEC`/`WATCH` optimistic locking, and its retry-storm failure mode.
- Lua scripting: `KEYS`/`ARGV`, the one-slot constraint in Cluster (hash tags), blocking the event loop.
- Redis Functions (`FUNCTION LOAD`) as the maintainable evolution of `EVAL`.
- Persistence (RDB vs AOF, fsync policies), async replication, and **failover write loss**.
- Idempotency keys; Redlock; fencing tokens; the Kleppmann–antirez debate.

**References**
- **Martin Kleppmann**, "How to do distributed locking" (2016) **and** **antirez**, "Is Redlock safe?" (`antirez.com/news/101`) — read back-to-back; this is the heart of the phase.
- antirez catalog — *distributed locking, Redlock, atomic updates*.
- Kleppmann, ***Designing Data-Intensive Applications*** — **ch. 7** (transactions), **ch. 8** (the trouble with distributed systems), **ch. 9** (consistency & consensus). Your math background will make ch. 9 enjoyable rather than painful.
- Docs — Programmability (`EVAL`, Functions), Transactions, Persistence, Replication.
- Redis University **"Redis for Java Developers"** (historically RU102J) — transactions, pipelining, Lua from the JVM. **Redisson docs** for `RLock` (watchdog auto-extends a ~30s lease), `RedLock`, semaphores.

**Toy projects**
1. **CAS counter, three ways.** Implement a conditional inventory decrement with (a) `WATCH`/`MULTI` retry loop, (b) Lua, (c) a Redis Function; measure retries under contention. *Teaches:* why Lua wins under contention. *Stretch:* make it Cluster-safe with hash tags.
2. **Efficiency lock vs correctness lock.** Build `SET NX PX` + a Lua safe-release; then add a fencing-token issuer (`INCR`) and a downstream resource that *rejects stale tokens*. Write the one-page decision doc. *Teaches:* the core correctness distinction. *Stretch:* implement single-instance vs Redlock and state exactly what each does and doesn't guarantee.
3. **Failover loss demo.** With a primary + replica (or ElastiCache), write, kill the primary before replication, observe the loss; then toggle AOF `everysec` and `min-replicas-to-write` and re-observe. *Teaches:* durability is a configuration, not a given. *Stretch:* design a consumer that's correct despite the loss.
4. **Idempotent webhook handler.** `SET NX` idempotency key + a Bloom filter for dedup. *Teaches:* idempotency in practice.

**Active-recall gate**
- Why can a single-instance `SET NX` lock be lost on failover, and how does that motivate Redlock?
- What does a fencing token protect that Redlock alone does not?
- Give one operation where `WATCH`/`MULTI` is the right tool, and one where Lua is.

**Interleave / your stack:** contrast Redis's single-threaded serialization with the JMM's happens-before and `j.u.c.` locks — Redis hands you atomic compound operations *without* the lost-update hazards you manage by hand on the JVM. Connect the idempotency work to exactly-once / transactional-outbox patterns you've used with Kafka.

---

## Phase 3 — Search, indexing & vector (Redis 8)
**~2 weeks, ~12h** *(Redis-only; does not run on Valkey)*

**What mastery looks like:** you build secondary indexes over JSON, run full-text and filtered queries, and implement KNN and hybrid vector search for a RAG feature — and you know precisely why this phase pins your engine choice.

**Core topics**
- Query Engine: `FT.CREATE`, `FT.SEARCH`, `FT.AGGREGATE`; field types `TEXT` / `TAG` / `NUMERIC` / `VECTOR`.
- JSON document model and path indexing.
- Vector search: `FLAT` vs `HNSW`, KNN + range, the `ef`/`M` knobs; `FT.HYBRID` (RRF or linear fusion of text + vector); vector sets (8.0 beta).
- RedisVL as the AI-native client.

**References**
- Docs — **Search and query** (indexing/querying), **Vectors**, **JSON**. Redis University querying/indexing course (historically **RU203**) and the current vector/AI course.
- Redis blog — real-time RAG with Redis; **RedisVL** docs and recipes.
- **Redis 8 GA** notes (Query Engine integrated into core; vector sets beta).
- Reminder: none of this exists on Valkey.

**Toy projects**
1. **Indexed product catalog.** Products as JSON; `FT.CREATE` with `TAG`/`NUMERIC`/`TEXT`; query with filters, sort, pagination; `FT.AGGREGATE` for facets. *Teaches:* secondary indexing + the query language.
2. **Semantic search over your notes.** Embed your own docs, store vectors, `FT.SEARCH` KNN. *Teaches:* vector search basics + the recall/latency tradeoff.
3. **Hybrid RAG retriever.** `FT.HYBRID` fusing BM25 text with vector via RRF; add a semantic cache (cache answers keyed by embedding similarity). *Teaches:* hybrid retrieval + semantic caching. *Stretch:* plot recall@k vs latency as you vary HNSW `M` and `ef`.

**Active-recall gate**
- When `FLAT` vs `HNSW`, and what do `ef_construction` / `ef_runtime` trade?
- Why does adopting this phase force a Redis-8 (not Valkey) decision for that component?

**Interleave / your stack:** inverted index + ANN connects directly to your math background (metric spaces, approximate nearest neighbour). This is the one phase that pins your engine, so write down the architectural consequence explicitly.

---

## Phase 4 — Production hardening
**~2 weeks, ~10h**

**What mastery looks like:** you can size and operate a cluster, co-locate keys correctly, run client-side caching, batch with pipelining, read memory encodings, and reason about the ElastiCache-vs-self-managed and Redis-vs-Valkey operational picture.

**Core topics**
- Cluster: 16384 slots, hash tags, `MOVED`/`ASK`, cross-slot multi-key limits; Sentinel/failover.
- Client-side caching: RESP3 `CLIENT TRACKING`, BCAST/OPTIN modes, the invalidation channel, flush-on-disconnect.
- Pipelining/batching; Lettuce connection multiplexing and when you actually need a pool.
- Memory: listpack / intset / quicklist / skiplist encodings, `OBJECT ENCODING`, eviction (`maxmemory-policy`).
- Observability: `INFO`, `SLOWLOG`, latency monitoring, keyspace notifications.
- ElastiCache vs self-managed; Valkey multi-threaded I/O.

**References**
- Redis University **"Running Redis at Scale"** (historically RU301).
- Docs — Cluster spec & tutorial, client-side caching, pipelining, memory optimization, latency monitoring; Lettuce reference (connection model, cluster).
- Carlson, *Redis in Action* — **ch. 9** (reducing memory), **ch. 10** (scaling), **ch. 11** (Lua).
- AWS — **ElastiCache for Valkey** docs/blog (pricing, performance) and migration best-practices. antirez catalog **production patterns** (Pinterest task queue, Uber resilience, Twitter internals).

**Toy projects**
1. **Cluster slot lab.** Run a 3-shard cluster; force a cross-slot error, then fix it with hash tags `{user:123}`; watch a `MOVED`. *Teaches:* the slot model + multi-key constraints. *Stretch:* make a Phase-2 Lua script cluster-safe.
2. **Client-side cache.** Enable RESP3 tracking in Lettuce; verify invalidation pushes when a key changes; measure local hit ratio. *Teaches:* near-caching + invalidation. *Stretch:* BCAST prefix mode + correct flush-on-disconnect.
3. **Pipelining throughput.** Run 10k ops with and without pipelining; chart the RTT savings. *Teaches:* batching economics.
4. **Encoding inspector.** Watch a hash/zset flip from listpack to hashtable/skiplist as it grows (`OBJECT ENCODING`). *Teaches:* the memory internals that drive cost.

**Active-recall gate**
- Why must every key in a Lua script or transaction share a slot in Cluster, and how do hash tags fix it?
- What does client-side caching push to you, and what must you do on disconnect?
- Name the failure each of RDB and AOF protects against, and one cost of each.

**Interleave / your stack:** Cluster slots ≈ Kafka partitions (key-affinity and co-location reasoning transfers). Connection multiplexing ties directly to your EKS pod/connection budget — revisit a Phase-1 pattern and re-implement it cluster-safely.

---

## Phase 5 — Mastery: integrative capstones
**~2+ weeks**

Pick **2–3**. Each capstone names the phases it exercises, a definition of done, and what to measure. Add one requirement that cements mastery better than anything else: **teach it back** — write a short internal design doc or give a brown-bag on the tradeoffs. If you can teach the Redlock decision to a colleague, you own it.

1. **Rate-limiter library** *(P1 + P2)* — one interface, four+ algorithms, Lua via `EVALSHA`, fail-open, standard headers. *Done when:* it survives a concurrent load test with correct counts and degrades open when Redis is down. *Measure:* accuracy vs a ground-truth counter under burst.
2. **Leaderboard service** *(P1 + P4)* — sorted sets, top-N + around-me, time-windowed boards, cluster-safe keys. *Done when:* it returns correct ranks across a multi-shard cluster. *Measure:* p99 of a top-100 query at 1M members.
3. **Feed / timeline system** *(P1 + P2 + P4)* — hybrid fan-out with a tuned celebrity threshold, capped sorted-set feeds, cursor pagination. *Done when:* writes and reads stay bounded as a "celebrity" gains followers. *Measure:* write amplification, push vs pull, at varying follower counts.
4. **RAG / vector-search feature** *(P3)* — `FT.HYBRID` + a semantic cache. *Done when:* it answers from your corpus with a measurable cache hit-rate. *Measure:* recall@k vs latency as HNSW params vary.
5. **Reliable job queue** *(P1 + P2)* — Streams + consumer groups, PEL recovery, `XAUTOCLAIM`, idempotent consumers, DLQ, delayed jobs. *Done when:* a killed worker's in-flight jobs are recovered exactly once (idempotently). *Measure:* zero lost/duplicated effects under chaos-killing workers. *Compare:* the semantics explicitly against your Kafka stack.
6. **Distributed lock library with fencing** *(P2)* — single-instance `SET NX PX` + Lua release, optional Redlock, a monotonic fencing-token issuer, and a resource that rejects stale tokens. *Done when:* you can demonstrate a scenario where the unfenced lock corrupts state and the fenced one doesn't. *Deliverable:* the "efficiency vs correctness" decision doc.

---

## Mastery self-assessment

You're done when you can, from memory and without hedging:
- Pick the right structure for a problem and justify it on complexity and memory.
- Explain and implement the three cache-stampede mitigations and when each fits.
- Implement any of the five rate-limiting algorithms atomically and explain the tradeoffs.
- State, for a given feature, whether it needs an efficiency or correctness lock, and back it with the Kleppmann/antirez reasoning.
- Explain what a failover can lose and design around it.
- Decide Redis 8 vs Valkey for a concrete workload and name the deciding feature.
- Make a Lua script and a leaderboard query correct under Cluster.

---

## Spaced-repetition / interleaving schedule

A light cadence so earlier material doesn't decay while you move forward. Adjust to your week.

| Week | Primary focus | Revisit (recall gate, from memory) |
|------|---------------|-------------------------------------|
| 1 | P0 | — |
| 2 | P1 (cache, rate-limit) | P0 gate |
| 3 | P1 (leaderboard, counting, queues) | P0 + P1 (cache) gates |
| 4 | P2 (Lua, transactions) | P1 (rate-limit) gate |
| 5 | P2 (locks, failover) | P1 (queues) + P2 (Lua) gates |
| 6 | P3 (indexing, JSON) | P2 (locks) gate |
| 7 | P3 (vector, hybrid) | P1 (counting) + P3 (indexing) gates |
| 8 | P4 (cluster, client-cache) | P2 (failover) + P3 (vector) gates |
| 9 | P4 (pipelining, memory) | P1 + P2 gates (mixed) |
| 10+ | P5 capstones | rotate all phase gates weekly |

The point of the "revisit" column: pulling a concept back from memory a few days later, when it's slightly effortful, is what moves it from "I read that" to "I know that."
