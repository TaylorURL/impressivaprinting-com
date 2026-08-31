#!/usr/bin/env python3
"""Cases the GitHub routing guard has to get right.

The guard is a refusal, so the cases it has to hold are symmetrical: on a
workstation it must never speak, and in a container it must catch the three
commands that fail quietly there while leaving the ones that work alone. A guard
that also stops `git push` or `gh api user` would take the working paths down
with the broken ones.

  github-route-guard-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "github-route-guard.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def blocked(mod, command):
    return bool(mod.verdict(command))


# Everything a container refuses, with what a reader should see named in the
# refusal so the guard cannot pass by blocking and saying nothing useful.
BLOCKS = [
    ("auth status", "gh auth status", "gh api user"),
    ("auth status with flags", "gh auth status --hostname github.com", "gh api user"),
    ("pr create", "gh pr create --base develop --fill", "mcp__github__create_pull_request"),
    ("pr merge", 'gh pr merge 12 --auto --squash', "mcp__github__"),
    ("pr list", "gh pr list --state open", "mcp__github__"),
    ("pr checks", "gh pr checks 40", "mcp__github__"),
    ("repo clone", "gh repo clone owner/name", "mcp__github__"),
    ("run watch", "gh run watch 123 --exit-status", "mcp__github__actions"),
    ("workflow run", "gh workflow run release.yml --ref main", "mcp__github__actions"),
    ("issue create", 'gh issue create --title "x"', "mcp__github__issue_write"),
    ("repo api read", "gh api repos/owner/name/branches", "mcp__github__"),
    ("repo api write", "gh api -X PATCH repos/o/n -f allow_auto_merge=true", "mcp__github__"),
    ("org api", "gh api orgs/acme/members", "mcp__github__"),
    ("api inside a pipeline", "gh api repos/o/n --jq .name | tr -d '\\n'", "mcp__github__"),
]

# Everything a container leaves alone: the paths that actually work there.
ALLOWS = [
    ("user endpoint", "gh api user --jq .login"),
    ("user orgs", "gh api user/orgs --jq '.[].login'"),
    ("version", "gh --version"),
    ("git push", "git push -u origin feature"),
    ("git clone", "git clone https://github.com/owner/name.git"),
    ("git ls-remote", "git ls-remote https://github.com/owner/name.git main"),
    ("unrelated word", "echo 'the graph shows a high'"),
    ("a path that merely contains repos", "ls ~/repos/name"),
    ("through the Pi", "~/.intelligence/tools/remote-access.py run mac -- gh pr create"),
]


AUTH = 'gh' + ' auth status'
CREATE = 'gh' + ' pr create'

# A command named inside a quoted payload is not a command. Without this the
# guard refuses the very text documenting what it refuses.
QUOTED = [
    ("a real command", AUTH, True),
    ("named in a message argument", 'git commit -m "%s is not a check"' % AUTH, False),
    ("named in a long message flag", 'git commit --message="%s"' % CREATE, False),
    ("named in a heredoc body",
     'git commit -q -F - <<EOF\n%s is refused here\nEOF\n' % CREATE, False),
    ("named inside a substitution",
     'git commit -q -m "$(printf %%s "%s")"' % AUTH, False),
    ("real, after a message", 'git commit -m "note" && %s' % CREATE, True),
    ("real, before a message", '%s && git commit -m "note"' % CREATE, True),
]


def run():
    mod = load()

    os.environ["CLAUDE_CODE_REMOTE"] = "true"
    os.environ.pop("INTELLIGENCE_ALLOW_GH", None)
    for label, command, expected in BLOCKS:
        message = mod.verdict(command)
        check(f"container blocks {label}", bool(message), True)
        if message:
            check(f"container names the way round {label}", expected in message, True)
    for label, command in ALLOWS:
        check(f"container allows {label}", blocked(mod, command), False)

    # The override is the way past a refusal the guard has misread.
    os.environ["INTELLIGENCE_ALLOW_GH"] = "1"
    check("override lets a blocked command through", blocked(mod, "gh pr create"), False)
    os.environ.pop("INTELLIGENCE_ALLOW_GH", None)

    # On a workstation gh carries real credentials, so the guard is silent.
    os.environ["CLAUDE_CODE_REMOTE"] = "false"
    for label, command, _ in BLOCKS:
        check(f"workstation allows {label}", blocked(mod, command), False)
    os.environ.pop("CLAUDE_CODE_REMOTE", None)
    check("no signal means workstation", blocked(mod, CREATE), False)

    os.environ["CLAUDE_CODE_REMOTE"] = "true"
    for label, command, want in QUOTED:
        check("quoted payload: " + label, blocked(mod, command), want)
    os.environ.pop("CLAUDE_CODE_REMOTE", None)

    if FAILURES:
        print("\n".join(FAILURES))
        return 1
    print(f"github-route-guard: {len(BLOCKS) * 2 + len(ALLOWS) + len(BLOCKS) + 2} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
