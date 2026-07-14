---
title: "Formal Verification in Software — Mastery Plan"
category: "Formal Methods"
description: "An ~18–24 month mastery arc through both cultures of formal verification: design-level specification with TLA+/PlusCal (plus Quint, Alloy, P) and code-level proof — SAT/SMT foundations, model checking theory, auto-active verification with Dafny and the Rust ecosystem (Verus), then the long arc of interactive theorem proving in Rocq/Lean 4 through separation logic, concurrency, and Iris. Tuned for a math-PhD backend engineer: theory chapters are compressed while proof-engineering craft and specification judgment get the reps, with capstone projects, a reading canon, and currency warnings as of July 2026."
---

# Formal Verification in Software — Mastery Plan

**Profile assumptions:** senior backend engineer (Kotlin/Spring/Kafka/Aurora/EKS), PhD in pure mathematics, working full-time, 6–10 focused hrs/week. Timeline: **~18–24 months** for the core arc, with mastery-level work continuing beyond.

**What "mastery" means here (exit criteria):**

1. You can specify a real distributed design (protocol, saga, replication scheme) and model-check it, including liveness under fairness.
2. You can do auto-active verification (SMT-backed) of nontrivial programs — invariants, termination, framing — without hand-holding.
3. You can build machine-checked proofs in an interactive theorem prover, including separation-logic reasoning about heap/concurrency.
4. You have shipped at least one substantial public verified/specified artifact and can explain the soundness boundary of every tool you use.

Your math PhD changes the shape of this plan: the logic, semantics, and type theory will read like home turf, so theory chapters are compressed. The actual gap for you is **proof engineering craft** (tooling, automation hygiene, managing state explosion) and **specification judgment** (knowing *what* to specify). The plan overweights reps on real systems accordingly.

---

## The map before the path

Formal verification splits into two cultures, and mastery means fluency in both plus the shared substrate.

**Design-level ("lightweight") methods** specify the *design* and exhaustively check finite instances: TLA+/PlusCal, Quint, Alloy, P, SPIN. Days-to-weeks to first value. This is what AWS, MongoDB, Confluent-adjacent engineers, and Cosmos-ecosystem teams actually use on distributed protocols. Catches design bugs no amount of testing finds.

**Code-level methods** prove the *implementation*:

- *Auto-active verification*: you write contracts and invariants; an SMT solver discharges obligations. Dafny, Verus (Rust), Frama-C (C), SPARK (Ada), KeY/OpenJML (Java).
- *Foundational/interactive theorem proving (ITP)*: you construct proofs a small kernel checks. Rocq (formerly Coq), Lean 4, Isabelle/HOL. This is how seL4, CompCert, and Iris exist.

**Shared substrate:** propositional/first-order logic, SAT/SMT solving, temporal logics and automata, Hoare logic, separation logic, operational semantics, type theory.

**Why this field, now:** as AI generates ever more code, verification becomes the trust bottleneck — and simultaneously LLMs are collapsing the cost of writing proofs (Lean/Rocq/Dafny/Verus proof agents are an extremely active research area in 2025–2026). FV is one of the few deep skills that *compounds* with AI tooling rather than competing with it. It's also uniquely safe territory for AI assistance: the kernel/solver checks everything, so a hallucinated proof simply fails.

---

## Phase 0 — Orientation and logic refresh (2–3 weeks, ~15 h)

**Goal:** own the map; calibrate on what industry actually does.

- Read: *How Amazon Web Services Uses Formal Methods* (Newcombe et al., CACM 2015) — the canonical industrial TLA+ story.
- Read: Hillel Wayne, *Why Don't People Use Formal Methods?* — honest taxonomy of costs and payoffs.
- Read/watch: Byron Cook, *Formal Reasoning About the Security of Amazon Web Services* (CAV 2018 invited) — the automated-reasoning-at-scale view (Zelkova for IAM policies, Tiros for network reachability).
- Refresh: Huth & Ryan, *Logic in Computer Science* — skim the propositional/FO chapters (trivial for you); actually study the LTL/CTL chapters since temporal logic in CS clothing may be new.

**Deliverable:** a one-page personal map of the field and 2–3 candidate capstone ideas (see Phase 8).

---

## Phase 1 — TLA+ and design-level specification (10–12 weeks, ~80 h)

Start here, not with theorem provers. This is the fastest path to value, and it plugs directly into your Kafka/EDA/outbox work. TLA+ is the industry standard for distributed-system design verification.

**Learning spine, in order:**

1. **learntla.com** (Hillel Wayne, free) — pragmatic on-ramp via PlusCal.
2. ***Practical TLA+*** (Wayne) — work the exercises.
3. **Lamport's *Specifying Systems*** (free PDF), Parts I–II, plus selected episodes of his **TLA+ Video Course** — this is where the semantics (behaviors as infinite state sequences, stuttering, fairness, refinement) actually clicks. Your math background makes this the fun part.

**Tooling to internalize:**

- **TLC** (explicit-state checker): BFS state exploration, invariants vs. temporal properties, symmetry sets, state constraints, and how to read a counterexample trace. Understanding *why* TLC blows up is half the craft.
- **Apalache** (SMT-backed symbolic checker; type annotations required): bounded model checking and inductive-invariant checking. Note: since Informal Systems ended funding in 2024 it's community-maintained by its original authors (Konnov et al.) — still active, with a JSON-RPC server enabling programmatic/interactive symbolic execution.
- **Quint**: engineer-friendly modern syntax over TLA semantics, using Apalache as backend. Learn to read both syntaxes; write in whichever sticks.
- Editor: the VS Code TLA+ extension is the de facto IDE now.

**Core reps (do these, don't just read):**

- Classics: DieHard, Lamport's `TCommit`/`TwoPhase` (two-phase commit), a mutex, Practical TLA+'s bounded-queue and threading exercises.
- Read (not write) the **Paxos** spec; study **Ongaro's Raft TLA+ spec** line by line.
- Your-domain reps: model an at-least-once consumer with idempotent dedup; then model your **outbox + Debezium/CDC pipeline** — invariant "every committed order event is eventually published, and consumed effects happen exactly once under crash/retry"; watch TLC find the bug when you remove fencing or reorder commit steps.
- Study **Jack Vanlightly's TLA+ analyses of the Kafka replication protocol** and the TLA+ specs living in the Kafka repo (replication/KRaft). This is the single best bridge from your existing Kafka depth into FV.

**Optional side quests (1–2 weeks each, can defer):**

- **Alloy 6** (Jackson, *Software Abstractions*): relational modeling with temporal operators — excellent for data-model/permission invariants, small-scope hypothesis thinking.
- **P language** (open source; used by AWS teams for S3/DynamoDB work): event-driven state machines — conceptually the closest formal tool to your EDA day job.

**Milestone:** publish (blog, Korean or English) a spec of your Baemin-style delivery lifecycle: ≥2 nontrivial safety invariants, 1 liveness property under fairness, and one honest TLC-found counterexample story.

**Reality check to carry forward:** TLC verifies your *model*, not your code, at *finite* scopes. The gap between model and implementation is addressed in Phase 8 (conformance/trace validation).

---

## Phase 2 — SAT/SMT foundations (6–8 weeks, ~50 h)

Everything auto-active (Apalache, Dafny, Verus, Kani, CBMC) stands on this. Understanding solver behavior is what separates people who fight the tools from people who steer them.

- **Spine:** Kroening & Strichman, *Decision Procedures* (2nd ed.). Alternative/supplement: Bradley & Manna, *The Calculus of Computation*.
- **Build a CDCL SAT solver** (Kotlin is fine; Rust if you want Phase 5 prep): unit propagation, two-watched literals, clause learning, VSIDS, restarts. A deeply satisfying 1–2 weekend project for you.
- **Z3 hands-on** (Python bindings): EUF, linear arithmetic, arrays, bitvectors, quantifiers and their perils (triggers/instantiation — this is *the* thing that will bite you in Dafny/Verus later). Encode puzzles, then real things: schedule feasibility, config-constraint checking, equivalence of two small functions.
- Understand **DPLL(T)** architecture and skim e-graphs/equality saturation (the `egg` line of work) as a fun aside.

**Milestone:** written notes titled "What SMT can and cannot do for me" — you will reuse this intuition weekly for the rest of the plan.

---

## Phase 3 — Model checking theory (6–8 weeks, ~50 h; interleaves well with Phase 2)

The theory behind what TLC/Apalache/SPIN/Lincheck are each doing.

- **Spine:** Baier & Katoen, *Principles of Model Checking* — transition systems, LTL/CTL/CTL\*, Büchi automata and LTL→automata translation, fairness, symbolic checking with BDDs, partial-order reduction, abstraction/CEGAR. It's dense; you have the math — select chapters rather than cover-to-cover. (Clarke et al., *Model Checking* 2e is the alternative.)
- **Hands-on:** SPIN/Promela (Holzmann) on one or two protocols; **CBMC** on small C functions; **Java Pathfinder** on a deliberately racy Java class (a fun JVM-native detour); revisit **Lincheck** and recognize it as bounded exploration of linearizability on the JVM — you already own this tool from your concurrency arc.

**Milestone:** a write-up precisely contrasting what TLC, Apalache, SPIN, CBMC, and Lincheck each explore and guarantee.

---

## Phase 4 — Auto-active program verification with Dafny (10–12 weeks, ~80 h)

Dafny is the best pedagogy in existence for code-level verification, and it's industrially real (AWS ships Dafny-verified crypto libraries).

- **Spine:** Rustan Leino, ***Program Proofs*** (MIT Press, 2023). Work most exercises — this book *is* the course.
- **Skills to acquire:** pre/postconditions, loop invariants, `decreases` termination measures, framing (`modifies`/`reads`), ghost state, lemmas and induction, `calc` proofs, abstraction via modules/traits, and — critically — *debugging verification failures* (timeouts, brittle quantifier instantiation).
- **Projects:** verified binary search, sorting, ring buffer; then something from your world — a verified LRU cache, or a token-bucket rate limiter with a proven no-overspend invariant. Compile one to Java and property-test the verified/unverified boundary.
- **Optional 1-week detour:** JML with **OpenJML** or **KeY** to see Java-native contracts, with the honest caveat that the tooling lags modern Java. Dafny remains the better learning vehicle.

**Milestone:** a public repo of one verified data structure with a README explaining every invariant and why each is necessary (delete one, show the failure).

---

## Phase 5 (elective, but hot) — Rust-ecosystem verification (6–10 weeks, ~60 h)

This is where industrial code-level FV momentum is concentrated right now, and it doubles as Rust upskilling relevant to your HFT curiosity. Skip or defer if you'd rather reach ITP sooner; concepts from Phase 4 transfer directly.

- **Prerequisite:** working Rust. If needed, fold in a 3–4 week Rust ramp (the Verus guide itself assumes basic Rust).
- **Kani** (CBMC-based bounded checking for Rust): low ceremony, great first taste; try challenges from the AWS-initiated **Verify Rust Std Lib** effort.
- **Verus** (SMT-based full functional verification): specs and proofs written *in Rust syntax*; Rust's ownership/borrowing does the aliasing reasoning that separation logic does manually — a beautiful convergence you'll appreciate doubly after Phase 7. Verus is under very active development (SOSP'24 systems paper; PLDI 2026 published *VerusBelt*, its semantic soundness foundation) — expect syntax churn.
- **Study:** **Anvil** (OSDI 2024) — *verified Kubernetes controllers in Verus*, proving liveness ("the controller eventually reconciles"). Given your EKS migration, this paper is squarely your world; read it and poke the repo.

**Milestone:** verify a small Rust component end-to-end in Verus (bounded queue, retry/backoff state machine), or land one Verify-Rust-Std contract.

---

## Phase 6 — Interactive theorem proving (16–24 weeks, ~150 h) — the long arc

**Prover choice framework:**

- **Rocq** (renamed from Coq in 2025; Rocq Prover 9.x): the canonical software-verification pedagogy via *Software Foundations*; home of Iris, CompCert, VST. → **Default spine.**
- **Lean 4**: strongest momentum and tooling ergonomics; mathlib (250k+ theorems) will exert gravitational pull on your math brain; growing industrial software use (AWS's Cedar authorization engine and SampCert differential-privacy library are formalized in Lean); the entire AI-theorem-proving wave targets Lean. PL-verification pedagogy is thinner than SF but improving (*Theorem Proving in Lean 4*, *Functional Programming in Lean*, *The Hitchhiker's Guide to Logical Verification*).
- **Isabelle/HOL**: *Concrete Semantics* (Nipkow & Klein, free) is superb; seL4 and the AFP live here; sledgehammer automation is unmatched. Smaller new-project ecosystem.

**Recommended path:** *Software Foundations* **Vol 1 (Logical Foundations)** → **Vol 2 (Programming Language Foundations)** in Rocq — inductive definitions, tactics, operational semantics, STLC with progress/preservation, and an embedded Hoare logic. Do the exercises honestly; this is where proof-engineering muscle is built. Then reassess: continue in Rocq toward Phase 7 (Iris), or hop to Lean for community/AI-tooling — the concepts transfer ~90%. If the math itch demands satisfaction, a parallel mathlib side-quest in Lean is a legitimate dual-track for you.

**Parallel theory:** Pierce, *Types and Programming Languages* (λ-calculus, STLC, subtyping, System F) — will read like a light novel given your background but fills the PL-theory vocabulary. Advanced follow-ups: Chlipala's *FRAP* (Formal Reasoning About Programs) and *CPDT* (proof automation craft).

**Milestones:** complete LF + PLF exercise sets; formalize a small typed interpreter end-to-end (type safety + evaluator correctness); if on the Lean track, one small mathlib-adjacent PR.

---

## Phase 7 — Separation logic, concurrency, Iris (12–16 weeks, ~120 h; research-grade)

The mastery differentiator: machine-checked reasoning about heap-manipulating, concurrent code.

- **Spine:** *Software Foundations Vol 6: Separation Logic Foundations* (Charguéraud). Context: O'Hearn's *Separation Logic* retrospective (CACM 2019).
- **Iris** (higher-order concurrent separation logic, in Rocq): the Iris lecture notes (Birkedal & Bizjak) plus *Iris from the Ground Up* (JFP 2018). Verify a spin lock, then a concurrent counter/queue against a logically-atomic spec.
- **Deep cut that closes the loop:** **RustBelt** (POPL 2018) — Iris used to prove Rust's ownership discipline sound. After Phase 5, this paper explains *why* Verus gets separation logic "for free."
- **Seoul-local advantage:** SNU's Software Foundations Lab (Chung-Kil Hur) and KAIST's Concurrency & Parallelism group (Jeehoon Kang) are world-class in exactly this area (Iris, relaxed memory, verified compilation). Their public seminars/colloquia are a realistic in-person community for you — worth checking current schedules, along with SIGPL Korea's summer/winter schools.

**Milestone:** one machine-checked correctness proof of a concurrent data structure.

---

## Phase 8 — Capstones and the frontier (ongoing)

Pick **at least one** substantial, public capstone:

1. **Spec-to-code conformance (recommended — rare and portfolio-grade):** take your Phase 1 saga/outbox spec, instrument your Kotlin implementation to emit traces, and validate traces against the spec (trace validation à la MongoDB's *eXtreme Modelling in Practice*, VLDB 2020, and Microsoft CCF's TLA+ practice; Apalache's newer JSON-RPC interface supports interactive symbolic testing against live implementations).
2. **IronFleet-lite:** a verified two-phase commit or Raft core in Dafny or Verus; study IronFleet (SOSP 2015) and Verdi (PLDI 2015) as the reference points.
3. **Lightweight FV at work:** replicate the S3 ShardStore recipe (*Using Lightweight Formal Methods to Validate a Key-Value Storage Node in Amazon S3*, SOSP 2021) on one of your services — a reference model plus property-based testing (jqwik/Kotest) plus Lincheck, with an explicit coverage argument.
4. **Contribute upstream:** Kafka's KRaft/replication TLA+ specs, TLA+ community modules, Quint/Apalache issues, Verify-Rust-Std, or mathlib.

**Frontier to track (and exploit):** LLM-assisted proving is moving extremely fast — proof-repair and "vericoding" pipelines for Verus/Dafny, Lean proof agents, and agentic setups where general models drive provers through MCP tools. As a heavy Claude Code user, use AI to draft specs and proof skeletons *from day one of Phase 4 onward* — this is the one domain where that's epistemically safe, because the checker is the final judge. But do Phases 1–3 exercises by hand; the intuition is the asset.

---

## Schedule overview

| Phase | Focus | Duration | Hours |
|---|---|---|---|
| 0 | Orientation, logic refresh | 2–3 wks | ~15 |
| 1 | TLA+ / Quint / design-level | 10–12 wks | ~80 |
| 2 | SAT/SMT foundations | 6–8 wks | ~50 |
| 3 | Model checking theory | 6–8 wks | ~50 |
| 4 | Dafny auto-active verification | 10–12 wks | ~80 |
| 5 | Rust: Kani + Verus (elective) | 6–10 wks | ~60 |
| 6 | ITP: Software Foundations (Rocq), Lean option | 16–24 wks | ~150 |
| 7 | Separation logic + Iris | 12–16 wks | ~120 |
| 8 | Capstone + frontier | ongoing | — |

**Cut-down variants:**

- **3 months ("useful at work immediately"):** Phases 0–1 only. You'll already be ahead of ~99% of backend engineers.
- **6–8 months ("credible generalist"):** add Phase 2 and Phase 4 (skim Phase 3).
- **18–24 months ("mastery arc"):** everything above; Phase 5 optional, Phase 7 is the differentiator.

---

## The canon

**Books:** *Specifying Systems* (Lamport, free) · *Practical TLA+* (Wayne) · *Software Abstractions* (Jackson) · *Decision Procedures* (Kroening & Strichman) · *Principles of Model Checking* (Baier & Katoen) · *Program Proofs* (Leino) · *Software Foundations* Vols 1, 2, 6 (free) · *TAPL* (Pierce) · *FRAP* + *CPDT* (Chlipala, free) · *Concrete Semantics* (Nipkow & Klein, free, if Isabelle) · *Theorem Proving in Lean 4* + *Hitchhiker's Guide to Logical Verification* (free, if Lean).

**Papers (reading order roughly matches phases):** AWS formal methods (CACM 2015) · Cook CAV 2018 · seL4 (SOSP 2009) · CompCert (Leroy, CACM 2009) · IronFleet (SOSP 2015) · Verdi (PLDI 2015) · Iris from the Ground Up (JFP 2018) · RustBelt (POPL 2018) · O'Hearn separation logic (CACM 2019) · eXtreme Modelling (VLDB 2020) · S3 ShardStore (SOSP 2021) · Verus (OOPSLA 2023 + SOSP 2024) · Anvil (OSDI 2024) · Cedar (2024).

**People/blogs worth following:** Hillel Wayne (*Computer Things* newsletter), Jack Vanlightly (Kafka/protocol TLA+ analyses), Igor Konnov (*Protocols Made Fun* — Apalache/Quint/conformance testing), Lamport's site, Leino's Dafny material, the Iris project pages.

**Communities:** TLA+ Foundation forum + annual TLA+ Conference · Lean Zulip (very active) · Rocq Discourse/Zulip · Isabelle AFP · CAV/POPL/PLDI/ITP/OSDI-SOSP proceedings · Seoul-local: SNU SF Lab and KAIST CP Lab seminars, SIGPL Korea schools.

---

## Currency warnings (as of July 2026)

- **Rocq**: the Coq→Rocq rename landed with Rocq Prover 9.0 (March 2025); older tutorials/StackOverflow answers say "Coq" — same system, migrating naming. Software Foundations has been updated.
- **Lean 4** releases monthly; pin toolchains per-project (`lean-toolchain` + elan). mathlib moves fast.
- **Verus** is young and evolving quickly (2026 releases are frequent); expect guide/syntax drift — always work from the current tutorial, not blog posts older than ~a year.
- **Quint/Apalache**: community-maintained since Informal Systems wound down funding (2024); healthy but check release cadence before betting a work project on them; TLC remains the boring, stable default.
- **LLM+FV tooling** (proof agents, MCP prover integrations, vericoding) is the fastest-moving corner of the whole field — anything written about it more than six months ago is stale.

## How this compounds with your existing arcs

TLA+/Quint formalizes the EDA, outbox, and Kafka replication material you already know deeply — you'll be *checking* designs you previously reasoned about informally. Lincheck and jqwik slot into Phase 3/8 as tools you already own. Anvil connects verification to your EKS migration. The math PhD makes Phases 2, 3, 6, 7 dramatically cheaper for you than for the median engineer — the plan's real bet is converting that theoretical advantage into tooling fluency and public artifacts.
