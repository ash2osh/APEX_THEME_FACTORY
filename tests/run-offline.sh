#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash tests/run-common-offline.sh
bash tests/run-package-offline.sh

# Agent compatibility is a project-level signal.  A missing or unavailable external runtime is
# honest UNVERIFIED (exit 2) and must not block theme/package offline verification; malformed evidence
# or generated-document drift remains a hard failure.
set +e
bash scripts/agent-compatibility-check.sh --check
AGENT_COMPATIBILITY_STATUS=$?
set -e
if [[ "$AGENT_COMPATIBILITY_STATUS" -ne 0 && "$AGENT_COMPATIBILITY_STATUS" -ne 2 ]]; then
  exit "$AGENT_COMPATIBILITY_STATUS"
fi
if [[ "$AGENT_COMPATIBILITY_STATUS" -eq 2 ]]; then
  echo "AGENT_COMPATIBILITY status=UNVERIFIED (offline signal; theme release remains A-D)"
fi

if [[ "${CI:-}" == "true" ]]; then
  git diff --exit-code
fi

echo "ALL_OFFLINE_CHECKS status=PASS"
