"""Atomic, recipe-driven generation of neutral theme package sources."""

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from lib.theme_factory.css_policy import scan_package
from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import ThemeManifest, load_manifest
from lib.theme_factory.recipe import (
    FontFaceSpec,
    FontRoleSpec,
    ThemeRecipe,
    axis_css_values,
    render_manifest,
    render_tokens,
    render_responsive_css,
)


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
    preserved_handwritten: tuple[Path, ...] = ()


def _recipe_document(recipe: ThemeRecipe) -> dict[str, object]:
    raw = asdict(recipe)
    document = {
        # Source emitted by the scaffold is always the current schema. Version-1
        # recipes are accepted by the loader only as a migration input.
        "schemaVersion": 2,
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
        "rhythm": {
            "density": raw["rhythm"]["density"],
            "spacing": raw["rhythm"]["spacing"],
            "typeScale": raw["rhythm"]["type_scale"],
        },
        "interaction": {
            "hover": raw["interaction"]["hover"],
            "selected": raw["interaction"]["selected"],
            "motion": raw["interaction"]["motion"],
        },
        "responsive": {
            "strategy": raw["responsive"]["strategy"],
            "compactControlsAt": raw["responsive"]["compact_controls_at"],
        },
    }
    if recipe.font_provenance is not None:
        provenance = recipe.font_provenance
        document["fontProvenance"] = {
            "family": provenance.family,
            "metadataUrl": provenance.metadata_url,
            "sourceRevision": provenance.source_revision,
            "sourceFilename": provenance.source_filename,
            "repositoryUrl": provenance.repository_url,
            "upstreamCommit": provenance.upstream_commit,
            "license": provenance.license,
            "tools": dict(provenance.tools),
            "faces": [
                {"file": face.file, "weight": face.weight, "sha256": face.sha256}
                for face in provenance.faces
            ],
        }
    return document


def _fallback_stack(recipe: ThemeRecipe) -> str:
    generic = {"serif", "sans-serif", "monospace", "system-ui", "ui-serif", "ui-sans-serif", "ui-monospace"}
    return ", ".join(value if value in generic else json.dumps(value) for value in recipe.typography.fallback)


def _replacements(recipe: ThemeRecipe) -> dict[str, str]:
    identity = recipe.identity
    palette = recipe.palette
    geometry = recipe.geometry
    focus = recipe.focus
    axis = axis_css_values(recipe)
    body_internal = f"ThemeFactory-{identity.name}-body"
    heading_internal = body_internal if recipe.typography.heading_family == "body" else f"ThemeFactory-{identity.name}-heading"
    border_width = {"technical": "2px", "hairline": "1px", "soft": "1px", "strong": "2px"}[geometry.border_style]
    shadow = {
        "none": "none",
        "offset": "4px 4px 0 var(--app-border-color)",
        "layered": "0 10px 30px color-mix(in srgb, var(--theme-page), transparent 30%)",
        "soft": "0 8px 24px color-mix(in srgb, var(--theme-page), transparent 55%)",
    }[geometry.shadow_style]
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
        "__DENSITY_SCALE__": axis["density_scale"],
        "__SPACE_UNIT__": axis["space_unit"],
        "__HEADING_SCALE__": axis["heading_scale"],
        "__HOVER_TRANSFORM__": axis["hover_transform"],
        "__HOVER_SHADOW__": axis["hover_shadow"],
        "__MOTION_DURATION__": axis["motion_duration"],
        "__SELECTED_TREATMENT__": axis["selected_treatment"],
        "__RESPONSIVE_STRATEGY__": axis["responsive_strategy"],
        "__COMPACT_AT__": axis["compact_at"],
        "__BORDER_WIDTH__": border_width,
        "__SHADOW__": shadow,
        "__BODY_INTERNAL__": body_internal,
        "__HEADING_INTERNAL__": heading_internal,
        "__FALLBACK__": _fallback_stack(recipe),
        "__MANIFEST_JSON__": render_manifest(recipe, {}),
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
        if relative.as_posix() == "css/tokens.css.tmpl":
            content = render_tokens(recipe)
        elif relative.as_posix() == "css/apex/responsive.css.tmpl":
            content = render_responsive_css(recipe)
        else:
            content = _render(source.read_text(encoding="utf-8"), replacements)
        target.write_text(content, encoding="utf-8")

    for profile_type, owner in PROFILE_OWNERS.items():
        profile = getattr(recipe.components, profile_type)
        source = templates / "components" / f"{profile_type}-{profile}.css.tmpl"
        if not source.is_file():
            raise PackageError(f"Component profile template not found: {source}")
        target = destination / "css/apex" / f"{owner}.css"
        with target.open("a", encoding="utf-8") as stream:
            stream.write("\n")
            stream.write(_render(source.read_text(encoding="utf-8"), replacements))


_THEME_SCOPE_RE = re.compile(r"app-theme-[a-z0-9]+(?:-[a-z0-9]+)*")


def _normalized_module(content: str) -> str:
    """Normalize only package scope names for the non-copying guard."""

    return _THEME_SCOPE_RE.sub("app-theme-THEME", content)


def _handwritten_module_digests(repo_root: Path, *, excluded: set[Path] | None = None) -> dict[str, Path]:
    excluded = excluded or set()
    found: dict[str, Path] = {}
    for path in sorted((repo_root / "sample-themes").glob("*/css/apex/*.css")):
        if path.resolve() in excluded:
            continue
        content = path.read_text(encoding="utf-8")
        if content.splitlines() and content.splitlines()[0].strip() == GENERATED_MARKER:
            continue
        digest = hashlib.sha256(_normalized_module(content).encode("utf-8")).hexdigest()
        found.setdefault(digest, path)
    return found


def _validate_non_copying(repo_root: Path, theme_root: Path, *, excluded: set[Path] | None = None) -> None:
    handwritten = _handwritten_module_digests(repo_root, excluded=excluded)
    for path in sorted((theme_root / "css/apex").glob("*.css")):
        content = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(_normalized_module(content).encode("utf-8")).hexdigest()
        source = handwritten.get(digest)
        if source is not None:
            raise PackageError(
                f"Generated module {path.name} is an exact normalized copy of handwritten module {source}"
            )


def _validate_rendered(repo_root: Path, theme_root: Path, *, excluded: set[Path] | None = None) -> None:
    load_manifest(theme_root / "theme.json", theme_root)
    violations = scan_package(theme_root, repo_root)
    if violations:
        first = violations[0]
        raise PackageError(f"Generated CSS failed policy: {first.path}:{first.line} {first.code}: {first.message}")
    _validate_non_copying(repo_root, theme_root, excluded=excluded)


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


def _manifest_font_specs(manifest: ThemeManifest) -> dict[str, FontRoleSpec]:
    return {
        role_name: FontRoleSpec(
            family=role.family,
            fallback=role.fallback,
            license=role.license.as_posix(),
            faces=tuple(
                FontFaceSpec(face.file.as_posix(), face.weight, face.style)
                for face in role.faces
            ),
        )
        for role_name, role in manifest.fonts.items()
    }


def owned_source_digest(theme_root: Path) -> str:
    """Hash deterministic generator-owned source without claiming handwritten modules."""

    theme_root = Path(theme_root).resolve()
    owned: list[Path] = []
    for relative in ("theme.json", "theme.recipe.json"):
        candidate = theme_root / relative
        if candidate.is_file():
            owned.append(candidate)
    css_root = theme_root / "css"
    if css_root.is_dir():
        for candidate in sorted(css_root.rglob("*.css")):
            lines = candidate.read_text(encoding="utf-8").splitlines()
            if lines and lines[0] == GENERATED_MARKER:
                owned.append(candidate)

    digest = hashlib.sha256()
    for path in sorted(owned):
        relative = path.relative_to(theme_root).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def regenerate_owned_files(theme_root: Path, recipe: ThemeRecipe) -> ScaffoldResult:
    """Regenerate owned sources and explicitly preserve handwritten CSS modules."""

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
        current_manifest = load_manifest(theme_root / "theme.json", theme_root)
        (staged_theme / "theme.json").write_text(
            render_manifest(recipe, _manifest_font_specs(current_manifest)),
            encoding="utf-8",
        )
        _validate_rendered(
            repo_root,
            staged_theme,
            excluded={theme_root / "css/apex" / path for path in MODULES},
        )
        staged_css = tuple(path for path in sorted((staged_theme / "css").rglob("*.css")))
        css_pairs = tuple((source, theme_root / source.relative_to(staged_theme)) for source in staged_css)
        replace_pairs: list[tuple[Path, Path]] = []
        preserved: list[Path] = []
        for source, target in css_pairs:
            lines = target.read_text(encoding="utf-8").splitlines() if target.is_file() else []
            if lines and lines[0] == GENERATED_MARKER:
                replace_pairs.append((source, target))
            else:
                preserved.append(target)

        for relative in ("theme.json", "theme.recipe.json"):
            replace_pairs.append((staged_theme / relative, theme_root / relative))

        for source, target in replace_pairs:
            temporary = target.with_name(f".{target.name}.theme-factory-tmp")
            temporary.write_bytes(source.read_bytes())
            os.replace(temporary, target)
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
    return ScaffoldResult(
        created=theme_root,
        written=tuple(target for _, target in replace_pairs),
        preserved_handwritten=tuple(preserved),
    )
