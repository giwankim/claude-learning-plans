# Jujutsu (jj): the Git successor that treats version control like it's 2026

**Jujutsu is a Git-compatible version control system that eliminates the staging area, makes every working-copy state a commit, stores conflicts as first-class data, and provides universal undo — solving the most persistent pain points developers face with Git while remaining fully compatible with existing Git repos and forges.** Built by Google engineer Martin von Zweigbergk starting in 2019, jj now has ~25,000 GitHub stars, is used internally at Google (~900 users as of late 2025, with plans to replace their Mercurial-based internal client), and is daily-driven by developers at companies like Oxide Computer. Because jj uses Git as its storage backend, adoption is zero-risk: your teammates won't know you switched, and you can revert by deleting a single `.jj` directory.

The core insight is radical simplification. Where Git exposes four distinct zones (working directory, staging area, HEAD, history) and dozens of commands to shuttle changes between them, jj has one concept: **commits**. Your working copy is a commit. Your stash is a commit. Everything is a commit. This collapses Git's cognitive overhead while simultaneously making powerful operations — editing history mid-stack, rebasing through conflicts, undoing any operation — trivial.

---

## Six Git pain points that jj eliminates by design

**The staging area tax.** Git's index requires learning what `git reset --soft`, `--mixed`, and `--hard` do, why `git rm` stages but file deletion doesn't, and the difference between `git restore --staged` and `git checkout`. jj removes the staging area entirely. Your working copy *is* the current commit, auto-snapshotted every time you run any `jj` command. As Evan Todd writes: "In Git you have the working copy, the staging area, the HEAD commit, and the commit history. There are a lot of different commands to move changes between these areas... In Jujutsu, the working copy is the current commit. You make changes, and whenever you run any Jujutsu command, those changes are automatically snapshotted. That's it."

**Stash fragility.** Git stash is a separate mechanism that can fail to apply cleanly, gets lost in long stash lists, and can't be rebased. In jj, stashing is unnecessary — your in-progress work is already a commit. Switch to any other change with `jj edit` or `jj new`, and your work stays exactly where you left it. Tony Finn explains: "Having concepts like the stash and the working copy be 'just a commit' does wonders for simplifying the mental model."

**Rebase conflicts blocking work.** In Git, a conflicting rebase halts the entire operation, forcing you to resolve immediately or abort. jj's **first-class conflicts** are stored as structured data inside commits — operations never fail due to conflicts. You can continue working, create child commits, and resolve conflicts when convenient. As the LWN.net article notes: "Jujutsu doesn't need an equivalent of `git rebase --continue`. Every rebase and every merge completes in one command, without stopping in the middle to ask for assistance."

**Losing work during branch switches.** Git's infamous "error: Your local changes to the following files would be overwritten by checkout" disappears. Since the working copy is always committed, switching between changes never fails and never loses work.

**Detached HEAD confusion.** In jj, branches (called "bookmarks") are optional labels, not a required part of the workflow. You're always "on a commit" — there's no detached HEAD state. You don't need to name a branch before you've built the feature.

**Stacked changes requiring external tooling.** Managing dependent PRs in Git requires tools like Graphite, ghstack, or painful manual rebasing of every downstream branch. In jj, editing any commit in a stack **automatically rebases all descendants**. Sandy Maguire captures it perfectly: "If my colleagues ask for changes during code review, I just add the change somewhere in my change tree, and it automatically propagates downstream. No more cherry picking. No more inter-branch merge commits."

---

## The five design decisions that make jj fundamentally different

### Working copy as a commit

This is jj's most consequential design choice. Checking out a revision creates a new working-copy commit on top of it. Every file edit amends this commit automatically. This single decision collapses Git's four-zone model into one, eliminates `git add`, `git stash`, and detached HEAD, and ensures you **never lose uncommitted work**. The official README states it "simplifies the user-facing data model (commits are the only visible object), simplifies internal algorithms, and completely subsumes features like Git's stashes or the index."

### First-class conflicts

Borrowed from patch-based VCS systems like Darcs and Pijul, jj stores conflicts as structured data — not text markers — inside commits. This means rebase always completes, merge always completes, and you can defer conflict resolution indefinitely. When you do resolve a conflict, the resolution **automatically propagates** to all descendant commits. Evan Todd explains: "It even automatically resolves the conflict in all later commits in the history, unlike `git rebase`, which often makes you resolve the same conflict over and over in each commit."

### Operation log and universal undo

Every mutation to the repository is recorded atomically in an operation log — think of Git's reflog but for the entire repo state, not per-ref. Running `jj undo` reverses any operation: a bad rebase, an accidental abandon, a messy merge. Running `jj op restore <id>` teleports the repo to any previous state. You can even inspect past states without modifying anything via `jj --at-op=<id> log`. As Evan Todd puts it: "Have you ever messed up a Git repository so bad that you had to delete and redownload it? With Jujutsu you just type `jj undo`. Version control has finally entered the 1960s."

### Change IDs vs commit IDs

Every change in jj has two identifiers: a **change ID** (lowercase letters only, e.g., `tnosltrr`) that is permanent and survives rewrites, and a **commit ID** (hex, like a Git SHA) that changes when the commit is amended or rebased. Change IDs solve the problem of tracking a logical change through history rewrites — something Git has no native answer for. Kuba Martin summarizes: "immutable change IDs, mutable changes, mutable revision IDs (Git SHAs), immutable underlying revisions."

### Automatic descendant rebasing

Whenever you rewrite any commit — amending it, rebasing it, splitting it — all descendant commits and bookmarks automatically rebase on top. This is what makes `jj edit` so powerful: jump to any commit in your stack, make changes, and everything downstream updates. The official docs describe it as "a completely transparent version of `git rebase --update-refs` combined with `git rerere`, supported by design."

---

## What developers say after switching

The developer community's response to jj has been unusually enthusiastic. **Chris Krycho**, after six months of daily use across all personal and open-source repos, wrote a 10,000-word essay calling jj "a real shot" at replacing Git: "At a minimum you get a better experience for using Git. At a maximum, you get an incredibly smooth on-ramp to what I earnestly hope is the future of version control." He reported using jj for seven months at Oxide Computer without anyone noticing, because the Git interop is "that solid and robust" — and when he finally told colleagues, over 10 engineers adopted it.

**Steve Klabnik**, author of *The Rust Programming Language*, wrote a comprehensive tutorial and observed that jj "has a property that's pretty rare: it is both simpler and easier than Git, but at the same time, it is more powerful." **Sandy Maguire** was even more emphatic: "Picking up jj has been the best change I've made to my developer workflow in over a decade... We all feel ashamed that our commit histories don't tell a clean story, because doing so in Git requires a huge amount of extra work. Version control Stockholm syndrome. Git sucks. And jujutsu is the answer."

The pattern across testimonials is strikingly consistent. **Arne Bahlo** removed jj from a repo to test whether he'd miss it — and added it back the same day. **Kristoffer Balintona** highlighted fearless experimentation: "With `jj op restore`, I can merge branches, create conflicts, resolve conflicts, mess up… then go back as if it never happened." A Hacker News commenter captured the trajectory many report: "The auto-committing behavior is a bit weird at first, but now I don't want to go back to git. It feels like the step from SVN to Git."

Martin von Zweigbergk started jj as a hobby project in late 2019. It became his full-time project at Google, where it is in open beta with ~900 internal users and growing. The tool uses an abstract backend architecture — the Git backend for open-source use, and a custom cloud backend internally — specifically designed to support Google's **86 TB monorepo**. A Linux-only GA inside Google was planned for early 2026, after which the team intends to migrate users from their existing Mercurial-based client.

---

## A complete workflow: from clone to stacked PRs

The following walkthrough demonstrates a realistic feature development cycle using jj, highlighting where the experience diverges from Git. Every command is real jj syntax.

### Setting up and starting work

```
$ jj git clone https://github.com/myorg/webapp
Fetching into new repo in "webapp"
$ cd webapp
```

This creates a colocated repo (both `.jj` and `.git` exist). Your teammates see a normal Git repo. Check the starting state:

```
$ jj log
@  sqpuoqvx you@example.com 2026-02-18 13:00:00 a1b2c3d4
│  (empty) (no description set)
◆  zrwmvnpk you@example.com 2026-02-18 12:55:00 main 8f4e2a1b
│  Merge pull request #142: fix auth timeout
~
```

The `@` symbol marks your working-copy commit — an empty commit automatically created on top of `main`. The `◆` symbol indicates an immutable commit (trunk). Change IDs are on the left (`sqpuoqvx`), commit hashes on the right (`a1b2c3d4`).

### Building a stack of changes

Start your first change. No branch name needed:

```
$ jj describe -m "refactor: extract auth middleware"
$ vim src/middleware/auth.rs    # make your changes
$ jj diff --stat               # review (changes auto-saved to current commit)
 src/middleware/auth.rs | 47 +++++++++++++++++-----------
 src/routes/login.rs   |  8 +----
 2 files changed, 31 insertions(+), 24 deletions(-)
```

**In Git, you would:** `git add -A && git commit -m "refactor: extract auth middleware"`. In jj, your edits are already in the commit.

Now stack a second change on top:

```
$ jj new -m "feat: add rate limiting to auth"
$ vim src/middleware/rate_limit.rs
$ vim src/middleware/auth.rs
```

And a third:

```
$ jj new -m "test: add rate limiting tests"
$ vim tests/rate_limit_test.rs
```

View your stack:

```
$ jj log
@  kkmpptlx you@example.com 2026-02-18 14:10:00 f8d3e2c1
│  test: add rate limiting tests
○  rrssnnww you@example.com 2026-02-18 14:00:00 c5a1b7d9
│  feat: add rate limiting to auth
○  sqpuoqvx you@example.com 2026-02-18 13:30:00 e2f4a8c6
│  refactor: extract auth middleware
◆  zrwmvnpk ... main 8f4e2a1b
│  Merge pull request #142: fix auth timeout
~
```

Three clean commits stacked on main — no branch names needed yet.

### Editing mid-stack with automatic rebasing

A reviewer points out that your auth middleware refactor (the first change) has a bug. In Git, this would require `git stash`, `git rebase -i` with `edit`, fixing the code, `git commit --amend`, `git rebase --continue` (possibly resolving conflicts at each step), and `git stash pop`. In jj:

```
$ jj edit sqpuoqvx              # jump to the auth refactor commit
Working copy (@) now at: sqpuoqvx e2f4a8c6 refactor: extract auth middleware
$ vim src/middleware/auth.rs     # fix the bug
$ jj log
@  sqpuoqvx you@example.com 2026-02-18 14:20:00 7b3f1d9e
│  refactor: extract auth middleware
│ ○  kkmpptlx you@example.com 2026-02-18 14:10:00 a9c2e5f7
│ │  test: add rate limiting tests
│ ○  rrssnnww you@example.com 2026-02-18 14:00:00 d4b8f1a3
│ │  feat: add rate limiting to auth
│ ○  sqpuoqvx (rebased)
├─╯
◆  zrwmvnpk ... main 8f4e2a1b
```

Both descendant commits have **automatically rebased** onto the updated version. Note the commit hashes changed (because the content changed) but the change IDs stayed the same. Return to your test work:

```
$ jj edit kkmpptlx              # back to tests
```

### Splitting a commit that grew too large

Your rate-limiting change actually contains two logical pieces — the middleware itself and configuration changes. Split it:

```
$ jj split -r rrssnnww
```

This launches an interactive diff editor. Remove the config changes from the right pane — they become the second commit. You're prompted for descriptions for both halves. The result: your stack now has four commits, with descendant commits auto-rebased.

### Using `jj absorb` to distribute fixes

You're at the top of your stack and realize you have small fixes that belong in different ancestor commits — a typo fix in the auth refactor, a missing edge case in rate limiting. Rather than manually editing each ancestor:

```
$ vim src/middleware/auth.rs      # fix typo (belongs in first commit)
$ vim src/middleware/rate_limit.rs # fix edge case (belongs in second commit)
$ jj absorb
Absorbed changes into 2 revisions:
  sqpuoqvx 3a7f9d1e refactor: extract auth middleware
  rrssnnww 8c2b4e6f feat: add rate limiting to auth
```

`jj absorb` automatically identified which lines were last modified in which ancestor commit and distributed each fix to the right place. Review what happened with `jj op show -p`, and undo instantly with `jj undo` if anything looks wrong.

**In Git**, there is no built-in equivalent. You would install the third-party `git-absorb`, create fixup commits, then run `git rebase --autosquash` — a multi-step process that can fail at each stage.

### Handling conflicts without blocking

Sync with upstream before pushing:

```
$ jj git fetch
$ jj rebase -d main
Rebased 4 commits onto updated main
New conflicts in 1 commits:
  rrssnnww: src/middleware/auth.rs
```

The rebase **completed successfully** despite conflicts. In Git, this would halt at the conflicting commit, forcing you to resolve before continuing. In jj, the conflict is recorded in the commit:

```
$ jj log
@  kkmpptlx you@example.com 2026-02-18 15:00:00 b2d4f6a8
│  test: add rate limiting tests
○  rrssnnww you@example.com 2026-02-18 15:00:00 e1c3a5d7 conflict
│  feat: add rate limiting to auth
○  sqpuoqvx you@example.com 2026-02-18 15:00:00 f9a1b3c5
│  refactor: extract auth middleware
◆  zrwmvnpk ... main 2c4e6a8b
```

You can keep working on your tests. Resolve the conflict when ready:

```
$ jj edit rrssnnww
$ jj resolve                    # opens your merge tool
$ jj edit kkmpptlx              # descendant conflict automatically resolved too
```

### Pushing stacked PRs to GitHub

Create bookmarks (jj's name for branches) and push:

```
$ jj bookmark create auth-refactor -r sqpuoqvx
$ jj bookmark create rate-limiting -r rrssnnww
$ jj bookmark create rate-limit-tests -r kkmpptlx
$ jj git push -b "glob:*"
```

Each bookmark becomes a branch on GitHub. Create PRs with appropriate base branches for a clean stack. When a reviewer requests changes to `auth-refactor`, the workflow is identical to the mid-stack edit above: `jj edit`, make changes, and all downstream bookmarks auto-update. Then `jj git push -b "glob:*"` force-pushes everything in one command.

### The safety net: operation log and undo

At any point, inspect what you've done:

```
$ jj op log
@  a8f3c1d2 you@machine 30 seconds ago, lasted 15ms
│  push all bookmarks to git remote
○  b7e2d4f6 you@machine 2 minutes ago, lasted 45ms
│  rebase 4 commits
│  args: jj rebase -d main
○  c6d1e3a5 you@machine 5 minutes ago, lasted 25ms
│  absorb changes into 2 commits
│  args: jj absorb
...
```

Made a mistake? `jj undo` reverses the last operation atomically. Need to go further back? `jj op restore <id>` teleports the entire repo to any previous state. Preview before committing: `jj --at-op=<id> log` shows the repo at that point without changing anything.

---

## The essential learning path and resources

The jj ecosystem has matured rapidly. Here is the recommended progression from beginner to proficient, with the best resources at each stage.

**Start with the "why"**: Chris Krycho's essay *"jj init"* (https://v5.chriskrycho.com/essays/jj-init) is the definitive explanation of jj's design philosophy and the most widely-cited introduction. At 10,000+ words, it covers the conceptual foundations thoroughly.

**Follow a hands-on tutorial**: Steve Klabnik's *Jujutsu Tutorial* (https://steveklabnik.github.io/jujutsu-tutorial/) is a full book-length mdBook guide covering basics through advanced topics, written in the same approachable style as *The Rust Programming Language*. The official tutorial at https://docs.jj-vcs.dev/latest/tutorial/ is shorter but authoritative. For developers without Git experience, *Jujutsu for Everyone* (https://jj-for-everyone.github.io/) teaches jj from scratch.

**Learn workflow strategies**: Sandy Maguire's *"Jujutsu Strategies"* (https://reasonablypolymorphic.com/blog/jj-strategy/) covers practical day-to-day patterns for stacked changes, code review, and history editing. Arne Bahlo's *"Jujutsu in practice"* (https://arne.me/blog/jj-in-practice) and Kuba Martin's *"Introduction and Patterns"* (https://kubamartin.com/posts/introduction-to-the-jujutsu-vcs/) provide complementary perspectives.

**Watch the creator**: Martin von Zweigbergk's Git Merge 2024 talk (https://www.youtube.com/watch?v=LV0JzI8IcCY) is a hands-on demo showing real workflows. Chris Krycho has a YouTube playlist (https://www.youtube.com/playlist?list=PLelyiwKWHHAq01Pvmpf6x7J0y-yQpmtxp) complementing his written essay.

**Keep a cheat sheet handy**: Justin Pombrio's printable two-page PDF (https://justinpombrio.net/src/jj-cheat-sheet.pdf) is the best visual quick reference. For Git-to-jj command translation, the official equivalence table lives at https://docs.jj-vcs.dev/latest/git-command-table/. The community-maintained gist by elithrar (https://gist.github.com/elithrar/4a09ef750af5624b729a6f1d87a0431c) covers real workflow patterns.

**Reference documentation**: The official docs at https://docs.jj-vcs.dev/latest/ are comprehensive, covering the revset language, templating, conflict handling, and GitHub/Gerrit integration. The GitHub repository (https://github.com/jj-vcs/jj) hosts discussions, a wiki with a community-maintained media page, and issue tracking. The community is active on Discord (linked from the GitHub README) and the `#jujutsu` IRC channel on Libera Chat.

**Deeper reads worth bookmarking**: Evan Todd's *"Should I Switch from Git to Jujutsu"* (https://etodd.io/2025/10/02/should-i-switch-from-git-to-jujutsu/) provides a practical switching guide. The LWN.net article (https://lwn.net/Articles/958468/) offers an authoritative technical overview. Stavros Korokithakis' *"Switch to Jujutsu Already"* (https://www.stavros.io/posts/switch-to-jujutsu-already-a-tutorial/) is a concise, persuasive tutorial. Chris Krycho's post on `jj absorb` (https://v5.chriskrycho.com/journal/jujutsu-megamerges-and-jj-absorb/) covers advanced features.

---

## Quick command reference for Git users

| What you want to do | Git | jj |
|---|---|---|
| Create a commit | `git add -A && git commit -m "msg"` | `jj commit -m "msg"` |
| Amend current commit | `git commit --amend` | Just edit files (auto-saved) |
| Edit an earlier commit | `git rebase -i` → mark `edit` | `jj edit <change-id>` |
| Stage partial changes | `git add -p` | `jj split` |
| Stash work | `git stash` / `git stash pop` | Not needed — `jj new` to switch |
| Undo anything | `git reflog` + `git reset` | `jj undo` |
| Rebase onto main | `git rebase main` (may halt) | `jj rebase -d main` (always completes) |
| Split a large commit | `git rebase -i` → `edit` → `reset` → `add -p` | `jj split -r <id>` |
| Distribute fixes to ancestors | Install `git-absorb` + `rebase --autosquash` | `jj absorb` |
| View history graph | `git log --graph --oneline --all` | `jj log` (graph is default) |
| Push stacked branches | Manual force-push each branch | `jj git push -b "glob:*"` |

---

## Conclusion: a better mental model with zero switching cost

Jujutsu's contribution isn't incremental polish on Git's interface — it's a **fundamental rethinking of the version control mental model** that happens to be fully Git-compatible. By collapsing working copy, staging, and stash into "everything is a commit," jj makes powerful operations trivial (mid-stack edits, universal undo, non-blocking conflicts) while eliminating entire categories of errors (lost work, detached HEAD, stash conflicts, rebase --continue loops).

The zero-risk adoption path — colocated repos that look like normal Git to every tool and teammate — removes the usual barrier to trying a new VCS. The practical insight from developers who've switched is that **jj doesn't just make version control faster; it changes how you think about structuring work**, encouraging clean commit histories and stacked changes because the tooling makes them effortless rather than painful. Steve Klabnik's observation captures it well: jj is "both simpler and easier than Git, but at the same time, more powerful." That combination is rare in software tools, and it's why jj may represent the most significant evolution in everyday version control since Git itself.