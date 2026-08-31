#!/usr/bin/env python3
"""Points GitHub work at the path that works on the box it is running on.

On a machine carrying real credentials `gh` is the whole story. In a cloud
container it is not, and the ways it fails are all quiet:

  - `gh auth status` reports the environment token invalid whatever else is
    true, because the session's proxy supplies the credential and the token is
    never consulted. A run that reads that as "gh is broken here" stops or
    routes around a `gh` that would have answered.
  - `gh pr`, `gh repo`, `gh run` and the rest of the porcelain travel over
    GraphQL, which the session serves only for a pinned set of PR-review
    operations. Everything else answers 403.
  - `gh api` against a repository endpoint answers 403 until an org admin
    connects the GitHub App for that organization, so it cannot be relied on
    for repository work either.

What does work in a container: `git` for the session's own repositories, the
`mcp__github__*` tools for pull requests, comments, reviews and issues, and the
Pi for anything outside the session's repository set. This guard names whichever
of those replaces the command it stopped.

  github-route-guard.py where     which side of the line this box is on
  github-route-guard.py guard     PreToolUse, reads a hook event on stdin
  github-route-guard.py install   wire it into settings.json
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

INTELLIGENCE = Path(os.environ.get("INTELLIGENCE_HOME") or (Path.home() / ".intelligence"))
SETTINGS = INTELLIGENCE / "settings.json"

# The porcelain, which travels over GraphQL. `gh pr checks` is in here too: it
# reads the same graph as the rest of the subcommand.
PORCELAIN = re.compile(
    r"\bgh\s+(?:pr|repo|issue|release|run|workflow|search|browse|project|ruleset)\b")

# `gh api` against anything repository- or org-shaped, as opposed to the
# user-scoped endpoints the proxy does answer.
REPO_API = re.compile(r"\bgh\s+api\b[^|;&]*\b(?:repos?|orgs?)/", re.I)

AUTH_STATUS = re.compile(r"\bgh\s+auth\s+status\b")

# A command handed to another machine runs where gh carries real credentials,
# so it is that machine's business rather than this guard's.
ELSEWHERE = re.compile(r"\bremote-access\.py\b|\bssh\s+\S|\bremote\s+(?:pi|mac|windows|vps)\b")

REPLACEMENT = {
    "pr": "mcp__github__create_pull_request / update_pull_request / pull_request_read",
    "issue": "mcp__github__issue_write / issue_read",
    "release": "mcp__github__list_releases / get_latest_release",
    "run": "mcp__github__actions_list / actions_get / get_job_logs",
    "workflow": "mcp__github__actions_run_trigger / actions_list",
    "repo": "mcp__github__get_file_contents / create_or_update_file / push_files",
    "search": "mcp__github__search_code / search_issues / search_pull_requests",
    "project": "the GitHub MCP tools",
    "browse": "the GitHub MCP tools",
    "ruleset": "the GitHub MCP tools",
}


def in_cloud():
    """Whether this is a cloud container.

    The same signal every other cloud-gated behaviour in the tree reads, so a
    box cannot be a container for one guard and not for another.
    """
    return str(os.environ.get("CLAUDE_CODE_REMOTE", "")).lower() == "true"


def executable(command):
    """The command with its quoted payloads removed.

    A commit message, a heredoc body or a message argument can name a command
    without running one, and a guard that reads those refuses the very text
    documenting what it refuses. What is left after they are stripped is the
    part the shell would actually execute.
    """
    command = re.sub(r"\$\((?:[^()]|\([^()]*\))*\)", " ", command, flags=re.S)
    command = re.sub(r"<<-?\s*(['\"]?)(\w+)\1.*?^\2\s*$", " ", command,
                     flags=re.S | re.M)
    command = re.sub(r"(?:-m|--message|--body|--title)\s*=?\s*(['\"])"
                     r"(?:\\.|(?!\1).)*\1", " ", command, flags=re.S)
    return command


def block(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def subcommand(command):
    match = PORCELAIN.search(command)
    return match.group(0).split()[-1] if match else ""


def verdict(command):
    """The refusal a command earns here, or an empty string when it earns none."""
    if not in_cloud() or os.environ.get("INTELLIGENCE_ALLOW_GH") == "1":
        return ""
    if ELSEWHERE.search(command):
        return ""
    command = executable(command)
    if AUTH_STATUS.search(command):
        return (
            "BLOCKED: `gh auth status` reports the token invalid on every cloud box.\n\n"
            "  The session's proxy supplies the credential and the environment\n"
            "  token is never consulted, so that command answers the same way\n"
            "  whether or not gh works. It is not a health check here.\n\n"
            "  What gh can actually reach:  gh api user\n"
            "  What a repository needs:     the mcp__github__* tools\n"
            "  What git needs:              nothing, the proxy answers for it\n")
    if PORCELAIN.search(command):
        verb = subcommand(command)
        return (
            "BLOCKED: `gh %s` travels over GraphQL, which this session does not serve.\n\n"
            "  Only a pinned set of PR-review operations is answered; everything\n"
            "  else returns 403, so this reports a failure that says nothing about\n"
            "  the work.\n\n"
            "  Use instead: %s\n\n"
            "  A repository outside this session's set is reached through the Pi:\n"
            "    ~/.intelligence/tools/remote-access.py run mac -- gh %s ...\n"
            % (verb, REPLACEMENT.get(verb, "the GitHub MCP tools"), verb))
    if REPO_API.search(command):
        return (
            "BLOCKED: `gh api` on a repository endpoint answers 403 on this box.\n\n"
            "  Repository REST needs the GitHub App connected for that\n"
            "  organization; until it is, every repos/ and orgs/ path is refused.\n\n"
            "  Use instead: the mcp__github__* tools, which are served here.\n"
            "  Outside this session's repository set, go through the Pi:\n"
            "    ~/.intelligence/tools/remote-access.py run mac -- gh api ...\n")
    return ""


def guard():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    if not command:
        return 0
    message = verdict(command)
    if message:
        block(message)
    return 0


def install():
    """Wire the guard, and take the dead token out of this box's settings.

    A token in the environment is what makes `gh auth status` report a hard
    failure, so removing it is part of wiring the guard rather than a separate
    tidy-up.
    """
    try:
        doc = json.loads(SETTINGS.read_text())
    except (OSError, ValueError):
        doc = {}
    changed = False

    env = doc.get("env") or {}
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        if in_cloud() and key in env:
            del env[key]
            changed = True
    if env:
        doc["env"] = env
    elif "env" in doc and not env:
        del doc["env"]
        changed = True

    hooks = doc.setdefault("hooks", {})
    entries = hooks.setdefault("PreToolUse", [])
    wanted = "~/.intelligence/tools/guard-hub.py pre"
    if not any(h.get("command", "").startswith(wanted.split()[0])
               for e in entries for h in (e.get("hooks") or [])):
        entries.append({"matcher": "Bash",
                        "hooks": [{"type": "command", "command": wanted, "timeout": 120}]})
        changed = True

    if changed:
        SETTINGS.write_text(json.dumps(doc, indent=2) + "\n")
    print("github-route-guard wired" + ("; settings.json token removed" if changed else ""))
    return 0


def where():
    if in_cloud():
        print("container: gh reaches user-scoped endpoints only; "
              "repositories go through the mcp__github__* tools, "
              "and anything outside this session's set goes through the Pi")
    else:
        print("workstation: gh carries real credentials and is the way")
    return 0


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else "guard"
    if verb == "guard":
        return guard()
    if verb == "install":
        return install()
    if verb == "where":
        return where()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
