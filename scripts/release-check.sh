#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

theme_name="${1:-}"
if [[ -z "$theme_name" || "$theme_name" == -* ]]; then
  echo "Usage: release-check.sh <theme-name> [--evidence-dir <path>]" >&2
  exit 1
fi
shift

evidence_dir=".agents/evaluations/runtime"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --evidence-dir) evidence_dir="$2"; shift 2;;
    *) echo "Unknown option: $1" >&2; exit 1;;
  esac
done

bash tests/run-offline.sh
scripts/package-theme.sh "$theme_name" "dist/$theme_name"
theme_version="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "sample-themes/$theme_name/theme.json")"
zip_path="dist/$theme_name/$theme_name-$theme_version.zip"
python3 -m lib.theme_factory.cli verify-package --package "$zip_path"
python3 -m lib.theme_factory.release \
  --theme "$theme_name" \
  --package "$zip_path" \
  --evidence-dir "$evidence_dir" \
  --output "dist/$theme_name/RELEASE-REPORT.md"
