from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
import unittest

from lib.theme_factory.errors import PackageError
from tools.release_smoke import ReleaseOptions, assert_pristine, run_release


@dataclass
class FakeReport:
    status: str
    issues: tuple = ()

    def to_human(self):
        return f"THEME_CHECK status={self.status}"


@dataclass
class FakeInstall:
    exit_code: int
    status: str = "IMPORTED"


class FakeSql:
    restore_error = None

    def __init__(self, calls):
        self.calls = calls

    def export_apexlang(self, app_id, dest):
        self.calls.append("export")
        return Path(dest)

    def import_apexlang(self, path, workspace, app_id):
        self.calls.append("restore")
        if self.restore_error:
            raise self.restore_error


class ReleaseSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.calls = []

    def run_with(self, *, live=True, check_status="PASS", install_code=0, problems=None, pristine=True,
                 restore_error=None):
        calls = self.calls
        FakeSql.restore_error = restore_error
        self.addCleanup(setattr, FakeSql, "restore_error", None)

        def checks(repo_root, theme):
            calls.append("check")
            return FakeReport(check_status, ("bad contrast",) if check_status != "PASS" else ())

        def build(repo_root, theme, out_dir):
            calls.append("package")
            return self.tmp / f"{theme}-1.0.0.zip"

        def verify(zip_path):
            calls.append("verify")

        def pristine_check(export_dir):
            calls.append("pristine")
            if not pristine:
                raise PackageError("already has packages")

        def install(root, options):
            calls.append("install")
            return FakeInstall(install_code)

        def browser(zip_path, theme, url, widths):
            calls.append("browser")
            return problems if problems is not None else {width: [] for width in widths}

        options = ReleaseOptions(repo_root=self.tmp, theme="linen", live=live, work_dir=self.tmp / "work")
        return run_release(
            options, checks=checks, build=build, verify=verify, sqlcl_factory=lambda conn: FakeSql(calls),
            pristine_check=pristine_check, extract=lambda zip_path, dest: dest, install=install,
            browser=browser, out=lambda line: calls.append(("out", line)),
        )

    def steps(self):
        return [call for call in self.calls if not isinstance(call, tuple)]

    def test_offline_release_checks_packages_and_stops(self):
        self.assertEqual(self.run_with(live=False), 0)
        self.assertEqual(self.steps(), ["check", "package", "verify"])

    def test_failed_check_stops_before_packaging(self):
        self.assertEqual(self.run_with(check_status="FAIL"), 1)
        self.assertEqual(self.steps(), ["check"])

    def test_live_release_installs_checks_browser_and_restores(self):
        self.assertEqual(self.run_with(), 0)
        self.assertEqual(self.steps(),
                         ["check", "package", "verify", "export", "pristine", "install", "browser", "restore"])

    def test_browser_problem_fails_and_still_restores(self):
        self.assertEqual(self.run_with(problems={1440: [], 375: ["console error: boom"]}), 1)
        self.assertEqual(self.steps()[-1], "restore")
        self.assertIn(("out", "  375px: console error: boom"), self.calls)

    def test_failed_install_skips_browser_and_restores(self):
        self.assertEqual(self.run_with(install_code=5), 1)
        self.assertNotIn("browser", self.steps())
        self.assertEqual(self.steps()[-1], "restore")

    def test_failed_restore_is_reported_next_to_the_failed_install(self):
        self.assertEqual(self.run_with(install_code=5, restore_error=PackageError("import refused")), 1)
        lines = [call[1] for call in self.calls if isinstance(call, tuple)]
        self.assertTrue(any("step=install" in line for line in lines))
        self.assertTrue(any("step=restore" in line and "NOT restored" in line for line in lines))

    def test_failed_restore_alone_fails_the_release(self):
        self.assertEqual(self.run_with(restore_error=PackageError("import refused")), 1)

    def test_restore_failure_does_not_hide_the_original_exception(self):
        calls = self.calls

        def boom(zip_path, theme, url, widths):
            raise RuntimeError("browser died")

        FakeSql.restore_error = PackageError("import refused")
        self.addCleanup(setattr, FakeSql, "restore_error", None)
        options = ReleaseOptions(repo_root=self.tmp, theme="linen", live=True, work_dir=self.tmp / "work")
        with self.assertRaises(RuntimeError):
            run_release(
                options, checks=lambda r, t: FakeReport("PASS"), build=lambda r, t, o: self.tmp / "z.zip",
                verify=lambda z: None, sqlcl_factory=lambda conn: FakeSql(calls), pristine_check=lambda d: None,
                extract=lambda z, d: d, install=lambda root, o: FakeInstall(0), browser=boom,
                out=lambda line: calls.append(("out", line)),
            )
        self.assertTrue(any(isinstance(c, tuple) and "step=restore" in c[1] for c in calls))

    def test_consumer_with_leftover_packages_is_refused_before_install(self):
        with self.assertRaises(PackageError):
            self.run_with(pristine=False)
        self.assertNotIn("install", self.steps())
        self.assertNotIn("restore", self.steps())

    def test_pristine_check_reads_the_install_registry(self):
        from lib.theme_factory.apexlang import apply_patch, plan_install
        assert_pristine(Path("tests/fixtures/apexlang/real-shape"))
        app = self.tmp / "app"
        shutil.copytree("tests/fixtures/apexlang/real-shape", app)
        apply_patch(plan_install(app, Path("tests/fixtures/packages/valid-basic"), "preserve"))
        with self.assertRaises(PackageError) as context:
            assert_pristine(app)
        self.assertIn("valid-basic", str(context.exception))


if __name__ == "__main__":
    unittest.main()
