#!/usr/bin/env python3
"""Cases the worktree tool has to get right.

The guard is worth only what it refuses, and worth nothing if it refuses a tree
it has no claim on. So these fix both edges: an edit in the primary checkout of
an owned repo is caught, and the same edit inside a worktree, an unowned repo,
a repo with no develop branch, or the config tree stays allowed. The verbs are
fixed by their contract — `new` cuts from origin/develop into the worktrees
root and refuses a taken branch name, `done` refuses a dirty tree, an open
design run, and the primary checkout itself.

Every fixture lives in a temporary directory: the child runs with HOME pointed
there, so the worktrees root, the design-run state, and the config exemption
all resolve inside it and nothing can reach the live tree. Origins are local
bare repositories, so no case touches the network.

  worktree-cases.py        run them
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "worktree.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def env_for(home):
    """A child environment whose HOME, and therefore every tree the tool
    derives from it, sits inside the fixture directory. Git's global and
    system config are silenced so no hooksPath or identity leaks in."""
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_AUTHOR_NAME"] = "Case Fixture"
    env["GIT_AUTHOR_EMAIL"] = "cases@example.invalid"
    env["GIT_COMMITTER_NAME"] = "Case Fixture"
    env["GIT_COMMITTER_EMAIL"] = "cases@example.invalid"
    env.pop("INTELLIGENCE_ALLOW_PRIMARY_WRITES", None)
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return env


def git_quiet(*args, cwd=None, env=None):
    subprocess.run(("git", *args), cwd=cwd, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_repo(tmp, home, env, owner="bradley-t-t", name="proj", develop=True):
    """A primary checkout cloned from a local bare origin. The owner segment in
    the bare repository's path is what `is_owned` reads, so an owned fixture
    and an unowned one differ only there."""
    bare = tmp / "remotes" / owner / (name + ".git")
    bare.mkdir(parents=True)
    git_quiet("init", "--bare", "-b", "main", str(bare), env=env)
    seed = tmp / ("seed-" + owner + "-" + name)
    git_quiet("init", "-b", "main", str(seed), env=env)
    (seed / "README.md").write_text(name + "\n")
    git_quiet("add", ".", cwd=str(seed), env=env)
    git_quiet("commit", "-q", "-m", "seed", cwd=str(seed), env=env)
    git_quiet("push", "-q", str(bare), "main:main", cwd=str(seed), env=env)
    if develop:
        git_quiet("push", "-q", str(bare), "main:develop", cwd=str(seed), env=env)
    primary = home / "Development" / "IdeaProjects" / name
    primary.parent.mkdir(parents=True, exist_ok=True)
    git_quiet("clone", "-q", str(bare), str(primary), env=env)
    assert str(primary).startswith(str(tmp)), "fixture escaped the temp tree"
    return primary


def run_guard(env, path=None, extra=None, raw=None):
    payload = {"tool_name": "Write", "tool_input": {}}
    if path is not None:
        payload["tool_input"]["file_path"] = str(path)
    ev = raw if raw is not None else json.dumps(payload)
    e = dict(env)
    e.update(extra or {})
    p = subprocess.run([sys.executable, str(TARGET), "guard"],
                       input=ev, capture_output=True, text=True, env=e)
    return p.returncode


def run_verb(env, cwd, *args):
    return subprocess.run([sys.executable, str(TARGET), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


def owned_repo_cases(tmp, home, env):
    primary = make_repo(tmp, home, env)
    worktrees = home / "Development" / "worktrees" / "proj"

    check("guard: primary checkout refused",
          run_guard(env, primary / "src.py"), 2)
    check("guard: notebook_path refused too",
          run_guard(env, raw=json.dumps({
              "tool_name": "NotebookEdit",
              "tool_input": {"notebook_path": str(primary / "nb.ipynb")}})), 2)
    check("guard: override allows the primary",
          run_guard(env, primary / "src.py",
                    extra={"INTELLIGENCE_ALLOW_PRIMARY_WRITES": "1"}), 0)
    check("guard: config tree exempt",
          run_guard(env, home / ".intelligence" / "tools" / "x.py"), 0)
    check("guard: outside any repo",
          run_guard(env, tmp / "nowhere" / "file.txt"), 0)
    check("guard: no path in the event", run_guard(env), 0)
    check("guard: unreadable event", run_guard(env, raw="not json"), 0)

    p = run_verb(env, primary, "new", "My Feature!")
    check("new: cuts from develop", p.returncode, 0)
    dest = Path(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else Path("/missing")
    check("new: slugified path", str(dest), str(worktrees / "my-feature"))
    assert str(dest).startswith(str(tmp)), "worktree escaped the temp tree: %s" % dest
    check("new: tree exists", dest.is_dir(), True)
    branch = subprocess.run(("git", "branch", "--show-current"), cwd=str(dest),
                            env=env, capture_output=True, text=True).stdout.strip()
    check("new: branch matches slug", branch, "my-feature")

    check("guard: worktree edit allowed", run_guard(env, dest / "src.py"), 0)

    p = run_verb(env, primary, "new", "My Feature!")
    check("new: same slug is idempotent", p.returncode, 0)
    check("new: says it already exists", "already exists" in p.stdout, True)

    p = run_verb(env, dest, "new", "second")
    check("new: from inside a worktree", p.returncode, 0)
    second = Path(p.stdout.strip().splitlines()[-1])
    check("new: never nests one", str(second.parent), str(worktrees))

    git_quiet("branch", "taken", cwd=str(primary), env=env)
    check("new: taken branch name refused",
          run_verb(env, primary, "new", "taken").returncode, 2)
    check("new: no slug refused",
          run_verb(env, primary, "new").returncode, 2)
    check("new: outside a repo refused",
          run_verb(env, tmp, "new", "stray").returncode, 2)

    p = run_verb(env, primary, "list")
    check("list: exits clean", p.returncode, 0)
    check("list: names the primary",
          any(l.startswith("primary") and str(primary) in l
              for l in p.stdout.splitlines()), True)
    check("list: names the worktree",
          any(l.startswith("worktree") and "my-feature" in l
              for l in p.stdout.splitlines()), True)

    p = run_verb(env, primary, "done", "second")
    check("done: removes a clean worktree", p.returncode, 0)
    check("done: tree is gone", second.exists(), False)
    gone = subprocess.run(("git", "rev-parse", "--verify", "--quiet",
                           "refs/heads/second"), cwd=str(primary), env=env,
                          capture_output=True, text=True)
    check("done: branch deleted with it", gone.returncode == 0, False)

    (dest / "wip.txt").write_text("unlanded\n")
    check("done: dirty worktree refused",
          run_verb(env, primary, "done", "my-feature").returncode, 2)
    (dest / "wip.txt").unlink()

    runs = home / ".intelligence" / "state" / "design-runs"
    runs.mkdir(parents=True)
    run_state = runs / "20260101-000000.json"
    run_state.write_text(json.dumps(
        {"id": "run1", "closed": False, "targets": [str(dest)]}))
    p = run_verb(env, primary, "done", "my-feature")
    check("done: open design run refused", p.returncode, 2)
    check("done: names the run", "design run" in p.stderr, True)
    run_state.write_text(json.dumps(
        {"id": "run1", "closed": True, "targets": [str(dest)]}))
    check("done: closed run does not block",
          run_verb(env, primary, "done", "my-feature").returncode, 0)

    check("done: primary itself refused",
          run_verb(env, primary, "done").returncode, 2)


def fake_gh(home, merged):
    """A `gh` that answers the one question the sweep asks it.

    Whether a tree is removed rests entirely on GitHub's answer, so both answers
    have to be fixed here. Reaching the real one would put the network inside a
    case suite and make a verdict depend on a repository somebody could merge.
    """
    bindir = home / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    gh = bindir / "gh"
    match = ("|".join(merged)) if merged else "@none@"
    gh.write_text("#!/bin/sh\n"
                  "for a in \"$@\"; do\n"
                  "  case \"$a\" in %s) echo 1; exit 0;; esac\n"
                  "done\n"
                  "echo 0\n" % match)
    gh.chmod(0o755)
    return bindir


def sweep_cases(tmp, home, env):
    primary = make_repo(tmp, home, env, name="swept")
    root = home / "Development" / "worktrees" / "swept"
    for slug in ("landed", "orphan", "wip"):
        check("sweep fixture: %s cut" % slug,
              run_verb(env, primary, "new", slug).returncode, 0)

    git_quiet("commit", "-q", "--allow-empty", "-m", "work",
              cwd=str(root / "orphan"), env=env)
    (root / "wip" / "draft.txt").write_text("half done\n")

    # The sweep asks gh only about a remote gh could answer for, so origin has
    # to read as a GitHub one. `insteadOf` sends the fetch back to the local
    # bare repository, which keeps the network out of the case.
    bare = tmp / "remotes" / "bradley-t-t" / "swept.git"
    remote = "https://github.com/bradley-t-t/swept.git"
    git_quiet("config", "url.%s.insteadOf" % bare, remote, cwd=str(primary), env=env)
    git_quiet("remote", "set-url", "origin", remote, cwd=str(primary), env=env)
    swept = dict(env)
    swept["PATH"] = "%s%s%s" % (fake_gh(home, ["landed"]), os.pathsep, env["PATH"])

    p = run_verb(swept, primary, "sweep", "--dry-run")
    check("dry run names the landed tree",
          "swept 1 landed worktree(s): swept/landed" in p.stdout, True)
    check("dry run removes nothing", (root / "landed").is_dir(), True)

    p = run_verb(swept, primary, "sweep")
    check("sweep exits clean", p.returncode, 0)
    check("the landed tree is gone", (root / "landed").is_dir(), False)
    left = subprocess.run(("git", "rev-parse", "--verify", "--quiet",
                           "refs/heads/landed"), cwd=str(primary), env=env,
                          capture_output=True, text=True)
    check("its branch went with it", left.returncode == 0, False)
    check("a tree holding a commit stays", (root / "orphan").is_dir(), True)
    check("and is named", "swept/orphan" in p.stdout, True)
    check("with the commit as the reason", "on no remote" in p.stdout, True)
    check("a dirty tree stays", (root / "wip").is_dir(), True)
    check("and says why", "uncommitted changes" in p.stdout, True)

    runs = home / ".intelligence" / "state" / "design-runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "20260101-000000.json").write_text(json.dumps(
        {"id": "run1", "closed": False, "targets": [str(root / "orphan")]}))
    p = run_verb(swept, primary, "sweep")
    check("an open design run holds the tree", "design run run1" in p.stdout, True)

    residue = root / "residue" / "node_modules"
    residue.mkdir(parents=True)
    keeper = root / "keeper"
    keeper.mkdir()
    (keeper / "notes.txt").write_text("mine\n")
    run_verb(swept, primary, "sweep")
    check("build output left behind is residue", residue.parent.exists(), False)
    check("anything else keeps the directory", keeper.is_dir(), True)

    for slug in ("orphan", "wip", "keeper"):
        shutil.rmtree(root / slug, ignore_errors=True)
    git_quiet("worktree", "prune", cwd=str(primary), env=env)
    run_verb(swept, primary, "sweep")
    check("the repo directory goes with its last tree", root.exists(), False)


def no_develop_cases(tmp, home, env):
    primary = make_repo(tmp, home, env, name="flat", develop=False)
    check("guard: no develop branch, allowed",
          run_guard(env, primary / "src.py"), 0)
    p = run_verb(env, primary, "new", "anything")
    check("new: no develop branch refused", p.returncode, 2)
    check("new: says why", "origin/develop" in p.stderr, True)


def unowned_repo_cases(tmp, home, env):
    primary = make_repo(tmp, home, env, owner="thirdparty", name="dep")
    check("guard: unowned repo allowed", run_guard(env, primary / "src.py"), 0)


def usage_cases(env, home):
    check("usage: no verb", run_verb(env, home, ).returncode, 2)
    check("usage: unknown verb", run_verb(env, home, "frobnicate").returncode, 2)


def main():
    with tempfile.TemporaryDirectory() as tmp_a:
        tmp = Path(tmp_a)
        home = tmp / "home"
        home.mkdir()
        env = env_for(home)
        owned_repo_cases(tmp, home, env)
        usage_cases(env, home)
    with tempfile.TemporaryDirectory() as tmp_b:
        tmp = Path(tmp_b)
        home = tmp / "home"
        home.mkdir()
        env = env_for(home)
        no_develop_cases(tmp, home, env)
        unowned_repo_cases(tmp, home, env)
    with tempfile.TemporaryDirectory() as tmp_c:
        tmp = Path(tmp_c)
        home = tmp / "home"
        home.mkdir()
        sweep_cases(tmp, home, env_for(home))

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
