#!/usr/bin/env python3
"""Cases the Chrome guard has to get right.

Every Chrome tool is refused, and so is a shell command that opens the real
browser. A headless run is refused on the same terms, since it is the same
binary under another flag, and so is a script that reaches the binary itself
rather than through a command the shell patterns can see. The environment
carries no key that lifts any of it.

  chrome-guard-cases.py        run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "chrome-guard.py")

FAILURES = []


def run(tool, command="", env=None):
    ev = json.dumps({"tool_name": tool, "tool_input": {"command": command}})
    p = subprocess.run([sys.executable, str(TARGET), "guard"],
                       input=ev, capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    return p.returncode


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got}, want {want}")


def main():
    for tool in ("mcp__claude-in-chrome__navigate",
                 "mcp__claude-in-chrome__computer",
                 "mcp__claude-in-chrome__tabs_context_mcp",
                 "mcp__claude-in-chrome__read_page"):
        check(f"tool {tool.split('__')[-1]}", run(tool), 2)

    # The in-app browser is the surface that stays open.
    for tool in ("mcp__Claude_Browser__navigate",
                 "mcp__Claude_Browser__computer",
                 "Read", "Write", "Bash"):
        check(f"allowed {tool.split('__')[-1]}", run(tool), 0)

    check("bash: open -a Google Chrome",
          run("Bash", 'open -a "Google Chrome" https://example.com'), 2)
    check("bash: Chrome.app path",
          run("Bash", '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome'), 2)

    # A flag is not a different binary.
    check("bash: headless capture",
          run("Bash", '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome '
                      '--headless --remote-debugging-port=9222'), 2)
    check("bash: a script that drives the binary itself",
          run("Bash", 'node ~/.intelligence/checklists/perf/scripts/capture.js '
                      '--url http://localhost:4173 --built'), 2)

    # The binary under its other names and on its other platforms.
    for cmd in ("google-chrome --headless https://example.com",
                "chromium-browser https://example.com",
                "chromium https://example.com",
                "chrome-headless-shell --dump-dom https://example.com",
                '"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"',
                "/opt/pw-browsers/chromium --version"):
        check(f"bash: {cmd.split()[0]}", run("Bash", cmd), 2)

    # A wrapper is the binary one call further down. The basename survives the
    # rename of the path around it.
    for cmd in ("bash ~/bin/perf-wrap.sh && node capture.js --url https://example.com",
                "python3 ./tools/lighthouse.py --url https://example.com",
                "sh -c 'cd ~/.intelligence/checklists/perf/scripts/ && ./run'"):
        check(f"wrapper: {cmd[:28]}", run("Bash", cmd), 2)

    # A script in that directory that never reaches the binary is not the binary.
    # psi.py is an HTTPS call to Google's PageSpeed API and the engine runs on
    # Google's hardware; parity-probe.js is pasted into an already-open page; and
    # bundle-probe.py reads a build directory. Refusing all three with the two that
    # drive the binary stalled every performance run, because psi.py is the only way
    # to file the baseline measurement the run's own edit guard demands.
    for cmd in ("python3 ~/.intelligence/checklists/perf/scripts/psi.py measure --url https://example.com",
                "python3 vendor/psi.py measure --url https://example.com",
                "python3 ~/.intelligence/checklists/perf/scripts/bundle-probe.py --dir dist",
                "cat ~/.intelligence/checklists/perf/scripts/parity-probe.js"):
        check(f"reaches no binary: {cmd[:30]}", run("Bash", cmd), 0)

    # The clause those three sit under still bites anything it cannot read a name
    # for, which is what stops a wrapper hiding a driver behind a name of its own.
    check("opaque runner in that directory",
          run("Bash", "sh -c 'cd ~/.intelligence/checklists/perf/scripts/ && ./run'"), 2)

    # The drivers that start it, and the variables that point at it.
    for cmd in ("npx playwright test",
                "node -e \"require('puppeteer').launch()\"",
                "npx lighthouse https://example.com",
                "PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers npm test",
                "PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium node run.js",
                "CHROME_PATH=/usr/bin/chromium npm run capture"):
        check(f"driver: {cmd[:26]}", run("Bash", cmd), 2)

    # No environment variable lifts a refusal.
    check("no key lifts a tool call",
          run("mcp__claude-in-chrome__navigate", env={"INTELLIGENCE_ALLOW_CHROME": "1"}), 2)
    check("no key lifts a shell launch",
          run("Bash", "google-chrome --headless https://example.com",
              env={"INTELLIGENCE_ALLOW_CHROME": "1"}), 2)
    check("no key lifts a checklist probe",
          run("Bash", "node capture.js --url http://localhost:4173 --built",
              env={"INTELLIGENCE_ALLOW_CHROME": "1"}), 2)

    check("bash: ordinary command", run("Bash", "git status"), 0)
    check("bash: mentions chrome in prose",
          run("Bash", 'echo "the chrome trim on the dashboard"'), 0)
    check("bash: an unrelated capture",
          run("Bash", "git commit -m 'capture the totals'"), 0)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
