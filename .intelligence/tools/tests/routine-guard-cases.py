#!/usr/bin/env python3
"""Cases the routine guard has to get right.

The guard is worth what it refuses: a scheduled run that reported to nobody, a
summary too short to say anything, a report that names nothing openable, a
maintenance phase whose gate went unanswered, a line the routine forbids. Each
refusal here sits beside the neighboring turn that stays allowed, so the guard
cannot drift wider without a case saying so. The routine's own text is the gate
list, and a phase heading quoted inside a fence is display rather than
declaration -- the parse skips it.

  routine-guard-cases.py        run them
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
              or Path(__file__).resolve().parent.parent / "routine-guard.py")

FAILURES = []

ROUTINE = """# Phase 0 -- Pull the shared ledgers
<!-- enforce run: pass-state(\\.py)?\\s+pull -->

Pull before anything else touches a ledger.

# Phase 1 -- Platform health
<!-- enforce report: Vercel -->

Read every project's deploy state and say what was found.
"""

QUIET_ROUTINE = """# Phase 0 -- Look at everything
<!-- enforce run: routine-sync(\\.py)?\\s+health -->

Look.

# Phase 1 -- Say what was wrong
<!-- enforce report: routine -->

Only when something was.

<!-- enforce quiet: routine-sync(\\.py)?\\s+health -->
"""

# The same routine with a fenced example quoting the marker syntax. The quoted
# phase declares nothing, so a parse that reads it fails every run over a phase
# that does not exist.
ROUTINE_FENCED = ROUTINE + """
## Every phase is gated

Each heading declares its own gates:

```
# Phase 9 -- Example only
<!-- enforce run: never-run -->
```
"""

# Over the length floor and anchored, but naming nothing the sentinel's report
# gate wants: a summary can be a real report and still miss its phase.
SILENT_SUMMARY = (
    "The sweep ran against bradley-t-t/intelligence and every checkout on this "
    "machine was already current. The shared ledgers were pulled at the start "
    "and pushed at the end so the next machine begins from this pass. Nothing "
    "needed changing anywhere, no branch was left unlanded, and no credential "
    "or history rewrite is outstanding for anyone to action."
)

# What the sentinel sends when it does have something: over the floor, anchored,
# and naming what its own report gate asks for.
SENTINEL_SUMMARY = (
    "One routine needed attention this hour. Blog & Social Posts in "
    "bradley-t-t/intelligence was carrying no repository list, so every push "
    "it attempted was refused by the proxy and yesterday's article never went "
    "live. The sources were restored from the checked-in config and read back "
    "to confirm they took. Every other routine answered with a prompt, a "
    "schedule and a successful last run, and the Pi timers are all active."
)

# Over the length floor and anchored: names a repo path and the platform the
# report gate wants.
GOOD_SUMMARY = (
    "Maintenance swept every owned repository under bradley-t-t/intelligence "
    "and found the tree clean. The shared ledgers were pulled first and pushed "
    "back at the end, so the next machine to run starts from this sweep rather "
    "than its own. Vercel answered for every project with the latest deploy "
    "serving, and no build was found behind its merge. Nothing needed changing "
    "in any checkout, no branch was left unlanded, and no credential or "
    "security finding surfaced anywhere the sweep looked."
)

# Over the floor and true of somewhere, silent about where: no path, no URL,
# no pull request number, no file name.
ANCHORLESS_SUMMARY = (
    "The sweep finished and nothing needed changing anywhere it looked. "
) * 8


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bash(command):
    return {"type": "tool_use", "name": "Bash", "input": {"command": command}}


def mcp(name, args=None):
    return {"type": "tool_use", "name": name, "input": args or {}}


PUSH_ID = "toolu_push_1"


def push(summary, delivered=True):
    """A report, and the transport's answer about whether it arrived.

    Every call in a real transcript is followed by its result, so a fixture that
    omits one models a turn that cannot happen and would let an undelivered
    report read as a delivered one.
    """
    call = {"type": "tool_use", "id": PUSH_ID, "name": "PushNotification",
            "input": {"message": "<routine_summary>%s</routine_summary>" % summary}}
    answer = "Delivered" if delivered else "Not sent - this terminal is active"
    return [call, {"type": "tool_result", "tool_use_id": PUSH_ID,
                   "content": answer}]


def webhook(summary):
    """A report posted to the webhook instead, which still reaches somebody."""
    call = {"type": "tool_use", "id": "toolu_hook_1", "name": "Bash",
            "input": {"command":
                      "curl -X POST https://discord.com/api/webhooks/1/x "
                      "-d '<routine_summary>%s</routine_summary>'" % summary}}
    return [call, {"type": "tool_result", "tool_use_id": "toolu_hook_1",
                   "content": "204"}]


def flatten(blocks):
    """Fixtures name a call or a call-and-answer pair interchangeably."""
    out = []
    for block in blocks:
        out.extend(block if isinstance(block, list) else [block])
    return out


def transcript(tmp, prompt, blocks):
    """A one-turn transcript: the firing prompt, then the tool calls made."""
    blocks = flatten(blocks)
    rows = [{"type": "user", "message": {"role": "user", "content": prompt}},
            {"type": "assistant", "message": {"role": "assistant", "content": blocks}}]
    path = Path(tmp) / "transcript.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def run_stop(prompt, blocks, routine=None, env_extra=None):
    """The guard's verdict on one turn, built entirely inside a temp tree."""
    with tempfile.TemporaryDirectory() as tmp:
        path = transcript(tmp, prompt, blocks)
        env = {k: v for k, v in os.environ.items()
               if k not in ("INTELLIGENCE_SKIP_ROUTINE_GUARD",
                            "INTELLIGENCE_ROUTINE_FILE")}
        if routine is not None:
            routine_path = Path(tmp) / "daily-maintenance.md"
            routine_path.write_text(routine)
            env["INTELLIGENCE_ROUTINE_FILE"] = str(routine_path)
            assert str(routine_path).startswith(tmp), routine_path
        if env_extra:
            env.update(env_extra)
        assert str(path).startswith(tmp), path
        ev = json.dumps({"transcript_path": str(path), "cwd": tmp})
        p = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                           input=ev, capture_output=True, text=True, env=env)
        return p.returncode


BILLING = ("[SCHEDULED TASK trig_abc] Read the account and follow "
           "routine/weekly-billing.md, phases in order.")
AGREEMENT = ("[SCHEDULED TASK trig_abc] Read routine/INTELLIGENCE.md, then "
             "watch the pull request and report.")

SENTINEL = ("[SCHEDULED TASK trig_abc] Follow routine/continuous-sentinel.md "
            "and check the other routines.")

SCHEDULED = "[SCHEDULED TASK trig_abc] Watch the pull request and report."
MAINTENANCE = "[SCHEDULED TASK trig_abc] Run the daily maintenance pass."
MAINT_DONE = [bash("~/.intelligence/tools/pass-state.py pull"),
              push(GOOD_SUMMARY)]


def main():
    # A turn nobody scheduled owes the guard nothing.
    check("unscheduled turn ignored",
          run_stop("do the thing", [push("short")]), 0)

    # The marker opens the prompt because that is where the runner stamps it.
    # A turn discussing scheduled runs is not one, and judging it as one holds
    # the session open on gates no routine declared.
    check("a prompt quoting the marker mid-sentence is not a scheduled run",
          run_stop("the runner stamps [SCHEDULED TASK blog] itself, so the rule "
                   "keeps applying", [bash("git status")]), 0)
    check("a prompt the runner stamped is still a scheduled run",
          run_stop("[SCHEDULED TASK blog]\n\npublish the day's copy",
                   [bash("git status")]), 2)

    # A scheduled turn ends only through a real report.
    check("no summary refused", run_stop(SCHEDULED, [bash("git status")]), 2)
    check("good summary passes", run_stop(SCHEDULED, [push(GOOD_SUMMARY)]), 0)
    check("short summary refused", run_stop(SCHEDULED, [push("All good.")]), 2)
    check("anchorless summary refused",
          run_stop(SCHEDULED, [push(ANCHORLESS_SUMMARY)]), 2)

    # The override and the malformed event both stand the guard down.
    check("skip env passes",
          run_stop(SCHEDULED, [bash("git status")],
                   env_extra={"INTELLIGENCE_SKIP_ROUTINE_GUARD": "1"}), 0)
    p = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                       input="not json", capture_output=True, text=True)
    check("bad stdin passes", p.returncode, 0)
    p = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                       input=json.dumps({}), capture_output=True, text=True)
    check("no transcript passes", p.returncode, 0)

    # A maintenance run answers to the routine's phase gates.
    check("gates answered passes",
          run_stop(MAINTENANCE, MAINT_DONE, routine=ROUTINE), 0)
    check("run gate unanswered refused",
          run_stop(MAINTENANCE, [bash("git status"), push(GOOD_SUMMARY)],
                   routine=ROUTINE), 2)
    check("report gate unanswered refused",
          run_stop(MAINTENANCE,
                   [bash("pass-state.py pull"),
                    push(GOOD_SUMMARY.replace("Vercel", "the platform"))],
                   routine=ROUTINE), 2)
    check("markerless phase refused",
          run_stop(MAINTENANCE, MAINT_DONE,
                   routine=ROUTINE + "\n# Phase 2 -- Unenforced\n\nbody\n"), 2)
    check("invalid marker refused",
          run_stop(MAINTENANCE, MAINT_DONE,
                   routine=ROUTINE + "\n# Phase 2 -- Broken\n"
                                     "<!-- enforce run: [unclosed -->\n"), 2)

    # A phase heading inside a fence is a quotation, not a phase.
    check("fenced phase not counted",
          run_stop(MAINTENANCE, MAINT_DONE, routine=ROUTINE_FENCED), 0)

    # The routine's prohibitions refuse the run; their lawful neighbors do not.
    check("force push to main refused",
          run_stop(MAINTENANCE,
                   MAINT_DONE + [bash("git push --force origin main")],
                   routine=ROUTINE), 2)
    check("plain push allowed",
          run_stop(MAINTENANCE,
                   MAINT_DONE + [bash("git push origin feature-branch")],
                   routine=ROUTINE), 0)

    # Delivery, not the attempt. A notification into an active terminal comes
    # back undelivered, and a run that reported to nobody is a silent run.
    check("a report the transport declined is not a report",
          run_stop(MAINTENANCE,
                   [b for b in MAINT_DONE if b is not MAINT_DONE[-1]]
                   + [push(GOOD_SUMMARY, delivered=False)],
                   routine=ROUTINE), 2)
    check("a report through the webhook counts",
          run_stop(MAINTENANCE,
                   [b for b in MAINT_DONE if b is not MAINT_DONE[-1]]
                   + [webhook(GOOD_SUMMARY)],
                   routine=ROUTINE), 0)

    # A routine never writes to a database.
    check("a migration by a routine is refused",
          run_stop(MAINTENANCE,
                   MAINT_DONE + [mcp("mcp__0917cb34__apply_migration",
                                     {"name": "add_column"})],
                   routine=ROUTINE), 2)
    check("a routine reading the database is untouched",
          run_stop(MAINTENANCE,
                   MAINT_DONE + [mcp("mcp__0917cb34__list_tables", {})],
                   routine=ROUTINE), 0)
    check("admin merge refused",
          run_stop(MAINTENANCE, MAINT_DONE + [bash("gh pr merge 7 --admin")],
                   routine=ROUTINE), 2)
    check("auto merge allowed",
          run_stop(MAINTENANCE,
                   MAINT_DONE + [bash("gh pr merge 7 --auto --squash")],
                   routine=ROUTINE), 0)
    check("protection removal refused",
          run_stop(MAINTENANCE,
                   MAINT_DONE + [bash("gh api -X DELETE "
                                      "repos/o/r/branches/main/protection")],
                   routine=ROUTINE), 2)

    # Money and messages are refused for every routine, not only the one whose
    # file forbids them, and the read beside the write stays allowed.
    check("stripe write refused",
          run_stop(SCHEDULED, [mcp("mcp__stripe__stripe_api_write",
                                   {"path": "/v1/invoices"}),
                               push(GOOD_SUMMARY)]), 2)
    check("stripe read allowed",
          run_stop(SCHEDULED, [mcp("mcp__stripe__stripe_api_read",
                                   {"path": "/v1/invoices"}),
                               push(GOOD_SUMMARY)]), 0)
    check("stripe shell write refused",
          run_stop(SCHEDULED, [bash("stripe invoices create --customer cus_1"),
                               push(GOOD_SUMMARY)]), 2)
    check("stripe curl post refused",
          run_stop(SCHEDULED,
                   [bash("curl -X POST https://api.stripe.com/v1/invoices"),
                    push(GOOD_SUMMARY)]), 2)
    check("stripe curl get allowed",
          run_stop(SCHEDULED,
                   [bash("curl -s https://api.stripe.com/v1/invoices?limit=5"),
                    push(GOOD_SUMMARY)]), 0)
    check("mail send refused",
          run_stop(SCHEDULED, [mcp("mcp__ms__outlook_send_mail", {"to": "x"}),
                               push(GOOD_SUMMARY)]), 2)
    # A read in one call and a method flag in another are not a write.
    check("split across calls allowed",
          run_stop(SCHEDULED,
                   [bash("curl -s https://api.stripe.com/v1/charges"),
                    bash("curl -X POST https://example.com/hook -d ok"),
                    push(GOOD_SUMMARY)]), 0)

    # A routine that never says "maintenance" still owes the phases of the file
    # its prompt named.
    check("named task file gates enforced",
          run_stop(BILLING, [push(GOOD_SUMMARY)], routine=ROUTINE), 2)
    check("named task file gates answered",
          run_stop(BILLING, MAINT_DONE, routine=ROUTINE), 0)

    # A routine allowed to end silently does so only once it has actually
    # looked, and a routine with no such marker owes its report regardless.
    check("quiet routine that looked ends silently",
          run_stop(SENTINEL, [bash("~/.intelligence/tools/routine-sync.py health --file /tmp/x")],
                   routine=QUIET_ROUTINE), 0)
    check("quiet routine that never looked is refused",
          run_stop(SENTINEL, [bash("echo nothing")], routine=QUIET_ROUTINE), 2)
    check("quiet routine still reports when it speaks",
          run_stop(SENTINEL,
                   [bash("~/.intelligence/tools/routine-sync.py health --file /tmp/x"),
                    push(SENTINEL_SUMMARY)], routine=QUIET_ROUTINE), 0)
    check("a summary that answers no report gate is still refused",
          run_stop(SENTINEL,
                   [bash("~/.intelligence/tools/routine-sync.py health --file /tmp/x"),
                    push(SILENT_SUMMARY)], routine=QUIET_ROUTINE), 2)
    check("silence is not allowed without the marker",
          run_stop(MAINTENANCE, [bash("~/.intelligence/tools/pass-state.py pull")],
                   routine=ROUTINE), 2)

    # `gates` prints the routine's own list; the fenced example stays out of it.
    with tempfile.TemporaryDirectory() as tmp:
        routine_path = Path(tmp) / "daily-maintenance.md"
        routine_path.write_text(ROUTINE_FENCED)
        assert str(routine_path).startswith(tmp), routine_path
        env = dict(os.environ, INTELLIGENCE_ROUTINE_FILE=str(routine_path))
        p = subprocess.run([sys.executable, str(TARGET), "gates"],
                           capture_output=True, text=True, env=env)
        check("gates exits clean", p.returncode, 0)
        check("gates names the file", str(routine_path) in p.stdout, True)
        check("gates lists Phase 0", "Phase 0" in p.stdout, True)
        check("gates lists the run gate", "pass-state" in p.stdout, True)
        check("gates skips fenced phase", "Phase 9" in p.stdout, False)

    # An unknown verb prints the contract and refuses.
    p = subprocess.run([sys.executable, str(TARGET)],
                       capture_output=True, text=True)
    check("no verb refused", p.returncode, 2)
    check("no verb prints usage", "guard-stop" in p.stderr, True)

    # The parsers, held directly.
    mod = load()
    phases = mod.gates_of(ROUTINE_FENCED)
    check("gates_of counts real phases", len(phases), 2)
    check("gates_of keeps real gates",
          [len(gates) for _, gates in phases], [1, 1])
    tilde = "~~~\n# Phase 9 -- Example only\n~~~\n"
    check("tilde fence skipped", len(mod.gates_of(ROUTINE + tilde)), 2)
    check("anchor: repo path", bool(mod.ANCHOR.search("see bradley-t-t/intelligence")), True)
    check("anchor: bare prose", bool(mod.ANCHOR.search("nothing needed changing")), False)
    check("task named from a prompt",
          str(mod.task_named(BILLING)), "routine/weekly-billing.md")
    check("the agreement is not a task", mod.task_named(AGREEMENT), None)
    check("no task named", mod.task_named(SCHEDULED), None)
    check("summary tag extracted",
          mod.SUMMARY.search("x <routine_summary>found it</routine_summary> y").group(1),
          "found it")

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
