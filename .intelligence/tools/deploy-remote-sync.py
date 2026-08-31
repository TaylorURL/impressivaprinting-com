#!/usr/bin/env python3
"""Keep a repo's deploy remote level with the branch it publishes.

Some projects are hosted from a second GitHub repo rather than the one work
lands in: TireTracker's Vercel project builds `IssacMoreno14/tiretracker`
while every PR merges into `TaylorURL/tiretracker`. A promotion into `main`
therefore finishes green, reports success, and changes nothing a visitor can
see, because the host is watching a repo the merge never reached. There is
nothing local to catch it -- the merge happens on GitHub, so no pre-push hook
ever runs -- which is why it is a check rather than a hook.

`check` reports whether the deploy remote is behind; `sync` fast-forwards it.
A repo with no second remote is not a repo with a problem, so both are silent
successes there.

A cloud container can answer for neither on its own, and the way it fails is
the dangerous one. Its clone carries only the repository the session was
sourced from, so a deploy remote reads as absent rather than unconfigured and
the check prints an all-clear over a site that is still serving the old tree;
add the remote by hand and the git proxy refuses a credential for a repo
outside that set. So a remote session runs both verbs on the workstation
instead, over the one host it can open a connection to. `--local` holds them
here, for asking what this checkout alone can see.
"""
from __future__ import annotations

import argparse
import base64
import os
import shlex
import subprocess
import sys

# Remotes that publish rather than store. `origin` is where work lands and is
# never a deploy remote; anything else pointing at a different repo is one.
DEPLOY_REMOTES = ("upstream", "deploy", "vercel", "mirror")

# The Pi terminates TLS on 443 through its Tailscale Funnel, and a cloud
# container's ssh config tunnels to it over that, which makes it the only host
# reachable from one. The workstation hangs off the Pi's own ssh config.
HOP_PI = os.environ.get("INTELLIGENCE_HOP_PI", "sunday")
HOP_WORKSTATION = os.environ.get("INTELLIGENCE_HOP_WORKSTATION", "trenton-mac")

# Where the workstation keeps its checkouts, searched in order for one whose
# directory name matches origin's repo.
WORKSTATION_ROOTS = (
    "$HOME/Development/IdeaProjects",
    "$HOME/Development/WebstormProjects",
    "$HOME/Development",
)


def git(*args: str, cwd: str | None = None) -> str:
    """Run a git command and return its stripped stdout, or "" if it failed."""
    done = subprocess.run(
        ("git", *args), cwd=cwd, capture_output=True, text=True
    )
    return done.stdout.strip() if done.returncode == 0 else ""


def is_remote_session() -> bool:
    return os.environ.get("CLAUDE_CODE_REMOTE", "").lower() == "true"


def repo_name(cwd: str | None) -> str:
    """The repository's own name, taken from origin rather than the directory.

    A cloud container clones into a path of its own choosing, so the local
    directory name is not what the workstation calls the same repository.
    """
    url = git("remote", "get-url", "origin", cwd=cwd)
    return url.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]


def run_on_workstation(name: str, action: str, branch: str) -> int:
    """Run this command against `name`'s checkout on the workstation.

    Two hops, because the container can reach the Pi and the Pi can reach the
    workstation. The inner script travels base64-encoded: it crosses two shells
    that would otherwise each take a turn at the quoting.
    """
    roots = " ".join(WORKSTATION_ROOTS)
    script = (
        "set -e\n"
        f"for root in {roots}; do\n"
        f'  d="$root/{name}"\n'
        '  [ -d "$d/.git" ] && repo="$d" && break\n'
        "done\n"
        'if [ -z "${repo:-}" ]; then\n'
        f'  echo "no checkout of {name} on the workstation" >&2\n'
        "  exit 2\n"
        "fi\n"
        f'exec "$HOME/.intelligence/tools/deploy-remote-sync.py" {shlex.quote(action)} '
        f"--local --branch {shlex.quote(branch)} --cwd \"$repo\"\n"
    )
    payload = base64.b64encode(script.encode()).decode()
    inner = f"echo {payload} | base64 -d | bash"
    hop = f"ssh -o BatchMode=yes {shlex.quote(HOP_WORKSTATION)} {shlex.quote(inner)}"
    done = subprocess.run(
        ("ssh", "-o", "BatchMode=yes", HOP_PI, hop),
        capture_output=True, text=True,
    )
    sys.stdout.write(done.stdout)
    if done.returncode != 0 and not done.stdout.strip():
        detail = done.stderr.strip() or "the workstation could not be reached"
        print(
            f"cannot answer for the deploy remote from here: {detail}\n"
            f"This session's clone carries only origin, so a local answer would be "
            f"a guess. Run it on the workstation, or fix the hop through "
            f"{HOP_PI}.",
            file=sys.stderr,
        )
        # An unreachable workstation is an unanswered check, never a passing one.
        return 2
    return done.returncode


def deploy_remote(cwd: str | None) -> str | None:
    """The remote this repo publishes from, or None when it publishes itself."""
    remotes = git("remote", cwd=cwd).split()
    origin_url = git("remote", "get-url", "origin", cwd=cwd)
    for name in DEPLOY_REMOTES:
        if name in remotes and git("remote", "get-url", name, cwd=cwd) != origin_url:
            return name
    return None


def branch_state(remote: str, branch: str, cwd: str | None) -> tuple[str, str, int]:
    """Where the two copies of `branch` stand, and how far apart they are."""
    git("fetch", "--quiet", "origin", cwd=cwd)
    git("fetch", "--quiet", remote, cwd=cwd)
    src = git("rev-parse", f"origin/{branch}", cwd=cwd)
    dst = git("rev-parse", f"{remote}/{branch}", cwd=cwd)
    if not src or not dst:
        return src, dst, 0
    behind = git("rev-list", "--count", f"{dst}..{src}", cwd=cwd)
    return src, dst, int(behind or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "sync"))
    parser.add_argument("--branch", default="main")
    parser.add_argument("--cwd", default=None)
    parser.add_argument(
        "--local", action="store_true",
        help="answer from this checkout alone, without the workstation hop",
    )
    args = parser.parse_args()

    if not git("rev-parse", "--git-dir", cwd=args.cwd):
        print("not a git repository", file=sys.stderr)
        return 2

    if is_remote_session() and not args.local:
        name = repo_name(args.cwd)
        if not name:
            print("origin has no URL, so the repository has no name to look up",
                  file=sys.stderr)
            return 2
        return run_on_workstation(name, args.action, args.branch)

    remote = deploy_remote(args.cwd)
    if remote is None:
        # A cloud clone has one remote whatever the repository is set up with,
        # so "none configured" and "none exists" look identical from inside one
        # and only the second is an all-clear.
        if is_remote_session():
            print("this clone carries no deploy remote, which a cloud clone would "
                  "not carry either way; this is not an answer about the repository",
                  file=sys.stderr)
            return 2
        print("no deploy remote; this repo is published from origin")
        return 0

    src, dst, behind = branch_state(remote, args.branch, args.cwd)
    if not src or not dst:
        print(f"{remote}/{args.branch} or origin/{args.branch} is missing", file=sys.stderr)
        return 2

    if behind == 0:
        print(f"{remote}/{args.branch} is level with origin/{args.branch} ({src[:7]})")
        return 0

    label = f"{remote}/{args.branch} is {behind} commit(s) behind origin/{args.branch}"
    if args.action == "check":
        print(f"{label} -- {dst[:7]} vs {src[:7]}; the host is still serving the older tree")
        return 1

    print(f"{label}; pushing {src[:7]}")
    done = subprocess.run(
        ("git", "push", remote, f"origin/{args.branch}:refs/heads/{args.branch}"),
        cwd=args.cwd, capture_output=True, text=True,
    )
    if done.returncode != 0:
        print(done.stderr.strip(), file=sys.stderr)
        return 2
    print(f"{remote}/{args.branch} -> {src[:7]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
