#!/usr/bin/env python3
"""Cases the address roster has to get right.

Three of them decide whether a client reaches their own figures. The noise
filter has to drop the placeholder a contact form prints inside its own empty
field while keeping a real address on a free mail host, because the free-host
address is the whole reason the roster exists. A crawl has to add without
removing, since a site that drops a contact page has not fired the person. And
`check` has to fail on a stale roster rather than reporting a set of sites it
last read a month ago.

  site-roster-cases.py        run them
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "site-roster.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load(roster_path=None):
    if roster_path:
        os.environ["INTELLIGENCE_SITE_ROSTER"] = str(roster_path)
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def roster(last_crawl, addresses):
    return {
        "project": "test",
        "supabase_project": "",
        "last_crawl": last_crawl,
        "ignored": [],
        "sites": {
            "example.com": {
                "site_id": "11111111-1111-1111-1111-111111111111",
                "origin": "https://example.com",
                "addresses": [{"email": a, "found_on": "https://example.com",
                               "first_seen": "2026-01-01T00:00:00+00:00"} for a in addresses],
            }
        },
    }


def main():
    mod = load()

    # A real address on a free mail host is the case the domain rule cannot
    # see, so it must survive the filter that drops form placeholders.
    keep = [
        "speedsway146@gmail.com",
        "sales@ccscaleservicesinc.com",
        "hanksclayton81@gmail.com",
        "hello@impressivaprinting.com",
    ]
    drop = [
        "you@yourbusiness.com",
        "name@example.com",
        "your@yourcompany.com",
        "noreply@example.com",
        "email@domain.com",
        "logo@sprite.png",
    ]
    for address in keep:
        check(f"keeps {address}", bool(mod.NOISE.search(address)), False)
    for address in drop:
        check(f"drops {address}", bool(mod.NOISE.search(address)), True)

    # An address written to dodge a scraper is still an address. The domain here
    # is a real one rather than example.com, which the filter drops on purpose.
    html = "Write to sales [at] baytowngokarts [dot] com or hi(at)smyrnatools(dot)com"
    found = mod.addresses_in(html)
    check("unwraps [at] and [dot]", "sales@baytowngokarts.com" in found, True)
    check("unwraps (at) and (dot)", "hi@smyrnatools.com" in found, True)

    # The roster grants what it holds, minus anything retired.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "r.json"
        data = roster("2026-08-01T00:00:00+00:00", ["a@gmail.com", "b@gmail.com"])
        path.write_text(json.dumps(data))
        mod = load(path)
        held = mod.load()
        check("both addresses grant", len(mod.entries(held)), 2)

        held["ignored"] = ["a@gmail.com"]
        check("a retired address grants nothing", len(mod.entries(held)), 1)
        check("the survivor is the other one", mod.entries(held)[0][0], "b@gmail.com")

    # A stale roster describes a set of sites that has moved on, so the gate
    # fails on age alone without reaching the network.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "r.json"
        old = (datetime.now(timezone.utc) - timedelta(days=mod.MAX_AGE_DAYS + 1)).isoformat()
        path.write_text(json.dumps(roster(old, ["a@gmail.com"])))
        mod = load(path)
        check("a stale roster fails", mod.check(mod.load(), offline=True), 1)

        fresh = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(roster(fresh, ["a@gmail.com"])))
        check("a fresh roster passes", mod.check(mod.load(), offline=True), 0)

        path.write_text(json.dumps(roster(None, ["a@gmail.com"])))
        check("a roster never crawled fails", mod.check(mod.load(), offline=True), 1)

    # The sync statement carries every held address and removes what the roster
    # no longer holds, so a retirement reaches the table rather than only the file.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "r.json"
        path.write_text(json.dumps(roster("2026-08-26T00:00:00+00:00", ["a@gmail.com"])))
        mod = load(path)
        sql = mod.sql_for(mod.load())
        check("insert carries the address", "'a@gmail.com'" in sql, True)
        check("sync removes what is gone", "delete from public.site_member_addresses" in sql, True)
        check("an address with a quote is escaped",
              "''" in mod.quote("o'brien@example.com"), True)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
