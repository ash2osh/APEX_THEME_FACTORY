#!/usr/bin/env python3
"""`scripts/theme.sh release NAME`: check, package, and (unless --offline) a quick live smoke.

The smoke installs the package into one disposable consumer app, looks at it in the browser at a
desktop and a mobile width, and restores the consumer to the clean export taken first. Nothing is
recorded or committed: the command prints PASS or FAIL and exits 0 or 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
import tempfile
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.theme_factory.errors import PackageError  # noqa: E402

DEFAULT_URL = "http://localhost:8181/ords/r/demo/tf-consumer-minimal-9010/home"


@dataclass(frozen=True)
class ReleaseOptions:
    repo_root: Path
    theme: str
    live: bool = True
    connection: str = "docker-demo"
    workspace: str = "DEMO"
    app_id: int = 9010
    url: str = DEFAULT_URL
    widths: tuple[int, ...] = (1440, 375)
    work_dir: Optional[Path] = None


def assert_pristine(export_dir: Path) -> None:
    """Refuse a consumer that already carries Theme Factory packages (pitfalls §5.7)."""
    from lib.theme_factory.apexlang import read_install_state
    installed, _default, _switcher = read_install_state(Path(export_dir))
    if installed:
        listed = ", ".join(f"{package.name} {package.version}" for package in installed)
        raise PackageError(
            f"The consumer app already has Theme Factory packages ({listed}); re-import "
            "tests/live/consumer-apps/minimal over it first (README: Releasing a theme)"
        )


def _install(root: Path, options: ReleaseOptions):
    from lib.theme_factory.install import InstallOptions, run_install
    return run_install(InstallOptions(
        package_roots=(root,), connection=options.connection, workspace=options.workspace,
        app_id=options.app_id, switcher_mode="enable", backup_dir=Path(options.work_dir) / "backups",
        apply=True, assume_yes=True,
    ))


def browser_problems(zip_path: Path, theme: str, url: str, widths: tuple[int, ...]) -> dict[int, list[str]]:
    """Open one background tab, check every width, close the tab."""
    from tools.browser_check import LiveBrowserMatrix, _text
    from tools.chrome_devtools_client import ChromeDevToolsClient
    client = ChromeDevToolsClient()
    opened = client.call_tool("new_page", {"url": url, "background": True})
    selected = re.findall(r"^(\d+): .*\[selected\]", _text(opened), re.MULTILINE)
    if len(selected) != 1:
        raise PackageError("Chrome did not identify the release background tab")
    page_id = int(selected[0])
    try:
        browser = LiveBrowserMatrix(client, page_id, package=zip_path)
        return {width: browser.capture_row("minimal", url, theme, width).problems(theme) for width in widths}
    finally:
        try:
            client.call_tool("close_page", {"pageId": page_id})
        except Exception:
            pass


def run_release(
    options: ReleaseOptions,
    *,
    checks: Optional[Callable] = None,
    build: Optional[Callable] = None,
    verify: Optional[Callable] = None,
    sqlcl_factory: Optional[Callable] = None,
    pristine_check: Callable = assert_pristine,
    extract: Optional[Callable] = None,
    install: Callable = _install,
    browser: Callable = browser_problems,
    out: Callable[[str], None] = print,
) -> int:
    from lib.theme_factory.archive import build_package, extract_package, verify_package
    from lib.theme_factory.checks import run_theme_checks
    from lib.theme_factory.sqlcl import SqlclClient
    checks = checks or run_theme_checks
    build = build or build_package
    verify = verify or verify_package
    sqlcl_factory = sqlcl_factory or SqlclClient
    extract = extract or extract_package
    repo_root = Path(options.repo_root).resolve()
    theme = options.theme

    report = checks(repo_root, theme)
    if report.status != "PASS":
        out(f"RELEASE theme={theme} status=FAIL step=check")
        for issue in report.issues:
            out(f"  {issue}")
        return 1
    zip_path = build(repo_root, theme, repo_root / "dist" / theme)
    verify(zip_path)
    if not options.live:
        out(f"RELEASE theme={theme} status=PASS live=skipped package={zip_path}")
        return 0

    work = Path(options.work_dir or tempfile.mkdtemp(prefix=f"theme-release-{theme}-"))
    options = ReleaseOptions(**{**options.__dict__, "work_dir": work})
    sqlcl = sqlcl_factory(options.connection)
    baseline = sqlcl.export_apexlang(options.app_id, work / "baseline")
    pristine_check(baseline)
    try:
        installed = install(extract(zip_path, work / "package"), options)
        if installed.exit_code != 0:
            out(f"RELEASE theme={theme} status=FAIL step=install ({installed.status})")
            return 1
        problems = browser(zip_path, theme, options.url, options.widths)
    finally:
        sqlcl.import_apexlang(baseline, options.workspace, options.app_id)
    failed = {width: found for width, found in problems.items() if found}
    out(f"RELEASE theme={theme} status={'FAIL' if failed else 'PASS'} package={zip_path}")
    for width, found in failed.items():
        for problem in found:
            out(f"  {width}px: {problem}")
    return 1 if failed else 0
