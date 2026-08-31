#!/usr/bin/env python3
"""No emoji, anywhere the tree produces text.

The rule covers responses, code, commits, comments, filenames and any other
output, and it has no exception, which makes it one of the few rules a pattern
settles completely. Prose in a memory file is read selectively; this is read
every time.

  guard-bash   a shell command, its heredocs included
  guard-edit   file content and the path being written
  guard-stop   the reply about to be handed back
  scan <path>  what a file carries

INTELLIGENCE_ALLOW_EMOJI=1 overrides one write the guard has misread.
"""
import json
import os
import re
import sys

# The pictographic planes, plus the variation selector that turns a text symbol
# into an emoji one, plus the handful of BMP characters that render as emoji
# with no selector. Arrows, box drawing, typographic dashes and the letterlike
# symbols are all outside this, so ordinary output is untouched.
EMOJI = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U0001F1E6-\U0001F1FF"
    "️"
    "✅❌❎✨⭐⭕❗❓❔❕"
    "⚡❤➕➖➗➰➿"
    "]"
)

NAMED = {
    "\U0001F916": "robot face",
    "✅": "white heavy check mark",
    "❌": "cross mark",
    "️": "emoji presentation selector",
}


def hits(text):
    """Every distinct emoji in the text, with the position of the first."""
    seen = {}
    for m in EMOJI.finditer(text or ""):
        seen.setdefault(m.group(0), m.start())
    return seen


def describe(seen):
    rows = []
    for ch, at in sorted(seen.items(), key=lambda kv: kv[1]):
        name = NAMED.get(ch) or "U+%04X" % ord(ch)
        rows.append("  %s  (%s) at offset %d" % (ch, name, at))
    return "\n".join(rows)


def refuse(where, seen):
    sys.stderr.write("BLOCKED: %s carries emoji.\n\n%s\n" % (where, describe(seen)))
    sys.stderr.write(
        "\nNothing this tree produces carries emoji: not responses, code,\n"
        "commits, comments, filenames or any other output.\n"
        "INTELLIGENCE_ALLOW_EMOJI=1 overrides a misread.\n")
    sys.exit(2)


def payload():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def guard_bash():
    p = payload()
    command = str((p.get("tool_input") or {}).get("command") or "")
    seen = hits(command)
    if seen:
        refuse("this command", seen)


def is_own_source(path):
    """Whether the path is this guard or its cases.

    The characters the guard refuses have to be spelled out somewhere for it to
    recognise them, so its own source and the cases that exercise it are the one
    place they are allowed to sit.
    """
    name = os.path.basename(path or "")
    return name in ("emoji-guard.py", "emoji-guard-cases.py")


def guard_edit():
    p = payload()
    inp = p.get("tool_input") or {}
    path = str(inp.get("file_path") or inp.get("notebook_path") or "")
    if is_own_source(path):
        return
    body = "".join(str(inp.get(k) or "")
                   for k in ("content", "new_string", "new_source"))
    old = str(inp.get("old_string") or "")

    # Only what this write adds is judged. A file that already carries one is a
    # separate problem, and refusing every edit to it stops the work that would
    # take it out.
    added = hits(body)
    for ch in list(added):
        if ch in old:
            added.pop(ch)
    if added:
        refuse("this write", added)
    seen = hits(path)
    if seen:
        refuse("this filename", seen)


def last_reply(transcript_path):
    """The text of the final assistant message in the transcript."""
    if not transcript_path or not os.path.exists(transcript_path):
        return ""
    text = ""
    with open(transcript_path, errors="replace") as fh:
        for line in fh:
            if '"assistant"' not in line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            msg = row.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            parts = msg.get("content")
            if isinstance(parts, str):
                text = parts
            elif isinstance(parts, list):
                text = "".join(b.get("text", "") for b in parts
                               if isinstance(b, dict) and b.get("type") == "text")
    return text


def guard_stop():
    p = payload()
    if p.get("stop_hook_active"):
        return
    seen = hits(last_reply(p.get("transcript_path")))
    if seen:
        refuse("this reply", seen)


def main():
    if os.environ.get("INTELLIGENCE_ALLOW_EMOJI") == "1":
        return 0
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "guard-bash":
        guard_bash()
    elif verb == "guard-edit":
        guard_edit()
    elif verb == "guard-stop":
        guard_stop()
    elif verb == "scan":
        bad = 0
        for path in sys.argv[2:]:
            if is_own_source(path):
                continue
            try:
                seen = hits(open(path, errors="replace").read())
            except OSError as exc:
                print("%s: %s" % (path, exc))
                continue
            if seen:
                bad += 1
                print("%s\n%s" % (path, describe(seen)))
        return 1 if bad else 0
    else:
        sys.stderr.write(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
