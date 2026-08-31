#!/usr/bin/env python3
"""One spawn per hook event, however many guards are wired behind it.

Wired one by one, every hook event starts an interpreter per guard behind it,
and most of those read the event and exit 0.
This dispatcher reads the event once, answers "could this guard possibly act"
in-process from the registry below, and execs only the guards whose answer is
yes, with the original bytes on stdin. A guard's judgment stays its own: every
precondition here is a strict superset of the guard's own first gate, taken
from the guard's source, so anything the guard would have done still happens
and everything else costs a string scan or a stat instead of a process.

  pre     PreToolUse dispatcher
  post    PostToolUse dispatcher
  stop    Stop dispatcher
  prompt  UserPromptSubmit dispatcher
  bench   time a no-op event through each dispatcher

All firing guards run; every one's output is forwarded; the exit is 2 when any
blocked. INTELLIGENCE_HUB_TRACE=1 names each exec on stderr, which is how the
parity cases watch the fast path stay empty.
"""
import json
import os
import re
import subprocess
import sys
import time
from hashlib import sha256
from pathlib import Path

HOME = Path.home()


def _tree():
    """The config tree this dispatcher belongs to.

    The directory above this file is that tree wherever the file lives — the
    installed config, a bare checkout in CI, or the copy a case run points a
    test target at — so the guards exec'd are always this copy's siblings. The
    installed tree is the fallback for a copy lifted out of any tree.
    """
    root = Path(__file__).resolve().parent.parent
    if (root / "tools").is_dir() and (root / "scripts").is_dir():
        return root
    return HOME / ".intelligence"


INTELLIGENCE = _tree()
TOOLS = INTELLIGENCE / "tools"
SCRIPTS = INTELLIGENCE / "scripts"

ROBOT_FACE = "\U0001f916"

# The retired names intelligence-naming polices, spelled the way that tool
# itself spells them; intelligence-naming: names the alias by design.
LEGACY_DIR = ".claude"
LEGACY_MEMORY = "CLAUDE.md"


def state_root():
    """Where the pass engines keep their state.

    An explicit override, then a remote session's own root outside the config
    tree, then the tree's own state directory.
    """
    override = os.environ.get("INTELLIGENCE_STATE_DIR")
    if override:
        return Path(override)
    if os.environ.get("CLAUDE_CODE_REMOTE"):
        return HOME / ".pass-state"
    return INTELLIGENCE / "state"


def session_id(payload):
    return payload.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID")


def run_pointer_exists(kind, payload, own_only=False):
    """Whether a checklist engine could resolve an open run.

    The engines read <state>/<kind>-runs/current-<session>.json, falling back
    to the shared current.json; with no pointer file at all, every one of their
    hook verbs is a proven exit 0.
    """
    runs = state_root() / ("%s-runs" % kind)
    sid = session_id(payload)
    if sid and (runs / ("current-%s.json" % sid)).is_file():
        return True
    if not own_only and (runs / "current.json").is_file():
        return True
    if own_only and not sid and (runs / "current.json").is_file():
        return True
    return False


# How recently a run's own state has to have been written for the run to count as
# in flight. Every resolve, verify and probe rewrites it, so a run somebody is
# working touches this file constantly and a run nobody is working goes quiet.
IN_FLIGHT_SECONDS = int(os.environ.get("INTELLIGENCE_IN_FLIGHT_SECONDS") or 300)


def run_in_flight(kind, payload):
    """Whether somebody is still working this run.

    Subagents inherit the session id of the agent that spawned them, so an open
    run being worked and an open run walked away from carry the same owner. Only
    recency separates them: the engines rewrite the run on every answer, so a
    file written seconds ago has somebody in it.

    Anything unreadable answers no. A guard that cannot tell still fires.
    """
    if os.environ.get("INTELLIGENCE_IN_FLIGHT_OFF") == "1":
        return False
    try:
        runs = state_root() / ("%s-runs" % kind)
        sid = session_id(payload)
        pointer = runs / ("current-%s.json" % sid) if sid else None
        if pointer is None or not pointer.is_file():
            pointer = runs / "current.json"
        if not pointer.is_file():
            return False
        run_id = json.loads(pointer.read_text()).get("id")
        if not run_id:
            return False
        newest = 0.0
        for path in list(runs.glob("%s.json" % run_id)) + list(runs.glob("*-%s.json" % run_id)):
            newest = max(newest, path.stat().st_mtime)
        if not newest:
            return False
        return (time.time() - newest) < IN_FLIGHT_SECONDS
    except Exception:
        return False


def agents_working(payload):
    """Whether a subagent has taken a step lately.

    A subagent writes its transcript on every tool call, which makes that file a
    truer liveness signal than a run's own state: an agent part-way through one
    checklist leaves its other runs untouched for as long as that takes, and those
    runs are waiting rather than abandoned.

    The transcripts sit beside the session transcript, so the path is derived from
    the payload rather than named. A payload carrying no transcript answers no, the
    same as a directory with no subagents in it.
    """
    try:
        transcript = payload.get("transcript_path")
        sid = session_id(payload)
        if not transcript or not sid:
            return False
        subagents = Path(transcript).resolve().parent / sid / "subagents"
        if not subagents.is_dir():
            return False
        cutoff = time.time() - IN_FLIGHT_SECONDS
        return any(path.stat().st_mtime > cutoff for path in subagents.glob("*.jsonl"))
    except Exception:
        return False


def run_needs_answering(kind, payload):
    """An owned run that nobody is working."""
    if not run_pointer_exists(kind, payload, own_only=True):
        return False
    if os.environ.get("INTELLIGENCE_IN_FLIGHT_OFF") == "1":
        return True
    return not run_in_flight(kind, payload) and not agents_working(payload)


# The landing regexes the engines and passes gate on, matched as supersets:
# `git ... commit` however the tokens are spelled, `gh pr create`, and
# writing-pass's wider `gh pr edit`.
LANDING = re.compile(r"git(?:\s+\S+)*?\s+[\"']?commit\b|gh\s+[\"']?pr[\"']?\s+[\"']?(?:create|edit)\b")

GIT_WRITE = re.compile(
    r"\bgit\s+(?:-\S+(?:\s+\S+)?\s+)*(?:commit|merge|revert|cherry-pick|rebase|am|push|tag)\b"
    r"|\bgh\s+(?:pr|issue|release)\s+(?:create|edit|comment|merge|review)\b"
    r"|\bgh\s+api\b.*(?:-X|--method)\s*(?:POST|PATCH|PUT)\b", re.I)

MCP_GH_WRITE = re.compile(
    r"^mcp__github__.*(create|update|add|edit|merge|comment|push|delete|dispatch|request)", re.I)

GH_OBJECT = re.compile(r"github\.com/[^/\s\"]+/[^/\s\"]+/(?:pull|issues)/\d+")

# Each of these is the guard's own first gate, or a superset of it, so a call
# the guard would refuse always reaches it and everything else costs a scan.
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U0001F1E6-\U0001F1FF"
    "️✅❌❎✨⭐⭕❗❓❔❕"
    "❑⚡❤➕➖➗➰➿]")
MAIL_SEND = re.compile(
    r"\b(?:sendmail|msmtp|mailx|mutt|swaks)\b|\bmail\s+-s\b"
    r"|api\.(?:resend|sendgrid|mailgun|postmarkapp|brevo)\."
    r"|/api/(?:outreach|newsletter|mail)/send\b", re.I)
MAIL_TOOL = re.compile(
    r"(?:^|__)(?:outlook_send_mail|outlook_send_draft|outlook_forward_mail"
    r"|gmail_send_message|send_email|send_mail)$", re.I)
MAIL_EDIT = re.compile(
    r"(?:^|/)(?:mail|email|newsletter|outreach)/|api/outreach/send\.", re.I)
# A database tool call that can change structure or data, and the two shell
# doors that land a change no required check has read.
DB_WRITE_TOOL = re.compile(
    r"(?:^|__)(apply_migration|execute_sql|deploy_edge_function|pause_project|"
    r"restore_project|delete_branch|merge_branch|reset_branch|create_branch)$")
DB_OVERRIDE = re.compile(
    r"\bgh\s+pr\s+merge\b[^\n]*--admin\b"
    r"|\bgh\s+api\b[^\n]*-X\s*(?:DELETE|PUT|PATCH)\b[^\n]*/protection"
    r"|\bsupabase\s+(?:db\s+(?:push|reset|dump)|migration\s+(?:up|repair))\b",
    re.I)

# A promotion into the branch a host actually serves.
PROMOTED = re.compile(
    r"\bgh\s+pr\s+merge\b[^\n]*--base[= ]main\b"
    r"|\bgit\s+push\b[^\n]*\borigin\s+(?:HEAD:)?main\b"
    r"|\bgh\s+pr\s+merge\b(?![^\n]*--base)[^\n]*\bmain\b", re.I)

GIT_PUSH = re.compile(r"\bgit\b(?:\s+-\S+(?:\s+\S+)?)*\s+push\b")
STRIPE = re.compile(r"\bstripe\b|api\.stripe\.com", re.I)
SECRET_SHAPE = re.compile(
    r"AKIA|xox[baprs]-|[sr]k_live_|AIza|sk-ant-|sk-proj-|npm_|SG\.|eyJ"
    r"|-----BEGIN|://[^\s:@/\"']+:[^\s:@/\"']{6,}@")


# The read verbs delegation-guard measures a survey in, matched loosely here:
# the guard tokenizes and re-tests, so the hub only has to avoid spawning it for
# a command that cannot possibly be a read.
READ_VERB = re.compile(
    r"\b(?:cat|head|tail|grep|rg|find|ls|fd|wc|sed|awk|tree|stat|file|nl|cut"
    r"|sort|uniq|jq|diff|basename|dirname|readlink|du|column)\b")


def delegation_armed(payload):
    """Whether the delegation gates could act on this event."""
    if os.environ.get("INTELLIGENCE_DELEGATION_OFF") == "1":
        return False
    name = str(payload.get("tool_name") or "")
    if name != "Bash":
        return True
    return bool(READ_VERB.search(command_of(payload)))


def comment_guard_armed(payload):
    """Whether comment-guard could act on this event.

    Its drift branch fires on any call while the writing-comments standard's
    stamped section disagrees with the stamp, so that comparison happens here,
    at file-read cost; the content branch needs actual content.
    """
    if os.environ.get("INTELLIGENCE_ALLOW_COMMENT"):
        return False
    stamp = INTELLIGENCE / "state" / "comment-guard-source.sha"
    skill = INTELLIGENCE / "skills" / "writing-comments" / "SKILL.md"
    try:
        text = skill.read_text()
        section = text.split("## Provenance Is Not Purpose", 1)[1]
        section = section.split("\n## ", 1)[0]
        digest = sha256(section.encode()).hexdigest()
        if not stamp.is_file() or stamp.read_text().strip() != digest:
            return True
    except (OSError, IndexError):
        return True
    return False


def edited_content(payload):
    ti = payload.get("tool_input") or {}
    return "".join(str(ti.get(k) or "") for k in ("content", "new_string", "new_source"))


def edited_path(payload):
    ti = payload.get("tool_input") or {}
    return str(ti.get("file_path") or ti.get("notebook_path") or "")


def command_of(payload):
    return str((payload.get("tool_input") or {}).get("command") or "")


def cases_hook_armed(payload, raw):
    """cases.py hook-edit acts to surface a recorded failure, or to check an
    edited tool; either way the marker stat is mandatory on every edit."""
    if (INTELLIGENCE / "state" / ".cases-hook-failure").is_file():
        return True
    path = Path(edited_path(payload))
    name = path.name
    if not name.endswith(".py"):
        return False
    tests = TOOLS / "tests"
    if name.endswith("-cases.py"):
        return True
    if path.parent == SCRIPTS:
        return (tests / ("scripts-" + name[:-3] + "-cases.py")).is_file()
    return (tests / (name[:-3] + "-cases.py")).is_file()


def sync_hook_armed(payload, raw):
    """config-sync hook-edit stamps and forks only for a synced-path edit with
    no publish already pending."""
    target = edited_path(payload)
    if not target:
        return False
    try:
        rel = Path(target).resolve().relative_to(INTELLIGENCE)
    except (ValueError, OSError):
        return False
    if str(rel).split("/")[0] not in ("skills", "scripts", "tools",
                                      "settings.json", "INTELLIGENCE.md"):
        return False
    stamp = INTELLIGENCE / "state" / ".config-sync-scheduled"
    try:
        return int(time.time()) - int(stamp.read_text().strip() or 0) >= 40
    except (OSError, ValueError):
        return True


def transcript_has_schedule(payload):
    path = payload.get("transcript_path") or ""
    if not path or os.environ.get("INTELLIGENCE_SKIP_ROUTINE_GUARD"):
        return False
    try:
        with open(path, "rb") as handle:
            # The tail overlaps consecutive chunks so a marker split across a
            # read boundary still matches; searching each chunk alone would
            # miss it.
            tail = b""
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                if b"[SCHEDULED TASK" in tail + chunk:
                    return True
                tail = chunk[-32:]
    except OSError:
        return False
    return False


def _nearest(kind, name):
    """The sibling copy where there is one, the installed tree where there is not.

    A tree holding only some of the guards -- a profile a set of gates was
    adopted into, a checkout carrying a subset -- otherwise drops the rest
    without saying so, and a guard that was skipped reads exactly like a guard
    that passed.
    """
    here = (INTELLIGENCE / kind) / name
    if here.is_file():
        return here
    return (HOME / ".intelligence" / kind) / name


def tool(name, *verb):
    return [str(_nearest("tools", name)), *verb]


def script(name, *verb):
    return [str(_nearest("scripts", name)), *verb]


# One row per wired guard: event, tool-name test, argv, precondition over the
# parsed payload and the raw stdin text. A row fires when both match; when()
# errs toward running the guard, since the guard itself stays the authority.
def registry():
    is_bash = lambda t: t == "Bash"
    is_edit = lambda t: t in ("Write", "Edit", "NotebookEdit")
    is_post_edit = lambda t: t in ("Write", "Edit", "MultiEdit")
    is_skill = lambda t: t == "Skill"
    is_read = lambda t: t in ("Read", "Bash", "NotebookRead")
    mcp_chrome = lambda t: t.startswith("mcp__claude-in-chrome__")
    mcp_github = lambda t: t.startswith("mcp__github__")

    def skill_name(p):
        return str((p.get("tool_input") or {}).get("skill") or "")

    def legacy_name_present(text):
        return LEGACY_DIR in text or LEGACY_MEMORY in text

    return {
        "pre": [
            (is_bash, script("git-develop-base-guard.sh", "guard-pr"),
             lambda p, raw: "gh pr create" in raw),
            (is_bash, tool("seo-pass.py", "guard-land"),
             lambda p, raw: LANDING.search(command_of(p))
             and run_pointer_exists("seo", p)),
            (is_bash, tool("perf-pass.py", "guard-land"),
             lambda p, raw: LANDING.search(command_of(p))
             and run_pointer_exists("perf", p)),
            (is_bash, tool("stack-pass.py", "guard-land"),
             lambda p, raw: LANDING.search(command_of(p))
             and run_pointer_exists("stack", p)),
            (is_bash, tool("design-pass.py", "guard-land"),
             lambda p, raw: LANDING.search(command_of(p))
             and run_pointer_exists("design", p)),
            (is_bash, tool("db-pass.py", "guard-land"),
             lambda p, raw: LANDING.search(command_of(p))
             and run_pointer_exists("db", p)),
            (is_bash, tool("google-pass.py", "guard-land"),
             lambda p, raw: LANDING.search(command_of(p))
             and run_pointer_exists("google", p)),
            (is_bash, tool("version-badge.py", "guard"),
             lambda p, raw: LANDING.search(command_of(p))),
            (is_bash, tool("writing-pass.py", "guard"),
             lambda p, raw: LANDING.search(command_of(p))),
            (is_bash, script("github-no-attribution.py", "guard"),
             lambda p, raw: GIT_WRITE.search(command_of(p)) and re.search(
                 r"claude|/code/session|%s" % ROBOT_FACE, command_of(p), re.I)),
            (is_bash, script("version-bump-guard.sh", "guard-pr"),
             lambda p, raw: "gh pr create" in raw
             and ("--base develop" in raw or "--base=develop" in raw)),
            (is_bash, tool("comment-guard.py", "guard-bash"),
             lambda p, raw: command_of(p)
             and ("<<" in command_of(p) or comment_guard_armed(p))),
            (is_bash, tool("intelligence-naming.py", "guard-bash"),
             lambda p, raw: not os.environ.get("INTELLIGENCE_ALLOW_LEGACY_NAME")
             and legacy_name_present(command_of(p))),
            (is_bash, tool("ai-attribution-guard.py", "guard-bash"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_AI_ATTRIBUTION") != "1"
             and GIT_WRITE.search(command_of(p))),
            (is_bash, tool("github-route-guard.py", "guard"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_GH") != "1"
             and re.search(r"\bgh\b", command_of(p))),
            (is_bash, tool("chrome-guard.py", "guard"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_CHROME") != "1"
             and re.search(r"chrom", command_of(p), re.I)),
            (is_edit, tool("worktree.py", "guard"),
             lambda p, raw: not os.environ.get("INTELLIGENCE_ALLOW_PRIMARY_WRITES")
             and edited_path(p)
             and not os.path.expanduser(edited_path(p)).startswith(str(INTELLIGENCE))),
            (is_edit, tool("perf-pass.py", "guard-edit"),
             lambda p, raw: run_pointer_exists("perf", p)),
            (is_edit, tool("comment-guard.py", "guard-edit"),
             lambda p, raw: not os.environ.get("INTELLIGENCE_ALLOW_COMMENT")
             and (edited_content(p) or comment_guard_armed(p))),
            (is_post_edit, tool("blog-variation-guard.py", "guard-edit"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_BLOG_DUPLICATE") != "1"
             and "data/blog" in edited_path(p).replace("\\", "/")),
            (is_edit, tool("intelligence-naming.py", "guard-edit"),
             lambda p, raw: not os.environ.get("INTELLIGENCE_ALLOW_LEGACY_NAME")
             and re.search(r"claude", edited_path(p) + edited_content(p), re.I)),
            (is_skill, tool("design-pass.py", "guard-skill"),
             lambda p, raw: re.fullmatch(r"(?:.*:)?design", skill_name(p))),
            (lambda t: t == "EnterWorktree",
             script("git-develop-base-guard.sh", "guard-worktree"),
             lambda p, raw: True),
            (mcp_github, script("github-no-attribution.py", "guard"),
             lambda p, raw: MCP_GH_WRITE.match(p.get("tool_name") or "")
             and re.search(r"claude|generated|/code/session",
                           json.dumps(p.get("tool_input") or {}), re.I)),
            (lambda t: t == "Bash" or t in ("Read", "Grep", "Glob",
                                            "NotebookRead"),
             tool("delegation-guard.py", "guard-probe"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_INLINE") != "1"
             and delegation_armed(p)),
            (lambda t: t in ("Agent", "Task"),
             tool("delegation-guard.py", "guard-agent"),
             lambda p, raw: os.environ.get("INTELLIGENCE_DELEGATION_OFF") != "1"),
            (lambda t: t in ("Write", "Edit", "NotebookEdit", "Read", "Bash",
                             "MultiEdit", "NotebookRead"),
             tool("scratchpad-guard.py", "guard"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_SCRATCHPAD") != "1"
             and "/scratchpad" in raw),
            (is_bash, tool("reporter-site-guard.py", "guard"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_SITE_RENAME") != "1"
             and re.search(r"\bgit\b[^|;&]*\bcommit\b", command_of(p))),
            (mcp_chrome, tool("chrome-guard.py", "guard"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_CHROME") != "1"),
            (is_bash, tool("mail-guard.py", "guard-bash"),
             lambda p, raw: os.environ.get("INTELLIGENCE_MAIL_OFF") != "1"
             and MAIL_SEND.search(command_of(p))),
            (lambda t: bool(MAIL_TOOL.search(t)),
             tool("mail-guard.py", "guard-mcp"),
             lambda p, raw: os.environ.get("INTELLIGENCE_MAIL_OFF") != "1"),
            (is_edit, tool("mail-guard.py", "guard-edit"),
             lambda p, raw: os.environ.get("INTELLIGENCE_MAIL_OFF") != "1"
             and MAIL_EDIT.search(edited_path(p).replace("\\", "/"))),
            (is_bash, tool("emoji-guard.py", "guard-bash"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_EMOJI") != "1"
             and EMOJI.search(command_of(p))),
            (is_edit, tool("emoji-guard.py", "guard-edit"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_EMOJI") != "1"
             and EMOJI.search(edited_path(p) + edited_content(p))),
            (is_bash, tool("push-flow-guard.py", "guard-bash"),
             lambda p, raw: os.environ.get(
                 "INTELLIGENCE_ALLOW_DIRECT_PUSH") != "1"
             and GIT_PUSH.search(command_of(p))),
            (is_bash, tool("stripe-guard.py", "guard-bash"),
             lambda p, raw: STRIPE.search(command_of(p))),
            (lambda t: "stripe_api_write" in t or "manage_stripe_accounts" in t,
             tool("stripe-guard.py", "guard-mcp"),
             lambda p, raw: True),
            (is_bash, tool("db-write-guard.py", "guard-bash"),
             lambda p, raw: DB_OVERRIDE.search(command_of(p))),
            (lambda t: bool(DB_WRITE_TOOL.search(t)),
             tool("db-write-guard.py", "guard-mcp"),
             lambda p, raw: True),
            (is_bash, tool("secret-shape-guard.py", "guard-bash"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_SECRET") != "1"
             and SECRET_SHAPE.search(command_of(p))),
            (is_edit, tool("secret-shape-guard.py", "guard-edit"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_SECRET") != "1"
             and SECRET_SHAPE.search(edited_content(p))),
        ],
        "post": [
            (is_bash, tool("serving-guard.py", "track"),
             lambda p, raw: PROMOTED.search(command_of(p))),
            (lambda t: t == "Bash" or t.startswith("mcp__github__"),
             script("github-no-attribution.py", "strip"),
             lambda p, raw: GH_OBJECT.search(
                 json.dumps(p.get("tool_response") or {})
                 + json.dumps(p.get("tool_input") or {}))
             or (all(k in (p.get("tool_input") or {}) for k in ("owner", "repo"))
                 and any(k in (p.get("tool_input") or {})
                         for k in ("pullNumber", "issue_number", "number")))),
            (is_skill, tool("design-pass.py", "hook-skill"),
             lambda p, raw: re.fullmatch(r"(?:.*:)?(?:design-checklist|design)",
                                         skill_name(p))),
            (is_skill, tool("seo-pass.py", "hook-skill"),
             lambda p, raw: re.fullmatch(r"(?:.*:)?seo-checklist", skill_name(p))),
            (is_skill, tool("perf-pass.py", "hook-skill"),
             lambda p, raw: re.fullmatch(r"(?:.*:)?(?:perf-checklist|checklist)",
                                         skill_name(p))),
            (is_skill, tool("stack-pass.py", "hook-skill"),
             lambda p, raw: re.fullmatch(r"(?:.*:)?stack-checklist", skill_name(p))),
            (is_skill, tool("db-pass.py", "hook-skill"),
             lambda p, raw: re.fullmatch(r"(?:.*:)?db-checklist", skill_name(p))),
            (is_skill, tool("google-pass.py", "hook-skill"),
             lambda p, raw: re.fullmatch(r"(?:.*:)?google-checklist", skill_name(p))),
            (is_read, tool("design-pass.py", "hook-read"),
             lambda p, raw: run_pointer_exists("design", p)),
            (is_read, tool("seo-pass.py", "hook-read"),
             lambda p, raw: run_pointer_exists("seo", p)),
            (is_read, tool("perf-pass.py", "hook-read"),
             lambda p, raw: run_pointer_exists("perf", p)),
            (is_read, tool("stack-pass.py", "hook-read"),
             lambda p, raw: run_pointer_exists("stack", p)),
            (is_post_edit, [str(TOOLS / "tests" / "cases.py"), "hook-edit"],
             cases_hook_armed),
            (is_post_edit, tool("perf-pass.py", "hook-edit"),
             lambda p, raw: edited_path(p)
             and run_pointer_exists("perf", p, own_only=True)),
            (is_post_edit, tool("stack-pass.py", "hook-edit"),
             lambda p, raw: edited_path(p)
             and run_pointer_exists("stack", p, own_only=True)),
            (is_post_edit, tool("config-sync.py", "hook-edit"), sync_hook_armed),
        ],
        "stop": [
            (None, tool("seo-pass.py", "guard-stop"),
             lambda p, raw: run_needs_answering("seo", p)),
            (None, tool("perf-pass.py", "guard-stop"),
             lambda p, raw: run_needs_answering("perf", p)),
            (None, tool("stack-pass.py", "guard-stop"),
             lambda p, raw: run_needs_answering("stack", p)),
            (None, tool("design-pass.py", "guard-stop"),
             lambda p, raw: run_needs_answering("design", p)),
            (None, tool("db-pass.py", "guard-stop"),
             lambda p, raw: run_needs_answering("db", p)),
            (None, tool("google-pass.py", "guard-stop"),
             lambda p, raw: run_needs_answering("google", p)),
            (None, tool("serving-guard.py", "guard-stop"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_UNSERVED") != "1"
             and (state_root() / "serving-pending.json").is_file()),
            (None, tool("intelligence-naming.py", "guard-stop"),
             lambda p, raw: not os.environ.get("INTELLIGENCE_ALLOW_LEGACY_NAME")),
            (None, tool("stated-facts.py", "guard-stop"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_STALE_FACT") != "1"),
            (None, tool("routine-guard.py", "guard-stop"),
             lambda p, raw: transcript_has_schedule(p)),
            (None, tool("concise-guard.py", "guard-stop"),
             lambda p, raw: os.environ.get("INTELLIGENCE_CONCISE_OFF") != "1"
             and not p.get("stop_hook_active")),
            (None, tool("reply-shape-guard.py", "guard-stop"),
             lambda p, raw: os.environ.get("INTELLIGENCE_REPLY_SHAPE_OFF") != "1"
             and not p.get("stop_hook_active")),
            # The one stop guard wired the other way round: it judges the reply
            # written after a refusal, which is the pass every other guard here
            # stands down for.
            (None, tool("repetition-guard.py", "guard-stop"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_REPEAT") != "1"
             and bool(p.get("stop_hook_active"))),
            (None, tool("delegation-guard.py", "guard-stop"),
             lambda p, raw: os.environ.get("INTELLIGENCE_DELEGATION_OFF") != "1"
             and not p.get("stop_hook_active")),
            (None, tool("day-plan.py", "guard-stop"),
             lambda p, raw: os.environ.get("INTELLIGENCE_DAYPLAN_OFF") != "1"
             and not p.get("stop_hook_active")
             # The plans sit under the resolved state root, which a container
             # puts off the config tree; reading the tree path there finds
             # nothing and stands the guard down in the one environment whose
             # ending takes the unshared work with it.
             and (state_root() / "day-plans").is_dir()),
            (None, tool("remote-access.py", "guard-stop"),
             lambda p, raw: os.environ.get("INTELLIGENCE_REMOTE_OFF") != "1"
             and not p.get("stop_hook_active")),
            (None, tool("emoji-guard.py", "guard-stop"),
             lambda p, raw: os.environ.get("INTELLIGENCE_ALLOW_EMOJI") != "1"
             and not p.get("stop_hook_active")),
            (None, tool("plain-brief-guard.py", "guard-stop"),
             lambda p, raw: os.environ.get("INTELLIGENCE_PLAIN_OFF") != "1"
             and not p.get("stop_hook_active")),
        ],
        "prompt": [
            (None, tool("delegation-guard.py", "guard-prompt"),
             lambda p, raw: os.environ.get("INTELLIGENCE_DELEGATION_OFF") != "1"),
            (None, tool("concise-guard.py", "guard-prompt"),
             lambda p, raw: os.environ.get("INTELLIGENCE_CONCISE_OFF") != "1"),
        ],
    }


def record(event, argv, tool, code):
    """One line per guard that ran, so what a guard has done is a reading.

    Best effort in both directions: the decision is the product, so a failure to
    write this never changes it, and a guard that was skipped writes nothing
    rather than a row saying it passed.
    """
    try:
        log = state_root() / "guard-log.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "event": event, "guard": Path(argv[0]).name,
               "verb": argv[1] if len(argv) > 1 else "",
               "tool": tool, "exit": code}
        with open(log, "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:
        pass


# cases.py hook-edit exits 2 to surface an overdue failure, and the redirects
# and refusals exit 2 to block; both travel through unchanged.
def dispatch(event):
    raw = sys.stdin.buffer.read().decode("utf-8", "replace")
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = {}
    name = str(payload.get("tool_name") or "")
    trace = os.environ.get("INTELLIGENCE_HUB_TRACE") == "1"
    blocked = False
    for tools_match, argv, when in registry().get(event, []):
        if tools_match is not None and not tools_match(name):
            continue
        try:
            due = bool(when(payload, raw))
        except Exception:
            due = True
        if not due:
            continue
        if trace:
            print("hub exec: %s" % " ".join(argv), file=sys.stderr)
        try:
            done = subprocess.run(argv, input=raw.encode(), timeout=600,
                                  capture_output=True)
        except (OSError, subprocess.TimeoutExpired) as err:
            print("guard-hub: %s did not run (%s)" % (argv[0], err), file=sys.stderr)
            continue
        sys.stdout.buffer.write(done.stdout)
        sys.stderr.buffer.write(done.stderr)
        record(event, argv, name, done.returncode)
        if done.returncode == 2:
            blocked = True
    return 2 if blocked else 0


def bench():
    ordinary = {"tool_name": "Bash", "tool_input": {"command": "git status"},
                "cwd": os.getcwd()}
    read = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}}
    halt = {"stop_hook_active": True}
    me = str(Path(__file__).resolve())
    for verb, event in (("pre", ordinary), ("post", read), ("stop", halt),
                        ("prompt", {"prompt": "status"})):
        t0 = time.time()
        subprocess.run([me, verb], input=json.dumps(event).encode(),
                       capture_output=True)
        print("%s: %d ms" % (verb, (time.time() - t0) * 1000))
    return 0


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb in ("pre", "post", "stop", "prompt"):
        return dispatch(verb)
    if verb == "bench":
        return bench()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
