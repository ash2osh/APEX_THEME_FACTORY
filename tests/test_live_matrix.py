"""Tests for the live release-matrix driver (tools/live_matrix.py).

The driver itself talks to SQLcl through the installer CLIs; here it runs against the fake
`sql` (real-shape fixture) and its evidence output is checked against the release checker.
"""

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from lib.theme_factory.archive import build_package_from_root
from lib.theme_factory.release import load_evidence
from tools.live_matrix import (
    ApplicationTarget,
    OperationResult,
    PackageRef,
    run_lifecycle,
    write_layer_c_evidence,
)

COMMIT = "a" * 40


class LiveMatrixEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def synthetic_operations(self, status: str = "PASS") -> dict:
        return {
            name: OperationResult(operation=name, status=status, steps=[{"command": "install", "exitCode": 0, "status": "IMPORTED"}])
            for name in ("install", "reinstall", "coexistence", "switcherEnableDisable", "uninstall", "restore", "preserveUnrelated")
        }

    def test_written_layer_c_evidence_is_accepted_by_the_release_checker(self):
        apps = [
            ApplicationTarget(consumer="minimal", app_id=9010, alias="TF-CONSUMER-MINIMAL-9010", apex_version="26.1.4"),
            ApplicationTarget(consumer="business", app_id=9011, alias="TF-CONSUMER-BUSINESS-9011", apex_version="26.1.4"),
        ]
        package = PackageRef(theme="linen", version="1.0.0", zip_path=self.tmp / "linen.zip", sha256="b" * 64)
        evidence_dir = self.tmp / "2026-09-16-release-linen"
        write_layer_c_evidence(evidence_dir, package, COMMIT, apps, self.synthetic_operations(), captured_at="2026-09-16T00:00:00Z")

        evidence = load_evidence(evidence_dir, "linen", expected_git_commit=COMMIT, expected_package_sha256="b" * 64)
        by_check = {item["check"]: item for item in evidence}
        self.assertEqual(by_check["database_installation"]["status"], "PASS")
        manifest = json.loads((evidence_dir / "evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["theme"], "linen")
        self.assertTrue((evidence_dir / "raw").is_dir())

    def test_failed_operation_marks_layer_c_failed_with_failures_listed(self):
        apps = [
            ApplicationTarget(consumer="minimal", app_id=9010, alias="A", apex_version="26.1.4"),
            ApplicationTarget(consumer="business", app_id=9011, alias="B", apex_version="26.1.4"),
        ]
        package = PackageRef(theme="linen", version="1.0.0", zip_path=self.tmp / "linen.zip", sha256="b" * 64)
        operations = self.synthetic_operations()
        operations["uninstall"] = OperationResult(operation="uninstall", status="FAIL", steps=[{"command": "uninstall", "exitCode": 6, "status": "IMPORTED_POSTCHECK_FAILED"}])
        evidence_dir = self.tmp / "2026-09-16-release-linen"
        write_layer_c_evidence(evidence_dir, package, COMMIT, apps, operations, captured_at="2026-09-16T00:00:00Z")
        evidence = load_evidence(evidence_dir, "linen", expected_git_commit=COMMIT, expected_package_sha256="b" * 64)
        by_check = {item["check"]: item for item in evidence}
        self.assertEqual(by_check["database_installation"]["status"], "FAIL")
        summary = json.loads((evidence_dir / "database_installation.json").read_text(encoding="utf-8"))
        self.assertIn("uninstall", " ".join(summary["results"]["failures"]))


class LiveMatrixLifecycleAgainstFakeSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.shared_tmp = Path(tempfile.mkdtemp())
        os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
        cls.zips = {}
        for name in ("linen", "solarized-dark"):
            cls.zips[name] = build_package_from_root(cls.repo_root, cls.repo_root / f"sample-themes/{name}", cls.shared_tmp / "dist")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.shared_tmp, ignore_errors=True)

    def test_lifecycle_passes_every_operation_on_the_real_shape_fixture(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        env = os.environ.copy()
        env["PATH"] = f"{(self.repo_root / 'tests/fixtures/bin').resolve()}:{env['PATH']}"
        env["FAKE_SQL_MODE"] = "success"
        env["FAKE_SQL_FIXTURE"] = "real-shape"
        env["FAKE_SQL_STATE_FILE"] = str(tmp / "state.txt")
        target = ApplicationTarget(consumer="business", app_id=314, alias="FIXTURE_APP", apex_version="26.1.0")
        results = run_lifecycle(
            connection="demo", workspace="DEMO", target=target,
            primary=self.zips["linen"], secondary=self.zips["solarized-dark"],
            work_dir=tmp / "work", env=env, with_switcher=True,
        )
        statuses = {name: result.status for name, result in results.items()}
        self.assertEqual(set(statuses), {"install", "reinstall", "coexistence", "switcherEnableDisable", "uninstall", "restore", "preserveUnrelated"})
        self.assertEqual(set(statuses.values()), {"PASS"}, statuses)


if __name__ == "__main__":
    unittest.main()
