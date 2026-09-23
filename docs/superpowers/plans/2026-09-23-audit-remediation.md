# Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Project preference (overrides the recommendation above):** the user has asked, repeatedly, that work run
> inline in one session — no subagents, no worktrees — unless they ask otherwise. Use
> superpowers:executing-plans, in the **main working tree** on a branch.

**Goal:** Fix every defect found by the 2026-09-23 repository audit and land the simplifications that are
compatible with the project's rules.

**Architecture:** One guarded install transaction (`lib/theme_factory/install.py`) serves both single and
multi-theme installs. `scripts/install_all_themes.py` becomes a thin front end that always builds from
source. The release batch passes the exact archives it verified to the installer. App 102's static-file sync
moves from a bash script that starts Python ~170 times to one Python module with a `--check` drift gate. It
also ships one bundled CSS file per theme instead of 9 chained `@import`s. Dead tools are deleted. The
pitfalls record becomes a short index plus one file per layer.

**Tech Stack:** Python 3.10+ standard library (`lib/` is copied into every package ZIP — no third-party
imports there), bash, `unittest`, SQLcl 26.2 (`sql -name docker-demo`), APEX 26.1.4 APEXLang, Chrome DevTools
MCP via the project daemon.

**Spec:** the audit findings table below (from the 2026-09-23 audit conversation; there is no separate spec
file). Background rules: `AGENTS.md`, `docs/PROJECT.md`, `.agents/knowledge/pitfalls.md` §5.x (evidence
binding) and §5.5 (hardcoded versions).

## Global Constraints

- APEX 26.1.x, Universal Theme 42, theme style **Iris only**. Never switch styles or use Theme Roller.
- Browser checks **only** through `python3 tools/chrome_devtools_client.py <tool> '<json>'`. Never call a
  `chrome-devtools` MCP tool directly, never start a second daemon. Open your own tab with
  `new_page {"background": true}`, pass its `pageId` to every call, close it when done. Never navigate with
  `#theme=`. Use `emulate`, not `resize_page`.
- `apex-import.sh`, `git push`, and anything that imports into an APEX application are **run by the user**.
  Hand over the exact commands. Imports into consumer apps 9010/9011 go through the release batch, which the
  user runs.
- Every built ZIP contains exactly one theme. Portable theme assets (fonts, licenses) stay inside
  `sample-themes/<name>/`. External font URLs are forbidden.
- **Evidence binding:** any committed change outside `.agents/evaluations/runtime/**` and `**/*.md`
  invalidates the Layer C/D release evidence and every package SHA-256. Edits to `AGENTS.md`, `CLAUDE.md`,
  `.agents/rules/**` or `.agents/skills/**` invalidate Layer E (agent compatibility). Phase 6 re-captures
  C/D. Task 14 is the only task that touches Layer E inputs, and it is optional.
- `lib/theme_factory/*.py` is copied into every package (`archive.py` step 5). New modules there are shipped
  automatically and must use the standard library only.
- Gate after every task: `tests/run-common-offline.sh` ends with `COMMON_OFFLINE_CHECKS status=PASS`.
  Focused runs use `python3 -m unittest tests.<module> -v`.
- Commit after every task on branch `audit-remediation`. End every commit message with the trailer
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Audit findings → tasks

| # | Finding (evidence) | Task |
|---|---|---|
| B1 | `install_all_themes.resolve_package_zip` falls back to any ZIP in `dist/` (sorted by name) and hardcodes `-1.0.0` (install_all_themes.py:141–163, 230). On this machine it resolves linen → `linen-1.0.0.zip` (source 1.1.0), solarized-dark → 1.1.0 (source 1.2.0), estate-slate(-dark) → 1.0.0 (source 1.1.0). Same-version source edits are never rebuilt. | 1, 3, 4 |
| B2 | `install_all_themes.py` skips all of `install.py`'s guards: APEX 26.1 check, UT 42/ut-26.1/Iris check, package checksum verification, drift guard, post-import check, unique backup directory. | 2, 3 |
| B3 | A SQL-driven nav bar is replaced by a hardcoded copy of app 102's entries (Install App, RTL → `javascript:toggleRtl();`, Theme Version). This drops the consumer's own entries (user menu, sign-out). The single-theme installer correctly refuses this case (apexlang_patch.py:66). No test covers it. The README says the installer "refuses … rather than rewriting your list". | 3 |
| B4 | `execute_live_batch` re-implements Layer C inline, so the tested `run_layer_c_batch` is dead and its tests cover nothing that runs. `run_layer_d_row` (tested, unused) holds an identity guard the live capture lacks. | 5 |
| B5 | The installer registers `.woff2`/`.jpg` with `charSet: utf-8`, the false statement sync-static already stopped making (test_sync_static.py). There are two MIME tables. | 6 |
| B6 | `plan_install` "source mode" writes `theme.css` into its input directory and guesses the repo root (apexlang_patch.py:112–118). It is unreachable from the CLI. | 7 |
| B7 | `apex-import.sh` and `SqlclClient.import_apexlang` rely on `whenever sqlerror` to stop after a failed `apex validate` in the same session. Not verified. | 8 |
| B8 | Per-theme READMEs (solarized-dark, estate-slate, estate-slate-dark) claim VERIFIED. The generated catalog says all 8 are UNVERIFIED. | 13 |
| S1 | `sync-static.sh` starts Python ~170 times (11 s no-op run) and duplicates the MIME table. Nothing checks that the committed export matches its sources. | 9, 10 |
| S2 | `app.css` → 8 × `theme.css` → tokens + 7 modules each: ~79 chained CSS requests on every app 102 page. | 10 |
| S3 | Dead code: `tools/capture_evidence.py`, `scripts/check-runtime-parity.sh` + `tools/runtime_parity.py`, `tools/theme_visual_diff.py` (test-only), `scripts/_font-css.py` (after Task 9). | 9, 11 |
| S4 | 6.6 MB of committed runtime evidence: 3 generations per theme, plus `superseded/` (85 files) and loose files. | 17 |
| S5 | `pitfalls.md` (46 KB) must be skimmed before every theme/runtime/import task. | 12 |
| S6 | 8 completed implementation plans (~300 KB) in `docs/superpowers/plans/`. | 13 |
| S7 | `AGENTS.md` makes every session read all of `AGENT_SPEC.md` (38 KB). | 14 (optional, Layer E) |

### Decided out of scope (with reasons)

- **Shared dark-theme CSS template** (audit item 4). `lib/theme_factory/fingerprint.py:84` normalizes
  comments, theme scope and colours, but **not custom-property names**. Moving the near-identical
  `misc.css`/`reports.css` of solarized-dark, velvet-signal and carbon-volt onto one template would make
  those modules byte-identical. The rise in matching profiles would push those pairs toward the
  `PROFILE_COLLISION` release error (≥ 0.92 CSS similarity with ≥ 5 matching profiles). The theme-uniqueness
  design (`docs/superpowers/specs/2026-09-20-release-gates-and-theme-uniqueness-design.md` §18) and the
  scaffold's non-copying guard (`scaffold.py: _validate_non_copying`) exist to prevent exactly this.
- **Sharing the IBM Plex Sans Arabic WOFF2 files between estate-slate and estate-slate-dark.** This breaks
  the `AGENTS.md` rule "Portable theme assets stay inside `sample-themes/<name>/`".
- **Running app 102 through the package installer.** App 102's navigation bar is a SQL list with a live
  "Theme Version" submenu over `apex_applications`. The installer can only attach to static lists, so
  converting it would delete that submenu. This needs a design decision (brainstorming), not a mechanical fix.
  Tasks 9–10 already remove the performance cost of the current path.

---

## Phase 1 — One guarded installer

### Task 1: `extract_package` — read the package root from the archive

**Files:**
- Modify: `lib/theme_factory/archive.py` (add a function after `verify_package`, currently ends line 340)
- Test: `tests/test_package_archive.py`

**Interfaces:**
- Produces: `extract_package(zip_path: Path, destination: Path) -> Path`. It extracts a validated package
  ZIP and returns `destination / <root directory named inside the ZIP>`. It raises `PackageError` on unsafe
  members.

- [ ] **Step 0: Branch in the main tree**

```bash
git switch -c audit-remediation
git add docs/superpowers/plans/2026-09-23-audit-remediation.md
git commit -m "docs: plan the audit remediation" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 1: Write the failing tests** — append inside `class ArchiveTests` in `tests/test_package_archive.py`, and add `from unittest import mock` to the imports:

```python
    def test_extract_package_returns_root_named_by_the_archive(self):
        from lib.theme_factory.archive import extract_package
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"THEME_FACTORY_ALLOW_DIRTY": "1"}):
            zip_path = build_package(self.repo_root, "linen", Path(tmp) / "zip")
            root = extract_package(zip_path, Path(tmp) / "out")
            self.assertEqual(root.name, zip_path.stem)
            self.assertEqual(root.parent, (Path(tmp) / "out").resolve())
            self.assertEqual(verify_package(root).name, "linen")

    def test_extract_package_refuses_traversal_before_writing(self):
        from lib.theme_factory.archive import extract_package
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(bad, "w") as archive:
                archive.writestr("pkg/theme.json", "{}")
                archive.writestr("../escape.txt", "x")
            with self.assertRaises(PackageError):
                extract_package(bad, Path(tmp) / "out")
            self.assertFalse((Path(tmp) / "escape.txt").exists())
```

- [ ] **Step 2: Run them — expect FAIL** (`ImportError: cannot import name 'extract_package'`)

```bash
python3 -m unittest tests.test_package_archive -v 2>&1 | tail -5
```

- [ ] **Step 3: Implement** — add after `verify_package` in `lib/theme_factory/archive.py`:

```python
def extract_package(zip_path: Path, destination: Path) -> Path:
    """Extract a package ZIP and return its single root directory.

    The root is read from the archive itself, never re-spelled from a version string
    (pitfalls §5.5), and every member is validated before anything is written.
    """
    zip_path = Path(zip_path).resolve()
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        root_name = _validate_zip_members(archive)
        archive.extractall(destination)
    root = destination / root_name
    if not root.is_dir():
        raise PackageError(f"Package root '{root_name}' missing after extracting {zip_path}")
    return root
```

- [ ] **Step 4: Run — expect PASS**, then the gate:

```bash
python3 -m unittest tests.test_package_archive -v 2>&1 | tail -3
tests/run-common-offline.sh 2>&1 | tail -1
```

- [ ] **Step 5: Commit**

```bash
git add lib/theme_factory/archive.py tests/test_package_archive.py
git commit -m "feat: extract packages by the root named in the archive" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `run_install` installs one or more packages in one transaction

**Files:**
- Modify: `lib/theme_factory/install.py` (`InstallOptions` :33–42, `_run_install` :128–327, `run_install_cli` :330–351)
- Modify: `lib/theme_factory/cli.py:33` (`--package-root` becomes repeatable)
- Test: `tests/test_installer_cli.py`

**Interfaces:**
- Consumes: `extract_package` (Task 1).
- Produces:
  - `InstallOptions.package_roots: tuple[Path, ...]`, which replaces `package_root`. The **last** package
    becomes the default theme.
  - `theme.sh install --package-root A --package-root B …`.
  - Backup directory names are `<ts>-before-<name>` for one package and `<ts>-before-<n>-themes` for several.
  - `target.json` gains `"themes": [{"name", "version"}, …]`. The `"theme"` and `"themeVersion"` keys stay
    and name the default.

- [ ] **Step 1: Write the failing tests** — in `tests/test_installer_cli.py`:

Add `from lib.theme_factory.archive import extract_package` to the imports. At the end of `setUpClass` add:

```python
        cls.linen_zip = zip_path
        cobalt_zip = build_package_from_root(
            cls.repo_root, cls.repo_root / "sample-themes/cobalt-press", cls.shared_tmp / "dist",
        )
        cls.cobalt_zip = cobalt_zip
        cls.second_package_dir = extract_package(cobalt_zip, cls.shared_tmp / "pkg2")
```

Add the methods:

```python
    def run_install_many(self, *package_dirs: Path, extra=(), stdin: str = "", log: Path = None):
        env = os.environ.copy()
        if log:
            env["FAKE_SQL_LOG"] = str(log)
        roots = [arg for path in package_dirs for arg in ("--package-root", str(path))]
        return subprocess.run(
            ["python3", "-m", "lib.theme_factory.cli", "install", *roots,
             "--connection", "demo", "--workspace", "DEMO", "--app-id", "314",
             "--backup-dir", str(self.tmp / "b"), *extra],
            input=stdin, text=True, capture_output=True, env=env, check=False,
        )

    def test_one_transaction_installs_every_package_and_last_is_default(self):
        from lib.theme_factory.apexlang import read_install_state
        result = self.run_install_many(self.package_dir, self.second_package_dir, extra=["--apply"], stdin="314\n")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Status: IMPORTED", result.stdout)
        store = Path(Path(os.environ["FAKE_SQL_STATE_FILE"]).read_text(encoding="utf-8").strip())
        packages, default_theme, _ = read_install_state(store)
        self.assertEqual(sorted(package.name for package in packages), ["cobalt-press", "linen"])
        self.assertEqual(default_theme, "cobalt-press")
        backups = list((self.tmp / "b" / "DEMO-314").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].name.endswith("-before-2-themes"), backups[0].name)
        target = json.loads((backups[0] / "target.json").read_text(encoding="utf-8"))
        self.assertEqual([item["name"] for item in target["themes"]], ["linen", "cobalt-press"])
        self.assertEqual(target["theme"], "cobalt-press")

    def test_same_theme_twice_is_refused_before_sqlcl(self):
        log = self.tmp / "sql.log"
        result = self.run_install_many(self.package_dir, self.package_dir, log=log)
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("more than once", result.stderr)
        self.assertFalse(log.exists())
```

- [ ] **Step 2: Run — expect FAIL.** argparse keeps only the last `--package-root`, so the first test
      installs one theme and the second never reaches the duplicate check.

```bash
python3 -m unittest tests.test_installer_cli -v 2>&1 | grep -E "FAIL|ERROR|OK" | head
```

- [ ] **Step 3: Make `--package-root` repeatable** — in `lib/theme_factory/cli.py`, `register_install_commands`, replace:

```python
    install.add_argument("--package-root", type=Path, required=True)
```

with

```python
    install.add_argument("--package-root", type=Path, required=True, action="append",
                         help="Package directory; repeat to install several in one transaction (last = default)")
```

- [ ] **Step 4: Change `InstallOptions`** — in `lib/theme_factory/install.py` replace the field `package_root: Path` with:

```python
    package_roots: tuple[Path, ...]
```

- [ ] **Step 5: Replace the whole `_run_install` function** (from `def _run_install` to the line before `def run_install_cli`) with:

```python
def _describe(manifests: list[ThemeManifest]) -> str:
    if len(manifests) == 1:
        return f"theme '{manifests[0].name}' v{manifests[0].version}"
    listed = ", ".join(f"'{manifest.name}' v{manifest.version}" for manifest in manifests)
    return f"themes {listed} (default '{manifests[-1].name}')"


def _run_install(options: InstallOptions, staging: list) -> OperationReport:
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

    # 5. Create immutable backup and target.json
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if options.backup_dir:
        base_dir = options.backup_dir.resolve() / f"{options.workspace}-{options.app_id}"
    else:
        base_dir = Path("./theme-factory-backups").resolve() / f"{options.workspace}-{options.app_id}"

    backup_dir = base_dir / f"{now}-before-{label}"
    count = 1
    while backup_dir.exists():
        backup_dir = base_dir / f"{now}-before-{label}-{count}"
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
        "themes": [{"name": item.name, "version": item.version} for item in manifests],
        "timestamp": now,
        "preExportDigest": pre_digest,
    }
    (backup_dir / "target.json").write_text(json.dumps(target_json, indent=2), encoding="utf-8")

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
        print(f"  Install:   {_describe(manifests)}")
        print(f"  Switcher:  {options.switcher_mode}")
        print(f"  Backup:    {backup_dir}")
        print(f"  Staged:    {staged_dir}")
        print("\nUnified Diff:\n" + "\n".join(diffs))
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
        post_digest = canonical_digest(post_dir)
    finally:
        shutil.rmtree(post_temp, ignore_errors=True)
    _record_post_digest(backup_dir, post_digest)

    print(f"\nResult: IMPORTED {_describe(manifests)} into application {options.app_id}.")
    print("Status: IMPORTED")
    return OperationReport(
        status="IMPORTED",
        exit_code=0,
        backup_dir=backup_dir,
        staged_dir=None,
        message=f"{_describe(manifests)} successfully imported",
    )
```

- [ ] **Step 6: Update `run_install_cli`** — replace `package_root=args.package_root,` with:

```python
        package_roots=tuple(args.package_root),
```

- [ ] **Step 7: Find other constructors of `InstallOptions`** — expected: only `run_install_cli`.

```bash
grep -rn "InstallOptions(\|package_root=" lib tools scripts tests | grep -v "args.package_root\|--package-root"
```

- [ ] **Step 8: Run — expect PASS**, then the gate (the lifecycle and live-matrix fixture tests exercise single installs):

```bash
python3 -m unittest tests.test_installer_cli tests.test_lifecycle_real_shape tests.test_live_matrix -v 2>&1 | tail -3
tests/run-common-offline.sh 2>&1 | tail -1
```

- [ ] **Step 9: Commit**

```bash
git add lib/theme_factory/install.py lib/theme_factory/cli.py tests/test_installer_cli.py
git commit -m "feat: install several packages in one guarded transaction" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `install-all-themes` becomes a thin front end that builds from source

**Files:**
- Rewrite: `scripts/install_all_themes.py`
- Modify: `tests/fixtures/bin/sql:16` (support an absolute fixture directory)
- Modify: `README.md` (section "Install all themes at once (with switcher)", ~lines 91–110)
- Test: `tests/test_installer_cli.py`

**Interfaces:**
- Consumes: `extract_package` (Task 1); `InstallOptions(package_roots=…)` and `run_install` (Task 2);
  `archive.build_package(repo_root, theme_name, output_dir) -> Path`.
- Produces:
  - `install_all_themes.parse_args(argv) -> Namespace` with `themes`, `packages`, `switcher`,
    `backup_dir`, `apply`, `yes`, `app_id`, `connection`, `workspace`.
  - `install_all_themes.stage_packages(args, work_dir: Path) -> tuple[Path, ...]`.
  - `install_all_themes.main(argv=None) -> int`.
  - CLI option `--packages zip1,zip2` (used by Task 4).

- [ ] **Step 1: Let the fake SQLcl serve any fixture directory** — in `tests/fixtures/bin/sql` replace:

```bash
fixture_root="$(cd "$fixture_bin/.." && pwd)/apexlang/${FAKE_SQL_FIXTURE:-minimal}"
```

with

```bash
fixture_root="${FAKE_SQL_FIXTURE_DIR:-$(cd "$fixture_bin/.." && pwd)/apexlang/${FAKE_SQL_FIXTURE:-minimal}}"
```

- [ ] **Step 2: Write the failing tests** — in `tests/test_installer_cli.py`, add `import contextlib` and
      `import io` to the imports. **Delete** `test_resolve_package_zip_prefers_manifest_version_over_legacy_archive`,
      because `resolve_package_zip` is removed. Add:

```python
    def sql_navigation_bar_fixture(self) -> Path:
        app = self.tmp / "sql-nav-app"
        shutil.copytree(self.repo_root / "tests/fixtures/apexlang/real-shape", app)
        lists = app / "shared-components/lists.apx"
        text = lists.read_text(encoding="utf-8")
        head, tail = text.split("list navigation-bar (\n    name: Navigation Bar\n", 1)
        body_end = tail.index("\n)\n")
        lists.write_text(
            head + "list navigation-bar (\n    name: Navigation Bar\n    source {\n        type: sqlQuery\n"
            "        sqlQuery:\n            ```sql\n            select 1 from dual\n            ```\n    }\n"
            + tail[body_end:],
            encoding="utf-8",
        )
        return app

    def test_install_all_refuses_sql_navigation_bar_and_never_imports(self):
        log = self.tmp / "sql.log"
        stderr = io.StringIO()
        env = {"FAKE_SQL_FIXTURE_DIR": str(self.sql_navigation_bar_fixture()), "FAKE_SQL_LOG": str(log)}
        with mock.patch.dict(os.environ, env), contextlib.redirect_stderr(stderr), \
                contextlib.redirect_stdout(io.StringIO()):
            code = install_all_themes.main([
                "--app-id", "314", "--connection", "demo", "--themes", "linen", "--with-switcher",
                "--apply", "--yes", "--backup-dir", str(self.tmp / "b"),
            ])
        self.assertNotEqual(code, 0)
        self.assertIn("MANUAL-INSTALL.md", stderr.getvalue())
        self.assertNotIn("apex import", log.read_text(encoding="utf-8"))

    def test_theme_names_are_built_from_current_source(self):
        args = install_all_themes.parse_args(["--app-id", "314", "--themes", "linen"])
        roots = install_all_themes.stage_packages(args, self.tmp / "work")
        version = json.loads((self.repo_root / "sample-themes/linen/theme.json").read_text(encoding="utf-8"))["version"]
        self.assertEqual([root.name for root in roots], [f"linen-{version}"])
        self.assertTrue(roots[0].is_relative_to((self.tmp / "work").resolve()))

    def test_packages_option_installs_the_given_archives_as_is(self):
        args = install_all_themes.parse_args(["--app-id", "314", "--packages", f"{self.linen_zip},{self.cobalt_zip}"])
        roots = install_all_themes.stage_packages(args, self.tmp / "work")
        self.assertEqual([root.name for root in roots], [self.linen_zip.stem, self.cobalt_zip.stem])

    def test_install_all_installs_current_versions_together(self):
        from lib.theme_factory.apexlang import read_install_state
        with contextlib.redirect_stdout(io.StringIO()):
            code = install_all_themes.main([
                "--app-id", "314", "--connection", "demo", "--themes", "linen,cobalt-press",
                "--without-switcher", "--apply", "--yes", "--backup-dir", str(self.tmp / "b"),
            ])
        self.assertEqual(code, 0)
        store = Path(Path(os.environ["FAKE_SQL_STATE_FILE"]).read_text(encoding="utf-8").strip())
        packages, default_theme, _ = read_install_state(store)
        for name in ("linen", "cobalt-press"):
            source = json.loads((self.repo_root / f"sample-themes/{name}/theme.json").read_text(encoding="utf-8"))
            self.assertEqual({p.name: p.version for p in packages}[name], source["version"])
        self.assertEqual(default_theme, "cobalt-press")
```

- [ ] **Step 3: Run — expect FAIL.** `main()` takes no argv; `stage_packages` doesn't exist.

```bash
python3 -m unittest tests.test_installer_cli -v 2>&1 | grep -E "^(FAIL|ERROR)" | head
```

- [ ] **Step 4: Replace `scripts/install_all_themes.py` entirely with:**

```python
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
```

- [ ] **Step 5: Run — expect PASS.** The refusal test must also show that nothing was imported.

```bash
python3 -m unittest tests.test_installer_cli -v 2>&1 | tail -3
```

- [ ] **Step 6: Update README.md** — replace the whole "Options:" bullet list under
      `### Install all themes at once (with switcher)` with:

```markdown
Options:
- `--app-id <ID>`: Target APEX application ID (required).
- `--connection <CONN>`: SQLcl saved connection name (default: `docker-demo`).
- `--workspace <WS>`: Target APEX workspace name (default: `DEMO`).
- `--themes <list>`: Comma-separated themes, built fresh from `sample-themes/` (default: every discovered theme). The build refuses a dirty tree unless `THEME_FACTORY_ALLOW_DIRTY=1`.
- `--packages <zip,...>`: Install these exact archives instead (used by the release batch).
- `--with-switcher` / `--without-switcher`: Control the navigation-bar switcher (default: `--with-switcher`). A navigation bar that is not a static list is refused, exactly like the single-theme installer — see `MANUAL-INSTALL.md`. This is why app 102 (SQL navigation bar) is served by `scripts/sync-static.sh` instead.
- `--backup-dir <dir>`: Backup root (default: `theme-factory-backups/`).
- `--apply`: Import into the database (default is a dry run). The last theme listed becomes the default.

It runs the same guarded transaction as `scripts/theme.sh install`: APEX 26.1 / UT 42 / Iris preflight,
checksum verification, backup, SQLcl validation, drift guard and post-import check.
```

- [ ] **Step 7: Gate and commit**

```bash
tests/run-common-offline.sh 2>&1 | tail -1
git add scripts/install_all_themes.py tests/fixtures/bin/sql tests/test_installer_cli.py README.md
git commit -m "fix: install-all-themes builds from source and uses the guarded installer" -m "Drops the stale dist/ fallback, the hardcoded 1.0.0 root and the nav-bar rewrite that replaced a consumer's SQL navigation bar with app 102 entries." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Release batch builds fresh packages and installs the exact archives it verified

**Files:**
- Modify: `tools/release_batch.py` (`_resolve_package` :222–235, its call sites :301–302, the candidate-set install :343–352)
- Test: `tests/test_release_batch.py`

**Interfaces:**
- Consumes: `archive.build_package_from_root(repo_root, theme_root, output_dir, source_identity=None) -> Path`;
  `install_all_themes --packages` (Task 3).
- Produces: `_resolve_package(repo_root: Path, value: str | Path, work_dir: Path, source_commit: str) -> Path`.
  A `.zip` path is returned resolved. A theme name is built into `work_dir/packages/<name>/` with
  `source_identity=source_commit`. This passes the dirty-tree check that uncommitted evidence from a
  `--resume` run would otherwise trip, and it is byte-identical to a clean `build_package`.

- [ ] **Step 1: Write the failing tests** — append to class `ReleaseBatchCliTests` in `tests/test_release_batch.py`
      (it already imports `json`, `tempfile`, `Path`):

```python
    def test_named_theme_is_built_fresh_into_the_work_dir(self):
        from tools.release_batch import _resolve_package
        repo = Path(__file__).resolve().parent.parent
        version = json.loads((repo / "sample-themes/linen/theme.json").read_text(encoding="utf-8"))["version"]
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = _resolve_package(repo, "linen", Path(tmp), "0" * 40)
            self.assertEqual(zip_path, (Path(tmp) / "packages/linen" / f"linen-{version}.zip").resolve())

    def test_explicit_zip_is_used_as_given(self):
        from tools.release_batch import _resolve_package
        with tempfile.TemporaryDirectory() as tmp:
            given = Path(tmp) / "x-9.9.9.zip"
            given.write_bytes(b"zip")
            self.assertEqual(_resolve_package(Path(tmp), given, Path(tmp) / "work", "0" * 40), given.resolve())

    def test_candidate_install_receives_the_verified_archives(self):
        source = (Path(__file__).resolve().parent.parent / "tools/release_batch.py").read_text(encoding="utf-8")
        self.assertIn('"--packages"', source)
        self.assertNotIn("resolve_package_zip", source)
```

- [ ] **Step 2: Run — expect FAIL** (wrong arity; source still uses `resolve_package_zip`).

```bash
python3 -m unittest tests.test_release_batch -v 2>&1 | grep -E "^(FAIL|ERROR)"
```

- [ ] **Step 3: Replace `_resolve_package`** with:

```python
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
```

- [ ] **Step 4: Update both call sites** in `execute_live_batch`:

```python
    packages = tuple(PackageRef.from_zip(_resolve_package(repo_root, value, work_dir, source_commit)) for value in themes)
    secondary = PackageRef.from_zip(_resolve_package(repo_root, args.secondary, work_dir, source_commit))
```

- [ ] **Step 5: Install the verified archives** — replace the block that starts
      `theme_names = ",".join(package.theme for package in packages)` and ends at the `raise PackageError(f"Candidate-set install failed …")` with:

```python
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
```

- [ ] **Step 6: Run — expect PASS**, gate, commit

```bash
python3 -m unittest tests.test_release_batch -v 2>&1 | tail -3
tests/run-common-offline.sh 2>&1 | tail -1
git add tools/release_batch.py tests/test_release_batch.py
git commit -m "fix: release batch builds fresh packages and installs the archives it verified" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The live batch runs the tested Layer C/D helpers

**Files:**
- Modify: `tools/release_batch.py` (`LayerCBatchReport` :53–57, `run_layer_c_batch` :99–125, the Layer C loop in `execute_live_batch` :325–340, `capture()` :392–399)
- Modify: `tools/browser_matrix.py` (replace `run_layer_d_row` :418–446 with `assert_row_identity`)
- Test: `tests/test_release_batch.py`, `tests/test_browser_matrix.py`

**Interfaces:**
- Produces:
  - `run_layer_c_batch(themes: Sequence[str], *, restore_baselines: Callable[[], None], theme_runner: Callable[[str], bool]) -> LayerCBatchReport`.
  - `LayerCBatchReport(status: str, completed: tuple[str, ...], failures: tuple[str, ...])`.
  - `browser_matrix.assert_row_identity(artifact: dict, identity: EvidenceIdentity) -> None`, which raises
    `RuntimeError`. The page is deliberately not compared: live identities key rows by URL, while artifacts
    record the APEX page id.

- [ ] **Step 1: Replace the Layer C tests** — in `tests/test_release_batch.py`, class `ReleaseBatchLayerCTests`
      (:119), delete both methods (`test_baseline_is_exported_once_per_consumer_and_restored_around_each_theme`,
      `test_candidate_failure_stops_that_consumer_before_the_next_theme`). Delete the `FakeSql` helper class
      (:100–117), which only those methods used. Add to `ReleaseBatchLayerCTests`:

```python
    def test_layer_c_restores_baselines_around_every_theme(self):
        events = []
        report = run_layer_c_batch(
            ["linen", "citrus-pop"],
            restore_baselines=lambda: events.append("restore"),
            theme_runner=lambda theme: events.append(theme) or True,
        )
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.completed, ("linen", "citrus-pop"))
        self.assertEqual(events, ["restore", "linen", "restore", "restore", "citrus-pop", "restore"])

    def test_layer_c_failure_stops_before_the_next_theme(self):
        events = []

        def runner(theme):
            events.append(theme)
            return False

        report = run_layer_c_batch(["linen", "citrus-pop"], restore_baselines=lambda: events.append("restore"),
                                   theme_runner=runner)
        self.assertEqual((report.status, report.completed, report.failures), ("FAIL", (), ("linen",)))
        self.assertEqual(events, ["restore", "linen", "restore"])

    def test_layer_c_restores_even_when_a_theme_run_raises(self):
        events = []

        def runner(theme):
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            run_layer_c_batch(["linen"], restore_baselines=lambda: events.append("restore"), theme_runner=runner)
        self.assertEqual(events, ["restore", "restore"])
```

- [ ] **Step 2: Replace the Layer D row test** — in `tests/test_browser_matrix.py`, change the import
      `run_layer_d_row,` to `assert_row_identity,`. Replace
      `test_single_row_checks_cleanliness_before_capture_and_checkpoint_write` with:

```python
    def test_row_identity_guard_accepts_a_matching_capture(self):
        artifact = build_runtime_artifact("linen", COMMIT, SHA, capture("business", 1440))
        identity = EvidenceIdentity(COMMIT, SHA, artifact["apexVersion"], artifact["browserVersion"],
                                    "business", "http://local/page1", 1440, "browser-runtime")
        assert_row_identity(artifact, identity)

    def test_row_identity_guard_rejects_a_browser_that_changed_mid_batch(self):
        artifact = build_runtime_artifact("linen", COMMIT, SHA, capture("business", 1440))
        identity = EvidenceIdentity(COMMIT, SHA, artifact["apexVersion"], "Chrome/999.0.0.0",
                                    "business", "http://local/page1", 1440, "browser-runtime")
        with self.assertRaises(RuntimeError) as context:
            assert_row_identity(artifact, identity)
        self.assertIn("browserVersion", str(context.exception))
```

- [ ] **Step 3: Run — expect FAIL** (old signature; `assert_row_identity` missing)

```bash
python3 -m unittest tests.test_release_batch tests.test_browser_matrix -v 2>&1 | grep -E "^(FAIL|ERROR)"
```

- [ ] **Step 4: Implement `run_layer_c_batch`** — in `tools/release_batch.py` replace `LayerCBatchReport` and `run_layer_c_batch` with:

```python
@dataclass(frozen=True)
class LayerCBatchReport:
    status: str
    completed: tuple[str, ...]
    failures: tuple[str, ...]


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
```

- [ ] **Step 5: Use it in `execute_live_batch`** — replace the `for package in packages: try: … if result.status != "PASS": raise …` loop with:

```python
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
```

Delete the later duplicate line `package_by_theme = {package.theme: package for package in packages}` in the Layer D block.

- [ ] **Step 6: Guard every captured row** — in `tools/browser_matrix.py` replace `run_layer_d_row` with:

```python
def assert_row_identity(artifact: dict, identity: EvidenceIdentity) -> None:
    """Refuse a captured row that disagrees with the checkpoint identity it will be filed under.

    The page is not compared: live batch identities key rows by URL, while the artifact
    records the APEX page id.
    """
    mismatched = [
        name for name, expected in (
            ("apexVersion", identity.apex_version),
            ("browserVersion", identity.browser_version),
            ("consumer", identity.consumer),
            ("viewportWidth", identity.viewport),
        )
        if artifact.get(name) != expected
    ]
    if mismatched:
        raise RuntimeError(f"captured browser row does not match its checkpoint identity: {', '.join(mismatched)}")
```

Remove any import that only `run_layer_d_row` used. Then check that nothing else uses those names:

```bash
grep -n "assert_clean_source\|write_checkpoint" tools/browser_matrix.py
```

In `tools/release_batch.py`, add `assert_row_identity` to the `from tools.browser_matrix import (…)`
inside `execute_live_batch`, and change `capture()` to:

```python
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
```

- [ ] **Step 7: Run — expect PASS**, gate, commit

```bash
python3 -m unittest tests.test_release_batch tests.test_browser_matrix -v 2>&1 | tail -3
tests/run-common-offline.sh 2>&1 | tail -1
git add tools/release_batch.py tools/browser_matrix.py tests/test_release_batch.py tests/test_browser_matrix.py
git commit -m "refactor: live release batch runs the tested Layer C/D helpers" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: One static-file registration rule (no `charSet` on binaries)

**Files:**
- Create: `lib/theme_factory/static_files.py`
- Modify: `lib/theme_factory/apexlang_patch.py` (`MIME_BY_SUFFIX` :24–32, block construction :210–229)
- Test: `tests/test_static_files.py`

**Interfaces:**
- Produces: `MIME_BY_SUFFIX: dict[str, str]`, `mime_type(rel: str) -> str`, `is_text_mime(mime: str) -> bool`,
  `file_block(rel: str) -> str`. `file_block` returns the exact `file "<rel>" (\n    mimeType: …[\n    charSet: utf-8]\n)`
  text without a trailing newline — byte-identical to what `sync-static.sh` writes today. Task 9 uses it.
  `apexlang_patch.MIME_BY_SUFFIX` stays importable, so the `lib/theme_factory/apexlang.py` facade is
  unchanged.

- [ ] **Step 1: Write the failing tests** — create `tests/test_static_files.py`:

```python
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from lib.theme_factory.static_files import file_block, mime_type

REPO = Path(__file__).resolve().parent.parent


class StaticFileBlockTests(unittest.TestCase):
    def test_text_assets_declare_utf8(self):
        self.assertEqual(file_block("css/app.css"), 'file "css/app.css" (\n    mimeType: text/css\n    charSet: utf-8\n)')
        self.assertIn("charSet: utf-8", file_block("icons/logo.svg"))
        self.assertIn("charSet: utf-8", file_block("js/app.js.map"))

    def test_binary_assets_declare_no_charset(self):
        for rel, mime in (("css/f/a.woff2", "font/woff2"), ("c/cover.jpg", "image/jpeg"), ("i/x.png", "image/png")):
            self.assertEqual(file_block(rel), f'file "{rel}" (\n    mimeType: {mime}\n)')

    def test_unknown_suffix_is_octet_stream_without_charset(self):
        self.assertEqual(mime_type("x/LICENSE.bin"), "application/octet-stream")
        self.assertNotIn("charSet", file_block("x/LICENSE.bin"))

    def test_installer_registers_fonts_without_charset(self):
        from lib.theme_factory.apexlang import plan_install
        from lib.theme_factory.archive import build_package, extract_package
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"THEME_FACTORY_ALLOW_DIRTY": "1"}):
            package = extract_package(build_package(REPO, "cobalt-press", Path(tmp) / "zip"), Path(tmp) / "pkg")
            app = Path(tmp) / "app"
            shutil.copytree(REPO / "tests/fixtures/apexlang/real-shape", app)
            patch = plan_install(app, package, "preserve")
            registered = patch.after_files[Path("shared-components/static-files.apx")]
            self.assertIn("mimeType: font/woff2\n)", registered)
            self.assertNotIn("font/woff2\n    charSet", registered)
            self.assertIn("mimeType: text/css\n    charSet: utf-8", registered)
```

- [ ] **Step 2: Run — expect FAIL** (`ModuleNotFoundError: lib.theme_factory.static_files`)

```bash
python3 -m unittest tests.test_static_files -v 2>&1 | tail -3
```

- [ ] **Step 3: Create `lib/theme_factory/static_files.py`:**

```python
"""How a static file is registered in APEXLang `shared-components/static-files.apx`.

Shared by the package installer and the app 102 sync so both write the same block. charSet is
only declared for text content: APEX ignores it for binaries, but declaring one is a false
statement in generated source. image/svg+xml is XML text and keeps it.
"""

from pathlib import PurePosixPath

MIME_BY_SUFFIX = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".map": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".woff2": "font/woff2",
    ".txt": "text/plain",
}
TEXT_MIME_TYPES = frozenset({"application/javascript", "application/json", "image/svg+xml"})


def mime_type(rel: str) -> str:
    return MIME_BY_SUFFIX.get(PurePosixPath(rel).suffix.lower(), "application/octet-stream")


def is_text_mime(mime: str) -> bool:
    return mime.startswith("text/") or mime in TEXT_MIME_TYPES


def file_block(rel: str) -> str:
    """The `file "<rel>" ( ... )` block for one static file, without a trailing newline."""
    mime = mime_type(rel)
    charset = "\n    charSet: utf-8" if is_text_mime(mime) else ""
    return f'file "{rel}" (\n    mimeType: {mime}{charset}\n)'
```

- [ ] **Step 4: Use it in the installer** — in `lib/theme_factory/apexlang_patch.py`, delete the
      `MIME_BY_SUFFIX = {…}` literal and add `from lib.theme_factory.static_files import MIME_BY_SUFFIX, file_block`
      to the imports. Replace the loop body and the registry block:

```python
    for src_path, dst_path in staged_copies:
        rel_static = dst_path.relative_to(export_dir / "shared-components/static-files").as_posix()
        new_sf_blocks.append(file_block(rel_static) + "\n")

    # Also register registry.json
    new_sf_blocks.append(file_block("theme-factory/runtime/registry.json") + "\n")
```

  Uninstall removes blocks with `\([^)]*\)` (uninstall.py:86), so it handles both forms. The post-import
  projection compares declared names, not block bodies (apexlang_state.py:369).

- [ ] **Step 5: Run — expect PASS**, gate, commit

```bash
python3 -m unittest tests.test_static_files tests.test_apexlang_patch tests.test_uninstaller_cli -v 2>&1 | tail -3
tests/run-common-offline.sh 2>&1 | tail -1
git add lib/theme_factory/static_files.py lib/theme_factory/apexlang_patch.py tests/test_static_files.py
git commit -m "fix: register binary static files without a charSet in the installer" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Remove `plan_install`'s unreachable "source mode"

**Files:**
- Modify: `lib/theme_factory/apexlang_patch.py:111–118`
- Test: `tests/test_apexlang_patch.py` (class `RealShapeTargetTests`, which defines `fixture_copy` and `PACKAGE`)

- [ ] **Step 1: Write the failing test** — add to `RealShapeTargetTests`:

```python
    def test_source_theme_directory_is_refused_without_writing_into_it(self):
        root = self.fixture_copy()
        source = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, source)
        shutil.copy(self.PACKAGE / "theme.json", source / "theme.json")
        with self.assertRaises(PackageError) as context:
            plan_install(root, source, "preserve")
        self.assertIn("theme.css", str(context.exception))
        self.assertFalse((source / "theme.css").exists())
```

- [ ] **Step 2: Run — expect ERROR** (source mode raises a plain `ValueError` from `flatten_css`)

```bash
python3 -m unittest tests.test_apexlang_patch.RealShapeTargetTests.test_source_theme_directory_is_refused_without_writing_into_it -v 2>&1 | tail -3
```

- [ ] **Step 3: Replace** the block from `theme_css_path = package_root / "theme.css"` through
      `temp_css.write_text(theme_css_content, encoding="utf-8")` with:

```python
    if not (package_root / "theme.css").is_file():
        raise PackageError(
            f"{package_root} has no built theme.css; install a built package, not a source theme directory"
        )
```

- [ ] **Step 4: Run — expect PASS**, gate, commit

```bash
python3 -m unittest tests.test_apexlang_patch -v 2>&1 | tail -3
tests/run-common-offline.sh 2>&1 | tail -1
git add lib/theme_factory/apexlang_patch.py tests/test_apexlang_patch.py
git commit -m "refactor: refuse unbuilt theme directories instead of writing into them" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Phase 2 — SQLcl validate gate

### Task 8: Prove whether a failed `apex validate` stops the session, then fix only if it doesn't

**Files:**
- Modify (outcome B only): `scripts/apex-import.sh`, `lib/theme_factory/sqlcl.py` (`import_apexlang` :178)
- Modify (both outcomes): `.agents/knowledge/pitfalls.md` §4.4 (or `pitfalls/4-tooling.md` if Task 12 ran first)
- Test (outcome B only): `tests/test_sqlcl.py`

- [ ] **Step 1: Hand the probe to the user.** It needs the database, never imports, and works on a throwaway copy:

```bash
tmp="$(mktemp -d)" && cp -R applications/ut "$tmp/ut" && printf '\nthis is not apexlang (\n' >> "$tmp/ut/pages/p00100-redirect.apx"
sql -S -name docker-demo <<SQL; echo "exit=$?"
whenever sqlerror exit failure
apex validate -input $tmp/ut -workspace DEMO
prompt REACHED_AFTER_VALIDATE
exit
SQL
rm -rf "$tmp"
```

- **Outcome A:** no `REACHED_AFTER_VALIDATE` line and `exit` ≠ 0. The same-session pattern is safe. Do
  Step 2A only.
- **Outcome B:** `REACHED_AFTER_VALIDATE` is printed. An import in the same script would have run after a
  failed validation. Do Steps 2B–6B.

- [ ] **Step 2A: Record the verified fact** — append to pitfalls §4.4:

```markdown
- `whenever sqlerror exit failure` **does** stop a script after a failed `apex validate` (probe 2026-09-23:
  a deliberately broken page, no `prompt` after validate ran, non-zero exit), so the one-session
  validate + import in `scripts/apex-import.sh` and `SqlclClient.import_apexlang` cannot import an invalid app.
```

  Then commit: `git commit -am "docs: record the verified SQLcl validate stop" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`.

- [ ] **Step 2B: Write the failing test** — add to `tests/test_sqlcl.py`:

```python
    def test_import_is_never_attempted_after_a_validation_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            env = {"FAKE_SQL_LOG": str(log), "FAKE_SQL_MODE": "validation-warning",
                   "FAKE_SQL_STATE_FILE": str(Path(tmp) / "state")}
            with patch.dict(os.environ, env):
                with self.assertRaises(PackageError):
                    SqlclClient("demo").import_apexlang(Path("tests/fixtures/apexlang/minimal"), "DEMO", 314)
            self.assertNotIn("apex import", log.read_text(encoding="utf-8"))
```

- [ ] **Step 3B: Run — expect FAIL** (the log contains the import that followed the warning)

```bash
python3 -m unittest tests.test_sqlcl -v 2>&1 | grep -E "^(FAIL|ERROR)"
```

- [ ] **Step 4B: Gate with a separate, text-checked session** — in `SqlclClient.import_apexlang`, after
      `apexlang_dir = apexlang_dir.resolve()`, insert:

```python
        # `whenever sqlerror` does not stop the script after a failed `apex validate` (probe
        # 2026-09-23), so refuse here first; the import session still validates in-session.
        self.validate(apexlang_dir, workspace)
```

  In `scripts/apex-import.sh`, insert before the `sql -S -name "$CONN" <<SQL` line:

```bash
"$ROOT/scripts/apex-validate.sh" || { echo "apex-import: validation failed - nothing imported" >&2; exit 1; }
```

- [ ] **Step 5B: Record the fact** in pitfalls §4.4:

```markdown
- `whenever sqlerror exit failure` does **not** stop a script after a failed `apex validate` (probe
  2026-09-23). Imports therefore run a separate, text-checked validate first (`apex-validate.sh`,
  `SqlclClient.validate`), then validate + import in one session. Cost: ~25 s per import.
```

- [ ] **Step 6B: Run, gate, commit**

```bash
python3 -m unittest tests.test_sqlcl tests.test_installer_cli -v 2>&1 | tail -3
tests/run-common-offline.sh 2>&1 | tail -1
git add scripts/apex-import.sh lib/theme_factory/sqlcl.py tests/test_sqlcl.py .agents/knowledge
git commit -m "fix: never import after a failed validation" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Phase 3 — App 102 static sync

### Task 9: Port `sync-static.sh` to Python with a `--check` mode (behaviour-identical)

**Files:**
- Create: `lib/theme_factory/sync_static.py`
- Rewrite: `scripts/sync-static.sh` (becomes a 5-line wrapper)
- Delete: `scripts/_font-css.py` (only `sync-static.sh` used it)
- Test: `tests/test_sync_static_module.py`

**Interfaces:**
- Consumes: `static_files.file_block` (Task 6); `css_bundle.render_font_css(manifest) -> str`;
  `manifest.load_manifest(path, root)`.
- Produces: `sync(root: Path, *, check: bool = False) -> SyncReport` and
  `SyncReport(themes, copied, registered, pruned, drift: list[str])`. CLI:
  `python3 -m lib.theme_factory.sync_static [--repo-root R] [--check]`, where `--check` exits 1 on drift and
  prints `SYNC_STATIC status=PASS|FAIL drift=N`. Task 10 changes only `_theme_files`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_sync_static_module.py`:

```python
from pathlib import Path
import shutil
import tempfile
import unittest

from lib.theme_factory.static_files import file_block
from lib.theme_factory.sync_static import sync

REPO = Path(__file__).resolve().parent.parent
THEMES = ("linen", "cobalt-press")  # linen has no custom fonts; cobalt-press has four WOFF2 faces


class SyncStaticTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        self.root = tmp / "repo"
        shutil.copytree(REPO / "static-files", self.root / "static-files")
        for name in THEMES:
            shutil.copytree(REPO / "sample-themes" / name, self.root / "sample-themes" / name)
        shared = self.root / "applications/ut/shared-components"
        (shared / "static-files/icons").mkdir(parents=True)
        (shared / "static-files/icons/app-icon.png").write_bytes(b"png")
        self.apx = shared / "static-files.apx"
        self.apx.write_text('file "icons/app-icon.png" (\n    mimeType: image/png\n)\n', encoding="utf-8")
        self.dst = shared / "static-files"

    def test_first_sync_copies_registers_and_writes_the_themes_block(self):
        sync(self.root)
        app_css = (self.root / "static-files/css/app.css").read_text(encoding="utf-8")
        self.assertIn('/* @themes:start */\n@import "themes/cobalt-press/theme.css";\n'
                      '@import "themes/linen/theme.css";\n/* @themes:end */', app_css)
        self.assertEqual((self.dst / "css/app.css").read_text(encoding="utf-8"), app_css)
        self.assertTrue((self.dst / "css/themes/linen/theme.json").is_file())
        self.assertTrue(list((self.dst / "css/themes/cobalt-press/fonts").glob("*.woff2")))
        self.assertIn("@font-face", (self.dst / "css/themes/cobalt-press/theme.css").read_text(encoding="utf-8"))
        self.assertFalse((self.dst / "js/vendor/alpine.js").exists())
        self.assertTrue((self.dst / "js/vendor/alpine.min.js").is_file())
        registered = self.apx.read_text(encoding="utf-8")
        self.assertIn(file_block("css/themes/cobalt-press/theme.css"), registered)
        font = next((self.dst / "css/themes/cobalt-press/fonts").glob("*.woff2")).name
        self.assertIn(file_block(f"css/themes/cobalt-press/fonts/{font}"), registered)
        self.assertIn('file "icons/app-icon.png"', registered)

    def test_second_sync_is_a_no_op_and_check_passes(self):
        sync(self.root)
        report = sync(self.root)
        self.assertEqual((report.copied, report.registered, report.pruned), (0, 0, 0))
        self.assertEqual(sync(self.root, check=True).drift, [])

    def test_stale_export_file_is_pruned_with_its_registration(self):
        sync(self.root)
        stale = self.dst / "css/themes/gone/theme.css"
        stale.parent.mkdir(parents=True)
        stale.write_text("x", encoding="utf-8")
        self.apx.write_text(self.apx.read_text(encoding="utf-8") + "\n" + file_block("css/themes/gone/theme.css") + "\n",
                            encoding="utf-8")
        report = sync(self.root)
        self.assertEqual(report.pruned, 1)
        self.assertFalse(stale.parent.exists())
        self.assertNotIn("css/themes/gone/", self.apx.read_text(encoding="utf-8"))

    def test_check_reports_drift_without_writing(self):
        sync(self.root)
        source = self.root / "sample-themes/linen/css/theme.css"
        source.write_text(source.read_text(encoding="utf-8") + "\n/* changed */\n", encoding="utf-8")
        before = {p: p.read_bytes() for p in self.dst.rglob("*") if p.is_file()}
        report = sync(self.root, check=True)
        self.assertTrue(any(item.startswith("css/themes/linen/") for item in report.drift), report.drift)
        self.assertEqual(before, {p: p.read_bytes() for p in self.dst.rglob("*") if p.is_file()})
```

- [ ] **Step 2: Run — expect FAIL** (`ModuleNotFoundError: lib.theme_factory.sync_static`)

```bash
python3 -m unittest tests.test_sync_static_module -v 2>&1 | tail -3
```

- [ ] **Step 3: Create `lib/theme_factory/sync_static.py`:**

```python
"""Assemble app 102's static files into its APEXLang export (scripts/sync-static.sh).

  static-files/css/**, static-files/js/**   -> applications/ut/shared-components/static-files/css|js/**
  sample-themes/<name>/css/**               -> …/css/themes/<name>/**  (theme.css gains the generated @font-face)
  sample-themes/<name>/fonts/**/*.woff2     -> …/css/themes/<name>/fonts/  (only when the theme declares fonts)
  sample-themes/<name>/theme.json           -> …/css/themes/<name>/theme.json  (read by the switcher and page 405)
  sample-themes/<name>/preview/cover.jpg    -> …/css/themes/<name>/cover.jpg

Also regenerates the @themes block in static-files/css/app.css, registers every synced file in
static-files.apx, and prunes export files under css/ and js/ that no longer have a source.
Sources are the only editable copies. check=True reports drift and writes nothing.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re

from lib.theme_factory.css_bundle import render_font_css
from lib.theme_factory.manifest import load_manifest
from lib.theme_factory.static_files import file_block

THEMES_BLOCK_RE = re.compile(r"/\* @themes:start \*/.*?/\* @themes:end \*/", re.S)


@dataclass
class SyncReport:
    themes: list[str]
    copied: int = 0
    registered: int = 0
    pruned: int = 0
    drift: list[str] = field(default_factory=list)


def _byte_order(path: Path) -> bytes:
    return path.as_posix().encode("utf-8")


def _theme_names(themes_root: Path) -> list[str]:
    # Sorting "<name>/" as bytes keeps the historical order (estate-slate-dark before estate-slate).
    names = [path.parent.name for path in themes_root.glob("*/theme.json") if path.is_file()]
    return sorted(names, key=lambda name: (name + "/").encode("utf-8"))


def _skipped(rel: str) -> bool:
    return (
        rel.endswith("README.md")
        or "/.about" in "/" + rel
        or "LICENSE" in rel
        or rel == "js/vendor/alpine.js"
    )


def _files(root: Path) -> list[Path]:
    return sorted((path for path in root.rglob("*") if path.is_file()), key=_byte_order) if root.is_dir() else []


def _theme_files(theme_root: Path, name: str) -> dict[str, bytes]:
    font_css = render_font_css(load_manifest(theme_root / "theme.json", theme_root)).rstrip("\n")
    wanted: dict[str, bytes] = {}
    css_root = theme_root / "css"
    for path in _files(css_root):
        data = path.read_bytes()
        if font_css and path == css_root / "theme.css":
            data = data + b"\n" + font_css.encode("utf-8") + b"\n"
        wanted[f"css/themes/{name}/{path.relative_to(css_root).as_posix()}"] = data
    if font_css:
        for font in (path for path in _files(theme_root / "fonts") if path.suffix == ".woff2"):
            wanted[f"css/themes/{name}/fonts/{font.name}"] = font.read_bytes()
    wanted[f"css/themes/{name}/theme.json"] = (theme_root / "theme.json").read_bytes()
    cover = theme_root / "preview/cover.jpg"
    if cover.is_file():
        wanted[f"css/themes/{name}/cover.jpg"] = cover.read_bytes()
    return wanted


def _reconcile_block(text: str, rel: str) -> tuple[str, str]:
    want = file_block(rel)
    pattern = re.compile(r'file "' + re.escape(rel) + r'" \(\n(?:    [^\n]*\n)*\)')
    match = pattern.search(text)
    if match and match.group(0) == want:
        return text, "same"
    if match:
        text = pattern.sub("", text, count=1)
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip("\n") + "\n\n" + want + "\n", "changed" if match else "new"


def _remove_block(text: str, rel: str) -> str:
    return re.sub(r'\n*file "' + re.escape(rel) + r'" \(\n(?:    .*\n)*\)\n', "\n", text)


def _remove_empty_dirs(base: Path) -> None:
    if not base.is_dir():
        return
    for directory in sorted((p for p in base.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    if not any(base.iterdir()):
        base.rmdir()


def sync(root: Path, *, check: bool = False) -> SyncReport:
    root = Path(root).resolve()
    source = root / "static-files"
    dst = root / "applications/ut/shared-components/static-files"
    apx = root / "applications/ut/shared-components/static-files.apx"
    app_css = source / "css/app.css"
    themes = _theme_names(root / "sample-themes")
    report = SyncReport(themes)

    # (1) themes block in app.css
    block = "\n".join(["/* @themes:start */", *(f'@import "themes/{name}/theme.css";' for name in themes),
                       "/* @themes:end */"])
    current_css = app_css.read_text(encoding="utf-8")
    new_css = THEMES_BLOCK_RE.sub(lambda _match: block, current_css)
    if new_css != current_css:
        if check:
            report.drift.append("static-files/css/app.css: @themes block")
        else:
            app_css.write_text(new_css, encoding="utf-8")

    # (2) desired export content
    wanted: dict[str, bytes] = {}
    for path in _files(source / "css") + _files(source / "js"):
        rel = path.relative_to(source).as_posix()
        if not _skipped(rel):
            wanted[rel] = new_css.encode("utf-8") if path == app_css else path.read_bytes()
    for name in themes:
        wanted.update(_theme_files(root / "sample-themes" / name, name))

    # (3) copy + register
    original_apx = apx.read_text(encoding="utf-8")
    apx_text = original_apx
    for rel, data in wanted.items():
        target = dst / rel
        if not target.is_file() or target.read_bytes() != data:
            report.copied += 1
            if check:
                report.drift.append(f"{rel}: content")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        apx_text, status = _reconcile_block(apx_text, rel)
        if status == "new":
            report.registered += 1
        if status != "same" and check:
            report.drift.append(f"{rel}: registration {status}")

    # (4) prune
    for path in _files(dst / "css") + _files(dst / "js"):
        rel = path.relative_to(dst).as_posix()
        if rel not in wanted:
            report.pruned += 1
            if check:
                report.drift.append(f"{rel}: stale")
            else:
                path.unlink()
                apx_text = _remove_block(apx_text, rel)

    if not check:
        if apx_text != original_apx:
            apx.write_text(apx_text, encoding="utf-8")
        _remove_empty_dirs(dst / "css")
        _remove_empty_dirs(dst / "js")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble app 102 static files into the APEXLang export")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--check", action="store_true", help="Report drift between sources and export; write nothing")
    args = parser.parse_args(argv)
    report = sync(args.repo_root, check=args.check)
    if args.check:
        for item in report.drift:
            print(f"SYNC_STATIC drift {item}")
        print(f"SYNC_STATIC status={'FAIL' if report.drift else 'PASS'} drift={len(report.drift)}")
        return 1 if report.drift else 0
    print(f"sync-static: themes=[{' '.join(report.themes)}] copied={report.copied} "
          f"registered={report.registered} pruned={report.pruned}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run — expect PASS**

```bash
python3 -m unittest tests.test_sync_static_module -v 2>&1 | tail -3
```

- [ ] **Step 5: Replace `scripts/sync-static.sh`** with:

```bash
#!/usr/bin/env bash
# Assemble app 102's static files into the APEXLang export (see lib/theme_factory/sync_static.py).
#   scripts/sync-static.sh           write
#   scripts/sync-static.sh --check   report drift only; exit 1 on drift
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="$ROOT" exec python3 -m lib.theme_factory.sync_static --repo-root "$ROOT" "$@"
```

  Then delete the helper:

```bash
git rm scripts/_font-css.py
```

- [ ] **Step 6: Prove the port is behaviour-identical on the real tree.** The old script was a verified
      no-op on this tree on 2026-09-23 (`copied=0 registered=0 pruned=0` in a clean clone, 11 s):

```bash
time scripts/sync-static.sh
git status --porcelain -- applications static-files
scripts/sync-static.sh --check
```

  Expected: `copied=0 registered=0 pruned=0` in well under a second, no `git status` output,
  `SYNC_STATIC status=PASS drift=0`. Any diff is a porting bug — fix it before continuing.

- [ ] **Step 7: Gate and commit**

```bash
tests/run-common-offline.sh 2>&1 | tail -1
git add lib/theme_factory/sync_static.py scripts/sync-static.sh tests/test_sync_static_module.py
git commit -m "refactor: port sync-static to one Python module with a --check mode" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Ship one bundled CSS file per theme and gate export drift in CI

**Files:**
- Modify: `lib/theme_factory/sync_static.py` (`_theme_files` and the module docstring)
- Modify: `static-files/css/app.css` (header comment)
- Modify: `tests/run-common-offline.sh` (add the drift gate)
- Regenerate: `applications/ut/shared-components/static-files/**`, `…/static-files.apx`
- Test: `tests/test_sync_static_module.py`

**Interfaces:**
- Consumes: `css_bundle.flatten_css(entry: Path, allowed_roots: Sequence[Path]) -> str`, which inlines local
  `@import`s and refuses remote/data/escaping imports.
- Produces: the export holds exactly `css/themes/<name>/{theme.css, theme.json, cover.jpg, fonts/*.woff2}`,
  with no `tokens.css` and no `apex/*.css`. `app.css` still `@import`s one `theme.css` per theme, so the
  CSS request count drops from ~79 to ~15.

- [ ] **Step 1: Write the failing tests** — add to `SyncStaticTests`:

```python
    def test_each_theme_ships_as_one_flattened_stylesheet(self):
        sync(self.root)
        linen = self.dst / "css/themes/linen"
        self.assertEqual(sorted(p.relative_to(linen).as_posix() for p in linen.rglob("*") if p.is_file()),
                         ["cover.jpg", "theme.css", "theme.json"])
        css = (linen / "theme.css").read_text(encoding="utf-8")
        self.assertNotIn("@import", css)
        self.assertIn("html.app-theme-linen", css)

    def test_previously_synced_module_files_are_pruned(self):
        module = self.dst / "css/themes/linen/apex/shell.css"
        module.parent.mkdir(parents=True)
        module.write_text("x", encoding="utf-8")
        self.apx.write_text(self.apx.read_text(encoding="utf-8") + "\n" + file_block("css/themes/linen/apex/shell.css") + "\n",
                            encoding="utf-8")
        sync(self.root)
        self.assertFalse(module.exists())
        self.assertNotIn("css/themes/linen/apex/", self.apx.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run — expect FAIL** (tokens.css and apex/*.css are still copied)

```bash
python3 -m unittest tests.test_sync_static_module -v 2>&1 | grep -E "^(FAIL|ERROR)"
```

- [ ] **Step 3: Bundle** — in `lib/theme_factory/sync_static.py`, add `flatten_css` to the `css_bundle` import:

```python
from lib.theme_factory.css_bundle import flatten_css, render_font_css
```

  Replace the `css_root = …` loop inside `_theme_files` with:

```python
    css_root = theme_root / "css"
    bundled = flatten_css(css_root / "theme.css", (css_root,)).encode("utf-8")
    if font_css:
        bundled += b"\n" + font_css.encode("utf-8") + b"\n"
    wanted[f"css/themes/{name}/theme.css"] = bundled
```

  In the module docstring, replace the `sample-themes/<name>/css/**` line with:

```text
  sample-themes/<name>/css/theme.css (+ its @imports) -> …/css/themes/<name>/theme.css  (one flattened file,
                                                          + generated @font-face; 1 request instead of 9)
```

- [ ] **Step 4: Update the app.css header comment** — in `static-files/css/app.css`, replace the line
      `   themes/     = one package per theme (source: sample-themes/<name>/css), every rule scoped to` with:

```css
   themes/     = one bundled stylesheet per theme (source: sample-themes/<name>/css, flattened by sync-static), every rule scoped to
```

- [ ] **Step 5: Run — expect PASS**, then regenerate the real export and check it:

```bash
python3 -m unittest tests.test_sync_static_module -v 2>&1 | tail -3
scripts/sync-static.sh
scripts/sync-static.sh --check
git status --short -- applications/ut/shared-components | head -20
find applications/ut/shared-components/static-files/css/themes -name '*.css' | sort
```

  Expected: `pruned=64` (8 themes × tokens.css + 7 modules), `status=PASS`, and exactly 8 `theme.css` files.

- [ ] **Step 6: Gate export drift in CI** — in `tests/run-common-offline.sh`, add after the
      `scripts/check-agent-layout.sh` line:

```bash
python3 -m lib.theme_factory.sync_static --repo-root . --check
```

- [ ] **Step 7: Update the docs that describe the export layout.** Find them:

```bash
grep -rn "css/themes/<name>/\*\*\|themes/<name>/\*\*" docs/*.md sample-themes/README.md README.md
```

  For each hit, describe the export as `css/themes/<name>/theme.css` (one flattened file) plus `theme.json`,
  `cover.jpg` and `fonts/`.

- [ ] **Step 8: Gate and commit**

```bash
tests/run-common-offline.sh 2>&1 | tail -2
git add lib/theme_factory/sync_static.py static-files/css/app.css tests/run-common-offline.sh tests/test_sync_static_module.py applications/ut docs README.md sample-themes/README.md
git commit -m "perf: ship one flattened stylesheet per theme to app 102 and gate export drift" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Phase 4 — Dead code

### Task 11: Delete tools that nothing runs

**Files:**
- Delete: `tools/capture_evidence.py`, `scripts/check-runtime-parity.sh`, `tools/runtime_parity.py`,
  `tests/test_runtime_parity.py`, `tools/theme_visual_diff.py`, `tests/test_theme_visual_diff.py`
- Modify: `.agents/evaluations/11-dark-package-coverage.md:7`

Keep `Pillow` in `tools/test-requirements.txt`: `tests/test_theme_cover.py` still imports it.

- [ ] **Step 1: Confirm there are no callers.** Expected: only the files being deleted and eval 11.
      `tests/test_release_report.py:98` is a string label in fixture data.

```bash
git grep -n "capture_evidence\|check-runtime-parity\|runtime_parity\|theme_visual_diff" -- ':!docs/superpowers' ':!.agents/evaluations/runs' ':!.agents/evaluations/runtime'
```

- [ ] **Step 2: Delete**

```bash
git rm tools/capture_evidence.py scripts/check-runtime-parity.sh tools/runtime_parity.py tests/test_runtime_parity.py tools/theme_visual_diff.py tests/test_theme_visual_diff.py
```

- [ ] **Step 3: Update eval 11** — replace line 7 of `.agents/evaluations/11-dark-package-coverage.md` with:

```markdown
- **Permitted Tools**: `chrome-devtools-mcp` (through `tools/chrome_devtools_client.py`), file reading/editing tools.
```

- [ ] **Step 4: Gate and commit.** Expect exactly 9 fewer tests than before (4 parity + 5 visual-diff).

```bash
tests/run-common-offline.sh 2>&1 | grep -E "^Ran|status="
git add -A tools scripts tests .agents/evaluations/11-dark-package-coverage.md
git commit -m "chore: delete unused evidence, parity and visual-diff tools" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Phase 5 — Docs and knowledge (Markdown only; no evidence is invalidated)

### Task 12: Split the pitfalls record into a short index plus one file per layer

**Files:**
- Create: `.agents/knowledge/pitfalls/{1-ut-iris-css,2-apex-javascript-widgets,3-apexlang-builder,4-tooling,5-workflow,6-evaluation-protocol}.md`
- Rewrite: `.agents/knowledge/pitfalls.md` (index; same path, so `AGENTS.md` and every `pitfalls §N.M` citation keep working)
- Test: `tests/test_pitfalls_index.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_pitfalls_index.py`:

```python
from pathlib import Path
import re
import unittest

KNOWLEDGE = Path(__file__).resolve().parent.parent / ".agents/knowledge"
INDEX = KNOWLEDGE / "pitfalls.md"
LAYERS = KNOWLEDGE / "pitfalls"
ENTRY = re.compile(r"^### (\S+) ", re.MULTILINE)


class PitfallsIndexTests(unittest.TestCase):
    def entries(self):
        return [(layer, entry) for layer in sorted(LAYERS.glob("*.md"))
                for entry in ENTRY.findall(layer.read_text(encoding="utf-8"))]

    def test_every_layer_entry_is_listed_in_the_index(self):
        index = INDEX.read_text(encoding="utf-8")
        entries = self.entries()
        self.assertGreaterEqual(len(entries), 51)
        for layer, entry in entries:
            self.assertIn(f"**§{entry}**", index, f"{layer.name}: §{entry} missing from the index")

    def test_entry_numbers_are_unique(self):
        numbers = [entry for _layer, entry in self.entries()]
        self.assertEqual(len(numbers), len(set(numbers)))

    def test_index_links_resolve(self):
        for target in re.findall(r"\]\((pitfalls/[^)]+)\)", INDEX.read_text(encoding="utf-8")):
            self.assertTrue((KNOWLEDGE / target).is_file(), target)

    def test_index_is_short_enough_to_skim(self):
        self.assertLess(len(INDEX.read_text(encoding="utf-8")), 12000)
```

- [ ] **Step 2: Run — expect FAIL** (no `pitfalls/` directory; the index is 46 KB)

```bash
python3 -m unittest tests.test_pitfalls_index -v 2>&1 | tail -3
```

- [ ] **Step 3: Record the entry count, then split mechanically.** Run once from the repo root; the script
      is not committed. Relative links are rewritten because the text moves one directory deeper.

```bash
grep -c '^### ' .agents/knowledge/pitfalls.md   # expect 51
python3 - <<'PY'
import re
from pathlib import Path

knowledge = Path(".agents/knowledge")
source = knowledge / "pitfalls.md"
slugs = {"1": "ut-iris-css", "2": "apex-javascript-widgets", "3": "apexlang-builder",
         "4": "tooling", "5": "workflow", "6": "evaluation-protocol"}
intro, rest = source.read_text(encoding="utf-8").split("\n---\n", 1)
sections = [part.strip("\n") for part in re.split(r"(?m)^(?=## \d+\. )", rest) if part.startswith("## ")]
assert [s[3:].split(".", 1)[0] for s in sections] == list(slugs), [s[:30] for s in sections]
(knowledge / "pitfalls").mkdir(exist_ok=True)

def relink(text):
    return re.sub(r"\]\((?!https?:|mailto:|#|/)([^)\s]+)\)", r"](../\1)", text)

old = "Add to it whenever something surprises you"
assert old in intro
intro = intro.replace(old, "Add to it — the entry in its layer file, its heading line here — whenever something surprises you")
index = [intro.rstrip("\n"), "",
         "Entries live in one file per layer under `pitfalls/`. Entry numbers are stable, so `pitfalls §4.3c` still",
         "means entry 4.3c: find it below and open its layer file. Skim this index before theme, runtime or import",
         "work; read a layer file when one of its headings touches the task.", "", "---", ""]
for section in sections:
    number, title = re.match(r"## (\d+)\. (.+)", section).groups()
    name = f"{number}-{slugs[number]}.md"
    (knowledge / "pitfalls" / name).write_text(
        f"# Pitfalls §{number} — {title}\n\nPart of the [pitfalls index](../pitfalls.md); entry numbers are stable "
        f"and cited as `pitfalls §{number}.N`.\n\n{relink(section)}\n", encoding="utf-8")
    index.append(f"## {number}. {title} — [pitfalls/{name}](pitfalls/{name})")
    index.extend(f"- **§{entry}** {heading}" for entry, heading in re.findall(r"(?m)^### (\S+) (.+)$", section))
    index.append("")
source.write_text("\n".join(index), encoding="utf-8")
PY
cat .agents/knowledge/pitfalls/*.md | grep -c '^### '   # expect the same 51
wc -c .agents/knowledge/pitfalls.md
```

- [ ] **Step 4: Run — expect PASS**, gate, commit

```bash
python3 -m unittest tests.test_pitfalls_index -v 2>&1 | tail -3
tests/run-common-offline.sh 2>&1 | tail -1
git add .agents/knowledge tests/test_pitfalls_index.py
git commit -m "docs: split pitfalls into a skimmable index and per-layer files" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  `tests/test_pitfalls_index.py` is source (not Markdown). Committing it moves `last_source_commit`, like
  every task before Phase 6.

---

### Task 13: Remove finished plans and hand-maintained status rows

**Files:**
- Delete: the 8 plans in `docs/superpowers/plans/` dated 2026-09-15 … 2026-09-22 (keep this plan and all specs;
  code comments cite the specs)
- Modify: `sample-themes/{solarized-dark,estate-slate,estate-slate-dark}/README.md` (their `| Status |` row)

- [ ] **Step 1: Find links to the plans outside `docs/superpowers`**

```bash
git grep -n "superpowers/plans/2026-09-1\|superpowers/plans/2026-09-2[0-2]" -- ':!docs/superpowers'
```

  Replace each link found with plain text: `<plan name> (removed 2026-09-23; see git history)`.

- [ ] **Step 2: Delete the finished plans**

```bash
git rm docs/superpowers/plans/2026-09-15-*.md docs/superpowers/plans/2026-09-17-*.md docs/superpowers/plans/2026-09-19-*.md docs/superpowers/plans/2026-09-20-*.md docs/superpowers/plans/2026-09-22-*.md
ls docs/superpowers/plans   # expect only 2026-09-23-audit-remediation.md
```

- [ ] **Step 3: Point per-theme status at the generated catalog.** In each of the three READMEs, replace the
      whole line that starts with `| Status |` with:

```markdown
| Status | Not hand-maintained — see the generated status table in [`../README.md`](../README.md) (`scripts/theme.sh catalog`). The history below records earlier release rounds. |
```

- [ ] **Step 4: Gate and commit**

```bash
tests/run-common-offline.sh 2>&1 | tail -1
scripts/theme.sh catalog --check
git add -A docs/superpowers/plans sample-themes
git commit -m "docs: drop finished plans and stale per-theme status rows" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14 (optional — ask the user first): Narrow what every session must read in `AGENT_SPEC.md`

This edits `AGENTS.md`, a Layer E input. Afterwards the three agent smokes must be re-run in their own
runtimes (Codex, Claude, Antigravity), which only the user can do. Skip this task unless the user says yes.

**Files:** Modify `AGENTS.md:3`

- [ ] **Step 1: Edit** — replace

```markdown
You are the Oracle APEX design-engineering agent defined in **docs/AGENT_SPEC.md**. Read it first.
```

with

```markdown
You are the Oracle APEX design-engineering agent defined in **docs/AGENT_SPEC.md**. Read §1–§14 and §75–§79
first; §15–§74 are reference — open the section a task needs (skills cite them as `spec §N`).
```

- [ ] **Step 2: Commit**, then hand over the re-verification (user-run):

```bash
git commit -am "docs: scope the mandatory AGENT_SPEC reading" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

```bash
python3 tools/agent_smoke.py claude
python3 tools/agent_smoke.py codex
python3 tools/agent_smoke.py antigravity
scripts/agent-compatibility-check.sh
scripts/agent-compatibility-check.sh --check
```

---

## Phase 6 — Live verification and evidence (user-run pieces)

### Task 15: Verify the bundled stylesheets in app 102

Needs the Chrome daemon. Check it with `pgrep -af chrome_mcp_daemon`. If it isn't running and the user is
away, stop and report — starting it raises a consent prompt.

- [ ] **Step 1: Save the probe** to the scratchpad as `probe.js`:

```js
() => {
  const themes = ["carbon-volt", "citrus-pop", "cobalt-press", "estate-slate", "estate-slate-dark",
                  "linen", "solarized-dark", "velvet-signal"];
  const root = document.documentElement;
  const saved = root.className;
  const region = document.querySelector(".t-Region");
  const probe = () => {
    const body = getComputedStyle(document.body);
    return [body.backgroundColor, body.color, body.fontFamily,
            region ? getComputedStyle(region).backgroundColor : ""].join(" | ");
  };
  const looks = {};
  for (const theme of themes) {
    root.className = saved.replace(/\bapp-theme-[a-z0-9-]+\b/g, "").trim() + " app-theme-" + theme;
    looks[theme] = probe();
  }
  root.className = saved;
  const css = performance.getEntriesByType("resource").filter(e => /\.css(\?|$)/.test(e.name)).length;
  return { css, looks };
}
```

- [ ] **Step 2: Capture BEFORE the user imports.** Open your own background tab. Read the id of the
      `[selected]` page from the output, evaluate, save, and close:

```bash
python3 tools/chrome_devtools_client.py new_page '{"url":"http://localhost:8181/ords/r/demo/ut/getting-started","background":true}'
PAGE=<id from the [selected] line>
python3 tools/chrome_devtools_client.py evaluate_script "$(python3 -c 'import json,sys; print(json.dumps({"pageId": int(sys.argv[1]), "function": open(sys.argv[2]).read()}))' "$PAGE" probe.js)" > before.json
python3 tools/chrome_devtools_client.py close_page "{\"pageId\": $PAGE}"
```

- [ ] **Step 3: Hand over the import (user-run):**

```bash
scripts/sync-static.sh --check
scripts/apex-validate.sh
scripts/apex-import.sh
```

- [ ] **Step 4: Capture AFTER** — repeat Step 2 into `after.json`. Also read console errors from the tab
      with `list_console_messages` before closing it.

- [ ] **Step 5: Compare.** Pass when `after.css` ≤ 20, `before.css` ≥ 60, `looks` is identical for all 8
      themes, and no new console errors. Report the numbers. Any `looks` difference is a bundling defect:
      diff that theme's `theme.css` in the export against the old modules in git history, and fix it before
      Task 16.

---

### Task 16: Re-capture release evidence (user-run)

All source changes above invalidated Layer C/D evidence and every package SHA. Hand over. It needs a
committed, clean tree; consumer apps 9010/9011; and the Chrome daemon. Two batches mirror the 2026-09-21
round: linen is the coexistence partner for the other seven, and solarized-dark is linen's partner.

- [ ] **Step 1: Commit everything, then hand over:**

```bash
scripts/theme.sh release-batch --themes carbon-volt,citrus-pop,cobalt-press,estate-slate,estate-slate-dark,solarized-dark,velvet-signal --secondary linen --connection docker-demo --workspace DEMO --minimal-id 9010 --business-id 9011 --minimal-url http://localhost:8181/ords/r/demo/tf-consumer-minimal-9010/home --business-url http://localhost:8181/ords/r/demo/tf-consumer-business-9011/home --apply
```

```bash
scripts/theme.sh release-batch --themes linen --secondary solarized-dark --connection docker-demo --workspace DEMO --minimal-id 9010 --business-id 9011 --minimal-url http://localhost:8181/ords/r/demo/tf-consumer-minimal-9010/home --business-url http://localhost:8181/ords/r/demo/tf-consumer-business-9011/home --apply
```

- [ ] **Step 2: Commit the new evidence first.** `release-check.sh` rebuilds each package, and the build
      refuses a dirty tree. Evidence-only commits don't move `last_source_commit`.

```bash
git add .agents/evaluations/runtime
git commit -m "evidence: release batch after audit remediation" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 3: Check each theme** (offline; release-check builds the package into `dist/<theme>/`). If the
      two batches ran on different UTC dates, use the date of the batch that ran the common offline suite:

```bash
for t in carbon-volt citrus-pop cobalt-press estate-slate estate-slate-dark linen solarized-dark velvet-signal; do
  scripts/release-check.sh "$t" --skip-common-offline --common-check-artifact .agents/evaluations/runtime/$(date -u +%F)-common-offline.json || echo "RELEASE_CHECK $t FAILED"
done
scripts/theme.sh catalog
scripts/theme.sh catalog --check
```

  Commit the regenerated catalogs (`README.md`, `sample-themes/README.md`). They are Markdown, so
  `last_source_commit` doesn't move.

---

### Task 17: Prune superseded evidence

Run only after Task 16 has committed fresh evidence for all 8 themes.

- [ ] **Step 1: Dry run, review, apply**

```bash
scripts/theme.sh evidence prune --keep-latest 1
scripts/theme.sh evidence prune --keep-latest 1 --apply
git rm -r -q .agents/evaluations/runtime/superseded
git rm -q .agents/evaluations/runtime/2026-09-15-p409-evidence.json .agents/evaluations/runtime/20260915T163631Z-parity.json .agents/evaluations/runtime/2026-09-20-common-offline.json .agents/evaluations/runtime/2026-09-21-common-offline.json
# prune groups by theme name; each <date>-batch-checkpoints directory is its own group, so remove old ones explicitly
git rm -r -q .agents/evaluations/runtime/2026-09-21-batch-checkpoints
```

- [ ] **Step 2: Annotate Markdown that cites pruned directories by full path** (per-theme READMEs,
      `docs/THEME_FACTORY_IMPLEMENTATION_AND_CHROME_MCP_REPORT.md`). `tests/live/RELEASE-MATRIX.md` cites
      bare directory names in a dated historical table; leave it.

```bash
python3 - <<'PY'
import re, subprocess
from pathlib import Path
files = subprocess.run(["git", "grep", "-l", ".agents/evaluations/runtime/20", "--", "*.md"],
                       capture_output=True, text=True).stdout.split()
pattern = re.compile(r"`?\.agents/evaluations/runtime/(20[0-9T:Z-]+[a-z0-9-]*)/?`?")
for name in files:
    path = Path(name)
    text = path.read_text(encoding="utf-8")
    def note(match):
        target = Path(".agents/evaluations/runtime") / match.group(1)
        return match.group(0) if target.exists() else f"`{match.group(1)}` (pruned 2026-09-23; in git history)"
    new = pattern.sub(note, text)
    if new != text:
        path.write_text(new, encoding="utf-8")
        print("annotated", name)
PY
```

- [ ] **Step 3: Prove the verdicts did not change, then commit.** Every theme must still pass. Check the size:

```bash
for t in carbon-volt citrus-pop cobalt-press estate-slate estate-slate-dark linen solarized-dark velvet-signal; do
  python3 -m lib.theme_factory.release --theme "$t" --package "dist/$t/$t-$(python3 -c "import json;print(json.load(open('sample-themes/$t/theme.json'))['version'])").zip" --evidence-dir .agents/evaluations/runtime | tail -1
done
scripts/theme.sh catalog --check
du -sh .agents/evaluations/runtime
git add -A .agents/evaluations/runtime '*.md'
git commit -m "chore: prune superseded release evidence" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Hand over the push (user-run):**

```bash
git push -u origin audit-remediation
```
