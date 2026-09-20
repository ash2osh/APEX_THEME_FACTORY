#!/usr/bin/env python3
"""Live release matrix driver (Layer C: database installation).

Runs the portable-package lifecycle against disposable consumer applications through the
same CLIs an operator uses (`lib.theme_factory.cli install|uninstall|restore`), records every
step, and writes the digest-bound raw + summary evidence that `lib/theme_factory/release.py`
requires before a Layer C `PASS` may be claimed.

Operations recorded (spec 2026-09-15-theme-factory-verification-design §3):
  install, reinstall, coexistence, switcherEnableDisable, uninstall, restore, preserveUnrelated

Nothing here provisions or deletes applications; use scripts/provision-consumer-fixtures.sh and
scripts/cleanup-consumer-fixtures.sh for that, with their own confirmations.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `python3 tools/live_matrix.py`

from lib.theme_factory.apexlang import canonical_digest, inspect_export, read_install_state
from lib.theme_factory.sqlcl import SqlclClient
from lib.theme_factory.gitstate import assert_clean_source

REQUIRED_OPERATIONS = (
    "install", "reinstall", "coexistence", "switcherEnableDisable", "uninstall", "restore", "preserveUnrelated",
)


@dataclass(frozen=True)
class ApplicationTarget:
    consumer: str
    app_id: int
    alias: str
    apex_version: str


@dataclass(frozen=True)
class PackageRef:
    theme: str
    version: str
    zip_path: Path
    sha256: str

    @classmethod
    def from_zip(cls, zip_path: Path) -> "PackageRef":
        zip_path = Path(zip_path).resolve()
        with zipfile.ZipFile(zip_path) as archive:
            root = archive.namelist()[0].split("/", 1)[0]
            manifest = json.loads(archive.read(f"{root}/theme.json"))
        return cls(theme=manifest["name"], version=manifest["version"], zip_path=zip_path,
                   sha256=hashlib.sha256(zip_path.read_bytes()).hexdigest())


@dataclass
class OperationResult:
    operation: str
    status: str
    steps: List[dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class LayerCThemeResult:
    status: str
    summary: Path
    operations: Dict[str, OperationResult]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- CLI steps

class Lifecycle:
    def __init__(self, connection: str, workspace: str, target: ApplicationTarget, work_dir: Path, env: Optional[dict]):
        self.connection = connection
        self.workspace = workspace
        self.target = target
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir = self.work_dir / "backups"
        self.env = dict(env or os.environ)
        self.repo_root = Path(__file__).resolve().parent.parent
        self.sqlcl = SqlclClient(connection, env=self.env)

    def extract(self, zip_path: Path) -> Path:
        dest = self.work_dir / "packages" / zip_path.stem
        if not dest.exists():
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(dest)
        return next(dest.iterdir())

    def cli(self, *args: str, confirm: bool = False) -> dict:
        command = [sys.executable, "-m", "lib.theme_factory.cli", *args,
                   "--connection", self.connection, "--workspace", self.workspace, "--app-id", str(self.target.app_id)]
        if args[0] != "restore":
            command += ["--backup-dir", str(self.backup_dir)]
        result = subprocess.run(command, input=f"{self.target.app_id}\n" if confirm else "", text=True,
                                capture_output=True, env=self.env, cwd=self.repo_root, check=False)
        status = next((line.split("Status:", 1)[1].strip().split(" ")[0]
                       for line in result.stdout.splitlines() if line.startswith("Status:")), "")
        return {
            "command": " ".join(args),
            "appId": self.target.app_id,
            "exitCode": result.returncode,
            "status": status,
            "stdoutTail": result.stdout[-1500:],
            "stderrTail": result.stderr[-800:],
        }

    def export(self) -> Path:
        temp = Path(tempfile.mkdtemp(prefix="apex-theme-factory-matrix-", dir=str(self.work_dir)))
        return self.sqlcl.export_apexlang(self.target.app_id, temp)

    @staticmethod
    def unrelated_digests(export_dir: Path) -> Dict[str, str]:
        static_root = export_dir / "shared-components/static-files"
        digests = {}
        if static_root.exists():
            for path in sorted(static_root.rglob("*")):
                rel = path.relative_to(static_root).as_posix()
                if path.is_file() and not rel.startswith("theme-factory/"):
                    digests[rel] = _sha256(path)
        return digests


def _expect(step: dict, status: str, result: OperationResult) -> bool:
    ok = step["exitCode"] == 0 and step["status"] == status
    result.steps.append(step)
    if not ok:
        result.status = "FAIL"
        result.notes.append(f"{step['command']}: expected {status}, got exit {step['exitCode']} status {step['status']!r}")
    return ok


def run_lifecycle(connection: str, workspace: str, target: ApplicationTarget, primary: Path, secondary: Path,
                  work_dir: Path, env: Optional[dict] = None, with_switcher: bool = True) -> Dict[str, OperationResult]:
    """install → reinstall → switcher on → second package → switcher off → uninstall both → restore."""
    life = Lifecycle(connection, workspace, target, work_dir, env)
    primary_root = life.extract(Path(primary))
    secondary_root = life.extract(Path(secondary))
    primary_name = json.loads((primary_root / "theme.json").read_text(encoding="utf-8"))["name"]
    secondary_name = json.loads((secondary_root / "theme.json").read_text(encoding="utf-8"))["name"]
    results = {name: OperationResult(operation=name, status="PASS") for name in REQUIRED_OPERATIONS}

    pristine = life.export()
    pristine_digest = canonical_digest(pristine)
    unrelated_before = life.unrelated_digests(pristine)

    # install: dry-run first (STAGED_ONLY), then apply
    op = results["install"]
    _expect(life.cli("install", "--package-root", str(primary_root)), "STAGED_ONLY", op)
    _expect(life.cli("install", "--package-root", str(primary_root), "--apply", confirm=True), "IMPORTED", op)
    if op.status == "PASS":
        installed = life.export()
        packages, default_theme, _switch = read_install_state(installed)
        if [p.name for p in packages] != [primary_name] or default_theme != primary_name:
            op.status = "FAIL"
            op.notes.append(f"registry after install: {[p.name for p in packages]} default={default_theme}")

    # stale-restore guard: the application has moved on since the dry-run backup, so restoring it
    # must be refused (exit 7) until the operator accepts discarding later changes
    op = results["restore"]
    first_backups = sorted(life.backup_dir.rglob("target.json"))
    if not first_backups:
        op.status = "FAIL"
        op.notes.append("no backup was recorded by the dry-run")
    else:
        stale = life.cli("restore", "--backup", str(first_backups[0].parent), "--apply", confirm=True)
        op.steps.append(stale)
        if stale["exitCode"] != 7:
            op.status = "FAIL"
            op.notes.append(f"restore did not refuse a backup whose application has moved on (exit {stale['exitCode']})")

    # reinstall: idempotent
    op = results["reinstall"]
    _expect(life.cli("install", "--package-root", str(primary_root), "--apply", confirm=True), "IMPORTED", op)
    if op.status == "PASS":
        again = life.export()
        page_zero = next(iter((again / "pages").glob("p00000-*.apx")), None)
        text = page_zero.read_text(encoding="utf-8") if page_zero else ""
        if text.count("region theme_factory_bootstrap (") != 1 or text.count("region theme_factory_bootstrap_dialog (") != 1:
            op.status = "FAIL"
            op.notes.append("bootstrap regions were duplicated or lost on reinstall")

    # switcher enable, then coexistence, then disable
    op_switch = results["switcherEnableDisable"]
    if with_switcher:
        _expect(life.cli("install", "--package-root", str(primary_root), "--with-switcher", "--apply", confirm=True), "IMPORTED", op_switch)
        if op_switch.status == "PASS":
            enabled = life.export()
            target_export = inspect_export(enabled)
            nav_text = target_export.navigation_file.read_text(encoding="utf-8") if target_export.navigation_file else ""
            _, _, switcher_on = read_install_state(enabled)
            if not switcher_on or "entry theme-factory-switcher-parent (" not in nav_text \
                    or "#APP_FILES#theme-factory/runtime/theme-factory-runtime.js" not in target_export.javascript_urls:
                op_switch.status = "FAIL"
                op_switch.notes.append("switcher enable did not produce list entries + runtime URL + registry flag")

    op = results["coexistence"]
    _expect(life.cli("install", "--package-root", str(secondary_root), "--apply", confirm=True), "IMPORTED", op)
    if op.status == "PASS":
        both = life.export()
        packages, default_theme, switcher_on = read_install_state(both)
        css_urls = inspect_export(both).css_urls
        if sorted(p.name for p in packages) != sorted([primary_name, secondary_name]) or default_theme != secondary_name:
            op.status = "FAIL"
            op.notes.append(f"registry after second install: {[p.name for p in packages]} default={default_theme}")
        if with_switcher and not switcher_on:
            op.status = "FAIL"
            op.notes.append("switcher state was not preserved by the second install")
        if len([u for u in css_urls if "theme-factory/packages/" in u]) != 2:
            op.status = "FAIL"
            op.notes.append(f"css urls after second install: {css_urls}")

    if with_switcher:
        _expect(life.cli("install", "--package-root", str(primary_root), "--without-switcher", "--apply", confirm=True), "IMPORTED", op_switch)
        if op_switch.status == "PASS":
            disabled = life.export()
            target_export = inspect_export(disabled)
            nav_text = target_export.navigation_file.read_text(encoding="utf-8") if target_export.navigation_file else ""
            if "theme-factory-" in nav_text or any("theme-factory/runtime" in u for u in target_export.javascript_urls):
                op_switch.status = "FAIL"
                op_switch.notes.append("switcher disable left entries or the runtime URL behind")
    else:
        op_switch.status = "NOT_APPLICABLE"

    # uninstall both, verify zero footprint
    op = results["uninstall"]
    _expect(life.cli("uninstall", "--theme", primary_name, "--apply", confirm=True), "UNINSTALLED", op)
    _expect(life.cli("uninstall", "--theme", secondary_name, "--apply", confirm=True), "UNINSTALLED", op)
    clean = None
    if op.status == "PASS":
        clean = life.export()
        traces = [
            path.relative_to(clean).as_posix() for path in clean.rglob("*")
            if path.is_file() and ("theme-factory" in path.relative_to(clean).as_posix()
                                   or (path.suffix == ".apx" and "theme-factory" in path.read_text(encoding="utf-8", errors="replace")))
        ]
        page_zero = next(iter((clean / "pages").glob("p00000-*.apx")), None)
        if page_zero and "theme_factory" in page_zero.read_text(encoding="utf-8"):
            traces.append(page_zero.name)
        if traces:
            op.status = "FAIL"
            op.notes.append(f"Theme Factory traces after full uninstall: {traces}")

    # preserveUnrelated: every unrelated static file byte-identical to the pristine export
    op = results["preserveUnrelated"]
    if clean is None:
        op.status = "FAIL"
        op.notes.append("uninstall did not complete; unrelated-file comparison skipped")
    else:
        unrelated_after = life.unrelated_digests(clean)
        op.steps.append({"command": "compare unrelated static files", "before": len(unrelated_before), "after": len(unrelated_after)})
        if unrelated_after != unrelated_before:
            op.status = "FAIL"
            op.notes.append("unrelated static files changed across the lifecycle")

    # restore: the very first (pristine) backup. After a byte-clean uninstall the live application
    # already equals it, so no --discard-later-changes is needed; afterwards the export must match.
    op = results["restore"]
    if first_backups:
        backup = first_backups[0].parent
        _expect(life.cli("restore", "--backup", str(backup), "--discard-later-changes", "--apply", confirm=True), "RESTORED", op)
        if op.status == "PASS" and canonical_digest(life.export()) != pristine_digest:
            op.status = "FAIL"
            op.notes.append("restored application digest differs from the pristine export")
    return results


# ---------------------------------------------------------------- evidence writer

def write_layer_c_evidence(evidence_dir: Path, package: PackageRef, git_commit: str, applications: List[ApplicationTarget],
                           operations: Dict[str, OperationResult], captured_at: Optional[str] = None) -> Path:
    """Write raw + summary artifacts and the evidence manifest for Layer C of one theme."""
    captured_at = captured_at or _now()
    evidence_dir = Path(evidence_dir)
    raw_dir = evidence_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    identity = {"schemaVersion": 1, "theme": package.theme, "gitCommit": git_commit,
                "packageSha256": package.sha256, "capturedAt": captured_at}

    def write_raw(name: str, document: dict) -> dict:
        path = raw_dir / f"{name}.json"
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        return {"path": f"raw/{name}.json", "sha256": _sha256(path)}

    app_refs = []
    for app in applications:
        app_refs.append({
            "appId": str(app.app_id), "appAlias": app.alias, "consumer": app.consumer,
            "evidence": write_raw(f"application-{app.consumer}", {
                **identity, "evidenceType": "sqlcl-application", "consumer": app.consumer,
                "appId": str(app.app_id), "appAlias": app.alias, "apexVersion": app.apex_version, "status": "PASS",
            }),
        })
    operation_refs = {}
    failures = []
    for name in REQUIRED_OPERATIONS:
        result = operations.get(name) or OperationResult(operation=name, status="UNVERIFIED", notes=["not executed"])
        operation_refs[name] = write_raw(f"operation-{name}", {**identity, "evidenceType": "sqlcl-operation", **asdict(result)})
        if result.status != "PASS":
            failures.append(f"{name}: {result.status} {' | '.join(result.notes)}".strip())
    status = "PASS" if not failures else "FAIL"
    summary = {
        **identity, "layer": "C", "check": "database_installation", "status": status,
        "results": {"applications": app_refs, "operationEvidence": operation_refs, "failures": failures},
    }
    summary_path = evidence_dir / "database_installation.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest_path = evidence_dir / "evidence.json"
    manifest = {"schemaVersion": 1, "theme": package.theme, "checks": []}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["checks"] = [c for c in manifest.get("checks", []) if not (c.get("layer") == "C" and c.get("check") == "database_installation")]
    manifest["checks"].append({
        "layer": "C", "check": "database_installation", "status": status,
        "artifact": summary_path.name, "artifactSha256": _sha256(summary_path),
        "details": (f"Live SQLcl lifecycle on {', '.join(a.alias for a in applications)} at commit {git_commit[:12]}"
                    + ("" if status == "PASS" else f"; failures: {'; '.join(failures)}")),
    })
    manifest["checks"].sort(key=lambda c: (c["layer"], c["check"]))
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return summary_path


def run_layer_c_theme(
    connection: str,
    workspace: str,
    targets: List[ApplicationTarget],
    primary: PackageRef,
    secondary: PackageRef,
    work_dir: Path,
    evidence_dir: Path,
    git_commit: str,
    *,
    env: Optional[dict] = None,
    lifecycle_runner=run_lifecycle,
    evidence_writer=write_layer_c_evidence,
    clean_checker=assert_clean_source,
) -> LayerCThemeResult:
    """Run one candidate across consumers and write evidence only from a clean source tree."""

    combined: Dict[str, OperationResult] = {}
    for target in targets:
        clean_checker()
        results = lifecycle_runner(
            connection, workspace, target, primary.zip_path, secondary.zip_path,
            Path(work_dir) / target.consumer, env=env, with_switcher=True,
        )
        for name, result in results.items():
            merged = combined.setdefault(name, OperationResult(operation=name, status="PASS"))
            merged.steps.extend({"consumer": target.consumer, **step} for step in result.steps)
            merged.notes.extend(f"{target.consumer}: {note}" for note in result.notes)
            if result.status == "FAIL" or (result.status != "PASS" and merged.status == "PASS"):
                merged.status = result.status if result.status == "FAIL" else (
                    merged.status if merged.status == "FAIL" else result.status
                )
    clean_checker()
    summary = evidence_writer(evidence_dir, primary, git_commit, targets, combined)
    status = "PASS" if combined and all(result.status == "PASS" for result in combined.values()) else "FAIL"
    return LayerCThemeResult(status, summary, combined)


# ---------------------------------------------------------------- CLI

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the live Theme Factory release matrix (Layer C)")
    parser.add_argument("--connection", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--minimal-id", type=int, required=True)
    parser.add_argument("--business-id", type=int, required=True)
    parser.add_argument("--primary", type=Path, required=True, help="ZIP whose theme this evidence is for")
    parser.add_argument("--secondary", type=Path, required=True, help="second single-theme ZIP for coexistence")
    parser.add_argument("--evidence-root", type=Path, default=Path(".agents/evaluations/runtime"))
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--apply", action="store_true", help="actually import into the disposable consumers")
    args = parser.parse_args()

    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    # evidence artifacts are outputs of this tool; anything else uncommitted invalidates the binding.
    # Re-checked before each consumer's lifecycle below, not only here - a tree that goes dirty
    # mid-run must abort within that operation, not silently pass it and only fail the next (Task 4).
    try:
        assert_clean_source()
    except RuntimeError as exc:
        print(f"Refusing: {exc}", file=sys.stderr)
        sys.exit(2)
    # The package must be what this source builds: theme.css carries a `Source commit:` banner, and a
    # package built before the final commit (or from a dirty tree) is bound to bytes the source no longer
    # produces. release-check.sh rejects that - but only after the whole matrix has run.
    from lib.theme_factory.gitstate import last_source_commit, package_source_commit, package_matches_source
    source_commit = last_source_commit()
    for label, package in (("primary", args.primary), ("secondary", args.secondary)):
        if not package_matches_source(package, source_commit):
            print(f"Refusing: {label} package {package} was built at {package_source_commit(package)!r}, "
                  f"but the current source is {source_commit!r}; rebuild it before capturing evidence",
                  file=sys.stderr)
            sys.exit(2)
    primary = PackageRef.from_zip(args.primary)
    secondary = PackageRef.from_zip(args.secondary)
    sqlcl = SqlclClient(args.connection)
    targets = []
    for consumer, app_id in (("minimal", args.minimal_id), ("business", args.business_id)):
        meta = sqlcl.preflight(args.workspace, app_id)
        targets.append(ApplicationTarget(consumer=consumer, app_id=meta.app_id, alias=meta.alias, apex_version=meta.apex_version))
    print(f"Targets: {[(t.consumer, t.app_id, t.alias, t.apex_version) for t in targets]}")
    print(f"Primary: {primary.theme} {primary.version} {primary.sha256[:12]}  Secondary: {secondary.theme} {secondary.version}")
    if not args.apply:
        print("Dry run: add --apply to import into the disposable consumers listed above")
        return

    work_dir = args.work_dir or Path(tempfile.mkdtemp(prefix="apex-theme-factory-live-matrix-"))
    combined: Dict[str, OperationResult] = {}
    for target in targets:
        try:
            assert_clean_source()
        except RuntimeError as exc:
            print(f"Refusing: {exc}", file=sys.stderr)
            sys.exit(2)
        results = run_lifecycle(args.connection, args.workspace, target, primary.zip_path, secondary.zip_path,
                                work_dir / target.consumer, with_switcher=True)
        for name, result in results.items():
            merged = combined.setdefault(name, OperationResult(operation=name, status="PASS"))
            merged.steps.extend({"consumer": target.consumer, **step} for step in result.steps)
            merged.notes.extend(f"{target.consumer}: {note}" for note in result.notes)
            if result.status == "FAIL" or (result.status != "PASS" and merged.status == "PASS"):
                merged.status = result.status if result.status == "FAIL" else merged.status if merged.status == "FAIL" else result.status
        print(f"{target.consumer} ({target.app_id}): " + ", ".join(f"{k}={v.status}" for k, v in results.items()))
    evidence_dir = args.evidence_root / f"{args.date}-release-{primary.theme}"
    summary = write_layer_c_evidence(evidence_dir, primary, commit, targets, combined)
    print(f"Layer C evidence written: {summary}")
    print(f"Work dir (backups, exports): {work_dir}")
    if any(result.status != "PASS" for result in combined.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
