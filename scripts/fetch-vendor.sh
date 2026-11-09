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

# macOS may have shasum instead of sha256sum
if command -v sha256sum >/dev/null; then sha256_of() { sha256sum "$1" | cut -d' ' -f1; }
else sha256_of() { shasum -a 256 "$1" | cut -d' ' -f1; }; fi

# SHA-256 of the Alpine.js $ALPINE_VERSION (3.17.2) files shipped to every consumer app, taken from the vendored
# copies in this repository. A different ALPINE_VERSION has no pinned digests and is refused.
ALPINE_PINNED_VERSION="3.17.2"
ALPINE_MIN_SHA256="abe5b75652884ce02c634ab1028b04758ec75fa874fd7a9bea1a0d97ebe5b2c3"
ALPINE_DEV_SHA256="c48454e6b315a7aaff67a4ea68a6651e4c7f9a196cc0aeb9cf9f34951b4a132c"
ALPINE_LICENSE_SHA256="08b7502da6e7aa1d0bbdc97d220fbf669b9366c61bd0f072238283c89bc4773a"

VENDOR="$ROOT/static-files/js/vendor"
mkdir -p "$VENDOR"

fetch() { # url dest [sha256]
  echo "  $1"
  curl -fsSL --max-time 60 "$1" -o "$2"
  if [[ -n "${3:-}" ]]; then
    local actual
    actual="$(sha256_of "$2")"
    if [[ "$actual" != "$3" ]]; then
      rm -f -- "$2"
      echo "fetch-vendor: SHA-256 mismatch for $1" >&2
      echo "  expected $3" >&2
      echo "  actual   $actual" >&2
      echo "  (bumping ALPINE_VERSION? update the pinned digests below after reviewing the new files)" >&2
      exit 1
    fi
  fi
}

if [[ "${1:-}" != "--reference" ]]; then
  if [[ "$ALPINE_VERSION" != "$ALPINE_PINNED_VERSION" ]]; then
    echo "fetch-vendor: no pinned SHA-256 for Alpine.js $ALPINE_VERSION (pinned: $ALPINE_PINNED_VERSION)." >&2
    echo "  Review the new release, then update ALPINE_PINNED_VERSION and the digests in this script." >&2
    exit 1
  fi
  echo "Alpine.js $ALPINE_VERSION -> $VENDOR"
  fetch "https://cdn.jsdelivr.net/npm/alpinejs@$ALPINE_VERSION/dist/cdn.min.js" "$VENDOR/alpine.min.js" "$ALPINE_MIN_SHA256"
  fetch "https://cdn.jsdelivr.net/npm/alpinejs@$ALPINE_VERSION/dist/cdn.js"     "$VENDOR/alpine.js" "$ALPINE_DEV_SHA256"
  fetch "https://raw.githubusercontent.com/alpinejs/alpine/v$ALPINE_VERSION/LICENSE.md" "$VENDOR/alpine.LICENSE.md" "$ALPINE_LICENSE_SHA256"
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

    vendored=("$ROOT"/static-files/js/vendor/*.js)
    [[ -e "${vendored[0]}" ]] || { echo "fetch-vendor: no vendored files in $VENDOR" >&2; exit 1; }
  {
    echo "# Fetched $(date -u +%Y-%m-%dT%H:%MZ) by scripts/fetch-vendor.sh"
    echo "alpinejs=$ALPINE_VERSION"
    echo "apex_origin=$APEX_ORIGIN ut=$UT_VERSION"
    command -v sha256sum >/dev/null && sha256=(sha256sum) || sha256=(shasum -a 256)
    (cd "$ROOT" && "${sha256[@]}" static-files/js/vendor/*.js .agents/knowledge/reference/ut-$UT_VERSION/*.{css,js})
  } > "$REF/MANIFEST.txt"
  echo "done; manifest: $REF/MANIFEST.txt"
done
