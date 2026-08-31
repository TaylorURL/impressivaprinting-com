#!/usr/bin/env python3
"""What this setup keeps getting wrong, read from its own transcripts.

A rule that has to be given twice is not a rule anybody is following. It is a
rule with no mechanism behind it, and the second telling costs exactly what the
first one did. The tree answers this for the rules somebody thought to mechanise
and answers nothing for the rules nobody has noticed repeating yet, because
noticing takes reading a fortnight of transcripts and nobody reads those.

So this reads them. Every correction and every refusal is fingerprinted and
counted across sessions, and what comes back is the short list of things that
happened in more than one. One occurrence is an incident. The same thing in
three sessions is a missing mechanism, and that is the whole judgement this tool
makes.

It makes no others. What a pattern deserves -- a guard, a line of context, or
nothing -- takes reading the code around it, and that is the routine's work
rather than a script's. What this does is spend no tokens finding the
candidates: the transcripts are read in process and never enter a context
window, and what reaches one is a ranked list with a count and one example
apiece.

  lessons.py scan [--days N] [--min-sessions N]   read, fingerprint, rank
  lessons.py list [--all]                         what is outstanding
  lessons.py mark <id> --as enforced|context|declined --note "why"
  lessons.py report                               what changed on the last scan

scan exits non-zero while anything is outstanding, so a routine that ignores it
is not a routine that answered it.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _shared():
    """The shared _lib module, loaded by path.

    Hooks and routines run this from arbitrary directories, so the module is
    found beside this file rather than through sys.path, with the installed
    tree as the fallback for a copy executed from elsewhere.
    """
    here = Path(__file__).resolve().parent / "_lib.py"
    path = here if here.is_file() else Path.home() / ".intelligence" / "tools" / "_lib.py"
    spec = importlib.util.spec_from_file_location("intelligence_tools_lib", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_lib = _shared()
state_root = _lib.state_root

HOME = Path.home()
TRANSCRIPTS = Path(os.environ.get("INTELLIGENCE_TRANSCRIPTS")
                   or HOME / ".intelligence" / "projects")

# A fortnight is the window a habit is visible in. Shorter and a weekly rhythm
# reads as noise; longer and a lesson already mechanised keeps being re-found
# from the sessions before the fix.
WINDOW_DAYS = 14

# One session is an incident. The same thing in two is what this exists to find,
# and the threshold is deliberately low: a false positive costs a glance and a
# missed one costs the correction being given again.
MIN_SESSIONS = 2

# What a run carries back. Past this the list stops being read, which is the
# failure mode every report of this shape has.
SHORTLIST = 12

NOW = lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat()

# Words carrying no topic. Fingerprinting on content words is what lets two
# corrections about one thing collide without matching on exact wording.
#
# The second block is the vocabulary of complaining itself. By the time a turn
# is fingerprinted it has already matched as a correction, so the words that
# made it one say nothing about which rule was broken. Leaving them in holds two
# spellings of one complaint apart -- an instruction to stop adding emoji and a
# report that emoji keep being added are the same lesson twice, and joining
# those up is the whole of what this tool does.
STOPWORDS = frozenset("""
stop stopped stopping keep keeps keeping said say says saying told tell telling
asked ask asking never always again wrong supposed meant doing done add adds
adding added remove removes removing removed
""".split()) | frozenset("""
about after again against all also always am an and any are aren as at be
because been before being below between both but by can cant cannot could
couldnt did didnt do does doesnt doing dont down during each few for from
further had hadnt has hasnt have havent having he her here hers herself him
himself his how if in into is isnt it its itself just let me more most must
my myself no nor not now of off on once only or other ought our ours ourselves
out over own same shant she should shouldnt so some such than that thats the
their theirs them themselves then there theres these they this those through
to too under until up very was wasnt we were werent what whats when where which
while who whom why with wont would wouldnt you your yours yourself yourselves
please thanks thank ok okay yeah yes need want make sure go going get got put
use using run ran like really actually thing things way ways time
""".split())

# A correction is a short turn saying the last thing was wrong, or that a
# standing instruction was not followed. The patterns are deliberately narrow: a
# loose one turns every ordinary instruction into a lesson and the list stops
# being read.
CORRECTION = re.compile(
    r"\bkeep (?:doing|saying|adding|forgetting)\b"
    r"|\btold you\b|\basked you\b|\bi (?:already )?said\b|\bas i said\b"
    r"|\bstop (?:doing|using|adding|saying|calling)\b"
    r"|\bthat(?:'s| is) not what\b|\bthat(?:'s| is) wrong\b"
    r"|\bdon't (?:ever )?(?:do|add|use|say|call|write|commit|create)\b"
    r"|\bdo not (?:ever )?(?:do|add|use|say|call|write|commit|create)\b"
    r"|\bnever (?:do|add|use|say|call|write|commit|create|again)\b"
    r"|\bsupposed to\b|\bmeant to\b"
    r"|\bshouldn't have to\b|\bshould not have to\b"
    r"|\bwrong again\b|\bagain\.\s*$",
    re.I)

# A refusal this tree raised. Every guard answers in the same shape, so the
# first line after the marker is the rule that fired.
BLOCKED = re.compile(r"BLOCKED:\s*(.+)")

# The turns a correction cannot be. A quoted transcript, a pasted log and a diff
# all carry the words without anybody having said them.
FENCE = re.compile(r"```.*?```", re.S)

MAX_CORRECTION_CHARS = 600


# ------------------------------------------------------------------- ledger


def ledger_path():
    return state_root() / "lessons" / "ledger.json"


def load():
    path = ledger_path()
    if not path.is_file():
        return {"lessons": {}, "last_scan": None, "scans": 0}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {"lessons": {}, "last_scan": None, "scans": 0}


def save(ledger):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _lib.write_atomic(path, json.dumps(ledger, indent=2, sort_keys=True) + "\n")


# -------------------------------------------------------------- the reading


def topic(text):
    """A fingerprint of what a turn is about rather than of how it was worded.

    Two complaints about one thing rarely share a sentence and almost always
    share their nouns, so the key is the content words: lowercased, stripped of
    everything carrying no topic, deduplicated, sorted, and cut to the six that
    survive. Sorting is what makes word order irrelevant.
    """
    words = re.findall(r"[a-z][a-z-]{3,}", text.lower())
    keep = sorted({w for w in words if w not in STOPWORDS})[:6]
    return " ".join(keep)


def fingerprint(kind, key):
    return "%s-%s" % (kind, hashlib.sha256(key.encode()).hexdigest()[:10])


def text_of(message):
    """The prose of a message, whatever shape its content arrived in."""
    content = message.get("content") if isinstance(message, dict) else message
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    out = []
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text":
            out.append(part.get("text") or "")
        elif isinstance(part, str):
            out.append(part)
    return "\n".join(out)


def transcripts(days):
    """Every session file written inside the window, newest first."""
    if not TRANSCRIPTS.is_dir():
        return []
    cutoff = time.time() - days * 86400
    found = []
    for path in TRANSCRIPTS.rglob("*.jsonl"):
        try:
            stamp = path.stat().st_mtime
        except OSError:
            continue
        if stamp >= cutoff:
            found.append((stamp, path))
    return [path for _, path in sorted(found, reverse=True)]


def harvest(days):
    """Every correction and refusal in the window, grouped by what it is about.

    A sidechain is a subagent's transcript. Its user turns are the prompt this
    tree wrote rather than anything a person said, so counting them would find
    this setup's own instructions and file them as corrections.
    """
    seen = defaultdict(lambda: {"sessions": set(), "count": 0, "example": "",
                                "kind": "", "at": ""})
    for path in transcripts(days):
        session = path.stem
        for row in _lib.read_transcript(path):
            kind = row.get("type")
            if row.get("isSidechain"):
                continue
            if kind == "user":
                body = FENCE.sub(" ", text_of(row.get("message") or {})).strip()
                if not body or len(body) > MAX_CORRECTION_CHARS:
                    continue
                if body.startswith("<") or not CORRECTION.search(body):
                    continue
                key = topic(body)
                if not key:
                    continue
                mark = fingerprint("said", key)
                entry = seen[mark]
                entry["kind"] = "correction"
                entry["example"] = entry["example"] or " ".join(body.split())[:200]
            elif kind == "system":
                blob = json.dumps(row.get("hookErrors") or "") + \
                    json.dumps(row.get("hookInfos") or "")
                hit = BLOCKED.search(blob)
                if not hit:
                    continue
                line = " ".join(hit.group(1).split())[:150].strip('"\\ ')
                mark = fingerprint("guard", topic(line) or line)
                entry = seen[mark]
                entry["kind"] = "refusal"
                entry["example"] = entry["example"] or line
            else:
                continue
            entry["sessions"].add(session)
            entry["count"] += 1
            entry["at"] = row.get("timestamp") or entry["at"]
    return seen


def scan(days, min_sessions, as_json):
    """Fold this window's reading into the ledger and report what stands out."""
    found = harvest(days)
    ledger = load()
    lessons = ledger["lessons"]
    fresh, grown = [], []

    for mark, entry in found.items():
        sessions = len(entry["sessions"])
        if sessions < min_sessions:
            continue
        held = lessons.get(mark)
        if held is None:
            lessons[mark] = {"kind": entry["kind"], "example": entry["example"],
                             "sessions": sessions, "count": entry["count"],
                             "status": "open", "note": "",
                             "first_seen": NOW(), "last_seen": NOW()}
            fresh.append(mark)
            continue
        was = held.get("sessions", 0)
        held["sessions"] = max(was, sessions)
        held["count"] = max(held.get("count", 0), entry["count"])
        held["last_seen"] = NOW()
        # A lesson answered by a mechanism that is still firing was not
        # answered. Reopening it is the only way a wrong fix is ever seen.
        if held["status"] in ("enforced", "context") and sessions > was:
            held["status"] = "open"
            held["note"] = "reopened: still recurring after %s" % held["status"]
            grown.append(mark)
        elif held["status"] == "open" and sessions > was:
            grown.append(mark)

    read = len(transcripts(days))
    ledger["last_scan"] = NOW()
    ledger["scans"] = ledger.get("scans", 0) + 1
    ledger["last_result"] = {"new": fresh, "grown": grown,
                             "window_days": days, "read": read}
    save(ledger)

    outstanding = [(m, l) for m, l in lessons.items() if l["status"] == "open"]
    outstanding.sort(key=lambda pair: (-pair[1]["sessions"], -pair[1]["count"]))

    if as_json:
        print(json.dumps({"new": fresh, "grown": grown, "read": read,
                          "outstanding": [dict(id=m, **l) for m, l in outstanding]},
                         indent=2))
    else:
        print("read %d transcript(s) over %d day(s)\n" % (read, days))
        show(outstanding, fresh, grown)
    return 1 if outstanding else 0


def show(outstanding, fresh=(), grown=()):
    if not outstanding:
        print("nothing recurring: every lesson on file has a mechanism behind it")
        return
    print("%d lesson(s) recurring across sessions, most-repeated first:\n"
          % len(outstanding))
    for mark, lesson in outstanding[:SHORTLIST]:
        flag = "NEW " if mark in fresh else ("MORE" if mark in grown else "    ")
        print("  %s %s  %s in %d session(s), %d time(s)"
              % (flag, mark, lesson["kind"], lesson["sessions"], lesson["count"]))
        print("       %s" % lesson["example"])
        if lesson.get("note"):
            print("       %s" % lesson["note"])
        print()
    if len(outstanding) > SHORTLIST:
        print("  %d more not listed; raise --min-sessions to narrow"
              % (len(outstanding) - SHORTLIST))


def cmd_list(args):
    ledger = load()
    rows = [(m, l) for m, l in ledger["lessons"].items()
            if args.all or l["status"] == "open"]
    rows.sort(key=lambda pair: (-pair[1]["sessions"], -pair[1]["count"]))
    if args.all:
        for mark, lesson in rows:
            print("  %-8s %s  %s in %d session(s)"
                  % (lesson["status"], mark, lesson["kind"], lesson["sessions"]))
            print("       %s" % lesson["example"])
        return 0
    show(rows)
    return 1 if rows else 0


def cmd_mark(args):
    ledger = load()
    lesson = ledger["lessons"].get(args.id)
    if lesson is None:
        print("no lesson %s on file" % args.id, file=sys.stderr)
        return 2
    if args.status != "declined" and not args.note:
        print("a mechanism has to say what it was, so --note is required",
              file=sys.stderr)
        return 2
    lesson["status"] = args.status
    lesson["note"] = args.note or ""
    lesson["settled_at"] = NOW()
    save(ledger)
    print("%s: %s" % (args.id, args.status))
    return 0


def cmd_report(args):
    ledger = load()
    last = ledger.get("last_result") or {}
    if not ledger.get("last_scan"):
        print("no scan on file", file=sys.stderr)
        return 1
    print("last scan %s over %d transcript(s) in %d day(s)"
          % (ledger["last_scan"], last.get("read", 0), last.get("window_days", 0)))
    settled = [(m, l) for m, l in ledger["lessons"].items()
               if l["status"] in ("enforced", "context")]
    print("  %d new, %d recurring further, %d settled by a mechanism"
          % (len(last.get("new") or []), len(last.get("grown") or []), len(settled)))
    for mark, lesson in settled:
        print("    %-8s %s  %s" % (lesson["status"], mark, lesson.get("note", "")))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)

    read = sub.add_parser("scan", help="read the window and rank what recurs")
    read.add_argument("--days", type=int, default=WINDOW_DAYS)
    read.add_argument("--min-sessions", type=int, default=MIN_SESSIONS)
    read.add_argument("--json", action="store_true")

    listing = sub.add_parser("list", help="what is outstanding")
    listing.add_argument("--all", action="store_true")

    settle = sub.add_parser("mark", help="record what a lesson became")
    settle.add_argument("id")
    settle.add_argument("--as", dest="status", required=True,
                        choices=("enforced", "context", "declined"))
    settle.add_argument("--note", default="")

    sub.add_parser("report", help="what the last scan changed")

    args = parser.parse_args()
    if args.verb == "scan":
        return scan(args.days, args.min_sessions, args.json)
    if args.verb == "list":
        return cmd_list(args)
    if args.verb == "mark":
        return cmd_mark(args)
    return cmd_report(args)


if __name__ == "__main__":
    sys.exit(main())
