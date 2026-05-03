---
title: "Alternatives to Baekjoon: Coding Interview & Competitive Programming Platforms for Korean Developers"
category: "Algorithms & Problem Solving"
description: "Platform-by-platform guide covering Korean tech hiring tests (Programmers, SWEA), global Big Tech prep (LeetCode, NeetCode 150, Educative, Hello Interview), and competitive programming (Codeforces, AtCoder, CSES, Kattis, USACO Guide) — all with first-class Kotlin and Java support"
---

# Alternatives to Baekjoon Online Judge: A Comprehensive Guide for Korean Developers Preparing for Coding Interviews & Competitive Programming

## TL;DR

- **For Korean tech-company hiring tests, the must-use platforms are 프로그래머스 (Programmers) and SWEA**: Kakao, Line, SK Hynix, Netmarble, Toss, NHN, Hyundai Mobis, Smilegate, and Market Kurly run their tests on Programmers' platform, while Samsung's SCSA/SWC competency tests are administered through SWEA. Pair these with Baekjoon (with the solved.ac difficulty overlay) to cover essentially every domestic test format.
- **For global Big Tech (Google, Meta, Amazon) interviews, LeetCode is the dominant platform**, supplemented by NeetCode 150 (free curated list + videos), Educative's "Grokking" courses for patterns and system design, and Hello Interview for system-design-heavy senior interviews. Both Kotlin and Java are first-class on every one of these platforms.
- **For pure competitive programming, Codeforces and AtCoder are the international gold standard** (both free, both support Kotlin and Java); the CSES Problem Set, Kattis, and the USACO Guide are the best free curricula. Solved.ac plus Baekjoon remains the single best Korean-language CP environment, while AlgoSpot has effectively gone dormant.

---

## Key Findings

1. **Korean hiring tests are tightly coupled to specific platforms.** Kakao's BLIND RECRUITMENT, the Kakao internships, and Line's recruitment all run on `career.programmers.co.kr` — this is publicly stated by Kakao's tech blog and Programmers Business. Samsung's SCSA/Software Competency Test runs on SWEA (samsungcareers.com explicitly directs applicants to "practice and participate in mock problem solving through the SW Expert Academy"). Coupang typically uses HackerRank for online assessments, and many other Korean firms (Toss, Naver) use Programmers, Goorm DEVTH, or Codility-style proctored tests. Therefore, *which platform you study on should match the company you target*.

2. **Baekjoon is unmatched for breadth in Korea but weak for "test format" practice.** Baekjoon hosts approximately 35,000+ problems (problem numbers are now in the 35,000s as of 2026), supports 60+ languages (including Kotlin and Java), and has the largest Korean-language problem archive. Its weakness is that it uses stdin/stdout I/O while most company coding tests use a "function-shell" format closer to LeetCode/Programmers. solved.ac fixes Baekjoon's missing difficulty system.

3. **Programmers, not Baekjoon, mirrors the actual coding-test environment most Korean candidates will face.** Programmers School problems use the `solution()` function-return format identical to what Kakao, Line, and many other firms use in their real tests, and Programmers' web IDE *is* the testing environment.

4. **Kotlin support is uneven.** Kotlin is well-supported on Baekjoon, Programmers, LeetCode, Codeforces (with dedicated "Kotlin Heroes" rounds), AtCoder, and Educative/AlgoExpert. **Kotlin is NOT supported on SW Expert Academy** (only C/C++/Java/Python) — a critical gap for Samsung-track candidates. Java is supported essentially everywhere.

5. **The free tier is sufficient for most candidates.** Baekjoon, Programmers' practice section, Codeforces, AtCoder, CSES, Kattis, USACO Guide, NeetCode (free 150), HackerRank, Exercism, and Project Euler are all free. Paid platforms (LeetCode Premium ~$35/mo or $159/yr, AlgoExpert ~$99–$199/yr, Educative ~$199/yr, NeetCode Pro ~$119/yr or ~$219 lifetime, Hello Interview Premium with reported "up to 20% off" promotions) are valuable mostly for company-tagged questions, mock interviews, or system-design content.

---

## Details

### A. Korean-language platforms (or platforms used primarily in Korea)

#### 1. Programmers / 프로그래머스 (school.programmers.co.kr)
- **Description.** Operated by Grepp Inc., this is the de-facto Korean coding-test platform. The "School" section is for individuals; "Business" / "career.programmers.co.kr" is the B2B testing engine used by companies for hiring.
- **Use case.** Primarily **interview prep** for Korean firms; secondarily for SQL practice and short challenges. Less suited for pure competitive programming.
- **Difficulty & count.** Levels 1–5; the curated archive covers a few hundred problems plus Kakao Blind Recruitment and Kakao Tech Internship past papers (2017–2024+), Kakao Code Festival, and Summer/Winter Coding sets. Problem count is much smaller than Baekjoon's, but quality and "test-likeness" are higher.
- **Languages.** C, C++, Java, **Kotlin**, JavaScript, Python, Swift, Ruby, Go (the exact set varies by problem; Kakao tests typically allow C++/Java/JavaScript/Kotlin/Python/Swift).
- **Pricing.** Free for individual practice; companies pay for B2B testing.
- **Notable features.** Function-shell I/O matching real coding tests; Kakao past papers with editorials; SQL track; weekly/monthly challenges (Wol-Ko-Chal); user-published solutions visible after AC; integrated web IDE.
- **Vs. Baekjoon.** Smaller archive but vastly better "real test" fidelity. Programmers' I/O format and IDE are exactly what Kakao/Line candidates encounter.
- **Korea community.** Massive — essentially every Korean developer prepping for a Kakao/Line interview practices here, and Programmers also runs the "프로그래머스 개발자 설문조사" (Korea developer survey) with thousands of respondents.
- **Korean companies that hire through it.** Kakao, Line, SK Hynix, Netmarble, NHN, Hyundai Mobis, Smilegate, Market Kurly, Amorepacific, Today's House, and many more (Programmers' B2B page lists these explicitly).

#### 2. Baekjoon Online Judge (acmicpc.net) — the reference point
- **Description.** Run by Startlink. The largest Korean-language algorithm judge.
- **Use case.** Both interview prep (Samsung-style implementation problems) and competitive programming (ICPC, KOI, university contests).
- **Difficulty & count.** ~35,000+ problems with no native difficulty system — this is solved by solved.ac (see below).
- **Languages.** 60+, including C/C++/Java/Python/**Kotlin**/Swift/Go/Ruby/Rust/Scala.
- **Pricing.** Free.
- **Notable features.** Problem workbooks, group function, blogs, Korean-language editorials, university/high-school contest archives, stdin/stdout I/O. Specific Samsung SW Expert past-test archives at `acmicpc.net/workbook/view/1152` and `2771`.
- **Caveat (re-baseline).** It appears, based on items in the front-page recent-problem feed seen during research (titles like "Good Bye, BOJ!"), that some kind of farewell/end-of-season event was running in 2026; readers should verify the platform's current operational status directly. The judge itself, the archive, and solved.ac remain functional and widely used as of this writing.

#### 3. solved.ac (solved.ac)
- **Description.** Community-built tier/rating overlay for Baekjoon, started in 2020 by 박수현 (shiftpsh), a Sogang University CS student. Adds Bronze→Ruby tiers, AC Rating, problem difficulty voting, and CLASSes (curated step-by-step problem sets).
- **Use case.** Companion to Baekjoon — strictly an aid, not a separate judge.
- **Pricing.** Free; an optional "solved.ac Pro" subscription exists (and as of late-2025 there were notes about "Free Access and Resale of the solved.ac Pro Subscription").
- **Why it matters.** Before solved.ac, Baekjoon's biggest weakness was "no difficulty info"; solved.ac now provides the standard 32-tier scale that Korean developers use to communicate skill level (e.g., "골드 4", "플래티넘"). Many Korean job-prep guides target "어려운 실버 ~ 쉬운 골드" (hard Silver to easy Gold) as the practical coding-test threshold.

#### 4. SW Expert Academy / SWEA (swexpertacademy.com)
- **Description.** Samsung-operated learning + judge platform, opened 2017.
- **Use case.** **Samsung hiring tests are the primary reason to use it.** Samsung SCSA, SWC (Software Competency Test), and most R&D affiliate tests use this exact platform. Per Samsung Careers, applicants are given 240 minutes to solve 2 problems on SW Expert Academy.
- **Difficulty & count.** Difficulty buckets D0–D5 (and beyond). Several thousand problems plus past Samsung A-type / Pro / Expert exams.
- **Languages.** **C, C++, Java, Python only — no Kotlin.** This is a major constraint for Kotlin developers targeting Samsung.
- **Pricing.** Free with Samsung membership signup.
- **Notable features.** Reference codes for each problem; learning courses; Samsung Youth SW Academy integration; SWC test environment is restrictive (no STL/library functions, only `Scanner` for input in Java, no auto-complete).
- **Vs. Baekjoon.** Smaller and less polished problem-wise, but the *only* place to practice the actual Samsung test sandbox. Many candidates do BOJ's "Samsung 기출" workbook in tandem.

#### 5. AlgoSpot (algospot.com)
- **Description.** Korea's first major competitive-programming judge/community, run by 구종만 (Jongman Koo), author of the influential textbook "알고리즘 문제 해결 전략" ("Algorithmic Problem Solving Strategies", a.k.a. JMBook).
- **Use case.** Historically a competitive programming forum + judge; today largely a problem archive paired with the JMBook.
- **Status.** **Effectively dormant** for new users — most of the Korean CP community migrated to Baekjoon/solved.ac and Codeforces years ago. Still cited as the canonical companion to JMBook problems, and the site still hosts UCPC announcements.
- **Pricing.** Free.
- **Why mention it.** If you're working through 알고리즘 문제 해결 전략 systematically, AlgoSpot's JMBook problemset is still the natural home. Otherwise, treat it as historical.

#### 6. Codeup (codeup.kr)
- **Description.** Beginner-oriented Korean judge popular in middle/high-school informatics education and KOI prep.
- **Use case.** Foundational programming and basic algorithm practice — closer to "learn to code" than "interview prep". Heavy overlap with the JOI/KOI training pipeline.
- **Languages.** C/C++/Python/Java.
- **Pricing.** Free.
- **Korea community.** Modest — mainly students/teachers in informatics-track high schools and KOI participants.

#### 7. Goorm Level (level.goorm.io) / Goorm DEVTH (devth.goorm.io)
- **Description.** Goorm runs both a learning platform (goormEDU), a cloud IDE (goormIDE), and a B2B coding-test platform (goormDEVTH). Goorm Level is the practice-problem track.
- **Use case.** Practice + company tests. Per public Goorm reporting, 1,500+ companies/institutions have adopted Goorm services, including NHN, Hyundai Mobis, Smilegate, Market Kurly, Amorepacific, Samsung, Kakao Enterprise, Toss, and Today's House.
- **Languages.** C, C++, Java, JavaScript, Python (Kotlin support has been added on the level practice site for some problems; depends on problem).
- **Pricing.** Free for individual practice; subscription for companies (free tier for startups under 20 employees / under 3 years old).
- **Notable features.** Cloud IDE in browser (no setup), proctoring/Observe feature, screen+webcam monitoring for real exams.
- **Vs. Baekjoon.** Smaller archive; main value is familiarizing yourself with the Goorm exam UI before a real proctored test.

#### Other Korean platforms worth knowing
- **JungOl (jungol.co.kr)** — KOI/Korea Olympiad in Informatics training problems; high-school/middle-school focus.
- **CodeTree / 코드트리** — Subscription Korean platform offering structured 알고리즘 커리큘럼 with milestone tests; popular among students prepping Samsung A-type and KOI.
- **NYPC, UCPC, SCPC, 카카오 코드페스티벌** — Annual Korean contests rather than persistent platforms; usually held on Programmers or a custom judge.

### B. International / English-language platforms

#### 1. LeetCode (leetcode.com)
- **Description.** The single most-cited platform for FAANG-style interview prep.
- **Use case.** Coding interview preparation (Google, Meta, Amazon, Microsoft, etc.). Some contest activity, but secondary.
- **Difficulty & count.** ~3,000+ problems (Easy/Medium/Hard). Premium adds 300+ premium-only problems and company-tagged lists (e.g., "~200 questions tagged Google").
- **Languages.** ~16 including C, C++, Java, **Kotlin**, Python, JavaScript, Go, Swift, Ruby, Rust, Scala, C#, TypeScript.
- **Pricing.** Free tier covers most problems. Premium is **$35/month or $159/year** (most-cited 2025 prices; some sources cite $39/month for shorter terms).
- **Notable features.** Company tags (Premium), curated study plans, mock interviews, weekly + biweekly contests, Discuss tab with high-quality community solutions, AI hints (recent addition).
- **Vs. Baekjoon.** LeetCode is function-shell I/O like Programmers; problems are tighter and more interview-pattern-focused; Baekjoon has more raw problems and is more contest-style. Korean developers preparing for Naver/Coupang/global big-tech routinely use both.
- **Korea community.** Large and growing — particularly common among engineers targeting FAANG, Coupang, foreign-MNC offices.

#### 2. HackerRank (hackerrank.com)
- **Description.** Originally a CP platform, now primarily an enterprise hiring-assessment tool.
- **Use case.** **Coupang's coding tests run on HackerRank**; many other multinationals also use it for OAs. Also good for SQL, regex, and shell scripting practice.
- **Languages.** 40+ including Java and Kotlin (Kotlin support is solid).
- **Pricing.** Free for candidates; companies pay.
- **Notable features.** Skill certifications (Problem Solving, Java, SQL), 30 Days of Code track, Interview Preparation Kit, domain coverage broader than LeetCode (AI, databases, functional programming).
- **Vs. LeetCode.** Less algorithm-pattern depth; better for SQL and "OA format familiarity"; not really used for company-tagged interview prep.

#### 3. Codeforces (codeforces.com)
- **Description.** The most active competitive-programming site, run by Mike Mirzayanov.
- **Use case.** **Pure competitive programming.** Weekly Div.1/2/3/4 rounds, Educational Rounds, Global Rounds, Kotlin Heroes (JetBrains-sponsored Kotlin-only rounds), ICPC qualifications.
- **Difficulty & count.** Tens of thousands of problems indexed by rating (800–3500+).
- **Languages.** C++ dominant; Java, Python, Kotlin, Rust, Go, C# all supported. Kotlin Heroes contests are Kotlin-only and JetBrains has explicitly partnered with Codeforces.
- **Pricing.** Free.
- **Notable features.** Live ranked contests (~5/month), hacking phase in Div.1/2 rounds, public submissions/editorials, blogs.
- **Vs. Baekjoon.** Codeforces is more contest-oriented and faster-paced; Baekjoon is more "study at your own pace." Most serious Korean CP enthusiasts use both.

#### 4. AtCoder (atcoder.jp)
- **Description.** Japan-based CP platform, widely respected for problem quality.
- **Use case.** Competitive programming with weekly Beginner Contest (ABC), Regular Contest (ARC), Grand Contest (AGC), Heuristic Contest (AHC), Beginner-friendly DP/Educational sets.
- **Difficulty & count.** Thousands of archived problems; ABC has 7–8 problems weekly graded A–H.
- **Languages.** 40+, including Kotlin, Java, C++, Rust, Python (PyPy3 highly competitive).
- **Pricing.** Free.
- **Notable features.** Concise, math-heavy problem statements (often considered higher-quality on average than Codeforces); Educational DP Contest is a globally-recommended DP curriculum; convenient time slots for Asia/Pacific (Saturday/Sunday evenings KST).
- **Vs. Codeforces.** AtCoder problems are shorter and often more elegant; no hacking phase; community considers ABC the cleanest weekly entry point for new CP participants.

#### 5. TopCoder (topcoder.com)
- **Description.** The original online CP platform (2001), home of Single Round Matches (SRM) and Marathon Matches.
- **Use case.** Historical CP, occasional contests. Mostly legacy now — community activity has shifted to Codeforces and AtCoder.
- **Languages.** Java, C++, C#, Python.
- **Pricing.** Free.
- **Korea community.** Small.

#### 6. CodeChef (codechef.com)
- **Description.** Indian CP platform (acquired by Unacademy), with monthly Long Challenge (deprecated/restructured), Cook-Off, LunchTime, Starters series.
- **Use case.** CP contests, structured DSA learning paths.
- **Languages.** 30+.
- **Pricing.** Free practice; some courses paid.
- **Korea community.** Small; mostly used by Korean students who want extra contest volume.

#### 7. HackerEarth (hackerearth.com)
- **Description.** Indian platform, blends CP contests, hackathons, and enterprise hiring.
- **Use case.** Hackathons, hiring challenges (Samsung India previously used HackerEarth as a gateway to its SWC test for working professionals).
- **Pricing.** Free for individuals.
- **Notable features.** Codemonk tutorials, monthly contests; corporate hackathons.

#### 8. Codewars (codewars.com)
- **Description.** Kata-based platform with kyu/dan ranking (8 kyu beginner → 1 dan expert).
- **Use case.** Casual practice, language-syntax mastery, gamified learning. Less suited to interview-pattern study.
- **Languages.** 55+ including Kotlin and Java.
- **Pricing.** Free; optional Red ($20/mo) tier for premium content.
- **Notable features.** Community-authored katas, solution comparisons, language-specific tracks. Good for picking up a new language.

#### 9. Project Euler (projecteuler.net)
- **Description.** 850+ math-and-programming puzzles, online since 2001.
- **Use case.** Mathematical problem-solving; not interview prep, not really CP.
- **Languages.** Any (you submit only the final numeric answer).
- **Pricing.** Free.
- **Notable features.** Forum unlock after solving; very long-tail collection of number theory, combinatorics, and discrete-math problems.

#### 10. Exercism (exercism.org)
- **Description.** Free mentor-driven coding practice across 70+ tracks.
- **Use case.** Learning a new language idiomatically; not interview-pattern-focused.
- **Pricing.** Free (donation-supported).
- **Notable features.** Optional human mentor reviews; well-suited to picking up Kotlin or Rust.

#### 11. USACO Guide + USACO contests (usaco.guide / usaco.org)
- **Description.** USACO is the US high-school informatics olympiad with Bronze→Silver→Gold→Platinum divisions. The free USACO Guide is one of the best curated CP curricula on the internet, written by USACO Finalists including 2× IOI winner Benjamin Qi.
- **Use case.** Structured CP self-study from beginner to IOI-level. Excellent for working through topics in order with curated problemsets.
- **Languages.** C++ and Java fully supported; Python supported in lower divisions.
- **Pricing.** Guide and problems are free. Optional paid classes from CPI ($100) or AlphaStar/VPlanet for deeper coaching.

#### 12. Kattis (open.kattis.com)
- **Description.** Swedish online judge used by ICPC World Finals and many regional contests.
- **Use case.** ICPC-style problemset practice; widely used in university CS courses.
- **Languages.** C, C++, Java, Kotlin, Python, Go, C#, Rust, Haskell, and more.
- **Pricing.** Free.
- **Notable features.** Submission CLI tool, university leaderboards, no native difficulty (problems have community-difficulty estimates).

#### 13. CSES Problem Set (cses.fi)
- **Description.** 300+ classic algorithm problems curated by Antti Laaksonen (author of the Competitive Programmer's Handbook), arranged by topic from Introductory through Advanced Techniques.
- **Use case.** Best-in-class CP curriculum for systematically learning algorithms. Many CP coaches consider "complete the CSES set" the canonical mid-level milestone.
- **Languages.** C++, Java, Python, etc.
- **Pricing.** Free.
- **Vs. Baekjoon.** Far smaller but more pedagogically structured; complementary, not substitutable.

#### 14. NeetCode (neetcode.io)
- **Description.** Created by an ex-Google engineer; built around the **NeetCode 150** (and NeetCode 75 / 250 / All) curated lists with free YouTube video solutions for almost every LeetCode interview pattern.
- **Use case.** Curated FAANG interview prep — "what should I solve and in what order?".
- **Languages.** Solutions in Python, Java, C++, JavaScript, Go, Rust, etc. (Kotlin solutions exist for many problems on community forks but are not the primary language).
- **Pricing.** Core list and YouTube videos are **free**; NeetCode Pro is ~$119/year or ~$219 lifetime, adding additional problems, progress tracking, and an interview cheatsheet.
- **Notable features.** "Roadmap" pattern visualization, the highest-quality free video explanations on the internet for interview problems.
- **Korea community.** Very widely recommended on Korean blogs and 인프런 reading lists for global big-tech prep.

#### 15. AlgoExpert (algoexpert.io)
- **Description.** Polished video-first interview prep platform by ex-Google/Facebook engineer Clément Mihailescu. ~160 curated problems across DS&A, plus add-on bundles SystemsExpert, MLExpert, FrontendExpert.
- **Use case.** Coding interview prep with high-production video walkthroughs.
- **Languages.** 9 (JavaScript, Python, Java, C++, Swift, **Kotlin**, Go, C#, TypeScript).
- **Pricing.** $99/yr (AlgoExpert), $148/yr (with SystemsExpert), $199/yr full bundle. **No free trial, no monthly plan, no lifetime.** Many reviewers (and NeetCode comparisons) note that NeetCode 150 + free YouTube videos covers similar ground for free.
- **Vs. LeetCode.** Smaller (~160 vs 3,000+) but with built-in video explanations; weaker as a problem-grinding platform but stronger as a structured "course".

#### 16. Hello Interview (hellointerview.com)
- **Description.** Newer (and rapidly popular) prep platform by ex-Meta/Amazon engineers. Strong focus on **system design**, low-level design, ML system design, behavioral, and coaching.
- **Use case.** Mid/Senior+ engineer prep, especially system-design-heavy interviews. The "System Design in a Hurry" guide is free and widely cited.
- **Pricing.** Mocks start around $170 each (with package discounts for 3 or 6 mocks). Premium content has multiple tiers (monthly/yearly/lifetime); pricing varies and the site shows "up to 20% off" promotions.
- **Notable features.** AI-powered guided practice, real interviewer mocks (engineers/managers from FAANG), recent-question banks for Meta/Amazon/Google/OpenAI.
- **Vs. LeetCode.** Complementary — LeetCode for coding rounds, Hello Interview for system-design rounds. Particularly strong for L5/L6+ candidates.

#### 17. Educative.io (educative.io)
- **Description.** Subscription text-based interactive learning platform. Home of the famous **"Grokking the Coding Interview"** and **"Grokking the System Design Interview"** courses (the latter has since partly migrated to DesignGurus.io but Educative still offers Grokking Modern System Design).
- **Use case.** Pattern-based interview prep (the Grokking Coding Interview's 16 patterns are widely-cited), system design, ML system design, software architecture, language courses.
- **Languages in courses.** Java, Python, C++, JavaScript, Go are typical; Kotlin courses are limited.
- **Pricing.** Educative Unlimited around **$199/yr** (sources cite frequent 30–55% promotional discounts; an oft-quoted rate is "around $14.99/month equivalent on annual"). Individual courses also sold standalone.
- **Notable features.** In-browser code execution, no IDE setup, AI tutor, 1,900+ courses and 300+ projects.

#### 18. Other notable mentions
- **InterviewBit (interviewbit.com)** — Free curated interview prep tracks, popular with Indian SDE candidates.
- **CodeSignal (codesignal.com)** — Used as the OA platform by some US companies (Quora, Robinhood, etc.). Has a polished "Arcade" gamified track.
- **Pramp / Exponent** — Free peer-to-peer mock interviews. Pramp has been acquired by Exponent.
- **Coderbyte, Edabit, GeeksforGeeks (Practice section)** — Additional free practice sources.
- **AlgoMonster** — Pattern-template-based platform ($119–$299/yr or $459 lifetime).

### C. Comparison summary table (text)

| Platform | Type | Cost | Kotlin | Java | Best for | Korea relevance |
|---|---|---|---|---|---|---|
| Baekjoon | Judge (KR) | Free | Yes | Yes | All-purpose KR study | Foundation; Samsung기출 |
| solved.ac | Tier overlay | Free / Pro | n/a | n/a | Difficulty system for BOJ | Standard KR skill metric |
| Programmers | Test platform | Free | **Yes** | Yes | KR company tests | **Kakao/Line/Toss/etc.** |
| SWEA | Test platform | Free | **No** | Yes | Samsung tests | **Samsung-bound only** |
| Goorm Level/DEVTH | Test platform | Free / B2B | Partial | Yes | KR company exam UI | Many KR firms |
| AlgoSpot | Judge (KR) | Free | Yes | Yes | JMBook companion | Largely dormant |
| Codeup | Judge (KR) | Free | No | Yes | Beginner / KOI | High-school informatics |
| LeetCode | Interview judge | Free / $159yr | **Yes** | Yes | FAANG prep | Heavy use among KR FAANG candidates |
| HackerRank | Mixed | Free | Yes | Yes | OA practice + SQL | **Coupang OAs** |
| Codeforces | CP | Free | **Yes** | Yes | Pure CP | Major KR CP scene |
| AtCoder | CP | Free | **Yes** | Yes | Quality weekly CP | Asia-friendly time |
| CSES | Curriculum | Free | No | Yes | Structured CP | Self-study staple |
| Kattis | Judge | Free | Yes | Yes | ICPC training | University use |
| USACO Guide | Curriculum | Free | No | Yes | CP from scratch | Good free roadmap |
| NeetCode | Curated list | Free / $119yr | Community | Yes | Pattern-based prep | Highly recommended in KR |
| AlgoExpert | Video course | $99–$199yr | **Yes** | Yes | Video learners | Some KR users |
| Hello Interview | System design | Mocks $170+, premium tiered | n/a | n/a | Senior interviews | Growing |
| Educative | Course platform | ~$199yr | Limited | Yes | Grokking patterns | Widely cited |
| Codewars | Kata | Free / $20mo | Yes | Yes | Language practice | Light use |
| Project Euler | Math puzzles | Free | Any | Any | Math-heavy puzzles | Niche |
| Exercism | Mentored learning | Free | Yes | Yes | Learn a language | Niche |
| TopCoder | CP (legacy) | Free | No | Yes | History only | Minimal |
| CodeChef | CP | Free | Yes | Yes | Extra contests | Minimal in KR |
| HackerEarth | Mixed | Free | Yes | Yes | Hackathons | Light KR use |

### D. Which Korean companies use which platform for hiring tests

| Company | Hiring-test platform |
|---|---|
| **Kakao** (BLIND, Tech Internship, Code Festival) | **programmers.co.kr** |
| **Line** | programmers.co.kr (also internal) |
| **NHN, Netmarble, SK Hynix, Smilegate, Today's House, Kurly, Amorepacific** | programmers.co.kr or Goorm DEVTH |
| **Samsung** (DS, SDI, Electronics R&D, SCSA) | **SW Expert Academy** |
| **Coupang** | **HackerRank** (and Codility-style for some teams) |
| **Naver** | Mixed — internal proctored coding tests, sometimes Programmers |
| **Toss** | Often **take-home / 사전과제** style; coding tests on Programmers or Goorm |
| **Hyundai Mobis, Kakao Enterprise** | Goorm DEVTH |
| **Foreign offices (Google Korea, Meta APAC, Amazon)** | Standard global LeetCode-style with internal tools (Phabricator/Coderpad) |

### E. Recommended study stacks

**Korean new-grad targeting Kakao/Line/Toss:**
1. Baekjoon + solved.ac to reach 골드 4–3 (≈ Programmers Level 2–3 mid).
2. Programmers School "고득점 Kit" + all past Kakao Blind/Tech Internship sets.
3. Optional: a few HackerRank challenges to get used to its UI in case Coupang/foreign-office tests appear.

**Samsung-track candidate:**
1. Baekjoon Samsung기출 workbook (`acmicpc.net/workbook/view/1152` and `2771`) — implementation/simulation heavy.
2. SW Expert Academy — D3–D5 problems and the "역량테스트 기출" set, without using STL/library functions, in C++/Java only.
3. **Switch off Kotlin** for this track; SWEA does not support it.

**Korean candidate targeting Google/Meta/Amazon (FAANG):**
1. NeetCode 150 + YouTube videos as the curriculum spine.
2. LeetCode for volume: aim for ~250–400 medium/hard problems with company tags filtered to your target.
3. Educative's "Grokking the Coding Interview" for pattern reinforcement; "Grokking the System Design Interview" or **Hello Interview** for system-design rounds (mid-senior).
4. Pramp/Exponent for free peer mocks; consider 1–2 paid Hello Interview mocks before onsite.
5. Optional: a LeetCode Premium subscription for the final 1–2 months.

**Pure competitive programmer:**
1. Baekjoon + solved.ac up to 플래티넘 → switch focus to Codeforces (Div. 2/3) and AtCoder (ABC every week).
2. Work through CSES Problem Set systematically, then use the USACO Guide for topics not covered.
3. Read editorials, upsolve missed problems, target ICPC Korea Regional and UCPC.

---

## Caveats

- **Pricing changes frequently.** LeetCode Premium ($35/mo or $159/yr), AlgoExpert ($99–$199/yr), Educative (~$199/yr with frequent 30–55% promos), NeetCode Pro (~$119/yr or ~$219 lifetime), Hello Interview ("up to 20% off" promotions on Premium tiers and ~$170+ per mock) all run seasonal sales and have changed prices over time. Verify current pricing on each site before purchasing.
- **Kotlin support varies by platform AND by problem.** Even on platforms that "support Kotlin," some specific contest problems or company hiring tests may restrict the language list — for example, Samsung's SWC restricts to C/C++/Java only and forbids standard libraries; some Programmers-hosted company tests may also restrict the language menu set by the hiring company. Always check the actual test description.
- **Baekjoon's status.** During research I observed front-page items in the Baekjoon problem feed in 2026 with titles like "Good Bye, BOJ!" and "Good Bye, 두 트리!" These appeared to be event/contest problems but I could not confirm whether they signal a planned operational change to the site itself; treat reports of any "shutdown" with skepticism and verify on acmicpc.net directly. solved.ac, as a community project layered on top of Baekjoon's API, would be affected if Baekjoon ever went offline.
- **AlgoSpot is largely dormant.** The site still works, but new active users are rare and the community has migrated; treat it as a problem archive paired with the JMBook rather than a live community.
- **"Company tags" on LeetCode are recency-biased and not authoritative.** Premium's company-tag lists are crowdsourced from candidate self-reports; they are useful as a directional signal, not a guaranteed question list.
- **Mock-interview platforms (Pramp/Exponent, Hello Interview, IGotAnOffer) vary a lot in interviewer quality.** Read recent reviews before paying.
- **Korean usage statistics are anecdotal.** I have not seen a rigorous published survey of which platforms Korean developers use most; the relative-popularity claims above are based on Programmers' published 2023 developer survey (4,034 respondents) and consistent commentary across Korean tech blogs (velog, namu.wiki, tech.kakao.com, programmers.co.kr) rather than a single authoritative source. The general consensus that "Baekjoon + Programmers + (SWEA if Samsung)" is the standard Korean trio is, however, near-universal in Korean job-prep guides.