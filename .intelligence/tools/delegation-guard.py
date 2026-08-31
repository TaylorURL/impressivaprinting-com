#!/usr/bin/env python3
"""Refuses a wide survey that one agent should have carried.

A turn that reads forty files into the main context pays for all forty twice:
once to fetch them and again in every later request, because they sit in the
window for the rest of the run. An agent reading the same forty returns the
conclusion and drops the rest. Across the transcripts on this machine, 273 of
1573 tool-using turns made twelve or more read-shaped calls and 14 of them
delegated -- so the default is inline sweeping, and the default is the expensive
one.

The gate sits where a redirect still saves something. A refusal at the end of a
turn saves nothing, since the reading is already paid for, so the survey is
counted while it runs and stopped at the threshold with the rest still unspent.
The prompt check runs earlier still, before any of it.

  guard-prompt  UserPromptSubmit. Weighs the ask for fan-out shape and names
                the delegation when there is one, silent when there is not.
  guard-probe   PreToolUse on read-shaped calls. Counts the survey so far in
                the turn and refuses the next call once it is wide enough to
                belong to an agent.
  guard-agent   PreToolUse on Agent. Refuses a dispatch that costs more than
                the single call it stands in for.
  guard-stop    Stop. Records what the turn did in the ledger.
  report        What the ledger holds, and what a transcript has spent.
  install       Wire the hooks into settings.json.

Both directions are enforced, because "use agents" alone produces a run that
spawns one to read a file it could have opened. The probe gate refuses a sweep
carried inline; the agent gate refuses an agent carrying a sweep of one.

INTELLIGENCE_DELEGATION_OFF=1 stands the whole thing down.
INTELLIGENCE_ALLOW_INLINE=1 exempts a survey that has to stay in one context.
INTELLIGENCE_DELEGATION_THRESHOLD sets the probe count that trips the redirect.
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

HOME = Path.home()
INTELLIGENCE = HOME / ".intelligence"

# The survey width that belongs to an agent rather than one context. Twelve is
# where the measured distribution separates: turns below it are ordinary work,
# turns above it are sweeps, and a sweep stopped at twelve has spent a fraction
# of what one run to completion costs.
THRESHOLD = int(os.environ.get("INTELLIGENCE_DELEGATION_THRESHOLD", "12"))

# A survey is wide as well as long. A turn stepping through one file with sed
# reaches any call count without covering any ground, and an agent handed that
# returns the same file through one more layer.
BREADTH = 6

# Commands that read. The verb list is what a survey is actually made of here:
# bypass mode routes reads through Bash, so Read and Grep between them account
# for a fraction of the reading a turn does.
READ_VERBS = {
    "cat", "head", "tail", "grep", "rg", "find", "ls", "fd", "wc", "sed",
    "awk", "tree", "stat", "file", "nl", "cut", "sort", "uniq", "jq", "diff",
    "basename", "dirname", "readlink", "du", "column",
}

# Anything that changes state disqualifies a command from being a read,
# whatever verbs it also carries. A redirect is the common case: `grep x > out`
# leads with a read verb and is not a read.
WRITES = re.compile(
    r"(?<![0-9<>&])>(?!&)|>>|\btee\b"
    r"|\b(?:rm|mv|cp|mkdir|touch|ln|chmod|chown|install|truncate)\b"
    r"|\bgit\s+(?:commit|push|add|checkout|merge|rebase|reset|apply)\b"
    r"|\b(?:npm|pip|pip3|yarn|pnpm|make|cargo|mvn|gradle)\b"
    r"|\bsed\b[^|;]*-i\b",
)

AGENT_TOOLS = ("Agent", "Task")
PROBE_TOOLS = ("Read", "Grep", "Glob", "NotebookRead")
EDIT_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")

# The checklist engines watch files be read to clear them, and a gate cannot
# credit a read that happened inside an agent. Redirecting a survey while one of
# their runs is open would trade a token saving for a run that cannot close.
CHECKLIST_KINDS = ("design", "seo", "perf", "stack", "db")


def state_root():
    override = os.environ.get("INTELLIGENCE_STATE_DIR")
    if override:
        return Path(override)
    if os.environ.get("CLAUDE_CODE_REMOTE"):
        return HOME / ".pass-state"
    return INTELLIGENCE / "state"


def ledger_path():
    return state_root() / "delegation" / "ledger.json"


def latch_path(session):
    return state_root() / "delegation" / ("latch-%s.json" % (session or "anon"))


def checklist_open(session):
    """Whether a checklist engine holds a run the caller owns.

    Ownership is the whole test. The engines keep a per-session pointer and a
    shared one, and a shared pointer outlives the run that wrote it -- two were
    standing on this machine from runs that ended days earlier. Honouring those
    would exempt every later session from the survey gate for good, which is an
    off switch nobody chose. A session with no id of its own falls back to the
    shared pointer, which is the same reading the other stop guards take.
    """
    root = state_root()
    for kind in CHECKLIST_KINDS:
        runs = root / ("%s-runs" % kind)
        if session:
            if (runs / ("current-%s.json" % session)).is_file():
                return kind
        elif (runs / "current.json").is_file():
            return kind
    return None


def read_shaped(command):
    """Whether a shell command only reads.

    The test is over the verbs actually invoked rather than the leading token,
    since a survey is routinely a pipeline and the read sits mid-chain. A
    command carrying any writing verb is not a read however it starts.
    """
    if not command or WRITES.search(command):
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    return any(os.path.basename(t) in READ_VERBS
               for t in tokens if not t.startswith("-"))


PATHISH = re.compile(r"^[~./]|/|\.[A-Za-z0-9]{1,6}$")


def targets_of(name, tool_input):
    """What a call went looking at, for measuring breadth rather than length."""
    if name in PROBE_TOOLS or name in EDIT_TOOLS:
        found = [tool_input.get(k) for k in
                 ("file_path", "notebook_path", "path", "pattern", "glob")]
        return {str(v) for v in found if v}
    command = str(tool_input.get("command") or "")
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    return {t for t in tokens
            if not t.startswith("-") and PATHISH.search(t)
            and os.path.basename(t) not in READ_VERBS}


def tail_rows(path, limit=1 << 21):
    """The parsed rows at the end of a transcript, and whether that is all of it.

    A transcript grows without bound while a turn is a few dozen rows, so the
    gate reads the end of the file rather than the file. A leading partial line
    is dropped. The second return says whether the window covered the whole
    file, which is what tells a caller its view of the turn is complete.
    """
    lines, whole = tail_lines(path, limit)
    rows = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows, whole


def tail_lines(path, limit):
    """The last lines of a file as text, unparsed."""
    whole = True
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as handle:
            if size > limit:
                whole = False
                handle.seek(size - limit)
                handle.readline()
            raw = handle.read().decode("utf-8", "replace")
    except OSError:
        return [], True
    return raw.splitlines(), whole


def is_prompt(row):
    """Whether a row is the person speaking, rather than a tool answering.

    Tool results arrive as user rows too, so the content decides: a result
    carries tool_result blocks and a prompt does not.
    """
    if row.get("type") != "user":
        return False
    content = (row.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return not any(isinstance(b, dict) and b.get("type") == "tool_result"
                       for b in content)
    return False


def current_turn(path, limit=1 << 21):
    """The rows since the person last spoke, or None when that is unknown.

    Parsed backwards from the end and stopped at the boundary, because a turn is
    a few dozen rows at the tail of a file that runs to megabytes: decoding the
    whole window to find them costs more than every gate reading it saves.

    The boundary is a prompt row. When the window did not reach one and the
    window was not the whole file, the turn extends further back than what was
    read and its size cannot be counted -- so the gates stand down rather than
    judge a fragment. The failure mode is a heavy turn that escapes, which costs
    tokens; the alternative is a refusal computed from a number nobody measured.
    """
    lines, whole = tail_lines(path, limit)
    rows = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        # A row that cannot be one of the two boundary shapes needs no decode,
        # and the great majority of a transcript's bytes are those rows.
        if '"user"' not in line:
            marker = None
        else:
            try:
                marker = json.loads(line)
            except ValueError:
                marker = None
        if marker is not None and is_prompt(marker):
            rows.reverse()
            return rows
        try:
            rows.append(marker if marker is not None else json.loads(line))
        except ValueError:
            continue
    if whole:
        rows.reverse()
        return rows
    return None


class Survey:
    """What a turn has done so far, in the terms the gates judge."""

    def __init__(self):
        self.probes = 0
        self.targets = set()
        self.agents = 0
        self.edited = False
        self.sidechain = False

    @property
    def wide(self):
        return self.probes >= THRESHOLD and len(self.targets) >= BREADTH


def survey(rows):
    """Measure a turn.

    Reads stop counting once the turn starts editing. Reading in order to change
    a file is not a survey -- it is the work -- and an agent cannot carry it,
    since the edits belong in the calling context.
    """
    found = Survey()
    for row in rows:
        if row.get("isSidechain"):
            found.sidechain = True
        if row.get("type") != "assistant":
            continue
        content = (row.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name") or ""
            tool_input = block.get("input") or {}
            if name in AGENT_TOOLS:
                found.agents += 1
            elif name in EDIT_TOOLS:
                found.edited = True
            elif not found.edited:
                if name in PROBE_TOOLS or (
                        name == "Bash"
                        and read_shaped(str(tool_input.get("command") or ""))):
                    found.probes += 1
                    found.targets |= targets_of(name, tool_input)
    return found


def spend(rows):
    """The tokens a transcript's assistant rows account for."""
    fresh = cached = out = 0
    for row in rows:
        usage = (row.get("message") or {}).get("usage")
        if not isinstance(usage, dict):
            continue
        fresh += int(usage.get("input_tokens") or 0)
        fresh += int(usage.get("cache_creation_input_tokens") or 0)
        cached += int(usage.get("cache_read_input_tokens") or 0)
        out += int(usage.get("output_tokens") or 0)
    return fresh, cached, out


def record(**counts):
    """Add to the day's row in the ledger."""
    from datetime import date
    path = ledger_path()
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        data = {}
    day = data.setdefault(date.today().isoformat(), {})
    for key, value in counts.items():
        day[key] = day.get(key, 0) + value
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    except OSError:
        pass


def event():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def standing_down():
    return os.environ.get("INTELLIGENCE_DELEGATION_OFF") == "1"


# Asks whose answer lives in more places than one context should hold. Each is
# a shape rather than a topic: breadth over an unknown set, a sweep across
# repositories, or a question whose answer is a conclusion drawn from many
# files rather than the files themselves.
FANOUT = (
    (re.compile(r"\b(?:every|all|each)\s+(?:\w+\s+){0,2}"
                r"(?:file|files|repo|repos|project|projects|site|sites|page|"
                r"pages|component|components|test|tests|route|routes|table|"
                r"tables|script|scripts|skill|skills|function|functions)\b",
                re.I),
     "a set whose members are independent"),
    (re.compile(r"\b(?:across|throughout)\s+(?:the\s+)?"
                r"(?:codebase|repo|repos|project|projects|tree|sites?)\b", re.I),
     "a sweep across the tree"),
    (re.compile(r"\b(?:find|search|locate|look)\s+(?:for\s+|through\s+)?"
                r"(?:\w+\s+){0,3}(?:everywhere|anywhere|all\b)", re.I),
     "a search with no known target"),
    (re.compile(r"\b(?:which|what|where)\s+(?:\w+\s+){0,2}"
                r"(?:files?|places?|repos?|projects?|modules?)\b", re.I),
     "a question answered by reading many files"),
    (re.compile(r"\b(?:audit|sweep|survey|inventory|catalogue|catalog)\b", re.I),
     "an inventory"),
    (re.compile(r"\bany(?:where|thing)\s+(?:that|which|else)\b", re.I),
     "an open-ended check"),
)

# The counter-signal. A prompt naming one thing is answered by opening it, and
# an agent sent to do that returns the same bytes a call would have, later.
NARROW = re.compile(
    r"\b(?:this file|that file|the file|this line|just the|only the|one line)\b",
    re.I,
)


def guard_prompt():
    """The check that runs on every prompt, speaking when it finds something."""
    if standing_down():
        return 0
    ev = event()
    prompt = str(ev.get("prompt") or "")
    if not prompt.strip():
        return 0

    shape = None
    if not NARROW.search(prompt):
        for pattern, why in FANOUT:
            if pattern.search(prompt):
                shape = why
                break

    if not shape:
        return 0

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext":
            "This ask is %s. Dispatch agents for the reading and keep the "
            "conclusion, not the file dumps -- Explore for a read-only sweep, "
            "one agent per independent item in a single message so they run "
            "concurrently. Where a single call answers it, make the call: an "
            "agent per lookup costs more than it saves." % shape,
    }}))
    return 0


def turn_key(rows):
    """An identifier for the turn in progress, for latching once per turn."""
    for row in rows:
        for key in ("uuid", "parentUuid", "timestamp"):
            if row.get(key):
                return str(row[key])
    return "0"


def guard_probe():
    """Stop a survey that has grown past one context, with the rest unspent."""
    if standing_down() or os.environ.get("INTELLIGENCE_ALLOW_INLINE") == "1":
        return 0
    ev = event()
    name = str(ev.get("tool_name") or "")
    tool_input = ev.get("tool_input") or {}
    if name == "Bash":
        if not read_shaped(str(tool_input.get("command") or "")):
            return 0
    elif name not in PROBE_TOOLS:
        return 0

    path = ev.get("transcript_path")
    if not path or not Path(path).exists():
        return 0
    session = ev.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID")

    if checklist_open(session):
        return 0

    rows = current_turn(path)
    if rows is None:
        return 0
    found = survey(rows)
    # An agent cannot delegate, and a turn already holding a subagent's answers
    # has done the thing the gate exists to ask for.
    if found.sidechain or found.agents:
        return 0
    if not found.wide:
        return 0

    # One redirect per turn. A gate that fires on every remaining call turns a
    # saving into a run spent arguing with a hook.
    key = turn_key(rows)
    latch = latch_path(session)
    try:
        if json.loads(latch.read_text()).get("turn") == key:
            return 0
    except (OSError, ValueError):
        pass
    try:
        latch.parent.mkdir(parents=True, exist_ok=True)
        latch.write_text(json.dumps({"turn": key, "probes": found.probes}) + "\n")
    except OSError:
        pass

    record(redirects=1)
    sys.stderr.write(
        "\nBLOCKED: this survey belongs to an agent.\n\n"
        "  %d read-shaped calls over %d targets, none of it delegated.\n\n"
        "Everything read here stays in the window for the rest of the run and "
        "is paid\nfor again on every later request. Hand the rest to an agent "
        "and keep what it\nconcludes: Explore for a read-only sweep, or one "
        "agent per independent target\nin a single message so they run "
        "concurrently. Read directly only what has to\nbe quoted or edited "
        "here.\n\nINTELLIGENCE_ALLOW_INLINE=1 exempts a survey that cannot "
        "leave one context.\n" % (found.probes, len(found.targets))
    )
    return 2


WORD = re.compile(r"\S+")
QUOTED_PATH = re.compile(r"[~./][^\s'\"`,;:]*|\b[\w./-]+\.[A-Za-z0-9]{1,6}\b")


def trivial_dispatch(prompt):
    """Whether an agent is being sent to do what one call does.

    The test is a short instruction naming a path that is already on disk. An
    agent costs a context of its own, a model turn to write the prompt and
    another to read the answer; sent after a file it can name, all of that
    stands in for one read.
    """
    if len(WORD.findall(prompt)) >= 25:
        return None
    # Sentence punctuation reads as a path to any pattern loose enough to catch
    # a bare filename, and a lone "." resolves to the working directory, so a
    # candidate has to carry a name. A directory that does resolve is breadth,
    # which is the case for an agent rather than against one.
    named = [m.group(0).rstrip(".,;:)!?") for m in QUOTED_PATH.finditer(prompt)]
    named = [c for c in named if re.search(r"[A-Za-z0-9]", c)]
    on_disk = [c for c in named if os.path.isfile(os.path.expanduser(c))]
    if len(on_disk) == 1 and len(named) <= 2:
        return on_disk[0]
    return None


def guard_agent():
    """Refuse a dispatch that costs more than the call it replaces."""
    if standing_down():
        return 0
    ev = event()
    if str(ev.get("tool_name") or "") not in AGENT_TOOLS:
        return 0
    prompt = str((ev.get("tool_input") or {}).get("prompt") or "")
    target = trivial_dispatch(prompt)
    if not target:
        return 0
    record(spam_refused=1)
    sys.stderr.write(
        "\nBLOCKED: this agent is standing in for one call.\n\n"
        "  The prompt is %d words and names %s, which is on disk.\n\n"
        "An agent costs a context of its own plus a turn to brief it and a turn "
        "to read\nit back. Read the file. Agents earn their cost on breadth: "
        "many targets, or an\nanswer that would take more reading than one "
        "context should hold.\n"
        % (len(WORD.findall(prompt)), target)
    )
    return 2


def guard_stop():
    """Record what the turn did, so the ledger can show the trend."""
    if standing_down():
        return 0
    ev = event()
    if ev.get("stop_hook_active"):
        return 0
    path = ev.get("transcript_path")
    if not path or not Path(path).exists():
        return 0
    rows = current_turn(path)
    if rows is None:
        return 0
    found = survey(rows)
    counts = {"turns": 1, "probes": found.probes}
    if found.agents:
        counts["delegated"] = 1
    elif found.wide:
        counts["inline_surveys"] = 1
    record(**counts)
    return 0


def report():
    ledger = {}
    try:
        ledger = json.loads(ledger_path().read_text())
    except (OSError, ValueError):
        pass
    if not ledger:
        print("delegation: nothing recorded yet")
    else:
        print("%-12s %6s %7s %8s %7s %6s %8s"
              % ("day", "turns", "probes", "agented", "swept", "redir",
                 "refused"))
        for day in sorted(ledger):
            row = ledger[day]
            print("%-12s %6d %7d %8d %7d %6d %8d"
                  % (day, row.get("turns", 0), row.get("probes", 0),
                     row.get("delegated", 0), row.get("inline_surveys", 0),
                     row.get("redirects", 0), row.get("spam_refused", 0)))
    path = sys.argv[2] if len(sys.argv) > 2 else ""
    if path and Path(path).exists():
        fresh, cached, out = spend(tail_rows(path, 1 << 30)[0])
        print("\ntranscript: %s fresh in, %s cached in, %s out"
              % (format(fresh, ","), format(cached, ","), format(out, ",")))
    return 0


def install():
    """Wire the hooks, putting back anything a sync dropped."""
    settings = INTELLIGENCE / "settings.json"
    try:
        data = json.loads(settings.read_text())
    except Exception:
        return 1
    tool = "~/.intelligence/tools/delegation-guard.py"
    wanted = [
        ("UserPromptSubmit", None, "%s guard-prompt" % tool),
        ("SessionStart", "*", "%s install" % tool),
    ]
    changed = False
    for hook_event, matcher, command in wanted:
        entries = data.setdefault("hooks", {}).setdefault(hook_event, [])
        if any(command in h.get("command", "")
               for m in entries for h in m.get("hooks", [])):
            continue
        entry = {"hooks": [{"type": "command", "command": command,
                            "timeout": 10}]}
        if matcher:
            entry["matcher"] = matcher
        entries.append(entry)
        changed = True
        print("wired %s" % hook_event)
    # The probe, agent and stop verbs are reached through the dispatcher rather
    # than their own entries, so a missing registry row is what to report.
    try:
        if "delegation-guard.py" not in (INTELLIGENCE / "tools" / "guard-hub.py").read_text():
            print("guard-hub.py carries no delegation rows; the probe and "
                  "agent gates are not wired", file=sys.stderr)
    except OSError:
        pass
    if changed:
        settings.write_text(json.dumps(data, indent=2) + "\n")
    return 0


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "guard-prompt":
        return guard_prompt()
    if verb == "guard-probe":
        return guard_probe()
    if verb == "guard-agent":
        return guard_agent()
    if verb == "guard-stop":
        return guard_stop()
    if verb == "report":
        return report()
    if verb == "install":
        return install()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
