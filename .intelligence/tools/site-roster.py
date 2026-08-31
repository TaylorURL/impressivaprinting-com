#!/usr/bin/env python3
"""The address roster: which people belong to which site, by name rather than by domain.

A site grants access two ways. The domain rule covers a company whose staff use
company mail, and it covers nobody else: the operator of a go-kart track reads
mail at gmail, and a scale company whose site is ccscaleservices.com sends from
ccscaleservicesinc.com. Both were locked out of their own figures, and both had
to ask for access by hand.

So the site itself is the source. Every address printed on a site belongs to
somebody who works there, and this crawls all of them, keeps the result in the
intelligence mirror, and seeds the table the signup trigger reads.

The roster is data, not a cache. A crawl adds what it finds and never removes an
address on its own, because a site that drops a contact page has not fired the
person. Removal is `forget`, which is a decision somebody makes.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROSTER = Path(
    os.environ.get("INTELLIGENCE_SITE_ROSTER", "")
    or Path.home() / ".intelligence" / "site-rosters" / "taylorurl.json"
)
# A roster older than this describes a set of sites that has moved on.
MAX_AGE_DAYS = 14
PAGE_BUDGET = 26

EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
HREF = re.compile(r'href=["\']([^"\']+)["\']', re.I)

# Addresses belonging to the tooling a page is built with rather than to the
# business, and the placeholders a form prints inside its own empty field.
NOISE = re.compile(
    r"@(example|sentry|wordpress|squarespace|wix|godaddy|shopify|schema|w3|sentry\.io)\."
    r"|\.(png|jpe?g|gif|svg|webp|css|js|woff2?|ico)$"
    r"|^[a-f0-9]{16,}@"
    r"|^(you|your|name|email|user|username|firstname|someone|somebody|test|noreply|no-reply|"
    r"donotreply|do-not-reply|placeholder|sample|yourname|youremail)@"
    r"|@(yourbusiness|yourcompany|yourdomain|domain|company|business|website|email)\.",
    re.I,
)
# Pages an address is printed on, tried before anything is followed.
SEEDS = ("", "/contact", "/contact-us", "/about", "/about-us", "/team", "/staff",
         "/support", "/connect", "/get-in-touch")
FOLLOW = ("contact", "about", "team", "staff", "connect", "support", "reach", "touch")

# Common obfuscations, unwrapped before the address pattern runs.
DEOBFUSCATE = [
    (re.compile(r"\s*[\[\(<{]\s*(?:at|@)\s*[\]\)>}]\s*", re.I), "@"),
    (re.compile(r"\s*[\[\(<{]\s*(?:dot|\.)\s*[\]\)>}]\s*", re.I), "."),
    (re.compile(r"\s+(?:at)\s+(?=[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", re.I), "@"),
]

NOW = lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ------------------------------------------------------------------ the file


def load():
    if not ROSTER.is_file():
        return {"project": "taylorurl", "supabase_project": "", "last_crawl": None,
                "ignored": [], "sites": {}}
    return json.loads(ROSTER.read_text())


def save(roster):
    ROSTER.parent.mkdir(parents=True, exist_ok=True)
    ROSTER.write_text(json.dumps(roster, indent=2, sort_keys=False) + "\n")


def entries(roster):
    """Every (email, site name, site id) the roster grants, ignores removed."""
    ignored = {a.lower() for a in roster.get("ignored", [])}
    out = []
    for name, site in sorted(roster["sites"].items()):
        for row in site.get("addresses", []):
            if row["email"].lower() not in ignored:
                out.append((row["email"].lower(), name, site["site_id"]))
    return out


# ------------------------------------------------------------------ the crawl


def fetch(url):
    try:
        done = subprocess.run(
            ["curl", "-sL", "--max-time", "25", "-A",
             "Mozilla/5.0 (compatible; taylorurl-roster/1.0)", url],
            capture_output=True, text=True, errors="replace", timeout=40)
        return done.stdout or ""
    except Exception:
        return ""


def addresses_in(html):
    text = html
    for pattern, into in DEOBFUSCATE:
        text = pattern.sub(into, text)
    found = set()
    for hit in EMAIL.findall(text):
        address = hit.strip(".").lower()
        if not NOISE.search(address):
            found.add(address)
    return found


def same_site_links(html, base, host):
    out = []
    for href in HREF.findall(html):
        if href.startswith(("mailto:", "tel:", "#", "javascript:", "data:")):
            continue
        url = urljoin(base, href).split("#")[0]
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https") and parsed.netloc.replace("www.", "") == host:
            out.append(url)
    return out


def crawl_site(site):
    """Every address printed anywhere on one site, with the page it was read from."""
    origin = site["origin"].rstrip("/")
    host = urlparse(origin).netloc.replace("www.", "")
    seen, hits, queue = set(), {}, [origin + path for path in SEEDS]

    while queue and len(seen) < PAGE_BUDGET:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        html = fetch(url)
        if not html:
            continue
        for address in addresses_in(html):
            hits.setdefault(address, url)
        for link in same_site_links(html, url, host):
            low = link.lower()
            if link not in seen and any(word in low for word in FOLLOW):
                queue.append(link)

    return {"origin": origin, "pages_read": len(seen), "found": hits}


def crawl(roster, only=None):
    targets = [dict(site, name=name) for name, site in roster["sites"].items()
               if not only or name in only]
    if not targets:
        print("site-roster: no sites in %s" % ROSTER, file=sys.stderr)
        return 1

    with ThreadPoolExecutor(max_workers=7) as pool:
        results = list(pool.map(crawl_site, targets))

    added, ignored = 0, {a.lower() for a in roster.get("ignored", [])}
    for site, result in zip(targets, results):
        held = roster["sites"][site["name"]]
        known = {row["email"].lower() for row in held.get("addresses", [])}
        fresh = []
        for address, page in sorted(result["found"].items()):
            if address in known or address in ignored:
                continue
            fresh.append({"email": address, "found_on": page, "first_seen": NOW()})
        held.setdefault("addresses", []).extend(fresh)
        held["addresses"].sort(key=lambda row: row["email"])
        held["pages_read"] = result["pages_read"]
        added += len(fresh)
        mark = "  +%d" % len(fresh) if fresh else "     "
        print("%s %-32s %2d pages, %d address(es)"
              % (mark, site["name"], result["pages_read"], len(held["addresses"])))
        for row in fresh:
            print("        new: %s" % row["email"])

    roster["last_crawl"] = NOW()
    save(roster)
    print("\n%d address(es) added; roster holds %d across %d site(s)"
          % (added, len(entries(roster)), len(roster["sites"])))
    return 0


# ------------------------------------------------------------------ the database


def sql_for(roster):
    """The upsert that makes the table match the roster, removals included."""
    rows = entries(roster)
    if not rows:
        return "-- roster is empty\n"
    values = ",\n    ".join(
        "('%s'::uuid, %s)" % (site_id, quote(email)) for email, _, site_id in rows)
    return (
        "insert into public.site_member_addresses (site_id, email)\nvalues\n    "
        + values
        + "\non conflict (site_id, email) do nothing;\n\n"
        "delete from public.site_member_addresses d\nwhere not exists (\n"
        "    select 1 from (values\n    " + values + "\n    ) as r(site_id, email)\n"
        "    where r.site_id = d.site_id and r.email = d.email\n);\n"
    )


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def rest(roster, path, method="GET", body=None):
    """One call against the project's REST endpoint, or None with no key to make it."""
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    ref = roster.get("supabase_project", "")
    if not key or not ref:
        return None
    cmd = ["curl", "-sS", "--max-time", "30", "-X", method,
           "https://%s.supabase.co/rest/v1/%s" % (ref, path),
           "-H", "apikey: %s" % key, "-H", "Authorization: Bearer %s" % key,
           "-H", "Content-Type: application/json",
           "-H", "Prefer: resolution=merge-duplicates,return=representation"]
    if body is not None:
        cmd += ["-d", json.dumps(body)]
    done = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(done.stdout or "null")
    except json.JSONDecodeError:
        return None


def sync(roster):
    rows = entries(roster)
    payload = [{"site_id": site_id, "email": email} for email, _, site_id in rows]
    got = rest(roster, "site_member_addresses", "POST", payload)
    if got is None:
        print("no SUPABASE_SERVICE_ROLE_KEY in the environment; the statement to apply is:\n")
        print(sql_for(roster))
        return 2
    print("wrote %d address(es) to site_member_addresses" % len(payload))
    return 0


def db_missing(roster):
    """Roster rows the table does not carry, or None when it cannot be read."""
    got = rest(roster, "site_member_addresses?select=site_id,email")
    if got is None or not isinstance(got, list):
        return None
    live = {(r["site_id"], r["email"].lower()) for r in got}
    return [(email, name) for email, name, site_id in entries(roster)
            if (site_id, email) not in live]


# ------------------------------------------------------------------ the gate


def check(roster, offline=False):
    """Non-zero whenever the roster is stale, incomplete, or not in the database."""
    faults = []

    stamp = roster.get("last_crawl")
    if not stamp:
        faults.append("never crawled")
    else:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(stamp)
        if age > timedelta(days=MAX_AGE_DAYS):
            faults.append("last crawled %d days ago, over the %d-day limit"
                          % (age.days, MAX_AGE_DAYS))

    if not offline:
        # A crawl now is the only thing that answers whether the roster is
        # complete: an address added to a site last week is invisible to a file.
        targets = [dict(site, name=name) for name, site in roster["sites"].items()]
        with ThreadPoolExecutor(max_workers=7) as pool:
            results = list(pool.map(crawl_site, targets))
        ignored = {a.lower() for a in roster.get("ignored", [])}
        unrostered = []
        for site, result in zip(targets, results):
            known = {row["email"].lower()
                     for row in roster["sites"][site["name"]].get("addresses", [])}
            for address in sorted(result["found"]):
                if address not in known and address not in ignored:
                    unrostered.append("%s on %s" % (address, site["name"]))
        if unrostered:
            faults.append("%d address(es) on a site and not in the roster: %s"
                          % (len(unrostered), ", ".join(unrostered[:6])))

        missing = db_missing(roster)
        if missing is None:
            faults.append("site_member_addresses could not be read, so the database "
                          "half of this gate is unanswered")
        elif missing:
            faults.append("%d rostered address(es) missing from site_member_addresses: %s"
                          % (len(missing), ", ".join("%s -> %s" % m for m in missing[:6])))

    if faults:
        for fault in faults:
            print("FAIL: %s" % fault)
        print("\nfix: site-roster.py crawl && site-roster.py sync")
        return 1

    print("roster current: %d address(es) across %d site(s), crawled %s, all in the database"
          % (len(entries(roster)), len(roster["sites"]), roster["last_crawl"]))
    return 0


# ------------------------------------------------------------------ the rest


def show(roster):
    for email, name, _ in entries(roster):
        print("%-44s %s" % (email, name))
    print("\n%d address(es) across %d site(s); last crawl %s"
          % (len(entries(roster)), len(roster["sites"]), roster.get("last_crawl") or "never"))
    if roster.get("ignored"):
        print("ignored: %s" % ", ".join(sorted(roster["ignored"])))
    return 0


def add(roster, email, site_name, note=None):
    email = email.strip().lower()
    if site_name not in roster["sites"]:
        print("site-roster: no site named %s; known: %s"
              % (site_name, ", ".join(sorted(roster["sites"]))), file=sys.stderr)
        return 1
    held = roster["sites"][site_name].setdefault("addresses", [])
    if any(row["email"].lower() == email for row in held):
        print("%s already rosters to %s" % (email, site_name))
        return 0
    held.append({"email": email, "found_on": note or "added by hand", "first_seen": NOW()})
    held.sort(key=lambda row: row["email"])
    save(roster)
    print("%s -> %s" % (email, site_name))
    return 0


def forget(roster, email):
    email = email.strip().lower()
    gone = 0
    for site in roster["sites"].values():
        before = len(site.get("addresses", []))
        site["addresses"] = [r for r in site.get("addresses", [])
                             if r["email"].lower() != email]
        gone += before - len(site["addresses"])
    if email not in [a.lower() for a in roster.get("ignored", [])]:
        roster.setdefault("ignored", []).append(email)
        roster["ignored"].sort()
    save(roster)
    print("removed %d entr(ies) for %s, and it will not be rostered again" % (gone, email))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    one = sub.add_parser("crawl", help="re-read every site and add what is new")
    one.add_argument("--site", action="append", help="limit to this site, repeatable")
    gate = sub.add_parser("check", help="non-zero when the roster is stale or unsynced")
    gate.add_argument("--offline", action="store_true",
                      help="age only; skip the crawl and the database read")
    sub.add_parser("sync", help="write the roster into site_member_addresses")
    sub.add_parser("sql", help="print the statement that syncs it")
    sub.add_parser("list", help="print the roster")
    plus = sub.add_parser("add", help="roster one address by hand")
    plus.add_argument("email")
    plus.add_argument("site")
    plus.add_argument("--note")
    minus = sub.add_parser("forget", help="remove an address and never roster it again")
    minus.add_argument("email")
    args = parser.parse_args()

    roster = load()
    if args.verb == "crawl":
        return crawl(roster, args.site)
    if args.verb == "check":
        return check(roster, args.offline)
    if args.verb == "sync":
        return sync(roster)
    if args.verb == "sql":
        print(sql_for(roster))
        return 0
    if args.verb == "list":
        return show(roster)
    if args.verb == "add":
        return add(roster, args.email, args.site, args.note)
    if args.verb == "forget":
        return forget(roster, args.email)
    return 1


if __name__ == "__main__":
    sys.exit(main())
