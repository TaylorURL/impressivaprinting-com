#!/usr/bin/env python3
"""Cases the hygiene rules have to get right.

Each rule runs against a tree built for it, so what is under test is the reading
rather than this machine's current state. The exemptions carry as much weight as
the rules: a vendored config tree keeps its own layout, and the toolchain's
module cache is not a project directory, so neither is a finding.

  hygiene-check-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "hygiene-check.py")

FAILURES = []


def load():
    spec = importlib.util.spec_from_file_location("hygiene_check", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def repo(root, name, files):
    """A checkout holding the named files, all tracked."""
    path = root / name
    path.mkdir(parents=True)
    q = {"capture_output": True, "cwd": str(path)}
    subprocess.run(["git", "init", "-q"], **q)
    for rel in files:
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n")
    subprocess.run(["git", "add", "-A"], **q)
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=T",
                    "commit", "-q", "-m", "base"], **q)
    return path


def main():
    mod = load()
    root = Path(tempfile.mkdtemp())

    home = root / "home"
    for name in ("Development", "Documents", "go"):
        (home / name).mkdir(parents=True)
    (home / ".hidden-config").mkdir()
    (home / "stray-project").mkdir()
    (home / "loose.txt").write_text("x\n")
    mod.HOME = home

    check("a stray directory and a loose file are found",
          sorted(Path(p).name for p in mod.home_level()),
          ["loose.txt", "stray-project"])

    checkouts = root / "checkouts"
    repo(checkouts, "clean", ["README.md", "src/app.js"])
    repo(checkouts, "stray", ["README.md", "docs/README.md"])
    repo(checkouts, "editor", ["README.md", ".idea/workspace.xml", "app.iml"])
    repo(checkouts, "retired", ["README.md", "src/swordfun.js"])
    repo(checkouts, "vendored",
         ["README.md",
          ".intelligence/skills/design/checklist/README.md",
          ".intelligence/notes/bloodplex.md"])
    repo(checkouts, "dependency",
         ["README.md", "node_modules/left-pad/README.md"])
    mod.CHECKOUT_ROOTS = [checkouts]

    strays = mod.stray_readmes()
    check("a README below the root is found",
          any("docs/README.md" in s for s in strays), True)
    check("the root README is not a finding",
          any(s.endswith(": README.md") for s in strays), False)
    check("a vendored config tree keeps its own README",
          any("vendored" in s for s in strays), False)
    check("a dependency's README is not a finding",
          any("dependency" in s for s in strays), False)

    editor = mod.editor_config()
    check("tracked IDE config is found",
          any(".idea/workspace.xml" in e for e in editor), True)
    check("a tracked module file is found",
          any("app.iml" in e for e in editor), True)
    check("a clean repo reports nothing",
          any("clean:" in e for e in editor), False)

    retired = mod.retired_references()
    check("a retired name is found",
          any("retired" in r for r in retired), True)
    check("a retired name inside a vendored tree is not a finding",
          any("vendored" in r for r in retired), False)

    # fix untracks the editor config and leaves everything else alone.
    mod.fix()
    check("editor config is gone after a fix", mod.editor_config(), [])
    check("the stray README survives a fix",
          any("docs/README.md" in s for s in mod.stray_readmes()), True)
    check("the retired name survives a fix",
          any("retired" in r for r in mod.retired_references()), True)

    for f in FAILURES:
        print(f)
    print(f"hygiene-check: {len(FAILURES)} failing")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
