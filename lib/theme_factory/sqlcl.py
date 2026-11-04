"""Safe SQLcl boundary for preflight, export, validation, and import."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Optional

from lib.theme_factory.errors import PackageError

CONNECTION_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
WORKSPACE_RE = re.compile(r"^[A-Z][A-Z0-9_$#]{0,127}$")
DEFAULT_TIMEOUT_SECONDS = 1800
TIMEOUT_ENV = "THEME_FACTORY_SQLCL_TIMEOUT"
TRANSLATED_ON_26_1 = (
    "APEX 26.1 can't export an application with Application-Based translations to APEXLang (ORA-20987), so this "
    "script can't work on it. Nothing was changed. Install by hand (MANUAL-INSTALL.md), upgrade to APEX 26.2, or move "
    "the application to Text Message-Based translation."
)
TRANSLATION_SCRIPT = Path("generated-artifacts/translations.sql")
TRANSLATION_IF = "if wwv_imp_util.is_component_created("
TRANSLATION_SPLIT_RE = re.compile(
    r"^(" + re.escape(TRANSLATION_IF) + r"[^\n]*\) then)\nend;\n/\nbegin\n", re.MULTILINE
)


@dataclass(frozen=True)
class TargetMetadata:
    app_id: int
    alias: str
    name: str
    workspace: str
    apex_version: str
    translation_rows: int = 0


@dataclass(frozen=True)
class SqlclResult:
    returncode: int
    stdout: str
    stderr: str


def repair_translation_script(text: str) -> str:
    """Repair SQLcl's -exptranslations output so `apex import` can run it (SQLcl 26.3, pitfalls §3.10).

    SQLcl splits the script into blocks every 10,000 lines or so, and can split between `if ... then` and its body,
    which fails the whole import with PLS-00103. Move that `if` into the next block. A block that is still unbalanced
    is refused here, because the import would fail on it.
    """
    repaired = TRANSLATION_SPLIT_RE.sub(r"end;\n/\nbegin\n\1\n", text)
    for block in repaired.split("\n/\n"):
        lines = block.splitlines()
        if sum(line.startswith(TRANSLATION_IF) for line in lines) != lines.count("end if;"):
            raise PackageError(
                "SQLcl's translation export has a shape this installer can't repair. Install by hand "
                "(MANUAL-INSTALL.md), or pass --discard-translations and translate the application again.",
                exit_code=3,
            )
    return repaired


def unistr_literals(text: str, size: int = 200) -> list[str]:
    """`text` as unistr('...') literals of `size` characters at most. Only letters, digits and spaces stay as they
    are, so no quote, `&` or console code page can change the text on its way to the database."""
    data = text.encode("utf-16-be", "surrogatepass")
    units = [data[i:i + 2].decode("utf-16-be", "surrogatepass") for i in range(0, len(data), 2)]
    tokens = [unit if unit.isascii() and (unit.isalnum() or unit == " ") else f"\\{ord(unit):04X}" for unit in units]
    return [f"unistr('{''.join(tokens[i:i + size // 5])}')" for i in range(0, len(tokens), size // 5)]


def validate_workspace(workspace: str) -> None:
    if not isinstance(workspace, str) or not WORKSPACE_RE.match(workspace):
        raise PackageError(
            f"Invalid workspace name: '{workspace}'. Must match ^[A-Z][A-Z0-9_$#]{{0,127}}$"
        )


def sqlcl_path(path: Path) -> str:
    """A resolved path safe to embed in a double-quoted SQLcl argument: no quote, no line break,
    no control character, so a path can never end the argument or start a new SQLcl command."""
    text = str(Path(path).resolve())
    if any(ch == '"' or not ch.isprintable() for ch in text):
        raise PackageError(f"Unsupported path for SQLcl (quote or control character): {text!r}")
    return text


def validate_app_id(app_id: int) -> None:
    if not isinstance(app_id, int) or app_id <= 0:
        raise PackageError(f"Application ID must be a positive integer, got: {app_id}")


def default_timeout_seconds() -> int:
    """Each SQLcl call's limit: a kill during `apex import` can leave the application half replaced."""
    raw = os.environ.get(TIMEOUT_ENV, "")
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    if not raw.isdigit() or int(raw) <= 0:
        raise PackageError(f"{TIMEOUT_ENV} must be a positive number of seconds, got: {raw!r}")
    return int(raw)


class SqlclClient:
    def __init__(self, connection: str, timeout_seconds: Optional[int] = None, env: Optional[dict] = None) -> None:
        if not isinstance(connection, str) or not CONNECTION_RE.match(connection):
            raise PackageError(
                f"Invalid SQLcl connection name: '{connection}'. Must match ^[A-Za-z0-9_.-]{{1,128}}$"
            )
        self.connection = connection
        self.timeout_seconds = default_timeout_seconds() if timeout_seconds is None else timeout_seconds
        # Application-Based translations: exports carry the repository so an import doesn't empty it.
        self.keep_translations = False
        self.env = env  # None = inherit; tests inject a PATH with the fake `sql`

    def __repr__(self) -> str:
        return f"SqlclClient(connection='{self.connection}')"

    def _run_script(self, script: str) -> SqlclResult:
        try:
            path_env = self.env.get("PATH") if self.env else None
            sql_bin = shutil.which("sql", path=path_env)
            if not sql_bin:
                raise FileNotFoundError("SQLcl executable 'sql' not found in PATH")
            res = subprocess.run(
                [sql_bin, "-S", "-name", self.connection],
                input=script,
                text=True,
                errors="replace",  # Windows consoles report in their own code page, not UTF-8
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
                env=self.env,
            )
            return SqlclResult(res.returncode, res.stdout, res.stderr)
        except subprocess.TimeoutExpired as exc:
            raise PackageError(
                f"SQLcl execution timed out after {self.timeout_seconds} seconds; "
                f"set {TIMEOUT_ENV} to allow longer"
            ) from exc
        except FileNotFoundError as exc:
            raise PackageError("SQLcl executable 'sql' not found in PATH") from exc

    def preflight(self, workspace: str, app_id: int) -> TargetMetadata:
        validate_workspace(workspace)
        validate_app_id(app_id)

        script = "\n".join([
            "set heading off feedback off pagesize 0 verify off echo off",
            "whenever sqlerror exit failure",
            "select 'THEME_FACTORY_TARGET=' || json_object(",
            "           'appId' value a.application_id,",
            "           'alias' value a.alias,",
            "           'name' value a.application_name,",
            "           'workspace' value a.workspace,",
            "           'apexVersion' value r.version_no,",
            "           'translationRows' value (select count(*) from apex_application_trans_repos t",
            "                                    where t.application_id = a.application_id)",
            "         returning varchar2)",
            "  from apex_applications a",
            " cross join apex_release r",
            f" where a.application_id = to_number('{app_id}')",
            f"   and upper(a.workspace) = upper('{workspace}');",
            "exit",
        ]) + "\n"

        result = self._run_script(script)
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            raise PackageError(f"SQLcl preflight failed (code {result.returncode}): {err}")

        prefix = "THEME_FACTORY_TARGET="
        target_lines = [
            line.strip() for line in result.stdout.splitlines() if line.strip().startswith(prefix)
        ]

        if not target_lines:
            raise PackageError(
                f"Application {app_id} not found in workspace {workspace} or target query returned no rows"
            )
        if len(target_lines) > 1:
            raise PackageError(f"Expected 1 target row, got {len(target_lines)}")

        raw_json = target_lines[0][len(prefix):]
        try:
            data = json.loads(raw_json)
            return TargetMetadata(
                app_id=int(data["appId"]),
                alias=str(data.get("alias") or ""),
                name=str(data.get("name") or ""),
                workspace=str(data["workspace"]),
                apex_version=str(data["apexVersion"]),
                translation_rows=int(data.get("translationRows") or 0),
            )
        except Exception as exc:
            raise PackageError(f"Failed to parse preflight target JSON: {raw_json}") from exc

    def export_apexlang(self, app_id: int, dest_dir: Path) -> Path:
        validate_app_id(app_id)
        dest_dir = Path(sqlcl_path(dest_dir))
        dest_dir.mkdir(parents=True, exist_ok=True)

        translations = " -exptranslations" if self.keep_translations else ""
        script = "\n".join([
            "whenever sqlerror exit failure",
            f'apex export -applicationid {app_id} -exptype APEXLANG -split -dir "{dest_dir}" -skipexportdate '
            f"-overwrite-files{translations}",
            "exit",
        ]) + "\n"

        result = self._run_script(script)
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            if "Translation Repository" in err:
                raise PackageError(TRANSLATED_ON_26_1, exit_code=3)
            raise PackageError(f"SQLcl export failed (code {result.returncode}): {err}")

        # Discover directory containing application.apx
        candidates = [
            child for child in dest_dir.iterdir()
            if child.is_dir() and (child / "application.apx").exists()
        ]
        if not candidates:
            # Maybe dest_dir itself has application.apx
            if (dest_dir / "application.apx").exists():
                candidates = [dest_dir]
            else:
                raise PackageError(f"No APEXLang export containing application.apx found in {dest_dir}")
        if len(candidates) > 1:
            names = ", ".join(c.name for c in candidates)
            raise PackageError(f"Multiple APEXLang application directories found in {dest_dir}: {names}")

        if self.keep_translations:
            script_path = candidates[0] / TRANSLATION_SCRIPT
            if not script_path.is_file():
                raise PackageError(
                    "SQLcl did not export this application's translations. Install by hand (MANUAL-INSTALL.md), or "
                    "pass --discard-translations and translate the application again.",
                    exit_code=3,
                )
            script_path.write_text(repair_translation_script(script_path.read_text(encoding="utf-8")),
                                   encoding="utf-8", newline="\n")
        return candidates[0]

    def read_translations(self, app_id: int) -> list[dict]:
        """Every row of the translation repository. Printed in ASCII and in marked chunks, so neither a console code
        page nor SQLcl trimming a line can change the text."""
        validate_app_id(app_id)
        script = "\n".join([
            "set serveroutput on",
            "set feedback off",
            "whenever sqlerror exit failure",
            "declare",
            "  l_rows pls_integer := 0;",
            "begin",
            "  dbms_output.enable(null);",
            "  for r in (select json_serialize(json_object('id' value to_char(id), 'fromId' value to_char(from_id),",
            "                     'column' value internal_column_id, 'path' value internal_column_json_path,",
            "                     'lang' value language_code, 'from' value from_string, 'to' value to_string",
            "                     returning clob) returning clob ascii) line",
            f"              from apex_application_trans_repos where application_id = {app_id}) loop",
            "    for i in 0 .. trunc((dbms_lob.getlength(r.line) - 1) / 4000) loop",
            "      dbms_output.put_line('TF_CHUNK ' || dbms_lob.substr(r.line, 4000, i * 4000 + 1) || '|');",
            "    end loop;",
            "    dbms_output.put_line('TF_ROW_END');",
            "    l_rows := l_rows + 1;",
            "  end loop;",
            "  dbms_output.put_line('THEME_FACTORY_TRANSLATIONS=' || l_rows);",
            "end;",
            "/",
            "exit",
        ]) + "\n"
        result = self._run_script(script)
        rows: list[dict] = []
        chunks: list[str] = []
        expected = None
        for line in result.stdout.split("\n"):
            line = line.rstrip("\r")
            if line.startswith("TF_CHUNK ") and line.endswith("|"):
                chunks.append(line[len("TF_CHUNK "):-1])
            elif line == "TF_ROW_END":
                rows.append(json.loads("".join(chunks)))
                chunks = []
            elif line.startswith("THEME_FACTORY_TRANSLATIONS="):
                expected = int(line.partition("=")[2])
        if result.returncode != 0 or expected != len(rows):
            err = result.stderr.strip() or result.stdout.strip()[-1000:]
            raise PackageError(f"Reading the translations failed: {err}")
        return rows

    def _for_each_language(self, workspace: str, app_id: int, call: str, sentinel: str) -> None:
        validate_workspace(workspace)
        validate_app_id(app_id)
        script = "\n".join([
            "set serveroutput on feedback off",
            "whenever sqlerror exit failure",
            "declare",
            "  l_workspace_id number;",
            "begin",
            f"  select workspace_id into l_workspace_id from apex_workspaces where upper(workspace) = upper('{workspace}');",
            "  apex_util.set_security_group_id(l_workspace_id);",
            "  for language_map in (select translated_app_language language_code from apex_application_trans_map",
            f"                       where primary_application_id = {app_id}) loop",
            f"    {call}(p_application_id => {app_id}, p_language => language_map.language_code);",
            "  end loop;",
            "  commit;",
            f"  dbms_output.put_line('{sentinel}');",
            "end;",
            "/",
            "exit",
        ]) + "\n"
        result = self._run_script(script)
        if result.returncode != 0 or sentinel not in result.stdout:
            err = result.stderr.strip() or result.stdout.strip()
            raise PackageError(f"{call} failed: {err}")

    def seed_translations(self, workspace: str, app_id: int) -> None:
        """Seeding keeps existing translated text. It only adds what is new."""
        self._for_each_language(workspace, app_id, "apex_lang.seed_translations", "THEME_FACTORY_SEEDED")

    def publish_translations(self, workspace: str, app_id: int) -> None:
        """An import leaves translated applications unpublished."""
        self._for_each_language(workspace, app_id, "apex_lang.publish_application", "THEME_FACTORY_PUBLISHED")

    def write_translations(self, workspace: str, updates: list[tuple[str, str, str]]) -> None:
        """Set the translated text of (row id, language, text) in one transaction."""
        validate_workspace(workspace)
        lines = [
            "set serveroutput on",
            "set feedback off",
            "set define off",
            "whenever sqlerror exit failure rollback",
            "declare",
            "  l_workspace_id number;",
            "begin",
            f"  select workspace_id into l_workspace_id from apex_workspaces where upper(workspace) = upper('{workspace}');",
            "  apex_util.set_security_group_id(l_workspace_id);",
            "end;",
            "/",
        ]
        for row_id, language, text in updates:
            if not re.fullmatch(r"\d+", row_id) or not re.fullmatch(r"[A-Za-z-]{1,30}", language):
                raise PackageError(f"Unexpected translation row: {row_id} {language}")
            literals = unistr_literals(text)
            lines += ["declare", "  l_text varchar2(32767);", "begin"]
            lines += [f"  l_text := l_text || {literal};" for literal in literals]
            lines += [
                f"  apex_lang.update_translated_string(p_id => {row_id}, p_language => '{language}', p_string => l_text);",
                "end;",
                "/",
            ]
        lines += ["commit;", "exec dbms_output.put_line('THEME_FACTORY_WRITTEN')", "exit"]
        result = self._run_script("\n".join(lines) + "\n")
        if result.returncode != 0 or "THEME_FACTORY_WRITTEN" not in result.stdout:
            err = result.stderr.strip() or result.stdout.strip()[-1000:]
            raise PackageError(f"Putting the translations back failed: {err}")

    def validate(self, apexlang_dir: Path, workspace: str) -> None:
        validate_workspace(workspace)
        apexlang_dir = Path(sqlcl_path(apexlang_dir))

        script = "\n".join([
            "whenever sqlerror exit failure",
            f'apex validate -input "{apexlang_dir}" -workspace "{workspace}"',
            "exit",
        ]) + "\n"

        result = self._run_script(script)
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            raise PackageError(f"APEXLang validation failed (code {result.returncode}): {err}")

        combined = f"{result.stdout}\n{result.stderr}"
        for line in combined.splitlines():
            clean = line.strip()
            if clean.startswith("WARNING") or clean.startswith("ERROR"):
                raise PackageError(f"APEXLang validation reported an issue: {clean}")

        if "validation" not in combined.lower() or "success" not in combined.lower():
            raise PackageError(f"APEXLang validation did not confirm success:\n{combined.strip()}")

    def import_apexlang(self, apexlang_dir: Path, workspace: str, confirmed_app_id: int) -> None:
        validate_workspace(workspace)
        validate_app_id(confirmed_app_id)
        apexlang_dir = Path(sqlcl_path(apexlang_dir))
        # `whenever sqlerror` does not stop the script after a failed `apex validate` (probe
        # 2026-09-23: three compile errors, the next statement still ran, exit 0), so refuse
        # here first; the import session still validates in-session.
        self.validate(apexlang_dir, workspace)

        script = "\n".join([
            "whenever sqlerror exit failure",
            f'apex validate -input "{apexlang_dir}" -workspace "{workspace}"',
            f'apex import -input "{apexlang_dir}" -workspace "{workspace}" -id {confirmed_app_id}',
            "exit",
        ]) + "\n"

        result = self._run_script(script)
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            raise PackageError(f"APEXLang import failed (code {result.returncode}): {err}")

        combined = f"{result.stdout}\n{result.stderr}"
        for line in combined.splitlines():
            clean = line.strip()
            if clean.startswith("ERROR") or (clean.startswith("WARNING") and "validation" in clean.lower()):
                raise PackageError(f"APEXLang import reported an issue: {clean}")
        # SQLcl exits 0 and prints "APEXlang Import Errors:" when a PL/SQL step of the import fails (pitfalls §3.10).
        if "import errors" in combined.lower() or "import successful" not in combined.lower():
            raise PackageError(f"APEXLang import did not confirm success:\n{combined.strip()}")
