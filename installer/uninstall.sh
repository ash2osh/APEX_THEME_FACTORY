#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { echo "Python 3.10+ is required (python3 not found)" >&2; exit 2; }
PY_VERSION="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo 0.0)"
case "$PY_VERSION" in
  3.1[0-9]|3.[2-9][0-9]|[4-9].*) ;;
  *) echo "Python 3.10+ is required (found $PY_VERSION)" >&2; exit 2 ;;
esac
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$SCRIPT_DIR" exec python3 -m lib.theme_factory.cli uninstall --package-root "$SCRIPT_DIR" "$@"
