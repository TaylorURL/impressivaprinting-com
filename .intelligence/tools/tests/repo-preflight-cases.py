#!/usr/bin/env python3
"""Cases the repo preflight has to get right.

The preflight exists for one failure: a machine holds two clones of a repo,
work lands in one, and a build runs from the other. So these fix both edges of
every reading it takes — a dirty or version-ahead sibling blocks, a clean or
behind one stays clear, and a checkout the scan must not count (the target
itself, a symlink onto it, a clone outside the scanned roots) never blocks.

The scan roots come from HOME at import, so every run here gets a temp HOME
and every fixture lives inside it; nothing touches a real project root.

  repo-preflight-cases.py        run them
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
              or Path(__file__).resolve().parent.parent / "repo-preflight.py")

# Origins never leave the string the fixture sets: the preflight only ever
# reads `remote get-url`, so an unreachable host proves no network is used.
ORIGIN = "https://example.invalid/owner/app"

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_q(cwd, *args):
    r = subprocess.run(["git", "-C", str(cwd),
                        "-c", "user.email=cases@example.invalid",
                        "-c", "user.name=Cases",
                        "-c", "commit.gpgsign=false", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} in {cwd}: {r.stderr.strip()}")


def make_checkout(home, rel, origin=ORIGIN, version=None,
                  manifest="package.json", dirty=False):
    """One committed checkout under the temp HOME, optionally dirty."""
    path = Path(home) / rel
    path.mkdir(parents=True)
    git_q(path, "init", "-q")
    git_q(path, "remote", "add", "origin", origin)
    (path / "README.md").write_text("app\n")
    if version is not None:
        if manifest == "package.json":
            (path / manifest).write_text(json.dumps({"name": "app", "version": version}))
        else:
            (path / manifest).write_text(f"version={version}\n")
    git_q(path, "add", "-A")
    git_q(path, "commit", "-q", "-m", "seed")
    if dirty:
        (path / "scratch.txt").write_text("wip\n")
    return path


def run_pf(home, target):
    # HOME is what the preflight expands its scan roots from, so pointing it at
    # the temp tree is what keeps the scan off the machine's real checkouts.
    # A fixture outside that tree would put a live project root in scope, so
    # every path is proven inside before the run.
    for p in (home, target):
        assert str(Path(p).resolve()).startswith(str(Path(home).resolve().parent)), \
            f"escaped the temp tree: {p}"
    env = dict(os.environ, HOME=str(home))
    p = subprocess.run([sys.executable, str(TARGET), str(target)],
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def main():
    # A directory with no origin is not a checkout the preflight can vouch for.
    with tempfile.TemporaryDirectory() as tmp:
        bare_dir = Path(tmp) / "IdeaProjects" / "app"
        bare_dir.mkdir(parents=True)
        code, out = run_pf(tmp, bare_dir)
        check("non-git dir refused", code, 1)
        check("non-git dir named", "not a git checkout" in out, True)

        no_remote = Path(tmp) / "IdeaProjects" / "loose"
        no_remote.mkdir()
        git_q(no_remote, "init", "-q")
        code, out = run_pf(tmp, no_remote)
        check("origin-less checkout refused", code, 1)

    # A lone clean checkout is clear, and the scan does not count the target
    # as its own sibling even though it sits inside a scanned root.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", version="1.0.0")
        code, out = run_pf(tmp, me)
        check("lone clean checkout clear", code, 0)
        check("clear is said", "clear to proceed" in out, True)
        check("target not doubled", out.count(str(me)), 1)

    # The target's own dirt is a note, never a block.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", version="1.0.0", dirty=True)
        code, out = run_pf(tmp, me)
        check("dirty target still clear", code, 0)
        check("dirty target noted", "uncommitted" in out, True)

    # A clean sibling at the same version is exactly the state two synced
    # clones sit in, and it stays clear.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", version="1.0.0")
        make_checkout(tmp, "WebstormProjects/app", version="1.0.0")
        code, out = run_pf(tmp, me)
        check("clean same-version sibling clear", code, 0)
        check("sibling listed", "sibling" in out, True)

    # A dirty sibling is the invisible-work case the tool exists for.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", version="1.0.0")
        make_checkout(tmp, "WebstormProjects/app", version="1.0.0", dirty=True)
        code, out = run_pf(tmp, me)
        check("dirty sibling blocks", code, 1)
        check("block is said", "BLOCKED" in out, True)
        check("dirt is the reason", "uncommitted" in out, True)

    # A sibling declaring a newer version marks the target stale.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", version="2026.32.9")
        make_checkout(tmp, "Projects/app", version="2026.32.48")
        code, out = run_pf(tmp, me)
        check("version-ahead sibling blocks", code, 1)
        check("staleness is the reason", "stale" in out, True)

    # A sibling behind the target is the target's own past, not a rival.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", version="2.0.0")
        make_checkout(tmp, "Projects/app", version="1.9.9")
        code, out = run_pf(tmp, me)
        check("version-behind sibling clear", code, 0)

    # gradle.properties carries the version for the repos package.json does not.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", version="1.0",
                           manifest="gradle.properties")
        make_checkout(tmp, "Projects/app", version="1.1",
                      manifest="gradle.properties")
        code, out = run_pf(tmp, me)
        check("gradle version-ahead blocks", code, 1)

    # Origin matching survives a trailing .git: the same repo cloned with and
    # without the suffix is still one repo.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", origin=ORIGIN, version="1.0.0")
        make_checkout(tmp, "WebstormProjects/app", origin=ORIGIN + ".git",
                      version="1.0.0", dirty=True)
        code, out = run_pf(tmp, me)
        check(".git-suffixed origin still matches", code, 1)

    # A different origin under the same directory name is a different repo.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", version="1.0.0")
        make_checkout(tmp, "WebstormProjects/app",
                      origin="https://example.invalid/owner/other",
                      version="9.9.9", dirty=True)
        code, out = run_pf(tmp, me)
        check("unrelated repo ignored", code, 0)

    # The scan covers the three project roots and nothing else, so a clone
    # elsewhere under HOME — a worktree above all — never reads as drift.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", version="1.0.0")
        make_checkout(tmp, "worktrees/app/fix", version="9.9.9", dirty=True)
        code, out = run_pf(tmp, me)
        check("clone outside the roots invisible", code, 0)

    # A symlink onto the target resolves to the target and is not a sibling.
    with tempfile.TemporaryDirectory() as tmp:
        me = make_checkout(tmp, "IdeaProjects/app", version="1.0.0")
        (Path(tmp) / "WebstormProjects").mkdir()
        os.symlink(me, Path(tmp) / "WebstormProjects" / "app")
        code, out = run_pf(tmp, me)
        check("symlink to target clear", code, 0)
        check("symlink not listed", "sibling" in out, False)

    mod = load()

    check("version_tuple orders numerically",
          mod.version_tuple("2026.32.48") > mod.version_tuple("2026.32.9"), True)
    check("version_tuple crosses schemes",
          mod.version_tuple("1.10.0") > mod.version_tuple("1.9.9"), True)
    # A pre-release suffix contributes digits, so rc1 sorts above its release.
    # Wrong in theory, harmless for a same-repo comparison, and pinned as such.
    check("version_tuple pre-release quirk",
          mod.version_tuple("1.2.3-rc1") > mod.version_tuple("1.2.3"), True)
    check("version_tuple of nothing", mod.version_tuple(None), (0,))

    with tempfile.TemporaryDirectory() as tmp:
        # gradle.properties outranks package.json when a repo carries both.
        (Path(tmp) / "gradle.properties").write_text("version=2.0.0\n")
        (Path(tmp) / "package.json").write_text('{"version": "1.0.0"}')
        check("version_of prefers gradle", mod.version_of(tmp), "2.0.0")
        check("version_of empty dir", mod.version_of(tempfile.mkdtemp(dir=tmp)), None)

    with tempfile.TemporaryDirectory() as tmp:
        repo = make_checkout(tmp, "IdeaProjects/app",
                             origin=ORIGIN + ".git/", version="1.0.0")
        check("origin_of normalizes suffix", mod.origin_of(str(repo)), ORIGIN)
        check("dirty_count of clean tree", mod.dirty_count(str(repo)), 0)
        (repo / "a.txt").write_text("x\n")
        (repo / "README.md").write_text("changed\n")
        check("dirty_count counts every entry", mod.dirty_count(str(repo)), 2)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
