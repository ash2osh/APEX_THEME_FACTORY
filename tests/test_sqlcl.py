import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from lib.theme_factory.errors import PackageError
from lib.theme_factory.sqlcl import SqlclClient, TargetMetadata


class SqlclTests(unittest.TestCase):
    def setUp(self):
        self.fake_bin = str((Path(__file__).resolve().parent / "fixtures/bin").resolve())
        self.orig_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.fake_bin}:{self.orig_path}"

    def tearDown(self):
        os.environ["PATH"] = self.orig_path

    def test_connection_name_validation(self):
        # Valid names
        client = SqlclClient("demo-connection_1.0")
        self.assertEqual(client.connection, "demo-connection_1.0")

        # Invalid names
        with self.assertRaises(PackageError):
            SqlclClient("bad connection; rm -rf")
        with self.assertRaises(PackageError):
            SqlclClient("")
        with self.assertRaises(PackageError):
            SqlclClient("a" * 129)

    def test_workspace_validation(self):
        client = SqlclClient("demo")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PackageError):
                client.preflight("demo", 102)  # Lowercase not allowed
            with self.assertRaises(PackageError):
                client.preflight("123INVALID", 102)  # Must start with uppercase letter
            with self.assertRaises(PackageError):
                client.preflight("DEMO;DROP", 102)

    def test_app_id_validation(self):
        client = SqlclClient("demo")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PackageError):
                client.preflight("DEMO", -1)
            with self.assertRaises(PackageError):
                client.preflight("DEMO", 0)

    def test_export_uses_exact_application_id_and_skip_export_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            with patch.dict(os.environ, {"FAKE_SQL_LOG": str(log), "FAKE_SQL_MODE": "success"}):
                app_dir = SqlclClient("demo-connection").export_apexlang(314, Path(tmp) / "export")
            call = log.read_text(encoding="utf-8")
            self.assertIn("apex export -applicationid 314", call)
            self.assertIn("-exptype APEXLANG", call)
            self.assertIn("-skipexportdate", call.lower())
            self.assertTrue(app_dir.exists())
            self.assertTrue((app_dir / "application.apx").exists())

    def test_export_duplicate_alias_directory_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            with patch.dict(os.environ, {"FAKE_SQL_LOG": str(log), "FAKE_SQL_MODE": "export-two-aliases"}):
                with self.assertRaises(PackageError) as ctx:
                    SqlclClient("demo-connection").export_apexlang(314, Path(tmp) / "export")
                self.assertIn("Multiple", str(ctx.exception))

    def test_preflight_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            with patch.dict(os.environ, {"FAKE_SQL_LOG": str(log), "FAKE_SQL_MODE": "success"}):
                meta = SqlclClient("demo").preflight("DEMO", 314)
            self.assertEqual(meta.app_id, 314)
            self.assertEqual(meta.alias, "FIXTURE_APP")
            self.assertEqual(meta.workspace, "DEMO")
            self.assertEqual(meta.apex_version, "26.1.0")

    def test_preflight_connection_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            with patch.dict(os.environ, {"FAKE_SQL_LOG": str(log), "FAKE_SQL_MODE": "connection-failure"}):
                with self.assertRaises(PackageError) as ctx:
                    SqlclClient("demo").preflight("DEMO", 314)
                self.assertIn("ORA-17820", str(ctx.exception))

    def test_validation_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            with patch.dict(os.environ, {"FAKE_SQL_LOG": str(log), "FAKE_SQL_MODE": "success"}):
                SqlclClient("demo").validate(Path("tests/fixtures/apexlang/minimal"), "DEMO")

    def test_validation_warning_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            with patch.dict(os.environ, {"FAKE_SQL_LOG": str(log), "FAKE_SQL_MODE": "validation-warning"}):
                with self.assertRaises(PackageError) as ctx:
                    SqlclClient("demo").validate(Path("tests/fixtures/apexlang/minimal"), "DEMO")
                self.assertIn("warning", str(ctx.exception).lower())

    def test_import_runs_validation_and_import_in_one_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            with patch.dict(os.environ, {"FAKE_SQL_LOG": str(log), "FAKE_SQL_MODE": "success"}):
                SqlclClient("demo").import_apexlang(Path("tests/fixtures/apexlang/minimal"), "DEMO", 314)
            call = log.read_text(encoding="utf-8")
            self.assertIn("whenever sqlerror exit failure", call)
            self.assertIn("apex validate", call)
            self.assertIn("apex import", call)
            self.assertIn("-id 314", call)

    def test_import_is_never_attempted_after_a_validation_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            env = {"FAKE_SQL_LOG": str(log), "FAKE_SQL_MODE": "validation-warning",
                   "FAKE_SQL_STATE_FILE": str(Path(tmp) / "state")}
            with patch.dict(os.environ, env):
                with self.assertRaises(PackageError):
                    SqlclClient("demo").import_apexlang(Path("tests/fixtures/apexlang/minimal"), "DEMO", 314)
            self.assertNotIn("apex import", log.read_text(encoding="utf-8"))

    def test_masked_logs_no_secrets(self):
        client = SqlclClient("secret_conn")
        # Ensure string representation doesn't expose sensitive info if any
        self.assertEqual(str(client), "SqlclClient(connection='secret_conn')")
