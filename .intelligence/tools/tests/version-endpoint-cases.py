#!/usr/bin/env python3
"""Cases the version endpoint installer has to get right.

The endpoint's shape follows how the project is built, and an endpoint already
present is left alone whatever it is called: a framework route is named for its
position rather than its subject, so a check that reads filenames reports a repo
that already answers as missing and writes a second one beside it.

  version-endpoint-cases.py     run them
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "version-endpoint.py")
FAILURES = []


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def project(tmp, name, deps):
    root = Path(tmp) / name
    root.mkdir()
    (root / "package.json").write_text(json.dumps({"dependencies": deps}))
    return root


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def main():
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        vite = project(tmp, "a-site", {"vite": "5"})
        check("a bundled site gets a function",
              mod.target(vite)[0].relative_to(vite).as_posix(), "api/version.js")

        nxt = project(tmp, "an-app", {"next": "15"})
        (nxt / "src" / "app").mkdir(parents=True)
        check("a framework app gets a route beside its other routes",
              mod.target(nxt)[0].relative_to(nxt).as_posix(),
              "src/app/api/version/route.js")

        cra = project(tmp, "an-older-site", {"react-scripts": "5"})
        check("a site built the older way gets one too",
              mod.target(cra)[0].relative_to(cra).as_posix(), "api/version.js")
        check("and it is the same function the bundled sites get",
              mod.target(cra)[1], mod.target(vite)[1])

        plain = project(tmp, "a-library", {"react": "19"})
        check("a project that serves no pages is left out", mod.target(plain)[0], None)

        check("installing writes it", "wrote" in mod.install(vite), True)
        check("the written file reads the build from the host",
              "VERCEL_GIT_COMMIT_SHA" in (vite / "api" / "version.js").read_text(), True)
        check("and refuses to be cached",
              "no-store" in (vite / "api" / "version.js").read_text(), True)
        check("installing twice changes nothing", mod.install(vite), "already answers")

        # A route named for its position is still an endpoint.
        existing = project(tmp, "an-app-2", {"next": "15"})
        route = existing / "src" / "app" / "api" / "version"
        route.mkdir(parents=True)
        (route / "route.js").write_text("export function GET() {}\n")
        check("a route file is recognised though its name says nothing",
              mod.present(existing) is not None, True)
        check("so it is not written over", mod.install(existing), "already answers")

        # The host can be pointed at a subdirectory, and an endpoint above it is
        # deployed nowhere while every check on the repository still passes.
        outer = project(tmp, "a-monorepo", {"react": "19"})
        inner = outer / "web"
        inner.mkdir()
        (inner / "package.json").write_text(json.dumps({"dependencies": {"vite": "5"}}))
        mod.deployed_root = lambda root: inner if root == outer else root
        check("the endpoint follows the directory the host builds",
              mod.target(outer)[0].relative_to(outer).as_posix(), "web/api/version.js")
        check("installing puts it there", "web/api/version.js" in mod.install(outer), True)
        check("and finds it there next time", mod.install(outer), "already answers")
        mod = load()

        # Dependencies are not the project.
        buried = project(tmp, "a-site-2", {"vite": "5"})
        packaged = buried / "node_modules" / "x" / "api" / "version"
        packaged.mkdir(parents=True)
        (packaged / "route.js").write_text("x\n")
        check("an endpoint inside a dependency is not this project's",
              mod.present(buried), None)

    for f in FAILURES:
        print(f)
    print("version-endpoint: %d failing" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
