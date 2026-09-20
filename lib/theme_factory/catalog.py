"""Evidence-bound catalog generation for every discovered theme package."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Mapping

from lib.theme_factory.archive import verify_package
from lib.theme_factory.discovery import DiscoveredTheme, discover_themes
from lib.theme_factory.errors import PackageError
from lib.theme_factory.gitstate import last_source_commit
from lib.theme_factory.release import calculate_layer_statuses, load_evidence, release_verdict


@dataclass(frozen=True)
class CatalogTheme:
    name: str
    title: str
    version: str
    tagline: str
    direction: str
    font_families: tuple[str, ...]
    verdict: str
    status_detail: str
    layers: dict[str, str]
    evidence_dir: Path | None = None
    package_path: Path | None = None


def _newest_evidence_dir(evidence_root: Path, theme_name: str) -> Path | None:
    candidates = [
        path for path in evidence_root.glob(f"*-release-{theme_name}")
        if path.is_dir() and (path / "evidence.json").is_file()
    ]
    return max(candidates, key=lambda path: (path.name, path.stat().st_mtime_ns)) if candidates else None


def _package_identity(repo_root: Path, theme: DiscoveredTheme) -> tuple[str | None, Path | None]:
    package = repo_root / "dist" / theme.name / f"{theme.name}-{theme.manifest.version}.zip"
    if not package.is_file():
        return None, None
    manifest = verify_package(package)
    if manifest.name != theme.name or manifest.version != theme.manifest.version:
        raise PackageError(f"Package identity mismatch for {theme.name}")
    return hashlib.sha256(package.read_bytes()).hexdigest(), package


def _short_reason(message: str, limit: int = 140) -> str:
    compact = " ".join(message.split())
    if compact.startswith("Evidence artifact is for Git commit"):
        return "release evidence is bound to a different source identity"
    if "package SHA-256" in compact or "Package checksum" in compact:
        return "release evidence is bound to a different package artifact"
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def catalog_themes(repo_root: Path, evidence_root: Path) -> tuple[CatalogTheme, ...]:
    """Return discovered themes with verdicts recomputed from current bound evidence."""

    repo_root = Path(repo_root).resolve()
    evidence_root = Path(evidence_root).resolve()
    source_identity = last_source_commit(repo_root)
    result: list[CatalogTheme] = []
    for theme in discover_themes(repo_root):
        evidence_dir = _newest_evidence_dir(evidence_root, theme.name)
        reason = ""
        package_digest = None
        package_path = None
        evidence: list[dict[str, object]] = [{
            "layer": "A", "status": "PASS" if source_identity else "UNVERIFIED",
            "check": "source_tree", "path": source_identity or "UNVERIFIED", "details": "catalog source identity",
        }]
        try:
            package_digest, package_path = _package_identity(repo_root, theme)
            evidence.append({
                "layer": "B", "status": "PASS" if package_digest else "UNVERIFIED",
                "check": "package_integrity", "path": str(package_path or "UNVERIFIED"),
                "details": "verified package" if package_digest else "current package artifact unavailable",
            })
            if evidence_dir is not None:
                evidence.extend(load_evidence(
                    evidence_dir,
                    theme.name,
                    expected_git_commit=source_identity,
                    expected_package_sha256=package_digest,
                ))
            else:
                reason = "no release evidence found"
        except PackageError as exc:
            reason = _short_reason(str(exc))

        layers = calculate_layer_statuses(evidence)
        verdict = release_verdict(layers)
        if not reason and verdict != "VERIFIED":
            missing = [layer for layer in "ABCDE" if layers.get(layer) != "PASS"]
            reason = "layers not current: " + ", ".join(missing)
        manifest = theme.manifest
        families = tuple(dict.fromkeys(role.family for role in manifest.fonts.values()))
        result.append(CatalogTheme(
            name=manifest.name,
            title=manifest.title,
            version=manifest.version,
            tagline=manifest.tagline,
            direction=manifest.direction or manifest.tagline,
            font_families=families,
            verdict=verdict,
            status_detail=reason,
            layers=layers,
            evidence_dir=evidence_dir,
            package_path=package_path,
        ))
    return tuple(result)


def update_generated_sections(path: Path, sections: Mapping[str, str], check: bool) -> tuple[Path, ...]:
    """Replace named generated sections atomically while preserving all handwritten bytes."""

    path = Path(path)
    original = path.read_text(encoding="utf-8")
    updated = original
    for name, body in sections.items():
        start = f"<!-- @generated:{name}:start -->"
        end = f"<!-- @generated:{name}:end -->"
        if updated.count(start) != 1 or updated.count(end) != 1:
            raise PackageError(f"Expected exactly one pair of generated markers '{name}' in {path}")
        prefix, remainder = updated.split(start, 1)
        _, suffix = remainder.split(end, 1)
        normalized = body if body.endswith("\n") else body + "\n"
        updated = prefix + start + "\n" + normalized + end + suffix
    if updated == original:
        return ()
    if check:
        return (path,)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return (path,)


def _safe(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _status(theme: CatalogTheme) -> str:
    return theme.verdict if theme.verdict == "VERIFIED" else f"{theme.verdict} — {theme.status_detail}"


def render_readme(themes: tuple[CatalogTheme, ...]) -> str:
    links = ", ".join(f"[{theme.title}](sample-themes/{theme.name}/)" for theme in themes)
    return f"**{len(themes)} themes ship with the factory:** {links}.\n"


def render_sample_catalog(themes: tuple[CatalogTheme, ...]) -> str:
    lines = ["| Theme | Direction | Status |", "|---|---|---|"]
    for theme in themes:
        lines.append(f"| [{theme.name}]({theme.name}/) | {_safe(theme.direction)} | **{_safe(_status(theme))}** |")
    return "\n".join(lines) + "\n"


def render_design_deltas(themes: tuple[CatalogTheme, ...]) -> str:
    lines = ["| Theme | Direction | Typography | Release verdict |", "|---|---|---|---|"]
    for theme in themes:
        fonts = ", ".join(theme.font_families) if theme.font_families else "Iris / system"
        lines.append(f"| `{theme.name}` | {_safe(theme.direction)} | {_safe(fonts)} | `{theme.verdict}` |")
    return "\n".join(lines) + "\n"


def render_release_status(themes: tuple[CatalogTheme, ...]) -> str:
    lines = ["| Theme | A | B | C | D | E | Verdict |", "|---|---:|---:|---:|---:|---:|---|"]
    for theme in themes:
        statuses = [theme.layers.get(layer, "UNVERIFIED") for layer in "ABCDE"]
        lines.append("| " + " | ".join([theme.name, *statuses, _safe(_status(theme))]) + " |")
    return "\n".join(lines) + "\n"


def update_catalog(repo_root: Path, evidence_root: Path, check: bool) -> tuple[Path, ...]:
    repo_root = Path(repo_root).resolve()
    themes = catalog_themes(repo_root, evidence_root)
    specs = (
        (repo_root / "README.md", {"theme-catalog": render_readme(themes)}),
        (repo_root / "sample-themes/README.md", {"theme-catalog": render_sample_catalog(themes)}),
        (repo_root / "docs/DESIGN_SYSTEM.md", {"theme-deltas": render_design_deltas(themes)}),
        (repo_root / "tests/live/RELEASE-MATRIX.md", {"theme-status": render_release_status(themes)}),
    )
    changed: list[Path] = []
    for path, sections in specs:
        changed.extend(update_generated_sections(path, sections, check))
    return tuple(changed)
