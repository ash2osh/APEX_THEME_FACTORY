#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

theme_name="${1:-}"
if [[ -z "$theme_name" || "$theme_name" == -* ]]; then
  echo "Usage: release-check.sh <theme-name> [--evidence-dir <path>] [--skip-common-offline --common-check-artifact <path>]" >&2
  exit 1
fi
shift

evidence_dir=".agents/evaluations/runtime"
skip_common_offline=false
common_check_artifact=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --evidence-dir) evidence_dir="$2"; shift 2;;
    --skip-common-offline) skip_common_offline=true; shift;;
    --common-check-artifact) common_check_artifact="$2"; shift 2;;
    *) echo "Unknown option: $1" >&2; exit 1;;
  esac
done

if [[ "$skip_common_offline" == true ]]; then
  if [[ -z "$common_check_artifact" ]]; then
    echo "--skip-common-offline requires --common-check-artifact" >&2
    exit 2
  fi
  python3 - "$common_check_artifact" <<'PY'
import sys
from pathlib import Path
from lib.theme_factory.evidence_cache import common_check_artifact_valid

diagnostics = []
if not common_check_artifact_valid(Path(sys.argv[1]), diagnostics=diagnostics):
    print("Invalid common-check artifact: " + "; ".join(diagnostics), file=sys.stderr)
    raise SystemExit(2)
PY
else
  if [[ -n "$common_check_artifact" ]]; then
    echo "--common-check-artifact is only valid with --skip-common-offline" >&2
    exit 2
  fi
  bash tests/run-common-offline.sh
fi
scripts/package-theme.sh "$theme_name" "dist/$theme_name"
# Theme release evidence is deliberately limited to Layers A-D.  Project-level agent
# compatibility is validated separately by scripts/agent-compatibility-check.sh.
theme_version="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "sample-themes/$theme_name/theme.json")"
zip_path="dist/$theme_name/$theme_name-$theme_version.zip"
python3 -m lib.theme_factory.cli verify-package --package "$zip_path"
python3 -m lib.theme_factory.release \
  --theme "$theme_name" \
  --package "$zip_path" \
  --evidence-dir "$evidence_dir" \
  --output "dist/$theme_name/RELEASE-REPORT.md"
