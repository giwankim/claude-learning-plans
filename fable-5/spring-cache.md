---
title: "Mastering Spring Framework's Cache Abstraction: A Progressive, Mathematically Rigorous Learning Plan"
category: "Spring & Spring Boot"
description: "A 4-phase, 8–12 week part-time plan from Spring cache abstraction basics to a production-grade L1 (Caffeine) + L2 (Redis/Valkey) layered cache with CDC-driven invalidation and full mastery of Spring internals (CacheInterceptor, CacheAspectSupport, CacheOperationSource, KeyGenerator, CacheResolver — and why self-invocation bypasses the proxy). Built on verified primary sources: the Spring reference docs, Caffeine's W-TinyLFU design wikis, the XFetch probabilistic early-expiration paper (VLDB 2015), Meta's memcache/leases paper (NSDI 2013), plus curated Korean (우아한형제들, Toss, LINE, 화해, 올리브영) and international (DoorDash, Meta) engineering blogs, with each phase shipping a Kotlin/Spring Boot project on a real Aurora MySQL/Testcontainers/Kafka-Debezium/EKS stack."
---

# Mastering Spring Framework's Cache Abstraction: A Progressive, Mathematically Rigorous Learning Plan

## TL;DR
- This is a **4-phase, 8–12 week part-time plan** taking you from the Spring cache abstraction basics to a production-grade **L1 (Caffeine) + L2 (Redis/Valkey)** layered cache with CDC-driven invalidation and full mastery of Spring internals — structured by milestone, not rigid weeks.
- It is built on **verified primary sources**: the Spring reference docs, the Caffeine W-TinyLFU design/efficiency wikis, the Vattani–Chierichetti–Lowenstein XFetch paper (VLDB 2015), the Nishtala et al. Memcache/leases paper (NSDI 2013), plus curated Korean (우아한형제들, Toss, LINE, 화해, 올리브영) and international (DoorDash, Meta) engineering blogs.
- Each phase ships a **Kotlin/Spring Boot project on your real stack** (Aurora MySQL, Testcontainers, Kafka/Debezium, EKS) with explicit mastery checkpoints tied to formal correctness arguments — e.g. deriving the XFetch early-expiration probability and explaining why self-invocation bypasses the proxy.

## Key Findings

**1. The Spring cache abstraction is an AOP interception layer, not a cache.** Its entire behavior reduces to: a `CacheInterceptor` (subclass of `CacheAspectSupport`) woven in by a `BeanFactoryCacheOperationSourceAdvisor`, resolving operations via `CacheOperationSource`, keys via `KeyGenerator`, and caches via `CacheResolver`. Understanding this is the difference between using it and mastering it.

**2. Caffeine's W-TinyLFU is near-optimal and worth studying formally.** Per the Caffeine "Efficiency" wiki, its policies "are compared against Bélády's optimal for the theoretical upper bound," and "Window TinyLfu provides a near optimal hit rate and is competitive with ARC and LIRS." It combines a small admission LRU window with a Segmented LRU main region, gated by a TinyLFU admission filter backed by a 4-bit Count-Min Sketch (8 bytes/entry). For a PhD mathematician this is the most rewarding theory in the whole plan — it connects Bloom-filter theory, frequency estimation, and hill-climbing optimization.

**3. Cache stampede has an optimal, provably-good solution you can derive.** The XFetch algorithm uses exponential-gap probabilistic early recomputation; the β parameter tunes the aggressiveness of early refresh. This is directly implementable and benchmarkable, and Korean engineering blogs (화해, LINE) have production implementations to compare against.

**4. Spring's `CompositeCacheManager` is NOT a layered cache.** It is a lookup-fallback across managers. True L1+L2 layering requires either a custom `CacheManager`/`Cache` (the Baeldung two-level approach with a custom interceptor to back-fill L1), or an off-the-shelf library: **JetCache** (`CacheType.BOTH`), **Redisson** `RLocalCachedMap`/local-cached Spring cache, or **Hazelcast near-cache**.

**5. Cross-instance invalidation is the crux of multi-tier correctness.** Near-caches go stale per-JVM; you need a broadcast (Redis pub/sub or Kafka). Your Debezium/CDC expertise is a direct asset: binlog-driven invalidation from Aurora MySQL is the most robust approach and is used in production.

## Details

### Phase 0 — Orientation (before Week 1, ~half a day)
Read the abstraction overview end-to-end once, without coding, to build the mental model.
- **Spring Framework Reference — Cache Abstraction:** https://docs.spring.io/spring-framework/reference/integration/cache.html and the "Understanding the Cache Abstraction" page https://docs.spring.io/spring-framework/reference/integration/cache/strategies.html
- Note the framework's own framing: the caching service "is an abstraction (not a cache implementation)"; materialized by `org.springframework.cache.Cache` and `CacheManager`.

### Phase 1 — Quick Tour: The Abstraction (Weeks 1–2)

**Concepts.** `@EnableCaching`; `@Cacheable`, `@CachePut`, `@CacheEvict`, `@Caching`, `@CacheConfig`; `CacheManager` and `Cache` interfaces; key generation (`SimpleKeyGenerator`, custom `KeyGenerator`, SpEL keys with `#p0`, `#result`, `#root`); `condition`/`unless` (note `unless` sees `#result`, `condition` does not); `Optional` unwrapping; `sync=true` single-loader; in-process providers `ConcurrentMapCacheManager` and Caffeine.

**Resources (verified).**
- **Declarative annotation-based caching:** https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html
- **Spring Boot caching + auto-config:** the Boot reference "Caching" chapter — provider detection order is Generic → JCache → EhCache 2 → Hazelcast → Infinispan → Couchbase → Redis → Caffeine → Simple; `spring.cache.cache-names`, `spring.cache.caffeine.spec=maximumSize=500,expireAfterAccess=600s`.
- **Baeldung — Spring Boot + Caffeine:** https://www.baeldung.com/spring-boot-caffeine-cache
- **Korean:** "카페인 캐시와 캐시 추상화" (velog) https://velog.io/@onetuks/카페인-캐시와-캐시-추상화 — good walkthrough of `@CacheConfig`, class-vs-method-level caching, and why Caffeine over EhCache.
- **Korean (LG U+):** "로컬 캐시 선택하기" https://medium.com/uplusdevu/로컬-캐시-선택하기-e394202d5c87 — EhCache vs Guava vs Caffeine decision writeup.

**Phase 1 project.** Kotlin + Spring Boot service, `@Cacheable` over an Aurora-MySQL-backed repository using Caffeine. Wire Micrometer + Actuator so `cache.gets{result=hit|miss}`, `cache.puts`, `cache.evictions`, and `cache.size` are exposed (call `.recordStats()` on the Caffeine builder). Integration tests with **Testcontainers MySQL**. Compare `ConcurrentMapCacheManager` vs `CaffeineCacheManager`.

**Mastery checkpoints.**
- Explain precisely when `condition` vs `unless` is evaluated and why `unless` can reference `#result`.
- Demonstrate a custom `KeyGenerator` and an equivalent SpEL key, and articulate why the default hash-based key is unsafe across JVMs for distributed caches (the reference warns `hashCode()` is not preserved across JVMs).
- Show a cache hit/miss ratio in Actuator under a Testcontainers integration test.

### Phase 2 — Providers, Consistency & Stampede (Weeks 3–6)

**2a. Caffeine deep dive (theory).** W-TinyLFU eviction; `expireAfterWrite` vs `expireAfterAccess` vs `refreshAfterWrite`; `maximumSize` vs `maximumWeight`; `AsyncCache` and `buildAsync()`.
- **Caffeine "Design" wiki:** https://github.com/ben-manes/caffeine/wiki/Design
- **Caffeine "Efficiency" wiki:** https://github.com/ben-manes/caffeine/wiki/Efficiency — W-TinyLFU vs ARC/LIRS, 4-bit CountMinSketch. Note the sketch-collision attack and its mitigation: per the "Design" wiki, an attacker can use a collision "to artificially raise the estimated frequency of the eviction policy's victim… A solution is to introduce a small amount of jitter… by randomly admitting ~1% of the rejected candidates that have a moderate frequency."
- **Ben Manes, "Design of a Modern Cache" (High Scalability, 2016):** https://highscalability.com/design-of-a-modern-cache/ — his own prose on the striped ring buffers, SLRU, and hill climbing.
- **Academic:** Gil Einziger, Roy Friedman & Ben Manes, "TinyLFU: A Highly Efficient Cache Admission Policy," ACM Transactions on Storage 13(4), 2017, DOI 10.1145/3149371 — https://dl.acm.org/doi/abs/10.1145/3149371. Per the abstract, TinyLFU "is very compact and lightweight as it builds upon Bloom filter theory," and W-TinyLFU "is demonstrated to obtain equal or better hit ratios than other state-of-the-art replacement policies on these traces."

**2b. Redis/Valkey via Spring Data Redis.** `RedisCacheManager`, `RedisCacheConfiguration` (`entryTtl`, `disableCachingNullValues`, `computePrefixWith`), serialization (`GenericJackson2JsonRedisSerializer` — note it embeds `@class` type info, a cross-service pitfall — vs `Jackson2JsonRedisSerializer` vs JDK), TTL strategy, Lettuce connection pooling.
- **Baeldung — Spring Boot + Redis cache:** https://www.baeldung.com/spring-boot-redis-cache
- **Korean (ASSU):** the "Spring Boot - Redis 와 스프링 캐시" series, e.g. https://assu10.github.io/dev/2023/09/24/springboot-redis-1/ (Spring Data Redis + Lettuce) and the CacheManager entry https://assu10.github.io/dev/2023/10/07/springboot-redis-4/ — careful treatment of serialization and TTL.

**2c. Transactional behavior.** `TransactionAwareCacheDecorator` and `setTransactionAware(true)`; how cache writes defer to after-commit; interaction with `@Transactional` ordering; why an eviction inside a rolled-back transaction must not leak.

**2d. Consistency: cache-aside vs read-through vs write-through vs write-behind; CDC invalidation.** Negative caching, hot keys, and the Korean triad 캐시 관통(penetration)/눈사태(avalanche)/breakdown.
- **Toss — 캐시 문제 해결 가이드:** https://toss.tech/article/cache-traffic-tip — null-object vs Bloom-filter negative caching, jitter for avalanche, penetration handling. Excellent, production-grade, Korean.
- **CDC invalidation:** Debezium "Automating Cache Invalidation with Change Data Capture" (debezium.io blog) and the Debezium docs use-case list; consume the Aurora MySQL binlog topic and evict Redis keys. Leverage your transactional-outbox/CDC expertise here.

**2e. Cache stampede / thundering herd / dog-piling.** `sync=true` maps to `Cache.get(key, Callable)` and is per-JVM only. Study and implement:
- **XFetch / probabilistic early recomputation** — Vattani, Chierichetti, Lowenstein, "Optimal Probabilistic Cache Stampede Prevention," Proc. VLDB Endow. 8(8):886–897, 2015. DOI 10.14778/2757807.2757813. Primary PDF: http://www.vldb.org/pvldb/vol8/p886-vattani.pdf. The core recompute condition (Figure 3) is `Time() − Δ·β·log(rand()) ≥ expiry`, where Δ is the measured recomputation time stored with the value, rand() is uniform on (0,1], and β (default 1) tunes early-refresh aggressiveness. Per the paper's Figure 3 caption, β "defaults to 1 and already provides effective prevention… It can be increased for even better guarantees against stampedes, if earlier expirations are not a concern" — i.e. increasing β yields earlier recomputation and stronger stampede prevention (the experiments show raising β=1/λ to 1.5 drops average stampede size below 2).
- **Facebook leases:** Nishtala et al., "Scaling Memcache at Facebook," NSDI 2013 — https://www.usenix.org/system/files/conference/nsdi13/nsdi13-final170_update.pdf. The lease is "a 64-bit token bound to the specific key the client originally requested," and "to mitigate thundering herds, memcached returns a token only once every 10 seconds per key" (reads within that window are told to retry). Also study the look-aside architecture and remote markers for cross-region staleness.
- **화해 (Hwahae) — PER 알고리즘 구현:** https://blog.hwahae.co.kr/all/tech/14003 — a Korean production implementation of XFetch with the exact pseudocode, ideal to compare against.
- **LINE — req-shield:** https://techblog.lycorp.co.jp/en/req-saver-for-thundering-herd-problem-in-cache — open-source local+global lock library for thundering herd, with load-test results.
- **DoorDash — Avoiding Cache Stampede:** https://careersatdoordash.com/blog/avoiding-cache-stampede-at-doordash/ — coroutine-based request coalescing/debouncing for L1-miss stampedes.

**Phase 2 project.** Swap to Redis-backed caching (Spring Data Redis) with proper serialization and TTL tuning; test with **Testcontainers Redis**. Then add stampede protection three ways — (1) `sync=true`, (2) a Redisson distributed lock, (3) a hand-rolled **XFetch** early-recompute — and benchmark with **k6 or Gatling**. Measure latency with **HdrHistogram** and explicitly correct for **coordinated omission**.

**Mastery checkpoints.**
- **Derive** the XFetch early-expiration condition and explain the β parameter's effect on expected recompute time and stampede probability.
- Explain why `sync=true` cannot prevent a stampede across 20 pods on EKS, and what does.
- Produce a benchmark table: p50/p99/p99.9 and DB QPS for no-protection vs sync vs lock vs XFetch, with coordinated-omission-corrected histograms.

### Phase 3 — The Goal Architecture: Layered L1 + L2 (Weeks 6–9)

**Concepts.** Why `CompositeCacheManager` is a lookup fallback, not a tier; building a composite `CacheManager`/`Cache` where an L1 (Caffeine) miss falls through to L2 (Redis) and back-fills L1; near-cache invalidation across instances via Redis pub/sub or Kafka; evaluating off-the-shelf libraries.

**Resources (verified).**
- **Baeldung — Implement Two-Level Cache with Spring:** https://www.baeldung.com/spring-two-level-cache — hand-rolled Caffeine+Redis, and crucially a **custom cache interceptor to back-fill L1 on an L2 hit** (Spring does not sync between two caches on the same method).
- **JetCache (Alibaba):** https://github.com/alibaba/jetcache — `@Cached(cacheType = CacheType.BOTH)`, `localLimit`, `syncLocal(true)` to invalidate local caches across JVMs via a broadcast channel, `@CachePenetrationProtect` for stampede.
- **Redisson:** `RLocalCachedMap` with `LocalCachedMapOptions` (`SyncStrategy.INVALIDATE`, pub/sub-based cross-instance invalidation) — https://github.com/redisson/redisson/wiki/7.-Distributed-collections ; Spring cache managers (local-cached variants are Redisson PRO) — https://redisson.pro/docs/cache/spring-cache/
- **spring-boot-multilevel-cache-starter (SuppieRK):** https://github.com/SuppieRK/spring-boot-multilevel-cache-starter — Redis+Caffeine with a Resilience4j circuit breaker and randomized local TTL for stampede mitigation; a clean reference implementation to read.
- **DoorDash — Standardized microservices caching:** https://careersatdoordash.com/blog/how-doordash-standardized-and-improved-microservices-caching/ (and the InfoQ writeup https://www.infoq.com/news/2023/10/doordash-multilayered-cache/) — 3-tier (request-local HashMap → Caffeine → Redis Lettuce), runtime layer toggles, shadow mode for staleness measurement.
- **Korean — 올리브영 (Oliveyoung):** "고성능 캐시 아키텍처 설계" https://oliveyoung.tech/2024-12-10/present-promotion-multi-layer-cache/ — multi-layer local+Redis (ElastiCache) with measured TPS +478% and ElastiCache egress −99.1%.
- **Korean — SK DEVOCEAN:** https://devocean.sk.com/blog/techBoardDetail.do?ID=167203 — Redis + local cache with pub/sub cache-refresh events and a batch-scheduler fallback (near-cache invalidation broadcast pattern).

**AWS specifics.** ElastiCache (Redis/Valkey) vs MemoryDB — the decision reduces to "is Redis your cache or your database": ElastiCache acknowledges writes on the primary and treats data as reconstructable; MemoryDB durably commits to a multi-AZ transaction log before ack and can serve as a primary DB. Per AWS's own docs, MemoryDB delivers "microsecond read latency and single-digit millisecond write latency." (Third-party benchmarking by OneUptime, "How to Compare MemoryDB vs ElastiCache," Feb 2026, puts ElastiCache p99 writes at ~200–500µs vs MemoryDB ~3–5ms and notes a cost premium for the transaction-log infrastructure — treat those specific figures as vendor-independent estimates, not AWS-published numbers.) For a cache layer, ElastiCache is the right and cheaper choice. Cover cluster mode, Lettuce connection pooling, running on EKS, and cross-AZ transfer cost.
- **AWS — Choose between MemoryDB and ElastiCache:** https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/related-services-choose-between-memorydb-and-redis.html

**Phase 3 project.** Build the layered L1 (Caffeine) + L2 (Redis) cache: first hand-rolled composite `CacheManager` + pub/sub invalidation, then compare against JetCache or Redisson `RLocalCachedMap`. Add **Kafka/Debezium CDC-driven invalidation** from Aurora MySQL binlog. Measure per-tier hit ratios and tail-latency improvements; run multi-pod on EKS (or kind/minikube) to prove cross-instance invalidation works.

**Mastery checkpoints.**
- Explain, with a concrete failure scenario, why `CompositeCacheManager` does not give you L1+L2 semantics.
- Demonstrate a stale near-cache across two pods, then fix it via pub/sub AND via Kafka CDC, and argue the consistency guarantees of each (eventual; bounded by broadcast latency).
- Produce per-tier hit-ratio and p99 tables before/after L1 introduction.

### Phase 4 — Spring Internals & Reactive (Weeks 9–12)

**Concepts.** How `@EnableCaching` works: `@Import(CachingConfigurationSelector.class)` → `ProxyCachingConfiguration` (or `AspectJCachingConfiguration` when `mode=ASPECTJ`), which registers the `BeanFactoryCacheOperationSourceAdvisor`, `CacheInterceptor`, and `CacheOperationSource`. `AnnotationCacheOperationSource` + `SpringCacheAnnotationParser`. `CacheResolver`/`KeyGenerator` resolution. **Self-invocation** bypasses the proxy (proxy mode intercepts external calls only) — and the three workarounds (self-injection, `AopContext.currentProxy()`, or extract to a second bean). AspectJ mode as the alternative. `CacheErrorHandler` extension point. `sync=true` → `Cache.get(key, Callable)`. Reactive caching in **Spring Framework 6.1+**.

**Resources (verified).**
- **`@EnableCaching` javadoc:** https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/cache/annotation/EnableCaching.html — explicitly names `CachingConfigurationSelector`, `ProxyCachingConfiguration`, `AspectJCachingConfiguration`, and warns "proxy mode allows for interception of calls through the proxy only; local calls within the same class cannot get intercepted."
- **`CacheAspectSupport` javadoc:** https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/cache/interceptor/CacheAspectSupport.html — the Strategy-pattern base class; note the `spring.cache.reactivestreams.ignore` system property.
- **`CacheInterceptor` javadoc:** https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/cache/interceptor/CacheInterceptor.html
- **Reactive/async caching (6.1):** the annotations reference (above) documents `CompletableFuture`, `Mono`, and `Flux` support; `CaffeineCacheManager.setAsyncCacheMode(true)` is required. Spring Framework 6.1 release notes: https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.1-Release-Notes
- **Source reading:** `org.springframework.cache` packages on GitHub — https://github.com/spring-projects/spring-framework/tree/main/spring-context/src/main/java/org/springframework/cache
- **Self-invocation writeup:** DZone "Spring Beans Self-Invocation Problem" https://dzone.com/articles/spring-beans-self-invocation-problem

**Phase 4 project.** Write a custom annotation + `CacheInterceptor`-level extension (or a custom `CacheResolver`/`KeyGenerator`/`CacheErrorHandler`); demonstrate the self-invocation pitfall with a failing test and three passing workarounds; read and annotate the actual Spring source for the `@Cacheable` interception path. Mastery capstone: answer 3–5 Stack Overflow questions on Spring caching, or file a small docs PR.

**Mastery checkpoints.**
- Trace, from `@EnableCaching` to `CacheInterceptor.invoke`, the full bean-post-processing/advisor wiring from memory.
- Explain why self-invocation bypasses caching and demonstrate three workarounds with tests.
- Implement reactive `@Cacheable` on a `Mono`-returning method with async Caffeine, and explain what actually gets cached (the emitted value, not the publisher).

### Books & Courses (supplementary)
- **Designing Data-Intensive Applications** (Kleppmann) — replication, consistency, and caching chapters, for the theory-to-consistency bridge.
- **'개발자를 위한 레디스'** (김가림) — Korean Redis book; the cache-stampede/PER material is directly relevant (a velog study exists: https://velog.io/@qkrtkdwns3410).
- **Redis in Action** (Carlson) — free online; look-aside and TTL patterns.
- **Inflearn:** search 스프링 캐시 / Redis 캐시 for Korean video courses (verify current catalog; 김영한's Spring ecosystem courses are the highest-quality baseline for framework internals).

## Recommendations
1. **Start narrow, prove instrumentation first.** In Week 1, do not chase providers — get Actuator + Micrometer hit/miss metrics green under a Testcontainers test. If you cannot see hit ratio, you cannot reason about anything downstream.
2. **Treat Phase 2e (stampede) as the mathematical centerpiece.** Derive the XFetch condition on paper, implement it, and benchmark it against `sync=true` and a distributed lock. Threshold to advance: your XFetch implementation holds DB QPS flat under a synchronized-expiry load spike where naive caching shows a QPS cliff.
3. **Do not build a custom L1+L2 cache until you have felt the pain of `CompositeCacheManager`.** Build the naive composite, observe a stale near-cache across two pods, THEN add pub/sub and CDC invalidation. Advance when cross-instance invalidation latency is measured and bounded.
4. **Default to ElastiCache, not MemoryDB, for the L2.** Only revisit if Redis becomes a source of truth. Benchmark Lettuce pool sizing on EKS before declaring done.
5. **Gate "mastery" on teaching.** The final checkpoint is external: answer Stack Overflow questions or file a docs PR. If you cannot explain self-invocation and the `@EnableCaching` wiring from memory, you are not done with Phase 4.

**Benchmarks that change the plan:** if L1 hit ratio is <80% for your workload, revisit key design and TTL before adding complexity; if p99 is dominated by serialization, switch serializer (or move hot data to L1) before scaling Redis; if cross-instance staleness windows exceed your SLA, move from TTL-only to CDC-driven invalidation.

## Caveats
- **Korean blog volatility.** Company blog URLs and Inflearn course catalogs change; the specific posts cited here were verified to exist at research time, but confirm before relying on any single one. The Toss, 화해, LINE, 올리브영, and SK DEVOCEAN posts are stable, high-quality anchors.
- **Redisson local-cached Spring cache is a PRO (paid) feature.** The community edition provides `RLocalCachedMap`; the `RedissonSpringLocalCachedCacheManager` requires Redisson PRO. Plan accordingly or use JetCache (Apache-licensed) for a free L1+L2.
- **Version specificity.** Reactive/async caching semantics are 6.1+ (Spring Boot 3.2+); async Caffeine requires Caffeine 3.x and `setAsyncCacheMode(true)`. Ehcache 2.x support was removed in Spring 6 — use Ehcache 3 via JCache.
- **`GenericJackson2JsonRedisSerializer` embeds `@class` type metadata**, which couples cross-service DTO packages; for polyglot/MSA cache sharing this is a real trap flagged by multiple Korean writeups.
- **XFetch's rand()∈(0,1] range** is the standard interpretation implied by the exponential inverse-transform; the paper states the formula and β semantics explicitly but does not print the range next to the pseudocode.