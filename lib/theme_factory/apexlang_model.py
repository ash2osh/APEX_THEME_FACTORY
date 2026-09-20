"""Immutable data exchanged by APEXLang inspection and mutation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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


