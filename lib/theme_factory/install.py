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
    package_roots: tuple[Path, ...]
    connection: str
    workspace: str
    app_id: int
    switcher_mode: str = "preserve"  # "preserve", "enable", "disable"
    backup_dir: Optional[Path] = None
    apply: bool = False
    assume_yes: bool = False


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
    Theme Factory prefix; anything else is left alone. Set
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


def assert_no_drift(sqlcl: SqlclClient, app_id: int, expected_digest: str, moment: str) -> None:
    """Re-export the target and refuse (exit 4) unless it still matches `expected_digest`."""
    drift_temp = make_staging_dir("apex-theme-factory-drift-")
    try:
        drift_dir = sqlcl.export_apexlang(app_id, drift_temp)
        if canonical_digest(drift_dir) != expected_digest:
            raise PackageError(f"Database drift detected on application {app_id} {moment}", exit_code=4)
    finally:
        shutil.rmtree(drift_temp, ignore_errors=True)


# Recorded when the import ran but the application could not be exported again: a later restore
# can then never prove "no later changes" and asks for --discard-later-changes.
UNKNOWN_POST_DIGEST = "unknown"


def create_backup(backup_root: Optional[Path], workspace: str, app_id: int, label: str,
                  staged_dir: Path, metadata: dict) -> Path:
    """Copy the untouched export to <root>/<WS>-<ID>/<timestamp>-before-<label>/ with target.json."""
    now = metadata["timestamp"]
    root = (backup_root or Path("./theme-factory-backups")).resolve() / f"{workspace}-{app_id}"
    backup_dir = root / f"{now}-before-{label}"
    count = 1
    while backup_dir.exists():
        backup_dir = root / f"{now}-before-{label}-{count}"
        count += 1
    backup_dir.mkdir(parents=True)
    shutil.copytree(staged_dir, backup_dir / "apexlang")
    (backup_dir / "target.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return backup_dir


def export_after_import(sqlcl: SqlclClient, app_id: int, dest: Path, backup_dir: Path) -> Path:
    try:
        return sqlcl.export_apexlang(app_id, dest)
    except PackageError as exc:
        _record_post_digest(backup_dir, UNKNOWN_POST_DIGEST)
        raise PackageError(f"Imported, but the post-import export failed: {exc}", exit_code=6) from exc


def utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _record_post_digest(backup_dir: Path, digest: str) -> None:
    """Remember what the application looked like right after this operation so a later
    restore can tell whether unrelated changes happened in between."""
    target_json = backup_dir / "target.json"
    data = json.loads(target_json.read_text(encoding="utf-8"))
    data["postOperationDigest"] = digest
    target_json.write_text(json.dumps(data, indent=2), encoding="utf-8")


def keep_or_remove_staging(staging: list, state: dict) -> None:
    """After an import the staged export is evidence of what was sent: keep it on any failure."""
    if state.get("imported"):
        for path in staging:
            print(f"Staged export kept for inspection: {path}", file=sys.stderr)
        return
    for path in staging:
        remove_staging_dir(path)


def run_install(options: InstallOptions) -> OperationReport:
    staging: list[Path] = []
    state: dict = {}
    try:
        report = _run_install(options, staging, state)
    except Exception:
        keep_or_remove_staging(staging, state)
        raise
    if report.status != "IMPORTED_POSTCHECK_FAILED":
        for path in staging:
            remove_staging_dir(path)
        report = OperationReport(report.status, report.exit_code, report.backup_dir, None, report.message)
    else:
        print(f"Staged export kept for inspection: {report.staged_dir}")
    return report


def _describe(manifests: list[ThemeManifest]) -> str:
    if len(manifests) == 1:
        return f"theme '{manifests[0].name}' v{manifests[0].version}"
    listed = ", ".join(f"'{manifest.name}' v{manifest.version}" for manifest in manifests)
    return f"themes {listed} (default '{manifests[-1].name}')"


def _run_install(options: InstallOptions, staging: list, state: dict) -> OperationReport:
    # 1. Verify every package before touching the target; the last one listed becomes the default.
    package_roots = tuple(Path(root).resolve() for root in options.package_roots)
    if not package_roots:
        raise PackageError("At least one package is required")
    manifests = [verify_package(root) for root in package_roots]
    names = [item.name for item in manifests]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        raise PackageError(f"Theme listed more than once: {', '.join(repeated)}")
    manifest = manifests[-1]
    label = manifest.name if len(manifests) == 1 else f"{len(manifests)}-themes"

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

    # 5. Immutable backup of the untouched export (apply only: a dry run writes nothing lasting)
    backup_dir = None
    if options.apply:
        backup_dir = create_backup(options.backup_dir, options.workspace, options.app_id, label, staged_dir, {
            "appId": target_meta.app_id,
            "alias": target_meta.alias,
            "name": target_meta.name,
            "workspace": target_meta.workspace,
            "apexVersion": target_meta.apex_version,
            "theme": manifest.name,
            "themeVersion": manifest.version,
            "themes": [{"name": item.name, "version": item.version} for item in manifests],
            "timestamp": utc_stamp(),
            "preExportDigest": pre_digest,
        })

    # 6. Plan and apply one staged patch per package, in the order given
    diffs = []
    for package_root in package_roots:
        patch = plan_install(staged_dir, package_root, options.switcher_mode)
        apply_patch(patch)
        diffs.append(patch.diff)
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
    assert_no_drift(sqlcl, options.app_id, pre_digest, "during staging")

    # 9. Dry-run mode (target untouched: post-operation state == pre-export state)
    if not options.apply:
        print(f"\nTarget Summary:")
        print(f"  App ID:    {target_meta.app_id} ({target_meta.name})")
        print(f"  Workspace: {target_meta.workspace}")
        print(f"  Alias:     {target_meta.alias}")
        print(f"  Install:   {_describe(manifests)}")
        print(f"  Switcher:  {options.switcher_mode}")
        print("  Backup:    none (dry run; --apply writes one before importing)")
        print("\nUnified Diff:\n" + "\n".join(diffs))
        print("\nStatus: STAGED_ONLY (dry-run, no database changes applied)")
        return OperationReport(
            status="STAGED_ONLY",
            exit_code=0,
            backup_dir=None,
            staged_dir=None,
            message="Dry-run completed successfully",
        )

    # 10. Apply mode: Confirmation
    print(f"\nTarget Application:")
    print(f"  App ID:        {target_meta.app_id} ({target_meta.name})")
    print(f"  Workspace:     {target_meta.workspace}")
    print(f"  Alias:         {target_meta.alias}")
    print(f"  Install:       {_describe(manifests)}")
    print(f"  Staged Digest: {staged_digest}")
    print(f"  Backup:        {backup_dir}")

    if options.assume_yes:
        # Requested explicitly by the operator. Recorded in the output so an unattended full
        # replace is never silent: this is the one path where no human confirmed the target.
        print(f"  Confirmation:  skipped via --yes (no wrong-application guard on {options.app_id})")
        typed = str(options.app_id)
    else:
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

    # The confirmation prompt can wait indefinitely: check again right before the full replace
    # so edits made while it was open are refused rather than overwritten.
    assert_no_drift(sqlcl, options.app_id, pre_digest, "while waiting for confirmation")

    # Import
    try:
        sqlcl.import_apexlang(staged_dir, options.workspace, options.app_id)
    except PackageError as exc:
        state["imported"] = True  # a failed import may still have replaced part of the application
        _record_post_digest(backup_dir, UNKNOWN_POST_DIGEST)
        raise PackageError(f"APEX import failed: {exc}", exit_code=5) from exc
    state["imported"] = True

    # Post-check. The post-operation digest is recorded before any comparison, so restore's
    # "later changes" guard works even when the check below fails.
    post_temp = make_staging_dir("apex-theme-factory-post-")
    try:
        post_dir = export_after_import(sqlcl, options.app_id, post_temp, backup_dir)
        post_digest = canonical_digest(post_dir)
        _record_post_digest(backup_dir, post_digest)
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
        if not all(matches_install(post_target, item, options.switcher_mode) for item in manifests):
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
        installed = {package.name: package for package in installed_packages}
        expected_switcher = options.switcher_mode == "enable" or (
            options.switcher_mode == "preserve" and switcher_enabled
        )
        if any(item.name not in installed for item in manifests) or default_theme != manifest.name or (
            options.switcher_mode != "preserve" and switcher_enabled != expected_switcher
        ):
            print("Status: IMPORTED_POSTCHECK_FAILED")
            return OperationReport(
                status="IMPORTED_POSTCHECK_FAILED", exit_code=6, backup_dir=backup_dir,
                staged_dir=staged_dir, message="Imported but registry postcheck failed",
            )
        for item in manifests:
            verify_package_ownership(post_dir, installed[item.name])
        verify_runtime_ownership(post_dir, read_registry_document(post_dir))
    finally:
        shutil.rmtree(post_temp, ignore_errors=True)

    print(f"\nResult: IMPORTED {_describe(manifests)} into application {options.app_id}.")
    print("Status: IMPORTED")
    return OperationReport(
        status="IMPORTED",
        exit_code=0,
        backup_dir=backup_dir,
        staged_dir=None,
        message=f"{_describe(manifests)} successfully imported",
    )


def run_install_cli(args) -> None:
    if getattr(args, "with_switcher", False):
        switcher_mode = "enable"
    elif getattr(args, "without_switcher", False):
        switcher_mode = "disable"
    else:
        switcher_mode = "preserve"

    options = InstallOptions(
        assume_yes=getattr(args, "yes", False),
        package_roots=tuple(args.package_root),
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
