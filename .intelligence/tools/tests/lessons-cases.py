#!/usr/bin/env python3
"""Cases the lessons tool has to get right.

The tool's whole value is the threshold. Below it every ordinary instruction
becomes a lesson and the list stops being read; above it the thing that keeps
happening never surfaces. So the cases hold both edges: one session is never a
lesson, two is, and an instruction that carries no complaint is neither however
often it appears.

The other half is the ledger not lying. A mechanism recorded against a lesson
that goes on recurring was not the fix, and a run that keeps reporting it as
settled hides the only evidence that it was wrong -- so a settled lesson seen in
more sessions than when it was settled reopens, and that is checked here.

Every fixture is a temporary directory and the state is pinned inside it through
INTELLIGENCE_STATE_DIR, so no case can write into the live ledger. No case reads
the real transcript tree.

  lessons-cases.py     run them
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
              or Path(__file__).resolve().parent.parent / "lessons.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def load(state_dir, transcripts):
    os.environ["INTELLIGENCE_STATE_DIR"] = str(state_dir)
    os.environ["INTELLIGENCE_TRANSCRIPTS"] = str(transcripts)
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def session(root, name, rows):
    """One transcript file, in the shape the harness writes them."""
    path = root / ("%s.jsonl" % name)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    return path


def said(text, sidechain=False):
    return {"type": "user", "isSidechain": sidechain,
            "message": {"content": [{"type": "text", "text": text}]},
            "timestamp": "2026-08-28T00:00:00Z"}


def refused(text):
    return {"type": "system", "hookErrors": "BLOCKED: %s" % text,
            "timestamp": "2026-08-28T00:00:00Z"}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state"
        feed = Path(tmp) / "projects"
        feed.mkdir()
        mod = load(state, feed)

        # ------------------------------------------------------ fingerprinting
        check("word order does not change the topic",
              mod.topic("never commit the vendored bundle"),
              mod.topic("the vendored bundle, never commit it"))
        check("different subjects do not collide",
              mod.topic("never commit the vendored bundle")
              == mod.topic("stop adding emoji to the changelog"), False)
        check("a turn of only stopwords has no topic", mod.topic("do the thing"), "")

        # ------------------------------------------------------- what counts
        check("a complaint is a correction",
              bool(mod.CORRECTION.search("you keep doing this, stop adding emoji")),
              True)
        check("an ordinary instruction is not",
              bool(mod.CORRECTION.search("add a portfolio entry for the new site")),
              False)
        check("a refusal is read off the marker",
              mod.BLOCKED.search("BLOCKED: the primary checkout is not a desk"
                                 ).group(1),
              "the primary checkout is not a desk")

        # --------------------------------------------------------- threshold
        session(feed, "one", [said("stop adding emoji to the changelog")])
        found = mod.harvest(30)
        check("one session is harvested", len(found), 1)
        code = mod.scan(30, 2, False)
        check("one session is not yet a lesson", len(mod.load()["lessons"]), 0)
        check("nothing outstanding exits zero", code, 0)

        session(feed, "two", [said("you keep adding emoji to the changelog")])
        mod.scan(30, 2, False)
        lessons = mod.load()["lessons"]
        check("two sessions is a lesson", len(lessons), 1)
        mark = next(iter(lessons))
        check("it counts both sessions", lessons[mark]["sessions"], 2)
        check("it opens open", lessons[mark]["status"], "open")

        # ----------------------------------------------------- what is ignored
        session(feed, "agent", [said("stop adding emoji to the changelog", True),
                                said("stop adding emoji to the changelog", True)])
        before = mod.load()["lessons"][mark]["sessions"]
        mod.scan(30, 2, False)
        check("a subagent's own prompt is not a correction",
              mod.load()["lessons"][mark]["sessions"], before)

        long_turn = "you keep doing this. " + ("word " * 400)
        session(feed, "long", [said(long_turn)])
        session(feed, "long2", [said(long_turn)])
        mod.scan(30, 2, False)
        check("a turn past the length cap is not a correction",
              len(mod.load()["lessons"]), 1)

        # -------------------------------------------------------- the ledger
        check("a mechanism has to say what it was",
              run_tool("mark", state, feed, [mark, "--as", "enforced"]).returncode, 2)
        run_tool("mark", state, feed, [mark, "--as", "enforced", "--note", "a guard"])
        check("marking settles it", mod.load()["lessons"][mark]["status"], "enforced")

        code = mod.scan(30, 2, False)
        check("a settled lesson that has not grown stays settled",
              mod.load()["lessons"][mark]["status"], "enforced")
        check("nothing outstanding exits zero", code, 0)

        session(feed, "three", [said("I told you about the emoji in the changelog")])
        code = mod.scan(30, 2, False)
        reopened = mod.load()["lessons"][mark]
        check("a mechanism that did not hold reopens the lesson",
              reopened["status"], "open")
        check("it says why", "reopened" in reopened["note"], True)
        check("anything outstanding exits non-zero", code, 1)

        check("an unknown lesson cannot be marked",
              run_tool("mark", state, feed, ["said-nothing", "--as", "declined"]
                       ).returncode, 2)

        # ------------------------------------------------------------- usage
        check("no verb is a usage error",
              run_tool("", state, feed, []).returncode, 2)
        check("an unknown verb is a usage error",
              run_tool("frobnicate", state, feed, []).returncode, 2)

    for failure in FAILURES:
        print("FAIL %s" % failure)
    print("%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


def run_tool(verb, state, feed, args):
    env = dict(os.environ)
    env["INTELLIGENCE_STATE_DIR"] = str(state)
    env["INTELLIGENCE_TRANSCRIPTS"] = str(feed)
    return subprocess.run([sys.executable, str(TARGET)]
                          + ([verb] if verb else []) + list(args),
                          capture_output=True, text=True, env=env)


if __name__ == "__main__":
    sys.exit(main())
