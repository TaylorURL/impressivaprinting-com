#!/usr/bin/env python3
"""Cases the push flow guard has to get right.

A push at develop or main is refused however it is spelled: named on the line,
named through a refspec, or left implicit by the branch HEAD is on. A push at a
feature branch is the flow working and passes, and so do the pushes that are not
branch updates at all. The implicit case runs against a real repository, because
that is the only way the branch lookup is exercised.

  push-flow-guard-cases.py        run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "push-flow-guard.py")

FAILURES = []


def run(command, cwd=None, env=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    if cwd:
        payload["cwd"] = cwd
    p = subprocess.run([sys.executable, str(TARGET), "guard-bash"],
                       input=json.dumps(payload), capture_output=True,
                       text=True, env={**os.environ, **(env or {})})
    return p.returncode


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got}, want {want}")


def repo_on(branch):
    """A repository with one commit, sitting on the named branch."""
    d = tempfile.mkdtemp()
    q = {"capture_output": True, "cwd": d}
    subprocess.run(["git", "init", "-q", "-b", branch], **q)
    subprocess.run(["git", "-c", "user.email=t@example.com",
                    "-c", "user.name=T", "commit", "-q", "--allow-empty",
                    "-m", "base"], **q)
    return d


def repo_with_remotes(origin_url, **others):
    """A repository whose remotes point where the test says."""
    d = tempfile.mkdtemp()
    q = {"capture_output": True, "cwd": d}
    subprocess.run(["git", "init", "-q", "-b", "main"], **q)
    subprocess.run(["git", "remote", "add", "origin", origin_url], **q)
    for name, url in others.items():
        subprocess.run(["git", "remote", "add", name, url], **q)
    return d


def main():
    check("push develop by name", run("git push origin develop"), 2)
    check("push main by name", run("git push origin main"), 2)
    check("push a refspec at develop",
          run("git push origin HEAD:develop"), 2)
    check("push a full ref at main",
          run("git push origin HEAD:refs/heads/main"), 2)
    check("force push at main", run("git push --force origin main"), 2)

    # A second remote is a build host, not the repository the flow lives in.
    # deploy-remote-sync.py mirrors main onto it on every promotion, carrying
    # commits a pull request and the required check already passed on origin.
    mirror = repo_with_remotes("https://github.com/Owner/thing.git",
                               upstream="https://github.com/Other/thing.git")
    check("mirroring main onto a deploy remote is not a direct push",
          run("git push upstream origin/main:refs/heads/main", cwd=mirror), 0)
    check("the same push at origin is still refused",
          run("git push origin origin/main:refs/heads/main", cwd=mirror), 2)
    check("a second remote pointing back at origin is still origin",
          run("git push twin main",
              cwd=repo_with_remotes("https://github.com/Owner/thing.git",
                                    twin="https://github.com/Owner/thing.git")), 2)
    check("an unknown remote is treated as origin",
          run("git push nowhere main", cwd=mirror), 2)

    # The payload names the session's directory; a command that cd's elsewhere
    # runs somewhere else entirely, and the remote has to be read there.
    check("a cd in the command is followed when reading the remote",
          run("cd %s && git push upstream origin/main:refs/heads/main" % mirror,
              cwd=os.path.expanduser("~")), 0)
    check("a cd does not excuse a push at origin",
          run("cd %s && git push origin main" % mirror,
              cwd=os.path.expanduser("~")), 2)
    check("a cd on its own line is followed too",
          run("export FOO=1\ncd %s\ngit push upstream origin/main:refs/heads/main" % mirror,
              cwd=os.path.expanduser("~")), 0)

    check("push a feature branch",
          run("git push -u origin fix/admin-timeout"), 0)
    check("push a branch whose name ends in main",
          run("git push origin feature-main-nav"), 0)
    check("a tag push", run("git push origin --tags"), 0)
    check("a branch delete", run("git push origin --delete stale"), 0)
    check("not a push at all", run("git status"), 0)
    check("the word push elsewhere", run("npm run push-docs"), 0)

    on_develop = repo_on("develop")
    on_feature = repo_on("fix/thing")
    check("bare push while on develop",
          run("git push", cwd=on_develop), 2)
    check("push origin while on develop",
          run("git push origin", cwd=on_develop), 2)
    check("bare push while on a feature branch",
          run("git push", cwd=on_feature), 0)

    check("guard off", run("git push origin main",
                           env={"INTELLIGENCE_ALLOW_DIRECT_PUSH": "1"}), 0)

    for f in FAILURES:
        print(f)
    print(f"push-flow-guard: {len(FAILURES)} failing")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
