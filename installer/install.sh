#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { echo "Python 3.10+ is required" >&2; exit 2; }
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$SCRIPT_DIR" exec python3 -m lib.theme_factory.cli install --package-root "$SCRIPT_DIR" "$@"
