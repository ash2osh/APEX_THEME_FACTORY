"""Install planning and filesystem mutation for APEXLang exports."""

import difflib
import json
from pathlib import Path
import re
import shutil
from typing import Dict, List

from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import load_manifest
from lib.theme_factory.apexlang_model import InstallPatch, InstalledPackage
from lib.theme_factory.apexlang_parser import (
    _find_matching_brace, insert_switcher_entries, strip_bootstrap_regions,
    strip_switcher_entries,
)
from lib.theme_factory.apexlang_runtime import build_bootstrap_regions, build_switcher_entries
from lib.theme_factory.apexlang_state import (
    _sha256_file, inspect_export, read_install_state, read_registry_document,
    verify_package_ownership, verify_runtime_ownership,
)


MIME_BY_SUFFIX = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".woff2": "font/woff2",
    ".txt": "text/plain",
}



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

