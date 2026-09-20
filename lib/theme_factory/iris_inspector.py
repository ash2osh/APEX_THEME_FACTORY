"""Deterministic inventory and drift reporting for Universal Theme Iris tokens."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable

from lib.theme_factory.errors import PackageError


APEX_VERSION = "26.1"
SOURCE_CANDIDATES = {
    "Core": ("Core.css", "Core.min.css"),
    "Iris": ("Iris.css", "Iris.min.css"),
    "Widget-Core": ("Widget-Core.css", "app_ui-Core.min.css"),
    "Theme-Standard": ("Theme-Standard.css", "app_ui-Theme-Standard.min.css"),
}
TOKEN_RE = re.compile(r"--[A-Za-z0-9_-]+")
DECLARATION_RE = re.compile(r"(?<![A-Za-z0-9_-])(--[A-Za-z0-9_-]+)\s*:")
COLOR_RE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|"
    r"(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix)\s*\([^;{}]*\)|"
    r"\b(?:transparent|currentColor|black|white)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TokenDeclaration:
    file: str
    selector: str
    token: str
    raw_value: str
    offset: int
    is_literal: bool
    is_chain: bool
    fallback_literals: tuple[str, ...]
    color_family: str | None
    color_role: str | None


@dataclass(frozen=True)
class TokenSource:
    file: str
    source_file: str
    sha256: str


@dataclass(frozen=True)
class TokenInventory:
    apex_version: str
    sources: tuple[TokenSource, ...]
    declarations: tuple[TokenDeclaration, ...]

    @property
    def html_only_jet_atoms(self) -> tuple[str, ...]:
        return tuple(sorted({item.token for item in self.declarations
                             if item.token.startswith("--oj-") and item.selector.strip() == "html"}))

    @property
    def widget_fallback_tokens(self) -> tuple[str, ...]:
        widget_files = {"Widget-Core", "Theme-Standard"}
        return tuple(sorted({item.token for item in self.declarations
                             if item.file in widget_files and item.is_chain
                             and item.fallback_literals}))

    @property
    def unpaired_color_families(self) -> tuple[str, ...]:
        roles: dict[str, set[str]] = {}
        for item in self.declarations:
            if item.color_family and item.color_role:
                roles.setdefault(item.color_family, set()).add(item.color_role)
        return tuple(sorted(family for family, found in roles.items()
                            if found != {"text", "background"}))


def _mask_comments_and_strings(text: str) -> str:
    """Blank comments and quoted strings while preserving every character offset."""
    chars = list(text)
    index = 0
    length = len(chars)
    while index < length:
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = length - 2 if end < 0 else end
            for position in range(index, min(length, end + 2)):
                if chars[position] not in "\r\n":
                    chars[position] = " "
            index = end + 2
            continue
        if text[index] in "\"'":
            quote = text[index]
            position = index
            while position < length:
                if position > index and text[position] == quote:
                    backslashes = 0
                    before = position - 1
                    while before >= index and text[before] == "\\":
                        backslashes += 1
                        before -= 1
                    if backslashes % 2 == 0:
                        break
                position += 1
            for masked in range(index, min(length, position + 1)):
                if chars[masked] not in "\r\n":
                    chars[masked] = " "
            index = position + 1
            continue
        index += 1
    return "".join(chars)


def _matching_brace(masked: str, opening: int, limit: int) -> int:
    depth = 1
    for index in range(opening + 1, limit):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise PackageError(f"Unbalanced CSS block at offset {opening}")


def _color_metadata(token: str) -> tuple[str | None, str | None]:
    for suffix, role in (("-background-color", "background"), ("-text-color", "text")):
        if token.endswith(suffix):
            return token[:-len(suffix)], role
    return None, None


def _make_declaration(text: str, logical_file: str, selector: str,
                      token: str, value_start: int, value_end: int,
                      offset: int) -> TokenDeclaration:
    raw_value = text[value_start:value_end].strip()
    literals = tuple(match.group(0).strip() for match in COLOR_RE.finditer(raw_value))
    family, role = _color_metadata(token)
    return TokenDeclaration(
        logical_file, " ".join(selector.split()), token, raw_value, offset,
        bool(literals) and "var(" not in raw_value,
        "var(" in raw_value,
        literals if "var(" in raw_value else (),
        family, role,
    )


def _declarations_in_rule(text: str, masked: str, logical_file: str,
                          selector: str, start: int, end: int) -> list[TokenDeclaration]:
    declarations: list[TokenDeclaration] = []
    curly = 0
    index = start
    while index < end:
        char = masked[index]
        if char == "{":
            curly += 1
            index += 1
            continue
        if char == "}":
            curly = max(0, curly - 1)
            index += 1
            continue
        if curly == 0:
            match = DECLARATION_RE.match(masked, index)
            if match:
                token = match.group(1)
                value_start = match.end()
                position = value_start
                parentheses = 0
                while position < end:
                    value_char = masked[position]
                    if value_char == "(":
                        parentheses += 1
                    elif value_char == ")":
                        parentheses = max(0, parentheses - 1)
                    elif value_char == ";" and parentheses == 0:
                        break
                    elif value_char in "{}" and parentheses == 0:
                        break
                    position += 1
                declarations.append(_make_declaration(
                    text, logical_file, selector, token, value_start, position, match.start(1)
                ))
                index = position + 1
                continue
        index += 1
    return declarations


def _structured_declarations(text: str, logical_file: str) -> tuple[TokenDeclaration, ...]:
    masked = _mask_comments_and_strings(text)
    declarations: list[TokenDeclaration] = []

    def scan(start: int, end: int) -> None:
        cursor = start
        while cursor < end:
            opening = masked.find("{", cursor, end)
            if opening < 0:
                return
            header_start = cursor
            # Semicolon-delimited at-rules before this block are not part of its header.
            prior_semicolon = masked.rfind(";", cursor, opening)
            if prior_semicolon >= cursor:
                header_start = prior_semicolon + 1
            # Use the masked source so comments cannot become part of a selector.
            header = masked[header_start:opening].strip()
            closing = _matching_brace(masked, opening, end)
            if header.startswith("@"):
                scan(opening + 1, closing)
            elif header:
                declarations.extend(_declarations_in_rule(
                    text, masked, logical_file, header, opening + 1, closing
                ))
                scan(opening + 1, closing)
            cursor = closing + 1

    scan(0, len(text))
    return tuple(declarations)


def _independent_tokens(text: str) -> set[str]:
    masked = _mask_comments_and_strings(text)
    return {match.group(1) for match in DECLARATION_RE.finditer(masked)}


def _resolve_sources(reference_root: Path) -> tuple[tuple[str, Path], ...]:
    resolved = []
    for logical, candidates in SOURCE_CANDIDATES.items():
        path = next((reference_root / name for name in candidates
                     if (reference_root / name).is_file()), None)
        if path is None:
            raise PackageError(
                f"Missing Iris reference source '{logical}'; expected one of: "
                + ", ".join(str(reference_root / name) for name in candidates)
            )
        resolved.append((logical, path))
    return tuple(resolved)


def inspect_iris(reference_root: Path, apex_version: str = APEX_VERSION) -> TokenInventory:
    reference_root = Path(reference_root)
    sources: list[TokenSource] = []
    declarations: list[TokenDeclaration] = []
    for logical_file, path in _resolve_sources(reference_root):
        data = path.read_bytes()
        text = data.decode("utf-8")
        structured = _structured_declarations(text, logical_file)
        structured_tokens = {item.token for item in structured}
        independent_tokens = _independent_tokens(text)
        if structured_tokens != independent_tokens:
            missing = sorted(independent_tokens - structured_tokens)
            extra = sorted(structured_tokens - independent_tokens)
            details = []
            if missing:
                details.append("structured parser dropped " + ", ".join(missing))
            if extra:
                details.append("structured parser invented " + ", ".join(extra))
            raise PackageError(f"Iris parser disagreement in {path.name}: " + "; ".join(details))
        sources.append(TokenSource(logical_file, path.name, hashlib.sha256(data).hexdigest()))
        declarations.extend(structured)
    return TokenInventory(apex_version, tuple(sources), tuple(declarations))


def _declaration_document(item: TokenDeclaration) -> dict[str, object]:
    result = asdict(item)
    result["rawValue"] = result.pop("raw_value")
    result["isLiteral"] = result.pop("is_literal")
    result["isChain"] = result.pop("is_chain")
    result["fallbackLiterals"] = list(result.pop("fallback_literals"))
    result["colorFamily"] = result.pop("color_family")
    result["colorRole"] = result.pop("color_role")
    return result


def inventory_document(inventory: TokenInventory) -> dict[str, object]:
    declarations = sorted(inventory.declarations,
                          key=lambda item: (item.token, item.file, item.selector, item.offset))
    sources = sorted(inventory.sources, key=lambda item: item.file)
    return {
        "schemaVersion": 1,
        "apexVersion": inventory.apex_version,
        "sources": [
            {"file": item.file, "sourceFile": item.source_file, "sha256": item.sha256}
            for item in sources
        ],
        "declarations": [_declaration_document(item) for item in declarations],
        "summaries": {
            "htmlOnlyJetAtoms": list(inventory.html_only_jet_atoms),
            "widgetFallbackTokens": list(inventory.widget_fallback_tokens),
            "unpairedColorFamilies": list(inventory.unpaired_color_families),
        },
    }


def render_inventory_json(inventory: TokenInventory) -> str:
    return json.dumps(inventory_document(inventory), indent=2, sort_keys=True) + "\n"


def inventory_from_json(text: str) -> TokenInventory:
    try:
        document = json.loads(text)
        sources = tuple(TokenSource(item["file"], item["sourceFile"], item["sha256"])
                        for item in document["sources"])
        declarations = tuple(TokenDeclaration(
            item["file"], item["selector"], item["token"], item["rawValue"], item["offset"],
            item["isLiteral"], item["isChain"], tuple(item["fallbackLiterals"]),
            item.get("colorFamily"), item.get("colorRole"),
        ) for item in document["declarations"])
        return TokenInventory(document["apexVersion"], sources, declarations)
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise PackageError(f"Invalid Iris token inventory: {exc}") from exc


def _identity(item: TokenDeclaration) -> tuple[str, str, str]:
    return item.file, item.selector, item.token


def _bullet_section(title: str, values: Iterable[str]) -> list[str]:
    values = tuple(values)
    return [f"## {title}", "", *(f"- `{value}`" for value in values)] if values else [
        f"## {title}", "", "None."]


def render_drift_report(current: TokenInventory, baseline: TokenInventory | None = None) -> str:
    baseline = baseline or current
    old = {_identity(item): item for item in baseline.declarations}
    new = {_identity(item): item for item in current.declarations}
    additions = sorted(new.keys() - old.keys())
    removals = sorted(old.keys() - new.keys())
    changes = sorted(key for key in new.keys() & old.keys()
                     if new[key].raw_value != old[key].raw_value)
    literal_roots = sorted({item.token for item in current.declarations
                            if item.selector == ":root" and item.is_literal})
    frozen_chains = sorted({item.token for item in current.declarations if item.is_chain})
    lines = [
        f"# Iris {current.apex_version} Token Report", "",
        "Generated by `scripts/theme.sh inspect-iris`; do not edit by hand.", "",
        f"- Sources: {len(current.sources)}", f"- Declarations: {len(current.declarations)}",
        f"- Added: {len(additions)}", f"- Removed: {len(removals)}",
        f"- Value changes: {len(changes)}", "",
    ]
    lines += _bullet_section("Literal root tokens", literal_roots) + [""]
    lines += _bullet_section("Frozen chains", frozen_chains) + [""]
    lines += _bullet_section("HTML-only JET atoms", current.html_only_jet_atoms) + [""]
    lines += _bullet_section("Widget fallback tokens", current.widget_fallback_tokens) + [""]
    lines += _bullet_section("Unpaired color families", current.unpaired_color_families) + [""]
    lines += _bullet_section("Additions", (" / ".join(key) for key in additions)) + [""]
    lines += _bullet_section("Removals", (" / ".join(key) for key in removals)) + [""]
    change_lines = [
        f"{' / '.join(key)}: `{old[key].raw_value}` → `{new[key].raw_value}`"
        for key in changes
    ]
    lines += _bullet_section("Value changes", change_lines) + [""]
    lines += ["## Source hashes", ""]
    lines += [f"- `{item.file}` (`{item.source_file}`): `{item.sha256}`"
              for item in sorted(current.sources, key=lambda source: source.file)]
    return "\n".join(lines).rstrip() + "\n"
