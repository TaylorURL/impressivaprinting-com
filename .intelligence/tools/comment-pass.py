#!/usr/bin/env python3
"""Tracks which files have had a comment pass, keyed on their content.

The writing-comments skill only helps if it actually runs. Relying on a rule in
INTELLIGENCE.md means it runs when the model remembers, which is not the same as every
time. This records the pass per file, keyed by content, so the landing skills
ask the ledger what is outstanding instead of recalling it.

Keying on content hash rather than a timestamp is what makes the "once, then only
changes" behavior fall out on its own: a file whose recorded hash still matches
its working-tree content has already been through the pass and stays out of the
way. An empty state means nothing has been swept, so every code file is
outstanding, which is the initial full-codebase sweep.

    list    paths still needing a pass, one per line (feed this to the skill)
    status  the same thing as a human-readable summary
    mark    record a pass for the given paths, or for everything outstanding

Scoped to repos under the owner's accounts, matching git-develop-base-guard.sh.
A cloned third-party repo is not part of this workflow and is left alone.
"""

import importlib.util
import re
import subprocess
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

STATE_DIR = _state_root() / "comment-pass"

# What a repo with no ledger on record starts from.
EMPTY_STATE = {"files": {}}

# Extensions whose comment syntax the writing-comments skill covers. Data and
# markup formats are deliberately absent: a pass over them has nothing to judge.
CODE_SUFFIXES = {
    ".bash", ".c", ".cc", ".cjs", ".cpp", ".cs", ".css", ".go", ".gradle",
    ".h", ".hpp", ".java", ".js", ".jsx", ".kt", ".kts", ".less", ".lua",
    ".mjs", ".php", ".py", ".rb", ".rs", ".scss", ".sh", ".sql", ".svelte",
    ".swift", ".ts", ".tsx", ".vue", ".zsh",
}

# Markup that earns a pass only by what it carries. A page is mostly tags, and
# sweeping every one of them in would bury the outstanding list in files with
# nothing to judge — but a single-file app keeps its whole frontend inside a
# <script>, and going by extension alone leaves that code permanently unswept
# while the summary still reads "up to date".
MARKUP_SUFFIXES = {".htm", ".html", ".xhtml"}

# Non-whitespace characters of inline script or style a page needs before it
# counts as code. An analytics snippet or a boot line falls under; a frontend
# does not.
EMBEDDED_CODE_MIN = 1000

# Inline <script>/<style> bodies. A src/href-only tag has no body to match, so
# a page that merely loads its code stays markup.
EMBEDDED_CODE_RE = re.compile(
    r"<(script|style)\b[^>]*>(.*?)</\1\s*>", re.DOTALL | re.IGNORECASE
)

# Directories holding code nobody on this side writes or reviews.
EXCLUDED_DIRS = {
    ".next", ".nuxt", ".svelte-kit", ".venv", "__pycache__", "build",
    "coverage", "dist", "node_modules", "out", "target", "vendor",
}

# Generated or minified output that happens to carry a source extension.
EXCLUDED_MARKERS = (".min.", ".generated.", ".pb.", "_pb2.", ".g.")


def state_path(slug):
    return _lib.state_path(STATE_DIR, slug)


def load_state(slug):
    return _lib.load_state(STATE_DIR, slug, EMPTY_STATE)


def save_state(slug, state):
    _lib.save_state(STATE_DIR, slug, state)


def context(cwd=None):
    """Returns (root, slug, state) for an in-scope repo, or None to stand down."""
    return _lib.context(STATE_DIR, EMPTY_STATE, cwd)


def embeds_code(path):
    """Whether a markup file carries enough inline script or style to review."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    total = 0
    for _, body in EMBEDDED_CODE_RE.findall(text):
        total += len("".join(body.split()))
        if total >= EMBEDDED_CODE_MIN:
            return True
    return False


def tracked(root):
    out = run(["git", "ls-files", "-z"], cwd=root)
    return [p for p in out.split("\0") if p] if out else []


def is_candidate(root, rel, vendored=frozenset()):
    """Whether one tracked path owes a comment pass at all.

    A VENDOR.md subtree is a copy of someone else's code, kept here only so it
    can be re-copied when upstream moves. Rewriting its comments would be
    overwritten by the next update and would make the diff against upstream
    unreadable, so the whole subtree is out of scope the same way `vendor/` is.
    """
    path = Path(rel)
    suffix = path.suffix.lower()
    if suffix not in CODE_SUFFIXES and suffix not in MARKUP_SUFFIXES:
        return False
    if EXCLUDED_DIRS.intersection(path.parts):
        return False
    if is_vendored(path, vendored):
        return False
    if any(marker in path.name for marker in EXCLUDED_MARKERS):
        return False
    return suffix not in MARKUP_SUFFIXES or embeds_code(root / rel)


def candidates(root):
    paths = tracked(root)
    vendored = vendored_roots(paths)
    return sorted(
        p for p in paths
        if is_candidate(root, p, vendored) and (root / p).is_file()
    )


def hash_paths(root, paths):
    """Hashes working-tree content, so an uncommitted edit reopens the pass."""
    if not paths:
        return {}
    done = subprocess.run(
        ["git", "hash-object", "--stdin-paths"],
        cwd=root, input="\n".join(paths) + "\n",
        capture_output=True, text=True, check=False,
    )
    if done.returncode != 0:
        return {}
    lines = [line for line in done.stdout.splitlines() if line]
    if len(lines) != len(paths):
        return {}
    return dict(zip(paths, lines))


def outstanding(root, state):
    """Returns (paths needing a pass, whether this repo has ever been swept)."""
    paths = candidates(root)
    current = hash_paths(root, paths)
    recorded = state.get("files", {})
    stale = [p for p in paths if current.get(p) and recorded.get(p) != current[p]]
    return stale, bool(recorded)


def cmd_list():
    ctx = context()
    if ctx is None:
        return 0
    root, _, state = ctx
    stale, _ = outstanding(root, state)
    for path in stale:
        print(path)
    return 0


def cmd_status():
    ctx = context()
    if ctx is None:
        print("Not an owned git repo; the comment pass does not apply here.")
        return 0
    root, slug, state = ctx
    stale, swept = outstanding(root, state)
    if not stale:
        print(f"{slug}: comment pass up to date across {len(candidates(root))} files.")
        return 0
    if not swept:
        print(f"{slug}: no comment pass on record. All {len(stale)} code files need one.")
    else:
        print(f"{slug}: {len(stale)} file(s) changed since their last comment pass.")
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
            if is_candidate(root, p, vendored) and (root / p).is_file()
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
    files.update(hash_paths(root, paths))
    # Drop files that have left the repo so the state does not grow forever.
    live = set(candidates(root))
    state["files"] = {p: h for p, h in files.items() if p in live}
    state.setdefault("first_pass_at", datetime.now(timezone.utc).isoformat())
    state["last_pass_at"] = datetime.now(timezone.utc).isoformat()
    save_state(slug, state)
    print(f"Recorded a comment pass for {len(paths)} file(s) in {slug}.")
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    if mode == "list":
        return cmd_list()
    if mode == "status":
        return cmd_status()
    if mode == "mark":
        return cmd_mark(sys.argv[2:])
    print(__doc__, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
