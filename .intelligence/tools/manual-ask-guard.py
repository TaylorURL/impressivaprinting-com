#!/usr/bin/env python3
"""Refuse a reply that hands a step back to the person reading it.

The rule is that asking is the last resort: every skill, server, tool and
machine gets exhausted first, and only what nothing here can reach is worth
raising. What actually happens is smaller and quieter than a refusal to work -
a run that could have made the call writes a command out instead, and the reply
reads as helpful while the work sits undone. That costs the reader the whole
turn: a result was expected and homework arrived.

One guard already covers a slice of this. `remote-access.py` refuses a reply
giving up on a machine that answers a probe, which is the case where a route
existed and went unused. It stops at a machine name, deliberately, because a
sentence naming none is not about a machine. This one covers the rest: the step
handed over with no machine in it at all, which is most of them.

So a sentence naming a machine is left alone here. That belongs to the other
guard, which probes before it refuses, and a machine that is genuinely asleep
has to stay sayable.

What may still be handed over is what a mechanism reserves to the owner rather
than what a run found inconvenient: an approval one of the gates requires, a
credential, a card, a domain to buy. None of those is a step a session may take
on the owner's behalf, and a guard that refused them would leave the only
honest reply unwritable.

  guard-stop    Stop hook. Refuse a reply that hands over a step
                nothing reserves to the owner.

INTELLIGENCE_MANUAL_ASK_OFF=1 disables this.
"""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path


def _shared():
    here = Path(__file__).resolve().parent / "_lib.py"
    path = here if here.is_file() else Path.home() / ".intelligence" / "tools" / "_lib.py"
    spec = importlib.util.spec_from_file_location("intelligence_tools_lib", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A Stop hook that crashes on a half-synced tree blocks every reply, so a
# missing _lib stands the guard down instead: guard_stop notes it and exits 0.
try:
    _lib = _shared()
    read_transcript = _lib.read_transcript
    final_reply = _lib.final_reply
    prose_only = _lib.prose_only
except Exception:
    _lib = None


# An errand opens its clause with the second person as the subject. The same
# words hanging off a noun state a property of that noun, so position is what
# separates the instruction from the description.
CLAUSE_OPEN = (
    r"(?:^|(?<=[.!?;:,|])\s*|(?<=\band\s)|(?<=\bbut\s)|(?<=\bso\s)|(?<=\bthen\s))"
)

# A bare demonstrative is the object an errand hands over. A demonstrative
# steering a noun is not one, and neither is a relative pronoun, which is what
# follows a noun rather than a verb. So the object closes its clause or turns
# into a place, and everything else is description. Copy is both a verb and a
# noun, and in a workspace that writes copy the noun is the frequent one.
OBJECT_END = (
    r"(?=\s*(?:[.,;:!?)\]|]|$)"
    r"|\s+(?:in|into|on|onto|at|to|from|back|there|here|and|then|once|so|before|"
    r"after|when|if|for|through|over|under|with|by|as|until)\b)"
)

# The shapes a step gets handed over in. Each one is an instruction aimed at the
# reader rather than a description of what was done, which is the whole
# difference between a report and a chore.
#
# The second-person opener carries its own exception list, because those three
# words also open the most ordinary sentence in a report - a fact the reader has
# to know, a decision only they can make - and the verb after them is what
# separates a fact from an errand.
HANDOVER = re.compile(
    CLAUSE_OPEN +
    r"you(?:'ll|'d|\s+will|\s+would)?\s+(?:need|have|want)\s+to\s+"
    r"(?!know|understand|be\b|decide|choose|pick|say|tell|approve|authoris|authoriz|allow)"
    r"|\b(?:please\s+)?(?:run|paste|send|set|export|type|enter|add|click|flip|toggle|"
    r"install|copy|drop|put)\s+(?:this|that|these|those|the following|it back)" + OBJECT_END +
    r"|\bsend\s+(?:it|this|that)\s+back\b"
    r"|\b(?:do|run|check|try|handle|fix|take care of)\s+(?:it|this|that|them)?\s*"
    r"(?:yourself|on your own)\b"
    r"|\b(?:from|on|at)\s+your\s+end\b"
    r"|\bover to you\b"
    r"|\bin the\s+\w+\s+(?:dashboard|console|panel|settings)\b[^.]*"
    r"\b(?:set|add|enable|disable|click|turn|flip|create|paste)\b",
    re.I,
)

# What a mechanism reserves to the owner, which is not a step a run declined to
# take. An approval one of the gates requires, anything that is a secret or a
# card, and a purchase. A sentence carrying one of these is the only honest
# thing a run can write, so it passes.
RESERVED = re.compile(
    r"INTELLIGENCE_(?:DB_WRITE|STRIPE_WRITE|MAIL_TO|SHOW_SECRET)"
    r"|\b(?:approve|approval|approves|authoris\w*|authoriz\w*)\b"
    r"|\b(?:password|passphrase|credential\w*|api key|secret key|access token|"
    r"card details|payment details|card number)\b"
    r"|\b(?:buy|purchase|register)\s+(?:the\s+|a\s+)?domain\b"
    r"|\bsign\s+in\b|\blog\s+in\b",
    re.I,
)

# A phrase inside quotation marks is named rather than used, which is the
# difference between an errand and a report about one. Without this, the only
# reply that cannot be written is the one describing what this guard refuses.
#
# Single quotes are left standing: an apostrophe in the middle of a word pairs
# with the next one and swallows the sentence between them, so a reply carrying
# "don't" and "it's" would excuse every errand sitting in between.
QUOTED = re.compile(
    r'"[^"\n]{0,300}"'
    r"|“[^”\n]{0,300}”"
    r"|`[^`\n]{0,300}`"
)

# The machines the other guard answers for. A sentence naming one belongs to it,
# where the route is probed before anything is refused, so this one stays out.
MACHINE = re.compile(
    r"\b(?:mac|macbook|workstation|trenton-mac|pi|raspberry ?pi|sunday|"
    r"windows|desktop|trentons-desktop|vps|vultr|domebreak-vps)\b",
    re.I,
)


def handovers(text):
    """Each sentence that hands a step over, with nothing excusing it.

    Scoped to the sentence for the reason the other guard is: measured over a
    whole reply, a handover phrase and the thing that would excuse it meet by
    accident, and a report naming an approval in one paragraph would then
    excuse an errand three paragraphs down.
    """
    found = []
    for sentence in re.split(r"(?<=[.!?\n])\s+", prose_only(text)):
        naked = QUOTED.sub(" ", sentence)
        if not HANDOVER.search(naked):
            continue
        if RESERVED.search(sentence) or MACHINE.search(sentence):
            continue
        trimmed = " ".join(sentence.split())
        if trimmed and trimmed not in found:
            found.append(trimmed)
    return found


def guard_stop():
    if os.environ.get("INTELLIGENCE_MANUAL_ASK_OFF") == "1":
        sys.exit(0)
    if _lib is None:
        sys.stderr.write("manual-ask-guard: _lib.py unavailable; standing down\n")
        sys.exit(0)
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    # A second pass means the reply has already been sent back once.
    if ev.get("stop_hook_active"):
        sys.exit(0)
    path = ev.get("transcript_path")
    if not path or not Path(path).exists():
        sys.exit(0)

    text, _ = final_reply(read_transcript(path))
    if not text.strip():
        sys.exit(0)

    found = handovers(text)
    if not found:
        sys.exit(0)

    sys.stderr.write(
        "\nBLOCKED: this reply hands a step back rather than taking it.\n\n"
        + "".join("  %s\n" % line[:200] for line in found[:4])
        + "\nDo it. A skill, an MCP server, a CLI, or another machine through\n"
        "remote-access.py reaches almost everything, and asking is what is left\n"
        "when none of them does.\n\n"
        "Where a mechanism genuinely reserves the act - an approval one of the\n"
        "gates requires, a credential, a card, a domain to buy - name which one\n"
        "and why it cannot be carried from here, in the sentence that asks. That\n"
        "reads as a gate rather than as a chore, and it stands.\n"
        "INTELLIGENCE_MANUAL_ASK_OFF=1 disables this.\n"
    )
    sys.exit(2)


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "guard-stop":
        guard_stop()
        return 0
    # An unrecognised verb exits as a refusal rather than a pass, so a caller
    # probing this guard by a name it does not carry cannot read the silent
    # exit as the guard reporting itself wired.
    print("unknown verb: %s" % verb, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
