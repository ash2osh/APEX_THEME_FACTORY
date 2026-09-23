#!/usr/bin/env python3
"""Batch and resume digest-bound Layer C/D theme release evidence.

Agent compatibility is a project-level instruction check and is intentionally not run,
copied, or duplicated by this per-theme batch.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.theme_factory.evidence_cache import (
    EvidenceIdentity,
    checkpoint_valid,
    read_checkpoint_payload,
    write_checkpoint,
)
from lib.theme_factory.errors import PackageError


@dataclass(frozen=True)
class BrowserRowPlan:
    theme: str
    consumer: str
    page: str
    viewport: int
    url: str

    @property
    def key(self) -> str:
        page = re.sub(r"[^a-z0-9]+", "-", self.page.lower()).strip("-") or "page"
        return f"{self.theme}-{self.consumer}-page{page}-{self.viewport}"


@dataclass(frozen=True)
class LayerDBatchReport:
    completed: int
    skipped: int
    artifacts: tuple[Path, ...]


@dataclass(frozen=True)
class LayerCBatchReport:
    status: str
    completed: tuple[str, ...]
    failures: tuple[str, ...]


def run_layer_d_batch(
    rows: Sequence[BrowserRowPlan],
    checkpoint_root: Path,
    *,
    resume: bool,
    identity_for: Callable[[BrowserRowPlan], EvidenceIdentity],
    row_runner: Callable[[BrowserRowPlan], dict],
) -> LayerDBatchReport:
    """Run browser rows, checkpointing each success before starting the next row."""

    checkpoint_root = Path(checkpoint_root)
    completed = 0
    skipped = 0
    artifacts: list[Path] = []
    for row in rows:
        identity = identity_for(row)
        path = checkpoint_root / row.theme / "rows" / f"{row.key}.json"
        if resume and checkpoint_valid(path, identity):
            skipped += 1
            artifacts.append(path)
            continue
        payload = row_runner(row)
        if not isinstance(payload, dict):
            raise TypeError(f"row runner returned non-object evidence for {row.key}")
        write_checkpoint(path, identity, payload)
        completed += 1
        artifacts.append(path)

    # A summary is rebuilt exclusively from exact, validated checkpoints. This makes an
    # interrupted run incomplete rather than optimistically PASS.
    for row in rows:
        path = checkpoint_root / row.theme / "rows" / f"{row.key}.json"
        identity = identity_for(row)
        if not checkpoint_valid(path, identity):
            continue
        read_checkpoint_payload(path)
    return LayerDBatchReport(completed, skipped, tuple(artifacts))


def run_layer_c_batch(
    themes: Sequence[str],
    *,
    restore_baselines: Callable[[], None],
    theme_runner: Callable[[str], bool],
) -> LayerCBatchReport:
    """Run each candidate between two baseline restores; stop at the first failure."""

    completed: list[str] = []
    for theme in themes:
        restore_baselines()
        try:
            ok = bool(theme_runner(theme))
        finally:
            restore_baselines()
        if not ok:
            return LayerCBatchReport("FAIL", tuple(completed), (theme,))
        completed.append(theme)
    return LayerCBatchReport("PASS", tuple(completed), ())


def find_obsolete_evidence(root: Path, identity_is_current: Callable[[Path], bool]) -> tuple[Path, ...]:
    root = Path(root).resolve()
    if not root.is_dir():
        return ()
    return tuple(
        path for path in sorted(root.iterdir())
        if path.is_dir() and not path.is_symlink() and not identity_is_current(path)
    )


def current_package_shas(repo_root: Path, candidates: Sequence[str] = ()) -> dict[str, str]:
    """Return SHA-256 identities for already-built packages without creating new archives."""

    from lib.theme_factory.discovery import theme_names
    values = set(theme_names(repo_root))
    values.update(str(value) for value in candidates)
    found: dict[str, str] = {}
    for value in sorted(values):
        path = Path(value)
        if path.is_file():
            from tools.live_matrix import PackageRef
            package = PackageRef.from_zip(path)
            found[package.theme] = package.sha256
            continue
        archives = sorted((Path(repo_root) / "dist" / value).glob(f"{value}-*.zip"))
        if archives:
            from tools.live_matrix import PackageRef
            package = PackageRef.from_zip(archives[-1])
            found[package.theme] = package.sha256
    return found


def evidence_directory_current(
    path: Path,
    repo_root: Path,
    package_shas: dict[str, str],
) -> bool:
    """Check a release directory against current source and package identities."""

    from lib.theme_factory.gitstate import last_source_commit, source_equivalent
    current_source = last_source_commit(repo_root)
    if current_source is None:
        return False
    for name in ("database_installation.json", "browser_runtime_matrix.json"):
        artifact = path / name
        if not artifact.is_file() or artifact.is_symlink():
            continue
        try:
            document = json.loads(artifact.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        theme = document.get("theme")
        captured_source = document.get("gitCommit")
        package_sha = document.get("packageSha256")
        return (
            isinstance(theme, str)
            and isinstance(captured_source, str)
            and source_equivalent(captured_source, current_source, cwd=repo_root)
            and package_shas.get(theme) == package_sha
        )
    return False


def _theme_from_directory(path: Path) -> str:
    match = re.search(r"-release-(.+)$", path.name)
    return match.group(1) if match else path.name


def prune_evidence(root: Path, *, keep_latest: int, apply: bool) -> tuple[Path, ...]:
    """Plan or apply bounded evidence deletion; dry-run is the default at every caller."""

    if keep_latest < 0:
        raise ValueError("keep_latest must be nonnegative")
    root = Path(root).resolve()
    groups: dict[str, list[Path]] = {}
    if not root.is_dir():
        return ()
    for path in sorted(root.iterdir()):
        if not path.name or path.name == "superseded" or not path.is_dir():
            continue
        groups.setdefault(_theme_from_directory(path), []).append(path)
    targets = tuple(
        path for paths in groups.values()
        for path in sorted(paths, key=lambda item: item.name, reverse=True)[keep_latest:]
    )
    for path in targets:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"evidence deletion target must remain beneath {root}: {path}")
    if apply:
        for path in targets:
            shutil.rmtree(path)
    return targets


def _resolve_package(repo_root: Path, value: str | Path, work_dir: Path, source_commit: str) -> Path:
    """A ZIP path is used as given; a theme name is built fresh from sample-themes/<name>.

    Building here (never reading dist/) binds the batch to the source it just checked clean;
    passing source_commit keeps uncommitted evidence from a resumed run out of the dirty check.
    """
    path = Path(value)
    if path.suffix == ".zip":
        if not path.is_file():
            raise PackageError(f"Package ZIP not found: {path}")
        return path.resolve()
    from lib.theme_factory.archive import build_package_from_root
    name = str(value)
    return build_package_from_root(
        repo_root, repo_root / "sample-themes" / name, Path(work_dir) / "packages" / name,
        source_identity=source_commit,
    ).resolve()


def _artifact_to_row(artifact: dict):
    from tools.browser_matrix import RowCapture
    page_keys = {
        "url", "appId", "appAlias", "pageId", "apexVersion", "browserVersion",
        "bodyClasses", "htmlClasses", "cssUrls", "javascriptUrls", "loadedUrls",
        "windowApp", "windowAlpine", "activeTheme", "registry", "switcherAvailable",
        "fonts", "fontApexFamilyBefore", "fontApexFamilyAfter",
    }
    page = {name: artifact.get(name) for name in page_keys}
    return RowCapture(
        consumer=str(artifact["consumer"]),
        width=int(artifact["viewportWidth"]),
        page=page,
        console_errors=list(artifact.get("consoleErrors", [])),
        failed_requests=list(artifact.get("failedRequests", [])),
        fonts_verified=artifact.get("fontsVerified") is True,
        accessibility_verified=artifact.get("accessibilityVerified") is True,
        persistence_verified=artifact.get("persistenceVerified") is True,
        notes=list(artifact.get("notes", [])),
        declared_face_count=int(artifact.get("declaredFaceCount", 0)),
    )


def execute_live_batch(args, themes: Sequence[str]) -> int:
    """Run the authorized Layer C/D batch with baseline restore and row checkpoints."""

    from lib.theme_factory.evidence_cache import common_check_artifact_valid
    from lib.theme_factory.gitstate import (
        assert_clean_source, last_source_commit, package_matches_source, package_source_commit,
    )
    from lib.theme_factory.sqlcl import SqlclClient
    from tools.browser_matrix import (
        LiveBrowserMatrix, _text, assert_row_identity, build_runtime_artifact,
        write_layer_d_evidence,
    )
    from tools.chrome_devtools_client import ChromeDevToolsClient
    from tools.live_matrix import ApplicationTarget, PackageRef, run_layer_c_theme

    repo_root = Path(args.repo_root).resolve()
    evidence_root = Path(args.evidence_root)
    if not evidence_root.is_absolute():
        evidence_root = repo_root / evidence_root
    evidence_root.mkdir(parents=True, exist_ok=True)
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    work_dir = Path(args.work_dir) if args.work_dir else Path(tempfile.mkdtemp(prefix="theme-release-batch-"))

    if args.common_check_artifact:
        diagnostics: list[str] = []
        if not common_check_artifact_valid(args.common_check_artifact, repo_root, diagnostics=diagnostics):
            raise PackageError("Invalid common-check artifact: " + "; ".join(diagnostics))
    else:
        common_artifact = evidence_root / f"{date}-common-offline.json"
        result = subprocess.run(
            ["bash", "tests/run-common-offline.sh", "--artifact", str(common_artifact)],
            cwd=repo_root, check=False,
        )
        if result.returncode != 0:
            raise PackageError("Common offline verification failed; live batch was not started")

    assert_clean_source(repo_root)
    source_commit = last_source_commit(repo_root)
    if source_commit is None:
        raise PackageError("Unable to determine current source commit")
    packages = tuple(PackageRef.from_zip(_resolve_package(repo_root, value, work_dir, source_commit)) for value in themes)
    secondary = PackageRef.from_zip(_resolve_package(repo_root, args.secondary, work_dir, source_commit))
    for package in (*packages, secondary):
        if not package_matches_source(package.zip_path, source_commit):
            raise PackageError(
                f"Package {package.zip_path} was built at {package_source_commit(package.zip_path)!r}, "
                f"not current source {source_commit}"
            )

    sqlcl = SqlclClient(args.connection)
    targets = []
    for consumer, app_id in (("minimal", args.minimal_id), ("business", args.business_id)):
        meta = sqlcl.preflight(args.workspace, app_id)
        targets.append(ApplicationTarget(consumer, meta.app_id, meta.alias, meta.apex_version))
    apex_versions = {target.apex_version for target in targets}
    if len(apex_versions) != 1:
        raise PackageError(f"Consumer APEX versions differ: {sorted(apex_versions)}")
    apex_version = next(iter(apex_versions))

    baselines = {}
    for target in targets:
        assert_clean_source(repo_root)
        baselines[target.consumer] = sqlcl.export_apexlang(
            target.app_id, work_dir / "baselines" / target.consumer
        )

    package_by_theme = {package.theme: package for package in packages}

    def restore_baselines() -> None:
        for target in targets:
            sqlcl.import_apexlang(baselines[target.consumer], args.workspace, target.app_id)

    def layer_c(theme: str) -> bool:
        result = run_layer_c_theme(
            args.connection, args.workspace, targets, package_by_theme[theme], secondary,
            work_dir / "layer-c" / theme,
            evidence_root / f"{date}-release-{theme}", source_commit,
            clean_checker=lambda: assert_clean_source(repo_root),
        )
        return result.status == "PASS"

    layer_c_report = run_layer_c_batch(
        [package.theme for package in packages],
        restore_baselines=restore_baselines, theme_runner=layer_c,
    )
    if layer_c_report.status != "PASS":
        raise PackageError(f"Layer C failed for {layer_c_report.failures[0]}; remaining candidates were not run")

    package_zips = ",".join(str(package.zip_path) for package in packages)
    for target in targets:
        assert_clean_source(repo_root)
        install = subprocess.run([
            str(repo_root / "scripts/install-all-themes.sh"),
            "--app-id", str(target.app_id), "--connection", args.connection,
            "--workspace", args.workspace, "--packages", package_zips,
            "--with-switcher", "--apply", "--yes",
        ], cwd=repo_root, check=False)
        if install.returncode != 0:
            raise PackageError(f"Candidate-set install failed for {target.consumer}")

    client = ChromeDevToolsClient()
    opened = client.call_tool("new_page", {"url": args.minimal_url, "background": True})
    selected = re.findall(r"^(\d+): .*\[selected\]", _text(opened), re.MULTILINE)
    if len(selected) != 1:
        raise PackageError("Chrome did not identify the release-batch background tab")
    page_id = int(selected[0])
    checkpoint_root = evidence_root / f"{date}-batch-checkpoints"
    try:
        matrix = LiveBrowserMatrix(client, page_id)
        matrix.navigate(args.minimal_url)
        environment = matrix.evaluate(r"""() => {
          const match = navigator.userAgent.match(/(?:Chrome|Chromium)\/[^ ]+/);
          return { apexVersion: String(apex.env.APEX_VERSION),
                   browserVersion: match ? match[0] : navigator.userAgent };
        }""")
        if environment.get("apexVersion") != apex_version:
            raise PackageError("Browser APEX version does not match SQLcl preflight")
        browser_version = str(environment.get("browserVersion") or "")
        if not browser_version:
            raise PackageError("Browser version could not be identified")
        widths = tuple(int(value) for value in args.widths.split(",") if value.strip())
        urls = [("minimal", args.minimal_url), ("business", args.business_url)]
        urls.extend(("business", url.strip()) for url in args.business_extra_urls.split(",") if url.strip())
        rows = tuple(
            BrowserRowPlan(package.theme, consumer, url, width, url)
            for package in packages for consumer, url in urls
            for width in (widths if url in {args.minimal_url, args.business_url}
                          else tuple(value for value in widths if value in {min(widths), max(widths)}))
        )

        def identity_for(row: BrowserRowPlan) -> EvidenceIdentity:
            return EvidenceIdentity(
                source_commit, package_by_theme[row.theme].sha256, apex_version,
                browser_version, row.consumer, row.page, row.viewport, "browser-runtime",
            )

        def capture(row: BrowserRowPlan) -> dict:
            assert_clean_source(repo_root)
            matrix.package = package_by_theme[row.theme].zip_path
            captured = matrix.capture_row(row.consumer, row.url, row.theme, row.viewport)
            assert_clean_source(repo_root)
            artifact = build_runtime_artifact(
                row.theme, source_commit, package_by_theme[row.theme].sha256, captured
            )
            assert_row_identity(artifact, identity_for(row))
            return artifact

        report = run_layer_d_batch(
            rows, checkpoint_root, resume=args.resume,
            identity_for=identity_for, row_runner=capture,
        )
        for package in packages:
            theme_rows = []
            for row in rows:
                if row.theme != package.theme:
                    continue
                path = checkpoint_root / row.theme / "rows" / f"{row.key}.json"
                if not checkpoint_valid(path, identity_for(row)):
                    raise PackageError(f"Layer D checkpoint is missing or stale: {row.key}")
                theme_rows.append(_artifact_to_row(read_checkpoint_payload(path)))
            assert_clean_source(repo_root)
            write_layer_d_evidence(
                evidence_root / f"{date}-release-{package.theme}", package.theme,
                source_commit, package.sha256, theme_rows,
            )
        print(json.dumps({
            "status": "PASS", "layerDRowsCompleted": report.completed,
            "layerDRowsSkipped": report.skipped, "themes": list(themes),
        }, separators=(",", ":"), sort_keys=True))
    finally:
        try:
            client.call_tool("close_page", {"pageId": page_id})
        except Exception:
            pass
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    import sys
    from lib.theme_factory.cli import run_cli
    return run_cli(["release-batch", *(list(argv) if argv is not None else sys.argv[1:])])


if __name__ == "__main__":
    raise SystemExit(main())
