import tempfile
import unittest
import contextlib
import io
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from lib.theme_factory.evidence_cache import EvidenceIdentity
from tools.release_batch import (
    BrowserRowPlan,
    find_obsolete_evidence,
    prune_evidence,
    run_layer_c_batch,
    run_layer_d_batch,
)
from lib.theme_factory.cli import run_cli


class FakeChromeClient:
    def __init__(self, fail_after=None):
        self.calls = []
        self.fail_after = fail_after

    def capture(self, row):
        if self.fail_after is not None and len(self.calls) >= self.fail_after:
            raise RuntimeError("interrupted")
        self.calls.append(row.key)
        return {"status": "PASS", "row": row.key}


class ReleaseBatchResumeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.identity = EvidenceIdentity(
            source_commit="a" * 40,
            package_sha256="b" * 64,
            apex_version="26.1.4",
            browser_version="Chrome/140.0.7339.81",
            consumer="business",
            page="1",
            viewport=1440,
            scenario="browser-runtime",
        )
        self.rows = tuple(
            BrowserRowPlan("linen", consumer, page, width, f"http://local/{consumer}/{page}")
            for consumer, page in (("minimal", "1"), ("business", "1"))
            for width in (1440, 375)
        )

    def tearDown(self):
        self.temporary.cleanup()

    def identity_for(self, row, package_sha=None):
        return replace(
            self.identity,
            package_sha256=package_sha or self.identity.package_sha256,
            consumer=row.consumer,
            page=row.page,
            viewport=row.viewport,
        )

    def test_resume_skips_only_the_two_exact_completed_rows(self):
        interrupted = FakeChromeClient(fail_after=2)
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            run_layer_d_batch(
                self.rows, self.root, resume=True,
                identity_for=self.identity_for, row_runner=interrupted.capture,
            )
        self.assertEqual(interrupted.calls, [row.key for row in self.rows[:2]])

        resumed = FakeChromeClient()
        report = run_layer_d_batch(
            self.rows, self.root, resume=True,
            identity_for=self.identity_for, row_runner=resumed.capture,
        )
        self.assertEqual(resumed.calls, [row.key for row in self.rows[2:]])
        self.assertEqual(report.skipped, 2)
        self.assertEqual(report.completed, 2)
        self.assertEqual(len(report.artifacts), 4)

    def test_package_sha_change_reruns_every_row(self):
        first = FakeChromeClient()
        run_layer_d_batch(
            self.rows, self.root, resume=True,
            identity_for=self.identity_for, row_runner=first.capture,
        )
        changed = FakeChromeClient()
        report = run_layer_d_batch(
            self.rows, self.root, resume=True,
            identity_for=lambda row: self.identity_for(row, package_sha="c" * 64),
            row_runner=changed.capture,
        )
        self.assertEqual(changed.calls, [row.key for row in self.rows])
        self.assertEqual(report.skipped, 0)


class ReleaseBatchLayerCTests(unittest.TestCase):
    def test_layer_c_restores_baselines_around_every_theme(self):
        events = []
        report = run_layer_c_batch(
            ["linen", "citrus-pop"],
            restore_baselines=lambda: events.append("restore"),
            theme_runner=lambda theme: events.append(theme) or True,
        )
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.completed, ("linen", "citrus-pop"))
        self.assertEqual(events, ["restore", "linen", "restore", "restore", "citrus-pop", "restore"])

    def test_layer_c_failure_stops_before_the_next_theme(self):
        events = []

        def runner(theme):
            events.append(theme)
            return False

        report = run_layer_c_batch(["linen", "citrus-pop"], restore_baselines=lambda: events.append("restore"),
                                   theme_runner=runner)
        self.assertEqual((report.status, report.completed, report.failures), ("FAIL", (), ("linen",)))
        self.assertEqual(events, ["restore", "linen", "restore"])

    def test_layer_c_restores_even_when_a_theme_run_raises(self):
        events = []

        def runner(theme):
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            run_layer_c_batch(["linen"], restore_baselines=lambda: events.append("restore"), theme_runner=runner)
        self.assertEqual(events, ["restore", "restore"])


    def test_parallel_restore_runs_every_target_concurrently(self):
        import threading
        from tools.release_batch import run_in_parallel
        both_running = threading.Barrier(2, timeout=5)
        seen = []

        def restore(target):
            both_running.wait()
            seen.append(target)

        run_in_parallel(restore, ["minimal", "business"])
        self.assertEqual(sorted(seen), ["business", "minimal"])

    def test_parallel_restore_surfaces_the_first_failure(self):
        from tools.release_batch import run_in_parallel

        def restore(target):
            if target == "business":
                raise RuntimeError("import failed")

        with self.assertRaises(RuntimeError):
            run_in_parallel(restore, ["minimal", "business"])

    def test_pristine_consumer_baseline_is_accepted(self):
        from tools.release_batch import assert_pristine_baseline
        assert_pristine_baseline("minimal", 9010, Path("tests/fixtures/apexlang/real-shape"))

    def test_consumer_baseline_with_leftover_packages_is_refused_before_any_work(self):
        import shutil
        from lib.theme_factory.apexlang import apply_patch, plan_install
        from lib.theme_factory.errors import PackageError
        from tools.release_batch import assert_pristine_baseline
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "app"
            shutil.copytree("tests/fixtures/apexlang/real-shape", app)
            apply_patch(plan_install(app, Path("tests/fixtures/packages/valid-basic"), "preserve"))
            with self.assertRaises(PackageError) as context:
                assert_pristine_baseline("minimal", 9010, app)
        self.assertIn("valid-basic", str(context.exception))
        self.assertIn("tests/live/consumer-apps/minimal", str(context.exception))

class ObsoleteEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / ".agents/evaluations/runtime"
        self.root.mkdir(parents=True)

    def tearDown(self):
        self.temporary.cleanup()

    def test_report_obsolete_and_prune_are_confined_to_runtime_root(self):
        for name in ("2026-01-01-release-linen", "2026-01-02-release-linen", "2026-01-03-release-linen"):
            path = self.root / name
            path.mkdir()
            (path / "identity.json").write_text("{}", encoding="utf-8")
        obsolete = find_obsolete_evidence(self.root, lambda _: False)
        self.assertEqual(len(obsolete), 3)
        planned = prune_evidence(self.root, keep_latest=2, apply=False)
        self.assertEqual(len(planned), 1)
        self.assertTrue(planned[0].exists())
        deleted = prune_evidence(self.root, keep_latest=2, apply=True)
        self.assertEqual(deleted, planned)
        self.assertFalse(deleted[0].exists())

    def test_prune_rejects_a_symlink_escape(self):
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        link = self.root / "2026-01-01-release-linen"
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "beneath"):
            prune_evidence(self.root, keep_latest=0, apply=True)
        self.assertTrue(outside.exists())


class ReleaseBatchCliTests(unittest.TestCase):
    @staticmethod
    def invoke(*arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = run_cli(list(arguments))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_release_batch_is_dry_run_without_apply(self):
        with tempfile.TemporaryDirectory() as temp:
            code, stdout, stderr = self.invoke(
                "release-batch", "--themes", "linen,cobalt-press",
                "--secondary", "solarized-dark.zip", "--evidence-root", temp,
                "--resume", "--report-obsolete",
            )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["status"], "DRY_RUN")

    def test_report_obsolete_uses_identity_validation_instead_of_listing_every_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp) / "current-release-linen"
            evidence.mkdir()
            with patch("tools.release_batch.evidence_directory_current", return_value=True):
                code, stdout, _ = self.invoke(
                    "release-batch", "--themes", "linen",
                    "--secondary", "solarized-dark.zip", "--evidence-root", temp,
                    "--report-obsolete",
                )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["obsolete"], [])

    def test_release_batch_apply_requires_explicit_consumer_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            code, _, stderr = self.invoke(
                "release-batch", "--themes", "linen,cobalt-press",
                "--secondary", "solarized-dark.zip", "--evidence-root", temp,
                "--apply",
            )
        self.assertEqual(code, 2)
        self.assertIn("--minimal-id", stderr)

    def test_evidence_prune_defaults_to_dry_run_and_apply_deletes(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            root = repo / ".agents/evaluations/runtime"
            for day in ("01", "02", "03"):
                (root / f"2026-01-{day}-release-linen").mkdir(parents=True)
            dry = self.invoke(
                "evidence", "prune", "--repo-root", str(repo), "--keep-latest", "2"
            )
            self.assertEqual(dry[0], 0)
            self.assertEqual(len(list(root.iterdir())), 3)
            applied = self.invoke(
                "evidence", "prune", "--repo-root", str(repo), "--keep-latest", "2", "--apply"
            )
            self.assertEqual(applied[0], 0)
            self.assertEqual(len(list(root.iterdir())), 2)

    def test_release_orchestration_is_theme_a_through_d_and_agent_checks_are_separate(self):
        repo = Path(__file__).resolve().parent.parent
        orchestration = (
            (repo / "scripts/release-check.sh").read_text(encoding="utf-8")
            + (repo / "tools/release_batch.py").read_text(encoding="utf-8")
        )
        self.assertNotIn("agent_behavior_matrix", orchestration)
        self.assertNotIn("tests/agent-smoke", orchestration)
        self.assertNotRegex(orchestration, r"\b(?:codex|claude|antigravity)\b")
        readme = (repo / "README.md").read_text(encoding="utf-8")
        self.assertIn("Layers A–D", readme)
        self.assertIn("docs/AGENT_COMPATIBILITY.md", readme)


    def test_named_theme_is_built_fresh_into_the_work_dir(self):
        from tools.release_batch import _resolve_package
        repo = Path(__file__).resolve().parent.parent
        version = json.loads((repo / "sample-themes/linen/theme.json").read_text(encoding="utf-8"))["version"]
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = _resolve_package(repo, "linen", Path(tmp), "0" * 40)
            self.assertEqual(zip_path, (Path(tmp) / "packages/linen" / f"linen-{version}.zip").resolve())

    def test_explicit_zip_is_used_as_given(self):
        from tools.release_batch import _resolve_package
        with tempfile.TemporaryDirectory() as tmp:
            given = Path(tmp) / "x-9.9.9.zip"
            given.write_bytes(b"zip")
            self.assertEqual(_resolve_package(Path(tmp), given, Path(tmp) / "work", "0" * 40), given.resolve())

    def test_candidate_install_receives_the_verified_archives(self):
        source = (Path(__file__).resolve().parent.parent / "tools/release_batch.py").read_text(encoding="utf-8")
        self.assertIn('"--packages"', source)
        self.assertNotIn("resolve_package_zip", source)

if __name__ == "__main__":
    unittest.main()
