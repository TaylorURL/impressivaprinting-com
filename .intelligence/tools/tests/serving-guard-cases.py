#!/usr/bin/env python3
"""Cases the serving guard has to get right.

A promotion into the branch a host serves leaves a marker, and the turn stays
open until a reading of the site agrees with it. A merge into the integration
branch leaves nothing, because no host serves that branch. A reading that could
not be taken holds the turn open rather than closing it, since an unread site is
the state the whole guard exists to stop being treated as a pass.

  serving-guard-cases.py       run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "serving-guard.py")
FAILURES = []

PROMOTE = "gh pr merge 8 --base main --merge"
INTEGRATE = "gh pr merge 8 --base develop --squash"


def repo(tmp):
    root = Path(tmp) / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def run(verb, payload, state, extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("INTELLIGENCE_")}
    env["INTELLIGENCE_STATE_DIR"] = str(state)
    env.update(extra or {})
    done = subprocess.run([sys.executable, str(TARGET), verb],
                          input=json.dumps(payload), capture_output=True,
                          text=True, env=env, timeout=120)
    return done.returncode, done.stderr


def track(command, cwd, state):
    return run("track", {"tool_name": "Bash", "tool_input": {"command": command},
                         "cwd": str(cwd)}, state)


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %s, want %s" % (label, got, want))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state"
        state.mkdir()
        root = repo(tmp)
        marker = state / "serving-pending.json"

        track(INTEGRATE, root, state)
        check("a merge into the integration branch leaves no marker",
              marker.exists(), False)

        track(PROMOTE, root, state)
        check("a promotion leaves a marker", marker.exists(), True)

        # Nothing outstanding is nothing to hold the turn for.
        clean = Path(tmp) / "clean"
        clean.mkdir()
        code, _ = run("guard-stop", {}, clean)
        check("no marker lets the turn end", code, 0)

        # A site that disagrees holds the turn open, and the words say which.
        stub = Path(tmp) / "site-live.py"
        stub.write_text(
            "import json,sys\n"
            "print(json.dumps({'site': {'root': 'x', 'hosts': ['vercel']}, 'stages': ["
            "{'stage': 'build', 'ok': True, 'state': 'ok', 'detail': 'built'},"
            "{'stage': 'serving', 'ok': False, 'state': 'failing', "
            "'detail': 'serving abc123 while main is at def456'}]}))\n")
        code, err = run("guard-stop", {}, state,
                        {"INTELLIGENCE_SITE_LIVE": str(stub)})
        check("a disagreeing site holds the turn open", code, 2)
        check("it says what disagrees", "not yet serving" in err, True)
        check("the marker still stands", marker.exists(), True)

        # A reading that agrees clears it.
        stub.write_text(
            "import json\n"
            "print(json.dumps({'site': {'root': 'x', 'hosts': ['vercel']}, 'stages': ["
            "{'stage': 'serving', 'ok': True, 'state': 'ok', "
            "'detail': 'serving def456'}]}))\n")
        code, _ = run("guard-stop", {}, state,
                      {"INTELLIGENCE_SITE_LIVE": str(stub)})
        check("an agreeing site lets the turn end", code, 0)
        check("and clears the marker", marker.exists(), False)

        # A reading with no serving row in it is a reading that was not taken,
        # and an unread site is the state the guard exists to stop passing.
        track(PROMOTE, root, state)
        stub.write_text(
            "import json\n"
            "print(json.dumps({'site': {'root': 'x', 'hosts': ['vercel']}, 'stages': ["
            "{'stage': 'build', 'ok': True, 'state': 'ok', 'detail': 'built'}]}))\n")
        code, err = run("guard-stop", {}, state,
                        {"INTELLIGENCE_SITE_LIVE": str(stub)})
        check("a reading missing the stage holds the turn open", code, 2)
        check("it says the reading came back unread", "unread" in err, True)

        stub.write_text(
            "import json\n"
            "print(json.dumps({'site': {'root': 'x', 'hosts': ['vercel']}, 'stages': ["
            "{'stage': 'serving', 'ok': False, 'state': 'unprobed', "
            "'detail': 'no host answers'}]}))\n")
        code, err = run("guard-stop", {}, state,
                        {"INTELLIGENCE_SITE_LIVE": str(stub)})
        check("an unprobed stage holds the turn open", code, 2)
        check("it says why it could not be read", "no host answers" in err, True)

        # A repository nothing hosts has no page to answer for, and a marker
        # that can never clear holds every turn after it.
        track(PROMOTE, root, state)
        stub.write_text(
            "import json\n"
            "print(json.dumps({'site': {'root': 'x', 'hosts': []}, 'stages': ["
            "{'stage': 'serving', 'ok': False, 'state': 'unprobed', "
            "'detail': 'no host project, so what is deployed cannot be read'}]}))\n")
        code, err = run("guard-stop", {}, state,
                        {"INTELLIGENCE_SITE_LIVE": str(stub)})
        check("an unhosted repository lets the turn end", code, 0)
        check("and the marker goes with it", marker.exists(), False)
        check("it says why nothing was read", "nothing hosts" in err, True)

        # The override is one run, not a mode.
        track(PROMOTE, root, state)
        code, _ = run("guard-stop", {}, state, {"INTELLIGENCE_ALLOW_UNSERVED": "1"})
        check("the override lets one run finish", code, 0)

    for f in FAILURES:
        print(f)
    print("serving-guard: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
