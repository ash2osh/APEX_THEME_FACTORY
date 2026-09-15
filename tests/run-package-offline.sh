#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m unittest \
  tests.test_manifest tests.test_css_bundle tests.test_package_archive \
  tests.test_runtime_contract tests.test_apexlang_patch tests.test_sqlcl \
  tests.test_installer_cli tests.test_uninstaller_cli -v

bash -n scripts/package-theme.sh installer/install.sh installer/uninstall.sh

tmp="$(mktemp -d)"
trap 'test -n "$tmp" && test "$tmp" != / && rm -rf -- "$tmp"' EXIT

scripts/package-theme.sh linen "$tmp/linen"
scripts/package-theme.sh solarized-dark "$tmp/solarized-dark"

echo "PACKAGE_OFFLINE status=PASS"
