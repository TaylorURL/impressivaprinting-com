#!/usr/bin/env python3
"""Keeps AI attribution off GitHub, on every write, in every environment.

Nothing on GitHub - commit, pull request, issue, comment, release - may carry AI
attribution. The model honours that in the text it writes, but two things slip
past intent: a stray "Co-Authored-By: Claude" trailer or a "Generated with Claude
Code" footer the model adds itself, and a footer a harness appends server-side
after the create call has already returned. This hook covers both.

  guard   PreToolUse. Deny any GitHub write whose payload carries attribution,
          before it reaches GitHub. This is the hard block: the write cannot land.
  strip   PostToolUse. A footer added server-side is invisible to the guard
          because it appears after the call. Fetch the pull request or issue the
          write touched and remove the footer from its body.

Both read the hook's JSON event on stdin. Wired for the Bash tool (git and gh)
and the mcp__github__* write tools.
"""
import json
import re
import subprocess
import sys

# The marks of AI authorship. Specific phrases, not the bare word "claude", so a
# branch or repo named intelligence never trips the block.
ATTRIBUTION = [
    re.compile(r"generated\s+(?:with|by)\s+claude", re.I),
    re.compile(r"co-authored-by:\s*claude", re.I),
    re.compile(r"\N{ROBOT FACE}\s*generated", re.I),
    re.compile(r"made\s+with\s+claude", re.I),
    re.compile(r"created\s+(?:with|by)\s+claude\s*code", re.I),
    re.compile(r"\bvia\s+claude\s*code\b", re.I),
    re.compile(r"claude\.ai/code", re.I),
    re.compile(r"https?://\S*/code/session[\w-]*", re.I),
]

# A Bash command that writes to GitHub. Reads (git log, gh pr list) are ignored.
GH_WRITE = re.compile(
    r"\bgit\s+commit\b"
    r"|\bgit\s+push\b"
    r"|\bgh\s+pr\s+(?:create|edit|comment|merge|review)\b"
    r"|\bgh\s+issue\s+(?:create|edit|comment)\b"
    r"|\bgh\s+release\s+(?:create|edit)\b"
    r"|\bgh\s+api\b[^\n]*(?:-X|--method)\s*(?:POST|PATCH|PUT)\b",
    re.I,
)

# The mcp__github__* tools that write. Reads carry no body, so they never match
# the attribution patterns anyway; this keeps the guard focused.
MCP_WRITE = re.compile(
    r"^mcp__github__.*"
    r"(?:create|update|add|edit|merge|comment|push|delete|dispatch|request)",
    re.I,
)

FOOTER = re.compile(
    r"\n*[-\s>*]*(?:"
    r"\N{ROBOT FACE}\s*)?generated\s+(?:with|by)\s+\[?claude\s*code.*$"
    r"|\n*[-\s>*]*co-authored-by:\s*claude.*$"
    r"|\n*[-\s>*]*https?://\S*/code/session[\w-]*\s*$",
    re.I | re.M,
)


def has_attribution(text):
    return bool(text) and any(p.search(text) for p in ATTRIBUTION)


def load_event():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def guard():
    """Deny a GitHub write that carries attribution. Exit 2 blocks the tool."""
    ev = load_event()
    tool = ev.get("tool_name", "")
    ti = ev.get("tool_input", {}) or {}
    if tool == "Bash":
        cmd = ti.get("command", "")
        if GH_WRITE.search(cmd) and has_attribution(cmd):
            deny()
    elif MCP_WRITE.match(tool):
        if has_attribution(json.dumps(ti)):
            deny()
    sys.exit(0)


def deny():
    sys.stderr.write(
        "Blocked: this GitHub write carries AI attribution (a Co-Authored-By: "
        "Claude trailer, a 'Generated with Claude Code' footer, or a session "
        "link). Remove every trace of it and write as the human author, then "
        "retry. This is not optional.\n"
    )
    sys.exit(2)


def gh_json(args):
    try:
        out = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
        return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else None
    except Exception:
        return None


def strip():
    """Remove a server-appended footer from the pull request or issue just written."""
    ev = load_event()
    tool = ev.get("tool_name", "")
    ti = ev.get("tool_input", {}) or {}
    resp = ev.get("tool_response", ev.get("tool_result", {})) or {}
    blob = json.dumps(resp) + "\n" + json.dumps(ti)

    m = re.search(r"github\.com/([^/\s\"]+)/([^/\s\"]+)/(?:pull|issues)/(\d+)", blob)
    repo = num = None
    if m:
        repo, num = f"{m.group(1)}/{m.group(2)}", m.group(3)
    else:
        owner = ti.get("owner")
        name = ti.get("repo")
        num = ti.get("pullNumber") or ti.get("issue_number") or ti.get("number")
        if owner and name and num:
            repo = f"{owner}/{name}"
    if not (repo and num):
        sys.exit(0)

    kind = "issues" if "issue" in tool.lower() or "/issues/" in blob else "pulls"
    obj = gh_json(["api", f"repos/{repo}/{kind}/{num}"])
    if not obj:
        # A pull is also reachable through the issues endpoint for its body.
        obj = gh_json(["api", f"repos/{repo}/issues/{num}"])
        kind = "issues"
    if not obj:
        sys.exit(0)
    body = obj.get("body") or ""
    cleaned = FOOTER.sub("", body).rstrip() + "\n" if body else body
    cleaned = cleaned.rstrip("\n")
    if cleaned != (body or "").rstrip("\n"):
        subprocess.run(
            ["gh", "api", "-X", "PATCH", f"repos/{repo}/{kind}/{num}",
             "-f", f"body={cleaned}"],
            capture_output=True, text=True, timeout=30,
        )
    sys.exit(0)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "guard"
    if mode == "strip":
        try:
            strip()
        except Exception:
            sys.exit(0)
    else:
        guard()
