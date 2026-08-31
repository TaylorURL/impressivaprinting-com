---
name: rethink
description: Judge work by what the person on the other end experiences, then propose a better shape sized honestly. Sweeps for byproducts, leftover state and unhappy paths. Use on /rethink, or "is there a better way", "what am I missing", "poke holes in this". Takes auto to carry the verdict out.
---

# Rethink

Code review asks whether the code does what it says. This asks a different
question: **what does the person on the other end actually end up with?**

Those come apart constantly. A function can be correct and still leave someone
staring at a blank panel, or hitting a button twice because nothing told them
the first press landed, or discovering three days later that a folder filled up
with files nobody meant to keep. None of that is in the diff. All of it is the
result.

Your job is to go find the real result, including the parts nobody wrote on
purpose, and then say what should change.

## Modes

**Default — propose and stop.** You produce the verdict and the plan. You do
not touch a file until Trenton says go.

**`auto` — carry it out.** `/rethink auto`, `/rethink --auto`, or a plain
"rethink this and just do it" runs the same analysis, prints the same verdict
and reasoning, then implements it without waiting. Report the proposal first
either way; auto changes whether you pause, never whether he sees the thinking.

Auto still stops for two things:

- **A `Scrap the premise` verdict.** Auto mode can change how a thing is built.
  Whether it should exist is his call, not yours.
- **Anything already gated.** Restarting live, deploying, publishing, posting to
  Discord, deleting. The standing rules outrank the flag.

Everything short of those, auto does.

## Step 1 — Name who experiences this

Before anything else, say out loud who the end user is and what surface they
meet the work through. Be concrete. Not "the user" — a player mid-match in
DomeBreak, a dispatcher checking a job board on a phone, a visitor who
landed on the site from a Discord link and has never seen it before.

The answer changes everything downstream. A player will spam the button. A staff
member will have the page open for six hours. A first-time visitor has none of
the context that makes the layout obvious.

If the work has more than one audience, name each one. The bug is usually in the
one you'd have forgotten.

## Step 2 — Get to the actual end result

**Never do this from the diff alone.** The diff is the description; you want the
thing itself.

Go look, by whatever means the project gives you:

- Run it. Launch the app, hit the endpoint, load the page, join the server.
- Look at it. Screenshot the screen, read the rendered page, watch the panel.
- Read the strings that ship — the actual message text, the actual button label,
  the actual error.
- Trace what it writes. Files, rows, config, logs, notifications.
- Follow it past the moment of success. What is on screen five seconds later?
  What is still there tomorrow?

If you cannot reach the running thing, say so in one line and reason
from the code — but say it, because a proposal built from reading alone is worth
less and he should know which one he's getting.

## Step 3 — Sweep for byproducts

This is the substance of the skill. Walk these deliberately; skipping to the
ones that look relevant is how the interesting one gets missed.

- **The unhappy path.** It fails, times out, gets bad input, loses connection.
  What does the person see? "Nothing" and "a raw stack trace" are both answers,
  and both are findings.
- **The second time.** Run it twice. Double-click the button. Re-run the
  command. Does it stack, duplicate, conflict, or quietly no-op?
- **Zero, one, and far too many.** Empty state, single item, ten thousand items.
  Empty is the one that ships broken most often, because nobody develops
  against it.
- **What it leaves behind.** Files, database rows, open handles, scheduled jobs,
  entries in a config nobody prunes, a notification that fires forever.
- **Who else it touches.** The other player on the server. The next person to
  open the panel. The teammate who pulls this branch. The version of himself
  who comes back to it in four months.
- **What the person has to hold.** Steps to remember, order that matters,
  a value to copy from one place to another, a thing that only works if you
  already knew about it. Every one of those is a defect with a workaround
  bolted on.
- **Time and interruption.** Slow network, offline, closed mid-way, killed
  process, browser refresh at the worst moment.
- **What it says versus what it does.** Copy that promises more, less, or other
  than reality. Hold every user-visible string to the standing rules: Title Case
  on labels, no context-derived copy, nothing that reads as the product
  explaining its own construction.
- **What it teaches.** Behavior trains expectations. If this one thing works
  differently to everything around it, the cost lands on every future
  interaction, not just this one.

## Step 4 — Ask whether the shape is right

Byproducts tell you what's wrong. This step asks whether the whole approach is
the problem.

- Is this fixing a symptom of something structural?
- Would the edge cases stop existing under a different design, rather than
  needing to be handled one by one? A pile of special cases is usually a shape
  problem wearing a costume.
- What is the version with fewer moving parts? Fewer states, fewer files, fewer
  things to keep in sync, fewer ways to be half-done.
- Does something in the project already solve this, and this is a second
  implementation of it?
- What would this look like if it had always worked this way, rather than having
  been arrived at?

## Step 5 — Deliver the verdict

Pick exactly one and lead with it:

| Verdict | Means |
|---|---|
| **Leave it** | The result is right. Nothing worth changing. |
| **Minor tweak** | A string, a guard, a default. Small and local. |
| **Major tweak** | Same approach, meaningful rework inside it. |
| **Different solution** | The approach is wrong. Here is the one that isn't. |
| **Scrap the premise** | The thing itself should not exist as scoped. |

**`Leave it` is a real verdict and you must be willing to use it.** A skill that
always finds a rewrite is noise, and he will stop trusting it. If the sweep came
back clean, say it came back clean.

**Size honestly in both directions.** Do not call a rewrite a tweak to make it
sound cheap, and do not inflate a string change into an architecture problem to
make the review look productive.

## Output

Keep it short. Every line either changes what he does next or is cut.

**Verdict** — one of the five, plus one sentence.

**What the person actually gets** — the real current experience, in two or three
lines. Ground it in what you observed, and name what you observed it with. "The
panel renders an empty grey box for ten seconds" beats "loading state may be
unclear."

**What's wrong with that** — the findings from the sweep, most consequential
first. Only real ones. A finding you can't tie to something you saw or traced
is a hunch, and hunches get labelled as hunches or dropped.

**The proposal** — what to build instead, concretely enough to act on. Say what
gets deleted, not only what gets added.

**Cost** — what it takes and what it risks breaking. One line.

Then: in default mode, stop and ask. In auto mode, build it and report what
landed.

## Rules

- **You are not extending the work, you are questioning it.** Being asked to
  rethink something is not permission to also add the feature you thought of.
  Ideas outside the verdict go in one line at the end for him to accept.
- **Every finding is grounded.** You ran it, read it, or traced it. Speculation
  is marked as speculation or left out.
- **His firsthand report is the spec.** If he says something felt wrong, it was
  wrong. Telemetry that disagrees is a lead about where the system is lying, not
  a reason to tell him he's mistaken. Find the mechanism.
- **No emojis, anywhere.** Not in the proposal, not in anything you build.
- **Never invent a problem to have something to say.** The empty result is
  allowed and is sometimes the most useful one.
