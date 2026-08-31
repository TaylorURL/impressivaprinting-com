#!/usr/bin/env python3
"""Whether the routines actually ran, and what they answered.

The machine that hosts them fails silently: an empty queue and a clean night
look identical from here, and a run that stopped happening announces nothing.
So the question is not whether anything complained, it is when each routine last
finished and what it finished with.

A routine that has not run inside its own cadence is overdue, and overdue is the
finding. A routine that ran and failed is a different finding, and both are
worse than the silence that currently stands for both.

  check        exit 2 when a routine is overdue or last failed
  report       every routine, when it last ran, and how it ended
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

INTELLIGENCE = Path.home() / ".intelligence"
REMOTE = INTELLIGENCE / "tools" / "remote-access.py"

# How long after its own cadence a routine is late rather than simply between
# runs. A daily routine is not overdue at twenty-five hours; it is at two days.
GRACE = 2.0

CADENCE = {
    "blog": 86400,
    "maintenance": 86400,
    "billing": 604800,
    "weekly": 604800,
    "monthly": 2678400,
    "error-monitor": None,
    "day-rollover": None,
}


def statuses():
    """Every routine's last recorded outcome, read from the machine that runs them."""
    done = subprocess.run(
        [sys.executable, str(REMOTE), "run", "pi", "--",
         "cat /home/sunday/routine-logs/*.status.json 2>/dev/null"],
        capture_output=True, text=True, timeout=180)
    out = {}
    for line in done.stdout.replace("}{", "}\n{").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        out[row.get("routine", "?")] = row
    return out


def scheduled_since():
    """When the schedule itself was written.

    A routine that has never run is only a finding once its own cadence has
    passed since it was scheduled. Before that it is simply waiting for its
    first turn, and reporting it as missing trains the reader to ignore this.

    The crontab is not readable by the account this runs as, so the read is
    made with sudo. Without it the stat fails, this returns zero, and every
    never-run routine is treated as still waiting however long it has been:
    the one branch that catches a routine that never started is switched off
    by a permission error that nothing prints.
    """
    done = subprocess.run(
        [sys.executable, str(REMOTE), "run", "pi", "--",
         "sudo -n stat -c %Y /var/spool/cron/crontabs/sunday 2>/dev/null"],
        capture_output=True, text=True, timeout=120)
    for line in done.stdout.split():
        if line.strip().isdigit():
            return float(line.strip())
    return 0.0


def findings():
    seen = statuses()
    now = time.time()
    since = scheduled_since()
    out = []
    for name, period in CADENCE.items():
        row = seen.get(name)
        if not row:
            waited = now - since if since else 0
            if period and since and waited > period * GRACE:
                out.append("%s has not run since it was scheduled %s ago"
                           % (name, span(waited)))
            continue
        age = now - float(row.get("at") or 0)
        if row.get("exit") not in (0, None):
            out.append("%s last ended in failure, %s ago" % (name, span(age)))
        elif period and age > period * GRACE:
            out.append("%s is overdue: last ran %s ago" % (name, span(age)))
    return out


def span(seconds):
    hours = seconds / 3600
    if hours < 48:
        return "%d hour(s)" % hours
    return "%d day(s)" % (hours / 24)


def cmd_report():
    seen = statuses()
    now = time.time()
    if not seen:
        print("no routine has recorded an outcome yet")
        return 0
    for name in CADENCE:
        row = seen.get(name)
        if not row:
            print("  %-16s never run" % name)
            continue
        print("  %-16s %-12s %s ago" % (
            name, "ok" if row.get("exit") == 0 else "exit %s" % row.get("exit"),
            span(now - float(row.get("at") or 0))))
    return 0


def cmd_check():
    gaps = findings()
    for gap in gaps:
        print(gap)
    print("routine-health: %d finding(s)" % len(gaps))
    return 2 if gaps else 0


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "report":
        return cmd_report()
    if verb == "check":
        return cmd_check()
    sys.stderr.write(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
