#!/usr/bin/env python3
"""The cases the Google gate tool answers to.

The tool named in INTELLIGENCE_TEST_TARGET is the local shim; the engine it runs
sits inside the skill, and that is what these load. Nothing here touches the
network or a real Google account, so a case set that passes on one machine
passes on every machine.
"""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        return
    FAILURES.append("%s%s" % (name, (" - " + detail) if detail else ""))


def load_engine():
    target = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
                  or Path.home() / ".intelligence/tools/google-pass.py")
    candidates = [
        Path.home() / ".intelligence/checklists/google/bin/google-pass.py",
        target.resolve().parent.parent / "checklists/google/bin/google-pass.py",
    ]
    for path in candidates:
        if path.is_file():
            spec = importlib.util.spec_from_file_location("google_pass_engine", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    return None


def run_of(engine, sites, **extra):
    run = {"id": "cases", "opened": "now", "session": "cases", "title": "cases",
           "registry": "", "sites": sites, "known": [], "scope": None,
           "results": {}, "probe": {}, "delegated": [], "order": []}
    run.update(extra)
    return run


def every_gate_is_answerable(engine):
    groups = engine.load_gates()
    gates = engine.all_gates(groups)
    check("gates load", len(gates) > 50, "only %d gates found" % len(gates))
    unknown = sorted({g["check"]["type"] for g in gates} - set(engine.CHECKS))
    check("every check type is dispatched", not unknown, "no checker for %s" % unknown)
    ids = [g["id"] for g in gates]
    check("gate ids are unique", len(ids) == len(set(ids)),
          "duplicates: %s" % sorted({i for i in ids if ids.count(i) > 1}))
    for gate in gates:
        check("%s has a rule" % gate["id"], len(gate.get("rule", "")) > 40)
        check("%s has a fix" % gate["id"], bool(gate.get("fix")))
        check("%s declares a known context" % gate["id"],
              all(w in engine.CONTEXT_KEYS for w in
                  (gate["when"] if isinstance(gate["when"], list) else [gate["when"]])),
              "unknown when: %r" % gate["when"])
        check("%s declares a known kind" % gate["id"],
              all(k == "*" or k in engine.KINDS for k in gate["kinds"]),
              "unknown kind in %r" % gate["kinds"])
    named = {g["check"].get("probe") for g in gates if g["check"]["type"] == "probe"}
    check("every probe gate names a probe", all(named), "a probe gate has no probe name")
    process = [g for g in gates if g["check"]["type"] in engine.SELF_SETTLING]
    check("the run protocol is present", len(process) >= 4,
          "only %d self-settling gates" % len(process))


def a_probe_gate_refuses_a_hand_answer(engine):
    groups = engine.load_gates()
    index = engine.gate_index(groups)
    gates = engine.all_gates(groups)
    probe_gate = next(g for g in gates if g["check"]["type"] == "probe")
    self_gate = next(g for g in gates if g["check"]["type"] in engine.SELF_SETTLING)
    site = "example.com"
    item = engine.key(site, probe_gate["id"])
    own = engine.key(site, self_gate["id"])
    run = run_of(engine, {site: {"domain": site, "kind": "local-business", "flags": []}},
                 results={item: {"status": "open", "auto": ""},
                          own: {"status": "open", "auto": ""}},
                 order=[item, own])
    note = "read the Business Profile dashboard at 14:02 and the listing is verified"
    faults = engine._validate_answer(item, "pass", note, run, index, {})
    check("a probe gate refuses pass", any("reading" in f for f in faults), str(faults))
    faults = engine._validate_answer(item, "na", note, run, index, {})
    check("a probe gate refuses na", any("reading" in f for f in faults), str(faults))
    faults = engine._validate_answer(item, "fixed", note, run, index, {})
    check("a probe gate accepts fixed", not faults, str(faults))
    faults = engine._validate_answer(own, "pass", note, run, index, {})
    check("a bookkeeping gate refuses an attestation",
          any("run's own state" in f for f in faults), str(faults))


def blocked_and_disputed_take_a_reason(engine):
    groups = engine.load_gates()
    index = engine.gate_index(groups)
    gate = next(g for g in engine.all_gates(groups) if g["check"]["type"] == "probe")
    site = "example.com"
    item = engine.key(site, gate["id"])
    run = run_of(engine, {site: {"domain": site, "kind": "local-business", "flags": []}},
                 results={item: {"status": "open", "auto": "fail: nobody claimed the listing"}},
                 order=[item])
    faults = engine._validate_answer(item, "blocked", "waiting", run, index, {})
    check("blocked refuses a bare note", any("waiting on" in f for f in faults), str(faults))
    long = "the verification postcard was requested on the 28th and Google says fourteen days"
    faults = engine._validate_answer(item, "blocked", long, run, index, {})
    check("blocked accepts a reason", not faults, str(faults))
    faults = engine._validate_answer(item, "disputed", "wrong", run, index, {})
    check("disputed refuses a bare note", any("measurement" in f for f in faults), str(faults))
    faults = engine._validate_answer(item, "unknowable", long, run, index, {})
    check("an invented status is refused", any("status must be" in f for f in faults),
          str(faults))


def a_reading_that_failed_blocks_pass(engine):
    groups = engine.load_gates()
    index = engine.gate_index(groups)
    gate = next(g for g in engine.all_gates(groups) if g["check"]["type"] == "attest")
    site = "example.com"
    item = engine.key(site, gate["id"])
    run = run_of(engine, {site: {"domain": site, "kind": "local-business", "flags": []}},
                 results={item: {"status": "open", "auto": "fail: a manual action is open"}},
                 order=[item])
    note = "signed in to Search Console on the 28th and the manual actions page was empty"
    faults = engine._validate_answer(item, "pass", note, run, index, {})
    check("a failing reading refuses pass", any("cannot be answered as passing" in f
                                                for f in faults), str(faults))
    faults = engine._validate_answer(item, "na", note, run, index, {})
    check("a failing reading refuses na", any("present and unmet" in f for f in faults),
          str(faults))


def an_attestation_takes_what_was_seen(engine):
    groups = engine.load_gates()
    index = engine.gate_index(groups)
    gate = next(g for g in engine.all_gates(groups) if g["check"]["type"] == "attest")
    site = "example.com"
    item = engine.key(site, gate["id"])
    run = run_of(engine, {site: {"domain": site, "kind": "local-business", "flags": []}},
                 results={item: {"status": "open", "auto": ""}}, order=[item])
    faults = engine._validate_answer(item, "pass", "looks fine", run, index, {})
    check("an attestation refuses a bare note", any("what was seen" in f for f in faults),
          str(faults))


def context_decides_what_applies(engine):
    groups = engine.load_gates()
    gates = engine.all_gates(groups)
    local_gate = next(g for g in gates if g["when"] == "local")
    run = run_of(engine, {})
    product = {"domain": "domebreak.com", "kind": "product", "flags": []}
    shop = {"domain": "faded-barbershop.com", "kind": "local-business", "flags": []}
    ok, _ = engine.applicable(local_gate, product, run, engine.context_for(product))
    check("a local gate skips a product", not ok, local_gate["id"])
    ok, _ = engine.applicable(local_gate, shop, run, engine.context_for(shop))
    check("a local gate applies to a local business", ok, local_gate["id"])
    declared = {"domain": "shop.example", "kind": "local-business", "flags": ["storefront"]}
    ctx = engine.context_for(declared)
    check("a declared flag reaches the context", ctx["storefront"] is True)
    check("an undeclared flag stays false", engine.context_for(shop)["storefront"] is False)


def the_portfolio_is_the_registry(engine):
    body = (
        "export const PORTFOLIO_PROJECTS = [\n"
        "  { name: 'Smyrna Tools', slug: 'smyrna', kind: 'client',\n"
        "    url: 'https://smyrnatools.com', displayUrl: 'smyrnatools.com', town: '' },\n"
        "  { name: 'DomeBreak', slug: 'dome', kind: 'product',\n"
        "    url: 'https://domebreak.com', displayUrl: 'domebreak.com', town: '' },\n"
        "]\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        registry = root / "src" / "app" / "data"
        registry.mkdir(parents=True)
        (registry / "portfolio.js").write_text(body)
        scripts = root / "scripts"
        scripts.mkdir()
        (scripts / "portfolio-sites.json").write_text(
            json.dumps({"excluded": [{"domain": "charliets.com", "reason": "retired"}]}))
        rows = engine.load_registry(root)
        domains = [r["domain"] for r in rows]
        check("the registry reads the portfolio", "smyrnatools.com" in domains, str(domains))
        check("the site the portfolio omits is added back", "taylorurl.com" in domains,
              str(domains))
        check("an excluded domain stays out", "charliets.com" not in domains, str(domains))
        text_rows = engine._registry_via_text(registry / "portfolio.js")
        check("the reader without node finds the same sites", len(text_rows) >= 2,
              str(text_rows))


def a_client_is_a_local_business(engine):
    check("a client is a local business",
          engine.site_kind({"domain": "x.com", "kind": "client", "town": ""}, {}),
          "local-business")
    check("a client with no town is still local",
          engine.site_kind({"domain": "x.com", "kind": "client", "town": ""}, {})
          == "local-business")
    check("a product is a product",
          engine.site_kind({"domain": "x.com", "kind": "product", "town": ""}, {}) == "product")
    check("the overlay outranks the portfolio",
          engine.site_kind({"domain": "x.com", "kind": "client", "town": "Baytown"},
                           {"x.com": {"kind": "ecommerce"}}) == "ecommerce")


def the_owner_splits_the_work(engine):
    groups = engine.load_gates()
    gates = engine.all_gates(groups)
    owners = {engine.gate_owner(g) for g in gates}
    check("both owners appear", owners == {"human", "agent"}, str(owners))
    claim = {"id": "T-01", "check": {"type": "probe"},
             "fix": "Claim the listing in the Business Profile dashboard."}
    check("a dashboard fix waits on a person", engine.gate_owner(claim) == "human")
    fetch = {"id": "T-02", "check": {"type": "probe"},
             "fix": "Add the canonical link to the document head and redeploy."}
    check("a code fix goes to an agent", engine.gate_owner(fetch) == "agent")
    stated = {"id": "T-03", "check": {"type": "probe"}, "owner": "agent",
              "fix": "Claim the listing in the dashboard."}
    check("an explicit owner outranks the guess", engine.gate_owner(stated) == "agent")


def coverage_holds_the_run_open(engine):
    groups = engine.load_gates()
    index = engine.gate_index(groups)
    run = run_of(engine, {"a.com": {"domain": "a.com", "kind": "site", "flags": []}},
                 known=[{"domain": "a.com"}, {"domain": "b.com"}])
    ok, note = engine._settled("site_coverage", run, index)
    check("a site outside the run fails coverage", not ok, note)
    check("coverage names the missing site", "b.com" in note, note)
    run["sites"]["b.com"] = {"domain": "b.com", "kind": "site", "flags": []}
    ok, note = engine._settled("site_coverage", run, index)
    check("coverage passes once every site is in", ok, note)
    ok, note = engine._settled("delegation", run, index)
    check("delegation holds the run open", not ok, note)
    run["nothing_delegated"] = True
    ok, note = engine._settled("delegation", run, index)
    check("recording nothing came up settles delegation", ok, note)


def a_probe_answers_per_site(engine):
    groups = engine.load_gates()
    gate = next(g for g in engine.all_gates(groups) if g["check"]["type"] == "probe")
    name = gate["check"]["probe"]
    site = {"domain": "a.com", "kind": "local-business", "flags": []}
    run = run_of(engine, {"a.com": site},
                 probe={engine.key("b.com", name): {"ok": True, "detail": "fine", "at": "now"}})
    status, detail = engine.check_probe(gate, site, run, {})
    check("another site's reading does not answer this one", status == engine.UNKNOWN, detail)
    run["probe"][engine.key("a.com", name)] = {"ok": False, "detail": "not set up", "at": "now"}
    status, detail = engine.check_probe(gate, site, run, {})
    check("a failing reading fails the gate", status == engine.FAIL, detail)
    run["probe"][engine.key("a.com", name)] = {"ok": True, "detail": "set up", "at": "now"}
    status, detail = engine.check_probe(gate, site, run, {})
    check("a passing reading passes the gate", status == engine.PASS, detail)


def main():
    engine = load_engine()
    if engine is None:
        print("google-pass: the skill is not installed, so its engine could not be loaded")
        return 1
    every_gate_is_answerable(engine)
    a_probe_gate_refuses_a_hand_answer(engine)
    blocked_and_disputed_take_a_reason(engine)
    a_reading_that_failed_blocks_pass(engine)
    an_attestation_takes_what_was_seen(engine)
    context_decides_what_applies(engine)
    the_portfolio_is_the_registry(engine)
    a_client_is_a_local_business(engine)
    the_owner_splits_the_work(engine)
    coverage_holds_the_run_open(engine)
    a_probe_answers_per_site(engine)

    for row in FAILURES:
        print("FAIL %s" % row)
    print("%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
