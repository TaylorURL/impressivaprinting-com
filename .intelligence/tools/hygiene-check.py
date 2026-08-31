#!/usr/bin/env python3
"""The hygiene rules, read from the tree rather than from a memory file.

Four rules a script settles completely and prose settles only when somebody
happens to read it: what sits at the home level, one README per project, no
editor config tracked in a repository, and no reference left to a retired
project.

Each is answered by looking, so a rule that has drifted says so with the paths
rather than staying true in a document while being false on disk.

  check    every rule, with what fails
  fix      remove what is safe to remove, then check again
"""
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()

# The directories the home level holds. Hidden entries are configuration and are
# outside this test. `go` is the toolchain's own module cache rather than a
# project, and Go resolves it here by default.
HOME_ALLOWED = {
    "Applications", "Archives", "Desktop", "Development", "Documents",
    "Downloads", "Library", "Movies", "Music", "Pictures", "Public", "go",
}

CHECKOUT_ROOTS = [
    HOME / "Development" / "IdeaProjects",
    HOME / "Development" / "WebstormProjects",
]

EDITOR_CONFIG = re.compile(
    r"(?:^|/)(?:\.idea/|\.vscode/|\.fleet/|\.zed/)|\.iml$")

RETIRED = re.compile(
    r"\bswordfun\b|\bbloodplex\b|\bknightplugins\b|\bminecraft\b"
    r"|\bspigot\b|\bbukkit\b|\bmicroquests\b|\boneplayersleep"
    r"|\bchunk-rescue\b|arbiter-panel", re.I)

# The parts of a checkout holding somebody else's files, where a README or a
# retired name is theirs. The vendored config tree is one of them: it is an
# installed copy of the setup, and its own layout answers to the source it came
# from rather than to the repository carrying it.
VENDORED = re.compile(
    r"(?:^|/)(?:node_modules|vendor|third_party|\.git|\.intelligence)/")


def repos():
    for root in CHECKOUT_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            if (path / ".git").exists():
                yield path


def tracked(repo):
    done = subprocess.run(["git", "-C", str(repo), "ls-files"],
                          capture_output=True, text=True, timeout=60)
    if done.returncode:
        return []
    return [line for line in done.stdout.splitlines()
            if line and not VENDORED.search(line)]


def home_level():
    """Loose files and project directories sitting at the home level."""
    out = []
    for entry in sorted(HOME.iterdir()):
        if entry.name.startswith(".") or entry.name in HOME_ALLOWED:
            continue
        out.append(str(entry))
    return out


def stray_readmes():
    """READMEs below a project root."""
    out = []
    for repo in repos():
        for path in tracked(repo):
            name = path.rsplit("/", 1)[-1]
            if name.lower().startswith("readme") and "/" in path:
                out.append("%s: %s" % (repo.name, path))
    return out


def editor_config():
    out = []
    for repo in repos():
        for path in tracked(repo):
            if EDITOR_CONFIG.search(path):
                out.append("%s: %s" % (repo.name, path))
    return out


def retired_references():
    """Names of retired projects still tracked in an owned checkout.

    Both halves count. A file named for a retired project is a reference
    whatever it contains, and a file named for something else still holds one
    when the name appears inside it.
    """
    out = []
    for repo in repos():
        found = set()
        for path in tracked(repo):
            if RETIRED.search(path):
                found.add(path)
        done = subprocess.run(
            ["git", "-C", str(repo), "grep", "-lIiE", RETIRED.pattern],
            capture_output=True, text=True, timeout=120)
        for path in done.stdout.splitlines():
            if path and not VENDORED.search(path):
                found.add(path)
        out += ["%s: %s" % (repo.name, path) for path in sorted(found)]
    return out


RULES = [
    ("home level holds only its directories", home_level,
     "file it under ~/Development or ~/Archives"),
    ("one README per project, at the root", stray_readmes,
     "fold it into the root README or delete it"),
    ("no editor config tracked", editor_config,
     "hygiene-check.py fix"),
    ("no reference to a retired project", retired_references,
     "remove the reference"),
]


def run():
    failures = 0
    for title, probe, remedy in RULES:
        try:
            found = probe()
        except (OSError, subprocess.SubprocessError) as exc:
            print("FAIL  %s\n      could not be read: %s" % (title, exc))
            failures += 1
            continue
        if not found:
            print("ok    %s" % title)
            continue
        failures += 1
        print("FAIL  %s  (%d)" % (title, len(found)))
        for path in found[:12]:
            print("        %s" % path)
        if len(found) > 12:
            print("        ... and %d more" % (len(found) - 12))
        print("      fix: %s" % remedy)
    return failures


def fix():
    """Untrack editor config and gitignore it.

    Only tracked editor config is removed here. A file at the home level might
    be anything and a README might be somebody's work, so those two are reported
    and left alone.
    """
    removed = 0
    for repo in repos():
        paths = [p for p in tracked(repo) if EDITOR_CONFIG.search(p)]
        if not paths:
            continue
        subprocess.run(["git", "-C", str(repo), "rm", "--cached", "-q", "--",
                        *paths], capture_output=True)
        ignore = repo / ".gitignore"
        lines = ignore.read_text().splitlines() if ignore.exists() else []
        for entry in (".idea/", ".vscode/", ".fleet/", ".zed/", "*.iml"):
            if entry not in lines:
                lines.append(entry)
        ignore.write_text("\n".join(lines) + "\n")
        removed += len(paths)
        print("%s: untracked %d editor file(s)" % (repo.name, len(paths)))
    if not removed:
        print("nothing to remove")
    return removed


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else "check"
    if verb == "check":
        return 1 if run() else 0
    if verb == "fix":
        fix()
        return 1 if run() else 0
    sys.stderr.write(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
