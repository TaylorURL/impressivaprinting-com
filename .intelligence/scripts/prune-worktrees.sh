#!/usr/bin/env bash
# Prune git worktrees whose branches have merged into develop/main or whose
# remote is [gone]. Invoked from the SessionStart hook. Reads hook JSON on
# stdin but works fine without it — falls back to $PWD.

set -u

input=$(cat 2>/dev/null || printf '{}')
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null || true)
[ -z "$cwd" ] && cwd=$PWD
pwd_at_entry=$PWD

cd "$cwd" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

main_dir=$(git worktree list --porcelain | awk '/^worktree / { print $2; exit }')
[ -z "$main_dir" ] && exit 0

cd "$main_dir" || exit 0

git fetch --prune --quiet 2>/dev/null || true

current_a="$cwd"
current_b="$pwd_at_entry"
removed=0

while IFS=$'\t' read -r wt_path wt_branch; do
  [ -z "$wt_path" ] && continue
  [ -z "$wt_branch" ] && continue
  [ "$wt_path" = "$main_dir" ] && continue
  # Never remove the worktree this session is standing in, or one that contains
  # it. Both the hook's reported cwd and the shell's own are checked because
  # they can differ, and the prefix cases catch a session sitting somewhere
  # below the worktree root rather than at it.
  [ "$wt_path" = "$current_a" ] && continue
  [ "$wt_path" = "$current_b" ] && continue
  case "$current_a" in "$wt_path"/*) continue ;; esac
  case "$current_b" in "$wt_path"/*) continue ;; esac
  [ ! -d "$wt_path" ] && continue

  branch=${wt_branch#refs/heads/}

  if [ -n "$(git -C "$wt_path" status --porcelain 2>/dev/null)" ]; then
    continue
  fi

  cleanup=0
  for base in develop main; do
    if git show-ref --verify --quiet "refs/heads/$base" \
      && git merge-base --is-ancestor "$branch" "$base" 2>/dev/null; then
      cleanup=1
      break
    fi
    if git show-ref --verify --quiet "refs/remotes/origin/$base" \
      && git merge-base --is-ancestor "$branch" "origin/$base" 2>/dev/null; then
      cleanup=1
      break
    fi
  done

  if [ $cleanup -eq 0 ]; then
    upstream=$(git rev-parse --abbrev-ref "$branch@{upstream}" 2>/dev/null || true)
    if [ -n "$upstream" ] && ! git show-ref --verify --quiet "refs/remotes/$upstream"; then
      cleanup=1
    fi
  fi

  if [ $cleanup -eq 1 ] && git worktree remove "$wt_path" 2>/dev/null; then
    git branch -D "$branch" 2>/dev/null || true
    removed=$((removed + 1))
    printf 'pruned worktree: %s (%s)\n' "$wt_path" "$branch" >&2
  fi
done < <(git worktree list --porcelain | awk '
  /^worktree / { path=$2 }
  /^branch /   { print path "\t" $2; path=""; }
  /^detached/  { path=""; }
')

git worktree prune 2>/dev/null || true

# Prune loose local branches whose remote is [gone] and that no longer have a
# worktree. Catches squash-merged feature branches after GitHub auto-deletes
# the remote — they otherwise pile up locally forever.
wt_branches=$(git worktree list --porcelain 2>/dev/null | awk '/^branch / { sub(/^refs\/heads\//, "", $2); print $2 }')
branches_removed=0
while IFS= read -r b; do
  [ -z "$b" ] && continue
  printf '%s\n' "$wt_branches" | grep -Fxq "$b" && continue
  if git branch -D "$b" >/dev/null 2>&1; then
    branches_removed=$((branches_removed + 1))
    printf 'pruned branch: %s\n' "$b" >&2
  fi
done < <(git for-each-ref --format='%(refname:short) %(upstream:track)' refs/heads | awk '$NF == "[gone]" { print $1 }')

if [ $removed -gt 0 ] || [ $branches_removed -gt 0 ]; then
  msg=""
  if [ $removed -gt 0 ]; then
    msg="Pruned $removed stale worktree(s)"
  fi
  if [ $branches_removed -gt 0 ]; then
    if [ -n "$msg" ]; then
      msg="$msg and $branches_removed stale branch(es)"
    else
      msg="Pruned $branches_removed stale branch(es)"
    fi
  fi
  printf '{"systemMessage": "%s."}\n' "$msg"
fi

exit 0
