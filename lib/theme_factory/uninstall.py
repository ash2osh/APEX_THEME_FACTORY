"""Uninstall and backup restore operations for APEX Theme Factory."""

from dataclasses import dataclass
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import List, Optional, Tuple

from lib.theme_factory.apexlang import (
    canonical_digest,
    inspect_export,
    TargetExport,
)
from lib.theme_factory.errors import PackageError
from lib.theme_factory.install import OperationReport
from lib.theme_factory.sqlcl import SqlclClient, TargetMetadata


@dataclass(frozen=True)
class UninstallOptions:
    theme_name: str
    connection: str
    workspace: str
    app_id: int
    backup_dir: Optional[Path] = None
    apply: bool = False


@dataclass(frozen=True)
class RestoreOptions:
    connection: str
    workspace: str
    app_id: int
    backup_dir: Path
    apply: bool = False


def choose_fallback(current_default: Optional[str], remaining: Tuple[str, ...] | List[str]) -> str:
    rem = sorted(remaining)
    if current_default and current_default in rem:
        return current_default
    if rem:
        return rem[0]
    return "iris"


def _remove_theme_from_static_files(static_files_apx: Path, prefix: str) -> None:
    if not static_files_apx.exists():
        return
    content = static_files_apx.read_text(encoding="utf-8")
    # File block pattern: file "prefix/..." (...)
    pattern = re.compile(
        r'\n[ \t]*file[ \t]+"' + re.escape(prefix) + r'[^"]*"[ \t]*\([^\)]*\)',
        re.MULTILINE | re.DOTALL,
    )
    new_content = pattern.sub("", content)
    static_files_apx.write_text(new_content, encoding="utf-8")


def _remove_theme_from_app_css(app_apx: Path, theme_name: str) -> None:
    if not app_apx.exists():
        return
    content = app_apx.read_text(encoding="utf-8")
    # In css { fileUrls: [ ... ] }
    pattern = re.compile(
        r'([ \t]*)#[APP_FILES#]*theme-factory/packages/' + re.escape(theme_name) + r'/[^,\n\]]+,?[ \t]*\n?',
    )
    new_content = pattern.sub("", content)
    app_apx.write_text(new_content, encoding="utf-8")


def _remove_runtime_from_app(app_apx: Path) -> None:
    if not app_apx.exists():
        return
    content = app_apx.read_text(encoding="utf-8")
    pattern = re.compile(
        r'([ \t]*)#[APP_FILES#]*theme-factory/runtime/[^,\n\]]+,?[ \t]*\n?',
    )
    new_content = pattern.sub("", content)
    app_apx.write_text(new_content, encoding="utf-8")


def _remove_managed_page_zero_regions(p0_path: Path) -> None:
    if not p0_path.exists():
        return
    content = p0_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'\n[ \t]*region[ \t]+"Theme Factory Bootstrap[^"]*"[ \t]*\([^\)]*\)',
        re.MULTILINE | re.DOTALL,
    )
    new_content = pattern.sub("", content)
    p0_path.write_text(new_content, encoding="utf-8")


def _remove_managed_nav_entries(nav_path: Path) -> None:
    if not nav_path or not nav_path.exists():
        return
    content = nav_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'\n[ \t]*entry[ \t]+"[^"]*"[ \t]*\([^)]*APEX_THEME_FACTORY_MANAGED[^)]*\)',
        re.MULTILINE | re.DOTALL,
    )
    new_content = pattern.sub("", content)
    nav_path.write_text(new_content, encoding="utf-8")


def plan_and_apply_uninstall(staged_dir: Path, theme_name: str) -> None:
    # 1. Check packages dir
    theme_pkg_dir = staged_dir / f"shared-components/static-files/theme-factory/packages/{theme_name}"
    if theme_pkg_dir.exists():
        shutil.rmtree(theme_pkg_dir, ignore_errors=True)

    static_files_apx = staged_dir / "shared-components/static-files.apx"
    _remove_theme_from_static_files(static_files_apx, f"theme-factory/packages/{theme_name}/")

    app_apx = staged_dir / "application.apx"
    _remove_theme_from_app_css(app_apx, theme_name)

    # 2. Check registry.json
    registry_file = staged_dir / "shared-components/static-files/theme-factory/runtime/registry.json"
    if registry_file.exists():
        try:
            reg = json.loads(registry_file.read_text(encoding="utf-8"))
            themes = [t for t in reg.get("themes", []) if t["name"] != theme_name]
            if not themes:
                # No themes left! Remove entire runtime
                runtime_dir = staged_dir / "shared-components/static-files/theme-factory/runtime"
                if runtime_dir.exists():
                    shutil.rmtree(runtime_dir, ignore_errors=True)
                _remove_theme_from_static_files(static_files_apx, "theme-factory/runtime/")
                _remove_runtime_from_app(app_apx)

                p0 = staged_dir / "pages/p00000-global-page.apx"
                _remove_managed_page_zero_regions(p0)

                nav = staged_dir / "shared-components/navigation/lists/navigation-bar.apx"
                _remove_managed_nav_entries(nav)
            else:
                reg["themes"] = themes
                reg["defaultTheme"] = choose_fallback(reg.get("defaultTheme"), [t["name"] for t in themes])
                registry_file.write_text(json.dumps(reg, indent=2), encoding="utf-8")
        except Exception:
            pass


def run_uninstall(options: UninstallOptions) -> OperationReport:
    sqlcl = SqlclClient(options.connection)
    target_meta = sqlcl.preflight(options.workspace, options.app_id)

    staging_temp = Path(tempfile.mkdtemp(prefix="apex-theme-factory-uninst-"))
    try:
        staged_dir = sqlcl.export_apexlang(options.app_id, staging_temp)
    except Exception as exc:
        raise PackageError(f"Failed to export application: {exc}", exit_code=5) from exc

    target = inspect_export(staged_dir)
    if (target.theme_number, target.base_theme, target.style) != (42, "ut-26.1", "iris"):
        raise PackageError(
            f"Target application {options.app_id} is not Universal Theme 42 / ut-26.1 / Iris",
            exit_code=3,
        )

    pre_digest = canonical_digest(staged_dir)

    # Check if theme is present
    theme_prefix = f"theme-factory/packages/{options.theme_name}/"
    css_has_theme = any(theme_prefix in url for url in target.css_urls)
    files_have_theme = (staged_dir / f"shared-components/static-files/{theme_prefix}").exists()

    if not css_has_theme and not files_have_theme:
        print(f"Theme '{options.theme_name}' is not installed in application {options.app_id}.")
        print("Status: ALREADY_ABSENT")
        return OperationReport(
            status="ALREADY_ABSENT",
            exit_code=0,
            backup_dir=None,
            staged_dir=None,
            message="Theme not found in target",
        )

    # Create immutable backup
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if options.backup_dir:
        base_dir = options.backup_dir.resolve() / f"{options.workspace}-{options.app_id}"
    else:
        base_dir = Path("./theme-factory-backups").resolve() / f"{options.workspace}-{options.app_id}"

    backup_dir = base_dir / f"{now}-before-uninstall-{options.theme_name}"
    count = 1
    while backup_dir.exists():
        backup_dir = base_dir / f"{now}-before-uninstall-{options.theme_name}-{count}"
        count += 1

    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(staged_dir, backup_dir / "apexlang", dirs_exist_ok=True)

    target_json = {
        "appId": target_meta.app_id,
        "alias": target_meta.alias,
        "name": target_meta.name,
        "workspace": target_meta.workspace,
        "apexVersion": target_meta.apex_version,
        "uninstalledTheme": options.theme_name,
        "timestamp": now,
        "preExportDigest": pre_digest,
    }
    (backup_dir / "target.json").write_text(json.dumps(target_json, indent=2), encoding="utf-8")

    # Mutate staged export
    plan_and_apply_uninstall(staged_dir, options.theme_name)

    # Validate
    try:
        sqlcl.validate(staged_dir, options.workspace)
    except PackageError as exc:
        raise PackageError(f"Staged export validation failed: {exc}", exit_code=5) from exc

    # Drift guard
    drift_temp = Path(tempfile.mkdtemp(prefix="apex-theme-factory-drift-"))
    try:
        drift_dir = sqlcl.export_apexlang(options.app_id, drift_temp)
        drift_digest = canonical_digest(drift_dir)
        if drift_digest != pre_digest:
            raise PackageError(
                f"Database drift detected on application {options.app_id} during staging",
                exit_code=4,
            )
    finally:
        shutil.rmtree(drift_temp, ignore_errors=True)

    # Dry-run
    if not options.apply:
        print(f"\nUninstall Summary:")
        print(f"  App ID:    {target_meta.app_id} ({target_meta.name})")
        print(f"  Workspace: {target_meta.workspace}")
        print(f"  Theme:     {options.theme_name}")
        print(f"  Backup:    {backup_dir}")
        print("\nStatus: STAGED_ONLY (dry-run, no database changes applied)")
        return OperationReport(
            status="STAGED_ONLY",
            exit_code=0,
            backup_dir=backup_dir,
            staged_dir=staged_dir,
            message="Dry-run uninstall completed",
        )

    # Apply Confirmation
    print(f"\nUninstall Confirmation:")
    print(f"  App ID:    {target_meta.app_id} ({target_meta.name})")
    print(f"  Workspace: {target_meta.workspace}")
    print(f"  Theme:     {options.theme_name}")

    try:
        typed = input(f"Type application ID {options.app_id} to uninstall: ").strip()
    except EOFError:
        typed = ""

    if typed != str(options.app_id):
        print(f"Confirmation mismatch (received '{typed}', expected '{options.app_id}'). Target untouched.")
        print("Status: TARGET_UNTOUCHED")
        return OperationReport(
            status="TARGET_UNTOUCHED",
            exit_code=0,
            backup_dir=backup_dir,
            staged_dir=staged_dir,
            message="Target untouched due to confirmation mismatch",
        )

    try:
        sqlcl.import_apexlang(staged_dir, options.workspace, options.app_id)
    except PackageError as exc:
        raise PackageError(f"Import failed during uninstall: {exc}", exit_code=5) from exc

    print(f"\nResult: UNINSTALLED theme '{options.theme_name}' from application {options.app_id}.")
    print("Status: UNINSTALLED")
    return OperationReport(
        status="UNINSTALLED",
        exit_code=0,
        backup_dir=backup_dir,
        staged_dir=None,
        message=f"Theme {options.theme_name} successfully uninstalled",
    )


def run_restore(options: RestoreOptions) -> OperationReport:
    backup_path = options.backup_dir.resolve()
    target_json_path = backup_path / "target.json"
    apexlang_path = backup_path / "apexlang"

    if not target_json_path.exists() or not apexlang_path.exists():
        raise PackageError(f"Invalid backup directory: missing target.json or apexlang/ in {backup_path}")

    metadata = json.loads(target_json_path.read_text(encoding="utf-8"))
    if metadata.get("workspace", "").upper() != options.workspace.upper():
        raise PackageError(
            f"Backup workspace '{metadata.get('workspace')}' does not match requested workspace '{options.workspace}'"
        )
    if int(metadata.get("appId", 0)) != options.app_id:
        raise PackageError(
            f"Backup appId '{metadata.get('appId')}' does not match requested appId '{options.app_id}'"
        )

    sqlcl = SqlclClient(options.connection)
    target_meta = sqlcl.preflight(options.workspace, options.app_id)

    live_temp = Path(tempfile.mkdtemp(prefix="apex-theme-factory-restore-live-"))
    try:
        live_dir = sqlcl.export_apexlang(options.app_id, live_temp)
        live_digest = canonical_digest(live_dir)
        backup_digest = canonical_digest(apexlang_path)
    finally:
        shutil.rmtree(live_temp, ignore_errors=True)

    print(f"\nRestore Preflight:")
    print(f"  App ID:        {target_meta.app_id} ({target_meta.name})")
    print(f"  Workspace:     {target_meta.workspace}")
    print(f"  Live Digest:   {live_digest}")
    print(f"  Backup Digest: {backup_digest}")

    if not options.apply:
        print("\nStatus: STAGED_ONLY (dry-run, backup validated, target untouched)")
        return OperationReport(
            status="STAGED_ONLY",
            exit_code=0,
            backup_dir=backup_path,
            staged_dir=None,
            message="Restore dry-run completed",
        )

    try:
        typed = input(f"Type application ID {options.app_id} to restore: ").strip()
    except EOFError:
        typed = ""

    if typed != str(options.app_id):
        print(f"Confirmation mismatch. Target untouched.")
        print("Status: TARGET_UNTOUCHED")
        return OperationReport(
            status="TARGET_UNTOUCHED",
            exit_code=0,
            backup_dir=backup_path,
            staged_dir=None,
            message="Restore cancelled by user",
        )

    try:
        sqlcl.import_apexlang(apexlang_path, options.workspace, options.app_id)
    except PackageError as exc:
        raise PackageError(f"Import failed during restore: {exc}", exit_code=5) from exc

    print(f"\nResult: RESTORED application {options.app_id} from {backup_path}.")
    print("Status: RESTORED")
    return OperationReport(
        status="RESTORED",
        exit_code=0,
        backup_dir=backup_path,
        staged_dir=None,
        message="Application successfully restored from backup",
    )


def run_uninstall_cli(args) -> None:
    options = UninstallOptions(
        theme_name=args.theme,
        connection=args.connection,
        workspace=args.workspace,
        app_id=args.app_id,
        backup_dir=getattr(args, "backup_dir", None),
        apply=getattr(args, "apply", False),
    )
    report = run_uninstall(options)
    if report.exit_code != 0:
        sys.exit(report.exit_code)


def run_restore_cli(args) -> None:
    options = RestoreOptions(
        connection=args.connection,
        workspace=args.workspace,
        app_id=args.app_id,
        backup_dir=args.backup,
        apply=getattr(args, "apply", False),
    )
    report = run_restore(options)
    if report.exit_code != 0:
        sys.exit(report.exit_code)
