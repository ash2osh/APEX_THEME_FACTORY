#!/usr/bin/env bash
# Compile-check applications/ut against the DEMO workspace. Exit 1 unless "Validation successful."
set -euo pipefail
source "$(dirname "$0")/_env.sh"
out=$(sql -S -name "$CONN" <<SQL
apex validate -input $APP_DIR -workspace $WORKSPACE
SQL
)
echo "$out"
grep -q "Validation successful" <<<"$out"
