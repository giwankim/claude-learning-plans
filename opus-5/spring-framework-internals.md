---
title: "Spring Framework Internals — A Verified Learning Path & Resource Guide"
category: "Spring & Spring Boot"
description: "A source-anchored, seven-stage path into Spring's machinery for the Boot 4 / Framework 7 era, built by triangulating three primary-source video courses (김영한 고급편 for proxy/AOP internals, 토비's 스프링 6 and 스프링 부트 for container and auto-config from first principles) against the source tree itself — read `AbstractApplicationContext.refresh()`, `ConfigurationClassPostProcessor`, and `AbstractAutoProxyCreator` while you watch. Treats version currency as the dominant risk: everything published before the November 20, 2025 GA predates Boot 4's split of `spring-boot-autoconfigure` into 70+ focused JARs and the Jackson 3 / JSpecify / Jakarta EE 11 baseline, so Stage 0 is a baseline reset before any older material can be read correctly. Includes honest per-resource verdicts (only Pro Spring 7 and Pro Spring 6 with Kotlin are current; 토비의 스프링 3.1 is conceptually timeless but structurally dated, and there is no print 토비 스프링 6), a named list of AI-generated Amazon 'Spring internals' slop to avoid, Spring Team conference talks where the framework authors explain their own design decisions, source-reading tooling, and a verdict on whether the Spring Certified Professional exam is worth it at a senior level."
---

# Spring Framework Internals: A Verified Learning Path & Resource Guide (Boot 4 / Framework 7 era, mid-2026)

## TL;DR
- The single strongest internals path for your profile is a **triangulation of three primary-source video courses plus the source tree itself**: 김영한's *스프링 핵심 원리 – 고급편* (proxy/AOP internals, ~16h 41m), 토비's *스프링 6 – 이해와 원리* and *스프링 부트 – 이해와 원리* (container/DI/auto-config first principles), and the Spring Team's own conference talks (Nicoll/Wilkinson "Kind of Magic", Halbritter "Inside Spring Boot 4", Hoeller "Core Resilience Features in Spring Framework 7"). Read these *against* `AbstractApplicationContext.refresh()` in the actual source.
- For books, only **Pro Spring 7 (Apress, 2026)** and **Pro Spring 6 with Kotlin (2023)** are current, legitimate reference works; 토비의 스프링 3.1 (2012) remains conceptually excellent but structurally dated. **Avoid self-published "deep dive into Spring internals" titles** (e.g. Caleb Bennett's *Spring Java: Deep Dive into Spring Internals*) — these are AI/SEO slop.
- **Version currency is the dominant risk**: anything written before Spring Framework 7 / Spring Boot 4 GA (November 20, 2025) predates Boot 4's modularization of `spring-boot-autoconfigure` (the codebase was split into 70+ focused JARs) and the Jackson 3 / JSpecify / Jakarta EE 11 baseline. `spring.factories` → `AutoConfiguration.imports` (Boot 2.7→3.0) already broke older material; Boot 4's module split breaks it again.

## Key Findings

### The internals-relevant resources that are genuinely worth your time
1. **The Spring source tree + reference docs** (free) — the only fully current, authoritative material for Framework 7 / Boot 4.
2. **Korean video courses** (paid, Inflearn) — 김영한 고급편 for AOP/proxy internals; 토비 스프링 6 + 스프링 부트 for container and auto-config first principles. These are the best structured internals pedagogy available in any language.
3. **Spring Team conference talks** (free, YouTube/InfoQ) — the only place where framework authors explain their own design decisions, including the brand-new Boot 4 material.
4. **Marco Behler's written guides + snicoll.be + the spring.io blog** (mix of free/paid) — English-language deep dives that are accurate and source-anchored.
5. **Pro Spring 7 / Pro Spring 6 with Kotlin** (paid books) — comprehensive references, honest but not line-by-line source analysis.

### What to skip or distrust
- Beginner "Spring in Action"-style books and most Udemy certification cram courses (usage, not internals).
- Self-published Amazon/Kindle "Spring internals" books — AI-generated slop (see deliverable 3).
- Chinese GitHub "spring source analysis" repos pinned to Spring 4.3/JDK 8 — conceptually adjacent but structurally obsolete for your stack.

---

## Details

### 1. Recommended learning path (sequenced, with prerequisites)

**Stage 0 — Baseline reset for Boot 4 / Framework 7 (½ day, free).** Before anything else, read the two primary-source posts that define the current structural reality, because every older resource is wrong about them:
- spring.io blog, *Modularizing Spring Boot* (28 Oct 2025) — the authoritative explanation of the `spring-boot-autoconfigure` module split.
- InfoQ, *Spring Framework 7 and Spring Boot 4 Deliver API Versioning, Resilience, and Null-Safe Annotations* (Nov 2025) and *The Spring Team on Spring Framework 7 and Spring Boot 4* — the baseline summary. Per InfoQ, "Spring Framework 7 keeps the JDK 17 baseline while embracing JDK 25, but adopts Jakarta EE 11 and Kotlin 2.2 as new baselines" (GA November 20, 2025). Project lead Juergen Hoeller's rationale for holding the baseline, to InfoQ: "the current industry consensus is clearly around a Java 17 baseline."
This stage is a prerequisite for correctly interpreting everything else, since the courses/books below predate it.

**Stage 1 — Container & DI internals from first principles (prerequisite for everything).** Watch 토비 *스프링 6 – 이해와 원리*, focusing on Section 3 ("Objects and Dependencies": object factory → DI container → singleton registry) and Section 7 (service abstraction / proxy). This builds the mental model for `BeanFactory`, `doGetBean`, singleton caches, and DI that the source code assumes. Then read the reference docs *Core Technologies* IoC chapter alongside. Do NOT skip to auto-config before you own this.

**Stage 2 — AOP & proxy internals (depends on Stage 1).** Watch 김영한 *스프링 핵심 원리 – 고급편* Sections 5–14 (proxy pattern → JDK dynamic proxy vs CGLIB → `ProxyFactory`/`Advisor` → `BeanPostProcessor`-based auto-proxying → `@Aspect` → practical pitfalls like self-invocation). This is the single best structured treatment of Spring's proxy machinery anywhere. Then read the AOP chapter of the reference docs and open `AbstractAutoProxyCreator` and `ReflectiveMethodInvocation` in source. Transaction internals (`TransactionInterceptor`, `AbstractPlatformTransactionManager`, `TransactionSynchronizationManager`) follow naturally because they ride the same advisor chain.

**Stage 3 — Boot auto-configuration machinery (depends on Stages 1–2).** Watch 토비 *스프링 부트 – 이해와 원리* (you build a miniature Boot from scratch: `@Conditional`, `@Import`, self-made auto-config, then converge on the real thing). Pair with Marco Behler's *How Spring Boot's Autoconfigurations Work* and the reference section *Creating Your Own Auto-configuration*. **Caveat: the Toby Boot course is on Boot 2.7** — you must overlay Stage 0's modularization knowledge and the `spring.factories`→`AutoConfiguration.imports` change.

**Stage 4 — Config-class parsing & metadata (depends on Stage 3).** Read `ConfigurationClassPostProcessor` and `ConfigurationClassParser` in source, watching for `ImportSelector` / `DeferredImportSelector` (this is exactly how `AutoConfigurationImportSelector` works) / `ImportBeanDefinitionRegistrar`, CGLIB enhancement of `@Configuration` (`proxyBeanMethods`), and ASM-based `AnnotationMetadata` reading. The "Kind of Magic" talk is the video companion.

**Stage 5 — AOT / native / Boot 4 restructuring (depends on all above).** Read the reference *Ahead of Time Optimizations* (core/aot) chapter, then watch Halbritter's *Inside Spring Boot 4* and Deleuze's AOT/native talks. This is where the newest structural changes live.

**Stage 6 — ongoing.** Subscribe to the spring.io blog and This Week/Month in Spring; read release notes and "what's new" wiki pages as they land.

**Redundancy to exploit for skipping:** 토비 스프링 6 and 김영한 기본편 overlap heavily on DI/container basics — as a 10-yr engineer, skip 김영한 기본편 entirely and use only 고급편. Marco Behler's *What is Spring Framework?* guide overlaps with Toby Stage 1 conceptually; skim it, don't dwell. Pro Spring 7 and the reference docs overlap substantially — use the book as a linear read-through and the docs as the current-version corrector.

### 2. Books — current editions, honest assessment

- **Pro Spring 7: An In-Depth Guide to the Spring Framework** — Iuliana Cosmina, Rob Harrop, Chris Schaefer, Clarence Ho (Apress, 2026; ISBN-13 979-8-8688-2591-0; Springer listing at link.springer.com/book/9798868825910). Source repo `Apress/Pro-Spring-7` "was built successfully with JDK 26, Gradle 9.4.1," with syntax "specific to Java versions up to and including 26." **This is the current definitive comprehensive Spring reference book.** Verdict: excellent breadth (container, AOP, data, transactions, web, testing) and it's the only book tracking Framework 7. It is a *thorough reference*, not a line-by-line source-code dissection — it explains mechanisms and design, not `refresh()` step by step. ~$50–60 print / eBook. Buy this as your one current print reference.
- **Pro Spring 6 with Kotlin** — Peter Späth, Cosmina, Harrop, Schaefer (Apress, 2023). Kotlin-native variant; JDK 17, Kotlin ≤1.8.10. **Directly on-stack for you (Kotlin).** Still Framework 6 / Boot 3, so pre-modularization, but conceptually sound for container/AOP/tx. Good second choice if you want Kotlin idioms; otherwise Pro Spring 7 supersedes it on currency.
- **토비의 스프링 3.1** (이일민, 에이콘/Acorn, 2012; Vol.1 스프링의 이해와 원리, Vol.2 스프링의 기술과 선택). **Still the best-written explanation of *why* Spring is designed the way it is, in any language.** Vol.1 (DI, test, template, exception, service abstraction, AOP) is conceptually timeless; Vol.2 is more dated (XML-heavy, Spring 3 APIs). Verdict: read Vol.1 for insight, treat all code as historical. **Confirmed: there is NO print "토비의 스프링 6" book** — the Spring 6 material exists *only* as the Inflearn video course. His only authored Spring print book remains 3.1.
- **Felipe Gutierrez, Apress Spring Boot titles** (*Pro Spring Boot 2*, *Spring Boot Messaging*). Boot 2-era, usage-focused, now structurally dated for Boot 4 — not internals books. Skip for your purpose. (Note the frequently-confused *Spring Boot Persistence Best Practices* is by Anghel Leonard, also usage-focused.)
- **Book-length source-code analysis in any language:** The genuine ones are Chinese-community GitHub projects (e.g. `txazo/spring`, `ab2h/spring-analysis`), pinned to Spring 4.3 / JDK 8. Conceptually useful for the *shape* of `BeanDefinition` loading and the post-processor pipeline, but structurally obsolete. No current, high-quality, book-length English or Korean source-analysis title exists as of mid-2026 — the closest substitutes are the video courses plus reading source directly.

### 3. Low-quality / likely AI-generated books to AVOID

- **"Spring Java: Deep Dive into Spring Internals — Understand the Inner Workings of Spring Framework to Optimize Performance and Customize Behavior Like a True Spring Ninja"** by "Caleb Bennett" (Kindle, ASIN B0CZK6QSZF). This is the archetype of the slop you flagged. **Tells:** (1) breathless marketing blurb ("become a true Spring ninja," "chart your path as a Spring Framework architect"); (2) no identifiable author with a Spring track record (no conference talks, no GitHub, no committer history); (3) Kindle-only, no reputable publisher (contrast Apress/Springer with ISBNs and source repos); (4) impossibly broad scope ("from bean creation to reactive programming to microservices") with no version anchoring; (5) essentially no substantive reviews.
- **General heuristic for detecting slop:** legitimate Spring books have (a) a named author with a verifiable Spring footprint (committer, conference speaker, KSUG/Broadcom/VMware affiliation — Cosmina, Harrop, 이일민, 김영한), (b) a real publisher with an ISBN and an accompanying GitHub source repo, (c) explicit version targeting (Framework 7 / Boot 4 / Java version), and (d) reviews from identifiable developers. Slop fails most of these. Be especially wary of any 2024+ Kindle-only title with "Deep Dive," "Internals," "Mastery," or "Ninja/Wizard/Guru" in a subtitle and a generic author name.
- Note: *Mastering Spring AI* (Banu Parasuraman, Apress) and *Spring AI in Action* (Craig Walls, Manning) are legitimate but **off-topic** (Spring AI, not framework internals) — don't be misled by "Mastering."

### 4. Video courses

**Korean (Inflearn) — the strongest internals pedagogy available:**
- **김영한 – 스프링 핵심 원리 (고급편)** — 93,500 KRW; **125 lectures, ~16h 41m**; rating 5.0. (김영한's courses collectively surpassed 250,000 students per Inflearn's "25만 수강생 돌파" curation.) Covers proxy pattern/decorator, JDK dynamic proxy vs CGLIB, `ProxyFactory`, `BeanPostProcessor`-based auto-proxying, `@Aspect`, ThreadLocal, and Spring AOP practical pitfalls. **This is *the* AOP/proxy internals course.** Version note: published Oct 2021, so Spring Boot 2.x / Framework 5.x era (the page itself does not state a version number) — the proxy mechanics are unchanged in Boot 4, so this ages very well; only the surrounding API cosmetics are dated. Skip 김영한 기본편 (DI basics — beneath your level).
- **토비 (이일민) – 토비의 스프링 6 – 이해와 원리** — 93,500 KRW; **58 lectures, 12h 27m**; rating 5.0 (255 reviews, ~3,500 learners). Dev env JDK 17+, Spring 6.1.8 (Boot 3.3+). Rebuilds 토비의 스프링 3.1 Vol.1's arc (objects/DI → test → template → exception → service abstraction) for Spring 6. Best first-principles container course. Note: it deliberately stops *before* deep framework-implementation detail ("excluding the difficult parts of Spring implementation as much as possible") — it builds the model, then points you at source.
- **토비 (이일민) – 토비의 스프링 부트 – 이해와 원리** — 77,000 KRW; **68 lectures, 11h 6m**; rating 5.0 (410 reviews, ~6,900 learners). **Boot 2.7.6 / JDK 11** (migration to Boot 3.0 covered in a section). You build a miniature Spring Boot from scratch — the single best way to internalize `@Conditional`, `@Import`, auto-config, and embedded-server bootstrap. **Version caveat is important:** it predates both the `AutoConfiguration.imports` change and Boot 4 modularization; the *mechanism* it teaches is right, the *artifacts* are two generations old.

**English:**
- **Marco Behler – The Confident Spring Professional / Spring Boot: Internals** (marcobehler.com; paid, frequently discounted ~50%). Reverse-order pedagogy (plain Java → core Spring → Boot) with a "crash course of Spring Boot internals: AutoConfigurations and build your own." Accurate and concise; the closest English analog to the Toby Boot course.
- **Spring Academy** (spring.academy; the vendor's own courses, some free) — "Spring Framework Essentials" covers bean lifecycle, DI, AOP; it's the certification path, so more usage than deep internals.
- **Udemy/Pluralsight/O'Reilly:** Overwhelmingly usage- or certification-focused. The Udemy Spring "certification" catalog (2V0-72.22 practice tests, etc.) is exam cramming, not internals. No English video course matches the Korean pair for internals depth.

### 5. Conference talks (titles, speakers, years, archives)

- **"It's a Kind of Magic: Under the Covers of Spring Boot"** — the canonical auto-config internals talk, delivered multiple years: Stéphane Nicoll & Andy Wilkinson (Spring I/O 2017, YouTube), and Brian Clozel & Stéphane Nicoll (SpringOne Platform 2017; archived on InfoQ, recorded Apr 2018, ~1h30m). Covers auto-configuration and the conditional configuration model. Free.
- **"Inside Spring Boot 4: Restructuring for the Future"** — Moritz Halbritter, Spring I/O 2026 (Barcelona, 14–15 Apr 2026). **Video IS published** (YouTube, id `KnLJ-vFsjwE`; slides at mhalbritter.github.io/slides/2026-04). Covers the dependency-tree cleanup, auto-config modularization, JSpecify null-safety hardening, Jackson 3 transition, and HTTP service client support. This is the single most important *current* internals talk for your stack. Free.
- **"Core Resilience Features in Spring Framework 7"** — Juergen Hoeller, Spring I/O 2026. **Video IS published** (YouTube, id `hyHBmYwe-Hk`; slides on 2026.springio.net). Covers `@Retryable`, `RetryTemplate`, `@ConcurrencyLimit` moving into core Framework. Free.
- **Juergen Hoeller** more broadly: *Spring Office Hours S5E06* and the "This Month in Spring" interviews on Framework 7 (YouTube) — design-rationale interviews; useful for the "why."
- **Sébastien Deleuze on AOT/native:** *Spring Native and Spring AOT* (SpringOne 2021, slides on Tanzu/SlideShare); *From Spring Native to Spring Boot 3* (2023); *Devoxx 2023: Spring Framework 6 strategic themes*; Spring I/O 2026 *Null-safe applications with Spring Boot 4*. His blog seb.deleuze.fr (tags/spring) indexes them. Free.
- **Oliver Drotbohm:** Spring I/O 2026 *Domain-centric? Why Hexagonal and Onion Architecture are answers to the wrong question* — architecture, not container internals, but high-signal.
- **Marco Behler – "Spring Debugger: Behind the Scenes of Spring Boot"** (Devoxx) — demos the JetBrains Spring Debugger plugin for making bean wiring/`@Cacheable` visible. Free.
- Archives to search by name: InfoQ presentations, the Spring I/O YouTube channel, Devoxx YouTube, SpringOne/Tanzu.

### 6. Blogs, newsletters, written deep dives

**English:**
- **Marco Behler** (marcobehler.com) — *What is Spring Framework? An Unorthodox Guide*, *How Spring Boot's Autoconfigurations Work*, *Spring Security In-Depth*. Genuinely under-the-hood, accurate, and maintained. Free.
- **snicoll.be** (Stéphane Nicoll) and **spring.io/blog** — primary source. The blog's *Modularizing Spring Boot* (28 Oct 2025) is required reading; release/"what's new" posts carry real internals detail.
- **Baeldung** — quality is bimodal. Genuinely deep, internals-relevant articles: *Guide to ApplicationContextRunner in Spring Boot*, *Display Auto-Configuration Report in Spring Boot* (`debug=true` condition report), *Native Images with Spring Boot and GraalVM*. Distinguish these from its thousands of shallow "how to do X" SEO pieces — the deep ones walk actual mechanisms and show the condition-evaluation output.
- **Dan Vega** (danvega.dev) — *Spring Boot 4 Modularization: Fix Missing Auto-Configuration* is a concrete, current walkthrough of the module split and the `spring-boot-autoconfigure-classic` escape hatch.
- **InfoQ** Spring coverage — reliable release-level analysis with direct quotes from the team.

**Korean:**
- **우아한형제들 기술블로그** (techblog.woowahan.com) — high-quality engineering posts; use for applied deep dives (concurrency, reactive) though pure container-internals posts are intermittent.
- **velog.io** — the richest vein of Korean source-level Spring analysis, largely from developers working through 김영한/토비 courses. Notable series: `@jeongyunsung`'s *스프링부트 해부학* ("Spring Boot Anatomy": AOP/`ProxyFactory`, advisor chains), and numerous JDK-proxy-vs-CGLIB and `BeanPostProcessor` walkthroughs. Quality varies per author; cross-check against source.
- **Tistory / GitHub-Pages blogs** — e.g. `madplay.github.io` (bean lifecycle method ordering), `incheol-jung.gitbook.io` (토비의 스프링 3.1 chapter-by-chapter summaries). Good for targeted concept lookups.
- Caveat: many Korean blog posts are course lecture-notes, so they inherit the course's version (often Boot 2.x/3.x); treat code as version-dated.

### 7. Official documentation — which sections actually repay close reading

- **Spring Framework Reference → Core Technologies** (docs.spring.io/spring-framework/reference/core.html): the IoC container section (bean lifecycle, `BeanFactoryPostProcessor` vs `BeanPostProcessor`, `Environment`/`PropertySource`) and the AOP section are the two highest-value chapters for internals. Read at v7.0.x.
- **Spring Framework Reference → Core → Ahead of Time Optimizations** (core/aot.html): explains that AOT inspects the `ApplicationContext` at build time; documents the key restriction that `BeanPostProcessor`s are *not* invoked during AOT except `MergedBeanDefinitionPostProcessor` and `SmartInstantiationAwareBeanPostProcessor`. Essential and current.
- **Spring Boot Reference → Creating Your Own Auto-configuration** (features/developing-auto-configuration.html): documents `ApplicationContextRunner`, `ConditionEvaluationReportLoggingListener`, and the `spring-autoconfigure-metadata.properties` eager-filtering mechanism. This is the practical internals-debugging chapter.
- **GitHub wiki / release material:** the Spring Boot 4.0 *Release Notes* and *Migration Guide*, and the *Modularizing Spring Boot* blog post, carry the real structural-change detail (module names now `org.springframework.boot.<module>`, classic starters, `spring-boot-autoconfigure-classic`). The Framework "What's New" reference chapter per minor version is worth a close read each upgrade.

### 8. Source-reading aids, tooling & debugging techniques

- **The source itself:** `spring-projects/spring-framework` and `spring-projects/spring-boot`. Suggested reading order for the container: `AbstractApplicationContext.refresh()` → `invokeBeanFactoryPostProcessors` → `ConfigurationClassPostProcessor`/`ConfigurationClassParser` → `registerBeanPostProcessors` → `finishBeanFactoryInitialization` → `DefaultListableBeanFactory.doGetBean`/`AbstractAutowireCapableBeanFactory.doCreateBean` → singleton caches & the three-level cache for circular refs → `AbstractAutoProxyCreator` post-processing.
- **Community source-analysis repos:** `txazo/spring` and `ab2h/spring-analysis` (Chinese, Spring 4.3/JDK 8) — annotated walkthroughs; use for *structure*, not current APIs.
- **Debugging/instrumentation toolkit:**
  - `-Ddebug=true` (or `debug=true` in properties) → prints the **CONDITIONS EVALUATION REPORT** (positive/negative matches for every auto-config) at startup.
  - **`ApplicationContextRunner`** + **`ConditionEvaluationReportLoggingListener.forLogLevel(...)`** + **`FilteredClassLoader`** → unit-test and introspect auto-configuration under controlled classpath/property conditions. The best hands-on way to *see* conditions fire.
  - **Actuator** `conditions`, `beans`, `configprops`, `env` endpoints → runtime view of the same information.
  - **`-Dspring.aop.proxy-target-class=true`** / observing `AopAutoConfiguration.CglibAutoProxyConfiguration` in the report to confirm CGLIB vs JDK proxying; add CGLIB/`ReflectiveMethodInvocation` breakpoints to watch the advisor chain.
  - **`ApplicationStartup` / `BufferingApplicationStartup`** (startup-step instrumentation) → measure and inspect `refresh()` phases; view in the Actuator `startup` endpoint or via Java Flight Recorder.
  - **JetBrains Spring Debugger plugin** → visualizes bean wiring, `@Cacheable` contents, and auto-config decisions in the IDE.
  - For AOT/native: `mvn spring-boot:process-aot` / `-Pnative`, inspect generated sources under `target/spring-aot`, and test `RuntimeHints` with `RuntimeHintsAssertions`.

### 9. Version-currency warnings (explicit)

- **Framework 7 / Boot 4 (Nov 2025+, current):** reference docs at v7.0.x; Pro Spring 7; Halbritter and Hoeller Spring I/O 2026 talks; spring.io *Modularizing Spring Boot*; Dan Vega Boot 4 posts; InfoQ Boot 4 coverage. Trust these for structure.
- **Framework 6 / Boot 3 (2022–2025):** Pro Spring 6 with Kotlin; 토비 스프링 6; most current Baeldung/AOT articles; Deleuze 2023 AOT talks. **Conceptually sound but pre-modularization.** The container/AOP/transaction internals are essentially unchanged from 6→7, so these age *well* on core mechanics; they are wrong only on the Boot 4 module split, Jackson 3, and JSpecify.
- **Framework 5 / Boot 2 (pre-2022):** 김영한 고급편 (2021); 토비 스프링 부트 (Boot 2.7); "Kind of Magic" (2017); Chinese source-analysis repos (Spring 4.3).
  - **Structurally wrong now, not just cosmetically:** anything teaching **`META-INF/spring.factories`** for auto-config registration — this was replaced by **`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`** in Boot 2.7→3.0. And anything assuming a **single `spring-boot-autoconfigure` jar** is now wrong under Boot 4's module split (the codebase is now 70+ focused JARs; config for a technology ships only if you pull its module/starter — e.g. a `spring-boot-starter-web`→`webmvc` swap drops the auto-configuration count dramatically).
  - **Merely cosmetically dated but conceptually sound:** JDK-proxy-vs-CGLIB mechanics, the `BeanPostProcessor` pipeline, `ProxyFactory`/advisor chains, the DI container model, transaction propagation — 김영한 고급편 and 토비's DI material remain accurate on all of these.
- **The `javax.*` → `jakarta.*` namespace migration** (Boot 3.0) invalidates code in every Boot 2-era resource; treat all pre-2023 code samples accordingly.

### 10. Spring Certified Professional — worth it for internals at your level?

**Verdict: No, not as an internals forcing function — it targets usage, not internals.** The current exam (VMware/Broadcom, Spring Professional Develop 2V0-72.22; 60 items, 130 minutes, scaled pass of 300/500 ≈ 76%, cost $250 USD) covers container/DI configuration, Spring MVC/REST, Spring Boot, Spring Data/JDBC/transactions, testing, and Spring Security — i.e. correct *use* of the APIs. It touches bean lifecycle and AOP at a conceptual level, but does not probe `refresh()`, the three-level singleton cache, `ConfigurationClassPostProcessor`, or AOT internals. For a 10-year engineer it would be a low-yield exercise: the study path (Spring Academy "Spring Framework Essentials") is essentially the beginner-to-intermediate track you're explicitly filtering out. It also lags the current release — practice material still centers on the pre-Boot-4 world. Skip it unless you need the credential for procurement/HR reasons; your time is far better spent in 고급편 + source.

---

## Recommendations

**Do this, in order:**
1. **This week (free):** Read spring.io *Modularizing Spring Boot* + the InfoQ Boot 4 articles to reset your mental model to the current structure. Watch Halbritter's *Inside Spring Boot 4* and Hoeller's *Core Resilience Features in Framework 7* (both now on YouTube).
2. **Weeks 1–3 (paid ₩93,500):** 김영한 *고급편* Sections 5–14 for proxy/AOP internals, read against `AbstractAutoProxyCreator` and `ReflectiveMethodInvocation` in source. This is your highest-yield single purchase.
3. **Weeks 3–5 (paid ₩93,500):** 토비 *스프링 6* Sections 3 & 7 for the container/DI model, then trace `refresh()` → `doCreateBean` in the actual 7.0.x source using the reading order in §8.
4. **Weeks 5–7 (paid ₩77,000):** 토비 *스프링 부트* to internalize auto-config by building it — then immediately correct it with Stage 0 knowledge (`AutoConfiguration.imports`, module split). Reinforce with `ApplicationContextRunner` + `debug=true` experiments on your own Boot 4 service.
5. **Ongoing (paid ~$50):** Keep Pro Spring 7 as the desk reference; read the AOT reference chapter and Deleuze's talks when you tackle native/GraalVM.

**Benchmarks that would change this plan:**
- If a **current (Boot 4) English internals video course** appears from a credible author (e.g. a Marco Behler or Spring Academy refresh targeting Boot 4), it would displace the version-caveated Toby Boot course for the auto-config stage.
- If **Toby publishes a Framework-7 print book** (none exists today), it would become the preferred linear read over Pro Spring 7 for the container/DI portion.
- If you move to **native image in production**, promote Stage 5 (AOT) to the front and add Deleuze's talks + the AOT reference chapter as priority-1.
- If your team standardizes on writing **custom starters**, the reference "Creating Your Own Auto-configuration" chapter + `ApplicationContextRunner` testing become mandatory rather than optional.

## Caveats
- **Pricing** is in KRW at Inflearn list price and fluctuates with frequent Inflearn promotions; USD book prices are approximate. Marco Behler course pricing was not captured precisely (he runs frequent ~50%-off sales).
- **김영한 고급편 Spring version is not stated on the course page**; the Oct-2021 publish date implies Spring Boot 2.x/Framework 5.x, but this is inference, not a confirmed on-page fact. The proxy/AOP mechanics it teaches are unchanged in Framework 7 regardless. (Note: the course page and its listing show a minor discrepancy in stated runtime, ~16h 41m vs ~16h 44m — immaterial.)
- **토비 스프링 6 runtime (12h 27m / 58 lectures)** is confirmed from the Inflearn page; the course deliberately stops short of the deepest framework-implementation detail, so it is a model-builder, not a source dissection.
- **Conference-talk permanence:** YouTube IDs cited were live at time of research; Spring I/O occasionally re-hosts videos, so search by title+speaker if a link rots.
- **Baeldung and velog quality is per-article**, not per-site — the specific pieces named are the vetted-deep ones; treat the sites' broader catalogs with more skepticism.
- I did not independently verify Marco Behler's exact current course price or the full page-count/TOC of Pro Spring 7 beyond the publisher listing and source repo; treat those as directional.