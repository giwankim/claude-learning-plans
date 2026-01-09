# Spring Security 6.x: A 16-week mastery roadmap for Kotlin developers

Your Spring Boot background gives you a significant head start—you already understand auto-configuration, beans, and the application lifecycle. This plan builds systematically from security fundamentals to advanced patterns like OAuth2 and multi-tenancy, with each week reinforcing the previous through hands-on projects. **The critical insight**: Spring Security isn't a collection of disconnected features but a unified filter-based architecture. Understanding this architecture deeply in weeks 1-4 makes everything else click into place.

## Phase 1: Architectural foundations (weeks 1-4)

This phase moves deliberately slowly. Resist the urge to skip ahead—developers who struggle with Spring Security almost always have gaps in these fundamentals.

### Week 1: Understanding what Spring Security actually does

**Core question to answer**: How does a single HTTP request flow through Spring Security before reaching your controller?

**Study activities (6-8 hours)**:
- Read the official Architecture documentation at `docs.spring.io/spring-security/reference/servlet/architecture.html`
- Watch Amigoscode's "Spring Security Full Course" introduction sections (YouTube, free)
- Study the relationship between **DelegatingFilterProxy** → **FilterChainProxy** → **SecurityFilterChain**

**Key concepts to master**:
- DelegatingFilterProxy bridges Servlet containers to Spring's ApplicationContext
- FilterChainProxy is the actual "springSecurityFilterChain" bean containing all security filters
- Multiple SecurityFilterChain beans can exist, matched by RequestMatcher
- **15+ filters** execute in a specific order for each request (authentication, authorization, exception handling, etc.)

**Hands-on exercise**: Clone the official samples repository and run the hello-security example:
```bash
git clone https://github.com/spring-projects/spring-security-samples
cd spring-security-samples/servlet/spring-boot/kotlin/hello-security
./gradlew bootRun
```

Debug through a login request, setting breakpoints in `UsernamePasswordAuthenticationFilter` and `FilterChainProxy` to observe the filter chain executing.

**Kotlin setup tip**: Add the `kotlin-spring` plugin to your build to avoid marking every `@Configuration` class and `@Bean` method as `open`:
```kotlin
plugins {
    kotlin("plugin.spring") version "1.9.22"
}
```

---

### Week 2: Authentication architecture deep dive

**Core question**: When a user submits credentials, what objects are created and how do they flow through the authentication pipeline?

**Study activities (8-10 hours)**:
- Read `docs.spring.io/spring-security/reference/servlet/authentication/architecture.html` carefully
- Chapter 2-3 of "Spring Security in Action, 2nd Edition" (Manning, April 2024) - the most current comprehensive book
- Baeldung article: "Spring Security Authentication Provider"

**Key components to understand**:

| Component | Purpose |
|-----------|---------|
| **AuthenticationManager** | API defining how filters perform authentication |
| **ProviderManager** | Most common AuthenticationManager implementation; delegates to a list of AuthenticationProviders |
| **AuthenticationProvider** | Performs specific authentication types (username/password, LDAP, OAuth2) |
| **Authentication** | Token representing authentication request OR successful principal |
| **UserDetailsService** | Loads user-specific data; returns UserDetails |
| **PasswordEncoder** | Encodes and verifies passwords |

**Authentication flow visualization**:
```
Request → Filter extracts credentials → Authentication token created
    → AuthenticationManager.authenticate() called
    → ProviderManager iterates AuthenticationProviders
    → Provider calls UserDetailsService.loadUserByUsername()
    → Password verified via PasswordEncoder
    → Fully populated Authentication returned
    → Stored in SecurityContextHolder
```

**Hands-on project**: Build a custom UserDetailsService in Kotlin:
```kotlin
@Service
class CustomUserDetailsService(
    private val userRepository: UserRepository
) : UserDetailsService {
    override fun loadUserByUsername(username: String): UserDetails {
        val user = userRepository.findByUsername(username)
            ?: throw UsernameNotFoundException("User not found: $username")
        return User.builder()
            .username(user.username)
            .password(user.passwordHash)
            .roles(*user.roles.toTypedArray())
            .build()
    }
}
```

**Kotlin gotcha**: When implementing UserDetails with a data class, you must explicitly override all interface methods because Java's getter naming conventions (`getUsername()`) differ from Kotlin properties:
```kotlin
data class CustomUser(
    private val username: String,
    private val password: String,
    private val authorities: Set<GrantedAuthority>
) : UserDetails {
    override fun getUsername(): String = username
    override fun getPassword(): String = password
    override fun getAuthorities(): Set<out GrantedAuthority> = authorities
    override fun isEnabled(): Boolean = true
    override fun isCredentialsNonExpired(): Boolean = true
    override fun isAccountNonExpired(): Boolean = true
    override fun isAccountNonLocked(): Boolean = true
}
```

---

### Week 3: SecurityContext, SecurityContextHolder, and form login

**Core question**: Where does Spring Security store the authenticated user, and how does form login actually work end-to-end?

**Study activities (6-8 hours)**:
- Official docs on SecurityContext and SecurityContextHolder
- Spring.io guide: "Securing a Web Application" (`spring.io/guides/gs/securing-web`)
- EazyBytes course sections 1-3 (Udemy, typically ~$15 on sale)

**SecurityContextHolder strategies**:
- **MODE_THREADLOCAL** (default): One SecurityContext per thread
- **MODE_INHERITABLETHREADLOCAL**: Child threads inherit parent's context
- **MODE_GLOBAL**: Single context for entire application

**Critical Spring Security 6 change**: SecurityContext is now saved only when explicitly needed, not after every request. This improves performance but means manual saves may be required in some scenarios.

**Form login components**:
- `UsernamePasswordAuthenticationFilter` - extracts credentials from form POST
- `DefaultLoginPageGeneratingFilter` - creates the default /login page
- `DefaultLogoutPageGeneratingFilter` - creates /logout page
- `AuthenticationSuccessHandler` / `AuthenticationFailureHandler` - handle outcomes

**Hands-on project**: Build a complete form login application with:
- Custom login page (Thymeleaf)
- In-memory users with different roles
- Success/failure redirect customization
- Logout functionality

**Kotlin DSL configuration** (CRITICAL: import the invoke function):
```kotlin
import org.springframework.security.config.annotation.web.invoke

@Configuration
@EnableWebSecurity
class SecurityConfig {
    @Bean
    fun filterChain(http: HttpSecurity): SecurityFilterChain {
        http {
            authorizeHttpRequests {
                authorize("/", permitAll)
                authorize("/login", permitAll)
                authorize("/admin/**", hasRole("ADMIN"))
                authorize(anyRequest, authenticated)
            }
            formLogin {
                loginPage = "/login"
                defaultSuccessUrl("/dashboard", false)
                failureUrl = "/login?error"
            }
            logout {
                logoutSuccessUrl = "/login?logout"
                deleteCookies("JSESSIONID")
            }
        }
        return http.build()
    }
}
```

---

### Week 4: HTTP Basic authentication and default auto-configuration

**Study activities (5-6 hours)**:
- Official docs: HTTP Basic Authentication
- Baeldung: "Spring Boot Security Auto-Configuration"
- Experiment with removing/adding security dependencies

**Auto-configuration behavior in Spring Boot 3.x**:
1. Adds `@EnableWebSecurity` automatically
2. Secures **all endpoints** by default (requires authentication)
3. Creates a default user "user" with random password (logged at startup)
4. Enables both HTTP Basic and form login
5. Provides CSRF protection for non-GET requests

**Understanding defaults before customizing**: Create a minimal Spring Boot project with only `spring-boot-starter-security`. Observe what happens without any configuration. This understanding is crucial—many developers fight against auto-configuration instead of working with it.

**Hands-on exercise**: Build a REST API secured with HTTP Basic:
```kotlin
@Bean
fun apiFilterChain(http: HttpSecurity): SecurityFilterChain {
    http {
        securityMatcher("/api/**")
        authorizeHttpRequests {
            authorize(anyRequest, authenticated)
        }
        httpBasic { 
            realmName = "My API"
        }
        csrf { disable() }  // OK for stateless APIs
        sessionManagement {
            sessionCreationPolicy = SessionCreationPolicy.STATELESS
        }
    }
    return http.build()
}
```

**Week 4 project**: Combine everything learned—create an application with:
- Public endpoints (permitAll)
- User endpoints (authenticated)
- Admin endpoints (hasRole("ADMIN"))
- Custom UserDetailsService backed by H2/PostgreSQL
- Password encoding with BCrypt
- Both form login (for web) and HTTP Basic (for API)

---

## Phase 2: Intermediate security patterns (weeks 5-8)

With foundations solid, you can now tackle real-world patterns confidently.

### Week 5: Session management and CSRF protection

**Study activities (6-8 hours)**:
- Official docs: Session Management, CSRF Protection
- Baeldung: "Control the Session with Spring Security", "CSRF Protection in Spring Security"

**Session management concepts**:
- **Session fixation protection**: Changes session ID after authentication (default: `changeSessionId`)
- **Concurrent session control**: Limit sessions per user
- **Session creation policies**: ALWAYS, IF_REQUIRED, NEVER, STATELESS

```kotlin
http {
    sessionManagement {
        sessionCreationPolicy = SessionCreationPolicy.IF_REQUIRED
        sessionFixation { changeSessionId() }
        maximumSessions = 1
        maxSessionsPreventsLogin = true
    }
}
```

**CSRF in Spring Security 6**: Major changes occurred:
- CSRF token loading is now **deferred by default** (performance improvement)
- **BREACH protection** enabled by default via `XorCsrfTokenRequestAttributeHandler`
- For SPAs, use `CookieCsrfTokenRepository`:

```kotlin
http {
    csrf {
        csrfTokenRepository = CookieCsrfTokenRepository.withHttpOnlyFalse()
        csrfTokenRequestHandler = SpaCsrfTokenRequestHandler()
    }
}
```

**When to disable CSRF**: Only for truly stateless REST APIs that don't use session cookies. If your API uses JWT tokens in Authorization headers (not cookies), CSRF protection isn't needed.

---

### Week 6: CORS configuration and custom filters

**Study activities (6-8 hours)**:
- Official docs: CORS, Adding Custom Filters
- Baeldung: "CORS with Spring", "Custom Filter in Spring Security Filter Chain"

**CORS configuration pattern**:
```kotlin
@Bean
fun corsConfigurationSource(): CorsConfigurationSource {
    val configuration = CorsConfiguration().apply {
        allowedOrigins = listOf("https://frontend.example.com")
        allowedMethods = listOf("GET", "POST", "PUT", "DELETE", "OPTIONS")
        allowedHeaders = listOf("*")
        allowCredentials = true
        maxAge = 3600
    }
    return UrlBasedCorsConfigurationSource().apply {
        registerCorsConfiguration("/**", configuration)
    }
}

@Bean
fun filterChain(http: HttpSecurity): SecurityFilterChain {
    http {
        cors { }  // Uses the CorsConfigurationSource bean
        // ... other config
    }
    return http.build()
}
```

**Custom filter placement**:
```kotlin
http {
    addFilterBefore<UsernamePasswordAuthenticationFilter>(MyCustomFilter())
    addFilterAfter<BasicAuthenticationFilter>(AnotherFilter())
    addFilterAt<LogoutFilter>(ReplacementFilter())
}
```

**Hands-on project**: Build a logging/auditing filter that records all authentication attempts.

---

### Week 7: Remember-me authentication and exception handling

**Study activities (5-6 hours)**:
- Official docs: Remember-Me Authentication
- Study `AuthenticationEntryPoint` and `AccessDeniedHandler`

**Remember-me implementation**:
```kotlin
http {
    rememberMe {
        key = "uniqueAndSecretKey"
        tokenValiditySeconds = 86400 * 14  // 2 weeks
        userDetailsService = customUserDetailsService
        useSecureCookie = true
    }
}
```

**Exception handling customization**:
```kotlin
http {
    exceptionHandling {
        authenticationEntryPoint = CustomAuthEntryPoint()
        accessDeniedHandler = CustomAccessDeniedHandler()
    }
}

class CustomAuthEntryPoint : AuthenticationEntryPoint {
    override fun commence(
        request: HttpServletRequest,
        response: HttpServletResponse,
        authException: AuthenticationException
    ) {
        response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Authentication required")
    }
}
```

---

### Week 8: Method-level security

**Study activities (6-8 hours)**:
- Official docs: Method Security
- Baeldung: "Introduction to Spring Method Security"

**Enable method security** (note: `@EnableGlobalMethodSecurity` is deprecated):
```kotlin
@Configuration
@EnableMethodSecurity(prePostEnabled = true, securedEnabled = true)
class MethodSecurityConfig
```

**Annotation types**:
```kotlin
@Service
class DocumentService {
    @PreAuthorize("hasRole('ADMIN')")
    fun deleteDocument(id: Long) { }
    
    @PreAuthorize("hasRole('USER') and #username == authentication.name")
    fun getUserDocuments(username: String): List<Document> { }
    
    @PostAuthorize("returnObject.owner == authentication.name")
    fun getDocument(id: Long): Document { }
    
    @PreFilter("filterObject.owner == authentication.name")
    fun updateDocuments(documents: List<Document>) { }
}
```

**SpEL expressions available**:
- `authentication` - current Authentication object
- `principal` - current principal (usually UserDetails)
- `#parameterName` - method parameter reference
- `returnObject` - method return value (for @PostAuthorize/@PostFilter)

**Kotlin coroutines with method security**: Spring Security 6 supports suspend functions:
```kotlin
@PreAuthorize("hasRole('ADMIN')")
suspend fun adminOnlyOperation(): Result {
    delay(100)
    return Result.success()
}
```

---

## Phase 3: Advanced patterns (weeks 9-12)

### Week 9-10: JWT authentication from scratch

**Study activities (10-12 hours total)**:
- Official docs: OAuth2 Resource Server JWT
- Blog: "JWT Authentication in Spring Boot 3 with Spring Security 6" (blog.tericcabrel.com)
- Repository: `MossaabFrifita/spring-boot-3-security-6-jwt`

**Two approaches to JWT**:
1. **DIY with custom filter** - build everything yourself (educational)
2. **OAuth2 Resource Server** - use Spring's built-in JWT support (production recommended)

**OAuth2 Resource Server approach** (recommended):
```yaml
# application.yml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://your-auth-server.com
          # OR
          jwk-set-uri: https://your-auth-server.com/.well-known/jwks.json
```

```kotlin
@Bean
fun filterChain(http: HttpSecurity): SecurityFilterChain {
    http {
        authorizeHttpRequests {
            authorize("/api/public/**", permitAll)
            authorize("/api/**", authenticated)
        }
        oauth2ResourceServer {
            jwt { }
        }
        sessionManagement {
            sessionCreationPolicy = SessionCreationPolicy.STATELESS
        }
    }
    return http.build()
}
```

**Week 10 project**: Build a complete JWT authentication system with:
- Registration endpoint (public)
- Login endpoint returning JWT
- Protected API endpoints
- Token refresh mechanism
- Proper error responses for expired/invalid tokens

---

### Week 11: OAuth2 and OpenID Connect

**Study activities (8-10 hours)**:
- Official docs: OAuth2 section (all subsections)
- Baeldung: "OAuth 2.0 Resource Server with Spring Security"
- EazyBytes course sections 14-16

**Three OAuth2 roles in Spring Security**:

| Role | Purpose | Configuration |
|------|---------|--------------|
| **Resource Server** | Protects APIs, validates tokens | `oauth2ResourceServer { }` |
| **Client** | Obtains tokens from authorization server | `oauth2Client { }` |
| **Login** | "Login with Google/GitHub" | `oauth2Login { }` |

**OAuth2 Login example**:
```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          google:
            client-id: ${GOOGLE_CLIENT_ID}
            client-secret: ${GOOGLE_CLIENT_SECRET}
            scope: openid, profile, email
```

```kotlin
http {
    oauth2Login {
        loginPage = "/login"
        defaultSuccessUrl("/dashboard", true)
    }
}
```

**Project**: Implement social login with Google AND a custom OAuth2 authorization server (Spring Authorization Server).

---

### Week 12: ACLs and permission-based authorization

**Study activities (6-8 hours)**:
- Official docs: Domain Object Security (ACLs)
- Baeldung: "Introduction to Spring Security ACL"

ACLs provide **instance-level** security (e.g., "user X can edit document Y but not document Z"). This is complex but essential for fine-grained permissions.

**ACL database tables**:
- `ACL_SID` - security identities (users/roles)
- `ACL_CLASS` - domain object classes
- `ACL_OBJECT_IDENTITY` - specific domain instances
- `ACL_ENTRY` - permissions linking SID to object

**Usage with method security**:
```kotlin
@PostFilter("hasPermission(filterObject, 'READ')")
fun findAllDocuments(): List<Document>

@PreAuthorize("hasPermission(#document, 'WRITE')")
fun updateDocument(document: Document)
```

---

## Phase 4: Specialization and mastery (weeks 13-16)

### Week 13: Reactive security with WebFlux

**Study activities (6-8 hours)**:
- Official docs: WebFlux Security
- Baeldung: "Spring Security for Reactive Applications"

**Key differences from servlet stack**:
- `@EnableWebFluxSecurity` instead of `@EnableWebSecurity`
- `SecurityWebFilterChain` instead of `SecurityFilterChain`
- `ServerHttpSecurity` instead of `HttpSecurity`
- `MapReactiveUserDetailsService` for user management

```kotlin
@Bean
fun securityWebFilterChain(http: ServerHttpSecurity): SecurityWebFilterChain {
    return http {
        authorizeExchange {
            authorize("/public/**", permitAll)
            authorize(anyExchange, authenticated)
        }
        httpBasic { }
        formLogin { }
    }
}
```

---

### Week 14: Multi-tenancy patterns

**Study activities (8-10 hours)**:
- Official docs: OAuth2 Resource Server Multi-tenancy
- Baeldung: "Multitenancy with Spring Data JPA"
- Callista Enterprise blog series (7 parts)

**Architectural patterns**:
1. **Database per tenant** - complete isolation
2. **Schema per tenant** - shared database, separate schemas
3. **Shared database with discriminator** - tenant column filtering
4. **PostgreSQL Row Level Security** - database-enforced tenant isolation

**Tenant context propagation**:
```kotlin
class TenantFilter : OncePerRequestFilter() {
    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        chain: FilterChain
    ) {
        val tenantId = request.getHeader("X-Tenant-ID")
        TenantContext.setCurrentTenant(tenantId)
        try {
            chain.doFilter(request, response)
        } finally {
            TenantContext.clear()
        }
    }
}
```

---

### Week 15-16: Capstone project

Build a **production-ready multi-tenant SaaS application** demonstrating:
- JWT authentication with refresh tokens
- OAuth2 social login option
- Role-based AND permission-based authorization
- Method-level security
- Multi-tenant data isolation
- Comprehensive security tests

**Testing Spring Security in Kotlin**:
```kotlin
@WebMvcTest(ApiController::class)
@Import(SecurityConfig::class)
class ApiControllerSecurityTest {
    @Autowired
    private lateinit var mockMvc: MockMvc
    
    @Test
    @WithMockUser(roles = ["ADMIN"])
    fun `admin can access admin endpoint`() {
        mockMvc.perform(get("/api/admin"))
            .andExpect(status().isOk)
    }
    
    @Test
    @WithMockUser(roles = ["USER"])
    fun `regular user cannot access admin endpoint`() {
        mockMvc.perform(get("/api/admin"))
            .andExpect(status().isForbidden)
    }
    
    @Test
    fun `JWT authentication works`() {
        mockMvc.perform(
            get("/api/resource")
                .with(jwt().authorities(SimpleGrantedAuthority("SCOPE_read")))
        ).andExpect(status().isOk)
    }
}
```

---

## Essential resource summary

**Primary learning resources by quality**:

| Resource | Coverage | Cost | Best For |
|----------|----------|------|----------|
| "Spring Security in Action, 2nd Ed" (Manning, 2024) | Complete, Spring Security 6 | ~$50 | Deep understanding |
| Official Spring Security Docs | Authoritative | Free | Reference |
| EazyBytes Udemy Course | Practical, JWT/OAuth2 | ~$15 | Video learners |
| Baeldung tutorials | Focused topics | Free | Quick how-tos |
| Official samples repo | Working code | Free | Hands-on learning |

**GitHub repositories to bookmark**:
- `spring-projects/spring-security-samples` - Official examples (Java + Kotlin)
- `eazybytes/springsecurity6` - Progressive course companion (16 sections)
- `hadiyarajesh/spring-security-kotlin-demo` - Kotlin-native JWT example
- `ch4mpy/spring-addons` - Advanced OAuth2 tooling

**Critical Spring Security 6 changes to remember**:
- `WebSecurityConfigurerAdapter` removed → use `SecurityFilterChain` beans
- `authorizeRequests()` deprecated → use `authorizeHttpRequests()`
- `antMatchers()` removed → use `requestMatchers()`
- `.and()` deprecated → use Lambda DSL
- `@EnableGlobalMethodSecurity` deprecated → use `@EnableMethodSecurity`
- Kotlin DSL requires importing `org.springframework.security.config.annotation.web.invoke`

## Kotlin-specific tips consolidated

**Configuration essentials**:
```kotlin
// build.gradle.kts
plugins {
    kotlin("plugin.spring")  // Removes need for 'open' on Spring classes
}

tasks.withType<KotlinCompile> {
    kotlinOptions {
        freeCompilerArgs = listOf("-Xjsr305=strict")  // Null safety with Java interop
        jvmTarget = "17"
    }
}
```

**Coroutine security context propagation** (for suspend functions outside reactive stack):
```kotlin
class SecurityCoroutineContext(
    private val securityContext: SecurityContext = SecurityContextHolder.getContext()
) : ThreadContextElement<SecurityContext?> {
    companion object Key : CoroutineContext.Key<SecurityCoroutineContext>
    override val key = Key

    override fun updateThreadContext(context: CoroutineContext): SecurityContext? {
        val previous = SecurityContextHolder.getContext()
        SecurityContextHolder.setContext(securityContext)
        return previous
    }

    override fun restoreThreadContext(context: CoroutineContext, oldState: SecurityContext?) {
        SecurityContextHolder.setContext(oldState ?: SecurityContextHolder.createEmptyContext())
    }
}
```

## Conclusion

This 16-week plan transforms you from Spring Security novice to confident practitioner. The key insight repeated throughout: **architecture first, features second**. Understanding how the filter chain, authentication pipeline, and security context work together makes every subsequent topic easier to grasp. The first four weeks feel slow, but developers who invest in this foundation consistently report that intermediate and advanced topics "just make sense" afterward.

Your Kotlin and Spring Boot experience means you can focus purely on security concepts rather than framework basics. Use the Kotlin DSL everywhere—it's cleaner and more type-safe than the Java equivalent. And when debugging issues, remember that Spring Security's behavior always traces back to which filters are active and in what order—`FilterChainProxy` is your friend for understanding what's actually happening.