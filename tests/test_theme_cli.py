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
        return CheckReport(status, "fixture", 4, issues)

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

    def test_cover_is_not_blocked_by_its_own_missing_file(self):
        issues = (CheckIssue("error", "COVER_MISSING", "no cover", "preview/cover.jpg", 0),)
        output = str(self.repo / "cover.jpg")
        with patch("lib.theme_factory.cli.run_theme_checks", return_value=CheckReport("ERROR", "fixture", 4, issues)), \
                patch("tools.theme_cover.capture_cover") as capture:
            capture.return_value.to_human.return_value = "captured"
            code, stdout, _ = self.invoke("cover", "fixture", "--repo-root", str(self.repo), "--output", output)
        self.assertEqual(code, 0)
        self.assertIn("captured", stdout)
        capture.assert_called_once()

        with patch("lib.theme_factory.cli.run_theme_checks", return_value=self.report("ERROR")), \
                patch("tools.theme_cover.capture_cover") as capture:
            code, _, stderr = self.invoke("cover", "fixture", "--repo-root", str(self.repo), "--output", output)
        self.assertEqual(code, 2)
        self.assertIn("BROKEN", stderr)
        capture.assert_not_called()

    def test_names_that_could_leave_sample_themes_are_refused(self):
        with patch("lib.theme_factory.font_pipeline.install_font") as install:
            code, _, stderr = self.invoke(
                "font", "add", "../escape", "--repo-root", str(self.repo), "--family", "X",
                "--metadata-url", "https://example.invalid/m", "--source-revision", "abc", "--weights", "400",
            )
        self.assertEqual(code, 2)
        self.assertIn("must match", stderr)
        install.assert_not_called()
        code, _, stderr = self.invoke("package", "--repo-root", str(self.repo), "--theme", "../x",
                                      "--output-dir", str(self.repo / "dist"))
        self.assertEqual(code, 2)
        self.assertIn("must match", stderr)

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


class UnexpectedErrorTests(unittest.TestCase):
    ARGS = ["verify-package", "--package", "nowhere.zip"]

    def run_with_boom(self, env):
        import os
        stderr = io.StringIO()
        with patch.dict(os.environ, env), patch("lib.theme_factory.cli._handle_verify_package",
                                                  side_effect=RuntimeError("boom")), \
                contextlib.redirect_stderr(stderr):
            return stderr, run_cli(self.ARGS)

    def test_unexpected_error_is_one_line_by_default(self):
        import os
        with patch.dict(os.environ):
            os.environ.pop("THEME_FACTORY_DEBUG", None)
            stderr, code = self.run_with_boom({})
        self.assertEqual(code, 1)
        self.assertIn("Unexpected error: boom", stderr.getvalue())

    def test_debug_mode_re_raises_for_the_traceback(self):
        with self.assertRaises(RuntimeError):
            self.run_with_boom({"THEME_FACTORY_DEBUG": "1"})


if __name__ == "__main__":
    unittest.main()
