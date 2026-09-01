#!/usr/bin/env python3
"""One spawn at session start, however many tools answer to it.

Wired one by one, every tool with an `install` verb starts an interpreter before
the first prompt, and each one reads the same settings file to decide it has
nothing to do. The wiring only changes when that file changes, so this records
what it hashed to after the last sweep and runs the installers when the hash has
moved. A session that starts with the wiring intact costs one read.

The tools that do real work run either way, behind the gate each one applies to
itself: the cloud refresh is a no-op outside a container, the worktree prune is
a no-op outside a repository, and the run prune has nothing to answer for while
every pointer is fresh. Reading those conditions here costs a stat apiece and
saves the process each would have spent reaching the same answer.

  run        the session-start sweep
  install    put this dispatcher in settings.json, replacing what it covers
  status     what would run, and why

INTELLIGENCE_SESSION_FORCE=1 runs the installers whatever the hash says.
"""
import contextlib
import hashlib
import json
import os

try:
    import fcntl
except ImportError:
    fcntl = None
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
INTELLIGENCE = Path(__file__).resolve().parent.parent
TOOLS = INTELLIGENCE / "tools"
SCRIPTS = INTELLIGENCE / "scripts"
SETTINGS = INTELLIGENCE / "settings.json"
STAMP = INTELLIGENCE / "state" / "session-init.json"

# The tools whose install verb puts their own rows back in the settings file.
# Removing a hook by hand buys one session at most, because the next start sees
# a hash it does not recognise and runs every one of these.
INSTALLERS = [
    ("intelligence-naming.py", "install"),
    ("ai-attribution-guard.py", "install"),
    ("chrome-guard.py", "install"),
    ("concise-guard.py", "install"),
    ("remote-access.py", "install"),
    ("plain-brief-guard.py", "install"),
    ("checklist-runs.py", "install"),
]


def in_container():
    return os.environ.get("CLAUDE_CODE_REMOTE") == "true"


def in_repository(cwd):
    here = Path(cwd or os.getcwd()).resolve()
    for path in [here, *here.parents]:
        if (path / ".git").exists():
            return True
    return False


def stale_run_pointer():
    """Whether any checklist run pointer is old enough to be worth pruning.

    A pointer rewritten in the last twelve hours belongs to a session somebody
    is still in and is never touched, so a tree holding only fresh ones has
    nothing for the prune to do.
    """
    root = INTELLIGENCE / "state"
    if not root.is_dir():
        return False
    cutoff = time.time() - 12 * 3600
    for kind in ("design", "seo", "perf", "stack", "db", "google"):
        for pointer in root.glob("%s-runs/*current*.json" % kind):
            try:
                if pointer.stat().st_mtime < cutoff:
                    return True
            except OSError:
                continue
    return False


def tasks(cwd):
    """The work that runs whatever the wiring hash says, each behind its gate."""
    return [
        (["bash", str(SCRIPTS / "cloud-refresh.sh")], in_container(),
         "cloud container"),
        ([str(SCRIPTS / "git-develop-base-guard.sh"), "session"], True, "always"),
        (["bash", str(SCRIPTS / "prune-worktrees.sh")], in_repository(cwd),
         "inside a repository"),
        ([str(TOOLS / "config-sync.py")], True, "always"),
        ([str(TOOLS / "remote-access.py"), "announce"], True, "always"),
        ([str(TOOLS / "checklist-runs.py"), "prune"], stale_run_pointer(),
         "a run pointer older than twelve hours"),
    ]


def fingerprint():
    try:
        return hashlib.sha256(SETTINGS.read_bytes()).hexdigest()
    except OSError:
        return ""


def recorded():
    try:
        return json.loads(STAMP.read_text()).get("settings", "")
    except (OSError, ValueError):
        return ""


def record(value):
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text(json.dumps({"settings": value}, indent=2) + "\n")


def spawn(argv, payload):
    try:
        done = subprocess.run(argv, input=payload, capture_output=True,
                              text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        sys.stderr.write("session-init: %s: %s\n" % (argv[0], exc))
        return 0
    if done.stdout:
        sys.stdout.write(done.stdout)
    if done.stderr:
        sys.stderr.write(done.stderr)
    return done.returncode


def run():
    payload = sys.stdin.read() if not sys.stdin.isatty() else "{}"
    try:
        cwd = (json.loads(payload or "{}") or {}).get("cwd") or os.getcwd()
    except ValueError:
        cwd = os.getcwd()

    for argv, gate, _why in tasks(cwd):
        if gate:
            spawn(argv, payload)

    current = fingerprint()
    if os.environ.get("INTELLIGENCE_SESSION_FORCE") == "1" \
            or current != recorded():
        for name, verb in INSTALLERS:
            spawn([str(TOOLS / name), verb], payload)
        # An installer puts its own session row back as well as the rows it
        # shares with the dispatcher, so the fold runs again after them. Without
        # it the file ends every sweep holding rows this dispatcher already
        # covers, the hash never settles, and the installers run every session.
        fold()
        record(fingerprint())
    return 0


# The tools whose own rows the two dispatchers stand in for. A guard reached
# through guard-hub belongs here as much as an installer reached through this
# one: both put their rows back when they run, and the fold is what settles the
# file afterwards.
COVERED = tuple(name for name, _ in INSTALLERS) + (
    "cloud-refresh.sh", "git-develop-base-guard.sh", "prune-worktrees.sh",
    "config-sync.py", "remote-access.py", "checklist-runs.py",
    "plain-brief-guard.py", "concise-guard.py")

def portable(tool, verb):
    """A hook command in the form the sync would rewrite this one into.

    settings.json lands in every container, and a command naming one machine's
    home exits 127 there. The sync normalises any absolute path under a home
    directory into this guarded form, so writing the absolute one here would
    have the sync rewrite it every session, move the settings hash, and run the
    installers this dispatcher exists to skip.

    A tree outside the home directory has no such form and keeps its own path,
    which is the case a checkout or a test target runs in.
    """
    target = TOOLS / tool
    try:
        tail = target.relative_to(HOME)
    except ValueError:
        return "%s %s" % (target, verb)
    return ('[ -e "$HOME/%s" ] || exit 0; exec "$HOME/%s" %s'
            % (tail, tail, verb))


# One row per event: the dispatcher that answers for everything wired behind it.
CANONICAL = {
    "PreToolUse": portable("guard-hub.py", "pre"),
    "PostToolUse": portable("guard-hub.py", "post"),
    "Stop": portable("guard-hub.py", "stop"),
    "UserPromptSubmit": portable("guard-hub.py", "prompt"),
    "SessionStart": portable("session-init.py", "run"),
}


@contextlib.contextmanager
def settings_held():
    """Exclusive hold over the settings file for one read-and-write.

    Every writer of this file loads it whole, edits it in memory and saves it
    back, so two sessions starting together resolve to whichever finished last
    and the other's edit is gone with nothing recording that it happened. The
    hold orders them. Where it cannot be taken the write goes ahead anyway: a
    session that refused to wire itself is worse than one that raced.
    """
    if fcntl is None:
        yield False
        return
    try:
        handle = open(SETTINGS.parent / ".settings-write-lock", "a+")
    except OSError:
        yield False
        return
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield True
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        handle.close()


def fold():
    """Reduce the hooks block to one dispatcher per event.

    A command is recognised by the tool name inside it rather than by the whole
    string, because the sync rewrites an absolute path to a portable one and a
    match on the full command would stop recognising the row it just wrote.
    Anything naming no covered tool is left where it is, so a hook from
    somewhere else survives the fold.
    """
    with settings_held():
        return _fold_locked()


def _fold_locked():
    settings = json.loads(SETTINGS.read_text())
    hooks = settings.setdefault("hooks", {})
    dropped = 0

    for event, canonical in CANONICAL.items():
        kept = []
        for row in hooks.get(event) or []:
            entries = []
            for entry in row.get("hooks") or []:
                command = entry.get("command", "")
                if "guard-hub.py" in command or "session-init.py" in command:
                    continue
                if any(name in command for name in COVERED):
                    dropped += 1
                    continue
                entries.append(entry)
            if entries:
                row["hooks"] = entries
                kept.append(row)
        kept.insert(0, {"matcher": "*", "hooks": [
            {"type": "command", "command": canonical}]})
        hooks[event] = kept

    tmp = SETTINGS.with_name(SETTINGS.name + ".tmp.%d" % os.getpid())
    tmp.write_text(json.dumps(settings, indent=2) + "\n")
    os.replace(tmp, SETTINGS)
    return dropped


def install():
    dropped = fold()
    print("session-init: wired, %d hook(s) folded in" % dropped)
    record(fingerprint())
    return 0


def status():
    cwd = os.getcwd()
    print("settings hash  %s" % (fingerprint() or "unreadable")[:16])
    print("recorded       %s" % (recorded() or "none")[:16])
    same = fingerprint() == recorded()
    print("installers     %s" % ("skipped, wiring unchanged" if same
                                 else "would run, wiring moved"))
    for argv, gate, why in tasks(cwd):
        print("%-14s %s (%s)" % (Path(argv[-2] if argv[0] == "bash" else argv[0]).name,
                                 "run" if gate else "skip", why))
    return 0


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else "run"
    if verb == "run":
        return run()
    if verb == "install":
        return install()
    if verb == "status":
        return status()
    sys.stderr.write(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
