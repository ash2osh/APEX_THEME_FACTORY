"""End-to-end lifecycle against a target shaped like a real SQLcl export.

The fake `sql` re-exports through the SQLcl formatting simulator, so every step after the
first import sees comment-free, re-indented, re-sorted APEXLang — the shapes that broke the
2026-09-15 installer on real consumers (marker regression, byte-digest post-check).
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from lib.theme_factory.archive import build_package_from_root
from lib.theme_factory.apexlang import inspect_export, read_install_state


class RealShapeLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.shared_tmp = Path(tempfile.mkdtemp())
        os.environ["THEME_FACTORY_ALLOW_DIRTY"] = "1"
        cls.packages = {}
        for name in ("linen", "solarized-dark"):
            zip_path = build_package_from_root(cls.repo_root, cls.repo_root / f"sample-themes/{name}", cls.shared_tmp / "dist")
            extract_root = cls.shared_tmp / f"pkg-{name}"
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract_root)
            cls.packages[name] = next(extract_root.iterdir())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.shared_tmp, ignore_errors=True)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.backups = self.tmp / "backups"
        self.state_file = self.tmp / "fake-sql-state.txt"
        fake_bin = str((Path(__file__).resolve().parent / "fixtures/bin").resolve())
        self.env = os.environ.copy()
        self.env["PATH"] = f"{fake_bin}:{self.env.get('PATH', '')}"
        self.env["FAKE_SQL_MODE"] = "success"
        self.env["FAKE_SQL_FIXTURE"] = "real-shape"
        self.env["FAKE_SQL_STATE_FILE"] = str(self.state_file)

    def cli(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess:
        backup_flag = [] if args[0] == "restore" else ["--backup-dir", str(self.backups)]
        return subprocess.run(
            ["python3", "-m", "lib.theme_factory.cli", *args, "--connection", "demo", "--workspace", "DEMO",
             "--app-id", "314", *backup_flag],
            input=stdin, text=True, capture_output=True, env=self.env, check=False, cwd=self.repo_root,
        )

    def install(self, name: str, *flags: str) -> subprocess.CompletedProcess:
        return self.cli("install", "--package-root", str(self.packages[name]), *flags, "--apply", stdin="314\n")

    def current_export(self) -> Path:
        # The fake sql "imports" by remembering the staged directory; the export that a
        # later SQLcl call would produce is that directory passed through the simulator.
        staged = Path(self.state_file.read_text(encoding="utf-8").strip())
        export = self.tmp / f"export-{len(list(self.tmp.iterdir()))}"
        shutil.copytree(staged, export)
        subprocess.run(["python3", str(Path(__file__).resolve().parent / "fixtures/bin/apexlang_roundtrip.py"), str(export)], check=True)
        return export

    def test_install_reinstall_coexist_switch_uninstall_restore(self):
        fixture = self.repo_root / "tests/fixtures/apexlang/real-shape"
        unrelated_before = {
            path.relative_to(fixture).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in fixture.rglob("*") if path.is_file() and path.suffix != ".apx"
        }

        # 1. install linen with the switcher into a comment-free real-shaped target
        result = self.install("linen", "--with-switcher")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Status: IMPORTED", result.stdout)
        export = self.current_export()
        self.assertNotIn("APEX_THEME_FACTORY_MANAGED:BEGIN", (export / "pages/p00000-global-page.apx").read_text(encoding="utf-8"))
        lists = (export / "shared-components/lists.apx").read_text(encoding="utf-8")
        self.assertIn("entry theme-factory-switcher-parent (", lists)
        self.assertIn("entry theme-factory-choice-linen (", lists)
        self.assertIn("#APP_FILES#theme-factory/runtime/theme-factory-runtime.js", inspect_export(export).javascript_urls)

        # 2. reinstall is idempotent and does not duplicate anything
        result = self.install("linen")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        export = self.current_export()
        page_zero = (export / "pages/p00000-global-page.apx").read_text(encoding="utf-8")
        self.assertEqual(page_zero.count("region theme_factory_bootstrap ("), 1)
        self.assertEqual(page_zero.count("region theme_factory_bootstrap_dialog ("), 1)
        self.assertEqual(page_zero.count("region business-global-banner ("), 1)
        self.assertEqual((export / "shared-components/lists.apx").read_text(encoding="utf-8").count("entry theme-factory-switcher-parent ("), 1)

        # 3. a second single-theme package coexists and the switcher lists both
        result = self.install("solarized-dark")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        export = self.current_export()
        packages, default_theme, switcher_enabled = read_install_state(export)
        self.assertEqual(sorted(package.name for package in packages), ["linen", "solarized-dark"])
        self.assertEqual(default_theme, "solarized-dark")
        self.assertTrue(switcher_enabled)
        lists = (export / "shared-components/lists.apx").read_text(encoding="utf-8")
        self.assertIn("entry theme-factory-choice-solarized-dark (", lists)
        self.assertIn("entry theme-factory-choice-linen (", lists)
        css_urls = inspect_export(export).css_urls
        self.assertIn("#APP_FILES#css/business-brand.css", css_urls)
        self.assertEqual(len([url for url in css_urls if "theme-factory/packages" in url]), 2)

        # 4. disabling the switcher removes entries and runtime URL, keeps both packages
        result = self.install("linen", "--without-switcher")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        export = self.current_export()
        self.assertNotIn("theme-factory-", (export / "shared-components/lists.apx").read_text(encoding="utf-8"))
        self.assertNotIn("theme-factory-runtime.js", " ".join(inspect_export(export).javascript_urls))

        # 5. uninstall the default package: the other one becomes default
        result = self.cli("uninstall", "--theme", "linen", "--apply", stdin="314\n")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Status: UNINSTALLED", result.stdout)
        export = self.current_export()
        packages, default_theme, _ = read_install_state(export)
        self.assertEqual([package.name for package in packages], ["solarized-dark"])
        self.assertEqual(default_theme, "solarized-dark")
        self.assertIn("region theme_factory_bootstrap (", (export / "pages/p00000-global-page.apx").read_text(encoding="utf-8"))

        # 6. uninstall the last package: no Theme Factory trace remains, unrelated content intact
        result = self.cli("uninstall", "--theme", "solarized-dark", "--apply", stdin="314\n")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        export = self.current_export()
        self.assertFalse((export / "shared-components/static-files/theme-factory").exists())
        self.assertNotIn("theme-factory", (export / "application.apx").read_text(encoding="utf-8"))
        self.assertNotIn("theme-factory", (export / "shared-components/static-files.apx").read_text(encoding="utf-8"))
        page_zero = (export / "pages/p00000-global-page.apx").read_text(encoding="utf-8")
        self.assertNotIn("theme_factory", page_zero)
        self.assertIn("region business-global-banner (", page_zero)
        unrelated_after = {
            path.relative_to(export).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in export.rglob("*") if path.is_file() and path.suffix != ".apx"
        }
        self.assertEqual(unrelated_after, unrelated_before)

        # 7. restore the very first backup after confirming what it will discard
        first_backup = sorted(self.backups.rglob("target.json"))[0].parent
        metadata = json.loads((first_backup / "target.json").read_text(encoding="utf-8"))
        self.assertIn("postOperationDigest", metadata)
        # the application has moved on since that backup: restore must refuse by default
        result = self.cli("restore", "--backup", str(first_backup), "--apply", stdin="314\n")
        self.assertEqual(result.returncode, 7, result.stderr + result.stdout)
        self.assertIn("changed since", result.stderr + result.stdout)
        # ...and proceed only when the operator explicitly accepts discarding later changes
        result = self.cli("restore", "--backup", str(first_backup), "--discard-later-changes", "--apply", stdin="314\n")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Status: RESTORED", result.stdout)
        export = self.current_export()
        self.assertFalse((export / "shared-components/static-files/theme-factory").exists())


if __name__ == "__main__":
    unittest.main()
