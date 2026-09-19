"""Command line interface for Theme Factory tools."""

import argparse
import json
import os
from pathlib import Path
import sys

from lib.theme_factory.archive import build_package, build_package_from_root, verify_package
from lib.theme_factory.errors import PackageError


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="APEX Theme Factory CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # package
    pkg_p = subparsers.add_parser("package", help="Build single-theme ZIP package")
    pkg_p.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root")
    theme_source = pkg_p.add_mutually_exclusive_group(required=True)
    theme_source.add_argument("--theme", help="Theme name in sample-themes/")
    theme_source.add_argument("--theme-root", type=Path, help="Explicit path to theme directory")
    pkg_p.add_argument("--output-dir", type=Path, required=True, help="Directory to place built ZIP")

    # verify-package
    ver_p = subparsers.add_parser("verify-package", help="Verify extracted package checksums and manifest")
    ver_src = ver_p.add_mutually_exclusive_group(required=True)
    ver_src.add_argument("--package-root", type=Path, help="Path to extracted package directory")
    ver_src.add_argument("--package", type=Path, help="Path to package ZIP file")

    # install
    inst_p = subparsers.add_parser("install", help="Install theme into APEX application")
    inst_p.add_argument("--package-root", type=Path, required=True, help="Path to package directory")
    inst_p.add_argument("--connection", required=True, help="SQLcl saved connection name")
    inst_p.add_argument("--workspace", required=True, help="APEX workspace name")
    inst_p.add_argument("--app-id", type=int, required=True, help="APEX application ID")
    switcher_grp = inst_p.add_mutually_exclusive_group()
    switcher_grp.add_argument("--with-switcher", action="store_true", help="Enable theme switcher in app")
    switcher_grp.add_argument("--without-switcher", action="store_true", help="Disable theme switcher in app")
    inst_p.add_argument("--backup-dir", type=Path, default=None, help="Backup directory")
    inst_p.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    inst_p.add_argument("--yes", action="store_true",
                        help="Skip the typed confirmation (for scripts). Removes the wrong-application "
                             "guard: whatever --app-id names is fully replaced without a human check.")

    # uninstall
    uninst_p = subparsers.add_parser("uninstall", help="Uninstall theme from APEX application")
    uninstall_source = uninst_p.add_mutually_exclusive_group(required=True)
    uninstall_source.add_argument("--theme", help="Name of installed theme to remove")
    uninstall_source.add_argument(
        "--package-root",
        type=Path,
        help="Path to the single-theme package whose theme should be removed",
    )
    uninst_p.add_argument("--connection", required=True, help="SQLcl saved connection name")
    uninst_p.add_argument("--workspace", required=True, help="APEX workspace name")
    uninst_p.add_argument("--app-id", type=int, required=True, help="APEX application ID")
    uninst_p.add_argument("--backup-dir", type=Path, default=None, help="Backup directory")
    uninst_p.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")

    # restore
    rest_p = subparsers.add_parser("restore", help="Restore application from backup")
    rest_p.add_argument("--connection", required=True, help="SQLcl saved connection name")
    rest_p.add_argument("--workspace", required=True, help="APEX workspace name")
    rest_p.add_argument("--app-id", type=int, required=True, help="APEX application ID")
    rest_p.add_argument("--backup", type=Path, required=True, help="Path to backup directory containing target.json and apexlang/")
    rest_p.add_argument("--apply", action="store_true", help="Apply restore to live application")
    rest_p.add_argument(
        "--discard-later-changes",
        action="store_true",
        help="Restore even though the application changed after the backed-up operation completed",
    )

    # font add
    font_p = subparsers.add_parser("font", help="Manage vendored theme fonts")
    font_subparsers = font_p.add_subparsers(dest="font_command", required=True)
    font_add = font_subparsers.add_parser("add", help="Install static WOFF2 faces from a pinned variable font")
    font_add.add_argument("name", help="Theme name in sample-themes/")
    font_add.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root")
    font_add.add_argument("--family", required=True, help="Expected upstream family name")
    font_add.add_argument("--metadata-url", required=True, help="Official upstream METADATA.pb URL")
    font_add.add_argument("--source-revision", required=True, help="Pinned 40-character source commit SHA")
    font_add.add_argument("--weights", required=True, help="Comma-separated static weights")
    font_add.add_argument("--dry-run", action="store_true", help="Resolve metadata without writing assets")
    font_add.add_argument("--json", action="store_true", help="Emit a machine-readable result")

    args = parser.parse_args(argv)

    try:
        if args.subcommand == "package":
            if args.theme_root:
                zip_path = build_package_from_root(args.repo_root, args.theme_root, args.output_dir)
            else:
                zip_path = build_package(args.repo_root, args.theme, args.output_dir)
            print(f"Built package: {zip_path}")
        elif args.subcommand == "verify-package":
            target = args.package or args.package_root
            manifest = verify_package(target)
            print(f"Package '{manifest.name}' v{manifest.version} verified successfully.")
        elif args.subcommand == "install":
            from lib.theme_factory.install import run_install_cli
            run_install_cli(args)
        elif args.subcommand == "uninstall":
            from lib.theme_factory.uninstall import run_uninstall_cli
            run_uninstall_cli(args)
        elif args.subcommand == "restore":
            from lib.theme_factory.uninstall import run_restore_cli
            run_restore_cli(args)
        elif args.subcommand == "font" and args.font_command == "add":
            from lib.theme_factory.font_pipeline import FontRequest, install_font
            try:
                weights = tuple(int(value.strip()) for value in args.weights.split(",") if value.strip())
            except ValueError as exc:
                raise PackageError("--weights must be a comma-separated integer list") from exc
            request = FontRequest(
                family=args.family,
                metadata_url=args.metadata_url,
                source_revision=args.source_revision,
                weights=weights,
            )
            result = install_font(
                args.repo_root,
                args.repo_root / "sample-themes" / args.name,
                request,
                dry_run=args.dry_run,
            )
            payload = {
                "status": "PASS",
                "family": result.family,
                "sourceFilename": result.source_filename,
                "dryRun": result.dry_run,
                "faces": [
                    {"file": face.file, "weight": face.weight, "sha256": face.sha256}
                    for face in result.faces
                ],
            }
            if args.json:
                print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
            else:
                action = "Resolved" if result.dry_run else "Installed"
                print(f"{action} {len(result.faces)} faces for {result.family}.")
    except PackageError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
