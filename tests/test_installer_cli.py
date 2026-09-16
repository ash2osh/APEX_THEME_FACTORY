import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from lib.theme_factory.archive import build_package_from_root, render_template


class InstallerCliTests(unittest.TestCase):
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

    def run_cli(self, package: Path, *args: str, stdin: str = "", mode: str = "success", log: Path = None):
        env = os.environ.copy()
        env["FAKE_SQL_MODE"] = mode
        if log:
            env["FAKE_SQL_LOG"] = str(log)
        return subprocess.run(
            ["python3", "-m", "lib.theme_factory.cli", "install", "--package-root", str(package), *args,
             *([] if "--backup-dir" in args else ["--backup-dir", str(self.tmp / "default-backups")])],
            input=stdin,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_dry_run_never_imports(self):
        log = self.tmp / "sql.log"
        result = self.run_cli(
            self.package_dir,
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            log=log,
        )
        self.assertEqual(result.returncode, 0, result.stderr + "\n" + result.stdout)
        self.assertIn("STAGED_ONLY", result.stdout)
        sql_calls = log.read_text(encoding="utf-8") if log.exists() else ""
        self.assertNotIn("apex import", sql_calls)

    def test_packaged_install_wrapper_runs_outside_package_directory(self):
        result = subprocess.run(
            [
                "bash", str(self.package_dir / "install.sh"),
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

    def test_checksum_failure_before_sqlcl(self):
        bad_pkg = self.tmp / "bad-pkg"
        shutil.copytree(self.package_dir, bad_pkg)
        (bad_pkg / "theme.css").write_text("/* corrupted */", encoding="utf-8")

        log = self.tmp / "sql.log"
        result = self.run_cli(
            bad_pkg,
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            log=log,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Checksum mismatch", result.stderr)
        self.assertFalse(log.exists())

    def test_apply_confirmation_mismatch_leaves_target_untouched(self):
        log = self.tmp / "sql.log"
        result = self.run_cli(
            self.package_dir,
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            "--apply",
            stdin="999\n",
            log=log,
        )
        # explicit cancellation is not success: scripts must be able to tell it apart (exit 7)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn("TARGET_UNTOUCHED", result.stdout)
        sql_calls = log.read_text(encoding="utf-8") if log.exists() else ""
        self.assertNotIn("apex import", sql_calls)

    def test_apply_confirmation_match_imports(self):
        log = self.tmp / "sql.log"
        backup_dir = self.tmp / "backups"
        result = self.run_cli(
            self.package_dir,
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            "--backup-dir", str(backup_dir),
            "--apply",
            stdin="314\n",
            log=log,
        )
        self.assertEqual(result.returncode, 0, result.stderr + "\n" + result.stdout)
        self.assertIn("IMPORTED", result.stdout)
        sql_calls = log.read_text(encoding="utf-8") if log.exists() else ""
        self.assertIn("apex import", sql_calls)

        self.assertTrue(backup_dir.exists())
        target_jsons = list(backup_dir.rglob("target.json"))
        self.assertEqual(len(target_jsons), 1)
        data = json.loads(target_jsons[0].read_text(encoding="utf-8"))
        self.assertEqual(data["appId"], 314)
        self.assertEqual(data["workspace"], "DEMO")
        self.assertNotIn("demo", data.values())

    def test_validation_failure_exits_code_5(self):
        result = self.run_cli(
            self.package_dir,
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            mode="validation-warning",
        )
        self.assertEqual(result.returncode, 5)

    def test_rejects_target_outside_apex_26_1_before_export(self):
        log = self.tmp / "sql.log"
        result = self.run_cli(
            self.package_dir,
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            mode="unsupported-apex",
            log=log,
        )
        self.assertEqual(result.returncode, 3)
        self.assertIn("APEX 26.1.x", result.stderr)
        calls = log.read_text(encoding="utf-8")
        self.assertNotIn("apex export", calls)

    def test_postcheck_failure_exits_code_6(self):
        result = self.run_cli(
            self.package_dir,
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            "--apply",
            stdin="314\n",
            mode="postcheck-fail",
        )
        self.assertEqual(result.returncode, 6)
        self.assertIn("IMPORTED_POSTCHECK_FAILED", result.stdout)

    def test_postcheck_detects_any_imported_export_divergence(self):
        result = self.run_cli(
            self.package_dir, "--connection", "demo", "--workspace", "DEMO",
            "--app-id", "314", "--apply", stdin="314\n", mode="postcheck-diverge",
        )
        self.assertEqual(result.returncode, 6, result.stderr + result.stdout)
        self.assertIn("IMPORTED_POSTCHECK_FAILED", result.stdout)

    def test_switcher_flags_are_mutually_exclusive(self):
        result = self.run_cli(
            self.package_dir,
            "--connection", "demo",
            "--workspace", "DEMO",
            "--app-id", "314",
            "--with-switcher",
            "--without-switcher",
        )
        self.assertEqual(result.returncode, 2)

    def test_templates_comply_with_heading_and_content_rules(self):
        readme_tmpl = (self.repo_root / "installer/templates/README.md.tmpl").read_text(encoding="utf-8")
        manual_tmpl = (self.repo_root / "installer/templates/MANUAL-INSTALL.md.tmpl").read_text(encoding="utf-8")

        replacements = {
            "THEME_NAME": "linen",
            "THEME_TITLE": "Linen",
            "THEME_VERSION": "1.0.0",
            "THEME_TAGLINE": "Warm editorial styling",
            "THEME_CLASS": "app-theme-linen",
            "BOOTSTRAP_SNIPPET": "<!-- snippet -->",
            "NAV_STYLE_LABEL": "t-TreeNav--styleB",
        }

        rendered_readme = render_template(self.repo_root / "installer/templates/README.md.tmpl", replacements)
        rendered_manual = render_template(self.repo_root / "installer/templates/MANUAL-INSTALL.md.tmpl", replacements)

        # No unresolved placeholders
        self.assertNotIn("__", rendered_readme)
        self.assertNotIn("__", rendered_manual)
        self.assertNotIn("{{", rendered_readme)
        self.assertNotIn("{{", rendered_manual)

        # No "repeat the automated process"
        self.assertNotIn("repeat the automated process", rendered_manual.lower())

        # Heading contracts
        readme_expected_headings = [
            "# Install Linen",
            "## Compatibility",
            "## Package contents and checksums",
            "## Automated SQLcl dry-run",
            "## Automated SQLcl apply",
            "## Optional switcher",
            "## Per-browser persistence",
            "## Uninstall and restore",
            "## Exit codes and recovery artifacts",
        ]
        for h in readme_expected_headings:
            self.assertIn(h, rendered_readme)

        manual_expected_headings = [
            "# Manual APEX Builder installation",
            "## Verify the ZIP",
            "## Upload application static files",
            "## Add the stylesheet URL",
            "## Add the Global Page pre-paint bootstrap",
            "## Optional native navigation switcher",
            "## Verify fonts, Font APEX, dialogs, and refreshes",
            "## Manual uninstall and recovery",
        ]
        for h in manual_expected_headings:
            self.assertIn(h, rendered_manual)

    def test_dry_run_and_apply_remove_staging_directories(self):
        """Temporary staging exports must not accumulate in the system temp directory."""
        tmpdir = self.tmp / "tmpdir"
        tmpdir.mkdir()
        env_backup = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = str(tmpdir)
        try:
            dry = self.run_cli(self.package_dir, "--connection", "demo", "--workspace", "DEMO", "--app-id", "314",
                               "--backup-dir", str(self.tmp / "b"))
            self.assertEqual(dry.returncode, 0, dry.stderr + dry.stdout)
            applied = self.run_cli(self.package_dir, "--connection", "demo", "--workspace", "DEMO", "--app-id", "314",
                                   "--backup-dir", str(self.tmp / "b"), "--apply", stdin="314\n")
            self.assertEqual(applied.returncode, 0, applied.stderr + applied.stdout)
        finally:
            if env_backup is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = env_backup
        leftovers = sorted(path.name for path in tmpdir.iterdir() if path.name.startswith("apex-theme-factory-"))
        self.assertEqual(leftovers, [])

    def test_install_wrapper_refuses_python_older_than_3_10(self):
        fake_bin = self.tmp / "oldpy"
        fake_bin.mkdir()
        shim = fake_bin / "python3"
        shim.write_text(
            "#!/usr/bin/env bash\n"
            "if [ \"$1\" = -c ]; then\n"
            "  # report an unsupported interpreter version for the wrapper's probe\n"
            "  echo 3.8; exit 0\n"
            "fi\n"
            "echo 'lib should never be imported' >&2; exit 99\n",
            encoding="utf-8",
        )
        shim.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env['PATH']}"
        result = subprocess.run(
            ["bash", str(self.package_dir / "install.sh"), "--connection", "demo", "--workspace", "DEMO", "--app-id", "314"],
            cwd=self.tmp, text=True, capture_output=True, env=env, check=False,
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("3.10", result.stderr)
        self.assertNotIn("lib should never be imported", result.stderr)
