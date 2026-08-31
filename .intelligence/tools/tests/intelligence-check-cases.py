#!/usr/bin/env python3
"""Cases the setup check has to get right.

The check exists so one run says whether the whole setup is sound, which makes
its own failure modes the expensive ones: a probe that cannot be taken reading
as a pass, a repair reported without being re-probed, or a machine being asleep
failing a run that is otherwise clean. Each of those turns the report into
something that gets ignored, and an ignored report is worse than none.

Every run pins the tools directory through INTELLIGENCE_TOOLS_DIR and HOME
through the fixture, so no case reads this machine's real tools or git config.

  intelligence-check-cases.py    run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "intelligence-check.py")

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


def stub(path, code, text="", writes=None):
    """A tool that reports what a case needs it to report.

    `writes` names a file the stub creates, which is how a repair is told apart
    from a probe that happened to be run twice: the probe reads for the file the
    repair leaves behind.
    """
    body = ["#!/usr/bin/env python3", "import sys, pathlib"]
    if writes:
        body.append(f"pathlib.Path({str(writes)!r}).write_text('done')")
    body.append(f"print({text!r})")
    body.append(f"sys.exit({code})")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n")
    path.chmod(0o755)


def gated(path, gate, text_ok, text_bad):
    """A probe that passes only once `gate` exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, pathlib\n"
        f"ok = pathlib.Path({str(gate)!r}).exists()\n"
        f"print({text_ok!r} if ok else {text_bad!r})\n"
        "sys.exit(0 if ok else 1)\n")
    path.chmod(0o755)


ALL_TOOLS = ["intelligence-naming.py", "config-sync.py", "pass-state.py",
             "routine-sync.py", "ai-attribution-guard.py", "pi-heartbeat.py",
             "remote-access.py", "hygiene-check.py", "sentinel.py",
             "routine-health.py", "stranded.py",
             "skills-routines-page.py"]


def fixture(root, hooks=True, executable=True):
    """A tools directory where every probe passes, and a git config to match."""
    tools = root / "tools"
    for name in ALL_TOOLS:
        stub(tools / name, 0, f"{name} fine")
    stub(tools / "tests" / "cases.py", 0, "0 failure(s)")
    home = root / "home"
    hook_dir = home / "git-hooks"
    if hooks:
        hook_dir.mkdir(parents=True, exist_ok=True)
        for hook in ("pre-commit", "commit-msg", "pre-push"):
            target = hook_dir / hook
            target.write_text("#!/bin/sh\nexit 0\n")
            target.chmod(0o755 if executable else 0o644)
    home.mkdir(parents=True, exist_ok=True)
    (home / ".gitconfig").write_text(
        f"[core]\n\thooksPath = {hook_dir}\n")
    return tools, home


def run(tools, home, *argv):
    env = dict(os.environ)
    env["INTELLIGENCE_TOOLS_DIR"] = str(tools)
    env["HOME"] = str(home)
    env.pop("GIT_CONFIG_GLOBAL", None)
    done = subprocess.run([sys.executable, str(TARGET), *argv],
                          capture_output=True, text=True, env=env, check=False)
    return done.returncode, done.stdout + done.stderr


def case_a_sound_tree_reports_whole(root):
    tools, home = fixture(root)
    code, out = run(tools, home, "check")
    check("a sound tree exits clean", code, 0)
    contains("a sound tree says so", out, "the setup is whole")
    missing("a sound tree names nothing broken", out, "still broken")


def case_a_broken_check_fails_the_run(root):
    tools, home = fixture(root)
    stub(tools / "routine-sync.py", 1, "a routine has no checked-in copy")
    code, out = run(tools, home, "check")
    check("a broken check fails the run", code, 1)
    contains("the broken check is named", out, "still broken: routines")
    contains("the reason is carried", out, "no checked-in copy")


def case_an_asleep_machine_does_not_fail_the_run(root):
    tools, home = fixture(root)
    stub(tools / "remote-access.py", 1, "the desktop is not answering")
    code, out = run(tools, home, "check")
    check("an advisory failure still exits clean", code, 0)
    contains("it is reported", out, "not answering")
    missing("it is not called broken", out, "still broken")


def case_an_absent_tool_fails_rather_than_skips(root):
    tools, home = fixture(root)
    (tools / "pass-state.py").unlink()
    code, out = run(tools, home, "check")
    check("an absent tool fails its check", code, 1)
    contains("the absence is the reason", out, "pass-state.py is not installed")


def case_a_repair_is_probed_again(root):
    tools, home = fixture(root)
    gate = root / "published"
    gated(tools / "config-sync.py", gate, "in step", "files differ")
    stub(tools / "config-sync-repair.py", 0, "pushed", writes=gate)
    code, out = run(tools, home, "check")
    check("the check fails before the repair", code, 1)
    missing("nothing is repaired by a probe", out, "repaired:")


def case_fix_repairs_and_then_passes(root):
    tools, home = fixture(root)
    gate = root / "published"
    gated(tools / "config-sync.py", gate, "in step", "files differ")
    # The repair verb is the tool's own second argument, so the stub answers
    # both roles: probing reads the gate, and any invocation writes it.
    (tools / "config-sync.py").write_text(
        "#!/usr/bin/env python3\n"
        "import sys, pathlib\n"
        f"gate = pathlib.Path({str(gate)!r})\n"
        "if len(sys.argv) > 1 and sys.argv[1] == 'publish':\n"
        "    gate.write_text('done')\n"
        "    print('1 pushed')\n"
        "    sys.exit(0)\n"
        "print('in step' if gate.exists() else 'files differ')\n"
        "sys.exit(0 if gate.exists() else 1)\n")
    (tools / "config-sync.py").chmod(0o755)
    code, out = run(tools, home, "fix")
    check("fix settles the check", code, 0)
    contains("the repair is named", out, "repaired: config")
    contains("the tree is whole after it", out, "the setup is whole")


def case_a_check_with_no_repair_stays_broken(root):
    tools, home = fixture(root)
    stub(tools / "tests" / "cases.py", 1, "2 failure(s)")
    code, out = run(tools, home, "fix")
    check("fix cannot settle what declares no repair", code, 1)
    contains("it is still named", out, "still broken: cases")
    missing("nothing claims to have repaired it", out, "repaired: cases")


def case_a_hook_without_its_bit_is_caught(root):
    tools, home = fixture(root, executable=False)
    code, out = run(tools, home, "check")
    check("a hook stored without its bit fails", code, 1)
    contains("the check is named", out, "still broken: attribution")
    contains("the reason is the bit", out, "not executable")


def case_no_hooks_path_is_caught(root):
    tools, home = fixture(root, hooks=False)
    (home / ".gitconfig").write_text("[user]\n\tname = nobody\n")
    code, out = run(tools, home, "check")
    check("an unwired guard fails", code, 1)
    contains("the reason is the missing path", out, "core.hooksPath")


def case_json_carries_every_check(root):
    tools, home = fixture(root)
    code, out = run(tools, home, "check", "--json")
    check("json exits clean on a sound tree", code, 0)
    payload = json.loads(out)
    check("every check is present", len(payload), 15)
    check("each carries a verdict",
          all(isinstance(r["ok"], bool) for r in payload), True)
    check("each carries its key",
          sorted(r["key"] for r in payload),
          ["attribution", "cases", "config", "hosts", "hygiene", "inbound",
           "ledgers", "naming", "pipeline", "routine-health", "routine-mirror", "routines",
           "sentinel", "skills-page", "stranded"])


def case_an_unknown_verb_is_refused(root):
    tools, home = fixture(root)
    code, _ = run(tools, home, "publish-everything")
    check("an unknown verb is refused", code, 2)


def main():
    for case in (case_a_sound_tree_reports_whole,
                 case_a_broken_check_fails_the_run,
                 case_an_asleep_machine_does_not_fail_the_run,
                 case_an_absent_tool_fails_rather_than_skips,
                 case_a_repair_is_probed_again,
                 case_fix_repairs_and_then_passes,
                 case_a_check_with_no_repair_stays_broken,
                 case_a_hook_without_its_bit_is_caught,
                 case_no_hooks_path_is_caught,
                 case_json_carries_every_check,
                 case_an_unknown_verb_is_refused):
        with tempfile.TemporaryDirectory() as tmp:
            case(Path(tmp))
    if FAILURES:
        for f in FAILURES:
            print(f"FAIL {f}", file=sys.stderr)
        return 1
    print("intelligence-check: all cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
