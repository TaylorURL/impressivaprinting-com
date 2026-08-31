#!/usr/bin/env python3
"""Cases the Sunday voice guard has to get right.

The refusal is the easy half. The half that decides whether the gate survives
is everything it must let through: an ordinary reply that names a file, a hook
mentioned as work rather than as an excuse, a build recompiling something that
is not itself, and any turn where the person named the machinery first.

The joke's three properties are exercised one at a time, because a gate that
refuses a good line is a gate that gets switched off: a fresh frame pointed at
the work passes, the same frame twice does not, a stock butler line does not,
and a line sharing no word with the turn does not.

  sunday-voice-guard-cases.py   run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "sunday-voice-guard.py")

# settings.json exports an env block into every child, so an inherited switch
# would green the whole suite without running any of it.
for name in ("INTELLIGENCE_SUNDAY_VOICE_OFF", "INTELLIGENCE_ALLOW_GUARD_TALK",
             "INTELLIGENCE_STATE_DIR"):
    os.environ.pop(name, None)

FAILURES = []

NARRATION = "Blocked by the delegation guard -- handing the sweep to agents."
GOOD = ("Sunday is having its hands recalibrated mid-run; the roster sweep goes "
        "out to three agents instead.")


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %s, want %s" % (label, got, want))


def user(text):
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


def assistant(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def stop(reply, question="go", extra=None, env=None, state=None):
    """The guard as the Stop hook runs it, against a written transcript."""
    with tempfile.TemporaryDirectory() as work:
        path = Path(work) / "t.jsonl"
        rows = [user(question), assistant(reply)]
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        payload = {"transcript_path": str(path)}
        payload.update(extra or {})
        child = dict(os.environ)
        child["INTELLIGENCE_STATE_DIR"] = state or str(Path(work) / "state")
        child.update(env or {})
        done = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                              input=json.dumps(payload), capture_output=True,
                              text=True, env=child)
        return done.returncode


def main():
    check("the line the gate exists for", stop(NARRATION), 2)
    check("a guard named without a verdict",
          stop("I added a hook for the resize event."), 0)
    check("ordinary work naming a file",
          stop("The roster lists nine sites, all in site-roster.py."), 0)
    check("a build recompiling something that is not itself",
          stop("I am recompiling the binary now."), 0)
    check("the machinery inside a fenced block",
          stop("The sweep is done.\n\n```\n%s\n```\n" % NARRATION), 0)

    check("their word to spend",
          stop(NARRATION, question="why did the delegation guard stop you?"), 0)
    check("the override for a real report",
          stop(NARRATION, env={"INTELLIGENCE_ALLOW_GUARD_TALK": "1"}), 0)
    check("the guard switched off",
          stop(NARRATION, env={"INTELLIGENCE_SUNDAY_VOICE_OFF": "1"}), 0)
    check("a reply already sent back once",
          stop(NARRATION, extra={"stop_hook_active": True}), 0)
    check("an empty reply", stop("   "), 0)

    check("a fresh frame pointed at the work",
          stop(GOOD + "\n\nThe roster now lists nine sites.",
               question="run the sweep over the site roster"), 0)
    check("the same frame twice in one reply",
          stop("Sunday is off recalibrating the roster reader.\n\n"
               "My recalibration of the roster reader is nearly done.",
               question="run the sweep over the site roster"), 2)
    check("a stock line carrying no imagery at all",
          stop("The roster sweep is out with agents, sir, as you wish.",
               question="run the sweep over the site roster"), 2)
    check("the stock phrase used by the person first",
          stop("The roster sweep is out with agents, sir.",
               question="sweep the roster, sir"), 0)
    check("a line off the shelf",
          stop("Sunday has been sent to the workshop again, sir; the roster "
               "sweep carries on.",
               question="run the sweep over the site roster"), 2)
    check("a line about nothing in the turn",
          stop("Sunday is off improving the mainframe.\n\nNine sites.",
               question="run the sweep"), 2)

    with tempfile.TemporaryDirectory() as shared:
        room = str(Path(shared) / "state")
        check("a frame's first outing",
              stop(GOOD + "\n\nThe roster now lists nine sites.",
                   question="run the sweep over the site roster",
                   extra={"session_id": "s1"}, state=room), 0)
        check("the same frame a second time in the session",
              stop("Sunday is being recalibrated again; the roster sweep "
                   "continues without it.",
                   question="run the sweep over the site roster",
                   extra={"session_id": "s1"}, state=room), 2)
        check("a different session, unspent",
              stop("Sunday is being recalibrated again; the roster sweep "
                   "continues without it.",
                   question="run the sweep over the site roster",
                   extra={"session_id": "s2"}, state=room), 0)

    missing = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                             input=json.dumps({"transcript_path": "/nowhere/t.jsonl"}),
                             capture_output=True, text=True)
    check("no transcript", missing.returncode, 0)

    unknown = subprocess.run([sys.executable, str(TARGET), "wobble"],
                             capture_output=True, text=True)
    check("an unrecognised verb", unknown.returncode, 2)

    with tempfile.TemporaryDirectory() as work:
        path = Path(work) / "t.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in
                                  [user("go"), assistant(NARRATION)]) + "\n")
        measured = subprocess.run([sys.executable, str(TARGET), "measure", str(path)],
                                  capture_output=True, text=True)
        check("measure reports the fault", measured.returncode, 1)
        check("measure names the finding",
              "reports the machinery" in measured.stdout, True)

    for failure in FAILURES:
        print(failure)
    print("sunday-voice-guard: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
