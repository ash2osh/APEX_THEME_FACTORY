import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from unittest import mock

from lib.theme_factory.archive import build_package_from_root, extract_package, render_template
from scripts import install_all_themes


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
        cls.linen_zip = zip_path
        cobalt_zip = build_package_from_root(
            cls.repo_root, cls.repo_root / "sample-themes/cobalt-press", cls.shared_tmp / "dist",
        )
        cls.cobalt_zip = cobalt_zip
        cls.second_package_dir = extract_package(cobalt_zip, cls.shared_tmp / "pkg2")

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

    def test_yes_skips_the_confirmation_and_imports(self):
        """--yes is the scripted path: no prompt, no stdin, still imports."""
        log = self.tmp / "sql.log"
        result = self.run_cli(
            self.package_dir,
            "--connection", "demo", "--workspace", "DEMO", "--app-id", "314",
            "--apply", "--yes", stdin="", log=log,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("apex import", log.read_text(encoding="utf-8") if log.exists() else "")

    def test_yes_says_in_the_output_that_the_guard_was_skipped(self):
        """A full replace with no human check must leave a trace in the log."""
        result = self.run_cli(
            self.package_dir,
            "--connection", "demo", "--workspace", "DEMO", "--app-id", "314",
            "--apply", "--yes", stdin="", log=self.tmp / "sql.log",
        )
        self.assertIn("--yes", result.stdout)

    def test_without_yes_an_empty_answer_still_cancels(self):
        """The guard must still be the default: no --yes and no answer means untouched."""
        log = self.tmp / "sql.log"
        result = self.run_cli(
            self.package_dir,
            "--connection", "demo", "--workspace", "DEMO", "--app-id", "314",
            "--apply", stdin="", log=log,
        )
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertNotIn("apex import", log.read_text(encoding="utf-8") if log.exists() else "")

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

    def test_default_theme_list_is_discovered_from_manifests(self):
        repo = self.tmp / "repo"
        shutil.copytree(self.repo_root / "sample-themes", repo / "sample-themes")
        ninth = repo / "sample-themes" / "ninth-theme"
        ninth.mkdir()
        manifest = {
            "schemaVersion": 1,
            "name": "ninth-theme",
            "title": "Ninth Theme",
            "version": "1.0.0",
            "tagline": "A dynamically discovered test package.",
            "class": "app-theme-ninth-theme",
            "compatibility": {
                "apex": ">=26.1.0 <26.2.0",
                "themeNumber": 42,
                "baseTheme": "ut-26.1",
                "themeStyle": "Iris",
            },
            "assets": {
                "stylesheet": "theme.css",
                "runtime": "theme-factory-runtime.js",
                "cover": "preview/cover.jpg",
            },
        }
        (ninth / "theme.json").write_text(json.dumps(manifest), encoding="utf-8")

        with mock.patch.object(install_all_themes, "repo_root", repo):
            args = install_all_themes.parse_args(["--app-id", "102"])

        names = args.themes.split(",")
        self.assertEqual(names, sorted(names))
        self.assertIn("ninth-theme", names)
        self.assertEqual(len(names), 9)

    def test_resolve_package_zip_prefers_manifest_version_over_legacy_archive(self):
        repo = self.tmp / "versioned-repo"
        theme = repo / "sample-themes" / "versioned-theme"
        theme.mkdir(parents=True)
        (theme / "theme.json").write_text(
            json.dumps({"name": "versioned-theme", "version": "2.1.0"}),
            encoding="utf-8",
        )
        dist = repo / "dist" / "versioned-theme"
        dist.mkdir(parents=True)
        old = dist / "versioned-theme-1.0.0.zip"
        current = dist / "versioned-theme-2.1.0.zip"
        old.write_bytes(b"old")
        current.write_bytes(b"current")

        with mock.patch.object(install_all_themes, "repo_root", repo):
            self.assertEqual(install_all_themes.resolve_package_zip("versioned-theme"), current)

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

    def run_install_many(self, *package_dirs: Path, extra=(), stdin: str = "", log: Path = None):
        env = os.environ.copy()
        if log:
            env["FAKE_SQL_LOG"] = str(log)
        roots = [arg for path in package_dirs for arg in ("--package-root", str(path))]
        return subprocess.run(
            ["python3", "-m", "lib.theme_factory.cli", "install", *roots,
             "--connection", "demo", "--workspace", "DEMO", "--app-id", "314",
             "--backup-dir", str(self.tmp / "b"), *extra],
            input=stdin, text=True, capture_output=True, env=env, check=False,
        )

    def test_one_transaction_installs_every_package_and_last_is_default(self):
        from lib.theme_factory.apexlang import read_install_state
        result = self.run_install_many(self.package_dir, self.second_package_dir, extra=["--apply"], stdin="314\n")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Status: IMPORTED", result.stdout)
        store = Path(Path(os.environ["FAKE_SQL_STATE_FILE"]).read_text(encoding="utf-8").strip())
        packages, default_theme, _ = read_install_state(store)
        self.assertEqual(sorted(package.name for package in packages), ["cobalt-press", "linen"])
        self.assertEqual(default_theme, "cobalt-press")
        backups = list((self.tmp / "b" / "DEMO-314").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].name.endswith("-before-2-themes"), backups[0].name)
        target = json.loads((backups[0] / "target.json").read_text(encoding="utf-8"))
        self.assertEqual([item["name"] for item in target["themes"]], ["linen", "cobalt-press"])
        self.assertEqual(target["theme"], "cobalt-press")

    def test_same_theme_twice_is_refused_before_sqlcl(self):
        log = self.tmp / "sql.log"
        result = self.run_install_many(self.package_dir, self.package_dir, log=log)
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("more than once", result.stderr)
        self.assertFalse(log.exists())
