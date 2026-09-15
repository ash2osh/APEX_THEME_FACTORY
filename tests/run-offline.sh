#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash -n scripts/*.sh installer/*.sh tests/*.sh

python3 -m unittest \
  tests.test_manifest tests.test_css_bundle tests.test_package_archive \
  tests.test_runtime_contract tests.test_apexlang_patch tests.test_sqlcl \
  tests.test_installer_cli tests.test_uninstaller_cli \
  tests.test_agent_layout tests.test_agent_smoke tests.test_css_policy \
  tests.test_runtime_parity tests.test_alpine_fixture -v

scripts/check-agent-layout.sh

bash tests/run-package-offline.sh

if [[ "${CI:-}" == "true" ]]; then
  git diff --exit-code
fi

echo "ALL_OFFLINE_CHECKS status=PASS"
