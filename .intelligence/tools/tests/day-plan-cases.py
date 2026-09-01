#!/usr/bin/env python3
"""Cases the day plan has to get right.

The ledger exists so the session that runs a plan can trust what the session
that wrote it agreed. Two things carry that trust: a task never comes back
ready while something it needs is still open, and unfinished work survives the
day boundary with its dependencies rewritten rather than retyped.

The rest guards the failure that costs most -- a plan silently accepting a task
that names a blocker nobody wrote, which reads as ordered and is not -- and the
page, which is the half a person actually reads and so the half whose drift
goes unnoticed.

Every run pins the ledger inside a TemporaryDirectory through
INTELLIGENCE_STATE_DIR, so no case can write into the live plan state.

  day-plan-cases.py        run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import date as _date, timedelta as _timedelta
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "day-plan.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def contains(label, haystack, needle):
    if needle not in haystack:
        FAILURES.append(f"{label}: {needle!r} missing from {haystack!r}")


def missing(label, haystack, needle):
    if needle in haystack:
        FAILURES.append(f"{label}: {needle!r} unexpectedly present")


def path_of(state, day):
    """Where a plan for one day lands under a fixture state tree."""
    return Path(state) / "day-plans" / f"{day}.json"


def run(state, *argv, stdin="", carrier=None, share=False, extra=None):
    """The tool under test, pinned to a fixture state tree.

    The ledger carries itself between machines, so a write schedules a push, a
    read fetches whatever it could have been overtaken by, and an empty tree
    pulls before it reports empty. All three reach the network, so all three
    are off unless a case asks for them and hands over a carrier of its own to
    answer. `extra` puts a variable back on top, which is how a case pins the
    override rather than the absence of a carrier.
    """
    env = dict(os.environ)
    env["INTELLIGENCE_STATE_DIR"] = str(state)
    env["HOME"] = str(state)
    env.pop("INTELLIGENCE_DAYPLAN_LOCK_HELD", None)
    if carrier is None and not share:
        env["INTELLIGENCE_DAYPLAN_NO_SYNC"] = "1"
    else:
        env.pop("INTELLIGENCE_DAYPLAN_NO_SYNC", None)
    if carrier is not None:
        env["INTELLIGENCE_PASS_STATE"] = str(carrier)
    env.update(extra or {})
    return subprocess.run(
        [sys.executable, str(TARGET), *argv],
        input=stdin, capture_output=True, text=True, env=env,
    )


PLAN = {
    "date": "2026-08-28",
    "subject": "taylorurl.com",
    "tasks": [
        {"id": "gbp", "phase": "Profile", "title": "Create the profile", "human": True},
        {"id": "verify", "phase": "Profile", "title": "Submit verification",
         "human": True, "needs": ["gbp"]},
        {"id": "www", "phase": "Indexing", "title": "Settle on www", "agent": True},
        {"id": "gsc", "phase": "Indexing", "title": "Verify Search Console",
         "needs": ["www"]},
        {"id": "social", "phase": "Social", "title": "Connect the channels",
         "needs": ["verify"]},
    ],
}


def case_ordering(state):
    """A task is ready only when everything it needs has closed."""
    run(state, "new", stdin=json.dumps(PLAN))

    out = run(state, "next").stdout
    contains("ready at open", out, "gbp")
    contains("ready at open", out, "www")
    missing("blocked stays back", out, "verify")
    missing("blocked stays back", out, "gsc")

    run(state, "done", "www")
    out = run(state, "next").stdout
    contains("cleared blocker frees dependent", out, "gsc")
    missing("done task leaves the queue", out, "\twww\t")

    # A skip is a decision, so its dependents move rather than stalling.
    run(state, "skip", "gbp", "--note", "no bank card to hand")
    out = run(state, "next").stdout
    contains("skipped blocker also frees", out, "verify")


def case_carry(state):
    """Unfinished work moves to the next day without its settled blockers."""
    run(state, "new", stdin=json.dumps(PLAN))
    run(state, "done", "www", "gbp")
    run(state, "carry", "2026-08-28")

    plan = json.loads((state / "day-plans" / "2026-08-29.json").read_text())
    ids = [t["id"] for t in plan["tasks"]]
    check("finished work is not carried", "www" in ids, False)
    check("unfinished work is carried", sorted(ids), ["gsc", "social", "verify"])

    index = {t["id"]: t for t in plan["tasks"]}
    check("cleared need is dropped", index["gsc"]["needs"], [])
    check("open need is kept", index["social"]["needs"], ["verify"])
    check("carry records its source", plan["carried_from"], "2026-08-28")

    # Everything carried is unblocked or waiting on something also carried, so
    # the new day opens with real work rather than an empty queue.
    out = run(state, "next", "2026-08-29").stdout
    contains("carried plan opens with work", out, "verify")


def case_unknown_need(state):
    """A blocker nobody wrote is refused, not silently ignored."""
    bad = {
        "date": "2026-09-01",
        "tasks": [{"id": "a", "title": "Depends on a ghost", "needs": ["nope"]}],
    }
    r = run(state, "new", stdin=json.dumps(bad))
    check("unknown need is refused", r.returncode != 0, True)
    contains("refusal names the task", r.stderr + r.stdout, "nope")

    dupe = {
        "date": "2026-09-02",
        "tasks": [{"id": "a", "title": "One"}, {"id": "a", "title": "Two"}],
    }
    r = run(state, "new", stdin=json.dumps(dupe))
    check("duplicate id is refused", r.returncode != 0, True)

    untitled = {"date": "2026-09-03", "tasks": [{"id": "a", "detail": "no title"}]}
    r = run(state, "new", stdin=json.dumps(untitled))
    check("untitled task is refused", r.returncode != 0, True)


def case_current(state):
    """`current` points at the plan with work left, not merely the newest."""
    run(state, "new", stdin=json.dumps(PLAN))
    later = dict(PLAN, date="2026-08-30", tasks=[{"id": "z", "title": "Only task"}])
    run(state, "new", stdin=json.dumps(later))

    run(state, "done", "z", "--date", "2026-08-30")
    check("finished newest is skipped", run(state, "current").stdout.strip(), "2026-08-28")

    for tid in ("gbp", "verify", "www", "gsc", "social"):
        run(state, "done", tid, "--date", "2026-08-28")
    check("all finished falls back to newest",
          run(state, "current").stdout.strip(), "2026-08-30")


# A page the reader opens is the deliverable, and the ledger is what it claims
# to show. These cases hold the join between them: an in-flight task is not
# ready, the page carries every task's real status, and a run that closed work
# without republishing is caught rather than trusted.

PAGE = """<html>
<style>.task { color: red; }</style>
<span id="done">0</span><span> / 5</span>
<label class="task"><input type="checkbox" data-k="t1"><div class="task-body"><p class="task-title">Create the profile</p></div></label>
<label class="task"><input type="checkbox" data-k="t2"><div class="task-body"><p class="task-title">Submit verification</p></div></label>
<label class="task"><input type="checkbox" data-k="t3"><div class="task-body"><p class="task-title">Settle on www</p></div></label>
<label class="task"><input type="checkbox" data-k="t4"><div class="task-body"><p class="task-title">Verify Search Console</p></div></label>
<label class="task"><input type="checkbox" data-k="t5"><div class="task-body"><p class="task-title">Connect the channels</p></div></label>
</html>
"""


def seed_page(state):
    """A plan with a page attached, as `artifact` would leave it."""
    run(state, "new", stdin=json.dumps(PLAN))
    html = state / "plan.html"
    html.write_text(PAGE)
    run(state, "artifact", "https://example.invalid/p", "--html", str(html))
    return html


def case_running_is_not_ready(state):
    run(state, "new", stdin=json.dumps(PLAN))
    contains("www ready before dispatch", run(state, "next").stdout, "www")

    run(state, "start", "www")
    missing("dispatched task still ready", run(state, "next").stdout, "www")
    missing("running task does not unblock its dependent",
            run(state, "next").stdout, "gsc")

    run(state, "done", "www")
    contains("finishing it frees the dependent", run(state, "next").stdout, "gsc")


def case_running_survives_the_day(state):
    run(state, "new", stdin=json.dumps(PLAN))
    run(state, "start", "www")
    run(state, "carry", "--to", "2026-08-29")
    carried = json.loads((state / "day-plans" / "2026-08-29.json").read_text())
    ids = [t["id"] for t in carried["tasks"]]
    contains("in-flight work carries forward", " ".join(ids), "www")
    statuses = {t["id"]: t["status"] for t in carried["tasks"]}
    check("carried task reopens", statuses["www"], "open")


def case_release_hands_a_task_back(state):
    run(state, "new", stdin=json.dumps(PLAN))
    run(state, "start", "www", extra={"CLAUDE_CODE_SESSION_ID": "one"})
    task = {t["id"]: t for t in json.loads(path_of(state, "2026-08-28").read_text())["tasks"]}
    check("a dispatch records its owner", task["www"].get("session"), "one")

    out = run(state, "release", "www")
    check("release succeeds", out.returncode, 0)
    contains("and says so", out.stdout, "released www")
    task = {t["id"]: t for t in json.loads(path_of(state, "2026-08-28").read_text())["tasks"]}
    check("the task is open again", task["www"]["status"], "open")
    check("the dispatch stamp comes off", "started" in task["www"], False)
    check("so does the owner", "session" in task["www"], False)
    check("and the moment it was handed back is kept",
          "released" in task["www"], True)
    contains("a released task is offered again", run(state, "next").stdout, "www")

    refused = run(state, "release", "www")
    check("releasing an open task refuses", refused.returncode, 1)
    contains("and says what it is instead", refused.stderr, "not in flight")


def case_an_ended_owners_marker_is_repaired(state):
    run(state, "new", stdin=json.dumps(PLAN))
    run(state, "start", "www", extra={"CLAUDE_CODE_SESSION_ID": "gone"})
    out = run(state, "guard-stop", stdin=json.dumps({"session_id": "here"}),
              extra={"CLAUDE_CODE_SESSION_ID": "here"})
    check("the session is stopped over it", out.returncode, 2)
    contains("and told what was repaired", out.stderr, "Released www")
    task = {t["id"]: t for t in json.loads(path_of(state, "2026-08-28").read_text())["tasks"]}
    check("the marker is cleared without being asked", task["www"]["status"], "open")


def case_your_own_marker_stops_the_session(state):
    run(state, "new", stdin=json.dumps(PLAN))
    run(state, "start", "www", extra={"CLAUDE_CODE_SESSION_ID": "here"})
    out = run(state, "guard-stop", stdin=json.dumps({"session_id": "here"}),
              extra={"CLAUDE_CODE_SESSION_ID": "here"})
    check("a marker of this session's own refuses the end", out.returncode, 2)
    contains("naming the task", out.stderr, "www")
    contains("and both ways out", out.stderr, "day-plan.py release www")
    task = {t["id"]: t for t in json.loads(path_of(state, "2026-08-28").read_text())["tasks"]}
    check("nothing is guessed on its behalf", task["www"]["status"], "running")


def case_page_follows_the_ledger(state):
    seed_page(state)
    page = state / "day-plans" / "2026-08-28.html"
    check("page moves beside the ledger", page.is_file(), True)

    run(state, "start", "www")
    run(state, "done", "gbp")
    text = page.read_text()
    contains("running task marked", text, 'data-id="www" data-status="running"')
    contains("done task marked", text, 'data-id="gbp" data-status="done"')
    contains("untouched task marked open", text, 'data-id="gsc" data-status="open"')
    contains("closed count rewritten", text, '<span id="done">1</span>')
    contains("status style injected once", text, "day-plan:status")
    check("style injected exactly once", text.count("day-plan:status"), 2)

    run(state, "skip", "verify", "--note", "not today")
    text = page.read_text()
    contains("skip reaches the page", text, 'data-id="verify" data-status="skipped"')
    contains("skips count as closed", text, '<span id="done">2</span>')


def case_the_page_is_named_for_its_day(state):
    seed_page(state)
    page = state / "day-plans" / "2026-08-28.html"
    run(state, "start", "www")
    contains("a page with no title gains one",
             page.read_text(), "<title>Aug 28 Day Plan</title>")

    page.write_text(page.read_text().replace(
        "<title>Aug 28 Day Plan</title>", "<title>Found, Posted, Sent</title>"))
    run(state, "done", "gbp")
    text = page.read_text()
    contains("a title written for the subject is replaced",
             text, "<title>Aug 28 Day Plan</title>")
    missing("and the subject name does not survive", text, "Found, Posted, Sent")
    check("exactly one title", text.count("<title>"), 1)


def case_add_grows_a_plan_without_disturbing_it(state):
    run(state, "new", stdin=json.dumps(PLAN))
    run(state, "start", "www")
    run(state, "done", "gbp")

    r = run(state, "add", stdin=json.dumps([
        {"id": "rss", "phase": "Capture", "title": "Ship a feed", "agent": True},
        {"id": "signup", "phase": "Capture", "title": "Signup on the blog",
         "agent": True, "needs": ["rss", "gbp"]},
    ]))
    contains("add reports the new size", r.stdout, "2 added")

    shown = run(state, "show", "--full")
    check("show survives a task in flight", shown.returncode, 0)
    contains("the new task is on the plan", shown.stdout, "Ship a feed")
    contains("a blocker among the new tasks holds", shown.stdout, "rss")
    contains("the closed task stays closed", shown.stdout, "[x] gbp")
    contains("the dispatched task reads as in flight", shown.stdout, "[>] www")
    missing("a dispatched task is still not ready", run(state, "next").stdout, "www")

    dup = run(state, "add", stdin=json.dumps([{"id": "rss", "title": "Again"}]))
    check("a repeated id is refused", dup.returncode != 0, True)
    contains("and says which", dup.stderr + dup.stdout, "rss")

    bad = run(state, "add", stdin=json.dumps([
        {"id": "orphan", "title": "Waits on nothing real", "needs": ["nope"]}]))
    check("an unknown blocker is refused", bad.returncode != 0, True)
    contains("and names it", bad.stderr + bad.stdout, "nope")

    empty = run(state, "add", stdin="[]")
    check("an empty list is refused", empty.returncode != 0, True)


def case_page_mismatch_refuses(state):
    seed_page(state)
    page = state / "day-plans" / "2026-08-28.html"
    page.write_text(PAGE.replace(
        '<label class="task"><input type="checkbox" data-k="t5">'
        '<div class="task-body"><p class="task-title">Connect the channels</p></div></label>\n',
        ""))
    r = run(state, "done", "gbp")
    check("a page of another plan is refused", r.returncode != 0, True)
    contains("and says why", r.stderr + r.stdout, "not a view of this plan")


def case_unpublished_page_is_caught(state):
    seed_page(state)
    check("freshly published page is true",
          run(state, "page").returncode, 0)

    run(state, "done", "gbp")
    r = run(state, "page")
    check("closing work puts the page behind", r.returncode, 1)
    contains("and names the url", r.stdout, "https://example.invalid/p")

    run(state, "published")
    check("recording the republish clears it", run(state, "page").returncode, 0)

    run(state, "start", "www")
    check("dispatching also puts it behind", run(state, "page").returncode, 1)


def case_one_human_step_at_a_time(state):
    """A person gets a next step, never a backlog.

    Agent work fans out and every ready piece is returned at once. Human work
    is paced, because six things handed over together is a list to triage
    rather than something to go and do.
    """
    plan = {
        "date": "2026-08-28",
        "subject": "pacing",
        "tasks": [
            {"id": "gsc", "title": "Verify Search Console", "human": True},
            {"id": "accounts", "title": "Create the company page", "human": True},
            {"id": "evidence", "title": "Gather the documents", "human": True},
            {"id": "citations", "title": "Claim the listings", "human": True},
            {"id": "www", "title": "Settle the canonical host", "agent": True},
            {"id": "schema", "title": "Fix the schema", "agent": True},
        ],
    }
    run(state, "new", stdin=json.dumps(plan))

    out = run(state, "next")
    contains("first human task shown", out.stdout, "gsc")
    missing("second human task withheld", out.stdout, "accounts")
    missing("third human task withheld", out.stdout, "evidence")
    contains("agent work still fans out", out.stdout, "www")
    contains("every agent task, not just one", out.stdout, "schema")
    contains("and the run is told some are held", out.stderr, "held back")

    everything = run(state, "next", "--all")
    contains("--all shows the second", everything.stdout, "accounts")
    contains("--all shows the third", everything.stdout, "evidence")

    run(state, "done", "gsc")
    after = run(state, "next")
    contains("closing one surfaces the next", after.stdout, "accounts")
    missing("and still only that one", after.stdout, "evidence")

    run(state, "skip", "accounts", "--note", "not doing it")
    contains("skipping also surfaces the next", run(state, "next").stdout, "evidence")

    run(state, "start", "evidence")
    held_out = run(state, "next")
    missing("a started step is not offered again", held_out.stdout, "evidence")
    missing("and holds the one behind it", held_out.stdout, "citations")
    contains("with the reason reported", held_out.stderr, "held back")

    run(state, "done", "evidence")
    contains("finishing it releases the next", run(state, "next").stdout, "citations")


def case_defer_moves_the_chain(state):
    """Deferring keeps the work and only moves when it is offered.

    Skipping records a decision not to do something and frees its dependents.
    Deferring records neither, so the blocking has to survive the move.
    """
    plan = {
        "date": "2026-08-28",
        "subject": "ordering",
        "tasks": [
            {"id": "evidence", "title": "Gather the documents", "human": True},
            {"id": "gbp", "title": "Create the profile", "human": True,
             "needs": ["evidence"]},
            {"id": "verify", "title": "Submit verification", "human": True,
             "needs": ["gbp"]},
            {"id": "accounts", "title": "Create the company page", "human": True},
            {"id": "www", "title": "Settle the canonical host", "agent": True},
        ],
    }
    run(state, "new", stdin=json.dumps(plan))
    contains("the chain leads before deferring", run(state, "next").stdout, "evidence")

    out = run(state, "defer", "evidence")
    contains("what waits on it moves too", out.stdout, "gbp")
    contains("transitively", out.stdout, "verify")

    after = run(state, "next")
    contains("the next standing task is offered", after.stdout, "accounts")
    missing("and the deferred one is not", after.stdout, "evidence")
    contains("agent work is untouched", after.stdout, "www")

    order = {t["id"]: t["order"] for t in json.loads(
        (state / "day-plans" / "2026-08-28.json").read_text())["tasks"]}
    check("deferred work sits last", order["evidence"] > order["accounts"], True)
    check("and its chain stays in sequence", order["gbp"] < order["verify"], True)

    # Deferring is not skipping: the work is still open and still blocking.
    plan_now = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    states = {t["id"]: t["status"] for t in plan_now["tasks"]}
    check("deferred work stays open", states["evidence"], "open")
    check("and so does what waits on it", states["gbp"], "open")
    missing("which is still not ready", run(state, "next").stdout, "gbp")

    # Deferring holds for the day. Once everything else is deferred too, the
    # answer is that the day is out of work, not the first thing put off.
    run(state, "done", "accounts")
    run(state, "done", "www")
    after = run(state, "next")
    missing("a deferred task is not re-offered", after.stdout, "evidence")
    contains("the day reports itself out of work", after.stdout, "put off today")
    contains("--all still shows it", run(state, "next", "--all").stdout, "evidence")

    # Deferral and its lifting belong to the day the tasks are still on,
    # so they are settled here, before the carry takes them off it.
    # A deferral outlives the reading it was made on, so lifting one is its
    # own act and leaves the ordering it was given alone.
    run(state, "resume", "gbp", "--date", "2026-08-28")
    plan_after = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    tasks_after = {t["id"]: t for t in plan_after["tasks"]}
    check("the deferral lifts", "deferred" in tasks_after["gbp"], False)
    check("the ordering it was given stays",
          tasks_after["gbp"]["order"] > tasks_after["accounts"]["order"], True)
    check("its own blocker still holds", tasks_after["gbp"]["needs"], ["evidence"])
    check("and a sibling stays deferred", "deferred" in tasks_after["verify"], True)

    # Tomorrow is a fresh day: carrying clears the deferral with the status,
    # and takes the work off today rather than leaving a copy of it.
    run(state, "carry", "--to", "2026-08-29")
    carried = json.loads(
        (state / "day-plans" / "2026-08-29.json").read_text())
    evidence = {t["id"]: t for t in carried["tasks"]}["evidence"]
    check("carrying clears the deferral", "deferred" in evidence, False)
    contains("so it leads again tomorrow",
             run(state, "next", "--date", "2026-08-29").stdout, "evidence")
    left = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    check("and yesterday keeps only what it closed",
          sorted(t["id"] for t in left["tasks"]), ["accounts", "www"])


    check("resuming an unknown id is refused",
          run(state, "resume", "nosuch", "--date", "2026-08-28").returncode != 0, True)

    r = run(state, "defer", "nosuch")
    check("an unknown id is refused", r.returncode != 0, True)


def case_amend_rewords_without_losing_structure(state):
    """Scope changes reach the prose and leave the plan's shape alone."""
    run(state, "new", stdin=json.dumps(PLAN))
    run(state, "start", "www")

    out = run(state, "amend", "www", "--title", "Settle on www and drop the apex",
              "--detail", "Canonical, og:url, sitemap, robots.")
    check("amend succeeds", out.returncode, 0)

    plan = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    task = {t["id"]: t for t in plan["tasks"]}["www"]
    check("the title moves", task["title"], "Settle on www and drop the apex")
    check("the detail moves", task["detail"], "Canonical, og:url, sitemap, robots.")
    check("status is untouched", task["status"], "running")
    check("order is untouched", task["order"], 3)

    gsc = {t["id"]: t for t in plan["tasks"]}["gsc"]
    check("blocking is untouched", gsc["needs"], ["www"])

    run(state, "amend", "gsc", "--why", "Matches the canonical decision.")
    plan = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    gsc = {t["id"]: t for t in plan["tasks"]}["gsc"]
    check("why moves on its own", gsc["why"], "Matches the canonical decision.")
    check("and the title is left alone", gsc["title"], "Verify Search Console")

    check("an unknown id is refused",
          run(state, "amend", "nosuch", "--title", "x").returncode != 0, True)
    check("amending nothing is refused",
          run(state, "amend", "www").returncode != 0, True)
    check("a task cannot lose its title",
          run(state, "amend", "www", "--title", "  ").returncode != 0, True)


def case_reorder_does_not_relabel_the_page(state):
    """Statuses follow the task, not the slot it happens to sit in.

    Page order is fixed at generation and plan order is not, so a positional
    match survives every sync until something reorders the plan and then
    stamps every status onto the wrong task while still reporting success.
    """
    seed_page(state)
    page = state / "day-plans" / "2026-08-28.html"

    run(state, "done", "gbp")
    contains("the closed task is marked", page.read_text(),
             'data-id="gbp" data-status="done"')

    run(state, "defer", "gbp")
    text = page.read_text()
    contains("it keeps its own status after the move", text,
             'data-id="gbp" data-status="done"')
    contains("and the task that moved up keeps its own", text,
             'data-id="www" data-status="open"')

    order = {t["id"]: t["order"] for t in json.loads(
        (state / "day-plans" / "2026-08-28.json").read_text())["tasks"]}
    check("the plan really did reorder", order["gbp"] > order["www"], True)

    run(state, "start", "www")
    text = page.read_text()
    contains("later syncs still follow the id", text,
             'data-id="www" data-status="running"')
    contains("and leave the deferred one alone", text,
             'data-id="gbp" data-status="done"')

    # A page naming a task this plan does not have is refused rather than
    # silently mapped onto whatever sits in that slot.
    page.write_text(page.read_text().replace('data-id="verify"', 'data-id="ghost"'))
    r = run(state, "done", "social")
    check("a page of another plan is refused", r.returncode != 0, True)
    contains("and names what it could not place", r.stderr + r.stdout, "ghost")


def case_needs_reopens_work_a_stale_blocker_held(state):
    """A blocker that stops gating is removable, and the work becomes ready.

    Nothing about a stale blocker looks different from a real one, so a task
    left waiting on it is reported as blocked forever.
    """
    run(state, "new", stdin=json.dumps(PLAN))
    missing("blocked while it waits", run(state, "next").stdout, "social")

    out = run(state, "needs", "social", "gbp")
    check("resetting succeeds", out.returncode, 0)
    contains("and says what moved", out.stdout, "was verify")
    missing("still blocked by the new one", run(state, "next").stdout, "social")

    run(state, "needs", "social", "--none")
    contains("clearing it makes the work ready", run(state, "next").stdout, "social")

    plan = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    social = {t["id"]: t for t in plan["tasks"]}["social"]
    check("the blockers are gone", social["needs"], [])
    check("and nothing else moved", social["status"], "open")

    check("an unknown task is refused",
          run(state, "needs", "nosuch", "gbp").returncode != 0, True)
    check("an unknown blocker is refused",
          run(state, "needs", "social", "ghost").returncode != 0, True)
    check("a task cannot wait on itself",
          run(state, "needs", "social", "social").returncode != 0, True)

    # A cycle is a plan that can never start, and easier to write than to spot.
    run(state, "needs", "social", "gsc")
    cyc = run(state, "needs", "www", "social")
    check("a cycle is refused", cyc.returncode != 0, True)
    contains("and drawn out", cyc.stderr + cyc.stdout, "cycle")

    plan = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    www = {t["id"]: t for t in plan["tasks"]}["www"]
    check("the refused edge did not land", www["needs"], [])


# The ledger is held on more than one machine, so what settles a conflict has to
# survive the trip. A file's modification time does not -- a clone stamps every
# file at once -- so the plan carries its own, and the carrier that moves it is
# reached from the writes and the reads rather than from a step someone runs.

CARRIER = """#!/usr/bin/env python3
import os
import pathlib
import sys

here = pathlib.Path(__file__).parent
with (here / "carrier.log").open("a") as fh:
    fh.write(" ".join(sys.argv[1:]) + "\\n")
if os.environ.get("INTELLIGENCE_DAYPLAN_LOCK_HELD"):
    (here / "took-the-hold-with-it").write_text("1\\n")
"""


# The same stand-in, turned away at the mirror. Being unreachable is an
# ordinary state and a read has to answer through it.
BROKEN_CARRIER = CARRIER + """
sys.stderr.write("fatal: could not read from remote repository\\n")
sys.exit(1)
"""

# The stand-in that lands what it was given, which is a push leaving its record
# behind. The record is the whole of what a session end reads, so a stub that
# carries the plans without writing one is a trip that never happened as far as
# the gate can tell -- which is the other stub, and the other case.
SETTLING_CARRIER = CARRIER + """
import json

root = pathlib.Path(os.environ["INTELLIGENCE_STATE_DIR"])
landed = {}
for path in sorted((root / "day-plans").glob("*.json")):
    body = json.loads(path.read_text())
    landed[body["date"]] = {
        "state": "shared",
        "stamp": body.get("updated") or body.get("created"),
        "at": "2026-08-28T00:00:00+00:00",
    }
(root / ".day-plan-shared.json").write_text(json.dumps({"plans": landed}))
"""


# A scheduled push leaves two traces and they settle at different moments. The
# mark is the run's own write, made before the carrier is spawned, so it is
# already there when the command returns. The carrier's record is written by a
# detached process the run does not wait for, so it lands some time after. Which
# trace a case reads is what decides whether it can be raced: an assertion that a
# push was scheduled waits for the record, and one that no push was scheduled
# reads the mark, because a record that has not arrived yet and one that is never
# coming are the same empty file.

SHARE_MARK = ".day-plan-share"

# What a spawned carrier is given to record itself. The spawn takes tens of
# milliseconds whether the machine is idle or oversubscribed, so this is not a
# tuned figure: it is far enough above that for running out to mean the carrier
# is not coming, and it is only ever waited out by a run that fails either way.
CARRIER_DEADLINE = 30.0


def stub_carrier(state, body=CARRIER):
    """A stand-in for the carrier that records what it was asked to do."""
    tool = state / "carrier" / "pass-state.py"
    tool.parent.mkdir(parents=True, exist_ok=True)
    tool.write_text(body)
    return tool


def carrier_calls(state):
    """The carrier's record as it stands, with no wait for one to arrive."""
    log = state / "carrier" / "carrier.log"
    return log.read_text().split() if log.is_file() else []


def carrier_log(state, expected):
    """What the carrier was asked to do, once it has been asked `expected` times.

    The wait is on the record itself rather than on a span of time, and a whole
    line is what counts as a call: the file appears when the carrier opens it and
    holds nothing until the write is flushed, so a read taken in between answers
    empty and reads exactly like a carrier that was never spawned. A deadline
    that runs out is reported as a deadline, which is what keeps a slow machine
    from being read as a tool that stopped scheduling pushes.
    """
    log = state / "carrier" / "carrier.log"
    deadline = time.monotonic() + CARRIER_DEADLINE
    while True:
        text = log.read_text() if log.is_file() else ""
        entries = text.splitlines()
        if len(entries) >= expected and (not text or text.endswith("\n")):
            return entries
        if time.monotonic() > deadline:
            FAILURES.append(
                f"the carrier recorded {len(entries)} of {expected} calls "
                f"within {CARRIER_DEADLINE:g}s")
            return entries
        time.sleep(0.01)


def share_stamp(state, root=None):
    """When the push was scheduled, or None where none was.

    A case reads the mark rather than the carrier's record because the mark is
    the run's own write, made before the carrier is spawned, and so has settled
    by the time the command returns. That is what makes it the trace an absence
    can be read from at all. A missing mark answers None rather than raising,
    so a case that expected one reports a failure instead of ending the run.
    """
    try:
        return (Path(root or state) / SHARE_MARK).stat().st_mtime
    except OSError:
        return None


def share_scheduled(state, root=None):
    """Whether the run scheduled a push."""
    return share_stamp(state, root) is not None


def asked(state, verb):
    """How many times the carrier has been asked for one verb."""
    return carrier_calls(state).count(verb)


def case_every_write_is_stamped(state):
    """A plan records when it was last written, inside the plan."""
    run(state, "new", stdin=json.dumps(PLAN))
    path = state / "day-plans" / "2026-08-28.json"
    first = json.loads(path.read_text()).get("updated")
    check("a new plan carries a stamp", bool(first), True)

    # A clone hands every file the same arrival time, so the stamp has to be
    # what moves rather than the file.
    os.utime(path, (0, 0))
    time.sleep(1.1)
    run(state, "done", "www")
    second = json.loads(path.read_text()).get("updated")
    check("closing a task moves the stamp", second > first, True)
    check("the stamp is not the file's clock", int(path.stat().st_mtime) > 0, True)


def case_empty_state_pulls_once(state):
    """A machine holding no plans asks the carrier before reporting none.

    The carrier leaves the plans alone on a machine holding none, which is what
    keeps a run with no plan to work out of them. This is the caller whose whole
    subject is the plans, so it is the one that asks for them by name.
    """
    tool = stub_carrier(state)
    out = run(state, "current", carrier=tool)
    check("no plan is still no plan", out.returncode != 0, True)
    check("the carrier was asked", carrier_log(state, 1), ["pull --plans"])

    run(state, "list", carrier=tool)
    check("and asked once", carrier_log(state, 1), ["pull --plans"])


# The push a write schedules is made by a separate process that resolves the
# mirror from its own configuration, so redirecting the state root moves where a
# plan is written and not where it is published. `share_soon` reads the root and
# the remote together to tell the two apart: a root pointed somewhere other than
# this machine's own is a throwaway and publishes nothing, unless the remote is
# redirected beside it, which puts the whole trip inside the fixture. So a case
# that wants its push measured has to say which of the two it is.


def own_root(state):
    """Where the tool's own root lands under a fixture HOME, computed its way."""
    if os.environ.get("CLAUDE_CODE_REMOTE"):
        return state / ".pass-state"
    return state / ".intelligence" / "state"


def round_trip(state):
    """A mirror of the run's own, which is what keeps a redirected root's push.

    The carrier reads the remote from the environment, so naming a bare
    repository inside the fixture leaves the trip nowhere to go but there.
    """
    return {"INTELLIGENCE_PASS_STATE_REMOTE": str(state / "mirror.git")}


def case_a_write_schedules_the_share(state):
    """Writing the ledger schedules the push that carries it off the machine.

    The fixture redirects the state root, which stands the push down on its own,
    so the run names a mirror of its own to leave a push there to measure.
    """
    tool = stub_carrier(state)
    mine = round_trip(state)
    run(state, "new", stdin=json.dumps(PLAN), carrier=tool, extra=mine)
    check("the write scheduled a share", carrier_log(state, 1), ["share-soon"])
    check("and left the mark that says so", share_scheduled(state), True)

    # A burst of closures is one push, not one each: the mark the scheduler
    # leaves is what the next write reads, and a write that finds it there
    # returns before spawning anything, so the mark stops moving. Reading that
    # is what makes the count below an assertion rather than a head start.
    stamped = share_stamp(state)
    run(state, "done", "www", carrier=tool, extra=mine)
    run(state, "done", "gbp", carrier=tool, extra=mine)
    check("a burst schedules one", carrier_log(state, 1), ["share-soon"])
    check("and does not rewrite the mark", share_stamp(state), stamped)

    # The write holds the plans while it runs and the carrier outlives it, so
    # the carrier has to reach them with nothing telling it they are held.
    check("the hold does not travel to the carrier",
          (state / "carrier" / "took-the-hold-with-it").exists(), False)


def case_a_throwaway_root_never_publishes(state):
    """A plan written under a borrowed root is not published as that day's plan.

    INTELLIGENCE_STATE_DIR moves where a plan is written and nothing else. The
    carrier the write spawns inherits the redirected root and still resolves the
    shared mirror on its own, so a fixture of a few tasks written under a
    throwaway directory arrives there as that day's plan and displaces the plan
    already on it. A root that is not this machine's own schedules nothing.
    """
    tool = stub_carrier(state)
    run(state, "new", stdin=json.dumps(PLAN), carrier=tool)
    check("a throwaway root schedules no push", share_scheduled(state), False)
    check("and reaches no carrier", carrier_calls(state), [])

    # Every verb that moves a task writes the plan back, so each reaches the
    # same gate that creating one does.
    run(state, "done", "www", carrier=tool)
    check("nor does closing work under one", share_scheduled(state), False)
    check("nor reaches one then", carrier_calls(state), [])


def case_a_redirected_remote_still_publishes(state):
    """A run that redirects the mirror as well keeps its push.

    A root redirected on its own borrows this machine's mirror. A root
    redirected beside a remote reaches a repository of its own and no further,
    which is the round trip the carrier's own cases are built on, so the gate
    has to leave it its push.
    """
    tool = stub_carrier(state)
    run(state, "new", stdin=json.dumps(PLAN), carrier=tool, extra=round_trip(state))
    check("naming a mirror of its own keeps the push",
          carrier_log(state, 1), ["share-soon"])
    check("and the mark records it", share_scheduled(state), True)


def case_the_machines_own_root_publishes(state):
    """Naming this machine's own root is not a redirect, and still publishes.

    The gate compares where the root resolves against where it would resolve
    unset, so a run that spells out the default is left alone. The fixture's
    HOME is what makes that path a temporary directory, and a gate reading the
    variable rather than the path it lands on fails this case rather than
    reaching the live tree.
    """
    own = own_root(state)
    tool = stub_carrier(state)
    run(state, "new", stdin=json.dumps(PLAN), carrier=tool,
        extra={"INTELLIGENCE_STATE_DIR": str(own)})
    check("the plan is written under the fixture's own root",
          (own / "day-plans" / "2026-08-28.json").is_file(), True)
    check("and spelling out the default schedules the share",
          carrier_log(state, 1), ["share-soon"])
    check("with the mark under that root", share_scheduled(state, own), True)


# A read answers from whatever the last session on any machine left, and a
# session cannot end holding what no other machine can reach. Both are the same
# failure at two ends of one trip, and the network is the part a case cannot
# have, so the carrier here is a stand-in that records what it was asked for
# and the record it would have written is placed by hand.

SHARED_RECORD = ".day-plan-shared.json"


def record(state, entries):
    """The carrier's record of what each plan settled, as a push leaves it."""
    (state / SHARED_RECORD).write_text(json.dumps({"plans": entries}, indent=2))


def shared(state, day):
    """Record a plan as having reached the mirror at the stamp it now holds."""
    plan = json.loads((state / "day-plans" / f"{day}.json").read_text())
    record(state, {day: {"state": "shared", "stamp": plan["updated"]}})


def stop(state, carrier):
    return run(state, "guard-stop", stdin="{}", carrier=carrier)


def case_unshared_state_holds_the_session(state):
    """A session cannot end holding plan state the mirror does not have.

    The push a write schedules waits out the burst behind it, so a session that
    ends first takes the process that was going to make it -- always, in a
    container, where the session ending is the machine going away. The plan is
    then worked tomorrow as it stood this morning.
    """
    tool = stub_carrier(state)
    run(state, "new", stdin=json.dumps(PLAN), carrier=tool)

    r = stop(state, tool)
    check("a plan that never travelled holds the stop", r.returncode, 2)
    contains("the plan is named", r.stderr, "2026-08-28")
    contains("and so is what is wrong with it", r.stderr, "never pushed")
    contains("and the command that settles it", r.stderr, "pass-state.py push")

    shared(state, "2026-08-28")
    check("a plan the mirror holds lets the session end",
          stop(state, tool).returncode, 0)

    run(state, "done", "www", carrier=tool)
    r = stop(state, tool)
    check("work closed since that push holds it again", r.returncode, 2)
    contains("and is named as such", r.stderr, "written since")

    # A rejection is not a push. Reading the last success as still standing is
    # how a machine's own edits become the older side.
    record(state, {"2026-08-28": {"state": "refused",
                                  "reason": "the mirror moved first"}})
    r = stop(state, tool)
    check("a refused push does not count as one", r.returncode, 2)
    contains("the refusal is named as one", r.stderr, "refused the last push")
    contains("with what the mirror said", r.stderr, "moved first")

    record(state, {"2026-08-28": {
        "state": "held", "reason": "a database url with a password in it"}})
    r = stop(state, tool)
    check("a plan held off the mirror holds it too", r.returncode, 2)
    contains("with what it carries named", r.stderr, "password in it")

    # A second pass is the session already being held once; holding it again
    # would be a loop rather than a gate.
    shared(state, "2026-08-28")
    run(state, "done", "gbp", carrier=tool)
    again = run(state, "guard-stop", stdin=json.dumps({"stop_hook_active": True}),
                carrier=tool)
    check("the second pass lets it rest", again.returncode, 0)

    # A plan written before writes were stamped carries only its creation, and
    # a gate nothing can open is worse than no gate.
    path = state / "day-plans" / "2026-08-28.json"
    old = json.loads(path.read_text())
    created = old.pop("updated")
    old["created"] = created
    path.write_text(json.dumps(old, indent=2))
    record(state, {"2026-08-28": {"state": "shared", "stamp": created}})
    check("an unstamped plan is read by its creation",
          stop(state, tool).returncode, 0)


def case_the_gate_makes_the_trip_before_it_refuses(state):
    """A session end carries the plans itself rather than reporting them behind.

    The push a write schedules waits out the burst behind it, so the gate meets
    plans that are behind the mirror for no reason but the clock. Making the
    trip is what separates that from a mirror that will not take them, and it
    is the difference between a session that ends and a person handed a command
    whose whole effect is to start the same push a moment early.
    """
    tool = stub_carrier(state, SETTLING_CARRIER)
    run(state, "new", stdin=json.dumps(PLAN), carrier=tool)

    r = stop(state, tool)
    check("a plan the gate could carry lets the session end", r.returncode, 0)
    contains("the gate made the trip", " ".join(carrier_calls(state)), "push --plans")
    missing("and says nothing about the mirror", r.stderr, "reached the mirror")


def case_a_trip_that_settles_nothing_still_holds_the_session(state):
    """A push that lands no record leaves the refusal where it was.

    A carrier that returns without recording a plan has settled nothing, and a
    gate reading the return rather than the record would let every unreachable
    mirror through as a success.
    """
    tool = stub_carrier(state)
    run(state, "new", stdin=json.dumps(PLAN), carrier=tool)

    r = stop(state, tool)
    check("the session is held", r.returncode, 2)
    contains("the trip is named as made", r.stderr, "settled none of these")
    contains("with the plan that is behind", r.stderr, "2026-08-28")


def case_the_page_and_the_ledger_are_reported_together(state):
    """Both halves of a session end are answered in one pass."""
    tool = stub_carrier(state)
    seed_page(state)
    run(state, "done", "gbp", carrier=tool)
    r = stop(state, tool)
    check("either one alone holds the stop", r.returncode, 2)
    contains("the ledger half is reported", r.stderr, "has not reached the mirror")
    contains("and the page half with it", r.stderr, "behind its ledger")


def case_a_read_fetches_when_it_could_be_stale(state):
    """The reads a run acts on fetch first, once per window.

    A machine holding a stale plan is the dangerous copy, not one holding none:
    another session closed three tasks ten minutes ago, and a run here reports
    them as outstanding and republishes a page that contradicts the mirror.
    """
    tool = stub_carrier(state)
    run(state, "new", stdin=json.dumps(PLAN), carrier=tool)
    check("a write does not fetch", asked(state, "pull"), 0)

    run(state, "next", carrier=tool)
    check("the first read does", asked(state, "pull"), 1)

    run(state, "next", carrier=tool)
    run(state, "show", carrier=tool)
    run(state, "current", carrier=tool)
    check("and the reads inside the window do not", asked(state, "pull"), 1)

    # The window is a file rather than a variable, so separate processes in one
    # session share it; ageing the mark is what a later read sees.
    marker = state / ".day-plan-pulled"
    old = time.time() - 600
    os.utime(marker, (old, old))
    run(state, "next", carrier=tool)
    check("a read past the window fetches again", asked(state, "pull"), 2)


def case_a_read_survives_an_unreachable_mirror(state):
    """Offline is ordinary, so a fetch that fails reports and stands aside."""
    tool = stub_carrier(state, BROKEN_CARRIER)
    run(state, "new", stdin=json.dumps(PLAN), carrier=tool)

    r = run(state, "next", carrier=tool)
    check("the read still answers", r.returncode, 0)
    contains("from the copy on this machine", r.stdout, "www")
    contains("and says the fetch did not happen", r.stderr, "could not be fetched")

    # A mirror that is down stays down, and paying a failed round trip per
    # command is the cost the window exists to bound.
    before = asked(state, "pull")
    run(state, "next", carrier=tool)
    run(state, "show", carrier=tool)
    check("a failed fetch is not retried per read", asked(state, "pull"), before)


def case_closures_at_the_same_moment_all_survive(state):
    """Two sessions closing different tasks on one plan both keep their work.

    Every verb that moves a task loads the plan, changes one task, and writes
    the whole plan back. Two of those overlapping means the second load happens
    before the first write, so the second write carries the first session's task
    back to open -- and nothing about the result says it happened.
    """
    run(state, "new", stdin=json.dumps(PLAN))
    env = dict(os.environ)
    env["INTELLIGENCE_STATE_DIR"] = str(state)
    env["HOME"] = str(state)
    env["INTELLIGENCE_DAYPLAN_NO_SYNC"] = "1"
    env.pop("INTELLIGENCE_DAYPLAN_LOCK_HELD", None)
    ids = ["gbp", "verify", "www", "gsc", "social"]
    running = [subprocess.Popen([sys.executable, str(TARGET), "done", tid],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, env=env)
               for tid in ids]
    for proc in running:
        proc.wait()

    plan = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    check("every closure is on the plan",
          {t["id"]: t["status"] for t in plan["tasks"]},
          {tid: "done" for tid in ids})
    check("and the plan is still one document", len(plan["tasks"]), len(ids))


def case_the_override_stands_it_all_down(state):
    """INTELLIGENCE_DAYPLAN_NO_SYNC=1 takes the whole carriage out of the way."""
    tool = stub_carrier(state)
    off = {"INTELLIGENCE_DAYPLAN_NO_SYNC": "1"}
    run(state, "new", stdin=json.dumps(PLAN), carrier=tool, extra=off)
    check("a write schedules nothing", share_scheduled(state), False)
    check("and reaches no carrier", carrier_calls(state), [])

    run(state, "next", carrier=tool, extra=off)
    run(state, "current", carrier=tool, extra=off)
    check("a read fetches nothing", asked(state, "pull"), 0)

    check("and a session with unshared state can end",
          run(state, "guard-stop", stdin="{}", carrier=tool, extra=off).returncode,
          0)


def case_a_parked_decision_is_refused(state):
    """A plan takes work. A question the user has not answered is not work.

    The failure this pins costs a whole day: a task nobody can execute reads
    as planned, sits through the run because no agent may make the call and
    no human is being given a step, and carries forward untouched. Refusing
    it at the write is what sends the question back to be asked.
    """
    parked = dict(PLAN, date="2026-09-10", tasks=[
        {"id": "domain", "phase": "Mail",
         "title": "Decide whether outreach links move off the domain"},
    ])
    r = run(state, "new", stdin=json.dumps(parked))
    check("a decision verb is refused", r.returncode, 1)
    contains("the refusal names the ask", r.stderr, "AskUserQuestion")
    check("nothing was written", (state / "day-plans" / "2026-09-10.json").exists(), False)

    # The phase is the stronger tell: one parked decision gets a title anyone
    # would read past, and a pile of them gets a heading.
    piled = dict(PLAN, date="2026-09-10", tasks=[
        {"id": "guides", "phase": "Say what is true",
         "title": "Reconcile the guides with the console"},
    ])
    r = run(state, "new", stdin=json.dumps(piled))
    check("a questions phase is refused", r.returncode, 1)
    contains("the refusal names the phase", r.stderr, "Say what is true")

    # Work reading like work goes in, including the investigation verbs that
    # would make the guard useless if it claimed them.
    fine = dict(PLAN, date="2026-09-10", tasks=[
        {"id": "domain", "phase": "Mail", "title": "Move outreach links to the sending domain"},
        {"id": "why", "phase": "Mail", "title": "Determine why the last send bounced"},
    ])
    check("work is not refused", run(state, "new", stdin=json.dumps(fine)).returncode, 0)

    # `add` and `amend` are the same door, and a reword is how work turns back
    # into a question after the plan was agreed.
    r = run(state, "add", "--date", "2026-09-10",
            stdin=json.dumps([{"id": "pick", "phase": "Mail", "title": "Choose the footer address"}]))
    check("add refuses one too", r.returncode, 1)
    r = run(state, "amend", "domain", "--date", "2026-09-10",
            "--title", "Decide whether the links move")
    check("amend refuses a reword into a question", r.returncode, 1)

    # A misread has a way through, and it is the only way through.
    r = run(state, "add", "--date", "2026-09-10",
            stdin=json.dumps([{"id": "pick", "phase": "Mail", "title": "Choose the footer address"}]),
            extra={"INTELLIGENCE_ALLOW_PLAN_DECISION": "1"})
    check("the override lets one through", r.returncode, 0)


def case_a_parked_decision_cannot_be_carried(state):
    """Carrying is how a parked decision survives the day that could not do it."""
    run(state, "new", stdin=json.dumps(PLAN))
    run(state, "add", stdin=json.dumps([
        {"id": "domain", "phase": "Mail", "title": "Move outreach links to the sending domain"},
    ]))
    # Written before the guard existed, which is the state every plan on file
    # is in the day it lands.
    path = state / "day-plans" / "2026-08-28.json"
    plan = json.loads(path.read_text())
    for t in plan["tasks"]:
        if t["id"] == "domain":
            t["title"] = "Decide whether outreach links move off the domain"
    path.write_text(json.dumps(plan))

    r = run(state, "carry", "2026-08-28")
    check("carry refuses to move it forward", r.returncode, 1)
    contains("carry names the ask too", r.stderr, "AskUserQuestion")


def case_tomorrows_plan_does_not_take_over_today(state):
    """Writing the next day's plan must not move the run off this one.

    Work agreed for a later day gets written down the moment it is agreed,
    which is nearly always the day before. The newest plan holding open work
    is the right answer only among the days that have actually arrived --
    without that, the act of planning ahead hands the run a plan for a day
    nobody is on yet.
    """
    from datetime import date, timedelta
    today = date.today()
    run(state, "new", stdin=json.dumps(dict(
        PLAN, date=today.isoformat(),
        tasks=[{"id": "now", "phase": "Today", "title": "The work of today"}])))
    run(state, "new", stdin=json.dumps(dict(
        PLAN, date=(today + timedelta(days=2)).isoformat(),
        tasks=[{"id": "later", "phase": "Later", "title": "The work of a later day"}])))

    check("today is what a run works", run(state, "current").stdout.strip(), today.isoformat())
    contains("and it is today's tasks that are ready", run(state, "next").stdout, "now")

    # The later plan is not lost, only not current -- it answers by name.
    contains("the later plan is still readable", 
             run(state, "show", (today + timedelta(days=2)).isoformat()).stdout, "later")

    # Once today's work closes, the run does not skip ahead to a day that has
    # still not arrived.
    run(state, "done", "now")
    check("a finished today does not reach forward",
          run(state, "current").stdout.strip(), today.isoformat())


def case_a_move_leaves_nothing_behind(state):
    """Work belonging to another day leaves this one entirely.

    Closing it here instead -- skipped, with a reason naming the other day --
    keeps it in the ledger and keeps its card on the page, and a plan showing
    another day's work has to be filtered by whoever reads it. So the move is
    a move, and the skip that reads like one is refused.
    """
    run(state, "new", stdin=json.dumps(PLAN))

    r = run(state, "skip", "social", "--note", "moved to the 2026-09-01 plan")
    check("a skip naming another day is refused", r.returncode, 1)
    contains("and it names the verb that does it", r.stderr, "move")
    check("so the task is untouched", 
          json.loads((state / "day-plans" / "2026-08-28.json").read_text())["tasks"][-1]["status"],
          "open")

    # `social` waits on `verify`, which is staying and still open, so the move
    # would land work on a day it cannot run. That is refused rather than
    # rewritten -- which way it should resolve is not the tool's call.
    r = run(state, "move", "social", "--to", "2026-09-05")
    check("a move that breaks the ordering is refused", r.returncode, 1)
    contains("and says what is in the way", r.stdout + r.stderr, "verify")

    run(state, "done", "verify")
    check("with the blocker closed it goes", 
          run(state, "move", "social", "--to", "2026-09-05").returncode, 0)

    here = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    check("gone from the source", "social" in {t["id"] for t in here["tasks"]}, False)
    check("and the source says where it went",
          [m["to"] for m in here["moved"] if m["id"] == "social"], ["2026-09-05"])
    there = json.loads((state / "day-plans" / "2026-09-05.json").read_text())
    check("landed on the target", [t["id"] for t in there["tasks"]], ["social"])
    check("open on arrival", there["tasks"][0]["status"], "open")
    check("without a blocker that did not travel", there["tasks"][0]["needs"], [])

    # A task cannot be in two plans at once, which is what a repeat would do.
    check("and it cannot be moved twice",
          run(state, "move", "social", "--to", "2026-09-05").returncode, 1)


def case_a_move_takes_the_card_off_the_page(state):
    """The page is prose the ledger only stamps, so a move has to cut it out.

    `sync_page` refuses a page whose card count no longer matches the ledger,
    so a card left behind does not read as a stale line -- it jams every later
    write to the plan.
    """
    run(state, "new", stdin=json.dumps(PLAN))
    page = state / "day-plans" / "2026-08-28.html"
    page.write_text(
        "<title>x</title>\n<div>\n"
        + "\n".join(
            '  <section class="phase">\n'
            '    <div class="phase-head"><h2>%s</h2>'
            '<span class="phase-count">1 task</span></div>\n'
            '    <label class="task" data-id="%s"><span>%s</span></label>\n'
            '  </section>' % (t["phase"], t["id"], t["title"])
            for t in PLAN["tasks"]
        )
        + '\n<span id="done">0</span><span> / 5 </span>closed\n</div>\n'
    )
    plan = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    plan["html"] = str(page)
    (state / "day-plans" / "2026-08-28.json").write_text(json.dumps(plan))

    run(state, "done", "verify")
    check("the move goes through", run(state, "move", "social", "--to", "2026-09-05").returncode, 0)

    text = page.read_text()
    missing("the card is gone", text, 'data-id="social"')
    missing("and its empty section with it", text, "<h2>Social</h2>")
    contains("the rest of the plan is untouched", text, 'data-id="gbp"')
    contains("and the tally counts what is left", text, "/ 4 ")

    # The proof it is really gone: a page still carrying it would refuse here.
    check("the page and the ledger still agree", run(state, "sync").returncode, 0)


def case_the_run_sheet_opens_every_page(state):
    """The page has to answer "what am I doing today" before it says anything else.

    A page written by hand opens on whatever its author reached for, and the
    answer ends up under the prose or spread across sections. So the ledger
    writes the answer itself and stamps it in on every sync, which is the only
    version of this that a page cannot be published without.
    """
    seed_page(state)
    page = state / "day-plans" / "2026-08-28.html"
    text = page.read_text()

    contains("the sheet lands on a page with no place for it", text,
             "<!-- day-plan:runsheet -->")
    check("it sits above the work it summarises",
          text.index("<!-- day-plan:runsheet -->") < text.index('<label class="task"'),
          True)
    contains("the agent's half is named in English", text,
             "What the agent is doing")
    contains("and so is yours", text, "What it needs from you")

    # One numbering across the whole day, so the two lists still read as one
    # order rather than two that happen to sit together.
    contains("your first step keeps its place in the day", text,
             '<li value="1" data-id="gbp"')
    contains("the agent's first step keeps its own", text,
             '<li value="3" data-id="www"')
    contains("a blocked step says so in English", text,
             "Cannot start until step 1 is done.")
    contains("and a blocking one says what it frees", text, "Frees step 2.")
    check("the sheet is on the page once", text.count("<!-- day-plan:runsheet -->"), 1)

    run(state, "sync")
    text = page.read_text()
    check("and a second sync replaces it rather than adding one",
          text.count("<!-- day-plan:runsheet -->"), 1)
    check("with one copy of its style", text.count("day-plan:sheet-style"), 1)


def case_the_run_sheet_says_what_the_ledger_says(state):
    """The sheet is the half that gets read, so it cannot lag the ledger."""
    seed_page(state)
    page = state / "day-plans" / "2026-08-28.html"

    run(state, "start", "www")
    run(state, "done", "gbp")
    run(state, "skip", "verify", "--note", "not doing it")
    text = page.read_text()
    contains("a dispatched step reads as in flight", text,
             '<li value="3" data-id="www" data-status="running">'
             '<span class="rs-state">In flight</span>')
    contains("a closed one reads as done", text,
             '<li value="1" data-id="gbp" data-status="done">'
             '<span class="rs-state">Done</span>')
    contains("a dropped one reads as skipped", text,
             '<li value="2" data-id="verify" data-status="skipped">')
    contains("your side counts what is closed", text,
             'What it needs from you<span class="rs-tally">2 of 2 done</span>')

    # A blocker that has closed stops being something the reader waits for.
    missing("a cleared blocker stops being named", text,
            "Cannot start until step 1 is done.")


def case_a_jargon_title_is_refused(state):
    """A title only a reader of the code can follow is the sheet failing.

    The run sheet has the title and nothing else to put in front of a person,
    so a title naming a file, a variable or a function makes the one readable
    part of the page unreadable. The detail is where those belong and nothing
    here touches it.
    """
    plan = {"date": "2026-08-28", "tasks": [
        {"id": "cron", "title": "Add a handler that authenticates on CRON_SECRET",
         "detail": "the specifics live here", "agent": True}]}
    out = run(state, "new", "--force", stdin=json.dumps(plan))
    check("a variable in a title is refused", out.returncode, 1)
    contains("and the refusal names it", out.stderr, "environment variable")
    contains("and says where the specifics go", out.stderr, "detail")

    for title, why in (
        ("Rewrite api/newsletter-send.js", "names a file"),
        ("Call run() from the cron handler", "names a function"),
        ("Select issues where scheduled_for has passed", "names an identifier"),
        ("Fix the getUser call", "names an identifier"),
        ("Set `status` to scheduled", "quotes code"),
    ):
        plan["tasks"][0]["title"] = title
        out = run(state, "new", "--force", stdin=json.dumps(plan))
        check(f"{title!r} is refused", out.returncode, 1)
        contains(f"{title!r} is named for what it is", out.stderr, why)

    # The shapes English actually has must go through, or the guard is noise.
    for title in ("Move outreach links to baytownwebdevelopment.com",
                  "Put the sending domain into Google Postmaster Tools",
                  "Get on Clutch, UpCity and GoodFirms",
                  "Check the DNS record and the API key",
                  "Re-paste the service role key into the cloud environment"):
        plan["tasks"][0]["title"] = title
        out = run(state, "new", "--force", stdin=json.dumps(plan))
        check(f"{title!r} goes through", out.returncode, 0)

    run(state, "new", "--force", stdin=json.dumps(PLAN))
    out = run(state, "add", stdin=json.dumps(
        {"tasks": [{"id": "x", "title": "Read src/index.css"}]}))
    check("add refuses one too", out.returncode, 1)
    out = run(state, "amend", "www", "--title", "Set SUPABASE_URL")
    check("and so does amend", out.returncode, 1)

    out = run(state, "amend", "www", "--title", "Set SUPABASE_URL",
              extra={"INTELLIGENCE_ALLOW_PLAN_JARGON": "1"})
    check("the override lets a misread through", out.returncode, 0)


def case_the_page_marks_are_comments_where_they_land(state):
    """A mark has to be a comment in the language it sits in, or it eats a rule.

    An HTML comment inside a `<style>` is not a comment to CSS: the parser
    reads it as the start of a selector and swallows the rule after it. Both
    stamped blocks were losing their first rule that way, which is invisible
    until the thing it styled is the thing being read.
    """
    seed_page(state)
    page = state / "day-plans" / "2026-08-28.html"
    text = page.read_text()
    missing("no html comment carries the status mark", text,
            "<!-- day-plan:status -->")
    missing("nor the sheet's", text, "<!-- day-plan:sheet-style -->")
    contains("the status mark is a comment css understands", text,
             "/* day-plan:status */")
    contains("and so is the sheet's", text, "/* day-plan:sheet-style */")

    # A page stamped before this was true is repaired rather than left broken.
    page.write_text(text.replace("/* day-plan:status */",
                                 "<!-- day-plan:status -->"))
    run(state, "sync")
    text = page.read_text()
    missing("a page stamped the old way is repaired", text,
            "<!-- day-plan:status -->")
    check("without stamping a second block", text.count("day-plan:status"), 2)


def case_a_reworded_task_leaves_the_page_stale(state):
    """The sheet is built from the titles, so rewording one is page drift.

    Statuses were once the whole fingerprint, on the ground that prose does not
    change what a page says is done. The sheet renders the titles and the
    blocking, so it does now, and a page left unpublished after an amend says
    something the ledger no longer says.
    """
    seed_page(state)
    check("the page starts true", run(state, "page").returncode, 0)
    run(state, "amend", "www", "--title", "Settle on the www redirect")
    out = run(state, "page")
    check("rewording it leaves the published page behind", out.returncode, 1)
    contains("the new wording is on the file already",
             (state / "day-plans" / "2026-08-28.html").read_text(),
             "Settle on the www redirect")
    run(state, "published")
    check("republishing settles it", run(state, "page").returncode, 0)


def case_the_run_sheet_reads_back_in_a_terminal(state):
    """A run has to be able to check what it published without opening it."""
    run(state, "new", stdin=json.dumps(PLAN))
    run(state, "done", "gbp")
    out = run(state, "runsheet").stdout
    contains("the day is named", out, "2026-08-28 -- taylorurl.com")
    contains("the agent's half is counted", out, "What the agent is doing (0 of 3 done)")
    contains("and yours", out, "What it needs from you (1 of 2 done)")
    contains("a closed step is marked", out, "1. [done] Create the profile")
    contains("the numbering runs across the day", out, "3. Settle on www")
    contains("and the blocking reads as English", out,
             "Cannot start until step 3 is done.")


def case_carrying_hands_the_link_to_the_new_day(state):
    """One link is the day plan, and it belongs to whichever day is current.

    A link per day is a gallery nobody opens, and the old one goes on being
    read after the work has moved off it. So the artifact travels with the
    work, and the day it leaves stops claiming it -- otherwise both plans name
    one url and the older of them demands the page back.
    """
    seed_page(state)
    run(state, "done", "gbp")
    run(state, "carry", "--to", "2026-08-29")

    was = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    now = json.loads((state / "day-plans" / "2026-08-29.json").read_text())
    check("the new day holds the link", now["artifact"], "https://example.invalid/p")
    check("the day it came from lets go", was["artifact"], "")
    check("and stops reporting on a page it no longer holds",
          run(state, "page", "--date", "2026-08-28").returncode, 0)
    check("while the new day reads as unpublished",
          run(state, "page", "--date", "2026-08-29").returncode, 1)


def case_a_day_gone_by_keeps_only_what_it_closed(state):
    """Carrying is a move, so no task is open on two days at once.

    Open work left behind is what made four plans report work left when there
    was only ever one, and a page for a day gone by still listing it reads as
    a day that never ended.
    """
    seed_page(state)
    page = state / "day-plans" / "2026-08-28.html"
    run(state, "done", "gbp", "www")
    run(state, "carry", "--to", "2026-08-29")

    was = json.loads((state / "day-plans" / "2026-08-28.json").read_text())
    check("yesterday keeps what it closed",
          sorted(t["id"] for t in was["tasks"]), ["gbp", "www"])
    check("and records where the rest went",
          sorted(m["id"] for m in was["moved"]), ["gsc", "social", "verify"])
    check("so it reports itself finished",
          "done" in run(state, "list").stdout.splitlines()[1], True)

    text = page.read_text()
    missing("the moved work is off its page", text, 'data-id="verify"')
    contains("what it closed stays on it", text, 'data-id="gbp"')
    check("and the page still answers to the ledger",
          run(state, "sync", "--date", "2026-08-28").returncode, 0)

    now = json.loads((state / "day-plans" / "2026-08-29.json").read_text())
    check("today holds the work exactly once",
          sorted(t["id"] for t in now["tasks"]), ["gsc", "social", "verify"])


def case_every_page_carries_the_log(state):
    """Replacing the page cannot lose the days it replaced.

    The link shows one day, so what stops that from erasing the rest is the
    log: every plan on file, what each day came to, and what is still ahead,
    stamped on from the ledger rather than written.
    """
    seed_page(state)
    run(state, "done", "gbp", "www")
    run(state, "carry", "--to", "2026-08-29")

    # The link travels; the page for a day is written for that day and
    # published over the one it replaces.
    written = state / "written.html"
    written.write_text(
        "<title>x</title>\n<style>.task { color: red; }</style>\n"
        '<span id="done">0</span><span> / 3</span>\n'
        + "\n".join('<label class="task" data-id="%s"><span>%s</span></label>' % (i, i)
                     for i in ("verify", "gsc", "social"))
        + "\n<script>var a = 1;</script>\n")
    run(state, "artifact", "https://example.invalid/p", "--date", "2026-08-29",
        "--html", str(written))

    page = state / "day-plans" / "2026-08-29.html"
    text = page.read_text()
    contains("the log is stamped in", text, "<!-- day-plan:log -->")
    contains("the day gone by keeps its record", text, "Fri 28 Aug")
    contains("with what it came to", text, "2 of 2 done")
    contains("and the current day is named as current", text,
             '<li data-when="today"><span class="dl-day">Sat 29 Aug</span>'
             '<span class="dl-said">today</span></li>')
    check("the log is on the page once", text.count("<!-- day-plan:log -->"), 1)

    run(state, "sync", "--date", "2026-08-29")
    text = page.read_text()
    check("and a second sync replaces it rather than adding one",
          text.count("<!-- day-plan:log -->"), 1)


def case_a_day_opened_elsewhere_is_page_drift(state):
    """The log is on the page, so a plan opened anywhere makes it stale."""
    seed_page(state)
    check("the page starts true", run(state, "page").returncode, 0)
    run(state, "new", stdin=json.dumps(
        {"date": "2026-09-04", "subject": "later",
         "tasks": [{"id": "later", "title": "Do the thing that waits"}]}))
    check("a day opened ahead leaves the published page behind",
          run(state, "page", "--date", "2026-08-28").returncode, 1)
    run(state, "sync", "--date", "2026-08-28")
    contains("and the sync puts it on the page",
             (state / "day-plans" / "2026-08-28.html").read_text(), "1 waiting")


def case_the_rollover_waits_for_the_date_to_turn(state):
    """The carry a clock makes has to be safe at every hour, not just one.

    A schedule pinned to an hour in one zone is an hour wrong for half the
    year, and a run that misses its slot skips the day. So the event is the
    date turning on the machine holding the plans, and every other reading is
    a no-op -- which is what lets it be checked as often as it likes and
    catch up after an outage.
    """
    today = _date.today().isoformat()
    gone = (_date.today() - _timedelta(days=1)).isoformat()

    plan = dict(PLAN, date=gone)
    run(state, "new", stdin=json.dumps(plan))
    out = run(state, "rollover")
    contains("a day already gone is carried onto today", out.stdout, today)
    check("today now holds the work", path_of(state, today).is_file(), True)
    left = json.loads(path_of(state, gone).read_text())
    check("and yesterday keeps only what it closed", left["tasks"], [])

    out = run(state, "rollover")
    contains("running it again does nothing", out.stdout, "already has a plan")
    check("and leaves the plan alone", out.returncode, 0)

    # A plan for the day in hand is not something to roll anywhere.
    fresh = Path(state) / "second"
    fresh.mkdir()
    run(fresh, "new", stdin=json.dumps(dict(PLAN, date=today)))
    out = run(fresh, "rollover")
    contains("today's own plan is left where it is", out.stdout, "already has a plan")

    # Nothing on file at all is a no-op rather than a failure.
    empty = Path(state) / "third"
    empty.mkdir()
    out = run(empty, "rollover")
    check("an empty tree rolls nothing", out.returncode, 0)
    contains("and says so", out.stdout, "no plans on file")

    # The schedule asks every hour and acts on one, so the question has to be
    # answerable without acting on it.
    ask = Path(state) / "asking"
    ask.mkdir()
    run(ask, "new", stdin=json.dumps(dict(PLAN, date=gone)))
    out = run(ask, "rollover", "--check")
    check("a rollover that is due answers yes", out.returncode, 0)
    contains("and says what would move", out.stdout, f"{gone} rolls onto {today}")
    check("while changing nothing", path_of(ask, today).is_file(), False)
    check("so the run after it still has the work to do",
          run(ask, "rollover").returncode, 0)
    check("and the check then answers no",
          run(ask, "rollover", "--check").returncode, 1)

    # A day that closed everything has nothing to carry, so it stays closed.
    done = Path(state) / "fourth"
    done.mkdir()
    run(done, "new", stdin=json.dumps({"date": gone, "tasks": [
        {"id": "one", "title": "Settle the last thing"}]}))
    run(done, "done", "one")
    out = run(done, "rollover")
    contains("a day that closed out is left closed", out.stdout, "nothing to carry")
    check("and today gets no empty plan", path_of(done, today).is_file(), False)


def case_the_page_travels_with_the_work(state):
    """A rollover on a clock has nobody to write the new day a page.

    Half of what it is for is the rename, so the page goes with the link and
    the work: the cards that moved come with it, the ones that stayed do not,
    and the title, the run sheet and the log are restamped for the day it is
    now.
    """
    seed_page(state)
    run(state, "done", "gbp", "www")
    run(state, "carry", "--to", "2026-08-29")

    page = state / "day-plans" / "2026-08-29.html"
    check("the new day has a page without one being written", page.is_file(), True)
    text = page.read_text()
    contains("it carries its own name", text, "<title>Aug 29 Day Plan</title>")
    contains("the work that moved is on it", text, 'data-id="verify"')
    missing("what stayed behind is not", text, 'data-id="gbp"')
    contains("and the run sheet is the new day's", text,
             '<span class="rs-what">Submit verification</span>')

    plan = json.loads((state / "day-plans" / "2026-08-29.json").read_text())
    check("the plan points at it", plan["html"], str(page))
    check("the ledger and the page agree",
          run(state, "sync", "--date", "2026-08-29").returncode, 0)

    old = (state / "day-plans" / "2026-08-28.html").read_text()
    contains("the day it left keeps its own page", old, 'data-id="gbp"')
    missing("with the work that moved off it", old, 'data-id="verify"')


def main():
    for case in (case_ordering, case_carry, case_unknown_need, case_current,
                 case_running_is_not_ready, case_running_survives_the_day,
                 case_release_hands_a_task_back,
                 case_an_ended_owners_marker_is_repaired,
                 case_your_own_marker_stops_the_session,
                 case_page_follows_the_ledger, case_the_page_is_named_for_its_day,
                 case_add_grows_a_plan_without_disturbing_it,
                 case_page_mismatch_refuses,
                 case_unpublished_page_is_caught, case_one_human_step_at_a_time,
                 case_defer_moves_the_chain,
                 case_amend_rewords_without_losing_structure,
                 case_reorder_does_not_relabel_the_page,
                 case_needs_reopens_work_a_stale_blocker_held,
                 case_every_write_is_stamped, case_empty_state_pulls_once,
                 case_a_write_schedules_the_share,
                 case_a_throwaway_root_never_publishes,
                 case_a_redirected_remote_still_publishes,
                 case_the_machines_own_root_publishes,
                 case_unshared_state_holds_the_session,
                 case_the_gate_makes_the_trip_before_it_refuses,
                 case_a_trip_that_settles_nothing_still_holds_the_session,
                 case_the_page_and_the_ledger_are_reported_together,
                 case_a_read_fetches_when_it_could_be_stale,
                 case_a_read_survives_an_unreachable_mirror,
                 case_closures_at_the_same_moment_all_survive,
                 case_the_override_stands_it_all_down,
                 case_a_parked_decision_is_refused,
                 case_a_parked_decision_cannot_be_carried,
                 case_tomorrows_plan_does_not_take_over_today,
                 case_a_move_leaves_nothing_behind,
                 case_a_move_takes_the_card_off_the_page,
                 case_the_run_sheet_opens_every_page,
                 case_the_run_sheet_says_what_the_ledger_says,
                 case_a_jargon_title_is_refused,
                 case_the_page_marks_are_comments_where_they_land,
                 case_a_reworded_task_leaves_the_page_stale,
                 case_the_run_sheet_reads_back_in_a_terminal,
                 case_carrying_hands_the_link_to_the_new_day,
                 case_a_day_gone_by_keeps_only_what_it_closed,
                 case_every_page_carries_the_log,
                 case_a_day_opened_elsewhere_is_page_drift,
                 case_the_rollover_waits_for_the_date_to_turn,
                 case_the_page_travels_with_the_work):
        with tempfile.TemporaryDirectory() as tmp:
            case(Path(tmp))
    if FAILURES:
        for f in FAILURES:
            print(f"FAIL {f}", file=sys.stderr)
        return 1
    print("day-plan: all cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
