import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from lib.theme_factory.static_files import file_block, mime_type

REPO = Path(__file__).resolve().parent.parent


class StaticFileBlockTests(unittest.TestCase):
    def test_text_assets_declare_utf8(self):
        self.assertEqual(file_block("css/app.css"), 'file "css/app.css" (\n    mimeType: text/css\n    charSet: utf-8\n)')
        self.assertIn("charSet: utf-8", file_block("icons/logo.svg"))
        self.assertIn("charSet: utf-8", file_block("js/app.js.map"))

    def test_binary_assets_declare_no_charset(self):
        for rel, mime in (("css/f/a.woff2", "font/woff2"), ("c/cover.jpg", "image/jpeg"), ("i/x.png", "image/png")):
            self.assertEqual(file_block(rel), f'file "{rel}" (\n    mimeType: {mime}\n)')

    def test_unknown_suffix_is_octet_stream_without_charset(self):
        self.assertEqual(mime_type("x/LICENSE.bin"), "application/octet-stream")
        self.assertNotIn("charSet", file_block("x/LICENSE.bin"))

    def test_installer_registers_fonts_without_charset(self):
        from lib.theme_factory.apexlang import plan_install
        from lib.theme_factory.archive import build_package, extract_package
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"THEME_FACTORY_ALLOW_DIRTY": "1"}):
            package = extract_package(build_package(REPO, "cobalt-press", Path(tmp) / "zip"), Path(tmp) / "pkg")
            app = Path(tmp) / "app"
            shutil.copytree(REPO / "tests/fixtures/apexlang/real-shape", app)
            patch = plan_install(app, package, "preserve")
            registered = patch.after_files[Path("shared-components/static-files.apx")]
            self.assertIn("mimeType: font/woff2\n)", registered)
            self.assertNotIn("font/woff2\n    charSet", registered)
            self.assertIn("mimeType: text/css\n    charSet: utf-8", registered)
