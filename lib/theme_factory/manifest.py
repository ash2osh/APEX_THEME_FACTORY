"""Manifest parser and validator for single-theme packages."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from lib.theme_factory.errors import PackageError

NAME_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_REGEX = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
FONT_NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z0-9 _-]{0,63}$")
FONT_FILE_REGEX = re.compile(r"^fonts/[a-z0-9]+(?:-[a-z0-9]+)*\.woff2$")
LICENSE_FILE_REGEX = re.compile(r"^licenses/[A-Za-z0-9][A-Za-z0-9._-]*$")

GENERIC_FONT_FAMILIES = {
    "serif", "sans-serif", "monospace", "system-ui", "ui-serif", "ui-sans-serif", "ui-monospace"
}
VALID_WEIGHTS = {100, 200, 300, 400, 500, 600, 700, 800, 900}
VALID_STYLES = {"normal", "italic"}


@dataclass(frozen=True)
class FontFace:
    file: Path
    weight: int
    style: str


@dataclass(frozen=True)
class FontRole:
    family: str
    fallback: tuple[str, ...]
    license: Path
    faces: tuple[FontFace, ...]


@dataclass(frozen=True)
class ThemeManifest:
    schema_version: int
    name: str
    title: str
    version: str
    tagline: str
    class_name: str
    navigation_menu_style: str | None
    fonts: dict[str, FontRole]
    stylesheet: Path
    runtime: Path
    cover: Path

    def font_asset_files(self) -> tuple[Path, ...]:
        font_files = {face.file for role in self.fonts.values() for face in role.faces}
        licenses = {role.license for role in self.fonts.values()}
        return tuple(sorted({*font_files, *licenses}))


def _check_allowed_keys(obj: dict[str, Any], allowed: set[str], path: str) -> None:
    for k in obj:
        if k not in allowed:
            prop = f"{path}/{k}" if path else k
            raise PackageError(f"Unknown property '{prop}'")


def load_manifest(path: Path, package_root: Path) -> ThemeManifest:
    """Load and strictly validate a theme.json manifest."""
    path = path.resolve()
    package_root = package_root.resolve()

    if not path.exists() or not path.is_file():
        raise PackageError(f"Manifest file not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise PackageError(f"Invalid JSON in manifest {path}: {e}")

    if not isinstance(raw, dict):
        raise PackageError("Manifest root must be an object")

    root_keys = {"schemaVersion", "name", "title", "version", "tagline", "class", "compatibility", "templateOptions", "fonts", "assets"}
    _check_allowed_keys(raw, root_keys, "")

    # Required top-level fields
    for req in ("schemaVersion", "name", "title", "version", "tagline", "class", "compatibility", "assets"):
        if req not in raw:
            raise PackageError(f"Missing required property '{req}'")

    if raw["schemaVersion"] != 1:
        raise PackageError("schemaVersion must be 1")

    name = raw["name"]
    if not isinstance(name, str) or not NAME_REGEX.match(name):
        raise PackageError(f"name '{name}' must match {NAME_REGEX.pattern}")

    if name != package_root.name:
        raise PackageError(f"name '{name}' does not match package directory '{package_root.name}'")

    title = raw["title"]
    if not isinstance(title, str) or not title.strip():
        raise PackageError("title must be a non-empty string")

    version = raw["version"]
    if not isinstance(version, str) or not SEMVER_REGEX.match(version):
        raise PackageError(f"version '{version}' is not a valid semantic version")

    tagline = raw["tagline"]
    if not isinstance(tagline, str) or not tagline.strip():
        raise PackageError("tagline must be a non-empty string")

    class_name = raw["class"]
    expected_class = f"app-theme-{name}"
    if class_name != expected_class:
        raise PackageError(f"class '{class_name}' must equal '{expected_class}'")

    # compatibility
    compat = raw["compatibility"]
    if not isinstance(compat, dict):
        raise PackageError("compatibility must be an object")
    compat_keys = {"apex", "themeNumber", "baseTheme", "themeStyle"}
    _check_allowed_keys(compat, compat_keys, "compatibility")
    for req in compat_keys:
        if req not in compat:
            raise PackageError(f"Missing required property 'compatibility/{req}'")

    if compat["themeNumber"] != 42:
        raise PackageError("compatibility/themeNumber must be 42")
    if compat["baseTheme"] != "ut-26.1":
        raise PackageError("compatibility/baseTheme must be 'ut-26.1'")
    if compat["themeStyle"] != "Iris":
        raise PackageError("compatibility/themeStyle must be 'Iris'")

    # templateOptions
    nav_style = None
    if "templateOptions" in raw:
        opts = raw["templateOptions"]
        if not isinstance(opts, dict):
            raise PackageError("templateOptions must be an object")
        _check_allowed_keys(opts, {"navigationMenuStyle"}, "templateOptions")
        nav_style = opts.get("navigationMenuStyle")
        if nav_style is not None and (not isinstance(nav_style, str) or not nav_style.strip()):
            raise PackageError("templateOptions/navigationMenuStyle must be a non-empty string")

    # assets
    assets = raw["assets"]
    if not isinstance(assets, dict):
        raise PackageError("assets must be an object")
    assets_keys = {"stylesheet", "runtime", "cover"}
    _check_allowed_keys(assets, assets_keys, "assets")
    for req in assets_keys:
        if req not in assets:
            raise PackageError(f"Missing required property 'assets/{req}'")

    if assets["stylesheet"] != "theme.css":
        raise PackageError("assets/stylesheet must be 'theme.css'")
    if assets["runtime"] != "theme-factory-runtime.js":
        raise PackageError("assets/runtime must be 'theme-factory-runtime.js'")
    if assets["cover"] != "preview/cover.jpg":
        raise PackageError("assets/cover must be 'preview/cover.jpg'")

    # fonts
    fonts_dict: dict[str, FontRole] = {}
    if "fonts" in raw:
        fonts_obj = raw["fonts"]
        if not isinstance(fonts_obj, dict):
            raise PackageError("fonts must be an object")
        _check_allowed_keys(fonts_obj, {"body", "heading", "mono"}, "fonts")

        if "body" not in fonts_obj:
            raise PackageError("fonts must include 'body' role")

        for role_name, role_obj in fonts_obj.items():
            role_path = f"fonts/{role_name}"
            if not isinstance(role_obj, dict):
                raise PackageError(f"{role_path} must be an object")
            role_keys = {"family", "fallback", "license", "faces"}
            _check_allowed_keys(role_obj, role_keys, role_path)
            for req in role_keys:
                if req not in role_obj:
                    raise PackageError(f"Missing required property '{role_path}/{req}'")

            family = role_obj["family"]
            if not isinstance(family, str) or not FONT_NAME_REGEX.match(family):
                raise PackageError(f"{role_path}/family '{family}' is invalid")

            fallback_list = role_obj["fallback"]
            if not isinstance(fallback_list, list) or len(fallback_list) < 1:
                raise PackageError(f"{role_path}/fallback must be a non-empty list")
            seen_fallbacks = set()
            for fb in fallback_list:
                if not isinstance(fb, str):
                    raise PackageError(f"{role_path}/fallback items must be strings")
                if fb in seen_fallbacks:
                    raise PackageError(f"{role_path}/fallback contains duplicate '{fb}'")
                seen_fallbacks.add(fb)
                if fb not in GENERIC_FONT_FAMILIES and not FONT_NAME_REGEX.match(fb):
                    raise PackageError(f"{role_path}/fallback item '{fb}' is invalid or unsafe")

            license_str = role_obj["license"]
            if not isinstance(license_str, str) or not LICENSE_FILE_REGEX.match(license_str):
                raise PackageError(f"{role_path}/license must match pattern {LICENSE_FILE_REGEX.pattern}")

            license_target = (package_root / license_str).resolve()
            licenses_dir = (package_root / "licenses").resolve()
            if not license_target.is_relative_to(licenses_dir):
                raise PackageError(f"{role_path}/license must stay under licenses/")
            if not license_target.exists() or not license_target.is_file():
                raise PackageError(f"{role_path}/license file not found: {license_str}")
            if license_target.stat().st_size == 0:
                raise PackageError(f"{role_path}/license file is empty: {license_str}")

            faces_list = role_obj["faces"]
            if not isinstance(faces_list, list) or len(faces_list) < 1:
                raise PackageError(f"{role_path}/faces must be a non-empty list")

            parsed_faces = []
            seen_tuples = set()
            fonts_dir = (package_root / "fonts").resolve()

            for idx, face_obj in enumerate(faces_list):
                face_path = f"{role_path}/faces/{idx}"
                if not isinstance(face_obj, dict):
                    raise PackageError(f"{face_path} must be an object")
                face_keys = {"file", "weight", "style"}
                _check_allowed_keys(face_obj, face_keys, face_path)
                for req in face_keys:
                    if req not in face_obj:
                        raise PackageError(f"Missing required property '{face_path}/{req}'")

                file_str = face_obj["file"]
                if not isinstance(file_str, str) or not FONT_FILE_REGEX.match(file_str):
                    raise PackageError(f"{face_path}/file must stay under fonts/ and end in .woff2")

                file_target = (package_root / file_str).resolve()
                if not file_target.is_relative_to(fonts_dir):
                    raise PackageError(f"{face_path}/file must stay under fonts/")
                if not file_target.exists() or not file_target.is_file():
                    raise PackageError(f"{face_path}/file not found: {file_str}")

                # Check WOFF2 signature: 'wOF2'
                with open(file_target, "rb") as f:
                    sig = f.read(4)
                    if sig != b"wOF2":
                        raise PackageError(f"{face_path}/file has invalid signature, expected 'wOF2'")

                weight = face_obj["weight"]
                if weight not in VALID_WEIGHTS:
                    raise PackageError(f"{face_path}/weight must be one of {sorted(VALID_WEIGHTS)}")

                style = face_obj["style"]
                if style not in VALID_STYLES:
                    raise PackageError(f"{face_path}/style must be one of {sorted(VALID_STYLES)}")

                pair = (weight, style)
                if pair in seen_tuples:
                    raise PackageError(f"{role_path} has duplicate face tuple {pair}")
                seen_tuples.add(pair)

                parsed_faces.append(FontFace(file=Path(file_str), weight=weight, style=style))

            fonts_dict[role_name] = FontRole(
                family=family,
                fallback=tuple(fallback_list),
                license=Path(license_str),
                faces=tuple(parsed_faces),
            )

    return ThemeManifest(
        schema_version=raw["schemaVersion"],
        name=name,
        title=title,
        version=version,
        tagline=tagline,
        class_name=class_name,
        navigation_menu_style=nav_style,
        fonts=fonts_dict,
        stylesheet=Path(assets["stylesheet"]),
        runtime=Path(assets["runtime"]),
        cover=Path(assets["cover"]),
    )
