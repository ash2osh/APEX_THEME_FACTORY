"""CSS policy scanner enforcing scoping, tokens, and font rules."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional, Set, Tuple

from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import load_manifest

DECLARATION_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")
CONSUMPTION_RE = re.compile(r"var\(\s*(--app-[A-Za-z0-9_-]+)")
CUSTOM_PROPERTY_RE = re.compile(r"--[A-Za-z0-9_-]+")
LITERAL_COLOR_RE = re.compile(
    r"(?i)(#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|device-cmyk)\([^)]*\))"
)
CSS_IDENT_RE = re.compile(r"(?<![-\\])\b[A-Za-z][A-Za-z0-9-]*\b")
CSS_NAMED_COLORS = frozenset("""
aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond
blue blueviolet brown burlywood cadetblue chartreuse chocolate coral
cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray
darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid
darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey
darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue
firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod
gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki
lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon
lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue
lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue
mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen
mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod
palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum
powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon
sandybrown seagreen seashell sienna silver skyblue slateblue slategray
slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet
wheat white whitesmoke yellow yellowgreen
""".split())
COLOR_PROPERTY_PREFIXES = (
    "background", "border", "column-rule", "outline", "text-decoration",
    "text-emphasis", "-webkit-text-fill", "-webkit-text-stroke", "mask-border",
)
COLOR_CAPABLE_PROPERTIES = frozenset({
    "accent-color", "backdrop-filter", "box-shadow", "caret-color", "color",
    "fill", "filter", "flood-color", "lighting-color", "scrollbar-color",
    "stop-color", "stroke", "text-shadow",
})
EXTERNAL_URL_RE = re.compile(r"""url\(\s*['"]?(?:https?:|//|data:)""", re.IGNORECASE)
IRIS_INLINE_RE = re.compile(r"/\*\s*Iris\s*:", re.IGNORECASE)
SCOPE_BOUNDARY_CHARS = frozenset(">+~.#[,:")
CSS_ESCAPE_RE = re.compile(r"\\(?:([0-9a-fA-F]{1,6})\s?|([^\r\n0-9a-fA-F]))")


@dataclass(frozen=True)
class PolicyViolation:
    path: Path
    line: int
    code: str
    message: str


def _collect_declared_app_tokens(theme_root: Path, repo_root: Optional[Path] = None) -> Set[str]:
    tokens: Set[str] = set()
    foundation_paths = []
    if repo_root:
        foundation_paths.append(repo_root / "static-files/css/foundation/tokens.css")
    current = theme_root.resolve()
    for parent in [current, *current.parents]:
        candidate = parent / "static-files/css/foundation/tokens.css"
        if candidate.exists() and candidate not in foundation_paths:
            foundation_paths.append(candidate)
    for path in foundation_paths:
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                tokens.update(match.group(1) for match in DECLARATION_RE.finditer(line))
    theme_tokens = theme_root / "css/tokens.css"
    if theme_tokens.exists():
        for line in theme_tokens.read_text(encoding="utf-8").splitlines():
            tokens.update(match.group(1) for match in DECLARATION_RE.finditer(line))
    return tokens


def _split_selectors(selector_text: str) -> List[str]:
    parts: List[str] = []
    start = 0
    depth = 0
    quote: Optional[str] = None
    escaped = False
    for index, character in enumerate(selector_text):
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in ("'", '"'):
            quote = character
        elif character in "([":
            depth += 1
        elif character in ")]":
            depth = max(0, depth - 1)
        elif character == "," and depth == 0:
            parts.append(selector_text[start:index].strip())
            start = index + 1
    parts.append(selector_text[start:].strip())
    return parts


def _has_scope_boundary(selector: str, prefix: str) -> bool:
    if not selector.startswith(prefix):
        return False
    return len(selector) == len(prefix) or (
        selector[len(prefix)].isspace() or selector[len(prefix)] in SCOPE_BOUNDARY_CHARS
    )


def _check_selectors(
    selector_text: str,
    line_num: int,
    css_file: Path,
    valid_scope_prefixes: Tuple[str, str],
    violations: List[PolicyViolation],
) -> None:
    for selector in _split_selectors(selector_text):
        if selector and not any(_has_scope_boundary(selector, prefix) for prefix in valid_scope_prefixes):
            violations.append(
                PolicyViolation(
                    path=css_file,
                    line=line_num,
                    code="unscoped-selector",
                    message=f"Selector not scoped to {valid_scope_prefixes[0]}: {selector}",
                )
            )


def _without_strings(value: str) -> str:
    characters: List[str] = []
    quote: Optional[str] = None
    escaped = False
    for character in value:
        if quote:
            characters.append(" ")
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif character in ("'", '"'):
            quote = character
            characters.append(" ")
        else:
            characters.append(character)
    return "".join(characters)


def _decode_css_escapes(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(1):
            codepoint = int(match.group(1), 16)
            return chr(codepoint) if codepoint and codepoint <= 0x10FFFF else "\ufffd"
        return match.group(2) or ""
    return CSS_ESCAPE_RE.sub(replace, value)


def _without_url_functions(value: str) -> str:
    """Mask complete url(...) values so asset names cannot look like color tokens."""
    result = list(value)
    for match in list(re.finditer(r"(?i)\burl\s*\(", value)):
        index = match.end()
        depth = 1
        quote: Optional[str] = None
        escaped = False
        while index < len(value) and depth:
            character = value[index]
            if quote:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = None
            elif character in ("'", '"'):
                quote = character
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            index += 1
        for position in range(match.start(), index):
            result[position] = " "
    return "".join(result)


def _property_accepts_color(property_name: str) -> bool:
    return (
        property_name.startswith("--")
        or property_name in COLOR_CAPABLE_PROPERTIES
        or property_name.startswith(COLOR_PROPERTY_PREFIXES)
        or property_name.endswith("-color")
    )


def scan_package(theme_root: Path, repo_root: Optional[Path] = None) -> Tuple[PolicyViolation, ...]:
    theme_root = theme_root.resolve()
    manifest_path = theme_root / "theme.json"
    if not manifest_path.exists():
        raise PackageError(f"Missing theme.json in {theme_root}")
    manifest = load_manifest(manifest_path, theme_root)
    valid_scope_prefixes = (f"html.app-theme-{manifest.name}", f".app-theme-{manifest.name}")
    declared_tokens = _collect_declared_app_tokens(theme_root, repo_root)
    violations: List[PolicyViolation] = []
    css_dir = theme_root / "css"
    if not css_dir.exists():
        return ()

    for css_file in sorted(css_dir.rglob("*.css")):
        is_tokens_file = css_file.name == "tokens.css"
        raw_lines = css_file.read_text(encoding="utf-8").splitlines()
        full_text = "\n".join(raw_lines)
        index = 0
        current_line = 1
        buffer = ""
        buffer_line = 1
        block_stack: List[str] = []
        in_comment = False
        in_string: Optional[str] = None
        escaped = False

        while index < len(full_text):
            character = full_text[index]
            if character == "\n":
                current_line += 1
            if in_comment:
                if character == "*" and index + 1 < len(full_text) and full_text[index + 1] == "/":
                    in_comment = False
                    buffer += "  "
                    index += 2
                    continue
                buffer += "\n" if character == "\n" else " "
                index += 1
                continue
            if in_string:
                buffer += character
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == in_string:
                    in_string = None
                index += 1
                continue
            if character == "/" and index + 1 < len(full_text) and full_text[index + 1] == "*":
                in_comment = True
                buffer += "  "
                index += 2
                continue
            if character in ("'", '"'):
                in_string = character
                buffer += character
                index += 1
                continue
            if character == "{":
                prelude = buffer.strip()
                parent = block_stack[-1] if block_stack else None
                if prelude.startswith("@"):
                    at_name = prelude[1:].split(None, 1)[0].lower()
                    if at_name.endswith("keyframes"):
                        block_stack.append("keyframes")
                    elif at_name in {"media", "supports", "layer", "container", "document", "scope"}:
                        block_stack.append("container")
                    else:
                        block_stack.append("declarations")
                else:
                    if parent != "keyframes":
                        _check_selectors(prelude, buffer_line, css_file, valid_scope_prefixes, violations)
                    block_stack.append("declarations")
                buffer = ""
                buffer_line = current_line
                index += 1
                continue
            if character == "}":
                if block_stack:
                    if block_stack[-1] == "declarations" and buffer.strip():
                        _check_declaration(
                            buffer.strip(), buffer_line, css_file, is_tokens_file,
                            declared_tokens, raw_lines, violations,
                        )
                    block_stack.pop()
                buffer = ""
                buffer_line = current_line
                index += 1
                continue
            if character == ";":
                if block_stack and block_stack[-1] == "declarations" and buffer.strip():
                    _check_declaration(
                        buffer.strip(), buffer_line, css_file, is_tokens_file,
                        declared_tokens, raw_lines, violations,
                    )
                buffer = ""
                buffer_line = current_line
                index += 1
                continue
            if not buffer.strip() and not character.isspace():
                buffer_line = current_line
            buffer += character
            index += 1

    return tuple(sorted(violations, key=lambda violation: (str(violation.path), violation.line, violation.code)))


def _check_declaration(
    decl_str: str,
    line_num: int,
    css_file: Path,
    is_tokens_file: bool,
    declared_tokens: Set[str],
    raw_lines: List[str],
    violations: List[PolicyViolation],
) -> None:
    if ":" not in decl_str:
        return
    prop, val = decl_str.split(":", 1)
    prop = prop.strip().lower()
    val = val.strip()
    decoded_value = _decode_css_escapes(val)
    if EXTERNAL_URL_RE.search(decoded_value):
        violations.append(PolicyViolation(css_file, line_num, "external-url", f"External or data URL is forbidden: {decl_str}"))
    if "!important" in val:
        declaration_lines = raw_lines[max(0, line_num - 1):]
        important_line = next((line for line in declaration_lines if "!important" in line), "")
        if not IRIS_INLINE_RE.search(important_line):
            violations.append(PolicyViolation(css_file, line_num, "unsupported-important", f"Unauthorized !important declaration: {decl_str}"))
    for match in CONSUMPTION_RE.finditer(val):
        token = match.group(1)
        if token not in declared_tokens:
            violations.append(PolicyViolation(css_file, line_num, "undeclared-app-token", f"Used undeclared token: {token}"))
    if not is_tokens_file:
        value_without_strings = _without_strings(_without_url_functions(decoded_value))
        value_without_token_names = CUSTOM_PROPERTY_RE.sub("", value_without_strings)
        match = LITERAL_COLOR_RE.search(value_without_token_names)
        literal_color = match.group(1) if match else None
        if not match and _property_accepts_color(prop):
            literal_color = next(
                (
                    identifier
                    for identifier in CSS_IDENT_RE.findall(value_without_token_names)
                    if identifier.lower() in CSS_NAMED_COLORS
                ),
                None,
            )
        if literal_color:
            color = literal_color.lower()
            violations.append(PolicyViolation(css_file, line_num, "literal-color", f"Literal color '{color}' in component declaration: {decl_str}"))
