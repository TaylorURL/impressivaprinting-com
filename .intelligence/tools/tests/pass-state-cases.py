#!/usr/bin/env python3
"""Cases the pass-state carrier has to get right.

The merge is lopsided on purpose: local wins for any path it already knows and
the shared copy only fills gaps, so a stale remote can never overwrite a mark
made here and a fresh machine still inherits everything. These fix that
asymmetry from both sides, along with the rest of the observable contract — the
state root each environment resolves, the verbs the CLI accepts, and a push
that folds the shared copy's marks back in rather than dropping them.

A day plan merges by the opposite rule, and the shape that rule cannot settle
gets its own set: a copy that only removes tasks, whatever its stamp says, has
to hold rather than resolve. So does a page whose card count no longer matches
the merge. Two runs at once get one too, since that is how agents use this.

The git half runs against a bare repo inside a temp directory: no network, and
every path the tool can write to is asserted to sit inside the fixture before a
verb runs, so a redirect the tool no longer honors fails loudly instead of
writing into the live state tree.

  pass-state-cases.py        run them
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "pass-state.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_quiet(*args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ledger(files, **extra):
    body = {"files": files}
    body.update(extra)
    return json.dumps(body, indent=2) + "\n"


def seed_bare(root, shared):
    """A bare repo whose main branch carries the given shared ledger files."""
    bare = root / "shared.git"
    git_quiet("init", "-q", "--bare", str(bare), cwd=root)
    # A clone checks out whatever the bare's HEAD names, and the tool clones
    # fresh without asking for a branch, so HEAD has to point at main.
    git_quiet("symbolic-ref", "HEAD", "refs/heads/main", cwd=bare)
    seed = root / "seedwork"
    git_quiet("clone", "-q", str(bare), str(seed), cwd=root)
    git_quiet("config", "user.email", "t@example.com", cwd=seed)
    git_quiet("config", "user.name", "T", cwd=seed)
    for rel, body in shared.items():
        dest = seed / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body)
    git_quiet("add", "-A", cwd=seed)
    git_quiet("commit", "-qm", "seed", cwd=seed)
    git_quiet("branch", "-M", "main", cwd=seed)
    git_quiet("push", "-q", "origin", "main", cwd=seed)
    return bare


def bare_show(bare, rel):
    p = subprocess.run(["git", "show", f"main:{rel}"], cwd=str(bare),
                       capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def bare_head(bare):
    p = subprocess.run(["git", "rev-parse", "main"], cwd=str(bare),
                       capture_output=True, text=True)
    return p.stdout.strip()


@contextlib.contextmanager
def fixture(shared=None, local=None):
    """A redirected module plus a temp state tree and a local bare remote.

    Every path the module can write to is asserted to sit inside the temp
    directory; a copy under test that stops exposing these globals fails here
    rather than reaching the live state tree.
    """
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        state = root / "state"
        for name in ("STATE_DIR", "CACHE", "REMOTE"):
            if not hasattr(mod, name):
                raise AssertionError(
                    "%s exposes no %s global to redirect; these cases would "
                    "touch the real state tree" % (TARGET, name))
        bare = seed_bare(root, shared or {})
        mod.STATE_DIR = state
        mod.CACHE = state / ".pass-state-repo"
        mod.REMOTE = str(bare)
        for path in (mod.STATE_DIR, mod.CACHE, Path(mod.REMOTE)):
            assert str(path).startswith(tmp), "escaped the temp tree: %s" % path
        for rel, body in (local or {}).items():
            dest = state / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body)
        yield mod, state, bare


def run_verb(fn):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = fn()
    return code, out.getvalue()


def cli(args, env_extra, cwd):
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run([sys.executable, str(TARGET), *args],
                          capture_output=True, text=True, env=env, cwd=cwd)


def state_root_cases():
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        saved = {k: os.environ.get(k)
                 for k in ("INTELLIGENCE_STATE_DIR", "CLAUDE_CODE_REMOTE", "HOME")}
        try:
            os.environ["INTELLIGENCE_STATE_DIR"] = tmp + "/elsewhere"
            os.environ["CLAUDE_CODE_REMOTE"] = "1"
            check("state root: override outranks everything",
                  mod._state_root(), Path(tmp) / "elsewhere")
            del os.environ["INTELLIGENCE_STATE_DIR"]
            os.environ["HOME"] = tmp
            check("state root: cloud session lives off the config tree",
                  mod._state_root(), Path(tmp) / ".pass-state")
            del os.environ["CLAUDE_CODE_REMOTE"]
            check("state root: default is the config state directory",
                  mod._state_root(), Path(tmp) / ".intelligence" / "state")
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def merge_cases():
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Local wins where it knows the path; the remote only fills gaps.
        remote = root / "remote.json"
        local = root / "local.json"
        remote.write_text(ledger({"a.py": "remote-key", "b.py": "new-key"},
                                 first_pass_at="2026-01-01T00:00:00Z",
                                 last_pass_at="2026-06-01T00:00:00Z",
                                 allows={"a.py": {"beacon": "remote reason"}}))
        local.write_text(ledger({"a.py": "local-key"},
                                first_pass_at="2026-03-01T00:00:00Z",
                                last_pass_at="2026-03-01T00:00:00Z",
                                allows={"a.py": {"beacon": "local reason"}}))
        check("merge: gap count", mod.merge_into_local(remote, local), 1)
        merged = json.loads(local.read_text())
        check("merge: local mark survives", merged["files"]["a.py"], "local-key")
        check("merge: remote fills the gap", merged["files"]["b.py"], "new-key")
        check("merge: earliest first pass kept",
              merged["first_pass_at"], "2026-01-01T00:00:00Z")
        check("merge: latest last pass kept",
              merged["last_pass_at"], "2026-06-01T00:00:00Z")
        check("merge: local allow survives",
              merged["allows"]["a.py"]["beacon"], "local reason")

        # A missing or unreadable shared ledger changes nothing here.
        untouched = root / "untouched.json"
        untouched.write_text(ledger({"a.py": "k"}))
        before = untouched.read_text()
        check("merge: absent remote is a no-op",
              mod.merge_into_local(root / "nope.json", untouched), 0)
        garbled = root / "garbled.json"
        garbled.write_text("{not json")
        check("merge: garbled remote is a no-op",
              mod.merge_into_local(garbled, untouched), 0)
        check("merge: local body untouched", untouched.read_text(), before)

        # A fresh machine inherits the whole shared ledger.
        fresh = root / "fresh" / "ledger.json"
        check("merge: empty local inherits all",
              mod.merge_into_local(remote, fresh), 2)
        check("merge: inherited marks land",
              json.loads(fresh.read_text())["files"]["a.py"], "remote-key")


def pull_cases():
    shared = {"ledgers/comment-pass/repo.json": ledger({"a.py": "shared-key",
                                                        "b.py": "shared-b"})}
    local = {"comment-pass/repo.json": ledger({"a.py": "local-key"})}
    with fixture(shared, local) as (mod, state, bare):
        code, out = run_verb(mod.cmd_pull)
        check("pull: exit", code, 0)
        check("pull: reports the gain", "1 entr(ies) gained" in out, True)
        merged = json.loads((state / "comment-pass" / "repo.json").read_text())
        check("pull: local mark survives", merged["files"]["a.py"], "local-key")
        check("pull: shared fills the gap", merged["files"]["b.py"], "shared-b")

        # A second pull finds nothing left to fold in.
        code, out = run_verb(mod.cmd_pull)
        check("pull: idempotent exit", code, 0)
        check("pull: idempotent gain", "0 entr(ies) gained" in out, True)


def push_cases():
    shared = {"ledgers/doc-pass/repo.json": ledger({"remote-only.md": "rk"}),
              "unrelated.txt": "not a ledger\n"}
    local = {"doc-pass/repo.json": ledger({"local.md": "lk"}),
             "doc-pass/notes.txt": "not a ledger\n",
             "scratch/other.json": ledger({"x": "y"})}
    with fixture(shared, local) as (mod, state, bare):
        code, out = run_verb(mod.cmd_push)
        check("push: exit", code, 0)
        pushed = bare_show(bare, "ledgers/doc-pass/repo.json")
        check("push: ledger reaches the remote", pushed is not None, True)
        body = json.loads(pushed)
        check("push: local mark travels", body["files"]["local.md"], "lk")
        # The shared copy's marks fold into the local file before it travels,
        # so a push never drops another machine's work.
        check("push: shared mark kept", body["files"]["remote-only.md"], "rk")
        local_body = json.loads((state / "doc-pass" / "repo.json").read_text())
        check("push: shared mark folded back locally",
              local_body["files"]["remote-only.md"], "rk")
        # Only the named ledgers travel; everything else in state/ is local.
        check("push: non-json stays home",
              bare_show(bare, "ledgers/doc-pass/notes.txt"), None)
        check("push: unlisted directory stays home",
              bare_show(bare, "ledgers/scratch/other.json"), None)
        check("push: unrelated repo file untouched",
              bare_show(bare, "unrelated.txt"), "not a ledger\n")

        # A stray file in the working clone never rides along: the commit is
        # scoped to the ledger root.
        (mod.CACHE / "stray.txt").write_text("stray\n")
        (state / "doc-pass" / "repo.json").write_text(
            ledger({"local.md": "lk", "remote-only.md": "rk", "more.md": "mk"}))
        code, _ = run_verb(mod.cmd_push)
        check("push: second exit", code, 0)
        check("push: stray clone file stays out",
              bare_show(bare, "stray.txt"), None)

        # Matching copies push nothing and mint no commit.
        head = bare_head(bare)
        code, out = run_verb(mod.cmd_push)
        check("push: nothing-to-do exit", code, 0)
        check("push: says it matched", "nothing to push" in out, True)
        check("push: no empty commit", bare_head(bare), head)


def plan_scope_cases():
    """What decides whether a run carries the plans at all.

    A ledger is wanted by every machine that sweeps a repo. A plan is a document
    somebody is working today, and a run that will not open one merging it,
    republishing its page and arming a session-end guard over it is a run doing
    somebody else's work badly. The scope is what separates the two, and the
    reading that settles it without a flag is whether a plan is already here.
    """
    day = "2026-08-28"
    shared = {f"ledgers/day-plans/{day}.json":
              plan(day, SHARED_STAMP, "shared", [("t1", "done")]),
              f"ledgers/day-plans/{day}.html": PLAN_PAGE,
              "ledgers/comment-pass/repo.json": ledger({"a.py": "shared-key"})}
    held = {f"day-plans/{day}.json":
            plan(day, LOCAL_STAMP, "local", [("t1", "open")]),
            f"day-plans/{day}.html": PLAN_PAGE}

    # The shape a scheduled run has: a container holding no plan of its own.
    for label, verb in (("bare", lambda m: m.cmd_pull()),
                        ("--no-plans", lambda m: m.cmd_pull(False))):
        with fixture(shared, {}) as (mod, state, bare):
            code, out = run_verb(lambda: verb(mod))
            check(f"scope: {label} pull on a fresh machine exits", code, 0)
            check(f"scope: {label} pull still carries the ledgers",
                  (state / "comment-pass" / "repo.json").is_file(), True)
            check(f"scope: {label} pull says the plans stayed behind",
                  "Plans not carried" in out, True)
            # The directory's absence is what the session-end guard reads, so
            # not writing a plan and not making the directory are one case.
            check(f"scope: {label} pull leaves no plan directory",
                  (state / "day-plans").exists(), False)

    # A machine holding a plan is one that works it, and needs no flag to say so.
    with fixture(shared, held) as (mod, state, bare):
        code, out = run_verb(mod.cmd_pull)
        check("scope: a machine holding a plan carries it", code, 0)
        check("scope: and the merge runs", "plan(s) updated" in out, True)
        check("scope: the further status is taken",
              statuses(json.loads((state / "day-plans" / f"{day}.json").read_text())),
              {"t1": "done"})

    # An explicit refusal outranks the plan sitting there.
    with fixture(shared, held) as (mod, state, bare):
        code, out = run_verb(lambda: mod.cmd_pull(False))
        check("scope: --no-plans outranks a plan on disk", code, 0)
        check("scope: the plan here is left as it stands",
              statuses(json.loads((state / "day-plans" / f"{day}.json").read_text())),
              {"t1": "open"})
        check("scope: and nothing is recorded about where it stands",
              (state / mod.SHARED_STATE).exists(), False)

    # A push with no plans in scope publishes the ledgers and says nothing about
    # plans -- neither shared nor, if the mirror refuses it, refused.
    seed = {"ledgers/comment-pass/other.json": ledger({"z.py": "z"})}
    with fixture(seed, {"comment-pass/repo.json": ledger({"a.py": "k"}),
                        **held}) as (mod, state, bare):
        code, out = run_verb(lambda: mod.cmd_push(False))
        check("scope: a ledgers-only push exits", code, 0)
        shared_state = state / mod.SHARED_STATE
        check("scope: a ledgers-only push records no plan state",
              shared_state.exists(), False)
        published = subprocess.run(["git", "ls-tree", "-r", "--name-only", "main"],
                                   cwd=bare, capture_output=True, text=True)
        check("scope: the ledgers reached the mirror",
              "ledgers/comment-pass/repo.json" in published.stdout, True)
        check("scope: the plan did not",
              f"ledgers/day-plans/{day}.json" in published.stdout, False)

    # The environment answers where a caller cannot pass a flag.
    with fixture(shared, {}) as (mod, state, bare):
        saved = os.environ.get(mod.PLANS_ENV)
        try:
            os.environ[mod.PLANS_ENV] = "1"
            check("scope: the environment can seed a fresh machine",
                  mod.plans_travel(), True)
            os.environ[mod.PLANS_ENV] = "0"
            check("scope: and can hold a run to the ledgers",
                  mod.plans_travel(), False)
        finally:
            if saved is None:
                os.environ.pop(mod.PLANS_ENV, None)
            else:
                os.environ[mod.PLANS_ENV] = saved

    # A plan write is what schedules the debounced share, so that push carries
    # the plans however the default would have read.
    with fixture(seed, {}) as (mod, state, bare):
        asked = []
        mod.QUIET_SECONDS = 0
        mod.cmd_push = lambda plans_on=None: asked.append(plans_on) or 0
        state.mkdir(parents=True, exist_ok=True)
        (state / mod.SHARE_MARK).write_text("")
        check("scope: share-soon exits", mod.cmd_share_soon(), 0)
        check("scope: share-soon carries the plans outright", asked, [True])


def retire_cases():
    shared = {"ledgers/comment-pass/o__gone.json": ledger({"a.js": "k"}),
              "ledgers/doc-pass/o__gone.json": ledger({"README.md": "k"}),
              "ledgers/doc-pass/o__live.json": ledger({"README.md": "k"}),
              "unrelated.txt": "not a ledger\n"}
    local = {"comment-pass/o__gone.json": ledger({"a.js": "k"}),
             "doc-pass/o__live.json": ledger({"README.md": "k"})}
    with fixture(shared, local) as (mod, state, bare):
        code, out = run_verb(lambda: mod.cmd_retire(["o/gone"]))
        check("retire: exit", code, 0)
        check("retire: local copy gone",
              (state / "comment-pass" / "o__gone.json").exists(), False)
        check("retire: shared copy gone",
              bare_show(bare, "ledgers/comment-pass/o__gone.json"), None)
        check("retire: gone from every ledger",
              bare_show(bare, "ledgers/doc-pass/o__gone.json"), None)
        # The whole point: a retired entry must not survive to be pulled back.
        run_verb(mod.cmd_pull)
        check("retire: pull does not resurrect it",
              (state / "comment-pass" / "o__gone.json").exists(), False)
        # A repo merely absent from this machine keeps its shared copy, which is
        # what makes retiring deliberate rather than a side effect of never
        # having swept something.
        check("retire: untouched repo kept",
              bare_show(bare, "ledgers/doc-pass/o__live.json") is not None, True)
        check("retire: unrelated repo file untouched",
              bare_show(bare, "unrelated.txt"), "not a ledger\n")

        head = bare_head(bare)
        code, _ = run_verb(lambda: mod.cmd_retire(["o/gone"]))
        check("retire: second run exit", code, 0)
        check("retire: no empty commit", bare_head(bare), head)

    with fixture({"unrelated.txt": "seed\n"}, {}) as (mod, state, bare):
        for bad in ("bare", "o/", "/repo", "o/../../etc", "a/b/c"):
            code, _ = run_verb(lambda bad=bad: mod.cmd_retire([bad]))
            check("retire: refuses %r" % bad, code, 2)
        code, _ = run_verb(lambda: mod.cmd_retire([]))
        check("retire: refuses an empty list", code, 2)
        check("retire: slug to filename",
              mod.ledger_name("TaylorURL/tiretracker"),
              "TaylorURL__tiretracker.json")


# A day plan is the other kind of state this carries, and it merges by the
# opposite rule. The pass ledgers are additive records where local-wins is safe;
# a plan is edited on both machines on the same day, so local-wins would throw
# away whichever session ran second. These pin the rule that replaces it: the
# copy written later supplies the document, status takes the furthest either
# copy reached, and the ledger and the page it renders move as a pair.

PLAN_PAGE = """<html>
<style>.task { color: red; }</style>
<span id="done">0</span><span> / 2</span>
<label class="task"><input type="checkbox"><div class="task-body"><p class="task-title">One</p></div></label>
<label class="task"><input type="checkbox"><div class="task-body"><p class="task-title">Two</p></div></label>
</html>
"""

# A credential the push has to refuse, assembled rather than written out: a
# cases file carrying one literally is a cases file the config sync holds off
# the mirror.
LEAKY_URL = "postgres://admin:" + "hunter" + "seven2" + "@db.example.invalid/app"


def plan(day, stamp, subject, tasks, **extra):
    """A plan as `day-plan.py` writes one, at a chosen stamp."""
    body = {"date": day, "subject": subject, "created": stamp, "updated": stamp,
            "artifact": "", "html": "", "tasks": []}
    for i, (tid, status) in enumerate(tasks, start=1):
        body["tasks"].append(
            {"id": tid, "order": i, "phase": "", "title": tid, "detail": "",
             "why": "", "agent": False, "human": False, "needs": [],
             "status": status})
    body.update(extra)
    return json.dumps(body, indent=2) + "\n"


def statuses(body):
    return {t["id"]: t["status"] for t in body["tasks"]}


SHARED_STAMP = "2026-08-28T10:00:00+00:00"
LOCAL_STAMP = "2026-08-28T12:00:00+00:00"


def plan_merge_cases():
    mod = load()
    older = json.loads(plan("2026-08-28", SHARED_STAMP, "shared",
                            [("t1", "done"), ("t2", "open")]))
    newer = json.loads(plan("2026-08-28", LOCAL_STAMP, "local",
                            [("t1", "open"), ("t2", "done")]))

    merged, lifted, dropped, took_remote, at_risk = mod.merge_plan(older, newer)
    check("plan merge: the later copy supplies the document",
          merged["subject"], "local")
    check("plan merge: which copy that was is reported", took_remote, False)
    check("plan merge: a task closed on the older copy stays closed",
          statuses(merged), {"t1": "done", "t2": "done"})
    check("plan merge: the task that moved is named", lifted, ["t1"])
    check("plan merge: nothing was left out", dropped, [])
    check("plan merge: and nothing was held", at_risk, [])

    # The same two copies, arriving the other way round, settle identically.
    swapped, _, _, took_remote, _ = mod.merge_plan(newer, older)
    check("plan merge: arrival order does not decide it",
          (swapped["subject"], statuses(swapped)),
          ("local", {"t1": "done", "t2": "done"}))
    check("plan merge: the shared copy won this time", took_remote, True)

    again, lifted, _, _, _ = mod.merge_plan(merged, merged)
    check("plan merge: running it twice changes nothing", again, merged)
    check("plan merge: and moves nothing", lifted, [])

    check("plan merge: an absent shared copy keeps this one",
          mod.merge_plan(None, newer)[0], newer)
    check("plan merge: an absent local copy takes the shared one",
          mod.merge_plan(older, None)[0], older)

    check("plan merge: running is further than open",
          mod.furthest("running", "open"), "running")
    check("plan merge: a decision not to do it outranks not having started",
          mod.furthest("open", "skipped"), "skipped")
    check("plan merge: done outranks everything",
          [mod.furthest("done", s) for s in ("open", "running", "skipped")],
          ["done", "done", "done"])

    dispatched = {"status": "running", "started": "2026-08-31T16:15:25.039+00:00"}
    handed_back = {"status": "open", "released": "2026-08-31T17:40:00.000+00:00"}
    check("plan settle: a release later than the dispatch it undoes wins",
          mod.settle(dispatched, handed_back), "open")
    check("plan settle: and the same pair the other way round agrees",
          mod.settle(handed_back, dispatched), "open")
    check("plan settle: a dispatch later than the release wins instead",
          mod.settle({"status": "open", "released": "2026-08-31T09:00:00.000+00:00"},
                     {"status": "running", "started": "2026-08-31T10:00:00.000+00:00"}),
          "running")
    check("plan settle: a copy that never started loses to one that did",
          mod.settle({"status": "open"}, dispatched), "running")
    check("plan settle: a closed status is still ordered by rank, not by clock",
          mod.settle({"status": "open", "released": "2099-01-01T00:00:00.000+00:00"},
                     {"status": "done", "closed": "2020-01-01T00:00:00.000+00:00"}),
          "done")

    released = {"date": "d", "updated": "2", "tasks": [
        {"id": "t", "status": "open", "released": "2026-08-31T17:40:00.000+00:00"}]}
    running = {"date": "d", "updated": "1", "tasks": [
        {"id": "t", "status": "running", "started": "2026-08-31T16:15:25.039+00:00",
         "session": "gone"}]}
    merged = mod.merge_plan(running, released)[0]
    check("plan merge: a released task is not dragged back to in flight",
          merged["tasks"][0]["status"], "open")
    check("plan merge: and it keeps neither the dispatch stamp nor its owner",
          [k in merged["tasks"][0] for k in ("started", "session")], [False, False])

    check("mirror holds: a stamp and a page path are not the work",
          mod.mirror_holds({"date": "d", "updated": "x", "html": "/here"},
                           {"date": "d", "updated": "y", "html": "/there"}), True)
    check("mirror holds: nor is a fingerprint of the statuses themselves",
          mod.mirror_holds({"date": "d", "page_state": "aaa"},
                           {"date": "d", "page_state": "bbb"}), True)
    check("mirror holds: a task that moved is",
          mod.mirror_holds({"tasks": [{"id": "t1", "status": "done"}]},
                           {"tasks": [{"id": "t1", "status": "open"}]}), False)
    check("mirror holds: and so is a field one copy does not carry",
          mod.mirror_holds({"date": "d", "subject": "s"}, {"date": "d"}), False)

    check("plan stamp: the write time is what is read",
          mod.plan_stamp({"updated": "b", "created": "a"}), "b")
    check("plan stamp: a plan written before stamps falls back to its creation",
          mod.plan_stamp({"created": "a"}), "a")
    check("plan stamp: an unstamped copy loses to a stamped one",
          mod.plan_stamp({}), "")

    # A task only the losing copy holds cannot be merged in: the page carries
    # one card per task, and a plan whose page is a card short can never sync.
    # An amendment is entitled to that -- it takes an id out while adding
    # another -- so it resolves and names what it left behind.
    amended = json.loads(plan("2026-08-28", "2026-08-28T13:00:00+00:00",
                              "amended", [("t1", "open"), ("t3", "open")]))
    merged, _, dropped, _, at_risk = mod.merge_plan(amended, newer)
    check("plan merge: an amendment supplies the document",
          [t["id"] for t in merged["tasks"]], ["t1", "t3"])
    check("plan merge: the task it took out is named", dropped, ["t2"])
    check("plan merge: and an amendment is never held", at_risk, [])


# The 2026-08-28 displacement, as a fixture: a two-task copy written later than
# a real twenty-four task plan, which a merge deciding on the stamp alone takes
# whole and publishes over the day's work.
BIG_STAMP = "2026-09-01T09:00:00+00:00"
SMALL_STAMP = "2026-09-01T11:00:00+00:00"
# Later than both, so a copy carrying it wins the stamp outright and the
# merge turns on what the copy says rather than on when it was written.
LATE_STAMP = "2026-09-01T13:00:00+00:00"
BIG_IDS = ["t%02d" % i for i in range(1, 25)]


def sized_plan(day, stamp, subject, ids, closed=()):
    return plan(day, stamp, subject,
                [(tid, "done" if tid in closed else "open") for tid in ids])


def page_for(count):
    """A page carrying one card per task, as the plan tool renders one."""
    cards = "\n".join(
        '<label class="task"><input type="checkbox"><div class="task-body">'
        '<p class="task-title">%d</p></div></label>' % i
        for i in range(1, count + 1))
    return ('<html>\n<style>.task { color: red; }</style>\n'
            '<span id="done">0</span><span> / %d</span>\n%s\n</html>\n'
            % (count, cards))


def plan_hold_cases():
    """A copy that only removes tasks is a conflict, not a resolution.

    A stamp says which copy was written last and nothing about what the copy
    is. A fixture, a truncated download, and a morning's editing all read the
    same to it, so the one shape that can only lose work -- a copy contributing
    no task the other lacks -- is held for a person instead of resolved.
    """
    mod = load()
    day = "2026-09-01"
    big = json.loads(sized_plan(day, BIG_STAMP, "taylorurl.com search recovery",
                                BIG_IDS, closed=("t03",)))
    small = json.loads(sized_plan(day, SMALL_STAMP, "fixture", BIG_IDS[:2],
                                  closed=("t01",)))

    merged, lifted, dropped, took_remote, at_risk = mod.merge_plan(small, big)
    check("plan hold: the superset supplies the document",
          len(merged["tasks"]), 24)
    check("plan hold: a later subset does not take the day",
          merged["subject"], "taylorurl.com search recovery")
    check("plan hold: no task is left out", dropped, [])
    check("plan hold: the ids the smaller copy would have dropped are named",
          at_risk, BIG_IDS[2:])
    check("plan hold: the copy that supplied the document is reported",
          took_remote, False)
    check("plan hold: status still merges onto the superset",
          [statuses(merged).get("t01"), statuses(merged).get("t03")],
          ["done", "done"])
    check("plan hold: and the task that moved is named", lifted, ["t01"])

    # Arrival order does not decide it, the same as any other merge.
    other, _, _, took_remote, at_risk = mod.merge_plan(big, small)
    check("plan hold: the superset supplies it from either side",
          [len(other["tasks"]), took_remote], [24, True])
    check("plan hold: and is held from either side", at_risk, BIG_IDS[2:])

    # The push that did the damage: the fixture is the copy on this machine.
    local = {"day-plans/%s.json" % day:
             sized_plan(day, SMALL_STAMP, "fixture", BIG_IDS[:2],
                        closed=("t01",)),
             "day-plans/%s.html" % day: page_for(2)}
    shared = {"ledgers/day-plans/%s.json" % day:
              sized_plan(day, BIG_STAMP, "taylorurl.com search recovery",
                         BIG_IDS, closed=("t03",)),
              "ledgers/day-plans/%s.html" % day: page_for(24)}
    with fixture(shared, local) as (mod, state, bare):
        code, out = run_verb(mod.cmd_push)
        check("plan hold: push exits", code, 0)
        check("plan hold: the run names it a conflict", "conflict" in out, True)
        check("plan hold: and says a person has to settle it",
              "a person has to settle" in out, True)
        pushed = json.loads(bare_show(bare, "ledgers/day-plans/%s.json" % day))
        check("plan hold: the mirror keeps every task",
              len(pushed["tasks"]), 24)
        check("plan hold: and the fixture never displaces it",
              pushed["subject"], "taylorurl.com search recovery")
        here = json.loads((state / "day-plans" / ("%s.json" % day)).read_text())
        check("plan hold: the copy here holds the superset too",
              len(here["tasks"]), 24)
        check("plan hold: with the work either copy had closed",
              [statuses(here).get("t01"), statuses(here).get("t03")],
              ["done", "done"])
        entry = json.loads((state / mod.SHARED_STATE).read_text())["plans"][day]
        check("plan hold: a held day is not recorded as shared",
              entry["state"], "conflict")
        check("plan hold: with the reading that held it",
              "drops" in entry.get("reason", ""), True)

    # The same collision the other way round: the fixture reached the mirror
    # first, and a pull must not bring it back over the day's work.
    local = {"day-plans/%s.json" % day:
             sized_plan(day, BIG_STAMP, "taylorurl.com search recovery",
                        BIG_IDS, closed=("t03",)),
             "day-plans/%s.html" % day: page_for(24)}
    shared = {"ledgers/day-plans/%s.json" % day:
              sized_plan(day, SMALL_STAMP, "fixture", BIG_IDS[:2],
                         closed=("t01",)),
              "ledgers/day-plans/%s.html" % day: page_for(2)}
    with fixture(shared, local) as (mod, state, bare):
        code, out = run_verb(mod.cmd_pull)
        check("plan hold: pull exits", code, 0)
        check("plan hold: a pull cannot truncate the copy here",
              len(json.loads((state / "day-plans" / ("%s.json" % day))
                             .read_text())["tasks"]), 24)
        here = json.loads((state / "day-plans" / ("%s.json" % day)).read_text())
        check("plan hold: a status closed on the smaller copy still arrives",
              [statuses(here).get("t01"), statuses(here).get("t03")],
              ["done", "done"])
        check("plan hold: the pull names the conflict too",
              "conflict" in out, True)
        check("plan hold: and records it as one",
              json.loads((state / mod.SHARED_STATE).read_text())
              ["plans"][day]["state"], "conflict")

    # A page whose card count disagrees with the merged plan is the same
    # evidence read from the other end: the merge settled on a body the page it
    # would travel with does not describe.
    day = "2026-09-03"
    local = {"day-plans/%s.json" % day:
             plan(day, "2026-09-03T09:00:00+00:00", "local",
                  [("t1", "open"), ("t2", "open")]),
             "day-plans/%s.html" % day: page_for(5)}
    with fixture({"unrelated.txt": "seed\n"}, local) as (mod, state, bare):
        code, out = run_verb(mod.cmd_push)
        check("plan hold: a page that disagrees exits", code, 0)
        check("plan hold: a page that disagrees holds the day too",
              "conflict" in out, True)
        check("plan hold: and nothing reaches the mirror",
              bare_show(bare, "ledgers/day-plans/%s.json" % day), None)
        check("plan hold: nor is it recorded as shared",
              json.loads((state / mod.SHARED_STATE).read_text())
              ["plans"][day]["state"], "conflict")


def background(state, bare, verb="push"):
    """One verb started and left running, so two of them can overlap."""
    env = dict(os.environ)
    env["INTELLIGENCE_STATE_DIR"] = str(state)
    env["HOME"] = str(state)
    env["INTELLIGENCE_PASS_STATE_REMOTE"] = str(bare)
    env["INTELLIGENCE_DAYPLAN_NO_SYNC"] = "1"
    env.pop("CLAUDE_CODE_REMOTE", None)
    env.pop("INTELLIGENCE_SYNC_LOCK_HELD", None)
    return subprocess.Popen([sys.executable, str(TARGET), verb],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env)


def marks(state, ledger_dir="comment-pass"):
    return sorted(json.loads((state / ledger_dir / "o__r.json").read_text())
                  ["files"])


def concurrent_push_cases():
    """Two pushes at once, which is the ordinary case with agents running.

    Two runs sharing a state directory are settled by the hold: one waits
    rather than cloning into the cache the other is resetting. Two machines
    are settled by the mirror, which rejects the second push, and the run
    reconciles against what landed and sends it again. Both have to finish,
    and neither may drop the other's marks.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bare = seed_bare(root, {"unrelated.txt": "seed\n"})

        first, second = root / "first", root / "second"
        for state, path, key in ((first, "a.py", "ak"), (second, "b.py", "bk")):
            (state / "comment-pass").mkdir(parents=True)
            (state / "comment-pass" / "o__r.json").write_text(ledger({path: key}))
        runs = [background(first, bare), background(second, bare)]
        for run in runs:
            run.communicate()
        check("concurrent: two machines both finish",
              [run.returncode for run in runs], [0, 0])
        landed = json.loads(bare_show(bare, "ledgers/comment-pass/o__r.json"))
        check("concurrent: neither machine's marks are dropped",
              sorted(landed["files"]), ["a.py", "b.py"])
        # Which of the two pushed second is the race, so what each machine
        # holds right afterwards is not: it keeps its own either way, and a
        # pull is what brings the other's home.
        check("concurrent: and each machine keeps its own",
              ["a.py" in marks(first), "b.py" in marks(second)], [True, True])
        for state in (first, second):
            background(state, bare, "pull").communicate()
        check("concurrent: a pull afterwards leaves both holding both",
              [marks(first), marks(second)],
              [["a.py", "b.py"], ["a.py", "b.py"]])

        shared = root / "shared"
        (shared / "doc-pass").mkdir(parents=True)
        (shared / "doc-pass" / "o__r.json").write_text(ledger({"README.md": "rk"}))
        runs = [background(shared, bare) for _ in range(2)]
        for run in runs:
            run.communicate()
        check("concurrent: two runs on one tree both finish",
              [run.returncode for run in runs], [0, 0])
        check("concurrent: and the mark reaches the mirror once",
              json.loads(bare_show(bare, "ledgers/doc-pass/o__r.json"))["files"],
              {"README.md": "rk"})
        check("concurrent: the run took this tree's publishing hold",
              (shared / load()._lib.SYNC_LOCK).is_file(), True)


def plan_pull_cases():
    day = "2026-08-28"
    shared = {f"ledgers/day-plans/{day}.json":
              plan(day, SHARED_STAMP, "shared", [("t1", "done"), ("t2", "open")]),
              f"ledgers/day-plans/{day}.html": PLAN_PAGE}

    # A machine that has never held a plan gains both halves of one once it
    # asks. Seeding is the one thing the default scope will not do on its own.
    with fixture(shared, {}) as (mod, state, bare):
        code, out = run_verb(lambda: mod.cmd_pull(True))
        check("plan pull: exit", code, 0)
        check("plan pull: the count is reported", "1 plan(s) updated" in out, True)
        landed = state / "day-plans" / f"{day}.json"
        page = state / "day-plans" / f"{day}.html"
        check("plan pull: a first-run machine gains the plan", landed.is_file(), True)
        check("plan pull: and the page it renders", page.is_file(), True)
        body = json.loads(landed.read_text())
        check("plan pull: the page is recorded where it landed",
              body["html"], str(page))
        check("plan pull: the statuses arrive", statuses(body),
              {"t1": "done", "t2": "open"})
        check("plan pull: the page shows what the ledger says",
              'data-status="done"' in page.read_text(), True)

        entry = json.loads((state / mod.SHARED_STATE).read_text())["plans"][day]
        check("plan pull: a plan taken whole is recorded as shared",
              entry["state"], "shared")
        check("plan pull: against the stamp this machine now holds",
              entry["stamp"], json.loads(landed.read_text())["updated"])

        code, out = run_verb(mod.cmd_pull)
        check("plan pull: a second pull settles", code, 0)
        check("plan pull: and moves nothing", "0 plan(s) updated" in out, True)

    # Two copies of the same day, each having closed a different task.
    local = {f"day-plans/{day}.json":
             plan(day, LOCAL_STAMP, "local", [("t1", "open"), ("t2", "done")]),
             f"day-plans/{day}.html": PLAN_PAGE}
    with fixture(shared, local) as (mod, state, bare):
        code, out = run_verb(mod.cmd_pull)
        check("plan pull: divergent exit", code, 0)
        body = json.loads((state / "day-plans" / f"{day}.json").read_text())
        check("plan pull: the later copy supplies the document",
              body["subject"], "local")
        check("plan pull: neither morning is thrown away", statuses(body),
              {"t1": "done", "t2": "done"})
        check("plan pull: the merge says what it moved", "t1 took a further" in out, True)
        # The mirror is behind on a plan whose merge took anything off the copy
        # here, so nothing about that pull may read as a completed trip.
        record = state / mod.SHARED_STATE
        check("plan pull: a merge the mirror has not seen is not recorded",
              json.loads(record.read_text())["plans"] if record.exists() else {},
              {})


def plan_push_cases():
    day = "2026-08-29"
    local = {f"day-plans/{day}.json":
             plan(day, "2026-08-29T09:00:00+00:00", "local",
                  [("t1", "open"), ("t2", "done")]),
             f"day-plans/{day}.html": PLAN_PAGE}
    with fixture({"unrelated.txt": "seed\n"}, local) as (mod, state, bare):
        code, out = run_verb(mod.cmd_push)
        check("plan push: exit", code, 0)
        pushed = bare_show(bare, f"ledgers/day-plans/{day}.json")
        check("plan push: the ledger travels", pushed is not None, True)
        check("plan push: the page travels with it",
              bare_show(bare, f"ledgers/day-plans/{day}.html") is not None, True)
        check("plan push: the statuses travel", statuses(json.loads(pushed)),
              {"t1": "open", "t2": "done"})
        # The page sits somewhere different on every machine, so the path stays
        # home; carrying it would make each push undo the one before it.
        check("plan push: no machine path travels", json.loads(pushed)["html"], "")

        head = bare_head(bare)
        code, out = run_verb(mod.cmd_push)
        check("plan push: a settled plan pushes nothing", code, 0)
        check("plan push: and mints no commit", bare_head(bare), head)


def plan_secret_cases():
    """A plan is prose, and prose can quote a credential the mirror publishes."""
    day = "2026-08-30"
    local = {f"day-plans/{day}.json":
             plan(day, "2026-08-30T09:00:00+00:00", "local",
                  [("t1", "open"), ("t2", "open")], note=LEAKY_URL),
             f"day-plans/{day}.html": PLAN_PAGE}
    with fixture({"unrelated.txt": "seed\n"}, local) as (mod, state, bare):
        head = bare_head(bare)
        code, out = run_verb(mod.cmd_push)
        check("plan secret: exit", code, 0)
        check("plan secret: the ledger is held back",
              bare_show(bare, f"ledgers/day-plans/{day}.json"), None)
        check("plan secret: and its page with it",
              bare_show(bare, f"ledgers/day-plans/{day}.html"), None)
        check("plan secret: the hold is named",
              f"held back day-plans/{day}" in out, True)
        check("plan secret: nothing was committed", bare_head(bare), head)
        check("plan secret: the copy here is untouched",
              (state / "day-plans" / f"{day}.json").is_file(), True)
        # A plan that cannot travel is recorded as one, so a session end says
        # what is wrong with it rather than that it was never offered.
        entry = json.loads((state / mod.SHARED_STATE).read_text())["plans"][day]
        check("plan secret: the hold is recorded", entry["state"], "held")
        check("plan secret: with the shape that caused it",
              "password" in entry["reason"], True)


def plan_share_record_cases():
    """What a plan settled with the mirror is recorded, and only once it has.

    A session end reads this record to tell a plan that reached the mirror from
    one that merely scheduled a push. Filing a trip that did not happen is the
    one thing it cannot survive: the session ends, the container goes, and the
    morning's closures go with it.
    """
    day = "2026-09-02"
    local = {f"day-plans/{day}.json":
             plan(day, "2026-09-02T09:00:00+00:00", "local",
                  [("t1", "open"), ("t2", "done")]),
             f"day-plans/{day}.html": PLAN_PAGE}
    with fixture({"unrelated.txt": "seed\n"}, local) as (mod, state, bare):
        record = state / mod.SHARED_STATE
        check("share record: nothing is recorded before a push",
              record.exists(), False)

        run_verb(mod.cmd_push)
        entry = json.loads(record.read_text())["plans"][day]
        check("share record: a push that landed is recorded",
              entry["state"], "shared")
        check("share record: against the stamp the copy here holds",
              entry["stamp"],
              json.loads((state / "day-plans" / f"{day}.json").read_text())["updated"])
        check("share record: and when it happened", bool(entry.get("at")), True)

        # Days this run did not carry keep what they last settled, so one plan
        # held back for a credential cannot erase the others.
        mod.record_plans({"2026-01-01": {"state": "shared", "stamp": "s"}})
        check("share record: a later run keeps the days it did not carry",
              sorted(json.loads(record.read_text())["plans"]),
              ["2026-01-01", day])

    # A mirror that cannot be reached is a push that did not happen, and the
    # last success standing would say the opposite.
    with fixture({"unrelated.txt": "seed\n"}, local) as (mod, state, bare):
        run_verb(mod.cmd_push)
        record = state / mod.SHARED_STATE
        check("share record: shared before the mirror goes",
              json.loads(record.read_text())["plans"][day]["state"], "shared")
        shutil.rmtree(mod.CACHE, ignore_errors=True)
        mod.REMOTE = str(Path(mod.REMOTE).parent / "no-such-remote.git")
        try:
            run_verb(mod.cmd_push)
        except RuntimeError:
            pass
        entry = json.loads(record.read_text())["plans"][day]
        check("share record: an unreachable mirror is filed as a refusal",
              entry["state"], "refused")
        check("share record: with what the mirror said",
              bool(entry.get("reason")), True)


DAY_PLAN = TARGET.parent / "day-plan.py"

ROUND_TRIP_PLAN = {
    "date": "2026-09-01",
    "subject": "taylorurl.com",
    "tasks": [{"id": "one", "title": "One"}, {"id": "two", "title": "Two"}],
}


def machine(state, bare, tool, *argv, stdin="", sync=False, remote=None):
    """One tool, on one machine, against a bare repo standing in for the mirror.

    `remote` overrides the mirror for one run, which is how a trip that cannot
    land is staged: the gate that carries a closure itself has to be shown
    holding the session when the carrying is what failed.
    """
    env = dict(os.environ)
    env["INTELLIGENCE_STATE_DIR"] = str(state)
    env["HOME"] = str(state)
    env["INTELLIGENCE_PASS_STATE_REMOTE"] = str(remote or bare)
    env.pop("CLAUDE_CODE_REMOTE", None)
    if sync:
        env.pop("INTELLIGENCE_DAYPLAN_NO_SYNC", None)
    else:
        env["INTELLIGENCE_DAYPLAN_NO_SYNC"] = "1"
    return subprocess.run([sys.executable, str(tool), *argv], input=stdin,
                          capture_output=True, text=True, env=env)


def plan_round_trip_cases():
    """The two tools together, over two machines that share only the mirror."""
    if not DAY_PLAN.is_file():
        return
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bare = seed_bare(root, {"unrelated.txt": "seed\n"})
        first, second = root / "first", root / "second"

        machine(first, bare, DAY_PLAN, "new", stdin=json.dumps(ROUND_TRIP_PLAN))
        page = first / "plan.html"
        page.write_text(PLAN_PAGE)
        machine(first, bare, DAY_PLAN, "artifact", "https://example.invalid/p",
                "--html", str(page))
        pushed = machine(first, bare, TARGET, "push")
        check("round trip: the first machine pushes", pushed.returncode, 0)

        # The second machine has never held a plan, and nothing tells it to go
        # and look: reading the ledger is what fetches it.
        asked = machine(second, bare, DAY_PLAN, "current", sync=True)
        check("round trip: the second machine reports the plan",
              asked.stdout.strip(), "2026-09-01")
        landed = second / "day-plans" / "2026-09-01.json"
        check("round trip: the ledger arrived", landed.is_file(), True)
        check("round trip: the page arrived with it",
              (second / "day-plans" / "2026-09-01.html").is_file(), True)
        check("round trip: the page is where this machine keeps it",
              json.loads(landed.read_text())["html"],
              str(second / "day-plans" / "2026-09-01.html"))

        # Work done there reaches the first machine, and the first machine's
        # own copy of that task is not what it had.
        machine(second, bare, DAY_PLAN, "done", "one")
        check("round trip: the second machine pushes",
              machine(second, bare, TARGET, "push").returncode, 0)
        check("round trip: the first machine pulls",
              machine(first, bare, TARGET, "pull").returncode, 0)
        back = json.loads((first / "day-plans" / "2026-09-01.json").read_text())
        check("round trip: work closed elsewhere arrives closed",
              statuses(back), {"one": "done", "two": "open"})
        check("round trip: the page here says so",
              'data-status="done"' in
              (first / "day-plans" / "2026-09-01.html").read_text(), True)

        # A closure the mirror has not been given is carried by the gate rather
        # than refused: the trip it would hand over is one it can make itself,
        # and a refusal whose whole remedy is a command the gate could run is
        # worth nobody's attention.
        machine(second, bare, DAY_PLAN, "done", "two")
        machine(second, bare, DAY_PLAN, "published")
        carried = machine(second, bare, DAY_PLAN, "guard-stop", stdin="{}",
                          sync=True)
        check("round trip: an unshared closure is carried rather than refused",
              carried.returncode, 0)
        check("round trip: the first machine pulls what the gate carried",
              machine(first, bare, TARGET, "pull").returncode, 0)
        closed = json.loads((first / "day-plans" / "2026-09-01.json").read_text())
        check("round trip: the closure the gate carried arrives closed",
              statuses(closed), {"one": "done", "two": "done"})

        # What the trip cannot settle is what the gate is actually for. A mirror
        # it cannot reach leaves the closure here, and the session is held with
        # the day named.
        machine(second, bare, DAY_PLAN, "amend", "two",
                "--why", "the scope moved after it closed")
        holding = machine(second, bare, DAY_PLAN, "guard-stop", stdin="{}",
                          sync=True, remote=root / "no-such-mirror.git")
        check("round trip: a trip that cannot land holds the session",
              holding.returncode, 2)
        check("round trip: naming the plan it is holding",
              "2026-09-01" in holding.stderr, True)
        freed = machine(second, bare, DAY_PLAN, "guard-stop", stdin="{}",
                        sync=True)
        check("round trip: and a trip that lands releases it",
              freed.returncode, 0)


def failure_case():
    """An unreachable remote is exit 1 with the error named, never a traceback."""
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        mod.STATE_DIR = Path(tmp) / "state"
        mod.CACHE = mod.STATE_DIR / ".pass-state-repo"
        mod.REMOTE = str(Path(tmp) / "no-such-remote.git")
        err = io.StringIO()
        saved_argv = sys.argv
        sys.argv = ["pass-state.py", "pull"]
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                code = mod.main()
        finally:
            sys.argv = saved_argv
        check("failure: unreachable remote exits 1", code, 1)
        check("failure: error is named", err.getvalue().startswith("pass-state:"), True)


def cli_cases():
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state"
        (state / "comment-pass").mkdir(parents=True)
        (state / "comment-pass" / "a.json").write_text(ledger({}))
        (state / "comment-pass" / "b.json").write_text(ledger({}))
        env = {"INTELLIGENCE_STATE_DIR": str(state)}

        p = cli(["status"], env, tmp)
        check("cli: status exit", p.returncode, 0)
        check("cli: status honors the state override",
              "comment-pass: 2 local file(s)" in p.stdout, True)
        check("cli: absent clone reported",
              "shared clone: not present" in p.stdout, True)

        p = cli([], env, tmp)
        check("cli: default verb is status", p.returncode, 0)
        check("cli: default verb output", "comment-pass:" in p.stdout, True)

        p = cli(["frobnicate"], env, tmp)
        check("cli: unknown verb refused", p.returncode, 2)
        check("cli: usage names the verbs", "usage: pass-state.py" in p.stderr, True)


def plan_move_cases():
    """A move is the removal the hold must not undo.

    The hold exists because a copy that only removes ids cannot be told from a
    truncated one by its stamp. A move is exactly that shape and is exactly
    that thing, so the copy records what left and where it went, and the merge
    reads the record rather than guessing. Without this a task moved to another
    day comes back on the next sync, and the day it left shows work that is not
    its own again.
    """
    mod = load()
    day = "2026-09-01"
    big = json.loads(sized_plan(day, BIG_STAMP, "taylorurl.com search recovery",
                                BIG_IDS, closed=("t03",)))
    moved = json.loads(sized_plan(day, LATE_STAMP, "taylorurl.com search recovery",
                                  BIG_IDS[:-1], closed=("t03",)))
    moved["moved"] = [{"id": BIG_IDS[-1], "to": "2026-09-08", "at": LATE_STAMP}]

    merged, _, dropped, _, at_risk = mod.merge_plan(big, moved)
    check("plan move: the removal is not held", at_risk, [])
    check("plan move: and the task stays gone",
          BIG_IDS[-1] in {t["id"] for t in merged["tasks"]}, False)
    check("plan move: the rest of the day survives it", len(merged["tasks"]), 23)
    check("plan move: what left is named to the caller", dropped, [BIG_IDS[-1]])

    # Only what the record names. A copy that drops more than it accounts for
    # is still the shape the hold was written for.
    short = json.loads(sized_plan(day, LATE_STAMP, "taylorurl.com search recovery",
                                  BIG_IDS[:2], closed=("t03",)))
    short["moved"] = [{"id": BIG_IDS[-1], "to": "2026-09-08", "at": LATE_STAMP}]
    merged, _, _, _, at_risk = mod.merge_plan(big, short)
    check("plan move: an unaccounted removal is still held",
          at_risk, BIG_IDS[2:-1])
    check("plan move: and the superset still supplies the document",
          len(merged["tasks"]), 24)


def main():
    state_root_cases()
    merge_cases()
    pull_cases()
    push_cases()
    plan_merge_cases()
    plan_hold_cases()
    plan_move_cases()
    concurrent_push_cases()
    plan_pull_cases()
    plan_push_cases()
    plan_secret_cases()
    plan_share_record_cases()
    plan_round_trip_cases()
    plan_scope_cases()
    retire_cases()
    failure_case()
    cli_cases()

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
