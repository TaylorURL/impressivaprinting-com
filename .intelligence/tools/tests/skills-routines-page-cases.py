#!/usr/bin/env python3
"""Cases the skills and routines register has to get right.

The page is only worth publishing if it cannot say something the machine does
not, so the two halves under test are the reading and the fingerprint. The
reading has to pull what a thing is out of two accounts of itself written for
different readers, one of which is a router. The fingerprint has to move when
what a reader would see moves, and stay still when a file was merely touched --
a hash over the files instead of over the rendered lines would have every sync
report a page that is still true as stale.

  skills-routines-page-cases.py      run them
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
              or Path(__file__).resolve().parent.parent
              / "skills-routines-page.py")
FAILURES = []

REGISTRY = {
    "routines": [
        {"id": "watcher", "name": "Watcher", "cadence": "continuous",
         "host": "pi", "schedule": None,
         "gate": "*/10 * * * * watcher-tick.sh",
         "does": "Works the queue, started only on a tick that finds one."},
        {"id": "nightly", "name": "Nightly", "cadence": "daily",
         "host": "mac", "schedule": "0 10 * * *",
         "does": "The pass over every repo. Reports only."},
    ]
}

# A description written for the router, which says when to reach for the skill
# and never what it is, so the prose under the heading is the only account of
# itself this skill has.
ROUTER = """---
name: router
description: When the user wants a thing done. Also use on /router.
---

# Router

It moves a thing from one place to another. Nothing else is under here.
"""

# A description that says what the skill is inside one sentence, alongside body
# prose that would read worse. The description has to win.
PLAIN = """---
name: plain
description: Move a thing from here to there. Use on /plain, or "move it".
---

# Plain

The long way round, which nobody reads, and which goes on at some length about
matters of implementation.
"""

# Both accounts run long, and the body opens by naming a file, which is how a
# skill describes how it is built rather than what it does.
DEEP = """---
name: deep
description: %s and then some more of it, at length, past any reasonable bound.
---

# Deep

Every rule this skill knows lives in `gates/rules.json`, which is read at the
start of a run.
""" % ("Check the wiring is alive - services reached over the network, "
       "variables present and not leaking, the linters actually enforced, the "
       "protection on both branches, and the legal routes served")


def fixture(root):
    """A tree shaped like the real one, holding only what a case needs."""
    tree = root / "intelligence"
    (tree / "tools").mkdir(parents=True)
    for text in (ROUTER, PLAIN, DEEP):
        name = text.split("name: ")[1].split("\n")[0]
        (tree / "skills" / name).mkdir(parents=True)
        (tree / "skills" / name / "SKILL.md").write_text(text)
    # An installed copy of somebody else's skill, which is not this machine's.
    (tree / "skills" / "synced" / "vendored").mkdir(parents=True)
    (tree / "skills" / "synced" / "SKILL.md").write_text(
        "---\nname: vendored\ndescription: Not authored here.\n---\n")
    repo = root / "repo"
    (repo / "routines").mkdir(parents=True)
    (repo / "routines" / "registry.json").write_text(json.dumps(REGISTRY))
    (root / "state").mkdir()
    return tree, repo


def env_for(root, tree, repo, extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("INTELLIGENCE_") and k != "CLAUDE_CODE_REMOTE"}
    env["INTELLIGENCE_TOOLS_DIR"] = str(tree / "tools")
    env["INTELLIGENCE_STATE_DIR"] = str(root / "state")
    env["INTELLIGENCE_REPO"] = str(repo)
    env.update(extra or {})
    return env


def load(env):
    """The tool under test, reading the fixture rather than the live tree.

    Two of its paths are module constants resolved at import, so the
    environment has to be standing before the load rather than around the call.
    """
    os.environ.update(env)
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(env, *argv, stdin=""):
    done = subprocess.run([sys.executable, str(TARGET), *argv], env=env,
                          input=stdin, capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def case_reading(root):
    tree, repo = fixture(root)
    mod = load(env_for(root, tree, repo))
    said = {s["name"]: s["summary"] for s in mod.skills()}

    check("a skill that says only when to use it falls back to its prose",
          said["router"],
          "It moves a thing from one place to another. Nothing else is under "
          "here.")
    check("a description that fits beats the prose under the heading",
          said["plain"], "Move a thing from here to there.")
    check("prose that opens by naming a file is not an account of the skill",
          "gates/rules.json" in said["deep"], False)
    check("a description too long to say whole is cut at a clause",
          said["deep"].endswith("."), True)
    check("and cut, not run on", len(said["deep"]) <= mod.CLAUSE_LIMIT + 1,
          True)
    check("an installed copy is not one of this machine's skills",
          "vendored" in said, False)
    check("every skill the tree holds is read", sorted(said),
          ["deep", "plain", "router"])

    fired = {r["id"]: r for r in mod.routines()}
    check("a routine started by a tick shows when the tick runs",
          fired["watcher"]["schedule"], "*/10 * * * *")
    check("a routine with a schedule shows it", fired["nightly"]["schedule"],
          "0 10 * * *")
    check("two sentences are two sentences",
          fired["nightly"]["summary"], "The pass over every repo. Reports only.")


def case_fingerprint(root):
    tree, repo = fixture(root)
    mod = load(env_for(root, tree, repo))
    before = mod.build()
    stamped = mod.load_ledger()["built_at"]

    mod.build()
    check("a rebuild that changes nothing does not restamp the page",
          mod.load_ledger()["built_at"], stamped)

    # A file touched without its prose changing is what a sync does to a whole
    # tree at once, and it is not a page that has fallen behind.
    skill = tree / "skills" / "plain" / "SKILL.md"
    skill.write_text(skill.read_text() + "\n\nMore prose, further down.\n")
    check("prose the page does not show is not drift", mod.build(), before)

    skill.write_text(skill.read_text().replace("Move a thing from here to there",
                                               "Move a thing somewhere else"))
    check("a summary the page shows is", mod.build() != before, True)

    page = mod.page_path().read_text()
    check("the page carries every skill", page.count('class="row"'),
          len(mod.skills()) + len(mod.routines()))
    check("and names itself once", page.count("<title>"), 1)


def case_guard(root):
    tree, repo = fixture(root)
    env = env_for(root, tree, repo)

    code, out = run(env, "guard-stop", stdin="{}")
    check("a machine that published nothing is not behind", (code, out), (0, ""))

    run(env, "status")
    page = (root / "state" / "skills-routines" / "page.html").read_text()
    run(env, "artifact", "https://example.invalid/page")
    check("recording where a page stands does not rewrite it",
          (root / "state" / "skills-routines" / "page.html").read_text(), page)
    code, out = run(env, "guard-stop", stdin="{}")
    check("a page just published is not behind", (code, out), (0, ""))

    skill = tree / "skills" / "plain" / "SKILL.md"
    skill.write_text(skill.read_text().replace("Move a thing from here to there",
                                               "Carry a thing between places"))
    code, out = run(env, "guard-stop", stdin="{}")
    check("a session that moved a register and did not republish is refused",
          code, 2)
    check("and is told where the page stands",
          "https://example.invalid/page" in out, True)

    code, _ = run(env, "guard-stop", stdin='{"stop_hook_active": true}')
    check("a refusal already answered does not refuse again", code, 0)

    off = dict(env, INTELLIGENCE_SKILLS_PAGE_OFF="1")
    code, _ = run(off, "guard-stop", stdin="{}")
    check("the override stands it down", code, 0)

    code, out = run(env, "status")
    check("status reports the drift", code, 1)
    check("and says so on its last line",
          out.strip().splitlines()[-1].endswith("BEHIND its sources"), True)

    run(env, "published")
    code, out = run(env, "guard-stop", stdin="{}")
    check("recording the republish settles it", (code, out), (0, ""))
    code, out = run(env, "status")
    check("and status agrees", code, 0)


def main():
    for case in (case_reading, case_fingerprint, case_guard):
        with tempfile.TemporaryDirectory() as tmp:
            case(Path(tmp))
    for f in FAILURES:
        print(f)
    print("skills-routines-page: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
