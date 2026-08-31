#!/usr/bin/env python3
"""Runs the SEO gate engine.

The engine sits in its own tree rather than inside the skill that describes it, so
that retiring the skill leaves the gates and the thing that runs them standing.
This is the entry point the hooks in guard-hub.py call; it holds no logic of its
own so the two cannot drift.

An engine it cannot find exits 2. guard-hub.py blocks on 2 and only prints on
anything else, so a gate tool that is not there refuses the action rather than
letting it through with a warning.
"""

import os
import sys
from pathlib import Path

CANDIDATES = [
    Path.home() / ".intelligence" / "checklists" / "seo" / "bin" / "seo-pass.py",
    Path(__file__).resolve().parent.parent / "checklists" / "seo" / "bin" / "seo-pass.py",
]


def main():
    for path in CANDIDATES:
        if path.is_file():
            os.execv(sys.executable, [sys.executable, str(path), *sys.argv[1:]])
    print("seo-pass: the SEO gate engine is not installed - looked for %s"
          % " and ".join(str(p) for p in CANDIDATES), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
