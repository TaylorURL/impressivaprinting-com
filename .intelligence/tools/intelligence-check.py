#!/usr/bin/env python3
"""Whether this machine's intelligence setup is whole, and what to run when it is not.

The setup is a tree of tools, skills and ledgers that each answer for one thing
and none of which answer for the whole. A tree can be named correctly, pass its
own case suites, and still be a version behind what a cloud container installs;
the ledgers can be current here and unpublished everywhere else. So the health
of the setup is a question no single tool holds the answer to, and asking it
piecemeal is how a broken half goes unnoticed between the halves that work.

Every check is a probe that reads and changes nothing, so a run says what is
true before anything acts on it. `fix` then runs the repair each failing check
declares and probes again, which is what separates a check that was repaired
from one that was merely rerun.

  intelligence-check.py check    probe everything, report, fail on a broken check
  intelligence-check.py fix      probe, repair what declares a repair, probe again
  intelligence-check.py list     the checks and what each one runs
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TOOLS = Path(os.environ.get("INTELLIGENCE_TOOLS_DIR")
             or Path(__file__).resolve().parent)

# A probe that reaches the network answers on a different scale to one reading
# a file, and a run that hangs on an asleep machine reports nothing at all.
QUICK = 120
NETWORK = 420


def tool(name):
    return str(TOOLS / name)


# Each check names the probe that decides it, the repair that can settle it
# without a person, and whether a failure is a broken setup or a fact worth
# reporting. `advisory` covers what depends on a machine being awake: it is
# reported and never fails the run, because an asleep machine is not a fault in
# this tree.
CHECKS = [
    {
        "key": "naming",
        "title": "Names, hooks and aliases",
        "probe": [sys.executable, tool("intelligence-naming.py"), "verify"],
        "repair": [sys.executable, tool("intelligence-naming.py"), "install"],
        "timeout": QUICK,
    },
    {
        "key": "config",
        "title": "Cloud would load what this machine holds",
        "probe": [sys.executable, tool("config-sync.py"), "check"],
        "repair": [sys.executable, tool("config-sync.py"), "publish"],
        "timeout": NETWORK,
    },
    {
        "key": "ledgers",
        "title": "Pass ledgers and day plans carried",
        "probe": [sys.executable, tool("pass-state.py"), "status"],
        "repair": [sys.executable, tool("pass-state.py"), "push"],
        "timeout": NETWORK,
    },
    {
        "key": "hygiene",
        "title": "Home layout, READMEs, editor config, retired names",
        "probe": [sys.executable, tool("hygiene-check.py"), "check"],
        "repair": [sys.executable, tool("hygiene-check.py"), "fix"],
        "timeout": NETWORK,
    },
    {
        "key": "stranded",
        "title": "Work left behind in a checkout",
        "probe": [sys.executable, tool("stranded.py"), "report"],
        "repair": [sys.executable, tool("stranded.py"), "repair"],
        "timeout": NETWORK,
    },
    {
        "key": "routines",
        "title": "Scheduled routines accounted for",
        "probe": [sys.executable, tool("routine-sync.py"), "check"],
        "repair": None,
        "timeout": QUICK,
    },
    {
        "key": "routine-mirror",
        "title": "Machines run the copy held here",
        "probe": [sys.executable, tool("routine-sync.py"), "mirrored"],
        "repair": None,
        "timeout": NETWORK,
    },
    {
        "key": "routine-health",
        "title": "Routines actually running",
        "probe": [sys.executable, tool("routine-health.py"), "check"],
        "repair": None,
        "timeout": QUICK,
    },
    {
        "key": "skills-page",
        "title": "Skills and routines page current",
        "probe": [sys.executable, tool("skills-routines-page.py"), "status"],
        "repair": None,
        "timeout": QUICK,
    },
    {
        "key": "cases",
        "title": "Tool case suites",
        "probe": [sys.executable, tool("tests/cases.py"), "all"],
        "repair": None,
        "timeout": NETWORK,
    },
    {
        "key": "attribution",
        "title": "Attribution guard wired",
        "probe_fn": "attribution_wired",
        "repair": [sys.executable, tool("ai-attribution-guard.py"), "install"],
        "timeout": QUICK,
    },
    {
        "key": "pipeline",
        "title": "Error pipeline alive",
        "probe": [sys.executable, tool("pi-heartbeat.py"), "check"],
        "repair": None,
        "timeout": NETWORK,
        "advisory": True,
    },
    {
        "key": "hosts",
        "title": "Machines reachable",
        "probe_fn": "machines_reachable",
        "repair": None,
        "timeout": NETWORK,
        "advisory": True,
    },
    {
        "key": "inbound",
        "title": "This machine reachable from the Pi",
        "probe": [sys.executable, tool("sentinel.py"), "inbound"],
        "repair": None,
        "timeout": NETWORK,
        "advisory": True,
    },
    {
        "key": "sentinel",
        "title": "The local watch is wired",
        "probe": [sys.executable, tool("sentinel.py"), "check"],
        "repair": [sys.executable, tool("sentinel.py"), "install"],
        "timeout": QUICK,
    },
]


def attribution_wired():
    """Whether the hooks the attribution guard installs are actually in place.

    The guard is invoked by git rather than by a person, so the thing to read
    is the wiring git resolves: a global hooks path pointing into this tree,
    holding the three hooks that answer at commit and at push, each executable.
    A hook stored without its bit is invoked and does nothing, which reads
    exactly like a repository with no attribution in it.
    """
    code, path = run(["git", "config", "--global", "core.hooksPath"], QUICK)
    if code != 0 or not path:
        return False, "no global core.hooksPath is set"
    where = Path(path).expanduser()
    if not where.is_dir():
        return False, f"core.hooksPath {path} is not a directory"
    missing = []
    for hook in ("pre-commit", "commit-msg", "pre-push"):
        target = where / hook
        if not target.is_file():
            missing.append(f"{hook} absent")
        elif not os.access(target, os.X_OK):
            missing.append(f"{hook} not executable")
    if missing:
        return False, ", ".join(missing)
    return True, f"three hooks under {path}"


def machines_reachable():
    """How many of the other machines answer, and which do not.

    The probe prints a row per machine, so the last line of it names one
    machine rather than the answer. What decides this check is the count and
    the names of whatever is out of reach.
    """
    argv = [sys.executable, tool("remote-access.py"), "hosts"]
    if not Path(argv[1]).is_file():
        return False, "remote-access.py is not installed"
    code, text = run(argv, NETWORK)
    if code != 0:
        return False, text.splitlines()[-1] if text else "the probe failed"
    rows = [ln for ln in text.splitlines() if ln.strip()]
    away = [ln.split()[0] for ln in rows if "out of reach" in ln]
    if away:
        return True, f"{len(rows) - len(away)} of {len(rows)} answer, " \
                     f"{', '.join(away)} out of reach"
    return True, f"all {len(rows)} answer"


def run(argv, timeout):
    """A probe or a repair, reduced to what decides it: the code and the text."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return 1, f"timed out after {timeout}s"
    except OSError as err:
        return 1, str(err)
    text = (done.stdout or "") + (done.stderr or "")
    return done.returncode, text.strip()


def probe(check):
    """Whether one check passes, and the line that says why.

    A tool that is absent is a failing check rather than a skipped one: the
    setup is meant to hold it, and treating the gap as nothing to report is how
    a tree that lost a tool goes on looking healthy.
    """
    if check.get("probe_fn"):
        return globals()[check["probe_fn"]]()
    argv = check["probe"]
    if not Path(argv[1]).is_file():
        return False, f"{Path(argv[1]).name} is not installed"
    code, text = run(argv, check.get("timeout", QUICK))
    line = text.splitlines()[-1] if text else ""
    return code == 0, line


def report(results, as_json):
    if as_json:
        print(json.dumps(results, indent=2))
        return
    width = max(len(r["title"]) for r in results)
    for r in results:
        if r["ok"]:
            mark = "ok  "
        elif r.get("advisory"):
            mark = "note"
        else:
            mark = "FAIL"
        print(f"  {mark}  {r['title']:<{width}}  {r['detail']}")


def survey(repair):
    """Probe every check, repair what declares one, and probe those again."""
    results = []
    for check in CHECKS:
        ok, detail = probe(check)
        repaired = False
        if not ok and repair and check.get("repair"):
            code, text = run(check["repair"], check.get("timeout", QUICK))
            repaired = True
            ok, detail = probe(check)
            if not ok and text:
                detail = f"{detail} (repair said: {text.splitlines()[-1]})"
        results.append({
            "key": check["key"],
            "title": check["title"],
            "ok": ok,
            "advisory": bool(check.get("advisory")),
            "repaired": repaired,
            "detail": detail,
        })
    return results


def main(argv):
    verb = argv[0] if argv else "check"
    as_json = "--json" in argv

    if verb == "list":
        for check in CHECKS:
            fix = " ".join(Path(a).name for a in check["repair"][1:]) \
                if check.get("repair") else "no repair"
            fix = fix or "no repair"
            print(f"  {check['key']:<12} {check['title']:<44} {fix}")
        return 0

    if verb not in ("check", "fix"):
        print(__doc__.strip().splitlines()[-3], file=sys.stderr)
        return 2

    results = survey(repair=(verb == "fix"))
    report(results, as_json)

    broken = [r for r in results if not r["ok"] and not r["advisory"]]
    if not as_json:
        fixed = [r for r in results if r["repaired"] and r["ok"]]
        if fixed:
            print(f"\nrepaired: {', '.join(r['key'] for r in fixed)}")
        if broken:
            print(f"\nstill broken: {', '.join(r['key'] for r in broken)}")
        else:
            print("\nthe setup is whole")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
