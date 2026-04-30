---
title: "Spring Cache Mastery — Application & Pattern Playbook"
category: "Spring & Spring Boot"
description: "Depth-first, tradeoff-heavy reference for production engineers (Kotlin 2.x · Spring Boot 3.x · Hibernate 6 · Lettuce/Redisson · AWS EKS/ECS · Aurora · Kafka). Skips internals; concentrates on what to build, with which library, why, and where it breaks — organized by use case domain, then by pattern."
---

# Spring Cache Mastery — Application & Pattern Playbook for Kotlin/Spring Boot 3.x

> A depth-first, tradeoff-heavy reference for production engineers (Kotlin 2.x · Spring Boot 3.x · Hibernate 6 · Lettuce/Redisson · AWS EKS/ECS · Aurora · Kafka). This guide intentionally skips the internals (`CacheAspectSupport`, `CacheInterceptor`, etc.) and concentrates on **what to build, with what library, why, and where it breaks.**

---

## Part 1 — Use Case Catalog (organized by domain)

The Spring Cache abstraction is great for one specific shape of work: *"call this method, key by these arguments, store the return value."* That shape covers maybe 40% of caching needs in a real system. The rest of this section walks the catalog of use cases and tells you, for each, whether `@Cacheable` is the right tool — and what to reach for when it isn't.

### 1.1 Read-Through Caches for Catalogs and Lookup Tables

The canonical use case: a product catalog, currency code table, country list, feature catalog, or a code-table lookup that changes slowly and is read constantly. Toss's engineering team frames this exactly: *"키 기반 단순 조회는 가장 좋은 캐시 후보"* — key-based simple lookups are the best cache candidates (🇰🇷 toss.tech, "캐시 문제 해결 가이드"). Olive Young's promotion service likewise caches event metadata in Redis and reports a 478% TPS uplift and a 99.1% reduction in Redis Network Bytes Out after layering Caffeine on top (🇰🇷 oliveyoung.tech, "고성능 캐시 아키텍처 설계").

This is the home turf of `@Cacheable` and you should use it without apology:

```kotlin
@Service
class ProductCatalogService(private val repo: ProductRepository) {

    @Cacheable(
        cacheNames = ["product"],
        key = "#sku",
        unless = "#result == null"
    )
    fun findBySku(sku: String): ProductDto? =
        repo.findBySku(sku)?.toDto()

    @CacheEvict(cacheNames = ["product"], key = "#sku")
    fun invalidate(sku: String) { /* called from CDC consumer */ }
}
```

Two production rules apply almost universally. First, **never cache a JPA entity directly** — cache an immutable DTO/`data class`/`record`. The Hibernate session that loaded the entity is gone the moment the method returns; a deserialized entity from Redis is detached, has dead lazy proxies, and will give you `LazyInitializationException` at the worst possible moment. Second, **always include `unless = "#result == null"` or design for negative caching deliberately** — negative caching is its own pattern (§4.7), and a silent `null` cache entry is the single most common bug in this category.

A subtle Spring Data Redis pitfall is worth noting up front: Woowahan's team published a sharp post-mortem on Kotlin `data class`/Java `record` deserialization with `GenericJackson2JsonRedisSerializer` (🇰🇷 techblog.woowahan.com/22767, "Spring Cache + Spring Data Redis 사용 시 record 직렬화 오류"). Jackson's polymorphic type info is lost on records/data classes, so the *first* request succeeds (no cache hit) and the *second* one explodes. The fix is to register the type with `BasicPolymorphicTypeValidator` and `activateDefaultTyping`, or to use a typed serializer per cache name. Test cache deserialization in CI, not just cache writes.

**When NOT to use Spring Cache here:** if your "lookup table" is actually a 200K-row materialized projection, don't lean on `@Cacheable` with a one-key-per-row layout. Use a **bulk-loaded, refresh-ahead local cache** (§4.5) seeded once at startup or a Redis `Hash` you populate via a CDC pipeline (§4.4) — Olive Young's `행사_지급_조건_v3` keying is exactly that pattern.

### 1.2 Computed Pricing, Discount, and Tax Calculations

These look like read-throughs but they aren't, because the *inputs* are a tuple `(sku, customerSegment, region, promoCode, time-bucket)` and the function is pure given those inputs. `@Cacheable` works, but the key is the trick:

```kotlin
@Cacheable(
    cacheNames = ["price-quote"],
    key = "T(java.util.Objects).hash(#sku, #segment, #region, #activePromos.hashCode())",
    condition = "#segment != 'INTERNAL'"   // skip cache for staff orders
)
fun quote(sku: String, segment: String, region: String, activePromos: Set<String>): PriceQuote
```

Two design forces collide. First, the cardinality of the key space is large; you do not want this in Redis (network round-trips on every quote dominate the cost of computing the quote). Second, the values are bounded and small. **Caffeine with `expireAfterWrite(60s)` and `maximumSize(50_000)` is the right tool**, with a `MeterRegistry`-backed `recordStats()` so you can see hit rate per region. Don't reach for Redis here unless you must coordinate prices across pods (you usually don't — short TTL plus Caffeine on each pod gives every customer eventually consistent pricing in seconds).

### 1.3 Rate Limiting (Token Bucket, Sliding Window, Leaky Bucket)

Rate limiting is **explicitly not a Spring Cache use case**. The Spring Cache abstraction is "cache a return value"; rate limiting is "decrement a counter atomically and decide." Use one of:

| Approach | Use when | Don't use when |
|---|---|---|
| **Bucket4j + Redis (Lettuce-based ProxyManager)** | Multi-pod, need shared token bucket across the fleet, want a battle-tested algorithm | You are inside a Spring Cloud Gateway pipeline (use the built-in `RequestRateLimiter`) |
| **Resilience4j RateLimiter** | Per-pod (in-process) limiting for an outbound dependency you're trying not to overwhelm; want an integrated bulkhead/circuit breaker stack | You need fleet-wide enforcement |
| **Spring Cloud Gateway `RedisRateLimiter`** | Edge gateway, Lua-script-backed token bucket, per-route config | You're not running a gateway |
| **Redisson `RRateLimiter`** | You're already using Redisson and want a one-line distributed limiter (RateType.OVERALL or PER_CLIENT) | You need fine-grained burst tuning Bucket4j gives you |
| **Redis `INCR` + `EXPIRE` (DIY Lua)** | You want full control, leaderboards or custom semantics | You're building it for the first time — there be dragons (race conditions on EXPIRE) |

The Bucket4j-on-Redis idiom is well-trodden and worth making the default for application-level limiting:

```kotlin
@Configuration
class RateLimitConfig(redisClient: RedisClient) {

    @Bean
    fun proxyManager(redisClient: RedisClient): LettuceBasedProxyManager<String> =
        LettuceBasedProxyManager.builderFor(redisClient.connect(StringCodec.UTF8))
            .withExpirationStrategy(
                ExpirationAfterWriteStrategy.basedOnTimeForRefillingBucketUpToMax(
                    Duration.ofMinutes(10)))
            .build()

    fun bucketFor(apiKey: String, tier: Tier): Bucket {
        val limit = when (tier) {
            Tier.FREE  -> Bandwidth.simple(100,  Duration.ofMinutes(1))
            Tier.PAID  -> Bandwidth.simple(1000, Duration.ofMinutes(1))
            Tier.ADMIN -> Bandwidth.simple(10_000, Duration.ofMinutes(1))
        }
        return proxyManager.builder()
            .build(apiKey) { BucketConfiguration.builder().addLimit(limit).build() }
    }
}
```

Why not Redisson `RRateLimiter`? It's perfectly fine for coarse limits, but its OVERALL/PER_CLIENT model is rigid — multi-tier buckets, scheduled refills, and burst configurations are awkward. Bucket4j's `Bandwidth` model maps cleanly to product tiers.

Read deeply: LINE's "Redis Lua script for atomic operations and cache stampede" (engineering.linecorp.com/en/blog/redis-lua-scripting-atomic-processing-cache) is the best treatment of why you cannot do `INCR; EXPIRE` as two commands across a Redis Cluster — you must use a Lua script or a properly-configured client library.

### 1.4 Idempotency Keys

Idempotency is *not* caching, even though it is implemented with the same Redis cluster. It is "remember the response of this request for some TTL, and if you see the same `Idempotency-Key` again, return the stored response without re-executing." Stripe's foundational write (stripe.com/blog/idempotency, brandur.org/idempotency-keys) is the canonical reference and worth reading once a year.

The mistake people make: using `@Cacheable` keyed on `Idempotency-Key`. Don't. The semantics you want are explicit and stricter:

1. On request entry, atomically `SET key state=in-progress NX EX 86400`. If someone else got there first, return their stored response (or `409 Conflict` if still in flight).
2. On successful completion, `SET key state=complete payload=<json>`.
3. On failure, leave the in-progress marker (so retries with the same key get a deterministic error) — **don't** delete it, otherwise a retry can re-execute a partially-applied side effect.

Use raw `RedisTemplate` or Redisson's `RBucket.trySet(value, TTL)` for this. The Spring Cache abstraction has no notion of "I started but haven't finished" — its state machine is binary (present/absent). Stripe explicitly stores both successful and 5xx responses under the key for 24 hours; your implementation must do the same.

### 1.5 Session, JWT Denylist, Refresh Tokens, OAuth2 Token Cache

Three different sub-problems, three different mechanisms:

**Server-side sessions** → Spring Session Redis. Don't roll your own. Spring Session's `@EnableRedisHttpSession` handles the serialization, TTL refresh, and `HttpSession` integration. Spring Session's eviction is independent of `CacheManager`; do not try to unify them.

**JWT denylist (revocation list)** → Raw Redis with key `revoked:<jti>` and TTL equal to the token's remaining lifetime. Verify path becomes: validate signature → check `exp` → `EXISTS revoked:<jti>`. Auth0/SuperTokens-style "blocklist" pattern; cost is one Redis round-trip per request. If that's too much, use a **token-version counter per user** (`SET user:42:ver 7`) and embed `ver` in the JWT — bumping the version invalidates all tokens for that user with a single `INCR`. Cache the version in Caffeine for a few seconds and the per-request cost effectively disappears.

**Refresh tokens** → Hashed and stored server-side (one row per device), not via `@Cacheable`. Treat them as first-class persisted state.

**OAuth2 client-credentials token caching** (your service is calling another service): this *is* a Spring Cache use case if you want it to be. Cache the access token under the client_id with TTL = `expires_in - 30s` skew. Spring Security's `OAuth2AuthorizedClientManager` does this in-process; if you want to share tokens across pods to reduce IdP load, wrap your client-credentials acquirer with `@Cacheable(cacheNames=["oauth-tokens"], key="#clientRegistration")` over Redis.

**`UserDetailsService`** → Spring Security ships `CachingUserDetailsService` for this. Alternatively, slap `@Cacheable` on `loadUserByUsername` (docs.spring.io/spring-security/reference/servlet/authentication/passwords/caching.html). **Important:** disable credential erasure (`AuthenticationManagerBuilder.eraseCredentials(false)`), otherwise the cached `UserDetails` will have a `null` password on second access and authentication will silently fail.

### 1.6 Materialized Projections / CQRS Read Models

This is *not* a use case for `@Cacheable`. A read model is durable state, not a cache. Build it as a Redis `Hash` (or, at scale, a separate read-store like a denormalized DynamoDB table) and populate it via Kafka + Debezium CDC (§4.4). The Spring Cache abstraction's TTL-based invalidation is fundamentally the wrong model — your read model should be eventually consistent with the source of truth, not "expires every 5 minutes."

If you must use Spring Cache here, use it for the *L1 layer* on top of the Redis read store (§4.2) — the Redis read store is your truth, and Caffeine in front of it absorbs hot-key load.

### 1.7 Expensive Aggregations: Analytics, Leaderboards, Dashboards

**Leaderboards**: don't cache them, *implement* them. Redis Sorted Sets (`ZADD`/`ZREVRANGE`) are the leaderboard. `@Cacheable` on top of `ZRANGEBYSCORE` is fine if your dashboard reads it every second and the leaderboard updates every minute, but the leaderboard itself is the Redis structure.

**Analytics rollups** (daily revenue per merchant, hourly request counts): cache with `@Cacheable` keyed on `(merchantId, day)` and a TTL of a few minutes. Watch out for cache stampede on dashboard load — apply the patterns from §4.6.

**Dashboards** (multiple metrics composed): cache the *individual* metrics with short TTL, not the composed dashboard payload, because dashboards are personalized (filters, date ranges) and the composed payload's cardinality is huge.

### 1.8 Third-Party API Response Caching

Geocoding, currency rates, payment gateway BIN lookups, address validation. Geocoding is the textbook example: same address → same lat/lon, costs $0.005 per call, TTL is essentially infinite. `@Cacheable(cacheNames="geocode", key="#address.normalized()")` with Redis as the backing store, plus a **circuit breaker fallback** to the cached value on upstream failure (§4.8). Currency rates are similar but with TTL of one hour.

```kotlin
@Cacheable(cacheNames = ["geocode"], key = "#norm", unless = "#result == null")
@CircuitBreaker(name = "geocoding", fallbackMethod = "stale")
fun geocode(address: String): LatLon? {
    val norm = normalize(address)
    return externalGeocoder.lookup(norm)
}
fun stale(address: String, t: Throwable): LatLon? =
    cacheManager.getCache("geocode")?.get(normalize(address), LatLon::class.java)
```

The Resilience4j fallback combined with a long cache TTL effectively gives you "stale-while-error" semantics for free.

### 1.9 Search Results Pagination, Recommendations, User Preferences

**Search pagination**: dangerous. Caching `(query, page)` is fine, but you're paying RAM for paginated views the user will never revisit. Cache only the *first 1–3 pages* (the long-tail of pagination is cold).

**Recommendations**: cache the *recommendations themselves* per user with a TTL of an hour or two, not the underlying feature vectors. The Pinterest team's CacheLib write-up describes the inverse — they cache the ML *feature data*, not the predictions, because the model output is cheap once features are loaded (medium.com/pinterest-engineering/feature-caching-for-recommender-systems-w-cachelib).

**User preferences**: `@Cacheable` on `loadPreferences(userId)`. Invalidate on save — make the eviction part of the same DB transaction's after-commit hook, not in the middle of the transaction (otherwise a rollback leaves the cache evicted and the DB unchanged, and the next reader populates the cache with the old value).

### 1.10 Permission / RBAC / ABAC Decisions

Authorization is read-heavy and changes infrequently. `@Cacheable(cacheNames="perm-decision", key="#userId + ':' + #resource + ':' + #action")` is exactly right, with TTL on the order of a few minutes. The trap: revocation. If a user loses a role, you need that to take effect within seconds. Two paths:

1. Short TTL (30–60s) and accept the lag. This is what Auth0 does for cached JWT claims.
2. Pub/sub-driven cache invalidation: when a role is changed, publish to a Redis channel; all pods subscribe and invalidate the relevant keys in their Caffeine L1. (§4.4)

ABAC with policy engines (OPA, Cerbos) usually has its own decision cache; don't duplicate it in Spring Cache.

### 1.11 Configuration / Settings Cache, Feature Flags, Service Discovery

These deserve their own caching layer separate from `CacheManager`. Togglz has its own `cache` config in `application.yml` with `time-to-live` and `time-unit` (togglz.org/documentation/spring-boot-starter.html). Unleash ships a client-side cache with periodic refresh from the control plane. **Don't put a feature-flag check inside a `@Cacheable` method** — the cache key won't include the flag and you'll cache stale decisions.

Service discovery: Spring Cloud's `LoadBalancerClient` already caches; don't shadow it. Aurora connection pool: HikariCP isn't a Spring Cache concern.

### 1.12 GraphQL Persisted Query Cache, HTTP Response Cache

**Persisted queries**: a `Map<sha256, queryString>` keyed on the document hash. Pure `@Cacheable` use case, very long TTL, no invalidation. Caffeine in-process is plenty — these are immutable.

**HTTP response cache** is a different mechanism: Spring's `CacheControl` builder, ETag generation via `WebRequest.checkNotModified`, and `ShallowEtagHeaderFilter` for "compute the hash and return 304 without rendering." This is *complementary* to `@Cacheable`; the `@Cacheable` saves your server work, ETag/Cache-Control saves your bandwidth and the client's. Beware Spring Security's `CacheControlHeadersWriter` — by default it adds `Cache-Control: no-cache, no-store, max-age=0, must-revalidate` to authenticated responses, which neuters your ETag work; you must explicitly override `headers().cacheControl().disable()` and apply your own policy.

---

## Part 2 — Library Decision Matrix

The single most asked question in this space is "which library?" The answer is almost always context-dependent. Below is the matrix that reflects how I'd actually decide on a Kotlin/Spring Boot 3 stack.

### 2.1 Caffeine vs Cache2k vs Ehcache 3 vs Guava (in-JVM caches)

Caffeine wins by default for new code. It's the spiritual successor to Guava Cache (same author wrote the cache part of Guava and then Caffeine), uses Window-TinyLFU eviction (better hit rates than LRU), and is the one Spring Boot ships an autoconfiguration for. **Use Caffeine.** Cache2k has slight edge in microbenchmarks but the ecosystem is thinner. Ehcache 3 is heavier and primarily justified if you need a JCache (`javax.cache`) provider for Hibernate L2C compatibility. Guava Cache is officially in maintenance — migrate. The Caffeine project even ships a `caffeine-guava` adapter for incremental migration:

```kotlin
// build.gradle.kts
implementation("com.github.ben-manes.caffeine:caffeine:3.2.x")
implementation("com.github.ben-manes.caffeine:guava:3.2.x") // adapter
```

Migration is mechanical: replace `CacheBuilder.newBuilder()` with `Caffeine.newBuilder()`, ditto `LoadingCache`. The semantic gotcha is that Caffeine's `refreshAfterWrite` is async and requires a `CacheLoader` — Spring Boot's `CaffeineCacheManager` auto-config does **not** wire this for `@Cacheable` methods (issue 41762 was declined, github.com/spring-projects/spring-boot/issues/41762). You must register a `Caffeine<Object,Object>` bean and supply a `CacheLoader<Object,Object>` explicitly. There's a Doctor J's Blog walkthrough that's worth reading once (doctorjw.wordpress.com/2022/03/08/caffeine-cache-in-spring-boot/).

### 2.2 Redisson vs Lettuce (Redis clients)

This is the single most consequential client decision in a modern Spring stack.

**Lettuce** is the Spring Boot default. Netty-based, non-blocking, supports Reactive. It gives you `RedisTemplate` and the raw command surface. It's *small* (a few MB), well-tested, and what Spring Data Redis is built on.

**Redisson** is a *much* larger library that gives you 50+ Redis-backed Java collections (`RMap`, `RMapCache`, `RBucket`, `RBloomFilter`, `RRateLimiter`, `RLock`, `RSemaphore`, `RAtomicLong`, `RScheduledExecutor`, `RTopic`, …). It also implements Hibernate L2C and Spring Cache providers. It uses Lua scripts internally for atomicity and pub/sub for distributed primitives.

The Korean engineering community has converged hard on Redisson for distributed locks and complex primitives. Hyperconnect's deep dive (🇰🇷 hyperconnect.github.io/2019/11/15/redis-distributed-lock-1.html) explains *why*: "Redisson은 pubsub 기능을 사용하여 스핀 락이 레디스에 주는 엄청난 트래픽을 줄였습니다" — Redisson uses pub/sub to eliminate the spin-lock traffic that a hand-rolled SETNX loop generates against Redis. Kurly (🇰🇷 helloworld.kurly.com/blog/distributed-redisson-lock/) and Woowahan (🇰🇷 techblog.woowahan.com/17416 — "WMS 재고 이관을 위한 분산 락 사용기") both built `@DistributedLock` AOP wrappers around Redisson `RLock` for transactional concurrency control, and SSG's piece (medium.com/ssgtech, 오민혁) covers the AOP-ordering trap with `@Transactional` (the distributed lock advisor must run *outside* the transaction, otherwise you release the lock before the transaction commits — `@Order(1)` on the lock aspect).

The decision rule:
- **Use Lettuce** for your primary `RedisTemplate`, Spring Data Redis, and Spring Cache `@Cacheable` storage.
- **Add Redisson alongside it** when you need RLock, RBloomFilter, RRateLimiter, RMapCache (per-entry TTL — vanilla Redis hashes don't support that), or RAtomicLong with distributed atomic operations. Redisson can coexist with Lettuce; both connect to the same Redis cluster.

The cost of Redisson is mostly bundle size and complexity surface. It pulls in Netty (which you already have via Lettuce), and its JCache/Spring Cache integrations are sometimes opinionated in surprising ways. Use it for what it's exceptional at, not as a wholesale Lettuce replacement.

### 2.3 Hibernate 2LC vs Spring Cache vs HTTP Cache vs CDN

These are *complementary*, not alternatives. The tiering is roughly:

```
[CDN / browser cache]  ← static assets, long-cached APIs (Cache-Control)
       ↓
[HTTP cache: ETag, 304] ← Spring's CacheControl, ShallowEtagHeaderFilter
       ↓
[Spring Cache @Cacheable: per-method, dto-shaped]
       ↓
[Hibernate L2C: per-entity, embedded in ORM]
       ↓
[DB (Aurora)]
```

Use **Hibernate 2LC** when (a) you have a heavy entity-graph workload (lots of `findById` with associations) *and* (b) you can guarantee writes go through Hibernate (no `UPDATE` from a cron job, no Liquibase migrations bypassing the cache). Hibernate 6 with Redisson's L2C provider is the most mature Redis-backed L2C path. JHipster's docs (jhipster.tech/using-cache/) are a pragmatic reference. The DZone "Hibernate, Redis, and L2 Cache Performance" article makes the broader point that for distributed setups you often *don't* want L2C and instead push Spring Cache higher up the stack with DTOs.

Use **Spring Cache** for everything else that has DTO-shape return values. It's higher-leverage because (a) it caches *the work*, including any DTO mapping/computation, not just the entity, and (b) cache keys are explicit and tenant-aware (§3.2).

Use **HTTP cache** (`CacheControl`/ETag) for read endpoints that are public or per-user-stable. It saves bandwidth, not server work — which is exactly right for mobile clients on flaky networks.

Use **CDN edge cache** for genuinely public payloads (catalog browsing, public profiles).

### 2.4 Bucket4j vs Resilience4j vs Redis-Cell vs Spring Cloud Gateway

Already covered in §1.3. The summary line: *Bucket4j-on-Redis for application-level distributed limits, Resilience4j for in-process bulkheads on outbound calls, Spring Cloud Gateway's `RequestRateLimiter` if you have a gateway, Redis-Cell only if you're already running a Redis with the CL.THROTTLE module loaded.*

### 2.5 Spring Session vs OAuth2 Token Cache vs `@Cacheable` UserDetailsService

Three distinct concerns, three layers:

| Layer | Purpose | Tool |
|---|---|---|
| HTTP session | Carry server state across HTTP requests for a logged-in user | **Spring Session Redis** (`@EnableRedisHttpSession`) |
| Auth principal | Avoid re-loading `UserDetails` from DB on each request | **`@Cacheable` on `UserDetailsService`** (or `CachingUserDetailsService`) — disable credential erasure |
| Outbound OAuth2 tokens | Avoid re-acquiring client-credentials tokens for service-to-service calls | **OAuth2AuthorizedClientManager** (in-process) or `@Cacheable` over Redis (fleet-wide) |

Don't try to unify these. Their lifecycles are different.

### 2.6 Hazelcast vs Ignite vs Infinispan (JVM-native distributed caches)

If your shop is already on AWS with ElastiCache/MemoryDB, you almost certainly want Redis (Lettuce + optionally Redisson) and you should not invest in a JVM-native data grid. The reasons to consider Hazelcast/Ignite/Infinispan are narrow:

- **Hazelcast** if you want true read-through/write-through/write-behind handled *inside the cache process*, not your application code (hazelcast.org/compare-with-redis/), and you want compute-with-data (entry processors, distributed executors).
- **Apache Ignite** if you want SQL-over-cache and ACID transactions across cache + persistent store.
- **Infinispan** primarily if you're in a Red Hat/Quarkus shop or need its tight JCache compliance.

All three add operational burden (a JVM cluster to babysit). Modern Redis (clustered, with persistent storage modes) covers 90% of these needs with an order of magnitude less ops complexity. Kakao's "if(kakao)2020 카카오톡 캐싱 시스템의 진화" piece (🇰🇷 tech.kakao.com/2020/11/10/if-kakao-2020-commentary-01-kakao/) describes their migration *toward* Redis on Kubernetes (cache farm) for exactly this reason — they were running 256 dedicated Memcached boxes and consolidated to right-sized Redis pods on K8s.

### 2.7 Bloom Filters: Guava vs RedisBloom vs Redisson RBloomFilter

- **Guava `BloomFilter`** for in-process negative caching ("does this username exist?"). Built once, never replicated, lost on restart. Zero ops cost.
- **RedisBloom (BF.* commands)** for shared bloom filter across the fleet. Requires the RedisBloom module loaded on the cluster; ElastiCache supports it on engine 7+.
- **Redisson `RBloomFilter`** if you want a Redis-backed bloom filter without requiring the RedisBloom module — it's implemented on top of vanilla Redis using a custom bitmap layout. The cluster variant `RClusteredBloomFilter` partitions across master nodes.

The 99% case is Guava in-process — bloom filters are about avoiding a downstream lookup, and you don't need fleet-wide coordination for that.

### 2.8 Counter Patterns: Redis INCR vs Redisson RAtomicLong

Plain `INCR key` is the right answer 90% of the time — atomic, single round-trip, you can pair with `EXPIRE` for time-bucketed counters. Use `RAtomicLong`/`RAtomicLongMap` only when you want the higher-level `compareAndSet`/`addAndGet` semantics directly in code, or when you need a *map* of named counters with atomic operations.

### 2.9 Pub/Sub for Cache Invalidation: Redis Pub/Sub vs Streams vs Kafka

- **Redis Pub/Sub** is fire-and-forget. If a pod is briefly disconnected, it loses the invalidation. Acceptable for L1 invalidation where the worst case is "stale for one TTL period."
- **Redis Streams** with consumer groups gives you durable, replayable invalidation — better for read models where missing an event corrupts state.
- **Kafka** is the right tool if invalidation is part of a broader CDC pipeline (Debezium → Kafka → multiple consumers, one of which is the cache invalidator). It's also the right tool when the invalidation event itself triggers more work (search index update, audit log).

For pure cache-busting on a Caffeine L1, Redis Pub/Sub is simpler and the loss tolerance is fine.

### 2.10 Serialization: Jackson JSON vs Kryo vs Protobuf vs JDK

- **Jackson JSON** is the default for Spring Data Redis. Human-readable in `redis-cli`, schema-flexible, evolutionary-friendly. Pay the cost in CPU and bytes.
- **JDK serialization** is the old default and is uniformly worse — slow, fragile to class evolution, security-fraught. Avoid.
- **Kryo** is fast and compact but you must register classes; a version mismatch on rolling deploy yields a thundering herd of deserialization errors. Use only with disciplined version management.
- **Protobuf** is the right answer if you have proto-defined DTOs already and want compact, evolvable cache values. The Twilio "Happy Marriage of Redis and Protobuf" talk lays out the case.

A practical rule: **stick with Jackson JSON** unless you have measured that serialization is your bottleneck. The Woowahan record-deserialization post-mortem (🇰🇷 techblog.woowahan.com/22767) is mandatory reading regardless of which serializer you pick — schema versioning in DTO classes (`@JsonTypeInfo`, version field) saves you on deploy day.

---

## Part 3 — Implementation Patterns Cookbook (Code-Level)

### 3.1 Annotation Composition and Meta-Annotations

`@Cacheable`, `@CachePut`, `@CacheEvict`, `@Caching`, `@CacheConfig` is the surface area. The pattern that actually scales is **custom meta-annotations**:

```kotlin
@Target(AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
@Cacheable(
    cacheNames = ["product"],
    keyGenerator = "tenantAwareKeyGenerator",
    cacheManager = "redisCacheManager",
    unless = "#result == null"
)
annotation class ProductCache(val key: String = "")
```

Now every product cache use looks like `@ProductCache(key = "#sku")` — and when you change the cacheManager from Redis to a two-tier (§4.2), you change one annotation.

`@CacheConfig` at class level handles the simpler case (shared cache name and key generator across methods of one service). Use it for boilerplate reduction; use meta-annotations for cross-cutting policy.

### 3.2 Custom KeyGenerator: Tenant-Aware and Context-Sensitive Keys

The default `SimpleKeyGenerator` has a notorious bug: two methods with the same arg types collide. Marschall's better generator (marschall.github.io/2017/10/01/better-spring-cache-key-generator.html) folds the method into the key, which you should always do. For multi-tenant work, fold the tenant in too:

```kotlin
@Component
class TenantAwareKeyGenerator(private val tenantContext: TenantContext) : KeyGenerator {
    override fun generate(target: Any, method: Method, vararg params: Any?): Any {
        val tenant = tenantContext.currentTenantId() ?: "global"
        val locale = LocaleContextHolder.getLocale().toLanguageTag()
        return SimpleKey(tenant, locale, target.javaClass.name, method.name, *params)
    }
}
```

A few production-tested rules: **normalize before hashing** (case-fold emails, trim whitespace, sort sets) — these are silent cache-miss generators. **Version the key** (`v2:product:42`) when the DTO schema changes, so old and new pods don't fight over an incompatible cache value during a rolling deploy.

### 3.3 Custom CacheResolver: Dynamic Cache Selection

`CacheResolver` is the right hook when the *cache itself* depends on runtime context (not just the key). The classic case is multi-tenancy where you want hard cache isolation per tenant — different cache names rather than shared cache with composite keys (Baeldung's "Using Multiple Cache Managers in Spring" is a starting point):

```kotlin
@Component("tenantCacheResolver")
class TenantCacheResolver(
    private val cacheManager: CacheManager,
    private val tenantContext: TenantContext
) : CacheResolver {
    override fun resolveCaches(ctx: CacheOperationInvocationContext<*>): Collection<Cache> {
        val tenant = tenantContext.currentTenantId() ?: "global"
        return ctx.operation.cacheNames.map { name ->
            cacheManager.getCache("$tenant:$name") ?: error("no cache $tenant:$name")
        }
    }
}
```

This is the right level of abstraction for A/B testing cache strategies, multi-tenant isolation, and for routing different operations to different backing stores (Caffeine for hot reads, Redis for shared state).

### 3.4 Programmatic Usage for Coroutines and Complex Flows

`@Cacheable` on a `suspend` function in Spring 6 / Boot 3 is **not reliable**. The Kotlin compiler rewrites suspend functions to take a `Continuation` parameter, and the cache interceptor doesn't unwrap it. Spring issue 33210 documents this misbehavior with combined aspects (github.com/spring-projects/spring-framework/issues/33210), and the official answer is "use `CacheManager` programmatically." Concretely:

```kotlin
@Service
class ProductService(
    private val cacheManager: CacheManager,
    private val repo: ProductRepository
) {
    suspend fun findBySku(sku: String): ProductDto? {
        val cache = cacheManager.getCache("product") ?: return repo.findBySku(sku)?.toDto()
        cache.get(sku, ProductDto::class.java)?.let { return it }
        val dto = repo.findBySku(sku)?.toDto() ?: return null
        cache.put(sku, dto)
        return dto
    }
}
```

Verbose, yes, but it sidesteps the entire AOP-meets-coroutines mess and gives you explicit control — including the ability to do `withContext(Dispatchers.IO) { ... }` around the source-of-truth call. Wrap it in an extension function:

```kotlin
suspend inline fun <reified V : Any> Cache.getOrLoad(key: Any, crossinline loader: suspend () -> V?): V? =
    get(key, V::class.java) ?: loader()?.also { put(key, it) }
```

The same applies to reactive code: prefer `Mono.justOrEmpty(cache.get(key, T::class.java))` patterns over `@Cacheable` on `Mono`-returning methods (which has its own asynchronous-cache-resolver wiring you almost certainly don't want).

### 3.5 Conditional Caching with `condition` and `unless`

`condition` is evaluated *before* the method runs (skips cache lookup AND store); `unless` is evaluated *after* and only skips the store. The mnemonic is "`condition` gates the cache, `unless` gates the write." Real-world idioms:

- `unless = "#result == null"` — skip caching null returns (negative-caching is a separate, deliberate pattern; §4.7)
- `unless = "#result.isEmpty()"` — skip caching empty collections (often hides bugs, but useful for lookup tables that legitimately can return empty)
- `condition = "#tenant.tier != 'INTERNAL'"` — bypass cache for internal/staff requests (so they always see fresh data)
- `condition = "#root.method.name.startsWith('findBy') and #pageable.pageNumber < 3"` — only cache the first 3 pages of search results (§1.9)

### 3.6 DTO Design for Cache Values

Three rules saved by hard experience:

1. **Immutable.** Kotlin `data class` with `val`s, no lateinit, no mutable collections. A cached value is shared across callers; mutation poisons the cache.
2. **No JPA entities.** Map to a DTO at the cache boundary. Hibernate proxies don't survive serialization.
3. **Schema versioning.** Add a `@JsonProperty("_v") val version: Int = 2` field. On deploy, increment for breaking changes, and either accept transient deserialization failures (fall back to source-of-truth) or namespace the cache by version (`v2:product:...`). The Woowahan record post-mortem is a case study in what goes wrong without this.

For polymorphic DTOs, `@JsonTypeInfo(use = Id.CLASS, include = As.PROPERTY, property = "@class")` is required by `GenericJackson2JsonRedisSerializer` to round-trip correctly. Validate in tests.

### 3.7 Testing Patterns

The testing playbook for cache-heavy code is well-established:

- **Unit tests**: use `ConcurrentMapCacheManager` (in-memory) so you can assert hit/miss without Docker. `@TestConfiguration` overrides the production `CacheManager` bean.
- **Integration tests**: Testcontainers with the `redis:7-alpine` image and `@ServiceConnection` (Spring Boot 3.1+) auto-wires `spring.data.redis.host/port`. The rieckpil walkthrough (rieckpil.de/testing-caching-mechanism-with-testcontainers-in-spring-boot/) covers the Hogwarts-themed full pattern.
- **Cache hit assertion**: enable `recordStats()` on Caffeine, expose via Micrometer, assert `cache_gets_total{result="hit"}` increased.
- **Spy on `CacheManager`**: wrap with `@SpyBean` and `verify()` `getCache(name).get(key)` was called once across two service invocations of the same input — the Mockito-on-Spring-bean idiom.
- **Invalidation flows**: write tests that go put-DB-update-evict-readback — the Olive Young setup (🇰🇷 oliveyoung.tech) effectively does this at the integration level.

```kotlin
@SpringBootTest
@Testcontainers
class ProductServiceCacheIT {
    companion object {
        @Container @ServiceConnection
        val redis = GenericContainer("redis:7-alpine").withExposedPorts(6379)
    }

    @Autowired lateinit var productService: ProductService
    @Autowired lateinit var cacheManager: CacheManager

    @Test
    fun `second call hits cache`() {
        productService.findBySku("ABC")
        val cached = cacheManager.getCache("product")?.get("ABC")
        assertThat(cached).isNotNull()
        // optional: verify DB is hit only once
    }
}
```

For coroutines, build a `CoroutineCache` test fixture and assert via `runTest { ... }` that the loader lambda is invoked once across N parallel `async` calls.

---

## Part 4 — Architectural Patterns Playbook

### 4.1 Cache-Aside vs Read-Through vs Write-Through vs Write-Behind

The four patterns differ in *who* writes to the cache and *when*:

- **Cache-aside (lookup)**: app checks cache → on miss reads DB → app writes to cache. This is what `@Cacheable` does. Pros: simple, cache failure is non-fatal, app controls cache shape. Cons: app code is responsible for invalidation; first reader pays the latency.
- **Read-through**: cache library reads DB on miss (you give the cache a `CacheLoader`). Same end-state as cache-aside, but encapsulated in the cache library. Caffeine `LoadingCache` is read-through. Hazelcast supports it natively (hazelcast.org/compare-with-redis/) — Redis fundamentally does not, so "Redis read-through" in Spring is just cache-aside under another name.
- **Write-through**: app writes simultaneously to cache and DB. Used when read-after-write must be immediate. Hazelcast does this; with vanilla Redis you write twice in your application code (one DB, one cache). The trap is failure handling — what if DB succeeds and cache write fails? You now have stale cache and you're inconsistent.
- **Write-behind**: app writes to cache, cache writes to DB asynchronously in batches. Massive throughput win; massive durability risk if the cache dies before flush. Olive Young's 영주's piece (🇰🇷 youngju.dev/blog/database/2026-03-03-redis-caching-strategies) frames this risk plainly: "Write-Behind 패턴의 최대 위험은? 캐시(Redis) 장애 시 아직 DB에 반영되지 않은 데이터가 유실될 수 있습니다." Use only with Redis AOF persistence and a separate write-ahead log.

In Spring Boot 3, **default to cache-aside via `@Cacheable`/`@CacheEvict`**. Reach for write-through only when a downstream system requires it and you have the operational maturity to debug the failure modes. Avoid write-behind unless you're building Pinterest-scale and can invest in CacheLib-class infrastructure.

### 4.2 Near-Cache (L1 + L2) — Caffeine on Top of Redis

The most practical pattern for medium-traffic services: Caffeine in-process as L1 (microseconds, no network), Redis as L2 (hundreds of microseconds, shared across pods). Olive Young's piece (🇰🇷 oliveyoung.tech) measured 478% TPS uplift and 99.1% Redis Network Bytes Out reduction by adding a Caffeine L1 in front of an existing ElastiCache deployment. Kakao Pay (🇰🇷 tech.kakaopay.com/post/local-caching-in-distributed-systems/) documents the same architecture for "잘 변하지 않고 단순한 조회성 데이터" — slowly-changing simple-lookup data.

Spring's `@Caching` lets you compose two `@Cacheable`s pointing to different `CacheManager`s, but the Baeldung two-level guide (baeldung.com/spring-two-level-cache) flags the catch: Spring does **not** propagate L2 hits back to L1, so once L1 expires, every request hits L2 until L1 is re-populated. Their solution is a custom interceptor that writes through to L1 on L2 hits. In Kotlin:

```kotlin
@Configuration
class TwoLevelCacheConfig {
    @Bean fun caffeineCacheManager(): CacheManager =
        CaffeineCacheManager().apply {
            setCaffeine(Caffeine.newBuilder().expireAfterWrite(Duration.ofSeconds(30)).maximumSize(10_000))
        }

    @Bean fun redisCacheManager(cf: RedisConnectionFactory): CacheManager =
        RedisCacheManager.builder(cf)
            .cacheDefaults(RedisCacheConfiguration.defaultCacheConfig().entryTtl(Duration.ofMinutes(5)))
            .build()

    @Bean fun cacheManager(l1: CacheManager, l2: CacheManager): CacheManager =
        CompositeCacheManager(l1, l2).apply { setFallbackToNoOpCache(false) }
}
```

But composite is *fall-through*, not write-through-on-hit. For real two-tier with backfill, write a `CacheManager` decorator that wraps each `Cache` — on `get()`, check L1, then L2, and if L2 hits, `put()` into L1 before returning.

The invalidation rule for two-tier is non-negotiable: **invalidations must reach all L1 instances**. Use Redis Pub/Sub to broadcast cache-evict events; each pod subscribes and invalidates its Caffeine. If you skip this, an update on pod A invalidates Redis but not pod B's Caffeine, and pod B serves stale data until L1 expires.

### 4.3 Multi-Tenant Caching

Three options in increasing isolation strength:

1. **Composite key** (`tenantId:productId`) in a shared cache. Cheapest, weakest isolation. Risk: a noisy tenant evicts another tenant's hot keys.
2. **Per-tenant cache name** (`tenant42:product`, `tenant43:product`) via a `CacheResolver` (§3.3). Better eviction isolation; same Redis instance.
3. **Per-tenant Redis database/cluster**. True isolation; operational burden of N clusters or DB-index proliferation. Justified for compliance-segregated tenants.

Per-tenant TTLs and per-tenant max-sizes need a custom `CacheManager` that knows about tenants. Most teams stop at level 2 and that's almost always enough.

### 4.4 CDC-Driven Invalidation (Debezium → Kafka → Cache Invalidator)

When DB writes can come from outside your application — bulk imports, admin tools, other services — TTL-based invalidation lies to you. CDC fixes that by treating the DB transaction log as the source of truth for change events. The Debezium team's "Automating Cache Invalidation With Change Data Capture" (debezium.io/blog/2018/12/05/automating-cache-invalidation-with-change-data-capture/) is the foundational piece, and the redis-developer/sql-cache-invalidation-debezium repo has a working Spring Boot reference.

The architecture for a Spring Boot 3 service:

```
[Aurora MySQL/Postgres]
      ↓ binlog/WAL
[Debezium connector → Kafka topic "myapp.public.products"]
      ↓
[Spring @KafkaListener in your service]
      ↓
cacheManager.getCache("product").evict(productId)
      ↓
[Redis pub/sub broadcast]
      ↓
[All pods evict their L1 Caffeine]
```

```kotlin
@Component
class ProductCdcConsumer(private val cacheManager: CacheManager) {
    @KafkaListener(topics = ["myapp.public.products"])
    fun onChange(record: ConsumerRecord<String, String>) {
        val event = mapper.readTree(record.value())
        val payload = event["payload"]
        val sku = payload["after"]?.get("sku")?.asText()
            ?: payload["before"]?.get("sku")?.asText()
            ?: return
        cacheManager.getCache("product")?.evict(sku)
    }
}
```

The architectural payoff: your service stops being responsible for cache invalidation on writes that didn't go through it. The trap: re-emitting an invalidation event for a change that *originated* in this service is wasteful but harmless; ignoring application-side `@CacheEvict` and relying *only* on CDC introduces a longer eviction window (Kafka latency) which can break read-after-write consistency. Most teams keep both.

### 4.5 Refresh-Ahead

The opposite of expiry: refresh the cache value *before* it expires, in the background, so callers never block on a cold lookup. Caffeine has first-class support via `refreshAfterWrite(Duration)` paired with a `LoadingCache` — when a key is past its refresh threshold, the next caller gets the old value immediately while a background thread reloads. Redisson's `RMapCache` has eviction listeners you can use to schedule a refresh in a similar way.

This is the right pattern for *predictably hot, expensive-to-compute* values: dashboards loaded by every internal user every morning, market data refreshed every 30 seconds, ML feature blocks. It is the *wrong* pattern for high-cardinality caches (millions of keys) — you'll thrash background refreshes for keys nobody will read again.

A gotcha unique to Spring Boot: Spring Boot's `CaffeineCacheManager` auto-config does **not** wire a `CacheLoader`, so `refreshAfterWrite` raises `LoadingCache is needed for refreshAfterWrite` at runtime. You must explicitly construct a `CaffeineCacheManager` with a `CacheLoader` bean — Spring Boot issue 7540 and 41762 cover this. The minimal fix:

```kotlin
@Bean fun caffeineCacheManager(loader: CacheLoader<Any, Any>): CacheManager =
    CaffeineCacheManager().apply {
        setCaffeine(Caffeine.newBuilder()
            .expireAfterWrite(Duration.ofMinutes(10))
            .refreshAfterWrite(Duration.ofMinutes(2))
        )
        setCacheLoader(loader)
    }
```

### 4.6 Cache Stampede (Thundering Herd) Protection

The pattern: a hot key expires; 1000 concurrent requests all miss the cache; all 1000 hit the DB; the DB falls over. Toss's "캐시 문제 해결 가이드" (🇰🇷 toss.tech/article/cache-traffic-tip) is the most accessible Korean-language treatment, and Lee Taesu's PER (Probabilistic Early Recomputation) implementation in Spring Data Redis (🇰🇷 medium.com/@taesulee93/spring-data-redis-환경에서-per-probabilistic-early-recomputation) is a working Kotlin reference. Three defenses, in increasing complexity:

1. **`sync = true`** on `@Cacheable`. Spring locks per cache key; only one thread loads, others wait. Works for single JVM, doesn't help across pods. Use as the baseline.

   ```kotlin
   @Cacheable(cacheNames = ["heavy-thing"], key = "#id", sync = true)
   fun load(id: Long): HeavyDto = repo.heavyComputation(id)
   ```

2. **Distributed lock around cache rebuild.** Use Redisson `RLock` with short TTL; first thread to acquire the lock does the rebuild, others retry the cache after a short wait. The Toss article describes this as the standard fix. The trap: a thread can acquire the lock, crash, and leave others spinning until lease expiry — always set a `leaseTime`.

3. **Probabilistic early recomputation (XFetch/PER).** Each reader rolls a probability based on `(remainingTtl, recomputeCost)` to decide whether to recompute the value early. This eliminates the synchronized boundary entirely. Lee's Kotlin implementation:

   ```kotlin
   fun get(key: String, ttl: Duration, beta: Double = 1.0, recompute: () -> String): String? {
       val now = Instant.now().toEpochMilli()
       val (value, delta, expiry) = redisGet(key, now) ?: return null
       val perGap = delta * beta * log10(Random.nextDouble(0.0, 1.0))
       if ((now - perGap) >= expiry) {
           val newValue = recompute()
           val newDelta = Instant.now().toEpochMilli() - now
           save(key, newValue, newDelta, ttl)
       }
       return value
   }
   ```

A fourth defense for the *avalanche* case (many keys expiring at the same wall-clock minute) is **TTL jitter** — `entryTtl = base + Random.nextLong(jitter)`. Toss explicitly recommends this for nightly cache refreshes.

### 4.7 Negative Caching

Cache the absence of a result. Done wrong, this is a recipe for stale 404s; done right, it eliminates a class of DDoS-by-cache-miss attacks. Olive Young's youngju.dev piece (🇰🇷 youngju.dev/blog/database/2026-03-03-redis-caching-strategies) recommends a short TTL (60s) for negative caches, which is the right calibration — enough to break the herd, short enough that real creates become visible quickly.

Implementation via Spring Cache: cache a sentinel `NotFound` DTO, distinguish from `null`:

```kotlin
sealed class CacheLookup<out T> {
    object NotFound : CacheLookup<Nothing>()
    data class Found<T>(val value: T) : CacheLookup<T>()
}

@Cacheable(cacheNames = ["product-neg"], key = "#sku")
fun lookup(sku: String): CacheLookup<ProductDto> =
    repo.findBySku(sku)?.let { CacheLookup.Found(it.toDto()) } ?: CacheLookup.NotFound
```

Combine with a Bloom filter (§2.7) for the *upstream* check on extremely high-cardinality miss spaces.

### 4.8 Circuit Breaker Around Cache

Cache itself can fail (Redis cluster failover, network partition). The pattern is to wrap cache lookups with Resilience4j and fall back to direct DB on cache failure — *never* fail user requests because the cache is down. Pair with the geocoding pattern (§1.8) where the fallback is to the *stale* cached value if the upstream API is down.

```kotlin
@CircuitBreaker(name = "redis", fallbackMethod = "loadDirect")
@Cacheable(cacheNames = ["product"], key = "#sku")
fun load(sku: String): ProductDto = repo.findBySku(sku)!!.toDto()

fun loadDirect(sku: String, t: Throwable): ProductDto = repo.findBySku(sku)!!.toDto()
```

Note the Resilience4j-Coroutines compatibility caveat (Code 'n' Roll, blog.code-n-roll.dev/getting-started-with-spring-and-coroutines-part-3): the `@CircuitBreaker` annotation is not supported on suspend functions; use `circuitBreaker.executeSuspendFunction { ... }` directly in coroutine code.

### 4.9 Cache Versioning for Zero-Downtime Deploys

Three strategies in production use:

- **Prefix versioning** (`v2:product:42`): the cleanest. New code reads/writes `v2:`, old code reads `v1:`. After full deploy, drop `v1:` keys. Required when the DTO schema is breaking.
- **Dual-write during migration**: new code writes both `v1:` and `v2:`, reads `v2:` (with `v1:` fallback). Old code reads `v1:`. Once all pods are new, stop dual-write.
- **Lazy migration on read**: read tries `v2:` then `v1:`, transforms `v1:` → `v2:` and writes back. Lowest cache-invalidation cost; complicates the read path.

The Hyperconnect and Toss teams both implicitly version their distributed lock keys for this same reason — an older code path's lock format must not collide with a newer one's.

### 4.10 Request-Scoped vs Application-Scoped Caching

A pattern often overlooked: `RequestContextHolder`-scoped caches for joining the same lookup multiple times *within a single request*. If a controller calls four service methods that each call `permissionService.check(userId, …)`, you don't need a Redis round-trip on every check. A request-scoped `Map<String, Permission>` (or a `@RequestScope` Spring bean wrapping a `HashMap`) absorbs the redundancy. This isn't Spring Cache territory — don't try to use `@Cacheable` for it — but it's a valid layer above and complementary.

---

## Part 5 — Testing Strategies for Cache-Heavy Code

A consolidated checklist, building on §3.7:

- **`@AutoConfigureCache(cacheProvider = CacheType.SIMPLE)`** in unit tests forces in-memory caching, bypassing Redis. Pair with `@SpyBean(repository)` to verify "second call did not hit DB."
- **Testcontainers Redis** for integration. Use `@ServiceConnection` (Spring Boot 3.1+) so you don't have to set `spring.data.redis.*` properties manually. The auroria.io and rieckpil.de walkthroughs are the best end-to-end Kotlin/Java references.
- **Assert serialization compatibility**. Write a test that serializes a fresh DTO with the production `RedisSerializer`, stores it in Redis, then reads it back with the same serializer. The Woowahan record bug is reproduced exactly this way.
- **Cache hit metrics**. `@Cacheable` Spring Cache integrates with Micrometer when you set `spring.cache.redis.enable-statistics=true` (or `recordStats()` for Caffeine). Expose `cache.gets{result="hit"}` and assert via `MeterRegistry` in tests.
- **Concurrency tests for stampede protection**. Launch N coroutines hitting the same key simultaneously; assert the loader was invoked exactly once with `sync=true`.
- **CDC integration tests**. Use the Testcontainers Debezium image plus Kafka and your service container, write to the source DB, assert the cache eviction event arrived.

---

## Part 6 — Migration Playbooks

### 6.1 Hibernate 2LC → Spring Cache + Redis (with DTOs)

The case for this migration: Hibernate 2LC caches entities, which (a) ties cache contents to ORM internals, (b) can't cache computed values (only entity loads), and (c) fights with `@OneToMany` lazy loading. Moving the cache one level up to DTO-shaped values via Spring Cache is almost always a win.

The phased approach:

1. Identify entities currently in 2LC. Add DTO mappings (MapStruct or Kotlin extension functions).
2. Add `@Cacheable` on the *service* methods that return DTOs, using a Redis backing store. Keep 2LC running.
3. Verify hit rate parity in staging (Micrometer `cache.gets`).
4. Disable 2LC for the migrated entities (`@Cache` annotation removed; `hibernate.cache.use_second_level_cache=false`).
5. Remove the 2LC provider dependency.

The risk is increased load on the source DB during migration if cache shapes diverge. Run both for a week.

### 6.2 Guava Cache → Caffeine

Largely mechanical (§2.1). The semantic differences worth flagging:

- Caffeine's `expireAfterAccess` resets timing on `getIfPresent` — Guava's behavior is identical, but verify your assumptions.
- Caffeine's eviction is asynchronous; reads after `invalidateAll()` may briefly see old values. Tests that asserted synchronous eviction need adjustment.
- The `caffeine-guava` adapter (com.github.ben-manes.caffeine:guava) provides a Guava-compatible `Cache` implementation backed by Caffeine — use it during incremental migration of large codebases.

### 6.3 Migrating Cache Infrastructure with Zero Downtime

The hardest version: switching from one Redis cluster to another (e.g., AWS ElastiCache → MemoryDB; or a Redis 6 cluster to a Redis 7 cluster with different sharding). The playbook:

1. Provision the new cluster in parallel.
2. Configure your `RedisCacheManager` to do **dual-write** to both clusters. Reads still go to the old cluster.
3. Wait for TTLs to expire on the old cluster's hot keys; new cluster fills naturally on cache misses.
4. Cut over reads to the new cluster (config-flag or feature-flag controlled).
5. Stop dual-writing; decommission the old cluster.

Kakao's K8s Redis migration piece (🇰🇷 tech.kakao.com/2022/02/09/k8s-redis/) is a real-world example with operator-pattern automation. The Netflix EVCache migration to KVSP (infoq.com/articles/netflix-global-cache/) generalizes the pattern at extreme scale — they used a separate replication reader service to seed the new cluster before cutover, halving cross-region NLB usage.

### 6.4 Migrating to Two-Tier (Adding L1 in Front of Redis)

The Olive Young migration (🇰🇷 oliveyoung.tech) is the template:

1. Identify the top N hottest keys via Redis `MONITOR` sampling or AWS Elasticache Redis SlowLog.
2. Add a `CompositeCacheManager` with Caffeine first, Redis second, for *only those cache names*. Other cache names still go directly to Redis.
3. Wire Redis Pub/Sub-based eviction broadcasting so writes invalidate all pods' L1.
4. Measure (TPS, Network Bytes Out, p99 latency). Olive Young saw 478% TPS and 99.1% Bytes Out reduction; budget similarly.
5. Roll out incrementally to other cache names.

---

## Part 7 — Reference Appendix: Engineering Blogs

A curated, not-exhaustive set. Marked with 🇰🇷 for Korean-language sources.

**Korean tech blogs**

- 🇰🇷 **Toss** — "캐시 문제 해결 가이드 (DB 과부하 방지 실전 팁)" — toss.tech/article/cache-traffic-tip. The single best Korean-language summary of cache stampede, jitter, negative caching, and distributed-lock cache rebuilds.
- 🇰🇷 **Woowahan (배민)** — "WMS 재고 이관을 위한 분산 락 사용기" — techblog.woowahan.com/17416. AOP + Redisson distributed lock for inventory transfer.
- 🇰🇷 **Woowahan** — "Spring Cache(@Cacheable) + Spring Data Redis 사용 시 record 직렬화 오류 원인과 해결" — techblog.woowahan.com/22767. Required reading before deploying record/data class DTOs to a Redis cache.
- 🇰🇷 **Woowahan** — "Redis New Connection 증가 이슈 돌아보기" — techblog.woowahan.com/23121. Lettuce + ElastiCache idle-timeout interaction; pipelining and dedicated connections.
- 🇰🇷 **Kakao** — "if(kakao)2020 카카오톡 캐싱 시스템의 진화 — Kubernetes와 Redis를 이용한 캐시 팜 구성" — tech.kakao.com/2020/11/10/if-kakao-2020-commentary-01-kakao/. Memcached → Redis on K8s consolidation, host-network for throughput.
- 🇰🇷 **Kakao** — "쿠버네티스에 레디스 캐시 클러스터 구축기" — tech.kakao.com/2022/02/09/k8s-redis/. Replica reads, scale-out playbook.
- 🇰🇷 **Kakao Pay** — "분산 시스템에서 로컬 캐시 활용하기" — tech.kakaopay.com/post/local-caching-in-distributed-systems/. L1 + Redis + messaging for L1 invalidation.
- 🇰🇷 **Kurly** — "풀필먼트 입고 서비스팀에서 분산락을 사용하는 방법 — Spring Redisson" — helloworld.kurly.com/blog/distributed-redisson-lock/. The reference `@DistributedLock` AOP annotation that half the Korean Spring ecosystem now uses.
- 🇰🇷 **Hyperconnect** — "레디스와 분산 락(1/2)" — hyperconnect.github.io/2019/11/15/redis-distributed-lock-1.html. The Lettuce-vs-Redisson explainer with the pub/sub vs spin-lock comparison.
- 🇰🇷 **LINE Engineering** — "Redis Lua script for atomic operations and cache stampede" — engineering.linecorp.com/en/blog/redis-lua-scripting-atomic-processing-cache. Why pipelines aren't atomic across Redis Cluster, and PER (Probabilistic Early Recomputation) in production.
- 🇰🇷 **Coupang Engineering** — "JSON in Redis: When to use RedisJSON" (Jay Won) — slideshare presentation, Redis Day Seattle 2020. Coupang's frequency-cap data model in their ad platform, with String vs Hash vs RedisJSON benchmarks.
- 🇰🇷 **Olive Young Tech** — "고성능 캐시 아키텍처 설계 — 로컬 캐시와 Redis로 대규모 증정 행사 관리 최적화" — oliveyoung.tech/2024-12-10/present-promotion-multi-layer-cache/. Real numbers (478% TPS, 99.1% bytes out reduction) from a two-tier migration.
- 🇰🇷 **SK DevOcean** — "Spring Boot 성능 개선 사례 공유 (1) — Redis 및 Local 캐싱 활용" — devocean.sk.com/blog/techBoardDetail.do?ID=167203. Costume-shop product catalog cache with circular-dependency `ApplicationEventPublisher` workaround.
- 🇰🇷 **SSG Tech** — "SSG 자동화센터 운영시스템에서 분산 락을 사용하는 방법" — medium.com/ssgtech (오민혁). The AOP-ordering trap with `@Transactional` and distributed locks.
- 🇰🇷 Lee Taesu — "Spring Data Redis 환경에서 PER 알고리즘을 활용한 캐시 스탬피드 현상 해결" — medium.com/@taesulee93. Working Kotlin implementation of probabilistic early recomputation.

**Global engineering blogs**

- **Stripe** — "Designing robust and predictable APIs with idempotency" — stripe.com/blog/idempotency. The foundational treatment.
- **Brandur** — "Implementing Stripe-like Idempotency Keys in Postgres" — brandur.org/idempotency-keys. The canonical implementation walkthrough.
- **Netflix** — "EVCache" overview and architecture — netflix.github.io/EVCache/, github.com/Netflix/EVCache. Memcached-on-AWS at 400M ops/sec; "Building a Global Caching System at Netflix" on InfoQ goes deep on cross-region replication.
- **Netflix** — Hollow (announcement) — infoq.com/news/2016/12/announcing-netflix-hollow/. Disseminated cache for whole-dataset replication on every consumer.
- **Shopify Engineering** — "IdentityCache: Improving Performance one Cached Model at a Time" — shopify.engineering/identitycache-improving-performance-one-cached-model-at-a-time. Read-through ActiveRecord caching at Cyber-Monday scale; the "we never use fetchers on the path that moves money" rule is engineering wisdom.
- **Shopify Partners** — "An Introduction to Rate Limits" series — shopify.com/partners/blog/rate-limits. Leaky-bucket implementation at the API gateway tier.
- **Discord** — "How Discord Indexes Trillions of Messages" — discord.com/blog/how-discord-indexes-trillions-of-messages. Redis as a real-time indexing queue, then migrated to PubSub for guaranteed delivery; lessons on when Redis is the wrong queue.
- **Cloudflare** — "Introducing the Workers Cache API" — blog.cloudflare.com/introducing-the-workers-cache-api-giving-you-control-over-how-your-content-is-cached/. Edge-cache patterns; the "cache POST requests" idiom and Cache-Tag-based invalidation.
- **Debezium** — "Automating Cache Invalidation With Change Data Capture" — debezium.io/blog/2018/12/05/automating-cache-invalidation-with-change-data-capture/. CDC-driven cache eviction for Hibernate L2C; the architectural pattern generalizes to any cache.
- **Pinterest Engineering** — "Feature Caching for Recommender Systems w/ CacheLib" — medium.com/pinterest-engineering/feature-caching-for-recommender-systems-w-cachelib-8fb7bacc2762. ML feature caching at scale; CacheLib over LevelDB/RocksDB.
- **Spring Team** — "Locks and Leaders with Spring Integration" (Dave Syer) — presos.dsyer.com/decks/locks-and-leaders.html. The conceptual model for `LockRegistryLeaderInitiator` and the right way to think about distributed lock semantics.

**Background reading worth one careful pass**

- Martin Kleppmann, "How to do distributed locking" — martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html. The classic critique of Redlock; required context before you build correctness-critical distributed locks.
- Spring Framework Reference — "Declarative Annotation-based Caching" — docs.spring.io/spring-framework/reference/integration/cache/annotations.html. The official surface area; re-read every couple of years because it evolves quietly.

---

## Closing Notes

Three meta-observations to close:

The first is that **the Spring Cache abstraction is small on purpose.** It does *one* thing — annotate-driven memoization of method return values — and it does it well across many backing stores. Most "Spring Cache pain" comes from trying to make it do things it isn't (idempotency, rate limiting, leader election, queueing). The Korean engineering community's pattern of layering Redisson alongside Lettuce, with Spring Cache for the memoization slice and Redisson for distributed primitives, is the cleanest separation of concerns I've seen in the wild and is the recommendation here.

The second is that **the cache is part of your durability story whether you want it to be or not.** A misconfigured TTL is a stale-data outage. A missed invalidation on a permission change is a security incident. A stampede is a cascading failure. Treat your caches as production state with monitoring (Micrometer cache hit-rate metrics, key cardinality, eviction counts, per-tenant percentiles), with a runbook (what to do when ElastiCache fails over), and with chaos testing (kill a Redis pod in staging, verify the circuit breaker takes over). Toss, Olive Young, and Kakao all publish post-mortems where the cache was the protagonist; learn from them rather than starring in your own.

The third is that **the Korean tech blog ecosystem is unusually rich on these topics**, often more applied than the global counterparts. The Hyperconnect lock article, Toss's stampede guide, Woowahan's record-deserialization post-mortem, Olive Young's two-tier numbers, and Kurly's `@DistributedLock` annotation are all things you'll never see in an English-language Spring book. Read them in the original where you can; the implementation details are where the value lives.