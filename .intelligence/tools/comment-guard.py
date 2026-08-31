#!/usr/bin/env python3
"""Refuse comments that narrate provenance or address the reader.

guard-edit   PreToolUse on Write/Edit/NotebookEdit: scans the content being written.
guard-bash   PreToolUse on Bash: scans heredoc bodies, where file content is authored.
check        Scans paths, or stdin with --stdin, outside the hook path.
restamp      Records the current wording of the source rules after they change.
"""

import ast
import hashlib
import io
import json
import os
import re
import sys
import tokenize
from pathlib import Path

HOME = Path.home()
SKILL = HOME / ".intelligence" / "skills" / "writing-comments" / "SKILL.md"
STAMP = HOME / ".intelligence" / "state" / "comment-guard-source.sha"
SECTION = "## Provenance Is Not Purpose"
ESCAPE = "INTELLIGENCE_ALLOW_COMMENT"

# Each pattern carries the rule it comes from, so a refusal quotes the standard
# rather than the guard's paraphrase of it.
PATTERNS = (
    (r"\byour?\b", "addresses the reader"),
    (r"\bI(?:'m|'ve|'ll| am| have| will| would)\b", "speaks as the author"),
    (r"\bas (?:requested|asked|discussed|agreed)\b", "phrased relative to a conversation"),
    (r"\bper (?:your|our) (?:request|conversation|discussion|rules?)\b",
     "phrased relative to a conversation"),
    (r"\bthis (?:session|conversation|chat)\b", "phrased relative to a working session"),
    (r"\bthe (?:user|conversation)\b", "phrased relative to a conversation"),
    (r"\b(?:Trenton|Claude)\b", "names a person or an agent rather than the system"),
    (r"\bused to\b", "narrates provenance"),
    (r"\b(?:previously|formerly|originally)\b", "narrates provenance"),
    (r"\bsupersed(?:e|es|ed|ing)\b", "narrates provenance"),
    (r"\bfolded in\b", "narrates provenance"),
    (r"\b(?:merged|ported) in from\b", "narrates provenance"),
    (r"\bwas (?:renamed|replaced|removed|added)\b", "narrates provenance"),
    (r"\bbelongs in\b", "instructs a person on handling rather than stating a fact"),
    (r"\bnowhere else\b", "instructs a person on handling rather than stating a fact"),
    (r"\bnever (?:in|into) (?:a|the) (?:repo|repository|commit)\b",
     "instructs a person on handling rather than stating a fact"),
    (r"\bdo not (?:commit|share|paste|copy|send)\b",
     "instructs a person on handling rather than stating a fact"),
    (r"\breplace it here\b", "instructs a person on handling rather than stating a fact"),
)
COMPILED = tuple((re.compile(p, re.I), why) for p, why in PATTERNS)

HASH_SYNTAX = {".py", ".sh", ".bash", ".zsh", ".rb", ".pl", ".yml", ".yaml",
               ".toml", ".tf", ".cfg", ".conf", ".ini", ".mk", ".dockerfile"}
SLASH_SYNTAX = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".c", ".h",
                ".cc", ".cpp", ".hpp", ".go", ".rs", ".cs", ".kt", ".kts", ".swift",
                ".php", ".scala", ".dart", ".gradle", ".groovy"}
BLOCK_ONLY = {".css", ".scss", ".less"}
DASH_SYNTAX = {".sql", ".lua", ".hs", ".elm"}

# Files whose whole content is prose written for a reader. Nothing inside one
# is a code comment, and a Markdown heading opens with the character a shell
# comment opens with, so scanning a document as shell reads every heading in it
# as a comment addressing the reader.
PROSE_SYNTAX = {".md", ".mdx", ".markdown", ".rst", ".txt", ".adoc", ".org"}

HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# The file a heredoc is redirected into, named on the same line as the opener.
# `2>&1` and the `<<` of the opener itself are excluded by the character class.
REDIRECT = re.compile(r">>?\s*([^\s;|&<>]+)")


def python_comments(text):
    """Every comment and docstring in Python source, or None if it will not parse.

    The line scanner cannot see where a string starts, only where one appears to
    end. A triple-quoted literal opened part-way along a line, the way a long
    word table is assigned to a name, is not read as opening anything, while its
    closing delimiter does start a line and is read as an opening one. The rest
    of the file is then one docstring until the next real one, so every regex and
    table between them is judged as prose -- which is how a pattern matching the
    word for the reader reads as a comment addressing the reader.

    The tokenizer knows what is a string and the syntax tree knows which strings
    are docstrings, so both questions are asked of the thing that can answer
    them. Source mid-edit often does not parse, and None hands those back to the
    scanner rather than passing them unchecked.
    """
    try:
        tree = ast.parse(text)
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (SyntaxError, ValueError, tokenize.TokenError, IndentationError):
        return None

    out = [(token.start[0], token.string.lstrip("# ").strip())
           for token in tokens if token.type == tokenize.COMMENT]

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node, clean=False)
        if not doc:
            continue
        first = node.body[0]
        line = getattr(first, "lineno", 1)
        for offset, row in enumerate(doc.split("\n")):
            out.append((line + offset, row.strip()))
    return sorted(out)


def comment_lines(text, suffix):
    """Yield (line number, comment text) for one file's worth of content.

    Docstrings count: they are documentation, and the standard covers both.
    """
    suffix = suffix.lower()
    if suffix == ".py":
        parsed = python_comments(text)
        if parsed is not None:
            return parsed
    out = []
    in_block = False
    in_doc = None
    for n, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if in_block:
            out.append((n, stripped))
            if "*/" in stripped:
                in_block = False
            continue
        if in_doc:
            out.append((n, stripped))
            if in_doc in stripped:
                in_doc = None
            continue
        if suffix in HASH_SYNTAX or suffix == "":
            if stripped.startswith("#") and not stripped.startswith("#!"):
                out.append((n, stripped.lstrip("# ")))
                continue
        if suffix == ".py":
            for quote in ('"""', "'''"):
                if stripped.startswith(quote):
                    body = stripped[3:]
                    if quote not in body:
                        in_doc = quote
                    out.append((n, body))
                    break
        if suffix in SLASH_SYNTAX:
            if stripped.startswith("//"):
                out.append((n, stripped.lstrip("/ ")))
                continue
        if suffix in SLASH_SYNTAX or suffix in BLOCK_ONLY:
            if stripped.startswith("/*"):
                out.append((n, stripped.lstrip("/* ")))
                if "*/" not in stripped[2:]:
                    in_block = True
                continue
        if suffix in DASH_SYNTAX and stripped.startswith("--"):
            out.append((n, stripped.lstrip("- ")))
    return out


def heredoc_blocks(command):
    """Yield (target, [(line number, line), ...]) for each heredoc in a command.

    The target is the file the body is redirected into, and None when the
    command names none.
    """
    lines = command.split("\n")
    out = []
    n = 0
    while n < len(lines):
        found = HEREDOC.search(lines[n])
        if not found:
            n += 1
            continue
        redirect = REDIRECT.search(lines[n])
        target = redirect.group(1).strip("\"'") if redirect else None
        terminator = found.group(2)
        block = []
        n += 1
        while n < len(lines) and lines[n].strip() != terminator:
            block.append((n + 1, lines[n]))
            n += 1
        n += 1
        out.append((target, block))
    return out


def heredoc_bodies(command):
    """Yield (line number, line) for every line inside a heredoc in a shell command."""
    return [pair for _, block in heredoc_blocks(command) for pair in block]


def prose_target(target):
    """True when a heredoc writes a file whose content is prose rather than code."""
    return bool(target) and Path(target).suffix.lower() in PROSE_SYNTAX


def findings(pairs):
    hits = []
    for n, text in pairs:
        if not text:
            continue
        for pattern, why in COMPILED:
            found = pattern.search(text)
            if found:
                hits.append((n, found.group(0), why, text.strip()[:100]))
                break
    return hits


def source_drifted():
    """True when the section the patterns were derived from no longer matches its stamp."""
    if not SKILL.exists():
        return False
    body = SKILL.read_text(errors="replace")
    if SECTION not in body:
        return True
    section = body.split(SECTION, 1)[1].split("\n## ", 1)[0]
    digest = hashlib.sha256(section.encode()).hexdigest()
    if not STAMP.exists():
        STAMP.parent.mkdir(parents=True, exist_ok=True)
        STAMP.write_text(digest)
        return False
    return STAMP.read_text().strip() != digest


def refuse(where, hits):
    lines = [
        "BLOCKED: %s carries comments the writing-comments standard rejects." % where,
        "",
    ]
    for n, phrase, why, text in hits[:8]:
        lines.append('  line %d: "%s" — %s' % (n, phrase, why))
        lines.append("    %s" % text)
    lines += [
        "",
        "A comment states what the system is, in the present tense. The test the",
        "standard sets: the comment would not exist if the code had always been",
        "this way. Rewrite the design rationale as a fact and delete the history;",
        "delete the comment outright when the structure already says it.",
        "",
        "%s=1 overrides this for a comment the guard has misread." % ESCAPE,
    ]
    print("\n".join(lines), file=sys.stderr)
    return 2


def drift_refusal():
    print(
        "BLOCKED: %s changed since comment-guard.py's patterns were derived from it.\n"
        "\n"
        "Reread that section, bring PATTERNS in ~/.intelligence/tools/comment-guard.py into\n"
        "step with it, then record the new wording:\n"
        "  ~/.intelligence/tools/comment-guard.py restamp\n" % SECTION,
        file=sys.stderr,
    )
    return 2


def cmd_guard_edit(argv):
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if os.environ.get(ESCAPE):
        return 0
    if source_drifted():
        return drift_refusal()
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    content = tool_input.get("content") or tool_input.get("new_string") or ""
    if not content:
        return 0
    hits = findings(comment_lines(content, Path(path).suffix))
    return refuse(path or "this edit", hits) if hits else 0


def cmd_guard_bash(argv):
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if os.environ.get(ESCAPE):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0
    if source_drifted():
        return drift_refusal()
    body = [pair for target, block in heredoc_blocks(command)
            if not prose_target(target) for pair in block]
    if not body:
        return 0
    text = "\n".join(line for _, line in body)
    pairs = []
    for suffix in (".sh", ".js", ".py"):
        pairs += comment_lines(text, suffix)
    hits = findings(sorted(set(pairs)))
    return refuse("this heredoc", hits) if hits else 0


def cmd_check(argv):
    if argv and argv[0] == "--stdin":
        text = sys.stdin.read()
        suffix = argv[1] if len(argv) > 1 else ".sh"
        hits = findings(comment_lines(text, suffix))
        return refuse("stdin", hits) if hits else 0
    bad = 0
    for name in argv:
        path = Path(name)
        if not path.is_file():
            continue
        hits = findings(comment_lines(path.read_text(errors="replace"), path.suffix))
        if hits:
            bad = refuse(str(path), hits)
    if not bad:
        print("clean")
    return bad


def cmd_restamp(argv):
    if not SKILL.exists():
        print("no %s to stamp" % SKILL, file=sys.stderr)
        return 2
    section = SKILL.read_text(errors="replace").split(SECTION, 1)[1].split("\n## ", 1)[0]
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text(hashlib.sha256(section.encode()).hexdigest())
    print("stamped %s" % SECTION)
    return 0


COMMANDS = {
    "guard-edit": cmd_guard_edit,
    "guard-bash": cmd_guard_bash,
    "check": cmd_check,
    "restamp": cmd_restamp,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
