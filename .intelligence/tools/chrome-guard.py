#!/usr/bin/env python3
"""Refuses the Chrome browser surface.

Browsing work goes through the in-app browser. The Chrome tools drive the real
signed-in profile, so a call that looks like a page read is a call made as the
account, against whatever that profile is logged into.

There is no exemption and no override. A headless run is the same binary under
another flag, a wrapper is the same binary one call further down, and a
checklist probe that reaches it is the same binary with a task attached.

  guard   PreToolUse. Deny a Chrome tool call before it runs.
"""
import json
import re
import sys

CHROME_TOOL = re.compile(r"^mcp__claude-in-chrome__", re.I)

# The binary, however it is spelled and wherever it is installed. A shell
# escapes the space in the application name, so the separator is a space that
# may carry a backslash rather than a space alone.
CHROME_SHELL = re.compile(
    r"open\s+(-a\s+)?[\"']?(Google\\?\s+Chrome|Chromium)"
    r"|/Applications/(Google\\?\s+Chrome|Chromium)\.app"
    r"|\bchrome-cli\b"
    r"|\bopen\b.*\bchrome://"
    r"|\bgoogle-chrome(-stable|-beta|-unstable)?\b"
    r"|\bchromium(-browser)?\b"
    r"|\bchrome-headless-shell\b"
    r"|\bchrome\.exe\b",
    re.I,
)

# The drivers that start the binary, and the flags that mark a run as one.
HEADLESS = re.compile(
    r"--headless|--remote-debugging-port|--user-data-dir"
    r"|puppeteer|playwright|selenium|webdriver"
    r"|chrome-launcher|chrome-remote-interface|lighthouse"
    r"|PLAYWRIGHT_BROWSERS_PATH|PUPPETEER_EXECUTABLE_PATH|CHROME_PATH",
    re.I,
)

# The scripts that resolve a local browser binary and run it. capture.js drives
# one directly and lighthouse.py finds one and runs the engine against it, so
# both are the binary one call further down. Matched on the basename, which is
# what a wrapper cannot rename away without becoming a different script.
#
# What does not belong here is anything that never reaches the binary. psi.py
# is an HTTPS call to Google's PageSpeed API, where the engine runs on Google's
# hardware; parity-probe.js is pasted into an already-open page and drives
# nothing; and bundle-probe.py reads a build directory. Refusing the whole
# scripts directory took all three down with the two that matter, and psi.py is
# the only way to file the baseline measurement a performance run's edit guard
# demands, so blocking it stalled every performance run rather than keeping a
# browser shut.
BROWSER_SCRIPT = re.compile(
    r"\bcapture\.js\b"
    r"|\blighthouse\.py\b",
    re.I,
)


# Anything executed out of that directory whose name the guard cannot read. The
# two drivers are caught by name wherever they are invoked from; this catches the
# wrapper that hides one behind a name of its own, which is what the directory
# clause was there for. The scripts that reach no binary are named as exempt
# rather than freed by dropping the clause, so the evasion stays shut.
PERF_SCRIPTS_DIR = re.compile(r"checklists/perf/scripts/", re.I)
REACHES_NO_BINARY = re.compile(
    r"\bpsi\.py\b"
    r"|\bbundle-probe\.py\b"
    r"|\bparity-probe\.js\b",
    re.I,
)


def deny(what):
    sys.stderr.write(
        f"BLOCKED: {what}\n\n"
        "Chrome is not used here, on any path, under any flag, for any task.\n"
        "The in-app browser tools (mcp__Claude_Browser__*) cover browsing and\n"
        "carry no signed-in profile. There is no exemption and no override:\n"
        "a gate that needs the real browser is answered by the in-app browser\n"
        "or reported unanswered.\n"
    )
    sys.exit(2)


def install():
    """Put the hook back into settings.json.

    The config sync settles a conflict by edit time over whole files, so a
    machine holding an older settings.json with a later clock drops this wiring
    and reports the run as a pull. Rewiring on every session start is what makes
    that cost one session rather than standing.
    """
    from pathlib import Path

    settings = Path.home() / ".intelligence" / "settings.json"
    try:
        data = json.loads(settings.read_text())
    except Exception:
        return
    tool = "~/.intelligence/tools/chrome-guard.py"
    wanted = [("PreToolUse", "mcp__claude-in-chrome__.*", f"{tool} guard"),
              ("PreToolUse", "Bash", f"{tool} guard"),
              ("SessionStart", "*", f"{tool} install")]
    changed = False
    for event, matcher, command in wanted:
        entries = data.setdefault("hooks", {}).setdefault(event, [])
        if any(command in h.get("command", "") and m.get("matcher") == matcher
               for m in entries for h in m.get("hooks", [])):
            continue
        # A guard-hub entry hosts this event's guards; the wiring lives there.
        if event != "SessionStart" and any(
                "guard-hub.py" in h.get("command", "")
                for m in entries for h in m.get("hooks", [])):
            continue
        entries.append({"matcher": matcher,
                        "hooks": [{"type": "command", "command": command}]})
        changed = True
        print(f"wired {event}[{matcher}]")
    if changed:
        settings.write_text(json.dumps(data, indent=2) + "\n")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        install()
        sys.exit(0)
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = ev.get("tool_name", "")
    if CHROME_TOOL.match(tool):
        deny(f"{tool} drives the signed-in Chrome profile.")
    if tool == "Bash":
        cmd = (ev.get("tool_input") or {}).get("command", "")
        if BROWSER_SCRIPT.search(cmd):
            deny("this script drives Chrome to capture a page.")
        if PERF_SCRIPTS_DIR.search(cmd) and not REACHES_NO_BINARY.search(cmd):
            deny("this runs something out of the performance scripts directory "
                 "under a name the guard cannot read.")
        if CHROME_SHELL.search(cmd) or HEADLESS.search(cmd):
            deny("this command opens Chrome.")
    sys.exit(0)


if __name__ == "__main__":
    main()
