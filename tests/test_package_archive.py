import hashlib
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from lib.theme_factory.archive import (
    build_package,
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


if __name__ == "__main__":
    unittest.main()
