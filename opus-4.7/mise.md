---
title: "Senior Developer's Guide to mise on macOS"
category: "Developer Tools"
description: "Migrating from SDKMAN/nvm/pyenv to mise (2026.4.x) on Apple Silicon — polyglot version management, task runner, and per-directory env, with copy-pasteable mise.toml configs for Python, Node/TS, Spring Boot Kotlin, and polyglot monorepos"
---

# A senior developer's guide to mise on macOS

**mise replaces SDKMAN, nvm, pyenv, direnv, and most of your Makefiles with one fast Rust binary** — and as of the `2026.4.x` release line, it is genuinely production-ready for the polyglot Python/Node/JVM stack you're running. The migration from SDKMAN is mechanical (mise even reads `.sdkmanrc` natively), the Spring Boot + Kotlin story is clean once you understand that mise pins the JDK while the Gradle wrapper still owns the build, and the team-friendly bits (`mise.lock`, `mise.local.toml`, `jdx/mise-action@v4`) close the reproducibility gap that older asdf-style setups suffered from. The catches are real but small: a recently-patched trust-bypass CVE, a known lockfile-location bug when `mise.local.toml` exists, a mandatory `usage`-syntax migration before mise `2026.11.0`, and Gradle's still-unresolved inability to auto-detect mise-managed JDKs. This guide walks from concepts to working configs for each of your stacks, and ends with copy-pasteable `mise.toml` files for Python, Node/TS, Spring Boot Kotlin, and a polyglot monorepo.

---

## Why mise, and what exactly it is

mise (pronounced "meez", from French *mise en place*) is a Rust-rewritten descendant of `asdf` that has grown into three tools fused into one: a **polyglot version manager**, a **task runner**, and a **per-directory environment manager**. It was named `rtx` until January 2024 — you'll occasionally still see that name in old blog posts — and its author Jeff Dickey (`@jdx`) declared it feature-complete entering 2025, with subsequent releases focused on refinement and a quieter calver release cadence (current stable: **`2026.4.22`**, released 2026-04-25).

The single-tool argument is the strongest one for your situation. Today you almost certainly run SDKMAN for JDK/Maven/Gradle, possibly nvm for Node, possibly pyenv or `uv` for Python. Each ships a Bash hook that fires on every shell prompt and on every `cd`. SDKMAN's hook alone is 30–300 ms; nvm's is famously worse. mise replaces that whole stack with a single ~10 ms Rust hook (≈4 ms when no config has changed), a single `mise.toml` per project, and one CI action. The performance difference is the most-cited reason teams switch — Edge Payments reported "up to 7× faster installs" on migration; the GitLab Development Kit officially dropped asdf support on July 31, 2025 and made mise its only supported manager.

The polyglot point matters even more for a senior dev who jumps between Python data work, Node tooling, and a Spring Boot Kotlin codebase in a single afternoon. **One config file pins everything**: JDK distribution and version, Gradle, Node and pnpm, Python, `uv`, Terraform, kubectl, plus arbitrary CLI tools from the registry of ~900 entries.

---

## Installation and shell integration on macOS M2

On Apple Silicon, mise ships native ARM64 binaries; the only thing that differs from Intel is the URL/architecture of the binary itself. Three install paths are reasonable:

```bash
# Option A: Homebrew — auto-updated by `brew upgrade`
brew install mise

# Option B: curl installer — installs to ~/.local/bin/mise
curl https://mise.run | sh

# Option C: signed/verified install (paranoid mode)
gpg --keyserver hkps://keys.openpgp.org --recv-keys 24853EC9F655CE80B48E6C3A8B81C9D17413A06D
curl https://mise.jdx.dev/install.sh.sig | gpg --decrypt > install.sh
sh ./install.sh
```

Homebrew is the simplest choice for a Mac. **Important caveat**: if you install via Homebrew, do not use `mise self-update` — let `brew upgrade mise` handle it.

### Shell activation: `activate` versus shims

mise has two ways to put its tools in your PATH, and you should understand both because IDE integration depends on it.

The `mise activate` mode hooks into your shell prompt; before each prompt, mise's `hook-env` recomputes PATH and environment variables based on the current directory. This is the **fast path with full features** (per-directory `[env]` vars, hooks like `enter`/`leave`/`watch_files`, templates, environment overlays). The cost is roughly 4 ms when nothing has changed and ~14 ms on a full reload. It only works inside a real interactive shell — IDEs and GUI apps that launch processes directly won't see it.

The shim mode adds `~/.local/share/mise/shims/` to PATH; each shim is a small Rust binary that intercepts the call, figures out which version of the tool to use, and re-execs the real one. Shims work everywhere — IDEs, scripts, GUI apps, cron — but **only the tool versions get resolved**; arbitrary `[env]` vars defined for the project are *not* set in the IDE process unless a shim is invoked.

The recommended setup on macOS is **both**, layered:

```bash
# ~/.zshrc — interactive shell, full power
eval "$(mise activate zsh)"

# ~/.zprofile — non-interactive (IDEs launched from Finder, GUI apps)
eval "$(mise activate zsh --shims)"
```

For bash users, swap `zsh` → `bash` and `.zshrc`/`.zprofile` → `.bashrc`/`.bash_profile`. For fish, use `mise activate fish | source` inside `if status is-interactive` and the `--shims` variant in the `else` branch. After editing, run `exec zsh` and verify with `mise doctor`, which checks activation status, PATH ordering, shim configuration, integrity of installed tools, and any untrusted configs. Treat `mise doctor` as the canonical "is everything wired correctly?" command.

### Trust: a small ceremony with real teeth

Because `mise.toml` can run code (via `_.source`, hooks, tasks, and template `exec()`), mise refuses to load a config it hasn't seen marked as trusted. The first time you `cd` into a new repo, you'll get:

```
mise ~/work/myproj/mise.toml is not trusted. Trust it? [y/n]
```

Run `mise trust` once per repo. Bulk-trust an entire workspace tree with `trusted_config_paths = ["~/work"]` in `~/.config/mise/config.toml`. **Security note**: the recently-disclosed advisory **GHSA-436v-8fw5-4mj8 / CVE-2026-35533** allowed a malicious `mise.toml` in a fork to bypass trust by setting `trusted_config_paths`/`yes`/`ci`/`paranoid` itself; this is patched in later 2026.x releases but is the reason you should keep mise current and avoid running `mise install` on unvetted PRs from forks until your CI is on a patched version.

---

## Configuration file resolution: the mental model

mise walks **upward** from the current directory collecting every config it sees, then merges them with closer-to-cwd taking precedence. In a project, the precedence (top wins) is:

1. `mise.{MISE_ENV}.local.toml` — env-scoped personal overrides
2. `mise.local.toml` — personal overrides (gitignored)
3. `mise.{MISE_ENV}.toml` — env-scoped shared (e.g., `mise.production.toml`)
4. `mise.toml` — main shared config
5. `.tool-versions` — asdf-compatible, lowest precedence

Above the project, your global config at `~/.config/mise/config.toml` is merged at lower priority, with system-wide `/etc/mise/config.toml` lowest of all.

**The 2026 filename convention is `mise.toml` (no leading dot)**, settled in discussion #2206. The dotted variant `.mise.toml` still works for backward compat, but `mise use` writes the non-dotted form, and the docs use it canonically. Pick one per repo and don't mix.

One breaking change to know if you migrate from pyenv/nvm: as of mise **`2025.10.0`**, `.python-version`, `.nvmrc`, `.java-version`, and `.sdkmanrc` files are **no longer auto-honored by default** — these "idiomatic version files" are now opt-in per tool:

```toml
# in mise.toml or ~/.config/mise/config.toml
[settings]
idiomatic_version_file_enable_tools = ["node", "python", "java"]
```

This was deliberate: with `uv` writing `.python-version` files, mise was triggering Python installs people didn't want. The fix is one line of config per repo, but it's the single biggest stumbling block for migrators today.

---

## Migrating from SDKMAN

Your existing setup is straightforward to translate. First, **audit what SDKMAN is currently managing**:

```bash
sdk current                              # active versions across all candidates
ls ~/.sdkman/candidates                  # one dir per candidate (java, maven, gradle, kotlin, …)
ls ~/.sdkman/candidates/java/            # versions + a `current` symlink
```

Then translate. mise covers the entire SDKMAN candidate list you actually use day-to-day — `java`, `maven`, `gradle`, `kotlin`, `scala`, `groovy`, `sbt`, `jbang`, `ant`, `leiningen` — and even **more JDK distributions than SDKMAN** out of the box (Microsoft, SAP Machine, Dragonwell, in addition to Temurin/Zulu/Corretto/Liberica/GraalVM Community/OpenJDK). The translation table for the SDKMAN suffixes you'll see in `.sdkmanrc`:

| `.sdkmanrc` value | mise.toml equivalent |
|---|---|
| `21.0.4-tem` | `java = "temurin-21.0.4"` |
| `21-zulu` | `java = "zulu-21"` |
| `21-amzn` | `java = "corretto-21"` |
| `21-librca` | `java = "liberica-21"` |
| `22-graalce` | `java = "graalvm-community-22"` |
| `21-ms` | `java = "microsoft-21"` |
| `21-sapmchn` | `java = "sapmachine-21"` |
| `21-open` | `java = "openjdk-21"` |

A complete migration sequence looks like this:

```bash
# 1. Install mise (Homebrew)
brew install mise
echo 'eval "$(mise activate zsh)"'        >> ~/.zshrc
echo 'eval "$(mise activate zsh --shims)"' >> ~/.zprofile
exec zsh
mise doctor

# 2. Set globals matching your previous `sdk current`
mise use -g java@temurin-21
mise use -g maven@3.9.9
mise use -g gradle@8.10
mise use -g kotlin@2.1.0

# 3. Convert per-project .sdkmanrc → mise.toml
cat .sdkmanrc
# java=21.0.4-tem
# maven=3.9.9
cat > mise.toml <<'EOF'
[tools]
java  = "temurin-21.0.4"
maven = "3.9.9"
EOF
mise trust && mise install

# 4. Disable SDKMAN's shell init (DO NOT delete ~/.sdkman yet)
#    Comment out at the bottom of ~/.zshrc:
#    [[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"
exec zsh
which java                    # should resolve under ~/.local/share/mise/installs/java/...
```

**Watch for the bare-version footgun.** Writing `java = "21"` resolves to OpenJDK reference builds, which only get patches for the 6-month window after GA. Always specify a vendor — `temurin-21` for general Spring Boot work, `graalvm-community-21` for native-image experiments, `corretto-21` if your prod runs on AWS. You can change the default vendor with `[settings] java.shorthand_vendor = "temurin"`, but explicit is better.

**Should you keep SDKMAN around?** For a few weeks, yes — as a fallback while you confirm every project builds. After a sprint of confidence, `rm -rf ~/.sdkman`. Keeping both running daily is asking for `JAVA_HOME` and PATH races on every `cd`: SDKMAN's `sdkman_auto_env` and mise's prompt hook will fight over the front of PATH and you'll waste an afternoon debugging "why does `java -version` give a different answer in two terminals." The narrow case for keeping SDKMAN long-term is if you depend on Bisheng (`bsg`), Liberica NIK (`nik`), or Oracle's commercial GraalVM — these aren't in mise's curated registry, though you can symlink them in manually if you must.

---

## The Python story: let mise own the interpreter, let uv own the venv

Python on mise is a core plugin, and by default it installs **precompiled binaries from `astral-sh/python-build-standalone`** rather than compiling from source. The practical effect: a fresh `python@3.13` install is seconds, not the 5+ minutes pyenv took to compile against macOS's OpenSSL. You opt into source builds with `[settings] python.compile = true`.

The recommended 2026 pattern is a **clean division of labor**: mise installs the interpreter, uv manages the virtualenv and dependencies. mise has explicit support for this via the `python.uv_venv_auto` setting:

```toml
# Python + uv project
min_version = "2024.9.5"

[tools]
python = "3.13"
uv     = "latest"
ruff   = "latest"
"pipx:pre-commit" = "latest"

[settings]
python.uv_venv_auto = "create|source"   # create with `uv sync` if missing, then source

[hooks]
postinstall = "uv sync"

[env]
PYTHONDONTWRITEBYTECODE = "1"
PYTHONUNBUFFERED        = "1"
_.path = ["{{config_root}}/scripts"]

[tasks.test]   = { run = "uv run pytest" }
[tasks.lint]   = { run = "ruff check src/ tests/" }
[tasks.format] = { run = "ruff format src/ tests/" }
```

The bare `true` value for `python.uv_venv_auto` is being deprecated in mise `2026.7`; the explicit string forms (`"source"`, `"create|source"`) are forward-compatible.

If you're still on Poetry, the rule is **declare `poetry` *before* `python` in `[tools]`** so Poetry uses mise's interpreter, and tell Poetry to keep its venv in-project so mise's `_.python.venv` directive can find it:

```toml
[tools]
poetry = "1.8"     # MUST come before python
python = "3.12"

[env]
POETRY_VIRTUALENVS_IN_PROJECT = "true"
_.python.venv = { path = ".venv", create = false }   # poetry creates it
```

For projects that don't use a dedicated dependency manager, mise has a built-in venv directive that creates one for you on `mise install`:

```toml
[env]
_.python.venv = { path = ".venv", create = true, python = "3.13" }
```

**Two pitfalls to know.** First, the venv directive only activates under `mise activate` (the shell hook), not pure shims — so `which python` from an IDE that calls mise's binary directly may resolve to the system Python, not your venv. The fix is the IDE plugin or running through `mise exec`. Second, on older Macs you may need `MISE_PYTHON_PRECOMPILED_ARCH=x86_64` because the standalone builds target newer CPUs.

---

## The Node story: pick Corepack *or* mise for pnpm, never both

Node is a core plugin too, downloading official prebuilt binaries from nodejs.org. The setup is unsurprising:

```toml
[tools]
node = "lts"        # or "22", "22.11.0", or ["22", "20"] for multi-version
```

`.nvmrc`, `.node-version`, and (since PR #8059 in 2025) `package.json#devEngines.runtime` are recognized as idiomatic version files when you opt them in.

The interesting decision is **how to manage pnpm/yarn**. There are two valid approaches and **mixing them silently breaks things**:

```toml
# Approach A — Corepack-first (idiomatic for modern pnpm/yarn 4)
[tools]
node = "22"

[settings]
node.corepack = true
```

Pair this with `"packageManager": "pnpm@10.7.0"` in `package.json`. Corepack reads that field and pins pnpm per-project.

```toml
# Approach B — Explicit pin via mise (DO NOT MIX with Corepack)
[tools]
pnpm = "10.7.0"     # MUST come before node so its binary wins on PATH
node = "22"
```

If you have *both* a `packageManager` field in `package.json` and `pnpm` in `mise.toml`, Corepack's shim silently overrides mise's pnpm — documented in discussion #7063 and a multi-hour debugging exercise the first time it happens. Pick one approach per repo.

For globally-installed CLIs, mise has dedicated backends: `"npm:typescript" = "latest"`, `"npm:@anthropic-ai/claude-code" = "latest"`, or the analogous `pnpm:` prefix. And the most useful single line for Node projects is `_.path = ['{{config_root}}/node_modules/.bin']` in the `[env]` section, which makes `eslint`, `vite`, `tsc`, etc. directly callable from the shell without `pnpm exec`.

---

## The Java/Kotlin story: mise pins JDK, Gradle wrapper still owns the build

This is the clarification that matters most for your Spring Boot + Kotlin context. **mise managing Gradle and Kotlin via `[tools]` is mostly cosmetic** when you're using the Gradle wrapper (which you should — `./gradlew` is industry-standard, the wrapper downloads its pinned Gradle into `~/.gradle/wrapper/dists/`, and the Kotlin Gradle Plugin pulls its own `kotlinc` from the build classpath). What mise *actually* gives a Spring Boot Kotlin project is:

1. **JDK pinning by vendor + version** (`temurin-21`, `graalvm-community-21`).
2. **Automatic `JAVA_HOME`** under `mise activate`.
3. **Project-scoped environment variables** for things like `SPRING_PROFILES_ACTIVE`, `JAVA_TOOL_OPTIONS`, `GRADLE_OPTS`.
4. **Tasks** that wrap `./gradlew` so the same `mise run test` works locally and in CI.
5. **A unified `mise.toml`** that also pins the Node version your frontend uses and the Python version your tooling scripts need.

A typical Spring Boot 4.0 + Kotlin `mise.toml` is therefore lean:

```toml
[tools]
java   = "temurin-21"        # or "temurin-25" for Spring Boot 4.0 with the recommended LTS
gradle = "8.10"              # cosmetic if you use ./gradlew; informative for IDE/contributors
# kotlin = "2.1.0"           # only if you actually invoke kotlinc directly anywhere

[env]
SPRING_PROFILES_ACTIVE = "local"
JAVA_TOOL_OPTIONS      = "-Dfile.encoding=UTF-8"
GRADLE_OPTS            = "-Xmx2g"

[tasks.run]   = { run = "./gradlew bootRun" }
[tasks.test]  = { run = "./gradlew test" }
[tasks.build] = { run = "./gradlew bootJar" }
[tasks.image] = { run = "./gradlew bootBuildImage" }
[tasks.lint]  = { run = "./gradlew spotlessCheck" }
[tasks.ci]
depends = ["lint", "test"]
```

Spring Boot 4.0 (current as of April 2026) requires Java 17 minimum, supports up to Java 26, and the Spring team recommends JDK 25 LTS for production. Spring Boot 3.5 also remains supported; 3.4 went OSS-EOL in November 2025.

**The Gradle toolchain caveat.** Gradle's `JavaToolchain` auto-provisioning does *not* yet know about mise's install layout (open Gradle issues #29508 and #29355). You have three options: (a) rely on `JAVA_HOME` set by `mise activate` and skip toolchain auto-provisioning, which is the simplest path; (b) point Gradle at mise's directory via `org.gradle.java.installations.paths` in `gradle.properties`; or (c) apply the `foojay-resolver-convention` plugin and let Gradle download its own toolchain JDK independently of mise. Option (a) works for nearly everyone.

For Kotlin specifically, **don't bother managing `kotlinc` via mise unless you actually run it standalone** (Kotlin scripts, `*.main.kts` files, ad-hoc `kotlinc-jvm Foo.kt` invocations, JBang-style use). The Kotlin Gradle Plugin version declared in your `build.gradle.kts` (e.g., `kotlin("jvm") version "2.1.0"`) is what governs the actual compilation, and it manages its own compiler.

---

## The task runner: replacing Make, npm scripts, and Gradle's outer shell

mise's task runner graduated from experimental in 2024 and is now a first-class feature. The mental model: **mise tasks are not a build system replacement, they're an outer-developer-workflow runner**. Gradle still does the JVM build graph; mise tasks are how you invoke `./gradlew test`, `docker compose up`, `prisma migrate deploy`, and `terraform plan` with one consistent interface across your polyglot projects.

### TOML tasks: the core syntax

Tasks live under `[tasks.<name>]` in `mise.toml`. Every form below is equivalent for the simplest case:

```toml
tasks.build = "cargo build"                    # inline shorthand
tasks.build = ["cargo build", "cargo test"]    # array, runs in series
tasks.build.run = "cargo build"                # dotted-key form

[tasks.build]                                  # full table form
run = "cargo build"
```

The full set of fields is large, but the ones that earn their keep are `run`, `description`, `depends`, `depends_post`, `wait_for`, `env`, `dir`, `sources`, `outputs`, `confirm`, `usage`, `hide`, and `tools`. A representative example:

```toml
[tasks.test]
description = "Run tests with backtraces enabled"
depends     = ["build"]
env         = { RUST_BACKTRACE = "1" }
sources     = ["src/**/*.rs", "tests/**/*.rs", "Cargo.toml"]
outputs     = { auto = true }
run         = "cargo test"

[tasks.release]
description = "Cut a new release"
confirm     = "Are you sure you want to cut a release?"
file        = "scripts/release.sh"
```

For multi-line scripts, prefer either an array (each element is a separate shell invocation, fail-fast in series) or a heredoc string with a shebang (single shell invocation):

```toml
[tasks.deploy]
run = """
#!/usr/bin/env bash
set -euo pipefail
terraform init
terraform workspace select $TF_WORKSPACE
terraform plan
"""
```

**Source/output tracking** gives you Make-like incremental builds: mise skips the task if the oldest output is newer than the newest source. Use `outputs = { auto = true }` (the default when you specify `sources`) when there are no obvious output files — mise will track an internal hash file at `~/.local/state/mise/task-outputs/`. Force re-run with `mise run --force <task>`. For more accuracy than mtime, set `[settings] task.source_freshness_hash_contents = true` to use blake3 content hashing.

### File-based tasks: when scripts get longer

Once a task is more than ~5 lines or wants to be in another language, move it to a file under `mise-tasks/`, `.mise-tasks/`, or `.config/mise/tasks/`:

```bash
#!/usr/bin/env bash
#MISE description="Deploy application"
#USAGE arg "<environment>" help="Deployment environment" {
#USAGE   choices "dev" "staging" "prod"
#USAGE }
#USAGE flag "--dry-run" help="Preview changes"
#USAGE flag "--region <region>" default="us-east-1" env="AWS_REGION"

set -euo pipefail
ENV="${usage_environment?}"
REGION="${usage_region?}"

if [[ "${usage_dry_run:-false}" == "true" ]]; then
  echo "DRY RUN: deploy to $ENV in $REGION"
else
  ./scripts/deploy.sh "$ENV" "$REGION"
fi
```

The header comments must be `#MISE` (uppercase, no space) or `# [MISE]` — mise intentionally ignores `# MISE ...` with a space. Make the file executable. Polyglot shebangs work — `#!/usr/bin/env python`, `#!/usr/bin/env -S deno run`, `#!/usr/bin/env pwsh` — and the `//MISE` comment marker is used for languages with `//` comments.

The `#USAGE` lines (or the `usage` field on TOML tasks) define a typed argument spec that gives you `--help`, validation, choice lists, environment-variable fallbacks, and shell completions for free. **This is replacing the older Tera-template arg syntax (`{{arg()}}`, `{{flag()}}`) which is deprecated and being removed in mise `2026.11.0`** — if you're starting fresh, use `usage` exclusively.

### Dependencies, parallelism, and orchestration

`depends` runs tasks before, in parallel where possible. `depends_post` runs cleanup tasks after. `wait_for` is a soft dependency — wait if it's running, but don't trigger it. There's deliberately **no `depends_series`**; if you need strict sequential execution, nest task references inside `run`:

```toml
[tasks.pipeline]
run = [
  { task = "lint" },                             # finishes first
  { tasks = ["test:unit", "test:integration"] }, # then these in parallel
  { task = "build", args = ["--release"] },
  "echo done",
]
```

Default parallelism is 4 jobs, tunable via `--jobs N` or `MISE_JOBS`. Output is line-prefixed with the task label; switch to `--interleave` if you prefer raw output.

Per-task `env = { ... }` does **not propagate to dependencies** — you have to use the structured form `depends = [{ task = "x", env = {...} }]` if you want to pass env to deps. This bites people; remember it.

### When to use mise tasks vs alternatives

For **Node.js**, the practical recommendation is hybrid: keep `dev`/`start` in `package.json` (it's the JS-ecosystem convention and tools like Heroku rely on it), but move orchestration — `mise run ci`, `mise run db:reset && mise run dev`, `mise run release` — to mise. The cross-tool win (a task that calls Docker, then Prisma, then pnpm) is hard to do cleanly in `package.json`.

For **Spring Boot/Gradle**, mise tasks wrap `./gradlew` invocations. Gradle is the build system; you don't reimplement it in mise. But `mise run test` working identically in your local terminal, your IDE's run configurations (via the IntelliJ mise plugin), and your CI workflow is genuine value.

Versus **Make**: mise tasks win on cross-platform, polyglot shebangs, no tab-character footguns, integrated tool/env management, and parallel-by-default. Make remains useful in environments where mise isn't installed.

Versus **`just` (justfile)**: just is cleaner for "always-run command-runner" use cases. mise wins when you want sources/outputs invalidation, parallel DAGs, watch mode, or unified tool/env/task management.

Versus **Taskfile (YAML)**: mostly a taste call. Taskfile has more mature checksum-based change detection out of the box. mise gives you bash files instead of YAML strings (real shellcheck/lint), and integrates with version management.

### Watch mode and pre-commit hooks

`mise watch <task>` shells out to `watchexec` (install once with `mise use -g watchexec`) and watches the files declared in `sources`. Use `-r` to restart-on-change. The feature is still marked experimental in April 2026 but works reliably.

For pre-commit hooks: `mise generate git-pre-commit --task=pre-commit` installs a hook that runs your `pre-commit` task. For onboarding contributors who don't have mise installed, `mise generate bootstrap` creates a `./bin/mise` wrapper that auto-downloads mise to a known version — pair it with `mise generate task-stubs` and your devs just run `./bin/test` regardless of what's installed.

---

## Environment variable management

The `[env]` section is the third leg of mise's tripod and the direct replacement for direnv. Basic syntax is dense but TOML-clean:

```toml
[env]
NODE_ENV = "development"
API_URL  = "https://api.example.com"
JAVA_OPTS = "-Xms512m -Xmx2g -XX:+UseG1GC"

# Inline-table form for advanced behavior
SECRET   = { value = "...", redact = true }                 # mark sensitive
DB_URL   = { required = "Set DB_URL in mise.local.toml" }   # error if unset
NODE_VER = { value = "{{ tools.node.version }}", tools = true }  # tool-aware
```

Values are rendered through the **Tera** template engine — Jinja2-like — with mise-specific variables (`env`, `cwd`, `config_root`, `mise_bin`, `mise_env`, `xdg_*`) and functions (`get_env`, `arch`, `os`, `num_cpus`, `exec`, `read_file`). This lets you do things like `LOG_DIR = "{{ env.HOME }}/logs/{{ env.APP_NAME }}"` or `GIT_BRANCH = "{{ exec(command='git branch --show-current') }}"`.

Three special directives drive the most common patterns:

- **`_.path`** prepends to PATH. `_.path = ["./node_modules/.bin", "{{config_root}}/scripts"]` is the universal "tools-on-PATH" line.
- **`_.file`** loads `.env` files. `_.file = [".env", ".env.local"]` is the standard "shared defaults + personal override" pattern; supports `KEY=VALUE` (via dotenvy), JSON (`.env.json`), and YAML (`.env.yaml`). Top-level `env_file` / `dotenv` keys exist for backward compat but are deprecated and removed in mise `2027.4.0`.
- **`_.source`** sources a Bash-compatible script. Useful when you genuinely need shell logic (not just TOML literals); the cost is that mise re-runs it on every prompt, so don't put expensive operations there.

For Python projects there's also `_.python.venv` covered earlier.

### Profiles for dev/staging/prod

mise supports per-environment configs via `MISE_ENV` or the `-E` flag:

```bash
mise -E development run server
MISE_ENV=production mise run deploy
```

When set, mise looks for `mise.{MISE_ENV}.toml` and `mise.{MISE_ENV}.local.toml` in addition to the base files. A typical layout:

```
project/
├── mise.toml                     # baseline, committed
├── mise.development.toml         # dev defaults, committed
├── mise.production.toml          # prod defaults, committed
├── mise.local.toml               # personal, gitignored
├── mise.development.local.toml   # personal dev overrides, gitignored
├── .env                          # non-secret defaults, committed
└── .env.local                    # secrets, gitignored
```

`MISE_ENV` itself **cannot be set inside `mise.toml`** (chicken-and-egg) — only via the CLI, ambient env, or a `.miserc.toml` file (`env = ["development"]`).

### Secrets: what mise does and doesn't do

mise has built-in **sops + age** support, marked experimental, introduced in late 2024. You drop a sops-encrypted `.env.json`, `.env.yaml`, or `.env.toml` and reference it normally:

```toml
[env]
_.file = { path = ".env.json", redact = true }
```

```bash
mise use -g sops age
age-keygen -o ~/.config/mise/age.txt
sops encrypt -i --age "<public_key>" .env.json   # encrypted file is safe to commit
```

The built-in fast path (using the embedded `rops` library) only supports **age encryption** — KMS backends require shelling out to `sops` itself (`MISE_SOPS_ROPS=0`). There is no native 1Password, AWS Secrets Manager, GCP, Vault, or Bitwarden integration — by design, since mise reloads env on every `cd` and network calls would be too slow.

For real production secrets, mise's docs now explicitly recommend a **separate companion tool, `fnox`** (`https://fnox.jdx.dev/`, also by `@jdx`), launched in late 2025. fnox supports age, AWS KMS / Secrets Manager / Parameter Store, Azure Key Vault, GCP Secret Manager, 1Password, Bitwarden, Vault, password-store, and macOS Keychain. There's no direct mise↔fnox integration; you set them up side-by-side and use `fnox exec -- <cmd>` or its own shell hook.

The non-negotiable secrets hygiene is the same as anywhere else: **never commit secrets**, gitignore the local-override files (`mise.local.toml`, `mise.*.local.toml`, `.env.local`), and set `redact = true` on any sensitive value so it doesn't leak in `mise env` or task logs. In CI, `mise-action` automatically masks redacted values via `::add-mask::`.

### mise vs direnv, in one sentence

The official docs page at `mise.jdx.dev/direnv.html` is now titled *"direnv deprecated"*: don't use both, and PRs to improve compatibility are not accepted. mise covers virtually all direnv use cases — per-directory env, PATH manipulation, dotenv loading, Python venv layouts — with declarative TOML instead of shell scripts, plus tool-version management direnv lacks. The narrow case for staying on direnv is if you have an `.envrc` doing genuinely complex shell logic (HTTP calls, password-manager calls, conditional sourcing) that you don't want to translate. In that case migrate everything else and keep direnv only for that repo, with no overlap on PATH or any single env var.

---

## Team workflow: lockfile, CI, onboarding

The team-readiness story is what separates 2026-mise from 2023-rtx, and it hinges on three things: `mise.lock`, the `jdx/mise-action` GitHub Action, and the local-override convention.

### The lockfile

`mise.lock` is opt-in but powerful once enabled. Run `mise lock` once to generate it; subsequent `mise install` / `mise upgrade` keep it updated. It records exact versions, sha256 checksums, download URLs, and provenance metadata (slsa, cosign, minisign, github-attestations) **per platform** — multi-platform lockfiles are critical for mixed Mac/Linux/WSL teams:

```bash
mise lock --platform linux-x64,linux-arm64,macos-arm64,windows-x64
```

The 2026 idiom is **fuzzy versions in `mise.toml` + exact pins in `mise.lock`**:

```toml
[tools]
node = "22"          # security patches via `mise upgrade`
java = "temurin-21"  # exact pin lives in mise.lock
```

For strict CI, set `MISE_LOCKED=1` (or `[settings] locked = true`) — mise then fails if the lockfile doesn't have pre-resolved URLs for the current platform, which prevents silent drift *and* eliminates GitHub API calls that can hit rate limits on busy repos.

**Two lockfile bugs to know.** First, discussion #8000 documents that with both `mise.toml` and `mise.local.toml` present, `mise lock` may write to `mise.local.lock` (gitignored) instead of `mise.lock`. Verify your version handles this correctly. Second, discussion #7210 reports an aqua-backend `v`-prefix stripping bug for some packages (e.g., 1password/cli). Both are tracked and being fixed; check status on your installed mise version before relying on lockfile-driven CI.

### What goes in git, what doesn't

| File | Status | Contents |
|---|---|---|
| `mise.toml` | **Committed** | tool versions, tasks, non-secret env defaults, settings |
| `mise.lock` | **Committed** (once generated) | exact versions, checksums, per-platform URLs |
| `mise.development.toml`, `mise.production.toml` | **Committed** | per-environment shared defaults |
| `mise.local.toml` | **Gitignored** | personal tool versions, local secrets, AWS profile |
| `mise.*.local.toml` | **Gitignored** | personal env-scoped overrides |
| `.env` | Sometimes committed (no secrets) | shared non-secret defaults |
| `.env.local`, `.env.*.local` | **Gitignored** | personal secrets |

The canonical `.gitignore` block:

```
mise.local.toml
mise.*.local.toml
.mise.local.toml
.mise.*.local.toml
mise.local.lock
.env.local
.env.*.local
```

For sensitive variables that *must* be set, use the `required` directive in `mise.toml` to make the requirement loud:

```toml
[env]
DATABASE_URL = { required = "Set DATABASE_URL in mise.local.toml" }
```

### GitHub Actions

The official action `jdx/mise-action` is at **v4.0.1** as of April 2026 (v4.0.0 in March 2026 bumped Node runtime 20→24). Pin to `@v4` for new pipelines:

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: jdx/mise-action@v4
        with:
          version: 2026.4.22         # pin for determinism, or omit for "latest"
          experimental: true
          cache: true
          cache_key_prefix: mise-v1
          github_token: ${{ secrets.GITHUB_TOKEN }}
        env:
          MISE_LOCKED: '1'           # fail if lockfile is stale; skip GitHub API
      - run: mise run ci             # the same command devs run locally
```

The action caches `~/.local/share/mise/installs` and the mise binary; cache keys default to a hash of `mise.toml`/`.tool-versions`/`mise.lock`. Cold-cache CI runs are typically tens of seconds for Python/Node/Java with precompiled binaries; warm caches are seconds. The single most important pattern is **`mise run ci`** — define a `ci` task with `depends = ["lint", "test", "build"]` in your `mise.toml`, and the same one-line invocation works on every dev laptop, every IDE run config, and every CI runner. `mise generate github-action --write --task=ci` even scaffolds the workflow for you.

For non-GitHub CI: GitLab gets a similar treatment via `mise generate bootstrap` (vendor a `./bin/mise` wrapper into the repo), CircleCI uses straightforward bash with cache directives, and Docker is a baked-image pattern using `mise install --system` so installs survive bind-mounted home directories. There's no official `mise/mise` Docker image; the cookbook recommends building your own slim image:

```dockerfile
FROM debian:13-slim
RUN apt-get update && apt-get -y --no-install-recommends install \
      sudo curl git ca-certificates build-essential && \
    rm -rf /var/lib/apt/lists/*
ENV MISE_VERSION=v2026.4.22
RUN curl https://mise.run | MISE_INSTALL_PATH=/usr/local/bin/mise sh
WORKDIR /app
COPY mise.toml mise.lock ./
RUN mise trust /app/mise.toml && mise install --system
ENV PATH="/usr/local/share/mise/shims:${PATH}"
```

### Onboarding new team members

Six commands gets a new dev fully set up:

```bash
brew install mise
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc && exec zsh
git clone <repo> && cd <repo>
mise trust
mise install --locked
mise run setup     # your project's bootstrap task
```

Document this verbatim in your README's "Development setup" section. The trust prompt and the activation step are the two stumbling blocks; everything else is automatic.

---

## IDE integration

**JetBrains (IntelliJ IDEA, PyCharm, RustRover, GoLand, WebStorm).** Recent JetBrains versions include direct mise support in the SDK picker — you can select a mise-managed JDK or Python from the IDE's standard SDK dialog. For full integration (running mise tasks, loading `[env]` vars in run configurations), install the third-party plugin **`intellij-mise`** by 134130 (`https://github.com/134130/intellij-mise`). It's the recommended path. As a fallback for older IDEs, the asdf-layout symlink trick still works because mise's on-disk layout is identical: `ln -s ~/.local/share/mise ~/.asdf` makes asdf-aware plugins find your tools.

**VS Code / Cursor.** Install the **`hverlin.mise-vscode`** extension (`https://github.com/hverlin/mise-vscode`). It auto-configures other extensions to use mise tools, manages tasks/tools/env from the command palette, loads `[env]` vars into run configurations, and provides JSON-schema autocomplete for `mise.toml`. Without the extension, you can fall back to shims-on-PATH via `~/.zprofile`, but on macOS GUI launches don't read `.zprofile` — add this to `settings.json` so the integrated terminal picks it up:

```json
"terminal.integrated.automationProfile.osx": {
  "path": "/usr/bin/zsh",
  "args": ["--login"]
}
```

For per-launch overrides, use `mise exec` in `launch.json` `runtimeExecutable`/`runtimeArgs`.

**Common gotcha across IDEs**: shims set tool versions but *not* arbitrary `[env]` vars — only the IDE plugins read `mise.toml` directly and propagate env into run configurations. If you're seeing "the right Python version, wrong `DATABASE_URL`," install the plugin.

---

## Pitfalls, gotchas, and debugging

**Idiomatic version files are off by default since `2025.10.0`.** `.python-version`, `.nvmrc`, `.java-version`, `.sdkmanrc` no longer auto-honored. Opt in via `[settings] idiomatic_version_file_enable_tools = ["python", "node", "java"]`.

**`java = "21"` defaults to OpenJDK reference builds** with only 6 months of patches. Always use a vendor: `temurin-21`, `corretto-21`, etc.

**Mixing Corepack and mise-managed pnpm silently breaks.** Pick one approach.

**Per-task `env` doesn't propagate to `depends`.** Use structured `depends = [{ task = "x", env = {...} }]` if you need it.

**`confirm` only gates the task's own `run`, not its `depends`.** Dependencies run *before* the prompt. If you need the prompt first, put the gated work in `run` (with `run = [{ task = "..." }, ...]`), not in `depends`.

**Gradle toolchain auto-detection ignores mise.** Rely on `JAVA_HOME` (set by `mise activate`), or use the `foojay-resolver-convention` plugin.

**Trust-bypass CVE GHSA-436v-8fw5-4mj8.** Affects mise ≤ `v2026.3.17`. Keep your mise current and especially your CI mise pinned to a patched version before running mise on PRs from forks.

**The Tera-template arg syntax in tasks is deprecated.** `{{arg()}}`, `{{flag()}}`, `{{option()}}` get warnings in `2026.5.0`, removed in `2026.11.0`. Migrate to the `usage` field.

**Top-level `env_file` / `dotenv` / `env_path` keys are deprecated.** Removed in `2027.4.0`. Use `env._.file` / `env._.path`.

**Debugging toolbox.** When something's wrong: `mise doctor` for system check, `mise config` for "which configs got loaded in what order", `mise ls` for installed tools and their source, `MISE_DEBUG=1` or `MISE_LOG_LEVEL=trace` for verbose output, `MISE_TIMINGS=2` to profile slow prompts. The most common slow-prompt cause is an expensive `_.source` script that re-runs on every prompt — check yours if your shell feels sluggish.

**Coexistence with old tools.** mise reads `.tool-versions` (asdf), `.nvmrc`, `.python-version`, `.sdkmanrc` — partial migrations are supported. But running mise *and* asdf *and* nvm *and* SDKMAN simultaneously is asking for PATH races. Pick a date, switch, and remove the old tools after a few weeks of confidence.

---

## Complete copy-pasteable configs

### Python data/backend project (mise + uv)

```toml
# mise.toml
min_version = "2024.9.5"

[tools]
python = "3.13"
uv     = "latest"
ruff   = "latest"
"pipx:pre-commit" = "latest"

[settings]
python.uv_venv_auto = "create|source"
idiomatic_version_file_enable_tools = ["python"]

[env]
PYTHONDONTWRITEBYTECODE = "1"
PYTHONUNBUFFERED        = "1"
PYTHONPATH              = "{{config_root}}/src"
_.path = ["{{config_root}}/scripts"]
_.file = [".env", ".env.local"]

[hooks]
postinstall = "uv sync"

[tasks.test]    = { run = "uv run pytest" }
[tasks.lint]    = { run = "ruff check src/ tests/" }
[tasks.format]  = { run = "ruff format src/ tests/" }
[tasks.typecheck] = { run = "uv run mypy src/" }

[tasks.ci]
depends = ["lint", "typecheck", "test"]
```

### Node.js / TypeScript project (Corepack-driven pnpm)

```toml
# mise.toml
[tools]
node = "22"

[settings]
node.corepack = true
idiomatic_version_file_enable_tools = ["node"]

[env]
NODE_ENV     = "development"
NODE_OPTIONS = "--max-old-space-size=4096"
_.path = ["{{config_root}}/node_modules/.bin"]
_.file = [".env", ".env.local"]

[hooks]
postinstall = "pnpm install --frozen-lockfile"

[tasks.dev]   = { run = "pnpm dev" }
[tasks.test]  = { run = "vitest run" }
[tasks.build] = { run = "pnpm build" }
[tasks.lint]
sources = ["src/**/*.{ts,tsx}", ".eslintrc.*", "package.json"]
run = ["eslint .", "prettier --check ."]

[tasks.ci]
depends = ["lint", "test", "build"]
```

Pair with `package.json`:

```json
{ "packageManager": "pnpm@10.7.0" }
```

### Spring Boot Kotlin project

```toml
# mise.toml
[tools]
java   = "temurin-21"
gradle = "8.10"

[settings]
java.shorthand_vendor = "temurin"
idiomatic_version_file_enable_tools = ["java"]

[env]
SPRING_PROFILES_ACTIVE = "local"
JAVA_TOOL_OPTIONS      = "-Dfile.encoding=UTF-8"
GRADLE_OPTS            = "-Xmx2g -XX:+UseG1GC"
_.file = [".env", ".env.local"]

# Required vars — devs see a clear error if not set
[env.DATABASE_URL]
required = "Set DATABASE_URL in mise.local.toml (e.g., postgres://localhost/myapp_dev)"

[tasks.run]
description = "Run Spring Boot app"
run = "./gradlew bootRun"

[tasks.test]
description = "Run unit + integration tests"
run = "./gradlew test"

[tasks.build]
description = "Produce executable JAR"
run = "./gradlew bootJar"

[tasks.image]
description = "Build OCI image with Buildpacks"
run = "./gradlew bootBuildImage"

[tasks.lint]
run = "./gradlew spotlessCheck detekt"

[tasks."db:migrate"]
description = "Apply Flyway migrations"
run = "./gradlew flywayMigrate"

[tasks."db:reset"]
confirm = "DROP and recreate the database?"
run = ["./gradlew flywayClean", "./gradlew flywayMigrate"]

[tasks.ci]
depends = ["lint", "test"]
```

Companion `mise.local.toml` (gitignored) for personal overrides:

```toml
[tools]
java = "graalvm-community-21"   # for native-image experiments

[env]
DATABASE_URL = "postgres://localhost:5432/myapp_dev"
SPRING_PROFILES_ACTIVE = "local,debug"
LOG_LEVEL = "DEBUG"
```

### Polyglot monorepo (Spring Boot + React/TS + Python ML)

```toml
# mise.toml at repo root
[tools]
java   = "temurin-21"
node   = "22"
python = "3.13"
uv     = "latest"
gradle = "8.10"
"npm:turbo" = "latest"

[settings]
java.shorthand_vendor   = "temurin"
node.corepack           = true
python.uv_venv_auto     = "create|source"
idiomatic_version_file_enable_tools = ["node", "java", "python"]

[env]
JAVA_TOOL_OPTIONS = "-Dfile.encoding=UTF-8"
NODE_ENV          = "development"
_.path  = ["{{config_root}}/node_modules/.bin"]
_.python.venv = { path = ".venv", create = true }
_.file  = [".env", ".env.local"]

[tasks."api:run"]    = { run = "./gradlew :api:bootRun" }
[tasks."api:test"]   = { run = "./gradlew :api:test" }
[tasks."web:dev"]    = { run = "pnpm --filter web dev" }
[tasks."web:test"]   = { run = "pnpm --filter web test" }
[tasks."web:build"]  = { run = "pnpm --filter web build" }
[tasks."ml:test"]    = { run = "uv run pytest ml/" }
[tasks."ml:train"]   = { run = "uv run python ml/train.py" }

[tasks.dev]
description = "Run the full stack locally"
depends = ["api:run", "web:dev"]

[tasks.test]
description = "Run all tests"
depends = ["api:test", "web:test", "ml:test"]

[tasks.ci]
depends = ["test"]
```

---

## Conclusion: a short opinion

The migration calculus for your context is clear-cut: **switch fully to mise**. Your polyglot stack is exactly what mise was built for, the SDKMAN translation is mechanical (and mise covers more JDK distributions than SDKMAN does anyway), the Spring Boot + Kotlin + Gradle wrapper pattern remains intact with only `JAVA_HOME` changing hands, and the team-readiness gap that existed in 2023-era rtx is closed by `mise.lock`, `jdx/mise-action@v4`, and the conventions around `mise.local.toml`. The novel insight worth absorbing is that **mise is not three tools that share a binary — it's one coherent declarative description of a development environment**, and the leverage compounds when you stop thinking of "which version of X do I have" and "where do I put this env var" and "how do I run that pipeline" as three different problems. Pin a recent mise (≥ `2026.4.x` to clear the trust-bypass CVE), commit a `mise.toml` and `mise.lock`, gitignore `mise.local.toml`, define a `ci` task, and the rest follows. The two things to keep an eye on after migrating: the `usage`-syntax migration deadline of `2026.11.0`, and the `mise.local.lock` location bug if you generate lockfiles on a machine that has personal overrides — verify `mise.lock` is what actually got created before opening the PR.