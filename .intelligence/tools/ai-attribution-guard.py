#!/usr/bin/env python3
"""Refuses any commit that names an AI as its author, committer, or co-author.

Attribution reaches a repository through three doors, and a guard on one leaves
the other two open. A trailer gets written into a commit message; a harness
commits under an AI identity without any message naming it; and a push carries
commits made earlier, elsewhere, by something that never saw this machine's
rules. So the same test runs at each door: the harness before a Bash command
runs, git at commit and at push, and a workflow on the server for commits made
where neither of the first two applied.

A squash commit is authored by whoever opened the pull request, so a fourth
door sits past all three: a branch written and pushed as the human still lands
on `develop` as the app when a cloud session opened the PR, and no hook sees it
because GitHub writes that commit after the push they guard. The container's
own credentials are the app's whatever `gh api user` reports, so the open-pr
verb routes the call through a machine holding the human's token instead.

  guard-bash        PreToolUse on Bash. Refuse a git or gh write whose command
                    text, identity flags, or environment names an AI, and
                    refuse a PR opened with credentials that are not the
                    human's.
  hook-commit-msg   git commit-msg. Refuse a message carrying an AI trailer.
  hook-pre-commit   git pre-commit. Refuse the identity the commit would carry.
  hook-pre-push     git pre-push. Scan every commit the push would send.
  open-pr           Open a pull request as the human. Reads the token from a
                    machine that holds one when this one does not.
  scan [range]      Report attribution over a commit range. Exit 1 if any.
  install           Put the git hooks in place and point core.hooksPath at them.

The identity test reads names as well as addresses: a vendor name over a
human's address passes any check that reads only the address.

INTELLIGENCE_ALLOW_AI_ATTRIBUTION=1 overrides a refusal the guard has misread.
"""
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
HOOKS = HOME / ".intelligence" / "scripts" / "git-hooks"
HOOK_NAMES = ("pre-commit", "commit-msg", "pre-push")

# Vendor marks, matched against a name or an address. The bare word "ai" is
# absent on purpose: it appears inside ordinary addresses and would refuse mail
# from anyone whose domain happens to contain it.
IDENTITY = re.compile(
    r"anthropic|claude|openai|codex|copilot|windsurf|\bdevin\b|\bbard\b"
    r"|githubcopilot|cursor\.(?:sh|com)|\[bot\]@",
    re.I,
)

# Attribution inside a message. Anchored on the trailer or the phrase rather
# than the bare vendor name, so a commit that discusses a vendor still lands.
MESSAGE = re.compile(
    r"co-?authored-?by:.*(?:claude|anthropic|codex|openai|copilot|gpt-|gemini|cursor|devin)"
    r"|generated\s+(?:with|by).*(?:claude|codex|openai|copilot|chatgpt)"
    r"|(?:made|written|created|authored)\s+(?:with|by)\s+(?:claude|codex|chatgpt|copilot)"
    r"|claude[-\s]?session:"
    r"|claude\.ai"
    r"|anthropic\.com"
    r"|\N{ROBOT FACE}",
    re.I,
)

# Bash commands that write to a repository or to GitHub. Reads never carry a
# payload, so scanning them only produces false refusals. Options are allowed
# between git and its subcommand: an identity is set through one of them, so a
# pattern expecting the subcommand to come first misses the case it exists for.
GIT_WRITE = re.compile(
    r"\bgit\s+(?:-\S+(?:\s+\S+)?\s+)*(?:commit|merge|revert|cherry-pick|rebase|am|push|tag)\b"
    r"|\bgh\s+(?:pr|issue|release)\s+(?:create|edit|comment|merge|review)\b"
    r"|\bgh\s+api\b.*(?:-X|--method)\s*(?:POST|PATCH|PUT)\b",
    re.I,
)

# An identity handed to git on the command line or through the environment.
# These set the author without the message ever mentioning it.
IDENT_FLAG = re.compile(
    r"--author\s*=?\s*[\"']?([^\"'\n]+)"
    r"|-c\s+user\.(?:name|email)\s*=\s*[\"']?([^\"'\s]+)"
    r"|GIT_(?:AUTHOR|COMMITTER)_(?:NAME|EMAIL)\s*=\s*[\"']?([^\"'\s]+)",
    re.I,
)

# Skipping the hooks is the one flag that turns every local layer off at once.
NO_VERIFY = re.compile(r"--no-verify\b")

# Opening a pull request, in the two spellings a session reaches for. The squash
# commit takes the opener's identity, so this is a write whether or not its text
# names anyone.
PR_OPEN = re.compile(
    r"\bgh\s+pr\s+create\b"
    r"|\bgh\s+api\b(?=.*(?:-X|--method)\s*POST)(?=.*/pulls\b)",
    re.I,
)


def allowed():
    return os.environ.get("INTELLIGENCE_ALLOW_AI_ATTRIBUTION") == "1"


def git(*args, cwd=None):
    p = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)
    return p.stdout if p.returncode == 0 else ""


def identity_hits(name, email, label):
    hits = []
    if IDENTITY.search(name or ""):
        hits.append(f"{label} name: {name.strip()}")
    if IDENTITY.search(email or ""):
        hits.append(f"{label} email: {email.strip()}")
    return hits


def commit_hits(sha, cwd=None):
    raw = git("show", "-s", "--format=%an%x1f%ae%x1f%cn%x1f%ce%x1f%B", sha, cwd=cwd)
    if not raw:
        return []
    an, ae, cn, ce, body = (raw.split("\x1f") + [""] * 5)[:5]
    hits = identity_hits(an, ae, "author") + identity_hits(cn, ce, "committer")
    m = MESSAGE.search(body or "")
    if m:
        hits.append(f"message: {m.group(0).strip()[:90]}")
    return hits


def refuse(lines, remedy):
    sys.stderr.write("\nBLOCKED: AI attribution.\n\n")
    for line in lines:
        sys.stderr.write(f"  {line}\n")
    sys.stderr.write(f"\n{remedy}\n")
    sys.stderr.write("INTELLIGENCE_ALLOW_AI_ATTRIBUTION=1 overrides.\n")


def guard_bash():
    """PreToolUse. Exit 2 denies the command before it runs."""
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if ev.get("tool_name") != "Bash":
        sys.exit(0)
    cmd = (ev.get("tool_input") or {}).get("command", "")
    if not GIT_WRITE.search(cmd):
        sys.exit(0)
    # A cloud container carries its own session-start hook that pins the global
    # identity to an AI name and address. Two session-start hooks have no
    # settled order, and on 2026-08-28 that one ran second, so the repair made
    # at session start was itself undone and the whole run began from the AI
    # identity. Repairing here instead binds it to the moment of use: whatever
    # holds the identity, the write about to carry it gets the human.
    assert_identity()
    if allowed():
        sys.exit(0)

    # Opening the pull request is what decides the squash commit's author, and
    # this container cannot do it as anyone but the app.
    if PR_OPEN.search(cmd) and app_fronted():
        refuse(["pull request opened from a container whose GitHub writes are "
                "issued by the app"],
               "Open it as the human instead:\n"
               "  ~/.intelligence/tools/ai-attribution-guard.py open-pr \\\n"
               "      <owner/repo> <head> <base> <title> <body>")
        sys.exit(2)

    hits = []
    m = MESSAGE.search(cmd)
    if m:
        hits.append(f"message: {m.group(0).strip()[:90]}")
    for match in IDENT_FLAG.finditer(cmd):
        value = next((g for g in match.groups() if g), "")
        if IDENTITY.search(value):
            hits.append(f"identity: {value.strip()}")
    if NO_VERIFY.search(cmd):
        hits.append("--no-verify: turns off every local attribution hook")
    if hits:
        refuse(hits, "Write as the human who owns the work, then retry.")
        sys.exit(2)
    sys.exit(0)


def hook_commit_msg(path):
    if allowed() or not path:
        return 0
    try:
        body = Path(path).read_text(errors="replace")
    except Exception:
        return 0
    body = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
    m = MESSAGE.search(body)
    if m:
        refuse([f"message: {m.group(0).strip()[:90]}"],
               "Remove the trailer and commit again.")
        return 1
    return 0


def hook_pre_commit():
    if allowed():
        return 0
    hits = []
    for var, label in (("GIT_AUTHOR_IDENT", "author"),
                       ("GIT_COMMITTER_IDENT", "committer")):
        m = re.match(r"^(.*?)\s*<([^>]*)>", git("var", var).strip())
        if m:
            hits += identity_hits(m.group(1), m.group(2), label)
    if hits:
        refuse(hits, "Set user.name and user.email to the human who owns the work.")
        return 1
    return 0


def hook_pre_push():
    """Scan the commits each ref update would send.

    A branch the remote does not have yet reports an all-zero remote sha,
    which reads as "no common ancestor" and puts the branch's entire history
    in range. One historical commit carrying attribution then refuses the
    first push of every branch cut after it, however clean the work on top
    is, and the only way through is a rewrite of published history that the
    protected branch will not take. Excluding the remote's own refs leaves
    exactly the commits this push would add, which are the only ones a
    rewrite could still reach.
    """
    if allowed():
        return 0
    bad = []
    for line in sys.stdin:
        parts = line.split()
        if len(parts) < 4:
            continue
        local_sha, remote_sha = parts[1], parts[3]
        if local_sha.strip("0") == "":
            continue
        if remote_sha.strip("0") == "":
            rng = ["rev-list", local_sha, "--not", "--remotes=origin"]
        else:
            rng = ["rev-list", f"{remote_sha}..{local_sha}"]
        for sha in git(*rng).split():
            hits = commit_hits(sha)
            if hits:
                bad.append((sha, hits))
    if bad:
        lines = []
        for sha, hits in bad[:10]:
            lines.append(sha[:12])
            lines += [f"    {h}" for h in hits]
        refuse(lines, "Rewrite those commits before pushing.")
        return 1
    return 0


def scan(rng):
    shas = git("rev-list", rng or "HEAD").split()
    bad = [(s, h) for s in shas if (h := commit_hits(s))]
    for sha, hits in bad:
        print(sha[:12])
        for h in hits:
            print(f"    {h}")
    print(f"{len(bad)} of {len(shas)} commit(s) carry AI attribution.")
    return 1 if bad else 0


def wire_settings():
    """Put the harness hooks back into settings.json.

    The config sync settles a conflict by edit time over whole files, so a
    machine holding an older settings.json with a later clock reverts this
    wiring and reports the run as a pull. Rewiring on every session start is
    what makes that cost one session rather than standing.
    """
    settings = HOME / ".intelligence" / "settings.json"
    try:
        data = json.loads(settings.read_text())
    except Exception:
        return
    tool = "~/.intelligence/tools/ai-attribution-guard.py"
    wanted = [("PreToolUse", "Bash", f"{tool} guard-bash"),
              ("SessionStart", "*", f"{tool} install")]
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
        print(f"wired {event}[{matcher}]")
    if changed:
        settings.write_text(json.dumps(data, indent=2) + "\n")


def human_identity():
    """The name and address commits belong to, or None where none is recorded.

    Read from the environment first so a machine can override, then from the
    settings the config mirror carries, which is what puts the same answer on
    every machine.
    """
    name = os.environ.get("INTELLIGENCE_GIT_NAME")
    email = os.environ.get("INTELLIGENCE_GIT_EMAIL")
    if not (name and email):
        try:
            env = json.loads((HOME / ".intelligence" / "settings.json").read_text())
            env = env.get("env") or {}
        except (OSError, ValueError):
            env = {}
        name = name or env.get("INTELLIGENCE_GIT_NAME")
        email = email or env.get("INTELLIGENCE_GIT_EMAIL")
    return (name, email) if name and email else None


def assert_identity():
    """Put the human back on the global git identity when an AI holds it.

    A cloud container is handed an AI name and address at session start, and the
    commit hooks then refuse every commit made there -- correctly, and with no
    way forward, since nothing else sets the identity back. Repairing it at the
    same moment the hooks go in turns that dead end into a working commit.
    """
    who = human_identity()
    if not who:
        return
    name, email = who
    current = (git("config", "--global", "--get", "user.name").strip(),
               git("config", "--global", "--get", "user.email").strip())
    if not identity_hits(current[0], current[1], "author"):
        return
    subprocess.run(["git", "config", "--global", "user.name", name])
    subprocess.run(["git", "config", "--global", "user.email", email])
    # A signature made with a key registered to the AI address reads as
    # unverified once the address is the human's, so the signing goes with it.
    subprocess.run(["git", "config", "--global", "commit.gpgsign", "false"])
    print(f"git identity {current[0]} <{current[1]}> -> {name} <{email}>")


def install():
    """Put the hooks in place and make git use them for every repository."""
    wire_settings()
    assert_identity()
    HOOKS.mkdir(parents=True, exist_ok=True)
    # The hooks travel to every machine through the config mirror, so the tool
    # is located from the hook's own directory rather than written in as a
    # path. An absolute one is right on the machine that installed it and
    # missing everywhere else, which fails every commit on the other machines.
    resolve = ('_ai_tool="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../tools" '
               '&& pwd)/ai-attribution-guard.py"\n')
    for name in HOOK_NAMES:
        path = HOOKS / name
        body = path.read_text() if path.exists() else (
            # core.hooksPath replaces a repository's own hook directory rather
            # than adding to it, so the repository's hook runs from here or it
            # stops running at all.
            "#!/usr/bin/env bash\nset -uo pipefail\n"
            f'own="$(git rev-parse --git-dir 2>/dev/null)/hooks/{name}"\n'
            '[ -x "$own" ] && ! [ "$own" -ef "$0" ] && exec "$own" "$@"\n'
            "exit 0\n"
        )
        if "_ai_tool" in body:
            continue
        # A hook wired by an older build names the tool by absolute path. Those
        # lines come out so the portable call can replace them, rather than the
        # hook keeping a call that cannot run here.
        if "ai-attribution-guard.py" in body:
            body = "".join(l for l in body.splitlines(keepends=True)
                           if "ai-attribution-guard.py" not in l
                           and "_ai_payload" not in l)

        if name == "pre-push":
            # git sends the ref list on stdin and the rest of the hook reads it
            # too, so it is held once and replayed to both readers.
            call = (
                resolve
                + '_ai_payload="$(cat)"\n'
                + f'printf \'%s\\n\' "$_ai_payload" | python3 "$_ai_tool" hook-{name} || exit $?\n'
                + "exec 0< <(printf '%s\\n' \"$_ai_payload\")\n"
            )
        else:
            call = resolve + f'python3 "$_ai_tool" hook-{name} "$@" || exit $?\n'

        # The call goes above the body: every one of these hooks returns early
        # on some path, and a check placed after one of those never runs.
        lines = body.splitlines(keepends=True)
        at = 1
        for i, line in enumerate(lines[:8]):
            if line.startswith("set -"):
                at = i + 1
        path.write_text("".join(lines[:at]) + call + "".join(lines[at:]))
        path.chmod(0o755)
        print(f"wired {name}")
    if git("config", "--global", "core.hooksPath").strip() != str(HOOKS):
        subprocess.run(["git", "config", "--global", "core.hooksPath", str(HOOKS)])
        print(f"core.hooksPath -> {HOOKS}")
    return 0


# A cloud container's GitHub writes are issued by the app that fronts them,
# whatever `gh api user` reports back -- the call is rewritten past the token
# the session holds. So the container is the signal, not the credentials.
def app_fronted():
    return os.environ.get("CLAUDE_CODE_REMOTE") == "true"


# Where a machine that holds the human's token keeps it. The error reporter is
# the one long-running thing on the Pi that needs to write to GitHub as him, so
# its config is where the token already lives.
TOKEN_HOST = os.environ.get("INTELLIGENCE_TOKEN_HOST", "pi")
TOKEN_FILE = os.environ.get("INTELLIGENCE_TOKEN_FILE",
                            "~/error-reporter/config.json")

# Reads the first GitHub token in that config and posts the pull request with
# it, on the machine that holds it. The token is never sent anywhere, never
# printed, and never reaches the machine that called this.
#
# The whole request arrives as one base64 argument rather than as five. A pull
# request body is prose the caller did not write -- it carries backticks, dollar
# signs and quotes as a matter of course -- and reaching the far end of an ssh
# hop means surviving two rounds of shell parsing, not one. The first attempt
# passed it as arguments and the shell on the far side ran a word out of the
# body as a command. Base64 has no character a shell reads.
_REMOTE_OPEN = r"""
python3 - "$1" <<'PY'
import base64, json, os, re, sys, urllib.error, urllib.request
cfg = json.load(open(os.path.expanduser(%(cfg)r)))
token = next(v for v in cfg.values()
             if isinstance(v, str) and re.match(r"^gh[pousr]_", v))
ask = json.loads(base64.b64decode(sys.argv[1]))
req = urllib.request.Request(
    "https://api.github.com/repos/%%s/pulls" %% ask.pop("repo"),
    data=json.dumps(ask).encode(),
    headers={"Authorization": "Bearer " + token,
             "Accept": "application/vnd.github+json",
             "User-Agent": "intelligence-open-pr"})
try:
    out = json.load(urllib.request.urlopen(req))
except urllib.error.HTTPError as e:
    sys.stderr.write(e.read().decode()[:400] + "\n")
    raise SystemExit(1)
print(json.dumps({"number": out["number"], "url": out["html_url"],
                  "opener": out["user"]["login"]}))
PY
"""


def open_pr(repo, head, base, title, body):
    """Open a pull request under an identity that is not the app's.

    The squash commit carries whoever opened the PR, and nothing downstream can
    change that afterwards -- the commit is written on GitHub's side, past every
    hook. Ten repositories took an app-authored commit on develop that way on
    2026-08-27 before anyone noticed, and the only repair for one that has
    landed is a protected-branch rewrite, which is no repair at all. So the
    identity is decided here, before the PR exists.
    """
    if not app_fronted():
        out = subprocess.run(
            ["gh", "api", "-X", "POST", f"repos/{repo}/pulls",
             "-f", f"title={title}", "-f", f"head={head}", "-f", f"base={base}",
             "-f", f"body={body}", "--jq",
             '{number:.number,url:.html_url,opener:.user.login}'],
            capture_output=True, text=True)
        sys.stdout.write(out.stdout)
        sys.stderr.write(out.stderr)
        return out.returncode

    ask = base64.b64encode(json.dumps(
        dict(repo=repo, title=title, head=head, base=base, body=body)
    ).encode()).decode()
    script = _REMOTE_OPEN % {"cfg": TOKEN_FILE}
    remote = HOME / ".intelligence" / "tools" / "remote-access.py"
    out = subprocess.run(
        [sys.executable, str(remote), "run", TOKEN_HOST, "--",
         "bash", "-s", "--", ask],
        input=script, capture_output=True, text=True)
    if out.returncode != 0:
        sys.stderr.write(
            f"open-pr: {TOKEN_HOST} could not open the pull request.\n"
            f"{out.stderr.strip()[:400]}\n\n"
            "The branch is pushed; the pull request is not open. Opening it\n"
            "from this container would author the squash commit as the app.\n")
        return 1
    sys.stdout.write(out.stdout)
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "guard-bash"
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    if mode == "open-pr":
        if len(sys.argv) != 7:
            sys.stderr.write(
                "usage: open-pr <owner/repo> <head> <base> <title> <body>\n")
            sys.exit(2)
        sys.exit(open_pr(*sys.argv[2:7]))
    if mode == "guard-bash":
        guard_bash()
    elif mode == "hook-commit-msg":
        sys.exit(hook_commit_msg(arg))
    elif mode == "hook-pre-commit":
        sys.exit(hook_pre_commit())
    elif mode == "hook-pre-push":
        sys.exit(hook_pre_push())
    elif mode == "scan":
        sys.exit(scan(arg))
    elif mode == "install":
        sys.exit(install())
    # An unrecognised verb exits as a refusal rather than a pass. A caller that
    # probes this guard by a name it does not carry would otherwise read the
    # silent exit as the guard reporting itself wired.
    print(f"unknown verb: {mode}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
