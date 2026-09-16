from pathlib import Path
import json
import shutil
import tempfile
import unittest

from lib.theme_factory.apexlang import (
    apply_patch,
    canonical_digest,
    inspect_export,
    plan_install,
)
from lib.theme_factory.errors import PackageError


class ApexLangPatchTests(unittest.TestCase):
    def fixture_copy(self, name: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copytree(Path("tests/fixtures/apexlang") / name, tmp / "app")
        return tmp / "app"

    def test_reads_supported_theme_boundary(self):
        target = inspect_export(self.fixture_copy("minimal"))
        self.assertEqual(
            (target.theme_number, target.base_theme, target.style),
            (42, "ut-26.1", "iris"),
        )

    def test_install_preserves_existing_urls(self):
        root = self.fixture_copy("with-existing-assets")
        patch = plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve")
        app_rel = Path("application.apx")
        self.assertIn(app_rel, patch.after_files)
        self.assertIn("#APP_FILES#existing.css", patch.after_files[app_rel])
        self.assertIn("theme-factory/packages/valid-basic/1.0.0/theme.css", patch.after_files[app_rel])

    def test_ambiguous_css_block_fails(self):
        root = self.fixture_copy("ambiguous-css-block")
        with self.assertRaises(PackageError) as ctx:
            inspect_export(root)
        self.assertIn("multiple css {} blocks", str(ctx.exception))

    def test_no_page_zero_creates_page_zero_and_registers(self):
        root = self.fixture_copy("no-global-page")
        patch = plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve")
        app_rel = Path("application.apx")
        p0_rel = Path("pages/p00000-global-page.apx")
        self.assertIn("globalPage: 0", patch.after_files[app_rel])
        self.assertIn(p0_rel, patch.after_files)
        self.assertIn("Theme Factory Bootstrap", patch.after_files[p0_rel])

    def test_switcher_enable_and_disable_transitions(self):
        root = self.fixture_copy("with-existing-assets")
        # 1. Enable switcher
        patch_enable = plan_install(root, Path("tests/fixtures/packages/valid-basic"), "enable")
        apply_patch(patch_enable)

        app_text = (root / "application.apx").read_text(encoding="utf-8")
        self.assertIn("theme-factory-runtime.js", app_text)
        nav_text = (root / "shared-components/navigation/lists/navigation-bar.apx").read_text(encoding="utf-8")
        self.assertIn("theme-factory-managed-switcher", nav_text)
        self.assertIn("theme-factory-choice-valid-basic", nav_text)
        self.assertIn("theme-factory-choice-iris", nav_text)

        # 2. Disable switcher
        patch_disable = plan_install(root, Path("tests/fixtures/packages/valid-basic"), "disable")
        apply_patch(patch_disable)

        app_text2 = (root / "application.apx").read_text(encoding="utf-8")
        self.assertNotIn("theme-factory-runtime.js", app_text2)
        nav_text2 = (root / "shared-components/navigation/lists/navigation-bar.apx").read_text(encoding="utf-8")
        self.assertNotIn("theme-factory-managed-switcher", nav_text2)

    def test_reinstall_idempotence(self):
        root = self.fixture_copy("minimal")
        patch1 = plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve")
        apply_patch(patch1)

        digest1 = canonical_digest(root)
        patch2 = plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve")
        apply_patch(patch2)
        digest2 = canonical_digest(root)

        self.assertEqual(digest1, digest2)

    def test_invalid_registry_fails_closed(self):
        root = self.fixture_copy("minimal")
        registry = root / "shared-components/static-files/theme-factory/runtime/registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_text("{not-json", encoding="utf-8")

        with self.assertRaises(PackageError) as context:
            plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve")

        self.assertIn("registry", str(context.exception).lower())

    def test_upgrade_refuses_tampered_owned_file(self):
        root = self.fixture_copy("minimal")
        first = plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve")
        apply_patch(first)
        installed_css = root / "shared-components/static-files/theme-factory/packages/valid-basic/1.0.0/theme.css"
        installed_css.write_text("tampered", encoding="utf-8")

        with self.assertRaises(PackageError) as context:
            plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve")

        self.assertIn("ownership", str(context.exception).lower())

    def test_reinstall_refuses_tampered_runtime_file(self):
        root = self.fixture_copy("minimal")
        apply_patch(plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve"))
        runtime = root / "shared-components/static-files/theme-factory/runtime/theme-factory-runtime.js"
        runtime.write_text("tampered", encoding="utf-8")

        with self.assertRaises(PackageError) as context:
            plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve")

        self.assertIn("runtime ownership", str(context.exception).lower())

    def test_upgrade_deletes_prior_owned_version(self):
        root = self.fixture_copy("minimal")
        package = Path(tempfile.mkdtemp()) / "valid-basic"
        self.addCleanup(shutil.rmtree, package.parent)
        shutil.copytree(Path("tests/fixtures/packages/valid-basic"), package)
        apply_patch(plan_install(root, package, "preserve"))
        manifest = json.loads((package / "theme.json").read_text(encoding="utf-8"))
        manifest["version"] = "2.0.0"
        (package / "theme.json").write_text(json.dumps(manifest), encoding="utf-8")

        upgrade = plan_install(root, package, "preserve")
        old_version = root / "shared-components/static-files/theme-factory/packages/valid-basic/1.0.0"
        self.assertIn(old_version, upgrade.staged_deletions)

    def test_unmarked_managed_region_name_is_a_collision(self):
        root = self.fixture_copy("minimal")
        page_zero = root / "pages/p00000-global-page.apx"
        page_zero.write_text(
            page_zero.read_text(encoding="utf-8").replace(
                "\n)", "\n    region theme_factory_bootstrap ( name: User Region )\n)"
            ),
            encoding="utf-8",
        )

        with self.assertRaises(PackageError) as context:
            plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve")

        self.assertIn("collision", str(context.exception).lower())

    def test_canonical_digest_stability_ignores_export_date(self):
        root = self.fixture_copy("minimal")
        d1 = canonical_digest(root)
        (root / "export.info").write_text("exportDate: 2026-09-15T12:00:00\n", encoding="utf-8")
        d2 = canonical_digest(root)
        self.assertEqual(d1, d2)

    def test_canonical_digest_detects_semantic_whitespace_changes(self):
        root = self.fixture_copy("minimal")
        before = canonical_digest(root)
        application = root / "application.apx"
        application.write_text(application.read_text(encoding="utf-8").replace("    name:", "        name:", 1), encoding="utf-8")
        self.assertNotEqual(before, canonical_digest(root))

    def test_canonical_digest_does_not_ignore_date_like_source_lines(self):
        root = self.fixture_copy("minimal")
        before = canonical_digest(root)
        application = root / "application.apx"
        application.write_text(application.read_text(encoding="utf-8") + "\n-- Date: <img src=x>\n", encoding="utf-8")
        self.assertNotEqual(before, canonical_digest(root))


if __name__ == "__main__":
    unittest.main()
