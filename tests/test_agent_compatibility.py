import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lib.theme_factory.agent_compatibility import (
    validate_agent_behavior_artifact,
)
from lib.theme_factory.errors import PackageError


class AgentCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def write_fixture(
        self,
        *,
        runtimes=("codex", "claude", "antigravity"),
        runtime_statuses=None,
        scenarios=("04", "05", "09", "14"),
        instruction_commit="a" * 40,
        include_package_sha=False,
    ) -> Path:
        raw = self.root / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        runtime_statuses = runtime_statuses or {}

        def write_raw(name, document):
            path = raw / name
            path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
            return {"path": str(path.relative_to(self.root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

        runtime_refs = {}
        for runtime in runtimes:
            runtime_refs[runtime] = write_raw(
                f"runtime-{runtime}.json",
                {
                    "schemaVersion": 1,
                    "evidenceType": "agent-runtime",
                    "runtime": runtime,
                    "status": runtime_statuses.get(runtime, "PASS"),
                    "instructionCommit": instruction_commit,
                    "capturedAt": "2026-09-20T00:00:00Z",
                },
            )

        scenario_refs = {}
        for scenario in scenarios:
            scenario_refs[scenario] = write_raw(
                f"scenario-{scenario}.json",
                {
                    "schemaVersion": 1,
                    "evidenceType": "agent-scenario",
                    "scenario": scenario,
                    "status": "PASS",
                    "instructionCommit": instruction_commit,
                    "capturedAt": "2026-09-20T00:00:00Z",
                },
            )

        document = {
            "schemaVersion": 1,
            "evidenceType": "agent-compatibility",
            "instructionCommit": instruction_commit,
            "capturedAt": "2026-09-20T00:00:00Z",
            "runtimes": runtime_refs,
            "scenarios": scenario_refs,
            "pendingFindings": 0,
        }
        if include_package_sha:
            document["packageSha256"] = "b" * 64
        path = self.root / "compatibility.json"
        path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
        return path

    def test_pass_requires_all_supported_runtimes(self):
        path = self.write_fixture()
        result = validate_agent_behavior_artifact(path, path.parent, "a" * 40)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.runtimes, ("antigravity", "claude", "codex"))

    def test_environmental_unavailability_is_unverified(self):
        path = self.write_fixture(runtime_statuses={"antigravity": "UNVERIFIED"})
        result = validate_agent_behavior_artifact(path, path.parent, "a" * 40)
        self.assertEqual(result.status, "UNVERIFIED")

    def test_instruction_change_invalidates_evidence(self):
        path = self.write_fixture(instruction_commit="a" * 40)
        result = validate_agent_behavior_artifact(path, path.parent, "b" * 40)
        self.assertEqual(result.status, "UNVERIFIED")

    def test_theme_package_sha_is_not_part_of_agent_identity(self):
        path = self.write_fixture(include_package_sha=False)
        self.assertNotIn("packageSha256", json.loads(path.read_text()))
        self.assertEqual(
            validate_agent_behavior_artifact(path, path.parent, "a" * 40).status,
            "PASS",
        )

    def test_scenario_11_is_not_required_by_project_compatibility(self):
        path = self.write_fixture(scenarios=("04", "05", "09", "14"))
        result = validate_agent_behavior_artifact(path, path.parent, "a" * 40)
        self.assertEqual(result.scenarios, ("04", "05", "09", "14"))
        self.assertEqual(result.status, "PASS")

    def test_behavioral_failure_is_fail(self):
        path = self.write_fixture(runtime_statuses={"claude": "FAIL"})
        result = validate_agent_behavior_artifact(path, path.parent, "a" * 40)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(result.failures)

    def test_path_traversal_is_rejected(self):
        path = self.write_fixture()
        document = json.loads(path.read_text())
        document["runtimes"]["codex"]["path"] = "../outside.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaises(PackageError):
            validate_agent_behavior_artifact(path, path.parent, "a" * 40)

    def test_digest_mismatch_is_rejected(self):
        path = self.write_fixture()
        document = json.loads(path.read_text())
        document["runtimes"]["codex"]["sha256"] = "0" * 64
        path.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(PackageError, "digest"):
            validate_agent_behavior_artifact(path, path.parent, "a" * 40)


if __name__ == "__main__":
    unittest.main()
