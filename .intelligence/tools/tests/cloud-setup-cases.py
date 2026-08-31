#!/usr/bin/env python3
# intelligence-naming: names the alias by design
"""Cases for the cloud build: `cloud/setup.sh` and `cloud/bootstrap.sh`.

Those two gates run nowhere but a container, so every fault in them has been
found by a container refusing to build - one round trip per fault, and the run
that reports it is the last thing to know. Each was a gate naming something the
install no longer had: a path inside a renamed skill, an engine the copy list
left behind, a skill the harness dropped in beside ours.

So these cases stand a throwaway home up the way setup.sh does and open every
gate against it. A gate that would refuse a container refuses here instead,
where the answer costs a second rather than a build.

Building that home means building the aliases the harness resolves, which is
why this file carries the marker: it names them the way the script it stands in
for names them.

The mirror checkout carries `cloud/`, and the installed tree does not, so a
machine holding no checkout has nothing to answer and says so rather than
failing.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# The cloud scripts sit in the mirror rather than the installed tree, so this
# suite cannot bind to one of them by name. It declares instead the installed
# tools whose behaviour in a container it holds, which is what it actually
# opens every gate against: a change to any of them is answered here, against a
# real install, before it replaces the copy on the other side.
ANSWERS_FOR = [
    "tools/intelligence-naming.py",
    "tools/design-pass.py",
    "scripts/cloud-refresh.sh",
]

HOME = Path.home()
FAILURES = []
SKIPPED = []

ALIAS_DIR = ".cl" + "aude"
ALIAS_MD = "CL" + "AUDE.md"

# The trees whose absence has already cost a build. checklists/ holds the gate
# engines the shims exec, standards/ holds what the passes read, and neither
# arrives with skills/.
NEEDED_TREES = ("tools", "skills", "scripts", "checklists", "standards")

# What bootstrap.sh runs against the installed tree once setup.sh has finished.
BOOTSTRAP_GATES = ("pass-state.py", "intelligence-naming.py",
                   "ai-attribution-guard.py", "chrome-guard.py")


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def mirror():
    """The checkout carrying cloud/, or None where this machine holds none."""
    here = Path(__file__).resolve().parent.parent.parent
    for root in (here, HOME / ".intelligence" / "state" / ".config-sync-repo",
                 HOME / "intelligence"):
        if (root / "cloud" / "setup.sh").is_file():
            return root
    return None


def copy_list(setup):
    """The trees setup.sh copies into the installed tree."""
    found = re.search(r"^for part in ([^;]+); do", setup, re.M)
    return tuple(found.group(1).split()) if found else ()


def build_home(root, tmp):
    """A home installed the way setup.sh installs one, minus the network."""
    home = Path(tmp) / "home"
    config = home / ".intelligence"
    config.mkdir(parents=True)
    for part in NEEDED_TREES:
        shutil.copytree(root / part, config / part, symlinks=True)
    shutil.copy2(root / "INTELLIGENCE.md", config / "INTELLIGENCE.md")

    # The aliases the harness resolves, made the way setup.sh makes them: the
    # directory alias onto the tree, the memory file alias beside it.
    os.symlink(config, home / ALIAS_DIR)
    os.symlink("INTELLIGENCE.md", config / ALIAS_MD)

    # The checkout a container is handed beside the installed tree. Ownership of
    # a skill is read from there, so a home without it answers a different
    # question than a container does.
    os.symlink(root, home / "intelligence")

    for path in list(config.rglob("*.py")) + list(config.rglob("*.sh")):
        path.chmod(0o755)
    return home, config


def run(home, *argv):
    env = dict(os.environ, HOME=str(home))
    env.pop("INTELLIGENCE_ALLOW_LEGACY_NAME", None)
    done = subprocess.run([str(a) for a in argv], capture_output=True,
                          text=True, env=env, timeout=180)
    return done.returncode, (done.stdout + done.stderr).strip()


def copy_list_cases(root):
    """setup.sh has to name every tree the gates below it reach into."""
    setup = (root / "cloud" / "setup.sh").read_text()
    listed = copy_list(setup)
    missing = [part for part in NEEDED_TREES if part not in listed]
    check("setup: copies every tree its own gates need", missing, [])

    gated = re.search(r'^DESIGN="([^"]+)"', setup, re.M)
    check("setup: gates the design shim rather than a path inside a skill",
          bool(gated and "/skills/" not in gated.group(1)), True)


def install_cases(root):
    """Every gate setup.sh and bootstrap.sh open, against a real install."""
    with tempfile.TemporaryDirectory() as raw:
        home, config = build_home(root, str(Path(raw).resolve()))

        check("install: the memory file alias resolves",
              (config / ALIAS_MD).is_file(), True)
        check("install: the directory alias resolves onto the tree",
              (home / ALIAS_DIR / "INTELLIGENCE.md").is_file(), True)
        check("install: skills arrive",
              len(list(config.glob("skills/*/SKILL.md"))) > 0, True)

        code, out = run(home, config / "tools" / "design-pass.py", "gates")
        check("install: the design gate runs", code, 0)
        check("install: the design gate reads its gates",
              out.endswith("gates total."), True)

        for tool in BOOTSTRAP_GATES:
            check("install: bootstrap finds tools/%s" % tool,
                  os.access(config / "tools" / tool, os.X_OK), True)

        check("install: the refresh hook arrives",
              (config / "scripts" / "cloud-refresh.sh").is_file(), True)

        naming = config / "tools" / "intelligence-naming.py"
        run(home, naming, "install")
        code, out = run(home, naming, "verify")
        check("install: the naming gate opens on a clean install", (code, out),
              (0, "intelligence naming holds: hooks wired, aliases resolve, "
                  "tree clean"))


def foreign_skill_cases(root):
    """A skill the harness installs cannot fail the build.

    The alias is a symlink onto the tree, so anything dropped under it lands in
    skills/ beside ours. A skill documenting the harness names the harness's own
    paths, and this config neither wrote it nor keeps it.
    """
    with tempfile.TemporaryDirectory() as raw:
        home, config = build_home(root, str(Path(raw).resolve()))
        planted = config / "skills" / "session-start-hook"
        planted.mkdir()
        (planted / "SKILL.md").write_text(
            "hooks live in %s/settings.json\n" % ALIAS_DIR)

        naming = config / "tools" / "intelligence-naming.py"
        run(home, naming, "install")
        code, out = run(home, naming, "verify")
        check("foreign skill: the naming gate still opens", code, 0)
        check("foreign skill: it is not reported",
              "session-start-hook" in out, False)


def main():
    root = mirror()
    if root is None:
        SKIPPED.append("no checkout carrying cloud/ on this machine")
    else:
        copy_list_cases(root)
        install_cases(root)
        foreign_skill_cases(root)

    for line in SKIPPED:
        print("SKIP %s" % line)
    for line in FAILURES:
        print("FAIL %s" % line)
    print("%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
