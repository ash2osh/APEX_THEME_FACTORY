import os
import subprocess
import unittest
from pathlib import Path


class ConsumerFixtureScriptTests(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.copy()
        self.env["PATH"] = f"{Path.cwd() / 'tests/fixtures/bin'}:{self.env.get('PATH', '')}"

    def test_dry_run_never_imports(self):
        result = subprocess.run(
            [
                "scripts/provision-consumer-fixtures.sh",
                "--connection", "demo",
                "--workspace", "DEMO",
                "--minimal-id", "9010",
                "--business-id", "9011",
            ],
            text=True, capture_output=True, env=self.env, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PROVISIONING DRY RUN", result.stdout)
        # Verify fake sql received no apex import command in dry-run
        fake_log = self.env.get("FAKE_SQL_LOG")
        if fake_log and Path(fake_log).exists():
            log_content = Path(fake_log).read_text(encoding="utf-8")
            self.assertNotIn("apex import", log_content)

    def test_ids_outside_range_fails(self):
        # 8999 is outside 9000-9099
        result = subprocess.run(
            [
                "scripts/provision-consumer-fixtures.sh",
                "--connection", "demo",
                "--workspace", "DEMO",
                "--minimal-id", "8999",
                "--business-id", "9010",
            ],
            text=True, capture_output=True, env=self.env, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("9000-9099", result.stderr + result.stdout)

        # 9100 is outside 9000-9099
        result2 = subprocess.run(
            [
                "scripts/provision-consumer-fixtures.sh",
                "--connection", "demo",
                "--workspace", "DEMO",
                "--minimal-id", "9010",
                "--business-id", "9100",
            ],
            text=True, capture_output=True, env=self.env, check=False,
        )
        self.assertNotEqual(result2.returncode, 0)
        self.assertIn("9000-9099", result2.stderr + result2.stdout)

    def test_collision_refusal(self):
        env = self.env.copy()
        env["FAKE_SQL_OCCUPIED_IDS"] = "9010"
        result = subprocess.run(
            [
                "scripts/provision-consumer-fixtures.sh",
                "--connection", "demo",
                "--workspace", "DEMO",
                "--minimal-id", "9010",
                "--business-id", "9011",
            ],
            text=True, capture_output=True, env=env, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("collision", (result.stderr + result.stdout).lower())

    def test_exact_id_confirmation_required_for_apply(self):
        # Missing confirm-ids
        result = subprocess.run(
            [
                "scripts/provision-consumer-fixtures.sh",
                "--connection", "demo",
                "--workspace", "DEMO",
                "--minimal-id", "9010",
                "--business-id", "9011",
                "--apply",
            ],
            text=True, capture_output=True, env=self.env, check=False,
        )
        self.assertNotEqual(result.returncode, 0)

        # Mismatched confirm-ids
        result_mismatch = subprocess.run(
            [
                "scripts/provision-consumer-fixtures.sh",
                "--connection", "demo",
                "--workspace", "DEMO",
                "--minimal-id", "9010",
                "--business-id", "9011",
                "--apply",
                "--confirm-ids", "9010,9099",
            ],
            text=True, capture_output=True, env=self.env, check=False,
        )
        self.assertNotEqual(result_mismatch.returncode, 0)

    def test_apply_with_exact_confirmation_succeeds(self):
        result = subprocess.run(
            [
                "scripts/provision-consumer-fixtures.sh",
                "--connection", "demo",
                "--workspace", "DEMO",
                "--minimal-id", "9010",
                "--business-id", "9011",
                "--apply",
                "--confirm-ids", "9010,9011",
            ],
            text=True, capture_output=True, env=self.env, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("PROVISIONING status=PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
