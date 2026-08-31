#!/usr/bin/env python3
"""Refuses a reply that narrates the session, or is the wrong shape for /short.

Three rules, one hook, because each asks about the shape of the reply just
written and separately they would read the same transcript three times.

The first rule is stated in INTELLIGENCE.md and in the /short skill: a reply
carries the answer and nothing about the exchange around it. An account of an
earlier mistake, an apology, and a trailing offer to do more are therefore
faults. concise-guard.py catches the opening preamble and the summary heading;
this one sees the same habit in the middle of a reply and at its close, which is
where it actually lives.

The second rule is /short's own promise: six sentences of prose. Nothing
measured it. A word budget is a different rule -- a twelve-sentence reply passes
150 words comfortably -- so the skill's headline constraint was the one thing
about it that nothing checked.

The cap is read out of the skill file rather than written here. A number copied
into a guard drifts from the document it came from and then enforces last
month's rule while the file says otherwise.

The third rule is /short's other promise: the question stands quoted above the
answer. An answer arriving alone is read against whatever the person remembers
asking, so an answer to a narrowed reading of the question passes as an answer
to the question. Putting the two side by side is what makes that visible, and
only holds if the quote carries the words that were typed -- a paraphrase in the
answerer's vocabulary is the narrowing, wearing the costume of the check against
it. So the quote is required, and its words are proved against the prompt.

It is not required where the question is the conversation's first message. That
one stands directly above the answer with nothing in between, so the pair is
already side by side and quoting it copies out a line the eye has not left yet.
A quote written there anyway is still held to the words that were typed, unless
it shares none of them: an error line or a paste being answered about is not
standing in for the question, and has nothing to be wrong about.

The exemption is a position and not a tally, and reading it as one was how it
leaked. Counted in questions, a session where somebody typed one question and
then a bare slash command still read as its own opening turn, so the quote went
on being excused for the rest of it while the answer had drifted two messages
down from what it settled. It is counted in turns now: a command is somebody
typing even though it asks nothing.

That same command is also where a reach can land on a question already answered,
which the skill gives a shape of its own -- the message quoted, one sentence
saying it holds nothing left, and a stop. Nothing measured that either, and what
it costs is the failure the rule was written against: an answer restated in
fewer words, standing where nothing on the page says it is a second copy.

The fourth rule is where the first three reach. /short shaped only the turns
that asked for it, which left the opening reply of every session -- the one read
hardest and argued with least -- free to run long and be wrong at the top. So
the shape is now owed by the first reply of a conversation whether or not the
command was typed. The reach is read out of the skill file rather than decided
here, and a file that no longer claims it leaves the rule off.

The cap lands on the writing up and never on the work. This is a Stop hook: it
sees a turn that has already finished running whatever it ran, so it can shorten
an answer and has no way to shorten the work behind one.

  guard-stop   Stop hook. Judge the reply just written.
  measure      Report the verdict for a transcript, without refusing.

INTELLIGENCE_REPLY_SHAPE_OFF=1 disables it. INTELLIGENCE_ALLOW_SELFREF=1 lets
through the one reply that has to name an earlier statement.
INTELLIGENCE_OPENER_OFF=1 leaves an opening reply unshaped.
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
    prose_only = _lib.prose_only
    answer_prose = _lib.answer_prose
    row_text = _lib.row_text
    active_skill = _lib.active_skill
    SKILL_MARKER = _lib.SKILL_MARKER
    COMMAND_MARKER = _lib.COMMAND_MARKER
except Exception:
    _lib = None


def _skill():
    """The /short skill file, beside this tool's own tree before the installed one.

    Same reason _lib is resolved this way: a copy running out of a checkout has
    to read that checkout's skill. Reading only the installed path made the cap
    unreadable wherever the tree is not installed, and an unreadable cap is a
    fault, so the cases failed on every machine that had not installed it.
    """
    beside = Path(__file__).resolve().parent.parent / "skills" / "short" / "SKILL.md"
    if beside.is_file():
        return beside
    return Path.home() / ".intelligence" / "skills" / "short" / "SKILL.md"


SKILL = _skill()

# Every form that narrates the exchange rather than answering within it. A
# corrected fact stated plainly matches none of these; an account of the mistake
# behind it does, which is the line the rule draws.
SELF_REFERENCE = re.compile(
    r"\b(?:"
    r"as (?:i|we) (?:mentioned|said|noted|explained)|"
    r"as (?:mentioned|noted|stated) (?:earlier|above|before|previously)|"
    r"(?:i|we) (?:previously|earlier|initially|originally) (?:said|mentioned|noted|claimed|told|wrote|reported)|"
    r"earlier (?:i|we) (?:said|wrote|claimed|reported|was|were|incorrectly|wrongly|mistakenly)|"
    r"my (?:earlier|previous|last|first) (?:answer|reply|response|statement|message|claim)|"
    r"apolog(?:y|ies|ise|ize|ised|ized|ising|izing)|"
    r"(?:i'?m |i am )?sorry\b|"
    r"my (?:mistake|error|bad)\b|"
    r"(?:i|that) was (?:wrong|incorrect|mistaken)|"
    r"to correct (?:myself|my earlier|that)|"
    r"(?:i|we) (?:misread|misspoke|miscounted|misstated)|"
    r"(?:correcting|correction to) (?:myself|my|the) (?:earlier|previous|above)|"
    r"you'?re right that (?:i|we)"
    r")\b",
    re.I,
)

# The trailing offer, matched only in the tail of a reply. The same words in the
# middle are usually a real question about which way to go, and a guard that
# refuses those trains the model out of asking.
CLOSING_OFFER = re.compile(
    r"\b(?:"
    r"let me know if|just (?:let me know|say the word|tell me)|"
    r"happy to (?:help|do|take|dig|keep)|"
    r"(?:do you )?want me to\b|would you like me to|"
    r"if you(?:'d| would) like|feel free to|"
    r"shall i\b|anything else"
    r")\b",
    re.I,
)

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
                "twelve": 12}

# The cap as the skill states it, in either of the two places the file says it.
CAP = re.compile(
    r"\b(?P<n>%s|\d+)\s+sentences?\b[^.\n]{0,40}?\b(?:at most|maximum|max)\b"
    % "|".join(NUMBER_WORDS),
    re.I,
)

# The reach, as the skill states it. Parsed for the same reason the cap is: a
# gate holding its own copy of a rule goes on enforcing it after the document
# has stopped saying it. Whitespace is loose because the sentence wraps.
OPENER = re.compile(r"first\s+reply\s+of\s+every\s+conversation", re.I)

# The skill's instruction for a reach that lands on a settled message. Read
# from the file for the reason the cap and the reach are: a rule the document
# has stopped stating is one this gate has to stop enforcing.
SETTLED = re.compile(
    r"say\s+in\s+a\s+sentence\s+that\s+it\s+holds\s+nothing\s+left\s+to\s+answer",
    re.I,
)

# A scheduled run has nobody reading it and no question to quote, so the reach
# stops at the door. The marker is the one guard-hub reads for the same purpose.
SCHEDULED = "[SCHEDULED TASK"

SENTENCE_END = re.compile(r"[.!?]+(?=\s|$)")

# The blockquote a /short reply opens with, and the marker stripped off each of
# its lines to get back to the words inside.
QUOTE_LINE = re.compile(r"^\s*>")
QUOTE_MARK = re.compile(r"^\s*>+\s?")

# Words too ordinary to prove one sentence came from another. Without them a
# paraphrase sharing nothing but its grammar reads as a quotation.
COMMON = {"that", "this", "with", "from", "have", "here", "there", "their",
          "them", "they", "your", "yours", "what", "when", "which", "where",
          "will", "would", "should", "could", "does", "just", "than", "then",
          "into", "onto", "over", "some", "such", "only", "also", "been",
          "being", "about", "above", "after", "before", "much", "more",
          "most", "make", "made", "take", "want", "need", "like", "said",
          "tell", "told", "give", "know", "thing", "things", "please"}

# Where a slash command carries the words typed after it. The two markers that
# say which skill is speaking are shared, since the vocabulary gate asks the
# same question of the same turn.
ARGS_MARKER = re.compile(r"<command-args>(.*?)</command-args>", re.S)

# What the harness injects on its own account, as against what it wraps around
# something typed. A row carrying only a reminder is nobody taking a turn, while
# a row carrying only a slash command is somebody taking one that asks nothing,
# so the two are stripped separately.
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)

# Scaffolding the harness wraps around a prompt. Left in, a quote is proved
# against text nobody typed, which is no proof at all.
NOISE = re.compile(
    r"<system-reminder>.*?</system-reminder>"
    r"|<command-message>.*?</command-message>"
    r"|<command-name>.*?</command-name>"
    r"|<command-args>.*?</command-args>",
    re.S,
)


def declared_cap(path=SKILL):
    """The sentence cap the skill file states, or None when it states none.

    Parsed rather than copied, so an edit to the skill moves the gate with it. A
    file that has stopped stating a cap is a rule gone unenforced, and the
    caller treats None as a fault rather than as permission.
    """
    try:
        text = path.read_text()
    except Exception:
        return None
    m = CAP.search(text)
    if not m:
        return None
    n = m.group("n").lower()
    return NUMBER_WORDS.get(n) or (int(n) if n.isdigit() else None)


def declared_opener(path=SKILL):
    """Whether the skill still claims the first reply of every conversation.

    A file that has stopped saying it, or that cannot be read at all, leaves the
    rule off. The cap is treated the other way round on purpose: it only ever
    binds a turn that asked to be shaped, while this binds turns nobody asked,
    so a half-installed tree would otherwise refuse the opening reply of every
    session on a machine that has never carried the skill.
    """
    try:
        text = path.read_text()
    except Exception:
        return False
    return bool(OPENER.search(text))


def person_turns(rows):
    """How many times the person has taken a turn, question or not.

    A slash command with nothing after it is somebody typing even though it asks
    nothing, and the difference from `typed_prompts` is the whole point: the
    exemption below is about where the question sits on the page rather than how
    many questions have been asked. A refusal from this guard comes back as a
    meta row, so a rewrite of a blocked reply is still the same turn.
    """
    n = 0
    for row in rows:
        if row.get("type") != "user" or row.get("isMeta"):
            continue
        if REMINDER.sub("", row_text(row)).strip():
            n += 1
    return n


def typed_prompts(rows):
    """How many times the person has typed into this session.

    Counted from the person's side rather than from the replies, because a turn
    answers one prompt however many times it stopped to run something. A skill
    body, a tool result and a bare reminder are all the harness talking to
    itself, and none of them is somebody asking.
    """
    n = 0
    for row in rows:
        if row.get("type") != "user" or row.get("isMeta"):
            continue
        text = row_text(row)
        if not text.strip():
            continue
        if SKILL_MARKER.search(text) or COMMAND_MARKER.search(text):
            continue
        if NOISE.sub("", text).strip():
            n += 1
    return n


def opening_reply(rows):
    """Whether this reply is the conversation's first answer.

    Counted in turns rather than in questions. The exemption this feeds is the
    skill's own, and the skill states it as a position -- it holds while the
    message being answered is the one directly above. So a bare command ends it
    exactly as a second question does: the answer that follows one stands two
    messages down from what it settles, which is where the quote is owed.

    A compaction ends the count rather than restarting it: the rows before the
    boundary are gone, so a reply well into a session would otherwise read as
    the first one and be refused for the shape of a turn nobody opened.
    """
    for row in rows:
        if row.get("isCompactSummary") or row.get("subtype") == "compact_boundary":
            return False
        if row.get("type") == "user" and SCHEDULED in row_text(row):
            return False
    return person_turns(rows) == 1


def governing_prompt(rows):
    """What the person typed for the turn being judged, or None.

    A /short invoked as a slash command carries the question in its arguments;
    one matched from an ordinary sentence leaves the question in the prompt that
    precedes the skill body. Both are the text a reply has to quote, so both
    resolve here. A plain prompt clears any arguments held from an earlier turn,
    because the question to quote is always the live one.

    A meta row is the harness speaking rather than the person -- this guard's own
    refusal comes back as one. Reading it as the live prompt leaves the rewrite
    owing a quote of the block that refused it, which no reply can satisfy, so
    the same rows `typed_prompts` passes over are passed over here.
    """
    plain, args = None, None
    for row in rows:
        if row.get("type") != "user" or row.get("isMeta"):
            continue
        text = row_text(row)
        if not text.strip():
            continue
        if SKILL_MARKER.search(text) or COMMAND_MARKER.search(text):
            found = ARGS_MARKER.search(text)
            if found and found.group(1).strip():
                args = found.group(1).strip()
            continue
        typed = NOISE.sub("", text).strip()
        if typed:
            plain, args = typed, None
    return args or plain


def declared_settled(path=SKILL):
    """Whether the skill still gives a settled reach one sentence and a stop.

    A file that no longer says it leaves the rule off, on the reach's reasoning
    rather than the cap's: this binds a turn nobody asked to be shaped, so a
    tree that cannot read the rule has to stand out of the way rather than
    refuse every reply on a rule it is guessing at.
    """
    try:
        text = path.read_text()
    except Exception:
        return False
    return bool(SETTLED.search(text))


def stale_reach(rows):
    """Whether the live prompt asks nothing and the reach fell back onto an answer.

    A slash command carrying no words sets the shape and asks nothing, so what
    the reply answers is the last thing actually typed. Where an answer already
    stands under that message, the skill asks for the message quoted and a
    sentence saying it holds nothing left, because the alternative is the same
    answer written shorter with nothing on the page saying it is a second copy.

    The answer standing in between is what makes it stale. A question typed
    twice before anything replied is live, owed a full answer, and reads
    identically without that test.
    """
    live = plain = None
    for i, row in enumerate(rows):
        if row.get("type") != "user" or row.get("isMeta"):
            continue
        text = row_text(row)
        if not text.strip():
            continue
        if SKILL_MARKER.search(text) or COMMAND_MARKER.search(text):
            found = ARGS_MARKER.search(text)
            if found and found.group(1).strip():
                plain = live = i
            else:
                live = i
            continue
        if NOISE.sub("", text).strip():
            plain = live = i
    if plain is None or live is None or live == plain:
        return False
    return any(row.get("type") == "assistant" and row_text(row).strip()
               for row in rows[plain + 1:live])


def quoted_head(text):
    """The blockquote a reply opens with, or None when it opens with anything else.

    Only the contiguous run of quoted lines at the top counts. A quote further
    down is evidence inside an answer, and reading one as the question would let
    a reply that never stated the question pass on the strength of a citation.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not QUOTE_LINE.match(lines[i]):
        return None
    out = []
    while i < len(lines) and QUOTE_LINE.match(lines[i]):
        out.append(QUOTE_MARK.sub("", lines[i]))
        i += 1
    return "\n".join(out).strip()


def significant(text):
    """The words in a phrase that could show where the phrase came from.

    Short and ordinary words are dropped, since two unrelated sentences share
    those freely. A phrase left with nothing falls back to all of its words
    rather than to an empty set, which would otherwise match anything.
    """
    words = re.findall(r"[\w']+", text.lower())
    carrying = {w for w in words if len(w) >= 4 and w not in COMMON}
    return carrying or set(words)


def echoes(quote, prompt):
    """Whether the quote is the prompt's own words rather than a restatement.

    Read one way only: every carrying word in the quote has to appear in the
    prompt, while the prompt may say a great deal the quote leaves out. That is
    the asymmetry the rule wants -- a long prompt quoted down to the sentence
    that asks is right, and a short prompt expanded into the answerer's
    vocabulary is the failure.
    """
    said = significant(prompt)
    shown = significant(quote)
    if not shown:
        return False
    if not said:
        return True
    return bool(shown & said) and not (shown - said)


def prose(text):
    """The reply's paragraphs: no fences, tables, headings, lists or quotes.

    Those carry facts that stand on their own, which the skill puts outside the
    count on purpose. Excluding them also keeps this guard from refusing a reply
    for the length of the evidence under it, rather than of the argument.
    """
    return answer_prose(text) if _lib else text


def count_sentences(text):
    parts = [p for p in SENTENCE_END.split(text) if re.search(r"\w", p)]
    return len(parts)


def tail(text, lines=3):
    """The closing few lines of prose, where a trailing offer sits."""
    rows = [line for line in text.splitlines() if line.strip()]
    return "\n".join(rows[-lines:])


def judge(text, skill=None, cap=None, prompt=None, opening=False, first=False,
          stale=False):
    """Every fault in one reply, as lines fit to print in a refusal.

    A prompt of None is a transcript the question could not be read out of,
    which leaves the quote checkable for presence and not for accuracy. The
    cap is treated the other way around, because its source is a file this
    tree owns: unreadable there means a rule has gone missing, not absent.

    An opening reply owes the same shape as one that asked for it, so the two
    reach the same branch rather than two branches that could drift apart.

    `first` says the answer settles the first message typed, which is what
    excuses the quote. An opening reply is one by definition; the flag is
    carried separately for a turn that typed the command on that first message
    while the opening reach is switched off, where the question stands just as
    plainly above the answer and the exemption is owed just the same.
    """
    faults = []
    body = prose(text)

    if os.environ.get("INTELLIGENCE_ALLOW_SELFREF") != "1":
        hit = SELF_REFERENCE.search(body)
        if hit:
            faults.append('says "%s" -- narrating the session rather than '
                          "answering within it" % hit.group(0).strip())

    hit = CLOSING_OFFER.search(tail(body))
    if hit:
        faults.append('closes with "%s"' % hit.group(0).strip())

    if skill == "short" or opening:
        # A first reply stands directly under the message it answers, so the
        # question is above the answer already and quoting it writes the same
        # words twice on one page. Nothing at the top of such a reply is read as
        # the question either, which leaves it free to open on the error or the
        # paste it is about.
        if not (opening or first):
            quote = quoted_head(text)
            if quote is None:
                faults.append("does not open with the question quoted above "
                              "the answer")
            elif prompt and not echoes(quote, prompt):
                faults.append('opens by quoting "%s", which is not what was '
                              'asked' % quote.splitlines()[0][:60].strip())
        # A reach that landed on a message already answered is owed that message
        # and one sentence saying it holds nothing left. Six spent restating a
        # settled answer is the shape the rule exists to refuse, so the cap the
        # file states for the ordinary case does not apply to this one.
        if stale and cap is not None:
            cap = 1
        if cap is None:
            faults.append("no sentence cap is readable in %s, so the skill's "
                          "own promise is unenforced" % SKILL)
        else:
            n = count_sentences(body)
            if n > cap:
                faults.append("%d sentences of prose against a cap of %d"
                              % (n, cap))
    return faults


def guard_stop():
    if os.environ.get("INTELLIGENCE_REPLY_SHAPE_OFF") == "1":
        sys.exit(0)
    if _lib is None:
        sys.stderr.write("reply-shape-guard: _lib.py unavailable; standing down\n")
        sys.exit(0)
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    # A second pass means the reply has already been sent back once. A rule
    # nobody can satisfy costs one rewrite rather than a session.
    if ev.get("stop_hook_active"):
        sys.exit(0)
    path = ev.get("transcript_path")
    if not path or not Path(path).exists():
        sys.exit(0)

    rows = read_transcript(path)
    text, _ = final_reply(rows)
    if not text.strip():
        sys.exit(0)
    skill = active_skill(rows)
    first = opening_reply(rows)
    opening = (os.environ.get("INTELLIGENCE_OPENER_OFF") != "1"
               and declared_opener() and first)
    stale = declared_settled() and stale_reach(rows)
    faults = judge(text, skill, declared_cap(), governing_prompt(rows), opening,
                   first, stale)
    if not faults:
        sys.exit(0)

    # Why the shape was owed, where nobody typed the command to ask for it. A
    # refusal that only lists faults reads as the guard having broken.
    why = ""
    if opening and skill != "short":
        why = (
            "\nThis is the conversation's first reply, which takes the /short shape\n"
            "whether or not the command was typed. The question is not quoted back:\n"
            "it is the message directly above this answer. The cap is on the writing\n"
            "up and not on the work -- carry the task as far as it goes first, put the\n"
            "paths, values and commands in a table or a fence where they cost no\n"
            "sentences, and say the conclusion in six or fewer.\n"
            "INTELLIGENCE_OPENER_OFF=1 leaves this one reply unshaped.\n"
        )
    if stale:
        why += (
            "\nThe command that shaped this reply asked nothing, so what it answers is\n"
            "the last thing typed -- and that question already has an answer standing\n"
            "under it. What is owed is that message quoted and one sentence saying it\n"
            "holds nothing left to answer. The same answer written shorter is the same\n"
            "answer twice, and the second copy is read as new because nothing on the\n"
            "page says it is not.\n"
        )

    sys.stderr.write(
        "\nBLOCKED: this reply is the wrong shape.\n\n"
        + "".join(f"  {f}\n" for f in faults)
        + why
        + "\nThe answer stands without the sentences that narrate the exchange. A\n"
        "correction reads as the corrected fact in the ordinary voice; the offer to\n"
        "do more reads as the thing done, or is absent. Under /short the reply opens\n"
        "with the question quoted in the words it was asked in, then a blank line,\n"
        "then the answer -- unless the question is the first message of the session,\n"
        "which stands above the answer already and is not written out again.\n"
        "INTELLIGENCE_ALLOW_SELFREF=1 covers a reply that has to name an earlier\n"
        "statement. INTELLIGENCE_REPLY_SHAPE_OFF=1 disables this.\n"
    )
    sys.exit(2)


def measure(path):
    if _lib is None:
        print("reply-shape-guard: _lib.py unavailable; nothing measured", file=sys.stderr)
        return 1
    rows = read_transcript(path)
    text, _ = final_reply(rows)
    skill = active_skill(rows)
    cap = declared_cap()
    prompt = governing_prompt(rows)
    opening = declared_opener() and opening_reply(rows)
    stale = declared_settled() and stale_reach(rows)
    faults = judge(text, skill, cap, prompt, opening, opening, stale)
    print("skill=%s cap=%s sentences=%d quoted=%s opening=%s stale=%s "
          "turns=%d prompts=%d"
          % (skill or "-", cap if cap is not None else "-",
             count_sentences(prose(text)),
             "yes" if quoted_head(text) else "no",
             "yes" if opening else "no", "yes" if stale else "no",
             person_turns(rows), typed_prompts(rows)))
    for f in faults:
        print(f"  {f}")
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
