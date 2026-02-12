---
title: "buildSrc vs build-logic"
category: "Build Tools"
description: "Comparing convention plugin approaches in Gradle"
---

# buildSrc vs build-logic (Included Builds) in Multi-Project Gradle Builds

This document summarizes trade-offs between using **`buildSrc`** and a **`build-logic` included build** (composite build) for sharing Gradle build logic (convention plugins, custom tasks, helpers) in a multi-project Gradle setup.

---

## 1) What each approach is

### buildSrc
- A special directory at the root of your build.
- Gradle automatically compiles it and places its classes on the buildscript classpath for **all projects**.
- “Zero configuration” to get started.

### build-logic included build
- A dedicated Gradle build (commonly `build-logic/`) included via `includeBuild("build-logic")` in `settings.gradle(.kts)`.
- Produces plugins (often convention plugins) that you apply via plugin IDs.
- Treated like an external dependency: clearer boundaries and selective application.

---

## 2) Build performance

### buildSrc
**Pros**
- Simple, minimal wiring.
- For small builds, performance impact is usually negligible.

**Cons**
- Any change in `buildSrc` tends to invalidate large parts of the build:
  - Rebuilds `buildSrc` first
  - Forces re-evaluation of build scripts across projects
- Becomes costly in large multi-module builds or while iterating on build logic.

### build-logic included build
**Pros**
- Finer-grained invalidation:
  - Only projects using the changed plugin are impacted
- Better iteration speed when actively developing build logic
- Scales better with many modules and diverse conventions

**Cons**
- Small upfront setup cost (structure + `includeBuild`).

---

## 3) Caching & incremental builds

### buildSrc
- Changes in `buildSrc` can broadly invalidate:
  - up-to-date checks
  - build cache hits
  - configuration caching effectiveness (because the build logic classpath changes globally)

### build-logic included build
- Better cache granularity:
  - only tasks/projects affected by the changed plugin tend to become out-of-date
  - unrelated modules can still be up-to-date or FROM-CACHE
- Generally plays nicer with large-scale caching (especially CI + remote caches).

---

## 4) IDE support (IntelliJ / autocomplete / navigation)

### buildSrc
**Pros**
- IDE imports it automatically as part of the main build.
- Great code navigation/completion for build logic.

**Cons**
- Testing build logic in `buildSrc` can be slightly awkward (historically less “normal project” feel).

### build-logic included build
**Pros**
- Imported like a standard Gradle project/module(s).
- Typically easier to run/debug tests for build logic.
- Encourages clean project boundaries and discoverability.

**Cons**
- Newcomers must learn “there is a separate included build for build logic” (minor).

---

## 5) Dependency & version management

### buildSrc
**Pros**
- Easy to put shared constants/utilities in one place.
- Anything on `buildSrc` classpath is implicitly available everywhere.

**Cons**
- Classpath “globalness” can lead to surprises:
  - dependencies in `buildSrc` may shadow or interact with plugin classpaths
  - harder to reason about “where did this dependency come from?”
- No real versioning/release model for buildSrc itself.

### build-logic included build
**Pros**
- Treated like a real dependency:
  - explicit plugin IDs
  - normal dependency resolution semantics
- Easier to manage, test, and evolve build logic as a product.

**Cons**
- Requires “plugin packaging mindset” (a positive trade in most medium/large builds).

> Tip: In both setups, prefer **Version Catalogs (`libs.versions.toml`)** for dependency version centralization where possible.

---

## 6) Modularity & isolation

### buildSrc
- One bucket, globally visible.
- Hard to “apply only the parts you need” per module.
- Tends to grow monolithic unless carefully organized.

### build-logic included build
- Naturally modular:
  - multiple convention plugins for different module types (e.g., `java-library`, `kotlin-service`, `android-app`)
  - apply only what a project needs
- Clearer isolation: changes to one plugin don’t necessarily impact unrelated modules.

---

## 7) Developer experience & onboarding

### buildSrc
**Pros**
- Fastest to start.
- “It’s just there” is easy to understand initially.

**Cons**
- As it grows, it can become a dumping ground.
- Changes can slow the whole build, frustrating day-to-day iteration.

### build-logic included build
**Pros**
- More explicit structure: build logic is a real project.
- Encourages tests, documentation, and separation.
- Typically smoother at scale.

**Cons**
- Slightly more concepts upfront (included builds + plugin IDs).

---

## 8) Maintainability & scalability

### buildSrc
- Fine for small builds and minimal logic.
- Risk of becoming a monolith and a performance bottleneck as the build grows.

### build-logic included build
- Better long-term maintainability:
  - separate modules/plugins
  - clearer ownership
  - incremental adoption
- Better scalability for large builds and organizations.

---

## 9) Publishing & reuse across projects

### buildSrc
- Not designed for reuse across repositories.
- Copy/paste is common (and painful).

### build-logic included build
- Straight path to reuse:
  - keep as an included build shared across multiple repos, or
  - publish convention plugins to an internal repository with versioning
- Supports proper lifecycle (versioning, release notes, compatibility strategy).

---

## 10) When to choose which

### Prefer buildSrc when…
- Your build is small and build logic is minimal.
- You want the lowest setup overhead.
- You’re prototyping conventions quickly.
- (Rare edge) You rely on buildSrc’s special classpath behavior (generally avoid; brittle).

### Prefer build-logic included build when…
- You have many modules or expect growth.
- You want better incremental behavior and caching.
- You have different module “types” needing different conventions.
- You want clean modularity, testing, and long-term maintainability.
- You want to reuse/share build logic across repos.

---

## 11) Practical migration notes

- Migration is usually straightforward:
  - move `buildSrc/` code into `build-logic/`
  - add `includeBuild("build-logic")` in `settings.gradle(.kts)`
  - package logic as convention plugins and apply via plugin IDs
- Use the migration as a chance to:
  - split monolithic build logic into multiple plugins
  - add tests (Gradle TestKit) for critical conventions
  - reduce cross-project “global” configuration

---

## Short conclusion

- **buildSrc**: great for small projects and fast prototyping; can become global, monolithic, and costly at scale.
- **build-logic included build**: slightly more setup, but better performance characteristics, modularity, cache behavior, and reuse—usually the better long-term choice for multi-project builds.
