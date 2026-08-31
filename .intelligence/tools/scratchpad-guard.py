#!/usr/bin/env python3
"""One scratchpad, one lane per agent, so two of them cannot write the same file.

The harness documents the scratchpad as session-specific and isolated, and for a
session on its own it is. Subagents inherit the session id of whoever spawned
them, so a fleet of them is handed one directory between them, and the guarantee
stops holding at exactly the moment it starts mattering.

What that costs is not theoretical. During the reporting rollout on 2026-08-31
one agent wrote its merged snippet to `reporter-body.js` and read the same path
back a tool call later to splice into `index.html`. A sibling had overwritten it
in between, so the file went in twice carrying another client's name -- first
"Dickinson Bayou Fleeting", then "Smyrna Tools" -- and a `git add` staged it.
Only an assertion on the staged content caught it. The generic filename was not
the mistake; two writers sharing one path was.

So a path in the scratchpad root is refused and a path in the caller's own lane
is not. The lane is the agent's transcript name, which is the one thing that
differs between siblings sharing a session id, and it is created on refusal so
the way forward is a path that already exists.

  scratchpad-guard.py guard      refuse a read or write outside the caller's lane
  scratchpad-guard.py lane       print the lane this caller should be using

Reading another lane is refused alongside writing it: the damage in the incident
was done by the read, and a lane nobody else writes is only worth having if
nobody else reads it either.

INTELLIGENCE_ALLOW_SCRATCHPAD=1 stands it down for a caller that has to reach
across, which is the person's escape hatch and not a way past a refusal.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# The harness builds this path, so it is matched on its shape rather than read
# from anywhere: a guard that took it from the environment would pass anything
# for a caller whose environment had lost it.
ROOT = re.compile(r"(?P<root>/(?:private/)?tmp/claude-\d+/[^/\s]+/"
                  r"[0-9a-fA-F-]{36}/scratchpad)(?P<rest>/[^\s'\"|;)&]*)?")


def lane_of(payload):
    """The caller's own lane, taken from the transcript only it writes.

    Subagents share their parent's session id and differ by transcript, so the
    transcript is what can tell two siblings apart. A payload carrying none is
    the parent session itself.
    """
    transcript = str(payload.get("transcript_path") or "")
    if not transcript:
        return "main"
    path = Path(transcript)
    if path.parent.name != "subagents":
        return "main"
    return path.stem or "main"


# `SP=/.../scratchpad` then `$SP/reporter-body.js` is the same path written two
# ways, and only one of them is a path. Assignments are resolved before the
# match so the shell's own indirection is not a way around the lane.
ASSIGN = re.compile(r"(?m)(?:^|[;&|]|\bexport\s+)\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
                    r"=(?P<quote>['\"]?)(?P<value>[^\s'\";|&)]+)(?P=quote)")
# Standing in the shared root puts every later relative path in it, so entering
# it is refused the same as writing into it.
ENTER = re.compile(r"\bcd\s+(?P<quote>['\"]?)(?P<path>[^\s'\";|&)]+)(?P=quote)")


def expand(command):
    """The command with any variable holding a scratchpad path written out."""
    text = str(command or "")
    for match in ASSIGN.finditer(text):
        value = match.group("value")
        if not ROOT.search(value):
            continue
        name = match.group("name")
        text = text.replace("${%s}" % name, value).replace("$" + name, value)
    return text


def targets(payload):
    """Every scratchpad path this call would touch, as (root, rest, entered).

    `rest` is what follows the root, and `entered` says the caller is standing in
    the root rather than naming it, which puts every later relative path there.
    """
    found = []
    tool_input = payload.get("tool_input") or {}

    def collect(text, allow_enter):
        for match in ROOT.finditer(text):
            found.append((match.group("root"),
                          (match.group("rest") or "").lstrip("/"), False))
        if not allow_enter:
            return
        for entering in ENTER.finditer(text):
            match = ROOT.fullmatch(entering.group("path").rstrip("/"))
            if not match:
                continue
            rest = (match.group("rest") or "").lstrip("/")
            # Entering a lane is ordinary; entering the root above them is what
            # puts a later relative path in everyone's way.
            found.append((match.group("root"), rest, not rest))

    for key in ("file_path", "notebook_path", "path"):
        value = tool_input.get(key)
        if value:
            collect(str(value), False)
    for key in ("command", "content", "new_string", "old_string"):
        value = tool_input.get(key)
        if not value:
            continue
        is_command = key == "command"
        collect(expand(value) if is_command else str(value), is_command)
    return found


def verdict(payload):
    """The first path that leaves the caller's lane, or None."""
    lane = lane_of(payload)
    for root, rest, entered in targets(payload):
        if entered:
            return lane, root, ""
        if not rest:
            continue  # the root named in passing, not written into
        if rest.split("/")[0] != lane:
            return lane, root, rest
    return None


def guard():
    if os.environ.get("INTELLIGENCE_ALLOW_SCRATCHPAD") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    answer = verdict(payload)
    if not answer:
        return 0
    lane, root, rest = answer
    try:
        Path(root, lane).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    sys.stderr.write(
        "BLOCKED: that scratchpad path is shared with the other agents.\n\n"
        "  reaching for: %s/%s\n"
        "  your lane is: %s/%s/\n\n"
        "Every agent in this session was handed the same scratchpad, so a file "
        "named\nthere is a file a sibling can overwrite between your writing it "
        "and your\nreading it back. That has already put one client's content "
        "into another\nclient's repository.\n\n"
        "The lane exists now. Put the same file at:\n\n  %s/%s/%s\n\n"
        "INTELLIGENCE_ALLOW_SCRATCHPAD=1 exempts a caller that has to reach "
        "across.\n" % (root, rest, root, lane, root, lane, rest))
    return 2


def main(argv):
    if len(argv) != 1 or argv[0] not in ("guard", "lane"):
        sys.stderr.write(__doc__)
        return 2
    if argv[0] == "lane":
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            payload = {}
        print(lane_of(payload))
        return 0
    return guard()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
