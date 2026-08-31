#!/usr/bin/env python3
"""Cases the dev server detector has to get right.

The detector exists for one failure: a worktree is removed and the server
started inside it keeps its port, so a later run either cannot bind or serves a
build from a tree that is gone. Killing the wrong one costs a session, so both
edges of every verdict are fixed here -- a served directory that has been
deleted and a landed branch settle as stale, a worktree a session is still
working in settles as live whatever its age, and a directory nothing claims
settles as unknown and is never taken by a default sweep.

The project roots and the transcript directory come from HOME at import, so the
run gets a temp HOME and every fixture lives inside it. Nothing here signals a
process: the sweep is exercised through --dry-run and the refusals in `end` are
called directly, because a fixture pid is a real pid on this machine.

  dev-servers-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "dev-servers.py")

FAILURES = []

HOUR = 3600.0


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def contains(label, text, want):
    if want not in text:
        FAILURES.append("%s: %r does not mention %r" % (label, text, want))


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_q(cwd, *args):
    done = subprocess.run(["git", "-C", str(cwd),
                           "-c", "user.email=cases@example.invalid",
                           "-c", "user.name=Cases",
                           "-c", "commit.gpgsign=false", *args],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError("git %s in %s: %s" % (" ".join(args), cwd, done.stderr.strip()))
    return done.stdout.strip()


def make_repo(home, name):
    """A primary checkout with one commit and an origin/develop ref on it.

    The remote ref is written directly rather than fetched, so the fixtures need
    no network and no second repository.
    """
    root = Path(home) / "Development" / "IdeaProjects" / name
    root.mkdir(parents=True)
    git_q(root, "init", "-q", "-b", "develop")
    (root / "README.md").write_text("fixture\n")
    git_q(root, "add", "-A")
    git_q(root, "commit", "-qm", "first")
    head = git_q(root, "rev-parse", "HEAD")
    git_q(root, "update-ref", "refs/remotes/origin/develop", head)
    return root


def cut(repo, home, slug, ahead=0):
    """A linked worktree under the worktrees root, optionally ahead of develop."""
    dest = Path(home) / "Development" / "worktrees" / repo.name / slug
    dest.parent.mkdir(parents=True, exist_ok=True)
    git_q(repo, "worktree", "add", "-q", "-b", slug, str(dest), "origin/develop")
    for n in range(ahead):
        (dest / ("work-%d.txt" % n)).write_text("change %d\n" % n)
        git_q(dest, "add", "-A")
        git_q(dest, "commit", "-qm", "work %d" % n)
    return dest


def age_tree(path, seconds):
    """Push every visible file in a tree back by `seconds`."""
    when = time.time() - seconds
    for base, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.startswith("."):
                continue
            os.utime(Path(base) / name, (when, when))


def server(mod, cwd, age=48 * HOUR, pid=424242, pgid=424242, command="node vite"):
    """One survey record, judged nowhere yet."""
    return {
        "pid": pid,
        "pgid": pgid,
        "ports": [5173],
        "command": command,
        "cwd": str(cwd) if cwd is not None else None,
        "age": age,
        "tree": mod.tree_state(str(cwd)) if cwd is not None else None,
        "verdict": "unknown",
        "evidence": [],
    }


def verdict(mod, cwd, **kw):
    record = server(mod, cwd, **kw)
    mod.judge(record, 12 * HOUR)
    return record


def write_run(state, kind, ident, repo, closed=None):
    folder = Path(state) / ("%s-runs" % kind)
    folder.mkdir(parents=True, exist_ok=True)
    body = {"id": ident, "repo": str(repo), "targets": [str(repo)]}
    if closed:
        body["closed"] = closed
    (folder / ("%s.json" % ident)).write_text(json.dumps(body))
    return folder / ("%s.json" % ident)


def parsing(mod):
    """Reading the process tables the verdicts are built on."""
    records = mod.parse_lsof("p101\nfcwd\nn/tmp/one\np202\nf3\nn*:4177\n")
    check("lsof groups names under the pid above them",
          records, {"101": ["/tmp/one"], "202": ["*:4177"]})

    check("etime hh:mm:ss", mod.elapsed_seconds("03:03:36"), 11016)
    check("etime dd-hh:mm:ss", mod.elapsed_seconds("4-05:12:33"), 364353)
    check("etime mm:ss", mod.elapsed_seconds("05:12"), 312)
    check("etime unreadable", mod.elapsed_seconds("later"), None)

    check("a duration under an hour reads in minutes", mod.span(1800), "30m")
    check("a duration under a day reads in hours", mod.span(18 * HOUR), "18h")
    check("a longer duration reads in days", mod.span(39 * HOUR), "1d")
    check("an unreadable duration says so", mod.span(None), "?")


def recognition(mod, home, worktree):
    """Which listeners are development and which are the machine's own."""
    check("a vite run is a dev server",
          mod.is_dev_server("node /x/node_modules/.bin/vite --port 5173", "/x"), True)
    check("an npm wrapper is a dev server",
          mod.is_dev_server("npm exec vite --port 5173 --strictPort", "/x"), True)
    check("a static serve is a dev server",
          mod.is_dev_server("node /x/node_modules/.bin/serve -s dist", "/x"), True)
    check("a python http.server is a dev server",
          mod.is_dev_server("Python -m http.server 4177", "/tmp/preview"), True)
    check("next dev is a dev server",
          mod.is_dev_server("node next dev", "/x"), True)

    # The command says nothing, so the directory has to: a script holding a port
    # from inside a worktree is the same failure under another name.
    check("an unrecognised command inside a checkout root is in scope",
          mod.is_dev_server("Python /tmp/capsink.py", str(worktree)), True)
    check("the same command outside every root is not",
          mod.is_dev_server("Python /tmp/capsink.py", "/tmp/elsewhere"), False)

    # An editor opened on a project has a project directory for a cwd, which is
    # exactly the reading that would take it for a server.
    check("an editor is never a dev server",
          mod.is_dev_server("/Applications/WebStorm.app/Contents/MacOS/webstorm",
                            str(worktree)), False)
    check("a background daemon is never a dev server",
          mod.is_dev_server("/usr/local/bin/tailscaled --state x", str(home)), False)
    check("a database is never a dev server",
          mod.is_dev_server("/opt/homebrew/opt/postgresql/bin/postgres -D d",
                            str(worktree)), False)


def orphaned(mod, home):
    """A server whose directory has been deleted is stale beyond argument."""
    gone = Path(home) / "Development" / "worktrees" / "app" / "removed"
    record = verdict(mod, gone, age=18 * HOUR)
    check("a deleted directory settles as stale", record["verdict"], "stale")
    contains("the missing directory is the reason given",
             record["evidence"][0], "no longer exists")

    unreadable = server(mod, None)
    mod.judge(unreadable, 12 * HOUR)
    check("a directory that could not be read is never swept by default",
          unreadable["verdict"], "unknown")


def landed(mod, repo, home):
    """A worktree whose branch is already in develop is stale however new it is."""
    tree = cut(repo, home, "shipped")
    record = verdict(mod, tree, age=5 * 60)
    check("a landed branch settles as stale", record["verdict"], "stale")
    contains("the landed branch is the reason given",
             record["evidence"][0], "already in origin/develop")
    check("a landed worktree holds nothing back", mod.holdings(record), [])


def live_worktree(mod, repo, home):
    """A worktree with unlanded work, recently touched, is never swept."""
    tree = cut(repo, home, "in-flight", ahead=1)
    record = verdict(mod, tree, age=3 * HOUR)
    check("a young server on an unlanded worktree is live", record["verdict"], "live")
    holds = mod.holdings(record)
    check("its unlanded commit is surfaced anyway", len(holds), 1)
    contains("the branch and its commit count are named", holds[0], "in-flight carries 1")

    # Age narrows a reading evidence has opened; it never opens one. The same
    # tree, untouched and serving for days, stops being live and does not
    # become stale either.
    age_tree(tree, 40 * HOUR)
    stale_looking = verdict(mod, tree, age=39 * HOUR)
    check("the same worktree gone quiet is not swept",
          stale_looking["verdict"], "unknown")
    contains("the quiet is the reason given",
             stale_looking["evidence"][0], "nothing here for")
    contains("the unlanded commit is still surfaced",
             mod.holdings(stale_looking)[0], "not in origin/develop")
    return tree


def ownership(mod, tree, state, home):
    """A session working in the directory outranks every staleness reading."""
    open_run = write_run(state, "design", "20260828-000001", tree)
    record = verdict(mod, tree, age=39 * HOUR)
    check("an open checklist run makes it live", record["verdict"], "live")
    contains("the run is named", record["evidence"][0], "design:20260828-000001")

    open_run.write_text(json.dumps({"id": "20260828-000001", "repo": str(tree),
                                    "targets": [str(tree)],
                                    "closed": "2026-08-28 12:43:39Z"}))
    check("a closed run claims nothing",
          verdict(mod, tree, age=39 * HOUR)["verdict"], "unknown")

    # A pointer names the run it belongs to and nothing else, so a directory is
    # only ever claimed by the run file itself.
    (Path(state) / "design-runs" / "current-abc.json").write_text('{"id": "x"}')
    check("a run pointer claims nothing on its own",
          verdict(mod, tree, age=39 * HOUR)["verdict"], "unknown")

    (Path(state) / "design-runs" / "torn.json").write_text("{not json")
    check("an unreadable run file claims nothing",
          verdict(mod, tree, age=39 * HOUR)["verdict"], "unknown")
    (Path(state) / "design-runs" / "torn.json").unlink()

    # Every engine that files runs is read, not only design.
    for kind in ("seo", "perf", "stack", "db"):
        ident = "%s-20260828-000002" % kind
        write_run(state, kind, ident, Path(tree) / "src")
        record = verdict(mod, tree, age=39 * HOUR)
        check("an open %s run over something inside the directory claims it" % kind,
              record["verdict"], "live")
        (Path(state) / ("%s-runs" % kind) / ("%s.json" % ident)).unlink()

    sessions = Path(home) / ".intelligence" / "projects" / \
        str(tree).replace("/", "-").replace(".", "-")
    sessions.mkdir(parents=True)
    (sessions / "s.jsonl").write_text("{}\n")
    check("a session transcript against the directory makes it live",
          verdict(mod, tree, age=39 * HOUR)["verdict"], "live")

    old = time.time() - 40 * HOUR
    os.utime(sessions / "s.jsonl", (old, old))
    check("a transcript older than the window claims nothing",
          verdict(mod, tree, age=39 * HOUR)["verdict"], "unknown")


def unclaimed(mod, home):
    """A directory that is no checkout at all is reported, never swept."""
    plain = Path(home) / "Development" / "scratch"
    plain.mkdir(parents=True)
    (plain / "index.html").write_text("<p>x</p>")
    age_tree(plain, 72 * HOUR)
    record = verdict(mod, plain, age=72 * HOUR, command="Python -m http.server 4177")
    check("a served directory nothing claims settles as unknown",
          record["verdict"], "unknown")
    contains("what would settle it is named",
             record["evidence"][0], "no session claims the directory")
    check("it holds nothing to land", mod.holdings(record), [])
    return plain


def refusals(mod):
    """The groups `end` will not signal, and the one it will.

    Every signal is recorded rather than delivered for the length of this
    function. A case that hands `end` a real group and trusts the guard under
    test to refuse it is a case that ends the run whenever the guard is the
    thing that broke -- and one of those groups is this process's own.
    """
    sent = []

    def record(pgid, sig):
        sent.append((pgid, sig))
        # A group that has been signalled is gone by the next probe, which is
        # what the wait in `end` is looking for.
        if sig == 0:
            raise ProcessLookupError(pgid)

    real = os.killpg
    os.killpg = record
    try:
        table = {1: {"pgid": 1, "age": 1.0, "command": "/sbin/launchd"}}
        ok, why = mod.end({"pgid": 0, "pid": 5, "ports": [1], "cwd": "/x"}, table)
        check("group 0 is refused", ok, False)
        contains("and says why", why, "not a job")
        check("nothing was signalled", sent, [])

        ok, why = mod.end({"pgid": 1, "pid": 5, "ports": [1], "cwd": "/x"}, table)
        check("group 1 is refused", ok, False)
        check("still nothing signalled", sent, [])

        own = os.getpgid(0)
        ok, why = mod.end({"pgid": own, "pid": os.getpid(), "ports": [1],
                           "cwd": "/x"}, {})
        check("this process's own group is refused", ok, False)
        contains("and says why", why, "own group")
        check("this process's group was never signalled", sent, [])

        # A group holding an application is not a dev server's job, whatever the
        # listener in it looks like.
        mixed = {900: {"pgid": 900, "age": 1.0, "command": "node vite"},
                 901: {"pgid": 900, "age": 1.0,
                       "command": "/Applications/WebStorm.app/Contents/MacOS/webstorm"}}
        ok, why = mod.end({"pgid": 900, "pid": 900, "ports": [1], "cwd": "/x"}, mixed)
        check("a group holding an application is refused", ok, False)
        contains("and names what is in it", why, "901")
        check("the mixed group was never signalled", sent, [])

        # The wrapper and the listener share a group, so the group is what a
        # sweep takes: ending the child alone leaves the wrapper standing.
        job = {910: {"pgid": 910, "age": 1.0, "command": "npm exec vite"},
               911: {"pgid": 910, "age": 1.0, "command": "node vite --port 5173"}}
        ok, why = mod.end({"pgid": 910, "pid": 911, "ports": [5173], "cwd": "/x"}, job)
        check("a dev server's own group is ended", ok, True)
        check("the whole group took the signal", sent, [(910, 15), (910, 0)])
        contains("and the count is reported", why, "2 process(es)")
    finally:
        os.killpg = real


def shim(bin_dir, name, body):
    path = Path(bin_dir) / name
    path.write_text("#!/bin/sh\n%s\n" % body)
    path.chmod(0o755)


def verbs(mod, home, live, gone, unclaimed_dir, state):
    """The two verbs, end to end, over one of each verdict.

    Nothing is signalled: `sweep` runs with --dry-run throughout, so a fixture
    pid that happens to name a real process on this machine is never touched.
    """
    bin_dir = Path(home) / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    ports = 'printf "p700\\nf3\\nn127.0.0.1:5202\\np701\\nf3\\nn*:4402\\n' \
            'p702\\nf3\\nn[::1]:4177\\np702\\nf4\\nn127.0.0.1:4177\\n"'
    cwds = 'printf "p700\\nfcwd\\nn%s\\np701\\nfcwd\\nn%s\\np702\\nfcwd\\nn%s\\n"' \
           % (live, gone, unclaimed_dir)
    shim(bin_dir, "lsof",
         'case "$*" in\n  *cwd*) %s ;;\n  *) %s ;;\nesac' % (cwds, ports))
    shim(bin_dir, "ps",
         'printf "700 700 03:00:00 node %s/node_modules/.bin/vite --port 5202\\n'
         '701 701 39:00:00 node serve -s dist\\n'
         '702 702 3-01:00:00 Python -m http.server 4177\\n"' % live)

    env = dict(os.environ)
    env["PATH"] = "%s:%s" % (bin_dir, env["PATH"])
    env["HOME"] = str(home)
    env["INTELLIGENCE_STATE_DIR"] = str(state)

    def run(*args):
        done = subprocess.run([sys.executable, str(TARGET), *args],
                              capture_output=True, text=True, env=env, timeout=120)
        return done.returncode, done.stdout + done.stderr

    code, out = run("report")
    check("report exits non-zero while something is stale", code, 1)
    contains("report names the port the stale one holds", out, "4402")
    contains("report names the port the live one holds", out, "5202")
    contains("report names the port the unclaimed one holds", out, "4177")

    code, out = run("report", "--json")
    rows = json.loads(out)
    check("a port bound on both stacks is counted once",
          [r["ports"] for r in rows if r["pid"] == 702], [[4177]])
    check("the record carries one verdict per server",
          {r["ports"][0]: r["verdict"] for r in rows},
          {5202: "live", 4402: "stale", 4177: "unknown"})
    check("the record carries the unlanded work",
          [r["holds"] for r in rows if r["pid"] == 700][0] != [], True)

    code, out = run("sweep", "--dry-run")
    contains("a dry sweep offers to end the deleted directory's server",
             out, "would end 4402")
    check("it does not offer to end the live one", "would end 5202" in out, False)
    check("it does not offer to end the unclaimed one",
          "would end 4177" in out, False)
    contains("it names the unclaimed one it left", out, "left 4177")
    contains("it carries the unlanded work forward", out, "holds:")

    code, out = run("sweep", "--dry-run", "--include-unknown")
    contains("asked for them, it takes the unclaimed one too",
             out, "would end 4177")
    check("it still never offers to end the live one",
          "would end 5202" in out, False)

    code, out = run("no-such-verb")
    check("an unknown verb prints the usage and refuses", code, 2)
    contains("the usage names the verbs", out, "sweep")


def main():
    with tempfile.TemporaryDirectory() as home:
        os.environ["HOME"] = home
        state = Path(home) / "state"
        state.mkdir()
        os.environ["INTELLIGENCE_STATE_DIR"] = str(state)
        mod = load()

        repo = make_repo(home, "app")
        scratch = cut(repo, home, "recognise")

        parsing(mod)
        recognition(mod, home, scratch)
        orphaned(mod, home)
        landed(mod, repo, home)
        tree = live_worktree(mod, repo, home)
        ownership(mod, tree, state, home)
        plain = unclaimed(mod, home)
        refusals(mod)
        verbs(mod, home, tree,
              Path(home) / "Development" / "worktrees" / "app" / "removed",
              plain, state)

    if FAILURES:
        print("dev-servers.py fails %d case(s):" % len(FAILURES))
        for line in FAILURES:
            print("  " + line)
        return 1
    print("dev-servers.py holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
