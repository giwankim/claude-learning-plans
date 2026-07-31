---
title: "Apache Kafka Mastery: A Phased Learning Curriculum for a Senior Backend Engineer"
category: "Data & Messaging"
description: "A 6-phase, roughly 5-6 month curriculum anchored to Kafka 4.x (KRaft-only, with ZooKeeper removed in March 2025). It consolidates fundamentals, then covers deep internals (KRaft/KIP-500, the storage engine, KIP-848 next-gen rebalancing, KIP-932 share groups), architecture patterns, the competitive landscape (Redpanda, WarpStream, AutoMQ, diskless KIP-1150), a production operations playbook, and a self-managed-versus-managed TCO decision framework. Its conclusion: MSK or Confluent Cloud beats Strimzi-on-EKS until sustained multi-hundred-MB/s throughput and dedicated platform headcount justify the switch. Every phase pairs concrete labs (a local KRaft cluster, Strimzi-on-EKS, a Debezium CDC pipeline, a MirrorMaker 2 DR drill, perf benchmarking, a cost model) with milestones."
---

# Apache Kafka Mastery: A Phased Learning Curriculum for a Senior Backend Engineer

## TL;DR
- This is a 6-phase, roughly 5-6 month curriculum taking you from consolidating fundamentals through deep internals (KRaft/KIP-500, the storage engine, KIP-848, KIP-932), architecture patterns, the competitive landscape (Redpanda, WarpStream, AutoMQ, diskless KIP-1150), a production operations playbook, and a detailed self-managed-versus-managed decision framework. Everything is anchored to Kafka 4.x, which is KRaft-only, since ZooKeeper was removed on March 18, 2025.
- On the decision you emphasized most: stay on a managed service (MSK or Confluent Cloud) until you have a clear, sustained reason not to. Aiven's "Kafka's 80% Problem" analysis quantifies the crossover: at a few MB/s (roughly 300-400 GB/day), self-managing a three-AZ, RF=3 posture "rounds to at least $300,000/yr once infra + people are counted," against a managed service "priced around $50,000/yr." Self-managing Strimzi-on-EKS therefore pays off only when you sustain multi-hundred-MB/s throughput, have 2-3 or more dedicated platform engineers, and have inter-AZ and licensing costs dominating.
- Every phase has concrete labs (a local KRaft cluster, Strimzi-on-EKS, a CDC pipeline with Debezium, a MirrorMaker 2 DR drill, perf benchmarking, a cost model) plus milestones. Resources are prioritized as recent and authoritative, and marked free or paid.

## Key Findings

1. Kafka 4.0, released March 18, 2025, is KRaft-only. ZooKeeper is fully removed, not deprecated. You cannot upgrade directly from ZooKeeper to 4.0, since 3.9 is the bridge release. Brokers require Java 17 and clients require Java 11. This reshapes every operations and internals resource, so prefer post-2024 material.
2. The consumer world changed twice. KIP-848, the next-gen rebalance protocol that went GA in 4.0, moves coordination server-side and eliminates stop-the-world rebalances. KIP-932 (Queues for Kafka, or share groups) adds true queue semantics and reached GA with Kafka 4.2 on Confluent's timeline. Both are directly relevant to your Spring Kafka stack.
3. The cloud-cost debate is now the center of gravity in the Kafka ecosystem. Per Confluent's own 2023 "A Guide to Mastering Kafka's Infrastructure Costs," cross-AZ data transfer due to replication "can surprisingly account for more than 50% of infrastructure costs when self-managing Apache Kafka," and Confluent's Freight-cluster blog puts it as high as 88%. This is why diskless and S3-native architectures (WarpStream, AutoMQ) emerged, and why the community accepted KIP-1150 (Diskless Topics). Per Aiven, the KIP author, "On March 2, 2026, the vote to accept Diskless topics into Apache Kafka passed with overwhelming support of 9 binding votes and 5 non-binding ones." Confluent acquired WarpStream in Sept 2024, and IBM's acquisition of Confluent (all common shares at $31 per share, an $11B enterprise value, announced Dec 8, 2025) closed March 17, 2026.
4. For your situation (Seoul/ap-northeast-2, EKS, Kotlin and Spring), the managed-versus-self-managed decision hinges on a TCO dominated by inter-AZ transfer and engineering headcount, not by sticker price. MSK Serverless is available in Seoul, and Strimzi-on-EKS is viable but shifts the upgrade, rebalance, and patching burden onto your team.

## Details

### Phase 0: orientation and environment (week 1, ~5-8 hrs)
**Goal:** establish a mental map and a working local lab tuned to the Kafka 4.x and KRaft era, since your existing knowledge predates some of it.

- Read (free): the Apache Kafka 4.0 release announcement (kafka.apache.org blog, March 2025) and the "Upgrading to 4.0" docs. These establish the KRaft-only reality and the deprecations that invalidate older tutorials.
- Watch (free): Confluent Developer's "Apache Kafka 101" (Tim Berglund) as a fast refresher on the event-centric mental model.
- Lab: stand up a single-node KRaft cluster from the official binaries, with no ZooKeeper and config now consolidated in `config/`. Confirm you can create topics, produce and consume, and inspect `__cluster_metadata`.
- Milestone: explain, in your own words, why KRaft stores metadata as an append-only log and why that removed a propagation bottleneck.

### Phase 1: fundamentals, consolidated (weeks 2-4, ~25 hrs)
**Goal:** convert your working knowledge into rigorous, first-principles understanding of topics, partitions, consumer groups, replication, ISR, log compaction, retention, idempotent producers, transactions, and exactly-once semantics (EOS).

**Canonical resources:**
- Book (paid, canonical): *Kafka: The Definitive Guide*, 2nd Edition, by Gwen Shapira, Todd Palino, Rajini Sivaram, and Krit Petty (O'Reilly, 2021). Confluent offers a free registration-gated PDF. This is the spine of Phases 1, 2, and 5.
- Book (paid): *Kafka in Action*, by Dylan Scott, Viktor Gamov, and Dave Klein (Manning, 2022), a more hands-on complement.
- Foundational essay (free): Jay Kreps, "The Log: What every software engineer should know about real-time data's unifying abstraction" (LinkedIn Engineering, Dec 2013). The single most important conceptual reading, and it pairs with Kreps's short book *I Heart Logs* (O'Reilly).
- Course (paid, around $15 on sale): Stephane Maarek, "Apache Kafka Series: Learn Apache Kafka for Beginners v3" (Udemy). The setup videos were updated to Kafka 4.0 in August 2025. Good for filling any CLI or API gaps quickly at 1.5x speed.
- Course (free): Confluent Developer's "Apache Kafka 101" plus the schema registry, Kafka Connect, and ksqlDB micro-courses.

**Focus areas that reward re-study even for experienced engineers:**
- The exact semantics of `acks=all` with `min.insync.replicas` and `replication.factor`, and the failure modes (unclean leader election, ISR shrink).
- Idempotent producer internals (producer ID plus sequence numbers), and how transactions build EOS across the producer-to-consumer boundary with `read_committed`.
- Log compaction against time and size retention, and when each is the right cleanup policy.

**Lab:** build a small Kotlin and Spring Boot producer/consumer pair using Spring Kafka, then deliberately induce a rebalance and observe the behavior. Enable idempotence and a transaction, and verify that `read_committed` filters aborted messages.

**Milestone:** write a one-page note reconciling your existing outbox and Debezium pattern with Kafka's native EOS, explaining precisely why the transactional outbox is still preferred over producer transactions for DB-to-Kafka consistency.

### Phase 2: internals for deep understanding (weeks 5-9, ~40 hrs)
**Goal:** understand Kafka's implementation deeply enough to reason about performance, failure, and new features.

**Storage engine and request path:**
- Course (free): Confluent Developer's "Kafka Internals" (Jun Rao, a Kafka co-creator), which covers the storage layer, replication, and the produce and fetch paths authoritatively.
- Docs and essays (free): the Definitive Guide 2e internals chapters on storage and replication, plus the Confluent engineering blog posts on the log segment format, indexes, and zero-copy (`sendfile`).
- Study RecordBatch format v2 (message formats v0 and v1 were removed in 4.0), log segments with `.index` and `.timeindex` files, page-cache reliance, and zero-copy reads.

**Controller and consensus:**
- KIP-500 (Replace ZooKeeper with a Self-Managed Metadata Quorum) and the KRaft design. Note KIP-996 (pre-vote) and KIP-853 (dynamic KRaft quorums, in 3.9). KRaft scales to roughly 1.9M partitions and gives near-instant controller failover.
- A real-world proof point: Aiven migrated 15,000 servers from ZooKeeper to KRaft in three months with zero downtime.

**Rebalance protocol (critical for your stack):**
- KIP-848, "The Next Generation of the Consumer Rebalance Protocol," GA in Kafka 4.0. Read the KIP (authors David Jacot, Guozhang Wang, Jason Gustafson) and the Confluent blog post. Coordination moves to the broker-side group coordinator via a continuous `ConsumerGroupHeartbeat`, and you enable it with `group.protocol=consumer`. The Kafka community benchmark cited by Confluent shows "a group with 10 consumers adding 900 partitions completes rebalancing in 5 seconds instead of 103 seconds", and Instaclustr frames the overall gain as "up to 20x faster".
- Watch the Current 2024 talk "The Performance of Kafka's New Consumer Rebalance Protocol."

**Queues and share groups:**
- KIP-932, "Queues for Kafka." Share groups allow more consumers than partitions, per-message acknowledgement (accept, release, reject, renew), 30-second acquisition locks, and a delivery-count limit (default 5) with archival. It was early access in 4.0, preview in 4.1, and GA with Kafka 4.2 (Confluent Platform 8.2). Read Gunnar Morling's "Let's Take a Look at… KIP-932" and the Spring Kafka "Kafka Queues (Share Consumer)" docs; Spring for Apache Kafka 4.1 gives full production support.

**Tiered storage:**
- KIP-405 (Kafka Tiered Storage, GA): local plus remote tiers (S3, HDFS), with separate `local.retention.*` and `retention.*` settings. Read the KIP and Uber's Current 2023 talk "Learnings of Running Kafka Tiered Storage at Scale" (Satish Duggana). Note KIP-1176 (tiered storage for the active log segment) and KIP-1272 (compacted topic support) as the frontier.

**Reading source code:**
- Start with the `clients` module (producer and consumer), then `storage` and `core` (the log, `RemoteLogManager`), then `metadata` and `raft` (KRaft). Use the KIP as the design doc for each area before diving in. The Strimzi operator (Java) is also worth reading to understand Kubernetes-native operations.

**Lab:** enable KIP-848 on your consumer group and measure rebalance time before and after with a synthetic scale-out. Separately, enable share groups on a sandbox 4.2 cluster and build a `KafkaShareConsumer`-based worker queue with retry and reject semantics.

**Milestone:** draw the full produce path (client, leader, ISR, high-watermark advance, ack) and the fetch path (including fetch-from-follower and tiered fetch), and explain where each new KIP intervenes.

### Phase 3: use cases and architecture patterns (weeks 10-13, ~30 hrs)
**Goal:** master event-driven architecture, event sourcing, CQRS, stream processing, CDC, and data integration, and know when each applies.

**Books and essays:**
- Book (paid, essential): *Designing Data-Intensive Applications*, Martin Kleppmann (O'Reilly). Chapters 11 (stream processing) and 5 (replication) are the theoretical backbone. A 2nd edition is in progress; the 1st edition remains the standard.
- Book/report (free): *Making Sense of Stream Processing*, Martin Kleppmann (O'Reilly and Confluent).
- Articles (free): Martin Fowler's "What do you mean by 'Event-Driven'?" and his related EDA, event-sourcing, and CQRS notes.
- Book (paid): *Kafka Streams in Action*, 2nd Edition, William P. Bejeck Jr. (Manning), for the Streams DSL.

**Stream processing and integration:**
- Kafka Streams against ksqlDB against Apache Flink, where Confluent's managed Flink is now the strategic direction. Confluent Developer has free Flink SQL and Kafka Streams courses.
- Kafka Connect for data integration. Understand single-message transforms, converters, and the connector ecosystem.

**CDC (your existing strength, deepened):**
- Gunnar Morling (morling.dev, ex-Debezium lead) is the authority. Read his outbox-pattern and "dual writes" material plus the Debezium docs, and reinforce why log-based CDC beats polling and why "friends don't let friends do dual writes."

**Real-world case studies (free, high-signal):**
- Uber: trillions of messages per day and roughly 12M messages per second. They built uReplicator, Chaperone, and uForwarder (a push-based consumer proxy that decouples partition count from consumer concurrency), plus cluster federation at roughly 150 nodes per cluster, Kappa+ backfill, and DLQs.
- Cloudflare: over 1 trillion inter-service messages, 14 clusters, and roughly 330 nodes, with Protobuf contracts, a "Messagebus" plus connector framework, and lessons on opinionated SDK defaults and schema governance (QCon London 2023).
- LinkedIn (the origin), Netflix, Pinterest, and Shopify engineering blogs.

**Lab:** build a CDC pipeline from Aurora MySQL through Debezium to Kafka and into a materialized read model (Elasticsearch, or a denormalized store), demonstrating CQRS. Bonus: enrich the stream with Kafka Streams.

**Milestone:** produce an architecture decision record for one of your real systems, choosing between messaging (a queue or share group), event streaming, and CDC, with explicit tradeoffs.

### Phase 4: tradeoffs and the competitive landscape (weeks 14-16, ~20 hrs)
**Goal:** form defensible opinions on Kafka against the alternatives, and understand the benchmark and cost wars.

**Alternatives (know the shape of each):**
- Apache Pulsar separates compute (brokers) from storage (BookKeeper), with native geo-replication and multi-tenancy, at the cost of more moving parts.
- RabbitMQ offers queue and routing semantics with no replay, and is great for task queues and complex routing.
- AWS Kinesis is fully managed and AWS-native, with no open-source portability.
- NATS JetStream is ultra-lightweight and cheap per stream, excellent for tens of thousands of per-tenant streams and for microservice and IoT messaging, but it is not a big-data firehose.
- Redpanda is C++ with a thread-per-core design, no JVM and no ZooKeeper, a single binary, and Kafka-API compatibility, with strong single-node latency.
- WarpStream is diskless and S3-native, with stateless "Agents," BYOC deployment, zero inter-AZ cost, and roughly 26 Kafka APIs. Per WarpStream's docs, it "typically achieves a p99 produce latency of 400ms in its default configuration"; with S3 Express One Zone it cuts "median produce latency to 105ms, and the p99 to 170ms", and its newer "Lightning Topics" reach roughly 33ms median and under 50ms p99. Confluent acquired it in Sept 2024.
- AutoMQ is Kafka-compatible, reuses KRaft, and offloads storage to S3 with an EBS WAL. It has an open-source core (S3Stream), supports roughly 73 Kafka APIs, and achieves single-digit-ms latency with the EBS WAL.
- Google Pub/Sub, Azure Event Hubs, and AWS SQS: know that SQS is the right answer for simple job dispatch.

**Benchmark and cost wars (read critically):**
- Jack Vanlightly's "Kafka vs Redpanda Performance: Do the claims add up?" (jack-vanlightly.com, May 2023). His conclusion: Redpanda's headline claims are "greatly exaggerated"; Redpanda degraded significantly at 50 producers and couldn't hit 1 GB/s with TLS, while Kafka could. His core message is that benchmarks are only useful when run on your own workload. Note the fsync counter-argument from Redpanda.
- Inter-AZ cost is the crux: every GiB replicated cross-AZ costs roughly $0.02 round trip, so roughly 1 TB/day at RF=3 works out to about $1,200/month just for internal replication, before consumer fan-out.
- KIP-1150 (Diskless Topics) was accepted on March 2, 2026 with 9 binding and 5 non-binding votes. It is a meta-KIP with sub-KIPs 1163 (core), 1164 (batch coordinator), and 1165 (compaction). It is leaderless and object-storage-backed, claims up to roughly 80% TCO reduction, and is years away from production readiness, since KIP-500 took around 5.5 years. Read Aiven's "Hitchhiker's Guide to Diskless Kafka" and the AutoMQ and Instaclustr analyses.
- The "Kafka is overkill" debate: Aiven's "Kafka's 80% Problem", written from running "4000+ Kafka clusters for 1000+ companies", states "60% of clusters are under 1 mb/s" and concludes "for 80% of use cases, Kafka is currently overkill."

**Milestone:** write a decision matrix. For three concrete workloads (a high-throughput event backbone, a per-tenant SaaS notification stream, and a simple job queue), pick Kafka, share groups, NATS, SQS, or a diskless platform, and justify each choice.

### Phase 5: production operations playbook (weeks 17-21, ~40 hrs)
**Goal:** be able to size, monitor, secure, upgrade, and firefight Kafka in production.

**Capacity and partition planning:**
- Rule of thumb: 100-200 partitions per broker as a baseline, and avoid more than 4,000 partitions per broker to protect the controller.
- Size for peak rather than average, and account for RF, retention, and consumer fan-out.

**Monitoring and tooling:**
- Key metrics: under-replicated partitions, `UnderMinIsrPartitionCount`, consumer lag, request-handler idle ratio, `ActiveControllerCount`, and request latencies.
- Tools: Cruise Control (rebalancing and self-healing), Burrow (lag), kcat, AKHQ, Kafka UI, and Conduktor, plus Prometheus and Grafana via the JMX exporter.
- Course (paid): Stephane Maarek's "Kafka Monitoring & Operations" and "Kafka Cluster Setup & Administration" (Udemy). Note that the setup course still teaches ZooKeeper, so treat that part as historical.

**Upgrades, DR, and multi-region:**
- Rolling restarts, and the 3.9 to 4.0 bridge path.
- MirrorMaker 2, Confluent Replicator, and stretch clusters for DR. Note MM2's operational sharp edges: topic renaming to `<source>.<topic>`, offset translation, and the fact that Uber found MM2 rebalancing caused weekly outages.

**Security:** TLS, SASL (SCRAM, GSSAPI), OAuth, ACLs, and quotas. Note that MSK Serverless requires IAM and does not support Kafka ACLs.

**Incident playbook (study each failure mode):** unclean leader election, ISR shrinkage, disk full, rebalance storms, and hot partitions.

**Performance tuning:** `batch.size`, `linger.ms`, compression, `fetch.min.bytes` and `fetch.max.wait.ms`, producer and consumer buffer sizes, OS page-cache tuning, and `client.rack` for fetch-from-follower to cut cross-AZ reads.

**War stories (free):** Uber's Chaperone, uReplicator, and uForwarder posts; Cloudflare's trillion-message posts; Confluent's operations docs; and the Definitive Guide 2e operations chapters.

**Lab:** (1) run `kafka-producer-perf-test` and `kafka-consumer-perf-test` on your local or EKS cluster, sweeping `linger.ms`, `batch.size`, and compression, and chart throughput against latency. (2) Chaos test: kill a broker mid-produce with `acks=all` and observe ISR and leader election. (3) Run a MirrorMaker 2 DR drill between two clusters and validate consumer offset translation.

**Milestone:** produce a one-page runbook for the top five incidents, each with its detection metric, immediate mitigation, and root-cause follow-up.

### Phase 6: the self-managed versus managed decision framework (weeks 22-24, ~25 hrs), the critical one

**Goal:** build a rigorous, numbers-driven framework for choosing among self-managed options (Strimzi-on-EKS, EC2), MSK and MSK Serverless, Confluent Cloud, Aiven, Redpanda Cloud, and WarpStream BYOC, tuned to your Seoul and EKS context.

**The options and who owns what:**
- Self-managed on EKS (Strimzi): you own upgrades, scaling, partition rebalancing (via Cruise Control), security patching, and DR. Strimzi is a CNCF project, KRaft-ready, and declarative via CRDs (Kafka, KafkaTopic, KafkaUser, KafkaNodePool). AWS publishes a "Deploying and scaling Kafka on EKS" (Data on EKS) blueprint, and Graviton (arm64) images give meaningful price-performance gains. One caveat, from Cookpad: Strimzi typically supports a new Kafka release about a month after GA, and understanding operator behavior sometimes means reading its Java source.
- Self-managed on EC2 or VMs: maximum control, maximum toil.
- AWS MSK Provisioned: AWS manages the brokers, but you still size and rebalance. Standard against Express brokers, where Express gives up to 3x throughput per broker, 20x faster scaling, and 90% faster recovery.
- MSK Serverless: no capacity planning, but it requires IAM, has no Kafka ACLs, and has a limited config surface. It is available in Seoul (ap-northeast-2).
- Confluent Cloud: the most complete platform (Schema Registry, connectors, ksqlDB, managed Flink, tiered storage, Kora engine autoscaling). Dedicated uses provisioned CKUs, while Basic, Standard, and Enterprise use elastic eCKUs, with a 99.99% SLA.
- Aiven, Redpanda Cloud, and WarpStream BYOC: Aiven is multi-cloud managed OSS Kafka; Redpanda Cloud is the low-latency C++ engine; WarpStream BYOC keeps data in your own S3 and VPC with a managed control plane and zero inter-AZ cost, which is ideal for logging and observability with relaxed latency.

**TCO anatomy (the part people get wrong):**
- Inter-AZ data transfer often dominates. Confluent's own "A Guide to Mastering Kafka's Infrastructure Costs" (2023) states that cross-AZ transfer "can surprisingly account for more than 50% of infrastructure costs when self-managing Apache Kafka", and its Freight-cluster blog puts it as high as 88%. A 3-AZ RF=3 cluster writes cross-zone two thirds of the time and replicates to two followers.
- Engineering headcount is the other half. Confluent's TCO analysis assumes roughly 3-4 engineers for self-managed against "nearly zero" for Cloud.
- An illustrative MSK Provisioned monthly example: a 6-broker cluster with 5 TB storage and 3 TB in and out, multi-AZ, comes to roughly $8,556/month, of which about $2,500 is operational overhead (0.5 FTE). Even on managed, people cost is a real line item.
- The shape of Confluent Cloud pricing: billed on eCKUs and CKUs ($/hour) plus networking ($/GB) plus storage ($/GB-hour). A CKU supports roughly 50 MB/s ingress and 150 MB/s egress. Confluent does not publish exact per-unit rates, so use their cost estimator, and expect Dedicated clusters with governance to reach five or six figures per month at scale.
- Diskless and S3 savings (vendor-reported, so verify on your workload): WarpStream claims 5-10x cheaper than cloud Kafka, AutoMQ reports roughly 50-77% reductions, and FunPlus reported over 60% infrastructure cost reduction migrating from MSK to AutoMQ. Treat all vendor figures skeptically and model your own.

**The threshold, with concrete guidance:**
- Aiven's "80% problem" anchor: at a few MB/s (roughly 300-400 GB/day), self-managing a three-AZ, RF=3 posture "rounds to at least $300,000/yr once infra + people are counted," against managed "priced around $50,000/yr." Below roughly 1 MB/s, where 60% of clusters live per Aiven, managed almost always wins.
- Migration reality (managed to self-managed): Cookpad moved from Confluent Cloud to Strimzi-on-EKS in a roughly 6-month project staffed by about 3 SREs, and they explicitly still recommend managed (Confluent Cloud) for teams getting started. Their decision was strategic, driven by wanting to run their own clusters, rather than purely about cost.
- A practical rule for your situation: self-managing Strimzi-on-EKS starts to pay off when you (a) sustain high, steady throughput in the hundreds of MB/s, (b) have two or three engineers who can own Kafka as a platform, (c) see inter-AZ and licensing costs dominating a managed bill, and (d) need config or plugin control, or data-residency guarantees a managed tier won't give. Otherwise the rational default is MSK (Serverless for spiky or early-stage workloads, Provisioned or Express for steady, high-throughput ones) or Confluent Cloud, for the ecosystem and elastic scaling.

**Seoul and ap-northeast-2 notes:** MSK (both Provisioned and Serverless) and Confluent Cloud are available in ap-northeast-2. If data residency in Korea is a compliance requirement, WarpStream BYOC, Confluent Private Cloud, or self-managed Strimzi keep data in your own VPC and buckets.

**Lab:** build a mock cost evaluation spreadsheet for one of your real workloads, modeling MSK Provisioned, MSK Serverless, Confluent Cloud, and Strimzi-on-EKS across broker and compute, storage, inter-AZ transfer, and estimated FTE cost. Include a sensitivity analysis on throughput growth and consumer fan-out.

**Milestone:** deliver a decision memo recommending a platform for your team, with explicit thresholds that would flip the recommendation, such as "switch to self-managed if sustained throughput exceeds X MB/s and we hire a second platform engineer."

## Korean-Language Resources (supplementary)
- Kakao Tech blog (tech.kakao.com): "카카오 개발자들을 위한 공용 Message Streaming Platform - Kafka & RabbitMQ", a real operational account of running shared Kafka and RabbitMQ clusters, Grafana dashboards, and the dedicated-versus-shared cluster tradeoffs.
- Woowahan (배달의민족) tech blog (techblog.woowahan.com): "우리 팀은 카프카를 어떻게 사용하고 있을까", on EventBus, Kafka Streams, and the transactional outbox pattern in production. It also references the Korean book *아파치 카프카 애플리케이션 프로그래밍 with 자바*.
- The LINE and Naver engineering blogs, for large-scale operations posts.
- Use these to reinforce the English core rather than to replace it.

## Recommendations
1. Start now with Phases 0 and 1, re-grounding in the 4.x and KRaft era, even though you know the basics. The ZooKeeper removal, KIP-848, and KIP-932 materially change what "fundamentals" means. Budget 2-3 weeks.
2. Front-load the two KIPs that touch your Spring stack, 848 and 932, in Phase 2. Enable `group.protocol=consumer` in a staging consumer group and measure the rebalance improvement yourself.
3. Do the CDC lab in Phase 3 against Aurora MySQL, to connect new learning to your existing Debezium and outbox expertise.
4. Treat Phase 6 as the capstone: produce a real cost model and decision memo for your team. Default to managed (MSK or Confluent Cloud in Seoul) unless your numbers cross the thresholds above.
5. Benchmarks that change your recommendation: revisit the self-managed decision if sustained throughput crosses into the hundreds of MB/s, if inter-AZ transfer exceeds roughly 30-50% of your managed bill, or if you add a dedicated platform engineer. Revisit diskless options (WarpStream, AutoMQ, KIP-1150) once the KIP-1150 sub-KIPs reach production maturity.

## Caveats
- Vendor sources are biased. Confluent, AutoMQ, WarpStream, Redpanda, and Instaclustr all publish self-favorable cost and benchmark claims. Every dollar figure and percentage from a vendor should be re-derived on your own workload before it drives a decision.
- Confluent does not publish exact per-CKU or per-eCKU rates. Third-party estimates, such as roughly $8.75 per CKU-hour, are unofficial, so use Confluent's cost estimator.
- KIP-1150 diskless is directional, not production-ready. The March 2026 vote approved the vision, but the sub-KIPs (core, coordinator, compaction) are still being engineered, and the latency, ordering, and transaction guarantees need validation.
- The IBM and Confluent acquisition ($31 per share, roughly $11B enterprise value, announced Dec 8, 2025 and closed March 17, 2026) introduces roadmap uncertainty for Confluent Cloud and WarpStream customers, so watch for changes.
- KIP-932 share groups reached GA on the Confluent Platform 8.2 and Kafka 4.2 timeline. Confirm the exact Apache release status before relying on it in production, and note that early-access clusters can't be upgraded in place.
- Courses age. Maarek's admin and setup courses still contain ZooKeeper material, and the Definitive Guide 2e (2021) predates 4.0, so supplement operations content with the current Apache docs and Confluent blogs.
