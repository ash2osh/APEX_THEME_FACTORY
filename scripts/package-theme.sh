#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="${1:?usage: scripts/package-theme.sh <theme-name> [output-dir]}"
output="${2:-$ROOT/dist/$name}"
PYTHONPATH="$ROOT/lib" exec python3 -m theme_factory.cli package --repo-root "$ROOT" --theme "$name" --output-dir "$output"
