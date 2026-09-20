"""Stable compatibility facade for Theme Factory APEXLang operations."""

from lib.theme_factory.apexlang_model import InstallPatch, InstalledPackage, TargetExport
from lib.theme_factory.apexlang_parser import (
    BOOTSTRAP_REGION_IDS, BOOTSTRAP_REGION_NAME_PREFIX, MARKER, MARKER_HTML,
    RUNTIME_JS_URL, SWITCHER_ENTRY_PREFIX, SWITCHER_ITEM_CLASS, SWITCHER_PARENT_ID,
    _find_matching_brace, insert_switcher_entries, list_is_static,
    strip_bootstrap_regions, strip_switcher_entries,
)
from lib.theme_factory.apexlang_runtime import (
    build_bootstrap_html, build_bootstrap_regions, build_switcher_entries,
)
from lib.theme_factory.apexlang_state import (
    canonical_digest, inspect_export, read_install_state, read_registry_document,
    theme_factory_projection, verify_package_ownership, verify_runtime_ownership,
)
from lib.theme_factory.apexlang_patch import (
    MIME_BY_SUFFIX, apply_navigation_menu_style, apply_patch, plan_install, set_file_urls,
)

__all__ = [
    "InstalledPackage", "TargetExport", "InstallPatch", "strip_bootstrap_regions",
    "strip_switcher_entries", "list_is_static", "insert_switcher_entries",
    "build_bootstrap_html", "build_bootstrap_regions", "build_switcher_entries",
    "inspect_export", "read_registry_document", "read_install_state",
    "verify_package_ownership", "verify_runtime_ownership", "canonical_digest",
    "plan_install", "set_file_urls", "apply_navigation_menu_style",
    "theme_factory_projection", "apply_patch",
]
