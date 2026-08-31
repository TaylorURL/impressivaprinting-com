#!/usr/bin/env python3
"""Cases the deploy remote sync has to get right.

The tool answers one question: is the deploy remote serving the branch origin
holds? These fix both edges of every verb. A level remote passes and a behind
one is named, `sync` moves the remote and `check` never does, a repo publishing
itself is a silent success locally and a refusal from a cloud clone, and the
workstation hop is taken only in a remote session and fails closed when the
hop cannot be opened. Every repository here is a local bare fixture; the ssh
binary the hop reaches is a stub on PATH, so no case touches a network.

  deploy-remote-sync-cases.py        run them
"""
from __future__ import annotations

import base64
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "deploy-remote-sync.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def base_env():
    """An environment that keeps git hermetic: no global config, no hooks,
    a fixed identity, and no leaked remote-session flag."""
    env = dict(os.environ)
    env.update({
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_AUTHOR_NAME": "cases", "GIT_AUTHOR_EMAIL": "cases@example.com",
        "GIT_COMMITTER_NAME": "cases", "GIT_COMMITTER_EMAIL": "cases@example.com",
    })
    env.pop("CLAUDE_CODE_REMOTE", None)
    return env


def git_quiet(*args, cwd, env):
    done = subprocess.run(("git", *args), cwd=cwd, env=env,
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(f"fixture git {' '.join(args)} failed: {done.stderr}")
    return done.stdout.strip()


def make_repos(tmp, env, remote_name="vercel"):
    """A work clone whose origin and deploy remote are bare repos in the temp
    tree, with one commit level on both sides."""
    origin = Path(tmp) / "origin.git"
    deploy = Path(tmp) / "deploy.git"
    work = Path(tmp) / "work"
    for path in (origin, deploy):
        git_quiet("init", "--bare", str(path), cwd=tmp, env=env)
    git_quiet("clone", str(origin), str(work), cwd=tmp, env=env)
    git_quiet("symbolic-ref", "HEAD", "refs/heads/main", cwd=work, env=env)
    (work / "a.txt").write_text("one\n")
    git_quiet("add", "a.txt", cwd=work, env=env)
    git_quiet("commit", "-m", "one", cwd=work, env=env)
    git_quiet("push", "origin", "main", cwd=work, env=env)
    git_quiet("remote", "add", remote_name, str(deploy), cwd=work, env=env)
    git_quiet("push", remote_name, "main", cwd=work, env=env)
    for path in (origin, deploy, work):
        assert str(path).startswith(str(tmp)), f"escaped the temp tree: {path}"
    return origin, deploy, work


def advance_origin(work, env):
    """One commit past the deploy remote, pushed to origin alone."""
    (work / "a.txt").write_text("two\n")
    git_quiet("add", "a.txt", cwd=work, env=env)
    git_quiet("commit", "-m", "two", cwd=work, env=env)
    git_quiet("push", "origin", "main", cwd=work, env=env)


def run_tool(action, cwd, env, *extra):
    return subprocess.run(
        [sys.executable, str(TARGET), action, "--cwd", str(cwd), *extra],
        env=env, capture_output=True, text=True)


def ssh_stub(tmp, body):
    """A fake ssh on PATH that logs its arguments, so the hop's shape is
    observable without a connection."""
    stubs = Path(tmp) / "stubs"
    stubs.mkdir(exist_ok=True)
    log = Path(tmp) / "ssh.log"
    script = stubs / "ssh"
    script.write_text("#!/bin/sh\n"
                      f"printf '%s\\n' \"$@\" >> {log}\n" + body)
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return stubs, log


def local_cases():
    env = base_env()

    with tempfile.TemporaryDirectory() as tmp:
        bare_dir = Path(tmp) / "empty"
        bare_dir.mkdir()
        p = run_tool("check", bare_dir, env)
        check("not a repo refuses", p.returncode, 2)
        check("not a repo names it", "not a git repository" in p.stderr, True)

    with tempfile.TemporaryDirectory() as tmp:
        _, _, work = make_repos(tmp, env)
        git_quiet("remote", "remove", "vercel", cwd=work, env=env)
        p = run_tool("check", work, env)
        check("no deploy remote passes", p.returncode, 0)
        check("no deploy remote says so",
              "no deploy remote; this repo is published from origin" in p.stdout, True)

    with tempfile.TemporaryDirectory() as tmp:
        origin, _, work = make_repos(tmp, env)
        git_quiet("remote", "set-url", "vercel", str(origin), cwd=work, env=env)
        p = run_tool("check", work, env)
        check("remote at origin's URL is not a deploy remote", p.returncode, 0)
        check("same-URL remote reported as none",
              "no deploy remote" in p.stdout, True)

    with tempfile.TemporaryDirectory() as tmp:
        _, _, work = make_repos(tmp, env)
        p = run_tool("check", work, env)
        check("level check passes", p.returncode, 0)
        check("level check says level", "is level with origin/main" in p.stdout, True)

    with tempfile.TemporaryDirectory() as tmp:
        _, deploy, work = make_repos(tmp, env)
        advance_origin(work, env)
        before = git_quiet("rev-parse", "main", cwd=deploy, env=env)
        p = run_tool("check", work, env)
        check("behind check fails", p.returncode, 1)
        check("behind check counts", "is 1 commit(s) behind origin/main" in p.stdout, True)
        check("behind check names the stale tree",
              "the host is still serving the older tree" in p.stdout, True)
        after = git_quiet("rev-parse", "main", cwd=deploy, env=env)
        check("check never pushes", after, before)

    with tempfile.TemporaryDirectory() as tmp:
        origin, deploy, work = make_repos(tmp, env)
        advance_origin(work, env)
        p = run_tool("sync", work, env)
        check("behind sync passes", p.returncode, 0)
        check("behind sync says pushing", "pushing" in p.stdout, True)
        src = git_quiet("rev-parse", "main", cwd=origin, env=env)
        dst = git_quiet("rev-parse", "main", cwd=deploy, env=env)
        check("sync levels the remote", dst, src)
        p = run_tool("check", work, env)
        check("check after sync passes", p.returncode, 0)

    with tempfile.TemporaryDirectory() as tmp:
        origin, deploy, work = make_repos(tmp, env)
        before = git_quiet("rev-parse", "main", cwd=deploy, env=env)
        p = run_tool("sync", work, env)
        check("level sync passes", p.returncode, 0)
        check("level sync pushes nothing",
              git_quiet("rev-parse", "main", cwd=deploy, env=env), before)

    with tempfile.TemporaryDirectory() as tmp:
        _, deploy, work = make_repos(tmp, env)
        # receive-pack points an empty bare repo's HEAD at the first branch
        # pushed into it, and then refuses to delete the branch HEAD names. A
        # hosting remote deletes a branch on request, so the fixture says so
        # rather than the case working around a policy no real deploy remote
        # applies.
        git_quiet("config", "receive.denyDeleteCurrent", "ignore",
                  cwd=deploy, env=env)
        git_quiet("push", "vercel", "--delete", "main", cwd=work, env=env)
        git_quiet("fetch", "--prune", "vercel", cwd=work, env=env)
        p = run_tool("check", work, env)
        check("missing deploy branch refuses", p.returncode, 2)
        check("missing deploy branch names it", "is missing" in p.stderr, True)

    with tempfile.TemporaryDirectory() as tmp:
        _, _, work = make_repos(tmp, env)
        git_quiet("branch", "develop", cwd=work, env=env)
        git_quiet("push", "origin", "develop", cwd=work, env=env)
        git_quiet("push", "vercel", "develop", cwd=work, env=env)
        p = run_tool("check", work, env, "--branch", "develop")
        check("named branch checked", p.returncode, 0)
        check("named branch in the report", "vercel/develop is level" in p.stdout, True)

    for name in ("upstream", "deploy", "mirror"):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, work = make_repos(tmp, env, remote_name=name)
            p = run_tool("check", work, env)
            check(f"{name} recognised as a deploy remote",
                  f"{name}/main is level" in p.stdout, True)

    with tempfile.TemporaryDirectory() as tmp:
        _, _, work = make_repos(tmp, env, remote_name="backup")
        p = run_tool("check", work, env)
        check("unlisted remote name is not a deploy remote",
              "no deploy remote" in p.stdout, True)


def remote_cases():
    with tempfile.TemporaryDirectory() as tmp:
        env = base_env()
        env["CLAUDE_CODE_REMOTE"] = "true"
        _, _, work = make_repos(tmp, env)
        git_quiet("remote", "remove", "vercel", cwd=work, env=env)
        p = run_tool("check", work, env, "--local")
        check("cloud clone with one remote refuses --local", p.returncode, 2)
        check("cloud refusal explains itself",
              "not an answer about the repository" in p.stderr, True)

    with tempfile.TemporaryDirectory() as tmp:
        env = base_env()
        env["CLAUDE_CODE_REMOTE"] = "true"
        _, _, work = make_repos(tmp, env)
        p = run_tool("check", work, env, "--local")
        check("cloud clone with a real deploy remote answers --local", p.returncode, 0)

    with tempfile.TemporaryDirectory() as tmp:
        env = base_env()
        env["CLAUDE_CODE_REMOTE"] = "true"
        nameless = Path(tmp) / "nameless"
        nameless.mkdir()
        git_quiet("init", cwd=nameless, env=env)
        p = run_tool("check", nameless, env)
        check("remote session without an origin URL refuses", p.returncode, 2)
        check("nameless refusal names the gap", "no name to look up" in p.stderr, True)

    with tempfile.TemporaryDirectory() as tmp:
        env = base_env()
        _, _, work = make_repos(tmp, env)
        stubs, log = ssh_stub(tmp, "echo workstation-answer\nexit 0\n")
        env.update({
            "CLAUDE_CODE_REMOTE": "true",
            "PATH": f"{stubs}:{env['PATH']}",
            "INTELLIGENCE_HOP_PI": "pi-stub",
            "INTELLIGENCE_HOP_WORKSTATION": "mac-stub",
        })
        p = run_tool("check", work, env)
        check("hop passes through the stub's exit", p.returncode, 0)
        check("hop forwards the workstation's stdout",
              "workstation-answer" in p.stdout, True)
        logged = log.read_text()
        check("hop targets the pi override", "pi-stub" in logged, True)
        check("hop carries the workstation override", "mac-stub" in logged, True)
        # The inner script crosses two shells base64-encoded, so the flag it
        # carries is read by decoding the payload out of the logged command.
        payload = logged.split("echo ", 1)[1].split(" |", 1)[0]
        inner = base64.b64decode(payload).decode()
        check("hop runs the tool with --local", "--local" in inner, True)
        # The lookup name comes from origin's URL, never the clone directory:
        # the fixture clones origin.git into work/, and the hop searches for
        # a checkout named origin.
        check("hop looks the repo up by origin's name", '"$root/origin"' in inner, True)
        check("hop never uses the clone's directory name", "/work" in inner, False)

    with tempfile.TemporaryDirectory() as tmp:
        env = base_env()
        _, _, work = make_repos(tmp, env)
        stubs, _ = ssh_stub(tmp, "echo workstation-failure\nexit 1\n")
        env.update({"CLAUDE_CODE_REMOTE": "true",
                    "PATH": f"{stubs}:{env['PATH']}"})
        p = run_tool("check", work, env)
        check("hop that answered keeps its exit", p.returncode, 1)
        check("hop failure output forwarded", "workstation-failure" in p.stdout, True)

    with tempfile.TemporaryDirectory() as tmp:
        env = base_env()
        _, _, work = make_repos(tmp, env)
        stubs, _ = ssh_stub(tmp, "echo down >&2\nexit 255\n")
        env.update({"CLAUDE_CODE_REMOTE": "true",
                    "PATH": f"{stubs}:{env['PATH']}"})
        p = run_tool("check", work, env)
        check("unreachable workstation fails closed", p.returncode, 2)
        check("unreachable workstation named",
              "cannot answer for the deploy remote from here" in p.stderr, True)

    with tempfile.TemporaryDirectory() as tmp:
        env = base_env()
        env["CLAUDE_CODE_REMOTE"] = "false"
        _, _, work = make_repos(tmp, env)
        p = run_tool("check", work, env)
        check("remote flag off answers locally", p.returncode, 0)
        check("remote flag off skips the hop", "is level with origin/main" in p.stdout, True)


def main():
    local_cases()
    remote_cases()
    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
