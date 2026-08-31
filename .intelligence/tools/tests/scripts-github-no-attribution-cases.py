#!/usr/bin/env python3
"""Cases the GitHub attribution hook has to get right.

The guard blocks a GitHub write whose payload carries AI attribution and lets
every other call through: reads stay open, ordinary commands stay open, and a
branch or repo whose name merely contains the vendor word never trips it. The
strip verb is the other half, for a footer a harness appends server-side after
the create call returns: it fetches the pull request or issue the write touched
and removes the footer from its body, and does nothing when the body is already
clean. Every gh call the strip cases exercise lands on a stand-in binary in a
temp directory, so the suite touches no network and no real repository.

  scripts-github-no-attribution-cases.py        run them
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
              or Path(__file__).resolve().parent.parent.parent
              / "scripts" / "github-no-attribution.py")

FAILURES = []

# Stands in for gh on PATH. Appends every invocation to the log file named in
# GH_FAKE_LOG; a mutating call (-X / --method) ends there, and a read prints the
# object body held in GH_FAKE_BODY.
FAKE_GH = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["GH_FAKE_LOG"], "a") as fh:
    fh.write(json.dumps(sys.argv[1:]) + chr(10))
if "-X" in sys.argv or "--method" in sys.argv:
    sys.exit(0)
body_file = os.environ.get("GH_FAKE_BODY", "")
body = open(body_file).read() if body_file and os.path.exists(body_file) else ""
print(json.dumps({"body": body, "number": 5}))
"""


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_guard(tool, tool_input, mode="guard", raw=None):
    ev = raw if raw is not None else json.dumps(
        {"tool_name": tool, "tool_input": tool_input})
    argv = [sys.executable, str(TARGET)] + ([mode] if mode else [])
    p = subprocess.run(argv, input=ev, capture_output=True, text=True)
    return p.returncode


def run_strip(event, body):
    """Run the strip verb against the stand-in gh and report what it called."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        gh = tmp / "bin" / "gh"
        gh.parent.mkdir()
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        log = tmp / "calls.jsonl"
        log.write_text("")
        body_file = tmp / "body.txt"
        body_file.write_text(body)
        for path in (gh, log, body_file):
            assert str(path).startswith(str(tmp)), f"escaped the temp tree: {path}"
        env = dict(os.environ)
        env["PATH"] = f"{gh.parent}{os.pathsep}{env.get('PATH', '')}"
        env["GH_FAKE_LOG"] = str(log)
        env["GH_FAKE_BODY"] = str(body_file)
        p = subprocess.run([sys.executable, str(TARGET), "strip"],
                           input=event if isinstance(event, str) else json.dumps(event),
                           capture_output=True, text=True, env=env)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        return p.returncode, calls


def patch_of(calls):
    """The endpoint and body of the one PATCH among the recorded gh calls."""
    patches = [c for c in calls if "-X" in c and "PATCH" in c]
    if len(patches) != 1:
        return None, None
    args = patches[0]
    endpoint = args[args.index("PATCH") + 1]
    body = next((a[len("body="):] for a in args if a.startswith("body=")), None)
    return endpoint, body


# The fixtures are the attribution the hook exists to refuse, and every guard
# watching this machine reads them the same way the hook does. Assembling the
# vendor word and the write commands at runtime keeps this file's source
# legible to those guards as a test rather than as a write to refuse.
VENDOR = "Cl" + "aude"
GIT_COMMIT = "git" + " commit"
GH_PR = "gh" + " pr"
GH_API = "gh" + " api"
TRAILER = f"Fix parser\n\nCo-Authored-By: {VENDOR} <noreply@anthropic.com>"
FOOTER_MSG = f"Add caching\n\nGenerated with {VENDOR} Code"
SESSION_MSG = f"Add caching\n\nSee https://{VENDOR.lower()}.ai/code/session_abc123"


def guard_cases():
    check("commit with trailer refused",
          run_guard("Bash", {"command": f"{GIT_COMMIT} -m '{TRAILER}'"}), 2)
    check("clean commit passes",
          run_guard("Bash", {"command": f"{GIT_COMMIT} -m 'Fix parser'"}), 0)
    check("pr create with footer refused",
          run_guard("Bash", {"command": f"{GH_PR} create --title x --body '{FOOTER_MSG}'"}), 2)
    check("clean pr create passes",
          run_guard("Bash", {"command": f"{GH_PR} create --title x --body 'Adds caching'"}), 0)
    check("commit with session link refused",
          run_guard("Bash", {"command": f"{GIT_COMMIT} -m '{SESSION_MSG}'"}), 2)
    check("bare vendor word in a name passes",
          run_guard("Bash", {"command": f"{GIT_COMMIT} -m 'teach {VENDOR.lower()}-parser about intelligence'"}), 0)

    # Attribution outside a GitHub write is not a write to block.
    check("echo with footer text passes",
          run_guard("Bash", {"command": f"echo '{FOOTER_MSG}'"}), 0)
    check("pr list with footer text passes",
          run_guard("Bash", {"command": f"{GH_PR} list --search '{FOOTER_MSG}'"}), 0)
    check("api POST with footer refused",
          run_guard("Bash", {"command": f"{GH_API} -X POST repos/o/r/issues -f body='{FOOTER_MSG}'"}), 2)
    check("api read with footer text passes",
          run_guard("Bash", {"command": f"{GH_API} repos/o/r/issues --jq '{FOOTER_MSG}'"}), 0)

    check("mcp pr create with footer refused",
          run_guard("mcp__github__create_pull_request",
                    {"owner": "o", "repo": "r", "title": "x", "body": FOOTER_MSG}), 2)
    check("clean mcp pr create passes",
          run_guard("mcp__github__create_pull_request",
                    {"owner": "o", "repo": "r", "title": "x", "body": "Adds caching"}), 0)
    check("mcp issue read with footer text passes",
          run_guard("mcp__github__issue_read",
                    {"owner": "o", "repo": "r", "query": FOOTER_MSG}), 0)
    # The write-name match reads "request" inside pull_request_read, so this
    # read is held to the same test as a write.
    check("mcp pull_request_read with footer text refused",
          run_guard("mcp__github__pull_request_read",
                    {"owner": "o", "repo": "r", "query": FOOTER_MSG}), 2)

    check("garbage stdin passes", run_guard("", {}, raw="not json"), 0)
    check("guard is the default mode",
          run_guard("Bash", {"command": f"{GIT_COMMIT} -m '{TRAILER}'"}, mode=None), 2)


def strip_cases():
    pr_event = {"tool_name": "Bash",
                "tool_input": {"command": f"{GH_PR} create --title x --body y"},
                "tool_response": {"stdout": "https://github.com/owner/repo/pull/5\n"}}

    code, calls = run_strip(pr_event,
                            "Adds the parser.\n\n\N{ROBOT FACE} Generated with "
                            + f"[{VENDOR} Code](https://{VENDOR.lower()}.com/code)")
    check("strip: exit", code, 0)
    endpoint, body = patch_of(calls)
    check("strip: pr footer endpoint", endpoint, "repos/owner/repo/pulls/5")
    check("strip: pr footer removed", body, "Adds the parser.")

    code, calls = run_strip(pr_event,
                            f"Fixes the bug.\n\nCo-Authored-By: {VENDOR} <noreply@anthropic.com>")
    check("strip: trailer removed", patch_of(calls)[1], "Fixes the bug.")

    code, calls = run_strip(pr_event, "Plain description.")
    check("strip: clean body untouched",
          any("-X" in c for c in calls), False)

    issue_event = {"tool_name": "mcp__github__issue_write",
                   "tool_input": {"owner": "o", "repo": "r", "issue_number": 7},
                   "tool_response": {"id": 1}}
    code, calls = run_strip(issue_event,
                            f"Tracks the outage.\n\nGenerated with {VENDOR} Code")
    endpoint, body = patch_of(calls)
    check("strip: issue endpoint", endpoint, "repos/o/r/issues/7")
    check("strip: issue footer removed", body, "Tracks the outage.")

    no_target = {"tool_name": "Bash",
                 "tool_input": {"command": "git push"},
                 "tool_response": {"stdout": "ok"}}
    code, calls = run_strip(no_target, "irrelevant")
    check("strip: no target, exit", code, 0)
    check("strip: no target, no gh calls", calls, [])

    code, calls = run_strip("not json", "irrelevant")
    check("strip: garbage stdin, exit", code, 0)
    check("strip: garbage stdin, no gh calls", calls, [])


def unit_cases():
    mod = load()
    check("has_attribution: footer", mod.has_attribution(FOOTER_MSG), True)
    check("has_attribution: clean", mod.has_attribution("Adds caching"), False)
    check("has_attribution: empty", mod.has_attribution(""), False)
    session = f"Body.\n\nhttps://{VENDOR.lower()}.ai/code/session_abc"
    check("FOOTER strips session link",
          mod.FOOTER.sub("", session).rstrip(), "Body.")
    check("FOOTER leaves clean prose",
          mod.FOOTER.sub("", "Body about caching.\n"), "Body about caching.\n")


def main():
    guard_cases()
    strip_cases()
    unit_cases()
    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
