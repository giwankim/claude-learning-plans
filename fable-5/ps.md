---
title: "Competitive Programming Training Curriculum for a Mathematically-Sophisticated Senior Engineer"
category: "Algorithms & Problem Solving"
description: "A 6-12 month, 10-15 hrs/week phased path from interview-level DS&A to Codeforces Expert (1600) and a Candidate Master (1900) push. It decodes the Codeforces/AtCoder/solved.ac rating systems and their fuzzy cross-mapping, says where a math PhD is a real edge (invariants, number theory, monoid-structured segment trees) and where it won't transfer (implementation speed under contest pressure), and explains when to migrate off Java: fast I/O, the Arrays.sort anti-quicksort trap, anti-hash tests, and AtCoder's no-extension time limits push you toward C++ around CF 1700-1900. Includes a topic ladder (Phases A-D), English and Korean resources (CPH, USACO Guide, CSES, CF EDU, 종만북, 바킹독), tooling (Competitive Companion, JHelper/KHelper, stress testing, Carrot, kenkoooo), a weekly routine, and a 2026 caveat on BOJ's judge-status flux."
---

# Competitive Programming Training Curriculum for a Mathematically-Sophisticated Senior Engineer

## TL;DR
- A realistic, math-leveraged path: reach Codeforces Expert (1600), AtCoder cyan to blue, or solved.ac Platinum in roughly 4-8 months, and Candidate Master (1900) or AtCoder blue in 12-18 months at 10-15 hrs/week. Your PhD-level proof skill and existing DS&A base put you well ahead on ideation, so your bottleneck will be implementation speed and contest time pressure rather than concepts.
- Stay in Java through Expert, and plan a partial migration to C++ around CF 1700-1900+. That is where strict time limits (AtCoder has no per-language TL extension, while Codeforces historically scales Java) and the missing ordered-map and policy (order-statistics) structures make Java painful. Kotlin is a reasonable professional-comfort compromise but shares the JVM's HashMap/TLE and boxing liabilities.
- Use all three ecosystems deliberately: AtCoder ABCs for clean math and DP work and for speed, Codeforces Div 3/4 then Div 2 for contest volume and rating, and BOJ/solved.ac tiers plus 종만북 and 바킹독 for structured Korean-language topic coverage. Note that BOJ's judge is in a service transition (an announced shutdown on 2026-04-28, then "judge service in preparation"), so keep AtCoder and Codeforces as your guaranteed-stable primary judges.

## Key Findings

### The three rating systems, decoded
The single biggest calibration tool is understanding that these three platforms measure different things. Codeforces is speed-and-volume ELO. AtCoder is cleaner and more math and ad-hoc. solved.ac measures the *difficulty of problems you've solved*, a cumulative "what can you solve" metric, rather than live contest performance.

Codeforces ranks (ELO-style, updated per contest):

| Rank | Rating band |
|---|---|
| Newbie | 0-1199 |
| Pupil | 1200-1399 |
| Specialist | 1400-1599 |
| Expert | 1600-1899 |
| Candidate Master | 1900-2099 |
| Master | 2100-2299 |
| International Master | 2300-2399 |
| Grandmaster | 2400-2599 |
| International Grandmaster | 2600-2999 |
| Legendary Grandmaster | 3000+ |

Per Codeforces' own 2026 rating-distribution analysis, "the majority of users are concentrated roughly between 800 and 1400 rating, which mostly corresponds to the Newbie and Pupil ranks," and that is where the distribution reaches its peak. Division cutoffs: Div 4 (rated below 1400), Div 3 (below 1600), Div 2 (below 2100), Div 1 (1900 and above).

AtCoder colors (each color spans exactly 400 points):

| Color | Rating band |
|---|---|
| Gray | 0-399 |
| Brown | 400-799 |
| Green | 800-1199 |
| Cyan | 1200-1599 |
| Blue | 1600-1999 |
| Yellow | 2000-2399 |
| Orange | 2400-2799 |
| Red | 2800-3199 |

AtCoder ratings run visibly "lower" than Codeforces for the same person, and AtCoder deliberately suppresses your rating until you've done about 10 contests. AtCoder cyan (1200) is a genuinely strong achievement, roughly comparable in skill to CF Expert territory.

solved.ac tiers are driven by "AC rating," computed from the difficulty sum of your hardest 100 solved problems plus CLASS and solve-count bonuses. The AC-rating cutoffs (these are solved.ac internal numbers, not Codeforces rating) are Bronze 30, Silver 200, Gold 800, Platinum 1600, Diamond 2200, and Ruby 2700. Each tier has 5 sub-levels (V through I). solved.ac was created by Park Su-hyeon (박수현, handle *shiftpsh*), a Sogang University CS student, who intends Platinum, Gold, Silver, and Bronze to correspond roughly to the top 10%, 33%, 67%, and 100% of users.

Cross-platform mapping (approximate community consensus, and genuinely fuzzy: the solved.ac to CF correlation is only about R²≈0.6):

| solved.ac tier | Approx. CF rating | Approx. CF rank | Approx. AtCoder color |
|---|---|---|---|
| Bronze | <1000 | Newbie | gray |
| Silver | 1000-1300 | Newbie to Pupil | brown |
| Gold | 1300-1600 | Pupil to Specialist | green to cyan |
| Platinum | 1600-1900 | Expert | cyan to blue |
| Diamond | 1900-2400 | CM to Master | blue to yellow |
| Ruby | 2400+ | GM+ | orange+ |

Your interview background (LeetCode Top Interview 150) maps to roughly CF Pupil or Specialist (1200-1500) on pure knowledge, but likely lower on *contest* rating initially because of unfamiliarity with format and speed. Expect your first few CF contests to under-rate you. It converges, so don't panic.

### Where your math PhD is a genuine edge, and where it won't help
Advantages to lean into: constructive and ad-hoc problems, since the CF "ad-hoc" style rewards exactly the "find a clean invariant" instinct; number theory and combinatorics, where modular arithmetic, group structure, inclusion-exclusion, and generating functions feel natural; proving greedy correctness via exchange arguments, since you already reason "assume optimal, swap, show no worse"; understanding why an algorithm is correct rather than memorizing it; and DP as a recurrence or algebra over a semiring, so matrix exponentiation, min-plus, and monoid-structured segment trees will click fast. Your comfort with monoids is literally the right abstraction for segment trees: a segment tree computes a monoid fold over ranges, and lazy propagation is a monoid action.

What won't transfer automatically: raw implementation speed, meaning typing a correct Dijkstra, DSU, or segment tree in a few minutes under pressure; "coding the obvious idea fast" on easy problems (Div 2 A/B, where the bottleneck is a 90-second implementation rather than insight); debugging under time pressure without a debugger; contest stamina and rating psychology; and the standard "tricks vocabulary," the fact that many problems are "just" a known technique in disguise. You build that catalog only by volume.

### Language reality: Java now, C++ later, Kotlin as a bridge
Java is used by strong competitors through Expert and beyond, but you have to respect its pitfalls:

- Fast I/O is mandatory. `Scanner` is far too slow. Use `BufferedReader` with `StringTokenizer`, or `StreamTokenizer` (fastest for pure-numeric input), plus `StringBuilder`, `BufferedOutputStream`, or `PrintWriter` for batched output. Never call `System.out.println` in a tight loop. Build a reusable `FastReader` template once.
- `Arrays.sort` on primitives is a TLE trap. Java's `Arrays.sort(int[])` uses dual-pivot quicksort with an O(n²) worst case, and adversaries craft anti-quicksort tests. The fix: shuffle the array before sorting, or box to `Integer[]` or `List<Integer>` and use `Collections.sort`, which is a guaranteed O(n log n) stable mergesort.
- HashMap and HashSet anti-hash tests. On Codeforces, especially in educational rounds with open hacking, integer-keyed `HashMap` and `HashSet` can be forced into O(n²) via collision-crafted inputs. JDK 8+ mitigates the worst case to O(log n) per bucket via JEP-180 balanced-tree treeification, but you can still be slowed badly. Defenses: add a random salt to keys, use `TreeMap` when ordering helps, or use primitive-array counting when the key domain is small.
- Autoboxing in hot loops (`Integer`, `Long`, `HashMap<Integer,Integer>`) creates GC pressure, so prefer primitive arrays.
- Time-limit scaling: Codeforces historically applies a language multiplier for Java on many problems, and the exact factor varies by problem and round, which softens the blow. AtCoder gives no per-language extension at all, since the time limit is identical for C++ and Java, which is why Java gets painful on AtCoder's tighter problems earlier.

When to switch to C++: the honest answer is that Java carries you comfortably to CF Expert (around 1600) and often into CM territory for most problem types. The pain concentrates at CF 1700-1900+ and AtCoder blue and above, specifically on problems needing an ordered map, `std::set` with `lower_bound`, or an order-statistics policy tree (`__gnu_pbds::tree`, for which Java has no clean equivalent, so you must hand-roll a Fenwick/BIT or balanced BST); on very tight constant-factor problems (heavy segment trees, suffix automata, FFT); and on AtCoder's no-extension time limits. Recommendation: learn C++ in parallel starting around Phase 3, port your template, and switch problem by problem when you hit a Java wall. Kotlin is legitimate since you use it professionally, Codeforces fully supports it, and it runs the recurring Kotlin Heroes contests (14 episodes as of 2026; Episode 14's main phase began March 2, 2026). But on the JVM, Kotlin inherits the exact same HashMap/TLE and boxing issues, so it solves the comfort problem rather than the JVM speed ceiling.

### Platform status caveat (important, 2026)
Baekjoon Online Judge's own notice stated "BOJ, which began in March 2010, will end its service on 2026-04-28," and a later April 19, 2026 notice warned that the shutdown could be moved up early due to scraping-induced server load. As of mid-2026 the landing page shifted from "shutdown" to "judge service in preparation" ("채점 서비스 준비 중"), signaling an intended return, while solved.ac announced it was preparing an independent path following the end of BOJ integration. The practical implication: treat AtCoder and Codeforces as your guaranteed-stable primary judges, and use BOJ and solved.ac for their excellent tiered problem curation and Korean-language topic ladders without making your whole routine depend on BOJ's judge being live. vjudge.net can proxy-submit to BOJ problems if the main judge is down.

## Details

### Topic progression (CP syllabus beyond interviews)
The core insight: interview prep teaches you what the algorithms are, while CP requires recognizing which one applies under a disguise, implementing it fast and bug-free, and combining two or three of them. You already have partial exposure to segment trees, sparse tables, RMQ, 0-1 BFS, Dijkstra, and matrix exponentiation, but CP-level mastery means implementing them from a blank file in minutes and knowing the variants (iterative segment tree, lazy propagation, segment tree beats, Dijkstra with potentials, and so on).

**Phase A, foundations and speed (CF 1300 and below / solved.ac Silver to low Gold / ABC A-C):**
- Complete search and brute force; recursion, backtracking, generating subsets and permutations
- Greedy with exchange-argument proofs
- Sorting-based techniques, custom comparators, coordinate compression
- Two pointers and sliding window
- Prefix sums and difference arrays (1D and 2D)
- Binary search, and binary search on the answer (parametric search, a huge CP staple)
- Basic number theory: sieve, gcd, modular arithmetic
- The goal here is speed: solve A/B/C-level fast and clean.

**Phase B, core algorithms (CF 1300-1600 / solved.ac Gold / ABC C-E):**
- Graphs: BFS/DFS, connected components, 0-1 BFS, Dijkstra, Bellman-Ford, Floyd-Warshall, topological sort
- DSU (union-find) with path compression and union by rank
- Classic DP: knapsack, coin change, LIS (O(n log n)), grid DP, interval DP, DP on subsequences
- Bitmasking and bitmask DP
- Number theory: modular inverse (Fermat or extended Euclid), combinatorics with precomputed factorials, fast exponentiation
- Elementary strings: hashing, prefix function (KMP), Z-algorithm

**Phase C, intermediate structures and advanced DP (CF 1600-1900 / solved.ac Platinum / AtCoder blue):**
- Segment trees (iterative and recursive), lazy propagation, Fenwick/BIT, sparse table. You know these already, so now master the variants and merge functions as monoids.
- Trees: rooting, subtree DP, tree DP, Euler tour with subtree-to-range, LCA via binary lifting
- Graph theory: MST (Kruskal, Prim), SCC (Tarjan, Kosaraju), bridges and articulation points, bipartite matching basics
- DP: digit DP, DP over subsets (SOS DP), tree DP with rerooting
- Number theory and math: matrix exponentiation for recurrences (recognize it in DP-speedup disguise), inclusion-exclusion, Möbius
- Strings: trie, Aho-Corasick (intro), suffix array (intro)
- Geometry basics: cross product, orientation, convex hull, line sweep intro

**Phase D, advanced (CF 1900+ / solved.ac Diamond / AtCoder yellow):**
- DP optimizations: divide-and-conquer optimization, Knuth optimization, convex hull trick (CHT), Li Chao tree
- Heavy-light decomposition, centroid decomposition, small-to-large merging
- Advanced flows and matching, advanced number theory (FFT/NTT, Lucas), advanced strings (suffix automaton, suffix array with LCP)
- Persistent data structures, segment tree beats, Mo's algorithm

### Recommended resources (English and Korean)

**Structured courses and books (English):**
- Competitive Programmer's Handbook (Antti Laaksonen), a free PDF and the single best concise overview covering most Silver-to-Platinum topics. Read it front to back over Phases A through C.
- USACO Guide (usaco.guide, led by two-time IOI winner Benjamin Qi), the best free structured path: Bronze, Silver, Gold, and Platinum tracks, each a module list with curated problems and both Java and C++ code. It aims to be a "one-stop shop" through Gold, and it is excellent for your topic checklist.
- CSES Problem Set (cses.fi), a canonical curated set of exactly 400 problems (expanded from the original 200 to 300 to 400, with a stated project goal of 1000) organized by topic: Introductory, Sorting and Searching, Dynamic Programming, Graphs, Range Queries, Tree Algorithms, Mathematics, Strings, Geometry, Advanced. Do the DP, Graph, Range Queries, and Tree sections in Phases B and C. It's the highest-signal problem grind available and supports C++, Java, and Python.
- cp-algorithms.com (the English port of e-maxx), the reference encyclopedia for implementations. Use it as a lookup rather than linear reading.
- Codeforces EDU / ITMO Academy (pashka's courses), with outstanding interactive lessons and step problems. The Segment Tree and Two Pointers courses are must-dos in Phase C. ITMO Semester 2 covers segment trees, Fenwick, sparse tables, BSTs and treaps, binary lifting, LCA, HLD, centroid, and link-cut trees.
- AtCoder Educational DP Contest, 26 problems A through Z, each teaching one DP pattern (from Frog and knapsack up through bitmask DP, tree DP, matrix-power DP, digit DP, and SOS/subset problems). Do all 26 across Phases B and C. It's the best DP drilling anywhere, and video editorials exist for all 26.
- Competitive Programming 4 (Steven and Felix Halim), a comprehensive topic reference and problem catalog, good as a breadth map.

**Korean-language resources:**
- 종만북 (『프로그래밍 대회에서 배우는 알고리즘 문제 해결 전략』, 구종만, Insight, a 2-volume set), the classic Korean CP bible. It is uniquely strong on the problem-solving framework (understand → design → verify → implement) and on proving correctness and analyzing complexity, which suits your mathematical style. Its early chapters on brute force, complexity, and proof strategy are worth reading even for an experienced engineer. Companion site: book.algospot.com.
- 바킹독 (BaaaaaaarkingDog) 실전 알고리즘 (blog.encrypted.gg and YouTube), the most popular free Korean CP lecture series, renewed into roughly 32 lectures numbered in hex from 0x00 to 0x1F plus appendices. It is C++-based, and each lesson is paired with BOJ practice problems. An excellent structured on-ramp with a matching problem set (github: encrypted-def/basic-algo-lecture) and a study Discord.
- BOJ 단계별로 풀어보기 (step by step) and solved.ac CLASS 1-10, the best beginner-to-intermediate ladders. The CLASS system enforces balanced topic coverage. Use these as your BOJ backbone, subject to the judge-status caveat above.
- Korean CP communities: the BOJ community boards, the Korean Codeforces community, and university PS blogs, many of which have strong write-ups on Velog, Tistory, and namu.wiki.

**YouTube and streamers (reference):** Errichto (technique explainers, stress-testing, contest streams), SecondThread (contest walkthroughs, and also a Kotlin Heroes commentator), Colin Galen (deep problem-solving mindset), plus William Lin (tmwilliamlin168) and Neal Wu contest screencasts for how top competitors read and attack problems.

### Practical setup and tooling
- Local IDE: IntelliJ IDEA (you're a Java pro) with a CP plugin. CHelper (EgorKulikov) is the classic. It parses problems and, critically for Codeforces' single-file requirement, inlines all your utility and library classes into one `Main.java` at submission and strips unused code. It's aging; modern alternatives are JHelper (the same inlining idea, actively used), KHelper (newer, supports Java and Kotlin, CHelper-inspired), and Caide or AutoCp.
- Competitive Companion (a Chrome and Firefox extension by Jasper van Merle). One click, or Ctrl+Shift+U, parses a problem's or an entire contest's sample tests directly into your IDE plugin. It supports Codeforces, AtCoder, and BOJ among roughly 117 judges, and it is the highest-ROI tooling install.
- Stress testing, which you should learn early because it's your debugger substitute. Write three programs: a generator (random valid input, seeded by a command-line argument so each run differs), your main solution, and a brute force (simple, provably correct, slow). Loop in a bash script: generate, run both, `diff` the outputs, and on mismatch print the minimal failing input and stop. For problems with multiple valid answers, replace `diff` with a custom checker. This finds the adversarial edge cases humans can't invent. The canonical loop:
  ```bash
  g++ -O2 gen.cpp -o gen; g++ -O2 main.cpp -o main; g++ -O2 brute.cpp -o brute
  for ((i=1;;i++)); do
    ./gen $i > in.txt
    ./main < in.txt > o1.txt; ./brute < in.txt > o2.txt
    diff -q o1.txt o2.txt >/dev/null || { echo "FAIL $i"; cat in.txt; break; }
  done
  ```
  In Java, compile once and swap the run commands; tools like QuickTest CLI wrap the pattern.
- Rating and analysis extensions: Carrot (a browser extension that computes your predicted CF rating delta live during a contest and your performance rating after, all in-browser from the CF API) and CF-Predictor (the same idea via a central server, lighter on your bandwidth). Use these plus your rating graph to track progress; both deltas are approximations. For AtCoder, use the difficulty-display userscript.
- AtCoder Problems by kenkoooo (kenkoooo.com/atcoder) is indispensable: per-problem difficulty ratings (defined as the rating at which 50% of contestants solve the problem), a Recommendation/Training tab giving Easy (around an 80% solve chance), Moderate (around 50%), and Difficult (around 20%) problems calibrated to your rating, solve-status tables, streak tracking, and a Virtual Contest builder (log in via GitHub) to replay any custom set of AtCoder problems as a timed contest.
- vjudge.net, a virtual-judge aggregator that proxy-submits to BOJ, Codeforces, AtCoder, and dozens more, and lets you build cross-judge virtual contests. Useful as a BOJ fallback and for team practice.
- Accounts to set up now: Codeforces, AtCoder, BOJ plus solved.ac (link them), and GitHub (for kenkoooo virtual contests). Build a public solutions repo for your mistake journal and template library.

### Contest strategy and practice methodology
- The core practice loop: for each problem, think for a fixed budget (say 20-30 min mid-tier, up to 45-60 for hard) without the editorial. If stuck, read the editorial only to the point of unblocking, then close it and re-implement from scratch. Re-implementation is where the learning sticks. Log the problem and the "trick" in your journal.
- Upsolving discipline: after every contest, solve the first one or two problems you couldn't finish, the "+1/+2" rule. This is the single highest-ROI habit for rating growth. Upsolve problems rated up to about 1900 while chasing Expert.
- Two training modes, both needed. Speed training means grinding easy problems (CF 800-1200, ABC A-C) on a timer to make implementation automatic. Depth training means problems roughly 200-300 points above your current rating (kenkoooo "Moderate" or a CF rating filter), where you expect to struggle. Random-select slightly-above-rating problems.
- Virtual contests: when you can't do a live round, do a virtual one, either a past CF Div 2/3 or a kenkoooo AtCoder virtual. Use Carrot or CF-Predictor to check your would-be delta.
- Rating psychology: Codeforces rating is noisy and drops feel bad, so measure progress over a roughly 10-contest window rather than per contest. AtCoder deliberately under-rates you for the first 10 or so contests. Detach ego from any single contest. The metric that matters is "problems I can now solve that I couldn't a month ago."
- Artifacts to maintain: a Java template (fast I/O `FastReader`, `PrintWriter`/`StringBuilder` output, and utilities for gcd, modpow, DSU, sieve, and a sort-with-shuffle wrapper); a snippets library (segment tree, Fenwick, Dijkstra, LCA, and so on); and a mistake journal recording every WA and TLE, what went wrong, the fix, and the general lesson.

## Recommended phased plan (6-12 months, 10-15 hrs/week)

| Phase | Months | Target milestone | Primary focus | Judges/resources |
|---|---|---|---|---|
| 0, setup and calibration | Weeks 1-2 | Accounts, template, first ~5 CF contests to seed rating | Tooling, fast I/O template, format familiarity | All accounts; CPH ch.1-3; easy ABC and a Div 3/4 |
| 1, foundations and speed | 1-2 | CF ~1200-1300 (Pupil) / solved.ac Silver to Gold / solve ABC A-C fast | Complete search, greedy, two pointers, prefix sums, binary search on answer | USACO Bronze to Silver; 바킹독 0x00-0x0F; BOJ 단계별; weekly ABC |
| 2, core algorithms | 3-4 | CF ~1500-1600 (Specialist to Expert) / solved.ac Gold to Platinum / ABC through D | Graphs, DSU, classic DP, bitmask, basic strings, mod arithmetic | USACO Silver to Gold; AtCoder DP Contest A-T; CSES Sorting/Graphs/DP; CF EDU |
| 3, intermediate plus start C++ | 5-7 | CF ~1600-1750 (Expert) / solved.ac Platinum / ABC through E | Segment tree with lazy, tree DP, LCA, SCC, digit/SOS DP, geometry basics | CF EDU Segment Tree course; CSES Range Queries/Tree; USACO Gold; port template to C++ |
| 4, advanced and consolidation | 8-12 | CF ~1800-1900+ (CM push) / solved.ac Diamond / AtCoder blue | DP optimizations, HLD, centroid, advanced strings and math, flows | CSES Advanced; USACO Platinum; cp-algorithms; Div 1 upsolving; ARC problems |

### Weekly routine template (about 12 hrs)

| Day | Activity | Hours |
|---|---|---|
| Mon | New topic: read (CPH/USACO/EDU) plus 2-3 guided problems | 2 |
| Tue | Topic practice: 3-4 problems at or above rating | 2 |
| Wed | Speed drill: 4-6 easy problems on a timer | 1.5 |
| Thu | AtCoder ABC virtual or live, plus upsolve | 2 |
| Fri | Depth: 2 hard problems (30-45 min each, then editorial and re-implement) | 2 |
| Sat | Live contest (CF Div 2/3/4 or AtCoder) | 2 |
| Sun | Upsolve contest (+1/+2), update journal and template | 1.5 |

Balance heuristic: roughly 40% solving problems, 30% learning new topics, 20% contests, and 10% upsolving and review early on. Shift toward more contests and upsolving as you climb, since contests become the main learning vehicle above Expert.

## Recommendations

1. Weeks 1-2, do this now: create Codeforces, AtCoder, BOJ plus solved.ac, and GitHub accounts. Install Competitive Companion and an IntelliJ CP plugin (JHelper or KHelper). Write and commit your Java `FastReader` and `PrintWriter` template with gcd, modpow, DSU, and sieve utilities and a shuffle-before-sort wrapper. Read CPH chapters 1 through 3. Do about 3 ABCs and 1 CF Div 3/4 to seed a rating and learn the format, and ignore the number.
2. Months 1-2 (foundations): follow USACO Bronze to Silver and 바킹독 in parallel, grind CSES Introductory plus Sorting and Searching, and do every weekly ABC. Milestone: comfortably solve ABC A-C and CF Div 2 A-B fast, and hit CF Pupil or solved.ac Silver to Gold.
3. Months 3-4 (core): USACO Silver to Gold, the full AtCoder Educational DP Contest, CSES Graphs plus DP, and CF EDU. Milestone: CF Specialist to Expert (1500-1600), solved.ac Gold to Platinum.
4. Months 5-7 (intermediate plus C++): the CF EDU Segment Tree course, CSES Range Queries plus Tree Algorithms, and USACO Gold. Port your template to C++ and start solving new problems in C++ when Java fights you. Milestone: hold CF Expert, solved.ac Platinum, AtCoder cyan to blue.
5. Months 8-12 (advanced, CM push): CSES Advanced, USACO Platinum, and cp-algorithms deep dives, with heavy upsolving of Div 2 D/E and Div 1 A/B and ARC participation. Milestone: push CF 1800-1900 (Candidate Master), solved.ac Diamond, AtCoder blue.

**Thresholds that should change your plan:**
- Plateau for 10 or more contests at one rating: switch from breadth to depth. Random-solve problems exactly 200-300 points above your rating and upsolve relentlessly. Plateaus almost always mean you aren't solving hard enough problems rather than that you're missing a topic.
- Java TLEs are costing you contests (repeated losses on tight problems, especially AtCoder blue and above): that's your signal to migrate that problem class to C++.
- You consistently get 1600+ *performance* per Carrot but your displayed rating lags: keep competing, and it will converge upward.
- Contest anxiety hurts more than skill gaps: do more virtual contests, which test the same skill with zero rating stakes, until the live format feels routine.

## Caveats
- Rating timelines are population averages, not guarantees. Some reach Expert in about 6 months, and a strong math background can be faster on the ideation axis, but implementation speed still takes calendar time to build. Your ceiling is high; your rate is bounded mostly by consistent deliberate practice and by typing and debugging speed.
- The solved.ac to Codeforces mapping is genuinely loose. The community-measured correlation is only about R²=0.6, and solved.ac rewards cumulative solving rather than contest speed, so a single hard problem's editorial can inflate a tier. Use the mapping table for rough goal-setting only, not for precise equivalence.
- BOJ judge status is in flux in 2026: an announced shutdown on 2026-04-28, later "judge service in preparation," with a warning that it could end early due to scraping load. solved.ac announced an independent path after BOJ integration ended. Verify the current status before building your routine around BOJ, keep AtCoder and Codeforces primary, and keep vjudge as a fallback.
- Codeforces Java time-limit scaling and AtCoder's no-extension policy are the specific mechanics behind "Java gets painful." The exact CF multiplier varies by problem and round, so verify per contest rather than assuming a fixed factor.
- Editorial dependence is the most common form of self-sabotage. Reading editorials too early feels productive but doesn't build the ideation muscle. Enforce your think-time budget and the re-implement-from-scratch rule.
- Tool and prediction accuracy: Carrot and CF-Predictor deltas are approximations, and Carrot notes reduced exactness since the "new rating system." kenkoooo difficulties are an unofficial statistical estimate. Treat all of them as directional.
