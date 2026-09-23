#!/usr/bin/env bash
# Fetch third-party runtime libraries and Universal Theme reference assets.
#   static-files/js/vendor/          -> shipped to app 102 as #APP_FILES# (runtime)
#   .agents/knowledge/reference/     -> read-only copies of the UT/Iris CSS+JS the app loads, for
#                                       offline token/selector discovery (spec §17). Never uploaded.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

ALPINE_VERSION="${ALPINE_VERSION:-3.17.2}"
APEX_ORIGIN="${APEX_ORIGIN:-http://localhost:8181}"
UT_VERSION="${UT_VERSION:-26.1}"

VENDOR="$ROOT/static-files/js/vendor"
REF="$ROOT/.agents/knowledge/reference/ut-$UT_VERSION"
mkdir -p "$VENDOR" "$REF"

fetch() { # url dest
  echo "  $1"
  curl -fsSL --max-time 60 "$1" -o "$2"
}

echo "Alpine.js $ALPINE_VERSION -> $VENDOR"
fetch "https://cdn.jsdelivr.net/npm/alpinejs@$ALPINE_VERSION/dist/cdn.min.js" "$VENDOR/alpine.min.js"
fetch "https://cdn.jsdelivr.net/npm/alpinejs@$ALPINE_VERSION/dist/cdn.js"     "$VENDOR/alpine.js"
fetch "https://raw.githubusercontent.com/alpinejs/alpine/v$ALPINE_VERSION/LICENSE.md" "$VENDOR/alpine.LICENSE.md"

echo "Universal Theme $UT_VERSION reference assets from $APEX_ORIGIN -> $REF"
fetch "$APEX_ORIGIN/i/themes/theme_42/$UT_VERSION/css/Core.min.css"          "$REF/Core.min.css"
fetch "$APEX_ORIGIN/i/themes/theme_42/$UT_VERSION/css/Iris.min.css"          "$REF/Iris.min.css"
fetch "$APEX_ORIGIN/i/themes/theme_42/$UT_VERSION/js/theme42.min.js"         "$REF/theme42.min.js"
# APEX widget CSS: *consumes* the --a-* atoms (with light fallbacks) that Core/Iris declare — needed to see
# which atom a component reads and what it falls back to (e.g. --a-gv-pagination-button-selected-background-color)
fetch "$APEX_ORIGIN/i/app_ui/css/Core.min.css"                               "$REF/app_ui-Core.min.css"
fetch "$APEX_ORIGIN/i/app_ui/css/Theme-Standard.min.css"                     "$REF/app_ui-Theme-Standard.min.css"
fetch "$APEX_ORIGIN/i/libraries/font-apex/2.5.1/css/font-apex.min.css"       "$REF/font-apex-2.5.1.min.css"
fetch "$APEX_ORIGIN/i/libraries/oracle-fonts/oraclesans-apex.min.css"        "$REF/oraclesans-apex.min.css"

{
  echo "# Fetched $(date -u +%Y-%m-%dT%H:%MZ) by scripts/fetch-vendor.sh"
  echo "alpinejs=$ALPINE_VERSION"
  echo "apex_origin=$APEX_ORIGIN ut=$UT_VERSION"
  (cd "$ROOT" && sha256sum static-files/js/vendor/*.js .agents/knowledge/reference/ut-$UT_VERSION/*.{css,js})
} > "$REF/MANIFEST.txt"
echo "done; manifest: $REF/MANIFEST.txt"
