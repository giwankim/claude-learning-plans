---
title: "Spring Boot + Micrometer — Foundations"
category: "Observability"
description: "A six-week, ~4 h/week prerequisite to the LGTM plan that treats Micrometer as a library with a design rather than properties copied from a blog post, on a Spring Boot 4.1 / Micrometer 1.17 baseline where Boot 4's modularization renamed starters and ended classpath-presence auto-configuration. Works through meter-type selection and naming discipline, the MeterBinder vs MeterRegistryCustomizer vs MeterFilter distinction (by reading binder source), http.server.requests tag-by-tag as the meter SLOs get built on, the Observation API end to end — conventions, handlers, and the lowCardinalityKeyValue/highCardinalityKeyValue split learned while the blast radius is a toy project — the three ways to get percentiles and why client-side ones cannot be aggregated across pods, and instrumentation tests that fail when a refactor silently drops a tag (with Boot 4's replacement of @AutoConfigureObservability). Ends exactly where the LGTM plan's Phase 1 begins."
---

# Spring Boot + Micrometer — Foundations

This is the phase the LGTM plan assumed you'd already done. Goal: understand Micrometer as a *library with a design*, not as a set of properties you copy from a blog post. Six weeks, ~4 h/week. It ends exactly where the LGTM plan's Phase 1 begins.

**Version baseline: Spring Boot 4.1 (June 2026), Micrometer 1.17.** This matters more than usual right now, because:

- **Boot 4 modularized everything.** `spring-boot-starter-web` is now `spring-boot-starter-webmvc`, every technology has its own starter, and a jar on the classpath no longer triggers auto-configuration by presence alone. Micrometer is affected directly (see Week 0).
- **Only 4.0 and 4.1 are in OSS support**; the entire 3.x line is EOL as of mid-2026. Any tutorial written for Boot 3 will have at least one wrong property name or dependency coordinate.
- This topic has attracted an unusual amount of AI-generated filler. Stick to `docs.spring.io`, `docs.micrometer.io`, and the GitHub wiki release notes. When a third-party post and the reference docs disagree, the docs win — I've seen widely-shared posts get the OTLP property namespaces wrong.

---

## Week 0 — A project that doesn't lie to you (half a day)

From `start.spring.io` on Boot 4.1: **Web** (`spring-boot-starter-webmvc`), **Actuator**, and `io.micrometer:micrometer-registry-prometheus`. Kotlin, Gradle.

Then set, explicitly:

```properties
management.endpoints.web.exposure.include=health,info,metrics,prometheus
```

Endpoint exposure defaults are conservative and changed in 4.0 — if `/actuator/prometheus` 404s, this is why, and it's the single most common "why doesn't this work" for people coming from Boot 3.

### The Boot 4 module story, because it changes the mental model

The old mental model — *"Actuator brings Micrometer"* — is no longer the whole truth. Boot 4's modularization explicitly enabled using **Micrometer metrics independently of Actuator**: you can pull in just the module that publishes metrics without the full Actuator dependency chain, which wasn't practical in Boot 3.

| You want | Depend on |
|---|---|
| Metrics only (no HTTP endpoints, no health) | `spring-boot-starter-micrometer-metrics` |
| Metrics + `/actuator/*` endpoints + health | `spring-boot-starter-actuator` |
| The Observation API without metrics or tracing | `spring-boot-micrometer-observation` |
| Tracing | `spring-boot-micrometer-tracing` + a bridge (`-brave` or `-opentelemetry`) |
| All three signals over OTLP | `spring-boot-starter-opentelemetry` |

Every starter now has a matching test starter (`spring-boot-starter-micrometer-metrics-test`, etc.), and you *do* need it in test scope. If a migration goes sideways, `spring-boot-starter-classic` gets you a Boot-3-shaped classpath to fix imports against.

Read: <https://spring.io/blog/2025/10/28/modularizing-spring-boot/> and the starters table in the [4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide#starters).

Start Actuator with only `spring-boot-starter-micrometer-metrics` and no Actuator, and see what you lose. Twenty minutes, and the module boundaries become concrete instead of trivia.

**Deliverable:** `/actuator/prometheus` returns text. Pick five metric families out of it and write down, for each, *which component registered it*. If you can't answer that for any of them, Week 2 is for you.

---

## Week 1 — Meter types, and the naming discipline

Read the Micrometer concepts section properly once: <https://docs.micrometer.io/micrometer/reference/concepts.html>

### The type decision

Four types cover almost everything, and the choice is mechanical:

| Question | Type | Prometheus output |
|---|---|---|
| Monotonically increasing count? | `Counter` | `_total` |
| Instantaneous value that goes up and down? | `Gauge` | bare name |
| A duration, and you want count + total + distribution? | `Timer` | `_seconds_count`, `_seconds_sum`, `_seconds_max` |
| A non-time magnitude (bytes, items per batch)? | `DistributionSummary` | `_count`, `_sum`, `_max` |

Then the specialised ones, which exist for reasons worth understanding: `LongTaskTimer` (measures tasks *still running* — the only way to see a job that hangs, since a `Timer` records nothing until completion), `FunctionCounter` / `FunctionTimer` (wrap a counter someone else owns, e.g. a driver's own stats), `TimeGauge`, `MultiGauge` (for a set of gauges whose tag values change over time).

### Two traps that will bite in week one

**The gauge weak reference.** `Gauge.builder("queue.size", queue) { it.size.toDouble() }` holds a **weak reference** to `queue`. If nothing else strongly references it, it's collected and the gauge reports `NaN` forever. This is the most common Micrometer bug in existence. Hold a field. Then deliberately reproduce the bug once so you recognise the symptom.

**Never publish a rate.** Export the monotonic count; let PromQL compute `rate()`. A hand-computed "requests per second" gauge can't be re-aggregated, can't be re-windowed, and silently lies across restarts.

### Naming

- Dot-separated lowercase, hierarchical, most-general-first: `order.payment.duration`, not `durationOfOrderPayment`.
- Micrometer translates per registry — `http.server.requests` becomes `http_server_requests_seconds_count` for Prometheus. Never hard-code the translated form in code.
- Base units: **seconds** for time, **bytes** for size. Micrometer and Prometheus both assume this.
- **Every meter with the same name must carry the same tag keys.** Different key sets under one name produce series that can't be aggregated, and Micrometer won't stop you.
- Global tags (`application`, `env`, `region`) go in one place:

```kotlin
@Bean
fun commonTags() = MeterRegistryCustomizer<MeterRegistry> { registry ->
    registry.config().commonTags("application", "order-service", "env", "prod")
}
```

**Deliverable:** one small Kotlin service instrumented by hand — a `Counter` of outcomes, a `Timer` on the main operation, a `Gauge` on a queue depth, a `DistributionSummary` on payload size. Write each meter twice: once through `MeterRegistry`, once via `@Timed`/`@Counted`. Note what the annotation version can and can't express (dynamic tag values, mostly). Annotations need `management.observations.annotations.enabled=true` and `aspectjweaver` on the classpath — a surprising number of people conclude annotations "don't work" without this.

---

## Week 2 — What Boot registers for you, and by what mechanism

The list is in the reference docs; the *mechanism* is the point.

**Three extension points that everyone confuses:**

| | What it does | When it runs |
|---|---|---|
| `MeterBinder` | *Registers* meters for some subsystem | once, at registry setup |
| `MeterRegistryCustomizer` | Configures the registry (common tags, naming convention) | before meters are registered |
| `MeterFilter` | Intercepts, renames, denies, or reconfigures meters as they're registered | on each meter registration |

Read the source of two or three binders — `JvmMemoryMetrics`, `ProcessorMetrics`, `DataSourcePoolMetrics`. They're short, and afterwards "Boot gives you JVM metrics for free" stops being magic. Then write your own `MeterBinder` for something in your domain.

### `http.server.requests`, in detail

This is the meter your SLOs will be built on, so understand its tags exactly:

- `uri` is the **route template** (`/orders/{id}`), not the actual path. If it were the path, you'd have one series per order ID. Understand *why* before you ever add a tag of your own.
- `outcome` (`SUCCESS`/`CLIENT_ERROR`/`SERVER_ERROR`) vs `status` (the numeric code) vs `error`/`exception`.
- What the `uri` tag becomes for an unmatched request (`NOT_FOUND`, `REDIRECTION`) and why that's protective.
- Customising it: `ServerRequestObservationConvention` (Boot 3+; the old `WebMvcTagsProvider` is gone).

### Distribution configuration by property

The `management.metrics.distribution.*` family — `percentiles`, `percentiles-histogram`, `slo`, `minimum-expected-value`, `maximum-expected-value` — applies per meter name prefix. **Verify the exact keys against Boot 4's configuration-properties appendix and the configuration changelog**, because a number of `management.*` keys moved in 4.0 and blog posts are unreliable here. Getting into the habit of checking the changelog rather than trusting prose is itself part of the learning.

One Boot 4.1 nicety worth knowing: convention beans are now picked up automatically by the auto-configured JVM metrics — declare a `JvmMemoryMeterConventions` / `JvmThreadMeterConventions` / `JvmClassLoadingMeterConventions` / `JvmCpuMeterConventions` bean and Boot wires it in, no manual re-declaration of the binders required.

**Deliverable:** an annotated dump of `/actuator/prometheus` — every metric family labelled with the binder that produced it — plus a `MeterFilter` that denies the twenty you decided you'll never query. Note the series-count difference. This is the first time you'll feel that instrumentation has a cost.

---

## Week 3 — The Observation API

This is the part that makes everything after it possible, and it's the part most tutorials skip because it postdates them.

The premise: instrument **once**, get metrics *and* traces *and* log context out of it. A `Timer` is a metric. An `Observation` is an event with a lifecycle that handlers turn into whatever signals are configured.

Read <https://docs.micrometer.io/micrometer/reference/observation/introduction.html> end to end, then the still-excellent conceptual introduction: <https://spring.io/blog/2022/10/12/observability-with-spring-boot-3/> (2022, and the best single explanation of *why* the API looks like this).

The pieces:

- `ObservationRegistry` — where handlers are registered
- `Observation` — start / stop / error / scope-open / scope-close
- `ObservationHandler` — turns lifecycle events into signals (the metrics handler makes a `Timer`; the tracing handler makes a span)
- `ObservationConvention` — *names and tags in one reusable place*, so twelve services agree
- `ObservationFilter` / `ObservationPredicate` — mutate or suppress observations
- `ObservationDocumentation` — declare your conventions as an enum, which generates documentation and keeps naming honest

### The one idea to internalise now

`lowCardinalityKeyValue` vs `highCardinalityKeyValue`. Low-cardinality keys become **metric tags**. High-cardinality keys become **span attributes only**. Learn this in week three, when the blast radius is a toy project, rather than the week you put `orderId` on a timer and take down the metrics backend.

**The single best exercise in this whole plan:** write an `ObservationHandler<Observation.Context>` that does nothing but `log.info` on each lifecycle callback, register it, and hit an endpoint. You will *see* the observations Spring creates for you — the HTTP request, the client call, the `@Observed` method — with their contexts and key-values. Ten minutes, and the API stops being abstract.

**Deliverable:** one business operation instrumented via `Observation` with a custom `ObservationConvention` — producing a metric with exactly the tags you intended and nothing more — plus the logging handler above, kept in the repo as a debugging tool.

---

## Week 4 — Percentiles, histograms, and how not to lie

Short week, high value. Everything downstream (SLOs, latency dashboards, alerting) is built on getting this right.

A `Timer` by default publishes only count, sum, and a decaying max. That gives you a mean, and the mean of a latency distribution is close to useless.

Three ways to get more, with different properties:

1. **`percentiles` (client-side)** — the JVM computes p95/p99 and ships the numbers. Cheap, *and cannot be aggregated across instances*. Averaging per-pod p99s produces a number with no statistical meaning. This is the most widespread error in Spring Boot dashboards.
2. **`percentiles-histogram` (bucket counts)** — ships bucket counts; Prometheus computes quantiles with `histogram_quantile`. Aggregatable across pods. Costs one series per bucket per tag combination.
3. **`slo` boundaries** — explicit buckets at values you care about ("under 200 ms"), which is what you actually want for an SLO.

Do this experiment, because reading it isn't the same as seeing it: run identical load against three configurations of the same endpoint and compare the p99 each reports. Then aggregate two instances and watch approach (1) give you a number that's simply wrong.

Then learn the query that consumes it, including the ordering that trips everyone:

```promql
histogram_quantile(0.99, sum by (le, uri) (rate(http_server_requests_seconds_bucket[5m])))
```

The `sum by (le)` must come *before* `histogram_quantile`. Reversed, it silently returns nonsense.

**Deliverable:** a one-page note — which of the three you'd use for `http.server.requests`, why, and what it costs in series count.

---

## Week 5 — Testing instrumentation, and a first real backend

### Testing

Instrumentation rots silently: a refactor drops a tag, nothing fails, and you find out during an incident six months later. So:

- **Unit tests:** `SimpleMeterRegistry`, then assert with `MeterRegistryAssert` from `micrometer-test`. Assert the meter *name and tag keys*, which is what breaks.
- **Integration tests:** metrics export is disabled under `@SpringBootTest` by default. In Boot 4, `@AutoConfigureObservability` has been **removed** in favour of the finer-grained `@AutoConfigureMetrics` and `@AutoConfigureTracing`, backed by `spring-boot-micrometer-metrics-test` and `spring-boot-micrometer-tracing-test`. Every Boot 3 tutorial gets this wrong now.

You already run Testcontainers with Podman, so this is comfortable ground — note that Boot 4 manages **Testcontainers 2.0**, where modules are prefixed `testcontainers-` and container classes moved packages.

### A backend, briefly

Prometheus + Grafana via Docker Compose. Scrape `/actuator/prometheus`. Then build **one** dashboard by hand — RED for a single endpoint: request rate, error rate, p99 latency. Do it manually exactly once, so that when you later generate dashboards from code you know what the JSON means.

**Deliverable:** a test that fails if the main endpoint's timer loses a tag. That test is the difference between instrumentation that survives two years of refactoring and instrumentation that doesn't.

---

## Reference shelf (deliberately short)

**Primary, in reading order**
1. Micrometer concepts + Observation reference — <https://docs.micrometer.io/micrometer/reference/>
2. Actuator reference: [Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html), [Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html), [Tracing](https://docs.spring.io/spring-boot/reference/actuator/tracing.html)
3. "Observability with Spring Boot 3" — <https://spring.io/blog/2022/10/12/observability-with-spring-boot-3/> — the conceptual on-ramp
4. "Modularizing Spring Boot" — <https://spring.io/blog/2025/10/28/modularizing-spring-boot/>
5. "OpenTelemetry with Spring Boot" — <https://spring.io/blog/2025/11/18/opentelemetry-with-spring-boot/> — read at the end of Week 5, as the bridge into the LGTM plan
6. Boot 4.0 and 4.1 release notes + configuration changelogs (GitHub wiki) — the only reliable source for property renames

**Code to read** (all short enough for one sitting)
- `io.micrometer.core.instrument`: `Counter`, `Timer`, `MeterFilter`, `DistributionStatisticConfig`
- `io.micrometer.observation`: `Observation`, `ObservationHandler`, `ObservationRegistry`
- Boot's `spring-boot-micrometer-metrics` auto-configuration
- Any `MeterBinder` implementation

**Talks** — Jonatan Ivanov and Marcin Grzejszczak (Micrometer maintainers) on the Observation API at SpringOne / Devoxx / GOTO. Maintainer talks are the closest thing to design-rationale documentation this project has.

**No book required.** There isn't a current, good, Micrometer-specific book, and the reference docs are genuinely well written. Brazil's *Prometheus: Up & Running* (2nd ed.) is worth buying at the *end* of this plan, when you start querying seriously.

---

## Gotcha list — read this once now, again in Week 3

1. `/actuator/prometheus` 404s → `management.endpoints.web.exposure.include`.
2. Gauge reports `NaN` → weak reference collected. Hold a field.
3. `@Timed` / `@Observed` do nothing → missing `management.observations.annotations.enabled=true` and/or `aspectjweaver`.
4. Metrics absent in tests → `@AutoConfigureMetrics` (not the removed `@AutoConfigureObservability`).
5. `spring-boot-starter-web` not found → it's `spring-boot-starter-webmvc` now.
6. A dependency's auto-configuration doesn't kick in → in Boot 4 you need its starter/module, not just the jar.
7. Averaged percentiles across pods. Wrong number, looks plausible, survives code review.
8. A tag with unbounded values (`userId`, `orderId`, raw URI path) → this is how metrics backends die.
9. Same meter name registered with different tag key sets → unaggregatable series.
10. Hand-computed rate gauges instead of counters.

---

## Where this hands off

At the end of Week 5 you can answer: what a meter is, who registered it, what its tags cost, how to add your own without wrecking cardinality, how percentiles get computed and where they lie, and how to test that any of it still works.

That's the assumed starting point of the LGTM plan — go straight to its Phase 1 (`grafana/otel-lgtm`, Boot 4 OTLP wiring, correlating the three signals). Phase 0 of that plan is worth doing first regardless, since it's methodology rather than tooling.

**Suggested compression if you want to move faster:** Weeks 0–2 can collapse into one week if you're willing to read source instead of docs. Do not compress Weeks 3 and 4 — the Observation API and the histogram material are where the leverage is, and they're the two things nearly everyone skips.
