#!/usr/bin/env bash
# Assemble app 102's static files into the APEXLang export (see lib/theme_factory/sync_static.py).
#   scripts/sync-static.sh           write
#   scripts/sync-static.sh --check   report drift only; exit 1 on drift
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="$ROOT" exec python3 -m lib.theme_factory.sync_static --repo-root "$ROOT" "$@"
