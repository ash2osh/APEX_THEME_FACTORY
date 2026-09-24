#!/usr/bin/env bash
# Export app 102 as split APEXLang into applications/ut (refreshes source from the live app).
set -euo pipefail
source "$(dirname "$0")/_env.sh"
mkdir -p "$ROOT/applications"
sql -S -name "$CONN" <<SQL
apex export -applicationid $APP_ID -exptype APEXLANG -split -dir "$ROOT/applications" -skipexportdate -overwrite-files
SQL
echo "exported to $APP_DIR ($(find "$APP_DIR" -type f | wc -l) files)"
