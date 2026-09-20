import re
import unittest
from pathlib import Path


REQUIRED_STATIC_IDS = (
    "theme_lab_typography",
    "theme_lab_surfaces",
    "theme_lab_buttons",
    "theme_lab_forms",
    "theme_lab_cards",
    "theme_lab_ir",
    "theme_lab_ig",
    "theme_lab_calendar",
    "theme_lab_chart",
    "theme_lab_overlays",
)


class ThemeLabSourceTests(unittest.TestCase):
    page = Path("applications/ut/pages/p00406-theme-lab.apx")

    def test_page_contains_every_required_native_specimen(self):
        source = self.page.read_text(encoding="utf-8")
        for static_id in REQUIRED_STATIC_IDS:
            self.assertIn(f"htmlDomId: {static_id}", source)
        for component_type in ("interactiveReport", "interactiveGrid", "calendar", "chart"):
            self.assertIn(f"type: {component_type}", source)
        self.assertIn("العربية", source)
        self.assertIn("400 500 600 700", source)

    def test_page_is_public_and_uses_native_items_and_redirects(self):
        source = self.page.read_text(encoding="utf-8")
        self.assertIn("alias: THEME-LAB", source)
        self.assertIn("authentication: public", source)
        self.assertIn("pageAccessProtection: argumentsMustHaveChecksum", source)
        for item_type in ("textField", "selectList", "datePicker", "popupLov", "radioGroup", "checkbox"):
            self.assertIn(f"type: {item_type}", source)
        for page in (1402, 1410, 1800, 1902):
            self.assertIn(f"page: {page}", source)
        self.assertNotIn("x-data", source)

    def test_data_queries_are_deterministic_and_bilingual(self):
        source = self.page.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("connect by level <= 6"), 4)
        self.assertIn("موضوع عربي", source)
        self.assertNotIn("eba_ut_", source.lower())

    def test_page_css_is_page_scoped_and_token_based(self):
        css = Path("static-files/css/pages/theme-lab.css").read_text(encoding="utf-8")
        without_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        self.assertNotRegex(without_comments, r"#[0-9a-fA-F]{3,8}\b")
        selectors = []
        for block in re.findall(r"([^{}]+)\{", without_comments):
            block = block.strip()
            if not block or block.startswith("@") or block.endswith(")"):
                continue
            selectors.extend(part.strip() for part in block.split(","))
        self.assertTrue(selectors)
        self.assertTrue(all(selector.startswith("html.page-406") for selector in selectors), selectors)
        self.assertIn("minmax(min(100%, 18rem), 1fr)", css)
        self.assertIn("@media (max-width: 767px)", css)

    def test_page_is_linked_and_css_loads_before_generated_themes(self):
        themes = Path("applications/ut/pages/p00405-themes.apx").read_text(encoding="utf-8")
        breadcrumbs = Path("applications/ut/shared-components/breadcrumbs.apx").read_text(encoding="utf-8")
        app_css = Path("static-files/css/app.css").read_text(encoding="utf-8")
        self.assertIn("page: 406", themes)
        self.assertIn("pageNumber: 406", breadcrumbs)
        self.assertLess(app_css.index('@import "pages/theme-lab.css"'), app_css.index("/* @themes:start */"))


if __name__ == "__main__":
    unittest.main()
