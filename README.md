# Claude Learning Plans

Structured, multi-week learning curricula for senior engineers who want deep mastery of backend, infrastructure, and systems topics.

## Overview

This repository contains 64 self-paced learning plans generated with Claude. Each plan follows a phased, project-based format designed for working engineers — typically 12–16 weeks of focused study with curated resources, hands-on milestones, and progressive complexity. Topics range from Spring Boot internals to Kubernetes, Go, and distributed data systems.

## Plans by Category

### Spring & Spring Boot

- [P50/P99 Latency Guide](opus-4.5/springboot_latency_p50_p99_guide.md) — Measuring and improving latency on JVM (ECS to EKS)
- [Production Guide to Spring Data JPA with Kotlin](opus-4.6/kotlin-jpa.md) — Entity design, compiler plugins, performance tuning, and N+1 prevention for Hibernate 6.x with Kotlin on Aurora MySQL/PostgreSQL
- [Spring Batch](opus-4.5/spring-batch.md) — 16-week Spring Batch mastery plan for Kotlin
- [Spring Batch Projects](opus-4.5/spring-batch-2.md) — 12 progressive Kotlin projects with Spring Batch
- [Spring Cloud Resiliency](opus-4.5/spring-cloud-resiliency.md) — Circuit breakers, retries, and fault tolerance patterns
- [Spring Cloud Scalability](opus-4.5/spring-cloud-scalability.md) — Microservices scalability patterns with Spring Cloud
- [Spring Framework & Boot Internals](opus-4.5/spring.md) — Deep dive into Spring's core abstractions and lifecycle
- [Spring Security 6.x](opus-4.5/spring-security.md) — Authentication, authorization, and OAuth2 for Kotlin
- [Spring WebFlux](opus-4.5/webflux.md) — Reactive web programming with Project Reactor

### JVM Internals

- [JVM Concurrency (from Node.js)](opus-4.5/jvm-concurrency.md) — Concurrency model transition from Node.js to Kotlin
- [JVM Concurrency Curriculum](opus-4.5/jvm-concurrency-2.md) — 16-week deep dive into threads, coroutines, and locks
- [JVM Performance Engineering](opus-4.5/jvm-performance-engineering.md) — GC tuning, profiling, and optimization on Kubernetes

### Build Tools

- [buildSrc vs build-logic](opus-4.5/buildSrc-vs-build-logic.md) — Comparing convention plugin approaches in Gradle
- [Gradle](opus-4.5/gradle.md) — Mastery-level Gradle for Spring Boot multi-project builds

### Data & Messaging

- [Apache Kafka](opus-4.5/kafka.md) — Kafka producers, consumers, and Streams for Spring Boot
- [Event-Driven Architecture](opus-4.5/event-driven-architecture.md) — Event sourcing and async patterns for Kotlin/Spring
- [Flyway Database Migrations](opus-4.6/db-migration.md) — Production Flyway migrations with Spring Boot, Kotlin, and Aurora MySQL
- [Flyway vs Liquibase vs Atlas](opus-4.6/flyway-liquibase.md) — Comparing database migration tools for Spring Boot Kotlin with MySQL/Aurora
- [HikariCP](opus-4.5/hikaricp.md) — Connection pool internals and tuning for Spring Boot
- [MySQL & Aurora Performance](opus-4.6/mysql-performance.md) — Deep dive into MySQL/Aurora performance engineering covering InnoDB internals, query optimization, and PostgreSQL architectural comparison for Spring Boot developers
- [MySQL Mastery](opus-4.6/mysql-mastery.md) — Definitive MySQL mastery plan covering essential books, InnoDB internals, Aurora-specific operations, and deliberate practice for Kotlin/Spring Boot developers
- [Redis](opus-4.5/redis.md) — Redis data structures, caching, and pub/sub patterns
- [Redis L2 Cache](opus-4.5/redis-l2-cache.md) — Redis as a high-traffic L2 cache for microservices
- [SQL Database Optimization](opus-4.5/sql-database-optimization.md) — Indexing, query tuning, and schema design over 16 weeks

### APIs & Protocols

- [GraphQL](opus-4.5/graphql.md) — GraphQL schema design and implementation in Spring Boot
- [WebSockets](opus-4.5/websocket.md) — Real-time communication with STOMP and Spring WebSocket

### Observability

- [Datadog Observability](opus-4.6/datadog.md) — Complete Datadog learning curriculum covering infrastructure monitoring, APM, log management, dashboards, and alerting for Kotlin/Spring Boot on AWS
- [Observability (o11y)](opus-4.5/o11y.md) — Metrics, tracing, and logging for Spring Boot microservices
- [Observability for Spring Boot on EKS](opus-4.6/o11y.md) — 26-week mastery plan covering metrics, logs, traces, alerting, SRE practices, and infrastructure deployment for Spring Boot on AWS EKS
- [Observability Fundamentals for Kotlin Spring Boot on EKS](opus-4.6/o11y2.md) — Mastery plan covering observability fundamentals, tools landscape, and Spring Boot-native instrumentation for Kotlin microservices on EKS
- [OpenTelemetry for Spring Boot in Kotlin](opus-4.6/otel-spring-boot.md) — 12-16 week mastery plan for OpenTelemetry with Spring Boot covering metrics, traces, logs, OTel Collector, Datadog, and Grafana stack on EKS

### Infrastructure

- [Kubernetes](opus-4.5/kubernetes.md) — Mastery-level K8s for Spring Boot deployments
- [Kubernetes Mastery for EKS](opus-4.6/k8s.md) — 24-week curriculum from K8s fundamentals to production EKS mastery with CKAD, CKA, and CKS certification milestones for Spring Boot engineers
- [Terraform](opus-4.5/terraform.md) — Infrastructure as code for AWS container deployments

### Languages & Paradigms

- [Arrow-kt for DDD](opus-4.5/arrow-for-ddd.md) — Functional domain-driven design with Arrow 2.x
- [Functional Programming](opus-4.5/fp.md) — FP foundations and patterns for JVM developers
- [Go](opus-4.5/go.md) — Complete Go roadmap for engineers coming from the JVM
- [Swift](opus-4.5/swift.md) — From Kotlin to native macOS development over 16 weeks

### NewSQL

- [NewSQL (ChatGPT)](opus-4.5/newsql-chatgpt.md) — NewSQL research notes from a ChatGPT perspective
- [NewSQL (Claude)](opus-4.5/newsql-claude.md) — Globally distributed active-active NewSQL databases

### API Design

- [REST Architecture](opus-4.6/rest.md) — What REST actually means per Fielding's dissertation, the six constraints, HATEOAS, and why most APIs aren't truly RESTful

### Backend & Infrastructure

- [Mastery-level microservices learning plan for Spring Boot engineers](opus-4.6/microservice-ddd.md) — 24-week curriculum transforming mid-level Kotlin/Spring Boot engineers into microservices architects, covering DDD, bounded contexts, decomposition strategy, and distributed patterns on AWS EKS/ECS.
- [Spring Cloud mastery roadmap for Kotlin engineers on AWS EKS](opus-4.6/spring-cloud.md) — 26-week curriculum taking Kotlin/Spring Boot developers from zero Spring Cloud knowledge to production-ready microservices on AWS EKS, covering service discovery, config management, and Kubernetes-native migration.

### Backend Engineering

- [Distributed Lock Use Cases](opus-4.6/distributed-lock-use-cases.md) — Catalog of distributed concurrency scenarios across e-commerce, fintech, and ticketing with production case studies and a decision framework for Redis, pessimistic, and optimistic locking
- [Legacy Code Modernization](opus-4.6/legacy-code.md) — Resource guide for legacy system modernization covering characterization tests, Spring Modulith, strangler fig patterns, and CDC-based decoupling for Kotlin/Spring Boot

### Career Development

- [Soft Skills for Software Engineers](opus-4.6/soft-skills.md) — Curated guide to books, courses, podcasts, and communities for communication, managing up, and engineering leadership

### Database

- [MySQL Slow Query Tuning on Aurora](opus-4.6/slow-query-tuning-mysql.md) — Production playbook for finding, analyzing, and fixing slow queries on Aurora MySQL 3.x and 2.x
- [트랜잭션 (Transactions)](opus-4.6/transaction.md) — Database transaction fundamentals including ACID properties, isolation levels, commit/rollback, and practical scenarios (Korean).

### Databases

- [The Definitive Guide to InnoDB Deadlocks](opus-4.6/innodb-deadlock.md) — Comprehensive guide to InnoDB deadlock internals, six reproducible scenarios, detection tooling for MySQL 8.0 and Aurora, prevention strategies, and Spring Boot/Kotlin resilience patterns.

### Developer Tools

- [Jujutsu Version Control](opus-4.6/jujutsu.md) — Comprehensive guide to Jujutsu (jj), a Git-compatible VCS that eliminates the staging area, makes every state a commit, and provides universal undo
- [Linear Project Management](opus-4.6/linear.md) — Comprehensive assessment of Linear for developer teams covering planning, sprint management, GitHub integration, and workflow automation
- [Stacked PRs with Jujutsu](opus-4.6/stacked-pr-jujutsu.md) — Guide to stacked pull requests and Jujutsu (jj) for breaking large changes into small, reviewable units with effortless rebasing

### Distributed Systems / Messaging

- [Mastering Apache Kafka](opus-4.6/kafka.md) — 6-month roadmap for Kotlin/Spring Boot developers covering Kafka architecture, Spring Kafka patterns, Kafka Streams, Schema Registry, monitoring, and CCDAK certification

### Distributed Systems / Workflow

- [Mastering Durable Execution on the JVM](opus-4.6/durable-execution.md) — 8–10 week roadmap covering Temporal, Restate, saga patterns, workflow versioning, and production-grade durable execution with Kotlin and Spring Boot

### Finance & Trading

- [High-Frequency Trading Learning Path](opus-4.6/hft.md) — Transition from Spring Boot to sub-microsecond HFT systems
- [Production Quant Roadmap](opus-4.6/quant.md) — Complete learning path from pure math PhD to production quant

### Git

- [Advanced Git for Team Workflows](opus-4.6/git.md) — Curated resource guide for experienced developers transitioning from solo to team Git, covering branching strategies, PR workflows, conflict resolution, and collaboration tools.

### Performance & Optimization

- [Performance Optimization Playbook](opus-4.6/godbolt-rady-performance-optimization.md) — Godbolt-Rady measure-first performance optimization from Two's Complement

### Rust

- [Rust Mastery for DataFusion/Arrow](opus-4.6/rust.md) — 10-month phased plan from Rust foundations to active Apache DataFusion and Arrow contributor, tailored for JVM engineers

### Spring

- [Spring Batch](opus-4.6/spring-batch.md) — 6-month Spring Batch mastery plan covering chunk-oriented processing, partitioning, fault tolerance, and AWS EKS/ECS deployment for Kotlin developers
- [Spring Framework Internals](opus-4.6/spring.md) — 14-week deep-dive into Spring IoC container, AOP proxies, auto-configuration mechanics, and framework extension patterns
- [Spring Security Mastery](opus-4.6/spring-security.md) — 30-week depth-first curriculum covering filter chain internals, OAuth2/OIDC, microservices auth, reactive security, and OWASP hardening

### Spring / Reactive

- [Mastering Spring WebFlux](opus-4.6/webflux.md) — 14-week learning plan for Kotlin engineers covering Project Reactor, Spring WebFlux, R2DBC, reactive Redis/Kafka, and production observability

### Spring / Real-Time

- [Mastering WebSockets in Spring Boot](opus-4.6/websocket.md) — 12-week curriculum covering STOMP messaging, reactive WebFlux WebSocket, Redis Pub/Sub broadcasting, Kafka integration, and AWS EKS deployment for real-time systems

## How to Use These Plans

Each plan is a standalone Markdown file structured around:

1. **Phases** — Progressive stages from foundations to advanced topics, typically spanning 12–16 weeks.
2. **Milestones** — Concrete projects and exercises at each phase to validate understanding.
3. **Curated Resources** — Books, documentation, talks, and blog posts selected for each topic.

Pick a plan that matches your current learning goal, work through the phases at your own pace, and use the milestones to gauge progress.
