---
name: enforce
description: Turn a rule into a mechanism that cannot be skipped: a hook that refuses, a check that fails, a tool that will not close. Use on /enforce, or "enforce this", "this keeps getting missed", "you did it again", "make it impossible to". Also on your own initiative the second time a rule is given.
argument-hint: "[the rule, in the user's words]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Skill
---

# Make the rule hold without anyone watching

A rule written down is a reminder to a model that can miss it. It gets missed.
That is not a discipline problem to be solved with a firmer sentence — it is
what writing a rule down does, every time, and the reason the same instruction
gets given three times.

So the deliverable of this skill is never a paragraph. It is a mechanism that
refuses. When it is finished, the wrong thing cannot happen quietly: it is
impossible, or it is repaired automatically, or the action is blocked with a
message naming what to do instead.

**Adding the rule to `INTELLIGENCE.md` is not doing this skill.** The documentation
comes after the mechanism, describing what was built. A run that ends with a
documented rule and no gate has failed, whatever the reply says.

## Pick the strongest form that fits

In this order. Take the first that can actually work; do not settle down the
list for convenience.

1. **Impossible.** Change the shape of the thing so the wrong state cannot be
   represented. A path that does not exist cannot be written to; a value read
   from one place cannot disagree with itself.
2. **Repaired automatically.** Detect and fix, with no one in the loop —
   `version-badge.py` rewrites the badge rather than refusing over it.
3. **Blocked.** A `PreToolUse` hook that refuses the action, a `Stop` hook that
   refuses to end the turn, a required CI check that refuses the merge.
4. **Reported.** Only where none of the above can reach: something that runs on
   a schedule and says loudly what is wrong. This is the weakest form and it is
   not enforcement; say so plainly when it is all that is available.

Where the rule is about what a session does, the four hook events `guard-hub.py`
dispatches are the instrument:

| The rule is about | Hook | Refuses by |
| :--- | :--- | :--- |
| An action being taken at all | `PreToolUse` | exit 2, with the reason on stderr |
| Work landing (`git commit`, `gh pr create`) | `PreToolUse(Bash)` | exit 2 |
| Something owed before the turn can end | `Stop` | exit 2 |
| State that must be recorded after an action | `PostToolUse` | writing the record itself |
| A repo's state at merge | `.github/workflows/ci.yml` job `check` | a non-zero step |

## Rules the gate itself has to keep

- **Read the source, not your memory of it.** Where the rule already lives in a
  file — a routine, a checklist, a skill — the gate parses that file and derives
  what it checks. A hardcoded copy drifts from the document it came from and
  then quietly enforces last month's rule.
- **A new rule cannot arrive unenforced.** When the gate is built from a
  document, an entry in that document with no gate declared fails the run.
  Otherwise adding a rule silently adds an unchecked one, which is where this
  started.
- **The attempt, not the outcome**, wherever the step can legitimately fail. A
  network that was down is a result to report; a step never taken is not.
- **No skip the model would reach for.** An escape hatch exists for the person,
  named in the file so they can find it, and is never something to set to get
  past a refusal. A gate you can talk your way around is a comment.
- **Prove it refuses.** Before landing, run the gate against a case that should
  fail and paste what it printed. A guard that has only ever been run against a
  passing case is untested, and the failure mode is silence.
- **Say what to do next.** The refusal names the command that fixes it. A block
  with no way forward gets disabled.

## Doing it

1. **Take the rule in their words.** Quote it in the gate's own documentation.
   The words are the specification; a paraphrase is how the wrong thing gets
   enforced.
2. **Find where it can be checked.** What signal exists at the moment the rule
   would be broken — a command about to run, a file's content, a transcript, a
   diff, an API response?
3. **Write the gate**, in `~/.intelligence/tools/` or `~/.intelligence/scripts/` for a rule
   about sessions, in the repo for a rule about that repo. Comments to the
   `writing-comments` standard.
4. **Wire it** as a row in `guard-hub.py`'s registry, whose precondition is a
   superset of the guard's own first gate, or into `ci.yml`, or wherever else it
   fires from. `session-init.py` owns `settings.json` and folds a hook added
   there by hand back out, so a guard wired that way survives one session.
5. **Test both directions**: it refuses the violation, and it stays out of the
   way of the ordinary case. Both, every time — a gate with a false positive
   gets switched off within a day. `state/guard-log.jsonl` carries one row per
   guard that ran, so what a guard has actually been doing is a reading rather
   than a memory.
6. **Then document it**, in `INTELLIGENCE.md` or the relevant skill, as a description
   of the mechanism rather than as the rule itself.
7. **Land it** through the normal PR flow, and mirror it into the repos that
   carry their own copy.

## Reporting

Say what refuses what, in one line, and show the refusal you triggered on
purpose. Not "this is now enforced" — the thing it printed when it blocked.
