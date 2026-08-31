#!/usr/bin/env python3
"""Cases the database write guard has to get right.

Reads pass and writes are refused, and the approval is per object: naming one
migration opens that migration and nothing beside it. The project reference is
never on its own an approval, because every migration against a project carries
it and an approval that a reference satisfies opens the project rather than the
object.

The same suite covers the two shell doors that land a change no required check
has read.

  db-write-guard-cases.py      run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "db-write-guard.py")

REF = "abcdefghijklmnopqrst"
OTHER_REF = "zyxwvutsrqponmlkjihg"
FAILURES = []

# Assembled rather than written out, so the suite's own source does not carry a
# command the guard is built to refuse.
MERGE = "gh pr merge 42 --ad" + "min --squash"
PROTECT = "gh api -X DELETE repos/o/r/branches/main/protec" + "tion"


def run(verb, payload, env=None):
    clean = {k: v for k, v in os.environ.items()
             if k != "INTELLIGENCE_DB_WRITE"}
    p = subprocess.run([sys.executable, str(TARGET), verb],
                       input=json.dumps(payload), capture_output=True,
                       text=True, env={**clean, **(env or {})})
    return p.returncode


def bash(command, env=None):
    return run("guard-bash", {"tool_name": "Bash",
                              "tool_input": {"command": command}}, env)


def mcp(name, inp, env=None):
    return run("guard-mcp", {"tool_name": "mcp__0917cb34__" + name,
                             "tool_input": inp}, env)


def approve(*pairs):
    return {"INTELLIGENCE_DB_WRITE": ",".join(pairs)}


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %s, want %s" % (label, got, want))


def main():
    migration = {"project_id": REF, "name": "add_customer_email",
                 "query": "ALTER TABLE orders ADD COLUMN customer_email text"}

    check("an unapproved migration is refused", mcp("apply_migration", migration), 2)
    check("the named migration is allowed",
          mcp("apply_migration", migration,
              approve(REF + ":add_customer_email")), 0)
    check("a second migration is not covered by the first approval",
          mcp("apply_migration", {"project_id": REF, "name": "drop_orders",
                                  "query": "DROP TABLE orders"},
              approve(REF + ":add_customer_email")), 2)
    check("the project reference alone is not an approval",
          mcp("apply_migration", migration, approve(REF + ":")), 2)
    check("an approval for another project does not carry",
          mcp("apply_migration", migration,
              approve(OTHER_REF + ":add_customer_email")), 2)

    check("a row count is a reading",
          mcp("execute_sql", {"query": "select count(*) from orders"}), 0)
    check("a query plan is a reading",
          mcp("execute_sql", {"query": "explain analyze select 1"}), 0)
    check("a common table expression is a reading",
          mcp("execute_sql", {"query": "with x as (select 1) select * from x"}), 0)
    check("a delete is a write", mcp("execute_sql",
                                     {"query": "delete from orders where id = 1"}), 2)
    check("a grant is a write",
          mcp("execute_sql", {"query": "grant all on orders to anon"}), 2)
    check("a write chained onto a read is still a write",
          mcp("execute_sql", {"query": "select 1; drop table orders"}), 2)

    check("pausing a project is a write", mcp("pause_project", {"project_id": REF}), 2)
    check("pausing a deployment is not a database write",
          mcp("pause_project", {"projectId": "prj_X9tGMgjjJRIzkAOujqE0fQj2eEsk",
                                "teamId": "team_8KwOtFUhRyHmZM8dPzqh0fq9"}), 0)
    check("a deployment call cannot be mistaken for its database namesake",
          mcp("restore_project", {"projectId": "prj_X", "teamId": "team_Y"}), 0)
    check("deploying a function is a write",
          mcp("deploy_edge_function", {"project_id": REF, "name": "charge"}), 2)
    check("listing tables is a reading", mcp("list_tables", {"project_id": REF}), 0)
    check("reading logs is a reading", mcp("query_logs", {"project_id": REF}), 0)

    check("merging past a required review is refused", bash(MERGE), 2)
    check("removing branch protection is refused", bash(PROTECT), 2)
    check("an ordinary merge is untouched", bash("gh pr merge 42 --squash"), 0)
    check("an ordinary command is untouched", bash("git status"), 0)
    check("a search naming a write verb is a reading",
          bash("grep -rn 'supabase db push' ."), 0)

    for f in FAILURES:
        print(f)
    print("db-write-guard: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
