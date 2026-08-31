#!/usr/bin/env python3
"""The routines, held where they can be checked and rebuilt.

A routine's prompt, schedule, repository list and connectors exist at runtime
in one place, and the run history does not carry them. The files under
`routines/` are the copy that survives a deletion, and a copy that has fallen
behind the definition that fires reads as a backup without being one.

So the registry is checkable rather than descriptive. `check` answers for the
side that lives here: every routine has its config, its prompt and its task
file, every task file's phases declare the gates the stop guard reads out of
them, every schedule parses, no two scheduled runs fire in the same minute,
and a routine with no schedule names the webhook that fires it instead.
`diff` answers for the other side, against a live definition fetched with the
RemoteTrigger tool, which no script can reach on its own.

The rotation is here for the same reason. Four of the five checklists run only
when somebody asks, so the weekly pass takes the projects longest since their
last sweep, and that ordering has to survive the run that produced it. A ledger
in the repository travels; a ledger on one machine is a rotation that restarts
every time the work moves.

  routine-sync.py list                    every routine, by cadence
  routine-sync.py check                   the checked-in side, validated
  routine-sync.py mirrored                the machines still run what is held here
  routine-sync.py health --file F         the live side, judged against the registry
  routine-sync.py diff --id X --live F    a live definition against its file
  routine-sync.py rotation next [-c N]    the projects longest since a sweep
  routine-sync.py rotation mark P ...     record a sweep that actually closed
  routine-sync.py rotation status         the whole rotation, oldest first

INTELLIGENCE_REPO names the intelligence checkout; otherwise it is searched for.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REGISTRY = Path("routines") / "registry.json"
REMOTE = Path(__file__).resolve().parent / "remote-access.py"
ROTATION = Path("routines") / "rotation.json"

# Every checklist a project can owe. A rotation mark carries the ones that
# actually closed, so a partial sweep leaves the rest outstanding instead of
# moving the project to the back of the queue.
CHECKLISTS = ("design", "seo", "perf", "stack", "db")

NOT_A_TASK = re.compile(r"^[A-Z_]+\.md$")

PHASE = re.compile(r"^#\s*Phase\s+([\w.]+)\s*[-—]*\s*(.*)$", re.M)
MARKER = re.compile(r"<!--\s*enforce\s+(run|report)\s*:\s*(.+?)\s*-->")

CRON_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))

# How long a routine may go without firing before the silence is the finding.
# Generous enough that one skipped run is not an alarm, tight enough that a
# routine which has stopped is caught inside its own next cycle. The cadence is
# the fallback: one bucket cannot be both tight enough for a routine firing
# hourly and wide enough for one firing every eight hours, so where the schedule
# says how often, the limit is read from that instead.
STALE_HOURS = {"continuous": 3, "daily": 30, "weekly": 192, "monthly": 792}


def repo_root(start=None):
    """The intelligence checkout, or None.

    The tool is installed beside the other tools, where the registry is not, so
    finding the checkout is the ordinary case. Named outright by
    INTELLIGENCE_REPO, else walked up from here, else looked for one level down
    from the usual roots.
    """
    named = os.environ.get("INTELLIGENCE_REPO")
    if named and (Path(named) / REGISTRY).is_file():
        return Path(named)
    here = Path(start or __file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / REGISTRY).is_file():
            return parent
    roots = [Path.cwd(), Path.home()]
    roots += [Path.home() / name for name in
              ("intelligence", "Projects", "IdeaProjects", "WebstormProjects",
               "Development")]
    for root in roots:
        if (root / REGISTRY).is_file():
            return root
        try:
            for candidate in root.glob("*/" + str(REGISTRY)):
                return candidate.parent.parent
        except OSError:
            pass
    return None


def load_registry(root):
    return json.loads((root / REGISTRY).read_text())["routines"]


def load_shared(root):
    """The programs every routine runs through, which belong to no single entry.

    A routine's own config and prompt are claimed by its entry. The runner, the
    delivery and the queue gate are claimed by nothing, so they read as files
    nothing accounts for while being the three the whole schedule runs through.
    Declaring them here is what lets both sides be checked: that the copy is
    held, and that it is still the copy the machine runs.
    """
    return json.loads((root / REGISTRY).read_text()).get("shared", [])


def valid_cron(expression):
    """Whether a five-field cron expression is one the scheduler would take.

    Only the shapes in use here: numbers, ranges, lists, steps and the wildcard.
    A malformed schedule never fires and reports nothing while never firing.
    """
    fields = expression.split()
    if len(fields) != 5:
        return False
    for field, (low, high) in zip(fields, CRON_RANGES):
        for part in field.split(","):
            step = 1
            if "/" in part:
                part, _, raw = part.partition("/")
                if not raw.isdigit() or int(raw) < 1:
                    return False
                step = int(raw)
            if part in ("*", ""):
                if part == "" and step == 1:
                    return False
                continue
            bounds = part.split("-")
            if len(bounds) > 2 or not all(b.isdigit() for b in bounds):
                return False
            values = [int(b) for b in bounds]
            if any(v < low or v > high for v in values):
                return False
            if len(values) == 2 and values[0] > values[1]:
                return False
    return True


def field_values(field, low, high):
    """Every value a single cron field stands for. Valid fields only."""
    out = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, _, raw = part.partition("/")
            step = int(raw)
        if part in ("*", ""):
            start, end = low, high
        else:
            bounds = part.split("-")
            start, end = int(bounds[0]), int(bounds[-1])
        out.update(range(start, end + 1, step))
    return out


def fire_minutes(schedule):
    """Every (hour, minute) a schedule fires at within a day.

    Two routines collide when their sets intersect, which a comparison of the
    expressions misses: `47 * * * *` and `47 */8 * * *` read as different
    schedules and land on each other three times a day.
    """
    fields = schedule.split()
    return {(hour, minute)
            for hour in field_values(fields[1], 0, 23)
            for minute in field_values(fields[0], 0, 59)}


def period_hours(schedule):
    """How many hours a schedule leaves between fires, or None.

    Only the hour field is read, and only while the day fields are open. A
    schedule pinned to one weekday or one date repeats on a cycle the hour
    field alone reports as daily, and a limit derived from that would call a
    weekly routine stale six days out of seven.
    """
    fields = (schedule or "").split()
    if len(fields) != 5 or fields[2] != "*" or fields[4] not in ("*", "?"):
        return None
    hour = fields[1]
    if hour == "*":
        return 1
    if hour.startswith("*/") and hour[2:].isdigit() and int(hour[2:]) > 0:
        return int(hour[2:])
    if hour.isdigit():
        return 24
    return None


def fired_by(entry):
    """What starts a routine that runs on no schedule."""
    hook = entry.get("webhook") or {}
    events = hook.get("events") or []
    if events:
        return "on %s" % ", ".join(events)
    return entry.get("gate") or "-"


def stale_limit(entry):
    """The hours of silence that make a routine's own schedule the finding.

    The slack is a quarter of the period, so one skipped run reads as a skipped
    run and two read as a routine that has stopped.
    """
    period = period_hours(entry.get("schedule"))
    if period is None:
        return STALE_HOURS.get(entry.get("cadence"), 30)
    return period + max(2, period // 4)


def gates_of(text):
    """Each phase in a task file, with the gates it declares.

    The same parse the stop guard runs, kept here so a routine file answers for
    itself at the point it is written rather than at the end of the first run
    that fires it. A fenced block holds display rather than declaration, so a
    heading quoted as an example is not counted.
    """
    out, fence, kept = [], None, []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if fence is None:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                fence = stripped[:3]
                kept.append("\n")
            else:
                kept.append(line)
        else:
            if stripped.startswith(fence):
                fence = None
            kept.append("\n")
    text = "".join(kept)
    found = list(PHASE.finditer(text))
    for i, match in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        body = text[match.end():end]
        label = ("Phase %s -- %s" % (match.group(1), match.group(2))).strip(" -")
        out.append((label, MARKER.findall(body)))
    return out


def check(root):
    """Everything wrong with the checked-in side, as printable lines."""
    problems = []
    routines = load_registry(root)
    seen = set()
    minutes = {}
    for entry in routines:
        rid = entry.get("id")
        if not rid or rid in seen:
            problems.append("duplicate or missing id: %r" % rid)
            continue
        seen.add(rid)
        if entry.get("cadence") not in ("continuous", "daily", "weekly", "monthly"):
            problems.append("%s: cadence %r is not one of the four"
                            % (rid, entry.get("cadence")))
        if entry.get("host") == "pi":
            problems.extend(check_pi(root, entry, minutes))
        elif entry.get("host") == "mac":
            problems.extend(check_mac(root, entry))
        else:
            problems.append("%s: host %r is not one of pi or mac"
                            % (rid, entry.get("host")))
    shared = load_shared(root)
    problems.extend(check_shared(root, shared))
    problems.extend(check_orphans(root, routines, shared))
    return problems


def check_pi(root, entry, minutes):
    """A Pi routine, which is one of two things that cannot answer for each other.

    A board or a monitor is a unit a timer starts, and what can go wrong is a
    source directory or a unit file that is not there. A scheduled run is a
    prompt a cron line hands to a headless turn, and what can go wrong is a
    missing prompt, a schedule that does not parse, or a minute two of them
    share. An entry says which it is by carrying a source directory.
    """
    if entry.get("source") or entry.get("unit"):
        return check_service(root, entry)
    return check_scheduled(root, entry, minutes)


def check_scheduled(root, entry, minutes):
    """A scheduled run's config, prompt, task file, and what fires it."""
    rid = entry["id"]
    problems = []
    for field in ("config", "prompt"):
        path = entry.get(field)
        if not path or not (root / path).is_file():
            problems.append("%s: %s is missing (%s)" % (rid, field, path))
    schedule = entry.get("schedule") or ""
    webhook = entry.get("webhook")
    # A gate is a cheap poll that starts a turn only when there is work, so it
    # is named rather than scheduled: the run it might start belongs to no
    # minute, and holding it against the ones that do would collide it with
    # every routine that shares the clock it polls on.
    gate = entry.get("gate")
    if not schedule and not webhook and not gate:
        problems.append("%s names neither a schedule nor a gate, so "
                        "nothing fires it" % rid)
    elif schedule and not valid_cron(schedule):
        problems.append("%s: schedule %r does not parse" % (rid, schedule))
    elif schedule:
        # Two runs starting in the same minute is not an error anything
        # reports. It surfaces as one run reading a repository the other is
        # part way through landing.
        clash = next((minutes[slot] for slot in sorted(fire_minutes(schedule))
                      if slot in minutes), None)
        if clash:
            problems.append("%s fires in the same minute as %s (%s)"
                            % (rid, clash, schedule))
        for slot in fire_minutes(schedule):
            minutes.setdefault(slot, rid)
    config = root / entry["config"] if entry.get("config") else None
    cfg = None
    if config and config.is_file():
        try:
            cfg = json.loads(config.read_text())
        except ValueError as error:
            problems.append("%s: config does not parse (%s)" % (rid, error))
    if cfg:
        if (cfg.get("cron_expression") or "") != schedule:
            problems.append("%s: registry says %r, config says %r"
                            % (rid, entry.get("schedule"),
                               cfg.get("cron_expression")))
        declared = cfg.get("webhook")
        if webhook and declared != webhook:
            problems.append("%s: the registry and the config disagree about "
                            "the webhook that fires it" % rid)
        if declared and not webhook:
            problems.append("%s: the config carries a webhook the registry "
                            "does not name" % rid)
        named = cfg.get("prompt_file")
        if named and entry.get("prompt") and not entry["prompt"].endswith(named):
            problems.append("%s: config names prompt %r, registry names %r"
                            % (rid, named, entry["prompt"]))
    task = entry.get("task")
    if task:
        problems.extend(check_task(root, rid, task))
    return problems


def check_task(root, rid, task):
    """A task file's phases, each of which declares its own gates."""
    path = root / task
    if not path.is_file():
        return ["%s: task file is missing (%s)" % (rid, task)]
    phases = gates_of(path.read_text(errors="ignore"))
    if not phases:
        return ["%s: %s declares no phases" % (rid, task)]
    problems = []
    for label, gates in phases:
        if not gates:
            problems.append("%s: %s declares no enforce marker; it cannot be checked"
                            % (rid, label))
            continue
        for _, pattern in gates:
            try:
                re.compile(pattern)
            except re.error:
                problems.append("%s: %s carries `%s`, which is not a pattern"
                                % (rid, label, pattern))
    return problems


def check_service(root, entry):
    """A Pi service's source directory and the units that start it."""
    rid = entry["id"]
    source = entry.get("source")
    if not source or not (root / source).is_dir():
        return ["%s: source directory is missing (%s)" % (rid, source)]
    problems = []
    unit = entry.get("unit")
    if unit:
        if not (root / source / unit).is_file():
            problems.append("%s: %s is missing from %s" % (rid, unit, source))
        service = unit.replace(".timer", ".service")
        if not (root / source / service).is_file():
            problems.append("%s: %s is missing from %s" % (rid, service, source))
    if not (root / source / "config.example.json").is_file():
        problems.append("%s: no config.example.json in %s" % (rid, source))
    return problems


def check_mac(root, entry):
    """A workstation routine's script, its task file and its schedule.

    A routine here is a script launchd fires rather than a definition the API
    holds, so there is no live side to read and nothing to restore a prompt
    from. What can go wrong is narrower: the script is gone, the task file that
    declares its phases is gone, or the schedule in the registry says something
    the script does not fire on. The first two are answered here. The third is
    the script's own `check`, because the plist is the only place that answer
    lives and this machine is the only place the plist exists.
    """
    rid = entry["id"]
    problems = []
    script = entry.get("script")
    if not script or not (root / script).is_file():
        problems.append("%s: script is missing (%s)" % (rid, script))
    schedule = entry.get("schedule") or ""
    if not schedule:
        problems.append("%s carries no schedule, so nothing fires it" % rid)
    elif not valid_cron(schedule):
        problems.append("%s: schedule %r does not parse" % (rid, schedule))
    task = entry.get("task")
    if task:
        problems.extend(check_task(root, rid, task))
    return problems


def check_shared(root, shared):
    """The shared programs, as files held here rather than only on the machine.

    Every scheduled turn on the Pi starts in one of these. They live outside any
    single routine, so nothing claimed them and nothing compared them, and the
    directory they install to could drift for months while the registry stayed
    green. Held, declared and pointed at an install path is what makes the
    machine-side comparison possible at all.
    """
    problems = []
    seen = set()
    for entry in shared:
        path = entry.get("path")
        if not path:
            problems.append("a shared entry carries no path")
            continue
        if path in seen:
            problems.append("%s is declared shared twice" % path)
            continue
        seen.add(path)
        if not (root / path).is_file():
            problems.append("%s is declared shared and is not in the tree" % path)
            continue
        if not entry.get("installed"):
            problems.append("%s names no install path, so nothing can compare it"
                            % path)
        if entry.get("host") not in ("pi", "mac"):
            problems.append("%s: host %r is not one of pi or mac"
                            % (path, entry.get("host")))
    return problems


def digest(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def installed_digests(host, directory):
    """Every file in a machine's install directory, by content.

    Read over the same route the rest of the setup uses, so a machine that
    cannot be reached is reported as unreached rather than as clean.
    """
    done = subprocess.run(
        [sys.executable, str(REMOTE), "run", host, "--",
         "sha256sum %s/* 2>/dev/null" % directory],
        capture_output=True, text=True, timeout=180)
    out = {}
    for line in done.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 64:
            out[parts[1]] = parts[0]
    return out, done.returncode


def mirrored(root, shared):
    """Whether each machine still runs the copy this repository holds.

    `check` answers for this side alone, and a file that is present and declared
    passes it however far the machine has drifted. The two ways a backup stops
    being one are invisible from here: a script edited in place where it runs,
    and a script added there that was never committed. Both leave a repository
    that looks complete and rebuilds something other than what was running.
    """
    problems = []
    directories = {}
    for entry in shared:
        host = entry.get("host")
        installed = entry.get("installed")
        if not host or not installed:
            continue
        directories.setdefault(host, set()).add(str(Path(installed).parent))

    for host, dirs in sorted(directories.items()):
        live = {}
        for directory in sorted(dirs):
            found, code = installed_digests(host, directory)
            if code != 0 and not found:
                problems.append("%s could not be reached, so %s is unchecked"
                                % (host, directory))
                continue
            live.update(found)
        declared = {}
        for entry in shared:
            if entry.get("host") == host and entry.get("installed"):
                declared[entry["installed"]] = entry["path"]
        for installed, path in sorted(declared.items()):
            if installed not in live:
                problems.append("%s is held here and is not installed on the %s"
                                % (path, host))
            elif live[installed] != digest((root / path).read_text()):
                problems.append("%s on the %s is not the copy held here"
                                % (installed, host))
        for installed in sorted(live):
            if installed not in declared:
                problems.append("the %s runs %s, which no shared entry declares "
                                "and no copy here would rebuild" % (host, installed))
    return problems


def check_orphans(root, routines, shared):
    """Files under the routine directories that no registry entry claims.

    A routine present in the tree and absent from the registry is one nothing
    checks and nothing rebuilds, which is the gap the registry closes.
    """
    claimed = set()
    for entry in routines:
        for field in ("config", "prompt", "task"):
            if entry.get(field):
                claimed.add(entry[field])
    for entry in shared:
        if entry.get("path"):
            claimed.add(entry["path"])
    problems = []
    for path in sorted((root / "routines").rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        if path.name in ("registry.json", "rotation.json", "README.md"):
            continue
        if rel not in claimed:
            problems.append("%s is in the tree but in no registry entry" % rel)
    for path in sorted((root / "routine").glob("*.md")):
        rel = str(path.relative_to(root))
        # A task file is lower case. The operating agreement travelling beside
        # them, and the alias onto it, are not, and neither declares phases.
        if NOT_A_TASK.match(path.name):
            continue
        if rel not in claimed:
            problems.append("%s is a task file no registry entry names" % rel)
    return problems


# The fields a live definition is compared on. The API returns more than it
# accepts back, so a diff over everything reports movement in fields nothing
# here could have caused. The webhook that fires a routine is absent from both
# ends of that comparison: the API holds it as a separate object and returns
# nothing about it here, so `check` answers for it against the config instead.
COMPARED = ("name", "cron_expression", "enabled", "mcp_connections", "job_config")


def diff(root, rid, live_path):
    """What a live routine holds that its checked-in copy does not, and back."""
    entry = next((r for r in load_registry(root) if r.get("id") == rid), None)
    if entry is None:
        return ["no routine %r in the registry" % rid]
    if not entry.get("config"):
        return ["%s is a %s service; it has no live definition to diff"
                % (rid, entry.get("host"))]
    raw = json.loads(Path(live_path).read_text())
    mine = strip_prompt(json.loads((root / entry["config"]).read_text()))
    live = strip_prompt(raw)
    out = []
    for field in COMPARED:
        ours, theirs = mine.get(field), live.get(field)
        if field == "cron_expression":
            # A routine fired only by a webhook carries no schedule, which the
            # file spells as an absent key and the API as an empty string.
            ours, theirs = ours or "", theirs or ""
        if ours != theirs:
            out.append("%s: %s differs" % (rid, field))
            out.extend(describe(field, ours, theirs))
    prompt = (root / entry["prompt"]).read_text() if entry.get("prompt") else ""
    live_prompt = prompt_of(raw)
    if live_prompt and prompt.strip() != live_prompt.strip():
        out.append("%s: the live prompt differs from %s" % (rid, entry["prompt"]))
    return out


def prompt_of(cfg):
    try:
        return cfg["job_config"]["ccr"]["events"][0]["data"]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""


def strip_prompt(cfg):
    # The prompt is held beside the config rather than inside it, so the file
    # carries a placeholder where a live definition carries the text.
    cfg = json.loads(json.dumps(cfg))
    try:
        cfg["job_config"]["ccr"]["events"][0]["data"]["message"]["content"] = ""
        cfg["job_config"]["ccr"]["events"][0]["data"]["uuid"] = ""
    except (KeyError, IndexError, TypeError):
        pass
    return cfg


def describe(field, ours, theirs):
    """The difference as something actionable rather than as a JSON dump."""
    if field == "mcp_connections":
        mine = {c.get("name") for c in ours or []}
        live = {c.get("name") for c in theirs or []}
        return ["    live has: %s" % ", ".join(sorted(live - mine) or ["-"]),
                "    file has: %s" % ", ".join(sorted(mine - live) or ["-"])]
    if field == "job_config":
        return describe_sources(ours, theirs)
    return ["    live: %r" % (theirs,), "    file: %r" % (ours,)]


def sources_of(cfg):
    try:
        return {s["git_repository"]["url"]
                for s in cfg["ccr"]["session_context"]["sources"]}
    except (KeyError, TypeError):
        return set()


def describe_sources(ours, theirs):
    mine, live = sources_of(ours or {}), sources_of(theirs or {})
    out = []
    if live - mine:
        out.append("    repositories only live: %s" % ", ".join(sorted(live - mine)))
    if mine - live:
        out.append("    repositories only in the file: %s"
                   % ", ".join(sorted(mine - live)))
    if not out:
        out.append("    the session config differs outside its repository list")
    return out


def live_routines(payload):
    """The trigger objects out of whatever shape the API answer was saved in."""
    if isinstance(payload, dict):
        payload = payload.get("data") or payload.get("triggers") or (
            [payload["trigger"]] if "trigger" in payload else [])
    return [r for r in payload if isinstance(r, dict) and r.get("id")]


def prompt_of_live(trigger):
    for source in (trigger.get("derived_state") or {}, ):
        if source.get("prompt"):
            return source["prompt"]
    return prompt_of(trigger.get("job_config") or {"job_config": {}}) or ""


def sources_of_live(trigger):
    return sources_of((trigger.get("job_config") or {}))


def hours_since(stamp, now):
    """Hours between an API timestamp and now, or None if it cannot be read."""
    if not stamp:
        return None
    text = stamp.strip().replace("Z", "+00:00")
    # The API answers with nanosecond precision, which fromisoformat refuses.
    trimmed = re.match(r"^(.*?\.\d{1,6})\d*(.*)$", text)
    if trimmed:
        text = trimmed.group(1) + trimmed.group(2)
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (now - when).total_seconds() / 3600.0


def health(root, payload, now=None):
    """Everything wrong with the routines as the API actually holds them.

    Four failures have each happened here and none of them announces itself: a
    routine whose prompt was emptied by a partial update, one carrying no
    repository so every push is refused, one disabled or never firing, and one
    running live with no copy in this repository to rebuild it from.
    """
    now = now or datetime.now(timezone.utc)
    registry = load_registry(root)
    by_trigger = {r["trigger_id"]: r for r in registry if r.get("trigger_id")}
    by_name = {r.get("name"): r for r in registry}
    problems = []
    seen = set()
    one_offs = 0

    for trigger in live_routines(payload):
        tid = trigger["id"]
        name = trigger.get("name") or tid
        entry = by_trigger.get(tid) or by_name.get(name)
        label = "%s (%s)" % (name, tid)
        # A trigger with no schedule and no registry entry is a one-off webhook
        # follow-up, spent once and left behind. Judging those as routines
        # buries the routines in them. Being disabled is what makes one spent:
        # a routine fired only by a webhook carries no schedule either, and
        # passing over that one leaves the error queue unwatched.
        if not entry and not trigger.get("cron_expression") \
                and not trigger.get("enabled"):
            one_offs += 1
            continue
        if entry:
            seen.add(entry["id"])
        else:
            problems.append("%s runs live and no registry entry names it, so "
                            "nothing here could rebuild it" % label)

        if not trigger.get("enabled"):
            problems.append("%s is disabled" % label)
        if not prompt_of_live(trigger).strip():
            problems.append("%s carries an empty prompt; it fires and does "
                            "nothing" % label)
        if not sources_of_live(trigger):
            problems.append("%s carries no repository, so every push it makes "
                            "is refused" % label)

        last = (trigger.get("last_run") or {}).get("status", "")
        if last and "SUCCEED" not in last.upper():
            problems.append("%s last run ended %s" % (label, last))

        # A routine fired by a webhook is judged on nothing here: a night
        # with no ticket in it is silence that means the sites were up. Only a
        # schedule carries an interval to be late against.
        schedule = trigger.get("cron_expression") or ""
        age = hours_since(trigger.get("last_fired_at"), now)
        limit = stale_limit({"schedule": schedule,
                             "cadence": (entry or {}).get("cadence", "daily")})
        if schedule:
            if age is None:
                problems.append("%s has never fired" % label)
            elif age > limit:
                problems.append("%s last fired %.0f hours ago, past the %d its "
                                "schedule allows" % (label, age, limit))
            if not trigger.get("next_run_at"):
                problems.append("%s has no next run scheduled" % label)

    for entry in registry:
        # Only an entry naming a live trigger is answerable here. A service the
        # timers start, and a routine a gate starts, have no definition on this
        # side to be missing from.
        if not entry.get("trigger_id") or entry["id"] in seen:
            continue
        problems.append("%s is recorded as %s and the API returned nothing "
                        "for it" % (entry["id"], entry["trigger_id"]))
    if one_offs:
        problems.append("(%d spent one-off trigger(s) ignored)" % one_offs)
    return problems


def projects(root):
    """Every project the routines are pointed at, from the daily pass's sources.

    Read from the routine config rather than from a second list, since a list
    kept in step with another one by hand eventually is not.
    """
    entry = next((r for r in load_registry(root) if r.get("id") == "maintenance"), None)
    if not entry:
        return []
    cfg = json.loads((root / entry["config"]).read_text())
    urls = sources_of(cfg.get("job_config") or {})
    return sorted(url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
                  for url in urls)


def load_rotation(root):
    path = root / ROTATION
    if path.is_file():
        return json.loads(path.read_text())
    return {"swept": {}}


def save_rotation(root, state):
    (root / ROTATION).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def rotation_order(root):
    """Projects oldest-swept first, with never-swept ones ahead of all of them."""
    state = load_rotation(root)
    swept = state.get("swept", {})
    out = []
    for name in projects(root):
        record = swept.get(name) or {}
        out.append((record.get("at") or "", name, record))
    out.sort(key=lambda row: (row[0], row[1]))
    return out


def rotation_next(root, count):
    return [name for _, name, _ in rotation_order(root)][:count]


def rotation_mark(root, project, checklists, today=None):
    known = projects(root)
    if project not in known:
        return "no project %r among the routines' repositories" % project
    unknown = [c for c in checklists if c not in CHECKLISTS]
    if unknown:
        return "not a checklist: %s" % ", ".join(unknown)
    state = load_rotation(root)
    state.setdefault("swept", {})[project] = {
        "at": today or date.today().isoformat(),
        "checklists": sorted(set(checklists)),
    }
    save_rotation(root, state)
    return None


def rotation(root, args):
    verb = args.rest[0] if args.rest else "status"
    if verb == "next":
        for name in rotation_next(root, args.count):
            print(name)
        return 0
    if verb == "mark":
        if len(args.rest) < 2:
            print("mark needs a project", file=sys.stderr)
            return 2
        checklists = [c.strip() for c in args.checklists.split(",") if c.strip()]
        if not checklists:
            print("mark needs --checklists naming what actually closed",
                  file=sys.stderr)
            return 2
        problem = rotation_mark(root, args.rest[1], checklists, args.today)
        if problem:
            print(problem, file=sys.stderr)
            return 1
        print("%s marked: %s" % (args.rest[1], ", ".join(sorted(set(checklists)))))
        return 0
    if verb == "status":
        for at, name, record in rotation_order(root):
            print("%-24s %-12s %s" % (name, at or "never",
                                      ", ".join(record.get("checklists", []))))
        return 0
    print("rotation takes next, mark or status", file=sys.stderr)
    return 2


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("verb", nargs="?", default="")
    parser.add_argument("rest", nargs="*")
    parser.add_argument("--id")
    parser.add_argument("--live")
    parser.add_argument("--file")
    parser.add_argument("-c", "--count", type=int, default=3)
    parser.add_argument("--checklists", default="")
    parser.add_argument("--today")
    args = parser.parse_args()

    root = repo_root()
    if root is None:
        print("no intelligence checkout found; set INTELLIGENCE_REPO",
              file=sys.stderr)
        return 2

    if args.verb == "list":
        for entry in load_registry(root):
            print("%-10s %-6s %-16s %-18s %s"
                  % (entry.get("cadence"), entry.get("host"), entry.get("id"),
                     entry.get("schedule") or fired_by(entry),
                     entry.get("does", "")[:70]))
        return 0
    if args.verb == "check":
        problems = check(root)
        for line in problems:
            print(line, file=sys.stderr)
        if problems:
            print("\n%d problem(s). A routine that cannot be rebuilt from these "
                  "files is one deletion away from gone." % len(problems),
                  file=sys.stderr)
            return 1
        print("%d routines, all accounted for" % len(load_registry(root)))
        return 0
    if args.verb == "mirrored":
        problems = mirrored(root, load_shared(root))
        for line in problems:
            print(line, file=sys.stderr)
        if problems:
            print("\n%d problem(s). A copy that no longer matches what runs "
                  "is a backup in name only." % len(problems), file=sys.stderr)
            return 1
        print("every shared program matches the machine that runs it")
        return 0
    if args.verb == "health":
        if not args.file:
            print("health needs --file naming the saved API answer", file=sys.stderr)
            return 2
        try:
            payload = json.loads(Path(args.file).read_text())
        except (OSError, ValueError) as error:
            print("could not read %s: %s" % (args.file, error), file=sys.stderr)
            return 2
        problems = health(root, payload)
        for line in problems:
            print(line, file=sys.stderr)
        if problems:
            print("\n%d routine(s) need attention. A routine that fires and "
                  "does nothing reports exactly what a healthy one does: "
                  "silence." % len(problems), file=sys.stderr)
            return 1
        print("every routine answers for itself")
        return 0

    if args.verb == "diff":
        if not args.id or not args.live:
            print("diff needs --id and --live", file=sys.stderr)
            return 2
        lines = diff(root, args.id, args.live)
        for line in lines:
            print(line)
        return 1 if lines else 0
    if args.verb == "rotation":
        return rotation(root, args)

    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
