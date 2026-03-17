---
title: "Performance Optimization Playbook"
category: "Performance & Optimization"
description: "Godbolt-Rady measure-first performance optimization from Two's Complement"
---

# The Godbolt-Rady performance optimization playbook

**Measure first, optimize second, and question whether you need to optimize at all.** That is the distilled wisdom from the two most recent performance-focused episodes of Two's Complement — "How Fast Is Fast?" (Feb 14, 2026) and "Measure Twice, Optimize Once" (Mar 9, 2026) — where hosts Matt Godbolt (creator of Compiler Explorer, ex-game engine developer, now in finance) and Ben Rady (XP engineering practices veteran, also in finance) lay out a practitioner's guide to making software fast. Across nearly 90 minutes of combined discussion, they cover everything from I/O-dominated workloads to compute-bound hot loops, building a layered framework that applies whether you're optimizing a Redis cache server or shaving nanoseconds off a financial trading system. What follows is a synthesized playbook drawn from both episodes.

## The cardinal rule: you must measure before you touch anything

Matt is emphatic on this point: **"The single most important thing about any kind of performance… is measuring it and making sure you know what you're doing before you make any changes."** This isn't generic advice — it's born from the painful reality that performance work is uniquely deceptive. Unlike other software engineering disciplines, performance is governed by hidden variables: CPU frequency scaling, cache warmth, branch predictor training, background processes, and the chasm between developer hardware and production environments.

The episode's titular principle — **"Measure at least twice, cut once"** — encodes a specific workflow. First, establish that the system is actually slow against a meaningful target. Second, use a profiler to confirm *which part* is slow in context. Third, make a targeted change. Fourth, re-measure to confirm improvement. Fifth, validate in a production-like environment. Skipping any step invites disaster.

Establishing a reproducible baseline matters more than you think. Results must be what Matt calls "intersubjective" — shareable with teammates who get the same numbers. Run benchmarks on dedicated machines at 2am. Use CI pipelines to track performance continuously. If you run the same benchmark twice with no code changes and get wildly different results, you have a measurement problem to solve before you have an optimization problem.

Statistical rigor is non-negotiable. **The mean is "a terrible representation of anything"** because performance distributions are typically log-normal with fat tails. Look at the minimum (your theoretical best case if everything aligns), examine the full CDF, and plot distributions. For throughput benchmarks, run for 20+ minutes to smooth out noise. For latency, you need fundamentally different tools.

## The optimization question hierarchy: four questions before writing any code

The hosts build a decision tree that should precede every optimization attempt. They call the first entry "Rule Zero," credited to a colleague's list of optimization rules:

1. **"Do I even need to do this at all?"** The most powerful optimization is removing work entirely. Kill that expensive log line nobody reads. Eliminate the redundant computation. Question every assumption about what the system must do. This single question eliminates more bottlenecks than any clever algorithm.

2. **"Do I need to do this now?"** If the answer is no, pre-compute it. Populate a lookup table at startup. Cache the result of an expensive call. Matt gives a concrete example: if you can predict the range of values a function will process, build the answer table at startup and turn runtime computation into a table lookup.

3. **"Can I defer this to something else?"** Offload non-critical work to background threads. Post approximate results on the hot path and reconcile later. Matt describes systems where a secondary thread periodically sends updated state — "hey, this is the amount of whatever's available" — letting the latency-critical path avoid expensive queries entirely.

4. **"Do I need a perfect answer?"** Approximations can be dramatically cheaper. If your system can tolerate a slightly stale or rounded value, exploit that tolerance ruthlessly.

Only after exhausting these questions should you consider making the remaining work faster.

## I/O versus compute: two fundamentally different performance worlds

Episode 1 ("How Fast Is Fast?") establishes the high-level framing: most performance problems fall into either **I/O-dominated** or **compute-dominated** categories, and conflating them leads to wasted effort.

For I/O-dominated workloads — the focus of Episode 1 — the critical insight is that your code spends most of its time waiting for something external: disk, network, or kernel transitions. The episode uses a Redis cache server as a running example, exploring how to optimize the I/O path. Techniques discussed include bypassing kernel space to reduce syscall overhead, understanding that network round-trips dominate total latency, and applying Grace Hopper's famous nanosecond wire visualization (an 11.8-inch piece of wire representing the distance light travels in one nanosecond) to build intuition about the physical limits of data movement. The key message: when I/O dominates, no amount of algorithmic cleverness in your application code will help. You must address the I/O path itself.

Episode 2 ("Measure Twice, Optimize Once") pivots to **compute-dominated** workloads, further splitting them into two dimensions. **Throughput** means processing large volumes efficiently — think NLP on text corpora or batch credit card processing. **Latency** means minimizing response time for individual operations — think video game frame rendering under 16ms or financial trading systems where fire-button-to-visual-feedback must stay under 120ms. These two dimensions require fundamentally different measurement approaches, and using the wrong one wastes your time.

## A practitioner's toolkit: matching the right instrument to the problem

One of the most valuable contributions of Episode 2 is a comprehensive, opinionated tour of profiling tools organized by problem type. The hosts' experience spans decades of games, Google, and finance, and they've used all of these in anger.

**For quick diagnosis when you don't know where to start**, `strace` is Matt's go-to. It shows every system call your program makes. Ben adds a critical insight: **"If you're in latency-sensitive code and strace gives you anything, well, there's your problem."** Latency-critical code should not be making system calls on the hot path, period. Separately, GDB serves as a "poor man's profiler" — run your program under GDB, hit Ctrl-C, type `backtrace`, see where you are. Repeat. You're sampling by hand, and for throughput problems this is surprisingly effective. Matt also recommends simply single-stepping through code: "If you get bored of stepping through stuff, then your CPU is taking too long." This reveals excessive indirection — functions calling functions calling functions — that no other tool shows as intuitively.

**For throughput problems**, sampling profilers like Linux `perf` are the standard approach. They interrupt your program ~1,000 times per second and record where the program counter is. Run the workload long enough, and you get a statistical picture of where time is spent. Flame graphs provide hierarchical visualization of this data. But Matt warns that **"a thousand times a second sounds amazing and really often, but to a computer, that's like eternities between sample points."**

**For latency problems**, sampling profilers are "useless" because 99.99% of samples land in the "wait for something to do" routine. You need instrumentation instead. The hosts recommend several approaches:

- **RAII-style timing classes** (in C++) that start a clock in the constructor, stop it in the destructor, and accumulate results. Use the CPU's timestamp counter (TSC) for minimal overhead.
- **Valgrind's instruction-counting mode** — not the memory checker, but a deterministic instruction counter. It virtualizes execution and reports exact instruction counts, immune to the noise that plagues time-based measurements. You can write CI tests: "If this function exceeds 20 million instructions, fail the build."
- **Intel Processor Trace (PT)** records every branch decision into a hardware buffer with near-zero overhead. Combined with **Magic Trace** (a visualization tool layered on top), it provides nanosecond-level accounting of every instruction — "the whole world open to you and every single nanosecond is accounted for."
- **SystemTap, DTrace, and eBPF** hook into kernel events beyond syscalls. Matt describes discovering page-fault-induced latency by hooking into page fault events with SystemTap, revealing that a "pre-allocated" memory slab was actually triggering on-demand page faults. The fix: pre-fault all pages at startup.

## The six traps that fool even experienced engineers

The episodes document a catalog of anti-patterns that the hosts have encountered — or committed — across their careers.

**Trap 1: Micro-benchmarking under ideal conditions.** Running the same code 100 million times in a tight loop with identical input means the branch predictor has perfectly learned every branch and every relevant cache line is hot. You're measuring the best case. In production, the branch predictor has forgotten about your code and the cache is cold. Matt illustrates this vividly with a hash map example: a new implementation benchmarks beautifully in isolation because it has the entire cache to itself, but in the real Redis server it tanks because "it uses tons more RAM than before" and competes for cache lines with the networking code. **Always validate optimizations in the real system context.**

**Trap 2: Trusting developer hardware.** Developer workstations differ from production servers in CPU model, core count, memory configuration, and thermal behavior. Optimizations that shine on your laptop may disappoint in production. Always benchmark on production-equivalent hardware.

**Trap 3: Hidden costs in innocent-looking functions.** Matt describes a class of bugs where the bottleneck isn't algorithmic complexity but a surprise: a string-parsing function that performs a locale lookup on every call ("checking if the user has switched to German"), or worse, a function that treats an identifier as a domain name and fires off a DNS lookup. The classic profiling discovery — "you spend 30% of your time in malloc and 30% in free" — also falls here.

**Trap 4: Confusing optimization flags with debug symbols.** Many developers assume debug builds are unoptimized. Matt insists on always compiling with debug symbols, even in optimized builds. "Separate the idea of optimization — the -O2, -O3 — from leaving the debug symbols around." A fully optimized binary with debug info lets you profile production-like code effectively.

**Trap 5: Formatting strings for disabled logs.** The classic waste: formatting an expensive debug message that gets passed to a logger configured to ignore debug output. The work of formatting happens before the log-level check. Guard the formatting itself behind the level check.

**Trap 6: Reaching for assembly too early.** Matt — who started his career writing assembly for game consoles — warns strongly against it: "You're trading off the ability to change and understand your code down the line. It is so fragile. It is so very, very fragile once you've written it in assembly." Compilers encode **"40 years of other people's experiences poured into heuristics"** and are usually better. When assembly is genuinely warranted (and Matt acknowledges it sometimes is, in finance where compilers cannot intuit which variables matter), keep a C reference implementation alongside it for correctness checking, and periodically race newer compiler versions against your hand-written code.

## The one true use case for linked lists and other surprising specifics

The episodes offer concrete case studies that ground the abstract principles. The most memorable is Matt's defense of the linked list — normally a cache-hostile data structure he would avoid — for financial exchange order books. The problem: maintain an insertion-ordered list with arbitrary middle removal by external ID. Solution: a hash map from order ID to linked list node, with the doubly-linked list enabling O(1) removal by wiring together the predecessor and successor. A vector would require shifting all subsequent elements and updating every hash map entry. The linked list gives consistently predictable (though individually slower) performance without catastrophic worst cases.

The virtual memory page-faulting case study is equally instructive. Matt describes allocating a large memory slab that the OS honors with virtual address space but not physical pages. Every first access triggers a page fault, introducing latency spikes into what should be a fast memory read. The fix — pre-faulting all pages at startup — eliminated the problem entirely.

## A step-by-step methodology for performance work

Synthesizing across both episodes, here is the complete workflow:

**Phase 1 — Define the target.** What does "fast enough" mean? A latency SLA? A throughput requirement? Without a concrete target, you cannot know when you're done, and you risk optimizing forever.

**Phase 2 — Classify the problem.** Is this I/O-dominated or compute-dominated? If compute, is it throughput or latency? This determines your entire tool selection and measurement strategy.

**Phase 3 — Establish a reproducible baseline.** Build a benchmark harness with representative workloads on production-equivalent hardware. Verify reproducibility: run it twice with no changes. If results differ significantly, fix your measurement setup first.

**Phase 4 — Profile to find the actual bottleneck.** Use the appropriate tool for your problem type. Do not guess. The profiler's answer will almost always surprise you.

**Phase 5 — Apply the question hierarchy.** For each identified bottleneck, ask: Can I eliminate this work? Pre-compute it? Defer it? Approximate it? Only then consider making it faster.

**Phase 6 — Make one targeted change.** Change as little as possible. This is a controlled experiment.

**Phase 7 — Re-measure and validate.** Confirm improvement in the benchmark. Then validate in the full system context, not just a micro-benchmark.

**Phase 8 — Guard the improvement.** Add the benchmark to CI. Use Valgrind instruction counting as a regression gate. Keep a graph of performance over time. Performance is easy to lose and hard to recover.

## Actionable do's and don'ts

| Do | Don't |
|---|---|
| Define "fast enough" with a number before starting | Optimize without a measurable target |
| Measure on production-equivalent hardware | Trust micro-benchmarks on your laptop |
| Use the min and distribution, not the mean | Rely on averages for latency analysis |
| Profile to find the real bottleneck | Guess where the bottleneck is |
| Guard log formatting behind level checks | Format strings for disabled log levels |
| Always compile with debug symbols, even in optimized builds | Conflate debug builds with unoptimized builds |
| Use `strace` as a first diagnostic pass | Ignore system calls as a potential source of latency |
| Pre-compute, cache, and defer before micro-optimizing | Jump straight to algorithmic tricks |
| Keep a C reference alongside any hand-written assembly | Write assembly without a correctness oracle |
| Design systems to be profilable from the start | Bolt observability on as an afterthought |

## Conclusion: design for profilability, then let the data lead

The deepest insight from these episodes is Ben's concept of "designing for profilability" — the idea that systems should be built from the start to be measurable under real conditions with real data, just as they should be designed for testability. Performance work is not a heroic rescue operation; it is a continuous engineering discipline built on reproducible measurement and intellectual honesty about what your code actually does.

The most immediately actionable takeaway for any backend developer: **add `strace` to your next debugging session.** If your latency-sensitive path makes syscalls you didn't expect, you've just found your biggest win. Then set up a CI benchmark with Valgrind instruction counting. These two changes cost hours to implement and prevent months of performance regression. Everything else — flame graphs, Intel PT, hand-tuned assembly — is a progression that only the data can justify reaching for.