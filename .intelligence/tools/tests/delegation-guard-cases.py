#!/usr/bin/env python3
"""Cases the delegation guard has to get right.

The guard is worth only what it refuses, and worth nothing if it refuses a turn
that had to read. So both edges are fixed here: a wide survey carried inline is
caught, an ordinary turn passes, a turn that already delegated passes, and a
turn that is editing rather than surveying passes. The spam edge is fixed too --
an agent sent after one file on disk is refused, and a real fan-out brief is
not -- since a gate that only pushes one way produces the opposite waste.

  delegation-guard-cases.py     run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "delegation-guard.py")

FAILURES = []
STATE = tempfile.mkdtemp(prefix="delegation-cases-")


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def load():
    import importlib.util
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def probe_block(command):
    return {"type": "tool_use", "name": "Bash", "input": {"command": command}}


def transcript(blocks, prompt="do the thing", sidechain=False, prefix=None):
    """A transcript ending mid-turn, with `blocks` already issued."""
    rows = [{"type": "user", "uuid": "u0",
             "message": {"role": "user", "content": prompt}}]
    for n, block in enumerate(prefix or []):
        rows.append({"type": "assistant", "uuid": "p%d" % n,
                     "message": {"role": "assistant", "content": [block]}})
    for n, block in enumerate(blocks):
        row = {"type": "assistant", "uuid": "a%d" % n,
               "message": {"role": "assistant", "content": [block]}}
        if sidechain:
            row["isSidechain"] = True
        rows.append(row)
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         dir=STATE)
    for row in rows:
        handle.write(json.dumps(row) + "\n")
    handle.close()
    return handle.name


def sweep(count=14):
    """A survey wide enough to belong to an agent."""
    return [probe_block("cat /etc/hosts%d" % n) for n in range(count)]


def run(verb, event, env=None):
    environ = dict(os.environ)
    environ["INTELLIGENCE_STATE_DIR"] = STATE
    environ.pop("INTELLIGENCE_DELEGATION_OFF", None)
    environ.pop("INTELLIGENCE_ALLOW_INLINE", None)
    environ.update(env or {})
    done = subprocess.run([sys.executable, str(TARGET), verb],
                          input=json.dumps(event).encode(),
                          capture_output=True, timeout=120, env=environ)
    return done.returncode, (done.stdout + done.stderr).decode()


def probe_event(path, session="cases", command="cat /etc/passwd"):
    return {"tool_name": "Bash", "tool_input": {"command": command},
            "transcript_path": path, "session_id": session}


def main():
    mod = load()

    # What counts as a read, which is what the survey is measured in.
    check("cat is a read", mod.read_shaped("cat foo.py"), True)
    check("piped grep is a read",
          mod.read_shaped("find . -name '*.py' | xargs grep todo"), True)
    check("redirect is not a read", mod.read_shaped("grep x foo > out.txt"), False)
    check("sed -i is not a read", mod.read_shaped("sed -i s/a/b/ foo"), False)
    check("rm is not a read", mod.read_shaped("rm -rf build"), False)
    check("install is not a read", mod.read_shaped("npm install"), False)
    check("empty is not a read", mod.read_shaped(""), False)

    # The survey gate, both edges.
    code, out = run("guard-probe", probe_event(transcript(sweep())))
    check("wide survey refused", code, 2)
    check("refusal names the count", "14 read-shaped calls" in out, True)

    code, _ = run("guard-probe", probe_event(transcript(sweep(4))))
    check("ordinary turn passes", code, 0)

    narrow = [probe_block("sed -n %d,%dp same.py" % (n, n + 5))
              for n in range(14)]
    code, _ = run("guard-probe", probe_event(transcript(narrow)))
    check("long walk of one file passes", code, 0)

    delegated = [{"type": "tool_use", "name": "Agent",
                  "input": {"prompt": "sweep the tree"}}] + sweep()
    code, _ = run("guard-probe", probe_event(transcript(delegated)))
    check("turn that already delegated passes", code, 0)

    editing = [{"type": "tool_use", "name": "Edit",
                "input": {"file_path": "/tmp/x"}}] + sweep()
    code, _ = run("guard-probe", probe_event(transcript(editing)))
    check("reads after an edit are not a survey", code, 0)

    code, _ = run("guard-probe",
                  probe_event(transcript(sweep(), sidechain=True)))
    check("a subagent is not asked to delegate", code, 0)

    code, _ = run("guard-probe", probe_event(transcript(sweep())),
                  {"INTELLIGENCE_ALLOW_INLINE": "1"})
    check("the inline override lets it through", code, 0)

    code, _ = run("guard-probe", probe_event(transcript(sweep())),
                  {"INTELLIGENCE_DELEGATION_OFF": "1"})
    check("the off switch stands it down", code, 0)

    code, _ = run("guard-probe", probe_event(transcript(sweep()),
                                             command="rm -rf /tmp/x"))
    check("a write is not measured", code, 0)

    # One refusal per turn: the same turn seen twice costs one redirect.
    path = transcript(sweep())
    first, _ = run("guard-probe", probe_event(path, session="latch"))
    second, _ = run("guard-probe", probe_event(path, session="latch"))
    check("first pass refuses", first, 2)
    check("second pass lets it stand", second, 0)

    # An open checklist run owns its own reads -- but only the run this
    # session opened. A shared pointer outlives its run, and honouring one
    # would turn the survey gate off for every session after it.
    runs = Path(STATE) / "design-runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "current-checklist.json").write_text("{}")
    code, _ = run("guard-probe", probe_event(transcript(sweep()),
                                             session="checklist"))
    check("a run the session owns is left alone", code, 0)
    (runs / "current-checklist.json").unlink()

    (runs / "current.json").write_text("{}")
    code, _ = run("guard-probe", probe_event(transcript(sweep()),
                                             session="unrelated"))
    check("a stale shared pointer is not an off switch", code, 2)
    (runs / "current.json").unlink()

    # A window that never reaches the boundary cannot be counted.
    check("no boundary, no judgment",
          mod.current_turn(transcript(sweep()), limit=200), None)

    # The spam edge.
    code, out = run("guard-agent", {
        "tool_name": "Agent",
        "tool_input": {"prompt": "Read %s and tell me what it does." % TARGET}})
    check("an agent sent after one file is refused", code, 2)
    check("the refusal names the file", str(TARGET) in out, True)

    code, _ = run("guard-agent", {"tool_name": "Agent", "tool_input": {
        "prompt": "Sweep every repository under the development tree and report "
                  "which ones carry a workflow file whose job name is not check, "
                  "naming the repository and the job it declares instead of it."}})
    check("a real brief passes", code, 0)

    code, _ = run("guard-agent", {"tool_name": "Agent", "tool_input": {
        "prompt": "Find where the retry budget is set."}})
    check("a short brief naming no file passes", code, 0)

    # The prompt check speaks on shape and stays quiet otherwise.
    code, out = run("guard-prompt", {"prompt": "audit every repo for stale badges"})
    check("a fan-out ask is answered", "additionalContext" in out, True)
    check("the prompt check never blocks", code, 0)

    code, out = run("guard-prompt", {"prompt": "fix the typo on line 12 of this file"})
    check("a narrow ask is left alone", out.strip(), "")

    code, out = run("guard-prompt", {"prompt": "thanks"})
    check("small talk is left alone", out.strip(), "")

    if FAILURES:
        print("delegation-guard: %d case(s) failed" % len(FAILURES))
        for line in FAILURES:
            print("  " + line)
        return 1
    print("delegation-guard: all cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
