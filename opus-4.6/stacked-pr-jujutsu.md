# Stacked PRs and Jujutsu: a modern developer's guide to faster code review

**Stacked pull requests break large changes into small, dependent, reviewable units — and Jujutsu (jj) is a Git-compatible version control system that makes this workflow nearly effortless.** Together, they represent the most significant shift in everyday developer workflow since Git replaced SVN. Stacked PRs solve the universal problem of slow code review by keeping each PR under ~300 lines, while jj eliminates the painful rebasing and branch management that makes stacking difficult in plain Git. This guide covers both in depth: the stacked PR concept and tooling ecosystem, Jujutsu's design and daily usage, and practical recommendations for adopting either or both.

---

## Part 1: Stacked PRs

### Why large PRs are killing your review cycle

The core insight behind stacked PRs is empirical: **review effectiveness degrades sharply as change size increases**. A 10-line diff gets 10 issues found; a 500-line diff gets "looks good to me." Research by Dr. Michaela Greiler and data from teams at Meta, Google, and Uber consistently show that PRs over ~400 lines receive rubber-stamp approvals, delayed reviews, and hide more bugs.

Large PRs create a cascade of problems beyond review quality. They generate painful merge conflicts because long-lived feature branches diverge from `main`. They block the author, who must context-switch to unrelated work while waiting days for review. And when something breaks in production, pinpointing the cause in a 1,200-line change is far harder than in a 150-line one.

Stacked PRs (also called stacked diffs, dependent PRs, or chained PRs) solve this by decomposing a large feature into a series of small, dependent pull requests that build on one another. Each PR branches off the previous one — not off `main` — forming a chain: PR1 → PR2 → PR3 → main. Each is independently reviewable, and they merge sequentially from bottom to top. The author continues building the next layer while earlier PRs are in review, staying unblocked.

This workflow aligns naturally with trunk-based development. Each PR stays close to `main`, reducing drift. The philosophy is **one logical change per PR** — a database migration, an API endpoint, a UI component — creating a narrative that reviewers can follow. Companies that pioneered this approach include **Meta** (which built Phabricator around stacked diffs and covers it during onboarding), **Google** (using Critique and Gerrit), **Uber**, and growing numbers of startups using tools like Graphite. The recommended sweet spot is **3–5 PRs per stack**, each under 200–400 lines.

### How stacked PRs work mechanically

The basic workflow in Git looks like this. First, create a branch off `main`, make changes, push, and open PR #1. Then create a second branch off that first branch (not off `main`), make changes, push, and open PR #2 targeting the first branch as its base. Repeat for PR #3, targeting PR #2's branch.

```bash
git checkout main && git checkout -b feat/db-migration
# ... make changes, commit, push, open PR #1 → main

git checkout -b feat/api-endpoint  # branches from feat/db-migration
# ... make changes, commit, push, open PR #2 → feat/db-migration

git checkout -b feat/ui-component  # branches from feat/api-endpoint
# ... make changes, commit, push, open PR #3 → feat/api-endpoint
```

When a reviewer requests changes on PR #1, you must update that branch, then **rebase every subsequent branch** onto the updated one, then force-push all of them. PRs merge bottom-up: PR #1 merges into `main` first, then PR #2 is retargeted to `main` and merged, and so on.

The pain points of doing this manually are severe. **Cascade rebasing** is the biggest: every change to an earlier branch requires manually rebasing every downstream branch and force-pushing each one. Git has no native concept of branch parent-child relationships, so you must mentally track which branch depends on which — easy to get wrong with 5+ branches. Each force-push triggers a full CI run on every PR. GitHub has no built-in PR dependency feature, no automatic cascade when a base PR merges, and its preferred squash-merge strategy breaks commit identity across stacked branches. Git's `--update-refs` flag (added in recent versions) helps update branch pointers during interactive rebase, but it doesn't handle PR creation, pushing, or CI management.

### Graphite: the most polished stacked PR tool

**Graphite** is the dominant commercial solution, built by ex-Meta engineers who lived the stacked diff workflow at Facebook. It provides a CLI (`gt`), VS Code extension, web dashboard, and merge queue — a full-stack solution layered on top of Git and GitHub.

The CLI manages stack metadata locally and syncs with GitHub PRs. Key commands:

```bash
gt branch create "db-migration" -m "Add database migration"   # Create stacked branch
gt modify                                                       # Amend current commit
gt submit --stack                                               # Push + create/update ALL PRs in stack
gt log short                                                    # Visualize stack
gt up / gt down                                                 # Navigate between stack branches
gt repo sync --force                                            # Sync with remote, clean merged branches
```

When you run `gt modify`, Graphite automatically restacks all child branches. `gt submit --stack` creates or updates every PR in the stack with a single command, adding stack visualization comments to each PR so reviewers can navigate between them. The web dashboard provides a modern PR inbox with stack-aware diff viewing, version comparison, team metrics (review speed, cycle time, PR size), and a merge queue that validates entire stacks atomically.

**Pricing** ranges from free (personal repos, limited features) to **$20/user/month** (Starter) and **$40/user/month** (Team, with merge queue and AI reviews) to custom Enterprise pricing. Graphite works only with GitHub — no GitLab or Bitbucket support. It requires a Graphite account for CLI authentication. The tool is very actively maintained, having launched out of beta in March 2025, and is used by teams at Asana, Ramp, and Shopify.

### git-town, spr, ghstack, and the open-source landscape

**git-town** is the most popular open-source alternative, positioning itself as "your Bash scripts for Git." It supports GitHub, GitLab, and Bitbucket — a major advantage over Graphite. Key stacking commands include `git town append branchB` (create a child branch), `git town sync --stack` (sync all branches in the current stack), and `git town propose` (create a PR). It auto-resolves "phantom merge conflicts" caused by squash-merge hash differences. Version 22.5 is current, it's written in Go, completely free, and requires no account.

**spr** (Stack Pull Requests) takes a different approach: **each commit on a single branch becomes a separate PR**. You work on one local branch with multiple commits, and `git spr update` creates remote branches and PRs for each commit automatically. The mental model is simple — commit equals PR — but it's restrictive: you must maintain exactly one commit per PR.

**ghstack**, created by Edward Yang at Meta for the PyTorch project, replicates Phabricator's stacked diff workflow on GitHub. It creates **three branches per commit** (base, head, and original) to enable clean per-commit PRs without force-pushing. The tradeoff is significant branch pollution on the remote and inability to use GitHub's merge button — you must use `ghstack land` instead. It's niche but battle-tested in the PyTorch ecosystem.

**Aviator** combines an open-source CLI (`av`) for stack management with a commercial merge queue service. Its merge queue is **stack-aware** — it treats stacked PRs as a single unit, validating and merging them atomically. Commands like `av sync --all` rebase all stacked branches, and `av pr --queue` queues PRs for auto-merge. The CLI is free; the merge queue is a paid service with SOC2 Type II certification.

**git-branchless** focuses on a commit-oriented workflow with `git sl` (smartlog) visualization and automatic descendant rebasing. It doesn't handle PR creation but pairs well with other tools. **ReviewStack** (from Meta's Sapling project) is a web viewer for stacked PRs showing clean, stack-aware diffs. **stack-pr** (from Modular, makers of Mojo) is a newer ghstack-inspired tool.

### Which tools to use in 2024–2025

The landscape has a clear hierarchy. **Graphite** dominates for teams wanting a polished, end-to-end stacked PR experience on GitHub — it has the most blog posts, tutorials, and community traction. **git-town** is the best open-source general-purpose option, especially for teams using GitLab or Bitbucket. **Aviator** is strongest for enterprises needing a production-grade merge queue. **spr** appeals to developers who prefer the commit-centric model. And an increasing number of developers are exploring **Jujutsu** as a free alternative with native stacking built into the VCS itself.

Best practices across all tools: aim for under 300 lines per PR and 3–5 PRs per stack. Submit PRs early, even as drafts. Review bottom-up. Assign different reviewers to different layers. Merge bottom-up using tooling rather than GitHub's merge button. Enable `git rerere` to remember conflict resolutions. And only stack truly dependent changes — independent work should be separate, non-stacked PRs.

---

## Part 2: Jujutsu (jj)

### A version control system that rethinks Git's worst decisions

Jujutsu was started in late 2019 as a hobby project by **Martin von Zweigbergk**, a senior Google engineer working on source control systems. It has since become his full-time project at Google, with several other Googlers contributing. Despite Google's involvement, it is not an official Google product. The repository moved to the `jj-vcs` GitHub organization in December 2024 and has accumulated over **22,800 GitHub stars**.

Jujutsu combines ideas from Git (data model, speed), Mercurial (anonymous branching, revsets, simple CLI), and Pijul/Darcs (first-class conflicts), adding innovations not found in any of them. It uses **Git as its storage backend** — commits created by jj are regular Git commits, pushable to any Git remote. You can always switch back to pure Git. The key insight is that jj doesn't replace Git's data model; it replaces Git's terrible user interface with something fundamentally better.

Four design decisions set jj apart from Git:

**The working copy is always a commit.** Every time you run any `jj` command, it automatically snapshots your working directory into the current commit. There is no staging area, no index, no `git add`. You never see "your local changes would be overwritten" errors. You never need `git stash`. Your work is always saved. If you want to switch to a different change, just `jj edit <id>` — your current work is already committed.

**Conflicts are first-class data, not emergencies.** In Git, a rebase conflict halts everything until you resolve it. In jj, conflicts are recorded as structured data within the commit. `jj rebase` **always succeeds**. You resolve conflicts whenever you want — not when the tool forces you. Fix a conflict in one commit and the resolution automatically propagates to all descendants. This alone makes stacked workflows dramatically easier.

**Every operation is undoable.** The operation log (`jj op log`) records every mutation to the repository — commits, rebases, fetches, pushes. `jj undo` reverses the last operation and can be called repeatedly. `jj op restore <id>` restores any previous state. This creates an unmatched safety net for experimentation.

**Change IDs are stable across rewrites.** Every change gets a randomly-generated identifier that **never changes** even as you amend, rebase, or rewrite the commit. The underlying Git SHA changes, but the change ID stays the same. This means jj can automatically track changes across rewrites and rebase descendants accordingly — something Git simply cannot do.

### Daily workflow and essential commands

Getting started is straightforward:

```bash
brew install jj                                    # Install (macOS)
jj config set --user user.name "Your Name"
jj config set --user user.email "you@email.com"

jj git clone https://github.com/owner/repo         # Clone (colocated by default)
# OR: cd existing-git-repo && jj git init --colocate  # Add jj to existing repo
```

A colocated workspace means both `.jj/` and `.git/` exist at the repo root. You can use `jj` and `git` commands interchangeably — IDEs, build tools, and Git-expecting tooling work normally. Your teammates won't even know you're using jj.

The core daily commands replace Git's most common operations:

```bash
jj new -m "Implement feature X"       # Start a new change (like checkout -b + commit)
# ... write code — it's auto-saved into the current commit ...
jj diff                                # See what you've changed (in the current commit)
jj describe -m "Better message"        # Update the commit message anytime
jj new                                 # Finalize this change, start a new empty one on top
```

**`jj squash`** moves changes from the current commit into its parent (useful for the "work in @, squash into @-" pattern). **`jj split -i`** interactively splits a commit into two. **`jj rebase -s <change> -d main`** rebases a change and all its descendants onto main — and it always succeeds, even with conflicts. **`jj log`** shows a compact ASCII graph filtered to your mutable changes by default.

The **revset language** (inspired by Mercurial) lets you query changes with expressive filters:

```bash
jj log -r 'trunk()..@'                 # All changes between trunk and working copy
jj log -r 'author("Alice") & conflicts()'  # Alice's conflicted changes
jj log -r 'bookmarks()'               # All bookmarked revisions
```

**Bookmarks** (renamed from "branches" in v0.22, October 2024) are named pointers to commits, equivalent to Git branches for interop. Unlike Git branches, they don't auto-advance with new commits. You create them when you're ready to push:

```bash
jj bookmark create my-feature -r @-
jj git push --bookmark my-feature
```

### How jj handles stacked changes without any extra tooling

Creating a stack in jj is just a sequence of `jj new` commands:

```bash
jj new main -m "Refactor: extract auth helper"
# ... write code ...
jj new -m "Feature: add OAuth endpoints"
# ... write code ...
jj new -m "Feature: add OAuth UI"
# ... write code ...
```

This creates a linear chain of three changes. To **edit the middle change**, you simply:

```bash
jj edit <middle-change-id>
# ... make your fix ...
# jj automatically prints: "Rebased 1 descendant commits onto updated working copy"
```

That's it. No manual rebase. No `--continue`. No force-pushing individual branches. All descendants are instantly and transparently rebased. If the edit causes conflicts in a descendant, jj records the conflict as data — it doesn't block you. Resolve it whenever you want, and the resolution propagates further.

The **`jj absorb`** command is particularly powerful for stacks. When you're at the top of a stack and realize a fix belongs in an earlier change, `jj absorb` automatically analyzes which ancestor commit last touched each modified line and distributes your changes to the appropriate commits — like a smarter `git commit --fixup` combined with `git rebase --autosquash`.

To push a stack for review, create bookmarks at each PR boundary and push:

```bash
jj bookmark create auth-refactor -r <change-A>
jj bookmark create oauth-api -r <change-B>
jj bookmark create oauth-ui -r <change-C>
jj git push --bookmark auth-refactor --bookmark oauth-api --bookmark oauth-ui
```

Then create PRs on GitHub with the appropriate base branches (auth-refactor → main, oauth-api → auth-refactor, oauth-ui → oauth-api). Tools like **jj-stack**, **jj-spr**, and **jj-ryu** automate this PR creation step.

### Current maturity, limitations, and ecosystem

Jujutsu describes itself as "experimental" but all core developers use it daily to develop jj itself. Chris Krycho used it full-time for 7+ months on all personal and open-source work; "no one has noticed." The project is pre-1.0, meaning CLI commands may change between versions (the branch → bookmark rename being a notable example).

**Known limitations** include no Git submodule support, no partial/shallow clones, limited pre-commit hook support (a frequently cited friction point — `jj fix` is a partial workaround for formatters/linters), and some CLI churn between releases. The ecosystem of third-party tools is growing rapidly: **lazyjj** and **jjui** for terminal UIs, **GG** for a desktop GUI with drag-and-drop rebasing, **VisualJJ** and **Jujutsu Kaizen** for VS Code, and **Selvejj** for JetBrains IDEs.

Google uses jj internally with custom backends designed to scale to their monorepo. Externally, adoption is strongest among individual developers and small teams, particularly in the Rust ecosystem community. **JJ Con 2025** was held, indicating growing community organization. The most influential adoption writings include Chris Krycho's "jj init" essay, Steve Klabnik's comprehensive tutorial, and Sandy Maguire's "Jujutsu Strategies" post.

---

## Part 3: How stacked PRs and Jujutsu connect

### Why jj makes Graphite's core value proposition redundant for local workflow

Graphite's primary value is automating the painful parts of stacked PRs in Git: cascade rebasing, branch tracking, and PR synchronization. Jujutsu eliminates the first two problems entirely at the VCS level. Editing any commit in a stack automatically rebases all descendants — no "restacking" step needed. Change IDs mean you never lose track of a change across rewrites. First-class conflicts mean rebases never fail. The working-copy-as-a-commit model means you never stash, never lose work, and switch between changes instantly.

Where Graphite still wins is **forge integration**. `gt submit --stack` creates or updates all stacked PRs with one command, adds navigation comments, and provides a web review UI. jj has no built-in PR management — you create bookmarks, push them, and create PRs manually or with third-party tools (jj-stack, jj-spr, jj-ryu). Graphite also offers a **merge queue** for landing stacks atomically, team dashboards, and AI code review — features that don't exist in the jj ecosystem.

| Dimension | Graphite + Git | Jujutsu natively |
|---|---|---|
| Editing mid-stack | `gt modify` + auto-restack | `jj edit` — instant, automatic |
| Conflict handling | Standard Git conflicts block operations | First-class: always succeeds, resolve later |
| PR creation | One command for entire stack | Manual bookmarks + push, or third-party tools |
| Merge queue | Built-in | Use GitHub's native or external tooling |
| Learning curve | Low (~5 new commands on Git) | Moderate (new mental model, ~1–4 hours) |
| Team adoption needed | No (reviewers use GitHub) | No (colocated mode, teammates see Git) |
| Cost | Free tier limited; $20–40/user/month for teams | Free, open-source (Apache 2.0) |
| Forge support | GitHub only | Any Git remote |
| Local VCS experience | Still Git underneath | Dramatically superior (undo, no stash, auto-snapshot) |

### Practical recommendations for a Git-experienced developer

**If you want stacked PRs with minimal disruption**, start with Graphite. It adds ~5 commands on top of Git, requires no team buy-in (reviewers just see GitHub PRs), and gives you the full stacked workflow immediately. The free tier works for personal repos; teams need a paid plan.

**If you want a fundamentally better version control experience** (and stacked changes as a bonus), start with Jujutsu. Run `jj git init --colocate` in an existing repo and start using jj for your daily work. Your teammates won't know — the repo is still a Git repo. The learning curve is real but modest: most developers report **1–4 hours** to become productive, and multiple blog authors note that "you will be hard-pressed to find someone who stuck with jj for a week and decided to go back to Git."

**The recommended migration path** for most developers: start jj individually in a colocated repo. Use it for daily work — committing, rebasing, splitting changes. When comfortable, try creating a 3-change stack and pushing bookmarks for review. If you need polished PR automation, add jj-stack or jj-spr. If your team wants stacked PRs but won't change their VCS, Graphite is the pragmatic choice.

**Do not try to use jj and Graphite together.** Both tools manage Git branch state and will conflict with each other. Pick one approach: Graphite for Git-native stacked PRs with polish, or jj for a superior VCS with stacking built in.

### Conclusion

Stacked PRs represent a proven workflow that Meta, Google, and Uber have practiced for over a decade — the tooling has finally matured enough for the broader industry. Graphite is the most polished commercial solution today, particularly for teams that want low-friction adoption on GitHub. But the more transformative technology is Jujutsu, which solves the underlying problems that made stacked PRs hard in the first place. jj's automatic cascade rebasing, first-class conflicts, and operation log don't just make stacking easier — they make every interaction with version control safer and faster. The forge integration gap is closing with tools like jj-stack and jj-spr, and with over 22,800 GitHub stars and a dedicated conference, the community is reaching critical mass. For a backend developer experienced with Git, the highest-leverage move is to run `jj git init --colocate` in your most active repo today and experience the difference firsthand.