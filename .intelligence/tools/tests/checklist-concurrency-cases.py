#!/usr/bin/env python3
"""Cases the checklist engines have to get right when more than one runs at once.

Agents spawned from one session inherit its id, so the session alone names a
fleet rather than a worker. Two things follow, and both have cost work here: the
run pointer keyed on the session alone is one file every worker writes, and a
probe written to a documented path is one file every worker writes. Each ends
with a worker reading another's state as its own.

The contract pinned here: a pointer carries the working tree it belongs to, the
shared pointer is claimed only while nothing else holds it, a run recorded under
the older unscoped name still resolves, a run governs only the directory it owns
whichever pointer reached it, and a probe refuses a path a recent reading holds.

  checklist-concurrency-cases.py     run them
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KINDS = ("seo", "perf", "stack", "design", "db", "google")
def installed_or_checkout(name):
    """The config tree's copy of a directory, or the checkout's own.

    A case file runs from the tree it was checked out into as often as from an
    installed config, and CI has neither an installed config nor a home to put
    one in.
    """
    installed = Path.home() / ".intelligence" / name
    if installed.is_dir():
        return installed
    return Path(__file__).resolve().parents[2] / name


CHECKLISTS = Path(os.environ.get("INTELLIGENCE_TEST_CHECKLISTS")
                  or installed_or_checkout("checklists"))

ANSWERS_FOR = [
    "checklists/seo/bin/seo-pass.py",
    "checklists/perf/bin/perf-pass.py",
    "checklists/stack/bin/stack-pass.py",
    "checklists/design/bin/design-pass.py",
    "checklists/db/bin/db-pass.py",
    "checklists/google/bin/google-pass.py",
]

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def engine(kind, state):
    """One engine, with its state root pointed at a fixture."""
    os.environ["INTELLIGENCE_STATE_DIR"] = state
    path = CHECKLISTS / kind / "bin" / ("%s-pass.py" % kind)
    return load(path, "engine_%s_%d" % (kind, time.time_ns()))


def a_tree(root, name):
    """A directory that reads as a working tree."""
    tree = Path(root) / name
    (tree / ".git").mkdir(parents=True)
    return tree


def a_repo(root, name):
    """A directory git answers for."""
    repo = Path(root) / name
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
    return repo


def a_run(kind, run_id, tree):
    """A run of this engine's own shape, open over one tree.

    Each engine names the tree it acts on under a different key and reads its
    gates from another, and a guard handed a run it cannot read answers as though
    nothing were open, which passes a scope case for the wrong reason.
    """
    run = {"id": run_id, "session": "S", "opened": "2026-08-30 12:00:00Z",
           "kind": "web-ui"}
    if kind == "db":
        run.update({"target": str(tree), "order": [], "answers": {}, "verdicts": {}})
    elif kind == "google":
        run.update({"registry": str(tree), "sites": {}, "order": ["X"],
                    "results": {"X": {"status": "open"}}})
    else:
        run.update({"repo": str(tree), "targets": [str(tree)], "order": ["X"],
                    "results": {"X": {"status": "open"}}})
    return run


def pointer_cases(kind):
    with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as work:
        mod = engine(kind, state)
        here = Path.cwd()
        one, two = a_tree(work, "one"), a_tree(work, "two")
        try:
            os.chdir(one)
            first = mod.session_pointer("S").name
            os.chdir(two)
            second = mod.session_pointer("S").name
            os.chdir(work)
            outside = mod.session_pointer("S").name
        finally:
            os.chdir(here)
        check("%s: two trees take two pointers" % kind, first == second, False)
        check("%s: a tree is named in the pointer" % kind,
              first.startswith("current-S-") and first.endswith(".json"), True)
        check("%s: outside a tree the plain name stands" % kind, outside, "current-S.json")
        check("%s: the plain name is the legacy one" % kind,
              mod.legacy_pointer("S").name, "current-S.json")


def legacy_cases(kind):
    """A run recorded under the unscoped name still resolves."""
    with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as work:
        mod = engine(kind, state)
        runs = Path(state) / ("%s-runs" % kind)
        runs.mkdir(parents=True, exist_ok=True)
        run = {"id": "20260829-000009", "session": "S", "order": [], "results": {}}
        (runs / "20260829-000009.json").write_text(json.dumps(run))
        (runs / "current-S.json").write_text(json.dumps({"id": "20260829-000009"}))
        here = Path.cwd()
        try:
            os.chdir(a_tree(work, "tree"))
            found = mod.load_run(required=False, session="S", own_only=True)
        finally:
            os.chdir(here)
        check("%s: an unscoped pointer still resolves" % kind,
              (found or {}).get("id"), "20260829-000009")


def shared_pointer_cases(kind):
    """The shared pointer is not taken from a run another worker still holds."""
    with tempfile.TemporaryDirectory() as state:
        mod = engine(kind, state)
        runs = Path(state) / ("%s-runs" % kind)
        runs.mkdir(parents=True, exist_ok=True)
        held = {"id": "20260829-000001", "session": "OTHER", "order": [], "results": {}}
        (runs / "20260829-000001.json").write_text(json.dumps(held))
        (runs / "current.json").write_text(json.dumps({"id": "20260829-000001"}))

        mine = {"id": "20260829-000002", "session": "MINE", "order": [], "results": {}}
        mod.save_run(mine)
        still = json.loads((runs / "current.json").read_text())["id"]
        check("%s: an open run keeps the shared pointer" % kind, still, "20260829-000001")

        held["closed"] = "2026-08-29 00:00:00Z"
        (runs / "20260829-000001.json").write_text(json.dumps(held))
        mod.save_run(mine)
        taken = json.loads((runs / "current.json").read_text())["id"]
        check("%s: a closed run releases it" % kind, taken, "20260829-000002")


def probe_cases():
    """A probe refuses to write over a reading something else may still hold."""
    for kind in ("db", "stack", "google"):
        path = CHECKLISTS / kind / "scripts" / "probe.py"
        mod = load(path, "probe_%s_%d" % (kind, time.time_ns()))
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "shared.json"
            fresh.write_text("{}")
            try:
                mod.guarded_probe_out(str(fresh))
                FAILURES.append("%s probe: a fresh reading was overwritten" % kind)
            except SystemExit as exc:
                check("%s probe: the refusal names the path" % kind,
                      str(fresh) in str(exc), True)
            check("%s probe: force takes it" % kind,
                  mod.guarded_probe_out(str(fresh), force=True), fresh)

            old = time.time() - 7200
            os.utime(fresh, (old, old))
            check("%s probe: a stale reading is free" % kind,
                  mod.guarded_probe_out(str(fresh)), fresh)

            first = mod.default_probe_out(kind)
            check("%s probe: the default names the kind" % kind, kind in first.name, True)
            check("%s probe: the default is not the documented shared path" % kind,
                  first.name in ("%s-probe.json" % kind,), False)


VERB = "git" + " " + "commit"

def two_runs_one_session_cases(kind):
    """Two runs in one session over two trees do not share a pointer.

    The observed failure: a design run over djrxexcellence had its pointer taken
    by a run over domebreak, two captures landed in the wrong run, and every
    verify afterwards swept one tree while reporting against the other.
    """
    with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as work:
        mod = engine(kind, state)
        runs = Path(state) / ("%s-runs" % kind)
        runs.mkdir(parents=True, exist_ok=True)
        first, second = a_tree(work, "djrx"), a_tree(work, "domebreak")
        one = {"id": "20260829-001632", "session": "S", "repo": str(first),
               "targets": [str(first)], "order": [], "results": {}}
        two = {"id": "20260829-003627", "session": "S", "repo": str(second),
               "targets": [str(second)], "order": [], "results": {}}
        mod.save_run(one)
        mod.save_run(two)

        p_one = mod.pointer_for("S", mod.run_target(one))
        p_two = mod.pointer_for("S", mod.run_target(two))
        check("%s: two trees take two pointers" % kind, p_one == p_two, False)
        check("%s: the first run keeps its own pointer" % kind,
              json.loads(p_one.read_text())["id"], "20260829-001632")
        check("%s: the second run keeps its own" % kind,
              json.loads(p_two.read_text())["id"], "20260829-003627")

        here = Path.cwd()
        try:
            os.chdir(first)
            found = mod.load_run(required=False, session="S", own_only=True)
        finally:
            os.chdir(here)
        check("%s: a call inside a tree resolves that tree's run" % kind,
              (found or {}).get("id"), "20260829-001632")

        # Standing in neither tree, with two open, nothing is returned. Guessing
        # is what put one run's readings in the other's ledger.
        picked = mod.run_here([one, two], here=work)
        check("%s: two open runs and no tree in common resolves nothing" % kind,
              picked, None)
        check("%s: one open run needs no tree to resolve" % kind,
              (mod.run_here([one], here=work) or {}).get("id"), "20260829-001632")
        # Standing inside a different project is not standing nowhere. A run
        # that has read nothing here must not gate a landing here.
        elsewhere = Path(work) / "another-project"
        elsewhere.mkdir(exist_ok=True)
        subprocess.run(["git", "init", "-q"], cwd=elsewhere, check=True)
        check("%s: one open run does not answer inside another project" % kind,
              mod.run_here([one], here=elsewhere), None)



def directory_scope_cases(kind):
    """A run governs the directory it owns and no other, whichever path reached it.

    The observed failure: a run opened over one worktree resolved through the
    pointer keyed on the session alone in every directory on the machine, and the
    landing guard then refused work in an unrelated repository over gates
    belonging to a project it had never read.
    """
    with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as work:
        mod = engine(kind, state)
        runs = Path(state) / ("%s-runs" % kind)
        runs.mkdir(parents=True, exist_ok=True)
        target, elsewhere = a_repo(work, "target"), a_repo(work, "elsewhere")
        run = a_run(kind, "20260830-211131", target)
        (runs / ("%s.json" % run["id"])).write_text(json.dumps(run))

        here = Path.cwd()
        try:
            os.chdir(elsewhere)
            # The pointer keyed on the session alone: the one path that reaches a
            # run without ever comparing its tree against a directory.
            mod.session_pointer("S").write_text(json.dumps({"id": run["id"]}))
            unscoped = mod.load_run(required=False, session="S", own_only=True)
            outside = mod.load_run(required=False, session="S", own_only=True,
                                   here=str(elsewhere))
            inside = mod.load_run(required=False, session="S", own_only=True,
                                  here=str(target))
            below = mod.load_run(required=False, session="S", own_only=True,
                                 here=str(target / "src" / "deep"))
            try:
                mod.load_run(required=True, session="S", own_only=True,
                             here=str(elsewhere))
                demanded = "returned"
            except SystemExit:
                demanded = "raised"
        finally:
            os.chdir(here)

        check("%s: a call naming no directory is not scoped" % kind,
              (unscoped or {}).get("id"), "20260830-211131")
        check("%s: a session pointer does not govern another project" % kind,
              outside, None)
        check("%s: it governs its own target" % kind,
              (inside or {}).get("id"), "20260830-211131")
        check("%s: it governs below its own target" % kind,
              (below or {}).get("id"), "20260830-211131")
        check("%s: a scoped-out run raises where one is required" % kind,
              demanded, "raised")


def moved_tree_cases(kind):
    """A run whose tree is gone still answers from outside every checkout.

    Nothing else could close it: the directory it was opened over no longer
    exists, so no call made inside that directory can reach the run.
    """
    with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as work:
        mod = engine(kind, state)
        runs = Path(state) / ("%s-runs" % kind)
        runs.mkdir(parents=True, exist_ok=True)
        run = a_run(kind, "20260830-211132", Path(work) / "moved-away")
        (runs / ("%s.json" % run["id"])).write_text(json.dumps(run))
        (runs / "current-S.json").write_text(json.dumps({"id": run["id"]}))
        found = mod.load_run(required=False, session="S", own_only=True, here=str(work))
        check("%s: a run whose tree has moved answers from outside every checkout" % kind,
              (found or {}).get("id"), "20260830-211132")


def guard_directory_cases(kind):
    """Both hooks judge the directory their payload names, not the process's.

    A hook runs in whatever directory the session holds, which in an agent thread
    is the home directory rather than the checkout the command acts on.
    """
    tool = CHECKLISTS / kind / "bin" / ("%s-pass.py" % kind)
    with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as work:
        runs = Path(state) / ("%s-runs" % kind)
        runs.mkdir(parents=True, exist_ok=True)
        target, elsewhere = a_repo(work, "target"), a_repo(work, "elsewhere")
        run = a_run(kind, "20260830-211133", target)
        (runs / ("%s.json" % run["id"])).write_text(json.dumps(run))
        # The pointer with no tree in its name, which every engine still reads.
        (runs / "current-S.json").write_text(json.dumps({"id": run["id"]}))
        env = dict(os.environ, INTELLIGENCE_STATE_DIR=state, CLAUDE_CODE_SESSION_ID="S")

        def hook(verb, named, standing):
            payload = {"session_id": "S", "cwd": str(named),
                       "tool_input": {"command": "%s -m x" % VERB}}
            done = subprocess.run([sys.executable, str(tool), verb],
                                  input=json.dumps(payload), capture_output=True,
                                  text=True, cwd=str(standing), env=env)
            return done.returncode, (done.stdout + done.stderr).strip()

        for verb in ("guard-land", "guard-stop"):
            # Standing in the other project, judging a command in the run's own.
            code, said = hook(verb, target, elsewhere)
            check("%s %s: the payload's tree is judged, not the process's" % (kind, verb),
                  code == 2 or "block" in said, True)
            # Standing in the run's own project, judging a command in the other.
            code, said = hook(verb, elsewhere, target)
            check("%s %s: another project's tree is left alone" % (kind, verb),
                  (code, said), (0, ""))


def landing_guard_cases(kind):
    """An apostrophe in a message must not make one run refuse another's tree."""
    mod = engine(kind, tempfile.mkdtemp())
    if not hasattr(mod, "landing_dir_from_text"):
        FAILURES.append("%s: carries no landing_dir_from_text" % kind)
        return
    with tempfile.TemporaryDirectory() as work:
        landing, other = a_tree(work, "landing"), a_tree(work, "other")
        command = "cd %s && %s -F - <<'MSG'\nTrenton's fix\nMSG" % (landing, VERB)
        got = mod.landing_dir_from_text(command, work)
        check("%s: the raw scan finds the cd target" % kind,
              got and Path(got).resolve(), Path(landing).resolve())
        check("%s: a command naming no tree resolves nothing" % kind,
              mod.landing_dir_from_text("%s -m x" % VERB, work), None)

        if hasattr(mod, "landing_dir"):
            where = mod.landing_dir({"cwd": str(work)}, command)
            check("%s: landing_dir resolves the tree despite the apostrophe" % kind,
                  where and Path(where).resolve(), Path(landing).resolve())

        run = {"id": "20260829-000003", "session": "S", "repo": str(other),
               "targets": [str(other)], "order": [], "results": {}}
        check("%s: an unresolvable tree is not covered" % kind,
              mod.run_covers(run, None), False)
        check("%s: another project's tree is not covered" % kind,
              mod.run_covers(run, str(landing)), False)
        check("%s: the run's own tree is covered" % kind,
              mod.run_covers(run, str(other)), True)


def closing_clears_pointers_cases(kind):
    """Closing a run leaves no pointer naming it.

    A pointer written under one name and removed under another outlives its run,
    and the next call resolves a closed run as an open one.
    """
    with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as work:
        mod = engine(kind, state)
        runs = Path(state) / ("%s-runs" % kind)
        runs.mkdir(parents=True, exist_ok=True)
        tree = a_tree(work, "proj")
        run = {"id": "20260829-000010", "session": "S", "repo": str(tree),
               "targets": [str(tree)], "order": [], "results": {}}
        mod.save_run(run)
        # Spellings an older build wrote, which a removal keyed on one name misses.
        (runs / "current-S.json").write_text(json.dumps({"id": run["id"]}))
        (runs / "current-hand-written.json").write_text(json.dumps({"id": run["id"]}))
        before = list(runs.glob("current*.json"))
        check("%s: several pointers name the run before closing" % kind, len(before) >= 3, True)

        run["closed"] = "2026-08-29 00:00:00Z"
        mod.clear_pointers(run)
        left = [p.name for p in runs.glob("current*.json")
                if json.loads(p.read_text()).get("id") == run["id"]]
        check("%s: closing leaves no pointer naming it" % kind, left, [])

        # A pointer naming somebody else's run is not this run's to remove.
        other = {"id": "20260829-000011", "session": "S", "repo": str(a_tree(work, "other")),
                 "targets": [], "order": [], "results": {}}
        mod.save_run(other)
        mod.clear_pointers(run)
        still = [p for p in runs.glob("current*.json")
                 if json.loads(p.read_text()).get("id") == other["id"]]
        check("%s: another run's pointer survives" % kind, bool(still), True)


def main():
    # A tree with the mechanism missing answers as a failure rather than a
    # traceback, so running this against an older checkout reports which engine
    # lacks it instead of stopping at the first.
    for kind in KINDS:
        for case in (pointer_cases, legacy_cases, shared_pointer_cases,
                     two_runs_one_session_cases, closing_clears_pointers_cases,
                     directory_scope_cases, moved_tree_cases,
                     guard_directory_cases):
            try:
                case(kind)
            except (AttributeError, TypeError) as exc:
                FAILURES.append("%s: the engine carries no %s" % (kind, exc))
    for kind in ("seo", "perf", "stack", "design"):
        try:
            landing_guard_cases(kind)
        except AttributeError as exc:
            FAILURES.append("%s landing guard: %s" % (kind, exc))
    try:
        probe_cases()
    except AttributeError as exc:
        FAILURES.append("probe: %s" % exc)
    for row in FAILURES:
        print("FAIL " + row)
    print("%d case(s) failed." % len(FAILURES) if FAILURES else "All cases pass.")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
