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
  tests.test_runtime_parity tests.test_alpine_fixture \
  tests.test_consumer_fixture_scripts tests.test_release_report \
  tests.test_apexlang_roundtrip_sim tests.test_lifecycle_real_shape tests.test_live_matrix tests.test_browser_matrix \
  tests.test_gitstate tests.test_capture_driver_dirty_checks tests.test_sync_static \
  tests.test_sample_themes_coverage -v
python3 -m unittest tests.test_chrome_mcp_daemon -v

scripts/check-agent-layout.sh

bash tests/run-package-offline.sh

if [[ "${CI:-}" == "true" ]]; then
  git diff --exit-code
fi

echo "ALL_OFFLINE_CHECKS status=PASS"
