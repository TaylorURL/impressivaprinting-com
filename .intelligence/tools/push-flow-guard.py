#!/usr/bin/env python3
"""Work reaches a protected branch through a pull request.

A worktree branch lands on develop through a PR with auto-merge, and develop
reaches main the same way. A direct push to either one skips the required check
that gates them both, and a generic instruction to push is a request to land the
change rather than an opt-out from the flow that lands it.

The refusal reads both halves of a push: the refspec when one is given, and the
branch HEAD is on when it is not.

  guard-bash   a git push aimed at a protected branch

INTELLIGENCE_ALLOW_DIRECT_PUSH=1 covers the push that has to go direct.
"""
import json
import os
import re
import subprocess
import sys

PROTECTED = ("develop", "main", "master")

GIT_PUSH = re.compile(r"\bgit\b(?:\s+-\S+(?:\s+\S+)?)*\s+push\b")

# Everything the push carries, up to the end of the command. The positional
# arguments in it are the remote and the refspecs; the flags are read separately
# so a flag between the verb and the refspec does not hide it.
REFSPEC = re.compile(r"\bgit\b[^\n;&|]*?\bpush\b([^\n;&|]*)", re.S)

# The flags that make a push something other than a branch update. A tag push
# and a delete are their own acts and are not what this guard is about.
EXEMPT_FLAG = re.compile(r"(?:^|\s)(?:--tags|--delete|-d|--mirror|--prune)\b")

# The flags that take a separate value, so the value is not read as a refspec.
FLAG_WITH_VALUE = ("-o", "--push-option", "--repo", "--receive-pack", "--exec")


def payload():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def head_branch(cwd):
    try:
        out = subprocess.run(
            ["git", "-C", cwd or ".", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


# A command that opens with `cd` does not run where the payload says. Reading a
# remote or a branch in the session's directory instead of the command's makes
# every remote unknown, and unknown is treated as origin, so the guard refuses
# pushes it has no business refusing.
CD_STEP = re.compile(
    r"""(?:^|[;&|\n]\s*)cd\s+('[^']*'|"[^"]*"|[^\s;&|]+)""", re.M)


def working_dir(command, cwd):
    """The directory the push runs in, following any cd the command performs."""
    where = cwd or os.getcwd()
    for m in CD_STEP.finditer(command):
        step = m.group(1).strip("'\"")
        step = step if os.path.isabs(step) else os.path.join(where, step)
        if os.path.isdir(step):
            where = step
    return where


def remote_url(name, cwd):
    try:
        out = subprocess.run(
            ["git", "-C", cwd or ".", "remote", "get-url", name],
            capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def _norm(url):
    url = url.strip().rstrip("/")
    return url[:-4] if url.endswith(".git") else url


def publishes_to_origin(name, cwd):
    """Whether this push goes to the repository the pull request flow lives in.

    A push to a second remote is a mirror onto a build host. The commits it
    carries have already been through a pull request and the required check on
    origin, and the other side has no pull request flow to use instead --
    `deploy-remote-sync.py sync` does exactly this on every promotion, and a
    guard that reads the branch name without the remote refuses it. An unknown
    or unreadable remote is treated as origin, so the doubt refuses rather than
    waves through.
    """
    if not name or name == "origin":
        return True
    target = name if ("://" in name or name.startswith("git@")) else remote_url(name, cwd)
    origin = remote_url("origin", cwd)
    if not target or not origin:
        return True
    return _norm(target) == _norm(origin)


def positional(tail):
    """The arguments of a push that are not flags or flag values."""
    args = []
    skip = False
    for token in tail.split():
        if skip:
            skip = False
            continue
        if token in FLAG_WITH_VALUE:
            skip = True
            continue
        if token.startswith("-"):
            continue
        args.append(token)
    return args


def targets(command, cwd):
    """The protected branches this command would push to."""
    found = set()
    for m in REFSPEC.finditer(command):
        tail = m.group(1) or ""
        if EXEMPT_FLAG.search(tail):
            continue
        args = positional(tail)
        if args and not publishes_to_origin(args[0], cwd):
            continue
        refs = args[1:]
        for ref in refs:
            dest = ref.split(":")[-1].rsplit("/", 1)[-1]
            if dest in PROTECTED:
                found.add(dest)
        if not refs:
            # A push with a remote and no refspec, or with no arguments at all,
            # moves whatever branch HEAD is on.
            here = head_branch(cwd)
            if here in PROTECTED:
                found.add(here)
    return found


def main():
    if os.environ.get("INTELLIGENCE_ALLOW_DIRECT_PUSH") == "1":
        return 0
    if (sys.argv[1:2] or [""])[0] != "guard-bash":
        sys.stderr.write(__doc__)
        return 1
    p = payload()
    command = str((p.get("tool_input") or {}).get("command") or "")
    if not GIT_PUSH.search(command):
        return 0
    hit = targets(command, working_dir(command, p.get("cwd") or os.getcwd()))
    if not hit:
        return 0
    branches = ", ".join(sorted(hit))
    sys.stderr.write(
        "BLOCKED: this pushes straight to %s.\n\n"
        "Landing work means the pull request flow: move the commits onto a\n"
        "branch, push that, open a PR and enable auto-merge. The required\n"
        "check gates the merge, and a direct push goes around it.\n\n"
        "  git branch <feature-branch>\n"
        "  git reset --hard origin/%s\n"
        "  git push -u origin <feature-branch>\n"
        "  gh pr create --base %s --fill && gh pr merge --auto --squash\n\n"
        "/commit runs all of that. INTELLIGENCE_ALLOW_DIRECT_PUSH=1 covers a\n"
        "push that genuinely has to go direct.\n"
        % (branches, sorted(hit)[0], sorted(hit)[0]))
    return 2


if __name__ == "__main__":
    sys.exit(main())
