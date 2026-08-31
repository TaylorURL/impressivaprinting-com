#!/usr/bin/env python3
"""Cases the documentation pass has to get right.

The ledger answers two different questions with one mechanism. An ordinary
Markdown file reopens only when its own prose changes; a README also reopens
when the scripts or the tree it documents move, and never for the version-badge
bump alone. A repo with no README at all owes the page before any ledger is
consulted, because there is nothing to record against a page that was never
written.

Every fixture lives in a TemporaryDirectory, and every run pins the ledger to a
directory inside it through INTELLIGENCE_STATE_DIR, so no case can write into
the live config tree or the real pass state.

  doc-pass-cases.py        run them
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
              or Path(__file__).resolve().parent.parent / "doc-pass.py")

SLUG = "bradley-t-t/demo"

README = (
    "# Demo\n"
    "\n"
    "![Version](https://img.shields.io/badge/version-1.2.3-blue)\n"
    "\n"
    "A repo that exists so its documentation can be judged.\n"
)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def check_in(label, needle, hay):
    if needle not in hay:
        FAILURES.append(f"{label}: {needle!r} not in {hay!r}")


def check_not_in(label, needle, hay):
    if needle in hay:
        FAILURES.append(f"{label}: {needle!r} unexpectedly in {hay!r}")


def load(state_dir):
    os.environ["INTELLIGENCE_STATE_DIR"] = str(state_dir)
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(root, *args):
    subprocess.run(
        ["git", "-c", "user.email=cases@localhost", "-c", "user.name=cases",
         *args],
        cwd=root, capture_output=True, text=True, check=True,
    )


def make_repo(tmp, slug=SLUG, name="repo"):
    root = Path(tmp) / name
    root.mkdir()
    git(root, "init", "-q")
    git(root, "remote", "add", "origin", f"git@github.com:{slug}.git")
    return root


def track(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    git(root, "add", "-f", str(rel))
    return path


def run_tool(verb, cwd, state_dir, args=(), stdin=None):
    env = dict(os.environ)
    env["INTELLIGENCE_STATE_DIR"] = str(state_dir)
    env.pop("CLAUDE_CODE_REMOTE", None)
    p = subprocess.run(
        [sys.executable, str(TARGET), verb, *args],
        cwd=cwd, input=stdin, capture_output=True, text=True, env=env,
    )
    return p


def out_of_scope_cases(tmp):
    state = Path(tmp) / "state"

    bare = Path(tmp) / "not-a-repo"
    bare.mkdir()
    p = run_tool("status", bare, state)
    check("no repo: status exits clean", p.returncode, 0)
    check_in("no repo: status says so", "does not apply", p.stdout)
    p = subprocess.run([sys.executable, str(TARGET)], cwd=bare, input="",
                       capture_output=True, text=True,
                       env={**os.environ, "INTELLIGENCE_STATE_DIR": str(state)})
    check("no verb: defaults to status", p.returncode, 0)
    check_in("no verb: status text", "does not apply", p.stdout)

    other = make_repo(tmp, slug="someone-else/thing", name="foreign")
    track(other, "README.md", "# Foreign\n")
    p = run_tool("list", other, state)
    check("foreign repo: list exits clean", p.returncode, 0)
    check("foreign repo: list prints nothing", p.stdout, "")
    p = run_tool("mark", other, state)
    check("foreign repo: mark exits clean", p.returncode, 0)
    check_in("foreign repo: mark says why", "Not an owned git repo", p.stderr)

    p = run_tool("nonsense", bare, state)
    check("unknown verb refused", p.returncode, 2)
    check_in("unknown verb prints usage", "usage:", p.stderr)


def lifecycle_cases(tmp):
    state = Path(tmp) / "state"
    root = make_repo(tmp)
    track(root, "docs/notes.md", "# Notes\n\nPlain prose about nothing else.\n")
    track(root, "package.json",
          json.dumps({"name": "demo", "scripts": {"build": "true"}}))

    # No README at the root: list names the debt, with nothing to mark.
    p = run_tool("list", root, state)
    check("missing readme: list exits clean", p.returncode, 0)
    check("missing readme: named first", p.stdout.splitlines()[:1], ["README.md"])
    check_in("missing readme: other docs still owe a pass",
             "docs/notes.md", p.stdout)

    # The README exists, but nothing has been swept.
    track(root, "README.md", README)
    p = run_tool("status", root, state)
    check("unswept: status exits clean", p.returncode, 0)
    check_in("unswept: status says no pass on record",
             "no documentation pass on record", p.stdout)

    # A recorded pass clears everything.
    p = run_tool("mark", root, state)
    check("mark: exits clean", p.returncode, 0)
    check_in("mark: reports the count", "Recorded a documentation pass", p.stdout)
    ledger = state / "doc-pass" / (SLUG.replace("/", "__") + ".json")
    check("mark: ledger lands where INTELLIGENCE_STATE_DIR points",
          ledger.is_file(), True)
    check("clean: list is empty", run_tool("list", root, state).stdout, "")
    p = run_tool("status", root, state)
    check_in("clean: status says up to date", "up to date", p.stdout)

    # The badge bump is normalized out; a version release reopens nothing.
    readme = root / "README.md"
    readme.write_text(readme.read_text().replace("version-1.2.3", "version-1.2.4"))
    check("badge bump: list stays empty", run_tool("list", root, state).stdout, "")

    # A prose edit is exactly what reopens a page.
    readme.write_text(readme.read_text() + "\nA sentence the last pass never saw.\n")
    check("prose edit: list names the page",
          run_tool("list", root, state).stdout.strip(), "README.md")
    p = run_tool("status", root, state)
    check_in("prose edit: status says something changed", "changed", p.stdout)

    # Marking one named path clears that path.
    p = run_tool("mark", root, state, args=("README.md",))
    check("mark path: exits clean", p.returncode, 0)
    check("mark path: repo is clean again",
          run_tool("list", root, state).stdout, "")

    # A path the ledger does not cover is named and skipped.
    p = run_tool("mark", root, state, args=("nope.md",))
    check("mark unknown path: exits clean", p.returncode, 0)
    check_in("mark unknown path: named as ignored", "Not tracked, ignored", p.stderr)
    check_in("mark unknown path: nothing recorded", "Nothing to record", p.stdout)

    # A new manifest script reopens the README's claims and nobody else's.
    (root / "package.json").write_text(
        json.dumps({"name": "demo", "scripts": {"build": "true", "test": "true"}}))
    check("new script: only the README reopens",
          run_tool("list", root, state).stdout.strip(), "README.md")
    run_tool("mark", root, state)

    # A new top-level path changes the tree shape the README describes.
    track(root, "cli/main.py", "print('hi')\n")
    check("new tree entry: only the README reopens",
          run_tool("list", root, state).stdout.strip(), "README.md")
    run_tool("mark", root, state)
    check("settled: list is empty again",
          run_tool("list", root, state).stdout, "")


def exclusion_cases(tmp):
    state = Path(tmp) / "state"
    root = make_repo(tmp, name="mixed")
    track(root, "README.md", README)
    track(root, "docs/notes.mdx", "# Notes\n")
    track(root, "LICENSE.md", "verbatim licence text\n")
    track(root, "third/VENDOR.md", "copied from upstream\n")
    track(root, "third/readme.md", "# Upstream\n")
    track(root, "archive/old.md", "# Old\n")

    out = run_tool("list", root, state).stdout
    check_in("scope: root README owes a pass", "README.md", out)
    check_in("scope: mdx owes a pass", "docs/notes.mdx", out)
    check_not_in("scope: licence text is left alone", "LICENSE.md", out)
    check_not_in("scope: vendored subtree is left alone", "third/", out)
    check_not_in("scope: archived records are left alone", "archive/", out)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        out_of_scope_cases(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        lifecycle_cases(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        exclusion_cases(tmp)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
