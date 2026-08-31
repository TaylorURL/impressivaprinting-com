#!/usr/bin/env python3
"""Cases the heartbeat has to get right.

The whole point is that a dead collector and a quiet week look identical from
the outside, so the one thing this cannot do is pass on a feed it could not
read. Unreachable, unparseable, undated and stale all have to fail, and only a
fresh feed passes.

The route a read takes is the second thing held here. A transport failure falls
back to a read taken on the Pi, which recovers reachability and nothing else: a
stale feed stays stale over that route, an HTTP error is the feed's own answer
and never reaches for a second route, and a feed neither route can read is a
machine that has stopped.

  pi-heartbeat-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "pi-heartbeat.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stamp(minutes_ago):
    when = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    mod = load()
    hops = []

    def feeding(body):
        def read(url, timeout=20):
            if isinstance(body, Exception):
                raise body
            return body
        mod.read_feed = read

    def hopping(body):
        def read(url, timeout=None):
            hops.append(url)
            if isinstance(body, Exception):
                raise body
            return body
        mod.read_feed_via_pi = read

    # Both routes are stood in for throughout, so no case can be answered by a
    # machine that happens to be up wherever this runs.
    hopping(OSError("the Pi did not answer"))

    feeding({"updated_at": stamp(1), "sites": [{"name": "a"}, {"name": "b"}]})
    code, message = mod.check("https://example.invalid/status.json", 15)
    check("a fresh feed passes", code, 0)
    check("it says how many sites", "2 site(s)" in message, True)

    feeding({"updated_at": stamp(90), "sites": []})
    code, message = mod.check("https://example.invalid/status.json", 15)
    check("a stale feed fails", code, 1)
    check("it says the queue proves nothing", "ticket queue" in message, True)

    feeding({"sites": []})
    check("an undated feed fails",
          mod.check("https://example.invalid/status.json", 15)[0], 1)

    feeding({"updated_at": "the other day"})
    check("an unreadable date fails",
          mod.check("https://example.invalid/status.json", 15)[0], 1)

    feeding(URLError("connection refused"))
    code, message = mod.check("https://example.invalid/status.json", 15)
    check("an unreachable feed fails", code, 1)
    check("it names the reason", "connection refused" in message, True)

    # The window covers a slow rebuild and stops well short of an outage.
    feeding({"updated_at": stamp(14), "sites": []})
    check("inside the window passes",
          mod.check("https://example.invalid/status.json", 15)[0], 0)
    check("the default window is a quarter hour", mod.MAX_AGE_MINUTES, 15)

    feeding(URLError("Name or service not known"))
    hopping({"updated_at": stamp(2), "sites": [{"name": "a"}]})
    code, message = mod.check("https://example.invalid/status.json", 15)
    check("a fresh feed read on the Pi passes", code, 0)
    check("it names the route it took", "through the Pi" in message, True)

    hopping({"updated_at": stamp(90), "sites": []})
    code, message = mod.check("https://example.invalid/status.json", 15)
    check("a stale feed read on the Pi still fails", code, 1)
    check("the second route recovers reach, never freshness",
          "ticket queue" in message, True)

    hops.clear()
    feeding(HTTPError("https://example.invalid/status.json", 500, "server", {}, None))
    hopping({"updated_at": stamp(1), "sites": []})
    code, message = mod.check("https://example.invalid/status.json", 15)
    check("an answering feed's HTTP error fails", code, 1)
    check("and takes no second route", hops, [])

    feeding(URLError("Name or service not known"))
    hopping(OSError("no route to the Pi"))
    code, message = mod.check("https://example.invalid/status.json", 15)
    check("neither route reaching it fails", code, 1)
    check("it names the direct attempt",
          "Name or service not known" in message, True)
    check("it names the attempt through the Pi",
          "no route to the Pi" in message, True)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
