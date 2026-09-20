"""Deterministic pairwise theme uniqueness report generation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import subprocess

from lib.theme_factory.discovery import discover_themes
from lib.theme_factory.fingerprint import (
    SimilarityReport,
    compare_fingerprints,
    fingerprint_theme,
)


@dataclass(frozen=True)
class PairwiseUniquenessRow:
    """One unordered pair in the repository-wide uniqueness matrix."""

    left: str
    right: str
    report: SimilarityReport
    severity: str
    issue_code: str


def _classify(report: SimilarityReport) -> tuple[str, str]:
    """Classify a pair using the current author-lane thresholds."""

    profile_count = len(report.matching_profiles)
    if report.css_similarity >= 0.98 and profile_count >= 5:
        return "error", "STRUCTURAL_RECOLOR"
    if (
        report.font_match
        and report.geometry_match
        and profile_count == 7
        and report.palette_delta_e < 12.0
    ):
        return "error", "IDENTITY_COLLISION"
    if report.css_similarity >= 0.85:
        return "warning", "STRUCTURAL_SIMILARITY"
    if profile_count >= 5:
        return "warning", "PROFILE_SIMILARITY"
    if report.font_match and report.geometry_match and report.palette_delta_e < 20.0:
        return "warning", "IDENTITY_SIMILARITY"
    return "PASS", "PASS"


def build_uniqueness_rows(repo_root: Path) -> tuple[PairwiseUniquenessRow, ...]:
    """Build every unordered theme pair in stable report order."""

    themes = discover_themes(Path(repo_root))
    fingerprints = {theme.name: fingerprint_theme(theme.root) for theme in themes}
    rows: list[PairwiseUniquenessRow] = []
    for index, left in enumerate(themes):
        for right in themes[index + 1:]:
            report = compare_fingerprints(fingerprints[left.name], fingerprints[right.name])
            severity, issue_code = _classify(report)
            rows.append(PairwiseUniquenessRow(left.name, right.name, report, severity, issue_code))
    return tuple(sorted(rows, key=lambda row: (-row.report.css_similarity, row.left, row.right)))


def _fmt_delta(value: float) -> str:
    return "n/a" if math.isinf(value) else f"{value:.2f}"


def render_uniqueness_report(rows: tuple[PairwiseUniquenessRow, ...], *, source_commit: str | None = None) -> str:
    """Render the pairwise matrix as reviewable Markdown."""

    lines = [
        "# Theme uniqueness report",
        "",
        "This generated matrix shows every unordered theme pair; warning-only similarities are intentionally retained.",
        "",
        f"- Source commit: `{source_commit or 'unknown'}`",
        "- Error thresholds: structural recolor ≥ 0.98 with ≥ 5 matching profiles; identity collision requires all seven profiles, matching geometry/font, and palette Delta E < 12.",
        "- Warning threshold: CSS similarity ≥ 0.85 when no error rule applies.",
        "",
        "| Theme A | Theme B | CSS similarity | Average palette Delta E | Matching profiles | Font match | Geometry match | Severity | Issue |",
        "|---|---|---:|---:|---:|---|---|---|---|",
    ]
    for row in rows:
        report = row.report
        lines.append(
            f"| `{row.left}` | `{row.right}` | {report.css_similarity:.3f} | {_fmt_delta(report.palette_delta_e)} | "
            f"{len(report.matching_profiles)}/7 | {'yes' if report.font_match else 'no'} | "
            f"{'yes' if report.geometry_match else 'no'} | {row.severity} | `{row.issue_code}` |"
        )
    return "\n".join(lines) + "\n"


def _source_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="fail when output differs; never write")
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    rendered = render_uniqueness_report(
        build_uniqueness_rows(repo_root),
        source_commit=_source_commit(repo_root),
    )
    output = args.output if args.output.is_absolute() else repo_root / args.output
    current = output.read_text(encoding="utf-8") if output.is_file() else None
    if args.check:
        if current != rendered:
            print(f"THEME_UNIQUENESS_REPORT status=DRIFT path={output}")
            return 1
        print(f"THEME_UNIQUENESS_REPORT status=PASS rows={rendered.count(chr(10)) - 12} path={output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"THEME_UNIQUENESS_REPORT status=PASS rows={len(build_uniqueness_rows(repo_root))} path={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
