#!/usr/bin/env python3
"""Cases the PR attribution sweep has to get right.

The sweep repairs bodies the model never wrote, so its worth is in the edges:
every attribution artifact comes out, and a body whose prose legitimately
names the tool keeps it. The command contract runs against a stand-in gh on
PATH, because the sweep's other job is telling a clean repo apart from one it
never reached, and both of those answers have to be pinned without a network.

  pr-attribution-guard-cases.py        run them
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
              or Path(__file__).resolve().parent.parent / "pr-attribution-guard.py")

FAILURES = []

# Environment keys the copy under test reads at import or in _state_root. Each
# load and each direct call pins them explicitly, so a cloud container's own
# CLAUDE_CODE_REMOTE cannot leak into a case that pins the local default.
ENV_KEYS = ("INTELLIGENCE_STATE_DIR", "CLAUDE_CODE_REMOTE")

# The footer a harness appends server-side, exactly as it lands in a body.
FOOTER = "Generated with [Claude Code](https://claude.ai/code)"

DIRTY = f"Fixes the widget.\n\n---\n{FOOTER}\n"


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load(env=None):
    saved = {k: os.environ.pop(k, None) for k in ENV_KEYS}
    if env:
        os.environ.update(env)
    try:
        spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def state_root_under(mod, env):
    saved = {k: os.environ.pop(k, None) for k in ENV_KEYS}
    os.environ.update(env)
    try:
        return mod._state_root()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def clean_cases():
    mod = load()

    check("footer with rule", mod.clean(DIRTY), "Fixes the widget.\n")

    bare = f"Fixes the widget.\n\n{FOOTER.replace('with', 'by')}"
    check("footer without rule", mod.clean(bare), "Fixes the widget.")

    robot = f"Body.\n\n\N{ROBOT FACE} {FOOTER}\n"
    check("robot footer", mod.clean(robot), "Body.\n")

    link = "Fixed.\n\nhttps://claude.ai/code/session_01ABC\n"
    check("bare session link", mod.clean(link), "Fixed.\n")

    cite = "See https://claude.ai/code/session_01ABC for the transcript.\n"
    check("session link in a sentence kept", mod.clean(cite), None)

    coauthor = "Body.\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"
    check("co-author trailer", mod.clean(coauthor), "Body.\n")

    trailer = "Body.\n\nClaude-Session: https://claude.ai/code/session_x\n"
    check("session trailer", mod.clean(trailer), "Body.\n")

    prose = "This PR updates the Claude API client.\n"
    check("prose mention kept", mod.clean(prose), None)

    # A footer with a session link appended after it is out of reach of the
    # end-anchored patterns until the link comes out, so one call has to settle
    # both and its output has to answer a second call with nothing.
    layered = f"Body.\n\n---\n{FOOTER}\nhttps://claude.ai/code/session_01\n"
    got = mod.clean(layered)
    check("layered artifacts", got, "Body.\n")
    check("strip output passes check", mod.clean(got), None)

    check("empty body", mod.clean(""), None)
    check("missing body", mod.clean(None), None)


def state_cases():
    with tempfile.TemporaryDirectory() as tmp:
        mod = load({"INTELLIGENCE_STATE_DIR": tmp})
        # Every ledger fixture sits inside the temp tree; a STATE that resolves
        # anywhere else would put these files into a live config directory.
        assert str(mod.STATE).startswith(tmp), f"STATE escaped the temp tree: {mod.STATE}"
        for ledger, name in (("comment-pass", "bradley-t-t__widget.json"),
                             ("doc-pass", "TaylorURL__site.json"),
                             ("writing-pass", "bradley-t-t__widget.json"),
                             ("comment-pass", "noseparator.json")):
            d = mod.STATE / ledger
            assert str(d).startswith(tmp), f"ledger escaped the temp tree: {d}"
            d.mkdir(parents=True, exist_ok=True)
            (d / name).write_text("{}")
        check("owned repos from ledgers", mod.owned_repos(),
              ["TaylorURL/site", "bradley-t-t/widget"])

    with tempfile.TemporaryDirectory() as tmp:
        mod = load({"INTELLIGENCE_STATE_DIR": tmp})
        assert str(mod.STATE).startswith(tmp)
        check("empty state reads as no repos", mod.owned_repos(), [])

    mod = load()
    check("state override wins",
          state_root_under(mod, {"INTELLIGENCE_STATE_DIR": "/override/state",
                                 "CLAUDE_CODE_REMOTE": "1"}),
          Path("/override/state"))
    check("remote state root",
          state_root_under(mod, {"CLAUDE_CODE_REMOTE": "1"}),
          Path.home() / ".pass-state")
    check("local state root", state_root_under(mod, {}),
          Path.home() / ".intelligence" / "state")


def git_cases():
    mod = load()
    cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True, capture_output=True)
            os.chdir(tmp)
            check("repo without origin", mod.current_repo(), None)
            subprocess.run(["git", "remote", "add", "origin",
                            "https://github.com/bradley-t-t/widget.git"],
                           check=True, capture_output=True)
            check("https origin", mod.current_repo(), "bradley-t-t/widget")
            subprocess.run(["git", "remote", "set-url", "origin",
                            "git@github.com:TaylorURL/site.git"],
                           check=True, capture_output=True)
            check("ssh origin", mod.current_repo(), "TaylorURL/site")
            subprocess.run(["git", "remote", "set-url", "origin",
                            "https://gitlab.com/x/y.git"],
                           check=True, capture_output=True)
            check("non-github origin", mod.current_repo(), None)
            os.chdir(cwd)
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            check("outside a repo", mod.current_repo(), None)
            os.chdir(cwd)
    finally:
        os.chdir(cwd)


# The stand-in gh serves a fixture pull request list, records every invocation,
# files every PATCH body it receives, and answers any path naming
# unreachable-repo with a refusal, so one binary covers the reachable repo, the
# repaired repo, and the one that never answers.
GH_STUB = '''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
rec = os.environ.get("FAKE_GH_RECORD")
if rec:
    with open(rec, "a") as f:
        f.write(json.dumps(args) + "\\n")
path = args[1] if len(args) > 1 else ""
if "unreachable-repo" in path:
    sys.stderr.write("HTTP 403: forbidden\\n")
    sys.exit(1)
if "PATCH" in args:
    with open(os.environ["FAKE_GH_PATCH"], "a") as f:
        f.write(sys.stdin.read() + "\\n")
    print("{}")
else:
    with open(os.environ["FAKE_GH_PRS"]) as f:
        sys.stdout.write(f.read())
'''


def cli_cases():
    mod = load()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bindir = root / "bin"
        bindir.mkdir()
        gh = bindir / "gh"
        gh.write_text(GH_STUB)
        gh.chmod(0o755)
        prs = root / "prs.json"
        record = root / "record.jsonl"
        patched = root / "patch.jsonl"
        state = root / "state"
        state.mkdir()
        work = root / "work"
        work.mkdir()

        def run(args, pr_bodies):
            prs.write_text(json.dumps(
                [{"number": i + 1, "body": b} for i, b in enumerate(pr_bodies)]))
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            env["FAKE_GH_PRS"] = str(prs)
            env["FAKE_GH_RECORD"] = str(record)
            env["FAKE_GH_PATCH"] = str(patched)
            env["INTELLIGENCE_STATE_DIR"] = str(state)
            env.pop("CLAUDE_CODE_REMOTE", None)
            return subprocess.run([sys.executable, str(TARGET)] + args,
                                  capture_output=True, text=True,
                                  cwd=work, env=env)

        p = run(["check", "o/dirty"], [DIRTY])
        check("check flags attribution", p.returncode, 1)
        check("check names the pull request",
              "o/dirty#1: attribution in body" in p.stdout, True)
        check("check leaves the body alone", patched.exists(), False)

        p = run(["check", "o/clean"], ["Just a fix.\n"])
        check("check passes a clean repo", p.returncode, 0)
        check("check reports zero",
              "0 pull request(s) carry attribution." in p.stdout, True)

        p = run(["strip", "o/dirty"], [DIRTY, "Untouched.\n"])
        check("strip exits clean", p.returncode, 0)
        check("strip reports the repair",
              "Stripped attribution from 1 of 1" in p.stdout, True)
        payloads = [json.loads(l) for l in patched.read_text().splitlines() if l.strip()]
        check("only the affected body is patched", len(payloads), 1)
        check("patched body passes check", mod.clean(payloads[0]["body"]), None)
        check("patched body keeps the prose",
              payloads[0]["body"], "Fixes the widget.\n")

        p = run(["check", "unreachable-repo/x"], [])
        check("every repo unreachable fails", p.returncode, 1)
        check("unreachable repo is named", "unreachable" in p.stderr, True)

        p = run(["check", "o/clean", "unreachable-repo/x"], ["Just a fix.\n"])
        check("partial reach still answers", p.returncode, 0)
        check("missed repo is counted",
              "1 of 2 repo(s) unreachable." in p.stdout, True)

        record.write_text("")
        run(["check", "o/clean", "--limit", "500"], [])
        calls = [json.loads(l) for l in record.read_text().splitlines()]
        check("limit clamps to 100",
              calls[-1][1].rsplit("per_page=", 1)[-1], "100")
        record.write_text("")
        run(["check", "o/clean", "--limit", "0"], [])
        calls = [json.loads(l) for l in record.read_text().splitlines()]
        check("limit floors at 1",
              calls[-1][1].rsplit("per_page=", 1)[-1], "1")

        d = state / "comment-pass"
        d.mkdir()
        (d / "bradley-t-t__widget.json").write_text("{}")
        record.write_text("")
        p = run(["check", "--all"], [])
        check("--all sweeps clean", p.returncode, 0)
        calls = [json.loads(l) for l in record.read_text().splitlines()]
        check("--all reads the ledger repos",
              any("repos/bradley-t-t/widget/pulls" in c[1] for c in calls), True)

    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state"
        state.mkdir()
        env = os.environ.copy()
        env["INTELLIGENCE_STATE_DIR"] = str(state)
        env.pop("CLAUDE_CODE_REMOTE", None)
        p = subprocess.run([sys.executable, str(TARGET), "check", "--all"],
                           capture_output=True, text=True, cwd=tmp, env=env)
        check("empty ledger with --all refuses", p.returncode, 2)
        check("refusal names the fix", "no repo to sweep" in p.stderr, True)
        p = subprocess.run([sys.executable, str(TARGET), "check"],
                           capture_output=True, text=True, cwd=tmp, env=env)
        check("no repo in reach refuses", p.returncode, 2)


def main():
    clean_cases()
    state_cases()
    git_cases()
    cli_cases()
    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
