#!/usr/bin/env python3
"""Refuses an explanation written in the vocabulary of the work rather than the reader's.

The rule, in the words it was given: "Respond with a plain-English brief --
organized by what is true now rather than by what I did, no jargon or tool
names, open decisions named at the end -- whenever reporting state or
explaining a situation."

Only the vocabulary half of that is decidable by a script. Whether a brief is
organized by what is true, and whether it closes on the open decisions, are
judgements a regular expression makes badly, and a gate that guesses at them
would refuse good replies until it was switched off. Those two live in
INTELLIGENCE.md as context. This refuses the half that can be read off the page:
a reply that answers "what is going on" by naming files, scripts, branches and
slash commands, none of which are things the reader asked about.

Two turns owe that. The first is the question: a request to explain, to say what
is happening, or to put something in plain English. The second is /short, whose
whole promise is an answer a person can read, and which was carrying the rule as
a line of guidance with nothing behind it. Every other turn is left alone, so
naming a file in an ordinary working reply costs nothing.

Under /short the reading is narrower, because that skill already separates the
answer from its evidence: the quoted question, the tables, the lists and the
fences are page, and only the sentences that explain are weighed. A path in the
evidence is the answer being concrete. The same path in the prose is the answer
being about the machinery.

A term the person used first is theirs, not the reply retreating into jargon, so
it never counts against either turn.

  guard-stop  Stop hook. Read the reply just written and refuse a jargon-heavy
              answer to a request for an explanation or a /short question.
  measure     Report what a transcript's last reply scores, without judging.
  install     Wire the hook into settings.json.

INTELLIGENCE_PLAIN_OFF=1 disables it. INTELLIGENCE_PLAIN_ALLOW=1 lets one reply
through that has to name a path, for a question that asked for the path.
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
# missing _lib stands the guard down instead: guard_stop notes it and exits 0.
try:
    _lib = _shared()
except Exception:
    _lib = None

# The number of jargon terms an explanation may carry before it stops being one.
# Not zero: a brief may have to name the one thing it is about, and refusing a
# single mention would refuse the sentence that identifies the subject.
BUDGET = int(os.environ.get("INTELLIGENCE_PLAIN_BUDGET", "2"))

# What counts as asking for an explanation. Each is a way of asking for the
# state of things rather than for a change to them.
ASKING = re.compile(
    r"\b(?:explain|in (?:plain )?english|plain english|what(?:'s| is| are)? (?:going on|"
    r"you doing|happening|the (?:state|status|situation))|where (?:are we|do (?:we|things) stand)|"
    r"catch me up|walk me through|what did you (?:do|change)|give me (?:the )?(?:a )?"
    r"(?:brief|rundown|summary|overview)|break (?:it|this) down|what does (?:this|that) mean|"
    r"more on what you mean)\b",
    re.I,
)

# Terms that name the machinery instead of the thing. Each is a lexical shape
# rather than a word list, so a file nobody has written yet is caught the same
# as one that exists.
JARGON = (
    ("a file name", re.compile(r"\b[\w.-]+\.(?:py|js|mjs|cjs|jsx|ts|tsx|sh|sql|toml|ya?ml)\b")),
    ("a path", re.compile(r"(?<![\w/])(?:src|lib|api|scripts|supabase|public|dist|node_modules)/[\w./-]+")),
    # Any word written as a command rather than the enumerated ones: a list of
    # names goes stale the day a skill is renamed, and then the guard passes the
    # new name while refusing the retired one.
    ("a slash command", re.compile(r"(?<![\w/])/[a-z][a-z-]{2,}\b")),
    ("a branch reference", re.compile(r"\b(?:origin/[\w.-]+|HEAD(?:~\d+|\^)?)\b")),
    ("a version-control term", re.compile(r"\b(?:rebase[ds]?|squash(?:ed|ing)?|force-push(?:ed)?|"
                                          r"worktree|auto-merge|fast-forward(?:ed)?|cherry-pick(?:ed)?|"
                                          r"pre-?commit|PreToolUse|PostToolUse|Stop hook)\b", re.I)),
    ("a code identifier", re.compile(r"\b[a-z]+(?:[A-Z][a-z]+)+\(\)|\b\w+\(\)")),
)


def last_question(rows):
    """The last thing the person actually typed.

    A user row also carries tool results, which are the session talking to
    itself. Only the text a person wrote decides whether they asked for an
    explanation, so everything else in the row is passed over.
    """
    for row in reversed(rows):
        if row.get("type") != "user":
            continue
        content = (row.get("message") or {}).get("content")
        if isinstance(content, str):
            said = content
        elif isinstance(content, list):
            said = "\n".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        else:
            continue
        # A turn the harness opened on its own carries no question of its own.
        said = re.sub(r"<system-reminder>.*?</system-reminder>", " ", said, flags=re.S)
        said = re.sub(r"<[^>]+>", " ", said)
        if said.strip():
            return said
    return ""


def findings(text, question="", answer_only=False):
    """Every jargon term in a reply's prose, as (what it is, the term).

    A term the question already carried is dropped. Somebody who names a file in
    the asking is owed an answer that names it back, and a gate that charged for
    that would push the reply into pronouns to say the same thing.
    """
    if _lib is None:
        prose = text
    else:
        prose = _lib.answer_prose(text) if answer_only else _lib.prose_only(text)
    asked = question.lower()
    found = []
    for name, pattern in JARGON:
        for hit in pattern.finditer(prose):
            if hit.group(0).lower() in asked:
                continue
            found.append((name, hit.group(0)))
    return found


def judge(question, reply, skill=None):
    """Whether this reply owes plain English, and what it spent if so."""
    if skill == "short":
        return True, findings(reply, question, answer_only=True)
    if not ASKING.search(question):
        return False, []
    return True, findings(reply, question)


def guard_stop():
    if os.environ.get("INTELLIGENCE_PLAIN_OFF") == "1":
        sys.exit(0)
    if os.environ.get("INTELLIGENCE_PLAIN_ALLOW") == "1":
        sys.exit(0)
    if _lib is None:
        sys.stderr.write("plain-brief-guard: _lib.py unavailable; standing down\n")
        sys.exit(0)
    try:
        event = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    # A second pass means the reply has already been sent back once.
    if event.get("stop_hook_active"):
        sys.exit(0)
    path = event.get("transcript_path")
    if not path or not Path(path).exists():
        sys.exit(0)

    rows = _lib.read_transcript(path)
    reply, _ = _lib.final_reply(rows)
    if not reply.strip():
        sys.exit(0)

    skill = _lib.active_skill(rows)
    applies, found = judge(last_question(rows), reply, skill)
    if not applies or len(found) <= BUDGET:
        sys.exit(0)

    listed = "".join(f"  {term}  ({what})\n" for what, term in found[:10])
    if len(found) > 10:
        listed += f"  and {len(found) - 10} more\n"
    if skill == "short":
        opening = ("\nBLOCKED: this is a /short answer written in the vocabulary of the\n"
                   "work rather than the reader's.\n\n")
        remedy = ("\nSay it in the words the person would use. The machinery still belongs\n"
                  "in the evidence under the answer, where a table, a list or a fenced\n"
                  "command costs nothing -- what cannot carry it is the prose.\n")
    else:
        opening = ("\nBLOCKED: this was a request for an explanation, and the reply answers it\n"
                   "in the vocabulary of the work.\n\n")
        remedy = ("\nWrite it again as a plain brief. Say what is true now rather than what was\n"
                  "done to get there, name things the way the reader would name them, and close\n"
                  "on the decisions still open. A file, a branch or a command is only worth\n"
                  "naming when the reader has to type it.\n")
    sys.stderr.write(
        opening + listed + remedy
        + "INTELLIGENCE_PLAIN_ALLOW=1 lets one through that genuinely has to name a path.\n"
    )
    sys.exit(2)


def measure(path):
    """What a transcript's last reply scores, for checking the gate itself."""
    if _lib is None:
        print("plain-brief-guard: _lib.py unavailable; nothing measured", file=sys.stderr)
        return 1
    rows = _lib.read_transcript(Path(path))
    reply, _ = _lib.final_reply(rows)
    skill = _lib.active_skill(rows)
    applies, found = judge(last_question(rows), reply, skill)
    print(f"governing skill: {skill or '-'}")
    print(f"owes plain english: {'yes' if applies else 'no'}")
    print(f"jargon terms: {len(found)} against a budget of {BUDGET}")
    for what, term in found:
        print(f"  {term}  ({what})")
    return 0


def install():
    """Put the Stop hook into settings.json, and leave it there once it is."""
    settings = Path.home() / ".intelligence" / "settings.json"
    command = "~/.intelligence/tools/plain-brief-guard.py guard-stop"
    try:
        config = json.loads(settings.read_text())
    except Exception:
        print("plain-brief-guard: settings.json unreadable; not wired", file=sys.stderr)
        return 1

    hooks = config.setdefault("hooks", {}).setdefault("Stop", [])
    for entry in hooks:
        for hook in entry.get("hooks", []):
            if "plain-brief-guard.py" in hook.get("command", ""):
                print("plain-brief-guard: already wired")
                return 0
    hooks.append({"matcher": "*", "hooks": [{"type": "command", "command": command}]})
    _lib.write_atomic(settings, json.dumps(config, indent=2) + "\n")
    print("plain-brief-guard: wired into Stop")
    return 0


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "guard-stop":
        guard_stop()
    elif action == "measure":
        return measure(sys.argv[2])
    elif action == "install":
        return install()
    else:
        print(__doc__.strip())
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
