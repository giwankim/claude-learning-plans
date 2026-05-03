---
title: "The Senior Engineer's Field Manual to Dynamic Programming"
category: "Algorithms & Problem Solving"
description: "Recognition signals, a 7-step derivation recipe, 15 canonical DP families, and a four-tier ~70-problem LeetCode ladder, plus a stretch tier (Convex Hull Trick, divide-and-conquer / Knuth optimization, SOS DP, matrix exponentiation) for FAANG senior/staff interview preparation"
---

# The Senior Engineer's Field Manual to Dynamic Programming
*A FAANG-Interview-Oriented Guide with a Mathematical Stretch Tier*

---

## TL;DR

- **DP is fundamentally a recurrence on a DAG of subproblems.** Master recognition (Part 1), the 7-step derivation recipe (Part 2), and the 15 canonical families (Part 3); then climb the four-tier ladder of ~70 LeetCode problems (Part 4). For senior FAANG, expect 1–2 DP problems per loop, typically Tier 2–3 difficulty, with Tier 4 stretch material differentiating staff/principal candidates.
- **Recognition is the bottleneck.** Trigger words ("number of ways", "min/max cost", "longest/shortest", "subsequence", "partition"), failed greedy, and exponential backtracking with repeated state are the strongest signals. Counting and optimization over a combinatorial structure with optimal substructure ⇒ DP. Watch out for false positives that have closed-form (Catalan, binomial), greedy (interval scheduling by end time), or linear-algebraic (matrix exponentiation) solutions.
- **For your math-PhD background, the stretch tier is the real payoff.** Convex Hull Trick is the lower envelope of an arrangement of lines; divide-and-conquer optimization rests on the Monge / quadrangle inequality (`C(a,c)+C(b,d) ≤ C(a,d)+C(b,c)` for `a≤b≤c≤d`); Knuth's optimization adds monotonicity of optimal split points; SOS DP is the Möbius/Zeta transform on the Boolean lattice; matrix exponentiation reduces linear recurrences to `O(k³ log n)`. These connect DP to lattice theory, combinatorial optimization, and harmonic analysis on `(ℤ/2ℤ)ⁿ`.

---

## PART 1 — RECOGNITION FRAMEWORK
*(The skill that breaks most candidates)*

### 1.1 The Two Necessary Conditions

A problem is amenable to DP iff it has **both**:

1. **Optimal substructure** — the optimal solution decomposes into optimal solutions of independent subproblems. Formally: there exists a function `f` on a state space `S` and a transition relation such that `f(s) = ⊕_{s' ∈ N(s)} g(s, s', f(s'))` where `⊕` is min/max/sum/and-or, and the `f(s')` are optimal answers to genuine sub-instances. This is *Bellman's principle of optimality*.
2. **Overlapping subproblems** — the recursion tree of the naïve algorithm revisits the same `s ∈ S` polynomially-many times; the *DAG of subproblems* has `|S|` polynomial in the input but the unrolled tree is exponential.

If only (1) holds and the recursion tree has no repetition (e.g., merge sort, quicksort), it is plain divide-and-conquer, not DP.

### 1.2 Linguistic / Structural Cues

| Cue in problem statement                              | Default first hypothesis           |
|-------------------------------------------------------|------------------------------------|
| "number of ways…", "count…"                           | Counting DP (sum recurrence)       |
| "minimum / maximum cost / profit / length"            | Optimization DP (min/max)          |
| "longest / shortest … subsequence / substring / path" | LIS/LCS or grid/DAG DP             |
| "can you / is it possible to partition / reach"       | Boolean DP (reachability)          |
| "expected value", "probability of"                    | Expectation DP                     |
| "k transactions / at most k of X"                     | Add a `k` dimension to state       |
| "subarray" (contiguous)                               | Often Kadane / 1D DP, not subseq.  |
| "subsequence" (not necessarily contiguous)            | LIS/LCS family                     |
| Grid + "only right/down" or weighted moves            | 2D grid DP                         |
| "intervals", "merge stones / balloons", chain costs   | Interval DP `dp[i][j]`             |
| Tree + "subtree property"                             | Tree DP (post-order)               |
| `n ≤ 20`, "visit all", permutations                   | Bitmask DP                         |
| "number ≤ N up to 10¹⁸ with property P"               | Digit DP                           |
| Linear recurrence, `n ≤ 10¹⁸`                         | Matrix exponentiation              |

### 1.3 The "What Choices at This Step?" Mental Model

For any candidate DP problem, ask three questions in order:

1. **What am I deciding right now?** (Take/skip; jump 1 or 2 steps; cut here or there; pair `i` with `j`; assign element to subset.)
2. **What information must I carry forward to make future decisions correctly?** That information *is* your state.
3. **What information from the past is irrelevant once the state is fixed?** (Markov property — if past affects future only through state, you have a valid DP.)

If you can answer (1)–(3) with a polynomial-size state, you have your DP.

### 1.4 DP vs Other Paradigms — A Decision Tree

```
Is there a single locally-optimal choice provably correct? → GREEDY
   (e.g., interval scheduling by earliest finish, Huffman, MST)
Else: do choices interact, with overlapping subproblems?    → DP
   Else: independent recursive subproblems, no overlap?     → DIVIDE & CONQUER
Else: searching for a value with monotonic predicate?        → BINARY SEARCH (on answer)
Else: must enumerate all solutions with pruning?             → BACKTRACKING
Else: closed-form via combinatorics / number theory?         → MATH
```

The classic FAANG trap: candidates over-reach for DP on problems that have a clean greedy. **Always sketch a greedy first** and produce a counterexample before committing to DP.

### 1.5 Common False Positives

- **"Maximum sum subarray"** — looks DP, but Kadane is essentially a 1-state DP collapsing to greedy.
- **Activity selection / interval scheduling (max non-overlapping)** — greedy by finish time beats DP.
- **Counting paths in an unweighted lattice from `(0,0)` to `(m,n)`** — `C(m+n, m)`, closed-form.
- **n-th Fibonacci / Tribonacci with huge n** — DP is `O(n)`, but matrix exponentiation gives `O(log n)`.
- **"Longest subarray with property X"** — sliding window / two pointers, not DP, when property is monotonic.
- **Catalan-counted structures** (parenthesizations, BSTs of n nodes, valid parenthesis sequences of length 2n) — DP works but `C_n = (1/(n+1))·C(2n, n)` is closed-form.
- **Minimum number of jumps / BFS on unit-cost graph** — BFS, not DP (DP is fine on a DAG; on a general graph it's shortest-path).
- **Knapsack with very large weights but few items** — meet-in-the-middle, not standard DP.

---

## PART 2 — DERIVATION RECIPE
*(From problem statement to working code in 7 disciplined steps)*

### Step 1 — Identify the State Space `S`

Define **what minimal tuple of variables uniquely determines the answer to a subproblem**. State variables typically include:

- A position / prefix index (`i`)
- A second position for two-pointer or interval problems (`j`)
- A capacity / budget / count remaining (`w`, `k`)
- A flag / mode (e.g., "currently holding stock", "last move was a sell")
- A bitmask of visited / used elements
- A "tightness" flag (digit DP)
- A parity / remainder mod m

Heuristic: write down the recursive function signature you'd hand to a junior; every parameter is a state dimension.

### Step 2 — Identify Transitions

For each state `s`, enumerate the **choices** available. Each choice maps `s` to a (possibly smaller) state `s'` with a transition cost. Draw the transition diagram — it is a DAG.

### Step 3 — Write the Recurrence

Express `f(s)` as `⊕` over choices: `f(s) = opt_{c ∈ choices(s)} [cost(s, c) + f(next(s, c))]`. Verify Bellman's principle: substituting suboptimal `f(s')` cannot yield a better `f(s)`.

### Step 4 — Base Cases

The "smallest" states for which `f(s)` is known directly. Be ruthless: empty prefix, capacity 0, single element, etc. Off-by-one disasters live here.

### Step 5 — Evaluation Order

- **Top-down (memoization)**: write the recurrence as a recursive function, cache results. Easy to derive, slight constant-factor overhead, risk of stack overflow on deep recursion (Kotlin/JVM default stack ~512KB).
- **Bottom-up (tabulation)**: choose a topological order of states (by index, by interval length, by mask popcount) and fill iteratively. Faster, allows space optimization, but requires you to know the DAG order upfront.

Rule of thumb: prototype top-down, ship bottom-up if performance matters or recursion depth threatens stack.

### Step 6 — Complexity Analysis

`Time = |S| × avg branching factor at each state`. `Space = |S|` (or less, after step 7). Always state both before coding.

### Step 7 — Space Optimization

- **Rolling array** when `dp[i]` only depends on `dp[i-1]` (or `dp[i-1], dp[i-2]`): keep two rows / three scalars.
- **In-place update**: 0/1 knapsack in 1D, iterate weight from high to low; unbounded knapsack from low to high — the iteration direction is the encoding of "use each item ≤1 vs ∞ times".
- **Dimensionality reduction**: if a dimension is uniquely determined by others (e.g., sum + count + index ⇒ one is redundant), drop it.
- **Bitset compression**: boolean DP arrays over integers can use `BitSet` and do `O(N/64)` shift-OR.

### 2.1 Worked Example: Longest Increasing Subsequence

1. **State**: `dp[i]` = length of LIS ending exactly at index `i`.
2. **Transitions**: from any `j < i` with `a[j] < a[i]`.
3. **Recurrence**: `dp[i] = 1 + max{ dp[j] : j < i, a[j] < a[i] }` (with the empty `max` = 0).
4. **Base**: `dp[i] ≥ 1` for all `i`; effectively `dp[0] = 1`.
5. **Order**: increasing `i`.
6. **Complexity**: `O(n²)` time, `O(n)` space.
7. **Optimization → `O(n log n)` patience sorting**: maintain `tails[k]` = smallest possible tail of an increasing subseq of length `k+1`. For each `a[i]`, binary-search for the first `tails[k] ≥ a[i]` (use `lower_bound` for strict; `upper_bound` for ≥); replace it. `tails.size()` at end is the LIS length. The mathematical content: this is Dilworth's theorem applied to the poset induced by `(index, value)` — patience sorting builds the unique chain decomposition.

### 2.2 Worked Example: Edit Distance (Levenshtein)

1. **State**: `dp[i][j]` = edit distance between `s[0..i)` and `t[0..j)`.
2. **Transitions**: insert (`dp[i][j-1]+1`), delete (`dp[i-1][j]+1`), replace/match (`dp[i-1][j-1] + [s[i-1]≠t[j-1]]`).
3. **Recurrence**: `dp[i][j] = min(...)` of the three.
4. **Base**: `dp[0][j] = j`, `dp[i][0] = i`.
5. **Order**: increasing `i`, then `j`.
6. **Complexity**: `O(mn)` time and space.
7. **Optimization**: rolling array → `O(min(m,n))` space. Hirschberg's algorithm reconstructs the alignment itself in `O(m+n)` space via divide-and-conquer (Erickson, *Algorithms*, Ch. D — recommended reading).

### 2.3 Worked Example: Coin Change (min coins)

1. **State**: `dp[a]` = min coins summing to `a`.
2. **Transitions**: for each coin `c ≤ a`, candidate `dp[a-c] + 1`.
3. **Recurrence**: `dp[a] = min_{c ∈ coins, c ≤ a} dp[a-c] + 1`; `+∞` if unreachable.
4. **Base**: `dp[0] = 0`.
5. **Order**: increasing `a`.
6. **Complexity**: `O(n × amount)`.
7. The "count combinations" sister problem (coin change II) requires iterating coins on the *outer* loop to avoid double-counting permutations — this is a textbook off-by-one trap.

---

## PART 3 — CLASSIFICATION OF PROBLEM FAMILIES

The 15 families below subsume essentially every interview DP problem. Aditya Verma's influential YouTube taxonomy collapses these into 6–7 super-families (Knapsack, Unbounded Knapsack, LCS, LIS, Kadane, MCM/Interval, DP on Trees, DP on Grids); the more granular taxonomy below maps cleanly onto his and onto the 26-problem AtCoder EDPC.

### Family 1 — Linear / 1D Sequence DP

- **Signature**: `dp[i]` = answer for prefix ending at `i`.
- **Recurrence pattern**: `dp[i] = f(dp[i-1], dp[i-2], …, dp[i-k], a[i])`.
- **Examples**: Climbing Stairs, House Robber, Decode Ways, Word Break, Maximum Subarray (Kadane), Min Cost Climbing Stairs.
- **Recognize**: 1D array, decision is "include / skip / which transition from a small set", answer at index `n-1` or `n`.

### Family 2 — Knapsack Family

- **0/1 Knapsack**: `dp[i][w]` = max value using items 1..i with capacity w. `dp[i][w] = max(dp[i-1][w], dp[i-1][w-w_i] + v_i)`. Outer loop items, inner loop capacity *descending* if 1D-rolled.
- **Unbounded Knapsack**: each item ∞ times. Inner loop capacity *ascending*.
- **Subset Sum / Partition Equal Subset / Target Sum**: boolean version, `dp[i][s]` reachable.
- **Multi-dimensional knapsack**: add capacity dimensions (LeetCode 474 *Ones and Zeroes*).
- **Recognize**: items + budget; max value or feasibility under capacity constraint.

### Family 3 — Coin Change Family

- **Min coins** (`dp[a] = min over coins`) — order of loops doesn't matter for min.
- **Count combinations** (`dp[a]` += `dp[a-c]`) — coins outer, amount inner.
- **Count permutations** (e.g., "number of ways to climb with steps 1,2,3") — amount outer, coins inner.

The loop order encoding the multiset/sequence distinction is a *frequently asked* detail.

### Family 4 — LIS Family

- **Plain LIS**: `O(n²)` DP or `O(n log n)` patience sorting.
- **Variants**: Russian Doll Envelopes (sort + LIS), Longest Bitonic Subseq (LIS forward × backward), Min number of LIS to cover (= longest non-increasing, Dilworth).
- **Recognize**: subsequence with monotonic predicate.

### Family 5 — LCS Family (2D string DP)

- **LCS**: `dp[i][j] = dp[i-1][j-1]+1` if match, else `max(dp[i-1][j], dp[i][j-1])`.
- **Edit Distance, Distinct Subsequences, Shortest Common Supersequence, Interleaving String, Wildcard / Regex Matching**.
- **Recognize**: two strings/arrays; align prefixes.

### Family 6 — 2D Grid DP

- **Unique Paths, Min Path Sum, Triangle, Maximal Square, Cherry Pickup (I/II), Dungeon Game**.
- **State**: `dp[i][j]` over grid; for Cherry Pickup, 3 or 4 dimensions for two simultaneous walkers (insight: walk both forward, parameterize by step `k = i+j`).
- **Recognize**: explicit grid + restricted moves.

### Family 7 — Interval DP

- **Signature**: `dp[i][j]` = optimal answer on subarray/substring `[i..j]`.
- **Recurrence pattern**: `dp[i][j] = opt_{i ≤ k < j} f(dp[i][k], dp[k+1][j], cost(i,j,k))`.
- **Iteration order**: by increasing `length = j - i`.
- **Examples**: Matrix Chain Multiplication, Burst Balloons (LC 312 — *the* canonical interval DP), Palindrome Partitioning II, Optimal BST, Stone Game variants, Strange Printer, Min Cost Tree from Leaf Values, Remove Boxes (3D state).
- **Mathematical structure**: when the cost satisfies the Monge/quadrangle inequality, Knuth's optimization reduces `O(n³) → O(n²)` (see Stretch Tier).

### Family 8 — Tree DP

- **Post-order DP**: compute child answers then combine. `dp[v][state]` = optimum on subtree of `v` given state.
- **Examples**: House Robber III, Binary Tree Cameras (3-state: covered-by-self, covered-by-child, uncovered), Diameter as DP (return depth, update global max), Tree distances.
- **Rerooting (advanced)**: when each node needs the answer assuming itself as root, two passes give `O(n)` for the whole tree (USACO Guide *DP on Trees — Solving for All Roots*).

### Family 9 — Bitmask DP

- **State**: subset `mask` ⊆ {0,…,n-1}, often plus a "current element" pointer.
- **Examples**: TSP (Held–Karp, `dp[mask][i]`), Partition to K Equal Sum Subsets, Assignment Problem, Shortest Path Visiting All Nodes (LC 847), Smallest Sufficient Team.
- **Complexity**: typically `O(2ⁿ · n)` to `O(2ⁿ · n²)`. Constraint `n ≤ 20–22` is the giveaway.

### Family 10 — State-Machine DP (DP on Stocks)

- **State**: `dp[i][state]` where `state` is finite (holding/not, transactions used, cooldown).
- **Examples**: LC 121, 122, 123, 188, 309, 714 — the *Best Time to Buy and Sell Stock* hexalogy. LC 188 (k transactions) generalizes them all: `dp[i][k][holding ∈ {0,1}]`.
- **Recognize**: sequence + finite-state finite-memory constraint.

### Family 11 — Digit DP

- **State**: `(pos, tight, …property accumulators…)`, where `tight` ∈ {0,1} encodes whether the prefix equals the prefix of `N`.
- **Pattern**: `count(L, R) = f(R) − f(L−1)`. Recurse over digit position; inside the loop, `next_tight = tight && (d == N[pos])`.
- **Examples**: CSES Counting Numbers, LC 233 *Number of Digit One*, LC 902 *Numbers At Most N Given Digit Set*, LC 1012 *Numbers With Repeated Digits*, LC 600 *Non-negative Integers without Consecutive Ones*.
- **Trick library** (Codeforces blogs by Jon.Snow, vamaddur, gnudgnaoh): only memoize when `tight==0`; track sums mod LCM rather than per-modulus; iterate from MSB to LSB.

### Family 12 — Probability / Expected Value DP

- **Recurrence is linear in expectations** by linearity (`E[X] = Σ p · E[X|event]`).
- **Examples**: Knight Probability in Chessboard (LC 688), Soup Servings (LC 808), New 21 Game (LC 837), Dice Throw with Target Sum (LC 1155).
- **Note**: when the recurrence is over real probabilities, watch numerical stability; for huge `n`, sometimes matrix exponentiation on the transition kernel is required.

### Family 13 — Counting DP

- **Distinct Subsequences (LC 115)**, **Number of Music Playlists (LC 920)**, **Count Vowels Permutation (LC 1220)**, **Number of Ways to Reorder Array to Get Same BST (LC 1569 — uses Catalan / binomial)**.
- Often modulo `10⁹+7`.

### Family 14 — Game Theory DP / Minimax

- **State**: position. `dp[s] = max over my moves min over opponent moves` (or sum-of-scores formulation).
- **Examples**: Stone Game I–IX, Predict the Winner (LC 486), Nim variants, Can I Win (LC 464, bitmask + game).
- **Math link**: Sprague–Grundy theorem reduces impartial games to XOR of Grundy numbers — overkill for interviews but elegant.

### Family 15 — DP on Strings with Two Pointers

- **Palindromic Substrings / Longest Palindromic Substring / Subsequence (LC 5, 647, 516)**.
- **Regex Matching (LC 10), Wildcard Matching (LC 44)** — `dp[i][j]` over prefixes with careful handling of `*`.
- **Recognize**: two indices on a string with structural constraints (palindrome, pattern matching).

---

## PART 4 — PROBLEM LADDER

LeetCode is the reference platform; AtCoder EDPC and CSES are listed where they materially extend coverage. Each problem is a *rung*: solve, then attempt without notes a week later (spaced repetition).

### TIER 1 — FOUNDATIONS (build the recurrence reflex)

| #    | Title                              | Difficulty | Teaches                           |
|------|------------------------------------|------------|-----------------------------------|
| 509  | Fibonacci Number                   | Easy       | Memo vs tab vs O(1) space         |
| 70   | Climbing Stairs                    | Easy       | Linear DP, base cases             |
| 746  | Min Cost Climbing Stairs           | Easy       | 1D DP with cost                   |
| 198  | House Robber                       | Medium     | Take/skip pattern                 |
| 213  | House Robber II (circular)         | Medium     | Reducing to two linear DPs        |
| 53   | Maximum Subarray                   | Medium     | Kadane / collapsed DP             |
| 152  | Maximum Product Subarray           | Medium     | Two-state DP (track min and max)  |
| 62   | Unique Paths                       | Medium     | 2D grid DP                        |
| 64   | Minimum Path Sum                   | Medium     | 2D grid DP, in-place              |
| 120  | Triangle                           | Medium     | Bottom-up 2D                      |
| 91   | Decode Ways                        | Medium     | 1D DP with conditional transitions|
| AtCoder DP A (Frog 1) | Jumps min cost           | Easy       | Pure recurrence intro             |
| AtCoder DP B (Frog 2) | k-step jump              | Easy       | Generalized transitions           |

### TIER 2 — STANDARD INTERVIEW DP (the must-know 30)

| #    | Title                              | Difficulty | Teaches                                |
|------|------------------------------------|------------|----------------------------------------|
| 322  | Coin Change                        | Medium     | Unbounded knapsack, min variant        |
| 518  | Coin Change II                     | Medium     | Counting variant; loop order           |
| 416  | Partition Equal Subset Sum         | Medium     | 0/1 subset sum                         |
| 494  | Target Sum                         | Medium     | Subset sum reformulation               |
| 474  | Ones and Zeroes                    | Medium     | 2-D knapsack                           |
| 139  | Word Break                         | Medium     | 1D DP over prefixes + dictionary       |
| 300  | Longest Increasing Subsequence     | Medium     | LIS `O(n²)` and `O(n log n)`           |
| 673  | Number of LIS                      | Medium     | LIS + counting                         |
| 354  | Russian Doll Envelopes             | Hard       | LIS after sort                         |
| 1143 | Longest Common Subsequence         | Medium     | Canonical 2D LCS                       |
| 583  | Delete Operation for Two Strings   | Medium     | LCS reformulation                      |
| 72   | Edit Distance                      | Medium     | Canonical 2D string DP                 |
| 115  | Distinct Subsequences              | Hard       | Counting LCS variant                   |
| 97   | Interleaving String                | Medium     | 2D DP with three strings               |
| 5    | Longest Palindromic Substring      | Medium     | Interval DP / expand around center     |
| 516  | Longest Palindromic Subsequence    | Medium     | Interval DP, related to LCS(s, rev(s)) |
| 647  | Palindromic Substrings             | Medium     | Counting palindromes                   |
| 132  | Palindrome Partitioning II         | Hard       | 1D DP + palindrome precomputation      |
| 121  | Best Time to Buy/Sell Stock        | Easy       | 1-pass DP (Kadane-like)                |
| 122  | Buy/Sell II (unlimited)            | Medium     | State-machine, 2 states                |
| 123  | Buy/Sell III (≤ 2 trans.)          | Hard       | 4-state machine                        |
| 188  | Buy/Sell IV (k trans.)             | Hard       | Generalized k-trans state machine      |
| 309  | Buy/Sell with Cooldown             | Medium     | 3-state machine                        |
| 714  | Buy/Sell with Fee                  | Medium     | 2-state with adjusted transition       |
| 10   | Regular Expression Matching        | Hard       | 2D DP with `*` and `.`                 |
| 44   | Wildcard Matching                  | Hard       | 2D DP with `*` and `?`                 |
| 221  | Maximal Square                     | Medium     | 2D DP, `min` of three neighbours       |
| 85   | Maximal Rectangle                  | Hard       | DP + monotonic stack hybrid            |
| 740  | Delete and Earn                    | Medium     | Reduces to House Robber                |
| 343  | Integer Break                      | Medium     | 1D DP / math                           |
| 279  | Perfect Squares                    | Medium     | Unbounded coin change variant          |
| 264  | Ugly Number II                     | Medium     | Multi-pointer DP                       |

### TIER 3 — HARDER FAANG-LEVEL (multi-state, harder transitions)

| #    | Title                                       | Difficulty | Teaches                              |
|------|---------------------------------------------|------------|--------------------------------------|
| 312  | Burst Balloons                              | Hard       | Canonical interval DP, "last burst"  |
| 1547 | Min Cost to Cut a Stick                     | Hard       | Interval DP variant of MCM           |
| 1000 | Minimum Cost to Merge Stones                | Hard       | Interval DP with feasibility check   |
| 87   | Scramble String                             | Hard       | 3D interval DP with memoization      |
| 174  | Dungeon Game                                | Hard       | 2D DP, fill bottom-right to top-left |
| 741  | Cherry Pickup                               | Hard       | 4D → 3D state, two simultaneous walks|
| 1463 | Cherry Pickup II                            | Hard       | 3-D DP, two robots                   |
| 1639 | Number of Ways to Form Target String        | Hard       | 2D DP with multiplicity              |
| 1235 | Maximum Profit in Job Scheduling            | Hard       | DP + binary search                   |
| 1335 | Minimum Difficulty of Job Schedule          | Hard       | Interval-style DP                    |
| 1553 | Min Days to Eat N Oranges                   | Hard       | DP with memoization on huge state    |
| 1955 | Count Number of Special Subsequences        | Hard       | Counting DP with 4 states            |
| 2742 | Painting the Walls                          | Hard       | Reformulation as knapsack            |
| 920  | Number of Music Playlists                   | Hard       | Counting DP, two-dim recurrence      |
| 1220 | Count Vowels Permutation                    | Hard       | State-machine DP                     |
| 688  | Knight Probability                          | Medium     | Probability DP                       |
| 837  | New 21 Game                                 | Medium     | Probability DP + sliding window      |
| 808  | Soup Servings                               | Medium     | Probability DP + truncation          |
| 1289 | Minimum Falling Path Sum II                 | Hard       | DP + tracking top-2 mins             |
| 1937 | Maximum Number of Points with Cost          | Medium     | DP + prefix max optimization         |
| 1771 | Maximize Palindrome Length from Subsequences| Hard       | LCS-style with reconstruction        |
| 879  | Profitable Schemes                          | Hard       | 3D knapsack                          |

### TIER 4 — STRETCH TIER (advanced patterns + optimizations)

This is where mathematical maturity pays off. Each subsection treats one technique with its theoretical underpinning.

#### 4A. Bitmask DP (subset enumeration)

| #    | Title                                       | Difficulty | Teaches                            |
|------|---------------------------------------------|------------|------------------------------------|
| 847  | Shortest Path Visiting All Nodes            | Hard       | BFS/DP on `(mask, node)`           |
| 943  | Find the Shortest Superstring               | Hard       | TSP on overlap graph               |
| 698  | Partition to K Equal Sum Subsets            | Medium     | Bitmask DP / backtracking          |
| 1494 | Parallel Courses II                         | Hard       | Bitmask DP over course sets        |
| 1681 | Minimum Incompatibility                     | Hard       | Bitmask + sort                     |
| 526  | Beautiful Arrangement                       | Medium     | Permutation counting via bitmask   |
| 1815 | Maximum Number of Groups Getting Fresh Donuts| Hard      | Bitmask state on small modulus     |
| AtCoder DP O — Matching                     | Hard       | `dp[mask]` perfect matching count  |
| AtCoder DP U — Grouping                     | Hard       | Subset-sum-of-subsets DP           |

The **TSP / Held–Karp** template:
```
dp[mask][i] = min cost path that visits exactly the vertices in mask
              and ends at vertex i  (i ∈ mask)
dp[{i}][i] = 0  (or w(s,i) from a fixed source)
dp[mask | {j}][j] = min over i ∈ mask of  dp[mask][i] + w(i, j)
Answer: min_j dp[full][j] (+ w(j, s) for cycles)
Time O(2ⁿ · n²), Space O(2ⁿ · n)
```

#### 4B. Digit DP

Practice in this order: LC 233 → LC 600 → LC 902 → LC 1012 → CSES Counting Numbers → CF 628D *Magic Numbers* → SPOJ CPCRC1C / NUMTSN. Best tutorials: Codeforces blog 53960 (the canonical introduction), 77096 (iterative template), 95488 (memory tricks), 126971 (clean recursive idiom). USACO Guide *Digit DP* module.

#### 4C. Tree DP — Advanced (Rerooting)

| Problem                                                  | Source              |
|----------------------------------------------------------|---------------------|
| Sum of Distances in Tree (LC 834)                        | LeetCode Hard       |
| Minimum Height Trees (LC 310)                            | LeetCode Medium     |
| Tree Distances I & II                                    | CSES                |
| Choosing Capital for Treeland (CF 219D)                  | Codeforces 1700     |
| Maximum White Subtree (CF 1324F)                         | Codeforces 2000     |

The **rerooting template** (USACO Guide *DP on Trees — Solving for All Roots*; Codeforces blog 124286): two DFS passes — first computes `down[v]` (answer in subtree rooted at `v`), the second computes `ans[v]` by transferring information from parent (`up[v]`) using an associative combine operation. Total `O(n)` (or `O(n log n)` if combine requires segment-tree style structures).

#### 4D. DP on DAGs (longest path, counting paths)

`dp[v] = max/sum over edges (u,v) of dp[u] + w(u,v)`, in topological order.

| Problem                                       | Source              |
|-----------------------------------------------|---------------------|
| Longest Increasing Path in a Matrix (LC 329)  | LeetCode Hard       |
| Largest Divisible Subset (LC 368)             | LeetCode Medium     |
| Course Schedule III (LC 630)                  | LeetCode Hard       |
| Parallel Courses III (LC 2050)                | LeetCode Hard       |
| Game Routes (CSES)                            | CSES                |
| AtCoder DP G — Longest Path                   | AtCoder EDPC        |

#### 4E. DP Optimizations — the Mathematical Core

Three classical optimizations reduce a quadratic (or cubic) DP to near-linear under structural assumptions on the cost. All assume a recurrence of the form
`dp[i] = min_{j < i} ( dp[j] + C(j, i) )`
or, for interval DP,
`dp[i][j] = min_{i ≤ k < j} ( dp[i][k] + dp[k+1][j] + C(i,j) )`.

**(i) Convex Hull Trick (CHT).** Applies when the inner expression is *linear in some parameter of `i`*: `dp[j] + C(j, i) = m_j · x_i + b_j` for parameter `x_i`. Then querying `min_j (m_j x_i + b_j)` is asking for the lower envelope of an arrangement of lines evaluated at `x_i`. The lower envelope is itself a convex piecewise-linear function with at most `n` segments and can be:
   - **Maintained in `O(n)` total** (amortized) when slopes are monotonic *and* queries are monotonic — push/pop from a deque.
   - **`O(n log n)`** when only slopes are monotonic — binary search for the dominating line.
   - **Fully dynamic via Li Chao tree** in `O(n log n)` — segment tree where each node stores at most one line, persistent across queries (cp-algorithms.com/geometry/convex_hull_trick).

   Geometric intuition: each `(m_j, b_j)` is a point in line-coefficient space; the dominating lines correspond to vertices on the lower (or upper, for max) convex hull in dual space — exactly the same lower-envelope structure as the medial axis or LP duality.

   *Canonical practice problems*: APIO 2010 Commando (USACO Guide solution uses LineContainer/CHT), CEOI 2017 Building Bridges, CF 311B *Cats Transport*, USACO Guide platinum *Convex Hull Trick* module.

**(ii) Divide-and-Conquer Optimization.** Applies to `dp[i][j] = min_k ( dp[i-1][k] + C(k, j) )` when the optimal split `opt(i, j)` is monotonically non-decreasing in `j`: `opt(i, j) ≤ opt(i, j+1)`. A *sufficient* condition is the **quadrangle inequality** (Monge / total monotonicity): for all `a ≤ b ≤ c ≤ d`,
   `C(a, c) + C(b, d) ≤ C(a, d) + C(b, c)`
(equivalently: cross is at least as expensive as un-cross — the cost is supermodular on the product order). Under this, computing one full layer of `dp[i][·]` for fixed `i` runs in `O(n log n)`, giving overall `O(n² log n)` (or `O(n²)` with stronger hypotheses), down from `O(n³)`. The recursion (cp-algorithms.com/dynamic_programming/divide-and-conquer-dp.html): compute `opt(i, mid)` by scanning `[lo, hi]`, then recurse on `(lo, mid-1, lo, opt(i,mid))` and `(mid+1, hi, opt(i,mid), hi)`. Each `k` is visited `O(log n)` times.

   *Math comment*: The Monge property is precisely "submodularity for negated functions" and ties to the theory of polymatroids and Monge transportation. Yao (1980) / Knuth (1971) developed this rigorously.

   *Canonical*: CF 321E *Ciel and Gondolas*, CF 868F *Yet Another Minimization Problem*, CSES *Hotel Queries*, USACO Plat problems.

**(iii) Knuth's Optimization.** For interval DP `dp[i][j] = min_{i < k < j} ( dp[i][k] + dp[k][j] ) + C(i, j)`, if `C` is Monge *and* monotonic on intervals (`C(b,c) ≤ C(a,d)` for `a ≤ b ≤ c ≤ d`), then `opt(i, j-1) ≤ opt(i, j) ≤ opt(i+1, j)`. Restricting the inner search to this 2D-monotone window collapses `O(n³)` to `O(n²)`. Originally introduced by Knuth (1971) for optimal binary search trees.

   *Canonical*: Optimal BST (LC 1130 *Min Cost Tree from Leaf Values* — applicable variant), Merging Stones (LC 1000 satisfies a related structure), Brackets / Optimal Triangulation.

**(iv) Monotonic Deque / Sliding-Window Optimization.** When the recurrence is `dp[i] = min_{i-k ≤ j ≤ i-1} dp[j] + f(i)` with a fixed window `k`, a monotonic deque maintains the running min in amortized `O(1)` per step (LC 239 *Sliding Window Maximum* generalizes this). Reduces 1D DP from `O(nk)` to `O(n)`.

   *Canonical*: LC 1425 *Constrained Subsequence Sum*, LC 1696 *Jump Game VI*, AtCoder DP B (with monotone-deque speedup).

#### 4F. SOS DP (Sum Over Subsets)

Compute, for every mask `S ⊆ {0,…,n-1}`, `F(S) = Σ_{T ⊆ S} A(T)` in `O(n · 2ⁿ)` instead of the naïve `O(3ⁿ)`. The reference implementation (Codeforces blog 45223 by usaxena95):
```
F[mask] = A[mask] for all mask
for i in 0..n-1:
    for mask in 0..2ⁿ-1:
        if mask has bit i: F[mask] += F[mask ^ (1<<i)]
```
**Mathematical content**: this is the Zeta transform on the Boolean lattice `(2^[n], ⊆)`; its inverse is the Möbius transform (subtract instead of add). Subset-sum convolution `(f * g)(S) = Σ_{T ⊆ S} f(T) g(S\T)` runs in `O(n² · 2ⁿ)` by stratifying by popcount and using rank-1 zeta/Möbius (Björklund–Husfeldt–Koivisto, 2007). USACO Guide *Sum over Subsets DP* (`usaco.guide/plat/dp-sos`) reframes SOS as an n-dimensional prefix sum on the cube, which is the cleanest mental model.

   *Canonical*: CF problems with "for each mask, count something over its subsets", CSES *Bit Inversions*, CodeChef SOS-DP problems.

#### 4G. Profile DP / Broken Profile DP (tiling)

Tile an `N × M` grid with dominoes / trominoes / arbitrary pieces. State: `dp[i][j][mask]` where `mask` encodes the boundary ("profile") between filled and unfilled cells. Standard reference: cp-algorithms.com *profile-dynamics*; USACO Guide *DP on Broken Profile*; Codeforces blog 59282.

   *Canonical*: SPOJ M3TILE, CSES *Counting Tilings*, LC 1659 *Maximize Grid Happiness*, AtCoder DP M / Y are related.

#### 4H. Matrix Exponentiation for Linear Recurrences

When `f(n) = c_1 f(n-1) + … + c_k f(n-k) + (constant or polynomial of n)` and `n` up to `10¹⁸`, build the `(k+m) × (k+m)` transition matrix `T` and compute `T^n` in `O((k+m)³ log n)` via binary exponentiation (Codeforces blog 67776).

   *Canonical*: LC 70 *Climbing Stairs* (`O(log n)`), LC 1220 *Count Vowels Permutation* with huge `n`, CSES *Throwing Dice*, *Graph Paths*, problems involving Fibonacci mod `p`.

   *Math link*: this is just the Cayley–Hamilton theorem in disguise; for even faster `O(k² log n)` with FFT, use Kitamasa / Berlekamp–Massey to reduce powers of the companion matrix modulo the characteristic polynomial (Codeforces blog 97627).

#### 4I. DP with Bitset Optimization

When the DP table is boolean and the transition is "for each old reachable sum, also reach `sum + a_i`", encode the row as a `BitSet`/`std::bitset`; the transition becomes `dp |= dp << a_i`, costing `O(N/64)`. Knapsack-feasibility in `O(NW/64)` is the canonical use; `Σ a_i ≤ 10⁵`–`10⁶` fits comfortably. CSES *Money Sums*, LC 416 (overkill), ICPC subset-sum problems.

#### 4J. Persistent / "Open" DP

Maintain a persistent data structure (segment tree, trie) so that all historical DP states are queryable; useful in competitive programming, rare in interviews. Reference: Codeforces persistent segment tree blogs.

---

## PART 5 — PITFALLS AND DEBUGGING

### 5.1 Classic Mistakes

- **0-indexed vs 1-indexed table.** Edit-distance, LCS, knapsack work cleaner 1-indexed (`dp[0][·]` and `dp[·][0]` are natural base cases). Pick a convention and stick to it across the function.
- **Wrong direction in 1D-rolled knapsack.** 0/1 needs **descending** capacity loop; unbounded needs **ascending**. Otherwise you double-count.
- **Wrong loop nesting in coin change.** Counting *combinations*: coins outer, amount inner. Counting *permutations*/sequences: amount outer, coins inner. Min coins: either order works.
- **Reading uninitialized `dp[i'][j']` in bottom-up.** Verify the topological order: in interval DP iterate by `len`, in mask DP iterate `mask` increasing, in tree DP iterate post-order.
- **Initialization of `min` DP arrays.** Use `Int.MAX_VALUE / 2` (not `Int.MAX_VALUE`) so `dp[i] + 1` doesn't overflow. Better: `Long.MAX_VALUE / 4` or a sentinel `INF` constant and explicit check before transitioning.
- **Forgetting modulus in counting DP.** Apply `% MOD` after each addition (and after multiplications: `(a.toLong() * b % MOD).toInt()`).
- **Returning the wrong cell.** LIS: answer is `max(dp[i])`, not `dp[n-1]`. House Robber: `dp[n-1]`, not `dp[n]`. Edit distance: `dp[m][n]`. Always state the answer cell explicitly.
- **Top-down recursion stack overflow.** JVM stack ~512 KB; deep DP (e.g., `n = 10⁵`) blows it up. Either run on a dedicated thread with a bigger stack, or convert to bottom-up.

### 5.2 Signs Your State Is Wrong

- You find yourself passing more and more variables to the recursive call — you missed a state dimension at the start.
- The recurrence has a `for k in something` loop that itself "remembers" prior info — that info belongs in the state.
- Different paths to the same `(state)` give different answers — your state is *not* sufficient; the problem doesn't satisfy the Markov property under your encoding.
- Naively memoizing gives wrong answers on small cases — base cases or transitions are wrong; print the table for `n = 2, 3` and compare to brute force.

### 5.3 When to Add a Dimension

Add a state dimension when:

- A boolean condition affects future transitions (cooldown active? holding stock? leading-zero in digit DP? "tight" flag).
- A counter matters (transactions used, deletions remaining, k partitions made).
- The "previous element" or "last move" affects what's legal now (e.g., LC 376 *Wiggle Subsequence* with up/down state).

### 5.4 Memoization in Kotlin / Java — Practical Patterns

**Preferred for fixed-size integer states**: typed arrays with a sentinel for "uncomputed":
```kotlin
val memo = Array(n + 1) { IntArray(W + 1) { -1 } }
fun rec(i: Int, w: Int): Int {
    if (i == 0 || w == 0) return 0
    if (memo[i][w] != -1) return memo[i][w]
    var best = rec(i - 1, w)
    if (weight[i - 1] <= w)
        best = maxOf(best, rec(i - 1, w - weight[i - 1]) + value[i - 1])
    memo[i][w] = best
    return best
}
```

**For sparse state or non-integer keys**: `HashMap<Pair<Int, Int>, Int>` or `HashMap<Long, Int>` with bit-packing:
```kotlin
val key = (i.toLong() shl 20) or j.toLong()  // when both fit in 20 bits
```
Bit-packing into a `Long` is materially faster than `Pair` because `Pair.hashCode()` allocates and the `Long` key avoids boxing. For three or more dimensions, consider a `LongArray` indexed by a flattened linear index.

**For boolean reachability over very large sums**: `java.util.BitSet`, transition is `dp.or(dp.shiftLeft(coin))` — but Java's `BitSet` doesn't have `shiftLeft`; you either implement `or` of a shifted copy manually, or import a library. Kotlin's `kotlin.collections.BitSet` (from kotlin-stdlib-jdk7) is the same `java.util.BitSet`.

**Pitfall**: Kotlin lambdas captured by `lateinit var` for top-down recursion incur a small overhead; for hot interview loops convert to explicit `fun rec(...)` to let HotSpot inline.

### 5.5 Top-Down → Bottom-Up Conversion

Mechanical procedure:
1. Identify all parameters `p₁, …, p_k` of the recursive function — those are the table dimensions.
2. Identify the base cases and write them as initialization.
3. Determine the partial order: in the recursion, `rec(s)` depends on `rec(s')` — therefore in the table, fill `s'` before `s`. Translate this to nested loops.
4. Replace each `rec(s')` by `dp[s'.indices]`.
5. The final answer is `dp[answer-state]`.

Then *immediately* apply space optimization: keep only the rows of `dp` actually referenced.

### 5.6 Space Optimization Cookbook

- **`dp[i]` depends only on `dp[i-1]`** → two scalars (or two 1D arrays in 2D problems). House Robber: 2 scalars.
- **`dp[i][j]` depends only on row `i-1`** → two 1D arrays of length `m+1`. LCS, edit distance.
- **0/1 knapsack** → 1 array of length `W+1`, iterate `w` from `W` down to `weight[i]`.
- **Unbounded knapsack** → 1 array of length `W+1`, iterate `w` from `weight[i]` up to `W`.
- **Interval DP** → typically can't be space-optimized below `O(n²)`.
- **Bitmask DP** with transition only adding one bit → in-place over `mask` works if you iterate by popcount.

---

## PART 6 — REFERENCES

### 6.1 Curated Problem Sets (the gold standard)

- **AtCoder Educational DP Contest ("EDPC")**: 26 problems A–Z, each illustrating a distinct DP technique. The most efficient single-set practice for DP — finishing it leaves you fluent in tree DP, bitmask DP, digit DP, probability DP, and matrix exponentiation. URL: `https://atcoder.jp/contests/dp`. Editorials: Neo Wang & Dong Liu's at `https://nwatx.me/post/atcoderdp`. Video editorials: Errichto's stream (Codeforces blog 65292) and Nachiket Kanore's full series (Codeforces blog 122422).
- **CSES Problem Set — Dynamic Programming section** (~22 problems): `https://cses.fi/problemset/` (DP section). Editorials: Codeforces blog 70018. Definitive bottom-up practice.
- **USACO Guide DP modules** (free, regularly updated): `https://usaco.guide/gold/intro-dp` (Gold tier), with deeper modules at `https://usaco.guide/plat` for *Convex Hull Trick*, *Divide & Conquer DP*, *Sum over Subsets*, *DP on Broken Profile*, *DP on Trees — All Roots*. The Plat tier maps almost 1-1 onto the Stretch Tier above.
- **LeetCode DP Study Plan**: `https://leetcode.com/studyplan/dynamic-programming/` — official ladder of ~35 problems.
- **NeetCode 150 / 250**: `https://neetcode.io/practice` — DP section has 23 (NC150) / ~40 (NC250) hand-picked problems with video solutions.
- **Codeforces tag `dp` filtered by rating**: `1500–1900` for Tier 2 prep, `2000–2400` for Tier 3/4.

### 6.2 Influential YouTube Curricula (FAANG-prep specific)

- **Aditya Verma — DP Playlist** (~50 videos): `https://www.youtube.com/playlist?list=PL_z_8CaSLPWekqhdCPmFohncHwz8TY2Go`. Categorizes DP into 6–7 super-patterns: 0/1 Knapsack, Unbounded Knapsack, LCS, LIS, Kadane, MCM (Matrix Chain / Interval DP), DP on Trees, DP on Grids. The *recursion → memoization → tabulation → space-optimized* progression he drills is highly effective for interview readiness; widely regarded as the best YouTube DP series for the FAANG audience. His Medium summary "Learn Top 10 Dynamic Programming Patterns" (`aditya-verma-manit.medium.com`) is a useful refresher.
- **Striver / takeUforward — DP Series** (~56 videos): `https://www.youtube.com/playlist?list=PLgUwDviBIf0qUlt5H_kiKYaNSqJ81PMMY`, lecture notes at `https://takeuforward.org/dynamic-programming/striver-dp-series-dynamic-programming-problems`. Very thorough; covers DP on subsequences, strings, grids, stocks, LIS, MCM/Partition DP including Burst Balloons. Java + C++ code provided.
- **NeetCode** — concise per-problem videos linked from the roadmap; less systematic than Aditya/Striver but excellent for individual problems.
- **Errichto** — AtCoder DP Contest 5-hour stream + CP school videos (`youtube.com/errichto`). Less hand-holdy but technically deep.

### 6.3 Books / Long-form Written References

- **Antti Laaksonen, *Competitive Programmer's Handbook*** (free PDF: `https://cses.fi/book/book.pdf`). Chapter 7 (Dynamic Programming) is concise and rigorous; read alongside Chapter 25 (*DP optimizations* in the expanded *Guide to Competitive Programming*, Springer 2024 edition).
- **Jeff Erickson, *Algorithms*** (free: `https://jeffe.cs.illinois.edu/teaching/algorithms/`). Chapter 3 (Dynamic Programming) is the best textbook chapter on DP currently in print; Appendix D (Advanced Dynamic Programming) covers Hirschberg's algorithm, total monotonicity, SMAWK, and Monge matrices — directly relevant to the Stretch Tier and aligned with your math background.
- **Steven Skiena, *Algorithm Design Manual* (3rd ed., Springer 2020)**. Chapter 10 (DP) has the famous "war stories" and a programmer-oriented presentation. Slides at `https://www3.cs.stonybrook.edu/~skiena/392/newlectures/week11.pdf`.
- **Kleinberg & Tardos, *Algorithm Design***. Chapter 6 has the cleanest treatment of weighted interval scheduling, segmented least squares, sequence alignment with linear space (Hirschberg), and Bellman–Ford as DP.
- **Cormen/Leiserson/Rivest/Stein, *Introduction to Algorithms*** (CLRS), Chapter 15.

### 6.4 Codeforces / cp-algorithms Tutorials (technique-specific)

- **cp-algorithms.com** (the de facto English wiki):
  - *Knapsack / 0-1 / unbounded*: `cp-algorithms.com/dynamic_programming/`
  - *Divide and Conquer DP*: `cp-algorithms.com/dynamic_programming/divide-and-conquer-dp.html`
  - *Convex Hull Trick / Li Chao tree*: `cp-algorithms.com/geometry/convex_hull_trick.html`
  - *DP on Broken Profile*: `cp-algorithms.com/dynamic_programming/profile-dynamics.html`
- **Codeforces — DP Tutorial and Problem List** (Ahnaf.Shahriar.Asif): `https://codeforces.com/blog/entry/67679` — meta-list of tutorials.
- **Codeforces — DP Optimizations** (mukel): `https://codeforces.com/blog/entry/8219` — the original blog cataloging Knuth, divide-and-conquer, and CHT conditions.
- **SOS DP** (usaxena95): `https://codeforces.com/blog/entry/45223` and the elegant follow-up "SOS DP as N-dimensional prefix sums": `https://codeforces.com/blog/entry/105247`.
- **Zeta / Möbius / Subset Sum Convolution**: `https://codeforces.com/blog/entry/72488`.
- **Digit DP (recursive)**: `https://codeforces.com/blog/entry/53960` (Sumeet Varma's intro), iterative variant: `https://codeforces.com/blog/entry/77096`, tricks: `https://codeforces.com/blog/entry/95488`.
- **Broken Profile DP**: `https://codeforces.com/blog/entry/59282`.
- **Convex Hull Trick — interactive tutorial** (Xellos / meooow): `https://codeforces.com/blog/entry/63823`.
- **Matrix Exponentiation**: `https://codeforces.com/blog/entry/67776`; faster via FFT: `https://codeforces.com/blog/entry/97627`.
- **Tree Rerooting DP — template**: `https://codeforces.com/blog/entry/124286`.

### 6.5 Hello Interview / Tech-Interview-Specific

- **Hello Interview — Dynamic Programming module**: `https://www.hellointerview.com/learn/code/dynamic-programming/fundamentals` — a polished, FAANG-focused tutorial covering fundamentals, the 7-step approach, and worked problems (Climbing Stairs, House Robber, Unique Paths, Maximal Square, Word Break). Excellent for the *interview communication patterns* — how to verbalize state design and recurrence to an interviewer.
- **Tech Interview Handbook — DP cheatsheet**: `https://www.techinterviewhandbook.org/algorithms/dynamic-programming/`.
- **interviewing.io — DP for senior engineers**: `https://interviewing.io/dynamic-programming-interview-questions`.
- **LeetCode Discuss canonical posts**:
  - "Dynamic Programming Patterns" (15k+ upvotes): `https://leetcode.com/discuss/study-guide/458695/dynamic-programming-patterns`.
  - "DP for Beginners — Patterns | Sample Solutions": `https://leetcode.com/discuss/general-discussion/662866/`.
  - "5 steps to think through DP questions" (template post): widely reproduced; good template-repetition resource.

### 6.6 Mathematical / Theoretical Background (for the math-PhD reader)

- **F. F. Yao**, *Efficient dynamic programming using quadrangle inequalities* (1980) and *Speed-up in Dynamic Programming* — the foundational papers behind Knuth's optimization and divide-and-conquer DP.
- **Knuth**, *Optimum binary search trees* (Acta Informatica, 1971) — original `O(n²)` algorithm via the monotonicity-of-roots property.
- **Galil & Park**, *A Linear-Time Algorithm for Concave One-Dimensional Dynamic Programming* — SMAWK and totally monotone matrices.
- **Björklund, Husfeldt, Kaski, Koivisto**, *Fourier meets Möbius: fast subset convolution* (STOC 2007) — the rigorous treatment of SOS / subset-sum convolution.
- **Erickson, Appendix D**, on Monge arrays and total monotonicity (`https://jeffe.cs.illinois.edu/teaching/algorithms/notes/D-faster-dynprog.pdf`) — most accessible bridge from interview-tier DP to research-tier optimizations.

---

## A 12-Week Study Plan (Suggested)

| Week  | Focus                                                  |
|-------|--------------------------------------------------------|
| 1     | Tier 1 (all). Internalize Part 2 recipe on every prob. |
| 2–3   | Tier 2: Linear / Knapsack / Coin Change families.      |
| 4     | Tier 2: LIS / LCS / Edit Distance.                     |
| 5     | Tier 2: Grid + Stocks (state-machine).                 |
| 6     | Tier 2: Palindromes + Regex/Wildcard. Re-do Tier 1 cold.|
| 7     | Tier 3: Interval DP (Burst Balloons, Merge Stones, Stick).|
| 8     | Tier 3: Multi-walker grid (Cherry Pickup), counting DP.|
| 9     | Tier 4A–4B: Bitmask DP + Digit DP.                     |
| 10    | Tier 4C–4D: Tree rerooting + DAG DP.                   |
| 11    | Tier 4E: CHT + D&C optimization + Knuth (math-heavy).  |
| 12    | Tier 4F–4H: SOS DP, Profile DP, Matrix exponentiation. |

Solve daily with a 25-minute timer; if stuck, read the editorial, then implement from scratch the next day. Aim for ~70 problems total; quality of recall > raw count.

---

## Caveats

- **Aditya Verma's "patterns" classification is pedagogically influential but not a formal taxonomy.** It is excellent for *building intuition* (especially the recursion-first → memo → tab → space progression), but real interview problems often combine 2–3 patterns. Treat it as scaffolding to discard once you can derive recurrences from first principles via Part 2.
- **The 7-step recipe in Part 2 is a discipline, not a guarantee.** Some problems require a non-obvious state encoding (e.g., LC 87 *Scramble String* parameterizing by length rather than two indices, or LC 1278 *Palindrome Partitioning III* with a clever min-changes precomputation) where mechanical application of "what carries forward" gives a too-large state. When stuck, search for *invariants*: what *doesn't* change as you make decisions — that's often a hint the state can be compressed.
- **Stretch Tier optimizations are interview-rare but staff-level differentiating.** CHT, D&C optimization, SOS DP, broken profile DP, and Knuth's optimization almost never appear in standard SWE loops. They *do* appear in (i) competitive programming, (ii) Google's harder loops and Jane Street / Citadel quant interviews, (iii) systems-research and optimization-flavored team rounds. For pure SWE FAANG prep, Tiers 1–3 plus 4A–4D are sufficient; 4E–4H are bonus that pays back as deeper algorithmic understanding even if never directly asked.
- **Constraints are noisy on dates/recency.** AtCoder EDPC was a 2019 contest but is the canonical practice set as of 2026; CSES is continuously updated; USACO Guide is actively maintained (note the "Updated: Last week" markers visible on its modules). Some Codeforces tutorials cited here are 4–8 years old but remain authoritative because the techniques themselves are stable.
- **Kotlin-specific note.** All major Kotlin idioms for memoization (typed arrays + `-1` sentinel; `HashMap<Pair<Int,Int>, Int>`; bit-packed `Long` keys) work but allocation costs differ. For tight `O(n²)` DPs at `n = 10⁴`, prefer raw `IntArray`/`LongArray` over `HashMap`; a 5–10× speedup is typical. For deep recursion (`n > 10⁴`), wrap top-down code in `Thread(null, runnable, "dp", 1 shl 26).start()` or convert to bottom-up to avoid `StackOverflowError`.
- **The math-PhD lens helps most on the optimization tier.** CHT = lower envelope of an arrangement; Monge / quadrangle inequality is supermodularity on the product order; SOS DP is the Zeta transform on the Boolean lattice (with Möbius as inverse); matrix exponentiation invokes the Cayley–Hamilton theorem; Sprague–Grundy reduces impartial games to nimbers in `(ℤ_{≥0}, ⊕)`. These connections are not interview decoration — they make the algorithms self-evidently correct and easier to recall under pressure.