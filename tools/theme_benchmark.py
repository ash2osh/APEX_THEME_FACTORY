#!/usr/bin/env python3
"""Record and report reproducible Theme Factory workflow measurements."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
from statistics import median
import sys
import tempfile
from typing import Sequence

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from lib.theme_factory.errors import PackageError


SHA40_RE = re.compile(r"[0-9a-f]{40}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
RESULTS = {"PASS", "FAIL", "UNVERIFIED"}


def _timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PackageError(f"{field} must be an ISO-8601 timestamp with timezone") from exc
    if parsed.tzinfo is None:
        raise PackageError(f"{field} must include a timezone")
    return parsed


@dataclass(frozen=True)
class BenchmarkRun:
    schema_version: int
    theme: str
    source_commit: str
    recipe_sha256: str
    started_at: str
    finished_at: str
    scaffold_seconds: float
    check_seconds: float
    dev_seconds: float
    first_preview_seconds: float
    commands: tuple[str, ...]
    files_read: tuple[str, ...]
    files_written: tuple[str, ...]
    validation_reruns: int
    browser_rows: int
    input_tokens: int | None
    output_tokens: int | None
    result: str

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise PackageError("benchmark schemaVersion must be 1")
        if not self.theme or self.theme.strip() != self.theme:
            raise PackageError("benchmark theme must be a non-empty exact identity")
        if SHA40_RE.fullmatch(self.source_commit) is None:
            raise PackageError("benchmark source commit must be a full lowercase 40-character SHA")
        if SHA256_RE.fullmatch(self.recipe_sha256) is None:
            raise PackageError("benchmark recipe SHA-256 must be a full lowercase digest")
        started = _timestamp(self.started_at, "startedAt")
        finished = _timestamp(self.finished_at, "finishedAt")
        if finished < started:
            raise PackageError("benchmark finishedAt must not precede startedAt")
        measurements = {
            "scaffoldSeconds": self.scaffold_seconds,
            "checkSeconds": self.check_seconds,
            "devSeconds": self.dev_seconds,
            "firstPreviewSeconds": self.first_preview_seconds,
            "validationReruns": self.validation_reruns,
            "browserRows": self.browser_rows,
        }
        if any(value < 0 for value in measurements.values()):
            raise PackageError("benchmark measurements must be nonnegative")
        if self.validation_reruns != int(self.validation_reruns) or self.browser_rows != int(self.browser_rows):
            raise PackageError("benchmark counters must be integers")
        if (self.input_tokens is None) != (self.output_tokens is None):
            raise PackageError("inputTokens and outputTokens must both be supplied or both be null")
        if self.input_tokens is not None and (self.input_tokens < 0 or self.output_tokens < 0):
            raise PackageError("benchmark token totals must be nonnegative")
        if self.result not in RESULTS:
            raise PackageError("benchmark result must be PASS, FAIL, or UNVERIFIED")
        for field, values in (("commands", self.commands), ("filesRead", self.files_read),
                              ("filesWritten", self.files_written)):
            if any(not isinstance(value, str) or not value for value in values):
                raise PackageError(f"benchmark {field} entries must be non-empty strings")

    @property
    def total_tokens(self) -> int | None:
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class BenchmarkSummary:
    run_count: int
    scaffold_median_seconds: float | None
    check_median_seconds: float | None
    preview_median_seconds: float | None
    candidate_median_tokens: float | None
    baseline_tokens: int | None
    token_reduction_percent: float | None
    scaffold_status: str
    check_status: str
    preview_status: str
    token_status: str
    overall_status: str


def _metric_status(value: float | None, threshold: float, complete: bool) -> str:
    if not complete or value is None:
        return "UNVERIFIED"
    return "PASS" if value < threshold else "FAIL"


def summarize_runs(baseline: BenchmarkRun, candidates: Sequence[BenchmarkRun],
                   *, allow_incomplete: bool = False) -> BenchmarkSummary:
    candidates = tuple(candidates)
    missing_tokens = baseline.total_tokens is None or any(run.total_tokens is None for run in candidates)
    if missing_tokens and not allow_incomplete:
        raise PackageError("three candidate runs with explicit token usage are required for the token target")
    scaffold = median(run.scaffold_seconds for run in candidates) if candidates else None
    check = median(run.check_seconds for run in candidates) if candidates else None
    preview = median(run.first_preview_seconds for run in candidates) if candidates else None
    candidate_tokens = (
        median(run.total_tokens for run in candidates if run.total_tokens is not None)
        if candidates and not any(run.total_tokens is None for run in candidates) else None
    )
    reduction = None
    if baseline.total_tokens and candidate_tokens is not None:
        reduction = round((baseline.total_tokens - candidate_tokens) / baseline.total_tokens * 100, 2)
    complete = len(candidates) >= 3
    scaffold_status = _metric_status(scaffold, 10.0, complete)
    check_status = _metric_status(check, 30.0, complete)
    preview_status = _metric_status(preview, 120.0, complete)
    token_status = "UNVERIFIED"
    if complete and reduction is not None:
        token_status = "PASS" if reduction >= 50.0 else "FAIL"
    statuses = (scaffold_status, check_status, preview_status, token_status)
    if any(run.result == "FAIL" for run in candidates) or "FAIL" in statuses:
        overall = "FAIL"
    elif all(status == "PASS" for status in statuses):
        overall = "PASS"
    else:
        overall = "UNVERIFIED"
    return BenchmarkSummary(
        len(candidates), scaffold, check, preview, candidate_tokens, baseline.total_tokens,
        reduction, scaffold_status, check_status, preview_status, token_status, overall,
    )


def run_document(run: BenchmarkRun) -> dict[str, object]:
    return {
        "schemaVersion": run.schema_version,
        "theme": run.theme,
        "sourceCommit": run.source_commit,
        "recipeSha256": run.recipe_sha256,
        "startedAt": run.started_at,
        "finishedAt": run.finished_at,
        "wallSeconds": {
            "scaffold": run.scaffold_seconds,
            "check": run.check_seconds,
            "dev": run.dev_seconds,
            "firstPreview": run.first_preview_seconds,
        },
        "commands": list(run.commands),
        "filesRead": list(run.files_read),
        "filesWritten": list(run.files_written),
        "validationReruns": run.validation_reruns,
        "browserRows": run.browser_rows,
        "inputTokens": run.input_tokens,
        "outputTokens": run.output_tokens,
        "result": run.result,
    }


def load_run(path: Path) -> BenchmarkRun:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        wall = data["wallSeconds"]
        return BenchmarkRun(
            data["schemaVersion"], data["theme"], data["sourceCommit"], data["recipeSha256"],
            data["startedAt"], data["finishedAt"], wall["scaffold"], wall["check"],
            wall["dev"], wall["firstPreview"], tuple(data["commands"]),
            tuple(data["filesRead"]), tuple(data["filesWritten"]), data["validationReruns"],
            data["browserRows"], data.get("inputTokens"), data.get("outputTokens"), data["result"],
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise PackageError(f"Invalid benchmark record {path}: {exc}") from exc


def _display(value: float | int | None, suffix: str = "") -> str:
    if value is None:
        return "UNMEASURED"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def render_report(baseline: BenchmarkRun, candidates: Sequence[BenchmarkRun],
                  *, allow_incomplete: bool = False) -> str:
    summary = summarize_runs(baseline, candidates, allow_incomplete=allow_incomplete)
    rows = (
        ("Scaffold", "< 10 s", _display(summary.scaffold_median_seconds, " s"), summary.scaffold_status),
        ("Cached theme check", "< 30 s", _display(summary.check_median_seconds, " s"), summary.check_status),
        ("First app-102 preview", "< 120 s", _display(summary.preview_median_seconds, " s"), summary.preview_status),
        ("Agent token reduction", ">= 50%", _display(summary.token_reduction_percent, "%"), summary.token_status),
        ("Overall", "all targets", f"{summary.run_count} candidate runs", summary.overall_status),
    )
    lines = [
        "# Theme Workflow Benchmark", "",
        "This benchmark compares the recipe-driven workflow with the preserved four-theme baseline. "
        "Token counts are supplied by the agent harness; they are never inferred from text size.", "",
        "## Current result", "",
        "| Measure | Target | Median / result | Status |", "|---|---:|---:|---|",
    ]
    lines += [f"| {name} | {target} | {value} | {status} |" for name, target, value, status in rows]
    lines += ["", "## Repeatable protocol", "",
              "Run exactly three trials in clean disposable worktrees, using the same requirement prompt:", "",
              "1. A compact light theme with no custom font.",
              "2. A dense technical dark theme with the complete dark-token treatment.",
              "3. A bilingual Arabic/Latin theme with four pinned WOFF2 weights.", "",
              "For each trial, stop timing after candidate-lane PASS. Record scaffold, cached check, candidate "
              "lane, and first-preview wall times; commands; files read and written; validation reruns; browser "
              "rows; and the harness-provided input/output token totals. Exclude only documented SQLcl/database "
              "outages. Do not change thresholds after observing results.", "",
              "## Source binding", "",
              f"- Baseline source commit: `{baseline.source_commit}`",
              f"- Baseline recipe SHA-256: `{baseline.recipe_sha256}`",
              f"- Baseline total tokens: {_display(summary.baseline_tokens)}", ""]
    if candidates:
        lines += ["## Candidate runs", ""]
        for run in candidates:
            lines.append(
                f"- `{run.theme}` at `{run.source_commit}` — result {run.result}; "
                f"tokens {_display(run.total_tokens)}; preview {_display(run.first_preview_seconds, ' s')}"
            )
        lines.append("")
    else:
        lines += ["No candidate run records were supplied. All targets remain `UNVERIFIED`.", ""]
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command_name", required=True)
    record = commands.add_parser("record", help="Write one explicit benchmark measurement")
    record.add_argument("--output", type=Path, required=True)
    record.add_argument("--overwrite", action="store_true")
    record.add_argument("--theme", required=True)
    record.add_argument("--source-commit", required=True)
    record.add_argument("--recipe-sha256", required=True)
    record.add_argument("--started-at", required=True)
    record.add_argument("--finished-at", required=True)
    for name in ("scaffold", "check", "dev", "first-preview"):
        record.add_argument(f"--{name}-seconds", type=float, required=True)
    record.add_argument("--command", action="append", default=[])
    record.add_argument("--file-read", action="append", default=[])
    record.add_argument("--file-written", action="append", default=[])
    record.add_argument("--validation-reruns", type=int, required=True)
    record.add_argument("--browser-rows", type=int, required=True)
    record.add_argument("--input-tokens", type=int)
    record.add_argument("--output-tokens", type=int)
    record.add_argument("--result", choices=sorted(RESULTS), required=True)

    report = commands.add_parser("report", help="Compare candidate records with the baseline")
    report.add_argument("--baseline", type=Path, required=True)
    report.add_argument("--runs", type=Path, required=True)
    report.add_argument("--output", type=Path)
    report.add_argument("--allow-incomplete", action="store_true")
    return parser


def _record(args: argparse.Namespace) -> int:
    if args.output.exists() and not args.overwrite:
        raise PackageError(f"Benchmark record already exists: {args.output}; pass --overwrite intentionally")
    run = BenchmarkRun(
        1, args.theme, args.source_commit, args.recipe_sha256, args.started_at, args.finished_at,
        args.scaffold_seconds, args.check_seconds, args.dev_seconds, args.first_preview_seconds,
        tuple(args.command), tuple(args.file_read), tuple(args.file_written), args.validation_reruns,
        args.browser_rows, args.input_tokens, args.output_tokens, args.result,
    )
    _atomic_write(args.output, json.dumps(run_document(run), indent=2, sort_keys=True) + "\n")
    print(f"BENCHMARK_RECORD status=PASS theme={run.theme} tokens={run.total_tokens if run.total_tokens is not None else 'UNMEASURED'}")
    return 0


def _report(args: argparse.Namespace) -> int:
    baseline = load_run(args.baseline)
    if args.runs.exists() and not args.runs.is_dir():
        raise PackageError(f"Benchmark runs path is not a directory: {args.runs}")
    if not args.runs.exists() and not args.allow_incomplete:
        raise PackageError(f"Benchmark runs directory does not exist: {args.runs}")
    paths = sorted(args.runs.glob("*.json")) if args.runs.is_dir() else []
    runs = tuple(load_run(path) for path in paths)
    report = render_report(baseline, runs, allow_incomplete=args.allow_incomplete)
    if args.output:
        _atomic_write(args.output, report)
        print(f"BENCHMARK_REPORT status={summarize_runs(baseline, runs, allow_incomplete=args.allow_incomplete).overall_status} output={args.output}")
    else:
        print(report, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        return _record(args) if args.command_name == "record" else _report(args)
    except PackageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
