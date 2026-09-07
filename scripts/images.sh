#!/usr/bin/env bash
# Builds the WebP and AVIF derivatives every photo on the site is offered in,
# at the widths the layouts ask for. Re-run after adding or replacing a
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

# The wordmark carries a third width because the hero prints it the full width
# of a phone: between 560 and 1200 there is nothing a 390 to 430 point screen
# can use, so it takes the 1200 and throws most of it away.
for width in 560 800 1200; do
  scaled="/tmp/impressiva-logo-$width.png"
  sips -Z "$width" logo.png --out "$scaled" >/dev/null
  cwebp -quiet -q 82 -alpha_q 90 "$scaled" -o "logo-${width}.webp"
  sips -s format avif -s formatOptions 60 "$scaled" --out "logo-${width}.avif" >/dev/null
  rm -f "$scaled"
done

# The faces are vendored rather than built, so a fresh drop from the foundry
# arrives carrying everything. These are the cuts that take one back down to
# what the site can render, recorded beside the images so a replacement does
# not quietly reinstate the rest. Run them from src/fonts after dropping a new
# file in; they need fonttools with brotli.
#
# They live under src rather than in public because a file in public keeps its
# name forever and one under src is emitted with a hash of its own bytes, and
# the host is told to cache these for a year. A face served from a name that
# does not move when its bytes do is a year a corrected file cannot reach
# anyone who already has the old one.
#
# Inter and Archivo ship the whole 100 to 900 axis and nothing in the project
# asks for a weight outside 400 to 800, so the axis is narrowed to that range.
# Every weight the design sets still interpolates from the same masters.
#
#   python3 -m fontTools.varLib.instancer inter-variable.woff2 wght=400:800 -o inter-variable.woff2
#   python3 -m fontTools.varLib.instancer archivo-variable.woff2 wght=400:800 -o archivo-variable.woff2
#
# Anton reaches text through the .display class alone, and that class sets
# text-transform: uppercase, so a lowercase codepoint whose uppercase form is
# also in the file can never be drawn. Those are the only ones dropped, which
# is why the range below reads as the file's own coverage with the letters cut
# out of it: every punctuation mark, symbol, currency sign and accented capital
# stays, because a future line of copy may well reach one.
#
#   python3 -m fontTools.subset anton-400-normal.woff2 --output-file=anton-400-normal.woff2 \
#     --flavor=woff2 --layout-features='*' --unicodes="U+0000,U+000D,U+0020-0060,U+007B-007E,\
#     U+00A0-00DE,U+00F7,U+00FF,U+0152,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0300-0301,U+0303-0304,\
#     U+0308-0309,U+0323,U+0329,U+2009,U+200B,U+2013-2014,U+2018-201A,U+201C-201E,U+2022,U+2026,\
#     U+2032-2033,U+2039-203A,U+2044,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215"
