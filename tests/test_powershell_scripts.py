import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from lib.theme_factory.archive import build_package_from_root

ROOT = Path(__file__).resolve().parent.parent
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


@unittest.skipUnless(POWERSHELL, "PowerShell is not installed")
class PowerShellScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        zip_path = build_package_from_root(ROOT, ROOT / "sample-themes/linen", self.tmp / "dist", source_identity="test")
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(self.tmp / "pkg")
        self.package = next((self.tmp / "pkg").iterdir())
        self.env = {
            **os.environ,
            "PATH": f"{ROOT / 'tests/fixtures/bin'}{os.pathsep}{os.environ['PATH']}",
            "FAKE_SQL_MODE": "success",
            "FAKE_SQL_FIXTURE": "real-shape",
            "FAKE_SQL_STATE_FILE": str(self.tmp / "state.txt"),
        }

    def run_script(self, script, *args, stdin=""):
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.package / script), *args],
            cwd=self.package, input=stdin, text=True, capture_output=True, env=self.env, check=False,
        )

    def test_install_uninstall_and_restore_from_the_package_folder(self):
        target = ["--connection", "demo", "--workspace", "DEMO", "--app-id", "314"]

        preview = self.run_script("install.ps1", *target)
        self.assertEqual(preview.returncode, 0, preview.stderr + preview.stdout)
        self.assertIn("STAGED_ONLY", preview.stdout)

        installed = self.run_script("install.ps1", *target, "--apply", stdin="314\n")
        self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)
        self.assertIn("Status: IMPORTED", installed.stdout)

        removed = self.run_script("uninstall.ps1", *target, "--apply", stdin="314\n")
        self.assertEqual(removed.returncode, 0, removed.stderr + removed.stdout)
        self.assertIn("Status: UNINSTALLED", removed.stdout)

        backups = sorted((self.package / "theme-factory-backups").glob("*/*"))
        restored = self.run_script("restore.ps1", *target, "--backup", str(backups[0]), "--apply",
                                   "--discard-later-changes", stdin="314\n")
        self.assertEqual(restored.returncode, 0, restored.stderr + restored.stdout)
        self.assertIn("Status: RESTORED", restored.stdout)

    def test_exit_codes_and_a_missing_python_are_reported(self):
        refused = self.run_script("install.ps1", "--connection", "bad name", "--workspace", "DEMO", "--app-id", "314")
        self.assertEqual(refused.returncode, 2, refused.stderr + refused.stdout)

        self.env["PATH"] = str(self.tmp / "nothing")
        missing = subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.package / "install.ps1")],
            cwd=self.package, text=True, capture_output=True, env=self.env, check=False,
        )
        self.assertEqual(missing.returncode, 2, missing.stderr + missing.stdout)
        self.assertIn("Python 3.10+ is required", missing.stderr)


if __name__ == "__main__":
    unittest.main()
