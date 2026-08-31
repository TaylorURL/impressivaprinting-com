#!/usr/bin/env python3
"""Remove credential values from session transcripts.

A vault tool that answers with a secret answers into the transcript, and the
harness writes that file to disk. Every such value is therefore sitting in plain
text for as long as the transcript survives -- weeks past the command it was
fetched for, and long past any rotation. The vault no longer hands one to a
session, but the transcripts written before that still hold what it handed over.

    transcript-scrub.py scan            # what is there, without printing any of it
    transcript-scrub.py clean [--yes]   # replace each value in place

Two shapes carry a secret: the result of a credential_get, and the `secret`
argument of a credential_put. Both are replaced with a marker. Nothing else in
the file is touched -- a line with no secret in it is not even parsed, so the
rest of the transcript stays byte for byte what it was.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path.home() / ".intelligence" / "projects"
MARKER = "[credential value removed]"
LIVE_SECONDS = 300
GET = "credential_get"
PUT = "credential_put"

# Shapes worth counting separately in a scan, so a report can say what class of
# credential is exposed without ever rendering one.
SHAPES = [
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("jwt or service role", r"^eyJ[A-Za-z0-9_-]{20,}\."),
    ("stripe key", r"^(sk|rk)_(live|test)_"),
    ("github token", r"^gh[pousr]_[A-Za-z0-9]{20,}"),
    ("url with a password", r"^\w+://[^:/]+:[^@]+@"),
    ("opaque, 32 or more", r"^[A-Za-z0-9_\-\.=+/]{32,}$"),
]


ID_RE = re.compile(r"toolu_[A-Za-z0-9_-]+")


def classify(value):
    for name, pattern in SHAPES:
        if re.search(pattern, value):
            return name
    return "short or unrecognised"


def blocks(line):
    """The content blocks of a transcript line, or nothing if it carries none."""
    try:
        record = json.loads(line)
    except ValueError:
        return None, None
    content = (record.get("message") or {}).get("content")
    return (record, content) if isinstance(content, list) else (None, None)


def get_ids(files):
    """Every tool_use id belonging to a credential_get, across all files.

    Collected before any file is rewritten because a resumed session replays
    earlier messages into a new transcript, which can separate a call from its
    answer.
    """
    ids = set()
    for path in files:
        with open(path, errors="replace") as fh:
            for line in fh:
                if GET not in line:
                    continue
                _, content = blocks(line)
                for block in content or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        if GET in str(block.get("name", "")):
                            ids.add(block.get("id"))
    return ids


def scrub_line(line, ids, found):
    """Return the line with any credential value replaced, or None if untouched."""
    record, content = blocks(line)
    if content is None:
        return None
    hit = False
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_result" and block.get("tool_use_id") in ids:
            body = block.get("content")
            if isinstance(body, list):
                for part in body:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        text = part["text"].strip()
                        if text and text != MARKER and not text.startswith("not found"):
                            found.append(classify(text))
                            part["text"] = MARKER
                            hit = True
            elif isinstance(body, str) and body.strip() and body.strip() != MARKER:
                found.append(classify(body.strip()))
                block["content"] = MARKER
                hit = True
        elif block.get("type") == "tool_use" and PUT in str(block.get("name", "")):
            args = block.get("input")
            if isinstance(args, dict) and isinstance(args.get("secret"), str):
                if args["secret"] and args["secret"] != MARKER:
                    found.append(classify(args["secret"]))
                    args["secret"] = MARKER
                    hit = True
    return json.dumps(record, ensure_ascii=False) + "\n" if hit else None


def walk(files, ids, write):
    """Scrub every file, counting what was found. Rewrites only when `write`."""
    tally, touched, live = {}, [], []
    for path in files:
        found, out, changed = [], [], False
        with open(path, errors="replace") as fh:
            for line in fh:
                # A tool_result names the call it answers by id, not by tool
                # name, so filtering on the tool name would skip every answer.
                candidate = PUT in line or bool(ids.intersection(ID_RE.findall(line)))
                fixed = scrub_line(line, ids, found) if candidate else None
                out.append(fixed if fixed else line)
                changed = changed or bool(fixed)
        if not changed:
            continue
        touched.append(path)
        for shape in found:
            tally[shape] = tally.get(shape, 0) + 1
        if not write:
            continue
        # A transcript the harness is still appending to is left alone: moving a
        # new file over it would strand the writer on the old inode and lose
        # whatever the session says next. The run that follows this one takes it.
        if time.time() - os.path.getmtime(path) < LIVE_SECONDS:
            live.append(path)
            continue
        # Written beside the original and moved over it, so an interrupted run
        # leaves the transcript it was holding rather than half of one.
        temp = str(path) + ".scrub"
        with open(temp, "w") as fh:
            fh.writelines(out)
        os.replace(temp, path)
    return tally, touched, live


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["scan", "clean"])
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--yes", action="store_true", help="rewrite without asking")
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    if not root.is_dir():
        print("no transcripts at %s" % root, file=sys.stderr)
        return 1
    files = sorted(root.glob("**/*.jsonl"))
    ids = get_ids(files)
    tally, touched, _ = walk(files, ids, write=False)
    total = sum(tally.values())

    if not total:
        print("%d transcripts, no credential values in them" % len(files))
        return 0
    print("%d credential values across %d of %d transcripts" % (total, len(touched), len(files)))
    for shape in sorted(tally, key=lambda k: -tally[k]):
        print("  %4d  %s" % (tally[shape], shape))
    if args.action == "scan":
        return 0
    if not args.yes and sys.stdin.isatty():
        if input("replace them in place? [y/N] ").strip().lower() != "y":
            return 1
    _, done, live = walk(files, ids, write=True)
    left, _, _ = walk(sorted(root.glob("**/*.jsonl")), ids, write=False)
    remaining = sum(left.values())
    print("rewrote %d transcripts; %d values left" % (len(done), remaining))
    if live:
        print("%d still being written; run again once the session ends" % len(live))
    return 0 if remaining == len(live) or not remaining else 1


if __name__ == "__main__":
    sys.exit(main())
