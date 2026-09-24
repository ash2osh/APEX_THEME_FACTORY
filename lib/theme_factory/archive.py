"""Deterministic package archive builder and checksum verifier."""

import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import stat
import subprocess
import tempfile
import zipfile
from typing import Dict

from lib.theme_factory.apexlang_runtime import script_json
from lib.theme_factory.css_bundle import build_theme_css
from lib.theme_factory.css_policy import scan_package
from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import NAME_REGEX, ThemeManifest, load_manifest

FIXED_DATETIME = (1980, 1, 1, 0, 0, 0)
REQUIRED_PACKAGE_FILES = frozenset({
    "theme.json", "theme.css", "theme-factory-runtime.js", "install.sh", "uninstall.sh",
    "README.md", "MANUAL-INSTALL.md", "preview/cover.jpg", "licenses/THIRD_PARTY.md",
    "lib/theme_factory/__init__.py",
})
SOURCE_ONLY_THEME_FILES = frozenset({"theme.recipe.json"})


def get_source_commit(repo_root: Path) -> str:
    """Commit named in each package banner: HEAD, suffixed -dirty for uncommitted changes."""
    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True,
                                  check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""
    commit = git("rev-parse", "HEAD") or "source"
    return f"{commit}-dirty" if git("status", "--porcelain") else commit


def render_template(tmpl_path: Path, replacements: Dict[str, str]) -> str:
    """Render template file with string replacements."""
    content = tmpl_path.read_text(encoding="utf-8")
    for k, v in replacements.items():
        content = content.replace(f"__{k}__", v)
    return content


def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_package_from_root(
    repo_root: Path,
    theme_root: Path,
    output_dir: Path,
    source_identity: str | None = None,
) -> Path:
    """Build deterministic ZIP package from theme directory."""
    repo_root = repo_root.resolve()
    theme_root = theme_root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(theme_root / "theme.json", theme_root)
    source_commit = source_identity or get_source_commit(repo_root)

    required_sources = (
        theme_root / manifest.cover,
        repo_root / "installer/theme-factory-runtime.js",
        repo_root / "installer/install.sh",
        repo_root / "installer/uninstall.sh",
        repo_root / "installer/templates/README.md.tmpl",
        repo_root / "installer/templates/MANUAL-INSTALL.md.tmpl",
        repo_root / "installer/templates/bootstrap.html.tmpl",
    )
    missing_sources = [path for path in required_sources if not path.is_file()]
    if missing_sources:
        raise PackageError(f"Missing required package source: {missing_sources[0]}")

    policy_violations = scan_package(theme_root, repo_root)
    if policy_violations:
        first = policy_violations[0]
        raise PackageError(
            f"CSS policy violation {first.code} at "
            f"{first.path}:{first.line}: {first.message}"
        )

    pkg_folder_name = f"{manifest.name}-{manifest.version}"
    theme_css_content = build_theme_css(repo_root, theme_root, manifest, source_commit)

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / pkg_folder_name
        staging.mkdir(parents=True)

        # 1. theme.json
        (staging / "theme.json").write_text(
            (theme_root / "theme.json").read_text(encoding="utf-8"), encoding="utf-8"
        )

        # 2. theme.css
        (staging / "theme.css").write_text(theme_css_content, encoding="utf-8")

        # 3. theme-factory-runtime.js
        runtime_src = repo_root / "installer/theme-factory-runtime.js"
        (staging / "theme-factory-runtime.js").write_text(
            runtime_src.read_text(encoding="utf-8"), encoding="utf-8"
        )

        # 4. install.sh & uninstall.sh
        for sh_name in ("install.sh", "uninstall.sh"):
            sh_src = repo_root / f"installer/{sh_name}"
            sh_dst = staging / sh_name
            sh_dst.write_text(sh_src.read_text(encoding="utf-8"), encoding="utf-8")
            sh_dst.chmod(0o755)

        # 5. Bundled lib/theme_factory/*.py
        lib_staging = staging / "lib/theme_factory"
        lib_staging.mkdir(parents=True)
        lib_src = repo_root / "lib/theme_factory"
        for py_file in lib_src.glob("*.py"):
            (lib_staging / py_file.name).write_text(py_file.read_text(encoding="utf-8"), encoding="utf-8")

        # 6. preview/cover.jpg
        cover_staging = staging / "preview"
        cover_staging.mkdir(parents=True)
        cover_src = theme_root / manifest.cover
        shutil.copy(cover_src, cover_staging / "cover.jpg")

        # 7. Declared fonts and licenses
        licenses_staging = staging / "licenses"
        licenses_staging.mkdir(parents=True, exist_ok=True)
        third_party_lines = ["# Third-Party Font Licenses\n"]

        for role_name, role in manifest.fonts.items():
            third_party_lines.append(f"## {role.family} ({role_name})\n")
            third_party_lines.append(f"- License: `{role.license.name}`\n")
            lic_src = theme_root / role.license
            if lic_src.exists():
                shutil.copy(lic_src, licenses_staging / role.license.name)

            for face in role.faces:
                font_src = theme_root / face.file
                font_dst = staging / face.file
                font_dst.parent.mkdir(parents=True, exist_ok=True)
                if font_src.exists():
                    shutil.copy(font_src, font_dst)

        (licenses_staging / "THIRD_PARTY.md").write_text("\n".join(third_party_lines) + "\n", encoding="utf-8")

        # 8. Render README.md and MANUAL-INSTALL.md
        bootstrap = render_template(
            repo_root / "installer/templates/bootstrap.html.tmpl",
            {
                "APP_ID": "&APP_ID.",
                "DEFAULT_THEME": manifest.name,
                "SWITCHER_ENABLED": "false",
                "THEMES_JSON": script_json([
                    {"name": manifest.name, "title": manifest.title, "className": manifest.class_name}
                ]),
            },
        )
        replacements = {
            "THEME_NAME": manifest.name,
            "THEME_TITLE": manifest.title,
            "THEME_VERSION": manifest.version,
            "THEME_TAGLINE": manifest.tagline,
            "THEME_CLASS": manifest.class_name,
            "BOOTSTRAP_SNIPPET": bootstrap,
            "NAV_STYLE_LABEL": manifest.navigation_menu_style or "the application's current value (this theme declares none)",
        }

        readme_tmpl = repo_root / "installer/templates/README.md.tmpl"
        if readme_tmpl.exists():
            (staging / "README.md").write_text(render_template(readme_tmpl, replacements), encoding="utf-8")

        manual_tmpl = repo_root / "installer/templates/MANUAL-INSTALL.md.tmpl"
        if manual_tmpl.exists():
            (staging / "MANUAL-INSTALL.md").write_text(render_template(manual_tmpl, replacements), encoding="utf-8")

        leaked_source = sorted(path for path in SOURCE_ONLY_THEME_FILES if (staging / path).exists())
        if leaked_source:
            raise PackageError(f"Source-only theme file leaked into package: {leaked_source[0]}")

        # 9. Write checksums.sha256
        checksum_lines = []
        for file_path in sorted(staging.rglob("*")):
            if file_path.is_file():
                rel = file_path.relative_to(staging).as_posix()
                if rel != "checksums.sha256":
                    h = calculate_sha256(file_path.read_bytes())
                    checksum_lines.append(f"{h}  {rel}")

        (staging / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

        # 10. Build ZIP file deterministically
        zip_path = output_dir / f"{pkg_folder_name}.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            for file_path in sorted(staging.rglob("*")):
                if file_path.is_file():
                    rel = file_path.relative_to(staging).as_posix()
                    arc_name = f"{pkg_folder_name}/{rel}"
                    data = file_path.read_bytes()
                    info = zipfile.ZipInfo(arc_name, date_time=FIXED_DATETIME)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    is_exec = arc_name.endswith(("/install.sh", "/uninstall.sh"))
                    info.external_attr = ((0o755 if is_exec else 0o644) & 0xFFFF) << 16
                    archive.writestr(info, data)

    return zip_path


def build_package(repo_root: Path, theme_name: str, output_dir: Path) -> Path:
    """Convenience wrapper for packaging named theme from sample-themes/."""
    if not isinstance(theme_name, str) or not NAME_REGEX.fullmatch(theme_name):
        raise PackageError(f"Theme name '{theme_name}' must match {NAME_REGEX.pattern}")
    return build_package_from_root(repo_root, repo_root / f"sample-themes/{theme_name}", output_dir)


def _verify_package_dir(package_root: Path) -> ThemeManifest:
    """Verify package directory against checksums.sha256 and validate manifest."""
    checksums_file = package_root / "checksums.sha256"
    if not checksums_file.exists():
        raise PackageError(f"Missing checksums.sha256 in {package_root}")

    package_root = package_root.resolve()
    lines = checksums_file.read_text(encoding="utf-8").splitlines()
    listed_paths: set[str] = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise PackageError(f"Invalid checksum line format: '{line}'")
        expected_hash, rel_path = parts
        posix_path = PurePosixPath(rel_path)
        if (
            not rel_path
            or posix_path.is_absolute()
            or "\\" in rel_path
            or any(part in ("", ".", "..") for part in posix_path.parts)
        ):
            raise PackageError(f"Unsafe checksum path '{rel_path}'")
        if rel_path in listed_paths:
            raise PackageError(f"Duplicate checksum path '{rel_path}'")
        listed_paths.add(rel_path)
        if len(expected_hash) != 64 or any(ch not in "0123456789abcdef" for ch in expected_hash.lower()):
            raise PackageError(f"Invalid SHA-256 digest for '{rel_path}'")

        target = (package_root / rel_path).resolve()
        if not target.is_relative_to(package_root):
            raise PackageError(f"Unsafe checksum path '{rel_path}'")
        if not target.exists() or not target.is_file() or target.is_symlink():
            raise PackageError(f"Checksum verification failed: missing file '{rel_path}'")
        actual_hash = calculate_sha256(target.read_bytes())
        if actual_hash != expected_hash:
            raise PackageError(f"Checksum mismatch for '{rel_path}': expected {expected_hash}, got {actual_hash}")

    actual_paths: set[str] = set()
    for target in package_root.rglob("*"):
        if target.is_symlink():
            raise PackageError(
                f"Package contains symlink '{target.relative_to(package_root).as_posix()}'"
            )
        if target.is_file() and target.name != "checksums.sha256":
            actual_paths.add(target.relative_to(package_root).as_posix())

    unlisted = sorted(actual_paths - listed_paths)
    if unlisted:
        raise PackageError(f"Package contains unlisted file '{unlisted[0]}'")
    missing = sorted(listed_paths - actual_paths)
    if missing:
        raise PackageError(f"Checksum verification failed: missing file '{missing[0]}'")

    missing_required = sorted(REQUIRED_PACKAGE_FILES - actual_paths)
    if missing_required:
        raise PackageError(f"Missing required package file '{missing_required[0]}'")

    manifest_path = package_root / "theme.json"
    return load_manifest(manifest_path, package_root)


def _validate_zip_members(archive: zipfile.ZipFile) -> str:
    seen: set[str] = set()
    roots: set[str] = set()
    for info in archive.infolist():
        name = info.filename
        path = PurePosixPath(name.rstrip("/"))
        if (
            not name
            or path.is_absolute()
            or "\\" in name
            or any(part in ("", ".", "..") for part in path.parts)
        ):
            raise PackageError(f"Unsafe ZIP member '{name}'")
        if name in seen:
            raise PackageError(f"Duplicate ZIP member '{name}'")
        seen.add(name)
        if path.parts:
            roots.add(path.parts[0])

        unix_mode = info.external_attr >> 16
        if stat.S_ISLNK(unix_mode):
            raise PackageError(f"ZIP symlink is forbidden: '{name}'")
        file_type = stat.S_IFMT(unix_mode)
        if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise PackageError(f"Unsupported ZIP member type: '{name}'")
    if len(roots) != 1:
        raise PackageError("ZIP must contain exactly one single package root")
    return next(iter(roots))


def verify_package(package_target: Path) -> ThemeManifest:
    """Verify package directory or ZIP archive against checksums.sha256 and validate manifest."""
    package_target = package_target.resolve()
    if package_target.is_file() and package_target.suffix == ".zip":
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with zipfile.ZipFile(package_target, "r") as archive:
                package_root_name = _validate_zip_members(archive)
                archive.extractall(tmp_path)
            children = list(tmp_path.iterdir())
            expected_root = tmp_path / package_root_name
            if children != [expected_root] or not expected_root.is_dir():
                raise PackageError("ZIP must contain exactly one single package root directory")
            return _verify_package_dir(expected_root)
    return _verify_package_dir(package_target)


def extract_package(zip_path: Path, destination: Path) -> Path:
    """Extract a package ZIP and return its single root directory.

    The root is read from the archive itself, never re-spelled from a version string
    (pitfalls §5.5), and every member is validated before anything is written.
    """
    zip_path = Path(zip_path).resolve()
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        root_name = _validate_zip_members(archive)
        archive.extractall(destination)
    root = destination / root_name
    if not root.is_dir():
        raise PackageError(f"Package root '{root_name}' missing after extracting {zip_path}")
    return root
