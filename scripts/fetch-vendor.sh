#!/usr/bin/env bash
# Fetch third-party runtime libraries and Universal Theme reference assets.
#   static-files/js/vendor/          -> shipped to app 102 as #APP_FILES# (runtime)
#   .agents/knowledge/reference/     -> read-only copies of the UT/Iris CSS+JS the app loads, for
#                                       offline token/selector discovery (spec §17). Never uploaded and
#                                       never committed (Oracle-copyrighted; gitignored).
#   scripts/fetch-vendor.sh              both
#   scripts/fetch-vendor.sh --reference  reference assets only (leaves the vendored Alpine.js alone)
#   UT_VERSION=26.2 scripts/fetch-vendor.sh --reference  one Universal Theme version only
set -euo pipefail
source "$(dirname "$0")/_env.sh"

ALPINE_VERSION="${ALPINE_VERSION:-3.17.2}"
APEX_ORIGIN="${APEX_ORIGIN:-http://localhost:8181}"
# Universal Theme versions to copy. Unset fetches both supported versions; UT_VERSION=26.2 fetches one.
UT_VERSIONS="${UT_VERSION:-26.1 26.2}"

VENDOR="$ROOT/static-files/js/vendor"
mkdir -p "$VENDOR"

fetch() { # url dest
  echo "  $1"
  curl -fsSL --max-time 60 "$1" -o "$2"
}

if [[ "${1:-}" != "--reference" ]]; then
  echo "Alpine.js $ALPINE_VERSION -> $VENDOR"
  fetch "https://cdn.jsdelivr.net/npm/alpinejs@$ALPINE_VERSION/dist/cdn.min.js" "$VENDOR/alpine.min.js"
  fetch "https://cdn.jsdelivr.net/npm/alpinejs@$ALPINE_VERSION/dist/cdn.js"     "$VENDOR/alpine.js"
  fetch "https://raw.githubusercontent.com/alpinejs/alpine/v$ALPINE_VERSION/LICENSE.md" "$VENDOR/alpine.LICENSE.md"
fi

for UT_VERSION in $UT_VERSIONS; do
  REF="$ROOT/.agents/knowledge/reference/ut-$UT_VERSION"
  mkdir -p "$REF"
  echo "Universal Theme $UT_VERSION reference assets from $APEX_ORIGIN -> $REF"
  fetch "$APEX_ORIGIN/i/themes/theme_42/$UT_VERSION/css/Core.min.css"          "$REF/Core.min.css"
  fetch "$APEX_ORIGIN/i/themes/theme_42/$UT_VERSION/css/Iris.min.css"          "$REF/Iris.min.css"
  fetch "$APEX_ORIGIN/i/themes/theme_42/$UT_VERSION/js/theme42.min.js"         "$REF/theme42.min.js"
  # APEX widget CSS: *consumes* the --a-* atoms (with light fallbacks) that Core/Iris declare. These paths are not
  # versioned, so they come from the APEX instance at APEX_ORIGIN; the manifest records which one that was.
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
done
