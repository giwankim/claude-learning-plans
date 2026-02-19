---
title: "Apache Kafka"
category: "Data & Messaging"
description: "Kafka producers, consumers, and Streams for Spring Boot"
---

# Mastery Learning Plan: Apache Kafka for Spring Boot Kotlin Developers

A Spring Boot Kotlin developer who has completed Stéphane Maarek's beginner course can achieve production mastery through a **five-phase journey spanning 6-8 months** of dedicated study. This plan builds systematically from Spring Kafka fundamentals through advanced patterns like event sourcing and CQRS, with each phase delivering immediately applicable skills. The recommended approach balances theoretical depth with hands-on implementation, leveraging Kotlin's expressive syntax for cleaner Kafka code.

---

## Phase 1: Spring Kafka fundamentals and async microservice communication

**Duration: 4-6 weeks | Focus: Production-ready producers and consumers**

### Learning objectives
By completing this phase, you will implement reliable asynchronous communication between Spring Boot microservices using Kafka, configure production-grade error handling and retry mechanisms, write comprehensive tests using EmbeddedKafka, and understand Spring's Kafka abstractions (KafkaTemplate, @KafkaListener) at a deep level.

### Core reading materials

**"Kafka: The Definitive Guide, 2nd Edition"** by Gwen Shapira, Todd Palino, Rajini Sivaram, and Krit Petty (O'Reilly, 2021) serves as your foundational reference. Chapters 1-6 cover producer and consumer internals you'll need to understand Spring's abstractions. The second edition adds crucial coverage of transactions, the AdminClient API, and KRaft mode. Available at [O'Reilly](https://www.oreilly.com/library/view/kafka-the-definitive/9781492043072/) or [Amazon](https://www.amazon.com/Kafka-Definitive-Real-Time-Stream-Processing/dp/1492043087) (~$60).

**"Designing Event-Driven Systems"** by Ben Stopford is a **free** Confluent ebook that establishes event-driven thinking patterns. Download it from [Confluent's resources page](https://www.confluent.io/resources/ebook/designing-event-driven-systems/). Read chapters 1-5 during this phase for architectural context.

### Official documentation deep-dive

Work through these documentation sections systematically:

- **Spring Kafka Reference**: [docs.spring.io/spring-kafka/reference/index.html](https://docs.spring.io/spring-kafka/reference/index.html) — Complete coverage of KafkaTemplate, @KafkaListener, consumer configuration, error handling, and transactions
- **Spring Kafka Quick Tour**: [docs.spring.io/spring-kafka/reference/quick-tour.html](https://docs.spring.io/spring-kafka/reference/quick-tour.html) — Immediate hands-on starting point
- **Spring Boot Kafka Integration**: [docs.spring.io/spring-boot/reference/messaging/kafka.html](https://docs.spring.io/spring-boot/reference/messaging/kafka.html) — Auto-configuration and property reference
- **Baeldung Spring Kafka Tutorial**: [baeldung.com/spring-kafka](https://www.baeldung.com/spring-kafka) — Excellent companion with practical Kotlin-adaptable examples

### Recommended courses

**Primary course**: "Apache Kafka for Developers using Spring Boot" by Pragmatic Code School on Udemy covers Spring Boot 3.x integration, KafkaTemplate patterns, unit testing with EmbeddedKafka, and consumer group management. [Udemy link](https://www.udemy.com/course/apache-kafka-for-developers-using-springboot/) (~$15-90).

**Supplement with free Confluent courses**: Complete "Apache Kafka 101" and the "Spring Boot with Kafka" module at [developer.confluent.io/courses/](https://developer.confluent.io/courses/) for additional perspectives.

### Hands-on practice

Clone and study **[spring-projects/spring-kafka](https://github.com/spring-projects/spring-kafka)** — the official repository with reference implementations. For Kotlin-specific patterns, explore **[rogervinas/spring-cloud-stream-kafka-step-by-step](https://github.com/rogervinas/spring-cloud-stream-kafka-step-by-step)** which includes Kotlin examples with excellent documentation.

**Practice project**: Build an order processing system with three microservices (Order, Inventory, Notification) communicating asynchronously via Kafka. Implement:
- Idempotent producers with exactly-once semantics
- Dead letter topics for failed message handling
- Consumer retry with exponential backoff
- Comprehensive integration tests using Testcontainers

---

## Phase 2: Event-driven architecture with Spring Cloud Stream

**Duration: 4-5 weeks | Focus: Declarative messaging and portable microservices**

### Learning objectives
Master Spring Cloud Stream's functional programming model for event-driven microservices, understand binder abstraction for message broker portability, implement complex routing and content-based filtering, and configure Schema Registry integration for schema evolution.

### Core reading materials

Complete **"Designing Event-Driven Systems"** (chapters 6-11) covering event collaboration patterns, streams as shared state, and building services around event streams. This free resource from Confluent establishes the architectural thinking you'll implement.

**"Building Event-Driven Microservices"** by Adam Bellemare (O'Reilly, 2020; 2nd edition 2024) provides production patterns for event-driven systems. Available at [O'Reilly](https://www.oreilly.com/library/view/building-event-driven-microservices/9781492057888/) (~$55). Chapters on bounded contexts, event stream design, and handling eventual consistency are essential.

### Official documentation

- **Spring Cloud Stream Reference**: [docs.spring.io/spring-cloud-stream/reference/index.html](https://docs.spring.io/spring-cloud-stream/reference/index.html) — Core programming model
- **Kafka Binder Documentation**: [docs.spring.io/spring-cloud-stream/docs/current/reference/html/spring-cloud-stream-binder-kafka.html](https://docs.spring.io/spring-cloud-stream/docs/current/reference/html/spring-cloud-stream-binder-kafka.html) — Kafka-specific configuration
- **Schema Registry Documentation**: [docs.confluent.io/platform/current/schema-registry/index.html](https://docs.confluent.io/platform/current/schema-registry/index.html) — Schema management with Avro, Protobuf, and JSON Schema
- **Confluent Schema Registry Fundamentals**: [docs.confluent.io/platform/current/schema-registry/fundamentals/index.html](https://docs.confluent.io/platform/current/schema-registry/fundamentals/index.html) — Compatibility modes and evolution strategies

### Recommended courses

**"Event-Driven Microservices: Spring Boot, Kafka and Elastic"** by Ali Gelenler covers event sourcing patterns, monitoring with Prometheus/Grafana, and Elasticsearch integration. [Udemy link](https://www.udemy.com/course/event-driven-microservices-spring-boot-kafka-and-elasticsearch/).

**"Confluent Schema Registry & REST Proxy"** by Stéphane Maarek teaches Avro serialization and schema evolution — critical for production systems. [Udemy link](https://www.udemy.com/course/confluent-schema-registry/).

### Hands-on practice

Study **[spring-cloud/spring-cloud-stream-samples](https://github.com/spring-cloud/spring-cloud-stream-samples)** for official patterns. The repository **[ivangfr/spring-cloud-stream-event-sourcing-testcontainers](https://github.com/ivangfr/spring-cloud-stream-event-sourcing-testcontainers)** demonstrates event sourcing with Cassandra and comprehensive Testcontainers integration.

**Practice project**: Refactor your Phase 1 order system to use Spring Cloud Stream's functional model:
- Replace @KafkaListener with `Function<Flux<Event>, Flux<Event>>` bindings
- Implement content-based routing with multiple consumer groups
- Add Schema Registry with backward-compatible schema evolution
- Create a domain event catalog with versioned Avro schemas

---

## Phase 3: Stream processing with Kafka Streams

**Duration: 6-8 weeks | Focus: Real-time transformations and stateful processing**

### Learning objectives
Build real-time data pipelines using the Kafka Streams DSL, implement stateful operations (aggregations, joins, windowing), understand the Processor API for custom processing, design and test stream topologies, and leverage Kotlin's expressive syntax for cleaner Streams code.

### Core reading materials

**"Kafka Streams in Action, 2nd Edition"** by William Bejeck (Manning, 2024) is the definitive stream processing resource. It covers the KStream API, Processor API, ksqlDB, and materialized views. Available at [Manning](https://www.manning.com/books/kafka-streams-in-action-second-edition) (~$60). This is your **primary textbook** for this phase.

**"Effective Kafka"** by Emil Koutanov provides additional architecture patterns and operational considerations. Available at [apachekafkabook.com](https://www.apachekafkabook.com/) or [Amazon](https://www.amazon.com/Effective-Kafka-Hands-Event-Driven-Applications/dp/B0863R7MKG) (~$35).

### Official documentation

- **Kafka Streams Developer Guide**: [kafka.apache.org/documentation/streams/developer-guide/](https://kafka.apache.org/41/documentation/streams/developer-guide/) — Official Apache guide
- **Confluent Kafka Streams Documentation**: [docs.confluent.io/platform/current/streams/overview.html](https://docs.confluent.io/platform/current/streams/overview.html) — Enhanced Confluent documentation with architecture details
- **Kafka Streams Concepts**: [docs.confluent.io/platform/current/streams/concepts.html](https://docs.confluent.io/platform/current/streams/concepts.html) — KStream, KTable, GlobalKTable, processing guarantees
- **Spring Cloud Stream Kafka Streams Binder**: [docs.spring.io/spring-cloud-stream/reference/kafka/kafka-streams.html](https://docs.spring.io/spring-cloud-stream/reference/kafka/kafka-streams.html) — Spring integration for Kafka Streams

### Recommended courses

**"Kafka Streams for Data Processing"** by Stéphane Maarek is the most comprehensive Kafka Streams course, covering exactly-once semantics, stateful operations, joins, windowing, and testing. [Udemy link](https://www.udemy.com/course/kafka-streams/) (~$15-90).

**"KSQL on ksqlDB for Stream Processing"** by Stéphane Maarek and Simon Aubury teaches SQL-based stream processing. [Udemy link](https://www.udemy.com/course/kafka-ksql/).

**Free alternative**: The Kafka Streams 101 course by Sophie Blee-Goldman at [developer.confluent.io/courses/](https://developer.confluent.io/courses/) provides 2.5 hours of video content.

### Hands-on practice (Kotlin-focused)

**[perkss/kotlin-kafka-and-kafka-streams-examples](https://github.com/perkss/kotlin-kafka-and-kafka-streams-examples)** — The most comprehensive Kotlin Kafka Streams repository with reactive producers, windowing, aggregates, joins, Avro schemas, and Testcontainers. **Star count: 54** and actively maintained with accompanying blog posts.

**[adamko-dev/kotka-streams](https://github.com/adamko-dev/kotka-streams)** — A Kotlin DSL library that makes Kafka Streams more idiomatic with extension functions and Kotlinx Serialization support.

**[confluentinc/kafka-streams-examples](https://github.com/confluentinc/kafka-streams-examples)** — Official Confluent examples including WordCount, Interactive Queries, Kafka Music application, and microservices patterns. **1.1k forks**.

**[confluentinc/tutorials](https://github.com/confluentinc/tutorials)** — The new home for Confluent examples with complete code solutions for common streaming use cases.

**Practice projects** (implement in sequence):
1. **Word count and sentiment analysis**: Process a stream of messages, aggregate word frequencies in tumbling windows, join with a sentiment dictionary KTable
2. **Fraud detection system**: Implement session windows to detect suspicious transaction patterns, use GlobalKTable for customer lookup, emit alerts via output topic
3. **Real-time dashboard backend**: Create interactive queries to expose state store data via REST endpoints, implement punctuators for time-based processing

---

## Phase 4: Event sourcing patterns with Kafka

**Duration: 5-6 weeks | Focus: Storing state as a sequence of events**

### Learning objectives
Understand event sourcing principles and when to apply them, implement event stores using Kafka topics with log compaction, design aggregates that rebuild state from event streams, handle snapshots for performance optimization, and integrate with frameworks like Axon.

### Core reading materials

**"Implementing Domain-Driven Design"** by Vaughn Vernon (Addison-Wesley, 2013) remains the authoritative implementation guide. Chapters on Domain Events, Event Sourcing, and Sagas provide the theoretical foundation. Available at [Amazon](https://www.amazon.com/Implementing-Domain-Driven-Design-Vaughn-Vernon/dp/0321834577) (~$55).

**"Domain-Driven Design Distilled"** by Vaughn Vernon (2016) offers a faster entry point if time is limited. Available at [Amazon](https://www.amazon.com/Domain-Driven-Design-Distilled-Vaughn-Vernon/dp/0134434420) (~$35).

**"Exploring CQRS and Event Sourcing"** (Microsoft Patterns & Practices) is a **free** practical guide documenting a real implementation journey with input from Greg Young and Udi Dahan. Download from [Microsoft](https://www.microsoft.com/en-us/download/details.aspx?id=34774).

### Essential reading (Confluent blog)

These articles bridge theory to Kafka-specific implementation:

- **Event Sourcing, CQRS, Stream Processing and Apache Kafka**: [confluent.io/blog/event-sourcing-cqrs-stream-processing-apache-kafka-whats-connection/](https://www.confluent.io/blog/event-sourcing-cqrs-stream-processing-apache-kafka-whats-connection/) — Essential reading on implementing CQRS with Kafka Streams
- **Event Sourcing vs Derivative Event Sourcing**: [confluent.io/blog/event-sourcing-vs-derivative-event-sourcing-explained/](https://www.confluent.io/blog/event-sourcing-vs-derivative-event-sourcing-explained/) — Advanced pattern using CDC and Kafka Streams
- **Event Sourcing Outgrows the Database**: [confluent.io/blog/event-sourcing-outgrows-the-database/](https://www.confluent.io/blog/event-sourcing-outgrows-the-database/) — Why Kafka+ksqlDB excels for event sourcing at scale

### Recommended courses

Confluent's free **Event Sourcing course** at [developer.confluent.io/courses/event-sourcing/event-driven-vs-state-based/](https://developer.confluent.io/courses/event-sourcing/event-driven-vs-state-based/) provides video instruction on event-driven versus state-based approaches.

### Hands-on practice

**[mguenther/spring-kafka-event-sourcing-sampler](https://github.com/mguenther/spring-kafka-event-sourcing-sampler)** — An excellent event-sourced GTD application using Spring Kafka and Apache Avro with detailed documentation. Companion to a JavaMagazin article.

**[kbastani/event-sourcing-microservices-example](https://github.com/kbastani/event-sourcing-microservices-example)** — Production-ready social network microservices demonstrating event sourcing with Kubernetes deployment, Helm charts, and Neo4j integration.

**[AxonFramework/extension-kafka](https://github.com/AxonFramework/extension-kafka)** — Official Axon Framework Kafka extension for publishing and handling event messages.

**[hsenasilva/sample-cqrs](https://github.com/hsenasilva/sample-cqrs)** — **Kotlin** implementation of CQRS with Axon Framework, Kafka, and MongoDB. Multiple branches demonstrate different patterns including reactive (WebFlux) and distributed command handling with Eureka.

**Practice project**: Build an event-sourced banking system:
- Design account aggregate with events: AccountOpened, MoneyDeposited, MoneyWithdrawn, AccountClosed
- Implement event store using compacted Kafka topic with event versioning
- Build aggregate repository that replays events to reconstruct state
- Add snapshotting every N events for performance
- Create projections for account balance and transaction history views

---

## Phase 5: CQRS implementation patterns

**Duration: 4-5 weeks | Focus: Separating read and write models**

### Learning objectives
Design systems with separate command and query responsibilities, implement multiple read-optimized projections from event streams, handle projection rebuilding and eventual consistency, choose appropriate synchronization strategies, and integrate CQRS with event sourcing.

### Core reading materials

Complete the previously started resources:
- Finish "Implementing Domain-Driven Design" chapters on CQRS architecture
- Complete "Exploring CQRS and Event Sourcing" from Microsoft (covers real-world implementation challenges)
- **"Architecture Patterns with Python"** by Harry Percival and Bob Gregory — While Python-focused, chapters on CQRS, event-driven microservices, and message bus patterns are language-agnostic and freely available at [cosmicpython.com](https://www.cosmicpython.com/)

### Hands-on practice

**[ddd-by-examples/all-things-cqrs](https://github.com/ddd-by-examples/all-things-cqrs)** — **Highly recommended**. Comprehensive guide showing multiple CQRS synchronization approaches: in-memory, events via Kafka, database log tailing with Debezium. Excellent documentation comparing trade-offs.

**[Rapter1990/cqrs-example](https://github.com/Rapter1990/cqrs-example)** — Complete Spring Boot CQRS setup with Docker, Kafka, MySQL (write), and MongoDB (read), including Postman collections for testing.

**[amaljoyc/cqrs-spring-kafka](https://github.com/amaljoyc/cqrs-spring-kafka)** — Clean DDD/CQRS implementation with Spring Cloud Stream and PostgreSQL.

**Capstone project**: Build a full e-commerce system combining all patterns:
- **Command side**: Event-sourced aggregates (Order, Product, Customer) with Axon or custom implementation
- **Query side**: Multiple projections — search-optimized (Elasticsearch), analytics-optimized (ClickHouse), real-time dashboard (Redis)
- **Sync mechanisms**: Implement and compare Kafka-based sync versus Debezium CDC
- **Production concerns**: Implement saga pattern for distributed transactions, handle projection failures with replay capability

---

## Community resources for continuous learning

### YouTube and conference talks

**Confluent's YouTube channel** ([youtube.com/confluent](https://www.youtube.com/confluent)) hosts Kafka Summit recordings, tutorials, and customer case studies. Essential viewing includes:

- "Is Kafka a Database?" by Martin Kleppmann (Kafka Summit London 2019)
- "The Migration to Event-Driven Microservices" by Adam Bellemare
- "Trade-offs in Distributed Systems Design" by Ben Stopford and Michael Noll

**Kafka Summit** ([kafka-summit.org/past-events/](https://www.kafka-summit.org/past-events/)) provides recordings from past events. The **Apache Kafka video archive** at [kafka.apache.org/community/videos/](https://kafka.apache.org/community/videos/) aggregates conference talks.

### Podcasts and newsletters

**Streaming Audio** (Confluent Developer Podcast) hosted by Tim Berglund and Viktor Gamov features weekly interviews on Kafka and real-time data. Available on [Apple Podcasts](https://podcasts.apple.com/us/podcast/streaming-audio-apache-kafka-real-time-data/id1401509765), [Spotify](https://open.spotify.com/show/65WRDvSFQ2tkdk1GXlRPqR), or [developer.confluent.io/learn-more/podcasts/](https://developer.confluent.io/learn-more/podcasts/).

**Confluent Developer Newsletter** ([developer.confluent.io/newsletter/](https://developer.confluent.io/newsletter/)) delivers bimonthly updates on learning materials, meetups, and ecosystem news.

**Data Engineering Weekly** ([dataengineeringweekly.com](https://www.dataengineeringweekly.com/)) covers streaming technology including Kafka implementations from Uber, Netflix, and LinkedIn.

### Community forums

- **Kafka Community Slack**: [slack.kafka.apache.org](https://slack.kafka.apache.org/) — Real-time help from practitioners
- **Stack Overflow**: [stackoverflow.com/questions/tagged/apache-kafka](https://stackoverflow.com/questions/tagged/apache-kafka) — Searchable Q&A archive (also monitor `kafka-streams`, `spring-kafka`, `ksqldb` tags)
- **r/apachekafka**: [reddit.com/r/apachekafka/](https://www.reddit.com/r/apachekafka/) — Architecture discussions and news

### Certification path

After completing this learning plan, validate your skills with the **Confluent Certified Developer for Apache Kafka (CCDAK)** exam — 60 questions, 90 minutes, $150. Prepare using Stéphane Maarek's practice tests on [Udemy](https://www.udemy.com/course/confluent-certified-developer-for-apache-kafka/). The free **Apache Kafka Fundamentals Accreditation** at [confluent.io/certification/](https://www.confluent.io/certification/) provides a preliminary credential.

---

## Recommended timeline and resource summary

| Phase | Duration | Primary Book | Primary Course | Key Repository |
|-------|----------|--------------|----------------|----------------|
| 1. Spring Kafka Basics | 4-6 weeks | Kafka: The Definitive Guide | Kafka for Developers using Spring Boot | spring-projects/spring-kafka |
| 2. Event-Driven Architecture | 4-5 weeks | Building Event-Driven Microservices | Confluent Schema Registry | spring-cloud-stream-samples |
| 3. Kafka Streams | 6-8 weeks | Kafka Streams in Action, 2nd Ed | Kafka Streams for Data Processing | perkss/kotlin-kafka-and-kafka-streams-examples |
| 4. Event Sourcing | 5-6 weeks | Implementing DDD | Confluent Event Sourcing Course | mguenther/spring-kafka-event-sourcing-sampler |
| 5. CQRS Patterns | 4-5 weeks | Exploring CQRS (MS) | — | ddd-by-examples/all-things-cqrs |

**Total estimated time: 6-8 months** with **10-15 hours weekly** study commitment. This timeline assumes depth-first learning with thorough practice projects rather than surface-level coverage.

## Conclusion

Mastering Kafka for production Spring Boot Kotlin applications requires building systematically from messaging fundamentals through increasingly sophisticated patterns. The critical insight is that **event sourcing and CQRS are not Kafka features but architectural patterns that Kafka enables exceptionally well** — understanding this distinction separates practitioners from experts.

The Kotlin ecosystem offers genuine advantages for Kafka development: extension functions create cleaner Streams DSL code, coroutines integrate naturally with reactive Kafka patterns, and data classes simplify event modeling. Leverage repositories like **perkss/kotlin-kafka-and-kafka-streams-examples** and **adamko-dev/kotka-streams** to write idiomatic Kotlin rather than translating Java patterns.

For production mastery, prioritize understanding failure modes and recovery patterns over happy-path implementations. Every practice project should include chaos engineering scenarios: broker failures, consumer rebalancing, schema evolution, and projection rebuild strategies. The Confluent blog posts on production best practices and Kafka Summit talks on real-world implementations provide essential context that courses alone cannot.