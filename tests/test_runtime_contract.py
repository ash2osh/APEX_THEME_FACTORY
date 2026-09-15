from pathlib import Path
import unittest


class RuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("installer/theme-factory-runtime.js").read_text(encoding="utf-8")
        cls.bootstrap_tmpl = Path("installer/templates/bootstrap.html.tmpl").read_text(encoding="utf-8")

    def test_storage_is_application_namespaced(self):
        self.assertIn("apex.themeFactory.", self.source)
        self.assertNotIn("localStorage['app.theme']", self.source)
        self.assertIn("apex.themeFactory.", self.bootstrap_tmpl)

    def test_uses_native_radio_group(self):
        self.assertIn('type: "radioGroup"', self.source)

    def test_allowlist_validation_and_iris_handling(self):
        self.assertIn('"iris"', self.source)
        self.assertIn("allowed.indexOf", self.source)

    def test_no_alpine_start(self):
        self.assertNotIn("Alpine.start", self.source)

    def test_bound_to_window_theme42ready(self):
        self.assertIn('(window)', self.source)
        self.assertIn('theme42ready.apexThemeFactory', self.source)

    def test_no_dynamic_stylesheet_insertion(self):
        self.assertNotIn("createElement('link')", self.source)
        self.assertNotIn('createElement("link")', self.source)


if __name__ == "__main__":
    unittest.main()
