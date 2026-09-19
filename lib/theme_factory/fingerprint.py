"""Explainable structural and visual fingerprints for theme uniqueness checks."""

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re
from typing import Sequence

from lib.theme_factory.manifest import load_manifest
from lib.theme_factory.recipe import ThemeRecipe, load_recipe


MODULES = ("shell", "regions", "buttons", "forms", "reports", "dialogs", "misc")
SCOPE_RE = re.compile(r"app-theme-[a-z0-9]+(?:-[a-z0-9]+)*")
COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
COLOR_RE = re.compile(
    r"(?i)(#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?)\([^)]*\))"
)
DECLARATION_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+);")
PROFILE_RE = re.compile(r"profile:\s*([a-z0-9-]+)", re.IGNORECASE)
TOKEN_RE = re.compile(
    r"--[A-Za-z0-9_-]+|[-+]?(?:\d*\.\d+|\d+)(?:px|rem|em|%)?|"
    r"[.#]?[A-Za-z_][A-Za-z0-9_-]*|[{}:;,()>+~*=\[\]]"
)
SEMANTIC_TOKENS = {
    "page": ("--app-surface-page",),
    "card": ("--app-surface-card",),
    "chrome": ("--app-surface-chrome",),
    "textPrimary": ("--app-text-emphasized", "--app-text-primary"),
    "textSecondary": ("--app-text-secondary",),
    "accent": ("--app-color-primary", "--app-accent"),
    "accentAlt": ("--app-color-info", "--app-accent-alt"),
    "onAccent": ("--app-text-on-accent", "--app-on-accent"),
    "danger": ("--app-color-danger", "--app-danger"),
}


@dataclass(frozen=True)
class ThemeFingerprint:
    name: str
    palette: tuple[tuple[str, str], ...]
    font_family: str
    geometry: tuple[tuple[str, str], ...]
    profiles: tuple[tuple[str, str], ...]
    component_hashes: tuple[tuple[str, str], ...]
    component_shingles: tuple[tuple[str, frozenset[tuple[str, ...]]], ...]


@dataclass(frozen=True)
class SimilarityReport:
    candidate: str
    nearest_theme: str
    css_similarity: float
    palette_delta_e: float
    matching_profiles: tuple[str, ...]
    font_match: bool
    geometry_match: bool


@dataclass(frozen=True)
class UniquenessIssue:
    code: str
    severity: str
    nearest_theme: str
    message: str
    report: SimilarityReport


def _normalize_css(content: str) -> str:
    content = COMMENT_RE.sub(" ", content)
    content = SCOPE_RE.sub("app-theme-THEME", content)
    content = COLOR_RE.sub("COLOR", content)
    return " ".join(content.split())


def _shingles(content: str, width: int = 5) -> frozenset[tuple[str, ...]]:
    tokens = TOKEN_RE.findall(content)
    if not tokens:
        return frozenset()
    if len(tokens) < width:
        return frozenset({tuple(tokens)})
    return frozenset(tuple(tokens[index:index + width]) for index in range(len(tokens) - width + 1))


def _profile_signature(content: str, normalized: str) -> str:
    marker = PROFILE_RE.search(content)
    if marker:
        return marker.group(1).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _css_declarations(content: str) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for name, value in DECLARATION_RE.findall(COMMENT_RE.sub(" ", content)):
        declarations[name] = value.strip()
    return declarations


def _parse_rgb(value: str) -> tuple[float, float, float] | None:
    value = value.strip()
    hex_match = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value)
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) == 3:
            digits = "".join(character * 2 for character in digits)
        return tuple(int(digits[index:index + 2], 16) / 255 for index in (0, 2, 4))
    rgb_match = re.fullmatch(r"rgba?\(([^)]+)\)", value, re.IGNORECASE)
    if rgb_match:
        raw = [part for part in re.split(r"[\s,/]+", rgb_match.group(1).strip()) if part]
        if len(raw) < 3:
            return None
        channels = []
        for part in raw[:3]:
            channels.append(float(part[:-1]) / 100 if part.endswith("%") else float(part) / 255)
        return tuple(max(0.0, min(1.0, channel)) for channel in channels)
    hsl_match = re.fullmatch(r"hsla?\(([^)]+)\)", value, re.IGNORECASE)
    if hsl_match:
        raw = [part for part in re.split(r"[\s,/]+", hsl_match.group(1).strip()) if part]
        if len(raw) < 3 or not raw[1].endswith("%") or not raw[2].endswith("%"):
            return None
        hue = float(raw[0].removesuffix("deg")) % 360 / 360
        saturation = float(raw[1][:-1]) / 100
        lightness = float(raw[2][:-1]) / 100
        if saturation == 0:
            return lightness, lightness, lightness

        def channel(offset: float) -> float:
            position = (hue + offset) % 1
            factor = lightness * (1 + saturation) if lightness < 0.5 else lightness + saturation - lightness * saturation
            base = 2 * lightness - factor
            if position < 1 / 6:
                return base + (factor - base) * 6 * position
            if position < 1 / 2:
                return factor
            if position < 2 / 3:
                return base + (factor - base) * (2 / 3 - position) * 6
            return base

        return channel(1 / 3), channel(0), channel(-1 / 3)
    return None


def _resolve_color(name: str, declarations: dict[str, str], seen: set[str] | None = None) -> str | None:
    seen = set() if seen is None else seen
    if name in seen:
        return None
    seen.add(name)
    value = declarations.get(name, "")
    literal = COLOR_RE.search(value)
    if literal and _parse_rgb(literal.group(1)) is not None:
        return literal.group(1)
    reference = re.search(r"var\(\s*(--[A-Za-z0-9_-]+)", value)
    return _resolve_color(reference.group(1), declarations, seen) if reference else None


def _recipe_palette(recipe: ThemeRecipe) -> tuple[tuple[str, str], ...]:
    palette = recipe.palette
    return (
        ("page", palette.page),
        ("card", palette.card),
        ("chrome", palette.chrome),
        ("textPrimary", palette.text_primary),
        ("textSecondary", palette.text_secondary),
        ("accent", palette.accent),
        ("accentAlt", palette.accent_alt),
        ("onAccent", palette.on_accent),
        ("danger", palette.danger),
    )


def _legacy_palette(declarations: dict[str, str]) -> tuple[tuple[str, str], ...]:
    palette = []
    for semantic, candidates in SEMANTIC_TOKENS.items():
        value = None
        for candidate in candidates:
            value = _resolve_color(candidate, declarations)
            if value is not None:
                break
        if value is not None:
            palette.append((semantic, value))
    return tuple(palette)


def _geometry_from_declarations(declarations: dict[str, str]) -> tuple[tuple[str, str], ...]:
    choices = {
        "radiusSmall": ("--app-radius-sm",),
        "radiusMedium": ("--app-radius-md",),
        "radiusLarge": ("--app-radius-lg",),
        "controlHeight": ("--app-control-h", "--app-control-height"),
        "border": ("--app-border-width", "--app-border-hairline"),
        "shadow": ("--app-shadow-card", "--app-shadow-md"),
    }
    result = []
    for key, names in choices.items():
        value = next((declarations[name] for name in names if name in declarations), "")
        result.append((key, " ".join(value.split())))
    return tuple(result)


def fingerprint_theme(theme_root: Path) -> ThemeFingerprint:
    """Build a recipe-aware fingerprint, falling back to legacy source extraction."""

    theme_root = Path(theme_root).resolve()
    manifest = load_manifest(theme_root / "theme.json", theme_root)
    recipe_path = theme_root / "theme.recipe.json"
    recipe = load_recipe(recipe_path) if recipe_path.is_file() else None
    tokens_path = theme_root / "css/tokens.css"
    token_content = tokens_path.read_text(encoding="utf-8") if tokens_path.is_file() else ""
    declarations = _css_declarations(token_content)

    hashes = []
    shingles = []
    extracted_profiles = []
    for module in MODULES:
        path = theme_root / "css/apex" / f"{module}.css"
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        normalized = _normalize_css(content)
        hashes.append((module, hashlib.sha256(normalized.encode("utf-8")).hexdigest()))
        shingles.append((module, _shingles(normalized)))
        extracted_profiles.append((module, _profile_signature(content, normalized)))

    if recipe:
        palette = _recipe_palette(recipe)
        font_family = recipe.typography.body_family.casefold()
        geometry = (
            ("radiusSmall", recipe.geometry.radius_small),
            ("radiusMedium", recipe.geometry.radius_medium),
            ("radiusLarge", recipe.geometry.radius_large),
            ("controlHeight", recipe.geometry.control_height),
            ("border", recipe.geometry.border_style),
            ("shadow", recipe.geometry.shadow_style),
        )
        profiles = (
            ("shell", f"navigation-{recipe.components.navigation}"),
            ("regions", f"cards-{recipe.components.cards}"),
            ("buttons", f"buttons-{recipe.components.buttons}"),
            ("forms", f"forms-{recipe.components.forms}"),
            ("reports", f"reports-{recipe.components.reports}"),
            ("dialogs", f"dialogs-{recipe.components.dialogs}"),
            ("misc", f"mode-{recipe.identity.mode}"),
        )
    else:
        palette = _legacy_palette(declarations)
        font_family = manifest.fonts.get("body").family.casefold() if "body" in manifest.fonts else "system"
        geometry = _geometry_from_declarations(declarations)
        profiles = tuple(extracted_profiles)

    return ThemeFingerprint(
        name=manifest.name,
        palette=palette,
        font_family=font_family,
        geometry=geometry,
        profiles=profiles,
        component_hashes=tuple(hashes),
        component_shingles=tuple(shingles),
    )


def _srgb_to_lab(color: str) -> tuple[float, float, float]:
    rgb = _parse_rgb(color)
    if rgb is None:
        raise ValueError(f"Unsupported CSS color: {color}")

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in rgb)
    x = (0.4124564 * red + 0.3575761 * green + 0.1804375 * blue) / 0.95047
    y = (0.2126729 * red + 0.7151522 * green + 0.0721750 * blue)
    z = (0.0193339 * red + 0.1191920 * green + 0.9503041 * blue) / 1.08883

    def pivot(value: float) -> float:
        delta = 6 / 29
        return value ** (1 / 3) if value > delta ** 3 else value / (3 * delta ** 2) + 4 / 29

    fx, fy, fz = pivot(x), pivot(y), pivot(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e_1976(left: str, right: str) -> float:
    """Return the CIE76 distance between two opaque CSS colors."""

    left_lab = _srgb_to_lab(left)
    right_lab = _srgb_to_lab(right)
    return math.sqrt(sum((left_lab[index] - right_lab[index]) ** 2 for index in range(3)))


def _jaccard(left: frozenset, right: frozenset) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def compare_fingerprints(candidate: ThemeFingerprint, existing: ThemeFingerprint) -> SimilarityReport:
    candidate_shingles = dict(candidate.component_shingles)
    existing_shingles = dict(existing.component_shingles)
    common_modules = sorted(set(candidate_shingles) & set(existing_shingles))
    css_similarity = (
        sum(_jaccard(candidate_shingles[module], existing_shingles[module]) for module in common_modules)
        / len(common_modules)
        if common_modules
        else 0.0
    )
    candidate_palette = dict(candidate.palette)
    existing_palette = dict(existing.palette)
    common_colors = sorted(set(candidate_palette) & set(existing_palette))
    palette_delta = (
        sum(delta_e_1976(candidate_palette[name], existing_palette[name]) for name in common_colors)
        / len(common_colors)
        if common_colors
        else math.inf
    )
    candidate_profiles = dict(candidate.profiles)
    existing_profiles = dict(existing.profiles)
    matching_profiles = tuple(
        name
        for name in sorted(set(candidate_profiles) & set(existing_profiles))
        if candidate_profiles[name] == existing_profiles[name]
    )
    return SimilarityReport(
        candidate=candidate.name,
        nearest_theme=existing.name,
        css_similarity=css_similarity,
        palette_delta_e=palette_delta,
        matching_profiles=matching_profiles,
        font_match=candidate.font_family == existing.font_family,
        geometry_match=candidate.geometry == existing.geometry,
    )


def _issue(code: str, severity: str, report: SimilarityReport) -> UniquenessIssue:
    delta = "unavailable" if math.isinf(report.palette_delta_e) else f"{report.palette_delta_e:.2f}"
    message = (
        f"{code}: nearest theme {report.nearest_theme}; CSS similarity "
        f"{report.css_similarity:.3f}; palette Delta E {delta}; matching profiles "
        f"{len(report.matching_profiles)}/7; font match {str(report.font_match).lower()}; "
        f"geometry match {str(report.geometry_match).lower()}"
    )
    return UniquenessIssue(code, severity, report.nearest_theme, message, report)


def check_uniqueness(
    candidate_root: Path,
    all_roots: Sequence[Path],
) -> tuple[UniquenessIssue, ...]:
    """Compare a candidate to every other theme and return explainable findings."""

    candidate_root = Path(candidate_root).resolve()
    candidate = fingerprint_theme(candidate_root)
    issues = []
    for root in all_roots:
        root = Path(root).resolve()
        if root == candidate_root:
            continue
        report = compare_fingerprints(candidate, fingerprint_theme(root))
        profile_count = len(report.matching_profiles)
        if report.css_similarity >= 0.98 and profile_count >= 5:
            issues.append(_issue("STRUCTURAL_RECOLOR", "error", report))
            continue
        if (
            report.font_match
            and report.geometry_match
            and profile_count == 7
            and report.palette_delta_e < 12.0
        ):
            issues.append(_issue("IDENTITY_COLLISION", "error", report))
            continue
        if report.css_similarity >= 0.85:
            issues.append(_issue("STRUCTURAL_SIMILARITY", "warning", report))
        elif profile_count >= 5:
            issues.append(_issue("PROFILE_SIMILARITY", "warning", report))
        elif report.font_match and report.geometry_match and report.palette_delta_e < 20.0:
            issues.append(_issue("IDENTITY_SIMILARITY", "warning", report))
    return tuple(sorted(issues, key=lambda issue: (issue.severity != "error", issue.nearest_theme, issue.code)))
