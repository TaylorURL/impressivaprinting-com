---
name: merge
description: Promote the current repo's `develop` branch to `main` by opening a PR with GitHub auto-merge enabled and waiting for it to land. Use whenever the user runs /merge, or asks to "merge develop into main", "promote develop", "release develop", "ship develop to main", or otherwise wants develop's accumulated work moved onto main. This skill is EXCLUSIVELY for the develop -> main promotion; worktree branches ship to develop via the normal PR + auto-merge flow, not this skill.
argument-hint: ""
allowed-tools: Bash, Read, Edit
---

# Promote develop to main via auto-merge

Open a PR from `develop` to `main`, enable GitHub auto-merge, and wait for it
to land. The required `check` status on `main` gates the merge, so this skill
never bypasses CI.

Do the work. Never ask the user to run a git or gh command by hand.

This skill deploys and does nothing else: no cleanup, comment, documentation,
or writing passes, and no other tools — those run on their own, never as part
of a promotion.

## Versioning happens on the develop side, not here

If the project is versioned, the version is incremented on each PR into
`develop` (that's the `/commit` flow's job — one bump per PR). By the time
`develop` is promoted to `main`, the version already reflects everything in the
release, so this skill does **not** bump it again — `main` simply inherits
develop's version. Re-incrementing here would double-count.

The one thing to check: `develop`'s version should be strictly ahead of the
version currently on `main`. If they're equal on a versioned project, a bump was
missed upstream — surface that to the user rather than silently promoting, since
it means a PR landed in develop without moving the version.

## Preconditions

The repo must already be set up with the standard workflow (see the "Git
workflow" section in the user's global `INTELLIGENCE.md`). Verify:

```bash
gh api repos/:owner/:repo --jq '{allow_auto_merge, delete_branch_on_merge}'
gh api repos/:owner/:repo/branches/main/protection --jq '.required_status_checks.contexts' 2>/dev/null
gh api repos/:owner/:repo/branches/develop --jq '.name' 2>/dev/null
```

- If `allow_auto_merge` is false, enable it:
  `gh api -X PATCH repos/:owner/:repo -f allow_auto_merge=true -f delete_branch_on_merge=true`.
- If `main` has no protection or no required status checks, stop and tell the
  user — auto-merge with no gate would merge immediately, defeating the purpose.
  Do not silently proceed.
- If `develop` does not exist on the remote, stop — there is nothing to promote.

## Step 1 — Sync develop

Fetch and confirm `develop` has commits ahead of `main`. If not, stop — there
is nothing to promote.

```bash
git fetch origin --prune
AHEAD=$(git rev-list --count origin/main..origin/develop)
if [ "$AHEAD" = "0" ]; then
  echo "develop is not ahead of main — nothing to promote"
  exit 0
fi
```

## Step 2 — Open (or reuse) the PR

Which tool opens it depends on the box, and the box decides silently: there is
nothing to weigh up at the time and nothing to say about it.

On a workstation:

```bash
PR=$(gh pr list --head "develop" --base "main" --state open --json number --jq '.[0].number')
URL=$(gh pr create --base "main" --head "develop" --title "<derived>" --body "<derived>")
PR=${URL##*/}
gh pr merge "$PR" --auto --merge
```

In a cloud container (`CLAUDE_CODE_REMOTE=true`), the same four steps are tool
calls, because the CLI's porcelain travels over GraphQL that the session does
not serve:

- `mcp__github__search_pull_requests` with `is:open head:<branch> base:<base>` to
  find an existing one
- `mcp__github__create_pull_request` to open it
- `mcp__github__enable_pr_auto_merge` with method MERGE; when it answers
  that the PR is already clean, `mcp__github__merge_pull_request` with the same
  method
- `mcp__github__pull_request_read` (`get`, `get_status`, `get_check_runs`) to
  watch it

That path appends an attribution footer to the body. Fetch the PR back with
`pull_request_read` and rewrite the body with `mcp__github__update_pull_request`
to remove it, before doing anything else.



Check for an existing open PR from `develop` to `main`:

```bash
PR=$(gh pr list --head develop --base main --state open --json number --jq '.[0].number')
```

If none, draft one. Title should summarize the release — look at commits and
merged PRs since `main` last moved:

```bash
git log --oneline origin/main..origin/develop
gh pr list --base develop --state merged --search "merged:>$(git log -1 --format=%cI origin/main)" --json number,title
```

Use those to write a title and body. No AI attribution. No emojis. Then:

`gh pr create` prints the pull request URL rather than JSON, so the number is
read off the end of it:

```bash
URL=$(gh pr create --base main --head develop \
  --title "<derived>" --body "<derived>")
PR=${URL##*/}
```

## Step 3 — Enable auto-merge (merge commit, never squash)

Use a real merge commit (`--merge`). This is deliberate, and squashing here
breaks the branch model:
`develop` is a permanent branch, so squashing it into `main` creates a commit
on `main` that shares no history with `develop`, leaving the two branches
diverged. The next promotion then conflicts and needs a manual reconciliation
(and the old "reset develop to main" workaround is impossible because branch
protection forbids force-pushing `develop`). A merge commit keeps `develop`'s
tip as an ancestor of `main`, so the branches never diverge and no reset is
ever required.

```bash
gh pr merge "$PR" --auto --merge
```

Do not switch to `--squash` or `--rebase` here — both rewrite history and
reintroduce the divergence. (Squash is correct for feature -> develop; it is
wrong for the permanent develop -> main promotion.)

If auto-merge is not allowed on the repo, enable it via the Preconditions step
and retry once.

## Step 4 — Wait for the merge

Poll every 20 seconds. Report state changes to the user; don't sit silent.

```bash
while :; do
  read -r STATE CHECKS <<<"$(gh pr view "$PR" \
    --json state,mergeStateStatus \
    --jq '[.state, .mergeStateStatus] | @tsv')"
  case "$STATE" in
    MERGED) break ;;
    CLOSED) echo "PR was closed without merging"; exit 1 ;;
  esac
  if [ "$CHECKS" = "DIRTY" ] || [ "$CHECKS" = "BLOCKED" ]; then
    if gh pr checks "$PR" | grep -Eq 'fail|error'; then
      echo "A required check failed:"
      gh pr checks "$PR"
      exit 1
    fi
  fi
  sleep 20
done
```

If a check fails, stop and surface the failing runs. Do not force-merge, do not
disable required checks, do not bypass the gate.

## Step 5 — Confirm develop and main are in sync

Because the promotion used a merge commit, `develop`'s tip is now an ancestor
of `main`, so the branches are already in sync — no reset, no force-push.
Verify it:

```bash
git fetch origin --prune
AHEAD=$(git rev-list --count origin/main..origin/develop)
echo "develop ahead of main by: $AHEAD (expected 0)"
```

`AHEAD` should be 0 after a merge-commit promotion. If it is somehow non-zero,
do NOT force-push (branch protection forbids it and this skill never weakens
protection) — report the anomaly to the user instead; it means something
outside this flow rewrote a branch.

Healing a pre-existing divergence: if `develop` and `main` were already diverged
from an earlier squash-based promotion, the first merge-commit promotion this
skill runs absorbs that divergence cleanly — when both sides carry identical
content the merge has no conflicts — and leaves them in sync from then on. No
manual step, no approval.

## Step 6 — Push to the deploy remote

Some projects are hosted from a second GitHub repo rather than the one work
lands in: TireTracker's Vercel project builds `IssacMoreno14/tiretracker`
while every PR merges into `TaylorURL/tiretracker`. A promotion that stops at
`origin` finishes green, reports success, and changes nothing a visitor can
see, because the host is watching a repo the merge never reached. Nothing
local catches it -- the merge happens on GitHub, so no pre-push hook ever runs.

```bash
~/.intelligence/tools/deploy-remote-sync.py sync
```

It finds the remote this repo publishes from, fast-forwards `main` onto it, and
says so. A repo published from `origin` has no second remote and the command is
a silent success there, so it is safe to run on every promotion.

Then confirm the host actually served it, rather than assuming the push was
enough. Where the project exposes its build, poll for the promoted commit:

```bash
SHA=$(git rev-parse origin/main)
for i in $(seq 1 30); do
  case "$(curl -sL https://<host>/api/version)" in *"$SHA"*) echo LIVE; break;; esac
  sleep 20
done
```

A host that never picks the commit up is worth saying out loud. A missed webhook
leaves the deployment to be created against the deploy remote's `main` by hand,
and it looks identical to a release that shipped.

## Step 7 — Report

Give the user a compact summary:

- PR number and merged-commit URL on `main`.
- Confirmation that `develop` and `main` are in sync (ahead-count 0).
- The deploy remote the promotion was pushed to, if the project has one, and
  the commit the host is now serving.
- Any phrase the writing pass retired with `allow`, and the reason given.

One paragraph. Do not list every command.

## Refusals

Stop and ask, don't guess, when any of these are true:

- `main` has no branch protection with required status checks.
- The writing pass flags `develop`'s prose, which is what the hook on
  `gh pr create` refuses on. Fix it and land it through its own feature-branch
  PR into `develop`, then start this skill again. Never fold that work into the
  promotion PR.
- `develop` does not exist or is not ahead of `main`.
- A required check fails on the PR.
- The PR is closed without merging.
- After the promotion, `develop` is still ahead of `main` (ahead-count non-zero)
  — do not force-push to fix it; report the anomaly instead.
- The host never serves the promoted commit. Say so plainly rather than
  reporting the release as shipped; a merged PR is not a deployed one.
