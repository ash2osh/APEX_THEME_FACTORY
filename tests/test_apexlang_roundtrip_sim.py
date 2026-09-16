"""Tests for the SQLcl re-export simulator used by the fake `sql` fixture.

The simulator must reproduce the formatting changes observed in real APEX 26.1 /
SQLcl 26.2 exports (theme-factory-backups DEMO-9011, 2026-09-15): APEXLang comment
lines vanish, fenced code is re-indented to the fence column, `file` blocks in
static-files.apx are sorted, and page files are named after the page name.
"""

from pathlib import Path
import shutil
import tempfile
import unittest

from tests.fixtures.bin.apexlang_roundtrip import simulate_export


class RoundtripSimulatorTests(unittest.TestCase):
    def make_export(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copytree(Path("tests/fixtures/apexlang/minimal"), tmp / "app")
        return tmp / "app"

    def test_drops_apexlang_comment_lines_but_keeps_fenced_comments(self):
        root = self.make_export()
        page = root / "pages/p00000-global-page.apx"
        page.write_text(
            "page 0 (\n"
            "    name: Global Page\n"
            "    // APEX_THEME_FACTORY_MANAGED:BEGIN:REGIONS\n"
            "    region r (\n"
            "        name: R\n"
            "        source {\n"
            "            htmlCode:\n"
            "                ```html\n"
            "                <!-- html comment stays -->\n"
            "                // js-looking line stays\n"
            "                ```\n"
            "        }\n"
            "    )\n"
            "    -- APEX_THEME_FACTORY_MANAGED:END:REGIONS\n"
            ")\n",
            encoding="utf-8",
        )
        simulate_export(root)
        text = page.read_text(encoding="utf-8")
        self.assertNotIn("APEX_THEME_FACTORY_MANAGED", text)
        self.assertIn("<!-- html comment stays -->", text)
        self.assertIn("// js-looking line stays", text)

    def test_reindents_fenced_code_to_fence_column(self):
        root = self.make_export()
        page = root / "pages/p00000-global-page.apx"
        page.write_text(
            "page 0 (\n"
            "    name: Global Page\n"
            "    region r (\n"
            "        name: R\n"
            "        source {\n"
            "            htmlCode:\n"
            "                ```html\n"
            "                <script>\n"
            "var x = 1;\n"
            "</script>\n"
            "                ```\n"
            "        }\n"
            "    )\n"
            ")\n",
            encoding="utf-8",
        )
        simulate_export(root)
        lines = page.read_text(encoding="utf-8").splitlines()
        self.assertIn("                                <script>", lines)
        self.assertIn("                var x = 1;", lines)
        self.assertIn("                </script>", lines)

    def test_sorts_static_file_blocks(self):
        root = self.make_export()
        static = root / "shared-components/static-files.apx"
        static.write_text(
            'file "z/last.css" (\n    mimeType: text/css\n    charSet: utf-8\n)\n\n'
            'file "a/first.js" (\n    mimeType: application/javascript\n    charSet: utf-8\n)\n',
            encoding="utf-8",
        )
        simulate_export(root)
        text = static.read_text(encoding="utf-8")
        self.assertLess(text.index('file "a/first.js"'), text.index('file "z/last.css"'))

    def test_names_page_file_after_page_name(self):
        root = self.make_export()
        (root / "pages/p00000-global-page.apx").unlink()
        (root / "pages/p00000-global-page.apx").write_text("page 0 (\n    name: Page Zero\n)\n", encoding="utf-8")
        simulate_export(root)
        self.assertFalse((root / "pages/p00000-global-page.apx").exists())
        self.assertTrue((root / "pages/p00000-page-zero.apx").exists())


if __name__ == "__main__":
    unittest.main()
