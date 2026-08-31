---
name: archive
description: Close a chat without leaving anything behind. Sweeps the work it still holds, harvests the correction or refusal nothing on this machine enforces, dispatches an unattended agent that builds that mechanism, then closes the chat. Use on /archive, or "archive this chat", "close this out", "wrap this up", "done with this one".
argument-hint: "[session id, or nothing for the chat this runs in]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Skill, mcp__ccd_session_mgmt__archive_session, mcp__ccd_session_mgmt__get_session, mcp__ccd_session_mgmt__list_sessions
---

# Archive

Archiving ends the one process that knows what the chat was doing. The
transcript survives, so nothing written down is lost. Everything not written
down goes with it, and it goes quietly: a worktree cut and never landed, a pull
request opened and never watched, a skill edited and never mirrored, and the
sentence somebody had to say twice because nothing catches it.

The second of those is the expensive one. A correction given inside a chat that
then closes is a correction that will be given again, at exactly the price it
cost the first time. That is the whole reason this skill starts a second agent
rather than writing a note: a note is a reminder to a model that can miss it,
and the mechanism is what does not get missed.

## The order

Sweep, harvest, hand off, close. In that order, because the archive call is
refused while the first three are outstanding.

That refusal is the skill. `guard-archive` runs as a `PreToolUse` row over
`mcp__ccd_session_mgmt__archive_session`, reads the target chat's own transcript,
and exits 2 while it is holding work or an unanswered lesson. Reaching for the
archive early does not skip a step, it produces a block naming the step.

A chat that cannot be read is refused rather than called clean. A session id off
by a character places no transcript, an absent transcript yields no rows, and no
rows are indistinguishable from a chat that closed with nothing outstanding.
Every verb here says so and exits 2 instead of answering.

## 1. Sweep

```bash
~/.intelligence/tools/archive.py check
```

Exit 1 while the chat is holding something. What it measures is scoped to the
footprint the transcript names: the directories it worked in, the repositories
behind them, the worktrees among those, the pull requests it opened, and the
config tree if it touched it. `--all` widens it to every checkout on the
machine, which is a different question and rarely the one being asked.

Time is deliberately not a factor here. Every other drift reading on this
machine waits a day before it calls a tree stranded, which is right for a tree
nobody is watching and wrong for a chat closing now: work made ten minutes ago
is precisely what is about to be abandoned.

Land what is landable through the normal flow. A worktree whose branch is done
ships to `develop` as a pull request with auto-merge; `/ship` carries it the
rest of the way. Where something cannot land, say where it goes instead. Do not
reach for `INTELLIGENCE_ALLOW_ARCHIVE=1` to get past a finding that is simply
inconvenient. That override exists for a misread, and a gate anybody can talk
their way around is a comment.

## 2. Harvest

```bash
~/.intelligence/tools/archive.py harvest
```

Two readings come out of one pass and they mean opposite things.

A **correction** is somebody supplying by hand what a mechanism should supply.
Repeated inside a single sitting, it is a rule with nothing behind it. That
wants a gate, and `/enforce` is the skill that builds one.

A **refusal** is a mechanism working. Repeated inside a single sitting, it is
not a missing gate, it is a missing fact: something the run needed to know
before it acted and could only learn by being refused. That wants context put
where the next run reads it, not another guard.

The reader takes refusals from all three shapes they arrive in, including the
denied tool call, which carries no prose and is invisible to the fortnight scan
that `lessons.py` runs. A correction counts only when a person actually typed
it. A hook and a finished agent both speak through the same kind of row and both
produce sentences that read exactly like somebody objecting.

Nothing found is a real answer. A chat where no correction repeated is a chat
that went well, and inventing a lesson to have one is worse than having none.

## 3. Hand off

```bash
~/.intelligence/tools/archive.py hand-off [<candidate id>]
```

Writes the brief and starts an unattended agent on it, carrying the opening
prompt. With no id it takes the top candidate, which is a correction where one
exists, since a rule nobody enforces outranks a rule that already fired.

The agent is a background session: `claude --bg`, no window, nothing to drive.
A hand-off that opened a chat somebody had to sit down at put a person back
into the one step whose whole purpose is taking the work off them, which is
why the deep link is gone rather than kept as an option.

Away from the Mac the same command travels `remote-access.py run mac`, and the
brief names that route so the agent reaches the checkouts itself instead of
stopping to ask. `INTELLIGENCE_HANDOFF_HOST=local|remote` settles the reading
where it comes out wrong.

Add `--print` to read the opening prompt without starting anything. Where the
agent cannot be started the brief path is reported, the run returns non-zero,
and the ledger records nothing -- so the gate goes on refusing rather than
releasing over an agent that is not running.

A hand-off releases the gate and settles nothing. The lesson belongs to the
agent that was started on it, which carries the brief, and the ledger holds it
open under that brief until that agent records what it became.

If the judgement is that nothing is owed, record that instead of pretending it
was built:

```bash
~/.intelligence/tools/archive.py settle <id> --as declined
```

`built` records a mechanism and has to name it. `context` records a line written
into `INTELLIGENCE.md` or a skill where no mechanism can reach. Marking is a
record of work done and nothing verifies it, so a candidate settled as `built`
with no gate behind it leaves the ledger saying the opposite of the truth.

## 4. Close

```bash
~/.intelligence/tools/archive.py close
```

A chat comes in one of two shapes and the close reads which one before it acts.

A chat the app knows carries a record, and `close` prints the name that record
holds. Archive it through `mcp__ccd_session_mgmt__archive_session`, passing
`self` for the chat this runs in, or the session id given as an argument. That
call prompts and nothing here stops it. The tool is marked
`requiresUserInteraction` by the server that serves it, which outranks
`bypassPermissions`, an entry in `permissions.allow`, and a `PreToolUse` hook
returning `allow`. One keystroke at the very end is the floor, and every step
before it is unattended.

A headless chat carries no record, so there is nothing for that call to reach
and `close` ends the process instead. That is the same ending arrived at
another way: the transcript survives both, and the transcript is everything
archiving keeps. Nothing is printed for somebody else to run and no second
session is asked to run it, because a close that has to be finished in another
window is the one step of this skill handed back to a person. A chat that fits
neither shape is refused rather than called closed.

The sweep and the harvest run again inside `close`. A headless ending makes no
tool call, so `guard-archive` never sees it, and an ending nothing refuses is
the gate switched off for whichever chats happen to take that branch.

Archiving another chat works the same way and reads that chat's transcript
rather than this one's. `list_sessions` finds the id where only a title is
known.

## Reporting

Four lines at most. What the sweep found and what happened to it, what the
harvest raised, what the agent was started on, and that the archive is
confirmed. If
the sweep found nothing and the harvest found nothing, say so in one line: that
is a chat that closed clean, and it is the ordinary case rather than a
suspicious one.
