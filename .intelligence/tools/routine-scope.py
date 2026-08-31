#!/usr/bin/env python3
"""Which repositories a scheduled sweep actually has to visit.

The daily pass covers every owned repo, and most of them did not move since the
last one. Each visit still costs a clone check, a fetch, a ledger read and a
platform probe, and the answer is the same one it gave yesterday.

This records the tip of every branch a sweep cares about at the end of a run and
compares it at the start of the next. A repo whose tips have not moved is
reported as unchanged; everything else is due. The record is per routine, so the
daily and the weekly keep their own reckoning.

A repo the record has never seen is due, so the first run after this is
installed sweeps everything, and a repo that cannot be read is due as well:
unreadable is not the same as unchanged, and treating it as unchanged hides
exactly the repo worth looking at.

  due [--routine daily]      the repos to sweep, one per line
  report [--routine daily]   every repo, with the reason
  record [--routine daily]   store the current tips as swept
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

STATE = Path.home() / ".intelligence" / "state" / "routine-scope"
OWNERS = ("bradley-t-t", "TaylorURL")
BRANCHES = ("develop", "main")


def gh(path):
    done = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if done.returncode:
        return None
    try:
        return json.loads(done.stdout)
    except ValueError:
        return None


def owned():
    names = []
    for owner in OWNERS:
        done = subprocess.run(
            ["gh", "repo", "list", owner, "--limit", "100",
             "--json", "nameWithOwner"], capture_output=True, text=True)
        if done.returncode:
            continue
        names += [r["nameWithOwner"] for r in json.loads(done.stdout)]
    return sorted(names)


def tips(repo):
    """The tip of every branch a sweep reads, or None when unreadable."""
    found = {}
    for branch in BRANCHES:
        data = gh("/repos/%s/branches/%s" % (repo, branch))
        if data is None:
            continue
        found[branch] = (data.get("commit") or {}).get("sha")
    return found or None


def ledger(routine):
    path = STATE / ("%s.json" % routine)
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {"repos": {}}


def save(routine, data):
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / ("%s.json" % routine)).write_text(json.dumps(data, indent=2) + "\n")


def survey(routine):
    """Every repo, paired with whether the sweep has to visit it and why."""
    known = ledger(routine).get("repos", {})
    rows = []
    for repo in owned():
        current = tips(repo)
        if current is None:
            rows.append((repo, True, "unreadable", None))
            continue
        before = known.get(repo, {}).get("tips")
        if before is None:
            rows.append((repo, True, "never swept", current))
        elif before != current:
            moved = [b for b in set(before) | set(current)
                     if before.get(b) != current.get(b)]
            rows.append((repo, True, "moved: %s" % ", ".join(sorted(moved)),
                         current))
        else:
            rows.append((repo, False, "unchanged", current))
    return rows


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("verb", choices=["due", "report", "record"])
    parser.add_argument("--routine", default="daily")
    args = parser.parse_args()

    rows = survey(args.routine)

    if args.verb == "due":
        for repo, is_due, _reason, _tips in rows:
            if is_due:
                print(repo)
        return 0

    if args.verb == "report":
        due = sum(1 for _r, d, _x, _t in rows if d)
        for repo, is_due, reason, _tips in rows:
            print("%-42s %-4s %s" % (repo, "due" if is_due else "skip", reason))
        print("\n%d of %d due" % (due, len(rows)))
        return 0

    data = ledger(args.routine)
    data.setdefault("repos", {})
    for repo, _is_due, _reason, current in rows:
        if current is not None:
            data["repos"][repo] = {"tips": current, "swept": int(time.time())}
    save(args.routine, data)
    print("routine-scope: recorded %d repo(s) for %s"
          % (len(data["repos"]), args.routine))
    return 0


if __name__ == "__main__":
    sys.exit(main())
