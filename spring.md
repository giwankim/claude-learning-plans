# Mastery-level Spring Framework and Spring Boot internals curriculum

An experienced Kotlin/Spring Boot developer seeking to contribute to the Spring open-source projects needs a structured journey from "I use Spring" to "I understand Spring's design and can modify its source code." This **16-week curriculum** prioritizes deep comprehension of IoC container mechanics, auto-configuration internals, and the contribution workflow, culminating in actual pull requests to spring-projects repositories.

The plan assumes **10-15 hours per week** of dedicated study, with heavier project work in later phases. Each phase builds on the previous one, alternating between conceptual study and hands-on implementation to cement understanding.

---

## Phase 1: Foundation of the container (Weeks 1-4)

The first four weeks establish deep understanding of Spring Framework's core—the IoC container, bean lifecycle, and extension mechanisms that everything else builds upon.

### Week 1-2: IoC container architecture and BeanFactory internals

**Primary study materials:**
- **Pro Spring 6** (Cosmina et al., Apress, July 2023) — Chapters on "Advanced Container Concepts" and "Bean Factory" provide the deepest coverage of IoC internals available in any book, with **938 pages** of comprehensive Spring Framework analysis
- Spring Framework Reference: Container Extension Points section at `docs.spring.io/spring-framework/reference/core/beans/factory-extension.html`
- Marco Behler's guide "How Spring Boot's Autoconfigurations Work" at `marcobehler.com/guides/spring-boot-autoconfiguration` — explains what Spring Boot automates so you understand the baseline

**Source code reading assignments:**
Clone the Spring Framework repository (`github.com/spring-projects/spring-framework`) and trace through these key classes:
- `DefaultListableBeanFactory` in `spring-beans/src/main/java/org/springframework/beans/factory/support/` — the main IoC container implementation
- `BeanFactory` interface hierarchy in `org.springframework.beans.factory`
- `AbstractBeanFactory.getBean()` method — follow the complete bean retrieval logic

**Hands-on exercise:** Write a simplified mini-IoC container in Kotlin (reference: `github.com/fahdarhalai/Lightweight-Java-IoC-Container`). Implement basic dependency injection with constructor injection, singleton scope, and simple `@Component` scanning. This forces you to understand what `DefaultListableBeanFactory` does under the hood.

**Milestone:** Explain in writing how Spring resolves a bean by name, including the role of `BeanDefinition`, `BeanDefinitionRegistry`, and the parent-child factory chain.

### Week 3-4: Bean lifecycle and BeanPostProcessor deep dive

**Study materials:**
- Spring Framework Reference: Bean Lifecycle section
- Baeldung article "Spring BeanPostProcessor" at `baeldung.com/spring-beanpostprocessor`
- Blog post "Spring internals - BeanPostProcessor" at `blog.pchudzik.com/201902/beanpostprocessor/`
- DZone article "Spring Bean Lifecycle" by John Thompson — includes detailed lifecycle diagrams

**Key classes to study in source:**
- `BeanPostProcessor` interface and all implementing classes (especially `AutowiredAnnotationBeanPostProcessor`)
- `BeanFactoryPostProcessor` interface and `PropertySourcesPlaceholderConfigurer`
- `ApplicationContextAwareProcessor` — see how Aware interfaces get injected
- The `AbstractAutowireCapableBeanFactory.initializeBean()` method — the lifecycle orchestration point

**Hands-on exercise:** Implement a custom `BeanPostProcessor` that wraps specific beans with logging proxies using `ProxyFactory`. Then implement a `BeanFactoryPostProcessor` that modifies bean definitions before instantiation.

**Conference talk:** Watch "Spring: Framework in Depth" on LinkedIn Learning (Frank Moley, ~2 hours) — covers IoC container internals, bean lifecycle, and AOP proxies.

**Milestone:** Draw the complete bean lifecycle diagram from memory, including the exact order of `BeanPostProcessor.postProcessBeforeInitialization()`, `InitializingBean.afterPropertiesSet()`, `@PostConstruct`, init-method, and `postProcessAfterInitialization()`.

---

## Phase 2: AOP mechanics and ApplicationContext hierarchy (Weeks 5-7)

### Week 5-6: AOP proxy creation internals

**Study materials:**
- Pro Spring 6: AOP Framework chapter
- Spring Framework Reference: Spring AOP APIs section at `docs.spring.io/spring-framework/reference/core/aop-api.html`
- Baeldung "Introduction to cglib" at `baeldung.com/cglib` — CGLIB bytecode instrumentation details
- Credera article "JDK Proxies vs CGLIB vs AspectJ" — explains Spring Boot 2.0+ defaulting to CGLIB

**Key classes to study:**
- `ProxyFactory` in `org.springframework.aop.framework`
- `JdkDynamicAopProxy` vs `CglibAopProxy` — understand when each is used
- `DefaultAopProxyFactory.createAopProxy()` — the selection logic
- `AspectJAutoProxyCreator` — how `@EnableAspectJAutoProxy` works

**Hands-on exercise:** Create AOP proxies programmatically (without declarative annotations) using `ProxyFactory`. Build both JDK dynamic proxy and CGLIB proxy versions of the same interface/class. Verify using `AopUtils.isJdkDynamicProxy()` and `AopUtils.isCglibProxy()`.

```kotlin
val factory = ProxyFactory(myService)
factory.addAdvice(MyMethodInterceptor())
factory.isProxyTargetClass = true // Force CGLIB
val proxy = factory.proxy as MyService
```

**Important insight:** Understand why self-invocation doesn't trigger aspects (proxy boundary issue) and the `AopContext.currentProxy()` workaround.

### Week 7: ApplicationContext hierarchy and Environment abstraction

**Study materials:**
- Baeldung "Context Hierarchy with the Spring Boot Fluent Builder API" at `baeldung.com/spring-boot-context-hierarchy`
- Baeldung "Spring Web Contexts" at `baeldung.com/spring-web-contexts`
- Spring Framework Reference: Environment Abstraction section

**Key classes to study:**
- `ApplicationContext` interface and `GenericApplicationContext` implementation
- `ConfigurableEnvironment` and `MutablePropertySources`
- `PropertySource` and `PropertySourcesPropertyResolver`
- `SpringApplicationBuilder` for context hierarchies

**Hands-on exercise:** Build a multi-context application with parent-child hierarchy using `SpringApplicationBuilder.parent().child()`. Demonstrate bean visibility rules (child sees parent beans, not vice versa). Use the `/actuator/beans` endpoint to visualize the hierarchy.

**Milestone:** Explain the difference between `BeanFactory` and `ApplicationContext`, list at least 5 additional capabilities `ApplicationContext` provides, and describe when you'd use parent-child contexts.

---

## Phase 3: Spring Boot auto-configuration internals (Weeks 8-10)

This phase focuses exclusively on Spring Boot's "magic"—demystifying auto-configuration so you can create, debug, and contribute to it.

### Week 8: SpringApplication bootstrap process

**Study materials:**
- Spring Boot Reference: SpringApplication section at `docs.spring.io/spring-boot/reference/features/spring-application.html`
- Medium article "What Happens Internally When You Start A Spring Boot Application" (Hamza Nassour) — line-by-line analysis of `SpringApplication.run()`
- DZone article "Spring Boot Under the Hood" (Ganesh Sahu)

**Key classes to study in spring-boot repository:**
- `SpringApplication.run()` — trace the entire startup sequence
- `SpringApplicationRunListener` — startup event notification
- `ApplicationContextInitializer` — context customization before refresh
- `EnvironmentPostProcessor` — environment customization

**Conference talk:** Watch Phil Webb's "Breaking the Magician's Code: Diving Deeper into Spring Boot Internals" (slides at `speakerdeck.com/philwebb/breaking-the-magicians-code-diving-deeper-into-spring-boot-internals`).

**Hands-on exercise:** Implement a custom `SpringApplicationRunListener` that logs every phase of application startup. Implement an `EnvironmentPostProcessor` that adds a custom `PropertySource`.

### Week 9: Auto-configuration mechanism and @Conditional internals

**Study materials:**
- Spring Boot Reference: Creating Your Own Auto-configuration at `docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html`
- Stéphane Nicoll's talk "Master Spring Boot Auto-configuration" (slides at `speakerdeck.com/snicoll/master-spring-boot-auto-configuration`)
- Stéphane Nicoll & Brian Clozel's talk "It's a Kind of Magic: Under the Covers of Spring Boot" at `infoq.com/presentations/spring-boot-auto-configuration/`

**Key classes to study:**
- `@AutoConfiguration` annotation (Spring Boot 3+)
- `AutoConfigurationImportSelector` — how auto-configurations are discovered
- `ConditionEvaluationReport` — debugging conditions
- `OnClassCondition`, `OnBeanCondition`, `OnPropertyCondition` implementations

**Critical file:** `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` — registration mechanism

**Hands-on exercise:** Enable the auto-configuration report (`debug=true` in application.properties) and trace why specific auto-configurations match or don't match. Study `DataSourceAutoConfiguration` as a model—it demonstrates `@ConditionalOnClass`, `@ConditionalOnMissingBean`, and `@EnableConfigurationProperties` patterns.

### Week 10: Building a production-quality custom starter

**Study materials:**
- Baeldung "A Custom Auto-Configuration with Spring Boot" at `baeldung.com/spring-boot-custom-auto-configuration`
- DZone "Spring Boot 3: Creating a Custom Starter" (2025)
- Spring Boot in Practice (Somnath Musib) Chapter 4: Autoconfiguration and Actuator

**Project:** Build a complete Spring Boot starter that:
1. Provides a client library for a hypothetical service (or wrap a real API like GitHub's)
2. Uses `@ConfigurationProperties` for type-safe configuration
3. Implements `@ConditionalOnClass` to activate only when needed
4. Implements `@ConditionalOnProperty` to allow opt-out
5. Orders itself correctly with `@AutoConfigureBefore`/`@AutoConfigureAfter`
6. Includes a custom `FailureAnalyzer` for common misconfigurations
7. Includes `spring-configuration-metadata.json` for IDE support

**Milestone:** Your starter should be publishable to Maven Central (or at least local Maven repository) and usable as a dependency in another Spring Boot project.

---

## Phase 4: Advanced Spring Boot internals (Weeks 11-13)

### Week 11: Embedded server lifecycle and actuator internals

**Study materials:**
- Spring Boot Reference: Embedded Web Servers section
- Baeldung "Spring Boot Actuator" at `baeldung.com/spring-boot-actuators`
- Spring Boot source: `spring-boot-project/spring-boot-actuator/`

**Key classes to study:**
- `ServletWebServerApplicationContext` — embedded Tomcat/Jetty/Undertow integration
- `TomcatServletWebServerFactory` — server configuration
- `Endpoint` annotation and `EndpointDiscoverer`
- `HealthIndicator` and `HealthContributor` interfaces

**Hands-on exercises:**
1. Implement a custom `@Endpoint` with `@ReadOperation`, `@WriteOperation`, and `@DeleteOperation`
2. Implement a custom `HealthIndicator` that checks an external dependency
3. Implement a custom `FailureAnalyzer` using `AbstractFailureAnalyzer<T>`

### Week 12: PropertySource resolution and configuration binding

**Study materials:**
- Spring Boot Reference: Externalized Configuration (property source order documentation)
- Spring Framework Reference: PropertySource and Environment sections

**Key concepts:**
- Property source precedence (17+ sources in specific order)
- `@ConfigurationProperties` binding mechanics
- Relaxed binding rules
- Configuration property validation with JSR-303

**Hands-on exercise:** Implement a custom `PropertySourceLoader` that reads configuration from an unconventional source (encrypted file, remote config server mock, etc.). Register it via `spring.factories`.

### Week 13: Kotlin-specific Spring features

**Study materials:**
- Official Kotlin support documentation at `docs.spring.io/spring-framework/reference/languages/kotlin.html`
- Spring Kotlin KDoc API at `docs.spring.io/spring-framework/docs/current/kdoc-api/`
- Baeldung "MockMvc Kotlin DSL" at `baeldung.com/kotlin/mockmvc-kotlin-dsl`

**Key features to master:**

**Bean Definition DSL:**
```kotlin
val beans = beans {
    bean<MyService>()
    bean { MyRepository(ref()) }
    profile("production") {
        bean<ProductionDataSource>()
    }
}
```

**Router DSL (WebFlux):**
```kotlin
@Bean
fun routes(handler: MyHandler) = coRouter {
    GET("/api/items", handler::list)
    POST("/api/items", handler::create)
}
```

**Coroutines support:** Understand how `suspend` functions work in controllers and how `Flow` integrates with reactive streams.

**Hands-on project:** Convert an existing Java/annotation-based Spring Boot application to use Kotlin functional bean definition DSL and router DSL. This reveals how much annotation processing Spring normally does.

---

## Phase 5: Contribution preparation (Weeks 14-16)

### Week 14: Development environment setup and codebase navigation

**Setup tasks:**
1. Clone Spring Framework: `git clone git@github.com:spring-projects/spring-framework.git`
2. Clone Spring Boot: `git clone git@github.com:spring-projects/spring-boot.git`
3. Install correct JDK (Spring Framework 7.x main branch requires **JDK 24**; 6.2.x branch requires JDK 17)
4. Use `.sdkmanrc` if using SDKMAN: `sdk env`
5. Build Spring Framework: `./gradlew build`
6. Build Spring Boot: `./gradlew publishToMavenLocal`

**IntelliJ IDEA setup:**
- Follow `github.com/spring-projects/spring-framework/blob/master/import-into-idea.md`
- Configure editor settings per wiki: use tabs (not spaces), set "Class count to use import with *" to 100
- Install Spring JavaFormat IntelliJ Plugin for Spring Boot contributions

**Codebase orientation:**
| Spring Framework Module | Purpose |
|------------------------|---------|
| `spring-core` | Fundamental utilities, resource abstraction |
| `spring-beans` | BeanFactory, IoC container core |
| `spring-context` | ApplicationContext, events, i18n |
| `spring-aop` | AOP implementation |
| `spring-expression` | SpEL |

| Spring Boot Module | Purpose |
|-------------------|---------|
| `spring-boot` | Core Boot functionality, SpringApplication |
| `spring-boot-autoconfigure` | All auto-configuration classes |
| `spring-boot-actuator` | Production monitoring |
| `spring-boot-starters` | Dependency aggregators |

### Week 15: Contribution workflow mastery

**Key contribution requirements (updated January 2025):**

Spring projects now use **Developer Certificate of Origin (DCO)** instead of CLA. Every commit must include:
```
A commit message

Closes gh-123
Signed-off-by: Your Name <email@example.com>
```

Use `git commit -s -m "message"` to add sign-off automatically.

**Code style requirements:**
- Run `./gradlew format` before committing (Spring Boot)
- Follow style guide at `github.com/spring-projects/spring-framework/wiki/Code-Style`
- Add Apache 2.0 license header to new files
- Add `@author` tag to modified classes
- Add `@since` tag to new public APIs

**Finding issues:**
- Search for label `status: ideal-for-contribution` — issues the team actively wants help with
- Filter by `theme: kotlin` for Kotlin-related improvements
- Filter by module: `in: core`, `in: web`

**Current Kotlin-related contribution opportunities:**
- Kotlin 2.x improvements (Spring Framework 7 uses Kotlin 2.x baseline)
- Kotlin value classes support
- Kotlin Serialization integration refinements
- Coroutines support enhancements

### Week 16: First contribution

**Approach:**
1. Find an issue labeled `ideal-for-contribution` or a documentation improvement
2. Comment on the issue expressing interest
3. Create a branch named after the issue (e.g., `gh-12345`)
4. Make changes following code style guidelines
5. Run test suite: `./gradlew build`
6. Submit PR against `main` branch with DCO sign-off

**Recommended first contributions:**
- Documentation fixes (Asciidoctor format)
- Test case additions for existing functionality
- Small bug fixes in existing releases
- Kotlin DSL enhancements

**Milestone:** Submit at least one pull request (even if it's documentation or a small fix) to either spring-framework or spring-boot repository.

---

## Essential resources organized by type

### Books (ranked by internals depth)
| Book | Authors | Year | Internals Depth |
|------|---------|------|-----------------|
| **Pro Spring 6** | Cosmina, Harrop, Schaefer, Ho | 2023 | Deepest — 938 pages |
| **Spring Boot in Practice** | Somnath Musib | 2022 | Strong (Ch 4 auto-config, Ch 10 Kotlin) |
| Spring in Action 6th Ed | Craig Walls | 2022 | Moderate |
| Professional Java Dev with Spring | Johnson, Hoeller et al. | 2005 | Historical — creator insights |

### Video courses (for internals focus)
| Course | Platform | Why Recommended |
|--------|----------|-----------------|
| **The Confident Spring Professional** | marcobehler.com | Builds from plain Java to Boot; best for understanding what Boot automates |
| **Learn Spring: The Master Class** | Baeldung | Comprehensive DI, AOP, Security depth |
| Spring: Framework in Depth | LinkedIn Learning | 2 hours covering IoC, lifecycle, AOP |
| Core Spring Learning Path | Pluralsight | Structured beginner-to-advanced |

### Conference talks (must-watch)
| Talk | Speaker | Topic |
|------|---------|-------|
| "It's a Kind of Magic" | Stéphane Nicoll, Brian Clozel | Auto-configuration deep dive |
| "Breaking the Magician's Code" | Phil Webb | Spring Boot internals |
| SpringOne Keynotes (annual) | Juergen Hoeller | Framework evolution |
| Spring I/O talks | Various | Technical deep dives |

**YouTube channels:** SpringDeveloper (official), Devoxx, Marco Behler

### Key blog posts and articles
- **Auto-configuration:** Marco Behler's guide at `marcobehler.com/guides/spring-boot-autoconfiguration`
- **Bean lifecycle:** HowToDoInJava article at `howtodoinjava.com/spring-core/spring-bean-life-cycle/`
- **BeanPostProcessor:** Baeldung at `baeldung.com/spring-beanpostprocessor`
- **CGLIB proxies:** Baeldung at `baeldung.com/cglib`
- **Custom starters:** Baeldung at `baeldung.com/spring-boot-custom-auto-configuration`

### GitHub repositories
| Repository | Purpose |
|------------|---------|
| `spring-projects/spring-framework` | Framework source |
| `spring-projects/spring-boot` | Boot source |
| `spring-projects-experimental/spring-fu` | KoFu functional Kotlin DSL (experimental) |
| `spring-petclinic/spring-petclinic-kotlin` | Reference Kotlin application |

---

## Hands-on project progression

| Week | Project | Key Learning |
|------|---------|--------------|
| 1-2 | Mini IoC container | DI fundamentals, reflection, BeanFactory |
| 3-4 | Custom BeanPostProcessor | Bean lifecycle, proxies |
| 7 | Parent-child context app | Context hierarchy |
| 8 | Custom SpringApplicationRunListener | Bootstrap sequence |
| 10 | Production starter | Complete auto-config |
| 11 | Custom actuator endpoint + HealthIndicator | Actuator internals |
| 12 | Custom PropertySourceLoader | Configuration resolution |
| 13 | Kotlin DSL refactoring | Kotlin-specific features |
| 16 | First OSS contribution | Contribution workflow |

---

## Success criteria by phase

**End of Phase 1 (Week 4):** Can explain IoC container architecture, draw bean lifecycle diagram, implement custom BeanPostProcessor/BeanFactoryPostProcessor.

**End of Phase 2 (Week 7):** Can create programmatic AOP proxies, explain JDK vs CGLIB proxy selection, build multi-context applications.

**End of Phase 3 (Week 10):** Can debug auto-configuration with condition report, build production-quality custom starters, trace SpringApplication bootstrap.

**End of Phase 4 (Week 13):** Can implement custom actuator endpoints, PropertySourceLoaders, FailureAnalyzers; proficient in Kotlin DSLs.

**End of Phase 5 (Week 16):** Development environment configured, first PR submitted, familiar with contribution workflow and codebase structure.

---

## Beyond the curriculum

After completing this curriculum, continue deepening expertise through:

- **Reading auto-configuration source code** — study `DataSourceAutoConfiguration`, `WebMvcAutoConfiguration`, `SecurityAutoConfiguration` as production patterns
- **Following Spring milestones** — subscribe to spring.io/blog and track GitHub releases
- **Attending Spring I/O** (Barcelona) or SpringOne conferences
- **Contributing regularly** — move from documentation fixes to feature implementations
- **Exploring Spring Cloud** internals if working with microservices

The path from "Spring user" to "Spring contributor" requires understanding not just *what* Spring does, but *why* its abstractions are designed the way they are. This curriculum provides that foundation through systematic study of source code, hands-on implementation of framework mechanics, and direct engagement with the open-source contribution process.