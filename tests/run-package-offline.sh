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

mapfile -t themes < <(python3 -c 'from pathlib import Path; from lib.theme_factory.discovery import theme_names; print(*theme_names(Path.cwd()), sep="\n")')
if [[ ${#themes[@]} -eq 0 ]]; then
  echo "THEME_PACKAGE status=FAIL reason=no-discovered-themes" >&2
  exit 1
fi

for theme in "${themes[@]}"; do
  if ! scripts/package-theme.sh "$theme" "$tmp/$theme"; then
    echo "THEME_PACKAGE theme=$theme status=FAIL phase=build" >&2
    exit 1
  fi
  archive="$(find "$tmp/$theme" -maxdepth 1 -name '*.zip' -print -quit)"
  if [[ -z "$archive" ]] || ! python3 -m lib.theme_factory.cli verify-package --package "$archive"; then
    echo "THEME_PACKAGE theme=$theme status=FAIL phase=verify" >&2
    exit 1
  fi
  echo "THEME_PACKAGE theme=$theme status=PASS"
done

echo "PACKAGE_OFFLINE status=PASS"
