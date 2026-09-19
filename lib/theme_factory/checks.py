"""Quiet, composed author-lane checks with content-addressed caching."""

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import time

from lib.theme_factory.archive import build_package_from_root, verify_package
from lib.theme_factory.cache import CacheKey, load_cached_report, store_cached_report
from lib.theme_factory.css_bundle import build_theme_css
from lib.theme_factory.css_policy import scan_package
from lib.theme_factory.discovery import discover_themes
from lib.theme_factory.errors import PackageError
from lib.theme_factory.fingerprint import check_uniqueness
from lib.theme_factory.manifest import NAME_REGEX, ThemeManifest, load_manifest
from lib.theme_factory.recipe import ThemeRecipe, load_recipe, validate_core_contrast


CHECK_CONTRACT_VERSION = "1"
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class CheckIssue:
    severity: str
    code: str
    message: str
    path: str = ""
    line: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "line": self.line,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "CheckIssue":
        return cls(
            severity=str(raw["severity"]),
            code=str(raw["code"]),
            message=str(raw["message"]),
            path=str(raw.get("path", "")),
            line=int(raw.get("line", 0)),
        )


@dataclass(frozen=True)
class CheckReport:
    status: str
    theme: str
    cache_hit: bool
    duration_ms: int
    input_digest: str
    issues: tuple[CheckIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "theme": self.theme,
            "cacheHit": self.cache_hit,
            "durationMs": self.duration_ms,
            "inputDigest": self.input_digest,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "CheckReport":
        required = {"status", "theme", "cacheHit", "durationMs", "inputDigest", "issues"}
        if set(raw) != required or not isinstance(raw["issues"], list):
            raise ValueError("Invalid cached check report")
        return cls(
            status=str(raw["status"]),
            theme=str(raw["theme"]),
            cache_hit=bool(raw["cacheHit"]),
            duration_ms=int(raw["durationMs"]),
            input_digest=str(raw["inputDigest"]),
            issues=tuple(CheckIssue.from_dict(issue) for issue in raw["issues"]),
        )

    def with_cache_hit(self, cache_hit: bool, duration_ms: int | None = None) -> "CheckReport":
        return replace(
            self,
            cache_hit=cache_hit,
            duration_ms=self.duration_ms if duration_ms is None else duration_ms,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    def to_human(self) -> str:
        cache = "hit" if self.cache_hit else "miss"
        summary = (
            f"THEME_CHECK theme={self.theme} status={self.status} cache={cache} "
            f"duration_ms={self.duration_ms} issues={len(self.issues)}"
        )
        if not self.issues:
            return summary
        details = [
            f"{issue.severity.upper()} {issue.code} {issue.path}:{issue.line} {issue.message}".strip()
            for issue in self.issues
        ]
        return "\n".join((summary, *details))


def _jpeg_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data.startswith(b"\xff\xd8"):
        return None
    offset = 2
    size_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            return None
        length = struct.unpack(">H", data[offset:offset + 2])[0]
        if marker in size_markers and offset + 7 <= len(data):
            height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
            return width, height
        if length < 2:
            return None
        offset += length
    return None


def _hash_file(digest, repo_root: Path, path: Path) -> None:
    relative = path.relative_to(repo_root).as_posix().encode("utf-8")
    data = path.read_bytes()
    mode = stat.S_IMODE(path.stat().st_mode)
    digest.update(len(relative).to_bytes(4, "big"))
    digest.update(relative)
    digest.update(mode.to_bytes(4, "big"))
    digest.update(len(data).to_bytes(8, "big"))
    digest.update(data)


def canonical_input_digest(repo_root: Path, theme_root: Path) -> str:
    """Hash every author-check input while reducing previews to cover dimensions."""

    repo_root = Path(repo_root).resolve()
    theme_root = Path(theme_root).resolve()
    digest = hashlib.sha256()
    digest.update(f"check-contract:{CHECK_CONTRACT_VERSION}\n".encode("utf-8"))

    for path in sorted(theme_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(theme_root)
        if relative.parts and relative.parts[0] == "preview":
            continue
        _hash_file(digest, repo_root, path)

    cover = theme_root / "preview/cover.jpg"
    dimensions = _jpeg_dimensions(cover)
    cover_state = f"cover:{'missing' if not cover.exists() else dimensions}\n"
    digest.update(cover_state.encode("utf-8"))

    direct_inputs = (
        repo_root / "static-files/css/foundation/tokens.css",
        repo_root / "installer/theme-factory-runtime.js",
        repo_root / "installer/install.sh",
        repo_root / "installer/uninstall.sh",
        repo_root / "tools/font-tools-requirements.txt",
    )
    for path in direct_inputs:
        if path.is_file():
            _hash_file(digest, repo_root, path)
    for directory in (repo_root / "theme-templates", repo_root / "installer/templates"):
        if directory.is_dir():
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    _hash_file(digest, repo_root, path)
    return digest.hexdigest()


def _relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _cover_issues(repo_root: Path, theme_root: Path, manifest: ThemeManifest | None) -> list[CheckIssue]:
    cover = theme_root / (manifest.cover if manifest else Path("preview/cover.jpg"))
    relative = _relative(repo_root, cover)
    if not cover.is_file():
        return [CheckIssue("error", "COVER_MISSING", "Declared 960px gallery cover is missing", relative)]
    dimensions = _jpeg_dimensions(cover)
    if dimensions is None:
        return [CheckIssue("error", "COVER_INVALID", "Gallery cover is not a readable JPEG", relative)]
    if dimensions[0] != 960:
        return [
            CheckIssue(
                "error",
                "COVER_WIDTH",
                f"Gallery cover width is {dimensions[0]}px; expected 960px",
                relative,
            )
        ]
    return []


def _font_provenance_issues(repo_root: Path, theme_root: Path, recipe: ThemeRecipe | None) -> list[CheckIssue]:
    if recipe is None or recipe.font_provenance is None:
        return []
    issues = []
    for face in recipe.font_provenance.faces:
        path = theme_root / face.file
        relative = _relative(repo_root, path)
        if not path.is_file():
            issues.append(CheckIssue("error", "FONT_FILE_MISSING", "Provenance font file is missing", relative))
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != face.sha256:
            issues.append(
                CheckIssue("error", "FONT_HASH_MISMATCH", f"Expected SHA-256 {face.sha256}, got {actual}", relative)
            )
    return issues


def _sort_issues(issues: list[CheckIssue]) -> tuple[CheckIssue, ...]:
    return tuple(
        sorted(
            issues,
            key=lambda issue: (
                SEVERITY_ORDER.get(issue.severity, 99),
                issue.code,
                issue.path,
                issue.line,
                issue.message,
            ),
        )
    )


def run_theme_checks(repo_root: Path, theme_name: str, use_cache: bool = True) -> CheckReport:
    """Run all cheap author checks directly and aggregate every finding."""

    if not isinstance(theme_name, str) or not NAME_REGEX.fullmatch(theme_name):
        raise PackageError(f"Invalid theme name '{theme_name}'")

    started = time.perf_counter()
    repo_root = Path(repo_root).resolve()
    theme_root = repo_root / "sample-themes" / theme_name
    input_digest = canonical_input_digest(repo_root, theme_root)
    key = CacheKey(CHECK_CONTRACT_VERSION, input_digest)
    cache_dir = repo_root / ".theme-factory/cache/checks" / theme_name
    if use_cache:
        cached = load_cached_report(cache_dir, key)
        if cached is not None:
            elapsed = round((time.perf_counter() - started) * 1000)
            return cached.with_cache_hit(True, elapsed)

    issues: list[CheckIssue] = []
    manifest = None
    recipe = None
    try:
        manifest = load_manifest(theme_root / "theme.json", theme_root)
    except PackageError as exc:
        issues.append(CheckIssue("error", "MANIFEST_INVALID", str(exc), _relative(repo_root, theme_root / "theme.json")))

    recipe_path = theme_root / "theme.recipe.json"
    if recipe_path.is_file():
        try:
            recipe = load_recipe(recipe_path)
            for finding in validate_core_contrast(recipe):
                issues.append(CheckIssue(finding.severity, finding.code, finding.message, _relative(repo_root, recipe_path)))
        except PackageError as exc:
            issues.append(CheckIssue("error", "RECIPE_INVALID", str(exc), _relative(repo_root, recipe_path)))

    if manifest is not None:
        try:
            for violation in scan_package(theme_root, repo_root):
                code = "CSS_" + violation.code.replace("-", "_").upper()
                issues.append(
                    CheckIssue(
                        "error",
                        code,
                        violation.message,
                        _relative(repo_root, violation.path),
                        violation.line,
                    )
                )
        except (PackageError, ValueError) as exc:
            issues.append(CheckIssue("error", "CSS_SCAN_FAILED", str(exc), _relative(repo_root, theme_root / "css")))
        try:
            build_theme_css(repo_root, theme_root, manifest, "author-check")
        except (PackageError, ValueError, OSError) as exc:
            issues.append(CheckIssue("error", "BUNDLE_INVALID", str(exc), _relative(repo_root, theme_root / "css/theme.css")))

    issues.extend(_cover_issues(repo_root, theme_root, manifest))
    issues.extend(_font_provenance_issues(repo_root, theme_root, recipe))

    try:
        roots = tuple(theme.root for theme in discover_themes(repo_root))
        if manifest is not None:
            for finding in check_uniqueness(theme_root, roots):
                issues.append(
                    CheckIssue(
                        finding.severity,
                        finding.code,
                        finding.message,
                        _relative(repo_root, theme_root),
                    )
                )
    except (PackageError, ValueError, OSError) as exc:
        issues.append(CheckIssue("error", "UNIQUENESS_FAILED", str(exc), _relative(repo_root, theme_root)))

    if manifest is not None:
        try:
            with tempfile.TemporaryDirectory(prefix="theme-author-check-") as temporary:
                package = build_package_from_root(
                    repo_root,
                    theme_root,
                    Path(temporary),
                    source_identity="author-check",
                )
                verify_package(package)
        except (PackageError, ValueError, OSError) as exc:
            issues.append(CheckIssue("error", "ARCHIVE_INVALID", str(exc), _relative(repo_root, theme_root)))

    sorted_issues = _sort_issues(issues)
    status = "ERROR" if any(issue.severity == "error" for issue in sorted_issues) else "PASS"
    elapsed = round((time.perf_counter() - started) * 1000)
    report = CheckReport(status, theme_name, False, elapsed, input_digest, sorted_issues)
    if use_cache and report.status == "PASS":
        store_cached_report(cache_dir, key, report)
    return report
