#!/usr/bin/env python3
"""Tracks which Markdown files have been checked against the code they describe.

The sibling of comment-pass.py, for prose instead of comments. Same verbs, same
state layout. What differs is what "unchanged" has to mean.

A comment sits in the file it describes, so that file's content hash answers the
whole question. A README does not: it makes claims about the repo around it, and
goes stale when the repo moves underneath it while the README itself sits still.
Keying a README on its own bytes alone would mean a new npm script or a new
top-level directory never reopens the page that documents them.

So a README is keyed on its own content plus a fingerprint of exactly what the
accuracy check reads: the script names in the manifest, and the shape of the
tracked tree. Change either and the page is outstanding again. Every other
Markdown file is keyed on its own content, because that is all it answers for.

The version badge is deliberately normalized out before hashing. It is derived
from the manifest and rewritten by the version bump on every PR, so leaving it
in would reopen every README on every release for a re-read that has nothing to
find.

    list    paths still needing a pass, one per line (feed this to the skill)
    status  the same thing as a human-readable summary
    mark    record a pass for the given paths, or for everything outstanding

Scoped to repos under the owner's accounts, matching comment-pass.py.
"""

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _shared():
    """The shared _lib module, loaded by path.

    Hooks and skills run this tool as a script from arbitrary directories, so
    the module is found beside this file rather than through sys.path, with
    the installed tree as the fallback for a copy executed from elsewhere.
    """
    here = Path(__file__).resolve().parent / "_lib.py"
    path = here if here.is_file() else Path.home() / ".intelligence" / "tools" / "_lib.py"
    spec = importlib.util.spec_from_file_location("intelligence_tools_lib", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_lib = _shared()

_state_root = _lib.state_root
run = _lib.run
repo_root = _lib.repo_root
origin_slug = _lib.origin_slug
is_owned = _lib.is_owned
vendored_roots = _lib.vendored_roots
is_vendored = _lib.is_vendored

STATE_DIR = _state_root() / "doc-pass"

# What a repo with no ledger on record starts from.
EMPTY_STATE = {"files": {}}

DOC_SUFFIXES = {".md", ".markdown", ".mdx"}

# Directories holding documentation nobody on this side writes or reviews.
# `published` and `archive` carry records of what was already sent or released:
# they are history, and a pass that reopens them is an invitation to rewrite it.
EXCLUDED_DIRS = {
    ".next", ".nuxt", ".svelte-kit", ".venv", "__pycache__", "archive",
    "build", "coverage", "dist", "node_modules", "out", "published",
    "target", "vendor",
}

# Verbatim legal text. It is copied from a licence, not written here, and the
# one rule that applies to it is that it stays exactly as it is.
EXCLUDED_NAMES = {"license.md", "licence.md", "copying.md"}

# The pages whose claims are about the repo rather than about themselves, and so
# reopen when the repo's shape moves. Matched on the file name, at any depth.
CLAIMS_DOCS = {"readme.md", "readme.markdown", "readme.mdx"}

# The one page every owned repo owes, at the path it owes it at.
ROOT_DOC = "README.md"

# Version badges, in the two forms the READMEs use: the shields.io path segment
# and the alt text beside it. Both carry the number, so both are normalized.
VERSION_BADGE_RE = re.compile(
    r"(badge/version-[^-?\"\s]+)|(alt=\"Version [^\"]*\")", re.IGNORECASE
)

# How deep the tree a README documents is taken to go. The project-structure
# block names top-level directories and the notable one below them; deeper than
# that is detail no page claims, and folding it in would reopen every README on
# any file added anywhere.
TREE_DEPTH = 2

# Manifests carrying the script names a README tabulates.
MANIFEST = "package.json"


def state_path(slug):
    return _lib.state_path(STATE_DIR, slug)


def load_state(slug):
    return _lib.load_state(STATE_DIR, slug, EMPTY_STATE)


def save_state(slug, state):
    _lib.save_state(STATE_DIR, slug, state)


def context(cwd=None):
    """Returns (root, slug, state) for an in-scope repo, or None to stand down."""
    return _lib.context(STATE_DIR, EMPTY_STATE, cwd)


def tracked(root):
    out = run(["git", "ls-files", "-z"], cwd=root)
    if not out:
        return []
    return [p for p in out.split("\0") if p]


def is_candidate(rel, vendored=frozenset()):
    """Whether one tracked path owes a documentation pass at all.

    A VENDOR.md subtree is a copy of someone else's documentation, kept here
    only so it can be re-copied when upstream moves. Rewriting it would be
    undone by the next update, so the whole subtree is out of scope the same
    way `vendor/` is. The marker file itself goes with it: it describes where
    the copy came from, which is a fact about upstream rather than this repo.
    """
    path = Path(rel)
    if path.suffix.lower() not in DOC_SUFFIXES:
        return False
    if path.name.lower() in EXCLUDED_NAMES:
        return False
    if is_vendored(path, vendored):
        return False
    return not EXCLUDED_DIRS.intersection(path.parts)


def candidates(root):
    paths = tracked(root)
    vendored = vendored_roots(paths)
    return sorted(
        p for p in paths if is_candidate(p, vendored) and (root / p).is_file()
    )


def claims_fingerprint(root):
    """Hashes what a README's factual claims are checked against.

    The script names and the tree shape, and nothing else. Dependency versions
    and file contents are left out on purpose: a README does not document them,
    so folding them in would reopen the page for changes it never described.
    """
    scripts = []
    manifest = root / MANIFEST
    if manifest.is_file():
        try:
            scripts = sorted((json.loads(manifest.read_text()).get("scripts") or {}))
        except (OSError, ValueError):
            scripts = []

    shape = set()
    paths = tracked(root)
    vendored = vendored_roots(paths)
    for rel in paths:
        path = Path(rel)
        if EXCLUDED_DIRS.intersection(path.parts):
            continue
        # An upstream copy reorganising itself is not a claim this repo made.
        if is_vendored(path, vendored):
            continue
        shape.add("/".join(path.parts[:TREE_DEPTH]))

    digest = hashlib.sha256()
    digest.update("\0".join(scripts).encode())
    digest.update(b"\1")
    digest.update("\0".join(sorted(shape)).encode())
    return digest.hexdigest()


def fingerprint(root, rel, claims):
    """The recorded key for one file, or None when it cannot be read."""
    try:
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    digest = hashlib.sha256()
    digest.update(VERSION_BADGE_RE.sub("", text).encode())
    if Path(rel).name.lower() in CLAIMS_DOCS:
        digest.update(b"\1")
        digest.update(claims.encode())
    return digest.hexdigest()


def fingerprints(root, paths):
    """Fingerprints working-tree content, so an uncommitted edit reopens the pass."""
    if not paths:
        return {}
    claims = claims_fingerprint(root)
    out = {}
    for rel in paths:
        key = fingerprint(root, rel, claims)
        if key:
            out[rel] = key
    return out


def outstanding(root, state):
    """Returns (paths needing a pass, whether this repo has ever been swept)."""
    paths = candidates(root)
    current = fingerprints(root, paths)
    recorded = state.get("files", {})
    stale = [p for p in paths if current.get(p) and recorded.get(p) != current[p]]
    return stale, bool(recorded)


def missing_readme(root):
    """Whether the repo has no README at its root.

    The ledger is built from the files a repo tracks, so a README that has gone
    stale is caught and a README that was never written is invisible: with
    nothing to disagree with, the pass reports the repo clean. A repo whose work
    lives in its issue tracker rather than in its files then reads as unused
    rather than as undocumented.

    There is nothing to record against this, and that is deliberate. `mark`
    cannot clear it because there is no file to hash; writing the README is what
    clears it, and the README then owes a pass like any other page.
    """
    return ROOT_DOC not in tracked(root)


def cmd_list():
    ctx = context()
    if ctx is None:
        return 0
    root, _, state = ctx
    if missing_readme(root):
        print(ROOT_DOC)
    stale, _ = outstanding(root, state)
    for path in stale:
        print(path)
    return 0


def cmd_status():
    ctx = context()
    if ctx is None:
        print("Not an owned git repo; the documentation pass does not apply here.")
        return 0
    root, slug, state = ctx
    stale, swept = outstanding(root, state)
    if missing_readme(root):
        print(f"{slug}: no {ROOT_DOC} at the repo root. Every owned repo owes one, "
              "whether or not it holds code.")
    if not stale:
        if missing_readme(root):
            return 0
        print(f"{slug}: documentation pass up to date across {len(candidates(root))} file(s).")
        return 0
    if not swept:
        print(f"{slug}: no documentation pass on record. All {len(stale)} file(s) need one.")
    else:
        print(f"{slug}: {len(stale)} file(s) changed, or describe something that changed, since their last pass.")
    for path in stale:
        print(f"  {path}")
    return 0


def cmd_mark(argv):
    ctx = context()
    if ctx is None:
        print("Not an owned git repo; nothing to record.", file=sys.stderr)
        return 0
    root, slug, state = ctx
    if argv:
        vendored = vendored_roots(tracked(root))
        paths = [
            p for p in argv
            if is_candidate(p, vendored) and (root / p).is_file()
        ]
        rejected = [p for p in argv if p not in paths]
        if rejected:
            print("Not tracked, ignored: " + ", ".join(rejected), file=sys.stderr)
    else:
        paths, _ = outstanding(root, state)
    if not paths:
        print("Nothing to record.")
        return 0

    files = state.setdefault("files", {})
    files.update(fingerprints(root, paths))
    # Drop files that have left the repo so the state does not grow forever.
    live = set(candidates(root))
    state["files"] = {p: h for p, h in files.items() if p in live}
    state.setdefault("first_pass_at", datetime.now(timezone.utc).isoformat())
    state["last_pass_at"] = datetime.now(timezone.utc).isoformat()
    save_state(slug, state)
    print(f"Recorded a documentation pass for {len(paths)} file(s) in {slug}.")
    return 0


def main():
    verbs = {
        "list": cmd_list,
        "status": cmd_status,
        "mark": lambda: cmd_mark(sys.argv[2:]),
    }
    verb = sys.argv[1] if len(sys.argv) > 1 else "status"
    handler = verbs.get(verb)
    if handler is None:
        print(f"usage: doc-pass.py [{'|'.join(verbs)}]", file=sys.stderr)
        return 2
    return handler()


if __name__ == "__main__":
    sys.exit(main())
