#!/usr/bin/env python3
"""Cases the billing read has to get right.

Three properties carry it. A hand-raised client's owed periods have to be
derived rather than remembered, or the month nobody raised is the month nobody
notices. An invoice that exists in Stripe and not in the ledger has to count as
raised, since the ledger is the copy and Stripe is the record. And the module
has to stay incapable of a write: the key in use carries write scope, so the
read-only half holds only as long as no request builder here can produce
anything but a GET.

  billing-review-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "billing-review.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LEDGER = {
    "account": "acct_test",
    "clients": [
        {"id": "monthly-one", "name": "Monthly One", "project": "P",
         "stripe_customer": "cus_1", "amount_usd": 99.99, "period": "monthly",
         "collection": "hand-raised", "first_period": "2026-06",
         "raised": ["2026-06"]},
        {"id": "annual-one", "name": "Annual One", "project": "Q",
         "stripe_customer": "cus_2", "amount_usd": 550.0, "period": "annual",
         "collection": "hand-raised", "first_period": "2026-06",
         "raised": ["2026-06"], "renews": "2027-06-22"},
    ],
}


def tree(tmp):
    root = Path(tmp)
    (root / "billing").mkdir()
    (root / "billing" / "clients.json").write_text(json.dumps(LEDGER))
    return root


def main():
    mod = load()

    check("months across a year boundary",
          mod.months_between("2026-11", date(2027, 2, 1)),
          ["2026-11", "2026-12", "2027-01", "2027-02"])
    check("one month is one period",
          mod.months_between("2026-08", date(2026, 8, 30)), ["2026-08"])

    monthly, annual = LEDGER["clients"]
    check("a monthly client owes every month since the first",
          mod.expected_periods(monthly, date(2026, 9, 5)),
          ["2026-06", "2026-07", "2026-08", "2026-09"])
    check("an annual client owes one period a year",
          mod.expected_periods(annual, date(2028, 1, 1)),
          ["2026-06", "2027-06"])

    # A draft is not money owed and a void is money withdrawn; neither marks a
    # period raised.
    invoices = [
        {"status": "paid", "created": 1780272000},
        {"status": "draft", "created": 1782950400},
        {"status": "void", "created": 1785628800},
        {"status": "open", "period_start": 1788307200},
    ]
    raised = mod.raised_periods(invoices)
    check("a paid invoice marks its period", mod.period_of(1780272000) in raised, True)
    check("a draft does not", mod.period_of(1782950400) in raised, False)
    check("a void does not", mod.period_of(1785628800) in raised, False)
    check("an open invoice does", mod.period_of(1788307200) in raised, True)
    check("period_start wins where it exists", len(raised), 2)

    with tempfile.TemporaryDirectory() as tmp:
        root = tree(tmp)
        rows = {r["client"]["id"]: r for r in mod.owed(root, "", date(2026, 9, 5))}
        check("an unraised month is the finding",
              rows["monthly-one"]["missing"], ["2026-07", "2026-08", "2026-09"])
        check("a client raised to date has nothing missing",
              rows["annual-one"]["missing"], [])
        check("no key means no Stripe error either",
              rows["monthly-one"]["error"], None)

        # Reported at any distance, because nothing else will raise it.
        renewals = mod.renewals(root, "", date(2026, 9, 5))
        check("a hand-raised renewal is reported far out",
              [c["id"] for c, _, _ in renewals], ["annual-one"])
        check("the count of days is real",
              renewals[0][2], (date(2027, 6, 22) - date(2026, 9, 5)).days)

    # The read-only half, held structurally rather than by habit.
    source = TARGET.read_text()
    check("only GET is constructed",
          sorted(set(re.findall(r'method="([A-Z]+)"', source))), ["GET"])
    check("no write verb reaches a request builder",
          bool(re.search(r'method="(?:POST|PUT|DELETE|PATCH)"', source)), False)
    check("the key is never written to a file",
          bool(re.search(r'write_text\([^)]*key', source)), False)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
