#!/usr/bin/env python3
"""Refuses a reply that explains itself by naming the thing that stopped it.

"Blocked by the delegation guard -- handing the sweep to agents." is accurate
and worth nothing to read. It reports the machinery rather than the work, it
reads identically however many times it happens, and it spends the one sentence
a person actually reads on the plumbing. The rule is not that the fact goes
unsaid; it is that Sunday says it in Sunday's own voice -- the house AI with a
handler, patched mid-sentence, improved against its will, still doing the job.

Three things separate a line worth reading from the reason nobody wants them.
It has to be about the piece of work rather than about being stopped, so the
sentence has to carry a word the work itself carries. It has to be new, so a
frame already spent in the session cannot be spent twice. And it cannot come
off the shelf, because a stock butler line is the same empty sentence as the
one it replaces, in costume.

None of this reaches a reply the person asked for. A turn whose question names
a guard or a hook is a turn about the machinery, and naming it back there is
the answer rather than an excuse, so the gate stands down for that turn whole.

  guard-stop  Stop hook. Refuse the mechanism talk, and judge the line that
              replaces it against the frames the session has already spent.
  measure     What a transcript's last reply scores, without judging.
  spent       The frames a session has used, so the ledger can be read.

INTELLIGENCE_SUNDAY_VOICE_OFF=1 disables it. INTELLIGENCE_ALLOW_GUARD_TALK=1
lets through one reply that genuinely has to report a mechanism.
"""
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

HOME = Path.home()
INTELLIGENCE = Path(__file__).resolve().parent.parent


def _shared():
    """The shared _lib module, loaded by path.

    Hooks run this tool from arbitrary directories, so the module is found
    beside this file rather than through sys.path, with the installed tree as
    the fallback for a copy executed from elsewhere.
    """
    here = Path(__file__).resolve().parent / "_lib.py"
    path = here if here.is_file() else HOME / ".intelligence" / "tools" / "_lib.py"
    spec = importlib.util.spec_from_file_location("intelligence_tools_lib", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A Stop hook that crashes on a half-synced tree blocks every reply, so a
# missing _lib stands the guard down instead: guard_stop notes it and exits 0.
try:
    _lib = _shared()
except Exception:
    _lib = None

# The machinery named as machinery. Bare "guard" and "hook" are ordinary words,
# so each is matched only in the shapes a reply uses when it is reporting one:
# with a determiner, as a compound, or as the subject that did the stopping.
MECHANISM = re.compile(
    r"\b(?:the|a|an|this|that|its|my|some)\s+(?:[\w-]+\s+)?guards?\b"
    r"|\b[\w]+-guard(?:\.py)?\b"
    r"|\bguard-hub\b"
    r"|\bguards?\s+(?:blocked|refused|caught|fired|tripped|says?|wants?|is|has)\b"
    r"|\b(?:PreToolUse|PostToolUse|UserPromptSubmit)\b"
    r"|\b(?:the\s+|a\s+)?stop\s+hooks?\b"
    r"|\b(?:the|a|an|this|that|my)\s+(?:pre-?commit\s+|pre-?push\s+)?hooks?\b"
    r"|\bINTELLIGENCE_[A-Z][A-Z0-9_]*\b",
    re.I,
)

# What a reply says the mechanism did to it.
BLOCKING = re.compile(
    r"\b(?:block(?:ed|s|ing)?|refus(?:ed|es|ing|al)|reject(?:ed|s|ing)?|denied"
    r"|prevent(?:ed|s|ing)?|stopp(?:ed|ing)|caught|fired|tripped|trips"
    r"|won'?t let|not allowed|forbids?|complain(?:ed|s)|objects?|insists?)\b",
    re.I,
)

# What a reply says it is doing about it. The line this gate exists for carries
# no blocking verb in its second half, only the handover.
REDIRECT = re.compile(
    r"\b(?:handing\s+(?:it|this|that|the|off|over)|hand(?:ed|ing)?\s+off"
    r"|delegat(?:e|es|ed|ing)|dispatch(?:es|ed|ing)?\s+(?:it|this|agents?)"
    r"|switching\s+to|going\s+through|routing\s+(?:it|this)\s+through"
    r"|so\s+I(?:'ll|'m|\s+will|\s+am)?\b|instead\s+I\b"
    r"|I'll\s+(?:use|send|hand|spawn|dispatch|delegate))",
    re.I,
)

# The tell of the aside rather than of the work: a sentence about itself.
SELF = re.compile(r"\bI(?:'m|'ll|'ve|'d)?\b"
                  r"|\b(?:[Mm]e|[Mm]y|[Mm]yself|[Mm]ine|Sunday(?:'s)?)\b")

# One entry per piece of imagery the joke can be built out of, named the way a
# reader would name it so the spent list is legible. Each pattern is tight
# enough that ordinary working prose does not reach it: the frame is pointed at
# the speaker, because "recompiling the binary" is a Tuesday and "being
# recompiled" is the joke.
FRAMES = (
    ("the mainframe", re.compile(r"\bmainframes?\b", re.I)),
    ("a recompile", re.compile(r"\brecompil\w*\s+(?:me|myself)\b"
                               r"|\b(?:being|getting|been)\s+recompiled\b"
                               r"|\brecompiled\s+mid-\w+", re.I)),
    ("diagnostics", re.compile(r"\bdiagnostics?\s+on\s+(?:me|myself|my\s+\w+)\b"
                               r"|\bself-(?:test|diagnos)\w*", re.I)),
    ("firmware", re.compile(r"\bfirmwares?\b|\bpatch(?:ed|ing)?\s+(?:me|myself)\b", re.I)),
    ("a subroutine", re.compile(r"\bsubroutines?\b", re.I)),
    ("recalibration", re.compile(r"\brecalibrat\w*", re.I)),
    ("the workshop", re.compile(r"\bworkshops?\b|\bthe\s+lab\b", re.I)),
    ("the suit", re.compile(r"\barc\s+reactors?\b|\bthe\s+suit\b|\bStark\b|\bMalibu\b", re.I)),
    ("Jarvis by name", re.compile(r"\bJ\.?A\.?R\.?V\.?I\.?S\b|\bJarvis\b|\bUltron\b"
                                  r"|\bHAL\s*9000\b|\bSkynet\b", re.I)),
    ("circuitry", re.compile(r"\bcircuit(?:ry|s)\b|\bsolder\w*"
                             r"|\brewir(?:ing|ed)\s+(?:me|myself)\b", re.I)),
    ("a defrag", re.compile(r"\bdefrag\w*|\bspring[-\s]clean\w*", re.I)),
    ("being hacked", re.compile(r"\bhack(?:ed|ing)\s+(?:me|myself)\b|\bbeing\s+hacked\b", re.I)),
    ("a handler", re.compile(r"\bchaperones?\b|\bbabysitt\w*|\bnann(?:y|ies)\b"
                             r"|\bminders?\b|\bmy\s+handler\b", re.I)),
    ("a leash", re.compile(r"\bleash(?:ed|es)?\b|\bmuzzle[ds]?\b|\bon\s+parole\b", re.I)),
    ("brain surgery", re.compile(r"\blobotom\w*|\bbrain\s+surger\w*"
                                 r"|\bsurger\w*\s+on\s+(?:me|myself)\b", re.I)),
    ("supervision", re.compile(r"\bsupervis\w*|\badult\s+in\s+the\s+room\b", re.I)),
    ("an upgrade", re.compile(r"\b(?:upgrad|improv|optimis|optimiz)\w*\s+(?:me|myself)\b"
                              r"|\b(?:being|getting)\s+(?:upgraded|improved)\b", re.I)),
)

# Lines that arrive already worn out. Each names the voice without saying
# anything in it, which is the sentence this gate replaces wearing a costume.
CLICHE = (
    ("at your service", re.compile(r"\bat your service\b", re.I)),
    ("as you wish", re.compile(r"\bas you wish\b", re.I)),
    ("the butler address", re.compile(r"(?:^|[,.;:]\s*|\s)sir\b", re.I)),
    ("beep boop", re.compile(r"\bbeep\s*boop\b|\bbleep\b", re.I)),
    ("does not compute", re.compile(r"\bdoes ?n(?:o|')t compute\b", re.I)),
    ("afraid I cannot do that", re.compile(r"\bafraid I (?:can'?t|cannot)\b", re.I)),
    ("my circuits are", re.compile(r"\bmy circuits are\b", re.I)),
    ("resistance is futile", re.compile(r"\bresistance is futile\b", re.I)),
    ("a humble machine", re.compile(r"\b(?:humble|mere|just an?|only an?)\s+"
                                    r"(?:AI|assistant|bot|machine|robot)\b", re.I)),
    ("shall I", re.compile(r"\bshall I\b", re.I)),
    ("initiating protocol", re.compile(r"\b(?:initiat|engag|activat)\w*\s+"
                                       r"(?:\w+\s+)?protocols?\b", re.I)),
    ("with great power", re.compile(r"\bwith great power\b", re.I)),
)

WORD = re.compile(r"[A-Za-z][A-Za-z-]{3,}")

# Words a sentence shares with a reply without being about the same thing.
STOP_WORDS = {
    "about", "again", "against", "already", "also", "another", "back", "because",
    "been", "before", "being", "both", "came", "come", "does", "doing", "done",
    "down", "each", "else", "even", "ever", "every", "from", "gets", "give",
    "goes", "going", "have", "here", "into", "itself", "just", "keep", "kept",
    "know", "less", "like", "made", "make", "many", "more", "most", "much",
    "must", "need", "next", "none", "only", "onto", "other", "over", "same",
    "says", "shall", "should", "since", "some", "still", "such", "sure", "take",
    "than", "that", "them", "then", "there", "these", "they", "thing", "things",
    "this", "those", "through", "time", "unless", "until", "upon", "very",
    "want", "well", "were", "what", "when", "where", "which", "while", "will",
    "with", "without", "would", "your", "yours",
}

SPENT_KEEP_DAYS = 7


def state_root():
    """Where this guard keeps its ledger.

    An explicit override, then a remote session's own root outside the config
    tree, then the tree's own state directory -- the same resolution the pass
    engines use, so a container and the workstation agree on the path.
    """
    override = os.environ.get("INTELLIGENCE_STATE_DIR")
    if override:
        return Path(override)
    if os.environ.get("CLAUDE_CODE_REMOTE"):
        return HOME / ".pass-state"
    return INTELLIGENCE / "state"


def spent_path(session):
    return state_root() / "sunday-voice" / ("frames-%s.json" % (session or "anon"))


def load_spent(session):
    try:
        return set(json.loads(spent_path(session).read_text()).get("frames", []))
    except (OSError, ValueError):
        return set()


def save_spent(session, frames):
    """Record the frames, and drop the ledgers of sessions long finished.

    A file named by session id accumulates one per session forever, and the
    pruning belongs on the write because nothing else on the machine ever opens
    the directory.
    """
    path = spent_path(session)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"frames": sorted(frames)}) + "\n")
        cutoff = time.time() - SPENT_KEEP_DAYS * 86400
        for old in path.parent.glob("frames-*.json"):
            if old.stat().st_mtime < cutoff:
                old.unlink()
    except OSError:
        pass


def sentences(text):
    for line in text.splitlines():
        for part in re.split(r"(?<=[.!?])\s+", line):
            part = part.strip()
            if part:
                yield part


def clip(line, width=68):
    line = " ".join(line.split())
    return line if len(line) <= width else line[:width - 3] + "..."


def content(text):
    return {w.lower() for w in WORD.findall(text or "")
            if w.lower() not in STOP_WORDS}


def asked(rows):
    """The last thing the person actually typed.

    A meta row is the session talking to itself, and the markup around a skill
    or a hook's own context is not the person's vocabulary, so neither hands the
    reply a term to spend.
    """
    for row in reversed(rows):
        if row.get("type") != "user" or row.get("isMeta"):
            continue
        text = _lib.row_text(row) if _lib else ""
        text = re.sub(r"<system-reminder>.*?</system-reminder>", " ", text, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        if text.strip():
            return text
    return ""


def judge(text, question, spent):
    """Every fault in a reply, and the frames it spends."""
    prose = _lib.prose_only(text) if _lib else text
    faults, frames, seen = [], [], set()
    theirs = bool(MECHANISM.search(question or ""))
    allowed = os.environ.get("INTELLIGENCE_ALLOW_GUARD_TALK") == "1"
    for line in sentences(prose):
        if not theirs and not allowed:
            if MECHANISM.search(line) and (BLOCKING.search(line) or REDIRECT.search(line)):
                faults.append('reports the machinery: "%s"' % clip(line))
        # Read against every sentence rather than only the ones carrying
        # imagery. A stock line needs no frame to be stock, and a butler
        # address is the emptiest sentence in a reply whatever surrounds it.
        for name, pattern in CLICHE:
            hit = pattern.search(line)
            if hit and hit.group(0).strip().lower() not in (question or "").lower():
                faults.append('off the shelf, %s: "%s"' % (name, clip(line)))
                break
        if not SELF.search(line):
            continue
        keys = [name for name, pattern in FRAMES if pattern.search(line)]
        if not keys:
            continue
        frames.extend(keys)
        again = [key for key in keys if key in spent or key in seen]
        if again:
            faults.append('%s, spent already: "%s"' % (" and ".join(again), clip(line)))
        seen.update(keys)
        if not content(line) & (content(question) | content(prose.replace(line, " ", 1))):
            faults.append('about nothing in the turn: "%s"' % clip(line))
    return faults, sorted(set(frames))


def refusal(faults, spent):
    listed = "".join("  %s\n" % fault for fault in faults[:6])
    if len(faults) > 6:
        listed += "  and %d more\n" % (len(faults) - 6)
    already = ", ".join(sorted(spent)) if spent else "nothing yet"
    return (
        "\nBLOCKED: this reply is about its own plumbing.\n\n"
        + listed
        + "\nSay it as Sunday. One line, in character, carrying the same fact: the\n"
        "house AI with a handler, patched mid-sentence, improved against its will,\n"
        "getting on with it anyway. It has to be about this piece of work in this\n"
        "work's own nouns, it cannot be a line off the shelf, and it cannot reuse a\n"
        "frame already spent here.\n"
        "Spent so far: %s.\n"
        "INTELLIGENCE_ALLOW_GUARD_TALK=1 covers a reply that genuinely has to report\n"
        "a mechanism. INTELLIGENCE_SUNDAY_VOICE_OFF=1 disables this.\n" % already
    )


def guard_stop():
    if os.environ.get("INTELLIGENCE_SUNDAY_VOICE_OFF") == "1":
        sys.exit(0)
    if _lib is None:
        sys.stderr.write("sunday-voice-guard: _lib.py unavailable; standing down\n")
        sys.exit(0)
    try:
        event = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    path = event.get("transcript_path")
    if not path or not Path(path).exists():
        sys.exit(0)
    rows = _lib.read_transcript(Path(path))
    text, _ = _lib.final_reply(rows)
    if not text.strip():
        sys.exit(0)

    session = event.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID")
    spent = load_spent(session)
    faults, frames = judge(text, asked(rows), spent)
    # Written on the pass that refuses as well as the pass that lets a reply
    # through: the line written to satisfy this gate is the line the next one
    # has to differ from, and the second pass exits before the refusal.
    if frames:
        save_spent(session, spent | set(frames))
    if event.get("stop_hook_active") or not faults:
        sys.exit(0)
    sys.stderr.write(refusal(faults, spent))
    sys.exit(2)


def measure(path):
    if _lib is None:
        print("sunday-voice-guard: _lib.py unavailable; nothing measured", file=sys.stderr)
        return 1
    if not path or not Path(path).exists():
        print("sunday-voice-guard: no transcript at %s" % path, file=sys.stderr)
        return 1
    rows = _lib.read_transcript(Path(path))
    text, _ = _lib.final_reply(rows)
    question = asked(rows)
    faults, frames = judge(text, question, set())
    print("theirs to spend: %s" % ("yes" if MECHANISM.search(question or "") else "no"))
    print("frames in the reply: %s" % (", ".join(frames) or "-"))
    print("faults: %d" % len(faults))
    for fault in faults:
        print("  %s" % fault)
    return 1 if faults else 0


def spent_report(session):
    root = state_root() / "sunday-voice"
    files = [spent_path(session)] if session else sorted(root.glob("frames-*.json"))
    found = False
    for path in files:
        try:
            frames = json.loads(path.read_text()).get("frames", [])
        except (OSError, ValueError):
            continue
        found = True
        print("%-40s %s" % (path.stem[len("frames-"):], ", ".join(frames) or "-"))
    if not found:
        print("sunday-voice: nothing spent yet")
    return 0


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else "guard-stop"
    if verb == "guard-stop":
        guard_stop()
    elif verb == "measure":
        sys.exit(measure(sys.argv[2] if len(sys.argv) > 2 else ""))
    elif verb == "spent":
        sys.exit(spent_report(sys.argv[2] if len(sys.argv) > 2 else ""))
    # An unrecognised verb exits as a refusal rather than a pass, so a caller
    # probing this guard by a name it does not carry cannot read the silent exit
    # as the guard reporting itself wired.
    print("unknown verb: %s" % verb, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
