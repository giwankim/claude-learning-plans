---
title: "Spring Boot 3 + Kotlin 2 + Redis 7/8 — An Implementation Guide"
category: "Spring & Spring Boot"
description: "Side-by-side Lettuce vs. Redisson implementation guide for Spring Boot 3 + Kotlin 2 + Redis 7/8, with coroutines, WebFlux, and production patterns (caching, locks, streams, pub/sub)."
---

# Spring Boot 3 + Kotlin 2 + Redis 7/8 — An Implementation Guide
### Lettuce vs. Redisson, side by side, with coroutines and WebFlux

## TL;DR

- **Use Lettuce + Spring Data Redis** (the Spring Boot default, configured via `spring.data.redis.*`) as your baseline: it gives you `RedisTemplate`, `ReactiveRedisTemplate`, `RedisCacheManager`, `StreamMessageListenerContainer`, Spring Session, repositories, and full Reactor/coroutine integration with zero extra dependencies. It is a low-level, command-oriented client.
- **Add Redisson** (`redisson-spring-boot-starter`) when you need higher-level distributed primitives — `RLock`, `RFairLock`, `RReadWriteLock`, `RFencedLock`, `RSemaphore`, `RCountDownLatch`, `RRateLimiter`, `RBloomFilter`, `RShardedTopic`, `RReliableTopic`, near-cache-backed `RedissonSpringCacheManager` — that you would otherwise hand-roll on top of Lua scripts. It is a data-grid-style abstraction.
- **Mixing both in one app is normal and recommended**: keep Lettuce as the `RedisConnectionFactory` powering `RedisTemplate`, Spring Cache and Spring Session; use Redisson alongside it through its own `RedissonClient` bean for locks/rate limiting/distributed objects. The two clients open separate connection pools, so size them accordingly. For coroutines, prefer `RedissonReactiveClient` with explicit `threadId`s — never call blocking `RLock.lock()` from a `suspend` function.

---

## Key Findings

This guide walks through, in order, project setup, `RedisTemplate`, Redisson basics, Spring Cache, distributed locks, rate limiting, Pub/Sub, Streams, Spring Session, repositories, coroutines, WebFlux, testing with Testcontainers, production gotchas, and a final decision matrix. Every major topic shows the **vanilla blocking** path first, then **coroutines**, then **reactive WebFlux**, and where applicable the **Lettuce vs. Redisson** code side by side.

The dependency baseline assumed throughout is Spring Boot **3.3+/3.5**, Kotlin **2.x**, JVM 21, Redis **7.2+** (or Redis 8 / Valkey 8 — the API surface used here is identical), Lettuce shipped by Spring Data Redis 4.x, and Redisson **3.50+** (or 4.x). Property names use the Spring Boot 3 prefix `spring.data.redis.*`; the legacy `spring.redis.*` is no longer recognized.

---

## Details

### 1. Project setup

#### `build.gradle.kts`

```kotlin
plugins {
    kotlin("jvm") version "2.1.0"
    kotlin("plugin.spring") version "2.1.0"
    id("org.springframework.boot") version "3.3.5"
    id("io.spring.dependency-management") version "1.1.6"
}

dependencies {
    // --- Spring Data Redis (Lettuce by default) ---------------------------
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.springframework.boot:spring-boot-starter-data-redis-reactive")
    implementation("org.apache.commons:commons-pool2")          // required for Lettuce pooling

    // --- Spring Cache abstraction + L1 (Caffeine) ------------------------
    implementation("org.springframework.boot:spring-boot-starter-cache")
    implementation("com.github.ben-manes.caffeine:caffeine")

    // --- Redisson (higher-level Redis objects) ---------------------------
    // Pulls in spring-boot-starter-data-redis transitively.
    implementation("org.redisson:redisson-spring-boot-starter:3.50.0")

    // --- Web layer -------------------------------------------------------
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-webflux")

    // --- Coroutines -------------------------------------------------------
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-reactor")  // awaitSingle, asFlow, ReactorContext

    // --- Kotlin Jackson module (critical for data-class serialization) ---
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")

    // --- Spring Session --------------------------------------------------
    implementation("org.springframework.session:spring-session-data-redis")

    // --- Bucket4j (alternative rate limiting) ----------------------------
    implementation("com.bucket4j:bucket4j-redis:8.10.1")

    // --- Redis OM Spring (full-text/secondary index search) --------------
    implementation("com.redis.om:redis-om-spring:0.9.7")

    // --- Test ------------------------------------------------------------
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("io.projectreactor:reactor-test")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test")
    testImplementation("org.testcontainers:testcontainers:1.20.4")
    testImplementation("org.testcontainers:junit-jupiter:1.20.4")
    testImplementation("com.redis:testcontainers-redis:2.2.2")
}
```

> Note: `redisson-spring-boot-starter` already depends on `spring-boot-starter-data-redis` and brings the `redisson-spring-data-3X` adapter that wires Redisson behind a `RedisConnectionFactory`. If you want **two parallel clients** (Lettuce for `RedisTemplate`/cache, Redisson for locks), set `spring.data.redis.client-type=lettuce` in YAML and Redisson's auto-configuration will create only its own `RedissonClient` bean without replacing the Lettuce factory. If you want Redisson to back `RedisTemplate` as well, omit that property.

#### `application.yml` — Lettuce

```yaml
spring:
  data:
    redis:
      # --- Single node ---
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
      username: ${REDIS_USER:}
      password: ${REDIS_PASSWORD:}
      database: 0
      timeout: 2s            # command timeout
      connect-timeout: 1s
      client-name: ${spring.application.name}
      ssl:
        enabled: false
      lettuce:
        pool:
          enabled: true       # turn on commons-pool2; required if you use blocking commands
          max-active: 32      # tune to peak parallel blocking commands per instance
          max-idle: 16
          min-idle: 4
          max-wait: 500ms
        shutdown-timeout: 100ms
      # --- Sentinel (override host/port with the block below) ---
      # sentinel:
      #   master: mymaster
      #   nodes: sentinel-1:26379,sentinel-2:26379,sentinel-3:26379
      #   password: ${REDIS_SENTINEL_PASSWORD:}
      # --- Cluster (override host/port with the block below) ---
      # cluster:
      #   nodes:
      #     - clusterep-1.use1.cache.amazonaws.com:6379
      #     - clusterep-2.use1.cache.amazonaws.com:6379
      #   max-redirects: 3
      # lettuce:
      #   cluster:
      #     refresh:
      #       adaptive: true
      #       period: 30s
      #       dynamic-refresh-sources: true
```

Key notes: pool sizing needs to budget one connection per concurrent **blocking** command (`BLPOP`, `BRPOP`, `XREAD BLOCK`, `XREADGROUP BLOCK`). For everything else Lettuce multiplexes commands over a single TCP connection and you can leave pooling disabled.

#### `application.yml` — Redisson

Redisson reads either the `spring.redis.redisson.*` properties or, more flexibly, a separate YAML file. The fallback file is the recommended approach because Redisson's `Config` exposes orders of magnitude more options than Spring Boot's properties bind.

```yaml
spring:
  data:
    redis:
      redisson:
        file: classpath:redisson.yaml
```

`src/main/resources/redisson.yaml` (single):

```yaml
singleServerConfig:
  address: "redis://${REDIS_HOST:localhost}:${REDIS_PORT:-6379}"
  password: ${REDIS_PASSWORD:}
  database: 0
  connectTimeout: 1000
  timeout: 2000
  retryAttempts: 3
  retryInterval: 200
  connectionMinimumIdleSize: 8
  connectionPoolSize: 64
  subscriptionConnectionMinimumIdleSize: 1
  subscriptionConnectionPoolSize: 50
  clientName: ${spring.application.name}
threads: 0           # 0 = #cpu * 2
nettyThreads: 0
codec: !<org.redisson.codec.JsonJacksonCodec> {}
lockWatchdogTimeout: 30000
```

Cluster variant of `redisson.yaml`:

```yaml
clusterServersConfig:
  nodeAddresses:
    - "redis://clusterep-1.use1.cache.amazonaws.com:6379"
    - "redis://clusterep-2.use1.cache.amazonaws.com:6379"
  scanInterval: 5000
  readMode: "MASTER"             # or SLAVE / MASTER_SLAVE
  subscriptionMode: "SLAVE"
  masterConnectionMinimumIdleSize: 8
  masterConnectionPoolSize: 64
  slaveConnectionMinimumIdleSize: 8
  slaveConnectionPoolSize: 64
  password: ${REDIS_PASSWORD:}
codec: !<org.redisson.codec.Kryo5Codec> {}
```

Sentinel variant:

```yaml
sentinelServersConfig:
  masterName: "mymaster"
  sentinelAddresses:
    - "redis://sentinel-1:26379"
    - "redis://sentinel-2:26379"
    - "redis://sentinel-3:26379"
  database: 0
  readMode: "MASTER"
```

Variables follow shell syntax (`${VAR:-default}`), which makes Redisson's YAML 12-factor friendly without extra plumbing.

#### Mixing Lettuce and Redisson cleanly

The simplest production pattern is: **keep Lettuce wired as `RedisConnectionFactory`** so all of Spring Data Redis, Spring Cache and Spring Session work out of the box, then expose Redisson only as a separate `RedissonClient` bean for locking/rate-limiting/sharded pub-sub. To prevent Redisson's auto-configuration from replacing the Spring Data Redis connection factory, set:

```yaml
spring:
  data:
    redis:
      client-type: lettuce
```

Then the auto-configuration still wires `RedissonClient` (so you can `@Autowired` it), but `RedisTemplate` and `RedisCacheManager` continue to use Lettuce.

If you need **two unrelated Redis endpoints** (e.g. one shared cluster for cache and a dedicated cluster for locks), define beans manually:

```kotlin
@Configuration
class DualRedisConfig {

    @Bean(destroyMethod = "destroy")
    @Primary
    fun cacheConnectionFactory(): LettuceConnectionFactory =
        LettuceConnectionFactory(RedisStandaloneConfiguration("cache.example.com", 6379))
            .apply { afterPropertiesSet() }

    @Bean(destroyMethod = "shutdown")
    fun lockRedisson(): RedissonClient {
        val cfg = Config().apply {
            useSingleServer().address = "redis://locks.example.com:6379"
            codec = Kryo5Codec()
        }
        return Redisson.create(cfg)
    }
}
```

---

### 2. RedisTemplate / StringRedisTemplate

Spring Boot auto-creates a `StringRedisTemplate` and a `RedisTemplate<Any?, Any?>` whose default value serializer is `JdkSerializationRedisSerializer`. **That default is wrong for almost every Kotlin codebase.** Java serialization breaks the moment a data class moves between deployments, doesn't roundtrip Kotlin types like `kotlin.collections.LinkedHashMap` cleanly, and produces opaque binary keys/values that can't be inspected from `redis-cli`. Replace it with `GenericJackson2JsonRedisSerializer` configured with the Kotlin Jackson module.

#### LettuceConnectionFactory with custom client options

```kotlin
@Configuration
class LettuceConfig(private val props: RedisProperties) {

    @Bean(destroyMethod = "shutdown")
    fun clientResources(): ClientResources = DefaultClientResources.create()

    @Bean
    fun lettuceConnectionFactory(resources: ClientResources): LettuceConnectionFactory {
        val socketOptions = SocketOptions.builder()
            .connectTimeout(Duration.ofSeconds(1))
            .keepAlive(true)
            .build()

        val clientOptions = ClusterClientOptions.builder()
            .socketOptions(socketOptions)
            .timeoutOptions(TimeoutOptions.enabled(Duration.ofSeconds(2)))
            .topologyRefreshOptions(
                ClusterTopologyRefreshOptions.builder()
                    .enableAllAdaptiveRefreshTriggers()      // MOVED/ASK/PERSISTENT_RECONNECTS
                    .enablePeriodicRefresh(Duration.ofSeconds(30))
                    .dynamicRefreshSources(true)
                    .build()
            )
            .disconnectedBehavior(ClientOptions.DisconnectedBehavior.REJECT_COMMANDS)
            .build()

        val poolConfig = GenericObjectPoolConfig<Any>().apply {
            maxTotal = 32; maxIdle = 16; minIdle = 4
            setMaxWait(Duration.ofMillis(500))
        }

        val client = LettucePoolingClientConfiguration.builder()
            .clientResources(resources)
            .clientOptions(clientOptions)
            .commandTimeout(Duration.ofSeconds(2))
            .poolConfig(poolConfig)
            .readFrom(ReadFrom.REPLICA_PREFERRED)
            .build()

        val server = RedisStandaloneConfiguration(props.host, props.port).apply {
            password = RedisPassword.of(props.password.orEmpty())
        }
        return LettuceConnectionFactory(server, client).apply { afterPropertiesSet() }
    }
}
```

> **Jedis comparison (briefly).** Jedis is connection-per-thread; you can opt in by adding `redis.clients:jedis` and setting `spring.data.redis.client-type=jedis`. It's simpler to reason about for purely synchronous code, but it has no native reactive API and every `RedisTemplate` call borrows a connection from the pool, so pool sizing becomes a hot tuning parameter. Lettuce is preferred for any non-trivial workload; this guide will not show Jedis-specific code beyond this paragraph.

#### Kotlin-friendly `RedisTemplate` beans

```kotlin
@Configuration
class RedisTemplateConfig {

    private fun objectMapper(): ObjectMapper = JsonMapper.builder()
        .addModule(KotlinModule.Builder()
            .configure(KotlinFeature.NullToEmptyCollection, true)
            .configure(KotlinFeature.NullIsSameAsDefault, true)
            .build())
        .addModule(JavaTimeModule())
        .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
        // Required if you want Jackson to write @class headers so the
        // GenericJackson2JsonRedisSerializer can round-trip arbitrary types.
        .activateDefaultTyping(
            BasicPolymorphicTypeValidator.builder().allowIfBaseType(Any::class.java).build(),
            ObjectMapper.DefaultTyping.NON_FINAL,
            JsonTypeInfo.As.PROPERTY,
        )
        .build()

    @Bean
    fun jsonSerializer(): GenericJackson2JsonRedisSerializer =
        GenericJackson2JsonRedisSerializer(objectMapper())

    @Bean
    fun redisTemplate(
        cf: RedisConnectionFactory,
        json: GenericJackson2JsonRedisSerializer,
    ): RedisTemplate<String, Any> = RedisTemplate<String, Any>().apply {
        connectionFactory = cf
        keySerializer = StringRedisSerializer.UTF_8
        hashKeySerializer = StringRedisSerializer.UTF_8
        valueSerializer = json
        hashValueSerializer = json
        afterPropertiesSet()
    }

    /** Strongly typed template for a specific data class. */
    @Bean
    fun userTemplate(cf: RedisConnectionFactory): RedisTemplate<String, User> =
        RedisTemplate<String, User>().apply {
            connectionFactory = cf
            keySerializer = StringRedisSerializer.UTF_8
            valueSerializer = Jackson2JsonRedisSerializer(jacksonObjectMapper(), User::class.java)
            afterPropertiesSet()
        }
}

data class User(val id: String, val email: String, val createdAt: Instant)
```

#### Using the various ops surfaces

```kotlin
@Service
class RedisOpsExamples(private val tpl: RedisTemplate<String, Any>) {

    private inline fun <reified V> v() = tpl.opsForValue() as ValueOperations<String, V>

    fun valueOps(user: User) {
        tpl.opsForValue().set("user:${user.id}", user, Duration.ofMinutes(15))
        val fetched = tpl.opsForValue().get("user:${user.id}") as User?
    }

    fun hashOps(orderId: String, lineItems: Map<String, Int>) =
        tpl.opsForHash<String, Int>().putAll("order:$orderId:items", lineItems)

    fun listOps(jobId: String, payload: String) =
        tpl.opsForList().rightPush("queue:jobs", payload)

    fun setOps(tag: String, postId: String) =
        tpl.opsForSet().add("posts:tag:$tag", postId)

    fun zsetOps(boardId: String, score: Double, postId: String) =
        tpl.opsForZSet().add("leaderboard:$boardId", postId, score)

    fun geoOps(driverId: String, lon: Double, lat: Double) =
        tpl.opsForGeo().add("drivers:active", Point(lon, lat), driverId)
}
```

#### Pipelining and transactions

```kotlin
fun bulkLoad(rows: List<User>): List<Any> =
    tpl.executePipelined(object : SessionCallback<Any?> {
        override fun <K : Any?, V : Any?> execute(ops: RedisOperations<K, V>): Any? {
            @Suppress("UNCHECKED_CAST")
            val o = ops as RedisOperations<String, User>
            rows.forEach { o.opsForValue().set("user:${it.id}", it, Duration.ofHours(1)) }
            return null
        }
    })

fun atomicCounterUpdate(key: String): Long? = tpl.execute(object : SessionCallback<Long?> {
    override fun <K, V> execute(ops: RedisOperations<K, V>): Long? {
        ops.watch(listOf(key as K))
        val current = (ops.opsForValue().get(key as K) as? Number)?.toLong() ?: 0
        ops.multi()
        ops.opsForValue().set(key, (current + 1) as V)
        @Suppress("UNCHECKED_CAST")
        val result = ops.exec() as List<Any?>
        return (result.firstOrNull() as? Number)?.toLong()
    }
})
```

---

### 3. Redisson basics

Redisson exposes Redis as a Java collections / concurrency API. Once the starter is on the classpath you simply inject `RedissonClient`:

```kotlin
@Service
class RedissonExamples(private val redisson: RedissonClient) {

    fun bucket(): RBucket<User> = redisson.getBucket("user:42", JsonJacksonCodec.INSTANCE)

    fun map(): RMap<String, Order> = redisson.getMap("orders")

    fun list(): RList<String> = redisson.getList("queue:jobs")

    fun zset(): RScoredSortedSet<String> = redisson.getScoredSortedSet("leaderboard")

    fun atomic(): RAtomicLong = redisson.getAtomicLong("global:order:seq")

    fun geo(): RGeo<String> = redisson.getGeo("drivers:active")

    fun bloom(): RBloomFilter<String> = redisson.getBloomFilter("seen:emails").apply {
        tryInit(/* expectedInsertions = */ 10_000_000L, /* falsePositiveRate = */ 0.001)
    }
}
```

Reactive and RxJava clients are derived from the same instance:

```kotlin
val reactive: RedissonReactiveClient = redisson.reactive()
val rx: RedissonRxClient = redisson.rxJava()
```

#### Codec selection

Redisson lets you set a codec globally and override per object. The trade-offs:

- `JsonJacksonCodec` — human-readable, interoperable across languages, biggest footprint. Default. Configure with a Kotlin-aware `ObjectMapper` if you want clean round-tripping of data classes.
- `Kryo5Codec` — fastest and smallest for JVM-only workloads. Requires registering classes for stable serialization across versions.
- `MarshallingCodec` — based on JBoss Marshalling; good middle ground if you can't use Kryo.
- `TypedJsonJacksonCodec(Class<T>)` — when a key namespace stores exactly one type and you want to drop the Jackson `@class` polymorphic header.

```kotlin
@Configuration
class RedissonCodecConfig {
    @Bean
    fun kotlinAwareJackson(): JsonJacksonCodec {
        val mapper = jacksonObjectMapper().registerModule(JavaTimeModule())
        return JsonJacksonCodec(mapper)
    }
}
```

#### When Redisson saves you code

The reason to take on Redisson — beyond curiosity — is the abstractions you'd otherwise hand-roll. A `RLock.tryLock(waitTime, leaseTime, unit)` already gives you a watchdog-renewed reentrant lock with proper unlock semantics; rebuilding that on Lettuce is a hundred lines of Lua plus tests. `RRateLimiter` already implements distributed token-bucket. `RBloomFilter` already gives you the distributed Bloom filter. `RReliableTopic` gives you persistent-on-the-broker pub/sub. If you find yourself writing Lua, ask first whether Redisson already has it.

---

### 4. Spring Cache (`@Cacheable`, `@CachePut`, `@CacheEvict`)

#### Lettuce-backed `RedisCacheManager`

```kotlin
@Configuration
@EnableCaching
class CacheConfig(private val json: GenericJackson2JsonRedisSerializer) {

    @Bean
    fun cacheConfiguration(): RedisCacheConfiguration =
        RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10))
            .computePrefixWith { name -> "cache:${name}::" }
            .serializeKeysWith(SerializationPair.fromSerializer(StringRedisSerializer.UTF_8))
            .serializeValuesWith(SerializationPair.fromSerializer(json))
            .disableCachingNullValues()

    @Bean
    fun cacheManagerCustomizer(): RedisCacheManagerBuilderCustomizer =
        RedisCacheManagerBuilderCustomizer { builder ->
            builder.withCacheConfiguration(
                "users",
                RedisCacheConfiguration.defaultCacheConfig()
                    .entryTtl(Duration.ofMinutes(30))
                    .serializeValuesWith(SerializationPair.fromSerializer(json)),
            )
            builder.withCacheConfiguration(
                "shortLived",
                RedisCacheConfiguration.defaultCacheConfig()
                    .entryTtl(Duration.ofSeconds(30))
                    .serializeValuesWith(SerializationPair.fromSerializer(json)),
            )
        }
}
```

Service annotations:

```kotlin
@Service
class UserService(private val repo: UserRepository) {

    @Cacheable(cacheNames = ["users"], key = "#id", sync = true,
               unless = "#result == null")
    fun load(id: String): User? = repo.findById(id).getOrNull()

    @CachePut(cacheNames = ["users"], key = "#u.id")
    fun save(u: User): User = repo.save(u)

    @CacheEvict(cacheNames = ["users"], key = "#id")
    fun delete(id: String) = repo.deleteById(id)

    @Cacheable(cacheNames = ["shortLived"],
               key = "T(java.util.Objects).hash(#filter.country, #filter.tier)",
               condition = "#filter.cacheable")
    fun search(filter: UserFilter): List<User> = repo.search(filter)
}
```

`sync = true` is your stampede protection — Spring serializes lookups for the same key inside a single JVM. It does not coordinate across instances; combine it with a randomized TTL and possibly a distributed lock if multiple instances cold-start the same hot key against an expensive backend.

#### Custom `KeyGenerator` for Kotlin data classes

```kotlin
@Component
class DataClassKeyGenerator : KeyGenerator {
    override fun generate(target: Any, method: Method, vararg params: Any?): Any =
        SimpleKey(method.name, *params.map(::asKey).toTypedArray())

    private fun asKey(p: Any?): Any = when (p) {
        null -> "null"
        is String, is Number, is Boolean, is Enum<*> -> p
        else -> p::class.simpleName + ":" + p.hashCode()  // or serialize to JSON if stable equality matters
    }
}
```

```kotlin
@Cacheable(cacheNames = ["users"], keyGenerator = "dataClassKeyGenerator")
fun search(filter: UserFilter): List<User> = repo.search(filter)
```

#### Redisson's `RedissonSpringCacheManager`

```kotlin
@Configuration
@EnableCaching
class RedissonCacheConfig {

    @Bean
    fun cacheManager(redisson: RedissonClient): CacheManager {
        val configs = mapOf(
            // ttl, maxIdleTime
            "users"      to CacheConfig(TimeUnit.MINUTES.toMillis(30), TimeUnit.MINUTES.toMillis(15)),
            "shortLived" to CacheConfig(TimeUnit.SECONDS.toMillis(30), 0),
        )
        return RedissonSpringCacheManager(redisson, configs).apply { setCodec(JsonJacksonCodec()) }
    }
}
```

The big differences from Spring's `RedisCacheManager`:

- TTL **and** max-idle are first-class per cache, computed on Redisson's side (it runs an eviction Lua script unless you switch to `RedissonSpringCacheNativeManager` for Redis 7.4+ native hash field expiry).
- The PRO edition adds `LocalCachedCacheConfig`, which gives you a near-cache that reads from in-process memory and listens on a pub/sub channel for invalidations — effectively L1+L2 in one bean. Read operations can be ~45× faster than going through Redis on every hit.
- Eviction policies (LRU / LFU / SOFT) are configurable on the local cache.

For most teams: start with `RedisCacheManager` (no extra dependency, plain JSON in Redis, easy to inspect), upgrade to Redisson when you need per-entry TTL or local-cache invalidation events.

#### Multi-level cache by hand

Spring's `CompositeCacheManager` doesn't write through to both layers. The idiomatic recipe is a custom `Cache` that wraps Caffeine and Redis:

```kotlin
class TwoLevelCache(
    private val name: String,
    private val l1: Cache,
    private val l2: Cache,
) : Cache by l1 {

    override fun getName() = name
    override fun getNativeCache() = mapOf("l1" to l1, "l2" to l2)

    override fun get(key: Any): ValueWrapper? =
        l1.get(key) ?: l2.get(key)?.also { l1.put(key, it.get()) }

    override fun <T : Any?> get(key: Any, type: Class<T>?): T? =
        l1.get(key, type) ?: l2.get(key, type)?.also { l1.put(key, it) }

    override fun put(key: Any, value: Any?) {
        l2.put(key, value)
        l1.put(key, value)
    }

    override fun evict(key: Any) { l2.evict(key); l1.evict(key) }
    override fun clear()         { l2.clear();   l1.clear() }
}

@Component
class TwoLevelCacheManager(
    private val caffeine: CaffeineCacheManager,
    private val redis: RedisCacheManager,
) : CacheManager {
    override fun getCache(name: String): Cache? {
        val l1 = caffeine.getCache(name) ?: return null
        val l2 = redis.getCache(name) ?: return null
        return TwoLevelCache(name, l1, l2)
    }
    override fun getCacheNames(): Collection<String> = caffeine.cacheNames
}
```

The remaining wrinkle is **L1 invalidation across instances**. The cheapest fix is to publish an invalidation event on a Redis pub/sub channel whenever the application writes to the cache and have every instance subscribe and call `l1.evict(key)`. The pre-built starters `spring-boot-multilevel-cache-starter` (SuppieRK) and `spring-boot-multi-layer-cache` (Piazzolla) implement exactly this pattern with Caffeine + Redis + Resilience4j circuit breaker, and Redisson PRO offers it out of the box via `LocalCachedMapCache`.

#### Cache patterns by hand

```kotlin
@Service
class CacheAside(private val tpl: RedisTemplate<String, User>, private val repo: UserRepository) {

    fun get(id: String): User? {
        val key = "user:$id"
        tpl.opsForValue().get(key)?.let { return it }                 // L2 hit
        val fresh = repo.findById(id).getOrNull() ?: return null      // miss → DB
        tpl.opsForValue().set(key, fresh, Duration.ofMinutes(10))     // populate
        return fresh
    }

    fun writeThrough(u: User) {
        repo.save(u)                                                  // DB first
        tpl.opsForValue().set("user:${u.id}", u, Duration.ofMinutes(10))
    }

    fun writeBehind(u: User, scope: CoroutineScope) {
        tpl.opsForValue().set("user:${u.id}", u, Duration.ofMinutes(10))
        scope.launch(Dispatchers.IO) { repo.save(u) }                 // async persist
    }
}
```

Read-through is just cache-aside hidden behind a service interface — Spring's `@Cacheable(sync=true)` is the read-through.

---

### 5. Distributed locks

#### Lettuce + Lua: SET NX with safe release

```kotlin
@Component
class LettuceLock(private val tpl: StringRedisTemplate) {

    private val releaseScript = DefaultRedisScript<Long>(
        """
        if redis.call('get', KEYS[1]) == ARGV[1] then
          return redis.call('del', KEYS[1])
        else
          return 0
        end
        """.trimIndent(), Long::class.java
    )

    /** Acquire `key` for `ttl`. Returns the unique fencing token if granted, null otherwise. */
    fun tryLock(key: String, ttl: Duration): String? {
        val token = UUID.randomUUID().toString()
        val ok = tpl.execute { conn ->
            conn.stringCommands().set(
                key.toByteArray(), token.toByteArray(),
                Expiration.from(ttl), RedisStringCommands.SetOption.SET_IF_ABSENT,
            )
        }
        return if (ok == true) token else null
    }

    fun unlock(key: String, token: String): Boolean =
        tpl.execute(releaseScript, listOf(key), token) == 1L
}

inline fun <T> LettuceLock.withLock(
    key: String, ttl: Duration = Duration.ofSeconds(30), block: () -> T,
): T {
    val token = tryLock(key, ttl) ?: throw IllegalStateException("lock $key not acquired")
    try { return block() } finally { unlock(key, token) }
}
```

Use it like this:

```kotlin
fettuceLock.withLock("billing:account:$accountId", ttl = Duration.ofSeconds(10)) {
    transferFunds(...)
}
```

There is no auto-renewal. If your critical section can take longer than `ttl`, either bump the TTL with a generous safety margin or add a heartbeat. This is the foot-gun Redisson hides from you.

#### Redisson `RLock`

```kotlin
@Component
class OrderProcessor(private val redisson: RedissonClient) {

    fun process(orderId: String) {
        val lock = redisson.getLock("lock:order:$orderId")
        // Wait up to 5s, hold for up to 30s. Pass -1 leaseTime to enable the watchdog.
        val acquired = lock.tryLock(5, 30, TimeUnit.SECONDS)
        require(acquired) { "could not acquire lock for $orderId" }
        try {
            // critical section
        } finally {
            if (lock.isHeldByCurrentThread) lock.unlock()
        }
    }
}
```

Variants:

- `redisson.getFairLock(name)` — FIFO across requesters, slower.
- `redisson.getReadWriteLock(name)` — `.readLock()` / `.writeLock()`.
- `redisson.getSemaphore(name)` — N permits.
- `redisson.getCountDownLatch(name)` — coordination across processes.
- `redisson.getFencedLock(name)` (4.x) — combines a lock with a monotonically increasing fencing token returned from `lockAndGetToken()`. **Use this whenever a stale lock holder could corrupt downstream state**: pass the token along with every write and have the downstream verify token ≥ last_seen_token.

#### `@Transactional` interaction

A persistent rule: **acquire the lock outside the transaction, release outside the transaction, and make the transaction the body of the critical section**. If you put `@Transactional` *around* a method that also acquires the lock, you risk holding the lock past commit (because Spring's transaction interceptor runs first, the lock is released *before* the DB commit completes, and another instance can read pre-committed state).

```kotlin
@Service
class CorrectOrdering(
    private val redisson: RedissonClient,
    private val tx: TransactionTemplate,
) {
    fun processOrder(orderId: String) {
        val lock = redisson.getLock("lock:order:$orderId")
        if (!lock.tryLock(5, 30, TimeUnit.SECONDS)) error("locked")
        try {
            tx.execute { /* DB writes commit here */ }
        } finally {
            if (lock.isHeldByCurrentThread) lock.unlock()
        }
    }
}
```

#### AOP-style `@DistributedLock`

```kotlin
@Target(AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
annotation class DistributedLock(
    val key: String,                 // SpEL, e.g. "'order:' + #orderId"
    val waitMs: Long = 5_000,
    val leaseMs: Long = 30_000,
)

@Aspect @Component
class DistributedLockAspect(private val redisson: RedissonClient) {
    private val parser = SpelExpressionParser()
    private val nameDiscoverer = StandardReflectionParameterNameDiscoverer()

    @Around("@annotation(lockAnn)")
    fun around(pjp: ProceedingJoinPoint, lockAnn: DistributedLock): Any? {
        val sig = pjp.signature as MethodSignature
        val ctx = StandardEvaluationContext().apply {
            nameDiscoverer.getParameterNames(sig.method)?.forEachIndexed { i, n ->
                setVariable(n, pjp.args[i])
            }
        }
        val key = parser.parseExpression(lockAnn.key).getValue(ctx, String::class.java)
            ?: error("blank lock key")
        val lock = redisson.getLock(key)
        check(lock.tryLock(lockAnn.waitMs, lockAnn.leaseMs, TimeUnit.MILLISECONDS)) {
            "could not acquire $key"
        }
        try { return pjp.proceed() } finally {
            if (lock.isHeldByCurrentThread) lock.unlock()
        }
    }
}

// Usage
@DistributedLock(key = "'order:' + #orderId", leaseMs = 60_000)
fun processOrder(orderId: String) { /* … */ }
```

---

### 6. Rate limiting

#### Lettuce + Lua — fixed window

`src/main/resources/scripts/fixed_window.lua`:

```lua
local current = redis.call('INCR', KEYS[1])
if tonumber(current) == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
if tonumber(current) > tonumber(ARGV[2]) then
  return 0
end
return 1
```

```kotlin
@Configuration
class RateLimitScripts {
    @Bean fun fixedWindow(): DefaultRedisScript<Long> = DefaultRedisScript<Long>().apply {
        setLocation(ClassPathResource("scripts/fixed_window.lua"))
        resultType = Long::class.java
    }
}

@Component
class FixedWindowLimiter(
    private val tpl: StringRedisTemplate,
    private val script: DefaultRedisScript<Long>,
) {
    fun allow(bucket: String, windowSec: Long, max: Long): Boolean =
        tpl.execute(script, listOf("rl:fw:$bucket"), windowSec.toString(), max.toString()) == 1L
}
```

#### Lettuce + Lua — sliding window log (sorted set)

`scripts/sliding_window.lua`:

```lua
local now    = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max    = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, now - window)
local count = redis.call('ZCARD', KEYS[1])
if count >= max then return 0 end
redis.call('ZADD', KEYS[1], now, member)
redis.call('PEXPIRE', KEYS[1], window)
return 1
```

```kotlin
@Component
class SlidingWindowLimiter(
    private val tpl: StringRedisTemplate,
    @Qualifier("slidingWindow") private val script: DefaultRedisScript<Long>,
) {
    fun allow(bucket: String, windowMs: Long, max: Long): Boolean {
        val now = System.currentTimeMillis()
        return tpl.execute(
            script,
            listOf("rl:sw:$bucket"),
            now.toString(), windowMs.toString(), max.toString(),
            "$now:${UUID.randomUUID()}",
        ) == 1L
    }
}
```

#### Token bucket via Lua

`scripts/token_bucket.lua`:

```lua
local tokens_key   = KEYS[1]
local timestamp_key= KEYS[2]
local rate         = tonumber(ARGV[1])
local capacity     = tonumber(ARGV[2])
local now          = tonumber(ARGV[3])
local requested    = tonumber(ARGV[4])

local last_tokens  = tonumber(redis.call("get", tokens_key)) or capacity
local last_refresh = tonumber(redis.call("get", timestamp_key)) or 0
local delta        = math.max(0, now - last_refresh)
local filled       = math.min(capacity, last_tokens + (delta * rate))
local allowed      = filled >= requested
local new_tokens   = allowed and (filled - requested) or filled

local ttl          = math.floor(2 * capacity / rate)
redis.call("setex", tokens_key,    ttl, new_tokens)
redis.call("setex", timestamp_key, ttl, now)
return allowed and 1 or 0
```

#### Redisson's built-in rate limiter

```kotlin
@Component
class RedissonLimiter(redisson: RedissonClient) {
    private val limiter: RRateLimiter = redisson.getRateLimiter("api:public").apply {
        // 100 permits per second across all instances
        trySetRate(RateType.OVERALL, 100, Duration.ofSeconds(1))
    }

    fun allow(): Boolean = limiter.tryAcquire(1)
    suspend fun allowAsync(): Boolean = limiter.tryAcquireAsync(1).asDeferred().await()
}
```

`RateType.OVERALL` aggregates across every JVM connected to the same Redis. `RateType.PER_CLIENT` bounds the rate per `RedissonClient` instance — useful when you want each pod to have its own quota. Be aware: `RRateLimiter` may permit short bursts beyond the rate when the bucket has accumulated permits during quiet periods (issue #3639). For strict shaping use the Lua sliding window or token-bucket recipes.

#### Servlet filter / WebFlux filter wrappers

Servlet (Spring MVC):

```kotlin
@Component
class RateLimitFilter(private val limiter: SlidingWindowLimiter) : OncePerRequestFilter() {
    override fun doFilterInternal(req: HttpServletRequest, res: HttpServletResponse, chain: FilterChain) {
        val key = req.getHeader("X-Api-Key") ?: req.remoteAddr
        if (!limiter.allow(key, windowMs = 60_000, max = 600)) {
            res.status = HttpStatus.TOO_MANY_REQUESTS.value()
            res.setHeader("Retry-After", "60")
            return
        }
        chain.doFilter(req, res)
    }
}
```

WebFlux:

```kotlin
@Component
class ReactiveRateLimitFilter(private val redisson: RedissonClient) : WebFilter {
    private val limiter = redisson.reactive().getRateLimiter("api:public").apply {
        trySetRate(RateType.OVERALL, 100, Duration.ofSeconds(1)).block()
    }

    override fun filter(exchange: ServerWebExchange, chain: WebFilterChain): Mono<Void> =
        limiter.tryAcquire(1).flatMap { ok ->
            if (ok) chain.filter(exchange)
            else {
                exchange.response.statusCode = HttpStatus.TOO_MANY_REQUESTS
                exchange.response.headers["Retry-After"] = "1"
                exchange.response.setComplete()
            }
        }
}
```

#### Bucket4j-Redis as an alternative

Bucket4j is the most feature-complete library if you need multiple bandwidths on a single bucket (e.g. 100 req/min **and** 1000 req/hour at the same time):

```kotlin
@Configuration
class Bucket4jConfig {
    @Bean fun proxyManager(client: RedisClient): LettuceBasedProxyManager<ByteArray> {
        val conn: StatefulRedisConnection<String, ByteArray> = client.connect(
            RedisCodec.of(StringCodec.UTF8, ByteArrayCodec()),
        )
        return LettuceBasedProxyManager.builderFor(conn)
            .withExpirationStrategy(
                ExpirationAfterWriteStrategy.basedOnTimeForRefillingBucketUpToMax(Duration.ofHours(1))
            )
            .build()
    }
}

@Component
class B4jLimiter(private val proxy: LettuceBasedProxyManager<ByteArray>) {
    private val cfg = BucketConfiguration.builder()
        .addLimit(Bandwidth.simple(100, Duration.ofMinutes(1)))
        .addLimit(Bandwidth.simple(1000, Duration.ofHours(1)))
        .build()

    fun bucket(user: String): Bucket =
        proxy.builder().build("u:$user".toByteArray(), cfg)

    fun allow(user: String): Boolean = bucket(user).tryConsume(1)
}
```

---

### 7. Pub/Sub

#### Vanilla Lettuce: convertAndSend + listener container

```kotlin
data class PriceTick(val symbol: String, val price: BigDecimal)

@Configuration
class PubSubConfig {

    @Bean
    fun listenerContainer(cf: RedisConnectionFactory, listener: PriceTickListener): RedisMessageListenerContainer =
        RedisMessageListenerContainer().apply {
            setConnectionFactory(cf)
            addMessageListener(listener, ChannelTopic("price.ticks"))
            // Or pattern subscription: PatternTopic("price.*")
        }
}

@Component
class PriceTickPublisher(private val tpl: RedisTemplate<String, Any>) {
    fun publish(t: PriceTick) = tpl.convertAndSend("price.ticks", t)
}

@Component
class PriceTickListener(
    private val mapper: ObjectMapper,
) : MessageListener {
    override fun onMessage(message: Message, pattern: ByteArray?) {
        val tick = mapper.readValue(message.body, PriceTick::class.java)
        // …
    }
}
```

#### Redisson `RTopic` and `RShardedTopic`

```kotlin
@Component
class RedissonPubSub(private val redisson: RedissonClient) {
    private val topic: RTopic = redisson.getTopic("price.ticks")
    private val shardedTopic: RShardedTopic = redisson.getShardedTopic("price.ticks")

    init {
        topic.addListener(PriceTick::class.java) { _, msg -> /* handle */ }
    }

    fun publish(t: PriceTick): Long = topic.publish(t)            // returns # subscribers
    fun publishSharded(t: PriceTick): Long = shardedTopic.publish(t)
}
```

`RShardedTopic` uses Redis 7's `SPUBLISH`/`SSUBSCRIBE`, restricting message propagation to the shard owning the topic key's slot. This is mandatory in any cluster pub-sub workload at scale: regular `RTopic` broadcasts every message to every node over the cluster bus, which scales linearly *negatively*. `RReliableTopic` (Redisson) and `RClusteredTopic` (PRO) add persistence and partitioning respectively.

#### Reactive WebFlux subscription via `ReactiveRedisMessageListenerContainer`

```kotlin
@Component
class ReactivePubSub(private val cf: ReactiveRedisConnectionFactory) {

    fun stream(): Flow<PriceTick> {
        val container = ReactiveRedisMessageListenerContainer(cf)
        return container.receive(ChannelTopic("price.ticks"))
            .map { it.message }                                   // raw String
            .map { jacksonObjectMapper().readValue<PriceTick>(it) }
            .asFlow()
    }
}
```

#### Pitfalls

Both Spring Data's pub/sub and Redisson's `RTopic` provide **at-most-once** delivery with no replay: any subscriber that's offline misses messages. If you need guarantees, either move to Redis Streams (next section) or use `RReliableTopic`. Redis Sentinel/Cluster failovers always cause a brief subscription resubscribe, during which messages are lost.

---

### 8. Redis Streams

Streams give you a persistent append-only log with consumer groups, just enough Kafka-lite behavior to handle workflows that need replayability without an actual broker.

#### Producer (Lettuce, blocking)

```kotlin
@Service
class StreamProducer(private val tpl: StringRedisTemplate) {

    fun publish(key: String, payload: Map<String, String>): RecordId? =
        tpl.opsForStream<String, String>()
            .add(MapRecord.create(key, payload))
}
```

#### Consumer group + `StreamMessageListenerContainer`

```kotlin
@Configuration
class StreamConsumerConfig(private val cf: RedisConnectionFactory) {

    @Bean(initMethod = "start", destroyMethod = "stop")
    fun streamContainer(handler: OrderEventHandler): StreamMessageListenerContainer<String, MapRecord<String, String, String>> {
        val opts = StreamMessageListenerContainer.StreamMessageListenerContainerOptions
            .builder()
            .pollTimeout(Duration.ofMillis(500))   // how long XREADGROUP BLOCKs
            .batchSize(20)
            .build()

        val container = StreamMessageListenerContainer.create(cf, opts)
        // Make sure the group exists – fails fast if you forget on a fresh stream.
        runCatching {
            cf.connection.streamCommands().xGroupCreate(
                "orders.events".toByteArray(), "orders-svc", ReadOffset.from("0"), true
            )
        }

        container.receive(
            Consumer.from("orders-svc", InetAddress.getLocalHost().hostName),
            StreamOffset.create("orders.events", ReadOffset.lastConsumed()),
            handler,
        )
        return container
    }
}

@Component
class OrderEventHandler(
    private val tpl: StringRedisTemplate,
    private val service: OrderService,
) : StreamListener<String, MapRecord<String, String, String>> {

    override fun onMessage(record: MapRecord<String, String, String>) {
        try {
            service.handle(record.value)
            tpl.opsForStream<String, String>().acknowledge("orders-svc", record)
        } catch (e: Exception) {
            // leave unacked — XPENDING will reflect it; reaper task will reclaim
        }
    }
}
```

#### XAUTOCLAIM reaper for stuck messages

```kotlin
@Component
class StuckMessageReaper(
    private val tpl: StringRedisTemplate,
    private val handler: OrderEventHandler,
) {
    @Scheduled(fixedDelay = 30_000)
    fun reclaim() {
        val cmd = tpl.connectionFactory!!.connection.streamCommands()
        // Reclaim anything pending for >60s; loop until cursor wraps to 0-0.
        var cursor = "0-0"
        do {
            val claim = cmd.xAutoClaim(
                "orders.events".toByteArray(),
                "orders-svc",
                "reaper-${UUID.randomUUID()}",
                Duration.ofSeconds(60),
                RecordId.of(cursor),
                XAutoClaimOptions.justIds().count(50),
            )
            // For each reclaimed record: re-deliver to the handler or DLQ after N attempts.
            cursor = claim.nextCursor.value
        } while (cursor != "0-0")
    }
}
```

#### Reactive consumer with `ReactiveStreamOperations`

```kotlin
@Component
class ReactiveStreamConsumer(private val rtpl: ReactiveStringRedisTemplate) {

    fun consume(): Flux<MapRecord<String, String, String>> =
        rtpl.opsForStream<String, String>().read(
            Consumer.from("orders-svc", "pod-1"),
            StreamReadOptions.empty().count(20).block(Duration.ofMillis(500)),
            StreamOffset.create("orders.events", ReadOffset.lastConsumed()),
        )
}
```

#### Coroutine + `Flow` consumer

```kotlin
@Component
class CoroutineStreamConsumer(
    private val rtpl: ReactiveStringRedisTemplate,
    private val handler: OrderEventHandler,
    @Qualifier("appScope") private val scope: CoroutineScope,
) {
    @PostConstruct
    fun start() {
        scope.launch {
            rtpl.opsForStream<String, String>().read(
                Consumer.from("orders-svc", "pod-1"),
                StreamReadOptions.empty().count(20).block(Duration.ofMillis(500)),
                StreamOffset.create("orders.events", ReadOffset.lastConsumed()),
            ).asFlow()
                .onEach { handler.onMessage(it) }
                .catch { e -> logger.error(e) { "stream consumer crashed" } }
                .collect()
        }
    }
}
```

#### Redisson `RStream`

```kotlin
@Service
class RedissonStreamUsage(redisson: RedissonClient) {
    private val stream: RStream<String, String> = redisson.getStream("orders.events")

    fun publish(payload: Map<String, String>): StreamMessageId =
        stream.add(StreamAddArgs.entries(payload))

    init { runCatching { stream.createGroup(StreamCreateGroupArgs.name("orders-svc").makeStream()) } }

    fun poll(): Map<StreamMessageId, Map<String, String>> =
        stream.readGroup("orders-svc", "pod-1",
            StreamReadGroupArgs.greaterThan(StreamMessageId.NEVER_DELIVERED).count(20).timeout(Duration.ofMillis(500)))
}
```

#### Idempotency

Stream IDs (`<ms>-<seq>`) are monotonic and unique within a stream — perfect natural dedup keys. The simplest pattern:

```kotlin
fun handleOnce(record: MapRecord<String, String, String>) {
    val newlyClaimed = tpl.opsForValue().setIfAbsent(
        "processed:${record.id}", "1", Duration.ofDays(7)
    ) == true
    if (!newlyClaimed) return
    process(record)
    tpl.opsForStream<String, String>().acknowledge("orders-svc", record)
}
```

The 7-day TTL covers your replay horizon; for true at-least-once with safe re-processing, make the downstream operation idempotent on the **business** key as well.

---

### 9. Spring Session Data Redis

#### Servlet HttpSession

```kotlin
// dependencies/version managed by spring-boot
implementation("org.springframework.session:spring-session-data-redis")
```

```yaml
spring:
  session:
    store-type: redis
    timeout: 30m
    redis:
      flush-mode: on_save        # or immediate
      namespace: "myapp:sessions"
      repository-type: indexed   # default is "default" since 3.x; indexed enables ZRANGEBYSCORE expiry
```

Enable explicitly if you want session events:

```kotlin
@Configuration
@EnableRedisIndexedHttpSession(maxInactiveIntervalInSeconds = 1800)
class SessionConfig
```

```kotlin
@Component
class SessionEvents {
    @EventListener fun onCreated(e: SessionCreatedEvent)   = log.info { "session ${e.sessionId} created" }
    @EventListener fun onDestroyed(e: SessionDestroyedEvent) = log.info { "session ${e.sessionId} destroyed" }
    @EventListener fun onExpired(e: SessionExpiredEvent)   = log.info { "session ${e.sessionId} expired" }
}
```

#### Reactive WebFlux WebSession

```kotlin
@Configuration
@EnableRedisIndexedWebSession(maxInactiveIntervalInSeconds = 1800)
class ReactiveSessionConfig {
    @Bean
    fun sessionRedisSerializer(json: GenericJackson2JsonRedisSerializer)
            : RedisSerializer<Any> = json
}
```

#### Custom session attribute serialization

The default is JDK serialization. Replace it with the JSON serializer so Kotlin data classes survive deployments and can be inspected from `redis-cli`:

```kotlin
@Bean("springSessionDefaultRedisSerializer")
fun springSessionDefaultRedisSerializer(json: GenericJackson2JsonRedisSerializer): RedisSerializer<Any> = json
```

#### Multi-region considerations

Spring Session stores by `sessionId` only; nothing about it is region-aware. If you replicate Redis cross-region (Active-Active for ElastiCache, Redis Enterprise CRDB), reads remain correct but session updates must converge somewhere; the safest production setup is sticky load-balancer routing within a region plus a same-region Redis, with cross-region failover handled by DNS rather than replication. If you absolutely need session continuity across regions, plan for clock skew effects on TTL.

---

### 10. Spring Data Redis Repositories

```kotlin
@RedisHash("Customer", timeToLive = 3600)
data class Customer(
    @Id val id: String? = null,
    @Indexed val email: String,
    val name: String,
    val tier: Tier,
    val address: Address,
)

data class Address(@Indexed val city: String, val country: String)

interface CustomerRepository : CrudRepository<Customer, String> {
    fun findByEmail(email: String): Customer?
    fun findByAddress_City(city: String): List<Customer>
}
```

```kotlin
@Configuration
@EnableRedisRepositories(
    basePackages = ["com.example.repo"],
    enableKeyspaceEvents = RedisKeyValueAdapter.EnableKeyspaceEvents.ON_STARTUP,
)
class RepoConfig
```

`@RedisHash` stores entities as Redis hashes plus secondary index sets keyed `Customer:email:foo@bar.com`. `@Indexed` covers exact-match equality lookups; range queries, full-text and projections are not supported. `findByAddress_City` works because property paths translate to nested indexes.

#### Redis OM Spring for full-text/secondary indexes

When you need RediSearch (full text, range, geo, vectors), drop in Redis OM Spring:

```kotlin
@Configuration
@EnableRedisDocumentRepositories(basePackages = ["com.example.search"])
class OmConfig
```

```kotlin
@Document
data class Product(
    @Id val id: String? = null,
    @Searchable val title: String,         // full-text
    @Indexed val brand: String,            // exact match
    @Indexed val price: Double,            // numeric range
    @Indexed val location: Point,          // geo
)

interface ProductRepository : RedisDocumentRepository<Product, String> {
    fun findByBrand(brand: String): List<Product>
    fun findByPriceBetween(min: Double, max: Double): List<Product>
    fun findByLocationNear(point: Point, distance: Distance): List<Product>
}
```

Behind the scenes Redis OM creates a RediSearch index on startup (`FT.CREATE`) and translates query methods to `FT.SEARCH`. Note: this requires the RediSearch module — Redis Stack or Redis 8 (where it's in core).

---

### 11. Coroutines + Redis (in depth)

#### What coroutines bring

Plain `RedisTemplate` is blocking: every call ties up a JVM thread waiting on the network. In a coroutine, that thread comes from a dispatcher pool, and blocking it means you can starve the dispatcher (especially `Dispatchers.Default`, which has only ~#CPU threads). The fix is either:

1. Marshall blocking calls onto `Dispatchers.IO` with `withContext(Dispatchers.IO) { ... }`. Functional, but every Redis call costs a thread switch.
2. Use the **reactive** stack (`ReactiveRedisTemplate`, `RedissonReactiveClient`) and bridge it to coroutines with `awaitSingle`, `awaitFirstOrNull`, and `asFlow` from `kotlinx-coroutines-reactor`. This is non-blocking end to end, structured concurrency works correctly, and one Netty event-loop thread can drive thousands of in-flight commands.

The second option is what every new coroutine-on-Redis codebase should adopt.

#### `ReactiveRedisTemplate` with await extensions

```kotlin
@Configuration
class ReactiveTemplateConfig {

    @Bean
    fun reactiveRedisTemplate(
        cf: ReactiveRedisConnectionFactory,
        json: GenericJackson2JsonRedisSerializer,
    ): ReactiveRedisTemplate<String, Any> {
        val ctx = RedisSerializationContext.newSerializationContext<String, Any>(StringRedisSerializer.UTF_8)
            .value(json).hashKey(StringRedisSerializer.UTF_8).hashValue(json)
            .build()
        return ReactiveRedisTemplate(cf, ctx)
    }
}

@Service
class CounterRepository(private val rtpl: ReactiveRedisTemplate<String, Any>) {

    suspend fun increment(key: String): Long =
        rtpl.opsForValue().increment(key).awaitSingle()

    suspend fun get(key: String): User? =
        rtpl.opsForValue().get(key).awaitFirstOrNull() as User?

    suspend fun set(key: String, value: User, ttl: Duration) {
        rtpl.opsForValue().set(key, value, ttl).awaitSingle()
    }

    fun streamRecent(stream: String): Flow<MapRecord<String, Any, Any>> =
        rtpl.opsForStream<Any, Any>().read(StreamOffset.fromStart(stream)).asFlow()
}
```

The `…AndAwait` family (e.g. `incrementAndAwait`) exists on Spring Data's repository interfaces but not always on `ReactiveRedisTemplate` — for the template, call the existing reactive method and chain `.awaitSingle()`/`.awaitFirstOrNull()`.

#### Coroutine-aware Redisson lock helper

This is the pattern the user heard about. Redisson's `RLock.lock()` records the current **JVM thread id** and refuses to unlock from a different thread — but coroutines are dispatched across thread pools, so unlock will almost always run on a different physical thread, throwing `IllegalMonitorStateException`.

The fix is to use Redisson's **explicit-`threadId` API** that's only on the reactive client, with a `CoroutineContext` element that pins a synthetic id to the coroutine for its lifetime.

```kotlin
class CoroutineId(val id: Long) : AbstractCoroutineContextElement(Key) {
    companion object Key : CoroutineContext.Key<CoroutineId>
}

private val coroutineIdSeq = AtomicLong(1)
fun newCoroutineId() = CoroutineId(coroutineIdSeq.getAndIncrement())

class CoroutineRedissonLock(private val redisson: RedissonReactiveClient, private val name: String) {
    suspend fun <T> withLock(
        wait: Duration = Duration.ofSeconds(5),
        lease: Duration = Duration.ofSeconds(30),
        block: suspend () -> T,
    ): T {
        val id = currentCoroutineContext()[CoroutineId]?.id
            ?: error("Run inside withContext(newCoroutineId()) { … } so the lock has a stable owner id.")
        val lock = redisson.getLock(name)
        val acquired = lock.tryLock(wait.toMillis(), lease.toMillis(), TimeUnit.MILLISECONDS, id)
            .awaitSingle()
        check(acquired) { "could not acquire $name within $wait" }
        try { return block() } finally { lock.unlock(id).awaitFirstOrNull() }
    }
}

// Usage:
suspend fun process(orderId: String, redisson: RedissonReactiveClient) =
    withContext(newCoroutineId()) {
        CoroutineRedissonLock(redisson, "lock:order:$orderId").withLock {
            // critical section
        }
    }
```

Without this pattern, two coroutines that happen to land on the same Netty thread would treat the Redisson lock as reentrant when they shouldn't, and unlock would succeed for the wrong owner. There are also third-party wrappers like `redisson-kotlin-coroutines-reactive` that codify this for you.

#### Suspend Lua scripts

```kotlin
@Component
class SuspendingLimiter(
    private val rtpl: ReactiveStringRedisTemplate,
    private val script: DefaultRedisScript<Long>,
) {
    suspend fun allow(bucket: String, windowSec: Long, max: Long): Boolean {
        val res = rtpl.execute(script, listOf("rl:fw:$bucket"), listOf(windowSec.toString(), max.toString()))
            .next()                               // Mono<Long>
            .awaitSingle()
        return res == 1L
    }
}
```

#### Structured concurrency for fan-out reads

```kotlin
suspend fun loadDashboard(userId: String): Dashboard = coroutineScope {
    val user      = async { repo.get("user:$userId") }
    val orders    = async { repo.get("orders:$userId") as List<Order>? ?: emptyList() }
    val features  = async { repo.get("features:$userId") as Features? ?: Features.DEFAULT }
    Dashboard(user.await()!!, orders.await(), features.await())
}
```

All three reads run concurrently on the Netty event loop; `coroutineScope` cancels the siblings if one fails.

#### Don't mix blocking RedisTemplate with coroutines

Calling `tpl.opsForValue().get(key)` from a `suspend` function on `Dispatchers.Default` will park a CPU dispatcher thread for the duration of the network round trip. Under load this turns into thread starvation and head-of-line blocking. Either wrap with `withContext(Dispatchers.IO)` (a per-call thread switch tax) or — preferred — convert to `ReactiveRedisTemplate` and `awaitSingle`. The blocking surface should only appear in places that can't bridge: inside `@Cacheable` interceptors, JCache integrations, etc.

---

### 12. WebFlux + Redis (in depth)

WebFlux's request thread is a Netty event loop with a small number of threads (default `2 * #CPU`). A blocking call holds it for the round-trip duration; one slow Redis command can stall hundreds of in-flight requests across the whole pod. Treat `Mono`/`Flux` as load-bearing: every Redis call must come from `ReactiveRedisTemplate`, `RedissonReactiveClient`, or a coroutine bridged through `mono { … }` / `coroutineScope`.

#### End-to-end controller

```kotlin
@RestController
@RequestMapping("/api/users")
class UserController(private val rtpl: ReactiveRedisTemplate<String, Any>) {

    @GetMapping("/{id}")
    fun get(@PathVariable id: String): Mono<ResponseEntity<User>> =
        rtpl.opsForValue().get("user:$id")
            .cast(User::class.java)
            .map { ResponseEntity.ok(it) }
            .defaultIfEmpty(ResponseEntity.notFound().build())

    @PostMapping
    fun create(@RequestBody u: User): Mono<Void> =
        rtpl.opsForValue().set("user:${u.id}", u, Duration.ofMinutes(30)).then()

    @GetMapping(produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
    fun stream(): Flux<PriceTick> =
        ReactiveRedisMessageListenerContainer(rtpl.connectionFactory)
            .receive(ChannelTopic("price.ticks"))
            .map { jacksonObjectMapper().readValue(it.message, PriceTick::class.java) }
}
```

Coroutine handler equivalent:

```kotlin
@RestController
@RequestMapping("/api/users-co")
class UserCoController(private val rtpl: ReactiveRedisTemplate<String, Any>) {

    @GetMapping("/{id}")
    suspend fun get(@PathVariable id: String): User =
        rtpl.opsForValue().get("user:$id").awaitFirstOrNull() as User?
            ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
}
```

#### Spring Cache + WebFlux

`@Cacheable` is fundamentally **synchronous**. As of Spring Framework 6.1 it understands `Mono`/`Flux`/`CompletableFuture` return types and will adapt automatically — the cache stores the materialized object — but only if the underlying cache implementation supports async (`CaffeineCacheManager` with `setAsyncCacheMode(true)` does; `RedisCacheManager` does not). On WebFlux, that means:

- Caching `Mono<Foo>` of a hot key with `RedisCacheManager` works but Spring will block briefly to write through.
- Prefer **manual cache-aside on `ReactiveRedisTemplate`** for performance-critical paths, and reserve `@Cacheable` for cold paths (admin endpoints, configuration).

#### Redisson Reactive vs `ReactiveRedisTemplate`

Both are non-blocking. Use `ReactiveRedisTemplate` for command-level access (`SET`, `GET`, `XADD`, `ZRANGEBYSCORE`); use `redisson.reactive()` when you specifically want the high-level objects (`RLockReactive`, `RRateLimiterReactive`, `RTopicReactive`, `RBucketReactive`). They share the same Netty plumbing under the hood when wired in the same app, and there's no harm in mixing them in different services.

#### Backpressure

`Flux` from `ReactiveRedisTemplate.opsForStream().read(...)` is push-based at Redis's pace. If your downstream is slower than ingest, add `.onBackpressureBuffer(1024)` or `.limitRate(50)` rather than letting Reactor drop messages with `MissingBackpressureException`. For SSE endpoints, `.publishOn(Schedulers.parallel(), 16)` plus `.onBackpressureLatest()` is a reasonable default.

---

### 13. Testing

#### Testcontainers setup

```kotlin
@Testcontainers
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class RedisIntegrationTest {

    companion object {
        @Container
        @JvmStatic
        val redis: GenericContainer<*> = GenericContainer("redis:7.4-alpine")
            .withExposedPorts(6379)
            .withReuse(true)

        @JvmStatic
        @DynamicPropertySource
        fun props(reg: DynamicPropertyRegistry) {
            reg.add("spring.data.redis.host") { redis.host }
            reg.add("spring.data.redis.port") { redis.firstMappedPort }
        }
    }

    @Autowired lateinit var tpl: StringRedisTemplate

    @Test fun `roundtrip`() {
        tpl.opsForValue().set("k", "v")
        assertThat(tpl.opsForValue().get("k")).isEqualTo("v")
    }
}
```

The Redis-specific module (`com.redis:testcontainers-redis`) adds `RedisContainer`/`RedisStackContainer` with built-in port mapping and waits — useful when you also want RediSearch:

```kotlin
@Container @JvmStatic
val stack: RedisStackContainer =
    RedisStackContainer(DockerImageName.parse("redis/redis-stack:7.4.0-v0"))
        .withExposedPorts(6379)
```

#### `@DataRedisTest` slice

```kotlin
@DataRedisTest
@Testcontainers
class CustomerRepoTest {
    companion object {
        @Container @JvmStatic
        val redis = GenericContainer<Nothing>("redis:7.4-alpine").apply { withExposedPorts(6379) }
        @JvmStatic @DynamicPropertySource
        fun props(reg: DynamicPropertyRegistry) {
            reg.add("spring.data.redis.host") { redis.host }
            reg.add("spring.data.redis.port") { redis.firstMappedPort }
        }
    }

    @Autowired lateinit var repo: CustomerRepository

    @Test fun `index lookup`() {
        repo.save(Customer(email = "x@y.com", name = "X", tier = Tier.GOLD,
            address = Address(city = "Berlin", country = "DE")))
        assertThat(repo.findByEmail("x@y.com")).isNotNull
    }
}
```

`@DataRedisTest` activates only the `RedisRepositoriesAutoConfiguration` and `RedisAutoConfiguration` slice — no web layer, no `@Service` beans.

#### Embedded Redis

`it.ozimov:embedded-redis` (or `com.github.codemonstur:embedded-redis`) starts a real `redis-server` binary in-process. It's fast (no Docker daemon) and good for unit tests that just need round-trip semantics, but **does not support modules**, has only intermittent maintenance, and breaks on Apple Silicon without ARM binaries. Stick with Testcontainers for anything beyond toy tests.

#### Testing locks

```kotlin
@Test fun `only one thread holds the lock at a time`() {
    val lock = redisson.getLock("test:lock")
    val executor = Executors.newFixedThreadPool(8)
    val concurrentHolders = AtomicInteger()
    val maxObserved = AtomicInteger()
    val latch = CountDownLatch(8)
    repeat(8) {
        executor.submit {
            try {
                lock.lock(5, TimeUnit.SECONDS)
                val now = concurrentHolders.incrementAndGet()
                maxObserved.updateAndGet { max(it, now) }
                Thread.sleep(50)
                concurrentHolders.decrementAndGet()
                lock.unlock()
            } finally { latch.countDown() }
        }
    }
    latch.await()
    assertThat(maxObserved.get()).isEqualTo(1)
}
```

#### Testing rate limiters

```kotlin
@Test fun `fixed window allows N then rejects`() {
    repeat(10) { assertThat(limiter.allow("u1", 60, 10)).isTrue }
    assertThat(limiter.allow("u1", 60, 10)).isFalse
}
```

#### Testing pub/sub & streams

Both are eventually consistent. Awaitility makes it readable:

```kotlin
import org.awaitility.Awaitility.await

@Test fun `subscriber receives published message`() {
    val received = CopyOnWriteArrayList<String>()
    container.addMessageListener({ m, _ -> received += String(m.body) }, ChannelTopic("test"))
    Thread.sleep(200) // let subscription settle
    tpl.convertAndSend("test", "hi")
    await().atMost(Duration.ofSeconds(2)).until { received.contains("\"hi\"") }
}
```

---

### 14. Connection management & production gotchas

**`shareNativeConnection`.** Lettuce defaults to a single multiplexed TCP connection. That's correct for non-blocking commands. The moment you call a blocking command (`BLPOP`, `XREAD BLOCK`, anything held open while waiting), it hijacks that one connection — every other thread blocks too. Either set `spring.data.redis.lettuce.pool.enabled=true` and tune the pool to ≥ peak parallel blocking commands, or push streaming consumption to the reactive container and keep the shared connection.

**Redisson connection pool.** `connectionPoolSize: 64` (default in YAML examples above) is a single pool shared by all of Redisson's collections. Watch `RedisExecutor`/`RedisTimeoutException` warnings; if you see them, the bottleneck is usually subscription connections (default 50) being saturated by many `RLock` instances rather than the main pool.

**Cluster topology refresh.** Always enable `enableAllAdaptiveRefreshTriggers()`. Periodic refresh is optional; if you do enable it, 30 s is fine for small clusters and should stretch to several minutes for clusters of >50 nodes. With **ElastiCache configuration endpoints**, set `dynamicRefreshSources = true` so a temporarily-failed seed node doesn't poison the topology view.

**SSL/TLS for ElastiCache.**

```kotlin
val server = RedisStandaloneConfiguration("master.cache.amazonaws.com", 6379)
val client = LettuceClientConfiguration.builder()
    .useSsl().disablePeerVerification()  // ElastiCache uses an Amazon-issued cert; you can chain in the AWS CA instead
    .commandTimeout(Duration.ofSeconds(2))
    .build()
LettuceConnectionFactory(server, client)
```

For `rediss://` URIs in Redisson, set `address: "rediss://...:6379"` and the SSL handshake is automatic.

**IAM auth for ElastiCache.** ElastiCache Valkey/Redis ≥ 7.0 supports SigV4-signed IAM auth tokens that you pass as the password. Tokens are valid for 15 minutes; long-lived connections must refresh. Use a `RedisCredentialsProvider`:

```kotlin
class IamCredentialsProvider(
    private val userId: String,
    private val cacheName: String,
    private val region: Region,
    private val isServerless: Boolean,
    private val awsCreds: AwsCredentialsProvider,
) : RedisCredentialsProvider {

    override fun resolveCredentials(): Mono<RedisCredentials> = Mono.fromSupplier {
        val token = IamAuthTokenRequest(userId, cacheName, region, isServerless)
            .toSignedRequestUri(awsCreds.resolveCredentials())
        RedisCredentials.just(userId, token)
    }.cache(Duration.ofMinutes(10))   // refresh well before 15-minute expiry
}

val redisURI = RedisURI.builder()
    .withHost("master.use1.cache.amazonaws.com").withPort(6379).withSsl(true)
    .withAuthentication(IamCredentialsProvider(...))
    .build()
```

For a `LettuceConnectionFactory` you can subclass `RedisStandaloneConfiguration` and override `getPassword()` (or set credentials via `LettuceClientConfiguration.builder().redisCredentialsProviderFactory(...)` in newer Lettuce). Be aware: the ElastiCache "12-hour absolute connection lifetime" rule applies — your client must reconnect every 12 hours regardless of token freshness. Expect the AUTH/HELLO command to need re-issuing on reconnect; some Lettuce versions cache the original auth and fail with `NOAUTH` after IAM-based reconnects (issue redis/lettuce#1201). The mitigation is the `RedisCredentialsProvider` wired into client config rather than a static password on `RedisStandaloneConfiguration`.

**Reconnect on failover.** Lettuce automatically reconnects on socket failure. The behaviors that bite teams:
- New connections will take seconds, not milliseconds, after a master failover; bound your command timeout (`commandTimeout: 2s`) so you fail fast.
- `topologyRefreshOptions.adaptiveRefreshTriggers` includes `MOVED_REDIRECT` and `PERSISTENT_RECONNECTS`, which is what triggers a clean refresh after the failover.
- If you use Lettuce's `disconnectedBehavior(REJECT_COMMANDS)`, the application will get fast-fail exceptions during the disconnect window instead of stacking up commands waiting on a queue.

**Spring Boot Actuator health.**

```yaml
management:
  endpoints.web.exposure.include: health,info,metrics
  endpoint.health.show-details: when-authorized
  health:
    redis.enabled: true
```

Spring Boot 3 provides `RedisHealthIndicator` and `RedisReactiveHealthIndicator` automatically. `INFO`-based health checks are cluster-aware in current versions; if you see "DOWN" with no error, upgrade Spring Boot — the `redis_version` parsing bug in cluster mode was fixed in 2.3.x. Add a custom indicator if you want to test specific keyspaces:

```kotlin
@Component("redisCacheHealth")
class RedisCacheHealth(private val tpl: StringRedisTemplate) : AbstractHealthIndicator() {
    override fun doHealthCheck(b: Health.Builder) {
        val pong = tpl.connectionFactory!!.connection.use { it.ping() }
        b.up().withDetail("ping", pong)
    }
}
```

---

### 15. Decision matrix

**Use Lettuce + Spring Data Redis when:**
- You need command-level access only (`GET`, `SET`, `XADD`, `ZADD`, etc.).
- You want the smallest dependency footprint and the broadest Spring ecosystem support — Spring Cache, Spring Session, repositories, reactive WebFlux, Boot health indicators all assume `RedisConnectionFactory`.
- You're committed to a Reactor/coroutine stack: Spring Data Redis Reactive with `awaitSingle` is the most natural API.
- Your distributed primitives are simple enough to ship as Lua scripts (rate limiting, idempotency markers, ad-hoc atomic update).

**Use Redisson when:**
- You need first-class distributed primitives: locks (`RLock`, `RFairLock`, `RFencedLock`, `RReadWriteLock`), `RSemaphore`, `RCountDownLatch`, `RBloomFilter`, `RHyperLogLog` with API parity, `RDelayedQueue`, `RScheduledExecutorService`.
- You want a built-in distributed rate limiter (`RRateLimiter`) without writing Lua.
- You need sharded / reliable pub-sub (`RShardedTopic`, `RReliableTopic`).
- You want a near-cache for Spring Cache (`RedissonSpringCacheManager` with local cache configuration, especially in PRO).
- Your team values "Java collections that happen to live in Redis" over "raw Redis commands".

**Use both when (this is the common case):**
- Lettuce powers `RedisTemplate`, `ReactiveRedisTemplate`, `RedisCacheManager`, Spring Session, repositories, actuator health.
- Redisson is injected only where a specific abstraction shines: `RLock`/`RFencedLock` around correctness-critical workflows, `RRateLimiter` for global API quotas, `RBloomFilter` for dedup, `RShardedTopic` for cluster pub-sub, `RedissonSpringCacheManager` if you adopt local caches.
- Keep `spring.data.redis.client-type=lettuce` so Spring Data doesn't get switched onto Redisson unintentionally; let Redisson auto-config wire its own client.
- Account for **two pools** in your Redis maxclients budget: Lettuce shared connection (~ 1 + pool max) and Redisson (`connectionPoolSize` + `subscriptionConnectionPoolSize`).
- For coroutines: never call `RLock` from a `suspend` fun. Use `RedissonReactiveClient.getLock(name).lock(threadId)` with a `CoroutineId` context element, or wrap in `withContext(Dispatchers.IO)` only for short critical sections you understand.

---

## Caveats

This guide reflects API surface for Spring Boot 3.3+ / 3.5, Spring Data Redis 4.x, Lettuce 6.5+, Redisson 3.50+ (and the just-released 4.x line), and Redis 7.2+/Redis 8 / Valkey 8 — all current as of the Spring Boot 3 era. A few things to watch:

- The **Redisson 3.x → 4.x** transition introduced `redisson-spring-data-4x` for Spring Data Redis 4 / Spring Boot 3.x compatibility. If you're on an older Spring Boot, pin `redisson-spring-boot-starter` 3.27–3.50 and the matching `redisson-spring-data-3x` adapter.
- **`RRateLimiter` burst behavior** — multiple users have observed that the limiter allows transient bursts above the configured rate when permits accumulate during quiet periods (issue #3639). If hard ceilings matter, prefer a Lua sliding window.
- **Coroutines + `RLock`**: the JVM-thread-id ownership rule is genuinely error-prone. The pattern shown using `RLockReactive.lock(threadId)` + `CoroutineId` is the correct workaround; do not rely on `forceUnlock()` in production.
- **Redis OM Spring** requires Redis Stack or Redis 8 (RediSearch is built-in there); plain open-source Redis 7 won't have `FT.*` commands.
- **`@Cacheable` reactive support** is recent (Spring Framework 6.1) and works for Caffeine in async-cache mode but does not yet make `RedisCacheManager` reactive — Redis cache writes still block briefly. Manual cache-aside on `ReactiveRedisTemplate` remains the lowest-risk pattern in WebFlux.
- **ElastiCache IAM auth + Lettuce reconnect** has a long-tail bug history (lettuce-io/lettuce-core#1201); test failover behavior end-to-end before relying on it in production. The published `RedisCredentialsProvider` pattern (rather than a static password) is what current AWS samples use.
- Numbers in the Caffeine + local-cache "~45×" figure come from Redisson's own marketing; treat as order-of-magnitude rather than benchmark-grade.
- Library version numbers in the `build.gradle.kts` snippet are pinned to release candidates current at the time of writing; bump them in lockstep when you update Spring Boot, since `redisson-spring-data-4x`, `bucket4j-redis`, and `redis-om-spring` are tightly coupled to specific Spring Data Redis majors.