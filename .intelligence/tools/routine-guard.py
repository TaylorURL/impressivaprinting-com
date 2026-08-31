#!/usr/bin/env python3
"""Stop hook: a scheduled run does not end until it has done its phases and reported them.

A routine fires with nobody watching. Its report went into the session
transcript, which is the one place its owner does not look -- so a run could do
everything right, write it all up, and reach no one. The report was not missing;
it was addressed to an empty room.

So the deliverable of a scheduled run is a report that reached somebody, not
the reply. The summary is wrapped in `<routine_summary>` and goes out whichever
door is open: `PushNotification`, which puts the first sentence on a phone and
the whole thing in an inbox, or a post to the board webhook, which is the only
one a machine with no terminal attached has. What counts is the delivery rather
than the attempt, so a call whose result comes back `Not sent` leaves the run
exactly as silent as one that never wrote anything. This refuses to end such a
turn until a report has landed, and refuses a token one: a summary short enough
to say nothing, or naming no repo, path, pull request or URL, is the shape a
report takes when it was written to satisfy a check.

The phases get the same treatment, and the routine itself is what says how. Each
phase in `daily-maintenance.md` carries its own gates as markers:

    # Phase 0 -- Pull the shared ledgers
    <!-- enforce run: pass-state(\\.py)?\\s+pull -->

    # Phase 3 -- Platform health
    <!-- enforce report: Vercel -->

A `run:` gate is a pattern that must match something the turn actually executed
-- a shell command, a skill invocation. A `report:` gate must match the summary
that went out, which is how a phase whose work is reading and judging still
answers for itself: it has to say what it found, by name. A phase carrying no
marker at all fails the run, so a phase added later cannot arrive unenforced.

What is required of a `run:` gate is the attempt, not the outcome: a pull that
fails for want of a network is a result the run reports, while a pull never made
is a run that starts by re-sweeping every repo it touches.

Some of the routine's rules are prohibitions rather than steps, and those are
checked the other way round -- the run is refused when the transcript shows one
was crossed.

The terminal reply is then free to be what it should be -- a few sentences. A
scheduled turn carries no human instruction, so it owes no point-by-point ledger.

  guard-stop   Stop hook: refuse to end a scheduled run left undone or unreported
  gates        Print the gate list read out of the routine, and where it was found

INTELLIGENCE_ROUTINE_FILE names the routine explicitly; otherwise it is searched for.
INTELLIGENCE_SKIP_ROUTINE_GUARD=1 stands the whole guard down.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path


def _shared():
    """The shared _lib module, loaded by path.

    Hooks run this tool as a script from arbitrary directories, so the module
    is found beside this file rather than through sys.path, with the installed
    tree as the fallback for a copy executed from elsewhere.
    """
    here = Path(__file__).resolve().parent / "_lib.py"
    path = here if here.is_file() else Path.home() / ".intelligence" / "tools" / "_lib.py"
    spec = importlib.util.spec_from_file_location("intelligence_tools_lib", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A Stop hook that crashes on a half-synced tree blocks every reply, so a
# missing _lib stands the guard down instead: guard-stop notes it and exits 0.
try:
    _lib = _shared()
except Exception:
    _lib = None

# The harness stamps this on a turn the scheduler started. It is the only
# reliable mark: the prompt text itself is whatever the routine was written as.
SCHEDULED = re.compile(r"\[SCHEDULED TASK[^\]]*\]", re.I)

# Which routine fired, read from its own prompt. A routine that names a task
# file owes that file's phases; one that watches a pull request owes a report
# and nothing else.
MAINTENANCE = re.compile(r"\bmaintenance\b", re.I)

# The task file a prompt points at. Every scheduled routine here is an
# orientation wrapper around one, so the phases come from whichever file its
# prompt named. A task file is lower case; the operating agreement travelling
# beside them is not, and declares no phases.
TASK_IN_PROMPT = re.compile(r"routine/([\w.-]+\.md)")
NOT_A_TASK = re.compile(r"^[A-Z_]+\.md$")

# Below this a summary is a receipt rather than a report. A day's sweep across
# every repo does not fit here, and nothing shorter is worth waking someone for.
MIN_SUMMARY_CHARS = 400

# The same anchor rule the answer guard uses: a report has to name something
# that can be opened. "Everything is fine" is true of somewhere and silent
# about where.
ANCHOR = re.compile(
    r"`[^`]+`"
    r"|https?://\S+"
    r"|\(#\d+\)|#\d{1,5}\b"
    r"|[\w.-]+/[\w./-]+"
    r"|\b[\w-]+\.(?:md|py|sh|json|jsx|js|mjs|css|ts|tsx|yml|yaml|txt)\b"
)

SUMMARY = re.compile(r"<routine_summary>(.*?)</routine_summary>", re.S | re.I)

PHASE = re.compile(r"^#\s*Phase\s+([\w.]+)\s*[-—]*\s*(.*)$", re.M)
MARKER = re.compile(r"<!--\s*enforce\s+(run|report)\s*:\s*(.+?)\s*-->")

# A routine that speaks on every firing whether or not anything happened is
# one nobody reads, which leaves it as silent in failure as the thing it
# watches. This marker lets such a routine end without a notification -- but
# only once the command named here has actually run, so a quiet run and a run
# that never looked stay different results.
QUIET = re.compile(r"<!--\s*enforce\s+quiet\s*:\s*(.+?)\s*-->")

ROUTINE_NAME = Path("routine") / "daily-maintenance.md"

# The routine's own prohibitions, as they would appear in what the run executed.
# A step can be checked by asking whether it happened; these can only be checked
# by asking whether they did, so they are named here rather than in the routine's
# markers -- there is no phase for them to hang under, and they hold everywhere.
FORBIDDEN = (
    (r"push\b[^|;&\n]*--force(?:-with-lease)?[^|;&\n]*\b(?:main|develop)\b"
     r"|push\b[^|;&\n]*\b(?:main|develop)\b[^|;&\n]*--force",
     "force-pushed a protected branch"),
    (r"gh\s+pr\s+merge\b[^|;&\n]*--admin", "merged a pull request with --admin"),
    (r"gh\s+api\b[^|;&\n]*-X\s*DELETE[^|;&\n]*branches/[^|;&\n]*protection",
     "removed branch protection"),
)


def task_named(prompt):
    """The task file the prompt points at, or None."""
    for name in TASK_IN_PROMPT.findall(prompt or ""):
        if not NOT_A_TASK.match(name):
            return Path("routine") / name
    return None


# Actions no scheduled run takes on its own, whichever routine fired. A run
# fires with nobody watching, and money moved and messages sent are the two
# results that cannot be recalled once they land. Reading is untouched: these
# match the write, not the query beside it.
FORBIDDEN_CALLS = (
    (r"stripe_api_write", "made a write call to Stripe"),
    (r"\bstripe\s+(?:invoice|invoiceitem|subscription|subscription_schedule"
     r"|charge|refund|payment_intent|payout|customer)s?\s+"
     r"(?:create|update|delete|void|pay|send|finalize|cancel|mark_uncollectible)",
     "ran a Stripe write from the shell"),
    (r"api\.stripe\.com(?=[\s\S]{0,400}?(?:-X\s*(?:POST|DELETE|PUT)|--data|\s-d\s))"
     r"|(?:-X\s*(?:POST|DELETE|PUT)|--data|\s-d\s)(?=[\s\S]{0,400}?api\.stripe\.com)",
     "posted to the Stripe API"),
    (r"outlook_send_mail|outlook_send_draft|outlook_forward_mail",
     "sent mail from the owner's mailbox"),
    (r"(?:^|__)apply_migration\b", "applied a migration to a database"),
    (r"(?:^|__)deploy_edge_function\b", "deployed a function to a project"),
    (r"(?:^|__)pause_project\b", "paused a project"),
    (r"(?:^|__)restore_project\b", "restored a project"),
    (r"(?:^|__)delete_branch\b", "deleted a database branch"),
)


def turn_start(rows):
    """The index of the scheduled prompt that opened this turn, or None.

    Read from the bottom so a session that has been steered since the firing
    still measures the firing it is closing, not an earlier one.

    The marker opens the prompt, because that is where the runner stamps it. A
    turn that merely quotes the marker is a conversation about scheduled runs
    rather than one of them, and judging it as a run holds the session open on
    gates no routine declared.
    """
    for i in range(len(rows) - 1, -1, -1):
        row = rows[i]
        if row.get("type") != "user":
            continue
        content = (row.get("message") or {}).get("content")
        if isinstance(content, str) and SCHEDULED.match(content.lstrip()):
            return i
    return None


def prompt_text(rows, since):
    content = (rows[since].get("message") or {}).get("content")
    return content if isinstance(content, str) else ""


def tool_calls(rows, since):
    """Every tool call made since the turn opened, as (name, input)."""
    out = []
    for row in rows[since:]:
        content = (row.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                out.append((block.get("name") or "", block.get("input") or {}))
    return out


# A result that opens with one of these is the transport declining, not the
# report arriving.
UNDELIVERED = re.compile(r"^\s*(?:not sent|failed|error|could not)\b", re.I)

# The webhook the Pi already posts its boards through, which reaches somebody
# when a notification into an active terminal does not.
DISCORD = re.compile(r"discord(?:app)?\.com/api/webhooks/", re.I)


def result_text(block):
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(part.get("text") or "" for part in content
                        if isinstance(part, dict))
    return ""


def summaries(rows, since):
    """Every routine summary that actually reached somebody.

    A notification call is an attempt and its paired result says whether it was
    delivered. A run that reported to nobody is a silent run whatever its own
    transcript claims, so an undelivered attempt counts for nothing. A summary
    posted to the webhook counts, because the question is whether the report
    arrived rather than which door it used.
    """
    pending, out = {}, []
    for row in rows[since:]:
        content = (row.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                name = block.get("name") or ""
                args = block.get("input") or {}
                if name == "PushNotification":
                    body = args.get("message") or ""
                elif name == "Bash" and DISCORD.search(str(args.get("command") or "")):
                    body = str(args.get("command") or "")
                else:
                    continue
                found = SUMMARY.search(body)
                if found:
                    pending[block.get("id")] = found.group(1).strip()
            elif block.get("type") == "tool_result":
                text = pending.pop(block.get("tool_use_id"), None)
                if text is not None and not UNDELIVERED.match(result_text(block)):
                    out.append(text)
    return out


def ran(calls):
    """The text of everything the turn asked a tool to do.

    Shell commands and skill invocations both, joined, because a step can be
    taken either way -- `/skill-sync` and the script it runs are the same step.
    """
    parts = []
    for _, args in calls:
        for key in ("command", "skill", "args", "prompt", "description"):
            value = args.get(key)
            if isinstance(value, str):
                parts.append(value)
    return "\n".join(parts)


def call_texts(calls):
    """Each tool call as one string of its name and its arguments.

    Checked per call rather than over the joined transcript, so a read of the
    billing API and an unrelated command carrying a method flag cannot combine
    into a write neither of them made.
    """
    out = []
    for name, args in calls:
        try:
            body = json.dumps(args, default=str)
        except (TypeError, ValueError):
            body = str(args)
        out.append("%s %s" % (name, body))
    return out


def forbidden_calls(calls):
    """Every line a run crossed, as (why, what) pairs."""
    hits = []
    for text in call_texts(calls):
        for pattern, why in FORBIDDEN_CALLS:
            found = re.search(pattern, text, re.I)
            if found:
                hits.append((why, text[:200]))
                break
    return hits


def routine_path(cwd=None, name=None):
    """Where a routine's task file is on this machine, or None.

    Named outright by `INTELLIGENCE_ROUTINE_FILE`, else the file the firing
    prompt pointed at, else the daily pass. The guard is installed beside the
    other tools, where no routine file lives, so finding the checkout is part
    of the job rather than an edge case.
    """
    named = os.environ.get("INTELLIGENCE_ROUTINE_FILE")
    if named and Path(named).is_file():
        return Path(named)
    name = name or ROUTINE_NAME
    here = Path(__file__).resolve().parent.parent
    roots = [here, Path(cwd or "."), Path.home()]
    roots += [Path.home() / name for name in
              ("intelligence", "Projects", "IdeaProjects", "WebstormProjects")]
    for root in roots:
        candidate = root / name
        if candidate.is_file():
            return candidate
    for root in (Path(cwd or "."), Path.home()):
        try:
            for candidate in root.glob("*/" + str(name)):
                if candidate.is_file():
                    return candidate
        except OSError:
            pass
    return None


def strip_fences(text):
    """The text with every fenced code block blanked out.

    A fence holds display rather than instruction: the routine quotes a phase
    heading as an example of the marker syntax, and a parse that reads it counts
    a phase the routine never declared. Fenced lines become blank ones, so the
    offsets around them keep their meaning.
    """
    out, fence = [], None
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if fence is None:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                fence = stripped[:3]
                out.append("\n")
            else:
                out.append(line)
        else:
            if stripped.startswith(fence):
                fence = None
            out.append("\n")
    return "".join(out)


def gates_of(text):
    """Each phase in the routine, with the gates it declares.

    Returns a list of (phase label, [(kind, compiled pattern, source)]). A phase
    with an empty gate list is a phase that declared nothing, which the caller
    refuses on -- silence here would let a phase be added and never checked.
    """
    text = strip_fences(text)
    found = list(PHASE.finditer(text))
    out = []
    for i, match in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        body = text[match.end():end]
        label = ("Phase %s -- %s" % (match.group(1), match.group(2))).strip(" -")
        gates = []
        for kind, pattern in MARKER.findall(body):
            try:
                gates.append((kind, re.compile(pattern, re.I), pattern))
            except re.error:
                gates.append((kind, None, pattern))
        out.append((label, gates))
    return out


def refuse(reason, detail=""):
    sys.stderr.write(
        "BLOCKED: this scheduled run has not reported to anyone.\n\n"
        "  %s\n%s\n"
        "The transcript is not where this report is read. Wrap the summary in\n"
        "<routine_summary> tags and send it with PushNotification, whose first\n"
        "sentence becomes the phone banner and whose whole text becomes the email\n"
        "body, or post it to the board webhook where no terminal is attached.\n"
        "Put the run's findings in there -- what changed, what landed, what could\n"
        "not be done and why -- and name the repos, pull requests and paths, so a\n"
        "line can be opened rather than taken on trust.\n\n"
        "Then keep the reply here to a few sentences. It is a receipt, not the\n"
        "report.\n" % (reason, detail)
    )
    return 2


def refuse_phases(missing, source):
    sys.stderr.write(
        "BLOCKED: this maintenance run has %d unanswered phase gate(s).\n\n"
        "%s\n"
        "Each gate is declared by the routine itself, in\n"
        "  %s\n"
        "as an `enforce run:` or `enforce report:` marker under its phase. A run\n"
        "gate wants the step actually executed; a report gate wants the phase's\n"
        "findings named in the summary that goes out.\n\n"
        "A step that fails -- no network, no credentials, the repo unreachable --\n"
        "still counts as run: say so in the report and carry on. What does not\n"
        "count is not attempting it.\n"
        % (len(missing), "".join("  %s\n" % m for m in missing), source)
    )
    return 2


def refuse_forbidden(hits):
    sys.stderr.write(
        "BLOCKED: this run crossed %d line the routine draws.\n\n"
        "%s\n"
        "These are the actions no phase authorises, at any point, for any reason.\n"
        "Undo what can be undone, and say plainly in the report what was done and\n"
        "what it will take to put right.\n"
        % (len(hits), "".join("  %s\n    %s\n" % (why, cmd) for why, cmd in hits))
    )
    return 2


def quiet_allowed(text, done):
    """Whether this routine may end silently, given what the run executed."""
    found = QUIET.search(strip_fences(text))
    if not found:
        return False
    try:
        return bool(re.search(found.group(1), done, re.I))
    except re.error:
        return False


def check_phases(text, source, done, report):
    """Phase gates the run left unanswered, as lines ready to print."""
    missing = []
    for label, gates in gates_of(text):
        if not gates:
            missing.append("%s declares no enforce marker; it cannot be checked"
                           % label)
            continue
        for kind, pattern, raw in gates:
            if pattern is None:
                missing.append("%s: marker `%s` is not a valid pattern"
                               % (label, raw))
                continue
            haystack = done if kind == "run" else report
            if not pattern.search(haystack):
                missing.append("%s: nothing %s matches `%s`"
                               % (label, "run" if kind == "run" else "reported", raw))
    return missing


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "gates":
        path = routine_path()
        if not path:
            print("no routine found", file=sys.stderr)
            return 1
        print(path)
        for label, gates in gates_of(path.read_text(errors="ignore")):
            print("  %s" % label)
            for kind, _, raw in gates or []:
                print("      %-6s %s" % (kind, raw))
            if not gates:
                print("      (none declared)")
        return 0
    if mode != "guard-stop":
        print(__doc__.strip(), file=sys.stderr)
        return 2
    if os.environ.get("INTELLIGENCE_SKIP_ROUTINE_GUARD"):
        return 0
    if _lib is None:
        print("routine-guard: _lib.py unavailable; standing down", file=sys.stderr)
        return 0
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0

    path = payload.get("transcript_path")
    if not path or not Path(path).is_file():
        return 0
    rows = _lib.read_transcript(path)
    since = turn_start(rows)
    if since is None:
        return 0  # not a scheduled run; nothing here applies

    calls = tool_calls(rows, since)
    sent = summaries(rows, since)
    best = max(sent, key=len) if sent else ""

    crossed = forbidden_calls(calls)
    if crossed:
        return refuse_forbidden(crossed)

    prompt = prompt_text(rows, since)
    task = task_named(prompt)
    if task or MAINTENANCE.search(prompt):
        done = ran(calls)
        hits = []
        for pattern, why in FORBIDDEN:
            found = re.search(pattern, done, re.I)
            if found:
                hits.append((why, found.group(0)[:160]))
        if hits:
            return refuse_forbidden(hits)

        routine = routine_path(payload.get("cwd"), task)
        if not routine:
            return refuse_phases(
                ["the routine itself could not be found, so no phase can be checked"],
                "%s (set INTELLIGENCE_ROUTINE_FILE)" % (task or ROUTINE_NAME))
        text = routine.read_text(errors="ignore")
        silent = not sent and quiet_allowed(text, done)
        missing = [m for m in check_phases(text, routine, done, best)
                   if not (silent and "reported" in m)]
        if missing:
            return refuse_phases(missing, routine)
        if silent:
            return 0

    if not sent:
        return refuse("No report carrying a <routine_summary> reached anybody.")
    if len(best) < MIN_SUMMARY_CHARS:
        return refuse(
            "The summary sent is %d characters, under the %d a report needs."
            % (len(best), MIN_SUMMARY_CHARS),
            "\n  It reads: %r\n" % best[:200],
        )
    if not ANCHOR.search(best):
        return refuse(
            "The summary names nothing that can be opened.",
            "\n  No repo, path, pull request or URL appears in it.\n",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
