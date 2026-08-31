#!/usr/bin/env python3
"""Keep a repo's README version badge equal to the version its manifest declares.

The badge is written by hand and the version is bumped by a release, so the two drift
apart silently — a README claiming 5.2.72 while package.json says 5.2.73 is wrong in
exactly the way nobody notices until they quote it. Drift is the normal state of an
unchecked badge, and it never announces itself.

Repair, not refusal. The correct value is never in doubt, so there is nothing to ask
and nothing to block: `guard` rewrites the badge as a commit is about to land and says
what it changed. `check` reports without writing, for a caller that wants the answer
rather than the fix.

Only the version badge is touched. A badge whose label is not `version-` is left alone,
and a repo with no recognisable manifest or no version badge is a no-op rather than an
error, so this is safe to run over every repo unconditionally.

    version-badge.py [path]          rewrite the badge to match the manifest
    version-badge.py check [path]    report a mismatch, exit 1, write nothing
    version-badge.py guard           PreToolUse hook: repair before a commit or PR
"""
import importlib.util
import json
import pathlib
import re
import sys

# shields.io escapes a literal dash in a label as a double dash, so the version segment
# stops at the first *single* dash — which is the colour that follows it. A double dash
# belongs to the version and is consumed, which is what lets a version carry its own.
BADGE = re.compile(r'(badge/version-)((?:--|[^-\s)"\'])+)(-)')


def escape(version):
    """The version as shields.io reads it: every literal dash doubled."""
    return version.replace('-', '--')


def unescape(segment):
    """The version a badge segment states, with shields.io's doubling undone."""
    return segment.replace('--', '-')
ALT = re.compile(r'(alt="Version )([^"]+)(")')


def declared(root):
    """The version the repo's own manifest states, and which file stated it."""
    pkg = root / 'package.json'
    if pkg.is_file():
        try:
            version = json.loads(pkg.read_text()).get('version')
            if version:
                return version, 'package.json'
        except (json.JSONDecodeError, OSError):
            pass
    props = root / 'gradle.properties'
    if props.is_file():
        match = re.search(r'(?m)^version\s*=\s*(\S+)', props.read_text())
        if match:
            return match.group(1), 'gradle.properties'
    pom = root / 'pom.xml'
    if pom.is_file():
        # The project's own version is the first <version> outside <dependencies> and
        # <build>. Maven requires the project coordinates before either block, so
        # cutting at whichever comes first and taking the first match gets it without
        # an XML parse — and without picking up a dependency's version instead.
        head = pom.read_text().split('<dependencies>')[0].split('<build>')[0]
        match = re.search(r'<version>([^<]+)</version>', head)
        if match:
            return match.group(1), 'pom.xml'
    return None, None


def drift(root):
    """(readme, current, declared, source) when the badge disagrees, else None."""
    readme = root / 'README.md'
    if not readme.is_file():
        return None
    version, source = declared(root)
    if not version:
        return None
    text = readme.read_text()
    found = BADGE.search(text)
    if not found or unescape(found.group(2)) == version:
        return None
    return readme, unescape(found.group(2)), version, source


def repair(root):
    """Rewrite the badge in place. Returns the message, or None if nothing was wrong."""
    found = drift(root)
    if found is None:
        return None
    readme, current, version, source = found
    text = readme.read_text()
    text = BADGE.sub(lambda m: m.group(1) + escape(version) + m.group(3), text)
    text = ALT.sub(lambda m: m.group(1) + version + m.group(3), text)
    readme.write_text(text)
    return f'{root.name}: version badge {current} -> {version} (from {source})'


def landing_cwd(command, base):
    """The directory a commit or PR in `command` would land in, or None.

    Delegates to the shared _lib, which walks `cd` and `git -C` to find it. One
    implementation means the gates cannot disagree about which repo is landing.
    Loaded here rather than at import so cmd_guard's blanket except keeps a
    missing module from standing between a commit and the repo.
    """
    here = pathlib.Path(__file__).resolve().parent / '_lib.py'
    path = here if here.is_file() else pathlib.Path.home() / '.intelligence' / 'tools' / '_lib.py'
    spec = importlib.util.spec_from_file_location('intelligence_tools_lib', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.landing_cwd(command, base)


def cmd_guard():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    command = (payload.get('tool_input') or {}).get('command') or ''
    try:
        cwd = landing_cwd(command, payload.get('cwd') or pathlib.Path.cwd())
    except Exception:
        # A gate that cannot read the command must not stand between a commit and the
        # repo. Drift is cosmetic; a broken import here would not be.
        return 0
    if cwd is None:
        return 0
    message = repair(pathlib.Path(cwd))
    if message:
        print(f'Corrected before landing — {message}')
    return 0


def main():
    args = sys.argv[1:]
    if args[:1] == ['guard']:
        return cmd_guard()
    check_only = args[:1] == ['check'] or '--check' in args
    args = [a for a in args if a not in ('check', '--check')]
    root = pathlib.Path(args[0]).resolve() if args else pathlib.Path.cwd()
    # There are no subcommands here beyond guard and check, so a verb typed as
    # one lands in args[0] and is read as a path. Every later step answers
    # "nothing to do" about a directory that was never there, and the run exits
    # 0 having left the badge exactly as it found it.
    if not root.is_dir():
        print(f'{args[0]}: not a directory. Usage: version-badge.py [check] [<repo root>]',
              file=sys.stderr)
        return 2
    if check_only:
        found = drift(root)
        if found is None:
            return 0
        _, current, version, source = found
        print(f'{root.name}: README badge says {current}, {source} says {version}')
        return 1
    message = repair(root)
    if message:
        print(message)
    return 0


if __name__ == '__main__':
    sys.exit(main())
