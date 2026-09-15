import unittest
from pathlib import Path

from lib.theme_factory.release import (
    calculate_layer_statuses,
    release_verdict,
    render_release_markdown,
)


class ReleaseVerdictTests(unittest.TestCase):
    def test_unverified_required_layer_blocks_verified(self):
        self.assertEqual(
            release_verdict({"A": "PASS", "B": "PASS", "C": "PASS", "D": "UNVERIFIED", "E": "PASS"}),
            "UNVERIFIED",
        )

    def test_failure_wins(self):
        self.assertEqual(
            release_verdict({"A": "PASS", "B": "FAIL", "C": "UNVERIFIED", "D": "PASS", "E": "PASS"}),
            "FAIL",
        )

    def test_all_pass_is_verified(self):
        self.assertEqual(
            release_verdict({"A": "PASS", "B": "PASS", "C": "PASS", "D": "PASS", "E": "PASS"}),
            "VERIFIED",
        )

    def test_missing_required_layer_is_unverified(self):
        self.assertEqual(
            release_verdict({"A": "PASS", "B": "PASS"}),
            "UNVERIFIED",
        )

    def test_optional_not_applicable_allowed(self):
        # Even with optional NOT_APPLICABLE checks, if required layers are PASS, verdict is VERIFIED
        self.assertEqual(
            release_verdict({"A": "PASS", "B": "PASS", "C": "PASS", "D": "PASS", "E": "PASS", "OPTIONAL": "NOT_APPLICABLE"}),
            "VERIFIED",
        )

    def test_render_release_markdown_contains_sections(self):
        metadata = {
            "theme": "linen",
            "version": "1.0.0",
            "git_commit": "abcdef1",
            "is_dirty": False,
            "apex_version": "26.1.4",
            "sqlcl_version": "26.1.0",
            "chrome_version": "128.0",
            "checksum": "1234567890abcdef",
        }
        evidence = [
            {"layer": "A", "check": "offline_tests", "path": "tests/run-offline.sh", "status": "PASS", "details": "All offline checks passed"},
            {"layer": "B", "check": "parity", "path": "tools/runtime_parity.py", "status": "PASS", "details": "Database matches source"},
            {"layer": "C", "check": "runtime", "path": "tests/live/evidence/runtime.json", "status": "PASS", "details": "Runtime elements verified"},
            {"layer": "D", "check": "consumer", "path": "tests/live/evidence/consumer.json", "status": "PASS", "details": "Consumer app verified"},
            {"layer": "E", "check": "evaluation", "path": ".agents/evaluations/04.md", "status": "PASS", "details": "Evaluations passed"},
        ]
        report = render_release_markdown(metadata, evidence, "VERIFIED")
        self.assertIn("# Release Report: linen v1.0.0", report)
        self.assertIn("VERIFIED", report)
        self.assertIn("Layer A", report)
        self.assertIn("Layer E", report)


if __name__ == "__main__":
    unittest.main()
