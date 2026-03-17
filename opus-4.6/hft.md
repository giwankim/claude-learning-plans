---
title: "High-Frequency Trading Learning Path"
category: "Finance & Trading"
description: "Transition from Spring Boot to sub-microsecond HFT systems"
---

# From Spring Boot to sub-microsecond: an HFT learning path

**Your combination of a Math PhD and 10 years of enterprise backend development puts you in a surprisingly strong position for HFT — but the transition requires 18–24 months of focused, deliberate effort and a fundamental rewiring of how you think about software.** The math PhD opens doors to quant researcher and quant developer roles that pure software engineers cannot access. The enterprise experience, while not directly transferable to hot-path code, provides system design maturity that HFT firms value for broader infrastructure. The most efficient strategy is to enter the industry through the JVM/quant research door first — not wait until you've mastered C++.

This guide covers everything: C++ learning progression, ultra-low-latency systems engineering, market microstructure, career landscape, open-source projects, and Korea-specific opportunities. It's designed as a reference you can return to at each phase.

---

## Phase 1: Rebuilding your mental model of software (months 1–4)

The hardest part of this transition isn't learning C++ syntax — it's unlearning the JVM mindset. In Spring Boot, you optimize for developer productivity, clean abstractions, and maintainability. In HFT, **performance IS correctness**. A trading system that is 1 microsecond slower loses real money, every day.

### The enterprise-to-HFT architecture shift

Everything you know about enterprise architecture needs reframing. The table below captures the core translations:

| Enterprise pattern | HFT reality |
|---|---|
| Dependency injection (Spring) | Compile-time injection via templates/policies — no runtime IoC container |
| ORM (Hibernate/JPA) | Does not exist. No databases on the hot path. Pre-allocated in-memory structures only |
| Message brokers (Kafka) | Lock-free SPSC queues in shared memory — no serialization, no network hop |
| REST/HTTP APIs | Raw TCP/UDP with binary protocols (FIX, ITCH, OUCH); kernel bypass networking |
| Microservices | Monolithic single-process — all components in one address space to eliminate IPC latency |
| JSON serialization | Forbidden. FlatBuffers, Cap'n Proto, or custom binary encoding |
| Thread pools | Fixed CPU-pinned threads (1 thread per core), no context switching |
| Cloud deployment | Bare-metal co-located servers next to the exchange, with tuned BIOS, OS, and NIC |
| Exception handling | Return codes or `std::expected`; exceptions forbidden on hot path |

**The HFT hot path is single-threaded, allocation-free, branch-free, and syscall-free.** The core trading loop is a linear pipeline — Market Data → Order Book → Strategy → Risk → Execution — where every stage is measured in nanoseconds. Unlike enterprise apps with request/response graphs flowing through service meshes, HFT systems are tight, sequential data pipelines where a single cache miss (L1: ~1ns → RAM: ~100ns) can cost you the trade.

### Key mental model shifts from JVM to C++

In the JVM, `new` is cheap (~10ns via bump allocation + GC). In C++, `new` is expensive and non-deterministic — **HFT systems pre-allocate everything at startup and never touch the heap during trading**. In Kotlin, everything is a reference on the heap. In C++, value semantics are preferred — objects live on the stack when possible, and move semantics transfer ownership without copying. In the JVM, garbage collection pauses are invisible at 50ms. In HFT, 50ms is an eternity: the entire tick-to-trade cycle targets under **10 microseconds**, competing against firms achieving sub-microsecond latencies.

Common mistakes JVM developers make in C++: over-using heap allocation, treating `shared_ptr` like a JVM reference (it has atomic reference counting overhead), using `std::string` everywhere (every operation potentially allocates — use `std::string_view`), relying on inheritance/virtual functions (vtable indirection adds ~2–5ns + potential cache miss), and assuming container operations are cheap (`std::vector::push_back` can reallocate; `std::map` allocates nodes).

### C++ book progression

Start with **"A Tour of C++" by Bjarne Stroustrup** (3rd edition, covers C++20) — a concise ~250-page overview designed for experienced programmers. Move immediately to **"Effective Modern C++" by Scott Meyers**, which covers 42 specific C++11/14 best practices including move semantics, perfect forwarding, smart pointers, and lambdas. This book is universally recommended in HFT circles and is critical for the JVM→C++ transition. Then read **"Effective C++"** and **"Effective STL"** (also by Meyers) for foundational idioms and container performance characteristics.

For performance-specific C++, read **"C++ High Performance" by Björn Andrist & Viktor Sehr** (C++20 coverage of memory allocators, metaprogramming, lock-free structures, and benchmarking), followed by **"The Art of Writing Efficient Programs" by Fedor Pikus** — an advanced guide to hardware utilization, compiler optimizations, and concurrency that explicitly targets algorithmic trading developers.

The single most directly relevant book is **"Building Low Latency Applications with C++" by Sourav Ghosh** (2023), which walks you through building a complete electronic trading system from scratch: matching engine, market data handlers, order gateways, and trading algorithms. The companion code is at `github.com/PacktPublishing/Building-Low-Latency-Applications-with-CPP`, and Stacy Gaudreau's blog at stacygaudreau.com provides detailed code walkthroughs.

Supplemental advanced references include **"C++ Concurrency in Action" by Anthony Williams** (the definitive text on C++ threading, atomics, and lock-free data structures), **"C++ Templates: The Complete Guide" by Vandevoorde, Josuttis & Gregor** for deep template metaprogramming, **Agner Fog's "Optimizing Software in C++"** (free PDF, the industry-standard reference on CPU microarchitecture), and **"Computer Systems: A Programmer's Perspective" (CS:APP)** for understanding how code maps to hardware.

---

## Phase 2: Low-latency systems engineering and performance obsession (months 4–8)

This phase transforms you from someone who writes correct C++ into someone who writes *fast* C++. The key insight: **HFT performance is about predictability, not peak speed.** Your worst-case execution time must be tightly bounded and repeatable.

### Modern C++ features that matter for HFT

| Feature | Why it matters |
|---|---|
| `constexpr` / `consteval` (C++17/20) | Move computations to compile time — benchmarked **~91% faster** than runtime equivalents |
| `if constexpr` (C++17) | Compile-time branching eliminates dead code paths |
| Concepts (C++20) | Cleaner template constraints replacing `enable_if` |
| `std::expected` (C++23) | Error handling without exceptions (exceptions forbidden on hot paths) |
| `[[likely]]`/`[[unlikely]]` (C++20) | Branch prediction hints for hot/cold path optimization |
| `std::span` (C++20) | Non-owning view of contiguous memory — zero-cost abstraction |
| CRTP pattern | Static polymorphism replacing virtual dispatch — no vtable overhead |

Features to **avoid on hot paths**: exceptions, RTTI, `dynamic_cast`, virtual functions, `std::shared_ptr`, `std::unordered_map` (dynamic allocation), and `std::deque`.

### Lock-free programming and memory allocation

The canonical resource for lock-free programming is **Dmitry Vyukov's 1024cores.net**. For implementations, study Erik Rigtorp's `SPSCQueue` (`github.com/rigtorp/SPSCQueue`) — a single-producer single-consumer wait-free queue — and his curated `awesome-lockfree` collection (`github.com/rigtorp/awesome-lockfree`). The LMAX Disruptor pattern (single-producer ring buffer) is widely used in HFT; Bilokon & Gunduz implemented it in C++ with significant performance gains over traditional queues.

For memory allocation, the HFT principle is absolute: **the hot path must never touch the heap.** Pre-allocated memory pools are created at startup. Arena/monotonic allocators (`std::pmr::monotonic_buffer_resource` in C++17) allocate from a pre-allocated buffer where deallocation is a no-op. Stack allocation (`std::array`, local variables) is preferred on hot paths. `jemalloc` and `tcmalloc` are useful as drop-in replacements for non-hot-path code.

### Kernel bypass networking

Three technologies dominate, each with different tradeoffs:

**DPDK (Data Plane Development Kit)** maps NIC memory directly into user-space using huge pages and memory-mapped I/O. Dedicated CPU cores run polling mode drivers (PMDs) that never sleep or context-switch. Achieves sub-microsecond packet processing. Tradeoff: DPDK takes exclusive control of NICs — the kernel can't use those interfaces.

**Solarflare/Xilinx OpenOnload** (now AMD) provides kernel bypass by intercepting socket calls via `LD_PRELOAD`. The killer feature is drop-in acceleration — applications using standard BSD sockets get speedup without code changes. The more aggressive **TCPDirect** API achieves **828ns TCP latency** — 39% faster than Mellanox alternatives. Requires Solarflare/Xilinx NICs.

**io_uring** (Linux 5.1+) is a newer async I/O interface using shared ring buffers between user and kernel space. Not true kernel bypass, but significantly reduces syscall overhead. More practical for applications that can't dedicate entire NICs. The DPDK community acknowledges future io_uring improvements may narrow the gap.

### FPGA programming for trading

FPGAs achieve deterministic **sub-25ns** latency for market data parsing and **270ns average round-trip** for complete trading strategies. The "Build fast, trade fast" paper (Boutros et al., FPL 2018) demonstrated a complete HLS-based HFT system on Xilinx Kintex Ultrascale at 42 clock cycles.

**High-Level Synthesis (HLS) dominates over Verilog/VHDL** in HFT due to rapid strategy iteration. A trading backend took 6 months for 4 engineers in Verilog versus 1.5 months for 2 engineers in HLS — with only 10–20% performance difference. AMD/Xilinx Alveo SmartNICs are the industry standard. For learning, the UCSD educational project on PYNQ-Z2 boards provides an affordable entry point, and `github.com/mustafabbas/ECE1373_2016_hft_on_fpga` offers a complete HFT subsystem in Vivado HLS.

### OS tuning essentials

Erik Rigtorp's "Low Latency Tuning Guide" (rigtorp.se/low-latency-guide/) is the gold-standard reference. The critical kernel boot parameters:

```
isolcpus=2-7 nohz_full=2-7 rcu_nocbs=2-7 rcu_nocb_poll
intel_idle.max_cstate=0 processor.max_cstate=1 idle=poll
intel_pstate=disable nosoftlockup skew_tick=1
```

This isolates cores 2–7 from the scheduler (jitter drops from **17ms to 18μs**), suppresses timer interrupts on isolated cores, and prevents the CPU from ever entering sleep states. Additional essentials: disable Transparent Huge Pages (causes TLB shootdowns), use 2MB/1GB huge pages for DPDK, disable hyper-threading (doubles effective L1/L2 cache per thread), and ensure the NIC and application are on the **same NUMA node**.

---

## Phase 3: Market microstructure — understanding what you're building (months 4–9, concurrent)

### How modern electronic markets work

The limit order book (LOB) is the central data structure of electronic exchanges. **Price-time priority** (FIFO) is standard for most equity exchanges — orders at the best price match first, and among equal-price orders, the earliest wins. This directly rewards speed, which is why HFT exists. Some futures markets (certain CME products) use **pro-rata matching**, where fills are allocated proportionally to order size, rewarding capital over speed.

Market data comes in three levels: **Level 1** (best bid/ask + last trade — available via SIP), **Level 2** (full depth at all price levels, aggregated by price — requires direct exchange feeds), and **Level 3** (every individual order with order IDs — the most granular view required for sophisticated order flow analysis).

### Exchange protocols you'll implement

**ITCH** is NASDAQ's proprietary binary market data protocol — outbound only, delivering full order book events at 1,000+ updates/second. **OUCH** is its companion for order entry. **FIX** (Financial Information eXchange) is the industry-standard text-based protocol (tag=value ASCII), versatile but slower to parse. **SBE** (Simple Binary Encoding), developed by the FIX Protocol's High Performance Working Group, was adopted by CME for MDP 3.0 market data and iLink 3 order entry. Protocol choice varies by exchange: NASDAQ uses ITCH/OUCH, CME uses SBE, NYSE has proprietary binary feeds, and Eurex uses EOBI/ETI.

### How asset classes differ

**Equities** are governed by Reg NMS, which mandates NBBO and order protection across ~16 fragmented exchanges. The SIP consolidates best bid/offer from all venues at ~18μs latency. Direct feeds provide richer data faster but at premium cost. **Futures** (CME) use central clearing, SBE protocols, and a mix of price-time and pro-rata matching. Futures lead price discovery in many markets (E-mini S&P 500 leads SPY). Co-location is at Aurora, IL, not New Jersey. **Crypto** trades 24/7 across hundreds of fragmented exchanges with no Reg NMS equivalent, no consolidated tape, higher volatility (±5–10% intraday common), and API-based access typically in milliseconds rather than microseconds. Approximately **60–80% of crypto trading** is algorithmic/HFT.

### Essential reading for market microstructure

Start with **"Trading and Exchanges" by Larry Harris** — the foundational text for practitioners. Follow with **"Algorithmic and High-Frequency Trading" by Cartea, Jaimungal & Penalva** for the mathematical framework (Avellaneda-Stoikov optimal market making). **"Trades, Quotes and Prices" by Bouchaud** provides the econophysics perspective. **"Algorithmic Trading and DMA" by Barry Johnson** covers execution algorithms practically. For the broader picture, **"Inside the Black Box" by Rishi Narang** explains how quant/HFT firms operate, and **"Advances in Financial Machine Learning" by Marcos López de Prado** is essential for modern ML-driven trading.

Key academic papers: Avellaneda & Stoikov (2008) for optimal market making, Glosten & Milgrom (1985) for adverse selection theory, and the Imperial College paper "C++ Design Patterns for Low-Latency Applications Including HFT" (arXiv:2309.04259) which benchmarks 12+ optimization techniques with code at `github.com/0burak/imperial_hft`.

---

## Phase 4: Build projects that prove you can do this (months 5–14)

### Progressive project roadmap

**Tier 1 — Foundations (months 2–5):** Build a **limit order book** with price-time priority targeting <1μs per operation. Implement a **FIX protocol parser** (build your own lightweight version, reference QuickFIX). Create a **custom memory pool allocator** with zero runtime allocation.

**Tier 2 — Intermediate (months 5–9):** Build a **market data feed handler** connecting to a real exchange (Binance WebSocket API is freely accessible) with microsecond timestamps. Implement a **lock-free SPSC queue** following the Disruptor pattern and benchmark against `std::queue`. Build a **full matching engine** supporting limit, market, IOC, FOK, and GTC orders targeting >1M orders/second.

**Tier 3 — Advanced (months 9–14):** Implement a **market-making simulator** with inventory management and risk limits, backtested against historical tick data. Build a **UDP multicast receiver** with busy-polling and kernel bypass (DPDK or ef_vi). Integrate everything into a **full trading ecosystem** — market data handler → strategy engine → order gateway → matching engine — and measure end-to-end latency with p50/p99/p999 percentiles.

Host all projects on GitHub with detailed READMEs, architecture documentation, and **benchmark results including profiling data, cache miss analysis, and latency distributions**. HFT firms care about demonstrated understanding of performance, not just correctness.

### Open-source projects to study and contribute to

- **CppTrader** (`github.com/chronoxor/CppTrader`) — ITCH parsing at **24ns/message** (41M msg/s), matching engine at 54–309ns
- **itch-order-book** (`github.com/charles-cooper/itch-order-book`) — Ultra-fast ITCH order book at **61ns/tick** using only vectors and C arrays
- **LiquiBook** (`github.com/enewhuis/liquibook`) — Header-only C++ matching engine, 2.0–2.5M inserts/second, well-documented
- **hftbacktest** (`github.com/nkaz001/hftbacktest`) — Premier HFT backtesting tool (Python/Rust) accounting for queue positions, feed/order latencies, and L2/L3 order book reconstruction
- **libtrading** (`github.com/libtrading/libtrading`) — Ultra-low-latency connectivity supporting FIX, FIX/FAST, ITCH, OUCH at **15–17μs** round-trip
- **hffix** (`github.com/jamesdbrock/hffix`) — Header-only HFT-optimized FIX parser
- **imperial_hft** (`github.com/0burak/imperial_hft`) — Benchmarked low-latency techniques from Imperial College (cache warming, constexpr, Disruptor, pairs trading)
- **Hummingbot** (`github.com/hummingbot/hummingbot`) — Open-source market making framework with 140+ exchange connectors

For FPGA practice: `github.com/mustafabbas/ECE1373_2016_hft_on_fpga` (complete HFT subsystem in Vivado HLS, <450ns roundtrip) and `github.com/mbattyani/sub-25-ns-nasdaq-itch-fpga-parser` (24.8ns fully pipelined ITCH parsing).

---

## The HFT career landscape and where you fit

### What top firms look for and how they hire

Major HFT firms — Citadel Securities, Jane Street, Hudson River Trading, Jump Trading, Optiver, Tower Research, IMC, DRW, Virtu, Two Sigma, DE Shaw, SIG — are among the most selective employers in technology. Interviews differ sharply from big tech: expect **deep C++ questions** (memory management, move semantics, lock-free programming, cache optimization), **probability puzzles and mental math speed tests**, **system design** focused on trading architecture, and brain teasers/Fermi estimation problems. Preparation resources include "Heard on the Street" by Timothy Crack, the "Green Book" (A Practical Guide to Quantitative Finance Interviews), and competitive programming on Codeforces.

**Your Math PhD is a significant differentiator.** It's the single most valuable credential for quant researcher roles at Two Sigma, HRT, Jane Street, Citadel, and DE Shaw. The critical gap is the absence of professional C++ low-latency experience. One hiring manager on QuantNet noted: "Cannot stress how many 'Math whiz' PhDs with strong PDE skills we have not hired because they don't have a strong SWE background." The key is demonstrating systems engineering capability alongside quantitative depth.

A crucial insight: **quant development roles are in higher demand and less saturated than quant research.** As one recruiter at Portofino Technologies noted, "If you tell a company you're more interested in quant development, they will be more interested in you." Target quant developer roles that leverage both your math and coding.

### Compensation context

Entry-level software engineers at top HFT firms earn **$300K–$500K** total compensation. HRT's median L1 engineer compensation is ~$403K; Jane Street averages **$1.4M per employee** across all levels. Senior quant researchers at top firms earn $800K–$3M+ with profit share. Jane Street UK LLP partners averaged **$19.6M** in 2024. Sign-on bonuses for experienced hires range from $75K to $200K.

### The optimal entry strategy for your profile

**Path A (highest viability): Enter through the JVM door.** Several firms use Java/JVM for trading. LMAX Exchange processes 6M+ orders/second on a single Java thread using the Disruptor pattern. Chronicle Software builds low-latency trading infrastructure in Java and specifically hires PhDs. As one eFinancialCareers source noted: "You won't get a C++ job in HFT with no C++ experience. Every firm I know of has a ton of Java devs handling the non-execution side of things." Get hired into a Java-based trading role first, learn C++ on the job, then transition internally.

**Path B (strong alternative): Enter as quant researcher.** Your Math PhD qualifies you directly for QR roles. HRT is "diversifying who it hires," looking at "people with better discretionary skillsets and academics from AI research firms." Many firms blur the researcher/developer boundary. Enter as QR, learn systems programming on the job.

**Path C: Crypto HFT as a stepping stone.** Lower barriers to entry, more accessible APIs, smaller firms willing to hire outside the traditional pipeline. Many use Python/Java alongside C++. Major traditional HFT firms (Jump, DRW/Cumberland, Jane Street, Flow Traders, IMC) are all active in crypto.

---

## Opportunities in the Korean market

### KRX and the Korean derivatives landscape

The Korea Exchange (KRX) operates KOSPI (main market), KOSDAQ (small/mid-cap), and a derivatives market that includes **KOSPI 200 futures and options** — historically among the world's most liquid index derivatives. A Eurex/KRX link allows international investors to access KOSPI 200 products during US and European hours. The CFTC issued a no-action letter in February 2025 for KRX to offer KOSPI 200 futures in the US.

Korea requires HFT firms to **register with KRX** before trading and assigns separate identifiers for monitoring. The Securities and Futures Commission imposed its **first-ever HFT penalty** — KRW 11.88 billion (~$9M) — on an overseas firm for market disturbance. Foreign institutions must establish a local entity to obtain direct KRX membership.

### Firms hiring in Korea

**Hudson River Trading maintains a Seoul office** (Three IFC, Yeongdeungpo-gu) with a hybrid remote policy and named a new Asia-Pacific business development head in February 2026. **WorldQuant has a Seoul research office** actively hiring data scientists and quant researchers (contact: WQKoreajobs@worldquant.com). Locally, **Blue Financial Group** (founded 2020 by an ex-Bank of America trader) focuses on quant trading of overseas assets and crypto, and **Alphanonce** specializes in digital asset quantitative trading across Korea and Singapore.

The founder of Blue Financial Group offers a critical insight: **"The biggest advantage to run a quant firm here in Seoul is quant developers and data scientists are so undervalued. The average salary is almost a third, or even a quarter of New York, while the only thing they are lacking is English."** Average quant analyst salary in Seoul is ~₩86.6M (~$65K) — significantly below global benchmarks. However, remote roles for global firms can benchmark toward US rates, and the compensation gap is narrowing.

**Seoul's timezone (KST, UTC+9) aligns perfectly with Asian markets** (Tokyo, Shanghai, Hong Kong, Singapore) and overlaps with European morning sessions. US equity markets open at 11:30pm KST — challenging for traditional HFT but irrelevant for 24/7 crypto markets. Crypto HFT firms are generally the most remote-friendly due to API-based exchange access.

---

## Blogs, communities, conferences, and ongoing learning

The most valuable online communities are **r/algotrading** and **r/quant** on Reddit, **QuantNet** (blends career forums with MFE program rankings), **Wilmott** (deep mathematical discussions from experienced quants), and **Elite Trader** (practical execution and exchange nuances). For blogs, follow the **Mechanical Markets blog** (anonymous HFT practitioner with deep technical posts), **Matt Levine's Money Stuff** (essential daily newsletter on market structure), **Databento's blog** (excellent technical posts on co-location and market data infrastructure), and **QuantStart** (tutorials and career guidance). The **Microstructure Exchange** (microstructure.exchange) hosts an online seminar series for market microstructure research.

For conferences, **CppCon** features multiple annual talks on low-latency C++ (search for Carl Cook's "When a Microsecond is an Eternity" from 2017, and Fedor Pikus's performance talks). The **QuantNet C++ Programming for Financial Engineering** certificate (16 weeks, personal TA from the quant industry) is specifically designed for this career path, with an advanced follow-up course covering C++17/20 concurrency and parallelism.

For video learning, the BytesQube HFT article series (bytesqube.com) covers 7 parts from Modern C++ to Market Microstructure, and the Imperial College paper's companion repository provides benchmarked code for every technique discussed.

---

## Conclusion

The path from Spring Boot to sub-microsecond trading systems is steep but navigable — and your profile is stronger than you might think. A Math PhD combined with a decade of professional software engineering gives you something rare in HFT: the ability to bridge the quant research and systems engineering worlds. The key is **not waiting to be "ready" before entering the industry**. Enter through the JVM trading door or a quant research role within 6 months while building C++ skills in parallel. Your existing JVM expertise has direct value at firms like LMAX and Chronicle Software, and your math background qualifies you for quant researcher positions at top firms immediately.

Three non-obvious insights from this research: First, the traditional boundary between quant researcher, quant developer, and trader is blurring — firms increasingly want people who can do all three, which is exactly where a Math PhD + senior developer profile excels. Second, crypto HFT offers a lower-friction entry point with higher marginal returns on speed improvements (millisecond arbitrage windows still exist across fragmented exchanges, unlike the nanosecond arms race in equities). Third, being based in Korea is less of a disadvantage than you might assume — HRT and WorldQuant have Seoul offices, crypto markets are timezone-agnostic, and Korean quant talent is dramatically undervalued relative to global rates, making you attractive to firms seeking cost-effective remote talent with top-tier credentials.

Start today with "A Tour of C++" and "Building Low Latency Applications with C++." Build the order book project within your first month. The eighteen months ahead will be the most intellectually demanding and rewarding of your career.