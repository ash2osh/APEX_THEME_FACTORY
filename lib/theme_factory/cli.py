"""Command line interface for Theme Factory tools."""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from lib.theme_factory.archive import build_package, build_package_from_root, verify_package
from lib.theme_factory.checks import run_theme_checks
from lib.theme_factory.errors import PackageError


def register_package_commands(subparsers: argparse._SubParsersAction) -> None:
    package = subparsers.add_parser("package", help="Build single-theme ZIP package")
    package.add_argument("--repo-root", type=Path, default=Path.cwd())
    source = package.add_mutually_exclusive_group(required=True)
    source.add_argument("--theme")
    source.add_argument("--theme-root", type=Path)
    package.add_argument("--output-dir", type=Path, required=True)
    package.set_defaults(handler=_handle_package)

    verify = subparsers.add_parser("verify-package", help="Verify package checksums and manifest")
    source = verify.add_mutually_exclusive_group(required=True)
    source.add_argument("--package-root", type=Path)
    source.add_argument("--package", type=Path)
    verify.set_defaults(handler=_handle_verify_package)


def register_install_commands(subparsers: argparse._SubParsersAction) -> None:
    install = subparsers.add_parser("install", help="Install theme into APEX application")
    install.add_argument("--package-root", type=Path, required=True)
    install.add_argument("--connection", required=True)
    install.add_argument("--workspace", required=True)
    install.add_argument("--app-id", type=int, required=True)
    switcher = install.add_mutually_exclusive_group()
    switcher.add_argument("--with-switcher", action="store_true")
    switcher.add_argument("--without-switcher", action="store_true")
    install.add_argument("--backup-dir", type=Path, default=None)
    install.add_argument("--apply", action="store_true")
    install.add_argument("--yes", action="store_true",
                         help="Skip typed confirmation; the named app is fully replaced.")
    install.set_defaults(handler=_handle_install)

    uninstall = subparsers.add_parser("uninstall", help="Uninstall theme from APEX application")
    source = uninstall.add_mutually_exclusive_group(required=True)
    source.add_argument("--theme")
    source.add_argument("--package-root", type=Path)
    uninstall.add_argument("--connection", required=True)
    uninstall.add_argument("--workspace", required=True)
    uninstall.add_argument("--app-id", type=int, required=True)
    uninstall.add_argument("--backup-dir", type=Path, default=None)
    uninstall.add_argument("--apply", action="store_true")
    uninstall.set_defaults(handler=_handle_uninstall)

    restore = subparsers.add_parser("restore", help="Restore application from backup")
    restore.add_argument("--connection", required=True)
    restore.add_argument("--workspace", required=True)
    restore.add_argument("--app-id", type=int, required=True)
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--apply", action="store_true")
    restore.add_argument("--discard-later-changes", action="store_true")
    restore.set_defaults(handler=_handle_restore)


def register_workshop_commands(subparsers: argparse._SubParsersAction) -> None:
    inspector = subparsers.add_parser("inspect-iris", help="Check or update the Iris token inventory")
    inspector.add_argument("--reference-root", type=Path,
                           default=Path(".agents/knowledge/reference/ut-26.1"))
    inspector.add_argument("--inventory", type=Path,
                           default=Path(".agents/knowledge/reference/ut-26.1/iris-token-inventory.json"))
    inspector.add_argument("--report", type=Path,
                           default=Path("docs/generated/iris-26.1-token-report.md"))
    action = inspector.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--write", action="store_true")
    inspector.set_defaults(handler=_handle_inspect_iris)

    new = subparsers.add_parser("new", help="Scaffold a theme from a recipe or neutral defaults")
    new.add_argument("name")
    new.add_argument("--repo-root", type=Path, default=Path.cwd())
    new.add_argument("--recipe", type=Path)
    new.add_argument("--title")
    new.add_argument("--tagline")
    new.add_argument("--mode", choices=("light", "dark"))
    new.add_argument("--json", action="store_true")
    new.set_defaults(handler=_handle_new)

    font = subparsers.add_parser("font", help="Manage vendored theme fonts")
    font_commands = font.add_subparsers(dest="font_command", required=True)
    add = font_commands.add_parser("add", help="Install static WOFF2 faces from pinned upstream")
    add.add_argument("name")
    add.add_argument("--repo-root", type=Path, default=Path.cwd())
    add.add_argument("--family", required=True)
    add.add_argument("--metadata-url", required=True)
    add.add_argument("--source-revision", required=True)
    add.add_argument("--weights", required=True)
    add.add_argument("--dry-run", action="store_true")
    add.add_argument("--json", action="store_true")
    add.set_defaults(handler=_handle_font_add)

    check = subparsers.add_parser("check", help="Run cached author checks for one theme")
    check.add_argument("name")
    check.add_argument("--repo-root", type=Path, default=Path.cwd())
    check.add_argument("--no-cache", action="store_true")
    check.add_argument("--json", action="store_true")
    check.set_defaults(handler=_handle_check)

    dev = subparsers.add_parser("dev", help="Run explicit candidate-lane gates")
    dev.add_argument("name")
    dev.add_argument("--repo-root", type=Path, default=Path.cwd())
    dev.add_argument("--sync", action="store_true")
    dev.add_argument("--validate", action="store_true")
    dev.add_argument("--import", dest="import_app", action="store_true")
    dev.add_argument("--apply", action="store_true")
    dev.add_argument("--open", dest="open_browser", action="store_true")
    dev.add_argument("--json", action="store_true")
    dev.set_defaults(handler=_handle_dev)

    catalog = subparsers.add_parser("catalog", help="Check or update generated theme catalogs")
    catalog.add_argument("--repo-root", type=Path, default=Path.cwd())
    catalog.add_argument("--evidence-root", type=Path, default=Path(".agents/evaluations/runtime"))
    action = catalog.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Report generated documentation drift")
    action.add_argument("--write", action="store_true", help="Update generated documentation atomically")
    catalog.set_defaults(handler=_handle_catalog)

    cover = subparsers.add_parser("cover", help="Capture a checked theme cover through Chrome")
    cover.add_argument("name")
    cover.add_argument("--repo-root", type=Path, default=Path.cwd())
    cover.add_argument("--output", type=Path, required=True)
    cover.add_argument("--apply", action="store_true")
    cover.add_argument("--overwrite", action="store_true")
    cover.add_argument("--json", action="store_true")
    cover.set_defaults(handler=_handle_cover)

    release_batch = subparsers.add_parser("release-batch", help="Batch digest-bound release evidence")
    release_batch.add_argument("--themes", required=True)
    release_batch.add_argument("--secondary", required=True, type=Path)
    release_batch.add_argument("--evidence-root", type=Path, default=Path(".agents/evaluations/runtime"))
    release_batch.add_argument("--repo-root", type=Path, default=Path.cwd())
    release_batch.add_argument("--connection")
    release_batch.add_argument("--workspace")
    release_batch.add_argument("--minimal-id", type=int)
    release_batch.add_argument("--business-id", type=int)
    release_batch.add_argument("--minimal-url")
    release_batch.add_argument("--business-url")
    release_batch.add_argument("--business-extra-urls", default="")
    release_batch.add_argument("--widths", default="1440,1024,768,375")
    release_batch.add_argument("--date")
    release_batch.add_argument("--work-dir", type=Path)
    release_batch.add_argument("--common-check-artifact", type=Path)
    release_batch.add_argument("--resume", action="store_true")
    release_batch.add_argument("--report-obsolete", action="store_true")
    release_batch.add_argument("--apply", action="store_true")
    release_batch.set_defaults(handler=_handle_release_batch)

    evidence = subparsers.add_parser("evidence", help="Manage runtime evidence")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    prune = evidence_commands.add_parser("prune", help="Prune old release evidence safely")
    prune.add_argument("--repo-root", type=Path, default=Path.cwd())
    prune.add_argument("--keep-latest", type=int, required=True)
    prune.add_argument("--apply", action="store_true")
    prune.set_defaults(handler=_handle_evidence_prune)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="APEX Theme Factory CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    register_package_commands(subparsers)
    register_install_commands(subparsers)
    register_workshop_commands(subparsers)
    return parser


def _handle_package(args: argparse.Namespace) -> int:
    path = (build_package_from_root(args.repo_root, args.theme_root, args.output_dir)
            if args.theme_root else build_package(args.repo_root, args.theme, args.output_dir))
    print(f"Built package: {path}")
    return 0


def _handle_verify_package(args: argparse.Namespace) -> int:
    manifest = verify_package(args.package or args.package_root)
    print(f"Package '{manifest.name}' v{manifest.version} verified successfully.")
    return 0


def _handle_install(args: argparse.Namespace) -> int:
    from lib.theme_factory.install import run_install_cli
    return int(run_install_cli(args) or 0)


def _handle_uninstall(args: argparse.Namespace) -> int:
    from lib.theme_factory.uninstall import run_uninstall_cli
    return int(run_uninstall_cli(args) or 0)


def _handle_restore(args: argparse.Namespace) -> int:
    from lib.theme_factory.uninstall import run_restore_cli
    return int(run_restore_cli(args) or 0)


def _inline_recipe(args: argparse.Namespace):
    from lib.theme_factory.manifest import NAME_REGEX
    from lib.theme_factory.recipe import (
        ComponentProfiles, Focus, Geometry, Identity, Palette, ThemeRecipe, Typography,
    )
    if not NAME_REGEX.fullmatch(args.name):
        raise PackageError(f"Theme name '{args.name}' must match {NAME_REGEX.pattern}")
    pairs = (("--title", args.title), ("--tagline", args.tagline), ("--mode", args.mode))
    missing = [flag for flag, value in pairs if not value]
    if missing:
        raise PackageError("new requires --recipe or inline fields: --title, --tagline, and --mode; missing "
                           + ", ".join(missing))
    dark = args.mode == "dark"
    palette = Palette(
        "#111318" if dark else "#F6F7FB", "#1B1F27" if dark else "#FFFFFF",
        "#151820" if dark else "#E9ECF3", "#F4F7FB" if dark else "#18202B",
        "#B8C0CC" if dark else "#4D5A68", "#75E6A4" if dark else "#2457FF",
        "#73C8FF" if dark else "#006B62", "#0E1A13" if dark else "#FFFFFF",
        "#FF7A8A" if dark else "#B42318",
    )
    return ThemeRecipe(
        1, Identity(args.name, args.title, args.tagline, "Neutral generated starting point.",
                    args.mode, ("neutral", args.mode)), palette,
        Typography("system-ui", "body", ("system-ui", "sans-serif"), (400, 500, 600, 700)),
        Geometry("4px", "8px", "12px", "40px", "hairline", "soft"),
        Focus(palette.accent_alt, "2px", "2px"),
        ComponentProfiles("minimal", "flat", "rounded", "comfortable", "spacious", "flat"),
    )


def _handle_new(args: argparse.Namespace) -> int:
    from lib.theme_factory.recipe import load_recipe
    from lib.theme_factory.scaffold import create_theme
    inline = (args.title, args.tagline, args.mode)
    if args.recipe and any(value is not None for value in inline):
        raise PackageError("--recipe cannot be combined with --title, --tagline, or --mode")
    recipe = load_recipe(args.recipe) if args.recipe else _inline_recipe(args)
    if recipe.identity.name != args.name:
        raise PackageError(f"Recipe theme '{recipe.identity.name}' does not match requested name '{args.name}'")
    result = create_theme(args.repo_root, recipe)
    payload = {"status": "PASS", "theme": recipe.identity.name,
               "created": str(result.created), "files": len(result.written)}
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True) if args.json
          else f"Created theme '{recipe.identity.name}' with {len(result.written)} source files.")
    return 0


def _handle_font_add(args: argparse.Namespace) -> int:
    from lib.theme_factory.font_pipeline import FontRequest, install_font
    try:
        weights = tuple(int(value.strip()) for value in args.weights.split(",") if value.strip())
    except ValueError as exc:
        raise PackageError("--weights must be a comma-separated integer list") from exc
    result = install_font(args.repo_root, args.repo_root / "sample-themes" / args.name,
                          FontRequest(metadata_url=args.metadata_url,
                                      source_revision=args.source_revision,
                                      weights=weights,
                                      family=args.family),
                          dry_run=args.dry_run)
    payload = {"status": "PASS", "family": result.family, "sourceFilename": result.source_filename,
               "dryRun": result.dry_run,
               "faces": [{"file": face.file, "weight": face.weight, "sha256": face.sha256}
                         for face in result.faces]}
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True) if args.json
          else f"{'Resolved' if result.dry_run else 'Installed'} {len(result.faces)} faces for {result.family}.")
    return 0


def _handle_check(args: argparse.Namespace) -> int:
    report = run_theme_checks(args.repo_root, args.name, use_cache=not args.no_cache)
    print(report.to_json() if args.json else report.to_human())
    return 0 if report.status == "PASS" else 2


def _handle_dev(args: argparse.Namespace) -> int:
    from lib.theme_factory.dev import DevOptions, run_dev
    report = run_dev(DevOptions(args.repo_root, args.name, args.sync, args.validate,
                                args.import_app, args.apply, args.open_browser))
    print(report.to_json() if args.json else report.to_human())
    return 0 if report.status == "PASS" else 2


def _handle_catalog(args: argparse.Namespace) -> int:
    from lib.theme_factory.catalog import update_catalog
    evidence_root = args.evidence_root
    if not evidence_root.is_absolute():
        evidence_root = args.repo_root / evidence_root
    changed = update_catalog(args.repo_root, evidence_root, check=args.check)
    if args.check and changed:
        for path in changed:
            print(f"DRIFT {path.relative_to(args.repo_root.resolve())}")
        return 2
    action = "updated" if changed else "current"
    print(f"THEME_CATALOG status=PASS files={len(changed)} action={action}")
    return 0


def _handle_cover(args: argparse.Namespace) -> int:
    from tools.theme_cover import capture_cover

    if args.overwrite and not args.apply:
        raise PackageError("cover --overwrite requires --apply")
    report = run_theme_checks(args.repo_root, args.name)
    if report.status != "PASS":
        raise PackageError(
            f"Theme '{args.name}' failed theme check; fix it before opening Chrome"
        )
    client = None
    if args.apply:
        from tools.chrome_devtools_client import ChromeDevToolsClient
        client = ChromeDevToolsClient()
    result = capture_cover(client, args.name, args.output, args.apply, args.overwrite)
    print(result.to_json() if args.json else result.to_human())
    return 0


def _handle_release_batch(args: argparse.Namespace) -> int:
    from tools.release_batch import (
        current_package_shas, evidence_directory_current, execute_live_batch,
        find_obsolete_evidence,
    )

    themes = [name.strip() for name in args.themes.split(",") if name.strip()]
    if not themes:
        raise PackageError("release-batch --themes must name at least one theme")
    if args.apply:
        required = {
            "--connection": args.connection,
            "--workspace": args.workspace,
            "--minimal-id": args.minimal_id,
            "--business-id": args.business_id,
            "--minimal-url": args.minimal_url,
            "--business-url": args.business_url,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise PackageError("release-batch --apply requires " + ", ".join(missing))
    payload = {
        "status": "READY" if args.apply else "DRY_RUN",
        "themes": themes,
        "secondary": str(args.secondary),
        "resume": bool(args.resume),
        "evidenceRoot": str(args.evidence_root),
    }
    if args.report_obsolete:
        package_shas = current_package_shas(args.repo_root.resolve(), themes)
        payload["obsolete"] = [
            str(path) for path in find_obsolete_evidence(
                args.evidence_root,
                lambda path: evidence_directory_current(path, args.repo_root.resolve(), package_shas),
            )
        ]
    if not args.apply:
        print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
        return 0
    return execute_live_batch(args, tuple(themes))


def _handle_evidence_prune(args: argparse.Namespace) -> int:
    from tools.release_batch import prune_evidence

    root = args.repo_root.resolve() / ".agents/evaluations/runtime"
    paths = prune_evidence(root, keep_latest=args.keep_latest, apply=args.apply)
    payload = {
        "status": "APPLIED" if args.apply else "DRY_RUN",
        "root": str(root),
        "keepLatest": args.keep_latest,
        "targets": [str(path) for path in paths],
    }
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _handle_inspect_iris(args: argparse.Namespace) -> int:
    from lib.theme_factory.iris_inspector import (
        inspect_iris, inventory_from_json, render_drift_report, render_inventory_json,
    )

    current = inspect_iris(args.reference_root)
    rendered_inventory = render_inventory_json(current)
    if args.write:
        rendered_report = render_drift_report(current, current)
        _atomic_write(args.inventory, rendered_inventory)
        _atomic_write(args.report, rendered_report)
        print(f"IRIS_INSPECT status=PASS action=updated tokens={len(current.declarations)}")
        return 0
    if not args.inventory.is_file():
        raise PackageError(f"Missing committed Iris token inventory: {args.inventory}")
    baseline_text = args.inventory.read_text(encoding="utf-8")
    baseline = inventory_from_json(baseline_text)
    rendered_report = render_drift_report(current, baseline)
    expected_report = render_drift_report(baseline, baseline)
    drift = []
    if rendered_inventory != baseline_text:
        drift.append(str(args.inventory))
    if not args.report.is_file() or args.report.read_text(encoding="utf-8") != expected_report:
        drift.append(str(args.report))
    if drift:
        for path in drift:
            print(f"DRIFT {path}")
        if rendered_inventory != baseline_text:
            print(rendered_report, end="")
        return 2
    print(f"IRIS_INSPECT status=PASS action=current tokens={len(current.declarations)}")
    return 0


def run_cli(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except PackageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None):
    code = run_cli(argv)
    if argv is None:
        raise SystemExit(code)
    return code


if __name__ == "__main__":
    main()
