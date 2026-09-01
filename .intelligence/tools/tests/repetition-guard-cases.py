#!/usr/bin/env python3
"""Cases the repetition guard has to get right.

The guard is worth only what it refuses, and worth nothing if it refuses a
second attempt that was fine. Both edges are fixed here, in the terms the
failure actually takes: a draft shaved to fit is caught, and so are the two
cheaper edits beside it, sentences moved and words swapped. A reply carrying a
fact the refused one lacked goes through, and so does one whose whole
resemblance is its evidence -- the same table, the same fence, the same paths
under different prose.

The refused draft is read out of the transcript rather than out of a store, so
the cases that matter for that are structural: a refusal row is found with the
draft above it, a skill body carrying the same words is not one, and a draft
from before the last typed message belongs to a turn that is over.

A refusal that named a phrase asks for that phrase gone and nothing more, so the
guard stands down once it is; a refusal that counted the reply against a cap
asked for the whole of it again, and no deletion answers that. Both directions
are held apart here, because the first is what keeps this guard from refusing
the exact edit its neighbour demanded.

  repetition-guard-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "repetition-guard.py")

# settings.json carries an env block that a session exports into every process
# under it. Inherited, the hatch decides the verdict before the guard reads a
# word, which reads as a guard that has stopped refusing.
os.environ.pop("INTELLIGENCE_ALLOW_REPEAT", None)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def above(label, got, floor):
    if got is None or got < floor:
        FAILURES.append(f"{label}: got {got!r}, want at least {floor!r}")


def below(label, got, ceiling):
    if got is None or got >= ceiling:
        FAILURES.append(f"{label}: got {got!r}, want under {ceiling!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g = load()


# The reply a shape guard refused, and the four things that can be sent back in
# its place. Three of them are the same answer arriving again; the fourth is an
# answer that moved.
DRAFT = """All three replicas are live now, on ports 3001, 3002 and 3003.

Each one is a full copy of the site running its own dev server, so the three tabs open side by side without interfering with one another. The colour is not painted on top: every accent step was remapped to a hue holding the same relative luminance as the blue it replaces, so every contrast ratio the stylesheet was built around survives the change intact. The logo came with it, and the wordmark, the mark and the touch icon were each recoloured to the matching step. The monochrome one is stricter than a grey repaint, because the accent there is the ground's own ink rather than a shade of it. Light, dark and gray settings all work in each of them. The sign-in screen and the console carry the theme as well. Nothing in the working checkout was touched."""

SHAVED = """All three replicas are live now, on ports 3001, 3002 and 3003.

Each one is a full copy of the site on its own dev server, so the three tabs open side by side. Every accent step was remapped to a hue holding the same relative luminance as the blue it replaces, so the contrast ratios the stylesheet was built around survive intact. The logo came with it, the wordmark, the mark and the touch icon recoloured to the matching step. The monochrome one is stricter than a grey repaint, because the accent is the ground's own ink. Light, dark and gray all work in each, the sign-in screen and console carry the theme, and the working checkout was not touched."""

REORDERED = """Nothing in the working checkout was touched. The sign-in screen and the console carry the theme as well. Light, dark and gray settings all work in each of them.

The monochrome one is stricter than a grey repaint, because the accent there is the ground's own ink rather than a shade of it. The logo came with it, and the wordmark, the mark and the touch icon were each recoloured to the matching step. The colour is not painted on top: every accent step was remapped to a hue holding the same relative luminance as the blue it replaces, so every contrast ratio the stylesheet was built around survives the change intact. Each one is a full copy of the site running its own dev server, so the three tabs open side by side without interfering with one another. All three replicas are live now, on ports 3001, 3002 and 3003."""

SWAPPED = """All three replicas are running now, on ports 3001, 3002 and 3003.

Each one is a complete copy of the site running its own dev server, so the three tabs open alongside each other without interfering with one another. The colour is not painted on top: every accent step was remapped to a shade holding the same relative luminance as the blue it supplants, so every contrast ratio the stylesheet was designed around survives the change intact. The logo came with it, and the wordmark, the mark and the touch icon were each repainted to the matching step. The monochrome one is stricter than a grey repaint, because the accent there is the ground's own ink rather than a tint of it. Light, dark and gray settings all work in each of them. The sign-in screen and the console carry the theme too. Nothing in the working checkout was touched."""

REWRITTEN = """Three replicas are serving and the fourth failed its build, because the token store holds no entry for it.

The accents are derived rather than substituted: each step keeps the luminance of the one it stands in for, which is why no ratio had to be measured again. Recolouring reached the images too, so a nav mark matches the page it sits on. Monochrome is the odd one out, since its accent has to be the ground's own ink and the three status colours had to separate into steps of that ink instead of one flat grey. The build log for the failure sits under the scratchpad, and that missing entry is the only thing between it and a fourth port."""

SHORT = "The row is wired and the mirror carries it."


# -- what counts as the same reply -------------------------------------------

check("an identical reply is wholly recycled", g.recycled(DRAFT, DRAFT), 1.0)
above("a clause cut from every sentence stays the same reply",
      g.recycled(DRAFT, SHAVED), g.SAME)
above("sentences moved stay the same reply",
      g.recycled(DRAFT, REORDERED), g.SAME)
above("words swapped stay the same reply",
      g.recycled(DRAFT, SWAPPED), g.SAME)
below("a reply carrying a fact the draft lacked is a different one",
      g.recycled(DRAFT, REWRITTEN), g.SAME)

check("a reply too small to measure answers nothing",
      g.recycled(DRAFT, SHORT), None)
check("a draft too small to measure answers nothing",
      g.recycled(SHORT, DRAFT), None)


# -- evidence is not prose ---------------------------------------------------

EVIDENCE = """
| guard | event | override |
|---|---|---|
| repetition-guard.py | Stop | INTELLIGENCE_ALLOW_REPEAT |
| reply-shape-guard.py | Stop | INTELLIGENCE_OPENER_OFF |

```bash
~/.intelligence/tools/guard-hub.py bench
~/.intelligence/tools/session-init.py status
```
"""

EVIDENCE_FIRST = (
    "The registry row fires only where the event carries the flag, so an "
    "ordinary turn pays a string test and no process at all. `tools/guard-hub.py` "
    "reads the payload once and hands the same bytes to whichever gate answers "
    "yes. Nothing under `state/` is written on the fast path, which is why the "
    "bench figure barely moves. The suite runs inside the sandbox that refuses a "
    "live session by name.\n" + EVIDENCE)

EVIDENCE_AGAIN = (
    "Two suites still fail, and both of them fail on the same fixture: a "
    "transcript written without the marker `tools/guard-hub.py` looks for. "
    "`tools/session-init.py` would fold a hand-added hook back out within one "
    "session, so wiring by hand buys nothing. The number under `state/` is a "
    "ledger rather than a decision. Nothing about the sandbox changed.\n"
    + EVIDENCE)

check("the same table, fence and paths under different prose cost nothing",
      g.recycled(EVIDENCE_FIRST, EVIDENCE_AGAIN), 0.0)


# -- what the refusal asked for ----------------------------------------------

OFFER = ('\nBLOCKED: this reply is the wrong shape.\n\n'
         '  closes with "want me to"\n\nThe answer stands without it.\n')
OFFER_AND_CAP = ('\nBLOCKED: this reply is the wrong shape.\n\n'
                 '  closes with "want me to"\n'
                 '  8 sentences of prose against a cap of 6\n')
CAP_ONLY = ('\nBLOCKED: this reply is the wrong shape.\n\n'
            '  8 sentences of prose against a cap of 6\n')
BUDGET = ('\nBLOCKED: this report is longer than it needs to be.\n\n'
          '  212 words against a budget of 150\n')

WITH_OFFER = DRAFT + "\nWant me to sync the Pi as well?"

check("removing the phrase the refusal named answers it",
      g.answered(OFFER, WITH_OFFER, DRAFT), True)
check("the phrase still there answers nothing",
      g.answered(OFFER, WITH_OFFER, WITH_OFFER), False)
check("a refusal that also counted the reply is not answered by a deletion",
      g.answered(OFFER_AND_CAP, WITH_OFFER, DRAFT), False)
check("a refusal naming no phrase is answered by nothing",
      g.answered(CAP_ONLY, DRAFT, SHAVED), False)
check("a budget refusal is a size refusal",
      g.answered(BUDGET, WITH_OFFER, DRAFT), False)
check("a phrase the draft never carried names no fault",
      g.answered(OFFER, DRAFT, DRAFT), False)
check("only the fault lines are read for a named phrase",
      g.named_faults('\nBLOCKED: the shape is wrong.\n\n'
                     '  closes with "want me to"\n\n'
                     'A reply "like this one" is not a fault line.\n'),
      ["want me to"])


# -- the drafts a turn has already had refused -------------------------------

def user(text):
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


def meta(text):
    return dict(user(text), isMeta=True)


def answer(text):
    return {"type": "assistant",
            "message": {"content": [{"type": "text", "text": text}]}}


FEEDBACK = "Stop hook feedback:\n" + CAP_ONLY
SKILL_BODY = ("Base directory for this skill: /Users/x/.intelligence/skills/short\n"
              "Stop hook feedback is what a refusal comes back as.\n")

ROWS = [user("theme the three replicas"), answer(DRAFT), meta(FEEDBACK)]

check("the draft above a refusal is the refused one",
      [d for d, _ in g.refused_drafts(ROWS)], [DRAFT])
check("a skill body carrying the same words is not a refusal",
      g.refused_drafts([user("go"), answer(DRAFT), meta(SKILL_BODY)]), [])
check("a draft from before the last typed message is out of the turn",
      g.refused_drafts(ROWS + [user("and the fourth?"), answer(REWRITTEN)]), [])
check("a row carrying only a reminder is nobody taking a turn",
      [d for d, _ in g.refused_drafts(
          [user("theme the three replicas"), answer(DRAFT),
           user("<system-reminder>the plan is current</system-reminder>"),
           meta(FEEDBACK)])], [DRAFT])
check("two refusals in one turn are both held",
      len(g.refused_drafts(ROWS + [answer(SHAVED), meta(FEEDBACK)])), 2)
check("a refusal from this guard is counted as its own",
      g.own_refusals(ROWS + [answer(SHAVED),
                             meta("Stop hook feedback:\n" + g.HEADLINE)]), 1)
check("another guard's refusal is not counted as this one's",
      g.own_refusals(ROWS), 0)


# -- the verdict -------------------------------------------------------------

DRAFTS = [(DRAFT, CAP_ONLY)]

check("a deletion-only resubmission is refused", len(g.judge(SHAVED, DRAFTS)), 1)
check("a real correction is not", g.judge(REWRITTEN, DRAFTS), [])
check("nothing refused leaves nothing to compare", g.judge(SHAVED, []), [])
check("the fault names the share it measured",
      any("already stood in the draft" in f for f in g.judge(SHAVED, DRAFTS)),
      True)
check("a resubmission answering the named phrase is let through",
      g.judge(DRAFT, [(WITH_OFFER, OFFER)]), [])
check("a copy of the first draft is caught behind a second that differs",
      len(g.judge(SHAVED, [(DRAFT, CAP_ONLY), (REWRITTEN, CAP_ONLY)])), 1)

os.environ["INTELLIGENCE_ALLOW_REPEAT"] = "1"
check("the hatch empties the verdict", g.judge(SHAVED, DRAFTS), [])
os.environ.pop("INTELLIGENCE_ALLOW_REPEAT")


# -- the hook itself ---------------------------------------------------------

def run_stop(rows, extra=None, env=None):
    """The guard as the Stop hook runs it, against a written transcript."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "t.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        payload = {"transcript_path": str(path), "stop_hook_active": True}
        payload.update(extra or {})
        e = dict(os.environ)
        e.update(env or {})
        p = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                           input=json.dumps(payload), capture_output=True,
                           text=True, env=e)
        return p.returncode, p.stderr


code, err = run_stop(ROWS + [answer(SHAVED)])
check("hook refuses the draft shaved to fit", code, 2)
check("the refusal says what a correction owes",
      "carries something the refused" in err, True)
check("the refusal names its own hatch",
      "INTELLIGENCE_ALLOW_REPEAT=1" in err, True)

code, _ = run_stop(ROWS + [answer(REORDERED)])
check("hook refuses the same sentences in another order", code, 2)

code, _ = run_stop(ROWS + [answer(SWAPPED)])
check("hook refuses the same sentences in other words", code, 2)

code, _ = run_stop(ROWS + [answer(REWRITTEN)])
check("hook passes a reply that says something new", code, 0)

code, _ = run_stop([user("wire the row"), answer(EVIDENCE_FIRST),
                    meta(FEEDBACK), answer(EVIDENCE_AGAIN)])
check("hook passes a reply whose only likeness is its evidence", code, 0)

code, _ = run_stop(ROWS + [answer(SHAVED)], extra={"stop_hook_active": False})
check("hook stands down where nothing has been refused", code, 0)

code, _ = run_stop(ROWS + [answer(SHAVED)],
                   env={"INTELLIGENCE_ALLOW_REPEAT": "1"})
check("the hatch lets the reply stand", code, 0)

code, _ = run_stop([user("go"), answer(WITH_OFFER),
                    meta("Stop hook feedback:\n" + OFFER), answer(DRAFT)])
check("hook passes the reply that removed the phrase it was told to", code, 0)

SPENT = ROWS + [answer(SHAVED), meta("Stop hook feedback:\n" + g.HEADLINE),
                answer(REORDERED), meta("Stop hook feedback:\n" + g.HEADLINE),
                answer(SWAPPED)]
code, _ = run_stop(SPENT)
check("hook stands down once its own refusals are spent", code, 0)

code, _ = run_stop([user("go"), answer(DRAFT)])
check("hook passes a reply with no refused draft behind it", code, 0)

code, _ = run_stop(ROWS + [answer(SHAVED)], extra={"transcript_path": ""})
check("an unreadable transcript refuses nothing", code, 0)

p = subprocess.run([sys.executable, str(TARGET), "sniff"],
                   capture_output=True, text=True)
check("an unrecognised verb is a refusal rather than a pass", p.returncode, 2)


if FAILURES:
    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"\n{len(FAILURES)} failing")
    sys.exit(1)
print("repetition-guard: all cases pass")
