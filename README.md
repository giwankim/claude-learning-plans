# Claude Learning Plans

Structured, multi-week learning curricula for senior engineers who want deep mastery of backend, infrastructure, and systems topics.

## Overview

This repository contains 34 self-paced learning plans generated with Claude. Each plan follows a phased, project-based format designed for working engineers — typically 12–16 weeks of focused study with curated resources, hands-on milestones, and progressive complexity. Topics range from Spring Boot internals to Kubernetes, Go, and distributed data systems.

## Plans by Category

### Spring & Spring Boot

- [P50/P99 Latency Guide](springboot_latency_p50_p99_guide.md) — Measuring and improving latency on JVM (ECS to EKS)
- [Spring Batch](spring-batch.md) — 16-week Spring Batch mastery plan for Kotlin
- [Spring Batch Projects](spring-batch-2.md) — 12 progressive Kotlin projects with Spring Batch
- [Spring Cloud Resiliency](spring-cloud-resiliency.md) — Circuit breakers, retries, and fault tolerance patterns
- [Spring Cloud Scalability](spring-cloud-scalability.md) — Microservices scalability patterns with Spring Cloud
- [Spring Framework & Boot Internals](spring.md) — Deep dive into Spring's core abstractions and lifecycle
- [Spring Security 6.x](spring-security.md) — Authentication, authorization, and OAuth2 for Kotlin
- [Spring WebFlux](webflux.md) — Reactive web programming with Project Reactor

### JVM Internals

- [JVM Concurrency (from Node.js)](jvm-concurrency.md) — Concurrency model transition from Node.js to Kotlin
- [JVM Concurrency Curriculum](jvm-concurrency-2.md) — 16-week deep dive into threads, coroutines, and locks
- [JVM Performance Engineering](jvm-performance-engineering.md) — GC tuning, profiling, and optimization on Kubernetes

### Build Tools

- [buildSrc vs build-logic](buildSrc-vs-build-logic.md) — Comparing convention plugin approaches in Gradle
- [Gradle](gradle.md) — Mastery-level Gradle for Spring Boot multi-project builds

### Data & Messaging

- [Apache Kafka](kafka.md) — Kafka producers, consumers, and Streams for Spring Boot
- [Event-Driven Architecture](event-driven-architecture.md) — Event sourcing and async patterns for Kotlin/Spring
- [HikariCP](hikaricp.md) — Connection pool internals and tuning for Spring Boot
- [Redis](redis.md) — Redis data structures, caching, and pub/sub patterns
- [Redis L2 Cache](redis-l2-cache.md) — Redis as a high-traffic L2 cache for microservices
- [SQL Database Optimization](sql-database-optimization.md) — Indexing, query tuning, and schema design over 16 weeks

### APIs & Protocols

- [GraphQL](graphql.md) — GraphQL schema design and implementation in Spring Boot
- [WebSockets](websocket.md) — Real-time communication with STOMP and Spring WebSocket

### Observability

- [Observability (o11y)](o11y.md) — Metrics, tracing, and logging for Spring Boot microservices
- [Observability for Spring Boot on EKS](opus-4.6/011y.md) — 26-week mastery plan covering metrics, logs, traces, alerting, SRE practices, and infrastructure deployment for Spring Boot on AWS EKS

### Infrastructure

- [Kubernetes](kubernetes.md) — Mastery-level K8s for Spring Boot deployments
- [Terraform](terraform.md) — Infrastructure as code for AWS container deployments

### Languages & Paradigms

- [Arrow-kt for DDD](arrow-for-DDD.md) — Functional domain-driven design with Arrow 2.x
- [Functional Programming](fp.md) — FP foundations and patterns for JVM developers
- [Go](go.md) — Complete Go roadmap for engineers coming from the JVM
- [Swift](swift.md) — From Kotlin to native macOS development over 16 weeks

### NewSQL

- [NewSQL (ChatGPT)](newsql-chatgpt.md) — NewSQL research notes from a ChatGPT perspective
- [NewSQL (Claude)](newsql-claude.md) — Globally distributed active-active NewSQL databases

### Rust

- [Rust Mastery for DataFusion/Arrow](opus-4.6/rust.md) — 10-month phased plan from Rust foundations to active Apache DataFusion and Arrow contributor, tailored for JVM engineers

### Spring

- [Spring Framework Internals](opus-4.6/spring.md) — 14-week deep-dive into Spring IoC container, AOP proxies, auto-configuration mechanics, and framework extension patterns
- [Spring Security Mastery](opus-4.6/spring-security.md) — 30-week depth-first curriculum covering filter chain internals, OAuth2/OIDC, microservices auth, reactive security, and OWASP hardening

## How to Use These Plans

Each plan is a standalone Markdown file structured around:

1. **Phases** — Progressive stages from foundations to advanced topics, typically spanning 12–16 weeks.
2. **Milestones** — Concrete projects and exercises at each phase to validate understanding.
3. **Curated Resources** — Books, documentation, talks, and blog posts selected for each topic.

Pick a plan that matches your current learning goal, work through the phases at your own pace, and use the milestones to gauge progress.
