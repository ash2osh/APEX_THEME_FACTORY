#!/usr/bin/env bash
# Validate and import applications/ut into app 102 in ONE SQLcl session (overwrites the live app).
set -euo pipefail
source "$(dirname "$0")/_env.sh"
if [[ "${1:-}" != "--yes" ]]; then
  read -r -p "This overwrites application $APP_ID in workspace $WORKSPACE from $APP_DIR. Continue? [y/N] " a
  [[ "$a" == "y" || "$a" == "Y" ]] || { echo "aborted"; exit 1; }
fi
sql -S -name "$CONN" <<SQL
whenever sqlerror exit failure
apex validate -input $APP_DIR -workspace $WORKSPACE
apex import -input $APP_DIR -workspace $WORKSPACE
SQL
