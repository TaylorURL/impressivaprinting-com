---
name: intelligence
description: Whether this machine's setup is whole and everything it holds is published: naming, hooks, mirror, ledgers, routines, case suites, and whether the other machines answer. Use on /intelligence, or "check my setup", "is everything in sync", "is anything broken". Superset of /env-sync.
---

# intelligence

The setup is a tree of tools, skills and ledgers where each part answers for one
thing and nothing answers for the whole. A tree can be named correctly, pass its
own case suites, and still be a version behind what a cloud container installs.
The ledgers can be current on this machine and unpublished everywhere else. So
the health of the setup is a question no single tool holds the answer to, and
asking it one tool at a time is how a broken half goes unnoticed between the
halves that work.

`intelligence-check.py` is that question asked once.

```bash
~/.intelligence/tools/intelligence-check.py check   # probe everything, change nothing
~/.intelligence/tools/intelligence-check.py fix     # probe, repair, probe again
~/.intelligence/tools/intelligence-check.py list    # the checks, and what repairs each
```

`check` reads and writes nothing, so a run says what is true before anything
acts on it. `fix` runs the repair each failing check declares and then probes
again, which is what separates a check that was actually repaired from one that
was merely rerun. Both exit non-zero while a check that is not advisory is still
failing.

## What it asks

| Check | What a failure means |
| :--- | :--- |
| `naming` | A retired name is back in the tree, or a guard was dropped from `settings.json` |
| `config` | A cloud container started now would load something other than what this machine holds |
| `ledgers` | The pass ledgers or a day plan exist here and nowhere else |
| `hygiene` | The home layout, a README, editor config or a retired name is out of line |
| `routines` | A routine is running with no checked-in copy to rebuild it, or the reverse |
| `routine-health` | A routine is overdue against its own cadence, or the last run of one ended in a failure |
| `cases` | A tool no longer does what its cases say it does |
| `attribution` | The hooks that refuse an AI identity are not wired, or a hook is stored without its executable bit |
| `pipeline` | The Pi has stopped rebuilding the feed, so an empty ticket queue means nothing |
| `hosts` | A machine is not answering |
| `inbound` | The Pi cannot reach this machine, so nothing can be handed to the half of the work that only runs here |
| `sentinel` | The local watch is unwired or on a schedule other than the one it is meant to keep |

Eleven of the twelve routines are cron lines on the Pi; the twelfth is a launchd
agent on this machine. So `routine-health` reads the run records the Pi writes,
and `sentinel` answers for the one that fires here.

`pipeline`, `hosts` and `inbound` are advisory and never fail a run. A machine
that is asleep is not a fault in this tree, and reporting it as one trains the
run's output to be ignored.

A probe that cannot be taken is a failure carrying its reason, never a pass. An
absent tool fails its check rather than skipping it, because the tree is meant to
hold it and a skip reads exactly like a tree that is fine.

## The mirror is the only thing that reaches another machine

Nothing on a workstation reaches a cloud container. The setup arrives from
`bradley-t-t/intelligence`, which `cloud/bootstrap.sh` installs and
`scripts/cloud-refresh.sh` re-fetches inside the session. So publishing is not
the last step of the work, it is the step that makes the work exist anywhere
else, and `config` is the check that answers it.

The other machines pull the same mirror. Bringing them into step is the same
publish followed by a sync on each, which runs from here rather than by hand:

```bash
~/.intelligence/tools/remote-access.py hosts
~/.intelligence/tools/remote-access.py run mac -- ~/.intelligence/tools/config-sync.py sync
```

The Pi answers directly and holds keys onward to the Mac, the Windows desktop
and the VPS, so every machine is one hop further on from wherever this is
running.

## Several agents at once

Agents work this tree in parallel, so the tools that publish it take a hold for
the length of one reconcile and push. Two overlapping publishes would otherwise
stage each other's half-written trees, and one push would revert the other.

The hold is reentrant, so a tool inside it can call a tool that takes it, and it
is per-machine. The remote side is settled by git: a rejected push is resolved by
reconciling against the moved mirror and pushing again, never by forcing.

What still needs care is the work itself. Give concurrent agents disjoint files.
Two agents editing one skill is a race no lock reaches, because the loser's edit
is gone before either tool runs.

## A redirected state root does not publish

Redirecting `INTELLIGENCE_STATE_DIR` moves where a plan is written and nothing
else. The push it schedules still runs, and the carrier resolves the real mirror
on its own, so a fixture written under a throwaway root reaches the shared ledger
as that day's plan and displaces the plan already there.

A redirected root is therefore refused a push, unless
`INTELLIGENCE_PASS_STATE_REMOTE` is redirected with it, which is the round trip
the case suites drive against a repository of their own.

## Reading the result

"0 pushed" means there was nothing to send, not that something was sent. A held
file carries a credential and stays on this machine on purpose: the fix is to
move the value into the environment's own variable settings, never to force the
file across. `GH_TOKEN` and `GITHUB_TOKEN` are deliberately outside that and are
not a finding.
