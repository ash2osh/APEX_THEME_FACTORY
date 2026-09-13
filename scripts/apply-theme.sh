#!/usr/bin/env bash
# Make sample-themes/<name>/css the active application CSS (static-files/css symlink).
# Follow with scripts/sync-static.sh and scripts/apex-import.sh to push it to app 102.
set -euo pipefail
source "$(dirname "$0")/_env.sh"
name="${1:?usage: apply-theme.sh <theme-name>  (see sample-themes/)}"
src="$ROOT/sample-themes/$name/css"
[[ -d "$src" ]] || { echo "no such theme: $src" >&2; exit 1; }
ln -sfn "../sample-themes/$name/css" "$ROOT/static-files/css"
echo "static-files/css -> $(readlink "$ROOT/static-files/css")"
