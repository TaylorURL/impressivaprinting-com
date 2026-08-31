#!/usr/bin/env python3
"""Cases the guard hub has to get right.

The hub's one promise: a guard whose own first gate matches an event is exec'd
with the event's exact bytes, and an event nothing could act on spawns no
process at all. The refusal texts come from the guards themselves, so parity
here is about which guards run and how their exits travel, not about restating
their judgments.

  guard-hub-cases.py        run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "guard-hub.py")

FAILURES = []


def run_hub(verb, event, env=None, state_dir=None):
    """The hub's exit code and the guard argvs it exec'd.

    Every INTELLIGENCE_ variable is dropped before the fixture puts back the
    ones it wants. The hub picks which guards to dispatch from exactly those
    variables, so one carried in from the calling shell switches off a case's
    own subject, and the suite then reads that silence as the hub's answer.
    """
    environ = {k: v for k, v in os.environ.items()
               if not k.startswith("INTELLIGENCE_")}
    environ["INTELLIGENCE_HUB_TRACE"] = "1"
    if state_dir:
        environ["INTELLIGENCE_STATE_DIR"] = state_dir
    environ.update(env or {})
    done = subprocess.run([sys.executable, str(TARGET), verb],
                          input=json.dumps(event), capture_output=True,
                          text=True, env=environ, timeout=300)
    execs = [line.split("hub exec: ", 1)[1]
             for line in done.stderr.splitlines() if line.startswith("hub exec: ")]
    return done.returncode, execs, done.stderr


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def check_in(label, needle, hay):
    if not any(needle in item for item in hay):
        FAILURES.append("%s: %r not among %r" % (label, needle, hay))


def bash(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": "/tmp"}


def in_flight_cases(quiet):
    """A run being worked keeps its guard asleep; a quiet one wakes it."""
    ending = {"session_id": "fixture-session", "stop_hook_active": False,
              "transcript_path": ""}
    env = dict(quiet, INTELLIGENCE_REMOTE_OFF="1", INTELLIGENCE_CONCISE_OFF="1",
               INTELLIGENCE_DELEGATION_OFF="1")
    with tempfile.TemporaryDirectory() as state:
        runs = Path(state) / "seo-runs"
        runs.mkdir(parents=True)
        (runs / "current-fixture-session.json").write_text(json.dumps({"id": "20260829-000001"}))
        run_file = runs / "20260829-000001.json"
        run_file.write_text(json.dumps({"id": "20260829-000001", "order": [], "results": {}}))

        _, execs, _ = run_hub("stop", ending, env=env, state_dir=state)
        check("a run written just now leaves its guard asleep",
              [e for e in execs if "seo-pass" in e], [])

        old = time.time() - 3600
        os.utime(run_file, (old, old))
        _, execs, _ = run_hub("stop", ending, env=env, state_dir=state)
        check_in("a run nobody has touched wakes it", "seo-pass.py", execs)

        # The window is a number rather than a constant of the machine, so a
        # deployment that works a run slowly can widen it.
        _, execs, _ = run_hub("stop", ending,
                              env=dict(env, INTELLIGENCE_IN_FLIGHT_SECONDS="7200"),
                              state_dir=state)
        check("a widened window covers an older write",
              [e for e in execs if "seo-pass" in e], [])

        # Recency decides nothing when the escape is set: an unconditional guard
        # is what a session ending for real needs.
        _, execs, _ = run_hub("stop", ending,
                              env=dict(env, INTELLIGENCE_IN_FLIGHT_OFF="1"),
                              state_dir=state)
        check_in("the escape fires the guard whatever the mtime", "seo-pass.py", execs)

        run_file.unlink()
        _, execs, _ = run_hub("stop", ending, env=env, state_dir=state)
        check_in("a pointer with no run behind it wakes the guard", "seo-pass.py", execs)


def agent_liveness_cases(quiet):
    """A working subagent holds the stop guards off its own session's runs."""
    env = dict(quiet, INTELLIGENCE_REMOTE_OFF="1", INTELLIGENCE_CONCISE_OFF="1",
               INTELLIGENCE_DELEGATION_OFF="1")
    sid = "fixture-session"
    with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as project:
        runs = Path(state) / "seo-runs"
        runs.mkdir(parents=True)
        (runs / ("current-%s.json" % sid)).write_text(json.dumps({"id": "20260829-000002"}))
        run_file = runs / "20260829-000002.json"
        run_file.write_text(json.dumps({"id": "20260829-000002", "order": [], "results": {}}))
        old = time.time() - 3600
        os.utime(run_file, (old, old))

        transcript = Path(project) / ("%s.jsonl" % sid)
        transcript.write_text("")
        ending = {"session_id": sid, "stop_hook_active": False,
                  "transcript_path": str(transcript)}

        # A quiet run with no subagent directory beside it is the abandoned case.
        _, execs, _ = run_hub("stop", ending, env=env, state_dir=state)
        check_in("a quiet run with no agents wakes the guard", "seo-pass.py", execs)

        subagents = Path(project) / sid / "subagents"
        subagents.mkdir(parents=True)
        working = subagents / "agent-fixture.jsonl"
        working.write_text("{}\n")
        _, execs, _ = run_hub("stop", ending, env=env, state_dir=state)
        check("a working subagent holds the guard off",
              [e for e in execs if "seo-pass" in e], [])

        os.utime(working, (old, old))
        _, execs, _ = run_hub("stop", ending, env=env, state_dir=state)
        check_in("a subagent that stopped writing releases it", "seo-pass.py", execs)

        # The escape answers for a session ending in earnest, whatever is moving.
        working.write_text("{}\n")
        _, execs, _ = run_hub("stop", ending,
                              env=dict(env, INTELLIGENCE_IN_FLIGHT_OFF="1"),
                              state_dir=state)
        check_in("the escape outranks a working subagent", "seo-pass.py", execs)

        # A payload naming no transcript cannot look for one.
        _, execs, _ = run_hub("stop", dict(ending, transcript_path=""), env=env,
                              state_dir=state)
        check_in("no transcript path leaves the guard armed", "seo-pass.py", execs)


def main():
    # The comment guard's drift branch and the naming guard's wiring check are
    # environment-wide facts, exercised by those tools' own cases; their escape
    # variables pin these fixtures to the dispatch question alone, so the same
    # assertions hold in the installed tree and in a bare CI checkout.
    quiet = {"INTELLIGENCE_ALLOW_COMMENT": "1", "INTELLIGENCE_ALLOW_LEGACY_NAME": "1"}
    tree = TARGET.resolve().parent.parent
    with tempfile.TemporaryDirectory() as state:
        # The fast paths: events nothing could act on spawn nothing.
        code, execs, _ = run_hub("pre", bash("git status"), env=quiet,
                                 state_dir=state)
        check("ordinary bash spawns nothing", (code, execs), (0, []))
        # A read-shaped command is not one of those: the survey gate counts
        # reads, so reaching it is the contract rather than a leak in the fast
        # path. Without a transcript it has nothing to measure and exits 0.
        code, execs, _ = run_hub("pre", bash("ls -la /tmp"), env=quiet,
                                 state_dir=state)
        check("a read reaches the survey gate",
              (code, [e for e in execs if "delegation-guard" in e]),
              (0, [str(TARGET.resolve().parent / "delegation-guard.py")
                   + " guard-probe"]))
        code, execs, _ = run_hub(
            "post", {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}},
            state_dir=state)
        check("ordinary read spawns nothing", (code, execs), (0, []))
        code, execs, _ = run_hub(
            "pre", {"tool_name": "Edit",
                    "tool_input": {"file_path": str(tree / "x.py"),
                                   "new_string": "pass"}},
            env=quiet, state_dir=state)
        check("config-tree edit skips worktree and naming",
              [e for e in execs if "worktree" in e or "naming" in e], [])

        # Blocks travel through with the guard's own exit and words.
        code, execs, err = run_hub(
            "pre", bash('open -a "Google Chrome" https://example.com'), state_dir=state)
        check("chrome command blocks", code, 2)
        check_in("chrome-guard ran", "chrome-guard.py", execs)
        if "BLOCKED" not in err:
            FAILURES.append("chrome refusal text missing")
        code, execs, _ = run_hub(
            "pre", bash('git commit -m "x" --author="Claude <noreply@anthropic.com>"'),
            state_dir=state)
        check("AI-attributed commit blocks", code, 2)
        check_in("attribution guard ran", "ai-attribution-guard.py", execs)
        code, execs, _ = run_hub("pre", bash("mkdir ~/.cl" + "aude"), state_dir=state)
        check("legacy-name command blocks", code, 2)

        # Telemetry: a guard that ran leaves a row carrying its own exit, and a
        # guard that was never due leaves none, so the log counts decisions
        # rather than opportunities.
        log = Path(state) / "guard-log.jsonl"
        rows = [json.loads(line) for line in log.read_text().splitlines()] \
            if log.exists() else []
        refusals = [r for r in rows if r.get("exit") == 2]
        check("a refusal is recorded", bool(refusals), True)
        check("the row names the guard that refused",
              any(r["guard"] == "chrome-guard.py" for r in refusals), True)
        check("the row carries the tool it judged",
              all(r.get("tool") == "Bash" for r in refusals), True)
        check("no row claims a guard that never ran",
              any(r["guard"] == "stripe-guard.py" for r in rows), False)
        check_in("naming guard ran", "intelligence-naming.py", execs)

        # A landing command reaches every landing gate.
        code, execs, _ = run_hub(
            "pre", bash('cd /tmp && git commit -m "tidy"'), state_dir=state)
        for name in ("writing-pass.py", "version-badge.py"):
            check_in("landing reaches %s" % name, name, execs)
        check("landing outside an owned repo does not block", code, 0)

        # Run-pointer stats decide the checklist engines.
        runs = Path(state) / "seo-runs"
        runs.mkdir(parents=True)
        (runs / "current.json").write_text(json.dumps({"id": "missing"}))
        _, execs, _ = run_hub(
            "post", {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}},
            state_dir=state)
        check_in("open seo pointer wakes the engine", "seo-pass.py", execs)
        check("other engines stay asleep",
              [e for e in execs if "perf-pass" in e or "stack-pass" in e
               or "design-pass" in e], [])

        # The env overrides are honored without a spawn.
        code, execs, _ = run_hub(
            "pre", bash('open -a "Google Chrome" x'),
            env=dict(quiet, INTELLIGENCE_ALLOW_CHROME="1"), state_dir=state)
        check("chrome override spawns nothing", (code, execs), (0, []))

        # Stop: the second pass lets the one-shot guards rest.
        code, execs, _ = run_hub("stop", {"stop_hook_active": True}, state_dir=state)
        check("second stop pass skips the one-shot guards",
              [e for e in execs if "concise" in e or "remote-access" in e], [])
        check_in("naming guard still holds the tree", "intelligence-naming.py", execs)
        code, execs, _ = run_hub("stop", {"stop_hook_active": True}, env=quiet,
                                 state_dir=state)
        check("the naming escape quiets its stop guard too",
              [e for e in execs if "intelligence-naming" in e], [])

        # Stop with a fresh transcript runs the reply guards. One typed prompt
        # makes this a session's first reply, which the reply guard holds to
        # the /short shape, so the fixture reply carries it.
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as t:
            t.write(json.dumps({"type": "user",
                                "message": {"content": "does the mirror carry the row"}}) + "\n")
            t.write(json.dumps({"type": "assistant", "message": {"content": [
                {"type": "text",
                 "text": "> does the mirror carry the row\n\nYes."}]}}) + "\n")
            transcript = t.name
        code, execs, _ = run_hub(
            "stop", {"stop_hook_active": False, "transcript_path": transcript},
            env=dict(quiet, INTELLIGENCE_REMOTE_OFF="1"), state_dir=state)
        os.unlink(transcript)
        check_in("first stop pass runs concise-guard", "concise-guard.py", execs)
        check("a short reply passes", code, 0)

        # A precondition that reads a path under the config tree answers for
        # the wrong tree wherever the state root moves, and a container moves
        # it off that tree entirely. Reading it as the state root resolves it
        # is what keeps the guard awake in the one environment whose ending
        # takes unshared work with it.
        quiet_stop = dict(quiet, INTELLIGENCE_REMOTE_OFF="1",
                          INTELLIGENCE_CONCISE_OFF="1")
        ending = {"stop_hook_active": False, "transcript_path": ""}
        with tempfile.TemporaryDirectory() as elsewhere:
            _, execs, _ = run_hub("stop", ending, env=quiet_stop,
                                  state_dir=elsewhere)
            check("no plans under the resolved root leaves day-plan asleep",
                  [e for e in execs if "day-plan" in e], [])
            (Path(elsewhere) / "day-plans").mkdir(exist_ok=True)
            _, execs, _ = run_hub("stop", ending, env=quiet_stop,
                                  state_dir=elsewhere)
            check_in("plans under the resolved root wake it",
                     "day-plan.py", execs)

    in_flight_cases(quiet)
    agent_liveness_cases(quiet)

    for f in FAILURES:
        print("FAIL %s" % f)
    print("%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
