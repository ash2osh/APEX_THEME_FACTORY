import json
from pathlib import Path
import shutil
import tempfile
import unittest

from lib.theme_factory.css_bundle import flatten_css
from lib.theme_factory.css_policy import scan_package
from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import load_manifest
from lib.theme_factory.recipe import load_recipe
from lib.theme_factory.scaffold import create_theme, regenerate_owned_files


EXPECTED_MODULES = {
    "buttons.css",
    "dialogs.css",
    "forms.css",
    "misc.css",
    "regions.css",
    "reports.css",
    "shell.css",
}


class ThemeScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        source_repo = Path(__file__).resolve().parent.parent
        shutil.copytree(source_repo / "theme-templates", self.repo / "theme-templates")
        (self.repo / "sample-themes").mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def recipe(self, name: str):
        raw = json.loads(
            (Path(__file__).parent / "fixtures/recipes/valid-dark.json").read_text(encoding="utf-8")
        )
        raw["identity"].update(
            {
                "name": name,
                "title": "Aurora Grid",
                "tagline": "A generated neutral technical theme.",
            }
        )
        recipe_root = self.repo / "recipes" / name
        recipe_root.mkdir(parents=True, exist_ok=True)
        recipe_path = recipe_root / "theme.recipe.json"
        recipe_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        return load_recipe(recipe_path)

    @staticmethod
    def snapshot(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def test_create_emits_complete_scoped_source(self):
        result = create_theme(self.repo, self.recipe("aurora-grid"))
        theme_root = self.repo / "sample-themes/aurora-grid"

        self.assertEqual(result.created, theme_root)
        self.assertTrue((theme_root / "theme.json").is_file())
        self.assertTrue((theme_root / "theme.recipe.json").is_file())
        self.assertTrue((theme_root / "README.md").is_file())
        self.assertEqual(
            {path.name for path in (theme_root / "css/apex").glob("*.css")},
            EXPECTED_MODULES,
        )
        for css in (theme_root / "css").rglob("*.css"):
            content = css.read_text(encoding="utf-8")
            self.assertEqual(content.splitlines()[0], "/* @theme-factory-generated */")
            self.assertNotIn("app-theme-THEME", content)
            self.assertIn("app-theme-aurora-grid", content)

        load_manifest(theme_root / "theme.json", theme_root)
        self.assertEqual(scan_package(theme_root, self.repo), ())
        flattened = flatten_css(theme_root / "css/theme.css", (theme_root / "css",))
        self.assertNotIn("@import", flattened)
        self.assertIn("profile: cards-offset", flattened)

    def test_recipe_colors_only_appear_in_tokens(self):
        theme_root = create_theme(self.repo, self.recipe("aurora-grid")).created
        colors = {
            "#0A0D0B",
            "#151A16",
            "#0F1310",
            "#F2F7F0",
            "#A8B5AB",
            "#B8FF3D",
            "#38E8FF",
            "#FF8791",
        }
        for css in (theme_root / "css/apex").glob("*.css"):
            content = css.read_text(encoding="utf-8").upper()
            for color in colors:
                self.assertNotIn(color, content, css)

    def test_component_profiles_are_rendered_into_owner_modules(self):
        theme_root = create_theme(self.repo, self.recipe("aurora-grid")).created
        expected = {
            "shell.css": "profile: navigation-rail",
            "regions.css": "profile: cards-offset",
            "buttons.css": "profile: buttons-square",
            "forms.css": "profile: forms-dense",
            "reports.css": "profile: reports-ruled",
            "dialogs.css": "profile: dialogs-offset",
        }
        for filename, marker in expected.items():
            self.assertIn(
                marker,
                (theme_root / "css/apex" / filename).read_text(encoding="utf-8"),
            )

    def test_collision_leaves_existing_directory_byte_identical(self):
        existing = create_theme(self.repo, self.recipe("aurora-grid")).created
        before = self.snapshot(existing)

        with self.assertRaisesRegex(PackageError, "already exists"):
            create_theme(self.repo, self.recipe(existing.name))

        self.assertEqual(self.snapshot(existing), before)

    def test_regeneration_preserves_handwritten_file(self):
        recipe = self.recipe("aurora-grid")
        theme_root = create_theme(self.repo, recipe).created
        buttons = theme_root / "css/apex/buttons.css"
        buttons.write_text("/* human edit */\n" + buttons.read_text(encoding="utf-8"), encoding="utf-8")
        before = buttons.read_bytes()

        result = regenerate_owned_files(theme_root, recipe)

        self.assertEqual(buttons.read_bytes(), before)
        self.assertEqual(result.preserved_handwritten, (buttons,))

    def test_regeneration_updates_all_owned_files_atomically(self):
        recipe = self.recipe("aurora-grid")
        theme_root = create_theme(self.repo, recipe).created
        tokens = theme_root / "css/tokens.css"
        tokens.write_text(tokens.read_text(encoding="utf-8") + "/* stale */\n", encoding="utf-8")

        result = regenerate_owned_files(theme_root, recipe)

        self.assertEqual(result.created, theme_root)
        self.assertNotIn("stale", tokens.read_text(encoding="utf-8"))
        self.assertTrue(result.written)


if __name__ == "__main__":
    unittest.main()
