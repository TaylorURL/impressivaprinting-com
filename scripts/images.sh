#!/usr/bin/env bash
# Builds the WebP and AVIF derivatives every photo on the site is offered in,
# at the two widths the layouts ask for. Re-run after adding or replacing a
# photograph in public/work or public/categories.
#
# Needs cwebp (brew install webp); AVIF comes from macOS sips.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)/public"
cd "$root"

derive() {
  local src="$1" stem="${1%.*}" width
  for width in 400 800; do
    local scaled="/tmp/impressiva-derive-$width.png"
    sips -Z "$width" "$src" --out "$scaled" >/dev/null
    cwebp -quiet -q 76 "$scaled" -o "${stem}-${width}.webp"
    sips -s format avif -s formatOptions 55 "$scaled" --out "${stem}-${width}.avif" >/dev/null
    rm -f "$scaled"
  done
}

for file in work/*.jpg categories/*.jpg; do
  derive "$file"
done

for width in 560 1200; do
  scaled="/tmp/impressiva-logo-$width.png"
  sips -Z "$width" logo.png --out "$scaled" >/dev/null
  cwebp -quiet -q 82 -alpha_q 90 "$scaled" -o "logo-${width}.webp"
  sips -s format avif -s formatOptions 60 "$scaled" --out "logo-${width}.avif" >/dev/null
  rm -f "$scaled"
done
