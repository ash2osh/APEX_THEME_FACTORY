from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from lib.theme_factory.archive import build_package, build_package_from_root, verify_package
from lib.theme_factory.recipe import (
    FontFaceSpec,
    FontRoleSpec,
    load_recipe,
    render_manifest,
    render_tokens,
)
from lib.theme_factory.scaffold import create_theme, owned_source_digest, regenerate_owned_files


class RecipeRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_repo = Path(__file__).resolve().parent.parent

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name) / "repo"
        shutil.copytree(self.real_repo / "theme-templates", self.repo / "theme-templates")
        (self.repo / "sample-themes").mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def recipe(self, name="aurora-grid", mode="dark"):
        raw = json.loads(
            (self.real_repo / "tests/fixtures/recipes/valid-dark.json").read_text(encoding="utf-8")
        )
        raw["identity"]["name"] = name
        raw["identity"]["mode"] = mode
        source = self.repo / "recipes" / name
        source.mkdir(parents=True, exist_ok=True)
        path = source / "theme.recipe.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return load_recipe(path)

    def test_same_recipe_renders_byte_identically(self):
        recipe = self.recipe()
        self.assertEqual(render_tokens(recipe).encode(), render_tokens(recipe).encode())
        self.assertEqual(render_manifest(recipe, {}).encode(), render_manifest(recipe, {}).encode())

    def test_manifest_renderer_has_stable_font_role_shape(self):
        recipe = self.recipe()
        roles = {
            "body": FontRoleSpec(
                family="Noto Kufi Arabic",
                fallback=("system-ui", "sans-serif"),
                license="licenses/OFL.txt",
                faces=(FontFaceSpec("fonts/body-400.woff2", 400),),
            )
        }
        document = json.loads(render_manifest(recipe, roles))
        self.assertEqual(document["class"], "app-theme-aurora-grid")
        self.assertEqual(document["fonts"]["body"]["faces"][0]["weight"], 400)
        self.assertTrue(render_manifest(recipe, roles).endswith("\n"))

    def test_dark_tokens_cover_iris_palette_jet_and_widget_families(self):
        tokens = render_tokens(self.recipe())
        for expected in (
            "--ut-color-scheme: dark",
            "--a-palette-primary:",
            "--oj-core-text-color-primary:",
            "--a-checkbox-background-color:",
            "--a-datepicker-background-color:",
            "--a-gv-background-color:",
            "--a-menu-background-color:",
            "--a-popuplov-chip-background-color:",
            "--ui-dialog-content-background-color:",
        ):
            self.assertIn(expected, tokens)

    def test_light_tokens_omit_dark_only_remaps_but_keep_semantic_roles(self):
        tokens = render_tokens(self.recipe(mode="light"))
        self.assertIn("--app-surface-page:", tokens)
        self.assertIn("--app-text-primary:", tokens)
        self.assertNotIn("--a-palette-primary:", tokens)
        self.assertNotIn("--a-datepicker-background-color:", tokens)

    def test_owned_source_digest_is_stable_and_tracks_generated_source(self):
        theme = create_theme(self.repo, self.recipe()).created
        first = owned_source_digest(theme)
        self.assertEqual(first, owned_source_digest(theme))
        tokens = theme / "css/tokens.css"
        tokens.write_text(tokens.read_text(encoding="utf-8") + "/* generated change */\n", encoding="utf-8")
        self.assertNotEqual(first, owned_source_digest(theme))

    def test_regeneration_updates_owned_and_preserves_handwritten_module(self):
        original = self.recipe()
        theme = create_theme(self.repo, original).created
        buttons = theme / "css/apex/buttons.css"
        buttons.write_text("/* handwritten */\n.button-note {}\n", encoding="utf-8")
        shell = theme / "css/apex/shell.css"
        shell.write_text(shell.read_text(encoding="utf-8") + "/* stale */\n", encoding="utf-8")
        updated = replace(original, palette=replace(original.palette, accent="#FFCC00"))

        result = regenerate_owned_files(theme, updated)

        self.assertEqual(result.preserved_handwritten, (buttons,))
        self.assertEqual(buttons.read_text(encoding="utf-8"), "/* handwritten */\n.button-note {}\n")
        self.assertNotIn("stale", shell.read_text(encoding="utf-8"))
        self.assertIn("#FFCC00", (theme / "css/tokens.css").read_text(encoding="utf-8"))
        self.assertIn("#FFCC00", (theme / "theme.recipe.json").read_text(encoding="utf-8"))

    def test_recipe_is_source_only_and_absent_from_zip(self):
        theme = create_theme(self.repo, self.recipe()).created
        preview = theme / "preview"
        preview.mkdir()
        shutil.copy2(self.real_repo / "sample-themes/linen/preview/cover.jpg", preview / "cover.jpg")
        output = self.repo / "dist"
        old = os.environ.get("THEME_FACTORY_ALLOW_DIRTY")
        os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
        try:
            package = build_package_from_root(self.real_repo, theme, output)
        finally:
            if old is None:
                os.environ.pop("THEME_FACTORY_ALLOW_DIRTY", None)
            else:
                os.environ["THEME_FACTORY_ALLOW_DIRTY"] = old
        with zipfile.ZipFile(package) as archive:
            self.assertFalse(any(name.endswith("theme.recipe.json") for name in archive.namelist()))

    def test_legacy_theme_without_recipe_still_builds(self):
        output = self.repo / "dist"
        old = os.environ.get("THEME_FACTORY_ALLOW_DIRTY")
        os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
        try:
            package = build_package(self.real_repo, "linen", output)
        finally:
            if old is None:
                os.environ.pop("THEME_FACTORY_ALLOW_DIRTY", None)
            else:
                os.environ["THEME_FACTORY_ALLOW_DIRTY"] = old
        self.assertEqual(verify_package(package).name, "linen")


if __name__ == "__main__":
    unittest.main()
