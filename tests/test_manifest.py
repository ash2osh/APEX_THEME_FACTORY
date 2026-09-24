import json
from pathlib import Path
import shutil
import tempfile
import unittest

from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import load_manifest


class ManifestTests(unittest.TestCase):
    def write_package(self, payload: dict, files: dict[str, bytes] | None = None) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / payload.get("name", "test-theme")
        root.mkdir(parents=True, exist_ok=True)
        (root / "theme.json").write_text(json.dumps(payload), encoding="utf-8")
        for relative, content in (files or {}).items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return root

    def test_accepts_no_font_manifest(self):
        root = Path("tests/fixtures/packages/valid-basic")
        manifest = load_manifest(root / "theme.json", root)
        self.assertEqual(manifest.name, "valid-basic")
        self.assertEqual(manifest.fonts, {})
        self.assertEqual(manifest.class_name, "app-theme-valid-basic")
        self.assertEqual(manifest.font_asset_files(), ())

    def test_optional_direction_is_preserved_and_must_be_non_empty(self):
        fixture = Path("tests/fixtures/packages/valid-basic/theme.json")
        raw = json.loads(fixture.read_text(encoding="utf-8"))
        root = self.write_package(raw)
        manifest_path = root / "theme.json"
        raw["direction"] = "Editorial rules with offset geometry."
        manifest_path.write_text(json.dumps(raw), encoding="utf-8")
        self.assertEqual(
            load_manifest(manifest_path, root).direction,
            "Editorial rules with offset geometry.",
        )

        raw["direction"] = "   "
        manifest_path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaisesRegex(PackageError, "direction"):
            load_manifest(manifest_path, root)

    def test_rejects_external_font_path(self):
        root = Path("tests/fixtures/packages/invalid/external-font")
        with self.assertRaises(PackageError) as ctx:
            load_manifest(root / "theme.json", root)
        self.assertIn("fonts/body/faces/0/file", str(ctx.exception))

    def test_directory_name_mismatch_fails(self):
        payload = {
            "schemaVersion": 1,
            "name": "mismatch-name",
            "title": "Title",
            "version": "1.0.0",
            "tagline": "Tagline",
            "class": "app-theme-mismatch-name",
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
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "actual-dir"
            root.mkdir()
            (root / "theme.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(PackageError) as ctx:
                load_manifest(root / "theme.json", root)
            self.assertIn("does not match package directory", str(ctx.exception))

    def test_unknown_top_level_property_fails(self):
        payload = {
            "schemaVersion": 1,
            "name": "valid-theme",
            "unknownProperty": True,
            "title": "Title",
            "version": "1.0.0",
            "tagline": "Tagline",
            "class": "app-theme-valid-theme",
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
        root = self.write_package(payload)
        with self.assertRaises(PackageError) as ctx:
            load_manifest(root / "theme.json", root)
        self.assertIn("Unknown property 'unknownProperty'", str(ctx.exception))

    def test_invalid_semantic_version_fails(self):
        payload = {
            "schemaVersion": 1,
            "name": "valid-theme",
            "title": "Title",
            "version": "v1.0",  # invalid semver
            "tagline": "Tagline",
            "class": "app-theme-valid-theme",
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
        root = self.write_package(payload)
        with self.assertRaises(PackageError) as ctx:
            load_manifest(root / "theme.json", root)
        self.assertIn("is not a valid semantic version", str(ctx.exception))

    def test_invalid_compatibility_boundary_fails(self):
        payload = {
            "schemaVersion": 1,
            "name": "valid-theme",
            "title": "Title",
            "version": "1.0.0",
            "tagline": "Tagline",
            "class": "app-theme-valid-theme",
            "compatibility": {
                "apex": ">=26.1.0 <26.2.0",
                "themeNumber": 42,
                "baseTheme": "ut-26.1",
                "themeStyle": "Vita",  # Not Iris
            },
            "assets": {
                "stylesheet": "theme.css",
                "runtime": "theme-factory-runtime.js",
                "cover": "preview/cover.jpg",
            },
        }
        root = self.write_package(payload)
        with self.assertRaises(PackageError) as ctx:
            load_manifest(root / "theme.json", root)
        self.assertIn("compatibility/themeStyle must be 'Iris'", str(ctx.exception))

    def test_apex_compatibility_must_be_exact_26_1_range(self):
        payload = json.loads(
            Path("tests/fixtures/packages/valid-basic/theme.json").read_text(encoding="utf-8")
        )
        payload["compatibility"]["apex"] = ">=24.1.0"
        root = self.write_package(payload)

        with self.assertRaisesRegex(PackageError, "compatibility/apex"):
            load_manifest(root / "theme.json", root)

    def test_unreferenced_woff2_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "custom-font"
            shutil.copytree(Path("tests/fixtures/packages/custom-font"), root)
            (root / "fonts/rogue.woff2").write_bytes(b"wOF2not-declared")

            with self.assertRaisesRegex(PackageError, "unreferenced font"):
                load_manifest(root / "theme.json", root)

    def test_non_woff2_font_file_in_fonts_directory_fails(self):
        # TrueType/OpenType (or any stray file) under fonts/ is rejected before packaging
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "custom-font"
            shutil.copytree(Path("tests/fixtures/packages/custom-font"), root)
            (root / "fonts/stray.ttf").write_bytes(b"\x00\x01\x00\x00")
            with self.assertRaises(PackageError) as context:
                load_manifest(root / "theme.json", root)
            self.assertIn("fonts/stray.ttf", str(context.exception))

    def test_missing_body_role_when_fonts_defined_fails(self):
        payload = {
            "schemaVersion": 1,
            "name": "valid-theme",
            "title": "Title",
            "version": "1.0.0",
            "tagline": "Tagline",
            "class": "app-theme-valid-theme",
            "compatibility": {
                "apex": ">=26.1.0 <26.2.0",
                "themeNumber": 42,
                "baseTheme": "ut-26.1",
                "themeStyle": "Iris",
            },
            "fonts": {
                "heading": {
                    "family": "Heading Font",
                    "fallback": ["sans-serif"],
                    "license": "licenses/license.txt",
                    "faces": [{"file": "fonts/head.woff2", "weight": 700, "style": "normal"}],
                }
            },
            "assets": {
                "stylesheet": "theme.css",
                "runtime": "theme-factory-runtime.js",
                "cover": "preview/cover.jpg",
            },
        }
        root = self.write_package(payload)
        with self.assertRaises(PackageError) as ctx:
            load_manifest(root / "theme.json", root)
        self.assertIn("fonts must include 'body' role", str(ctx.exception))

    def test_duplicate_face_tuple_fails(self):
        payload = {
            "schemaVersion": 1,
            "name": "valid-theme",
            "title": "Title",
            "version": "1.0.0",
            "tagline": "Tagline",
            "class": "app-theme-valid-theme",
            "compatibility": {
                "apex": ">=26.1.0 <26.2.0",
                "themeNumber": 42,
                "baseTheme": "ut-26.1",
                "themeStyle": "Iris",
            },
            "fonts": {
                "body": {
                    "family": "Body Font",
                    "fallback": ["sans-serif"],
                    "license": "licenses/license.txt",
                    "faces": [
                        {"file": "fonts/body-1.woff2", "weight": 400, "style": "normal"},
                        {"file": "fonts/body-2.woff2", "weight": 400, "style": "normal"},
                    ],
                }
            },
            "assets": {
                "stylesheet": "theme.css",
                "runtime": "theme-factory-runtime.js",
                "cover": "preview/cover.jpg",
            },
        }
        files = {
            "licenses/license.txt": b"OFL License Text",
            "fonts/body-1.woff2": b"wOF2sample",
            "fonts/body-2.woff2": b"wOF2sample",
        }
        root = self.write_package(payload, files)
        with self.assertRaises(PackageError) as ctx:
            load_manifest(root / "theme.json", root)
        self.assertIn("duplicate face tuple", str(ctx.exception))

    def test_invalid_woff2_signature_fails(self):
        payload = {
            "schemaVersion": 1,
            "name": "valid-theme",
            "title": "Title",
            "version": "1.0.0",
            "tagline": "Tagline",
            "class": "app-theme-valid-theme",
            "compatibility": {
                "apex": ">=26.1.0 <26.2.0",
                "themeNumber": 42,
                "baseTheme": "ut-26.1",
                "themeStyle": "Iris",
            },
            "fonts": {
                "body": {
                    "family": "Body Font",
                    "fallback": ["sans-serif"],
                    "license": "licenses/license.txt",
                    "faces": [
                        {"file": "fonts/body.woff2", "weight": 400, "style": "normal"},
                    ],
                }
            },
            "assets": {
                "stylesheet": "theme.css",
                "runtime": "theme-factory-runtime.js",
                "cover": "preview/cover.jpg",
            },
        }
        files = {
            "licenses/license.txt": b"OFL License Text",
            "fonts/body.woff2": b"BAD!not-woff2",
        }
        root = self.write_package(payload, files)
        with self.assertRaises(PackageError) as ctx:
            load_manifest(root / "theme.json", root)
        self.assertIn("invalid signature", str(ctx.exception))

    def test_empty_license_fails(self):
        payload = {
            "schemaVersion": 1,
            "name": "valid-theme",
            "title": "Title",
            "version": "1.0.0",
            "tagline": "Tagline",
            "class": "app-theme-valid-theme",
            "compatibility": {
                "apex": ">=26.1.0 <26.2.0",
                "themeNumber": 42,
                "baseTheme": "ut-26.1",
                "themeStyle": "Iris",
            },
            "fonts": {
                "body": {
                    "family": "Body Font",
                    "fallback": ["sans-serif"],
                    "license": "licenses/license.txt",
                    "faces": [
                        {"file": "fonts/body.woff2", "weight": 400, "style": "normal"},
                    ],
                }
            },
            "assets": {
                "stylesheet": "theme.css",
                "runtime": "theme-factory-runtime.js",
                "cover": "preview/cover.jpg",
            },
        }
        files = {
            "licenses/license.txt": b"",  # empty license
            "fonts/body.woff2": b"wOF2sample",
        }
        root = self.write_package(payload, files)
        with self.assertRaises(PackageError) as ctx:
            load_manifest(root / "theme.json", root)
        self.assertIn("license file is empty", str(ctx.exception))

    def test_valid_custom_font_package_succeeds(self):
        payload = {
            "schemaVersion": 1,
            "name": "font-theme",
            "title": "Custom Font Theme",
            "version": "1.0.0",
            "tagline": "Testing all three font roles.",
            "class": "app-theme-font-theme",
            "compatibility": {
                "apex": ">=26.1.0 <26.2.0",
                "themeNumber": 42,
                "baseTheme": "ut-26.1",
                "themeStyle": "Iris",
            },
            "fonts": {
                "body": {
                    "family": "Custom Body",
                    "fallback": ["Oracle Sans", "sans-serif"],
                    "license": "licenses/ofl-body.txt",
                    "faces": [
                        {"file": "fonts/custom-body-400.woff2", "weight": 400, "style": "normal"},
                        {"file": "fonts/custom-body-700.woff2", "weight": 700, "style": "normal"},
                    ],
                },
                "heading": {
                    "family": "Custom Heading",
                    "fallback": ["Oracle Sans", "sans-serif"],
                    "license": "licenses/ofl-heading.txt",
                    "faces": [
                        {"file": "fonts/custom-heading-700.woff2", "weight": 700, "style": "normal"},
                    ],
                },
                "mono": {
                    "family": "Custom Mono",
                    "fallback": ["monospace"],
                    "license": "licenses/ofl-mono.txt",
                    "faces": [
                        {"file": "fonts/custom-mono-400.woff2", "weight": 400, "style": "normal"},
                    ],
                },
            },
            "assets": {
                "stylesheet": "theme.css",
                "runtime": "theme-factory-runtime.js",
                "cover": "preview/cover.jpg",
            },
        }
        files = {
            "licenses/ofl-body.txt": b"Body License",
            "licenses/ofl-heading.txt": b"Heading License",
            "licenses/ofl-mono.txt": b"Mono License",
            "fonts/custom-body-400.woff2": b"wOF2sample",
            "fonts/custom-body-700.woff2": b"wOF2sample",
            "fonts/custom-heading-700.woff2": b"wOF2sample",
            "fonts/custom-mono-400.woff2": b"wOF2sample",
        }
        root = self.write_package(payload, files)
        manifest = load_manifest(root / "theme.json", root)
        self.assertEqual(manifest.name, "font-theme")
        self.assertEqual(len(manifest.fonts), 3)
        self.assertEqual(len(manifest.font_asset_files()), 7)


    def test_title_must_be_safe_for_apexlang_and_script(self):
        raw = json.loads(Path("tests/fixtures/packages/valid-basic/theme.json").read_text(encoding="utf-8"))
        root = self.write_package(raw)
        manifest_path = root / "theme.json"
        for title in ("Estate Slate Dark", "Linen 2", "Café Noir", "O'Neil"):
            raw["title"] = title
            manifest_path.write_text(json.dumps(raw), encoding="utf-8")
            self.assertEqual(load_manifest(manifest_path, root).title, title)
        for title in ("</script><script>alert(1)</script>", "R&D.", "Two\nlines", " padded",
                      "x" * 65, "Label (x)", "a: b", 'say "hi"', ""):
            raw["title"] = title
            manifest_path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(PackageError, msg=title):
                load_manifest(manifest_path, root)

    def test_navigation_menu_style_must_be_a_tree_nav_option(self):
        raw = json.loads(Path("tests/fixtures/packages/valid-basic/theme.json").read_text(encoding="utf-8"))
        root = self.write_package(raw)
        manifest_path = root / "theme.json"
        raw["templateOptions"] = {"navigationMenuStyle": "t-TreeNav--styleB"}
        manifest_path.write_text(json.dumps(raw), encoding="utf-8")
        self.assertEqual(load_manifest(manifest_path, root).navigation_menu_style, "t-TreeNav--styleB")
        for style in ("t-TreeNav--styleB\n        cssClasses: evil", "styleB", "t-TreeNav--a]"):
            raw["templateOptions"] = {"navigationMenuStyle": style}
            manifest_path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(PackageError, "navigationMenuStyle", msg=style):
                load_manifest(manifest_path, root)


if __name__ == "__main__":
    unittest.main()
