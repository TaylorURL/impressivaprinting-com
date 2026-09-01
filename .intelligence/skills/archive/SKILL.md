---
name: archive
description: Close a chat without leaving anything behind. Finishes what the opening message asked for and nothing carried out, runs the clean and copywriting passes over the diff the chat made, sweeps the work it still holds, harvests the correction, refusal or collision nothing on this machine settles, dispatches an unattended agent that answers the top finding, then closes the chat. Use on /archive, or "archive this chat", "close this out", "wrap this up", "done with this one".
argument-hint: "[session id, or nothing for the chat this runs in]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Skill, mcp__ccd_session_mgmt__archive_session, mcp__ccd_session_mgmt__get_session, mcp__ccd_session_mgmt__list_sessions
---

# Archive

Archiving ends the one process that knows what the chat was doing. The
transcript survives, so nothing written down is lost. Everything not written
down goes with it, and it goes quietly: an ask from the opening message that
nothing ever carried out, a file changed and never passed over, a worktree cut
and never landed, a pull request opened and never watched, a skill edited and
never mirrored, and the sentence somebody had to say twice because nothing
catches it.

The first of those is the one that costs the person who typed the message. A
message asking for three things gets two of them, the reply describes the two,
and the third is gone unless somebody re-reads the message they already sent.
The whole cost of that lands on one side of the conversation: the run finished,
the reply looked complete, and the only person who can tell it was not is the
one who has to go back and ask again. That is friction with a single source and
it is arithmetic to detect, so it is detected here rather than left to be
noticed.

The last is the one that costs the next chat. A correction given inside a chat
that then closes is a correction that will be given again, at exactly the price
it cost the first time. Worse is the argument between two rules: the run that
walks into one settles it in the moment, on its own, and the settlement closes
with the chat, so the next run starts the same argument from the same standing
start. That is the whole reason this skill starts a second agent rather than
writing a note: a note is a reminder to a model that can miss it, and the
mechanism is what does not get missed.

## The order

Finish, polish, sweep, harvest, hand off, close. In that order, because the
archive call is refused while any of the first four is outstanding.

That refusal is the skill. `guard-archive` runs as a `PreToolUse` row over
`mcp__ccd_session_mgmt__archive_session`, reads the target chat's own transcript,
and exits 2 while it is holding work, an unpassed diff, a dropped ask or an
unanswered lesson. Reaching for the archive early does not skip a step, it
produces a block naming the step.

Nothing in this run is offered back as a choice. A finding is acted on, and the
one keystroke at the very end is the only thing anybody is asked for. A question
put here is a question about work that could have been done in the time it took
to ask it.

A chat that cannot be read is refused rather than called clean. A session id off
by a character places no transcript, an absent transcript yields no rows, and no
rows are indistinguishable from a chat that closed with nothing outstanding.
Every verb here says so and exits 2 instead of answering.

## 1. Finish

```bash
~/.intelligence/tools/archive.py finish
```

What was asked for and never done. Exit 1 while anything is unanswered.

Two readings, catching the same failure from opposite ends. The opening message
is taken apart into the separate things it asked for and each is checked against
everything the run did afterwards -- every reply, every path, every command,
every file written. An ask whose words never surface again was read and not
carried out. The second reading is somebody having said so: a later turn asking
again for something already asked for, which is the same finding with a person's
own words as the evidence.

Three things hold before an absence counts. The message has to carry more than
one ask, since a message asking for one thing has no part it could have lost.
The run has to have done something, since a chat that touched nothing leaves no
trace of what it carried out. And at least one ask has to have landed, because a
message where none of the words came back is a reading that cannot see the work
rather than a run that did none of it. What is left is the shape this is about:
some of it done, and the rest quietly dropped.

Do the work. Not a summary of it, not a plan for it, not a question about which
half to start with -- the thing that was asked for, including the half that was
implied rather than spelled out. Then record it:

```bash
~/.intelligence/tools/archive.py settle <id> --as done --note "what was finished"
```

Where it was asked and answered and the reading is simply wrong, `--as declined`
records that. A decline that is really a shrug is the same finding arriving in
the next chat with the work still not done.

## 2. Polish

```bash
~/.intelligence/tools/archive.py polish
~/.intelligence/tools/archive.py polish --files
```

Every file the chat changed goes past `/clean`, and the half of it carrying
words a person reads goes past `/copywriting` as well. Exit 1 while any of it is
outstanding, every time, with no judgement about whether this particular diff
deserved it.

`--files` prints the diff as paths, one per line, which is what both skills are
scoped to. The scope is the change set and never the repository: a pass over a
whole project at the moment a chat closes is a pass nobody runs, and a gate
demanding one is a gate somebody switches off inside a week.

The set is read from three places, because no one of them is complete. The calls
that wrote files name what a chat that already landed its work no longer has a
diff for. The working tree carries what a heredoc wrote without naming. And half
the trees on this machine answer to no repository at all, so a file there counts
on the clock: one that moved after the chat first named it moved while the chat
had it in hand, and one whose last change predates the first mention of it was
somebody else's work however recent.
What enters the set stays in it for the rest of the chat: the diff empties the
moment a branch lands or the mirror takes the file, and neither of those is a
pass.

Run `/clean` over the paths and `/copywriting` over the ones a person reads,
then record it:

```bash
~/.intelligence/tools/archive.py polish --mark
```

The mark is held against what each file contains rather than against its name,
so a file edited after its pass reopens on its own rather than carrying a pass
that covered work done afterwards. The copy half is checked rather than marked:
`writing-pass.py` reads the current text on every run, `--mark` refuses while
anything is still flagged, and fixing the prose is the only thing that opens it.

## 3. Sweep

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

## 4. Harvest

```bash
~/.intelligence/tools/archive.py harvest
```

Five readings come out of one pass and they answer different questions. The
first is the dropped ask above, which leads them because it is the only one
about whether the work was done at all.

A **correction** is somebody supplying by hand what a mechanism should supply.
Repeated inside a single sitting, it is a rule with nothing behind it. That
wants a gate, and `/enforce` is the skill that builds one.

A **refusal** is a mechanism working. Repeated inside a single sitting, it is
not a missing gate, it is a missing fact: something the run needed to know
before it acted and could only learn by being refused. That wants context put
where the next run reads it, not another guard.

A **collision** is two mechanisms refusing one reply on different grounds. Both
gates exist, both fired, and satisfying the first is what broke the second. It
needs no repeat: one occurrence already carries both demands in full, along with
every draft that failed to meet them, and waiting for a second is waiting for
another run to lose the same hour picking a side. What it wants is neither a
gate nor a fact. It wants a decision -- which of the two yields where they meet
-- written where both are read.

Nothing about a collision is settled by loosening one of the gates. The run that
met it already had that option and the entire cost of the collision is that it
took one quietly, in a chat that then closed. A gate that gives way to whoever
it inconveniences is a comment. Where one of the two already carries an override
for exactly that reading, naming it is the whole answer.

A **recurrence** is one ground that refused runs in three separate chats, none
of which repeated it often enough to raise it alone. It is assembled rather than
read, out of what the close keeps.

The reader takes refusals from all three shapes they arrive in, including the
denied tool call, which carries no prose and is invisible to the fortnight scan
that `lessons.py` runs. One firing reaches a transcript more than once -- as
feedback on the turn it stopped, and again in the summary of the hooks that ran
-- and counts once, keyed on the sentence it opens with, which is the part every
copy of it survives with. A refusal inside a subagent counts, because it is the
same machine saying no; a correction there does not, because nobody types in a
sidechain. A correction counts only when a person actually typed it. A hook and
a finished agent both speak through the same kind of row and both produce
sentences that read exactly like somebody objecting.

Nothing found is a real answer. A chat where no correction repeated is a chat
that went well, and inventing a lesson to have one is worse than having none.

### What the close keeps

A guard that refuses once, is obeyed, and never fires again raises nothing. That
is the ordinary case and the reading is right to stay quiet about it.

What is not right is that the two drafts either side of it go with the chat. The
one it turned down and the one that stood in its place are, together, the
clearest statement anywhere on this machine of what the guard actually wanted:
the refusal says what was wrong, and only the second draft says what right looked
like. That is the half a lesson closes on, and it was being read once and
dropped.

Both are held now against the ground that refused them, in `evidence.json`
beside the ledger, and a brief raised on that ground carries the pair. Three
chats meeting the same ground raises it as a recurrence. Nobody was present for
all three, which is the whole point of keeping them: a wall that costs one draft
per chat is invisible from inside any single chat and plain from above them.

## 5. Hand off

```bash
~/.intelligence/tools/archive.py hand-off [<candidate id>]
```

Writes the brief and starts an unattended agent on it, carrying the opening
prompt. With no id it takes the top candidate. The order is omission, collision,
correction, recurrence, refusal: work somebody asked for and never got outranks
two rules that contradict each other, which outranks a rule nobody enforces,
which outranks a rule that already fired and will fire again.

An omission reaching the hand-off is a fallback rather than the route. It is
answered in step 1, in this chat, because the person who asked for it is here
and the work is in front of the run that dropped it. It travels only where it
cannot be done from here at all.

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

`built` records a mechanism and has to name it. `done` records work that was
asked for and has now been carried out. `context` records a line written into
`INTELLIGENCE.md` or a skill where no mechanism can reach. A collision settles
as `context` too: what it produces is a line saying which rule yields, and a
third gate stacked on two that already fired is one more thing to collide with.
Marking is a record of work done and nothing verifies it, so a candidate settled
as `built` with no gate behind it leaves the ledger saying the opposite of the
truth.

## 6. Close

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

Every earlier step runs again inside `close`. A headless ending makes no tool
call, so `guard-archive` never sees it, and an ending nothing refuses is the
gate switched off for whichever chats happen to take that branch.

Archiving another chat works the same way and reads that chat's transcript
rather than this one's. `list_sessions` finds the id where only a title is
known.

## Reporting

Five lines at most. What was finished, what the passes covered, what the sweep
found and what happened to it, what the harvest raised, what the agent was
started on, and that the archive is confirmed. Where a step found nothing, it
takes no line. If nothing was dropped and nothing was held and nothing was
harvested, say so in one line: that is a chat that closed clean, and it is the
ordinary case rather than a suspicious one.
