#!/usr/bin/env bash
# Import applications/ut into app 102 (overwrites the live app). A failed `apex validate` does not stop a
# SQLcl script (pitfalls §4.4), so a separate text-checked validate gates it; then validate + import run in ONE session.
set -euo pipefail
source "$(dirname "$0")/_env.sh"
if [[ "${1:-}" != "--yes" ]]; then
  read -r -p "This overwrites application $APP_ID in workspace $WORKSPACE from $APP_DIR. Continue? [y/N] " a
  [[ "$a" == "y" || "$a" == "Y" ]] || { echo "aborted"; exit 1; }
fi
# `apex import` ships whatever is on disk: refuse a stale static-file assembly (README "See it in the reference app").
PYTHONPATH="$ROOT" python3 -m lib.theme_factory.sync_static --repo-root "$ROOT" --check >/dev/null \
  || { echo "apex-import: static files are out of date - run scripts/sync-static.sh first; nothing imported" >&2; exit 1; }
"$ROOT/scripts/apex-validate.sh" || { echo "apex-import: validation failed - nothing imported" >&2; exit 1; }
sql -S -name "$CONN" <<SQL
whenever sqlerror exit failure
apex validate -input "$APP_DIR" -workspace "$WORKSPACE"
apex import -input "$APP_DIR" -workspace "$WORKSPACE"
SQL
