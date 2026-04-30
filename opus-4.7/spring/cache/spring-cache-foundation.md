---
title: "A Foundational Treatise on Spring's Cache Abstraction"
category: "Spring & Spring Boot"
description: "Ground-up, first-principles exposition of Spring's cache abstraction (Cache, CacheManager, @Cacheable contracts and where they leak) for experienced Kotlin/Spring Boot 3.x engineers — rebuilds the picture so the parts fit, enabling reasoning from contracts about any caching question."
---

# A Foundational Treatise on Spring's Cache Abstraction

*A careful, ground-up exposition for an experienced Kotlin / Spring Boot 3.x engineer*

---

## Preface: How to read this

Before we begin, a small note about pacing. You already know what a cache is. You already know what an annotation-driven proxy is. You probably already know that `@Cacheable` exists and roughly does the obvious thing. None of that is the point. The point of this essay is to *rebuild* the picture so the parts fit. By the end you should be able to look at any caching question — "why isn't this working?", "should I use Caffeine or Redis?", "why is `#result` null in my `condition`?", "why does my Kotlin service silently miss the cache?" — and answer it from first principles, by tracing the question down to the abstraction's contracts and back up.

Read it linearly. Each section assumes the previous. There are a few small "thinking questions" sprinkled in. They are not exercises with answers in the back of the book; they are nudges to pause and let the next idea install itself before you read it stated.

---

## 1. Why a cache abstraction at all

### 1.1 The recurring shape of caching code

Imagine, for a moment, that Spring did not exist. You have a method that fetches a `Book` by its ISBN from Aurora MySQL. The query takes thirty milliseconds. You look up the same ISBN forty times a second. The obvious move is to keep the answer around so you don't go to the database every time:

```kotlin
class BookService(private val repo: BookRepository) {
    private val cache = ConcurrentHashMap<ISBN, Book>()

    fun findBook(isbn: ISBN): Book {
        // 1. check the cache
        val hit = cache[isbn]
        if (hit != null) return hit
        // 2. on miss, compute
        val book = repo.findBy(isbn)
        // 3. store
        cache[isbn] = book
        // 4. return
        return book
    }
}
```

Now imagine doing this for fifty different methods. Every one of them grows a small private cache, each with its own naming, its own eviction policy (or none), its own thread-safety story, its own way of dealing with `null`. Every one of them weaves together two unrelated concerns — the *business logic* ("ask the repository for a book") and the *operational concern* ("avoid asking too often"). Now imagine your operations team asks you to switch the in-process map for Redis so that the cache is shared across the four pods running behind your ALB. You are now editing fifty methods.

That repeated shape — *check, compute on miss, store, return* — is the shape that the cache abstraction wants to lift out of your business code. It is not glamorous. It is not novel. It is, however, a textbook example of a *cross-cutting concern*: a bit of behaviour that wants to apply to many methods, all in the same way, but is not what those methods are about.

### 1.2 Why hardcoding a cache library into business code is bad

There are three independent reasons, and it is worth keeping them separate in your head.

The first is **vendor lock-in**. The day you write `Cache<ISBN, Book> cache = Caffeine.newBuilder()...build()` inside `BookService`, you have decided that this service uses Caffeine. If you later need a Redis-backed cache because the value must be visible across pods, the change is no longer a configuration change; it is an edit to every callsite that mentions Caffeine.

The second is **mixed concerns**. The body of `findBook` is now half about books and half about caching. When someone reads the method to understand what it does, they have to filter the cache plumbing out of their head. When you write a unit test, you must decide whether you are testing book-finding or cache-using. The two tests look the same.

The third is **untestable seams**. To test the caching behaviour you need to inject a fake cache. To test the business behaviour you need to bypass the cache. Both are awkward when the cache is created inline.

### 1.3 What an abstraction buys you

An abstraction in the dependency-inversion sense gives you a small interface (`Cache`, `CacheManager`) that your *framework* knows how to invoke and that your *provider* knows how to implement. The business code talks to neither directly. It talks to declarations like `@Cacheable("books")` and lets a framework component intercept the call, consult some `Cache` it found by name, and fall back to your method only on a miss.

Three things become easy. Swapping the implementation is a configuration change, because nothing in your code mentions Caffeine or Redis. Testing in isolation is easy, because you can configure the framework to use an in-memory map, or even a no-op cache, without touching production code. And the methods themselves become readable again — they describe what they compute, not how often.

### 1.4 Where the abstraction leaks (preview)

I want to be honest with you up front: the abstraction is good but it is not perfect. There is no `setTtl` on `Cache`. There is no eviction-policy enum. There are no statistics in the core API. These are deliberately absent because they vary too much across providers to model uniformly. Spring's `Cache` is the lowest common denominator: a key-value store with get/put/evict semantics. Anything richer must be configured at the provider layer. We will revisit this when we have a clearer picture; for now, just notice that the abstraction draws a careful line between "what every cache provider does the same way" and "what every cache provider does differently."

---

## 2. What the abstraction models

### 2.1 The `Cache` interface

At the centre of the abstraction sits one Java interface, in package `org.springframework.cache`. Conceptually:

```java
public interface Cache {
    String getName();
    Object getNativeCache();
    ValueWrapper get(Object key);
    <T> T get(Object key, Class<T> type);
    <T> T get(Object key, Callable<T> valueLoader);
    void put(Object key, Object value);
    ValueWrapper putIfAbsent(Object key, Object value);
    void evict(Object key);
    void clear();
    // Spring 6.1+: async/reactive hooks
    CompletableFuture<?> retrieve(Object key);
    <T> CompletableFuture<T> retrieve(Object key, Supplier<CompletableFuture<T>> valueLoader);
}
```

That is essentially it. A name, a handle to the underlying provider object (so you can do provider-specific things when you need to escape the abstraction), the four operations you'd expect on a key-value store, an `if-absent` variant, and a couple of newer asynchronous variants that we'll come back to.

You should let yourself be a little surprised by how small that is. There is no `setTtl(Duration)`. There is no `size()`. There is no `keys()`. There is no `Map<K, V>` view. Everything Spring's annotation machinery does, it does on top of these primitives.

### 2.2 The `ValueWrapper` pattern

Here is a question worth pausing on. Why does `get(key)` return a `Cache.ValueWrapper` rather than just `Object`? The interface even has a typed convenience overload `<T> T get(key, Class<T>)` that returns the bare value. So why bother wrapping?

The answer is that the abstraction needs to distinguish three states that all *look like* a null in Java:

1. The key is not in the cache at all (a cache miss).
2. The key is in the cache, mapped to the value `null` (a cached null — perhaps because the source returned `null` and we deliberately memoized that).
3. The key is in the cache, mapped to a real, non-null value.

If `get` simply returned `Object?`, states (1) and (2) would be indistinguishable. You could not tell whether you had cached a "no such record" answer or whether the cache had simply never seen the key. That is not a hypothetical concern: caching the negative result of an expensive lookup ("no, this user does not exist") is one of the most useful things a cache can do, and the framework needs a way to tell "miss" apart from "negatively cached."

So Spring returns `null` from `get` for state (1), and a `ValueWrapper` whose own `get()` returns `null` for state (2). The contract is laid out in the Javadoc almost verbatim: "Returns null if the cache contains no mapping for this key; otherwise, the cached value (which may be null itself) will be returned in a Cache.ValueWrapper."

The convenience overload `<T> T get(key, Class<T>)` *cannot* preserve this distinction — that is exactly why the Javadoc warns "this variant of get does not allow for differentiating between a cached null value and no cache entry found at all."

### 2.3 `NullValue` and `AbstractValueAdaptingCache`

Most caches you'll plug into Spring don't natively store nulls. Redis can't (a missing key and a key whose value is `nil` are not really the same thing under the hood, and the Java client wouldn't tolerate `null` in a `byte[]` payload anyway). Caffeine treats `null` as a "no value" sentinel. JCache providers vary. So how does Spring keep its "we can cache nulls" promise?

It uses a sentinel. There is a class `org.springframework.cache.support.NullValue` whose only job is to be a serializable singleton, `NullValue.INSTANCE`, that stands in for `null` on the way to the store and is translated back to `null` on the way out. The translation lives in `AbstractValueAdaptingCache`, which is the base class most provider adapters extend. Two protected methods do the work:

- `toStoreValue(userValue)` — if the value is `null` and null caching is enabled, returns `NullValue.INSTANCE`; otherwise the value as-is.
- `fromStoreValue(storeValue)` — if the value is `NullValue.INSTANCE`, returns `null`; otherwise as-is.

Each provider adapter (`RedisCache`, `CaffeineCache`, `ConcurrentMapCache`, `JCacheCache`) extends `AbstractValueAdaptingCache` and only has to implement the actual lookup against the underlying store. The null-translation is inherited.

This is the kind of detail that pays off later when you stare at a Redis instance with `redis-cli` and see what looks like a serialized Java object whose toString is `NullValue` — that's *not* a bug. That's the abstraction faithfully storing your cached null.

### 2.4 The `CacheManager` as a registry of named caches

The next interface up is `org.springframework.cache.CacheManager`:

```java
public interface CacheManager {
    Cache getCache(String name);
    Collection<String> getCacheNames();
}
```

A `CacheManager` is just a registry. You ask it for a cache by name and it gives you a `Cache`. Spring's annotation-driven machinery does exactly that — when it sees `@Cacheable("books")` it asks the manager for a cache called `"books"` and operates on it.

You may be asking — and this is exactly the kind of question I want you to ask — *isn't this just a `Map<String, Cache>`?* Couldn't we have skipped the indirection? Two reasons we couldn't.

First, **lazy creation**. Many providers create caches on demand. The first time someone asks Caffeine's adapter for a cache called `"users"`, the adapter spins it up using whatever default `CaffeineSpec` is configured. A bare map can't do that.

Second, and more importantly, **cache names are the unit of configuration**. Per-cache TTL, per-cache size, per-cache serializers — all of it hangs off the name. When Spring Data Redis builds a `RedisCacheManager` it accepts a `Map<String, RedisCacheConfiguration>` mapping each cache name to its own configuration; cache names not in that map fall back to a default configuration. When Caffeine's `CaffeineCacheManager` is configured with `spring.cache.cache-names=books,authors`, those two names get pre-created with the default spec. The `CacheManager` is *the* place where "the operational concerns of this cache" are bound to "this name", which is the only thing your business code knows about.

That is also why you should think carefully when you pick cache names. `"books"` is a thing whose TTL, size, eviction, and serialization can be set as a unit. If you have one cache for "popular books" with a one-hour TTL and another for "rare books" with a one-week TTL, those should be different cache *names*, even if they ultimately live in the same Redis instance.

### 2.5 The `retrieve(...)` async variant

In Spring Framework 6.1, the `Cache` interface gained two new methods, `retrieve(key)` and `retrieve(key, Supplier<CompletableFuture<T>>)`, with default implementations that throw `UnsupportedOperationException`. Providers may opt in. The motivation is reactive integration: when the cached method returns a `Mono<Book>` or a `CompletableFuture<Book>`, the abstraction needs a way to talk to the cache without blocking the calling thread on `get(...)`. With `retrieve` it can chain a non-blocking lookup onto the same async pipeline. Caffeine's adapter implements it via `AsyncCache`; Redis Cache implements it where the underlying Lettuce client already speaks reactively.

For day-to-day Kotlin coroutines code this matters mostly because, as of 6.1, `@Cacheable` understands `CompletableFuture` and reactive return types and adapts accordingly — you can write an annotated reactive method without the cache itself becoming a blocking dam in the middle of your pipeline, *provided* the cache implementation supports `retrieve`.

### 2.6 `CacheResolver` — when cache name is dynamic

There is one more abstraction that tends to surprise people on first encounter: `CacheResolver`. It exists because sometimes the name of the cache to consult depends on the call itself, not on a static annotation attribute. Maybe tenant `acme` and tenant `globex` should write to physically separate caches; maybe production and staging share the codebase but hit different cache regions; maybe you have several `CacheManager` beans and need to choose between them per call.

The default `CacheResolver` (a `SimpleCacheResolver`) is uninteresting: it takes the cache names from the annotation and resolves them against the configured `CacheManager`. But you can write your own and reference it via the `cacheResolver` attribute on `@Cacheable`/`@CachePut`/`@CacheEvict`. The resolution happens *for every cache operation* and has access to a `CacheOperationInvocationContext` that includes the target object and arguments — i.e. you have everything you need to compute a cache name at runtime. For a tenant-aware system this is the cleanest place to put the logic.

A small but useful gotcha: `cacheManager` and `cacheResolver` are mutually exclusive on the annotations. If you set both, the framework throws — but the surprise is that a custom `CacheResolver` *ignores* a `cacheManager` because the resolver is presumed to handle resolution wholesale.

---

## 3. How you use it: the annotations

We now have the model. The model is a `CacheManager` registry of named `Cache` objects, each of which is a small key-value store with null-aware semantics. Everything else is *how Spring uses that model on your behalf when you annotate methods*.

### 3.1 Switching it on: `@EnableCaching`

Spring does nothing automatic with cache annotations until something turns the feature on. In a Spring Boot app, that something is `@EnableCaching`, conventionally placed on a `@Configuration` class:

```kotlin
@Configuration
@EnableCaching
class CachingConfig
```

A common piece of advice — and one I'd echo for a Kotlin/Boot 3.x codebase — is *not* to put `@EnableCaching` on the main `@SpringBootApplication` class. If you do, every test slice that loads the application class will load caching too, even slices that don't want it (and slices that don't want it will then fail, because `@EnableCaching` expects a `CacheManager` to exist). Putting it on a dedicated `@Configuration` class lets you exclude that class from a test's configuration and run cache-free.

`@EnableCaching` does just one thing: it imports `CachingConfigurationSelector`, which (as we'll see in §4) decides which infrastructure to register. You don't need to know that yet. You just need to know that without `@EnableCaching`, all your other annotations are inert decorations.

### 3.2 `@Cacheable`: memoize this method

`@Cacheable` is the workhorse. Conceptually: "before invoking the method, check the named cache for a value under a key derived from the arguments; if there's a hit, return that and skip the body; if not, run the body and store its return value in the cache."

```kotlin
@Cacheable(cacheNames = ["books"], key = "#isbn")
fun findBook(isbn: String, includeUsed: Boolean): Book = repo.findByIsbn(isbn)
```

Let's walk every attribute, because every one is a real lever you'll reach for at some point.

**`cacheNames`** (alias `value`) — the names to consult. If you supply more than one (`["popular", "books"]`), Spring consults them in order on the read side and writes the new value to *all* of them on a miss. This is rarely what you want for normal application caching; it's a feature aimed at tiered storage scenarios. Most of the time supply exactly one name.

**`key`** — a SpEL expression that produces the cache key. If omitted, the configured `KeyGenerator` is used (more on that shortly). If you write `key = "#isbn"`, the SpEL evaluates the expression in a context where the method's parameters are available by name. We will dwell on the SpEL context in §3.7 because misunderstanding it is the single most common source of "but it should be hitting!" tickets.

**`condition`** — a SpEL expression that, if it evaluates to false, *suppresses* the entire caching behaviour: the body runs as if `@Cacheable` weren't there. Evaluated *before* the method invocation, so `#result` is not available. Typical use: `condition = "#size < 100"` to skip caching pathological inputs.

**`unless`** — a SpEL expression that, if it evaluates to true, *suppresses storing* the result into the cache (but the body still runs and the value is returned to the caller). Evaluated *after* the method invocation, so `#result` *is* available. This is how you do negative-caching control: `unless = "#result == null"` means "compute and return, but don't memoize the null."

The pairing is worth committing to memory. **`condition` runs before, `unless` runs after.** `condition` controls "do we engage the cache at all?", `unless` controls "given we engaged, do we store the answer?" If you keep that distinction clear, half the SpEL questions answer themselves.

**`sync`** — boolean, default false. With `sync = true`, the cache layer asks the provider to lock the entry while the value is being computed, so that simultaneous misses for the same key compute *once* and the rest wait. This is the right choice for expensive cold-start computations where stampeding-herd is a real concern. Without it, the abstraction does no synchronization — if ten threads miss simultaneously, all ten run the method. As of Spring 6.1, `sync = true` even works with `CompletableFuture` and reactive return types, provided you've configured your cache for async mode (e.g. `caffeineCacheManager.setAsyncCacheMode(true)`).

**`keyGenerator`** — bean name of a custom `KeyGenerator` to use for this method instead of the default. Mutually exclusive with `key`.

**`cacheManager`** — bean name of a custom `CacheManager`. Useful when you have several (Caffeine for hot local stuff, Redis for shared stuff). Mutually exclusive with `cacheResolver`.

**`cacheResolver`** — bean name of a custom `CacheResolver` (see §2.6).

### 3.3 `@CachePut`: always invoke and update

`@CachePut` is `@Cacheable`'s twin and a frequent source of confusion because the names sound similar. The contract is opposite: `@CachePut` *always* runs the method and stores the return value into the cache. It never short-circuits.

The use case is "an update happened — refresh the cache." You have a method that updates a `Book` in the database, and you want the cache to reflect the new state immediately:

```kotlin
@CachePut(cacheNames = ["books"], key = "#book.isbn")
fun updateBook(book: Book): Book = repo.save(book)
```

Note that here `#result` *is* available in `unless`, because the method always runs.

The reference documentation explicitly warns against using `@Cacheable` and `@CachePut` on the same method. They have different policies on whether the method runs, and the combined behaviour is rarely what anyone expects.

### 3.4 `@CacheEvict`: invalidate

`@CacheEvict` removes one entry, or all entries, from a named cache:

```kotlin
@CacheEvict(cacheNames = ["books"], key = "#isbn")
fun deleteBook(isbn: String) { repo.deleteByIsbn(isbn) }

@CacheEvict(cacheNames = ["books"], allEntries = true)
fun reloadAllBooks() { /* full refresh */ }
```

Two attributes are worth dwelling on.

**`allEntries`** — when true, the framework ignores `key` entirely and clears the whole cache. The Javadoc puts it concisely: "this option comes in handy when an entire cache region needs to be cleared out — rather than evicting each entry (which would take a long time, since it is inefficient), all the entries are removed in one operation." Useful for batch jobs that change many things at once.

**`beforeInvocation`** — when false (the default), eviction runs *after* the method completes successfully; if the method throws, the cache is left alone. When true, eviction runs *before* the method, unconditionally. The default is correct most of the time: you don't want to evict the cache for a delete that then throws a `DataIntegrityViolationException`. The `beforeInvocation = true` case shows up when the eviction is purely defensive — e.g., "before recomputing, drop any stale entries" — and you want the eviction to happen regardless of method outcome.

### 3.5 `@Caching`: composing operations

Sometimes one method legitimately needs more than one cache operation. Maybe saving a `Book` should put into a `byIsbn` cache and evict from a `byAuthor` cache (because the count for that author may have changed). For that you compose:

```kotlin
@Caching(
    put   = [CachePut(cacheNames = ["booksByIsbn"],    key = "#book.isbn")],
    evict = [CacheEvict(cacheNames = ["booksByAuthor"], key = "#book.author")]
)
fun saveBook(book: Book): Book = repo.save(book)
```

`@Caching` is just a bag — it's used when a single Spring annotation (`@Cacheable`, `@CachePut`, `@CacheEvict`) is not enough because you need multiple of the same kind, or because you need a mix.

### 3.6 `@CacheConfig`: shared class-level defaults

When every method on a class operates on the same cache, repeating `cacheNames = ["books"]` on each method gets tedious. `@CacheConfig` lifts shared attributes to the class level:

```kotlin
@Service
@CacheConfig(cacheNames = ["books"])
class BookService {
    @Cacheable(key = "#isbn")
    fun findBook(isbn: String): Book = ...

    @CacheEvict(key = "#isbn")
    fun deleteBook(isbn: String): Unit = ...
}
```

`@CacheConfig` does *not* turn on caching for every method (a common misconception). It just supplies defaults — `cacheNames`, `keyGenerator`, `cacheManager`, `cacheResolver` — that the actual operation annotations can inherit. A method without `@Cacheable`, `@CachePut`, or `@CacheEvict` is still uncached.

### 3.7 SpEL: the evaluation context

This is the section that, if you read it once carefully, will save you an embarrassing number of debugging hours.

When Spring evaluates a `key`, `condition`, or `unless` expression, it builds a `CacheEvaluationContext` (which extends `MethodBasedEvaluationContext`, which in turn extends the SpEL `StandardEvaluationContext`). Inside this context, four kinds of references are available:

- **The `#root` object**, which exposes the method invocation. Specifically, `#root.method` is the `java.lang.reflect.Method`, `#root.target` is the instance whose method is being invoked, `#root.args` is the `Object[]` of arguments, `#root.caches` is the collection of `Cache` objects involved, `#root.methodName` and `#root.targetClass` are convenient shortcuts.
- **Positional argument variables** `#a0`, `#a1`, ..., `#aN` and aliases `#p0`, `#p1`, ..., `#pN`. These are *always* available, regardless of whether parameter names are preserved at compile time. Use them when you must work without parameter metadata.
- **Named argument variables** `#isbn`, `#user`, etc. These exist *only if* the parameter names are discoverable at runtime. For Java that means compiling with `-parameters`. For Kotlin it means having the Kotlin metadata in the bytecode (the default for any normal Spring Boot project — the kotlin-spring plugin handles this).
- **`#result`** — the return value of the method. *Only available* in `unless` (always evaluated after the call) and in `@CachePut`'s and `@CacheEvict`'s `key` and `condition` when `beforeInvocation = false`. It is *not* available in a `@Cacheable` `condition` or a `@Cacheable` `key`, because those evaluate before the method runs and there is, by construction, no result yet.

Here's the timing picture, which I find easier to remember as a story than as a table. When the proxy intercepts a call to a cacheable method, it does this in order:

1. Pre-invocation evictions (`@CacheEvict` with `beforeInvocation = true`) run. Their SpEL evaluates without `#result`.
2. For `@Cacheable` operations, `condition` is evaluated. If false, skip caching entirely. Otherwise, the key is computed and the cache is consulted. On a hit, the cached value is returned and the method body never runs.
3. On a miss (or for `@CachePut`, always), the method body runs.
4. Post-invocation evictions (`@CacheEvict` with `beforeInvocation = false`) run. Their SpEL now has `#result`.
5. For `@Cacheable` (on miss) and `@CachePut`, `unless` is evaluated; if false, the result is stored. Both have `#result`.

Now you see why it's not arbitrary that `condition` runs before and `unless` after. `condition` is "should we even try the cache?", which has to be answerable before the call. `unless` is "given that we got a result, should we cache it?", which is naturally answered after.

A concrete failure mode that this clarifies: people sometimes write `@Cacheable(condition = "#result != null")` and wonder why they get a `SpelEvaluationException`. The answer is that `#result` does not exist in `condition` for `@Cacheable`. They wanted `unless = "#result == null"`. The expressions are very nearly opposite — `condition` is a permission, `unless` is a veto.

### 3.8 The default `KeyGenerator` — and its famous bug

If you don't supply `key`, Spring delegates to a `KeyGenerator`. The default is `SimpleKeyGenerator`. Its source is short enough to read in full:

```java
public Object generate(Object target, Method method, Object... params) {
    return generateKey((KotlinDetector.isSuspendingFunction(method) ?
            Arrays.copyOf(params, params.length - 1) : params));
}

public static Object generateKey(Object... params) {
    if (params.length == 0) {
        return SimpleKey.EMPTY;
    }
    if (params.length == 1) {
        Object param = params[0];
        if (param != null && !param.getClass().isArray()) {
            return param;
        }
    }
    return new SimpleKey(params);
}
```

Three things to notice. First: if the method takes a single non-null, non-array argument, *that argument itself is the key*. This is fine for `findBookByIsbn(isbn)` — the ISBN is the key, no wrapping. Second: for zero or multiple arguments, a `SimpleKey` is constructed from the arguments. `SimpleKey` is essentially `Arrays.deepHashCode(params)` plus a stored copy of `params` for equality. Third: the Kotlin-coroutines line strips the trailing `Continuation` parameter that the Kotlin compiler appends to `suspend` functions — without that, two calls with identical arguments would produce different keys because `Continuation` instances are not equal across invocations.

Now, the famous bug. `SimpleKeyGenerator` does *not* include the `target` or `method` in the key. That means that if you have two methods `findById(Long)` on two different services, both annotated `@Cacheable(cacheNames = ["entities"])`, with no explicit `key`, and you call both with `1L`, they collide. Both write to the same cache slot. You get cross-method pollution. Worse, if the two methods have different return types, you'll get a `ClassCastException` on the second call.

The reference documentation warns about this with notable emphasis: "the default strategy might work for some methods, it rarely works for all methods... this is the recommended approach over the default generator, since methods tend to be quite different in signatures as the code base grows." The fix in practice is one of two things. Either give every cache operation an explicit `key` and an explicit, *narrow* cacheName — `@Cacheable(cacheNames = ["bookByIsbn"], key = "#isbn")` — so cross-method collisions are impossible by construction. Or write a custom `KeyGenerator` that incorporates the method (Marschall has an oft-cited blog showing one). The first option is what most production codebases settle on, because per-cache configuration (TTL, size) wants distinct cache names anyway.

### 3.9 When to *not* use the annotations

The annotations are wonderful for the canonical case: an injected service whose public method should memoize. They are not always the right tool. Two situations call for going programmatic and using `cacheManager.getCache(name)` directly.

The first is **dynamic cache logic** that the SpEL grammar can't express comfortably. If your cache key needs three database lookups to compute, you don't want that in a `key` SpEL expression — it'll be evaluated every call, including hits. You want to compute it explicitly and check the cache yourself.

The second, increasingly important in a Kotlin/Spring 3.x codebase, is **coroutines and reactive code with edge-case requirements**. The annotation machinery has been steadily improved for `suspend` and `Mono`/`Flux`, but the moment you need to do something subtle — e.g. cache only one element of a stream, or interact with the cache from inside a coroutine flow — directly invoking `cache.get(...)` and `cache.put(...)` is clearer than fighting the annotation. The abstraction's `Cache` interface is perfectly nice to call by hand.

There is a small but important footnote here: when you go programmatic, you give up the proxy-based interception machinery (§4) but you keep all the rest of the abstraction — provider portability, named caches, null handling. You still get the Caffeine/Redis swap for free.

---

## 4. How it works under the hood

We now turn the lens around. Everything in §3 is what you write. Let's trace what Spring does with what you wrote, starting from the moment `@EnableCaching` enters the picture and ending in a method call. This section is "useful-to-know" — you don't need it to use the abstraction, but you'll diagnose problems much faster if you've internalised it.

### 4.1 Bootstrapping: from `@EnableCaching` to advisor

`@EnableCaching` is just an `@Import(CachingConfigurationSelector.class)`. `CachingConfigurationSelector` extends `AdviceModeImportSelector<EnableCaching>`. Its only job is to decide, at configuration time, which infrastructure beans to register, based on the `mode` attribute (`PROXY` by default, `ASPECTJ` for compile-/load-time weaving) and on whether JSR-107 is on the classpath.

In the default `PROXY` mode, it imports `AutoProxyRegistrar` (which registers an auto-proxy creator if none is present) and `ProxyCachingConfiguration`. If JSR-107 is on the classpath it additionally imports `ProxyJCacheConfiguration`.

`ProxyCachingConfiguration` is a tiny `@Configuration` class. It registers three beans:

- An `AnnotationCacheOperationSource`, which knows how to look at a method, find `@Cacheable`/`@CachePut`/`@CacheEvict`/`@Caching` annotations on it, and parse them into a `Collection<CacheOperation>` (one of `CacheableOperation`, `CachePutOperation`, `CacheEvictOperation`). The actual parsing is delegated to a `SpringCacheAnnotationParser`.
- A `CacheInterceptor`, which is the AOP `MethodInterceptor` that handles the runtime work. It inherits most of its logic from `CacheAspectSupport`.
- A `BeanFactoryCacheOperationSourceAdvisor`, which is the AOP advisor that pairs the operation source's pointcut with the interceptor's advice.

When the application context comes up, the auto-proxy creator (`AbstractAutoProxyCreator`) sees the advisor, asks its pointcut "does method `X` of bean `Y` apply?", and that pointcut asks the `CacheOperationSource` "does this method have any cache annotations?" If yes, the bean gets wrapped in a proxy (a JDK dynamic proxy if the target implements interfaces, or a CGLIB subclass otherwise) whose calls flow through the `CacheInterceptor`.

### 4.2 At runtime: a single annotated call, traced

Imagine your controller calls `bookService.findBook("978-...")`. Here is what physically happens:

1. The `bookService` reference your controller holds is *not* the original `BookService` bean. It is a proxy. The call `findBook("978-...")` is dispatched against the proxy.
2. The proxy routes the call into Spring AOP's `ReflectiveMethodInvocation`, which walks an interceptor chain. For a cached method, that chain contains the `CacheInterceptor`.
3. `CacheInterceptor.invoke(invocation)` calls the inherited `CacheAspectSupport.execute(...)`. This is the heart of the runtime.
4. `execute` first asks the `CacheOperationSource` for the operations on this method (a list of `CacheableOperation`/`CachePutOperation`/`CacheEvictOperation`). That lookup is cached itself, keyed by method+target class, so it's cheap after the first call.
5. It builds a `CacheOperationContexts` aggregating all those operations with the actual target/method/args.
6. It runs **before-invocation evicts** (any `@CacheEvict` with `beforeInvocation = true`).
7. If there are `@Cacheable` operations and no `@CachePut` operations, it tries to find a cached value: for each cacheable operation, evaluate `condition`, generate the key (via SpEL or `KeyGenerator`), consult the resolved caches in order, return the first non-null `ValueWrapper`'s value as the result.
8. If a hit was found, it skips the method invocation and proceeds to step 11. Otherwise:
9. The method body actually runs (`invokeOperation(invoker)`), producing a result (or throwing).
10. The `@CachePut` operations are queued as "puts" and (assuming no exception) are applied; the `@Cacheable` operations whose miss triggered the invocation also queue puts to populate the cache, gated by their `unless`.
11. **After-invocation evicts** (`@CacheEvict` with `beforeInvocation = false`) run.
12. The result is returned to the caller.

The exact flow has been refined over Spring versions but this skeleton has been stable since 4.x. The shape — pre-evicts, find-cached, invoke, queue-puts, post-evicts — is what you should picture when reasoning about ordering.

### 4.3 The SpEL evaluation context, materialised

Earlier (§3.7) I described the SpEL context abstractly. Here is what actually happens. For each operation that needs SpEL, `CacheOperationExpressionEvaluator` builds a `CacheEvaluationContext`. The context is constructed with a root object that exposes `method`, `target`, `args`, `caches`, plus a lazy `ParameterNameDiscoverer` that resolves `#paramName` references on demand. The `#aN`/`#pN` aliases are supplied by `MethodBasedEvaluationContext`. The `#result` variable is *added* to the context post-invocation, so the same context is re-used and simply gains a new variable. There is also a notion of "unavailable variables" — if you try to use `#result` in a `@Cacheable` `condition`, the context throws explicitly rather than silently evaluating to null.

The lazy parameter-name resolution is a small performance optimisation: parameter names require classfile parsing, and most expressions don't use them, so the parsing is deferred until you actually write `#isbn` and not `#a0`.

### 4.4 The self-invocation issue

This is the gotcha that bites everyone exactly once. Cache annotations are processed by a *proxy*. The proxy intercepts calls *coming in from outside*. Calls *from one method of a bean to another method of the same bean* go through `this` — they never touch the proxy. Concretely:

```kotlin
@Service
class BookService(private val repo: BookRepository) {
    fun handle(req: Request): Book {
        // This call is on `this`, not the proxy.
        // The @Cacheable on findBook is bypassed completely.
        return findBook(req.isbn)
    }

    @Cacheable("books")
    fun findBook(isbn: String): Book = repo.findByIsbn(isbn)
}
```

`handle` calls `findBook` directly. The cache is never consulted. The body runs every time. There is no warning. This is the same gotcha as `@Transactional`, and for the same reason — both rely on AOP proxies, and both cannot intercept what they don't see.

There are three honest ways out. You can split the methods across two beans, so the call genuinely crosses a proxy boundary. You can inject the bean into itself (Spring 4.3+ allows `@Autowired private lateinit var self: BookService`) and call `self.findBook(...)`. Or you can switch to AspectJ load-time weaving (`@EnableCaching(mode = AdviceMode.ASPECTJ)`), which weaves the advice into the bytecode and so works for self-invocations too. The third option pays an operational tax — agent-based weaving complicates deployment, especially on EKS where you'd need to mind the JVM agent flags — and is rarely worth it for caching alone.

The first option, splitting into separate beans, is what production codebases reach for in practice. It also produces cleaner architectural seams.

### 4.5 CGLIB vs JDK proxy, and the Kotlin angle

Spring's auto-proxy creator picks a proxy strategy based on whether the target bean implements interfaces. If it does, JDK dynamic proxies (which proxy the interface) are used. If it doesn't, CGLIB generates a runtime subclass that overrides each method. Spring Boot defaults to CGLIB across the board (`spring.aop.proxy-target-class=true`) because it's more uniform.

This is where Kotlin gets interesting. By default, Kotlin classes and methods are `final`. CGLIB generates a *subclass*. You cannot subclass a final class or override a final method. Without intervention, every `@Service`-annotated Kotlin class would refuse to be proxied, and every cache annotation would be silently inert (or, depending on Spring version and configuration, would fail at startup).

The `kotlin-spring` compiler plugin solves this by automatically opening — that is, removing the implicit `final` from — classes annotated with any of `@Component`, `@Async`, `@Transactional`, `@Cacheable`, `@SpringBootTest` (and meta-annotations such as `@Service`, `@Repository`, `@Controller`, which are themselves annotated with `@Component`). The `start.spring.io`-generated Kotlin starter has this plugin enabled by default, which is why most Spring Boot Kotlin applications never have to think about this.

But it is worth knowing, because two related problems trip people up. First, if you write a custom annotation that *applies* a cache annotation as a meta-annotation, the `kotlin-spring` plugin will not necessarily open classes annotated with your custom annotation; you may need to add it to the `all-open` plugin list. Second, if you cache methods on a Kotlin data class or any class that's not a `@Component`-stereotype, you may need explicit `open` modifiers. The error messages in these cases are blunt — "Cannot subclass final class ..." — but the cause is now obvious.

### 4.6 Why ASPECTJ mode is rarely worth it

`@EnableCaching` accepts `mode = AdviceMode.ASPECTJ`, which switches from proxy-based interception to compile-time or load-time weaving via AspectJ. This sidesteps both the self-invocation issue and the final-method issue. So why not always use it?

Because it brings real operational cost. Compile-time weaving requires AspectJ in the build pipeline. Load-time weaving requires a JVM agent or a custom `LoadTimeWeaver`, which interacts with class loaders and other agents in subtle ways — e.g., on ECS or EKS, you have to mind the JVM start command. You also lose the ability to easily disable caching by removing one configuration line, which is a debuggability superpower. For 95% of applications, the proxy approach is fine, and the self-invocation issue is best handled by structuring the code so it doesn't arise.

---

## 5. How Spring Boot wires it all for you

Now we have the framework picture. Spring Boot's auto-configuration takes that picture and removes the manual wiring.

### 5.1 The starter

Adding `org.springframework.boot:spring-boot-starter-cache` does two things. It pulls in `spring-context` (which contains the cache abstraction itself, including `CacheAspectSupport`, `CacheInterceptor`, and `ConcurrentMapCacheManager`) and `spring-context-support` (which adds JCache and EhCache support). It also makes `CacheAutoConfiguration` available on the classpath, where Spring Boot's auto-configuration scanner picks it up.

### 5.2 The condition for activation

`CacheAutoConfiguration` declares (paraphrased to current versions): `@ConditionalOnClass(CacheManager.class)`, `@ConditionalOnBean(CacheAspectSupport.class)`, `@ConditionalOnMissingBean(value = CacheManager.class, name = "cacheResolver")`, and `@EnableConfigurationProperties(CacheProperties.class)`. The middle two are the key. The `@ConditionalOnBean(CacheAspectSupport.class)` is satisfied only when something in the context has registered `CacheAspectSupport` — which is exactly what `@EnableCaching` does (via `ProxyCachingConfiguration`'s `CacheInterceptor` bean, which extends `CacheAspectSupport`). And the `@ConditionalOnMissingBean` clause means: if you've already supplied your own `CacheManager` bean, Boot stays out of the way.

In other words: *just having `spring-boot-starter-cache` on the classpath does nothing*. You opt in with `@EnableCaching`. This was a deliberate design choice — Stéphane Nicoll's GitHub thread on caching auto-configuration says it explicitly: "we need this thing to be opt-in, as the mere presence of a caching library in the classpath is no good reason to enable it."

### 5.3 The provider-detection cascade

When `CacheAutoConfiguration` is active and you haven't defined your own `CacheManager`, Boot needs to pick one. It does so via a sub-class `CacheConfigurationImportSelector` that conditionally imports one of several provider configurations from `org.springframework.boot.autoconfigure.cache`. The order in current Spring Boot is:

1. **Generic** — used if the context defines at least one bean of type `org.springframework.cache.Cache`. Boot wraps them in a `SimpleCacheManager`.
2. **JCache (JSR-107)** — used if a `javax.cache.spi.CachingProvider` is on the classpath. Covers EhCache 3, Hazelcast, Infinispan, and other JSR-107 implementations.
3. **Hazelcast** — used if a `HazelcastInstance` has been auto-configured and `com.hazelcast:hazelcast-spring` is on the classpath.
4. **Infinispan** — used if Infinispan is on the classpath, with explicit configuration.
5. **Couchbase** — used if Couchbase is configured.
6. **Redis** — used if a `RedisConnectionFactory` is auto-configured (which Spring Data Redis with Lettuce will do).
7. **Caffeine** — used if Caffeine is on the classpath.
8. **Cache2k** — used if Cache2k's Spring integration is on the classpath.
9. **Simple** — the fallback. Uses `ConcurrentMapCacheManager`, an in-memory `ConcurrentHashMap` per cache name. Not recommended for production but lovely for tests and getting started.

The first match wins. You can override the choice with `spring.cache.type=redis` (or `caffeine`, `simple`, `none`, etc.). Given typical modern stacks, the most common situation is "Redis is auto-configured for session/data and Caffeine is also on the classpath." Without `spring.cache.type` set, Redis wins because it appears earlier in the cascade. This is a frequent surprise, especially because both are valid — you usually want one *or* the other, or both behind a `CacheResolver` that decides per cache name.

### 5.4 Predefining caches and customising

Two property knobs handle most of what you'll ever configure:

```properties
# Predeclare cache names; useful when the provider creates them eagerly
spring.cache.cache-names=books,authors,reviews

# Force a particular provider (rarely needed, but unambiguous)
spring.cache.type=redis
```

Predeclaring `spring.cache.cache-names` does subtly different things per provider. For Caffeine it eagerly creates the named caches with the default spec; if you ask for an undeclared name at runtime, the manager fails. For Redis the same logic applies. For the simple `ConcurrentMapCacheManager`, declaring names *restricts* which caches can exist; without the declaration, caches are created lazily on first use.

For finer-grained customization, Spring Boot offers `CacheManagerCustomizer<T>` beans. Boot's `CacheAutoConfiguration` invokes any such bean it finds with the auto-configured `CacheManager` *before* the manager is fully initialized:

```kotlin
@Bean
fun caffeineCustomizer() = CacheManagerCustomizer<CaffeineCacheManager> { mgr ->
    mgr.setAllowNullValues(false)
}
```

There are provider-specific variants too — `RedisCacheManagerBuilderCustomizer` and `CaffeineCacheManagerCustomizer` — that hook in earlier in the construction process and let you tweak the *builder* before the manager is built. Use these when you need to set things that are immutable on the finished manager (e.g. per-cache `RedisCacheConfiguration` overrides).

### 5.5 Provider-specific properties

For Caffeine:

```properties
spring.cache.cache-names=books,authors
spring.cache.caffeine.spec=maximumSize=500,expireAfterAccess=600s
```

The `caffeine.spec` accepts the standard Caffeine string DSL, parsed by `CaffeineSpec.parse(...)`. Alternatively you can declare a `Caffeine` or `CaffeineSpec` bean for programmatic configuration; the bean wins over `caffeine.spec`. If a `CacheLoader<Object, Object>` bean is on the classpath, Boot wires it into the `CaffeineCacheManager`.

For Redis:

```properties
spring.cache.redis.time-to-live=10m
spring.cache.redis.key-prefix=my-app:
spring.cache.redis.use-key-prefix=true
spring.cache.redis.cache-null-values=true
spring.cache.redis.enable-statistics=false
```

These configure the *default* `RedisCacheConfiguration` that the auto-configured `RedisCacheManager` applies to every cache name. Per-cache overrides require a `RedisCacheManagerBuilderCustomizer` bean that calls `withCacheConfiguration("books", customConfig)` on the builder. There is a long-standing GitHub issue requesting native property-based per-cache configuration; until that lands, the customizer is the canonical answer.

### 5.6 RedisCacheManager: the `RedisCacheWriter` trade-off

`RedisCacheManager` defers per-cache configuration to `RedisCacheConfiguration`, which holds: a TTL (or a `TtlFunction` for per-entry TTL, since Spring Data Redis 3.2), key prefix logic, key serializer (default: `StringRedisSerializer`), value serializer (default: `JdkSerializationRedisSerializer` — usually you'll want `GenericJackson2JsonRedisSerializer` instead for inspectability and language portability), and `cacheNullValues` flag.

Underneath, the manager uses a `RedisCacheWriter`. There are two flavours, and the choice is a real trade-off:

- **Lock-free** (`RedisCacheWriter.nonLockingRedisCacheWriter(...)`, the default). Higher throughput. The trade-off is that `putIfAbsent` and `clean` are not atomic — they require a get followed by a set, with no synchronization, so a concurrent writer could slip in between. For most caching workloads this is fine, because the failure mode is "two writers compute the same value and the second overwrites the first" rather than data loss.
- **Locking** (`RedisCacheWriter.lockingRedisCacheWriter(...)`). The writer takes an explicit lock key in Redis before performing operations that would otherwise race. This makes `putIfAbsent` truly atomic at the cost of additional round-trips and potential wait time. Useful only if you actually depend on `putIfAbsent` semantics — typically not for vanilla `@Cacheable` use.

The default — lock-free — is correct for the vast majority of `@Cacheable`-driven caches. The locking variant exists for the rare case where you'd otherwise need a distributed lock anyway.

A second worthwhile tweak: `RedisCacheWriter` defaults to using `KEYS` + `DEL` to clear a cache. On Aurora-scale deployments (or ElastiCache Redis with millions of keys), `KEYS` is operationally hostile — it scans the whole keyspace synchronously. A SCAN-based batch strategy is available: `BatchStrategies.scan(1000)`. For any production deployment, set this; for development, the default is fine.

---

## 6. The provider landscape, briefly

We've tunnelled through a lot of internals. Step back. What providers actually exist, and roughly when do you reach for which?

In-process providers live entirely inside the JVM, sharing nothing across pods. They're cheap, they're fast (microseconds), and they're appropriate for data that's read-mostly per pod or that's tolerant of cache divergence between pods. The contenders:

- `ConcurrentMapCache` is built into the framework. Useful for tests and trivial cases. Has no eviction. Not for production at any scale.
- **Caffeine** is the modern in-process default. It implements the W-TinyLfu eviction policy — a hybrid of a small LRU admission window in front of a Segmented LRU main space, gated by a frequency sketch (a 4-bit CountMinSketch) that tracks historic usage. The hill-climbing tuner adjusts the window/main split based on observed hit rate. You don't need to know any of that to use it; you do need to know that its hit rate is near-optimal across a remarkable variety of workloads, which is why everyone has been migrating from Guava and Ehcache 2 to Caffeine for a decade. Configured via `spring.cache.caffeine.spec` or a `Caffeine`/`CaffeineSpec` bean.
- **Cache2k** is another modern in-process option, smaller and arguably simpler than Caffeine, with very predictable behaviour. Less common.
- **EhCache 3** speaks JCache and so plugs in via the JSR-107 path. It can do disk overflow, which Caffeine cannot, so it's the choice when you specifically need a tiered local cache with disk persistence.

Distributed providers live outside the JVM and are visible to all pods sharing the connection. The latency is in milliseconds rather than microseconds, but the data is consistent across the fleet, which matters for things like session state, rate-limit counters, or anything user-visible that must not differ between pods.

- **Redis via Spring Data Redis** is the workhorse for AWS-deployed Spring applications. Lettuce (the default Spring Data Redis client) is non-blocking and works well with reactive code. ElastiCache or MemoryDB on AWS are operationally turnkey. The serialization story (JDK vs JSON) and key-prefix policy are the two things you'll pick deliberately.
- **Hazelcast** can run in two topologies: embedded (every pod is a cluster member, low latency but every pod holds data) and client-server (a separate Hazelcast cluster, lower per-pod overhead). The embedded mode is unusual on EKS because pods come and go more often than a cluster wants them to.
- **Infinispan** and **Couchbase** are less common in the Spring Boot world but well-supported.

JCache (JSR-107) is the *unifying spec*. Spring's JCache integration in `spring-context-support` lets you use any JSR-107-compliant provider through a uniform configuration, and (since Spring 4.1) it also supports the JSR-107 annotations (`@CacheResult`, `@CacheRemove`, `@CacheRemoveAll`) backed by Spring's own cache abstraction. The principal benefit is portability across compliant providers; the principal cost is one more layer of indirection.

The detailed "when to pick which" trade-offs belong to the playbook artifact you already have. The thumbnail rule is: *Caffeine for hot per-pod state, Redis for shared state, both behind a `CacheResolver` if you need both.*

---

## 7. The contract Spring Cache does *not* model

I promised in §1 that the abstraction leaks, and that we'd come back to it once you had the model. Now we do.

The `Cache` interface has no `setTtl`, no `getStats`, no `keys()`, no eviction-policy enum, and only the most basic atomic operation (`putIfAbsent`). Why?

Because *every cache provider does these differently*, and trying to unify them would either drop to a useless lowest common denominator or impose semantics that some providers can't honor. TTL on Caffeine is `expireAfterWrite`/`expireAfterAccess`/`expireAfter` (a custom `Expiry` policy). TTL on Redis is a key-level expiration set via `EXPIRE` or `SET EX`. TTL on Hazelcast can be configured per-map or per-entry. TTL on JCache is `ExpiryPolicy`. The names of the parameters differ, the *semantics* of "access" differ, and the granularities differ. A single `Duration setTtl(Duration)` on the abstraction would either lose information or surprise users.

So the abstraction draws a line. *What every cache does the same way* — mapping keys to values, getting, putting, evicting — lives in the abstraction. *What every cache does differently* — TTL, eviction policy, statistics, advanced atomics — lives in provider-specific configuration.

The practical consequence: when you configure a cache, you do it at the *provider* layer, by the cache name. For Caffeine, that's a `CaffeineSpec` per name. For Redis, it's a `RedisCacheConfiguration` per name held in `RedisCacheManager`. The cache's name is the bridge between the provider configuration and the annotations in your code, and the annotations themselves never need to know about TTL.

There is one partial unification: **statistics**. Micrometer provides a `CacheMeterBinder` for each major provider, plus `CacheMetricsAutoConfiguration` in Spring Boot Actuator that auto-registers them. So while the abstraction doesn't expose stats, the *observability* layer above it does, in a uniform way you'll see in your Prometheus/CloudWatch dashboards.

This is the right design. Resist the urge to wish for more in the core API. The abstraction is small *because* it has to span dramatically different implementations, and shrinking the surface is what keeps it honest.

---

## 8. Closing principles for using the abstraction well

Having built the picture from scratch, let's gather a few principles. These are not a how-to. They are the reflexes you should acquire from understanding the model.

**Cache DTOs, not entities.** Hibernate-managed entities carry runtime proxies (especially for lazy associations) that do not survive serialization. Putting a JPA-managed `Customer` into Redis with the default JDK serializer typically yields one of two outcomes: a `SerializationException` complaining about `ByteBuddyInterceptor` and "no properties discovered to create BeanSerializer," or a successful write of an entity whose lazy fields will explode the next time something touches them after deserialization (because the proxy's session is long gone). The fix is to map to a DTO at the cache boundary, which also forces you to think clearly about what you're caching. Hibernate's *second-level cache* is a different mechanism with different semantics; Spring's cache abstraction is *not* a second-level cache and shouldn't be used as one.

**Decide deliberately about negative caching.** `@Cacheable` will, by default, store a `null` return as `NullValue.INSTANCE`. Sometimes that is exactly what you want (the lookup is expensive and the answer is genuinely "no such record"). Sometimes it isn't (the `null` is a transient failure and you'd rather retry next time). Either decide explicitly with `unless = "#result == null"` to opt out, or design negative caching as a real feature with its own TTL that's shorter than the positive-result TTL.

**Remember the SpEL evaluation timing.** `condition` runs before, `unless` runs after. `#result` lives only in the after-context. The number of bug tickets that boil down to "I tried to use `#result` in a `condition`" is, empirically, large.

**Self-invocation is the same gotcha as `@Transactional`.** Same root cause (proxy doesn't see internal calls), same workarounds (split beans, inject self, AspectJ). If you've internalised it for transactions, you've internalised it for caching.

**Test that the cache populates *and* that cached reads work.** A test that calls a cacheable method twice and asserts the body ran once is necessary but not sufficient. The body running once tells you the framework intercepted; it doesn't tell you the *cached value* survived a real round-trip through your serializer. The Woowahan engineering blog has a now-famous post about a bug where Java records serialized fine but failed to *deserialize* from Redis because Jackson couldn't find a constructor — the cache appeared to work in unit tests (where the local map handled the round-trip trivially) and fell over in production. The lesson is that the meaningful integration test for a Redis cache should always perform a *separate* read after the write, ideally via a different `RedisTemplate` instance, to exercise the deserializer path.

**Set TTLs at the provider level, sized to data volatility.** "Cache for ten minutes" is a one-line Redis configuration. It is not an annotation attribute. The abstraction is right to keep it that way. Give different cache names different TTLs by data volatility — pricing data may want sixty seconds, user-profile data may want an hour, country-list lookups may want a day. Resist the urge to make every cache have the same TTL because the property is global. It's a small amount of configuration to set per cache and it pays back enormously in incident response.

---

### A final thinking question

Read this if you want a small exercise to consolidate. Suppose you write:

```kotlin
@Service
@CacheConfig(cacheNames = ["users"])
class UserService(private val repo: UserRepository) {

    @Cacheable
    fun findById(id: Long): User? = repo.findById(id).orElse(null)

    @Cacheable
    fun findByEmail(email: String): User? = repo.findByEmail(email)
}
```

You call `findById(1L)`, then `findByEmail("a@b.com")`. The second call returns the wrong user. Why?

Take a moment.

The `cacheNames` is `"users"` for both methods, and neither sets a `key`. The default `SimpleKeyGenerator` does *not* incorporate the method, so both calls produce keys derived purely from a single argument. The key for the first call is the `Long` `1L`; the key for the second is the `String` `"a@b.com"` — different, so we'd expect no collision. But now imagine a third method `findByDepartmentId(id: Long)` on the same service, also `@Cacheable` with the same defaults. Call `findById(7L)`, then `findByDepartmentId(7L)`. Same cache, same key (`7L`), different return types. The second call gets the user back, and quite possibly throws a `ClassCastException` deep in your business code, or worse, returns the cached `User` mistyped as a `Department`.

The fix is structural: distinct cache names for distinct concerns. `@Cacheable("userById")` and `@Cacheable("userByEmail")` and `@Cacheable("departmentById")`, each with its own per-cache configuration in the provider, each immune to cross-method collision by construction.

If you reached that conclusion before reading the explanation, you've internalised the model. The rest is just practice.

---

*This treatise is the fourth in a series. The previous artifacts cover (1) a 12-week depth-first internals curriculum, (2) an applications/patterns playbook with library trade-offs, and (3) a curated reading and viewing list of conference talks and engineering blogs. They complement this one by going where this one deliberately doesn't: deeper into source, broader into trade-offs, and out into the wider community's experience.*