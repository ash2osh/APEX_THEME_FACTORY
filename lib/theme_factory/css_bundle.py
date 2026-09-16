"""CSS flattener, font renderer, and theme stylesheet bundler."""

from pathlib import Path
import re
from typing import Sequence

from lib.theme_factory.manifest import FontFace, ThemeManifest

IMPORT_RE = re.compile(
    r"^[ \t]*@import\s+(?:"
    r"url\(\s*(?:\"(?P<url_dq>[^\"]+)\"|'(?P<url_sq>[^']+)'|(?P<url_bare>[^)\s\"']+))\s*\)"
    r"|\"(?P<dq>[^\"]+)\"|'(?P<sq>[^']+)'"
    r")[ \t]*;[ \t]*(?:\r?\n|$)",
    re.MULTILINE,
)
ANY_IMPORT_RE = re.compile(r"^[ \t]*@import\b", re.MULTILINE)


def _mask_comments(content: str) -> str:
    """Replace comment bytes with spaces while preserving offsets/newlines."""
    chars = list(content)
    index = 0
    while index < len(chars) - 1:
        if chars[index] == "/" and chars[index + 1] == "*":
            end = content.find("*/", index + 2)
            if end == -1:
                end = len(chars) - 2
            for pos in range(index, min(end + 2, len(chars))):
                if chars[pos] not in "\r\n":
                    chars[pos] = " "
            index = end + 2
        else:
            index += 1
    return "".join(chars)

HEADING_SELECTORS = (
    "h1", "h2", "h3", "h4", "h5", "h6",
    ".t-HeroRegion-title",
    ".t-Region-title",
    ".t-Breadcrumb-label",
)


def flatten_css(entry: Path, allowed_roots: Sequence[Path]) -> str:
    """Recursively flatten CSS @import statements into a single stylesheet."""
    entry = entry.resolve()
    resolved_roots = tuple(r.resolve() for r in allowed_roots)

    visited: set[Path] = set()
    active_stack: list[Path] = []

    def _process_file(file_path: Path) -> str:
        if file_path in active_stack:
            raise ValueError(f"CSS import cycle detected: {file_path}")
        if file_path in visited:
            raise ValueError(f"duplicate CSS import: {file_path}")

        if not any(file_path.is_relative_to(r) for r in resolved_roots):
            raise ValueError(f"CSS file '{file_path}' escapes allowed roots")

        if not file_path.exists() or not file_path.is_file():
            raise ValueError(f"CSS file not found: {file_path}")

        visited.add(file_path)
        active_stack.append(file_path)

        content = file_path.read_text(encoding="utf-8")
        scan_content = _mask_comments(content)
        out_chunks = []
        last_idx = 0

        consumed_spans: list[tuple[int, int]] = []
        for match in IMPORT_RE.finditer(scan_content):
            start, end = match.span()
            consumed_spans.append((start, end))
            # Add text before import
            pre_text = content[last_idx:start]
            if pre_text:
                out_chunks.append(pre_text)
            last_idx = end

            target_str = next(
                value
                for value in (
                    match.group("url_dq"),
                    match.group("url_sq"),
                    match.group("url_bare"),
                    match.group("dq"),
                    match.group("sq"),
                )
                if value is not None
            ).strip()
            # Validate target string
            if target_str.startswith(("http://", "https://", "//")):
                raise ValueError(f"remote CSS imports are forbidden: {target_str}")
            if target_str.startswith("data:"):
                raise ValueError(f"data: URL CSS imports are forbidden: {target_str}")

            resolved_target = (file_path.parent / target_str).resolve()
            flattened_import = _process_file(resolved_target)
            out_chunks.append(flattened_import)

        post_text = content[last_idx:]
        if post_text:
            out_chunks.append(post_text)

        masked_remainder = list(scan_content)
        for start, end in consumed_spans:
            for pos in range(start, end):
                if masked_remainder[pos] not in "\r\n":
                    masked_remainder[pos] = " "
        if ANY_IMPORT_RE.search("".join(masked_remainder)):
            raise ValueError(f"unresolved CSS import in {file_path}")

        active_stack.pop()

        res = "".join(out_chunks)
        if not res.endswith("\n"):
            res += "\n"
        return res

    return _process_file(entry)


def internal_family(theme_name: str, role: str) -> str:
    """Return package-prefixed internal font-family name."""
    return f"ThemeFactory-{theme_name}-{role}"


def render_face(theme_name: str, role: str, face: FontFace) -> str:
    """Render single @font-face rule."""
    return (
        "@font-face {\n"
        f'  font-family: "{internal_family(theme_name, role)}";\n'
        f'  src: url("./{face.file.as_posix()}") format("woff2");\n'
        f"  font-weight: {face.weight};\n"
        f"  font-style: {face.style};\n"
        "  font-display: swap;\n"
        "}\n"
    )


def render_font_css(manifest: ThemeManifest) -> str:
    """Render @font-face declarations and scoped tokens from manifest."""
    if not manifest.fonts:
        return ""

    chunks = ["/* ==========================================================================\n   Theme Custom Fonts (@font-face)\n   ========================================================================== */\n"]

    # 1. @font-face rules
    for role_name in ("body", "heading", "mono"):
        if role_name in manifest.fonts:
            role = manifest.fonts[role_name]
            for face in role.faces:
                chunks.append(render_face(manifest.name, role_name, face))

    # 2. Scoped tokens on html.<class>
    chunks.append(f"\n/* Scoped font-family tokens */\nhtml.{manifest.class_name} {{\n")
    
    # Body
    body_role = manifest.fonts["body"]
    body_stack = [f'"{internal_family(manifest.name, "body")}"'] + list(body_role.fallback)
    chunks.append(f"  --app-font-family-body: {', '.join(body_stack)};\n")
    chunks.append("  --a-base-font-family: var(--app-font-family-body);\n")

    # Heading
    if "heading" in manifest.fonts:
        head_role = manifest.fonts["heading"]
        head_stack = [f'"{internal_family(manifest.name, "heading")}"'] + list(head_role.fallback)
        chunks.append(f"  --app-font-family-heading: {', '.join(head_stack)};\n")

    # Mono
    if "mono" in manifest.fonts:
        mono_role = manifest.fonts["mono"]
        mono_stack = [f'"{internal_family(manifest.name, "mono")}"'] + list(mono_role.fallback)
        chunks.append(f"  --app-font-family-mono: {', '.join(mono_stack)};\n")
        chunks.append("  --a-base-font-family-mono: var(--app-font-family-mono);\n")

    chunks.append("}\n")

    # 3. Scoped heading selectors if heading role present
    if "heading" in manifest.fonts:
        sel_list = ",\n".join(f"html.{manifest.class_name} {sel}" for sel in HEADING_SELECTORS)
        chunks.append(f"\n/* Scoped heading typography */\n{sel_list} {{\n  font-family: var(--app-font-family-heading);\n}}\n")

    return "".join(chunks)


def build_theme_css(
    repo_root: Path,
    theme_root: Path,
    manifest: ThemeManifest,
    source_commit: str,
) -> str:
    """Assemble complete standalone theme stylesheet."""
    repo_root = repo_root.resolve()
    theme_root = theme_root.resolve()

    banner = (
        "/**\n"
        f" * Theme: {manifest.name} ({manifest.title})\n"
        f" * Version: {manifest.version}\n"
        f" * Tagline: {manifest.tagline}\n"
        " * Compatibility: APEX 26.1.x / Universal Theme 42 / Iris\n"
        f" * Source commit: {source_commit}\n"
        " */\n\n"
    )

    parts = [banner]

    # 1. Custom font CSS (if any)
    font_css = render_font_css(manifest)
    if font_css:
        parts.append(font_css)
        parts.append("\n")

    # 2. Shared foundation CSS
    foundation_dir = repo_root / "static-files/css/foundation"
    foundation_files = [
        foundation_dir / "tokens.css",
        foundation_dir / "reset.css",
        foundation_dir / "typography.css",
        foundation_dir / "utilities.css",
    ]
    parts.append("/* ==========================================================================\n   Shared Foundation\n   ========================================================================== */\n")
    for f in foundation_files:
        parts.append(flatten_css(f, (foundation_dir,)))

    # 3. Scoped Theme CSS
    theme_css_entry = theme_root / "css/theme.css"
    allowed_theme_roots = (theme_root / "css",)
    parts.append("\n/* ==========================================================================\n   Theme Package Styles\n   ========================================================================== */\n")
    parts.append(flatten_css(theme_css_entry, allowed_theme_roots))

    return "".join(parts)
