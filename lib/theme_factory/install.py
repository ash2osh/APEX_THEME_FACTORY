"""Install transaction and CLI integration for APEX Theme Factory."""

from dataclasses import dataclass
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Optional

from lib.theme_factory.apexlang import (
    canonical_digest,
    inspect_export,
    plan_install,
    apply_patch,
    TargetExport,
    read_install_state,
    theme_factory_projection,
    verify_package_ownership,
    verify_runtime_ownership,
    read_registry_document,
)
from lib.theme_factory.archive import verify_package
from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import ThemeManifest
from lib.theme_factory.sqlcl import SqlclClient, TargetMetadata


@dataclass(frozen=True)
class InstallOptions:
    package_root: Path
    connection: str
    workspace: str
    app_id: int
    switcher_mode: str = "preserve"  # "preserve", "enable", "disable"
    backup_dir: Optional[Path] = None
    apply: bool = False


@dataclass(frozen=True)
class OperationReport:
    status: str
    exit_code: int
    backup_dir: Optional[Path]
    staged_dir: Optional[Path]
    message: str = ""


APEX_26_1_RE = re.compile(r"^26\.1(?:\.\d+)?(?:[-+].*)?$")
# Exit codes: 2 package/argument, 3 unsupported target, 4 drift, 5 validation/import,
# 6 post-import verification, 7 explicit cancellation or refused stale restore.
CANCELLED_EXIT_CODE = 7


def require_supported_apex_version(version: str) -> None:
    if not APEX_26_1_RE.fullmatch(str(version).strip()):
        raise PackageError(
            f"Target APEX version '{version}' is unsupported; expected APEX 26.1.x",
            exit_code=3,
        )


def matches_install(target: TargetExport, manifest: ThemeManifest, switcher_mode: str) -> bool:
    if target.theme_number != 42 or target.base_theme != "ut-26.1" or target.style != "iris":
        return False
    expected_css = f"#APP_FILES#theme-factory/packages/{manifest.name}/{manifest.version}/theme.css"
    if expected_css not in target.css_urls:
        return False
    if switcher_mode == "enable":
        expected_js = "#APP_FILES#theme-factory/runtime/theme-factory-runtime.js"
        if expected_js not in target.javascript_urls:
            return False
    return True


def make_staging_dir(prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def remove_staging_dir(staging_temp: Optional[Path]) -> None:
    """Delete a staging directory created by make_staging_dir, and nothing else.

    The path must still be a direct child of the system temp directory and carry the
    Theme Factory prefix; anything else is left alone (spec §10). Set
    THEME_FACTORY_KEEP_STAGING=1 to keep staged exports for inspection.
    """
    if staging_temp is None or os.environ.get("THEME_FACTORY_KEEP_STAGING") == "1":
        return
    staging_temp = Path(staging_temp)
    temp_root = Path(tempfile.gettempdir()).resolve()
    if (
        staging_temp.is_dir()
        and not staging_temp.is_symlink()
        and staging_temp.resolve().parent == temp_root
        and staging_temp.name.startswith("apex-theme-factory-")
    ):
        shutil.rmtree(staging_temp, ignore_errors=True)


def _record_post_digest(backup_dir: Path, digest: str) -> None:
    """Remember what the application looked like right after this operation so a later
    restore can tell whether unrelated changes happened in between."""
    target_json = backup_dir / "target.json"
    data = json.loads(target_json.read_text(encoding="utf-8"))
    data["postOperationDigest"] = digest
    target_json.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_install(options: InstallOptions) -> OperationReport:
    staging: list[Path] = []
    try:
        report = _run_install(options, staging)
    except Exception:
        for path in staging:
            remove_staging_dir(path)
        raise
    if report.status != "IMPORTED_POSTCHECK_FAILED":
        for path in staging:
            remove_staging_dir(path)
        report = OperationReport(report.status, report.exit_code, report.backup_dir, None, report.message)
    return report


def _run_install(options: InstallOptions, staging: list) -> OperationReport:
    # 1. Verify package and manifest
    package_root = options.package_root.resolve()
    manifest = verify_package(package_root)

    # 2. Setup SQLcl client & validate connection/workspace/app_id
    sqlcl = SqlclClient(options.connection)

    # 3. SQLcl preflight check
    target_meta = sqlcl.preflight(options.workspace, options.app_id)
    require_supported_apex_version(target_meta.apex_version)

    # 4. Fresh export into staging
    staging_temp = make_staging_dir("apex-theme-factory-stage-")
    staging.append(staging_temp)
    try:
        staged_dir = sqlcl.export_apexlang(options.app_id, staging_temp)
    except Exception as exc:
        raise PackageError(f"Failed to export application: {exc}", exit_code=5) from exc

    target = inspect_export(staged_dir)
    if (target.theme_number, target.base_theme, target.style) != (42, "ut-26.1", "iris"):
        raise PackageError(
            f"Target application {options.app_id} is not Universal Theme 42 / ut-26.1 / Iris "
            f"(found: {target.theme_number}/{target.base_theme}/{target.style})",
            exit_code=3,
        )

    pre_digest = canonical_digest(staged_dir)

    # 5. Create immutable backup and target.json
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if options.backup_dir:
        base_dir = options.backup_dir.resolve() / f"{options.workspace}-{options.app_id}"
    else:
        base_dir = Path("./theme-factory-backups").resolve() / f"{options.workspace}-{options.app_id}"

    backup_dir = base_dir / f"{now}-before-{manifest.name}"
    count = 1
    while backup_dir.exists():
        backup_dir = base_dir / f"{now}-before-{manifest.name}-{count}"
        count += 1

    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_apexlang = backup_dir / "apexlang"
    shutil.copytree(staged_dir, backup_apexlang, dirs_exist_ok=True)

    target_json = {
        "appId": target_meta.app_id,
        "alias": target_meta.alias,
        "name": target_meta.name,
        "workspace": target_meta.workspace,
        "apexVersion": target_meta.apex_version,
        "theme": manifest.name,
        "themeVersion": manifest.version,
        "timestamp": now,
        "preExportDigest": pre_digest,
    }
    (backup_dir / "target.json").write_text(json.dumps(target_json, indent=2), encoding="utf-8")

    # 6. Plan and apply staged patch
    patch = plan_install(staged_dir, package_root, options.switcher_mode)
    apply_patch(patch)
    staged_digest = canonical_digest(staged_dir)
    # SQLcl reformats APEXLang on export (indentation, ordering, dropped comments), so the
    # post-import comparison uses the semantic Theme Factory projection, not raw bytes.
    staged_projection = theme_factory_projection(staged_dir)

    # 7. Validate staged changes via SQLcl
    try:
        sqlcl.validate(staged_dir, options.workspace)
    except PackageError as exc:
        raise PackageError(f"Staged export validation failed: {exc}", exit_code=5) from exc

    # 8. Drift guard: fresh second export to check for DB state modification during staging
    drift_temp = make_staging_dir("apex-theme-factory-drift-")
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

    # 9. Dry-run mode (target untouched: post-operation state == pre-export state)
    if not options.apply:
        _record_post_digest(backup_dir, pre_digest)
        print(f"\nTarget Summary:")
        print(f"  App ID:    {target_meta.app_id} ({target_meta.name})")
        print(f"  Workspace: {target_meta.workspace}")
        print(f"  Alias:     {target_meta.alias}")
        print(f"  Theme:     {manifest.name} v{manifest.version}")
        print(f"  Switcher:  {options.switcher_mode}")
        print(f"  Backup:    {backup_dir}")
        print(f"  Staged:    {staged_dir}")
        print(f"\nUnified Diff:\n{patch.diff}")
        print("\nStatus: STAGED_ONLY (dry-run, no database changes applied)")
        return OperationReport(
            status="STAGED_ONLY",
            exit_code=0,
            backup_dir=backup_dir,
            staged_dir=staged_dir,
            message="Dry-run completed successfully",
        )

    # 10. Apply mode: Confirmation
    print(f"\nTarget Application:")
    print(f"  App ID:        {target_meta.app_id} ({target_meta.name})")
    print(f"  Workspace:     {target_meta.workspace}")
    print(f"  Alias:         {target_meta.alias}")
    print(f"  Theme:         {manifest.name} v{manifest.version}")
    print(f"  Staged Digest: {staged_digest}")
    print(f"  Backup:        {backup_dir}")

    try:
        typed = input(f"Type application ID {options.app_id} to import: ").strip()
    except EOFError:
        typed = ""

    if typed != str(options.app_id):
        print(f"Confirmation mismatch (received '{typed}', expected '{options.app_id}'). Target untouched.")
        print("Status: TARGET_UNTOUCHED")
        _record_post_digest(backup_dir, pre_digest)
        return OperationReport(
            status="TARGET_UNTOUCHED",
            exit_code=CANCELLED_EXIT_CODE,
            backup_dir=backup_dir,
            staged_dir=staged_dir,
            message="Target untouched due to confirmation mismatch",
        )

    # Import
    try:
        sqlcl.import_apexlang(staged_dir, options.workspace, options.app_id)
    except PackageError as exc:
        raise PackageError(f"APEX import failed: {exc}", exit_code=5) from exc

    # Post-check
    post_temp = make_staging_dir("apex-theme-factory-post-")
    try:
        post_dir = sqlcl.export_apexlang(options.app_id, post_temp)
        post_projection = theme_factory_projection(post_dir)
        if post_projection != staged_projection:
            differing = sorted(key for key in staged_projection if staged_projection[key] != post_projection.get(key))
            print(f"Post-import export differs from the staged transaction in: {', '.join(differing)}")
            print("Status: IMPORTED_POSTCHECK_FAILED")
            return OperationReport(
                status="IMPORTED_POSTCHECK_FAILED", exit_code=6, backup_dir=backup_dir,
                staged_dir=staged_dir, message="Imported export differs from staged transaction",
            )
        post_target = inspect_export(post_dir)
        if not matches_install(post_target, manifest, options.switcher_mode):
            print("WARNING: Post-check inspection did not match expected installed state!")
            print("Status: IMPORTED_POSTCHECK_FAILED")
            return OperationReport(
                status="IMPORTED_POSTCHECK_FAILED",
                exit_code=6,
                backup_dir=backup_dir,
                staged_dir=staged_dir,
                message="Imported but postcheck verification failed",
            )
        installed_packages, default_theme, switcher_enabled = read_install_state(post_dir)
        installed = next((package for package in installed_packages if package.name == manifest.name), None)
        expected_switcher = options.switcher_mode == "enable" or (
            options.switcher_mode == "preserve" and switcher_enabled
        )
        if not installed or default_theme != manifest.name or (
            options.switcher_mode != "preserve" and switcher_enabled != expected_switcher
        ):
            print("Status: IMPORTED_POSTCHECK_FAILED")
            return OperationReport(
                status="IMPORTED_POSTCHECK_FAILED", exit_code=6, backup_dir=backup_dir,
                staged_dir=staged_dir, message="Imported but registry postcheck failed",
            )
        verify_package_ownership(post_dir, installed)
        verify_runtime_ownership(post_dir, read_registry_document(post_dir))
        post_digest = canonical_digest(post_dir)
    finally:
        shutil.rmtree(post_temp, ignore_errors=True)
    _record_post_digest(backup_dir, post_digest)

    print(f"\nResult: IMPORTED theme '{manifest.name}' v{manifest.version} into application {options.app_id}.")
    print("Status: IMPORTED")
    return OperationReport(
        status="IMPORTED",
        exit_code=0,
        backup_dir=backup_dir,
        staged_dir=None,
        message=f"Theme {manifest.name} v{manifest.version} successfully imported",
    )


def run_install_cli(args) -> None:
    if getattr(args, "with_switcher", False):
        switcher_mode = "enable"
    elif getattr(args, "without_switcher", False):
        switcher_mode = "disable"
    else:
        switcher_mode = "preserve"

    options = InstallOptions(
        package_root=args.package_root,
        connection=args.connection,
        workspace=args.workspace,
        app_id=args.app_id,
        switcher_mode=switcher_mode,
        backup_dir=getattr(args, "backup_dir", None),
        apply=getattr(args, "apply", False),
    )

    report = run_install(options)
    if report.exit_code != 0:
        sys.exit(report.exit_code)
