#!/usr/bin/env python3
"""Whether the Pi is still answering, judged by the feed rather than by silence.

The error reporter, the uptime monitor and all three boards run on one machine.
When that machine stops, every one of them stops with it: no alert fires, no
board updates, and the ticket queue stops filling. A run that reads an empty
queue and finishes clean is reading a dead collector, and the two look identical
from the outside.

The public feed carries the timestamp of its last rebuild, so the difference is
one read: a feed that answers and is recent means the pipeline is alive, and a
feed that is stale by more than a board's own interval means it is not,
whatever the queue says.

The feed's host is a Tailscale MagicDNS name, which resolves on the tailnet and
nowhere else. A cloud container is not on the tailnet; it reaches the Pi over
the tunnel to the public Funnel that remote-access.py drives. So a read that
fails at the transport is taken again on the Pi itself over that route, and only
a feed neither route reaches counts as a machine that has stopped. A server
answering with an HTTP error has answered, so that stays a failure with no
second route to try, and the age of the feed decides the verdict the same way
whichever route carried the read.

  pi-heartbeat.py check [--url U] [--max-age-minutes N]

Exits 0 when the feed is fresh, 1 when it is stale or unreachable.
INTELLIGENCE_STATUS_FEED overrides the URL.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FEED = "https://sunday.tail1f78d7.ts.net/status.json"

# A read taken on the Pi crosses the Funnel tunnel twice, so it is slower than
# the direct one by the width of a round trip rather than of a fetch.
HOP_TIMEOUT = 120

# The boards rebuild every two minutes. Fifteen leaves room for a slow rebuild
# and a retried post without leaving room for an outage.
MAX_AGE_MINUTES = 15


def read_feed(url, timeout=20):
    request = Request(url, headers={"User-Agent": "intelligence-pi-heartbeat/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def remote_access():
    """The remote-access tool, from beside this file or from the installed set.

    A hook runs this script from whatever directory the session is standing in,
    so the sibling copy is found by path rather than by the working directory.
    """
    here = Path(__file__).resolve().parent / "remote-access.py"
    if here.is_file():
        return here
    return Path.home() / ".intelligence" / "tools" / "remote-access.py"


def read_feed_via_pi(url, timeout=HOP_TIMEOUT):
    """The same feed, fetched on the Pi and handed back over the tunnel.

    remote-access.py picks the route, which is a direct connection from the
    tailnet and the Funnel tunnel from anywhere else, so the fetch runs on the
    machine whose own name the feed is served under.
    """
    tool = remote_access()
    if not tool.is_file():
        raise OSError("remote-access.py is not on this machine")
    command = "curl -fsS --max-time 20 %s" % shlex.quote(url)
    done = subprocess.run(
        [sys.executable, str(tool), "run", "pi", "--", command],
        capture_output=True, text=True, timeout=timeout,
    )
    if done.returncode != 0:
        raise OSError(done.stderr.strip() or "the Pi did not answer")
    return json.loads(done.stdout)


def age_minutes(stamp):
    when = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - when).total_seconds() / 60.0


def check(url, limit):
    route = "directly"
    try:
        feed = read_feed(url)
    except HTTPError as error:
        # The server answered, so the machine is up and the answer is its own.
        return 1, "the feed answered HTTP %d" % error.code
    except ValueError as error:
        return 1, "the feed is unreadable: %s" % error
    except (URLError, OSError) as error:
        direct = getattr(error, "reason", error)
        try:
            feed = read_feed_via_pi(url)
        except (URLError, OSError, ValueError, subprocess.SubprocessError) as hop:
            return 1, ("the feed is unreachable: %s directly, and %s through "
                       "the Pi. Both routes failed, so this is the machine "
                       "rather than the route." % (direct, hop))
        route = "through the Pi"
    stamp = feed.get("updated_at")
    if not stamp:
        return 1, "the feed carries no updated_at, so its age cannot be read"
    try:
        age = age_minutes(stamp)
    except ValueError:
        return 1, "the feed's updated_at is unreadable: %r" % stamp
    sites = len(feed.get("sites") or [])
    if age > limit:
        return 1, ("the feed, read %s, was last rebuilt %.0f minutes ago, past "
                   "the %d minute mark. The collector, the monitor and the "
                   "boards all run on that machine, so an empty ticket queue "
                   "right now says nothing about the sites." % (route, age, limit))
    return 0, ("the feed rebuilt %.0f minute(s) ago over %d site(s), read %s"
               % (age, sites, route))


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("verb", nargs="?", default="")
    parser.add_argument("--url", default=os.environ.get("INTELLIGENCE_STATUS_FEED") or FEED)
    parser.add_argument("--max-age-minutes", type=int, default=MAX_AGE_MINUTES)
    args = parser.parse_args()
    if args.verb != "check":
        print(__doc__.strip(), file=sys.stderr)
        return 2
    code, message = check(args.url, args.max_age_minutes)
    print(message, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
