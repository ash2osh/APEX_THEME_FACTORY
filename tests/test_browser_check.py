"""Tests for the live browser check used by `scripts/theme.sh release` (tools/browser_check.py)."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from tools.browser_check import RowCapture


def capture(consumer: str, width: int, **overrides) -> RowCapture:
    page = {
        "url": "http://localhost:8181/ords/r/demo/tf-consumer-minimal-9010/home",
        "appId": "9010", "appAlias": "TF-CONSUMER-MINIMAL-9010", "pageId": "1", "apexVersion": "26.1.4",
        "browserVersion": "Chrome/140.0.7339.81",
        "bodyClasses": ["t-PageBody", "apex-theme-iris"], "htmlClasses": ["app-theme-linen"],
        "cssUrls": ["x.css"], "javascriptUrls": ["y.js"], "loadedUrls": ["x.css", "y.js"],
        "windowApp": None, "windowAlpine": None, "activeTheme": "linen",
        "registry": {"defaultTheme": "linen"}, "switcherAvailable": True,
        "fonts": [],  # linen declares no faces; a themed fixture overrides this explicitly
        "fontApexFamilyBefore": "\"Font APEX\"", "fontApexFamilyAfter": "\"Font APEX\"",
    }
    values = dict(consumer=consumer, width=width, page=page, console_errors=[], failed_requests=[],
                  fonts_verified=True, accessibility_verified=True, persistence_verified=True)
    values.update(overrides)
    return RowCapture(**values)



class RowProblemTests(unittest.TestCase):
    def test_clean_row_has_no_problems(self):
        self.assertEqual(capture("minimal", 1440).problems("linen"), [])

    def test_each_failure_is_named(self):
        row = capture("minimal", 375, console_errors=["boom"], fonts_verified=False,
                      accessibility_verified=False, persistence_verified=False, notes=["detail"])
        problems = row.problems("linen")
        self.assertIn("console error: boom", problems)
        self.assertIn("declared fonts not loaded", problems)
        self.assertIn("contrast or keyboard check failed", problems)
        self.assertIn("theme selection not kept across reload", problems)
        self.assertIn("note: detail", problems)

    def test_wrong_active_theme_is_a_problem(self):
        self.assertTrue(capture("minimal", 1440).problems("citrus-pop"))


class ContrastInstrumentTests(unittest.TestCase):
    """The audit must score SVG text too: JET charts paint their labels with `fill`, not `color`."""

    def test_documented_snippet_scores_svg_text_fill(self):
        from tools.browser_check import _contrast_function
        snippet = _contrast_function()
        self.assertIn("svg", snippet.lower())
        self.assertIn("fill", snippet)
        # a tree walker over text nodes alone cannot reach SVG <text>; the snippet must query them
        self.assertRegex(snippet, r"querySelectorAll\(\s*['\"][^'\"]*svg[^'\"]*text")



class LiveCaptureTests(unittest.TestCase):
    def test_live_capture_uses_per_tab_emulation_not_shared_window_resize(self):
        import inspect
        from tools.browser_check import LiveBrowserMatrix
        source = inspect.getsource(LiveBrowserMatrix.capture_row)
        self.assertIn('"emulate"', source)
        self.assertNotIn('"resize_page"', source)



class FontExpectationTests(unittest.TestCase):
    """The capture must derive what SHOULD load from the package, then prove it did.

    Until 2026-09-17 the page snippet probed a hard-coded ['Font APEX', 'Oracle Sans']
    and emitted {family, loaded}, so a font-bearing package was stamped fontsVerified
    without any evidence its own WOFF2 files were ever requested.
    """

    def _package(self, fonts):
        root = self.tmp / "pkg"
        (root / "fonts").mkdir(parents=True, exist_ok=True)
        (root / "licenses").mkdir(parents=True, exist_ok=True)
        manifest = {"schemaVersion": 1, "name": "linen", "title": "Linen", "version": "1.0.0",
                    "tagline": "t", "class": "app-theme-linen",
                    "compatibility": {"apex": ">=26.1.0 <26.2.0", "themeNumber": 42,
                                      "baseTheme": "ut-26.1", "themeStyle": "Iris"},
                    "assets": {"stylesheet": "theme.css"}}
        if fonts:
            manifest["fonts"] = fonts
        (root / "theme.json").write_text(json.dumps(manifest), encoding="utf-8")
        archive = self.tmp / "linen-1.0.0.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.write(root / "theme.json", "linen-1.0.0/theme.json")
        return archive

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_expectations_are_read_from_the_package_manifest(self):
        from tools.browser_check import font_expectations
        archive = self._package({"body": {"family": "IBM Plex Sans", "fallback": ["sans-serif"],
                                          "license": "licenses/x.txt",
                                          "faces": [{"file": "fonts/a.woff2", "weight": 400, "style": "normal"},
                                                    {"file": "fonts/b.woff2", "weight": 600, "style": "normal"}]}})
        expected = font_expectations(archive, "linen")
        self.assertEqual(len(expected), 2)
        self.assertEqual(expected[0]["role"], "body")
        self.assertEqual(expected[0]["family"], "ThemeFactory-linen-body")
        self.assertEqual({e["weight"] for e in expected}, {400, 600})
        self.assertEqual(expected[0]["file"], "fonts/a.woff2")

    def test_fontless_package_expects_nothing(self):
        from tools.browser_check import font_expectations
        self.assertEqual(font_expectations(self._package(None), "linen"), [])

    def test_a_declared_face_that_never_loaded_fails_the_check(self):
        from tools.browser_check import evaluate_fonts
        expected = [{"role": "body", "family": "ThemeFactory-linen-body", "weight": 400,
                     "style": "normal", "file": "fonts/a.woff2"}]
        page = {"fontApexFamilyAfter": '"Font APEX"', "fontApexLoaded": True,
                "bodyFontFamily": '"ThemeFactory-linen-body", sans-serif',
                "faceResults": [{"family": "ThemeFactory-linen-body", "weight": 400, "style": "normal",
                                 "check": False, "requestUrl": ""}]}
        ok, entries = evaluate_fonts(page, {"body": "system-ui"}, "linen", expected)
        self.assertFalse(ok, "a declared face that did not load must not pass")
        self.assertEqual(len(entries), 1)
        self.assertEqual(set(entries[0]),
                         {"role", "family", "weight", "style", "check", "requestUrl", "mimeType"})

    def test_all_faces_loaded_passes_and_matches_the_schema(self):
        from tools.browser_check import evaluate_fonts
        expected = [{"role": "body", "family": "ThemeFactory-linen-body", "weight": 400,
                     "style": "normal", "file": "fonts/a.woff2"}]
        page = {"fontApexFamilyAfter": '"Font APEX"', "fontApexLoaded": True,
                "bodyFontFamily": '"ThemeFactory-linen-body", sans-serif',
                "faceResults": [{"family": "ThemeFactory-linen-body", "weight": 400, "style": "normal",
                                 "check": True, "requestUrl": "http://h/fonts/a.woff2"}]}
        ok, entries = evaluate_fonts(page, {"body": "system-ui"}, "linen", expected)
        self.assertTrue(ok)
        self.assertEqual(entries[0]["mimeType"], "font/woff2")



class FaceLoadForcingTests(unittest.TestCase):
    """A declared face must be proven usable, not merely observed being used.

    Until 2026-09-17 the page snippet asked `document.fonts.check` and looked for a
    resource entry, both of which only become true once something on the page renders
    text in that family. `solarized-dark` declares a mono face that no captured page
    exercises, so a correctly packaged, served and usable face was reported
    `check: false` and the theme was refused. The capture must force each declared
    face to load and judge *that*, then read the resource entries afterwards.
    """

    def test_snippet_forces_every_declared_face_to_load(self):
        from tools.browser_check import page_snippet
        snippet = page_snippet([{"role": "mono", "family": "ThemeFactory-solarized-dark-mono",
                                 "weight": 400, "style": "normal", "file": "fonts/m.woff2"}])
        self.assertIn("document.fonts.load(", snippet,
                      "the snippet must force the face to load, not wait for the page to use it")

    def test_snippet_reads_resource_entries_after_forcing_the_loads(self):
        from tools.browser_check import page_snippet
        snippet = page_snippet([])
        forced = snippet.index("document.fonts.load(")
        harvested = snippet.rindex("getEntriesByType('resource')")
        self.assertLess(forced, harvested,
                        "requestUrl is only meaningful if resources are read after the forced load")

    def test_expected_faces_are_injected_into_the_snippet(self):
        from tools.browser_check import page_snippet
        snippet = page_snippet([{"role": "body", "family": "ThemeFactory-linen-body",
                                 "weight": 400, "style": "normal", "file": "fonts/a.woff2"}])
        self.assertIn("ThemeFactory-linen-body", snippet)
        self.assertNotIn("__EXPECTED_FACES__", snippet)



if __name__ == "__main__":
    unittest.main()
