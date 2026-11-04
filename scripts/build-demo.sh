#!/usr/bin/env bash
# Build the public demo ZIP (see tools/build_demo.py and docs/PUBLIC_DEMO.md).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/tools/build_demo.py" "$@"
