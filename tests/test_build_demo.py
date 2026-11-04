import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from lib.theme_factory.errors import PackageError
from tools.build_demo import DEMO_ALIAS, build, demo_application, demo_lists

ROOT = Path(__file__).resolve().parent.parent


class BuildDemoTests(unittest.TestCase):
    def test_zip_is_rebranded_resalted_and_leaves_the_source_alone(self):
        source = (ROOT / "applications/ut/application.apx").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = build(Path(tmp), salt="ABC123")
            self.assertTrue(zip_path.with_name(zip_path.name + ".sha256").is_file())
            with zipfile.ZipFile(zip_path) as archive:
                names = set(archive.namelist())
                application = archive.read("application.apx").decode("utf-8")
                global_page = archive.read("pages/p00000-global-page.apx").decode("utf-8")
                gallery = archive.read("pages/p00405-themes.apx").decode("utf-8")
                lists = archive.read("shared-components/lists.apx").decode("utf-8")
                deployment = json.loads(archive.read("deployments/default.json"))
        self.assertIn("application.apx", names, "application files sit at the top of the ZIP")
        self.assertNotIn("theme-factory.json", names)
        self.assertTrue(any(name.endswith("carbon-volt/theme.css") for name in names))
        self.assertTrue(application.startswith(f"app {DEMO_ALIAS} ("))
        self.assertIn("checksumSalt: ABC123", application)
        self.assertNotIn("runtimeApiUsage", application)
        self.assertRegex(application, r"homeUrl: \{\s+page: 405")
        self.assertIn("not affiliated", global_page)
        self.assertIn("github.com", gallery)
        self.assertNotIn("id", deployment["app"])
        self.assertNotIn("'Theme Version' label", lists)
        self.assertNotIn("entry theme-factory-lifecycle", lists)
        self.assertIn("'Theme' label", lists, "the theme switcher stays")
        self.assertEqual(source, (ROOT / "applications/ut/application.apx").read_text(encoding="utf-8"))

    def test_an_unexpected_source_fails_instead_of_shipping_unchanged(self):
        with self.assertRaises(PackageError):
            demo_application("app X (\n)\n", "SALT")
        with self.assertRaises(PackageError):
            demo_lists("list navigation-bar (\n)\n")


if __name__ == "__main__":
    unittest.main()
