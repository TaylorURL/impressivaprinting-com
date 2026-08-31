#!/usr/bin/env python3
"""Cases for the two decisions the in-session refresh makes before it clones.

Both of them fail silently when they are wrong, and both failed silently on a
container that then ran three days behind the mirror. The first is whether the
working directory is a repository carrying its own vendored copy: the setup
installs the config into every home, so a sibling home has the shape of one
without being one, and the script's own reassuring line prints either way. The
second is whether a previous refresh still stands: a container outlives the
session it was built for, so existence alone freezes it forever while age lets
a burst of resumes inside one session still skip.

Neither case fetches anything. The subject is run with no credentials and no
route to the Pi, so every method it tries is refused and it says so, which is
what tells a case that the two decisions above let it through.

  scripts-cloud-refresh-cases.py        run them
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent.parent
              / "scripts" / "cloud-refresh.sh")

FAILURES = []

VENDORED = "vendored"      # exited saying the repository carries the skills
REFRESHED = "reached"      # got as far as trying to fetch
SKIPPED = "skipped"        # a recent refresh still stands


def refused_fetch():
    """A PATH entry that turns every route to the mirror into a refusal.

    The Mac this runs on reaches the Pi over its own ssh agent and a resolvable
    host name, so the subject's first route succeeds here and rsyncs the whole
    mirror into the fixture home -- four times a run, over the network, for a
    verdict about two decisions taken before any of it. Stubbing ssh, rsync and
    gh makes the three that shell out fail at once; GIT_ALLOW_PROTOCOL below
    refuses https to the two git clones without a packet leaving the machine.
    Only `git rev-parse`, which the vendored check runs against a local
    fixture, is left alone.
    """
    stubs = Path(tempfile.mkdtemp()) / "bin"
    stubs.mkdir(parents=True)
    for name in ("ssh", "rsync", "gh"):
        stub = stubs / name
        stub.write_text("#!/bin/sh\necho 'refused by the fixture' >&2\nexit 255\n")
        stub.chmod(0o755)
    return stubs


STUBS = refused_fetch()


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def home_with_config(root):
    """A home holding an installed copy, which is what the script refreshes."""
    home = root / "home"
    (home / ".intelligence" / "skills").mkdir(parents=True)
    (home / ".intelligence" / "INTELLIGENCE.md").write_text("x\n")
    return home


def gates_under(base):
    gates = base / "checklists" / "design" / "checklist" / "gates"
    gates.mkdir(parents=True)
    (gates / "10-a.json").write_text("{}\n")


def run(project, home, mark_age_minutes=None):
    """Run the subject and say which of its three exits it took."""
    if mark_age_minutes is not None:
        mark = home / ".intelligence" / ".cloud-refresh"
        mark.write_text("2026-08-25T21:26:55Z\n")
        when = time.time() - mark_age_minutes * 60
        os.utime(mark, (when, when))

    env = dict(os.environ)
    env.update(CLAUDE_CODE_REMOTE="true", HOME=str(home), GH_TOKEN="",
               GITHUB_TOKEN="", PATH=f"{STUBS}:/usr/bin:/bin",
               GIT_ALLOW_PROTOCOL="file")
    env.pop("CLAUDE_PROJECT_DIR", None)
    out = subprocess.run(["bash", str(TARGET)], cwd=str(project), env=env,
                         capture_output=True, text=True).stdout
    if "Skills come from this repository" in out:
        return VENDORED
    # Reaching the fetch is the assertion, and it reads the same whether the
    # fetch then succeeds or is refused. Keying on one method's refusal would
    # tie these cases to whichever route happens to run last.
    for reached in ("every clone method failed", "intelligence: cloned via",
                    "intelligence refreshed in-session"):
        if reached in out:
            return REFRESHED
    return SKIPPED


def main():
    # A sibling home directory carries the same shape as a vendored copy and is
    # not one. Reading it as one is what stopped the refresh for three days.
    root = Path(tempfile.mkdtemp())
    home = home_with_config(root)
    other = root / "user"
    (other / ".intelligence").mkdir(parents=True)
    gates_under(other / ".intelligence")
    check("a sibling home is not a vendored copy", run(other, home), REFRESHED)

    # A real one is a git repository, and it says so with VENDOR.md.
    root = Path(tempfile.mkdtemp())
    home = home_with_config(root)
    repo = root / "repo"
    (repo / ".intelligence").mkdir(parents=True)
    (repo / ".intelligence" / "VENDOR.md").write_text("installed copy\n")
    gates_under(repo / ".intelligence")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    check("a checked-in copy stands", run(repo, home), VENDORED)

    # VENDOR.md without a repository around it is still not one.
    root = Path(tempfile.mkdtemp())
    home = home_with_config(root)
    loose = root / "loose"
    (loose / ".intelligence").mkdir(parents=True)
    (loose / ".intelligence" / "VENDOR.md").write_text("installed copy\n")
    gates_under(loose / ".intelligence")
    check("a copy outside a repository does not stand", run(loose, home), REFRESHED)

    # A resume minutes into a session finds the marker and leaves it alone.
    root = Path(tempfile.mkdtemp())
    home = home_with_config(root)
    plain = root / "plain"
    plain.mkdir()
    check("a fresh marker skips the refresh", run(plain, home, 5), SKIPPED)

    # A run a day later does not, which is the whole point of reading its age.
    root = Path(tempfile.mkdtemp())
    home = home_with_config(root)
    plain = root / "plain"
    plain.mkdir()
    check("a day-old marker refreshes anyway", run(plain, home, 60 * 24), REFRESHED)

    # No marker at all is the first run in a container.
    root = Path(tempfile.mkdtemp())
    home = home_with_config(root)
    plain = root / "plain"
    plain.mkdir()
    check("no marker refreshes", run(plain, home), REFRESHED)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
