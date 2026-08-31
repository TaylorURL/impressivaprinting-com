#!/usr/bin/env python3
"""Whether a site is reachable at its own address, and what is standing between it and that.

A promotion into `main` finishes green whether or not anything reached a
visitor. GitHub answers for the merge and nothing answers for the rest: the host
may build a different repository, the domain may point nowhere, the build
webhook may have been missed, and the monitor may never have been told the site
exists. Each of those leaves a release that reports as shipped and serves the
previous week, or a site that is live and unwatched, which reads exactly like a
site that is live and quiet.

Nothing about a site follows from its directory name. `ccscaleservicesinc-com`
serves ccscaleservices.com, the checkout called `baytowngokarts-com` has an
origin spelled with a c, and the Vercel project building it is `speedway-146`.
So resolution runs from origin to the host project's own git link to the domains
actually attached, and the name on the directory is never consulted.

Every stage here is a probe that reads and changes nothing, so a run says what
is true before anything acts on it. A stage that could not be probed is reported
as unprobed and fails the run: an unverified site and a verified one must never
look alike.

  site-live.py resolve [target]   what site this is, and where it lives
  site-live.py check   [target]   every stage, probed
  site-live.py canonical <target> --set <host>
                                  redirect every other attached host to <host>

  target          a checkout path, or a domain, or nothing for the cwd
  --stage NAME    one stage rather than all seven
  --json          the record rather than the table

check exits non-zero while any stage is unresolved, so a run that ignores it is
not a run that answered it.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path.home()
INTELLIGENCE = Path(os.environ.get("INTELLIGENCE_DIR") or HOME / ".intelligence")
TOOLS = Path(__file__).resolve().parent

# Where the portfolio names every site and the address each one answers on. It
# is the only place the canonical host is written down by a person, which makes
# it the first authority when the attached domains allow more than one reading.
PORTFOLIO = Path(
    os.environ.get("INTELLIGENCE_PORTFOLIO", "")
    or HOME / "Development/WebstormProjects/taylorurl-com/src/app/data/portfolio.js"
)

# Where the portfolio sits inside whichever checkout holds it. The path above
# names one checkout, and a worktree cut from that repository is a different
# root carrying the same file, so a test for which tree the portfolio belongs
# to has to be the relative one. Asking the absolute path instead reports the
# studio's own site as missing from a portfolio it is the source of, every time
# the run happens anywhere but the primary checkout.
PORTFOLIO_IN_REPO = Path("src/app/data/portfolio.js")

# The Vercel CLI's own credential store, which is where a workstation already
# holds a working token. It expires, so it is read per run and never cached.
VERCEL_AUTH = (
    HOME / "Library/Application Support/com.vercel.cli/auth.json",
    HOME / ".local/share/com.vercel.cli/auth.json",
)

API = "https://api.vercel.com"
UA = "site-live"
TIMEOUT = 25

# The browser-reachable copy of the Pi's feed, proxied by a function on
# taylorurl-com. The Pi's own origin sits behind Tailscale and answers to this
# machine and not to a visitor, so the proxy is what a site is published in.
STATUS_FEED = os.environ.get(
    "INTELLIGENCE_STATUS_FEED", "https://www.taylorurl.com/api/status-feed")

# The reporter is matched on the endpoint it posts to rather than on any
# identifier around it: the snippet is inlined and minified into the built page,
# which renames every local it declares and leaves the URL untouched.
REPORTER = re.compile(
    r"sunday\.tail[0-9a-z]+\.ts\.net/report"
    r"|error-reporting-service/report"
    r"|errorReportingEndpoint", re.I)

# A snippet that reports and lets the browser print anyway serves a client a red
# console on their own site, and reads from outside exactly like one that does
# not. Both markers are strings the snippet holds rather than names it declares,
# so neither is renamed on the way into a built page.
SUPPRESSING = re.compile(r"__reporter|reporter-console")

STAGES = ("repo", "landed", "host", "address", "serving", "watched", "known")

# Hosts Vercel attaches to every project. They serve the site and are never its
# address, so they take no part in the canonical reading.
VENDOR_HOST = re.compile(r"\.vercel\.app$", re.I)


class Unprobed(Exception):
    """A reading that could not be taken, carrying why.

    Distinct from a failing reading: one says the site is wrong and the other
    says nothing was learned. Both fail the run, and only one is a defect.
    """


# ----------------------------------------------------------------- plumbing


def run(argv, cwd=None, timeout=TIMEOUT):
    """A command reduced to what decides a probe: the code and the text."""
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as err:
        return 1, str(err)
    return done.returncode, ((done.stdout or "") + (done.stderr or "")).strip()


def git(*args, cwd=None):
    code, text = run(["git", *args], cwd=cwd)
    return text if code == 0 else ""


def gh_json(path):
    """A GitHub read, as parsed JSON or None.

    INTELLIGENCE_ALLOW_GH is set for the child because the route guard refuses
    the commands a container cannot serve, and every call here is a read the
    workstation serves.
    """
    env = dict(os.environ, INTELLIGENCE_ALLOW_GH="1")
    try:
        done = subprocess.run(["gh", "api", path], capture_output=True,
                              text=True, timeout=TIMEOUT, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    try:
        return json.loads(done.stdout)
    except ValueError:
        return None


def vercel_token():
    """The token this machine already holds, from the environment or the CLI store."""
    from_env = os.environ.get("VERCEL_TOKEN")
    if from_env:
        return from_env
    for path in VERCEL_AUTH:
        if path.is_file():
            try:
                token = json.loads(path.read_text()).get("token")
            except (OSError, ValueError):
                continue
            if token:
                return token
    return None


def token_state(token):
    """Whether the API still answers to this token, and what to say when it does not.

    Holding a token is not the same as having one that works. The CLI's store
    keeps its credential after it expires, and every read taken with an expired
    one comes back empty, which is indistinguishable from a scope holding no
    projects. So a dead credential reported as "no Vercel project builds this
    repository" - a definite claim about the site, made on no evidence, and the
    wrong one. The identity call costs one request and separates the two.

    @returns one of missing, refused, unreachable, ok.
    """
    if not token:
        return "missing"
    request = urllib.request.Request(API + "/v2/user")
    request.add_header("Authorization", "Bearer %s" % token)
    request.add_header("User-Agent", UA)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT):
            return "ok"
    except urllib.error.HTTPError as err:
        return "refused" if err.code in (401, 403) else "unreachable"
    except (urllib.error.URLError, OSError, ValueError):
        return "unreachable"


# What each of those states leaves unanswered, in the words a probe reports it
# in. Every one of them is an Unprobed rather than a failure: none of them is a
# reading about the site.
TOKEN_UNPROBED = {
    "missing": "no Vercel token on this machine, so the host cannot be read",
    "refused": "the Vercel token on this machine was refused; run `vercel login`",
    "unreachable": "the Vercel API could not be reached, so the host cannot be read",
}


def api(path, token, method="GET", body=None):
    """One Vercel API call, or None when it was refused."""
    request = urllib.request.Request(API + path, method=method)
    request.add_header("Authorization", "Bearer %s" % token)
    request.add_header("User-Agent", UA)
    if body is not None:
        request.add_header("Content-Type", "application/json")
        request.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            return json.loads(answer.read().decode() or "{}")
    except (urllib.error.URLError, ValueError, OSError):
        return None


def head(url, follow=False):
    """How a host answers: the status, and where it points when it redirects.

    A HEAD is enough for the status and the location, and a site that refuses
    HEAD still answers GET, so a refusal falls through to one.
    """
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method)
        request.add_header("User-Agent", UA)
        opener = urllib.request.build_opener(
            urllib.request.HTTPRedirectHandler if follow else NoRedirect())
        try:
            with opener.open(request, timeout=TIMEOUT) as answer:
                return answer.status, answer.headers.get("Location", ""), answer
        except urllib.error.HTTPError as err:
            if err.code in (403, 405) and method == "HEAD":
                continue
            return err.code, err.headers.get("Location", "") if err.headers else "", None
        except (urllib.error.URLError, OSError, ssl.SSLError) as err:
            raise Unprobed("%s did not answer: %s" % (url, err))
    raise Unprobed("%s refused both HEAD and GET" % url)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is the reading here, so it is returned rather than followed."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

    def http_error_301(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)

    http_error_302 = http_error_303 = http_error_307 = http_error_308 = http_error_301


def fetch(url, fresh=False):
    """The body a visitor is served, or an Unprobed saying why there was none.

    `fresh` asks every cache in the path to stand aside. A reading that settles
    whether a deploy arrived is worthless taken from a copy made before it.
    """
    request = urllib.request.Request(url)
    request.add_header("User-Agent", UA)
    if fresh:
        request.add_header("Cache-Control", "no-cache")
        request.add_header("Pragma", "no-cache")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            return answer.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ssl.SSLError) as err:
        raise Unprobed("%s did not answer: %s" % (url, err))


def resolves(host):
    try:
        socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        return True
    except socket.gaierror:
        return False


# ---------------------------------------------------------------- resolving


def portfolio_entries():
    """Every portfolio entry, as (name, url, host).

    The file is JavaScript rather than data, so it is read for the three fields
    that matter rather than parsed. A field that moves takes its entry out of
    the reading instead of the whole file, which is the failure worth having.
    """
    if not PORTFOLIO.is_file():
        return []
    text = PORTFOLIO.read_text()
    out = []
    for block in re.split(r"\n\s*\{", text):
        name = re.search(r"name:\s*'([^']+)'", block)
        url = re.search(r"url:\s*'(https://[^']+)'", block)
        shown = re.search(r"displayUrl:\s*'([^']+)'", block)
        if name and url:
            host = re.sub(r"^https://|/.*$", "", url.group(1))
            out.append({"name": name.group(1), "url": url.group(1).rstrip("/"),
                        "host": host, "display_url": shown.group(1) if shown else host})
    return out


def checkout_for(target):
    """The checkout a target names: a path, or the cwd, or a domain's repository."""
    if target and Path(target).expanduser().is_dir():
        root = git("rev-parse", "--show-toplevel", cwd=str(Path(target).expanduser()))
        if root:
            return Path(root)
    if not target:
        root = git("rev-parse", "--show-toplevel", cwd=os.getcwd())
        if root:
            return Path(root)
    return None


def repo_from_url(url):
    """The owner/name a remote URL points at, in either of git's two spellings."""
    if not url:
        return ""
    url = url.rstrip("/").removesuffix(".git")
    parts = url.replace(":", "/").split("/")
    return "/".join(parts[-2:]) if len(parts) >= 2 else ""


def repo_of(root):
    return repo_from_url(git("remote", "get-url", "origin", cwd=str(root))
                         if root else "")


def deploy_repo(root):
    """The repository a host builds when it is not the one work lands in.

    A project can publish from a second GitHub repo: TireTracker's Vercel
    project builds IssacMoreno14/tiretracker while every pull request merges
    into TaylorURL/tiretracker. Matching the host project on origin alone
    leaves such a site permanently unprobeable on two stages, which reads the
    same as a site with no host at all. The remote names come from
    deploy-remote-sync, so one list decides what publishes for both tools.
    """
    if not root:
        return ""
    origin = git("remote", "get-url", "origin", cwd=str(root))
    for name in deploy_remote_names():
        url = git("remote", "get-url", name, cwd=str(root))
        if url and url != origin:
            return repo_from_url(url)
    return ""


def deploy_remote_names():
    spec = importlib.util.spec_from_file_location(
        "deploy_remote_sync", TOOLS / "deploy-remote-sync.py")
    if not spec or not spec.loader:
        return ()
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return ()
    return getattr(module, "DEPLOY_REMOTES", ())


def vercel_projects(token):
    """Every project the token can see, across every scope it belongs to.

    A site can sit under either team here, and the scope a run happens to be
    pointed at is not a fact about the site, so both are read.
    """
    scopes = [None]
    teams = api("/v2/teams?limit=100", token) or {}
    scopes += [t.get("id") for t in teams.get("teams", []) if t.get("id")]
    seen, out = set(), []
    for scope in scopes:
        query = "/v9/projects?limit=100" + ("&teamId=%s" % scope if scope else "")
        answer = api(query, token) or {}
        for project in answer.get("projects", []):
            key = project.get("id")
            if key in seen:
                continue
            seen.add(key)
            project["_scope"] = scope
            out.append(project)
    return out


def project_for(repo, token):
    """The host project that builds this repository, matched on its own git link."""
    if not repo or not token:
        return None
    org, _, name = repo.partition("/")
    for project in vercel_projects(token):
        link = project.get("link") or {}
        if (link.get("org") or "").lower() == org.lower() and \
           (link.get("repo") or "").lower() == name.lower():
            return project
    return None


def project_domains(project, token):
    """Every custom host attached to the project, vendor hosts left out."""
    if not project:
        return []
    scope = "?teamId=%s" % project["_scope"] if project.get("_scope") else ""
    answer = api("/v9/projects/%s/domains%s" % (project["name"], scope), token) or {}
    return [d for d in answer.get("domains", [])
            if not VENDOR_HOST.search(d.get("name", ""))]


def declared_host(root):
    """The address a site states in its own tree, for when nothing else says it.

    The portfolio is written one entry per site of work done for somebody, and
    the attached domains need a credential that answers. A repository in neither
    - the studio's own, which a portfolio of client work will never carry an
    entry for - has no address at all, and every stage that reads a page then
    goes unprobed on the one site the whole pipeline is published from.

    Each source here is a place a person maintains and a build reads, so none of
    them is a guess at the address the way a directory name is. They are tried
    from the most explicit to the most incidental.
    """
    if not root:
        return ""
    root = Path(root)

    for name in (".env.production", ".env.local", ".env"):
        path = root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text()
        except OSError:
            continue
        found = re.search(r"^\s*(?:VITE_)?SITE_URL\s*=\s*[\"']?(https?://[^\s\"']+)",
                          text, re.M)
        if found:
            return re.sub(r"^https?://|/.*$", "", found.group(1))

    package = root / "package.json"
    if package.is_file():
        try:
            homepage = json.loads(package.read_text()).get("homepage") or ""
        except (OSError, ValueError):
            homepage = ""
        if homepage.startswith("http"):
            return re.sub(r"^https?://|/.*$", "", homepage)

    index = root / "index.html"
    if index.is_file():
        try:
            markup = index.read_text()
        except OSError:
            markup = ""
        found = re.search(r"<link[^>]+rel=[\"']canonical[\"'][^>]+href=[\"'](https?://[^\"']+)",
                          markup, re.I)
        if found:
            return re.sub(r"^https?://|/.*$", "", found.group(1))

    # robots.txt names the sitemap absolutely, which makes it the one file in a
    # static tree that has to carry the host the site is served on. A site with
    # SEO at all has one, and it is wrong the moment the address moves, so it is
    # maintained rather than left behind.
    robots = root / "public/robots.txt"
    if robots.is_file():
        try:
            text = robots.read_text()
        except OSError:
            text = ""
        found = re.search(r"^\s*Sitemap:\s*(https?://[^\s]+)", text, re.I | re.M)
        if found:
            return re.sub(r"^https?://|/.*$", "", found.group(1))

    return ""


def resolve(target):
    """What site this is: repository, host project, addresses, display name.

    The canonical host is the portfolio's reading first, because it is the only
    one a person wrote down; then the attached host nothing redirects away from.
    """
    root = checkout_for(target)
    repo = repo_of(root)
    token = vercel_token()
    credential = token_state(token)
    entries = portfolio_entries()

    build_repo = repo
    working = token if credential == "ok" else None
    project = project_for(repo, working) if working else None
    if project is None and working:
        published = deploy_repo(root)
        if published and published != repo:
            project = project_for(published, working)
            if project is not None:
                build_repo = published
    domains = project_domains(project, working) if project else []

    entry = None
    if target and not root:
        host = re.sub(r"^https?://|/.*$", "", target)
        entry = next((e for e in entries if host in (e["host"], e["display_url"])), None)
    if entry is None and repo:
        stem = repo.split("/")[-1].removesuffix("-com").replace("-", "")
        entry = next((e for e in entries
                      if e["host"].split(".")[0].replace("-", "") == stem
                      or e["display_url"].split(".")[0].replace("-", "") == stem), None)
    # The repository name is a guess at the address, and it misses whenever the
    # two were spelled differently: ccscaleservicesinc-com serves
    # ccscaleservices.com, so the stem carries an "inc" the host never had. The
    # hosts attached to the project say which site this is without guessing, so
    # they settle it where the name cannot.
    if entry is None and domains:
        attached = {d["name"] for d in domains}
        entry = next((e for e in entries
                      if e["host"] in attached or e["display_url"] in attached), None)

    canonical = ""
    if entry:
        canonical = entry["host"]
    if not canonical and domains:
        standing = [d["name"] for d in domains if not d.get("redirect")]
        canonical = standing[0] if standing else domains[0]["name"]
    if not canonical:
        canonical = declared_host(root)
    if not canonical and target and not root:
        canonical = re.sub(r"^https?://|/.*$", "", target)

    return {
        "root": str(root) if root else "",
        "repo": repo,
        "build_repo": build_repo,
        "project": project["name"] if project else "",
        "scope": (project or {}).get("_scope") or "",
        "prod_branch": ((project or {}).get("link") or {}).get("productionBranch", ""),
        "canonical": canonical,
        "hosts": [d["name"] for d in domains],
        "domains": domains,
        "display": entry["name"] if entry else (repo.split("/")[-1] if repo else ""),
        "portfolio": entry,
        "token": credential == "ok",
        "credential": credential,
    }


# ------------------------------------------------------------------ probes


def probe_repo(site):
    """The repository set up the way every owned repo is."""
    repo = site["repo"]
    if not repo:
        raise Unprobed("no origin remote, so there is no repository to read")
    missing = []
    meta = gh_json("repos/%s" % repo)
    if meta is None:
        raise Unprobed("GitHub did not answer for %s" % repo)
    if not meta.get("allow_auto_merge"):
        missing.append("auto-merge off")
    if not meta.get("delete_branch_on_merge"):
        missing.append("branches kept on merge")
    if gh_json("repos/%s/branches/develop" % repo) is None:
        missing.append("no develop branch")
    for branch in ("main", "develop"):
        rule = gh_json("repos/%s/branches/%s/protection" % (repo, branch))
        contexts = (((rule or {}).get("required_status_checks") or {})
                    .get("contexts") or [])
        if "check" not in contexts:
            missing.append("%s has no required check" % branch)
    if missing:
        return False, "; ".join(missing)
    return True, "protected on both branches, auto-merge on"


def probe_landed(site):
    """Nothing waiting: no dirty tree, nothing ahead of develop, develop level with main."""
    root = site["root"]
    if not root:
        raise Unprobed("no checkout here, so there is nothing to land")
    git("fetch", "origin", "--prune", cwd=root)
    dirty = [ln for ln in git("status", "--porcelain=v1", cwd=root).splitlines() if ln]
    ahead = git("rev-list", "--count", "origin/develop..HEAD", cwd=root) or "0"
    unpromoted = git("rev-list", "--count", "origin/main..origin/develop", cwd=root) or "0"
    # Every feature branch lands by squash, which writes develop a commit of its
    # own, so the branch's commit is never an ancestor of develop however
    # completely the work arrived there. Counting commits calls a fully landed
    # branch unlanded for as long as the branch exists, which is until the next
    # sweep. What is actually waiting is content develop does not have, so the
    # count only stands when the two trees differ as well.
    if ahead != "0" and run(["git", "diff", "--quiet", "origin/develop", "HEAD"],
                            cwd=root)[0] == 0:
        ahead = "0"
    waiting = []
    if dirty:
        waiting.append("%d uncommitted file(s)" % len(dirty))
    if ahead != "0":
        waiting.append("%s commit(s) ahead of develop" % ahead)
    if unpromoted != "0":
        waiting.append("%s commit(s) on develop not promoted" % unpromoted)
    if waiting:
        return False, "; ".join(waiting)
    return True, "develop and main level, tree clean"


def probe_host(site):
    """A host project that builds this repository, from main, and is not paused."""
    if not site["token"]:
        raise Unprobed(TOKEN_UNPROBED.get(site.get("credential"), TOKEN_UNPROBED["missing"]))
    if not site["project"]:
        raise Unprobed("no Vercel project builds %s" % (site["repo"] or "this repo"))
    wrong = []
    if site["prod_branch"] and site["prod_branch"] != "main":
        wrong.append("production branch is %s" % site["prod_branch"])
    code, text = run([sys.executable, str(TOOLS / "deploy-remote-sync.py"), "check",
                      "--local"], cwd=site["root"] or None, timeout=60)
    if code != 0:
        wrong.append(text.splitlines()[-1] if text else "deploy remote is behind")
    if wrong:
        return False, "; ".join(wrong)
    built = site.get("build_repo") or site["repo"]
    published = "" if built == site["repo"] else ", which origin publishes to"
    return True, "%s builds %s from main%s" % (site["project"], built, published)


def probe_address(site):
    """One canonical host answering, and every other attached host redirecting to it."""
    canonical = site["canonical"]
    if not canonical:
        raise Unprobed("no canonical host could be resolved")
    if not resolves(canonical):
        return False, "%s does not resolve" % canonical
    status, _, _ = head("https://%s/" % canonical, follow=True)
    if status >= 400:
        return False, "%s answers %s" % (canonical, status)
    second = []
    for host in site["hosts"]:
        if host == canonical:
            continue
        if not resolves(host):
            continue
        code, where, _ = head("https://%s/" % host)
        if code < 300 or code >= 400:
            second.append("%s answers %s rather than redirecting" % (host, code))
        elif canonical not in (where or ""):
            second.append("%s redirects to %s" % (host, where or "nowhere"))
    if second:
        return False, "; ".join(second)
    return True, "%s answers %s, every other host redirects to it" % (canonical, status)


def version_endpoint(site):
    """The commit the live page says its build came from, or "" if it says nothing.

    Every site answers at /api/version with the SHA behind the build being
    served. It is the only reading in this file taken from what a visitor
    actually gets rather than from a record of what a host was asked to make,
    and it needs no credential, which is what lets a site be verified on a
    machine whose Vercel login has expired.

    A site without the endpoint answers nothing here rather than failing. The
    absence is a repository to run `version-endpoint.py install` in; it is not a
    site serving the wrong commit.
    """
    host = site.get("canonical")
    if not host:
        return ""
    try:
        body = fetch("https://%s/api/version" % host, fresh=True)
    except Unprobed:
        return ""
    found = (re.search(r"\b[0-9a-f]{40}\b", body or "")
             or re.search(r"\b[0-9a-f]{7,40}\b", body or ""))
    return found.group(0) if found else ""


def production_deployment(site):
    """The deployment the production address actually points at.

    The newest production build and the one being served are different things:
    a rollback, a pinned alias or a promote that has not finished all leave the
    newest build in front of the one visitors get.
    """
    scope = "?teamId=%s" % site["scope"] if site["scope"] else ""
    project = api("/v9/projects/%s%s" % (site["project"], scope), vercel_token())
    aliased = (((project or {}).get("targets") or {}).get("production") or {})
    if aliased.get("id"):
        full = api("/v13/deployments/%s%s" % (aliased["id"], scope), vercel_token())
        if full:
            return full
        return aliased
    listed = api("/v6/deployments?projectId=%s&target=production&limit=1%s"
                 % (site["project"], "&teamId=%s" % site["scope"] if site["scope"] else ""),
                 vercel_token())
    if not listed or not listed.get("deployments"):
        raise Unprobed("Vercel reported no production deployment")
    return listed["deployments"][0]


def probe_serving(site):
    """The page a visitor gets carrying the commit that is on main.

    The site is asked first and the host second. A page answering for itself is
    the whole question - it is the thing a visitor loads - while a deployment
    record is the host's account of what it was asked to build, which a
    command-line build, a pinned alias or a held cache each make wrong. The
    record is still read where a site has no endpoint to ask, because a reading
    from the wrong side of the question beats no reading at all.

    Absent evidence is not a pass. A deployment record with no commit on it, or
    a checkout whose main cannot be read, leaves the question unanswered rather
    than answered in the affirmative.
    """
    # The page first, and the host's record of it only when there is no page to
    # ask. A site answering for itself needs no credential, which is what lets a
    # release be verified on a machine whose Vercel login has expired.
    served = version_endpoint(site)
    source = "the page"

    if not served:
        if not site["token"] or not site["project"]:
            raise Unprobed(
                "%s serves no /api/version, and %s"
                % (site["canonical"] or "this site",
                   TOKEN_UNPROBED.get(site.get("credential"),
                                      "no Vercel project builds this repository")))
        deployment = production_deployment(site)
        state = deployment.get("readyState") or deployment.get("state")
        if state and state != "READY":
            return False, "the production deployment is %s" % state
        served = ((deployment.get("meta") or {}).get("githubCommitSha")
                  or (deployment.get("gitSource") or {}).get("sha") or "")
        source = "Vercel's record"
        if not served:
            raise Unprobed(
                "the production deployment carries no commit, so what it serves "
                "cannot be read from Vercel's record of it")

    if not site["root"]:
        raise Unprobed(
            "no checkout, so the commit it serves cannot be compared with main")
    git("fetch", "--quiet", "origin", "main", cwd=site["root"])
    on_main = git("rev-parse", "origin/main", cwd=site["root"])
    if not on_main:
        raise Unprobed("origin/main could not be read in %s" % site["root"])
    if not on_main.startswith(served[:7]):
        return False, "serving %s while main is at %s" % (served[:7], on_main[:7])
    return True, "serving %s, which is main, read from %s" % (served[:7], source)


def probe_watched(site):
    """A reporter that swallows what it reports, and the site known to the monitor and the feed."""
    canonical = site["canonical"]
    if not canonical:
        raise Unprobed("no canonical host, so nothing can be read from the page")
    gaps = []
    page = fetch("https://%s/" % canonical)
    if not REPORTER.search(page):
        gaps.append("the served page carries no reporting snippet")
    elif not SUPPRESSING.search(page):
        gaps.append("the served snippet reports errors and prints them too, so a client "
                    "reading the console sees what an agent is already fixing")
    try:
        feed = json.loads(fetch(STATUS_FEED))
    except (Unprobed, ValueError) as err:
        raise Unprobed("the public feed could not be read: %s" % err)
    stem = canonical.removeprefix("www.")
    rows = feed.get("sites") or []
    named = json.dumps(rows)
    if stem not in named and site["display"] not in named:
        gaps.append("%s is in no row of the public feed" % (site["display"] or stem))
    if gaps:
        return False, "; ".join(gaps)
    return True, "reporting snippet served, %d row(s) in the feed" % len(rows)


def probe_known(site):
    """The site written down where people and search engines look for it."""
    canonical = site["canonical"]
    if not canonical:
        raise Unprobed("no canonical host, so nothing can be looked up")
    gaps = []
    # The site that carries the portfolio is not in it. Every other site is
    # listed there as work done for somebody, and the one place that list is
    # published from is the studio's own, which has no client to be a study of.
    # Asked for an entry it will never have, this stage would fail forever on
    # the one site in the portfolio that is the portfolio.
    root = Path(site["root"]) if site["root"] else None
    carries_portfolio = bool(root) and (
        (root / PORTFOLIO_IN_REPO).is_file() or PORTFOLIO.is_relative_to(root)
    )
    if carries_portfolio:
        pass
    elif site["portfolio"] is None:
        gaps.append("no portfolio entry")
    elif site["portfolio"]["host"] != canonical:
        gaps.append("the portfolio names %s" % site["portfolio"]["host"])
    for leaf in ("robots.txt", "sitemap.xml"):
        code, _, _ = head("https://%s/%s" % (canonical, leaf), follow=True)
        if code >= 400:
            gaps.append("/%s answers %s" % (leaf, code))
    if gaps:
        return False, "; ".join(gaps)
    if carries_portfolio:
        return True, "carries the portfolio, robots and sitemap served"
    return True, "in the portfolio, robots and sitemap served"


PROBES = {
    "repo": probe_repo,
    "landed": probe_landed,
    "host": probe_host,
    "address": probe_address,
    "serving": probe_serving,
    "watched": probe_watched,
    "known": probe_known,
}

TITLES = {
    "repo": "Repository set up",
    "landed": "Work landed on main",
    "host": "A host builds it",
    "address": "One address answers",
    "serving": "Serving the promoted commit",
    "watched": "Watched",
    "known": "Known",
}


# ------------------------------------------------------------------ verbs


def check(site, only, as_json):
    results = []
    for stage in (only and [only] or list(STAGES)):
        try:
            ok, detail = PROBES[stage](site)
            state = "ok" if ok else "failing"
        except Unprobed as err:
            ok, detail, state = False, str(err), "unprobed"
        results.append({"stage": stage, "title": TITLES[stage],
                        "ok": ok, "state": state, "detail": detail})
    if as_json:
        print(json.dumps({"site": summary(site), "stages": results}, indent=2))
    else:
        say(site)
        width = max(len(r["title"]) for r in results)
        for r in results:
            mark = {"ok": "ok  ", "failing": "FAIL", "unprobed": "????"}[r["state"]]
            print("  %s  %-*s  %s" % (mark, width, r["title"], r["detail"]))
        stuck = [r["stage"] for r in results if not r["ok"]]
        print()
        print("not live" if stuck else "live", end="")
        print(": " + ", ".join(stuck) if stuck else " at https://%s" % site["canonical"])
    return 0 if all(r["ok"] for r in results) else 1


def summary(site):
    return {k: site[k] for k in
            ("root", "repo", "build_repo", "project", "prod_branch", "canonical",
             "hosts", "display")}


def say(site):
    print("  %-10s %s" % ("repo", site["repo"] or "none"))
    if site.get("build_repo") and site["build_repo"] != site["repo"]:
        print("  %-10s %s" % ("builds", site["build_repo"]))
    print("  %-10s %s" % ("project", site["project"] or "none"))
    print("  %-10s %s" % ("address", site["canonical"] or "unresolved"))
    others = [h for h in site["hosts"] if h != site["canonical"]]
    if others:
        print("  %-10s %s" % ("also", ", ".join(others)))
    print("  %-10s %s" % ("name", site["display"] or "unresolved"))
    print()


def canonical(site, wanted):
    """Point every other attached host at one, the way the rest of the estate is.

    A host attached with no redirect serves the site rather than pointing at it,
    so two attached hosts is two sites to anything that reads them. This is the
    one write here, and it moves nothing but the redirect.
    """
    token = vercel_token()
    if not token or not site["project"]:
        print("no host project resolved, so no redirect can be set")
        return 1
    if wanted not in site["hosts"]:
        print("%s is not attached to %s" % (wanted, site["project"]))
        return 1
    scope = "?teamId=%s" % site["scope"] if site["scope"] else ""
    changed = []
    for domain in site["domains"]:
        host = domain["name"]
        if host == wanted:
            if domain.get("redirect"):
                api("/v9/projects/%s/domains/%s%s" % (site["project"], host, scope),
                    token, "PATCH", {"redirect": None, "redirectStatusCode": None})
                changed.append("%s no longer redirects" % host)
            continue
        if domain.get("redirect") == wanted:
            continue
        answer = api("/v9/projects/%s/domains/%s%s" % (site["project"], host, scope),
                     token, "PATCH", {"redirect": wanted, "redirectStatusCode": 308})
        if answer is None:
            print("Vercel refused the redirect for %s" % host)
            return 1
        changed.append("%s -> %s" % (host, wanted))
    print("; ".join(changed) if changed else "already canonical on %s" % wanted)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("verb", choices=("resolve", "check", "canonical"))
    parser.add_argument("target", nargs="?", default="")
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--set", dest="wanted", help="the host every other one redirects to")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    site = resolve(args.target)

    if args.verb == "resolve":
        if args.json:
            print(json.dumps(summary(site), indent=2))
        else:
            say(site)
        return 0 if site["repo"] or site["canonical"] else 1
    if args.verb == "canonical":
        if not args.wanted:
            print("canonical needs --set <host>")
            return 2
        return canonical(site, args.wanted)
    return check(site, args.stage, args.json)


if __name__ == "__main__":
    sys.exit(main())
