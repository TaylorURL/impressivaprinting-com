---
name: checklist
description: Run every checklist a project answers to at once - design, SEO, performance, stack, database and Google, swept concurrently and reported as one record. Use on /checklist, or "run the checklists", "check everything", "full pass on this site", "is this ready to ship". Also before releasing a public site.
---

# The full checklist pass

Six checklists govern a public site, and each owns one question. Design answers
for what a reader sees; SEO for whether they arrive at all; performance for how
long they wait; stack for whether the thing is wired up and alive underneath those
three; the database checklist for whether the schema underneath all four still
matches what the code does; and the Google checklist for whether the accounts
Google keeps about the site are set up and correct, which is the one question no
amount of reading the repository can answer. They are separate registries with
separate state, and a project that ships owes all six.

Running them one after another multiplies the wall-clock for no reason: the runs
share no state, live under different directories, and none reads another's results.
This skill runs them together.

Three of them have an order to it. The performance run needs a live URL, and a
baseline measurement and a rendered capture taken **before anything is edited** - a
`PreToolUse` hook refuses a source edit until both exist, because neither can be
established afterwards. The stack and database runs need their probes, which are
network-bound and slow, and whose findings change what the others are even looking
at: there is no point tuning a bundle on a site whose production deployment is three
weeks behind main, or polishing a page served by a database timing out under a
relation nobody reads. So those three open first and the other sweeps run while they
are in flight.

Because each checklist owns one question, each hands the others what it finds
outside its own. That handover is a recorded step in the stack run and a reported
one in the rest; a finding dropped because it belonged to somebody else is the one
nobody comes back for.

**This is an instruction to change the project, not to survey it.** A gate that is
not met is work to do. The only ways past one are changing the code or naming the
condition that makes it inapplicable.

## 0. Find the five tools

```bash
DESIGN="$HOME/.intelligence/checklists/design/bin/design-pass.py"
SEO="$HOME/.intelligence/checklists/seo/bin/seo-pass.py"
PERF="$HOME/.intelligence/checklists/perf/bin/perf-pass.py"
STACK="$HOME/.intelligence/checklists/stack/bin/stack-pass.py"
DB="$HOME/.intelligence/checklists/db/bin/db-pass.py"
GOOGLE="$HOME/.intelligence/checklists/google/bin/google-pass.py"
PERFDIR="$HOME/.intelligence/checklists/perf/scripts"
STACKPROBE="$HOME/.intelligence/checklists/stack/scripts/probe.py"
DBPROBE="$HOME/.intelligence/checklists/db/scripts/probe.py"
GOOGLEPROBE="$HOME/.intelligence/checklists/google/scripts/probe.py"
```

Each resolves its own registry from its own location, so a vendored copy in a repo
works the same way. If any is missing, say so rather than running five sixths of a
pass and reporting it as a full one.

The Google run is the one that is not scoped to the project. It reads the whole
portfolio, so under `/checklist` on a single project open it against that
project's own domain rather than `--all`, and leave the portfolio sweep to a
`/google-checklist` run of its own:

```bash
"$GOOGLE" start --site <domain> --registry <taylorurl-com checkout>
```

## 1. Open all five runs, concurrently

```bash
"$DESIGN" start --kind web-ui --target <path> --title "<what this is>" &
"$SEO" start --kind site --target <path> --title "<what this is>" &
"$PERF" start --kind site --target <path> --url https://<host> --title "<what this is>" &
"$STACK" start --kind site --target <path> --url https://<host> --title "<what this is>" &
"$DB" start --kind site --target <path> --project-ref <ref> --title "<what this is>" &
wait
```

`--project-ref` may be left off where the repository names one. The database run
takes `--kind` and `--title` like the rest and ignores both when deciding which
gates apply; its probe settles that.

Then the performance baseline, before any file is touched. The key is in CryptoFort
as `google-pagespeed-api-key`; read it at the point of use:

```bash
GOOGLE_PAGESPEED_API_KEY=<from CryptoFort> "$PERFDIR/psi.py" measure \
  --url https://<host> --runs 3 --out /tmp/perf-before.json
"$PERF" measure --file /tmp/perf-before.json --label before
"$PERF" scan --metric <whichever metric psi named as worst in the field>

node "$PERFDIR/capture.js" --url https://<host> --out /tmp/perf-before-capture.json --built
"$PERF" parity --phase before --file /tmp/perf-before-capture.json
```

The stack probes go alongside those, because they are the slowest thing in the pass
and everything else is cheaper to redo than to run against a wrong answer. Every
credential comes from CryptoFort into the call that needs it, never into a file:

```bash
SUPABASE_URL=<url> SUPABASE_ANON_KEY=<key> SUPABASE_ACCESS_TOKEN=<pat> \
STRIPE_SECRET_KEY=<key> CLERK_SECRET_KEY=<key> VERCEL_TOKEN=<token> \
  "$STACKPROBE" all --root <path> --url https://<host>
"$STACK" probe --file <the path the probe printed>

SUPABASE_ACCESS_TOKEN=<from the vault> \
  "$DBPROBE" all --root <path>
"$DB" probe --file <the path the probe printed>
"$STACK" services
```

Read `services` before going further. A paused project, a development key in
production, or a production deployment that is not the commit `main` points at makes
most of the rest of this pass beside the point until it is fixed.

Each prints the gates that apply, derived from what the target contains. The design
run also needs its design read before any file is written:

```bash
"$DESIGN" read --page-kind <landing|portfolio|editorial|product> --audience "<who>" \
  --vibe "<the words the brief used>" --palette "<family>" --face "<display face>"
```

## 2. Sweep all five, concurrently

```bash
"$DESIGN" verify > /tmp/design-sweep.txt 2>&1 &
"$SEO" verify > /tmp/seo-sweep.txt 2>&1 &
"$PERF" verify > /tmp/perf-sweep.txt 2>&1 &
"$STACK" verify > /tmp/stack-sweep.txt 2>&1 &
"$DB" verify > /tmp/db-sweep.txt 2>&1 &
wait
```

The performance sweep reads the build as well as the source, and the two differ by
everything the bundler did. Build before it runs; it leads with a warning when the
output is behind the source.

The design sweep runs its checks across processes on its own, because they are regex
over the whole source bundle and a thread would take the same wall-clock as one. On a
450-file project that is the difference between 77 seconds and 21. The SEO sweep stays
serial on purpose: two seconds of work against a six-megabyte payload, where a pool
costs more to feed than it saves.

## 3. Fix what the sweeps found

Every tool names a file and a line. Fix the code. A gate the sweep failed cannot be
answered `pass` by any of them, so there is nothing to decide here.

## 4. Answer what a script cannot settle

Ask each tool for its open gates with the rule and the fix attached:

```bash
"$DESIGN" status --full > /tmp/design-open.txt 2>&1 &
"$SEO" status --full > /tmp/seo-open.txt 2>&1 &
"$PERF" status --full > /tmp/perf-open.txt 2>&1 &
"$STACK" status --full > /tmp/stack-open.txt 2>&1 &
"$DB" status --full > /tmp/db-open.txt 2>&1 &
wait
```

Then answer each in one call per tool:

```bash
"$DESIGN" resolve --batch - <<'JSON'
[{"id": "PTR-02", "status": "fixed", "note": "added :active scale(0.97) to every button and row"},
 {"id": "SLP-28", "status": "na",    "note": "no hero video; the hero is a single still at 3:2"}]
JSON

"$SEO" resolve --batch - <<'JSON'
[{"id": "HED-04", "status": "fixed", "note": "wrote a 152-character description for every route"}]
JSON

"$PERF" resolve --batch - <<'JSON'
[{"id": "JSB-01", "status": "fixed", "note": "17 routes moved behind React.lazy; first load 204KB -> 61KB"}]
JSON

"$STACK" resolve --batch - <<'JSON'
[{"id": "TLG-03", "status": "fixed", "note": "added the format:check step to ci.yml on both branches"}]
JSON

"$DB" resolve --batch - <<'JSON'
[{"id": "HLT-02", "status": "fixed", "note": "scheduled a daily prune and a weekly vacuum on the cron run log"}]
JSON
```

The database run refuses `pass` and `na` on every gate in its orphan, access,
health and provenance groups, for the same reason the stack run does on its
services: its whole subject is outside the repository, and a table created by hand
in a dashboard is invisible to any number of migration files read carefully.

The stack run's service gates take no hand answer either, for the same reason and in
the same shape as parity: `pass` and `na` are both refused on anything that answers
to a request, because an attestation that a service is up is exactly what the probe
replaces. Change the setting and probe again.

This pass is also where the handovers get recorded. Anything the stack sweep turned
up that belongs to one of the other three is filed against it and fixed in that run:

```bash
"$STACK" delegate --to design --note "the bar sits 4px under the CTA at 375px"
"$STACK" delegate --none      # when nothing outside that checklist came up

"$DB" delegate --to stack --note "email-service reads a table that exists in no schema"
"$DB" delegate --none
```

The performance run's parity gates take no hand answer at all. `pass` and `na` are
both refused on PAR-01 through PAR-08: they answer to the before and after captures,
because an attestation that the page looks the same is the thing those captures exist
to replace.

Every row keeps its own status and its own note. The note minimum applies per row, a
sweep-failed gate cannot be answered `pass`, the bookkeeping gates refuse an
attestation, and a batch carrying one bad row is refused whole with every fault named.

### Where subagents fit, and where they do not

A run is single-owner state. It is keyed on the session id, the file ledger is
credited by this session's `PostToolUse` hook, and there is no lock on the run file,
so a subagent that calls `resolve` either races the parent or opens a second run that
answers for nothing.

What a subagent can do is the reading. Give one a slice of the deliverable and the
open gates for that slice, and have it return **proposed answers as JSON and nothing
else** - no tool calls against either run:

```
Read <these files>. For each gate below, return one JSON array of
{"id", "status", "note"} where status is pass, fixed, or na and the note says what
you looked at and what it showed. Do not run design-pass.py or seo-pass.py.
```

The parent merges what comes back and submits it through `resolve --batch`, where
every guarantee still applies. Evidence gathering fans out; recording verdicts does
not. Split by area rather than by gate - one subagent per route or per component tree
- so each one reads a coherent slice instead of the same files N times.

Fan out only when the slices are independent of each other and the reading is the cost. A
handful of open gates is cheaper answered directly than handed off.

## 5. Rule on every file, in batches

Each tool keeps a ledger of every file under its targets, and a file cannot be
cleared until the harness has watched it be read.

```bash
sed -n '1,400p' <path> <path> <path>          # one call reads and credits many
"$DESIGN" file-clear --batch - <<'JSON'
[{"path": "src/lib/format.ts", "note": "read in full; pure date maths, carries no design"}]
JSON
```

The database run keeps the same kind of ledger over tables rather than files, since
a table is not something the harness can watch being read. Every table ends dropped
or kept with its reader named:

```bash
"$DB" tables
"$DB" table-clear --batch - <<'JSON'
[{"table": "mixers_history", "note": "read by src/app/hooks/useStatusHistory.js"}]
JSON
```

## 6. Report all five, as one record

```bash
"$DESIGN" report
"$SEO" report
"$PERF" report
"$STACK" report
"$DB" report
```

Every filled checklist is shown in full. The stack and database reports lead with
what answered over the network and out of the catalogue, which is the part that
describes the world rather than the repository. Lead with what changed. Every gate answered
`na` is listed in its own section, because a gate only entered a run when its
condition was found in the target, and skipping one is a claim worth reading.

## 7. Close all five

Close the performance run last: it needs the after capture and the after
measurement, which need the build the other runs' changes produced.

```bash
node "$PERFDIR/capture.js" --url http://localhost:4173 --out /tmp/perf-after-capture.json --built
"$PERF" parity --phase after --file /tmp/perf-after-capture.json
"$PERF" parity --diff

"$DESIGN" finish
"$SEO" finish
"$PERF" finish
"$STACK" finish
"$DB" finish
```

Each refuses while anything is open, and a `Stop` hook refuses to end the session
with any of them still going. Do not close four and leave the fifth; a
half-answered pass reported as a full one is the failure this skill exists to
remove.

A design change made in this pass will move the page, and the performance run's
parity diff will report it. That is correct and it is not a conflict: the parity
gates ask whether the *performance* work changed the rendering, so a deliberate
design change is recorded against the design run and answered on the performance run
as `disputed`, naming the design gate that caused it.

## What this skill does not do

It does not lower any bar to go faster. The gate registries, their severities, the
per-row validation, the file ledger, and the refusal to record a failing gate as
passing are exactly what they are when either skill runs alone. What it changes is
how many things wait on each other.
