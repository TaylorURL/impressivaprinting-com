#!/usr/bin/env python3
"""Cases the routine health check has to get right.

Silence and success look the same on a machine that reports nothing, so the
check has to separate three states that are easy to collapse into one: a run
that succeeded, a run that failed, and a run that never happened. The third is
only a finding once enough time has passed that it should have.

  routine-health-cases.py      run them
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "routine-health.py")
FAILURES = []

DAY = 86400


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verdict(rows, scheduled_ago):
    mod = load()
    now = time.time()
    mod.statuses = lambda: rows
    mod.scheduled_since = lambda: now - scheduled_ago
    return mod.findings()


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def main():
    now = time.time()
    fresh = {"maintenance": {"routine": "maintenance", "exit": 0, "at": now - 3600}}
    failed = {"maintenance": {"routine": "maintenance", "exit": 1, "at": now - 3600}}
    stale = {"maintenance": {"routine": "maintenance", "exit": 0, "at": now - 5 * DAY}}

    check("a run that succeeded recently is not a finding",
          [f for f in verdict(fresh, DAY) if "maintenance" in f], [])
    check("a run that failed is a finding",
          any("failure" in f for f in verdict(failed, DAY)), True)
    check("a run that stopped happening is a finding",
          any("overdue" in f for f in verdict(stale, 10 * DAY)), True)

    # A routine scheduled an hour ago has not failed to run; it is waiting.
    check("a schedule installed moments ago reports nothing",
          verdict({}, 3600), [])
    check("but one that never ran after long enough is a finding",
          any("has not run since it was scheduled" in f
              for f in verdict({}, 30 * DAY)), True)

    # An event-driven routine has no cadence, so it can never be overdue.
    check("a routine with no cadence is never overdue",
          any("error-monitor" in f for f in verdict({}, 365 * DAY)), False)

    for f in FAILURES:
        print(f)
    print("routine-health: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
