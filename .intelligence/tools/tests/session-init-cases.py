#!/usr/bin/env python3
"""Cases the session dispatcher has to get right.

The fold has to be idempotent and it has to settle: running it twice leaves the
same file, and an installer putting its own row back is folded away again on the
next sweep rather than leaving the hash moving forever. A hook naming no covered
tool survives, because a fold that ate an unrelated hook would be a worse problem
than the spawns it saves.

  session-init-cases.py        run them
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
            or Path(__file__).resolve().parent.parent / "session-init.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def tree(settings, at=None):
    """A config tree holding the given settings and a stub of every tool."""
    root = Path(tempfile.mkdtemp(dir=str(at) if at else None))
    (root / "tools").mkdir()
    (root / "scripts").mkdir()
    (root / "state").mkdir()
    shutil.copy(TOOL, root / "tools" / "session-init.py")
    (root / "settings.json").write_text(json.dumps(settings, indent=2))
    return root


def run(root, verb="run", env=None):
    p = subprocess.run([sys.executable, str(root / "tools" / "session-init.py"),
                        verb],
                       input=json.dumps({"cwd": str(root)}),
                       capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    return p.returncode, p.stdout + p.stderr


def hooks(root):
    d = json.loads((root / "settings.json").read_text())
    return {ev: [h["command"] for r in rows for h in r.get("hooks", [])]
            for ev, rows in d.get("hooks", {}).items()}


def main():
    many = {"hooks": {"SessionStart": [{"matcher": "*", "hooks": [
        {"type": "command", "command": "~/.intelligence/tools/config-sync.py"},
        {"type": "command",
         "command": "~/.intelligence/tools/chrome-guard.py install"},
        {"type": "command",
         "command": "~/.intelligence/scripts/prune-worktrees.sh"},
        {"type": "command", "command": "/usr/local/bin/somebody-elses-hook"},
    ]}], "Stop": [{"matcher": "*", "hooks": [
        {"type": "command",
         "command": "~/.intelligence/tools/plain-brief-guard.py guard-stop"},
    ]}]}}

    root = tree(many)
    run(root, "install")
    after = hooks(root)

    check("one session row", len(after["SessionStart"]), 2)
    check("the dispatcher is first",
          "session-init.py" in after["SessionStart"][0], True)

    # A tree outside the home directory has no $HOME form and keeps its path.
    check("a tree outside home keeps its own path",
          all(str(root) in c for cs in after.values() for c in cs
              if "guard-hub.py" in c or "session-init.py" in c), True)
    check("an unrelated hook survives",
          "/usr/local/bin/somebody-elses-hook" in after["SessionStart"], True)
    check("a covered installer is gone",
          any("chrome-guard" in c for c in after["SessionStart"]), False)
    check("the stop guard is folded into the hub",
          any("plain-brief-guard" in c for c in after["Stop"]), False)
    check("every event has a dispatcher",
          sorted(after), ["PostToolUse", "PreToolUse", "SessionStart", "Stop",
                          "UserPromptSubmit"])

    # Running it again changes nothing.
    before = (root / "settings.json").read_text()
    run(root, "install")
    check("fold is idempotent", (root / "settings.json").read_text(), before)

    # An installer that puts its own row back is folded away on the next sweep,
    # and the recorded hash follows the fold rather than the installer.
    d = json.loads((root / "settings.json").read_text())
    d["hooks"]["SessionStart"].append({"matcher": "*", "hooks": [
        {"type": "command",
         "command": "~/.intelligence/tools/chrome-guard.py install"}]})
    (root / "settings.json").write_text(json.dumps(d, indent=2))
    run(root, "run")
    check("a re-added row is folded away",
          any("chrome-guard" in c for c in hooks(root)["SessionStart"]), False)

    code, out = run(root, "status")
    check("status settles after the sweep",
          "wiring unchanged" in out, True)

    # A tree under the home directory is wired in the guarded form the sync
    # normalises to. An absolute path there is rewritten on every session, which
    # moves the settings hash and runs the installers this dispatcher skips.
    under = Path(tempfile.mkdtemp(dir=Path.home()))
    try:
        home_tree = tree(many, at=under)
        run(home_tree, "install")
        wired = hooks(home_tree)
        mine = [c for cs in wired.values() for c in cs
                if "guard-hub.py" in c or "session-init.py" in c]
        check("every dispatcher row is wired", len(mine), 5)
        check("each is in the guarded form",
              all(c.startswith('[ -e "$HOME/') and 'exec "$HOME/' in c
                  for c in mine), True)
        check("none names the home directory in full",
              any(str(Path.home()) in c for c in mine), False)
    finally:
        shutil.rmtree(under, ignore_errors=True)

    # A tree whose settings never move never runs the installers again.
    code, out = run(root, "run")
    check("a settled tree runs no installer", code, 0)

    for f in FAILURES:
        print(f)
    print(f"session-init: {len(FAILURES)} failing")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
