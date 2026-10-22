#!/bin/sh
# Copies the design tokens from the handoff (the single source of truth) into the web app, and the fonts they use.
# Run from web/: `bun run sync:tokens`. A Vitest test (src/common/theme/tokens.test.ts) fails if the copy drifts.
#
# The handoff's @font-face rules point at ../05-assets/fonts and are dropped here: the app loads the same
# files with next/font/local (src/common/theme/fonts.ts), which self-hosts them with hashed names.
set -eu

web_dir=$(cd "$(dirname "$0")/.." && pwd)
src="$web_dir/../Docs/design/01-design-system/tokens.css"
fonts="$web_dir/../Docs/design/05-assets/fonts"
out="$web_dir/src/common/theme"

{
  echo "/* Copied from Docs/design/01-design-system/tokens.css by scripts/sync-tokens.sh; do not edit by hand."
  echo "   @font-face rules are dropped: fonts load through next/font/local (fonts.ts). */"
  # Drop the @font-face lines and the file's own header comment, then any leading blank lines.
  grep -v '^@font-face' "$src" | sed '1,/\*\//d' | tr -d '\r' | sed '/./,$!d'
} > "$out/tokens.css"

mkdir -p "$out/fonts"
cp "$fonts"/*.woff2 "$fonts"/*-OFL.txt "$out/fonts/"
