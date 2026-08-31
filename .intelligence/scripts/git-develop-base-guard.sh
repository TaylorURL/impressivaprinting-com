#!/usr/bin/env bash
# Keeps feature branches based on origin/develop.
#
# The harness cuts worktrees from the repo's default branch (main), so a fresh
# worktree silently starts behind develop. Its PR then reintroduces already
# merged commits and conflicts on files develop has since changed. This runs as
# a hook so the fix does not depend on anyone remembering the rule.
#
#   session         SessionStart      detect and repair the current worktree
#   guard-pr        PreToolUse(Bash)  refuse `gh pr create` into develop from a
#                                     branch that is not based on develop
#   guard-worktree  PreToolUse        refresh refs before a worktree is made
#
# Repairs only ever move a branch forward onto develop. Anything that could
# lose work - a pushed branch, a conflicting stash - stops and reports instead.

set -uo pipefail

MODE="${1:-session}"

owned_repo() {
    local url
    url=$(git remote get-url origin 2>/dev/null) || return 1
    [[ "$url" == *"bradley-t-t/"* || "$url" == *"TaylorURL/"* ]]
}

in_repo() { git rev-parse --git-dir >/dev/null 2>&1; }

has_develop() { git rev-parse --verify --quiet origin/develop >/dev/null 2>&1; }

# True when origin/develop is already an ancestor of HEAD.
based_on_develop() { git merge-base --is-ancestor origin/develop HEAD 2>/dev/null; }

current_branch() { git branch --show-current 2>/dev/null; }

# A branch already published under its own name cannot be rewritten without a
# force push, so it is never repaired automatically. Deliberately not an
# upstream check: `git worktree add -b x origin/main` sets upstream to
# origin/main, which would make every fresh worktree look published.
is_pushed() {
    local b
    b=$(current_branch) || return 1
    [[ -n "$b" ]] && git rev-parse --verify --quiet "refs/remotes/origin/$b" >/dev/null 2>&1
}

case "$MODE" in
guard-pr)
    # stdin carries the tool call; only Bash `gh pr create` is interesting.
    payload=$(cat 2>/dev/null || true)
    case "$payload" in
    *"gh pr create"*) ;;
    *) exit 0 ;;
    esac
    # Only PRs targeting develop. `/merge` opens develop -> main legitimately,
    # and a hotfix may target main; neither should be blocked.
    case "$payload" in
    *"--base develop"* | *"--base=develop"*) ;;
    *"--base"*) exit 0 ;;
    *) ;;
    esac
    # The command often carries its own working directory (`cd <path> && gh pr
    # create …`) while this hook runs in the session's directory. Judge the
    # repo the command targets, or the check reads a different checkout's HEAD.
    # The command is pulled out of the JSON payload first. Matching against the
    # raw payload trips over JSON escape sequences, so a multi-line command
    # yields no working directory and the hook silently judges whatever
    # checkout the session happens to be standing in.
    if command -v jq >/dev/null 2>&1; then
        cmdtext=$(jq -r '.tool_input.command // empty' <<<"$payload" 2>/dev/null)
    else
        cmdtext=$payload
    fi
    # The `cd` is rarely at the start of a line: `cd /path && gh pr create` and
    # `A=x && cd "$A" && gh pr create` are both ordinary. Collect every `cd` that
    # stands as a command word and keep the last that names a real directory.
    workdir=""
    saw_cd=0
    while IFS= read -r cand; do
        saw_cd=1
        d=${cand#*cd }
        d="${d%\"}"; d="${d#\"}"; d="${d%\'}"; d="${d#\'}"
        d="${d%"${d##*[![:space:]]}"}"
        d="${d/#\~/$HOME}"
        [[ -d "$d" ]] && workdir=$d
    done < <(printf '%s' "$cmdtext" | grep -oE '(^|&&|;|\|)[[:space:]]*cd[[:space:]]+[^&;|]+' | sed -E 's/^[^c]*//')

    # A `cd` through a shell variable cannot be expanded here. Judging the
    # session's directory instead blocks a landing in one repo over the state of
    # another; declining leaves the same check to CI, which runs it anyway.
    if [[ $saw_cd -eq 1 && -z "$workdir" ]]; then
        exit 0
    fi
    if [[ -n "$workdir" ]]; then
        cd "$workdir" 2>/dev/null || exit 0
    fi
    in_repo || exit 0
    owned_repo || exit 0
    # When --repo names a repo other than the one this check landed in, HEAD
    # here says nothing about the branch being pushed, and judging it would
    # block a legitimate PR over whatever is checked out somewhere else.
    target=$(printf '%s' "$payload" | sed -n 's/.*--repo[ =]\{1,\}\([A-Za-z0-9._-]\{1,\}\/[A-Za-z0-9._-]\{1,\}\).*/\1/p')
    if [[ -n "$target" ]]; then
        origin=$(git remote get-url origin 2>/dev/null)
        case "$origin" in
        *"/$target" | *"/$target.git" | *":$target" | *":$target.git") ;;
        *) exit 0 ;;
        esac
    fi
    has_develop || exit 0
    git fetch --quiet origin develop >/dev/null 2>&1
    if ! based_on_develop; then
        branch=$(current_branch)
        {
            echo "BLOCKED: '${branch}' is not based on origin/develop."
            echo
            echo "Opening this PR into develop would reintroduce already merged"
            echo "commits and conflict on files develop has since changed."
            echo
            echo "Commits this branch would carry that develop does not have:"
            git log --oneline origin/develop..HEAD 2>/dev/null | head -20
            echo
            echo "Rebase first, then reopen the PR:"
            echo "  git rebase --onto origin/develop \$(git merge-base origin/develop HEAD)"
        } >&2
        exit 2
    fi
    exit 0
    ;;

guard-worktree)
    in_repo || exit 0
    owned_repo || exit 0
    git fetch --quiet origin develop main >/dev/null 2>&1
    exit 0
    ;;

session) ;;
*) exit 0 ;;
esac

in_repo || exit 0
owned_repo || exit 0

git fetch --quiet origin develop main >/dev/null 2>&1
has_develop || exit 0

BRANCH=$(current_branch)

# Protected branches are managed by the PR flow, not repaired here.
if [[ -z "$BRANCH" || "$BRANCH" == "main" || "$BRANCH" == "develop" ]]; then
    exit 0
fi

based_on_develop && exit 0

BEHIND=$(git rev-list --count "HEAD..origin/develop" 2>/dev/null || echo 0)

# Only commits absent from BOTH develop and main are this branch's own work. A
# worktree cut from main inherits main's merge and squash commits; replaying
# those onto develop reintroduces already merged content and conflicts.
OWN=$(git rev-list --count HEAD --not origin/develop origin/main 2>/dev/null || echo 0)

# Replay from whichever of the two bases is later in history, so the smallest
# possible set of commits moves.
rebase_base() {
    local mb db
    mb=$(git merge-base origin/main HEAD 2>/dev/null) || return 1
    db=$(git merge-base origin/develop HEAD 2>/dev/null) || return 1
    if git merge-base --is-ancestor "$mb" "$db" 2>/dev/null; then
        echo "$db"
    else
        echo "$mb"
    fi
}

if is_pushed; then
    cat <<EOF
GIT BASE WARNING: '${BRANCH}' is not based on origin/develop (behind by ${BEHIND} commits).

It is already pushed, so it was not repaired automatically - rebasing would need
a force push. Fix it before opening a PR into develop:

  git rebase --onto origin/develop \$(git merge-base origin/develop HEAD)
  git push --force-with-lease
EOF
    exit 0
fi

DIRTY=0
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    DIRTY=1
    if ! git stash push -u -q -m "develop-base-guard" >/dev/null 2>&1; then
        echo "GIT BASE WARNING: '${BRANCH}' is not based on origin/develop and its"
        echo "changes could not be stashed, so it was left alone. Rebase manually"
        echo "before opening a PR into develop."
        exit 0
    fi
fi

REPAIRED=0
if [[ "$OWN" -eq 0 ]]; then
    git reset --hard -q origin/develop >/dev/null 2>&1 && REPAIRED=1
else
    if git rebase --onto origin/develop "$(rebase_base)" -q >/dev/null 2>&1; then
        REPAIRED=1
    else
        git rebase --abort >/dev/null 2>&1
    fi
fi

if [[ "$DIRTY" -eq 1 ]]; then
    if ! git stash pop -q >/dev/null 2>&1; then
        # git keeps the stash when a pop conflicts, so the work is not at risk.
        # Clear the conflicted index; leaving it would break every later command.
        if [[ -n "$(git stash list 2>/dev/null)" ]]; then
            git reset --hard -q HEAD >/dev/null 2>&1
        fi
        cat <<EOF
GIT BASE WARNING: '${BRANCH}' was rebased onto origin/develop, but your
uncommitted changes conflicted and could NOT be reapplied cleanly.

They are safe in the stash - nothing was discarded. Recover them with:

  git stash list
  git stash pop

Resolve the conflicts before continuing.
EOF
        exit 0
    fi
fi

if [[ "$REPAIRED" -eq 1 ]]; then
    cat <<EOF
Git base: '${BRANCH}' was cut from the wrong branch (behind origin/develop by
${BEHIND} commits) and has been rebased onto origin/develop automatically.
Uncommitted changes were preserved.

develop had moved on, so re-read any file you are about to edit rather than
trusting earlier context - the surrounding content may have changed.
EOF
else
    cat <<EOF
GIT BASE WARNING: '${BRANCH}' is not based on origin/develop (behind by ${BEHIND}
commits) and could not be rebased automatically. Fix it before opening a PR:

  git rebase --onto origin/develop \$(git merge-base origin/develop HEAD)
EOF
fi

exit 0
