#!/usr/bin/env python3
"""Cases the liveness tool has to get right.

The one thing this tool must never do is report a site as live on a reading it
could not take. So the cases that matter are the ones separating three states a
report could otherwise blur into one: a site that answered and was right, a site
that answered and was wrong, and a site that did not answer at all. The third is
Unprobed, it fails the run, and it carries its reason.

The rest hold resolution, which is where this tool would go wrong quietly. No
part of a site here follows from its directory name, so a case fixes a portfolio
naming one host and a project attached to another, and the reading is checked
against the portfolio rather than the directory.

Every fixture is a temporary directory and the network is stood in for
throughout, so no case can be answered by a host that happens to be up wherever
this runs.

  site-live-cases.py     run them
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "site-live.py")

FAILURES = []

PORTFOLIO_FIXTURE = """
export const PORTFOLIO_PROJECTS = [
  {
    name: 'Delux Financial Solutions',
    slug: 'delux',
    kind: 'client',
    url: 'https://deluxlavello.com',
    displayUrl: 'deluxlavello.com',
  },
  {
    name: 'SETX Football',
    slug: 'setx',
    kind: 'client',
    url: 'https://www.setxfootball.org',
    displayUrl: 'setxfootball.org',
  },
]
"""


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def load(state_dir, portfolio):
    os.environ["INTELLIGENCE_STATE_DIR"] = str(state_dir)
    os.environ["INTELLIGENCE_PORTFOLIO"] = str(portfolio)
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def site(mod, **over):
    """A resolved site with every field present, so a probe reads a whole one."""
    base = {"root": "", "repo": "TaylorURL/deluxlavello-com",
            "project": "deluxlavello-com", "scope": "team_x",
            "prod_branch": "main", "canonical": "deluxlavello.com",
            "hosts": ["deluxlavello.com", "www.deluxlavello.com"],
            "domains": [{"name": "deluxlavello.com", "redirect": None},
                        {"name": "www.deluxlavello.com", "redirect": None}],
            "display": "Delux Financial Solutions", "portfolio": None,
            "token": True, "credential": "ok"}
    base.update(over)
    return base


def answers(mod, table):
    """Stand in for every host, so a probe reads the table and never a network."""
    def head(url, follow=False):
        host = url.split("//", 1)[-1].split("/", 1)[0]
        if host not in table:
            raise mod.Unprobed("%s did not answer" % host)
        code, where = table[host]
        return code, where, None
    mod.head = head
    mod.resolves = lambda host: host in table



def repo_fixture(where):
    """An origin with develop and main on it, and a clone to run probes in.

    The landed stage reads refs rather than a network, so it is the one stage a
    case cannot stand in for. Building the real thing is cheap and it is what
    lets a squash merge be reproduced exactly: the content arrives on develop
    under a commit the branch has never seen.
    """
    def run_git(*args, cwd):
        subprocess.run(["git", *args], cwd=str(cwd), check=True,
                       capture_output=True, text=True)

    origin = where / "origin.git"
    origin.mkdir(parents=True)
    run_git("init", "--bare", "--initial-branch=main", ".", cwd=origin)

    clone = where / "clone"
    clone.mkdir()
    run_git("init", "--initial-branch=main", ".", cwd=clone)
    run_git("config", "user.email", "cases@example.invalid", cwd=clone)
    run_git("config", "user.name", "Cases", cwd=clone)
    run_git("remote", "add", "origin", str(origin), cwd=clone)
    (clone / "file.txt").write_text("one\n")
    run_git("add", "-A", cwd=clone)
    run_git("commit", "-m", "one", cwd=clone)
    run_git("push", "-u", "origin", "main", cwd=clone)
    run_git("checkout", "-b", "develop", cwd=clone)
    run_git("push", "-u", "origin", "develop", cwd=clone)
    return origin, clone, run_git


def main():
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state"
        portfolio = Path(tmp) / "portfolio.js"
        portfolio.write_text(PORTFOLIO_FIXTURE)
        mod = load(state, portfolio)

        # ---------------------------------------------------------- portfolio
        entries = mod.portfolio_entries()
        check("portfolio reads every entry", len(entries), 2)
        first = {e["host"]: e for e in entries}
        check("apex entry keeps its host",
              "deluxlavello.com" in first, True)
        check("a www entry keeps the www it names",
              first["www.setxfootball.org"]["display_url"], "setxfootball.org")
        check("the display name is carried",
              first["deluxlavello.com"]["name"], "Delux Financial Solutions")

        # ------------------------------------------------ the site's own tree
        # A repository in no portfolio, read with a credential that answers
        # nothing, has no address from either of the first two sources. The
        # studio's own site is exactly that: a portfolio of client work carries
        # no entry for the studio, so without this the whole pipeline is
        # published from the one site the tool cannot name.
        declared = Path(tmp) / "declared"
        (declared / "public").mkdir(parents=True)
        (declared / "public/robots.txt").write_text(
            "User-agent: *\nAllow: /\nSitemap: https://www.taylorurl.com/sitemap.xml\n")
        check("robots names the host the sitemap is served on",
              mod.declared_host(declared), "www.taylorurl.com")

        (declared / "index.html").write_text(
            '<link rel="canonical" href="https://canonical.example/" />')
        check("a canonical link outranks robots",
              mod.declared_host(declared), "canonical.example")

        (declared / "package.json").write_text('{"homepage": "https://homepage.example"}')
        check("homepage outranks the markup",
              mod.declared_host(declared), "homepage.example")

        (declared / ".env").write_text("VITE_SITE_URL=https://declared.example/\n")
        check("the site's own variable outranks them all",
              mod.declared_host(declared), "declared.example")

        check("a tree that states nothing states nothing",
              mod.declared_host(Path(tmp) / "empty"), "")
        check("and no root at all is not an error", mod.declared_host(""), "")

        mod.checkout_for = lambda target: declared
        mod.repo_of = lambda root: "TaylorURL/taylorurl-com"
        mod.vercel_token = lambda: None
        mod.token_state = lambda token: "missing"
        mod.project_for = lambda repo, token: None
        mod.project_domains = lambda project, token: []
        found = mod.resolve("")
        check("resolution falls through to what the site states",
              found["canonical"], "declared.example")
        check("and records that there was no credential",
              found["credential"], "missing")
        check("which is not the same as a working one", found["token"], False)

        # ------------------------------------------------- a dead credential
        # A store holding an expired token reads exactly like a scope holding no
        # projects. Reported as "no Vercel project builds this repository" it is
        # a definite claim about the site, made on no evidence and wrong.
        mod.vercel_token = lambda: "expired"
        mod.token_state = lambda token: "refused"
        found = mod.resolve("")
        check("a refused token is not a working one", found["token"], False)
        check("and the run says which it was", found["credential"], "refused")

        raised = ""
        try:
            mod.probe_host(site(mod, token=False, credential="refused"))
        except mod.Unprobed as err:
            raised = str(err)
        check("the host stage blames the credential, not the site",
              "refused" in raised, True)
        check("and never claims no project exists",
              "no Vercel project" in raised, False)

        # ------------------------------------------------- entry from the host
        # A repository spelled unlike its address is the case the stem match
        # cannot serve: deluxfinancial-com against deluxlavello.com shares no
        # stem, and reading the attached hosts is what still finds the entry.
        mod.checkout_for = lambda target: Path("/nowhere/deluxfinancial-com")
        mod.repo_of = lambda root: "TaylorURL/deluxfinancial-com"
        mod.vercel_token = lambda: "t"
        mod.token_state = lambda token: "ok"
        mod.project_for = lambda repo, token: {"name": "deluxfinancial-com",
                                               "_scope": "", "link": {}}
        mod.project_domains = lambda project, token: [
            {"name": "deluxlavello.com"}, {"name": "www.deluxlavello.com",
                                           "redirect": "deluxlavello.com"}]
        found = mod.resolve("")
        check("a host-spelled entry is still found",
              found["canonical"], "deluxlavello.com")
        check("and it brings its display name",
              found["display"], "Delux Financial Solutions")
        check("and the entry itself is carried",
              (found["portfolio"] or {}).get("host"), "deluxlavello.com")

        # ------------------------------------------------------------ address
        answers(mod, {"deluxlavello.com": (200, ""),
                      "www.deluxlavello.com": (200, "")})
        ok, detail = mod.probe_address(site(mod))
        check("two hosts each answering 200 is not one address", ok, False)
        check("it names the host that should have redirected",
              "www.deluxlavello.com" in detail, True)

        answers(mod, {"deluxlavello.com": (200, ""),
                      "www.deluxlavello.com": (308, "https://deluxlavello.com/")})
        ok, _ = mod.probe_address(site(mod))
        check("one canonical host with the other redirecting passes", ok, True)

        answers(mod, {"deluxlavello.com": (200, ""),
                      "www.deluxlavello.com": (308, "https://elsewhere.invalid/")})
        ok, detail = mod.probe_address(site(mod))
        check("a redirect to a third host fails", ok, False)

        answers(mod, {"www.deluxlavello.com": (200, "")})
        ok, detail = mod.probe_address(site(mod))
        check("a canonical host that does not resolve fails", ok, False)
        check("it says so plainly", "does not resolve" in detail, True)

        raised = ""
        try:
            mod.probe_address(site(mod, canonical=""))
        except mod.Unprobed as err:
            raised = str(err)
        check("no canonical host is unprobed rather than failing",
              "canonical" in raised, True)

        # ------------------------------------------------------------ serving
        # No page answers unless a case says it does, so the fallback onto the
        # host's record is what the cases below walk.
        def no_page(url, fresh=False):
            raise mod.Unprobed("%s did not answer" % url)
        mod.fetch = no_page
        mod.api = lambda *a, **k: {"deployments": [
            {"readyState": "READY", "meta": {"githubCommitSha": "a" * 40}}]}
        mod.vercel_token = lambda: "t"
        raised = ""
        try:
            mod.probe_serving(site(mod))
        except mod.Unprobed as err:
            raised = str(err)
        check("no checkout leaves the comparison unprobed rather than passing",
              "cannot be compared" in raised, True)

        # A deployment made from the command line carries no commit, and the
        # question is then unanswered rather than answered in the affirmative.
        mod.api = lambda *a, **k: {"deployments": [{"readyState": "READY"}]}
        raised = ""
        try:
            mod.probe_serving(site(mod))
        except mod.Unprobed as err:
            raised = str(err)
        check("a deployment carrying no commit is unprobed",
              "no commit" in raised, True)

        # The address visitors reach, not the newest build behind it.
        def by_path(path, *a, **k):
            if "/v9/projects/" in path and "/domains" not in path:
                return {"targets": {"production": {"id": "dpl_alias"}}}
            if "/v13/deployments/dpl_alias" in path:
                return {"readyState": "READY",
                        "meta": {"githubCommitSha": "c" * 40}}
            return {"deployments": [
                {"readyState": "READY", "meta": {"githubCommitSha": "f" * 40}}]}
        mod.api = by_path
        served = mod.production_deployment(site(mod))
        check("the aliased deployment is read, not the newest",
              (served.get("meta") or {}).get("githubCommitSha"), "c" * 40)

        mod.api = lambda *a, **k: {"deployments": [
            {"readyState": "ERROR", "meta": {"githubCommitSha": "a" * 40}}]}
        ok, detail = mod.probe_serving(site(mod))
        check("a failed production deployment fails", ok, False)

        mod.api = lambda *a, **k: {"deployments": []}
        raised = ""
        try:
            mod.probe_serving(site(mod))
        except mod.Unprobed as err:
            raised = str(err)
        check("no deployment at all is unprobed", "no production" in raised, True)

        raised = ""
        mod.api = lambda *a, **k: {"deployments": [{"readyState": "READY"}]}
        try:
            mod.probe_serving(site(mod, token=False, project=""))
        except mod.Unprobed as err:
            raised = str(err)
        check("no host project leaves serving unprobed", bool(raised), True)

        # ------------------------------------------------------------- landed
        # Every feature branch lands by squash, which writes develop a commit of
        # its own. The branch's commit is then never an ancestor of develop
        # however completely the work arrived, so counting commits calls a fully
        # landed branch unlanded for as long as the branch exists.
        origin, clone, run_git = repo_fixture(Path(tmp) / "landed")

        ok, detail = mod.probe_landed(site(mod, root=str(clone)))
        check("develop level with main and nothing local is landed", ok, True)

        run_git("checkout", "-b", "feature", cwd=clone)
        (clone / "file.txt").write_text("two\n")
        run_git("commit", "-am", "two", cwd=clone)
        ok, detail = mod.probe_landed(site(mod, root=str(clone)))
        check("a branch develop has not got is waiting", ok, False)
        check("and it says how much", "ahead of develop" in detail, True)

        # The squash: the same content reaches develop under another commit.
        run_git("checkout", "develop", cwd=clone)
        (clone / "file.txt").write_text("two\n")
        run_git("commit", "-am", "two, squashed", cwd=clone)
        run_git("push", "origin", "develop", cwd=clone)
        run_git("checkout", "feature", cwd=clone)
        ok, detail = mod.probe_landed(site(mod, root=str(clone)))
        check("the squashed work is on develop, not waiting on the branch",
              "ahead of develop" in detail, False)
        check("what is left is develop waiting on main",
              "not promoted" in detail, True)

        # The promotion leaves main one merge commit ahead of develop, which is
        # the end state the ship path mandates and not a reading against it. The
        # branch is still checked out and still holds its pre-squash commit.
        run_git("checkout", "main", cwd=clone)
        run_git("merge", "--no-ff", "-m", "promote", "develop", cwd=clone)
        run_git("push", "origin", "main", cwd=clone)
        run_git("checkout", "feature", cwd=clone)
        ok, detail = mod.probe_landed(site(mod, root=str(clone)))
        check("a squash-merged branch after promotion has landed", ok, True)
        check("and the merge commit on main is not counted against it",
              detail, "develop and main level, tree clean")

        # Content develop really has not got still counts, squash or no squash.
        run_git("checkout", "feature", cwd=clone)
        (clone / "file.txt").write_text("three\n")
        run_git("commit", "-am", "three", cwd=clone)
        ok, detail = mod.probe_landed(site(mod, root=str(clone)))
        check("real unlanded content is still waiting", ok, False)

        (clone / "file.txt").write_text("four\n")
        ok, detail = mod.probe_landed(site(mod, root=str(clone)))
        check("an uncommitted file is waiting too", ok, False)
        check("and is named as one", "uncommitted" in detail, True)

        # ------------------------------------------------------------ watched
        check("the reporter matches the endpoint it posts to",
              bool(mod.REPORTER.search(
                  "fetch('https://sunday.tail1f78d7.ts.net/report',{")), True)
        check("the reporter is not matched by the word alone",
              bool(mod.REPORTER.search("<p>report an issue</p>")), False)

        mod.fetch = lambda url: (
            '{"sites":[{"name":"Delux Financial Solutions"}]}'
            if "status-feed" in url else "<html><head></head></html>")
        ok, detail = mod.probe_watched(site(mod))
        check("a page with no snippet is not watched", ok, False)
        check("it names the snippet", "snippet" in detail, True)

        check("a snippet that swallows is recognised by the flag it reads",
              bool(mod.SUPPRESSING.search("localStorage.getItem('reporter-console')")), True)
        check("and by the replay it hangs on the window",
              bool(mod.SUPPRESSING.search("window.__reporter={held:h}")), True)
        check("a snippet that only reports carries neither",
              bool(mod.SUPPRESSING.search(
                  "<script>u='https://sunday.tail1f78d7.ts.net/report'</script>")), False)

        served = ("<script>u='https://sunday.tail1f78d7.ts.net/report';"
                  "window.__reporter={}</script>")
        mod.fetch = lambda url: (
            '{"sites":[{"name":"Delux Financial Solutions"}]}'
            if "status-feed" in url else served)
        ok, _ = mod.probe_watched(site(mod))
        check("snippet served and named in the feed passes", ok, True)

        mod.fetch = lambda url: (
            '{"sites":[{"name":"Delux Financial Solutions"}]}'
            if "status-feed" in url
            else "<script>u='https://sunday.tail1f78d7.ts.net/report'</script>")
        ok, detail = mod.probe_watched(site(mod))
        check("a snippet that prints what it reports is not watched", ok, False)
        check("it names the console rather than the snippet being absent",
              "console" in detail and "no reporting snippet" not in detail, True)

        mod.fetch = lambda url: ('{"sites":[{"name":"Somebody Else"}]}'
                                 if "status-feed" in url else served)
        ok, detail = mod.probe_watched(site(mod))
        check("a site absent from the feed is not watched", ok, False)

        def refuse(url):
            raise mod.Unprobed("the feed did not answer")
        mod.fetch = refuse
        raised = ""
        try:
            mod.probe_watched(site(mod))
        except mod.Unprobed as err:
            raised = str(err)
        check("an unreadable feed is unprobed rather than passing",
              bool(raised), True)

        # The page is asked before the host's record of it, and answering needs
        # no credential: a machine whose Vercel login has expired can still
        # settle whether a release arrived.
        _, page_clone, page_git = repo_fixture(Path(tmp) / "serving")
        on_main = subprocess.run(["git", "rev-parse", "origin/main"], cwd=str(page_clone),
                                 capture_output=True, text=True).stdout.strip()

        def serves(sha):
            def page(url, fresh=False):
                if url.endswith("/api/version"):
                    return '{"build":"%s"}' % sha
                raise mod.Unprobed("%s did not answer" % url)
            return page

        mod.api = lambda *a, **k: {"deployments": []}
        mod.fetch = serves(on_main)
        ok, detail = mod.probe_serving(site(mod, root=str(page_clone)))
        check("the page carrying main's commit is serving it", ok, True)
        check("and the reading says where it came from",
              "read from the page" in detail, True)

        mod.fetch = serves("b" * 40)
        ok, detail = mod.probe_serving(site(mod, root=str(page_clone)))
        check("a page carrying another commit is not serving main", ok, False)

        # No endpoint and no credential leaves it unanswered, and the reason is
        # the credential rather than a claim about the site.
        mod.fetch = no_page
        raised = ""
        try:
            mod.probe_serving(site(mod, root=str(page_clone), token=False,
                                   project="", credential="refused"))
        except mod.Unprobed as err:
            raised = str(err)
        check("no page and no credential is unprobed", bool(raised), True)
        check("and the credential is what it names", "refused" in raised, True)

        # -------------------------------------------------------------- known
        answers(mod, {"deluxlavello.com": (200, ""),
                      "www.deluxlavello.com": (200, "")})
        entry = {"name": "Delux Financial Solutions", "url": "https://deluxlavello.com",
                 "host": "deluxlavello.com", "display_url": "deluxlavello.com"}

        ok, _ = mod.probe_known(site(mod, portfolio=entry))
        check("a site listed in the portfolio is known", ok, True)

        ok, detail = mod.probe_known(site(mod))
        check("a site missing from the portfolio is not known", ok, False)
        check("it says which gap it found", "no portfolio entry" in detail, True)

        ok, detail = mod.probe_known(site(mod, portfolio=dict(entry, host="elsewhere.invalid")))
        check("a portfolio naming a different host fails", ok, False)

        # The site carrying the portfolio has no entry in it and never will, so
        # it is held to the rest of the stage and not to that.
        carrier = site(mod, root=str(portfolio.parent), portfolio=None)
        ok, detail = mod.probe_known(carrier)
        check("the site that carries the portfolio needs no entry in it", ok, True)
        check("and says that is why", "carries the portfolio" in detail, True)

        # A worktree of the repository that carries the portfolio is a root the
        # configured path is not under, and it holds the same file at the same
        # place inside itself. The file the tree holds is what settles the
        # question, so the studio's own site reads the same from either tree.
        worktree = Path(tmp) / "worktree"
        held = worktree / "src/app/data/portfolio.js"
        held.parent.mkdir(parents=True)
        held.write_text(PORTFOLIO_FIXTURE)
        ok, detail = mod.probe_known(site(mod, root=str(worktree), portfolio=None))
        check("a worktree of the carrying repository carries it too", ok, True)
        check("and is not read as missing an entry",
              "no portfolio entry" in detail, False)

        answers(mod, {"deluxlavello.com": (404, "")})
        ok, detail = mod.probe_known(carrier)
        check("carrying the portfolio does not excuse a missing robots.txt", ok, False)

        # -------------------------------------------------------------- usage
        for verb, want in (("", 2), ("frobnicate", 2)):
            done = subprocess.run(
                [sys.executable, str(TARGET)] + ([verb] if verb else []),
                capture_output=True, text=True)
            check("usage rejects %r" % verb, done.returncode, want)

        done = subprocess.run([sys.executable, str(TARGET), "canonical"],
                              capture_output=True, text=True)
        check("canonical without --set is a usage error", done.returncode, 2)

    for failure in FAILURES:
        print("FAIL %s" % failure)
    print("%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
