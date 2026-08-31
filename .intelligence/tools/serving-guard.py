#!/usr/bin/env python3
"""A turn does not end on a merge; it ends on a page.

A promotion answers with GitHub's word that the branch moved, and a person
answers with what the browser shows them. Nothing in the ship path crosses that
distance, so the last thing a run knows is that a merge happened and the first
thing a person asks is whether the site changed.

Recording the merge is what lets the stop guard ask. Without a marker it would
have to read a deployment on every stop, including the runs that shipped
nothing.

  track        PostToolUse: note a promotion into the production branch
  guard-stop   Stop: hold the turn open until the site serves that commit
  status       what is outstanding

INTELLIGENCE_ALLOW_UNSERVED=1 lets one run finish without the reading.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
INTELLIGENCE = HOME / ".intelligence"
def site_live():
    """The reader, which a case suite replaces with one whose answer it fixes."""
    return Path(os.environ.get("INTELLIGENCE_SITE_LIVE")
                or INTELLIGENCE / "tools" / "site-live.py")

# A promotion into production, however it is spelled. A merge into the
# integration branch is not one: nothing serves that branch, so there is no
# page for it to disagree with.
PROMOTED = re.compile(
    r"\bgh\s+pr\s+merge\b[^\n]*--base[= ]main\b"
    r"|\bgit\s+push\b[^\n]*\borigin\s+(?:HEAD:)?main\b"
    r"|\bgh\s+pr\s+merge\b(?![^\n]*--base)[^\n]*\bmain\b",
    re.I)

# How long a marker stands before it is stale rather than outstanding. A run
# that ended hours ago is not a promotion this turn is responsible for.
STALE_SECONDS = 6 * 60 * 60


def state_root():
    override = os.environ.get("INTELLIGENCE_STATE_DIR")
    if override:
        return Path(override)
    if os.environ.get("CLAUDE_CODE_REMOTE"):
        return HOME / ".pass-state"
    return INTELLIGENCE / "state"


def marker():
    return state_root() / "serving-pending.json"


def payload():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def repo_of(cwd):
    done = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd or None,
                          capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def cmd_track():
    p = payload()
    command = str((p.get("tool_input") or {}).get("command") or "")
    if not PROMOTED.search(command):
        return 0
    root = repo_of(p.get("cwd"))
    if not root:
        return 0
    path = marker()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"root": root, "at": time.time(),
                                "command": command[:200]}) + "\n")
    return 0


def outstanding():
    path = marker()
    if not path.exists():
        return None
    try:
        note = json.loads(path.read_text())
    except ValueError:
        path.unlink(missing_ok=True)
        return None
    if time.time() - float(note.get("at") or 0) > STALE_SECONDS:
        path.unlink(missing_ok=True)
        return None
    return note


def reading(root):
    """What the serving stage says, as (verdict, words).

    Four answers rather than two. A site serving the promoted commit and a site
    still serving the old one are the pair this was built for. A reading that
    could not be taken is the third, and it holds the turn open, since an unread
    site is exactly the state the guard exists to stop passing for a live one. A
    repository nothing hosts is the fourth, and it clears: there is no page to
    read now and none to read later, so a turn held for one is held forever.
    """
    done = subprocess.run(
        [sys.executable, str(site_live()), "check", root, "--stage", "serving",
         "--json"], capture_output=True, text=True, timeout=180)
    try:
        answer = json.loads(done.stdout or "{}")
    except ValueError:
        return None, (done.stderr or done.stdout or "").strip()[:200]
    # The reading comes back as one row per stage, each carrying its own name,
    # so the row is reached for by name. A run over every stage and a run over
    # one then read alike, and a reading in any other shape is a reading that
    # was not taken.
    rows = answer.get("stages") if isinstance(answer, dict) else None
    stage = next((row for row in rows or []
                  if isinstance(row, dict) and row.get("stage") == "serving"), None)
    if stage is None:
        return "unread", (done.stderr or done.stdout or "").strip()[:200] or "unread"
    if not (answer.get("site") or {}).get("hosts"):
        return "unhosted", stage.get("detail") or "no host serves this repository"
    if stage.get("state") == "unprobed":
        return "unread", stage.get("detail") or "unread"
    return ("ok" if stage.get("ok") else "failing"), stage.get("detail") or ""


def guard_stop():
    if os.environ.get("INTELLIGENCE_ALLOW_UNSERVED") == "1":
        return 0
    note = outstanding()
    if not note:
        return 0
    try:
        state, detail = reading(note["root"])
    except (OSError, subprocess.SubprocessError) as err:
        sys.stderr.write("serving-guard: the site could not be read (%s)\n" % err)
        return 0
    if state == "unhosted":
        marker().unlink(missing_ok=True)
        sys.stderr.write("serving-guard: nothing hosts this repository, so the "
                         "promotion has no page to answer for (%s)\n" % detail)
        return 0
    if state == "ok":
        marker().unlink(missing_ok=True)
        return 0
    if state == "unread":
        sys.stderr.write(
            "BLOCKED: a promotion this turn has not been seen on the site.\n\n"
            "  the reading came back unread: %s\n\n"
            "A merge is GitHub's answer. The question is what the page serves,\n"
            "and that has not been established.\n\n"
            "INTELLIGENCE_ALLOW_UNSERVED=1 lets one run finish without it.\n"
            % detail)
        return 2
    sys.stderr.write(
        "BLOCKED: the site is not yet serving what was promoted.\n\n  %s\n\n"
        "The turn ends when a visitor gets the new build, not when the merge\n"
        "lands. Wait for the deployment, or say what is holding it.\n\n"
        "INTELLIGENCE_ALLOW_UNSERVED=1 lets one run finish without it.\n" % detail)
    return 2


def cmd_status():
    note = outstanding()
    if not note:
        print("serving-guard: nothing outstanding")
        return 0
    print("serving-guard: %s promoted, awaiting a reading" % note["root"])
    return 0


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "track":
        return cmd_track()
    if verb == "guard-stop":
        return guard_stop()
    if verb == "status":
        return cmd_status()
    sys.stderr.write(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
