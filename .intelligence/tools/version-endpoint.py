#!/usr/bin/env python3
"""The commit a site is serving, answered by the site itself.

A deployment record says what a host was asked to build. It is wrong whenever a
build was made from the command line, an address is pinned to an older one, or a
cache is still holding the previous bundle. The page is the only thing that
knows what a visitor is getting, so it is the page that answers.

The shape differs by framework and the answer does not: the commit the running
build came from, never cached.

  check [repo]     whether a repo answers, and how it would
  install <repo>   write the endpoint for that repo's framework
  sweep            install into every owned checkout that lacks one
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
ROOTS = (HOME / "Development" / "WebstormProjects",
         HOME / "Development" / "IdeaProjects",
         HOME / "Development")

NEXT_ROUTE = '''import { NextResponse } from 'next/server';

// Never cached: the answer is what is deployed now, and a cached one tells a
// stale app it is current.
export const dynamic = 'force-dynamic';

export function GET() {
  return NextResponse.json(
    { build: process.env.VERCEL_GIT_COMMIT_SHA || 'dev' },
    { headers: { 'Cache-Control': 'no-store, max-age=0' } }
  );
}
'''

VERCEL_FUNCTION = '''// The commit this deployment was built from, read from the page rather than
// from the host's record of it. Never cached: a cached answer would report a
// build that is no longer being served.
//
// The host value is reached through globalThis because this file runs on the
// server while the rest of the project runs in a browser: a project whose
// linter knows only browser globals rejects the bare name, and one that knows
// both rejects a declaration of it.
export default function handler(request, response) {
  const build = globalThis.process?.env?.VERCEL_GIT_COMMIT_SHA || 'dev';
  response.setHeader('Cache-Control', 'no-store, max-age=0');
  response.status(200).json({ build });
}
'''


def framework(root):
    manifest = root / "package.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text())
    except ValueError:
        return None
    deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
    if "next" in deps:
        return "next"
    # A Create React App build is served as static files like a Vite one, and
    # the host reads `api/` beside them the same way. Leaving it out is what
    # made the two projects on it the only ones a ship run could not take its
    # own reading from: the endpoint was never written, so the request fell
    # through to whatever the project sends an unmatched path.
    if "vite" in deps or "astro" in deps or "react-scripts" in deps:
        return "vercel-function"
    return None


def deployed_root(root):
    """The directory the host actually builds, which is not always the checkout.

    A project whose host is pointed at a subdirectory never sees anything above
    it, so an endpoint written beside the outer manifest is deployed nowhere and
    answers nothing while every check on the repository still passes.
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "site_live", str(Path(__file__).resolve().parent / "site-live.py"))
        sl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sl)
        site = sl.resolve(str(root))
        if not site.get("project"):
            return root
        scope = "?teamId=%s" % site["scope"] if site.get("scope") else ""
        project = sl.api("/v9/projects/%s%s" % (site["project"], scope),
                         sl.vercel_token()) or {}
        inner = (project.get("rootDirectory") or "").strip("/")
        if inner and (root / inner).is_dir():
            return root / inner
    except Exception:
        pass
    return root


def target(root):
    """Where the endpoint belongs, given how the project is built."""
    root = deployed_root(root)
    kind = framework(root)
    if kind == "next":
        for base in (root / "src" / "app", root / "app"):
            if base.exists():
                return base / "api" / "version" / "route.js", NEXT_ROUTE
        return root / "app" / "api" / "version" / "route.js", NEXT_ROUTE
    if kind == "vercel-function":
        return root / "api" / "version.js", VERCEL_FUNCTION
    return None, None


def present(root):
    """Any endpoint already answering the question, wherever it was put.

    A framework route is named for its position rather than its subject, so the
    directory is what identifies it and the filename does not.
    """
    for parent in root.rglob("version"):
        if "node_modules" in parent.parts or ".git" in parent.parts:
            continue
        if parent.is_dir() and parent.parent.name == "api":
            for child in parent.iterdir():
                if child.suffix in (".js", ".ts", ".mjs"):
                    return child
    for base in root.rglob("api"):
        if "node_modules" in base.parts or ".git" in base.parts or not base.is_dir():
            continue
        for suffix in (".js", ".ts", ".mjs"):
            candidate = base / ("version" + suffix)
            if candidate.exists():
                return candidate
    return None


def checkouts():
    seen = {}
    for base in ROOTS:
        if not base.exists():
            continue
        for entry in sorted(base.iterdir()):
            if entry.is_dir() and (entry / ".git").exists() and entry.name not in seen:
                seen[entry.name] = entry
    return list(seen.values())


def cmd_check(argv):
    roots = [Path(argv[0]).resolve()] if argv else checkouts()
    missing = 0
    for root in roots:
        kind = framework(root)
        if not kind:
            continue
        found = present(root)
        if found:
            print("%-32s answers at %s" % (root.name, found.relative_to(root)))
            continue
        missing += 1
        path, _ = target(root)
        print("%-32s missing, would write %s" % (root.name, path.relative_to(root)))
    print("\n%d checkout(s) without one" % missing)
    return 0


def install(root):
    path, body = target(root)
    if path is None:
        return "not a framework this covers"
    if present(deployed_root(root)):
        return "already answers"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    conform(root, path)
    return "wrote %s" % path.relative_to(root)


def conform(root, path):
    """Rewrite the file in whatever style the project already enforces.

    A repository that checks formatting rejects a file written in anyone else's
    style, so the endpoint is generated and then handed to the project's own
    formatter rather than being written to look right in general.
    """
    manifest = root / "package.json"
    try:
        data = json.loads(manifest.read_text())
    except (OSError, ValueError):
        return
    deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
    if "prettier" not in deps:
        return
    subprocess.run(["npx", "--no-install", "prettier", "--write",
                    str(path.relative_to(root))], cwd=root,
                   capture_output=True, timeout=180)


def cmd_install(argv):
    if not argv:
        sys.stderr.write("install needs a repository path\n")
        return 1
    root = Path(argv[0]).resolve()
    print("%s: %s" % (root.name, install(root)))
    return 0


def cmd_sweep():
    for root in checkouts():
        if not framework(root):
            continue
        print("%-32s %s" % (root.name, install(root)))
    return 0


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    rest = sys.argv[2:]
    if verb == "check":
        return cmd_check(rest)
    if verb == "install":
        return cmd_install(rest)
    if verb == "sweep":
        return cmd_sweep()
    sys.stderr.write(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
