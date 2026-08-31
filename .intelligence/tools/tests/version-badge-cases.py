#!/usr/bin/env python3
"""Cases the version badge tool has to get right.

The tool repairs rather than refuses: the correct value is always the manifest's,
so `guard` rewrites the badge and exits 0 in every case, and never blocks a
commit. These fix both halves of that contract — a drifted badge is rewritten
wherever a landing verb names the repo, and a repo that is in step, has no badge,
or has no manifest is left byte-for-byte alone. `check` is the read-only half:
exit 1 and a report on drift, exit 0 and no write otherwise.

  version-badge-cases.py        run them
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
              or Path(__file__).resolve().parent.parent / "version-badge.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


README = (
    "# Widget\n\n"
    "![Version](https://img.shields.io/badge/version-{v}-blue)\n"
    '<img alt="Version {v}" src="badge.svg">\n\n'
    "![Build](https://img.shields.io/badge/build-passing-green)\n"
)


def repo(tmp, name="widget", badge="1.0.0", package=None, gradle=None,
         pom=None, readme=True):
    """A repo fixture inside `tmp`: a README badge and whichever manifests are given."""
    root = Path(tmp) / name
    root.mkdir(parents=True, exist_ok=True)
    assert str(root).startswith(str(tmp)), f"escaped the temp tree: {root}"
    if readme:
        (root / "README.md").write_text(README.format(v=badge))
    if package is not None:
        (root / "package.json").write_text(package)
    if gradle is not None:
        (root / "gradle.properties").write_text(gradle)
    if pom is not None:
        (root / "pom.xml").write_text(pom)
    return root


def cli(args, cwd=None):
    p = subprocess.run([sys.executable, str(TARGET)] + args,
                       capture_output=True, text=True, cwd=cwd)
    return p.returncode, p.stdout


def guard(event):
    p = subprocess.run([sys.executable, str(TARGET), "guard"],
                       input=event, capture_output=True, text=True)
    return p.returncode, p.stdout


POM = (
    "<project>\n"
    "  <groupId>com.example</groupId>\n"
    "  <artifactId>widget</artifactId>\n"
    "  <version>3.1.0</version>\n"
    "  <dependencies>\n"
    "    <dependency><version>9.9.9</version></dependency>\n"
    "  </dependencies>\n"
    "</project>\n"
)


def declared_cases(mod):
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(tmp, package='{"version": "2.0.0"}')
        check("declared: package.json", mod.declared(root), ("2.0.0", "package.json"))

        root = repo(tmp, name="both", package='{"version": "2.0.0"}',
                    gradle="version=4.0.0\n")
        check("declared: package.json outranks gradle",
              mod.declared(root), ("2.0.0", "package.json"))

        root = repo(tmp, name="gradle", gradle="version = 4.0.0\n")
        check("declared: gradle.properties", mod.declared(root),
              ("4.0.0", "gradle.properties"))

        # The project's own <version> is read, never a dependency's.
        root = repo(tmp, name="pom", pom=POM)
        check("declared: pom head only", mod.declared(root), ("3.1.0", "pom.xml"))

        # A manifest that does not parse falls through to the next one.
        root = repo(tmp, name="broken", package="{not json",
                    gradle="version=4.0.0\n")
        check("declared: broken package.json falls through",
              mod.declared(root), ("4.0.0", "gradle.properties"))

        root = repo(tmp, name="versionless", package='{"name": "widget"}',
                    gradle="version=4.0.0\n")
        check("declared: versionless package.json falls through",
              mod.declared(root), ("4.0.0", "gradle.properties"))

        root = repo(tmp, name="bare")
        check("declared: no manifest", mod.declared(root), (None, None))


def drift_cases(mod):
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(tmp, badge="1.0.0", package='{"version": "2.0.0"}')
        found = mod.drift(root)
        check("drift: mismatch found", found is not None, True)
        if found:
            check("drift: tuple", (found[1], found[2], found[3]),
                  ("1.0.0", "2.0.0", "package.json"))

        # A version carrying its own dash. shields.io reads a single dash as a
        # field separator and a double dash as one literal dash, so the version
        # segment is written escaped and the colour is whatever follows the first
        # single dash after it.
        root = repo(tmp, name="prerelease", badge="2026.35.27--1",
                    package='{"version": "2026.35.27-2"}')
        msg = mod.repair(root)
        check("repair: hyphenated version message",
              msg, "prerelease: version badge 2026.35.27-1 -> 2026.35.27-2 (from package.json)")
        text = (root / "README.md").read_text()
        check("repair: hyphenated badge escaped",
              "badge/version-2026.35.27--2-blue" in text, True)
        check("repair: whole version replaced",
              "2026.35.27--2-1" in text or "2026.35.27-2-1" in text, False)
        check("repair: hyphenated alt is unescaped",
              'alt="Version 2026.35.27-2"' in text, True)
        check("repair: hyphenated nothing left to fix", mod.repair(root), None)

        # An escaped badge already matching the manifest is in step: the two
        # spellings of one version are not drift between two versions.
        root = repo(tmp, name="prestep", badge="2026.35.27--2",
                    package='{"version": "2026.35.27-2"}')
        check("repair: escaped badge in step returns None", mod.repair(root), None)

        root = repo(tmp, name="instep", badge="2.0.0",
                    package='{"version": "2.0.0"}')
        check("drift: badge in step", mod.drift(root), None)

        root = repo(tmp, name="noreadme", readme=False,
                    package='{"version": "2.0.0"}')
        check("drift: no README", mod.drift(root), None)

        # A badge whose label is not `version-` never counts as drift.
        root = repo(tmp, name="nobadge", package='{"version": "2.0.0"}')
        (root / "README.md").write_text(
            "![Build](https://img.shields.io/badge/build-old-red)\n")
        check("drift: only non-version badges", mod.drift(root), None)

        root = repo(tmp, name="nomanifest", badge="1.0.0")
        check("drift: no manifest", mod.drift(root), None)


def repair_cases(mod):
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(tmp, badge="1.0.0", package='{"version": "2.0.0"}')
        msg = mod.repair(root)
        check("repair: message",
              msg, "widget: version badge 1.0.0 -> 2.0.0 (from package.json)")
        text = (root / "README.md").read_text()
        check("repair: badge rewritten", "badge/version-2.0.0-blue" in text, True)
        check("repair: alt rewritten", 'alt="Version 2.0.0"' in text, True)
        check("repair: build badge untouched",
              "badge/build-passing-green" in text, True)
        check("repair: nothing left to fix", mod.repair(root), None)

        root = repo(tmp, name="instep", badge="2.0.0",
                    package='{"version": "2.0.0"}')
        before = (root / "README.md").read_text()
        check("repair: in step returns None", mod.repair(root), None)
        check("repair: in step writes nothing",
              (root / "README.md").read_text(), before)


def cli_cases():
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(tmp, badge="1.0.0", package='{"version": "2.0.0"}')
        rc, out = cli(["check", str(root)])
        check("cli check: drift exits 1", rc, 1)
        check("cli check: drift reported",
              "README badge says 1.0.0, package.json says 2.0.0" in out, True)
        check("cli check: writes nothing",
              "version-1.0.0" in (root / "README.md").read_text(), True)

        rc, out = cli(["--check", str(root)])
        check("cli --check: same as check", rc, 1)

        rc, out = cli([str(root)])
        check("cli rewrite: exits 0", rc, 0)
        check("cli rewrite: message printed",
              "version badge 1.0.0 -> 2.0.0" in out, True)
        check("cli rewrite: badge moved",
              "version-2.0.0" in (root / "README.md").read_text(), True)

        rc, out = cli([str(root)])
        check("cli rewrite: repeat is silent", (rc, out), (0, ""))

        rc, out = cli(["check", str(root)])
        check("cli check: in step exits 0", (rc, out), (0, ""))

        # With no path the current directory is the repo.
        root = repo(tmp, name="cwdrepo", badge="1.0.0",
                    package='{"version": "2.0.0"}')
        rc, out = cli([], cwd=str(root))
        check("cli no-arg: repairs cwd", rc, 0)
        check("cli no-arg: badge moved",
              "version-2.0.0" in (root / "README.md").read_text(), True)


def guard_cases():
    with tempfile.TemporaryDirectory() as tmp:
        def event(command, cwd):
            return json.dumps({"tool_input": {"command": command},
                               "cwd": str(cwd)})

        # The guard repairs and never refuses: exit 0 with drift and without.
        root = repo(tmp, badge="1.0.0", package='{"version": "2.0.0"}')
        rc, out = guard(event("git commit -m 'move on'", root))
        check("guard: commit exits 0", rc, 0)
        check("guard: commit repairs",
              "version-2.0.0" in (root / "README.md").read_text(), True)
        check("guard: repair announced",
              out.startswith("Corrected before landing"), True)

        rc, out = guard(event("git commit -m again", root))
        check("guard: in-step commit is silent", (rc, out), (0, ""))

        root = repo(tmp, name="pr", badge="1.0.0",
                    package='{"version": "2.0.0"}')
        rc, out = guard(event("gh pr create --fill", root))
        check("guard: pr create exits 0", rc, 0)
        check("guard: pr create repairs",
              "version-2.0.0" in (root / "README.md").read_text(), True)

        # The repo the command lands in is the one repaired, not the session's cwd.
        target = repo(tmp, name="target", badge="1.0.0",
                      package='{"version": "2.0.0"}')
        bystander = repo(tmp, name="bystander", badge="1.0.0",
                         package='{"version": "2.0.0"}')
        rc, out = guard(event(f"cd {target} && git commit -m x", bystander))
        check("guard: cd rebinds the repo", rc, 0)
        check("guard: cd target repaired",
              "version-2.0.0" in (target / "README.md").read_text(), True)
        check("guard: bystander untouched",
              "version-1.0.0" in (bystander / "README.md").read_text(), True)

        rc, out = guard(event(f"git -C {bystander} commit -m x", target))
        check("guard: -C rebinds the repo", rc, 0)
        check("guard: -C target repaired",
              "version-2.0.0" in (bystander / "README.md").read_text(), True)

        # A command that lands nothing writes nothing, whatever the drift.
        root = repo(tmp, name="idle", badge="1.0.0",
                    package='{"version": "2.0.0"}')
        for command in ("git status", "git log --oneline",
                        'echo "git commit"', "ls -la"):
            rc, out = guard(event(command, root))
            check(f"guard: no landing verb ({command})", (rc, out), (0, ""))
        check("guard: idle repo untouched",
              "version-1.0.0" in (root / "README.md").read_text(), True)

        rc, out = guard("not json")
        check("guard: garbage stdin exits 0", (rc, out), (0, ""))

        rc, out = guard(json.dumps({}))
        check("guard: empty event exits 0", (rc, out), (0, ""))


def a_mistyped_verb_is_not_a_path(mod):
    """There are no subcommands here beyond guard and check.

    A verb typed as one lands in args[0] and is read as a repo root. Every
    later step then answers "nothing to do" about a directory that was never
    there, and the run exits 0 having left the badge as it found it.
    """
    import subprocess, sys as _sys
    tool = Path.home() / ".intelligence" / "tools" / "version-badge.py"
    done = subprocess.run([_sys.executable, str(tool), "repair", "."],
                          capture_output=True, text=True)
    check("cli: a mistyped verb exits non-zero", done.returncode != 0,
          "exit %d" % done.returncode)
    check("cli: it says which argument was wrong", "repair" in done.stderr, done.stderr)
    check("cli: it prints the usage", "Usage:" in done.stderr, done.stderr)


def main():
    mod = load()
    declared_cases(mod)
    drift_cases(mod)
    repair_cases(mod)
    cli_cases()
    guard_cases()

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
