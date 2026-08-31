#!/usr/bin/env python3
"""What Stripe holds, against what the ledger says is owed.

Two live clients are billed by hand and Stripe carries no subscription and no
schedule for either, so a period nobody raises is a period nobody collects.
Stripe cannot report that gap: from its side an uninvoiced month is
indistinguishable from a month with nothing to bill. `billing/clients.json` is
the other half -- what each client actually owes, how it is collected, and which
periods have been raised -- and this reads the two together.

Every call it makes is a GET. The key in use carries write scope whatever its
name says, so the read-only half is enforced here rather than assumed: `get` is
the only request this builds, and there is no verb that reaches a write. An
invoice is raised by a person who has said yes to that invoice.

  billing-review.py report     the full reading
  billing-review.py check      exit non-zero when something needs a person
  billing-review.py ledger     the ledger alone, with no network

STRIPE_API_KEY is read at the point of use and never written anywhere.
INTELLIGENCE_REPO names the intelligence checkout; otherwise it is searched for.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

LEDGER = Path("billing") / "clients.json"
API = "https://api.stripe.com/v1/"

# Beyond this a renewal is somebody else's problem for now. A hand-raised
# renewal is reported at any distance, since nothing else will ever raise it.
RENEWAL_HORIZON_DAYS = 45

# Subscription states that renew nothing. A cancelled subscription keeps the
# period end it died in, which reads as a renewal date long past.
DORMANT = ("canceled", "incomplete_expired", "incomplete")


def repo_root(start=None):
    """The intelligence checkout, or None."""
    named = os.environ.get("INTELLIGENCE_REPO")
    if named and (Path(named) / LEDGER).is_file():
        return Path(named)
    here = Path(start or __file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / LEDGER).is_file():
            return parent
    roots = [Path.cwd(), Path.home()]
    roots += [Path.home() / name for name in
              ("intelligence", "Projects", "IdeaProjects", "WebstormProjects",
               "Development")]
    for root in roots:
        if (root / LEDGER).is_file():
            return root
        try:
            for candidate in root.glob("*/" + str(LEDGER)):
                return candidate.parent.parent
        except OSError:
            pass
    return None


def get(path, params=None, key=None, timeout=20):
    """One GET against the API.

    The only request builder here. A write needs a method this module does not
    construct, which is what keeps a well-argued exception from having anywhere
    to land.
    """
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    request = urllib.request.Request(url, method="GET")
    request.add_header("Authorization", "Bearer %s" % key)
    request.add_header("Stripe-Version", "2024-06-20")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def page(path, params, key):
    """Every object on a list endpoint, following Stripe's cursor."""
    out = []
    params = dict(params or {})
    params.setdefault("limit", 100)
    while True:
        body = get(path, params, key)
        rows = body.get("data") or []
        out.extend(rows)
        if not body.get("has_more") or not rows:
            return out
        params["starting_after"] = rows[-1]["id"]


def months_between(first, today):
    """Every YYYY-MM period from `first` through the month `today` falls in."""
    year, month = (int(part) for part in first.split("-")[:2])
    out = []
    while (year, month) <= (today.year, today.month):
        out.append("%04d-%02d" % (year, month))
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return out


def expected_periods(client, today):
    """The periods this client owes, by the ledger's own reckoning."""
    first = client.get("first_period")
    if not first:
        return []
    if client.get("period") == "monthly":
        return months_between(first, today)
    if client.get("period") == "annual":
        out, year = [], int(first.split("-")[0])
        month = first.split("-")[1]
        while date(year, int(month), 1) <= today:
            out.append("%04d-%s" % (year, month))
            year += 1
        return out
    return [first]


def period_of(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m")


def money(cents, currency="usd"):
    return "%s%.2f" % ("$" if currency == "usd" else "", (cents or 0) / 100.0)


def read_ledger(root):
    return json.loads((root / LEDGER).read_text())


def invoices_for(client, key):
    customer = client.get("stripe_customer")
    if not customer:
        return []
    return page("invoices", {"customer": customer}, key)


def raised_periods(invoices):
    """The periods Stripe holds an invoice against, however it was raised.

    Read from the invoice's own period where it carries one and from its
    creation date otherwise, since a hand-raised invoice carries no period.
    """
    out = set()
    for invoice in invoices:
        if invoice.get("status") in ("draft", "void"):
            continue
        stamp = (invoice.get("period_start") or invoice.get("created"))
        if stamp:
            out.add(period_of(stamp))
    return out


def owed(root, key, today=None):
    """Per client, the periods the ledger expects and Stripe does not hold."""
    today = today or date.today()
    ledger = read_ledger(root)
    out = []
    for client in ledger.get("clients", []):
        expected = expected_periods(client, today)
        recorded = set(client.get("raised") or [])
        stripe_side, error = set(), None
        if key:
            try:
                stripe_side = raised_periods(invoices_for(client, key))
            except Exception as problem:
                error = str(problem)
        missing = [p for p in expected
                   if p not in recorded and p not in stripe_side]
        drifted = sorted(stripe_side - recorded) if key and not error else []
        out.append({
            "client": client,
            "expected": expected,
            "missing": missing,
            "ledger_behind": drifted,
            "error": error,
        })
    return out


def overdue(key, now=None):
    """Invoices raised and not paid, and charges that failed this week."""
    now = now or datetime.now(timezone.utc)
    week = int((now - timedelta(days=7)).timestamp())
    late = []
    for invoice in page("invoices", {"status": "open"}, key):
        due = invoice.get("due_date")
        if due and due < int(now.timestamp()):
            late.append(invoice)
    failed = [c for c in page("charges", {"created[gte]": week}, key)
              if c.get("status") == "failed"]
    uncollectible = page("invoices", {"status": "uncollectible"}, key)
    stalled = [s for s in page("subscriptions", {"status": "all"}, key)
               if s.get("status") in ("past_due", "unpaid")]
    return late, failed, uncollectible, stalled


def renewals(root, key, today=None):
    """What renews soon, plus every hand-raised renewal at any distance."""
    today = today or date.today()
    horizon = today + timedelta(days=RENEWAL_HORIZON_DAYS)
    out = []
    for client in read_ledger(root).get("clients", []):
        when = client.get("renews")
        if not when:
            continue
        due = date.fromisoformat(when)
        if client.get("collection") == "hand-raised" or due <= horizon:
            out.append((client, due, (due - today).days))
    if key:
        for subscription in page("subscriptions", {"status": "all"}, key):
            end = subscription.get("current_period_end")
            if not end or subscription.get("status") in DORMANT:
                continue
            due = datetime.fromtimestamp(end, timezone.utc).date()
            if today <= due <= horizon:
                out.append((subscription, due, (due - today).days))
    return out


def report(root, key):
    """The whole reading, printed. Returns True when something needs a person."""
    ledger = read_ledger(root)
    today = date.today()
    needs_person = False

    print("Account %s, ledger of %d client(s), read %s"
          % (ledger.get("account", "?"), len(ledger.get("clients", [])), today))
    if not key:
        print("\nSTRIPE_API_KEY is not set, so nothing below was checked against "
              "Stripe. The ledger's own reckoning follows; treat it as a claim.")

    print("\nOwed and not raised")
    for row in owed(root, key, today):
        client = row["client"]
        head = "  %s (%s, %s %s)" % (client["name"], client["project"],
                                     money(client["amount_usd"] * 100),
                                     client["period"])
        if row["error"]:
            print("%s: Stripe could not be read (%s)" % (head, row["error"]))
            needs_person = True
            continue
        if row["missing"]:
            needs_person = True
            print("%s: no invoice for %s" % (head, ", ".join(row["missing"])))
            print("      approve to raise: %s, %s, covering %s"
                  % (client["stripe_customer"], money(client["amount_usd"] * 100),
                     row["missing"][-1]))
        else:
            print("%s: every period through %s is invoiced"
                  % (head, row["expected"][-1] if row["expected"] else "-"))
        if row["ledger_behind"]:
            print("      the ledger is behind Stripe on: %s"
                  % ", ".join(row["ledger_behind"]))

    print("\nLate and failed")
    if not key:
        print("  not read")
    else:
        try:
            late, failed, uncollectible, stalled = overdue(key)
        except Exception as problem:
            print("  Stripe could not be read (%s)" % problem)
            needs_person = True
        else:
            for invoice in late:
                needs_person = True
                days = (datetime.now(timezone.utc)
                        - datetime.fromtimestamp(invoice["due_date"], timezone.utc)).days
                print("  %s %s is %d day(s) past due (%s)"
                      % (invoice.get("customer"), money(invoice.get("amount_due"),
                                                        invoice.get("currency", "usd")),
                         days, invoice.get("number") or invoice["id"]))
            for charge in failed:
                needs_person = True
                when = datetime.fromtimestamp(charge.get("created", 0),
                                              timezone.utc).date()
                print("  %s failed for %s on %s: %s"
                      % (money(charge.get("amount"), charge.get("currency", "usd")),
                         charge.get("customer"), when,
                         charge.get("failure_message")
                         or charge.get("failure_code") or "no reason given"))
            for invoice in uncollectible:
                needs_person = True
                print("  %s is marked uncollectible (%s)"
                      % (invoice.get("number") or invoice["id"], invoice.get("customer")))
            for subscription in stalled:
                needs_person = True
                print("  subscription %s for %s is %s"
                      % (subscription["id"], subscription.get("customer"),
                         subscription.get("status")))
            if not (late or failed or uncollectible or stalled):
                print("  nothing overdue, nothing failed in the last seven days")

    print("\nAhead")
    try:
        rows = renewals(root, key, today)
    except Exception as problem:
        print("  Stripe could not be read (%s)" % problem)
        needs_person = True
        rows = []
    if not rows:
        print("  nothing renewing inside %d days" % RENEWAL_HORIZON_DAYS)
    for subject, due, days in rows:
        name = subject.get("name") or subject.get("id")
        note = " (raised by hand or not collected)" if subject.get(
            "collection") == "hand-raised" else ""
        print("  %s renews %s, %d day(s) out%s" % (name, due, days, note))
        if days <= RENEWAL_HORIZON_DAYS:
            needs_person = True

    return needs_person


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    root = repo_root()
    if root is None:
        print("no intelligence checkout found; set INTELLIGENCE_REPO",
              file=sys.stderr)
        return 2
    if verb == "ledger":
        print(json.dumps(read_ledger(root), indent=2))
        return 0
    if verb not in ("report", "check"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    key = os.environ.get("STRIPE_API_KEY") or ""
    needs_person = report(root, key)
    if verb == "check":
        return 1 if needs_person or not key else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
