import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib.theme_factory.checks import CheckIssue, CheckReport
from lib.theme_factory.cli import run_cli


class ThemeCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def report(status: str = "PASS") -> CheckReport:
        issues = () if status == "PASS" else (
            CheckIssue("error", "BROKEN", "broken package", "theme.json", 1),
        )
        return CheckReport(status, "fixture", False, 4, "a" * 64, issues)

    def invoke(self, *arguments: str):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = run_cli(list(arguments))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_check_returns_zero_on_pass_and_two_on_error(self):
        with patch("lib.theme_factory.cli.run_theme_checks", return_value=self.report("PASS")):
            passed = self.invoke("check", "fixture", "--repo-root", str(self.repo))
        with patch("lib.theme_factory.cli.run_theme_checks", return_value=self.report("ERROR")):
            failed = self.invoke("check", "fixture", "--repo-root", str(self.repo))
        self.assertEqual(passed[0], 0)
        self.assertEqual(failed[0], 2)

    def test_check_json_writes_exactly_one_document(self):
        with patch("lib.theme_factory.cli.run_theme_checks", return_value=self.report("PASS")):
            code, stdout, stderr = self.invoke(
                "check", "fixture", "--repo-root", str(self.repo), "--json"
            )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        decoder = json.JSONDecoder()
        payload, end = decoder.raw_decode(stdout)
        self.assertEqual(stdout[end:].strip(), "")
        self.assertEqual(payload["status"], "PASS")

    def test_new_requires_recipe_or_all_inline_identity_fields(self):
        code, _, stderr = self.invoke("new", "new-theme", "--repo-root", str(self.repo))
        self.assertEqual(code, 2)
        self.assertIn("--recipe", stderr)

        code, _, stderr = self.invoke(
            "new", "new-theme", "--repo-root", str(self.repo),
            "--title", "New Theme", "--tagline", "A theme",
        )
        self.assertEqual(code, 2)
        self.assertIn("--mode", stderr)

    def test_dev_import_requires_apply(self):
        code, _, stderr = self.invoke(
            "dev", "fixture", "--repo-root", str(self.repo), "--import"
        )
        self.assertEqual(code, 2)
        self.assertIn("--apply", stderr)


if __name__ == "__main__":
    unittest.main()
