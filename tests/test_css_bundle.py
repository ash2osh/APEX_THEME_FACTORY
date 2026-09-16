from pathlib import Path
import tempfile
import unittest

from lib.theme_factory.css_bundle import (
    build_theme_css,
    flatten_css,
    internal_family,
    render_font_css,
)
from lib.theme_factory.manifest import FontFace, FontRole, ThemeManifest


class CssBundleTests(unittest.TestCase):
    def test_flattens_each_local_import_once_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.css").write_text('@import "b.css";\n.a { color: red; }\n', encoding="utf-8")
            (root / "b.css").write_text(".b { color: blue; }\n", encoding="utf-8")
            self.assertEqual(
                flatten_css(root / "a.css", (root,)),
                ".b { color: blue; }\n.a { color: red; }\n",
            )

    def test_rejects_remote_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.css").write_text('@import url("https://fonts.example/x.css");\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "remote CSS imports are forbidden"):
                flatten_css(root / "a.css", (root,))

    def test_rejects_protocol_relative_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.css").write_text('@import "//cdn.example.com/x.css";\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "remote CSS imports are forbidden"):
                flatten_css(root / "a.css", (root,))

    def test_rejects_data_url_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.css").write_text('@import url("data:text/css;base64,AAA");\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "data: URL CSS imports are forbidden"):
                flatten_css(root / "a.css", (root,))

    def test_flattens_unquoted_url_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "entry.css").write_text(
                "@import url(other.css);\n.entry { color: blue; }\n",
                encoding="utf-8",
            )
            (root / "other.css").write_text(".other { color: red; }\n", encoding="utf-8")

            flattened = flatten_css(root / "entry.css", (root,))

            self.assertNotIn("@import", flattened)
            self.assertEqual(
                flattened,
                ".other { color: red; }\n.entry { color: blue; }\n",
            )

    def test_rejects_unrecognized_import_syntax(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "entry.css").write_text(
                "@import layer(theme);\n.entry { color: blue; }\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unresolved CSS import"):
                flatten_css(root / "entry.css", (root,))

    def test_import_text_inside_comment_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = '/*\n@import "missing.css";\n*/\n.entry { color: blue; }\n'
            (root / "entry.css").write_text(original, encoding="utf-8")

            self.assertEqual(flatten_css(root / "entry.css", (root,)), original)

    def test_detects_import_cycles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.css").write_text('@import "b.css";\n', encoding="utf-8")
            (root / "b.css").write_text('@import "a.css";\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CSS import cycle detected"):
                flatten_css(root / "a.css", (root,))

    def test_rejects_duplicate_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "common.css").write_text(".common {}\n", encoding="utf-8")
            (root / "a.css").write_text('@import "common.css";\n', encoding="utf-8")
            (root / "b.css").write_text('@import "common.css";\n', encoding="utf-8")
            (root / "entry.css").write_text('@import "a.css";\n@import "b.css";\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate CSS import"):
                flatten_css(root / "entry.css", (root,))

    def test_rejects_root_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            root.mkdir()
            outside = Path(tmp) / "secret.css"
            outside.write_text(".secret {}\n", encoding="utf-8")
            (root / "entry.css").write_text('@import "../secret.css";\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escapes allowed roots"):
                flatten_css(root / "entry.css", (root,))

    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "entry.css").write_text('@import "missing.css";\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CSS file not found"):
                flatten_css(root / "entry.css", (root,))

    def test_no_font_output_emits_no_font_face(self):
        manifest = ThemeManifest(
            schema_version=1,
            name="linen",
            title="Linen",
            version="1.0.0",
            tagline="Linen canvas",
            class_name="app-theme-linen",
            navigation_menu_style=None,
            fonts={},
            stylesheet=Path("theme.css"),
            runtime=Path("theme-factory-runtime.js"),
            cover=Path("preview/cover.jpg"),
        )
        self.assertEqual(render_font_css(manifest), "")

    def test_render_font_css_all_three_roles(self):
        body_face1 = FontFace(file=Path("fonts/body-400.woff2"), weight=400, style="normal")
        body_face2 = FontFace(file=Path("fonts/body-700.woff2"), weight=700, style="normal")
        head_face = FontFace(file=Path("fonts/heading-700.woff2"), weight=700, style="normal")
        mono_face = FontFace(file=Path("fonts/mono-400.woff2"), weight=400, style="normal")

        manifest = ThemeManifest(
            schema_version=1,
            name="custom-theme",
            title="Custom Theme",
            version="1.0.0",
            tagline="Tagline",
            class_name="app-theme-custom-theme",
            navigation_menu_style=None,
            fonts={
                "body": FontRole(
                    family="Custom Body",
                    fallback=("Oracle Sans", "sans-serif"),
                    license=Path("licenses/body.txt"),
                    faces=(body_face1, body_face2),
                ),
                "heading": FontRole(
                    family="Custom Heading",
                    fallback=("Oracle Sans", "sans-serif"),
                    license=Path("licenses/head.txt"),
                    faces=(head_face,),
                ),
                "mono": FontRole(
                    family="Custom Mono",
                    fallback=("monospace",),
                    license=Path("licenses/mono.txt"),
                    faces=(mono_face,),
                ),
            },
            stylesheet=Path("theme.css"),
            runtime=Path("theme-factory-runtime.js"),
            cover=Path("preview/cover.jpg"),
        )
        css = render_font_css(manifest)
        self.assertIn('@font-face', css)
        self.assertIn('"ThemeFactory-custom-theme-body"', css)
        self.assertIn('"ThemeFactory-custom-theme-heading"', css)
        self.assertIn('"ThemeFactory-custom-theme-mono"', css)
        self.assertIn('font-display: swap;', css)
        self.assertIn('src: url("./fonts/body-400.woff2") format("woff2");', css)
        self.assertIn('--app-font-family-body:', css)
        self.assertIn('--app-font-family-heading:', css)
        self.assertIn('--app-font-family-mono:', css)
        self.assertIn('html.app-theme-custom-theme .t-HeroRegion-title', css)
        # Ensure icon font isolation
        self.assertNotIn('.fa', css)
        self.assertNotIn('.t-Icon', css)

    def test_build_theme_css_golden_order(self):
        repo_root = Path(__file__).resolve().parent.parent
        theme_root = repo_root / "sample-themes/linen"

        manifest = ThemeManifest(
            schema_version=1,
            name="linen",
            title="Linen",
            version="1.0.0",
            tagline="Light linen canvas",
            class_name="app-theme-linen",
            navigation_menu_style="t-TreeNav--styleB",
            fonts={},
            stylesheet=Path("theme.css"),
            runtime=Path("theme-factory-runtime.js"),
            cover=Path("preview/cover.jpg"),
        )
        built = build_theme_css(repo_root, theme_root, manifest, "test-commit-hash")

        # Verify exact order:
        # 1. Banner
        # 2. Shared Foundation (tokens, reset, typography, utilities)
        # 3. Theme Package Styles
        banner_idx = built.find("Theme: linen")
        foundation_idx = built.find("Shared Foundation")
        theme_idx = built.find("Theme Package Styles")

        self.assertNotEqual(banner_idx, -1)
        self.assertNotEqual(foundation_idx, -1)
        self.assertNotEqual(theme_idx, -1)
        self.assertTrue(banner_idx < foundation_idx < theme_idx)
        self.assertIn("Source commit: test-commit-hash", built)


if __name__ == "__main__":
    unittest.main()
