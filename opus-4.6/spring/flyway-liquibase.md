---
title: "Flyway vs Liquibase vs Atlas"
category: "Data & Messaging"
description: "Comparing database migration tools for Spring Boot Kotlin with MySQL/Aurora"
---

# Database migration tools for Spring Boot Kotlin with MySQL/Aurora

**Flyway and Liquibase remain the two dominant migration tools in the Spring Boot ecosystem, but both face licensing turbulence heading into 2026, while declarative newcomer Atlas emerges as a serious third option.** For a Kotlin/Spring Boot team targeting MySQL/Aurora MySQL, the choice hinges on whether you value Flyway's radical simplicity and clean Apache 2.0 license, Liquibase's free rollback and diff capabilities (now under a controversial FSL license), or Atlas's Terraform-like declarative paradigm. Korean tech companies overwhelmingly favor Flyway—Toss Bank confirmed its use from system inception—while global tech giants at Netflix, Stripe, GitHub, and Uber have all built custom migration infrastructure at scale.

---

## How Liquibase works and where it differs from Flyway

Liquibase organizes database changes around **changesets** within **changelog** files. Each changeset carries a unique `id + author + filepath` triple, and Liquibase tracks applied changesets in a `DATABASECHANGELOG` table with MD5 checksums that detect unauthorized modifications. A companion `DATABASECHANGELOGLOCK` table prevents concurrent executions. Changesets execute top-to-bottom within the changelog, and Liquibase skips already-applied ones unless `runAlways` or `runOnChange` flags override this behavior.

The tool supports four changelog formats—**XML** (most mature, with XSD validation), **YAML** (popular in Spring/Kotlin projects), **JSON**, and **formatted SQL** (with special comment annotations). The XML/YAML/JSON formats use ~40 built-in "change types" (`createTable`, `addColumn`, `renameColumn`) that abstract database-specific DDL. This abstraction enables Liquibase's headline feature: **automatic rollback generation** for roughly 15 change types. A `createTable` automatically generates `DROP TABLE` on rollback; `addColumn` generates column removal; `renameColumn` reverses the rename. This works only with the DSL formats—formatted SQL changesets require manually defined rollback blocks, putting them on equal footing with Flyway's approach.

Flyway takes a fundamentally different philosophy. It is **SQL-first by design**: you write plain SQL migration scripts named `V1__Create_table.sql`, drop them in `db/migration`, and Flyway applies them sequentially. Convention over configuration. The learning curve is near-zero for anyone who knows SQL. This simplicity comes with tradeoffs: **Flyway Community offers no rollback capability at all**—undo migrations require Enterprise tier. No diff tool, no dry-run, no preconditions in the free tier. Liquibase Community provides all of these.

The core philosophical tension is clear. Flyway optimizes for the **80% case** where teams write SQL migrations for a single database and want minimal ceremony. Liquibase optimizes for the **enterprise case** where teams need rollbacks, multi-database portability, selective deployment via contexts/labels, and conditional execution via preconditions.

### Feature-by-feature breakdown

| Capability | Flyway Community | Liquibase Community |
|---|---|---|
| Migration formats | SQL, Java/Kotlin | SQL, XML, YAML, JSON |
| Rollback | ❌ (Enterprise only) | ✅ Auto-generated for DSL types |
| Schema diff | ❌ (Enterprise only) | ✅ `diff` and `diff-changelog` |
| Dry-run SQL preview | ❌ (Enterprise only) | ✅ `update-sql` |
| Preconditions | ❌ | ✅ Built-in |
| Snapshots | ❌ | ✅ |
| Repeatable migrations | ✅ `R__` prefix | ✅ `runAlways` attribute |
| Callbacks/lifecycle hooks | ✅ Rich set (beforeMigrate, afterMigrate, etc.) | Limited |
| Java/Kotlin-based migrations | ✅ Native, mature API | ✅ Custom change classes |
| Database support | 22+ | 50+ (including NoSQL) |
| Contexts/labels | ❌ | ✅ Environment and feature filtering |

---

## Spring Boot integration and Kotlin/Gradle setup

Both tools enjoy **first-class Spring Boot auto-configuration**. Adding `org.liquibase:liquibase-core` to the classpath triggers `LiquibaseAutoConfiguration`, which runs migrations on startup before JPA/Hibernate initialization. Flyway works identically with `org.flywaydb:flyway-core` (plus `flyway-mysql` for MySQL). Spring Boot 4.0+ introduces dedicated starters: `spring-boot-starter-flyway` and `spring-boot-starter-liquibase`.

For a Kotlin/Gradle project targeting MySQL/Aurora MySQL, the Liquibase setup in `build.gradle.kts` is minimal:

```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.liquibase:liquibase-core")  // version managed by Spring BOM
    runtimeOnly("com.mysql:mysql-connector-j")
}
```

Configuration in `application.yml` points to the master changelog (default: `classpath:/db/changelog/db.changelog-master.yaml`) and sets `spring.jpa.hibernate.ddl-auto=none`. Liquibase's `spring.liquibase.*` namespace exposes **20+ properties** including `contexts`, `label-filter`, `default-schema`, `drop-first`, `rollback-file`, and `test-rollback-on-update`. Flyway's `spring.flyway.*` namespace offers comparable breadth with `locations`, `baseline-on-migrate`, `out-of-order`, and `clean-disabled`.

**Flyway edges ahead slightly in Spring Boot setup simplicity**—drop SQL files in `db/migration` and it works. Liquibase requires understanding the changelog/changeset structure. However, Liquibase's YAML format pairs naturally with Spring Boot's YAML-first configuration culture, and its contexts/labels provide deployment flexibility that Flyway simply cannot match in the free tier.

One practical Kotlin-specific note: Flyway's Java migration API works seamlessly from Kotlin for complex data transformations. Some community friction has been reported with the Liquibase Gradle plugin when configuring JPA entity diffing in Kotlin projects, though this affects only the optional diff-changelog workflow, not core migration execution.

---

## Liquibase contexts, labels, and environment-specific migrations

Liquibase's **contexts** and **labels** system solves a problem Flyway handles clumsily (or not at all): running different migrations in different environments. Contexts are environment-level filters—mark a changeset with `context: "test"` and it only runs when the `test` context is active. Labels are feature/version tags—mark a changeset with `labels: "v1.2, JIRA-1234"` and filter at deployment time with expressions like `--label-filter="v1.2 and !hotfix"`.

The key architectural distinction: **contexts allow complex boolean expressions in the changeset definition** (author controls filtering), while **labels allow complex boolean expressions at runtime** (deployer controls filtering). You can use both simultaneously—contexts for environments, labels for feature sets. A critical gotcha: running Liquibase without specifying any context deploys **all** changesets, including context-restricted ones. Use the `@` prefix for mandatory context specification.

---

## The 2025-2026 licensing earthquake

Both tools underwent **significant licensing changes** that fundamentally alter the decision calculus.

**Flyway** eliminated its mid-tier Teams edition in May 2025. New customers now face a binary choice: **Community (free, Apache 2.0)** or **Enterprise (contact sales)**. This removed the affordable path to undo migrations, dry-run, and drift detection. Flyway Community remains Apache 2.0 licensed with no commercial restrictions, but the feature gap between free and paid widened substantially.

**Liquibase** changed its Community edition from Apache 2.0 to the **Functional Source License (FSL)** with version 5.0 in September 2025. FSL is explicitly **not open source** per the OSI definition—it restricts competing commercial use for two years before reverting to Apache 2.0. The impact has been severe: **Keycloak** (CNCF project) opened a blocking issue since CNCF prohibits source-available licenses. The Apache Software Foundation is evaluating FSL compatibility. Spring Boot is tracking the issue. Liquibase 5.0+ also ships without bundled extensions and drivers, requiring users to manage dependencies via a new package manager (`liquibase lpm`).

**For a Spring Boot/Kotlin team**, Flyway Community's Apache 2.0 license presents zero compliance risk. Liquibase's FSL may create issues depending on organizational open-source policies. Staying on Liquibase 4.x (Apache 2.0) is an option but risks falling behind on updates and security fixes.

| Licensing dimension | Flyway Community | Liquibase Community 5.0+ |
|---|---|---|
| License | Apache 2.0 | FSL (not OSI-approved) |
| Commercial restrictions | None | Cannot compete commercially with Liquibase |
| CNCF/ASF compatible | ✅ | ⚠️ Under review |
| Free rollback | ❌ | ✅ |
| Free diff/dry-run | ❌ | ✅ |

---

## Alternative tools and the declarative paradigm shift

### Atlas: Terraform for databases

**Atlas** by Ariga is the fastest-growing alternative, taking a **declarative, schema-as-code** approach. Developers define desired database state in HCL or SQL; Atlas computes the diff and generates migration plans automatically. It uniquely supports a **hybrid workflow**: declarative locally for fast iteration, versioned migrations for production via `atlas migrate diff`. Built in Go (no JVM dependency), Atlas offers a **Kubernetes Operator** with `AtlasSchema` and `AtlasMigration` CRDs, ArgoCD integration, and **50+ built-in analyzers** for migration linting (destructive change detection, table lock analysis, data loss risks). MySQL is fully supported. The tradeoff: Atlas lacks Flyway/Liquibase's native Spring Boot auto-configuration—it operates as an external tool rather than an embedded library.

### Bytebase: database DevOps platform

Bytebase positions itself as **"GitHub/GitLab for database DevSecOps"**—a web-based collaboration platform rather than a library. It provides GUI-driven approval workflows, **200+ SQL lint rules**, batch changes across multi-tenant databases, dynamic data masking, and drift detection. It supports 20+ databases including MySQL. Pricing starts free (20 users, 10 instances) with Pro at **$20/user/month**. Bytebase does not integrate into Spring Boot at the application level; it manages database changes externally. Notable customers include Tencent, BYD, Red Hat, and reportedly Kakao.

### Other notable tools

**SchemaHero** is a CNCF Sandbox Kubernetes operator for declarative schema management via CRDs. Ideal for EKS deployments with GitOps workflows, but limited to PostgreSQL and MySQL, with a smaller community and no support for complex imperative data migrations. **Sqitch** uses an explicit **dependency graph** rather than sequential versions, solving parallel development conflicts common with Flyway's linear numbering. Each change has deploy, revert, and verify scripts. **dbmate** is a lightweight Go binary using pure SQL with `-- migrate:up` and `-- migrate:down` sections—perfect for polyglot microservice teams wanting one tool across all languages. **MyBatis Migrations** offers SQL migrations with `-- @UNDO` sections for MyBatis users, but lacks an official Spring Boot starter. **jOOQ Migrations** remains **experimental** (marked `@Experimental` since jOOQ 3.14); the jOOQ team officially recommends using Flyway alongside jOOQ.

### Migration-based vs declarative paradigms

The industry is shifting toward declarative approaches, but both paradigms have clear sweet spots:

- **Migration-based (Flyway, Liquibase, Sqitch, dbmate)**: Best for regulated environments needing explicit change approval, complex data migrations requiring specific ordering, and teams with established code review processes. The accumulated migration file count (hundreds or thousands over years) and the inability to see current schema state at a glance are real downsides.

- **Declarative (Atlas, SchemaHero)**: Best for rapid development, Kubernetes/GitOps environments, and multi-tenant architectures. The single source of truth for schema state is powerful, but **rename detection remains fundamentally unsolvable**—declarative tools cannot distinguish a column rename from a drop-and-create, risking data loss without human oversight.

- **Hybrid (Atlas's approach)**: Emerging as the pragmatic middle ground. Define state declaratively, generate versioned migration files for production review and approval.

---

## Decision matrix for Spring Boot Kotlin with MySQL/Aurora

| Factor | Flyway | Liquibase | Atlas | Bytebase |
|---|---|---|---|---|
| **Spring Boot integration** | ★★★★★ Native | ★★★★★ Native | ★★☆☆☆ External | ★☆☆☆☆ Platform |
| **MySQL/Aurora compatibility** | ★★★★★ Verified | ★★★★☆ Supported | ★★★★☆ Supported | ★★★★☆ Supported |
| **Learning curve** | ★★★★★ Minimal | ★★★☆☆ Moderate | ★★★☆☆ Moderate | ★★☆☆☆ Platform learning |
| **Small team (≤5 devs)** | ★★★★★ Ideal | ★★★★☆ Good | ★★★☆☆ Overhead | ★★☆☆☆ Overkill |
| **Large org (50+ devs)** | ★★★☆☆ Limited | ★★★★☆ Good | ★★★★☆ Good | ★★★★★ Ideal |
| **Free rollback** | ❌ | ✅ | ✅ | ✅ |
| **CI/CD maturity** | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★★☆ |
| **Kubernetes/EKS native** | ★★☆☆☆ | ★★☆☆☆ | ★★★★★ Operator | ★★★☆☆ |
| **License clarity** | ★★★★★ Apache 2.0 | ★★☆☆☆ FSL | ★★★★☆ Apache 2.0 | ★★★☆☆ Mixed |
| **Community/ecosystem** | ★★★★★ ~9.5K GitHub stars | ★★★☆☆ ~3.9K stars | ★★★☆☆ Growing | ★★★☆☆ Growing |
| **Multi-database portability** | ★★☆☆☆ SQL-specific | ★★★★★ DSL-agnostic | ★★★★☆ HCL-agnostic | ★★★★☆ |

---

## Real-world adoption across Korean and global tech

### Korean tech companies favor Flyway

**Toss Bank** is the strongest confirmed data point: their SLASH 22 conference talk explicitly states they adopted **Flyway with Hibernate DDL Validation from system inception** across all microservices (user, terms, product, loan servers) running Kotlin/Spring Boot on Kubernetes. **Woowahan Brothers** (Baemin) hasn't published a definitive statement, but their tech course curriculum teaches Flyway, and their tech blog explicitly advises "don't use hibernate.hbm2ddl.auto; use Flyway instead"—strong indirect evidence. **LINE** (LY Corp) documented Flyway usage in their Spring Boot 2→3 migration, noting compatibility issues with MySQL 5.7 support being dropped in Flyway 7.16+. Kakao, Coupang, and Naver have no publicly confirmed tool choices, though Bytebase lists Kakao among its customers.

The Korean developer community **overwhelmingly favors Flyway**. Across velog.io, Woowahan tech blog, Tecoble, and Popit, virtually all migration tool tutorials and adoption stories focus on Flyway. The reasons cited consistently: SQL-first simplicity matching JPA/Hibernate workflows, strong Spring Boot auto-configuration, and lower learning curve. Korean developers frequently mention the **JPA Buddy (now JPA Assist)** IntelliJ plugin as a companion for generating Flyway migration diffs from entity changes.

A common production pattern described in Korean engineering posts: **Flyway enabled in local/dev/test environments for automatic migration, but disabled in production** where DDL changes are manually reviewed and applied by DBAs. This pragmatic approach acknowledges that large DDL operations on production tables with hundreds of millions of rows can take hours and need careful orchestration beyond what Flyway manages.

### Global tech giants build custom tools

At scale, **every major tech company builds custom migration infrastructure**. Netflix built the **Data Gateway Platform** for traffic shadowing during storage engine migrations and recently automated migration of ~400 PostgreSQL clusters from RDS to Aurora. Stripe built a **Data Movement Platform** using a 4-step dual-writing pattern for zero-downtime migrations across thousands of database shards, processing 5 million queries per second. GitHub created **gh-ost** (open-sourced under MIT), a triggerless online schema change tool for MySQL using binary log streaming—enabling schema changes multiple times daily in production. Uber built **Schemaless** on MySQL, migrating tens of petabytes from PostgreSQL with custom tooling.

The pattern is consistent: companies use Flyway/Liquibase until roughly **Series C / 100+ engineers**, then build custom tools when they need zero-downtime DDL on billion-row tables, cross-datacenter replication coordination, shard management, and traffic shadowing capabilities that no off-the-shelf tool provides.

---

## Conclusion: what to choose and why it matters now

The 2025-2026 licensing changes have created a genuine inflection point. **For a Spring Boot Kotlin team with MySQL/Aurora MySQL starting today, Flyway remains the default recommendation**: its Apache 2.0 license is unambiguous, its Spring Boot integration is the simplest in the ecosystem, the Korean developer community provides abundant resources and patterns, and its SQL-first approach requires no additional DSL learning. The lack of free rollback is a real limitation, but most production teams disable automated rollback anyway, preferring forward-only migrations with manual DBA oversight for critical changes.

**Choose Liquibase** if free rollback, diff, and dry-run capabilities are non-negotiable and your organization accepts the FSL license. Pin to **Liquibase 4.x (Apache 2.0)** if FSL is a blocker but you need Liquibase features—though this increasingly becomes a dead-end as updates cease.

**Evaluate Atlas seriously** if your team operates in a Kubernetes/GitOps environment (especially EKS), wants declarative schema management, or needs a tool that works across polyglot services. Its hybrid declarative-plus-versioned approach and Go-based architecture (no JVM dependency for the migration tool itself) represent the direction the industry is heading, though its Spring Boot integration story is still immature compared to the incumbents.

The most important insight from researching real-world adoption: **the tool matters less than the discipline**. Toss Bank runs Flyway successfully at banking-grade scale. The Korean community's pragmatic pattern—automated migrations in dev, manual DBA-reviewed changes in production—works regardless of which tool generates the SQL. Pick the tool that fits your team's workflow today, keep your migrations in version control, and never let Hibernate manage your production schema.