#!/usr/bin/env python3
"""The register of what this machine answers to and what it does on its own.

Two lists govern this setup and neither can be read at a glance. The skills
under `skills/` are what the machine does when it is asked; the routine registry
in the mirror is what it does when nobody is at the keyboard. Reading either
means opening a tree of frontmatter or a JSON file, so the pair is never
actually read together, and a skill retired or a routine added goes unnoticed by
the one person who owns both.

This renders them as one page. Nothing on it is written by hand: every line is
derived from the two sources, so the page cannot say something the machine does
not, and a page that has fallen behind is a fingerprint that stopped matching
rather than a judgement somebody has to make. The publish is the single step no
script can take, because an artifact is republished by a session holding the
tool, so the stop guard is what puts that step inside the session whose own
changes caused the drift.

  skills-routines-page.py build       rebuild the page from its two sources
  skills-routines-page.py status      whether what is published is still true
  skills-routines-page.py artifact U  record the url the page stands at
  skills-routines-page.py published   record the standing page as current
  skills-routines-page.py guard-stop  Stop hook: refuse a session that left it stale

INTELLIGENCE_STATE_DIR names the state directory, INTELLIGENCE_REPO the checkout
the routine registry is read from, and INTELLIGENCE_SKILLS_PAGE_OFF=1 stands the
guard down for one run.
"""
from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
TOOLS = Path(os.environ.get("INTELLIGENCE_TOOLS_DIR")
             or Path(__file__).resolve().parent)
INTELLIGENCE = TOOLS.parent

# Installed copies of somebody else's skills land here and are managed by the
# sync rather than authored, so they are not part of what this machine can be
# said to know how to do.
VENDOR = "synced"

TITLE = "Skills & Routines"
STANDFIRST = ("Two registers: what this machine answers to when it is asked, "
              "and what it does when nobody is.")

# A summary is two sentences at most, and a sentence that runs past this is cut
# at its last clause rather than mid-word. The bound is on the rendered line,
# not on the source, so a skill that opens with a long compound sentence still
# leaves the row readable.
SENTENCES = 2
CLAUSE_LIMIT = 200

BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'`(\[])")
CLAUSE = re.compile(r"[,;:]|\s--?\s|\s—\s")
# A description is written for the router that matches it, so it carries lines
# that say when to reach for a skill rather than what the skill is. Those are
# the sentences a reader of a register does not need.
TRIGGER = re.compile(
    r"^(use\b|also\b|triggers? on\b|takes\b|not the\b"
    r"|when the user\b|this skill is\b|superset of\b"
    r"|for [^,]{1,40}, see\b)", re.I)
# Prose that opens by naming a file is describing how the thing is built, not
# what it is, which makes it the wrong half of a skill to put in a register.
IMPLEMENTATION = re.compile(r"`[^`]*[./][^`]*`")

CADENCES = ("continuous", "daily", "weekly", "monthly")


def state_root():
    """Where this machine keeps state, by the order every tool here uses.

    The override outranks everything so a case suite can point the ledger at a
    fixture; a remote session keeps its own root off the config tree, which is
    the one environment where the tree is a fresh install every time.
    """
    override = os.environ.get("INTELLIGENCE_STATE_DIR")
    if override:
        return Path(override)
    if os.environ.get("CLAUDE_CODE_REMOTE"):
        return HOME / ".pass-state"
    return HOME / ".intelligence" / "state"


def ledger_path():
    return state_root() / "skills-routines.json"


def page_path():
    return state_root() / "skills-routines" / "page.html"


def write_atomic(path, text):
    """A file replaced whole, so a concurrent read never lands mid-write."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("%s.%d.tmp" % (path.name, os.getpid()))
    tmp.write_text(text)
    os.replace(tmp, path)


def load_ledger():
    try:
        return json.loads(ledger_path().read_text())
    except (OSError, ValueError):
        return {}


def save_ledger(led):
    write_atomic(ledger_path(), json.dumps(led, indent=2) + "\n")


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def registry_path():
    """The routine registry, wherever this machine holds the mirror.

    `routine-sync.py` owns the question of where the checkout is, so it is asked
    rather than answered again here. Its search covers the checkouts a person
    works in; the copy the config sync keeps is the one a machine that has never
    held a working checkout still has, which is every container.
    """
    named = os.environ.get("INTELLIGENCE_REPO")
    if named:
        found = Path(named) / "routines" / "registry.json"
        return found if found.is_file() else None
    sync = TOOLS / "routine-sync.py"
    if sync.is_file():
        try:
            spec = importlib.util.spec_from_file_location("routine_sync",
                                                          str(sync))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            root = mod.repo_root()
            if root:
                found = Path(root) / "routines" / "registry.json"
                if found.is_file():
                    return found
        except Exception:
            pass
    found = state_root() / ".config-sync-repo" / "routines" / "registry.json"
    return found if found.is_file() else None


def frontmatter(text):
    """The YAML block a skill opens with, flattened to single-line values.

    Only `name` and `description` are read and both are written on one line in
    every skill here, so this stops at the first key rather than carrying a
    parser for a shape the tree does not use.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out = {}
    for line in text[3:end].splitlines():
        if line[:1] in (" ", "\t", "") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def opening_paragraph(text):
    """The prose a skill opens with under its own heading.

    A description is written for the router that has to match it, so it carries
    trigger phrases and lists of aliases that read as noise in a summary. The
    paragraph under the first heading is written for a person, which is what a
    reader of this page is.
    """
    body = text
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end >= 0:
            body = body[end + 4:]
    heading = re.search(r"^#\s+.+$", body, re.M)
    if not heading:
        return ""
    rest = body[heading.end():].lstrip("\n")
    para = []
    for line in rest.splitlines():
        if not line.strip():
            if para:
                break
            continue
        if line.lstrip().startswith(("#", "-", "*", ">", "|", "```", "1.")):
            break
        para.append(line.strip())
    return " ".join(para)


def trim(sentence):
    """A sentence cut at its last clause boundary when it outruns a row."""
    if len(sentence) <= CLAUSE_LIMIT:
        return sentence
    cuts = [m.start() for m in CLAUSE.finditer(sentence)
            if m.start() < CLAUSE_LIMIT]
    if not cuts:
        return sentence[:CLAUSE_LIMIT].rsplit(" ", 1)[0] + "."
    return sentence[:cuts[-1]].rstrip(" ,;:") + "."


def _summarize(text):
    """Two sentences at most, and whether saying it took a cut."""
    text = " ".join((text or "").split())
    if not text:
        return "", False
    kept, cut = [], False
    for sentence in BOUNDARY.split(text):
        sentence = sentence.strip()
        if not sentence or TRIGGER.match(sentence):
            continue
        shortened = trim(sentence)
        cut = cut or shortened != sentence
        kept.append(shortened)
        if len(kept) == SENTENCES:
            break
    return " ".join(kept), cut


def summarize(text):
    """At most two sentences of what a thing is, never how it is triggered."""
    return _summarize(text)[0]


def best_summary(description, body):
    """Whichever of a skill's two accounts of itself fits a row whole.

    The description is the canonical line -- it is what the router matches and
    what a skill is judged by, so it is written to say what the thing does. It
    is also where a skill that wants to be found stacks clauses, and one that
    ran long would reach a reader mid-clause. The prose under the heading is the
    fallback for exactly that case, and for a description that says only when to
    reach for the skill and never what it is.
    """
    said, cut = _summarize(description)
    if said and not cut:
        return said
    spoken, spoken_cut = _summarize(body)
    if spoken and not spoken_cut and not IMPLEMENTATION.search(spoken):
        return spoken
    return said or spoken


def inline(text):
    """Markdown a summary carries, rendered rather than shown as punctuation."""
    out = html.escape(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return out


def skills():
    """Every skill this machine holds, by name, with what each one is."""
    root = INTELLIGENCE / "skills"
    found = []
    for path in sorted(root.glob("*/SKILL.md")):
        if path.parent.name == VENDOR:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        meta = frontmatter(text)
        summary = best_summary(meta.get("description", ""),
                               opening_paragraph(text))
        found.append({
            "name": meta.get("name") or path.parent.name,
            "summary": summary,
        })
    return found


def routines():
    """Every routine the registry holds, in the order a day meets them."""
    where = registry_path()
    if not where:
        return []
    try:
        data = json.loads(where.read_text())
    except (OSError, ValueError):
        return []
    found = []
    for row in data.get("routines", []):
        found.append({
            "id": row.get("id", ""),
            "name": row.get("name") or row.get("id", ""),
            "cadence": row.get("cadence", ""),
            "host": row.get("host", ""),
            "schedule": schedule_of(row),
            "summary": summarize(row.get("does", "")),
        })
    order = {c: i for i, c in enumerate(CADENCES)}
    found.sort(key=lambda r: (order.get(r["cadence"], len(CADENCES)),
                              r["name"].lower()))
    return found


def source_hash(skill_rows, routine_rows):
    """A fingerprint of what the page says, so drift is a comparison.

    Every field rendered is in here and nothing else is. A skill reworded
    changes the page, so it changes this; a skill's file touched without its
    prose changing does not, which keeps a sync that rewrites mtimes from
    reporting a page that is still true as stale.
    """
    body = "|".join("%s:%s" % (s["name"], s["summary"]) for s in skill_rows)
    body += "||" + "|".join(
        "%s:%s:%s:%s:%s" % (r["id"], r["cadence"], r["host"], r["schedule"],
                            r["summary"]) for r in routine_rows)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def schedule_of(row):
    """When a routine fires, as short as the registry allows it to be said.

    A routine started by a tick script carries the whole invocation in its gate,
    and the part that answers "when" is the cron in front of it. What the tick
    then decides is in the routine's own line, so nothing is lost by dropping it
    from the column.
    """
    named = (row.get("schedule") or "").strip()
    if named:
        return named
    gate = (row.get("gate") or "").strip()
    fields = gate.split()
    if len(fields) > 5:
        return " ".join(fields[:5])
    return gate or "on demand"


def host_label(host):
    return {"pi": "Pi", "mac": "Mac"}.get(host, host.title() or "Unassigned")


STYLE = """
:root {
  --ground: #e8ecea;
  --surface: #fbfcfb;
  --ink: #101716;
  --ink-soft: #4e5a58;
  --rule: #ccd5d2;
  --typed: #0d5c57;
  --scheduled: #8a5f17;
  --chip: #dde4e1;
}
:root:not([data-theme="light"]) {
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground: #0e1312;
    --surface: #151c1b;
    --ink: #e7ecea;
    --ink-soft: #93a2a0;
    --rule: #28322f;
    --typed: #5fc9be;
    --scheduled: #c89a4a;
    --chip: #1e2726;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --ground: #0e1312;
  --surface: #151c1b;
  --ink: #e7ecea;
  --ink-soft: #93a2a0;
  --rule: #28322f;
  --typed: #5fc9be;
  --scheduled: #c89a4a;
  --chip: #1e2726;
  color-scheme: dark;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: "Source Serif 4", Georgia, "Times New Roman", serif;
  font-size: 17px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.sheet {
  max-width: 62rem;
  margin: 0 auto;
  padding: clamp(2rem, 6vw, 4.5rem) clamp(1.1rem, 4vw, 3rem) 4rem;
}
.mono {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-variant-numeric: tabular-nums;
}
.masthead { border-bottom: 2px solid var(--ink); padding-bottom: 1.5rem; }
h1 {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 500;
  font-size: clamp(2rem, 6vw, 3.1rem);
  letter-spacing: -0.045em;
  line-height: 1.05;
  margin: 0 0 0.7rem;
  text-wrap: balance;
}
.standfirst {
  margin: 0;
  max-width: 34em;
  font-size: 1.12rem;
  color: var(--ink-soft);
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 2.2rem;
  margin-top: 1.6rem;
  font-size: 0.72rem;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--ink-soft);
}
.meta b { color: var(--ink); font-weight: 500; }
section { margin-top: 3.4rem; }
.register {
  display: flex;
  align-items: baseline;
  gap: 0.9rem;
  border-bottom: 1px solid var(--rule);
  padding-bottom: 0.5rem;
}
h2 {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 500;
  font-size: 1.3rem;
  letter-spacing: -0.02em;
  margin: 0;
}
.count { font-size: 0.72rem; letter-spacing: 0.09em; color: var(--ink-soft); }
.note {
  margin: 0.9rem 0 0;
  font-size: 0.95rem;
  color: var(--ink-soft);
  max-width: 40em;
}
.rows { margin-top: 1.4rem; }
.row {
  display: grid;
  gap: 0.35rem 1.6rem;
  padding: 1rem 0 1rem 1.1rem;
  border-top: 1px solid var(--rule);
  border-left: 2px solid transparent;
  background: var(--surface);
}
.row:last-child { border-bottom: 1px solid var(--rule); }
.skills .row { grid-template-columns: 10rem 1fr; border-left-color: var(--typed); }
.routines .row {
  grid-template-columns: 11rem 10rem 1fr;
  border-left-color: var(--scheduled);
}
.label {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.94rem;
  font-weight: 500;
  letter-spacing: -0.01em;
  overflow-wrap: anywhere;
}
.skills .label { color: var(--typed); }
.when { font-size: 0.82rem; color: var(--ink-soft); overflow-wrap: anywhere; }
.host {
  display: inline-block;
  margin-top: 0.3rem;
  padding: 0.1rem 0.45rem;
  border-radius: 2px;
  background: var(--chip);
  color: var(--ink-soft);
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.summary { margin: 0; }
.summary code {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.86em;
  background: var(--chip);
  padding: 0.05em 0.3em;
  border-radius: 2px;
}
.band {
  margin: 2.2rem 0 0;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--scheduled);
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.band::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--rule);
}
.band + .rows { margin-top: 0.8rem; }
footer {
  margin-top: 3.6rem;
  padding-top: 1.2rem;
  border-top: 1px solid var(--rule);
  font-size: 0.78rem;
  color: var(--ink-soft);
}
footer p { margin: 0.35rem 0; overflow-wrap: anywhere; }
@media (max-width: 720px) {
  .skills .row, .routines .row { grid-template-columns: 1fr; }
  .row { padding-top: 0.9rem; padding-bottom: 0.9rem; }
}
"""


def render(skill_rows, routine_rows, fingerprint):
    """The page itself, every line of it derived from the two registers."""
    out = []
    out.append("<title>" + TITLE + "</title>")
    out.append('<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
               "?family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,"
               'wght@8..60,400;8..60,600&display=swap">')
    out.append("<style>" + STYLE + "</style>")
    out.append('<main class="sheet">')

    out.append('<header class="masthead">')
    out.append("<h1>" + html.escape(TITLE) + "</h1>")
    out.append('<p class="standfirst">' + html.escape(STANDFIRST) + "</p>")
    out.append('<div class="meta mono">'
               "<span><b>" + str(len(skill_rows)) + "</b> Skills</span>"
               "<span><b>" + str(len(routine_rows)) + "</b> Routines</span>"
               "<span>Generated <b>" + datetime.now(timezone.utc)
               .strftime("%d %b %Y %H:%M UTC") + "</b></span>"
               "<span>Source <b>" + fingerprint + "</b></span>"
               "</div>")
    out.append("</header>")

    out.append('<section class="skills">')
    out.append('<div class="register"><h2>Skills</h2>'
               '<span class="count mono">Invoked by name</span></div>')
    out.append('<p class="note">Each one is typed as a command or matched by '
               "what it describes.</p>")
    out.append('<div class="rows">')
    for row in skill_rows:
        out.append('<article class="row">'
                   '<div class="label">/' + html.escape(row["name"]) + "</div>"
                   '<p class="summary">' + inline(row["summary"]) + "</p>"
                   "</article>")
    out.append("</div></section>")

    out.append('<section class="routines">')
    out.append('<div class="register"><h2>Routines</h2>'
               '<span class="count mono">Fired on a schedule</span></div>')
    out.append('<p class="note">Each one runs without being asked, on the '
               "machine named beside it.</p>")
    for cadence in CADENCES:
        band = [r for r in routine_rows if r["cadence"] == cadence]
        if not band:
            continue
        out.append('<p class="band mono">' + cadence.title() + "</p>")
        out.append('<div class="rows">')
        for row in band:
            out.append('<article class="row">'
                       '<div><span class="label">'
                       + html.escape(row["name"]) + "</span><br>"
                       '<span class="host">' + html.escape(
                           host_label(row["host"])) + "</span></div>"
                       '<div class="when mono">' + html.escape(row["schedule"])
                       + "</div>"
                       '<p class="summary">' + inline(row["summary"]) + "</p>"
                       "</article>")
        out.append("</div>")
    unplaced = [r for r in routine_rows if r["cadence"] not in CADENCES]
    if unplaced:
        out.append('<p class="band mono">Unscheduled</p><div class="rows">')
        for row in unplaced:
            out.append('<article class="row">'
                       '<div><span class="label">'
                       + html.escape(row["name"]) + "</span></div>"
                       '<div class="when mono">' + html.escape(row["schedule"])
                       + "</div>"
                       '<p class="summary">' + inline(row["summary"]) + "</p>"
                       "</article>")
        out.append("</div>")
    out.append("</section>")

    out.append("<footer>")
    out.append('<p class="mono">Skills read from ~/.intelligence/skills</p>')
    out.append('<p class="mono">Routines read from routines/registry.json</p>')
    out.append("</footer>")
    out.append("</main>")
    return "\n".join(out) + "\n"


def build(force=False):
    """Bring the page file into line with the two registers.

    The file is only rewritten when what it would say has changed, so the stamp
    it carries is the moment the registers last moved rather than the moment
    something last ran. That matters because every verb here builds first: a
    rebuild on each call would leave a page whose date advances while nothing
    about the machine did.
    """
    skill_rows, routine_rows = skills(), routines()
    fingerprint = source_hash(skill_rows, routine_rows)
    led = load_ledger()
    if (force or led.get("source_hash") != fingerprint
            or not page_path().is_file()):
        write_atomic(page_path(), render(skill_rows, routine_rows, fingerprint))
        led["source_hash"] = fingerprint
        led["built_at"] = stamp()
        led["skills"] = len(skill_rows)
        led["routines"] = len(routine_rows)
        save_ledger(led)
    return fingerprint


def cmd_build():
    fingerprint = build(force=True)
    print("%s (%s)" % (page_path(), fingerprint))
    return 0


def cmd_status():
    """Whether what a reader would open still says what the machine holds."""
    fingerprint = build()
    led = load_ledger()
    url = led.get("url", "")
    if not url:
        print("skills-routines: page built, none published from this machine")
        return 0
    if led.get("published_state") == fingerprint:
        print("skills-routines: the published page matches its sources")
        return 0
    print("  page: %s\n  url:  %s" % (page_path(), url))
    print("skills-routines: the published page is BEHIND its sources")
    return 1


def cmd_artifact(url):
    """Record the url the page stands at, without touching the page.

    What is published is the file as it stood when it was published. A rebuild
    here would restamp it a moment later and leave the live page a minute
    behind its own local copy, which is the drift this tool exists to catch.
    """
    led = load_ledger()
    led["url"] = url
    save_ledger(led)
    fingerprint = build()
    led = load_ledger()
    led["published_state"] = fingerprint
    led["published_at"] = stamp()
    save_ledger(led)
    print("skills-routines: %s" % url)
    return 0


def cmd_published():
    """Record that the page standing at the url now says what the sources do."""
    fingerprint = build()
    led = load_ledger()
    if not led.get("url"):
        sys.stderr.write("skills-routines: no url recorded; run artifact <url>"
                         " with where the page was published\n")
        return 1
    led["published_state"] = fingerprint
    led["published_at"] = stamp()
    save_ledger(led)
    print("skills-routines: page recorded as published")
    return 0


def guard_stop():
    """Refuse to end a session that left the page saying something older.

    Every other part of this is automatic: the file is generated, and it is
    regenerated by the verb the hooks call. The republish is the step that needs
    a session, and a session that changed a skill and ended is exactly when
    nobody is left to take it. So it is taken here, by the run that caused it,
    rather than left for whoever opens the link next.
    """
    if os.environ.get("INTELLIGENCE_SKILLS_PAGE_OFF") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    if payload.get("stop_hook_active"):
        return 0
    led = load_ledger()
    if not led.get("url"):
        return 0
    fingerprint = build()
    if led.get("published_state") == fingerprint:
        return 0
    sys.stderr.write(
        "BLOCKED: the skills and routines page no longer says what this "
        "machine holds.\n\n"
        "  page: %s\n  url:  %s\n\n"
        "Republish that file to that url with the Artifact tool, passing the "
        "url so it\nupdates in place, then record it:\n\n"
        "  ~/.intelligence/tools/skills-routines-page.py published\n\n"
        "INTELLIGENCE_SKILLS_PAGE_OFF=1 lets one run finish without it.\n"
        % (page_path(), led["url"]))
    return 2


def hook_edit():
    """Rebuild after an edit that could have moved a register.

    The precondition lives in the hub, which fires this only for a write under
    the skills tree or to the registry, so reaching here is enough to rebuild.
    Nothing is printed: a hook that talks on every skill edit is a hook that
    gets turned off.
    """
    try:
        build()
    except Exception:
        return 0
    return 0


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "build":
        return cmd_build()
    if verb == "status":
        return cmd_status()
    if verb == "artifact":
        if len(sys.argv) < 3:
            sys.stderr.write("skills-routines: artifact needs a url\n")
            return 1
        return cmd_artifact(sys.argv[2])
    if verb == "published":
        return cmd_published()
    if verb == "guard-stop":
        return guard_stop()
    if verb == "hook-edit":
        return hook_edit()
    sys.stderr.write(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
