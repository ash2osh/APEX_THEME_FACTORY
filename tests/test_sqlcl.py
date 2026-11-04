import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from lib.theme_factory.errors import PackageError
from lib.theme_factory.sqlcl import SqlclClient, SqlclResult, repair_translation_script, unistr_literals


class SqlclTests(unittest.TestCase):
    def setUp(self):
        self.fake_bin = str((Path(__file__).resolve().parent / "fixtures/bin").resolve())
        self.orig_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.fake_bin}{os.pathsep}{self.orig_path}"

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

    def test_timeout_comes_from_the_environment_and_rejects_nonsense(self):
        with patch.dict(os.environ, {"THEME_FACTORY_SQLCL_TIMEOUT": "7200"}):
            self.assertEqual(SqlclClient("demo").timeout_seconds, 7200)
        with patch.dict(os.environ, {"THEME_FACTORY_SQLCL_TIMEOUT": "soon"}):
            with self.assertRaisesRegex(PackageError, "THEME_FACTORY_SQLCL_TIMEOUT"):
                SqlclClient("demo")
        with patch.dict(os.environ):
            os.environ.pop("THEME_FACTORY_SQLCL_TIMEOUT", None)
            self.assertEqual(SqlclClient("demo").timeout_seconds, 1800)

    def test_import_needs_sqlcl_to_confirm_success(self):
        failed = SqlclResult(0, "Importing application ID: 314\nAPEXlang Import Errors:\nType: PLSQL_ERROR\n", "")
        silent = SqlclResult(0, "", "")
        passed = SqlclResult(0, "Importing application ID: 314\nImport successful.\n", "")
        client = SqlclClient("demo")
        with patch.object(client, "validate"):
            for result in (failed, silent):
                with patch.object(client, "_run_script", return_value=result):
                    with self.assertRaisesRegex(PackageError, "did not confirm success"):
                        client.import_apexlang(Path("tests/fixtures/apexlang/minimal"), "DEMO", 314)
            with patch.object(client, "_run_script", return_value=passed):
                client.import_apexlang(Path("tests/fixtures/apexlang/minimal"), "DEMO", 314)

    def test_translation_script_split_is_repaired(self):
        call = "wwv_flow_imp_shared.create_translation(\n p_id=>null\n);\nend if;\n"
        if_line = "if wwv_imp_util.is_component_created(1,wwv_flow_t_varchar2('a'),null,null) then\n"
        broken = f"begin\n{if_line}{call}{if_line}end;\n/\nbegin\n{call}end;\n/\n"
        repaired = repair_translation_script(broken)
        self.assertEqual(repaired, f"begin\n{if_line}{call}end;\n/\nbegin\n{if_line}{call}end;\n/\n")
        self.assertEqual(repair_translation_script(repaired), repaired, "a repaired script stays as it is")

    def test_translation_script_that_stays_unbalanced_is_refused(self):
        if_line = "if wwv_imp_util.is_component_created(1,wwv_flow_t_varchar2('a'),null,null) then\n"
        with self.assertRaises(PackageError) as refused:
            repair_translation_script(f"begin\n{if_line}end;\n/\n")
        self.assertEqual(refused.exception.exit_code, 3)

    def test_unistr_literals_survive_quotes_ampersands_and_any_language(self):
        text = "l'é « &ITEM. » \\ \n😀 Status"
        literals = unistr_literals(text, size=20)
        joined = "".join(literal[len("unistr('"):-len("')")] for literal in literals)
        self.assertTrue(joined.isascii())
        self.assertNotIn("'", joined)
        self.assertNotIn("&", joined)
        self.assertTrue(all(len(literal) <= 20 + len("unistr('')") for literal in literals))
        # What Oracle's UNISTR does: every \\XXXX is one UTF-16 unit.
        decoded = re.sub(r"\\([0-9A-F]{4})", lambda m: chr(int(m[1], 16)), joined)
        self.assertEqual(decoded.encode("utf-16", "surrogatepass").decode("utf-16"), text)

    def test_read_translations_rejoins_chunks_and_keeps_edge_spaces(self):
        row = '{"id":"1","fromId":"2","column":14,"lang":"fr","from":"Status ","to":" \\u00C9tat "}'
        out = f"TF_CHUNK {row[:30]}|\r\nTF_CHUNK {row[30:]}|\nTF_ROW_END\nTHEME_FACTORY_TRANSLATIONS=1\n"
        client = SqlclClient("demo")
        with patch.object(client, "_run_script", return_value=SqlclResult(0, out, "")):
            self.assertEqual(client.read_translations(314)[0]["to"], " État ")
        with patch.object(client, "_run_script", return_value=SqlclResult(0, out.replace("=1", "=2"), "")):
            with self.assertRaises(PackageError):
                client.read_translations(314)

    def test_apex_26_1_refusing_translated_text_is_explained(self):
        refusal = SqlclResult(2, "ORA-20987: APEX - This application contains translated text in the "
                                 "<strong>Translation Repository</strong>, which is not supported", "")
        client = SqlclClient("demo")
        with tempfile.TemporaryDirectory() as tmp, patch.object(client, "_run_script", return_value=refusal):
            with self.assertRaises(PackageError) as refused:
                client.export_apexlang(314, Path(tmp) / "export")
        self.assertEqual(refused.exception.exit_code, 3)
        self.assertIn("MANUAL-INSTALL.md", str(refused.exception))

    def test_export_asks_for_translations_only_when_keeping_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            client = SqlclClient("demo")
            with patch.dict(os.environ, {"FAKE_SQL_LOG": str(log), "FAKE_SQL_MODE": "success"}):
                client.export_apexlang(314, Path(tmp) / "plain")
                self.assertNotIn("-exptranslations", log.read_text(encoding="utf-8"))
                client.keep_translations = True
                with self.assertRaises(PackageError) as missing:
                    client.export_apexlang(314, Path(tmp) / "kept")  # the fake SQLcl writes no translations
            self.assertIn("-exptranslations", log.read_text(encoding="utf-8"))
            self.assertEqual(missing.exception.exit_code, 3)

    def test_workspace_validation(self):
        client = SqlclClient("demo")
        with tempfile.TemporaryDirectory():
            with self.assertRaises(PackageError):
                client.preflight("demo", 102)  # Lowercase not allowed
            with self.assertRaises(PackageError):
                client.preflight("123INVALID", 102)  # Must start with uppercase letter
            with self.assertRaises(PackageError):
                client.preflight("DEMO;DROP", 102)

    def test_app_id_validation(self):
        client = SqlclClient("demo")
        with tempfile.TemporaryDirectory():
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


class SqlclPathTests(unittest.TestCase):
    def test_paths_that_could_break_out_of_a_quoted_argument_are_refused(self):
        from lib.theme_factory.sqlcl import sqlcl_path
        self.assertTrue(sqlcl_path(Path("/tmp/backups/DEMO-1")).endswith("DEMO-1"))
        for bad in ('/tmp/x" -overwrite-files', "/tmp/x\napex import -input /evil", "/tmp/x\rb"):
            with self.assertRaises(PackageError, msg=repr(bad)):
                sqlcl_path(Path(bad))
