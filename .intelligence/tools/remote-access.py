#!/usr/bin/env python3
"""Reaches the workstation machines from wherever the run is happening.

A cloud container is not cut off from them. It carries a key for the Pi and
reaches it over a WebSocket tunnel to the public Funnel, which needs no tailnet
membership, and the Pi carries keys for the Mac, the Windows desktop and the
VPS. So every machine is one hop further on, and a run that assumes otherwise
hands work back to a person who then does it by hand.

  announce      SessionStart. Name the machines reachable from here.
  hosts         The machines, the route to each, and what each answered.
  run <host> -- <command>       Run a command there, over whichever route works.
  read <host> <path>            Read a remote file to stdout over that route.
  check [host]  Probe; exit non-zero when a machine is out of reach.
  guard-stop    Stop hook. Refuse a reply that hands work back for a machine
                that is in fact reachable from here.
  install       Wire the hooks into settings.json.

The route is probed rather than assumed, so a machine that is genuinely asleep
reads as unreachable and saying so stays allowed. That is also what keeps the
guard narrow: it fires only where the reply gave up on a machine that answered.

INTELLIGENCE_REMOTE_OFF=1 disables the guard.
"""
import importlib.util
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path

INTELLIGENCE = Path.home() / ".intelligence"
CACHE = INTELLIGENCE / "state" / "remote-access.json"
CACHE_TTL = 600

# Alias to the ssh config host it answers to. The aliases are what a person says
# ("the mac", "the pi"); the second name is what ssh resolves.
HOSTS = {
    "mac": ("trenton-mac", "the workstation: checkouts, worktrees, ~/.intelligence"),
    "pi": ("sunday", "Raspberry Pi: error reporter, uptime monitor, Discord boards"),
    "windows": ("trentons-desktop", "Windows desktop: DomeBreak on Windows"),
    "vps": ("domebreak-vps", "Vultr VPS: DomeBreak match server, Caddy"),
}

# The one machine that reaches all the others, and so the route of last resort
# from anywhere holding a key for it.
JUMP = "pi"

CONNECT_TIMEOUT = 15
PROBE_TIMEOUT = 45

# Ways a reply gives up on a machine or hands the work to the person reading it.
SURRENDER = re.compile(
    # The passive carries the same surrender as the active, and a couple of
    # words routinely sit between the two halves: "cannot be reached",
    # "can't currently get onto".
    r"(?:can'?t|cannot|can not|unable to|no way to|not able to)\s+"
    r"(?:\w+\s+){0,2}?(?:reach(?:ed)?|access(?:ed)?|ssh|connect(?:ed)?|"
    r"get (?:to|onto|into)|run|see|read)"
    r"|(?:do(?:n'?t| not)|does(?:n'?t| not)) have (?:direct |any )?access"
    r"|(?:no|without) (?:direct )?access to"
    r"|(?:is|are|'s|isn'?t|aren'?t)\s+not\s+"
    r"(?:reachable|accessible|available|answering|responding)"
    r"|(?:run|do|check|try) (?:it|this|that|them|the command)?\s*"
    r"(?:there|yourself|on your (?:own )?\w+|from your \w+)"
    r"|you'?(?:ll|d) (?:need|have) to"
    r"|(?:from|on|at) your end"
    r"|not (?:reachable|available|accessible|possible) from (?:the |a )?cloud"
    r"|only (?:works|runs|available) (?:locally|on the \w+)"
    r"|local(?:ly)?[ -]only"
    r"|(?:this|the) (?:cloud )?(?:session|container|environment) (?:can'?t|cannot|has no)",
    re.I,
)

# The machine a surrender was about. Without one of these the sentence is about
# something else and the guard has no business in it.
NAMED = {
    "mac": re.compile(r"\b(?:mac|macbook|workstation|trenton-mac)\b", re.I),
    "pi": re.compile(r"\b(?:pi|raspberry ?pi|sunday)\b", re.I),
    "windows": re.compile(r"\b(?:windows|desktop|trentons-desktop)\b", re.I),
    "vps": re.compile(r"\b(?:vps|vultr|domebreak-vps)\b", re.I),
}


def ssh_base():
    return ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={CONNECT_TIMEOUT}"]


def is_local(alias):
    """Whether the machine asked for is the one running this.

    A route to yourself is a hop that cannot work, since neither end holds a key
    authorizing the other back to itself.
    """
    name = socket.gethostname().lower()
    if alias == "pi":
        return name.startswith("raspberrypi")
    if alias == "mac":
        return sys.platform == "darwin" and Path.home().name == "trentontaylor"
    if alias == "windows":
        return sys.platform.startswith("win")
    return False


def wrap(alias, command):
    """The argv that runs `command` on `alias` from here.

    Direct where ssh already resolves the host, and direct whenever the jump is
    this machine, since a hop through yourself asks the host to authorize a
    connection back to itself. Otherwise through the Pi, whose own config names
    every other machine. The inner command is quoted for the shell on each
    machine it passes through, so a hop costs a level of quoting rather than a
    broken command.
    """
    if is_local(alias):
        return ["bash", "-lc", command]
    host = HOSTS[alias][0]
    direct = ssh_base() + [host, command]
    if alias == JUMP or is_local(JUMP):
        return direct
    inner = " ".join(ssh_base() + [host, shlex.quote(command)])
    return ssh_base() + [HOSTS[JUMP][0], inner]


def attempt(argv, timeout=PROBE_TIMEOUT):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"
    except OSError as e:
        return 127, "", str(e)


def route_of(alias):
    """How this machine reaches `alias`, or None when nothing does.

    Direct is tried before the jump because it is one connection rather than
    two; the jump is what makes the cloud case work at all, since a container
    resolves no MagicDNS name of its own.
    """
    if is_local(alias):
        return "local"
    host = HOSTS[alias][0]
    if attempt(ssh_base() + [host, "true"])[0] == 0:
        return "direct"
    if alias != JUMP and attempt(wrap(alias, "true"))[0] == 0:
        return "via %s" % HOSTS[JUMP][0]
    return None


def cache_read():
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}


def cache_write(data):
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(data, indent=2) + "\n")
    except OSError:
        pass


def reachable(alias, max_age=CACHE_TTL):
    """The route to `alias`, from cache while it is fresh.

    A probe costs a round trip over a tunnel and the Stop hook runs on every
    turn, so a recent answer stands rather than being taken again.
    """
    data = cache_read()
    row = data.get(alias)
    if row and time.time() - row.get("at", 0) < max_age:
        return row.get("route")
    route = route_of(alias)
    data[alias] = {"route": route, "at": int(time.time())}
    cache_write(data)
    return route


def cmd_hosts(probe=True):
    for alias, (host, what) in HOSTS.items():
        route = reachable(alias) if probe else "?"
        state = route or "out of reach"
        print("%-8s %-18s %-14s %s" % (alias, host, state, what))
    return 0


def cmd_announce():
    """SessionStart: name the machines reachable from here.

    Only the jump host is probed. Probing all four would cost four tunnelled
    round trips at every session start, and the Pi is the one that decides
    whether any of the others can be reached from a container.
    """
    if not any((Path.home() / ".ssh" / n).exists() for n in ("config", "cloud_sunday")):
        return 0
    route = reachable(JUMP, max_age=CACHE_TTL)
    if not route:
        print("Remote access: the Pi is not answering, so the Mac, the Windows "
              "desktop and the VPS cannot be reached from here either. "
              "~/.intelligence/tools/remote-access.py hosts re-probes.")
        return 0
    print("Remote access: the Pi answers (%s), and the Mac, the Windows desktop "
          "and the VPS are reachable through it. Running in the cloud does not "
          "mean cut off from them.\n"
          "  ~/.intelligence/tools/remote-access.py run mac -- <command>\n"
          "  ~/.intelligence/tools/remote-access.py hosts\n"
          "Work belonging on one of those machines gets done over that route, "
          "never handed back to be run by hand." % route)
    return 0


def cmd_run(argv):
    if not argv:
        print("usage: remote-access.py run <host> -- <command>", file=sys.stderr)
        return 2
    alias = argv[0]
    if alias not in HOSTS:
        print("unknown host %r; try one of %s" % (alias, ", ".join(HOSTS)), file=sys.stderr)
        return 2
    rest = argv[1:]
    if rest and rest[0] == "--":
        rest = rest[1:]
    if not rest:
        print("no command given", file=sys.stderr)
        return 2
    command = " ".join(rest)
    code, out, err = attempt(wrap(alias, command), timeout=600)
    sys.stdout.write(out)
    sys.stderr.write(err)
    return code


def cmd_read(argv):
    if len(argv) < 2:
        print("usage: remote-access.py read <host> <path>", file=sys.stderr)
        return 2
    alias, path = argv[0], argv[1]
    if alias not in HOSTS:
        print("unknown host %r" % alias, file=sys.stderr)
        return 2
    code, out, err = attempt(wrap(alias, "cat %s" % shlex.quote(path)), timeout=600)
    sys.stdout.write(out)
    sys.stderr.write(err)
    return code


def cmd_check(argv):
    aliases = argv or list(HOSTS)
    bad = 0
    for alias in aliases:
        if alias not in HOSTS:
            print("unknown host %r" % alias, file=sys.stderr)
            return 2
        route = route_of(alias)
        print("%-8s %s" % (alias, route or "out of reach"))
        bad += 0 if route else 1
    return 1 if bad else 0


def read_transcript(path):
    try:
        return [json.loads(l) for l in open(path) if l.strip()]
    except (OSError, ValueError):
        return []


def final_reply(rows):
    """Every assistant text block since the last user turn, in spoken order.

    The whole closing reply, not just the last message: a surrender can sit in
    any of the messages a multi-part turn ends with.
    """
    text = []
    for row in reversed(rows):
        if row.get("type") == "user":
            break
        if row.get("type") != "assistant":
            continue
        content = (row.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "text":
                text.append(block.get("text", ""))
    return "\n".join(reversed(text))


def prose_only(text):
    """The reply's sentences, with its fenced blocks dropped.

    Loaded from _lib by path, the way every tool here reaches it, since hooks
    run this file as a script from arbitrary directories. A tree that arrives
    without _lib reads the whole reply, which is what this did before the
    module existed -- a Stop hook that crashes blocks every reply, and that
    costs more than the false positive it would avoid.
    """
    try:
        here = Path(__file__).resolve().parent / "_lib.py"
        path = here if here.is_file() else Path.home() / ".intelligence" / "tools" / "_lib.py"
        spec = importlib.util.spec_from_file_location("intelligence_tools_lib", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.prose_only(text)
    except Exception:
        return text


def surrenders(text):
    """The machines a reply gave up on, by alias.

    A surrender and a machine name have to land in the same sentence. Measured
    over a whole reply they meet by accident: a note that the VPS is down sits
    happily beside an unrelated line about the Mac.

    Fenced blocks are not read at all. A script quoted into a reply carries its
    own error strings -- "the Pi is not answering" is a line the setup prints,
    not the writer giving up on the Pi.
    """
    found = []
    for sentence in re.split(r"(?<=[.!?\n])\s+", prose_only(text)):
        if not SURRENDER.search(sentence):
            continue
        for alias, pattern in NAMED.items():
            if pattern.search(sentence) and alias not in found:
                found.append(alias)
    return found


def guard_stop():
    if os.environ.get("INTELLIGENCE_REMOTE_OFF") == "1":
        sys.exit(0)
    try:
        ev = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)
    if ev.get("stop_hook_active"):
        sys.exit(0)
    path = ev.get("transcript_path")
    if not path or not Path(path).exists():
        sys.exit(0)
    text = final_reply(read_transcript(path))
    if not text.strip():
        sys.exit(0)
    given_up = surrenders(text)
    if not given_up:
        sys.exit(0)
    live = [(a, r) for a in given_up if (r := reachable(a))]
    if not live:
        sys.exit(0)
    lines = "".join("  %s is reachable (%s)\n" % (HOSTS[a][0], r) for a, r in live)
    sys.stderr.write(
        "\nBLOCKED: this reply gives up on a machine that answers from here.\n\n"
        + lines
        + "\nDo the work over that route and report the result:\n"
        "  ~/.intelligence/tools/remote-access.py run %s -- <command>\n"
        "A cloud container reaches the Pi over the Funnel tunnel and every other\n"
        "machine through it. Say a machine is out of reach only when a probe says\n"
        "so: ~/.intelligence/tools/remote-access.py check.\n"
        "INTELLIGENCE_REMOTE_OFF=1 disables this.\n" % live[0][0]
    )
    sys.exit(2)


def install():
    settings = INTELLIGENCE / "settings.json"
    try:
        data = json.loads(settings.read_text())
    except (OSError, ValueError):
        return 1
    tool = "~/.intelligence/tools/remote-access.py"
    wanted = [("Stop", "*", "%s guard-stop" % tool),
              ("SessionStart", "*", "%s announce" % tool),
              ("SessionStart", "*", "%s install" % tool)]
    changed = False
    for event, matcher, command in wanted:
        entries = data.setdefault("hooks", {}).setdefault(event, [])
        if any(command in h.get("command", "")
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
        print("wired %s[%s]" % (event, matcher))
    if changed:
        settings.write_text(json.dumps(data, indent=2) + "\n")
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "hosts"
    rest = sys.argv[2:]
    if mode == "guard-stop":
        guard_stop()
    elif mode == "announce":
        return cmd_announce()
    elif mode == "hosts":
        return cmd_hosts()
    elif mode == "run":
        return cmd_run(rest)
    elif mode == "read":
        return cmd_read(rest)
    elif mode == "check":
        return cmd_check(rest)
    elif mode == "install":
        return install()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
