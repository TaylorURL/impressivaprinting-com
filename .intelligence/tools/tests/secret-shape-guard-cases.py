#!/usr/bin/env python3
"""Cases the credential shape guard has to get right.

Each shape is refused on a command line and in a write. GitHub tokens are the
deliberate absence and are exercised as such: one on a command line passes,
because they live in the synced settings file on purpose and raising one is
itself a defect. Placeholders and shell interpolations pass, since a fixture
needs a key-shaped value and a variable is not a value at all.

  secret-shape-guard-cases.py        run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent
              / "secret-shape-guard.py")

# Key-shaped values that are not keys. Each is built to match a pattern and
# nothing here has ever been live.
AWS = "AKIA" + "Q" * 16
SLACK = "xoxb-" + "1" * 24
STRIPE_LIVE = "sk_live_" + "b" * 24
GOOGLE = "AIza" + "C" * 35
ANTHROPIC = "sk-ant-" + "d" * 24
NPM = "npm_" + "e" * 36
GITHUB = "ghp_" + "f" * 36
FAILURES = []


def run(verb, payload, env=None):
    p = subprocess.run([sys.executable, str(TARGET), verb],
                       input=json.dumps(payload), capture_output=True,
                       text=True, env={**os.environ, **(env or {})})
    return p.returncode


def bash(command, env=None):
    return run("guard-bash", {"tool_name": "Bash",
                              "tool_input": {"command": command}}, env)


def edit(path, new, old="", env=None):
    return run("guard-edit", {"tool_name": "Edit", "tool_input": {
        "file_path": path, "new_string": new, "old_string": old}}, env)


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got}, want {want}")


def main():
    for name, value in (("aws", AWS), ("slack", SLACK),
                        ("stripe live", STRIPE_LIVE), ("google", GOOGLE),
                        ("anthropic", ANTHROPIC), ("npm", NPM)):
        check(f"{name} on a command line",
              bash(f"curl -H 'Authorization: Bearer {value}' https://x"), 2)
        check(f"{name} in a write",
              edit("/repo/.env", f"KEY={value}"), 2)

    # Assembled from parts for the same reason as the URL below: written out,
    # the marker makes this file itself read as a leaked key to every scanner
    # that reads the tree, the mirror's own among them.
    block = "-----BEGIN " + "OPENSSH PRIVATE" + " KEY-----\nabc"
    check("private key block in a write", edit("/repo/id_rsa", block), 2)
    # Assembled from parts, so no substring of this file is shaped like a
    # connection URL and the mirror's content gate lets the file through.
    parts = ("postgres", "app", "hunter2hunter", "db.internal.taylorurl.com")
    url = "%s://%s:%s@%s/app" % parts
    check("credentialled url", bash("psql " + url), 2)
    # The reserved documentation hosts are fixtures whatever they carry.
    doc = "%s://%s:%s@%s/app" % (parts[0], parts[1], parts[2], "db.example.com")
    check("credentialled url at a documentation host", bash("psql " + doc), 0)

    # GitHub tokens are deliberate and are never a finding.
    check("github token on a command line",
          bash(f"GH_TOKEN={GITHUB} gh pr list"), 0)
    check("github token in settings",
          edit("/repo/settings.json", f'"GH_TOKEN": "{GITHUB}"'), 0)

    check("the wrapper that does this correctly",
          bash("~/.intelligence/tools/with-credential.py "
               "google-pagespeed-api-key=GOOGLE_PAGESPEED_API_KEY -- psi.py"), 0)
    check("a variable rather than a value",
          bash("curl -H \"Authorization: Bearer $ANTHROPIC_API_KEY\" https://x"),
          0)
    check("a placeholder in a fixture",
          edit("/repo/test.py", 'KEY = "AIzaSyTHIS-IS-NOT-A-REAL-KEY-000000000"'),
          0)
    check("an ordinary command", bash("git status"), 0)
    check("an ordinary write", edit("/repo/README.md", "# Title"), 0)

    # A value already in the file is not what this write is adding.
    check("value already present",
          edit("/repo/.env", f"KEY={AWS}\nOTHER=1", f"KEY={AWS}"), 0)

    check("guard off", bash(f"echo {AWS}",
                            {"INTELLIGENCE_ALLOW_SECRET": "1"}), 0)

    for f in FAILURES:
        print(f)
    print(f"secret-shape-guard: {len(FAILURES)} failing")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
