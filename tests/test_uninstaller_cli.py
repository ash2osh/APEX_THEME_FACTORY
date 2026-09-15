import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from lib.theme_factory.archive import build_package_from_root
from lib.theme_factory.uninstall import choose_fallback


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
        state_file = Path(f"/tmp/fake_sql_imported_{os.getenv('USER', 'default')}.txt")
        if state_file.exists():
            state_file.unlink()

    def tearDown(self):
        os.environ["PATH"] = self.orig_path
        state_file = Path(f"/tmp/fake_sql_imported_{os.getenv('USER', 'default')}.txt")
        if state_file.exists():
            state_file.unlink()

    def run_uninstall(self, theme: str, *args: str, stdin: str = "", log: Path = None):
        env = os.environ.copy()
        env["FAKE_SQL_MODE"] = "success"
        if log:
            env["FAKE_SQL_LOG"] = str(log)
        return subprocess.run(
            ["python3", "-m", "lib.theme_factory.cli", "uninstall", "--theme", theme, *args],
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
            ["python3", "-m", "lib.theme_factory.cli", "install", "--package-root", str(package), *args],
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
