#!/usr/bin/env bash
# Copy repository static files (static-files/css, static-files/js) into the APEXLang export
# (applications/ut/shared-components/static-files/…) and register any new file in static-files.apx,
# so `apex import` uploads them as application static files (#APP_FILES#css/…, #APP_FILES#js/…).
# static-files/ stays the editing source; never edit the export copy by hand.
set -euo pipefail
source "$(dirname "$0")/_env.sh"
SRC="$ROOT/static-files"
DST="$APP_DIR/shared-components/static-files"
APX="$APP_DIR/shared-components/static-files.apx"

mime() {
  case "${1##*.}" in
    css) echo text/css ;; js) echo application/javascript ;; json|map) echo application/json ;;
    md) echo text/markdown ;; svg) echo image/svg+xml ;; png) echo image/png ;; *) echo application/octet-stream ;;
  esac
}

added=0; copied=0
while IFS= read -r -d '' f; do
  rel="${f#"$SRC"/}"
  case "$rel" in *README.md|*.about.css|*LICENSE*|js/vendor/alpine.js) continue ;; esac   # docs / readable build stay repo-only
  mkdir -p "$DST/$(dirname "$rel")"
  if ! cmp -s "$f" "$DST/$rel"; then cp "$f" "$DST/$rel"; copied=$((copied+1)); fi
  if ! grep -qF "file \"$rel\" (" "$APX"; then
    printf '\nfile "%s" (\n    mimeType: %s\n    charSet: utf-8\n)\n' "$rel" "$(mime "$rel")" >> "$APX"
    added=$((added+1))
  fi
done < <(find -H "$SRC/css" "$SRC/js" -type f -print0 | sort -z)   # -H: static-files/css is a symlink to the active theme
echo "sync-static: $copied file(s) copied, $added declaration(s) added to static-files.apx"
