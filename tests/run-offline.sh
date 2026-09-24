#!/usr/bin/env bash
# Offline gate (no database, no browser): shell syntax, unit tests, skills layout, shared adapter segments and
# the app 102 export in sync with their sources, and every theme through check -> package -> verify.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

bash -n scripts/*.sh installer/*.sh tests/*.sh
python3 -m unittest discover -s tests -t . -p 'test_*.py'
scripts/check-agent-layout.sh
python3 -m lib.theme_factory.adapters --repo-root . --check
python3 -m lib.theme_factory.responsive --repo-root . --check
python3 -m lib.theme_factory.sync_static --repo-root . --check

tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
for theme in $(python3 -c 'from pathlib import Path; from lib.theme_factory.discovery import theme_names; print(*theme_names(Path.cwd()))'); do
  scripts/theme.sh check "$theme" > "$tmp/check.txt" || { cat "$tmp/check.txt"; exit 1; }
  scripts/theme.sh release "$theme" --offline --repo-root . > "$tmp/release.txt" 2>&1 || { cat "$tmp/release.txt"; exit 1; }
  echo "THEME $theme status=PASS"
done
echo "OFFLINE status=PASS"
