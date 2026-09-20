import json
from pathlib import Path
import tempfile
import unittest

from lib.theme_factory.fingerprint import (
    check_uniqueness,
    compare_fingerprints,
    delta_e_1976,
    fingerprint_theme,
)


MODULES = ("shell", "regions", "buttons", "forms", "reports", "dialogs", "misc")
BASE_CSS = """
html.app-theme-NAME .t-Widget {
  background: COLOR_A;
  color: COLOR_B;
  border: 1px solid var(--app-border-color);
  border-radius: var(--app-radius-md);
}
html.app-theme-NAME .t-Widget:hover { transform: translateY(-2px); }
"""


class ThemeFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def theme(self, name: str, colors: tuple[str, str], component_css: str = BASE_CSS) -> Path:
        root = self.root / name
        apex = root / "css/apex"
        apex.mkdir(parents=True)
        manifest = {
            "schemaVersion": 1,
            "name": name,
            "title": name.title(),
            "version": "1.0.0",
            "tagline": "Fingerprint fixture",
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
        (root / "css/theme.css").write_text(
            "\n".join(f'@import "apex/{module}.css";' for module in MODULES),
            encoding="utf-8",
        )
        (root / "css/tokens.css").write_text(
            f"""html.app-theme-{name} {{
  --app-surface-page: {colors[0]};
  --app-surface-card: {colors[1]};
  --app-surface-chrome: {colors[0]};
  --app-text-emphasized: {colors[1]};
  --app-text-primary: {colors[1]};
  --app-text-secondary: {colors[1]};
  --app-color-primary: {colors[0]};
  --app-color-info: {colors[0]};
  --app-text-on-accent: {colors[1]};
  --app-color-danger: {colors[0]};
  --app-radius-sm: 2px;
  --app-radius-md: 4px;
  --app-radius-lg: 8px;
  --app-control-h: 2.5rem;
  --app-border-width: 1px;
  --app-shadow-card: none;
}}\n""",
            encoding="utf-8",
        )
        for module in MODULES:
            rendered = component_css.replace("NAME", name).replace("COLOR_A", colors[0]).replace("COLOR_B", colors[1])
            (apex / f"{module}.css").write_text(rendered, encoding="utf-8")
        return root

    def recipe_theme(self, name: str, colors: tuple[str, str], *, axes: dict | None = None, component_css: str = BASE_CSS) -> Path:
        root = self.theme(name, colors, component_css)
        recipe = json.loads((Path("tests/fixtures/recipes/valid-dark.json")).read_text(encoding="utf-8"))
        recipe["identity"]["name"] = name
        recipe["palette"]["page"] = colors[0]
        recipe["palette"]["card"] = colors[1]
        recipe["palette"]["chrome"] = colors[0]
        recipe["palette"]["textPrimary"] = colors[1]
        recipe["palette"]["textSecondary"] = colors[1]
        recipe["palette"]["accent"] = colors[0]
        recipe["palette"]["accentAlt"] = colors[0]
        recipe["palette"]["onAccent"] = colors[1]
        recipe["palette"]["danger"] = colors[0]
        recipe["schemaVersion"] = 2
        recipe["rhythm"] = {"density": "balanced", "spacing": "technical", "typeScale": "balanced"}
        recipe["interaction"] = {"hover": "none", "selected": "fill", "motion": "precise"}
        recipe["responsive"] = {"strategy": "reflow", "compactControlsAt": 768}
        if axes:
            for section, values in axes.items():
                recipe[section].update(values)
        (root / "theme.recipe.json").write_text(json.dumps(recipe), encoding="utf-8")
        return root

    def test_color_only_copy_is_rejected(self):
        left = self.theme("left", ("#101820", "#F2F2F2"))
        right = self.theme("right", ("#301040", "#FFF0FA"))
        issues = check_uniqueness(right, (left, right))
        self.assertIn(
            "STRUCTURAL_RECOLOR",
            {issue.code for issue in issues if issue.severity == "error"},
        )

    def test_structurally_distinct_theme_is_not_an_error(self):
        left = self.theme("left", ("#101820", "#F2F2F2"))
        right = self.theme(
            "right",
            ("#301040", "#FFF0FA"),
            ".app-theme-NAME .t-Widget { display: grid; grid-template-columns: 1fr 2fr 3fr; COLOR_A: COLOR_B; }",
        )
        issues = check_uniqueness(right, (left, right))
        self.assertFalse(any(issue.severity == "error" for issue in issues))

    def test_profile_collision_uses_the_lower_structural_threshold(self):
        left = self.recipe_theme("left", ("#101820", "#F2F2F2"))
        right = self.recipe_theme("right", ("#301040", "#FFF0FA"))
        for module in ("shell",):
            path = right / "css/apex" / f"{module}.css"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "border-radius: var(--app-radius-md);",
                    "border-radius: var(--app-radius-md); gap: 1px;",
                ),
                encoding="utf-8",
            )
        issues = check_uniqueness(right, (left, right))
        self.assertIn("PROFILE_COLLISION", {issue.code for issue in issues if issue.severity == "error"})

    def test_identity_collision_requires_all_explicit_identity_axes(self):
        left = self.recipe_theme("left", ("#101820", "#F2F2F2"))
        right = self.recipe_theme(
            "right",
            ("#111921", "#F5F5F5"),
            component_css=".app-theme-NAME .t-Widget { display: grid; grid-template-columns: repeat(7, 1fr); align-items: stretch; gap: 1.25rem; }",
        )
        issues = check_uniqueness(right, (left, right))
        self.assertIn("IDENTITY_COLLISION", {issue.code for issue in issues if issue.severity == "error"})

    def test_distinct_explicit_axes_avoid_identity_collision_even_with_same_font(self):
        left = self.recipe_theme("left", ("#101820", "#F2F2F2"))
        right = self.recipe_theme(
            "right",
            ("#111921", "#F5F5F5"),
            axes={
                "rhythm": {"density": "spacious", "spacing": "playful", "typeScale": "display"},
                "interaction": {"hover": "lift", "selected": "outline", "motion": "buoyant"},
                "responsive": {"strategy": "stack", "compactControlsAt": 375},
            },
            component_css=".app-theme-NAME .t-Widget { display: flex; flex-direction: column; min-block-size: 12rem; }",
        )
        issues = check_uniqueness(right, (left, right))
        self.assertFalse(any(issue.code == "IDENTITY_COLLISION" for issue in issues))

    def test_legacy_theme_without_recipe_has_a_fingerprint(self):
        fingerprint = fingerprint_theme(Path("sample-themes/linen"))
        self.assertEqual(fingerprint.name, "linen")
        self.assertGreater(len(fingerprint.component_hashes), 3)
        self.assertEqual(len(fingerprint.profiles), 7)

    def test_similarity_report_explains_every_dimension(self):
        left = fingerprint_theme(self.theme("left", ("#101820", "#F2F2F2")))
        right = fingerprint_theme(self.theme("right", ("#301040", "#FFF0FA")))
        report = compare_fingerprints(right, left)
        self.assertEqual(report.nearest_theme, "left")
        self.assertGreaterEqual(report.css_similarity, 0.98)
        self.assertEqual(len(report.matching_profiles), 7)
        self.assertIsInstance(report.palette_delta_e, float)
        self.assertIsInstance(report.font_match, bool)
        self.assertIsInstance(report.geometry_match, bool)

    def test_delta_e_matches_reference_extremes(self):
        self.assertAlmostEqual(delta_e_1976("#000000", "#000000"), 0.0, places=5)
        self.assertAlmostEqual(delta_e_1976("#000000", "#FFFFFF"), 100.0, places=2)
        self.assertAlmostEqual(delta_e_1976("#FF0000", "rgb(255 0 0 / 50%)"), 0.0, places=5)
        self.assertAlmostEqual(delta_e_1976("#00FF00", "hsl(120 100% 50%)"), 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
