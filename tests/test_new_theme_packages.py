import json
import struct
import unittest
from pathlib import Path


THEMES = {
    "carbon-volt": {
        "title": "Carbon Volt",
        "class": "app-theme-carbon-volt",
        "font": "Noto Kufi Arabic",
        "mode": "dark",
        "weights": {400, 500, 600, 700},
    },
    "velvet-signal": {
        "title": "Velvet Signal",
        "class": "app-theme-velvet-signal",
        "font": "Alexandria",
        "mode": "dark",
        "weights": {400, 500, 600, 700},
    },
    "cobalt-press": {
        "title": "Cobalt Press",
        "class": "app-theme-cobalt-press",
        "font": "Cairo",
        "mode": "light",
        "weights": {400, 500, 600, 700},
    },
    "citrus-pop": {
        "title": "Citrus Pop",
        "class": "app-theme-citrus-pop",
        "font": "Tajawal",
        "mode": "light",
        "weights": {400, 500, 700, 800},
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
    def test_manifests_fonts_and_docs_match_the_approved_contract(self):
        families = set()
        for name, expected in THEMES.items():
            with self.subTest(theme=name):
                root = Path("sample-themes") / name
                manifest = json.loads((root / "theme.json").read_text(encoding="utf-8"))

                self.assertEqual(manifest["name"], name)
                self.assertEqual(manifest["title"], expected["title"])
                self.assertEqual(manifest["class"], expected["class"])
                self.assertEqual(manifest["version"], "1.0.0")
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
                self.assertIn("UNVERIFIED", (root / "README.md").read_text(encoding="utf-8"))

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

    def test_theme_catalog_reports_every_new_package(self):
        catalog = Path("sample-themes/README.md").read_text(encoding="utf-8")
        for name in THEMES:
            with self.subTest(theme=name):
                self.assertIn(f"[{name}]({name}/)", catalog)
                self.assertIn("UNVERIFIED", next(line for line in catalog.splitlines() if f"[{name}]" in line))


if __name__ == "__main__":
    unittest.main()
