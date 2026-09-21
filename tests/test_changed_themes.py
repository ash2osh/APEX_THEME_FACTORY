import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from lib.theme_factory.changed import changed_themes, select_changed_themes


class ChangedThemeSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Theme Test")
        for name in ("alpha", "beta"):
            theme = self.root / "sample-themes" / name
            (theme / "css").mkdir(parents=True)
            (theme / "theme.json").write_text(json.dumps({
                "schemaVersion": 1,
                "name": name,
                "title": name.title(),
                "version": "1.0.0",
                "tagline": f"{name} theme",
                "class": f"app-theme-{name}",
                "compatibility": {
                    "apex": ">=26.1.0 <26.2.0", "themeNumber": 42,
                    "baseTheme": "ut-26.1", "themeStyle": "Iris",
                },
                "assets": {
                    "stylesheet": "theme.css", "runtime": "theme-factory-runtime.js",
                    "cover": "preview/cover.jpg",
                },
            }), encoding="utf-8")
            (theme / "css/tokens.css").write_text(f"/* {name} */\n", encoding="utf-8")
        (self.root / "lib/theme_factory").mkdir(parents=True)
        (self.root / "theme-templates").mkdir()
        (self.root / "static-files/css/foundation").mkdir(parents=True)
        (self.root / "installer").mkdir()
        (self.root / ".github/workflows").mkdir(parents=True)
        (self.root / "docs").mkdir()
        (self.root / "lib/theme_factory/checks.py").write_text("# checks\n", encoding="utf-8")
        (self.root / "theme-templates/base.tmpl").write_text("base\n", encoding="utf-8")
        (self.root / "static-files/css/foundation/tokens.css").write_text("root\n", encoding="utf-8")
        (self.root / "installer/install.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.root / ".github/workflows/verify.yml").write_text("name: verify\n", encoding="utf-8")
        (self.root / "docs/NOTES.md").write_text("# notes\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "baseline")
        self.base = self.git("rev-parse", "HEAD")

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True, text=True
        ).stdout.strip()

    def commit_change(self, relative: str, content: str = "changed\n") -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"change {relative}")
        return self.git("rev-parse", "HEAD")

    def test_package_local_change_selects_only_that_theme(self):
        head = self.commit_change("sample-themes/alpha/css/tokens.css")
        self.assertEqual(changed_themes(self.root, self.base, head), ("alpha",))

    def test_each_shared_source_class_selects_every_theme(self):
        paths = (
            "lib/theme_factory/checks.py",
            "theme-templates/base.tmpl",
            "static-files/css/foundation/tokens.css",
            "installer/install.sh",
            ".github/workflows/verify.yml",
        )
        for relative in paths:
            with self.subTest(relative=relative):
                head = self.commit_change(relative, f"changed {relative}\n")
                self.assertEqual(changed_themes(self.root, f"{head}^", head), ("alpha", "beta"))

    def test_docs_only_change_outside_generated_sections_selects_none(self):
        head = self.commit_change("docs/NOTES.md", "# prose only\n")
        selection = select_changed_themes(self.root, self.base, head)
        self.assertEqual(selection.themes, ())
        self.assertFalse(selection.repository_wide)

    def test_deleted_theme_is_repository_wide_but_is_not_sent_to_theme_check(self):
        import shutil
        shutil.rmtree(self.root / "sample-themes/beta")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "delete beta")
        head = self.git("rev-parse", "HEAD")
        selection = select_changed_themes(self.root, self.base, head)
        self.assertTrue(selection.repository_wide)
        self.assertEqual(selection.deleted_themes, ("beta",))
        self.assertEqual(selection.themes, ("alpha",))
        self.assertNotIn("beta", selection.themes)

    def test_rename_records_are_parsed_without_treating_status_as_a_path(self):
        self.git("mv", "sample-themes/alpha", "sample-themes/gamma")
        manifest = self.root / "sample-themes/gamma/theme.json"
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document.update({"name": "gamma", "title": "Gamma", "class": "app-theme-gamma"})
        manifest.write_text(json.dumps(document), encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "rename alpha to gamma")
        selection = select_changed_themes(self.root, self.base, self.git("rev-parse", "HEAD"))
        self.assertEqual(selection.deleted_themes, ("alpha",))
        self.assertEqual(selection.themes, ("beta", "gamma"))

    def test_matrix_json_is_stable_and_contains_repository_condition(self):
        head = self.commit_change("lib/theme_factory/checks.py")
        payload = json.loads(select_changed_themes(self.root, self.base, head).to_matrix_json())
        self.assertEqual(payload["include"], [{"theme": "alpha"}, {"theme": "beta"}])
        self.assertTrue(payload["repositoryWide"])
        self.assertEqual(payload["deletedThemes"], [])


class CiTierContractTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parent.parent

    def test_workflows_parse_and_keep_live_layers_out_of_hosted_ci(self):
        import yaml
        verify_path = self.ROOT / ".github/workflows/verify.yml"
        nightly_path = self.ROOT / ".github/workflows/nightly.yml"
        verify = verify_path.read_text(encoding="utf-8")
        nightly = nightly_path.read_text(encoding="utf-8")
        self.assertIsInstance(yaml.safe_load(verify), dict)
        self.assertIsInstance(yaml.safe_load(nightly), dict)
        self.assertIn("lib.theme_factory.changed", verify)
        self.assertIn("catalog --check", verify)
        self.assertIn("inspect-iris --check", verify)
        self.assertIn("Layers C-E are UNVERIFIED", verify)
        self.assertNotIn("chrome_devtools", nightly)
        self.assertNotIn("apex-import", nightly)

    def test_workflows_install_declared_offline_test_dependencies(self):
        requirements_path = self.ROOT / "tools/test-requirements.txt"
        self.assertTrue(requirements_path.is_file())
        requirements = requirements_path.read_text(encoding="utf-8")
        for dependency in ("Pillow==", "PyYAML=="):
            self.assertIn(dependency, requirements)

        for workflow_name in ("verify.yml", "nightly.yml"):
            workflow = (self.ROOT / ".github/workflows" / workflow_name).read_text(encoding="utf-8")
            self.assertIn("python -m pip install", workflow)
            self.assertIn("tools/test-requirements.txt", workflow)

    def test_package_offline_script_discovers_themes_without_a_shortlist(self):
        script = (self.ROOT / "tests/run-package-offline.sh").read_text(encoding="utf-8")
        self.assertIn("theme_names", script)
        self.assertNotIn("package-theme.sh linen", script)
        self.assertNotIn("package-theme.sh solarized-dark", script)


if __name__ == "__main__":
    unittest.main()
