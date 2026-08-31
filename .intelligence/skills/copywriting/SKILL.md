---
name: copywriting
description: Write, rewrite or improve marketing copy for any page - homepage, landing, pricing, feature, about, product - and hold it to the avoid-ai-writing standard before it ships. Use on /copywriting, or "write copy for", "improve this copy", "rewrite this page", "marketing copy", "headline help", "CTA copy", "this reads like AI".
---

# Copywriting

One skill with two halves. The first draws the copy: what the page argues, in
what order, under what headline. The second is the avoid-ai-writing standard,
which decides whether the sentences are allowed to ship. Neither half is
optional and the second one runs last, because a draft that reads well and
scores badly is still not going on a page.

The drafting half is adapted from an upstream skill, kept under `vendor/` and
read rather than invoked. Where the two disagree, this file wins and the
disagreement is written down under "Where upstream is overruled" instead of
being quietly reconciled.

## Before writing

Read the project's own marketing and brand documentation first, then ask only
for what it does not answer. A project that has written this down keeps it at
`docs/product-marketing-context.md`; one that has not is worth starting there
rather than answering the same questions on every page.

- **The page.** Which type, and the one action a visitor should take.
- **The audience.** Who they are, the problem they arrived with, the objection
  that stops them, and the words they use for all three.
- **The offer.** What is being sold, what makes it different, the outcome, and
  any number or quote that can be proved.
- **The traffic.** Where visitors come from and what they already know.

Voice-of-customer beats invention. Reviews, support tickets and sales call
notes carry the phrasing to reuse; a headline written in the company's words
about the customer's problem is the common failure.

## The rules that decide a line

1. **Clear over clever.** When the two compete, clear wins outright.
2. **Specific over vague.** "Cut weekly reporting from four hours to fifteen
   minutes", not "save time on your workflow".
3. **Benefit over feature.** The feature is what it does; the benefit is what
   that means for the person reading.
4. **Their words over ours.** Mirror the customer's vocabulary, not the
   company's.
5. **One idea per section.** Each block advances one argument, and the blocks
   in order make a case.
6. **Plain over inflated.** "Use" not "utilize", "help" not "facilitate".
7. **Active over passive.** "We generate reports", not "reports are generated".
8. **Confident over qualified.** Cut "almost", "very", "really", "quite".
9. **Honest over sensational.** Never invent a statistic, a testimonial or a
   customer. A number that cannot be sourced does not go on the page.
10. **No exclamation points.** None.

## Page structure

Above the fold: headline, subheadline of one or two sentences that adds
specificity, and one primary call to action. Everything else supports those
three.

| Section | What it does |
|---|---|
| Social proof | Logos, a metric, a rating - credibility before the argument |
| Problem | Describe their situation well enough that they recognise it |
| Solution | Three to five benefits tied to outcomes, not ten |
| How it works | Three or four steps, to cut the sense of difficulty |
| Objections | FAQ, comparison, guarantee |
| Final CTA | Restate the value, repeat the action, reverse the risk |

A hero, four product blurbs and a button is a list, not an argument. The
section inventory and the page templates worth copying are in
[vendor/references/copy-frameworks.md](vendor/references/copy-frameworks.md),
which also holds the headline formulas - outcome, problem, audience,
differentiation and proof shaped. Point at that file rather than restating it.

## CTAs

Formula: action verb, then the thing they get, then a qualifier if one is
needed.

Weak: Submit. Sign Up. Learn More. Click Here. Get Started.
Better: Start My Free Trial. Get the Complete Checklist. See Pricing for My Team.

A button that says what happens next beats a button that says what the visitor
must do.

## By page type

- **Homepage.** Several audiences at once without going generic. Lead with the
  broadest true claim, then split the paths by intent.
- **Landing page.** One message, one action, argument complete on the page, and
  the headline matching whatever ad or email sent them.
- **Pricing.** The visitor is asking which plan is theirs. Answer that, make the
  recommended one obvious, and handle the anxiety rather than the arithmetic.
- **Feature page.** Feature to benefit to outcome, with a use case that shows
  it, and a way to try it.
- **About.** Why the company exists, connected to why that helps the reader. It
  still needs a call to action.

## Where upstream is overruled

Three of upstream's recommendations are patterns the standard removes. The
resolutions are settled and are not to be re-litigated per project.

- **Rhetorical questions.** Upstream recommends them generally. They are kept
  as headlines, where the question is the hook and the page answers it
  immediately. They are dropped as section transitions, which is the case the
  standard flags: a question that stalls in front of a point already known.
- **Transition phrases.** `vendor/references/natural-transitions.md` is
  superseded whole and is not to be read for guidance. Its recommended openers
  include "When it comes to", "That said", "Let's break this down step by step",
  "Research shows" and "experts believe", each on the standard's removal list.
  Use the standard's own transitions section instead.
- **Sibling skills.** Upstream closes by naming copy-editing, page-cro,
  email-sequence, popup-cro and ab-test-setup. None is installed here. Editing
  is the closing gate below; page structure is this file.

## The closing gate

The draft is not finished when it reads well. It is finished when it scores
clean, and that is not on trust: invoking this skill arms a gate. Every text
file written from that moment is recorded, and the session cannot end while any
of them, or the reply carrying the copy, still scores blocked.

Run the standard at `~/.intelligence/standards/avoid-ai-writing` over the copy
in rewrite mode, fix what it flags, then verify before the stop rather than
finding out at it:

```bash
~/.intelligence/tools/writing-pass.py check <the files the copy landed in>
```

Copy that has not been written to a file yet goes through the same check on
standard input:

```bash
pbpaste | ~/.intelligence/tools/writing-pass.py check --stdin
```

A non-zero exit means the copy is blocked and the work is not done. Fix the
named phrase rather than arguing with the category. A flag that is right anyway
- a literal word the product actually uses - is retired with `writing-pass.py
allow`, which takes a reason and records it against that one phrase in that one
file. `INTELLIGENCE_ALLOW_COPY=1` stands the gate down for a session that wrote
no copy the gate should hold.

The gate scores the current text every time it runs and keeps no record of a
verdict, so rewriting the copy is the only thing that opens it. The rhythm and
punctuation measures are reported and never block: they describe a voice rather
than a defect, so read them and move on.

## Output

Copy organised by section, in the order it appears on the page: headline,
subheadline, primary CTA, then each section's header and body.

Two or three options for the headline and the primary CTA, each with the reason
it might be the one. One line per option, no essay.

Page title and meta description when the page is public.

Say which of the rules above drove any choice that looks odd. Skip the
annotation everywhere else; a rationale under every line is noise.
