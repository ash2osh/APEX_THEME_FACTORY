# Theme Production Accelerator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a recipe-driven Theme Workshop, consolidated Theme Lab, and resumable release pipeline that makes distinctive APEX themes faster and less token-intensive without weakening any existing quality gate.

**Architecture:** Add source-only recipes and template-time component starters on top of the existing strict manifest, CSS, archive, installer, and evidence libraries. Expose three lanes through one CLI: fast offline authoring, explicit app-102 candidate verification, and digest-bound release verification. Existing packages remain compatible, live APEX work continues through SQLcl and the project Chrome daemon, and generated documentation is derived from manifests plus verified evidence.

**Tech Stack:** Python 3.12+ standard library, `unittest`, Bash wrappers, Oracle APEX 26.1.4 APEXLang, Universal Theme 42/Iris, SQLcl saved connection `docker-demo`, Chrome DevTools through `tools/chrome_devtools_client.py`, temporary pinned fontTools/Brotli environment, CSS and JSON.

**Spec:** `docs/superpowers/specs/2026-09-19-theme-production-accelerator-design.md`

## Global Constraints

- Target exactly Oracle APEX **26.1.4**, Universal Theme **42**, `baseTheme: ut-26.1`, and theme style **Iris**.
- Linen remains the application default; new tooling must not change the default implicitly.
- Runtime truth uses the already-running project daemon through `python3 tools/chrome_devtools_client.py`; never start or call a second Chrome DevTools MCP instance.
- Declarative source remains `applications/ut/`; validate every APEXLang change and import only when the user explicitly requests it.
- Theme appearance remains under `sample-themes/<name>/css`, scoped to `html.app-theme-<name>` and `.app-theme-<name> .apex-theme-iris`.
- Recipes are source-only authoring inputs; distributable ZIPs retain the existing single-theme runtime and archive contract.
- Fonts are licensed, package-local WOFF2 files with no external runtime URLs; Font APEX remains isolated.
- Author and candidate checks can never emit `VERIFIED`; only complete, current Layers A-E evidence can do so.
- A cached or resumed check is valid only when all of its consumed inputs and environment identity match.
- Source work must be committed before package builds; packages must be built before live evidence; no source file may change during capture.
- All Python behavior is developed with `unittest`: write a focused failing test, observe the expected failure, implement minimally, and rerun the focused and affected suites.
- Preserve unrelated and untracked theme packages, application files, and user changes.

## Review Focus

- A malformed, duplicate, path-traversing, or case-colliding theme name must fail before any directory is created; Task 1 and Task 3 pin this behavior.
- A font request for a nonexistent axis value, unsupported weight, non-OFL source, or missing Arabic/Latin coverage must fail without leaving partial assets; Task 5 pins this behavior.
- A cache or resume entry from different source bytes, package SHA, APEX/browser version, consumer, page, viewport, or validator version must be treated as a miss; Tasks 7 and 12 pin this behavior.
- Cover and candidate browser tools must not alter shared `localStorage`, resize the user's Chrome window, reuse the wrong page, or leave a background tab open; Task 11 pins this behavior.
- Legacy themes without `theme.recipe.json` must remain discoverable, installable, checkable, and comparable, while invalid manifests must be reported rather than skipped; Tasks 1, 6, and 8 pin this behavior.

---

## File Structure

### New authoring modules

| Path | Responsibility |
|---|---|
| `lib/theme_factory/discovery.py` | Strict, deterministic discovery of theme source directories. |
| `lib/theme_factory/recipe.py` | Recipe dataclasses, strict parser, static contrast, and generated-source ownership. |
| `lib/theme_factory/scaffold.py` | Atomic neutral-theme creation and recipe-driven regeneration. |
| `lib/theme_factory/font_pipeline.py` | Pinned metadata/font acquisition, static WOFF2 instancing, validation, and provenance. |
| `lib/theme_factory/fingerprint.py` | Legacy/recipe fingerprints and uniqueness comparisons. |
| `lib/theme_factory/checks.py` | Composed theme-specific author checks and compact result model. |
| `lib/theme_factory/cache.py` | Content-addressed local check cache. |
| `lib/theme_factory/catalog.py` | Generated catalog/design-system/release Markdown sections. |
| `lib/theme_factory/iris_inspector.py` | Independent scans of pinned UT/Iris token declarations and chains. |
| `lib/theme_factory/dev.py` | Candidate-lane sync, validation, optional import, and browser-open orchestration. |
| `lib/theme_factory/evidence_cache.py` | Strict checkpoint/resume identity and obsolete-evidence reporting. |

### New templates, tools, and declarative source

| Path | Responsibility |
|---|---|
| `theme-templates/neutral/**` | Brand-neutral manifest, recipe, README, CSS module, and preview-source templates. |
| `theme-templates/components/*.css.tmpl` | Template-time component profiles; never shipped as shared runtime CSS. |
| `scripts/theme.sh` | Stable shell entry point for the unified CLI. |
| `tools/theme_cover.py` | Daemon-backed page-500 cover capture. |
| `tools/theme_visual_diff.py` | Scratch-image dimensions and pixel-difference reporting. |
| `tools/release_batch.py` | Batch Layer C/D orchestration with validated checkpoints. |
| `tools/theme_benchmark.py` | Repeatable wall-time, command-count, file-touch, and agent-token measurements. |
| `applications/ut/pages/p00406-theme-lab.apx` | Native APEX Theme Lab page. |
| `static-files/css/pages/theme-lab.css` | Page-406 layout only, scoped to `html.page-406`. |
| `.agents/knowledge/reference/ut-26.1/iris-token-inventory.json` | Deterministic token inventory generated from pinned reference CSS. |
| `docs/generated/iris-26.1-token-report.md` | Human-readable drift report generated from the same inventory. |

### Existing files changed deliberately

| Path | Change |
|---|---|
| `lib/theme_factory/cli.py` | Register `new`, `font`, `check`, `dev`, `cover`, `catalog`, `inspect-iris`, and `release-batch`. |
| `scripts/install_all_themes.py` | Replace `DEFAULT_THEMES` with strict discovery. |
| `scripts/release-check.sh` | Separate common offline work from one-theme release evaluation and support validated resume. |
| `tools/live_matrix.py`, `tools/browser_matrix.py` | Expose reusable runners and row checkpoints without changing evidence semantics. |
| `lib/theme_factory/release.py` | Public programmatic verdict API and environment-bound resume validation. |
| `lib/theme_factory/apexlang.py` | Compatibility facade after its focused behavior-preserving split. |
| `README.md`, `sample-themes/README.md`, `docs/DESIGN_SYSTEM.md`, `tests/live/RELEASE-MATRIX.md` | Handwritten prose plus generated, checkable sections. |
| `.github/workflows/verify.yml`, `.github/workflows/nightly.yml` | Fast pull-request and complete offline/package tiers. |
| `.gitignore` | Ignore `.theme-factory/cache/` and benchmark scratch captures. |

---

### Task 1: Strict theme discovery and dynamic installer defaults

**Files:**
- Create: `lib/theme_factory/discovery.py`
- Create: `tests/test_theme_discovery.py`
- Modify: `scripts/install_all_themes.py:29,90-103`
- Modify: `tests/test_installer_cli.py`

**Interfaces:**
- Consumes: `load_manifest(path: Path, package_root: Path) -> ThemeManifest`.
- Produces: `DiscoveredTheme`; `discover_themes(repo_root: Path) -> tuple[DiscoveredTheme, ...]`; `theme_names(repo_root: Path) -> tuple[str, ...]`.

- [ ] **Step 1: Write discovery failures and ordering tests**

```python
class ThemeDiscoveryTests(unittest.TestCase):
    def test_valid_manifests_are_sorted_by_manifest_name(self):
        self.make_theme("z-dir", name="zeta")
        self.make_theme("a-dir", name="alpha")
        self.assertEqual(tuple(t.name for t in discover_themes(self.root)), ("alpha", "zeta"))

    def test_candidate_with_invalid_manifest_is_not_silently_skipped(self):
        bad = self.root / "sample-themes" / "bad"
        bad.mkdir(parents=True)
        (bad / "theme.json").write_text('{"schemaVersion":1}', encoding="utf-8")
        with self.assertRaisesRegex(PackageError, "bad/theme.json"):
            discover_themes(self.root)

    def test_directory_without_manifest_is_ignored(self):
        (self.root / "sample-themes" / "notes").mkdir(parents=True)
        self.assertEqual(discover_themes(self.root), ())
```

- [ ] **Step 2: Run the focused test and confirm the missing-module failure**

Run: `python3 -m unittest tests.test_theme_discovery -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'lib.theme_factory.discovery'`.

- [ ] **Step 3: Implement the discovery model and strict loader**

```python
@dataclass(frozen=True)
class DiscoveredTheme:
    name: str
    root: Path
    manifest: ThemeManifest

def discover_themes(repo_root: Path) -> tuple[DiscoveredTheme, ...]:
    themes_root = Path(repo_root).resolve() / "sample-themes"
    found: list[DiscoveredTheme] = []
    for manifest_path in sorted(themes_root.glob("*/theme.json")):
        root = manifest_path.parent
        try:
            manifest = load_manifest(manifest_path, root)
        except PackageError as exc:
            raise PackageError(f"Invalid theme source {manifest_path.relative_to(repo_root)}: {exc}") from exc
        found.append(DiscoveredTheme(manifest.name, root, manifest))
    names = [item.name.casefold() for item in found]
    if len(names) != len(set(names)):
        raise PackageError("Theme names collide when compared case-insensitively")
    return tuple(sorted(found, key=lambda item: item.name))

def theme_names(repo_root: Path) -> tuple[str, ...]:
    return tuple(item.name for item in discover_themes(repo_root))
```

- [ ] **Step 4: Replace the hard-coded installer default**

Set the `--themes` default from `theme_names(repo_root)` at argument-parser construction time. Preserve an
explicit comma-separated `--themes` exactly as today. Add a test that the repository default includes all eight
current manifests and a temporary ninth manifest without changing Python source.

- [ ] **Step 5: Run discovery and installer tests**

Run: `python3 -m unittest tests.test_theme_discovery tests.test_installer_cli -v`

Expected: PASS; the default installer list is manifest-derived and deterministic.

- [ ] **Step 6: Commit**

```bash
git add lib/theme_factory/discovery.py tests/test_theme_discovery.py scripts/install_all_themes.py tests/test_installer_cli.py
git commit -m "feat: discover theme packages dynamically"
```

### Task 2: Strict recipe model and static contrast preflight

**Files:**
- Create: `lib/theme_factory/recipe.py`
- Create: `tests/test_theme_recipe.py`
- Create: `tests/fixtures/recipes/valid-dark.json`
- Create: `tests/fixtures/recipes/invalid-low-contrast.json`

**Interfaces:**
- Consumes: `NAME_REGEX`, `VALID_WEIGHTS`, and `PackageError`.
- Produces: `ThemeRecipe`; `load_recipe(path: Path) -> ThemeRecipe`; `contrast_ratio(foreground: str, background: str) -> float`; `validate_core_contrast(recipe: ThemeRecipe) -> tuple[RecipeIssue, ...]`.

- [ ] **Step 1: Write strict-schema and contrast tests**

```python
def test_unknown_recipe_property_fails(self):
    raw = self.valid_raw()
    raw["identity"]["surprise"] = True
    with self.assertRaisesRegex(PackageError, "identity/surprise"):
        self.load(raw)

def test_theme_name_rejects_path_escape(self):
    raw = self.valid_raw()
    raw["identity"]["name"] = "../escape"
    with self.assertRaisesRegex(PackageError, "must match"):
        self.load(raw)

def test_primary_text_below_4_5_is_an_error(self):
    recipe = self.load_fixture("invalid-low-contrast.json")
    issues = validate_core_contrast(recipe)
    self.assertIn(("CONTRAST_PRIMARY_CARD", "error"), {(i.code, i.severity) for i in issues})
```

- [ ] **Step 2: Run the recipe test and confirm it fails for the absent API**

Run: `python3 -m unittest tests.test_theme_recipe -v`

Expected: FAIL importing `lib.theme_factory.recipe`.

- [ ] **Step 3: Implement immutable recipe dataclasses and strict key checking**

Define `Identity`, `Palette`, `Typography`, `Geometry`, `Focus`, `ComponentProfiles`, `ThemeRecipe`, and
`RecipeIssue` as frozen dataclasses. Accept only the keys and enum values shown in the design spec. Normalize
hex colors to uppercase `#RRGGBB`, require unique integer weights from `VALID_WEIGHTS`, and require the
identity name to match the parent directory when loading from a theme root.

- [ ] **Step 4: Implement dependency-free WCAG calculations**

```python
def _linear(channel: int) -> float:
    value = channel / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

def contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        red, green, blue = (int(color[index:index + 2], 16) for index in (1, 3, 5))
        return 0.2126 * _linear(red) + 0.7152 * _linear(green) + 0.0722 * _linear(blue)
    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)
```

Check primary and secondary text on page/card at 4.5:1, `onAccent` on accent fills at 4.5:1, focus color
against page/card at 3:1, and danger text on card at 4.5:1. Return all failures so an agent can repair them in
one pass.

- [ ] **Step 5: Run the focused tests**

Run: `python3 -m unittest tests.test_theme_recipe -v`

Expected: PASS with ratios asserted to two decimal places.

- [ ] **Step 6: Commit**

```bash
git add lib/theme_factory/recipe.py tests/test_theme_recipe.py tests/fixtures/recipes
git commit -m "feat: define strict theme recipes"
```

### Task 3: Neutral scaffold and atomic source generation

**Files:**
- Create: `lib/theme_factory/scaffold.py`
- Create: `tests/test_theme_scaffold.py`
- Create: `theme-templates/neutral/theme.json.tmpl`
- Create: `theme-templates/neutral/theme.recipe.json.tmpl`
- Create: `theme-templates/neutral/README.md.tmpl`
- Create: `theme-templates/neutral/css/theme.css.tmpl`
- Create: `theme-templates/neutral/css/tokens.css.tmpl`
- Create: `theme-templates/neutral/css/apex/{shell,regions,buttons,forms,reports,dialogs,misc}.css.tmpl`
- Create: `theme-templates/components/{navigation-rail,navigation-pill,navigation-editorial,navigation-minimal,cards-flat,cards-layered,cards-offset,cards-buoyant,buttons-square,buttons-rounded,buttons-underline,buttons-pill,forms-dense,forms-comfortable,forms-outlined,forms-soft,reports-ruled,reports-spacious,dialogs-flat,dialogs-layered}.css.tmpl`

**Interfaces:**
- Consumes: `ThemeRecipe`, `load_recipe`, `discover_themes`.
- Produces: `ScaffoldResult`; `create_theme(repo_root: Path, recipe: ThemeRecipe) -> ScaffoldResult`; `regenerate_owned_files(theme_root: Path, recipe: ThemeRecipe) -> ScaffoldResult`.

- [ ] **Step 1: Write scaffold contract tests**

```python
def test_create_emits_complete_scoped_source(self):
    result = create_theme(self.repo, self.recipe("aurora-grid"))
    self.assertEqual(result.created, self.repo / "sample-themes/aurora-grid")
    self.assertTrue((result.created / "theme.json").is_file())
    self.assertEqual({p.name for p in (result.created / "css/apex").glob("*.css")}, EXPECTED_MODULES)
    for css in (result.created / "css").rglob("*.css"):
        self.assertNotIn("app-theme-THEME", css.read_text(encoding="utf-8"))
        self.assertIn("app-theme-aurora-grid", css.read_text(encoding="utf-8"))

def test_collision_leaves_existing_directory_byte_identical(self):
    before = self.snapshot(self.existing)
    with self.assertRaisesRegex(PackageError, "already exists"):
        create_theme(self.repo, self.recipe(self.existing.name))
    self.assertEqual(self.snapshot(self.existing), before)
```

- [ ] **Step 2: Run the scaffold test and confirm the missing implementation**

Run: `python3 -m unittest tests.test_theme_scaffold -v`

Expected: FAIL importing `lib.theme_factory.scaffold`.

- [ ] **Step 3: Implement atomic creation in a sibling temporary directory**

```python
def create_theme(repo_root: Path, recipe: ThemeRecipe) -> ScaffoldResult:
    themes_root = repo_root.resolve() / "sample-themes"
    destination = themes_root / recipe.identity.name
    if destination.exists():
        raise PackageError(f"Theme directory already exists: {destination}")
    temp_root = Path(tempfile.mkdtemp(prefix=f".{recipe.identity.name}-", dir=themes_root))
    try:
        _render_neutral_tree(repo_root, temp_root, recipe)
        load_manifest(temp_root / "theme.json", temp_root)
        os.replace(temp_root, destination)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
    return ScaffoldResult(created=destination, written=tuple(sorted(destination.rglob("*"))))
```

- [ ] **Step 4: Render a genuinely neutral base**

Use recipe colors only in `tokens.css`; every component module consumes `--app-*` or theme-private tokens.
Emit body/heading family variables, `color-scheme`, focus tokens, geometry, and dark-mode hook sections. Do not
copy Linen or Solarized source. Each component profile inserts geometry/state rules into its owning module and
a marker comment such as `/* profile: cards-offset */` used by fingerprinting.

- [ ] **Step 5: Protect handwritten content during regeneration**

Only replace files whose first line is `/* @theme-factory-generated */`. If an owned file has lost the marker,
raise `PackageError("Refusing to overwrite handwritten file: …")`. Add a test that edits `buttons.css`, removes
the marker, and confirms regeneration leaves its bytes unchanged.

- [ ] **Step 6: Validate the scaffold with existing policies**

Run: `python3 -m unittest tests.test_theme_scaffold tests.test_manifest tests.test_css_policy tests.test_css_bundle -v`

Expected: PASS; the temporary sample passes manifest and CSS-policy validation without package fonts.

- [ ] **Step 7: Commit**

```bash
git add lib/theme_factory/scaffold.py tests/test_theme_scaffold.py theme-templates
git commit -m "feat: scaffold neutral theme sources"
```

### Task 4: Recipe-to-source compiler and legacy compatibility

**Files:**
- Modify: `lib/theme_factory/recipe.py`
- Modify: `lib/theme_factory/scaffold.py`
- Create: `tests/test_recipe_rendering.py`
- Modify: `lib/theme_factory/archive.py`
- Modify: `tests/test_package_archive.py`

**Interfaces:**
- Consumes: `ThemeRecipe`, `ThemeManifest`, neutral templates.
- Produces: `render_manifest(recipe: ThemeRecipe, font_roles: dict[str, FontRoleSpec]) -> str`; `render_tokens(recipe: ThemeRecipe) -> str`; `owned_source_digest(theme_root: Path) -> str`.

- [ ] **Step 1: Write deterministic-rendering tests**

```python
def test_same_recipe_renders_byte_identically(self):
    first = render_tokens(self.recipe)
    second = render_tokens(self.recipe)
    self.assertEqual(first.encode(), second.encode())

def test_recipe_is_source_only_and_absent_from_zip(self):
    package = self.build_recipe_theme()
    with zipfile.ZipFile(package) as archive:
        self.assertFalse(any(name.endswith("theme.recipe.json") for name in archive.namelist()))

def test_legacy_theme_without_recipe_still_builds(self):
    package = build_package(self.repo, "linen", self.output)
    self.assertEqual(verify_package(package).name, "linen")
```

- [ ] **Step 2: Run the focused tests and observe missing renderer failures**

Run: `python3 -m unittest tests.test_recipe_rendering -v`

Expected: FAIL because `render_manifest`, `render_tokens`, and `owned_source_digest` do not exist.

- [ ] **Step 3: Render manifest and tokens with stable formatting**

Use `json.dumps(document, indent=2, ensure_ascii=False) + "\n"` for JSON. Use a fixed token order matching the
recipe schema. Generate dark literal-token sections from one maintained template containing the current Iris,
frozen `--a-palette-*`, JET-on-`html`, menus, grids, pickers, Popup LOV, and dialog families; light themes omit
dark-only remaps but still declare complete semantic `--app-*` roles.

- [ ] **Step 4: Keep component CSS as an escape hatch**

Regenerating a recipe may replace owned `theme.json`, recipe-owned token block, and still-marked starter
modules. Any module with the generated marker removed is reported as `preservedHandwritten` and is not changed.
Add a test with one owned and one handwritten module.

- [ ] **Step 5: Confirm package compatibility**

Run: `python3 -m unittest tests.test_recipe_rendering tests.test_package_archive tests.test_new_theme_packages -v`

Expected: PASS; current archives have unchanged required runtime members and no recipe member.

- [ ] **Step 6: Commit**

```bash
git add lib/theme_factory/recipe.py lib/theme_factory/scaffold.py lib/theme_factory/archive.py tests/test_recipe_rendering.py tests/test_package_archive.py
git commit -m "feat: compile recipes into portable theme source"
```

### Task 5: Pinned bilingual font pipeline

**Files:**
- Create: `lib/theme_factory/font_pipeline.py`
- Create: `tests/test_font_pipeline.py`
- Create: `tests/fixtures/fonts/metadata.pb`
- Create: `tests/fixtures/fonts/OFL.txt`
- Create: `tools/font-tools-requirements.txt`
- Modify: `lib/theme_factory/cli.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `ThemeRecipe`, strict manifest font structures.
- Produces: `FontRequest`; `FontInstallResult`; `inspect_metadata(text: str) -> FontMetadata`; `install_font(repo_root: Path, theme_root: Path, request: FontRequest) -> FontInstallResult`.

- [ ] **Step 1: Pin the isolated tooling environment**

Create `tools/font-tools-requirements.txt` with:

```text
fonttools[woff]==4.60.1
brotli==1.1.0
```

The implementation creates its venv under a `tempfile.TemporaryDirectory` and installs with
`python -m pip install --no-deps -r tools/font-tools-requirements.txt`. Both direct packages are pinned to exact
versions, the venv is deleted after conversion, and the README provenance records both tool versions.

- [ ] **Step 2: Write metadata, weight, coverage, and cleanup tests**

```python
def test_unsupported_weight_fails_before_writing_assets(self):
    request = self.request(weights=(400, 450, 700))
    with self.assertRaisesRegex(PackageError, "450.*not supported"):
        install_font(self.repo, self.theme, request, runner=self.fake_runner)
    self.assertEqual(list((self.theme / "fonts").glob("*")), [])

def test_missing_arabic_coverage_removes_staging_directory(self):
    self.fake_runner.output_cmap = {ord("A")}
    with self.assertRaisesRegex(PackageError, "Arabic"):
        install_font(self.repo, self.theme, self.request(), runner=self.fake_runner)
    self.assertFalse((self.theme / ".font-staging").exists())

def test_source_revision_is_required(self):
    with self.assertRaisesRegex(PackageError, "source revision"):
        FontRequest(metadata_url=self.url, source_revision="", weights=(400, 700))
```

- [ ] **Step 3: Run the font tests and confirm the missing module failure**

Run: `python3 -m unittest tests.test_font_pipeline -v`

Expected: FAIL importing `lib.theme_factory.font_pipeline`.

- [ ] **Step 4: Parse only the official metadata fields required by the pipeline**

Extract family name, license, repository URL, filenames, axis ranges, and subsets from `METADATA.pb`. Reject a
metadata document whose family differs from the requested family, whose license is not `OFL`, or whose source
URL/revision is absent. Cache downloads only under the ignored `.theme-factory/cache/fonts/` directory and key
them by URL plus revision.

- [ ] **Step 5: Implement static WOFF2 instancing in staging**

For each requested weight, call a helper process inside the temporary venv that opens `TTFont`, verifies a
`wght` axis range containing the requested value, calls `instantiateVariableFont(font, {"wght": weight})`,
sets `font.flavor = "woff2"`, and saves to a staging filename. Reopen every output, require its first four
bytes to be `wOF2`, and require cmap coverage for Basic Latin plus at least one code point in Arabic
`U+0600-U+06FF`.

- [ ] **Step 6: Install assets and provenance atomically**

Move the completed staging files and OFL license into `fonts/` and `licenses/`, update recipe typography/font
provenance and `theme.json` face entries, and insert a deterministic README section containing metadata URL,
source revision, source filename, tool versions, weights, and SHA-256 values. Do not retain TTFs or the venv.

- [ ] **Step 7: Add the CLI contract**

Register `font add NAME --family FAMILY --metadata-url URL --source-revision SHA --weights CSV`. Add
`--dry-run` to print resolved axes/files without writing. Machine mode returns `{"status":"PASS","faces":…}`.

- [ ] **Step 8: Run font, manifest, bundle, and archive tests**

Run: `python3 -m unittest tests.test_font_pipeline tests.test_manifest tests.test_css_bundle tests.test_package_archive -v`

Expected: PASS, including a four-face fixture and a failed unsupported-weight fixture with no partial files.

- [ ] **Step 9: Commit**

```bash
git add lib/theme_factory/font_pipeline.py lib/theme_factory/cli.py tests/test_font_pipeline.py tests/fixtures/fonts tools/font-tools-requirements.txt .gitignore
git commit -m "feat: automate pinned bilingual font assets"
```

### Task 6: Theme fingerprinting and uniqueness gate

**Files:**
- Create: `lib/theme_factory/fingerprint.py`
- Create: `tests/test_theme_fingerprint.py`
- Modify: `tests/test_new_theme_packages.py`

**Interfaces:**
- Consumes: `ThemeRecipe` when present; manifest and CSS for legacy themes.
- Produces: `ThemeFingerprint`; `fingerprint_theme(theme_root: Path) -> ThemeFingerprint`; `compare_fingerprints(candidate: ThemeFingerprint, existing: ThemeFingerprint) -> SimilarityReport`; `check_uniqueness(candidate_root: Path, all_roots: Sequence[Path]) -> tuple[UniquenessIssue, ...]`.

- [ ] **Step 1: Write recolor and legacy tests**

```python
def test_color_only_copy_is_rejected(self):
    left = self.theme("left", component_css=BASE_CSS, colors=FIRST_COLORS)
    right = self.theme("right", component_css=BASE_CSS, colors=SECOND_COLORS)
    issues = check_uniqueness(right, (left, right))
    self.assertIn("STRUCTURAL_RECOLOR", {issue.code for issue in issues if issue.severity == "error"})

def test_legacy_theme_without_recipe_has_a_fingerprint(self):
    fingerprint = fingerprint_theme(Path("sample-themes/linen"))
    self.assertEqual(fingerprint.name, "linen")
    self.assertGreater(len(fingerprint.component_hashes), 3)
```

- [ ] **Step 2: Run the focused test and confirm it fails importing fingerprinting**

Run: `python3 -m unittest tests.test_theme_fingerprint -v`

Expected: FAIL importing `lib.theme_factory.fingerprint`.

- [ ] **Step 3: Implement structural normalization and perceptual color distance**

Normalize selector scopes to `app-theme-THEME`, replace hex/rgb/hsl color literals with `COLOR`, collapse
whitespace/comments, and compute per-module token shingles plus SHA-256. Implement sRGB-to-CIELAB conversion in
the standard library and calculate mean palette Delta E 1976 for named semantic pairs.

- [ ] **Step 4: Implement explainable thresholds**

Emit `STRUCTURAL_RECOLOR` as an error when normalized component similarity is at least `0.98` and at least five
of seven component-profile dimensions match. Emit `IDENTITY_COLLISION` as an error when font, geometry, profiles,
and mean palette Delta E below `12.0` all match. Emit warnings for isolated similarities. Include nearest theme,
CSS similarity, Delta E, matching profiles, font match, and geometry match in every report.

- [ ] **Step 5: Run fingerprint and current-theme tests**

Run: `python3 -m unittest tests.test_theme_fingerprint tests.test_new_theme_packages -v`

Expected: PASS; all eight current themes avoid error-level uniqueness findings.

- [ ] **Step 6: Commit**

```bash
git add lib/theme_factory/fingerprint.py tests/test_theme_fingerprint.py tests/test_new_theme_packages.py
git commit -m "feat: detect structural theme recolors"
```

### Task 7: Content-addressed fast checks and compact output

**Files:**
- Create: `lib/theme_factory/cache.py`
- Create: `lib/theme_factory/checks.py`
- Create: `tests/test_theme_cache.py`
- Create: `tests/test_theme_checks.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: recipe, manifest, CSS policy, CSS bundle, font, archive-source, discovery, and fingerprint APIs.
- Produces: `CheckIssue`; `CheckReport`; `run_theme_checks(repo_root: Path, theme_name: str, use_cache: bool = True) -> CheckReport`; `CacheKey`; `load_cached_report`; `store_cached_report`.

- [ ] **Step 1: Write cache invalidation tests**

```python
def test_shared_token_change_invalidates_theme_cache(self):
    first = self.run_cached()
    self.shared_tokens.write_text(self.shared_tokens.read_text() + "\n:root{--app-test:1px}\n")
    second = self.run_cached()
    self.assertFalse(second.cache_hit)
    self.assertNotEqual(first.input_digest, second.input_digest)

def test_validator_version_change_is_a_cache_miss(self):
    store_cached_report(self.cache, CacheKey("check-v1", "abc"), self.report)
    self.assertIsNone(load_cached_report(self.cache, CacheKey("check-v2", "abc")))
```

- [ ] **Step 2: Write composed-check tests**

Assert a valid fixture returns one-line human output and a JSON object with `status`, `theme`, `cacheHit`,
`durationMs`, `inputDigest`, and `issues`. Assert three deliberate defects are all returned in one run rather
than stopping at the first.

- [ ] **Step 3: Run focused tests and observe missing modules**

Run: `python3 -m unittest tests.test_theme_cache tests.test_theme_checks -v`

Expected: FAIL importing `cache` and `checks`.

- [ ] **Step 4: Implement canonical input hashing**

Hash relative path, mode, and bytes for the selected theme, `static-files/css/foundation/tokens.css`, relevant
templates, and a constant `CHECK_CONTRACT_VERSION = "1"`. Exclude preview images from author checks except the
cover existence/dimensions check. Store JSON at `.theme-factory/cache/checks/<theme>/<digest>.json` using an
atomic temporary-file replace.

- [ ] **Step 5: Compose checks without subprocess log noise**

Call Python APIs directly. For archive-content preflight, build in a temporary directory with an injected
source identity of `author-check` rather than setting `THEME_FACTORY_ALLOW_DIRTY`; verify the resulting ZIP and
delete it. Sort issues by severity, code, path, and line. Human success output is:

```text
THEME_CHECK theme=carbon-volt status=PASS cache=hit duration_ms=42 issues=0
```

- [ ] **Step 6: Run focused and affected suites**

Run: `python3 -m unittest tests.test_theme_cache tests.test_theme_checks tests.test_css_policy tests.test_css_bundle tests.test_package_archive -v`

Expected: PASS with a demonstrated cache hit and misses after both local and shared input changes.

- [ ] **Step 7: Commit**

```bash
git add lib/theme_factory/cache.py lib/theme_factory/checks.py tests/test_theme_cache.py tests/test_theme_checks.py .gitignore
git commit -m "feat: add cached theme-specific quality checks"
```

### Task 8: Unified Theme Workshop CLI and candidate lane

**Files:**
- Create: `lib/theme_factory/dev.py`
- Create: `scripts/theme.sh`
- Create: `tests/test_theme_cli.py`
- Create: `tests/test_theme_dev.py`
- Modify: `lib/theme_factory/cli.py`
- Modify: `scripts/package-theme.sh`

**Interfaces:**
- Consumes: Tasks 1-7 APIs plus existing sync/validate/import scripts.
- Produces: CLI subcommands `new`, `font add`, `check`, `dev`; `DevOptions`; `DevReport`; `run_dev(options: DevOptions) -> DevReport`.

- [ ] **Step 1: Write parser and exit-code tests**

Use `unittest.mock` around command handlers. Assert `check` returns 0 on PASS and 2 on ERROR; `new` rejects a
missing recipe or missing required inline fields; `dev --import` without `--apply` is rejected; and JSON mode
writes exactly one JSON document to stdout.

- [ ] **Step 2: Run CLI tests and confirm subcommands are unavailable**

Run: `python3 -m unittest tests.test_theme_cli -v`

Expected: FAIL because argparse rejects `new` and `check`.

- [ ] **Step 3: Refactor CLI registration into focused functions**

Create `register_package_commands`, `register_install_commands`, and `register_workshop_commands` while keeping
the current command lines compatible. Handler functions accept parsed arguments and return an integer; only
`main()` calls `sys.exit`.

- [ ] **Step 4: Add the stable wrapper**

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="$ROOT" exec python3 -m lib.theme_factory.cli "$@"
```

- [ ] **Step 5: Implement the candidate orchestration state machine**

`run_dev` always runs `run_theme_checks` first. `--sync` executes `scripts/sync-static.sh`; `--validate` executes
`scripts/apex-validate.sh`; `--import --apply` executes the existing confirmed import workflow; `--open` calls
the project daemon to create one background page at `/ords/r/demo/ut/theme-lab`. Record command, exit code,
duration, and truncated failure output in `DevReport`. Stop before import when check/sync/validation fails.

- [ ] **Step 6: Test mutation boundaries**

Mock subprocesses and daemon calls. Assert plain `dev` runs no external command; `dev --sync --validate` runs
exactly those commands; import requires `--apply`; and a validation failure prevents import/open.

- [ ] **Step 7: Run CLI, dev, and existing command tests**

Run: `python3 -m unittest tests.test_theme_cli tests.test_theme_dev tests.test_installer_cli tests.test_uninstaller_cli -v`

Expected: PASS and existing package/install/uninstall command syntax remains accepted.

- [ ] **Step 8: Commit**

```bash
git add lib/theme_factory/dev.py lib/theme_factory/cli.py scripts/theme.sh scripts/package-theme.sh tests/test_theme_cli.py tests/test_theme_dev.py
git commit -m "feat: add unified Theme Workshop CLI"
```

### Task 9: Generated catalog, design-system table, and release matrix

**Files:**
- Create: `lib/theme_factory/catalog.py`
- Create: `tests/test_theme_catalog.py`
- Modify: `lib/theme_factory/manifest.py`
- Modify: all `sample-themes/*/theme.json`
- Modify: `README.md`
- Modify: `sample-themes/README.md`
- Modify: `docs/DESIGN_SYSTEM.md`
- Modify: `tests/live/RELEASE-MATRIX.md`
- Modify: `lib/theme_factory/cli.py`

**Interfaces:**
- Consumes: discovery, `load_evidence`, `calculate_layer_statuses`, `release_verdict`.
- Produces: optional manifest `direction`; `CatalogTheme`; `catalog_themes(repo_root: Path, evidence_root: Path) -> tuple[CatalogTheme, ...]`; `update_generated_sections(path: Path, sections: Mapping[str, str], check: bool) -> tuple[Path, ...]`.

- [ ] **Step 1: Write marker and verdict-integrity tests**

```python
def test_handwritten_text_outside_markers_is_preserved(self):
    original = "Intro\n<!-- @generated:themes:start -->\nold\n<!-- @generated:themes:end -->\nEnd\n"
    self.path.write_text(original, encoding="utf-8")
    update_generated_sections(self.path, {"themes": "new\n"}, check=False)
    self.assertEqual(self.path.read_text(), "Intro\n<!-- @generated:themes:start -->\nnew\n<!-- @generated:themes:end -->\nEnd\n")

def test_stale_or_incomplete_evidence_never_renders_verified(self):
    theme = self.catalog_theme_with_layer_e_missing()
    self.assertEqual(theme.verdict, "UNVERIFIED")
```

- [ ] **Step 2: Run the catalog tests and observe missing module failures**

Run: `python3 -m unittest tests.test_theme_catalog -v`

Expected: FAIL importing `lib.theme_factory.catalog`.

- [ ] **Step 3: Extend manifests with optional direction metadata**

Allow a non-empty root `direction` property without changing `schemaVersion`. Add direction text to every
current manifest from the existing package catalog. Page 405 already reads `$.direction`, so this also fills
the gallery body without changing its SQL.

- [ ] **Step 4: Generate status from real evidence contracts**

For each discovered theme, locate its newest evidence directory, package ZIP, and current source identity. Call
the same evidence loader and layer/verdict functions as the release gate. Catch `PackageError` and render
`UNVERIFIED — <short reason>`; never infer `VERIFIED` from README prose.

- [ ] **Step 5: Add generated markers and renderers**

Generate: the main README theme count/list; sample catalog rows; design-system theme-delta summary; release
matrix status rows. Keep authoring guidance and architectural prose outside markers. `catalog --check` exits 2
and lists drifted files; `catalog --write` updates atomically.

- [ ] **Step 6: Run generation and its tests**

Run: `scripts/theme.sh catalog --write`

Run: `python3 -m unittest tests.test_theme_catalog tests.test_manifest tests.test_sample_themes_coverage -v`

Expected: PASS; `scripts/theme.sh catalog --check` exits 0 and README no longer says only two themes ship.

- [ ] **Step 7: Commit**

```bash
git add lib/theme_factory/catalog.py lib/theme_factory/manifest.py lib/theme_factory/cli.py tests/test_theme_catalog.py sample-themes/*/theme.json README.md sample-themes/README.md docs/DESIGN_SYSTEM.md tests/live/RELEASE-MATRIX.md
git commit -m "feat: generate the theme catalog from source and evidence"
```

### Task 10: Native APEX Theme Lab page

**Files:**
- Create: `applications/ut/pages/p00406-theme-lab.apx`
- Create: `static-files/css/pages/theme-lab.css`
- Create: `tests/test_theme_lab.py`
- Modify: `static-files/css/app.css`
- Modify: `applications/ut/pages/p00405-themes.apx`
- Modify: `applications/ut/shared-components/breadcrumbs.apx`

**Interfaces:**
- Consumes: existing native component examples and shared application CSS.
- Produces: public page 406 alias `THEME-LAB` and stable IDs `theme_lab_typography`, `theme_lab_surfaces`, `theme_lab_buttons`, `theme_lab_forms`, `theme_lab_cards`, `theme_lab_ir`, `theme_lab_ig`, `theme_lab_calendar`, `theme_lab_chart`, `theme_lab_overlays`.

- [ ] **Step 1: Write source-contract tests**

```python
class ThemeLabSourceTests(unittest.TestCase):
    def test_page_contains_every_required_native_specimen(self):
        source = Path("applications/ut/pages/p00406-theme-lab.apx").read_text(encoding="utf-8")
        for static_id in REQUIRED_STATIC_IDS:
            self.assertIn(f"htmlDomId: {static_id}", source)
        for component_type in ("interactiveReport", "interactiveGrid", "calendar", "chart"):
            self.assertIn(f"type: {component_type}", source)
        self.assertIn("العربية", source)
        self.assertIn("400 500 600 700", source)

    def test_page_css_is_page_scoped(self):
        css = Path("static-files/css/pages/theme-lab.css").read_text(encoding="utf-8")
        without_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        selectors = [part.strip() for part in re.findall(r"([^{}]+)\{", without_comments)
                     if not part.lstrip().startswith("@")]
        self.assertTrue(all(selector.lstrip().startswith("html.page-406") for selector in selectors))
```

- [ ] **Step 2: Run the test and confirm page 406 is absent**

Run: `python3 -m unittest tests.test_theme_lab -v`

Expected: ERROR reading `p00406-theme-lab.apx`.

- [ ] **Step 3: Build the page shell and compact specimens**

Create a Standard page with public authentication and checksum protection. Add native regions for bilingual
type, semantic surfaces, all button contexts/states, native text/select/date/Popup LOV/radio/checkbox items,
validation messaging, Cards, and overlay launch buttons. Use `advanced { htmlDomId: … }` for every required ID.
Use native labels and buttons; do not introduce custom Alpine or replace APEX controls.

- [ ] **Step 4: Add real data components from proven APEXLang blocks**

Use these exact source blocks as grammar references while changing source SQL to deterministic `dual` rows and
assigning the Theme Lab IDs:

| Target | Proven source block |
|---|---|
| `theme_lab_ir` | `applications/ut/pages/p01402-interactive-report.apx`, region `simple-interactive-report` |
| `theme_lab_ig` | `applications/ut/pages/p01410-interactive-grid.apx`, region `basic-reporting` |
| `theme_lab_calendar` | `applications/ut/pages/p01800-calendars.apx`, region `demo` |
| `theme_lab_chart` | `applications/ut/pages/p01902-charts.apx`, region `1-bar` |

Each query must return at least six rows and include Arabic and Latin labels. Keep the IG read-only so the Lab
does not create database state. Add direct buttons to pages 1402, 1410, 1800, and 1902 for full reference
behavior.

- [ ] **Step 5: Add modal, drawer, menu, picker, and error-state launchers**

Use native redirect/dialog targets to existing dialog reference pages and native page items to open the date
picker and Popup LOV. Add one button that submits a deliberately required empty item so the native error state
is reproducible without custom JavaScript.

- [ ] **Step 6: Add page-only responsive layout CSS**

Import `pages/theme-lab.css` before the generated themes block. Scope every rule with `html.page-406`; use
shared `--app-*` tokens, CSS Grid with `minmax(min(100%, 18rem), 1fr)`, and stack actions below 768 px. Do not
set theme palette, typography, component colors, or global UT rules here.

- [ ] **Step 7: Link page 405 and breadcrumb source**

Add a native button from the page-405 overview to `f?p=&APP_ID.:406:&SESSION.::&DEBUG.:::` and add the Theme Lab
breadcrumb entry under Themes. Keep page 405 discovery behavior unchanged.

- [ ] **Step 8: Sync and validate without importing**

Run: `scripts/sync-static.sh`

Run: `scripts/apex-validate.sh`

Expected: `Validation successful.` with no new warnings.

- [ ] **Step 9: Run source, sync, and accessibility static tests**

Run: `python3 -m unittest tests.test_theme_lab tests.test_sync_static tests.test_css_policy -v`

Expected: PASS; the page exposes every stable specimen ID and CSS remains page-scoped.

- [ ] **Step 10: Commit**

```bash
git add applications/ut/pages/p00406-theme-lab.apx applications/ut/pages/p00405-themes.apx applications/ut/shared-components/breadcrumbs.apx static-files/css/pages/theme-lab.css static-files/css/app.css applications/ut/shared-components/static-files tests/test_theme_lab.py
git commit -m "feat: add a consolidated native Theme Lab"
```

### Task 11: Safe cover capture and visual-difference triage

**Files:**
- Create: `tools/theme_cover.py`
- Create: `tools/theme_visual_diff.py`
- Create: `tests/test_theme_cover.py`
- Create: `tests/test_theme_visual_diff.py`
- Modify: `lib/theme_factory/cli.py`

**Interfaces:**
- Consumes: `ChromeDevToolsClient`, discovered manifest, running app-102 page 500.
- Produces: `capture_cover(client, theme, output, apply, overwrite) -> CoverReport`; `compare_images(baseline: Path, candidate: Path) -> VisualDiffReport`.

- [ ] **Step 1: Write browser-etiquette tests with a fake daemon client**

```python
def test_capture_uses_background_tab_and_per_tab_emulation(self):
    capture_cover(self.client, "carbon-volt", self.output, apply=True, overwrite=False)
    self.assertIn(("new_page", {"url": PAGE_500, "background": True}), self.client.calls)
    self.assertTrue(any(name == "emulate" and args["viewport"] == "1280x700x0.75" for name, args in self.client.calls))
    self.assertFalse(any(name == "resize_page" for name, args in self.client.calls))
    self.assertTrue(any(name == "close_page" for name, args in self.client.calls))

def test_capture_never_writes_local_storage(self):
    capture_cover(self.client, "carbon-volt", self.output, apply=True, overwrite=False)
    scripts = "\n".join(args.get("function", "") for name, args in self.client.calls if name == "evaluate_script")
    self.assertNotIn("localStorage.setItem", scripts)
```

- [ ] **Step 2: Run the tests and confirm both tools are missing**

Run: `python3 -m unittest tests.test_theme_cover tests.test_theme_visual_diff -v`

Expected: FAIL importing the two tools.

- [ ] **Step 3: Implement safe capture sequencing**

Open one background tab, emulate 1280x700x0.75 so the CSS viewport remains 1280x700 while the captured bitmap
is 960 px wide, navigate to page 500, remove only existing `app-theme-*` classes
from `documentElement`, add the requested class, set `dataset.appThemeCurrent`, inject a temporary style hiding
`#apexDevToolbar`, wait for `document.fonts.ready`, and verify `apex.env.APP_ID === "102"` and page `500`.
Inspect console/network before screenshot. Close the tab in `finally`.

- [ ] **Step 4: Decode and validate the screenshot**

Call the daemon's allowed screenshot tool with JPEG output at quality 90 and decode its base64 result. The
0.75 device scale produces the required 960-pixel bitmap without a local image-processing dependency. Check
JPEG SOI and exact 960 px width before atomic output replacement. Existing output requires both `apply=True`
and `overwrite=True`.

- [ ] **Step 5: Implement deterministic difference summaries**

Read two images into RGBA arrays, normalize to matching dimensions, and report changed-pixel percentage, mean
absolute channel delta, and a heatmap path under ignored `scratch/theme-diffs/`. A changed-pixel percentage
above 2 percent is `REVIEW`, never automatic failure or approval. Dimension mismatch is an error.

- [ ] **Step 6: Add `cover` CLI behavior**

Default is dry-run and prints the intended URL/output. `--apply` writes a missing cover; replacing one also
requires `--overwrite`. Reject a theme that fails `theme check` before opening Chrome.

- [ ] **Step 7: Run tool and daemon-client tests**

Run: `python3 -m unittest tests.test_theme_cover tests.test_theme_visual_diff tests.test_chrome_mcp_daemon -v`

Expected: PASS, including cleanup after a simulated screenshot failure.

- [ ] **Step 8: Commit**

```bash
git add tools/theme_cover.py tools/theme_visual_diff.py lib/theme_factory/cli.py tests/test_theme_cover.py tests/test_theme_visual_diff.py
git commit -m "feat: automate safe theme cover capture"
```

### Task 12: Strict checkpoints, resumable browser rows, and batched release matrices

**Files:**
- Create: `lib/theme_factory/evidence_cache.py`
- Create: `tools/release_batch.py`
- Create: `tests/test_evidence_cache.py`
- Create: `tests/test_release_batch.py`
- Modify: `tools/live_matrix.py`
- Modify: `tools/browser_matrix.py`
- Modify: `lib/theme_factory/release.py`
- Modify: `tests/test_live_matrix.py`
- Modify: `tests/test_browser_matrix.py`
- Modify: `scripts/release-check.sh`

**Interfaces:**
- Consumes: current Layer C/D artifact writers and release validators.
- Produces: `EvidenceIdentity`; `checkpoint_valid(path: Path, expected: EvidenceIdentity) -> bool`; reusable `run_layer_c_theme`; reusable `run_layer_d_row`; batch CLI with `--themes`, fixed `--secondary`, and `--resume`.

- [ ] **Step 1: Write exhaustive checkpoint-identity tests**

Create one valid checkpoint and mutate source commit, package SHA, APEX version, browser version, consumer,
page, viewport, and scenario one at a time. Assert every mutation is a miss. Assert malformed JSON and schema
failure are misses with diagnostics rather than uncaught exceptions.

- [ ] **Step 2: Write interrupted-run tests**

Use fake SQL and fake Chrome clients. Complete two rows, interrupt, rerun with `--resume`, and assert those exact
rows are not repeated while the remaining rows run. Change the package SHA and assert all rows rerun.

- [ ] **Step 3: Run focused tests and confirm the batch APIs are absent**

Run: `python3 -m unittest tests.test_evidence_cache tests.test_release_batch -v`

Expected: FAIL importing the new cache and batch modules.

- [ ] **Step 4: Add browser/environment identity to raw evidence**

Record Chrome product/version from the daemon, APEX version, consumer, page, viewport, source commit, package
SHA, and `EVIDENCE_CONTRACT_VERSION`. Update the runtime evidence schema and release validation so absent or
mismatched fields fail closed.

- [ ] **Step 5: Separate reusable Layer E instruction evidence from theme-bound evidence**

Agent-runtime readiness, scenarios 04/05/09/14, and finding-resolution artifacts are bound to
`last_instruction_commit()` and may be referenced by multiple theme reports because their subject is the agent
instruction system. Any scenario that loads or judges a theme, including scenario 11, remains independently
bound to that theme's package SHA. Add tests proving a shared instruction artifact survives a package rebuild,
while theme-runtime evidence from the old SHA is rejected.

- [ ] **Step 6: Extract reusable single-unit runners**

Keep `tools/live_matrix.py` and `tools/browser_matrix.py` command lines compatible. Move one consumer lifecycle
and one browser row into functions returning typed results. Both call `assert_clean_source` immediately before
work and again before writing evidence.

- [ ] **Step 7: Implement safe Layer C batching**

Export each consumer baseline once. For each candidate: restore baseline; run install, reinstall, switcher,
fixed-secondary coexistence, uninstall, unrelated-file comparison, and restore; write independent theme-bound
evidence. Do not run reciprocal pairs because package-order behavior is already covered by candidate-first then
secondary install. If a candidate or restore fails, stop that consumer batch before the next theme.

- [ ] **Step 8: Implement Layer D batching and row checkpoints**

Install the candidate set once through the existing installer, use one daemon-owned background tab, and iterate
theme -> consumer/page -> 1440/1024/768/375. Before skipping a row, validate its complete identity and schema.
Write a checkpoint after each row and rebuild each theme summary from validated rows so interruption cannot
produce an optimistic PASS.

- [ ] **Step 9: Separate common offline verification from per-theme release checks**

Add `tests/run-common-offline.sh` for repository-wide tests and make a batch release invoke it once. Keep
`scripts/release-check.sh <theme>` backward compatible, but accept `--skip-common-offline` only when the caller
passes a fresh common-check artifact containing the current source digest and PASS status.

- [ ] **Step 10: Report obsolete evidence without deleting it**

Add `scripts/theme.sh release-batch --themes carbon-volt,velvet-signal --report-obsolete`. It lists evidence
directories whose source/package identity no longer matches. Add
`scripts/theme.sh evidence prune --keep-latest 2`; dry-run is mandatory by default, deletion requires
`--apply`, and tests require every deletion target to remain beneath `.agents/evaluations/runtime/`.

- [ ] **Step 11: Run release, lifecycle, browser, schema, and dirty-tree tests**

Run: `python3 -m unittest tests.test_evidence_cache tests.test_release_batch tests.test_live_matrix tests.test_browser_matrix tests.test_release_report tests.test_evidence_schema tests.test_capture_driver_dirty_checks -v`

Expected: PASS; interruption resumes valid rows, every identity mismatch reruns, and existing single-theme CLIs
still behave identically.

- [ ] **Step 12: Commit**

```bash
git add lib/theme_factory/evidence_cache.py lib/theme_factory/release.py tools/release_batch.py tools/live_matrix.py tools/browser_matrix.py scripts/release-check.sh tests/run-common-offline.sh tests/test_evidence_cache.py tests/test_release_batch.py tests/test_live_matrix.py tests/test_browser_matrix.py tests/live/runtime-evidence.schema.json
git commit -m "feat: batch and resume digest-bound release evidence"
```

### Task 13: CI tiers and changed-theme selection

**Files:**
- Create: `lib/theme_factory/changed.py`
- Create: `tests/test_changed_themes.py`
- Create: `.github/workflows/nightly.yml`
- Modify: `.github/workflows/verify.yml`
- Modify: `tests/run-offline.sh`
- Modify: `tests/run-package-offline.sh`

**Interfaces:**
- Consumes: discovery and `run_theme_checks`.
- Produces: `changed_themes(repo_root: Path, base: str, head: str) -> tuple[str, ...]`; CI JSON matrix.

- [ ] **Step 1: Write path-impact tests**

Assert a file under one package selects only that theme; a shared validator, template, foundation token,
installer, or workflow change selects all themes; a docs-only change outside generated sections selects none;
and a deleted theme is reported as a repository-wide check condition rather than passed to `theme check`.

- [ ] **Step 2: Run the focused test and confirm changed-theme logic is absent**

Run: `python3 -m unittest tests.test_changed_themes -v`

Expected: FAIL importing `lib.theme_factory.changed`.

- [ ] **Step 3: Implement Git diff classification**

Use `git diff --name-status -z base...head`, parse rename/delete records safely, map
`sample-themes/<name>/` paths to names, and return all discovered themes for shared-source prefixes listed in a
constant. Do not invoke a shell or interpolate refs.

- [ ] **Step 4: Update pull-request CI**

Run shell syntax and common unit tests once, run `catalog --check` and `inspect-iris --check`, compute a JSON
matrix, then run `theme check` only for affected themes. Build changed theme ZIPs with a CI source identity and
upload them as non-release artifacts. State explicitly that Layers C-E remain unverified.

- [ ] **Step 5: Add nightly complete offline/package CI**

Nightly discovers every theme, runs the complete offline suite once, checks every theme, builds every package,
verifies every ZIP, and uploads all archives. It performs no database import and does not start Chrome on a
GitHub-hosted runner.

- [ ] **Step 6: Replace two-theme package tests with discovery**

Modify `tests/run-package-offline.sh` to iterate strict discovered names rather than only Linen and
Solarized Dark. Preserve per-theme failure attribution and temporary-directory cleanup.

- [ ] **Step 7: Run CI-selection and offline suites**

Run: `python3 -m unittest tests.test_changed_themes -v`

Run: `bash tests/run-offline.sh`

Expected: `ALL_OFFLINE_CHECKS status=PASS`; workflow YAML parses and no hard-coded theme shortlist remains.

- [ ] **Step 8: Commit**

```bash
git add lib/theme_factory/changed.py tests/test_changed_themes.py .github/workflows/verify.yml .github/workflows/nightly.yml tests/run-offline.sh tests/run-package-offline.sh
git commit -m "ci: add fast changed-theme and nightly package tiers"
```

### Task 14: Iris token drift inspector

**Files:**
- Create: `lib/theme_factory/iris_inspector.py`
- Create: `tests/test_iris_inspector.py`
- Create: `tests/fixtures/iris-inspector/{Core,Iris,Widget-Core,Theme-Standard}.css`
- Create: `.agents/knowledge/reference/ut-26.1/iris-token-inventory.json`
- Create: `docs/generated/iris-26.1-token-report.md`
- Modify: `lib/theme_factory/cli.py`
- Modify: `scripts/fetch-vendor.sh`

**Interfaces:**
- Consumes: four pinned reference CSS files.
- Produces: `TokenDeclaration`; `TokenInventory`; `inspect_iris(reference_root: Path) -> TokenInventory`; `render_inventory_json`; `render_drift_report`; CLI `inspect-iris --check|--write`.

- [ ] **Step 1: Write parser blind-spot tests**

Fixture CSS must include multiple `:root` blocks, nested `var()` fallbacks, comments containing fake tokens,
element-scoped atoms, literal widget fallbacks, JET chains, and `--ut-palette-primary`. Assert the inventory
classifies each correctly and excludes commented fake declarations.

- [ ] **Step 2: Write independent-scan disagreement test**

Mock the structured parser to omit `--ut-palette-primary`; assert `inspect_iris` raises an error naming the
token because the independent token-name regex still sees it. This directly guards the parser failure recorded
in `pitfalls.md` section 1.10.

- [ ] **Step 3: Run tests and observe the absent inspector**

Run: `python3 -m unittest tests.test_iris_inspector -v`

Expected: FAIL importing `lib.theme_factory.iris_inspector`.

- [ ] **Step 4: Implement balanced CSS scanning and classification**

Mask comments and strings without changing offsets; scan balanced braces; parse declarations with balanced
parentheses; record file, selector, token, raw value, literal/chain status, fallback literals, and paired
text/background family. Independently collect token names with a second regex over comment-masked bytes and
require both name sets to match.

- [ ] **Step 5: Generate deterministic inventory and report**

Sort declarations by token, file, selector, and offset. JSON contains source-file SHA-256 values and APEX
version. Markdown summarizes literal root families, frozen chains, html-only JET atoms, widget fallbacks,
unpaired text/background atoms, additions, removals, and value changes versus the committed inventory.

- [ ] **Step 6: Integrate with vendor refresh**

After `fetch-vendor.sh` updates reference bytes, print the exact command `scripts/theme.sh inspect-iris --write`.
Do not silently update the inventory during a fetch. `--check` exits 2 on drift and is part of CI.

- [ ] **Step 7: Run inspector and related policy tests**

Run: `scripts/theme.sh inspect-iris --write`

Run: `python3 -m unittest tests.test_iris_inspector tests.test_css_policy -v`

Expected: PASS; `scripts/theme.sh inspect-iris --check` exits 0 and the inventory contains
`--ut-palette-primary`, `--a-palette-primary`, and `--oj-core-text-color-primary`.

- [ ] **Step 8: Commit**

```bash
git add lib/theme_factory/iris_inspector.py lib/theme_factory/cli.py tests/test_iris_inspector.py tests/fixtures/iris-inspector .agents/knowledge/reference/ut-26.1/iris-token-inventory.json docs/generated/iris-26.1-token-report.md scripts/fetch-vendor.sh
git commit -m "feat: detect Universal Theme token drift"
```

### Task 15: Behavior-preserving APEXLang module split

**Files:**
- Create: `lib/theme_factory/apexlang_model.py`
- Create: `lib/theme_factory/apexlang_parser.py`
- Create: `lib/theme_factory/apexlang_runtime.py`
- Create: `lib/theme_factory/apexlang_state.py`
- Create: `lib/theme_factory/apexlang_patch.py`
- Modify: `lib/theme_factory/apexlang.py`
- Modify: `tests/test_apexlang_patch.py`
- Modify: `tests/test_apexlang_roundtrip_sim.py`
- Modify: `tests/test_lifecycle_real_shape.py`

**Interfaces:**
- Consumes: the existing public names in `lib.theme_factory.apexlang`.
- Produces: focused internal modules while `lib.theme_factory.apexlang` re-exports every existing public class and function with unchanged signatures.

- [ ] **Step 1: Freeze the compatibility surface**

Add a test with the exact public names imported by repository callers:

```python
PUBLIC = {
    "InstalledPackage", "TargetExport", "InstallPatch", "strip_bootstrap_regions",
    "strip_switcher_entries", "list_is_static", "insert_switcher_entries",
    "build_bootstrap_html", "build_bootstrap_regions", "build_switcher_entries",
    "inspect_export", "read_registry_document", "read_install_state",
    "verify_package_ownership", "verify_runtime_ownership", "canonical_digest",
    "plan_install", "set_file_urls", "apply_navigation_menu_style",
    "theme_factory_projection", "apply_patch",
}
self.assertTrue(PUBLIC.issubset(set(dir(apexlang))))
```

- [ ] **Step 2: Run the full APEXLang/lifecycle baseline before moving code**

Run: `python3 -m unittest tests.test_apexlang_patch tests.test_apexlang_roundtrip_sim tests.test_lifecycle_real_shape tests.test_installer_cli tests.test_uninstaller_cli -v`

Expected: PASS; save the test count in the commit message.

- [ ] **Step 3: Move dataclasses without behavior changes**

Move `InstalledPackage`, `TargetExport`, and `InstallPatch` to `apexlang_model.py`; re-export them immediately;
run the focused suite and commit only after it passes.

- [ ] **Step 4: Move balanced block/string parsing helpers**

Move `_find_matching_brace`, `_iter_blocks`, span removal, list-block parsing, and formatting helpers to
`apexlang_parser.py`. Keep private aliases in the facade only where tests or internal callers still need them.
Run the focused suite.

- [ ] **Step 5: Move runtime source renderers**

Move bootstrap HTML/regions and switcher-entry rendering to `apexlang_runtime.py`. Keep output byte-identical by
asserting golden strings from current tests. Run the focused suite.

- [ ] **Step 6: Move inspection and semantic projection**

Move export inspection, registry/install-state reading, ownership verification, canonical digest, and semantic
projection to `apexlang_state.py`. Run round-trip and real-shape tests.

- [ ] **Step 7: Move planning and mutation**

Move install planning, file URL edits, navigation style edits, and patch application to `apexlang_patch.py`.
Leave `apexlang.py` as documented imports plus `__all__`. Run installer/uninstaller tests.

- [ ] **Step 8: Run every offline test**

Run: `bash tests/run-offline.sh`

Expected: `ALL_OFFLINE_CHECKS status=PASS` with no changed golden APEXLang output.

- [ ] **Step 9: Commit**

```bash
git add lib/theme_factory/apexlang.py lib/theme_factory/apexlang_model.py lib/theme_factory/apexlang_parser.py lib/theme_factory/apexlang_runtime.py lib/theme_factory/apexlang_state.py lib/theme_factory/apexlang_patch.py tests/test_apexlang_patch.py tests/test_apexlang_roundtrip_sim.py tests/test_lifecycle_real_shape.py
git commit -m "refactor: split APEXLang responsibilities without behavior changes"
```

### Task 16: Workflow benchmark and token-efficiency evidence

**Files:**
- Create: `tools/theme_benchmark.py`
- Create: `tests/test_theme_benchmark.py`
- Create: `tests/fixtures/benchmark/baseline.json`
- Create: `docs/THEME_WORKFLOW_BENCHMARK.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: Theme Workshop commands and externally supplied agent usage totals.
- Produces: `BenchmarkRun`; `summarize_runs(baseline: BenchmarkRun, candidates: Sequence[BenchmarkRun]) -> BenchmarkSummary`; CLI `record` and `report`.

- [ ] **Step 1: Write calculation and missing-usage tests**

```python
def test_token_reduction_is_calculated_from_total_input_and_output(self):
    summary = summarize_runs(self.baseline(tokens=100_000), [self.run(tokens=45_000)])
    self.assertEqual(summary.token_reduction_percent, 55.0)

def test_success_target_requires_three_candidate_runs_with_token_usage(self):
    with self.assertRaisesRegex(PackageError, "three.*token"):
        summarize_runs(self.baseline(tokens=100_000), [self.run(tokens=None)])
```

- [ ] **Step 2: Run the test and confirm the benchmark module is absent**

Run: `python3 -m unittest tests.test_theme_benchmark -v`

Expected: FAIL importing `tools.theme_benchmark`.

- [ ] **Step 3: Implement measurement records**

Record theme, source commit, recipe SHA, started/finished timestamps, scaffold/check/dev wall times, commands,
files read, files written, validation reruns, browser rows, input tokens, output tokens, and result. Validate
nonnegative values and exact source identities. `record` accepts token totals explicitly from the agent harness;
it never estimates tokens from characters.

- [ ] **Step 4: Add a repeatable benchmark protocol**

Document one compact light theme, one technical dark theme, and one font-bearing bilingual theme. For each,
start from a clean worktree, use the same requirement prompt, stop after candidate-lane PASS, and record usage.
Compare median candidate results with the preserved four-theme baseline. Report scaffold under 10 seconds,
check under 30 seconds, first preview under 120 seconds, and token reduction at least 50 percent separately.

- [ ] **Step 5: Run calculation tests and a local no-browser smoke benchmark**

Run: `python3 -m unittest tests.test_theme_benchmark -v`

Run: `python3 tools/theme_benchmark.py report --baseline tests/fixtures/benchmark/baseline.json --runs scratch/theme-benchmarks --allow-incomplete`

Expected: tests PASS; incomplete report labels every unmeasured target `UNVERIFIED`, never PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/theme_benchmark.py tests/test_theme_benchmark.py tests/fixtures/benchmark/baseline.json docs/THEME_WORKFLOW_BENCHMARK.md README.md
git commit -m "feat: measure theme workflow speed and token usage"
```

### Task 17: Documentation, final source verification, live deployment, and evidence recapture

**Files:**
- Modify: `README.md`
- Modify: `sample-themes/README.md`
- Modify: `docs/DESIGN_SYSTEM.md`
- Modify: `docs/COMPONENTS.md`
- Modify: `docs/PROJECT.md`
- Modify: `docs/CHROME_DEVTOOLS_MCP.md`
- Modify: `.agents/knowledge/pitfalls.md` only for newly confirmed traps
- Modify: generated APEXLang static files from `scripts/sync-static.sh`
- Create/Modify: `.agents/evaluations/runtime/<date>-release-<theme>/**`
- Modify: `tests/live/RELEASE-MATRIX.md`

**Interfaces:**
- Consumes: every preceding task.
- Produces: documented workflow, clean source commit, app-102 Theme Lab deployment, current Layers C-E evidence, generated catalog, and benchmark report.

- [ ] **Step 1: Document the final command contract**

Document author, candidate, and release lanes; recipe schema; generated ownership markers; font provenance;
cache invalidation; Theme Lab coverage; cover etiquette; CI limits; and the fact that candidate PASS is not a
release verdict. Replace manual copy/rename instructions with `scripts/theme.sh new`, retaining a legacy-package
maintenance note.

- [ ] **Step 2: Register reusable patterns**

Add Theme Lab specimen groups and template-time component profiles to `docs/COMPONENTS.md` and the visual-pattern
registry in `docs/DESIGN_SYSTEM.md`. State that profiles are copied into packages at creation and are not shared
runtime CSS.

- [ ] **Step 3: Run generated-file checks and full offline verification**

Run: `scripts/theme.sh catalog --write`

Run: `scripts/theme.sh inspect-iris --check`

Run: `scripts/sync-static.sh`

Run: `scripts/apex-validate.sh`

Run: `bash tests/run-offline.sh`

Expected: APEXLang `Validation successful.` and `ALL_OFFLINE_CHECKS status=PASS`.

- [ ] **Step 4: Inspect the generated diff and commit all source**

Run: `git status --short` and `git diff --check`.

Confirm no temporary venv, TTF, download cache, scratch screenshot, iteration PNG, or package ZIP is staged.
Commit all source, generated static files, tests, workflow files, and documentation before building packages.

Stage only the remaining planned documentation and generated app-102 outputs; every implementation task has
already committed its own source:

```bash
git add README.md sample-themes/README.md docs/DESIGN_SYSTEM.md docs/COMPONENTS.md docs/PROJECT.md docs/CHROME_DEVTOOLS_MCP.md \
  static-files/css/app.css applications/ut/shared-components/static-files applications/ut/shared-components/static-files.apx
git commit -m "feat: accelerate high-quality APEX theme production"
```

- [ ] **Step 5: Build and verify every current theme package**

Run discovery to obtain the exact list, then build and verify each name:

```bash
mapfile -t themes < <(python3 -c 'from pathlib import Path; from lib.theme_factory.discovery import theme_names; print(*theme_names(Path.cwd()), sep="\n")')
for theme in "${themes[@]}"; do
  version="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "sample-themes/$theme/theme.json")"
  scripts/package-theme.sh "$theme" "dist/$theme"
  python3 -m lib.theme_factory.cli verify-package --package "dist/$theme/$theme-$version.zip"
done
```

Expected: eight deterministic ZIPs, each bound to the final source commit and containing only its own runtime
assets. Confirm `package_matches_source` for every ZIP before any live capture.

- [ ] **Step 6: Import app 102 only with the user's explicit authorization**

When authorized, run the existing SQLcl workflow after the final sync and validate. Export app 102 afterward,
compare the semantic projection, and ensure page 406 plus static assets round-trip. If authorization is not
present, record candidate runtime verification as blocked and do not claim it.

- [ ] **Step 7: Verify the Theme Lab through the approved daemon**

Use a private background tab, per-tab emulation at 1440, 1024, 768, and 375, and each theme plus bare Iris.
Exercise buttons, required error state, IR, IG, calendar, JET chart, menu, date picker, Popup LOV, modal, drawer,
Arabic/Latin specimens, every declared font weight, focus, hover, selected, disabled, and error states. Record
console errors, failed requests, overflow, clipped actions, contrast node counts, SVG text counts, WOFF2 MIME,
and Font APEX before/after. Close the tab.

- [ ] **Step 8: Capture covers with explicit overwrite**

For every theme whose design is approved, run `scripts/theme.sh cover NAME --apply --overwrite`. Confirm each
JPEG is 960 px wide, catalog discovery still works, and no capture changed `localStorage` or the user's active
tab.

- [ ] **Step 9: Capture one batched Layers C and D run without touching source**

Run `tools/release_batch.py` with all eight package paths, the two disposable consumer app IDs, fixed valid
secondary theme, business/minimal URLs, standard widths, evidence root, `--resume`, and `--apply`. Do not edit,
format, regenerate, or run an agent smoke that writes source while the batch is active. Any failure remains a
FAIL artifact and blocks the affected theme.

- [ ] **Step 10: Regenerate Layer E and final reports**

Run the three agent runtimes plus instruction-only scenarios/finding-resolution checks once against the final
instruction commit. Run theme-runtime scenarios, including scenario 11, separately for each final package SHA.
Run `scripts/release-check.sh` for every theme. Only themes with all A-E PASS may render `VERIFIED`; others
remain explicitly `UNVERIFIED` with the missing layer named.

- [ ] **Step 11: Run three benchmark trials and generate the report**

Execute the documented light, dark, and bilingual-font trials in clean disposable worktrees. Supply actual
agent input/output token totals from each harness and generate `docs/THEME_WORKFLOW_BENCHMARK.md`. If the median
does not meet a target, report the measured value and bottleneck; do not change thresholds after observing it.

- [ ] **Step 12: Regenerate catalog/release Markdown and commit evidence only**

Run `scripts/theme.sh catalog --write`, verify that only evidence and Markdown changed after capture, and commit
those files. This preserves the last source commit to which package and runtime evidence are bound.

```bash
git add .agents/evaluations/runtime tests/live/RELEASE-MATRIX.md sample-themes/README.md README.md docs/THEME_WORKFLOW_BENCHMARK.md
git commit -m "docs: record accelerated theme workflow evidence"
```

- [ ] **Step 13: Final verification**

Run: `bash tests/run-offline.sh`

Run: `scripts/theme.sh catalog --check`

Run: `scripts/theme.sh inspect-iris --check`

Run each current `scripts/release-check.sh <theme>`.

Expected: offline PASS, generated files clean, inspector clean, and release verdicts exactly match current
evidence. Run `git status --short`; expected output is empty.

---

## Self-Review Results

- **Spec coverage:** Every design section is mapped: lanes/CLI (Tasks 7-8), recipes/scaffold/component profiles
  (Tasks 2-4), fonts (Task 5), uniqueness (Task 6), Theme Lab (Task 10), cover/visual comparison (Task 11),
  discovery/catalog/docs (Tasks 1 and 9), resumable batching/evidence (Task 12), CI (Task 13), Iris drift
  inspection (Task 14), APEXLang maintainability (Task 15), measurement (Task 16), and final live proof (Task 17).
- **Placeholder scan:** The plan contains no deferred implementation markers or unspecified error-handling/test
  instructions. Commands, signatures, failure conditions, and acceptance results are explicit.
- **Type consistency:** `ThemeRecipe`, `DiscoveredTheme`, `CheckReport`, `EvidenceIdentity`, and the public CLI
  handlers are introduced before downstream use. Existing manifest, package, release, and APEXLang interfaces
  remain the compatibility boundaries.
- **Review Focus coverage:** Name/path collisions are tested in Tasks 1/3; font axes/license/coverage in Task 5;
  cache and resume identities in Tasks 7/12; Chrome state/tab cleanup in Task 11; and recipe-less legacy themes
  plus invalid manifests in Tasks 1/4/6/9.
