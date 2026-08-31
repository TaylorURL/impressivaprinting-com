#!/usr/bin/env bash
# Refuses `gh pr create` into develop when the project version has not moved.
#
# Every PR into develop carries one version bump, so develop always reads as a
# distinct, increasing version and main inherits it on promotion. This runs as
# a PreToolUse hook so the rule does not depend on anyone remembering it; the
# same gate runs in CI as the "Version moved on" step, which catches PRs opened
# from anywhere this hook is not.
#
#   guard-pr   PreToolUse(Bash)   block `gh pr create --base develop` when the
#                                 manifest version equals origin/develop's

set -uo pipefail

MODE="${1:-guard-pr}"
[[ "$MODE" == "guard-pr" ]] || exit 0

payload=$(cat 2>/dev/null || true)
case "$payload" in *"gh pr create"*) ;; *) exit 0 ;; esac
case "$payload" in
*"--base develop"* | *"--base=develop"*) ;;
*) exit 0 ;;
esac

if command -v jq >/dev/null 2>&1; then
    cmdtext=$(jq -r '.tool_input.command // empty' <<<"$payload" 2>/dev/null)
else
    cmdtext=$payload
fi
# The command usually carries its own working directory, and it is rarely at the
# start of a line: `cd /path && gh pr create` and `A=x && cd "$A" && gh pr create`
# are both ordinary. Collect every `cd` that stands as a command word, in order,
# and keep the last one that names a real directory.
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

# A `cd` written through a shell variable cannot be expanded from here. Judging
# the session's directory instead means blocking a landing in one repo over the
# version in another. The same check runs in CI on the pull
# request, so declining to judge costs nothing and guessing does.
if [[ $saw_cd -eq 1 && -z "$workdir" ]]; then
    exit 0
fi
if [[ -n "$workdir" ]]; then
    cd "$workdir" 2>/dev/null || exit 0
fi

git rev-parse --git-dir >/dev/null 2>&1 || exit 0
url=$(git remote get-url origin 2>/dev/null) || exit 0
[[ "$url" == *"bradley-t-t/"* || "$url" == *"TaylorURL/"* ]] || exit 0
target=$(printf '%s' "$payload" | sed -n 's/.*--repo[ =]\{1,\}\([A-Za-z0-9._-]\{1,\}\/[A-Za-z0-9._-]\{1,\}\).*/\1/p')
if [[ -n "$target" ]]; then
    case "$url" in *"/$target" | *"/$target.git" | *":$target" | *":$target.git") ;; *) exit 0 ;; esac
fi
git rev-parse --verify --quiet origin/develop >/dev/null 2>&1 || exit 0
git fetch --quiet origin develop >/dev/null 2>&1

# The manifest decides whether the project is versioned at all.
read_version() { # <ref-or-empty> <file>
    local ref="$1" file="$2" text
    if [[ -n "$ref" ]]; then text=$(git show "$ref:$file" 2>/dev/null) || return 1; else text=$(cat "$file" 2>/dev/null) || return 1; fi
    case "$file" in
    package.json) printf '%s' "$text" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("version",""))' 2>/dev/null ;;
    pom.xml) printf '%s' "$text" | python3 -c 'import re,sys; m=re.search(r"<version>([^<]+)</version>", sys.stdin.read()); print(m.group(1) if m else "")' 2>/dev/null ;;
    gradle.properties) printf '%s' "$text" | sed -n 's/^version[[:space:]]*=[[:space:]]*//p' | head -1 ;;
    esac
}
manifest=""
for f in package.json pom.xml gradle.properties; do
    if [[ -f "$f" ]] || git cat-file -e "origin/develop:$f" 2>/dev/null; then manifest=$f; break; fi
done
[[ -n "$manifest" ]] || exit 0
base=$(read_version origin/develop "$manifest")

# `gh pr create --head <branch>` names the branch being proposed, and that
# branch is often checked out somewhere other than here - a worktree, or a
# machine this command is relayed to. Read the manifest from the ref when one
# is named, so the comparison is against the branch rather than whatever tree
# the command happened to start in.
head_ref=$(printf '%s' "$cmdtext" | sed -n 's/.*--head[ =]\{1,\}\([A-Za-z0-9._\/-]\{1,\}\).*/\1/p')
head=""
if [[ -n "$head_ref" ]]; then
    for candidate in "origin/$head_ref" "$head_ref"; do
        if git rev-parse --verify --quiet "$candidate" >/dev/null 2>&1; then
            head=$(read_version "$candidate" "$manifest")
            [[ -n "$head" ]] && break
        fi
    done
fi
[[ -n "$head" ]] || head=$(read_version "" "$manifest")
[[ -n "$base" ]] || exit 0

newer=$(python3 - "$base" "$head" <<'PY'
import re, sys
def parts(v): return [int(x) if x.isdigit() else x for x in re.split(r"[.+-]", v) if x != ""]
b, h = parts(sys.argv[1]), (parts(sys.argv[2]) if sys.argv[2] else [])
if not h: print("no"); sys.exit()
for x, y in zip(h + [0]*len(b), b + [0]*len(h)):
    if x == y: continue
    if isinstance(x, int) and isinstance(y, int): print("yes" if x > y else "no")
    else: print("yes" if str(x) > str(y) else "no")
    sys.exit()
print("no")
PY
)
if [[ "$manifest" == "package.json" ]]; then
    rel=""
    if [[ -n "$head_ref" ]]; then
        for candidate in "origin/$head_ref" "$head_ref"; do
            if git cat-file -e "$candidate:public/release.json" 2>/dev/null; then
                rel=$(git show "$candidate:public/release.json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("version",""))' 2>/dev/null)
                break
            fi
        done
    fi
    if [[ -z "$rel" && -f public/release.json ]]; then
        rel=$(python3 -c 'import json; print(json.load(open("public/release.json")).get("version",""))' 2>/dev/null)
    fi
    if [[ -n "$rel" && "$rel" != "$head" ]]; then
        {
            echo "BLOCKED: public/release.json says ${rel} but package.json says ${head}."
            echo
            echo "The app reports its version from release.json, so it would announce an"
            echo "older version than the manifest. Move the version the project's own way:"
            echo "  ~/.intelligence/tools/bump-version.py"
        } >&2
        exit 2
    fi
fi
if [[ "$newer" != "yes" ]]; then
    {
        echo "BLOCKED: the version has not moved on for this PR into develop."
        echo
        echo "  $manifest on origin/develop: ${base}"
        echo "  $manifest on this branch:    ${head:-none}"
        echo
        echo "Every PR into develop carries one version bump. Bump it, fold the"
        echo "change into the commit, then reopen the PR:"
        case "$manifest" in
        package.json) echo "  npm version patch --no-git-tag-version   (minor for new functionality)" ;;
        pom.xml) echo "  edit the <version> in pom.xml one step up" ;;
        gradle.properties) echo "  edit version= in gradle.properties one step up" ;;
        esac
    } >&2
    exit 2
fi
exit 0
