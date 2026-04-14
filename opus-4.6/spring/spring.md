---
title: "Spring Framework Internals"
category: "Spring"
description: "14-week deep-dive into Spring IoC container, AOP proxies, auto-configuration mechanics, and framework extension patterns"
---

# Spring Framework and Spring Boot internals mastery plan

**You already know how to use Spring Boot — this plan teaches you how it actually works.** Structured as a 14-week deep-dive for a mid-level Kotlin/Spring Boot developer, this curriculum moves from IoC container internals through auto-configuration mechanics to production-grade framework extension. Every resource was selected for its focus on *mechanism over usage*, and every project forces you to rebuild what Spring does behind the scenes. By week 14, you'll read Spring source code fluently and be positioned to contribute upstream.

---

## Phase 1: The container beneath your application (weeks 1–4)

The Spring IoC container is the foundation everything else builds on. Most developers interact with it through `@Autowired` and `@Component` without understanding what those annotations trigger. This phase strips away the abstractions.

### Week 1–2: BeanFactory, BeanDefinition, and the creation chain

**Core reading — Official documentation (start here):**
The Spring Framework reference documentation remains the single most authoritative source. Read these sections in order, focusing on the "how" rather than the "how to":

- **Introduction to the Spring IoC Container and Beans** (`docs.spring.io/spring-framework/reference/core/beans/introduction.html`) — Establishes the `org.springframework.beans` and `org.springframework.context` package architecture and the fundamental distinction between `BeanFactory` and `ApplicationContext`
- **Bean Overview / Bean Definition** (`docs.spring.io/spring-framework/reference/core/beans/definition.html`) — How `BeanDefinition` objects encode metadata: class, scope, dependencies, init/destroy methods. This is the data model the entire container operates on.
- **Dependencies** (`docs.spring.io/spring-framework/reference/core/beans/dependencies.html`) — Constructor injection internals, autowiring algorithms, circular dependency detection, and lazy initialization
- **Container Extension Points** (`docs.spring.io/spring-framework/reference/core/beans/factory-extension.html`) — `BeanPostProcessor`, `BeanFactoryPostProcessor`, and `FactoryBean`. **This is the most important section for understanding how Spring's "magic" works.** Every framework feature — `@Autowired`, `@Transactional`, `@Cacheable` — is implemented through these extension points.
- **The BeanFactory API** (`docs.spring.io/spring-framework/reference/core/beans/beanfactory.html`) — Low-level API differences from ApplicationContext; when and why you'd use one over the other

**Primary book:**
***Pro Spring 6 with Kotlin*** by Peter Späth, Iuliana Cosmina, Rob Harrop, and Chris Schaefer (Apress, 2023). Rob Harrop was an original Spring contributor. This is the deepest treatment of Spring internals available, adapted with all Kotlin examples. Read chapters covering IoC container architecture, bean lifecycle management, and AOP implementation. The companion repository is at `github.com/Apress/pro-spring-6`. For a mid-level developer who already uses Spring, this is the single most valuable book purchase.

**Source code study:**
Clone `github.com/spring-projects/spring-framework` and checkout a release tag (e.g., `v6.2.2`). In IntelliJ, enable source JAR download (`idea { module { isDownloadSources = true } }` in Gradle). Read these classes in order:

1. `BeanFactory` interface — understand the contract
2. `BeanDefinition` interface — what metadata describes a bean
3. `DefaultListableBeanFactory` — the actual bean storage and creation engine; follow `getBean()` → `doGetBean()` → `createBean()` → `doCreateBean()`
4. `DefaultSingletonBeanRegistry` — the three-level cache that resolves circular dependencies
5. `AbstractAutowireCapableBeanFactory` — autowiring logic and bean population

**Supplementary — mini-spring repository:**
Study **DerekYRC/mini-spring** (`github.com/DerekYRC/mini-spring`, ~6,300 stars). This simplified reimplementation preserves Spring's actual class hierarchy while stripping away production complexity. Follow the commit history progressively — each step adds one feature. The README maps each mini-spring class to its Spring Framework equivalent. This is the fastest way to build a mental model of the container.

### Week 2–3: Bean lifecycle and the `refresh()` method

**The single most important method in Spring** is `AbstractApplicationContext.refresh()`. This 13-step orchestrator bootstraps the entire container:

1. `prepareRefresh()` — sets start date, active flags, initializes property sources
2. `obtainFreshBeanFactory()` — creates and configures the internal `BeanFactory`
3. `prepareBeanFactory()` — configures classloader, registers environment beans
4. `postProcessBeanFactory()` — template method for subclass customization
5. `invokeBeanFactoryPostProcessors()` — invokes registered `BeanFactoryPostProcessors`
6. `registerBeanPostProcessors()` — registers `BeanPostProcessors` for later interception
7. `initMessageSource()` — i18n support
8. `initApplicationEventMulticaster()` — event broadcasting setup
9. `onRefresh()` — template method (this is where Spring Boot starts the embedded server)
10. `registerListeners()` — registers `ApplicationListeners`
11. `finishBeanFactoryInitialization()` — instantiates all remaining singletons
12. `finishRefresh()` — publishes `ContextRefreshedEvent`

Set a debugger breakpoint on `refresh()` in your own Spring Boot application and step through each phase. This single debugging session will teach you more about Spring internals than hours of tutorial videos.

**Official documentation to read:**
- **Customizing the Nature of a Bean** (`docs.spring.io/spring-framework/reference/core/beans/factory-nature.html`) — `InitializingBean`, `DisposableBean`, `@PostConstruct`, `@PreDestroy`, lifecycle callbacks, startup/shutdown hooks
- **Bean Scopes** (`docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html`) — How singleton, prototype, request, and session scopes are implemented internally
- **ApplicationContext Additional Capabilities** (`docs.spring.io/spring-framework/reference/core/beans/context-introduction.html`) — MessageSource, event publication, resource loading

The complete bean lifecycle sequence, which you should be able to recite by end of week 3: Constructor → Dependency Injection → `BeanNameAware` → `BeanFactoryAware` → `ApplicationContextAware` → `BeanPostProcessor.postProcessBeforeInitialization` → `@PostConstruct` → `InitializingBean.afterPropertiesSet` → custom init method → `BeanPostProcessor.postProcessAfterInitialization` → Ready → `@PreDestroy` → `DisposableBean.destroy` → custom destroy method.

### Week 3–4: Configuration processing and component scanning

**Official documentation:**
- **Java-based Container Configuration** (`docs.spring.io/spring-framework/reference/core/beans/java.html`) — How `@Configuration` and `@Bean` work internally, including **CGLIB proxying of @Configuration classes** (this is why `@Bean` methods calling other `@Bean` methods return the same singleton)
- **Classpath Scanning and Managed Components** (`docs.spring.io/spring-framework/reference/core/beans/classpath-scanning.html`) — Component scanning internals, stereotype annotations, candidate filtering
- **Annotation-based Container Configuration** (`docs.spring.io/spring-framework/reference/core/beans/annotation-config.html`) — How `@Autowired`, `@Resource`, `@Value`, and `@Qualifier` are processed internally

**Source code to trace:**
- `ConfigurationClassPostProcessor` — the `BeanFactoryPostProcessor` that processes `@Configuration` classes; this is where the "magic" of Java/Kotlin config happens
- `ConfigurationClassParser` — parses `@Bean`, `@Import`, `@ComponentScan` directives
- `ClassPathBeanDefinitionScanner` — how component scanning walks the classpath
- `AutowiredAnnotationBeanPostProcessor` — how `@Autowired` resolution actually works

**GitHub wiki essential reading:**
The Spring Framework GitHub wiki (`github.com/spring-projects/spring-framework/wiki/`) contains 33 pages of design documentation. Two are critical at this stage:
- **Spring Annotation Programming Model** — explains composed annotations, meta-annotations, and how Spring's annotation processing differs from standard Java annotation processing
- **MergedAnnotation API Internals** — documents how annotations are discovered, merged, and cached, including the trade-offs between ASM bytecode reading and reflection

**🏁 Milestone project — "KontainerDI":** Build a minimal IoC container from scratch in pure Kotlin. Implement bean registration, constructor injection via Kotlin reflection (`KClass`), singleton/prototype scopes, custom `@Component` and `@Inject` annotations with classpath scanning, circular dependency detection, and init/destroy lifecycle callbacks. Use `inline fun <reified T> getBean()` for type-safe retrieval. By comparing your implementation against `DefaultListableBeanFactory`, you'll understand every design decision Spring made. Success criteria: your container can bootstrap a small application with **20+ interdependent beans**, detect circular dependencies, and execute lifecycle callbacks in the correct order.

---

## Phase 2: AOP, Environment, and SpEL internals (weeks 5–7)

### Week 5: How Spring AOP actually creates proxies

Spring AOP works through runtime proxy generation — every `@Transactional`, `@Cacheable`, and `@Async` annotation works because Spring replaces your bean with a proxy that intercepts method calls. Understanding this mechanism explains most "why doesn't my annotation work?" bugs.

**Official documentation:**
- **AOP with Spring** (`docs.spring.io/spring-framework/reference/core/aop.html`) — @AspectJ support, proxy creation, AOP concepts
- **Spring AOP APIs** (`docs.spring.io/spring-framework/reference/core/aop-api.html`) — Pointcut API, advice types, `ProxyFactory`, the proxy creation mechanism (JDK dynamic proxy vs CGLIB), and the advisor chain. **This lower-level API documentation is more revealing of internals than the @AspectJ section.**

**Source code reading path:**
1. `DefaultAopProxyFactory.createAopProxy()` — the decision point between JDK and CGLIB proxies
2. `JdkDynamicAopProxy.invoke()` — how the JDK proxy chains advice through `ReflectiveMethodInvocation`
3. `CglibAopProxy.DynamicAdvisedInterceptor.intercept()` — CGLIB interception
4. `AbstractAutoProxyCreator` — this is a `BeanPostProcessor` that automatically wraps beans with proxies
5. `TransactionInterceptor` — trace this to understand exactly what `@Transactional` does internally

**Critical Kotlin-specific knowledge:**
- Kotlin classes are **final by default**. CGLIB cannot proxy final classes. The `kotlin-spring` compiler plugin (all-open) automatically opens `@Component`, `@Configuration`, `@Service`, etc. If you've ever wondered why this plugin exists — this is why.
- Kotlin extension functions compile to static methods and **cannot be advised by Spring AOP**
- `suspend` functions require special treatment in AOP aspects
- Kotlin data classes need the `kotlin-noarg` plugin for CGLIB proxying

**Recommended article:**
"Understanding AOP in Spring: from Magic to Proxies" by Marcos Abel (Medium/Trabe) — clear explanation of JDK Dynamic Proxies vs CGLIB, the self-invocation problem, and how `@Transactional` works through proxy interception.

### Week 6: Environment abstraction, PropertySource, and SpEL

**Official documentation:**
- **Environment Abstraction** (`docs.spring.io/spring-framework/reference/core/beans/environment.html`) — `PropertySource` hierarchy, profile activation mechanism, property resolution internals
- **Spring Expression Language** (`docs.spring.io/spring-framework/reference/core/expressions.html`) — Expression parsing, evaluation context, type conversion, compiler mode

**Source code:**
- `ConfigurableEnvironment` / `PropertySourcesPropertyResolver` — how property resolution walks the source hierarchy
- `SpelExpressionParser` — the expression language engine; understanding SpEL internals helps you debug complex `@Value` expressions and `@ConditionalOnExpression`

### Week 7: Lifecycle Explorer project

**🏁 Milestone project — "Spring Lifecycle Explorer":** Build a Spring Boot application implementing custom post-processors: (1) a `BeanFactoryPostProcessor` that reads custom YAML and dynamically registers bean definitions via `BeanDefinitionRegistry`, (2) a `BeanPostProcessor` that wraps beans with timing/logging proxies, (3) a custom `@AutoLog` annotation processed by a `BeanPostProcessor`, and (4) an `@EventSubscriber` annotation processor that auto-registers event listeners. Study `AutowiredAnnotationBeanPostProcessor`, `ConfigurationClassPostProcessor`, and `CommonAnnotationBeanPostProcessor` as reference implementations. Success criteria: you can explain and demonstrate the exact ordering of all post-processor invocations, and your custom processors work correctly with `@Ordered` and `PriorityOrdered`.

---

## Phase 3: Spring Boot's layer on top of Spring Core (weeks 8–11)

### Week 8–9: Auto-configuration — how the magic works

Spring Boot's most powerful feature is auto-configuration, and it's built entirely on Spring Framework's extension points — specifically `BeanFactoryPostProcessor` and `@Import`.

**Official documentation (critical reading):**
- **Creating Your Own Auto-configuration** (`docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html`) — This single documentation page is the Rosetta Stone for Spring Boot internals. It explains `@Conditional` annotations (`@ConditionalOnClass`, `@ConditionalOnBean`, `@ConditionalOnProperty`, `@ConditionalOnMissingBean`), the `AutoConfiguration.imports` file mechanism (which replaced `spring.factories` in Boot 2.7+), auto-configuration ordering, and starter creation conventions.
- **SpringApplication** (`docs.spring.io/spring-boot/reference/features/spring-application.html`) — The bootstrap sequence: `SpringApplication.run()` internals, event listeners, failure analyzers
- **Externalized Configuration** (`docs.spring.io/spring-boot/reference/features/external-config.html`) — The **17-level PropertySource ordering** is essential knowledge for debugging configuration issues in production

**Source code deep-dive:**
The Spring Boot source at `github.com/spring-projects/spring-boot` is remarkably readable. Trace these in order:

1. **`SpringApplication.run()`** — the orchestrator. It determines application type (`SERVLET`/`REACTIVE`/`NONE` via `WebApplicationType.deduceFromClasspath()`), creates the appropriate `ApplicationContext`, prepares the environment, triggers auto-configuration, and starts the embedded server.
2. **`AutoConfigurationImportSelector`** — reads `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`, filters based on conditions, and returns the list of auto-configuration classes to load
3. **`OnClassCondition`**, **`OnBeanCondition`**, **`OnPropertyCondition`** — the condition evaluators that make `@ConditionalOnClass` and friends work
4. **`ConfigurationPropertiesBindingPostProcessor`** — how `@ConfigurationProperties` binding actually works
5. Study an existing auto-configuration like `DataSourceAutoConfiguration` to see how all these pieces compose

**Essential free guide:**
Marco Behler's "How Spring Boot's Autoconfigurations Work" (`marcobehler.com/guides/spring-boot-autoconfiguration`) — a ~3,500-word walkthrough of the actual source code showing how Spring Boot scans the classpath, reads META-INF files, and creates beans through `@Conditional` evaluation. This is the best single article on auto-configuration internals.

**Debugging technique:** Run your application with `--debug` or set `debug=true` in `application.properties` to see the **CONDITIONS EVALUATION REPORT** — a complete listing of every auto-configuration class and whether its conditions matched or failed, and why. The actuator `/actuator/conditions` endpoint provides this at runtime.

**Primary book:**
***Pro Spring Boot 3 with Kotlin*** by Peter Späth and Felipe Gutierrez (Apress, January 2025, 936 pages). Gutierrez is a Senior Platform Architect at Pivotal (the company behind Spring). This is the most current Kotlin + Spring Boot book available, covering Spring Boot 3 internals, auto-configuration mechanics, and cloud-native patterns with first-hand knowledge of how the technology works internally.

### Week 9–10: Actuator internals and production infrastructure

**Official documentation:**
- **Spring Boot Actuator** (`docs.spring.io/spring-boot/reference/actuator/`) — Endpoint implementation, health indicator internals, metrics collection, info contributors
- **Common Application Properties** (`docs.spring.io/spring-boot/appendix/application-properties/`) — The complete list of all auto-configuration properties; essential for understanding what each auto-configuration controls

Study the actuator source code to understand how custom endpoints are registered and how the health check system composes multiple `HealthIndicator` beans into an aggregate status.

### Week 10–11: Custom starter project

**🏁 Milestone project — "Kotlin Metrics Starter":** Build a production-quality Spring Boot starter (`kotlin-metrics-spring-boot-starter`) as a multi-module project: `metrics-library`, `metrics-autoconfigure`, and `metrics-starter`. The auto-configuration should provide a metrics registry, a custom `@Timed` annotation for automatic method timing (implemented via AOP — connecting Phase 2 knowledge), a custom actuator endpoint, and full `@ConfigurationProperties` support with IDE autocompletion via `spring-configuration-metadata.json` generation. Use Kotlin data classes with `@ConstructorBinding` for configuration properties. Test using `ApplicationContextRunner` (Spring Boot's dedicated auto-configuration test utility). Success criteria: the starter can be published to a local Maven repository, consumed by a separate test application, and the auto-configuration correctly backs off when beans are already defined.

---

## Phase 4: Advanced patterns and contribution readiness (weeks 12–14)

### Week 12: AOP deep-dive project

**🏁 Milestone project — "AspectForge":** Build a project with two parts. First, implement a mini AOP framework in Kotlin using both JDK Dynamic Proxies and CGLIB/ByteBuddy, with a before/after/around advice chain and a `MethodInterceptor` pattern. Second, create production-grade custom aspects in Spring: `@Retry(maxAttempts=3, backoff=1000)` with exponential backoff, `@RateLimit(requestsPerSecond=10)` using a token bucket algorithm, and `@DistributedTrace` that generates trace/span IDs. Demonstrate the self-invocation problem explicitly. Success criteria: you can explain why `@Transactional` doesn't work on private methods or self-calls, and your custom aspects handle Kotlin's `open`/`final` semantics correctly.

### Week 13–14: Framework synthesis and open-source contribution

**🏁 Capstone project — "KSpring":** Build a mini-framework in idiomatic Kotlin replicating Spring's core: an `ApplicationContext` with a `refresh()` lifecycle mirroring Spring's 13-step process, annotation scanning (`@KComponent`, `@KBean`), property resolution with a `KEnvironment` abstraction, auto-configuration discovery, and event publishing. Use Kotlin coroutines for async bean initialization, sealed interfaces for type-safe scope definitions, and the `beans { }` DSL pattern that Spring already supports for Kotlin. This synthesizes everything from the previous 12 weeks.

**Contribution preparation:** Search `github.com/spring-projects/spring-framework/issues` with label `in: kotlin` for open issues. Study the **Code Style** wiki page and **Build from Source** instructions. Start with documentation improvements or Kotlin DSL enhancements — the Spring team actively welcomes Kotlin contributions, and Sébastien Deleuze (the Spring team member championing Kotlin support) is responsive to pull requests in this area.

---

## Recommended books — ranked by internals depth

| Book | Author(s) | Year | Why it matters |
|---|---|---|---|
| **Pro Spring 6 with Kotlin** | Späth, Cosmina, Harrop, Schaefer | 2023 | Deepest internals treatment, all Kotlin examples, co-authored by original Spring contributor |
| **Pro Spring Boot 3 with Kotlin** | Späth, Gutierrez | 2025 | Most current Boot internals book; Gutierrez is a Pivotal architect |
| **Spring in Action, 6th Ed** | Craig Walls (Spring team) | 2022 | The classic reference by a Spring engineering team member |
| **Spring Boot: Up and Running** | Mark Heckler (Spring team) | 2021 | Covers both Java and Kotlin; authored by a Spring team member who contributed to Boot, Data, Security |
| **Reactive Spring** | Josh Long (Spring Developer Advocate) | 2020 | Project Reactor internals by the most visible Spring contributor |
| **Spring Security in Action, 2nd Ed** | Laurențiu Spilcă | 2024 | SecurityFilterChain architecture internals; foreword by Spring Security team |
| **Kotlin in Action, 2nd Ed** | Aigner, Elizarov, Isakova, Jemerov | 2024 | Kotlin language depth by JetBrains team; essential for understanding Spring's Kotlin extensions |

---

## Video courses and where they fit

**The Confident Spring Professional** by Marco Behler (`marcobehler.com/courses/spring-professional`) is the single best internals-focused course. It builds from plain Java servlets → adding Spring Framework manually → adding Spring Boot, so you understand exactly what each layer contributes. Updated for Spring Boot 3.5+/Spring Framework 6.2+. Multiple Spring contributors have endorsed it. Use this during **weeks 1–4**.

**Spring Academy** (`spring.academy`) provides free official courses by Josh Long, Sébastien Deleuze, Craig Walls, and Dan Vega. The "Spring Framework Essentials" and "Spring Boot" learning paths cover IoC, DI, and auto-configuration from the perspective of people who write the framework. Use this during **weeks 1–2** as a parallel resource.

**Baeldung's Learn Spring Master Class** (`baeldung.com/courses`) includes Module 4 "Deep Dive Into Spring Boot" covering auto-configuration internals and actuator deep-dives. The code-focused approach complements the more conceptual course content. Use during **weeks 8–9**.

**Modern Spring from Scratch** by Koushik Kothagal on Udemy targets developers "tired of treating Spring as a magical black box" and covers IoC, DI patterns, bean scopes, and lifecycle callbacks. Good supplementary material for **weeks 1–3**.

**Spring Boot 4, Spring Framework 7: Beginner to Guru** by John Thompson on Udemy (33.5+ hours, updated November 2025) goes deep into Spring MVC internals, WebFlux, and Spring Security. Despite the "beginner to" title, later sections cover advanced internals. Use selectively during **weeks 8–11**.

---

## Conference talks worth your time

Five talks stand above the rest for internals understanding:

**Phil Webb — "Breaking the Magician's Code: Diving Deeper into Spring Boot Internals"** explains auto-configuration, the conditional configuration model, and how Spring Boot's conventions actually work. Phil Webb co-created Spring Boot. This is the most directly relevant talk for this curriculum.

**Juergen Hoeller — "Spring Framework 5.2: Core Container Revisited"** (SpringOne Platform 2019, YouTube: `youtu.be/NelebWHGrSM`). Juergen Hoeller is the Spring Framework co-founder and lead. This covers core container architecture decisions and bean lifecycle improvements from the person who designed them.

**Stéphane Nicoll and Brian Clozel — "Ahead Of Time and Native in Spring Boot 3.0"** (Devoxx Belgium 2022) explains how Spring Boot was adapted for native image and AOT compilation, revealing deep internals of the bean definition and proxy generation process.

**Madhura Bhave — "Demystifying Spring's Internals"** (SpringOne Essentials 2023) was specifically highlighted by Josh Long as an excellent talk on Spring internals.

**Josh Long's "Spring Tips" YouTube series** provides weekly deep-dives on specific Spring topics. Search for episodes covering auto-configuration, bean lifecycle, and Kotlin support.

Follow the **Spring I/O YouTube channel** (recordings from the annual Barcelona conference, 60+ talks per year) and the **Devoxx channels** for ongoing talks by Spring team members.

---

## Essential articles and blogs

- **Marco Behler's "How Spring Boot's Autoconfigurations Work"** (`marcobehler.com/guides/spring-boot-autoconfiguration`) — the single best article on auto-configuration mechanics
- **Marco Behler's "What is Spring Framework?"** (`marcobehler.com/guides/spring-framework`) — IoC container internals walkthrough
- **Baeldung's "A Custom Auto-Configuration with Spring Boot"** (`baeldung.com/spring-boot-custom-auto-configuration`) — hands-on auto-configuration creation guide
- **JetBrains' "Demystifying Spring Boot With Spring Debugger"** (`blog.jetbrains.com/idea/2025/06/demystifying-spring-boot-with-spring-debugger/`) — practical techniques for inspecting beans, property resolution, and AOP proxies using IntelliJ's Spring Debugger plugin
- **Spring Framework GitHub Wiki** (`github.com/spring-projects/spring-framework/wiki/`) — 33 pages of design documents including MergedAnnotation API internals and the Spring Annotation Programming Model

---

## GitHub repositories for learning

| Repository | Stars | Purpose |
|---|---|---|
| `spring-projects/spring-framework` | ~57k | The source of truth; read `AbstractApplicationContext.refresh()` first |
| `spring-projects/spring-boot` | ~76k | Trace `SpringApplication.run()` and study `spring-boot-autoconfigure` |
| `DerekYRC/mini-spring` | ~6.3k | Simplified Spring preserving actual class hierarchy; best "build mental model" resource |
| `fuzhengwei/small-spring` | ~5k | Step-by-step Spring reimplementation with accompanying blog series |
| `code4craft/tiny-spring` | ~2k | Git-tag-based progressive IoC construction; checkout each tag sequentially |
| `spring-guides/tut-spring-boot-kotlin` | — | Official Kotlin + Spring Boot guide repository |
| `ThomasVitale/awesome-spring` | — | Comprehensive curated resource list by Thomas Vitale |
| `spring-office-hours/resources-learning-spring` | — | Curated by the Spring team podcast hosts |

---

## Design patterns to recognize in Spring source code

Understanding these patterns makes the source code dramatically more readable:

| Pattern | Where it appears | Key class |
|---|---|---|
| Template Method | Container lifecycle | `AbstractApplicationContext.refresh()` |
| Factory Method | Bean creation | `BeanFactory.getBean()`, `FactoryBean` |
| Proxy | AOP, @Transactional | `JdkDynamicAopProxy`, `CglibAopProxy` |
| Observer | Event system | `ApplicationEventPublisher`, `ApplicationListener` |
| Chain of Responsibility | AOP advice chain | `ReflectiveMethodInvocation.proceed()` |
| Strategy | Transaction management | `PlatformTransactionManager` |
| Decorator | Bean wrapping | `BeanDefinitionDecorator` |
| Composite | Property sources | `CompositePropertySource` |
| Builder | Fluent configuration | `BeanDefinitionBuilder`, `SpringApplicationBuilder` |

---

## When NOT to use — architectural trade-offs to internalize

Understanding internals means knowing the boundaries. These anti-patterns emerge from deep framework knowledge:

**Don't use `@Autowired` field injection** in Kotlin. Constructor injection is not just a style preference — it enables immutability (`val` properties), makes dependencies explicit for testing, and allows the compiler to enforce required dependencies rather than deferring to runtime `NoSuchBeanDefinitionException`. Spring's own codebase uses constructor injection exclusively.

**Don't create a custom `BeanPostProcessor` when an `@Aspect` will do.** BeanPostProcessors operate at the container level and affect *all* beans. AOP aspects target specific join points. The overhead and debugging complexity of BeanPostProcessors is only justified when you need to modify bean definitions or wrap beans in ways that AOP cannot express.

**Don't build a custom starter for internal libraries that won't be shared.** Auto-configuration adds indirection. For application-internal configuration, a simple `@Configuration` class is more debuggable and explicit. Starters earn their complexity only when consumed by multiple independent applications.

**Don't use SpEL in `@Value` expressions for complex logic.** SpEL expressions are evaluated at runtime, are not type-checked at compile time, and are invisible to IDE refactoring. Use `@ConfigurationProperties` with Kotlin data classes for type-safe, IDE-supported configuration binding.

**Don't use Spring AOP when you need to advise self-invocations, final classes, or private methods.** Spring AOP works through proxies — the proxy wraps the bean, so calls within the bean bypass the proxy. If you need these capabilities, you need AspectJ's compile-time or load-time weaving, which is a fundamentally different mechanism.

---

## Conclusion

This curriculum inverts the typical Spring learning path. Instead of learning more APIs, you're learning fewer abstractions more deeply. The key insight is that **Spring Boot is a thin layer of convention and condition evaluation built on Spring Framework's extension points** — primarily `BeanFactoryPostProcessor`, `BeanPostProcessor`, `@Import`, and the `Environment` abstraction. Once you understand these four mechanisms, auto-configuration stops being magic and becomes straightforward engineering.

The five projects form a deliberate progression: rebuild the container → master its extension points → build on the extension points the way Spring Boot does → understand the proxy layer that powers cross-cutting concerns → synthesize everything into a mini-framework. Each project forces you to read specific Spring source code and compare your implementation against the real thing.

For open-source contribution readiness, focus on Kotlin-specific issues in the Spring Framework repository. Sébastien Deleuze maintains the Kotlin support, and the `in: kotlin` label on GitHub issues surfaces contribution opportunities. Start with documentation or Kotlin DSL improvements before tackling core container changes. By week 14, you'll have the source code fluency to make meaningful contributions.