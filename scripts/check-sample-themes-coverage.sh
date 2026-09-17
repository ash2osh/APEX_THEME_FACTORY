#!/usr/bin/env bash
# Plan Task 6: every sample-themes/<name>/ must either have a real release verdict or be
# explicitly marked unverified in sample-themes/README.md's status table. Silence - a theme with
# no row at all - is the defect this exists to catch; estate-slate/estate-slate-dark were invisible
# to the release system for exactly this reason until 2026-09-17.
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

python3 - "$ROOT" <<'PY_EOF'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
themes_dir = root / "sample-themes"
readme_path = themes_dir / "README.md"
readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

theme_names = sorted(
    p.name for p in themes_dir.iterdir()
    if p.is_dir() and (p / "theme.json").exists()
)

# A status-table row starts with a markdown link to the theme's own directory, e.g.
# "| [linen](linen/) ... | ... |". Case-insensitive VERIFIED/UNVERIFIED anywhere in that row is
# enough - this check's job is to catch silence, not to re-derive the verdict release-check.sh and
# RELEASE-MATRIX.md already prove.
rows = {}
for line in readme.splitlines():
    match = re.match(r"\|\s*\[([a-z0-9-]+)\]\(([a-z0-9-]+)/\)", line)
    if match and match.group(1) == match.group(2):
        rows[match.group(1)] = line

errors = []
for name in theme_names:
    row = rows.get(name)
    if row is None:
        errors.append(f"{name}: no row in sample-themes/README.md's status table (silent - not reported as verified or unverified)")
    elif "VERIFIED" not in row.upper():
        errors.append(f"{name}: row exists but states neither VERIFIED nor UNVERIFIED: {row.strip()}")

if errors:
    for error in errors:
        print(f"SAMPLE_THEMES_COVERAGE error: {error}", file=sys.stderr)
    print(f"SAMPLE_THEMES_COVERAGE status=FAIL themes={len(theme_names)} errors={len(errors)}")
    sys.exit(1)

print(f"SAMPLE_THEMES_COVERAGE status=PASS themes={len(theme_names)}")
PY_EOF
