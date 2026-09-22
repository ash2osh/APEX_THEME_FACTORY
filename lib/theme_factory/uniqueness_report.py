"""Deterministic pairwise theme uniqueness report generation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path

from lib.theme_factory.discovery import discover_themes
from lib.theme_factory.fingerprint import (
    ERROR_PROFILE_MATCH_THRESHOLD,
    IDENTITY_COLLISION_DELTA_E_THRESHOLD,
    PROFILE_COLLISION_CSS_THRESHOLD,
    SimilarityReport,
    STRUCTURAL_RECOLOR_CSS_THRESHOLD,
    STRUCTURAL_SIMILARITY_CSS_THRESHOLD,
    classify_similarity,
    compare_fingerprints,
    fingerprint_theme,
)
from lib.theme_factory.gitstate import last_source_commit


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
    return classify_similarity(report)


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
        "- Error thresholds: "
        f"structural recolor CSS ≥ {STRUCTURAL_RECOLOR_CSS_THRESHOLD:g} with "
        f"≥ {ERROR_PROFILE_MATCH_THRESHOLD} matching profiles; "
        f"profile collision CSS ≥ {PROFILE_COLLISION_CSS_THRESHOLD:g} with "
        f"≥ {ERROR_PROFILE_MATCH_THRESHOLD} matching profiles; "
        "identity collision requires matching geometry, rhythm, typography treatment, "
        "interaction, and responsive strategy with palette Delta E "
        f"< {IDENTITY_COLLISION_DELTA_E_THRESHOLD:g}.",
        f"- Warning threshold: CSS similarity ≥ {STRUCTURAL_SIMILARITY_CSS_THRESHOLD:g} "
        "when no error rule applies.",
        "",
        "| Theme A | Theme B | CSS similarity | Average palette Delta E | Matching profiles | Font match | Geometry match | Rhythm match | Typography match | Interaction match | Responsive match | Severity | Issue |",
        "|---|---|---:|---:|---:|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        report = row.report
        lines.append(
            f"| `{row.left}` | `{row.right}` | {report.css_similarity:.3f} | {_fmt_delta(report.palette_delta_e)} | "
            f"{len(report.matching_profiles)}/7 | {'yes' if report.font_match else 'no'} | "
            f"{'yes' if report.geometry_match else 'no'} | {'yes' if report.rhythm_match else 'no'} | "
            f"{'yes' if report.typography_match else 'no'} | {'yes' if report.interaction_match else 'no'} | "
            f"{'yes' if report.responsive_match else 'no'} | {row.severity} | `{row.issue_code}` |"
        )
    return "\n".join(lines) + "\n"


def _source_commit(repo_root: Path) -> str:
    # Generated Markdown is intentionally excluded from source identity. This lets a
    # report-only follow-up commit keep the report stable while still binding it to the
    # latest commit that changed packages, CSS, recipes, or build code.
    return last_source_commit(repo_root) or "unknown"


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
