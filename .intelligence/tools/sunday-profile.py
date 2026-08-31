#!/usr/bin/env python3
"""Builds the Sunday profile out of the live setup, so the two cannot drift.

Sunday reads its rules from a profile directory rather than from this tree, and
the profile is the same skills, tools, scripts and checklists under the names
Sunday uses: `~/.sunday/profile` where this tree says `~/.intelligence`, and a
`SUNDAY_` environment prefix where it says `INTELLIGENCE_`. A profile written by
hand is a photograph, and a photograph of a tree that retires a skill a week
holds skills nothing else on the machine still has.

Two things in the profile are written rather than derived and are never touched
here: `gates/`, which is Sunday's own rule format and has no counterpart in this
tree, and `share.yaml`, which is the judgement about what is general enough to
hand to somebody else.

The test fixtures stay behind. A case file carrying a fake key reads as a real
one to anything scanning bytes, and the profile is the half that travels.

  sunday-profile.py build      write the profile, pruning what the live tree dropped
  sunday-profile.py check      what build would change, writing nothing
"""
from __future__ import annotations

import filecmp
import os
import re
import shutil
import sys
from pathlib import Path

HOME = Path.home()
INTELLIGENCE = Path(__file__).resolve().parent.parent
# The profile is a built tree and lives where built trees live. The home level
# carries broad directories and nothing granular, so a build that lands there
# fails the layout every hygiene sweep reads.
DEST = Path(os.environ.get("SUNDAY_PROFILE_DIR")
            or HOME / "Development" / "sunday-profile")

# Whole trees carried across under the renaming below. A checklist is its two
# declarations plus the references, gates and binaries they name, and those sit
# beside the declarations rather than in the skill that runs them, so the tree
# travels whole or the checklist arrives unable to answer its own gates.
TREES = ("skills", "standards", "tools", "scripts", "checklists")
# Written by hand in the profile, with no source in this tree.
PRESERVED = ("gates", "share.yaml")

SKIP_DIRS = {"__pycache__", ".git", "tests", "synced", "node_modules"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".bak", ".orig", ".rej", ".tmp"}

TEXT_SUFFIXES = {".py", ".sh", ".md", ".yaml", ".yml", ".json", ".txt", ".toml", ".cfg"}

# `.intelligence` only ever renames as a path component, never as the word in
# prose or in the repository's own name. The environment prefix renames wherever
# it is spelled, because nothing else carries it.
RENAMES = (
    (re.compile(r"(?<=[/\"'`~])\.intelligence\b"), ".sunday/profile"),
    (re.compile(r"\bINTELLIGENCE_(?=[A-Z])"), "SUNDAY_"),
)


def renamed(body: str) -> str:
    for pattern, replacement in RENAMES:
        body = pattern.sub(replacement, body)
    return body


def wanted(path: Path) -> bool:
    if path.suffix in SKIP_SUFFIXES:
        return False
    return not any(part in SKIP_DIRS for part in path.parts)


def sources() -> dict[str, Path]:
    """Every path the profile carries, keyed by where it lands under it."""
    found: dict[str, Path] = {}
    for tree in TREES:
        root = INTELLIGENCE / tree
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(INTELLIGENCE)
            if wanted(rel):
                found[str(rel)] = path
    return found


def rendered(path: Path) -> bytes:
    if path.suffix not in TEXT_SUFFIXES:
        return path.read_bytes()
    try:
        return renamed(path.read_text()).encode()
    except UnicodeDecodeError:
        return path.read_bytes()


def stale(dest: Path, keys: set[str]) -> list[str]:
    """Profile files with no source left in the live tree.

    A skill retired here stays in a profile nothing prunes, and Sunday loads it
    on every machine that reads the profile. Pruning is what makes a retirement
    reach the layer Sunday enforces from.
    """
    gone = []
    for path in dest.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(dest))
        if rel.split(os.sep)[0] in PRESERVED or rel in PRESERVED:
            continue
        if ".git" in Path(rel).parts:
            continue
        # Anything the build does not write and the hand-written set does not
        # claim has no source, fixtures and caches included. Holding those back
        # from the prune is what leaves a fixture in the half that travels.
        if rel not in keys:
            gone.append(rel)
    return sorted(gone)


def build(dest: Path, write: bool) -> int:
    found = sources()
    added, changed = [], []
    for rel, path in sorted(found.items()):
        target = dest / rel
        body = rendered(path)
        if not target.exists():
            added.append(rel)
        elif target.read_bytes() != body:
            changed.append(rel)
        else:
            continue
        if write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            shutil.copymode(path, target)

    gone = stale(dest, set(found))
    if write:
        for rel in gone:
            (dest / rel).unlink()
        for path in sorted(dest.rglob("*"), key=lambda p: -len(p.parts)):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()

    verb = "wrote" if write else "would write"
    for rel in added:
        print("%s %s" % ("added   " if write else "adds    ", rel))
    for rel in changed:
        print("%s %s" % ("updated " if write else "updates ", rel))
    for rel in gone:
        print("%s %s" % ("pruned  " if write else "prunes  ", rel))
    missing = [name for name in PRESERVED if not (dest / name).exists()]
    for name in missing:
        print("absent   %s (written by hand, and this build does not supply it)" % name)
    print("%s %d files: %d new, %d changed, %d pruned"
          % (verb, len(found), len(added), len(changed), len(gone)))
    return 1 if (not write and (added or changed or gone)) else 0


def main() -> int:
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else DEST
    if verb not in ("build", "check"):
        print(__doc__.strip())
        return 2
    if verb == "build":
        dest.mkdir(parents=True, exist_ok=True)
    elif not dest.is_dir():
        print("no profile at %s" % dest)
        return 1
    return build(dest, write=verb == "build")


if __name__ == "__main__":
    raise SystemExit(main())
