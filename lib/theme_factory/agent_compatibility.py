"""Project-level agent compatibility evidence.

Agent smokes exercise the repository instruction surface rather than a particular theme
package.  This module validates that evidence independently from the A-D theme release
contract while keeping a reader for historical Layer E artifacts.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.theme_factory.errors import PackageError
from lib.theme_factory.gitstate import instruction_equivalent, source_equivalent

SUPPORTED_RUNTIMES = ("codex", "claude", "antigravity")
REQUIRED_SCENARIOS = ("04", "05", "09", "14")
VALID_STATUSES = {"PASS", "FAIL", "UNVERIFIED"}


@dataclass(frozen=True)
class AgentCompatibilityResult:
    status: str
    instruction_commit: str | None
    runtimes: tuple[str, ...]
    scenarios: tuple[str, ...]
    failures: tuple[str, ...]
    evidence_path: Path | None


def _result(
    status: str,
    instruction_commit: str | None,
    *,
    runtimes: tuple[str, ...] = (),
    scenarios: tuple[str, ...] = (),
    failures: tuple[str, ...] = (),
    evidence_path: Path | None = None,
) -> AgentCompatibilityResult:
    return AgentCompatibilityResult(
        status=status,
        instruction_commit=instruction_commit,
        runtimes=runtimes,
        scenarios=scenarios,
        failures=failures,
        evidence_path=evidence_path,
    )


def _sha256(value: Path) -> str:
    return hashlib.sha256(value.read_bytes()).hexdigest()


def _reference_path(evidence_dir: Path, reference: Any, context: str) -> tuple[Path, str]:
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise PackageError(f"{context} must be a path/SHA-256 evidence reference")
    relative = reference.get("path")
    digest = reference.get("sha256")
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or not isinstance(digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
    ):
        raise PackageError(f"{context} has an invalid path or SHA-256")
    path = (evidence_dir / relative).resolve()
    if not path.is_relative_to(evidence_dir.resolve()):
        raise PackageError(f"{context} evidence escapes evidence directory: {relative}")
    if path.suffix.lower() != ".json" or not path.is_file():
        raise PackageError(f"{context} does not reference an evidence JSON file: {relative}")
    if _sha256(path) != digest:
        raise PackageError(f"{context} evidence digest mismatch: {relative}")
    return path, relative


def _read_raw(
    evidence_dir: Path,
    reference: Any,
    context: str,
    *,
    evidence_type: str,
    identity_key: str,
    identity_value: str,
) -> tuple[dict[str, Any], bool, str]:
    path, relative = _reference_path(evidence_dir, reference, context)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"Invalid raw agent evidence JSON {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise PackageError(f"{context} raw evidence must be an object: {relative}")
    commit = raw.get("instructionCommit", raw.get("gitCommit"))
    if (
        raw.get("schemaVersion") != 1
        or raw.get("evidenceType") != evidence_type
        or raw.get(identity_key) != identity_value
        or not isinstance(raw.get("capturedAt"), str)
        or not isinstance(commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", commit) is None
        or raw.get("status") not in VALID_STATUSES
    ):
        raise PackageError(f"{context} raw evidence identity/schema mismatch: {relative}")
    return raw, raw.get("status") == "UNVERIFIED", commit


def _instruction_matches(expected: str | None, actual: str, cwd: Path) -> bool:
    return expected is None or instruction_equivalent(expected, actual, cwd=cwd)


def validate_agent_behavior_artifact(
    path: Path,
    evidence_dir: Path,
    expected_instruction_commit: str | None,
) -> AgentCompatibilityResult:
    """Validate one standalone instruction-bound compatibility artifact.

    Schema/path/digest defects raise ``PackageError``.  A valid artifact that is missing a
    runtime, has environmental ``UNVERIFIED`` results, or was captured against a different
    instruction revision returns ``UNVERIFIED``.  A valid behavioral mismatch returns ``FAIL``.
    """
    path = Path(path)
    evidence_dir = Path(evidence_dir)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"Invalid agent compatibility JSON {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise PackageError(f"Agent compatibility artifact must be an object: {path}")

    instruction_commit = document.get("instructionCommit")
    runtimes = document.get("runtimes")
    scenarios = document.get("scenarios")
    pending_findings = document.get("pendingFindings")
    if (
        document.get("schemaVersion") != 1
        or document.get("evidenceType") != "agent-compatibility"
        or not isinstance(instruction_commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", instruction_commit) is None
        or not isinstance(document.get("capturedAt"), str)
        or not isinstance(runtimes, dict)
        or not isinstance(scenarios, dict)
        or not isinstance(pending_findings, int)
        or isinstance(pending_findings, bool)
        or pending_findings < 0
    ):
        raise PackageError(f"Agent compatibility artifact schema mismatch: {path}")

    unsupported_runtimes = sorted(set(runtimes) - set(SUPPORTED_RUNTIMES))
    if unsupported_runtimes:
        raise PackageError(f"Unsupported agent runtime(s): {', '.join(unsupported_runtimes)}")

    runtime_names = tuple(sorted(set(runtimes) & set(SUPPORTED_RUNTIMES)))
    scenario_names = tuple(sorted(str(name) for name in scenarios))
    failures: list[str] = []
    environmental = False
    instruction_invalidated = not _instruction_matches(expected_instruction_commit, instruction_commit, evidence_dir)

    runtime_documents: dict[str, dict[str, Any]] = {}
    for runtime in runtime_names:
        raw, unavailable, raw_commit = _read_raw(
            evidence_dir,
            runtimes[runtime],
            f"Runtime {runtime}",
            evidence_type="agent-runtime",
            identity_key="runtime",
            identity_value=runtime,
        )
        runtime_documents[runtime] = raw
        environmental = environmental or unavailable
        if not _instruction_matches(instruction_commit, raw_commit, evidence_dir):
            instruction_invalidated = True

    scenario_documents: dict[str, dict[str, Any]] = {}
    for scenario in scenario_names:
        raw, unavailable, raw_commit = _read_raw(
            evidence_dir,
            scenarios[scenario],
            f"Scenario {scenario}",
            evidence_type="agent-scenario",
            identity_key="scenario",
            identity_value=scenario,
        )
        scenario_documents[scenario] = raw
        environmental = environmental or unavailable
        if not _instruction_matches(instruction_commit, raw_commit, evidence_dir):
            instruction_invalidated = True

    missing_runtimes = sorted(set(SUPPORTED_RUNTIMES) - set(runtime_names))
    missing_scenarios = sorted(set(REQUIRED_SCENARIOS) - set(scenario_names))
    if missing_runtimes:
        environmental = True
        failures.append(f"Missing runtime evidence: {', '.join(missing_runtimes)}")
    if missing_scenarios:
        environmental = True
        failures.append(f"Missing scenario evidence: {', '.join(missing_scenarios)}")

    for runtime, raw in runtime_documents.items():
        if raw["status"] == "FAIL":
            failures.append(f"Runtime {runtime} reported FAIL")
    for scenario, raw in scenario_documents.items():
        if scenario in REQUIRED_SCENARIOS and raw["status"] == "FAIL":
            failures.append(f"Scenario {scenario} reported FAIL")
    if pending_findings:
        failures.append(f"pendingFindings={pending_findings}")

    if instruction_invalidated:
        status = "UNVERIFIED"
        if expected_instruction_commit is not None:
            failures.insert(0, "Instruction surface differs from the expected commit")
    elif failures and not environmental:
        status = "FAIL"
    elif environmental:
        status = "UNVERIFIED"
    else:
        status = "PASS"
    return _result(
        status,
        instruction_commit,
        runtimes=runtime_names,
        scenarios=scenario_names,
        failures=tuple(failures),
        evidence_path=path,
    )


def latest_agent_compatibility(
    evidence_root: Path,
    expected_instruction_commit: str | None,
) -> AgentCompatibilityResult:
    """Validate the newest standalone compatibility artifact below ``evidence_root``."""
    evidence_root = Path(evidence_root)
    candidates = sorted(
        {
            path
            for pattern in ("compatibility.json", "*/compatibility.json", "*/*/compatibility.json")
            for path in evidence_root.glob(pattern)
            if path.is_file()
        },
        key=lambda candidate: (candidate.stat().st_mtime_ns, str(candidate)),
        reverse=True,
    )
    if not candidates:
        return _result("UNVERIFIED", None, failures=("No standalone agent compatibility evidence found",))
    return validate_agent_behavior_artifact(candidates[0], candidates[0].parent, expected_instruction_commit)


def validate_legacy_layer_e_artifact(
    path: Path,
    evidence_dir: Path,
    theme_name: str,
    check_name: str,
    status: str,
    expected_git_commit: str | None,
    expected_package_sha256: str | None,
) -> None:
    """Validate the historical theme-bound Layer E shape without making it standalone evidence."""
    try:
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"Invalid evidence artifact {path}: {exc}") from exc
    if not (
        isinstance(artifact, dict)
        and artifact.get("schemaVersion") == 1
        and artifact.get("theme") == theme_name
        and artifact.get("layer") == "E"
        and artifact.get("check") == check_name
        and artifact.get("status") == status
        and isinstance(artifact.get("capturedAt"), str)
        and isinstance(artifact.get("gitCommit"), str)
        and re.fullmatch(r"[0-9a-f]{40}", artifact.get("gitCommit", "")) is not None
        and isinstance(artifact.get("packageSha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", artifact.get("packageSha256", "")) is not None
        and isinstance(artifact.get("results"), dict)
    ):
        raise PackageError(f"Evidence artifact identity/schema mismatch: {path}")
    if not _instruction_matches(expected_git_commit, artifact["gitCommit"], Path(evidence_dir)):
        raise PackageError(
            f"Evidence artifact is for Git commit {artifact['gitCommit']}, whose source differs from {expected_git_commit}: {path}"
        )
    if expected_package_sha256 is not None and artifact["packageSha256"] != expected_package_sha256:
        raise PackageError(f"Evidence artifact is for a different package: {path}")
    results = artifact["results"]
    if status == "FAIL":
        if not isinstance(results.get("failures"), list) or not results["failures"]:
            raise PackageError(f"Failed evidence artifact must list failures: {path}")
        return

    runtimes = results.get("runtimes", {})
    scenarios = results.get("scenarios", {})
    finding_evidence = results.get("findingEvidence")
    valid = (
        isinstance(runtimes, dict)
        and set(runtimes) == set(SUPPORTED_RUNTIMES)
        and isinstance(scenarios, dict)
        and set(scenarios) == {"04", "05", "09", "11", "14"}
        and isinstance(finding_evidence, list)
        and len(finding_evidence) >= 7
        and results.get("pendingFindings") == 0
    )
    if not valid:
        raise PackageError(f"Evidence artifact does not satisfy required legacy Layer E contract: {path}")

    # Import lazily to keep release.py's A-D module free of instruction-only imports while
    # allowing historical E validation to continue using the existing path/digest guard.
    from lib.theme_factory.release import _load_bound_raw_artifact

    for runtime, reference in runtimes.items():
        raw = _load_bound_raw_artifact(
            Path(evidence_dir), reference, theme_name, expected_git_commit,
            expected_package_sha256, f"Layer E runtime {runtime}",
            commit_equivalence=instruction_equivalent, instruction_bound=True,
        )
        if raw.get("evidenceType") != "agent-runtime" or raw.get("runtime") != runtime or raw.get("status") != "PASS":
            raise PackageError(f"Evidence artifact does not satisfy required legacy Layer E contract: {path}")
    for scenario, reference in scenarios.items():
        instruction_only = scenario in {"04", "05", "09", "14"}
        raw = _load_bound_raw_artifact(
            Path(evidence_dir), reference, theme_name, expected_git_commit,
            expected_package_sha256, f"Layer E scenario {scenario}",
            commit_equivalence=instruction_equivalent if instruction_only else source_equivalent,
            instruction_bound=instruction_only,
        )
        if raw.get("evidenceType") != "agent-scenario" or str(raw.get("scenario", "")) != scenario or raw.get("status") != "PASS":
            raise PackageError(f"Evidence artifact does not satisfy required legacy Layer E contract: {path}")
    seen_findings: set[str] = set()
    for index, reference in enumerate(finding_evidence):
        raw = _load_bound_raw_artifact(
            Path(evidence_dir), reference, theme_name, expected_git_commit,
            expected_package_sha256, f"Layer E finding {index + 1}",
            commit_equivalence=instruction_equivalent, instruction_bound=True,
        )
        finding = raw.get("finding")
        if raw.get("evidenceType") != "finding-resolution" or not isinstance(finding, str) or not finding or raw.get("status") not in {"ACCEPTED", "REJECTED"}:
            raise PackageError(f"Evidence artifact does not satisfy required legacy Layer E contract: {path}")
        seen_findings.add(finding)
    if len(seen_findings) < 7:
        raise PackageError(f"Evidence artifact does not satisfy required legacy Layer E contract: {path}")
