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


SCHEDULED = [{"id": "maintenance", "host": "pi", "schedule": "0 10 * * *"}]
POLL = [{"id": "error-monitor", "host": "pi", "interval": 600}]
SILENT = [{"id": "error-monitor", "host": "pi"}]
TIMED = [{"id": "status-board", "host": "pi", "unit": "status-board.timer",
          "schedule": "every 120s"}]
WATCH = [{"id": "sentinel", "host": "mac", "schedule": "47 3,11,19 * * *"}]


def verdict(rows, scheduled_ago, routines=None, units=None, loaded=True):
    """The findings, with every machine the check would reach stubbed out.

    A suite that opens a connection is a suite that fails when the line does,
    and it reports the far machine rather than the code under test.
    """
    mod = load()
    now = time.time()
    mod.statuses = lambda: rows
    mod.scheduled_since = lambda: now - scheduled_ago
    mod.registry = lambda: SCHEDULED if routines is None else routines
    mod.units_state = lambda: units or {}
    mod.mac_loaded = lambda label=None: loaded
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

    # A poll declares an interval, and an interval is a cadence like any other.
    # Reading one as uncadenced is what let a routine firing hourly sit silent
    # for a day without the check having anything to say about it.
    check("a poll that stopped is a finding like any other",
          any("error-monitor" in f for f in verdict({}, 3 * DAY, POLL)), True)
    check("a poll inside its own interval is not",
          verdict({"error-monitor": {"routine": "error-monitor", "exit": 0,
                                     "at": now - 60}}, 3 * DAY, POLL), [])

    # A routine the registry names and this cannot judge is the one state that
    # must never pass quietly: it is indistinguishable from a healthy one.
    check("a routine declaring no cadence at all is a finding",
          any("no schedule this can judge" in f
              for f in verdict({}, 3 * DAY, SILENT)), True)

    # A board writes no status, so its unit is the only account of it.
    check("a timer running clean is not a finding",
          verdict({}, 3 * DAY, TIMED,
                  {"status-board.timer": {"active": "active",
                                          "result": "success", "exit": "0"}}),
          [])
    check("a timer that is not running is a finding",
          any("its timer is" in f for f in verdict(
              {}, 3 * DAY, TIMED,
              {"status-board.timer": {"active": "failed", "result": "success",
                                      "exit": "0"}})), True)
    check("a timer whose last run failed is a finding",
          any("ended" in f for f in verdict(
              {}, 3 * DAY, TIMED,
              {"status-board.timer": {"active": "active", "result": "timeout",
                                      "exit": "1"}})), True)
    check("a unit that did not answer is a finding",
          any("did not answer" in f
              for f in verdict({}, 3 * DAY, TIMED, {})), True)

    # The workstation's watch exits non-zero when it finds something, so its
    # exit code is its verdict and being loaded is its health.
    check("the workstation's watch loaded is not a finding",
          verdict({}, 3 * DAY, WATCH, None, True), [])
    check("the workstation's watch unloaded is a finding",
          any("not loaded" in f
              for f in verdict({}, 3 * DAY, WATCH, None, False)), True)

    for f in FAILURES:
        print(f)
    print("routine-health: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
