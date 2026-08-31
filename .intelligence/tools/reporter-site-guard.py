#!/usr/bin/env python3
"""A site's reporting snippet names that site, and a commit cannot change which.

The snippet carries one string that decides where every error from the page is
filed: `var site = '...'`. Nothing downstream questions it. A page carrying
another site's name reports into that site's tickets, and the client whose
browser threw the error is never told.

It is also the one line a bad splice gets wrong. On 2026-08-31 a merged snippet
was assembled through a shared path, a sibling overwrote it mid-run, and the
wrong client's block reached a staging area twice. The name was the only visible
difference between the right file and the wrong one.

So the name is held against the name the repository already used. A commit that
changes it is either an onboarding -- where there is nothing to change it from --
or a mistake, and this refuses the second without having to know which sites
exist. A second reading catches the case where the line survived a swap that
took everything around it: any other site's name appearing inside the block is
refused too, drawn from the snippets the other checkouts on this machine carry
rather than from a list written down here.

  reporter-site-guard.py guard      refuse a commit that renames the site
  reporter-site-guard.py check      report on the working tree, changing nothing

INTELLIGENCE_ALLOW_SITE_RENAME=1 covers a rename that is genuinely intended,
which is a rebrand and not a way past a refusal.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPORTER = re.compile(r"sunday\.tail[0-9a-z]+\.ts\.net/report"
                      r"|error-reporting-service/report", re.I)
SITE = re.compile(r"""\bvar\s+site\s*=\s*(['"])(?P<name>[^'"]+)\1""")
ROOTS = (Path.home() / "Development" / "WebstormProjects",
         Path.home() / "Development" / "IdeaProjects")
TIMEOUT = 20


def run(args, cwd=None):
    try:
        done = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                              timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def repo_root(cwd):
    out = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    return Path(out.strip()) if out else None


def staged_files(root):
    out = run(["git", "diff", "--cached", "--name-only"], cwd=root) or ""
    return [line for line in out.splitlines() if line.strip()]


def name_in(text):
    match = SITE.search(text or "")
    return match.group("name") if match else None


def known_names(exclude):
    """Every other site's name, read from the snippet each checkout carries.

    Taken from the trees rather than from a list here, so a site onboarded after
    this was written is covered without anyone remembering to add it.
    """
    names = set()
    for base in ROOTS:
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if not (entry / ".git").exists():
                continue
            for candidate in ("index.html", "public/index.html",
                              "partials/headcommon.html", "web/index.html",
                              "src/app/layout.jsx"):
                path = entry / candidate
                try:
                    text = path.read_text(errors="ignore")
                except OSError:
                    continue
                if not REPORTER.search(text):
                    continue
                found = name_in(text)
                if found and found != exclude:
                    names.add(found)
    return names


def findings(root):
    """Every staged snippet whose site name does not match the one on record."""
    problems = []
    for name in staged_files(root):
        staged = run(["git", "show", ":" + name], cwd=root)
        if staged is None or not REPORTER.search(staged):
            continue
        now = name_in(staged)
        if not now:
            problems.append((name, None, None, "the snippet carries no site name"))
            continue
        before = run(["git", "show", "HEAD:" + name], cwd=root)
        was = name_in(before) if before else None
        if was and was != now:
            problems.append((name, was, now,
                             "the commit renames the site this page reports as"))
            continue
        others = sorted(n for n in known_names(now) if n in staged)
        if others:
            problems.append((name, ", ".join(others), now,
                             "another site's name is in the file"))
    return problems


def report(problems):
    sys.stderr.write("BLOCKED: the reporting snippet does not name this site.\n\n")
    for path, was, now, why in problems:
        sys.stderr.write("  %s\n    %s\n" % (path, why))
        if was:
            sys.stderr.write("    on record: %s\n    staged:    %s\n" % (was, now))
    sys.stderr.write(
        "\nThe name decides which site's tickets every error from this page is "
        "filed\nunder, so a wrong one reports a client's errors into somebody "
        "else's queue.\nCheck the staged content rather than whatever it was "
        "spliced from:\n\n  git show :<path> | grep 'var site'\n\n"
        "INTELLIGENCE_ALLOW_SITE_RENAME=1 covers a rename that is intended.\n")


def guard():
    if os.environ.get("INTELLIGENCE_ALLOW_SITE_RENAME") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    if not re.search(r"\bgit\b[^|;&]*\bcommit\b", command):
        return 0
    root = repo_root(payload.get("cwd") or os.getcwd())
    if root is None:
        return 0
    problems = findings(root)
    if not problems:
        return 0
    report(problems)
    return 2


def check():
    root = repo_root(os.getcwd())
    if root is None:
        sys.stderr.write("not a git repository\n")
        return 2
    problems = findings(root)
    if problems:
        report(problems)
        return 1
    print("the staged snippet names this site")
    return 0


def main(argv):
    if len(argv) != 1 or argv[0] not in ("guard", "check"):
        sys.stderr.write(__doc__)
        return 2
    return guard() if argv[0] == "guard" else check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
