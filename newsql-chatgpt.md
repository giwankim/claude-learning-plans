---
title: "NewSQL (ChatGPT)"
category: "NewSQL"
description: "NewSQL research notes from a ChatGPT perspective"
---

# Globally Distributed Active-Active NewSQL: Research Notes

## 1) What “globally distributed active-active NewSQL” means
A **globally distributed active-active NewSQL** system is a **distributed SQL database** that:
- Runs across **multiple geographic regions** (multi-datacenter / multi-cloud regions).
- Is **active-active**: more than one region is **serving live traffic** (reads and typically writes).
- Preserves **SQL + ACID transactions** (strong transactional semantics) while scaling horizontally.

NewSQL aims to combine:
- **NoSQL-style scale-out** (shared-nothing, sharding, replication), and
- **Relational DB guarantees** (SQL, schemas, joins, ACID, constraints).

---

## 2) Core architecture patterns

### 2.1 Shared-nothing + sharding (partitioning)
- **Shared-nothing**: each node has its own CPU/memory/disk; no shared storage.
- Data is split into **shards / ranges / tablets**.
- Shards can **split/merge** automatically as they grow and can be **moved** for rebalancing.

### 2.2 Replication + consensus groups
- Each shard is replicated across multiple nodes/regions.
- Replicas for a shard form a **consensus group** (typically **Raft** or **Paxos**).
- Usually **single-leader per shard**:
  - The leader coordinates writes for that shard.
  - Followers replicate the log.
  - Majority quorum acks → commit.

### 2.3 Distributed transactions across shards
When a transaction spans multiple shards:
- The system coordinates commit across them (often **2PC layered on consensus logs**).
- Most systems use **MVCC** (multi-version concurrency control) so readers can get consistent snapshots.
- Some systems use globally meaningful timestamps (e.g., TrueTime-like bounded uncertainty) or hybrid logical clocks.

### 2.4 Metadata and placement services
- A small set of metadata services track:
  - shard ownership/locations,
  - replica membership,
  - placement rules.
- These services are usually replicated and not on the critical data path for most queries.

---

## 3) Consistency & availability tradeoffs (CAP + PACELC)

### 3.1 CAP in one sentence
During a **network partition**, you can’t have both **availability** and **strong consistency**.  
Most globally distributed NewSQL systems choose **CP** behavior: preserve consistency, potentially reject/queue some operations if quorum can’t be reached.

### 3.2 PACELC: the “else latency” reminder
Even when there’s *no* partition, there’s still a tradeoff:
- **Else**: choose **latency** or **consistency**.
NewSQL commonly favors **consistency**, which means cross-region coordination can increase latency, especially for writes.

### 3.3 Practical consistency model
- Typically offers **serializable** (or strict-serializable/linearizable) transactions.
- The database, not the app, prevents write conflicts by ordering them through leaders + quorums.

---

## 4) Latency: what gets slower, and what can be optimized

### 4.1 What inherently costs latency
- **Cross-region write commits**: consensus requires WAN round trips.
- **Multi-shard transactions**: additional coordination beyond a single shard.

### 4.2 Mitigation techniques
1. **Data locality / geo-partitioning**
   - Keep data near the users who most often access it.
   - Place leaders close to the primary write region for that shard.

2. **Follower reads / stale reads**
   - Serve reads from local replicas at a safe timestamp (bounded staleness) to avoid leader round trips.
   - Great for read-heavy workloads where “a few seconds old” is acceptable.

3. **Locality-aware routing**
   - Send clients to nearest region/replica.
   - Route writes to the shard leader; route reads to local replica when allowed.

4. **Minimize cross-region transactions via schema design**
   - Partition keys that keep common transactions within a single region/shard.
   - Avoid global uniqueness constraints unless necessary.

---

## 5) Use cases where global active-active NewSQL is a good fit
- **Financial/ledger-like systems** (payments, balances) needing global correctness.
- **Multi-region SaaS** with global customers and strict data integrity.
- **E-commerce** where inventory/orders must be consistent, with high availability.
- **Operational + near-real-time analytics (HTAP)** where fresh global data matters.
- Some **IoT backends** when you need consistent global state (not just telemetry ingestion).

A good rule:
- If **eventual consistency is unacceptable** and you need **multi-region failover + global presence**, NewSQL is compelling.

---

## 6) Comparisons to other approaches

### 6.1 Multi-primary RDBMS clusters (traditional “multi-master”)
Pros:
- Writes can occur at multiple sites.
Cons:
- **Conflict resolution** is hard; strong global ACID is difficult without heavy coordination.
- Often limited scale; operational complexity increases quickly.

### 6.2 Distributed NoSQL (often AP / eventual consistency)
Pros:
- Excellent availability and local write latency.
Cons:
- Often eventual consistency; app must handle anomalies/conflicts.
- Limited joins/transactions (varies by product).

### 6.3 Single-primary + read replicas (active-passive)
Pros:
- Simpler operational model; strong consistency if reads go to primary.
Cons:
- Writes centralized to one region; failover is non-trivial; distant writers pay high latency.

---

## 7) Implementation planning pointers (deploying or building)

### 7.1 Topology & quorums
- Use **odd replication factors** (3 or 5) per shard.
- Place replicas so a quorum survives a region outage.
- Decide if quorums are regional (low latency) or global (higher resilience + higher latency).

### 7.2 Data placement & schema strategy
- Geo-partition by tenant/user/region to keep most transactions local.
- Avoid cross-region hot keys and wide multi-shard transactions.
- Decide which data must be global vs regional.

### 7.3 Routing and client behavior
- Geo-aware load balancing to nearest region.
- Make sure client drivers handle retries on leader changes and transient failures.

### 7.4 Failure testing
- Regularly simulate:
  - region loss,
  - partial partitions,
  - leader churn.
- Validate application behavior under “cannot reach quorum” errors.

### 7.5 Observability and operations
- Monitor:
  - p50/p95/p99 latencies by region,
  - leader distribution,
  - replication health,
  - transaction retries/aborts,
  - network egress costs (can be significant).
- Plan rolling upgrades, backups, and restores (consistent snapshots).

---

## 8) Quick reference table

| Dimension | Global Active-Active NewSQL | Multi-primary RDBMS | Distributed NoSQL (eventual/AP) |
|---|---|---|---|
| Consistency | Strong (often serializable) | Often conflicts unless heavy coordination | Often eventual / tunable |
| Writes | Quorum/consensus per shard | Any master can write; conflict risk | Local writes; async sync |
| Latency | Writes can be WAN-bound | Sync = WAN-bound; async = conflicts | Very low local; global convergence later |
| Scale-out | Built-in sharding | Limited unless manual sharding | Strong scale-out |
| App complexity | Lower (DB enforces consistency) | Higher (conflicts/edge cases) | Higher (staleness/conflicts) |
| Ops complexity | High but automated in modern systems | High; conflict handling is painful | Moderate; app complexity shifts left |

---

## 9) Next steps for learning + implementation
- Read about **Raft/Paxos**, **quorums**, **MVCC**, **2PC**, and **geo-partitioning**.
- For hands-on:
  - Build a toy model: shard → consensus group → MVCC storage → 2PC coordinator.
  - Deploy a real distributed SQL system in 2–3 regions and measure:
    - local vs remote write latency,
    - follower-read behavior,
    - failover time,
    - cost (egress).
