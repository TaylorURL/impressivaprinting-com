#!/usr/bin/env python3
"""Cases the local watch has to get right.

This script is fired by launchd with nobody watching, which makes its failure
modes the quiet ones. A phase whose tool is missing must fail rather than be
skipped, or a tree that lost a tool goes on reporting clean. A laptop with its
lid shut must not fail the run, or the report becomes noise and gets ignored.
And a run that found something must exit non-zero, because the exit code is the
only thing launchd records.

The plist matters as much as the pass. An agent wired to the wrong schedule, or
to a path that no longer exists, is an agent that never fires -- and a watch
that never fires reports exactly what a clean one does.

Every run pins the tools directory, the state directory, HOME and launchctl
through the fixture, so no case reads this machine's real tree or talks to the
real launchd.

  sentinel-cases.py    run them
"""
from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "sentinel.py")

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


def stub(path, code, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n"
                    "import sys\n"
                    f"print({text!r})\n"
                    f"sys.exit({code})\n")
    path.chmod(0o755)


# Every tool the pass shells out to. `remote-access.py` is here because the
# inbound probe reaches for it even when no case exercises the probe.
ALL_TOOLS = ["pass-state.py", "intelligence-check.py", "repo-preflight.py",
             "remote-access.py"]


def fixture(root):
    """A tree where every phase passes, and a launchctl that says so."""
    tools = root / "tools"
    for name in ALL_TOOLS:
        stub(tools / name, 0, f"{name} fine")
    launchctl = root / "launchctl"
    stub(launchctl, 0, "loaded")
    state = root / "state"
    home = root / "home"
    home.mkdir(parents=True, exist_ok=True)
    return tools, home, state, launchctl


def run(tools, home, state, launchctl, *argv):
    env = dict(os.environ)
    env["INTELLIGENCE_TOOLS_DIR"] = str(tools)
    env["INTELLIGENCE_SENTINEL_STATE"] = str(state)
    env["INTELLIGENCE_SENTINEL_LAUNCHCTL"] = str(launchctl)
    env["HOME"] = str(home)
    done = subprocess.run([sys.executable, str(TARGET), *argv],
                          capture_output=True, text=True, env=env, check=False)
    return done.returncode, done.stdout + done.stderr


def case_a_clean_pass_says_little(root):
    tools, home, state, ctl = fixture(root)
    code, out = run(tools, home, state, ctl, "run")
    check("a clean pass exits clean", code, 0)
    contains("it says how many it read", out, "all answered")
    missing("it names no phase", out, "BROKEN")


def case_a_broken_phase_fails_the_run(root):
    tools, home, state, ctl = fixture(root)
    stub(tools / "repo-preflight.py", 1, "cryptofort is held 2 times")
    code, out = run(tools, home, state, ctl, "run")
    check("a broken phase fails the run", code, 1)
    contains("the phase is named", out, "Every repo held once")
    contains("the reason is carried", out, "held 2 times")


def case_an_absent_tool_fails_rather_than_skips(root):
    tools, home, state, ctl = fixture(root)
    (tools / "intelligence-check.py").unlink()
    code, out = run(tools, home, state, ctl, "run")
    check("an absent tool fails the run", code, 1)
    contains("it says which", out, "intelligence-check.py is not installed")


def case_the_pass_is_recorded_either_way(root):
    tools, home, state, ctl = fixture(root)
    stub(tools / "repo-preflight.py", 1, "held twice")
    run(tools, home, state, ctl, "run")
    payload = json.loads((state / "last.json").read_text())
    check("every phase is recorded", len(payload["phases"]), 4)
    check("the finding is recorded",
          [p["ok"] for p in payload["phases"] if p["key"] == "repos"], [False])
    contains("the run is stamped", payload["ran_at"], "T")


def case_the_ledgers_are_pushed_after_a_finding(root):
    """A pass that found something still has to put the ledgers back.

    The pull is the first phase and the push is the last. A run that stopped at
    the first finding would leave this machine holding marks no other machine
    can see, and the next machine to run would redo the work they record.
    """
    tools, home, state, ctl = fixture(root)
    stub(tools / "intelligence-check.py", 1, "still broken: config")
    run(tools, home, state, ctl, "run")
    payload = json.loads((state / "last.json").read_text())
    keys = [p["key"] for p in payload["phases"]]
    check("the push still ran", keys[-1], "ledgers-out")
    check("and it answered",
          [p["ok"] for p in payload["phases"] if p["key"] == "ledgers-out"],
          [True])


def case_status_before_any_pass(root):
    tools, home, state, ctl = fixture(root)
    code, out = run(tools, home, state, ctl, "status")
    check("nothing recorded is not clean", code, 1)
    contains("it says so plainly", out, "no pass recorded yet")


def case_install_writes_the_schedule_this_file_declares(root):
    tools, home, state, ctl = fixture(root)
    code, out = run(tools, home, state, ctl, "install")
    check("install succeeds", code, 0)
    plist = home / "Library" / "LaunchAgents" / "com.intelligence.sentinel.plist"
    held = plistlib.loads(plist.read_bytes())
    check("it fires three times a day",
          len(held["StartCalendarInterval"]), 3)
    check("at the declared minute",
          sorted({e["Minute"] for e in held["StartCalendarInterval"]}), [47])
    check("eight hours apart",
          sorted(e["Hour"] for e in held["StartCalendarInterval"]), [3, 11, 19])
    check("it runs the pass", held["ProgramArguments"][-1], "run")
    missing("it does not fire on load", str(held["RunAtLoad"]), "True")


def case_check_catches_an_unwired_agent(root):
    tools, home, state, ctl = fixture(root)
    code, out = run(tools, home, state, ctl, "check")
    check("no plist is not wired", code, 1)
    contains("it says what is missing", out, "no plist at")
    contains("it names the way out", out, "sentinel.py install")


def case_check_catches_a_drifted_plist(root):
    """A plist left behind by an older build is the failure that hides.

    launchd holds what it was given, so a schedule changed in this file and
    never reinstalled leaves an agent firing on the old one. It is loaded, it
    is running, and it is running the wrong thing.
    """
    tools, home, state, ctl = fixture(root)
    run(tools, home, state, ctl, "install")
    plist = home / "Library" / "LaunchAgents" / "com.intelligence.sentinel.plist"
    held = plistlib.loads(plist.read_bytes())
    held["StartCalendarInterval"] = [{"Hour": 2, "Minute": 0}]
    plist.write_bytes(plistlib.dumps(held))
    code, out = run(tools, home, state, ctl, "check")
    check("a drifted schedule is caught", code, 1)
    contains("it says which way it drifted", out, "different schedule")


def case_check_catches_an_unloaded_agent(root):
    tools, home, state, ctl = fixture(root)
    run(tools, home, state, ctl, "install")
    stub(ctl, 1, "no such job")
    code, out = run(tools, home, state, ctl, "check")
    check("a plist launchd never took is caught", code, 1)
    contains("it says so", out, "has not loaded")


def case_a_wired_agent_passes(root):
    tools, home, state, ctl = fixture(root)
    run(tools, home, state, ctl, "install")
    code, out = run(tools, home, state, ctl, "check")
    check("a wired agent is clean", code, 0)
    contains("it says when it fires", out, "47 past")


def case_uninstall_removes_it(root):
    tools, home, state, ctl = fixture(root)
    run(tools, home, state, ctl, "install")
    code, _ = run(tools, home, state, ctl, "uninstall")
    check("uninstall succeeds", code, 0)
    plist = home / "Library" / "LaunchAgents" / "com.intelligence.sentinel.plist"
    check("the plist is gone", plist.exists(), False)


def case_inbound_tells_a_refusal_from_a_silence(root):
    """The two ways in fail for opposite reasons and take opposite fixes.

    A refused login is a machine that answered: it is awake, on the tailnet,
    and missing a key. A silence is a machine that is not there at all. Calling
    both `out of reach` sends somebody to check the network when the fix is a
    key, so the probe has to separate them.
    """
    tools, home, state, ctl = fixture(root)
    stub(tools / "remote-access.py", 255,
         "sunday@trenton-mac: Permission denied (publickey,password)")
    code, out = run(tools, home, state, ctl, "inbound")
    check("a refusal is not clean", code, 1)
    contains("it says the machine answered", out, "cannot log in")

    stub(tools / "remote-access.py", 255, "ssh: connect to host ... timed out")
    code, out = run(tools, home, state, ctl, "inbound")
    check("a silence is not clean", code, 1)
    contains("it says it could not be reached", out, "cannot reach this machine")


def case_inbound_reads_the_answer(root):
    tools, home, state, ctl = fixture(root)
    stub(tools / "remote-access.py", 0, "reached\ntrenton-mac")
    code, out = run(tools, home, state, ctl, "inbound")
    check("a reached machine is clean", code, 0)
    contains("it says so", out, "can open a shell here")


def case_an_unknown_verb_is_refused(root):
    tools, home, state, ctl = fixture(root)
    code, _ = run(tools, home, state, ctl, "watch-everything")
    check("an unknown verb is refused", code, 2)


def main():
    for case in (case_a_clean_pass_says_little,
                 case_a_broken_phase_fails_the_run,
                 case_an_absent_tool_fails_rather_than_skips,
                 case_the_pass_is_recorded_either_way,
                 case_the_ledgers_are_pushed_after_a_finding,
                 case_status_before_any_pass,
                 case_install_writes_the_schedule_this_file_declares,
                 case_check_catches_an_unwired_agent,
                 case_check_catches_a_drifted_plist,
                 case_check_catches_an_unloaded_agent,
                 case_a_wired_agent_passes,
                 case_uninstall_removes_it,
                 case_inbound_tells_a_refusal_from_a_silence,
                 case_inbound_reads_the_answer,
                 case_an_unknown_verb_is_refused):
        with tempfile.TemporaryDirectory() as tmp:
            case(Path(tmp))
    if FAILURES:
        for line in FAILURES:
            print("FAIL " + line)
        return 1
    print("sentinel: all cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
