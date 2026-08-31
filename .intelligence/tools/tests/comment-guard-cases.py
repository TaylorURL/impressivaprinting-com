#!/usr/bin/env python3
"""Cases the comment guard has to get right.

A guard verb refuses a comment that narrates provenance, addresses the reader,
or instructs a person on handling, and lets a comment stating what the system
is stand. Both edges are pinned at every door the guard watches: the edit hook,
the heredoc scan on shell commands, and the standalone check verb. The drift
stamp is pinned too, since a reworded source section has to block every guard
until the patterns are brought into step and restamped.

  comment-guard-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "comment-guard.py")

FAILURES = []

SECTION_HEAD = "## Provenance Is Not Purpose"
SKILL_V1 = "# Standard\n\n" + SECTION_HEAD + "\n\nRule wording one.\n\n## Next\n\nOther.\n"
SKILL_V2 = "# Standard\n\n" + SECTION_HEAD + "\n\nRule wording two.\n\n## Next\n\nOther.\n"

CLEAN_PY = "x = 1\n# Reads the manifest and resolves each path.\n"
PROVENANCE_PY = "x = 1\n# This used to be slower.\n"
READER_DOC_PY = '"""Adjust your settings before running."""\nx = 1\n'
CONVERSATION_PY = "x = 1\n# Kept small, as requested.\n"
CODE_ONLY_PY = 'name = "previously"\nx = 1\n'
PROVENANCE_JS = "// formerly the default path\nvar x = 1;\n"
HASH_IN_JS = "# formerly the default\nvar x = 1;\n"

HEREDOC_BAD = ("cat > out.sh <<'EOF'\n"
               "# originally a cron job\n"
               "echo hi\n"
               "EOF\n")
# A Markdown heading opens with the character a shell comment opens with, and
# the words a document addresses its reader with are the words the patterns
# flag, so a document scanned as shell trips every one of them.
HEREDOC_PROSE = ("cat > doc.md <<'EOF'\n"
                 "# Read before you speak\n"
                 "\n"
                 "## What you should know\n"
                 "Previously the default was different.\n"
                 "EOF\n")
HEREDOC_CLEAN = ("cat > out.sh <<'EOF'\n"
                 "# Prints the greeting.\n"
                 "echo hi\n"
                 "EOF\n")
HEREDOC_CODE_ONLY = ("cat > out.sh <<'EOF'\n"
                     "echo previously\n"
                     "EOF\n")


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(verb, payload, home, allow=False):
    """Run one guard verb against a hook event, homed inside a temp tree.

    The guard resolves its skill file and stamp from HOME, so pointing HOME at
    the fixture keeps every read and every stamp write inside the temp tree and
    away from the live config.
    """
    env = dict(os.environ)
    env["HOME"] = str(home)
    env.pop("INTELLIGENCE_ALLOW_COMMENT", None)
    if allow:
        env["INTELLIGENCE_ALLOW_COMMENT"] = "1"
    return subprocess.run([sys.executable, str(TARGET), verb],
                          input=payload, capture_output=True, text=True, env=env)


def edit_event(path, content, tool="Write", key="content"):
    return json.dumps({"tool_name": tool, "tool_input": {"file_path": path, key: content}})


def bash_event(command):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def stamped_home(tmp, body=SKILL_V1):
    home = Path(tmp) / "home"
    skill = home / ".intelligence" / "skills" / "writing-comments" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text(body)
    assert str(home).startswith(tmp), "escaped the temp tree: %s" % home
    return home


def guard_edit_cases():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        assert str(home).startswith(tmp), "escaped the temp tree: %s" % home

        check("edit: clean comment passes",
              run("guard-edit", edit_event("a.py", CLEAN_PY), home).returncode, 0)
        check("edit: provenance comment refused",
              run("guard-edit", edit_event("a.py", PROVENANCE_PY), home).returncode, 2)
        check("edit: reader-addressed docstring refused",
              run("guard-edit", edit_event("a.py", READER_DOC_PY), home).returncode, 2)
        check("edit: conversation-relative comment refused",
              run("guard-edit", edit_event("a.py", CONVERSATION_PY), home).returncode, 2)
        check("edit: flagged word in code, not a comment",
              run("guard-edit", edit_event("a.py", CODE_ONLY_PY), home).returncode, 0)
        check("edit: js slash comment refused",
              run("guard-edit", edit_event("a.js", PROVENANCE_JS), home).returncode, 2)
        check("edit: hash line is not js comment syntax",
              run("guard-edit", edit_event("a.js", HASH_IN_JS), home).returncode, 0)
        check("edit: Edit new_string scanned",
              run("guard-edit",
                  edit_event("a.py", "# per our discussion, one pass\n",
                             tool="Edit", key="new_string"),
                  home).returncode, 2)
        check("edit: empty content passes",
              run("guard-edit", edit_event("a.py", ""), home).returncode, 0)
        check("edit: unreadable event passes",
              run("guard-edit", "not json", home).returncode, 0)
        check("edit: escape variable overrides",
              run("guard-edit", edit_event("a.py", PROVENANCE_PY), home,
                  allow=True).returncode, 0)


def guard_bash_cases():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        home.mkdir()

        check("bash: bad heredoc comment refused",
              run("guard-bash", bash_event(HEREDOC_BAD), home).returncode, 2)
        check("bash: clean heredoc passes",
              run("guard-bash", bash_event(HEREDOC_CLEAN), home).returncode, 0)
        check("bash: flagged word outside a heredoc passes",
              run("guard-bash", bash_event('echo "formerly the default"'), home).returncode, 0)
        check("bash: heredoc code line with flagged word passes",
              run("guard-bash", bash_event(HEREDOC_CODE_ONLY), home).returncode, 0)
        check("bash: empty command passes",
              run("guard-bash", bash_event(""), home).returncode, 0)
        check("bash: heredoc writing a document passes",
              run("guard-bash", bash_event(HEREDOC_PROSE), home).returncode, 0)
        check("bash: a document beside a script does not excuse the script",
              run("guard-bash", bash_event(HEREDOC_PROSE + HEREDOC_BAD), home).returncode, 2)


def check_verb_cases():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        bad = Path(tmp) / "bad.py"
        good = Path(tmp) / "good.py"
        bad.write_text(PROVENANCE_PY)
        good.write_text(CLEAN_PY)
        for path in (bad, good):
            assert str(path).startswith(tmp), "escaped the temp tree: %s" % path

        env = dict(os.environ)
        env["HOME"] = str(home)
        env.pop("INTELLIGENCE_ALLOW_COMMENT", None)
        p = subprocess.run([sys.executable, str(TARGET), "check", str(bad)],
                           capture_output=True, text=True, env=env)
        check("check: bad file refused", p.returncode, 2)
        check("check: refusal quotes the standard",
              "writing-comments standard" in p.stderr, True)
        p = subprocess.run([sys.executable, str(TARGET), "check", str(good)],
                           capture_output=True, text=True, env=env)
        check("check: clean file passes", p.returncode, 0)
        check("check: clean file reports clean", p.stdout.strip(), "clean")
        p = subprocess.run([sys.executable, str(TARGET), "check", "--stdin", ".py"],
                           input=PROVENANCE_PY, capture_output=True, text=True, env=env)
        check("check: --stdin refused", p.returncode, 2)
        p = subprocess.run([sys.executable, str(TARGET), "check", "--stdin", ".py"],
                           input=CLEAN_PY, capture_output=True, text=True, env=env)
        check("check: --stdin clean passes", p.returncode, 0)


def drift_cases():
    with tempfile.TemporaryDirectory() as tmp:
        home = stamped_home(tmp)
        stamp = home / ".intelligence" / "state" / "comment-guard-source.sha"

        # A first run against an unstamped skill file stamps it and judges the
        # content on its merits.
        p = run("guard-edit", edit_event("a.py", PROVENANCE_PY), home)
        check("drift: first run self-stamps and still refuses content", p.returncode, 2)
        check("drift: first refusal is about the standard, not drift",
              "writing-comments standard" in p.stderr, True)
        check("drift: stamp written inside the fixture home", stamp.is_file(), True)

        (home / ".intelligence" / "skills" / "writing-comments" / "SKILL.md").write_text(SKILL_V2)
        p = run("guard-edit", edit_event("a.py", CLEAN_PY), home)
        check("drift: reworded section blocks even clean content", p.returncode, 2)
        check("drift: refusal names the drift", "changed since" in p.stderr, True)
        p = run("guard-bash", bash_event(HEREDOC_CLEAN), home)
        check("drift: bash guard blocks on drift too", p.returncode, 2)

        env = dict(os.environ)
        env["HOME"] = str(home)
        p = subprocess.run([sys.executable, str(TARGET), "restamp"],
                           capture_output=True, text=True, env=env)
        check("drift: restamp accepts the new wording", p.returncode, 0)
        check("drift: restamp reports the section",
              p.stdout.strip().startswith("stamped"), True)
        check("drift: restamp reopens the guard",
              run("guard-edit", edit_event("a.py", CLEAN_PY), home).returncode, 0)

    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        env = dict(os.environ)
        env["HOME"] = str(home)
        p = subprocess.run([sys.executable, str(TARGET), "restamp"],
                           capture_output=True, text=True, env=env)
        check("drift: restamp with no skill file refuses", p.returncode, 2)


def parser_cases():
    mod = load()

    body = mod.heredoc_bodies("cat <<EOF\nline one\nline two\nEOF\necho done\n")
    check("parser: heredoc lines", [text for _, text in body], ["line one", "line two"])
    check("parser: heredoc line numbers", [n for n, _ in body], [2, 3])
    check("parser: command with no heredoc", mod.heredoc_bodies("echo hi"), [])

    css = mod.comment_lines("/* the panel grid */\nbody { color: red; }\n", ".css")
    check("parser: css block comment collected", len(css), 1)
    sql = mod.comment_lines("-- selects open rows\nSELECT 1;\n", ".sql")
    check("parser: sql dash comment collected", len(sql), 1)
    check("parser: shebang is not a comment",
          mod.comment_lines("#!/bin/sh\necho hi\n", ".sh"), [])

    # A word table assigned to a name closes on a line that opens with the same
    # delimiter a docstring opens with. Read line by line that close is an open,
    # and everything after it is judged as prose until the next real docstring,
    # so the patterns inside a regex answer for wording nobody wrote.
    table = ('STOP = frozenset("""\nyour own words here\n""".split())\n'
             'CORRECTION = re.compile(r"\\byour\\b")\n')
    collected = [text for _, text in mod.comment_lines(table, ".py")]
    check("parser: a word table is not a docstring", collected, [])
    check("parser: source after a word table is not a comment",
          any("your" in text for text in collected), False)

    real = ('def f():\n    """States what f is."""\n    return 1\n'
            '# a trailing note\n')
    got = [text for _, text in mod.comment_lines(real, ".py")]
    check("parser: a real docstring is still read", "States what f is." in got, True)
    check("parser: a real comment is still read", "a trailing note" in got, True)

    broken = 'def f(:\n    """unparseable."""\n'
    check("parser: source that will not parse falls back rather than passing",
          bool(mod.comment_lines(broken, ".py")), True)

    blocks = mod.heredoc_blocks("cat > doc.md <<'EOF'\nline one\nEOF\n")
    check("parser: heredoc target", [target for target, _ in blocks], ["doc.md"])
    check("parser: heredoc target absent",
          [t for t, _ in mod.heredoc_blocks("cat <<EOF | sh\nline\nEOF\n")], [None])
    check("parser: redirect ignores a descriptor dup",
          [t for t, _ in mod.heredoc_blocks("cat <<EOF 2>&1\nline\nEOF\n")], [None])
    check("parser: document target reads as prose", mod.prose_target("a/b/SKILL.md"), True)
    check("parser: script target does not", mod.prose_target("out.sh"), False)
    check("parser: absent target does not", mod.prose_target(None), False)

    hits = mod.findings([(1, "kept as agreed")])
    check("parser: findings names the rule", hits[0][2], "phrased relative to a conversation")
    check("parser: findings passes clean text", mod.findings([(1, "reads the file")]), [])


def main():
    check("usage: unknown verb refuses",
          subprocess.run([sys.executable, str(TARGET), "nope"],
                         capture_output=True, text=True).returncode, 2)
    guard_edit_cases()
    guard_bash_cases()
    check_verb_cases()
    drift_cases()
    parser_cases()

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
