import json
from pathlib import Path
import shutil
import tempfile
import unittest

from lib.theme_factory.checks import run_theme_checks
from lib.theme_factory.errors import PackageError


class ThemeChecksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_repo = Path(__file__).resolve().parent.parent

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name) / "repo"
        shutil.copytree(self.source_repo / "sample-themes/linen", self.repo / "sample-themes/linen")
        shutil.copytree(self.source_repo / "static-files/css/foundation", self.repo / "static-files/css/foundation")
        shutil.copytree(self.source_repo / "installer", self.repo / "installer")
        shutil.copytree(self.source_repo / "lib", self.repo / "lib")
        shutil.copytree(self.source_repo / "theme-templates", self.repo / "theme-templates")
        shutil.copytree(self.source_repo / "tools", self.repo / "tools")
        self.shared_tokens = self.repo / "static-files/css/foundation/tokens.css"

    def tearDown(self):
        self.temporary.cleanup()

    def test_valid_theme_has_compact_human_and_machine_output(self):
        report = run_theme_checks(self.repo, "linen", use_cache=False)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(len(report.to_human().splitlines()), 1)
        self.assertRegex(
            report.to_human(),
            r"^THEME_CHECK theme=linen status=PASS cache=miss duration_ms=\d+ issues=0$",
        )
        payload = json.loads(report.to_json())
        self.assertEqual(
            set(payload),
            {"status", "theme", "cacheHit", "durationMs", "inputDigest", "issues"},
        )

    def test_unsafe_theme_name_is_rejected_before_cache_path_construction(self):
        with self.assertRaisesRegex(PackageError, "theme name"):
            run_theme_checks(self.repo, "../escape")

    def test_cache_hits_then_shared_and_local_changes_invalidate(self):
        first = run_theme_checks(self.repo, "linen")
        second = run_theme_checks(self.repo, "linen")
        self.assertFalse(first.cache_hit)
        self.assertTrue(second.cache_hit)
        self.assertEqual(first.input_digest, second.input_digest)

        self.shared_tokens.write_text(
            self.shared_tokens.read_text(encoding="utf-8") + "\n:root { --app-test: 1px; }\n",
            encoding="utf-8",
        )
        shared_change = run_theme_checks(self.repo, "linen")
        self.assertFalse(shared_change.cache_hit)
        self.assertNotEqual(first.input_digest, shared_change.input_digest)

        buttons = self.repo / "sample-themes/linen/css/apex/buttons.css"
        buttons.write_text(buttons.read_text(encoding="utf-8") + "\n/* local input */\n", encoding="utf-8")
        local_change = run_theme_checks(self.repo, "linen")
        self.assertFalse(local_change.cache_hit)
        self.assertNotEqual(shared_change.input_digest, local_change.input_digest)

    def test_multiple_defects_are_aggregated_in_one_run(self):
        theme = self.repo / "sample-themes/linen"
        recipe = json.loads(
            (self.source_repo / "tests/fixtures/recipes/invalid-low-contrast.json").read_text(encoding="utf-8")
        )
        recipe["identity"]["name"] = "linen"
        (theme / "theme.recipe.json").write_text(json.dumps(recipe), encoding="utf-8")
        component = theme / "css/apex/buttons.css"
        component.write_text(
            component.read_text(encoding="utf-8") + "\n.unscoped { color: #ff00ff; }\n",
            encoding="utf-8",
        )
        (theme / "preview/cover.jpg").unlink()

        report = run_theme_checks(self.repo, "linen", use_cache=False)

        self.assertEqual(report.status, "ERROR")
        codes = {issue.code for issue in report.issues}
        self.assertIn("CONTRAST_PRIMARY_PAGE", codes)
        self.assertIn("CSS_UNSCOPED_SELECTOR", codes)
        self.assertIn("COVER_MISSING", codes)
        self.assertGreaterEqual(len(report.issues), 3)

    def test_preview_gallery_images_do_not_invalidate_but_cover_dimensions_do(self):
        first = run_theme_checks(self.repo, "linen")
        gallery = self.repo / "sample-themes/linen/preview/p500-getting-started-1440.jpg"
        gallery.write_bytes(gallery.read_bytes() + b"ignored author preview change")
        gallery_change = run_theme_checks(self.repo, "linen")
        self.assertTrue(gallery_change.cache_hit)
        self.assertEqual(first.input_digest, gallery_change.input_digest)

        cover = self.repo / "sample-themes/linen/preview/cover.jpg"
        cover.write_bytes(b"not a jpeg")
        cover_change = run_theme_checks(self.repo, "linen")
        self.assertFalse(cover_change.cache_hit)
        self.assertNotEqual(first.input_digest, cover_change.input_digest)


if __name__ == "__main__":
    unittest.main()
