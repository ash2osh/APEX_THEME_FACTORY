# Theme Uniqueness Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate themes from neutral Iris scaffolding and upgrade all eight shipped packages into measurably and visibly distinct design systems without sacrificing APEX behavior or accessibility.

**Architecture:** Recipe schema version 2 makes density, typographic rhythm, interaction, and responsive strategy explicit. The scaffold composes neutral Universal Theme adapters with independent component profiles; the fingerprint gate measures those axes and produces a pairwise report. Each existing theme is migrated and restyled against an approved identity matrix, then verified offline and at runtime.

**Tech Stack:** Python 3 dataclasses/JSON, CSS custom properties, Universal Theme 42/Iris, WOFF2 fonts, `unittest`, existing package/archive tools, APEXLang/SQLcl, approved Chrome DevTools project daemon.

**Spec:** `docs/superpowers/specs/2026-09-20-release-gates-and-theme-uniqueness-design.md`

## Global Constraints

- APEX remains 26.1.x, Universal Theme 42, Iris only; Linen remains the default.
- Existing names and classes remain stable: `app-theme-<name>`.
- New source starts from `theme-templates/neutral`, never by copying Linen or another theme.
- Shared UT selectors, dark-token coverage, accessibility rules, and packaging structure are allowed; visual values and profile combinations are theme-owned.
- Every selector remains scoped to its theme class, except documented `html.app-theme-<name>` JET tokens.
- No external runtime font URLs, Theme Roller output, alternate theme styles, custom replacement markup, or new Alpine behavior.
- Existing font provenance, licenses, WOFF2 files, and Font APEX isolation remain intact.
- Material visual changes use minor package version bumps.
- Import app 102 and run Chrome verification only after explicit user authorization at execution time.

## Review Focus

- A neutral scaffold must contain no Linen identifier, palette literal, or copied handwritten module; Task 3 pins this.
- A dark theme must retain complete Iris/frozen-palette/JET coverage even when its structure changes; Tasks 7–9 pin this.
- A pair with different colors but the same structure/profile vector must fail author checks; Task 4 pins this.
- Mobile uniqueness must not create overflow, clipped actions, or unusable data controls; Tasks 6–10 pin this at 375 and 768 pixels.
- Shared fonts or similar modes must not create false identity collisions when the remaining axes differ; Task 4 pins this.

---

### Task 1: Capture the current pairwise baseline

**Files:**
- Create: `lib/theme_factory/uniqueness_report.py`
- Create: `tests/test_uniqueness_report.py`
- Create: `docs/generated/theme-uniqueness-report.md`

**Interfaces:**
- Consumes: `fingerprint_theme`, `compare_fingerprints`, and `discover_themes`.
- Produces: `build_uniqueness_rows(repo_root: Path) -> tuple[PairwiseUniquenessRow, ...]`; `render_uniqueness_report(rows) -> str`; CLI module entry supporting `--check`.

- [ ] **Step 1: Write deterministic report tests**

Create tests asserting:

- eight discovered themes produce exactly 28 unordered pair rows;
- rows sort by descending CSS similarity, then theme names;
- each row prints CSS similarity, average palette Delta E, matching profile count, font match, geometry match, severity, and issue code;
- `--check` detects drift without writing.

- [ ] **Step 2: Run the test and confirm the module is missing**

Run: `python3 -m unittest tests.test_uniqueness_report -v`

Expected: FAIL importing `lib.theme_factory.uniqueness_report`.

- [ ] **Step 3: Implement the report module**

Deduplicate candidate/existing pairs with a sorted `(left.name, right.name)` key. Render a heading with the source commit, thresholds, and a Markdown table. Include warning-free pairs as `PASS`; do not hide near matches.

- [ ] **Step 4: Generate the baseline report**

Run: `python3 -m lib.theme_factory.uniqueness_report --repo-root . --output docs/generated/theme-uniqueness-report.md`

Expected: 28 rows. The current duplicated shell structures, including Cobalt Press/Citrus Pop/Estate Slate and Carbon Volt/Velvet Signal/Solarized Dark, are visible even when they do not yet fail.

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m unittest tests.test_uniqueness_report tests.test_theme_fingerprint -v`

Expected: PASS.

```bash
git add lib/theme_factory/uniqueness_report.py tests/test_uniqueness_report.py docs/generated/theme-uniqueness-report.md
git commit -m "feat: generate pairwise theme uniqueness report"
```

### Task 2: Add recipe schema version 2

**Files:**
- Modify: `lib/theme_factory/recipe.py`
- Modify: `lib/theme_factory/scaffold.py`
- Modify: `lib/theme_factory/cli.py`
- Modify: `tests/test_theme_recipe.py`
- Modify: `tests/test_recipe_rendering.py`
- Modify: `tests/test_theme_cli.py`
- Modify: `theme-templates/neutral/theme.recipe.json.tmpl`
- Modify: `docs/DESIGN_SYSTEM.md`

**Interfaces:**
- Consumes: existing `ThemeRecipe`, `load_recipe`, and version-1 fields.
- Produces: `Rhythm`, `Interaction`, and `Responsive` dataclasses; version-2 recipes; version-1 read compatibility.

- [ ] **Step 1: Add schema tests**

Test a valid version-2 recipe containing:

```json
"rhythm": {"density":"compact","spacing":"technical","typeScale":"compact"},
"interaction": {"hover":"shift","selected":"outline","motion":"precise"},
"responsive": {"strategy":"compress","compactControlsAt":768}
```

Add one failing test for every invalid enum and for `compactControlsAt: 640`. Add a version-1 fixture and assert it receives deterministic compatibility defaults: `balanced`, `technical`, `balanced`, `none`, `fill`, `precise`, `reflow`, `768`.

- [ ] **Step 2: Run recipe tests and confirm version 2 fails**

Run: `python3 -m unittest tests.test_theme_recipe -v`

Expected: FAIL because only schema version 1 and the old root keys are accepted.

- [ ] **Step 3: Implement strict parsing**

Add frozen dataclasses:

```python
@dataclass(frozen=True)
class Rhythm:
    density: str
    spacing: str
    type_scale: str

@dataclass(frozen=True)
class Interaction:
    hover: str
    selected: str
    motion: str

@dataclass(frozen=True)
class Responsive:
    strategy: str
    compact_controls_at: int
```

Accept schema versions 1 and 2. Version 2 requires all three new objects and rejects unknown keys. Version 1 uses the compatibility defaults only when loading; all newly emitted recipes are version 2. Update `scaffold.py` serialization and the CLI's inline neutral recipe constructor to provide the new dataclasses explicitly.

- [ ] **Step 4: Update the neutral recipe template and design-system docs**

The template must require explicit choices; it must not silently stamp Linen's choices. Document every enum and the supported widths.

- [ ] **Step 5: Run and commit**

Run: `python3 -m unittest tests.test_theme_recipe tests.test_recipe_rendering tests.test_theme_cli -v`

Expected: PASS.

```bash
git add lib/theme_factory/recipe.py lib/theme_factory/scaffold.py lib/theme_factory/cli.py tests/test_theme_recipe.py tests/test_recipe_rendering.py tests/test_theme_cli.py theme-templates/neutral/theme.recipe.json.tmpl docs/DESIGN_SYSTEM.md
git commit -m "feat: model theme rhythm interaction and responsiveness"
```

### Task 3: Compile a neutral, non-copying scaffold

**Files:**
- Modify: `lib/theme_factory/scaffold.py`
- Modify: `tests/test_theme_scaffold.py`
- Modify: `theme-templates/neutral/css/tokens.css.tmpl`
- Modify: `theme-templates/neutral/css/apex/misc.css.tmpl`
- Modify: `README.md`

**Interfaces:**
- Consumes: schema-v2 `ThemeRecipe` and existing component-profile templates.
- Produces: `scaffold_theme(recipe, destination, overwrite_generated=False)` with the existing public signature preserved if already established; neutral output provenance marker; deterministic CSS tokens/rules for recipe rhythm, interaction, and responsive axes.

- [ ] **Step 1: Add anti-copy tests**

Scaffold a fixture named `test-neutral` and assert:

```python
combined = "\n".join(path.read_text() for path in generated_css_paths)
self.assertNotIn("linen", combined.casefold())
self.assertNotIn("app-theme-linen", combined)
self.assertNotIn("#fffaf0", combined.casefold())  # reserved Linen canvas literal
self.assertIn("/* generated-from: theme-templates/neutral */", combined)
```

Also hash every handwritten `sample-themes/*/css/apex/*.css` file and assert no generated module has an identical hash after scope-name normalization.

Add generated-CSS assertions for a compact/technical/display/shift/outline/precise/compress fixture:

```python
self.assertIn("--app-density-scale: 0.875", tokens)
self.assertIn("--app-space-unit: 0.375rem", tokens)
self.assertIn("--app-heading-scale: 1.5", tokens)
self.assertIn("--app-hover-transform: translateX(2px)", tokens)
self.assertIn("--app-motion-duration: 120ms", tokens)
self.assertIn("--app-selected-treatment: outline", tokens)
self.assertIn("@media (max-width: 768px)", misc)
self.assertIn("--app-responsive-strategy: compress", misc)
self.assertIn("prefers-reduced-motion: reduce", misc)
```

- [ ] **Step 2: Run the scaffold test and confirm the provenance assertion fails**

Run: `python3 -m unittest tests.test_theme_scaffold -v`

Expected: FAIL until the recipe-axis tokens, responsive/reduced-motion rules, neutral provenance marker, and normalized-copy guard exist.

- [ ] **Step 3: Add deterministic recipe-to-CSS mappings**

Render these exact maps into the neutral token template:

| Axis | Value → emitted token |
|---|---|
| density | `compact → --app-density-scale: 0.875`, `balanced → 1`, `spacious → 1.125` |
| spacing | `technical → --app-space-unit: 0.375rem`, `editorial → 0.5rem`, `soft → 0.625rem`, `playful → 0.75rem` |
| typeScale | `compact → --app-heading-scale: 1.125`, `balanced → 1.25`, `editorial → 1.375`, `display → 1.5` |
| hover | `none → none`, `lift → translateY(-2px)`, `shift → translateX(2px)`, `glow → none` plus `--app-hover-shadow: 0 0 0 3px color-mix(in srgb, var(--app-accent), transparent 70%)` |
| motion | `none → 0ms`, `precise → 120ms`, `smooth → 180ms`, `buoyant → 240ms` |
| selected | emit the enum unchanged as `--app-selected-treatment` for the selected-state profile rule |

Render one media query at `responsive.compact_controls_at`. `compress` reduces control height and space unit by 12.5%; `reflow` enables wrapping for button/header action containers; `stack` changes generated card/action layout hooks to one column. Always emit a `prefers-reduced-motion: reduce` block setting duration to `0ms` and transform to `none`.

- [ ] **Step 4: Add provenance and copy protection**

Every generated CSS file starts with:

```css
/* @theme-factory-generated */
/* generated-from: theme-templates/neutral */
/* profile: <profile-name> */
```

Before writing a new theme, compare its normalized generated module hashes to discovered handwritten modules. Raise `PackageError` if an entire visual module matches a handwritten theme after only scope substitution. The guard does not reject shared neutral safety fragments or generated profile templates.

- [ ] **Step 5: Document the authoring boundary**

In README, state: neutral UT adapters are shared; recipes choose a new composition; no theme is a parent; Linen is only the default runtime selection.

- [ ] **Step 6: Run and commit**

Run: `python3 -m unittest tests.test_theme_scaffold tests.test_theme_recipe -v`

Expected: PASS.

```bash
git add lib/theme_factory/scaffold.py tests/test_theme_scaffold.py theme-templates/neutral/css/tokens.css.tmpl theme-templates/neutral/css/apex/misc.css.tmpl README.md
git commit -m "feat: enforce neutral non-copying theme scaffolds"
```

### Task 4: Strengthen the uniqueness fingerprint and gate

**Files:**
- Modify: `lib/theme_factory/fingerprint.py`
- Modify: `tests/test_theme_fingerprint.py`
- Modify: `tests/test_new_theme_packages.py`
- Modify: `lib/theme_factory/cli.py`

**Interfaces:**
- Consumes: schema-v2 recipe fields.
- Produces: expanded `ThemeFingerprint` and `SimilarityReport`; stable issue codes from the design spec; `theme.sh check` fails on error-level issues.

- [ ] **Step 1: Add threshold and false-positive tests**

Build recipe-backed fixtures and add tests for:

- palette-only recolor at `>=0.98` plus five profiles → `STRUCTURAL_RECOLOR` error;
- `>=0.92` plus five profiles → `PROFILE_COLLISION` error;
- identical rhythm/type treatment/interaction/responsive plus Delta E `<20` → `IDENTITY_COLLISION` error;
- same font family but distinct geometry, profiles, interaction, and responsive strategy → no identity error;
- `>=0.85` without an error condition → `STRUCTURAL_SIMILARITY` warning;
- warning-only findings do not make `theme.sh check` fail.

- [ ] **Step 2: Run tests and confirm missing dimensions fail**

Run: `python3 -m unittest tests.test_theme_fingerprint -v`

Expected: FAIL because rhythm, type-scale treatment, interaction, and responsive strategy are absent.

- [ ] **Step 3: Expand fingerprints**

Add immutable fields:

```python
rhythm: tuple[tuple[str, str], ...]
typography: tuple[tuple[str, str], ...]
interaction: tuple[tuple[str, str], ...]
responsive: tuple[tuple[str, str], ...]
```

For legacy recipes/CSS, derive conservative values without claiming uniqueness. Update issue messages to print each match dimension. Retain the current color parser and normalized module shingles.

- [ ] **Step 4: Implement the exact thresholds**

Apply the rules in design section 3.5 in priority order: recolor, profile collision, identity collision, structural warning, then lower-risk informational similarity. One pair must produce at most one error code and may additionally carry explanatory metrics in the report.

- [ ] **Step 5: Wire author checks**

Ensure `scripts/theme.sh check NAME` compares against all discovered themes and exits nonzero on any error-level finding. Print warnings with the nearest theme and all metrics.

- [ ] **Step 6: Run and commit**

Run: `python3 -m unittest tests.test_theme_fingerprint -v`

Expected: PASS. Then run `python3 -m unittest tests.test_new_theme_packages.NewThemePackageTests.test_all_current_themes_avoid_error_level_uniqueness_findings -v` and record its expected error-level collisions as the red baseline for Tasks 6–9; no other package-policy failure is accepted.

```bash
git add lib/theme_factory/fingerprint.py lib/theme_factory/cli.py tests/test_theme_fingerprint.py tests/test_new_theme_packages.py
git commit -m "feat: gate multi-axis theme uniqueness"
```

### Task 5: Migrate all eight packages to explicit version-2 recipes

**Files:**
- Create: `sample-themes/{linen,estate-slate,estate-slate-dark,solarized-dark,carbon-volt,velvet-signal,cobalt-press,citrus-pop}/theme.recipe.json`
- Modify: `tests/test_new_theme_packages.py`

**Interfaces:**
- Consumes: schema-v2 recipe loader and identity matrix.
- Produces: eight loadable recipes with unique complete profile vectors.

- [ ] **Step 1: Add package-wide recipe tests**

Assert every discovered theme has a recipe, schema version 2, identity name matching its directory/manifest, and a complete rhythm/interaction/responsive block. Assert no two themes have the same tuple of component profiles, rhythm, interaction, and responsive strategy.

- [ ] **Step 2: Run the package test and confirm all eight recipes are missing**

Run: `python3 -m unittest tests.test_new_theme_packages -v`

Expected: FAIL listing the eight missing `theme.recipe.json` files.

- [ ] **Step 3: Write the recipes from the identity matrix**

Use the exact profile choices below:

| Theme | navigation | cards | buttons | forms | reports | dialogs | density | spacing | typeScale | hover | selected | motion | responsive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linen | minimal | flat | rounded | comfortable | spacious | flat | balanced | editorial | editorial | none | underline | precise | reflow |
| estate-slate | editorial | flat | rounded | outlined | ruled | layered | balanced | technical | balanced | shift | rail | precise | reflow |
| estate-slate-dark | rail | layered | square | dense | spacious | offset | compact | technical | compact | glow | rail | precise | compress |
| solarized-dark | minimal | flat | underline | dense | ruled | flat | compact | technical | compact | none | underline | none | compress |
| carbon-volt | rail | offset | square | dense | ruled | offset | compact | technical | display | shift | outline | precise | compress |
| velvet-signal | pill | layered | rounded | soft | spacious | layered | spacious | soft | display | lift | fill | smooth | stack |
| cobalt-press | editorial | offset | underline | outlined | ruled | offset | balanced | editorial | editorial | shift | underline | precise | reflow |
| citrus-pop | pill | buoyant | pill | soft | spacious | layered | spacious | playful | display | lift | fill | buoyant | stack |

Use each current manifest palette/font/provenance as source truth. Do not synthesize new font assets.
Set `compactControlsAt` to `768` for all eight recipes so responsive behavior changes at a width exercised by the required matrix.

- [ ] **Step 4: Validate recipes**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
from lib.theme_factory.recipe import load_recipe, validate_core_contrast

for path in sorted(Path("sample-themes").glob("*/theme.recipe.json")):
    recipe = load_recipe(path)
    issues = validate_core_contrast(recipe)
    if issues:
        raise SystemExit(f"{path}: " + "; ".join(issue.message for issue in issues))
    print(f"RECIPE theme={recipe.identity.name} status=PASS")
PY
```

Expected: every recipe parses and passes static contrast checks. The full uniqueness gate remains the red baseline until CSS upgrades are complete.

- [ ] **Step 5: Commit recipes**

```bash
git add sample-themes/*/theme.recipe.json tests/test_new_theme_packages.py
git commit -m "feat: define explicit identities for every theme"
```

### Task 6: Upgrade Linen and Estate Slate as distinct light systems

**Files:**
- Modify: `sample-themes/linen/theme.json`
- Modify: `sample-themes/linen/css/tokens.css`
- Modify: `sample-themes/linen/css/apex/{shell,regions,buttons,forms,reports,dialogs,misc}.css`
- Modify: `sample-themes/linen/README.md`
- Modify: `sample-themes/estate-slate/theme.json`
- Modify: `sample-themes/estate-slate/css/tokens.css`
- Modify: `sample-themes/estate-slate/css/apex/{shell,regions,buttons,forms,reports,dialogs,misc}.css`
- Modify: `sample-themes/estate-slate/README.md`
- Modify: `tests/test_new_theme_packages.py`

**Interfaces:**
- Consumes: the recipes from Task 5 and existing UT/Iris selectors.
- Produces: Linen `1.1.0` and Estate Slate `1.1.0`, matching their matrix rows.

- [ ] **Step 1: Add identity assertions**

Add source tests that assert Linen uses no header accent strip, editorial title tracking, hairline/flat region shadows, and underline selected navigation; assert Estate Slate uses section markers, metric-strip regions, outlined form borders, ruled data rows, and rail selection. Assert their normalized shell/region/button modules are not identical.

- [ ] **Step 2: Run the focused package tests and confirm failure**

Run: `python3 -m unittest tests.test_new_theme_packages -v`

Expected: FAIL on the new identity markers.

- [ ] **Step 3: Restyle Linen**

Keep it quiet and low-elevation: warm page, white/paper cards, hairline separators, no decorative lift, editorial heading scale, text-led minimal navigation, and an underline selected state. Preserve system/Iris typography and Linen as default.

- [ ] **Step 4: Restyle Estate Slate**

Build formal property-operation hierarchy: compact slate chrome, champagne section markers, metric strips, crisp outlined fields, ruled financial/report surfaces, and layered dialogs. Do not reuse Linen's flat paper composition.

- [ ] **Step 5: Bump versions and update READMEs**

Set both manifests to `1.1.0`. Record the identity matrix, upgrade notes, and unchanged font provenance.

- [ ] **Step 6: Run checks**

Run: `scripts/theme.sh check linen && scripts/theme.sh check estate-slate && python3 -m unittest tests.test_new_theme_packages -v`

Expected: no error-level uniqueness finding for either theme and all focused tests PASS.

- [ ] **Step 7: Commit**

```bash
git add sample-themes/linen sample-themes/estate-slate tests/test_new_theme_packages.py
git commit -m "feat: distinguish linen and estate slate identities"
```

### Task 7: Upgrade Estate Slate Dark and Solarized Dark as independent dark systems

**Files:**
- Modify: `sample-themes/estate-slate-dark/theme.json`
- Modify: `sample-themes/estate-slate-dark/css/tokens.css`
- Modify: `sample-themes/estate-slate-dark/css/apex/{shell,regions,buttons,forms,reports,dialogs,misc}.css`
- Modify: `sample-themes/estate-slate-dark/README.md`
- Modify: `sample-themes/solarized-dark/theme.json`
- Modify: `sample-themes/solarized-dark/css/tokens.css`
- Modify: `sample-themes/solarized-dark/css/apex/{shell,regions,buttons,forms,reports,dialogs,misc}.css`
- Modify: `sample-themes/solarized-dark/README.md`
- Modify: `tests/test_new_theme_packages.py`

**Interfaces:**
- Consumes: complete dark-theme token policy and recipes.
- Produces: Estate Slate Dark `1.1.0` and Solarized Dark `1.2.0` with different structures and behavior.

- [ ] **Step 1: Add dark identity and coverage tests**

Assert both themes retain `color-scheme`, frozen `--a-palette-*`, `--oj-*` on `html`, SVG chart text, menus, grids, date picker, Popup LOV, dialog, and utility-report coverage. Then assert Estate Slate Dark has rail/layered/map-frame markers and Solarized Dark has minimal/flat/terminal-rule markers.

- [ ] **Step 2: Run tests and confirm identity assertions fail**

Run: `python3 -m unittest tests.test_new_theme_packages -v`

Expected: coverage tests pass or expose existing gaps; new structural identity assertions fail.

- [ ] **Step 3: Restyle Estate Slate Dark**

Make it a compact geospatial intelligence cockpit: dense rail navigation, layered monitor panels, inset map-like frames, luminous amber/emerald state rails, square controls, and offset detail dialogs. It must not share Estate Slate's light-theme composition.

- [ ] **Step 4: Restyle Solarized Dark**

Make it a flat terminal/documentation workspace: minimal chrome, low radius, dense rows, explicit rules, underline actions, flat dialogs, and no decorative card lift. Keep all contrast-corrected Solarized accents.

- [ ] **Step 5: Bump versions and update READMEs**

Set Estate Slate Dark to `1.1.0` and Solarized Dark to `1.2.0`. Document the independent identities and retained dark-token coverage.

- [ ] **Step 6: Run checks**

Run: `scripts/theme.sh check estate-slate-dark && scripts/theme.sh check solarized-dark && python3 -m unittest tests.test_new_theme_packages -v`

Expected: no error-level uniqueness issues; dark-policy and package tests PASS.

- [ ] **Step 7: Commit**

```bash
git add sample-themes/estate-slate-dark sample-themes/solarized-dark tests/test_new_theme_packages.py
git commit -m "feat: separate the legacy dark theme identities"
```

### Task 8: Refine Carbon Volt and Velvet Signal

**Files:**
- Modify: `sample-themes/carbon-volt/theme.json`
- Modify: `sample-themes/carbon-volt/css/tokens.css`
- Modify: `sample-themes/carbon-volt/css/apex/{shell,regions,buttons,forms,reports,dialogs,misc}.css`
- Modify: `sample-themes/carbon-volt/README.md`
- Modify: `sample-themes/velvet-signal/theme.json`
- Modify: `sample-themes/velvet-signal/css/tokens.css`
- Modify: `sample-themes/velvet-signal/css/apex/{shell,regions,buttons,forms,reports,dialogs,misc}.css`
- Modify: `sample-themes/velvet-signal/README.md`
- Modify: `tests/test_new_theme_packages.py`

**Interfaces:**
- Consumes: dark-theme coverage tests and recipes.
- Produces: Carbon Volt `1.1.0` and Velvet Signal `1.1.0` without the current Solarized-derived shell structure/comments.

- [ ] **Step 1: Add source-identity regression tests**

Assert neither theme contains `VS Code`, Solarized palette names, or copied Solarized commentary. Assert Carbon Volt includes segmented rail/hard module/outline-state markers; assert Velvet Signal includes pill navigation/sculpted layered surface/smooth lift markers. Retain the four declared font faces and license checks.

- [ ] **Step 2: Run the tests and confirm copied commentary is caught**

Run: `python3 -m unittest tests.test_new_theme_packages -v`

Expected: FAIL because current shell comments still identify a VS Code-derived structure.

- [ ] **Step 3: Restyle Carbon Volt**

Use square segmented rail navigation, hard module boundaries, compact telemetry density, cyan secondary indicators, acid-lime primary state outlines, and short axis-aligned shift motion. Avoid terminal/editor pane composition.

- [ ] **Step 4: Restyle Velvet Signal**

Use pill navigation, generous spacing, nested aubergine surfaces, strong radius progression, fuchsia/violet signal layers, soft fields, and smooth lift. Avoid Carbon Volt's hard edges and compact density.

- [ ] **Step 5: Bump versions and update READMEs**

Set both manifests to `1.1.0`; keep pinned WOFF2 provenance unchanged.

- [ ] **Step 6: Run checks and commit**

Run: `scripts/theme.sh check carbon-volt && scripts/theme.sh check velvet-signal && python3 -m unittest tests.test_new_theme_packages -v`

Expected: PASS with no error-level uniqueness issues.

```bash
git add sample-themes/carbon-volt sample-themes/velvet-signal tests/test_new_theme_packages.py
git commit -m "feat: sharpen carbon volt and velvet signal identities"
```

### Task 9: Refine Cobalt Press and Citrus Pop

**Files:**
- Modify: `sample-themes/cobalt-press/theme.json`
- Modify: `sample-themes/cobalt-press/css/tokens.css`
- Modify: `sample-themes/cobalt-press/css/apex/{shell,regions,buttons,forms,reports,dialogs,misc}.css`
- Modify: `sample-themes/cobalt-press/README.md`
- Modify: `sample-themes/citrus-pop/theme.json`
- Modify: `sample-themes/citrus-pop/css/tokens.css`
- Modify: `sample-themes/citrus-pop/css/apex/{shell,regions,buttons,forms,reports,dialogs,misc}.css`
- Modify: `sample-themes/citrus-pop/README.md`
- Modify: `tests/test_new_theme_packages.py`

**Interfaces:**
- Consumes: light-theme identity recipes and AA contrast checks.
- Produces: Cobalt Press `1.1.0` and Citrus Pop `1.1.0` without Estate Slate-derived shell duplication.

- [ ] **Step 1: Add source-identity tests**

Assert neither theme contains `dark command slate chrome with amber branding`. Assert Cobalt Press has editorial rules, offset sheets/shadows, cobalt underline directives, and vermilion marks. Assert Citrus Pop has pill navigation, buoyant card lift, teal structure, and tangerine action states. Preserve Citrus hot-button AA test and all declared font-face checks.

- [ ] **Step 2: Run tests and confirm duplicated commentary is caught**

Run: `python3 -m unittest tests.test_new_theme_packages -v`

Expected: FAIL because both current shells use the inherited Estate Slate comment/structure.

- [ ] **Step 3: Restyle Cobalt Press**

Use warm paper, black editorial chrome/rules, offset white sheets, square-to-small radii, cobalt directive underlines, vermilion annotations, outlined inputs, and deliberate shift motion.

- [ ] **Step 4: Restyle Citrus Pop**

Use pale aqua canvas, deep teal chrome, rounded pill navigation, buoyant cards, soft fields, tangerine actions with the audited hot-button text token, and playful but reduced-motion-safe lift.

- [ ] **Step 5: Bump versions and update READMEs**

Set both manifests to `1.1.0`; keep pinned WOFF2 provenance unchanged.

- [ ] **Step 6: Run checks and commit**

Run: `scripts/theme.sh check cobalt-press && scripts/theme.sh check citrus-pop && python3 -m unittest tests.test_new_theme_packages -v`

Expected: PASS with no error-level uniqueness issues and Citrus hot-action contrast at least `4.5:1`.

```bash
git add sample-themes/cobalt-press sample-themes/citrus-pop tests/test_new_theme_packages.py
git commit -m "feat: separate cobalt press and citrus pop identities"
```

### Task 10: Regenerate static files, packages, and catalog

**Files:**
- Modify: `docs/generated/theme-uniqueness-report.md`
- Modify: generated blocks in `README.md`, `sample-themes/README.md`, `docs/DESIGN_SYSTEM.md`, `tests/live/RELEASE-MATRIX.md`
- Modify: `applications/ut/shared-components/static-files/*` through `scripts/sync-static.sh`

**Interfaces:**
- Consumes: all eight upgraded sources.
- Produces: current static bundle, preliminary one-theme ZIP verification, and updated catalog/report. Runtime-derived covers are deliberately deferred until app 102 serves the new CSS in Task 11.

- [ ] **Step 1: Regenerate the uniqueness report and assert no errors**

Run: `python3 -m lib.theme_factory.uniqueness_report --repo-root . --output docs/generated/theme-uniqueness-report.md && ! rg '\| error \|' docs/generated/theme-uniqueness-report.md`

Expected: 28 pair rows and no error severity.

- [ ] **Step 2: Run author and package checks for every theme**

Run: `for theme in sample-themes/*; do name="$(basename "$theme")"; scripts/theme.sh check "$name"; scripts/package-theme.sh "$name"; done`

Expected: every check/package command exits `0`; each archive contains exactly one manifest, scoped CSS bundle, declared fonts/license when applicable, README, and cover.

- [ ] **Step 3: Synchronize static source and validate APEXLang**

Run: `scripts/sync-static.sh && scripts/apex-validate.sh`

Expected: static-files APEXLang contains the new package versions and CSS; validation exits `0`.

- [ ] **Step 4: Update generated catalogs**

Run: `scripts/theme.sh catalog --write && scripts/theme.sh catalog --check`

Expected: updated versions/statuses and no drift on the check run.

- [ ] **Step 5: Run complete offline/package suites**

Run: `tests/run-offline.sh && tests/run-package-offline.sh`

Expected: both exit `0`.

- [ ] **Step 6: Commit generated artifacts**

```bash
git add applications/ut/shared-components/static-files README.md sample-themes/README.md docs/DESIGN_SYSTEM.md docs/generated/theme-uniqueness-report.md tests/live/RELEASE-MATRIX.md
git commit -m "build: regenerate unique theme packages and catalog"
```

### Task 11: Import and verify runtime behavior when authorized

**Files:**
- Modify: `sample-themes/*/preview/cover.jpg`
- Modify: `applications/ut/shared-components/static-files/*` after cover capture
- Modify: `.agents/evaluations/runtime/<date>-release-<theme>/**`
- Modify: `tests/live/RELEASE-MATRIX.md`
- Modify on a failed runtime assertion: affected `sample-themes/<name>/css/**`

**Interfaces:**
- Consumes: clean source commit, built package SHA-256 values, SQLcl `docker-demo`, and the already approved project Chrome daemon.
- Produces: Layer C/D evidence bound to each theme package and source commit.

- [ ] **Step 1: Confirm explicit import authorization and a clean source identity**

Run: `git status --short && git rev-parse HEAD`

Expected: clean worktree and a 40-character commit. If the user has not explicitly authorized importing app 102 for this execution, stop before the next step.

- [ ] **Step 2: Import app 102 through the existing workflow**

Run: `scripts/apex-import.sh --yes`

Expected: SQLcl import succeeds against saved connection `docker-demo` with no validation errors.

- [ ] **Step 3: Use only the project daemon**

Run: `python3 tools/chrome_devtools_client.py list_pages '{}'`

Expected: the user's approved Chrome session responds. If unavailable, start exactly one `python3 tools/chrome_mcp_daemon.py` instance and wait for user approval; never invoke a direct Chrome MCP server.

- [ ] **Step 4: Inspect app 102 and correct runtime defects**

Use page 406 Theme Lab at `http://localhost:8181/ords/r/demo/ut/theme-lab` and page 500 at `http://localhost:8181/ords/r/demo/ut/getting-started`. For each theme, verify shell, regions, cards, forms, validation, IR/IG, reports, calendar, JET charts, menus, date picker, Popup LOV, modal/dialog/drawer, hover, focus, selected, disabled, and error states at `1440`, `1024`, `768`, and `375` pixels. Check Arabic/Latin samples, every declared weight, WOFF2 MIME responses, unchanged Font APEX, keyboard switching, persistence after reload, zero package-caused AA failures, zero new console errors/failed requests, and no horizontal overflow or clipped actions.

Expected: every matrix row passes. If a row fails, return to the owning theme task, add a regression test, fix the source, run `scripts/sync-static.sh && scripts/apex-import.sh --yes`, and repeat this step before proceeding.

- [ ] **Step 5: Capture the eight runtime-derived covers**

Run: `for theme in sample-themes/*; do name="$(basename "$theme")"; scripts/theme.sh cover "$name" --output "sample-themes/$name/preview/cover.jpg" --apply --overwrite; done`

Expected: eight JPEG covers, each exactly 960 pixels wide, with the upgraded runtime styling and no browser/request errors.

- [ ] **Step 6: Synchronize covers, verify, and create the clean evidence source commit**

Run: `scripts/sync-static.sh && scripts/apex-validate.sh && tests/run-offline.sh && tests/run-package-offline.sh`

Expected: all commands exit `0`.

```bash
git add sample-themes/*/preview/cover.jpg applications/ut/shared-components/static-files
git commit -m "docs: refresh unique theme gallery covers"
```

- [ ] **Step 7: Build final packages from the clean source commit**

Run: `for theme in sample-themes/*; do scripts/package-theme.sh "$(basename "$theme")"; done && git status --short`

Expected: eight packages are rebuilt with source identity equal to `git rev-parse HEAD`; the worktree remains clean because `dist/` is ignored.

- [ ] **Step 8: Run the A–D batch matrices**

Run the seven non-Linen candidates with Linen as the fixed coexistence package:

```bash
scripts/theme.sh release-batch \
  --themes estate-slate,estate-slate-dark,solarized-dark,carbon-volt,velvet-signal,cobalt-press,citrus-pop \
  --secondary dist/linen/linen-1.1.0.zip \
  --connection docker-demo --workspace DEMO \
  --minimal-id 9010 --business-id 9011 \
  --minimal-url http://localhost:8181/ords/r/demo/tf-consumer-minimal-9010/home \
  --business-url http://localhost:8181/ords/r/demo/tf-consumer-business-9011/home \
  --widths 1440,1024,768,375 --resume --apply
```

Then run Linen with Solarized Dark as the fixed coexistence package:

```bash
scripts/theme.sh release-batch \
  --themes linen \
  --secondary dist/solarized-dark/solarized-dark-1.2.0.zip \
  --connection docker-demo --workspace DEMO \
  --minimal-id 9010 --business-id 9011 \
  --minimal-url http://localhost:8181/ords/r/demo/tf-consumer-minimal-9010/home \
  --business-url http://localhost:8181/ords/r/demo/tf-consumer-business-9011/home \
  --widths 1440,1024,768,375 --resume --apply
```

Expected: Layer C proves install/reinstall/coexistence/switcher enable-disable/uninstall/restore/preserve-unrelated. Layer D produces every required row and no missing checkpoint.

- [ ] **Step 9: Attribute accessibility failures**

For any failure, repeat on bare Iris at the same page/viewport. Record package-caused failures as blocking; record identical bare-Iris failures as inherited with A/B evidence. Do not mark a theme `VERIFIED` while a package-caused failure remains.

- [ ] **Step 10: Rebuild final A–D reports and catalog**

Run: `for theme in linen estate-slate estate-slate-dark solarized-dark carbon-volt velvet-signal cobalt-press citrus-pop; do scripts/release-check.sh "$theme"; done`

Expected: each report is `VERIFIED` only when A–D are current and PASS.

Run: `scripts/theme.sh catalog --write && scripts/theme.sh catalog --check`

Expected: generated release tables show A–D only and every fully passing theme as `VERIFIED`.

- [ ] **Step 11: Commit bound evidence and release matrix**

```bash
git add .agents/evaluations/runtime README.md sample-themes/README.md docs/DESIGN_SYSTEM.md tests/live/RELEASE-MATRIX.md
git commit -m "test: bind runtime evidence for unique theme release"
```

### Task 12: Final review and handoff

**Files:**
- No planned source changes; fixes discovered here return to the owning task.

**Interfaces:**
- Consumes: completed source, packages, reports, and runtime evidence.
- Produces: reviewable proof that the design spec is satisfied.

- [ ] **Step 1: Run the full verification set from a clean checkout**

Run: `tests/run-offline.sh && tests/run-package-offline.sh && scripts/theme.sh catalog --check && python3 -m lib.theme_factory.uniqueness_report --repo-root . --output docs/generated/theme-uniqueness-report.md --check`

Expected: all commands exit `0`.

- [ ] **Step 2: Verify public identities and versions**

Run: `for f in sample-themes/*/theme.json; do jq -r '[.name,.class,.version] | @tsv' "$f"; done`

Expected: eight stable names/classes; versions are `1.1.0` except `solarized-dark` at `1.2.0`.

- [ ] **Step 3: Prove Linen remains the default**

Run: `rg -n "linen|app-theme-linen" applications/ut static-files/js | head -n 40`

Expected: application default references still resolve to Linen; no other theme is promoted to default.

- [ ] **Step 4: Inspect scope and external URL policy**

Run: `scripts/check-sample-themes-coverage.sh && ! rg -n 'https?://.*\.(woff2?|ttf|otf)' sample-themes/*/css sample-themes/*/theme.json`

Expected: coverage check passes and no external runtime font URL is found.

- [ ] **Step 5: Review the final diff**

Run: `git status --short && git diff --stat HEAD~1..HEAD && git log --oneline --decorate -12`

Expected: no unrelated/untracked package changes, no historical evidence deletion, and task-sized commits corresponding to this plan.

- [ ] **Step 6: Request code/design review**

Use `superpowers:requesting-code-review` and `apex-design-review`. Address findings by returning to the task that owns the affected interface, rerunning that task's focused tests, then rerunning Step 1.
