# Redis mastery roadmap for Spring Boot Kotlin developers

**Your fastest path from redis-cli basics to production-ready caching and advanced patterns takes approximately 6-8 weeks of focused learning.** This roadmap prioritizes hands-on practice with Kotlin-specific patterns, leveraging your existing Spring Boot expertise. Each phase builds incrementally—starting with data structure refreshers before diving into Spring integration, caching, advanced use cases, and production deployment. The estimated **40-55 hours** of learning assumes active coding alongside tutorials, not passive reading.

---

## Phase 1: Redis fundamentals refresher (8-12 hours)

Since you have basic redis-cli experience, this phase focuses on deepening your understanding of when and why to use each data structure, plus the critical memory management concepts that directly impact production caching.

### Data structures you'll actually use

**Strings** remain your workhorse for simple caching—session tokens, serialized objects, and atomic counters using `INCR`/`DECR`. Time complexity is O(1) for nearly everything, making them ideal for high-throughput scenarios. The key insight: Redis stores numeric strings as actual integers internally, so counter operations are memory-efficient.

**Hashes** deserve special attention for Kotlin data classes. Instead of storing `user:1:name`, `user:1:email` as separate keys, a single hash `HSET user:1 name "Alice" email "alice@example.com"` achieves **50-70% memory savings** through compact listpack encoding (for hashes under 512 entries). Redis 7.4 introduced **hash field expiration**—individual fields can now have TTLs, which is transformative for partial cache invalidation.

**Sorted Sets** power leaderboards, rate limiters, and priority queues. The combination of skip list and hash table provides O(log N) insertion with O(1) score lookups. Use `ZINCRBY` for atomic score updates and `ZREVRANGE` (not `ZRANGE`) for descending leaderboards.

| Structure | Primary Use Case | Time Complexity | Memory Tip |
|-----------|-----------------|-----------------|------------|
| **String** | Caching, counters | O(1) | Use `SETEX` with TTL |
| **Hash** | Object storage | O(1) per field | Keep under 512 entries for listpack |
| **List** | Queues, feeds | O(1) head/tail | Enable `list-compress-depth` |
| **Set** | Unique tracking | O(1) add/check | Integer-only sets use compact intset |
| **Sorted Set** | Rankings, rate limiting | O(log N) | ~5-6x memory of plain list |
| **Stream** | Event sourcing | O(1) append | Trim with `MAXLEN ~1000` |
| **HyperLogLog** | Cardinality estimation | O(1) | Fixed 12KB for billions of items |
| **Bitmap** | Binary flags | O(1) | 100M users = ~12MB |
| **Geospatial** | Location queries | O(log N) | Stored as sorted set internally |

### Expiration and eviction policies matter for caching

Understanding eviction policies prevents mysterious cache misses in production. Set `maxmemory` (always—never run unbounded) and choose your policy based on workload:

- **`allkeys-lru`**: Recommended default for pure caching—evicts least recently used keys regardless of TTL
- **`allkeys-lfu`**: Better hit rates when some keys are genuinely "hotter" than others
- **`volatile-lru`**: Use when mixing cache (with TTL) and persistent data (without TTL)
- **`noeviction`**: Returns errors on write when full—only for critical data scenarios

Configure LFU tuning with `lfu-log-factor` (higher = more accesses needed to saturate) and `lfu-decay-time` for counter decay. Monitor with `INFO stats` checking `keyspace_hits`, `keyspace_misses`, and `evicted_keys`.

**Practice exercises**: Build a redis-cli session exploring `OBJECT ENCODING` on different data sizes, experiment with `MEMORY USAGE`, and test eviction behavior with `DEBUG SLEEP` during writes at memory limits.

**Key resources**:
- Redis University RU101 (free): https://university.redis.com/courses/ru101/
- Data types reference: https://redis.io/docs/latest/develop/data-types/
- Eviction policies: https://redis.io/docs/latest/develop/reference/eviction/

---

## Phase 2: Spring Boot + Redis integration with Kotlin (10-14 hours)

This phase transforms your redis-cli knowledge into production Kotlin code. Focus on Lettuce (the default client), proper serialization for data classes, and idiomatic Kotlin patterns.

### Configuration that actually works

Start with `spring-boot-starter-data-redis` and configure through `application.yml`:

```yaml
spring:
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
      timeout: 2000ms
      lettuce:
        pool:
          max-active: 8
          max-idle: 8
          min-idle: 0
```

For reactive applications (WebFlux with coroutines), add `spring-boot-starter-data-redis-reactive` and `kotlinx-coroutines-reactor`.

### RedisTemplate versus ReactiveRedisTemplate

| Aspect | RedisTemplate | ReactiveRedisTemplate |
|--------|---------------|----------------------|
| Return types | Direct values | `Mono<T>`, `Flux<T>` |
| Kotlin integration | Direct usage | Coroutines via `awaitSingle()` |
| Client support | Lettuce or Jedis | Lettuce only |
| Transactions | Full MULTI/EXEC | Limited |
| Best for | MVC apps, batch ops | WebFlux, high concurrency |

### Kotlin-specific patterns that reduce boilerplate

**Extension functions** make Redis operations feel native to Kotlin:

```kotlin
inline fun <reified T> RedisTemplate<String, T>.getOrNull(key: String): T? =
    opsForValue().get(key)

suspend fun <T : Any> ReactiveRedisTemplate<String, T>.getOrDefault(
    key: String, 
    default: T
): T = opsForValue().get(key).awaitSingleOrNull() ?: default
```

**Coroutines with reactive Redis** require `kotlinx-coroutines-reactor`:

```kotlin
@Repository
class UserRepository(private val redis: ReactiveRedisTemplate<String, User>) {
    suspend fun findById(id: String): User? =
        redis.opsForValue().get("user:$id").awaitSingleOrNull()
    
    suspend fun save(user: User): Boolean =
        redis.opsForValue().set("user:${user.id}", user, Duration.ofHours(1)).awaitSingle()
}
```

### Serialization configuration for Kotlin data classes

The default `JdkSerializationRedisSerializer` creates large, unreadable payloads with versioning nightmares. Use Jackson with `KotlinModule`:

```kotlin
@Configuration
class RedisConfig {
    @Bean
    fun redisTemplate(connectionFactory: RedisConnectionFactory): RedisTemplate<String, Any> {
        val mapper = ObjectMapper().apply {
            registerModule(KotlinModule.Builder().build())
            registerModule(JavaTimeModule())
        }
        val serializer = GenericJackson2JsonRedisSerializer(mapper)
        
        return RedisTemplate<String, Any>().apply {
            setConnectionFactory(connectionFactory)
            keySerializer = StringRedisSerializer()
            valueSerializer = serializer
            hashKeySerializer = StringRedisSerializer()
            hashValueSerializer = serializer
        }
    }
}
```

**Serialization comparison**:

| Serializer | Payload Size | Human Readable | Kotlin Support |
|------------|-------------|----------------|----------------|
| JDK (default) | Large | No | Requires Serializable |
| Jackson JSON | Medium | Yes | Needs KotlinModule |
| GenericJackson2Json | Medium-Large | Yes | Includes @class info |
| Kotlinx Serialization | Small | Yes | Native, compile-time safe |

**Practice project**: Build a Kotlin service with `RedisTemplate`, test with different serializers, measure payload sizes with `MEMORY USAGE`, and implement a reactive repository with coroutines.

**Key resources**:
- Spring Data Redis reference: https://docs.spring.io/spring-data/redis/reference/
- Baeldung tutorial: https://www.baeldung.com/spring-data-redis-tutorial
- Kotlin-specific guide: https://www.geekyhacker.com/getting-started-with-spring-data-redis-with-kotlin/
- GitHub example: https://github.com/kasramp/spring-data-redis-example-kotlin

---

## Phase 3: Caching with Spring Cache + Redis (6-8 hours)

Spring's cache abstraction combined with Redis provides declarative caching that integrates naturally with Kotlin services. This phase focuses on the annotations, configuration, and patterns that prevent common pitfalls.

### Cache configuration with per-cache TTLs

```kotlin
@Configuration
@EnableCaching
class CacheConfig {
    @Bean
    fun cacheManager(connectionFactory: RedisConnectionFactory): RedisCacheManager {
        val defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(30))
            .serializeKeysWith(RedisSerializationContext.SerializationPair
                .fromSerializer(StringRedisSerializer()))
            .serializeValuesWith(RedisSerializationContext.SerializationPair
                .fromSerializer(GenericJackson2JsonRedisSerializer()))
            .disableCachingNullValues()
        
        val cacheConfigs = mapOf(
            "users" to defaultConfig.entryTtl(Duration.ofHours(1)),
            "products" to defaultConfig.entryTtl(Duration.ofMinutes(15)),
            "sessions" to defaultConfig.entryTtl(Duration.ofHours(24))
        )
        
        return RedisCacheManager.builder(connectionFactory)
            .cacheDefaults(defaultConfig)
            .withInitialCacheConfigurations(cacheConfigs)
            .build()
    }
}
```

### Annotation patterns for Kotlin services

```kotlin
@Service
class ProductService(private val repository: ProductRepository) {
    
    @Cacheable(value = ["products"], key = "#id")
    fun findById(id: String): Product =
        repository.findById(id).orElseThrow { ProductNotFoundException(id) }
    
    @CachePut(value = ["products"], key = "#product.id")
    fun update(product: Product): Product = repository.save(product)
    
    @CacheEvict(value = ["products"], key = "#id")
    fun delete(id: String) = repository.deleteById(id)
    
    @CacheEvict(value = ["products"], allEntries = true)
    @Scheduled(fixedRate = 3600000) // Hourly cache refresh
    fun refreshCache() { /* triggers eviction */ }
}
```

### Cache-aside pattern implementation

For scenarios requiring more control than annotations provide:

```kotlin
@Service
class CacheAsideService(
    private val redisTemplate: RedisTemplate<String, User>,
    private val database: UserRepository
) {
    fun getUser(id: String): User {
        val cached = redisTemplate.opsForValue().get("user:$id")
        if (cached != null) return cached
        
        val user = database.findById(id).orElseThrow()
        redisTemplate.opsForValue().set("user:$id", user, Duration.ofHours(1))
        return user
    }
}
```

### Common pitfalls to avoid

- **Caching null values**: Disabled by default with `.disableCachingNullValues()`, but be aware this means cache misses for genuinely null results will hit the database repeatedly
- **Key collisions**: Use `key-prefix: "myapp:"` in configuration to namespace keys
- **Self-invocation bypass**: `@Cacheable` on a method called from within the same class won't trigger caching—Spring proxies don't intercept internal calls
- **Serialization mismatches**: Changing data class structure breaks existing cached values; consider versioning strategies or cache invalidation on deploy

**Practice project**: Implement a product catalog service with multi-tier caching, write integration tests using embedded Redis (`it.ozimov:embedded-redis`), and measure cache hit rates.

**Key resources**:
- Spring Boot caching: https://docs.spring.io/spring-boot/reference/io/caching.html
- Redis cache configuration: https://docs.spring.io/spring-data/redis/reference/redis/redis-cache.html
- Baeldung cache tutorial: https://www.baeldung.com/spring-boot-redis-cache

---

## Phase 4: Advanced Redis use cases (12-16 hours)

These patterns transform Redis from a simple cache into a versatile infrastructure component. Each use case represents 2-3 hours of focused learning and implementation.

### Pub/Sub messaging (2-3 hours)

Redis Pub/Sub provides fire-and-forget messaging—if no subscriber is listening, messages are lost. Use for real-time notifications, not reliable messaging (use Streams for that).

**Reactive subscriber with Kotlin coroutines**:

```kotlin
@Configuration
class PubSubConfig(private val connectionFactory: ReactiveRedisConnectionFactory) {
    
    fun subscribeToChannel(channel: String): Flow<String> {
        val container = ReactiveRedisMessageListenerContainer(connectionFactory)
        return container.receive(ChannelTopic.of(channel))
            .map { it.message }
            .asFlow()
    }
}
```

**Key insight**: Use `PatternTopic("events.*")` for wildcard subscriptions, but note pattern matching is more expensive than direct channel subscriptions.

### Distributed locks with Redisson (3-4 hours)

Redisson provides production-ready distributed primitives. The critical pattern: **always set TTL to prevent deadlocks**.

```kotlin
@Service
class OrderService(private val redisson: RedissonClient) {
    
    fun processOrder(orderId: String): OrderResult {
        val lock = redisson.getLock("order:$orderId")
        val acquired = lock.tryLock(500, 5000, TimeUnit.MILLISECONDS)
        
        if (!acquired) throw OrderLockedException(orderId)
        
        try {
            // Critical section
            return doProcessOrder(orderId)
        } finally {
            if (lock.isHeldByCurrentThread) lock.unlock()
        }
    }
}
```

Add `redisson-spring-boot-starter` (version 3.45.0+) and configure via `redisson.yaml` or programmatically. For Spring Integration, `RedisLockRegistry` provides a simpler API but fewer features.

### Rate limiting implementations (2-3 hours)

**Sliding window with sorted sets** provides accurate, per-user rate limiting:

```kotlin
fun isAllowed(userId: String, limit: Int, windowSeconds: Long): Boolean {
    val key = "ratelimit:$userId"
    val now = System.currentTimeMillis()
    val windowStart = now - (windowSeconds * 1000)
    
    redisTemplate.opsForZSet().removeRangeByScore(key, 0.0, windowStart.toDouble())
    val count = redisTemplate.opsForZSet().size(key) ?: 0
    
    if (count < limit) {
        redisTemplate.opsForZSet().add(key, now.toString(), now.toDouble())
        redisTemplate.expire(key, windowSeconds, TimeUnit.SECONDS)
        return true
    }
    return false
}
```

For production, consider Lua scripts for atomicity or `bucket4j-redis` for a battle-tested implementation.

### Session management with Spring Session (2-3 hours)

Spring Session with Redis enables horizontal scaling by externalizing session state:

```yaml
spring:
  session:
    store-type: redis
    redis:
      namespace: spring:session
```

Add `spring-session-data-redis` dependency. Enable `@EnableRedisHttpSession(maxInactiveIntervalInSeconds = 1800)` for indexed sessions that support querying by principal name. **Critical**: Enable keyspace notifications (`notify-keyspace-events Egx`) for proper session expiration cleanup.

### Redis Streams for event-driven patterns (3-4 hours)

Streams provide Kafka-like semantics with consumer groups, acknowledgments, and message replay—unlike Pub/Sub, messages persist.

```kotlin
@Configuration
class StreamConfig {
    @Bean
    fun streamListener(factory: RedisConnectionFactory): StreamMessageListenerContainer<String, MapRecord<String, String, String>> {
        val options = StreamMessageListenerContainerOptions.builder<String, MapRecord<String, String, String>>()
            .pollTimeout(Duration.ofMillis(100))
            .build()
        
        val container = StreamMessageListenerContainer.create(factory, options)
        
        container.receive(
            Consumer.from("order-group", "consumer-1"),
            StreamOffset.create("orders", ReadOffset.lastConsumed())
        ) { message ->
            processOrder(message.value)
            redisTemplate.opsForStream().acknowledge("order-group", message)
        }
        
        container.start()
        return container
    }
}
```

**Critical patterns**: Always acknowledge messages to prevent PEL (Pending Entries List) growth, use `XTRIM MAXLEN ~10000` to cap stream size, and implement `XCLAIM` for handling failed consumer recovery.

### Leaderboards and geospatial queries (2 hours)

**Leaderboard** operations are straightforward with sorted sets:

```kotlin
fun addScore(playerId: String, score: Double) = 
    redisTemplate.opsForZSet().incrementScore("leaderboard", playerId, score)

fun getTopPlayers(count: Long) = 
    redisTemplate.opsForZSet().reverseRangeWithScores("leaderboard", 0, count - 1)

fun getPlayerRank(playerId: String) = 
    redisTemplate.opsForZSet().reverseRank("leaderboard", playerId)
```

**Geospatial** queries use `GEOSEARCH` (Redis 6.2+):

```kotlin
fun findNearby(longitude: Double, latitude: Double, radiusKm: Double) =
    redisTemplate.opsForGeo().radius(
        "locations",
        Circle(Point(longitude, latitude), Distance(radiusKm, Metrics.KILOMETERS))
    )
```

**Key resources**:
- Redisson documentation: https://github.com/redisson/redisson
- Spring Data Redis Streams: https://docs.spring.io/spring-data/redis/reference/redis/redis-streams.html
- Spring Session Redis: https://docs.spring.io/spring-session/reference/guides/boot-redis.html
- Distributed locks pattern: https://redis.io/docs/reference/patterns/distributed-locks/

---

## Phase 5: Production considerations (6-8 hours)

This phase covers the operational knowledge that separates hobby projects from production systems.

### Cluster versus Sentinel architecture decision

| Factor | Sentinel | Cluster |
|--------|----------|---------|
| Data size | Single machine capacity | Multi-terabyte with sharding |
| Write scaling | Single master only | Multiple masters |
| Multi-key operations | Full support | Requires hash tags `{key}` |
| Minimum nodes | 3 Sentinels + master + replicas | 6 nodes (3 masters + 3 replicas) |
| Complexity | Lower | Higher |

**Decision rule**: If your data fits on one machine and you need simplicity, use Sentinel. If you need write scaling or data exceeds single-node capacity, use Cluster.

### Lettuce configuration for production

The **most critical production setting** is cluster topology refresh—without it, your application won't detect failovers:

```kotlin
@Bean
fun lettuceConnectionFactory(): LettuceConnectionFactory {
    val topologyRefresh = ClusterTopologyRefreshOptions.builder()
        .enablePeriodicRefresh(Duration.ofSeconds(10))
        .enableAllAdaptiveRefreshTriggers() // React to MOVED, ASK, failures
        .build()
    
    val clientOptions = ClusterClientOptions.builder()
        .topologyRefreshOptions(topologyRefresh)
        .autoReconnect(true)
        .build()
    
    val clientConfig = LettuceClientConfiguration.builder()
        .clientOptions(clientOptions)
        .commandTimeout(Duration.ofSeconds(2))
        .build()
    
    return LettuceConnectionFactory(clusterConfig, clientConfig)
}
```

### Monitoring essentials

Deploy **Redis Exporter** for Prometheus (Grafana Dashboard ID: 763) and monitor:

- **Memory**: Alert at >80% of `maxmemory`
- **Hit rate**: `keyspace_hits / (keyspace_hits + keyspace_misses)` should exceed 90%
- **Latency**: p99 command latency >10ms indicates problems
- **Evictions**: Increasing `evicted_keys` means memory pressure
- **Connections**: `rejected_connections > 0` requires immediate attention

Enable **SLOWLOG** for debugging: `CONFIG SET slowlog-log-slower-than 10000` logs commands taking >10ms. Avoid `KEYS` (use `SCAN`), watch for expensive `HGETALL` on large hashes.

### Performance tuning checklist

**Application level**:
- Use pipelining for batch operations (5x throughput improvement)
- Set appropriate TTLs on all cache keys
- Use `SCAN` instead of `KEYS` for iteration
- Implement circuit breakers for Redis calls

**Redis server**:
- Set `maxmemory` to 80% of available RAM
- Choose appropriate eviction policy (`allkeys-lru` for caching)
- Enable `activedefrag yes` for memory optimization

**Linux kernel**:
- `vm.overcommit_memory = 1` (prevents OOM during fork)
- `vm.swappiness = 1` (avoid swapping)
- Disable transparent huge pages
- Increase `net.core.somaxconn` for high connection scenarios

### Persistence trade-offs

| Mode | Data Loss Risk | Performance | Best For |
|------|---------------|-------------|----------|
| RDB only | Minutes (last snapshot) | Minimal impact | Pure caching |
| AOF only | Up to 1 second | Higher (continuous writes) | Critical data |
| RDB + AOF | Minimal | Moderate | Maximum safety |
| None | Complete | Best | Ephemeral cache |

**Key resources**:
- Redis persistence: https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/
- Prometheus integration: https://redis.io/docs/latest/integrate/prometheus-with-redis-enterprise/
- Grafana dashboard: https://grafana.com/grafana/dashboards/763

---

## Learning resources summary

### Official documentation

| Resource | URL |
|----------|-----|
| Redis docs | https://redis.io/docs/latest/ |
| Spring Data Redis | https://docs.spring.io/spring-data/redis/reference/ |
| Spring Cache | https://docs.spring.io/spring-boot/reference/io/caching.html |
| Redis commands | https://redis.io/commands/ |

### Free courses

- **Redis University RU101** (fundamentals): https://university.redis.com/courses/ru101/
- **Redis for Java Developers**: https://university.redis.io/
- **Getting Started with Spring Data Redis**: https://redis.io/learn/develop/java/redis-and-spring-course

### Tutorials

- Baeldung Spring Data Redis: https://www.baeldung.com/spring-data-redis-tutorial
- Baeldung Redis Cache: https://www.baeldung.com/spring-boot-redis-cache
- Kotlin-specific guide: https://www.geekyhacker.com/getting-started-with-spring-data-redis-with-kotlin/

### GitHub repositories

| Repository | Focus |
|------------|-------|
| spring-projects/spring-data-redis | Official source |
| kasramp/spring-data-redis-example-kotlin | Kotlin CRUD + messaging |
| redisson/redisson | Distributed objects |
| eugenp/tutorials (persistence-modules) | Baeldung examples |

### Books

- **"Redis in Action"** (Manning): Comprehensive patterns with real-world examples
- **"Mastering Redis"** (O'Reilly): Advanced clustering, Lua scripting, internals

### Community

- Redis Discord: https://discord.com/invite/redis (15,000+ members)
- Stack Overflow tags: `[spring-data-redis]`, `[redis]`, `[lettuce]`, `[redisson]`

---

## Suggested weekly schedule

| Week | Phase | Hours | Focus |
|------|-------|-------|-------|
| 1 | Fundamentals | 8-12 | Data structures, eviction, Redis University RU101 |
| 2 | Spring Integration | 10-14 | RedisTemplate, serialization, Kotlin patterns |
| 3 | Caching | 6-8 | Spring Cache annotations, cache-aside, TTLs |
| 4-5 | Advanced Patterns | 12-16 | Pub/Sub, locks, rate limiting, Streams |
| 6 | Production | 6-8 | Cluster config, monitoring, performance tuning |

**Total estimated time: 40-55 hours** over 6-8 weeks, assuming 6-10 hours per week of focused learning with hands-on coding. Adjust based on your pace and depth requirements.