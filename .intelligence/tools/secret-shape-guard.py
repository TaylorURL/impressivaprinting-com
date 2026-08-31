#!/usr/bin/env python3
"""A credential reaches a program through the environment, never a command line.

The vault answers into the transcript, and a value pasted from there onto a
command line is in the shell history, the process table and every log watching
either. with-credential.py opens one vault session inside a single process and
hands the value to the child's environment without rendering it:

  ~/.intelligence/tools/with-credential.py name=VAR -- <the command>

GitHub tokens are deliberately absent from the shapes below. They live in
settings.json, sync with it on purpose, and are never a finding.

  guard-bash   a shell command carrying a credential
  guard-edit   a write carrying one into a file
  scan <path>  what a file carries

INTELLIGENCE_ALLOW_SECRET=1 overrides one call the guard has misread.
"""
import json
import os
import re
import sys

SHAPES = [
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("stripe-live-key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{20,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{32,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b")),
    ("npm-token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("sendgrid-key",
     re.compile(r"\bSG\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\b")),
    ("supabase-service-role",
     re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{20,}"
                r"\.[A-Za-z0-9_\-]{20,}\b")),
    ("private-key-block",
     re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY")),
    ("credentialled-url",
     re.compile(r"\b(?:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis|amqp)"
                r"://[^\s:@/\"']+:[^\s:@/\"']{6,}@[A-Za-z0-9.\-]+")),
]

# A value that is key-shaped and is not a key: the placeholders a fixture needs,
# and the interpolations that stand where a value will be at run time. The
# reserved documentation hosts count; the bare word "example" does not, since it
# appears beside real values often enough to hide one.
FIXTURE = re.compile(
    r"THIS[-_]IS[-_]NOT[-_]A[-_]REAL|NOT[-_]A[-_]REAL|PLACEHOLDER|REDACTED|"
    r"XXXX|\.\.\.|\$\{|\$[A-Z_]{3,}|<[a-z-]+>|your[-_]|"
    r"\bexample\.(?:com|org|net)\b", re.I)


def findings(text):
    out = []
    for name, pattern in SHAPES:
        for m in pattern.finditer(text or ""):
            window = text[max(0, m.start() - 40):m.end() + 40]
            if FIXTURE.search(window):
                continue
            out.append((name, m.group(0)))
    return out


def masked(value):
    return value[:6] + "..." + value[-4:] if len(value) > 14 else "..."


def refuse(where, found):
    rows = "\n".join("  %s  %s" % (n, masked(v)) for n, v in found)
    sys.stderr.write(
        "BLOCKED: %s carries a credential.\n\n%s\n\n"
        "A secret goes to a program through the environment, never a command\n"
        "line or a file:\n\n"
        "  ~/.intelligence/tools/with-credential.py name=VAR -- <the command>\n\n"
        "INTELLIGENCE_ALLOW_SECRET=1 overrides a misread.\n" % (where, rows))
    sys.exit(2)


def payload():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def own_source(path):
    return os.path.basename(path or "") in (
        "secret-shape-guard.py", "secret-shape-guard-cases.py")


def main():
    if os.environ.get("INTELLIGENCE_ALLOW_SECRET") == "1":
        return 0
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "guard-bash":
        p = payload()
        found = findings(str((p.get("tool_input") or {}).get("command") or ""))
        if found:
            refuse("this command", found)
    elif verb == "guard-edit":
        p = payload()
        inp = p.get("tool_input") or {}
        if own_source(str(inp.get("file_path") or "")):
            return 0
        body = "".join(str(inp.get(k) or "")
                       for k in ("content", "new_string", "new_source"))
        old = str(inp.get("old_string") or "")
        found = [(n, v) for n, v in findings(body) if v not in old]
        if found:
            refuse("this write", found)
    elif verb == "scan":
        bad = 0
        for path in sys.argv[2:]:
            if own_source(path):
                continue
            try:
                found = findings(open(path, errors="replace").read())
            except OSError:
                continue
            if found:
                bad += 1
                print(path)
                for n, v in found:
                    print("  %s  %s" % (n, masked(v)))
        return 1 if bad else 0
    else:
        sys.stderr.write(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
