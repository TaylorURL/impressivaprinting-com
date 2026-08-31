#!/usr/bin/env bash
# Puts the Sunday binary at the one path every machine's hooks name, and loads
# the rule layers it reads.
#
# The hooks in settings.json are guarded on this exact path, so a machine
# without the binary runs none of them and says nothing about it. Cloud setup
# and every desk call this same script, so a container and a desk end up with
# the same binary reading the same layers.
set -u

bin="$HOME/.sunday/bin"
profile_src="${1:-}"
state="$HOME/.intelligence/state"
tried="$state/.sunday-install-tried"

# The binary being present is the whole gate. Reloading layers on a machine that
# already has them either duplicates a registration or fails on the name, and
# neither is worth a network call at every session start.
[ -x "$bin/sunday" ] && exit 0

os=$(uname -s | tr '[:upper:]' '[:lower:]')
case "$(uname -m)" in
  x86_64|amd64) arch=amd64 ;;
  arm64|aarch64) arch=arm64 ;;
  *) arch="" ;;
esac

# A failed fetch is stamped so a machine with no build for its architecture, or
# no route out, does not spend a network call on every session. The stamp
# expires rather than sticking, so a build published later still lands.
if [ -z "$arch" ]; then
  mkdir -p "$state" && : > "$tried"
  echo "No Sunday build for $os/$(uname -m); this machine keeps the guards it has."
  exit 0
fi

mkdir -p "$bin"
if ! curl -fsSL \
  "https://github.com/TaylorURL/sunday/releases/latest/download/sunday-$os-$arch" \
  -o "$bin/sunday.part"; then
  rm -f "$bin/sunday.part"
  mkdir -p "$state" && : > "$tried"
  echo "Sunday did not download; this machine keeps the guards it has."
  exit 0
fi

# A side name moved into place, so an interrupted fetch cannot leave a truncated
# file at the path the hooks exec.
chmod +x "$bin/sunday.part"
mv "$bin/sunday.part" "$bin/sunday"
rm -f "$tried"

"$bin/sunday" init || echo "sunday init failed; the wiring it writes is not in place."

"$bin/sunday" profile add \
  https://github.com/TaylorURL/sunday-standards.git standards \
  || echo "sunday standards not loaded."

# The private layer is generated into the mirror checkout by sunday-profile.py,
# and that checkout is not one of the paths the config sync installs, so the
# caller passes its location and the fallbacks cover the two places it sits.
for candidate in "$profile_src" "$HOME/intelligence/sunday-profile" \
                 "$HOME/.intelligence/sunday-profile"; do
  [ -n "$candidate" ] && [ -d "$candidate" ] || continue
  "$bin/sunday" profile add "$candidate" own || echo "the private profile did not load."
  break
done

case ":$PATH:" in
  *":$bin:"*) ;;
  *) printf '\nexport PATH="$HOME/.sunday/bin:$PATH"\n' >> "$HOME/.bashrc" 2>/dev/null || true ;;
esac

echo "Sunday $("$bin/sunday" version 2>/dev/null || echo unknown) wired."
