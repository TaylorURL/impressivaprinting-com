#!/usr/bin/env python3
"""The watch that has to happen on the workstation, three times a day.

Most of what keeps this setup honest runs on the Pi, and that machine is the
wrong place for a whole class of work: it holds one checkout of one repository,
no worktrees, no second copy of anything to find, and no credential for a
deploy remote outside the owner's accounts. The daily pass hits that wall every
run -- a promotion that stops at `origin`, a repo held twice that only a
workstation could see -- and reports it accurately every time.

That is the shape of the gap. It is not that the scheduled runs are failing;
it is that nothing on this side ever picks the work up, so an accurate report
of a wall becomes a task that is never done by anybody.

This is that side. One script, fired by launchd every eight hours, doing only
what has to happen here and reporting only when something is wrong.

Two rules shape it. It composes rather than reimplements: every phase is a tool
that already owns its question, so a fix lands once, in that tool, rather than
here and there. And it stays quiet -- a run that says all is well three times a
day is one nobody reads by the second day, which would make this as silent in
failure as the thing it watches. A clean pass writes its state and prints one
line. Only a finding is surfaced.

  sentinel.py run          the pass; what launchd fires
  sentinel.py install      wire the launchd agent, or bring it back into line
  sentinel.py uninstall    unload the agent and remove its plist
  sentinel.py status       when it last ran, what it found, whether it is wired
  sentinel.py check        whether the agent is loaded and on the right schedule
  sentinel.py inbound      whether the Pi can reach this machine right now

INTELLIGENCE_SENTINEL_STATE names the state directory; otherwise it is
`state/sentinel` beside the tools.
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
TOOLS = Path(os.environ.get("INTELLIGENCE_TOOLS_DIR")
             or Path(__file__).resolve().parent)
INTELLIGENCE = TOOLS.parent
STATE = Path(os.environ.get("INTELLIGENCE_SENTINEL_STATE")
             or INTELLIGENCE / "state" / "sentinel")

LABEL = "com.intelligence.sentinel"
PLIST = HOME / "Library" / "LaunchAgents" / f"{LABEL}.plist"

# Named rather than hardcoded so the cases can hand this a launchctl that
# answers however a case needs. Every other seam here is a file the fixture
# writes; this one talks to the running system, and a suite that shells out to
# the real launchd would pass or fail on whether this machine happens to have
# the agent loaded while it runs.
LAUNCHCTL = os.environ.get("INTELLIGENCE_SENTINEL_LAUNCHCTL", "launchctl")

# Three fires a day, offset from the hour. A pass that starts exactly on the
# hour races the Pi timers, which all fire at :00, for the same network and the
# same feed.
HOURS = (3, 11, 19)
MINUTE = 47

# A probe reading a file answers on a different scale to one that fetches
# thirty repositories, and a run that hangs on a sleeping machine reports
# nothing at all -- which is the failure mode this whole script exists to
# close, so every phase is bounded.
QUICK = 180
NETWORK = 900


def tool(name):
    return str(TOOLS / name)


def run(argv, timeout):
    """A phase reduced to what decides it: the exit code and the text."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return 1, f"timed out after {timeout}s"
    except OSError as err:
        return 1, str(err)
    return done.returncode, ((done.stdout or "") + (done.stderr or "")).strip()


def last_line(text):
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def inbound():
    """Whether the Pi can open a shell on this machine right now.

    Every check here reads outward: this machine asking whether the Pi, the
    desktop and the VPS answer. Nothing asks the reverse, and the reverse is
    the direction the work actually travels -- the routines run on the Pi, and
    the Pi reaches this Mac over the tailnet. So the one link that carries every
    piece of delegated work is the one link nothing probes, and it reads as
    healthy from here whatever it is doing from there.

    It is a laptop, so `out of reach` is usually a closed lid rather than a
    fault. That is why this reports rather than fails: a sleeping machine is
    not a broken setup. It is worth saying out loud all the same, because a
    routine that lost work to a closed lid says only that the Mac was
    unreachable, and never that it should not have been asked.
    """
    argv = [sys.executable, tool("remote-access.py"), "run", "pi", "--",
            "ssh -o BatchMode=yes -o ConnectTimeout=15 trenton-mac "
            "'echo reached; hostname -s'"]
    if not Path(argv[1]).is_file():
        return False, "remote-access.py is not installed"
    code, text = run(argv, QUICK)
    if code == 0 and "reached" in text:
        return True, "the Pi can open a shell here"
    detail = last_line(text) or "no answer"
    if "Permission denied" in text:
        return False, f"the Pi reaches this machine but cannot log in: {detail}"
    return False, f"the Pi cannot reach this machine: {detail}"


# The pass, in order. `advisory` marks a phase whose failure is a fact to
# report rather than a broken setup: an asleep machine and an unpublished
# deploy remote are both real findings, and neither means this tree is wrong.
#
# The ledgers bracket everything. A pass that pulled and then died without
# pushing leaves this machine holding marks no other machine can see, so the
# push runs even when a phase before it found something.
PHASES = [
    {
        "key": "ledgers-in",
        "title": "Ledgers pulled",
        "argv": [sys.executable, tool("pass-state.py"), "pull"],
        "timeout": NETWORK,
    },
    {
        "key": "setup",
        "title": "The setup is whole",
        "argv": [sys.executable, tool("intelligence-check.py"), "check"],
        "timeout": NETWORK,
    },
    {
        "key": "repos",
        "title": "Every repo held once",
        "argv": [sys.executable, tool("repo-preflight.py"), "--all"],
        "timeout": NETWORK,
    },
    {
        "key": "ledgers-out",
        "title": "Ledgers pushed",
        "argv": [sys.executable, tool("pass-state.py"), "push"],
        "timeout": NETWORK,
    },
]


def probe(phase):
    """Whether one phase holds, and the line that says why.

    A tool that is absent is a failing phase rather than a skipped one. The
    tree is meant to hold it, and counting the gap as nothing to report is how
    a setup that lost a tool goes on looking healthy.
    """
    if phase.get("fn"):
        return phase["fn"]()
    argv = phase["argv"]
    if not Path(argv[1]).is_file():
        return False, f"{Path(argv[1]).name} is not installed"
    code, text = run(argv, phase.get("timeout", QUICK))
    return code == 0, last_line(text)


def pass_once():
    """Every phase, in order, and what each one answered."""
    results = []
    for phase in PHASES:
        ok, detail = probe(phase)
        results.append({
            "key": phase["key"],
            "title": phase["title"],
            "ok": ok,
            "advisory": bool(phase.get("advisory")),
            "detail": detail,
        })
    return results


def findings(results):
    """The phases that are a person's problem, advisory ones included."""
    return [r for r in results if not r["ok"]]


def broken(results):
    """The phases that mean the setup itself is wrong."""
    return [r for r in results if not r["ok"] and not r["advisory"]]


def write_state(results):
    STATE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {"ran_at": stamp, "phases": results}
    (STATE / "last.json").write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def render(results):
    width = max(len(r["title"]) for r in results)
    lines = []
    for r in results:
        mark = "ok  " if r["ok"] else ("note" if r["advisory"] else "BROKEN")
        lines.append("  %-6s %-*s  %s" % (mark, width, r["title"], r["detail"]))
    return "\n".join(lines)


def cmd_run(_args):
    results = pass_once()
    write_state(results)
    hurt = findings(results)
    if not hurt:
        print("%d phase(s) read, all answered" % len(results))
        return 0
    print(render(results))
    print()
    for r in hurt:
        print("%s: %s" % (r["title"], r["detail"]))
    return 1 if broken(results) else 0


def cmd_inbound(_args):
    ok, detail = inbound()
    print(detail)
    return 0 if ok else 1


def agent_plist():
    """The launchd job, as launchd will hold it.

    `StartCalendarInterval` rather than `StartInterval` because this is a
    laptop. An interval counts seconds the machine was awake for and drifts
    every time the lid closes; a calendar entry names three wall-clock times
    and launchd runs a missed one on wake, which is the behaviour wanted from
    a machine that is closed more often than it is open.
    """
    return {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(TOOLS / "sentinel.py"), "run"],
        "StartCalendarInterval": [{"Hour": h, "Minute": MINUTE} for h in HOURS],
        "RunAtLoad": False,
        "StandardOutPath": str(STATE / "run.log"),
        "StandardErrorPath": str(STATE / "run.log"),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:"
                    "/usr/sbin:/sbin",
            "HOME": str(HOME),
        },
    }


def loaded():
    code, _ = run([LAUNCHCTL, "list", LABEL], QUICK)
    return code == 0


def cmd_install(_args):
    STATE.mkdir(parents=True, exist_ok=True)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_bytes(plistlib.dumps(agent_plist()))
    # bootout before bootstrap so a changed schedule actually takes; launchd
    # keeps the old job otherwise and the new plist sits on disk unread.
    uid = os.getuid()
    run([LAUNCHCTL, "bootout", f"gui/{uid}/{LABEL}"], QUICK)
    code, text = run([LAUNCHCTL, "bootstrap", f"gui/{uid}", str(PLIST)], QUICK)
    if code != 0:
        print("launchd refused the agent: %s" % (last_line(text) or code),
              file=sys.stderr)
        return 1
    print("wired: %s at %s past %s" %
          (LABEL, MINUTE, ", ".join(str(h) for h in HOURS)))
    return 0


def cmd_uninstall(_args):
    run([LAUNCHCTL, "bootout", f"gui/{os.getuid()}/{LABEL}"], QUICK)
    if PLIST.exists():
        PLIST.unlink()
    print("removed: %s" % LABEL)
    return 0


def cmd_check(_args):
    """Whether the agent is wired the way this file says it should be."""
    problems = []
    if not PLIST.is_file():
        problems.append("no plist at %s" % PLIST)
    else:
        held = plistlib.loads(PLIST.read_bytes())
        want = agent_plist()
        if held.get("StartCalendarInterval") != want["StartCalendarInterval"]:
            problems.append("the plist fires on a different schedule")
        if held.get("ProgramArguments") != want["ProgramArguments"]:
            problems.append("the plist runs something else")
    if not loaded():
        problems.append("launchd has not loaded %s" % LABEL)
    if problems:
        for line in problems:
            print(line)
        print("sentinel.py install settles this")
        return 1
    print("wired and loaded: %s at %s past %s" %
          (LABEL, MINUTE, ", ".join(str(h) for h in HOURS)))
    return 0


def cmd_status(_args):
    state = STATE / "last.json"
    if not state.is_file():
        print("no pass recorded yet")
        return 1
    payload = json.loads(state.read_text())
    print("last pass %s" % payload["ran_at"])
    print(render(payload["phases"]))
    print("agent: %s" % ("loaded" if loaded() else "NOT loaded"))
    return 0


COMMANDS = {
    "run": cmd_run,
    "install": cmd_install,
    "uninstall": cmd_uninstall,
    "status": cmd_status,
    "check": cmd_check,
    "inbound": cmd_inbound,
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=sorted(COMMANDS))
    args = parser.parse_args(argv)
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
