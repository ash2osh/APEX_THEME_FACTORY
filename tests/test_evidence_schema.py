"""Tests for lib/theme_factory/evidence_schema.py.

tests/live/runtime-evidence.schema.json documents the Layer D artifact contract, but until
2026-09-17 nothing read it: the emitter and the release gate agreed with each other by hand,
which is a coincidence waiting to lapse (it already had — see pitfalls.md 5.x / plan Task 1).
This is the validator that makes the schema an enforced contract instead of a comment.
"""

import copy
import json
from pathlib import Path
import unittest

SCHEMA_PATH = Path(__file__).resolve().parent / "live" / "runtime-evidence.schema.json"


def _good_artifact() -> dict:
    return {
        "schemaVersion": 1,
        "evidenceContractVersion": 2,
        "evidenceType": "browser-runtime",
        "theme": "solarized-dark",
        "gitCommit": "c" * 40,
        "packageSha256": "d" * 64,
        "capturedAt": "2026-09-17T00:00:00Z",
        "consumer": "business",
        "viewportWidth": 1440,
        "url": "http://localhost:8181/ords/r/demo/tf-consumer-business-9011/home",
        "appId": "9011",
        "appAlias": "TF-CONSUMER-BUSINESS-9011",
        "pageId": "1",
        "apexVersion": "26.1.4",
        "browserVersion": "Chrome/140.0.7339.81",
        "bodyClasses": ["t-PageBody"],
        "htmlClasses": ["app-theme-solarized-dark"],
        "cssUrls": ["theme.css"],
        "javascriptUrls": ["theme-factory-runtime.js"],
        "loadedUrls": ["theme.css", "theme-factory-runtime.js"],
        "windowApp": None,
        "windowAlpine": None,
        "activeTheme": "solarized-dark",
        "registry": {"defaultTheme": "solarized-dark"},
        "switcherAvailable": True,
        "consoleErrors": [],
        "failedRequests": [],
        "declaredFaceCount": 1,
        "fonts": [{
            "role": "mono", "family": "ThemeFactory-solarized-dark-mono", "weight": 400,
            "style": "normal", "check": True,
            "requestUrl": "http://localhost:8181/.../ibm-plex-mono-regular.woff2",
            "mimeType": "font/woff2",
        }],
        "fontApexFamilyBefore": "\"Font APEX Small\"",
        "fontApexFamilyAfter": "\"Font APEX Small\"",
        "fontsVerified": True,
        "accessibilityVerified": True,
        "persistenceVerified": True,
        "notes": [],
    }


class EvidenceSchemaTests(unittest.TestCase):
    def test_known_good_artifact_validates(self):
        from lib.theme_factory.evidence_schema import validate
        errors = validate(_good_artifact(), SCHEMA_PATH)
        self.assertEqual(errors, [])

    def test_font_entry_missing_request_url_fails(self):
        from lib.theme_factory.evidence_schema import validate
        artifact = _good_artifact()
        del artifact["fonts"][0]["requestUrl"]
        errors = validate(artifact, SCHEMA_PATH)
        self.assertTrue(errors)
        self.assertTrue(any("requestUrl" in e for e in errors), errors)

    def test_extra_top_level_key_fails(self):
        from lib.theme_factory.evidence_schema import validate
        artifact = _good_artifact()
        artifact["unexpectedField"] = "surprise"
        errors = validate(artifact, SCHEMA_PATH)
        self.assertTrue(errors)
        self.assertTrue(any("unexpectedField" in e for e in errors), errors)

    def test_extra_font_entry_key_fails(self):
        from lib.theme_factory.evidence_schema import validate
        artifact = _good_artifact()
        artifact["fonts"][0]["loaded"] = True  # the pre-2026-09-17 shape, must not sneak back in
        errors = validate(artifact, SCHEMA_PATH)
        self.assertTrue(errors)
        self.assertTrue(any("loaded" in e for e in errors), errors)

    def test_out_of_range_viewport_width_fails(self):
        from lib.theme_factory.evidence_schema import validate
        artifact = _good_artifact()
        artifact["viewportWidth"] = 1441
        errors = validate(artifact, SCHEMA_PATH)
        self.assertTrue(errors)
        self.assertTrue(any("viewportWidth" in e or "1441" in e for e in errors), errors)

    def test_missing_top_level_required_field_fails(self):
        from lib.theme_factory.evidence_schema import validate
        artifact = _good_artifact()
        del artifact["gitCommit"]
        errors = validate(artifact, SCHEMA_PATH)
        self.assertTrue(any("gitCommit" in e for e in errors), errors)

    def test_bad_git_commit_pattern_fails(self):
        from lib.theme_factory.evidence_schema import validate
        artifact = _good_artifact()
        artifact["gitCommit"] = "not-a-sha"
        errors = validate(artifact, SCHEMA_PATH)
        self.assertTrue(errors)

    def test_fontless_theme_with_empty_fonts_array_validates(self):
        from lib.theme_factory.evidence_schema import validate
        artifact = _good_artifact()
        artifact["theme"] = "linen"
        artifact["activeTheme"] = "linen"
        artifact["htmlClasses"] = ["app-theme-linen"]
        artifact["fonts"] = []
        artifact["declaredFaceCount"] = 0
        errors = validate(artifact, SCHEMA_PATH)
        self.assertEqual(errors, [])

    def test_unsupported_schema_keyword_raises_rather_than_being_ignored(self):
        # An ignored keyword is exactly how the original defect started: the schema documented a
        # contract nothing enforced. The validator must fail loudly on a keyword it doesn't implement,
        # not silently accept everything under it.
        from lib.theme_factory.evidence_schema import validate
        with self.assertRaises(ValueError):
            validate({"x": 1}, None, schema={"type": "object", "propertyNames": {"minLength": 1}})

    def test_every_committed_layer_d_artifact_validates(self):
        """Current-contract committed artifacts validate; obsolete rows are intentionally misses."""
        from lib.theme_factory.evidence_schema import validate
        root = Path(__file__).resolve().parent.parent / ".agents" / "evaluations" / "runtime"
        artifacts = sorted(root.glob("*/raw/browser-*.json"))
        self.assertTrue(artifacts, "expected at least one committed Layer D artifact to check")
        current = 0
        obsolete = 0
        for path in artifacts:
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("evidenceContractVersion") != 2:
                obsolete += 1
                errors = validate(document, SCHEMA_PATH)
                self.assertTrue(any("evidenceContractVersion" in error for error in errors), errors)
                continue
            current += 1
            errors = validate(document, SCHEMA_PATH)
            self.assertEqual(errors, [], f"{path} does not satisfy the runtime-evidence schema: {errors}")
        self.assertGreater(obsolete + current, 0)


if __name__ == "__main__":
    unittest.main()
