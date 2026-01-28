# Globally distributed active-active NewSQL databases explained

NewSQL databases represent a fundamental architectural shift that delivers what traditional systems couldn't: **full ACID transactions with horizontal scalability across global regions**. For a developer moving from MySQL with Kafka-based eventual consistency patterns, these systems eliminate the complexity of managing distributed transactions at the application layer—the database handles it natively through consensus protocols like Raft and Paxos.

The critical insight is that "active-active" in NewSQL means something different than traditional multi-master replication. Rather than accepting writes everywhere and resolving conflicts afterward (last-write-wins), consensus-based NewSQL databases **prevent conflicts entirely** by routing writes through elected leaders and requiring majority acknowledgment before commit. This delivers strong consistency but introduces latency proportional to cross-region round-trip times—typically **100-300ms for global writes**.

## What makes NewSQL distinct from RDBMS and NoSQL

The term "NewSQL" was coined by 451 Research analyst Matt Aslett in 2011 to describe databases that don't fit the traditional RDBMS mold yet diverge from NoSQL's eventual consistency model. The defining characteristics are: relational model with standard SQL, full ACID compliance in distributed environments, shared-nothing architecture with automatic sharding, and consensus-based replication.

**Traditional RDBMS limitations become apparent at scale**. MySQL and PostgreSQL primarily scale vertically—adding more CPU and RAM to a single node. While read replicas exist, write scaling remains constrained to the primary. Manual sharding is possible but breaks cross-shard transactions, requires application-level routing logic, and creates significant operational overhead for rebalancing.

**NoSQL solved scalability but sacrificed consistency**. Cassandra and DynamoDB provide horizontal scaling through eventual consistency. They're AP systems under CAP theorem—prioritizing availability over consistency during partitions. MongoDB added multi-document ACID transactions in version 4.0 (2018), but with significant performance overhead compared to single-document operations.

**NewSQL delivers both**. CockroachDB, for example, automatically divides data into ~64MB ranges, replicates each range via Raft consensus (typically 3 replicas), and transparently rebalances when nodes are added or removed. The application sees a single logical database while the system handles distribution:

```sql
-- Standard SQL works transparently across distributed ranges
SELECT o.order_id, c.name, p.product_name
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN products p ON o.product_id = p.id
WHERE o.created_at > '2026-01-01';
```

The fundamental trade-off is that NewSQL databases are **CP systems**—they choose consistency over availability during network partitions. If a majority quorum cannot be reached, writes block rather than risk inconsistency.

## Global distribution means data lives where your users are

"Globally distributed" means data is replicated across multiple geographic regions—not just for disaster recovery, but for active use. A database might span AWS us-east-1, eu-west-1, and ap-northeast-1 simultaneously, with each region containing multiple availability zones.

**Cross-region latency is the fundamental constraint**. Typical round-trip times: intra-region cross-AZ is 1-6ms, same-continent cross-region is 20-50ms, transatlantic is 70-100ms, and US West to Asia is 150-200ms. No software can overcome physics—designing for data locality becomes essential.

**Data placement strategies minimize cross-region traffic**. Geo-partitioning pins specific data to specific regions:

```sql
-- YugabyteDB: partition users by geography
CREATE TABLE users (
    id UUID, geo VARCHAR, data JSONB,
    PRIMARY KEY (id HASH, geo)
) PARTITION BY LIST (geo);

CREATE TABLE users_eu PARTITION OF users FOR VALUES IN ('eu') TABLESPACE eu_west;
CREATE TABLE users_us PARTITION OF users FOR VALUES IN ('us') TABLESPACE us_east;
```

CockroachDB uses localities hierarchy (`region=us-east-1,zone=us-east-1a`) and supports `REGIONAL BY ROW` tables where each row includes a `crdb_region` column determining its home region. This keeps EU user data in EU, US user data in US, while maintaining a single logical table.

**Replication topology affects both latency and fault tolerance**. A 5-replica configuration across 3 regions (2+2+1) survives region failure but requires cross-region consensus. A 3-replica single-region configuration has lower latency but only survives zone failure. CockroachDB exposes this via "survival goals"—`ZONE` (default) or `REGION` level.

## Active-active architecture prevents conflicts through consensus

The term "active-active" has two distinct meanings in distributed databases, and understanding the difference is crucial.

**Traditional active-active (multi-master)** allows independent writes to any node, propagates changes asynchronously, and resolves conflicts after the fact using mechanisms like last-write-wins (LWW), vector clocks, or CRDTs. DynamoDB Global Tables and Redis Enterprise use this approach. The trade-off: eventual consistency and potential data loss when conflicts are resolved.

**Consensus-based active-active (NewSQL)** takes a fundamentally different approach. Any node can accept writes, but the write routes to the current leader (leaseholder) for the affected data range, which proposes the change via Raft consensus. Only after majority acknowledgment does the write commit. Conflicts are **prevented, not resolved**—only one write can succeed at a time for a given key range.

```
Traditional Active-Active:          Consensus-Based (CockroachDB):
  Node A writes X=1 ─────┐           Client writes X=1 → Gateway node
  Node B writes X=2 ─────┤ (async)                      ↓
                         ↓           Routes to leaseholder for range
            Conflict! Resolve via                       ↓
            LWW → X=2 wins           Raft proposal to followers
                                                        ↓
                                     Majority ack → commit (no conflict possible)
```

**The latency trade-off is explicit**. Single-leader active-passive has low write latency but requires failover on primary failure. Consensus-based active-active has higher write latency (must wait for majority) but automatic failover with zero RPO. Traditional async active-active has lowest latency but eventual consistency.

CockroachDB calls their approach "Multi-Active Availability"—any node can serve as gateway for any operation, but writes are serialized through the leaseholder. This provides the operational simplicity of "write anywhere" while maintaining strong consistency.

## CAP theorem and the real challenge of distributed ACID

The CAP theorem states distributed systems can provide at most two of: Consistency, Availability, and Partition tolerance. Since network partitions are inevitable, the practical choice is between CP (consistency over availability) and AP (availability over consistency). **All NewSQL databases choose CP**—they refuse writes when quorum cannot be reached rather than risk inconsistency.

**PACELC theorem is more useful for understanding trade-offs**. It extends CAP: during Partition choose Availability or Consistency; Else choose Latency or Consistency. NewSQL databases are **PC/EC**—they choose consistency over both availability (during partitions) and latency (during normal operation). This is why cross-region writes inherently have higher latency.

**Consensus protocols are the implementation mechanism**. Raft (used by CockroachDB, YugabyteDB, TiDB) elects a leader per data partition. All writes go through the leader, which replicates to followers via `AppendEntries` RPC. Once a majority acknowledges, the entry commits. Leader election happens automatically when heartbeats timeout, typically completing in seconds.

**Clock synchronization is the hard problem**. Google Spanner uses TrueTime—GPS receivers and atomic clocks providing timestamps with bounded uncertainty (~7ms). When committing, Spanner performs "commit-wait": it waits until the uncertainty interval has passed before acknowledging, ensuring that any subsequent transaction sees the committed data. This provides **external consistency**—if T1 commits before T2 starts in real time, T1's timestamp is guaranteed less than T2's.

Without specialized hardware, CockroachDB uses **Hybrid Logical Clocks (HLC)** combining wall-clock time with logical counters. The trade-off: configurable `max_offset` (default 500ms) creates an "uncertainty interval." If a read encounters a value within this interval, the transaction may need to restart at a higher timestamp. As their docs put it: "Spanner always waits after writes; CockroachDB sometimes retries reads."

**Distributed transactions use enhanced 2PC**. Standard two-phase commit has a blocking problem—if the coordinator fails after prepare but before commit, participants hold locks indefinitely. Spanner solves this by making each 2PC participant a Paxos group (no single point of failure). CockroachDB uses "parallel commits" where the coordinator writes an intent and participants can infer the outcome even if the coordinator fails.

## How the major NewSQL databases compare

### Google Cloud Spanner
The pioneer, launching in 2012 internally and 2017 publicly. Uses **Paxos per partition** with TrueTime for global timestamps. External consistency guarantee is the strongest available—real-time ordering of transactions is preserved. The cost: it's fully managed GCP-only with no self-hosted option, and TrueTime cannot be replicated outside Google infrastructure. Write latency varies from 5-200ms depending on configuration.

### CockroachDB
Open-source (BSL license) with strong PostgreSQL wire protocol compatibility. Uses **Raft consensus** with HLC for timestamps. Provides serializable isolation by default with optimistic concurrency control (transaction retries on conflict). Multi-region features are mature: survival goals, `REGIONAL BY ROW` tables, non-voting replicas for follower reads. The HLC approach means external consistency isn't guaranteed for causally unrelated transactions—a "causal reverse" anomaly is theoretically possible.

### YugabyteDB
Apache 2.0 licensed with dual API support: YSQL (PostgreSQL compatible, using actual PG query layer code) and YCQL (Cassandra compatible). Uses **Raft replication** per tablet. Distinguishes between synchronous replication (strong consistency, higher latency) and **xCluster async replication** (low latency, last-writer-wins conflict resolution). The xCluster approach enables true active-active with independent writes to each region, but with eventual consistency trade-offs.

### TiDB
MySQL-compatible with a clean three-tier architecture: stateless TiDB SQL servers, TiKV distributed storage (CNCF graduated), and PD placement driver. Uses **Multi-Raft** with a centralized **Timestamp Oracle (TSO)** for global ordering. The TSO is a potential bottleneck and SPOF (mitigated by etcd clustering). Excellent for MySQL migrations and HTAP workloads via TiFlash columnar storage. Default isolation is snapshot rather than serializable.

| Feature | Spanner | CockroachDB | YugabyteDB | TiDB |
|---------|---------|-------------|------------|------|
| Open source | ❌ | ✅ (BSL) | ✅ (Apache) | ✅ (Apache) |
| Clock system | TrueTime | HLC (~500ms) | HLC | Centralized TSO |
| Wire compatibility | Custom | PostgreSQL | PG (YSQL) / Cassandra (YCQL) | MySQL |
| True multi-region writes | Leader-based | Leader-based | xCluster (async) | Leader-based |
| External consistency | Yes | Partial | Yes (sync) | Yes (via TSO) |

## Use cases where this architecture delivers value

**Global applications with regulatory requirements** benefit from geo-partitioning. Financial services can keep EU customer data in Frankfurt, US data in Virginia, and Asian data in Singapore—all within one logical database. GDPR compliance becomes architectural rather than application-level.

**Multi-region high availability** with zero RPO is achievable. A 5-replica configuration across 3 regions survives complete region failure without data loss. Traditional MySQL replication requires manual failover and accepts potential data loss; NewSQL provides automatic failover with synchronous replication.

**Low-latency global reads** use follower reads. YugabyteDB reports **8x latency improvement** (430ms → 20ms) for Singapore users reading from a US-primary database when using local follower reads with bounded staleness. CockroachDB's non-voting replicas serve the same purpose.

**Replacing manual sharding** eliminates operational complexity. If you're running MySQL with application-level sharding (or Vitess), migrating to CockroachDB or TiDB provides automatic sharding with cross-shard transactions—no more "shard key must be in every query" constraints.

**Event sourcing complements** exist with Kafka. For a Spring Boot/Kafka architecture, NewSQL databases can serve as the system of record with Kafka handling event streaming. CockroachDB's CDC (Change Data Capture) can publish row changes to Kafka, enabling event-driven architectures with strongly consistent source data.

## Trade-offs demand careful evaluation

**Cross-region write latency is unavoidable**. Physics dictates that a US-East to EU-West round trip takes ~100ms. For synchronous consensus requiring 2 RTTs, expect **200-400ms commit latency** for cross-region writes. Mitigations include geo-partitioning (keep writes local), async replication (accept eventual consistency), or accepting the latency for global consistency.

**Operational complexity increases**. These systems require understanding of consensus protocols, quorum configurations, locality settings, and failure modes. Debugging distributed transactions is harder than single-node MySQL. The managed versions (Spanner, CockroachDB Cloud, TiDB Cloud) reduce but don't eliminate this complexity.

**Cost considerations vary significantly**. Spanner's pricing is premium (~$0.90/node-hour plus storage/networking). Self-hosted CockroachDB or TiDB requires 3+ nodes minimum per region with NVMe storage recommended. For a 3-region deployment with 3 nodes per region, expect significant infrastructure costs plus operational overhead.

**Not every workload needs global distribution**. If your users are in one region and single-node PostgreSQL handles your load, the complexity isn't justified. NewSQL shines when you've outgrown single-node capacity OR need multi-region deployment with strong consistency.

## Conclusion

Globally distributed active-active NewSQL databases solve the historically impossible: ACID transactions across geographic regions with horizontal scalability. The enabling technologies—Raft/Paxos consensus, hybrid logical clocks (or TrueTime), and distributed transaction protocols—have matured significantly since Spanner's 2012 debut.

For a developer familiar with MySQL and Kafka, the key shift is moving transaction coordination from application code into the database. Where you might have used sagas or event sourcing for cross-service consistency, NewSQL provides distributed transactions natively. The trade-off is latency—cross-region writes take 100-400ms versus single-digit milliseconds for single-node operations.

**Choose CockroachDB** for PostgreSQL compatibility with mature multi-region features. **Choose TiDB** for MySQL compatibility with excellent HTAP capabilities. **Choose YugabyteDB** if you need both PostgreSQL and Cassandra APIs or want async active-active via xCluster. **Choose Spanner** if you're on GCP and want the strongest consistency guarantees without operational burden.

The fundamental insight: these databases don't eliminate CAP theorem constraints—they make the trade-offs explicit and configurable. Understanding that cross-region latency, consistency guarantees, and operational complexity are interconnected enables informed architectural decisions.