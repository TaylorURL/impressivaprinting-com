#!/usr/bin/env python3
"""Cases the routine registry has to get right.

The registry is worth what it refuses. A schedule that does not parse never
fires and says nothing about it; a phase with no gate is a phase nothing checks;
a routine file present in the tree and absent from the registry is one nothing
could rebuild; a shared program held here but no longer the one the machine
runs is a backup in name only; a routine carrying neither a schedule nor a webhook is one
nothing starts. Each of those sits here beside the tree that stays valid, so the
check cannot quietly narrow. The rotation is held to the one property that makes
it a rotation: a project just swept goes to the back, and a project never swept
goes first.

  routine-sync-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "routine-sync.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TASK = """# Phase 0 -- Read the thing
<!-- enforce run: some-tool(\\.py)?\\s+read -->

Read it.

# Phase 1 -- Say what it held
<!-- enforce report: finding -->

Say it.
"""

UNGATED = "# Phase 0 -- Read the thing\n\nNo marker anywhere.\n"


HOOK = {"source": "github", "hook_type": "app", "scope_id": "o/one",
        "events": ["issues.opened"]}


def config(cron, prompt_file, sources=("https://github.com/o/one",),
           webhook=None):
    body = {
        "name": "Test",
        "enabled": True,
        "prompt_file": prompt_file,
        "mcp_connections": [{"name": "Stripe"}],
        "job_config": {"ccr": {"session_context": {
            "sources": [{"git_repository": {"url": u}} for u in sources]}}},
    }
    if cron:
        body["cron_expression"] = cron
    if webhook:
        body["webhook"] = webhook
    return body


PINNED = "claude-opus-4-6"


def tree(tmp, routines, tasks=None, configs=None, shared=None):
    """A checkout holding just enough for the registry to be read."""
    root = Path(tmp)
    root.mkdir(parents=True, exist_ok=True)
    (root / "routines").mkdir(exist_ok=True)
    (root / "routine").mkdir(exist_ok=True)
    runner = root / "routines" / "bin" / "routine-run.sh"
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text("#!/bin/sh\nMODEL=${ROUTINE_MODEL:-%s}\n" % PINNED)
    body = {"routines": routines}
    declared = list(shared) if shared is not None else []
    declared.append({
        "path": "routines/bin/routine-run.sh",
        "host": "pi",
        "installed": "/home/sunday/bin/routine-run.sh",
        "does": "Hands a registry entry's prompt to a headless turn on the pinned model",
    })
    body["shared"] = declared
    (root / "routines" / "registry.json").write_text(json.dumps(body))
    for name, text in (tasks or {}).items():
        (root / "routine" / name).write_text(text)
    for name, body in (configs or {}).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body))
    return root


def entry(rid="one", cron="0 10 * * *", task="one.md", webhook=None):
    out = {
        "id": rid, "cadence": "daily", "host": "pi", "schedule": cron,
        "config": "routines/daily/%s.json" % rid,
        "prompt": "routines/daily/%s.prompt.md" % rid,
        "task": "routine/%s" % task,
        "does": "a thing",
    }
    if webhook:
        out["webhook"] = webhook
    return out


def built(tmp, entries, tasks, crons=None, shared=None):
    configs = {}
    for e in entries:
        crons = crons or {}
        configs[e["config"]] = config(crons.get(e["id"], e["schedule"]),
                                      Path(e["prompt"]).name,
                                      webhook=e.get("webhook"))
    root = tree(tmp, entries, tasks, configs, shared)
    for e in entries:
        (root / e["prompt"]).write_text("orientation\n")
    return root


def main():
    mod = load()

    # Every schedule the registry actually carries parses, and the shapes that
    # would silently never fire do not.
    for good in ("0 10 * * *", "23 * * * *", "0 15 * * 0", "0 16 1 * *",
                 "*/5 * * * *", "0 9-17 * * 1-5", "0 0,12 1,15 * *"):
        check("cron accepts %r" % good, mod.valid_cron(good), True)
    for bad in ("0 10 * *", "60 * * * *", "0 24 * * *", "0 0 32 * *",
                "0 0 * 13 *", "x * * * *", "0 17-9 * * *", "*/0 * * * *", ""):
        check("cron refuses %r" % bad, mod.valid_cron(bad), False)

    # A heading quoted inside a fence is display, not a declaration.
    check("gates_of counts phases", len(mod.gates_of(TASK)), 2)
    fenced = TASK + "```\n# Phase 9 -- Quoted only\n```\n"
    check("fenced phase skipped", len(mod.gates_of(fenced)), 2)
    check("gates_of keeps both gates",
          [len(g) for _, g in mod.gates_of(TASK)], [1, 1])

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK})
        check("a complete registry is clean", mod.check(root), [])

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": UNGATED})
        problems = mod.check(root)
        check("an ungated phase is caught",
              any("declares no enforce marker" in p for p in problems), True)

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {})
        check("a missing task file is caught",
              any("task file is missing" in p for p in mod.check(root)), True)

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry("one"), entry("two", task="two.md")],
                     {"one.md": TASK, "two.md": TASK})
        check("two routines in one minute are caught",
              any("same minute" in p for p in mod.check(root)), True)

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK},
                     crons={"one": "0 11 * * *"})
        check("a config disagreeing with the registry is caught",
              any("config says" in p for p in mod.check(root)), True)

    # A routine fires on a schedule, on a webhook, or on a gate, and the
    # registry names whichever one it is.
    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry(cron=None, webhook=HOOK)], {"one.md": TASK})
        check("a webhook routine with no schedule is clean", mod.check(root), [])

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry(cron=None)], {"one.md": TASK})
        check("a routine nothing fires is caught",
              any("nothing fires it" in p for p in mod.check(root)), True)

    with tempfile.TemporaryDirectory() as tmp:
        gated = dict(entry(cron=None), gate="*/10 * * * * tick.sh")
        root = built(tmp, [gated], {"one.md": TASK})
        check("a gated routine with no schedule is clean", mod.check(root), [])
        check("a gate is what list says starts it",
              mod.fired_by(gated), "*/10 * * * * tick.sh")

    # A gate polls on a clock it shares with everything else, and the turn it
    # might start belongs to no minute. Holding it against the scheduled runs
    # would collide it with every one of them.
    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [dict(entry("one", cron=None),
                                gate="*/10 * * * * tick.sh"),
                           entry("two", cron="0 10 * * *", task="two.md")],
                     {"one.md": TASK, "two.md": TASK})
        check("a gate never collides with a schedule",
              [p for p in mod.check(root) if "same minute" in p], [])

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry(cron=None, webhook=HOOK)], {"one.md": TASK})
        moved = dict(HOOK, events=["issues.closed"])
        path = root / "routines" / "daily" / "one.json"
        body = json.loads(path.read_text())
        body["webhook"] = moved
        path.write_text(json.dumps(body))
        check("a webhook the config spells differently is caught",
              any("disagree about the webhook" in p for p in mod.check(root)),
              True)

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK})
        path = root / "routines" / "daily" / "one.json"
        body = json.loads(path.read_text())
        body["webhook"] = HOOK
        path.write_text(json.dumps(body))
        check("a webhook the registry does not name is caught",
              any("does not name" in p for p in mod.check(root)), True)

    # Two schedules collide on the minutes they share, which a comparison of
    # the expressions does not see.
    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry("one", cron="47 * * * *"),
                           entry("two", cron="47 */8 * * *", task="two.md")],
                     {"one.md": TASK, "two.md": TASK})
        check("schedules that overlap are caught",
              any("same minute" in p for p in mod.check(root)), True)

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry("one", cron="47 1 * * *"),
                           entry("two", cron="47 */8 * * *", task="two.md")],
                     {"one.md": TASK, "two.md": TASK})
        check("schedules sharing a minute and no hour are not",
              [p for p in mod.check(root) if "same minute" in p], [])

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK})
        (root / "routine" / "stray.md").write_text(TASK)
        check("a task file no entry names is caught",
              any("no registry entry names" in p for p in mod.check(root)), True)

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK})
        (root / "routines" / "daily" / "extra.json").write_text("{}")
        check("an unclaimed config is caught",
              any("in no registry entry" in p for p in mod.check(root)), True)

    # A live definition that has moved is the whole reason the copies exist.
    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK})
        live = Path(tmp) / "live.json"
        moved = config("0 11 * * *", "one.prompt.md")
        live.write_text(json.dumps(moved))
        lines = mod.diff(root, "one", live)
        check("diff sees a moved schedule",
              any("cron_expression differs" in l for l in lines), True)
        live.write_text(json.dumps(config("0 10 * * *", "one.prompt.md",
                                          ("https://github.com/o/two",))))
        lines = mod.diff(root, "one", live)
        check("diff names a repository only live",
              any("only live" in l and "two" in l for l in lines), True)
        live.write_text(json.dumps(config("0 10 * * *", "one.prompt.md")))
        check("diff is silent on an identical copy",
              mod.diff(root, "one", live), [])
        check("diff refuses an unknown id",
              mod.diff(root, "nope", live), ["no routine 'nope' in the registry"])

    # The live side. Each of these has actually happened here, and none of them
    # announces itself: the routine keeps its schedule and does nothing.
    with tempfile.TemporaryDirectory() as tmp:
        entries = [dict(entry("one"), trigger_id="trig_one", cadence="daily")]
        root = built(tmp, entries, {"one.md": TASK})

        def live(**over):
            base = {
                "id": "trig_one", "name": "One", "enabled": True,
                "cron_expression": "0 10 * * *",
                "derived_state": {"prompt": "do the thing"},
                "last_fired_at": mod.datetime.now(mod.timezone.utc).isoformat(),
                "next_run_at": "2030-01-01T10:00:00Z",
                "last_run": {"status": "ROUTINE_RUN_STATUS_SUCCEEDED"},
                "job_config": {"ccr": {"session_context": {"sources": [
                    {"git_repository": {"url": "https://github.com/o/one"}}]}}},
            }
            base.update(over)
            return {"data": [base]}

        check("a healthy routine reports nothing", mod.health(root, live()), [])
        check("an empty prompt is caught",
              any("empty prompt" in p for p in
                  mod.health(root, live(derived_state={"prompt": "   "}))), True)
        check("no repository is caught",
              any("no repository" in p for p in mod.health(root, live(
                  job_config={"ccr": {"session_context": {"sources": []}}}))), True)
        check("disabled is caught",
              any("is disabled" in p for p in mod.health(root, live(enabled=False))), True)
        check("a failed last run is caught",
              any("last run ended" in p for p in mod.health(root, live(
                  last_run={"status": "ROUTINE_RUN_STATUS_FAILED"}))), True)
        check("never fired is caught",
              any("never fired" in p for p in mod.health(root, live(last_fired_at=""))), True)
        check("no next run is caught",
              any("no next run" in p for p in mod.health(root, live(next_run_at=""))), True)
        stale = (mod.datetime.now(mod.timezone.utc)
                 - mod.timedelta(hours=48)).isoformat()
        check("a daily routine silent two days is caught",
              any("past the 30" in p for p in mod.health(root, live(last_fired_at=stale))), True)
        hourly = built(tmp + "/h",
                       [dict(entry("one", cron="7 * * * *"),
                             trigger_id="trig_one", cadence="continuous")],
                       {"one.md": TASK})
        five = (mod.datetime.now(mod.timezone.utc)
                - mod.timedelta(hours=5)).isoformat()
        check("an hourly routine is judged on its own clock",
              any("past the 3" in p for p in mod.health(
                  hourly, live(cron_expression="7 * * * *",
                               last_fired_at=five))), True)
        # The same silence against an eight-hourly schedule is a run that has
        # not come round yet, and the cadence the two share cannot tell them
        # apart.
        eight = built(tmp + "/e",
                      [dict(entry("one", cron="47 */8 * * *"),
                            trigger_id="trig_one", cadence="continuous")],
                      {"one.md": TASK})
        check("an eight-hourly routine is given its own period",
              [p for p in mod.health(eight, live(cron_expression="47 */8 * * *",
                                                 last_fired_at=five))], [])
        twelve = (mod.datetime.now(mod.timezone.utc)
                  - mod.timedelta(hours=12)).isoformat()
        check("and is still caught once it has stopped",
              any("past the 10" in p for p in mod.health(
                  eight, live(cron_expression="47 */8 * * *",
                              last_fired_at=twelve))), True)

        # A routine fired by a webhook has no interval to be late against.
        hooked = built(tmp + "/w",
                       [dict(entry("one", cron=None, webhook=HOOK),
                             trigger_id="trig_one", cadence="continuous")],
                       {"one.md": TASK})
        quiet = (mod.datetime.now(mod.timezone.utc)
                 - mod.timedelta(hours=90)).isoformat()
        check("a quiet webhook routine is not stale",
              mod.health(hooked, live(cron_expression="", next_run_at="",
                                      last_fired_at=quiet)), [])
        check("and an emptied repository list is still caught",
              any("no repository" in p for p in mod.health(
                  hooked, live(cron_expression="", next_run_at="",
                               job_config={"ccr": {"session_context":
                                                   {"sources": []}}}))), True)

        # A routine running live that nothing here could rebuild.
        stranger = live()
        stranger["data"][0].update(id="trig_two", name="Two")
        check("an unregistered routine is caught",
              any("no registry entry names it" in p
                  for p in mod.health(root, stranger)), True)

        # An enabled trigger with no schedule is shaped like a spent one-off
        # and is not one: a routine fired by a webhook carries no schedule
        # either, and counting it leaves the queue it works unwatched.
        hookless = live()
        hookless["data"][0].update(id="trig_two", name="Two",
                                   cron_expression="")
        check("an enabled webhook routine nothing names is caught",
              any("no registry entry names it" in p
                  for p in mod.health(root, hookless)), True)

        # A spent one-off webhook is counted, never judged as a routine.
        one_off = {"data": [live()["data"][0], {
            "id": "trig_off", "name": "Unblock something", "enabled": False}]}
        problems = mod.health(root, one_off)
        check("a spent one-off is counted not judged",
              [p for p in problems if "one-off" in p],
              ["(1 spent one-off trigger(s) ignored)"])
        check("and nothing else is reported about it",
              any("Unblock something" in p for p in problems), False)

        # A registry entry the API has never heard of.
        check("a recorded routine the API lost is caught",
              any("returned nothing for it" in p
                  for p in mod.health(root, {"data": []})), True)

    # The rotation: never swept goes first, and a sweep moves a project back.
    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [dict(entry("maintenance", task="one.md"))],
                     {"one.md": TASK})
        (root / "routines/daily/maintenance.json").write_text(json.dumps(
            config("0 10 * * *", "maintenance.prompt.md",
                   ("https://github.com/o/alpha", "https://github.com/o/beta"))))
        check("projects come from the routine's own sources",
              mod.projects(root), ["alpha", "beta"])
        check("never swept comes first", mod.rotation_next(root, 2),
              ["alpha", "beta"])
        check("mark records", mod.rotation_mark(root, "alpha", ["seo"],
                                                today="2026-01-01"), None)
        check("a swept project goes to the back",
              mod.rotation_next(root, 2), ["beta", "alpha"])
        check("mark refuses an unknown project",
              mod.rotation_mark(root, "gamma", ["seo"]) is not None, True)
        check("mark refuses an unknown checklist",
              mod.rotation_mark(root, "beta", ["vibes"]) is not None, True)
        state = json.loads((root / "routines/rotation.json").read_text())
        check("the mark carries what closed",
              state["swept"]["alpha"]["checklists"], ["seo"])


    # One line in the runner decides what every scheduled turn is judged by.
    # A config carrying a model of its own overrides it for that routine, and
    # the two saying different things is the state nothing else reads as wrong.
    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK})
        cfg = json.loads((root / "routines/daily/one.json").read_text())
        cfg["job_config"] = {"ccr": {"session_context": {"model": "elsewhere"}}}
        (root / "routines/daily/one.json").write_text(json.dumps(cfg))
        check("a config running a model of its own is caught",
              any("the runner pins" in p for p in mod.check(root)), True)

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK})
        cfg = json.loads((root / "routines/daily/one.json").read_text())
        cfg["job_config"] = {"ccr": {"session_context": {"model": PINNED}}}
        (root / "routines/daily/one.json").write_text(json.dumps(cfg))
        check("a config naming the pinned model is clean", mod.check(root), [])

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK})
        (root / "routines/bin/routine-run.sh").unlink()
        check("a tree whose runner names no model is caught",
              any("nothing pins the routines" in p for p in mod.check(root)),
              True)

    # The programs every routine runs through belong to no single entry, so
    # without a shared block they read as files nothing accounts for.
    def sh(path="routines/bin/run.sh", installed="/home/sunday/bin/run.sh",
           host="pi"):
        return {"path": path, "host": host, "installed": installed,
                "does": "runs a routine"}

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK}, shared=[sh()])
        (root / "routines/bin").mkdir(parents=True, exist_ok=True)
        (root / "routines/bin/run.sh").write_text("#!/bin/sh\ntrue\n")
        check("a declared shared program is not an orphan", mod.check(root), [])

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK})
        (root / "routines/bin").mkdir(parents=True, exist_ok=True)
        (root / "routines/bin/run.sh").write_text("#!/bin/sh\ntrue\n")
        check("an undeclared program is still an orphan",
              any("in no registry entry" in p for p in mod.check(root)), True)

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK}, shared=[sh()])
        check("a shared program missing from the tree is caught",
              any("is not in the tree" in p for p in mod.check(root)), True)

    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK},
                     shared=[sh(installed=None)])
        (root / "routines/bin").mkdir(parents=True, exist_ok=True)
        (root / "routines/bin/run.sh").write_text("#!/bin/sh\ntrue\n")
        check("a shared program with no install path is caught",
              any("names no install path" in p for p in mod.check(root)), True)

    # The two ways a held copy stops being a backup are both invisible from
    # this side: the machine's copy edited in place, and a program running
    # there that was never committed.
    with tempfile.TemporaryDirectory() as tmp:
        root = built(tmp, [entry()], {"one.md": TASK}, shared=[sh()])
        (root / "routines/bin").mkdir(parents=True, exist_ok=True)
        (root / "routines/bin/run.sh").write_text("#!/bin/sh\ntrue\n")
        here = mod.digest("#!/bin/sh\ntrue\n")

        mod.installed_digests = lambda h, d: ({"/home/sunday/bin/run.sh": here}, 0)
        check("a matching machine is clean", mod.mirrored(root, [sh()]), [])

        mod.installed_digests = lambda h, d: ({"/home/sunday/bin/run.sh": "0" * 64}, 0)
        check("a machine copy edited in place is caught",
              any("is not the copy held here" in p
                  for p in mod.mirrored(root, [sh()])), True)

        mod.installed_digests = lambda h, d: ({}, 0)
        check("a program held here and not installed is caught",
              any("is not installed on the pi" in p
                  for p in mod.mirrored(root, [sh()])), True)

        mod.installed_digests = lambda h, d: (
            {"/home/sunday/bin/run.sh": here,
             "/home/sunday/bin/stray.sh": "1" * 64}, 0)
        check("a program running there and committed nowhere is caught",
              any("no shared entry declares" in p
                  for p in mod.mirrored(root, [sh()])), True)

        mod.installed_digests = lambda h, d: ({}, 255)
        check("an unreachable machine reports unchecked, never clean",
              any("could not be reached" in p
                  for p in mod.mirrored(root, [sh()])), True)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
