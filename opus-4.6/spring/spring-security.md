---
title: "Spring Security Mastery"
category: "Spring"
description: "30-week depth-first curriculum covering filter chain internals, OAuth2/OIDC, microservices auth, reactive security, and OWASP hardening"
---

# Spring Security mastery in 30 weeks: a depth-first curriculum

**This plan transforms a mid-level Kotlin/Spring Boot developer from default auto-config dependency into a Spring Security contributor-level expert across all four critical domains: traditional web security, OAuth2/OIDC, microservices authentication, and reactive security.** The curriculum assumes 10–15 hours per week, structured in seven progressive phases with concrete deliverables, hands-on projects that build on each other, and clear success indicators. Every resource listed is current for Spring Security 6.x and Spring Boot 3.x as of early 2026. The final capstone deploys a production-grade, multi-service system on AWS EKS that exercises every concept in the plan.

---

## Phase 1: The filter chain — understanding Spring Security from the inside out (weeks 1–4)

**Goal:** Internalize the servlet filter chain architecture so deeply that you can mentally trace any HTTP request through every security filter, predict exactly where it will be intercepted, and explain why each filter exists.

**Weekly commitment:** 12–15 hours (heavy reading and source code study)

### Core study materials

Begin with the **official Spring Security Architecture documentation** at `docs.spring.io/spring-security/reference/servlet/architecture.html`. Read every word of the Servlet Security section. Then watch Daniel Garnier-Moiroux's **"Spring Security: Architecture Principles"** from Spring I/O 2024 (youtube.com/watch?v=HyoLl3VcRFY) and his **"Spring Security, demystified"** from Devoxx Belgium 2022 (youtube.com/watch?v=iJ2muJniikY). These two talks provide the single best visual explanation of the filter chain that exists.

Start reading **"Spring Security in Action, 2nd Edition"** by Laurentiu Spilca (Manning, April 2024, foreword by Joe Grandja) — Parts 1 and 2 (chapters 1–9). This is the definitive book for Spring Security 6.x, covering **440 pages** across authentication fundamentals, `SecurityFilterChain` configuration, password management, custom filters, CSRF, and CORS. All code is Java, but translating to Kotlin is straightforward with Spring Security's Kotlin DSL.

### Source code deep dive

Clone `github.com/spring-projects/spring-security` and study these classes in this order:

1. **`DelegatingFilterProxy`** — the bridge between the servlet container and Spring's `ApplicationContext`
2. **`FilterChainProxy`** — the actual `springSecurityFilterChain` bean that routes requests to the correct `SecurityFilterChain` based on `RequestMatcher`
3. **`DefaultSecurityFilterChain`** — the default implementation; study how filters are ordered
4. **`HttpSecurity`** — the builder/DSL that constructs the chain; read every `.configure()` method
5. **`SecurityContextHolder`** — understand all three strategies: `MODE_THREADLOCAL`, `MODE_INHERITABLETHREADLOCAL`, `MODE_GLOBAL`
6. The key filter ordering defined in `SecurityFilters.java` (path: `config/src/main/java/org/springframework/security/config/http/SecurityFilters.java`)

The **default filter chain executes in this exact order**: `DisableEncodeUrlFilter` → `SecurityContextHolderFilter` → `HeaderWriterFilter` → `CorsFilter` → `CsrfFilter` → `LogoutFilter` → authentication filters → `SecurityContextHolderAwareRequestFilter` → `AnonymousAuthenticationFilter` → `SessionManagementFilter` → `ExceptionTranslationFilter` → `AuthorizationFilter`. Memorize this sequence. Draw it on a whiteboard. It is the skeleton of everything that follows.

### Week-by-week breakdown

| Week | Focus | Activities |
|------|-------|------------|
| 1 | Filter chain architecture | Read Architecture docs, watch both Garnier-Moiroux talks, read Spilca ch. 1–3, clone Spring Security repo and trace `FilterChainProxy` |
| 2 | Authentication internals | Read Spilca ch. 4–6, study `AuthenticationManager` → `ProviderManager` → `AuthenticationProvider` → `DaoAuthenticationProvider` chain, implement custom `UserDetailsService` in Kotlin |
| 3 | CSRF, CORS, headers | Read Spilca ch. 7–9, study `CsrfFilter` source, configure CORS with `CorsConfigurationSource`, add CSP and `Permissions-Policy` headers manually |
| 4 | Custom filters and authorization | Write 3 custom filters (logging, rate-limiting, header validation), study `AuthorizationManager<T>` and `AuthorizationFilter` replacing legacy `FilterSecurityInterceptor` |

### Hands-on project: Secure blog API

Build a Kotlin/Spring Boot 3 REST API for a blog platform with MySQL/PostgreSQL. Implement form login, HTTP Basic for the API, `BCryptPasswordEncoder`, role-based authorization (`ADMIN`, `EDITOR`, `READER`), CSRF protection for browser endpoints, CORS for a specific frontend origin, and all security headers including CSP. Write the entire `SecurityFilterChain` configuration using the **Kotlin DSL** (reference: `baeldung.com/kotlin/spring-security-dsl`).

### Success indicators

- Can draw the complete filter chain from memory and explain each filter's purpose
- Can implement a `SecurityFilterChain` in Kotlin without looking at documentation
- Can insert a custom filter at a precise position in the chain and explain why that position matters
- Can articulate when to disable CSRF (stateless JWT APIs) vs. when it is dangerous to do so (session-based apps serving browsers)
- Blog API passes manual security review: no open CORS, CSRF tokens validated, proper session fixation protection

---

## Phase 2: OAuth2 and OpenID Connect with Keycloak and Cognito (weeks 5–10)

**Goal:** Master the OAuth2/OIDC protocol family deeply enough to implement, debug, and architect token-based authentication with both Keycloak and AWS Cognito, including PKCE, the BFF pattern, and emerging standards like DPoP.

**Weekly commitment:** 12–15 hours

### Core study materials

Read **"Spring Security in Action" Part 4** (chapters 12–15), covering the complete OAuth2 stack: authorization server, resource server, and client. Study the **Spring Authorization Server** project at `github.com/spring-projects/spring-authorization-server` — this is the official replacement for the deprecated Spring Security OAuth project, designed to conform to **OAuth 2.1**.

Read **RFC 9700** (published January 2025), the definitive OAuth 2.0 Security Best Current Practice. Key mandates: **PKCE required for all clients** (not just public ones), implicit grant removed entirely, exact redirect URI matching required, sender-constrained tokens recommended via mTLS or DPoP. Then read the **OAuth 2.1 draft** at `oauth.net/2.1/` to understand the consolidation of these practices into a single specification.

For the BFF pattern, study the Baeldung tutorial at `baeldung.com/spring-cloud-gateway-bff-oauth2` and the ProductDock implementation guide at `productdock.com/securing-your-web-apps-spring-security-oauth-2-0-bff-pattern/`. This pattern is now the **recommended approach for SPA security**: the gateway acts as a confidential OAuth2 client, manages tokens server-side, and uses HttpOnly session cookies with the browser. Tokens never reach the browser, eliminating XSS-based token theft.

### Keycloak deep dive (weeks 5–7)

Since Keycloak **deprecated its Spring Boot adapters**, integration now uses standard Spring Security OAuth2 starters exclusively. Configure `spring-boot-starter-oauth2-client` for login flows and `spring-boot-starter-oauth2-resource-server` for API protection, all through standard `spring.security.oauth2.*` properties. Study Piotr Minkowski's microservices tutorial at `piotrminkowski.com/2024/03/01/microservices-with-spring-cloud-gateway-oauth2-and-keycloak/` for a production-realistic architecture.

Run Keycloak in Docker. Configure a realm, clients (public and confidential), roles, groups, and custom claim mappers. Implement the **authorization code flow with PKCE**, study the token exchange between Spring Security and Keycloak at the HTTP level using browser dev tools and Wireshark/mitmproxy.

### AWS Cognito integration (weeks 8–9)

Cognito uses the same standard Spring Security OAuth2 configuration — the provider changes but the architecture remains identical. Study the Rieckpil tutorial at `rieckpil.de/thymeleaf-oauth2-login-with-spring-security-and-aws-cognito/` and the reactive variant at `aosolorzano.medium.com/oauth2-in-spring-boot-native-reactive-microservice-with-amazon-cognito-as-oidc-service`. Learn the **ALB + Cognito integration pattern** where the load balancer handles the entire OAuth2 flow, passing decoded claims via `x-amzn-oidc-*` headers — useful for simpler architectures.

### BFF pattern and DPoP (week 10)

Implement a **Backend-for-Frontend** using Spring Cloud Gateway with the `TokenRelay` filter. The gateway authenticates users via Keycloak, stores tokens in a Redis-backed session, and relays access tokens to downstream resource servers. The browser only sees HttpOnly session cookies.

Study **DPoP (RFC 9449)** — an application-layer alternative to mTLS for sender-constraining tokens. Lighter than mTLS, no PKI infrastructure needed. The client generates a key pair, creates a signed DPoP proof JWT per request, and the authorization server binds the access token to the client's public key. **Spring Security 6.5 added OAuth 2.0 DPoP support** — study the implementation.

### Key source code to study

- **`OAuth2LoginAuthenticationFilter`** — handles the authorization code callback
- **`OidcAuthorizationCodeAuthenticationProvider`** — processes OIDC tokens
- **`JwtAuthenticationProvider`** — validates JWTs for resource servers
- **`NimbusJwtDecoder`** — the default JWT decoder using the Nimbus JOSE library
- **Spring Security OAuth2 modules**: `spring-security-oauth2-core`, `spring-security-oauth2-client`, `spring-security-oauth2-resource-server`, `spring-security-oauth2-jose`

### Hands-on project: Multi-provider auth platform

Extend the blog API to support OAuth2 login via both Keycloak and Cognito. Implement a `JwtAuthenticationConverter` that maps Keycloak realm roles and Cognito groups to Spring Security authorities. Build a BFF gateway with Spring Cloud Gateway + TokenRelay + Redis sessions. Configure the Spring Authorization Server as your own OIDC provider for the development environment.

### Success indicators

- Can explain the entire authorization code + PKCE flow at the HTTP level, including every redirect and token exchange
- Can configure Spring Security to work with any OIDC-compliant provider by changing only `application.yml`
- Can articulate when to use the BFF pattern vs. direct token-based auth vs. ALB-level authentication
- Can explain JWT structure, validation, and the trade-offs of local vs. remote token validation
- BFF gateway correctly manages sessions, relays tokens, and handles token refresh transparently

---

## Phase 3: Microservices authentication and API gateway security (weeks 11–16)

**Goal:** Design and implement secure inter-service communication patterns including JWT propagation, client credentials flows, mTLS, and service mesh integration, deployed on AWS EKS.

**Weekly commitment:** 12–15 hours

### Core study materials

Study the **JWT vs. opaque tokens trade-off matrix** thoroughly. JWTs enable stateless local validation (fast, scalable) but are difficult to revoke; opaque tokens require introspection calls but support instant revocation. The **recommended hybrid approach**: JWTs for access tokens with short expiry, opaque tokens for refresh tokens with server-side revocation. For sensitive operations, fall back to remote validation even with JWTs.

Read the Spring Cloud Gateway security documentation and the Okta patterns guide at `developer.okta.com/blog/2020/08/14/spring-gateway-patterns`. Study the five gateway auth patterns:

- **Token Relay** — gateway forwards user's access token to downstream services
- **Token Exchange** — gateway exchanges incoming token for a different one (cross-domain, different audiences)
- **Client Credentials at Gateway** — gateway obtains its own token for backend calls
- **BFF Pattern** — gateway manages sessions, stores tokens server-side
- **Gateway Offloading** — gateway validates tokens, backend trusts gateway headers

### Service-to-service authentication (weeks 11–12)

Implement the **OAuth2 client credentials grant** for machine-to-machine communication. Use `spring-boot-starter-oauth2-client` with `authorization-grant-type: client_credentials`. Study `OAuth2AuthorizedClientManager` and `WebClient` integration using `ServerBearerExchangeFilterFunction` (reactive) or `ServletOAuth2AuthorizedClientExchangeFilterFunction` (servlet). For thread-boundary crossing in async scenarios, use `DelegatingSecurityContextRunnable` and `DelegatingSecurityContextCallable`.

### mTLS and service mesh (weeks 13–14)

Understand that **service mesh (Istio/Linkerd) and Spring Security are complementary, not alternatives**. Istio handles transport-level security (automatic mTLS between sidecars via `PeerAuthentication` CRD with `STRICT` mode), while Spring Security handles application-level authorization. Even with mTLS, JWTs carry user identity needed for authorization decisions — this is the **confused deputy problem** that mTLS alone cannot solve.

Configure Istio `AuthorizationPolicy` for fine-grained RBAC at the network level. Study how to offload JWT validation to Istio's sidecar for basic claims checking while keeping complex business authorization in Spring Security.

### AWS deployment patterns (weeks 15–16)

Implement the **layered security architecture for EKS**:

1. **Network layer**: VPC with private subnets for services, security groups, NACLs
2. **Load balancer layer**: ALB with TLS termination
3. **Gateway layer**: Spring Cloud Gateway as BFF/resource server
4. **Service layer**: Spring Security resource server per microservice
5. **Secrets management**: AWS Secrets Manager with **IRSA** (IAM Roles for Service Accounts) — enables pod-level AWS IAM authentication without static credentials
6. **Credential injection**: Choose between Spring Cloud AWS `spring-cloud-aws-starter-secrets-manager`, Kubernetes Secrets Store CSI Driver with ASCP, or External Secrets Operator

### Hands-on project: Secure microservices platform

Build a 4-service system: API Gateway (Spring Cloud Gateway), User Service, Order Service, Notification Service. Implement these patterns:

- Gateway authenticates users via Keycloak OIDC, relays tokens to downstream services
- Order Service calls User Service using client credentials flow (machine-to-machine)
- All services validate JWTs locally; Order Service falls back to introspection for refund operations
- Custom `JwtAuthenticationConverter` per service extracts service-specific authorities
- Containerize with Docker, deploy to EKS with Istio `STRICT` mTLS
- Inject database credentials via AWS Secrets Manager + IRSA

### Success indicators

- Can architect a microservices security topology and justify every pattern choice
- Can explain why mTLS alone is insufficient and when JWT propagation vs. token exchange is appropriate
- Can configure Spring Cloud Gateway in all five auth patterns
- Can deploy services to EKS with IRSA, mTLS, and proper secrets management
- All inter-service calls authenticated; no service trusts another without token validation

---

## Phase 4: Reactive security with WebFlux and Kotlin coroutines (weeks 17–21)

**Goal:** Master Spring Security's reactive stack deeply enough to build production WebFlux applications and understand exactly where reactive security diverges from the servlet model.

**Weekly commitment:** 10–12 hours

### Core study materials

Read **"Spring Security in Action" Part 5** on reactive application security. Study the official reactive documentation at `docs.spring.io/spring-security/reference/reactive/index.html`. Watch Garnier-Moiroux's architecture talks again, now focusing on how the reactive model differs.

The fundamental difference: **`ReactiveSecurityContextHolder` stores security context in the Reactor Context** (a subscriber-side construct that flows through the reactive pipeline) instead of `ThreadLocal`. This means security context propagates automatically through `Mono`/`Flux` chains without the thread-affinity problems of the servlet model. The `ReactorContextWebFilter` manages this propagation in the default reactive filter chain.

### Imperative vs. reactive comparison

| Concept | Servlet | WebFlux |
|---------|---------|---------|
| Config annotation | `@EnableWebSecurity` | `@EnableWebFluxSecurity` |
| Config bean | `SecurityFilterChain` via `HttpSecurity` | `SecurityWebFilterChain` via `ServerHttpSecurity` |
| Method security | `@EnableMethodSecurity` | `@EnableReactiveMethodSecurity` |
| User loading | `UserDetailsService` | `ReactiveUserDetailsService` |
| Auth manager | `AuthenticationManager` | `ReactiveAuthenticationManager` |
| Context storage | `SecurityContextHolder` (ThreadLocal) | `ReactiveSecurityContextHolder` (Reactor Context) |
| OAuth2 client manager | `OAuth2AuthorizedClientManager` | `ReactiveOAuth2AuthorizedClientManager` |

### The reactive filter chain

Study this order: `HttpHeaderWriterWebFilter` → `HttpsRedirectWebFilter` → `CorsWebFilter` → `CsrfWebFilter` → `ReactorContextWebFilter` → `AuthenticationWebFilter` → `SecurityContextServerWebExchangeWebFilter` → `ServerRequestCacheWebFilter` → `LogoutWebFilter` → `ExceptionTranslationWebFilter` → `AuthorizationWebFilter`.

### Kotlin coroutines integration (critical)

This is the most treacherous area. **Kotlin coroutines don't work with `ThreadLocal`-based `SecurityContextHolder`** because coroutines are not bound to specific threads. Two solutions exist:

- **WebFlux + coroutines**: `@EnableReactiveMethodSecurity` works because security context propagates via Reactor Context automatically. `@PreAuthorize` and `@PostAuthorize` work on `suspend` functions.
- **Spring MVC + coroutines**: Requires `SecurityCoroutineContext` — a custom `ThreadContextElement` implementation. Study the JDriven guide at `jdriven.com/blog/2021/07/Propagating-the-Spring-SecurityContext-to-your-Kotlin-Coroutines`.

**Known issues**: There have been bugs with `@PreAuthorize` on `suspend` functions (GitHub issues #12821 and #10810 in the Spring Security repo). Test thoroughly and check the current status of these issues before relying on method security with coroutines.

Study the **`soasada/kotlin-coroutines-webflux-security`** repository on GitHub — the best Kotlin-specific example of JWT authentication with coroutines and WebFlux security, including a full filter chain diagram.

### Hands-on project: Reactive notification service

Rebuild the Notification Service from Phase 3 as a fully reactive WebFlux application with Kotlin coroutines:

- `SecurityWebFilterChain` configuration using the Kotlin DSL
- Reactive OAuth2 resource server with JWT validation
- `ReactiveUserDetailsService` backed by R2DBC (Aurora PostgreSQL)
- Method-level security with `@PreAuthorize` on `suspend` functions
- `WebClient` with `ServerBearerExchangeFilterFunction` for authenticated downstream calls
- Server-Sent Events endpoint with reactive security context propagation

### Success indicators

- Can configure `SecurityWebFilterChain` as fluently as `SecurityFilterChain`
- Can explain exactly how security context propagates in a reactive pipeline vs. a servlet thread
- Can debug coroutine context loss issues and implement `SecurityCoroutineContext` when needed
- Can articulate when reactive security provides genuine benefits (high-concurrency notification/streaming) vs. when servlet security is simpler and sufficient
- Notification service handles 10,000+ concurrent SSE connections with proper per-connection security

---

## Phase 5: Security testing, hardening, and OWASP (weeks 22–25)

**Goal:** Build a comprehensive security testing strategy and harden all previous projects against the OWASP Top 10, learning to think like an attacker targeting Spring Boot applications.

**Weekly commitment:** 10–12 hours

### Spring Security test support

The `spring-security-test` module provides powerful testing primitives. Master all of these:

- **`@WithMockUser`**: Simulates authentication without real credentials. Customizable: `@WithMockUser(username="admin", roles=["ADMIN"])`. Default: user/password/`ROLE_USER`.
- **`@WithUserDetails`**: Loads a real user from your `UserDetailsService` — tests the full user-loading pipeline.
- **`@WithSecurityContext`**: Maximum flexibility via custom `SecurityContextFactory` — create `@WithOAuth2User` or `@WithKeycloakUser` annotations.
- **`SecurityMockMvcRequestPostProcessors`**: Programmatic approach — `.with(user("duke"))`, `.with(csrf())`, `.with(jwt().jwt { it.claim("email", "test@example.com") })`, `.with(oauth2Login())`, `.with(opaqueToken())`.
- **Reactive testing**: `WebTestClient` with `.mutateWith(mockUser())`, `.mutateWith(mockJwt())`, and `StepVerifier` for method security.

Read the official testing docs at `docs.spring.io/spring-security/reference/servlet/test/index.html` and the excellent Code With Arho guide at `arhohuttunen.com/spring-security-testing/`.

### OWASP ZAP integration

Integrate **OWASP ZAP** (Zed Attack Proxy) into your CI/CD pipeline. Use the `owasp/zap2docker-stable` Docker image with `zap-api-scan.py` pointed at your OpenAPI spec endpoint (`/v3/api-docs`). Configure passive scanning on every commit via GitHub Actions and active scanning on a nightly schedule. Add **OWASP Dependency-Check** for SCA scanning of dependencies for known CVEs.

### Common Spring Security misconfigurations to audit

These are the vulnerabilities that appear most frequently in Spring Boot applications:

- **Exposed Actuator endpoints**: `/actuator/heapdump` leaks credentials from memory, `/actuator/env` exposes configuration. Restrict to `health` and `info` only, require authentication for everything else.
- **Global CSRF disable**: `http.csrf { disable() }` is safe for pure stateless JWT APIs but dangerous when any endpoint serves browser-based clients with sessions.
- **CORS wildcard with credentials**: `@CrossOrigin(origins = "*")` combined with `allowCredentials(true)` allows any domain to make authenticated requests — a critical vulnerability.
- **Missing security headers**: Spring Security provides Cache-Control, X-Content-Type-Options, HSTS, X-Frame-Options, and X-XSS-Protection by default, but **Content-Security-Policy, Referrer-Policy, and Permissions-Policy must be added manually**.
- **Session fixation**: Protected by default (new session ID on authentication via `changeSessionId` strategy), but verify this hasn't been overridden.
- **Clickjacking**: Protected by default with `X-Frame-Options: DENY`, but modern applications should also set `frame-ancestors` via CSP.

### Hands-on project: Security hardening sprint

Audit and harden all projects from Phases 1–4:

- Write comprehensive security tests using every `@With*` annotation and mock processor
- Create a custom `@WithKeycloakUser` annotation using `@WithSecurityContext`
- Run OWASP ZAP against all services, fix every finding
- Run OWASP Dependency-Check, update vulnerable dependencies
- Add CSP headers in report-only mode, then enforce
- Create a penetration testing checklist and execute it manually
- Document every security decision with "why" and "when NOT to use this"

### Success indicators

- Every endpoint has at least one security test; OAuth2 flows tested with mock JWTs
- OWASP ZAP produces zero high/medium findings across all services
- Can list the OWASP Top 10 and explain how each applies to Spring Boot with specific mitigations
- Can identify at least 5 common Spring Security misconfigurations by code review alone
- Security test suite runs in CI/CD and blocks deployment on failures

---

## Phase 6: Advanced patterns and contribution readiness (weeks 26–28)

**Goal:** Study advanced production patterns, learn the Spring Security codebase well enough to fix bugs, and make your first contribution.

**Weekly commitment:** 10–15 hours

### Advanced patterns to study

Watch **Daniel Garnier-Moiroux's "Passkeys, One-Time Tokens: Passwordless Spring Security"** from Devoxx Belgium 2025 (youtube.com/watch?v=AEuOdJu9K9A). Spring Security 6.4 added **One-Time Token Login** and **Passkeys/WebAuthn support** — implement both in your blog platform. Listen to Rob Winch on **Spring Office Hours S3E43** discussing Spring Security 6.4 features and deprecation notices toward version 7.

Study the **Spring Authorization Server** deeply enough to extend it: add custom grant types, implement dynamic client registration, and configure multi-tenant realms. Read the source at `github.com/spring-projects/spring-authorization-server`.

### Contribution process

The Spring Security project uses **GitHub Issues** (migrated from JIRA) and requires the **Developer Certificate of Origin** (DCO) — sign every commit with `git commit -s`. Find starter issues labeled **"ideal-for-contribution"** at `github.com/spring-projects/spring-security/issues?q=label:"status:+ideal-for-contribution"`.

Follow this contribution workflow:

1. Browse open issues with the `ideal-for-contribution` label
2. Comment on the issue expressing interest; wait for team acknowledgment
3. Check the milestone to determine the target branch (e.g., milestone `6.4.3` → branch `6.4.x`; no milestone → `main`)
4. Fork, create a feature branch, implement with JUnit tests for all behavior changes
5. Commit messages: 55-char subject, imperative tense, `Closes gh-XXXXX`, `Signed-off-by` trailer
6. Submit PR against the target branch; expect review from maintainers who may request significant rework

Read the full contribution guidelines at `github.com/spring-projects/spring-security/blob/main/CONTRIBUTING.adoc` and the wiki's **Contributor Guidelines** page. Study the **Pull Request Reviewer Guidelines** to understand what reviewers look for. Build the project locally: clone, run `./gradlew build` (requires JDK 17+).

### Hands-on milestone: First contribution

Start with documentation fixes or test improvements. Then identify a small bug or enhancement in the OAuth2 or reactive modules — areas where your Phase 4–5 expertise gives you an advantage. Write a comprehensive PR with tests, documentation updates, and a clear commit message. Even if the PR requires extensive rework, the process itself builds deep understanding of the codebase.

### Success indicators

- Can navigate the Spring Security codebase and locate the source of any behavior
- Have submitted at least one PR (even if just documentation or tests)
- Can implement passkeys and one-time tokens in a production application
- Understand the deprecation path toward Spring Security 7 and can prepare applications accordingly

---

## Phase 7: Capstone project — full-stack secure platform on AWS (weeks 29–30+)

**Goal:** Demonstrate mastery across all four domains by building and deploying a production-grade system that an interviewer, colleague, or open-source maintainer would consider exemplary.

### Capstone specification: SecureCommerce platform

Build a multi-tenant e-commerce platform with these components:

**Services (5 microservices + 1 gateway):**

| Service | Stack | Security role |
|---------|-------|---------------|
| API Gateway | Spring Cloud Gateway (reactive) | BFF pattern, OAuth2 client, token relay, rate limiting |
| User Service | Spring Boot MVC + Kotlin | OAuth2 resource server, Keycloak + Cognito federation, passkey authentication |
| Product Catalog | Spring WebFlux + Kotlin coroutines | Reactive OAuth2 resource server, method-level security |
| Order Service | Spring Boot MVC + Kotlin | Resource server, service-to-service auth via client credentials |
| Notification Service | Spring WebFlux + Kotlin coroutines | Reactive resource server, SSE with security context propagation |
| Auth Server | Spring Authorization Server | Custom OIDC provider, multi-tenant, PKCE enforcement |

**Security requirements exercising each domain:**

**Traditional web security**: CSRF protection on the admin dashboard (Thymeleaf-rendered), CORS configured per-tenant, security headers including CSP, session fixation protection, clickjacking prevention.

**OAuth2/OIDC**: Keycloak as primary IdP, Cognito as secondary (multi-provider federation). BFF pattern with Spring Cloud Gateway + Redis sessions. PKCE enforced for all flows. Custom claim mappers for tenant isolation. Refresh token rotation with revocation support.

**Microservices authentication**: JWT propagation from gateway to all services. Client credentials flow for Order → User service calls. Custom `JwtAuthenticationConverter` per service. Istio mTLS between all services. Spring Cloud Gateway `AuthorizationPolicy` for route-level access control.

**Reactive security**: Product Catalog and Notification Service fully reactive. `SecurityWebFilterChain` with Kotlin DSL. `@PreAuthorize` on `suspend` functions. SSE endpoint maintaining security context across 10,000+ concurrent connections. Reactive method security tests with `StepVerifier`.

**Infrastructure (AWS EKS):**

- EKS cluster with Istio service mesh (`STRICT` mTLS)
- ALB with TLS termination
- Aurora PostgreSQL (User, Order databases) and Aurora MySQL (Product database)
- AWS Secrets Manager + IRSA for all credentials
- External Secrets Operator syncing secrets to Kubernetes
- GitHub Actions CI/CD with OWASP ZAP scanning and Dependency-Check

**Testing requirements:**

- Unit tests with `@WithMockUser`, `@WithSecurityContext`, custom `@WithTenantUser`
- Integration tests with `SecurityMockMvcRequestPostProcessors.jwt()` and `WebTestClient.mutateWith(mockJwt())`
- Contract tests for inter-service JWT validation
- OWASP ZAP active scan with zero high/medium findings
- Penetration testing checklist executed and documented

### Success indicators for the capstone

- All services deployed and communicating securely on EKS
- Multi-provider OIDC federation works seamlessly (users can log in via Keycloak or Cognito)
- BFF gateway handles session management correctly under load
- Reactive services maintain security context under high concurrency
- Security test suite achieves >90% coverage of security configurations
- OWASP ZAP and Dependency-Check produce clean reports
- Architecture Decision Records document every security trade-off with "when NOT to use this" guidance

---

## Complete resource reference by phase

### Books

| Title | Author | Year | Use in phase |
|-------|--------|------|-------------|
| Spring Security in Action, 2nd Ed. | Laurentiu Spilca | 2024 | Phases 1–4 (primary text) |
| Pro Spring Security, 3rd Ed. | Massimo Nardone, Carlo Scarioni | 2023 | Phase 3–6 (enterprise patterns) |

### Courses

| Course | Platform | Use in phase |
|--------|----------|-------------|
| Spring Security 6 Zero to Master (Eazy Bytes/Madan Reddy) | Udemy | Phase 1–2 (comprehensive video companion) |
| Learn Spring Security | Baeldung | Phase 2–3 (OAuth2 deep dives, 20 modules) |
| Spring Certified Professional path | Spring Academy (free) | Phase 1 (official fundamentals) |
| Secure Coding in Spring Framework (Andrew Morgan) | Pluralsight | Phase 5 (OWASP Top 10 in Spring context, 7h) |

### Essential conference talks (watch order)

| Talk | Speaker | Phase |
|------|---------|-------|
| "Spring Security, demystified" (Devoxx 2022) | Garnier-Moiroux | 1 |
| "Spring Security: Architecture Principles" (Spring I/O 2024) | Garnier-Moiroux | 1 |
| "The Good Parts" (Devoxx UK 2024) | Garnier-Moiroux | 1 |
| "Authorization: permissions, roles and beyond" (Spring I/O 2025) | Garnier-Moiroux | 2 |
| "OAuth2, OpenID: SSO under the hood" (Voxxed Zürich 2025) | Garnier-Moiroux | 2 |
| "Passkeys, One-Time Tokens" (Devoxx Belgium 2025) | Garnier-Moiroux | 6 |
| Spring Security 6.4 (Spring Office Hours S3E43) | Rob Winch | 6 |

### GitHub repositories

| Repository | Use in phase |
|------------|-------------|
| `spring-projects/spring-security` (source code study) | All phases |
| `spring-projects/spring-security-samples` (official samples, includes Kotlin) | 1, 4 |
| `spring-projects/spring-authorization-server` | 2, 7 |
| `soasada/kotlin-coroutines-webflux-security` | 4 |
| `Kehrlann/spring-security-architecture-workshop` (Garnier-Moiroux's 4h workshop) | 1 |
| `hendisantika/kotlin-spring-boot-3-spring-security-jwt` | 1–2 |
| `amrutprabhu/keycloak-spring-cloud-gateway-and-resource-server` | 3 |
| `timtebeek/spring-security-samples` (JDriven, Gateway + Keycloak) | 3 |

### Documentation sections (study order)

| Section | URL path (under docs.spring.io/spring-security/reference/) | Phase |
|---------|-----|-------|
| Architecture | `servlet/architecture.html` | 1 |
| Authentication | `servlet/authentication/index.html` | 1 |
| Authorization | `servlet/authorization/index.html` | 1–2 |
| OAuth2 Login | `servlet/oauth2/login/core.html` | 2 |
| OAuth2 Resource Server (JWT) | `servlet/oauth2/resource-server/jwt.html` | 2–3 |
| Reactive Security | `reactive/index.html` | 4 |
| Testing | `servlet/test/index.html` | 5 |
| Migration Guide (5.x → 6.x) | GitHub wiki | 6 |

---

## When NOT to use certain approaches — architectural trade-off guide

Depth-first mastery means knowing when a pattern is wrong, not just when it is right. Internalize these anti-patterns:

**Don't use the BFF pattern** when your API serves only mobile clients or other backend services — it adds unnecessary complexity. Use direct bearer token authentication instead. BFF exists specifically because browsers cannot securely store tokens.

**Don't disable CSRF globally** just because "it's a REST API." If any endpoint is accessed by a browser with session cookies, CSRF protection is mandatory. Only disable it for truly stateless, token-authenticated endpoints.

**Don't use JWTs for sessions.** JWTs are access tokens, not session replacements. They cannot be revoked individually, they bloat cookies, and storing them in `localStorage` creates XSS vulnerabilities. Use server-side sessions for session management.

**Don't implement mTLS at the application level** if you have a service mesh. Let Istio/Linkerd handle transport security; focus Spring Security on application-level authorization. Doing both creates operational complexity with no security benefit.

**Don't use opaque tokens in a microservices architecture** without understanding the introspection bottleneck. Every request to every service requires a round-trip to the authorization server. JWTs with short expiry (5–15 minutes) and refresh token rotation provide better scalability.

**Don't mix servlet and reactive security stacks.** If a Spring Boot application has both `spring-boot-starter-web` and `spring-boot-starter-webflux` on the classpath, it defaults to servlet. Mixing causes subtle configuration bugs that are extremely difficult to debug. Choose one stack per service.

**Don't store secrets in environment variables or `application.yml` in production.** Use AWS Secrets Manager with IRSA, or External Secrets Operator. Environment variables appear in process listings, crash dumps, and container inspection output.

This curriculum, executed with discipline over 30 weeks, will produce a developer who not only configures Spring Security competently but understands its architecture deeply enough to debug any issue, make informed architectural decisions, and contribute meaningfully to the project itself.