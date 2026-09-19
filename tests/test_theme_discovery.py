import json
import shutil
import tempfile
import unittest
from pathlib import Path

from lib.theme_factory.discovery import discover_themes
from lib.theme_factory.errors import PackageError


class ThemeDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / "sample-themes").mkdir()

    def make_theme(self, name: str) -> Path:
        root = self.root / "sample-themes" / name
        root.mkdir()
        manifest = {
            "schemaVersion": 1,
            "name": name,
            "title": name.replace("-", " ").title(),
            "version": "1.0.0",
            "tagline": f"The {name} test theme.",
            "class": f"app-theme-{name}",
            "compatibility": {
                "apex": ">=26.1.0 <26.2.0",
                "themeNumber": 42,
                "baseTheme": "ut-26.1",
                "themeStyle": "Iris",
            },
            "assets": {
                "stylesheet": "theme.css",
                "runtime": "theme-factory-runtime.js",
                "cover": "preview/cover.jpg",
            },
        }
        (root / "theme.json").write_text(json.dumps(manifest), encoding="utf-8")
        return root

    def test_valid_manifests_are_sorted_by_manifest_name(self):
        self.make_theme("zeta")
        self.make_theme("alpha")
        self.assertEqual(tuple(theme.name for theme in discover_themes(self.root)), ("alpha", "zeta"))

    def test_candidate_with_invalid_manifest_is_not_silently_skipped(self):
        bad = self.root / "sample-themes" / "bad"
        bad.mkdir()
        (bad / "theme.json").write_text('{"schemaVersion":1}', encoding="utf-8")
        with self.assertRaisesRegex(PackageError, "bad/theme.json"):
            discover_themes(self.root)

    def test_directory_without_manifest_is_ignored(self):
        (self.root / "sample-themes" / "notes").mkdir()
        self.assertEqual(discover_themes(self.root), ())


if __name__ == "__main__":
    unittest.main()
