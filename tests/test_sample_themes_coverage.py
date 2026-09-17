"""Task 6 (verification-integrity-defects plan): estate-slate / estate-slate-dark were committed
in a38076b with zero Layer C/D/E evidence, no row in tests/live/RELEASE-MATRIX.md, and no row in
sample-themes/README.md's status table - simply invisible to the release system. Not a code defect
in a theme; a silence in the reporting. This is the check the plan asks for: every sample-themes/
directory must either show a real verdict or be explicitly marked unverified.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class SampleThemesCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "scripts").mkdir()
        shutil.copy("scripts/check-sample-themes-coverage.sh", self.tmp / "scripts/check-sample-themes-coverage.sh")
        (self.tmp / "sample-themes").mkdir()

    def _make_theme(self, name):
        theme_dir = self.tmp / "sample-themes" / name
        theme_dir.mkdir()
        (theme_dir / "theme.json").write_text("{}", encoding="utf-8")

    def _write_readme(self, body):
        (self.tmp / "sample-themes" / "README.md").write_text(body, encoding="utf-8")

    def _run(self):
        return subprocess.run(
            ["bash", str(self.tmp / "scripts/check-sample-themes-coverage.sh"), str(self.tmp)],
            capture_output=True, text=True,
        )

    def test_every_theme_reported_verified_passes(self):
        self._make_theme("linen")
        self._make_theme("solarized-dark")
        self._write_readme(
            "| Theme | Status |\n|---|---|\n"
            "| [linen](linen/) | release verdict **VERIFIED** |\n"
            "| [solarized-dark](solarized-dark/) | release verdict **VERIFIED** |\n"
        )
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("status=PASS", result.stdout)

    def test_a_theme_with_no_row_at_all_fails_by_name(self):
        self._make_theme("linen")
        self._make_theme("estate-slate")
        self._write_readme(
            "| Theme | Status |\n|---|---|\n"
            "| [linen](linen/) | release verdict **VERIFIED** |\n"
        )
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("estate-slate", result.stderr)
        self.assertIn("silent", result.stderr)

    def test_a_theme_explicitly_marked_unverified_passes(self):
        self._make_theme("estate-slate")
        self._write_readme(
            "| Theme | Status |\n|---|---|\n"
            "| [estate-slate](estate-slate/) | **UNVERIFIED** — not a release candidate |\n"
        )
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_row_that_names_neither_word_fails(self):
        self._make_theme("estate-slate")
        self._write_readme(
            "| Theme | Status |\n|---|---|\n"
            "| [estate-slate](estate-slate/) | work in progress |\n"
        )
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("estate-slate", result.stderr)

    def test_a_directory_without_theme_json_is_not_a_theme(self):
        (self.tmp / "sample-themes" / "not-a-theme").mkdir()
        self._write_readme("| Theme | Status |\n|---|---|\n")
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
