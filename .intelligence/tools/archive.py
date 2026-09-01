#!/usr/bin/env python3
"""What a chat still holds at the moment somebody closes it.

Archiving a chat ends the one process that knows what the chat was doing. The
transcript survives, so nothing written down is lost, and everything not written
down goes with it: a worktree cut and never landed, a pull request opened and
never watched, a skill edited and never mirrored, and the sentence somebody had
to say twice because no mechanism catches it.

Those are three different problems and all three are answered here. Unfinished
work is a matter of fact and gets measured -- the trees the chat touched, the
branches it cut, the pull requests it opened, the config it edited, and the
files it changed without either pass running over them. A dropped ask is a
matter of arithmetic: an opening message carries several things, the run carries
out some of them, and the words of the rest never surface again. A lesson is a
matter of reading, and the transcript is where it is legible: a correction is
somebody supplying by hand what a mechanism should supply, a refusal is a
mechanism that fired and went on firing, and a collision is two mechanisms
refusing one reply on terms that cannot both be met.

The dropped ask leads all of them. The other readings are about how the work was
done and it is the only one about whether it was done, and the person who typed
the message has already paid for it once.

A refusal that fires once, is obeyed and never returns is the common case and
raises nothing, but the draft it turned down and the draft that replaced it are
the clearest statement anywhere of what the machine wanted. Those are kept
against the ground rather than read and dropped, so a wall met once in each of
several chats becomes visible to a run that was present for none of them.

Scope is what keeps this from crying wolf. A machine-wide sweep refuses over a
stale branch in a repository the chat never opened, and a gate that refuses over
somebody else's mess gets switched off within a day. So the reading is held to
the directories, repositories and branches the transcript actually names, and
--all widens it for a run that wants the whole machine.

  archive.py check [--all] [--json] [--session ID]   work the chat still holds
  archive.py finish [--json] [--session ID]          what was asked and not done
  archive.py polish [--files|--mark [path...]]       the passes the diff is owed
  archive.py harvest [--json] [--session ID]         what nothing enforces yet
  archive.py hand-off [<id>] [--session ID]          start the agent that fixes it
  archive.py close [--session ID]                    end the chat, either shape
  archive.py settle <id> --as built|context|declined --note "why"
  archive.py guard-archive                           PreToolUse over the archive
  archive.py guard-stop                              Stop hook over a chat left open

check and harvest exit non-zero while anything is outstanding, and guard-archive
refuses the archive call itself, so closing a chat over unfinished work is an
action the harness declines rather than a discipline anybody has to keep.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import shlex
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
TOOLS = Path(__file__).resolve().parent


def _shared():
    """The shared _lib module, loaded by path.

    Hooks and routines run this from arbitrary directories, so the module is
    found beside this file rather than through sys.path, with the installed
    tree as the fallback for a copy executed from elsewhere.
    """
    here = TOOLS / "_lib.py"
    path = here if here.is_file() else HOME / ".intelligence" / "tools" / "_lib.py"
    spec = importlib.util.spec_from_file_location("intelligence_tools_lib", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(stem):
    """A sibling tool as a module, found by path.

    The names carry hyphens and the tools run as scripts, so nothing about them
    is importable by name. Loading them anyway is what keeps one answer to how a
    correction is fingerprinted: the vocabulary, the stopwords and the hash all
    stay in the file that owns them, so a lesson raised here and a lesson raised
    by the window scan carry the same id.
    """
    beside = TOOLS / (stem + ".py")
    path = beside if beside.is_file() else \
        HOME / ".intelligence" / "tools" / (stem + ".py")
    spec = importlib.util.spec_from_file_location(
        "intelligence_" + stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_lib = _shared()
state_root = _lib.state_root

NOW = lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat()

TRANSCRIPTS = Path(os.environ.get("INTELLIGENCE_TRANSCRIPTS")
                   or HOME / ".intelligence" / "projects")

# The app keeps one record per chat here, and it is the only thing that
# says whether a chat is one the app knows about. A headless session has
# no file in this tree, which is the fact the close turns on.
SESSIONS = Path(os.environ.get("INTELLIGENCE_SESSION_STORE")
                or HOME / "Library" / "Application Support" / "Claude"
                / "claude-code-sessions")

WORKTREES = HOME / "Development" / "worktrees"
CONFIG = str((HOME / ".intelligence").resolve())

# A correction repeated inside one sitting is the signal this tool trades on.
# The window scan needs two sessions before it will speak, because across
# sessions one telling is an incident; inside a single transcript the second
# telling is already the whole evidence, and waiting for a third means the chat
# closes before anything is raised.
MIN_REPEATS = 2

# A guard that fires twice in one sitting is not a missing mechanism, since the
# mechanism is what fired. It is missing context: something the run needed to
# know before it acted and had to learn by being refused.
CONTEXT_REPEATS = 2

# Two mechanisms refusing one reply on different grounds need no repeat. A
# correction told once could be a slip of the moment and a guard that fires once
# is a guard doing its job, so both wait for a second telling before they mean
# anything. A collision is already complete on its first occurrence: both
# demands are on record, in full, along with the drafts that failed to satisfy
# them. Waiting for a repeat waits for another run to walk into the same
# contradiction and lose the same hour deciding which side to take.
COLLISION_GROUNDS = 2

# How many separate chats have to meet the same ground before it is raised on
# that evidence alone. Inside one sitting a refusal has to repeat to mean
# anything; across sittings the repeat is the evidence, and nobody was present
# for all of it. Two is a coincidence in a busy week. Three is a wall.
RECURRENCE_CHATS = 3

# How much of a draft is worth keeping beside the ground that refused it. The
# pair is read to work out what the machine wanted, and the opening of a reply
# is where its shape is decided.
DRAFT_KEEP = 600

# Findings are read to a person who is closing a chat, so the list has to fit on
# a screen or it gets skimmed past the thing that mattered.
SHORTLIST = 12

# Paths worth resolving out of a shell command. Anything shorter than a home
# directory reference is noise, and a match only becomes a repository when git
# says so.
PATHS = re.compile(r"(?:~|/Users/[A-Za-z0-9._-]+)/[A-Za-z0-9._/-]{2,}")

# The same file named from inside its own directory. Nobody working in a tree
# types the whole path to it, so a reading that takes only absolute paths sees
# the commands that set a directory up and none of the ones that did the work.
# A match counts only where the file it names is really there.
RELATIVE = re.compile(r"(?<![\w/.-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)")

# Where a command put itself before it named anything. The directory stamped on
# a row is where the session is, and a command opening with a move is working
# somewhere else for the rest of its length.
MOVED = re.compile(r"(?:^|[;&|]\s*)cd\s+['\"]?((?:~|/)[A-Za-z0-9._/-]+)")

PR_URL = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)")

# The three shapes a refusal takes in a transcript. A PreToolUse denial arrives
# as a tool result, stop feedback as a plain user turn, and a stop summary as a
# system row; reading only the last of those sees a fraction of what refused.
STOP_FEEDBACK = re.compile(r"^\s*stop hook feedback", re.I)

# The gate reporting itself is not a lesson. Each refusal it issues would
# otherwise count toward a candidate, so a chat it blocked twice could never
# reach an ending: the block becomes the reason for the next block.
OWN_BLOCK = "the chat is still holding something"

CANDIDATE_STATES = ("built", "context", "declined", "done")

# A handed-off lesson belongs to the chat opened on it, which carries the brief.
# It stays unsettled in the ledger and stops being raised, because a gate that
# goes on refusing after the hand-off leaves only a settle that claims work
# nobody did.
HANDED_OFF = "handed-off"

ANSWERED = CANDIDATE_STATES + (HANDED_OFF,)


class Unreadable(Exception):
    """The chat that was named cannot be read on this machine."""


def ledger_path():
    return state_root() / "archive" / "ledger.json"


def read_ledger():
    try:
        return json.loads(ledger_path().read_text())
    except (OSError, ValueError):
        return {"candidates": {}}


def save_ledger(ledger):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _lib.write_atomic(path, json.dumps(ledger, indent=2, sort_keys=True) + "\n")


def evidence_path():
    return state_root() / "archive" / "evidence.json"


def read_evidence():
    try:
        return json.loads(evidence_path().read_text())
    except (OSError, ValueError):
        return {"grounds": {}}


def save_evidence(store):
    path = evidence_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _lib.write_atomic(path, json.dumps(store, indent=2, sort_keys=True) + "\n")


def keep_evidence(session, marks):
    """Hold what one refusal wanted, against the chat that met it.

    A guard that refuses once, is obeyed, and never fires again leaves nothing
    behind: the chat closes, the reading finds no repeat, and the pair of drafts
    that says exactly what the machine wanted goes with it. That pair is the
    clearest statement on this machine of what right looked like, and it is
    thrown away every time.

    Keeping it costs a line and turns a single firing into evidence. The same
    ground met in three separate chats is a lesson nobody had to be present for,
    which is the only kind that survives the chats it was learned in.

    Keyed by ground and then by chat, so a guard rerun over a transcript it has
    already read rewrites what it wrote rather than counting it again.
    """
    if not marks:
        return
    store = read_evidence()
    grounds = store.setdefault("grounds", {})
    for mark, seen in marks.items():
        held = grounds.setdefault(mark, {"chats": {}})
        held["ground"] = seen["ground"]
        held["chats"][session] = {
            "at": NOW(), "refused": seen["refused"], "accepted": seen["accepted"]}
    save_evidence(store)


def git(cwd, *args, timeout=60):
    """Git's stdout, stripped, or None where the command failed."""
    try:
        done = subprocess.run(["git", "-C", str(cwd), *args],
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def here_session(payload=None):
    """The session being read, from a hook payload where there is one."""
    if payload:
        found = payload.get("session_id")
        if found:
            return found
    return os.environ.get("CLAUDE_CODE_SESSION_ID") or ""


def transcript_for(session, payload=None):
    """The transcript file of one session, or None where it cannot be placed.

    A hook payload names the file outright and is trusted over reconstruction,
    because the directory is fixed when the session opens while the working
    directory can move under it afterwards.
    """
    if payload:
        named = payload.get("transcript_path")
        if named and Path(named).is_file():
            return Path(named)
    if not session:
        return None
    direct = list(TRANSCRIPTS.glob("*/%s.jsonl" % session))
    return direct[0] if direct else None


def rows_of(session, payload=None):
    """The rows of one transcript, refusing to answer where there are none.

    A session id off by a character places no file, an absent file yields no
    rows, and no rows read exactly like a chat that closed clean. That is the
    one reading this tool cannot afford to get wrong, so an absence is raised
    rather than reported as a result.
    """
    path = transcript_for(session, payload)
    if path is None:
        raise Unreadable("no transcript for %s" % (session or "the chat"))
    return _lib.read_transcript(path)


# --------------------------------------------------------------- the footprint


def paths_in(text, cwd):
    """Every path one command names, absolute or named from where it stands.

    Nobody working in a tree types the whole path to a file in it, so a reading
    that takes only absolute paths sees the commands that set a directory up
    and none of the ones that did the work. A relative match counts only where
    the file it names is really there.
    """
    out = {os.path.expanduser(hit) for hit in PATHS.findall(text)}
    bases = [cwd] if cwd else []
    bases.extend(os.path.expanduser(one) for one in MOVED.findall(text))
    for base in bases:
        for hit in RELATIVE.findall(text):
            beside = Path(base) / hit
            if beside.exists():
                out.add(str(beside))
    return out


def footprint(rows):
    """Every directory, repository and pull request one transcript names.

    Scope is the difference between a gate that gets read and a gate that gets
    disabled, so the sweep measures what the chat reached and nothing else. A
    path reaches this set from three places: the working directory stamped on
    every row, an absolute path inside a shell command, and a pull request URL
    printed by one.
    """
    paths, prs = set(), set()
    for row in rows:
        cwd = row.get("cwd")
        if cwd:
            paths.add(cwd)
        for text in _commands(row):
            paths |= paths_in(text, cwd)
            for slug, number in PR_URL.findall(text):
                prs.add((slug, number))
        result = row.get("toolUseResult") or {}
        if isinstance(result, dict):
            for slug, number in PR_URL.findall(str(result.get("stdout") or "")):
                prs.add((slug, number))
    return paths, prs


def _commands(row):
    """The shell commands and file paths one row carries, as raw text."""
    message = row.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    out = []
    for part in content:
        if not isinstance(part, dict) or part.get("type") != "tool_use":
            continue
        given = part.get("input") or {}
        for key in ("command", "file_path", "path", "cwd"):
            value = given.get(key)
            if isinstance(value, str):
                out.append(value)
    return out


def repos_of(paths):
    """The repository roots behind a set of paths, deduped by realpath."""
    roots = {}
    for raw in sorted(paths):
        candidate = Path(raw)
        while candidate != candidate.parent and not candidate.exists():
            candidate = candidate.parent
        if not candidate.is_dir():
            candidate = candidate.parent
        if not candidate.is_dir():
            continue
        root = git(candidate, "rev-parse", "--show-toplevel")
        if not root:
            continue
        real = str(Path(root).resolve())
        roots.setdefault(real, Path(real))
    return sorted(roots.values(), key=str)


def every_tree():
    """Every checkout on the machine, for a run that asked for all of it.

    Worktrees are left to the walk that owns them, which reports the branch and
    the pull request behind each one. Counted here as well, a tree holding work
    is named twice under two headings that disagree about what it is.
    """
    roots = {}
    for base in (HOME / "Development",):
        if not base.is_dir():
            continue
        for found in base.rglob(".git"):
            root = found.parent
            if root == WORKTREES or WORKTREES in root.parents:
                continue
            roots.setdefault(str(root.resolve()), root)
    return sorted(roots.values(), key=str)


# -------------------------------------------------------------------- the work


def tree_findings(root):
    """What one checkout is holding that no remote has.

    Time is deliberately not a factor. The drift reading elsewhere waits a day
    before it calls a tree stranded, which is correct for a tree nobody is
    looking at and wrong here: work made minutes ago is exactly what a chat
    closing now is about to abandon.
    """
    found = []
    # An untracked directory counts once. Expanding it into every file inside
    # turns one vendored tree into six hundred findings and buries the three a
    # person closing a chat can act on.
    status = git(root, "status", "--porcelain")
    if status:
        found.append("%d uncommitted change(s)" % len(status.splitlines()))
    unpushed = git(root, "log", "--oneline", "HEAD", "--not", "--remotes")
    if unpushed:
        found.append("%d commit(s) no remote has" % len(unpushed.splitlines()))
    for name, label in ((".git/rebase-merge", "a rebase"),
                        (".git/rebase-apply", "a rebase"),
                        (".git/MERGE_HEAD", "a merge"),
                        (".git/CHERRY_PICK_HEAD", "a cherry-pick"),
                        (".git/BISECT_LOG", "a bisect")):
        if (root / name).exists():
            found.append("%s is part-way through" % label)
            break
    return found


def worktree_findings(roots, everything=False):
    """Worktrees holding work, walked directly rather than swept.

    The sweep prints what it removed and what it held and passes over a tree
    whose pull request has not landed yet, which is the state a chat closing now
    most needs named.
    """
    found = []
    if not WORKTREES.is_dir():
        return found
    wanted = None if everything else {str(r.resolve()) for r in roots}
    for repo in sorted(WORKTREES.iterdir()):
        if not repo.is_dir():
            continue
        for tree in sorted(repo.iterdir()):
            if not tree.is_dir():
                continue
            if wanted is not None and str(tree.resolve()) not in wanted:
                continue
            branch = git(tree, "rev-parse", "--abbrev-ref", "HEAD") or "(detached)"
            held = tree_findings(tree)
            landed = merged(tree, branch)
            if held:
                found.append("%s/%s on %s: %s"
                             % (repo.name, tree.name, branch, "; ".join(held)))
            elif landed is False:
                found.append("%s/%s on %s: open, no merged pull request"
                             % (repo.name, tree.name, branch))
    return found


def merged(root, branch):
    """Whether a branch has a merged pull request, or None where GitHub is mute."""
    try:
        done = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--state", "merged",
             "--json", "number"],
            cwd=str(root), capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    try:
        return bool(json.loads(done.stdout or "[]"))
    except ValueError:
        return None


def pr_findings(prs):
    """Pull requests the chat opened that have not landed."""
    found = []
    for slug, number in sorted(prs):
        try:
            done = subprocess.run(
                ["gh", "pr", "view", number, "--repo", slug,
                 "--json", "state,title,url"],
                capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if done.returncode != 0:
            continue
        try:
            pull = json.loads(done.stdout or "{}")
        except ValueError:
            continue
        if pull.get("state") == "OPEN":
            found.append("%s#%s is still open: %s"
                         % (slug, number, pull.get("title") or ""))
    return found


# The sync walks the whole config tree, and both the drift reading and the
# change set ask it the same question. Held for the life of the process, since
# two walks answer identically and the second one is paid for at the gate,
# where somebody is waiting on it.
_SYNC = []


def sync_drift():
    """What the sync says differs, as its own lines, read once.

    An empty list is a mirror in step and None is a mirror nothing could read.
    Answering both with the same value reports a tree that is fine as a tree
    nobody can see, which is the reading this whole tool is built to avoid.
    """
    if _SYNC:
        return _SYNC[0]
    tool = TOOLS / "config-sync.py"
    if not tool.is_file():
        _SYNC.append(None)
        return _SYNC[0]
    try:
        done = subprocess.run([sys.executable, str(tool), "check"],
                              capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError):
        _SYNC.append(None)
        return _SYNC[0]
    if done.returncode == 0:
        _SYNC.append([])
        return _SYNC[0]
    # The first line carries a count and the names are underneath it, so a
    # reading that keeps one line reports a number and no way to act on it.
    # The closing remedy is dropped instead, since the block already names it.
    _SYNC.append([line.strip()
                  for line in (done.stdout or done.stderr or "").splitlines()
                  if line.strip() and not line.lstrip().startswith("Run:")])
    return _SYNC[0]


def config_findings(paths):
    """Whether the mirror carries what the machine holds.

    A chat that edited a skill, a tool or a hook and closed before the mirror
    took it leaves a container installing last week's copy, and nothing about
    the local tree looks wrong afterwards.
    """
    detail = sync_drift()
    if detail is None:
        return ["the mirror could not be read"]
    if not detail:
        return []
    # The sync answers for the whole config tree, so a chat that edited one
    # skill is held to every file any chat has moved. Keeping only the names
    # this one touched is what stops work in progress elsewhere from refusing
    # an ending here.
    named = [one for one in detail[1:] if (Path(CONFIG) / one).exists()]
    if not named:
        return detail
    touched = {str(Path(one).resolve()) for one in paths}
    mine = sorted(one for one in named
                  if str((Path(CONFIG) / one).resolve()) in touched)
    if not mine:
        return []
    return ["%d file(s) differ from the mirror:" % len(mine)] + mine


def survey(session, payload=None, everything=False):
    """Everything one chat is about to leave behind, as findings by area."""
    rows = rows_of(session, payload)
    paths, prs = footprint(rows)
    roots = every_tree() if everything else repos_of(paths)
    areas = []
    held = []
    for root in roots:
        for line in tree_findings(root):
            held.append("%s: %s" % (root.name, line))
    if held:
        areas.append(("work no remote has", held))
    trees = worktree_findings(roots, everything)
    if trees:
        areas.append(("worktrees still holding work", trees))
    opened = pr_findings(prs)
    if opened:
        areas.append(("pull requests not landed", opened))
    if any(str(Path(p).resolve()).startswith(str(CONFIG)) for p in paths):
        drift = config_findings(paths)
        if drift:
            areas.append(("config not mirrored", drift))
    # The passes are owed on the diff the transcript names and on nothing else,
    # so the repositories it reached are the scope whether or not the run asked
    # for the whole machine. A sweep holding one chat to another chat's unpassed
    # diff is the gate switched off inside a day.
    owed = polish_findings(rows, repos_of(paths), session)
    if owed:
        areas.append(("changed code not passed over", owed))
    return areas


# ------------------------------------------------------------ what it changed


# Every file the chat wrote goes past /clean, and the half of it a person reads
# goes past /copywriting as well. The split is by extension rather than by
# judgement, because a judgement made per file is a judgement that gets skipped
# on the fortieth one, and a file's name already says whether anybody outside
# the repository ever reads its words.
READ_BY_PEOPLE = frozenset("""
.md .mdx .markdown .txt .html .htm .jsx .tsx .vue .svelte
""".split())

# What a pass has anything to say about. A file outside this set was changed by
# the chat and is nobody's writing: a lockfile, a manifest, a generated bundle.
PASSABLE = frozenset("""
.md .mdx .markdown .txt .html .htm .css .scss .sass .less .js .mjs .cjs .jsx
.ts .mts .cts .tsx .vue .svelte .py .rb .go .rs .java .kt .swift .sh .zsh
.sql .yml .yaml .toml
""".split())

# Changed by a chat without being written by one. Holding a pass open over a
# lockfile teaches the run to mark passes it did not do, which costs more than
# the file was ever worth.
NOT_WORK = re.compile(
    r"(?:^|/)(?:package-lock\.json|yarn\.lock|pnpm-lock\.yaml|\.DS_Store"
    r"|[^/]+\.min\.(?:js|css)|[^/]+\.map)$")

# Trees where nothing is ours to pass over. The mirror clone is the config tree
# copied, so a pass owed on a file inside it is owed twice: once on the original,
# which the config reading already names, and once on a duplicate that every
# machine's sync rewrites. Worse, its branch carries whatever any chat has synced
# since develop last moved, so the diff a chat is held to there is mostly other
# people's -- and a sweep that answers its own mirror finding by publishing then
# reads the publish back as unpassed work. The harness writes a fetched artifact
# into its own tool results the same way: a file that appeared because something
# was read, which no pass has anything to say about.
NOT_OURS = ("/node_modules/", "/.next/", "/dist/", "/build/", "/.venv/",
            "/venv/", "/__pycache__/", "/.git/", "/vendor/", "/coverage/",
            "/.config-sync-repo/", "/tool-results/")

# The calls that put words in a file. A file reached any other way is caught by
# the tree reading below instead.
WRITING_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")

# A shell writes a file without any tool naming it. The config tree is edited
# this way most of the time and answers to no git repository, so a reading that
# waits for a diff to appear covers none of it.
REDIRECTS = re.compile(
    r"(?:>>?|\btee\s+(?:-a\s+)?|\bsed\s+-i(?:\s+\S+)?\s+[^|;&]*?\s)"
    r"\s*['\"]?(?!/dev/)((?:~|/)[A-Za-z0-9._/-]{2,})")


def touched(rows):
    """Every file the chat wrote, taken from the calls that wrote them.

    Read from the tool inputs rather than from the working tree, because a chat
    that landed its work has no diff left and changed the code all the same.
    The tree reading is the other half and neither is complete alone: a file
    written by a heredoc never names itself in an input, and a file written and
    then reverted never reaches the tree.
    """
    out = set()
    for row in rows:
        message = row.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for part in content if isinstance(content, list) else []:
            if not isinstance(part, dict) or part.get("type") != "tool_use":
                continue
            if part.get("name") not in WRITING_TOOLS:
                continue
            given = part.get("input") or {}
            for key in ("file_path", "notebook_path", "path"):
                value = given.get(key)
                if isinstance(value, str) and value.strip():
                    out.add(os.path.expanduser(value.strip()))
        result = row.get("toolUseResult")
        if isinstance(result, dict):
            named = result.get("filePath") or result.get("file_path")
            if isinstance(named, str) and named.strip():
                out.add(os.path.expanduser(named.strip()))
        for command in _commands(row):
            for hit in REDIRECTS.findall(command):
                out.add(os.path.expanduser(hit))
    return out


def worth_passing(path):
    """Whether a changed file is one either pass has anything to say about.

    A ledger, a day plan and a published board are written by the machine
    rather than by anybody, and they move while a chat is open whatever the
    chat is doing. Holding a pass open over one puts a file nobody wrote in
    front of a person closing a chat, every time.
    """
    real = str(path)
    if real.startswith(str(state_root())) or \
            real.startswith(str(Path(CONFIG) / "state")):
        return False
    if any(part in real for part in NOT_OURS) or NOT_WORK.search(real):
        return False
    if not Path(real).is_file():
        return False
    return Path(real).suffix.lower() in PASSABLE


def at(row):
    """When a row happened, as seconds, or None where it does not say."""
    stamp = row.get("timestamp")
    if not isinstance(stamp, str) or not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def first_named(rows):
    """Every path the transcript names, against the moment it first named it.

    Half the trees on this machine answer to no repository, so there is no diff
    to read them out of. What is left is the clock, and the clock on its own
    says only that a file moved while the chat was open -- which is true of
    every file a routine rewrote in the same minutes.

    The moment the chat first named a file is what separates the two. A file
    that moved after that moved while the chat had it in hand. A file whose
    last change predates the first mention of it was somebody else's work,
    however recent, and the chat was reading it rather than writing it.
    """
    out, clock = {}, None
    for row in rows:
        clock = at(row) or clock
        cwd = row.get("cwd")
        for text in _commands(row):
            for one in paths_in(text, cwd):
                if one not in out and clock is not None:
                    out[one] = clock
    return out


def moved_after(named):
    """The files that changed after the chat first reached for them."""
    out = set()
    for raw, when in named.items():
        one = Path(raw)
        try:
            if one.is_file() and one.stat().st_mtime > when:
                out.add(str(one))
        except OSError:
            continue
    return out


def config_changed(paths):
    """The config files that differ from the mirror and were reached here.

    The config tree answers to no repository, so the sync is the only thing on
    the machine that knows what moved in it. Held to the paths the transcript
    named, because the sync answers for the whole tree and work in progress
    elsewhere belongs to whichever chat is doing it.
    """
    reached = {str(Path(one).resolve()) for one in paths}
    out = set()
    for one in (sync_drift() or [])[1:]:
        full = Path(CONFIG) / one
        if full.exists() and str(full.resolve()) in reached:
            out.add(str(full))
    return out


def remembered(session):
    """The change set already recorded against a chat.

    A file leaves the diff the moment the branch lands or the mirror takes it,
    and neither of those is a pass. Held per chat, what entered the set stays in
    it, so the order the steps run in cannot empty the thing the gate measures.
    """
    return set((read_polish().get("chats") or {}).get(session) or [])


def remember(session, files):
    store = read_polish()
    held = store.setdefault("chats", {})
    held[session] = sorted(set(held.get(session) or []) | set(files))
    save_polish(store)


def changed(rows, roots, session=""):
    """The files this chat is answerable for, from every place they show up.

    The branch is read against the point it was cut from rather than against
    its own tip, so a chat that committed as it went is still held to what it
    wrote. Where nothing says where it was cut from, the reading falls back to
    the working tree, which is the only honest answer left.
    """
    mine = moved_after(first_named(rows))
    found = set(touched(rows)) | config_changed(mine) | mine
    for root in roots:
        base = git(root, "merge-base", "HEAD", "origin/develop")
        spans = [["diff", "--name-only", "--cached"],
                 ["diff", "--name-only"],
                 ["ls-files", "--others", "--exclude-standard"]]
        spans.insert(0, ["diff", "--name-only", base] if base
                     else ["diff", "--name-only", "HEAD"])
        for span in spans:
            for name in (git(root, *span) or "").splitlines():
                if name.strip():
                    found.add(str(Path(root) / name.strip()))
    keep = {one for one in found if worth_passing(one)}
    if session:
        keep |= {one for one in remembered(session) if worth_passing(one)}
        remember(session, keep)
    return sorted(keep)


def polish_path():
    return state_root() / "archive" / "polish.json"


def read_polish():
    path = polish_path()
    if not path.is_file():
        return {"files": {}}
    try:
        held = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"files": {}}
    return held if isinstance(held, dict) else {"files": {}}


def save_polish(store):
    path = polish_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _lib.write_atomic(path, json.dumps(store, indent=2, sort_keys=True) + "\n")


def digest(path):
    """What a file holds, as the thing a pass is recorded against.

    A mark against a name survives the next edit to the file, which leaves the
    ledger claiming a pass that covered work done after it. Against the
    contents the mark reopens on its own the moment the file moves again.
    """
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
    except OSError:
        return ""


def unpassed(files):
    """The changed files no pass is recorded against as they now stand."""
    marks = read_polish().get("files") or {}
    out = []
    for one in files:
        real = str(Path(one).resolve())
        held = marks.get(real) or {}
        if held.get("hash") and held["hash"] == digest(real):
            continue
        out.append(one)
    return out


def flagged(files):
    """What the AI-writing detector still blocks among the files people read.

    The copy half is the one part of this a tool can settle outright, so it is
    checked rather than marked. Everywhere else a mark is a record of work done
    and nothing verifies it; here something does, and a mark cannot close it.
    """
    wanted = [one for one in files
              if Path(one).suffix.lower() in READ_BY_PEOPLE]
    tool = TOOLS / "writing-pass.py"
    if not wanted or not tool.is_file():
        return []
    try:
        done = subprocess.run([sys.executable, str(tool), "check", *wanted],
                              capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError):
        return []
    if done.returncode == 0:
        return []
    lines = [" ".join(line.split())
             for line in (done.stdout or done.stderr or "").splitlines()
             if line.strip() and not line.lstrip().startswith("Run:")]
    return lines[:SHORTLIST]


def shorten(path):
    """A path as it reads to somebody who knows the machine."""
    text = str(path)
    home = str(HOME)
    return "~" + text[len(home):] if text.startswith(home) else text


def owed(files):
    """The passes a change set is owed and has not had.

    Scoped to what changed and to nothing else. A pass over a whole repository
    at the moment a chat closes is a pass nobody runs, and a gate demanding one
    is a gate somebody switches off inside a week.
    """
    if not files:
        return []
    found = []
    waiting = unpassed(files)
    if waiting:
        copy = [one for one in waiting
                if Path(one).suffix.lower() in READ_BY_PEOPLE]
        found.append("%d changed file(s) have had no /clean pass:" % len(waiting))
        found.extend("  " + shorten(one) for one in waiting[:SHORTLIST])
        if len(waiting) > SHORTLIST:
            found.append("  and %d more" % (len(waiting) - SHORTLIST))
        if copy:
            found.append("%d of them carry words a person reads, so /copywriting "
                         "owes them a pass too:" % len(copy))
            found.extend("  " + shorten(one) for one in copy[:SHORTLIST])
    for line in flagged(files):
        found.append("copy still flagged: %s" % line)
    return found


def polish_findings(rows, roots, session=""):
    """What one transcript's own diff is owed."""
    return owed(changed(rows, roots, session))


def cmd_polish(argv):
    """What the diff is owed, the diff itself, or the record that both ran."""
    session = _named(argv, "--session") or here_session()
    try:
        rows = rows_of(session)
    except Unreadable as why:
        print("the chat could not be read: %s" % why, file=sys.stderr)
        return 2
    paths, _ = footprint(rows)
    roots = repos_of(paths)
    files = changed(rows, roots, session)
    if "--files" in argv:
        for one in files:
            print(one)
        return 0
    if "--mark" in argv:
        # The clock reading claims a named file that moved while the chat was
        # open, which is right for the gate and wrong for the ledger: a file
        # somebody else changed lands in the set and a mark over the whole set
        # records a pass nobody did. Naming the paths is what keeps the two
        # apart, and taking the set is the shorthand for having passed all of
        # it.
        named = [one for one in _positional_all(argv)
                 if one != "--mark"] or files
        outside = [one for one in named
                   if str(Path(one).resolve())
                   not in {str(Path(f).resolve()) for f in files}]
        if outside:
            print("refusing: %s is not in the change set"
                  % ", ".join(shorten(one) for one in outside),
                  file=sys.stderr)
            return 2
        blocking = flagged(named)
        if blocking:
            print("refusing: the copy half is checked rather than marked, and "
                  "it is still flagged.", file=sys.stderr)
            for line in blocking:
                print("  %s" % line, file=sys.stderr)
            return 2
        store = read_polish()
        held = store.setdefault("files", {})
        for one in named:
            mark = digest(one)
            if mark:
                held[str(Path(one).resolve())] = {
                    "hash": mark, "at": NOW(), "session": session}
        save_polish(store)
        print("%d changed file(s) recorded as passed over" % len(named))
        return 0
    found = owed(files)
    if "--json" in argv:
        print(json.dumps({"files": files, "findings": found}, indent=2))
        return 1 if found else 0
    if not found:
        print("nothing owed: every changed file has had both passes")
        return 0
    for line in found:
        print(line)
    print("Run /clean over those paths, /copywriting over the ones a person "
          "reads, then archive.py polish --mark.")
    return 1


# --------------------------------------------------------------- what it missed


# Somebody asking a second time for something already asked for. The reading is
# narrow on purpose: a loose pattern turns every follow-up instruction into a
# dropped ask, and a list that cries wolf is a list nobody opens twice.
OMISSION = re.compile(
    r"\byou (?:forgot|missed|skipped|ignored|didn'?t|did not|never did)\b"
    r"|\bstill (?:haven'?t|hasn'?t|need|needs|needed|missing|not done)\b"
    r"|\b(?:i|we) (?:also|already) (?:said|asked|told|wanted)\b"
    r"|\bwhat about (?:the|my|that|this)\b"
    r"|\byou (?:only|just) (?:did|added|changed|wrote)\b"
    r"|\byou left out\b|\bleft that out\b"
    r"|\bthe rest of (?:it|them|the)\b"
    r"|\bfinish (?:the|it|that)\b|\bhalf (?:done|of it)\b",
    re.I)

# How much of an ask has to surface in the work afterwards before it counts as
# answered. An ask is read by its content words, and a run that carried one out
# names most of them somewhere: in a reply, a path, a command, or the text it
# wrote. Half is the line, and below it the words never came up again, which is
# what a dropped ask looks like from outside.
ANSWERED_SHARE = 0.5

# An ask carrying fewer content words than this cannot be checked by its words,
# and one longer than a message is a message rather than an ask.
MIN_ASK_WORDS = 3
MIN_ASK_TOPIC = 2

# How many separate asks an opening message has to carry before the words
# reading applies to it. The failure it catches is a message asking for several
# things and getting some of them, so a message asking for one thing has no part
# it could have lost.
MIN_ASKS = 2

# How much of what a run did is read back when deciding whether an ask was
# carried out. Long enough to hold a working session, short enough that the
# reading stays a reading rather than a second pass over the transcript.
DID_CAP = 500000


def asks(text):
    """One turn split into the separate things it asked for.

    A message asking for three things in one breath is answered in part and
    read as answered, and that is the whole shape this catches. The split is on
    sentence ends, list markers and the joining words a second ask arrives
    under, because that is how a second ask is actually written down.
    """
    body = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    body = re.sub(r"<[^>]{1,80}>", " ", body)
    parts = re.split(r"(?<=[.!?;])\s+|\n+|\s+(?:also|and also|plus)[,:]?\s+",
                     body, flags=re.I)
    out = []
    for part in parts or []:
        one = " ".join((part or "").split()).strip("-*#> ").strip()
        if len(one.split()) >= MIN_ASK_WORDS:
            out.append(one)
    return out


def did(rows, start):
    """Everything the run wrote or ran after a turn, as one body of words.

    Tool inputs count as much as prose. A run that acted on an ask names its
    words in a path, a command or the text it wrote far more reliably than it
    restates them in a reply, and a reading that looks only at the replies calls
    quiet work forgotten.
    """
    out, size = [], 0
    for row in rows[start + 1:]:
        pieces = []
        if row.get("type") == "assistant":
            pieces.append(_reply_text(row))
        message = row.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for part in content if isinstance(content, list) else []:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_use":
                pieces.append(json.dumps(part.get("input") or {})[:4000])
            elif part.get("type") == "tool_result" and not part.get("is_error"):
                body = part.get("content")
                if isinstance(body, str):
                    pieces.append(body[:2000])
        for piece in pieces:
            out.append(piece)
            size += len(piece)
        if size > DID_CAP:
            break
    return " ".join(out).lower()


def _human_turns(rows, lessons):
    """The turns a person actually typed, in order, as prose.

    A hook injects feedback through a user row and a finished agent reports
    through one, and neither is somebody asking for anything. The command
    marker the harness writes is dropped for the same reason.
    """
    out = []
    for index, row in enumerate(rows):
        if row.get("type") != "user" or row.get("isSidechain"):
            continue
        if (row.get("origin") or {}).get("kind") != "human":
            continue
        body = lessons.FENCE.sub(" ", lessons.text_of(row.get("message") or {}))
        line = " ".join(body.split()).strip()
        if not line or line.startswith("<") or STOP_FEEDBACK.match(line):
            continue
        out.append((index, line))
    return out


def worked(rows, start):
    """Whether the run did anything after a turn that a reading could measure.

    A chat that answered in prose and touched nothing leaves no trace of what
    it carried out, so an ask whose words are absent from it proves nothing.
    The reading stays quiet there rather than calling a conversation a dropped
    ask.
    """
    for row in rows[start + 1:]:
        message = row.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for part in content if isinstance(content, list) else []:
            if isinstance(part, dict) and part.get("type") == "tool_use":
                return True
    return False


def dropped(rows, lessons):
    """Asks that went in and never came out.

    Two readings, catching the same failure from opposite ends. The first takes
    the opening message apart into the separate things it asked for and checks
    each against everything the run did afterwards. The second is somebody
    saying so -- a later turn asking again for something already asked for --
    which is the same finding with a person's own words as the evidence.

    Only the opening message is read the first way. Every turn after it is
    answered under the eye of the person who typed it, and a run that drops
    something there gets told inside the chat. The opening message is the one
    nobody re-reads, and it is where the implied half of an ask lives.

    Three things have to hold before an absence means anything. The message has
    to carry more than one ask, since a message asking for one thing has no
    part it could have lost. The run has to have done something, since a chat
    that touched nothing leaves no trace of what it carried out. And at least
    one of the asks has to have been carried out, because a message where none
    of the words came back is a reading that cannot see the work rather than a
    run that did none of it. What is left is the shape this is about: some of it
    done, and the rest quietly dropped.
    """
    out = []
    turns = _human_turns(rows, lessons)
    if not turns:
        return out
    start, opening = turns[0]
    wanted = asks(opening)
    if len(wanted) >= MIN_ASKS and worked(rows, start):
        later = did(rows, start)
        answered, missing = 0, []
        for one in wanted:
            words = sorted({w for w in re.findall(r"[a-z][a-z-]{3,}",
                                                  one.lower())
                            if w not in lessons.STOPWORDS})
            if len(words) < MIN_ASK_TOPIC:
                continue
            need = max(1, math.ceil(len(words) * ANSWERED_SHARE))
            if sum(1 for w in words if w in later) >= need:
                answered += 1
            else:
                missing.append(one)
        if answered:
            out.extend(("part of the opening message, and nothing carried it "
                        "out", one[:200]) for one in missing)
    for _, line in turns[1:]:
        if len(line) > lessons.MAX_CORRECTION_CHARS:
            continue
        if OMISSION.search(line):
            out.append(("asked again, because the first time went undone",
                        line[:200]))
    return out


# ----------------------------------------------------------------- the lessons


# What each reading is owed, and the order they are owed it in. A collision
# leads because the other three cost a repeat of something while a collision
# costs a decision: two rules that contradict each other cannot both be kept, so
# every run after one picks a side alone and records nothing, and the run after
# that picks again from the same standing start.
WANTS = {"omission": "the work finished", "collision": "precedence",
         "correction": "a mechanism", "recurrence": "context",
         "refusal": "context"}

# An omission leads. The other four are readings about how the work was done
# and it is the only one about whether the work was done at all: a rule with no
# gate behind it costs the next run an argument, and an ask nobody carried out
# costs the person who typed it the thing they asked for. Nothing else here
# outranks that.
ORDER = ("omission", "collision", "correction", "recurrence", "refusal")


def candidates(session, payload=None):
    """What one transcript shows that nothing on this machine enforces.

    Four readings come out of the same pass and they mean different things.

    A correction is somebody supplying by hand what a mechanism should supply,
    so a repeat means no mechanism exists. A refusal is a mechanism working, so
    a repeat means the run kept walking into a rule it had no way to know, which
    is missing context rather than a missing gate.

    A collision is two mechanisms refusing one reply on different grounds. It is
    neither a missing gate nor a missing fact: both gates exist and both fired,
    and satisfying one is what broke the other. What it wants is a decision
    about which of the two yields, written where both are read.

    A recurrence is a ground the transcript carries that enough earlier
    transcripts carry too. A single refusal proves nothing inside one sitting
    and is left alone there; held across sittings the same ground is a wall the
    runs keep meeting, and no one sitting is where that becomes visible.
    """
    lessons = load("lessons")
    rows = rows_of(session, payload)
    seen = {}
    stretch = {}
    pending = {}
    evidence = {}
    met = set()
    # Whether a reply has been written since the last ground was taken down. A
    # second ground only collides with the first once the run has answered the
    # first, and a run of refusals with no draft between them is a list of
    # things wrong with one draft rather than two rules pulling against it.
    redrafted = [False]

    def note(kind, mark, example):
        if OWN_BLOCK in example:
            return
        entry = seen.setdefault(mark, {"kind": kind, "count": 0, "example": ""})
        entry["count"] += 1
        entry["example"] = entry["example"] or example

    def refused_reply(line, draft):
        """One ground that landed on a reply rather than on a tool call."""
        if OWN_BLOCK in line:
            return
        mark = lessons.fingerprint("guard", _ground(line))
        met.add(mark)
        if not stretch or (mark not in stretch and redrafted[0]):
            stretch[mark] = _ground(line)
            redrafted[0] = False
        # The first pairing is the honest one. One firing is written down again
        # further along the transcript, by which time the draft in front of it
        # is the one that answered it, and a second pairing over the same ground
        # records the accepted draft as the refused one.
        if mark in evidence:
            return
        pending.setdefault(mark, {"ground": _ground(line), "refused": draft,
                                  "accepted": ""})

    def close_stretch():
        """The collision reading, taken where a run of drafts ends.

        Two grounds inside one stretch mean the reply was refused, written
        again, and refused on other terms. Nothing else produces that shape: a
        stop hook speaks only over a finished reply, so a second ground with no
        human turn between them is the machine turning down the answer its own
        first refusal asked for.
        """
        if len(stretch) >= COLLISION_GROUNDS:
            grounds = [stretch[m] for m in sorted(stretch)]
            topics = sorted(lessons.topic(g) or g for g in grounds)
            mark = lessons.fingerprint("collide", " ".join(topics))
            note("collision", mark,
                 " -- then, on the redraft -- ".join(grounds))
            # A collision counts the mechanisms that refused rather than the
            # times it was met, and it carries the grounds it is made of so the
            # drafts held against each one can be read back beside it.
            held = seen.get(mark)
            if held:
                held["count"] = len(stretch)
                held["marks"] = sorted(set(held.get("marks", []))
                                       | set(stretch))
        stretch.clear()

    for row in rows:
        kind = row.get("type")
        side = bool(row.get("isSidechain"))
        if kind == "user":
            # A refusal issued inside a subagent is the same machine saying no.
            # Only the correction half is confined to the main thread, because
            # nobody types in a sidechain.
            for source, line in _refusals(row):
                mark = lessons.fingerprint("guard", lessons.topic(line) or line)
                note("refusal", mark, line)
                if source == "stop":
                    refused_reply(line, _reply_before(rows, row))
            if side:
                continue
            body = _said(row, lessons)
            if body:
                close_stretch()
                key = lessons.topic(body)
                if key:
                    note("correction", lessons.fingerprint("said", key),
                         " ".join(body.split())[:200])
        elif kind == "system":
            blob = json.dumps(row.get("hookErrors") or "") + \
                json.dumps(row.get("hookInfos") or "")
            hit = lessons.BLOCKED.search(blob)
            if hit:
                line = " ".join(hit.group(1).split())[:150].strip('"\\ ')
                mark = lessons.fingerprint("guard", lessons.topic(line) or line)
                note("refusal", mark, line)
                refused_reply(line, _reply_before(rows, row))
        elif kind == "assistant" and not side:
            text = _reply_text(row)
            if not text:
                continue
            redrafted[0] = True
            # The draft that follows a refusal is the half nothing keeps. The
            # ground says what was wrong with the first one; the second one is
            # the only statement anywhere of what right looked like.
            for held in pending.values():
                if not held["accepted"]:
                    held["accepted"] = text[:DRAFT_KEEP]
            for mark, held in list(pending.items()):
                if held["accepted"]:
                    evidence[mark] = held
                    del pending[mark]
    close_stretch()
    # Read once over the whole transcript rather than turn by turn, because
    # whether an ask was carried out is a question about everything that came
    # after it and cannot be answered from the turn it arrived in.
    for why, line in dropped(rows, lessons):
        key = lessons.topic(line) or line
        note("omission", lessons.fingerprint("dropped", key),
             "%s: %s" % (why, line))
    keep_evidence(session, evidence)

    ledger = read_ledger().get("candidates", {})
    # An omission needs no repeat. A correction told once could be a slip and a
    # guard firing once is a guard working, so both wait for a second telling
    # before they mean anything. Something asked for and not done means the
    # same thing the first time as the fifth, and the person who asked has
    # already paid for it once.
    floors = {"omission": 1, "correction": MIN_REPEATS, "collision": 1,
              "refusal": CONTEXT_REPEATS}
    out = []
    for mark, entry in seen.items():
        if entry["count"] < floors.get(entry["kind"], CONTEXT_REPEATS):
            continue
        if ledger.get(mark, {}).get("status") in ANSWERED:
            continue
        out.append(dict(entry, id=mark, wants=WANTS[entry["kind"]]))
    out.extend(recurrences(met, ledger))
    out.sort(key=lambda c: (ORDER.index(c["kind"]), -c["count"]))
    return out


def recurrences(met, ledger):
    """Grounds the transcript carries that enough earlier chats carried too.

    Read from what was kept rather than from the transcript, because no single
    transcript holds it: a ground that fired once in one sitting and once in
    another is worth nothing in either, and worth raising across both. Held to
    the grounds the transcript itself met, so a chat is never stopped over a
    wall it never walked into.
    """
    grounds = read_evidence().get("grounds", {})
    out = []
    for mark, held in grounds.items():
        chats = held.get("chats") or {}
        if len(chats) < RECURRENCE_CHATS or mark not in met:
            continue
        if ledger.get(mark, {}).get("status") in ANSWERED:
            continue
        out.append({"id": mark, "kind": "recurrence", "count": len(chats),
                    "wants": WANTS["recurrence"],
                    "example": held.get("ground", "")})
    return out


def _ground(line):
    """The sentence a refusal leads with, the one part every shape of it shares.

    A single firing reaches a transcript more than once: as feedback on the turn
    it stopped, and again in the summary of the hooks that ran. The copies are
    cut to different lengths and escaped differently, so a key taken over the
    whole line reads one mechanism as two. The opening sentence is what survives
    both cuts.
    """
    head = re.split(r"(?<=[.!?])\s|\\n|\n", line.strip(), maxsplit=1)[0]
    return " ".join(head.lower().split())[:120]


def _reply_text(row):
    """The prose of an assistant turn, with thinking and tool calls left out."""
    content = ((row.get("message") or {}).get("content"))
    if isinstance(content, str):
        return " ".join(content.split())
    parts = [block.get("text") or "" for block in content or []
             if isinstance(block, dict) and block.get("type") == "text"]
    return " ".join(" ".join(parts).split())


def _reply_before(rows, row):
    """The last reply written before a row, which is what a stop hook refused."""
    try:
        stop = rows.index(row)
    except ValueError:
        return ""
    for earlier in reversed(rows[:stop]):
        if earlier.get("type") != "assistant" or earlier.get("isSidechain"):
            continue
        text = _reply_text(earlier)
        if text:
            return text[:DRAFT_KEEP]
    return ""


def _said(row, lessons):
    """The text of a human correction, or empty for anything else.

    Only a turn a person typed counts. A hook injects feedback as a user row and
    a completed agent reports through one, and both carry sentences that read
    exactly like somebody objecting.
    """
    if (row.get("origin") or {}).get("kind") != "human":
        return ""
    message = row.get("message") or {}
    body = lessons.FENCE.sub(" ", lessons.text_of(message)).strip()
    if not body or len(body) > lessons.MAX_CORRECTION_CHARS:
        return ""
    if body.startswith("<") or STOP_FEEDBACK.match(body):
        return ""
    return body if lessons.CORRECTION.search(body) else ""


def _refusals(row):
    """Every refusal carried by a user row, tagged by what it landed on.

    A denied tool call and a refused reply are both the machine saying no, and
    they answer different questions. A tool call is the machine steering the
    work. A reply is the machine and the run disagreeing over the answer itself,
    which is the only one of the two that another rule can collide with, since
    it is the only one where two mechanisms are reading the same words.
    """
    out = []
    message = row.get("message") or {}
    content = message.get("content")
    if isinstance(content, str) and STOP_FEEDBACK.match(content.strip()):
        for line in re.findall(r"BLOCKED:\s*(.+)", content):
            out.append(("stop", " ".join(line.split())[:150]))
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "tool_result":
                continue
            if not part.get("is_error"):
                continue
            body = part.get("content")
            text = body if isinstance(body, str) else json.dumps(body)
            for line in re.findall(r"BLOCKED:\s*(.+)", text or ""):
                out.append(("tool", " ".join(line.split())[:150]))
    return out


def _refused(row):
    """Every refusal carried by a user row, from either shape it takes."""
    return [line for _, line in _refusals(row)]


# ------------------------------------------------------------------- the verbs


def cmd_check(argv):
    everything = "--all" in argv
    session = _named(argv, "--session") or here_session()
    try:
        areas = survey(session, everything=everything)
    except Unreadable as why:
        print("the chat could not be read: %s" % why, file=sys.stderr)
        return 2
    if "--json" in argv:
        print(json.dumps([{"area": a, "findings": f} for a, f in areas], indent=2))
        return 1 if areas else 0
    if not areas:
        print("nothing held: the chat closes clean")
        return 0
    for area, findings in areas:
        print("%s:" % area)
        for line in findings:
            print("  %s" % line)
    print("HELD %d area(s)" % len(areas))
    return 1


def cmd_finish(argv):
    """What the chat was asked for and never did.

    The same reading the harvest carries, on its own, because it is the one
    finding here that is answered by doing the work rather than by building
    something. Putting it in front of the other four is what keeps a chat from
    closing tidily over the thing somebody actually wanted.
    """
    session = _named(argv, "--session") or here_session()
    try:
        found = [one for one in candidates(session)
                 if one["kind"] == "omission"]
    except Unreadable as why:
        print("the chat could not be read: %s" % why, file=sys.stderr)
        return 2
    if "--json" in argv:
        print(json.dumps(found, indent=2))
        return 1 if found else 0
    if not found:
        print("nothing dropped: every ask was carried out")
        return 0
    for entry in found[:SHORTLIST]:
        print("  %-18s x%-3d %s" % (entry["id"], entry["count"],
                                    entry["example"]))
    print("%d ask(s) unanswered. Do them, then archive.py settle <id> --as "
          "done --note \"what was finished\"." % len(found))
    return 1


def cmd_harvest(argv):
    session = _named(argv, "--session") or here_session()
    try:
        found = candidates(session)
    except Unreadable as why:
        print("the chat could not be read: %s" % why, file=sys.stderr)
        return 2
    if "--json" in argv:
        print(json.dumps(found, indent=2))
        return 1 if found else 0
    if not found:
        print("nothing to harvest: no correction, refusal or collision")
        return 0
    for entry in found[:SHORTLIST]:
        print("  %-18s %-11s x%-3d wants %s"
              % (entry["id"], entry["kind"], entry["count"], entry["wants"]))
        print("      %s" % entry["example"])
    print("%d candidate(s) unsettled" % len(found))
    return 1


def cmd_settle(argv):
    if not argv or argv[0].startswith("-"):
        print("settle takes the candidate id", file=sys.stderr)
        return 2
    mark = argv[0]
    status = _named(argv, "--as")
    note = _named(argv, "--note") or ""
    if status not in CANDIDATE_STATES:
        print("--as takes one of %s" % ", ".join(CANDIDATE_STATES), file=sys.stderr)
        return 2
    if status != "declined" and not note:
        print("a mechanism has to say what it was, so --note is required",
              file=sys.stderr)
        return 2
    ledger = read_ledger()
    ledger.setdefault("candidates", {})[mark] = {
        "status": status, "note": note, "settled_at": NOW()}
    save_ledger(ledger)
    print("%s settled as %s" % (mark, status))
    return 0


def _positional_all(argv):
    """Every bare argument, skipping the values the named flags consume."""
    out, skip = [], False
    for item in argv:
        if skip:
            skip = False
            continue
        if item in ("--session",):
            skip = True
            continue
        if not item.startswith("-"):
            out.append(os.path.expanduser(item))
    return out


def _positional(argv, taking):
    """The first bare argument, skipping the values the named flags consume."""
    skip = False
    for item in argv:
        if skip:
            skip = False
            continue
        if item in taking:
            skip = True
            continue
        if not item.startswith("-"):
            return item
    return None


def _named(argv, flag):
    """The value of a --flag, whether it arrived joined or separated."""
    for index, item in enumerate(argv):
        if item == flag and index + 1 < len(argv):
            return argv[index + 1]
        if item.startswith(flag + "="):
            return item.split("=", 1)[1]
    return None


BRIEF = """# %(id)s

%(kind)s, seen %(count)s times in the chat that raised it. What it wants: %(wants)s.

## What happened

%(example)s

## What closes this

%(closing)s

## Settling it

    ~/.intelligence/tools/archive.py settle %(id)s --as %(state)s --note "%(names)s"

`built` records a mechanism and needs to name it. `context` records a line
written into INTELLIGENCE.md or a skill where no mechanism can reach. `done`
records work that was asked for and has now been carried out. `declined`
records a judgement that none of them is owed.
"""

MECHANISM = ("A correction repeated inside one sitting is a rule with no gate "
             "behind it. Run /enforce over it and build the strongest form that "
             "fits: impossible, repaired automatically, or blocked with a "
             "message naming the way forward.")

CONTEXT = ("A guard that refuses the same run twice is a mechanism working and "
           "a fact missing. Find what the run needed to know before it acted, "
           "and put it where the next run reads it rather than where it gets "
           "refused.")

PRECEDENCE = ("Two mechanisms refused one reply on different grounds, so "
              "satisfying the first is what broke the second. Neither is wrong "
              "on its own and neither gets loosened to end the argument: a gate "
              "that yields to whoever it inconveniences is a comment. Decide "
              "which one gives way at the point the two meet, write that where "
              "both are read, and leave both gates standing. Where one of them "
              "already carries an override for exactly this reading, saying so "
              "is the whole answer.")

RECURRENCE = ("One ground has refused runs in separate chats, and no single one "
              "of them repeated it often enough to raise it alone. The drafts "
              "either side of each refusal are held beside it: the first is "
              "what a run reached for and the second is what the machine "
              "accepted, and the difference between them is the fact nobody has "
              "written down. Write it where the next run reads it before it "
              "drafts rather than where it gets refused.")

FINISH = ("Something asked for went undone. What closes this is neither a gate "
          "nor a note: it is the work. Read the ask in the words it was typed "
          "in, including the half that was implied rather than spelled out, do "
          "the whole of it, and settle this as done naming what was finished. "
          "Where it was asked and answered and this reading is simply wrong, "
          "decline it -- but a decline that is really a shrug is the same "
          "finding coming back on the next chat, with the work still not done.")

CLOSING = {"omission": FINISH, "correction": MECHANISM, "refusal": CONTEXT,
           "collision": PRECEDENCE, "recurrence": RECURRENCE}

# The prompt travels as an argument to an agent rather than through a URL, so
# nothing truncates it on the way. The cap stays anyway, because a brief that
# outgrows an argv entry is a brief that belongs in the file it points at.
PROMPT_CAP = 14336

# What `claude --bg` prints once the session is up. An agent that cannot be
# named is still an agent that is running, so a line this misses is reported as
# unnamed rather than as a hand-off that did not happen.
BACKGROUNDED = re.compile(r"backgrounded[^0-9a-f]*([0-9a-f]{6,})", re.I)

# Where the agent is told to reach when it is not on the machine the checkouts
# are on. Naming the route inside the brief is what keeps the run from ending
# in a request for somebody to go and type something.
REACH = ("This is running away from the Mac the checkouts are on. Reach it "
         "with ~/.intelligence/tools/remote-access.py run mac -- <command> "
         "rather than asking anybody to run something there by hand.")


def brief_path(session, mark):
    return state_root() / "archive" / "briefs" / ("%s-%s.md" % (session[:8], mark))


def settling(kind):
    """The state a finding of this kind settles into, and what the note names.

    A correction settles as a mechanism and everything else as context.
    Offering `built` to all of them invites a refusal to be recorded as a gate
    that was never written, which is the ledger saying the opposite of the
    truth. A collision settles as context too: what it produces is a line
    saying which rule yields, and a new gate on top of two that already fired
    is a third thing to collide with.
    """
    if kind == "omission":
        return "done", "what was finished"
    if kind == "correction":
        return "built", "what was built"
    if kind == "collision":
        return "context", "which rule yields, and where that is written"
    return "context", "where the fact was written"


def drafts_for(entry):
    """The refused and accepted pairs held against a finding, as a brief reads it.

    A ground on its own says what was wrong. The pair says what right looked
    like, which is the half that closes the lesson and the half no reading of a
    single sitting keeps. A collision is made of two grounds and reads both,
    since the point of it is the two side by side.
    """
    grounds = read_evidence().get("grounds") or {}
    out = []
    for mark in entry.get("marks") or [entry["id"]]:
        chats = (grounds.get(mark) or {}).get("chats") or {}
        for session, pair in sorted(chats.items(),
                                    key=lambda kv: kv[1].get("at", ""))[-2:]:
            out.append("%s, chat %s" % ((grounds.get(mark) or {}).get(
                "ground", mark)[:90], session[:8]))
            out.append("")
            out.append("    refused   %s" % pair.get("refused", "")[:400])
            out.append("    accepted  %s" % pair.get("accepted", "")[:400])
            out.append("")
    if not out:
        return ""
    return "\n".join(["", "", "## What was refused, and what stood in its place",
                      ""] + out)


def write_brief(session, entry):
    """The brief the next chat opens on, saved where a link can reach it."""
    closing = CLOSING.get(entry["kind"], CONTEXT) + drafts_for(entry)
    state, names = settling(entry["kind"])
    body = BRIEF % {"id": entry["id"], "kind": entry["kind"].capitalize(),
                    "count": entry["count"], "wants": entry["wants"],
                    "example": entry["example"], "closing": closing,
                    "state": state, "names": names}
    path = brief_path(session, entry["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    _lib.write_atomic(path, body)
    return path


def opening_prompt(entry, path, remote=False):
    """What the next agent starts on, and where it reaches for a shell.

    A correction opens on /enforce, whose argument is the rule in the words it
    was given in. A refusal opens on prose: what it wants is a fact written
    where the next run reads it, there is no command for that, and a brevity
    command in the first position asks the chat to be short about work it has
    not done.

    An agent started anywhere but the Mac is told the route to it, because the
    alternative to naming that route is an agent that stops and asks.
    """
    state, _ = settling(entry["kind"])
    kind = entry["kind"]
    if kind == "omission":
        head = ("Something asked for in the chat that closed was never carried "
                "out. Do it, in full, as it was asked, including the part that "
                "was implied rather than spelled out. Do not report on it and "
                "do not ask which half to do first.")
    elif kind == "correction":
        head = "/enforce %s" % entry["example"][:200]
    elif kind == "collision":
        head = ("Two mechanisms refused one reply on different grounds. Read "
                "both, decide which one yields where they meet, and write that "
                "where both are read. Neither gate comes out and neither gets "
                "weakened.")
    else:
        head = ("Write the fact this run was missing into INTELLIGENCE.md or "
                "the skill that owns it, so the next run reads it rather than "
                "learning it by being refused.")
    seen = {"omission": "Raised out of the chat that closed, where it was "
                        "asked %d time(s) and nothing afterwards carried it "
                        "out.",
            "collision": "Raised out of the chat that closed, where %d "
                         "mechanisms refused one reply and nothing on this "
                         "machine says which of them wins.",
            "recurrence": "Raised across %d separate chats, none of which "
                          "repeated it often enough to raise it alone."}.get(
        kind, "Raised out of the chat that closed. Seen %d times there, and "
              "nothing on this machine answers it yet.")
    text = ("%s\n\n"
            "%s\n\n"
            "  %s\n\n"
            "%s\n\n"
            "%s"
            "The brief is at %s. When it is settled, record what it became:\n"
            "  ~/.intelligence/tools/archive.py settle %s --as %s --note \"...\"\n"
            % (head, seen % entry["count"], entry["example"],
               CLOSING.get(kind, CONTEXT) + drafts_for(entry),
               (REACH + "\n\n") if remote else "",
               path, entry["id"], state))
    return text[:PROMPT_CAP]


def on_mac():
    """Whether this run is on the workstation the checkouts live on.

    A cloud container carries the same tools and the same mirror and none of
    the trees, so an agent started there opens beside nothing. This decides
    where the hand-off goes, never whether it happens.

    INTELLIGENCE_HANDOFF_HOST settles it outright, for a machine the reading
    gets wrong and for a case that has to exercise the branch it is not on.
    """
    forced = os.environ.get("INTELLIGENCE_HANDOFF_HOST")
    if forced:
        return forced == "local"
    return sys.platform == "darwin" and (HOME / "Development").is_dir()


FIXTURE_ROOTS = ("INTELLIGENCE_STATE_DIR", "INTELLIGENCE_TRANSCRIPTS")


def fixture_run():
    """Whether this run belongs to a case suite rather than to the machine.

    INTELLIGENCE_STATE_DIR and INTELLIGENCE_TRANSCRIPTS exist so a suite's
    fixtures stay out of the live tree, which makes a run carrying either one a
    suite by construction. Both are read, because a lesson's origin is the
    transcript it was raised from: a run pointed at fabricated chats writes a
    brief about a rule nobody gave, and a live state root underneath it makes
    that brief real rather than making the run genuine. Nothing a suite does is
    meant to reach anybody.

    Both arrive only once a suite has pointed them somewhere, which leaves a
    suite that reaches for a session before doing so unmarked here. What stops
    that one is suite-sandbox.py, whose stand-in is on the PATH of every suite
    from its first line and does not depend on the suite marking itself.
    """
    return any(os.environ.get(name) for name in FIXTURE_ROOTS)


def child_env():
    """The environment a started agent gets, without the fixture roots in it.

    A session inherits the environment of whatever started it, and a root
    pointing at a temporary tree makes every tool the session runs read and
    write that tree instead of the machine. A settle then reports success and
    lands nowhere. The roots come off here so the agent starts on the machine
    it was started to work on, whatever the run holding the door was carrying.
    """
    return {k: v for k, v in os.environ.items() if k not in FIXTURE_ROOTS}


class NotForFixtures(Exception):
    """The run is a case suite, so there was no agent to start.

    Apart from a launch that failed because the two want opposite answers: a
    suite refused is this file working, and a launcher that would not start is
    a hand-off owed another attempt.
    """


class Undispatched(Exception):
    """The agent did not start.

    The one outcome the ledger must never record as a hand-off, since a
    released gate over an agent that was never running is the archive letting
    the lesson go.
    """


def dispatch(prompt, folder):
    """Start an unattended agent on the brief, and name it if it says its name.

    A hand-off that opens a window is a hand-off that waits for somebody to
    come and drive it, which puts a person back into the one step that exists
    to take the work off them. `claude --bg` returns as soon as the session is
    up, and the session then runs with nothing watching it.

    Away from the Mac the same command travels the remote route. That route is
    synchronous and holds the channel open for as long as anything owns the
    far end's output, so the command detaches itself rather than relying on
    the agent to let go of the terminal it started under.

    A case suite reaches this door the same way a person does, and a brief it
    writes lives in a tree that exists to be thrown away, so an agent started
    from one opens on a file that is already gone. The launch answers to the
    state the hand-off is recorded into for that reason. There is no override:
    a run that wants a live agent is a run against the live state, and has one
    already.
    """
    if fixture_run():
        raise NotForFixtures(
            "a case suite may not start an agent. The brief went into the "
            "fixture tree the suite deletes, so the agent would open on a "
            "file that is already gone. Read the hand-off with `archive.py "
            "hand-off --print`, or hand off for real with "
            "INTELLIGENCE_STATE_DIR unset.")
    if on_mac():
        argv, cwd = ["claude", "--bg", prompt], folder
    else:
        started = "cd %s && claude --bg %s" % (shlex.quote(folder),
                                               shlex.quote(prompt))
        argv = [str(TOOLS / "remote-access.py"), "run", "mac", "--",
                "nohup sh -c %s > /dev/null 2>&1 & disown" % shlex.quote(started)]
        cwd = None
    done = subprocess.run(argv, cwd=cwd, env=child_env(), capture_output=True,
                          text=True, timeout=300)
    if done.returncode != 0:
        raise Undispatched((done.stderr or done.stdout or "").strip()
                           or "exit %d" % done.returncode)
    found = BACKGROUNDED.search(done.stdout or "")
    return found.group(1) if found else ""


def record_handoff(entry, path, name):
    """Write the hand-off into the ledger that lets the archive close.

    Held apart from the launch so what a hand-off leaves behind can be read
    back without anything having to be started to leave it.
    """
    ledger = read_ledger()
    ledger.setdefault("candidates", {})[entry["id"]] = {
        "status": HANDED_OFF, "note": "", "brief": str(path),
        "agent": name, "settled_at": NOW()}
    save_ledger(ledger)


def cmd_handoff(argv):
    session = _named(argv, "--session") or here_session()
    wanted = _positional(argv, ("--session",))
    try:
        found = candidates(session)
    except Unreadable as why:
        print("the chat could not be read: %s" % why, file=sys.stderr)
        return 2
    if not found:
        print("nothing to hand off: no repeated correction or refusal")
        return 0
    entry = next((c for c in found if c["id"] == wanted), None) if wanted \
        else found[0]
    if entry is None:
        print("no candidate %s in the chat" % wanted, file=sys.stderr)
        return 2
    path = write_brief(session, entry)
    folder = os.environ.get("INTELLIGENCE_HANDOFF_FOLDER") or str(HOME)
    prompt = opening_prompt(entry, path, not on_mac())
    if "--print" in argv:
        print(prompt)
        return 0
    try:
        name = dispatch(prompt, folder)
    except NotForFixtures as why:
        print("no agent was started: %s" % why, file=sys.stderr)
        print("the brief is at %s" % path, file=sys.stderr)
        return 2
    except (OSError, subprocess.SubprocessError, Undispatched) as why:
        print("the agent could not be started: %s" % why, file=sys.stderr)
        print("the brief is at %s" % path, file=sys.stderr)
        return 1
    record_handoff(entry, path, name)
    print("dispatched an agent on %s%s"
          % (entry["id"], (" as %s" % name) if name else ""))
    print("  %s" % entry["example"])
    print("  brief: %s" % path)
    return 0



def store_record(session):
    """The app's own record of one chat, found by the id its transcript carries.

    A chat is named twice and the two names never match. The store calls it
    `local_<uuid>`, the transcript on disk carries a different uuid, and the
    two meet at one field inside the record. A lookup that hands the
    transcript's name straight to the store gets "not found" back, and "not
    found" is indistinguishable from a chat the app never registered.
    Resolving the pair here is what tells those two apart.
    """
    if not session:
        return None
    for path in sorted(SESSIONS.glob("*/*/local_*.json")):
        try:
            held = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if held.get("cliSessionId") == session:
            return held
    return None


def agent_entry(session):
    """The running session the background listing reports under one id.

    That listing is the only place a headless session appears. It holds no
    store record, so nothing else on the machine knows it is there, and a
    listing that cannot be read yields no entry -- which leaves `close`
    refusing rather than guessing at a process to end.
    """
    if not session:
        return None
    try:
        done = subprocess.run(["claude", "agents", "--json"], timeout=30,
                              capture_output=True, text=True)
        held = json.loads(done.stdout or "[]")
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    for one in held if isinstance(held, list) else []:
        if one.get("sessionId") == session:
            return one
    return None


def cmd_close(argv):
    """Close the chat this runs in, whichever of the two shapes it has.

    A chat the app knows is closed by the archive call, and this resolves the
    name that call has to carry. A headless chat has no record to flip, so
    closing it is the session ending, which is the whole of what archiving
    does to it either way: the conversation is kept by both endings. The
    background listing owns that ending and is asked for it first; the signal
    is what answers a listing that will not perform it.

    The gate is re-run here rather than left to guard-archive. A headless
    close makes no tool call, so nothing else refuses it, and a way out of
    this skill that nothing refuses is the skill switched off.
    """
    session = _named(argv, "--session") or here_session()
    if not session:
        print("no session to close: nothing names this chat", file=sys.stderr)
        return 2
    if os.environ.get("INTELLIGENCE_ALLOW_ARCHIVE") != "1":
        try:
            areas = survey(session)
            found = candidates(session)
        except Unreadable as why:
            print("the chat could not be read: %s" % why, file=sys.stderr)
            return 2
        if areas or found:
            print("BLOCKED: the chat is still holding something. archive.py "
                  "check and archive.py harvest name it.", file=sys.stderr)
            return 2
    held = store_record(session)
    if held:
        print("registered: %s" % held.get("sessionId"))
        print("archive it: mcp__ccd_session_mgmt__archive_session "
              "session_id=self")
        return 0
    entry = agent_entry(session)
    if not entry:
        print("unplaceable: no store record and no running session under %s"
              % session, file=sys.stderr)
        return 2
    if entry.get("kind") != "background":
        print("refusing: %s runs in the foreground and has no store record, "
              "so neither ending applies to it" % session, file=sys.stderr)
        return 2
    if fixture_run():
        print("a case suite may not end a session: the pid belongs to the "
              "machine rather than to the fixture", file=sys.stderr)
        return 2
    pid = entry.get("pid")
    if not isinstance(pid, int) or pid < 2:
        print("refusing: %s reports no process to end" % session,
              file=sys.stderr)
        return 2
    named = entry.get("id") or session
    print("headless: no store record, so the close is the session ending")
    print("  %s, pid %d" % (named, pid))
    sys.stdout.flush()
    try:
        done = subprocess.run(["claude", "stop", str(named)], timeout=60,
                              capture_output=True, text=True)
        if done.returncode == 0:
            return 0
        why = (done.stderr or done.stdout or "").strip()
    except (OSError, subprocess.SubprocessError) as failed:
        why = str(failed)
    print("  the session did not stop on its own route (%s), ending the "
          "process" % (why or "no reason given"))
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as failed:
        print("the session would not end: %s" % failed, file=sys.stderr)
        return 2
    return 0


def cmd_guard(argv):
    """PreToolUse over the archive call itself.

    The sweep and the harvest both exit non-zero while something is outstanding,
    and a rule that only says so is a rule a run can finish over. Refusing the
    call is what makes the order real: the work lands and the lesson is handed
    off, or the chat stays open.
    """
    if os.environ.get("INTELLIGENCE_ALLOW_ARCHIVE") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    given = (payload.get("tool_input") or {}).get("session_id") or "self"
    target = here_session(payload) if given == "self" else given
    own = target == here_session(payload)
    try:
        areas = survey(target, payload if own else None)
        found = candidates(target, payload if own else None)
    except Unreadable as why:
        sys.stderr.write(
            "BLOCKED: %s.\n\n"
            "A chat nobody can read is not a chat that closed clean, and this\n"
            "one can be neither swept nor harvested. Name a session id that\n"
            "has a transcript.\n\n"
            "INTELLIGENCE_ALLOW_ARCHIVE=1 lets one archive through.\n" % why)
        return 2
    if not areas and not found:
        return 0
    lines = []
    for area, findings in areas:
        lines.extend("%s: %s" % (area, one) for one in findings)
    lines.extend("%s x%d, wants %s: %s"
                 % (c["id"], c["count"], c["wants"], c["example"][:90])
                 for c in found[:SHORTLIST])
    ways = []
    names = {area for area, _ in areas}
    if names - {"config not mirrored", "changed code not passed over"}:
        ways.append("Land the work, or say where it goes.")
    if "config not mirrored" in names:
        ways.append("config-sync.py publish puts the mirror in step.")
    if "changed code not passed over" in names:
        ways.append("archive.py polish --files names the diff; run /clean over "
                    "it and /copywriting over the words a person reads, then "
                    "archive.py polish --mark.")
    if any(c["kind"] == "omission" for c in found):
        ways.append("archive.py finish names what was asked and not done. Do "
                    "it, then archive.py settle <id> --as done.")
    if found:
        ways.append("archive.py hand-off opens the chat that answers the "
                    "lesson; archive.py settle records a judgement that "
                    "nothing is owed.")
    sys.stderr.write(
        "BLOCKED: the chat is still holding something.\n\n  %s\n\n"
        "Archiving ends the one process that knows what the chat was doing.\n"
        "%s\n\n"
        "INTELLIGENCE_ALLOW_ARCHIVE=1 lets one archive through.\n"
        % ("\n  ".join(lines), " ".join(ways)))
    return 2



# The two shapes a typed command takes in a transcript. The marker is what the
# harness writes for a slash command; the bare line is the same instruction
# reaching a session through its opening prompt.
ASKED = re.compile(r"<command-name>\s*/archive\b", re.I)


def asked_to_close(rows):
    """Whether the chat was told to close itself.

    Read from the transcript rather than from a marker file, so a session that
    was told twice and a session restarted mid-close both answer the same.
    """
    for row in rows:
        content = ((row.get("message") or {}).get("content"))
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            text = block.get("text") or ""
            if ASKED.search(text) or text.strip() == "/archive":
                return True
    return False


def cmd_guard_stop(argv):
    """Stop hook over a headless chat that was told to close and has not.

    A chat the app knows ends through the archive call, which carries its own
    gate. A headless chat has no such call to gate, so the instruction to close
    it can be answered with a sentence and the session goes on running -- which
    is the ending this skill exists to make unnecessary. This refuses the stop
    instead, and `close` is the way through.
    """
    if os.environ.get("INTELLIGENCE_ALLOW_ARCHIVE") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    session = here_session(payload)
    if not session or store_record(session):
        return 0
    entry = agent_entry(session)
    if not entry or entry.get("kind") != "background":
        return 0
    try:
        rows = rows_of(session, payload)
    except Unreadable:
        return 0
    if not asked_to_close(rows):
        return 0
    sys.stderr.write(
        "BLOCKED: this chat was told to close and is still running.\n\n"
        "  session %s, pid %s\n\n"
        "It holds no record the archive call can reach, so the close is the\n"
        "process ending and nothing else performs it. Neither a sentence\n"
        "saying the call is unavailable nor a request to another session is\n"
        "an ending.\n\n"
        "  ~/.intelligence/tools/archive.py close\n\n"
        "INTELLIGENCE_ALLOW_ARCHIVE=1 lets one stop through.\n"
        % (session, entry.get("pid")))
    return 2


COMMANDS = {"check": cmd_check, "finish": cmd_finish, "polish": cmd_polish,
            "harvest": cmd_harvest, "settle": cmd_settle,
            "hand-off": cmd_handoff, "close": cmd_close,
            "guard-archive": cmd_guard,
            "guard-stop": cmd_guard_stop}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
