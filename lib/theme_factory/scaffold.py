"""Atomic, recipe-driven generation of neutral theme package sources."""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import tempfile

from lib.theme_factory.css_policy import scan_package
from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import load_manifest
from lib.theme_factory.recipe import ThemeRecipe


GENERATED_MARKER = "/* @theme-factory-generated */"
MODULES = ("shell", "regions", "buttons", "forms", "reports", "dialogs", "misc")
PROFILE_OWNERS = {
    "navigation": "shell",
    "cards": "regions",
    "buttons": "buttons",
    "forms": "forms",
    "reports": "reports",
    "dialogs": "dialogs",
}


@dataclass(frozen=True)
class ScaffoldResult:
    created: Path
    written: tuple[Path, ...]


def _recipe_document(recipe: ThemeRecipe) -> dict[str, object]:
    raw = asdict(recipe)
    return {
        "schemaVersion": raw["schema_version"],
        "identity": {
            "name": raw["identity"]["name"],
            "title": raw["identity"]["title"],
            "tagline": raw["identity"]["tagline"],
            "direction": raw["identity"]["direction"],
            "mode": raw["identity"]["mode"],
            "keywords": list(raw["identity"]["keywords"]),
        },
        "palette": {
            "page": raw["palette"]["page"],
            "card": raw["palette"]["card"],
            "chrome": raw["palette"]["chrome"],
            "textPrimary": raw["palette"]["text_primary"],
            "textSecondary": raw["palette"]["text_secondary"],
            "accent": raw["palette"]["accent"],
            "accentAlt": raw["palette"]["accent_alt"],
            "onAccent": raw["palette"]["on_accent"],
            "danger": raw["palette"]["danger"],
        },
        "typography": {
            "bodyFamily": raw["typography"]["body_family"],
            "headingFamily": raw["typography"]["heading_family"],
            "fallback": list(raw["typography"]["fallback"]),
            "weights": list(raw["typography"]["weights"]),
        },
        "geometry": {
            "radiusSmall": raw["geometry"]["radius_small"],
            "radiusMedium": raw["geometry"]["radius_medium"],
            "radiusLarge": raw["geometry"]["radius_large"],
            "controlHeight": raw["geometry"]["control_height"],
            "borderStyle": raw["geometry"]["border_style"],
            "shadowStyle": raw["geometry"]["shadow_style"],
        },
        "focus": {
            "color": raw["focus"]["color"],
            "width": raw["focus"]["width"],
            "offset": raw["focus"]["offset"],
        },
        "components": raw["components"],
    }


def _fallback_stack(recipe: ThemeRecipe) -> str:
    generic = {"serif", "sans-serif", "monospace", "system-ui", "ui-serif", "ui-sans-serif", "ui-monospace"}
    return ", ".join(value if value in generic else json.dumps(value) for value in recipe.typography.fallback)


def _replacements(recipe: ThemeRecipe) -> dict[str, str]:
    identity = recipe.identity
    palette = recipe.palette
    geometry = recipe.geometry
    focus = recipe.focus
    body_internal = f"ThemeFactory-{identity.name}-body"
    heading_internal = body_internal if recipe.typography.heading_family == "body" else f"ThemeFactory-{identity.name}-heading"
    border_width = {"technical": "2px", "hairline": "1px", "soft": "1px", "strong": "2px"}[geometry.border_style]
    shadow = {
        "none": "none",
        "offset": "4px 4px 0 var(--app-border-color)",
        "layered": "0 10px 30px color-mix(in srgb, var(--theme-page), transparent 30%)",
        "soft": "0 8px 24px color-mix(in srgb, var(--theme-page), transparent 55%)",
    }[geometry.shadow_style]
    manifest = {
        "schemaVersion": 1,
        "name": identity.name,
        "title": identity.title,
        "version": "1.0.0",
        "tagline": identity.tagline,
        "class": f"app-theme-{identity.name}",
        "compatibility": {
            "apex": ">=26.1.0 <26.2.0",
            "themeNumber": 42,
            "baseTheme": "ut-26.1",
            "themeStyle": "Iris",
        },
        "templateOptions": {"navigationMenuStyle": "t-TreeNav--styleB"},
        "assets": {
            "stylesheet": "theme.css",
            "runtime": "theme-factory-runtime.js",
            "cover": "preview/cover.jpg",
        },
    }
    return {
        "__NAME__": identity.name,
        "__TITLE__": identity.title,
        "__TAGLINE__": identity.tagline,
        "__DIRECTION__": identity.direction,
        "__MODE__": identity.mode,
        "__KEYWORDS__": ", ".join(identity.keywords),
        "__PAGE__": palette.page,
        "__CARD__": palette.card,
        "__CHROME__": palette.chrome,
        "__TEXT_PRIMARY__": palette.text_primary,
        "__TEXT_SECONDARY__": palette.text_secondary,
        "__ACCENT__": palette.accent,
        "__ACCENT_ALT__": palette.accent_alt,
        "__ON_ACCENT__": palette.on_accent,
        "__DANGER__": palette.danger,
        "__FOCUS_COLOR__": focus.color,
        "__FOCUS_WIDTH__": focus.width,
        "__FOCUS_OFFSET__": focus.offset,
        "__RADIUS_SMALL__": geometry.radius_small,
        "__RADIUS_MEDIUM__": geometry.radius_medium,
        "__RADIUS_LARGE__": geometry.radius_large,
        "__CONTROL_HEIGHT__": geometry.control_height,
        "__BORDER_WIDTH__": border_width,
        "__SHADOW__": shadow,
        "__BODY_INTERNAL__": body_internal,
        "__HEADING_INTERNAL__": heading_internal,
        "__FALLBACK__": _fallback_stack(recipe),
        "__MANIFEST_JSON__": json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        "__RECIPE_JSON__": json.dumps(_recipe_document(recipe), indent=2, ensure_ascii=False) + "\n",
    }


def _render(text: str, replacements: dict[str, str]) -> str:
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    unresolved = sorted(word for word in text.split() if word.startswith("__") and word.endswith("__"))
    if unresolved:
        raise PackageError(f"Unresolved scaffold placeholder: {unresolved[0]}")
    return text


def _render_neutral_tree(repo_root: Path, destination: Path, recipe: ThemeRecipe) -> None:
    templates = repo_root / "theme-templates"
    neutral = templates / "neutral"
    if not neutral.is_dir():
        raise PackageError(f"Neutral theme templates not found: {neutral}")
    destination.mkdir(parents=True)
    replacements = _replacements(recipe)

    for source in sorted(neutral.rglob("*.tmpl")):
        relative = source.relative_to(neutral)
        target = destination / relative.with_suffix("")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render(source.read_text(encoding="utf-8"), replacements), encoding="utf-8")

    for profile_type, owner in PROFILE_OWNERS.items():
        profile = getattr(recipe.components, profile_type)
        source = templates / "components" / f"{profile_type}-{profile}.css.tmpl"
        if not source.is_file():
            raise PackageError(f"Component profile template not found: {source}")
        target = destination / "css/apex" / f"{owner}.css"
        with target.open("a", encoding="utf-8") as stream:
            stream.write("\n")
            stream.write(_render(source.read_text(encoding="utf-8"), replacements))


def _validate_rendered(repo_root: Path, theme_root: Path) -> None:
    load_manifest(theme_root / "theme.json", theme_root)
    violations = scan_package(theme_root, repo_root)
    if violations:
        first = violations[0]
        raise PackageError(f"Generated CSS failed policy: {first.path}:{first.line} {first.code}: {first.message}")


def create_theme(repo_root: Path, recipe: ThemeRecipe) -> ScaffoldResult:
    """Render and atomically publish a new theme directory."""

    repo_root = Path(repo_root).resolve()
    themes_root = repo_root / "sample-themes"
    themes_root.mkdir(parents=True, exist_ok=True)
    destination = themes_root / recipe.identity.name
    if destination.exists():
        raise PackageError(f"Theme directory already exists: {destination}")

    staging_parent = Path(tempfile.mkdtemp(prefix=f".{recipe.identity.name}-", dir=themes_root))
    staged_theme = staging_parent / recipe.identity.name
    try:
        _render_neutral_tree(repo_root, staged_theme, recipe)
        _validate_rendered(repo_root, staged_theme)
        os.replace(staged_theme, destination)
    except Exception:
        shutil.rmtree(staging_parent, ignore_errors=True)
        raise
    shutil.rmtree(staging_parent, ignore_errors=True)
    written = tuple(path for path in sorted(destination.rglob("*")) if path.is_file())
    return ScaffoldResult(created=destination, written=written)


def regenerate_owned_files(theme_root: Path, recipe: ThemeRecipe) -> ScaffoldResult:
    """Regenerate marked CSS sources while refusing to overwrite human-owned files."""

    theme_root = Path(theme_root).resolve()
    if theme_root.name != recipe.identity.name:
        raise PackageError(
            f"Theme directory '{theme_root.name}' does not match recipe '{recipe.identity.name}'"
        )
    repo_root = theme_root.parent.parent
    staging_parent = Path(tempfile.mkdtemp(prefix=f".{recipe.identity.name}-regen-", dir=theme_root.parent))
    staged_theme = staging_parent / recipe.identity.name
    try:
        _render_neutral_tree(repo_root, staged_theme, recipe)
        _validate_rendered(repo_root, staged_theme)
        staged_css = tuple(path for path in sorted((staged_theme / "css").rglob("*.css")))
        targets = tuple(theme_root / path.relative_to(staged_theme) for path in staged_css)
        for target in targets:
            if not target.is_file() or target.read_text(encoding="utf-8").splitlines()[0] != GENERATED_MARKER:
                raise PackageError(f"Refusing to overwrite handwritten file: {target}")

        for source, target in zip(staged_css, targets):
            temporary = target.with_name(f".{target.name}.theme-factory-tmp")
            temporary.write_bytes(source.read_bytes())
            os.replace(temporary, target)
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
    return ScaffoldResult(created=theme_root, written=targets)
