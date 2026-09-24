"""Read-only inspection, ownership verification, and semantic projection."""

import hashlib
import json
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import NAME_REGEX, SEMVER_REGEX, validate_title
from lib.theme_factory.apexlang_model import InstalledPackage, TargetExport
from lib.theme_factory.apexlang_parser import (
    SWITCHER_ENTRY_PREFIX, _find_matching_brace, _is_bootstrap_identity,
    _is_bootstrap_owned, _iter_blocks, _list_block_span, list_is_static,
)


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
                title=validate_title(package_data["title"], "registry theme title"),
                version=version,
                class_name=class_name,
                stylesheet_url=stylesheet_url,
                files=dict(files),
            ))
        default_theme = data.get("defaultTheme", "iris")
        if default_theme != "iris" and default_theme not in {package.name for package in packages}:
            raise ValueError("default theme is neither 'iris' nor an installed theme")
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
