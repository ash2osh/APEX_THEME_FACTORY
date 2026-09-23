#!/usr/bin/env python3
"""Install several Theme Factory packages into one APEX application in a single guarded transaction.

A thin front end over lib.theme_factory.install.run_install: the same preflight, backup, drift
guard, validation and post-check as `scripts/theme.sh install`. Themes named with --themes are
built fresh from sample-themes/ (dist/ may hold stale builds — pitfalls §5.5); --packages takes
exact archives, as the release batch does. The last package listed becomes the default theme.
A navigation bar that is not a static list is refused, never rewritten (see MANUAL-INSTALL.md).
"""

import argparse
from pathlib import Path
import shutil
import sys
import tempfile

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from lib.theme_factory.archive import build_package, extract_package
from lib.theme_factory.discovery import theme_names
from lib.theme_factory.errors import PackageError
from lib.theme_factory.install import InstallOptions, run_install


def parse_args(argv=None):
    default_themes = theme_names(repo_root)
    parser = argparse.ArgumentParser(
        description="Install Theme Factory packages into an APEX application with switcher support."
    )
    parser.add_argument("--app-id", type=int, required=True, help="Target APEX application ID (required)")
    parser.add_argument("--connection", default="docker-demo", help="SQLcl saved connection name (default: docker-demo)")
    parser.add_argument("--workspace", default="DEMO", help="Target APEX workspace name (default: DEMO)")
    parser.add_argument(
        "--themes",
        default=",".join(default_themes),
        help=f"Comma-separated themes to build from sample-themes/ (default: {','.join(default_themes)})",
    )
    parser.add_argument("--packages", help="Comma-separated package ZIPs to install as-is (overrides --themes)")
    switcher_group = parser.add_mutually_exclusive_group()
    switcher_group.add_argument("--with-switcher", dest="switcher", action="store_true", default=True,
                                help="Enable the navigation-bar theme switcher (default)")
    switcher_group.add_argument("--without-switcher", dest="switcher", action="store_false",
                                help="Install without the navigation-bar switcher")
    parser.add_argument("--backup-dir", type=Path, default=repo_root / "theme-factory-backups",
                        help="Backup root (default: theme-factory-backups/)")
    parser.add_argument("--apply", action="store_true", help="Import into the database (default is a dry run)")
    parser.add_argument("--yes", action="store_true", help="Skip the typed confirmation with --apply")
    return parser.parse_args(argv)


def stage_packages(args, work_dir: Path) -> tuple[Path, ...]:
    """Extracted package roots, in install order."""
    work_dir = Path(work_dir)
    if args.packages:
        zips = [Path(value.strip()) for value in args.packages.split(",") if value.strip()]
    else:
        names = [value.strip() for value in args.themes.split(",") if value.strip()]
        zips = [build_package(repo_root, name, work_dir / "zips" / name) for name in names]
    if not zips:
        raise PackageError("At least one theme or package must be given")
    return tuple(extract_package(zip_path, work_dir / "packages" / zip_path.stem) for zip_path in zips)


def main(argv=None) -> int:
    args = parse_args(argv)
    work_dir = Path(tempfile.mkdtemp(prefix=f"tf-app{args.app_id}-pkgs-"))
    try:
        roots = stage_packages(args, work_dir)
        report = run_install(InstallOptions(
            package_roots=roots,
            connection=args.connection,
            workspace=args.workspace,
            app_id=args.app_id,
            switcher_mode="enable" if args.switcher else "disable",
            backup_dir=args.backup_dir,
            apply=args.apply,
            assume_yes=args.yes,
        ))
    except PackageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exc.exit_code
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
