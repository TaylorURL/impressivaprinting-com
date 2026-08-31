# Vendored

This directory is an installed copy of `bradley-t-t/intelligence`, which is where
the skills, tools, and hooks are written and maintained. It is checked in so a
session on this repo has the working setup without a machine-level install — which
is the only way a Claude Code session on the web gets it at all, since a cloud
container starts with the repository and nothing else.

Do not edit anything under here to change how a skill behaves. The edit belongs in
`intelligence`, and `config-sync.py` carries it between machines; a fix made here
is one that gets overwritten the next time the copy is refreshed.

Refresh every repo that carries a copy:

    ~/.intelligence/tools/vendor-intelligence.py sweep

Or just this one:

    ~/.intelligence/tools/vendor-intelligence.py install .

The refresh leaves out what belongs to the machine rather than to this repo:
another project's hooks, the personal config and ledger sync that reach private
repositories, and the skills that act outside the repository they would ship in.
`vendor-intelligence.py` holds that list, so the exclusion survives a refresh instead of
having to be remembered.

The comment, documentation, and writing passes skip this subtree, for the same
reason they skip any vendored directory: the text answers to its own repo.
