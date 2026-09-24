"""Strict source-only theme recipe parsing and static contrast checks."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import APEX_COMPATIBILITY, FONT_NAME_REGEX, NAME_REGEX, VALID_WEIGHTS


HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
CSS_LENGTH = re.compile(r"^(?:0|(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:px|rem|em))$")

MODES = {"light", "dark"}
BORDER_STYLES = {"technical", "hairline", "soft", "strong"}
SHADOW_STYLES = {"none", "offset", "layered", "soft"}
PROFILE_VALUES = {
    "navigation": {"rail", "pill", "editorial", "minimal"},
    "cards": {"flat", "layered", "offset", "buoyant"},
    "buttons": {"square", "rounded", "underline", "pill"},
    "forms": {"dense", "comfortable", "outlined", "soft"},
    "reports": {"ruled", "spacious"},
    "dialogs": {"flat", "layered", "offset"},
}
RHYTHM_VALUES = {
    "density": {"compact", "balanced", "spacious"},
    "spacing": {"technical", "editorial", "soft", "playful"},
    "typeScale": {"compact", "balanced", "editorial", "display"},
}
INTERACTION_VALUES = {
    "hover": {"none", "lift", "shift", "glow"},
    "selected": {"fill", "rail", "underline", "outline"},
    "motion": {"none", "precise", "smooth", "buoyant"},
}
RESPONSIVE_VALUES = {"compress", "reflow", "stack"}
RESPONSIVE_WIDTHS = {0, 375, 768, 1024}
GENERATED_CSS_MARKER = "/* @theme-factory-generated */"


@dataclass(frozen=True)
class Identity:
    name: str
    title: str
    tagline: str
    direction: str
    mode: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class Palette:
    page: str
    card: str
    chrome: str
    text_primary: str
    text_secondary: str
    accent: str
    accent_alt: str
    on_accent: str
    danger: str


@dataclass(frozen=True)
class Typography:
    body_family: str
    heading_family: str
    fallback: tuple[str, ...]
    weights: tuple[int, ...]


@dataclass(frozen=True)
class Geometry:
    radius_small: str
    radius_medium: str
    radius_large: str
    control_height: str
    border_style: str
    shadow_style: str


@dataclass(frozen=True)
class Focus:
    color: str
    width: str
    offset: str


@dataclass(frozen=True)
class ComponentProfiles:
    navigation: str
    cards: str
    buttons: str
    forms: str
    reports: str
    dialogs: str


@dataclass(frozen=True)
class Rhythm:
    density: str
    spacing: str
    type_scale: str


@dataclass(frozen=True)
class Interaction:
    hover: str
    selected: str
    motion: str


@dataclass(frozen=True)
class Responsive:
    strategy: str
    compact_controls_at: int


@dataclass(frozen=True)
class FontProvenanceFace:
    file: str
    weight: int
    sha256: str


@dataclass(frozen=True)
class FontProvenance:
    family: str
    metadata_url: str
    source_revision: str
    source_filename: str
    repository_url: str
    upstream_commit: str
    license: str
    tools: tuple[tuple[str, str], ...]
    faces: tuple[FontProvenanceFace, ...]


@dataclass(frozen=True)
class ThemeRecipe:
    schema_version: int
    identity: Identity
    palette: Palette
    typography: Typography
    geometry: Geometry
    focus: Focus
    components: ComponentProfiles
    font_provenance: FontProvenance | None = None
    rhythm: Rhythm = Rhythm("balanced", "technical", "balanced")
    interaction: Interaction = Interaction("none", "fill", "precise")
    responsive: Responsive = Responsive("reflow", 768)


@dataclass(frozen=True)
class FontFaceSpec:
    file: str
    weight: int
    style: str = "normal"


@dataclass(frozen=True)
class FontRoleSpec:
    family: str
    fallback: tuple[str, ...]
    license: str
    faces: tuple[FontFaceSpec, ...]


@dataclass(frozen=True)
class RecipeIssue:
    code: str
    severity: str
    foreground: str
    background: str
    ratio: float
    minimum: float

    @property
    def message(self) -> str:
        return (
            f"{self.code}: {self.foreground} on {self.background} is "
            f"{self.ratio:.2f}:1; requires {self.minimum:.1f}:1"
        )


def _check_allowed_keys(value: dict[str, Any], allowed: set[str], path: str) -> None:
    for key in value:
        if key not in allowed:
            prop = f"{path}/{key}" if path else key
            raise PackageError(f"Unknown property '{prop}'")


def _object(raw: dict[str, Any], key: str, allowed: set[str]) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise PackageError(f"'{key}' must be an object")
    _check_allowed_keys(value, allowed, key)
    missing = sorted(allowed - value.keys())
    if missing:
        raise PackageError(f"Missing required property '{key}/{missing[0]}'")
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PackageError(f"'{path}' must be a non-empty string")
    return value.strip()


def _color(value: Any, path: str) -> str:
    if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
        raise PackageError(f"'{path}' must be a #RRGGBB color")
    return value.upper()


def _length(value: Any, path: str) -> str:
    if not isinstance(value, str) or not CSS_LENGTH.fullmatch(value):
        raise PackageError(f"'{path}' must be a CSS length using px, rem, or em")
    return value


def _choice(value: Any, path: str, allowed: set[str]) -> str:
    if value not in allowed:
        raise PackageError(f"'{path}' must be one of {sorted(allowed)}")
    return value


def load_recipe(path: Path) -> ThemeRecipe:
    """Load a strict recipe whose identity matches its source directory."""

    path = Path(path).resolve()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"Invalid JSON in recipe {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise PackageError("Recipe root must be an object")

    required_root_keys = {"schemaVersion", "identity", "palette", "typography", "geometry", "focus", "components"}
    root_keys = {*required_root_keys, "fontProvenance", "rhythm", "interaction", "responsive"}
    _check_allowed_keys(raw, root_keys, "")
    missing = sorted(required_root_keys - raw.keys())
    if missing:
        raise PackageError(f"Missing required property '{missing[0]}'")
    schema_version = raw["schemaVersion"]
    if schema_version not in {1, 2}:
        raise PackageError("schemaVersion must be 1 or 2")

    identity_raw = _object(
        raw,
        "identity",
        {"name", "title", "tagline", "direction", "mode", "keywords"},
    )
    name = identity_raw["name"]
    if not isinstance(name, str) or not NAME_REGEX.fullmatch(name):
        raise PackageError(f"identity/name '{name}' must match {NAME_REGEX.pattern}")
    if path.parent.name != name:
        raise PackageError(f"identity/name '{name}' does not match recipe directory '{path.parent.name}'")
    keywords_raw = identity_raw["keywords"]
    if not isinstance(keywords_raw, list) or not keywords_raw:
        raise PackageError("'identity/keywords' must be a non-empty list")
    keywords = tuple(_text(item, "identity/keywords") for item in keywords_raw)
    if len(keywords) != len(set(keywords)):
        raise PackageError("'identity/keywords' must contain unique values")
    identity = Identity(
        name=name,
        title=_text(identity_raw["title"], "identity/title"),
        tagline=_text(identity_raw["tagline"], "identity/tagline"),
        direction=_text(identity_raw["direction"], "identity/direction"),
        mode=_choice(identity_raw["mode"], "identity/mode", MODES),
        keywords=keywords,
    )

    palette_raw = _object(
        raw,
        "palette",
        {"page", "card", "chrome", "textPrimary", "textSecondary", "accent", "accentAlt", "onAccent", "danger"},
    )
    palette = Palette(
        page=_color(palette_raw["page"], "palette/page"),
        card=_color(palette_raw["card"], "palette/card"),
        chrome=_color(palette_raw["chrome"], "palette/chrome"),
        text_primary=_color(palette_raw["textPrimary"], "palette/textPrimary"),
        text_secondary=_color(palette_raw["textSecondary"], "palette/textSecondary"),
        accent=_color(palette_raw["accent"], "palette/accent"),
        accent_alt=_color(palette_raw["accentAlt"], "palette/accentAlt"),
        on_accent=_color(palette_raw["onAccent"], "palette/onAccent"),
        danger=_color(palette_raw["danger"], "palette/danger"),
    )

    typography_raw = _object(raw, "typography", {"bodyFamily", "headingFamily", "fallback", "weights"})
    body_family = _text(typography_raw["bodyFamily"], "typography/bodyFamily")
    heading_family = _text(typography_raw["headingFamily"], "typography/headingFamily")
    if not FONT_NAME_REGEX.fullmatch(body_family):
        raise PackageError("'typography/bodyFamily' is not a valid font family")
    if heading_family != "body" and not FONT_NAME_REGEX.fullmatch(heading_family):
        raise PackageError("'typography/headingFamily' must be 'body' or a valid font family")
    fallback_raw = typography_raw["fallback"]
    if not isinstance(fallback_raw, list) or not fallback_raw:
        raise PackageError("'typography/fallback' must be a non-empty list")
    fallback = tuple(_text(item, "typography/fallback") for item in fallback_raw)
    if len(fallback) != len(set(fallback)):
        raise PackageError("'typography/fallback' must contain unique values")
    weights_raw = typography_raw["weights"]
    if not isinstance(weights_raw, list) or not weights_raw:
        raise PackageError("'typography/weights' must be a non-empty list")
    if any(not isinstance(weight, int) or isinstance(weight, bool) or weight not in VALID_WEIGHTS for weight in weights_raw):
        raise PackageError("'typography/weights' contains a value that is not a valid font weight")
    if len(weights_raw) != len(set(weights_raw)):
        raise PackageError("'typography/weights' must contain unique values")
    typography = Typography(body_family, heading_family, fallback, tuple(weights_raw))

    geometry_raw = _object(
        raw,
        "geometry",
        {"radiusSmall", "radiusMedium", "radiusLarge", "controlHeight", "borderStyle", "shadowStyle"},
    )
    geometry = Geometry(
        radius_small=_length(geometry_raw["radiusSmall"], "geometry/radiusSmall"),
        radius_medium=_length(geometry_raw["radiusMedium"], "geometry/radiusMedium"),
        radius_large=_length(geometry_raw["radiusLarge"], "geometry/radiusLarge"),
        control_height=_length(geometry_raw["controlHeight"], "geometry/controlHeight"),
        border_style=_choice(geometry_raw["borderStyle"], "geometry/borderStyle", BORDER_STYLES),
        shadow_style=_choice(geometry_raw["shadowStyle"], "geometry/shadowStyle", SHADOW_STYLES),
    )

    focus_raw = _object(raw, "focus", {"color", "width", "offset"})
    focus = Focus(
        color=_color(focus_raw["color"], "focus/color"),
        width=_length(focus_raw["width"], "focus/width"),
        offset=_length(focus_raw["offset"], "focus/offset"),
    )

    component_raw = _object(raw, "components", set(PROFILE_VALUES))
    components = ComponentProfiles(
        navigation=_choice(component_raw["navigation"], "components/navigation", PROFILE_VALUES["navigation"]),
        cards=_choice(component_raw["cards"], "components/cards", PROFILE_VALUES["cards"]),
        buttons=_choice(component_raw["buttons"], "components/buttons", PROFILE_VALUES["buttons"]),
        forms=_choice(component_raw["forms"], "components/forms", PROFILE_VALUES["forms"]),
        reports=_choice(component_raw["reports"], "components/reports", PROFILE_VALUES["reports"]),
        dialogs=_choice(component_raw["dialogs"], "components/dialogs", PROFILE_VALUES["dialogs"]),
    )

    if schema_version == 2:
        rhythm_raw = _object(raw, "rhythm", set(RHYTHM_VALUES))
        rhythm = Rhythm(
            density=_choice(rhythm_raw["density"], "rhythm/density", RHYTHM_VALUES["density"]),
            spacing=_choice(rhythm_raw["spacing"], "rhythm/spacing", RHYTHM_VALUES["spacing"]),
            type_scale=_choice(rhythm_raw["typeScale"], "rhythm/typeScale", RHYTHM_VALUES["typeScale"]),
        )
        interaction_raw = _object(raw, "interaction", set(INTERACTION_VALUES))
        interaction = Interaction(
            hover=_choice(interaction_raw["hover"], "interaction/hover", INTERACTION_VALUES["hover"]),
            selected=_choice(interaction_raw["selected"], "interaction/selected", INTERACTION_VALUES["selected"]),
            motion=_choice(interaction_raw["motion"], "interaction/motion", INTERACTION_VALUES["motion"]),
        )
        responsive_raw = _object(raw, "responsive", {"strategy", "compactControlsAt"})
        strategy = _choice(responsive_raw["strategy"], "responsive/strategy", RESPONSIVE_VALUES)
        compact_at = responsive_raw["compactControlsAt"]
        if isinstance(compact_at, bool) or not isinstance(compact_at, int) or compact_at not in RESPONSIVE_WIDTHS:
            raise PackageError("'responsive/compactControlsAt' must be one of [0, 375, 768, 1024]")
        responsive = Responsive(strategy, compact_at)
    else:
        rhythm = Rhythm("balanced", "technical", "balanced")
        interaction = Interaction("none", "fill", "precise")
        responsive = Responsive("reflow", 768)

    font_provenance = None
    if "fontProvenance" in raw:
        provenance_raw = _object(
            raw,
            "fontProvenance",
            {
                "family", "metadataUrl", "sourceRevision", "sourceFilename", "repositoryUrl",
                "upstreamCommit", "license", "tools", "faces",
            },
        )
        tools_raw = provenance_raw["tools"]
        if not isinstance(tools_raw, dict) or not tools_raw:
            raise PackageError("'fontProvenance/tools' must be a non-empty object")
        for tool_name, version in tools_raw.items():
            _text(tool_name, "fontProvenance/tools")
            _text(version, f"fontProvenance/tools/{tool_name}")
        faces_raw = provenance_raw["faces"]
        if not isinstance(faces_raw, list) or not faces_raw:
            raise PackageError("'fontProvenance/faces' must be a non-empty list")
        provenance_faces = []
        for index, face_raw in enumerate(faces_raw):
            path = f"fontProvenance/faces/{index}"
            if not isinstance(face_raw, dict):
                raise PackageError(f"'{path}' must be an object")
            _check_allowed_keys(face_raw, {"file", "weight", "sha256"}, path)
            if set(face_raw) != {"file", "weight", "sha256"}:
                raise PackageError(f"'{path}' must contain file, weight, and sha256")
            file_name = _text(face_raw["file"], f"{path}/file")
            weight = face_raw["weight"]
            digest = face_raw["sha256"]
            if not isinstance(weight, int) or isinstance(weight, bool) or weight not in VALID_WEIGHTS:
                raise PackageError(f"'{path}/weight' is not a valid font weight")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise PackageError(f"'{path}/sha256' must be a lowercase SHA-256 digest")
            provenance_faces.append(FontProvenanceFace(file_name, weight, digest))
        font_provenance = FontProvenance(
            family=_text(provenance_raw["family"], "fontProvenance/family"),
            metadata_url=_text(provenance_raw["metadataUrl"], "fontProvenance/metadataUrl"),
            source_revision=_text(provenance_raw["sourceRevision"], "fontProvenance/sourceRevision"),
            source_filename=_text(provenance_raw["sourceFilename"], "fontProvenance/sourceFilename"),
            repository_url=_text(provenance_raw["repositoryUrl"], "fontProvenance/repositoryUrl"),
            upstream_commit=_text(provenance_raw["upstreamCommit"], "fontProvenance/upstreamCommit"),
            license=_text(provenance_raw["license"], "fontProvenance/license"),
            tools=tuple(sorted((str(key), str(value)) for key, value in tools_raw.items())),
            faces=tuple(provenance_faces),
        )

    return ThemeRecipe(
        schema_version, identity, palette, typography, geometry, focus, components,
        font_provenance, rhythm, interaction, responsive,
    )


def _linear(channel: int) -> float:
    value = channel / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG 2.x contrast ratio for two opaque #RRGGBB colors."""

    foreground = _color(foreground, "foreground")
    background = _color(background, "background")

    def luminance(color: str) -> float:
        red, green, blue = (int(color[index:index + 2], 16) for index in (1, 3, 5))
        return 0.2126 * _linear(red) + 0.7152 * _linear(green) + 0.0722 * _linear(blue)

    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def validate_core_contrast(recipe: ThemeRecipe) -> tuple[RecipeIssue, ...]:
    """Return every failed static core color pair; browser evidence remains authoritative."""

    palette = recipe.palette
    checks = (
        ("CONTRAST_PRIMARY_PAGE", palette.text_primary, palette.page, 4.5),
        ("CONTRAST_PRIMARY_CARD", palette.text_primary, palette.card, 4.5),
        ("CONTRAST_SECONDARY_PAGE", palette.text_secondary, palette.page, 4.5),
        ("CONTRAST_SECONDARY_CARD", palette.text_secondary, palette.card, 4.5),
        ("CONTRAST_ON_ACCENT", palette.on_accent, palette.accent, 4.5),
        ("CONTRAST_ON_ACCENT_ALT", palette.on_accent, palette.accent_alt, 4.5),
        ("CONTRAST_FOCUS_PAGE", recipe.focus.color, palette.page, 3.0),
        ("CONTRAST_FOCUS_CARD", recipe.focus.color, palette.card, 3.0),
        ("CONTRAST_DANGER_CARD", palette.danger, palette.card, 4.5),
    )
    issues = []
    for code, foreground, background, minimum in checks:
        ratio = contrast_ratio(foreground, background)
        if ratio < minimum:
            issues.append(RecipeIssue(code, "error", foreground, background, ratio, minimum))
    return tuple(issues)


def _font_role_document(role: FontRoleSpec) -> dict[str, object]:
    return {
        "family": role.family,
        "fallback": list(role.fallback),
        "license": role.license,
        "faces": [
            {"file": face.file, "weight": face.weight, "style": face.style}
            for face in role.faces
        ],
    }


def render_manifest(recipe: ThemeRecipe, font_roles: dict[str, FontRoleSpec]) -> str:
    """Render a stable package manifest from a validated recipe."""

    identity = recipe.identity
    document: dict[str, object] = {
        "schemaVersion": 1,
        "name": identity.name,
        "title": identity.title,
        "version": "1.0.0",
        "tagline": identity.tagline,
        "direction": identity.direction,
        "class": f"app-theme-{identity.name}",
        "compatibility": {
            "apex": APEX_COMPATIBILITY,
            "themeNumber": 42,
            "baseTheme": "ut-26.1",
            "themeStyle": "Iris",
        },
        "templateOptions": {"navigationMenuStyle": "t-TreeNav--styleB"},
    }
    if font_roles:
        document["fonts"] = {
            role_name: _font_role_document(font_roles[role_name])
            for role_name in ("body", "heading", "mono")
            if role_name in font_roles
        }
    document["assets"] = {
        "stylesheet": "theme.css",
        "runtime": "theme-factory-runtime.js",
        "cover": "preview/cover.jpg",
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def _css_font_stack(values: tuple[str, ...]) -> str:
    generic = {
        "serif", "sans-serif", "monospace", "system-ui", "ui-serif",
        "ui-sans-serif", "ui-monospace",
    }
    return ", ".join(value if value in generic else json.dumps(value) for value in values)


def axis_css_values(recipe: ThemeRecipe) -> dict[str, str]:
    """Map schema-v2 identity axes to deterministic CSS values."""

    density_scale = {"compact": "0.875", "balanced": "1", "spacious": "1.125"}[recipe.rhythm.density]
    space_unit = {"technical": "0.375rem", "editorial": "0.5rem", "soft": "0.625rem", "playful": "0.75rem"}[recipe.rhythm.spacing]
    heading_scale = {"compact": "1.125", "balanced": "1.25", "editorial": "1.375", "display": "1.5"}[recipe.rhythm.type_scale]
    hover_transform = {"none": "none", "lift": "translateY(-2px)", "shift": "translateX(2px)", "glow": "none"}[recipe.interaction.hover]
    hover_shadow = (
        "0 0 0 3px color-mix(in srgb, var(--app-accent), transparent 70%)"
        if recipe.interaction.hover == "glow" else "none"
    )
    motion_duration = {"none": "0ms", "precise": "120ms", "smooth": "180ms", "buoyant": "240ms"}[recipe.interaction.motion]
    responsive_tokens = ""
    responsive_hooks = ""
    if recipe.responsive.strategy == "compress":
        # From the recipe's literals: a custom property that reads itself is a cycle, and the browser then
        # treats it as unset (controls lost their min-height on narrow screens).
        responsive_tokens = (
            f"--app-control-h: calc({recipe.geometry.control_height} * 0.875);\n"
            f"    --app-space-unit: calc({space_unit} * 0.875);"
        )
    elif recipe.responsive.strategy == "reflow":
        responsive_hooks = (
            "html.app-theme-__NAME__ .t-Header-controls,\n"
            "html.app-theme-__NAME__ .t-Body-actions { flex-wrap: wrap; }"
        )
    else:
        responsive_hooks = (
            "html.app-theme-__NAME__ .t-Cards,\n"
            "html.app-theme-__NAME__ .t-Region--cards .t-Cards-body { grid-template-columns: 1fr; }"
        )
    return {
        "density_scale": density_scale,
        "space_unit": space_unit,
        "heading_scale": heading_scale,
        "hover_transform": hover_transform,
        "hover_shadow": hover_shadow,
        "motion_duration": motion_duration,
        "selected_treatment": recipe.interaction.selected,
        "responsive_strategy": recipe.responsive.strategy,
        "compact_at": str(recipe.responsive.compact_controls_at),
        "responsive_tokens": responsive_tokens,
        "responsive_hooks": responsive_hooks,
    }


def render_tokens(recipe: ThemeRecipe) -> str:
    """Compile semantic and Iris token layers in deterministic source order."""

    name = recipe.identity.name
    palette = recipe.palette
    geometry = recipe.geometry
    focus = recipe.focus
    body_family = f"ThemeFactory-{name}-body"
    heading_family = body_family if recipe.typography.heading_family == "body" else f"ThemeFactory-{name}-heading"
    fallback = _css_font_stack(recipe.typography.fallback)
    axis = axis_css_values(recipe)
    border_width = {"technical": "2px", "hairline": "1px", "soft": "1px", "strong": "2px"}[geometry.border_style]
    shadow = {
        "none": "none",
        "offset": "4px 4px 0 var(--app-border-color)",
        "layered": "0 10px 30px color-mix(in srgb, var(--theme-page), transparent 30%)",
        "soft": "0 8px 24px color-mix(in srgb, var(--theme-page), transparent 55%)",
    }[geometry.shadow_style]
    lines = [
        GENERATED_CSS_MARKER,
        "/* generated-from: theme-templates/neutral */",
        f"/* Deterministic recipe tokens for html.app-theme-{name}. */",
        f"html.app-theme-{name} {{",
        f"  color-scheme: {recipe.identity.mode};",
        f"  --theme-page: {palette.page};",
        f"  --theme-card: {palette.card};",
        f"  --theme-chrome: {palette.chrome};",
        f"  --theme-text-primary: {palette.text_primary};",
        f"  --theme-text-secondary: {palette.text_secondary};",
        f"  --theme-accent: {palette.accent};",
        f"  --theme-accent-alt: {palette.accent_alt};",
        f"  --theme-on-accent: {palette.on_accent};",
        f"  --theme-danger: {palette.danger};",
        "  --app-surface-page: var(--theme-page);",
        "  --app-surface-card: var(--theme-card);",
        "  --app-surface-chrome: var(--theme-chrome);",
        "  --app-surface-subtle: color-mix(in srgb, var(--theme-card), var(--theme-accent) 5%);",
        "  --app-surface-input: color-mix(in srgb, var(--theme-card), var(--theme-text-primary) 4%);",
        "  --app-surface-hover: color-mix(in srgb, var(--theme-card), var(--theme-accent) 10%);",
        "  --app-surface-selected: color-mix(in srgb, var(--theme-card), var(--theme-accent) 16%);",
        "  --app-text-emphasized: var(--theme-text-primary);",
        "  --app-text-primary: var(--theme-text-primary);",
        "  --app-text-secondary: var(--theme-text-secondary);",
        "  --app-text-on-accent: var(--theme-on-accent);",
        "  --app-accent: var(--theme-accent);",
        "  --app-accent-alt: var(--theme-accent-alt);",
        "  --app-on-accent: var(--theme-on-accent);",
        "  --app-danger: var(--theme-danger);",
        "  --app-color-primary: var(--theme-accent);",
        "  --app-color-info: var(--theme-accent-alt);",
        "  --app-color-danger: var(--theme-danger);",
        "  --app-border-color: color-mix(in srgb, var(--theme-text-secondary), transparent 45%);",
        "  --app-border-strong: color-mix(in srgb, var(--theme-accent-alt), transparent 25%);",
        f"  --app-border-width: {border_width};",
        f"  --app-radius-sm: {geometry.radius_small};",
        f"  --app-radius-md: {geometry.radius_medium};",
        f"  --app-radius-lg: {geometry.radius_large};",
        f"  --app-control-h: {geometry.control_height};",
        f"  --app-density-scale: {axis['density_scale']};",
        f"  --app-space-unit: {axis['space_unit']};",
        f"  --app-heading-scale: {axis['heading_scale']};",
        f"  --app-hover-transform: {axis['hover_transform']};",
        f"  --app-hover-shadow: {axis['hover_shadow']};",
        f"  --app-motion-duration: {axis['motion_duration']};",
        f"  --app-shadow-card: {shadow};",
        f"  --app-focus-color: {focus.color};",
        f"  --app-focus-width: {focus.width};",
        f"  --app-focus-offset: {focus.offset};",
        f'  --app-font-family-body: "{body_family}", {fallback};',
        f'  --app-font-family-heading: "{heading_family}", {fallback};',
        "  --app-font-family-mono: ui-monospace, SFMono-Regular, monospace;",
        "  --oj-core-text-color-primary: var(--app-text-primary);",
        "  --oj-core-text-color-secondary: var(--app-text-secondary);",
        "  --oj-heading-text-color: var(--app-text-emphasized);",
        "  --oj-core-text-color-brand: var(--app-color-primary);",
        "  --oj-link-text-color: var(--app-color-primary);",
        "  --oj-core-divider-color: var(--app-border-color);",
        "  --oj-core-focus-border-color: var(--app-focus-color);",
        "}",
        "",
        f"html.app-theme-{name} .apex-theme-iris {{",
        "  --ut-body-background-color: var(--app-surface-page);",
        "  --ut-body-text-color: var(--app-text-primary);",
        "  --ut-component-background-color: var(--app-surface-card);",
        "  --ut-component-text-default-color: var(--app-text-primary);",
        "  --ut-component-text-title-color: var(--app-text-emphasized);",
        "  --ut-component-text-muted-color: var(--app-text-secondary);",
        "  --ut-component-border-color: var(--app-border-color);",
        "  --ut-component-highlight-background-color: var(--app-surface-hover);",
        "  --ut-focus-outline-color: var(--app-focus-color);",
        "  --ut-link-text-color: var(--app-color-primary);",
        "  --ut-palette-primary: var(--app-color-primary);",
        "  --ut-palette-primary-contrast: var(--app-text-on-accent);",
        "  --ut-palette-primary-shade: var(--app-surface-selected);",
        "  --ut-palette-primary-alt: var(--app-accent-alt);",
        "  --ut-palette-danger: var(--app-color-danger);",
        "  --ut-palette-danger-contrast: var(--app-text-on-accent);",
        "  --ut-palette-danger-shade: var(--app-surface-selected);",
    ]
    if recipe.identity.mode == "dark":
        lines.extend([
            "  --ut-color-scheme: dark;",
            "  --a-palette-primary: var(--ut-palette-primary);",
            "  --a-palette-primary-contrast: var(--ut-palette-primary-contrast);",
            "  --a-palette-primary-shade: var(--ut-palette-primary-shade);",
            "  --a-palette-danger: var(--ut-palette-danger);",
            "  --a-palette-danger-contrast: var(--ut-palette-danger-contrast);",
            "  --a-palette-danger-shade: var(--ut-palette-danger-shade);",
            "  --a-checkbox-background-color: var(--app-surface-input);",
            "  --a-checkbox-border-color: var(--app-border-strong);",
            "  --a-checkbox-checked-background-color: var(--app-accent-alt);",
            "  --a-menu-background-color: var(--app-surface-chrome);",
            "  --a-menu-text-color: var(--app-text-primary);",
            "  --a-gv-background-color: var(--app-surface-card);",
            "  --a-gv-header-background-color: var(--app-surface-chrome);",
            "  --a-datepicker-background-color: var(--app-surface-chrome);",
            "  --a-datepicker-calendar-background-color: var(--app-surface-card);",
            "  --a-datepicker-calendar-day-hover-background-color: var(--app-surface-hover);",
            "  --a-popuplov-chip-background-color: var(--app-surface-hover);",
            "  --a-popuplov-search-background-color: var(--app-surface-input);",
            "  --ui-dialog-content-background-color: var(--app-surface-card);",
            "  --ui-dialog-titlebar-background-color: var(--app-surface-chrome);",
            "  --ui-dialog-titlebar-text-color: var(--app-text-emphasized);",
        ])
    lines.extend(["}", ""])
    return "\n".join(lines)
