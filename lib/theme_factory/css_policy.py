"""CSS policy scanner enforcing scoping, tokens, and font rules."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional, Set, Tuple

from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import load_manifest

DECLARATION_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")
CONSUMPTION_RE = re.compile(r"var\(\s*(--app-[A-Za-z0-9_-]+)")
VAR_RE = re.compile(r"var\([^)]+\)")
LITERAL_COLOR_RE = re.compile(
    r"(?i)(#[0-9a-f]{3,8}\b|\brgba?\([^)]*\)|\bhsla?\([^)]*\)|\b(?:white|black|red|blue|green|gray|grey)\b)"
)
EXTERNAL_URL_RE = re.compile(r"""url\(\s*['"]?(?:https?:|//|data:)""", re.IGNORECASE)


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
    cur = theme_root.resolve()
    for parent in [cur, *cur.parents]:
        f = parent / "static-files/css/foundation/tokens.css"
        if f.exists() and f not in foundation_paths:
            foundation_paths.append(f)

    for fp in foundation_paths:
        if fp.exists():
            for line in fp.read_text(encoding="utf-8").splitlines():
                for m in DECLARATION_RE.finditer(line):
                    tokens.add(m.group(1))

    theme_tokens = theme_root / "css/tokens.css"
    if theme_tokens.exists():
        for line in theme_tokens.read_text(encoding="utf-8").splitlines():
            for m in DECLARATION_RE.finditer(line):
                tokens.add(m.group(1))

    return tokens


def scan_package(theme_root: Path, repo_root: Optional[Path] = None) -> Tuple[PolicyViolation, ...]:
    theme_root = theme_root.resolve()
    manifest_path = theme_root / "theme.json"
    if not manifest_path.exists():
        raise PackageError(f"Missing theme.json in {theme_root}")

    manifest = load_manifest(manifest_path, theme_root)
    theme_name = manifest.name
    valid_scope_prefixes = (f"html.app-theme-{theme_name}", f".app-theme-{theme_name}")

    declared_tokens = _collect_declared_app_tokens(theme_root, repo_root)
    violations: List[PolicyViolation] = []

    css_dir = theme_root / "css"
    if not css_dir.exists():
        return ()

    for css_file in sorted(css_dir.rglob("*.css")):
        is_tokens_file = (css_file.name == "tokens.css")
        raw_lines = css_file.read_text(encoding="utf-8").splitlines()
        full_text = "\n".join(raw_lines)

        i = 0
        n = len(full_text)
        current_line = 1
        depth = 0
        current_selector = ""
        selector_line = 1
        current_decl = ""
        decl_line = 1
        in_comment = False

        while i < n:
            ch = full_text[i]
            if ch == "\n":
                current_line += 1

            if in_comment:
                if ch == "*" and i + 1 < n and full_text[i + 1] == "/":
                    in_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if ch == "/" and i + 1 < n and full_text[i + 1] == "*":
                in_comment = True
                i += 2
                continue

            if ch == "{":
                if depth == 0:
                    sel_text = current_selector.strip()
                    if sel_text:
                        if not sel_text.startswith("@"):
                            parts = [p.strip() for p in sel_text.split(",")]
                            for part in parts:
                                if not part or part.startswith("@"):
                                    continue
                                if not any(part.startswith(prefix) for prefix in valid_scope_prefixes):
                                    violations.append(
                                        PolicyViolation(
                                            path=css_file,
                                            line=selector_line,
                                            code="unscoped-selector",
                                            message=f"Selector not scoped to {valid_scope_prefixes[0]}: {part}",
                                        )
                                    )
                    current_selector = ""
                depth += 1
                i += 1
                continue

            elif ch == "}":
                if depth > 0:
                    if current_decl.strip():
                        _check_declaration(
                            current_decl.strip(),
                            decl_line,
                            css_file,
                            is_tokens_file,
                            declared_tokens,
                            raw_lines,
                            violations,
                        )
                    current_decl = ""
                    depth -= 1
                current_selector = ""
                i += 1
                continue

            if depth == 0:
                if not current_selector.strip():
                    selector_line = current_line
                current_selector += ch
            else:
                if not current_decl.strip():
                    decl_line = current_line
                if ch == ";":
                    _check_declaration(
                        current_decl.strip(),
                        decl_line,
                        css_file,
                        is_tokens_file,
                        declared_tokens,
                        raw_lines,
                        violations,
                    )
                    current_decl = ""
                else:
                    current_decl += ch

            i += 1

    return tuple(sorted(violations, key=lambda v: (str(v.path), v.line, v.code)))


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
    prop = prop.strip()
    val = val.strip()

    # Check external URLs
    if EXTERNAL_URL_RE.search(val):
        violations.append(
            PolicyViolation(
                path=css_file,
                line=line_num,
                code="external-url",
                message=f"External or data URL is forbidden: {decl_str}",
            )
        )

    # Check !important
    if "!important" in val:
        # Check if current line or lines immediately preceding have Iris or [x-cloak]
        start_line = max(0, line_num - 6)
        context_lines = raw_lines[start_line:line_num]
        allowed = any("iris" in l.lower() for l in context_lines) or "[x-cloak]" in val
        if not allowed:
            violations.append(
                PolicyViolation(
                    path=css_file,
                    line=line_num,
                    code="unsupported-important",
                    message=f"Unauthorized !important declaration: {decl_str}",
                )
            )

    # Check consumed tokens
    for match in CONSUMPTION_RE.finditer(val):
        tok = match.group(1)
        if tok not in declared_tokens:
            violations.append(
                PolicyViolation(
                    path=css_file,
                    line=line_num,
                    code="undeclared-app-token",
                    message=f"Used undeclared token: {tok}",
                )
            )

    # Check literal colors (forbidden in component files, allowed in tokens.css)
    if not is_tokens_file:
        val_without_vars = VAR_RE.sub("", val)
        m = LITERAL_COLOR_RE.search(val_without_vars)
        if m:
            matched = m.group(1).lower()
            if matched not in ("transparent", "currentcolor", "inherit", "initial", "unset"):
                violations.append(
                    PolicyViolation(
                        path=css_file,
                        line=line_num,
                        code="literal-color",
                        message=f"Literal color '{matched}' in component declaration: {decl_str}",
                    )
                )
