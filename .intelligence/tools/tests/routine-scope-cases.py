#!/usr/bin/env python3
"""Cases the sweep scope has to get right.

The survey is exercised against stubbed tips rather than the network, so the
comparison is what is under test. Three answers have to hold: a repo nobody has
recorded is due, a repo whose tips moved is due, and a repo that could not be
read is due rather than quietly skipped, because unreadable and unchanged look
the same to everything downstream and only one of them is safe to skip.

  routine-scope-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "routine-scope.py")

FAILURES = []


def load():
    spec = importlib.util.spec_from_file_location("routine_scope", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def main():
    mod = load()
    mod.STATE = Path(tempfile.mkdtemp()) / "routine-scope"

    state = {
        "a/one": {"develop": "aaa", "main": "aaa"},
        "a/two": {"develop": "bbb", "main": "bbb"},
        "a/gone": None,
    }
    mod.owned = lambda: sorted(state)
    mod.tips = lambda repo: state[repo]

    rows = {r: (due, why) for r, due, why, _t in mod.survey("daily")}
    check("never swept is due", rows["a/one"][0], True)
    check("never swept says so", rows["a/one"][1], "never swept")
    check("unreadable is due", rows["a/gone"][0], True)
    check("unreadable says so", rows["a/gone"][1], "unreadable")

    mod.main_argv = None
    sys.argv = ["routine-scope.py", "record", "--routine", "daily"]
    mod.main()

    rows = {r: (due, why) for r, due, why, _t in mod.survey("daily")}
    check("recorded repo is skipped", rows["a/one"][0], False)
    check("recorded repo says unchanged", rows["a/one"][1], "unchanged")
    check("unreadable stays due after a record", rows["a/gone"][0], True)

    state["a/two"] = {"develop": "ccc", "main": "bbb"}
    rows = {r: (due, why) for r, due, why, _t in mod.survey("daily")}
    check("a moved branch is due", rows["a/two"][0], True)
    check("the moved branch is named", rows["a/two"][1], "moved: develop")
    check("its neighbour is still skipped", rows["a/one"][0], False)

    # A second routine keeps its own reckoning.
    rows = {r: (due, why) for r, due, why, _t in mod.survey("weekly")}
    check("another routine has swept nothing", rows["a/one"][0], True)

    # A repo that becomes readable again is due, then settles.
    state["a/gone"] = {"develop": "ddd", "main": "ddd"}
    sys.argv = ["routine-scope.py", "record", "--routine", "daily"]
    mod.main()
    rows = {r: (due, why) for r, due, why, _t in mod.survey("daily")}
    check("a recovered repo settles", rows["a/gone"][0], False)

    for f in FAILURES:
        print(f)
    print(f"routine-scope: {len(FAILURES)} failing")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
