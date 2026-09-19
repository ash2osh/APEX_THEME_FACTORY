"""Atomic content-addressed cache for theme author checks."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lib.theme_factory.checks import CheckReport


@dataclass(frozen=True)
class CacheKey:
    contract_version: str
    input_digest: str


def _entry_path(cache_dir: Path, key: CacheKey) -> Path:
    return Path(cache_dir) / f"{key.input_digest}.json"


def load_cached_report(cache_dir: Path, key: CacheKey) -> "CheckReport | None":
    """Load a schema-matching report; corruption and version drift are cache misses."""

    path = _entry_path(cache_dir, key)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("contractVersion") != key.contract_version:
            return None
        if payload.get("inputDigest") != key.input_digest:
            return None
        from lib.theme_factory.checks import CheckReport
        report = CheckReport.from_dict(payload["report"])
        if report.input_digest != key.input_digest or report.status != "PASS":
            return None
        return report.with_cache_hit(True)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def store_cached_report(cache_dir: Path, key: CacheKey, report: "CheckReport") -> Path:
    """Atomically store a successful check report."""

    if report.status != "PASS":
        raise ValueError("Only passing theme checks may be cached")
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = _entry_path(cache_dir, key)
    payload = {
        "contractVersion": key.contract_version,
        "inputDigest": key.input_digest,
        "report": report.to_dict(),
    }
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=cache_dir)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
