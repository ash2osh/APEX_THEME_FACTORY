import unittest
from pathlib import Path


class AlpineFixtureTests(unittest.TestCase):
    def test_component_registers_once_and_never_restarts_alpine(self):
        component_path = Path("static-files/js/components/themeFactoryDisclosure.js")
        self.assertTrue(component_path.exists(), f"Missing {component_path}")
        source = component_path.read_text(encoding="utf-8")
        self.assertIn("document.addEventListener('alpine:init'", source)
        self.assertIn("{ once: true }", source)
        self.assertNotIn("Alpine.start", source)
        self.assertIn("Alpine.data('themeFactoryDisclosure'", source)

    def test_page_has_real_item_region_and_refresh_action(self):
        page_path = Path("applications/ut/pages/p00409-theme-factory-lifecycle.apx")
        self.assertTrue(page_path.exists(), f"Missing {page_path}")
        page = page_path.read_text(encoding="utf-8")
        for phrase in (
            "P409_DISCLOSURE_OPEN",
            "theme_factory_disclosure_region",
            "apex.region('theme_factory_disclosure_region').refresh()",
            "type: dynamicContent",
            "REFRESH_FIXTURE",
        ):
            self.assertIn(phrase, page)

        # Markup assertions
        self.assertIn("aria-expanded", page)
        self.assertIn("aria-controls", page)
        self.assertIn("x-show", page)
        self.assertIn("x-cloak", page)
        # Ensure no inline duplicate definition
        self.assertNotIn("Alpine.data", page)

    def test_application_loads_component_before_alpine(self):
        app_path = Path("applications/ut/application.apx")
        app_text = app_path.read_text(encoding="utf-8")
        component_file = "#APP_FILES#js/components/themeFactoryDisclosure.js"
        alpine_file = "#APP_FILES#js/vendor/alpine.min.js"
        self.assertIn(component_file, app_text)
        self.assertIn(alpine_file, app_text)
        idx_comp = app_text.index(component_file)
        idx_alpine = app_text.index(alpine_file)
        self.assertLess(idx_comp, idx_alpine, "themeFactoryDisclosure.js must load before alpine.min.js")

    def test_navigation_entry_exists(self):
        lists_path = Path("applications/ut/shared-components/lists.apx")
        lists_text = lists_path.read_text(encoding="utf-8")
        self.assertIn("Theme Factory Lifecycle", lists_text)
        self.assertIn("page: 409", lists_text)


if __name__ == "__main__":
    unittest.main()
