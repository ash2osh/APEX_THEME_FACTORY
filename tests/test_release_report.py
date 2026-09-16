import unittest
from pathlib import Path

from lib.theme_factory.release import (
    calculate_layer_statuses,
    load_evidence,
    release_verdict,
    render_release_markdown,
)
from lib.theme_factory.errors import PackageError
import json
import hashlib
import tempfile
from unittest.mock import patch


class ReleaseVerdictTests(unittest.TestCase):
    def test_git_command_failure_is_unverified(self):
        from lib.theme_factory.release import read_git_state

        failed = type("Result", (), {"returncode": 1, "stdout": ""})()
        with patch("lib.theme_factory.release.subprocess.run", return_value=failed):
            commit, dirty = read_git_state()
        self.assertIsNone(commit)
        self.assertIsNone(dirty)
        self.assertEqual(
            release_verdict({"A": "UNVERIFIED", "B": "PASS", "C": "PASS", "D": "PASS", "E": "PASS"}),
            "UNVERIFIED",
        )
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

    def test_required_layers_cannot_be_not_applicable(self):
        self.assertEqual(
            release_verdict({name: "NOT_APPLICABLE" for name in "ABCDE"}),
            "UNVERIFIED",
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
        self.assertIn("Package artifact", report)
        self.assertIn("Database installation", report)

    def test_legacy_arbitrary_evidence_list_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.json"
            path.write_text(json.dumps([{"layer": "E", "status": "PASS"}]), encoding="utf-8")
            with self.assertRaises(PackageError):
                load_evidence(Path(temp), "linen")

    def test_pass_claim_requires_digest_bound_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.json"
            path.write_text(json.dumps({
                "schemaVersion": 1,
                "theme": "linen",
                "checks": [{
                    "layer": "D", "check": "runtime", "status": "PASS",
                    "artifact": "missing.json", "artifactSha256": "0" * 64,
                    "details": "claimed",
                }],
            }), encoding="utf-8")
            with self.assertRaises(PackageError):
                load_evidence(Path(temp), "linen")

    def test_arbitrary_digest_bound_bytes_are_not_runtime_evidence(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "proof.txt"
            artifact.write_text("claimed", encoding="utf-8")
            (root / "evidence.json").write_text(json.dumps({
                "schemaVersion": 1, "theme": "linen", "checks": [{
                    "layer": "D", "check": "browser_runtime_matrix", "status": "PASS",
                    "artifact": "proof.txt",
                    "artifactSha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    "details": "claimed",
                }],
            }), encoding="utf-8")
            with self.assertRaises(PackageError):
                load_evidence(root, "linen")

    def test_evidence_for_another_theme_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.json"
            path.write_text(json.dumps({"schemaVersion": 1, "theme": "other", "checks": []}), encoding="utf-8")
            with self.assertRaises(PackageError):
                load_evidence(Path(temp), "linen")

    def test_claim_must_match_release_commit_and_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "claim.json"
            artifact.write_text(json.dumps({
                "schemaVersion": 1,
                "theme": "linen",
                "layer": "C",
                "check": "database_installation",
                "status": "FAIL",
                "capturedAt": "2026-09-16T00:00:00Z",
                "gitCommit": "a" * 40,
                "packageSha256": "b" * 64,
                "results": {"failures": ["install failed"]},
            }), encoding="utf-8")
            (root / "evidence.json").write_text(json.dumps({
                "schemaVersion": 1,
                "theme": "linen",
                "checks": [{
                    "layer": "C",
                    "check": "database_installation",
                    "status": "FAIL",
                    "artifact": "claim.json",
                    "artifactSha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                }],
            }), encoding="utf-8")
            with self.assertRaisesRegex(PackageError, "Git commit"):
                load_evidence(root, "linen", "c" * 40, "b" * 64)
            with self.assertRaisesRegex(PackageError, "different package"):
                load_evidence(root, "linen", "a" * 40, "d" * 64)

    def test_layer_c_summary_without_digest_bound_raw_artifacts_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "database-summary.json"
            operations = {
                name: {"path": f"raw/{name}.json", "sha256": "0" * 64}
                for name in (
                    "install", "reinstall", "coexistence", "switcherEnableDisable",
                    "uninstall", "restore", "preserveUnrelated",
                )
            }
            artifact.write_text(json.dumps({
                "schemaVersion": 1,
                "theme": "linen",
                "layer": "C",
                "check": "database_installation",
                "status": "PASS",
                "capturedAt": "2026-09-16T00:00:00Z",
                "gitCommit": "a" * 40,
                "packageSha256": "b" * 64,
                "results": {
                    "applications": [
                        {"appId": "201", "appAlias": "minimal", "evidence": {"path": "raw/minimal.json", "sha256": "0" * 64}},
                        {"appId": "202", "appAlias": "business", "evidence": {"path": "raw/business.json", "sha256": "0" * 64}},
                    ],
                    "operationEvidence": operations,
                },
            }), encoding="utf-8")
            (root / "evidence.json").write_text(json.dumps({
                "schemaVersion": 1,
                "theme": "linen",
                "checks": [{
                    "layer": "C",
                    "check": "database_installation",
                    "status": "PASS",
                    "artifact": artifact.name,
                    "artifactSha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                }],
            }), encoding="utf-8")
            with self.assertRaisesRegex(PackageError, "does not reference"):
                load_evidence(root, "linen", "a" * 40, "b" * 64)


if __name__ == "__main__":
    unittest.main()


class ReleaseEvidenceDiscoveryTests(unittest.TestCase):
    """The checker must find per-theme evidence under the runtime evidence root and ignore
    unrelated runtime artifacts (parity reports carry a `checks` key of their own)."""

    def test_per_theme_subdirectory_is_discovered_from_the_evidence_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "20260915T163631Z-parity.json").write_text(
                json.dumps({"timestamp": "x", "workspace": "DEMO", "appId": 102, "verdict": "PASS", "checks": []}),
                encoding="utf-8",
            )
            theme_dir = root / "2026-09-15-release-linen"
            theme_dir.mkdir()
            (theme_dir / "evidence.json").write_text(json.dumps({
                "schemaVersion": 1, "theme": "linen",
                "checks": [{"layer": "C", "check": "database_installation", "status": "UNVERIFIED", "artifact": "", "details": "none yet"}],
            }), encoding="utf-8")
            evidence = load_evidence(root, "linen")
        by_check = {item["check"]: item for item in evidence}
        self.assertEqual(by_check["database_installation"]["details"], "none yet")
        self.assertEqual(by_check["browser_runtime_matrix"]["status"], "UNVERIFIED")

    def test_release_cli_reports_package_errors_without_traceback(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "broken.json").write_text(json.dumps({"schemaVersion": 2, "theme": "linen", "checks": []}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "lib.theme_factory.release", "--theme", "linen", "--evidence-dir", str(root)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("schemaVersion", result.stderr)
