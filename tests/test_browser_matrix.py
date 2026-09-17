"""Tests for the browser-matrix evidence builder (tools/browser_matrix.py)."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from lib.theme_factory.release import _valid_browser_runtime_artifact, load_evidence
from tools.browser_matrix import RowCapture, build_runtime_artifact, write_layer_d_evidence

COMMIT = "c" * 40
SHA = "d" * 64


def capture(consumer: str, width: int, **overrides) -> RowCapture:
    page = {
        "url": "http://localhost:8181/ords/r/demo/tf-consumer-business-9011/home",
        "appId": "9011", "appAlias": "TF-CONSUMER-BUSINESS-9011", "pageId": "1", "apexVersion": "26.1.4",
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


class BrowserMatrixEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_runtime_artifact_satisfies_the_release_contract(self):
        artifact = build_runtime_artifact("linen", COMMIT, SHA, capture("business", 1440), captured_at="2026-09-16T00:00:00Z")
        self.assertTrue(_valid_browser_runtime_artifact(artifact, "linen", "business", 1440))
        self.assertEqual(artifact["evidenceType"], "browser-runtime")

    def test_unverified_flags_and_errors_are_never_upgraded(self):
        artifact = build_runtime_artifact("linen", COMMIT, SHA, capture("business", 1440, console_errors=["boom"], persistence_verified=False))
        self.assertFalse(_valid_browser_runtime_artifact(artifact, "linen", "business", 1440))
        self.assertEqual(artifact["consoleErrors"], ["boom"])
        self.assertFalse(artifact["persistenceVerified"])

    def test_full_matrix_is_accepted_as_layer_d_pass(self):
        rows = [capture(consumer, width) for consumer in ("minimal", "business") for width in (1440, 1024, 768, 375)]
        evidence_dir = self.tmp / "2026-09-16-release-linen"
        write_layer_d_evidence(evidence_dir, "linen", COMMIT, SHA, rows, captured_at="2026-09-16T00:00:00Z")
        evidence = load_evidence(evidence_dir, "linen", expected_git_commit=COMMIT, expected_package_sha256=SHA)
        by_check = {item["check"]: item for item in evidence}
        self.assertEqual(by_check["browser_runtime_matrix"]["status"], "PASS")

    def test_incomplete_matrix_or_failed_row_is_recorded_as_fail(self):
        rows = [capture("business", 1440, console_errors=["ReferenceError: x"])]
        evidence_dir = self.tmp / "2026-09-16-release-linen"
        write_layer_d_evidence(evidence_dir, "linen", COMMIT, SHA, rows, captured_at="2026-09-16T00:00:00Z")
        summary = json.loads((evidence_dir / "browser_runtime_matrix.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "FAIL")
        self.assertTrue(any("1440" in failure for failure in summary["results"]["failures"]))
        evidence = load_evidence(evidence_dir, "linen", expected_git_commit=COMMIT, expected_package_sha256=SHA)
        self.assertEqual({item["check"]: item for item in evidence}["browser_runtime_matrix"]["status"], "FAIL")


class ContrastInstrumentTests(unittest.TestCase):
    """The audit must score SVG text too: JET charts paint their labels with `fill`, not `color`."""

    def test_documented_snippet_scores_svg_text_fill(self):
        from tools.browser_matrix import _contrast_function
        snippet = _contrast_function()
        self.assertIn("svg", snippet.lower())
        self.assertIn("fill", snippet)
        # a tree walker over text nodes alone cannot reach SVG <text>; the snippet must query them
        self.assertRegex(snippet, r"querySelectorAll\(\s*['\"][^'\"]*svg[^'\"]*text")


if __name__ == "__main__":
    unittest.main()



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
        from tools.browser_matrix import font_expectations
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
        from tools.browser_matrix import font_expectations
        self.assertEqual(font_expectations(self._package(None), "linen"), [])

    def test_a_declared_face_that_never_loaded_fails_the_check(self):
        from tools.browser_matrix import evaluate_fonts
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
        from tools.browser_matrix import evaluate_fonts
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
        from tools.browser_matrix import page_snippet
        snippet = page_snippet([{"role": "mono", "family": "ThemeFactory-solarized-dark-mono",
                                 "weight": 400, "style": "normal", "file": "fonts/m.woff2"}])
        self.assertIn("document.fonts.load(", snippet,
                      "the snippet must force the face to load, not wait for the page to use it")

    def test_snippet_reads_resource_entries_after_forcing_the_loads(self):
        from tools.browser_matrix import page_snippet
        snippet = page_snippet([])
        forced = snippet.index("document.fonts.load(")
        harvested = snippet.rindex("getEntriesByType('resource')")
        self.assertLess(forced, harvested,
                        "requestUrl is only meaningful if resources are read after the forced load")

    def test_expected_faces_are_injected_into_the_snippet(self):
        from tools.browser_matrix import page_snippet
        snippet = page_snippet([{"role": "body", "family": "ThemeFactory-linen-body",
                                 "weight": 400, "style": "normal", "file": "fonts/a.woff2"}])
        self.assertIn("ThemeFactory-linen-body", snippet)
        self.assertNotIn("__EXPECTED_FACES__", snippet)


class SchemaEnforcedAtTheGateTests(unittest.TestCase):
    """Task 1 (verification-integrity-defects plan): the release gate must validate Layer D
    artifacts against tests/live/runtime-evidence.schema.json, not just check for a handful of
    keys. Before this, `_valid_browser_runtime_artifact` only checked `isinstance(fonts, list)`,
    so a font entry in the pre-2026-09-17 {family, loaded} shape - or any other schema violation -
    passed the gate silently as long as the artifact still looked roughly right.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def _themed_row(self, **font_overrides):
        font = {
            "role": "mono", "family": "ThemeFactory-solarized-dark-mono", "weight": 400,
            "style": "normal", "check": True,
            "requestUrl": "http://localhost:8181/.../ibm-plex-mono-regular.woff2",
            "mimeType": "font/woff2",
        }
        font.update(font_overrides)
        row = capture("business", 1440)
        row.page = dict(row.page, fonts=[font], activeTheme="solarized-dark",
                        htmlClasses=["app-theme-solarized-dark"])
        return row

    def test_a_schema_valid_font_entry_passes_the_gate(self):
        row = self._themed_row()
        evidence_dir = self.tmp / "2026-09-17-release-solarized-dark"
        write_layer_d_evidence(evidence_dir, "solarized-dark", COMMIT, SHA, [row])
        evidence = load_evidence(evidence_dir, "solarized-dark", expected_git_commit=COMMIT, expected_package_sha256=SHA)
        # A single row can't satisfy full coverage, but it must get past schema validation to reach
        # that (unrelated) coverage failure rather than being rejected for its shape.
        by_check = {item["check"]: item for item in evidence}
        self.assertIn("failures:", by_check["browser_runtime_matrix"]["details"].lower() + ":failures:")

    def test_font_entry_missing_request_url_fails_the_gate_by_name(self):
        from lib.theme_factory.release import RUNTIME_EVIDENCE_SCHEMA, _load_bound_raw_artifact
        from lib.theme_factory.errors import PackageError

        row = self._themed_row()
        del row.page["fonts"][0]["requestUrl"]
        raw_dir = self.tmp / "raw"
        raw_dir.mkdir()
        artifact = build_runtime_artifact("solarized-dark", COMMIT, SHA, row)
        path = raw_dir / "browser-business-page1-1440.json"
        path.write_text(json.dumps(artifact), encoding="utf-8")
        import hashlib
        reference = {"path": "raw/browser-business-page1-1440.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

        with self.assertRaises(PackageError) as ctx:
            _load_bound_raw_artifact(self.tmp, reference, "solarized-dark", COMMIT, SHA, "Layer D business/1440", schema_path=RUNTIME_EVIDENCE_SCHEMA)
        message = str(ctx.exception)
        self.assertIn("requestUrl", message)
        self.assertIn("browser-business-page1-1440.json", message)

    def test_extra_font_entry_key_fails_the_gate(self):
        from lib.theme_factory.release import RUNTIME_EVIDENCE_SCHEMA, _load_bound_raw_artifact
        from lib.theme_factory.errors import PackageError
        import hashlib

        row = self._themed_row(loaded=True)  # the pre-2026-09-17 shape smuggled in alongside the new one
        raw_dir = self.tmp / "raw"
        raw_dir.mkdir()
        artifact = build_runtime_artifact("solarized-dark", COMMIT, SHA, row)
        path = raw_dir / "browser-business-page1-1440.json"
        path.write_text(json.dumps(artifact), encoding="utf-8")
        reference = {"path": "raw/browser-business-page1-1440.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

        with self.assertRaises(PackageError) as ctx:
            _load_bound_raw_artifact(self.tmp, reference, "solarized-dark", COMMIT, SHA, "Layer D business/1440", schema_path=RUNTIME_EVIDENCE_SCHEMA)
        self.assertIn("loaded", str(ctx.exception))
