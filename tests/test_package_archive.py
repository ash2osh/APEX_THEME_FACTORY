import hashlib
import os
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile
import shutil

from lib.theme_factory.archive import (
    build_package,
    build_package_from_root,
    verify_package,
)
from lib.theme_factory.errors import PackageError


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent

    def test_two_builds_are_byte_identical_and_single_theme(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            env = dict(os.environ, THEME_FACTORY_ALLOW_DIRTY="1")
            old_val = os.environ.get("THEME_FACTORY_ALLOW_DIRTY")
            os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
            try:
                zip_a = build_package(self.repo_root, "linen", Path(first))
                zip_b = build_package(self.repo_root, "linen", Path(second))
                self.assertEqual(
                    hashlib.sha256(zip_a.read_bytes()).digest(),
                    hashlib.sha256(zip_b.read_bytes()).digest(),
                )
                with zipfile.ZipFile(zip_a) as archive:
                    names = archive.namelist()
                    self.assertEqual(sum(name.endswith("/theme.json") for name in names), 1)
                    self.assertNotIn("sample-themes/solarized-dark/theme.json", names)
            finally:
                if old_val is None:
                    os.environ.pop("THEME_FACTORY_ALLOW_DIRTY", None)
                else:
                    os.environ["THEME_FACTORY_ALLOW_DIRTY"] = old_val

    def test_zip_metadata_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_val = os.environ.get("THEME_FACTORY_ALLOW_DIRTY")
            os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
            try:
                zip_path = build_package(self.repo_root, "linen", Path(tmp))
                with zipfile.ZipFile(zip_path) as archive:
                    for info in archive.infolist():
                        self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                        mode = (info.external_attr >> 16) & 0o777
                        if info.filename.endswith(("/install.sh", "/uninstall.sh")):
                            self.assertEqual(mode, 0o755)
                        else:
                            self.assertEqual(mode, 0o644)
                        # No absolute paths or traversals
                        self.assertFalse(info.filename.startswith("/"))
                        self.assertNotIn("..", info.filename)
            finally:
                if old_val is None:
                    os.environ.pop("THEME_FACTORY_ALLOW_DIRTY", None)
                else:
                    os.environ["THEME_FACTORY_ALLOW_DIRTY"] = old_val

    def test_extracted_package_verifies_checksums_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_val = os.environ.get("THEME_FACTORY_ALLOW_DIRTY")
            os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
            try:
                zip_path = build_package(self.repo_root, "linen", Path(tmp))
                extract_dir = Path(tmp) / "extracted"
                with zipfile.ZipFile(zip_path) as archive:
                    archive.extractall(extract_dir)

                pkg_root = next(extract_dir.iterdir())
                manifest = verify_package(pkg_root)
                self.assertEqual(manifest.name, "linen")
                self.assertEqual(manifest.version, "1.0.0")

                # Test tamper detection
                (pkg_root / "theme.css").write_text("/* tampered */", encoding="utf-8")
                with self.assertRaises(PackageError):
                    verify_package(pkg_root)
            finally:
                if old_val is None:
                    os.environ.pop("THEME_FACTORY_ALLOW_DIRTY", None)
                else:
                    os.environ["THEME_FACTORY_ALLOW_DIRTY"] = old_val

    def test_verifier_rejects_unchecksummed_extra_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_val = os.environ.get("THEME_FACTORY_ALLOW_DIRTY")
            os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
            try:
                zip_path = build_package(self.repo_root, "linen", Path(tmp))
                extract_dir = Path(tmp) / "extracted"
                with zipfile.ZipFile(zip_path) as archive:
                    archive.extractall(extract_dir)
                pkg_root = next(extract_dir.iterdir())
                (pkg_root / "EXTRA.bin").write_bytes(b"not covered by checksums")

                with self.assertRaisesRegex(PackageError, "unlisted file"):
                    verify_package(pkg_root)
            finally:
                if old_val is None:
                    os.environ.pop("THEME_FACTORY_ALLOW_DIRTY", None)
                else:
                    os.environ["THEME_FACTORY_ALLOW_DIRTY"] = old_val

    def test_verifier_rejects_unsafe_zip_member_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../escape.txt", b"escape")

            with self.assertRaisesRegex(PackageError, "(?i)unsafe ZIP member"):
                verify_package(archive_path)
            self.assertFalse((Path(tmp).parent / "escape.txt").exists())

    def test_verifier_rejects_duplicate_zip_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "duplicate.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("theme/theme.json", b"first")
                archive.writestr("theme/theme.json", b"second")

            with self.assertRaisesRegex(PackageError, "(?i)duplicate ZIP member"):
                verify_package(archive_path)

    def test_verifier_rejects_zip_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "symlink.zip"
            info = zipfile.ZipInfo("theme/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(info, b"../../outside")

            with self.assertRaisesRegex(PackageError, "symlink"):
                verify_package(archive_path)

    def test_verifier_rejects_extra_top_level_zip_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
            valid = build_package(self.repo_root, "linen", Path(tmp))
            altered = Path(tmp) / "altered.zip"
            shutil.copy2(valid, altered)
            with zipfile.ZipFile(altered, "a") as archive:
                archive.writestr("EXTRA.txt", b"outside package root")
            with self.assertRaisesRegex(PackageError, "single package root"):
                verify_package(altered)

    def test_verifier_requires_portable_core_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
            valid = build_package(self.repo_root, "linen", Path(tmp))
            extracted = Path(tmp) / "extracted"
            with zipfile.ZipFile(valid) as archive:
                archive.extractall(extracted)
            package = next(extracted.iterdir())
            (package / "theme-factory-runtime.js").unlink()
            (package / "preview/cover.jpg").unlink()
            checksums = []
            for path in sorted(package.rglob("*")):
                if path.is_file() and path.name != "checksums.sha256":
                    checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(package).as_posix()}")
            (package / "checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(PackageError, "required package file"):
                verify_package(package)

    def test_builder_rejects_theme_import_outside_theme_css_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            theme_root = repo / "sample-themes/linen"
            shutil.copytree(self.repo_root / "sample-themes/linen", theme_root)
            shutil.copytree(
                self.repo_root / "static-files/css/foundation",
                repo / "static-files/css/foundation",
            )
            shutil.copytree(self.repo_root / "installer", repo / "installer")
            shutil.copytree(self.repo_root / "lib", repo / "lib")
            shared = repo / "static-files/css/unowned.css"
            shared.write_text(".unowned { color: red; }\n", encoding="utf-8")
            entry = theme_root / "css/theme.css"
            entry.write_text(
                '@import "../../../static-files/css/unowned.css";\n' + entry.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            old_val = os.environ.get("THEME_FACTORY_ALLOW_DIRTY")
            os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
            try:
                with self.assertRaisesRegex(ValueError, "escapes allowed roots"):
                    build_package_from_root(repo, theme_root, repo / "dist")
            finally:
                if old_val is None:
                    os.environ.pop("THEME_FACTORY_ALLOW_DIRTY", None)
                else:
                    os.environ["THEME_FACTORY_ALLOW_DIRTY"] = old_val

    def test_builder_refuses_missing_declared_cover(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_root = Path(tmp) / "linen"
            shutil.copytree(self.repo_root / "sample-themes/linen", theme_root)
            (theme_root / "preview/cover.jpg").unlink()
            old_val = os.environ.get("THEME_FACTORY_ALLOW_DIRTY")
            os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
            try:
                with self.assertRaisesRegex(PackageError, "cover"):
                    build_package_from_root(self.repo_root, theme_root, Path(tmp) / "dist")
            finally:
                if old_val is None:
                    os.environ.pop("THEME_FACTORY_ALLOW_DIRTY", None)
                else:
                    os.environ["THEME_FACTORY_ALLOW_DIRTY"] = old_val

    def test_builder_runs_css_policy_before_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_root = Path(tmp) / "linen"
            shutil.copytree(self.repo_root / "sample-themes/linen", theme_root)
            component = theme_root / "css/apex/dialogs.css"
            component.write_text(
                component.read_text(encoding="utf-8")
                + '\nhtml.app-theme-linen .t-Dialog { background-image: url("https://example.invalid/a.png"); }\n',
                encoding="utf-8",
            )
            old_val = os.environ.get("THEME_FACTORY_ALLOW_DIRTY")
            os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
            try:
                with self.assertRaisesRegex(PackageError, "CSS policy"):
                    build_package_from_root(self.repo_root, theme_root, Path(tmp) / "dist")
            finally:
                if old_val is None:
                    os.environ.pop("THEME_FACTORY_ALLOW_DIRTY", None)
                else:
                    os.environ["THEME_FACTORY_ALLOW_DIRTY"] = old_val

    def test_builder_excludes_source_only_recipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_root = Path(tmp) / "linen"
            shutil.copytree(self.repo_root / "sample-themes/linen", theme_root)
            (theme_root / "theme.recipe.json").write_text('{"sourceOnly": true}\n', encoding="utf-8")
            old_val = os.environ.get("THEME_FACTORY_ALLOW_DIRTY")
            os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
            try:
                package = build_package_from_root(self.repo_root, theme_root, Path(tmp) / "dist")
                with zipfile.ZipFile(package) as archive:
                    self.assertFalse(
                        any(name.endswith("/theme.recipe.json") for name in archive.namelist())
                    )
            finally:
                if old_val is None:
                    os.environ.pop("THEME_FACTORY_ALLOW_DIRTY", None)
                else:
                    os.environ["THEME_FACTORY_ALLOW_DIRTY"] = old_val


if __name__ == "__main__":
    unittest.main()
