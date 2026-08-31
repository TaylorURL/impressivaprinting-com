# Vendored: the copywriting skill

`SKILL.md` and everything under `references/` are upstream's files, taken from
`boraoztunc/skills` at `645553c`, path `copywriting`, version 1.0.0 by its own
frontmatter. Do not hand-edit them: a local change is lost the next time the
skill is replaced, and it makes the diff against upstream unreadable. That is
also why the comment, documentation, and writing ledgers skip any directory
carrying this marker.

The skill that actually runs is `../SKILL.md`, which is ours. Upstream sits
underneath it as source material rather than as the thing invoked, because the
two disagree and the disagreements are not editorial. Upstream writes marketing
copy and stops there; it has no opinion about the sentence-level tells the
writing pass gates on, and three of its recommendations are the tells:

- `references/natural-transitions.md` teaches openers the avoid-ai-writing
  standard removes on sight. Superseded whole; do not read it for guidance.
- `SKILL.md` recommends rhetorical questions as section transitions, which the
  standard flags. Ours keeps the headline case and drops the transition case.
- `SKILL.md` names sibling skills from its own repo that are not installed here.

`references/copy-frameworks.md` is the part that survives contact with the
standard: it scores clean, and its headline formulas and section inventory are
what ours points at rather than restating.

To update: replace the three files with the new upstream release, leave this
marker, re-run `writing-pass.py check` over them to see what the new version
brought in, and record any new disagreement in the list above. Then
`config-sync.py check`.
