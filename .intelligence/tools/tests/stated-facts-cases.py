#!/usr/bin/env python3
"""Cases the stated-facts check has to get right.

A count in a document agrees with the setup or it is a disagreement, and a
sentence that no longer states the count is a disagreement too: a rule that
quietly stops applying still reports clean, which is worse than having no rule.

  stated-facts-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "stated-facts.py")
FAILURES = []

GOOD = ("Twelve run on their own: eleven on the Pi and one on the Mac.\n\n"
        "| Continuous | Sentinel, `47 3,11,19 * * *` | x |\n"
        "| Daily | Maintenance | The pass over every owned repo, nine phases |\n")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verdict(mod, text):
    with tempfile.TemporaryDirectory() as tmp:
        doc = Path(tmp) / "INTELLIGENCE.md"
        doc.write_text(text)
        mod.AGREEMENT = doc
        mod.RULES = tuple((doc, pattern, keys) for _, pattern, keys in mod.RULES)
        mod.facts = lambda: {"routines.total": 12, "routines.cloud": 0,
                             "routines.pi": 11, "routines.mac": 1,
                             "sentinel.schedule": "47 3,11,19 * * *",
                             "maintenance.phases": 9}
        return mod.disagreements()


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %s, want %s" % (label, got, want))


def main():
    check("a document that agrees is clean", verdict(load(), GOOD), [])
    check("a wrong host count disagrees",
          bool(verdict(load(), GOOD.replace("eleven on the Pi", "nine on the Pi"))), True)
    check("a wrong total disagrees",
          bool(verdict(load(), GOOD.replace("Twelve run", "Nine run"))), True)
    check("a wrong schedule disagrees",
          bool(verdict(load(), GOOD.replace("47 3,11,19", "47 */8"))), True)
    check("the word and the digit are the same count",
          verdict(load(), GOOD.replace("Twelve run", "12 run")), [])
    check("a sentence that stopped stating the count disagrees",
          bool(verdict(load(), "Some routines run in various places.\n")), True)
    check("moving a routine between machines is caught",
          bool(verdict(load(), GOOD.replace("one on the Mac", "two on the Mac"))), True)
    check("a phase added without the sentence following is caught",
          bool(verdict(load(), GOOD.replace("nine phases", "eight phases"))), True)

    for f in FAILURES:
        print(f)
    print("stated-facts: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
