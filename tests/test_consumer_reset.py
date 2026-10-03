import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


def find_bash() -> str:
    if sys.platform == "win32":
        for b in [shutil.which("bash"), shutil.which("bash.exe")]:
            if b and "system32" not in b.lower():
                return b
        git = shutil.which("git")
        if git:
            for parent in Path(git).resolve().parents:
                for rel in ("bin/bash.exe", "usr/bin/bash.exe"):
                    cand = parent / rel
                    if cand.exists():
                        return str(cand)
        for cand in [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"]:
            if Path(cand).exists():
                return cand
    return "bash"


class ConsumerResetScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log = self.tmp / "sql.log"
        self.env = os.environ.copy()
        self.env["PATH"] = f"{Path.cwd() / 'tests/fixtures/bin'}{os.pathsep}{self.env.get('PATH', '')}"
        self.env["FAKE_SQL_LOG"] = str(self.log)
        self.env["FAKE_SQL_STATE_FILE"] = str(self.tmp / "state")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_reset(self, *args, existing="", stdin=""):
        env = dict(self.env, FAKE_SQL_EXISTING_APPS=existing)
        cmd = [find_bash(), "scripts/reset-consumer.sh"] if sys.platform == "win32" else ["scripts/reset-consumer.sh"]
        return subprocess.run([*cmd, "--connection", "demo", *args],
                              input=stdin, text=True, capture_output=True, env=env, check=False)

    def sql_log(self):
        return self.log.read_text(encoding="utf-8") if self.log.exists() else ""

    def test_id_outside_the_disposable_range_is_refused_before_sqlcl(self):
        result = self.run_reset("--app-id", "102", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("9000-9099", result.stderr)
        self.assertEqual(self.sql_log(), "")

    def test_id_used_by_another_app_is_never_overwritten(self):
        result = self.run_reset("--app-id", "9010", "--yes", existing="9010:SOMETHING-ELSE")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SOMETHING-ELSE", result.stderr)
        self.assertNotIn("apex import", self.sql_log())

    def test_existing_consumer_is_reimported_clean(self):
        result = self.run_reset("--yes", existing="9010:TF-CONSUMER-MINIMAL-9010")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("apex import -input", self.sql_log())
        self.assertIn("-id 9010 -alias TF-CONSUMER-MINIMAL-9010", self.sql_log())
        self.assertIn("status=RESET", result.stdout)

    def test_missing_consumer_is_created(self):
        result = self.run_reset("--yes")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("-id 9010 -alias TF-CONSUMER-MINIMAL-9010", self.sql_log())

    def test_declined_confirmation_imports_nothing(self):
        result = self.run_reset(existing="9010:TF-CONSUMER-MINIMAL-9010", stdin="n\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("apex import", self.sql_log())


if __name__ == "__main__":
    unittest.main()
