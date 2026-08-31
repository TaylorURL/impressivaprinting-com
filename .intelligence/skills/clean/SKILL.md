---
name: clean
description: Clean up code and project structure: naming, organization, dead code, comments, linters, and repeated patterns extracted into shared utilities. Use on /clean, or "clean this up", "tidy", "reorganize", "remove dead code", "this is messy".
---

# Clean

Cleanup work is about lowering the ongoing cost of a codebase: making structure
predictable, deleting what doesn't earn its place, keeping comments honest, and
holding the linter's line. The goal each run is to **complete every item you take
on to the fullest** — a half-cleaned directory is often worse than an untouched
one, because it reads as intentional.

You are optimizing for the next person to open this file (often the user, often
future-you). Everything below serves that.

## Scope: read the context first

`/clean` may arrive with specific context ("clean up `src/net/`", "the comments
in the auth module") or none at all ("let's clean up the project"). Before doing
anything, pin down what "the code" refers to:

- **Specific target** (a file, directory, or module named): confine the sweep to
  it and its immediate dependents (imports you must update, callers you must
  check). Don't wander the whole repo.
- **Non-specific / whole-project**: the target is the source tree, minus
  generated and vendored paths (`node_modules`, `dist`, `build`, `release`,
  `.next`, lockfiles, migrations, anything in `.gitignore` or linter `ignores`).

When in doubt about boundaries, state your interpretation in the plan (next
section) rather than guessing silently.

## Always plan before you touch anything

Whole-project cleanup changes a lot of files at once, and several of the moves
here are hard to eyeback later (renamed directories, deleted code, rewritten
comments). So survey first, then present a plan, then execute — never dive
straight into edits.

### 1. Survey

Build an accurate picture before proposing changes:

- **Toolchain**: find the linter/formatter and how it's run. Check `package.json`
  scripts and config files (`eslint.config.*`, `.eslintrc*`, `biome.json`,
  `.prettierrc*`, `ruff.toml`, `pyproject.toml`, etc.). Note the lint command
  (e.g. `npm run lint`), the test command, and any build/typecheck step — you'll
  need all three to verify at the end.
- **Structure**: map the directory tree (excluding ignored paths). Note naming
  conventions in use, nesting depth, folders that mix conventions, dumping-ground
  directories, near-empty directories, and files that sit somewhere surprising.
- **Dead code**: run whatever the ecosystem offers (linter unused-vars, and if
  available `knip`, `ts-prune`, `depcheck`, `vulture`, etc.) and grep for usages
  of exported symbols. Treat tool output as leads, not verdicts.
- **Comments**: note the prevailing style and how densely the code is
  documented; section 3 hands the judgment to the `writing-comments` skill.
- **Repetition**: scan for the same shape appearing across files — the same
  three-line idiom, the same 10-line "connect X and clean up" dance, the same
  inline formatter. Sample by domain (see Area 5): DB/network, formatting/
  display, async/timers, DOM/framework, math/data. What repeats now often
  points at a utility that ought to exist.

### 2. Present the plan

Lay out concretely what you intend to do, grouped by the five areas below, sized
to the scope. Call out anything destructive or risky (directory renames that
touch many imports, deletions you're less than certain about, utility
extractions that will touch many callers) so the user can veto specifics. Get
an explicit go-ahead before executing.

Scale the plan to the request: a narrow, low-risk target warrants a one-line
plan and a quick confirm; a whole-project sweep warrants a real breakdown.

### 3. Execute, then verify

Work through the approved plan. Track the items so nothing is left half-done —
"to the fullest" means you don't stop at the easy 80%. Then run the verification
in the last section.

---

## The five areas

### 1. Directory and file organization & naming

Predictable structure is the cheapest documentation a project has. Aim for a tree
where someone can guess where a thing lives.

- **Naming consistency**: within any one directory, don't mix conventions —
  `userProfile.js` next to `user-settings.js` next to `UserAvatar.js` forces
  everyone to memorize exceptions. Detect the *dominant* convention (per the
  ecosystem and the surrounding code) and align to it rather than imposing a
  personal preference. Framework conventions win where they apply (e.g. React
  components often `PascalCase`, config files `kebab-case`).
- **Directory naming**: apply the same consistency to folder names, and make them
  describe what they hold.
- **File-extension separation**: files with different source extensions (e.g.
  `.js` and `.jsx`, `.ts` and `.tsx`) must not live in the same folder. A mixed
  folder means two kinds of module are cohabiting — split them into separate
  directories (e.g. plain logic modules in one, JSX/TSX components in another)
  so the extension boundary matches the directory boundary. Update all imports
  after the split, like any other move.
- **Depth**: right-size nesting. A chain of single-child folders (`a/b/c/one.js`)
  adds friction with no benefit — flatten it. A directory with 40 unrelated files
  wants grouping. Neither extreme is good.
- **Organization & usage**: move misplaced files next to what they relate to,
  group by feature/responsibility over file-type where the project leans that way,
  and delete directories that are empty or orphaned after moves.

**Moving or renaming files breaks imports.** This is the highest-risk area. For
every move, update every reference — imports, re-exports, dynamic `import()`,
config paths, test paths, string references. Prefer the tooling's rename/move if
it rewrites imports; otherwise grep the old path across the repo and fix each
hit. Verify the build/tests after moves, not just at the very end.

### 2. Dead code removal

Dead code isn't only code that's never imported — that's the easy half. The
costlier half is code that *is* wired in but earns nothing:

- Never imported / never called; unreachable branches; unused exports.
- Imported and invoked but inert: no-op wrappers, one-line pass-through functions
  that only forward arguments, abstractions with a single caller that add a layer
  without adding meaning, parameters/props threaded through but never read, flags
  that are always the same value, defensive branches for conditions that can't
  occur, `else` after exhaustive returns.
- Commented-out code (delete it — version control remembers).
- Redundant re-implementations of something the codebase or a dependency already
  provides.

**Delete with judgment, not just tool output.** A symbol can be "unused"
statically yet reached dynamically (string keys, reflection, framework
conventions), be part of a deliberate public API, or exist for a side effect.
Before removing anything non-obvious, confirm it's truly reachable-for-nothing —
check for dynamic usage and whether it's an intended external surface. When
genuinely unsure, flag it in the plan instead of deleting silently.

### 3. Rewrite the comments

Comments and in-code documentation are judged by the `writing-comments` skill,
not by this one. Invoke it via the Skill tool and apply it to every file in
scope — it decides what to add, rewrite, and delete, and it goes further than a
tidy-up would: it also calls for documentation that is missing on named types,
struct fields, and private symbols that carry real behavior.

Then record the pass, so the next run over this repo covers only what has
changed since. Nothing refuses a landing over the ledger, so the record is the
only thing standing behind the work: mark a file only once it is actually done.

```bash
~/.intelligence/tools/comment-pass.py mark <files in scope>
```

Two things this skill still owns, because they are hygiene rather than judgment:
commented-out code (delete it, covered in section 2) and any comment carrying an
AI self-reference or an emoji (strip it).

Keep license headers and legally required notices regardless.

### 4. Linter compliance — hold the line

Leaving the linter broken is not an option. Every violation in scope ends one of
two ways: **the code is fixed**, or **the rule is deliberately changed**.

- Run the project's linter and read what it reports. Fix violations by correcting
  the code — that's the default and the large majority.
- Changing a rule is a real decision, not an escape hatch. Do it only when the
  rule genuinely doesn't fit the project (not to silence a legitimate finding),
  and surface the change in your summary so it's a conscious choice, not a
  quiet one. Never blanket-disable inline (`eslint-disable`, `# noqa`) just to
  make a warning disappear — that hides the problem instead of resolving it.
- Respect existing intent: a config may keep certain rules as warnings on
  purpose. Don't silently promote/demote severities; if you think a warning
  should be fixed, fix the code.
- If a formatter is configured (Prettier, Biome), run it so style is consistent
  rather than hand-fixing whitespace.

Apply the same fully-resolved standard to the whole scope — don't leave a tail of
"minor" violations behind.

### 5. Extract shared utilities (only when the repetition is real)

Cleanup is the moment to notice patterns that have quietly duplicated
themselves across the codebase and collapse them into a small utility library.
Done well this shrinks every caller, prevents the copies from drifting apart,
and gives the next feature a natural home. Done reflexively — extracting one
call site into a "helper" nobody else needs — it does the opposite.

**When to extract.**

- The same shape appears in **≥2 real call sites**, ideally 3+. Two shallow
  occurrences with different surrounding predicates usually read cleaner
  inline than behind a name.
- The pattern is **generic** — a formatter, a clamp, a small async harness, a
  DB read shape. Domain-shaped operations (a query that knows about your
  `world.units` slot/hp/alive predicate, a solver that reads business rules)
  belong beside the domain, not in the utility library.
- The extraction **shrinks each caller** and makes the intent clearer. If the
  helper's name is longer than its body, or callers have to read the helper
  to understand what the call does, keep the code inline.

**Where to look.** Sample by domain — different domains hide different
patterns:

- **Database / network** — repeated `getSession()` + user-id extraction, the
  same `.from(t).select().eq().maybeSingle()` shape, edge-function invocation
  wrappers, realtime channel subscribe/cleanup, retry-with-backoff idioms.
- **Formatting / display** — number → localized string, percent-of-fraction,
  compact currency, duration, "Month Year" date, thousands-with-suffix
  ("1,250 km"), signed values.
- **Async / timers** — `setTimeout` + cleanup, rAF loops with cancel-on-
  unmount, `let cancelled = false` cancellation flags, sleep/backoff,
  visibility-pause loops, fire-and-forget promise wrappers.
- **DOM / framework** — window/document event add/remove pairs, latest-value
  refs, disclosure trios (open state + open + close), localStorage-backed
  stores, try/catch-around-imperative-API scaffolding (map/canvas/audio).
- **Math / data** — `Math.max(lo, Math.min(hi, x))` clamps, 0..1 normalize
  + clamp, angle wrap, bounded/signed random draws, `arr.find(x => x.id ===
  id)`, `bucket[k] = (bucket[k] || 0) + 1`, `new Map(arr.map(x => [k, v]))`.

Cast the net wide during survey, not deep — enumerate candidates from every
domain, then prune. It's the pruning that matters.

**How to organize.** Respect what already exists — extend the current utility
tree instead of forking a parallel one. If there's no utility tree yet, add
one at a level all callers can reach (a top-level `lib/` for a monorepo, a
`src/lib/` inside a package). Group by domain, one small file per domain
(`math.js`, `iter.js`, `db.js`, `raf.js`, …). Keep the module boundaries
narrow — utilities that only serve UI live near the UI; utilities the server
also uses live at the shared root.

**How to pick names.** Name utilities for **what they do**, not for the
callsite that inspired them. `clamp01(x)`, `byId(arr, id)`, `readRow(t, opts)`
read regardless of where they land. Match the ecosystem's convention
(camelCase in JS/TS, snake_case in Python, etc.); don't invent a house style
mid-cleanup.

**How to present the change.** Extract, then refactor callers, then verify.
Never leave a utility that no caller uses. Never leave a caller half-migrated
— pick a domain, do every callsite in it, then move to the next. Add small
pure-function tests for anything with real logic (a formatter, a clamp, a
weighted pick). A utility library with untested primitives becomes the
default source of bugs the moment its behaviour shifts.

**When to leave it alone.** Not every duplication deserves collapsing. Skip
extraction when:

- The pattern only fits 2 callsites and each is shorter than the helper name.
- The pattern superficially matches across callers but the surrounding
  predicates diverge — a helper here erases a distinction that matters.
- The behaviour has real semantic differences per callsite that the shared
  helper would have to expose as options — an options bag with 6 flags is
  worse than the copies.
- The pattern is heavy domain logic that would drag business rules into a
  generic library.

Trust the future refactor. It's cheaper to extract when the third caller
appears than to guess wrong today.

---

## Verify before you're done

Cleanup that breaks the build is a net loss. After executing, confirm the project
is at least as healthy as you found it:

1. **Lint** passes (or is clean except for pre-existing, intentionally-kept
   warnings you didn't introduce).
2. **Tests** pass — run the suite. Dead-code removal and file moves are exactly
   the changes that silently break things.
3. **Build / typecheck** succeeds if the project has one.

If anything fails, fix it before reporting done. Then give a concise summary: what
moved, what was deleted (and why, for anything non-obvious), the comment pass, and
any lint rules you changed. Keep it scannable — the user should be able to review
the sweep without re-reading every diff.

## Then run the markdowner pass

Cleanup routinely moves files, renames directories, deletes code, and removes
options — exactly the changes that leave a project's Markdown stale: a README
pointing at a path that no longer exists, a documented flag that's now gone, a
structure diagram that no longer matches the tree. So after the cleanup is
verified and summarized, always run the `/markdowner` skill over the same scope
to bring the docs back into agreement with the code you just changed. It's the
natural other half of a cleanup — code and docs left consistent, not just the
code. Fold its findings into the same run rather than handing back a project
whose docs you know are now out of date.
