import json
import re
import struct
import unittest
from pathlib import Path

from lib.theme_factory.discovery import discover_themes
from lib.theme_factory.fingerprint import check_uniqueness
from lib.theme_factory.recipe import contrast_ratio, load_recipe


THEMES = {
    "carbon-volt": {
        "title": "Carbon Volt",
        "class": "app-theme-carbon-volt",
        "font": "Noto Kufi Arabic",
        "mode": "dark",
        "weights": {400, 500, 600, 700},
        "anchors": {"#0a0d0b", "#151a16", "#b8ff3d", "#38e8ff", "#f2f7f0"},
        "radius": "0px",
        "control": "2.125rem",
    },
    "velvet-signal": {
        "title": "Velvet Signal",
        "class": "app-theme-velvet-signal",
        "font": "Alexandria",
        "mode": "dark",
        "weights": {400, 500, 600, 700},
        "anchors": {"#140b1b", "#24132f", "#ff4fb3", "#9c6cff", "#fff4fc"},
        "radius": "10px",
        "control": "2.75rem",
    },
    "cobalt-press": {
        "title": "Cobalt Press",
        "class": "app-theme-cobalt-press",
        "font": "Cairo",
        "mode": "light",
        "weights": {400, 500, 600, 700},
        "anchors": {"#fff8e8", "#ffffff", "#1a1a26", "#2457ff", "#c53618"},
        "radius": "0px",
        "control": "2.5rem",
    },
    "citrus-pop": {
        "title": "Citrus Pop",
        "class": "app-theme-citrus-pop",
        "font": "Tajawal",
        "mode": "light",
        "weights": {400, 500, 700, 800},
        "anchors": {"#ecfaf6", "#ffffff", "#073b3a", "#007f78", "#ff6b35"},
        "radius": "8px",
        "control": "2.625rem",
    },
}

CSS_MODULES = {
    "shell.css",
    "regions.css",
    "buttons.css",
    "forms.css",
    "reports.css",
    "dialogs.css",
    "misc.css",
}


def jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        raise AssertionError(f"{path} is not a JPEG")
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        length = struct.unpack(">H", data[offset : offset + 2])[0]
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
            return width, height
        offset += length
    raise AssertionError(f"{path} has no JPEG size marker")


class NewThemePackageTests(unittest.TestCase):
    def test_every_theme_has_a_distinct_structural_identity_marker_set(self):
        markers = {
            "linen": ("no accent strip", "editorial title tracking", "underline selected navigation"),
            "estate-slate": ("section markers", "metric-strip", "outlined form borders", "ruled data rows", "rail selection"),
            "estate-slate-dark": ("dense rail", "layered monitor panels", "map-frame"),
            "solarized-dark": ("minimal command nav", "flat pane", "terminal rule"),
            "carbon-volt": ("segmented rail", "hard module", "outline-state"),
            "velvet-signal": ("pill navigation", "sculpted layered surface", "smooth lift"),
            "cobalt-press": ("editorial rules", "offset sheet", "cobalt underline", "vermilion mark"),
            "citrus-pop": ("pill navigation", "buoyant card lift", "teal structure", "tangerine action"),
        }
        for name, expected in markers.items():
            content = "\n".join(
                (Path("sample-themes") / name / "css/apex" / module).read_text(encoding="utf-8").casefold()
                for module in CSS_MODULES
            )
            with self.subTest(theme=name):
                for marker in expected:
                    self.assertIn(marker.casefold(), content)
        for name in ("carbon-volt", "velvet-signal"):
            content = "\n".join(
                (Path("sample-themes") / name / "css/apex" / module).read_text(encoding="utf-8")
                for module in CSS_MODULES
            ).casefold()
            self.assertNotIn("vs code", content)
            self.assertNotIn("solarized", content)

    def test_every_theme_has_an_explicit_version_two_identity_recipe(self):
        vectors = {}
        for discovered in discover_themes(Path.cwd()):
            with self.subTest(theme=discovered.name):
                recipe_path = discovered.root / "theme.recipe.json"
                self.assertTrue(recipe_path.is_file(), f"missing {recipe_path}")
                recipe = load_recipe(recipe_path)
                self.assertEqual(recipe.schema_version, 2)
                self.assertEqual(recipe.identity.name, discovered.name)
                vector = (
                    recipe.components.navigation,
                    recipe.components.cards,
                    recipe.components.buttons,
                    recipe.components.forms,
                    recipe.components.reports,
                    recipe.components.dialogs,
                    recipe.rhythm,
                    recipe.interaction,
                    recipe.responsive,
                )
                self.assertNotIn(vector, vectors, f"identity vector collides with {vectors.get(vector)}")
                vectors[vector] = discovered.name
        self.assertEqual(len(vectors), 8)

    def test_citrus_hot_button_text_meets_wcag_aa_on_tangerine(self):
        root = Path("sample-themes/citrus-pop/css")
        tokens = (root / "tokens.css").read_text(encoding="utf-8")
        buttons = (root / "apex/buttons.css").read_text(encoding="utf-8")

        def literal(name: str) -> str:
            match = re.search(rf"{re.escape(name)}:\s*(#[0-9a-fA-F]{{6}})\s*;", tokens)
            self.assertIsNotNone(match, f"{name} must be a literal audited color")
            return match.group(1)

        self.assertGreaterEqual(
            contrast_ratio(literal("--cit-hot-button-text"), literal("--cit-tangerine")),
            4.5,
        )
        self.assertIn("--a-button-text-color: var(--cit-hot-button-text)", buttons)
        self.assertIn("--a-button-hover-text-color: var(--cit-hot-button-text)", buttons)

    def test_solarized_transparent_primary_button_uses_text_safe_link_color(self):
        buttons = (Path("sample-themes/solarized-dark/css/apex/buttons.css")).read_text(encoding="utf-8")
        primary_rule = re.search(
            r"\.app-theme-solarized-dark \.apex-theme-iris \.t-Button--primary\s*\{(?P<body>[^}]*)\}",
            buttons,
        )
        self.assertIsNotNone(primary_rule, "Solarized primary button rule must remain explicit")
        body = primary_rule.group("body")
        self.assertIn("color: var(--app-color-primary)", body)

    def test_all_current_themes_avoid_error_level_uniqueness_findings(self):
        roots = tuple(theme.root for theme in discover_themes(Path.cwd()))
        for candidate in roots:
            with self.subTest(theme=candidate.name):
                issues = check_uniqueness(candidate, roots)
                self.assertEqual(
                    [issue.message for issue in issues if issue.severity == "error"],
                    [],
                )

    def test_manifests_fonts_and_docs_match_the_approved_contract(self):
        families = set()
        for name, expected in THEMES.items():
            with self.subTest(theme=name):
                root = Path("sample-themes") / name
                manifest = json.loads((root / "theme.json").read_text(encoding="utf-8"))

                self.assertEqual(manifest["name"], name)
                self.assertEqual(manifest["title"], expected["title"])
                self.assertEqual(manifest["class"], expected["class"])
                expected_version = "1.1.0" if name in THEMES else "1.0.0"
                self.assertEqual(manifest["version"], expected_version)
                self.assertEqual(manifest["compatibility"]["themeStyle"], "Iris")
                self.assertEqual(manifest["compatibility"]["themeNumber"], 42)

                body = manifest["fonts"]["body"]
                self.assertEqual(body["family"], expected["font"])
                self.assertEqual(
                    {(face["weight"], face["style"]) for face in body["faces"]},
                    {(weight, "normal") for weight in expected["weights"]},
                )
                families.add(body["family"])
                for face in body["faces"]:
                    font = root / face["file"]
                    self.assertEqual(font.read_bytes()[:4], b"wOF2")
                self.assertTrue((root / body["license"]).read_text(encoding="utf-8").strip())

                self.assertEqual(jpeg_dimensions(root / "preview/cover.jpg")[0], 960)

        self.assertEqual(len(families), len(THEMES), "Every new theme must use a unique family")

    def test_css_packages_have_the_standard_scoped_module_contract(self):
        for name, expected in THEMES.items():
            with self.subTest(theme=name):
                root = Path("sample-themes") / name
                self.assertEqual(
                    {path.name for path in (root / "css/apex").glob("*.css")},
                    CSS_MODULES,
                )
                tokens = (root / "css/tokens.css").read_text(encoding="utf-8")
                self.assertIn(f"html.{expected['class']}", tokens)
                self.assertIn(f"color-scheme: {expected['mode']}", tokens)

                normalized = tokens.lower()
                for anchor in expected["anchors"]:
                    self.assertIn(anchor, normalized)
                self.assertIn(f"--app-radius-sm: {expected['radius']}", tokens)
                self.assertIn(f"--app-control-h: {expected['control']}", tokens)
                self.assertIn(f'"ThemeFactory-{name}-body"', tokens)

                if expected["mode"] == "dark":
                    for required_atom in (
                        "--ut-color-scheme: dark",
                        "--a-palette-primary:",
                        "--a-checkbox-background-color:",
                        "--a-datepicker-background-color:",
                        "--a-gv-background-color:",
                        "--a-menu-background-color:",
                        "--oj-core-text-color-primary:",
                    ):
                        self.assertIn(required_atom, tokens)

    def test_themes_are_component_systems_not_duplicate_recolors(self):
        bundles = {}
        for name in THEMES:
            apex = Path("sample-themes") / name / "css/apex"
            bundles[name] = "\n".join(
                (apex / module).read_text(encoding="utf-8") for module in sorted(CSS_MODULES)
            )

        for left_index, left in enumerate(THEMES):
            for right in list(THEMES)[left_index + 1 :]:
                with self.subTest(left=left, right=right):
                    left_shape = bundles[left].replace(left, "THEME")
                    right_shape = bundles[right].replace(right, "THEME")
                    self.assertNotEqual(left_shape, right_shape)

        signatures = {
            "carbon-volt": ("technical-grid", "telemetry-rail"),
            "velvet-signal": ("signal-glow", "layered-surface"),
            "cobalt-press": ("editorial-rule", "offset-shadow"),
            "citrus-pop": ("buoyant-card", "pill-control"),
        }
        for name, markers in signatures.items():
            with self.subTest(theme=name):
                for marker in markers:
                    self.assertIn(marker, bundles[name])

    def test_theme_list_names_every_new_package(self):
        catalog = Path("sample-themes/README.md").read_text(encoding="utf-8")
        for name in THEMES:
            with self.subTest(theme=name):
                self.assertIn(f"[{name}]({name}/)", catalog)


if __name__ == "__main__":
    unittest.main()
