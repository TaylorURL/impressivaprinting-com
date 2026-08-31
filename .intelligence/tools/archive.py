#!/usr/bin/env python3
"""What a chat still holds at the moment somebody closes it.

Archiving a chat ends the one process that knows what the chat was doing. The
transcript survives, so nothing written down is lost, and everything not written
down goes with it: a worktree cut and never landed, a pull request opened and
never watched, a skill edited and never mirrored, and the sentence somebody had
to say twice because no mechanism catches it.

Those are two different problems and both are answered here. Unfinished work is
a matter of fact and gets measured -- the trees the chat touched, the branches it
cut, the pull requests it opened, the config it edited. A lesson is a matter of
reading, and the transcript is where it is legible: a correction is somebody
supplying by hand what a mechanism should supply, and a refusal is a mechanism
that fired and went on firing.

Scope is what keeps this from crying wolf. A machine-wide sweep refuses over a
stale branch in a repository the chat never opened, and a gate that refuses over
somebody else's mess gets switched off within a day. So the reading is held to
the directories, repositories and branches the transcript actually names, and
--all widens it for a run that wants the whole machine.

  archive.py check [--all] [--json] [--session ID]   work the chat still holds
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

import importlib.util
import json
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

# Findings are read to a person who is closing a chat, so the list has to fit on
# a screen or it gets skimmed past the thing that mattered.
SHORTLIST = 12

# Paths worth resolving out of a shell command. Anything shorter than a home
# directory reference is noise, and a match only becomes a repository when git
# says so.
PATHS = re.compile(r"(?:~|/Users/[A-Za-z0-9._-]+)/[A-Za-z0-9._/-]{2,}")

PR_URL = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)")

# The three shapes a refusal takes in a transcript. A PreToolUse denial arrives
# as a tool result, stop feedback as a plain user turn, and a stop summary as a
# system row; reading only the last of those sees a fraction of what refused.
STOP_FEEDBACK = re.compile(r"^\s*stop hook feedback", re.I)

# The gate reporting itself is not a lesson. Each refusal it issues would
# otherwise count toward a candidate, so a chat it blocked twice could never
# reach an ending: the block becomes the reason for the next block.
OWN_BLOCK = "the chat is still holding something"

CANDIDATE_STATES = ("built", "context", "declined")

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
            for hit in PATHS.findall(text):
                paths.add(os.path.expanduser(hit))
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


def config_findings(paths):
    """Whether the mirror carries what the machine holds.

    A chat that edited a skill, a tool or a hook and closed before the mirror
    took it leaves a container installing last week's copy, and nothing about
    the local tree looks wrong afterwards.
    """
    tool = TOOLS / "config-sync.py"
    if not tool.is_file():
        return []
    try:
        done = subprocess.run([sys.executable, str(tool), "check"],
                              capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError):
        return []
    if done.returncode == 0:
        return []
    # The first line carries a count and the names are underneath it, so a
    # reading that keeps one line reports a number and no way to act on it.
    # The closing remedy is dropped instead, since the block already names it.
    detail = [line.strip()
              for line in (done.stdout or done.stderr or "").splitlines()
              if line.strip() and not line.lstrip().startswith("Run:")]
    if not detail:
        return ["the mirror could not be read"]
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
    return areas


# ----------------------------------------------------------------- the lessons


def candidates(session, payload=None):
    """What one transcript shows that nothing on this machine enforces.

    Two readings come out of the same pass and mean opposite things. A
    correction is somebody supplying by hand what a mechanism should supply, so
    a repeat means no mechanism exists. A refusal is a mechanism working, so a
    repeat means the run kept walking into a rule it had no way to know, which
    is missing context rather than a missing gate.
    """
    lessons = load("lessons")
    rows = rows_of(session, payload)
    seen = {}

    def note(kind, mark, example):
        if OWN_BLOCK in example:
            return
        entry = seen.setdefault(mark, {"kind": kind, "count": 0, "example": ""})
        entry["count"] += 1
        entry["example"] = entry["example"] or example

    for row in rows:
        if row.get("isSidechain"):
            continue
        kind = row.get("type")
        if kind == "user":
            for line in _refused(row):
                mark = lessons.fingerprint("guard", lessons.topic(line) or line)
                note("refusal", mark, line)
            body = _said(row, lessons)
            if body:
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

    ledger = read_ledger().get("candidates", {})
    out = []
    for mark, entry in seen.items():
        floor = MIN_REPEATS if entry["kind"] == "correction" else CONTEXT_REPEATS
        if entry["count"] < floor:
            continue
        if ledger.get(mark, {}).get("status") in ANSWERED:
            continue
        out.append(dict(entry, id=mark, wants=(
            "a mechanism" if entry["kind"] == "correction" else "context")))
    out.sort(key=lambda c: (c["kind"] != "correction", -c["count"]))
    return out


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


def _refused(row):
    """Every refusal carried by a user row, from either shape it takes."""
    out = []
    message = row.get("message") or {}
    content = message.get("content")
    if isinstance(content, str) and STOP_FEEDBACK.match(content.strip()):
        for line in re.findall(r"BLOCKED:\s*(.+)", content):
            out.append(" ".join(line.split())[:150])
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "tool_result":
                continue
            if not part.get("is_error"):
                continue
            body = part.get("content")
            text = body if isinstance(body, str) else json.dumps(body)
            for line in re.findall(r"BLOCKED:\s*(.+)", text or ""):
                out.append(" ".join(line.split())[:150])
    return out


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
        print("nothing to harvest: no repeated correction or refusal")
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
written into INTELLIGENCE.md or a skill where no mechanism can reach. `declined`
records a judgement that neither is owed.
"""

MECHANISM = ("A correction repeated inside one sitting is a rule with no gate "
             "behind it. Run /enforce over it and build the strongest form that "
             "fits: impossible, repaired automatically, or blocked with a "
             "message naming the way forward.")

CONTEXT = ("A guard that refuses the same run twice is a mechanism working and "
           "a fact missing. Find what the run needed to know before it acted, "
           "and put it where the next run reads it rather than where it gets "
           "refused.")

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

    A correction settles as a mechanism and a refusal as context. Offering
    `built` to both invites a refusal to be recorded as a gate that was never
    written, which is the ledger saying the opposite of the truth.
    """
    if kind == "correction":
        return "built", "what was built"
    return "context", "where the fact was written"


def write_brief(session, entry):
    """The brief the next chat opens on, saved where a link can reach it."""
    closing = MECHANISM if entry["kind"] == "correction" else CONTEXT
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
    if entry["kind"] == "correction":
        head = "/enforce %s" % entry["example"][:200]
    else:
        head = ("Write the fact this run was missing into INTELLIGENCE.md or "
                "the skill that owns it, so the next run reads it rather than "
                "learning it by being refused.")
    text = ("%s\n\n"
            "Raised out of the chat that closed. Seen %d times there, and "
            "nothing on this machine answers it yet.\n\n"
            "  %s\n\n"
            "%s\n\n"
            "%s"
            "The brief is at %s. When it is settled, record what it became:\n"
            "  ~/.intelligence/tools/archive.py settle %s --as %s --note \"...\"\n"
            % (head, entry["count"], entry["example"],
               MECHANISM if entry["kind"] == "correction" else CONTEXT,
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
    if names - {"config not mirrored"}:
        ways.append("Land the work, or say where it goes.")
    if "config not mirrored" in names:
        ways.append("config-sync.py publish puts the mirror in step.")
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


COMMANDS = {"check": cmd_check, "harvest": cmd_harvest, "settle": cmd_settle,
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
