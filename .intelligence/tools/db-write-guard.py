#!/usr/bin/env python3
"""The database is read-only until one named object is approved.

Reading is the job: rows, plans, logs, advisors, schema listings. A statement
that changes structure or data is one object approved at a time, and approval
for one is not approval for the next.

The same rule covers the two shell doors that reach past a review: merging a
pull request with administrator rights, and editing or removing branch
protection. Both land changes no check has seen.

  guard-mcp    a database tool call that writes
  guard-bash   a shell command that overrides a review

INTELLIGENCE_DB_WRITE=<project ref>:<object> approves that one object.
"""
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

# The segment splitter and the reading-tool filter are one implementation, held
# by the guard that first needed them. A search naming a write verb is a
# reading on every surface, and two answers to that would drift apart.
_spec = importlib.util.spec_from_file_location(
    "stripe_guard", str(Path(__file__).resolve().parent / "stripe-guard.py"))
_shell = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shell)
acting_segments = _shell.acting_segments

# The tool names that change something, matched on the suffix because a server
# prefixes its own identity onto every name it publishes.
MCP_WRITE = re.compile(
    r"(?:^|__)(apply_migration|execute_sql|deploy_edge_function|pause_project|"
    r"restore_project|delete_branch|merge_branch|reset_branch|create_branch)$")

# Two servers publish pause_project: Supabase pauses a database, Vercel pauses a
# deployment. Only the first is this guard's business, and the name alone cannot
# tell them apart. Every Vercel call carries a teamId, which no Supabase tool
# takes, so the argument shape separates them without pinning a server id that
# differs per install. Judging a deployment as a database write was worse than
# noise: `named()` reads snake_case keys and a 20-letter reference, so a Vercel
# call offered no token an approval could bind to and no value of
# INTELLIGENCE_DB_WRITE could ever clear it.
HOSTING_CALL = re.compile(r'"teamId"\s*:')

# execute_sql carries either kind, so it is judged by the statement rather than
# by its name.
BY_STATEMENT = re.compile(r"(?:^|__)execute_sql$")

# A statement that only reads. Anything not matching is treated as a write,
# because a guard that guesses in the other direction is worth nothing.
READ_SHAPED = re.compile(
    r"^\s*(?:select|with\b[\s\S]*?\bselect|explain|show|table|values)\b", re.I)

# Writes spelled as a shell command rather than a tool call.
CLI_WRITE = re.compile(
    r"\bsupabase\s+(?:db\s+(?:push|reset|dump)|migration\s+(?:up|repair))\b", re.I)

# Landing without the review the branch requires.
ADMIN_MERGE = re.compile(r"\bgh\s+pr\s+merge\b[^\n]*--admin\b", re.I)
PROTECTION_EDIT = re.compile(
    r"\bgh\s+api\b[^\n]*-X\s*(?:DELETE|PUT|PATCH)\b[^\n]*/branches/[^\s]+/protection",
    re.I)

# A project reference, which is what an approval has to name.
PROJECT_REF = re.compile(r"\b[a-z]{20}\b")


def payload():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def approved():
    """Each approval as a project reference and the one object it opens.

    The reference alone is never an approval. A door opened for one migration
    is not a door opened for the next one against the same project, which is
    the whole distinction the rule is made of.
    """
    out = set()
    for part in (os.environ.get("INTELLIGENCE_DB_WRITE") or "").split(","):
        part = part.strip()
        if not part:
            continue
        ref, _, obj = part.rpartition(":")
        out.add((ref.strip(), obj.strip()))
    return out


def named(body):
    """Every token an approval could be written against."""
    found = set(PROJECT_REF.findall(body))
    for key in ("name", "migration_name", "function_slug", "branch_id", "project_id"):
        for match in re.finditer(r'"%s"\s*:\s*"([^"]+)"' % key, body):
            found.add(match.group(1))
    return found


def statements(sql):
    """Every statement in the text, split on the separator rather than the line.

    A write chained onto a read shares one line, so a split that needs a newline
    reads the pair as a single statement and judges it by the read that opens it.
    """
    return [s for s in sql.split(";") if s.strip()]


def refuse(what, body):
    tokens = sorted(named(body))
    sys.stderr.write(
        "BLOCKED: this writes to the database.\n\n"
        "The database is read-only here. A write is one object approved out\n"
        "loud, and approval for one object is not approval for the next.\n\n"
        "what this would do:\n  %s\n" % what[:400])
    if tokens:
        sys.stderr.write("\nnames it carries:\n  %s\n" % "\n  ".join(tokens))
    sys.stderr.write(
        "\nINTELLIGENCE_DB_WRITE=<project ref>:<object> approves that one.\n")
    sys.exit(2)


def guard_mcp():
    p = payload()
    name = str(p.get("tool_name") or "")
    if not MCP_WRITE.search(name):
        return
    body = json.dumps(p.get("tool_input") or {})
    if HOSTING_CALL.search(body):
        return
    if BY_STATEMENT.search(name):
        sql = str((p.get("tool_input") or {}).get("query") or "")
        if all(READ_SHAPED.match(s) for s in statements(sql)):
            return
    tokens = named(body)
    for ref, obj in approved():
        if obj and obj in tokens and (not ref or ref in tokens):
            return
    refuse(name.rsplit("__", 1)[-1], body)


def guard_bash():
    p = payload()
    command = str((p.get("tool_input") or {}).get("command") or "")
    for segment in acting_segments(command):
        for pattern, what in ((ADMIN_MERGE, "merge past a required review"),
                              (PROTECTION_EDIT, "change branch protection"),
                              (CLI_WRITE, "write to the database")):
            found = pattern.search(segment)
            if not found:
                continue
            if any(obj and obj in segment for _, obj in approved()):
                continue
            refuse("%s: %s" % (what, found.group(0)), segment)


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "guard-mcp":
        guard_mcp()
    elif verb == "guard-bash":
        guard_bash()
    else:
        sys.stderr.write(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
