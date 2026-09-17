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
# A charSet only means something for text content; APEX ignores it for binaries, but declaring one
# anyway is a false statement in generated source (plan Task 5). image/svg+xml is XML text, unlike
# the other image/* types here, so it keeps a charSet.
is_text_mime() { case "$1" in text/*|application/javascript|application/json|image/svg+xml) return 0;; *) return 1;; esac; }

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
  local f="$1" rel="$2" m want status; wanted["$rel"]=1
  m="$(mime "$rel")"
  mkdir -p "$DST/$(dirname "$rel")"
  if ! cmp -s "$f" "$DST/$rel"; then cp "$f" "$DST/$rel"; copied=$((copied+1)); fi
  if is_text_mime "$m"; then
    printf -v want 'file "%s" (\n    mimeType: %s\n    charSet: utf-8\n)' "$rel" "$m"
  else
    printf -v want 'file "%s" (\n    mimeType: %s\n)' "$rel" "$m"
  fi
  # Reconcile a registration that has drifted from what this file should look like now - e.g. a
  # charSet left over from before its mimeType classification changed here - not just add files
  # never registered at all. A no-op when the existing block already matches, so an unchanged file
  # doesn't get needlessly reordered to the end on every run.
  status="$(python3 - "$APX" "$rel" "$want" <<'PY'
import re, sys
apx_path, rel, want = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(apx_path, encoding="utf-8").read()
pattern = re.compile(r'file "' + re.escape(rel) + r'" \(\n(?:    [^\n]*\n)*\)')
match = pattern.search(text)
if match and match.group(0) == want:
    print("same"); sys.exit(0)
if match:
    text = pattern.sub('', text, count=1)
    text = re.sub(r'\n{3,}', '\n\n', text)
text = text.rstrip('\n') + '\n\n' + want + '\n'
open(apx_path, 'w', encoding='utf-8').write(text)
print("new" if not match else "changed")
PY
)"
  if [[ "$status" == "new" ]]; then added=$((added+1)); fi
}
while IFS= read -r -d '' f; do rel="${f#"$SRC"/}"
  case "$rel" in *README.md|*/.about*|*LICENSE*|js/vendor/alpine.js) continue;; esac
  sync_one "$f" "$rel"
done < <(find "$SRC/css" "$SRC/js" -type f -print0 | sort -z)
for t in "${themes[@]}"; do
  # A package with custom fonts needs its @font-face block here too. The package build generates that
  # block into the distributable theme.css; the app's copy is assembled from source, so without this it
  # would declare no faces, ship no WOFF2 files, and silently fall back to the system stack.
  font_css="$(python3 "$ROOT/scripts/_font-css.py" "$ROOT" "$t")"
  while IFS= read -r -d '' f; do
    rel="css/themes/$t/${f#"$THEMES/$t/css/"}"
    if [[ -n "$font_css" && "$f" == "$THEMES/$t/css/theme.css" ]]; then
      tmp="$(mktemp)"; { cat "$f"; printf '\n'; printf '%s\n' "$font_css"; } > "$tmp"
      sync_one "$tmp" "$rel"; rm -f "$tmp"
    else
      sync_one "$f" "$rel"
    fi
  done < <(find "$THEMES/$t/css" -type f -print0 | sort -z)
  if [[ -n "$font_css" && -d "$THEMES/$t/fonts" ]]; then
    while IFS= read -r -d '' f; do sync_one "$f" "css/themes/$t/fonts/$(basename "$f")"; done \
      < <(find "$THEMES/$t/fonts" -type f -name '*.woff2' -print0 | sort -z)
  fi
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
