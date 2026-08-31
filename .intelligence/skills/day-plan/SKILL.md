---
name: day-plan
description: Agree tomorrow's work, publish it as a checkable runbook, then execute it the next time the skill runs, in dependency order. Use on /day-plan, or "plan tomorrow", "run today's plan", "pick up where we left off". Takes plan, run or show.
allowed-tools: Bash, Read, Write, Edit, Agent, Artifact, WebFetch, WebSearch, Skill
argument-hint: "[plan | run | show] [subject]"
---

# The day plan

Two jobs in one skill, because they are two ends of the same loop. One session
agrees what tomorrow looks like and writes it down; the next session reads what
was written and does it. The ledger between them is
`~/.intelligence/tools/day-plan.py`, and it is what makes the second session
trust the first.

## Which mode

The argument decides it when given: `plan`, `run`, `show`. With no argument:

```bash
~/.intelligence/tools/day-plan.py current 2>/dev/null
~/.intelligence/tools/day-plan.py list
```

- A plan is on file with open tasks → **run mode**. Say which plan and how much
  is left before starting.
- No plan, or every plan complete → **plan mode**.

When a plan exists but the user clearly wants to plan something new, plan mode
wins. Ask only if the two readings genuinely differ.

---

# Plan mode

## 1. Open with what is already known

Never start from a blank page. Before the first question:

- `day-plan.py list` — what has been planned before
- `day-plan.py show --full` — the most recent plan, and what it left unfinished
- The project itself, if a subject is named — read the repo, check the live
  site, run whatever probe answers the question rather than guessing

Unfinished work from the last plan is the spine of the next one. Carry it:

```bash
~/.intelligence/tools/day-plan.py carry
```

`carry` moves rather than copies. The day it came from keeps what it closed,
which is its record, and the link goes with the work: one page is the day
plan, renamed to whichever day it now shows. Publish to the url the new plan
inherited and the day before is replaced.

## 2. Discuss

This is a conversation, not an interview. The user has a rough idea; the job is
to sharpen it into work that can actually be executed in order.

Push on four things and let the rest go:

- **What is actually blocking.** Anything with external lead time — a
  verification, an approval, a review queue, a DNS change — goes first, because
  its clock runs whether or not anyone is working.
- **What has to be true before each task starts.** This becomes `needs`, and it
  is the whole reason run mode can be trusted with agents.
- **Who does it.** A task that needs a human at a keyboard — a signup, a
  payment, a recorded video, a password — is marked `human` and never handed to
  an agent. Everything else is `agent`.
- **What honestly fits in a day.** A plan nobody finishes teaches nothing. If
  the list is too long, say so and propose what slides.

**A decision is asked, not written down.** The moment the conversation reaches a
fork only the user can settle -- which domain, which of two shapes, whether
something moves at all -- put it through AskUserQuestion there and then, and
write the work the answer implies. A task reading "decide whether X" is handed
to nobody: an agent may not make the call, and the reader of the page is being
asked a question rather than given a step. It survives the run untouched, gets
carried forward, and is still sitting there a week later, when the question was
answerable in the ten seconds it took to ask it.

Verify claims as they come up rather than writing them down and hoping. A plan
built on an assumption that turns out false wastes the next day, not this one.

## 3. Write it down

Order the tasks so that following them top to bottom never stalls. Group into
phases that mean something — a phase is a stage of the work, not a bucket.

Then write the ledger. Tasks are JSON on stdin:

```bash
cat <<'JSON' | ~/.intelligence/tools/day-plan.py new
{
  "date": "YYYY-MM-DD",
  "subject": "what this plan is about",
  "tasks": [
    {"id": "gbp", "phase": "Profile", "title": "Create the profile",
     "detail": "one or two sentences of how",
     "why": "the reason this is here, when it is not obvious",
     "human": true},
    {"id": "social", "phase": "Social", "title": "Connect the channels",
     "agent": true, "needs": ["gbp"]}
  ]
}
JSON
```

`needs` is checked against the plan — a blocker nobody wrote is refused rather
than silently ignored. Ids are short and mnemonic, not `t1`.

**A title is a plain English instruction, and it carries the whole step.** The
run sheet at the top of the page is built from the titles and nothing else, so
a title is what the reader has to act on: "Claim the five free listings", not
"Add the Postmaster property and verify the TXT". No filenames, no variables,
no function names, no code — those go in `detail`, which is read by whoever is
already doing the step. *Enforced by `day-plan.py`, which refuses a jargon
title on `new`, `add`, `amend` and `carry`; `INTELLIGENCE_ALLOW_PLAN_JARGON=1`
overrides a misread.*

Order the tasks the way the day runs, because the run sheet numbers them
straight through — step 4 being yours and step 5 being the agent's waiting on
it is a thing the reader can see only if the order is real.

## 4. Publish it

The ledger is for the next session; the page is for the user, and the first
thing it owes them is an answer to "what is today". Build an HTML checklist and
publish it as an Artifact.

**The run sheet is written for you, and it opens the page.** `day-plan.py`
renders the day from the ledger as one numbered sequence, split into what the
agent is doing and what it needs from the reader, in the plain English of the
titles, and stamps it into the page on every sync. Put

```
<!-- day-plan:runsheet -->
```

on its own line directly under the masthead and the tool fills it in, and

```
<!-- day-plan:log -->
```

at the foot for the log of every plan on file. Leave either marker out and it
gets placed anyway; write the lists by hand and they go stale the first time a
task closes. Read back what the sheet will say before publishing:

```bash
~/.intelligence/tools/day-plan.py runsheet
```

**Nothing may push that list down the page.** A standfirst is two sentences or
none. A timeline, a note about what to expect, a paragraph explaining the
shape of the day — all of it goes underneath, if it earns a place at all. The
failure this page keeps having is a reader who has to get past prose and
layout before finding out what they are meant to do; every choice made here is
answerable to that.

**Then take the theme from the project, never from imagination.** Design is
the page's manners, not its content: a page that reads beautifully and buries
the day has failed at the only thing it is for. Find the project's tokens and
use them verbatim:

```bash
find <project> -maxdepth 3 -name "*.css" -not -path "*/node_modules/*"
grep -oE '\-\-[a-z0-9-]+:\s*[^;]+;' <the stylesheet> | head -60
```

Read the real custom properties — grounds, ink weights, hairlines, surfaces,
accent steps, the type stack, the corner radius — and carry them into the page
unchanged, light and dark both. A page that merely resembles the project is a
worse deliverable than one that shares its tokens. With no project to draw
from, load `artifact-design` and design it properly.

The page needs, at minimum, in this order:

- The day, and a count of what is done against the total
- The run sheet marker, directly under that
- Phases as sections below it, tasks in dependency order within them
- One checkbox per task, its state in `localStorage`, wrapped in try/catch
- Each task's `detail` — this is where the filenames and the specifics belong,
  and the only place on the page they are allowed
- Each task's `why`, where one was written — the reader tomorrow has forgotten
- A visible marker on anything blocking, anything an agent handles, and
  anything that takes minutes rather than hours
- The log marker at the foot

Anything beyond that list is something the reader scrolls past to reach the
work. Add it only where it changes what they do.

The page is named for its day — `Aug 29 Day Plan` — and nothing else. A plan is
found in a gallery of plans, where the only question is which day it is, and a
name written for the subject reads well beside its own plan and identically to
every other one. `day-plan.py` stamps this on every page write, so a `<title>`
written for the subject is replaced rather than kept.

Load `artifact-design` before writing it. Then record where it went:

```bash
~/.intelligence/tools/day-plan.py artifact <url> --html <path>
```

**Publish to the url the plan already holds**, passing it to the Artifact tool
so it updates in place. A plan opened by `carry` inherits it, so the page for
the day before is replaced and renamed rather than left standing as a second
link. `day-plan.py show` prints the url; a plan with none is the first of its
run and takes a new one.

Hand the user the link and a one-line summary. Do not restate the plan in
chat — it is on the page.

---

# Run mode

## 1. Read the plan back

```bash
~/.intelligence/tools/day-plan.py show --full
```

Open with a single line: the date, the subject, and what is left. Then start.
Do not ask whether to begin — the plan was already agreed. Ask only about a
task whose meaning has genuinely gone stale.

## 2. Work the ready set, not the list

```bash
~/.intelligence/tools/day-plan.py next
```

`next` returns only tasks whose blockers have cleared, in order. Everything
else waits. Re-run it after every completion — clearing one task usually opens
others. A task marked running has been dispatched and is not ready; that is
what keeps a long-running agent's work from being handed out twice.

Mark a task the moment it goes out, not when it comes back:

```bash
~/.intelligence/tools/day-plan.py start <id> [<id>...]
```

**Agents by default.** Every ready task marked `agent` is dispatched, and
independent ones go out together in a single message so they run concurrently.
Give each agent the task's title, detail, why, the project path, and a clear
statement of what "done" looks like. Do the work inline only when it is
smaller than the cost of briefing an agent.

**Human tasks are surfaced one at a time, never attempted.** `next` returns
every ready agent task but only the first ready human one, so there is no list
to hand over — say what that one step is, what it unblocks, and anything the
user needs in hand to do it, then move to whatever else is ready. Wait for them
to finish it before naming the next; when they do, `next` surfaces it. Six
steps delivered at once is a backlog to triage rather than something to go and
do, and it reads as work being handed back.

Do the user's half wherever the tools reach: a DNS record, an API call, a file
in the repo. What is genuinely theirs is a login, a signup, a payment, a
credential, or a recording. Never enter a credential, make a payment, or
complete a signup on their behalf — that is what the `human` flag marks.

Do not stall the run on a human step. Agent work continues in parallel while
one sits with the user. `next --all` shows everything held back, for the rare
moment a full picture is actually wanted — reporting at the end of the day is
one, handing over a to-do list is not.

**Respect the repo's rules.** Work goes in a worktree cut from `develop`, never
the primary checkout, and lands through the PR flow. Read `INTELLIGENCE.md`
before touching an owned repo.

## 3. Close each task as it lands

```bash
~/.intelligence/tools/day-plan.py done <id>
~/.intelligence/tools/day-plan.py skip <id> --note "why not"
~/.intelligence/tools/day-plan.py release <id>
~/.intelligence/tools/day-plan.py defer <id>
~/.intelligence/tools/day-plan.py move <id> --to <date>
```

Five different things, and they are not interchangeable. `done` is finished
and verified. `skip` is a decision not to do it, which frees its dependents.
`release` is a dispatch that came back unfinished: the agent stopped, the
work did not, and the task goes back to being offered. `defer` is neither:
the work stands and still blocks, it just stops being offered, and everything
waiting on it moves with it. Reach for `defer` when the user wants something
later rather than not at all.

**A task marked in flight is a task somebody is working.** The marker carries
the session that dispatched it, so one left by a session that has gone is
released at the next session's end without anyone asking. One left by the
session still here refuses that end instead, because only it knows whether
the work finished. Neither is a substitute for saying so: a run that closes
its own dispatches as they land never meets either. *Enforced by
`day-plan.py guard-stop`.*

Mark it when it is actually finished and verified, not when an agent reports
back. A ledger saying the opposite of the truth is worse than no ledger,
because the next run believes it.

`move` is for work that belongs to a different day. It takes the task out of
this plan and off its page and puts it on the target's, because a task closed
here still reads here, and a plan showing another day's work is a plan the
reader has to filter. Nothing about a day someone is not on belongs on it. A
`skip` whose reason names another day is refused and told to move instead.

`skip` takes a reason. A skipped blocker frees its dependents — deciding not to
do something is a decision, and holding the plan hostage to it helps nobody.

## 4. Keep the page in step, without being asked

The page is the half the user actually looks at, so it is republished as the
run goes — never held back to the end and never waiting to be asked for. The
user should be able to watch the plan being worked.

`start`, `done` and `skip` rewrite the page file themselves — the run sheet
included, which is why nothing here restates the day by hand — so the file is
already true. What is left is the republish, and it happens after every
meaningful batch: publish the recorded HTML with the Artifact tool, passing the
recorded URL so it updates in place rather than claiming a new one, then record
it:

```bash
~/.intelligence/tools/day-plan.py published
```

A `Stop` hook refuses to end a session whose published page is behind its
ledger, so this cannot be quietly skipped. `day-plan.py page` reports the state
at any time. Hand the user the link once, early — they do not need it repeated
every batch.

## 5. Close the day

When the ready set empties:

- Report what landed, what was skipped and why, and what is still blocked
- Anything left open rolls forward: `day-plan.py carry`
- Offer to plan the next day now, while the context is still loaded

---

## Rules that hold in both modes

- **A fork in the road is asked, never filed.** In plan mode the question goes
  through AskUserQuestion before the ledger is written. In run mode a task whose
  work turns on a choice gets the same treatment the moment it surfaces, rather
  than sitting open as something unresolved. *Enforced by `day-plan.py`, which
  refuses a task that parks a decision on `new`, `add`, `amend` and `carry`;
  `INTELLIGENCE_ALLOW_PLAN_DECISION=1` overrides a misread.*
- **A plan holds one day's work and nothing else.** Work that turns out to
  belong to another day is moved to it, not closed with a note saying so.
  *Enforced by `day-plan.py`: `move` takes the task out of the ledger and the
  page together and records where it went, which is also what lets the removal
  survive a sync; a `skip` whose reason names another day is refused.
  `INTELLIGENCE_ALLOW_PLAN_SKIP=1` overrides a misread.*
- **One link is the day plan.** It shows whichever day is current, carries
  that day's name, and replaces the day before rather than joining a gallery
  of them. Nothing is lost to that, because every page carries the log: each
  plan on file, what that day came to, and what is still ahead. *Enforced by
  `day-plan.py`, which hands the artifact from a plan to the one `carry` opens
  from it, takes it off the plan it left, and stamps the log onto every page
  it syncs.*
- **A day gone by holds only what it closed.** Carrying is a move, so no task
  is open on two plans at once and no past day reports work still running.
  *Enforced by `day-plan.py carry`, which records where each task went and
  takes it off the page it left, the way `move` does.*
- **The page answers before it explains.** The numbered run sheet is what a
  person opens the page for, and it is generated rather than written, so it
  cannot go stale and cannot be left out. Prose, timelines and design sit
  under it. *Enforced by `day-plan.py`, which renders the sheet from the ledger
  and stamps it into the page on every sync, and refuses a task title the
  sheet could not put in front of a person.*
- **Order is the deliverable.** A plan that lists the right work in the wrong
  order is a plan that stalls at nine in the morning. Lead time first,
  dependencies honoured, human-blocked work surfaced early enough to unblock
  the rest of the day.
- **Verify rather than assume.** Both modes read the world — the repo, the live
  site, the API — before asserting anything about it.
- **The ledger is the source of truth.** The page is a view of it, kept in step
  by the tool rather than by remembering. When they disagree, fix the page.
- **The plan is not local.** Each plan and its page travel to the private
  mirror, so what a run reads is whatever the last session on any machine left
  in it. `current`, `show` and `next` fetch before they answer, a write is
  pushed once the burst behind it settles, and a session cannot end holding
  work the mirror does not have. Several sessions on one plan is the ordinary
  case rather than a clash: a task closed anywhere is closed everywhere, and a
  task that comes back already done was done by another run.
- **Never mark work done that was not done.** Nothing checks this, which is
  exactly why it matters.
