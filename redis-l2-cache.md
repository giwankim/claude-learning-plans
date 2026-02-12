---
title: "Redis L2 Cache"
category: "Data & Messaging"
description: "Redis as a high-traffic L2 cache for microservices"
---

# Redis Mastery for High-Traffic Microservices with Spring Boot and Kotlin

Building on your foundation of JWT token storage and session management, this curriculum will transform you into a Redis expert capable of architecting production-grade caching systems, distributed coordination, and event-driven microservices. The plan spans **10-12 weeks** of focused study, progressing from data structure mastery through advanced patterns to production deployment.

## Phase 1: Deep data structure mastery (Weeks 1-2)

Your existing Redis experience provides a foundation, but mastery requires understanding *when* and *why* to use each structure—not just *how*. This phase rebuilds your mental model around Redis's **O(1)** and **O(log N)** operations.

**Strings** extend far beyond simple key-value storage. Use `INCR`/`DECR` for atomic counters (rate limiting, page views), `SETEX` for distributed locks with automatic expiration, and `MGET`/`MSET` for batch operations reducing network round-trips. The critical insight: strings store binary-safe data up to **512MB**, making them suitable for serialized objects when hash overhead isn't justified.

**Hashes** excel for object storage where you need partial updates. Storing a user profile as `HSET user:123 email jane@example.com age 28` allows updating individual fields without deserializing the entire object—**40% memory savings** versus equivalent JSON strings for objects with multiple fields. Use hashes when your access pattern involves reading/writing individual fields frequently.

**Lists** implement FIFO queues with `LPUSH`/`RPOP` and capped collections with `LTRIM`. The blocking variants `BLPOP`/`BRPOP` enable efficient job queues without polling. Critical limitation: O(N) access by index makes lists unsuitable for random access patterns.

**Sets** provide membership testing, intersection, and union operations—ideal for tagging systems, social graphs (mutual friends via `SINTER`), and unique visitor tracking. **HyperLogLog** extends this for probabilistic cardinality counting with **12KB fixed memory** regardless of set size, achieving **0.81% standard error**—perfect for unique visitor counts across billions of events.

**Sorted sets** are Redis's most powerful structure for leaderboards and range queries. With O(log N) operations, they support millions of members efficiently. Twitter uses sorted sets for timeline caching, storing tweet IDs scored by timestamp. The `ZRANGEBYSCORE` command enables time-range queries, while `ZREVRANK` provides instant ranking lookups.

**Streams** (introduced in Redis 5.0) provide an append-only log with consumer groups—essentially Kafka-like functionality within Redis. Use streams for audit logs, event sourcing, and inter-service messaging when throughput requirements are moderate (thousands of messages per minute, not millions).

**Bitmaps** offer memory-efficient boolean arrays—tracking **365 days of user activity costs only 46 bytes**. Use `SETBIT`/`GETBIT` for feature flags, daily active users, and A/B test assignments.

### Week 1-2 milestones
- Complete the interactive tutorial at **try.redis.io**
- Finish **"Get Started with Redis"** course on Redis University (free, ~3 hours)
- Read chapters 1-4 of **"Redis in Action"** by Josiah Carlson—while dated on clients, the data modeling patterns remain authoritative
- **Practice project**: Build a social network backend storing user profiles (hashes), follower relationships (sets), timeline (sorted sets), and activity feed (streams)

---

## Phase 2: Advanced patterns for high-traffic systems (Weeks 3-5)

This phase introduces the distributed coordination patterns that separate Redis novices from experts.

### Distributed locking and the Redlock controversy

The basic distributed lock uses `SET lock:resource $uuid NX PX 30000`—atomic acquisition with automatic expiration preventing deadlocks. The **critical safety requirement**: release locks using a Lua script that verifies ownership:

```lua
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
```

The **Redlock algorithm** extends this across N independent Redis masters (typically 5), requiring majority agreement. However, Martin Kleppmann's critique raises valid concerns: Redlock assumes synchronous timing, which distributed systems cannot guarantee. **For correctness-critical applications** (financial transactions, inventory management), implement **fencing tokens**—monotonically increasing values verified by the protected resource—or consider Zookeeper/etcd for consensus-based locking.

**Redisson** (Java/Kotlin) provides production-ready implementations including fair locks (FIFO ordering), read/write locks, and reentrant locks with automatic lease renewal. For most microservice coordination needs, Redisson's `RLock` with configurable lease times strikes the right balance between simplicity and safety.

### Rate limiting implementation patterns

**Fixed window** (`INCR` + `EXPIRE`) is simplest but allows 2x burst at window boundaries. **Sliding window log** (sorted set with timestamps) provides precision but costs O(N) memory per user.

**Figma's sliding window counter** offers the optimal tradeoff: store counts in hash fields keyed by minute timestamps, sum the relevant windows on each request. Memory cost drops from **20MB to 2.4MB** for 10K users at 500 requests/day while maintaining second-level accuracy.

**Token bucket** requires Lua scripting for atomicity—refill tokens based on elapsed time, then attempt to consume. This pattern enables controlled bursts while maintaining average rate limits, ideal for API throttling:

```lua
local tokens = math.min(capacity, tokens + elapsed * rate)
if tokens >= 1 then
    tokens = tokens - 1
    redis.call('set', tokens_key, tokens)
    return 1
end
return 0
```

### Redis Streams for event-driven architecture

Streams provide **consumer groups** with explicit acknowledgment, enabling exactly-once processing semantics within your application logic. The critical commands:

- `XADD orders * order_id 123 status created` — append events with auto-generated IDs
- `XGROUP CREATE orders processors $ MKSTREAM` — create consumer group
- `XREADGROUP GROUP processors worker1 COUNT 10 STREAMS orders >` — read unprocessed messages
- `XACK orders processors {message_id}` — acknowledge processing

**When to choose Streams over Kafka**: existing Redis infrastructure, moderate throughput (thousands/minute), sub-millisecond latency requirements, simpler operational overhead. **Choose Kafka when**: throughput exceeds tens of thousands/second, long-term event retention needed, complex stream processing required.

### Lua scripting for atomic operations

Lua scripts execute atomically, eliminating race conditions in check-and-set patterns. Redis 7.0 introduced **Functions**—persistent, replicated server-side code replacing ephemeral `EVAL` scripts:

```
FUNCTION LOAD "#!lua name=mylib
redis.register_function('rate_limit', function(keys, args)
    -- atomic rate limiting logic
end)"
FCALL rate_limit 1 user:123 100 60
```

### Pipelining and transactions

**Pipelining** batches commands in a single round-trip, achieving **10x throughput improvement** for bulk operations—but commands aren't atomic. **MULTI/EXEC transactions** guarantee sequential execution without interleaving, but lack rollback on individual command failures.

Use **WATCH** for optimistic locking—the transaction aborts if watched keys change before EXEC. However, Lua scripts are generally preferred over WATCH patterns for their simplicity and atomicity.

### Week 3-5 milestones
- Complete **Stephen Grider's "Redis: The Complete Developer's Guide"** on Udemy (4.7/5 rating, includes E-commerce project)
- Read Uber's CacheFront case study for production caching patterns at **40M reads/second**
- Study Twitter's timeline architecture storing **105TB RAM across 10,000+ instances**
- **Practice project**: Implement a rate-limited API gateway with distributed locking for idempotency, supporting sliding window (1000 req/hour), token bucket (burst of 50), and circuit breaker patterns

---

## Phase 3: Multi-level caching architecture (Weeks 6-7)

Production systems rarely use Redis alone—multi-level caching with **local (L1) and distributed (L2) layers** reduces latency and Redis load while maintaining consistency.

### Caffeine + Redis architecture

Caffeine provides **sub-microsecond** local cache access versus Redis's millisecond network latency. The pattern: check Caffeine first, fall back to Redis on miss, populate Caffeine from Redis hits.

```kotlin
class MultiLevelCache(
    private val l1Cache: Cache,
    private val l2Cache: Cache
) : Cache {
    override fun get(key: Any): Cache.ValueWrapper? {
        l1Cache.get(key)?.let { return it }
        return l2Cache.get(key)?.also { value ->
            l1Cache.put(key, value.get())
        }
    }
}
```

### Cache coherence strategies

Local caches create consistency challenges—different instances may hold stale data. **Redis Pub/Sub** provides lightweight invalidation broadcasting:

```kotlin
@PostConstruct
fun subscribeToInvalidation() {
    redisTemplate.connectionFactory?.connection?.subscribe(
        { message, _ ->
            val key = String(message.body)
            caffeineCacheManager.cacheNames.forEach { name ->
                caffeineCacheManager.getCache(name)?.evict(key)
            }
        },
        "cache:invalidation".toByteArray()
    )
}
```

For stronger consistency, use **TTL-based expiration** with short windows (30-60 seconds) combined with event-driven invalidation for critical updates.

### Caching patterns comparison

- **Cache-aside (lazy loading)**: Application manages cache explicitly. Most flexible, but requires careful null handling and thundering herd mitigation
- **Read-through**: Cache manages loading from backing store. Simpler application code, but requires cache provider support
- **Write-through**: Writes go to cache and backing store synchronously. Strong consistency, but higher write latency
- **Write-behind**: Writes buffered in cache, async persisted. Lowest latency, but durability risk. Redisson provides native write-behind with configurable batch sizes and delays

### Cross-service cache invalidation in MSA

The most challenging caching problem: Service A updates data, Services B-D have cached copies. Solutions:

- **Event-driven invalidation via Kafka/Streams**: Publish change events, consuming services invalidate locally
- **CDC (Change Data Capture)**: Use Debezium to tail database binlog, publish changes automatically
- **Shared cache with TTL**: Accept eventual consistency with short TTLs
- **Cache versioning**: Include version in cache keys, increment on updates

Uber's CacheFront uses CDC tailing MySQL binlog for cache invalidation, achieving strong consistency while supporting **40M reads/second**.

### Week 6-7 milestones
- Read **"Redis Stack for Application Modernization"** (2024) for modern multi-model patterns
- Study the `spring-boot-multilevel-cache-starter` library implementation
- **Practice project**: Implement a product catalog with Caffeine L1 (1000 items, 10-minute TTL) + Redis L2, Pub/Sub-based invalidation across multiple application instances, and metrics tracking hit rates at each level

---

## Phase 4: Spring Boot and Kotlin integration (Weeks 8-9)

This phase focuses on idiomatic Kotlin patterns and production-grade Spring Data Redis configuration.

### Lettuce configuration for production

Lettuce is the default Spring Boot client—**thread-safe** and **auto-reconnecting**, connection pooling is often unnecessary except for blocking operations:

```kotlin
@Bean
fun lettuceConnectionFactory(): LettuceConnectionFactory {
    val socketOptions = SocketOptions.builder()
        .connectTimeout(Duration.ofSeconds(10))
        .keepAlive(SocketOptions.KeepAliveOptions.builder()
            .enable()
            .idle(Duration.ofSeconds(30))
            .build())
        .build()
    
    val clientOptions = ClientOptions.builder()
        .autoReconnect(true)
        .pingBeforeActivateConnection(true)
        .socketOptions(socketOptions)
        .build()
    
    val clientConfig = LettuceClientConfiguration.builder()
        .commandTimeout(Duration.ofSeconds(2))
        .readFrom(ReadFrom.REPLICA_PREFERRED)
        .clientOptions(clientOptions)
        .build()
    
    return LettuceConnectionFactory(serverConfig, clientConfig)
}
```

### Kotlin coroutines with reactive Redis

Lettuce provides native coroutines support via `connection.coroutines()`:

```kotlin
suspend fun getAndSet(key: String, value: String): String? {
    val api = connection.coroutines()
    val oldValue = api.get(key)
    api.set(key, value)
    return oldValue
}

fun getAllUsers(): Flow<User> {
    return reactiveRedisTemplate
        .opsForValue()
        .scan(ScanOptions.scanOptions().match("user:*").build())
        .asFlow()
}
```

Spring Data Redis supports `CoroutineCrudRepository` for reactive repository patterns:

```kotlin
interface UserCoroutineRepository : CoroutineCrudRepository<User, String> {
    suspend fun findByEmail(email: String): User?
    fun findByLastName(lastName: String): Flow<User>
}
```

### Spring Cache abstraction with multiple managers

Configure per-cache TTLs and serialization:

```kotlin
@Bean
fun redisCacheManager(connectionFactory: RedisConnectionFactory): RedisCacheManager {
    val defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
        .entryTtl(Duration.ofMinutes(30))
        .serializeValuesWith(
            RedisSerializationContext.SerializationPair.fromSerializer(
                Jackson2JsonRedisSerializer(objectMapper, Any::class.java)
            )
        )
    
    return RedisCacheManager.builder(connectionFactory)
        .cacheDefaults(defaultConfig)
        .withInitialCacheConfigurations(mapOf(
            "products" to defaultConfig.entryTtl(Duration.ofHours(1)),
            "users" to defaultConfig.entryTtl(Duration.ofMinutes(15)),
            "sessions" to defaultConfig.entryTtl(Duration.ofHours(24))
        ))
        .enableStatistics()
        .build()
}
```

### Hibernate L2 cache with Redisson

For JPA entities requiring caching:

```kotlin
@Entity
@Cacheable
@org.hibernate.annotations.Cache(
    usage = CacheConcurrencyStrategy.READ_WRITE,
    region = "productCache"
)
data class Product(
    @Id val id: Long,
    val name: String
)
```

Configure in `application.yml`:
```yaml
spring:
  jpa:
    properties:
      hibernate:
        cache:
          use_second_level_cache: true
          region.factory_class: org.redisson.hibernate.RedissonRegionFactory
```

### Week 8-9 milestones
- Study Lettuce Kotlin API documentation and Spring Data Redis reference
- Explore GitHub repos: `kasramp/spring-data-redis-example-kotlin`, `redisson/redisson-examples`
- Complete Redis University language-specific course (Java or Python path, applicable patterns transfer)
- **Practice project**: Build a complete microservice with coroutine-based Redis operations, Spring Cache abstraction with Caffeine+Redis, custom Kotlin DSL for common operations, and comprehensive integration tests

---

## Phase 5: Production deployment and operations (Weeks 10-12)

The final phase covers topology decisions, resilience patterns, and operational excellence.

### Cluster versus Sentinel topology decision

**Choose Sentinel when**: dataset fits in single node memory, HA is primary concern, simpler operations preferred. Sentinel provides automatic failover with **3+ sentinels** monitoring masters and replicas.

**Choose Cluster when**: dataset exceeds single node capacity, write scalability needed, geographic distribution required. Cluster automatically shards across **16,384 hash slots**, scaling linearly to 1000 nodes. **Critical limitation**: multi-key operations must target same slot (use hash tags: `{user}:profile`, `{user}:sessions`).

### Circuit breaker pattern with Resilience4j

Prevent cascading failures when Redis becomes unavailable:

```yaml
resilience4j:
  circuitbreaker:
    instances:
      redis-cache:
        failureRateThreshold: 50
        waitDurationInOpenState: 30s
        slidingWindowSize: 20
        permittedNumberOfCallsInHalfOpenState: 5
```

Implement graceful degradation: return stale cached data, fall back to database, or continue with reduced functionality.

### Critical metrics to monitor

| **Metric** | **Warning Threshold** | **Critical Threshold** |
|-----------|----------------------|----------------------|
| Memory utilization | >80% | >90% |
| `mem_fragmentation_ratio` | >1.5 | >2.0 |
| Cache hit rate | <85% | <70% |
| Connected clients | >80% maxclients | >90% maxclients |
| p99 latency | >5ms | >10ms |
| `evicted_keys` rate | >100/s | >1000/s |

Export metrics to **Prometheus** using redis_exporter, visualize with **Grafana** dashboards. Monitor `SLOWLOG` for commands exceeding configured thresholds.

### Memory management and eviction policies

- **`allkeys-lru`**: Default choice for caching—evicts least recently used keys when memory full
- **`allkeys-lfu`** (Redis 4.0+): Often achieves better hit rates—evicts least *frequently* used
- **`volatile-ttl`**: Only evicts keys with TTL, preserves permanent data
- **`noeviction`**: Returns errors when full—use for session stores where data loss unacceptable

Configure `maxmemory` at **75% of available RAM**, leaving headroom for operations and fragmentation. Enable `activedefrag yes` for automatic defragmentation.

### Connection configuration best practices

```yaml
spring:
  data:
    redis:
      timeout: 2000ms
      connect-timeout: 5000ms
      lettuce:
        cluster:
          refresh:
            adaptive: true
            period: 30s
        pool:
          max-active: 100
          max-idle: 50
          min-idle: 10
```

Enable TCP keepalives to detect dead connections, configure command timeouts based on your largest value sizes, and implement retry with exponential backoff for transient failures.

### Week 10-12 milestones
- Study Slack's job queue evolution (from Redis-only to Kafka+Redis hybrid)
- Review AWS ElastiCache and Azure Cache for Redis best practices documentation
- Set up Prometheus + Grafana monitoring for Redis metrics
- **Capstone project**: Deploy a complete microservices system with Redis Cluster (3 shards, 1 replica each), implement circuit breakers with fallback strategies, configure comprehensive monitoring and alerting, perform chaos engineering tests (node failures, network partitions), document runbooks for common operational scenarios

---

## Essential resources organized by phase

### Official documentation (ongoing reference)
- **redis.io/docs** — Commands reference, data structures, clustering, Lua scripting
- **Spring Data Redis Reference** — Configuration, repositories, reactive support
- **Lettuce Reference Guide** — Kotlin coroutines API, connection management

### Books
- **"Redis in Action"** (Carlson, 2013) — Foundational patterns, still relevant for data modeling
- **"Redis Stack for Application Modernization"** (Fugaro & Ortensi, 2024) — Most current, covers JSON/vector types

### Courses
- **Redis University** (free) — "Get Started with Redis", language-specific courses, Redis Streams
- **Stephen Grider's Udemy course** (4.7/5) — Comprehensive with hands-on E-commerce project

### GitHub repositories
- `redisson/redisson` — 50+ distributed data structures, locks, caches
- `kasramp/spring-data-redis-example-kotlin` — Spring Data Redis + Kotlin patterns
- `vearne/ratelimit` — Rate limiting implementations with Lua scripts

### Engineering case studies
- **Uber CacheFront** — 40M reads/second, CDC-based invalidation
- **Twitter Timeline** — 105TB RAM, sorted set fanout architecture
- **Slack Job Queue** — Redis limitations at scale, Kafka integration
- **Discord Messaging** — Pub/Sub scaling challenges and solutions

### Practice environments
- **try.redis.io** — Interactive command tutorial
- **redis.io/try/sandbox** — Command sandbox
- **KodeKloud/LabEx Playgrounds** — Full Redis environments with exercises

---

## Success indicators

By completing this curriculum, you will be able to:

- **Design data models** using optimal Redis structures for any access pattern
- **Implement distributed coordination** including locks, rate limiters, and leader election
- **Architect multi-level caching** with proper invalidation strategies for microservices
- **Write idiomatic Kotlin** with coroutines and reactive Redis
- **Deploy production clusters** with appropriate topology, monitoring, and failover handling
- **Debug performance issues** using slowlog analysis, memory profiling, and metrics correlation

The journey from basic Redis usage to mastery requires both theoretical understanding and hands-on practice with progressively complex systems. Each milestone project builds on previous knowledge, culminating in a production-grade microservices deployment that demonstrates comprehensive Redis expertise.