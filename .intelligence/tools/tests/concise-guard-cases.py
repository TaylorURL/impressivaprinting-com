#!/usr/bin/env python3
"""Cases the concise guard has to get right.

The guard is worth only what it refuses, and worth nothing if it refuses a reply
that had to be long. So these fix both edges: a padded answer is caught, a short
one passes, and a turn that did real work gets the wider budget rather than the
tight one. The loop guard is fixed too, since a budget nobody can meet has to
cost one rewrite and not a session.

  concise-guard-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "concise-guard.py")

# The guard reads its off switch and both budgets from the environment, and
# settings.json carries an env block that a session exports into every process
# under it. Inherited, those three decide the verdict before the guard reads a
# word: a machine with INTELLIGENCE_CONCISE_OFF=1 set answers 0 to every case
# here, which reads as a guard that has stopped refusing. The budgets the cases
# below are written against are set here for the same reason, and this runs at
# import so the in-process load() and the subprocess runs see one environment.
os.environ.pop("INTELLIGENCE_CONCISE_OFF", None)
os.environ["INTELLIGENCE_CONCISE_ANSWER"] = "80"
os.environ["INTELLIGENCE_CONCISE_REPORT"] = "150"

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got}, want {want}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def transcript(text, used_tool):
    """A one-turn transcript ending in an assistant reply."""
    blocks = [{"type": "text", "text": text}]
    if used_tool:
        blocks.insert(0, {"type": "tool_use", "name": "Bash", "input": {}})
    rows = [
        {"type": "user", "message": {"role": "user", "content": "do the thing"}},
        {"type": "assistant", "message": {"role": "assistant", "content": blocks}},
    ]
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for r in rows:
        fh.write(json.dumps(r) + "\n")
    fh.close()
    return fh.name


def run_stop(text, used_tool, active=False):
    path = transcript(text, used_tool)
    ev = json.dumps({"transcript_path": path, "stop_hook_active": active})
    try:
        p = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                           input=ev, capture_output=True, text=True)
        return p.returncode
    finally:
        os.unlink(path)


def main():
    mod = load()
    short = "Done. Two routines: Maintenance and Error Monitor. Delete the old two yourself."
    padded = " ".join(["word"] * 200)

    check("short answer passes", run_stop(short, used_tool=False), 0)
    check("padded answer refused", run_stop(padded, used_tool=False), 2)

    # A turn that did work owes more than a turn that answered a question.
    mid = " ".join(["word"] * 120)
    check("mid-length answer refused", run_stop(mid, used_tool=False), 2)
    check("mid-length report passes", run_stop(mid, used_tool=True), 0)
    check("padded report refused", run_stop(padded, used_tool=True), 2)

    # One rewrite, never a loop.
    check("second pass lets it stand", run_stop(padded, used_tool=False, active=True), 0)

    # An empty or toolless-but-silent turn is not a reply to judge.
    check("empty reply ignored", run_stop("", used_tool=False), 0)

    check("preamble caught", bool(mod.PREAMBLE.search("Great question! The answer is 4.")), True)
    check("preamble: straight answer", bool(mod.PREAMBLE.search("Yes. Two routines remain.")), False)
    check("recap heading caught", bool(mod.RECAP.search("text\n\n## What I did\n- a\n")), True)
    check("ordinary heading kept", bool(mod.RECAP.search("text\n\n## Maintenance\n- a\n")), False)

    check("words counts tokens", mod.words("one two   three\nfour"), 4)

    # A file reproduced because it was asked for is not the reply's length.
    # Counted, no budget survives showing anyone a script.
    quoted = "Here it is.\n\n```bash\n%s\n```\n" % "\n".join(["echo word"] * 200)
    check("words: a fenced block is not spent", mod.words(quoted), 3)
    check("a reply that is mostly a quoted file passes",
          run_stop(quoted, used_tool=True), 0)
    check("prose past the budget is still refused",
          run_stop(padded + "\n\n```\ncode\n```\n", used_tool=False), 2)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
