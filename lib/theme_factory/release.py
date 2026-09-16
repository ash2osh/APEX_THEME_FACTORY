"""Theme Factory Release Report Generator.

Aggregates verification layers A through E without converting unbound claims into proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from lib.theme_factory.archive import verify_package
from lib.theme_factory.errors import PackageError

LAYER_DESCRIPTIONS = {
    "A": "Repository source",
    "B": "Package artifact",
    "C": "Database installation",
    "D": "Browser runtime",
    "E": "Agent behavior",
}
VALID_STATUSES = {"PASS", "FAIL", "UNVERIFIED", "NOT_APPLICABLE"}
REQUIRED_EVIDENCE_CHECKS = {
    "C": "database_installation",
    "D": "browser_runtime_matrix",
    "E": "agent_behavior_matrix",
}
from lib.theme_factory.gitstate import EVIDENCE_ROOT, last_source_commit, source_equivalent  # noqa: E402


def commit_matches(expected: str | None, actual: str) -> bool:
    return expected is None or source_equivalent(expected, actual)


def release_verdict(layers: dict[str, str]) -> str:
    """Compute overall release verdict from layer statuses.
    
    A-E are strictly required. Any FAIL results in FAIL; any UNVERIFIED results in UNVERIFIED.
    Returns 'VERIFIED' only when all required layers are PASS.
    """
    required_names = ("A", "B", "C", "D", "E")
    if any(name not in layers for name in required_names):
        return "UNVERIFIED"

    statuses = [layers[name] for name in required_names]
    if "FAIL" in statuses:
        return "FAIL"
    if any(status != "PASS" for status in statuses):
        return "UNVERIFIED"
    return "VERIFIED"


def calculate_layer_statuses(evidence: list[dict[str, Any]]) -> dict[str, str]:
    """Group evidence items by layer and calculate per-layer status."""
    by_layer: dict[str, list[str]] = {}
    for item in evidence:
        layer = str(item.get("layer", "UNKNOWN")).upper()
        status = str(item.get("status", "UNVERIFIED")).upper()
        by_layer.setdefault(layer, []).append(status)

    layer_statuses: dict[str, str] = {}
    for layer, statuses in by_layer.items():
        if "FAIL" in statuses:
            layer_statuses[layer] = "FAIL"
        elif "UNVERIFIED" in statuses:
            layer_statuses[layer] = "UNVERIFIED"
        elif all(s == "PASS" for s in statuses):
            layer_statuses[layer] = "PASS"
        else:
            layer_statuses[layer] = "UNVERIFIED"

    return layer_statuses


def _artifact_path(evidence_dir: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise PackageError(f"Evidence artifact path must be relative: {relative!r}")
    target = (evidence_dir / relative).resolve()
    if not target.is_relative_to(evidence_dir.resolve()):
        raise PackageError(f"Evidence artifact escapes evidence directory: {relative}")
    return target


def load_evidence(
    evidence_dir: Path,
    theme_name: str,
    expected_git_commit: str | None = None,
    expected_package_sha256: str | None = None,
) -> list[dict[str, Any]]:
    """Load theme evidence and bind PASS/FAIL claims to this source and package."""
    if not evidence_dir.exists():
        return []
    evidence: list[dict[str, Any]] = []
    # Release manifests live either directly in the evidence directory or one level down in
    # per-theme folders (`<root>/<date>-release-<theme>/evidence.json`). Other runtime
    # artifacts (parity reports, raw captures) sit beside them and are not release manifests.
    candidates = sorted(evidence_dir.glob("*.json")) + sorted(evidence_dir.glob("*/*.json"))
    for path in candidates:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PackageError(f"Invalid evidence JSON {path}: {exc}") from exc
        if isinstance(document, list):
            raise PackageError(f"Evidence {path} uses the legacy list format; a schemaVersion 1 manifest is required")
        if not isinstance(document, dict) or "checks" not in document:
            continue
        if "theme" not in document and "schemaVersion" not in document:
            continue  # runtime artifact (parity report) that merely has its own `checks`
        if document.get("theme") != theme_name:
            if path.parent != evidence_dir:
                continue  # another theme's manifest in a shared evidence root
            raise PackageError(f"Evidence {path} is for theme {document.get('theme')!r}, not {theme_name!r}")
        if document.get("schemaVersion") != 1:
            raise PackageError(f"Evidence {path} must be a schemaVersion 1 object")
        checks = document.get("checks")
        if not isinstance(checks, list):
            raise PackageError(f"Evidence {path} checks must be an array")
        for check in checks:
            if not isinstance(check, dict):
                raise PackageError(f"Evidence {path} contains a non-object check")
            layer = str(check.get("layer", "")).upper()
            status = str(check.get("status", "")).upper()
            check_name = check.get("check")
            if layer not in LAYER_DESCRIPTIONS or status not in VALID_STATUSES or not isinstance(check_name, str):
                raise PackageError(f"Evidence {path} contains an invalid layer, status, or check name")
            artifact = str(check.get("artifact", ""))
            digest = str(check.get("artifactSha256", ""))
            if status in {"PASS", "FAIL"}:
                artifact_path = _artifact_path(path.parent, artifact)
                if artifact_path.suffix.lower() != ".json" or not artifact_path.is_file() or not re_full_sha256(digest):
                    raise PackageError(f"Evidence check {check_name!r} lacks a valid digest-bound artifact")
                actual = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
                if actual != digest:
                    raise PackageError(f"Evidence artifact digest mismatch: {artifact}")
                _validate_evidence_artifact(
                    artifact_path,
                    path.parent,
                    theme_name,
                    layer,
                    check_name,
                    status,
                    expected_git_commit,
                    expected_package_sha256,
                )
            evidence.append({
                "layer": layer,
                "check": check_name,
                "path": artifact or path.name,
                "status": status,
                "details": str(check.get("details", "")),
            })
    for layer, required_check in REQUIRED_EVIDENCE_CHECKS.items():
        if not any(item["layer"] == layer and item["check"] == required_check for item in evidence):
            evidence.append({
                "layer": layer, "check": required_check, "path": "missing",
                "status": "UNVERIFIED", "details": "Required evidence check is missing",
            })
    return evidence


def re_full_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _load_bound_raw_artifact(
    evidence_dir: Path,
    reference: Any,
    theme_name: str,
    expected_git_commit: str | None,
    expected_package_sha256: str | None,
    context: str,
) -> dict[str, Any]:
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise PackageError(f"{context} must be a path/SHA-256 evidence reference")
    relative = reference.get("path")
    digest = reference.get("sha256")
    if not isinstance(relative, str) or not isinstance(digest, str) or not re_full_sha256(digest):
        raise PackageError(f"{context} has an invalid path or SHA-256")
    path = _artifact_path(evidence_dir, relative)
    if path.suffix.lower() != ".json" or not path.is_file():
        raise PackageError(f"{context} does not reference an evidence JSON file: {relative}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise PackageError(f"{context} evidence digest mismatch: {relative}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"Invalid raw evidence JSON {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise PackageError(f"{context} raw evidence must be an object: {relative}")
    git_commit = document.get("gitCommit")
    package_sha256 = document.get("packageSha256")
    identity_valid = (
        document.get("schemaVersion") == 1
        and document.get("theme") == theme_name
        and isinstance(document.get("capturedAt"), str)
        and isinstance(git_commit, str)
        and re.fullmatch(r"[0-9a-f]{40}", git_commit) is not None
        and isinstance(package_sha256, str)
        and re_full_sha256(package_sha256)
    )
    if not identity_valid:
        raise PackageError(f"{context} raw evidence identity/schema mismatch: {relative}")
    if not commit_matches(expected_git_commit, git_commit):
        raise PackageError(f"{context} raw evidence is for Git commit {git_commit}, whose source differs from {expected_git_commit}")
    if expected_package_sha256 is not None and package_sha256 != expected_package_sha256:
        raise PackageError(f"{context} raw evidence is for a different package: {relative}")
    return document


def _valid_browser_runtime_artifact(
    artifact: dict[str, Any], theme_name: str, consumer: str, width: int,
) -> bool:
    required_fields = {
        "url", "appId", "appAlias", "pageId", "apexVersion", "bodyClasses",
        "htmlClasses", "cssUrls", "javascriptUrls", "loadedUrls", "windowApp",
        "windowAlpine", "activeTheme", "registry", "switcherAvailable",
        "consoleErrors", "failedRequests", "fonts", "fontApexFamilyBefore",
        "fontApexFamilyAfter",
    }
    return (
        artifact.get("evidenceType") == "browser-runtime"
        and artifact.get("consumer") == consumer
        and artifact.get("viewportWidth") == width
        and artifact.get("activeTheme") == theme_name
        and str(artifact.get("apexVersion", "")).startswith("26.1.")
        and required_fields.issubset(artifact)
        and isinstance(artifact.get("bodyClasses"), list)
        and isinstance(artifact.get("htmlClasses"), list)
        and isinstance(artifact.get("cssUrls"), list)
        and isinstance(artifact.get("javascriptUrls"), list)
        and isinstance(artifact.get("loadedUrls"), list)
        and artifact.get("consoleErrors") == []
        and artifact.get("failedRequests") == []
        and isinstance(artifact.get("fonts"), list)
        and artifact.get("fontsVerified") is True
        and artifact.get("accessibilityVerified") is True
        and artifact.get("persistenceVerified") is True
    )


def _validate_evidence_artifact(
    path: Path,
    evidence_dir: Path,
    theme_name: str,
    layer: str,
    check_name: str,
    status: str,
    expected_git_commit: str | None,
    expected_package_sha256: str | None,
) -> None:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"Invalid evidence artifact {path}: {exc}") from exc
    required_identity = (
        isinstance(artifact, dict)
        and artifact.get("schemaVersion") == 1
        and artifact.get("theme") == theme_name
        and artifact.get("layer") == layer
        and artifact.get("check") == check_name
        and artifact.get("status") == status
        and isinstance(artifact.get("capturedAt"), str)
        and isinstance(artifact.get("gitCommit"), str)
        and re.fullmatch(r"[0-9a-f]{40}", artifact.get("gitCommit", "")) is not None
        and isinstance(artifact.get("packageSha256"), str)
        and re_full_sha256(artifact.get("packageSha256", ""))
        and isinstance(artifact.get("results"), dict)
    )
    if not required_identity:
        raise PackageError(f"Evidence artifact identity/schema mismatch: {path}")
    if not commit_matches(expected_git_commit, artifact["gitCommit"]):
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
    if layer == "C":
        applications = results.get("applications")
        operation_evidence = results.get("operationEvidence")
        required_operations = {
            "install", "reinstall", "coexistence", "switcherEnableDisable",
            "uninstall", "restore", "preserveUnrelated",
        }
        valid = (
            isinstance(applications, list) and len(applications) >= 2
            and isinstance(operation_evidence, dict)
            and set(operation_evidence) == required_operations
        )
        if valid:
            seen_applications: set[tuple[str, str]] = set()
            for application in applications:
                if not isinstance(application, dict):
                    valid = False
                    break
                app_id = str(application.get("appId", ""))
                app_alias = application.get("appAlias")
                if not app_id.isdigit() or not isinstance(app_alias, str) or not app_alias:
                    valid = False
                    break
                raw = _load_bound_raw_artifact(
                    evidence_dir, application.get("evidence"), theme_name,
                    expected_git_commit, expected_package_sha256,
                    f"Layer C application {app_alias}",
                )
                if not (
                    raw.get("evidenceType") == "sqlcl-application"
                    and str(raw.get("appId")) == app_id
                    and raw.get("appAlias") == app_alias
                    and str(raw.get("apexVersion", "")).startswith("26.1.")
                    and raw.get("status") == "PASS"
                ):
                    valid = False
                    break
                seen_applications.add((app_id, app_alias))
            if len(seen_applications) < 2:
                valid = False
        if valid:
            for operation in sorted(required_operations):
                raw = _load_bound_raw_artifact(
                    evidence_dir, operation_evidence.get(operation), theme_name,
                    expected_git_commit, expected_package_sha256,
                    f"Layer C operation {operation}",
                )
                if not (
                    raw.get("evidenceType") == "sqlcl-operation"
                    and raw.get("operation") == operation
                    and raw.get("status") == "PASS"
                ):
                    valid = False
                    break
    elif layer == "D":
        rows = results.get("rows")
        valid = isinstance(rows, list) and bool(rows)
        if valid:
            covered: set[tuple[str, int]] = set()
            for row in rows:
                if not isinstance(row, dict):
                    valid = False
                    break
                consumer = row.get("consumer")
                width = row.get("width")
                if consumer not in {"minimal", "business"} or not isinstance(width, int):
                    valid = False
                    break
                raw = _load_bound_raw_artifact(
                    evidence_dir, row.get("evidence"), theme_name,
                    expected_git_commit, expected_package_sha256,
                    f"Layer D {consumer}/{width}",
                )
                if not _valid_browser_runtime_artifact(raw, theme_name, consumer, width):
                    valid = False
                    break
                covered.add((consumer, width))
            required_rows = {
                (consumer, width)
                for consumer in ("minimal", "business")
                for width in (1440, 1024, 768, 375)
            }
            valid = valid and required_rows.issubset(covered)
    elif layer == "E":
        runtimes = results.get("runtimes", {})
        scenarios = results.get("scenarios", {})
        finding_evidence = results.get("findingEvidence")
        valid = (
            isinstance(runtimes, dict)
            and set(runtimes) == {"codex", "claude", "antigravity"}
            and isinstance(scenarios, dict)
            and set(scenarios) == {"04", "05", "09", "11", "14"}
            and isinstance(finding_evidence, list) and len(finding_evidence) >= 7
            and results.get("pendingFindings") == 0
        )
        if valid:
            for runtime, reference in runtimes.items():
                raw = _load_bound_raw_artifact(
                    evidence_dir, reference, theme_name, expected_git_commit,
                    expected_package_sha256, f"Layer E runtime {runtime}",
                )
                if not (
                    raw.get("evidenceType") == "agent-runtime"
                    and raw.get("runtime") == runtime
                    and raw.get("status") == "PASS"
                ):
                    valid = False
                    break
        if valid:
            for scenario, reference in scenarios.items():
                raw = _load_bound_raw_artifact(
                    evidence_dir, reference, theme_name, expected_git_commit,
                    expected_package_sha256, f"Layer E scenario {scenario}",
                )
                if not (
                    raw.get("evidenceType") == "agent-scenario"
                    and str(raw.get("scenario", "")) == scenario
                    and raw.get("status") == "PASS"
                ):
                    valid = False
                    break
        if valid:
            seen_findings: set[str] = set()
            for index, reference in enumerate(finding_evidence):
                raw = _load_bound_raw_artifact(
                    evidence_dir, reference, theme_name, expected_git_commit,
                    expected_package_sha256, f"Layer E finding {index + 1}",
                )
                finding = raw.get("finding")
                if not (
                    raw.get("evidenceType") == "finding-resolution"
                    and isinstance(finding, str) and finding
                    and raw.get("status") in {"ACCEPTED", "REJECTED"}
                ):
                    valid = False
                    break
                seen_findings.add(finding)
            if len(seen_findings) < 7:
                valid = False
    else:
        valid = False
    if not valid:
        raise PackageError(f"Evidence artifact does not satisfy required Layer {layer} contract: {path}")


def render_release_markdown(metadata: dict[str, Any], evidence: list[dict[str, Any]], verdict: str) -> str:
    """Render deterministic markdown release report."""
    ordered = sorted(evidence, key=lambda item: (str(item.get("layer", "")), str(item.get("check", "")), str(item.get("path", ""))))
    
    layer_statuses = calculate_layer_statuses(ordered)

    lines = [
        f"# Release Report: {metadata.get('theme', 'unknown')} v{metadata.get('version', 'unknown')}",
        "",
        f"**Verdict:** `{verdict}`",
        "",
        "## Release Metadata",
        "",
        f"- **Git Commit:** `{metadata.get('git_commit', 'unknown')}`" + (" *(dirty working tree)*" if metadata.get("is_dirty") else ""),
        f"- **Theme Name:** `{metadata.get('theme', 'unknown')}`",
        f"- **Theme Version:** `{metadata.get('version', 'unknown')}`",
        f"- **Package Checksum:** `{metadata.get('checksum', 'n/a')}`",
        f"- **Target APEX Version:** `{metadata.get('apex_version', '26.1.x')}`",
        f"- **Target Universal Theme:** `42 (Iris)`",
        "",
        "## Verification Layer Summary",
        "",
        "| Layer | Description | Status |",
        "|---|---|---|",
        *[f"| Layer {layer} | {description} | `{layer_statuses.get(layer, 'UNVERIFIED')}` |" for layer, description in LAYER_DESCRIPTIONS.items()],
        "",
        "## Evidence Details",
        "",
        "| Layer | Check | Path / Identifier | Status | Details |",
        "|---|---|---|---|---|",
    ]

    for item in ordered:
        layer = item.get("layer", "")
        check = item.get("check", "")
        path = item.get("path", "")
        status = item.get("status", "")
        details = item.get("details", "")
        lines.append(f"| {layer} | {check} | `{path}` | `{status}` | {details} |")

    lines.append("")
    return "\n".join(lines)


def read_git_state() -> tuple[str | None, bool | None]:
    """Return exact source identity, failing closed when either Git query fails."""
    try:
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False,
        )
        commit = commit_result.stdout.strip()
        if commit_result.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
            return None, None
        status_result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=False,
        )
        if status_result.returncode != 0:
            return commit, None
        return commit, bool(status_result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return None, None


def run_release_cli(args: argparse.Namespace) -> None:
    theme_name = args.theme
    evidence_dir = Path(args.evidence_dir)
    output_path = Path(args.output) if args.output else None

    theme_json_path = Path(f"sample-themes/{theme_name}/theme.json")
    if not theme_json_path.exists():
        raise PackageError(f"Unknown theme: {theme_name}")
    data = json.loads(theme_json_path.read_text(encoding="utf-8"))
    version = data["version"]

    git_commit, is_dirty = read_git_state()
    # bind to the last commit that changed the source under test; evidence-only commits don't count
    source_commit = last_source_commit() if git_commit else None

    checksum = "UNVERIFIED"
    zip_candidate = Path(f"dist/{theme_name}/{theme_name}-{version}.zip")
    if getattr(args, "package", None):
        zip_candidate = Path(args.package)
    if zip_candidate.exists():
        import hashlib
        checksum = hashlib.sha256(zip_candidate.read_bytes()).hexdigest()

    package_manifest = None
    if zip_candidate.exists():
        package_manifest = verify_package(zip_candidate)
        if package_manifest.name != theme_name or package_manifest.version != version:
            raise PackageError("Package identity does not match requested theme/version")

    metadata = {
        "theme": theme_name,
        "version": version,
        "git_commit": source_commit or git_commit or "UNVERIFIED",
        "is_dirty": is_dirty is True,
        "apex_version": data.get("compatibility", {}).get("apex", "UNVERIFIED"),
        "checksum": checksum,
    }

    source_verified = git_commit is not None and is_dirty is False
    if git_commit is None:
        source_details = "Git commit identity is unavailable"
    elif is_dirty is None:
        source_details = "Git working-tree status is unavailable"
    elif is_dirty:
        source_details = "Dirty trees cannot be release-verified"
    else:
        source_details = "Release checker ran from a clean Git tree"
    evidence: list[dict[str, Any]] = [{
        "layer": "A", "check": "source_tree", "path": source_commit or git_commit or "UNVERIFIED",
        "status": "PASS" if source_verified else "UNVERIFIED",
        "details": source_details,
    }]
    evidence.append({
        "layer": "B", "check": "package_integrity", "path": str(zip_candidate),
        "status": "PASS" if package_manifest else "UNVERIFIED",
        "details": "ZIP layout, checksums, manifest, and identity verified" if package_manifest else "Package artifact unavailable",
    })
    evidence.extend(load_evidence(
        evidence_dir,
        theme_name,
        expected_git_commit=source_commit or git_commit,
        expected_package_sha256=checksum if re_full_sha256(checksum) else None,
    ))

    layer_statuses = calculate_layer_statuses(evidence)
    verdict = release_verdict(layer_statuses)
    report = render_release_markdown(metadata, evidence, verdict)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"Report written to {output_path}")
    else:
        print(report)

    if verdict != "VERIFIED":
        sys.exit(3)


def main() -> None:
    parser = argparse.ArgumentParser(description="Theme Factory Release Checker")
    parser.add_argument("--theme", required=True, help="Theme name")
    parser.add_argument("--evidence-dir", required=True, help="Path to evidence JSON directory")
    parser.add_argument("--package", help="Path to theme ZIP package")
    parser.add_argument("--output", help="Path to write release report markdown")
    args = parser.parse_args()
    try:
        run_release_cli(args)
    except PackageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    main()
