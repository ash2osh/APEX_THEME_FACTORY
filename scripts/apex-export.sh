#!/usr/bin/env bash
# Export app 102 as split APEXLang into applications/ut (refreshes source from the live app).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
mkdir -p "$ROOT/applications"
sql -S -name "$CONN" <<SQL
apex export -applicationid $APP_ID -exptype APEXLANG -split -dir "$ROOT/applications" -skipexportdate -overwrite-files
SQL
exported="$(find "$APP_DIR" -type f 2>/dev/null | wc -l)"
if (( exported == 0 )); then
  echo "apex-export: the export produced no files in $APP_DIR (check the connection '$CONN' and application $APP_ID)" >&2
  exit 1
fi
echo "exported to $APP_DIR ($exported files)"
