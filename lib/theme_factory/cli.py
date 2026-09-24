"""Command line interface for Theme Factory tools."""

import argparse
import json
from pathlib import Path
import sys

from lib.theme_factory.archive import build_package, build_package_from_root, verify_package
from lib.theme_factory.checks import run_theme_checks
from lib.theme_factory.errors import PackageError


def workspace_name(value: str) -> str:
    """APEX workspace names are upper case; accept `demo` as `DEMO`."""
    return value.strip().upper()


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
    install.add_argument("--package-root", type=Path, required=True, action="append",
                         help="Package directory; repeat to install several in one transaction (last = default)")
    install.add_argument("--connection", required=True)
    install.add_argument("--workspace", required=True, type=workspace_name)
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
    uninstall.add_argument("--workspace", required=True, type=workspace_name)
    uninstall.add_argument("--app-id", type=int, required=True)
    uninstall.add_argument("--backup-dir", type=Path, default=None)
    uninstall.add_argument("--apply", action="store_true")
    uninstall.set_defaults(handler=_handle_uninstall)

    restore = subparsers.add_parser("restore", help="Restore application from backup")
    restore.add_argument("--connection", required=True)
    restore.add_argument("--workspace", required=True, type=workspace_name)
    restore.add_argument("--app-id", type=int, required=True)
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--apply", action="store_true")
    restore.add_argument("--discard-later-changes", action="store_true")
    restore.set_defaults(handler=_handle_restore)


def register_workshop_commands(subparsers: argparse._SubParsersAction) -> None:
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

    check = subparsers.add_parser("check", help="Run the offline author checks for one theme")
    check.add_argument("name")
    check.add_argument("--repo-root", type=Path, default=Path.cwd())
    check.add_argument("--json", action="store_true")
    check.set_defaults(handler=_handle_check)

    cover = subparsers.add_parser("cover", help="Capture a checked theme cover through Chrome")
    cover.add_argument("name")
    cover.add_argument("--repo-root", type=Path, default=Path.cwd())
    cover.add_argument("--output", type=Path, required=True)
    cover.add_argument("--apply", action="store_true")
    cover.add_argument("--overwrite", action="store_true")
    cover.add_argument("--json", action="store_true")
    cover.set_defaults(handler=_handle_cover)

    adapters = subparsers.add_parser("adapters", help="Render shared adapter segments into theme CSS")
    adapters.add_argument("--repo-root", type=Path, default=Path.cwd())
    adapters.add_argument("--check", action="store_true", help="Report drift only; exit 1 on drift")
    adapters.set_defaults(handler=_handle_adapters)

    release = subparsers.add_parser("release", help="Check, package, and smoke-test one theme live")
    release.add_argument("name")
    release.add_argument("--repo-root", type=Path, default=Path.cwd())
    release.add_argument("--offline", action="store_true", help="Stop after check + package (no database, no browser)")
    release.add_argument("--connection", default="docker-demo")
    release.add_argument("--workspace", default="DEMO", type=workspace_name)
    release.add_argument("--app-id", type=int, default=9010, help="Disposable consumer app (default 9010)")
    release.add_argument("--url", help="Consumer page to check (default: the 9010 home page)")
    release.set_defaults(handler=_handle_release)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="APEX Theme Factory CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    register_package_commands(subparsers)
    register_install_commands(subparsers)
    register_workshop_commands(subparsers)
    return parser


def _handle_package(args: argparse.Namespace) -> int:
    path = (build_package_from_root(args.repo_root, args.theme_root, args.output_dir)
            if args.theme_root else build_package(args.repo_root, _theme_name(args.theme), args.output_dir))
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
        ComponentProfiles, Focus, Geometry, Identity, Interaction, Palette, Responsive,
        Rhythm, ThemeRecipe, Typography,
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
        2, Identity(args.name, args.title, args.tagline, "Neutral generated starting point.",
                    args.mode, ("neutral", args.mode)), palette,
        Typography("system-ui", "body", ("system-ui", "sans-serif"), (400, 500, 600, 700)),
        Geometry("4px", "8px", "12px", "40px", "hairline", "soft"),
        Focus(palette.accent_alt, "2px", "2px"),
        ComponentProfiles("minimal", "flat", "rounded", "comfortable", "spacious", "flat"),
        None,
        Rhythm("balanced", "editorial", "balanced"),
        Interaction("none", "fill", "precise"),
        Responsive("reflow", 768),
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


def _theme_name(name: str) -> str:
    """A theme name is also a directory under sample-themes/: refuse anything that could leave it."""
    from lib.theme_factory.manifest import NAME_REGEX
    if not isinstance(name, str) or not NAME_REGEX.fullmatch(name):
        raise PackageError(f"Theme name '{name}' must match {NAME_REGEX.pattern}")
    return name


def _handle_font_add(args: argparse.Namespace) -> int:
    from lib.theme_factory.font_pipeline import FontRequest, install_font
    _theme_name(args.name)
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
    report = run_theme_checks(args.repo_root, args.name)
    print(report.to_json() if args.json else report.to_human())
    return 0 if report.status == "PASS" else 2




def _handle_adapters(args: argparse.Namespace) -> int:
    from lib.theme_factory.adapters import main as adapters_main
    return adapters_main(["--repo-root", str(args.repo_root), *(["--check"] if args.check else [])])


def _handle_release(args: argparse.Namespace) -> int:
    from tools.release_smoke import DEFAULT_URL, ReleaseOptions, run_release
    return run_release(ReleaseOptions(
        repo_root=args.repo_root, theme=args.name, live=not args.offline, connection=args.connection,
        workspace=args.workspace, app_id=args.app_id, url=args.url or DEFAULT_URL,
    ))

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
