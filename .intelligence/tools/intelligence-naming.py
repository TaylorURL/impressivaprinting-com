#!/usr/bin/env python3
"""Holds every configuration path to the intelligence namespace.

The harness resolves a fixed set of legacy names and cannot be told to look
elsewhere. Each one stays reachable as a symlink onto the intelligence-named
file or directory holding the content, so the harness resolves and nothing a
person opens or edits carries the legacy name.

    scan [path]      real paths still carrying a legacy name
    convert [path]   rename them and leave the alias the harness resolves
    sweep            convert every checkout held on this machine
    install          wire the guards into settings.json
    verify           exit non-zero when the wiring, aliases, or tree are off
    aliases          the paths the harness resolves, one per line
    guard-edit       PreToolUse: refuse a Write/Edit onto a legacy name
    guard-bash       PreToolUse: refuse a shell command that creates one
    guard-stop       Stop: refuse to end with a legacy name in the tree
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
INTELLIGENCE = HOME / ".intelligence"
SETTINGS = INTELLIGENCE / "settings.json"
ESCAPE = "INTELLIGENCE_ALLOW_LEGACY_NAME"
SELF = "~/.intelligence/tools/intelligence-naming.py"

# The harness resolves the key; the value holds the content.
CANON = {
    ".claude": ".intelligence",
    "CLAUDE.md": "INTELLIGENCE.md",
    "CLAUDE.local.md": "INTELLIGENCE.local.md",
}

# Names upstream owns. A path or a line carrying one is outside this namespace.
FOREIGN = (
    ".claude-plugin",
    ".claude.json",
    "claude-plugins-official",
    "claude-in-chrome",
    "claude-code",
    "claude.ai",
    "CLAUDE_CODE_",
    "CLAUDE_PROJECT_DIR",
    "CLAUDE_ENV_FILE",
    "CLAUDECODE",
)

# Directories holding harness state or third-party trees rather than configuration.
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "projects", "sessions", "session-env",
    "shell-snapshots", "telemetry", "tasks", "backups", "ide", "plugins",
    "dist", "build", "target", ".next", "vendor", "venv", ".venv",
    "state",
}

# The files defining the mapping. Each states both names by definition.
MAPPING_OWNERS = {"intelligence-naming.py", "vendor-intelligence.py",
                  ".config-sync-removed.json"}

# A file carrying this marker builds the aliases and so has to name them.
ALIAS_MARKER = "intelligence-naming: names the alias by design"

# Files the harness writes and owns. Their paths resolve through the aliases, and
# a rewrite is overwritten the next time the harness saves one.
HARNESS_FILES = {
    "launcher-settings.json", "mcp-needs-auth-cache.json", "policy-limits.json",
    ".claude.json", ".credentials.json", "history.jsonl", ".last-cleanup",
}

# Snapshots of an earlier tree. Their names record what was there at the time.
BACKUP_DIR = re.compile(r".*(?:^|-)backup(?:-|$).*")

CONTENT_PATTERNS = (
    (re.compile(r"~/\.claude(?![\w-])"), "~/.intelligence"),
    (re.compile(r"\$HOME/\.claude(?![\w-])"), "$HOME/.intelligence"),
    (re.compile(r"(?<![\w-])\.claude(?![\w-])"), ".intelligence"),
    (re.compile(r"(?<!\w)CLAUDE\.md(?!\w)"), "INTELLIGENCE.md"),
    (re.compile(r"(?<![\w-])claude-config(?![\w-])"), "intelligence"),
    (re.compile(r"~%2F\.claude(?![\w-])"), "~%2F.intelligence"),
    (re.compile(r"(?<![\w-])vendor-claude(?![\w-])"), "vendor-intelligence"),
    (re.compile(r"(?<![\w-])cloud-claude(?![\w-])"), "cloud-intelligence"),
    (re.compile(r"CLAUDE_(STATE_DIR|ROUTINE_FILE|TRANSCRIPT_PATH|SKIP_|ALLOW_)"),
     r"INTELLIGENCE_\1"),
)

# Extensions holding text a path can be named in.
TEXT_SUFFIXES = {
    "", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".sh", ".bash", ".zsh",
    ".py", ".js", ".cjs", ".mjs", ".ts", ".tsx", ".jsx", ".html", ".css", ".xml",
    ".cfg", ".ini", ".conf", ".env", ".gradle", ".properties", ".gitignore",
}

# Shell commands that bring a retired path into being: a creating verb naming
# one, or a redirect writing the legacy memory file.
BASH_CREATES = re.compile(
    r"(?:mkdir|touch|cp|mv|install|tee|git\s+mv|ln)\b[^;&|\n]*?"
    r"(?<![\w-])(?:\.claude(?![\w-])|CLAUDE\.md)"
    r"|>\s*[^\s;&|]*(?<![\w-])CLAUDE\.md"
)


def foreign(text):
    """Whether this text names something outside the intelligence namespace."""
    return any(tok in text for tok in FOREIGN)


def canonical_for(name):
    """The intelligence name for a path component, or None when it already is one."""
    return CANON.get(name)


def agent_worktree_root(entry):
    """True for a retired-name directory holding worktrees git has registered.

    The harness cuts each agent's worktree into a `worktrees` directory under
    the retired name and takes no setting that would change where. What sits
    there is checkouts rather than configuration, and every one is registered
    in the repository by absolute path, so renaming the directory detaches
    them and strands whatever is uncommitted inside.

    Registration is the whole test. A retired-name directory holding settings
    is still an offender, and this one stops being exempt the moment git no
    longer knows about the trees in it.
    """
    if entry.name not in CANON or not entry.is_dir():
        return False
    worktrees = entry / "worktrees"
    if not worktrees.is_dir():
        return False
    try:
        listed = subprocess.run(
            ["git", "-C", str(entry.parent), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if listed.returncode != 0:
        return False
    known = {
        line.split(" ", 1)[1].strip()
        for line in listed.stdout.splitlines()
        if line.startswith("worktree ")
    }
    children = [d for d in worktrees.iterdir() if d.is_dir()]
    return bool(children) and all(str(d.resolve()) in known for d in children)


def offenders(root):
    """Real files and directories under root carrying a legacy name."""
    root = Path(root)
    found = []
    if not root.exists():
        return found
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            if entry.name in SKIP_DIRS or BACKUP_DIR.match(entry.name):
                continue
            if canonical_for(entry.name) and not entry.is_symlink():
                if agent_worktree_root(entry):
                    continue
                found.append(entry)
                continue
            if entry.is_dir() and not entry.is_symlink():
                stack.append(entry)
    return sorted(found)


def text_files(root):
    """Every text file under root that is not vendored, generated, or a snapshot."""
    root = Path(root)
    out = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            if entry.name in SKIP_DIRS or BACKUP_DIR.match(entry.name):
                continue
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name == ".intelligence" and entry != INTELLIGENCE:
                    continue
                stack.append(entry)
            elif (entry.suffix in TEXT_SUFFIXES
                  and entry.name not in MAPPING_OWNERS
                  and not harness_owned(entry)):
                out.append(entry)
    return sorted(out)


def harness_owned(path):
    """Whether the harness writes this file rather than the config does.

    The config directory's top level is where the harness drops its state as
    JSON. Only the two settings files there are authored.
    """
    if path.name in HARNESS_FILES:
        return True
    return (path.parent == INTELLIGENCE and path.suffix == ".json"
            and path.name not in ("settings.json", "settings.local.json"))


# Inside the config directory, only a few trees are written here. The rest is
# harness state, caches, clones of the mirrors, and third-party bundles, none of
# which this config can rename and all of which it keeps rediscovering one file
# at a time - each rediscovery landing as a container that will not launch.
#
# So membership is stated rather than subtracted: a file under the config
# directory is checked when it sits in a tree this config authors, and is
# otherwise none of its business. Outside the config directory nothing changes,
# because a checkout is all ours.
AUTHORED_TREES = ("skills", "tools", "scripts")
AUTHORED_FILES = ("settings.json", "settings.local.json", "INTELLIGENCE.md")
# Third-party skills, kept current by the skills sync rather than written here.
FOREIGN_TREES = (("skills", "synced"),)

_MIRROR_SKILLS = {}


def mirror_skills():
    """The skill names the mirror ships, or None where no checkout is on disk.

    The retired name is a symlink onto this tree, so a skill the harness or a
    plugin installs under it lands in `skills/` beside the ones written here.
    Those document the harness, which means naming the harness's own paths, and
    a rename would rewrite a file this config does not keep: the next refresh
    puts the retired name straight back.

    Read from the mirror rather than listed, because listing them is what the
    note above `AUTHORED_TREES` refuses - each one discovered a container late,
    on the check that was meant to prove the container was whole. A desk holds
    the checkout under state, a container is handed one beside the installed
    tree, and a machine holding neither answers None so that nothing changes.

    The two paths are read at call time rather than bound at import, because the
    cases redirect the tree globals and a path fixed at import would walk the
    real config directory instead of the fixture.
    """
    if INTELLIGENCE in _MIRROR_SKILLS:
        return _MIRROR_SKILLS[INTELLIGENCE]
    names = None
    for skills in (INTELLIGENCE / "state" / ".config-sync-repo" / "skills",
                   HOME / "intelligence" / "skills"):
        try:
            found = {entry.name for entry in skills.iterdir() if entry.is_dir()}
        except (OSError, PermissionError):
            continue
        if found:
            names = found
            break
    _MIRROR_SKILLS[INTELLIGENCE] = names
    return names


def authored(path):
    """Whether this config wrote the file, and can therefore answer for its names."""
    try:
        rel = path.resolve().relative_to(INTELLIGENCE)
    except ValueError:
        return True
    parts = rel.parts
    if len(parts) == 1:
        return parts[0] in AUTHORED_FILES
    if parts[0] not in AUTHORED_TREES:
        return False
    for foreign in FOREIGN_TREES:
        if parts[:len(foreign)] == foreign:
            return False
    if parts[0] == "skills":
        shipped = mirror_skills()
        if shipped is not None and parts[1] not in shipped:
            return False
    return True


def content_offenders(root):
    """Files under root whose text still names a retired path, with the hits."""
    found = []
    for path in text_files(root):
        if not authored(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits = content_hits(text)
        if hits:
            found.append((path, hits))
    return found


def repo_root_of(cwd):
    """The git checkout containing cwd, or None outside one."""
    if not cwd:
        return None
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        return None
    root = Path(r.stdout.strip())
    return root if root != HOME else None


def tracked_by_git(path):
    """Whether git tracks this path, so the rename goes through git."""
    r = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=str(path.parent), capture_output=True, text=True,
    )
    return r.returncode == 0


def convert_one(path):
    """Renames one path to its intelligence name and leaves the harness alias."""
    target = path.parent / CANON[path.name]
    if target.exists() and not target.is_symlink():
        return "%s already exists beside %s" % (target.name, path.name)
    if tracked_by_git(path):
        subprocess.run(["git", "mv", path.name, target.name],
                       cwd=str(path.parent), capture_output=True, text=True)
    if path.exists():
        path.rename(target)
    alias = path
    if alias.is_symlink():
        alias.unlink()
    os.symlink(target.name, alias)
    return None


FOREIGN_RE = re.compile("|".join(re.escape(t) for t in FOREIGN))
MASK = "\x00%d\x00"


def mask_foreign(line):
    """The line with every upstream name replaced by a placeholder, and the names."""
    kept = []

    def take(m):
        kept.append(m.group(0))
        return MASK % (len(kept) - 1)

    return FOREIGN_RE.sub(take, line), kept


def unmask(line, kept):
    for i, token in enumerate(kept):
        line = line.replace(MASK % i, token)
    return line


def rewrite_content(text):
    """Text with every legacy path replaced and every upstream name left alone."""
    out, changed = [], 0
    for line in text.splitlines(keepends=True):
        masked, kept = mask_foreign(line)
        new = masked
        for pattern, repl in CONTENT_PATTERNS:
            new = pattern.sub(repl, new)
        new = unmask(new, kept)
        if new != line:
            changed += 1
        out.append(new)
    return "".join(out), changed


def content_hits(text):
    """Line numbers and text of every legacy path in this content."""
    hits = []
    if ALIAS_MARKER in text:
        return hits
    for n, line in enumerate(text.splitlines(), 1):
        masked, _ = mask_foreign(line)
        for pattern, _repl in CONTENT_PATTERNS:
            m = pattern.search(masked)
            if m:
                hits.append((n, m.group(0), line.strip()[:100]))
                break
    return hits


# A heredoc opener, and the file its redirection names. Content authored this way
# reaches disk without ever passing through Write or Edit, so the content check
# that guards those tools never sees it.
HEREDOC_OPEN = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
HEREDOC_TARGET = re.compile(r">>?\s*([^\s<>|&;]+)")


def heredoc_bodies(command):
    """Each heredoc in a shell command, as (target file, body text)."""
    lines = command.splitlines()
    out, i = [], 0
    while i < len(lines):
        opener = HEREDOC_OPEN.search(lines[i])
        if not opener:
            i += 1
            continue
        target = HEREDOC_TARGET.search(lines[i].split("<<")[0])
        body, i = [], i + 1
        while i < len(lines) and lines[i].strip() != opener.group(2):
            body.append(lines[i])
            i += 1
        out.append((target.group(1) if target else "", "\n".join(body)))
        i += 1
    return out


def refuse(lines):
    print("\n".join(lines), file=sys.stderr)
    return 2


def path_refusal(path, canonical):
    return refuse([
        "BLOCKED: %s is a retired name." % path,
        "",
        "  write %s instead" % canonical,
        "",
        "The harness resolves the old names, so they stay as symlinks onto the",
        "intelligence-named file that holds the content:",
        "",
        "  %s convert <repo>" % SELF,
        "",
        "%s=1 overrides this." % ESCAPE,
    ])


def content_refusal(where, hits):
    lines = ["BLOCKED: %s writes retired configuration paths." % where, ""]
    for n, token, text in hits[:8]:
        lines.append('  line %d: "%s"' % (n, token))
        lines.append("    %s" % text)
    lines += [
        "",
        "Configuration lives under ~/.intelligence and the memory file is",
        "INTELLIGENCE.md. Name those, not the aliases the harness resolves.",
        "",
        "%s=1 overrides this." % ESCAPE,
    ]
    return refuse(lines)


def offending_component(path):
    """The first retired component of this path that is not a live symlink."""
    p = Path(path)
    for i, part in enumerate(p.parts):
        canonical = canonical_for(part)
        if not canonical:
            continue
        prefix = Path(*p.parts[:i + 1])
        if prefix.is_symlink():
            continue
        return part, canonical
    return None, None


def cmd_scan(argv):
    root = Path(argv[0]).expanduser() if argv else Path.cwd()
    paths = offenders(root)
    texts = content_offenders(root)
    for path in paths:
        print("path     %s" % path)
    for path, hits in texts:
        print("content  %s (%d)" % (path, len(hits)))
        for n, token, _ in hits[:3]:
            print("           line %d: %s" % (n, token))
    print("%d retired path(s), %d file(s) naming one, under %s"
          % (len(paths), len(texts), root))
    return 1 if paths or texts else 0


def convert_tree(root):
    """Renames every retired path under root and rewrites every mention of one."""
    renamed = rewritten = 0
    for path in offenders(root):
        problem = convert_one(path)
        if problem:
            print("  SKIP %s (%s)" % (path, problem))
            continue
        print("  ok   %s -> %s" % (path, CANON[path.name]))
        renamed += 1
    for path, _ in content_offenders(root):
        text = path.read_text(encoding="utf-8")
        new, changed = rewrite_content(text)
        if not changed:
            continue
        path.write_text(new, encoding="utf-8")
        print("  ok   %s (%d line%s)" % (path, changed, "" if changed == 1 else "s"))
        rewritten += 1
    return renamed, rewritten


def cmd_convert(argv):
    root = Path(argv[0]).expanduser() if argv else Path.cwd()
    renamed, rewritten = convert_tree(root)
    if not renamed and not rewritten:
        print("nothing to convert under %s" % root)
    else:
        print("%d renamed, %d rewritten" % (renamed, rewritten))
    return 0


CHECKOUT_ROOTS = (HOME / "Development" / "IdeaProjects", HOME / "Development" / "WebstormProjects", HOME / "Development" / "worktrees")


def checkouts():
    """Every git checkout under the directories projects are held in."""
    found = []
    for root in CHECKOUT_ROOTS:
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if (entry / ".git").exists():
                found.append(entry)
            elif entry.is_dir():
                found.extend(c for c in sorted(entry.iterdir())
                             if (c / ".git").exists())
    return found


def cmd_sweep(argv):
    repos = checkouts()
    renamed = rewritten = 0
    for repo in repos:
        if not offenders(repo) and not content_offenders(repo):
            continue
        print("%s" % repo)
        a, b = convert_tree(repo)
        renamed += a
        rewritten += b
    print("%d renamed, %d rewritten across %d checkout(s)"
          % (renamed, rewritten, len(repos)))
    return 0


HOOKS = (
    ("SessionStart", None, "%s install" % SELF),
    ("PreToolUse", "Write|Edit|NotebookEdit", "%s guard-edit" % SELF),
    ("PreToolUse", "Bash", "%s guard-bash" % SELF),
    ("Stop", "*", "%s guard-stop" % SELF),
)


def alias_pairs():
    """Each name the harness resolves, and the tree it points onto."""
    memory = next(k for k in CANON if k.endswith(".md") and "local" not in k)
    directory = next(k for k in CANON if k.startswith("."))
    return (
        (HOME / directory, INTELLIGENCE),
        (INTELLIGENCE / memory, INTELLIGENCE / CANON[memory]),
    )


def alias_broken():
    """Aliases that do not resolve onto the tree holding the content."""
    bad = []
    for alias, target in alias_pairs():
        if not target.exists():
            continue
        if not alias.is_symlink() or alias.resolve() != target.resolve():
            bad.append(alias)
    return bad


def ensure_aliases():
    """Puts the names the harness resolves onto the intelligence-named tree."""
    made = []
    for alias, target in alias_pairs():
        if not target.exists():
            continue
        if alias.is_symlink() and alias.resolve() == target.resolve():
            continue
        if alias.exists() and not alias.is_symlink():
            continue
        if alias.is_symlink():
            alias.unlink()
        os.symlink(target.name if alias.parent == target.parent else str(target), alias)
        made.append(str(alias))
    return made


def cmd_aliases(argv):
    for alias, _ in alias_pairs():
        print(alias)
    return 0


def cmd_install(argv):
    settings = json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {}
    hooks = settings.setdefault("hooks", {})
    added = 0
    for event, matcher, command in HOOKS:
        entries = hooks.setdefault(event, [])
        present = any(
            h.get("command") == command
            for entry in entries for h in entry.get("hooks", [])
        )
        if present or hub_covers(entries):
            continue
        block = {"hooks": [{"type": "command", "command": command, "timeout": 15}]}
        if matcher:
            block["matcher"] = matcher
        entries.append(block)
        added += 1
    if added:
        SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")
    aliases = ensure_aliases()
    print("intelligence-naming: %d hook(s) added, %d already wired, %d alias(es) created"
          % (added, len(HOOKS) - added, len(aliases)))
    for alias in aliases:
        print("  %s" % alias)
    return 0


def hub_covers(entries):
    """Whether a dispatcher entry already carries this event's guards.

    guard-hub answers for the tool events and session-init for session start.
    A command of ours living behind either one is wired.
    """
    return any(("guard-hub.py" in h.get("command", "")
                or "session-init.py" in h.get("command", ""))
               for entry in entries for h in entry.get("hooks", []))


def wired():
    """Hook commands from HOOKS that settings.json does not carry.

    A dispatcher entry for an event hosts that event's guards, so a command of
    ours living behind one is wired, not missing.
    """
    if not SETTINGS.exists():
        return [c for _, _, c in HOOKS]
    settings = json.loads(SETTINGS.read_text())
    hooks = settings.get("hooks", {})
    missing = []
    for event, _, command in HOOKS:
        entries = hooks.get(event, [])
        if hub_covers(entries):
            continue
        if not any(h.get("command") == command
                   for entry in entries for h in entry.get("hooks", [])):
            missing.append(command)
    return missing


def cmd_verify(argv):
    missing = wired()
    broken = alias_broken()
    found = offenders(INTELLIGENCE)
    texts = content_offenders(INTELLIGENCE)
    for command in missing:
        print("unwired: %s" % command)
    for alias in broken:
        print("alias does not resolve: %s" % alias)
    for path in found:
        print("retired name: %s" % path)
    for path, hits in texts:
        print("names a retired path: %s (%d)" % (path, len(hits)))
    if not missing and not broken and not found and not texts:
        print("intelligence naming holds: hooks wired, aliases resolve, tree clean")
        return 0
    return 1


def cmd_guard_edit(argv):
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if os.environ.get(ESCAPE):
        return 0
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if path and not foreign(path):
        part, canonical = offending_component(path)
        if part:
            return path_refusal(path, canonical)
    body = "".join(
        str(tool_input.get(k) or "")
        for k in ("content", "new_string", "new_source")
    )
    if body and Path(path).name not in MAPPING_OWNERS:
        hits = content_hits(body)
        if hits:
            return content_refusal(path or "this edit", hits)
    return 0


def cmd_guard_bash(argv):
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if os.environ.get(ESCAPE):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    # A heredoc is how a file gets authored through the shell, so its body
    # answers to the content check that Write and Edit answer to. Without this
    # the same string is refused on one path and waved through on the other,
    # and the copy that got through took every cloud routine down for an hour
    # on 2026-08-28.
    for target, body in heredoc_bodies(command):
        if foreign(target) or Path(target).name in MAPPING_OWNERS:
            continue
        hits = content_hits(body)
        if hits:
            return content_refusal(target or "this heredoc", hits)
    for line in command.splitlines():
        if foreign(line) or line.lstrip().startswith("#"):
            continue
        if BASH_CREATES.search(line):
            return refuse([
                "BLOCKED: this command creates a retired configuration path.",
                "",
                "  %s" % line.strip()[:160],
                "",
                "Create `.intelligence/` or `INTELLIGENCE.md` and let the name the",
                "harness resolves be a symlink onto it:",
                "",
                "  %s convert <repo>" % SELF,
                "",
                "%s=1 overrides this." % ESCAPE,
            ])
    return 0


def cmd_guard_stop(argv):
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    if os.environ.get(ESCAPE):
        return 0
    roots = [INTELLIGENCE]
    repo = repo_root_of(payload.get("cwd"))
    if repo:
        roots.append(repo)
    found = []
    for root in roots:
        found.extend(offenders(root))
    missing = wired()
    if not found and not missing:
        return 0
    lines = ["BLOCKED: this session leaves the intelligence naming broken.", ""]
    for path in sorted(set(found))[:10]:
        lines.append("  %s -> %s" % (path, CANON[path.name]))
    for command in missing:
        lines.append("  hook not wired: %s" % command)
    lines += [
        "",
        "  %s convert <path>" % SELF,
        "  %s install" % SELF,
        "",
        "%s=1 overrides this." % ESCAPE,
    ]
    return refuse(lines)


COMMANDS = {
    "scan": cmd_scan,
    "convert": cmd_convert,
    "sweep": cmd_sweep,
    "aliases": cmd_aliases,
    "install": cmd_install,
    "verify": cmd_verify,
    "guard-edit": cmd_guard_edit,
    "guard-bash": cmd_guard_bash,
    "guard-stop": cmd_guard_stop,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
