#!/usr/bin/env python3
"""Work this machine holds that nothing else knows about, and how long it has sat there.

A checkout is fine at the moment it is written and rots quietly afterwards. The
base branch moves under it, the diff stops applying, and a branch that took an
afternoon takes a rewrite. Nothing else in the workflow watches for that: git
reads clean, the remote shows nothing missing, and the tree looks exactly the
way it looked when the work was good.

Three things go stale, and they are not the same kind of problem:

  uncommitted changes   one disk away from gone, and invisible to every clone
  local-only commits    committed, so they look safe, and still on one machine
  drift from the base   the ground moved; the longer it moves the worse the merge

The first two are work at risk and are never touched here -- what to do with an
edit somebody is part-way through is a judgement, and a tool that guesses at it
destroys the thing it was watching. Drift is the opposite: a clean branch that
is merely behind is brought forward by a fetch and a rebase with nothing to
decide, so `repair` does exactly that and reports whatever it could not settle.

  stranded.py report [--all] [--offline] [--json]  what is at risk, and for how long
  stranded.py repair [--json]                      fetch, rebase what is clean, report the rest

`report` refreshes the remote refs before it measures anything, and `repair`
does the same. It has to: the whole reading is a comparison against remotes, and
a branch deleted when its pull request merged leaves a tracking ref behind that
goes on answering for it, so a commit no remote has still reads as published
until something prunes. `--offline` skips the refresh for a run that cannot
reach the network, and measures against whatever the last fetch left.

Exit is non-zero while anything is stranded, which is what lets a health check
and a scheduled routine both gate on it.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent

HOUR = 3600.0

# A working day is the unit for all three clocks. Work that has survived one is
# work nobody is holding: an edit still uncommitted the next morning, a commit
# that spent a day on a single disk, a base commit a branch has gone a day
# without.
#
# The clock alone is too slow for a repository that moves in bursts. The two
# busiest here land around 90 and 165 commits a day on their base branch, so a
# day of drift there is several hundred commits and the damage is done long
# before the clock says anything. The count is the second trigger and fires
# first in exactly those repositories: it sits above the busiest full week any
# of the slower repositories has, so it never front-runs the clock where the
# clock is the better measure, and it is roughly six hours in the two fast ones,
# where it is.
HELD_HOURS = 24.0
DRIFT_HOURS = 24.0
DRIFT_COMMITS = 40

# Worst first. A tree can be several of these at once and is named by the one
# that decides what happens to it.
ORDER = ("holds", "blocked", "drifted", "clear")


def load(stem):
    """A sibling tool as a module, found by path.

    The names carry hyphens and the tools run as scripts, so nothing about them
    is importable by name. Loading them anyway is what keeps one answer to where
    the checkouts are: the project roots, the worktrees root, and the rule that
    a repository is held once all live in those files.
    """
    path = TOOLS / (stem + ".py")
    spec = importlib.util.spec_from_file_location(
        "intelligence_" + stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preflight = load("repo-preflight")
worktrees = load("worktree")


def git(cwd, *args, timeout=60):
    """Git's stdout, stripped, or None where the command failed."""
    try:
        done = subprocess.run(["git", "-C", str(cwd), *args],
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def git_ok(cwd, *args, timeout=300):
    """Whether a git command succeeded, and everything it said."""
    try:
        done = subprocess.run(["git", "-C", str(cwd), *args],
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as why:
        return False, str(why)
    return done.returncode == 0, ((done.stdout or "") + (done.stderr or "")).strip()


def common_dir(path):
    """The object store a tree shares with its siblings.

    Every worktree of a repository answers with the same path, which is what
    makes it the key for fetching once per repository rather than once per tree.
    """
    found = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return found or str(Path(path) / ".git")


def every_tree():
    """Every checkout and worktree on this machine, deduplicated by real path.

    Two sweeps, because neither is complete alone. `repo-preflight` finds the
    primary checkouts under the project roots and each of those names its own
    linked worktrees; a worktree whose primary sits outside the roots is
    reachable only from the worktrees root itself.
    """
    seen, found = set(), []

    def add(path):
        real = os.path.realpath(path)
        if real in seen:
            return
        seen.add(real)
        found.append(path)

    for primary in preflight.every_checkout():
        add(primary)
        listing = git(primary, "worktree", "list", "--porcelain") or ""
        for line in listing.splitlines():
            if line.startswith("worktree "):
                add(line.split(" ", 1)[1])

    root = worktrees.ROOT
    if root.is_dir():
        for repo in sorted(root.iterdir()):
            if not repo.is_dir():
                continue
            for tree in sorted(repo.iterdir()):
                if (tree / ".git").exists():
                    add(str(tree))

    return found


def base_ref(tree):
    """The branch this work is measured against.

    `origin/develop` is the branch every unit of work is cut from, so it is the
    branch every unit of work is judged against. A repository outside that model
    falls back to `origin/main`, and one with neither is measured against
    whatever the current branch tracks.
    """
    for ref in ("origin/develop", "origin/main"):
        if git(tree, "rev-parse", "--verify", "--quiet", ref):
            return ref
    upstream = git(tree, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    return upstream if upstream and "\n" not in upstream else None


def dirty_paths(tree):
    """Every path git reports as changed, rename targets included.

    The NUL-separated form is what is read, because a path holding a space or a
    quote arrives escaped in the human-readable one and an escaped path cannot
    be opened to ask how old it is.
    """
    try:
        done = subprocess.run(["git", "-C", str(tree), "status", "--porcelain=v1", "-z"],
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return []
    if done.returncode != 0:
        return []
    fields = [f for f in done.stdout.split("\0") if f]
    paths, index = [], 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        paths.append(path)
        # A rename or a copy carries its source as the next field.
        if "R" in status or "C" in status:
            index += 1
    return paths


def newest_change(tree, paths):
    """How recently anything in the working tree moved, in hours.

    The most recent edit is what says whether somebody is holding this work. A
    tree whose newest change is minutes old is being worked in; one whose newest
    change is a day old is not, whatever else it holds. A deleted path cannot be
    stat'd, so the index stands in for it -- removing a file writes it.
    """
    now = time.time()
    stamps = []
    for path in paths:
        try:
            stamps.append(os.stat(os.path.join(str(tree), path)).st_mtime)
        except OSError:
            continue
    if not stamps:
        index = Path(common_dir(tree)) / "index"
        try:
            stamps.append(index.stat().st_mtime)
        except OSError:
            return None
    return (now - max(stamps)) / HOUR


# When a commit landed, and when the work in it was written. A rebase stamps a
# new committer date on every commit it moves and leaves the author date alone,
# so local work measured by the committer date reads as minutes old the moment
# anything brings it forward -- which is the one measurement that must survive a
# repair. A base commit is never rewritten here and is dated by its arrival,
# because what a branch lacks is a commit that landed on the base, whenever the
# work in it happens to have been written.
LANDED = "%ct"
WRITTEN = "%at"


def commit_times(tree, *revs, clock=LANDED):
    """Commit timestamps for a revision range, newest first."""
    out = git(tree, "log", "--format=" + clock, *revs)
    if out is None:
        return []
    return [int(line) for line in out.splitlines() if line.strip().isdigit()]


def busy_with(tree):
    """The git operation a tree is part-way through, or None when it is idle.

    A tree stopped in the middle of a rebase or a merge holds a resolution
    belonging to whoever started it, and running anything over that loses it.
    """
    gitdir = git(tree, "rev-parse", "--absolute-git-dir") or ""
    if not gitdir:
        return None
    where = Path(gitdir)
    for marker, name in (("rebase-merge", "a rebase"), ("rebase-apply", "a rebase"),
                         ("MERGE_HEAD", "a merge"),
                         ("CHERRY_PICK_HEAD", "a cherry-pick"),
                         ("BISECT_LOG", "a bisect")):
        if (where / marker).exists():
            return name
    return None


def survey(tree):
    """One tree, and everything that decides whether the work in it is at risk."""
    now = time.time()
    record = {
        "path": str(tree),
        "repo": Path(common_dir(tree)).parent.name,
        "branch": git(tree, "branch", "--show-current") or None,
        "primary": worktrees.is_primary(Path(tree)),
        "base": None, "behind": 0, "ahead": 0, "drift_hours": None,
        "dirty": 0, "dirty_hours": None,
        "unpushed": 0, "unpushed_hours": None,
        "busy": busy_with(tree),
        "drifted": False, "blocker": None,
        "findings": [], "level": "clear",
    }

    paths = dirty_paths(tree)
    if paths:
        record["dirty"] = len(paths)
        record["dirty_hours"] = newest_change(tree, paths)

    local = commit_times(tree, "HEAD", "--not", "--remotes", clock=WRITTEN)
    if local:
        record["unpushed"] = len(local)
        record["unpushed_hours"] = (now - max(local)) / HOUR

    base = base_ref(tree)
    head = git(tree, "rev-parse", "--verify", "--quiet", "HEAD")
    if base and head:
        record["base"] = base
        merge_base = git(tree, "merge-base", base, "HEAD")
        if merge_base:
            missing = commit_times(tree, "%s..%s" % (merge_base, base))
            record["behind"] = len(missing)
            record["ahead"] = len(commit_times(tree, "%s..HEAD" % merge_base))
            if missing:
                record["drift_hours"] = (now - min(missing)) / HOUR

    return judge(record)


def judge(record):
    """The findings a tree earns, and the one level that says what happens to it.

    Drift is measured from the oldest base commit the tree lacks rather than from
    the fork point. A branch cut this morning off a base branch whose tip is a
    week old lacks nothing, and dating it by that tip would report every fresh
    branch in a quiet repository as a week stale.

    Risk and repairability are separate questions. A branch can hold a commit no
    remote has and still be brought forward by a rebase that decides nothing; the
    commit stays reported because it is still on one disk, and the drift under it
    stops growing. What rules a rebase out is named in `blocker`.
    """
    findings, held = [], False

    if record["dirty"] and (record["dirty_hours"] or 0) >= HELD_HOURS:
        findings.append("%d uncommitted file(s), untouched for %s"
                        % (record["dirty"], span(record["dirty_hours"])))
        held = True
    if record["unpushed"] and (record["unpushed_hours"] or 0) >= HELD_HOURS:
        findings.append("%d commit(s) on no remote, newest %s old"
                        % (record["unpushed"], span(record["unpushed_hours"])))
        held = True

    record["drifted"] = bool(record["behind"] >= DRIFT_COMMITS
                             or (record["behind"]
                                 and (record["drift_hours"] or 0) >= DRIFT_HOURS))
    record["blocker"] = why_not_repairable(record) if record["drifted"] else None

    if record["drifted"]:
        findings.append("%d commit(s) behind %s, missing the oldest for %s"
                        % (record["behind"], record["base"], span(record["drift_hours"])))
        if record["blocker"]:
            findings.append(record["blocker"])

    if held:
        record["level"] = "holds"
    elif record["drifted"] and record["blocker"]:
        record["level"] = "blocked"
    elif record["drifted"]:
        record["level"] = "drifted"
    else:
        record["level"] = "clear"
    record["findings"] = findings
    return record


def why_not_repairable(record):
    """What stands between a drifted tree and a rebase, or None where nothing does.

    Uncommitted work rules a tree out whatever its age: a rebase refuses to start
    over it, and the work in it is the thing this tool exists to keep.

    A branch whose own commits are already on a remote is ruled out for a
    different reason. Rebasing rewrites them, which forks the branch from the
    copy the remote holds and from any review open against it, and leaves the
    only good version on one disk -- the state this tool reports. What to do with
    a branch in that shape is a judgement about the work, so it is named here and
    left alone.
    """
    if record["dirty"]:
        return "%d uncommitted file(s) in the way" % record["dirty"]
    if record["busy"]:
        return "%s is part-way through" % record["busy"]
    if not record["branch"]:
        return "the head is detached"
    if not record["base"]:
        return "no base branch to measure against"
    published = record["ahead"] - record["unpushed"]
    if published > 0:
        return "%d of its commit(s) are on a remote; a rebase would fork it there" \
            % published
    return None


def span(hours):
    """A duration in the largest unit that still says something."""
    if hours is None:
        return "an unknown time"
    if hours < 48:
        return "%dh" % round(hours)
    return "%dd" % round(hours / 24)


def refresh(records):
    """Fetch once per repository, so every worktree of it reads current refs."""
    for store in sorted({common_dir(r["path"]) for r in records}):
        git(str(Path(store).parent), "fetch", "--quiet", "--all", "--prune", timeout=180)


def rebase_onto(record):
    """Bring one clean tree forward, and say what happened.

    A tree sitting on the base branch is fast-forwarded, which is the only move
    that cannot rewrite anything. Anything else is rebased, and a rebase that
    does not apply is unwound completely: a tree left holding conflict markers is
    worse off than the tree that was merely behind.
    """
    tree, base = record["path"], record["base"]
    if record["branch"] and base.endswith("/" + record["branch"]):
        ok, said = git_ok(tree, "merge", "--ff-only", base)
        return ("repaired", "fast-forwarded to %s" % base) if ok else \
            ("blocked", "will not fast-forward: %s" % first_line(said))

    ok, said = git_ok(tree, "rebase", base)
    if ok:
        return "repaired", "rebased onto %s" % base
    git_ok(tree, "rebase", "--abort")
    return "blocked", "the rebase does not apply: %s" % first_line(said)


def first_line(text):
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()[:120]
    return "git said nothing"


def repair(records):
    """Rebase every drifted tree nothing rules out, and re-judge the whole set.

    The refs are refreshed first, so the drift acted on is the drift that exists
    rather than the drift the last fetch left behind.
    """
    refresh(records)
    fixed = []
    for record in records:
        record.update(survey(record["path"]))
        if not record["drifted"] or record["blocker"]:
            continue
        outcome, note = rebase_onto(record)
        record.update(survey(record["path"]))
        record["repair"] = note
        if outcome == "repaired":
            fixed.append(record)
        else:
            # A tree holding work at risk keeps saying so; a failed rebase is
            # the lesser of the two facts about it.
            if record["level"] != "holds":
                record["level"] = "blocked"
            record["blocker"] = note
            record["findings"] = record["findings"] + [note]
    return fixed


def name_of(record):
    if record["primary"]:
        return record["repo"] + " (primary)"
    return record["repo"] + "/" + Path(record["path"]).name


def render(records, show_all):
    # A tree that came back clear still shows what repair did to it, so a run
    # that settled something says which trees it moved and how.
    shown = [r for r in records
             if show_all or r["level"] != "clear" or r.get("repair")]
    shown.sort(key=lambda r: (ORDER.index(r["level"]), -(r["behind"] or 0), r["path"]))
    if not shown:
        return
    width = max(len(name_of(r)) for r in shown)
    for record in shown:
        print("  %-7s %-*s %s" % (record["level"], width, name_of(record),
                                  record["branch"] or "(detached)"))
        for finding in record["findings"]:
            print("          %s" % finding)
        if record.get("repair"):
            print("          %s" % record["repair"])


def summary(records):
    """One line saying what the whole machine came to."""
    counts = {level: len([r for r in records if r["level"] == level]) for level in ORDER}
    stranded = len(records) - counts["clear"]
    if not stranded:
        return "%d tree(s) clear" % len(records)
    parts = []
    if counts["holds"]:
        parts.append("%d holding work no remote has" % counts["holds"])
    if counts["blocked"]:
        parts.append("%d drifted and not repairable here" % counts["blocked"])
    if counts["drifted"]:
        parts.append("%d drifted and repairable" % counts["drifted"])
    return "STRANDED %d of %d tree(s) - %s" % (stranded, len(records), ", ".join(parts))


def main(argv):
    verb = next((a for a in argv if not a.startswith("-")), "report")
    if verb not in ("report", "repair"):
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2

    records = [survey(tree) for tree in every_tree()]
    fixed = []
    if verb == "repair":
        fixed = repair(records)
    elif "--offline" not in argv:
        refresh(records)
        records = [survey(r["path"]) for r in records]

    if "--json" in argv:
        print(json.dumps(records, indent=2))
    else:
        render(records, "--all" in argv)
        if fixed:
            print("repaired: %s" % ", ".join(name_of(r) for r in fixed))
        print(summary(records))

    return 1 if any(r["level"] != "clear" for r in records) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
