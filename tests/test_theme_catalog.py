import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib.theme_factory.catalog import CatalogTheme, catalog_themes, render_release_status, update_generated_sections


class GeneratedSectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "README.md"

    def tearDown(self):
        self.temporary.cleanup()

    def test_handwritten_text_outside_markers_is_preserved(self):
        original = (
            "Intro\n<!-- @generated:themes:start -->\nold\n"
            "<!-- @generated:themes:end -->\nEnd\n"
        )
        self.path.write_text(original, encoding="utf-8")
        changed = update_generated_sections(self.path, {"themes": "new\n"}, check=False)
        self.assertEqual(changed, (self.path,))
        self.assertEqual(
            self.path.read_text(encoding="utf-8"),
            "Intro\n<!-- @generated:themes:start -->\nnew\n<!-- @generated:themes:end -->\nEnd\n",
        )

    def test_check_reports_drift_without_writing(self):
        original = "<!-- @generated:themes:start -->\nold\n<!-- @generated:themes:end -->\n"
        self.path.write_text(original, encoding="utf-8")
        changed = update_generated_sections(self.path, {"themes": "new\n"}, check=True)
        self.assertEqual(changed, (self.path,))
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_missing_or_duplicate_markers_fail_closed(self):
        self.path.write_text("handwritten only\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "generated markers"):
            update_generated_sections(self.path, {"themes": "new\n"}, check=False)


class CatalogVerdictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parent.parent

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.evidence = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_missing_evidence_never_renders_verified(self):
        themes = catalog_themes(self.repo, self.evidence)
        self.assertTrue(themes)
        self.assertTrue(all(theme.verdict == "UNVERIFIED" for theme in themes))

    def test_incomplete_a_through_d_evidence_never_renders_verified(self):
        evidence_dir = self.evidence / "2026-09-20-release-linen"
        evidence_dir.mkdir()
        (evidence_dir / "evidence.json").write_text("{}", encoding="utf-8")
        incomplete = [
            {"layer": "C", "status": "PASS", "check": "layer-C", "path": "x", "details": "ok"},
            {"layer": "D", "status": "UNVERIFIED", "check": "layer-D", "path": "x", "details": "not captured"},
            {"layer": "E", "status": "FAIL", "check": "agent_behavior_matrix", "path": "legacy", "details": "historical"},
        ]
        with patch("lib.theme_factory.catalog.load_evidence", return_value=incomplete) as loader, \
             patch("lib.theme_factory.catalog._package_identity", return_value=("b" * 64, Path("fixture.zip"))), \
             patch("lib.theme_factory.catalog.last_source_commit", return_value="a" * 40):
            themes = catalog_themes(self.repo, self.evidence)
        linen = next(theme for theme in themes if theme.name == "linen")
        loader.assert_called_once()
        self.assertEqual(linen.layers["C"], "PASS")
        self.assertEqual(linen.layers["D"], "UNVERIFIED")
        self.assertEqual(linen.layers["E"], "FAIL")
        self.assertEqual(linen.verdict, "UNVERIFIED")
        self.assertEqual(linen.status_detail, "layers not current: D")

    def test_release_status_header_is_a_through_d_only(self):
        theme = CatalogTheme(
            name="fixture", title="Fixture", version="1.0.0", tagline="fixture",
            direction="fixture", font_families=("Fixture",), verdict="VERIFIED",
            status_detail="", layers={name: "PASS" for name in "ABCDE"},
        )
        rendered = render_release_status((theme,))
        self.assertEqual(rendered.splitlines()[0], "| Theme | A | B | C | D | Verdict |")
        self.assertNotIn("| E |", rendered.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
