---
title: "Apache Kafka Mastery: A Phased Learning Curriculum for a Senior Backend Engineer"
category: "Data & Messaging"
description: "A 6-phase, ~5-6 month curriculum anchored to Kafka 4.x (KRaft-only; ZooKeeper removed March 2025): consolidating fundamentals, deep internals (KRaft/KIP-500, storage engine, KIP-848 next-gen rebalancing, KIP-932 share groups), architecture patterns, the competitive landscape (Redpanda, WarpStream, AutoMQ, diskless KIP-1150), a production operations playbook, and a self-managed-vs-managed TCO decision framework — concluding that MSK/Confluent Cloud beats Strimzi-on-EKS until sustained multi-hundred-MB/s throughput and dedicated platform headcount justify the switch. Every phase pairs concrete labs (local KRaft cluster, Strimzi-on-EKS, Debezium CDC pipeline, MirrorMaker 2 DR drill, perf benchmarking, cost model) with milestones."
---

# Apache Kafka Mastery: A Phased Learning Curriculum for a Senior Backend Engineer

## TL;DR
- This is a 6-phase, ~5-6 month curriculum taking you from consolidating fundamentals through deep internals (KRaft/KIP-500, storage engine, KIP-848, KIP-932), architecture patterns, the competitive landscape (Redpanda, WarpStream, AutoMQ, diskless KIP-1150), a production operations playbook, and a detailed self-managed-vs-managed decision framework — all anchored to Kafka 4.x (KRaft-only; ZooKeeper removed March 18, 2025).
- On the decision you emphasized most: **stay on a managed service (MSK or Confluent Cloud) until you have a clear, sustained reason not to.** Aiven's "Kafka's 80% Problem" analysis quantifies the crossover: at a few MB/s (~300-400 GB/day), self-managing a three-AZ, RF=3 posture "rounds to at least $300,000/yr once infra + people are counted," versus a managed service "priced around $50,000/yr" — so self-managing Strimzi-on-EKS pays off only when you sustain multi-hundred-MB/s throughput, have 2-3+ dedicated platform engineers, and inter-AZ/licensing costs dominate.
- Every phase has concrete labs (local KRaft cluster, Strimzi-on-EKS, CDC pipeline with Debezium, MirrorMaker 2 DR drill, perf benchmarking, cost model) plus milestones. Resources are prioritized recent/authoritative and marked free vs. paid.

## Key Findings

1. **Kafka 4.0 (released March 18, 2025) is KRaft-only** — ZooKeeper is fully removed, not deprecated. You cannot upgrade directly from ZooKeeper to 4.0; 3.9 is the bridge release. Brokers require Java 17; clients require Java 11. This reshapes every operations and internals resource — prefer post-2024 material.
2. **The consumer world changed twice**: KIP-848 (next-gen rebalance protocol, GA in 4.0) moves coordination server-side and eliminates stop-the-world rebalances; KIP-932 (Queues for Kafka / share groups) adds true queue semantics and reached GA with Kafka 4.2 on Confluent's timeline. Both are directly relevant to your Spring Kafka stack.
3. **The cloud-cost debate is now the center of gravity in the Kafka ecosystem.** Per Confluent's own 2023 "A Guide to Mastering Kafka's Infrastructure Costs," cross-AZ data transfer due to replication "can surprisingly account for more than 50% of infrastructure costs when self-managing Apache Kafka" (Confluent's Freight-cluster blog puts it as high as 88%). This is why diskless/S3-native architectures (WarpStream, AutoMQ) emerged and why the community accepted KIP-1150 (Diskless Topics) — per Aiven (the KIP author), "On March 2, 2026, the vote to accept Diskless topics into Apache Kafka passed with overwhelming support of 9 binding votes and 5 non-binding ones." Confluent acquired WarpStream (Sept 2024); IBM's acquisition of Confluent (all common shares at $31/share, an $11B enterprise value, announced Dec 8, 2025) closed March 17, 2026.
4. **For your situation (Seoul/ap-northeast-2, EKS, Kotlin/Spring), the managed-vs-self-managed decision hinges on TCO dominated by inter-AZ transfer + engineering headcount, not sticker price.** MSK Serverless is available in Seoul; Strimzi-on-EKS is viable but shifts upgrade/rebalance/patching burden onto your team.

## Details

### Phase 0 — Orientation & Environment (Week 1, ~5-8 hrs)
**Goal:** Establish a mental map and a working local lab tuned to the Kafka 4.x/KRaft era, since your existing knowledge predates some of it.

- **Read (free):** The Apache Kafka 4.0 release announcement (kafka.apache.org blog, March 2025) and the "Upgrading to 4.0" docs. These establish the KRaft-only reality and the deprecations that invalidate older tutorials.
- **Watch (free):** Confluent Developer "Apache Kafka 101" (Tim Berglund) as a fast refresher of the event-centric mental model.
- **Lab:** Stand up a single-node KRaft cluster from the official binaries (no ZooKeeper, config now consolidated in `config/`). Confirm you can create topics, produce/consume, and inspect `__cluster_metadata`.
- **Milestone:** Explain, in your own words, why KRaft stores metadata as an append-only log and why that removed a propagation bottleneck.

### Phase 1 — Fundamentals, Consolidated (Weeks 2-4, ~25 hrs)
**Goal:** Convert your working knowledge into rigorous, first-principles understanding of topics, partitions, consumer groups, replication, ISR, log compaction, retention, idempotent producers, transactions, and exactly-once semantics (EOS).

**Canonical resources:**
- **Book (paid, canonical):** *Kafka: The Definitive Guide*, 2nd Edition — Gwen Shapira, Todd Palino, Rajini Sivaram & Krit Petty (O'Reilly, 2021). Confluent offers a free registration-gated PDF. This is the spine of Phases 1, 2, and 5.
- **Book (paid):** *Kafka in Action* — Dylan Scott, Viktor Gamov, Dave Klein (Manning, 2022). A more hands-on complement.
- **Foundational essay (free):** Jay Kreps, "The Log: What every software engineer should know about real-time data's unifying abstraction" (LinkedIn Engineering, Dec 2013). The single most important conceptual reading; pairs with Kreps's short book *I Heart Logs* (O'Reilly).
- **Course (paid, ~$15 on sale):** Stephane Maarek, "Apache Kafka Series – Learn Apache Kafka for Beginners v3" (Udemy). Setup videos were updated to Kafka 4.0 in August 2025. Good for filling any CLI/API gaps quickly at 1.5x speed.
- **Course (free):** Confluent Developer "Apache Kafka 101" + the schema registry / Kafka Connect / ksqlDB micro-courses.

**Focus areas that reward re-study even for experienced engineers:**
- The exact semantics of `acks=all` + `min.insync.replicas` + `replication.factor`, and the failure modes (unclean leader election, ISR shrink).
- Idempotent producer internals (producer ID + sequence numbers) and how transactions build EOS across the producer→consumer boundary (`read_committed`).
- Log compaction vs. time/size retention, and when each is the right cleanup policy.

**Lab:** Build a small Kotlin/Spring Boot producer/consumer pair using Spring Kafka; deliberately induce a rebalance and observe behavior. Enable idempotence and a transaction; verify `read_committed` filters aborted messages.

**Milestone:** Write a one-page note reconciling your existing outbox+Debezium pattern with Kafka's native EOS — explain precisely why the transactional outbox is still preferred over producer transactions for DB-to-Kafka consistency.

### Phase 2 — Internals for Deep Understanding (Weeks 5-9, ~40 hrs)
**Goal:** Understand Kafka's implementation deeply enough to reason about performance, failure, and new features.

**Storage engine & request path:**
- **Course (free):** Confluent Developer "Kafka Internals" (Jun Rao, a Kafka co-creator). Covers the storage layer, replication, and the produce/fetch path authoritatively.
- **Docs/essays (free):** The Definitive Guide 2e internals chapters (storage, replication); Confluent engineering blog posts on the log segment format, indexes, and zero-copy (`sendfile`).
- Study RecordBatch format v2 (message format v0/v1 were removed in 4.0), log segments + `.index`/`.timeindex` files, page-cache reliance, and zero-copy reads.

**Controller & consensus:**
- **KIP-500** (Replace ZooKeeper with a Self-Managed Metadata Quorum) and the KRaft design. Note KIP-996 (pre-vote) and KIP-853 (dynamic KRaft quorums, in 3.9). KRaft scales to ~1.9M partitions and gives near-instant controller failover.
- **Real-world proof point:** Aiven migrated 15,000 servers from ZooKeeper to KRaft in three months with zero downtime.

**Rebalance protocol (critical for your stack):**
- **KIP-848** — "The Next Generation of the Consumer Rebalance Protocol," GA in Kafka 4.0. Read the KIP (authors David Jacot, Guozhang Wang, Jason Gustafson) and the Confluent blog. Coordination moves to the broker-side group coordinator via a continuous `ConsumerGroupHeartbeat`; enable with `group.protocol=consumer`. The Kafka community benchmark cited by Confluent shows "a group with 10 consumers adding 900 partitions completes rebalancing in 5 seconds instead of 103 seconds" (Instaclustr frames the overall gain as "up to 20x faster").
- Watch the Current 2024 talk "The Performance of Kafka's New Consumer Rebalance Protocol."

**Queues / share groups:**
- **KIP-932** — "Queues for Kafka." Share groups allow more consumers than partitions, per-message acknowledgement (accept/release/reject/renew), 30-second acquisition locks, and a delivery-count limit (default 5) with archival. Early access in 4.0, preview in 4.1, GA with Kafka 4.2 (Confluent Platform 8.2). Read Gunnar Morling's "Let's Take a Look at… KIP-932" and the Spring Kafka "Kafka Queues (Share Consumer)" docs — Spring for Apache Kafka 4.1 gives full production support.

**Tiered storage:**
- **KIP-405** (Kafka Tiered Storage, GA) — local + remote tiers (S3/HDFS), separate `local.retention.*` vs. `retention.*`. Read the KIP and Uber's Current 2023 talk "Learnings of Running Kafka Tiered Storage at Scale" (Satish Duggana). Note KIP-1176 (tiered storage for active log segment) and KIP-1272 (compacted topic support) as the frontier.

**Reading source code:**
- Start with the `clients` module (producer/consumer), then `storage`/`core` (log, `RemoteLogManager`), then `metadata`/`raft` (KRaft). Use the KIP as the "design doc" for each area before diving in. The Strimzi operator (Java) is also worth reading to understand K8s-native operations.

**Lab:** Enable KIP-848 on your consumer group and measure rebalance time before/after with a synthetic scale-out. Separately, enable share groups on a sandbox 4.2 cluster and build a `KafkaShareConsumer`-based worker-queue with retry/reject semantics.

**Milestone:** Draw the full produce path (client → leader → ISR → high-watermark advance → ack) and the fetch path (including fetch-from-follower and tiered fetch), and explain where each new KIP intervenes.

### Phase 3 — Use Cases & Architecture Patterns (Weeks 10-13, ~30 hrs)
**Goal:** Master event-driven architecture (EDA), event sourcing, CQRS, stream processing, CDC, and data integration — and know when each applies.

**Books & essays:**
- **Book (paid, essential):** *Designing Data-Intensive Applications* — Martin Kleppmann (O'Reilly). Chapters 11 (stream processing) and 5 (replication) are the theoretical backbone. (A 2nd edition is in progress; the 1st edition remains the standard.)
- **Book/report (free):** *Making Sense of Stream Processing* — Martin Kleppmann (O'Reilly/Confluent).
- **Articles (free):** Martin Fowler's "What do you mean by 'Event-Driven'?" and related EDA/event-sourcing/CQRS notes.
- **Book (paid):** *Kafka Streams in Action*, 2nd Edition — William P. Bejeck Jr. (Manning) for the Streams DSL.

**Stream processing & integration:**
- Kafka Streams vs. ksqlDB vs. Apache Flink (Confluent's managed Flink is now the strategic direction). Confluent Developer has free Flink SQL and Kafka Streams courses.
- **Kafka Connect** for data integration; understand single-message transforms, converters, and the connector ecosystem.

**CDC (your existing strength, deepened):**
- **Gunnar Morling** (morling.dev, ex-Debezium lead) is the authority. Read his outbox-pattern and "dual writes" material, plus the Debezium docs. Reinforce why log-based CDC beats polling and why "friends don't let friends do dual writes."

**Real-world case studies (free, high-signal):**
- **Uber:** trillions of messages/day, ~12M messages/sec; built uReplicator, Chaperone, uForwarder (push-based consumer proxy decoupling partition count from consumer concurrency), cluster federation (~150 nodes/cluster), Kappa+ backfill, DLQs.
- **Cloudflare:** 1 trillion+ inter-service messages, 14 clusters, ~330 nodes; Protobuf contracts, "Messagebus" + connector framework; lessons on opinionated SDK defaults and schema governance (QCon London 2023).
- **LinkedIn** (origin), **Netflix**, **Pinterest**, **Shopify** engineering blogs.

**Lab:** Build a CDC pipeline: Aurora MySQL → Debezium → Kafka → a materialized read model (e.g., Elasticsearch or a denormalized store), demonstrating CQRS. Bonus: enrich the stream with Kafka Streams.

**Milestone:** Produce an architecture decision record (ADR) for one of your real systems choosing between messaging (queue/share group), event streaming, and CDC — with explicit tradeoffs.

### Phase 4 — Tradeoffs & the Competitive Landscape (Weeks 14-16, ~20 hrs)
**Goal:** Form defensible opinions on Kafka vs. alternatives and understand the benchmark/cost wars.

**Alternatives (know the shape of each):**
- **Apache Pulsar:** separates compute (brokers) from storage (BookKeeper); native geo-replication and multi-tenancy; more moving parts.
- **RabbitMQ:** queue/routing semantics, no replay; great for task queues and complex routing.
- **AWS Kinesis:** fully managed, AWS-native, no open-source portability.
- **NATS JetStream:** ultra-lightweight, cheap per-stream; excellent for tens of thousands of per-tenant streams and microservice/IoT messaging; not a big-data firehose.
- **Redpanda:** C++/thread-per-core, no JVM/ZooKeeper, single binary, Kafka-API compatible; strong single-node latency.
- **WarpStream:** diskless, S3-native, stateless "Agents," BYOC, zero inter-AZ cost; ~26 Kafka APIs. Per WarpStream's docs, it "typically achieves a p99 produce latency of 400ms in its default configuration"; with S3 Express One Zone it cuts "median produce latency to 105ms, and the p99 to 170ms" (its newer "Lightning Topics" reach ~33ms median / <50ms p99). Acquired by Confluent Sept 2024.
- **AutoMQ:** Kafka-compatible, reuses KRaft, offloads storage to S3/EBS WAL; open-source core (S3Stream); supports ~73 Kafka APIs; single-digit-ms with EBS WAL.
- **Google Pub/Sub, Azure Event Hubs, AWS SQS:** know that SQS is the right answer for simple job dispatch.

**Benchmark & cost wars (read critically):**
- **Jack Vanlightly's** "Kafka vs Redpanda Performance – Do the claims add up?" (jack-vanlightly.com, May 2023). His conclusion: Redpanda's headline claims are "greatly exaggerated"; Redpanda degraded significantly at 50 producers and couldn't hit 1 GB/s with TLS, while Kafka could. His core message: benchmarks are only useful run on your own workload. Note the fsync counter-argument from Redpanda.
- **Inter-AZ cost** is the crux: every GiB replicated cross-AZ costs ~$0.02 round trip; ~1 TB/day at RF=3 ≈ ~$1,200/month just for internal replication before consumer fan-out.
- **KIP-1150 (Diskless Topics):** accepted March 2, 2026 (9 binding + 5 non-binding votes); a "meta-KIP" with sub-KIPs 1163 (core), 1164 (batch coordinator), 1165 (compaction). Leaderless, object-storage-backed, claims up to ~80% TCO reduction; production-readiness is years away (KIP-500 took ~5.5 years). Read Aiven's "Hitchhiker's Guide to Diskless Kafka" and the AutoMQ/Instaclustr analyses.
- **The "Kafka is overkill" debate:** Aiven's "Kafka's 80% Problem" (running "4000+ Kafka clusters for 1000+ companies") states "60% of clusters are under 1 mb/s" and concludes "for 80% of use cases, Kafka is currently overkill."

**Milestone:** Write a decision matrix: for three concrete workloads (a high-throughput event backbone, a per-tenant SaaS notification stream, a simple job queue), pick Kafka / share groups / NATS / SQS / a diskless platform and justify it.

### Phase 5 — Production Operations Playbook (Weeks 17-21, ~40 hrs)
**Goal:** Be able to size, monitor, secure, upgrade, and firefight Kafka in production.

**Capacity & partition planning:**
- Rule of thumb: **100-200 partitions per broker as a baseline; avoid >4,000 partitions per broker** to protect the controller.
- Size for peak, not average; account for RF, retention, and consumer fan-out.

**Monitoring & tooling:**
- **Key metrics:** under-replicated partitions, `UnderMinIsrPartitionCount`, consumer lag, request-handler idle ratio, `ActiveControllerCount`, request latencies.
- **Tools:** Cruise Control (rebalancing/self-healing), Burrow (lag), kcat, AKHQ, Kafka UI, Conduktor; Prometheus + Grafana via JMX exporter.
- **Course (paid):** Stephane Maarek "Kafka Monitoring & Operations" and "Kafka Cluster Setup & Administration" (Udemy) — note the setup course still teaches ZooKeeper, so treat that part as historical.

**Upgrades, DR, multi-region:**
- Rolling restarts; the 3.9 → 4.0 bridge path.
- **MirrorMaker 2**, Confluent Replicator, and stretch clusters for DR. Note MM2's operational sharp edges (topic renaming `<source>.<topic>`, offset translation; Uber found MM2 rebalancing caused weekly outages).

**Security:** TLS, SASL (SCRAM/GSSAPI), OAuth, ACLs, quotas. Note MSK Serverless requires IAM and does **not** support Kafka ACLs.

**Incident playbook (study each failure mode):** unclean leader election, ISR shrinkage, disk full, rebalance storms, hot partitions.

**Performance tuning:** `batch.size`, `linger.ms`, compression, `fetch.min.bytes`/`fetch.max.wait.ms`, producer/consumer buffer sizes, OS page-cache tuning, `client.rack` for fetch-from-follower to cut cross-AZ reads.

**War stories (free):** Uber's Chaperone/uReplicator/uForwarder posts; Cloudflare's trillion-message posts; Confluent's operations docs; the Definitive Guide 2e operations chapters.

**Lab:** (1) Run `kafka-producer-perf-test` and `kafka-consumer-perf-test` on your local/EKS cluster; sweep `linger.ms`/`batch.size`/compression and chart throughput vs. latency. (2) Chaos test: kill a broker mid-produce with `acks=all` and observe ISR/leader election. (3) Run a MirrorMaker 2 DR drill between two clusters and validate consumer offset translation.

**Milestone:** Produce a one-page runbook for the top-5 incidents with detection metric, immediate mitigation, and root-cause follow-up.

### Phase 6 — Self-Managed vs. Managed Decision Framework (Weeks 22-24, ~25 hrs) — CRITICAL

**Goal:** Build a rigorous, numbers-driven framework for choosing among self-managed (Strimzi-on-EKS, EC2), MSK / MSK Serverless, Confluent Cloud, Aiven, Redpanda Cloud, and WarpStream BYOC — tuned to your Seoul/EKS context.

**The options and who owns what:**
- **Self-managed on EKS (Strimzi):** you own upgrades, scaling, partition rebalancing (via Cruise Control), security patching, DR. Strimzi is a CNCF project, KRaft-ready, declarative via CRDs (Kafka, KafkaTopic, KafkaUser, KafkaNodePool). AWS publishes a "Deploying and scaling Kafka on EKS" (Data on EKS) blueprint; Graviton (arm64) images give meaningful price-performance gains. Caveat (from Cookpad): Strimzi typically supports a new Kafka release ~a month after GA, and understanding operator behavior sometimes means reading its Java source.
- **Self-managed on EC2/VMs:** maximum control, maximum toil.
- **AWS MSK Provisioned:** AWS manages brokers; you still size and rebalance. Standard vs. Express brokers (Express = up to 3x throughput/broker, 20x faster scaling, 90% faster recovery).
- **MSK Serverless:** no capacity planning; **requires IAM, no Kafka ACLs**, limited config surface; available in **Seoul (ap-northeast-2)**.
- **Confluent Cloud:** most complete platform (Schema Registry, connectors, ksqlDB, managed Flink, tiered storage, Kora engine autoscaling); Dedicated uses provisioned **CKUs**, Basic/Standard/Enterprise use elastic **eCKUs**; 99.99% SLA.
- **Aiven, Redpanda Cloud, WarpStream BYOC:** Aiven = multi-cloud managed OSS Kafka; Redpanda Cloud = low-latency C++ engine; WarpStream BYOC = data stays in your S3/VPC, control plane managed, zero inter-AZ cost, ideal for logging/observability with relaxed latency.

**TCO anatomy (the part people get wrong):**
- **Inter-AZ data transfer often dominates** — Confluent's own "A Guide to Mastering Kafka's Infrastructure Costs" (2023) states cross-AZ transfer "can surprisingly account for more than 50% of infrastructure costs when self-managing Apache Kafka" (its Freight-cluster blog puts it as high as 88%). A 3-AZ RF=3 cluster writes cross-zone 2/3 of the time and replicates to two followers.
- **Engineering headcount is the other half** — Confluent's TCO analysis assumes ~3-4 engineers for self-managed vs. "nearly zero" for Cloud.
- **Illustrative MSK Provisioned monthly example:** 6-broker cluster, 5 TB storage, 3 TB in/out, multi-AZ ≈ $8,556/month, of which ~$2,500 is operational overhead (0.5 FTE) — showing people cost is a real line item even on managed.
- **Confluent Cloud pricing shape:** billed on eCKUs/CKUs ($/hour) + networking ($/GB) + storage ($/GB-hour); a CKU supports roughly ~50 MB/s ingress / ~150 MB/s egress. Confluent does not publish exact per-unit rates — use their cost estimator; expect Dedicated clusters with governance to reach five-to-six figures/month at scale.
- **Diskless/S3 savings (vendor-reported, verify on your workload):** WarpStream claims 5-10x cheaper than cloud Kafka; AutoMQ reports ~50-77% reductions; FunPlus reported >60% infra cost reduction migrating MSK→AutoMQ. Treat all vendor figures skeptically and model your own.

**The threshold — concrete guidance:**
- **Aiven's "80% problem" anchor:** at a few MB/s (~300-400 GB/day), self-managing a three-AZ, RF=3 posture "rounds to at least $300,000/yr once infra + people are counted," versus managed "priced around $50,000/yr." Below ~1 MB/s (where 60% of clusters live, per Aiven), managed almost always wins.
- **Migration reality (managed → self-managed):** Cookpad moved Confluent Cloud → Strimzi-on-EKS with a ~6-month project staffed by ~3 SREs, and explicitly still recommends managed (Confluent Cloud) for teams getting started. The decision was strategic (wanting to run their own clusters), not purely cost.
- **Practical rule for your situation:** self-managing Strimzi-on-EKS starts to pay off when you (a) sustain high, steady throughput (hundreds of MB/s), (b) have ≥2-3 engineers who can own Kafka as a platform, (c) see inter-AZ/licensing costs dominating a managed bill, and (d) need config/plugin control or data-residency guarantees a managed tier won't give. Otherwise, MSK (Serverless for spiky/early-stage, Provisioned/Express for steady/high-throughput) or Confluent Cloud (for the ecosystem and elastic scaling) is the rational default.

**Seoul/ap-northeast-2 notes:** MSK (Provisioned + Serverless) and Confluent Cloud are available in ap-northeast-2. If data residency in Korea is a compliance requirement, WarpStream BYOC / Confluent Private Cloud / self-managed Strimzi keep data in your own VPC/buckets.

**Lab:** Build a mock cost evaluation spreadsheet for one of your real workloads: model MSK Provisioned, MSK Serverless, Confluent Cloud, and Strimzi-on-EKS across broker/compute, storage, inter-AZ transfer, and estimated FTE cost. Include a sensitivity analysis on throughput growth and consumer fan-out.

**Milestone:** Deliver a decision memo recommending a platform for your team with explicit thresholds that would flip the recommendation (e.g., "switch to self-managed if sustained throughput exceeds X MB/s AND we hire a second platform engineer").

## Korean-Language Resources (supplementary)
- **Kakao Tech blog** (tech.kakao.com): "카카오 개발자들을 위한 공용 Message Streaming Platform - Kafka & RabbitMQ" — real operational account of running shared Kafka + RabbitMQ clusters, Grafana dashboards, dedicated vs. shared cluster tradeoffs.
- **Woowahan (배달의민족) tech blog** (techblog.woowahan.com): "우리 팀은 카프카를 어떻게 사용하고 있을까" — EventBus, Kafka Streams, and transactional outbox pattern in production; also references the Korean book *아파치 카프카 애플리케이션 프로그래밍 with 자바*.
- **LINE/Naver engineering blogs** for large-scale operations posts.
- Use these to reinforce, not replace, the English core.

## Recommendations
1. **Start now with Phases 0-1 (re-grounding in the 4.x/KRaft era)** even though you know the basics — the ZooKeeper removal, KIP-848, and KIP-932 materially change what "fundamentals" means. Budget 2-3 weeks.
2. **Front-load the two KIPs that touch your Spring stack** (848 and 932) in Phase 2; enable `group.protocol=consumer` in a staging consumer group and measure the rebalance improvement yourself.
3. **Do the CDC lab in Phase 3 against Aurora MySQL** to connect new learning to your existing Debezium/outbox expertise.
4. **Treat Phase 6 as the capstone**: produce a real cost model and decision memo for your team. Default to managed (MSK or Confluent Cloud in Seoul) unless your numbers cross the thresholds above.
5. **Benchmarks changing your recommendation:** revisit the self-managed decision if sustained throughput crosses into the hundreds of MB/s, if inter-AZ transfer exceeds ~30-50% of your managed bill, or if you add a dedicated platform engineer. Revisit diskless (WarpStream/AutoMQ/KIP-1150) once KIP-1150 sub-KIPs reach production maturity.

## Caveats
- **Vendor sources are biased.** Confluent, AutoMQ, WarpStream, Redpanda, and Instaclustr all publish self-favorable cost/benchmark claims. Every dollar figure and percentage from a vendor should be re-derived on your own workload before it drives a decision.
- **Confluent does not publish exact per-CKU/eCKU rates**; third-party estimates (e.g., ~$8.75/CKU-hour) are unofficial — use Confluent's cost estimator.
- **KIP-1150 diskless is directional, not production-ready.** The vote (March 2026) approved the vision; the sub-KIPs (core, coordinator, compaction) are still being engineered, and latency/ordering/transaction guarantees need validation.
- **The IBM–Confluent acquisition ($31/share, ~$11B enterprise value, announced Dec 8, 2025; closed March 17, 2026) introduces roadmap uncertainty** for Confluent Cloud/WarpStream customers; watch for changes.
- **KIP-932 share groups reached GA on Confluent's Platform 8.2 / Kafka 4.2 timeline; confirm the exact Apache release status before relying on it in production**, and note early-access clusters can't be upgraded in place.
- **Courses age.** Maarek's admin/setup courses still contain ZooKeeper material; the Definitive Guide 2e (2021) predates 4.0 — supplement operations content with current Apache docs and Confluent blogs.