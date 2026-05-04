---
title: "System Design Interviews for Mid-Level FAANG Candidates (L4/L5)"
category: "Backend Engineering"
description: "Two interview-prep plans (16-week Deep Mastery and 4-week Crash Course) for L4/L5 system-design rounds at FAANG, with a curated AI-mock + book + human-mock stack and weekly practice cadence."
---

# Comprehensive Guided Learning Plan: System Design Interviews for Mid‑Level FAANG Candidates (L4/L5)

This plan was built specifically for a mid‑level engineer (3–5 years) targeting Google L4, Meta E4/E5, Amazon SDE‑2, Apple ICT3, Netflix Senior, or Microsoft 62/63. It emphasizes (1) building durable foundations and pattern libraries, (2) practice‑heavy reps, and (3) AI‑powered mock interviews you can do on demand without scheduling friction.

Two plans are included:
- **Deep Mastery Plan** — 16 weeks (~4 months); extensible to 6 months
- **Crash Course Plan** — 4 weeks (~28 days)

All pricing reflects late‑2025 / 2026 publicly listed prices and is best‑effort accurate; promotions change frequently, so verify on the vendor pages before buying.

---

## TL;DR

- **Buy this stack first (≈ $250–$350 total) and you’re set:** ByteByteGo lifetime/annual ($89/yr or ~$499 lifetime, frequently 50% off), Hello Interview Premium ($35/mo ~$249/yr ~$549 lifetime range), and the *Designing Data‑Intensive Applications* book (~$45). Keep ~$150–$300 in reserve for 2–3 human mock interviews on Hello Interview ($170–$419) or interviewing.io ($179+).
- **For AI mocks (your stated priority): the best three in 2026 are Hello Interview "Guided Practice" (live AI feedback inside Premium, the closest to FAANG style); Bugfree.ai (LeetCode‑style AI mock with timed practice and follow‑ups, ~$25/mo or ~$100–$150 lifetime with discount); and mockingly.ai (free conversational AI system‑design interviewer with diagram canvas + Pro tier).** Use them daily — they’re fast (~30–60 min, 24/7), cheap, and ideal for L4/L5 reps.
- **Practice cadence is what wins:** in the 4‑week crash course do 1 AI mock per day + 1 weekly written/timed exercise; in the 16‑week deep plan do 3–4 AI mocks per week, plus 1 human mock every 2 weeks in Phase 4. **Mid‑level (L4/E4/SDE‑2) interviewers want a clean framework, correct trade‑offs, working back‑of‑the‑envelope math, and a structurally complete design — not staff‑level depth.**

---

## Key Findings From Research

### What FAANG mid‑level system design rounds actually test (L4/E4/SDE‑2)
- **One 45–60 min round** (Meta E4 typically gets one; Google L4 sometimes; Amazon SDE‑2 always; Microsoft/Netflix yes; Apple varies by team).
- **Expectation rubric (per Hello Interview, IGotAnOffer, DesignGurus 2026 guides):** clean problem framing & requirements clarification, simple back‑of‑the‑envelope estimation, working API/contract, data model, high‑level architecture diagram, justified DB choice, scaling story (sharding, caching, load balancing, replication), reasonable failure handling, and explicit trade‑off discussion. **You are not expected to design planet‑scale, multi‑region or invent novel consensus protocols** — that’s L5+ territory.
- **Format quirks by company:**
  - **Meta:** "Pirate" round; explicit choice between *system design* (infrastructure) and *product design* (API/feature‑oriented). Heavy on trade‑offs (consistency vs. availability, latency vs. throughput) and depth in one sub‑component.
  - **Google:** Strong emphasis on requirement clarification, data‑model reasoning, and APIs over distributed‑systems theory. L4 is borderline — sometimes you get a "simpler scope" design question; L5 always.
  - **Amazon:** Always include a system‑design round for SDE‑2; the **Bar Raiser** often layers Leadership Principles into the design discussion (e.g., "Customer Obsession" while debating consistency).
  - **Netflix / Microsoft / Apple:** Standard 1 design round at this level; Netflix likes streaming/media questions, Apple prefers product‑oriented design, MS varies by org.

### Best resources (2026 prices, verified)

**Books (canonical):**
- **Designing Data‑Intensive Applications (DDIA)** — Martin Kleppmann (~$40–$50 print; 2nd ed). The "bible" of distributed systems. Read selectively.
- **System Design Interview Vol 1 & Vol 2** — Alex Xu (~$30 each on Amazon, or both included with ByteByteGo). Vol 1 = fundamentals + 16 classic problems; Vol 2 = advanced problems.
- **Understanding Distributed Systems (2nd ed)** — Roberto Vitillo (~$30). Lighter, more approachable than DDIA; great as a *first* book before DDIA.
- **Database Internals** — Alex Petrov (~$45). Optional; only valuable if you want to confidently discuss B‑trees vs LSM‑trees, replication protocols, etc. for L5 ambition.

**Subscription platforms (priced for an individual):**
| Platform | Price (2026) | Best for |
|---|---|---|
| **Hello Interview Premium** | Month / Year / Lifetime tiers (typically ~$35/mo, ~$249/yr, ~$549 lifetime; 20–25% off promos common) | Tightly interview‑calibrated theory + Guided Practice (AI feedback) + 5,000+ tagged real questions. **Best single subscription for this user.** |
| **ByteByteGo** | $189/yr or $499 lifetime list (often 50% off → $89/yr or $249–$299 lifetime) | Alex Xu's books + visual breakdowns of 50+ systems. Strongest for breadth and diagrams. |
| **DesignGurus.io** ("Grokking the System Design Interview" + "Grokking the Advanced System Design Interview") | ~$59–$99/course one‑time; ~$199/yr all‑courses; ~$499 lifetime bundle | Pattern‑first, framework‑driven. Original "Grokking" course. |
| **Educative.io** ("Grokking the Modern System Design Interview") | ~$59 single course; Educative Unlimited ~$299/yr (often 50–70% off → ~$120–$150) | Interactive text + quizzes; widest catalog. |
| **AlgoExpert + SystemsExpert** | $99 + $99, or $148–$199 bundle/yr | Curated video walkthroughs. SystemsExpert is surface‑level for L5+ but solid for L4 fundamentals. |
| **Exponent (TryExponent)** | ~$59/yr starter; ~$79/mo or ~$12/mo on promos for full Pro | Strong courses + free 5/mo peer mocks (Pramp now lives here). |

**AI‑powered mock interview platforms (your stated priority):**
| Platform | Price (2026) | What it does well | Caveats |
|---|---|---|---|
| **Hello Interview – Guided Practice** | Included with Premium | Step‑by‑step practice on 43+ system design / LLD problems with AI feedback tuned by FAANG interviewers; interactive whiteboard. **Highest‑quality AI feedback on the market for system design.** | One free problem outside premium; their old standalone "AI Mock" was deprecated and merged into Guided Practice. |
| **Bugfree.ai** | Lifetime plan $99–$199 (40% off promos common); subscription tiers | "LeetCode for system design" — timed practice, AI follow‑up questions, scoring on diagrams + communication, 150+ problems. Also covers OOD and behavioral. | Newer, smaller content library than Hello Interview. |
| **mockingly.ai** | Free AI mocks; Pro for company‑specific questions and detailed analysis | Free conversational AI interviewer with diagram canvas; instant analysis; 24/7. Great supplement. | Less interview‑calibrated than Hello Interview. |
| **Codemia.io** | Free tier + lifetime (~$99 with 60% off promo) | AI‑guided system design problems + interactive whiteboard + peer mocks. | AI feedback less specific than Hello Interview's. |
| **Exponent AI Practice** | Included in Pro membership ($59–$79+/yr or monthly) | AI behavioral mocks; AI for system design is in beta and weaker than competitors today. | Their peer‑to‑peer mocks (former Pramp) are stronger than their AI for SD. |
| **PracHub** | $21.99/mo or $89.99 lifetime | AI behavioral + system design questions calibrated per company (Meta, Amazon LPs, Google, Anthropic). | Newer; smaller user base. |
| **Pramp (now on Exponent)** | Free peer‑to‑peer; 5 credits/mo on free tier | Live human peer (not AI), free, low pressure. | Quality varies by partner. |

**Human mock interview platforms (worth using late in prep):**
- **interviewing.io** — anonymous mocks with FAANG engineers, $179–$300+/session; dedicated coaching ~$2,000 for 3 sessions.
- **Hello Interview Mocks** — $170–$419/session depending on coach level; vetted FAANG staff/EM coaches; 35–40 min mock + 15–20 min written feedback + recording. **Best human mock platform for system design specifically.**
- **IGotAnOffer** — credit system, 1 credit = $50, 2–5 credits/hour, hundreds of vetted ex‑FAANG coaches; 4.95 average rating. Often the cheapest "real coach" option.
- **Prepfully** — pay‑per‑session, can pick coaches by company.
- **Exponent Coaching** — one‑off sessions $100–$350.

**Free / YouTube essentials:**
- **Hello Interview YouTube** — full mock interview recordings with feedback, the closest free FAANG simulation available.
- **ByteByteGo YouTube** — short, well‑animated explainers; perfect first‑pass on each topic.
- **Gaurav Sen** — classic distributed‑systems explainers (Cassandra, Kafka, consistent hashing).
- **Jordan Has No Life** — deep, opinionated walkthroughs of design problems.
- **System Design Interview channel** — ad‑free, direct walkthroughs.
- **MIT 6.5840 / 6.824 Distributed Systems** — full lectures + lab assignments free at pdos.csail.mit.edu/6.824. Optional but exceptional for fundamentals.
- **Donne Martin's "system‑design‑primer"** GitHub — free, comprehensive cheat‑sheet repo.
- **Hello Interview's free "System Design in a Hurry"** guide — surprisingly complete free curriculum.

---

## The Canonical Topic Map (use for both plans)

### Phase A – Fundamentals
- Scalability axes (vertical vs horizontal; stateless services)
- Latency vs throughput, p50/p95/p99, back‑of‑the‑envelope (QPS, storage, bandwidth)
- CAP theorem; PACELC; ACID vs BASE; consistency models (strong, eventual, causal, read‑your‑writes, monotonic, linearizable)
- Networking basics: HTTP, gRPC, WebSocket, long polling, SSE; DNS; TCP vs UDP; TLS

### Phase B – Building Blocks
- Load balancers (L4 vs L7), reverse proxies, API gateways
- Caching: client/CDN/edge/in‑process/distributed; Redis vs Memcached; cache‑aside, write‑through, write‑back; eviction (LRU/LFU/TTL); cache stampede
- Databases: relational vs document vs wide‑column vs key‑value vs graph vs time‑series vs search (Elasticsearch); B‑trees vs LSM‑trees; indexes
- Replication (single‑leader, multi‑leader, leaderless), partitioning/sharding (range, hash, consistent hashing), quorums
- Message queues / streams: Kafka, SQS, RabbitMQ; at‑most/at‑least/exactly‑once; ordering; backpressure
- Object storage / blob stores (S3); CDNs
- Consensus: Paxos/Raft (high‑level), leader election (ZooKeeper/etcd)

### Phase C – Patterns
- Rate limiting (token bucket, leaky bucket, sliding window)
- Pub/Sub and event‑driven architectures
- Event sourcing & CQRS (mention only — rarely required at L4)
- Idempotency, retries with exponential backoff, circuit breakers, bulkheads, timeouts, dead‑letter queues
- Pagination strategies, fan‑out on read vs fan‑out on write
- Geospatial (geohash, quadtree, S2)
- Search & autocomplete (inverted index, trie, prefix caches)
- Notification/feed delivery patterns

### Phase D – Modern Topics (skim for L4; learn for L5)
- Microservices vs monolith trade‑offs; service mesh (Envoy, Istio)
- Observability: metrics, logs, distributed tracing (OpenTelemetry, Jaeger)
- CI/CD, blue‑green / canary deployments
- ML system design basics (only if applying to ML‑adjacent roles)

### Canonical Practice Problem Set (the "must do" 20)
Tier 1 (every candidate must master): URL Shortener, Pastebin, Rate Limiter, Distributed Cache, Twitter/X News Feed, WhatsApp/Messenger Chat, Instagram, Web Crawler, Search Autocomplete/Typeahead, Notification System.
Tier 2 (highly probable at L4/L5): Dropbox/Google Drive, YouTube/Netflix video streaming, Uber/Lyft, Yelp/Nearby Friends, Top‑K/Trending, Distributed ID Generator (Snowflake), Ticketmaster, Ad Click Aggregation, Metrics & Monitoring (Datadog), Distributed Job Scheduler.
Tier 3 (modern flavors increasingly common 2025–26): Design ChatGPT/LLM serving, Design TikTok, Design Stripe (payments), Design a CDN, Design Google Docs (collaborative editing).

---

# PLAN 1 — DEEP MASTERY (16 weeks, ~6–10 hrs/week; extensible to 24 weeks)

**Goal:** Pattern fluency + 25 problems solved start‑to‑finish + 8–10 mock interviews (mostly AI, some human at the end). Total budget recommendation: ~$300–$600 in resources + ~$300–$500 in human mocks.

### Tools to buy on Day 1
1. **ByteByteGo lifetime or annual** (with 50% off promo if available). *Reason:* gets you Vol 1, Vol 2, OOD book, and ML SD book in one place — cheaper than buying physical books separately.
2. **Hello Interview Premium — annual** ($249‑ish range, 20% off promos common). *Reason:* AI Guided Practice + the best company‑tagged real‑question library + the cleanest "delivery framework" in the industry.
3. **Designing Data‑Intensive Applications** (physical or Kindle, ~$40).
4. **Bugfree.ai lifetime** (~$99–$150 with promo) for daily LeetCode‑style timed mocks.
5. **Optional:** Educative Grokking the Modern System Design Interview ($59) if you want a second written framework.

### Phase 1 — Foundations & Building Blocks (Weeks 1–4, ~30 hrs)

**Week 1 — "Populate the mind: fundamentals"**
- Read: Hello Interview's free "System Design in a Hurry" → Core Concepts + Key Technologies (free).
- Read: DDIA Ch. 1 (Reliable, Scalable, Maintainable) and Ch. 2 (Data Models).
- Watch: ByteByteGo YouTube playlist on basics (CAP, scaling, load balancers, caches).
- Drill: Back‑of‑the‑envelope math — practice converting "100M DAU, 5 posts/user/day" into QPS / storage. Do 5 worked examples.
- Output: write a 1‑page "cheat sheet" of formulas (1 byte per char, 1KB tweet, etc.) you can recall without thinking.

**Week 2 — Storage & databases**
- Read: DDIA Ch. 3 (Storage & Retrieval — B‑trees vs LSM), Ch. 5 (Replication), Ch. 6 (Partitioning).
- Read: Alex Xu Vol 1 chapters on Consistent Hashing and Distributed Systems primer.
- Watch: ByteByteGo videos on SQL vs NoSQL, sharding, replication strategies.
- Mock: do **Bugfree.ai** "Design a Distributed Key‑Value Store" with timer.

**Week 3 — Caching, CDNs, message queues**
- Read: Alex Xu Vol 1 chapters on Distributed Cache + Notification System.
- Read: Understanding Distributed Systems chapters on Caching + Messaging.
- Watch: Gaurav Sen on Kafka internals; Hello Interview YouTube on caching patterns.
- Mock: AI mock on **mockingly.ai** — Design a Distributed Cache. Free.

**Week 4 — Networking, APIs, consistency, consensus (skim)**
- Read: DDIA Ch. 9 (Consistency & Consensus) — read for intuition, not implementation.
- Read: Hello Interview "Key Technologies" pages on Kafka, Redis, ZooKeeper, Postgres, DynamoDB, Elasticsearch, S3.
- Memorize: "When to pick X" decision tree for each technology.
- Mock: AI mock on **Hello Interview Guided Practice** — Design Rate Limiter (the entry‑level classic).

**Phase 1 Milestone:** Can verbally explain consistent hashing, CAP, leader‑based replication, and back‑of‑the‑envelope a simple service in <5 min.

### Phase 2 — Patterns & Frameworks (Weeks 5–7, ~20 hrs)

**Week 5 — Adopt a delivery framework**
- Internalize one structured 7‑step framework. Recommended: **Hello Interview's "Delivery Framework"** (Requirements → Core Entities → API → High‑level design → Deep dive → Scale). Memorize the time budget: 5–7 min requirements, 5 min API/data model, 10 min high‑level, 15 min deep dive, 5 min scaling.
- Watch: 3 Hello Interview full mock interview videos on YouTube (free) — observe pacing.
- Drill: Re‑design the URL Shortener using the framework on a whiteboard, 35 min timed.

**Week 6 — Patterns library**
- Read: Educative Grokking the Modern System Design Interview pattern catalogue (or Designgurus.io equivalent).
- Make flashcards for: rate limiting algorithms, fan‑out strategies, idempotency, circuit breakers, retry/backoff, geospatial indexing, leader election.
- Practice problem: Design Twitter News Feed (use Hello Interview written breakdown).

**Week 7 — Modern flavors**
- Read: Alex Xu Vol 2 chapters on Ad Click Aggregation, Metrics Monitoring, Real‑time Gaming Leaderboard.
- Topic: microservices, observability, distributed tracing, service mesh — high‑level only.
- Mock: AI mock on Bugfree.ai — Design a Notification System, timed 45 min.

**Phase 2 Milestone:** You can stop a question mid‑sentence and explain which pattern applies (e.g., "this is a fan‑out‑on‑write read‑optimized feed problem with celebrity asymmetry").

### Phase 3 — Practice the Classic Problems (Weeks 8–12, ~35 hrs)

Solve **20 problems** (5 weeks × 4/week). For each problem: (a) read the Hello Interview / ByteByteGo write‑up first, (b) close the laptop, (c) re‑design from scratch on a whiteboard (Excalidraw recommended) for 35 min, (d) compare your solution to the reference and note misses, (e) once a week, solve a NEW problem in Bugfree.ai under timed AI conditions without reading first.

Recommended sequence:
- **Week 8:** URL Shortener, Pastebin, Rate Limiter, Distributed Cache.
- **Week 9:** WhatsApp/Messenger, Twitter News Feed, Instagram, Notification System.
- **Week 10:** Web Crawler, Search Autocomplete, YouTube/Netflix, Dropbox/Google Drive.
- **Week 11:** Uber, Yelp/Nearby Friends, Ticketmaster, Top‑K Trending.
- **Week 12:** Ad Click Aggregation, Metrics & Monitoring, Distributed Job Scheduler, Design ChatGPT.

**Phase 3 Milestone:** You have written designs for 20 problems and a "personal cheat sheet" capturing which DB / queue / cache / sharding key you use for each archetype.

### Phase 4 — Mock Interview Heavy (Weeks 13–16, ~25 hrs)

This phase compounds practice. Practice cadence: **3 AI mocks/week + 1 human mock every 2 weeks** + nightly review of feedback.

**Week 13 — Self‑calibration**
- 3 AI mocks (Hello Interview Guided Practice → Bugfree.ai → mockingly.ai) on three different problem types.
- 1 human mock on **Hello Interview** ($170–$250) with a coach from your **target** company. Be anonymous if uncomfortable.

**Week 14 — Stress test**
- Pick your weakest 2 problem categories from Phase 3; redo them on AI mocks.
- 1 human mock on **interviewing.io** (anonymous). Compare feedback styles.

**Week 15 — Company calibration**
- Use Hello Interview's "company‑tagged real questions" library to pick 3 *recent* real questions reported at your target company. Run them through AI mocks.
- Read recent interview experiences on Onsites.fyi, Blind, jointaro.com.
- 1 human mock with an ex‑interviewer from your target company on Hello Interview or IGotAnOffer.

**Week 16 — Polish & taper**
- Slow down to 1 AI mock every other day. Focus on communication: filler words, time management (use a real timer), narrating trade‑offs.
- Re‑read your "personal cheat sheet" daily.
- 48 hrs before real interview: light review only, no new problems.

**Phase 4 Milestone:** Across the last 3 mocks (mix of AI + human), at least 2 reviewers say you’d be a "lean hire" or better at L4/L5.

### Stretch (Weeks 17–24, optional, only if interview is ≥5 months away)
- DDIA Ch. 7–11 (Transactions, Distributed problems, Batch + Stream processing) for L5 ambition.
- MIT 6.5840 lectures + Lab 2 (Raft) — overkill for L4, big differentiator for L5+.
- Build a small distributed project (mini Kafka, mini key‑value store) — best signal in behavioral round and grows real intuition.

---

# PLAN 2 — CRASH COURSE (4 weeks, ~10–14 hrs/week)

**Assumptions:** You already have 3+ years of backend/full‑stack experience, are reasonably fluent with HTTP, SQL, and at least one cache/queue, and have an interview within ~30 days. Total budget: ~$200–$400.

### Buy on Day 0 (do not skip)
1. **Hello Interview Premium — 1 month** (~$35–$45). This is THE single most efficient resource for short‑timeline FAANG prep. Includes Guided Practice (AI mocks).
2. **ByteByteGo annual** (~$89 with 50% promo) OR borrow/buy *System Design Interview Vol 1* used (~$25). Vol 1 alone is sufficient for the crash course.
3. **Bugfree.ai monthly or lifetime promo** (~$25/mo or ~$99–$150 lifetime) — for daily AI reps.
4. **Optional one human mock** at the end of week 3: Hello Interview, $170–$250, with a coach at/above your target level.

You do **not** need DDIA, AlgoExpert, Educative, or DesignGurus for the 4‑week sprint.

### Week 1 — Foundations + Framework (≈12 hrs)

**Days 1–2: Speed‑read fundamentals**
- Hello Interview "System Design in a Hurry": read the entire Core Concepts + Key Technologies sections (free, ~3 hrs).
- Memorize the **Hello Interview Delivery Framework** (Requirements → Core Entities → API → High‑level → Deep Dive). Practice narrating it out loud against a wall.
- Memorize back‑of‑the‑envelope shortcuts: 1 day ≈ 100K seconds, 1MB ≈ 1M bytes, 1B requests/day ≈ ~12K QPS.

**Days 3–4: Building blocks crash**
- Read Alex Xu Vol 1, Ch. 1–6 (Scaling, BotE, Framework, Consistent Hashing, Key‑Value, Unique IDs).
- Watch ByteByteGo YouTube: SQL vs NoSQL, Caching strategies, Load Balancers (10 short videos total).

**Days 5–7: First problems**
- Day 5: read Hello Interview's URL Shortener breakdown → close laptop → redo it from scratch in 35 min (Excalidraw).
- Day 6: same loop with Rate Limiter.
- Day 7: AI mock on **Hello Interview Guided Practice** — Design Distributed Cache.

**Week 1 outcome:** Framework is automatic; you can rough‑sketch any storage‑heavy service in 35 min.

### Week 2 — Pattern fluency (≈14 hrs)

Goal: cover 4 problem archetypes with pattern recognition.

- **Day 8:** Twitter News Feed (fan‑out write vs read; celebrity problem). Read → redo → AI mock.
- **Day 9:** WhatsApp/Messenger (websockets, presence, message ordering). Read → redo → AI mock on Bugfree.ai.
- **Day 10:** Web Crawler (BFS, politeness, dedup, distributed work). Read → redo.
- **Day 11:** Search Autocomplete (trie, prefix cache, ranking). Read → redo.
- **Day 12:** Notification System. Read → redo → AI mock.
- **Day 13:** Watch 2 full Hello Interview YouTube mock recordings end‑to‑end and take notes on **what the interviewer probes**, not just the answer.
- **Day 14:** Buffer / catch‑up / review your "personal one‑pager" of trade‑off cliches (push vs pull, fan‑out write vs read, SQL vs NoSQL, sync vs async, strong vs eventual).

### Week 3 — More problems + first human mock (≈14 hrs)

- **Day 15:** Instagram (media + feed hybrid). Read → redo → AI mock.
- **Day 16:** Dropbox/Google Drive (chunking, dedup, sync). Read → redo.
- **Day 17:** YouTube/Netflix streaming (CDN, HLS/DASH, transcoding). Read → redo → AI mock on mockingly.ai.
- **Day 18:** Uber (geospatial, dispatch). Read → redo.
- **Day 19:** Ticketmaster *or* Top‑K (concurrency control or aggregation pipeline). Pick the one closer to your target company. Read → redo.
- **Day 20:** **Human mock** on Hello Interview ($170–$250) — choose a coach who interviews at your target company. Be anonymous if you want. **Take notes immediately afterward and do not start a new problem for 24 hours — let the feedback sink in.**
- **Day 21:** Rest day OR write up a 1‑page personal post‑mortem of the human mock and integrate gaps into your cheat sheet.

### Week 4 — Polish, AI Reps, Tapered (≈10 hrs)

**Days 22–24: AI mock blitz on weak areas**
- 1 AI mock per day (Hello Interview Guided Practice → Bugfree.ai → mockingly.ai). Pick problems that exposed weakness in the Day‑20 human mock.
- Re‑read your cheat sheet each morning.

**Days 25–26: Modern problems**
- Skim Alex Xu Vol 2 chapters on Metrics & Monitoring + Ad Click Aggregation (15 min each).
- Try **Design ChatGPT** on Hello Interview (one of the most‑asked 2025–2026 problems).

**Day 27: Final human or AI dress rehearsal**
- Either book a second Hello Interview mock OR run a full 60‑min self‑mock recorded on Zoom; review the recording.

**Day 28 (24–48 hrs before interview): Taper**
- No new content. Skim cheat sheet. Light walk. Sleep well.

---

## What to use AI mocks for vs. human mocks for

**AI mocks (cheap, fast, on demand) are best for:**
- Building reps and muscle memory for the Delivery Framework.
- Time‑pressure simulation (35‑min timer is critical — don't skip it).
- Trying the same problem multiple ways.
- Practicing narration of trade‑offs out loud.
- Catching obvious structural omissions (no API, no data model, no scaling story).

**Human mocks (expensive, scheduled, scarce) are best for:**
- Calibrating to a real interviewer's pushback style.
- Detecting subtle communication issues (jargon misuse, getting flustered under follow‑ups).
- Company‑specific signal (Meta loves trade‑offs; Amazon weaves in LPs; Google loves data modeling).
- The **last 1–2 weeks** before the real interview.

**Recommended AI mock cadence:**
- Crash course: 8–10 AI mocks total + 1 human.
- Deep mastery: 25–35 AI mocks total + 3–4 human mocks (last 4 weeks).

---

## Concrete "Day 1" shopping list

**Crash course shopper (~$200):**
1. Hello Interview Premium — 1 month — $35
2. Bugfree.ai — 1 month or lifetime promo — $25–$150
3. *System Design Interview Vol 1* (Alex Xu, used Amazon) — $25
4. One Hello Interview human mock — $170–$250

**Deep mastery shopper (~$400–$700):**
1. Hello Interview Premium — 1 year — ~$249 (or lifetime ~$549 if you'll use it for promotions later)
2. ByteByteGo — 1 year ~$89 (50% off) or lifetime ~$249–$499
3. DDIA — $40
4. Bugfree.ai — lifetime ~$99–$150
5. 2–3 Hello Interview / interviewing.io mocks — $400–$700 (use only in Phase 4)
6. Free: ByteByteGo + Hello Interview YouTube; system‑design‑primer GitHub; mockingly.ai free tier; Pramp on Exponent.

---

## FAANG‑specific tactical tips (for both plans)

- **Meta:** When given the choice, mid‑level candidates with backend experience usually pick *system design* over *product design*. Lean heavy on trade‑offs (consistency vs availability, latency vs throughput) and deep‑dive one component when the interviewer asks. Meta interviews are time‑pressured; do not overspend on requirements.
- **Google:** Spend more time on requirements clarification and data modeling. Google interviewers love when you reference real Google tech (Bigtable, Spanner, Colossus, Borg). Don't fake familiarity, but show awareness.
- **Amazon:** Weave in **Leadership Principles** (Customer Obsession, Ownership, Bias for Action) when justifying trade‑offs. The Bar Raiser may push you on a sub‑component for 15 minutes — be deep.
- **Apple:** Often product‑oriented; expect API/data model emphasis. Less obsession with planet‑scale numbers.
- **Netflix:** Senior bar; if interviewing here as L4, the bar is closer to L5 elsewhere. Practice streaming/media problems specifically.
- **Microsoft:** Highly variable by org. Ask the recruiter what flavor (Azure infra teams = real distributed systems; product teams = lighter scope).
- **At every company:** narrate your **time budget** out loud at the start ("I'll spend 5 min on requirements, 10 on high‑level, 15 on deep dive…"). Interviewers love this.

---

## Caveats

- **Pricing fluctuates.** All paid platforms run frequent 25–70% promotions, especially Black Friday, New Year, and back‑to‑school. The numbers above are list / typical promo prices observed in 2025–2026; verify on the vendor site before purchase. ByteByteGo, Educative, DesignGurus, Codemia, and Bugfree.ai run near‑perpetual sales.
- **Hello Interview deprecated their standalone "AI Mock Interviews" feature in 2025–2026 and replaced it with "Guided Practice"** (with AI feedback) inside Premium. The functionality is similar/better but if you read older reviews mentioning a separate AI Mock product, that's no longer accurate.
- **AI mock quality is real but bounded.** Even Hello Interview's Guided Practice and Bugfree.ai can't perfectly mimic an experienced human interviewer's adaptive probing, especially on senior/staff‑level depth. For L4/E4/SDE‑2, AI mocks are sufficient for the bulk of practice; for L5+ ambition, allocate more budget to human mocks.
- **L4 vs L5 expectations differ sharply** at Google in particular (Google L4s sometimes don't even get a system design round). Confirm with your recruiter what you'll be evaluated on. Do not over‑prepare to L6 depth and run out of time on L4 fundamentals — that's the most common failure mode for ambitious mid‑levels.
- **Source quality:** Some review sites cited above (Medium articles by "javinpaul," substack reviews) are partially affiliate‑marketing‑driven. Their *facts* (pricing, features) generally check out, but treat their recommendation hierarchy with skepticism. The most consistently FAANG‑calibrated content sources used in this plan are Hello Interview (founded by ex‑Meta staff engineers), Alex Xu's books/ByteByteGo, IGotAnOffer's interview guides, DDIA (Kleppmann), and the official MIT 6.5840 course.
- **The single most important variable is reps under time pressure with feedback.** Subscriptions are leverage; mocks are the work. If forced to pick one paid item from this list, pick **Hello Interview Premium** — it gives you the framework, the curated company‑tagged questions, and AI Guided Practice all in one. Add Bugfree.ai for sheer volume of timed AI reps if budget allows.

You can start tomorrow morning by buying Hello Interview Premium, opening "System Design in a Hurry," and doing the URL Shortener Guided Practice problem. Everything compounds from there.