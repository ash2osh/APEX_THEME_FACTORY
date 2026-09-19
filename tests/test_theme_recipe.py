import json
import shutil
import tempfile
import unittest
from pathlib import Path

from lib.theme_factory.errors import PackageError
from lib.theme_factory.recipe import contrast_ratio, load_recipe, validate_core_contrast


class ThemeRecipeTests(unittest.TestCase):
    fixtures = Path(__file__).parent / "fixtures/recipes"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def valid_raw(self) -> dict:
        return json.loads((self.fixtures / "valid-dark.json").read_text(encoding="utf-8"))

    def load(self, raw: dict, directory: str | None = None):
        theme_name = directory or raw["identity"]["name"]
        root = self.tmp / theme_name
        root.mkdir(parents=True, exist_ok=True)
        path = root / "theme.recipe.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return load_recipe(path)

    def load_fixture(self, name: str):
        raw = json.loads((self.fixtures / name).read_text(encoding="utf-8"))
        return self.load(raw)

    def test_unknown_recipe_property_fails(self):
        raw = self.valid_raw()
        raw["identity"]["surprise"] = True
        with self.assertRaisesRegex(PackageError, "identity/surprise"):
            self.load(raw)

    def test_theme_name_rejects_path_escape(self):
        raw = self.valid_raw()
        raw["identity"]["name"] = "../escape"
        with self.assertRaisesRegex(PackageError, "must match"):
            self.load(raw, directory="safe-directory")

    def test_recipe_name_must_match_parent_directory(self):
        with self.assertRaisesRegex(PackageError, "does not match recipe directory"):
            self.load(self.valid_raw(), directory="different-name")

    def test_colors_are_normalized_and_collections_are_immutable(self):
        recipe = self.load(self.valid_raw())
        self.assertEqual(recipe.palette.page, "#0A0D0B")
        self.assertEqual(recipe.typography.weights, (400, 500, 600, 700))
        self.assertEqual(recipe.identity.keywords, ("technical", "dense"))

    def test_duplicate_or_unknown_weights_fail(self):
        duplicate = self.valid_raw()
        duplicate["typography"]["weights"] = [400, 400, 700]
        with self.assertRaisesRegex(PackageError, "unique"):
            self.load(duplicate)

        unknown = self.valid_raw()
        unknown["identity"]["name"] = "unknown-weight"
        unknown["typography"]["weights"] = [400, 450, 700]
        with self.assertRaisesRegex(PackageError, "valid font weight"):
            self.load(unknown)

    def test_primary_text_below_4_5_is_an_error(self):
        recipe = self.load_fixture("invalid-low-contrast.json")
        issues = validate_core_contrast(recipe)
        pairs = {(issue.code, issue.severity) for issue in issues}
        self.assertIn(("CONTRAST_PRIMARY_CARD", "error"), pairs)
        self.assertIn(("CONTRAST_PRIMARY_PAGE", "error"), pairs)
        self.assertIn(("CONTRAST_FOCUS_CARD", "error"), pairs)

    def test_valid_fixture_has_no_core_contrast_errors(self):
        recipe = self.load_fixture("valid-dark.json")
        self.assertEqual(validate_core_contrast(recipe), ())

    def test_wcag_ratios_match_known_pairs(self):
        self.assertEqual(round(contrast_ratio("#000000", "#FFFFFF"), 2), 21.00)
        self.assertEqual(round(contrast_ratio("#777777", "#FFFFFF"), 2), 4.48)


if __name__ == "__main__":
    unittest.main()
