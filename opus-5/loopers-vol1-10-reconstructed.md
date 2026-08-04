---
title: "Loopers Backend L2 Vol. 4: Volume 1-10 reconstruction from 116 pull requests"
category: "Backend Engineering"
description: "A reconstruction of the ten-volume Loopers backend curriculum assembled from the 116 pull requests in loop-pack-be-l2-vol4-kotlin and about 30 PR bodies, since the assignment specs themselves are absent from main. Requirements are inferred from what 10 to 13 participants independently submitted per volume, plus the checklists a few submitters pasted verbatim, and the author marks where inference replaces quotation. Volume 1 covers three user endpoints built test first, with test taxonomy as the graded artifact. Volume 2 is documents only: requirements spec, sequence diagrams, class diagram, and ERD. Volume 3 implements that design as brand, product, stock, like, and order. Volume 4 adds coupons and requires a different lock mechanism per resource, each defended, proven by MySQL Testcontainers concurrency tests. Volume 5 stages read optimization as index, then denormalization, then cache, in that order and measured at each step. Volume 6 integrates an asynchronous pg-simulator at roughly 60% success and introduces UNKNOWN as a first-class payment state alongside compensation and reconciliation. Volume 7 moves from Spring ApplicationEvents to a Transactional Outbox with Kafka consumers, then re-solves the first-come coupon at spike scale after measuring the synchronous ceiling. Volume 8 builds a Redis sorted-set waiting room with token-bucket admission. Volume 9 builds daily ranking on a Redis ZSET with Lua-atomic idempotency and decayed midnight carry-over. Volume 10 adds restartable Spring Batch weekly and monthly rollups, including a benchmark of four aggregation strategies. Rejected alternatives with trade-offs and self-measured numbers are graded in every volume."
---

> [!summary]
> A reconstruction of the Loopers `loop-pack-be-l2-vol4-kotlin` curriculum (Volumes 1 to 10), built from 116 pull requests and about 30 PR bodies. The assignment specs are absent from `main`; the repo root holds only the Spring/Kotlin template.
> The volumes run from TDD'd user APIs and design-only domain documents through the coupon domain and concurrency control, read optimization, PG resilience, Outbox plus Kafka events, Redis waiting rooms, real-time ranking, and Spring Batch rollups. The Gradle module list (`commerce-api`, `commerce-batch`, `commerce-streamer`) doubles as the syllabus.
> The PR template is itself graded: every submission must name the alternatives it rejected and state the price paid for the one it picked. The author marks where they are inferring rather than quoting.

# Loopers `loop-pack-be-l2-vol4-kotlin`: Volume 1-10 반증적 재구성

> How this was built: GitHub blocks automated fetches on the `/pulls` path, so I pulled all 5 pages of the PR list directly (116 PRs: 25 open, 91 closed) and then read about 30 representative PR bodies across all ten volumes. The assignment specs themselves are not in `main`; the repo root is just the Spring/Kotlin template, with no `docs/` directory. So what follows is reconstructed from the intersection of what 10 to 13 people independently submitted per volume, plus the explicit checklists a few submitters pasted into their PR bodies. Where I'm inferring rather than quoting, I say so.
>
> Volume 10 is the last step. PR #149 is the highest-numbered PR and it's a Volume 10 submission.

---

## Repo shape (constant across all volumes)

The template is a Gradle multi-module Spring Boot + Kotlin project. The module list is the syllabus in disguise: `commerce-streamer` and `commerce-batch` sit empty for the first six volumes, then get switched on exactly when the curriculum needs them.

```
apps/
├── commerce-api        # main service, used from V1
├── commerce-batch      # Spring Batch, first used in V6 (reconciliation), central in V10
└── commerce-streamer   # Kafka consumer app, introduced in V7, extended in V9
modules/  jpa · redis · kafka
supports/ jackson · monitoring · logging
```

Supporting infrastructure is given up front: `docker-compose` for local infra, a separate compose file for Prometheus + Grafana (`localhost:3000`, admin/admin), and a `make init` that installs a ktlint pre-commit hook. A `pg-simulator` module gets added to the repo mid-course (PR #84), immediately before Volume 6.

### The PR template is itself part of the assignment

Every submission follows a fixed structure, and the reviewers clearly grade on it as much as on the code:

- 📌 Summary: 배경 / 목표 / 결과
- 🧭 Context & Decision: 문제 정의 (현재 동작·제약 / 문제·리스크 / 성공 기준=완료 정의) → 선택지와 결정 (고려한 대안 A/B/C → 최종 결정 → 트레이드오프 → 추후 개선 여지)
- 🤔 고민한 점 / 막혔던 부분
- 🙋 기타 (배워간 것, 질문)

PR #1 removes the Summary section from the template and PR #2 adds a 테크 노트 issue form, so the format was still being tuned in week 1. The consistent demand across all ten volumes is: *name the alternatives you rejected and state the price you paid for the one you picked.* Several submissions are effectively design docs with code attached.

### Volume ↔ week mapping

Doc paths in the PRs (`docs/week4/`, `docs/week7/`, `docs/week8/`, `docs/week10/`) confirm that Volume N = Week N. PR #25 also calls Volume 2 "Round 2". PR counts run 13, 8, 11, 12, 11, 10, 11, 12, 9, 7 from Volume 1 through Volume 10; the tapering at the end is the usual attrition curve.

---

## Volume 1: 회원가입 / 내 정보 조회 / 비밀번호 수정

Three endpoints, built test first. The endpoints are almost incidental; what gets graded is TDD discipline and test taxonomy.

### API surface
| 기능 | Method | Path |
|---|---|---|
| 회원가입 | `POST` | `/api/v1/users` |
| 내 정보 조회 | `GET` | `/api/v1/users/me` |
| 비밀번호 수정 | `PATCH` | `/api/v1/users/me/password` |

(The path prefix varies; some used `/api/users`. Not graded.)

### Functional requirements (converged across submissions)
- Auth is deliberately primitive. No session, no JWT, no Spring Security. Identity comes from the `X-Loopers-LoginId` and `X-Loopers-LoginPw` headers, re-verified on every authenticated call. Multiple submitters explicitly justify not pulling in Spring Security ("2%의 기능을 사용하기 위한 복잡도가 너무 큼"); one uses only `at.favre.lib:bcrypt` behind a `PasswordEncoder` port.
- Signup does field validation (loginId, password 8-16자, email, birthDate), hashes the password before persisting, and returns 409 CONFLICT on a duplicate loginId.
- The duplicate-check race is an intended trap. A pre-`SELECT` can't prevent a concurrent insert; the expected answer is to lean on a DB unique constraint and translate the integrity-violation exception. Several PRs call this out explicitly ("중복 체크와 실제 가입 요청 간 갭").
- Password change re-verifies the current password, applies the same policy to the new one, and rejects a new password identical to the old one.
- Some submissions mask the name on `GET /me`.

### Design requirements
- Layer boundaries: `domain` / `application` / `infrastructure` / `interfaces`, with the argument for each boundary written down. Recurring debates: VO extraction (`LoginId`/`Password`/`Email`/`BirthDate`) vs. validating in the entity; separating `SignupRequest` (web DTO) from `SignupCommand` (application input); whether a Facade layer is justified for a single-domain auth concern; whether the domain model and the JPA entity should be separate types (`UserModel` ↔ `UserJpaEntity` with `toDomain()`/`from()`).
- Test taxonomy is the graded artifact. The consensus that emerges: unit tests are white-box and cover every edge case; integration and E2E tests are black-box and cover *one test per responsibility of that layer*, grouping equivalent requirements ("비밀번호는 8~16자가 아니면 BadRequest" as one test, not two). Integration covers domain branching and invariants; E2E covers response format and the HTTP contract. Strict RED → GREEN → REFACTOR, with top-down vs. bottom-up TDD explicitly compared.
- Test fixtures and steps objects (`UserSteps`), plus Testcontainers-backed integration tests.

Side note: PR #32 is a Volume 1 and Volume 2 port from Java to Kotlin, so the cohort included people migrating work from a Java track.

---

## Volume 2: 이커머스 도메인 설계 (문서 4종)

Documents only, with zero production code. The domain scope gets fixed here: 상품 / 브랜드 / 좋아요 / 주문, with 재고, 쿠폰 and 결제 appearing as supporting concepts.

### Required artifacts
1. 요구사항 명세서: user-scenario driven, readable by PM, designer and developer alike, derived from the given API list, and including error and recovery scenarios.
2. 시퀀스 다이어그램: at least two. Split into (a) cross-domain business flows for a non-technical audience and (b) per-domain class-level sequences detailed enough that a developer can implement directly from them.
3. 클래스 다이어그램: an inter-domain relationship map plus per-domain fields, methods, constraints and notes.
4. ERD: table relationships and full schemas, designed for data integrity.

### What the reviewers were actually pushing on
- Document purpose discipline. The dominant complaint in the PRs is content bleeding between the four docs. The cleanest expression of the intent comes from one submitter, who added a per-document checklist plus `SC-{도메인}-{숫자}` scenario IDs so sequence diagrams can *reference* a flow instead of re-drawing it. Another decides soft delete must not appear until the class-level sequence diagram, because the earlier docs have non-developer readers.
- Mentor guidance was explicitly "stay at the design layer this week". Several PRs mention being told not to dive into transaction and concurrency detail yet, since that's V4.
- Design decisions that recur and get carried into V3 and V4: the order line snapshot strategy (typed columns vs. JSON, where typed wins for migration safety and analytics); the order state machine (`payment_pending` → `paid` / `cancelled`, with "payment failed" deliberately not a terminal state); whether the Order aggregate should own stock deduction and coupon usage (the answer is no, Order coordinates state transitions and each domain owns its own rule); and sync-in-one-transaction vs. async payment worker, where most chose async-with-outbox on paper, which V6 and V7 then cash in.

---

## Volume 3: 이커머스 도메인 구현

V2's design, now in code: Brand, Product, Stock/Inventory, Like, Order.

### Per-domain requirements
- Brand and Product: CRUD plus soft delete expressed as a status transition (`ACTIVE → DELETED`) rather than a boolean.
- Product list: filter by `brandId`, sort by latest / price / likeCount, paginate. Offset vs. keyset (cursor) pagination is an explicit decision point; some ship keyset on `(id, price, likeCount)` immediately, most defer it to V5.
- Stock and Inventory: deduct and restore. The big modelling question is whether stock is a VO inside Product or its own aggregate with its own lifecycle. Most start with the VO and note that "주문 생성 → 재고 선점 → 재고 확정" will force a split later. `PESSIMISTIC_WRITE` on stock rows already appears here in several submissions.
- Like: toggle with idempotency (unique constraint on `(user_id, product_id)`), plus a denormalized like count on the product. This is where domain events enter. Publish `ProductLikedEvent`/`ProductUnlikedEvent` once, and let separate `AFTER_COMMIT` listeners handle the count update and the append-only `LikeEvent` history. The lost-update hazard of `product.likeCount++` under dirty checking, versus an atomic `SET like_count = like_count + 1`, is a graded discussion.
- Order: Order aggregate + OrderLine + OrderStatus, order placement reserving stock, order lookup. An idempotency key on order creation, enforced by a DB unique constraint.

### Architectural requirements
- Hexagonal vs. layered + DIP: argue and choose. Both answers are accepted with justification; the common compromise is layered with ports only at the repository boundary (`XxxRepositoryPort` / `XxxRepositoryAdapter`).
- Where does the repository dependency live? A domain service with the repository injected, or a Facade/application layer that does the fetching and hands pure domain objects to a stateless domain service. The second is the more common and more defended answer.
- Keeping Spring out of the domain layer. At least one submission enforces "no `org.springframework.*` import anywhere in `domain/`" by registering domain services as `@Bean`s from an application-layer `@Configuration`, and lists the boilerplate cost as the trade-off.
- Package strategy: layer-first vs. domain-first, with the navigation cost of layer-first acknowledged.
- Separate admin and public application ports, so a public controller can't reach an admin use case.
- Tests must cover creation, state transition, query, sorting, stock deduction, order placement and like toggle.

Explicitly out of scope in V3: real payment (order placement assumes success) and admin authentication (stubbed as an interfaces-layer concern).

---

## Volume 4: 쿠폰 도메인 + 트랜잭션 · 동시성 제어

A coupon domain, an atomic order flow, and proof by concurrent test that the invariants hold. This is the first volume with a hard, measurable pass condition.

### New domain
- CouponTemplate ↔ UserCoupon split. The template holds the discount policy (정액/정률, min order amount, expiry); the issued coupon references it and tracks usage state. Everyone who chose this notes the same trade-off: editing a template retroactively changes already-issued coupons, and snapshotting the discount terms onto `UserCoupon` is the documented escape hatch.
- Expiry by timestamp, not status. Check `expiredAt < now()` at use time rather than running a batch that flips rows to `EXPIRED`, since a batch cannot flip 100k coupons at exactly 10:00.
- Customer-facing and admin APIs for coupons.

### Order flow requirement
Coupon usage, discount calculation, stock deduction and order persistence all happen in one transaction, all or nothing. Transaction ownership must sit in the Facade/application layer, not in the controller and not in a domain service. Several PRs note the reason explicitly: V6 will need to pull the external PG call out of that boundary, so getting it right now is prep work.

### Lock strategy per resource, the core exercise
The exercise is to pick a different mechanism per resource and defend the choice, not simply to add locks:

| 자원 | 채택 | 근거 |
|---|---|---|
| 재고 | 비관적 락 `SELECT … FOR UPDATE` | 재고 10개에 11명이 오면 1~10번은 성공시켜야 한다 → 대기 후 순차 처리가 맞다. 여러 상품 주문 시 `productId` 오름차순으로 락 획득해 데드락 방지 |
| 쿠폰 사용 | 낙관적 락 `@Version` | 경합 주체가 같은 유저(웹+앱 동시 결제) → 1건만 성공, 나머지는 실패시키는 게 맞다. `OptimisticLockingFailureException` → 409 |
| 좋아요 | DB unique constraint / 원자 UPDATE | 중복 방지가 목적인데 락은 과하다 |
| 선착순 쿠폰 발급 | 비관적 락 또는 원자적 조건부 UPDATE | `UPDATE … SET issued_count = issued_count+1 WHERE issued_count < total_quantity`. 캡슐화 vs 성능 트레이드오프를 명시 |

### Verification requirement
MySQL Testcontainers concurrency tests, minimum scenarios:
- same coupon, 10 threads → exactly 1 success, and the failed orders' stock deduction rolled back
- stock 5, 10 threads → exactly 5 successes, remaining stock 0, never negative
- 10 concurrent like/unlike → count stays consistent
- limited-quantity coupon → no over-issuance

The strongest submissions add k6 load measurement (one runs it on an EC2 t3.micro with the load generator on a separate box) and use it to show that the ceiling is lock serialization rather than CPU: single-product 93 req/s vs. distributed 156 req/s at the same ~95% CPU. Two measurement traps get documented and are worth stealing. Per-request BCrypt cost-10 auth dominates the measurement unless you seed the load accounts at cost 4, and a missing index on `inventory.product_id` turns `FOR UPDATE` into a full-scan lock that destroys inter-product isolation.

---

## Volume 5: 읽기 성능 최적화 (설계 및 분석)

A measured, staged optimization of the product read path, where the write-up carries as much weight as the code.

### Required setup
Seed a realistic dataset and measure *before* changing anything. The best-instrumented submission uses 50 브랜드 (대형 5 / 중형 15 / 소형 30), 100,000 상품, 1,000 유저 with Pareto-distributed activity, and 200,000+ 좋아요 with a power law so the top 1% of products hold about 40% of likes. Tools: `EXPLAIN ANALYZE` for single queries, k6 for concurrent load. Baselines reported: 인기순 리스트 344ms to 2.8s single-shot, and at 500 VU, p99 18.5s / 27.7 RPS / 4.4% error.

### Required stages, in this order (the ordering is the lesson)
1. 복합 인덱스. Equality columns (`deleted_at`, `brand_id`) leading, sort column trailing, `id` last for stable sort. Kills filesort on latest-order and price-order queries (18.4ms → 0.44ms; 16.1ms → 0.50ms).
2. The deliberate failure. `ORDER BY COUNT(l.id)` after a `GROUP BY` cannot be fixed by a B-Tree index. In one measurement, adding the index made it *worse* (274ms → 344ms) because the optimizer switched from hash join to nested loop. This sets up stage 3.
3. 비정규화 or 집계 테이블. Either a `products.like_count` column or a separate `product_like_count` MV table. The trade-off is explicit: the denormalized column puts sync and lock contention on the like *write* path, while the MV table decouples writes at the cost of refresh lag. Results: 344ms → 0.15ms, roughly 2,300×. MV refresh is done safely by filling a shadow table and issuing `RENAME TABLE`, which is atomic since DDL doesn't roll back.
4. 캐시. Redis read-through on product detail and list. Required decisions: key strategy (include a `v1` version segment so a response-shape change doesn't serve stale structures), TTL, and invalidation scope. The consistent answer: the detail cache is evicted directly on like events, and the list cache gets a short TTL because the brand × sort × page × size key space is too large to track. Separate the *order* (a sorted ID array) from the *data* (per-id card) into two layers to shrink the invalidation blast radius. Don't cache volatile fields; stock and `soldOut` are composed live on top of cached cards. Cache stampede must be handled, via single-flight or `@Cacheable(sync=true)`.

### Reported outcome format
A staged table is the expected deliverable:

| 단계 | p99 | 처리량 | 에러 |
|---|---|---|---|
| baseline (filesort) | 18.56s | 27.7 RPS | 4.44% |
| + filesort 제거 | 2.39s | 279 RPS | 0% |
| + 레이어 캐시 | 1.01s | 975 RPS | 0% |

And the conclusion the reviewers want: the index and denormalization work contributed more than the cache, and caching first would have hidden the real bottleneck until every miss re-exposed it.

---

## Volume 6: 외부 PG 연동과 회복 탄력성

Integrate the `pg-simulator` (added to the repo in PR #84) as a real external dependency, and survive it.

### The simulator's behaviour defines the problem
It is asynchronous by design: 요청 지연 100-500ms, then 처리 1-5초 후 콜백, at around a 60% success rate. So "the request was accepted" and "the payment completed" are separate events, and there is always a window where you don't know the outcome. Spring is thread per request, so blocking on it leads straight to thread-pool exhaustion.

### Required capabilities
- Transaction boundary (수준 2 → 수준 3). Tx1 validates the order, persists `Payment(PENDING)` and commits → the PG call happens outside any transaction → Tx2 records the result. Respond `PENDING` immediately. The self-invocation trap (`@Transactional` on a method calling itself through `this`) is called out in more than one PR.
- A Resilience4j stack, with each number justified: connect timeout around 200 to 250ms; read timeout around 700ms to 1s, derived from the simulator's 500ms upper bound plus margin and cross-checked against Tomcat's 200 threads; Retry with exponential backoff that excludes 4xx and domain exceptions (`ignore-exceptions`) so business rejections aren't retried; CircuitBreaker with sliding window 10, min calls 5, 50% failure rate, roughly 5 to 10s open, and half-open trial calls; TimeLimiter; and a Fallback returning a user-facing "잠시 후 다시 시도". Composition order matters and must be argued: the circuit wraps the retry, so one exhausted retry cycle counts as one circuit failure.
- A callback endpoint, `POST /api/v1/payments/callback`, made safe by compare-and-set: `UPDATE payments SET … WHERE status='PENDING'`, where affected rows 0 means someone else already finalized it, so the call is a no-op. That is what makes callback and polling racing each other harmless.
- UNKNOWN as a first-class state. A timeout or an open circuit means the outcome is genuinely unknown, and marking it `FAILED` produces "PG took the money, order says failed". The state machine becomes `PENDING → PAID / FAILED / UNKNOWN`, with transitions encapsulated in the enum and same-state transitions idempotent.
- Reconciliation and recovery: re-query stale PENDING payments. Several PRs flag the design trap here. A payment that timed out has no transactionKey yet, since the key is assigned in the response, so recovery must query by `orderId` rather than by key. Terminal handling: confirmed-not-accepted → `FAILED(NOT_ACCEPTED)` plus compensation; still unknown past `T_max` → `UNRESOLVED`, isolate and alert, and do not auto-transition the order. Recovery job placement is a decision point, and most put it in `commerce-batch` as a Spring Batch Job to keep API and batch load separate.
- Compensation atomicity. On failure, the payment state transition, `order.markAsFailed()`, stock restore and coupon restore all happen in a single transaction, idempotently, taking stock locks in the same `productId` ascending order as order creation.
- Callback verification. Match `transactionKey ↔ orderId ↔ amount` and reject mismatches; compare a shared-secret header (`X-Payment-Callback-Secret`) in constant time. A success callback arriving for a `CANCELLED` order goes to `REFUND_REQUIRED` isolation.
- Concurrency: a unique constraint on `payments.order_id` allows at most one active payment per order.

### Verification
WireMock PG stub plus MySQL Testcontainers. Expected matrix: timeout / circuit-open fallback / callback success / callback failure / duplicate callback (CAS) / callback and polling simultaneously (affected=0) / recovery after request timeout / not-accepted finalization / UNRESOLVED isolation / compensation rollback idempotency / CANCELLED→REFUND_REQUIRED / amount mismatch / concurrent payment requests.

---

## Volume 7: 이벤트 기반 아키텍처 + Kafka

Three explicitly staged steps, and the volume where `commerce-streamer` finally gets used.

### Step 1: Spring ApplicationEvent (in-process decoupling)
Pull auxiliary logic out of the main transaction: audit logging, notification stubs, metric collection. Use `@TransactionalEventListener(AFTER_COMMIT)` with `@Async`. The exercise is knowing what *not* to make async; several submissions keep the like-count update synchronous because it's a correctness concern rather than an auxiliary one. An `AsyncUncaughtExceptionHandler` is required so async failures don't disappear silently.

### Step 2: Transactional Outbox → Kafka → consumer
- Publishing. A direct `KafkaTemplate.send()` after commit is the rejected option, because it's a dual write: if the publish fails the event is lost, and if you publish then roll back, a fact that never happened is now public. What's required instead is to write an `outbox_events` row inside the business transaction (`BEFORE_COMMIT`, or `AFTER_COMMIT` with `REQUIRES_NEW`), and have a `@Scheduled` relay publish it with `acks=all` and `enable.idempotence`. Row status is `PENDING/PUBLISHING/PUBLISHED/FAILED` plus `nextRetryAt`. A single `eventId` (UUID) is written to both the row and the payload.
- The nuance that separates good submissions: not everything belongs in the outbox. A product *view* event has no business write to hitch a ride on (the transaction is `readOnly`, so the `BEFORE_COMMIT` insert won't even flush) and losing one is acceptable, so it gets published directly, best effort. The stated rule: "반드시 전달 = Outbox / 유실 허용 = 직접 발행."
- Consuming. `commerce-streamer` consumes `catalog-events` and `order-events` and maintains a `product_metrics` read model. Requirements: at-least-once delivery makes idempotency mandatory, via an `event_handled(event_id)` table plus atomic `INSERT … ON DUPLICATE KEY UPDATE` for the increments; manual ack after processing; poison-pill isolation via per-record error handling or a DLT. The streamer must not depend on `commerce-api`, so it parses its own DTOs. `product_metrics` is defined as a derived, rebuildable read model, with `likes`, orders and view events remaining the sources of truth.
- Topics that stabilize across submissions: `catalog-events`, `order-events`, `coupon-issue-requests`.

### Step 3: 선착순 (limited-quantity) 쿠폰
The same coupon feature as V4, re-solved at spike scale. Requirement: over-issuance 0, duplicate issuance 0, rejections must also be queryable, and confirmation within about 10 seconds.

The intended arc is a measured migration:
1. Measure the DB-only ceiling. A pessimistic lock holding the coupon row's X-lock across the whole transaction means that at a 1000 req/s spike, HikariCP (40) exhausts, `Connection is not available` 500s hit 1.38%, effective throughput lands around 219 req/s, and the bottleneck is lock serialization rather than CPU (api 0.79 core / mysql 0.27 core).
2. Swap to the atomic conditional `UPDATE … WHERE issued_quantity < total_quantity`, where affected rows 0 means SOLD_OUT. Same MySQL, about 6 files changed: 500-errors down 94%, p95 down 35%, and the knee roughly doubles to 550-590 req/s. But peak throughput is unchanged at around 210-220 req/s, which is the structural limit of the synchronous model and the argument for step 3.
3. Go async. The API accepts the request and returns a `requestId` immediately → Kafka (single partition for per-coupon ordering, `acks=all`, idempotent producer) → a single consumer finalizes issuance → the client polls `GET /coupons/issue/{requestId}`. The consumer splits into three transactions: insert `coupon_issue_result(PK=requestId)` as PENDING first, which is the idempotency gate, since a redelivered message sees a finalized row and skips; then the issuance itself (conditional UPDATE + `user_coupon` insert + ISSUED record) in one transaction; then REJECTED recording for failures. Ack only after processing.
4. Optional but well received: a Redis Lua gate in front of Kafka doing an atomic stock `DECR` plus `SADD userId` in one script, returning 409 immediately for sold-out or duplicate requests so invalid traffic never reaches the broker. Redis is framed as an *접수 장부* (admission ledger) rather than a cache, and on Redis failure it fails open, because over-issuance is structurally blocked downstream by the conditional UPDATE plus unique key. Reported result: 0% spike errors, 0 invalid messages into Kafka, over-issuance 0. A new bottleneck also surfaced and got quantified: consumer throughput around 26/s, plus the polling read load.

---

## Volume 8: Redis 기반 주문 대기열 (Virtual Waiting Room)

Back-pressure in front of the order path. The framing: a 초당 100 → 10,000건 spike must not reach the DB connection pool or the PG.

### Why a queue rather than a rate limiter
The required argument is that plain 429 rate-limiting triggers a retry storm, which amplifies load, and has no fairness. A waiting room flattens the peak and gives the user a position, so they wait instead of hammering. The queue does not reduce total work; it controls the release rate.

### Data structure
A Redis Sorted Set: `score` = entry epoch-ms, `member` = userId.
- `ZADD NX` for entry. Because member = userId, duplicate entry is structurally impossible and re-entry preserves the original position.
- `ZRANK` for position, O(log N).
- `ZPOPMIN N` for admission, atomic so there's no contention between schedulers.
- Rejected alternative: a List (`LPUSH`/`RPOP`), which has no position query.

### Admission control
A scheduler pops every fixed delay, typically 100ms. Release rate = batch size × (1000 / fixed-delay). There are two designs, and the upgrade between them is the graded bit:
- Leaky bucket: fixed N per tick. Simple, but after a quiet period it still admits only N even though the system is idle.
- Token bucket: tokens accrue up to a `burst` cap while quiet, so a sudden arrival is absorbed instantly while the average rate stays at `refill`. Combined with `admit = min(floor(bucket), capacity − active)`, a hard capacity ceiling protects the DB pool regardless of burst.
- Sizing must be derived rather than guessed: DB pool 50 × 200ms per order → ~250 theoretical TPS → 70% safety margin → refill ≈ 175/s, burst = 50 (equal to capacity, since the ceiling caps concurrency anyway). All values externalized as properties (`queue.capacity`, `refill-per-second`, `burst`, `token-ttl-seconds`).

### Entry token + gate
Admitted users get a single-use entry token with a TTL of about 5 minutes, issued idempotently via `SET NX`. The order API only accepts requests carrying it. Two gate placements are accepted:
- `@RequestHeader("X-Entry-Token")` plus an application-layer `EntryTokenGate` (validate → execute → consume). Minimal diff, and `CreateOrderUsecase` stays untouched.
- A declarative `@WaitingQueue(topic)` annotation plus `HandlerInterceptor.preHandle`. Chosen over Spring AOP because the interceptor can write a 429 and a waiting token directly to the `HttpServletResponse`, and `topic` lets several endpoints in one user flow share a single queue rather than each having its own line. One limitation is documented: `topic` is a static string, so runtime grouping such as per-product queues isn't possible yet.

### Feedback to the user
`GET /queue/position` polling returns rank, an estimated wait (`rank / refill_rate`) and a dynamic recommended poll interval. SSE and WebSocket were considered and rejected as infra churn, since `ZRANK` takes microseconds and the polling load is fine. `/queue/*` paths must touch no DB at all.

### Boundary conditions (explicitly required, both directions accepted with justification)
- Queue full: a bounded queue that returns 429. One submission notes that the `ZCARD`-then-`ZADD` race is acceptable because the cap is a UX policy rather than a correctness invariant, so it doesn't need Lua atomicity.
- Redis down. This is the interesting one, and the two cohorts split:
  - fail-close 503. Ordering touches stock and payment, so if the gate is unavailable, refuse. Deliberately contrasted against the coupon gate's fail-open in V7 and the detail cache's fail-open, where the cache has a DB fallback and the queue doesn't.
  - fail-open bypass. Keep taking orders ungated and rely on downstream protections.
- Additionally, an admin API to retune admission variables without redeploy (`pollingIntervalMs`, `admitCountPerPoll`, `accessTokenTtlSec`, `admitWindowSec`), effective from the next tick.
- Read/write role separation is part of the design: reads such as product detail go to a Redis cache with stampede protection, stock-bound writes go through the queue, and the external PG stays behind the circuit breaker.

Everyone documents the same caveat: the scheduler runs per instance, so two app instances double the release rate. Everything here assumes a single instance, and the multi-instance fix is moving the bucket into Redis via Lua.

---

## Volume 9: 실시간 상품 랭킹 (Redis ZSET)

### Explicit checklist (pasted verbatim into at least one PR, so this is close to the real spec)

**📈 Ranking Consumer**
- 랭킹 ZSET의 TTL, 키 전략을 적절하게 구성 (`ranking:all:{yyyyMMdd}`, TTL 2일)
- 날짜별로 적재할 키를 계산하는 기능
- 이벤트가 발생한 후, ZSET에 점수가 적절하게 반영

**⚾ Ranking API**
- 랭킹 Page 조회 시 정상적으로 랭킹 정보가 반환
- 랭킹 Page 조회 시 상품정보가 Aggregation되어 제공 (상품명, 가격 등)
- 상품 상세 조회 시 해당 상품의 순위가 함께 반환 (순위에 없다면 `null`)

**🧪 검증**
- 이벤트 발행 → ZSET 점수 반영 → API 조회까지 E2E 흐름 정상 동작
- 일자가 변경되어도 이전 날짜의 랭킹 조회가 정상 동작
- 가중치 적용이 의도대로 랭킹 순서에 반영 (주문 1건 > 좋아요 3건)

### Design requirements behind the checklist
- Why ZSET at all: sorting happens at *write* time via `ZINCRBY`, so reads are O(log N + M). The rejected baseline is `GROUP BY + ORDER BY` on `product_metrics` per request.
- Weights. View, like and order at roughly 0.1 / 0.2 / 0.7. Raw count summation is rejected because views swamp everything else. Order amount gets log10 normalization (`log10(price × quantity + 1)`) so a ₩100,000 single sale doesn't outrank ten ₩1,000 sales. Unlike is a negative `ZINCRBY`. Weights are externalized to config for tuning.
- Time quantization. Daily keys with a short TTL, specifically to kill the long-tail problem where a permanently accumulating score locks old products into the top.
- Idempotency is the hard requirement. Kafka delivers at least once and `ZINCRBY` is not idempotent. The required solution is a Lua script doing `SETNX rank:seen:{eventId}:{productId}` and, only if new, `ZINCRBY`, then applying the TTL to both, atomically. Putting the dedup marker in MySQL and the increment in Redis reintroduces a dual write: the marker is saved but the score lost, or the score is applied and then the transaction rolls back, double counting on redelivery.
- Consumer isolation. A dedicated consumer group (`loopers-ranking-consumer`) on the same topics, with offsets separate from the metrics consumer, so one pipeline's lag, retry or failure can't affect the other. On a Redis outage, propagate the exception and let Kafka redelivery recover, so lag grows but nothing is lost; only unrecoverable format errors go to the DLT.
- Product detail must not depend on Redis. `ZREVRANK` is one O(log N) call, but a Redis failure has to degrade to `ranking: null` rather than a 500.
- Deleted products must be excluded from both the live board and any recovery aggregation.
- Midnight cold start, the flagship design problem. Options weighed: a sliding 24h window (no cold start, but "오늘의 랭킹" loses meaning and bucket management is expensive); a straight copy of yesterday's board (yesterday's #1 starts as today's #1, drowning today's signal); and carry-over at ×0.1 via `ZUNIONSTORE`, which leaves yesterday as a hint that today's real events overtake quickly and that self-extinguishes over days (0.1 → 0.01 → …). Carry-over wins. A nice implementation detail from the best submission: store weights as ×10 integers (10/50/500) so the first generation of carry-over stays integral, then `floor`, and skip the carry entirely once it rounds to 0.
- Rollover with no visible gap. Running the carry-over batch *at* 00:00 means users see a half-built board while it runs. The refined answer is to run it at 23:50 against a separate `ranking:snapshot:{D}` key that stops receiving writes at 23:50, so the batch iterates a frozen structure with no reordering mid-scan, and to have the consumer dual-write during the 23:50 to 24:00 cutoff window: full weight to today's key, ×0.1 to tomorrow's, with all ZSET updates for one event done under a single dedup key in one Lua call so partial application is impossible. The net effect is that the date rollover requires no switchover logic at all, and the API just reads today's key.
- Failure handling. If the batch dies or misses the deadline, the API must still return 200 with a meaningful board, the system should self-trigger recovery, and operators need a metric and an alert. Redis loss must be recoverable by rebuilding today's board from RDB hourly aggregates, since replaying already-committed Kafka offsets is not a recovery path.

---

## Volume 10: 주간 / 월간 랭킹 배치 (Spring Batch), the final volume

### Explicit checklist (again, pasted into a PR)

**Spring Batch**
- Spring Batch Job을 작성하고, **파라미터 기반**으로 동작시킬 수 있다
- **Chunk Oriented Processing** 기반의 배치 처리를 구현했다
- 집계 결과를 저장할 **Materialized View**의 구조를 설계하고 올바르게 적재했다

**Ranking API**
- API가 **일간 / 주간 / 월간** 랭킹을 제공하며, 조회해야 하는 형태에 따라 적절한 데이터를 기반으로 랭킹을 제공한다

### Requirements as implemented
- Job: `productRankJob` / `rankingAggregationJob` in `commerce-batch`, parameterized either as `periodType` (WEEKLY/MONTHLY) plus `periodKey` (`2026-W30`, `2026-07`), or as a single `targetDate` from which the containing ISO week and calendar month are derived. `commerce-batch` runs once and exits; scheduling is an external cron or K8s CronJob concern.
- Source data. `product_metrics` (lifetime totals) is unusable because it has no time axis, so the aggregation source must be `product_metrics_hourly` (product × hour bucket: `view_count`, `like_count` net delta, `order_quantity`). Store raw signals rather than scores in the hourly and the weekly/monthly aggregate tables, and apply weights only at TOP-100 generation time, so a weight change is a re-run rather than a migration.
- Sink. A materialized view: either a single `mv_product_rank` discriminated by `period_type` (simpler to manage, identical schema) or split `mv_product_rank_weekly` / `_monthly`. Columns: period type and key, ranking, product_id, score, and the underlying metric columns. TOP 100 per period.
- Chunk-oriented processing: a real Reader/Processor/Writer step, or chunked processing inside a Tasklet (`EntityManager` with `chunked(500)`). The Tasklet route is accepted when the logic is a single-table read → score → sort → load and the cohesion argument is written down.
- Idempotent re-runs: running the same period twice must not duplicate aggregate or ranking rows.
- Restartability: a failed `JobInstance`, once restarted, must skip completed steps and resume at the failure point. The corollary gets called out too. Don't put the "delete previous period aggregate" work inside a chunk step, or a mid-failure restart will delete data that a later chunk already committed.
- No half-built board visible. Deleting the old MV rows and then inserting new ones in chunks exposes an empty or partial ranking to readers, so use a staging table plus an atomic swap.
- API: `GET /api/v1/rankings?period=DAILY|WEEKLY|MONTHLY&date=…&size=&page=`, defaulting to DAILY for backward compatibility. DAILY reads the Redis ZSET while WEEKLY and MONTHLY read the MV, and both then reuse the existing product and brand assembly logic. Since `commerce-batch` writes a table that `commerce-api` reads with no compile-time dependency between them, the period-key format and schema contract has to be pinned deliberately.
- Tests: week and month boundaries, re-run idempotency, TOP-100 truncation, tie-break ordering, and API regression on the DAILY path.

### The optional but exemplary part
The strongest V10 submission treats "which aggregation strategy" as the actual assignment and benchmarks four variants at 100k products × 49 days (14.7M rows):

| 전략 | 월간 900만 행 | 문제 |
|---|---|---|
| 단발 `INSERT INTO staging SELECT … GROUP BY` (기준선) | 7.4s | 페이스 조절 불가, 버퍼풀 오염, 데이터 10배면 킬하기 애매한 70초 쿼리 |
| A. 페이징 GROUP BY | 388s | MySQL이 매 페이지 GROUP BY 재실행 → 8.94억 행 읽기, 디스크 57.4GB 재독. 부하 분산이 아니라 총량 100배 증폭 |
| B. 스테이징 upsert 누적 | 445s | redo 1.36GB, 앱→DB 전송 1.09GB. 읽기 부하를 줄이려다 쓰기 폭탄 |
| C. 앱 인메모리 Map 집계 | 46.8s | **채택.** DB CPU ~30% 평탄, DB 쓰기는 최종 100행뿐 |

The chosen answer is 6× slower than the baseline on wall clock and loses on total CPU, and gets picked anyway, because the selection criterion is *"운영 DB에 얌전한 것"*: load shape (flat vs. spike), controllability and buffer-pool pollution are axes the benchmark number doesn't capture. Two traps are documented. A `JdbcPagingItemReader` sort key that didn't match the physical PK, because Hibernate orders `@EmbeddedId` columns alphabetically in DDL, turned every page into a full-window filesort, and fixing it took the job from 58분 to 92초. And wall-clock numbers swing by tens of percent depending on buffer-pool warming, so DB-internal counters such as rows examined and redo bytes were used as the cross-check.

---

## The arc, in one paragraph

V1 establishes test discipline and layer boundaries on a trivially small domain. V2 forces the design onto paper before any code exists, and V3 implements it. V4 breaks that implementation with concurrency and makes you pick a *different* lock per resource. V5 breaks it again with data volume and makes you measure before optimizing: index, then denormalize, then cache, in that order, for a reason. V6 introduces an external dependency that can neither be trusted nor rolled back, which produces UNKNOWN states, compensation and reconciliation. V7 removes the synchronous coupling entirely, first with application events, then outbox + Kafka + idempotent consumers, then by re-solving V4's coupon problem at spike scale after *measuring* the synchronous ceiling. V8 puts back-pressure in front of the whole thing. V9 builds a real-time read model on the V7 event stream. V10 adds the offline batch tier and closes the loop by serving daily, weekly and monthly from three different stores behind one endpoint.

Two things are graded in every single volume, and both are emphasized more consistently than any specific technology: rejected alternatives with their trade-offs written down, and numbers from your own measurements rather than reasoning about what should be faster.
