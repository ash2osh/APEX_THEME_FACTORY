#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

connection=""
workspace=""
app_id=""
browser_evidence=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --connection) connection="$2"; shift 2 ;;
    --workspace) workspace="$2"; shift 2 ;;
    --app-id) app_id="$2"; shift 2 ;;
    --browser-evidence) browser_evidence="$2"; shift 2 ;;
    *) echo "Unknown option $1" >&2; exit 2 ;;
  esac
done

if [ -z "$connection" ] || [ -z "$workspace" ] || [ -z "$app_id" ]; then
  echo "Usage: $0 --connection <conn> --workspace <ws> --app-id <id> [--browser-evidence <file>]" >&2
  exit 2
fi

tmp_dir="$(mktemp -d)"
trap 'test -n "$tmp_dir" && test "$tmp_dir" != / && rm -rf -- "$tmp_dir"' EXIT

export_output=""
if ! export_output="$(sql -S -name "$connection" <<SQL
whenever sqlerror exit failure
apex export -applicationid $app_id -exptype APEXLANG -split -dir "$tmp_dir" -skipexportdate -overwrite-files
exit
SQL
)"; then
  echo "WARNING: SQLcl export failed for connection '$connection':" >&2
  echo "$export_output" >&2
  out_dir=".agents/evaluations/runtime"
  mkdir -p "$out_dir"
  now_str="$(date -u +%Y%m%dT%H%M%SZ)"
  cat > "$out_dir/${now_str}-parity.json" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "workspace": "$workspace",
  "appId": $app_id,
  "verdict": "UNVERIFIED",
  "error": "SQLcl export failed: unreachable connection or credentials unavailable",
  "checks": {}
}
EOF
  echo "Wrote unverified status report to: $out_dir/${now_str}-parity.json"
  exit 0
fi

browser_args=()
if [ -n "$browser_evidence" ]; then
  browser_args=(--browser-evidence "$browser_evidence")
fi

python3 tools/runtime_parity.py \
  --source applications/ut \
  --database-export "$tmp_dir" \
  --workspace "$workspace" \
  --app-id "$app_id" \
  "${browser_args[@]}"
