import subprocess
import tempfile
import unittest
from pathlib import Path

from lib.theme_factory.checks import CheckReport
from lib.theme_factory.dev import DevOptions, run_dev


class ThemeDevTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        (self.repo / "scripts").mkdir()
        self.commands = []
        self.opened = []

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def check(status: str = "PASS") -> CheckReport:
        return CheckReport(status, "fixture", False, 1, "a" * 64, ())

    def runner(self, command, cwd):
        self.commands.append((tuple(command), Path(cwd)))
        return subprocess.CompletedProcess(command, 0, "ok", "")

    def opener(self, url):
        self.opened.append(url)
        return {"pageId": 7}

    def test_plain_dev_only_runs_theme_checks(self):
        report = run_dev(
            DevOptions(self.repo, "fixture"),
            check_runner=lambda *_: self.check(),
            command_runner=self.runner,
            browser_opener=self.opener,
        )
        self.assertEqual(report.status, "PASS")
        self.assertEqual(self.commands, [])
        self.assertEqual(self.opened, [])
        self.assertEqual([step.name for step in report.steps], ["check"])

    def test_sync_and_validate_run_exactly_those_commands(self):
        report = run_dev(
            DevOptions(self.repo, "fixture", sync=True, validate=True),
            check_runner=lambda *_: self.check(),
            command_runner=self.runner,
            browser_opener=self.opener,
        )
        self.assertEqual(report.status, "PASS")
        self.assertEqual(
            [command for command, _ in self.commands],
            [
                (str(self.repo / "scripts/sync-static.sh"),),
                (str(self.repo / "scripts/apex-validate.sh"),),
            ],
        )

    def test_import_requires_apply_even_for_direct_api_call(self):
        with self.assertRaisesRegex(ValueError, "--apply"):
            run_dev(
                DevOptions(self.repo, "fixture", import_app=True),
                check_runner=lambda *_: self.check(),
                command_runner=self.runner,
                browser_opener=self.opener,
            )

    def test_validation_failure_prevents_import_and_open(self):
        def failing_runner(command, cwd):
            self.commands.append((tuple(command), Path(cwd)))
            if command[0].endswith("apex-validate.sh"):
                return subprocess.CompletedProcess(command, 1, "", "compile failed")
            return subprocess.CompletedProcess(command, 0, "ok", "")

        report = run_dev(
            DevOptions(
                self.repo, "fixture", validate=True, import_app=True,
                apply=True, open_browser=True,
            ),
            check_runner=lambda *_: self.check(),
            command_runner=failing_runner,
            browser_opener=self.opener,
        )
        self.assertEqual(report.status, "ERROR")
        self.assertEqual(len(self.commands), 1)
        self.assertTrue(self.commands[0][0][0].endswith("apex-validate.sh"))
        self.assertEqual(self.opened, [])
        self.assertIn("compile failed", report.steps[-1].output)


if __name__ == "__main__":
    unittest.main()
