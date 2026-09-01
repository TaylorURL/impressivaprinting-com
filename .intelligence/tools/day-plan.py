#!/usr/bin/env python3
"""Holds the day plan between the session that writes it and the one that runs it.

A plan agreed in conversation and left in the transcript is a plan the next
session cannot read. This keeps the agreed tasks as data, so the morning run
knows what was decided, what is already done, and what is still blocked.

The ordering is the point. Each task names what it needs, and `next` returns
only the tasks whose needs are all satisfied — so a run works the plan in the
order the work actually allows rather than the order it was written in. A task
waiting on a signup nobody has done yet never gets handed to an agent.

    new       write a plan from JSON on stdin
    list      the plans on file, newest first
    current   the plan a run should be working, as a date
    show      the plan's tasks, grouped by phase
    runsheet  the day numbered, split into agent steps and yours
    next      the tasks that are unblocked right now, in order
    start     mark tasks as in flight, when they are dispatched
    done      mark tasks complete
    skip      mark tasks deliberately not done, with a reason
    amend     reword a task whose scope changed after the plan was agreed
    needs     reset what a task waits on, when a blocker stops gating it
    defer     send tasks and what waits on them to the end of the order
    move      send tasks to another day's plan, leaving nothing behind
    resume    lift a deferral, leaving the ordering alone
    carry     open tomorrow's plan from what today's left unfinished
    rollover  the same carry on a clock, once the day has turned
    artifact  record where the plan was published
    sync      rewrite the page so it matches the ledger
    page      report whether the published page is still true
    published record that the page has been republished

State lives beside the other ledgers, one file per plan date plus the page
rendered from it. `pass-state.py` carries the pair between machines, so the
session that runs a plan need not be the one that wrote it. Several sessions
hold the same plan open at once, on more than one machine, which is what the
rest of this answers to: a write schedules the push that shares it and the
session cannot end until that push has landed, a read fetches first whenever
the copy here could have been overtaken, and every command that changes a plan
holds the plans while it does, so two closures in the same minute both survive.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import date as _date, datetime, timedelta, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None


def _shared():
    """The shared _lib module, loaded by path.

    Skills run this tool as a script from arbitrary directories, so the module
    is found beside this file rather than through sys.path, with the installed
    tree as the fallback for a copy executed from elsewhere.
    """
    here = Path(__file__).resolve().parent / "_lib.py"
    path = here if here.is_file() else Path.home() / ".intelligence" / "tools" / "_lib.py"
    spec = importlib.util.spec_from_file_location("intelligence_tools_lib", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    _lib = _shared()
    _state_root = _lib.state_root
except Exception:
    _lib = None

    def _state_root():
        # The same three answers the shared module gives, because a copy
        # running without it still has to find the state the rest of this
        # machine keeps: the override first, then a remote session's own root
        # off the config tree, then the tree's own state directory.
        override = os.environ.get("INTELLIGENCE_STATE_DIR")
        if override:
            return Path(override)
        if os.environ.get("CLAUDE_CODE_REMOTE"):
            return Path.home() / ".pass-state"
        return Path.home() / ".intelligence" / "state"


def _write(path, text):
    """A file replaced whole, so a concurrent read never lands mid-write."""
    if _lib is not None:
        _lib.write_atomic(path, text)
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("%s.%d.tmp" % (path.name, os.getpid()))
    tmp.write_text(text)
    os.replace(tmp, path)


# The hold's file and the variable naming a process already inside it, taken
# from the shared module so the carrier's merge and this tool answer to one
# protocol, and spelled here for a copy running without that module.
LOCK_FILE = getattr(_lib, "PLAN_LOCK", ".day-plan-lock")
LOCK_HELD = getattr(_lib, "PLAN_LOCK_HELD", "INTELLIGENCE_DAYPLAN_LOCK_HELD")


@contextlib.contextmanager
def _held():
    """Exclusive hold over the plans for the length of one command.

    The shared module owns the protocol, so the carrier's own merge takes the
    same file by the same name and the two cannot interleave. The branch below
    covers a copy of this tool running without that module beside it.
    """
    if _lib is not None:
        with _lib.plan_lock(_state_root()) as got:
            yield got
        return
    if fcntl is None:
        yield False
        return
    directory = Path(_state_root())
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / LOCK_FILE, "a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


OPEN, DONE, SKIPPED, RUNNING = "open", "done", "skipped", "running"

# The statuses a task can hold without being finished. `carry` moves these
# forward and `resolve_day` counts a plan holding any of them as live: a run
# that died mid-dispatch leaves tasks marked running, and treating those as
# settled would hand the next morning a plan that looks complete.
UNFINISHED = (OPEN, RUNNING)


# A plan holds work. A decision is not work, and parking one here is what this
# refuses. The cost is a day: a task reading "decide whether X" is handed to
# nobody, because an agent cannot make the call and the human reading the page
# is being asked a question rather than given a step. It sits through the run,
# gets carried to the next plan, and is still sitting there a week later. The
# question was answerable in the ten seconds it took to ask it.
#
# So the decision is taken before the plan is written, with AskUserQuestion,
# and what lands in the ledger is the work the answer implies.
ALLOW_DECISION = "INTELLIGENCE_ALLOW_PLAN_DECISION"

# Titles that open on a decision verb, and the phases a parked decision
# collects under once there is more than one of them.
# Only verbs that ask the reader for a choice. "Determine", "settle" and
# "figure out" were here and came out again: they open investigation work an
# agent does perfectly well, and refusing those turns the guard into noise.
DECISION_TITLE = re.compile(
    r"^\s*(?:decide|choose|pick\s+between|agree\s+(?:on|whether))\b",
    re.I,
)
DECISION_BODY = re.compile(r"\bdecide\s+(?:whether|if|which|between)\b", re.I)
DECISION_PHASE = re.compile(
    r"^\s*(?:say\s+what\s+is\s+true|decisions?|open\s+questions?|questions?"
    r"|to\s+decide|undecided|unresolved|choices?)\s*$",
    re.I,
)


def decision_parked(task):
    """What reads as a question waiting for an answer rather than a step.

    Three tells, and the phase is the strongest of them: a decision arriving
    alone gets a title anyone can read, but once two of them collect they get
    a heading that names the pile, and every plan that has ever had one has
    grown the rest.
    """
    if DECISION_PHASE.match(task.get("phase", "") or ""):
        return f"phase {task.get('phase', '')!r} is a pile of unanswered questions"
    if DECISION_TITLE.match(task.get("title", "") or ""):
        return f"title {task.get('title', '')!r} opens on a decision verb"
    if DECISION_BODY.search(task.get("title", "") or ""):
        return f"title {task.get('title', '')!r} names a decision to be made"
    return ""


def refuse_parked_decision(task):
    """Refuse a task that asks the reader a question instead of naming work."""
    if os.environ.get(ALLOW_DECISION) == "1":
        return
    why = decision_parked(task)
    if not why:
        return
    raise SystemExit(
        f"day-plan: task {task.get('id', '?')} parks a decision -- {why}.\n"
        "  Ask it with AskUserQuestion now, then write the work the answer\n"
        "  implies. A decision nobody has made blocks the plan it sits in.\n"
        f"  {ALLOW_DECISION}=1 overrides a misread."
    )


# A title is the whole of what the run sheet can say about a step, so a title
# only a reader of the repo could parse leaves the sheet unreadable to the
# person it is for. The specifics still belong in the detail, which nothing
# here touches. Every tell below is a shape English prose does not have.
ALLOW_JARGON = "INTELLIGENCE_ALLOW_PLAN_JARGON"

JARGON_TITLE = (
    (re.compile(r"`"), "quotes code"),
    (re.compile(r"[<>]"), "carries markup"),
    (re.compile(r"\b[\w.]+\(\s*\)"), "names a function"),
    (re.compile(r"\b[\w-]+\.(?:js|mjs|cjs|ts|tsx|jsx|py|rb|go|rs|sh|zsh|css|scss"
                r"|html|json|ya?ml|sql|toml|env|ini|cfg|lock|md)\b", re.I), "names a file"),
    (re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b"), "names an environment variable"),
    (re.compile(r"\b[a-z]+_[a-z]\w*\b"), "names an identifier"),
    (re.compile(r"\b[a-z]{2,}[A-Z][a-zA-Z]*\b"), "names an identifier"),
)


def jargon_title(task):
    """What in a title only somebody already inside the code could read."""
    title = task.get("title", "") or ""
    for pattern, why in JARGON_TITLE:
        hit = pattern.search(title)
        if hit:
            return f"{hit.group(0)!r} {why}"
    return ""


def refuse_jargon_title(task):
    """Refuse a title the run sheet could not put in front of a person."""
    if os.environ.get(ALLOW_JARGON) == "1":
        return
    why = jargon_title(task)
    if not why:
        return
    raise SystemExit(
        f"day-plan: task {task.get('id', '?')} has a title only a reader of the\n"
        f"  code can follow -- {why}.\n"
        "  The title is the whole of what the run sheet says about this step, and\n"
        "  the run sheet is what a person reads to know what the day is. Write it\n"
        "  as a plain English instruction and put the specifics in the detail.\n"
        f"  {ALLOW_JARGON}=1 overrides a misread."
    )


def root():
    d = Path(_state_root()) / "day-plans"
    d.mkdir(parents=True, exist_ok=True)
    return d


def path_for(day):
    return root() / f"{day}.json"


def plan_dates():
    return sorted((p.stem for p in root().glob("*.json")), reverse=True)


def load(day):
    p = path_for(day)
    if not p.is_file():
        raise SystemExit(f"day-plan: no plan for {day}")
    return json.loads(p.read_text())


def save(plan):
    # `updated` is what settles a plan held on two machines at once. A file's
    # modification time cannot: a clone stamps every file at the moment it
    # arrives, so a checkout of an older plan reads as the newer one. The stamp
    # sits inside the plan, travels with its bytes, and is written here because
    # this is the one place a plan is written.
    plan["updated"] = _stamp()
    _write(path_for(plan["date"]), json.dumps(plan, indent=2) + "\n")
    share_soon()


def _stamp():
    """When a write happened, to the millisecond.

    The stamp is what the carrier's record of a shared plan is held against, so
    its resolution is how small a change can still be told apart: at one second
    a task closed in the same second as the push that shared the plan reads as
    already shared, and the session that closed it ends holding it.
    """
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# The carrier that moves this state between machines, the marks it leaves, and
# how long a burst of writes is given to finish before one push covers it.
SHARE_MARK = ".day-plan-share"
PULLED_MARK = ".day-plan-pulled"
QUIET_SECONDS = 20

# What the carrier records about each plan's last trip to the mirror. It is
# written there, after a push watched to succeed, and read here, which is how
# a session end can tell a plan that travelled from one that only scheduled a
# push. `pass-state.py` spells the same name.
SHARED_STATE = ".day-plan-shared.json"

# How long a fetched copy counts as current. The failure this closes is a run
# acting on tasks another session closed minutes ago and republishing a page
# that contradicts the mirror, so the window is what bounds that staleness:
# ninety seconds, which is shorter than the gap between one session closing a
# task and another reaching for it, and longer than one dispatch-and-close
# cycle, so the repeated `next` calls inside a cycle cost one fetch between
# them rather than one each. The window lives in a file, so separate processes
# in the same session share it rather than each paying for their own.
FRESH_SECONDS = 90

# What a fetch is given before the read goes ahead on what is already here. The
# freshness fetch has a local copy to fall back on, so it waits briefly; the
# first fetch on a machine holding no plans has nothing to fall back on and is
# allowed the longer clone.
FRESH_TIMEOUT = 45
FIRST_PULL_TIMEOUT = 120

# What the session end gives the push it makes for itself. A write schedules a
# push that waits out the rest of the burst, so a session reaching its end
# inside that window is behind the mirror only because the trip has not come
# round yet. The gate makes the trip rather than reporting it missing, and this
# is what it waits: long enough for a fetch, a commit and a push on a slow
# line, short enough that a mirror nobody can reach ends the session anyway.
CARRY_TIMEOUT = 45


def _sync_off():
    return os.environ.get("INTELLIGENCE_DAYPLAN_NO_SYNC") == "1"


def _own_root():
    """This machine's own state root, ignoring any redirect."""
    if os.environ.get("CLAUDE_CODE_REMOTE"):
        return Path.home() / ".pass-state"
    return Path.home() / ".intelligence" / "state"


def _borrowed_root():
    """Whether the state root points somewhere other than this machine's own.

    Redirecting the root moves where a plan is written and nothing else. The
    push it schedules still runs, and the carrier inherits the redirected root
    while resolving the real mirror on its own, so a fixture written under a
    throwaway root reaches the shared ledger as that day's plan and displaces
    the plan already there. A redirected root belongs to a throwaway, and a
    throwaway does not publish.

    A run that redirects the remote as well is a round trip against a repository
    of its own and never reaches the mirror, so it keeps its push.
    """
    override = os.environ.get("INTELLIGENCE_STATE_DIR")
    if not override:
        return False
    if os.environ.get("INTELLIGENCE_PASS_STATE_REMOTE"):
        return False
    try:
        return Path(override).resolve() != _own_root().resolve()
    except OSError:
        return True


def _carrier():
    """The ledger carrier, or None where it is not installed."""
    named = os.environ.get("INTELLIGENCE_PASS_STATE")
    candidates = [Path(named)] if named else []
    candidates.append(Path(__file__).resolve().parent / "pass-state.py")
    candidates.append(Path.home() / ".intelligence" / "tools" / "pass-state.py")
    return next((c for c in candidates if c.is_file()), None)


def _carrier_env():
    env = dict(os.environ)
    # The carrier resolves its own state root, and a run that redirected this
    # one wants both halves in the same place.
    env["INTELLIGENCE_STATE_DIR"] = str(Path(_state_root()))
    # The hold belongs to this process and ends with this command. The carrier
    # runs on its own and outlives it, so handing over the mark would send it
    # into the plans believing something holds them.
    env.pop(LOCK_HELD, None)
    return env


def _fetched(marker):
    """Stamp a fetch as taken, whatever it came back with.

    The mark goes down before the fetch rather than after it, so it is what
    holds a second process in the same session off the network while the first
    is still on it, and so a mirror that cannot be reached is asked once per
    window rather than once per command. Being unreachable is an ordinary
    state, and paying a failed round trip for every read in it is the cost this
    avoids.
    """
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(_stamp() + "\n")
    except OSError:
        pass


def _pull_now(timeout):
    """Run the carrier's pull. Returns what stopped it, or None.

    A read that refuses when the mirror is unreachable is a read that stops the
    day, so a fetch that cannot finish leaves the copy on this machine standing
    and the caller answers from it.
    """
    tool = _carrier()
    if tool is None:
        return "no carrier is installed"
    try:
        # The carrier leaves the plans alone on a machine holding none, which
        # is what keeps a run with no plan to work out of them. This caller is
        # the one whose whole subject is the plans, so it asks for them.
        done = subprocess.run([sys.executable, str(tool), "pull", "--plans"],
                              env=_carrier_env(), capture_output=True, text=True,
                              check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"the mirror did not answer within {timeout}s"
    except (OSError, subprocess.SubprocessError) as err:
        return str(err)
    if done.returncode == 0:
        return None
    lines = [ln for ln in (done.stderr + done.stdout).splitlines() if ln.strip()]
    return lines[-1].strip() if lines else f"the carrier exited {done.returncode}"


def freshen():
    """Fetch the shared plans when this machine's copy could have been overtaken.

    The dangerous copy is not a missing one, it is a stale one: another session
    closed three tasks ten minutes ago, this machine still shows them open, a
    run reports them as outstanding and republishes a page that contradicts the
    mirror. So the reads a run acts on fetch first, inside the window above,
    and report rather than refuse when the fetch cannot be made.
    """
    if _sync_off():
        return
    marker = Path(_state_root()) / PULLED_MARK
    try:
        if time.time() - marker.stat().st_mtime < FRESH_SECONDS:
            return
    except OSError:
        pass
    # A machine holding nothing has nothing to answer from, so its first fetch
    # is allowed the clone rather than the window's brief wait.
    _fetched(marker)
    failed = _pull_now(FRESH_TIMEOUT if plan_dates() else FIRST_PULL_TIMEOUT)
    if failed:
        print(f"# the shared plans could not be fetched ({failed}); "
              "reading the copy on this machine", file=sys.stderr)


def pull_shared():
    """Fetch the shared plans onto a machine holding none.

    A plan is agreed in one session and worked in the next, and the two are
    routinely on different machines: state is per-machine, and a container
    starts with none of it. A run that finds nothing local has either never
    held a plan or is a fresh container, and both want the shared copy before
    reporting an empty page. Once per state directory, so a machine with
    genuinely no plans pays one round trip rather than one per command.
    """
    if _sync_off():
        return
    marker = Path(_state_root()) / PULLED_MARK
    if marker.exists():
        return
    _fetched(marker)
    _pull_now(FIRST_PULL_TIMEOUT)


def share_soon():
    """Schedule the push that carries this write off the machine.

    A plan worked in a container and never pushed dies with the container, and
    the closing push of a scheduled routine is the only step that carries one
    otherwise. A session running the plan on its own has no such step, so the
    ledger schedules it: one publisher in flight, waiting out the rest of the
    burst, so ten tasks closed in a row cost one push.
    """
    if _sync_off() or _borrowed_root():
        return
    tool = _carrier()
    if tool is None:
        return
    mark = Path(_state_root()) / SHARE_MARK
    try:
        if mark.exists() and time.time() - mark.stat().st_mtime < QUIET_SECONDS * 2:
            return
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.write_text(_stamp() + "\n")
        subprocess.Popen([sys.executable, str(tool), "share-soon"],
                         env=_carrier_env(), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return


def normalize(plan):
    """Fill in what a hand-written plan is allowed to leave out.

    A plan is authored in conversation, so it arrives with the fields that
    carry meaning and none of the bookkeeping. Ordering defaults to the order
    the tasks were written in, which is the order they were agreed.
    """
    plan.setdefault("created", _stamp())
    plan.setdefault("subject", "")
    plan.setdefault("artifact", "")
    plan.setdefault("html", "")
    seen = set()
    for i, t in enumerate(plan.get("tasks", []), start=1):
        t.setdefault("id", f"t{i}")
        if t["id"] in seen:
            raise SystemExit(f"day-plan: duplicate task id {t['id']}")
        seen.add(t["id"])
        t.setdefault("order", i)
        t.setdefault("phase", "")
        t.setdefault("detail", "")
        t.setdefault("why", "")
        t.setdefault("agent", False)
        t.setdefault("human", False)
        t.setdefault("needs", [])
        t.setdefault("status", OPEN)
        if not t.get("title"):
            raise SystemExit(f"day-plan: task {t['id']} has no title")
        refuse_parked_decision(t)
        refuse_jargon_title(t)
    for t in plan.get("tasks", []):
        for n in t["needs"]:
            if n not in seen:
                raise SystemExit(f"day-plan: task {t['id']} needs unknown task {n}")
    return plan


def by_id(plan):
    return {t["id"]: t for t in plan["tasks"]}


def ready(plan):
    """The open tasks whose blockers have all cleared, in plan order.

    A skipped blocker counts as cleared: deciding not to do something is a
    decision, and holding its dependents open forever turns one skip into a
    stalled plan.
    """
    index = by_id(plan)
    out = []
    for t in sorted(plan["tasks"], key=lambda x: x["order"]):
        if t["status"] != OPEN:
            continue
        if all(index[n]["status"] in (DONE, SKIPPED) for n in t["needs"]):
            out.append(t)
    return out


def counts(plan):
    c = {OPEN: 0, DONE: 0, SKIPPED: 0, RUNNING: 0}
    for t in plan["tasks"]:
        c[t["status"]] = c.get(t["status"], 0) + 1
    return c


def resolve_day(day):
    if day:
        return day
    dates = plan_dates()
    if not dates:
        pull_shared()
        dates = plan_dates()
    if not dates:
        raise SystemExit("day-plan: no plans on file")
    # A plan for a day that has not arrived is not the plan a run should be
    # working. Tomorrow's work gets written the moment it is agreed, which is
    # usually today, and without this the act of writing it takes the run off
    # the day it is actually on.
    today = _date.today().isoformat()
    arrived = [d for d in dates if d <= today] or dates
    # The newest plan with work left is the one a run should be working; a
    # finished plan means the newest is simply the last thing that happened.
    for d in arrived:
        c = counts(load(d))
        if any(c[k] for k in UNFINISHED):
            return d
    return arrived[0]


# The page is a view of the ledger, and a view that drifts is worse than none:
# the checkboxes are what gets read tomorrow morning. So the ledger writes the
# page rather than a run remembering to. Every verb that moves a task calls
# `sync_page`, which is why the two cannot disagree for longer than one command.

# The mark is the bare word, and the wrapper is whatever the language it lands
# in calls a comment. An HTML comment inside a `<style>` is not one: CSS reads
# `<!--` as a token, then the mark as a selector, and swallows the rule that
# follows it. The first rule of both blocks was being dropped that way.
STATUS_MARK = "day-plan:status"

STATUS_STYLE = """
<style>
/* """ + STATUS_MARK + """ */
  .task[data-status="done"] > .task-body > .task-title,
  .task[data-status="skipped"] > .task-body > .task-title {
    color: var(--ink-mute);
  }

  .task[data-status="done"] > .task-body > .task-title { text-decoration: line-through;
    text-decoration-color: var(--ink-ghost); text-decoration-thickness: 1px; }

  .task[data-status] > .task-body::before {
    display: inline-block;
    margin: 0 0 8px;
    padding: 3px 9px;
    border-radius: 999px;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 600;
    line-height: 1.5;
    letter-spacing: var(--track-caps);
    text-transform: uppercase;
  }

  .task[data-status="open"] > .task-body::before { content: none; }
  .task[data-status="done"] > .task-body::before { content: "Done"; background: var(--good-wash); color: var(--good); }
  .task[data-status="skipped"] > .task-body::before { content: "Skipped"; background: var(--wash-ink); color: var(--ink-mute); }
  .task[data-status="running"] > .task-body::before {
    content: "In flight";
    background: var(--wash-accent);
    color: var(--accent);
    animation: pulse 1.8s var(--ease) infinite;
  }

  .task[data-status="running"] { border-color: var(--accent); }

  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.45; } }

  .runline {
    margin: 14px 0 0;
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.04em;
    color: var(--ink-faint);
  }

  @media (prefers-reduced-motion: reduce) {
    .task[data-status="running"] > .task-body::before { animation: none; }
  }
</style>
"""

STATUS_SCRIPT = """
<script>
/* """ + STATUS_MARK + """ */
  (function () {
    // The ledger outranks whatever this browser last stored: a task closed by
    // the run is closed however the reader left the box. Runs last, so the
    // page's own restore has already happened and this corrects it.
    var boxes = Array.prototype.slice.call(document.querySelectorAll('input[type="checkbox"]'));
    var closed = 0;
    boxes.forEach(function (b) {
      var label = b.closest('.task');
      var status = label && label.getAttribute('data-status');
      if (status === 'done' || status === 'skipped') { b.checked = true; closed += 1; }
    });
    var doneEl = document.getElementById('done');
    var fillEl = document.getElementById('fill');
    if (doneEl) { doneEl.textContent = String(closed); }
    if (fillEl && boxes.length) { fillEl.style.width = (closed / boxes.length * 100) + '%'; }
  })();
</script>
"""


# The run sheet ------------------------------------------------------------
#
# The page is opened by somebody deciding what to do next, and a page that
# opens on prose and layout has buried that answer. So the ledger writes the
# answer itself: the day as one numbered sequence, split into the steps an
# agent runs and the steps waiting on a person, in the plain English of the
# titles. It is stamped in on every sync, which is what stops a hand-written
# page from ever shipping without it.

RUNSHEET_OPEN = "<!-- day-plan:runsheet -->"
RUNSHEET_CLOSE = "<!-- /day-plan:runsheet -->"
RUNSHEET_BLOCK = re.compile(
    re.escape(RUNSHEET_OPEN) + r".*?" + re.escape(RUNSHEET_CLOSE), re.S
)

SIDE_HEADING = {
    "agent": "What the agent is doing",
    "you": "What it needs from you",
}

STATUS_WORD = {DONE: "Done", SKIPPED: "Skipped", RUNNING: "In flight", OPEN: ""}


def _numbered(numbers):
    """Step numbers as English: step 3, or steps 3 and 5, or steps 3, 5 and 8."""
    if len(numbers) == 1:
        return f"step {numbers[0]}"
    marks = [str(n) for n in numbers]
    return "steps " + ", ".join(marks[:-1]) + " and " + marks[-1]


def runsheet_rows(plan):
    """The day as a numbered sequence, each step with who holds it and what it waits on.

    The numbering runs across the whole day rather than restarting on each
    side, so the two lists still read as one order: the reader sees that step 4
    is theirs and that step 5 cannot start until it lands. Nothing here is
    written by hand -- the ordering and the blocking are already in the ledger,
    and a sentence a person retypes is a sentence that goes stale.
    """
    tasks = sorted(plan["tasks"], key=lambda x: x["order"])
    index = by_id(plan)
    number = {t["id"]: i for i, t in enumerate(tasks, start=1)}
    waited_on = {}
    for t in tasks:
        for n in t["needs"]:
            waited_on.setdefault(n, []).append(number[t["id"]])

    rows = []
    for t in tasks:
        blocked = sorted(number[n] for n in t["needs"] if index[n]["status"] in UNFINISHED)
        note = []
        if blocked and t["status"] in UNFINISHED:
            note.append("Cannot start until " + _numbered(blocked) + " is done.")
        frees = sorted(waited_on.get(t["id"], []))
        if frees and t["status"] in UNFINISHED:
            note.append("Frees " + _numbered(frees) + ".")
        rows.append({
            "n": number[t["id"]],
            "task": t,
            "side": "you" if t["human"] else "agent",
            "note": " ".join(note),
        })
    return rows


def _esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_runsheet(plan):
    """The two lists as markup, generated whole so they can never drift."""
    rows = runsheet_rows(plan)
    out = [
        RUNSHEET_OPEN,
        '<section class="runsheet">',
        "  <h2>Today, step by step</h2>",
    ]
    for side in ("agent", "you"):
        mine = [r for r in rows if r["side"] == side]
        closed = sum(1 for r in mine if r["task"]["status"] in (DONE, SKIPPED))
        tally = f"{closed} of {len(mine)} done" if mine else "nothing today"
        out.append(f'  <div class="rs-side" data-side="{side}">')
        out.append(
            f'    <h3>{SIDE_HEADING[side]}<span class="rs-tally">{tally}</span></h3>'
        )
        if not mine:
            out.append('    <p class="rs-empty">Nothing on this side of the day.</p>')
        else:
            out.append("    <ol>")
            for r in mine:
                t = r["task"]
                word = STATUS_WORD.get(t["status"], "")
                state = f'<span class="rs-state">{word}</span>' if word else ""
                note = (
                    f'<span class="rs-note">{_esc(r["note"])}</span>'
                    if r["note"] else ""
                )
                out.append(
                    f'      <li value="{r["n"]}" data-id="{t["id"]}"'
                    f' data-status="{t["status"]}">{state}'
                    f'<span class="rs-what">{_esc(t["title"])}</span>{note}</li>'
                )
            out.append("    </ol>")
        out.append("  </div>")
    out.extend(["</section>", RUNSHEET_CLOSE])
    return "\n".join(out) + "\n"


def runsheet_text(plan):
    """The same two lists for a terminal, so a run can read back what it published."""
    rows = runsheet_rows(plan)
    head = plan["date"]
    if plan.get("subject"):
        head += f" -- {plan['subject']}"
    lines = [head, ""]
    for side in ("agent", "you"):
        mine = [r for r in rows if r["side"] == side]
        closed = sum(1 for r in mine if r["task"]["status"] in (DONE, SKIPPED))
        lines.append(f"{SIDE_HEADING[side]} ({closed} of {len(mine)} done)")
        if not mine:
            lines.append("  nothing on this side of the day")
        for r in mine:
            word = STATUS_WORD.get(r["task"]["status"], "")
            mark = f"[{word.lower()}] " if word else ""
            lines.append(f"  {r['n']}. {mark}{r['task']['title']}")
            if r["note"]:
                lines.append(f"      {r['note']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def place_runsheet(text, block):
    """Put the run sheet where the page opens, whatever the page is made of.

    A marker already in the page wins, because that is the author saying where
    it reads best. Without one it goes above everything the page has to say,
    since the whole point is that it is read before the prose rather than after
    it. Every fallback lands somewhere legible rather than refusing: a page
    that renders without the sheet is the failure this exists to prevent.
    """
    if RUNSHEET_BLOCK.search(text):
        return RUNSHEET_BLOCK.sub(lambda _: block.rstrip("\n"), text, count=1)
    for anchor in ("</header>", "</style>"):
        i = text.find(anchor)
        if i != -1:
            i += len(anchor)
            return text[:i] + "\n\n" + block + text[i:]
    return block + "\n" + text


RUNSHEET_STYLE = """
  /* The run sheet is the part of the page that has to survive being skimmed,
     so it is set larger than the prose under it and given nothing to compete
     with. Every colour falls back, because this is stamped into a page whose
     tokens it does not get to choose. */
  .runsheet {
    margin: 0 0 8px;
    display: flex;
    flex-direction: column;
    gap: 34px;
  }

  .runsheet h2 {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-faint, #6b6b6b);
  }

  .runsheet h3 {
    margin: 0 0 14px;
    font-size: 17px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--ink, #111);
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 10px;
  }

  .rs-tally {
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.03em;
    color: var(--ink-mute, #6b6b6b);
  }

  .runsheet ol {
    margin: 0;
    padding: 0 0 0 2.4em;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .runsheet li {
    padding-left: 4px;
    font-size: 16px;
    line-height: 1.5;
    color: var(--ink, #111);
  }

  .runsheet li::marker {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    color: var(--ink-ghost, #9a9a9a);
  }

  /* The state tag reads as part of the sentence rather than above it, so a
     closed step stays one line rather than two. */
  .rs-what { display: inline; }

  .rs-note {
    display: block;
    margin-top: 2px;
    font-size: 14px;
    color: var(--ink-mute, #6b6b6b);
  }

  .rs-empty {
    margin: 0;
    font-size: 15px;
    color: var(--ink-mute, #6b6b6b);
  }

  .rs-state {
    display: inline-block;
    margin-right: 7px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    vertical-align: 2px;
  }

  .runsheet li[data-status="done"] .rs-state { color: var(--good, #0f7350); }
  .runsheet li[data-status="skipped"] .rs-state { color: var(--ink-mute, #6b6b6b); }
  .runsheet li[data-status="running"] .rs-state { color: var(--accent, #1a4ed8); }

  .runsheet li[data-status="done"] .rs-what,
  .runsheet li[data-status="skipped"] .rs-what {
    color: var(--ink-mute, #6b6b6b);
  }

  .runsheet li[data-status="done"] .rs-what {
    text-decoration: line-through;
    text-decoration-color: var(--ink-ghost, #9a9a9a);
    text-decoration-thickness: 1px;
  }

  @media (min-width: 720px) {
    .runsheet li { font-size: 17px; }
  }
"""

# A page written before the run sheet existed already carries the status
# stamp, so the two are marked apart: a page stamped once still gains the sheet
# and the style it needs rather than showing it unstyled.


# The log ------------------------------------------------------------------
#
# One link is the day plan. It is renamed to whichever day it is now showing
# and the day before it is replaced, because a link per day is a gallery
# nobody reads and a stale one is a page saying work is open that moved on
# without it. What keeps that from losing anything is the log: every plan on
# file, what each day settled, and what is still ahead, stamped onto the page
# from the ledger the same way the run sheet is.

LOG_OPEN = "<!-- day-plan:log -->"
LOG_CLOSE = "<!-- /day-plan:log -->"
LOG_BLOCK = re.compile(re.escape(LOG_OPEN) + r".*?" + re.escape(LOG_CLOSE), re.S)


def _day_name(day):
    d = _date.fromisoformat(day)
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


def log_rows(plan):
    """Every plan on file, oldest first, with what each day came to."""
    rows = []
    for day in sorted(plan_dates()):
        try:
            other = plan if day == plan["date"] else load(day)
        except (SystemExit, ValueError):
            continue
        c = counts(other)
        total = len(other["tasks"])
        closed = c[DONE] + c[SKIPPED]
        if day == plan["date"]:
            when, said = "today", "today"
        elif day < plan["date"]:
            when = "past"
            said = f"{closed} of {total} done" if total else "nothing closed"
        else:
            when = "ahead"
            said = f"{total} waiting" if total else "empty"
        rows.append({"date": day, "when": when, "said": said,
                     "name": _day_name(day)})
    return rows


def render_log(plan):
    """The log as markup, generated whole from the plans on file."""
    rows = log_rows(plan)
    out = [LOG_OPEN, '<section class="daylog">',
           "  <h2>Every day plan</h2>", "  <ol>"]
    for r in rows:
        out.append(
            f'    <li data-when="{r["when"]}">'
            f'<span class="dl-day">{_esc(r["name"])}</span>'
            f'<span class="dl-said">{_esc(r["said"])}</span></li>'
        )
    out.extend(["  </ol>",
                "  <p class=\"dl-note\">This page is whichever day is current. "
                "A day that has passed keeps its record here and stops holding "
                "the link.</p>",
                "</section>", LOG_CLOSE])
    return "\n".join(out) + "\n"


def place_log(text, block):
    """Put the log at the foot of the page, wherever the page ends.

    A marker already in the page wins. Without one it goes after everything
    the page has to say and before the scripts, which is where a record
    belongs: read when somebody asks what happened, not on the way to the work.
    """
    if LOG_BLOCK.search(text):
        return LOG_BLOCK.sub(lambda _: block.rstrip("\n"), text, count=1)
    i = text.find("<script")
    if i != -1:
        return text[:i] + block + "\n" + text[i:]
    return text.rstrip("\n") + "\n\n" + block


LOG_STYLE = """
  /* A record rather than a feature: one line a day, set small, with the
     current day the only one carrying full weight.

     It carries its own column, because it is stamped onto a page that may
     have closed its container before this lands and a section that inherits
     nothing renders edge to edge at the window's left. Separation is space
     rather than a rule, which is the one thing that reads the same whether it
     falls inside the page's own column or beside it. */
  .daylog {
    max-width: 760px;
    margin: 44px auto 0;
    padding: 0 20px 72px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .daylog h2 {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-faint, #6b6b6b);
  }

  .daylog ol {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 7px;
  }

  .daylog li {
    display: flex;
    gap: 14px;
    align-items: baseline;
    font-size: 14px;
    color: var(--ink-mute, #6b6b6b);
  }

  .dl-day {
    flex: 0 0 auto;
    min-width: 8.5em;
    font-variant-numeric: tabular-nums;
  }

  .daylog li[data-when="today"] { color: var(--ink, #111); font-weight: 600; }
  .daylog li[data-when="ahead"] { color: var(--ink-faint, #8b8b8b); }

  .dl-note {
    margin: 0;
    font-size: 13px;
    color: var(--ink-faint, #8b8b8b);
    max-width: 66ch;
  }
"""

SHEET_MARK = "day-plan:sheet-style"
SHEET_COMMENT = "/* " + SHEET_MARK + " */"
STAMPED_STYLE = RUNSHEET_STYLE + LOG_STYLE
SHEET_STYLE = "\n<style>\n" + SHEET_COMMENT + STAMPED_STYLE + "</style>\n"

# From the marker to the end of whatever style block holds it. The stamp sits in
# its own block on a page that already carries the status style, and inside the
# status block on a page that does not, so the closing tag is the only end both
# layouts share.
SHEET_BLOCK = re.compile(re.escape(SHEET_COMMENT) + r".*?(?=</style>)", re.S)
PAGE_STYLE = STATUS_STYLE.replace(
    "</style>", SHEET_COMMENT + STAMPED_STYLE + "</style>", 1)

ID_ON_LABEL = re.compile(r'data-id="([^"]*)"')

LABEL_RE = re.compile(r'<label class="task"(?:\s+data-[a-z-]+="[^"]*")*\s*>')

TITLE_RE = re.compile(r"(<title>)(.*?)(</title>)", re.S)


def page_title(plan):
    """What the page is called wherever it is listed rather than opened.

    A plan page is found in a gallery of them, so the one thing it has to say
    is which day it is. Names written for the subject read well beside the
    plan and identically to each other beside the next one.
    """
    d = _date.fromisoformat(plan["date"])
    return f"{d.strftime('%b')} {d.day} Day Plan"


def page_path(plan):
    """Where the plan's page lives.

    A page written to a session scratchpad is gone by the time another session
    needs to republish it, which loses the only copy of a deliverable the
    ledger points at. So the page is kept beside the ledger and the recorded
    path is moved there on the first sync.
    """
    return root() / f"{plan['date']}.html"


def sync_page(plan, quiet=True):
    """Rewrite the plan's page so it says exactly what the ledger says.

    Returns a short report, or None when the plan has no page yet. The page is
    matched to the ledger by document order, which holds because the page is
    generated from the plan in the first place. A mismatch in count means the
    two are no longer the same plan, and that is raised rather than guessed at.
    """
    src = Path(plan["html"]) if plan.get("html") else None
    target = page_path(plan)
    if src and src.is_file() and src.resolve() != target.resolve():
        _write(target, src.read_text())
        plan["html"] = str(target)
        save(plan)
    elif not target.is_file():
        return None

    text = target.read_text()
    # A page stamped before the mark was a comment in the language it sits in
    # is repaired on the next sync rather than left with a rule the browser
    # threw away.
    for legacy in (STATUS_MARK, SHEET_MARK):
        text = text.replace(f"<!-- {legacy} -->", f"/* {legacy} */")
    tasks = sorted(plan["tasks"], key=lambda x: x["order"])
    labels = list(LABEL_RE.finditer(text))
    if len(labels) != len(tasks):
        raise SystemExit(
            f"day-plan: page has {len(labels)} tasks, ledger has {len(tasks)}; "
            "the page is not a view of this plan"
        )

    # Document order matches plan order only until something reorders the plan.
    # `defer` does, and a positional match then stamps every status onto the
    # wrong task while still looking like a clean sync. So the id a label
    # already carries wins, and position is used only to place ids on a page
    # that has never been stamped.
    stamped = [ID_ON_LABEL.search(m.group(0)) for m in labels]
    by_position = all(hit is None for hit in stamped)
    if not by_position and not all(stamped):
        raise SystemExit(
            "day-plan: the page carries ids on some tasks and not others; "
            "it is not a view this can sync"
        )
    if by_position:
        assignment = [t["id"] for t in tasks]
    else:
        assignment = [hit.group(1) for hit in stamped]
        known = {t["id"] for t in tasks}
        unknown = [i for i in assignment if i not in known]
        if unknown or len(set(assignment)) != len(assignment):
            raise SystemExit(
                "day-plan: the page names tasks this plan does not have "
                f"({', '.join(sorted(set(unknown))) or 'duplicated ids'})"
            )

    status_of = {t["id"]: t["status"] for t in tasks}
    out, last = [], 0
    for task_id, m in zip(assignment, labels):
        out.append(text[last:m.start()])
        out.append(f'<label class="task" data-id="{task_id}" data-status="{status_of[task_id]}">')
        last = m.end()
    out.append(text[last:])
    text = "".join(out)

    want = page_title(plan)
    if TITLE_RE.search(text):
        text = TITLE_RE.sub(lambda m: m.group(1) + want + m.group(3), text, count=1)
    else:
        text = f"<title>{want}</title>\n" + text

    text = place_runsheet(text, render_runsheet(plan))
    text = place_log(text, render_log(plan))

    c = counts(plan)
    closed = c[DONE] + c[SKIPPED]
    text = re.sub(r'(<span id="done">)\d*(</span>)', rf'\g<1>{closed}\g<2>', text)
    text = re.sub(r'(<span>\s*/\s*)\d+(\s*</span>)', rf'\g<1>{len(tasks)}\g<2>', text)

    if STATUS_MARK not in text:
        text = text.replace("</style>", "</style>\n" + PAGE_STYLE, 1)
        text = text.rstrip() + "\n" + STATUS_SCRIPT
    elif SHEET_MARK not in text:
        text = text.replace("</style>", "</style>\n" + SHEET_STYLE, 1)
    else:
        # The marker records that a stamp is present, not which style it holds.
        # A page keeps whatever block it already carries, so the markup and the
        # style drift apart the moment the stamped style grows: the new section
        # lands on a page holding no rule for it. Rewriting the block on every
        # pass is what keeps the two the same.
        text = SHEET_BLOCK.sub(lambda _: SHEET_COMMENT + STAMPED_STYLE, text, 1)

    _write(target, text)
    plan["page_state"] = state_hash(plan)
    save(plan)
    report = f"{target}: {closed}/{len(tasks)} closed, {c[RUNNING]} in flight"
    if not quiet:
        print(report)
    return report


def state_hash(plan):
    """A fingerprint of everything the page says, so drift is detectable.

    Statuses were once the whole of it, on the ground that prose does not make
    a published page wrong about what is done. The run sheet changed that: it
    is generated from the titles and the ordering, so a task reworded or
    re-blocked leaves a published page saying something the ledger no longer
    says. So does the log, which is generated from every other plan on file.
    What is stamped onto the page is what is fingerprinted here.
    """
    body = "|".join(
        f"{t['id']}:{t['status']}:{t['title']}:{','.join(t['needs'])}:"
        f"{'you' if t['human'] else 'agent'}"
        for t in sorted(plan["tasks"], key=lambda x: x["order"])
    )
    # The log is stamped on from the other plans on file, so a day opened or
    # closed elsewhere is drift on this page like anything else it says.
    body += "||" + "|".join(f"{r['date']}:{r['said']}" for r in log_rows(plan))
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def cmd_rollover(args):
    """Carry the plan onto today, once the day has actually turned.

    This is the carry a clock makes rather than a person, so it is safe at any
    hour and any number of times: it acts only when the plan a run would work
    belongs to a day already gone and today has none of its own, and every
    other reading is a no-op that says which one it was.

    That is also why nothing here names an hour. A schedule fixed in one zone
    is an hour wrong for half the year, and one that misses its slot skips the
    day entirely. The turn of the date on the machine holding the plans is the
    event; a run that finds it has not happened costs nothing and the next one
    catches it.
    """
    freshen()
    today = _date.today().isoformat()
    # `--check` answers the same question without acting, so the schedule can
    # ask every hour for the price of a read and wake a turn only on the hour
    # the answer changes.
    held = "due" if getattr(args, "check", False) else ""

    def no(why):
        print(why)
        return 1 if held else 0

    if path_for(today).is_file():
        return no(f"{today}: already has a plan")
    if not plan_dates():
        return no("no plans on file")
    day = resolve_day(None)
    if day >= today:
        return no(f"{day}: the day has not turned yet")
    c = counts(load(day))
    if not any(c[k] for k in UNFINISHED):
        return no(f"{day}: closed out, nothing to carry")
    if held:
        print(f"{day} rolls onto {today}: "
              f"{c[OPEN] + c[RUNNING]} still open")
        return 0
    return cmd_carry(argparse.Namespace(date=day, to=today, force=False))


def cmd_runsheet(args):
    """Print the day as the page states it: numbered, split by who holds it."""
    freshen()
    plan = load(resolve_day(args.date))
    sys.stdout.write(runsheet_text(plan))
    return 0


def cmd_sync(args):
    plan = load(resolve_day(args.date))
    report = sync_page(plan, quiet=False)
    if report is None:
        print(f"{plan['date']}: no page on file")
    return 0


def cmd_page(args):
    """Report whether the published artifact still tells the truth.

    This is what the Stop hook reads. A run that closed tasks and never
    republished leaves the reader a page saying the work is still open, which
    is the one failure this whole mechanism exists to prevent.
    """
    plan = load(resolve_day(args.date))
    now = state_hash(plan)
    published = plan.get("published_state")
    url = plan.get("artifact", "")
    if not url:
        print(f"{plan['date']}: no artifact published")
        return 0
    if published == now:
        print(f"{plan['date']}: published page matches the ledger")
        return 0
    c = counts(plan)
    print(
        f"{plan['date']}: published page is BEHIND the ledger "
        f"({c[DONE]} done, {c[RUNNING]} in flight, {c[SKIPPED]} skipped)\n"
        f"  page:  {plan.get('html') or '(none)'}\n"
        f"  url:   {url}\n"
        "  republish it to that same url with the Artifact tool, then run: "
        f"day-plan.py published"
    )
    return 1


def cmd_published(args):
    """Record that the page now standing at the artifact url matches the ledger."""
    plan = load(resolve_day(args.date))
    plan["published_state"] = state_hash(plan)
    plan["published_at"] = _stamp()
    save(plan)
    print(f"{plan['date']}: page recorded as published")
    return 0


def cmd_new(args):
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("day-plan: new reads a plan as JSON on stdin")
    plan = normalize(json.loads(raw))
    if not plan.get("date"):
        raise SystemExit("day-plan: plan has no date")
    if path_for(plan["date"]).is_file() and not args.force:
        raise SystemExit(f"day-plan: {plan['date']} already exists; --force to replace")
    save(plan)
    print(f"{plan['date']}: {len(plan['tasks'])} tasks")
    return 0


def cmd_add(args):
    """Append tasks to a plan already on file.

    A day's scope grows while the day is being agreed. Appending leaves every
    task already in the plan untouched, including the statuses a run part-way
    through has earned, which rewriting the whole plan cannot promise.
    """
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("day-plan: add reads tasks as JSON on stdin")
    body = json.loads(raw)
    incoming = body.get("tasks", []) if isinstance(body, dict) else body
    if not isinstance(incoming, list) or not incoming:
        raise SystemExit("day-plan: add takes a non-empty list of tasks")

    plan = load(resolve_day(args.date))
    known = {t["id"] for t in plan["tasks"]}
    highest = max((t["order"] for t in plan["tasks"]), default=0)

    staged = []
    for i, t in enumerate(incoming, start=1):
        t.setdefault("id", f"t{highest + i}")
        if t["id"] in known:
            raise SystemExit(f"day-plan: {t['id']} is already in this plan")
        known.add(t["id"])
        t.setdefault("order", highest + i)
        t.setdefault("phase", "")
        t.setdefault("detail", "")
        t.setdefault("why", "")
        t.setdefault("agent", False)
        t.setdefault("human", False)
        t.setdefault("needs", [])
        t.setdefault("status", OPEN)
        if not t.get("title"):
            raise SystemExit(f"day-plan: task {t['id']} has no title")
        refuse_parked_decision(t)
        refuse_jargon_title(t)
        staged.append(t)

    # Blockers resolve against the plan as it will stand, so one new task may
    # wait on another. An id belonging to neither side is refused rather than
    # dropped, on the same ground `new` refuses one.
    for t in staged:
        for n in t["needs"]:
            if n not in known:
                raise SystemExit(f"day-plan: task {t['id']} needs unknown task {n}")

    plan["tasks"].extend(staged)
    save(plan)
    print(f"{plan['date']}: {len(staged)} added, {len(plan['tasks'])} tasks")
    return 0


def cmd_list(args):
    dates = plan_dates()
    if not dates:
        pull_shared()
        dates = plan_dates()
    if not dates:
        print("no plans on file")
        return 0
    for d in dates:
        c = counts(load(d))
        state = "done" if not c[OPEN] else f"{c[OPEN]} open"
        print(f"{d}  {c[DONE]}/{len(load(d)['tasks'])} complete  ({state})")
    return 0


def cmd_current(args):
    freshen()
    print(resolve_day(None))
    return 0


def cmd_show(args):
    freshen()
    plan = load(resolve_day(args.date))
    c = counts(plan)
    head = f"{plan['date']}"
    if plan.get("subject"):
        head += f" — {plan['subject']}"
    print(head)
    print(f"{c[DONE]} done, {c[OPEN]} open, {c[SKIPPED]} skipped")
    if plan.get("artifact"):
        print(f"published: {plan['artifact']}")
    print()
    index = by_id(plan)
    phase = None
    for t in sorted(plan["tasks"], key=lambda x: x["order"]):
        if t["phase"] != phase:
            phase = t["phase"]
            print(f"-- {phase or 'unfiled'}")
        mark = {DONE: "x", SKIPPED: "-", OPEN: " ", RUNNING: ">"}[t["status"]]
        tags = []
        if t["agent"]:
            tags.append("agent")
        if t["human"]:
            tags.append("human")
        blocked = [n for n in t["needs"] if index[n]["status"] == OPEN]
        if blocked:
            tags.append("waits on " + ",".join(blocked))
        suffix = f"  [{'; '.join(tags)}]" if tags else ""
        print(f"  [{mark}] {t['id']}  {t['title']}{suffix}")
        if args.full and t.get("detail"):
            print(f"          {t['detail']}")
    return 0


def cmd_next(args):
    freshen()
    plan = load(resolve_day(args.date))
    rows = ready(plan)
    if not rows:
        c = counts(plan)
        print("nothing ready" if c[OPEN] else "plan complete")
        return 0
    # A running human task holds the queue exactly as an unclosed ready one
    # does. Without this, marking a step started is what hands over the step
    # after it, and one step becomes a queue.
    in_hand = any(t["human"] and t["status"] == RUNNING for t in plan["tasks"])
    shown, held = [], 0
    for t in rows:
        if args.agent_only and not t["agent"]:
            continue
        if args.human_only and not t["human"]:
            continue
        # Agent work fans out, so every ready one is returned at once. Human work
        # does not: a person handed six things at once has been handed a backlog,
        # not a next step, and the run cannot honestly claim to know how long any
        # of them takes. So only the first is returned, and the rest stay behind
        # it until it closes. Handing over a list is then not something a run has
        # to remember not to do -- it does not have the list.
        # Deferring is a decision, and re-offering the task once everything
        # around it is also deferred turns that decision into a question asked
        # twice. It comes back tomorrow, through `carry`, not this afternoon.
        if t.get("deferred") and not args.all:
            held += 1
            continue
        if t["human"] and not args.all:
            if in_hand or any(x["human"] for x in shown):
                held += 1
                continue
        shown.append(t)

    for t in shown:
        who = "agent" if t["agent"] else ("human" if t["human"] else "either")
        print(f"{t['id']}\t{who}\t{t['phase']}\t{t['title']}")
    if not shown:
        print("nothing ready that has not been put off today")
    if held:
        print(f"# {held} task(s) held back; --all to see them", file=sys.stderr)
    return 0


def _mark(args, status):
    plan = load(resolve_day(args.date))
    index = by_id(plan)
    for tid in args.ids:
        if tid not in index:
            raise SystemExit(f"day-plan: no task {tid}")
        index[tid]["status"] = status
        if status == RUNNING:
            index[tid]["started"] = _stamp()
            index[tid].pop("closed", None)
            index[tid].pop("released", None)
            # Whose dispatch this was. A marker with no owner cannot be told
            # apart from one whose session is still working it, which is how a
            # task ends up reading as in flight for the rest of the day.
            owner = _session()
            if owner:
                index[tid]["session"] = owner
            else:
                index[tid].pop("session", None)
        else:
            index[tid]["closed"] = _stamp()
        if getattr(args, "note", None):
            index[tid]["note"] = args.note
    save(plan)
    c = counts(plan)
    print(
        f"{plan['date']}: {c[DONE]} done, {c[RUNNING]} in flight, "
        f"{c[OPEN]} open, {c[SKIPPED]} skipped"
    )
    report = sync_page(plan)
    if report:
        print(f"  page: {report}")
    return 0


def _session():
    """This session, as far as anything here can tell.

    Subagents inherit their parent's id, so this separates one session from
    another and never a session from the agents it dispatched. That is the
    distinction a released marker needs.
    """
    return os.environ.get("CLAUDE_CODE_SESSION_ID") or ""


def _release(plan, ids):
    """Hand tasks back from in flight without closing them.

    Returns the ids that moved. `started` and the owner come off, because an
    open task has neither, and `released` goes on so the carrier can tell this
    apart from the dispatch it undoes.
    """
    index = by_id(plan)
    moved = []
    for tid in ids:
        task = index.get(tid)
        if task is None or task.get("status") != RUNNING:
            continue
        task["status"] = OPEN
        task.pop("started", None)
        task.pop("session", None)
        task["released"] = _stamp()
        moved.append(tid)
    return moved


def cmd_release(args):
    """Say that work stopped without finishing.

    Between dispatch and done there was nothing to say. `done` is a lie while
    the work is unfinished, `skip` is a decision nobody made, and `defer` says
    it is not being offered today when it is. So a task whose agent stopped
    stayed marked in flight, reading on the page as an hour of work still
    happening, and the ledger had no way to be corrected.
    """
    plan = load(resolve_day(args.date))
    index = by_id(plan)
    for tid in args.ids:
        if tid not in index:
            raise SystemExit(f"day-plan: no task {tid}")
        if index[tid].get("status") != RUNNING:
            raise SystemExit(
                f"day-plan: {tid} is {index[tid].get('status')}, not in flight.\n"
                "  release hands back a task that was dispatched and stopped."
            )
    moved = _release(plan, args.ids)
    save(plan)
    c = counts(plan)
    print(
        f"{plan['date']}: released {', '.join(moved)} -- {c[DONE]} done, "
        f"{c[RUNNING]} in flight, {c[OPEN]} open, {c[SKIPPED]} skipped"
    )
    report = sync_page(plan)
    if report:
        print(f"  page: {report}")
    return 0


def cmd_start(args):
    """Mark tasks as in flight, the moment they are dispatched.

    Without this the page shows an agent's hour of work as an untouched
    checkbox, which reads as nothing happening. It also keeps `next` honest:
    a running task is not ready, and returning it invites a second dispatch of
    work already under way.
    """
    return _mark(args, RUNNING)


def cmd_done(args):
    return _mark(args, DONE)


# A skip closes work on the ground it is not being done. Work that is being
# done, only on another day, gets moved -- and the reason written for a skip is
# where that distinction goes wrong, because "moved to the 1st" reads as a
# record while leaving the task sitting on a plan it does not belong to.
ANOTHER_DAY = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}"
    r"|(?:next\s+|on\s+)?(?:mon|tues|wednes|thurs|fri|satur|sun)day"
    r"|tomorrow|next\s+(?:week|month)"
    r"|(?:the\s+)?\d{1,2}(?:st|nd|rd|th)\b)",
    re.I,
)


def cmd_skip(args):
    if not args.note:
        raise SystemExit("day-plan: skip takes --note saying why")
    hit = ANOTHER_DAY.search(args.note)
    if hit and os.environ.get("INTELLIGENCE_ALLOW_PLAN_SKIP") != "1":
        raise SystemExit(
            f"day-plan: the reason names another day ({hit.group(0)!r}), so this is a\n"
            "  move rather than a skip. A skipped task stays on this plan and reads\n"
            "  on its page, which is how a day ends up showing work that is not its\n"
            "  own. Use: day-plan.py move " + " ".join(args.ids) + " --to <date>\n"
            "  INTELLIGENCE_ALLOW_PLAN_SKIP=1 overrides a misread."
        )
    return _mark(args, SKIPPED)


EYEBROW_DAY = re.compile(r'(<div class="eyebrow">\s*<span>)[^<]*(</span>)')
TODAY_ROW = re.compile(r'(<div class="clock-row)\s+is-today(")')
CLOCK_ROW = re.compile(r'(<div class="clock-row)(">\s*<span class="clock-day">)([^<]*)(</span>)')


def _reday_page(text, was, now):
    """Rewrite what a page says about which day it is.

    A page states its day in three places a reader or a browser acts on: the
    masthead date, the marked row in the timeline, and the key each checkbox
    saves under. A page carrying the day before under a new name reads as that
    day, marks that day as the one in hand, and writes today's boxes into the
    store yesterday's already holds, so opening either page shows the other's
    ticks.

    The headline and the standfirst are the day's own words and stay as they
    are; nothing mechanical can write those.
    """
    d = _date.fromisoformat(now)
    long_day = "%s %d %s" % (d.strftime("%A"), d.day, d.strftime("%B %Y"))
    short_day = "%s %d" % (d.strftime("%a"), d.day)

    text = EYEBROW_DAY.sub(lambda m: m.group(1) + long_day + m.group(2), text, 1)
    text = TODAY_ROW.sub(lambda m: m.group(1) + m.group(2), text)
    text = CLOCK_ROW.sub(
        lambda m: (m.group(1) + (" is-today" if m.group(3).strip() == short_day else "")
                   + m.group(2) + m.group(3) + m.group(4)),
        text)
    return text.replace("day-plan:%s:" % was, "day-plan:%s:" % now)


def cmd_carry(args):
    """Open the next plan from what this one did not finish, taking the work with it.

    Unfinished work is the bulk of any next-day plan, and retyping it is how a
    task quietly goes missing. The needs are rewritten to drop anything that
    already cleared, so a task carried forward is not still waiting on
    yesterday's finished work.

    It is a move rather than a copy. A task sitting open on two plans is a task
    two days both claim, and a day gone by still showing open work reads as one
    that never ended -- which is also what made the ledger list four plans with
    work left when there was only ever one. What stays behind is what that day
    actually closed, and that is the record of it.

    The link travels with the work. One page is the day plan, renamed to
    whichever day it now shows, and the day it replaces keeps its record in the
    log every page carries.
    """
    src = load(resolve_day(args.date))
    target = args.to or (_date.fromisoformat(src["date"]) + timedelta(days=1)).isoformat()
    if path_for(target).is_file() and not args.force:
        raise SystemExit(f"day-plan: {target} already exists; --force to replace")
    index = by_id(src)
    kept = [t for t in sorted(src["tasks"], key=lambda x: x["order"]) if t["status"] in UNFINISHED]
    tasks = []
    for i, t in enumerate(kept, start=1):
        c = dict(t)
        c["status"] = OPEN
        c.pop("deferred", None)
        c["order"] = i
        c["needs"] = [n for n in t["needs"] if index[n]["status"] in UNFINISHED]
        c.pop("closed", None)
        tasks.append(c)
    plan = normalize(
        {
            "date": target,
            "subject": src.get("subject", ""),
            "carried_from": src["date"],
            "artifact": src.get("artifact", ""),
            "tasks": tasks,
        }
    )
    save(plan)

    # The page goes with the work, or the link handed over shows the day
    # before under its own name until somebody sits down and writes a new one.
    # A rollover that happens on a clock has nobody to do that, and renaming
    # the page is half of what it is for.
    going = {t["id"] for t in kept}
    staying = {t["id"] for t in src["tasks"] if t["id"] not in going}
    carried_page = page_path(src)
    if carried_page.is_file():
        _write(page_path(plan),
               _reday_page(carried_page.read_text(), src["date"], target))
        plan["html"] = str(page_path(plan))
        save(plan)
        for tid in sorted(staying):
            strip_task_from_page(plan, tid)

    # The work goes rather than doubles, by the same route `move` takes: the
    # carrier cannot tell a removal from a copy that arrived short, so the plan
    # records which it was or the next sync hands every task straight back.
    if going:
        src.setdefault("moved", []).extend(
            {"id": tid, "to": target, "at": _stamp()} for tid in sorted(going))
        src["tasks"] = [t for t in src["tasks"] if t["id"] not in going]
        for i, t in enumerate(sorted(src["tasks"], key=lambda x: x["order"]), start=1):
            t["order"] = i
    # Two plans naming one url is a page the older of them would demand back.
    src["artifact"] = ""
    src.pop("published_state", None)
    save(src)
    for tid in sorted(going):
        strip_task_from_page(src, tid)
    save(src)
    sync_page(src)
    sync_page(load(target))
    print(f"{target}: {len(tasks)} carried from {src['date']}, "
          f"{len(src['tasks'])} left as its record")
    return 0


def strip_task_from_page(plan, task_id):
    """Take a task's block out of the page, and its section if it empties.

    The page is hand-written prose the ledger only stamps statuses onto, so a
    task removed from the ledger leaves its paragraphs behind -- which is the
    whole complaint: a plan showing work that is not this day's. `sync_page`
    refuses a page whose task count no longer matches, so leaving this undone
    would jam every later write rather than pass quietly.
    """
    target = page_path(plan)
    if not target.is_file():
        return False
    text = target.read_text()
    label = re.search(
        r'\n?[ \t]*<label class="task"(?=[^>]*data-id="%s")[^>]*>.*?</label>\n'
        % re.escape(task_id),
        text,
        re.S,
    )
    if not label:
        return False
    text = text[: label.start()] + "\n" + text[label.end():]

    # A phase that held only that task is now a heading over nothing. Sections
    # are flat, so the one wrapping the hole is the last opened before it.
    start = text.rfind('<section class="phase">', 0, label.start())
    if start != -1:
        end = text.find("</section>", start)
        if end != -1:
            end += len("</section>")
            section = text[start:end]
            if 'class="task"' not in section:
                head = text.rfind("\n", 0, start)
                text = text[: head if head != -1 else start] + text[end:]
            else:
                held = section.count('class="task"')
                section = re.sub(
                    r'(<span class="phase-count">)\d+ tasks?(</span>)',
                    rf"\g<1>{held} task{'' if held == 1 else 's'}\g<2>",
                    section,
                )
                text = text[:start] + section + text[end:]

    _write(target, re.sub(r"\n{3,}", "\n\n", text))
    return True


def cmd_move(args):
    """Send tasks to another day's plan, leaving nothing behind on this one.

    A task that belongs to a different day and is merely marked closed here
    still reads on the page, and a plan showing work for another day is a plan
    that has to be filtered by whoever reads it. So the move is a move: out of
    this ledger, out of this page, and into the target's.

    Dependencies are refused rather than rewritten. A task left behind that
    waits on one going, or one going that waits on something staying open, is
    an ordering the move would silently break, and the operator is the one who
    knows which way it should resolve.
    """
    src = load(resolve_day(args.date))
    index = by_id(src)
    for tid in args.ids:
        if tid not in index:
            raise SystemExit(f"day-plan: no task {tid}")
    going = set(args.ids)

    stranded = [
        f"{t['id']} waits on {n}"
        for t in src["tasks"]
        if t["id"] not in going
        for n in t["needs"]
        if n in going
    ]
    held = [
        f"{t['id']} waits on {n}, which is staying and still open"
        for t in src["tasks"]
        if t["id"] in going
        for n in t["needs"]
        if n not in going and index[n]["status"] in UNFINISHED
    ]
    if stranded or held:
        raise SystemExit(
            "day-plan: the move would break the ordering:\n  "
            + "\n  ".join(stranded + held)
            + "\n  settle those first, or move them together."
        )

    if args.to == src["date"]:
        raise SystemExit("day-plan: a task cannot move to the day it is already on")

    moving = [dict(index[t]) for t in args.ids]
    if path_for(args.to).is_file():
        dest = load(args.to)
        clash = {t["id"] for t in dest["tasks"]} & going
        if clash:
            raise SystemExit(
                f"day-plan: {args.to} already holds {', '.join(sorted(clash))}"
            )
        highest = max((t["order"] for t in dest["tasks"]), default=0)
    else:
        dest = normalize({"date": args.to, "subject": src.get("subject", ""), "tasks": []})
        highest = 0

    for i, t in enumerate(moving, start=1):
        t["status"] = OPEN
        t["order"] = highest + i
        t["needs"] = [n for n in t["needs"] if n in going]
        for gone in ("closed", "started", "deferred", "note"):
            t.pop(gone, None)
    dest["tasks"].extend(moving)
    save(dest)

    # The carrier cannot tell a removal from a copy gone short, so the plan
    # says which it was. Without this the next sync hands every moved task
    # back, and the day shows work belonging to another one again.
    src.setdefault("moved", []).extend(
        {"id": t["id"], "to": args.to, "at": _stamp()} for t in moving
    )
    src["tasks"] = [t for t in src["tasks"] if t["id"] not in going]
    for i, t in enumerate(sorted(src["tasks"], key=lambda x: x["order"]), start=1):
        t["order"] = i
    save(src)

    missed = [t for t in args.ids if not strip_task_from_page(src, t)]
    save(src)
    sync_page(src)
    sync_page(dest)
    print(f"{src['date']}: {len(moving)} moved to {args.to}, {len(src['tasks'])} left")
    if missed:
        print(f"  not on the page to remove: {', '.join(missed)}")
    return 0


def cmd_artifact(args):
    plan = load(resolve_day(args.date))
    plan["artifact"] = args.url
    if args.html:
        plan["html"] = args.html
    save(plan)
    sync_page(plan)
    plan = load(plan["date"])
    plan["published_state"] = state_hash(plan)
    plan["published_at"] = _stamp()
    save(plan)
    print(f"{plan['date']}: {args.url}")
    return 0


def dependents_of(plan, ids):
    """Every task that needs one of these, transitively, plus the tasks named.

    A chain moves as a chain. Deferring a blocker on its own leaves what waits
    on it sitting high in the order, where it reads as the next thing and can
    never be ready.
    """
    moving = set(ids)
    changed = True
    while changed:
        changed = False
        for t in plan["tasks"]:
            if t["id"] in moving:
                continue
            if any(n in moving for n in t["needs"]):
                moving.add(t["id"])
                changed = True
    return moving


def cmd_resume(args):
    """Put deferred tasks back in play without moving them.

    A deferral made on one reading of the plan outlives the reading. Work put
    off as a dependent of something else stays put off after the dependency is
    gone, and the ordering it was given is usually still the right one, so
    only the deferral lifts.
    """
    plan = load(resolve_day(args.date))
    index = by_id(plan)
    for tid in args.ids:
        if tid not in index:
            raise SystemExit(f"day-plan: no task {tid}")
    lifted = [t for t in (index[i] for i in args.ids) if t.pop("deferred", None)]
    save(plan)
    sync_page(plan)
    names = ", ".join(t["id"] for t in lifted) or "nothing that was deferred"
    print(f"{plan['date']}: resumed {names}")
    return 0


def cmd_needs(args):
    """Reset what a task waits on.

    Blockers are written when the plan is agreed, from what is known then. A
    fact that changes underneath one leaves a task waiting on something that
    no longer gates it, and nothing about a stale blocker looks different from
    a real one -- the task simply never becomes ready and the run reports it
    as blocked.

    A blocker nobody wrote is refused here, as it is at `new`, and so is a
    task waiting on itself or on a cycle.
    """
    plan = load(resolve_day(args.date))
    index = by_id(plan)
    if args.id not in index:
        raise SystemExit(f"day-plan: no task {args.id}")
    wanted = [] if args.none else list(args.on)
    for n in wanted:
        if n not in index:
            raise SystemExit(f"day-plan: task {args.id} cannot need unknown task {n}")
        if n == args.id:
            raise SystemExit(f"day-plan: task {args.id} cannot need itself")
    was = index[args.id]["needs"]
    index[args.id]["needs"] = wanted

    # A cycle is a plan that can never start, and it is easier to write than to
    # notice, so the whole graph is walked rather than the one edge changed.
    seen, stack = set(), []

    def walk(tid):
        if tid in stack:
            raise SystemExit("day-plan: that would make a cycle: "
                             + " -> ".join(stack[stack.index(tid):] + [tid]))
        if tid in seen:
            return
        stack.append(tid)
        for n in index[tid]["needs"]:
            walk(n)
        stack.pop()
        seen.add(tid)

    for t in plan["tasks"]:
        walk(t["id"])

    save(plan)
    sync_page(plan)
    print(f"{plan['date']}: {args.id} needs {', '.join(wanted) or 'nothing'}"
          f" (was {', '.join(was) or 'nothing'})")
    return 0


def cmd_amend(args):
    """Reword a task whose scope changed after the plan was agreed.

    A plan meets facts it was written without, and a task that no longer says
    what the work is silently stops matching it. Rewording keeps the ordering,
    the blocking and the history that a delete-and-re-add would lose.

    Only the prose moves. Status, order and needs are the plan's structure and
    have their own verbs.
    """
    plan = load(resolve_day(args.date))
    index = by_id(plan)
    if args.id not in index:
        raise SystemExit(f"day-plan: no task {args.id}")
    task = index[args.id]
    fields = {"title": args.title, "detail": args.detail, "why": args.why}
    moved = {k: v for k, v in fields.items() if v is not None}
    if not moved:
        raise SystemExit("day-plan: amend takes at least one of --title, --detail, --why")
    if "title" in moved and not moved["title"].strip():
        raise SystemExit("day-plan: a task cannot lose its title")
    refuse_parked_decision({**task, **moved})
    refuse_jargon_title({**task, **moved})
    task.update(moved)
    save(plan)
    sync_page(plan)
    print(f"{plan['date']}: amended {args.id} ({', '.join(sorted(moved))})")
    print("  the page carries its own copy; edit it there too before republishing")
    return 0


def cmd_defer(args):
    """Send tasks to the end of the order without closing them.

    Ordering is what `next` reads, so a task nobody wants to do today and a
    task nobody can do today need to be told apart. Skipping records a
    decision not to do something and frees whatever waits on it; deferring
    keeps the work and the blocking intact and only moves when it is offered.
    """
    plan = load(resolve_day(args.date))
    index = by_id(plan)
    for tid in args.ids:
        if tid not in index:
            raise SystemExit(f"day-plan: no task {tid}")
    moving = dependents_of(plan, args.ids)
    ordered = sorted(plan["tasks"], key=lambda x: x["order"])
    staying = [t for t in ordered if t["id"] not in moving]
    going = [t for t in ordered if t["id"] in moving]
    for i, t in enumerate(staying + going, start=1):
        t["order"] = i
    for t in going:
        t["deferred"] = _stamp()
    save(plan)
    sync_page(plan)
    carried = [t["id"] for t in going if t["id"] not in set(args.ids)]
    tail = f" (with {', '.join(carried)})" if carried else ""
    print(f"{plan['date']}: deferred {', '.join(args.ids)}{tail}")
    return 0


def share_record():
    """What each plan on this machine settled with the mirror, by date.

    The carrier writes this after a push it watched succeed, so it says what
    landed rather than what was scheduled. Nothing else may write it: a mark
    left by the act of scheduling would say a plan travelled the moment it was
    queued, which is the reading this exists to refuse.
    """
    try:
        body = json.loads((Path(_state_root()) / SHARED_STATE).read_text())
    except (OSError, ValueError):
        return {}
    plans = body.get("plans")
    return plans if isinstance(plans, dict) else {}


def unshared():
    """The plans holding work the mirror does not have, each with why.

    A plan whose stamp matches the one recorded against a successful push has
    travelled. Everything else has not, and the four ways that happens want
    different answers, so they are told apart rather than folded into one: a
    plan the carrier has never carried, one written since the trip it last
    made, one the mirror refused, and one held back for a credential it quotes.
    """
    record = share_record()
    rows = []
    for day in sorted(plan_dates()):
        try:
            plan = load(day)
        except (SystemExit, ValueError):
            continue
        entry = record.get(day) or {}
        state = entry.get("state")
        reason = entry.get("reason") or ""
        # The same reading the carrier takes: a plan written before writes were
        # stamped carries only its creation, and holding a session forever over
        # one is a gate nothing can open.
        stamp = plan.get("updated") or plan.get("created") or ""
        if state == "shared" and entry.get("stamp") == stamp:
            continue
        if state == "held":
            rows.append((day, "held off the mirror: it carries " +
                         (reason or "a credential")))
        elif state == "refused":
            rows.append((day, "the mirror refused the last push" +
                         (f": {reason}" if reason else "")))
        elif state == "shared":
            rows.append((day, "written since the push that shared it"))
        else:
            rows.append((day, "never pushed"))
    return rows


def carry_now(stranded):
    """Make the trip a session end would otherwise be refused for, then re-read.

    A ledger write schedules a push that waits out the rest of the burst, so a
    session reaching its end inside that window stands behind the mirror only
    because the trip has not come round yet. A refusal there hands a person a
    command whose whole effect is to start the same push a few seconds early,
    and which reports having nothing to do once the scheduled one has been and
    gone. Neither reading is worth anybody's attention, and both wear the face
    of the failure this gate exists for.

    So the gate carries the plans itself and reads the record again. What
    survives that is behind for a reason no push settles -- a mirror refusing
    it, a credential holding it back, a carrier that is not installed -- which
    is the case worth stopping on.
    """
    tool = _carrier()
    if tool is None:
        return stranded
    try:
        subprocess.run([sys.executable, str(tool), "push", "--plans"],
                       env=_carrier_env(), timeout=CARRY_TIMEOUT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False)
    except (OSError, subprocess.SubprocessError):
        # A push that did not finish settles nothing, timeout included, so the
        # reading already taken stands rather than being retaken against a trip
        # that stopped halfway.
        return stranded
    return unshared()


def page_behind():
    """The plan whose published page no longer says what its ledger says."""
    try:
        plan = load(resolve_day(None))
    except SystemExit:
        return None
    if not plan.get("artifact"):
        return None
    if plan.get("published_state") == state_hash(plan):
        return None
    return plan


def cmd_guard_stop(args):
    """Refuse to end a session that left the page lying or the ledger stranded.

    Everything else here is a convenience; these two are the parts that hold,
    and they are one failure at two depths. A run closes tasks all morning, the
    ledger is correct, and the page opened by whoever reads it still shows the
    work as untouched -- unnoticed, because a stale page looks exactly like a
    page with nothing done. `sync` keeps the file true on its own, so the step
    left to forget is the republish.

    A stranded ledger is the same shape one layer down. The push that shares a
    write is debounced, so a session that ends inside the quiet window takes
    the process that was going to make it -- always, on a container, where the
    session ending is the machine going away. The next session, on the next
    machine, then works the plan as it stood this morning and closes tasks that
    are already closed. A scheduled push is not a push and a rejected one is
    not either, so what settles this is the carrier's record of what landed.
    """
    if os.environ.get("INTELLIGENCE_DAYPLAN_OFF") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    if payload.get("stop_hook_active"):
        return 0
    # A machine holding no plans has nothing to be behind on, and reaching the
    # carrier for one would put a network fetch between a session and its reply.
    if not plan_dates():
        return 0

    problems = []

    # An owner that has gone leaves a marker nothing will ever clear, so it is
    # repaired here. An owner still present is asked instead, because only it
    # knows whether the work finished, and a ledger that guesses between done
    # and unfinished is worse than one that stops.
    here = payload.get("session_id") or _session()
    for day in plan_dates():
        plan = load(day)
        held, orphaned = [], []
        for task in plan.get("tasks") or []:
            if task.get("status") != RUNNING:
                continue
            owner = task.get("session") or ""
            (held if not owner or owner == here else orphaned).append(task["id"])
        if orphaned:
            _release(plan, orphaned)
            save(plan)
            sync_page(plan)
            problems.append(
                f"Released {', '.join(orphaned)} on {day}: marked in flight by "
                "an owner that has ended.\nThe page has been rewritten and now "
                "needs republishing."
            )
        if held:
            problems.append(
                f"The {day} plan still shows {', '.join(held)} in flight.\n"
                "A task nobody is working cannot stay in flight -- the page "
                "reads as an agent mid-job. Close it or hand it back:\n"
                f"  ~/.intelligence/tools/day-plan.py done {' '.join(held)}\n"
                f"  ~/.intelligence/tools/day-plan.py release {' '.join(held)}"
            )

    stranded = [] if _sync_off() else unshared()
    if stranded:
        stranded = carry_now(stranded)
    if stranded:
        problems.append(
            "Plan state on this machine has not reached the mirror, and the "
            "push made for it settled none of these:\n"
            + "\n".join(f"  {day}: {why}" for day, why in stranded)
            + "\nUntil they land, the next session works the plan as it stood "
            "before. The carrier prints what stopped it:\n"
            "  ~/.intelligence/tools/pass-state.py push"
        )
    plan = page_behind()
    if plan is not None:
        c = counts(plan)
        problems.append(
            f"The {plan['date']} plan page is behind its ledger: "
            f"{c[DONE]} done, {c[RUNNING]} in flight, {c[SKIPPED]} skipped.\n"
            f"Republish {plan.get('html')} to {plan['artifact']} with the "
            "Artifact tool, passing that url so it updates in place, then run:\n"
            "  ~/.intelligence/tools/day-plan.py published"
        )
    if not problems:
        return 0
    print("\n\n".join(problems), file=sys.stderr)
    return 2


def main(argv=None):
    ap = argparse.ArgumentParser(prog="day-plan", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="write a plan from JSON on stdin")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_new, writes=True)

    p = sub.add_parser("add", help="append tasks to a plan from JSON on stdin")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_add, writes=True)

    p = sub.add_parser("list", help="plans on file")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("current", help="the plan a run should work")
    p.set_defaults(fn=cmd_current)

    p = sub.add_parser("show", help="tasks grouped by phase")
    p.add_argument("date", nargs="?")
    p.add_argument("--full", action="store_true", help="include each task's detail")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("next", help="tasks unblocked right now")
    p.add_argument("--date")
    p.add_argument("--all", action="store_true",
                   help="every ready task, human ones included, rather than one at a time")
    p.add_argument("date", nargs="?")
    p.add_argument("--agent-only", action="store_true")
    p.add_argument("--human-only", action="store_true")
    p.set_defaults(fn=cmd_next)

    p = sub.add_parser("done", help="mark tasks complete")
    p.add_argument("ids", nargs="+")
    p.add_argument("--date")
    p.add_argument("--note")
    p.set_defaults(fn=cmd_done, writes=True)

    p = sub.add_parser("skip", help="mark tasks deliberately not done")
    p.add_argument("ids", nargs="+")
    p.add_argument("--date")
    p.add_argument("--note", required=False)
    p.set_defaults(fn=cmd_skip, writes=True)

    p = sub.add_parser("carry", help="open the next plan from what is unfinished")
    p.add_argument("date", nargs="?")
    p.add_argument("--to", help="target date; default is the day after")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_carry, writes=True)

    p = sub.add_parser("start", help="mark tasks as in flight")
    p.add_argument("ids", nargs="+")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_start, writes=True)

    p = sub.add_parser("release", help="hand a task back from in flight")
    p.add_argument("ids", nargs="+")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_release, writes=True)

    p = sub.add_parser(
        "rollover",
        help="carry onto today if the day has turned; safe on a clock")
    p.add_argument("--check", action="store_true",
                   help="answer whether one is due and change nothing; "
                        "exits 0 when it is")
    p.set_defaults(fn=cmd_rollover, writes=True)

    p = sub.add_parser(
        "runsheet",
        help="the day numbered, split into agent steps and yours")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_runsheet)

    p = sub.add_parser("sync", help="rewrite the page from the ledger")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_sync, writes=True)

    p = sub.add_parser("page", help="is the published page still true")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_page)

    p = sub.add_parser("published", help="record the page as republished")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_published, writes=True)

    p = sub.add_parser("resume", help="lift a deferral")
    p.add_argument("ids", nargs="+")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_resume, writes=True)

    p = sub.add_parser("needs", help="reset what a task waits on")
    p.add_argument("id")
    p.add_argument("on", nargs="*")
    p.add_argument("--none", action="store_true", help="clear every blocker")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_needs, writes=True)

    p = sub.add_parser("amend", help="reword a task whose scope changed")
    p.add_argument("id")
    p.add_argument("--title")
    p.add_argument("--detail")
    p.add_argument("--why")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_amend, writes=True)

    p = sub.add_parser("defer", help="send tasks and their dependents to the end")
    p.add_argument("ids", nargs="+")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_defer, writes=True)

    p = sub.add_parser(
        "guard-stop",
        help="Stop hook: has the ledger travelled and is the page still true")
    p.set_defaults(fn=cmd_guard_stop)

    p = sub.add_parser("move", help="send tasks to another day's plan")
    p.add_argument("ids", nargs="+")
    p.add_argument("--to", required=True)
    p.add_argument("--date")
    p.set_defaults(fn=cmd_move)

    p = sub.add_parser("artifact", help="record where the plan was published")
    p.add_argument("url")
    p.add_argument("--date")
    p.add_argument("--html")
    p.set_defaults(fn=cmd_artifact, writes=True)

    args = ap.parse_args(argv)
    if not getattr(args, "writes", False):
        return args.fn(args)
    # Every verb that moves a task loads the plan, changes it, and writes it
    # back. Two of those running at once interleave into one losing the other's
    # change, so the hold spans the whole command rather than the write alone.
    with _held():
        return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
