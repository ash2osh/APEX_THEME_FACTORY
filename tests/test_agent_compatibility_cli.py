import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TOOL = Path("tools/agent_compatibility_report.py")


class AgentCompatibilityCliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def write_fixture(self, *, missing_runtime=None, failing_runtime=None):
        evidence = self.root / "evidence" / "2026-09-20"
        raw = evidence / "raw"
        raw.mkdir(parents=True)
        instruction_commit = "a" * 40
        runtimes = {}
        for runtime in ("codex", "claude", "antigravity"):
            if runtime == missing_runtime:
                continue
            path = raw / f"runtime-{runtime}.json"
            path.write_text(json.dumps({
                "schemaVersion": 1,
                "evidenceType": "agent-runtime",
                "runtime": runtime,
                "status": "FAIL" if runtime == failing_runtime else "PASS",
                "instructionCommit": instruction_commit,
                "capturedAt": "2026-09-20T00:00:00Z",
            }, sort_keys=True), encoding="utf-8")
            runtimes[runtime] = {
                "path": str(path.relative_to(evidence)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        scenarios = {}
        for scenario in ("04", "05", "09", "14"):
            path = raw / f"scenario-{scenario}.json"
            path.write_text(json.dumps({
                "schemaVersion": 1,
                "evidenceType": "agent-scenario",
                "scenario": scenario,
                "status": "PASS",
                "instructionCommit": instruction_commit,
                "capturedAt": "2026-09-20T00:00:00Z",
            }, sort_keys=True), encoding="utf-8")
            scenarios[scenario] = {
                "path": str(path.relative_to(evidence)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        artifact = evidence / "compatibility.json"
        artifact.write_text(json.dumps({
            "schemaVersion": 1,
            "evidenceType": "agent-compatibility",
            "instructionCommit": instruction_commit,
            "capturedAt": "2026-09-20T00:00:00Z",
            "runtimes": runtimes,
            "scenarios": scenarios,
            "pendingFindings": 0,
        }, sort_keys=True), encoding="utf-8")
        return evidence.parent, artifact

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(TOOL), *map(str, args)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_pass_renders_one_row_per_runtime(self):
        evidence_root, _ = self.write_fixture()
        documentation = self.root / "AGENT_COMPATIBILITY.md"
        documentation.write_text("# Compatibility\n\nHandwritten context.\n", encoding="utf-8")
        result = self.run_cli(
            "--evidence-root", evidence_root,
            "--documentation", documentation,
            "--expected-instruction-commit", "a" * 40,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = documentation.read_text(encoding="utf-8")
        self.assertEqual(rendered.count("| codex |"), 1)
        self.assertEqual(rendered.count("| claude |"), 1)
        self.assertEqual(rendered.count("| antigravity |"), 1)
        self.assertNotIn("packageSha256", rendered)
        self.assertNotIn("theme:", rendered)

    def test_missing_runtime_is_unverified(self):
        evidence_root, _ = self.write_fixture(missing_runtime="antigravity")
        documentation = self.root / "AGENT_COMPATIBILITY.md"
        documentation.write_text("# Compatibility\n", encoding="utf-8")
        result = self.run_cli(
            "--evidence-root", evidence_root,
            "--documentation", documentation,
            "--expected-instruction-commit", "a" * 40,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("UNVERIFIED", documentation.read_text(encoding="utf-8"))

    def test_behavioral_failure_exits_one(self):
        evidence_root, _ = self.write_fixture(failing_runtime="claude")
        documentation = self.root / "AGENT_COMPATIBILITY.md"
        documentation.write_text("# Compatibility\n", encoding="utf-8")
        result = self.run_cli(
            "--evidence-root", evidence_root,
            "--documentation", documentation,
            "--expected-instruction-commit", "a" * 40,
        )
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_check_reports_drift_without_writing(self):
        evidence_root, _ = self.write_fixture()
        documentation = self.root / "AGENT_COMPATIBILITY.md"
        documentation.write_text("# Compatibility\n", encoding="utf-8")
        generated = self.run_cli(
            "--evidence-root", evidence_root,
            "--documentation", documentation,
            "--expected-instruction-commit", "a" * 40,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        documentation.write_text(
            documentation.read_text(encoding="utf-8").replace("| codex | `PASS` |", "| codex | `FAIL` |"),
            encoding="utf-8",
        )
        before = documentation.read_bytes()
        result = self.run_cli(
            "--evidence-root", evidence_root,
            "--documentation", documentation,
            "--expected-instruction-commit", "a" * 40,
            "--check",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("drift", result.stderr.lower())
        self.assertEqual(documentation.read_bytes(), before)

    def test_migrate_legacy_artifact_is_standalone_and_omits_scenario_11(self):
        legacy = Path(".agents/evaluations/runtime/2026-09-17-release-linen/agent_behavior_matrix.json")
        output = self.root / "agent-compatibility" / "2026-09-17" / "compatibility.json"
        result = self.run_cli("--migrate-legacy", legacy, "--output", output)
        self.assertEqual(result.returncode, 2, result.stderr)
        document = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(document["evidenceType"], "agent-compatibility")
        self.assertEqual(set(document["runtimes"]), {"codex", "claude", "antigravity"})
        self.assertEqual(set(document["scenarios"]), {"04", "05", "09", "14"})
        self.assertNotIn("theme", document)
        self.assertNotIn("packageSha256", document)
        self.assertNotIn("scenario11", document)


if __name__ == "__main__":
    unittest.main()
