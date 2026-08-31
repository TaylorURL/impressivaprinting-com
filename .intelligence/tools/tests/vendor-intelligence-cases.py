#!/usr/bin/env python3
"""Cases the vendoring tool has to get right about what a copy is meant to hold.

Three of its decisions are invisible until they are wrong somewhere else. What a
repo declares it does not carry decides whether `check` can ever say current, and
a tool that cannot read the declaration refuses every commit in a curated repo
with no action that clears it. The name a repo answers to decides whether the
self-hosted and no-code lists recognise it, and a worktree is named for the work
rather than for the repo. The mode on a copied file decides whether two machines
flip the same permission bits back and forth on every landing.

  vendor-intelligence-cases.py    run them
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "vendor-intelligence.py")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def source_tree(root):
    """A stand-in for ~/.intelligence holding one skill, one tool, one script."""
    (root / "skills" / "keep").mkdir(parents=True)
    (root / "skills" / "keep" / "SKILL.md").write_text("kept\n")
    (root / "skills" / "drop").mkdir(parents=True)
    (root / "skills" / "drop" / "SKILL.md").write_text("dropped\n")
    (root / "tools").mkdir(parents=True)
    (root / "tools" / "runme.py").write_text("#!/usr/bin/env python3\nx = 1\n")
    (root / "tools" / "plain.md").write_text("not run\n")
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "hook.sh").write_text("#!/bin/sh\ntrue\n")
    return root


def repo_with(root, install_sh=None):
    """A git checkout with an origin URL, and optionally a declaration in it."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin",
                    "https://github.com/TaylorURL/tiretracker.git"], check=True)
    (root / ".intelligence").mkdir(exist_ok=True)
    if install_sh is not None:
        (root / ".intelligence" / "install.sh").write_text(install_sh)
    return root


DECLARATION = """#!/usr/bin/env bash
SKILL_EXCLUDES=(
    --exclude 'drop'
)
EXCLUDES=(
    --exclude 'plain.*'
)
"""


def case_reads_declaration():
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        repo = repo_with(Path(tmp) / "repo", DECLARATION)
        return sorted(mod.declared_exclusions(repo)) == ["drop", "plain.*"]


def case_no_declaration_is_empty():
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        repo = repo_with(Path(tmp) / "repo")
        return mod.declared_exclusions(repo) == frozenset()


def case_declared_names_match_as_globs():
    mod = load()
    dropped = frozenset({"drop", "plain.*"})
    return (mod.declared_drop(Path("drop/SKILL.md"), dropped)
            and mod.declared_drop(Path("plain.md"), dropped)
            and not mod.declared_drop(Path("keep/SKILL.md"), dropped))


def case_declaration_changes_the_digest():
    """A declared omission has to move the stamp, or a curated copy never agrees."""
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        mod.INTELLIGENCE = source_tree(Path(tmp) / "src")
        whole = mod.source_digest()
        curated = mod.source_digest(frozenset({"drop"}))
        return whole != curated and curated == mod.source_digest(frozenset({"drop"}))


def case_name_comes_from_the_remote():
    """A worktree is named for the work; the repo it hangs off is in the remote."""
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        repo = repo_with(Path(tmp) / "daily-maintenance")
        return mod.repo_name_of(repo) == "tiretracker"


def case_mode_comes_from_the_shebang():
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        src = source_tree(Path(tmp) / "src")
        os.chmod(src / "tools" / "runme.py", 0o644)
        os.chmod(src / "tools" / "plain.md", 0o755)
        dst = Path(tmp) / "dst"
        mod.copy_tree(src / "tools", dst)
        return ((dst / "runme.py").stat().st_mode & 0o777 == 0o755
                and (dst / "plain.md").stat().st_mode & 0o777 == 0o644)


def case_declared_files_are_not_copied():
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        src = source_tree(Path(tmp) / "src")
        dst = Path(tmp) / "dst"
        mod.copy_tree(src / "skills", dst, dropped=frozenset({"drop"}))
        return (dst / "keep" / "SKILL.md").is_file() and not (dst / "drop").exists()


def case_unfinished_skill_does_not_travel():
    """A directory with no SKILL.md is a skill somebody is still writing."""
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        src = source_tree(Path(tmp) / "src")
        (src / "skills" / "half-written" / "checklist").mkdir(parents=True)
        (src / "skills" / "half-written" / "checklist" / "gates.json").write_text("{}\n")
        mod.INTELLIGENCE = src
        excluded = mod.skill_excludes()
        dst = Path(tmp) / "dst"
        mod.copy_tree(src / "skills", dst, skip_names=excluded)
        return ("half-written" in excluded
                and not (dst / "half-written").exists()
                and (dst / "keep" / "SKILL.md").is_file())


CASES = [
    ("a skill directory with no SKILL.md does not travel",
     case_unfinished_skill_does_not_travel),
    ("the declaration in install.sh is what a repo says it leaves out",
     case_reads_declaration),
    ("a repo with no declaration leaves nothing out", case_no_declaration_is_empty),
    ("declared names match the top-level entry, as globs",
     case_declared_names_match_as_globs),
    ("a declared omission moves the stamp and moves it the same way twice",
     case_declaration_changes_the_digest),
    ("a repo answers to its remote's name, not its directory's",
     case_name_comes_from_the_remote),
    ("the executable bit is derived from the shebang, not carried over",
     case_mode_comes_from_the_shebang),
    ("a declared omission is not written into the copy",
     case_declared_files_are_not_copied),
]


def main():
    bad = 0
    for name, case in CASES:
        try:
            ok = bool(case())
        except Exception as err:                       # noqa: BLE001
            print("    raised %s" % err)
            ok = False
        bad += not ok
        print("%s  %s" % ("pass" if ok else "FAIL", name))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
