#!/usr/bin/env python3
"""A message an agent sends reaches one address and no other.

A send has no undo. The outreach machine and the newsletter firing on their own
schedules are the product working; an agent composing a message and putting it
in front of somebody is a different act, and only that second one passes through
a hook. Every such send is held against the allowed address, and a send whose
recipient set cannot be read is refused rather than allowed and inspected after
it has gone.

Two smaller rules ride along, both decidable from the bytes being written:

  the outreach enrolment write, which the newsletter list depends on
  the postal address, which stays out of mail

  guard-bash   a shell command that sends mail
  guard-mcp    a mail tool call
  guard-edit   an edit to the outreach send path or a mail template
  allow        print the address a send may reach

INTELLIGENCE_MAIL_TO names the recipient set for one deliberate send.
INTELLIGENCE_MAIL_OFF=1 stands the whole guard down.
"""
import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()
DEFAULT_TO = "trenton@taylorurl.com"

ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# The transports that reach a person from a shell. Each carries its recipients
# on the command line or in the body piped to it, so one address scan over the
# whole command sees them either way.
SENDING = re.compile(
    r"\b(?:sendmail|msmtp|mailx|mutt|swaks)\b"
    r"|\bmail\s+-s\b"
    r"|api\.resend\.com/emails"
    r"|api\.sendgrid\.com/v3/mail/send"
    r"|api\.mailgun\.net/v3/[^/\s]+/messages"
    r"|api\.postmarkapp\.com/email"
    r"|api\.brevo\.com/v3/smtp/email"
    r"|/api/(?:outreach|newsletter|mail)/send\b",
    re.I,
)

# The mail tools by the name the harness gives them. A draft is not a send and
# is left alone; only the calls that put a message in flight are held.
SENDING_TOOLS = re.compile(
    r"(?:^|__)(?:outlook_send_mail|outlook_send_draft|outlook_forward_mail"
    r"|gmail_send_message|send_email|send_mail)$",
    re.I,
)

# A street line followed by a city, state and ZIP. The address itself is absent
# from this file: a guard that spells out what it refuses publishes it to every
# machine holding the tree, which is the disclosure the rule prevents.
POSTAL = re.compile(
    r"\b\d{1,6}\s+[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,4}\s+"
    r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|"
    r"Court|Pkwy|Parkway|Hwy|Highway|Ste|Suite|Unit|PO\s+Box|P\.O\.\s+Box)\b"
    r"[^\n]{0,60}?\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\b"
)

MAIL_TEMPLATE = re.compile(r"(?:^|/)(?:mail|email|newsletter|outreach)/", re.I)

# The tools that read rather than act. A search whose pattern happens to name a
# transport is not a send, and a guard that cannot tell the two apart refuses
# the reading that would have found the real one.
READ_ONLY = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*"
    r"(?:sudo\s+)?"
    r"(?:grep|rg|ag|ack|egrep|fgrep|cat|bat|less|more|head|tail|sed|awk|cut|"
    r"sort|uniq|wc|find|fd|ls|tree|file|stat|diff|git\s+grep|git\s+log|"
    r"git\s+show|git\s+diff|echo|printf)\b")


def split_commands(command):
    """A compound line broken at its separators, quotes respected.

    A separator inside quotes belongs to an argument rather than to the shell,
    and splitting on one turns the alternation in a search pattern into a
    command of its own.
    """
    parts, current, quote = [], [], None
    index = 0
    text = command or ""
    while index < len(text):
        char = text[index]
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"":
            quote = char
            current.append(char)
            index += 1
            continue
        if char in ";\n|&":
            run = 2 if text[index:index + 2] in ("&&", "||") else 1
            if char == "&" and run == 1:
                current.append(char)
                index += 1
                continue
            parts.append("".join(current))
            current = []
            index += run
            continue
        current.append(char)
        index += 1
    parts.append("".join(current))
    return parts


def acting_segments(command):
    """The parts of a command that could actually do something.

    Every read-only segment is dropped, so a search naming a transport is left
    alone while a send sharing the line with one is still caught.
    """
    return [part for part in split_commands(command)
            if part.strip() and not READ_ONLY.match(part.strip())]


# The write that puts a business on the newsletter list, and the two shapes that
# take it away: deleting the call, and adding a constraint the row cannot pass.
ENROL_CALL = re.compile(r"\benrol\s*\(")
ENROL_PATH = re.compile(r"api/outreach/send\.(?:js|ts|mjs)$")
AUDIENCE_CONSTRAINT = re.compile(
    r"ADD\s+CONSTRAINT[^\n;]*\b(?:subscriber|audience|newsletter)\b"
    r"|\bCHECK\s*\([^)]*\b(?:opted_in|opt_in|subscribed)\b",
    re.I,
)


def allowed():
    """The addresses a send may reach, read from the environment."""
    named = os.environ.get("INTELLIGENCE_MAIL_TO")
    if named:
        return {a.lower() for a in ADDRESS.findall(named)} or {DEFAULT_TO}
    return {DEFAULT_TO}


def refuse(reason, detail=""):
    sys.stderr.write("BLOCKED: %s\n" % reason)
    if detail:
        sys.stderr.write("\n%s\n" % detail)
    sys.stderr.write(
        "\nINTELLIGENCE_MAIL_TO names the recipients for one deliberate send.\n")
    sys.exit(2)


def payload():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def check_recipients(text, where):
    """Refuse unless every address in the text is one a send may reach.

    Text carrying no address at all is refused too. A recipient set assembled
    from a variable, a file or a query is unreadable at this point, and reading
    unreadable as empty passes exactly the sends worth stopping.
    """
    found = {a.lower() for a in ADDRESS.findall(text)}
    ok = allowed()
    outside = found - ok
    if outside:
        refuse("this send reaches an address outside the allowed set.",
               "outside:\n  " + "\n  ".join(sorted(outside))
               + "\n\nallowed: " + ", ".join(sorted(ok)))
    if not found:
        refuse("this %s sends mail and names no recipient here." % where,
               "The recipient set has to be readable at the point of the send.\n"
               "A set assembled from a variable, a file or a query cannot be\n"
               "checked, so the send stops rather than going out unchecked.")


def guard_bash():
    p = payload()
    command = str((p.get("tool_input") or {}).get("command") or "")
    for segment in acting_segments(command):
        if SENDING.search(segment):
            check_recipients(segment, "command")


def guard_mcp():
    p = payload()
    name = str(p.get("tool_name") or "")
    if not SENDING_TOOLS.search(name):
        return
    check_recipients(json.dumps(p.get("tool_input") or {}), "call")


def guard_edit():
    p = payload()
    inp = p.get("tool_input") or {}
    path = str(inp.get("file_path") or inp.get("notebook_path") or "")
    new = str(inp.get("content") or inp.get("new_string") or "")
    old = str(inp.get("old_string") or "")
    unix = path.replace("\\", "/")

    if ENROL_PATH.search(unix) and ENROL_CALL.search(old) \
            and not ENROL_CALL.search(new):
        refuse("this removes the outreach enrolment write.",
               "Every business the outreach machine writes to joins the\n"
               "newsletter list. US commercial email is opt-out, so a business\n"
               "that never subscribed is a lawful recipient. The one-click\n"
               "unsubscribe and the suppression list are the parts that stay.")

    if AUDIENCE_CONSTRAINT.search(new) and not AUDIENCE_CONSTRAINT.search(old):
        refuse("this adds a constraint refusing the newsletter row.",
               "The enrolment write is deliberate; a constraint against it\n"
               "removes the rows the outreach machine exists to create.")

    if MAIL_TEMPLATE.search(unix) and POSTAL.search(new) \
            and not POSTAL.search(old):
        refuse("this puts a postal address into mail.",
               "The address stays out of the outreach footer and the\n"
               "newsletter. CAN-SPAM asks for one and that is knowingly unmet.")


def main():
    if os.environ.get("INTELLIGENCE_MAIL_OFF") == "1":
        return 0
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "guard-bash":
        guard_bash()
    elif verb == "guard-mcp":
        guard_mcp()
    elif verb == "guard-edit":
        guard_edit()
    elif verb == "allow":
        print("\n".join(sorted(allowed())))
    else:
        sys.stderr.write(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
