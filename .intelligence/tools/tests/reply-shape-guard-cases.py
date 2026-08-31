#!/usr/bin/env python3
"""Cases the reply-shape guard has to get right.

The guard is worth only what it refuses, and worth nothing if it refuses a reply
that was fine. So both edges are fixed here: the narrating forms are caught, a
plainly stated correction is not, a trailing offer is caught while the same
words mid-reply are left alone, and the cap applies while /short governs the
turn or the turn is the session's first.

That reach is the one with a false positive to spend, so its edges are held
apart here in both directions: a skill body, a tool result, a reminder and a
scheduled run are none of them somebody typing, and a second typed prompt ends
the reach for the rest of the session.

The quoted question rides the same reach with one exemption, held here in both
directions too: a first reply answers the message directly above it and is asked
for no quote, while a /short turn further in is asked for one and has its words
proved.

The cap itself is read from the skill file, so one case points the guard at a
skill stating a different number and checks that the verdict moves with it. The
quote is proved against the prompt in one direction only, so two cases hold that
edge apart: a long prompt quoted down to the sentence that asks passes, and a
short one restated in other words does not.

  reply-shape-guard-cases.py        run them
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
              or Path(__file__).resolve().parent.parent / "reply-shape-guard.py")

# settings.json carries an env block that a session exports into every process
# under it. Inherited, either switch decides the verdict before the guard reads
# a word, which reads as a guard that has stopped refusing.
os.environ.pop("INTELLIGENCE_REPLY_SHAPE_OFF", None)
os.environ.pop("INTELLIGENCE_ALLOW_SELFREF", None)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g = load()


# The question every fixture reply is answering, and the quote a /short reply
# has to open with to be answering it.
ASKED = "does the mirror carry the row"
Q = "> %s\n\n" % ASKED


def faults(text, skill=None, cap=6, prompt=ASKED, opening=False, first=False,
           stale=False):
    return g.judge(text, skill, cap, prompt, opening, first, stale)


# -- narrating the session ---------------------------------------------------

for label, text in [
    ("as i mentioned", "As I mentioned, the Pi holds its own copy."),
    ("apology", "Apologies for that. The Pi holds its own copy."),
    ("sorry", "Sorry, the Pi holds its own copy."),
    ("my mistake", "My mistake. The Pi holds its own copy."),
    ("i was wrong", "I was wrong about the Pi. It holds its own copy."),
    ("earlier i said", "Earlier I said the Pi was current. It is not."),
    ("previous answer", "My previous answer put the file on the Pi."),
    ("misread", "I misread the registry. The row is wired."),
    ("youre right that i", "You're right that I skipped the Pi."),
]:
    check(f"catches {label}", len(faults(text)), 1)

check("plain corrected fact passes",
      faults("The Pi holds its own copy and it lagged two versions behind."), [])
check("ordinary report passes",
      faults("The row is wired and the mirror carries it."), [])

os.environ["INTELLIGENCE_ALLOW_SELFREF"] = "1"
check("override lets self-reference through",
      faults("Apologies, the row is wired."), [])
os.environ.pop("INTELLIGENCE_ALLOW_SELFREF")


# -- the trailing offer ------------------------------------------------------

check("catches let me know if",
      len(faults("The row is wired.\nLet me know if you want the Pi synced too.")), 1)
check("catches want me to",
      len(faults("The row is wired.\nWant me to sync the Pi as well?")), 1)
check("catches happy to help",
      len(faults("The row is wired.\nHappy to help with the rest.")), 1)

MID = ("Want me to sync the Pi, or leave it?\n"
       "The row is wired and the mirror carries it.\n"
       "The cap comes out of the skill file.\n"
       "Nothing else is owed.\n"
       "The mirror commit is 5e1ea807.\n"
       "The Pi reports in step.")
check("a mid-reply question is not a closing offer", faults(MID), [])


# -- the sentence cap --------------------------------------------------------

SIX = "One. Two. Three. Four. Five. Six."
SEVEN = SIX + " Seven."

check("six sentences pass under /short", faults(Q + SIX, "short"), [])
check("seven sentences are refused under /short",
      len(faults(Q + SEVEN, "short")), 1)
check("the cap is silent without /short", faults(SEVEN), [])
check("the cap is silent under another skill", faults(SEVEN, "ship"), [])

PAGE = ("One. Two. Three.\n"
        "\n"
        "| a | b |\n"
        "|---|---|\n"
        "| the row is wired | yes |\n"
        "| the mirror carries it | yes |\n"
        "\n"
        "- the Pi reports in step\n"
        "- the cap reads six\n"
        "- the commit is 5e1ea807\n"
        "\n"
        "# A heading\n"
        "> a quoted line\n")
check("tables, lists, headings and quotes cost no sentences",
      faults(Q + PAGE, "short"), [])

FENCED = "One. Two.\n\n```\necho one. two. three. four. five. six. seven.\n```\n"
check("a fenced block costs no sentences", faults(Q + FENCED, "short"), [])

check("a missing cap is a fault under /short",
      len(faults(Q + SIX, "short", None)), 1)


# -- the question above the answer -------------------------------------------

check("an answer without the question above it is refused",
      len(faults(SIX, "short")), 1)
check("the quote is only asked for under /short", faults(SIX), [])
check("a restatement in other words is refused",
      len(faults("> whether the deployment carries the change\n\n" + SIX,
                 "short")), 1)
check("a long prompt quoted down to the sentence that asks passes",
      faults(Q + SIX, "short", 6,
             "I was reading the ledger this morning and it left me wondering: "
             "does the mirror carry the row, or has it gone stale?"), [])
check("an unreadable prompt leaves presence checkable and accuracy not",
      faults(Q + SIX, "short", 6, None), [])
check("an unreadable prompt still asks for the quote",
      len(faults(SIX, "short", 6, None)), 1)
check("a quote further down does not stand in for one at the top",
      len(faults("One. Two.\n\n> %s\n" % ASKED, "short")), 1)

check("the first message is not quoted back at it",
      faults(SIX, "short", first=True), [])
check("quoting it anyway is not a fault",
      faults(Q + SIX, "short", first=True), [])
check("a first reply may open on the thing it is about",
      faults("> ReferenceError: window is not defined\n\n" + SIX,
             "short", first=True), [])
check("a first reply owes the cap all the same",
      len(faults(SEVEN, "short", first=True)), 1)

check("no quote at the top reads as none", g.quoted_head("Yes.\n"), None)
check("leading blank lines do not hide the quote",
      g.quoted_head("\n\n> %s\n\nYes." % ASKED), ASKED)
check("a two-line quote is read as one",
      g.quoted_head("> does the mirror\n> carry the row\n\nYes."),
      "does the mirror\ncarry the row")

check("quoting the prompt echoes it", g.echoes("carry the row", ASKED), True)
check("inventing a word does not",
      g.echoes("carry the deployment", ASKED), False)
check("an empty quote echoes nothing", g.echoes("", ASKED), False)


# -- the cap comes from the skill file ---------------------------------------

with tempfile.TemporaryDirectory() as d:
    skill = Path(d) / "SKILL.md"
    skill.write_text("# Short\n\nThree sentences of prose, at most, and fewer.\n")
    check("cap parsed from a file stating three", g.declared_cap(skill), 3)
    skill.write_text("# Short\n\nNo limit is stated here.\n")
    check("no cap parsed from a file stating none", g.declared_cap(skill), None)

check("cap parsed from the installed skill", g.declared_cap(), 6)


# -- which skill governs the turn --------------------------------------------

def user(text):
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


MARKER = "Base directory for this skill: /Users/x/.intelligence/skills/short"


def meta(text):
    return dict(user(text), isMeta=True)


def result(text="the row is wired"):
    return {"type": "user",
            "message": {"content": [{"type": "tool_result", "content": text}]}}


def answer(text="The row is wired and the mirror carries it."):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def command(name="short", args=None):
    """A slash command as the harness records it: a plain row, not a meta one."""
    text = ("<command-message>%s</command-message>"
            "<command-name>/%s</command-name>" % (name, name))
    if args:
        text += "<command-args>%s</command-args>" % args
    return user(text)

check("skill invoked last governs",
      g.active_skill([user("what is up"), user(MARKER)]), "short")
check("a plain prompt after the skill ends it",
      g.active_skill([user(MARKER), user("what is up")]), None)
check("no skill in the transcript",
      g.active_skill([user("what is up")]), None)
check("a command-name marker counts",
      g.active_skill([user("hi"), user("<command-name>/short</command-name>")]), "short")


# -- what the person actually typed ------------------------------------------

check("the prompt before the skill body is the question",
      g.governing_prompt([user(ASKED), user(MARKER)]), ASKED)
check("a slash command carries its own question",
      g.governing_prompt([user("<command-name>/short</command-name>"
                               "<command-args>%s</command-args>" % ASKED)]),
      ASKED)
check("a system reminder is not what was typed",
      g.governing_prompt([user(ASKED + "<system-reminder>read the registry"
                               "</system-reminder>"), user(MARKER)]), ASKED)
check("a later plain prompt replaces earlier arguments",
      g.governing_prompt([user("<command-name>/short</command-name>"
                               "<command-args>an older question</command-args>"),
                          user(ASKED), user(MARKER)]), ASKED)
check("nothing typed reads as no question",
      g.governing_prompt([user(MARKER)]), None)
# A refusal from this guard returns as a meta row. Read as the live prompt, the
# rewrite it asks for owes a quote of the refusal itself, which is unsatisfiable.
check("a stop hook refusal is not what was typed",
      g.governing_prompt([user(ASKED), meta("BLOCKED: this reply is the wrong "
                                            "shape.")]), ASKED)


# -- the hook itself ---------------------------------------------------------

# A transcript with two typed prompts behind it: the conversation has opened,
# so the reach that only binds its first reply is done.
LATER = [user(ASKED), user("and does the Pi carry it too")]

# /short invoked on a question the session has already moved past. The answer no
# longer sits under the message it settles, which is where the quote is owed.
SHORT_LATER = [user("what is the mirror for"), user(ASKED), user(MARKER)]


def run_stop(reply, rows=None, extra=None, env=None):
    """The guard as the Stop hook runs it, against a written transcript."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "t.jsonl"
        lines = list(rows or [user("go")])
        lines.append({"type": "assistant",
                      "message": {"content": [{"type": "text", "text": reply}]}})
        path.write_text("\n".join(json.dumps(r) for r in lines) + "\n")
        payload = {"transcript_path": str(path)}
        payload.update(extra or {})
        e = dict(os.environ)
        e.update(env or {})
        p = subprocess.run([sys.executable, str(TARGET), "guard-stop"],
                           input=json.dumps(payload), capture_output=True,
                           text=True, env=e)
        return p.returncode, p.stderr


code, err = run_stop("Apologies, the row is wired.")
check("hook refuses a narrating reply", code, 2)
check("the refusal names the phrase", 'says "Apologies"' in err, True)

code, _ = run_stop("The row is wired and the mirror carries it.", rows=LATER)
check("hook passes an ordinary reply", code, 0)

code, _ = run_stop("Apologies, the row is wired.", extra={"stop_hook_active": True})
check("a second pass lets the reply stand", code, 0)

code, _ = run_stop("Apologies, the row is wired.",
                   env={"INTELLIGENCE_REPLY_SHAPE_OFF": "1"})
check("the off switch stands the guard down", code, 0)

code, err = run_stop(Q + SEVEN, rows=[user(ASKED), user(MARKER)])
check("hook refuses seven sentences under /short", code, 2)
check("the refusal names the count", "7 sentences of prose" in err, True)

code, _ = run_stop(Q + SIX, rows=[user(ASKED), user(MARKER)])
check("hook passes six sentences under /short", code, 0)

code, err = run_stop(SIX, rows=SHORT_LATER)
check("hook refuses an answer with no question above it", code, 2)
check("the refusal says what is missing", "quoted above the" in err, True)

code, _ = run_stop(SIX, rows=[user(ASKED), meta(MARKER)])
check("hook asks for no quote where the question is the message above", code, 0)

code, err = run_stop(SIX, rows=[user(ASKED), answer(), command()])
check("hook asks for the quote once a command stands between", code, 2)
check("the refusal says what is missing there", "quoted above the" in err, True)

code, err = run_stop("> whether the deployment carries the change\n\n" + SIX,
                     rows=SHORT_LATER)
check("hook refuses a restated question", code, 2)
check("the refusal quotes what was written instead",
      "which is not what was asked" in err, True)

code, _ = run_stop("", rows=[user("go")])
check("an empty reply is nothing to judge", code, 0)

code, _ = run_stop("Apologies.", extra={"transcript_path": "/nonexistent/x.jsonl"})
check("a missing transcript stands the guard down", code, 0)


# -- the reach on the conversation's first reply -----------------------------

check("an opening reply does not owe the quote", faults(SIX, opening=True), [])
check("an opening reply owes the cap",
      len(faults(Q + SEVEN, opening=True)), 1)
check("an opening reply in shape passes", faults(Q + SIX, opening=True), [])
check("a later reply owes neither", faults(SEVEN), [])
check("an opening reply under /short is judged once",
      len(faults(SEVEN, "short", opening=True)), 1)

with tempfile.TemporaryDirectory() as d:
    skill = Path(d) / "SKILL.md"
    skill.write_text("# Short\n\nthe first reply\nof every conversation takes this shape.\n")
    check("the reach is read across a wrapped line", g.declared_opener(skill), True)
    skill.write_text("# Short\n\nSix sentences, at most.\n")
    check("a file no longer claiming it leaves the reach off",
          g.declared_opener(skill), False)
    check("an unreadable file leaves the reach off",
          g.declared_opener(Path(d) / "gone.md"), False)

check("the installed skill claims it", g.declared_opener(), True)


# -- what counts as somebody typing ------------------------------------------

check("one typed prompt is the opening turn",
      g.opening_reply([user(ASKED)]), True)
check("a second typed prompt ends it",
      g.opening_reply([user(ASKED), user("and the Pi?")]), False)
check("a skill body is not somebody typing",
      g.opening_reply([user(ASKED), meta(MARKER)]), True)
# The reach is a position rather than a tally. A command asks nothing, so it
# adds no question, but the answer after one no longer stands under the message
# it settles -- which is the whole of what the exemption was excusing.
check("a slash command ends the opening turn",
      g.opening_reply([user(ASKED),
                       user("<command-name>/short</command-name>")]), False)
check("a tool result is not somebody typing",
      g.opening_reply([user(ASKED), result(), result()]), True)
check("a bare reminder is not somebody typing",
      g.opening_reply([user(ASKED),
                       user("<system-reminder>read the registry</system-reminder>")]),
      True)
check("a scheduled run is outside the reach",
      g.opening_reply([user("[SCHEDULED TASK] run the maintenance pass")]), False)
check("a compaction ends the reach rather than restarting it",
      g.opening_reply([dict(user("carry on"), isCompactSummary=True),
                       user(ASKED)]), False)
check("nothing typed is not an opening turn", g.opening_reply([result()]), False)
check("prompts are counted from the person's side",
      g.typed_prompts([user(ASKED), meta(MARKER), result(), user("and the Pi?")]), 2)
check("turns count the command the questions do not",
      g.person_turns([user(ASKED), meta(MARKER), result(), command()]), 2)
check("a reminder on its own is not a turn",
      g.person_turns([user(ASKED),
                      user("<system-reminder>read the registry</system-reminder>")]),
      1)


# -- a reach that lands on a settled question --------------------------------

check("a command over an answered question is stale",
      g.stale_reach([user(ASKED), answer(), command()]), True)
check("a command carrying its own words asks something",
      g.stale_reach([user(ASKED), answer(),
                     command(args="and does the Pi carry it")]), False)
# Asked twice before anything replied, the question is live and owed an answer.
check("nothing answered yet is not stale",
      g.stale_reach([user(ASKED), command()]), False)
check("a plain question last is not stale",
      g.stale_reach([user(ASKED), answer(), user("and the Pi?")]), False)
check("a skill body is not the person reaching back",
      g.stale_reach([user(ASKED), answer(), meta(MARKER)]), False)
check("nothing typed is not stale", g.stale_reach([result()]), False)

check("a stale reach is a sentence and the quote",
      faults(Q + "It holds nothing left to answer.", "short", stale=True), [])
check("a stale reach refuses the answer written shorter",
      len(faults(Q + SIX, "short", stale=True)), 1)
check("a stale reach still owes the quote",
      len(faults("It holds nothing left to answer.", "short", stale=True)), 1)

with tempfile.TemporaryDirectory() as d:
    skill = Path(d) / "SKILL.md"
    skill.write_text("# Short\n\nsay in a sentence that it holds nothing "
                     "left to answer, and stop.\n")
    check("the settled shape is read from the file", g.declared_settled(skill), True)
    skill.write_text("# Short\n\nSix sentences, at most.\n")
    check("a file no longer saying it leaves the rule off",
          g.declared_settled(skill), False)
    check("an unreadable file leaves the rule off",
          g.declared_settled(Path(d) / "gone.md"), False)

check("the installed skill states it", g.declared_settled(), True)


# -- the reach through the hook ----------------------------------------------

code, err = run_stop(SEVEN, rows=[user(ASKED)])
check("hook refuses a long unquoted opening reply", code, 2)
check("the refusal says why the shape was owed",
      "conversation's first reply" in err, True)
check("the refusal names the count", "7 sentences of prose" in err, True)
check("the refusal names its own hatch",
      "INTELLIGENCE_OPENER_OFF=1" in err, True)

code, _ = run_stop(Q + SIX, rows=[user(ASKED)])
check("hook passes an opening reply in shape", code, 0)

code, _ = run_stop(SEVEN, rows=LATER)
check("hook leaves a later reply alone", code, 0)

code, _ = run_stop(SEVEN, rows=[user(ASKED)],
                   env={"INTELLIGENCE_OPENER_OFF": "1"})
check("the hatch leaves the opening reply unshaped", code, 0)

code, _ = run_stop(SEVEN, rows=[user("[SCHEDULED TASK] run the pass")])
check("hook leaves a scheduled run alone", code, 0)

code, err = run_stop(Q + SEVEN, rows=[user(ASKED), user(MARKER)])
check("a /short refusal does not explain the opening reach",
      "conversation's first reply" in err, False)


# -- the settled reach through the hook --------------------------------------

SETTLED_ROWS = [user(ASKED), answer(), command()]

code, err = run_stop(Q + SIX, rows=SETTLED_ROWS)
check("hook refuses the settled answer written shorter", code, 2)
check("the refusal names the cap it fell to",
      "against a cap of 1" in err, True)
check("the refusal says why the reach landed there",
      "already has an answer standing" in err, True)

code, _ = run_stop(Q + "It holds nothing left to answer.", rows=SETTLED_ROWS)
check("hook passes the message quoted and a sentence", code, 0)

LIVE = "and does the Pi carry it"
code, _ = run_stop("> %s\n\n%s" % (LIVE, SIX),
                   rows=[user(ASKED), answer(), command(args=LIVE)])
check("hook leaves a command carrying its own question alone", code, 0)


if FAILURES:
    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"\n{len(FAILURES)} failing")
    sys.exit(1)
print("reply-shape-guard: all cases pass")
