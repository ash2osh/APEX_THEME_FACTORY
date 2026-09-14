#!/usr/bin/env bash
# Assemble the application static files into the APEXLang export so `apex import` uploads them:
#   static-files/css/**, static-files/js/**        -> applications/ut/shared-components/static-files/css|js/**
#   sample-themes/<name>/css/**                     -> …/static-files/css/themes/<name>/**
#   sample-themes/<name>/theme.json                 -> …/static-files/css/themes/<name>/theme.json  (theme switcher
#   sample-themes/<name>/preview/cover.jpg          -> …/static-files/css/themes/<name>/cover.jpg    and page 405 read these)
# Also (1) regenerates the @themes block in static-files/css/app.css from sample-themes/*/theme.json,
# (2) registers every synced file in static-files.apx, (3) prunes export files under css/ and js/ that no
# longer have a source. Sources are the only editable copies; never edit the export by hand.
set -euo pipefail
source "$(dirname "$0")/_env.sh"
SRC="$ROOT/static-files"
THEMES="$ROOT/sample-themes"
DST="$APP_DIR/shared-components/static-files"
APX="$APP_DIR/shared-components/static-files.apx"
APPCSS="$SRC/css/app.css"

mime() { case "${1##*.}" in css) echo text/css;; js) echo application/javascript;; json|map) echo application/json;;
         svg) echo image/svg+xml;; png) echo image/png;; jpg|jpeg) echo image/jpeg;; woff2) echo font/woff2;;
         *) echo application/octet-stream;; esac; }

# (1) themes block in app.css
themes=(); for j in "$THEMES"/*/theme.json; do [[ -f "$j" ]] && themes+=("$(basename "$(dirname "$j")")"); done
block="/* @themes:start */"; for t in "${themes[@]}"; do block+=$'\n'"@import \"themes/$t/theme.css\";"; done; block+=$'\n'"/* @themes:end */"
python3 - "$APPCSS" "$block" <<'PY'
import re,sys; p,block=sys.argv[1],sys.argv[2]; s=open(p).read()
s2=re.sub(r'/\* @themes:start \*/.*?/\* @themes:end \*/', block, s, flags=re.S)
open(p,'w').write(s2) if s2!=s else None
PY

# (2) copy + register
declare -A wanted; copied=0; added=0
sync_one() { # src-file rel-dest
  local f="$1" rel="$2"; wanted["$rel"]=1
  mkdir -p "$DST/$(dirname "$rel")"
  if ! cmp -s "$f" "$DST/$rel"; then cp "$f" "$DST/$rel"; copied=$((copied+1)); fi
  if ! grep -qF "file \"$rel\" (" "$APX"; then
    printf '\nfile "%s" (\n    mimeType: %s\n    charSet: utf-8\n)\n' "$rel" "$(mime "$rel")" >> "$APX"; added=$((added+1)); fi
}
while IFS= read -r -d '' f; do rel="${f#"$SRC"/}"
  case "$rel" in *README.md|*/.about*|*LICENSE*|js/vendor/alpine.js) continue;; esac
  sync_one "$f" "$rel"
done < <(find "$SRC/css" "$SRC/js" -type f -print0 | sort -z)
for t in "${themes[@]}"; do
  while IFS= read -r -d '' f; do sync_one "$f" "css/themes/$t/${f#"$THEMES/$t/css/"}"; done < <(find "$THEMES/$t/css" -type f -print0 | sort -z)
  sync_one "$THEMES/$t/theme.json" "css/themes/$t/theme.json"          # title/tagline for the switcher + gallery
  if [[ -f "$THEMES/$t/preview/cover.jpg" ]]; then sync_one "$THEMES/$t/preview/cover.jpg" "css/themes/$t/cover.jpg"; fi
done

# (3) prune
pruned=0
while IFS= read -r -d '' f; do rel="${f#"$DST"/}"
  if [[ -z "${wanted[$rel]:-}" ]]; then rm "$f"; pruned=$((pruned+1))
    python3 - "$APX" "$rel" <<'PY'
import re,sys; p,rel=sys.argv[1],sys.argv[2]; s=open(p).read()
s=re.sub(r'\n*file "'+re.escape(rel)+r'" \(\n(?:    .*\n)*\)\n', '\n', s); open(p,'w').write(s)
PY
  fi
done < <(find "$DST/css" "$DST/js" -type f -print0 2>/dev/null | sort -z)
find "$DST/css" "$DST/js" -type d -empty -delete 2>/dev/null || true
echo "sync-static: themes=[${themes[*]}] copied=$copied registered=$added pruned=$pruned"
