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
import zipfile

from lib.theme_factory.archive import build_package_from_root
from lib.theme_factory.release import load_evidence
from tools.live_matrix import (
    ApplicationTarget,
    OperationResult,
    PackageRef,
    run_layer_c_theme,
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

    def test_single_theme_runner_checks_cleanliness_before_work_and_evidence_write(self):
        apps = [
            ApplicationTarget("minimal", 9010, "MIN", "26.1.4"),
            ApplicationTarget("business", 9011, "BUS", "26.1.4"),
        ]
        package = PackageRef("linen", "1.0.0", self.tmp / "linen.zip", "b" * 64)
        secondary = PackageRef("solarized-dark", "1.0.0", self.tmp / "secondary.zip", "c" * 64)
        checks = []
        calls = []

        def lifecycle(connection, workspace, target, primary, secondary_path, work_dir, **kwargs):
            calls.append(target.consumer)
            return self.synthetic_operations()

        written = []

        def writer(evidence_dir, package_ref, commit, targets, operations):
            written.append((evidence_dir, package_ref, commit, targets, operations))
            return evidence_dir / "database_installation.json"

        result = run_layer_c_theme(
            "demo", "DEMO", apps, package, secondary, self.tmp / "work",
            self.tmp / "evidence", COMMIT,
            lifecycle_runner=lifecycle, evidence_writer=writer,
            clean_checker=lambda: checks.append("clean"),
        )
        self.assertEqual(sorted(calls), ["business", "minimal"])
        self.assertGreaterEqual(len(checks), 3)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(len(written), 1)


    def test_consumers_run_concurrently_and_evidence_keeps_target_order(self):
        import threading
        import time
        apps = [
            ApplicationTarget("minimal", 9010, "MIN", "26.1.4"),
            ApplicationTarget("business", 9011, "BUS", "26.1.4"),
        ]
        package = PackageRef("linen", "1.0.0", self.tmp / "linen.zip", "b" * 64)
        secondary = PackageRef("solarized-dark", "1.0.0", self.tmp / "secondary.zip", "c" * 64)
        both_running = threading.Barrier(2, timeout=5)  # serial execution can never pass this

        def lifecycle(connection, workspace, target, primary, secondary_path, work_dir, **kwargs):
            both_running.wait()
            if target.consumer == "minimal":
                time.sleep(0.2)  # business finishes first; merged evidence must still list minimal first
            operations = self.synthetic_operations()
            for result in operations.values():
                result.notes.append(f"ran {target.consumer}")
            return operations

        captured = []

        def writer(evidence_dir, package_ref, commit, targets, operations):
            captured.append(operations)
            return evidence_dir / "database_installation.json"

        result = run_layer_c_theme(
            "demo", "DEMO", apps, package, secondary, self.tmp / "work", self.tmp / "evidence", COMMIT,
            lifecycle_runner=lifecycle, evidence_writer=writer, clean_checker=lambda: None,
        )
        self.assertEqual(result.status, "PASS")
        self.assertEqual(captured[0]["install"].notes, ["minimal: ran minimal", "business: ran business"])
        self.assertEqual([step["consumer"] for step in captured[0]["install"].steps], ["minimal", "business"])


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


class PackageSourceBindingTests(unittest.TestCase):
    """A capture must refuse a package that is not what the current source builds.

    Each theme.css carries a `Source commit:` banner. Building before the final source
    commit (or from a dirty tree) stamps something other than last_source_commit(), and
    the mismatch is only discovered after the whole matrix has run - it cost an hour on
    2026-09-17. Catch it in milliseconds instead.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def _package(self, stamp):
        root = self.tmp / "pkg"
        root.mkdir(parents=True, exist_ok=True)
        (root / "theme.css").write_text(
            "/**\n * Theme: linen (Linen)\n * Version: 1.0.0\n"
            f" * Source commit: {stamp}\n */\n\nhtml{{}}\n", encoding="utf-8")
        archive = self.tmp / "linen-1.0.0.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.write(root / "theme.css", "linen-1.0.0/theme.css")
        return archive

    def test_reads_the_stamped_commit_from_a_zip(self):
        from lib.theme_factory.gitstate import package_source_commit
        self.assertEqual(package_source_commit(self._package("a" * 40)), "a" * 40)

    def test_a_dirty_build_is_reported_verbatim_so_it_can_be_refused(self):
        from lib.theme_factory.gitstate import package_source_commit
        self.assertEqual(package_source_commit(self._package("b" * 40 + "-dirty")), "b" * 40 + "-dirty")

    def test_package_built_from_a_dirty_tree_never_matches_source(self):
        from lib.theme_factory.gitstate import package_matches_source
        self.assertFalse(package_matches_source(self._package("c" * 40 + "-dirty"), "c" * 40))

    def test_package_built_at_another_commit_does_not_match(self):
        from lib.theme_factory.gitstate import package_matches_source
        self.assertFalse(package_matches_source(self._package("d" * 40), "e" * 40))

    def test_package_built_at_the_current_source_matches(self):
        from lib.theme_factory.gitstate import package_matches_source
        self.assertTrue(package_matches_source(self._package("f" * 40), "f" * 40))
