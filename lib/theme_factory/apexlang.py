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
from lib.theme_factory.manifest import ThemeManifest, load_manifest

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


@dataclass(frozen=True)
class InstalledPackage:
    name: str
    title: str
    version: str
    class_name: str
    stylesheet_url: str


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
            if c in ('"', "'"):
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

    # Locate theme file
    theme_files = list(export_dir.glob("**/theme.apx"))
    if not theme_files:
        raise PackageError(f"No theme.apx found in {export_dir}")
    theme_file = theme_files[0]
    theme_text = theme_file.read_text(encoding="utf-8")

    # Check themeNumber
    tn_match = re.search(r"themeNumber:\s*([0-9]+)", theme_text)
    theme_num = int(tn_match.group(1)) if tn_match else 0
    if theme_num != 42:
        raise PackageError(f"Unsupported themeNumber: {theme_num} (expected 42)")

    # Check baseTheme
    bt_match = re.search(r"baseTheme:\s*([^\s\(\)\{\}]+)", theme_text)
    base_theme = bt_match.group(1).strip('"\'') if bt_match else ""
    if base_theme != "ut-26.1":
        raise PackageError(f"Unsupported baseTheme: '{base_theme}' (expected 'ut-26.1')")

    # Check currentThemeStyle
    ts_match = re.search(r"currentThemeStyle:\s*@/([^\s\(\)\{\}]+)", theme_text)
    theme_style = ts_match.group(1).strip('"\'').lower() if ts_match else ""
    if theme_style != "iris":
        raise PackageError(f"Unsupported themeStyle: '{theme_style}' (expected 'iris')")

    # Locate static-files.apx
    sf_files = list(export_dir.glob("**/static-files.apx"))
    if not sf_files:
        # Create minimal static-files.apx if missing
        sf_file = export_dir / "shared-components/static-files.apx"
        sf_file.parent.mkdir(parents=True, exist_ok=True)
        sf_file.write_text("", encoding="utf-8")
    else:
        sf_file = sf_files[0]

    # Locate page 0
    p0_files = list(export_dir.glob("**/p00000-global-page.apx"))
    if not p0_files:
        p0_files = list(export_dir.glob("**/page-0*.apx"))
    p0_file = p0_files[0] if p0_files else None

    # Locate navigation-bar list file
    nav_files = list(export_dir.glob("**/navigation-bar.apx"))
    nav_file = nav_files[0] if nav_files else None

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
    )


def read_install_state(export_dir: Path) -> Tuple[List[InstalledPackage], str, bool]:
    """Read installed Theme Factory packages, default theme, and switcher state."""
    registry_file = export_dir / "shared-components/static-files/theme-factory/runtime/registry.json"
    if not registry_file.exists():
        return [], "iris", False

    try:
        data = json.loads(registry_file.read_text(encoding="utf-8"))
        packages = [
            InstalledPackage(
                name=p["name"],
                title=p["title"],
                version=p["version"],
                class_name=p["className"],
                stylesheet_url=p["stylesheetUrl"],
            )
            for p in data.get("themes", [])
        ]
        default_theme = data.get("defaultTheme", "iris")
        switcher_enabled = bool(data.get("switcherEnabled", False))
        return packages, default_theme, switcher_enabled
    except Exception:
        return [], "iris", False


def canonical_digest(export_dir: Path) -> str:
    """Calculate deterministic SHA-256 digest of export directory."""
    digest = hashlib.sha256()
    for path in sorted(export_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(export_dir).as_posix()
            if rel in ("export.info", "export.log"):
                continue
            content = path.read_bytes()
            # Normalize export date and newlines
            lines = []
            for line in content.splitlines():
                line_str = line.decode("utf-8", errors="replace").strip()
                if line_str.startswith(("exportDate:", "-- Date:")):
                    continue
                lines.append(line_str)
            norm = "\n".join(lines).encode("utf-8")
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
    
    # Determine switcher enabled state
    if mode == "enable":
        switcher_enabled = True
    elif mode == "disable":
        switcher_enabled = False
    else:  # preserve
        switcher_enabled = prior_switcher

    # Build updated packages list
    pkg_stylesheet_url = f"#APP_FILES#theme-factory/packages/{manifest.name}/{manifest.version}/theme.css"
    new_pkg = InstalledPackage(
        name=manifest.name,
        title=manifest.title,
        version=manifest.version,
        class_name=manifest.class_name,
        stylesheet_url=pkg_stylesheet_url,
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

    # Write registry.json
    registry_payload = {
        "defaultTheme": default_theme,
        "switcherEnabled": switcher_enabled,
        "themes": [
            {
                "name": p.name,
                "title": p.title,
                "version": p.version,
                "className": p.class_name,
                "stylesheetUrl": p.stylesheet_url,
            }
            for p in all_pkgs
        ],
    }

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

    # Patch css {} block in application.apx
    after_app = before_app
    css_formatted = "[\n" + "\n".join(f"            {u}" for u in css_urls) + "\n        ]" if css_urls else "[]"
    if re.search(r"\bcss\s*\{", after_app):
        after_app = re.sub(
            r"(\bcss\s*\{\s*fileUrls:\s*)(?:\[[^\]]*\]|[^\s\(\)\{\}]+)",
            r"\1" + css_formatted,
            after_app,
        )
    else:
        # insert before closing paren
        last_paren = after_app.rfind(")")
        css_block = f"    css {{\n        fileUrls: {css_formatted}\n    }}\n"
        after_app = after_app[:last_paren] + css_block + after_app[last_paren:]

    # Patch javaScript {} block in application.apx
    js_formatted = "[\n" + "\n".join(f"            {u}" for u in js_urls) + "\n        ]" if js_urls else "[]"
    if re.search(r"\bjavaScript\s*\{", after_app):
        after_app = re.sub(
            r"(\bjavaScript\s*\{\s*fileUrls:\s*)(?:\[[^\]]*\]|[^\s\(\)\{\}]+)",
            r"\1" + js_formatted,
            after_app,
        )

    # Ensure globalPage: 0
    if not re.search(r"globalPage:\s*0", after_app):
        if re.search(r"\buserInterface\s*\{", after_app):
            after_app = re.sub(
                r"(\buserInterface\s*\{)",
                r"\1\n        globalPage: 0",
                after_app,
            )

    after_files[app_rel] = after_app

    # 4. Update or create Page 0
    p0_rel = target.page_zero_file.relative_to(export_dir) if target.page_zero_file else Path("pages/p00000-global-page.apx")
    p0_full = export_dir / p0_rel
    before_p0 = p0_full.read_text(encoding="utf-8") if p0_full.exists() else ""
    if before_p0:
        before_files[p0_rel] = before_p0

    # Build bootstrap HTML
    themes_json_str = json.dumps([
        {"name": p.name, "title": p.title, "className": p.class_name} for p in all_pkgs
    ])
    bootstrap_html = f"""<script>
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

    bootstrap_regions = f"""
    -- {MARKER}:BEGIN:REGIONS
    region theme_factory_bootstrap (
        name: Theme Factory Bootstrap
        type: staticContent
        source {{
            htmlCode:
                ```html
                {bootstrap_html}
                ```
        }}
        layout {{
            sequence: 10
            slot: banner
        }}
        appearance {{
            template: @/blank-with-attributes
            templateOptions: #DEFAULT#
        }}
    )

    region theme_factory_bootstrap_dialog (
        name: Theme Factory Bootstrap (Dialog)
        type: staticContent
        source {{
            htmlCode:
                ```html
                {bootstrap_html}
                ```
        }}
        layout {{
            sequence: 11
            slot: breadcrumbBar
        }}
        appearance {{
            template: @/blank-with-attributes
            templateOptions: #DEFAULT#
        }}
    )
    -- {MARKER}:END:REGIONS
"""

    if not before_p0:
        after_p0 = f"page 0 (\n    name: Page Zero\n{bootstrap_regions}\n)\n"
    else:
        # Strip existing marked regions
        clean_p0 = re.sub(
            rf"\s*-- {MARKER}:BEGIN:REGIONS[\s\S]*?-- {MARKER}:END:REGIONS\s*",
            "\n",
            before_p0,
        )
        last_paren = clean_p0.rfind(")")
        after_p0 = clean_p0[:last_paren].rstrip() + "\n" + bootstrap_regions + "\n)\n"

    after_files[p0_rel] = after_p0

    # 5. Switcher Navigation List entries if enabled
    if target.navigation_file and target.navigation_file.exists():
        nav_rel = target.navigation_file.relative_to(export_dir)
        before_nav = target.navigation_file.read_text(encoding="utf-8")
        before_files[nav_rel] = before_nav

        clean_nav = re.sub(
            rf"\s*-- {MARKER}:BEGIN:SWITCHER[\s\S]*?-- {MARKER}:END:SWITCHER\s*",
            "\n",
            before_nav,
        )

        if switcher_enabled:
            # Add switcher parent entry and child entries
            entries_code = [f"    -- {MARKER}:BEGIN:SWITCHER", '    entry "theme-factory-switcher-parent" (', '        label: "Theme"', '        sequence: 9000', '        cssClasses: "theme-factory-managed-switcher"', '        link { target: { type: url url: "javascript:void(0);" } }', '    )']
            seq = 9010
            for p in all_pkgs:
                entries_code.append(
                    f'    entry "theme-factory-choice-{p.name}" (\n'
                    f'        label: "{p.title}"\n'
                    f'        sequence: {seq}\n'
                    f'        parentEntry: "theme-factory-switcher-parent"\n'
                    f'        link {{ target: {{ type: url url: "javascript:void(0);" }} }}\n'
                    f'    )'
                )
                seq += 10
            # Add Iris
            entries_code.append(
                f'    entry "theme-factory-choice-iris" (\n'
                f'        label: "Iris"\n'
                f'        sequence: {seq}\n'
                f'        parentEntry: "theme-factory-switcher-parent"\n'
                f'        link {{ target: {{ type: url url: "javascript:void(0);" }} }}\n'
                f'    )'
            )
            entries_code.append(f"    -- {MARKER}:END:SWITCHER\n")

            last_paren = clean_nav.rfind(")")
            after_nav = clean_nav[:last_paren].rstrip() + "\n" + "\n".join(entries_code) + "\n)\n"
        else:
            after_nav = clean_nav

        after_files[nav_rel] = after_nav

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
