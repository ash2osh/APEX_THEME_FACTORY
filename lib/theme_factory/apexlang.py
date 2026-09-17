"""APEXLang parser, patch planner, and drift verification for theme installation."""

from dataclasses import dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from typing import Dict, List, Optional, Set, Tuple

from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import NAME_REGEX, SEMVER_REGEX, ThemeManifest, load_manifest

MIME_BY_SUFFIX = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".woff2": "font/woff2",
    ".txt": "text/plain",
}

MARKER = "APEX_THEME_FACTORY_MANAGED"
# Ownership must live in data APEX stores and re-exports. APEXLang comment lines are not
# part of the APEX metadata model and never come back from `apex export`, so the managed
# Page 0 regions carry an HTML comment inside their source plus a fixed Static ID, and the
# switcher list entries live in the `theme-factory-` static-id namespace.
MARKER_HTML = f"<!-- {MARKER}:BOOTSTRAP -->"
BOOTSTRAP_REGION_IDS = ("theme_factory_bootstrap", "theme_factory_bootstrap_dialog")
BOOTSTRAP_REGION_NAME_PREFIX = "Theme Factory Bootstrap"
SWITCHER_ENTRY_PREFIX = "theme-factory-"
SWITCHER_PARENT_ID = f"{SWITCHER_ENTRY_PREFIX}switcher-parent"
SWITCHER_ITEM_CLASS = "theme-factory-managed-switcher"
RUNTIME_JS_URL = "#APP_FILES#theme-factory/runtime/theme-factory-runtime.js"


@dataclass(frozen=True)
class InstalledPackage:
    name: str
    title: str
    version: str
    class_name: str
    stylesheet_url: str
    files: Dict[str, str]


@dataclass(frozen=True)
class TargetExport:
    export_dir: Path
    alias: str
    name: str
    theme_number: int
    base_theme: str
    style: str
    css_urls: list[str]
    javascript_urls: list[str]
    global_page: Optional[int]
    application_file: Path
    theme_file: Path
    static_files_file: Path
    page_zero_file: Optional[Path]
    navigation_file: Optional[Path]
    navigation_list_alias: Optional[str] = None
    navigation_list_static: bool = False
    navigation_menu_template: Optional[str] = None
    has_user_interface_block: bool = False


@dataclass
class InstallPatch:
    export_dir: Path
    before_files: Dict[Path, str]
    after_files: Dict[Path, str]
    diff: str
    staged_copies: List[Tuple[Path, Path]]
    staged_deletions: List[Path]


def _find_matching_brace(text: str, open_pos: int) -> int:
    depth = 1
    pos = open_pos + 1
    in_str = False
    quote_char = ""
    in_fence = False
    
    while pos < len(text) and depth > 0:
        c = text[pos]
        if in_fence:
            if text[pos:pos+3] == "```":
                in_fence = False
                pos += 3
                continue
        elif text[pos:pos+3] == "```":
            in_fence = True
            pos += 3
            continue
        elif in_str:
            if c == "\\" and pos + 1 < len(text):
                pos += 2
                continue
            if c == quote_char:
                in_str = False
        else:
            if c == '"':
                in_str = True
                quote_char = c
            elif c in "{([":
                depth += 1
            elif c in "})]":
                depth -= 1
                if depth == 0:
                    return pos
        pos += 1
    return -1


def _iter_blocks(text: str, keyword: str):
    """Yield (start, end, identifier, body) for top-level `<keyword> <id> ( ... )` blocks.

    Blocks are consumed whole, so nested occurrences (for example the word `region`
    inside fenced source code of an earlier block) are never matched again.
    """
    pattern = re.compile(rf"^[ \t]*{keyword}[ \t]+(\"[^\"\n]+\"|[^\s(]+)[ \t]*\(", re.MULTILINE)
    position = 0
    while True:
        match = pattern.search(text, position)
        if not match:
            return
        close = _find_matching_brace(text, match.end() - 1)
        if close == -1:
            raise PackageError(f"Unbalanced {keyword} block in APEXLang source")
        end = close + 1
        yield match.start(), end, match.group(1).strip('"'), text[match.start():end]
        position = end


def _remove_spans(text: str, spans: List[Tuple[int, int]]) -> str:
    for start, end in sorted(spans, reverse=True):
        # swallow the line break that followed the block and any blank line before it
        while end < len(text) and text[end] in "\r\n":
            end += 1
        while start > 0 and text[start - 1] in " \t":
            start -= 1
        text = text[:start] + text[end:]
    return re.sub(r"\n{3,}", "\n\n", text)


def _is_bootstrap_identity(identifier: str, body: str) -> bool:
    if identifier in BOOTSTRAP_REGION_IDS:
        return True
    dom_id = re.search(r"htmlDomId:\s*([A-Za-z0-9_-]+)", body)
    if dom_id and dom_id.group(1) in BOOTSTRAP_REGION_IDS:
        return True
    name = re.search(r"^\s*name:\s*(.+?)\s*$", body, re.MULTILINE)
    return bool(name and name.group(1).startswith(BOOTSTRAP_REGION_NAME_PREFIX))


def _is_bootstrap_owned(body: str) -> bool:
    return MARKER_HTML in body or "window.APEX_THEME_FACTORY_CONFIG" in body


def strip_bootstrap_regions(p0_text: str) -> str:
    """Remove the Theme Factory bootstrap regions from Page 0 APEXLang text.

    Ownership is proven by content APEX round-trips (the HTML marker / config object
    inside the region source), never by APEXLang comments. A region that claims the
    managed identity (static id, DOM id or name) without that content is a collision;
    a region that carries our content under a foreign identity is refused as well.
    """
    cleaned = re.sub(
        rf"\s*(?:--|//) {MARKER}:BEGIN:REGIONS[\s\S]*?(?:--|//) {MARKER}:END:REGIONS\s*",
        "\n",
        p0_text,
    )
    spans: List[Tuple[int, int]] = []
    for start, end, identifier, body in _iter_blocks(cleaned, "region"):
        identity = _is_bootstrap_identity(identifier, body)
        owned = _is_bootstrap_owned(body)
        if identity and owned:
            spans.append((start, end))
        elif identity:
            raise PackageError(
                f"Managed Page 0 region name collision: region '{identifier}' uses the Theme Factory "
                "identity but does not contain Theme Factory content"
            )
        elif owned:
            raise PackageError(
                f"Theme Factory bootstrap content found in unmanaged Page 0 region '{identifier}'"
            )
    return _remove_spans(cleaned, spans)


def strip_switcher_entries(nav_text: str) -> str:
    """Remove Theme Factory switcher entries (static-id namespace `theme-factory-`)."""
    cleaned = re.sub(
        rf"\s*(?:--|//) {MARKER}:BEGIN:SWITCHER[\s\S]*?(?:--|//) {MARKER}:END:SWITCHER\s*",
        "\n",
        nav_text,
    )
    spans = [
        (start, end)
        for start, end, identifier, _body in _iter_blocks(cleaned, "entry")
        if identifier.startswith(SWITCHER_ENTRY_PREFIX)
    ]
    return _remove_spans(cleaned, spans)


def _list_block_span(lists_text: str, alias: str) -> Optional[Tuple[int, int]]:
    for start, end, identifier, _body in _iter_blocks(lists_text, "list"):
        if identifier == alias:
            return start, end
    return None


def list_is_static(list_body: str) -> bool:
    source = re.search(r"\bsource\s*\{", list_body)
    if not source:
        return True
    close = _find_matching_brace(list_body, source.end() - 1)
    source_body = list_body[source.end():close if close != -1 else len(list_body)]
    kind = re.search(r"\btype:\s*([A-Za-z]+)", source_body)
    return kind is None or kind.group(1).lower() == "static"


def insert_switcher_entries(lists_text: str, alias: str, entries_code: str) -> str:
    span = _list_block_span(lists_text, alias)
    if span is None:
        raise PackageError(f"Navigation bar list '{alias}' not found in lists source")
    start, end = span
    block = lists_text[start:end]
    last_paren = block.rfind(")")
    new_block = block[:last_paren].rstrip() + "\n\n" + entries_code.rstrip("\n") + "\n\n)"
    return lists_text[:start] + new_block + lists_text[end:]


def build_bootstrap_html(default_theme: str, switcher_enabled: bool, themes_json_str: str) -> str:
    return f"""{MARKER_HTML}
<script>
window.APEX_THEME_FACTORY_CONFIG = {{
  appId: &APP_ID.,
  defaultTheme: "{default_theme}",
  switcherEnabled: {"true" if switcher_enabled else "false"},
  themes: {themes_json_str}
}};
(function (doc, config) {{
  "use strict";
  var root = doc.documentElement;
  var key = "apex.themeFactory." + config.appId;
  var allowed = ["iris"].concat(config.themes.map(function (theme) {{ return theme.name; }}));
  var selected = config.defaultTheme;
  if (config.switcherEnabled) {{
    try {{
      selected = window.localStorage.getItem(key) || selected;
      if (allowed.indexOf(selected) === -1) {{
        window.localStorage.removeItem(key);
        selected = config.defaultTheme;
      }}
    }} catch (e) {{
      selected = config.defaultTheme;
    }}
  }}
  Array.prototype.slice.call(root.classList).forEach(function (name) {{
    if (name.indexOf("app-theme-") === 0) {{ root.classList.remove(name); }}
  }});
  if (selected !== "iris") {{ root.classList.add("app-theme-" + selected); }}
  root.dataset.appThemeDefault = config.defaultTheme;
  root.dataset.appThemeCurrent = selected;
}}(document, window.APEX_THEME_FACTORY_CONFIG));
</script>"""


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line if line.strip() else line for line in text.splitlines())


def build_bootstrap_regions(default_theme: str, switcher_enabled: bool, themes: list) -> str:
    """Generate APEXLang for the two owned Page 0 bootstrap regions (standard + dialog slots)."""
    themes_data = [
        {
            "name": t["name"] if isinstance(t, dict) else t.name,
            "title": t["title"] if isinstance(t, dict) else t.title,
            "className": t["className"] if isinstance(t, dict) else t.class_name,
        }
        for t in themes
    ]
    bootstrap_html = _indent(
        build_bootstrap_html(default_theme, switcher_enabled, json.dumps(themes_data)), " " * 16
    )

    def region(identifier: str, name: str, sequence: int, slot: str) -> str:
        return f"""    region {identifier} (
        name: {name}
        type: staticContent
        source {{
            htmlCode:
                ```html
{bootstrap_html}
                ```
        }}
        layout {{
            sequence: {sequence}
            slot: {slot}
        }}
        appearance {{
            template: @/blank-with-attributes
            templateOptions: #DEFAULT#
        }}
        advanced {{
            htmlDomId: {identifier}
        }}
    )
"""

    return (
        "\n"
        + region(BOOTSTRAP_REGION_IDS[0], "Theme Factory Bootstrap", 10, "banner")
        + "\n"
        + region(BOOTSTRAP_REGION_IDS[1], "Theme Factory Bootstrap (Dialog)", 11, "breadcrumbBar")
    )


def build_switcher_entries(themes: list) -> str:
    """Generate static navigation-bar list entries in the grammar SQLcl 26.2 exports.

    The parent entry gets list attribute 2 (Universal Theme navigation bar: additional
    list item classes) so the runtime can find `.t-NavigationBar-item.theme-factory-managed-switcher`.
    """

    def entry(identifier: str, label: str, sequence: int, parent: Optional[str], extra: str = "") -> str:
        parent_line = f"\n            parentEntry: @{parent}" if parent else ""
        return (
            f"    entry {identifier} (\n"
            f"        label: {label}\n"
            f"        layout {{\n"
            f"            sequence: {sequence}{parent_line}\n"
            f"        }}\n"
            f"        link {{\n"
            f"            target: {{\n"
            f"                type: url\n"
            f"                url: #\n"
            f"            }}\n"
            f"        }}\n"
            f"{extra}"
            f"    )\n"
        )

    parent_extra = (
        "        icon {\n"
        "            imageIconCssClasses: fa-paint-brush\n"
        "        }\n"
        "        userDefinedAttributes {\n"
        f"            2: {SWITCHER_ITEM_CLASS}\n"
        "        }\n"
    )
    chunks = [entry(SWITCHER_PARENT_ID, "Theme", 9000, None, parent_extra)]
    sequence = 9010
    for package in themes:
        name = package["name"] if isinstance(package, dict) else package.name
        title = package["title"] if isinstance(package, dict) else package.title
        chunks.append(entry(f"{SWITCHER_ENTRY_PREFIX}choice-{name}", title, sequence, SWITCHER_PARENT_ID))
        sequence += 10
    chunks.append(entry(f"{SWITCHER_ENTRY_PREFIX}choice-iris", "Iris", sequence, SWITCHER_PARENT_ID))
    return "\n".join(chunks)


def inspect_export(export_dir: Path) -> TargetExport:
    """Inspect and validate an APEXLang application export directory."""
    export_dir = export_dir.resolve()
    
    # Locate application.apx
    app_files = list(export_dir.glob("**/application.apx"))
    if not app_files:
        app_files = list(export_dir.glob("application.apx"))
    if not app_files:
        raise PackageError(f"No application.apx found in {export_dir}")
    if len(app_files) > 1:
        raise PackageError(f"Multiple application.apx files found in {export_dir}")
    app_file = app_files[0]
    app_text = app_file.read_text(encoding="utf-8")

    # Check for ambiguous css blocks
    css_blocks = re.findall(r"\bcss\s*\{", app_text)
    if len(css_blocks) > 1:
        raise PackageError("Ambiguous application.apx: multiple css {} blocks found")

    # Parse app declaration
    app_match = re.search(r"^\s*app\s+([A-Za-z0-9_$-]+)\s*\(", app_text, re.MULTILINE)
    if not app_match:
        raise PackageError("Missing 'app <alias> (' in application.apx")
    app_alias = app_match.group(1)

    name_match = re.search(r"^\s*name:\s*(.+)$", app_text, re.MULTILINE)
    app_name = name_match.group(1).strip() if name_match else app_alias

    # Parse userInterface
    gp_match = re.search(r"globalPage:\s*([0-9]+)", app_text)
    global_page = int(gp_match.group(1)) if gp_match else None

    # Parse CSS URLs
    css_urls = []
    css_match = re.search(r"\bcss\s*\{", app_text)
    if css_match:
        brace_end = _find_matching_brace(app_text, css_match.end() - 1)
        if brace_end != -1:
            css_content = app_text[css_match.end():brace_end]
            # Check for fileUrls: [ ... ] or fileUrls: single_val
            urls_match = re.search(r"fileUrls:\s*\[", css_content)
            if urls_match:
                arr_end = _find_matching_brace(css_content, urls_match.end() - 1)
                if arr_end != -1:
                    arr_content = css_content[urls_match.end():arr_end]
                    for line in arr_content.splitlines():
                        val = line.strip()
                        if val and not val.startswith("--") and not val.startswith("//"):
                            css_urls.append(val.strip('"\''))
            else:
                single_match = re.search(r"fileUrls:\s*([^\s\(\)\{\}\[\]]+)", css_content)
                if single_match:
                    css_urls.append(single_match.group(1).strip('"\''))

    # Parse JavaScript URLs
    js_urls = []
    js_match = re.search(r"\bjavaScript\s*\{", app_text)
    if js_match:
        brace_end = _find_matching_brace(app_text, js_match.end() - 1)
        if brace_end != -1:
            js_content = app_text[js_match.end():brace_end]
            urls_match = re.search(r"fileUrls:\s*\[", js_content)
            if urls_match:
                arr_end = _find_matching_brace(js_content, urls_match.end() - 1)
                if arr_end != -1:
                    arr_content = js_content[urls_match.end():arr_end]
                    for line in arr_content.splitlines():
                        val = line.strip()
                        if val and not val.startswith("--") and not val.startswith("//"):
                            js_urls.append(val.strip('"\''))
            else:
                single_match = re.search(r"fileUrls:\s*([^\s\(\)\{\}\[\]]+)", js_content)
                if single_match:
                    js_urls.append(single_match.group(1).strip('"\''))

    # Resolve the *current* theme through userInterface.currentTheme rather than the first
    # theme.apx on disk: applications may keep legacy themes installed.
    ui_match = re.search(r"\buserInterface\s*\{", app_text)
    ui_body = ""
    if ui_match:
        ui_close = _find_matching_brace(app_text, ui_match.end() - 1)
        ui_body = app_text[ui_match.end():ui_close] if ui_close != -1 else ""
    theme_files = sorted(export_dir.glob("**/themes/*/theme.apx")) or sorted(export_dir.glob("**/theme.apx"))
    if not theme_files:
        raise PackageError(f"No theme.apx found in {export_dir}", exit_code=3)
    current_theme = re.search(r"currentTheme:\s*@([^\s(){}]+)", ui_body)
    if current_theme:
        alias = current_theme.group(1)
        candidates = [path for path in theme_files if path.parent.name == alias]
        if len(candidates) != 1:
            raise PackageError(
                f"Current theme '@{alias}' does not resolve to exactly one theme.apx ({len(candidates)} found)",
                exit_code=3,
            )
        theme_file = candidates[0]
    elif len(theme_files) == 1:
        theme_file = theme_files[0]
    else:
        raise PackageError(
            "Ambiguous target: several themes are installed and userInterface.currentTheme is missing",
            exit_code=3,
        )
    theme_text = theme_file.read_text(encoding="utf-8")

    # Check themeNumber
    tn_match = re.search(r"themeNumber:\s*([0-9]+)", theme_text)
    theme_num = int(tn_match.group(1)) if tn_match else 0
    if theme_num != 42:
        raise PackageError(f"Unsupported themeNumber: {theme_num} (expected 42)", exit_code=3)

    # Check baseTheme
    bt_match = re.search(r"baseTheme:\s*([^\s\(\)\{\}]+)", theme_text)
    base_theme = bt_match.group(1).strip('"\'') if bt_match else ""
    if base_theme != "ut-26.1":
        raise PackageError(f"Unsupported baseTheme: '{base_theme}' (expected 'ut-26.1')", exit_code=3)

    # Check currentThemeStyle
    ts_match = re.search(r"currentThemeStyle:\s*@/([^\s\(\)\{\}]+)", theme_text)
    theme_style = ts_match.group(1).strip('"\'').lower() if ts_match else ""
    if theme_style != "iris":
        raise PackageError(f"Unsupported themeStyle: '{theme_style}' (expected 'iris')", exit_code=3)

    # Locate static-files.apx
    sf_files = list(export_dir.glob("**/static-files.apx"))
    if not sf_files:
        sf_file = export_dir / "shared-components/static-files.apx"
    else:
        sf_file = sf_files[0]

    # Locate the global page file by page number (SQLcl names files pNNNNN-<page-name>.apx)
    page_number = global_page if global_page is not None else 0
    p0_files = sorted(export_dir.glob(f"pages/p{page_number:05d}-*.apx"))
    if len(p0_files) > 1:
        raise PackageError(f"Ambiguous page {page_number} source: {[path.name for path in p0_files]}", exit_code=3)
    p0_file = p0_files[0] if p0_files else None

    # Resolve the navigation bar list (SQLcl 26.2 exports all lists into shared-components/lists.apx)
    nav_alias = None
    nav_file = None
    nav_static = False
    nav_bar = re.search(r"\bnavigationBar\s*\{", app_text)
    if nav_bar:
        nav_close = _find_matching_brace(app_text, nav_bar.end() - 1)
        nav_body = app_text[nav_bar.end():nav_close] if nav_close != -1 else ""
        alias_match = re.search(r"\blist:\s*@([^\s(){}]+)", nav_body)
        if alias_match:
            nav_alias = alias_match.group(1)
            for candidate in sorted(export_dir.glob("**/lists.apx")) + sorted(export_dir.glob(f"**/lists/{nav_alias}.apx")):
                text = candidate.read_text(encoding="utf-8")
                span = _list_block_span(text, nav_alias)
                if span:
                    nav_file = candidate
                    nav_static = list_is_static(text[span[0]:span[1]])
                    break
    nav_menu_template = None
    nav_menu = re.search(r"\bnavigationMenu\s*\{", app_text)
    if nav_menu:
        menu_close = _find_matching_brace(app_text, nav_menu.end() - 1)
        menu_body = app_text[nav_menu.end():menu_close] if menu_close != -1 else ""
        template = re.search(r"\blistTemplate:\s*(@/[^\s(){}]+)", menu_body)
        nav_menu_template = template.group(1) if template else None

    return TargetExport(
        export_dir=export_dir,
        alias=app_alias,
        name=app_name,
        theme_number=theme_num,
        base_theme=base_theme,
        style=theme_style,
        css_urls=css_urls,
        javascript_urls=js_urls,
        global_page=global_page,
        application_file=app_file,
        theme_file=theme_file,
        static_files_file=sf_file,
        page_zero_file=p0_file,
        navigation_file=nav_file,
        navigation_list_alias=nav_alias,
        navigation_list_static=nav_static,
        navigation_menu_template=nav_menu_template,
        has_user_interface_block=ui_match is not None,
    )


def read_registry_document(export_dir: Path) -> Optional[dict]:
    registry_file = export_dir / "shared-components/static-files/theme-factory/runtime/registry.json"
    if not registry_file.exists():
        return None

    try:
        data = json.loads(registry_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("themes", []), list):
            raise ValueError("registry root or themes is invalid")
        return data
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise PackageError(f"Invalid Theme Factory registry {registry_file}: {exc}") from exc


def read_install_state(export_dir: Path) -> Tuple[List[InstalledPackage], str, bool]:
    """Read installed Theme Factory packages, default theme, and switcher state."""
    data = read_registry_document(export_dir)
    if data is None:
        return [], "iris", False
    try:
        packages = []
        for package_data in data.get("themes", []):
            if not isinstance(package_data, dict):
                raise ValueError("theme entry is not an object")
            name = package_data["name"]
            version = package_data["version"]
            class_name = package_data["className"]
            stylesheet_url = package_data["stylesheetUrl"]
            expected_stylesheet = f"#APP_FILES#theme-factory/packages/{name}/{version}/theme.css"
            if not isinstance(name, str) or NAME_REGEX.fullmatch(name) is None:
                raise ValueError("theme name is unsafe")
            if not isinstance(version, str) or SEMVER_REGEX.fullmatch(version) is None:
                raise ValueError("theme version is unsafe")
            if class_name != f"app-theme-{name}" or stylesheet_url != expected_stylesheet:
                raise ValueError("theme class or stylesheet URL does not match its identity")
            files = package_data.get("files", {})
            if not isinstance(files, dict):
                raise ValueError("theme files are not an object")
            packages.append(InstalledPackage(
                name=name,
                title=package_data["title"],
                version=version,
                class_name=class_name,
                stylesheet_url=stylesheet_url,
                files=dict(files),
            ))
        default_theme = data.get("defaultTheme", "iris")
        switcher_enabled = bool(data.get("switcherEnabled", False))
        return packages, default_theme, switcher_enabled
    except (ValueError, TypeError, KeyError) as exc:
        raise PackageError(f"Invalid Theme Factory registry content: {exc}") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_package_ownership(export_dir: Path, package: InstalledPackage) -> None:
    """Refuse destructive replacement/removal unless every owned byte matches the registry."""
    if not package.files:
        raise PackageError(f"Missing ownership digests for installed theme '{package.name}'")
    if NAME_REGEX.fullmatch(package.name) is None or SEMVER_REGEX.fullmatch(package.version) is None:
        raise PackageError(f"Unsafe ownership identity for installed theme '{package.name}'")
    static_root = (export_dir / "shared-components/static-files").resolve()
    packages_root = (static_root / "theme-factory/packages").resolve()
    if not packages_root.is_relative_to(static_root):
        raise PackageError("Theme Factory package namespace escapes the static-file root")
    theme_path = packages_root / package.name
    version_path = theme_path / package.version
    if theme_path.is_symlink() or version_path.is_symlink():
        raise PackageError(f"Ownership path is a symlink for installed theme '{package.name}'")
    theme_root = theme_path.resolve()
    version_root = version_path.resolve()
    if theme_root.parent != packages_root or version_root.parent != theme_root:
        raise PackageError(f"Ownership path escapes package namespace for installed theme '{package.name}'")
    expected_paths: Set[Path] = set()
    for relative, expected_digest in package.files.items():
        if not isinstance(relative, str) or not re.fullmatch(r"[a-f0-9]{64}", str(expected_digest)):
            raise PackageError(f"Invalid ownership metadata for installed theme '{package.name}'")
        expected_prefix = f"theme-factory/packages/{package.name}/{package.version}/"
        if not relative.startswith(expected_prefix):
            raise PackageError(f"Ownership path is outside installed theme '{package.name}': {relative}")
        raw_target = static_root / relative
        target = raw_target.resolve()
        if raw_target.is_symlink() or not target.is_relative_to(version_root) or not target.is_file():
            raise PackageError(f"Ownership check failed for installed theme '{package.name}': {relative}")
        if _sha256_file(target) != expected_digest:
            raise PackageError(f"Ownership digest mismatch for installed theme '{package.name}': {relative}")
        expected_paths.add(target)
    actual_paths = {path.resolve() for path in version_root.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        raise PackageError(f"Ownership file set mismatch for installed theme '{package.name}'")
    siblings = {path.resolve() for path in theme_root.iterdir()} if theme_root.exists() else set()
    if siblings != {version_root}:
        raise PackageError(f"Unowned sibling content exists for installed theme '{package.name}'")


def verify_runtime_ownership(export_dir: Path, registry: Optional[dict]) -> None:
    runtime_root = (export_dir / "shared-components/static-files/theme-factory/runtime").resolve()
    if not runtime_root.exists():
        return
    if registry is None or not isinstance(registry.get("runtimeFiles"), dict):
        raise PackageError("Runtime files exist without ownership digests")
    expected: Set[Path] = set()
    for relative, expected_digest in registry["runtimeFiles"].items():
        if not isinstance(relative, str) or not re.fullmatch(r"[a-f0-9]{64}", str(expected_digest)):
            raise PackageError("Invalid runtime ownership metadata")
        raw_target = runtime_root / relative
        target = raw_target.resolve()
        if raw_target.is_symlink() or not target.is_relative_to(runtime_root) or not target.is_file():
            raise PackageError(f"Runtime ownership check failed: {relative}")
        if _sha256_file(target) != expected_digest:
            raise PackageError(f"Runtime ownership digest mismatch: {relative}")
        expected.add(target)
    actual = {
        path.resolve() for path in runtime_root.rglob("*")
        if path.is_file() and path.name != "registry.json"
    }
    if actual != expected:
        raise PackageError("Runtime ownership file set mismatch")


def canonical_digest(export_dir: Path) -> str:
    """Calculate deterministic SHA-256 digest of export directory."""
    digest = hashlib.sha256()
    for path in sorted(export_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(export_dir).as_posix()
            if rel in ("export.info", "export.log"):
                continue
            content = path.read_bytes()
            if path.suffix == ".apx":
                norm = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            else:
                norm = content
            digest.update(rel.encode("utf-8") + b"\0" + norm + b"\0")
    return digest.hexdigest()


def plan_install(
    export_dir: Path,
    package_root: Path,
    mode: str = "preserve",
) -> InstallPatch:
    """Plan staged changes for installing a theme package into an APEXLang export."""
    if mode not in ("preserve", "enable", "disable"):
        raise PackageError(f"Invalid switcher mode: '{mode}'")

    export_dir = export_dir.resolve()
    package_root = package_root.resolve()
    manifest = load_manifest(package_root / "theme.json", package_root)
    target = inspect_export(export_dir)

    installed_pkgs, current_default, prior_switcher = read_install_state(export_dir)
    registry_document = read_registry_document(export_dir)
    verify_runtime_ownership(export_dir, registry_document)

    prior_package = next((package for package in installed_pkgs if package.name == manifest.name), None)
    if prior_package:
        verify_package_ownership(export_dir, prior_package)
    
    # Determine switcher enabled state
    if mode == "enable":
        switcher_enabled = True
    elif mode == "disable":
        switcher_enabled = False
    else:  # preserve
        switcher_enabled = prior_switcher

    if switcher_enabled and (target.navigation_file is None or not target.navigation_list_static):
        reason = (
            "no static navigation bar list is referenced by the application"
            if target.navigation_file is None
            else f"navigation bar list '{target.navigation_list_alias}' is not a static list"
        )
        raise PackageError(
            f"Cannot install the theme switcher: {reason}. Install without --with-switcher or "
            "follow MANUAL-INSTALL.md to add the switcher by hand.",
            exit_code=3,
        )
    if target.global_page not in (None, 0):
        raise PackageError(
            f"Unsupported target: the application's global page is page {target.global_page}; "
            "only page 0 is supported. See MANUAL-INSTALL.md.",
            exit_code=3,
        )
    if not target.has_user_interface_block:
        raise PackageError(
            "Unsupported target: application.apx has no userInterface block to reference the global page",
            exit_code=3,
        )

    # Build updated packages list
    pkg_stylesheet_url = f"#APP_FILES#theme-factory/packages/{manifest.name}/{manifest.version}/theme.css"
    new_pkg = InstalledPackage(
        name=manifest.name,
        title=manifest.title,
        version=manifest.version,
        class_name=manifest.class_name,
        stylesheet_url=pkg_stylesheet_url,
        files={},
    )
    other_pkgs = [p for p in installed_pkgs if p.name != manifest.name]
    all_pkgs = sorted(other_pkgs + [new_pkg], key=lambda x: x.name)
    default_theme = manifest.name

    before_files: Dict[Path, str] = {}
    after_files: Dict[Path, str] = {}
    staged_copies: List[Tuple[Path, Path]] = []
    staged_deletions: List[Path] = []

    # 1. Plan files to copy into shared-components/static-files/theme-factory/packages/<name>/<version>/
    pkg_static_dir = export_dir / f"shared-components/static-files/theme-factory/packages/{manifest.name}/{manifest.version}"
    
    # Add manifest, theme.css, cover.jpg
    theme_css_path = package_root / "theme.css"
    if not theme_css_path.exists():
        # Source mode: build CSS if not already built in package_root
        from lib.theme_factory.css_bundle import build_theme_css
        theme_css_content = build_theme_css(export_dir.parent.parent if (export_dir.parent.parent / "static-files").exists() else export_dir, package_root, manifest, "source")
        temp_css = package_root / "theme.css"
        temp_css.write_text(theme_css_content, encoding="utf-8")
    
    staged_copies.append((package_root / "theme.json", pkg_static_dir / "theme.json"))
    staged_copies.append((package_root / "theme.css", pkg_static_dir / "theme.css"))
    if (package_root / "preview/cover.jpg").exists():
        staged_copies.append((package_root / "preview/cover.jpg", pkg_static_dir / "cover.jpg"))

    # Fonts and licenses
    for asset_rel in manifest.font_asset_files():
        src_asset = package_root / asset_rel
        if src_asset.exists():
            dst_asset = pkg_static_dir / asset_rel
            staged_copies.append((src_asset, dst_asset))

    package_files = {
        destination.relative_to(export_dir / "shared-components/static-files").as_posix(): _sha256_file(source)
        for source, destination in staged_copies
        if destination.is_relative_to(pkg_static_dir)
    }
    new_pkg = InstalledPackage(
        name=new_pkg.name,
        title=new_pkg.title,
        version=new_pkg.version,
        class_name=new_pkg.class_name,
        stylesheet_url=new_pkg.stylesheet_url,
        files=package_files,
    )
    all_pkgs = sorted(other_pkgs + [new_pkg], key=lambda package: package.name)
    if prior_package and prior_package.version != manifest.version:
        prior_dir = export_dir / f"shared-components/static-files/theme-factory/packages/{manifest.name}/{prior_package.version}"
        staged_deletions.append(prior_dir)

    # Runtime assets
    runtime_dir = export_dir / "shared-components/static-files/theme-factory/runtime"
    runtime_js_src = package_root / "theme-factory-runtime.js"
    if not runtime_js_src.exists():
        # look in installer
        installer_runtime = package_root.parent.parent / "installer/theme-factory-runtime.js"
        if installer_runtime.exists():
            runtime_js_src = installer_runtime
    if runtime_js_src.exists():
        staged_copies.append((runtime_js_src, runtime_dir / "theme-factory-runtime.js"))

    runtime_files = {
        destination.relative_to(runtime_dir).as_posix(): _sha256_file(source)
        for source, destination in staged_copies
        if destination.is_relative_to(runtime_dir)
    }

    # Write registry.json
    registry_payload = {
        "defaultTheme": default_theme,
        "switcherEnabled": switcher_enabled,
        "runtimeFiles": runtime_files,
        "themes": [
            {
                "name": p.name,
                "title": p.title,
                "version": p.version,
                "className": p.class_name,
                "stylesheetUrl": p.stylesheet_url,
                "files": p.files,
            }
            for p in all_pkgs
        ],
    }
    reg_rel = Path("shared-components/static-files/theme-factory/runtime/registry.json")
    after_files[reg_rel] = json.dumps(registry_payload, indent=2) + "\n"

    # 2. Update shared-components/static-files.apx
    sf_rel = target.static_files_file.relative_to(export_dir)
    before_sf = target.static_files_file.read_text(encoding="utf-8") if target.static_files_file.exists() else ""
    before_files[sf_rel] = before_sf

    sf_lines = before_sf.splitlines()
    # Collect all static files registered
    owned_prefix = f"theme-factory/packages/{manifest.name}/"
    filtered_sf_lines = []
    skip = False
    for line in sf_lines:
        if line.strip().startswith("file ") and (
            owned_prefix in line or "theme-factory/runtime/" in line
        ):
            skip = True
            continue
        if skip:
            if line.strip() == ")":
                skip = False
            continue
        filtered_sf_lines.append(line)

    new_sf_blocks = []
    # Add files from staged_copies that go under shared-components/static-files/
    for src_path, dst_path in staged_copies:
        rel_static = dst_path.relative_to(export_dir / "shared-components/static-files").as_posix()
        suffix = dst_path.suffix.lower()
        mime = MIME_BY_SUFFIX.get(suffix, "application/octet-stream")
        block = (
            f'file "{rel_static}" (\n'
            f"    mimeType: {mime}\n"
            f"    charSet: utf-8\n"
            f")\n"
        )
        new_sf_blocks.append(block)

    # Also register registry.json
    new_sf_blocks.append(
        'file "theme-factory/runtime/registry.json" (\n'
        '    mimeType: application/json\n'
        '    charSet: utf-8\n'
        ')\n'
    )

    clean_sf = "\n".join(filtered_sf_lines).strip()
    after_sf = (clean_sf + "\n\n" + "\n".join(new_sf_blocks)).strip() + "\n"
    after_files[sf_rel] = after_sf

    # 3. Update application.apx
    app_rel = target.application_file.relative_to(export_dir)
    before_app = target.application_file.read_text(encoding="utf-8")
    before_files[app_rel] = before_app

    # Update CSS URLs: remove any prior version for manifest.name, append new
    css_urls = [u for u in target.css_urls if not f"theme-factory/packages/{manifest.name}/" in u]
    if pkg_stylesheet_url not in css_urls:
        css_urls.append(pkg_stylesheet_url)

    # Update JS URLs:
    runtime_js_url = "#APP_FILES#theme-factory/runtime/theme-factory-runtime.js"
    js_urls = [u for u in target.javascript_urls if u != runtime_js_url]
    if switcher_enabled:
        js_urls.append(runtime_js_url)

    # Patch css {} / javaScript {} blocks (created, rewritten or removed as their URL lists require)
    after_app = before_app
    after_app = set_file_urls(after_app, "css", css_urls)
    after_app = set_file_urls(after_app, "javaScript", js_urls)

    # Ensure userInterface.globalPage: 0 (target.global_page is None or 0 at this point)
    if target.global_page is None:
        after_app = re.sub(r"(\buserInterface\s*\{)", r"\1\n        globalPage: 0", after_app, count=1)

    # Apply the manifest's navigation menu style to the side navigation template options
    if manifest.navigation_menu_style and target.navigation_menu_template == "@/side-navigation-menu":
        after_app = apply_navigation_menu_style(after_app, manifest.navigation_menu_style)

    after_files[app_rel] = after_app

    # 4. Update or create Page 0
    p0_rel = target.page_zero_file.relative_to(export_dir) if target.page_zero_file else Path("pages/p00000-global-page.apx")
    p0_full = export_dir / p0_rel
    before_p0 = p0_full.read_text(encoding="utf-8") if p0_full.exists() else ""
    if before_p0:
        before_files[p0_rel] = before_p0

    # Build bootstrap regions
    bootstrap_regions = build_bootstrap_regions(default_theme, switcher_enabled, all_pkgs)

    if not before_p0:
        after_p0 = f"page 0 (\n    name: Global Page\n{bootstrap_regions}\n)\n"
    else:
        # Strip existing marked or managed regions
        clean_p0 = strip_bootstrap_regions(before_p0)
        last_paren = clean_p0.rfind(")")
        after_p0 = clean_p0[:last_paren].rstrip() + "\n" + bootstrap_regions + "\n)\n"

    after_files[p0_rel] = after_p0

    # 5. Switcher navigation-bar entries live inside the referenced list in lists.apx
    if target.navigation_file and target.navigation_file.exists():
        nav_rel = target.navigation_file.relative_to(export_dir)
        before_nav = target.navigation_file.read_text(encoding="utf-8")
        before_files[nav_rel] = before_nav
        clean_nav = strip_switcher_entries(before_nav)
        if switcher_enabled:
            clean_nav = insert_switcher_entries(clean_nav, target.navigation_list_alias, build_switcher_entries(all_pkgs))
        after_files[nav_rel] = clean_nav

    # Compute unified diff
    diff_lines = []
    for rel_path, after_text in sorted(after_files.items()):
        before_text = before_files.get(rel_path, "")
        if before_text != after_text:
            diff = difflib.unified_diff(
                before_text.splitlines(keepends=True),
                after_text.splitlines(keepends=True),
                fromfile=f"a/{rel_path.as_posix()}",
                tofile=f"b/{rel_path.as_posix()}",
            )
            diff_lines.extend(diff)

    full_diff = "".join(diff_lines)

    return InstallPatch(
        export_dir=export_dir,
        before_files=before_files,
        after_files=after_files,
        diff=full_diff,
        staged_copies=staged_copies,
        staged_deletions=staged_deletions,
    )


def set_file_urls(app_text: str, block_name: str, urls: List[str]) -> str:
    """Set `<block_name> { fileUrls: ... }` in application.apx.

    SQLcl emits a scalar for one URL and a list for several, and the compiler rejects an
    empty `fileUrls`, so an empty list removes the whole block. A missing block is created
    before `css {}` (javaScript precedes css in exports) or before the closing paren.
    """
    block = re.search(rf"^[ \t]*{block_name}\s*\{{", app_text, re.MULTILINE)
    if block:
        close = _find_matching_brace(app_text, block.end() - 1)
        if close == -1:
            raise PackageError(f"Unbalanced {block_name} block in application.apx")
        end = close + 1
        while end < len(app_text) and app_text[end] in "\r\n":
            end += 1
        if not urls:
            return app_text[: block.start()] + app_text[end:]
        body = app_text[block.end():close]
        if not re.search(r"\bfileUrls:", body):
            raise PackageError(f"Ambiguous {block_name} block without fileUrls in application.apx")
        new_body = re.sub(
            r"(\bfileUrls:\s*)(?:\[[^\]]*\]|[^\s(){}\[\]]+)",
            lambda m: m.group(1) + _format_file_urls(urls),
            body,
            count=1,
        )
        return app_text[: block.end()] + new_body + app_text[close:]
    if not urls:
        return app_text
    new_block = f"    {block_name} {{\n        fileUrls: {_format_file_urls(urls)}\n    }}\n"
    anchor = None
    if block_name == "javaScript":
        anchor = re.search(r"^[ \t]*css\s*\{", app_text, re.MULTILINE)
    insert_at = anchor.start() if anchor else app_text.rfind(")")
    return app_text[:insert_at] + new_block + app_text[insert_at:]


def _format_file_urls(urls: List[str]) -> str:
    if len(urls) == 1:
        return urls[0]
    return "[\n" + "\n".join(f"            {url}" for url in urls) + "\n        ]"


def apply_navigation_menu_style(app_text: str, style: str) -> str:
    """Replace or add the `t-TreeNav--*` option inside navigationMenu.templateOptions."""
    menu = re.search(r"\bnavigationMenu\s*\{", app_text)
    if not menu:
        return app_text
    close = _find_matching_brace(app_text, menu.end() - 1)
    if close == -1:
        return app_text
    body = app_text[menu.end():close]
    options = re.search(r"templateOptions:\s*(\[[^\]]*\]|[^\s(){}]+)", body)
    if not options:
        return app_text
    value = options.group(1)
    if value.startswith("["):
        if re.search(r"\bt-TreeNav--[A-Za-z0-9_-]+", value):
            new_value = re.sub(r"\bt-TreeNav--[A-Za-z0-9_-]+", style, value)
        else:
            new_value = value[: value.rfind("]")].rstrip() + f"\n            {style}\n        ]"
    else:
        new_value = f"[\n            {value}\n            {style}\n        ]"
    new_body = body[: options.start(1)] + new_value + body[options.end(1):]
    return app_text[: menu.end()] + new_body + app_text[close:]


def _normalized_block(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def theme_factory_projection(export_dir: Path) -> dict:
    """Semantic view of everything Theme Factory owns or must not disturb.

    Used to compare the staged export with the post-import export: SQLcl reformats text
    (indentation, ordering, dropped comments), so byte digests are not comparable, but
    the URLs, files, registry, owned regions and switcher entries must match exactly.
    """
    export_dir = export_dir.resolve()
    target = inspect_export(export_dir)
    static_root = export_dir / "shared-components/static-files"
    theme_files: Dict[str, str] = {}
    other_files: Dict[str, str] = {}
    if static_root.exists():
        for path in sorted(static_root.rglob("*")):
            if path.is_file():
                rel = path.relative_to(static_root).as_posix()
                (theme_files if rel.startswith("theme-factory/") else other_files)[rel] = _sha256_file(path)
    declared = []
    if target.static_files_file.exists():
        declared = sorted(
            match.group(1).strip('"')
            for match in re.finditer(r"^file\s+(\"[^\"\n]+\"|\S+)\s*\(", target.static_files_file.read_text(encoding="utf-8"), re.MULTILINE)
        )
    regions = []
    if target.page_zero_file and target.page_zero_file.exists():
        for _start, _end, identifier, body in _iter_blocks(target.page_zero_file.read_text(encoding="utf-8"), "region"):
            if _is_bootstrap_identity(identifier, body) and _is_bootstrap_owned(body):
                source = re.search(r"```html\n([\s\S]*?)\n\s*```", body)
                regions.append({
                    "id": identifier,
                    "content": _normalized_block(source.group(1) if source else body),
                    "slot": (re.search(r"slot:\s*(\S+)", body) or [None, None])[1],
                })
    entries = []
    if target.navigation_file and target.navigation_file.exists():
        for _start, _end, identifier, body in _iter_blocks(target.navigation_file.read_text(encoding="utf-8"), "entry"):
            if identifier.startswith(SWITCHER_ENTRY_PREFIX):
                label = re.search(r"^\s*label:\s*(.+?)\s*$", body, re.MULTILINE)
                parent = re.search(r"parentEntry:\s*@?(\S+)", body)
                entries.append({"id": identifier, "label": label.group(1) if label else "", "parent": parent.group(1) if parent else None})
    pages = sorted(path.name.split("-", 1)[0] for path in (export_dir / "pages").glob("p*.apx")) if (export_dir / "pages").exists() else []
    registry = read_registry_document(export_dir)
    return {
        "theme": [target.theme_number, target.base_theme, target.style],
        "cssUrls": list(target.css_urls),
        "javascriptUrls": list(target.javascript_urls),
        "globalPage": target.global_page,
        "registry": registry,
        "themeFactoryFiles": theme_files,
        "otherStaticFiles": other_files,
        "declaredStaticFiles": declared,
        "bootstrapRegions": sorted(regions, key=lambda item: item["id"]),
        "switcherEntries": sorted(entries, key=lambda item: item["id"]),
        "pages": pages,
    }


def apply_patch(patch: InstallPatch) -> None:
    """Apply planned changes to the export directory."""
    # 1. Write text file changes
    for rel_path, content in patch.after_files.items():
        dst = patch.export_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")

    # 2. Perform staged copies
    for src, dst in patch.staged_copies:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # 3. Perform staged deletions
    for target in patch.staged_deletions:
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink()
