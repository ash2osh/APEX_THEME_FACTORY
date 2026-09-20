#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash tests/run-common-offline.sh
bash tests/run-package-offline.sh

if [[ "${CI:-}" == "true" ]]; then
  git diff --exit-code
fi

echo "ALL_OFFLINE_CHECKS status=PASS"
