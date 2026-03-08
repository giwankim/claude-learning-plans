---
title: "Legacy Code Modernization"
category: "Backend Engineering"
description: "Resource guide for legacy system modernization covering characterization tests, Spring Modulith, strangler fig patterns, and CDC-based decoupling for Kotlin/Spring Boot"
---

# The definitive resource guide for taming legacy systems in Kotlin and Spring Boot

The single most important resource for any engineer facing legacy code remains Michael Feathers' *Working Effectively with Legacy Code* — its concepts of **seams**, **characterization tests**, and the **Legacy Code Change Algorithm** form the foundational vocabulary the entire industry uses. Pair it with Sam Newman's *Monolith to Microservices* for migration patterns and you have roughly 80% of the strategic toolkit covered. But the landscape of resources has expanded dramatically since 2022, with Spring Modulith emerging as a preferred intermediate step, Korean tech companies publishing battle-tested migration playbooks, and Kafka-based CDC becoming the go-to decoupling mechanism. This guide organizes the best resources across books, courses, articles, and code repositories — curated for a Kotlin/Spring Boot engineer working across all four phases of legacy modernization.

---

## The essential bookshelf: ten books ranked by impact

**Working Effectively with Legacy Code** by Michael Feathers (2004) is non-negotiable. Despite its age, no book has replaced it. Feathers defines legacy code simply as "code without tests" and provides **24 dependency-breaking techniques** that translate almost directly from Java to Kotlin. The most critical chapters for your context: Chapter 4 introduces the **Seam Model** — places where behavior can be altered without editing code; Chapter 13 covers **characterization tests** for capturing existing behavior before refactoring; Chapters 9–10 address getting classes into test harnesses; and Chapter 6 teaches Sprout Method/Sprout Class for safely adding new functionality alongside old code. The problem-oriented chapter naming ("I Can't Get This Class Into a Test Harness") makes it function as a reference guide you'll return to repeatedly.

**Monolith to Microservices** by Sam Newman (2019) is the tactical companion. Chapter 3 is the heart — it details the **Strangler Fig pattern** (HTTP proxy–based request rerouting), **Branch by Abstraction** (internal abstraction layers for deeper refactoring), **Parallel Run** (comparing old and new systems simultaneously, citing GitHub's Scientist library), and **Change Data Capture** for Kafka-based decoupling. Chapter 4 on database decomposition covers the hardest part of any migration: splitting shared data stores using patterns like Database View, Tracer Write, and Split Table. Newman honestly evaluates when microservices are simply the wrong answer.

**Refactoring: Improving the Design of Existing Code** (2nd Edition) by Martin Fowler (2018) catalogs ~70 refactoring patterns with smaller, more incremental steps than the first edition — specifically beneficial for legacy work. Chapter 3's code smell taxonomy (Long Function, Shotgun Surgery, Feature Envy) gives you diagnostic vocabulary, while Chapter 4 dedicates itself to building test infrastructure before any refactoring begins. IntelliJ IDEA automates most of these refactorings for Kotlin, making the patterns immediately actionable.

The remaining essential books each fill a distinct niche. **Domain-Driven Design** by Eric Evans (2003) provides the strategic compass — Part IV on Bounded Contexts, Context Maps, and the **Anti-Corruption Layer** tells you *where* to draw service boundaries. **Implementing Domain-Driven Design** by Vaughn Vernon (2013) bridges Evans' theory to JVM implementation with Java examples directly transferable to Kotlin, covering Hexagonal Architecture and Domain Events. **Kill It with Fire** by Marianne Bellotti (2021) is the only book addressing organizational dynamics — coalition building, managing stakeholder expectations, and overcoming inertia; Chapter 5 on "Building and Protecting Momentum" is essential for tech leads. **Designing Event-Driven Systems** by Ben Stopford (2018, free from Confluent) is the Kafka architecture bible, with Chapter 7's section on **Change Data Capture for unlocking legacy systems** showing how to stream changes from legacy databases into Kafka without modifying the source system.

Three more recent additions round out the shelf: **Software Design X-Rays** by Adam Tornhill (2018) uses git log analysis to identify hotspots and temporal coupling — a data-driven approach to prioritizing what to modernize first. **Refactoring at Scale** by Maude Lemaire (2020), drawn from Slack's growth from 100 to 1,200 engineers, covers feature flags, monitoring, and managing parallel development during large refactoring projects. **The Programmer's Brain** by Felienne Hermans (2021) applies cognitive science to the challenge of reading and understanding unfamiliar codebases.

---

## Courses and video content worth your time

The highest-value free content comes from conference talks. **Sam Newman's "Monolith Decomposition Patterns"** at GOTO 2019 (available on YouTube) is essential viewing — a 45-minute masterclass on Strangler Fig, Branch by Abstraction, and Change Data Capture, with the memorable warning that "the monolith is not the enemy." His QCon London 2020 version adds stronger emphasis on modular monoliths as an alternative. **Michael Feathers' 2024 interview on GOTO** revisits his techniques 20 years later, including how AI tools can assist with legacy code understanding. Alexandra Noonan's QCon talk **"To Microservices and Back Again"** provides the essential cautionary tale of Segment migrating to microservices, then back.

For hands-on practice, **Emily Bache's Gilded Rose Refactoring Kata** (GitHub, available in Kotlin) is the premier exercise for practicing characterization testing and safe refactoring. Bache has recorded video screencasts solving the kata with Approval Tests and Mutation Testing — watch these after attempting it yourself. Her broader YouTube presence covers approval testing techniques extensively.

Among paid platforms, Pluralsight offers **"Domain-Driven Design: Working with Legacy Projects"** by Vladimir Khorikov, which directly bridges DDD with legacy modernization including Anti-Corruption Layers and the Strangler pattern. On Udemy, **"Refactoring Legacy Code like a Pro"** by Charfaoui Younes is notable as one of the rare courses using **Kotlin** as the primary language. For Kafka-based decoupling, Ali Gelenler's **"Event-Driven Microservices: Spring Boot, Kafka and Elastic"** and his companion course on Clean Architecture with DDD, SAGA, Outbox, and Kafka cover the full spectrum of event-driven patterns with Spring Boot.

The most exciting recent content centers on **Spring Modulith**. JetBrains published **"Building Modular Monoliths With Kotlin and Spring"** (February 2026) showing exactly how to use Spring Modulith in a Kotlin application with working GitHub examples. The companion piece **"Migrating to Modular Monolith using Spring Modulith and IntelliJ IDEA"** provides step-by-step migration guidance. Codecentric's article on **Spring Modulith with Kotlin and Hexagonal Architecture** specifically addresses legacy systems, noting that individual modules can be declared as "open" for codebases that don't allow immediate clean separation. This Spring Modulith path — modularize first, extract to microservices later if needed — is emerging as **the preferred 2024–2026 approach** for Spring Boot legacy modernization.

---

## Blog posts and articles from the engineering trenches

Martin Fowler's writing remains the canonical starting point. His **"Strangler Fig Application"** article was significantly rewritten in August 2024, adding modern context and linking to the "Patterns of Legacy Displacement" catalog by Ian Cartwright, Rob Horn, and James Lewis. His **"Branch by Abstraction"** bliki entry defines the pattern, while Jez Humble's companion piece on continuousdelivery.com provides a real-world example of iBatis-to-Hibernate migration in ThoughtWorks' Go CD tool — directly relevant to Spring Boot JPA teams.

**Nicolas Carlo's understandlegacycode.com** is the single best website dedicated entirely to legacy code. His article **"Key Points of Working Effectively with Legacy Code"** provides an accessible modern summary of Feathers' entire methodology. **"7 Techniques to Regain Control of Your Legacy Codebase"** combines git hotspot analysis with testing strategies. His comparison of characterization tests versus approval tests versus regression tests clears up terminology confusion and connects to practical tooling. Michael Feathers' own blog post on **characterization testing** walks through the exact process with Java examples — write assertion, let it fail, capture actual behavior, make the test pass.

Korean tech companies have published some of the most practical migration content available. **Woowahan (배달의민족/Baemin)** documented their legacy ad system migration to Spring Boot/JPA, dealing with MS-SQL composite key mappings and API isolation of coupled code. Their points system rewrite series describes testing legacy MSSQL stored procedures using Docker and comparing JSON outputs between old and new APIs — a real-world form of characterization testing. The INFCON 2022 talk **"레거시 시스템 개편의 기술"** by Kwon Yonggeun covers the complete spectrum from business justification through testing to deployment. **Coupang's** two-part series on their "Vitamin Project" documents their complete monolith-to-microservices journey including an in-house message queue for decoupling, while **Toss (토스)** published a series on modernizing a **20-year-old legacy payment system** using Kotlin, Spring Boot, Kafka, and Kubernetes.

Among Western companies, **Shopify's "Deconstructing the Monolith"** provides the important counter-narrative — they chose a modular monolith over microservices for their **2.8-million-line** Ruby codebase, with strict boundary enforcement via their Packwerk tool. The principles translate directly to Spring Boot applications. Uber's engineering blog offers candid accounts of pitfalls, notably their admission of converting "our monolithic API into a distributed monolithic API." For Kafka-based migration, Kai Waehner's 2025 article **"Replacing Legacy Systems with Data Streaming: The Strangler Fig Approach"** bridges the pattern with Kafka and Flink, including an Allianz insurance case study with DDD and Event Storming integration.

---

## GitHub repositories for hands-on learning

The most valuable repositories fall into five categories, each serving a different learning need.

**For migration pattern implementation**, the standout is **javieraviles/split-the-monolith** — a complete three-phase walkthrough combining Strangler Fig (Phase 2, with NGINX proxy routing) and Branch by Abstraction (Phase 3, with feature toggles via Spring's `@Value` annotation) in a Spring Boot project. **hpgrahsl/strangler-fig-pattern-demo** adds Kafka-based CDC using Debezium to synchronize data between legacy and new services — critical for teams using event-driven decoupling.

**For DDD in Kotlin**, **ttulka/ddd-example-ecommerce-kotlin** is the best available example with proper bounded contexts, hexagonal architecture, and event-driven communication between contexts using Spring Boot Starters for module composition. **dustinsand/hex-arch-kotlin-spring-boot** (~200 stars) is the reference multi-module project combining Hexagonal Architecture with DDD, using Kotlin's `internal` modifier plus **ArchUnit** to enforce architecture rules — a powerful combination for preventing legacy code from creeping back in.

**For legacy code testing practice**, Emily Bache's **GildedRose-Refactoring-Kata** (~3,600 stars, available in Kotlin) remains the canonical exercise. Pair it with **approvals/ApprovalTests.Java** for golden master testing and **testdouble/contributing-tests** wiki for the conceptual framework connecting Feathers' seam model to practical testing workflows. For architecture enforcement, **TNG/ArchUnit** (~3,200 stars) works with Kotlin bytecode and is essential for preventing architectural regression during modernization.

**For Kafka and event-driven patterns**, **thecodemonkey/kafka-microservices** stands out as the best incremental learning resource — written in both Kotlin and Java, covering pub/sub basics through Event Sourcing and SAGA patterns. **kbastani/event-sourcing-microservices-example** (~700 stars) shows production-grade CQRS with events streamed through Kafka to hydrate different database technologies.

**For Kotlin-specific tooling**, **detekt/detekt** (~6,300 stars) provides static analysis with a critical feature for legacy projects: **baseline generation** that suppresses existing issues while ensuring no new ones are introduced — exactly the incremental approach legacy modernization demands. **kotest/kotest** (~4,500 stars) is the best Kotlin-native test framework for writing characterization tests with property testing and data-driven testing support.

- **feststelltaste/awesome-legacy-systems** — curated list linking to books, conferences, tools, and related awesome lists for legacy modernization
- **modernizing/awesome-modernization** — catalog of analysis and modernization tools including Coca for legacy refactoring analysis, DesigniteJava for code smell detection, and ArchUnit
- **meshcloud/spring-kotlin-example** — side-by-side Java vs Kotlin branches of the same Spring Boot app, perfect for teams converting legacy Java code

---

## A practical learning sequence that builds on itself

The resources above cover enormous ground. For maximum efficiency, sequence your learning to build compounding knowledge. Start with Feathers' characterization testing concept (read Chapter 4 and Chapter 13 of *Working Effectively with Legacy Code*, then practice on the Gilded Rose Kata in Kotlin). This gives you the safety net technique everything else depends on. Next, absorb the strategic migration patterns: watch Sam Newman's GOTO 2019 talk, then read Chapters 3–4 of *Monolith to Microservices* for Strangler Fig, Branch by Abstraction, and database decomposition. Layer on DDD by reading Eric Evans' "Getting Started with DDD When Surrounded by Legacy Systems" (free PDF from domainlanguage.com) for the **Bubble Context** pattern — creating a clean DDD-based bounded context connected to legacy via an Anti-Corruption Layer.

Then move to implementation. Study the **split-the-monolith** GitHub repo for Spring Boot migration patterns, explore Spring Modulith via the JetBrains Kotlin tutorials, and work through **thecodemonkey/kafka-microservices** for event-driven decoupling. Read the Woowahan and Toss engineering blogs for real-world validation of these patterns in production Korean tech companies using Spring Boot, Kafka, and Kotlin.

---

## Conclusion

Three insights emerge from surveying the full resource landscape. First, **Spring Modulith has shifted the default modernization path** — the 2024–2026 consensus favors modularizing monoliths before (or instead of) extracting microservices, and this is now well-supported for Kotlin. Second, the gap between theory and practice is closing rapidly: Korean tech companies like Woowahan and Toss are publishing detailed, Spring Boot–specific migration playbooks that complement the pattern-oriented Western literature with operational reality. Third, the most underutilized technique remains **behavioral code analysis** (Tornhill's git-log-based hotspot detection) — it provides data-driven prioritization of what to modernize first, yet most teams still rely on intuition. The engineer who combines Feathers' testing discipline, Newman's migration patterns, DDD's strategic boundaries, and Kafka's CDC-based decoupling has a complete toolkit for any legacy modernization challenge they'll face.