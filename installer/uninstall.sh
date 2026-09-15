#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { echo "Python 3.10+ is required" >&2; exit 2; }
PYTHONPATH="$SCRIPT_DIR/lib" exec python3 -m theme_factory.cli uninstall --package-root "$SCRIPT_DIR" "$@"
