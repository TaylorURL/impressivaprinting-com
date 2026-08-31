#!/usr/bin/env python3
"""Cases the transcript scrub has to get right before it rewrites a transcript.

The scrub edits files the harness owns, so the failures worth fixing here are
the ones that either leave a secret behind or take something else with it.

A tool_result names the call it answers by id and never by tool name, so a run
that decides which lines to read by looking for `credential_get` in them reads
the calls and none of the answers -- which is how a first pass found seventy
values where there were a thousand. A resumed session replays earlier messages
into a new transcript, which can put the call in one file and the answer in
another, so ids are collected across every file before any of them is rewritten.
A line with no secret in it is never re-encoded, because a transcript that comes
back differently punctuated is a diff nobody asked for. And a file the harness is
still appending to is left alone: replacing it would strand the writer on the old
inode and lose whatever the session says next.

  transcript-scrub-cases.py        run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "transcript-scrub.py")
MARKER = "[credential value removed]"


def line(role, blocks):
    return json.dumps({"type": role, "message": {"role": role, "content": blocks}}) + "\n"


def call(tool_id, name="mcp__cryptofort__credential_get", args=None):
    return {"type": "tool_use", "id": tool_id, "name": name, "input": args or {"name": "k"}}


def answer(tool_id, text):
    return {"type": "tool_result", "tool_use_id": tool_id,
            "content": [{"type": "text", "text": text}]}


def run(root, action="clean"):
    out = subprocess.run([sys.executable, str(TARGET), action, "--root", str(root), "--yes"],
                         capture_output=True, text=True)
    return out.stdout + out.stderr


def bodies(root):
    return {p.name: p.read_text() for p in sorted(Path(root).glob("**/*.jsonl"))}


def case(name, build, check):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects"
        (root / "a").mkdir(parents=True)
        build(root)
        report = run(root)
        problem = check(root, report)
    if problem:
        print("FAIL %s: %s" % (name, problem))
        return 1
    print("ok   %s" % name)
    return 0


def secret_is_replaced(root):
    (root / "a" / "s.jsonl").write_text(
        line("assistant", [call("toolu_1")]) + line("user", [answer("toolu_1", "sk_live_secret")]))


def check_replaced(root, report):
    text = bodies(root)["s.jsonl"]
    if "sk_live_secret" in text:
        return "the secret is still there"
    if MARKER not in text:
        return "no marker written"
    return None


def answer_only_line(root):
    """The answer carries the id and nothing that names the tool."""
    (root / "a" / "one.jsonl").write_text(line("assistant", [call("toolu_2")]))
    (root / "a" / "two.jsonl").write_text(line("user", [answer("toolu_2", "ghp_aaaaaaaaaaaa")]))


def check_split(root, report):
    if "ghp_aaaaaaaaaaaa" in bodies(root)["two.jsonl"]:
        return "an answer in another file was missed"
    return None


def put_argument(root):
    blocks = [call("toolu_3", "mcp__cryptofort__credential_put",
                   {"name": "k", "secret": "hunter2-in-the-argument"})]
    (root / "a" / "p.jsonl").write_text(line("assistant", blocks))


def check_put(root, report):
    if "hunter2-in-the-argument" in bodies(root)["p.jsonl"]:
        return "a stored secret was left in the call that stored it"
    return None


def innocent_lines(root):
    body = (json.dumps({"type": "user", "message": {"role": "user", "content": "plain"}}) + "\n"
            + line("assistant", [call("toolu_4")])
            + line("user", [answer("toolu_4", "not found: k")]))
    (root / "a" / "keep.jsonl").write_text(body)
    (root / "a" / "keep.copy").write_text(body)


def check_untouched(root, report):
    kept = (root / "a" / "keep.jsonl").read_text()
    if kept != (root / "a" / "keep.copy").read_text():
        return "a file with no secret in it was rewritten"
    return None


def live_file(root):
    (root / "a" / "live.jsonl").write_text(
        line("assistant", [call("toolu_5")]) + line("user", [answer("toolu_5", "sk_live_live")]))
    now = time.time()
    os.utime(root / "a" / "live.jsonl", (now, now))


def check_live(root, report):
    if "sk_live_live" not in bodies(root)["live.jsonl"]:
        return "a transcript still being written was rewritten under the writer"
    if "still being written" not in report:
        return "the skipped transcript was not reported: %r" % report
    return None


def idempotent(root):
    (root / "a" / "twice.jsonl").write_text(
        line("assistant", [call("toolu_6")]) + line("user", [answer("toolu_6", "sk_live_twice")]))
    old = time.time() - 3600
    os.utime(root / "a" / "twice.jsonl", (old, old))
    run(root)


def check_idempotent(root, report):
    if "no credential values" not in report:
        return "a second run found something to do: %r" % report
    return None


def main():
    stale = lambda fn: (lambda root: (fn(root), _age(root))[0])

    def _age(root):
        old = time.time() - 3600
        for path in Path(root).glob("**/*.jsonl"):
            os.utime(path, (old, old))

    failures = 0
    failures += case("replaces a fetched secret", stale(secret_is_replaced), check_replaced)
    failures += case("finds an answer that names no tool", stale(answer_only_line), check_split)
    failures += case("replaces a secret in a put", stale(put_argument), check_put)
    failures += case("leaves everything else byte for byte", stale(innocent_lines), check_untouched)
    failures += case("leaves a live transcript alone", live_file, check_live)
    failures += case("finds nothing on a second run", idempotent, check_idempotent)
    print("%d case(s) failed" % failures if failures else "all cases pass")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
