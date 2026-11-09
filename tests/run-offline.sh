#!/usr/bin/env bash
# Offline gate (no database, no browser): shell syntax, unit tests, skills layout, shared adapter segments and
# the app 102 export in sync with their sources, and every theme through check -> package -> verify.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

bash -n scripts/*.sh installer/*.sh tests/*.sh
unit_log="$(mktemp)"
trap 'rm -f -- "$unit_log"' EXIT
python3 -m unittest discover -s tests -t . -p 'test_*.py' -v > "$unit_log" 2>&1 || { cat "$unit_log"; exit 1; }
grep -E '^(Ran [0-9]+ tests|OK)' "$unit_log"
# A skipped test (no Node, Pillow, AF_UNIX...) is coverage this run did not have: say so instead of hiding it.
grep -E ' \.\.\. skipped ' "$unit_log" | sed -E 's/^([^ ]+) \(([^)]+)\).* skipped /  SKIPPED \2: /' || true
scripts/check-agent-layout.sh
python3 -m lib.theme_factory.adapters --repo-root . --check
python3 -m lib.theme_factory.responsive --repo-root . --check
python3 -m lib.theme_factory.sync_static --repo-root . --check

tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp" "$unit_log"' EXIT
for theme in $(python3 -c 'from pathlib import Path; from lib.theme_factory.discovery import theme_names; print(*theme_names(Path.cwd()))'); do
  scripts/theme.sh check "$theme" > "$tmp/check.txt" || { cat "$tmp/check.txt"; exit 1; }
  scripts/theme.sh release "$theme" --offline --repo-root . > "$tmp/release.txt" 2>&1 || { cat "$tmp/release.txt"; exit 1; }
  echo "THEME $theme status=PASS"
done
echo "OFFLINE status=PASS"
