#!/usr/bin/env python3
"""Stripe is read-only until one named object is approved.

Reading the account is the job: customers, invoices, charges, balances, decline
reasons. Every write is an object approved one at a time, and approval for one
object is not approval for the next, so the environment variable that opens the
door names the object it opens it for.

The key carries write scope whatever its name says, so nothing about the
credential stops a write. This does.

  guard-bash   a shell command that writes to Stripe
  guard-mcp    a Stripe tool call that writes

INTELLIGENCE_STRIPE_WRITE=<object id> approves that object and no other.
"""
import json
import os
import re
import sys

# The verbs that change an object, spelled the way each surface spells them.
CLI_WRITE = re.compile(
    r"\bstripe\s+(?:invoices?|customers?|subscriptions?|charges?|refunds?|"
    r"payment_intents?|prices?|products?|coupons?|credit_notes?)\s+"
    r"(?:create|update|delete|void|finalize|send|pay|cancel|refund|expire)\b",
    re.I,
)
CURL_WRITE = re.compile(
    r"api\.stripe\.com/[^\s\"']+", re.I)
CURL_METHOD = re.compile(r"-X\s*(POST|DELETE|PUT|PATCH)\b|--data|-d\s", re.I)

MCP_WRITE = re.compile(r"stripe_api_write|manage_stripe_accounts", re.I)

# A Stripe object identifier, which is what an approval has to name. The account
# is one of them: its business profile carries the support phone printed on every
# receipt, and a settings write no approval string could name was a write the
# door could not be opened for rather than one it was holding shut.
OBJECT_ID = re.compile(r"\b(?:acct|in|cus|sub|ch|re|pi|price|prod|cn|il)_[A-Za-z0-9]{6,}\b"
                       r"|\b[A-Z0-9]{8}-\d{4}\b")

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



def payload():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def approved():
    named = os.environ.get("INTELLIGENCE_STRIPE_WRITE") or ""
    return {m.group(0) for m in OBJECT_ID.finditer(named)}


def refuse(text):
    ids = sorted({m.group(0) for m in OBJECT_ID.finditer(text)})
    sys.stderr.write(
        "BLOCKED: this writes to Stripe.\n\n"
        "Stripe is read-only here. A write is one object approved out loud,\n"
        "and approval for one object is not approval for the next.\n")
    if ids:
        sys.stderr.write("\nobjects this call would change:\n  %s\n"
                         % "\n  ".join(ids))
    sys.stderr.write(
        "\nINTELLIGENCE_STRIPE_WRITE=<object id> approves that one object.\n")
    sys.exit(2)


def guard_bash():
    p = payload()
    command = str((p.get("tool_input") or {}).get("command") or "")
    for segment in acting_segments(command):
        writes = bool(CLI_WRITE.search(segment)) or bool(
            CURL_WRITE.search(segment) and CURL_METHOD.search(segment))
        if not writes:
            continue
        ids = {m.group(0) for m in OBJECT_ID.finditer(segment)}
        if ids and ids <= approved():
            continue
        refuse(segment)


def guard_mcp():
    p = payload()
    if not MCP_WRITE.search(str(p.get("tool_name") or "")):
        return
    body = json.dumps(p.get("tool_input") or {})
    ids = {m.group(0) for m in OBJECT_ID.finditer(body)}
    if ids and ids <= approved():
        return
    refuse(body)


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "guard-bash":
        guard_bash()
    elif verb == "guard-mcp":
        guard_mcp()
    else:
        sys.stderr.write(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
