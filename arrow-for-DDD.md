# Arrow-kt 2.x for Functional DDD in Spring Boot

Arrow-kt 2.x fundamentally changes Kotlin application architecture by replacing traditional exception-based error handling with typed, composable errors through the **Raise DSL**. This guide covers the complete setup and patterns for building domain-driven applications with Arrow **2.2.1.1** (current stable), Spring Boot **3.4.x**, and Gradle Kotlin DSL—including the critical migration from deprecated `Validated` to the new `zipOrAccumulate` pattern.

The key insight: Arrow 2.x unifies error handling around the `Raise<E>` context, eliminating the artificial distinction between fail-fast (`Either`) and error-accumulating (`Validated`) approaches. You now choose the behavior through *how* you compose, not *which type* you use.

## Complete Gradle setup with Arrow BOM and KSP

The build configuration requires three coordinated elements: the Arrow BOM for version management, KSP for optics code generation, and Spring Boot's Kotlin plugin for class proxying.

```kotlin
// build.gradle.kts
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    id("org.springframework.boot") version "3.4.1"
    id("io.spring.dependency-management") version "1.1.7"
    kotlin("jvm") version "2.0.21"
    kotlin("plugin.spring") version "2.0.21"
    id("com.google.devtools.ksp") version "2.0.21-1.0.28"
}

group = "com.example"
version = "0.0.1-SNAPSHOT"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(17)
    }
}

repositories {
    mavenCentral()
}

val arrowVersion = "2.2.1.1"

dependencies {
    // Spring Boot
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    
    // Arrow BOM - manages all Arrow dependency versions
    implementation(platform("io.arrow-kt:arrow-stack:$arrowVersion"))
    
    // Arrow Core (Either, Option, Raise DSL, Nel)
    implementation("io.arrow-kt:arrow-core")
    
    // Arrow Optics (immutable data transformation)
    implementation("io.arrow-kt:arrow-optics")
    ksp("io.arrow-kt:arrow-optics-ksp-plugin:$arrowVersion")
    
    // Optional: Coroutines support
    implementation("io.arrow-kt:arrow-fx-coroutines")
    
    // Testing
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

kotlin {
    compilerOptions {
        freeCompilerArgs.addAll("-Xjsr305=strict")
    }
    // Make generated optics visible to IDE
    sourceSets.main {
        kotlin.srcDir("build/generated/ksp/main/kotlin")
    }
}

tasks.withType<Test> {
    useJUnitPlatform()
}
```

**Critical compatibility note**: KSP version must match your Kotlin version. For Kotlin **2.0.21**, use KSP **2.0.21-1.0.28**. The first three segments must align exactly. The `kotlin-spring` plugin automatically opens Spring-annotated classes, which is essential since Kotlin classes are final by default.

## Either and the Raise DSL replace Validated entirely

Arrow 2.0 removed `Validated` because it duplicated `Either`'s abstraction with different composition semantics. The **Raise DSL** now provides both fail-fast and accumulating behaviors through a single, more ergonomic API.

### Defining sealed error hierarchies

```kotlin
sealed interface OrderError {
    data class NotFound(val orderId: OrderId) : OrderError
    data class InvalidStatus(val current: Status, val required: Status) : OrderError
    data object InsufficientInventory : OrderError
    data class ValidationFailed(val errors: NonEmptyList<ValidationError>) : OrderError
}

sealed interface ValidationError {
    data object EmptyName : ValidationError
    data class InvalidEmail(val value: String) : ValidationError
    data class NegativeQuantity(val value: Int) : ValidationError
}
```

### Fail-fast error handling with either { }

The `either { }` builder provides a `Raise<E>` context where you can use `bind()` to unwrap `Either` values and `ensure()` for assertions:

```kotlin
fun processOrder(orderId: OrderId): Either<OrderError, ProcessedOrder> = either {
    // bind() unwraps Either or short-circuits on Left
    val order = orderRepository.findById(orderId).bind()
    
    // ensure() checks predicates, raises error if false
    ensure(order.status == Status.PENDING) { 
        OrderError.InvalidStatus(order.status, Status.PENDING) 
    }
    
    // ensureNotNull() checks for null with smart-casting
    val customer = ensureNotNull(order.customer) { 
        OrderError.NotFound(orderId) 
    }
    
    ProcessedOrder(order, customer)
}
```

### Error accumulation with zipOrAccumulate

The `zipOrAccumulate` function collects **all** errors instead of stopping at the first. This replaces `Validated.zip()`:

```kotlin
data class Email private constructor(val value: String) {
    companion object {
        operator fun invoke(value: String): Either<ValidationError, Email> = either {
            ensure(value.isNotBlank()) { ValidationError.EmptyEmail }
            ensure(value.contains("@")) { ValidationError.InvalidEmail(value) }
            Email(value)
        }
    }
}

data class Customer private constructor(
    val name: String,
    val email: Email,
    val age: Int
) {
    companion object {
        operator fun invoke(
            name: String, 
            email: String, 
            age: Int
        ): Either<NonEmptyList<ValidationError>, Customer> = either {
            zipOrAccumulate(
                { ensure(name.isNotBlank()) { ValidationError.EmptyName } },
                { Email(email).bind() },
                { ensure(age >= 0) { ValidationError.NegativeAge(age) } }
            ) { _, validEmail, _ -> 
                Customer(name, validEmail, age) 
            }
        }
    }
}

// Usage: accumulates ALL validation failures
Customer("", "invalid", -5)
// Returns: Left(NonEmptyList(EmptyName, InvalidEmail("invalid"), NegativeAge(-5)))
```

### mapOrAccumulate for validating collections

```kotlin
data class OrderItem private constructor(val productId: String, val quantity: Int)

fun validateItems(
    items: List<Pair<String, Int>>
): Either<NonEmptyList<ValidationError>, NonEmptyList<OrderItem>> = either {
    val validated = items.mapOrAccumulate { (productId, qty) ->
        ensure(qty > 0) { ValidationError.NegativeQuantity(qty) }
        OrderItem(productId, qty)
    }
    ensureNotNull(validated.toNonEmptyListOrNull()) { ValidationError.EmptyOrder }
}
```

### Using Raise<E> as extension receiver

For internal domain logic, prefer `Raise<E>` as context over returning `Either`. This avoids wrapping/unwrapping and reads more naturally:

```kotlin
// Extension receiver style (preferred for domain internals)
fun Raise<OrderError>.confirmOrder(order: Order): Order.Confirmed {
    ensure(order.status == Status.PENDING) {
        OrderError.InvalidStatus(order.status, Status.PENDING)
    }
    return Order.Confirmed(order.id, order.items, Instant.now())
}

// Convert to Either at boundaries
fun OrderService.confirm(orderId: OrderId): Either<OrderError, Order.Confirmed> = either {
    val order = findOrder(orderId).bind()
    confirmOrder(order) // Uses Raise context implicitly
}
```

## Arrow Optics transforms nested immutable structures

The `@optics` annotation generates lenses, prisms, and isos that make deep immutable updates readable. KSP generates extension properties on companion objects.

### Setting up optics-enabled domain models

```kotlin
import arrow.optics.optics

@optics data class Order(
    val id: OrderId,
    val customer: Customer,
    val shippingAddress: Address,
    val items: List<OrderItem>,
    val status: OrderStatus
) { companion object }

@optics data class Customer(
    val id: CustomerId,
    val name: String,
    val email: Email
) { companion object }

@optics data class Address(
    val street: String,
    val city: String,
    val zipCode: String,
    val country: String
) { companion object }

@optics data class OrderItem(
    val productId: ProductId,
    val quantity: Int,
    val unitPrice: Money
) { companion object }

@JvmInline @optics value class Money(val cents: Long) { companion object }
@JvmInline @optics value class OrderId(val value: String) { companion object }
```

**The empty `companion object` is required** for KSP to generate optics. A beta Arrow Optics Gradle plugin (`io.arrow-kt.optics`) removes this requirement, but is not yet stable.

### Lens composition for nested updates

Generated lenses compose with dot notation for deep access:

```kotlin
// Without optics: nested copy nightmare
fun updateCity(order: Order, newCity: String): Order =
    order.copy(
        shippingAddress = order.shippingAddress.copy(
            city = newCity
        )
    )

// With optics: composable lenses
fun updateCity(order: Order, newCity: String): Order =
    Order.shippingAddress.city.set(order, newCity)

// Modify transforms using a function
fun normalizeAddress(order: Order): Order =
    Order.shippingAddress.city.modify(order) { it.uppercase() }

// Chain multiple lens operations
val customerCity: Lens<Order, String> = 
    Order.customer compose Customer.address compose Address.city
```

### Copy DSL for multiple updates

The `copy { }` DSL handles multiple nested changes elegantly:

```kotlin
fun Order.updateShipping(newStreet: String, newCity: String, newZip: String): Order = 
    copy {
        Order.shippingAddress.street set newStreet
        Order.shippingAddress.city set newCity
        Order.shippingAddress.zipCode set newZip
    }

// Using `inside` to scope changes
fun Order.normalizeShipping(): Order = copy {
    inside(Order.shippingAddress) {
        Address.street transform { it.trim().uppercase() }
        Address.city transform { it.trim().capitalize() }
        Address.zipCode transform { it.replace(" ", "") }
    }
}

// Apply discount to all items
fun Order.applyDiscount(percent: Double): Order = copy {
    inside(Order.items.every) {
        OrderItem.unitPrice.cents transform { (it * (1 - percent)).toLong() }
    }
}
```

### Prisms for sealed class hierarchies

Prisms safely access variants of sealed classes:

```kotlin
@optics sealed interface OrderStatus { companion object }
@optics data class Pending(val createdAt: Instant) : OrderStatus { companion object }
@optics data class Confirmed(val confirmedAt: Instant) : OrderStatus { companion object }
@optics data class Shipped(val trackingNumber: String, val shippedAt: Instant) : OrderStatus { companion object }
@optics data class Cancelled(val reason: String, val cancelledAt: Instant) : OrderStatus { companion object }

// Access only Shipped orders' tracking numbers
fun getTrackingNumber(order: Order): String? =
    Order.status.shipped.trackingNumber.getOrNull(order)

// Modify only if order is Pending
fun updatePendingTimestamp(order: Order, newTime: Instant): Order =
    Order.status.pending.createdAt.modify(order) { newTime }
```

## Smart constructors enforce domain invariants

Value objects with private constructors and validation in companion `invoke` guarantee valid instances throughout the domain:

```kotlin
@JvmInline
value class Email private constructor(val value: String) {
    companion object {
        private val EMAIL_REGEX = Regex("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")
        
        operator fun invoke(value: String): Either<ValidationError.InvalidEmail, Email> = either {
            val trimmed = value.trim().lowercase()
            ensure(trimmed.matches(EMAIL_REGEX)) { 
                ValidationError.InvalidEmail(value) 
            }
            Email(trimmed)
        }
        
        // Convenience for trusted contexts
        fun fromOrThrow(value: String): Email = 
            invoke(value).getOrElse { throw IllegalArgumentException(it.toString()) }
    }
}

@JvmInline
value class OrderId private constructor(val value: String) {
    companion object {
        operator fun invoke(value: String): Either<ValidationError.InvalidOrderId, OrderId> = either {
            ensure(value.isNotBlank()) { ValidationError.InvalidOrderId(value) }
            ensure(value.length <= 36) { ValidationError.InvalidOrderId(value) }
            OrderId(value.trim())
        }
    }
}

@JvmInline
value class Quantity private constructor(val value: Int) {
    companion object {
        operator fun invoke(value: Int): Either<ValidationError.InvalidQuantity, Quantity> = either {
            ensure(value > 0) { ValidationError.InvalidQuantity(value) }
            ensure(value <= 10_000) { ValidationError.InvalidQuantity(value) }
            Quantity(value)
        }
    }
}
```

## Domain services use Raise context internally

Services operate within `Raise<E>` for clean composition, with `either { }` at the boundary:

```kotlin
@Service
class OrderService(
    private val orderRepository: OrderRepository,
    private val inventoryService: InventoryService,
    private val eventPublisher: DomainEventPublisher
) {
    suspend fun confirmOrder(orderId: OrderId): Either<OrderError, Order> = either {
        val order = orderRepository.findById(orderId)
            .mapLeft { OrderError.NotFound(orderId) }
            .bind()
        
        ensureNotNull(order) { OrderError.NotFound(orderId) }
        
        val confirmed = confirmOrderInternal(order)
        
        orderRepository.save(confirmed)
            .mapLeft { OrderError.PersistenceFailed(it.message) }
            .bind()
        
        eventPublisher.publish(OrderConfirmed(confirmed.id))
        confirmed
    }
    
    // Internal logic uses Raise context
    private fun Raise<OrderError>.confirmOrderInternal(order: Order): Order {
        ensure(order.status is Pending) {
            OrderError.InvalidStatus(order.status, Pending::class)
        }
        
        // Check inventory for all items, accumulating errors
        order.items.mapOrAccumulate { item ->
            val available = inventoryService.checkAvailability(item.productId)
            ensure(available >= item.quantity.value) {
                OrderError.InsufficientInventory(item.productId)
            }
        }
        
        return Order.status.set(order, Confirmed(Instant.now()))
    }
}
```

### Repository interfaces return Either

```kotlin
interface OrderRepository {
    suspend fun findById(id: OrderId): Either<RepositoryError, Order?>
    suspend fun save(order: Order): Either<RepositoryError, Order>
    suspend fun findByCustomer(customerId: CustomerId): Either<RepositoryError, List<Order>>
}

sealed interface RepositoryError {
    data class ConnectionFailed(val message: String) : RepositoryError
    data class OptimisticLockFailed(val entityId: String) : RepositoryError
    data class ConstraintViolation(val message: String) : RepositoryError
}

@Repository
class JpaOrderRepository(
    private val jpaRepo: OrderJpaRepository
) : OrderRepository {
    
    override suspend fun findById(id: OrderId): Either<RepositoryError, Order?> =
        Either.catch { jpaRepo.findById(id.value).orElse(null)?.toDomain() }
            .mapLeft { RepositoryError.ConnectionFailed(it.message ?: "Unknown error") }
    
    override suspend fun save(order: Order): Either<RepositoryError, Order> =
        Either.catch { jpaRepo.save(order.toEntity()).toDomain() }
            .mapLeft { e ->
                when {
                    e is OptimisticLockingFailureException -> 
                        RepositoryError.OptimisticLockFailed(order.id.value)
                    e is DataIntegrityViolationException -> 
                        RepositoryError.ConstraintViolation(e.message ?: "Constraint violation")
                    else -> RepositoryError.ConnectionFailed(e.message ?: "Unknown error")
                }
            }
}
```

## Controllers convert Either to HTTP responses

The controller layer transforms typed errors into appropriate HTTP status codes:

```kotlin
@RestController
@RequestMapping("/api/orders")
class OrderController(private val orderService: OrderService) {
    
    @PostMapping("/{id}/confirm")
    suspend fun confirmOrder(@PathVariable id: String): ResponseEntity<*> {
        val orderId = OrderId(id).getOrElse { 
            return ResponseEntity.badRequest().body(ErrorResponse("Invalid order ID")) 
        }
        
        return orderService.confirmOrder(orderId).fold(
            ifLeft = { error -> error.toResponseEntity() },
            ifRight = { order -> ResponseEntity.ok(order.toDto()) }
        )
    }
    
    @PostMapping
    suspend fun createOrder(@RequestBody request: CreateOrderRequest): ResponseEntity<*> {
        return either {
            val customer = Customer(
                request.customerName,
                request.customerEmail,
                request.customerAge
            ).mapLeft { OrderError.ValidationFailed(it) }.bind()
            
            val items = validateItems(request.items)
                .mapLeft { OrderError.ValidationFailed(it) }.bind()
            
            orderService.createOrder(customer, items).bind()
        }.fold(
            ifLeft = { it.toResponseEntity() },
            ifRight = { ResponseEntity.status(HttpStatus.CREATED).body(it.toDto()) }
        )
    }
    
    private fun OrderError.toResponseEntity(): ResponseEntity<ErrorResponse> = when (this) {
        is OrderError.NotFound -> 
            ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(ErrorResponse("Order ${orderId.value} not found"))
        is OrderError.InvalidStatus -> 
            ResponseEntity.status(HttpStatus.CONFLICT)
                .body(ErrorResponse("Order must be ${required.name} but is ${current.name}"))
        is OrderError.InsufficientInventory -> 
            ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
                .body(ErrorResponse("Insufficient inventory"))
        is OrderError.ValidationFailed -> 
            ResponseEntity.badRequest()
                .body(ErrorResponse("Validation failed", errors.map { it.toString() }))
        is OrderError.PersistenceFailed -> 
            ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ErrorResponse("Failed to save order"))
    }
}

data class ErrorResponse(
    val message: String,
    val details: List<String> = emptyList()
)
```

## Complete aggregate root with optics and state transitions

```kotlin
@optics sealed interface Order {
    val id: OrderId
    val customer: Customer
    val items: NonEmptyList<OrderItem>
    
    companion object
}

@optics data class PendingOrder(
    override val id: OrderId,
    override val customer: Customer,
    override val items: NonEmptyList<OrderItem>,
    val shippingAddress: Address,
    val createdAt: Instant
) : Order { companion object }

@optics data class ConfirmedOrder(
    override val id: OrderId,
    override val customer: Customer,
    override val items: NonEmptyList<OrderItem>,
    val shippingAddress: Address,
    val confirmedAt: Instant
) : Order { companion object }

@optics data class ShippedOrder(
    override val id: OrderId,
    override val customer: Customer,
    override val items: NonEmptyList<OrderItem>,
    val shippingAddress: Address,
    val trackingNumber: TrackingNumber,
    val shippedAt: Instant
) : Order { companion object }

// State transitions as pure functions
object OrderOperations {
    fun Raise<OrderError>.confirm(order: PendingOrder, now: Instant): ConfirmedOrder {
        return ConfirmedOrder(
            id = order.id,
            customer = order.customer,
            items = order.items,
            shippingAddress = order.shippingAddress,
            confirmedAt = now
        )
    }
    
    fun Raise<OrderError>.ship(
        order: ConfirmedOrder,
        trackingNumber: TrackingNumber,
        now: Instant
    ): ShippedOrder {
        return ShippedOrder(
            id = order.id,
            customer = order.customer,
            items = order.items,
            shippingAddress = order.shippingAddress,
            trackingNumber = trackingNumber,
            shippedAt = now
        )
    }
    
    fun Raise<OrderError>.updateShippingAddress(
        order: PendingOrder,
        newAddress: Address
    ): PendingOrder {
        // Using optics for immutable update
        return PendingOrder.shippingAddress.set(order, newAddress)
    }
}
```

## Conclusion

Arrow-kt 2.x provides a cohesive functional toolkit for domain-driven design: **Either** with the **Raise DSL** replaces both traditional exceptions and the deprecated Validated type, while **Arrow Optics** eliminates nested copy boilerplate for immutable aggregates. The key patterns are:

- **Sealed error hierarchies** enable exhaustive, compiler-verified error handling
- **Smart constructors** with `either { }` guarantee domain invariants at creation time
- **zipOrAccumulate** collects all validation failures instead of failing fast
- **Raise<E> context** keeps domain logic clean, with `either { }` wrapping at boundaries
- **Repository Either returns** make infrastructure failures explicit in the type system
- **Optics composition** scales gracefully with domain model complexity

The combination produces code where invalid states are unrepresentable, errors are values rather than exceptions, and immutable updates remain readable regardless of nesting depth.