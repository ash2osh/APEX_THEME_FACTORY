#!/usr/bin/env python3
"""Validate and render project-level agent compatibility evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.theme_factory.agent_compatibility import (
    REQUIRED_SCENARIOS,
    SUPPORTED_RUNTIMES,
    latest_agent_compatibility,
    validate_agent_behavior_artifact,
    validate_legacy_layer_e_artifact,
)
from lib.theme_factory.errors import PackageError
from lib.theme_factory.gitstate import last_instruction_commit

START_MARKER = "<!-- @generated:agent-compatibility:start -->"
END_MARKER = "<!-- @generated:agent-compatibility:end -->"


def _status_code(status: str) -> int:
    return {"PASS": 0, "FAIL": 1, "UNVERIFIED": 2}.get(status, 3)


def _runtime_status(result, runtime: str) -> str:
    if runtime not in result.runtimes:
        return "UNVERIFIED"
    return result.status


def render_generated_section(result) -> str:
    lines = [
        START_MARKER,
        "## Current standalone agent compatibility",
        "",
        f"- Status: `{result.status}`",
        f"- Instruction commit: `{result.instruction_commit or 'unknown'}`",
        f"- Evidence: `{result.evidence_path or 'none'}`",
        "",
        "| Runtime | Status |",
        "|---|---|",
    ]
    lines.extend(
        f"| {runtime} | `{_runtime_status(result, runtime)}` |"
        for runtime in SUPPORTED_RUNTIMES
    )
    lines.extend([
        "",
        f"- Required scenarios: `{', '.join(result.scenarios) or 'none'}`",
    ])
    if result.failures:
        lines.append("- Findings:")
        lines.extend(f"  - {failure}" for failure in result.failures)
    else:
        lines.append("- Findings: none")
    lines.extend([END_MARKER, ""])
    return "\n".join(lines)


def _replace_generated(documentation: Path, section: str, *, check: bool) -> None:
    if documentation.exists():
        original = documentation.read_text(encoding="utf-8")
    else:
        original = ""
    start = original.count(START_MARKER)
    end = original.count(END_MARKER)
    if start > 1 or end > 1 or start != end:
        raise PackageError("Generated agent compatibility markers are missing or duplicated")
    if start == 0:
        if check:
            raise PackageError("Generated agent compatibility section is missing (drift)")
        updated = original.rstrip() + ("\n\n" if original.strip() else "") + section
    else:
        start_index = original.index(START_MARKER)
        end_index = original.index(END_MARKER, start_index) + len(END_MARKER)
        existing = original[start_index:end_index]
        expected = section.rstrip()
        if check:
            if existing != expected:
                raise PackageError("Generated agent compatibility section has drift")
            return
        updated = original[:start_index] + section.rstrip() + original[end_index:]
    if check:
        return
    documentation.parent.mkdir(parents=True, exist_ok=True)
    documentation.write_text(updated, encoding="utf-8")


def _legacy_reference_path(legacy_dir: Path, reference: Any, context: str) -> Path:
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise PackageError(f"{context} must be a path/SHA-256 evidence reference")
    relative = reference.get("path")
    digest = reference.get("sha256")
    if not isinstance(relative, str) or Path(relative).is_absolute() or not isinstance(digest, str):
        raise PackageError(f"{context} has an invalid path or SHA-256")
    base = legacy_dir.parent if relative.startswith("shared/") else legacy_dir
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise PackageError(f"{context} escapes the legacy evidence directory: {relative}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise PackageError(f"{context} evidence digest mismatch: {relative}")
    return path


def migrate_legacy(legacy_path: Path, output: Path) -> int:
    legacy_path = Path(legacy_path)
    output = Path(output)
    try:
        legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"Invalid legacy Layer E artifact {legacy_path}: {exc}") from exc
    if not isinstance(legacy, dict):
        raise PackageError("Legacy Layer E artifact must be an object")
    validate_legacy_layer_e_artifact(
        legacy_path,
        legacy_path.parent,
        str(legacy.get("theme", "")),
        str(legacy.get("check", "agent_behavior_matrix")),
        str(legacy.get("status", "")),
        None,
        None,
    )
    results = legacy["results"]
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = output.parent / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    def copy_reference(reference: Any, destination_name: str, context: str) -> dict[str, str]:
        source = _legacy_reference_path(legacy_path.parent, reference, context)
        destination = raw_dir / destination_name
        shutil.copyfile(source, destination)
        return {
            "path": str(destination.relative_to(output.parent)),
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        }

    runtime_refs = {
        runtime: copy_reference(results["runtimes"][runtime], f"runtime-{runtime}.json", f"Runtime {runtime}")
        for runtime in SUPPORTED_RUNTIMES
    }
    scenario_refs = {
        scenario: copy_reference(results["scenarios"][scenario], f"scenario-{scenario}.json", f"Scenario {scenario}")
        for scenario in REQUIRED_SCENARIOS
    }
    standalone = {
        "schemaVersion": 1,
        "evidenceType": "agent-compatibility",
        "instructionCommit": legacy["gitCommit"],
        "capturedAt": legacy["capturedAt"],
        "runtimes": runtime_refs,
        "scenarios": scenario_refs,
        "pendingFindings": 0,
    }
    output.write_text(json.dumps(standalone, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    expected = last_instruction_commit()
    result = validate_agent_behavior_artifact(output, output.parent, expected)
    print(f"AGENT_COMPATIBILITY status={result.status} evidence={output}")
    return _status_code(result.status)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, default=Path(".agents/evaluations/agent-compatibility"))
    parser.add_argument("--documentation", type=Path, default=Path("docs/AGENT_COMPATIBILITY.md"))
    parser.add_argument("--expected-instruction-commit")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--migrate-legacy", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.migrate_legacy is not None:
            if args.output is None:
                raise PackageError("--output is required with --migrate-legacy")
            return migrate_legacy(args.migrate_legacy, args.output)
        if args.output is not None:
            raise PackageError("--output is only valid with --migrate-legacy")
        result = latest_agent_compatibility(args.evidence_root, args.expected_instruction_commit)
        section = render_generated_section(result)
        _replace_generated(args.documentation, section, check=args.check)
        if args.check:
            print(f"AGENT_COMPATIBILITY_CHECK status={result.status}")
        else:
            print(f"AGENT_COMPATIBILITY status={result.status} evidence={result.evidence_path or 'none'}")
        return _status_code(result.status)
    except PackageError as exc:
        print(f"AGENT_COMPATIBILITY_ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
