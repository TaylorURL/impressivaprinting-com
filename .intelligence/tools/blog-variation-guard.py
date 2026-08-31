#!/usr/bin/env python3
"""Refuses an article that is already on the blog, before it reaches a file.

The blog is written by a scheduled routine reading a file of standing
instructions and the articles beside it, which is the setup that drifts into
rewriting a published piece with different nouns. Two pages saying the same
thing cost an index slot rather than filling one, so the draft has to be
stopped at the edit rather than found in review.

The measure lives with the articles, at `scripts/blog-variation.js` in the
repository, because the article format is the repository's and its continuous
integration runs the same command over the whole blog. This is the other door
onto it: a `PreToolUse` hook that reconstructs the file the edit would leave
behind, hands it over as a candidate, and refuses the call when the checker
reports a collision.

Fail closed. A checker that cannot be run, or that runs without reaching a
verdict, refuses the edit, since an unchecked article is the state this exists
to keep off the blog -- and so does a checker gone missing from a project whose
manifest still calls for it, so removing the file to get past a refusal refuses
every later edit instead. A project that never declared the check has nothing
to enforce and is left alone, which is what keeps a checkout cut before the
check existed from having its whole blog frozen.

  guard-edit   PreToolUse. Deny a blog edit whose article is already published.

INTELLIGENCE_ALLOW_BLOG_DUPLICATE=1 lifts it for an edit the checker has
misread.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BLOG_DIR = "src/app/data/blog/"
CHECKER = "scripts/blog-variation.js"
TIMEOUT_SECONDS = 90


def deny(reason, detail=""):
    sys.stderr.write(f"BLOCKED: {reason}\n")
    if detail:
        sys.stderr.write(f"\n{detail.rstrip()}\n")
    sys.stderr.write(
        "\nAn article too close to a published one takes the slot the published\n"
        "one holds instead of adding a slot. Write the piece the blog does not\n"
        "have yet, or fold the new material into the article it repeats.\n"
        f"The whole blog is measured by: node {CHECKER}\n"
    )
    sys.exit(2)


def blog_file(path):
    """Whether a path is one of the article data files."""
    spelled = str(path).replace("\\", "/")
    return BLOG_DIR in spelled and spelled.endswith(".js")


def proposed(tool, tool_input, path):
    """The file the edit would leave behind, or None when it would not apply.

    An edit whose anchor is not in the file fails on its own terms, and judging
    a reconstruction that never happens would refuse an article over text that
    was never written.
    """
    if tool == "Write":
        return str(tool_input.get("content") or "")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""

    edits = tool_input.get("edits")
    if not isinstance(edits, list):
        edits = [tool_input]
    for edit in edits:
        old = str(edit.get("old_string") or "")
        new = str(edit.get("new_string") or "")
        if not old:
            text = new
            continue
        if old not in text:
            return None
        text = text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)
    return text


def repo_of(path):
    """The project the file belongs to, by the manifest above it."""
    for parent in path.resolve().parents:
        if (parent / "package.json").is_file():
            return parent
    return None


def declares_check(root):
    """Whether the project's manifest calls for the measure.

    A project that names it in a script has one and is missing it; a project
    that never named it has nothing this guard can hold it to.
    """
    try:
        scripts = json.loads((root / "package.json").read_text(encoding="utf-8")).get("scripts")
    except (OSError, ValueError, AttributeError):
        return False
    if not isinstance(scripts, dict):
        return False
    return any("blog-variation" in str(value) for value in scripts.values())


def verdict(root, candidate, target):
    argv = ["node", str(root / CHECKER), "--candidate", str(candidate),
            "--as", str(target), "--json"]
    try:
        run = subprocess.run(argv, cwd=str(root), capture_output=True, text=True,
                             timeout=TIMEOUT_SECONDS)
    except FileNotFoundError:
        deny("node is not on the path, so the article could not be measured "
             "against the blog")
    except subprocess.TimeoutExpired:
        deny(f"measuring the article against the blog did not finish in "
             f"{TIMEOUT_SECONDS}s")
    if run.returncode == 0:
        return
    try:
        report = json.loads(run.stdout or "{}")
    except ValueError:
        report = {}
    hits = report.get("collisions") or []
    if not hits:
        deny("the article could not be measured against the blog",
             (run.stderr or run.stdout or "").strip())
    lines = []
    for hit in hits:
        lines.append(
            "  %s repeats %s (%s): %.3f of its five-word phrases, bar %.3f"
            % (hit.get("draft"), hit.get("against"), hit.get("where"),
               hit.get("score", 0), report.get("bar", 0))
        )
        for run_text in hit.get("lifted") or []:
            lines.append(f'    already written: "{run_text}"')
    deny("this article is already on the blog", "\n".join(lines))


def guard_edit():
    if os.environ.get("INTELLIGENCE_ALLOW_BLOG_DUPLICATE") == "1":
        return
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return
    tool = payload.get("tool_name") or ""
    if tool not in ("Write", "Edit", "MultiEdit"):
        return
    tool_input = payload.get("tool_input") or {}
    target = str(tool_input.get("file_path") or "")
    if not target or not blog_file(target):
        return

    path = Path(target)
    root = repo_of(path)
    if root is None:
        return
    if not (root / CHECKER).is_file():
        if declares_check(root):
            deny(f"{root.name} calls for {CHECKER} and does not have it, so "
                 "the article could not be measured against the blog")
        return

    content = proposed(tool, tool_input, path)
    if content is None:
        return

    handle = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8")
    try:
        handle.write(content)
        handle.close()
        verdict(root, Path(handle.name), path)
    finally:
        os.unlink(handle.name)


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "guard-edit":
        guard_edit()
        return
    sys.stderr.write(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    main()
