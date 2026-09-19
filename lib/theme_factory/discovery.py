"""Strict discovery of Theme Factory source packages."""

from dataclasses import dataclass
from pathlib import Path

from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import ThemeManifest, load_manifest


@dataclass(frozen=True)
class DiscoveredTheme:
    """A validated theme source directory and its manifest."""

    name: str
    root: Path
    manifest: ThemeManifest


def discover_themes(repo_root: Path) -> tuple[DiscoveredTheme, ...]:
    """Return every valid source theme, sorted by manifest name.

    Directories without a manifest are not candidates. A directory with a
    manifest is a candidate and therefore fails discovery loudly when invalid.
    """

    repo_root = Path(repo_root).resolve()
    themes_root = repo_root / "sample-themes"
    found: list[DiscoveredTheme] = []
    for manifest_path in sorted(themes_root.glob("*/theme.json")):
        root = manifest_path.parent
        try:
            manifest = load_manifest(manifest_path, root)
        except PackageError as exc:
            relative = manifest_path.relative_to(repo_root)
            raise PackageError(f"Invalid theme source {relative}: {exc}") from exc
        found.append(DiscoveredTheme(manifest.name, root, manifest))

    folded_names = [theme.name.casefold() for theme in found]
    if len(folded_names) != len(set(folded_names)):
        raise PackageError("Theme names collide when compared case-insensitively")
    return tuple(sorted(found, key=lambda theme: theme.name))


def theme_names(repo_root: Path) -> tuple[str, ...]:
    """Return validated source theme names in deterministic order."""

    return tuple(theme.name for theme in discover_themes(repo_root))
