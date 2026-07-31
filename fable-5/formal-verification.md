---
title: "Formal Verification in Software: A Mastery Plan"
category: "Formal Methods"
description: "An 18-24 month mastery arc through both cultures of formal verification: design-level specification with TLA+/PlusCal (plus Quint, Alloy, P), and code-level proof, covering SAT/SMT foundations, model checking theory, auto-active verification with Dafny and the Rust ecosystem (Verus), then the long arc of interactive theorem proving in Rocq/Lean 4 through separation logic, concurrency, and Iris. It is tuned for a math-PhD backend engineer, so theory chapters are compressed while proof-engineering craft and specification judgment get the reps, with capstone projects, a reading canon, and currency warnings as of July 2026."
---

# Formal Verification in Software: A Mastery Plan

**Profile assumptions:** a senior backend engineer (Kotlin, Spring, Kafka, Aurora, EKS) with a PhD in pure mathematics, working full-time, at 6-10 focused hrs/week. The timeline is roughly 18-24 months for the core arc, with mastery-level work continuing beyond that.

**What "mastery" means here (the exit criteria):**

1. You can specify a real distributed design (a protocol, saga, or replication scheme) and model-check it, including liveness under fairness.
2. You can do auto-active verification (SMT-backed) of nontrivial programs, covering invariants, termination, and framing, without hand-holding.
3. You can build machine-checked proofs in an interactive theorem prover, including separation-logic reasoning about the heap and concurrency.
4. You have shipped at least one substantial public verified or specified artifact, and you can explain the soundness boundary of every tool you use.

Your math PhD changes the shape of this plan. The logic, semantics, and type theory will read like home turf, so theory chapters are compressed. The actual gap for you is proof engineering craft (tooling, automation hygiene, managing state explosion) and specification judgment (knowing what to specify). The plan overweights reps on real systems accordingly.

---

## The map before the path

Formal verification splits into two cultures, and mastery means fluency in both plus the shared substrate.

**Design-level, or "lightweight," methods** specify the design and exhaustively check finite instances: TLA+/PlusCal, Quint, Alloy, P, SPIN. They take days to weeks to first value. This is what AWS, MongoDB, Confluent-adjacent engineers, and Cosmos-ecosystem teams actually use on distributed protocols, and it catches design bugs no amount of testing finds.

**Code-level methods** prove the implementation:

- *Auto-active verification*: you write contracts and invariants, and an SMT solver discharges the obligations. Dafny, Verus (Rust), Frama-C (C), SPARK (Ada), KeY and OpenJML (Java).
- *Foundational or interactive theorem proving (ITP)*: you construct proofs that a small kernel checks. Rocq (formerly Coq), Lean 4, Isabelle/HOL. This is how seL4, CompCert, and Iris exist.

**Shared substrate:** propositional and first-order logic, SAT/SMT solving, temporal logics and automata, Hoare logic, separation logic, operational semantics, and type theory.

**Why this field, now:** as AI generates ever more code, verification becomes the trust bottleneck, and at the same time LLMs are collapsing the cost of writing proofs, with Lean, Rocq, Dafny, and Verus proof agents an extremely active research area in 2025 and 2026. FV is one of the few deep skills that compounds with AI tooling rather than competing with it. It's also uniquely safe territory for AI assistance, because the kernel or solver checks everything, so a hallucinated proof simply fails.

---

## Phase 0: orientation and logic refresh (2-3 weeks, ~15 h)

**Goal:** own the map, and calibrate on what industry actually does.

- Read *How Amazon Web Services Uses Formal Methods* (Newcombe et al., CACM 2015), the canonical industrial TLA+ story.
- Read Hillel Wayne's *Why Don't People Use Formal Methods?*, an honest taxonomy of costs and payoffs.
- Read or watch Byron Cook's *Formal Reasoning About the Security of Amazon Web Services* (a CAV 2018 invited talk), for the automated-reasoning-at-scale view, covering Zelkova for IAM policies and Tiros for network reachability.
- Refresh with Huth and Ryan's *Logic in Computer Science*. Skim the propositional and first-order chapters, which are trivial for you, and actually study the LTL and CTL chapters, since temporal logic in CS clothing may be new.

**Deliverable:** a one-page personal map of the field, plus two or three candidate capstone ideas (see Phase 8).

---

## Phase 1: TLA+ and design-level specification (10-12 weeks, ~80 h)

Start here rather than with theorem provers. This is the fastest path to value, and it plugs directly into your Kafka, EDA, and outbox work. TLA+ is the industry standard for distributed-system design verification.

**Learning spine, in order:**

1. learntla.com (Hillel Wayne, free), a pragmatic on-ramp via PlusCal.
2. *Practical TLA+* (Wayne). Work the exercises.
3. Lamport's *Specifying Systems* (free PDF), Parts I and II, plus selected episodes of his TLA+ Video Course. This is where the semantics (behaviors as infinite state sequences, stuttering, fairness, refinement) actually clicks, and your math background makes it the fun part.

**Tooling to internalize:**

- TLC, the explicit-state checker: BFS state exploration, invariants against temporal properties, symmetry sets, state constraints, and how to read a counterexample trace. Understanding why TLC blows up is half the craft.
- Apalache, the SMT-backed symbolic checker, which requires type annotations: bounded model checking and inductive-invariant checking. Note that since Informal Systems ended funding in 2024, it is community-maintained by its original authors (Konnov et al.). It is still active, with a JSON-RPC server enabling programmatic and interactive symbolic execution.
- Quint, an engineer-friendly modern syntax over TLA semantics that uses Apalache as its backend. Learn to read both syntaxes, and write in whichever sticks.
- Editor: the VS Code TLA+ extension is the de facto IDE now.

**Core reps (do these, don't just read):**

- The classics: DieHard, Lamport's `TCommit` and `TwoPhase` (two-phase commit), a mutex, and the bounded-queue and threading exercises from *Practical TLA+*.
- Read, rather than write, the Paxos spec, and study Ongaro's Raft TLA+ spec line by line.
- Reps from your own domain: model an at-least-once consumer with idempotent dedup, then model your outbox plus Debezium and CDC pipeline, with the invariant "every committed order event is eventually published, and consumed effects happen exactly once under crash and retry." Watch TLC find the bug when you remove fencing or reorder commit steps.
- Study Jack Vanlightly's TLA+ analyses of the Kafka replication protocol, and the TLA+ specs living in the Kafka repo for replication and KRaft. This is the single best bridge from your existing Kafka depth into FV.

**Optional side quests (1-2 weeks each, and deferrable):**

- Alloy 6 (Jackson, *Software Abstractions*): relational modeling with temporal operators, excellent for data-model and permission invariants and for small-scope hypothesis thinking.
- The P language (open source, used by AWS teams for S3 and DynamoDB work): event-driven state machines, conceptually the closest formal tool to your EDA day job.

**Milestone:** publish, on a blog in Korean or English, a spec of your Baemin-style delivery lifecycle with at least two nontrivial safety invariants, one liveness property under fairness, and one honest TLC-found counterexample story.

**A reality check to carry forward:** TLC verifies your model rather than your code, and only at finite scopes. The gap between model and implementation is addressed in Phase 8, on conformance and trace validation.

---

## Phase 2: SAT and SMT foundations (6-8 weeks, ~50 h)

Everything auto-active (Apalache, Dafny, Verus, Kani, CBMC) stands on this. Understanding solver behavior is what separates people who fight the tools from people who steer them.

- Spine: Kroening and Strichman, *Decision Procedures* (2nd ed.). An alternative or supplement is Bradley and Manna's *The Calculus of Computation*.
- Build a CDCL SAT solver (Kotlin is fine, or Rust if you want Phase 5 prep): unit propagation, two-watched literals, clause learning, VSIDS, restarts. This is a deeply satisfying one-or-two-weekend project for you.
- Z3 hands-on, via the Python bindings: EUF, linear arithmetic, arrays, bitvectors, and quantifiers with their perils (triggers and instantiation, which is the thing that will bite you in Dafny and Verus later). Encode puzzles, then real things: schedule feasibility, config-constraint checking, and equivalence of two small functions.
- Understand the DPLL(T) architecture, and skim e-graphs and equality saturation (the `egg` line of work) as a fun aside.

**Milestone:** written notes titled "What SMT can and cannot do for me." You will reuse this intuition weekly for the rest of the plan.

---

## Phase 3: model checking theory (6-8 weeks, ~50 h, and it interleaves well with Phase 2)

This is the theory behind what TLC, Apalache, SPIN, and Lincheck are each doing.

- Spine: Baier and Katoen, *Principles of Model Checking*, covering transition systems, LTL, CTL, and CTL\*, Büchi automata and the LTL-to-automata translation, fairness, symbolic checking with BDDs, partial-order reduction, and abstraction with CEGAR. It's dense, but you have the math, so select chapters rather than reading cover to cover. Clarke et al., *Model Checking* 2e, is the alternative.
- Hands-on: SPIN and Promela (Holzmann) on one or two protocols; CBMC on small C functions; Java Pathfinder on a deliberately racy Java class, which is a fun JVM-native detour; and a revisit of Lincheck, recognizing it as bounded exploration of linearizability on the JVM, a tool you already own from your concurrency arc.

**Milestone:** a write-up precisely contrasting what TLC, Apalache, SPIN, CBMC, and Lincheck each explore and guarantee.

---

## Phase 4: auto-active program verification with Dafny (10-12 weeks, ~80 h)

Dafny is the best pedagogy in existence for code-level verification, and it's industrially real, since AWS ships Dafny-verified crypto libraries.

- Spine: Rustan Leino, *Program Proofs* (MIT Press, 2023). Work most of the exercises, because this book is the course.
- Skills to acquire: pre- and postconditions, loop invariants, `decreases` termination measures, framing (`modifies` and `reads`), ghost state, lemmas and induction, `calc` proofs, abstraction via modules and traits, and, critically, debugging verification failures such as timeouts and brittle quantifier instantiation.
- Projects: a verified binary search, sorting, and ring buffer, then something from your world, such as a verified LRU cache or a token-bucket rate limiter with a proven no-overspend invariant. Compile one to Java and property-test the verified and unverified boundary.
- An optional one-week detour: JML with OpenJML or KeY, to see Java-native contracts, with the honest caveat that the tooling lags modern Java. Dafny remains the better learning vehicle.

**Milestone:** a public repo of one verified data structure, with a README explaining every invariant and why each is necessary. Delete one and show the failure.

---

## Phase 5 (elective, but hot): Rust-ecosystem verification (6-10 weeks, ~60 h)

This is where industrial code-level FV momentum is concentrated right now, and it doubles as Rust upskilling relevant to your HFT curiosity. Skip or defer it if you'd rather reach ITP sooner, since the concepts from Phase 4 transfer directly.

- Prerequisite: working Rust. If needed, fold in a 3-4 week Rust ramp, since the Verus guide itself assumes basic Rust.
- Kani, CBMC-based bounded checking for Rust: low ceremony and a great first taste. Try challenges from the AWS-initiated Verify Rust Std Lib effort.
- Verus, SMT-based full functional verification, where specs and proofs are written in Rust syntax. Rust's ownership and borrowing do the aliasing reasoning that separation logic does manually, a beautiful convergence you'll appreciate doubly after Phase 7. Verus is under very active development (a SOSP'24 systems paper, and PLDI 2026 published *VerusBelt*, its semantic soundness foundation), so expect syntax churn.
- Study Anvil (OSDI 2024), which covers verified Kubernetes controllers in Verus and proves liveness, that "the controller eventually reconciles." Given your EKS migration, this paper is squarely your world, so read it and poke the repo.

**Milestone:** verify a small Rust component end to end in Verus (a bounded queue, or a retry and backoff state machine), or land one Verify-Rust-Std contract.

---

## Phase 6: interactive theorem proving (16-24 weeks, ~150 h), the long arc

**A framework for choosing a prover:**

- Rocq (renamed from Coq in 2025, currently Rocq Prover 9.x): the canonical software-verification pedagogy via *Software Foundations*, and the home of Iris, CompCert, and VST. This is the default spine.
- Lean 4: the strongest momentum and tooling ergonomics. mathlib, with over 250k theorems, will exert gravitational pull on your math brain, and industrial software use is growing (AWS's Cedar authorization engine and its SampCert differential-privacy library are formalized in Lean). The entire AI-theorem-proving wave targets Lean. PL-verification pedagogy is thinner than Software Foundations but improving, via *Theorem Proving in Lean 4*, *Functional Programming in Lean*, and *The Hitchhiker's Guide to Logical Verification*.
- Isabelle/HOL: *Concrete Semantics* (Nipkow and Klein, free) is superb, seL4 and the AFP live here, and sledgehammer automation is unmatched. The new-project ecosystem is smaller.

**Recommended path:** *Software Foundations* Vol 1 (Logical Foundations), then Vol 2 (Programming Language Foundations), in Rocq. These cover inductive definitions, tactics, operational semantics, STLC with progress and preservation, and an embedded Hoare logic. Do the exercises honestly, because this is where proof-engineering muscle is built. Then reassess: continue in Rocq toward Phase 7 and Iris, or hop to Lean for the community and AI tooling, since the concepts transfer around 90%. If the math itch demands satisfaction, a parallel mathlib side-quest in Lean is a legitimate dual track for you.

**Parallel theory:** Pierce's *Types and Programming Languages* (λ-calculus, STLC, subtyping, System F) will read like a light novel given your background, but it fills in the PL-theory vocabulary. Advanced follow-ups: Chlipala's *FRAP* (Formal Reasoning About Programs) and *CPDT*, on proof automation craft.

**Milestones:** complete the LF and PLF exercise sets, formalize a small typed interpreter end to end (type safety plus evaluator correctness), and, if you are on the Lean track, land one small mathlib-adjacent PR.

---

## Phase 7: separation logic, concurrency, Iris (12-16 weeks, ~120 h, research-grade)

This is the mastery differentiator: machine-checked reasoning about heap-manipulating, concurrent code.

- Spine: *Software Foundations Vol 6: Separation Logic Foundations* (Charguéraud). For context, read O'Hearn's *Separation Logic* retrospective (CACM 2019).
- Iris, higher-order concurrent separation logic in Rocq: the Iris lecture notes (Birkedal and Bizjak) plus *Iris from the Ground Up* (JFP 2018). Verify a spin lock, then a concurrent counter or queue against a logically-atomic spec.
- A deep cut that closes the loop: RustBelt (POPL 2018), which uses Iris to prove Rust's ownership discipline sound. After Phase 5, this paper explains why Verus gets separation logic "for free."
- A Seoul-local advantage: SNU's Software Foundations Lab (Chung-Kil Hur) and KAIST's Concurrency & Parallelism group (Jeehoon Kang) are world-class in exactly this area, covering Iris, relaxed memory, and verified compilation. Their public seminars and colloquia are a realistic in-person community for you, so check current schedules, along with SIGPL Korea's summer and winter schools.

**Milestone:** one machine-checked correctness proof of a concurrent data structure.

---

## Phase 8: capstones and the frontier (ongoing)

Pick at least one substantial, public capstone:

1. Spec-to-code conformance, which is recommended because it is rare and portfolio-grade: take your Phase 1 saga or outbox spec, instrument your Kotlin implementation to emit traces, and validate those traces against the spec. This is trace validation in the style of MongoDB's *eXtreme Modelling in Practice* (VLDB 2020) and Microsoft CCF's TLA+ practice, and Apalache's newer JSON-RPC interface supports interactive symbolic testing against live implementations.
2. IronFleet-lite: a verified two-phase commit or Raft core in Dafny or Verus. Study IronFleet (SOSP 2015) and Verdi (PLDI 2015) as the reference points.
3. Lightweight FV at work: replicate the S3 ShardStore recipe (*Using Lightweight Formal Methods to Validate a Key-Value Storage Node in Amazon S3*, SOSP 2021) on one of your services, with a reference model plus property-based testing (jqwik or Kotest) plus Lincheck, and an explicit coverage argument.
4. Contribute upstream: Kafka's KRaft and replication TLA+ specs, the TLA+ community modules, Quint and Apalache issues, Verify-Rust-Std, or mathlib.

**The frontier to track, and exploit:** LLM-assisted proving is moving extremely fast, including proof-repair and "vericoding" pipelines for Verus and Dafny, Lean proof agents, and agentic setups where general models drive provers through MCP tools. As a heavy Claude Code user, use AI to draft specs and proof skeletons from day one of Phase 4 onward. This is the one domain where that's epistemically safe, because the checker is the final judge. But do the Phase 1 through 3 exercises by hand, because the intuition is the asset.

---

## Schedule overview

| Phase | Focus | Duration | Hours |
|---|---|---|---|
| 0 | Orientation, logic refresh | 2-3 wks | ~15 |
| 1 | TLA+ / Quint / design-level | 10-12 wks | ~80 |
| 2 | SAT/SMT foundations | 6-8 wks | ~50 |
| 3 | Model checking theory | 6-8 wks | ~50 |
| 4 | Dafny auto-active verification | 10-12 wks | ~80 |
| 5 | Rust: Kani + Verus (elective) | 6-10 wks | ~60 |
| 6 | ITP: Software Foundations (Rocq), Lean option | 16-24 wks | ~150 |
| 7 | Separation logic + Iris | 12-16 wks | ~120 |
| 8 | Capstone + frontier | ongoing | n/a |

**Cut-down variants:**

- 3 months, "useful at work immediately": Phases 0 and 1 only. You'll already be ahead of roughly 99% of backend engineers.
- 6-8 months, "credible generalist": add Phase 2 and Phase 4, and skim Phase 3.
- 18-24 months, "mastery arc": everything above, with Phase 5 optional and Phase 7 as the differentiator.

---

## The canon

**Books:** *Specifying Systems* (Lamport, free), *Practical TLA+* (Wayne), *Software Abstractions* (Jackson), *Decision Procedures* (Kroening and Strichman), *Principles of Model Checking* (Baier and Katoen), *Program Proofs* (Leino), *Software Foundations* Vols 1, 2, and 6 (free), *TAPL* (Pierce), *FRAP* and *CPDT* (Chlipala, free), *Concrete Semantics* (Nipkow and Klein, free, if you go with Isabelle), and *Theorem Proving in Lean 4* plus the *Hitchhiker's Guide to Logical Verification* (free, if you go with Lean).

**Papers (the reading order roughly matches the phases):** AWS formal methods (CACM 2015), Cook (CAV 2018), seL4 (SOSP 2009), CompCert (Leroy, CACM 2009), IronFleet (SOSP 2015), Verdi (PLDI 2015), Iris from the Ground Up (JFP 2018), RustBelt (POPL 2018), O'Hearn on separation logic (CACM 2019), eXtreme Modelling (VLDB 2020), S3 ShardStore (SOSP 2021), Verus (OOPSLA 2023 and SOSP 2024), Anvil (OSDI 2024), and Cedar (2024).

**People and blogs worth following:** Hillel Wayne (the *Computer Things* newsletter), Jack Vanlightly (Kafka and protocol TLA+ analyses), Igor Konnov (*Protocols Made Fun*, on Apalache, Quint, and conformance testing), Lamport's site, Leino's Dafny material, and the Iris project pages.

**Communities:** the TLA+ Foundation forum and the annual TLA+ Conference; the Lean Zulip, which is very active; the Rocq Discourse and Zulip; the Isabelle AFP; the CAV, POPL, PLDI, ITP, and OSDI/SOSP proceedings; and, locally in Seoul, the SNU SF Lab and KAIST CP Lab seminars plus the SIGPL Korea schools.

---

## Currency warnings (as of July 2026)

- Rocq: the Coq-to-Rocq rename landed with Rocq Prover 9.0 in March 2025. Older tutorials and Stack Overflow answers say "Coq," which is the same system under a migrating name. Software Foundations has been updated.
- Lean 4 releases monthly, so pin toolchains per project with `lean-toolchain` and elan. mathlib moves fast.
- Verus is young and evolving quickly, with frequent 2026 releases, so expect guide and syntax drift. Always work from the current tutorial rather than blog posts older than about a year.
- Quint and Apalache have been community-maintained since Informal Systems wound down funding in 2024. They are healthy, but check the release cadence before betting a work project on them. TLC remains the boring, stable default.
- LLM-plus-FV tooling (proof agents, MCP prover integrations, vericoding) is the fastest-moving corner of the whole field, and anything written about it more than six months ago is stale.

## How this compounds with your existing arcs

TLA+ and Quint formalize the EDA, outbox, and Kafka replication material you already know deeply, so you'll be checking designs you previously reasoned about informally. Lincheck and jqwik slot into Phases 3 and 8 as tools you already own. Anvil connects verification to your EKS migration. The math PhD makes Phases 2, 3, 6, and 7 dramatically cheaper for you than for the median engineer, and the plan's real bet is converting that theoretical advantage into tooling fluency and public artifacts.
