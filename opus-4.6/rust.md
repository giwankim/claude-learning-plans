---
title: "Rust Mastery for DataFusion/Arrow"
category: "Rust"
description: "10-month phased plan from Rust foundations to active Apache DataFusion and Arrow contributor, tailored for JVM engineers"
---

# Rust mastery plan for Apache DataFusion and Arrow contribution

**A mid-level JVM engineer can reach meaningful open-source contribution to DataFusion and Arrow in 8–10 months by following a phased, milestone-driven plan that front-loads Rust's ownership model and trait system, then layers on async patterns, Arrow memory internals, and query engine architecture.** The critical insight: DataFusion's codebase relies overwhelmingly on `Arc<dyn Trait>` patterns and async streams — not deep lifetime gymnastics — making the learning curve more approachable than "systems Rust" reputation suggests. Your Kotlin/Spring Boot background directly transfers in areas like generics, functional iteration, null safety (`Option<T>` ≈ nullable types), and build tooling (`Cargo` ≈ Gradle). The biggest mental model shifts are ownership semantics (no garbage collector), composition-over-inheritance (no classes), and explicit concurrency bounds (`Send + Sync`).

This plan assumes **10–15 hours per week** alongside a full-time role, totaling roughly 400–600 hours of deliberate practice across six phases. Each phase has concrete deliverables, success criteria, and a capstone project.

---

## Phase 1: Rust foundations through a JVM lens (months 1–2)

The goal of these first eight weeks is to internalize Rust's ownership model, write idiomatic code with structs/enums/traits, and build muscle memory with the compiler. Everything here maps to concepts you already know — but the mechanism is fundamentally different.

**Core resource sequence.** Start with *The Rust Programming Language* (2nd edition, free at doc.rust-lang.org/book) — read chapters 1–13 thoroughly. This covers variables, ownership/borrowing, structs, enums, pattern matching, modules, collections, error handling, generics, traits, closures, and iterators. Simultaneously work through **Rustlings v6** (~95 exercises that mirror TRPL chapters), fixing compiler errors in watch mode. Supplement with **Let's Get Rusty** YouTube videos for chapter-by-chapter visual reinforcement and **Rust by Example** (doc.rust-lang.org/rust-by-example) as a quick-reference companion.

**JVM-to-Rust translation guide.** Your Kotlin `val`/`var` distinction maps directly to Rust's `let`/`let mut`. Kotlin's `when` expression is Rust's `match` — but Rust's is exhaustive and supports destructuring. `Result<T, E>` replaces exceptions entirely; the `?` operator is your new `try/catch`. Traits are interfaces — but with default implementations, associated types, and no inheritance hierarchy. The biggest shock: assigning a `String` to another variable **moves** it (the original becomes invalid). This is the core of ownership.

**Key concepts to nail.** Ownership and borrowing (`&T` for shared references, `&mut T` for exclusive), the `String` vs `&str` distinction (heap-allocated vs. borrowed slice — analogous to understanding `StringBuilder` vs `String` in Java but more fundamental), `Vec<T>` vs `&[T]`, `Option<T>`, `Result<T, E>`, pattern matching, and the `From`/`Into` trait pattern for type conversions.

**Week-by-week breakdown:**

- **Weeks 1–2**: TRPL chapters 1–6 + Rustlings through move semantics. Build the number-guessing game. Goal: compile simple programs without fighting the borrow checker.
- **Weeks 3–4**: TRPL chapters 7–10 (modules, collections, error handling, generics/traits). Complete Rustlings through traits section. Goal: write a multi-file Rust project with custom error types.
- **Weeks 5–6**: TRPL chapters 11–13 (testing, closures, iterators). Start **Google's Comprehensive Rust** course (4-day self-paced, at google.github.io/comprehensive-rust) for a structured review. Goal: write unit and integration tests fluently.
- **Weeks 7–8**: TRPL chapters 15–16 (smart pointers: `Box`, `Rc`, `Arc`, `RefCell`; basic concurrency with threads/channels). This is critical — `Arc<T>` is the dominant ownership pattern in DataFusion/Arrow. Goal: understand when to use `Box` vs `Rc` vs `Arc`.

**Capstone project**: Build a CSV-to-JSON converter CLI tool using `clap` for argument parsing, `csv` and `serde_json` crates for I/O, custom error types with `thiserror`, and unit tests. This exercises ownership (reading file data), iterators (processing rows), error handling (`Result` propagation with `?`), and Cargo dependency management.

**Success criteria**: Complete all Rustlings exercises. Pass the capstone without `unwrap()` in library code. Explain ownership/borrowing to a colleague using a whiteboard. Read a simple Rust function signature and predict what the borrow checker will allow.

---

## Phase 2: Intermediate Rust — traits, async, and the patterns DataFusion uses (month 3)

This phase targets the exact Rust features that dominate the DataFusion and Arrow codebases: trait objects with dynamic dispatch, async/await with tokio, and `Arc`-heavy shared-ownership patterns. You should also start building database domain knowledge in parallel.

**Primary resources.** Read TRPL chapters 17–19 (OOP patterns, advanced traits/types, macros). Begin *Rust for Rustaceans* by Jon Gjengset — chapters 1–4 covering types, traits, designing interfaces, and error handling. Watch **Crust of Rust** YouTube episodes on: Lifetime Annotations, Iterators, Smart Pointers & Interior Mutability, and Dispatch and Fat Pointers. Start **Exercism Rust track** — aim for 30+ exercises focusing on trait implementations and iterator chains.

**Trait objects and dynamic dispatch — the #1 pattern.** DataFusion's entire architecture uses `Arc<dyn Trait>` for extensibility. Every physical plan node is `Arc<dyn ExecutionPlan>`, every expression is `Arc<dyn PhysicalExpr>`, every data source is `Arc<dyn TableProvider>`. The `as_any()` → `downcast_ref::<ConcreteType>()` pattern replaces Java's `instanceof` checks. You must understand **trait object safety** (why some traits can't be used as `dyn Trait`) and associated types.

**Async Rust with tokio.** DataFusion runs its entire execution engine on the tokio async runtime — even CPU-bound work. Work through the **tokio tutorial** (tokio.rs/tokio/tutorial) to understand `async fn`, `.await`, `tokio::spawn`, `Stream` trait, and `Pin<Box<dyn Stream>>`. The key DataFusion type is `SendableRecordBatchStream = Pin<Box<dyn RecordBatchStream + Send>>` — a pull-based async stream of Arrow record batches. Understanding `Send + Sync` bounds is essential: `Send` means a type can move between threads, `Sync` means it can be referenced from multiple threads. `Arc<T>` is both when `T` is both.

**Begin database theory in parallel.** Start watching **CMU 15-445 lectures** (freely on YouTube, Andy Pavlo) — focus on lectures covering query processing, sorting, aggregation, hash joins, and query optimization. This maps directly to DataFusion's `SortExec`, `AggregateExec`, `HashJoinExec`, and optimizer rules. Read the **DataFusion SIGMOD 2024 paper** ("Apache Arrow DataFusion: A Fast, Embeddable, Modular Analytic Query Engine") for the definitive architecture overview.

**Capstone project**: Build an async HTTP API (using `axum` + `tokio`) that accepts a CSV upload, stores it in memory, and supports basic filtering and aggregation queries via query parameters. Use `Arc<Mutex<T>>` for shared state, implement a custom trait for different aggregation operations (sum, count, average), and return JSON results. This exercises `Arc`, dynamic dispatch, async streams, and the trait patterns you'll encounter in DataFusion.

**Success criteria**: Explain the difference between `Box<dyn Trait>` and `Arc<dyn Trait>` and when to use each. Write an async function that returns a `Pin<Box<dyn Stream<Item = Result<T>>>>`. Complete 30+ Exercism exercises. Explain DataFusion's query flow (SQL → logical plan → optimize → physical plan → execution) from memory.

---

## Phase 3: Arrow internals and systems-level Rust (months 4–5)

Now you dive into the Arrow Rust codebase itself. The goal is to understand Arrow's memory model deeply enough to read and modify compute kernels, and to make your first small contributions to `arrow-rs`.

**Primary resources.** Read the **Arrow columnar format specification** (arrow.apache.org/docs/format/Columnar.html) — understand physical layouts, validity bitmaps, offset buffers, and 64-byte alignment. Study the **arrow-rs repository structure** (github.com/apache/arrow-rs): the top-level `arrow` crate re-exports from `arrow-schema`, `arrow-buffer`, `arrow-data`, `arrow-array`, `arrow-arith`, `arrow-ord`, `arrow-select`, `arrow-string`, `arrow-cast`, `arrow-csv`, `arrow-json`, `arrow-ipc`, plus the `parquet` crate. Read Andrew Lamb's **"Arrow and Parquet Part 1–3"** blog series for how primitive types, nested types, and nullability map between the two formats.

**Arrow's memory model — key types to understand:**

- **`Buffer`**: Immutable, reference-counted (`Arc<Bytes>` internally), 64-byte-aligned contiguous memory. Zero-copy slicing via `buffer.slice(offset, length)` — O(1), shares underlying memory.
- **`MutableBuffer`**: Builder for constructing `Buffer`. Supports `push`, `extend`, and efficient `from_trusted_len_iter`. Converts to immutable `Buffer` via `.into()` (zero-copy, one-way).
- **`ScalarBuffer<T>`**: Strongly-typed wrapper around `Buffer` — conceptually `Arc<Vec<T>>` with zero-copy slicing.
- **`NullBuffer`**: Bit-packed validity bitmap. Bit 1 = valid, bit 0 = null. `None` means "all valid" (optimization).
- **`ArrayData`**: Untyped representation holding `DataType`, length, offset, buffers, child data, and nulls. The `offset` field enables zero-copy slicing.
- **Typed arrays**: `PrimitiveArray<T>`, `StringArray`, `BooleanArray`, etc. wrap `ArrayData` with type-safe APIs. All implement the `Array` trait. `ArrayRef = Arc<dyn Array>` is the standard type-erased reference.

**The downcast pattern.** Arrow's central code pattern: match on `DataType`, then downcast `ArrayRef` to the concrete type. Macros like `downcast_primitive_array!` generate this boilerplate across all numeric types. Understanding `macro_rules!` syntax is necessary to read kernel implementations.

**Unsafe Rust in Arrow.** Arrow upholds a **Soundness Pledge**: safe APIs must never trigger undefined behavior. Unsafe appears in: (1) performance invariants the compiler can't verify (e.g., `StringArray` values are valid UTF-8, `TrustedLen` iterators), (2) FFI via the C Data Interface for cross-language zero-copy exchange, (3) buffer operations with raw pointer manipulation. **You won't need to write unsafe code for typical contributions** — but understanding why it exists helps you read the codebase.

**Hands-on exploration.** Clone `apache/arrow-rs`, run `cargo test` (set `ARROW_TEST_DATA` and `PARQUET_TEST_DATA` env vars via `git submodule update --init`). Read through `arrow-arith/src/` to see how arithmetic kernels work. Study `arrow-select/src/filter.rs` for the optimized filter kernel (achieves **10x performance** through batch-copying strategies). Run benchmarks with `cargo bench` using the criterion harness.

**Week-by-week:**

- **Weeks 1–2**: Read Arrow spec + arrow-rs README. Clone repo, build, run tests. Study `arrow-array/src/` — understand `PrimitiveArray`, `StringArray`, `Array` trait hierarchy.
- **Weeks 3–4**: Study compute kernels in `arrow-arith` and `arrow-select`. Implement a custom unary kernel using the `arity::unary` helper function. Read Arrow's `cast.rs` to understand the macro-heavy type dispatch.
- **Weeks 5–6**: Study the `parquet` crate — understand `ArrowWriter` and `ParquetRecordBatchReaderBuilder`. Read the `object_store` crate (now at `apache/arrow-rs-object-store`) — given your AWS background, the S3 integration (`AmazonS3Builder`) will be immediately familiar.
- **Weeks 7–8**: Find and claim a **good-first-issue** on arrow-rs (comment `take` to self-assign). Target documentation improvements, adding test coverage, or small bug fixes first.

**Capstone project**: Build a Parquet file analyzer CLI that reads a Parquet file from local disk or S3 (using `object_store`), displays schema information, row group statistics (min/max/null counts), and computes basic aggregations (sum, count, average) on specified columns using Arrow compute kernels. This exercises the full Arrow stack: reading Parquet, working with `RecordBatch` and `ArrayRef`, downcasting typed arrays, and using compute kernels.

**Success criteria**: Explain Arrow's `Buffer` → `ArrayData` → typed array hierarchy from memory. Write a function that takes an `ArrayRef`, matches on `DataType`, downcasts, and computes a result. Have at least **1 merged PR** to `arrow-rs` (even a documentation or test improvement counts). Understand how Parquet row group statistics enable predicate pushdown.

---

## Phase 4: DataFusion architecture and first contributions (months 6–7)

With Arrow internals understood, you now tackle DataFusion's query engine architecture and begin contributing to its ~30-crate codebase.

**Primary resources.** Read the **DataFusion architecture guide** (datafusion.apache.org/contributor-guide/architecture.html). Study the **optimization blog series** by Andrew Lamb & Mustafa Akur (June 2025) — Part 1 covers the three optimization classes (always-beneficial, engine-specific, access-path/join-order), Part 2 details specific optimizer rules with code pointers. Read *Programming Rust* (Blandy/Orendorff/Tindall) chapters on concurrency and unsafe as a reference companion. Continue *Rust for Rustaceans* chapters 5–8 (async, unsafe, macros, FFI).

**DataFusion's query flow in detail:**

1. **Parsing**: SQL → AST via `sqlparser` crate
2. **Logical planning** (`SqlToRel`): AST → `LogicalPlan` tree (Projection, Filter, Aggregate, Join, TableScan nodes)
3. **Analysis**: `AnalyzerRule`s handle type coercion and name resolution
4. **Optimization**: `OptimizerRule`s rewrite the logical plan (predicate pushdown, projection pushdown, constant folding, subquery decorrelation, join reordering) — runs up to **16 passes**
5. **Physical planning**: `LogicalPlan` → `ExecutionPlan` DAG with concrete strategies (hash join vs. sort-merge join)
6. **Physical optimization**: `PhysicalOptimizerRule`s insert repartition nodes and enforce sort requirements
7. **Execution**: Each `ExecutionPlan` node produces `SendableRecordBatchStream` — async pull-based streams of **8,192-row** `RecordBatch`es, parallel across partitions

**Key DataFusion traits to study:**

- **`ExecutionPlan`**: `execute()` returns `SendableRecordBatchStream`; `children()` and `with_new_children()` enable tree transformations
- **`TableProvider`**: `scan()` returns `Arc<dyn ExecutionPlan>`; your AWS background maps well to implementing custom S3-backed table providers
- **`OptimizerRule`** and **`PhysicalOptimizerRule`**: For adding optimization passes
- **`ScalarUDF`**, **`AggregateUDF`**, **`WindowUDF`**: For user-defined functions — often the easiest intermediate contribution area

**Error handling in DataFusion.** `DataFusionError` is a comprehensive enum with variants for Arrow errors, Parquet errors, planning errors, execution errors, and more. Convenience macros `plan_err!()`, `exec_err!()`, `internal_err!()`, and `not_impl_err!()` replace manual error construction. The `?` operator with `From` trait implementations enables seamless error propagation.

**Contribution pathway — practical steps:**

1. **Browse good-first-issues** at github.com/apache/datafusion/contribute
2. **Start with**: adding documentation, consolidating test files, implementing missing SQL functions (`ScalarUDF`)
3. **Comment `take`** on an unassigned issue to claim it
4. **Submit PR** targeting `main` branch; a committer will trigger CI for first-time contributors
5. **Review others' PRs** — this is explicitly encouraged and is the fastest way to learn the codebase and build community standing
6. **Major PRs** have a 24-hour waiting period between approval and merge for global community review

**Capstone project**: Implement a custom `TableProvider` that serves data from a REST API (or mock data source), register it with a `SessionContext`, and run SQL queries against it through DataFusion. Include predicate pushdown (pass filter conditions to the data source) and projection pushdown (only fetch needed columns). This exercises the full DataFusion extension API and mirrors how real production integrations work.

**Success criteria**: Trace a SQL query through DataFusion's codebase from parsing to execution using a debugger. Implement and register a `ScalarUDF`. Have at least **2 merged PRs** to DataFusion. Explain three optimizer rules (e.g., predicate pushdown, projection pushdown, constant folding) and where they live in the source code.

---

## Phase 5: Deepening expertise with query optimization and performance (months 8–9)

This phase focuses on the harder, higher-impact contribution areas: optimizer rules, physical plan operators, and performance optimization. You transition from "getting started" contributions to "intermediate contributor" status.

**Advanced Rust resources.** Complete *Rust for Rustaceans* (remaining chapters on testing, no_std, procedural macros). Read *Effective Rust* by David Drysdale for idiomatic patterns (the Rust equivalent of *Effective Java*). Watch Crust of Rust episodes on async/await internals and atomics/memory ordering. Read *Rust Atomics and Locks* by Mara Bos (free at marabos.nl/atomics) for deep concurrency understanding.

**Query optimization theory.** Continue CMU 15-445 lectures on query optimization. Study the **MonetDB/X100 paper** ("Hyper-Pipelining Query Execution") — this vectorized batch execution model is core to DataFusion's design. Read the **Volcano optimizer paper** (Graefe, 1993) for theoretical background, though DataFusion uses multi-pass rule rewriting rather than Cascades. Study DataFusion's optimizer source in `datafusion/optimizer/src/` — each rule is a separate file implementing `OptimizerRule`.

**Performance work.** DataFusion benchmarks against **ClickBench** (achieved #1 for single-file Parquet queries). Learn to run benchmarks with `cargo bench`, use `criterion` for microbenchmarks, and profile with `perf`/`flamegraph`. Key optimization patterns: avoid unnecessary allocations, leverage Arrow's zero-copy slicing, use `StringView` (German-style strings) for string-heavy workloads, and understand how Parquet page-level statistics enable predicate pushdown.

**Active development areas where contributions are welcome** (as of early 2026):

- **Dynamic filter pushdown** for hash joins (runtime adaptive optimization)
- **Sort pushdown** to table providers
- **Memory management** improvements (tracking, statistics, spill-to-disk)
- **FFI** for cross-language table providers and UDFs
- **Spark-compatible functions** in the new `datafusion-spark` crate
- **Parquet optimization** (custom indexes, metadata caching, late materialization)

**Capstone project**: Identify a performance bottleneck in DataFusion using ClickBench queries, implement an optimization (new optimizer rule, kernel improvement, or physical plan enhancement), benchmark the improvement with before/after measurements, and submit it as a PR with benchmark results. Alternatively, implement a missing SQL function or optimization rule from the issue tracker.

**Success criteria**: Have **5+ merged PRs** across arrow-rs and DataFusion. Successfully implement a non-trivial optimization or feature. Participate in code review on others' PRs. Understand DataFusion's physical optimizer well enough to explain sort enforcement and repartitioning strategies.

---

## Phase 6: Specialization and sustained contribution (month 10 and beyond)

By this point you're an active contributor. This phase is about finding your niche, deepening community ties, and building toward committer-level understanding.

**Specialization paths based on your background:**

- **Cloud storage integration** (leverages your AWS experience): Contribute to the `object_store` crate or DataFusion's Parquet-on-S3 optimizations. Implement custom `TableProvider`s backed by cloud storage with intelligent caching.
- **Query optimization** (leverages your Spring Boot/data-pipeline intuition): Implement new `OptimizerRule`s, improve cost-based statistics, work on join reordering algorithms.
- **DataFusion Comet** (leverages your JVM knowledge): This Apache Spark accelerator translates Spark physical plans to DataFusion — your JVM background is directly valuable here.
- **New SQL functions**: The `datafusion-functions` and `datafusion-spark` crates have extensive lists of functions to implement — accessible and high-impact.

**Community engagement.** Join the **Arrow Rust Discord** (discord.gg/Qw5gKqHxUM) — channels include `#datafusion`, `#arrow-rust`, and `#general`. Subscribe to `dev@datafusion.apache.org` mailing list for release discussions and project-wide decisions. Attend the **weekly DataFusion video call** (details on Discord). Follow Andrew Lamb (`@alamb`) on GitHub — his "This Week in DataFusion" issue summaries are the best way to track active development. Subscribe to **This Week in Rust** newsletter for ecosystem-wide updates.

**Key people to follow**: Andrew Lamb (PMC Chair, architecture decisions), Andy Grove (original creator, Comet lead), Jay Zhan and Jonah Gao (PMC members, active reviewers), Xiangpeng Hao (StringView/caching work), and the active committer pool (`@comphead`, `@Omega359`, `@goldmedal`, `@2010YOUY01`).

**Success criteria**: Have **10+ merged PRs**. Be recognized by name in the community. Review PRs regularly. Propose a feature or improvement via a GitHub issue with design discussion. Consider applying for **Google Summer of Code** mentorship (DataFusion is an accepted mentoring organization).

---

## Complete resource reference organized by phase

The resources below are sequenced for maximum efficiency. Items marked with ★ are highest-priority within each category.

**Books progression**: ★ *The Rust Programming Language* (months 1–2) → *Programming Rust* (month 3, reference) → ★ *Rust for Rustaceans* (months 3–5) → *Effective Rust* (month 6) → *Rust Atomics and Locks* (month 8, optional). For database theory: ★ *DataFusion SIGMOD 2024 paper* (month 3) → CMU 15-445 lectures (months 3–6) → CMU 15-721 lectures on OLAP systems (months 7–9).

**Hands-on platforms progression**: ★ Rustlings v6 (month 1) → ★ Exercism Rust track (months 2–3, 30+ exercises) → Advent of Code in Rust (December, whenever it falls) → arrow-rs good-first-issues (month 5) → DataFusion contributions (month 6+).

**Video/audio**: Let's Get Rusty (month 1, alongside TRPL) → ★ Crust of Rust by Jon Gjengset (months 3–5, intermediate concepts) → No Boilerplate (ongoing, short advocacy videos) → fasterthanlime blog + YouTube (ongoing, deep technical dives).

**DataFusion-specific reading**: ★ Architecture guide at datafusion.apache.org → ★ Optimization blog series (Lamb & Akur, June 2025) → Arrow and Parquet blog series (Lamb, 2022) → "Dynamic Filters" blog (Sept 2025) → "Aggregating Millions of Groups Fast" (Aug 2023) → "Using StringView/German Style Strings" (Sept 2024).

---

## What makes this plan work

Three design principles separate this plan from generic "learn Rust" curricula. First, **front-loading `Arc<dyn Trait>` patterns** rather than spending weeks on complex lifetime annotations — because DataFusion's architecture uses `Arc` pervasively to sidestep the hardest ownership scenarios. You'll encounter lifetime parameters eventually, but they're less central than the Rust reputation suggests for this specific contribution target. Second, **interleaving database theory with Rust learning** starting in month 3 — because understanding why DataFusion makes certain architectural choices (Volcano-style pull execution, multi-pass rule rewriting, partitioned parallel execution) makes the code far more readable than approaching it as pure Rust. Third, **contributing before you feel ready** — claiming a good-first-issue in month 5 and submitting your first PR when you're still uncomfortable with parts of the codebase. The DataFusion community explicitly welcomes this: review bandwidth is their scarcest resource, and even small contributions (documentation, test consolidation, reviewing others' PRs) build context faster than passive study ever will.

The total estimated investment is **400–600 hours** over 10 months. By month 6, you should be able to read any file in the DataFusion codebase and understand its purpose. By month 10, you should be a recognized contributor with a trail of merged PRs and the technical foundation to tackle substantial features.