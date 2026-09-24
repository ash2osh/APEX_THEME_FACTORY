"""Safe SQLcl boundary for preflight, export, validation, and import."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Optional

from lib.theme_factory.errors import PackageError

CONNECTION_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
WORKSPACE_RE = re.compile(r"^[A-Z][A-Z0-9_$#]{0,127}$")


@dataclass(frozen=True)
class TargetMetadata:
    app_id: int
    alias: str
    name: str
    workspace: str
    apex_version: str


@dataclass(frozen=True)
class SqlclResult:
    returncode: int
    stdout: str
    stderr: str


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


class SqlclClient:
    def __init__(self, connection: str, timeout_seconds: int = 300, env: Optional[dict] = None) -> None:
        if not isinstance(connection, str) or not CONNECTION_RE.match(connection):
            raise PackageError(
                f"Invalid SQLcl connection name: '{connection}'. Must match ^[A-Za-z0-9_.-]{{1,128}}$"
            )
        self.connection = connection
        self.timeout_seconds = timeout_seconds
        self.env = env  # None = inherit; tests inject a PATH with the fake `sql`

    def __repr__(self) -> str:
        return f"SqlclClient(connection='{self.connection}')"

    def _run_script(self, script: str) -> SqlclResult:
        try:
            res = subprocess.run(
                ["sql", "-S", "-name", self.connection],
                input=script,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
                env=self.env,
            )
            return SqlclResult(res.returncode, res.stdout, res.stderr)
        except subprocess.TimeoutExpired as exc:
            raise PackageError(f"SQLcl execution timed out after {self.timeout_seconds} seconds") from exc
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
            "           'apexVersion' value r.version_no",
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
            )
        except Exception as exc:
            raise PackageError(f"Failed to parse preflight target JSON: {raw_json}") from exc

    def export_apexlang(self, app_id: int, dest_dir: Path) -> Path:
        validate_app_id(app_id)
        dest_dir = Path(sqlcl_path(dest_dir))
        dest_dir.mkdir(parents=True, exist_ok=True)

        script = "\n".join([
            "whenever sqlerror exit failure",
            f'apex export -applicationid {app_id} -exptype APEXLANG -split -dir "{dest_dir}" -skipexportdate -overwrite-files',
            "exit",
        ]) + "\n"

        result = self._run_script(script)
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            raise PackageError(f"SQLcl export failed (code {result.returncode}): {err}")

        # Discover directory containing application.apx
        candidates = [
            child for child in dest_dir.iterdir()
            if child.is_dir() and (child / "application.apx").exists()
        ]
        if not candidates:
            # Maybe dest_dir itself has application.apx
            if (dest_dir / "application.apx").exists():
                return dest_dir
            raise PackageError(f"No APEXLang export containing application.apx found in {dest_dir}")
        if len(candidates) > 1:
            names = ", ".join(c.name for c in candidates)
            raise PackageError(f"Multiple APEXLang application directories found in {dest_dir}: {names}")

        return candidates[0]

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
