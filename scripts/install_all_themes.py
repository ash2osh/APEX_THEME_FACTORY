#!/usr/bin/env python3
"""Generic script to install multiple Theme Factory packages into any APEX application with switcher."""

import argparse
import datetime
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from lib.theme_factory.apexlang import (
    apply_patch,
    canonical_digest,
    inspect_export,
    list_is_static,
    plan_install,
    read_install_state,
)
from lib.theme_factory.errors import PackageError
from lib.theme_factory.discovery import theme_names
from lib.theme_factory.sqlcl import SqlclClient

STATIC_NAV_BAR_FALLBACK = """list navigation-bar (
    name: Navigation Bar

    entry install-app (
        label: Install App
        icon {
            imageIconCssClasses: fa-cloud-download
        }
        layout {
            sequence: 10
        }
        link {
            target: {
                type: url
                url: #
            }
        }
        userDefinedAttributes {
            2: a-pwaInstall
        }
    )

    entry rtl (
        label: RTL
        icon {
            imageIconCssClasses: fa-arrow-right
        }
        layout {
            sequence: 20
        }
        link {
            target: {
                type: url
                url: javascript:toggleRtl();
            }
        }
    )

    entry theme-version (
        label: Theme Version
        icon {
            imageIconCssClasses: fa-hashtag
        }
        layout {
            sequence: 30
        }
        link {
            target: {
                type: url
                url: #
            }
        }
    )

)
"""


def parse_args(argv=None):
    default_themes = theme_names(repo_root)
    parser = argparse.ArgumentParser(
        description="Install Theme Factory packages into an APEX application with switcher support."
    )
    parser.add_argument(
        "--app-id",
        type=int,
        required=True,
        help="Target APEX application ID (required)",
    )
    parser.add_argument(
        "--connection",
        default="docker-demo",
        help="SQLcl saved connection name (default: docker-demo)",
    )
    parser.add_argument(
        "--workspace",
        default="DEMO",
        help="Target APEX workspace name (default: DEMO)",
    )
    parser.add_argument(
        "--themes",
        default=",".join(default_themes),
        help=f"Comma-separated list of theme names to install (default: {','.join(default_themes)})",
    )
    switcher_group = parser.add_mutually_exclusive_group()
    switcher_group.add_argument(
        "--with-switcher",
        dest="switcher",
        action="store_true",
        default=True,
        help="Enable client-side Theme Switcher in navigation bar (default)",
    )
    switcher_group.add_argument(
        "--without-switcher",
        dest="switcher",
        action="store_false",
        help="Install themes without the navigation bar switcher",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to the live database (default is dry-run)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt when running with --apply",
    )
    return parser.parse_args(argv)


def resolve_package_zip(theme_name: str) -> Path:
    direct_zip = repo_root / f"dist/{theme_name}/{theme_name}-1.0.0.zip"
    if direct_zip.is_file():
        return direct_zip
    dist_dir = repo_root / f"dist/{theme_name}"
    if dist_dir.is_dir():
        candidates = sorted(dist_dir.glob("*.zip"))
        if candidates:
            return candidates[-1]
    theme_source = repo_root / f"sample-themes/{theme_name}"
    if theme_source.is_dir():
        print(f"Building package archive for '{theme_name}'...")
        from lib.theme_factory.archive import build_package
        return build_package(repo_root, theme_name, dist_dir)
    raise PackageError(f"Theme '{theme_name}' not found in dist/ or sample-themes/")


def main():
    args = parse_args()
    themes_list = [t.strip() for t in args.themes.split(",") if t.strip()]
    if not themes_list:
        raise ValueError("At least one theme must be specified")

    print(f"Connecting to {args.connection} and running preflight for {args.workspace} app {args.app_id}...")
    sqlcl = SqlclClient(args.connection)
    meta = sqlcl.preflight(args.workspace, args.app_id)
    print(f"Target: App {meta.app_id} ({meta.name}), Alias: {meta.alias}, APEX: {meta.apex_version}")

    stage_temp = Path(tempfile.mkdtemp(prefix=f"tf-app{args.app_id}-install-"))
    pkg_temp = Path(tempfile.mkdtemp(prefix=f"tf-app{args.app_id}-pkgs-"))
    try:
        print(f"\n1. Exporting Application {args.app_id}...")
        staged_dir = sqlcl.export_apexlang(args.app_id, stage_temp)
        pre_digest = canonical_digest(staged_dir)
        print(f"Exported to {staged_dir}")
        print(f"Pre-export canonical digest: {pre_digest}")

        print("\n2. Creating immutable backup...")
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_dir = repo_root / f"theme-factory-backups/{args.workspace}-{args.app_id}/{now}-before-themes"
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(staged_dir, backup_dir / "apexlang", dirs_exist_ok=True)
        target_meta = {
            "appId": meta.app_id,
            "alias": meta.alias,
            "name": meta.name,
            "workspace": meta.workspace,
            "apexVersion": meta.apex_version,
            "operation": "install-themes",
            "themes": themes_list,
            "switcherEnabled": args.switcher,
            "timestamp": now,
            "preExportDigest": pre_digest,
        }
        (backup_dir / "target.json").write_text(json.dumps(target_meta, indent=2), encoding="utf-8")
        print(f"Backup recorded at {backup_dir}")

        # Check navigation bar in lists.apx
        lists_file = staged_dir / "shared-components/lists.apx"
        if lists_file.is_file() and args.switcher:
            lists_text = lists_file.read_text(encoding="utf-8")
            nav_match = re.search(r"list navigation-bar \([\s\S]*?\n\)\n", lists_text)
            if nav_match:
                list_body = nav_match.group(0)
                if not list_is_static(list_body):
                    print("\n3. Migrating legacy dynamic SQL navigation-bar to static list...")
                    lists_text = lists_text[:nav_match.start()] + STATIC_NAV_BAR_FALLBACK + lists_text[nav_match.end():]
                    lists_file.write_text(lists_text, encoding="utf-8")
                    print("Legacy SQL navigation bar converted to declarative static list.")
                else:
                    print("\n3. Target application navigation bar is already static.")
            else:
                print("\n3. No list 'navigation-bar' block detected; installer will attach to referenced navigation list.")

        print("\n4. Staging theme packages sequentially...")
        mode = "enable" if args.switcher else "disable"
        for theme_name in themes_list:
            zip_path = resolve_package_zip(theme_name)
            extract_dir = pkg_temp / theme_name
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract_dir)
            pkg_root = extract_dir / f"{theme_name}-1.0.0"
            if not pkg_root.is_dir():
                # Look for single root directory
                roots = [d for d in extract_dir.iterdir() if d.is_dir()]
                pkg_root = roots[0] if roots else extract_dir

            patch = plan_install(staged_dir, pkg_root, mode=mode)
            apply_patch(patch)
            print(f"  -> Staged theme '{theme_name}' (switcher mode: {mode})")

        packages, default_theme, switcher_on = read_install_state(staged_dir)
        print(f"\nStaged install summary:")
        print(f"  Installed themes: {[p.name for p in packages]}")
        print(f"  Default theme:    {default_theme}")
        print(f"  Switcher enabled: {switcher_on}")

        print("\n5. Validating staged export with SQLcl...")
        sqlcl.validate(staged_dir, args.workspace)
        print("SQLcl validation PASSED successfully!")

        staged_digest = canonical_digest(staged_dir)
        print(f"Final staged digest: {staged_digest}")

        if not args.apply:
            target_meta["postOperationDigest"] = pre_digest
            (backup_dir / "target.json").write_text(json.dumps(target_meta, indent=2), encoding="utf-8")
            print("\nSTATUS: DRY RUN COMPLETED SUCCESSFULLY.")
            print(f"No changes were written to Application {args.app_id}.")
            print(f"To apply this installation to the live database, re-run with --apply:")
            print(f"  {sys.argv[0]} --app-id {args.app_id} --apply")
            return

        print(f"\nTarget Application Confirmation:")
        print(f"  App ID:        {args.app_id} ({meta.name})")
        print(f"  Workspace:     {args.workspace}")
        print(f"  Themes:        {', '.join(themes_list)}")
        print(f"  Switcher:      {'Enabled' if args.switcher else 'Disabled'}")
        print(f"  Backup:        {backup_dir}")

        if not args.yes:
            try:
                typed = input(f"Type application ID {args.app_id} to confirm import: ").strip()
            except EOFError:
                typed = ""
            if typed != str(args.app_id):
                print("Aborted: Confirmation mismatch. Database was NOT modified.")
                sys.exit(7)

        print(f"\n6. Importing into Application {args.app_id} via SQLcl...")
        sqlcl.import_apexlang(staged_dir, args.workspace, confirmed_app_id=args.app_id)
        print(f"SQLcl import PASSED successfully into Application {args.app_id}!")

        target_meta["postOperationDigest"] = staged_digest
        (backup_dir / "target.json").write_text(json.dumps(target_meta, indent=2), encoding="utf-8")
        print(f"Post-operation digest recorded in backup: {staged_digest}")
        print(f"\n=== THEMES SUCCESSFULLY INSTALLED INTO APPLICATION {args.app_id} ===")

    finally:
        shutil.rmtree(stage_temp, ignore_errors=True)
        shutil.rmtree(pkg_temp, ignore_errors=True)


if __name__ == "__main__":
    main()
