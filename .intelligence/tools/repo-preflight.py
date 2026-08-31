#!/usr/bin/env python3
"""Refuse to build or land from a repo checkout when a sibling checkout is newer or dirty.

A machine can hold several clones of one repo. Work done in one is invisible to the others:
git reads clean, the remote shows nothing, and a build from the wrong clone silently ships
stale code over newer work. This scans the usual project roots for every checkout sharing
the target's origin, compares working-tree state and declared versions, and exits nonzero
when the target is not the place to build from.

Usage: repo-preflight.py [repo-dir]        (default: cwd)
       repo-preflight.py --all             every repo on the machine, held once or not
Exit:  0 = clear to proceed; 1 = a sibling checkout is dirty or ahead — reconcile first.
"""

import os
import re
import subprocess
import sys

# Where a second clone of a repo would plausibly be sitting.
#
# The three bare-home roots are what this machine used before development moved
# under ~/Development, and none of them has existed here since. A scan whose
# roots do not exist finds no siblings and prints `clear to proceed` every time,
# which is the same answer it gives when there genuinely is no duplicate -- so
# the guard against holding a repo twice read as passing for as long as it was
# pointed at nothing. They stay in the list because other machines still use
# them; ~/Development and its two subdirectories are what answer here.
ROOTS = [
    os.path.expanduser("~/Development"),
    os.path.expanduser("~/Development/IdeaProjects"),
    os.path.expanduser("~/Development/WebstormProjects"),
    os.path.expanduser("~/IdeaProjects"),
    os.path.expanduser("~/WebstormProjects"),
    os.path.expanduser("~/Projects"),
]

# A worktree is a second checkout of the same origin and would answer every test
# below as a rival clone, so an open worktree would block every landing made
# from it. They are excluded by the directory they live in rather than by
# reading .git, because that is true of a worktree whatever state it is in.
WORKTREES = "worktrees"


def git(cwd, *args):
    try:
        out = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def origin_of(path):
    url = git(path, "remote", "get-url", "origin")
    return url.rstrip("/").removesuffix(".git") if url else None


def version_of(path):
    for probe, pattern in (("gradle.properties", r"^version=(.+)$"),
                          ("package.json", r'"version"\s*:\s*"([^"]+)"')):
        f = os.path.join(path, probe)
        if os.path.isfile(f):
            m = re.search(pattern, open(f).read(), re.M)
            if m:
                return m.group(1).strip()
    return None


def version_tuple(v):
    # Every digit run in order, so 2026.32.48 and 1.4.2 both compare sensibly
    # without knowing which scheme a repo uses. A pre-release suffix contributes
    # its own digits, which makes 1.2.3-rc1 sort above 1.2.3 — wrong in theory,
    # harmless here, because this only ever compares two checkouts of one repo
    # and the answer it drives is "reconcile first".
    return tuple(int(x) for x in re.findall(r"\d+", v or "0")) or (0,)


def dirty_count(path):
    out = git(path, "status", "--porcelain")
    return len([l for l in (out or "").splitlines() if l.strip()])


def describe(path):
    return {
        "path": path,
        "branch": git(path, "branch", "--show-current") or "(detached)",
        "dirty": dirty_count(path),
        "version": version_of(path),
        "head": (git(path, "rev-parse", "--short", "HEAD") or "?"),
    }


def every_checkout():
    """Every git checkout under the roots, worktrees excluded, deduplicated.

    A root can be a parent of another root, so the same path is reachable twice
    and would otherwise be reported as its own sibling.
    """
    seen, found = set(), []
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if name == WORKTREES:
                continue
            path = os.path.join(root, name)
            if not os.path.isdir(os.path.join(path, ".git")):
                continue
            real = os.path.realpath(path)
            if real in seen:
                continue
            seen.add(real)
            found.append(path)
    return found


def find_checkouts(target_origin, target_real):
    return [p for p in every_checkout()
            if origin_of(p) == target_origin
            and os.path.realpath(p) != target_real]


def held_twice():
    """Every origin this machine holds more than one checkout of.

    One repo, one checkout is the rule; this is the sweep that answers it for
    the whole machine rather than for the repo somebody happens to be standing
    in. A duplicate is reported with both paths, because which one to keep is
    a judgment about which holds the work.
    """
    by_origin = {}
    for path in every_checkout():
        origin = origin_of(path)
        if origin:
            by_origin.setdefault(origin, []).append(path)
    return {o: paths for o, paths in by_origin.items() if len(paths) > 1}


def sweep():
    """The whole machine: how many repos, and which are held twice."""
    total = len(every_checkout())
    doubled = held_twice()
    if not doubled:
        print(f"{total} checkout(s), each repo held once")
        return 0
    for origin, paths in sorted(doubled.items()):
        print(f"{origin} is held {len(paths)} times:")
        for path in paths:
            c = describe(path)
            print(f"  {path} (branch {c['branch']} @ {c['head']}, "
                  f"{c['dirty']} dirty file(s))")
    print(f"{len(doubled)} repo(s) held more than once")
    return 1


def main():
    if "--all" in sys.argv[1:]:
        return sweep()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    target = os.path.realpath(args[0] if args else os.getcwd())
    origin = origin_of(target)
    if not origin:
        print(f"repo-preflight: {target} is not a git checkout with an origin remote")
        return 1

    me = describe(target)
    siblings = [describe(p) for p in find_checkouts(origin, target)]

    print(f"repo-preflight: {origin}")
    for c in [me] + siblings:
        tag = "TARGET " if c["path"] == target else "sibling"
        print(f"  {tag} {c['path']}")
        print(f"          branch {c['branch']} @ {c['head']}, version {c['version']}, "
              f"{c['dirty']} dirty file(s)")

    problems = []
    for c in siblings:
        if c["dirty"] > 0:
            problems.append(f"{c['path']} has {c['dirty']} uncommitted file(s) — that work is "
                            "invisible from here and a build would ship without it")
        if version_tuple(c["version"]) > version_tuple(me["version"]):
            problems.append(f"{c['path']} declares version {c['version']} > {me['version']} — "
                            "the target checkout is stale")

    if problems:
        print("\nBLOCKED — reconcile before building or landing from this checkout:")
        for p in problems:
            print(f"  - {p}")
        return 1

    if me["dirty"] > 0:
        print(f"\nnote: the target tree itself has {me['dirty']} uncommitted file(s); "
              "the build will carry them.")
    print("clear to proceed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
