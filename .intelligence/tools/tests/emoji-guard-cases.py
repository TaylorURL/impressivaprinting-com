#!/usr/bin/env python3
"""Cases the emoji guard has to get right.

Every surface the rule names is exercised: a command, a write, a filename and a
reply. The other half matters as much, because a guard that refuses ordinary
punctuation gets switched off: dashes, arrows, box drawing, accented letters and
the letterlike symbols all pass. An edit that takes an emoji out of a file it
already carries passes too, since only what a write adds is judged.

  emoji-guard-cases.py        run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "emoji-guard.py")

ROBOT = "\U0001F916"
ROCKET = "\U0001F680"
CHECK_EMOJI = "✅"
CHECK_TEXT = "✓"
FAILURES = []


def run(verb, payload, env=None):
    p = subprocess.run([sys.executable, str(TARGET), verb],
                       input=json.dumps(payload), capture_output=True,
                       text=True, env={**os.environ, **(env or {})})
    return p.returncode


def bash(command, env=None):
    return run("guard-bash", {"tool_name": "Bash",
                              "tool_input": {"command": command}}, env)


def edit(path, new, old="", env=None):
    return run("guard-edit", {"tool_name": "Edit", "tool_input": {
        "file_path": path, "new_string": new, "old_string": old}}, env)


def stop(reply, env=None):
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        fh.write(json.dumps({"type": "assistant", "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": reply}]}}) + "\n")
        path = fh.name
    try:
        return run("guard-stop", {"transcript_path": path}, env)
    finally:
        os.unlink(path)


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got}, want {want}")


def main():
    check("emoji in a command", bash(f"echo '{ROCKET} shipped'"), 2)
    check("emoji in a heredoc",
          bash(f"cat <<'EOF' > x.md\n# Notes {CHECK_EMOJI}\nEOF"), 2)
    check("plain command", bash("echo shipped"), 0)
    check("command with a dash and an arrow", bash("echo 'a -- b -> c'"), 0)
    check("command with box drawing", bash("printf '┌─┐\\n'"), 0)

    check("emoji in a write", edit("/repo/README.md", f"# Title {ROCKET}"), 2)
    check("emoji in a commit body",
          edit("/repo/.git/COMMIT_EDITMSG", f"fix: thing {CHECK_EMOJI}"), 2)
    check("plain write", edit("/repo/README.md", "# Title"), 0)
    check("accented and typographic characters",
          edit("/repo/README.md", "café — naïve – “q”"), 0)
    check("text check mark", edit("/repo/README.md", f"{CHECK_TEXT} done"), 0)

    # Taking one out is the work the rule wants; the write that removes it has
    # to pass.
    check("emoji removed", edit("/repo/README.md", "# Title",
                                f"# Title {ROCKET}"), 0)
    check("emoji already there and untouched",
          edit("/repo/README.md", f"# Title {ROCKET}\nmore",
               f"# Title {ROCKET}"), 0)

    check("emoji in a filename", edit(f"/repo/{ROCKET}-notes.md", "text"), 2)

    check("emoji in a reply", stop(f"Shipped {ROCKET}"), 2)
    check("plain reply", stop("Shipped. The check is green."), 0)
    check("reply with an em-dash", stop("Shipped — the check is green."), 0)

    # The guard's own source spells out what it refuses and is the one file
    # allowed to carry them.
    check("the guard's own source",
          edit(str(TARGET), f"EMOJI = '{ROCKET}'"), 0)

    check("guard off", bash(f"echo '{ROCKET}'",
                            {"INTELLIGENCE_ALLOW_EMOJI": "1"}), 0)

    for f in FAILURES:
        print(f)
    print(f"emoji-guard: {len(FAILURES)} failing")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
