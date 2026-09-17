"""Tests for the browser-matrix evidence builder (tools/browser_matrix.py)."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

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
        "fonts": [{"family": "Font APEX", "loaded": True}],
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
