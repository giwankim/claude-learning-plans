---
title: "A Comprehensive Guide to Mastering Binary Search for FAANG Interviews"
category: "Algorithms & Problem Solving"
description: "Single canonical template (half-open `[lo, hi)` predicate search) plus a three-tier problem ladder (foundations → modified arrays → binary-search-on-the-answer) and curated 2025–2026 reading list for a senior engineer converting logarithmic intuition into bug-free interview code"
---

# A Comprehensive Guide to Mastering Binary Search for FAANG Interviews

A focused playbook for a senior backend engineer (Kotlin/Spring, math PhD) who needs to convert a deep instinct for "the answer is logarithmic" into reliably bug-free interview code. The guide is organized in three parts: a conceptual framework, a curated problem ladder, and a curated reading list.

---

## TL;DR

- **Adopt a single template — the "find the leftmost `lo` such that `predicate(lo)` is True" pattern (the half-open `[lo, hi)` form popularized by zhijun_liao on LeetCode and by competitive programmers like Errichto and the USACO Guide).** Every binary search interview problem — sorted-array search, lower/upper bound, rotated arrays, 2D matrices, "Koko"-style parametric search, even median-of-two-sorted-arrays — collapses to choosing a search space and a monotone predicate. Stop memorizing variants; memorize one template plus the recipe for designing the predicate.
- **Climb the ladder in three tiers.** (1) Foundations: 704, 35, 278, 34, 69, 367. (2) Modified arrays: 33 → 81 → 153 → 154 → 162 → 540 → 74 → 240. (3) Binary-search-on-the-answer: 875 → 1011 → 1283 → 1482 → 410/1231 → 2517 → 2560 → 1898 → 668 → 378 → 719 → 4. This sequence is exactly what NeetCode, Striver, and the LeetCode "Binary Search Study Plan" converge on, with each rung adding exactly one new mental hook.
- **The 2025–2026 best-in-class resources are: the zhijun_liao "Powerful Ultimate Binary Search Template" post, Errichto's 30-minute Codeforces lecture, Hello Interview's Binary Search module, NeetCode's free Binary Search playlist + neetcode.io solution pages, Striver's TUF binary search playlist, the USACO Guide silver-tier "Binary Search" module, Antti Laaksonen's *Competitive Programmer's Handbook* (Ch. 3), Skiena's *Algorithm Design Manual* (§4.9 / §5.1), and the LeetCode official "Binary Search" 8-pattern study plan.** Skip the Topcoder article only if short on time; it's still the canonical "predicate-based" treatment.

---

## Key Findings

1. **There is broad consensus on a single canonical template.** The most-cited LeetCode template (zhijun_liao, 425k+ views), the USACO Guide's `firstTrue`/`lastTrue`, AlgoMonster's "first true in a sorted boolean array," labuladong's "left bound" framework, Hello Interview's pointer-update guide, and Errichto's lecture all describe the same idea: maintain a monotone boolean predicate over an integer interval and binary-search the transition point. The half-open `while (lo < hi)` / `right = mid` / `left = mid + 1` form is the most foolproof because there is never an off-by-one in the update step and `lo == hi` is the unique invariant at exit.
2. **"Binary search on the answer" is just the ordinary template applied to a derived predicate.** If you can phrase the problem as "find min/max X such that `feasible(X)`," and `feasible` is monotone in X, you binary-search the answer space. Koko, Capacity to Ship, Split Array Largest Sum, Smallest Divisor, Bouquets, Aggressive Cows, Painter's Partition, House Robber IV, Tastiness of Candy Basket, Divide Chocolate, Minimum Time to Repair Cars, and Maximum Removable Characters are all instances of the same recipe.
3. **Rotated-array problems reduce to one invariant: at each step, exactly one half is sorted; decide which, then ask if the target lies inside its sorted range.** Duplicates (LC 81/154) break this when `nums[lo] == nums[mid] == nums[hi]`; the standard fix is to shrink both ends by one (degrading the worst case to O(n)).
4. **Median of Two Sorted Arrays (LC 4) is the apex problem** — but it is essentially "binary-search the partition index in the smaller array," reusing the same template. Once you can do LC 410 and LC 719, LC 4 becomes a partition exercise rather than a new technique.
5. **The most modern, FAANG-targeted resource in 2025–2026 is Hello Interview's Binary Search module**, which adds interview-style narration (e.g., "Apple Harvest" = Koko renamed) on top of the standard NeetCode 150 / takeUforward content. For raw competitive-programming rigor, Errichto's lecture and the USACO Guide remain unmatched.

---

## Details

### Part 1 — Conceptual Framework

#### 1.1 The Universal Mental Model

Every binary search problem, no matter how exotic, fits this schema:

> *Given a search space `S = {lo, lo+1, …, hi}` and a predicate `P : S → {False, True}` that is monotone (once it flips it stays flipped), find the boundary index where `P` flips.*

The two primitives are:
- **`firstTrue(lo, hi, P)`** — smallest `x ∈ [lo, hi]` with `P(x) == True`. Returns `hi+1` if no such x.
- **`lastTrue(lo, hi, P)`** — largest `x` with `P(x) == True`. Returns `lo-1` if no such x.

Everything else is sugar:
| Problem type | What is `S`? | What is `P(x)`? | Which primitive? |
|---|---|---|---|
| Search target in sorted array | array indices | `nums[x] >= target` | `firstTrue`; check equality after |
| Lower bound (LC 35) | `[0, n]` | `nums[x] >= target` | `firstTrue` |
| Upper bound | `[0, n]` | `nums[x] > target` | `firstTrue` |
| First / last occurrence (LC 34) | indices | first: `nums[x] >= target`; last: `nums[x] > target` then subtract 1 | both |
| First Bad Version (LC 278) | `[1, n]` | `isBadVersion(x)` | `firstTrue` |
| Sqrt(x) (LC 69) | `[0, x]` | `m*m > x` | `firstTrue` then subtract 1 |
| Find Peak (LC 162) | `[0, n-1]` | `nums[x] > nums[x+1]` (the peak is at the first such x) | `firstTrue` |
| Find min in rotated array (LC 153) | `[0, n-1]` | `nums[x] <= nums[hi]` | `firstTrue` |
| Koko Eating Bananas (LC 875) | `[1, max(piles)]` | `hoursNeeded(speed) <= h` | `firstTrue` |
| Capacity to Ship (LC 1011) | `[max(weights), sum(weights)]` | `daysNeeded(cap) <= D` | `firstTrue` |
| Split Array Largest Sum (LC 410) | `[max(nums), sum(nums)]` | `subarraysNeeded(maxSum) <= k` | `firstTrue` |
| Divide Chocolate (LC 1231) — *maximize* | `[min(s), sum(s)]` | `cuts(minSweet) >= k+1` | `lastTrue` |

#### 1.2 The Recommended Template (Kotlin)

This is the half-open `firstTrue` template, the one zhijun_liao popularized and the form Errichto, USACO, AlgoMonster, and Hello Interview all teach. It works on any monotone predicate without modification.

```kotlin
// Returns the smallest x in [lo, hi] such that p(x) is true.
// Returns hi + 1 if no such x exists. p must be monotone (false…falseTrue…true).
inline fun firstTrue(lo: Int, hi: Int, p: (Int) -> Boolean): Int {
    var l = lo
    var r = hi + 1                 // half-open: search interval is [l, r)
    while (l < r) {
        val m = l + (r - l) / 2    // overflow-safe midpoint
        if (p(m)) r = m            // m might be the answer; keep it
        else      l = m + 1        // m is definitely not the answer
    }
    return l                       // l == r at exit
}

// Symmetric helper for "last true": largest x with p(x) true.
inline fun lastTrue(lo: Int, hi: Int, p: (Int) -> Boolean): Int =
    firstTrue(lo, hi) { x -> !p(x) } - 1
```

**Why this template is recommended over the inclusive `while (l <= r)` style:**
- The loop invariant (`l <= true-boundary <= r`) is unambiguous.
- There is *one* update rule: `l = m + 1` (failure) or `r = m` (possible success). You never write `r = m - 1`.
- It eliminates the most common interview bug — infinite loops when you write `l = m` instead of `l = m + 1` because integer division floors mid toward `l`.
- It generalizes verbatim from arrays to "binary search on the answer."

The classic inclusive template (`l <= r`, `r = mid - 1`, `l = mid + 1`, return target index or -1) is fine for the literal "search a value" case (LC 704), and labuladong's framework defends it well, but every problem with boundaries (lower_bound, leftmost, rightmost, parametric) becomes simpler with the half-open form. **Pick one and use it everywhere.**

#### 1.3 Pitfalls (and how the template avoids them)

- **Integer overflow:** always `m = l + (r - l) / 2`, never `(l + r) / 2`. In Kotlin on `Int` this matters when `l + r` exceeds `Int.MAX_VALUE` (e.g., LC 410 search space `sum(nums)` can be 10^9 and the test `l + r` reaches 2·10^9). Use `Long` if `r` itself can exceed 2^30.
- **Infinite loop:** happens when neither bound makes progress. With the half-open template, `l = m + 1` always advances `l`, and `r = m` strictly shrinks `[l, r)` because `m < r` whenever `l < r`. Bug-free by construction.
- **Off-by-one in search space:** for "find a value in indices `[0, n)`," set `hi = n - 1`. For lower_bound (where the answer can be `n`, meaning "insert at end"), set `hi = n`. Always ask: *what is the largest index that can legally be the answer?*
- **Predicate non-monotonicity:** the #1 cause of "binary search gives wrong answer." Before coding, prove monotonicity. For Koko, "if speed `k` works, every `k' > k` also works." For Split Array, "if max-sum `S` is feasible with `k` parts, every `S' > S` is feasible." If you can't articulate this, binary search will silently fail.
- **Choosing wrong ends of the search space.** Too narrow misses the answer; too wide is fine but wasteful. Standard widths:
  - Koko: `[1, max(piles)]`
  - Ship Packages / Split Array: `[max(nums), sum(nums)]`
  - Smallest Divisor: `[1, max(nums)]`
  - Bouquets: `[min(bloomDay), max(bloomDay)]`
  - Pair Distance (LC 719): `[0, max(nums) - min(nums)]`
  - Kth in Multiplication Table (LC 668): `[1, m*n]`
- **Returning `lo` vs `hi`:** with the half-open template, `lo == hi` at exit and you return `lo`. If the answer is "the largest `x` for which P holds" (a `lastTrue`), it's `lo - 1`. If `P` may be false everywhere, you must check `lo > hi` (or equivalent) before using `nums[lo]`.

#### 1.4 Mental Model for Rotated Sorted Arrays (LC 33, 81, 153, 154)

The single invariant: *at any iteration of binary search on a rotated sorted array, the element `nums[mid]` lies in either the "left sorted run" or the "right sorted run." Compare `nums[mid]` to `nums[lo]` (or `nums[hi]`) to discover which.*

Algorithm for **LC 33 (no duplicates):**
```
while (lo <= hi):
    mid = lo + (hi - lo) / 2
    if nums[mid] == target: return mid
    if nums[lo] <= nums[mid]:                     # left half is sorted
        if nums[lo] <= target < nums[mid]:        # target inside left
            hi = mid - 1
        else: lo = mid + 1
    else:                                         # right half is sorted
        if nums[mid] < target <= nums[hi]:
            lo = mid + 1
        else: hi = mid - 1
```

**Two-pass alternative (cleaner for many people):** binary-search for the pivot index (LC 153), then binary-search the appropriate half. This decomposes one tricky search into two textbook searches and is what Errichto recommends in his lecture commits.

**For LC 81 / 154 (duplicates):** when `nums[lo] == nums[mid] == nums[hi]`, you cannot decide which half is sorted; shrink both ends by one (`lo++; hi--`) and continue. Worst case becomes O(n) — this is unavoidable and is a common follow-up question.

For **LC 153 / Find Minimum in Rotated Sorted Array**, the cleanest framing is the predicate `P(x) = nums[x] <= nums[hi]`, which is monotone false→true in the rotated array, and `firstTrue` returns the pivot directly. This is the same template, no special case.

#### 1.5 The "Binary Search on the Answer" Recipe

A drop-in five-step procedure (zhijun_liao's framing, refined by NeetCode and Hello Interview):

1. **Identify the numeric answer.** Read the question — the thing you return. Speed (Koko), capacity (Ship), max-sum (Split), min-distance (Aggressive Cows), tastiness (LC 2517), wealth threshold (LC 2560 House Robber IV), etc.
2. **Establish bounds.** Lower bound = the smallest value that could conceivably work. Upper bound = something definitely large enough. Common idioms above.
3. **Write `feasible(x): Boolean`.** Usually a single linear pass with greedy accumulation (Koko/Ship/Split/Bouquets all share this skeleton). For counting problems (LC 668, 378, 719) it's a "count of values ≤ x" function, often using two pointers, sorted-array prefix counts, or per-row arithmetic.
4. **Verify monotonicity.** Articulate: "if `feasible(x)` is true, why is `feasible(x+1)` true?" (or vice versa for max-problems). If you can't, the technique doesn't apply.
5. **Plug into `firstTrue` / `lastTrue`.** That's it. The template doesn't change.

This recipe is exactly what's taught in: zhijun_liao's LeetCode post, the Codeforces "Binary Search on the Answer" blog (entry/143038), the USACO Guide silver section, and Hello Interview's "Apple Harvest" walk-through.

---

### Part 2 — Curated Problem Ladder

Each rung adds *one* new idea. Solve in order; do not skip. Difficulty in parentheses is LeetCode's.

#### Tier 1 — Foundations (template fluency)
| # | Problem | Diff | What it teaches |
|---|---|---|---|
| 704 | Binary Search | Easy | The literal template; baseline reps. |
| 35 | Search Insert Position | Easy | First problem where the answer can be `n` (lower_bound). Use `hi = n`. |
| 278 | First Bad Version | Easy | The pure abstract `firstTrue` problem — predicate is given. |
| 374 | Guess Number Higher or Lower | Easy | Same as 278 but explicit ternary feedback. |
| 69 | Sqrt(x) | Easy | First "binary search on a numeric answer" — search `[0, x]` for the largest m with m·m ≤ x. Practice overflow-safe products (use `Long`). |
| 367 | Valid Perfect Square | Easy | Variant of 69 with equality check. |
| 34 | Find First and Last Position | Medium | Two binary searches: `firstTrue(nums[x] >= target)` and `firstTrue(nums[x] > target) - 1`. The cleanest demonstration of the template's power. |

#### Tier 2 — Modified Sorted Arrays (the predicate isn't directly the array)
| # | Problem | Diff | What it adds |
|---|---|---|---|
| 162 | Find Peak Element | Medium | Local invariant: predicate `nums[x] > nums[x+1]` is monotone false→true. Demonstrates that monotonicity does not require a globally sorted array. |
| 852 | Peak Index in a Mountain Array | Easy | Same as 162 with a guarantee — pure ramp-up. |
| 540 | Single Element in Sorted Array | Medium | Monotone predicate on parity of indices. Subtle but uses the exact template. |
| 153 | Find Minimum in Rotated Sorted Array | Medium | Predicate `nums[x] <= nums[hi]`. Foundational rotated-array intuition. |
| 33 | Search in Rotated Sorted Array | Medium | The "which half is sorted" mental model. |
| 154 | Find Minimum in Rotated Sorted Array II | Hard | Adds the duplicate degeneracy → O(n) worst case via `lo++; hi--`. |
| 81 | Search in Rotated Sorted Array II | Medium | Same duplicate twist applied to LC 33. |
| 74 | Search a 2D Matrix | Medium | Treat the matrix as a flattened sorted array; index map `row = m / cols`, `col = m % cols`. |
| 240 | Search a 2D Matrix II | Medium | Different structure (rows + columns sorted but no global order). Use **staircase search from top-right** in O(m+n) — and learn when binary search does *not* apply directly. |
| 658 | Find K Closest Elements | Medium | Binary-search the *left edge* of a window of size k; great practice for non-obvious predicates. |
| 875 | Koko Eating Bananas | Medium | The canonical "binary search on the answer" introduction. |

#### Tier 3 — Binary Search on the Answer (the bread and butter)
| # | Problem | Diff | What it adds |
|---|---|---|---|
| 1011 | Capacity to Ship Packages Within D Days | Medium | Same shape as Koko but predicate computes "days needed" rather than "hours needed." Cementing pattern recognition. |
| 1283 | Find the Smallest Divisor Given a Threshold | Medium | The predicate is given near-verbatim by the problem; trains you to recognize the pattern from the problem statement alone. |
| 1482 | Minimum Number of Days to Make m Bouquets | Medium | First problem where `feasible` is non-trivial (consecutive-flowers counting). |
| 410 | Split Array Largest Sum | Hard | Same recipe as 1011 with a tighter constraint; also solvable by DP — the comparison teaches *when* binary search beats DP (here: O(n log S) vs O(n²k)). |
| 1231 | Divide Chocolate | Hard | Maximizing the minimum (the dual flavor). Use `lastTrue` instead of `firstTrue`. |
| 2064 | Minimized Maximum of Products Distributed to Any Store | Medium | Recipe-identical to 1011, lower constraints. |
| 1760 | Minimum Limit of Balls in a Bag | Medium | Slightly trickier `feasible` (operation count). |
| 2187 | Minimum Time to Complete Trips | Medium | Predicate is sum of `time/t` — extremely common interview shape. |
| 2226 | Maximum Candies Allocated to K Children | Medium | Maximize-the-minimum, simple feasibility. |
| 2517 | Maximum Tastiness of Candy Basket | Medium | Maximize min pairwise distance after sorting. Greedy feasibility. |
| 2560 | House Robber IV | Medium | Binary-search the "capability"; `feasible` uses 1-D DP/greedy. Demonstrates that the inner check itself can be a non-trivial algorithm. |
| 1898 | Maximum Number of Removable Characters | Medium | Binary-search the *count* of removals; predicate uses two-pointer subsequence check. Excellent FAANG-style pivot from "search an array" to "search an integer parameter of an arbitrary problem." |

#### Tier 4 — Advanced (k-th element, partitions, hardest variants)
| # | Problem | Diff | What it adds |
|---|---|---|---|
| 378 | Kth Smallest Element in a Sorted Matrix | Medium | Binary-search the *value*; `feasible(v)` counts entries ≤ v in O(n) via staircase. |
| 668 | Kth Smallest Number in a Multiplication Table | Hard | Same idea as 378 but the count is computed arithmetically per row in O(m). |
| 719 | Find K-th Smallest Pair Distance | Hard | Binary-search on the distance value with a sliding-window count. Most ICs find this the hardest "value-search" problem. |
| 4 | Median of Two Sorted Arrays | Hard | The capstone. Binary-search the partition index in the smaller array; learn the partition invariants `maxLeft1 <= minRight2` and `maxLeft2 <= minRight1`. |
| 302 | Smallest Rectangle Enclosing Black Pixels | Hard | Four nested binary searches over coordinates; great for spatial-binary-search intuition. |
| 1539 | Kth Missing Positive Number | Easy → Medium with binary search | A subtle predicate on "how many missing before index x." |
| 1539, 644, 786 | Various "k-th"-type | Hard | Repetition is the point: by now the recipe should feel automatic. |
| 1095 | Find in Mountain Array | Hard | Three binary searches: peak, left half, right half. Combines Tiers 2 and 3. |

**Practice cadence (recommended for a 10-yr veteran):** Tier 1 in one evening; Tier 2 over 3–4 evenings; Tier 3 over a week (one new problem per evening, redo the previous day's first); Tier 4 over a second week. Total ~3 weeks of focused work. Time-box each problem at 30 minutes; if stuck, read the editorial, then re-implement from scratch the next day.

---

### Part 3 — References (2025–2026, ranked by usefulness)

#### Primary (read/watch these first)

1. **zhijun_liao — "Powerful Ultimate Binary Search Template and Many LeetCode Problems"**
   - LeetCode Discuss: https://leetcode.com/discuss/post/786126/
   - Towards Data Science mirror: https://towardsdatascience.com/powerful-ultimate-binary-search-template-and-many-leetcode-problems-1f850ef95651/
   - The single most-cited binary search article in the LeetCode ecosystem. Walks the same template through First Bad Version, Sqrt, Koko, Ship, Split Array, Bouquets, Smallest Divisor, and Multiplication Table.

2. **Errichto — "The most comprehensive Binary Search lecture"** (30 min, 2018, still definitive)
   - YouTube: https://www.youtube.com/watch?v=GU7DpgHINWQ
   - Codeforces companion post: https://codeforces.com/blog/entry/67509
   - Code: https://github.com/Errichto/youtube/tree/master/lectures/binary-search
   - Watch at 1.25× with captions, as he recommends. Covers find-first-true, sqrt approximations, and rotated-array tricks. The cleanest "stop guessing about ±1" framing on the internet.

3. **Hello Interview — Binary Search module** (the most modern interview-tailored resource, 2024–2026)
   - https://www.hellointerview.com/learn/code/binary-search/overview
   - Includes "Apple Harvest" (Koko renamed for interview pretext), 2D-matrix lessons, and step-by-step "what would you say to the interviewer" framing — perfect for a senior IC who already knows algorithms but needs to *talk through* them on a whiteboard.

4. **NeetCode Binary Search playlist + neetcode.io**
   - Roadmap & solutions: https://neetcode.io/roadmap (the Binary Search column, ~25 problems with video + written explanations)
   - Playlist: https://www.youtube.com/playlist?list=PLot-Xpze53leNZQd0iINpD-MAhMOMzWvO
   - Problem list mirrored on LeetCode: https://leetcode.com/problem-list/mqud5iw3/
   - The de facto FAANG prep curriculum; videos run 8–15 min and use the same Python template throughout.

5. **Striver / takeUforward — Binary Search playlist**
   - Playlist: https://www.youtube.com/playlist?list=PLgUwDviBIf0pMFMWuuvDNMAkoQFi-h0ZF (and the equivalent on the official channel: https://www.youtube.com/playlist?list=PLF6ChxadzFf8vjafLIxxbKUfarW4V4IOh)
   - Companion blog index: https://takeuforward.org/blogs/binary-search
   - Strongest progression for Tier 3 ("BS on Answer") problems. ~30 videos, India-focused but uniformly excellent.

#### Secondary (deeper dives, theory, additional perspectives)

6. **LeetCode official "Binary Search" Study Plan** (8 patterns, 42 curated problems): https://leetcode.com/studyplan/binary-search/
7. **LeetCode Explore Card — Binary Search:** https://leetcode.com/explore/learn/card/binary-search/ (includes the three "Templates I/II/III" article that the community typically dismisses in favor of zhijun_liao's, but worth reading once for contrast).
8. **labuladong — "Binary Search Algorithm Code Template"**: https://labuladong.online/en/algo/essential-technique/binary-search-framework/ (the inclusive `[lo, hi]` style done thoroughly; useful as a comparison point if you find the half-open style unfamiliar).
9. **USACO Guide — Binary Search (Silver):** https://usaco.guide/silver/binary-search (rigorous Haskell-style `firstTrue/lastTrue` exposition; explicit treatment of off-by-ones, integer overflow, and negative bounds).
10. **AlgoMonster — Binary Search & Monotonic Function:** https://algo.monster/problems/binary-search-monotonic and the Speedrun: https://algo.monster/problems/binary-search-speedrun (paid, but the free preview structure mirrors the Tier ladder above).
11. **Topcoder — "Binary Search" tutorial (Lovro Pužar):** https://www.topcoder.com/community/competitive-programming/tutorials/binary-search — the canonical predicate-based treatment; old (2008-ish) but its "main theorem" framing is timeless.
12. **Codeforces — "Binary Search on the Answer" (entry/143038):** https://codeforces.com/blog/entry/143038 — concise modern restatement.
13. **Codeforces — Errichto's resource wiki on binary search:** https://github.com/Errichto/youtube/wiki/Learning-resources
14. **AlgoMaster — "LeetCode was HARD until I Learned these 15 Patterns"** (Modified Binary Search section): https://blog.algomaster.io/p/15-leetcode-patterns
15. **Sean Prashad's Leetcode Patterns:** https://seanprashad.com/leetcode-patterns/ — filter by "Binary Search" for a company-tagged practice list.

#### Books / long-form

16. **Antti Laaksonen — *Competitive Programmer's Handbook*, Chapter 3 ("Sorting"), §3.3 ("Binary search"):** free PDF at https://cses.fi/book/book.pdf. The "powers of two jumps" implementation in §3.3 is an elegant alternative — concise and historically used by competitive programmers — but for interviews stick with the half-open template above.
17. **Steven S. Skiena — *The Algorithm Design Manual* (3rd ed., 2020), §4.9 "Binary Search and Related Algorithms" / §5.1 "Divide and Conquer."** The "Counting Occurrences" and "One-Sided Binary Search" subsections are particularly relevant for FAANG-level pivots.
18. **CP-Algorithms (e-maxx) — Binary Search:** https://cp-algorithms.com/num_methods/binary_search.html — formal treatment including binary search on real-valued continuous functions and the "binary lifting" pointer/power variant (useful for tree LCA, occasionally appears in advanced FAANG problems).
19. **Brent Yorgey — "Competitive programming in Haskell: better binary search":** https://byorgey.wordpress.com/2023/01/01/competitive-programming-in-haskell-better-binary-search/ — for the math-PhD reader: an unusually elegant articulation of the predicate abstraction.

#### LeetCode Discuss posts worth bookmarking

- **"Binary Search for Beginners | Problems | Patterns | Sample solutions"** (~20 problems by category): https://leetcode.com/discuss/general-discussion/691825/
- **Amit Maity — "Binary Search on Answer | Concepts with all curated problems":** https://medium.com/@maityamit/binary-search-binary-search-on-answer-concepts-with-all-curated-problems-on-leetcode-4e373384e676
- **"Curated Binary Search Problem List (Easy → Hard)":** https://leetcode.com/discuss/post/7487874/
- **"Binary Search: A Comprehensive Guide" (LC study guide):** https://leetcode.com/discuss/study-guide/3726061/

---

## Caveats

- **Template choice is partly stylistic.** The half-open `firstTrue` template recommended here is the modal choice across modern resources, but the inclusive `while (lo <= hi)` style (labuladong, NeetCode's videos, the LeetCode Explore "Template I") is also valid and sometimes nicer for "find exact match" problems like LC 704. The mistake is not picking one — the mistake is mixing them. Pick the half-open form, use it for *every* problem, and your bug rate will plummet.
- **"Binary search on the answer" requires a real proof of monotonicity.** Several problems look like they admit it but don't (e.g., problems where increasing the parameter `x` can break a constraint non-monotonically). Always articulate the monotonicity argument before writing code; if you can't, treat the technique as inapplicable. Codeforces commenters routinely note that mis-recognizing this pattern is the most common reason candidates submit wrong answers in interviews.
- **LC 240 (Search 2D Matrix II) is *not* really binary search.** The canonical solution is a top-right "staircase" two-pointer walk in O(m+n). Some resources (and even some interviewers) mis-categorize it. Know both and pick the right tool.
- **LC 81 / 154's worst case is O(n), not O(log n).** Be ready to explain why duplicates degrade the bound and that this is provably tight (no comparison-based algorithm can do better when all elements equal).
- **Hello Interview, AlgoMonster, and Striver's premium tier are paid.** All have substantial free content (Hello Interview's Code module preview, AlgoMonster's "speedrun" intros, Striver's full YouTube playlist). NeetCode 150 is fully free including video solutions.
- **Errichto's lecture is from 2018.** Nothing about binary search has changed since, and his code on GitHub still compiles and runs. But if you want a 2024+ presentation style with diagrams, prefer Hello Interview or NeetCode.
- **The Codeforces "When to Use Binary Search" and "How to recognize BS-on-answer" blogs are community posts, not official editorials.** Their advice is sound but uneven; treat as supplementary, not primary.
- **For a math-PhD reader:** the cleanest formalism is "we have a monotone Boolean function on `Z ∩ [a, b]` and seek its transition point in O(log(b-a)) queries." This generalizes to: (a) ternary search for unimodal real functions; (b) parametric search à la Megiddo (which the literature often, somewhat loosely, cites as the academic ancestor of "binary search on the answer"); (c) binary search on bit representations of floats (the USACO Guide and Yorgey blog cover this — though note Yorgey's post has an erratum about the float bit-trick that he flagged in his own comments).

Use this as a 2–3 week sprint plan: master the template in week one, climb Tiers 2 and 3 in week two, finish Tier 4 plus mock-interview problems (LC 4, 719, 668, 1095) in week three. By that point binary search will be a *recognition* skill rather than a *recall* skill — which is exactly what FAANG bar-raisers are screening for.