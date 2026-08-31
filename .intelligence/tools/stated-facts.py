#!/usr/bin/env python3
"""Facts about this setup, produced by reading it rather than by being typed.

A rule with a mechanism is enforced. A fact about the setup written into prose
is enforced by nobody, so it drifts from the thing it describes and is then read
as true. Every count here is computed from the registry, the skill directory and
the tool directory, and every sentence that states one is checked against it.

  render                what is actually true, one fact per line
  check                 exit 2 when a document disagrees with the setup
  guard-stop            the same check, as a hook

INTELLIGENCE_ALLOW_STALE_FACT=1 lets a run finish over a disagreement.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
INTELLIGENCE = HOME / ".intelligence"
MIRROR = INTELLIGENCE / "state" / ".config-sync-repo"
AGREEMENT = INTELLIGENCE / "INTELLIGENCE.md"

WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
         7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
         12: "twelve", 13: "thirteen"}


# What a fact reads when its source could not be reached. It is not zero, and
# it is not a disagreement: a container holding a partial mirror clone, and no
# repository REST, can read neither the registry nor the routine files, and a
# count invented for that case is a count the documents get asked to match.
UNREADABLE = object()


def registry():
    """The routine list, from the mirror clone or from GitHub.

    UNREADABLE where neither answers, so the caller can tell a setup with no
    routines from a box that cannot see the ones there are.
    """
    local = MIRROR / "routines" / "registry.json"
    if local.exists():
        return json.loads(local.read_text())
    done = subprocess.run(
        ["gh", "api", "repos/bradley-t-t/intelligence/contents/routines/registry.json",
         "--jq", ".content"], capture_output=True, text=True)
    if done.returncode != 0:
        return UNREADABLE
    import base64
    return json.loads(base64.b64decode(done.stdout).decode())


def phase_count(name):
    """Phases in one routine, counted the way the run itself counts them.

    A phase is a heading that declares an enforce marker. A heading without one
    is prose, and a run that treats it as a phase fails on a gate nobody wrote.
    """
    local = MIRROR / "routine" / name
    text = ""
    if local.exists():
        text = local.read_text(errors="ignore")
    else:
        done = subprocess.run(
            ["gh", "api", "repos/bradley-t-t/intelligence/contents/routine/%s" % name,
             "--jq", ".content"], capture_output=True, text=True)
        if done.returncode == 0:
            import base64
            text = base64.b64decode(done.stdout).decode(errors="ignore")
    if not text:
        return UNREADABLE
    blocks = re.split(r"^## ", text, flags=re.M)[1:]
    return sum(1 for b in blocks if "enforce" in b)


def routines():
    raw = registry()
    if raw is UNREADABLE:
        return UNREADABLE
    if isinstance(raw, dict):
        raw = raw.get("routines") or list(raw.values())
    return [r for r in raw if isinstance(r, dict)]


def _count_dirs(path):
    return len([d for d in path.iterdir() if d.is_dir()]) if path.exists() else 0


def facts():
    """Every countable claim the documents make, as it actually stands."""
    rs = routines()
    if rs is UNREADABLE:
        return {
            "routines.total": UNREADABLE,
            "routines.cloud": UNREADABLE,
            "routines.pi": UNREADABLE,
            "routines.mac": UNREADABLE,
            "sentinel.schedule": UNREADABLE,
            "skills": _count_dirs(INTELLIGENCE / "skills"),
            "tools": len(list((INTELLIGENCE / "tools").glob("*.py"))),
            "cases": len(list((INTELLIGENCE / "tools" / "tests").glob("*-cases.py"))),
            "maintenance.phases": phase_count("daily-maintenance.md"),
            "checklists": _count_dirs(INTELLIGENCE / "checklists"),
        }
    hosts = {}
    for r in rs:
        where = r.get("where") or r.get("host") or r.get("runs_on") or "unknown"
        hosts[where] = hosts.get(where, 0) + 1
    sentinel = next((r for r in rs if (r.get("name") or "").lower() == "sentinel"), {})
    skills = INTELLIGENCE / "skills"
    checklists = INTELLIGENCE / "checklists"
    tools = INTELLIGENCE / "tools"
    return {
        "routines.total": len(rs),
        "routines.cloud": hosts.get("cloud", 0),
        "routines.pi": hosts.get("pi", 0),
        "routines.mac": hosts.get("mac", 0),
        "sentinel.schedule": sentinel.get("schedule") or sentinel.get("cron") or "",
        "skills": len([d for d in skills.iterdir() if d.is_dir()]) if skills.exists() else 0,
        "tools": len(list(tools.glob("*.py"))) if tools.exists() else 0,
        "cases": len(list((tools / "tests").glob("*-cases.py"))) if tools.exists() else 0,
        "maintenance.phases": phase_count("daily-maintenance.md"),
        "checklists": len([d for d in checklists.iterdir() if d.is_dir()])
        if checklists.exists() else 0,
    }


def number(value):
    """Both spellings of a count, since prose uses one and a table the other."""
    return {str(value), WORDS.get(value, "")} - {""}


# Each rule finds a sentence that states a count and names the fact it must
# agree with. A pattern that matches nothing is itself a disagreement: the
# sentence it was written against has changed shape, and a rule that quietly
# stops applying is worse than no rule, because the check still reports clean.
RULES = (
    (AGREEMENT, r"(\w+) on the Pi and (\w+) on the Mac",
     ("routines.pi", "routines.mac")),
    (AGREEMENT, r"(\w+) run on their own:", ("routines.total",)),
    (AGREEMENT, r"Sentinel, `([^`]+)`", ("sentinel.schedule",)),
    (AGREEMENT, r"The pass over every owned repo, (\w+) phases",
     ("maintenance.phases",)),
)


def disagreements():
    truth = facts()
    out = []
    for path, pattern, keys in RULES:
        if not path.exists():
            continue
        text = path.read_text(errors="ignore")
        found = re.search(pattern, text)
        if not found:
            out.append("%s no longer carries the sentence stating %s, so it is "
                       "unchecked" % (path.name, " and ".join(keys)))
            continue
        if any(truth[key] is UNREADABLE for key in keys):
            continue
        for index, key in enumerate(keys):
            said = found.group(index + 1)
            want = truth[key]
            ok = (said.lower() in {n.lower() for n in number(want)}
                  if isinstance(want, int) else said == want)
            if not ok:
                out.append("%s says %s is %r; it is %r"
                           % (path.name, key, said, want))
    return out


def cmd_render():
    for key, value in facts().items():
        print("%-20s %s" % (key, "unreadable here" if value is UNREADABLE else value))
    return 0


def cmd_check():
    gaps = disagreements()
    for gap in gaps:
        print(gap)
    blind = sorted(k for k, v in facts().items() if v is UNREADABLE)
    if blind:
        print("unreadable from here, so unchecked: %s" % ", ".join(blind))
    print("stated-facts: %d disagreement(s)" % len(gaps))
    return 2 if gaps else 0


def guard_stop():
    if os.environ.get("INTELLIGENCE_ALLOW_STALE_FACT") == "1":
        return 0
    gaps = disagreements()
    if not gaps:
        return 0
    sys.stderr.write(
        "BLOCKED: a document states a count the setup disagrees with.\n\n  %s\n\n"
        "A fact about this setup is read from the setup, never typed. Correct\n"
        "the sentence, or correct the setup it describes.\n\n"
        "INTELLIGENCE_ALLOW_STALE_FACT=1 lets one run finish over it.\n"
        % "\n  ".join(gaps))
    return 2


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "render":
        return cmd_render()
    if verb == "check":
        return cmd_check()
    if verb == "guard-stop":
        return guard_stop()
    sys.stderr.write(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
