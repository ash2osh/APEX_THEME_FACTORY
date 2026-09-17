"""Task 5 (verification-integrity-defects plan): scripts/sync-static.sh registered every synced
file with `charSet: utf-8`, including `.woff2` and images. Harmless to APEX at runtime (it ignores
charSet for binaries) but a false statement in generated source that will mislead the next person
reading the export.

This reads the real, committed applications/ut/shared-components/static-files.apx - not a fixture -
because that generated file *is* the thing under test (plan note: this changes applications/ut/**,
which is source, so the fix and the regenerated export land together in this batch).

Scoped to css/ and js/ - the paths sync-static.sh actually registers (its own themes, plus the
project's static-files/ tree). static-files.apx also carries ~30 pre-existing binary entries
(icons/, img/, pwa/, demo/, theme_styles/, one APEX$DATA$PKG zip) that ship with the base Universal
Theme demo app and were never written by this script; those are Oracle's own export default, not
this project's source, and are out of scope for this task.
"""

from pathlib import Path
import re
import unittest

STATIC_FILES_APX = Path(__file__).resolve().parent.parent / "applications/ut/shared-components/static-files.apx"

# Mirrors sync-static.sh's is_text_mime(): image/svg+xml is XML text, unlike the other image/*
# types mime() can emit here (png, jpeg), so it is deliberately not treated as binary.
TEXT_MIME_PREFIXES = ("text/",)
TEXT_MIME_EXACT = {"application/javascript", "application/json", "image/svg+xml"}


def _is_text_mime(mime: str) -> bool:
    return mime in TEXT_MIME_EXACT or mime.startswith(TEXT_MIME_PREFIXES)


class SyncStaticCharsetTests(unittest.TestCase):
    def _file_blocks(self):
        text = STATIC_FILES_APX.read_text(encoding="utf-8")
        blocks = re.findall(r'file "([^"]+)" \(\n((?:    [^\n]*\n)+)\)', text)
        # Only what sync-static.sh manages - see module docstring for what else lives in this file.
        return [(path, body) for path, body in blocks if path.startswith(("css/", "js/"))]

    def test_no_binary_file_block_declares_a_charset(self):
        offenders = []
        for path, body in self._file_blocks():
            mime_match = re.search(r"mimeType:\s*(\S+)", body)
            mime = mime_match.group(1) if mime_match else ""
            if mime and not _is_text_mime(mime) and "charSet:" in body:
                offenders.append(path)
        self.assertEqual(offenders, [], f"binary static files must not declare charSet: {offenders}")

    def test_font_and_image_file_blocks_are_covered_by_this_test(self):
        # guards against the check silently checking nothing if the file layout ever changes
        mimes = {re.search(r"mimeType:\s*(\S+)", body).group(1) for _, body in self._file_blocks()}
        self.assertIn("font/woff2", mimes)
        self.assertTrue(any(m.startswith("image/") and m != "image/svg+xml" for m in mimes), mimes)

    def test_text_file_blocks_still_declare_a_charset(self):
        # the fix must narrow the check, not just delete charSet everywhere - a real text asset
        # (CSS, JS, JSON) losing its charSet would be a regression, not a fix.
        css_or_js = [
            (path, body) for path, body in self._file_blocks()
            if re.search(r"mimeType:\s*(text/css|application/javascript|text/javascript)\b", body)
        ]
        self.assertTrue(css_or_js, "expected at least one CSS/JS file block to check")
        missing = [path for path, body in css_or_js if "charSet:" not in body]
        self.assertEqual(missing, [], f"text files should still declare charSet: {missing}")


if __name__ == "__main__":
    unittest.main()
