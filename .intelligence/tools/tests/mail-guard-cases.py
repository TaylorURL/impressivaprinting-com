#!/usr/bin/env python3
"""Cases the mail guard has to get right.

A send reaches the allowed address or it does not go. A send whose recipients
cannot be read is refused on the same terms as one addressed elsewhere, because
an unreadable set is the shape that hides the sends worth stopping. The two
edit rules are exercised in both directions: removing the enrolment write is
refused, leaving it alone is not.

  mail-guard-cases.py        run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "mail-guard.py")

ME = "trenton@taylorurl.com"
FAILURES = []


def run(verb, payload, env=None):
    p = subprocess.run([sys.executable, str(TARGET), verb],
                       input=json.dumps(payload), capture_output=True,
                       text=True, env={**os.environ, **(env or {})})
    return p.returncode


def bash(command, env=None):
    return run("guard-bash", {"tool_name": "Bash",
                              "tool_input": {"command": command}}, env)


def mcp(tool, inp, env=None):
    return run("guard-mcp", {"tool_name": tool, "tool_input": inp}, env)


def edit(path, new, old="", env=None):
    return run("guard-edit", {"tool_name": "Edit", "tool_input": {
        "file_path": path, "new_string": new, "old_string": old}}, env)


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got}, want {want}")


def main():
    check("resend to me",
          bash(f"curl -X POST https://api.resend.com/emails -d 'to={ME}'"), 0)
    check("resend to somebody else",
          bash("curl -X POST https://api.resend.com/emails "
               "-d 'to=owner@example.com'"), 2)
    check("resend to me and somebody else",
          bash("curl -X POST https://api.resend.com/emails "
               f"-d 'to={ME},owner@example.com'"), 2)
    check("recipients from a variable",
          bash("curl -X POST https://api.resend.com/emails -d \"to=$LIST\""), 2)
    check("outreach send route with no address",
          bash("curl -X POST localhost:3000/api/outreach/send"), 2)

    # A command that sends nothing is not this guard's business, whatever
    # addresses it happens to carry.
    check("grep over an address",
          bash("grep -r owner@example.com ."), 0)
    check("git commit naming an address",
          bash("git commit -m 'reply to owner@example.com'"), 0)

    check("send tool to me",
          mcp("mcp__x__outlook_send_mail", {"to": [ME]}), 0)
    check("send tool elsewhere",
          mcp("mcp__x__outlook_send_mail", {"to": ["owner@example.com"]}), 2)
    check("forward elsewhere",
          mcp("mcp__x__outlook_forward_mail", {"to": ["owner@example.com"]}), 2)

    # A draft is not a send.
    check("draft elsewhere",
          mcp("mcp__x__outlook_create_draft", {"to": ["owner@example.com"]}), 0)

    check("named recipient approved",
          mcp("mcp__x__outlook_send_mail", {"to": ["owner@example.com"]},
              {"INTELLIGENCE_MAIL_TO": "owner@example.com"}), 0)
    check("named recipient does not cover a second one",
          mcp("mcp__x__outlook_send_mail",
              {"to": ["owner@example.com", "other@example.com"]},
              {"INTELLIGENCE_MAIL_TO": "owner@example.com"}), 2)

    send_path = "/repo/api/outreach/send.js"
    check("enrolment removed",
          edit(send_path, "await log(row)", "await enrol(row)"), 2)
    check("enrolment kept",
          edit(send_path, "await enrol(row)\nawait log(row)",
               "await enrol(row)"), 0)
    check("constraint against the audience row",
          edit("/repo/supabase/migrations/1.sql",
               "ALTER TABLE subscribers ADD CONSTRAINT subscriber_opt "
               "CHECK (opted_in)"), 2)
    check("postal address into a mail template",
          edit("/repo/lib/mail/footer.js",
               "const FOOTER = '900 Example Street, Houston TX 77002'"), 2)
    check("postal address outside mail",
          edit("/repo/app/contact/page.tsx",
               "const OFFICE = '900 Example Street, Houston TX 77002'"), 0)

    check("guard off", bash("curl -X POST https://api.resend.com/emails "
                            "-d 'to=owner@example.com'",
                            {"INTELLIGENCE_MAIL_OFF": "1"}), 0)

    # A search naming a transport is a reading. A guard that cannot tell the two
    # apart refuses the reading that would have found the real send.
    check("grep for a send endpoint",
          bash("grep -rn '/api/outreach/send' ."), 0)
    check("grep for a transport by name",
          bash("grep -rniE 'resend|sendmail' routine/"), 0)
    check("ls of a mail directory", bash("ls lib/mail/"), 0)
    check("a send sharing a line with a search is still caught",
          bash("grep -rn resend . && curl -X POST https://api.resend.com/emails"
               " -d 'to=owner@example.com'"), 2)

    for f in FAILURES:
        print(f)
    print(f"mail-guard: {len(FAILURES)} failing")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
