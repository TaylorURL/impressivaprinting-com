#!/usr/bin/env python3
"""Dev servers still listening on this machine, and which of them nothing owns.

A worktree is removed while the `vite` or `serve` started inside it keeps
running. The directory goes and the process does not. It holds its port, so the
next run asking for that port with --strictPort fails outright, and where the
port is taken without one, a visitor is served the previous build out of a tree
that no longer exists. That last one is the failure that costs something, and it
looks exactly like a working server.

Nothing else looks for these, so they accumulate.

A verdict rests on evidence. Two readings are conclusive on their own: a served
directory that is gone, and a worktree whose branch is already an ancestor of
origin/develop. Ownership is the other side of it -- a checklist run still open
over the directory, a session transcript against it, or a live worktree whose
server started inside the window -- and a server with ownership behind it is
never touched. Age is a signal inside one of those readings and never a verdict
by itself. What answers to neither reading is reported and left running: a wrong
kill costs someone a session, a missed one costs a port.

  report          every dev server found, what it serves, and the verdict
  sweep           end the ones judged stale, process group and all

  --json          report as a record rather than a table
  --dry-run       name what sweep would end, and end nothing
  --include-unknown
                  extend sweep to the servers ownership could not settle;
                  the default sweep never takes one
  --window HOURS  how recently evidence has to land to read as live (12)

report exits non-zero while anything is judged stale, so a run that ignores it
is not a run that answered it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()

# The roots a checkout of this machine's own work lives under. A listener whose
# directory sits inside one is development whatever it is running, which is what
# catches a capture sink or a one-off script holding a port from a worktree.
PROJECT_ROOTS = (
    HOME / "Development" / "worktrees",
    HOME / "Development" / "IdeaProjects",
    HOME / "Development" / "WebstormProjects",
    HOME / "Projects",
)

# Session transcripts are filed under the directory the session runs in, with
# the separators flattened. The directory's own timestamp is enough: it moves
# whenever a transcript in it is written.
SESSIONS = HOME / ".intelligence" / "projects"

# The runners a dev server is normally started through. Matched against the
# whole command line, so `npm exec vite` and a node path ending in vite both
# read as one.
RUNNERS = re.compile(
    r"(?:^|/|\s)(?:vite|next|nuxt|astro|remix|parcel|snowpack|gatsby|docusaurus"
    r"|webpack(?:-dev-server)?|serve|sirv|http-server|live-server|browser-sync"
    r"|storybook|start-storybook|ng|rails|hugo|jekyll|uvicorn|gunicorn|flask"
    r"|wrangler|netlify|vercel|turbo|nodemon|ts-node-dev|bun|deno)\b"
    r"|python[0-9.]*\s+-m\s+http\.server"
    r"|\bphp\s+-S\b"
    r"|\bmanage\.py\s+runserver\b"
    r"|\b(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:dev|start|serve|preview|exec)\b",
    re.I,
)

# Applications that listen as part of what they are. An editor opened on a
# project has a project directory for a cwd and is not a dev server.
NOT_A_SERVER = re.compile(
    r"(?:^|/)(?:webstorm|idea|pycharm|goland|rubymine|clion|phpstorm|fleet"
    r"|code|codium|cursor|zed|sublime_text|emacs"
    r"|Google Chrome|Firefox|Safari|Arc|Brave Browser"
    r"|Discord|Slack|Spotify|Docker|com\.docker|OrbStack|Postgres|mysqld|redis-server"
    r"|tailscaled?|rapportd|ControlCe|sharingd|cef_server|sshd|ssh"
    r"|node_modules/\.bin/electron|Electron)\b",
    re.I,
)

DEFAULT_WINDOW_HOURS = 12.0

# The checklist engines keep one file per run under here. A run without a
# `closed` stamp is a session still working in the directories it names.
RUN_KINDS = ("design", "seo", "perf", "stack", "db")


def state_root():
    """Where the checklist engines keep their run files on this machine."""
    override = os.environ.get("INTELLIGENCE_STATE_DIR")
    if override:
        return Path(override)
    if os.environ.get("CLAUDE_CODE_REMOTE"):
        return HOME / ".pass-state"
    return HOME / ".intelligence" / "state"


def sh(args):
    """Stdout of a command, or "" when it cannot run."""
    try:
        done = subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError:
        return ""
    return done.stdout


def git(directory, *args):
    """Stripped stdout of a git command in `directory`, or "" when it failed."""
    try:
        done = subprocess.run(("git", "-C", str(directory), *args),
                              capture_output=True, text=True, check=False)
    except OSError:
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def git_ok(directory, *args):
    try:
        done = subprocess.run(("git", "-C", str(directory), *args),
                              capture_output=True, text=True, check=False)
    except OSError:
        return False
    return done.returncode == 0


def parse_lsof(text):
    """The `-F` records of lsof as {pid: [name]}.

    lsof emits a `p<pid>` line and then a run of file records under it, so the
    pid in force is carried down the lines rather than read off each one.
    """
    found, pid = {}, None
    for line in text.splitlines():
        if not line:
            continue
        tag, value = line[0], line[1:]
        if tag == "p":
            pid = value.strip()
            found.setdefault(pid, [])
        elif tag == "n" and pid is not None:
            found[pid].append(value.strip())
    return found


def lsof(*args):
    """lsof's field output, from PATH or from the location it installs to."""
    text = sh(["lsof", *args])
    return text if text else sh(["/usr/sbin/lsof", *args])


def listeners():
    """Every listening TCP port on this machine, as {pid: sorted ports}."""
    ports = {}
    for pid, names in parse_lsof(lsof("-nP", "-iTCP", "-sTCP:LISTEN", "-Fpn")).items():
        seen = set()
        for name in names:
            # Addresses arrive as `*:5173`, `127.0.0.1:5173` or `[::1]:5173`,
            # and a port bound on both stacks appears once per family.
            port = name.rsplit(":", 1)[-1]
            if port.isdigit():
                seen.add(int(port))
        if seen and pid.isdigit():
            ports[int(pid)] = sorted(seen)
    return ports


def working_dirs(pids):
    """The working directory of each pid, read from the process itself.

    A command line names the directory it serves about as often as it does not:
    a bare `vite` or `serve -s dist` carries the tree only in the cwd. lsof
    reports the path of a directory that has since been deleted, which is what
    makes its absence readable.
    """
    if not pids:
        return {}
    arg = ",".join(str(p) for p in pids)
    records = parse_lsof(lsof("-a", "-p", arg, "-d", "cwd", "-Fpn"))
    return {int(pid): names[0] for pid, names in records.items()
            if names and pid.isdigit()}


ETIME = re.compile(r"^(?:(?:(\d+)-)?(\d+):)?(\d+):(\d+)$")


def elapsed_seconds(etime):
    """Seconds from ps's `[[dd-]hh:]mm:ss` elapsed field, or None."""
    match = ETIME.match(etime.strip())
    if not match:
        return None
    days, hours_, minutes, seconds = (int(g or 0) for g in match.groups())
    return ((days * 24 + hours_) * 60 + minutes) * 60 + seconds


def process_table():
    """Every process as {pid: {pgid, age, command}}."""
    table = {}
    for line in sh(["ps", "-Ao", "pid=,pgid=,etime=,command="]).splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4 or not parts[0].isdigit():
            continue
        pid, pgid, etime, command = parts
        table[int(pid)] = {
            "pgid": int(pgid) if pgid.isdigit() else 0,
            "age": elapsed_seconds(etime),
            "command": command.strip(),
        }
    return table


def is_dev_server(command, cwd):
    """Whether a listener is development rather than an installed application.

    Two ways in, because neither covers the other: the command is one of the
    runners a dev server is started through, or the directory it serves from is
    inside a checkout root, which is where a script nobody would recognise still
    holds a port belonging to a project.
    """
    if NOT_A_SERVER.search(command):
        return False
    if RUNNERS.search(command):
        return True
    if not cwd:
        return False
    path = Path(cwd)
    return any(root == path or root in path.parents for root in PROJECT_ROOTS)


def tree_state(cwd):
    """What git knows about the directory a server runs in.

    Returns None when it is not a checkout. `worktree` distinguishes a linked
    tree from the primary one: a linked tree's git dir sits under
    `.git/worktrees/<name>`, and only a linked tree is one this workflow cuts,
    lands, and removes.
    """
    if not cwd or not Path(cwd).is_dir():
        return None
    top = git(cwd, "rev-parse", "--show-toplevel")
    if not top:
        return None
    gitdir = git(cwd, "rev-parse", "--absolute-git-dir")
    state = {
        "root": top,
        "worktree": bool(gitdir) and Path(gitdir).parent.name == "worktrees",
        "branch": git(cwd, "branch", "--show-current"),
        "landed": False,
        "ahead": 0,
        "dirty": len([l for l in git(cwd, "status", "--porcelain").splitlines() if l]),
    }
    if git(cwd, "rev-parse", "--verify", "--quiet", "origin/develop"):
        state["landed"] = git_ok(cwd, "merge-base", "--is-ancestor",
                                 "HEAD", "origin/develop")
        count = git(cwd, "rev-list", "--count", "origin/develop..HEAD")
        state["ahead"] = int(count) if count.isdigit() else 0
    return state


def covers(directory, candidate):
    """Whether `candidate` is `directory` or something inside it, either way up."""
    try:
        a = Path(directory).resolve()
        b = Path(candidate).resolve()
    except OSError:
        return False
    return a == b or a in b.parents or b in a.parents


def open_runs(directory):
    """The checklist runs still open over a directory, as `kind:id` strings.

    This is the reading `worktree.py` takes before removing a tree, widened from
    design to every engine that files runs. A run without a `closed` stamp
    belongs to a session that has not finished with the directory it named.
    """
    root = state_root()
    held = []
    for kind in RUN_KINDS:
        folder = root / ("%s-runs" % kind)
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.json")):
            # A `current-*.json` is a pointer holding an id and no targets; the
            # run it names is read here under its own name.
            if path.name.startswith("current"):
                continue
            try:
                run = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if not isinstance(run, dict) or run.get("closed"):
                continue
            places = list(run.get("targets") or [])
            if run.get("repo"):
                places.append(run["repo"])
            if any(covers(directory, place) for place in places):
                held.append("%s:%s" % (kind, run.get("id") or path.stem))
    return held


def transcript_age(directory):
    """Seconds since a session last wrote a transcript for a directory, or None."""
    if not SESSIONS.is_dir():
        return None
    encoded = str(Path(directory)).replace("/", "-").replace(".", "-")
    folder = SESSIONS / encoded
    if not folder.is_dir():
        return None
    newest = None
    for path in folder.glob("*.jsonl"):
        try:
            stamp = path.stat().st_mtime
        except OSError:
            continue
        newest = stamp if newest is None else max(newest, stamp)
    return None if newest is None else max(0.0, time.time() - newest)


# Directories whose contents say nothing about when anyone last worked in a
# tree: installed packages and build output are written by a build rather than
# by a person, and walking them costs more than the rest of the tree together.
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".next", ".nuxt",
             ".output", ".turbo", ".vite", "coverage", "__pycache__",
             ".venv", "venv", "target", "vendor"}

WALK_BUDGET = 4000


def tree_write_age(directory):
    """Seconds since the tree was last written, or None when nothing is readable.

    Bounded rather than exhaustive: the walk stops at a fixed number of entries,
    which is enough to date a source tree and keeps a large checkout from turning
    a report into a scan.
    """
    root = Path(directory)
    if not root.is_dir():
        return None
    newest, seen = None, 0
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            # A linked worktree's `.git` pointer is stamped when the tree is cut
            # and dates the tree rather than the work in it; the same goes for
            # every other hidden file a tool keeps beside the source.
            if name.startswith("."):
                continue
            seen += 1
            try:
                stamp = (Path(base) / name).stat().st_mtime
            except OSError:
                continue
            newest = stamp if newest is None else max(newest, stamp)
        if seen >= WALK_BUDGET:
            break
    return None if newest is None else max(0.0, time.time() - newest)


def span(seconds):
    """A duration at the coarsest unit that still says something."""
    if seconds is None:
        return "?"
    if seconds < 3600:
        return "%dm" % (seconds // 60)
    if seconds < 86400:
        return "%dh" % (seconds // 3600)
    return "%dd" % (seconds // 86400)


def short(path):
    text = str(path)
    home = str(HOME)
    return "~" + text[len(home):] if text.startswith(home) else text


def judge(server, window):
    """Settle one server into live, stale, or unknown, and say on what.

    The order carries the safety rule. A directory that is gone is beyond
    argument, so it is read first. Ownership is read next, ahead of the
    landed-branch reading, because a session working in a tree whose branch has
    already landed is still a session working in it. Age only ever narrows a
    reading that evidence has already opened.
    """
    cwd = server["cwd"]

    if not cwd:
        server["verdict"] = "unknown"
        server["evidence"] = ["its working directory could not be read"]
        return
    if not Path(cwd).is_dir():
        server["verdict"] = "stale"
        server["evidence"] = ["the directory it serves from no longer exists"]
        return

    held = open_runs(cwd)
    if held:
        server["verdict"] = "live"
        server["evidence"] = ["%s is open over this directory" % ", ".join(held)]
        return

    session = transcript_age(cwd)
    if session is not None and session <= window:
        server["verdict"] = "live"
        server["evidence"] = ["a session wrote here %s ago" % span(session)]
        return

    tree = server["tree"]
    if tree and tree["worktree"] and tree["landed"]:
        server["verdict"] = "stale"
        server["evidence"] = ["%s is already in origin/develop"
                              % (tree["branch"] or "its branch")]
        return

    if tree and tree["worktree"]:
        stamps = [x for x in (tree_write_age(cwd), server["age"]) if x is not None]
        freshest = min(stamps) if stamps else None
        if freshest is not None and freshest <= window:
            server["verdict"] = "live"
            server["evidence"] = ["an unlanded worktree, worked %s ago"
                                  % span(freshest)]
            return
        server["evidence"] = ["an unlanded worktree, nothing here for %s"
                              % span(freshest)]
    else:
        server["evidence"] = ["not a worktree, and no session claims the directory"]
    server["verdict"] = "unknown"


def survey(window):
    """Every dev server on this machine, judged."""
    ports = listeners()
    table = process_table()
    dirs = working_dirs(list(ports))
    found = []
    for pid, open_ports in sorted(ports.items()):
        info = table.get(pid)
        if not info:
            continue
        cwd = dirs.get(pid)
        if not is_dev_server(info["command"], cwd):
            continue
        server = {
            "pid": pid,
            "pgid": info["pgid"],
            "ports": open_ports,
            "command": info["command"],
            "cwd": cwd,
            "age": info["age"],
            "tree": tree_state(cwd),
            "verdict": "unknown",
            "evidence": [],
        }
        judge(server, window)
        found.append(server)
    return found


def holdings(server):
    """What ending a server leaves behind in the tree it served.

    Ending a process is not landing the work of the tree it served. A branch
    carrying commits that never reached develop is a finding of its own, and a
    sweep reporting only the ports it freed buries it.
    """
    tree = server["tree"]
    if not tree or not tree["worktree"]:
        return []
    notes = []
    if tree["ahead"]:
        notes.append("%s carries %d commit(s) not in origin/develop"
                     % (tree["branch"] or "its branch", tree["ahead"]))
    if tree["dirty"]:
        notes.append("%d uncommitted file(s) in the tree" % tree["dirty"])
    return notes


def group_members(pgid, table):
    return [pid for pid, info in table.items() if info["pgid"] == pgid]


def end(server, table):
    """End a server's whole process group, and say what happened.

    The listener is regularly the child of a wrapper -- `npm exec vite` in front
    of the node that binds the port -- and ending only the child leaves the
    wrapper to restart it or to sit as the next thing nobody looks for. Both
    share a process group, so the group is the unit. A group holding this
    process, or one that is not a job at all, is refused rather than signalled.
    """
    pgid = server["pgid"]
    if pgid <= 1:
        return False, "process group %d is not a job" % pgid
    try:
        own = os.getpgid(0)
    except OSError:
        own = -1
    if pgid == own:
        return False, "that is this process's own group"
    members = group_members(pgid, table)
    guarded = [pid for pid in members if NOT_A_SERVER.search(table[pid]["command"])]
    if guarded:
        return False, ("group %d also holds %s"
                       % (pgid, ", ".join(str(p) for p in sorted(guarded))))
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return True, "already gone"
    except PermissionError:
        return False, "no permission to signal group %d" % pgid
    except OSError as error:
        return False, "group %d: %s" % (pgid, error)

    deadline = time.time() + 5.0
    while time.time() < deadline:
        try:
            os.killpg(pgid, 0)
        except (ProcessLookupError, PermissionError):
            return True, "ended group %d (%d process(es))" % (pgid, len(members))
        time.sleep(0.2)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except OSError:
        pass
    return True, "ended group %d after SIGKILL (%d process(es))" % (pgid, len(members))


ORDER = {"stale": 0, "unknown": 1, "live": 2}


def label(server):
    return "%s pid %d %s" % (",".join(str(p) for p in server["ports"]),
                             server["pid"], short(server["cwd"] or "?"))


def render(servers):
    """The table, with each server's evidence and holdings under its row."""
    if not servers:
        print("no dev servers listening")
        return
    print("%-9s %-7s %-8s %-6s %s" % ("PORT", "PID", "VERDICT", "AGE", "SERVES"))
    for server in sorted(servers, key=lambda s: (ORDER[s["verdict"]], s["ports"])):
        print("%-9s %-7d %-8s %-6s %s" % (
            ",".join(str(p) for p in server["ports"]),
            server["pid"],
            server["verdict"],
            span(server["age"]),
            short(server["cwd"] or "?"),
        ))
        for line in server["evidence"]:
            print("          %s" % line)
        for line in holdings(server):
            print("          holds: %s" % line)


def cmd_report(args):
    servers = survey(args.window * 3600)
    if args.json:
        record = [dict({k: v for k, v in s.items() if k != "tree"},
                       holds=holdings(s)) for s in servers]
        print(json.dumps(record, indent=2, sort_keys=True))
    else:
        render(servers)
    return 1 if any(s["verdict"] == "stale" for s in servers) else 0


def cmd_sweep(args):
    servers = survey(args.window * 3600)
    table = process_table()
    wanted = {"stale"} | ({"unknown"} if args.include_unknown else set())
    targets = [s for s in servers if s["verdict"] in wanted]
    left = []

    for server in targets:
        if args.dry_run:
            print("would end %s (%s)" % (label(server), server["verdict"]))
        else:
            ok, message = end(server, table)
            print("%s %s -- %s" % ("ended" if ok else "kept", label(server), message))
            if not ok:
                left.append(server)
        for line in holdings(server):
            print("  holds: %s" % line)

    # A server the sweep is not allowed to decide is named rather than passed
    # over: the port it holds and the branch under it are both findings.
    for server in servers:
        if server in targets:
            continue
        if server["verdict"] == "live" and not holdings(server):
            continue
        print("left %s -- %s" % (label(server), "; ".join(server["evidence"])))
        for line in holdings(server):
            print("  holds: %s" % line)

    if not targets:
        print("nothing to sweep; %d dev server(s) standing" % len(servers))
    return 1 if left else 0


COMMANDS = {"report": cmd_report, "sweep": cmd_sweep}


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("verb", nargs="?", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-unknown", action="store_true")
    parser.add_argument("--window", type=float, default=float(
        os.environ.get("INTELLIGENCE_DEV_SERVER_WINDOW") or DEFAULT_WINDOW_HOURS))
    args, _ = parser.parse_known_args()
    if args.verb not in COMMANDS:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return COMMANDS[args.verb](args)


if __name__ == "__main__":
    sys.exit(main())
