import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from lib.theme_factory.archive import build_package_from_root
from lib.theme_factory.errors import PackageError
from lib.theme_factory.uninstall import choose_fallback, plan_and_apply_uninstall


class UninstallerCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.shared_tmp = Path(tempfile.mkdtemp())
        os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
        zip_path = build_package_from_root(
            cls.repo_root,
            cls.repo_root / "sample-themes/linen",
            cls.shared_tmp / "dist",
        )
        cls.package_root = cls.shared_tmp / "pkg"
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(cls.package_root)
        cls.package_dir = next(cls.package_root.iterdir())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.shared_tmp, ignore_errors=True)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.fake_bin = str((Path(__file__).resolve().parent / "fixtures/bin").resolve())
        self.orig_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.fake_bin}:{self.orig_path}"
        # keep the fake SQLcl state and default backups inside this test's temp dir
        os.environ["FAKE_SQL_STATE_FILE"] = str(self.tmp / "fake-sql-state.txt")

    def tearDown(self):
        os.environ["PATH"] = self.orig_path
        os.environ.pop("FAKE_SQL_STATE_FILE", None)

    def run_uninstall(self, theme: str, *args: str, stdin: str = "", log: Path = None, mode: str = "success"):
        env = os.environ.copy()
        env["FAKE_SQL_MODE"] = mode
        if log:
            env["FAKE_SQL_LOG"] = str(log)
        return subprocess.run(
            ["python3", "-m", "lib.theme_factory.cli", "uninstall", "--theme", theme, *args,
             *([] if "--backup-dir" in args else ["--backup-dir", str(self.tmp / "default-backups")])],
            input=stdin,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def run_install(self, package: Path, *args: str, stdin: str = ""):
        env = os.environ.copy()
        env["FAKE_SQL_MODE"] = "success"
        return subprocess.run(
            ["python3", "-m", "lib.theme_factory.cli", "install", "--package-root", str(package), *args,
             *([] if "--backup-dir" in args else ["--backup-dir", str(self.tmp / "default-backups")])],
            input=stdin,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def run_restore(self, backup: Path, *args: str, stdin: str = ""):
        env = os.environ.copy()
        env["FAKE_SQL_MODE"] = "success"
        return subprocess.run(
            ["python3", "-m", "lib.theme_factory.cli", "restore", "--backup", str(backup), *args],
            input=stdin,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_keeps_valid_default_then_uses_lexicographic_fallback(self):
        self.assertEqual(choose_fallback("linen", ("linen", "solarized-dark")), "linen")
        self.assertEqual(choose_fallback("removed", ("solarized-dark", "linen")), "linen")
        self.assertEqual(choose_fallback("removed", ()), "iris")

    def test_rejects_unsafe_theme_name_before_sqlcl(self):
        log = self.tmp / "sql.log"
        result = self.run_uninstall(
            "../../..",
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            log=log,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid theme name", result.stderr.lower())
        self.assertFalse(log.exists(), "unsafe input must be rejected before SQLcl runs")

    def test_uninstall_planner_rejects_path_traversal_without_deleting_files(self):
        staged = self.tmp / "app"
        package_dir = staged / "shared-components/static-files/theme-factory/packages/linen/1.0.0"
        unrelated = staged / "shared-components/static-files/keep/user.txt"
        package_dir.mkdir(parents=True)
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("keep", encoding="utf-8")

        with self.assertRaises(PackageError) as ctx:
            plan_and_apply_uninstall(staged, "../../..")

        self.assertIn("invalid theme name", str(ctx.exception).lower())
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep")

    def test_uninstall_refuses_tampered_owned_file(self):
        staged = Path(tempfile.mkdtemp()) / "app"
        self.addCleanup(shutil.rmtree, staged.parent)
        shutil.copytree(Path("tests/fixtures/apexlang/minimal"), staged)
        from lib.theme_factory.apexlang import apply_patch, plan_install
        apply_patch(plan_install(staged, Path("tests/fixtures/packages/valid-basic"), "preserve"))
        installed_css = staged / "shared-components/static-files/theme-factory/packages/valid-basic/1.0.0/theme.css"
        installed_css.write_text("tampered", encoding="utf-8")

        with self.assertRaises(PackageError) as context:
            plan_and_apply_uninstall(staged, "valid-basic")

        self.assertIn("ownership", str(context.exception).lower())

    def test_uninstall_refuses_unowned_sibling_version(self):
        staged = Path(tempfile.mkdtemp()) / "app"
        self.addCleanup(shutil.rmtree, staged.parent)
        shutil.copytree(Path("tests/fixtures/apexlang/minimal"), staged)
        from lib.theme_factory.apexlang import apply_patch, plan_install
        apply_patch(plan_install(staged, Path("tests/fixtures/packages/valid-basic"), "preserve"))
        unowned = staged / "shared-components/static-files/theme-factory/packages/valid-basic/unowned-version/user.txt"
        unowned.parent.mkdir(parents=True)
        unowned.write_text("keep", encoding="utf-8")

        with self.assertRaises(PackageError):
            plan_and_apply_uninstall(staged, "valid-basic")

        self.assertEqual(unowned.read_text(encoding="utf-8"), "keep")

    def test_uninstall_refuses_registry_version_traversal_before_deletion(self):
        staged = Path(tempfile.mkdtemp()) / "app"
        self.addCleanup(shutil.rmtree, staged.parent)
        shutil.copytree(Path("tests/fixtures/apexlang/minimal"), staged)
        from lib.theme_factory.apexlang import apply_patch, plan_install
        apply_patch(plan_install(staged, Path("tests/fixtures/packages/valid-basic"), "preserve"))

        outside = staged.parent / "outside-only/victim"
        outside.mkdir(parents=True)
        marker = outside / "user.txt"
        marker.write_text("keep", encoding="utf-8")
        registry = staged / "shared-components/static-files/theme-factory/runtime/registry.json"
        data = json.loads(registry.read_text(encoding="utf-8"))
        data["themes"][0]["version"] = "../../../../../../outside-only/victim"
        data["themes"][0]["stylesheetUrl"] = (
            "#APP_FILES#theme-factory/packages/valid-basic/"
            "../../../../../../outside-only/victim/theme.css"
        )
        data["themes"][0]["files"] = {"../../../outside-only/victim/user.txt": "0" * 64}
        registry.write_text(json.dumps(data), encoding="utf-8")

        with self.assertRaises(PackageError):
            plan_and_apply_uninstall(staged, "valid-basic")

        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_uninstall_refuses_unowned_css_reference_without_registry(self):
        staged = Path(tempfile.mkdtemp()) / "app"
        self.addCleanup(shutil.rmtree, staged.parent)
        shutil.copytree(Path("tests/fixtures/apexlang/minimal"), staged)
        application = staged / "application.apx"
        original = application.read_text(encoding="utf-8")
        owned_looking = original.replace(
            "#APP_FILES#base.css",
            "#APP_FILES#base.css\n            #APP_FILES#theme-factory/packages/user-theme/1.0.0/theme.css",
        )
        application.write_text(owned_looking, encoding="utf-8")

        with self.assertRaises(PackageError):
            plan_and_apply_uninstall(staged, "user-theme")

        self.assertEqual(application.read_text(encoding="utf-8"), owned_looking)


    def test_packaged_uninstall_wrapper_infers_single_theme(self):
        installed = self.run_install(
            self.package_dir,
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            "--apply",
            stdin="314\n",
        )
        self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)

        result = subprocess.run(
            [
                "bash", str(self.package_dir / "uninstall.sh"),
                "--connection", "demo",
                "--workspace", "DEMO",
                "--app-id", "314",
            ],
            cwd=self.tmp,
            text=True,
            capture_output=True,
            env=os.environ.copy(),
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("STAGED_ONLY", result.stdout)

    def test_dry_run_never_imports(self):
        # First install into state
        self.run_install(self.package_dir, "--connection", "demo", "--workspace", "DEMO", "--app-id", "314", "--apply", stdin="314\n")

        log = self.tmp / "sql.log"
        result = self.run_uninstall(
            "linen",
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            log=log,
        )
        self.assertEqual(result.returncode, 0, result.stderr + "\n" + result.stdout)
        self.assertIn("STAGED_ONLY", result.stdout)
        sql_calls = log.read_text(encoding="utf-8") if log.exists() else ""
        self.assertNotIn("apex import", sql_calls)

    def test_apply_confirmation_match_uninstalls(self):
        # First install
        self.run_install(self.package_dir, "--connection", "demo", "--workspace", "DEMO", "--app-id", "314", "--apply", stdin="314\n")

        log = self.tmp / "sql.log"
        backup_dir = self.tmp / "backups"
        result = self.run_uninstall(
            "linen",
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            "--backup-dir", str(backup_dir),
            "--apply",
            stdin="314\n",
            log=log,
        )
        self.assertEqual(result.returncode, 0, result.stderr + "\n" + result.stdout)
        self.assertIn("UNINSTALLED", result.stdout)
        sql_calls = log.read_text(encoding="utf-8") if log.exists() else ""
        self.assertIn("apex import", sql_calls)

    def test_uninstall_postcheck_detects_any_export_divergence(self):
        self.run_install(self.package_dir, "--connection", "demo", "--workspace", "DEMO", "--app-id", "314", "--apply", stdin="314\n")
        result = self.run_uninstall(
            "linen", "--connection", "demo", "--workspace", "DEMO", "--app-id", "314",
            "--apply", stdin="314\n", mode="postcheck-diverge",
        )
        self.assertEqual(result.returncode, 6, result.stderr + result.stdout)
        self.assertIn("IMPORTED_POSTCHECK_FAILED", result.stdout)

    def test_restore_workflow(self):
        backup_dir = self.tmp / "backups"
        # 1. Install
        self.run_install(self.package_dir, "--connection", "demo", "--workspace", "DEMO", "--app-id", "314", "--backup-dir", str(backup_dir), "--apply", stdin="314\n")

        # Find backup created
        backups = [p for p in backup_dir.rglob("target.json")]
        self.assertTrue(backups)
        specific_backup = backups[0].parent

        # 2. Restore apply
        result = self.run_restore(
            specific_backup,
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            "--apply",
            stdin="314\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr + "\n" + result.stdout)
        self.assertIn("RESTORED", result.stdout)

    def test_restore_refuses_modified_backup(self):
        backup_dir = self.tmp / "backups"
        installed = self.run_install(
            self.package_dir, "--connection", "demo", "--workspace", "DEMO",
            "--app-id", "314", "--backup-dir", str(backup_dir), "--apply", stdin="314\n",
        )
        self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)
        target_json = next(backup_dir.rglob("target.json"))
        backup = target_json.parent
        (backup / "apexlang/application.apx").write_text("tampered", encoding="utf-8")

        result = self.run_restore(
            backup, "--connection", "demo", "--workspace", "DEMO", "--app-id", "314",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("digest", result.stderr.lower())
