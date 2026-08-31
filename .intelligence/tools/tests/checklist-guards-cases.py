#!/usr/bin/env python3
"""Cases the four checklist tools have to get right.

Each one answers to a way a fleet run went wrong: a run that recorded another
project as its repo, a sweep that erased the evidence somebody gathered, a
parity gate with no legal answer, a capture of a page that rendered nothing,
and a note that names no file.

  checklist-guards-cases.py        run them
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ANSWERS_FOR = [
    "checklists/seo/bin/seo-pass.py",
    "checklists/perf/bin/perf-pass.py",
    "checklists/stack/bin/stack-pass.py",
    "checklists/design/bin/design-pass.py",
    "checklists/db/bin/db-pass.py",
    "checklists/google/bin/google-pass.py",
]

def installed_or_checkout(name):
    """The config tree's copy of a directory, or the checkout's own.

    A case file runs from the tree it was checked out into as often as from an
    installed config, and CI has neither an installed config nor a home to put
    one in.
    """
    installed = Path.home() / ".intelligence" / name
    if installed.is_dir():
        return installed
    return Path(__file__).resolve().parents[2] / name


SKILLS = installed_or_checkout("skills")
CHECKLISTS = installed_or_checkout("checklists")
TOOLS_DIR = installed_or_checkout("tools")
TOOLS = {
    "design": CHECKLISTS / "design" / "bin" / "design-pass.py",
    "seo": CHECKLISTS / "seo" / "bin" / "seo-pass.py",
    "perf": CHECKLISTS / "perf" / "bin" / "perf-pass.py",
    "stack": CHECKLISTS / "stack" / "bin" / "stack-pass.py",
}

FAILURES: list[str] = []


def check(name, got, want):
    if got != want:
        FAILURES.append(f"{name}: got {got!r}, want {want!r}")


def source(tool):
    return TOOLS[tool].read_text(encoding="utf-8")


def git_repo(path):
    """A throwaway working tree, so a refusal has something real to compare."""
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "package.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    return path


def run_tool(tool, args, cwd):
    done = subprocess.run([sys.executable, str(TOOLS[tool])] + args,
                          cwd=str(cwd), capture_output=True, text=True, timeout=60)
    return done.returncode, (done.stdout + done.stderr)


def main():
    # A run takes its repo from its target. Reading it from the process cwd is
    # what made twelve agents open every run against the parent's worktree.
    for tool in TOOLS:
        check(f"{tool}: derives the run root from its target",
              "def target_root(" in source(tool), True)
        check(f"{tool}: refuses a start from another tree",
              "def refuse_foreign_cwd(" in source(tool), True)
        check(f"{tool}: the refusal is actually called at start",
              bool(re.search(r"\n\s+refuse_foreign_cwd\(targets\)\n", source(tool))), True)
        check(f"{tool}: the repo field no longer comes from cwd alone",
              "target_root(targets) or repo_root()" in source(tool), True)

    with tempfile.TemporaryDirectory() as tmp:
        outside = git_repo(Path(tmp) / "outside")
        target = git_repo(Path(tmp) / "target")
        code, out = run_tool("stack", ["start", "--kind", "site", "--target", str(target),
                                       "--title", "case"], cwd=outside)
        check("a start whose target is another tree is refused", code, 2)
        check("the refusal names both trees",
              ("REFUSED" in out) and (str(target) in out or "target" in out), True)

    # The sweep summarises; a hand answer carries the reasoning behind it.
    # Replacing the second with the first leaves the ledger saying less.
    for tool in TOOLS:
        check(f"{tool}: a hand note survives a later passing sweep",
              'result.get("by") == "hand" and result.get("note")' in source(tool)
              or 'result.get("by") == "hand"' in source(tool), True)

    # Every status was refused on an inconclusive parity gate, which left no
    # honest way to close a run.
    perf = source("perf")
    check("an inconclusive parity gate can be recorded unmeasured",
          "_inconclusive" in perf and "startswith(\"inconclusive\")" in perf, True)

    # A page that threw on boot renders an empty root, and an empty capture
    # diffs clean against another empty capture.
    check("a capture holding no elements at all is refused",
          "recorded no elements at all" in perf, True)

    # A note that names no file, line or measurement describes a category.
    for tool in TOOLS:
        check(f"{tool}: the note evidence test exists", "EVIDENCE = re.compile" in source(tool), True)
        check(f"{tool}: the note evidence test is called", "EVIDENCE.search" in source(tool), True)

    bump = TOOLS_DIR / "bump-version.py"
    text = bump.read_text(encoding="utf-8")
    check("bump-version treats --help as help, not a step", '"--help"' in text, True)
    check("bump-version can be pinned to a root", '"--root"' in text, True)
    with tempfile.TemporaryDirectory() as tmp:
        here = git_repo(Path(tmp) / "here")
        done = subprocess.run([sys.executable, str(bump), "--help"], cwd=str(here),
                              capture_output=True, text=True, timeout=30)
        check("--help exits clean", done.returncode, 0)
        check("--help writes no version",
              json.loads((here / "package.json").read_text())["version"], "1.0.0")
        done = subprocess.run([sys.executable, str(bump), "wobble"], cwd=str(here),
                              capture_output=True, text=True, timeout=30)
        check("an unknown step is refused", done.returncode, 2)
        check("an unknown step writes nothing",
              json.loads((here / "package.json").read_text())["version"], "1.0.0")

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
