#!/usr/bin/env python3
"""Cases the reporting snippet's site-name guard has to get right.

The name is held against the repository's own record of it rather than against a
list of sites, so the guard works on a repo it has never seen and stays correct
when a site is onboarded. That makes the first commit its own case: there is
nothing to compare against, and refusing there would block every onboarding.

  reporter-site-guard-cases.py     run them
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "reporter-site-guard.py")
FAILURES = []
ENDPOINT = "https://sunday.tail1f78d7.ts.net/report"


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def snippet(name):
    return ('<script>(function(){var endpoint="%s";var site = "%s";})()</script>\n'
            % (ENDPOINT, name))


def git(root, *args):
    subprocess.run(["git"] + list(args), cwd=root, capture_output=True,
                   text=True, check=False)


def repo(tmp, name, site):
    root = Path(tmp) / name
    root.mkdir()
    git(root, "init", "-q", ".")
    git(root, "config", "user.email", "t@t.t")
    git(root, "config", "user.name", "T")
    (root / "index.html").write_text(snippet(site))
    git(root, "add", "-A")
    git(root, "commit", "-qm", "initial")
    return root


def stage(root, text):
    (root / "index.html").write_text(text)
    git(root, "add", "-A")


def main():
    mod = load()

    check("a site name is read out of the snippet",
          mod.name_in(snippet("Baytown Go Karts")), "Baytown Go Karts")
    check("single quotes read the same",
          mod.name_in("var site = 'Smyrna Tools'"), "Smyrna Tools")
    check("a file with no snippet has no name", mod.name_in("<p>hello</p>"), None)

    with tempfile.TemporaryDirectory() as tmp:
        # The incident: another client's block staged over this one's.
        site = repo(tmp, "baytown", "Baytown Go Karts")
        stage(site, snippet("Dickinson Bayou Fleeting"))
        found = mod.findings(site)
        check("a staged rename is refused", len(found), 1)
        check("and it names both sides",
              (found[0][1], found[0][2]) if found else None,
              ("Baytown Go Karts", "Dickinson Bayou Fleeting"))

        # The ordinary case this rollout was actually making.
        stage(site, snippet("Baytown Go Karts") + "<!-- preventDefault -->\n")
        check("the same name with a new body passes", mod.findings(site), [])

        # An onboarding has nothing to compare against and must not be refused.
        fresh = Path(tmp) / "fresh"
        fresh.mkdir()
        git(fresh, "init", "-q", ".")
        git(fresh, "config", "user.email", "t@t.t")
        git(fresh, "config", "user.name", "T")
        (fresh / "index.html").write_text(snippet("A New Site"))
        git(fresh, "add", "-A")
        check("a first snippet is not a rename", mod.findings(fresh), [])

        # A snippet that lost its name entirely reports nowhere.
        nameless = repo(tmp, "nameless", "Impressiva Printing")
        stage(nameless, '<script>var endpoint="%s";</script>\n' % ENDPOINT)
        check("a snippet with no site name is refused",
              len(mod.findings(nameless)), 1)

        # A file that never carried the reporter is not this guard's business.
        plain = repo(tmp, "plain", "Faded Barber Shop")
        (plain / "README.md").write_text("Dickinson Bayou Fleeting\n")
        git(plain, "add", "-A")
        check("an unrelated file naming another site passes",
              mod.findings(plain), [])

    for failure in FAILURES:
        print("FAIL %s" % failure)
    print("reporter-site-guard: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
