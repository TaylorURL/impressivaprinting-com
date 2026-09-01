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
import re
import subprocess
import sys
import time
from pathlib import Path

INTELLIGENCE = Path.home() / ".intelligence"
REMOTE = INTELLIGENCE / "tools" / "remote-access.py"

# How long after its own cadence a routine is late rather than simply between
# runs. A daily routine is not overdue at twenty-five hours; it is at two days.
GRACE = 2.0

# A schedule this cannot read is worth naming rather than skipping. The whole
# point of the tool is that silence and health look identical from here, and a
# routine quietly left out of the reading rebuilds exactly that.
CRON_PERIOD = {
    "minute": 60, "hour": 3600, "day": 86400, "week": 604800, "month": 2678400,
}


def registry():
    """Every routine there is, read from the list that can rebuild one.

    The registry is the coverage rather than a table kept beside it. A list
    held by hand is the one shape that cannot survive a routine being added:
    what it leaves out is not reported healthy, it is not reported at all,
    which is the silence this tool exists to break. So a routine the registry
    names and this cannot judge is a finding rather than a line that never
    prints.
    """
    for base in (Path(__file__).resolve().parent.parent,
                 Path.home() / "Development" / "intelligence",
                 INTELLIGENCE / "state" / ".config-sync-repo"):
        path = base / "routines" / "registry.json"
        if path.is_file():
            return json.loads(path.read_text()).get("routines", [])
    return []


def gated(entry):
    """Whether a routine starts on a tick's judgement rather than on a clock.

    A gated routine declares the tick's cadence and not its own, because it has
    none: the error queue fills when a visitor hits a bug and the day turns when
    the workstation says it has. Judging the work against the tick's interval
    reads every quiet hour as an outage, which is the false finding that buries
    the true ones.
    """
    return bool(entry.get("gate")) and not entry.get("schedule")


def period_of(entry):
    """How often a routine comes round, in seconds, or None if unreadable.

    A poll declares an interval and a slot declares a schedule. They are
    separate fields because the schedule is also what the minute-collision
    check reads, and a routine firing every ten minutes shares a minute with
    everything without that being a clash anybody can act on.
    """
    if entry.get("interval"):
        return int(entry["interval"])
    schedule = entry.get("schedule")
    if not schedule:
        return None
    text = schedule.strip()
    hit = re.match(r"every\s+(\d+)\s*s", text, re.I)
    if hit:
        return int(hit.group(1))
    if re.match(r"daily\b", text, re.I):
        return CRON_PERIOD["day"]
    if re.match(r"weekly\b", text, re.I):
        return CRON_PERIOD["week"]
    fields = text.split()
    if len(fields) != 5:
        return None
    minute, hour, dom, month, dow = fields
    if month != "*":
        return CRON_PERIOD["month"]
    if dom != "*":
        return CRON_PERIOD["month"]
    if dow != "*":
        return CRON_PERIOD["week"]
    if hour != "*":
        # A list of hours fires that many times a day; one hour is daily.
        return CRON_PERIOD["day"] // max(1, len(hour.split(",")))
    if minute.startswith("*/"):
        return CRON_PERIOD["minute"] * int(minute[2:])
    return CRON_PERIOD["hour"]


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


def units_state():
    """Every timer-backed routine's unit, as the machine running it reports.

    A board writes no status file, so systemd's account is the only one there
    is. One call rather than one per unit, because a probe costing a round trip
    per routine is a probe that stops being run.
    """
    units = [e["unit"] for e in registry() if e.get("unit")]
    if not units:
        return {}
    script = (
        'for u in %s; do s=${u%%.timer}.service; '
        'printf "%%s|%%s|%%s|%%s\\n" "$u" "$(systemctl is-active $u)" '
        '"$(systemctl show -p Result --value $s)" '
        '"$(systemctl show -p ExecMainStatus --value $s)"; done'
        % " ".join(units))
    done = subprocess.run(
        [sys.executable, str(REMOTE), "run", "pi", "--", script],
        capture_output=True, text=True, timeout=180)
    out = {}
    for line in done.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) == 4 and parts[0].endswith(".timer"):
            out[parts[0]] = {"active": parts[1], "result": parts[2],
                             "exit": parts[3]}
    return out


def mac_loaded(label="com.intelligence.sentinel"):
    """Whether the workstation's own watch is still loaded.

    Its exit code is its verdict and not its health: it returns non-zero when
    the setup check finds something, so reading that as a failure reports a
    routine doing its job as a routine that is broken.
    """
    done = subprocess.run(
        [sys.executable, str(REMOTE), "run", "mac", "--",
         "launchctl list | grep -c %s" % label],
        capture_output=True, text=True, timeout=120)
    for token in done.stdout.split():
        if token.strip().isdigit():
            return int(token.strip()) > 0
    return None


def rows():
    """Every routine the registry names, paired with how it is actually doing."""
    seen = statuses()
    units = units_state()
    now = time.time()
    since = scheduled_since()
    out = []
    for entry in registry():
        rid = entry.get("id")
        period = period_of(entry)
        if entry.get("unit"):
            state = units.get(entry["unit"])
            if not state:
                out.append((rid, "unreadable", "its unit did not answer"))
            elif state["active"] != "active":
                out.append((rid, "broken", "its timer is %s" % state["active"]))
            elif state["result"] not in ("success", ""):
                out.append((rid, "broken",
                            "its last run ended %s" % state["result"]))
            else:
                out.append((rid, "ok", "timer active, last run clean"))
            continue
        if entry.get("host") == "mac":
            loaded = mac_loaded()
            out.append((rid, "ok" if loaded else "broken",
                        "loaded" if loaded else "not loaded on the workstation"))
            continue
        row = seen.get(rid)
        if not row:
            waited = now - since if since else 0
            if gated(entry):
                out.append((rid, "ok", "gated: its tick has started no run"))
            elif period and since and waited > period * GRACE:
                out.append((rid, "broken", "has not run since it was scheduled "
                                           "%s ago" % span(waited)))
            elif not period:
                out.append((rid, "unreadable",
                            "has never run and names no schedule this can judge"))
            else:
                out.append((rid, "waiting", "not yet due for its first run"))
            continue
        age = now - float(row.get("at") or 0)
        if row.get("exit") not in (0, None):
            out.append((rid, "broken",
                        "last ended in failure, %s ago" % span(age)))
        elif not period:
            out.append((rid, "unreadable", "ran %s ago, and names no schedule "
                        "this can judge it against" % span(age)))
        elif gated(entry):
            out.append((rid, "ok", "gated: last started a run %s ago" % span(age)))
        elif age > period * GRACE:
            out.append((rid, "broken", "overdue: last ran %s ago" % span(age)))
        else:
            out.append((rid, "ok", "ran %s ago" % span(age)))
    return out


def findings():
    return ["%s %s" % (rid, why) for rid, verdict, why in rows()
            if verdict in ("broken", "unreadable")]


def span(seconds):
    hours = seconds / 3600
    if hours < 48:
        return "%d hour(s)" % hours
    return "%d day(s)" % (hours / 24)


def cmd_report():
    listed = rows()
    if not listed:
        print("the registry names no routines")
        return 1
    for rid, verdict, why in listed:
        print("  %-16s %-11s %s" % (rid, verdict, why))
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
