#!/usr/bin/env python3
"""Refuses a reply that says again what the reply just refused already said.

A Stop hook that blocks a reply sends the turn back to be written again, and
nothing until now held the blocked draft. Without it the second attempt is
judged only against the rule that stopped the first, so the cheapest way past a
count is to delete a clause and resubmit the same paragraph. The count clears
and the rule the count stands for -- that a second attempt carries something the
first did not -- fails with nothing saying so.

The refused draft needs no store: it stays in the transcript, with the harness's
own row carrying the refusal directly after it. So the comparison is between two
rows that are already on disk, which is why nothing here has to be cleaned up,
survives a restart, and cannot fall out of step with what was actually written.

Similarity is measured over prose alone -- `answer_prose` drops fences, tables,
headings, lists and quotes -- because those carry facts that stand on their own.
A path, a value, a command and a quoted line are evidence, and a reply that
states the same evidence twice is right to. What may not repeat is the writing
around it.

The measure is the share of the new reply's own three-word runs that already
stood in the refused one. Runs are order-free across sentences, so reordering
does not lower it; they are counted out of the new reply alone, so deleting from
the old one does not either; and a swapped word costs only the runs it touches.
Each of those is the edit a refusal is cheapest to answer with, and none of them
moves the number far.

A refusal that named a phrase is answered by removing that phrase, and the reply
around it was never at fault. So a refusal quoting one, and demanding no size of
the reply, stands this guard down once that phrase is gone: the alternative
refuses the exact edit the other guard asked for. A refusal counting the reply
against a cap or a budget is about the whole of it, and shaving it to fit is the
failure rather than the fix.

  guard-stop   Stop hook. Judge the reply just written against the refused one.
  measure      Report the verdict for a transcript, without refusing.

INTELLIGENCE_ALLOW_REPEAT=1 lets through the one reply that has to stand as it
is.
"""
import importlib.util
import json
import os
import re
import sys
from pathlib import Path


def _shared():
    """The shared _lib module, loaded by path.

    Hooks run this tool as a script from arbitrary directories, so the module is
    found beside this file rather than through sys.path, with the installed tree
    as the fallback for a copy executed from elsewhere.
    """
    here = Path(__file__).resolve().parent / "_lib.py"
    path = here if here.is_file() else Path.home() / ".intelligence" / "tools" / "_lib.py"
    spec = importlib.util.spec_from_file_location("intelligence_tools_lib", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A Stop hook that crashes on a half-synced tree blocks every reply, so a
# missing _lib stands the guard down instead.
try:
    _lib = _shared()
    read_transcript = _lib.read_transcript
    final_reply = _lib.final_reply
    answer_prose = _lib.answer_prose
    row_text = _lib.row_text
    SKILL_MARKER = _lib.SKILL_MARKER
except Exception:
    _lib = None


# The row the harness writes back when a Stop hook refuses. Its own label is the
# reliable marker; the refusal headline is accepted beside it so a change to
# that label leaves the guard reading rather than silent.
REFUSAL = re.compile(r"Stop hook feedback\b|^\s*BLOCKED:", re.M)

# Where a refusing guard prints the faults it found, one indented line each.
# Only these lines are read for a named phrase: the paragraphs around them
# explain the rule and quote nothing the reply is answerable for.
FAULT_LINE = re.compile(r"^  (?! )(\S.*)$", re.M)

# A phrase a refusal quoted, which is a fault the reply can answer by removing.
NAMED = re.compile(r'"([^"\n]{3,})"')

# A refusal that weighed the whole reply rather than naming a part of it. The
# forms are the ones a counting gate prints: a tally against a limit, or the
# headline that stands in for one.
SIZED = re.compile(
    r"\b\d+\s+(?:sentences?|words?|lines?|characters?)\b[^\n]*?"
    r"\b(?:cap|budget|limit|maximum|max|allowance)\b"
    r"|\blonger than it needs\b",
    re.I,
)

# Spans that are evidence rather than writing. A reply repeats an identifier
# because the identifier has not changed, so counting one as recycled prose
# charges the reply for being about the same subject.
CODE_SPAN = re.compile(r"`[^`]*`")
LINK = re.compile(r"https?://\S+|\b[\w.-]+/[\w./-]{2,}")

# How much of a reply's own phrasing may already have stood in the refused one
# before it is the refused one again. Calibrated against the refused-and-
# resubmitted pairs this machine's transcripts hold: a reply shaved to fit sits
# above it, and one restructured or carrying a fact the first lacked sits below.
SAME = 0.65

# The run length, and the fewest runs a reply must have before it is measured at
# all. A short answer has one right form, so measuring one charges it for being
# brief; the floor holds this guard off a bare yes, a single corrected value and
# a one-line result.
RUN = 3
FLOOR = 25

# How many times this may refuse inside one turn. A rule nobody can satisfy has
# to cost rewrites rather than the session, and the second refusal is the last
# one that can still be telling the writer something it has not been told.
LIMIT = 2

HEADLINE = "BLOCKED: this reply says again what the refused one said."


def turn_rows(rows):
    """The rows since the person last typed, which is one turn's worth of work.

    A refusal returns as a row the harness marks its own, so the drafts refused
    inside a turn all sit after the same typed message. Cutting there is what
    keeps a reply from being measured against an answer to a different question,
    which two turns on one subject would otherwise fail.
    """
    start = 0
    for i, row in enumerate(rows):
        if row.get("type") == "user" and not row.get("isMeta") \
                and row_text(row).strip():
            start = i
    return rows[start:]


def reply_before(rows, index):
    """The assistant turn that ends at `index`, flattened to its text.

    Mirrors how the final reply is read, so a draft refused mid-session is the
    same thing this guard compares against as the reply it is judging: the text
    blocks of one contiguous assistant turn, tool calls left out.
    """
    text = []
    for row in reversed(rows[:index]):
        if row.get("type") == "user":
            break
        if row.get("type") != "assistant":
            continue
        content = (row.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text.append(block.get("text", ""))
    return "\n".join(reversed(text))


def refused_drafts(rows):
    """Every draft a Stop hook refused this turn, each with the refusal it drew.

    Paired rather than listed, because what the refusal asked for decides
    whether the reply that followed answered it. A skill body is excluded by
    name: it is marked the same way a refusal is and can carry the same words
    without being one.
    """
    out = []
    turn = turn_rows(rows)
    for i, row in enumerate(turn):
        if row.get("type") != "user" or not row.get("isMeta"):
            continue
        text = row_text(row)
        if SKILL_MARKER.search(text) or not REFUSAL.search(text):
            continue
        draft = reply_before(turn, i)
        if draft.strip():
            out.append((draft, text))
    return out


def own_refusals(rows):
    """How many of this turn's refusals came from this guard."""
    return sum(1 for _, feedback in refused_drafts(rows) if HEADLINE in feedback)


def runs(text, n=RUN):
    """The word runs of a reply's prose, which is what its phrasing amounts to.

    Evidence is dropped before the words are taken: an inline code span and a
    path are quoted from somewhere else, so two replies carrying the same one
    are agreeing about a fact rather than repeating a sentence.
    """
    body = LINK.sub(" ", CODE_SPAN.sub(" ", answer_prose(text) if _lib else text))
    words = re.findall(r"[a-z0-9']+", body.lower())
    return set(tuple(words[i:i + n]) for i in range(len(words) - n + 1))


def recycled(draft, reply):
    """The share of the reply's own runs that already stood in the draft.

    Read out of the reply rather than out of the pair, so a draft that lost
    material cannot lower it. The question is only whether what is being sent
    now was already written, and a reply too small to hold `FLOOR` runs answers
    nothing either way.
    """
    new = runs(reply)
    if len(new) < FLOOR:
        return None
    old = runs(draft)
    if len(old) < FLOOR:
        return None
    return len(new & old) / len(new)


def named_faults(feedback):
    """The phrases a refusal quoted, out of the lines where it names faults."""
    return [phrase
            for line in FAULT_LINE.findall(feedback)
            for phrase in NAMED.findall(line)]


def answered(feedback, draft, reply):
    """Whether the reply removed the phrase the refusal named and owed no more.

    A refusal that also weighed the reply's size asked for the whole of it
    again, so no removal answers it. One that named a phrase and nothing else
    is answered by that phrase being gone, and the writing it sat in was never
    what was refused.
    """
    if SIZED.search(feedback):
        return False
    named = [p for p in named_faults(feedback) if p.lower() in draft.lower()]
    if not named:
        return False
    return all(p.lower() not in reply.lower() for p in named)


def judge(reply, drafts):
    """Every fault in a resubmitted reply, as lines fit to print in a refusal.

    `drafts` is this turn's refused drafts paired with the refusals they drew.
    All of them are compared, not only the last: a third attempt can be a copy
    of the first while differing from the one immediately behind it.
    """
    if os.environ.get("INTELLIGENCE_ALLOW_REPEAT") == "1":
        return []
    faults = []
    for draft, feedback in drafts:
        if answered(feedback, draft, reply):
            continue
        share = recycled(draft, reply)
        if share is not None and share >= SAME:
            faults.append("%d%% of this reply's phrasing already stood in the "
                          "draft that was refused" % round(share * 100))
    return faults[:1]


def guard_stop():
    if os.environ.get("INTELLIGENCE_ALLOW_REPEAT") == "1":
        sys.exit(0)
    if _lib is None:
        sys.stderr.write("repetition-guard: _lib.py unavailable; standing down\n")
        sys.exit(0)
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    # Nothing has been refused until the turn is being written a second time,
    # and this guard has nothing to compare before then.
    if not ev.get("stop_hook_active"):
        sys.exit(0)
    path = ev.get("transcript_path")
    if not path or not Path(path).exists():
        sys.exit(0)

    rows = read_transcript(path)
    text, _ = final_reply(rows)
    if not text.strip():
        sys.exit(0)
    if own_refusals(rows) >= LIMIT:
        sys.exit(0)
    faults = judge(text, refused_drafts(rows))
    if not faults:
        sys.exit(0)

    sys.stderr.write(
        "\n" + HEADLINE + "\n\n"
        + "".join("  %s\n" % f for f in faults)
        + "\nA refusal is not a count to get under. What it asks for is the reply\n"
        "written again, and a reply written again carries something the refused\n"
        "one did not: the corrected fact, in the ordinary voice, with no account\n"
        "of what was wrong before. Deleting a clause and sending the same\n"
        "paragraph clears the count and leaves the answer where it was.\n"
        "Say the thing that decides what happens next in the first line, put the\n"
        "paths, values and commands in a table or a fence where they cost no\n"
        "prose, and let the rest go.\n"
        "INTELLIGENCE_ALLOW_REPEAT=1 lets a reply stand as it is.\n"
    )
    sys.exit(2)


def measure(path):
    if _lib is None:
        print("repetition-guard: _lib.py unavailable; nothing measured",
              file=sys.stderr)
        return 1
    rows = read_transcript(path)
    text, _ = final_reply(rows)
    drafts = refused_drafts(rows)
    shares = [recycled(draft, text) for draft, _ in drafts]
    print("refused=%d recycled=%s runs=%d threshold=%.2f own=%d"
          % (len(drafts),
             ",".join("%.3f" % s if s is not None else "-" for s in shares) or "-",
             len(runs(text)), SAME, own_refusals(rows)))
    faults = judge(text, drafts)
    for f in faults:
        print("  %s" % f)
    return 1 if faults else 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "guard-stop"
    if mode == "guard-stop":
        guard_stop()
    elif mode == "measure":
        sys.exit(measure(sys.argv[2] if len(sys.argv) > 2 else ""))
    # An unrecognised verb exits as a refusal rather than a pass, so a caller
    # probing this guard by a name it does not carry cannot read the silent exit
    # as the guard reporting itself wired.
    print("unknown verb: %s" % mode, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
