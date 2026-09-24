from pathlib import Path
import shutil
import tempfile
import unittest

from lib.theme_factory.static_files import file_block
from lib.theme_factory.sync_static import sync

REPO = Path(__file__).resolve().parent.parent
THEMES = ("linen", "cobalt-press")  # linen has no custom fonts; cobalt-press has four WOFF2 faces


class SyncStaticTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        self.root = tmp / "repo"
        shutil.copytree(REPO / "static-files", self.root / "static-files")
        shutil.copytree(REPO / "installer", self.root / "installer")
        for name in THEMES:
            shutil.copytree(REPO / "sample-themes" / name, self.root / "sample-themes" / name)
        shared = self.root / "applications/ut/shared-components"
        (shared / "static-files/icons").mkdir(parents=True)
        (shared / "static-files/icons/app-icon.png").write_bytes(b"png")
        self.apx = shared / "static-files.apx"
        self.apx.write_text('file "icons/app-icon.png" (\n    mimeType: image/png\n)\n', encoding="utf-8")
        self.dst = shared / "static-files"

    def test_first_sync_copies_registers_and_writes_the_themes_block(self):
        sync(self.root)
        app_css = (self.root / "static-files/css/app.css").read_text(encoding="utf-8")
        self.assertIn('/* @themes:start */\n@import "themes/cobalt-press/theme.css";\n'
                      '@import "themes/linen/theme.css";\n/* @themes:end */', app_css)
        self.assertEqual((self.dst / "css/app.css").read_text(encoding="utf-8"), app_css)
        self.assertTrue((self.dst / "css/themes/linen/theme.json").is_file())
        self.assertTrue(list((self.dst / "css/themes/cobalt-press/fonts").glob("*.woff2")))
        self.assertIn("@font-face", (self.dst / "css/themes/cobalt-press/theme.css").read_text(encoding="utf-8"))
        self.assertFalse((self.dst / "js/vendor/alpine.js").exists())
        self.assertTrue((self.dst / "js/vendor/alpine.min.js").is_file())
        self.assertTrue((self.dst / "js/theme-factory-runtime.js").is_file())
        registered = self.apx.read_text(encoding="utf-8")
        self.assertIn(file_block("css/themes/cobalt-press/theme.css"), registered)
        font = next((self.dst / "css/themes/cobalt-press/fonts").glob("*.woff2")).name
        self.assertIn(file_block(f"css/themes/cobalt-press/fonts/{font}"), registered)
        self.assertIn(file_block("js/theme-factory-runtime.js"), registered)
        self.assertIn('file "icons/app-icon.png"', registered)

    def write_page_zero(self, regions: int = 2) -> Path:
        page = self.root / "applications/ut/pages/p00000-global-page.apx"
        page.parent.mkdir(parents=True, exist_ok=True)
        blocks = []
        if regions >= 1:
            blocks.append("""    region theme (
        name: Theme
        type: staticContent
        source {
            htmlCode:
                ```html
                <script>old</script>
                ```
        }
        layout {
            sequence: 15
            slot: banner
        }
    )""")
        if regions >= 2:
            blocks.append("""    region theme_dialog (
        name: Theme (dialog, drawer, wizard pages)
        type: staticContent
        source {
            htmlCode:
                ```html
                <script>old</script>
                ```
        }
        layout {
            sequence: 1
            slot: breadcrumbBar
        }
    )""")
        page.write_text("page 0 (\n" + "\n\n".join(blocks) + "\n)\n", encoding="utf-8")
        return page

    def test_page_zero_allow_list_tracks_the_installed_themes(self):
        page = self.write_page_zero()
        self.assertTrue(any("bootstrap regions" in item for item in sync(self.root, check=True).drift))
        sync(self.root)
        content = page.read_text(encoding="utf-8")
        self.assertEqual(content.count("window.APEX_THEME_FACTORY_CONFIG ="), 2)
        self.assertIn('"cobalt-press"', content)
        self.assertIn('"linen"', content)
        self.assertEqual(sync(self.root, check=True).drift, [])

    def test_page_zero_with_an_unexpected_region_count_is_refused(self):
        self.write_page_zero(regions=1)
        with self.assertRaises(ValueError):
            sync(self.root, check=True)

    def test_second_sync_is_a_no_op_and_check_passes(self):
        sync(self.root)
        report = sync(self.root)
        self.assertEqual((report.copied, report.registered, report.pruned), (0, 0, 0))
        self.assertEqual(sync(self.root, check=True).drift, [])

    def test_stale_export_file_is_pruned_with_its_registration(self):
        sync(self.root)
        stale = self.dst / "css/themes/gone/theme.css"
        stale.parent.mkdir(parents=True)
        stale.write_text("x", encoding="utf-8")
        self.apx.write_text(self.apx.read_text(encoding="utf-8") + "\n" + file_block("css/themes/gone/theme.css") + "\n",
                            encoding="utf-8")
        report = sync(self.root)
        self.assertEqual(report.pruned, 1)
        self.assertFalse(stale.parent.exists())
        self.assertNotIn("css/themes/gone/", self.apx.read_text(encoding="utf-8"))

    def test_check_reports_drift_without_writing(self):
        sync(self.root)
        source = self.root / "sample-themes/linen/css/theme.css"
        source.write_text(source.read_text(encoding="utf-8") + "\n/* changed */\n", encoding="utf-8")
        before = {p: p.read_bytes() for p in self.dst.rglob("*") if p.is_file()}
        report = sync(self.root, check=True)
        self.assertTrue(any(item.startswith("css/themes/linen/") for item in report.drift), report.drift)
        self.assertEqual(before, {p: p.read_bytes() for p in self.dst.rglob("*") if p.is_file()})

    def test_each_theme_ships_as_one_flattened_stylesheet(self):
        sync(self.root)
        linen = self.dst / "css/themes/linen"
        self.assertEqual(sorted(p.relative_to(linen).as_posix() for p in linen.rglob("*") if p.is_file()),
                         ["cover.jpg", "theme.css", "theme.json"])
        css = (linen / "theme.css").read_text(encoding="utf-8")
        self.assertNotIn("@import", css)
        self.assertIn("html.app-theme-linen", css)

    def test_previously_synced_module_files_are_pruned(self):
        module = self.dst / "css/themes/linen/apex/shell.css"
        module.parent.mkdir(parents=True)
        module.write_text("x", encoding="utf-8")
        self.apx.write_text(self.apx.read_text(encoding="utf-8") + "\n" + file_block("css/themes/linen/apex/shell.css") + "\n",
                            encoding="utf-8")
        sync(self.root)
        self.assertFalse(module.exists())
        self.assertNotIn("css/themes/linen/apex/", self.apx.read_text(encoding="utf-8"))
