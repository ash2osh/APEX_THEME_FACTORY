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


class RealShapeTargetTests(unittest.TestCase):
    """Targets shaped like real SQLcl 26.2 exports (lists.apx, comment-free re-exports)."""

    PACKAGE = Path("tests/fixtures/packages/valid-basic")

    def fixture_copy(self, name: str = "real-shape") -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copytree(Path("tests/fixtures/apexlang") / name, tmp / "app")
        return tmp / "app"

    def install_and_reexport(self, root: Path, mode: str = "preserve") -> None:
        from tests.fixtures.bin.apexlang_roundtrip import simulate_export
        apply_patch(plan_install(root, self.PACKAGE, mode))
        simulate_export(root)

    def test_reinstall_after_real_reexport_owns_its_regions(self):
        root = self.fixture_copy()
        self.install_and_reexport(root)
        page_zero = root / "pages/p00000-global-page.apx"
        self.assertNotIn("APEX_THEME_FACTORY_MANAGED:BEGIN", page_zero.read_text(encoding="utf-8"))

        patch = plan_install(root, self.PACKAGE, "preserve")
        after = patch.after_files[Path("pages/p00000-global-page.apx")]
        self.assertEqual(after.count("region theme_factory_bootstrap ("), 1)
        self.assertEqual(after.count("region theme_factory_bootstrap_dialog ("), 1)
        self.assertIn("region business-global-banner (", after)

    def test_unrelated_region_named_like_ours_is_still_a_collision(self):
        root = self.fixture_copy()
        page_zero = root / "pages/p00000-global-page.apx"
        page_zero.write_text(
            page_zero.read_text(encoding="utf-8").replace(
                "\n)\n", "\n    region theme_factory_bootstrap (\n        name: Theme Factory Bootstrap\n        type: staticContent\n        source {\n            htmlCode: <p>user content</p>\n        }\n    )\n)\n"
            ),
            encoding="utf-8",
        )
        with self.assertRaises(PackageError) as context:
            plan_install(root, self.PACKAGE, "preserve")
        self.assertIn("collision", str(context.exception).lower())

    def test_switcher_entries_land_in_lists_apx_with_valid_grammar(self):
        root = self.fixture_copy()
        patch = plan_install(root, self.PACKAGE, "enable")
        lists = patch.after_files[Path("shared-components/lists.apx")]
        self.assertIn("entry theme-factory-switcher-parent (", lists)
        self.assertIn("entry theme-factory-choice-valid-basic (", lists)
        self.assertIn("entry theme-factory-choice-iris (", lists)
        self.assertIn("parentEntry: @theme-factory-switcher-parent", lists)
        self.assertIn("2: theme-factory-managed-switcher", lists)
        self.assertNotIn("cssClasses", lists)
        self.assertNotIn("APEX_THEME_FACTORY_MANAGED", lists)
        # entries must be inside the navigation-bar list, not the navigation menu
        nav_bar_start = lists.index("list navigation-bar (")
        nav_menu_start = lists.index("list navigation-menu (")
        parent_pos = lists.index("entry theme-factory-switcher-parent (")
        self.assertTrue(nav_bar_start < parent_pos and (parent_pos < nav_menu_start or nav_menu_start < nav_bar_start))

    def test_switcher_creates_javascript_block_when_absent(self):
        root = self.fixture_copy()
        patch = plan_install(root, self.PACKAGE, "enable")
        app = patch.after_files[Path("application.apx")]
        self.assertIn("#APP_FILES#theme-factory/runtime/theme-factory-runtime.js", app)
        self.assertEqual(app.count("javaScript {"), 1)

    def test_switcher_entries_survive_reexport_and_are_regenerated_once(self):
        root = self.fixture_copy()
        self.install_and_reexport(root, "enable")
        patch = plan_install(root, self.PACKAGE, "enable")
        lists = patch.after_files[Path("shared-components/lists.apx")]
        self.assertEqual(lists.count("entry theme-factory-switcher-parent ("), 1)
        self.assertEqual(lists.count("entry theme-factory-choice-iris ("), 1)

    def test_disable_after_enable_removes_switcher_entries_and_runtime_url(self):
        root = self.fixture_copy()
        self.install_and_reexport(root, "enable")
        patch = plan_install(root, self.PACKAGE, "disable")
        self.assertNotIn("theme-factory-", patch.after_files[Path("shared-components/lists.apx")])
        self.assertNotIn("theme-factory-runtime.js", patch.after_files[Path("application.apx")])

    def test_switcher_refuses_sql_query_navigation_bar(self):
        root = self.fixture_copy()
        lists = root / "shared-components/lists.apx"
        text = lists.read_text(encoding="utf-8")
        head, tail = text.split("list navigation-bar (\n    name: Navigation Bar\n", 1)
        body_end = tail.index("\n)\n")
        text = head + "list navigation-bar (\n    name: Navigation Bar\n    source {\n        type: sqlQuery\n        sqlQuery:\n            ```sql\n            select 1 from dual\n            ```\n    }\n" + tail[body_end:]
        lists.write_text(text, encoding="utf-8")
        with self.assertRaises(PackageError) as context:
            plan_install(root, self.PACKAGE, "enable")
        self.assertIn("MANUAL-INSTALL.md", str(context.exception))

    def test_theme_file_is_resolved_from_current_theme(self):
        root = self.fixture_copy()
        legacy = root / "shared-components/themes/legacy/theme.apx"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("theme legacy (\n    name: Legacy\n    themeNumber: 1\n    baseTheme: ut-24.2\n)\n", encoding="utf-8")
        target = inspect_export(root)
        self.assertEqual(target.theme_number, 42)

    def test_ambiguous_theme_without_current_theme_is_refused(self):
        root = self.fixture_copy()
        legacy = root / "shared-components/themes/legacy/theme.apx"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("theme legacy (\n    name: Legacy\n    themeNumber: 42\n    baseTheme: ut-26.1\n)\n", encoding="utf-8")
        app = root / "application.apx"
        app.write_text(app.read_text(encoding="utf-8").replace("        currentTheme: @universal-theme\n", ""), encoding="utf-8")
        with self.assertRaises(PackageError) as context:
            inspect_export(root)
        self.assertIn("theme", str(context.exception).lower())

    def styled_package(self) -> Path:
        package = Path(tempfile.mkdtemp()) / "valid-basic"
        self.addCleanup(shutil.rmtree, package.parent)
        shutil.copytree(self.PACKAGE, package)
        manifest = json.loads((package / "theme.json").read_text(encoding="utf-8"))
        manifest["templateOptions"] = {"navigationMenuStyle": "t-TreeNav--styleB"}
        (package / "theme.json").write_text(json.dumps(manifest), encoding="utf-8")
        return package

    def test_navigation_menu_style_from_manifest_replaces_existing_style(self):
        root = self.fixture_copy()
        patch = plan_install(root, self.styled_package(), "preserve")
        app = patch.after_files[Path("application.apx")]
        self.assertIn("t-TreeNav--styleB", app)
        self.assertNotIn("t-TreeNav--styleA", app)
        self.assertIn("js-defaultCollapsed", app)

    def test_navigation_menu_style_is_skipped_without_side_navigation_template(self):
        root = self.fixture_copy()
        app_file = root / "application.apx"
        app_file.write_text(
            app_file.read_text(encoding="utf-8").replace("listTemplate: @/side-navigation-menu", "listTemplate: @/top-navigation-menu"),
            encoding="utf-8",
        )
        patch = plan_install(root, self.styled_package(), "preserve")
        self.assertIn("t-TreeNav--styleA", patch.after_files[Path("application.apx")])

    def test_projection_is_stable_across_real_reexport(self):
        from lib.theme_factory.apexlang import theme_factory_projection
        from tests.fixtures.bin.apexlang_roundtrip import simulate_export
        root = self.fixture_copy()
        apply_patch(plan_install(root, self.PACKAGE, "enable"))
        staged = theme_factory_projection(root)
        simulate_export(root)
        self.assertEqual(staged, theme_factory_projection(root))
        self.assertIn("valid-basic", json.dumps(staged))

    def test_projection_detects_unrelated_static_file_change(self):
        from lib.theme_factory.apexlang import theme_factory_projection
        root = self.fixture_copy()
        apply_patch(plan_install(root, self.PACKAGE, "preserve"))
        before = theme_factory_projection(root)
        (root / "shared-components/static-files/css/business-brand.css").write_text("changed", encoding="utf-8")
        self.assertNotEqual(before, theme_factory_projection(root))
