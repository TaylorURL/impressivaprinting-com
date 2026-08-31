#!/usr/bin/env python3
"""Cases the comment pass has to get right.

The ledger keys each file on its working-tree content, so a repo with no record
owes a full sweep, a recorded file stays quiet until it changes, and an
uncommitted edit reopens it without waiting for a commit. Scope is what makes
the outstanding list honest: data and markup carry nothing to judge, vendored
and generated code is not this side's to rewrite, and a page counts as code
only when it holds a real inline script.

Every fixture lives in a TemporaryDirectory, and every run pins the ledger to a
directory inside it through INTELLIGENCE_STATE_DIR, so no case can write into
the live config tree or the real pass state.

  comment-pass-cases.py        run them
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
              or Path(__file__).resolve().parent.parent / "comment-pass.py")

SLUG = "bradley-t-t/demo"

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


def ledger(state_dir, slug=SLUG):
    path = Path(state_dir) / "comment-pass" / (slug.replace("/", "__") + ".json")
    return path, (json.loads(path.read_text()) if path.is_file() else None)


def unit_cases(tmp):
    state = Path(tmp) / "state"
    mod = load(state)
    # The redirected state root is the whole containment story: every ledger
    # write below lands under it, so it has to sit inside this temp tree.
    check("state: STATE_DIR follows the override",
          str(mod.STATE_DIR).startswith(str(tmp)), True)

    saved = {k: os.environ.get(k)
             for k in ("INTELLIGENCE_STATE_DIR", "CLAUDE_CODE_REMOTE")}
    try:
        os.environ["INTELLIGENCE_STATE_DIR"] = str(state)
        os.environ["CLAUDE_CODE_REMOTE"] = "1"
        check("state root: the override wins over the remote flag",
              mod._state_root(), Path(state))
        del os.environ["INTELLIGENCE_STATE_DIR"]
        check("state root: a cloud session keeps the ledger off ~/.intelligence",
              mod._state_root(), Path.home() / ".pass-state")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


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
    track(other, "app.py", "value = 1\n")
    p = run_tool("list", other, state)
    check("foreign repo: list exits clean", p.returncode, 0)
    check("foreign repo: list prints nothing", p.stdout, "")
    p = run_tool("mark", other, state)
    check("foreign repo: mark exits clean", p.returncode, 0)
    check_in("foreign repo: mark says why", "Not an owned git repo", p.stderr)

    p = run_tool("nonsense", bare, state)
    check("unknown verb refused", p.returncode, 1)
    check_in("unknown verb prints the contract", "mark", p.stderr)


def scope_cases(tmp):
    state = Path(tmp) / "state"
    root = make_repo(tmp, name="mixed")
    track(root, "app.py", "value = 1\n")
    track(root, "src/util.js", "export const one = 1\n")
    track(root, "styles.css", "body { margin: 0 }\n")
    track(root, "notes.md", "# Notes\n")
    track(root, "data.json", "{}\n")
    track(root, "vendor/lib.js", "export const two = 2\n")
    track(root, "node_modules/pkg/index.js", "module.exports = 3\n")
    track(root, "third/VENDOR.md", "copied from upstream\n")
    track(root, "third/copy.js", "export const four = 4\n")
    track(root, "bundle.min.js", "var a=1;\n")
    track(root, "loader.html",
          '<p>hi</p><script src="app.js"></script>\n')
    track(root, "inline.html",
          "<h1>App</h1><script>\n" + "let x = 1;\n" * 200 + "</script>\n")

    out = run_tool("list", root, state).stdout
    check("scope: the code files owe a pass",
          out.splitlines(), ["app.py", "inline.html", "src/util.js", "styles.css"])
    check_not_in("scope: prose is left alone", "notes.md", out)
    check_not_in("scope: data is left alone", "data.json", out)
    check_not_in("scope: vendor directory is left alone", "vendor/", out)
    check_not_in("scope: node_modules is left alone", "node_modules", out)
    check_not_in("scope: VENDOR.md subtree is left alone", "third/", out)
    check_not_in("scope: minified output is left alone", "bundle.min.js", out)
    check_not_in("scope: src-only markup stays markup", "loader.html", out)

    # A path outside the scope cannot be marked into the ledger either.
    p = run_tool("mark", root, state, args=("notes.md",))
    check_in("mark excluded path: named as ignored", "Not tracked, ignored", p.stderr)
    check_in("mark excluded path: nothing recorded", "Nothing to record", p.stdout)


def lifecycle_cases(tmp):
    state = Path(tmp) / "state"
    root = make_repo(tmp)
    track(root, "app.py", "value = 1\n")
    track(root, "cli.py", "print(1)\n")
    track(root, "src/util.js", "export const one = 1\n")

    # Nothing recorded yet: the whole codebase is the first sweep.
    p = run_tool("status", root, state)
    check("unswept: status exits clean", p.returncode, 0)
    check_in("unswept: status says no pass on record",
             "no comment pass on record", p.stdout)
    check_in("unswept: status counts every file", "All 3 code files", p.stdout)

    # A recorded pass clears everything.
    p = run_tool("mark", root, state)
    check("mark: exits clean", p.returncode, 0)
    check_in("mark: reports the count",
             "Recorded a comment pass for 3 file(s)", p.stdout)
    path, body = ledger(state)
    check("mark: ledger lands where INTELLIGENCE_STATE_DIR points",
          path.is_file(), True)
    check("mark: every candidate is keyed",
          sorted((body or {}).get("files", {})), ["app.py", "cli.py", "src/util.js"])
    check("clean: list is empty", run_tool("list", root, state).stdout, "")
    p = run_tool("status", root, state)
    check_in("clean: status says up to date", "up to date", p.stdout)

    # An uncommitted edit reopens the file: the key is working-tree content.
    (root / "app.py").write_text("value = 2\n")
    (root / "src/util.js").write_text("export const one = 2\n")
    check("edit: only the edited files reopen",
          run_tool("list", root, state).stdout.splitlines(),
          ["app.py", "src/util.js"])
    p = run_tool("status", root, state)
    check_in("edit: status counts the reopened",
             "2 file(s) changed since their last comment pass", p.stdout)

    # Marking one named path clears that path and nobody else's.
    p = run_tool("mark", root, state, args=("app.py",))
    check("mark path: exits clean", p.returncode, 0)
    check("mark path: the other file still owes",
          run_tool("list", root, state).stdout.strip(), "src/util.js")

    # A path the repo does not track is named and skipped.
    p = run_tool("mark", root, state, args=("nope.py",))
    check("mark unknown path: exits clean", p.returncode, 0)
    check_in("mark unknown path: named as ignored", "Not tracked, ignored", p.stderr)
    check_in("mark unknown path: nothing recorded", "Nothing to record", p.stdout)

    # Reverting the edit closes the file again with no mark at all, because the
    # recorded hash matches the working tree once more.
    (root / "src/util.js").write_text("export const one = 1\n")
    check("revert: list is empty again", run_tool("list", root, state).stdout, "")

    # A file that leaves the repo leaves the ledger on the next mark.
    git(root, "rm", "-qf", "cli.py")
    (root / "app.py").write_text("value = 3\n")
    run_tool("mark", root, state)
    _, body = ledger(state)
    check("prune: departed file dropped from the ledger",
          sorted((body or {}).get("files", {})), ["app.py", "src/util.js"])


def main():
    with tempfile.TemporaryDirectory() as tmp:
        unit_cases(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        out_of_scope_cases(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        scope_cases(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        lifecycle_cases(tmp)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
