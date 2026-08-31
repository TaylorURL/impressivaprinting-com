#!/usr/bin/env python3
"""Cases the Stripe guard has to get right.

Reads pass on every surface and writes are refused on every surface. The
approval is per object: naming one invoice opens that invoice and nothing
beside it, which is the whole point of holding the approval in the variable
rather than in a mode.

  stripe-guard-cases.py        run them
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "stripe-guard.py")

INVOICE = "in_1QaBcDeFgHiJkLmN"
OTHER = "in_9ZyXwVuTsRqPoNmL"
ACCOUNT = "acct_1SD4TDRl1Yxm7pjb"
FAILURES = []


def run(verb, payload, env=None):
    p = subprocess.run([sys.executable, str(TARGET), verb],
                       input=json.dumps(payload), capture_output=True,
                       text=True, env={**os.environ, **(env or {})})
    return p.returncode


def bash(command, env=None):
    return run("guard-bash", {"tool_name": "Bash",
                              "tool_input": {"command": command}}, env)


def mcp(tool, inp, env=None):
    return run("guard-mcp", {"tool_name": tool, "tool_input": inp}, env)


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got}, want {want}")


def main():
    check("list invoices", bash("stripe invoices list --limit 10"), 0)
    check("read a customer", bash("stripe customers retrieve cus_V7AOsCK"), 0)
    check("read over curl",
          bash(f"curl https://api.stripe.com/v1/invoices/{INVOICE}"), 0)

    check("void an invoice",
          bash(f"stripe invoices void {INVOICE}"), 2)
    check("finalize an invoice",
          bash(f"stripe invoices finalize {INVOICE}"), 2)
    check("create a subscription",
          bash("stripe subscriptions create --customer cus_V7AOsCK"), 2)
    check("refund a charge", bash("stripe refunds create --charge ch_3AbC"), 2)
    check("write over curl",
          bash(f"curl -X POST https://api.stripe.com/v1/invoices/{INVOICE}/void"),
          2)

    check("mcp read", mcp("mcp__x__stripe_api_read", {"path": "/v1/invoices"}), 0)
    check("mcp write",
          mcp("mcp__x__stripe_api_write",
              {"path": f"/v1/invoices/{INVOICE}/void"}), 2)

    check("approved object",
          bash(f"stripe invoices void {INVOICE}",
               {"INTELLIGENCE_STRIPE_WRITE": INVOICE}), 0)
    check("approval does not carry to another object",
          bash(f"stripe invoices void {OTHER}",
               {"INTELLIGENCE_STRIPE_WRITE": INVOICE}), 2)
    check("approval does not cover a write naming both",
          bash(f"stripe invoices void {INVOICE} {OTHER}",
               {"INTELLIGENCE_STRIPE_WRITE": INVOICE}), 2)
    check("approval does not cover a write naming no object",
          bash("stripe subscriptions create --customer cus_V7AOsCK",
               {"INTELLIGENCE_STRIPE_WRITE": INVOICE}), 2)

    # The account is an object an approval can name. Its business profile holds
    # the support phone every receipt prints, so a settings write has to be
    # refusable and approvable the same way a refund is.
    account_write = {"account": ACCOUNT,
                     "business_profile": {"support_phone": "+15550000000"}}
    check("account write unapproved",
          mcp("mcp__x__stripe_api_write", account_write), 2)
    check("approved account write",
          mcp("mcp__x__stripe_api_write", account_write,
              {"INTELLIGENCE_STRIPE_WRITE": ACCOUNT}), 0)
    check("an account approval reaches no invoice",
          bash("stripe invoices %s %s" % ("void", INVOICE),
               {"INTELLIGENCE_STRIPE_WRITE": ACCOUNT}), 2)

    check("unrelated command", bash("git commit -m 'stripe notes'"), 0)

    # A search naming a write verb is a reading, not a write.
    check("grep for a write", bash("grep -rn 'stripe invoices void' ."), 0)
    check("a write sharing a line with a search is still caught",
          bash("grep -rn stripe . && stripe invoices void %s" % INVOICE), 2)

    for f in FAILURES:
        print(f)
    print(f"stripe-guard: {len(FAILURES)} failing")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
