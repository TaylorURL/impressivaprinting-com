#!/usr/bin/env python3
"""Cases for plain-brief-guard.py.

Two directions, both of which have to hold: an answer written in the vocabulary
of the work is refused, and every other reply is left alone. The second is the
half that decides whether the gate survives -- a guard that refuses ordinary
working replies gets switched off, and then the rule it was built for is
unenforced again with nothing saying so.

Two turns owe the plain answer, so both are fixed here. The explanation is
weighed whole. A /short answer is weighed over its prose alone, since that skill
puts the quoted question and every table, list and fence under it outside the
argument, and a gate reading those as prose would refuse the concrete evidence
the skill asks for.
"""
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "plain-brief-guard.py"

spec = importlib.util.spec_from_loader(
    "plain_brief_guard",
    importlib.machinery.SourceFileLoader("plain_brief_guard", str(TOOL)),
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

failures = []


def case(name, question, reply, refused, skill=None):
    """One reply against one question, and whether the gate should refuse it."""
    applies, found = guard.judge(question, reply, skill)
    blocked = applies and len(found) > guard.BUDGET
    if blocked != refused:
        want = "refused" if refused else "allowed"
        got = "refused" if blocked else "allowed"
        terms = ", ".join(term for _, term in found) or "none"
        failures.append(f"{name}: wanted {want}, got {got} (applies={applies}, found: {terms})")


# The shape the rule was written for: a request to explain, answered in paths
# and commands.
case(
    "explanation in machinery",
    "I misclicked explain what is going on in English",
    "The bio change is on the email-bio branch. I ran /commit which bumped "
    "package.json, then rebased onto origin/develop. The wording lives in "
    "lib/mail/bio.js and src/app/views/Contact.jsx reads it.",
    refused=True,
)

case(
    "same question answered plainly",
    "explain what is going on",
    "Your site still shows the old wording. The new version is finished but not "
    "published yet. Two images are already on the server, pointed at by nothing. "
    "Do you want it published now, or held until the signup change is done?",
    refused=False,
)

case(
    "status question in machinery",
    "where are we",
    "Four commits sit ahead of origin/develop, HEAD is at the version bump, and "
    "scripts/check-email-bio.js passes. The worktree is clean.",
    refused=True,
)

# An ordinary working turn. Naming files here is the job, and a gate that
# refuses this is a gate that gets removed.
case(
    "ordinary work naming files",
    "fix the failing check",
    "The failure was in scripts/check-email-bio.js: the fixture had an empty "
    "work list, so lib/outreach/message.js never drew the previews. "
    "src/app/data/portfolio.js now exports the email variant.",
    refused=False,
)

case(
    "a direct request for the path",
    "which file holds the bio wording",
    "lib/mail/bio.js holds it, and src/app/views/Contact.jsx reads from it.",
    refused=False,
)

# One or two mentions inside a brief is the subject being identified, not the
# reply retreating into machinery.
case(
    "brief naming one thing",
    "explain what is going on",
    "Nothing is published yet. The wording lives in one place now, lib/mail/bio.js, "
    "so the site and the emails cannot drift apart. Do you want it live?",
    refused=False,
)

case(
    "plain english request answered in commands",
    "put that in plain english",
    "I ran /merge to promote develop, then /live confirmed the deploy. "
    "A rebase moved the worktree onto origin/main and auto-merge landed it.",
    refused=True,
)

# Code blocks are the source's words rather than the writer's: a command the
# reader was given to run is not the reply hiding behind jargon.
case(
    "fenced command in a brief",
    "explain what is going on",
    "Nothing is live yet. To publish it yourself:\n\n```bash\nnpm run deploy\n```\n\n"
    "Everything else is waiting on your call about the signup email.",
    refused=False,
)

# The trigger is the question. A reply nobody asked to have explained is out of
# scope however it is written.
case(
    "no explanation asked for",
    "ship it",
    "Done. Rebased onto origin/develop, squashed, and /merge promoted it. "
    "scripts/check-email-bio.js and lib/mail/bio.js both landed.",
    refused=False,
)

# The /short turn. The trigger is the skill, so the question decides nothing
# about whether the rule applies -- only about which words are already the
# reader's.
case(
    "short answer in machinery",
    "did the wording change land",
    "> did the wording change land\n\n"
    "It landed on origin/develop, and lib/mail/bio.js carries it. "
    "The deploy ran after /merge squashed it.",
    refused=True,
    skill="short",
)

case(
    "short answer in english",
    "did the wording change land",
    "> did the wording change land\n\n"
    "Yes. The site and the emails both read the new wording, and they now take "
    "it from one place, so they cannot drift apart again.",
    refused=False,
    skill="short",
)

# The evidence is where exact things belong. A gate that charged for them would
# push the answer into vagueness to stay inside the rule.
case(
    "short answer keeping its machinery in the evidence",
    "did the wording change land",
    "> did the wording change land\n\n"
    "Yes, and the site and the emails now read it from one place.\n\n"
    "| what | where |\n|---|---|\n| the wording | lib/mail/bio.js |\n"
    "| the page that shows it | src/app/views/Contact.jsx |\n\n"
    "- scripts/check-email-bio.js passes\n"
    "- origin/develop carries it\n\n"
    "```bash\nnpm run deploy\n```\n",
    refused=False,
    skill="short",
)

# The quote at the top is the person's own words, and charging the answer for
# them refuses a reply for quoting the question it was told to quote.
case(
    "short answer quoting a question full of machinery",
    "did lib/mail/bio.js land on origin/develop after /merge ran",
    "> did lib/mail/bio.js land on origin/develop after /merge ran\n\n"
    "Yes, an hour ago. Nothing is published yet, so the site still shows the "
    "old wording.",
    refused=False,
    skill="short",
)

case(
    "short answer naming what the question named",
    "which file holds the bio wording and does src/app/views/Contact.jsx read it",
    "> which file holds the bio wording and does src/app/views/Contact.jsx read it\n\n"
    "lib/mail/bio.js holds it, and yes, src/app/views/Contact.jsx reads from "
    "it rather than keeping its own copy.",
    refused=False,
    skill="short",
)

# Another skill's turn is out of scope however it is written, the same way an
# ordinary turn is.
case(
    "another skill naming files",
    "get this live",
    "The deploy is out. lib/mail/bio.js, src/app/views/Contact.jsx and "
    "scripts/check-email-bio.js all landed on origin/develop.",
    refused=False,
    skill="ship",
)


if failures:
    print("plain-brief-guard: FAILED")
    for failure in failures:
        print(f"  {failure}")
    sys.exit(1)

print("plain-brief-guard: 15 cases pass")
