#!/usr/bin/env python3
"""Run a command with credentials from CryptoFort in its environment.

The vault is reachable only over the MCP server's stdio protocol, which leaves
every caller two bad options: read the secret into a transcript and paste it onto
a command line, or do without. Both have happened. A key that reaches a command
line reaches the shell history, the process table, and whatever log is watching,
and a checklist that does without files a gate as unread when the credential was
sitting in the vault the whole time.

This is the third option. The secret travels from the server into the child's
environment inside one process and is never rendered anywhere a person or a log
can see it.

    with-credential.py google-pagespeed-api-key=GOOGLE_PAGESPEED_API_KEY -- probe.py all

Each argument before `--` maps a credential name to the variable the child reads
it from. A credential the vault does not hold is named on stderr and left unset,
because a tool that reports the variable it wanted gives a better error than this
one could invent.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SERVER = str(Path.home() / ".intelligence" / "cryptofort-mcp.sh")


class Vault:
    """One MCP session, opened once and reused for every credential asked for."""

    def __init__(self):
        # This process is the one place a decrypted secret is allowed to exist:
        # it goes straight into a child's environment and is never rendered. The
        # read permission is asked for here rather than granted in the launcher,
        # so a session reaching the vault any other way cannot read a value at
        # all. The launcher puts --allow-write ahead of these arguments, so this
        # private session also carries put and purge; it calls neither.
        self.proc = subprocess.Popen(
            ["bash", SERVER, "--allow-secret-read"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.seq = 0
        self._call("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "with-credential", "version": "1"}})
        self._notify("notifications/initialized")

    def _send(self, payload):
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def _notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _call(self, method, params):
        self.seq += 1
        self._send({"jsonrpc": "2.0", "id": self.seq, "method": method, "params": params})
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("the vault closed before answering")
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get("id") == self.seq:
                if "error" in msg:
                    raise RuntimeError(msg["error"].get("message", "unknown vault error"))
                return msg.get("result", {})

    def get(self, name):
        result = self._call("tools/call",
                            {"name": "credential_get", "arguments": {"name": name}})
        if result.get("isError"):
            raise RuntimeError("the vault holds no %s" % name)
        for block in result.get("content", []):
            if block.get("type") != "text":
                continue
            text = block.get("text", "")
            try:
                payload = json.loads(text)
            except ValueError:
                return text.strip()
            if isinstance(payload, dict):
                for field in ("secret", "value", "password", "token"):
                    if payload.get(field):
                        return str(payload[field])
            return text.strip()
        raise RuntimeError("the vault returned no value for %s" % name)

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def main():
    argv = sys.argv[1:]
    if "--" not in argv:
        print(__doc__, file=sys.stderr)
        return 2
    split = argv.index("--")
    mappings, command = argv[:split], argv[split + 1:]
    if not command:
        print("nothing to run after --", file=sys.stderr)
        return 2

    env = dict(os.environ)
    vault, missing = None, []
    try:
        for pair in mappings:
            name, _, var = pair.partition("=")
            if not name or not var:
                print("%r is not <credential-name>=<ENV_VAR>" % pair, file=sys.stderr)
                return 2
            if vault is None:
                vault = Vault()
            try:
                env[var] = vault.get(name)
            except RuntimeError as exc:
                missing.append("%s -> %s: %s" % (name, var, exc))
    finally:
        if vault is not None:
            vault.close()

    for row in missing:
        print("unset: %s" % row, file=sys.stderr)
    return subprocess.run(command, env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
