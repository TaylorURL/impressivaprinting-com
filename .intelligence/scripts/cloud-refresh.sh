#!/usr/bin/env bash
# Refreshes ~/.intelligence from intelligence at the start of a cloud session.
#
# The environment's setup script installs ~/.intelligence before Claude Code starts, but
# it runs before the session exists and therefore before GH_TOKEN does. intelligence
# is private, so if the repo was not attached as a source the clone there fails and
# the container comes up with no skills - and `/design`, the canvas builder in the
# binary, still resolves, so nothing looks wrong.
#
# This runs a moment later, inside the session, where the token is set. It is the
# same fetch with credentials that exist, and it is idempotent: a container whose
# setup script already installed everything gets the same files again.
set -euo pipefail

[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

# One memory file per session. The environment installs the config into every
# home so the agent finds it whichever user it runs as, but a home that lost
# that coin toss can sit on the working directory's ancestor path, where the
# harness reads its copy as project instructions on top of the running home's
# global one -- the same 56KB in every turn, twice. The running home keeps its
# copy, verified first; the others lose only the memory file and the alias
# symlink left dangling by its removal, never their tools or skills.
if [ -s "$HOME/.intelligence/INTELLIGENCE.md" ]; then
  for other_home in /home/* /root; do
    [ "$other_home" = "$HOME" ] && continue
    [ -f "$other_home/.intelligence/INTELLIGENCE.md" ] || continue
    rm -f "$other_home/.intelligence/INTELLIGENCE.md"
    find "$other_home/.intelligence" -maxdepth 1 -type l ! -exec test -e {} \; -delete 2>/dev/null || true
  done
fi

# A repository that carries its own copy has already answered the question this
# script exists to ask, and it answered it without a token. Cloning intelligence
# over the top would only replace a working setup with the same files, and the
# failure notice printed when the clone is refused reads as missing skills to a
# session that in fact has everything.
#
# The test is a vendored copy inside a git repository, not a directory that
# merely looks like the installed setup. The environment installs the config
# into every home so the agent finds it whichever user it runs as, and the
# working directory here is often one of those homes rather than a checkout.
# Shape alone would let a sibling home's copy answer for a repository that is
# not there: the script exits, the container stays on the version its setup
# installed, and the line below prints on every session, reading as
# confirmation rather than as a refresh that never ran.
PROJECT="${CLAUDE_PROJECT_DIR:-$PWD}"
if [ -f "$PROJECT/.intelligence/VENDOR.md" ] \
   && [ -d "$PROJECT/.intelligence/checklists/design/checklist/gates" ] \
   && git -C "$PROJECT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  g=$(ls "$PROJECT"/.intelligence/checklists/design/checklist/gates/*.json 2>/dev/null | wc -l | tr -d ' ') || g=0
  n=$(find "$PROJECT/.intelligence/skills" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ') || n=0
  echo "Skills come from this repository: ${n} skills, ${g} design gate files under .intelligence/."
  exit 0
fi

DEST="$HOME/.intelligence"
MARK="$DEST/.cloud-refresh"
# The hook fires on resume and compact as well as on start, and re-cloning on
# each of those costs seconds for no change, so a recent refresh stands. Age
# rather than existence is what decides that: a container outlives the session
# it was built for, and a marker that never expires pins every later run to the
# setup installed the day the container was made. An hour is longer than any
# burst of resumes inside one session and shorter than the gap between runs.
#
# Written as an `if` rather than `[ ... ] && exit 0`, because under `set -e` the
# short form kills the script the first time the marker is absent: the test fails,
# the statement returns non-zero, and the shell exits before the refresh runs. The
# failure is silent and looks exactly like a container that had nothing to do.
if [ -f "$MARK" ] && [ -z "$(find "$MARK" -mmin +60 2>/dev/null)" ]; then
  exit 0
fi

token="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [ -z "$token" ] && command -v gh >/dev/null 2>&1; then
  token="$(gh auth token 2>/dev/null || true)"
fi
# The Pi route below carries no credentials, so an absent token rules out the
# three GitHub methods rather than the refresh itself.

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Four ways in, and the first needs no credentials. The Pi holds a copy of the
# mirror and answers over the Funnel tunnel the setup script already built, so it
# reaches a session sourced under any owner. The three GitHub methods cannot: the
# session proxy serves only the repositories a session is authorized for, and the
# mirror belongs to a different owner than most sessions start from, which no
# token widens. Where a session is authorized for it, a token is often still
# scoped to the repository the session is for, and a GitHub App installation
# token cannot read a different private repo however valid it looks. gh has its
# own credentials and the credential helper a third set.
#
# The error is printed rather than swallowed: a bare "clone failed" with the
# output discarded turns a fixable auth problem into rounds of guessing.
clone_ok=""
for method in pi token gh helper; do
  case "$method" in
    pi)     command -v rsync >/dev/null 2>&1 \
              && ssh -o BatchMode=yes -o ConnectTimeout=25 sunday \
                   'git -C "$HOME/intelligence" pull -q --ff-only 2>/dev/null || true' \
                   >/dev/null 2>"$WORK/err" \
              && rsync -az --delete --exclude .git \
                   -e "ssh -o BatchMode=yes -o ConnectTimeout=25" \
                   sunday:intelligence/ "$WORK/c/" 2>"$WORK/err" \
              && clone_ok="$method" ;;
    token)  [ -n "$token" ] && git clone --depth 1 --quiet \
              "https://x-access-token:${token}@github.com/bradley-t-t/intelligence.git" \
              "$WORK/c" 2>"$WORK/err" && clone_ok="$method" ;;
    gh)     command -v gh >/dev/null 2>&1 && \
              gh repo clone bradley-t-t/intelligence "$WORK/c" -- --depth 1 2>"$WORK/err" \
              && clone_ok="$method" ;;
    helper) git clone --depth 1 --quiet \
              "https://github.com/bradley-t-t/intelligence.git" "$WORK/c" 2>"$WORK/err" \
              && clone_ok="$method" ;;
  esac
  if [ -n "$clone_ok" ]; then
    break
  fi
  # Keep each method's error. The last to run is the credential helper, whose
  # "terminal prompts disabled" is what a method with no credentials always
  # says; reporting only that hides why the token was refused, which is the
  # answer worth having.
  printf '  [%s] ' "$method" >> "$WORK/all"
  head -1 "$WORK/err" >> "$WORK/all" 2>/dev/null || echo "(no output)" >> "$WORK/all"
  rm -rf "$WORK/c"
done

if [ -z "$clone_ok" ]; then
  echo "intelligence refresh: every clone method failed."
  cat "$WORK/all" 2>/dev/null | head -6
  echo "  (token present: $([ -n "$token" ] && echo yes || echo no); gh: $(command -v gh >/dev/null 2>&1 && echo yes || echo no))"
  echo ""
  echo "A better token does not fix this. The session proxy serves only the repositories"
  echo "a session is authorized for, and the mirror belongs to bradley-t-t, so a session"
  echo "sourced under another owner cannot clone it and add_repo cannot attach it across"
  echo "owners. The route that needs no credentials is the Pi, which holds a copy of the"
  echo "mirror behind the Funnel tunnel; the setup script leaves the key for it at"
  echo "~/.ssh/cloud_sunday. The [pi] line above says what that route reported."
  echo ""
  echo "~/.intelligence is whatever the setup script installed, so /design-checklist may not"
  echo "be here at all. Report this verbatim rather than working around it."
  exit 0
fi
echo "intelligence: cloned via ${clone_ok}."

mkdir -p "$DEST"
for part in INTELLIGENCE.md settings.json skills checklists scripts tools; do
  [ -e "$WORK/c/$part" ] || continue
  rm -rf "${DEST:?}/$part"
  cp -R "$WORK/c/$part" "$DEST/$part"
done
find "$DEST/skills" "$DEST/checklists" "$DEST/tools" "$DEST/scripts" -type f \( -name '*.py' -o -name '*.sh' \) \
  -exec chmod +x {} + 2>/dev/null || true

# The refresh above covers ~/.intelligence, and the routines are not in it. They are
# read out of the session's own checkout of the mirror, which a routine's firing
# prompt names directly and routine-sync.py resolves through the working
# directory -- and in a container that checkout is a snapshot taken when the
# container was built, not a clone taken when the session started. Containers
# outlive the sessions they were built for, so the snapshot goes on aging while
# the mirror moves. On 2026-08-28 it served seven dead trigger ids for two hours
# after the live ones had landed, and every check the sentinel ran that hour was
# run against them.
#
# Only a checkout that is not a git working tree is replaced. A snapshot holds
# nothing a session could recover and nothing git is tracking, so overwriting it
# costs nothing; a real clone may carry a branch or an uncommitted edit, and that
# session can pull for itself.
if [ -f "$PROJECT/routines/registry.json" ] \
   && ! git -C "$PROJECT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  for part in routines routine error-reporting; do
    [ -e "$WORK/c/$part" ] || continue
    rm -rf "${PROJECT:?}/$part"
    cp -R "$WORK/c/$part" "$PROJECT/$part"
  done
  echo "routines refreshed from the mirror: $PROJECT was a container snapshot."
fi

date -u +%FT%TZ > "$MARK"

n=$(find "$DEST/skills" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ') || n=0
g=$(ls "$DEST"/checklists/design/checklist/gates/*.json 2>/dev/null | wc -l | tr -d ' ') || g=0
echo "intelligence refreshed in-session: ${n} skills, ${g} design gate files."

# The CLI ships its own skill called `design`. It is a different thing - a canvas
# builder that draws artboards and never touches a repo - and a design request that
# lands on it produces a mockup instead of a changed file. The note below names the
# one that applies here, since the file on disk is the authority either way.
cat <<'NOTE'

Design work in this session runs /design-checklist, whose engine is at
~/.intelligence/checklists/design/bin/design-pass.py. /design is the CLI's canvas
builder and does not apply here.

Before doing any design work, run that engine and follow what it prints. It opens
a run over the repository; anything that does not open one is not this skill.
NOTE
