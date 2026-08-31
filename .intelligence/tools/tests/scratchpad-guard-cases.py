#!/usr/bin/env python3
"""Cases the scratchpad lane guard has to get right.

The lane is taken from the transcript because that is the only thing that
differs between two subagents sharing a session id, and the whole guard rests on
that: a lane derived from the session would give every sibling the same one and
refuse nothing. The read cases matter as much as the write cases, since the
damage in the incident was done by a read of a path a sibling had overwritten.

  scratchpad-guard-cases.py     run them
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "scratchpad-guard.py")
FAILURES = []

ROOT = ("/private/tmp/claude-501/-Users-trentontaylor/"
        "17d04815-031a-4b09-9422-58d3a9d5e6cf/scratchpad")
PROJECTS = "/Users/trentontaylor/.intelligence/projects/-Users-trentontaylor"
SESSION_DIR = PROJECTS + "/17d04815-031a-4b09-9422-58d3a9d5e6cf"
AGENT = SESSION_DIR + "/subagents/a8966e06.jsonl"
SIBLING = SESSION_DIR + "/subagents/aa141d8a.jsonl"
SESSION = SESSION_DIR + ".jsonl"


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def write(transcript, path):
    return {"tool_name": "Write", "transcript_path": transcript,
            "tool_input": {"file_path": path}}


def bash(transcript, command):
    return {"tool_name": "Bash", "transcript_path": transcript,
            "tool_input": {"command": command}}


def blocked(mod, payload):
    return mod.verdict(payload) is not None


def main():
    mod = load()

    check("an agent's lane is its own transcript",
          mod.lane_of({"transcript_path": AGENT}), "a8966e06")
    check("two siblings do not share one",
          mod.lane_of({"transcript_path": AGENT})
          == mod.lane_of({"transcript_path": SIBLING}), False)
    check("the session itself is the main lane",
          mod.lane_of({"transcript_path": SESSION}), "main")
    check("and so is a payload carrying no transcript",
          mod.lane_of({}), "main")

    # The incident: written to the shared root, read back a call later.
    check("writing the shared root is refused",
          blocked(mod, write(AGENT, ROOT + "/reporter-body.js")), True)
    check("reading it back is refused too",
          blocked(mod, bash(AGENT, "cat %s/reporter-body.js" % ROOT)), True)
    check("reaching into a sibling's lane is refused",
          blocked(mod, write(AGENT, ROOT + "/aa141d8a/reporter-body.js")), True)

    check("the agent's own lane passes",
          blocked(mod, write(AGENT, ROOT + "/a8966e06/reporter-body.js")), False)
    check("nested under its own lane passes",
          blocked(mod, write(AGENT, ROOT + "/a8966e06/deep/x.js")), False)
    check("the session's own lane passes",
          blocked(mod, write(SESSION, ROOT + "/main/notes.md")), False)
    check("a path outside the scratchpad is not this guard's business",
          blocked(mod, write(AGENT, "/Users/trentontaylor/Development/x.html")),
          False)
    check("naming the root without writing into it passes",
          blocked(mod, bash(AGENT, "ls %s" % ROOT)), False)

    # A command naming several paths is refused on the first that leaves.
    check("one bad path among good ones is still refused",
          blocked(mod, bash(AGENT, "cp %s/a8966e06/a.js %s/b.js" % (ROOT, ROOT))),
          True)

    check("the root shape is matched without the /private prefix",
          blocked(mod, write(AGENT, ROOT.replace("/private", "") + "/x.js")), True)

    # A guard walked around is a comment, so the two ways of writing the same
    # path without writing it out both close.
    check("a variable holding the root does not hide it",
          blocked(mod, bash(AGENT, "SP=%s; cat > $SP/reporter-body.js" % ROOT)),
          True)
    check("braces around the variable do not either",
          blocked(mod, bash(AGENT, "SP=%s\ncat > ${SP}/x.js" % ROOT)), True)
    check("an exported one is the same",
          blocked(mod, bash(AGENT, "export SP=%s && cp a $SP/x.js" % ROOT)), True)
    check("standing in the root is refused, since what follows lands there",
          blocked(mod, bash(AGENT, "cd %s && cat > x.js" % ROOT)), True)
    check("and standing in it through a variable too",
          blocked(mod, bash(AGENT, "SP=%s; cd $SP; ls" % ROOT)), True)
    check("standing in the caller's own lane passes",
          blocked(mod, bash(AGENT, "cd %s/a8966e06 && cat > x.js" % ROOT)), False)
    check("a variable pointing at the caller's lane passes",
          blocked(mod, bash(AGENT, "SP=%s/a8966e06; cat > $SP/x.js" % ROOT)),
          False)
    check("a variable holding something else is left alone",
          blocked(mod, bash(AGENT, "SP=/tmp/other; cat > $SP/x.js")), False)

    for failure in FAILURES:
        print("FAIL %s" % failure)
    print("scratchpad-guard: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
