#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

artifact=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifact) artifact="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

bash -n scripts/*.sh installer/*.sh tests/*.sh
python3 -m unittest discover -s tests -t . -p 'test_*.py' -v
scripts/check-agent-layout.sh

if [[ -n "$artifact" ]]; then
  python3 - "$artifact" <<'PY'
import sys
from pathlib import Path
from lib.theme_factory.evidence_cache import write_common_check_artifact

write_common_check_artifact(Path(sys.argv[1]))
PY
fi

echo "COMMON_OFFLINE_CHECKS status=PASS"
