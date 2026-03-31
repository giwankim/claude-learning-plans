---
title: "Feature Flags in Spring Boot and Kotlin"
category: "Spring"
description: "Complete guide to feature flags covering the four-type taxonomy, DIY vs platform approaches, Spring Boot 3.x integration, and flag lifecycle management for Kotlin microservices"
---

# Feature flags in Spring Boot and Kotlin: a complete guide

**Feature flags — conditional code paths controlled by external configuration — have become the backbone of modern continuous delivery.** They decouple deployment from release, letting teams ship code to production daily while controlling exactly who sees what, when. This guide covers the conceptual foundations, the full spectrum of implementation approaches for Spring Boot 3.x and Kotlin, trade-offs between DIY and platform solutions, and hard-won lessons from Korean and global engineering teams. The bottom line: every team shipping Kotlin microservices should adopt feature flags, but the right approach depends on team size, experimentation needs, and willingness to manage "flag debt."

## The concept and its four-type taxonomy

A feature flag is a conditional statement — an `if/else` — whose branch is determined not by code logic but by external configuration changeable at runtime. The core insight, popularized by **Flickr's engineering team in 2009** and codified by Jez Humble and David Farley in *Continuous Delivery* (2010), is simple: deploy code frequently, release features independently.

Pete Hodgson's definitive 2016 article on martinfowler.com established the taxonomy that the industry still uses. He classifies flags along two dimensions — **longevity** (how long the flag lives) and **dynamism** (how granularly the toggle decision is made) — producing four categories:

**Release Toggles** are short-lived and static. They hide incomplete features behind disabled paths so teams can commit to trunk daily. Once the feature is fully rolled out, the flag should be removed within days or weeks. These are the most common type and the most prone to becoming stale. Fowler himself warns that release toggles should be a last resort — breaking features into small, safely releasable increments is preferable.

**Experiment Toggles** are medium-lived and highly dynamic. They route individual users into A/B test cohorts using consistent hashing, enabling data-driven product decisions. Hodgson frames these as resolving "contentious product debates based on data, rather than HiPPOs" (Highest Paid Person's Opinion). They must persist long enough for statistical significance, then be removed.

**Ops Toggles** control operational behavior — kill switches that let SRE teams disable non-critical features during peak load. Some are short-lived (for a risky rollout); others become permanent, manually managed circuit breakers. They require near-instant runtime reconfigurability; waiting for a deployment to flip an ops toggle defeats the purpose.

**Permission Toggles** gate features by user segment — premium features for paying users, alpha features for internal dogfooding, beta access for select groups. These are the longest-lived, sometimes permanent, and always per-request dynamic. LaunchDarkly calls these "entitlement flags."

Beyond Hodgson's taxonomy, LaunchDarkly adds **migration flags** (for system/database migrations) and **kill switch flags** as first-class categories. The trunk-based development community treats flags primarily as enablers of branchless workflows.

## When feature flags become dangerous

The most cautionary tale remains **Knight Capital's $460 million loss in 45 minutes** on August 1, 2012. During a manual deployment across 8 servers, one server was missed. When a repurposed feature flag was activated, that server executed dead code from 2003 — a trading algorithm that bought high and sold low in an infinite loop. The attempted fix made it worse. The lessons are stark: never reuse flag names, always remove dead code, automate deployments, and maintain kill switch procedures.

Feature flags should not be used for every change. Bug fixes and minor tweaks don't warrant the overhead. Flags should never substitute for proper architecture — they mask the need for service decomposition or API versioning when left in place too long. Each flag doubles the theoretical testing surface area; with N flags, **2^N possible states** exist. Performance degrades as flag evaluation accumulates. Client-side flags can leak unreleased features to determined users. And the most insidious risk is cultural: teams start treating flags as safety nets that excuse shipping untested code.

## DIY implementation patterns in Spring Boot and Kotlin

The simplest approach uses Spring's built-in mechanisms. **`@ConditionalOnProperty`** conditionally loads beans at startup based on `application.yml` values — effective for infrastructure-level toggles but requires a restart to change:

```kotlin
@Configuration
@ConditionalOnProperty(name = ["features.new-checkout"], havingValue = "true")
class NewCheckoutConfig {
    @Bean
    fun checkoutService(): CheckoutService = NewCheckoutService()
}
```

For runtime-flexible flags, **`@ConfigurationProperties`** provides type-safe access to a `features:` block in YAML, though changes still require a restart unless paired with Spring Cloud Config's `@RefreshScope`. Database-backed flags offer true runtime toggling — a JPA entity storing flag name, enabled state, and description, wrapped in a service with `@Cacheable` for performance — but require building your own admin UI, caching layer, and targeting logic.

Spring Profiles (`@Profile("experimental")`) work as the crudest flag mechanism — per-environment, not per-user. Environment variables via `@Value("${FEATURE_X:false}")` integrate well with Kubernetes ConfigMaps but share the same restart limitation.

The DIY path costs nothing upfront but grows expensive fast. You'll eventually need percentage rollouts (consistent hashing by user ID), audit trails, an admin dashboard, and cleanup tooling — all of which dedicated libraries already provide.

## Open-source libraries: Togglz, FF4J, Unleash, and OpenFeature

**Togglz** (v4.6.1, ~1,000 GitHub stars) is the most Kotlin-friendly option. Its `togglz-kotlin` module provides enum-based feature definitions with `@Label` and `@EnabledByDefault` annotations. The `togglz-spring-boot-starter` auto-configures everything, including an admin console at `/togglz-console` and a Spring Boot Actuator endpoint. Built-in activation strategies include username-based, role-based, **gradual percentage rollout**, release date, and script engine strategies. State can be stored in memory, files, JDBC, or Redis. Version 4.0+ requires Spring Boot 3 and Java 17 — fully aligned with modern Kotlin stacks.

**FF4J** (v2.1 core, ~1,400 GitHub stars) is the most feature-complete JVM library. Its standout capabilities are a built-in **audit event repository**, AOP-driven toggling via `@Flip` annotations (swapping interface implementations at runtime without if/else), a property store for dynamic configuration beyond booleans, and support for **20+ storage backends** including MongoDB, Redis, Cassandra, DynamoDB, and Elasticsearch. The web console supports 10+ languages. The trade-off is slightly less polished Spring Boot 3 support compared to Togglz.

**Unleash** (v12.0.0 Java SDK, ~12,000 GitHub stars) is the most popular open-source platform, operating as a client-server architecture: a Node.js+PostgreSQL server with a rich admin UI, plus client SDKs that fetch and cache flag configurations locally. The Java SDK evaluates flags client-side using the **Yggdrasil engine** (a Rust-based evaluation core), ensuring privacy and low latency. Strategies include percentage rollouts by user ID or session, IP targeting, and custom strategies. The Spring Boot starter provides a `@Toggle` annotation for AOP-style implementation swapping. Self-hosting is free; cloud plans start at **$49/month**.

**OpenFeature** (CNCF Incubating, Java SDK v1.20.2) is the emerging vendor-agnostic standard — "OpenTelemetry for feature flags." It defines a standard evaluation API (`getBooleanValue`, `getStringValue`, etc.), provider interfaces that any vendor can implement, evaluation context for targeting data, and hooks for lifecycle callbacks. Providers exist for LaunchDarkly, Unleash, Flagsmith, ConfigCat, Flipt, and the reference **flagd** daemon. The key value proposition is **portability**: switch from one flag provider to another without changing application code. Korean e-commerce platform 11st (11번가) adopted OpenFeature + flagd on Kubernetes for exactly this reason.

## Commercial platforms and cloud-native options

**LaunchDarkly** dominates the market with 5,500+ customers. Its Java SDK (v7.x) uses SSE streaming for near-instant flag updates. Key differentiators include advanced targeting rules, percentage rollouts with guardrail metrics, built-in experimentation with statistical analysis, approval workflows, and **stale flag detection with automated cleanup workflows**. Pricing starts free (developer tier) and scales to **$12/service connection/month** on Foundation, with enterprise contracts averaging ~$72,000/year. An experimental Spring Boot starter from `launchdarkly-labs` auto-configures the `LDClient` bean.

**Split.io**, acquired by **Harness in June 2024** and rebranded as Harness Feature Management & Experimentation (FME), differentiates through measurement. Its SDK evaluates flags locally using Murmur hash bucketing, connecting flag states to business metrics for automated impact detection. Existing SDK integrations required no code changes post-acquisition.

**ConfigCat** positions itself as the affordable alternative: **all features available on every plan including Free**, with pricing based only on usage limits, not team size or MAUs. Its Java SDK downloads flag configuration from a CDN and evaluates entirely locally. Plans start at **$55/month** for Pro. The trade-off: no built-in experimentation and less enterprise governance.

**Flagsmith** offers a fully **open-source (BSD 3-Clause) self-hosted** option with no API request limits, plus a cloud offering starting at $45/month. It's a founding member of OpenFeature. For teams wanting open-source with a polished UI, Flagsmith fills the gap between DIY libraries and commercial SaaS.

**AWS AppConfig** provides managed feature flags within AWS Systems Manager. Since July 2024, it supports **advanced targeting and traffic-splitting** for A/B tests. Pricing is pure pay-per-use (~$0.0000002/request), making it extremely cost-effective for AWS-native stacks. The limitation: no official Spring Boot starter and no built-in data analysis for experiments.

**Spring Cloud Config** can manage flags as externalized properties in a Git-backed config server, with `@RefreshScope` enabling runtime changes and Spring Cloud Bus broadcasting refreshes across instances via RabbitMQ or Kafka. It's free and native to Spring, but lacks targeting rules, percentage rollouts, admin UI, and audit trails — suitable only for simple boolean on/off flags.

## How the approaches compare in practice

| Dimension | DIY (Config/DB) | Library (Togglz/FF4J) | OSS Platform (Unleash) | Commercial SaaS |
|---|---|---|---|---|
| **Setup cost** | Minutes | Hours | Half-day (server + SDK) | Hours (SDK + dashboard) |
| **Runtime toggling** | Requires restart or custom code | Built-in | Built-in with streaming | Near-instant via SSE |
| **User targeting** | Must build hashing/bucketing | Basic (percentage, role) | Rich (segments, constraints) | Advanced (attributes, ML) |
| **A/B testing** | Very difficult to build correctly | Need separate analytics | Variants supported | Integrated statistical engine |
| **Audit trail** | Must build | FF4J only | Built-in | Full with RBAC |
| **Admin UI** | Must build | Web console included | Full web dashboard | Polished multi-team dashboard |
| **Flag cleanup tooling** | None | None | Marks stale flags after TTL | Code references, automated alerts |
| **Cost at scale** | Engineering time only | Free (OSS) + hosting | Free self-hosted; $49+/mo cloud | $12/svc/mo to $70K+/yr enterprise |
| **Vendor lock-in** | None | Low (Togglz/FF4J API) | Moderate (Unleash API) | High — mitigated by OpenFeature |

The recommended progression: **solo/small teams** start with Togglz or Flipt (free, embedded). **Teams of 5–15** should adopt Flagsmith or Unleash with RBAC and quarterly flag audits, targeting fewer than 30 active flags. **Teams of 15–50** benefit from LaunchDarkly or Statsig with full governance. **At 50+ engineers**, a dedicated platform with automated rollout progression, anomaly detection, and centralized lifecycle management becomes essential.

## Lifecycle management and the fight against flag debt

Uber documented their flag debt problem openly: inactive toggles were "bloating apps" and degrading performance. They built **Piranha**, an automated AST-based refactoring tool that generated cleanup diffs for 1,381 flags, deleting **71,000+ lines of code**. 65% of diffs landed without manual changes. This was published at ICSE 2020.

The feature flag lifecycle should follow five stages: **creation** (with name, type, owner, and expiration date, reviewed in PR), **development** (flag OFF in production, ON in dev), **rollout** (progressive delivery through internal → canary → beta → GA), **stabilization** (flag at 100% for 7–14 days with metrics confirmed stable), and **cleanup** (flag removed from code within 30 days of GA). The most effective teams set "time bombs" — tests that fail if a flag outlives its expiration date — and enforce a Lean inventory limit: to add a new flag, you must remove an existing one.

Testing with feature flags does not require covering all 2^N combinations. Fowler's guidance is pragmatic: run two configurations — all flags as they'll be in the next release, and all flags as they are in current production. Test each individual flag's ON and OFF paths. GitHub runs two CI builds: one with all flags disabled, one with all flags enabled. For kill switches, regularly exercise the OFF path ("Chaos Toggling") to prevent fallback bit rot.

In microservices, the critical challenge is **cross-service consistency**. When a request traverses services A → B → C, each service evaluating flags independently can produce "split-brain" behavior. The solution: evaluate all flags at the request entry point and propagate context via W3C Trace Context Baggage headers or OpenFeature's Transaction Context Propagator (ThreadLocal in Java). CloudBees warns explicitly: **do not build a feature flag microservice**. Flags are a cross-cutting concern like logging — embed them as libraries in each service with centralized configuration.

## Korean engineering teams lead with custom platforms

Korean tech companies have embraced feature flags deeply, often building custom platforms tailored to their specific needs.

**Woowahan Brothers (배달의민족)** built a dedicated experimentation platform that unifies A/B testing and feature flags into a single system. Feature flags share the same data structure as experiments internally. They use **Redis for flag storage with local caching** to handle the load from all internal services depending on the group distribution API, with Airflow pipelines for data extraction across services.

**Karrot (당근) Money Service Team** adopted feature flags to enable daily deployments, migrating from Git Flow to GitHub Flow plus feature toggles. They built a custom **Spring AOP-based system** with a `@FeatureToggle` annotation and `FeatureToggleProvider`, using modulo operations on user IDs for canary group assignment. Their JSON configuration supports per-flag canary percentages. They estimate feature flags contributed **over 70% to enabling daily deployment capability**, but warn about "toggle debt" spreading across codebases like broken windows.

**11st (11번가)** stands out for adopting the **OpenFeature + flagd** (CNCF) stack on their Kubernetes-based MSA platform "Vine." Their specific use case: switching between REST and gRPC calls at runtime for a company-wide library, deploying safely to production without confidence in high-traffic gRPC behavior. They emphasized that Spring Boot profiles alone are insufficient — flags must be externalized and dynamically changeable without redeployment.

**Ohouse (오늘의집)** built a custom A/B experiment platform on EKS with Flask, stress-tested at **10x peak TPS** achieving TP95 of 30ms, using Kafka Streams for real-time log streaming. **KakaoPay** outgrew the open-source Wasabi A/B platform and built a custom system with MySQL and MongoDB, planning to add feature flags as a future capability. **Toss** embeds experimentation deeply into their data-driven culture with gradual rollout strategies, though they haven't published a dedicated feature flag architecture post. The Korean SaaS platform **Hackle (핵클)** provides A/B testing and feature flags as a unified product widely adopted in the Korean market.

## How global companies use flags at scale

**Netflix** runs thousands of A/B tests simultaneously, propagating flag changes via **Kafka** across hundreds of microservices. They use deterministic hashing (userId + experimentName) for consistent group assignment and treat flags as "safety valves" — instantly disabling recommendation engines or analytics under load.

**GitHub** runs two CI builds per commit (flags on and flags off), uses a rubocop-ast script to automatically delete flag-related code blocks when retiring flags, and provides a web UI accessible to most engineers for flag management. Their rollout strategies progress through individual actors → staff shipping → early access groups → percentage rollouts → dark shipping.

**Meta's Gatekeeper** system enables quasi-continuous releases with the pattern `if (gatekeeper_allowed('feature_name', $user))`. It supports internal usage testing across thousands of employees, staged country-level rollouts, and dark launches — exposing features to production load before users see them.

**Spotify** evolved from ABBA (2013, with 1:1 mapping between experiments and flags) to a full Experimentation Platform, now offered externally as Confidence. They use deterministic hashing for cross-platform consistency (same user gets same variant on iPhone and desktop) and support mutually exclusive experiments — critical for ML model testing. They report an **80% reduction in deployment risks** from robust feature flagging.

## Conclusion

Feature flags are not optional for teams practicing continuous delivery with Spring Boot and Kotlin — they are infrastructure. The four-type taxonomy (release, experiment, ops, permission) should guide both technical implementation and organizational governance. For most Kotlin/Spring Boot teams, the practical starting point is **Togglz for embedded flags** or **Unleash for platform-level management**, with OpenFeature as the abstraction layer that prevents vendor lock-in. Korean engineering teams at 배달의민족, 당근, and 11번가 demonstrate that the real engineering challenge isn't adding flags — it's building the discipline to remove them. The $460 million Knight Capital loss and Uber's 71,000-line cleanup effort prove that flag debt compounds faster than technical debt. Set expiration dates, automate cleanup, and treat every flag as inventory with a carrying cost.