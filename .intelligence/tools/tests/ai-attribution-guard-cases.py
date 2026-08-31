#!/usr/bin/env python3
"""Cases the attribution guard has to get right at each of its three doors.

The guard is worth only what it refuses, and every gap in it is a shape nobody
thought to test: a vendor name over a human's address, an identity handed to git
on the command line so no message ever names it, a trailer that arrives in a
push rather than a commit. These fix each of those, and they fix the other half
too: a repository that merely discusses a vendor, or a person whose address
happens to contain a matching run of letters, has to keep landing.

  ai-attribution-guard-cases.py        run them
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
              or Path(__file__).resolve().parent.parent / "ai-attribution-guard.py")


def load(path):
    spec = importlib.util.spec_from_file_location("candidate", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bash_event(cmd):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})


def run_guard(cmd):
    """Return the exit code the PreToolUse guard gives a command."""
    p = subprocess.run([sys.executable, str(TARGET), "guard-bash"],
                       input=bash_event(cmd), capture_output=True, text=True)
    return p.returncode


def run_commit_msg(text):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(text)
        path = fh.name
    try:
        p = subprocess.run([sys.executable, str(TARGET), "hook-commit-msg", path],
                           capture_output=True, text=True)
        return p.returncode
    finally:
        os.unlink(path)


ZERO = "0" * 40


def run_pre_push(cwd, local_sha, remote_sha):
    """The exit code the pre-push hook gives one ref update."""
    line = f"refs/heads/topic {local_sha} refs/heads/topic {remote_sha}\n"
    p = subprocess.run([sys.executable, str(TARGET), "hook-pre-push"],
                       input=line, capture_output=True, text=True, cwd=str(cwd))
    return p.returncode


def commit(cwd, message, author=None):
    env = dict(os.environ)
    env.update(GIT_AUTHOR_NAME="Trenton Taylor", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="Trenton Taylor", GIT_COMMITTER_EMAIL="t@example.com")
    if author:
        env["GIT_AUTHOR_NAME"], env["GIT_AUTHOR_EMAIL"] = author
    (cwd / "file.txt").write_text(message)
    subprocess.run(["git", "add", "-A"], cwd=str(cwd), env=env, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "--no-verify", "-m", message], cwd=str(cwd),
                   env=env, check=True, capture_output=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(cwd),
                          capture_output=True, text=True).stdout.strip()


def published_history():
    """A repo whose remote already holds a commit carrying attribution.

    This is the shape every branch takes once one attributed commit lands on
    develop: the branch is new, so the remote sha is all zeros, and whatever
    is written on top sits over history the remote already has.
    """
    root = Path(tempfile.mkdtemp())
    origin, work = root / "origin.git", root / "work"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "develop", str(work)], check=True)
    subprocess.run(["git", "remote", "add", "origin", str(origin)], cwd=str(work),
                   check=True)
    commit(work, "first")
    commit(work, "landed",
           author=("claude[bot]", "claude[bot]@users.noreply.github.com"))
    subprocess.run(["git", "push", "-q", "--no-verify", "origin", "develop"],
                   cwd=str(work), check=True, capture_output=True)
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=str(work), check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "topic"], cwd=str(work),
                   check=True)
    return work


def guard_over_config(cmd, name, email):
    """Run the Bash guard against a throwaway global git config.

    Returns the exit code and the identity that config holds afterwards, so a
    case can tell a refusal apart from a repair.
    """
    root = Path(tempfile.mkdtemp())
    cfg = root / "gitconfig"
    cfg.write_text(f"[user]\n\tname = {name}\n\temail = {email}\n")
    env = dict(os.environ)
    env.update(GIT_CONFIG_GLOBAL=str(cfg), HOME=str(root),
               INTELLIGENCE_GIT_NAME="Trenton Taylor",
               INTELLIGENCE_GIT_EMAIL="trenton.taylor.email@gmail.com")
    env.pop("INTELLIGENCE_ALLOW_AI_ATTRIBUTION", None)
    code = subprocess.run([sys.executable, str(TARGET), "guard-bash"], env=env,
                          input=bash_event(cmd), capture_output=True,
                          text=True).returncode

    def held(key):
        return subprocess.run(["git", "config", "--global", "--get", key],
                              env=env, capture_output=True,
                              text=True).stdout.strip()

    return code, (held("user.name"), held("user.email"))


FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got}, want {want}")


def main():
    mod = load(TARGET)

    # An address alone is the easy half. A vendor name over a human's address is
    # the half that passes any check reading only the address.
    check("identity: vendor address", bool(mod.IDENTITY.search("noreply@anthropic.com")), True)
    check("identity: bot address", bool(mod.IDENTITY.search("209825114+claude[bot]@users.noreply.github.com")), True)
    check("identity: vendor name", bool(mod.IDENTITY.search("Claude")), True)
    check("identity: human name", bool(mod.IDENTITY.search("Trenton Taylor")), False)
    check("identity: human address", bool(mod.IDENTITY.search("trenton.taylor.email@gmail.com")), False)

    # A domain that merely starts the same way is not an AI.
    check("identity: innocent domain", bool(mod.IDENTITY.search("sam@claudiabakery.com")), False)

    # Trailers and footers, in the spellings that actually occur.
    for trailer in ("Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>",
                    "Co-authored-by: Claude <noreply@anthropic.com>",
                    "Co-Authored-By: Codex <codex@openai.com>",
                    "Claude-Session: https://claude.ai/code/session_01X"):
        check(f"message: {trailer[:28]}", bool(mod.MESSAGE.search(trailer)), True)

    # A commit that discusses a vendor is ordinary work and has to land.
    for ok in ("Remove the vendored config directory",
               "Document how the claude skill router picks a name",
               "Fix codex-style formatting in the parser"):
        check(f"message clean: {ok[:28]}", bool(mod.MESSAGE.search(ok)), False)

    # The identity doors that leave no trace in a message.
    check("bash: --author", run_guard('git commit -m "x" --author="Claude <noreply@anthropic.com>"'), 2)
    check("bash: -c user.email", run_guard('git -c user.email=noreply@anthropic.com commit -m "x"'), 2)
    check("bash: env identity", run_guard('GIT_AUTHOR_NAME=Claude git commit -m "x"'), 2)
    check("bash: trailer in text", run_guard('git commit -m "x\n\nCo-Authored-By: Claude <noreply@anthropic.com>"'), 2)
    check("bash: no-verify", run_guard('git commit --no-verify -m "x"'), 2)

    # Ordinary writes, and reads of any kind, must not be refused.
    check("bash: clean commit", run_guard('git commit -m "Add rate limiting"'), 0)
    check("bash: clean push", run_guard("git push origin develop"), 0)
    check("bash: read", run_guard("git log --oneline -5"), 0)

    # The identity a container hands the session survives its own session-start
    # repair, so the write itself has to put the human back rather than trust
    # what an earlier hook left behind.
    human = ("Trenton Taylor", "trenton.taylor.email@gmail.com")
    code, held = guard_over_config('git commit -m "Add rate limiting"',
                                   "Claude", "noreply@anthropic.com")
    check("bash: write repairs an AI identity", (code, held), (0, human))

    # An identity already the human's is left exactly as it is.
    code, held = guard_over_config('git commit -m "Add rate limiting"', *human)
    check("bash: write leaves a human identity", (code, held), (0, human))

    # A read carries nothing, so it neither refuses nor repairs.
    code, held = guard_over_config("git log --oneline -5",
                                   "Claude", "noreply@anthropic.com")
    check("bash: read does not repair", (code, held),
          (0, ("Claude", "noreply@anthropic.com")))

    # The squash commit takes the opener's identity, and a container's GitHub
    # writes are the app's whatever its own credentials report. Both spellings
    # of opening one have to be refused there, and neither anywhere else.
    def in_container(cmd):
        env = dict(os.environ, CLAUDE_CODE_REMOTE="true")
        env.pop("INTELLIGENCE_ALLOW_AI_ATTRIBUTION", None)
        return subprocess.run([sys.executable, str(TARGET), "guard-bash"],
                              input=bash_event(cmd), env=env,
                              capture_output=True, text=True).returncode

    for opener in ('gh pr create --base develop --head topic --title "x"',
                   'gh api -X POST repos/o/r/pulls -f title=x'):
        check(f"bash: container opens a PR: {opener[:24]}", in_container(opener), 2)

    # A merge, a comment and a push are not what decides that author.
    for other in ("gh pr merge --auto --squash 7",
                  'gh pr comment 7 --body "rerunning the check"',
                  "git push -u origin topic"):
        check(f"bash: container allows: {other[:24]}", in_container(other), 0)

    # Off a container the local credentials are the human's, so it stays open.
    # The variable is cleared rather than left alone, because these cases run
    # inside a container as often as not.
    def on_workstation(cmd):
        env = dict(os.environ)
        env.pop("CLAUDE_CODE_REMOTE", None)
        env.pop("INTELLIGENCE_ALLOW_AI_ATTRIBUTION", None)
        return subprocess.run([sys.executable, str(TARGET), "guard-bash"],
                              input=bash_event(cmd), env=env,
                              capture_output=True, text=True).returncode

    check("bash: workstation opens a PR",
          on_workstation('gh pr create --base develop --head topic --title "x"'), 0)

    # A first push sends only what the remote does not have. Scanning the whole
    # history instead refuses every branch cut after one attributed commit lands.
    work = published_history()
    clean = commit(work, "clean work on top")
    check("pre-push: new branch skips published history",
          run_pre_push(work, clean, ZERO), 0)

    dirty = commit(work, "own work",
                   author=("Claude", "noreply@anthropic.com"))
    check("pre-push: new branch still refuses its own attributed commit",
          run_pre_push(work, dirty, ZERO), 1)

    # An update to a branch the remote already has keeps the explicit range.
    check("pre-push: update scans only the new commits",
          run_pre_push(work, dirty, clean), 1)
    check("pre-push: update with nothing attributed passes",
          run_pre_push(work, clean, clean), 0)

    check("commit-msg: trailer", run_commit_msg("Add thing\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"), 1)
    check("commit-msg: clean", run_commit_msg("Add thing\n\nA real body.\n"), 0)
    # A comment line in the template is not part of the message.
    check("commit-msg: commented out", run_commit_msg("Add thing\n\n# Co-Authored-By: Claude <x@anthropic.com>\n"), 0)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
