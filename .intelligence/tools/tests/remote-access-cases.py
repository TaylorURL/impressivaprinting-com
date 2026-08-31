#!/usr/bin/env python3
"""Cases the remote-access guard has to get right.

The two directions that matter: a reply handing work back for a machine that
answers is refused, and a reply reporting a machine that genuinely does not
answer stands. A guard that cannot tell those apart either blocks honest
reporting or waves the handback through.

  remote-access-cases.py        run them
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

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "remote-access.py")

FAILURES = []


def load():
    spec = importlib.util.spec_from_file_location("remote_access", TARGET)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def transcript(dirpath, reply):
    rows = [{"type": "user", "message": {"content": "go"}},
            {"type": "assistant",
             "message": {"content": [{"type": "text", "text": reply}]}}]
    path = Path(dirpath) / "transcript.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def run_guard(reply, routes, stop_hook_active=False, env=None):
    """Exit code of guard-stop for a reply, against a primed route cache."""
    with tempfile.TemporaryDirectory() as home:
        state = Path(home) / ".intelligence" / "state"
        state.mkdir(parents=True)
        now = int(time.time())
        (state / "remote-access.json").write_text(json.dumps(
            {a: {"route": r, "at": now} for a, r in routes.items()}))
        path = transcript(home, reply)
        ev = json.dumps({"transcript_path": str(path),
                         "stop_hook_active": stop_hook_active})
        environ = dict(os.environ, HOME=home)
        environ.pop("INTELLIGENCE_REMOTE_OFF", None)
        environ.update(env or {})
        p = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                           input=ev, capture_output=True, text=True, env=environ)
        return p.returncode


def main():
    mod = load()

    # A surrender and a machine name in one sentence is the shape being caught.
    for text, want in [
        ("I can't reach your Mac from the cloud.", ["mac"]),
        ("Run it there if that's the question.", []),
        ("Run it on your Mac if that's the question.", ["mac"]),
        ("This is local only, so the Pi is out of scope.", ["pi"]),
        ("You'll need to run this on the Windows desktop yourself.", ["windows"]),
        ("The VPS is not reachable from cloud.", ["vps"]),
        ("I don't have access to the Mac.", ["mac"]),
        ("This cloud session can't see the Mac's unpublished edits.", ["mac"]),
        # No machine named: the sentence is about something else.
        ("I can't reach the database from here.", []),
        ("You'll need to decide which palette to use.", []),
        # A machine named with no surrender.
        ("The Mac is in step with the mirror.", []),
        ("Ran the check on the Mac and the Pi; both clean.", []),
        # Separate sentences must not pair up.
        ("The VPS cannot be reached.\nThe Mac is in step.", ["vps"]),
        # A quoted script carries its own error strings. Read as the writer's,
        # showing anyone the setup script reads as giving up on the Pi.
        ("Here it is.\n\n```bash\ndie \"the Pi is not answering\"\n```\n", []),
        ("```\nlog 'cannot reach the Mac'\n```\nThe Mac is in step.", []),
        # Prose outside a block still answers for itself.
        ("```\ncode\n```\nI can't reach your Mac from the cloud.", ["mac"]),
    ]:
        check(f"surrenders {text[:40]!r}", mod.surrenders(text), want)

    # A cloud container reaches the Mac by way of the Pi, so the argv carries
    # the inner ssh quoted for the Pi's shell.
    #
    # Which machine is the local one is pinned rather than read off the host
    # running this: on the Mac, is_local answers true for "mac" and wrap takes
    # the local shortcut, so the jump route would go untested on the machine
    # these cases run on most. Both readings are asserted below.
    was_local = mod.is_local
    try:
        mod.is_local = lambda alias: False
        argv = mod.wrap("mac", "echo hi")
        check("wrap mac goes through the jump", argv[-2], "sunday")
        check("wrap mac carries the inner hop", "trenton-mac" in argv[-1], True)
        check("wrap pi is one hop",
              mod.wrap("pi", "echo hi")[-2:], ["sunday", "echo hi"])

        mod.is_local = lambda alias: alias == "mac"
        check("wrap on the machine asked for stays home",
              mod.wrap("mac", "echo hi"), ["bash", "-lc", "echo hi"])

        mod.is_local = lambda alias: alias == "pi"
        argv = mod.wrap("mac", "echo hi")
        check("wrap from the jump host goes direct", argv[-2:],
              ["trenton-mac", "echo hi"])
        check("wrap from the jump host does not hop through itself",
              "sunday" in argv, False)
    finally:
        mod.is_local = was_local

    # The refusal, and the cases that have to stay out of the way.
    check("blocks handback for a reachable mac",
          run_guard("I can't reach your Mac; run it there.",
                    {"mac": "via sunday"}), 2)
    check("allows an honest unreachable report",
          run_guard("I can't reach your Mac; it is not answering.",
                    {"mac": None}), 0)
    check("allows an ordinary reply",
          run_guard("The Mac is in step with the mirror.",
                    {"mac": "via sunday"}), 0)
    check("allows a second pass",
          run_guard("I can't reach your Mac; run it there.",
                    {"mac": "via sunday"}, stop_hook_active=True), 0)
    check("override disables it",
          run_guard("I can't reach your Mac; run it there.",
                    {"mac": "via sunday"},
                    env={"INTELLIGENCE_REMOTE_OFF": "1"}), 0)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
