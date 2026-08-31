#!/usr/bin/env python3
"""Cases the stranded-work report has to get right.

The tool is worth what it says nothing about. A report that names every branch
on the machine is read once and ignored after that, and an ignored report leaves
work rotting exactly as fast as no report at all -- so the silence is the part
under test here as much as the alarm: a tree that is clean and current, a branch
cut minutes ago, an edit somebody is part-way through, all have to pass without
a word.

The other half is that repair never costs anything. A tree holding uncommitted
work is never touched, a rebase that does not apply is unwound rather than left
sitting in the tree, and a commit that exists on no remote survives whatever the
repair does around it.

Every fixture is a temporary directory with HOME pointed inside it, so the
project roots, the worktrees root and every checkout the tool walks resolve
there and nothing can reach the live tree. Origins are local bare repositories
and commit dates are set explicitly, so no case touches the network or waits on
a clock.

  stranded-cases.py    run them
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "stranded.py")

FAILURES = []


def declared(name):
    """A threshold read out of the tool's source.

    The cases are pinned to what the tool declares rather than to a number
    repeated here, so a threshold that moves moves in one place and the cases
    still describe the tool that exists.
    """
    tree = ast.parse(TARGET.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("%s declares no %s" % (TARGET.name, name))


HELD_HOURS = declared("HELD_HOURS")
DRIFT_HOURS = declared("DRIFT_HOURS")
DRIFT_COMMITS = declared("DRIFT_COMMITS")


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def contains(label, haystack, needle):
    if needle not in haystack:
        FAILURES.append("%s: %r missing from the output" % (label, needle))


def missing(label, haystack, needle):
    if needle in haystack:
        FAILURES.append("%s: %r unexpectedly present" % (label, needle))


def env_for(home):
    """A child environment rooted entirely inside the fixture.

    The tool derives the project roots and the worktrees root from HOME at
    import, so pointing HOME here is what keeps every walk inside the temporary
    directory. Git's global and system config are silenced so no identity or
    hooks path leaks in from the machine running the cases.
    """
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_AUTHOR_NAME"] = "Case Fixture"
    env["GIT_AUTHOR_EMAIL"] = "cases@example.invalid"
    env["GIT_COMMITTER_NAME"] = "Case Fixture"
    env["GIT_COMMITTER_EMAIL"] = "cases@example.invalid"
    for leak in ("GIT_DIR", "GIT_WORK_TREE", "INTELLIGENCE_TEST_TARGET"):
        env.pop(leak, None)
    return env


def git(tree, env, *args, must=True):
    done = subprocess.run(("git", *args), cwd=str(tree), env=env,
                          capture_output=True, text=True)
    if must and done.returncode != 0:
        raise AssertionError("git %s in %s said: %s"
                             % (" ".join(args), tree, done.stderr.strip()))
    return done.stdout.strip()


def dated(env, ago_hours):
    when = datetime.now(timezone.utc) - timedelta(hours=ago_hours)
    stamp = when.strftime("%Y-%m-%dT%H:%M:%S+0000")
    aged = dict(env)
    aged["GIT_AUTHOR_DATE"] = stamp
    aged["GIT_COMMITTER_DATE"] = stamp
    return aged


def commit_dated(tree, env, message, ago_hours=0.0, path=None, body=None):
    target = Path(tree) / (path or (message.replace(" ", "-") + ".txt"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body if body is not None else message + "\n")
    aged = dated(env, ago_hours)
    git(tree, aged, "add", "-A")
    git(tree, aged, "commit", "-q", "-m", message)
    return git(tree, aged, "rev-parse", "HEAD")


class Repo:
    """A bare origin, a primary checkout under a project root, and a scratch
    clone that moves the base branch without touching either."""

    def __init__(self, tmp, home, env, name="proj"):
        self.env, self.name = env, name
        self.bare = tmp / "remotes" / "bradley-t-t" / (name + ".git")
        self.bare.mkdir(parents=True)
        git(tmp, env, "init", "--bare", "-q", "-b", "main", str(self.bare))

        seed = tmp / ("seed-" + name)
        seed.mkdir()
        git(seed, env, "init", "-q", "-b", "main", ".")
        commit_dated(seed, env, "seed", ago_hours=240, path="README.md")
        git(seed, env, "push", "-q", str(self.bare), "main:main")
        git(seed, env, "push", "-q", str(self.bare), "main:develop")

        self.primary = home / "Development" / "IdeaProjects" / name
        self.primary.parent.mkdir(parents=True, exist_ok=True)
        git(tmp, env, "clone", "-q", str(self.bare), str(self.primary))
        git(self.primary, env, "checkout", "-q", "develop")

        self.scratch = tmp / ("push-" + name)
        git(tmp, env, "clone", "-q", str(self.bare), str(self.scratch))
        git(self.scratch, env, "checkout", "-q", "develop")

    def advance(self, count, ago_hours, prefix="base", body=None, path=None):
        """Move origin/develop forward by commits of a chosen age."""
        for index in range(count):
            commit_dated(self.scratch, self.env, "%s %d" % (prefix, index),
                         ago_hours=ago_hours,
                         path=path or ("base-%s-%d.txt" % (prefix, index)),
                         body=body)
        git(self.scratch, self.env, "push", "-q", "origin", "develop")

    def fetch(self):
        """What the machine knows about the remote, which is what report reads."""
        git(self.primary, self.env, "fetch", "-q", "origin", "--prune")

    def worktree(self, slug, start="origin/develop"):
        dest = Path(self.env["HOME"]) / "Development" / "worktrees" / self.name / slug
        dest.parent.mkdir(parents=True, exist_ok=True)
        git(self.primary, self.env, "worktree", "add", "-q", "-b", slug,
            str(dest), start)
        return dest


def run(env, *argv):
    done = subprocess.run([sys.executable, str(TARGET), *argv],
                          capture_output=True, text=True, env=env)
    return done.returncode, done.stdout + done.stderr


def age_file(path, hours):
    when = datetime.now(timezone.utc).timestamp() - hours * 3600
    os.utime(path, (when, when))


def head_of(tree, env):
    return git(tree, env, "rev-parse", "HEAD")


def case_clean_and_current_is_silent(tmp, home, env):
    repo = Repo(tmp, home, env)
    repo.worktree("fresh")
    code, out = run(env, "report")
    check("a clean machine exits clean", code, 0)
    contains("it says every tree is clear", out, "tree(s) clear")
    missing("it names nothing", out, "STRANDED")
    missing("it lists no tree", out, "drifted")


def case_a_new_branch_is_not_reported(tmp, home, env):
    repo = Repo(tmp, home, env)
    dest = repo.worktree("just-cut")
    # The base moves while the branch is minutes old, which is the ordinary
    # state of a busy repository rather than a finding.
    repo.advance(5, ago_hours=0.2)
    repo.fetch()
    code, out = run(env, "report")
    check("a branch cut minutes ago exits clean", code, 0)
    missing("the fresh branch is not named", out, "just-cut")
    check("the tree is still where it was",
          git(dest, env, "rev-list", "--count", "HEAD", "--not", "--remotes"), "0")


def case_fresh_work_in_hand_is_silent(tmp, home, env):
    repo = Repo(tmp, home, env)
    dest = repo.worktree("in-hand")
    scratch = dest / "wip.txt"
    scratch.write_text("part-way through\n")
    age_file(scratch, HELD_HOURS - 2)
    commit_dated(dest, env, "in flight", ago_hours=HELD_HOURS - 2, path="done.txt")
    code, out = run(env, "report")
    check("work from this session exits clean", code, 0)
    missing("nothing in hand is named", out, "in-hand")


def case_behind_and_clean_is_repairable(tmp, home, env):
    repo = Repo(tmp, home, env)
    dest = repo.worktree("stale")
    repo.advance(3, ago_hours=DRIFT_HOURS + 48)
    repo.fetch()

    code, out = run(env, "report")
    check("a drifted branch fails the report", code, 1)
    contains("it is named", out, "stale")
    contains("it is called repairable", out, "drifted and repairable")
    contains("the base is named", out, "behind origin/develop")

    code, out = run(env, "repair")
    check("repair settles it", code, 0)
    contains("the repair is named", out, "repaired:")
    contains("the machine is clear afterwards", out, "tree(s) clear")
    check("the branch now holds the base tip",
          git(dest, env, "rev-list", "--count", "origin/develop..HEAD"), "0")

    code, out = run(env, "report")
    check("a second report stays clean", code, 0)


def case_the_primary_is_fast_forwarded(tmp, home, env):
    repo = Repo(tmp, home, env)
    repo.advance(2, ago_hours=DRIFT_HOURS + 24)
    repo.fetch()
    code, out = run(env, "report")
    check("a stale primary fails the report", code, 1)
    contains("the primary is named as such", out, "(primary)")

    code, out = run(env, "repair")
    check("repair settles the primary", code, 0)
    contains("it is fast-forwarded rather than rebased", out, "fast-forwarded to origin/develop")


def case_uncommitted_work_is_reported_and_never_touched(tmp, home, env):
    repo = Repo(tmp, home, env)
    dest = repo.worktree("holding")
    tracked = dest / "README.md"
    tracked.write_text("half an edit\n")
    untracked = dest / "notes.txt"
    untracked.write_text("a thought\n")
    for path in (tracked, untracked):
        age_file(path, HELD_HOURS + 24)
    repo.advance(3, ago_hours=DRIFT_HOURS + 24)
    repo.fetch()

    before = head_of(dest, env)
    code, out = run(env, "report")
    check("uncommitted work fails the report", code, 1)
    contains("the tree is named", out, "holding")
    contains("the age is carried", out, "uncommitted file(s), untouched for")
    contains("it is not called repairable", out, "holding work no remote has")

    code, out = run(env, "repair")
    check("repair cannot settle it", code, 1)
    contains("the reason is the uncommitted work", out, "uncommitted file(s) in the way")
    check("the tree was not moved", head_of(dest, env), before)
    check("the edit survives", tracked.read_text(), "half an edit\n")
    check("the untracked file survives", untracked.read_text(), "a thought\n")
    check("nothing was staged", git(dest, env, "diff", "--cached", "--name-only"), "")


def case_a_local_only_commit_is_reported(tmp, home, env):
    repo = Repo(tmp, home, env)
    dest = repo.worktree("unpushed")
    commit_dated(dest, env, "a live fix", ago_hours=HELD_HOURS + 24, path="fix.txt")

    code, out = run(env, "report")
    check("a commit on no remote fails the report", code, 1)
    contains("the tree is named", out, "unpushed")
    contains("the count and the age are carried", out, "commit(s) on no remote, newest")
    contains("it is called work at risk", out, "holding work no remote has")

    code, out = run(env, "repair")
    check("repair does not settle a commit on no remote", code, 1)
    contains("the commit survives whatever repair did",
             git(dest, env, "log", "--format=%s"), "a live fix")


def case_a_local_only_commit_still_gets_its_drift_repaired(tmp, home, env):
    repo = Repo(tmp, home, env)
    dest = repo.worktree("held-and-stale")
    commit_dated(dest, env, "a live fix", ago_hours=HELD_HOURS + 24, path="fix.txt")
    repo.advance(3, ago_hours=DRIFT_HOURS + 24)
    repo.fetch()

    code, out = run(env, "repair")
    check("the tree still fails for the commit it holds", code, 1)
    check("the drift under it is gone",
          git(dest, env, "rev-list", "--count", "origin/develop..HEAD"), "1")
    contains("the commit came through the rebase",
             git(dest, env, "log", "--format=%s"), "a live fix")


def case_a_published_branch_is_never_rewritten(tmp, home, env):
    repo = Repo(tmp, home, env)
    dest = repo.worktree("shipped")
    commit_dated(dest, env, "the work", ago_hours=DRIFT_HOURS + 48, path="work.txt")
    git(dest, env, "push", "-q", "-u", "origin", "shipped")
    repo.advance(3, ago_hours=DRIFT_HOURS + 24)
    repo.fetch()
    before = head_of(dest, env)

    code, out = run(env, "report")
    check("a drifted published branch fails the report", code, 1)
    contains("the branch is named", out, "shipped")
    contains("the reason it is left alone is stated", out, "a rebase would fork it there")
    contains("it is not called repairable", out, "not repairable here")

    code, _ = run(env, "repair")
    check("repair leaves it to a person", code, 1)
    check("the commit on the remote was not rewritten", head_of(dest, env), before)
    check("the branch still matches what origin holds",
          git(dest, env, "rev-list", "--count", "origin/shipped..HEAD"), "0")


def case_a_conflicting_rebase_is_unwound(tmp, home, env):
    repo = Repo(tmp, home, env)
    dest = repo.worktree("collides")
    commit_dated(dest, env, "one reading", ago_hours=HELD_HOURS + 24,
                 path="shared.txt", body="branch\n")
    repo.advance(1, ago_hours=DRIFT_HOURS + 24, prefix="other",
                 path="shared.txt", body="base\n")
    repo.advance(DRIFT_COMMITS, ago_hours=DRIFT_HOURS + 24, prefix="filler")
    repo.fetch()
    before = head_of(dest, env)

    code, out = run(env, "repair")
    check("a rebase that does not apply leaves the run failing", code, 1)
    contains("the reason is named", out, "the rebase does not apply")
    check("the tree is back where it started", head_of(dest, env), before)
    check("no rebase is left in the tree",
          (Path(git(dest, env, "rev-parse", "--absolute-git-dir")) / "rebase-merge").exists(),
          False)
    check("the branch is checked out again",
          git(dest, env, "branch", "--show-current"), "collides")
    check("the tree is clean", git(dest, env, "status", "--porcelain"), "")


def case_a_detached_head_is_never_rebased(tmp, home, env):
    repo = Repo(tmp, home, env)
    dest = repo.worktree("adrift")
    repo.advance(3, ago_hours=DRIFT_HOURS + 24)
    repo.fetch()
    git(dest, env, "checkout", "-q", "--detach")
    before = head_of(dest, env)

    code, out = run(env, "report")
    check("a detached tree fails the report", code, 1)
    contains("the reason is the head", out, "the head is detached")
    contains("it is not called repairable", out, "not repairable here")

    code, _ = run(env, "repair")
    check("repair cannot settle it", code, 1)
    check("the tree was not moved", head_of(dest, env), before)


def case_a_tree_part_way_through_is_left_alone(tmp, home, env):
    repo = Repo(tmp, home, env)
    dest = repo.worktree("mid-rebase")
    repo.advance(3, ago_hours=DRIFT_HOURS + 24)
    repo.fetch()
    gitdir = Path(git(dest, env, "rev-parse", "--absolute-git-dir"))
    (gitdir / "rebase-merge").mkdir()
    before = head_of(dest, env)

    code, out = run(env, "report")
    check("a tree part-way through fails the report", code, 1)
    contains("the operation is named", out, "a rebase is part-way through")

    code, _ = run(env, "repair")
    check("repair cannot settle it", code, 1)
    check("the tree was not moved", head_of(dest, env), before)
    check("the operation is still there", (gitdir / "rebase-merge").is_dir(), True)


def case_the_count_fires_where_the_clock_is_too_slow(tmp, home, env):
    """A base that gains a day of commits in an hour is the case the clock misses."""
    repo = Repo(tmp, home, env)
    repo.worktree("fast-moving")
    repo.advance(DRIFT_COMMITS - 1, ago_hours=0.2)
    repo.fetch()
    code, out = run(env, "report")
    check("one under the count stays silent", code, 0)
    missing("nothing is named", out, "fast-moving")

    repo.advance(1, ago_hours=0.2, prefix="one-more")
    repo.fetch()
    code, out = run(env, "report")
    check("the count alone trips it", code, 1)
    contains("the branch is named", out, "fast-moving")
    contains("the count is carried", out, "%d commit(s) behind" % DRIFT_COMMITS)


def case_report_refreshes_before_it_measures(tmp, home, env):
    """A reading against remotes is only as current as the refs it reads.

    The default has to fetch, because the tree that most needs reporting is the
    one whose branch was deleted when its pull request merged: the tracking ref
    it left behind answers for a commit no remote has, and the tree reads clear
    until something prunes. `--offline` is the run that cannot reach the
    network, and it is the only one measuring against the last fetch.
    """
    repo = Repo(tmp, home, env)
    repo.worktree("unfetched")
    repo.advance(DRIFT_COMMITS + 5, ago_hours=DRIFT_HOURS + 24)

    code, out = run(env, "report", "--offline")
    check("offline reports only what the last fetch left", code, 0)
    contains("the machine reads clear", out, "tree(s) clear")

    code, out = run(env, "report")
    check("the default sees it", code, 1)
    contains("the branch is named", out, "unfetched")


def case_all_shows_the_clear_trees(tmp, home, env):
    repo = Repo(tmp, home, env)
    repo.worktree("quiet")
    code, out = run(env, "report", "--all")
    check("a clear machine still exits clean", code, 0)
    contains("a clear tree is listed", out, "clear")
    contains("the quiet worktree is listed", out, "quiet")


def case_json_carries_every_tree(tmp, home, env):
    repo = Repo(tmp, home, env)
    repo.worktree("one")
    repo.advance(3, ago_hours=DRIFT_HOURS + 24)
    repo.fetch()
    code, out = run(env, "report", "--json")
    check("json fails the same way", code, 1)
    records = json.loads(out)
    check("every tree is present", len(records), 2)
    check("each carries a level",
          all(r["level"] in ("holds", "blocked", "drifted", "clear") for r in records),
          True)
    check("each carries a path", all(Path(r["path"]).is_dir() for r in records), True)
    check("the drifted one carries its base",
          sorted({r["base"] for r in records}), ["origin/develop"])


def case_an_unknown_verb_is_refused(tmp, home, env):
    Repo(tmp, home, env)
    code, _ = run(env, "rebase-everything")
    check("an unknown verb is refused", code, 2)


CASES = (
    case_clean_and_current_is_silent,
    case_a_new_branch_is_not_reported,
    case_fresh_work_in_hand_is_silent,
    case_behind_and_clean_is_repairable,
    case_the_primary_is_fast_forwarded,
    case_uncommitted_work_is_reported_and_never_touched,
    case_a_local_only_commit_is_reported,
    case_a_local_only_commit_still_gets_its_drift_repaired,
    case_a_published_branch_is_never_rewritten,
    case_a_conflicting_rebase_is_unwound,
    case_a_detached_head_is_never_rebased,
    case_a_tree_part_way_through_is_left_alone,
    case_the_count_fires_where_the_clock_is_too_slow,
    case_report_refreshes_before_it_measures,
    case_all_shows_the_clear_trees,
    case_json_carries_every_tree,
    case_an_unknown_verb_is_refused,
)


def main():
    for case in CASES:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            home = tmp / "home"
            home.mkdir()
            env = env_for(home)
            try:
                case(tmp, home, env)
            except Exception as why:
                FAILURES.append("%s raised %s: %s"
                                % (case.__name__, type(why).__name__, why))

    for failure in FAILURES:
        print("FAIL %s" % failure)
    print("%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
