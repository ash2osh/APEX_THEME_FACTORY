"""Deterministic package archive builder and checksum verifier."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from typing import Dict

from lib.theme_factory.css_bundle import build_theme_css
from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import ThemeManifest, load_manifest

FIXED_DATETIME = (1980, 1, 1, 0, 0, 0)


def get_source_commit(repo_root: Path) -> str:
    """Determine source commit or check dirty state."""
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        status = ""

    allow_dirty = os.getenv("THEME_FACTORY_ALLOW_DIRTY", "0") == "1"
    if status and not allow_dirty:
        raise PackageError("Repository has uncommitted changes (set THEME_FACTORY_ALLOW_DIRTY=1 to override)")

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return f"{commit}-dirty" if (status and allow_dirty) else (commit or "source")
    except Exception:
        return "dirty" if status else "source"


def render_template(tmpl_path: Path, replacements: Dict[str, str]) -> str:
    """Render template file with string replacements."""
    content = tmpl_path.read_text(encoding="utf-8")
    for k, v in replacements.items():
        content = content.replace(f"__{k}__", v)
    return content


def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_package_from_root(repo_root: Path, theme_root: Path, output_dir: Path) -> Path:
    """Build deterministic ZIP package from theme directory."""
    repo_root = repo_root.resolve()
    theme_root = theme_root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(theme_root / "theme.json", theme_root)
    source_commit = get_source_commit(repo_root)

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
        if runtime_src.exists():
            (staging / "theme-factory-runtime.js").write_text(
                runtime_src.read_text(encoding="utf-8"), encoding="utf-8"
            )

        # 4. install.sh & uninstall.sh
        for sh_name in ("install.sh", "uninstall.sh"):
            sh_src = repo_root / f"installer/{sh_name}"
            if sh_src.exists():
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
        cover_src = theme_root / "preview/cover.jpg"
        if cover_src.exists():
            shutil.copy(cover_src, cover_staging / "cover.jpg")
        else:
            # Minimal placeholder JPEG (1x1 pixel)
            dummy_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
            (cover_staging / "cover.jpg").write_bytes(dummy_jpg)

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
        replacements = {
            "THEME_NAME": manifest.name,
            "THEME_TITLE": manifest.title,
            "THEME_VERSION": manifest.version,
            "THEME_TAGLINE": manifest.tagline,
            "THEME_CLASS": manifest.class_name,
            "BOOTSTRAP_SNIPPET": (repo_root / "installer/templates/bootstrap.html.tmpl").read_text(encoding="utf-8") if (repo_root / "installer/templates/bootstrap.html.tmpl").exists() else "",
        }

        readme_tmpl = repo_root / "installer/templates/README.md.tmpl"
        if readme_tmpl.exists():
            (staging / "README.md").write_text(render_template(readme_tmpl, replacements), encoding="utf-8")

        manual_tmpl = repo_root / "installer/templates/MANUAL-INSTALL.md.tmpl"
        if manual_tmpl.exists():
            (staging / "MANUAL-INSTALL.md").write_text(render_template(manual_tmpl, replacements), encoding="utf-8")

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
    return build_package_from_root(repo_root, repo_root / f"sample-themes/{theme_name}", output_dir)


def verify_package(package_root: Path) -> ThemeManifest:
    """Verify package directory against checksums.sha256 and validate manifest."""
    package_root = package_root.resolve()
    checksums_file = package_root / "checksums.sha256"
    if not checksums_file.exists():
        raise PackageError(f"Missing checksums.sha256 in {package_root}")

    lines = checksums_file.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise PackageError(f"Invalid checksum line format: '{line}'")
        expected_hash, rel_path = parts
        target = package_root / rel_path
        if not target.exists():
            raise PackageError(f"Checksum verification failed: missing file '{rel_path}'")
        actual_hash = calculate_sha256(target.read_bytes())
        if actual_hash != expected_hash:
            raise PackageError(f"Checksum mismatch for '{rel_path}': expected {expected_hash}, got {actual_hash}")

    manifest_path = package_root / "theme.json"
    return load_manifest(manifest_path, package_root)
