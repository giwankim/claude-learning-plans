---
title: "Spring Cache Mastery for Kotlin Engineers"
category: "Spring & Spring Boot"
description: "12-week depth-first curriculum from Cache/CacheManager SPI internals and CacheAspectSupport source reading through Caffeine/Redis backends, stampede/avalanche defense, and Micrometer instrumentation, on Kotlin 2.x + Spring Boot 3.x with AWS/Aurora/Redis/Kafka"
---

# Spring cache mastery: a 12-week depth-first curriculum for Kotlin engineers

This curriculum takes you from "I use `@Cacheable` and it works" to "I can read the `CacheAspectSupport` source, design a multi-tier cache for a 10k-TPS service, defend it against stampede/avalanche, instrument it on Micrometer, debug `LazyInitializationException` on cached entities, and pick the right backend in 2026." It assumes ~10 hrs/week (8 hrs build, 2 hrs reading), Kotlin 2.x + Spring Boot 3.x, and your existing AWS/Aurora/Redis/Kafka stack.

The plan is deliberately depth-first. You will not touch `@Cacheable` until **Week 4**. You will read `CacheAspectSupport.java` in **Week 2** and write your own `Cache`/`CacheManager` in **Week 3**. Phase 4 (correctness) is the longest because that is where production caches actually fail.

---

## How to use this curriculum

Each week has: **Goals**, **Deep technical content** (annotated, with file paths and class names), **Kotlin pitfalls**, **Hands-on / deliverable**, **Reading (EN + KO)**, and **Self-test prompts**. Phases end with a portfolio project that you should commit to a public repo. A capstone (Phase 7) integrates everything against a realistic Aurora + Redis + Kafka simulation on EKS/ECS.

A small notational convention: **🇰🇷** marks Korean-language resources, **📜** marks primary sources (papers, official docs, source code), **🎯** marks deliverables.

---

## Phase 1 — Foundations and reading the source (Weeks 1–3)

The thesis of this phase is **Joel Spolsky's Law of Leaky Abstractions**: you cannot use `@Cacheable` correctly without knowing what `CacheAspectSupport` does on every invocation. We will not write a single `@Cacheable` annotation in this phase.

### Week 1 — The SPI: `Cache`, `CacheManager`, `ValueWrapper`

**Goals.** Internalize the two interfaces that everything else builds on. Understand the four-state semantics of `retrieve()`, the `NullValue` sentinel, and why `put` is allowed to be deferred.

**Deep content.**

The cache abstraction has exactly **two** interfaces you must know cold: `org.springframework.cache.Cache` and `org.springframework.cache.CacheManager`. Read the Javadoc word-by-word — the contract is unusually subtle.

`Cache` exposes four "shapes" of read:
- `get(Object)` returns a `ValueWrapper` or `null`. **A non-null wrapper whose `.get()` returns `null` is a cached null** — semantically distinct from a miss. This is what `NullValue.INSTANCE` (the sentinel in `org.springframework.cache.support`) and `AbstractValueAdaptingCache` exist to manage for stores that can't represent null natively (Redis being the obvious example).
- `get(Object, Class<T>)` adds type coercion and throws `IllegalStateException` on type mismatch.
- `get(Object, Callable<T>)` is the **single-flight loader**. The contract says: *"implementations should ensure that the loading operation is synchronized so that the specified `valueLoader` is only called once in case of concurrent access on the same key"* — this is what `@Cacheable(sync=true)` rides on.
- `retrieve(...)` (since 6.1) returns a `CompletableFuture<?>` and has a four-state return: straight `null` (cache *immediately* knows there's no mapping), CF completing with `null` (late-determined miss), CF completing with `ValueWrapper` (nullable hit), or CF completing with the raw value (when nulls are disallowed). This is what enables reactive/`Mono` caching from Spring 6.1 onwards.

`CacheManager` is just `getCache(name)` + `getCacheNames()`. Note that `getCache` *typically lazily creates on first call* — `ConcurrentMapCacheManager` and `CaffeineCacheManager` both do this by default unless `setCacheNames(...)` locks the set.

**Kotlin pitfalls (introduced now, applied later).**
- Kotlin `data class` is `final` by default. CGLIB silently filters final methods (`Enhancer.RejectModifierPredicate(ACC_FINAL)`). Without `kotlin-spring`, `@Cacheable` annotations compile, run, and **never cache**. We will fix this in Week 4 once we understand AOP.
- `@JvmInline value class` arguments arrive at the proxy already unboxed; SpEL `#id.raw` on a `value class UserId(val raw: UUID)` parameter will fail because `#id` is already the `UUID`.

**🎯 Deliverable.** Write `MinimalCache.kt` — a `HashMap`-backed `Cache` implementation in pure Kotlin, **no Spring**, just implementing the interface methods directly. Include: cached-null support via your own sentinel, `get(key, Callable)` with a per-key lock via `ConcurrentHashMap.compute`, and a `retrieve()` returning `CompletableFuture`. Write JUnit 5 tests that exercise all four `retrieve()` return states. **No `@Cacheable`** — instantiate `Cache` directly and call methods.

**Reading.**
- 📜 Spring reference, "Cache abstraction": https://docs.spring.io/spring-framework/reference/integration/cache.html
- 📜 `Cache` Javadoc: https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/cache/Cache.html
- 📜 `CacheManager` Javadoc: https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/cache/CacheManager.html
- 📜 Source: https://github.com/spring-projects/spring-framework/tree/main/spring-context/src/main/java/org/springframework/cache
- 🇰🇷 NHN Cloud — 개발자를 위한 레디스 튜토리얼 01/02 (foundational, vendor-neutral): https://meetup.toast.com/posts/224 and /225

**Self-test.** Without looking it up: what does `cache.get("missing")` return when the cache *holds a null mapping* for `"missing"`? When the cache *has no mapping at all*? Why does this matter for a Redis-backed `RedisCache`?

---

### Week 2 — AOP, interception, and where annotations actually live

**Goals.** Trace one `@Cacheable` invocation from caller to method body and back, naming every class involved. Understand the difference between PROXY and ASPECTJ modes. Read source.

**Deep content.**

`@EnableCaching` imports `CachingConfigurationSelector` (an `AdviceModeImportSelector`). In `PROXY` mode this pulls in `AutoProxyRegistrar` + `ProxyCachingConfiguration`. The latter (extends `AbstractCachingConfiguration`, `ImportAware`) registers three infrastructure beans:

```java
@Bean(CacheManagementConfigUtils.CACHE_ADVISOR_BEAN_NAME)  // "internalCacheAdvisor"
BeanFactoryCacheOperationSourceAdvisor cacheAdvisor(...)
@Bean CacheOperationSource cacheOperationSource()    // = AnnotationCacheOperationSource
@Bean CacheInterceptor    cacheInterceptor(...)
```

The advisor's pointcut (`CacheOperationSourcePointcut`) returns `true` for any method whose `CacheOperationSource.getCacheOperations(method, targetClass)` is non-null. The `AbstractAutoProxyCreator` then wraps matched beans.

At runtime: caller → JDK proxy or CGLIB subclass → `ReflectiveMethodInvocation.proceed()` → `CacheInterceptor.invoke(MethodInvocation)` → `CacheAspectSupport.execute(invoker, target, method, args)`. The execute method:

1. Processes `@CacheEvict(beforeInvocation=true)`.
2. `findCachedValue(...)` walks `@Cacheable` operations; first hit wins; misses are queued as `cachePutRequests`.
3. On hit, returns the wrapped value.
4. On miss with `sync=true`, calls `cache.get(key, Callable)` (or `cache.retrieve(key, Supplier)` for async).
5. Otherwise invokes the underlying method, then iterates queued put requests.
6. Processes `@CachePut` (always invoke + put).
7. Processes `@CacheEvict(beforeInvocation=false)`.

**Critical files to actually read this week:**
- `spring-context/.../cache/interceptor/CacheAspectSupport.java` — the heart. ~700 lines; read all of `execute(...)`, `findCachedValue(...)`, `processCacheEvicts(...)`, `wrapCacheValue(...)`.
- `spring-context/.../cache/interceptor/CacheInterceptor.java` — small; just adapts to `MethodInterceptor`.
- `spring-context/.../cache/annotation/SpringCacheAnnotationParser.java` — how `@Cacheable` becomes `CacheableOperation`.

**Kotlin pitfalls.**
- In `PROXY` mode (the default; `ASPECTJ` requires AspectJ weaving) self-invocation bypasses the proxy. `this.cachedMethod()` from inside the same bean does *not* hit the interceptor. This is the same trap as `@Transactional`. Solutions: extract to another bean (preferred), self-inject with `@Lazy private val self: ProductService`, or `@EnableCaching(exposeProxy=true)` + `AopContext.currentProxy()`.
- `companion object` methods, top-level `fun foo()`, and extension functions are all compiled as static methods on synthetic classes — Spring AOP cannot proxy them. Refactor to `@Component class` if you need caching.

**🎯 Deliverable.** Write a tiny standalone Spring app with `@EnableCaching` and one bean exposing one `@Cacheable`-annotated method (in Java, deliberately, to bypass Kotlin issues for now). Set a breakpoint inside `CacheAspectSupport.execute`. Write a 1-page **execution trace document** — a sequence diagram (Mermaid is fine) showing: proxy → advisor chain → interceptor → operation source lookup → cache resolver → key generator → cache.get → method.invoke → cache.put → return. Annotate it with the exact class names and method signatures.

**Reading.**
- 📜 `CacheAspectSupport` Javadoc: https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/cache/interceptor/CacheAspectSupport.html
- 📜 `EnableCaching` Javadoc (mode/proxyTargetClass/exposeProxy/order semantics): https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/cache/annotation/EnableCaching.html
- Spring Cloud blog — Spring cache source code analysis: https://www.springcloud.io/post/2022-03/spring-cache-source-code-analysis/
- Baeldung — Guide to Caching in Spring (read for confirmation, after the source): https://www.baeldung.com/spring-cache-tutorial

**Self-test.** Without IDE help: name every Spring class involved in answering one `@Cacheable` call, in order. What's the difference between `CacheOperation`, `CacheOperationContext`, and `CacheOperationInvocationContext`? Why does ASPECTJ mode handle self-invocation but PROXY mode doesn't?

---

### Week 3 — SpEL, `KeyGenerator`, `CacheResolver`, custom `CacheManager`

**Goals.** Understand the SpEL evaluation pipeline, `SimpleKeyGenerator`'s exact algorithm (and its method-name-collision trap), when to write a custom `CacheResolver`, and how to plug in a brand-new cache backend.

**Deep content.**

**SpEL.** Each operation gets a `CacheEvaluationContext` (extends `MethodBasedEvaluationContext`). On first variable access, `lazyLoadArguments()` fires `ParameterNameDiscoverer` and exposes:
- `#root.method`, `#root.target`, `#root.targetClass`, `#root.args`, `#root.caches`, `#root.methodName`
- `#aN`, `#pN` always available
- `#paramName` only when `-parameters` (Java) or Kotlin metadata is present

Timing matters: `condition` is evaluated **before** invocation (and `#result` is registered as *unavailable* — referencing it throws); `key` is evaluated before for `@Cacheable`/`@CacheEvict` but after for `@CachePut`; `unless` is always after.

**`SimpleKeyGenerator`.**
```java
if (params.length == 0) return SimpleKey.EMPTY;
if (params.length == 1) {
    Object p = params[0];
    if (p != null && !p.getClass().isArray()) return p;  // single-arg shortcut
}
return new SimpleKey(params);  // deepHashCode + deepEquals
```
Two production traps: (1) `SimpleKey` ignores method name + target class — `getModelA(1L)` and `getModelB(1L)` collide if they share a cache name; (2) the single-arg shortcut means a bare `Long`/`String`/data class is passed straight through to the backend — your Redis serializer must handle it.

**`CacheResolver` vs `CacheManager`.** A `CacheManager` is "name → Cache". A `CacheResolver` is "operation invocation context → caches". Use `CacheResolver` when the cache name itself depends on runtime args (multi-tenant `users-${tenantId}`), or when you route across multiple managers (e.g., L1 vs L2). They are mutually exclusive at the operation level.

**Boot's `CacheAutoConfiguration`.** Detection order (when no user-defined `CacheManager`/`CacheResolver`): GENERIC → JCACHE → HAZELCAST → INFINISPAN → COUCHBASE → REDIS → CAFFEINE → CACHE2K → SIMPLE → NONE. Override with `spring.cache.type=...`. Pre-create caches at startup with `spring.cache.cache-names=`.

**Kotlin pitfalls.**
- `data class` arguments are safe SimpleKey values (structural equals/hashCode). Plain `class` with `var` properties have identity equality → guaranteed cache miss.
- Inline value classes break SpEL property access: `data class Order(val userId: UserId)` generates `getUserId-<hash>()` and `#order.userId` will not resolve until [spring-projects/spring-framework#30468](https://github.com/spring-projects/spring-framework/issues/30468) lands. Rule of thumb: **never use `@JvmInline value class` in `@Cacheable` SpEL expressions**.

**🎯 Deliverable — Phase 1 capstone.** Build `ttl-cache-starter`: a publishable Spring Boot starter (autoconfiguration + properties) implementing a TTL-bounded, thread-safe, single-flight-capable in-memory cache as a custom `Cache`+`CacheManager`+`@AutoConfiguration`. Requirements:
1. Implements `retrieve()` so it works in Spring 6.1+ reactive contexts.
2. Uses `AbstractValueAdaptingCache` for free `NullValue` handling.
3. Has a `@ConfigurationProperties("acme.cache")` record with `defaultTtl: Duration`, `cacheNames: List<String>`.
4. Registers via `@AutoConfiguration` listed in `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`, conditional on `@ConditionalOnMissingBean(CacheManager.class)`.
5. Includes integration tests using `@SpringBootTest` with the starter on the classpath.

A skeleton is provided here:

```kotlin
class TtlCache(
    private val cacheName: String,
    private val ttl: Duration,
    allowNullValues: Boolean = true,
    private val clock: () -> Long = System::nanoTime,
) : AbstractValueAdaptingCache(allowNullValues) {
    private data class Entry(val storedValue: Any?, val expiresAt: Long)
    private val store = ConcurrentHashMap<Any, Entry>()

    override fun getName() = cacheName
    override fun getNativeCache(): Any = store
    override fun lookup(key: Any): Any? = store[key]?.takeIf { it.expiresAt >= clock() }?.storedValue
        .also { if (store[key]?.expiresAt?.let { e -> e < clock() } == true) store.remove(key) }

    override fun <T> get(key: Any, valueLoader: Callable<T>): T {
        val entry = store.compute(key) { _, existing ->
            val now = clock()
            if (existing != null && existing.expiresAt >= now) existing
            else try { Entry(toStoreValue(valueLoader.call()), now + ttl.toNanos()) }
                 catch (t: Throwable) { throw Cache.ValueRetrievalException(key, valueLoader, t) }
        }!!
        @Suppress("UNCHECKED_CAST") return fromStoreValue(entry.storedValue) as T
    }
    override fun put(key: Any, value: Any?) { store[key] = Entry(toStoreValue(value), clock() + ttl.toNanos()) }
    override fun evict(key: Any) { store.remove(key) }
    override fun clear() { store.clear() }
    // retrieve(), putIfAbsent(), evictIfPresent(), invalidate() omitted for brevity
}
```

**Reading.**
- 📜 `MethodBasedEvaluationContext` Javadoc: https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/context/expression/MethodBasedEvaluationContext.html
- Marschall — A Better Spring Cache KeyGenerator (collision pitfall): https://marschall.github.io/2017/10/01/better-spring-cache-key-generator.html
- Baeldung — Multiple cache managers / `CacheResolver`: https://www.baeldung.com/spring-multiple-cache-managers
- 📜 Boot autoconfig source: https://github.com/spring-projects/spring-boot/tree/main/spring-boot-project/spring-boot-autoconfigure/src/main/java/org/springframework/boot/autoconfigure/cache

**Self-test.** Why does `@Cacheable("foo") fun a(id: Long)` and `@Cacheable("foo") fun b(id: Long)` both cache under the same key for `id=1L`? How do you fix it without renaming caches?

---

## Phase 2 — Provider integrations and trade-offs (Weeks 4–5)

Now that you know what's *behind* the abstraction, start using it — and learn which backend to pick and why.

### Week 4 — Caffeine deep dive (the modern default)

**Goals.** Understand W-TinyLFU well enough to explain it to a peer. Know the three expiration knobs cold. Use `AsyncCache` for non-blocking single-flight. Wire Micrometer.

**Deep content.**

**W-TinyLFU.** Caffeine's eviction is the single biggest reason it beats Guava cache. Three components:
1. **Window cache (~1%)**: small LRU; new entries land here. Captures recency bursts.
2. **Main cache (~99%)**: Segmented LRU (probation + protected).
3. **TinyLFU admission filter**: when a candidate would be evicted from the window into main, TinyLFU compares the candidate's frequency-sketch estimate against the main-cache victim's. Higher-frequency wins. The frequency sketch is a 4-bit Count-Min Sketch (~8 bytes/entry); a doorkeeper Bloom filter rejects one-hit wonders from polluting CMS; periodic aging halves all counters. The window/main ratio self-tunes via hill-climbing: recency-skewed traces grow the window, frequency-skewed shrink it. ([Einziger, Friedman, Manes, ACM TOS 2017](https://dl.acm.org/doi/10.1145/3149371))

Result: hit rates within ~99% of Bélády's optimal across diverse traces, beating ARC and LIRS while using less memory.

**The three expiration knobs.**

| | Timer reset on | Behavior on expired entry |
|---|---|---|
| `expireAfterWrite(d)` | write/replace | **blocks** caller while reloading |
| `expireAfterAccess(d)` | every read or write | **blocks** caller while reloading |
| `refreshAfterWrite(d)` | write only | **returns stale value immediately**; async reload |

The "soft refresh" pattern combines hard ceiling + async refresh:
```kotlin
Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(Duration.ofMinutes(5))      // hard ceiling
    .refreshAfterWrite(Duration.ofMinutes(1))     // soft refresh after 1 min
    .recordStats()
    .build<Key, Value> { key -> loadFromDb(key) }
```
The first stale request after 1 min returns the old value and triggers an async reload via `ForkJoinPool.commonPool` (or a custom `executor`). This eliminates the latency tail of synchronous misses for hot keys without serving truly stale data forever.

**`AsyncCache` vs `Cache`.** `AsyncCache<K,V>` stores `CompletableFuture<V>`. Multiple concurrent gets for a missing key share *one* future — built-in stampede protection. Required for non-blocking I/O loaders (e.g., `WebClient`) and for Spring 6.1+ reactive caching: `CaffeineCacheManager.setAsyncCacheMode(true)` switches the manager onto Caffeine's `AsyncCache`.

**Spring integration.**
```yaml
spring.cache.type: caffeine
spring.cache.cache-names: products,users
spring.cache.caffeine.spec: maximumSize=10000,expireAfterWrite=10m,recordStats
```
For programmatic config or async mode, override with a `Caffeine<Object,Object>` `@Bean` or a `CacheManagerCustomizer<CaffeineCacheManager>`.

**Kotlin pitfalls.**
- This is the week to actually add the `kotlin-spring` plugin if you haven't:
  ```kotlin
  plugins { kotlin("plugin.spring") version "2.0.21" }
  ```
  Without it, `@Cacheable` on Kotlin classes silently does nothing.
- For custom cache-bearing meta-annotations: `allOpen { annotation("com.acme.Cached") }` in your Gradle `build.gradle.kts`.

**🎯 Deliverable.** Convert your Phase-1 starter benchmark service to Caffeine. Wire `CaffeineCacheMetrics` to Micrometer + Prometheus, expose `/actuator/prometheus`, and produce a Grafana dashboard JSON showing hit ratio, eviction counts (broken down by cause: `SIZE`/`EXPIRED`/`EXPLICIT`/`REPLACED`), and load-time histograms. Include a Gatling/k6 load test that drives the cache and shows the `refreshAfterWrite` latency improvement vs `expireAfterWrite`.

**Reading.**
- 📜 Caffeine wiki — Design: https://github.com/ben-manes/caffeine/wiki/Design — Efficiency: https://github.com/ben-manes/caffeine/wiki/Efficiency — Refresh: https://github.com/ben-manes/caffeine/wiki/Refresh
- 📜 TinyLFU paper (ACM TOS 2017): https://dl.acm.org/doi/10.1145/3149371
- 🇰🇷 LG U+ — 로컬 캐시 선택하기 (Caffeine vs EhCache vs Guava 비교): https://medium.com/uplusdevu/로컬-캐시-선택하기-e394202d5c87

**Self-test.** Explain in three sentences why W-TinyLFU dominates LRU on a workload with a temporary scan + a stable hot set. When would you pick `expireAfterWrite` over `refreshAfterWrite`?

---

### Week 5 — Redis (Spring Cache integration) + alternatives + trade-offs

**Goals.** Configure `RedisCacheManager` correctly (serializers, TTL, prefix, null handling). Understand the Redis 7.4 license shift and the Valkey migration path. Know when to reach for Hazelcast/Memcached/DragonflyDB/MemoryDB — and when not to.

**Deep content.**

**`RedisCacheManager` correct config.**
```kotlin
@Bean
fun cacheManager(cf: RedisConnectionFactory, om: ObjectMapper): RedisCacheManager {
    val defaults = RedisCacheConfiguration.defaultCacheConfig()
        .entryTtl(Duration.ofMinutes(10))
        .computePrefixWith { name -> "v2:$name::" }              // schema versioning
        .serializeKeysWith(SerializationPair.fromSerializer(StringRedisSerializer()))
        .serializeValuesWith(SerializationPair.fromSerializer(GenericJackson2JsonRedisSerializer(om)))
        .disableCachingNullValues()                              // explicit choice
    return RedisCacheManager.builder(cf)
        .cacheDefaults(defaults)
        .withCacheConfiguration("hot",  defaults.entryTtl(Duration.ofSeconds(30)))
        .withCacheConfiguration("cold", defaults.entryTtl(Duration.ofHours(6)))
        .enableStatistics()                                      // mandatory for Micrometer
        .transactionAware()                                      // honors @Transactional rollback
        .build()
}
```

Why each line matters: `JdkSerializationRedisSerializer` encodes `serialVersionUID` and package paths — any class refactor breaks every existing cache entry; **never use it**. `GenericJackson2JsonRedisSerializer` includes Jackson `@class` polymorphism markers — Java records and Kotlin sealed classes have specific gotchas (see Woowahan blog cited in Phase 4).

**The 2024 license shift, briefly.** Redis 7.2.4 was the last BSD release. 7.4+ became RSALv2/SSPLv1 dual-license (March 2024); Redis 8.0 added AGPLv3 as a third option. The Linux Foundation forked Valkey from 7.2.4. For commercial deployments, the cleanest path in 2026 is **Valkey** — drop-in compatible, BSD-3, AWS/Google/Oracle-backed, ~20% cheaper on ElastiCache nodes, ~33% cheaper on serverless. Lettuce, Spring Data Redis, redis-cli, RDB/AOF — all unchanged.

**Alternatives, decision-graded.**

| If you need… | Use |
|---|---|
| Fastest local read (sub-µs) | **Caffeine** (L1) |
| Caffeine + cross-instance coherence | **Caffeine + Valkey + pub/sub invalidation** |
| Drop-in BSD Redis replacement, AWS-managed | **ElastiCache for Valkey** |
| Durable in-memory primary DB (replace cache+DB pair) | **MemoryDB for Valkey** |
| JVM distributed primitives + cache | **Hazelcast** (CP Subsystem for strong consistency) |
| SQL on cached data, ACID | **Apache Ignite** |
| Multi-core single-node Redis at >1M QPS (after measuring!) | **DragonflyDB** |
| Active-active multi-master Redis API | **KeyDB** (or Valkey-based routing) |
| .NET stack with C# extensibility | **Garnet** |
| String-only, multi-core, ephemeral | **Memcached** |
| Off-heap > heap, JCache compliance | **Ehcache 3** |
| Anything new on Guava cache | **Migrate to Caffeine** |

**MemoryDB ≠ ElastiCache (the most-confused distinction).** ElastiCache is a *cache*: async replication, possible data loss on primary failure, ack on write before replication. MemoryDB is a *primary database*: every write committed to a Multi-AZ distributed transaction log before ack, 11 9s durability, single-digit-ms write latency, ~30–55% cost premium. Don't pay MemoryDB prices for cache workloads.

**Vendor benchmark sanity check.** The DragonflyDB "25× Redis" number is real — at `c6gn.16xlarge`, extreme connection counts. On a typical `m5.large` cache, the gap collapses to single-digit %. Real-world WordPress object-cache benchmarks (TweaksWP, 2026) show 12–17% real-world improvement. **Optimize your L1 hit rate before changing your L2 engine.**

**Kotlin pitfalls.**
- `GenericJackson2JsonRedisSerializer` + Java records has a deserialization-on-second-call bug (see Woowahan techblog #22767, Phase 4). Always include integration tests that hit the cache *twice* — once miss, once hit — to catch deserialization issues that don't manifest on the populating call.
- Spring Data Redis `RedisCache` does **not** record statistics by default — you must call `.enableStatistics()` (or set `spring.cache.redis.enable-statistics=true`). Without this, your Micrometer dashboard is blank for Redis.

**🎯 Deliverable.** Build a comparison harness that runs the same `getProduct(id)` workload (Zipfian distribution over 1M IDs, mixed read/write 95/5) against four configurations: (1) Spring `SimpleCacheManager` (in-process `ConcurrentMapCache`); (2) `CaffeineCacheManager`; (3) `RedisCacheManager` over local Redis; (4) two-level Caffeine + Redis (custom `Cache` impl — see Week 7). Report p50/p95/p99 latency, hit ratio, and DB QPS reduction. **Write up the trade-off in `BENCHMARK.md`.**

**Reading.**
- 📜 Spring Boot caching: https://docs.spring.io/spring-boot/reference/io/caching.html
- 📜 Valkey project: https://valkey.io/ — A year of Valkey: https://www.linuxfoundation.org/blog/a-year-of-valkey
- 📜 ElastiCache vs MemoryDB: https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/related-services-choose-between-memorydb-and-redis.html
- Foojay — distributed cache invalidation patterns: https://foojay.io/today/distributed-cache-invalidation-patterns/
- 🇰🇷 Olive Young — 고성능 캐시 아키텍처 설계 (L1+L2 case study, +478% TPS): https://oliveyoung.tech/2024-12-10/present-promotion-multi-layer-cache/

**Self-test.** Why does enabling `transactionAware()` on `RedisCacheManager` matter for write-through correctness? When does `disableCachingNullValues()` cause cache penetration?

---

## Phase 3 — Multi-tier and reactive (Weeks 6–7)

### Week 6 — Reactive caching and Kotlin coroutines

**Goals.** Cache `Mono`/`Flux` correctly under Spring 6.1+. Know why pre-6.1 was broken. Pick a workaround for `suspend fun`.

**Deep content.**

**The pre-6.1 reactive caching footgun.** Annotating a `Mono`-returning method with `@Cacheable` cached the `Mono` *publisher*, not the emitted value. Most reactive sources (`ReactiveMongoRepository.findById` etc.) are *cold* — every subscription re-executes. Worse, errors got cached as a permanent error publisher. `CacheMono` from `reactor-extra` was the workaround.

**Spring 6.1+ native support.** The interceptor consults `ReactiveCachingHandler` (using `ReactiveAdapterRegistry`) when the return type is `CompletableFuture`, `Mono`, or `Flux`. For `Mono` it stores the emitted value (or `NullValue` for empty); for `Flux` it `collectList()`s and rehydrates from the cached list. **For Caffeine this requires `setAsyncCacheMode(true)`.** `ConcurrentMapCache` adapts automatically.

⚠️ The `Flux` `collectList()` semantics are a memory hazard — if the flux is large, the entire list is held in cache memory. For streams, do not use `@Cacheable`; use `Mono#cache()` or roll your own `AsyncCache<K, List<T>>`.

**Kotlin coroutines: there is no first-class support.** A `suspend fun load(id: Long): Foo` compiles to `Object load(long, Continuation)`. Consequences:
- `#root.args` carries the trailing `Continuation` — never reference it in SpEL.
- Return type is `Object` (the `COROUTINE_SUSPENDED` sentinel or value), so 6.1's reactive detection does not apply.
- Without intervention, you cache `COROUTINE_SUSPENDED` and get `ClassCastException`s.

**Three workarounds, in order of preference.**

(a) Bridge to `Mono` with `mono { ... }` from `kotlinx-coroutines-reactor`:
```kotlin
@Cacheable("books", key = "#isbn")
fun findBookAsync(isbn: String): Mono<Book> = mono { repo.findById(isbn) }
suspend fun findBook(isbn: String): Book = findBookAsync(isbn).awaitSingle()
```

(b) Manual `cache.get`/`cache.put` in service code — simplest, fully type-safe:
```kotlin
@Service
class BookService(cacheManager: CacheManager, private val repo: BookRepo) {
    private val cache = cacheManager.getCache("books")!!
    suspend fun find(isbn: String): Book =
        cache.get(isbn, Book::class.java) ?: load(isbn).also { cache.put(isbn, it) }
    private suspend fun load(isbn: String): Book = repo.findById(isbn)
}
```
For per-key single-flight, replace the manual lookup with Caffeine `AsyncCache.get(key, mappingFunction)` and bridge via `kotlinx-coroutines-jdk8` (`CompletionStage.await()`).

(c) Custom interceptor (`spring-kotlin-coroutine` library, unmaintained — avoid for new code).

**Resilience4j around the cache.** Treat Redis as a remote dependency. Wrap reads in `CircuitBreaker` + `TimeLimiter` + `Bulkhead`:
```yaml
resilience4j.circuitbreaker.instances.redisCache:
  slidingWindowType: TIME_BASED
  slidingWindowSize: 60
  failureRateThreshold: 50
  slowCallDurationThreshold: 200ms
  waitDurationInOpenState: 30s
resilience4j.timelimiter.instances.redisCache:
  timeoutDuration: 150ms
```
On open circuit, fall through to DB — never let cache failure fail the request.

**🎯 Deliverable.** Build `reactive-cache-lab`: a Spring WebFlux + Kotlin coroutines service with three endpoints — `/products/{id}` using Spring 6.1 native `Mono` caching (Caffeine async mode), `/users/{id}` using manual coroutine cache.get/put with Caffeine `AsyncCache`, `/orders/{id}` using `CacheMono` over Redis. Apply Resilience4j circuit-breaker around the Redis path. Show, with chaos tests (kill Redis), that requests still succeed via the DB fallback.

**Reading.**
- 📜 Spring Framework 6.1 release notes: https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.1-Release-Notes
- Baeldung — WebFlux + `@Cacheable`: https://www.baeldung.com/spring-webflux-cacheable
- code-n-roll.dev — Spring + coroutines (caching limits): https://blog.code-n-roll.dev/getting-started-with-spring-and-coroutines-part-3
- 📜 Resilience4j Spring Boot 3 getting started: https://resilience4j.readme.io/docs/getting-started-3

**Self-test.** Why does `@Cacheable` on a `Flux<Order>` create a memory hazard for large result sets? What's the exact JVM signature of `suspend fun foo(id: Long): Bar`?

---

### Week 7 — Multi-tier (L1+L2) caching done right

**Goals.** Build a real two-level cache. Solve cross-instance L1 invalidation. Understand why `CompositeCacheManager` does *not* compose caches.

**Deep content.**

**The pattern.** Caffeine L1 (sub-µs) + Redis/Valkey L2 (~1ms) + DB (~5–50ms). L1 hits avoid the network entirely; L2 catches L1 misses without falling through to DB; L2 also survives pod restart and is shared across instances.

**The hard problem: cross-instance L1 invalidation.** When pod A writes a new value, A's L1 is updated but pods B/C/D still hold the old value locally.

Three approaches, ordered by complexity:
1. **Short L1 TTL** (30s–2min): bounded staleness, no infrastructure. Works when business tolerance is "stale by ≤1 min is fine."
2. **Redis pub/sub invalidation bus**: all pods subscribe to `cache:invalidation`; on every write, publish `<cacheName>:<key>`. Latency to convergence: 5–50ms typically. Caveat: pub/sub is at-most-once — pair with short TTL as backstop.
3. **Kafka-based bus**: each instance is a Kafka consumer with its own group ID (so every instance sees every message). Durable, ordered, replayable. Pay this cost only when invalidation reliability matters.

**`CompositeCacheManager` is misleadingly named.** It does **not** compose caches. It iterates managers and returns the first match. For real L1+L2 you must implement a custom `Cache`:

```kotlin
class TwoLevelCache(
    private val name: String,
    private val l1: Cache,                              // Caffeine
    private val l2: Cache,                              // Redis
    private val publisher: InvalidationPublisher,
) : Cache {
    override fun getName() = name
    override fun getNativeCache(): Any = l1.nativeCache
    override fun get(key: Any): ValueWrapper? =
        l1.get(key) ?: l2.get(key)?.also { l1.put(key, it.get()) }
    override fun <T> get(key: Any, type: Class<T>?): T? =
        l1.get(key, type) ?: l2.get(key, type)?.also { l1.put(key, it) }
    override fun <T> get(key: Any, valueLoader: Callable<T>): T =
        l1.get(key, type = null) as? T
            ?: l2.get(key, valueLoader).also { l1.put(key, it) }
    override fun put(key: Any, value: Any?) { l2.put(key, value); l1.put(key, value) }
    override fun evict(key: Any) {
        l2.evict(key); l1.evict(key); publisher.publish(name, key.toString())
    }
    override fun clear() { l2.clear(); l1.clear(); publisher.publishClear(name) }
}
```

The publisher implementation:
```kotlin
@Component
class InvalidationPublisher(private val redis: StringRedisTemplate) {
    fun publish(cache: String, key: String) {
        redis.convertAndSend("cache:invalidation", "$cache:$key")
    }
}
@Component
class InvalidationListener(@Qualifier("l1") private val l1: CacheManager) : MessageListener {
    override fun onMessage(message: Message, pattern: ByteArray?) {
        val (cache, key) = String(message.body).split(":", limit = 2)
        l1.getCache(cache)?.evict(key)
    }
}
```

**TTL sizing.** L1 TTL < L2 TTL. L1 `maximumSize` limits per-pod memory. Use `refreshAfterWrite` on L1 so hot entries refresh asynchronously from L2/DB and never block the request thread. L2 longer TTL survives pod recycling.

**🎯 Deliverable — Phase 3 capstone.** `multi-tier-product-cache`: a Spring Boot 3 service with `TwoLevelCache` wrapping Caffeine + Redis, pub/sub-driven L1 eviction, version-prefixed Redis keys (`v1:products::123`), Micrometer metrics for both tiers, deployed on a local k3d cluster with 3 replicas. Demonstrate cross-pod invalidation propagation in <50ms via integration test.

**Reading.**
- Baeldung — two-level cache: https://www.baeldung.com/spring-two-level-cache
- 🇰🇷 Kakao Pay — 분산 시스템에서 로컬 캐시 활용하기: https://tech.kakaopay.com/post/local-caching-in-distributed-systems/
- 🇰🇷 Olive Young — 고성능 캐시 아키텍처 설계: https://oliveyoung.tech/2024-12-10/present-promotion-multi-layer-cache/
- 🇰🇷 SK Devocean — Spring Boot 성능 개선 (Redis 및 Local 캐싱): https://devocean.sk.com/blog/techBoardDetail.do?ID=167203
- 🇰🇷 Woowahan — 가게노출 시스템 (3-tier Reactor + Redis + DynamoDB): https://woowabros.github.io/experience/2020/02/19/introduce-shop-display.html
- Stack Overflow — Nick Craver, "How we do app caching": https://nickcraver.com/blog/2019/08/06/stack-overflow-how-we-do-app-caching/

**Self-test.** Your team is debating whether to drop the pub/sub bus and just use a 60-second L1 TTL. What three questions should you ask the product owner before deciding?

---

## Phase 4 — Correctness and consistency (Weeks 8–10) — the longest phase

This phase is the heart of the curriculum. The user explicitly called these out as the primary operational concerns, and most engineers get the dual-write reasoning subtly wrong. Plan for ~12–14 hours/week here.

### Week 8 — The anomaly trio: penetration, breakdown, avalanche

**Goals.** Implement and mitigate each anomaly in code. Understand why `sync=true` is single-JVM and what to do for cluster-wide single-flight.

**Deep content.**

**Cache penetration (캐시 관통).** Repeated lookups for keys that exist in neither cache nor DB. Causes: malicious ID scans, broken FK references, deletions. Mitigations:
- **Null caching** with short TTL: `redis.setex("product:$id", 60, NULL_SENTINEL)`. Trade-off: bloats keyspace; bound the negative-key namespace.
- **Bloom filter pre-check**: in-memory (Guava `BloomFilter`) or **RedisBloom** module (`BF.RESERVE`/`BF.ADD`/`BF.EXISTS`). False-positive rate ~0.1% costs ~18 MB for 10M keys. False negatives are mathematically impossible — that's the property we exploit.
- **Validation at gateway**: range checks, auth.

The Toss tech-blog's "캐시 문제 해결 가이드" recommends **Null Object Pattern over Bloom Filter** because *"if the bloom filter's integrity is broken, you have to rebuild it from all caches, which is operationally hard."* Read the article — it's the single best Korean-language reference on this topic.

**Cache breakdown (핫키 만료).** A single hot key expires; thousands of concurrent readers stampede the DB.
- `@Cacheable(sync=true)` — single-flight via `cache.get(key, Callable)`. **Per-JVM only**: each pod still does one DB call. Confirmed in [spring-data-redis#1670](https://github.com/spring-projects/spring-data-redis/issues/1670). Watch for the recursive-call trap: calling `sync=true` method with same key from inside its own loader throws `IllegalStateException: Recursive update` from `ConcurrentHashMap.computeIfAbsent`.
- **Distributed lock for cluster-wide single-flight**: Redisson `RLock` with watchdog. Default lease 30s, auto-extended every 10s while holder is alive (`Config.lockWatchdogTimeout`). Use `tryLock(waitTime, leaseTime, unit)` with explicit `leaseTime` to disable watchdog when work is bounded.
- **Logical / soft TTL** ("logical expiration"): store `{value, expireAt}` with no Redis TTL; on read, if `now > expireAt`, asynchronously refresh and return stale. Equivalent to HTTP `stale-while-revalidate` (RFC 5861).
- **Probabilistic Early Recomputation (PER)**: `if (-delta * beta * Math.log(random.nextDouble()) >= remainingTTL) recompute`. Higher beta → earlier recompute. Hwahae's case study eliminated TTL expirations during a 5-minute stress test even with 5–15s cache regeneration time.

**Cache avalanche (캐시 애벌랜치).** Many keys expire simultaneously (mass TTL coincidence, Redis restart, AZ failover) → DB overrun. Mitigations:
- **Jittered TTL**: `ttl = base + ThreadLocalRandom.nextLong(0, jitter)`. Industry default ±10–30%.
- **Tiered TTLs** by importance.
- **Pre-computed / scheduled refresh** for top-N hot keys via `@Scheduled`.
- **Multi-level cache** (Phase 3) — Caffeine L1 absorbs the burst.
- **Persistence** so a Redis restart doesn't cold-start everything (RDB+AOF).
- **Circuit breaker** to shed load to DB.

**🎯 Deliverable.** `stampede-simulator`: a load-test rig (k6 or Gatling) that drives a Spring Boot service with a deliberately small Caffeine cache (5 entries) + 30s TTL against a slow PostgreSQL (200ms query). Implement four mitigation modes via runtime config: (1) baseline (no protection), (2) `@Cacheable(sync=true)`, (3) Redisson `RLock`, (4) PER with logical expiration. Measure p99 latency and DB QPS for each mode under a 1000-RPS load against 5 hot keys.

**Reading.**
- 🇰🇷 Toss — 캐시 문제 해결 가이드 (DB 과부하 방지 실전 팁): https://toss.tech/article/cache-traffic-tip
- 🇰🇷 LINE Engineering — Redis Lua scripting + PER algorithm: https://engineering.linecorp.com/en/blog/redis-lua-scripting-atomic-processing-cache/
- 🇰🇷 Hwahae — 캐시 스탬피드를 대응하는 PER 알고리즘 구현: https://blog.hwahae.co.kr/all/tech/14003
- 🇰🇷 NHN Cloud Meetup — 캐시 성능 향상기: https://meetup.nhncloud.com/posts/251
- 📜 Redisson distributed locks: https://redisson.pro/docs/data-and-services/locks-and-synchronizers/
- 📜 RedisBloom: https://redis.io/docs/latest/develop/data-types/probabilistic/bloom-filter/

**Self-test.** Why does `@Cacheable(sync=true)` not protect against cluster-wide stampede? Name three reasons jittered TTL is preferable to perfectly aligned TTL even in a cluster with no avalanche history.

---

### Week 9 — The dual-write problem (the most important week)

**Goals.** Be able to derive — without notes — exactly why each of the four naive cache+DB write strategies is broken. Implement delayed double-delete. Understand transactional outbox + Debezium for cache invalidation.

**Deep content.** Most Medium articles get this subtly wrong. Read these failure modes carefully — there is no algorithm using only DB+cache that is strongly consistent without external coordination.

**Strategy 1 — Update DB, then update cache.**
```
T1 (writer A): UPDATE db id=1 SET v=100  ─┐
T2 (writer B): UPDATE db id=1 SET v=200    │ interleave on cache writes
T2: SET cache:1 = 200                      │
T1: SET cache:1 = 100                     ─┘
DB: v=200      Cache: v=100   ❌ stale forever (until TTL)
```
DB writes commit in order (B last) but the cache `SET`s race — A's set arrives last because of GC pause / network jitter.

**Strategy 2 — Update cache, then update DB.**
```
T1: SET cache:1 = 100
T1: UPDATE db id=1 SET v=100  → fails (constraint, deadlock, network)
DB: v=old      Cache: v=100   ❌ cache reflects data DB never committed
```
Worse: any reader sees a value that doesn't exist in the system of record.

**Strategy 3 — Delete cache, then update DB (pre-invalidate).**
```
T1 (writer): DEL cache:1
T2 (reader): GET cache:1 → MISS
T2 (reader): SELECT db → reads OLD v=100 (T1 hasn't committed yet)
T1 (writer): UPDATE db id=1 SET v=200 (commits)
T2 (reader): SET cache:1 = 100   ← stale repopulation
DB: v=200      Cache: v=100   ❌ permanent until TTL
```
The dangerous, non-obvious case. Between the delete and the DB commit, a concurrent reader populates the cache from the *unchanged* DB.

**Strategy 4 — Update DB, then delete cache (canonical Cache-Aside).** Best of the four. What Microsoft Azure docs recommend. Still has a race:
```
T2 (reader): GET cache:1 → MISS               (before T1 even starts)
T2 (reader): SELECT db → reads OLD v=100
T1 (writer): UPDATE db id=1 SET v=200 (commits)
T1 (writer): DEL cache:1
T2 (reader): SET cache:1 = 100                ← old value resurrects
DB: v=200      Cache: v=100   ❌
```
Failure window is small but possible under load. Solutions: delayed double delete, transactional outbox.

**Delayed double delete (지연된 이중 삭제).**
```
1. DEL cache:k          // pre-invalidate
2. UPDATE db SET ...
3. sleep N ms           // ≥ worst-case stale-read window
4. DEL cache:k          // mop up stale repopulation
```
Tuning N: must exceed `(read_latency + DB_query_latency + cache_set_latency)` for any reader started before step 2. Typical 500ms–2s, traffic-dependent. Drawbacks: still eventual; latency in the write path; tuning is fragile (GC pauses, slow queries, replica lag); if step 4 fails, staleness persists until TTL; doesn't help cross-region replicas.

In Spring, do step 4 via `TransactionalEventListener(AFTER_COMMIT) + @Async` so it runs only after DB commit:
```kotlin
@Transactional
fun update(id: Long, v: String) {
    redis.del("k:$id")
    repo.update(id, v)
    publisher.publishEvent(CacheInvalidate(id))
}
@TransactionalEventListener(phase = AFTER_COMMIT)
@Async
fun onInvalidate(e: CacheInvalidate) {
    Thread.sleep(800)
    redis.del("k:${e.id}")
}
```

**Transactional outbox + Kafka (the "real" solution).** App writes business state and an event row into an `outbox` table in the *same* DB transaction. A separate process (poller or Debezium CDC) reads outbox and publishes to Kafka. Consumers invalidate caches.

This reduces dual-write to a single ACID transaction (DB + DB). Eventual consistency between DB and cache is bounded by CDC pipeline lag — typically 100ms to a few seconds.

```
┌──────────┐  TX   ┌───────────┐   binlog/WAL   ┌──────────┐    ┌───────┐    ┌──────────────┐
│ Service  │───────► Aurora    │────────────────► Debezium │────► Kafka │────► Cache invalid │
│          │       │  - orders │                └──────────┘    └───────┘    │   consumer   │
│          │       │  - outbox │                                              └──────┬───────┘
└──────────┘       └───────────┘                                                     │ DEL k
                                                                                     ▼
                                                                                   Redis
```

Use Debezium's [Outbox Event Router SMT](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html) to reshape outbox rows into proper Kafka messages. Use `aggregate_id` as the Kafka partition key to preserve per-entity order.

Toss Bank's article "캐시를 적용하기 까지의 험난한 길" describes a production version of this for their terms-agreement (약관) service: cache eviction tied to `@TransactionalEventListener(AFTER_COMMIT)` + Kafka events + Resilience4j circuit breaker around Redis.

**🎯 Deliverable.** `dual-write-lab`: implement all four naive strategies as separate services using Aurora MySQL (or local MySQL in Testcontainers) + Redis. Use coordinated `CountDownLatch` and `Awaitility` to deterministically reproduce the race in each strategy via JUnit 5 integration tests. Then implement (a) delayed-double-delete via `TransactionalEventListener`, and (b) outbox + Debezium + Kafka + invalidator. Show via tests that (a) reduces but doesn't eliminate races, while (b) bounds staleness to CDC lag (and write up the trade-offs).

**Reading.**
- 📜 Microsoft — Cache-Aside pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside
- 📜 Confluent — The Dual-Write Problem: https://www.confluent.io/blog/dual-write-problem/
- 📜 Chris Richardson — Transactional Outbox: https://microservices.io/patterns/data/transactional-outbox.html
- 📜 Debezium Outbox Event Router: https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html
- 🇰🇷 Toss Bank — 캐시를 적용하기 까지의 험난한 길: https://toss.tech/article/34481
- 🇰🇷 Toss — 대규모 CDC Pipeline (Debezium 운영 여정): https://toss.tech/article/cdc_pipeline
- gajabagi — Caching deep dive on race conditions: https://gajabagi.medium.com/caching-part-1-a-deep-dive-into-sync-race-conditions-and-the-timeline-fallacy-41cb10bbffe8
- aleksk1ng — Outbox pattern with Spring + Kotlin: https://dev.to/aleksk1ng/transactional-outbox-pattern-step-by-step-with-spring-and-kotlin-3gkd

**Self-test.** Walk through Strategy 4's race condition in a sequence diagram on a whiteboard, naming each thread's actions and the exact moment cache and DB diverge. Why does outbox+CDC fix the race that delayed-double-delete only mitigates?

---

### Week 10 — Replica lag, distributed locks, fencing tokens, Hibernate L2

**Goals.** Recognize Aurora replica-lag-poisons-cache patterns. Know Kleppmann's critique of Redlock and why it matters. Decide between Hibernate L2 cache and Spring Cache.

**Deep content.**

**Aurora replica lag + cache.** Aurora's replication is shared-storage-based and typically <100ms within region; cross-region binlog replication is <1s typical, multi-second under load. The pernicious bug:
```
1. Writer: UPDATE order SET status='SHIPPED'
2. Reader (replica, 200ms behind): SELECT status → 'PENDING'
3. App: SET cache:order:1 = 'PENDING'
4. TTL = 10 min → cache poisoned for 10 minutes
```
Mitigations: read-your-writes routing (mark `lastWriteAt` per session, route subsequent reads to writer if `now - lastWriteAt < replicaLagBudget`), Aurora's `aurora_replica_read_consistency = SESSION | GLOBAL` (readers wait for replica catch-up), version tokens in cache (LinkedIn's SCN approach — see case studies), or simply don't cache reads from replicas immediately after a write.

The Woowahan "누군가에게는 빼빼로데이" post (2016) is a perfect case study: Pepero Day promo built a participation counter on Redis master + 2 replicas; counter incremented on master, *read from replicas*. Replication lag let participants pass through the limit → over-allocated prizes. Lesson: counter-style hot reads must hit the master.

**Distributed locks for cache rebuild.**

*Single-instance Redis lock (efficiency):*
```
SET lock:k <uuid> NX PX 5000
... do work ...
EVAL "if redis.call('get',KEYS[1])==ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end" 1 lock:k <uuid>
```
Atomic CAS release. **Good enough for cache rebuild** where occasional double-execution is just wasted DB work.

*Redlock (multi-master Redis):* acquire on majority of N independent masters within a timeout. Salvatore Sanfilippo's algorithm.

*Kleppmann's critique* (mandatory reading): (1) no fencing tokens — random UUIDs aren't monotonic, you can't safely reject a "zombie" client's write; (2) timing assumptions — Redlock assumes bounded clock drift, network delay, and process pauses; in practice JVM GC pauses can exceed lock TTL → two clients believe they hold the lock simultaneously. **Recommendation**: for *efficiency* locks (cache rebuild), single-Redis `SET NX EX` is fine. For *correctness* locks, use ZooKeeper/etcd/Consul (which provide fencing via `zxid`/revision) and enforce fencing token checks at the resource.

*Redisson RLock*: built on single-instance Redis (or `RedissonRedLock`). Watchdog auto-renews the lease every 10s; explicit `leaseTime` disables watchdog. Reentrant. Inherits all of Kleppmann's concerns — use for efficiency, not correctness.

Kurly's blog (helloworld.kurly.com) describes their Redisson-based AOP annotation lock for the WMS receiving service. They explicitly chose Redisson over plain Lettuce *"because Redisson uses Pub/Sub instead of spinlock, supports timeouts natively."*

**Hibernate L2 cache vs Spring Cache.** Different tools for different problems.

| | Hibernate 2LC | Spring `@Cacheable` |
|---|---|---|
| What | Entity hydrated state, collections, queries | Arbitrary method returns |
| Invalidation | Automatic via persistence context | Manual |
| Concurrency | `READ_ONLY`, `NONSTRICT_READ_WRITE`, `READ_WRITE`, `TRANSACTIONAL` | None |
| Best for | Read-mostly entities by id | Computed/aggregated/projection data |

Vlad's recommendation for an Aurora+Redis stack: `READ_WRITE` with optimistic `@Version` on entities — even if the cache returns stale, optimistic checks reject stale writes. **Avoid Hibernate query cache** — it caches just IDs; missing entries in the entity region cause N+1 queries; any DML on the table invalidates *all* query-cache entries for that table.

**The "cache JPA entities" footgun.** Don't. `LazyInitializationException` on the *second* call (which returns from cache), Hibernate-proxy serialization issues, identity-equality breakage on `merge`. Always cache DTOs or projections.

**🎯 Deliverable — Phase 4 capstone.** `replica-lag-defense`: Spring Boot 3 service connected to a 2-node MySQL Group Replication setup (or Aurora local emulator) with one writer + one lagging reader. Implement four cache strategies: (1) baseline (read replica → set cache); (2) read-your-writes routing via cookie; (3) version-token guard in cache (write rejects older versions); (4) Redisson `RLock` around cache rebuild. Run a chaos test that injects 1s replica lag during 100 writes and measure cache staleness windows for each strategy.

**Reading.**
- 📜 Martin Kleppmann — How to do distributed locking (Redlock critique): https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
- 📜 Antirez rebuttal — Is Redlock safe?: https://antirez.com/news/101
- 📜 Vlad Mihalcea — JPA/Hibernate 2LC: https://vladmihalcea.com/jpa-hibernate-second-level-cache/
- 📜 Vlad Mihalcea — Query cache N+1: https://vladmihalcea.com/hibernate-query-cache-n-plus-1-issue/
- 📜 Aurora replication: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Replication.html
- 🇰🇷 Kurly — Spring Redisson 분산락: https://helloworld.kurly.com/blog/distributed-redisson-lock/
- 🇰🇷 Woowahan — 누군가에게는 빼빼로데이 (replica lag incident): https://woowabros.github.io/experience/2016/11/28/woowahan_4one_event.html
- 🇰🇷 Hyperconnect — 레디스와 분산 락: https://hyperconnect.github.io/2019/11/15/redis-distributed-lock-1.html
- 🇰🇷 Woowahan — WMS 재고 이관을 위한 분산 락: https://techblog.woowahan.com/17416/

**Self-test.** Why are random UUIDs unsafe as lock identities for correctness-critical operations? In a service where Aurora replica lag is bounded by 500ms and the cache TTL is 10 minutes, what's the worst-case staleness window without any read-your-writes routing?

---

## Phase 5 — Observability and ops (Week 11)

### Week 11 — Metrics, hot-key detection, Lettuce tuning, HA

**Goals.** Wire Micrometer metrics correctly for both Caffeine and Redis (knowing the gotchas). Detect hot keys and big keys safely in production. Tune Lettuce for cluster topology refresh and connection pooling. Pick between Sentinel and Cluster modes.

**Deep content.**

**Micrometer metrics.** `CacheMeterBinder<C>` is the abstract base; built-in subclasses are `CaffeineCacheMetrics`, `RedisCacheMetrics`, etc. Spring Boot binds *only caches that exist at startup* — caches created on the fly (or `RedisTemplate`-driven keys) are not auto-instrumented; register them with `CacheMetricsRegistrar` or wrap them manually.

Standard meters:
- `cache.gets` (counter, tags `cache`, `cacheManager`, `result=hit|miss`) — hit ratio derived as `rate(cache_gets_total{result="hit"}) / rate(cache_gets_total)`.
- `cache.puts` (counter)
- `cache.evictions` (counter; Caffeine adds `cause=SIZE|EXPIRED|EXPLICIT|REPLACED|COLLECTED`)
- `cache.size` (gauge)
- `cache.load`, `cache.load.duration` (Caffeine only)

**Redis gotcha — statistics are off by default.** `RedisCache` does not record `CacheStatistics` unless you call `.enableStatistics()` on `RedisCacheManagerBuilder`, or set `spring.cache.redis.enable-statistics=true`. If you bypass `RedisCacheManager` and use `RedisTemplate.opsForValue().get(...)` directly, there is no `RedisCache` and `enable-statistics` has zero effect — instrument manually with `Timer`/`Counter` or use Lettuce's `MicrometerCommandLatencyRecorder`.

**Hot key detection.**
- `redis-cli --hotkeys`: requires `maxmemory-policy=*-lfu`. Caps output at 16 hot keys. Per-key probe: `OBJECT FREQ key` (0–255 logarithmic counter).
- `redis-cli --bigkeys`: SCAN-based, non-blocking, top largest per type.
- **`MONITOR` — DON'T in production.** Throughput drops >50%, latency spikes, can starve real clients. Dev/replica only.
- Cluster-mode-enabled caveat: connect to *each primary node endpoint* — running against the configuration endpoint produces `MOVED` errors.
- Production-friendly: client-side instrumentation (timed/tagged by key *prefix*, never full key — high cardinality), Slowlog (`SLOWLOG GET 128`), Latency monitor (`LATENCY DOCTOR`).

**Hot key mitigation.** Local L1 cache in front of Redis is the most effective — even a 1-second Caffeine TTL crushes Redis QPS by >100× on a hot key. Other techniques: key splitting (`hot:counter:{shard0..15}`, write random shard, read SUMs all), read fan-out to replicas (Lettuce `ReadFrom.REPLICA_PREFERRED`), request coalescing.

**Lettuce vs Jedis.** Boot defaults to Lettuce since 2.0. Reasons: Netty-based non-blocking I/O, single thread-safe connection (no pool overhead), reactive support, native cluster topology refresh.

When to add a Lettuce pool: blocking commands (`BLPOP`, `XREAD BLOCK`), `MULTI/EXEC` transactions, very high concurrency triggering `LettuceFutures.awaitOrCancel` blocking. Add `commons-pool2` and:
```yaml
spring.data.redis.lettuce:
  pool: { enabled: true, max-active: 16, max-idle: 8, min-idle: 2, max-wait: 200ms }
  cluster.refresh: { adaptive: true, period: 30s, dynamic-refresh-sources: true }
```

**Cluster topology refresh.** Two modes: periodic (background `CLUSTER NODES`/`CLUSTER SLOTS` every N seconds) and adaptive (refresh on `MOVED_REDIRECT`, `ASK_REDIRECT`, `PERSISTENT_RECONNECTS`, `UNCOVERED_SLOT`, `UNKNOWN_NODE`; rate-limited by `adaptiveRefreshTriggersTimeout`). On AWS ElastiCache: enable adaptive triggers, set JVM DNS TTL to 5–10s (`networkaddress.cache.ttl=5`), set `validateClusterNodeMembership=false` because failover may rotate IPs.

**Sentinel vs Cluster vs MemoryDB.**
| | Sentinel | Cluster | MemoryDB |
|---|---|---|---|
| Sharding | No (single primary) | Yes (16384 hash slots) | Yes |
| Failover detection | 10–30s typical | Gossip-driven, faster | <20s unplanned, <200ms planned |
| Multi-key ops | Full | Hash-tag–constrained, `CROSSSLOT` errors | Full |
| Durability | Async replication | Async replication | **Multi-AZ transaction log, zero data loss** |
| Use as primary DB? | No | No | **Yes** |

Hash tags constrain colocation: `{user:42}:profile` and `{user:42}:cart` both hash on `user:42` → same slot, supports `MGET`/`MULTI`/Lua across them. Caveat: overuse creates skewed slots and hot shards.

**Resilience4j around cache reads.** Treat Redis as a remote dependency. Combine `CircuitBreaker` + `TimeLimiter` (150–200ms on cache) + `Bulkhead`. On open circuit, fall through to DB.

**Memory pressure on Redis.** `INFO memory`:
- `used_memory_rss / used_memory` (`mem_fragmentation_ratio`): 1.0–1.5 healthy; >1.5 → `activedefrag yes`; <1.0 → swapping (very bad).
- `evicted_keys` from `INFO stats`: should be 0 unless intentional. Alert on `rate(evicted_keys[5m]) > 0`.

**🎯 Deliverable.** Take the multi-tier cache from Phase 3 and add: (1) Caffeine + Redis Micrometer metrics with `enableStatistics()`, (2) Grafana dashboard JSON with hit ratio, eviction rate, p99 lookup latency for L1 and L2, (3) a synthetic hot-key generator + a sidecar process running `redis-cli --hotkeys` periodically and exporting top-N to Prometheus, (4) Resilience4j circuit-breaker on Redis with chaos test killing Redis mid-traffic.

**Reading.**
- 📜 Spring Boot Actuator metrics: https://docs.spring.io/spring-boot/reference/actuator/metrics.html
- 📜 Spring Data Redis observability: https://docs.spring.io/spring-data/redis/reference/observability.html
- 📜 ElastiCache Lettuce best practices: https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/BestPractices.Clients-lettuce.html
- 📜 MemoryDB FAQ: https://aws.amazon.com/memorydb/faqs/
- 🇰🇷 Woowahan — Redis New Connection 증가 이슈: https://techblog.woowahan.com/23121/
- 🇰🇷 Woowahan — 스토리지 최적의 스펙 관리 시스템 (cost optimization, ~50% savings): https://techblog.woowahan.com/13539/
- 🇰🇷 NHN Cloud — Redis Cluster + Spring Boot Lettuce 설정: https://meetup.nhncloud.com/posts/379

**Self-test.** Why does `spring.cache.redis.enable-statistics=true` not produce metrics for code that uses `RedisTemplate.opsForValue().get()`? When does `MONITOR` actually make sense (briefly)?

---

## Phase 6 — Advanced topics (Week 12)

### Week 12 — Schema migration, multi-region, GDPR

**Goals.** Deploy a cache-schema change without taking downtime. Understand multi-region cache replication options. Comply with GDPR right-to-erasure on cached data.

**Deep content.**

**Cache versioning / zero-downtime schema migration.** Problem: deploy v2 of `UserViewDTO` (renamed `displayName` → `name`) while v1 pods still read from Redis values written by v2 → `SerializationException`. Use multiple defenses:

1. **Version-prefixed keys** (most robust):
```kotlin
@Bean
fun redisCacheConfig(buildProps: BuildProperties): RedisCacheConfiguration {
    val schemaVersion = buildProps.get("cache.schema.version") ?: "v2"
    return RedisCacheConfiguration.defaultCacheConfig()
        .computePrefixWith { "${schemaVersion}:${it}::" }
        .entryTtl(Duration.ofHours(1))
        .serializeValuesWith(SerializationPair.fromSerializer(GenericJackson2JsonRedisSerializer()))
}
```
Keys become `v2:users::42`. Old `v1:users::42` keys stay until TTL. Each schema bump = global cold cache for that namespace.

2. **Schema-tolerant serializers**:
```kotlin
@JsonIgnoreProperties(ignoreUnknown = true)
data class UserViewDTO(
    val id: Long,
    val email: String,
    val name: String,          // was displayName in v1
    val plan: String? = null,  // additive-only with default
)
```
Always Jackson, never JDK serialization. Make all changes additive — only add nullable fields with defaults. Removing/renaming requires a key version bump.

3. **Parallel namespaces during deploy**: v1 and v2 readers/writers run concurrently against the same Redis but with different prefixes. Once v2 is fully rolled out, evict v1 namespace via `SCAN` + `UNLINK` (async delete avoids blocking).

The Woowahan techblog #22767 article on Java records + `GenericJackson2JsonRedisSerializer` is a perfect cautionary tale: deserialization failure manifests on the *second* request only — once the cache is populated and you start reading from it. Always include integration tests that hit the cache twice.

**Multi-region cache replication.**

| Pattern | Read latency | Write latency | Consistency |
|---|---|---|---|
| Single-region | Local | Local | Strong (primary) |
| ElastiCache Global Datastore (active-passive) | Local read replicas | Cross-region hop | Eventual ~1s on secondaries |
| MemoryDB Multi-Region (active-active) | Local microseconds | Local single-digit ms | Per-key eventual; durable in each region |
| Kafka-async app-level | Local | Local | Eventual (Kafka lag) |
| Synchronous dual-write | Local | max(regions) | Strong but fragile |

Choose Global Datastore for read-heavy multi-region with bounded staleness. Choose MemoryDB Multi-Region when you need both low latency and multi-region writes (gaming leaderboards, multi-region session). For app-level: write to local Redis + publish a `cache.invalidate` event to a global Kafka topic; consumers in each region apply locally.

**GDPR/PII in caches.**
- TTL ≤ 24h aligns with right-to-erasure (Art. 17, ~30-day SLA) — caches purge naturally.
- Encryption: ElastiCache `at_rest_encryption_enabled = true` (KMS), `transit_encryption_enabled = true` (TLS); Lettuce `RedisURI.builder().withSsl(true).withVerifyPeer(true)`.
- **Never log PII.** Spring Cache TRACE emits computed cache keys — `logging.level.org.springframework.cache.interceptor=WARN` in prod. Spring Data Redis verbose logging off too.
- On `UserDeletedEvent`, evict from every cache namespace touching the user; use Redis `SCAN` + `UNLINK` for pattern deletes.
- For PII fields accessed rarely, **don't cache them** — fetch direct from DB with column-level encryption. If you must, prefer Caffeine in-process (vanishes on pod death) over Redis (network, snapshots, replication).

**🎯 Deliverable.** Take the Phase 4 capstone and: (1) add a build-time `cache.schema.version` injected via `BuildProperties` and version-prefix all keys; (2) deploy a v1 → v2 schema change in a green/blue manner using Testcontainers + a JUnit harness simulating a rolling update; (3) implement a `GdprCacheEvictor` that listens on a Kafka `UserDeleted` topic and evicts all known namespaces; (4) write a `CACHE_OPS.md` runbook explaining how to rotate the schema version and perform a controlled cold-start.

**Reading.**
- 🇰🇷 Woowahan — `@Cacheable` + Java record 직렬화 오류: https://techblog.woowahan.com/22767/
- dev.to — Versioning Redis keys for Spring Boot deploys: https://dev.to/ibrahimgunduz34/versioning-redis-cache-keys-to-prevent-stale-data-during-spring-boot-deployments-1d8e
- 📜 ElastiCache Global Datastore: https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Redis-Global-Datastore.html
- 📜 Werner Vogels — MemoryDB design: https://www.allthingsdistributed.com/2021/11/amazon-memorydb-for-redis-speed-consistency.html

**Self-test.** A teammate proposes solving cache-schema drift with Jackson `@JsonIgnoreProperties(ignoreUnknown = true)` alone, no key versioning. Give two failure cases this leaves open.

---

## Phase 7 — Capstone integration project (concurrent with Weeks 11–12, ~30 hours)

**🎯 The capstone.** `gwk-cache-mastery`: a production-grade demo service combining everything.

**Spec.**
- Kotlin 2.x + Spring Boot 3.x. Aurora MySQL (or MySQL 8 in Testcontainers). Redis (Valkey 8) on ElastiCache or local. Kafka via `confluentinc/cp-kafka`. Debezium MySQL connector. EKS deployment via Helm chart (or `k3d` for local).
- Domain: a product catalog API with `/products/{id}`, `/products/search?q=...`, `/products` (admin write). Read 50k RPS target, write 500 RPS.
- Cache architecture: Caffeine L1 (`maximumSize=10_000`, `refreshAfterWrite=1m`, `expireAfterWrite=5m`) + Redis L2 (`time-to-live=15m`, `enable-statistics=true`, version-prefixed keys, `GenericJackson2JsonRedisSerializer`).
- Cross-instance L1 invalidation: Kafka topic `cache.invalidations` with consumer per pod (unique group ID). Backstop: short L1 TTL.
- Write path: outbox pattern. Service writes product update + outbox row in same DB transaction. Debezium → Kafka → cache invalidator consumer → publishes to `cache.invalidations`.
- Stampede protection: Redisson `RLock` around L2 cache rebuild for hot keys; PER on top-100 product entries.
- Resilience4j circuit breaker around L2; on open circuit, fall through directly to DB.
- Observability: Caffeine + Redis Micrometer metrics, Grafana dashboard with hit ratio, p99 lookup, eviction rate per cause, Redis fragmentation ratio. Alert rules on hit ratio < 0.85 for >5min, eviction-by-SIZE rate >100/s.
- Chaos tests: kill Redis mid-load, kill one pod, simulate 500ms Aurora replica lag, push schema version v1 → v2 with key reprefixing.
- Documentation: `ARCHITECTURE.md` with sequence diagrams, `INCIDENT_RUNBOOK.md` covering hot-key, cache penetration, avalanche, Redis OOM, cache-schema rollback. `TRADEOFFS.md` listing every architectural decision with the rejected alternatives and why.

The capstone repo is your portfolio piece — link it in your CV.

---

## Reference appendix: must-read resources

### Books and papers

- 📜 Kleppmann, *Designing Data-Intensive Applications* — Ch 5 (Replication), 7 (Transactions), 9 (Consistency & Consensus). Caching is derived data; the dual-write problem is the database/index sync problem.
- 📜 *Scaling Memcache at Facebook* (NSDI 2013): https://www.usenix.org/system/files/conference/nsdi13/nsdi13-final170_update.pdf — leases, gutter pool, regional pools, cold-cluster warmup.
- 📜 Einziger, Friedman, Manes, *TinyLFU: A Highly Efficient Cache Admission Policy* (ACM TOS 2017): https://dl.acm.org/doi/10.1145/3149371

### Spring source code (read in order)

- `spring-context/.../cache/Cache.java`, `CacheManager.java`
- `spring-context/.../cache/interceptor/CacheAspectSupport.java` (the heart)
- `spring-context/.../cache/interceptor/CacheInterceptor.java`
- `spring-context/.../cache/annotation/SpringCacheAnnotationParser.java`
- `spring-context/.../cache/interceptor/SimpleKeyGenerator.java`, `CacheEvaluationContext.java`
- `spring-context/.../cache/support/AbstractValueAdaptingCache.java`, `NullValue.java`
- `spring-boot-autoconfigure/.../cache/CacheAutoConfiguration.java`

### Korean engineering blogs (organized by topic)

| Topic | Best article |
|---|---|
| Cache stampede / PER | Toss 캐시 문제 해결 가이드 — https://toss.tech/article/cache-traffic-tip |
| Lua + cache stampede | LINE — https://engineering.linecorp.com/en/blog/redis-lua-scripting-atomic-processing-cache/ |
| PER implementation | Hwahae — https://blog.hwahae.co.kr/all/tech/14003 |
| Distributed lock (Redisson) | Kurly — https://helloworld.kurly.com/blog/distributed-redisson-lock/ |
| Distributed lock internals | Hyperconnect — https://hyperconnect.github.io/2019/11/15/redis-distributed-lock-1.html |
| Strong-consistency cache | Toss Bank — https://toss.tech/article/34481 |
| L1+L2 (Caffeine + Redis) | Olive Young — https://oliveyoung.tech/2024-12-10/present-promotion-multi-layer-cache/ |
| Local cache + pub/sub | Kakao Pay — https://tech.kakaopay.com/post/local-caching-in-distributed-systems/ |
| 3-tier reactive cache | Woowahan — https://woowabros.github.io/experience/2020/02/19/introduce-shop-display.html |
| Pub/Sub + batch fallback | SK Devocean — https://devocean.sk.com/blog/techBoardDetail.do?ID=167203 |
| Redis Client-Side Caching | SK Devocean — https://devocean.sk.com/blog/techBoardDetail.do?ID=167301 |
| Redis on K8s | Kakao — https://tech.kakao.com/2022/02/09/k8s-redis/ |
| Cache farm migration | Kakao — https://tech.kakao.com/2020/11/10/if-kakao-2020-commentary-01-kakao/ |
| Redis-as-a-Service on K8s | Kakao Pay Securities — https://tech.kakaopay.com/post/kakaopaysec-redis-on-kubernetes/ |
| CDC pipeline (Debezium) | Toss — https://toss.tech/article/cdc_pipeline |
| Replica-lag incident | Woowahan (2016) — https://woowabros.github.io/experience/2016/11/28/woowahan_4one_event.html |
| `@Cacheable` + Java record bug | Woowahan — https://techblog.woowahan.com/22767/ |
| Lettuce connection storms | Woowahan — https://techblog.woowahan.com/23121/ |
| Cost optimization | Woowahan — https://techblog.woowahan.com/13539/ |
| Local cache choice | LG U+ — https://medium.com/uplusdevu/로컬-캐시-선택하기-e394202d5c87 |

**Honest gaps:** I could not verify Coupang or Daangn-specific cache architecture deep-dives during research; their public engineering blogs focus elsewhere. The "지연된 이중 삭제" (delayed double delete) pattern is more commonly written up in Chinese (Alibaba) tech blogs than Korean ones — Toss Bank's `AFTER_COMMIT` + Kafka pattern is the closest Korean equivalent. For DEVIEW/if-Kakao YouTube talks (e.g., the if(kakaoAI) 2024 선물하기 caching session), search the conference's official YouTube channels directly — I could not retrieve verified URLs in research.

### Global engineering blogs (case studies)

- Netflix EVCache — https://netflixtechblog.com/caching-for-a-global-netflix-7bcc457012f1, https://netflixtechblog.com/ephemeral-volatile-caching-in-the-cloud-8eba7b124589
- Twitter Pelikan — https://pelikan.io/, https://github.com/twitter/pelikan
- Discord trillions of messages — https://discord.com/blog/how-discord-stores-trillions-of-messages
- Slack Flannel — https://slack.engineering/flannel-an-application-level-edge-cache-to-make-slack-scale/
- Stack Overflow — Nick Craver — https://nickcraver.com/blog/2019/08/06/stack-overflow-how-we-do-app-caching/
- LinkedIn profile caching (SCN fencing) — https://www.linkedin.com/blog/engineering/data-management/upscaling-profile-datastore-while-reducing-costs
- Shopify IdentityCache — https://shopify.engineering/identitycache-improving-performance-one-cached-model-at-a-time
- Vlad Mihalcea on Hibernate caching — https://vladmihalcea.com/jpa-hibernate-second-level-cache/

### Conference talks (search and verify)

- *What's new in Spring Framework 6.1* (Juergen Hoeller / Stéphane Nicoll, SpringOne 2023) — covers reactive cache adaptation.
- Sébastien Deleuze, *Reactive Spring with Kotlin Coroutines* (KotlinConf / Spring I/O) — coroutine ↔ Reactor bridging.
- Search SpringOne YouTube channel for *Caffeine* and *Spring Cache* tags; KotlinConf for *coroutines + Spring*; if(kakaoAI) 2024 catalog for the 선물하기 service caching strategy talk.

---

## Closing principles (the 80/20 of cache mastery)

A few invariants I would internalize even before completing all 12 weeks:

**Read the contract before the annotation.** Every footgun in this curriculum — null-vs-miss confusion, sync=true single-JVM scope, reactive `Mono` caching, suspend-function `Continuation` leak — comes from misunderstanding what `Cache`, `CacheManager`, and `CacheAspectSupport` actually promise. Read the Javadoc twice.

**There is no strongly consistent algorithm using only DB + cache.** Pick one of: bounded staleness (TTL + eventual), strong eventual via outbox+CDC, or strong-per-entity via Hibernate L2 with `@Version`. Anything else is a race waiting to manifest in production at 2am.

**Optimize L1 hit rate before changing L2 engine.** Caffeine in front of Redis routinely produces 100× latency improvements; switching Redis → DragonflyDB rarely produces 2×.

**Treat cache as a remote dependency.** Circuit breakers, fallbacks, timeouts. Cache failure must never fail the request.

**Caches multiply your data surface area.** GDPR, schema migration, multi-region — every cache copy is another place state can drift, leak, or break. Cache *less than you think you need*.

**Most production cache incidents have already been written up — in Korean.** The Toss, Kakao, Woowahan, Kurly, and SK Devocean blogs cover failure modes you will encounter, often in more concrete detail than English-language sources. Read them.

By the end of Week 12 you should be the engineer your team turns to for cache-design reviews — not because you memorized annotations, but because you understand the framework's mechanics, the algorithms underneath, the production failure modes, and the trade-offs between every available alternative.