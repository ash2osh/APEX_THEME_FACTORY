"""Strict, digest-bound checkpoint identities for resumable release evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, MutableSequence

from lib.theme_factory.gitstate import last_source_commit


EVIDENCE_CONTRACT_VERSION = 2

_FIELDS = {
    "source_commit": "sourceCommit",
    "package_sha256": "packageSha256",
    "apex_version": "apexVersion",
    "browser_version": "browserVersion",
    "consumer": "consumer",
    "page": "page",
    "viewport": "viewport",
    "scenario": "scenario",
}


@dataclass(frozen=True)
class EvidenceIdentity:
    source_commit: str
    package_sha256: str
    apex_version: str
    browser_version: str
    consumer: str
    page: str
    viewport: int
    scenario: str

    def to_dict(self) -> dict[str, object]:
        return {
            "evidenceContractVersion": EVIDENCE_CONTRACT_VERSION,
            **{serialized: getattr(self, field) for field, serialized in _FIELDS.items()},
        }


def _diagnose(diagnostics: MutableSequence[str] | None, message: str) -> None:
    if diagnostics is not None:
        diagnostics.append(message)


def _validate_shape(document: Any) -> list[str]:
    if not isinstance(document, dict):
        return ["checkpoint must be a JSON object"]
    required = {"evidenceContractVersion", *_FIELDS.values(), "payload"}
    errors = [f"missing field {name}" for name in sorted(required - set(document))]
    if errors:
        return errors
    if document.get("evidenceContractVersion") != EVIDENCE_CONTRACT_VERSION:
        errors.append(
            f"contract version mismatch: expected {EVIDENCE_CONTRACT_VERSION}, "
            f"found {document.get('evidenceContractVersion')!r}"
        )
    if re.fullmatch(r"[0-9a-f]{40}", str(document.get("sourceCommit", ""))) is None:
        errors.append("sourceCommit must be a full lowercase Git SHA")
    if re.fullmatch(r"[0-9a-f]{64}", str(document.get("packageSha256", ""))) is None:
        errors.append("packageSha256 must be a lowercase SHA-256")
    for name in ("apexVersion", "browserVersion", "consumer", "page", "scenario"):
        if not isinstance(document.get(name), str) or not document[name]:
            errors.append(f"{name} must be a non-empty string")
    viewport = document.get("viewport")
    if not isinstance(viewport, int) or isinstance(viewport, bool) or viewport <= 0:
        errors.append("viewport must be a positive integer")
    if not isinstance(document.get("payload"), dict):
        errors.append("payload must be an object")
    return errors


def checkpoint_valid(
    path: Path,
    expected: EvidenceIdentity,
    diagnostics: MutableSequence[str] | None = None,
) -> bool:
    """Return true only for a regular, schema-valid checkpoint with exact identity."""

    path = Path(path)
    if path.is_symlink():
        _diagnose(diagnostics, f"checkpoint is a symlink: {path}")
        return False
    if not path.is_file():
        _diagnose(diagnostics, f"checkpoint is missing: {path}")
        return False
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _diagnose(diagnostics, f"checkpoint JSON is unreadable: {exc}")
        return False
    errors = _validate_shape(document)
    if errors:
        for error in errors:
            _diagnose(diagnostics, error)
        return False
    payload = document["payload"]
    if payload.get("evidenceType") == "browser-runtime":
        from lib.theme_factory.evidence_schema import validate
        schema_path = Path(__file__).resolve().parents[2] / "tests/live/runtime-evidence.schema.json"
        runtime_errors = validate(payload, schema_path)
        identity_errors = []
        required_values = {
            "evidenceContractVersion": EVIDENCE_CONTRACT_VERSION,
            "gitCommit": expected.source_commit,
            "packageSha256": expected.package_sha256,
            "apexVersion": expected.apex_version,
            "browserVersion": expected.browser_version,
            "consumer": expected.consumer,
            "viewportWidth": expected.viewport,
        }
        for name, value in required_values.items():
            if payload.get(name) != value:
                identity_errors.append(f"runtime payload {name} identity mismatch")
        if payload.get("pageId") != expected.page and payload.get("url") != expected.page:
            identity_errors.append("runtime payload page identity mismatch")
        if runtime_errors or identity_errors:
            for error in (*runtime_errors, *identity_errors):
                _diagnose(diagnostics, f"runtime payload: {error}")
            return False
    expected_document = expected.to_dict()
    mismatches = []
    for field, serialized in _FIELDS.items():
        if document.get(serialized) != expected_document[serialized]:
            mismatches.append(
                f"{field} mismatch: expected {expected_document[serialized]!r}, "
                f"found {document.get(serialized)!r}"
            )
    if document.get("evidenceContractVersion") != EVIDENCE_CONTRACT_VERSION:
        mismatches.append("contract version mismatch")
    for mismatch in mismatches:
        _diagnose(diagnostics, mismatch)
    return not mismatches


def write_checkpoint(path: Path, identity: EvidenceIdentity, payload: dict[str, Any]) -> Path:
    """Atomically write a checkpoint whose identity cannot be overridden by payload data."""

    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"refusing to replace symlink checkpoint: {path}")
    document = {**identity.to_dict(), "payload": dict(payload)}
    errors = _validate_shape(document)
    if errors:
        raise ValueError("invalid checkpoint: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=f".{path.name}.", suffix=".tmp",
            dir=path.parent, delete=False,
        ) as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            temporary = Path(stream.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def read_checkpoint_payload(path: Path) -> dict[str, Any]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    payload = document.get("payload")
    if not isinstance(payload, dict):
        raise ValueError(f"checkpoint payload is invalid: {path}")
    return payload


def current_source_identity(repo_root: Path | None = None) -> tuple[str, str]:
    """Return the source commit and its immutable Git tree digest."""

    root = Path(repo_root or Path.cwd())
    commit = last_source_commit(root)
    if commit is None:
        raise RuntimeError("unable to determine the current source commit")
    import subprocess
    result = subprocess.run(
        ["git", "rev-parse", f"{commit}^{{tree}}"], cwd=root,
        capture_output=True, text=True, check=False,
    )
    digest = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", digest) is None:
        raise RuntimeError("unable to determine the current source tree digest")
    return commit, digest


def write_common_check_artifact(path: Path, repo_root: Path | None = None) -> Path:
    commit, digest = current_source_identity(repo_root)
    document = {
        "schemaVersion": 1,
        "evidenceType": "common-offline-check",
        "status": "PASS",
        "sourceCommit": commit,
        "sourceDigest": digest,
        "capturedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=f".{path.name}.", suffix=".tmp",
            dir=path.parent, delete=False,
        ) as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            temporary = Path(stream.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def common_check_artifact_valid(
    path: Path,
    repo_root: Path | None = None,
    *,
    diagnostics: MutableSequence[str] | None = None,
) -> bool:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        _diagnose(diagnostics, f"common check artifact is missing or a symlink: {path}")
        return False
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _diagnose(diagnostics, f"common check artifact JSON is unreadable: {exc}")
        return False
    try:
        commit, digest = current_source_identity(repo_root)
    except RuntimeError as exc:
        _diagnose(diagnostics, str(exc))
        return False
    expected = {
        "schemaVersion": 1,
        "evidenceType": "common-offline-check",
        "status": "PASS",
        "sourceCommit": commit,
        "sourceDigest": digest,
    }
    if not isinstance(document, dict) or not isinstance(document.get("capturedAt"), str):
        _diagnose(diagnostics, "common check artifact schema is invalid")
        return False
    for name, value in expected.items():
        if document.get(name) != value:
            _diagnose(diagnostics, f"source identity field {name} is stale or invalid")
            return False
    return True
