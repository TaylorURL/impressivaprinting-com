#!/usr/bin/env python3
"""Cases the case runner has to get right.

Every other tool's protection runs through this one, and the way it fails is
quiet: a run that ends non-zero while the last line it printed reads clean.
That line is the whole report for anything reading a probe's tail, so the
contract held here is that the exit code and the last line always say the same
thing, whichever way a suite went wrong -- reported failures, a death before
any verdict, a suite that never returns, or one answering for a tool the tree
no longer holds.

  cases-cases.py        run them
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ANSWERS_FOR = ["tools/tests/cases.py"]

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent / "cases.py")

FAILURES: list[str] = []

PASSING = "print('0 failure(s)')\n"
REPORTING_FAILURE = ("import sys\n"
                     "print('FAIL something: got 1, want 2')\n"
                     "print('1 failure(s)')\n"
                     "sys.exit(1)\n")
DYING = "import a_module_that_is_not_installed\n"
NEVER_RETURNING = "import time\ntime.sleep(600)\n"


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def staged(root, timeout=3):
    """A throwaway tree holding the runner under test, on a short clock.

    The hang case has to wait out the runner's own timeout, so the copy under
    test carries a few seconds rather than a few minutes. A substitution that
    matched nothing is fatal: the case would otherwise sit for the real timeout
    and report a pass at the end of it.
    """
    text = TARGET.read_text(encoding="utf-8")
    patched, swaps = re.subn(r"^TIMEOUT = \d+$", "TIMEOUT = %d" % timeout,
                             text, count=1, flags=re.M)
    if not swaps:
        raise SystemExit("cases.py declares no TIMEOUT constant, so the suite "
                         "that never returns cannot be timed")
    tests = root / "tools" / "tests"
    tests.mkdir(parents=True)
    runner = tests / "cases.py"
    runner.write_text(patched, encoding="utf-8")
    # The runner starts every suite through the sandbox, found beside its own
    # tools first and in the installed tree after. A checkout is where there is
    # no installed tree, so the copy carries its own rather than reading the
    # machine's -- which is the difference between this suite passing here and
    # passing anywhere.
    (tests.parent / "suite-sandbox.py").write_bytes(
        (TARGET.parent.parent / "suite-sandbox.py").read_bytes())
    return runner


def suite(runner, name, body, subject=True):
    """One fixture suite, and the tool it answers for where it has one."""
    tools = runner.parent.parent
    if subject:
        (tools / ("%s.py" % name)).write_text("#!/usr/bin/env python3\n",
                                              encoding="utf-8")
    (runner.parent / ("%s-cases.py" % name)).write_text(body, encoding="utf-8")


def run_all(runner):
    """The runner's exit code and the last line anything reading its tail sees."""
    done = subprocess.run([sys.executable, str(runner), "all"],
                          cwd=str(runner.parent.parent.parent),
                          capture_output=True, text=True, timeout=180)
    text = ((done.stdout or "") + (done.stderr or "")).strip()
    return done.returncode, (text.splitlines()[-1] if text else "")


def case(label, bodies, want_code, wants):
    """Stage one tree, run it, and hold the exit code and last line together."""
    with tempfile.TemporaryDirectory() as root:
        runner = staged(Path(root))
        for name, (body, has_subject) in bodies.items():
            suite(runner, name, body, subject=has_subject)
        code, last = run_all(runner)
    check("%s: exit code" % label, code, want_code)
    for want in wants:
        check("%s: the last line names %r" % (label, want), want in last, True)
    if want_code:
        # The defect this whole suite answers to: a non-zero run whose last line
        # reads like a sound one, which is every line a single suite prints
        # about itself.
        check("%s: a non-zero run cannot end on a clean-reading line" % label,
              last.startswith("BLOCKED "), True)
    return last


def main():
    case("a clean run", {"good": (PASSING, True)}, 0, ["suite(s) pass"])
    with tempfile.TemporaryDirectory() as root:
        runner = staged(Path(root))
        suite(runner, "good", PASSING)
        code, last = run_all(runner)
        check("a clean run does not read as blocked", "BLOCKED" in last, False)

    case("a suite reporting failures",
         {"good": (PASSING, True), "bad": (REPORTING_FAILURE, True)},
         1, ["failed", "bad"])

    case("a suite that dies before any verdict",
         {"good": (PASSING, True), "dies": (DYING, True)},
         1, ["never reported", "dies", "ModuleNotFoundError"])

    case("a suite that never returns",
         {"good": (PASSING, True), "hangs": (NEVER_RETURNING, True)},
         1, ["never reported", "hangs", "no verdict inside"])

    case("a suite answering for a tool the tree does not hold",
         {"good": (PASSING, True), "ghost": (PASSING, False)},
         1, ["unbound", "ghost"])

    last = case("every way of going wrong at once",
                {"good": (PASSING, True), "bad": (REPORTING_FAILURE, True),
                 "dies": (DYING, True), "ghost": (PASSING, False)},
                1, ["failed", "never reported", "unbound"])
    check("the count covers every suite, sound and not", "3 of 4 suite(s)" in last, True)

    for f in FAILURES:
        print("FAIL %s" % f)
    print("cases.py: %d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
