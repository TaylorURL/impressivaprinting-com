#!/usr/bin/env python3
"""Cases for manual-ask-guard.py.

Both edges are fixed here, and the second one carries the weight. A guard that
refuses every sentence written in the second person stops a run from putting
the one true reply on the page - the gate that reserves an act to the owner -
and a turn with nothing sayable is worse than the errand it was aimed at.

So each refusal below is paired with the sentence it must not reach: an
approval, a credential, a purchase, a machine the other guard answers for, and
the ordinary report sentence that opens with the same three words.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "manual-ask-guard.py")

# The guard reads its off switch from the environment, and settings.json carries
# an env block a session exports into every process under it. Inherited, that
# switch decides every case here before the guard reads a word, and a machine
# carrying it would report a guard that has stopped refusing.
os.environ.pop("INTELLIGENCE_MANUAL_ASK_OFF", None)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def transcript(text):
    """A one-turn transcript ending in an assistant reply."""
    rows = [
        {"type": "user", "message": {"role": "user", "content": "do the thing"}},
        {"type": "assistant", "message": {"role": "assistant",
                                          "content": [{"type": "text", "text": text}]}},
    ]
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for row in rows:
        fh.write(json.dumps(row) + "\n")
    fh.close()
    return fh.name


def run_stop(text, active=False):
    path = transcript(text)
    ev = json.dumps({"transcript_path": path, "stop_hook_active": active})
    try:
        done = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                              input=ev, capture_output=True, text=True)
        return done.returncode
    finally:
        os.unlink(path)


HANDED_OVER = [
    ("a command written out for the reader",
     "The branch is ready. Run this in the repo and it lands."),
    ("a value handed back",
     "The figure is wrong. Paste this back and the run continues."),
    ("an errand with no machine in it",
     "You will need to add the DNS record before it resolves."),
    ("a provider's own screen",
     "In the Vercel dashboard, set the key on the production target."),
    ("the work returned outright",
     "The rest is straightforward, so do it yourself."),
    ("the work placed at the reader's end",
     "The build is clean; the deploy happens at your end."),
]

STANDS = [
    ("an approval a gate requires",
     "The write needs INTELLIGENCE_DB_WRITE naming that one migration, which "
     "cannot be set from inside a running session."),
    ("an approval by name",
     "Nothing here can approve a payment on your behalf, so that one act stays yours."),
    ("a credential",
     "The password for that account is not in the vault and cannot be minted from here."),
    ("a purchase",
     "The address is free at the registrar. Buy the domain and the rest wires itself."),
    ("a machine, which the other guard answers for",
     "The Pi is not answering a probe, so run this on the Pi once it is back."),
    ("an ordinary report sentence",
     "You need to know that the monthly starts on launch day rather than at signup."),
    ("a decision that is genuinely the reader's",
     "You will have to decide whether the old pages are worth keeping."),
    ("a demonstrative steering a noun rather than closing the clause",
     "A rule of that shape reads: never touch this path, never run this command."),
    ("copy as a noun with a relative pronoun behind it",
     "The standard refuses copy that must not explain itself."),
    ("the same noun inside a list of what gets judged",
     "What it reads is voice, casing, and copy that references the conversation "
     "that produced it."),
    ("an obligation hung off a noun rather than opening a clause",
     "The whole arrangement ships already, and none of it needs a script that "
     "somebody has to maintain."),
    ("second person hung off a noun states a property",
     "Everything there is in the box, and none of it needs a script you have to "
     "maintain."),
]


def main():
    mod = load()

    for label, text in HANDED_OVER:
        check("refused: %s" % label, run_stop(text), 2)
        check("found: %s" % label, len(mod.handovers(text)), 1)

    for label, text in STANDS:
        check("stands: %s" % label, run_stop(text), 0)
        check("nothing found: %s" % label, mod.handovers(text), [])

    # A sentence carrying both is excused. A reply naming the gate it is asking
    # about is the honest one, and the errand-shaped words in it are the ask.
    both = "Send this back as INTELLIGENCE_DB_WRITE=ref:object and the migration applies."
    check("an approval outranks the shape it arrives in", run_stop(both), 0)

    # A handover phrase and its excuse in different sentences do not meet.
    apart = ("The approval is a gate rather than a chore.\n\n"
             "The rest is mechanical, so run this and it finishes.")
    check("an excuse a sentence away does not carry", run_stop(apart), 2)

    # A phrase in quotation marks is named rather than used. Without this the
    # one reply that cannot be written is the report on what this guard refuses.
    named = 'It refuses a reply that returns the work as "do it yourself".'
    check("a quoted phrase is named rather than used", run_stop(named), 0)

    backticked = "The shape it catches is `run this` with nothing reserving it."
    check("a backticked phrase is named rather than used", run_stop(backticked), 0)

    # An apostrophe is not a quotation mark. Two of them in one sentence would
    # otherwise pair and excuse whatever sat between them.
    apostrophes = "It doesn't matter what the branch is called, so run this and it's done."
    check("an apostrophe pair excuses nothing", run_stop(apostrophes), 2)

    # A fenced block is the evidence under an answer rather than an instruction.
    fenced = "The branch landed and the site serves it.\n\n```bash\nnpm run build\n```\n"
    check("a fenced command on its own stands", run_stop(fenced), 0)
    check("a fence spends nothing", mod.handovers(fenced), [])

    check("an empty reply stands", run_stop("   "), 0)
    check("a second pass lets it stand", run_stop(HANDED_OVER[0][1], active=True), 0)

    missing = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                             input="not json", capture_output=True, text=True)
    check("an unreadable event stands the guard down", missing.returncode, 0)

    unknown = subprocess.run([sys.executable, str(TARGET), "wired?"],
                             capture_output=True, text=True)
    check("an unknown verb refuses rather than passing", unknown.returncode, 2)

    for fault in FAILURES:
        print("FAIL %s" % fault)
    print("manual-ask-guard: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
