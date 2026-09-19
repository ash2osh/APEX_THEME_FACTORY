# Theme Production Accelerator Design

**Status:** Approved direction from the 2026-09-19 conversation; implementation has not started.

## Objective

Reduce the time, repeated editing, and agent-token cost required to create a distinctive Oracle APEX theme
without weakening the current package, accessibility, offline, consumer-installation, browser, or evidence
requirements.

The target workflow is:

```text
recipe -> scaffold -> customize -> fast check -> Theme Lab -> release evidence
```

The project remains an APEX 26.1.4 / Universal Theme 42 / Iris factory. The accelerator automates authoring
and orchestration; it does not introduce a second rendering system, Theme Roller output, external runtime
assets, or custom replacements for native APEX components.

## Success Measures

- Scaffold a complete source package in under 10 seconds on the development machine.
- Run package-specific offline checks in under 30 seconds when their inputs are unchanged or locally cached.
- Reach the first imported app-102 preview in under 2 minutes, excluding SQLcl or database outages.
- Reduce agent input/output tokens for a comparable new theme by at least 50 percent against the four-theme
  2026-09-19 baseline.
- Generate manifests, standard CSS structure, font declarations, provenance, catalog rows, and release-matrix
  rows without manual duplication.
- Preserve every existing release gate and the rule that only complete Layers A-E evidence earns `VERIFIED`.
- Reject unsafe scoping, unsupported font weights, inaccessible core color pairs, missing licenses, broken
  packages, and structural recolors before expensive browser work.

Benchmarks are directional until the implementation records a baseline and three representative trial runs.

## Three Verification Lanes

### Author lane

Runs without a database or browser. It validates one theme and emits compact, failure-oriented output.

```text
theme new -> recipe/schema -> generated source -> CSS/font/package preflight -> uniqueness report
```

The author lane may cache successful checks by content digest. It must invalidate a cached result whenever a
consumed source file, validator version, or referenced shared token file changes.

### Candidate lane

Runs against app 102 only when explicitly requested. It synchronizes static files, validates APEXLang, may
import through SQLcl with the existing confirmation rules, and inspects the Theme Lab at 1440, 1024, 768,
and 375 px through the project Chrome daemon.

The candidate lane is an iteration aid. Passing it never produces `VERIFIED`.

### Release lane

Builds deterministic packages from a clean source commit and runs the existing release contract. Layer C
consumer lifecycles, Layer D browser matrices, Layer E agent evidence, source/package binding, and the final
release report remain authoritative. Resume and batching may skip work only when existing evidence is
schema-valid and bound to the exact source commit, package SHA-256, APEX version, browser version, consumer,
page, viewport, and scenario.

## Command-Line Interface

`scripts/theme.sh` is the human entry point and delegates to `python3 -m lib.theme_factory.cli`.

```text
scripts/theme.sh new NAME --recipe FILE
scripts/theme.sh new NAME --title TITLE --tagline TEXT --mode light|dark
scripts/theme.sh font add NAME --metadata-url URL --source-revision SHA --weights 400,500,600,700
scripts/theme.sh check NAME [--json] [--no-cache]
scripts/theme.sh dev NAME [--sync] [--validate] [--import] [--open]
scripts/theme.sh cover NAME --output sample-themes/NAME/preview/cover.jpg
scripts/theme.sh catalog --check|--write
scripts/theme.sh inspect-iris --check|--write
scripts/theme.sh release NAME [existing release target arguments] [--resume]
```

Commands that mutate APEX or overwrite a curated cover retain explicit `--apply` or overwrite confirmation.
Read-only and source-generation commands are deterministic and non-interactive when every required argument
is supplied.

Machine-readable mode writes one JSON document to stdout. Human mode prints one summary line per gate and
detailed diagnostics only for failures or explicit `--verbose` requests.

## Theme Recipe

New themes use source-only `sample-themes/<name>/theme.recipe.json`. Existing themes remain valid without a
recipe. The recipe is not copied into a distributable ZIP and is not required at runtime.

Schema version 1 contains:

```json
{
  "schemaVersion": 1,
  "identity": {
    "name": "example-theme",
    "title": "Example Theme",
    "tagline": "A concise catalog description.",
    "direction": "A distinctive visual direction.",
    "mode": "dark",
    "keywords": ["technical", "dense"]
  },
  "palette": {
    "page": "#0A0D0B",
    "card": "#151A16",
    "chrome": "#0F1310",
    "textPrimary": "#F2F7F0",
    "textSecondary": "#A8B5AB",
    "accent": "#B8FF3D",
    "accentAlt": "#38E8FF",
    "onAccent": "#0A0D0B",
    "danger": "#FF6673"
  },
  "typography": {
    "bodyFamily": "Noto Kufi Arabic",
    "headingFamily": "body",
    "fallback": ["system-ui", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
    "weights": [400, 500, 600, 700]
  },
  "geometry": {
    "radiusSmall": "0px",
    "radiusMedium": "2px",
    "radiusLarge": "4px",
    "controlHeight": "2.125rem",
    "borderStyle": "technical",
    "shadowStyle": "offset"
  },
  "focus": {"color": "#38E8FF", "width": "2px", "offset": "2px"},
  "components": {
    "navigation": "rail",
    "cards": "offset",
    "buttons": "square",
    "forms": "dense",
    "reports": "ruled",
    "dialogs": "offset"
  }
}
```

The recipe generates the manifest, a scoped token foundation, selected component starter fragments, and
documentation metadata. Component CSS remains editable source. Regeneration is ownership-aware: generated
files or marked generated sections can be replaced; handwritten sections are never silently overwritten.

## Neutral Starter and Component Recipes

The factory owns a neutral starter under `theme-templates/neutral/`. It is not Linen and carries no branded
palette. All selectors contain the requested theme scope from creation time; global or placeholder scopes are
never emitted.

Reusable component recipes are template-time fragments, not shared runtime CSS. A generated theme remains
portable and independent. Profiles provide starting geometry and states for shell, regions, buttons, forms,
reports, and dialogs. They intentionally do not choose final brand colors or complete the designer's work.

## Font Pipeline

The font command accepts pinned upstream metadata and a required source revision. It operates in a temporary
virtual environment using pinned fontTools/Brotli versions, validates official metadata and OFL licensing,
reports the variable source's real axes and named instances, statically instantiates only supported requested
weights, validates `wOF2` signatures and Arabic/Latin cmap coverage, and writes provenance into the package
README and recipe.

No Python environment, source TTF, downloaded metadata, cache, or temporary file is committed. Runtime font
URLs remain package-local. Font APEX is never included in body or heading font rules.

## Fast Quality Checks

The author gate combines existing validators with new checks:

- strict manifest and recipe schema validation;
- source-module and generated-file completeness;
- CSS scope, literal-color, external-URL, and `!important` policy;
- font signatures, face references, supported weights, license, provenance, Arabic/Latin coverage;
- static WCAG contrast for declared primary, secondary, accent, danger, and focus pairs;
- deterministic bundle and archive-content validation without requiring a clean commit;
- uniqueness analysis against every discoverable theme;
- generated catalog and Iris-inventory drift checks.

Static contrast is a preflight, not a substitute for runtime compositing, SVG/JET, focus, hover, selected,
disabled, error, menu, picker, grid, dialog, and native APEX state verification.

## Uniqueness Analysis

Each theme produces a fingerprint from recipe metadata when available and from manifest/CSS extraction for
legacy packages. It includes color distances, typography, radius/control-height values, shadow/border
families, component profile choices, navigation shape, and normalized component-CSS structure.

An error is raised when component CSS is structurally identical after replacing theme names and color values,
or when palette, typography, geometry, and component signatures collectively match an existing theme closely
enough to be a recolor. Individual similarities are warnings. The report explains the nearest existing theme
and the dimensions that caused the result.

## Theme Lab

App 102 gains public page 406, `THEME-LAB`. It uses native Universal Theme components and stable Static IDs.
It contains bilingual typography specimens, palette/surface specimens, buttons and states, native form items
and validation examples, cards and regions, IR/IG/classic report specimens, a calendar, JET chart, menu/date
picker/Popup LOV launchers, and modal/drawer launchers. Where a heavyweight component is clearer on its
existing reference page, the Lab contains both a compact native specimen and a direct reference-page link.

Page-specific layout rules live in `static-files/css/pages/theme-lab.css`, scoped by
`html.page-406`. Theme-specific appearance continues to come exclusively from each package.

## Cover Capture and Visual Comparison

Cover capture always uses the existing project Chrome daemon, a private background tab, per-tab viewport
emulation, DOM-only class swapping that does not modify shared localStorage, hidden developer toolbar, and
page 500 at 1280x700. It writes a 960 px JPEG only after validating the active theme, zero new console errors,
zero failed requests, and expected dimensions. Existing covers require `--apply --overwrite`.

Candidate comparison stores scratch screenshots outside Git and computes a deterministic pixel-difference
summary. A threshold breach requests visual inspection; it never automatically approves a design.

## Discovery, Catalog, and Documentation

One `discover_themes()` API replaces hard-coded theme lists. It returns only directories whose strict
manifest validates and sorts them by manifest name. Invalid candidate directories are reported, not silently
ignored.

Generated Markdown sections in the main README, sample catalog, design-system theme table, and release matrix
are derived from manifests plus bound evidence. Handwritten prose stays outside generated markers. A theme is
shown as `VERIFIED` only when the release gate validates all required evidence for its current package.

## Iris Drift Inspector

The inspector parses all four pinned APEX/UT CSS references, records literal root tokens, variable chains,
element-scoped declarations, widget fallbacks, and paired text/background atoms, and cross-checks its parsed
inventory with an independent token-name scan. A missing common root such as `--ut-palette-primary` is an
error. Updating the APEX reference intentionally regenerates the inventory and a human-readable diff report.

## Evidence, Batching, and CI

- Fast results are cached locally under `.theme-factory/cache/` and never committed.
- Release resume trusts only schema-valid, digest-bound artifacts.
- Layer C exports each consumer baseline once per batch, restores it between candidates, and tests each theme
  with a fixed valid secondary package for coexistence. Reciprocal pairs are not rerun unless package-order
  behavior differs.
- Layer D installs the candidate set once, reuses one daemon-owned tab, checkpoints every row, and still
  records independent evidence for each theme/consumer/viewport.
- Raw JSON is the evidence truth. Markdown status tables are generated from it. Obsolete evidence is reported;
  deletion requires an explicit apply flag.
- Pull requests run the common offline suite once and theme-specific checks for changed packages. Nightly CI
  builds and verifies every package. Live database/browser release work remains explicit unless a secured,
  self-hosted runner provides SQLcl, APEX, and the approved Chrome daemon.

## APEXLang Maintainability

The existing `lib/theme_factory/apexlang.py` public imports remain compatible while its parser/model,
inspection/state, runtime-rendering, and patch/apply responsibilities move into focused modules. The split is
behavior-preserving and occurs after accelerator features are covered by tests, so it cannot become a hidden
rewrite of installation behavior.

## Compatibility and Non-Goals

- Existing themes without recipes remain buildable, installable, and verifiable.
- Existing package ZIP layout and runtime APIs remain compatible.
- Linen stays the application default.
- No external runtime font or CSS URLs.
- No Theme Roller output or alternate theme style.
- No new JavaScript framework or custom APEX component replacement.
- No automatic `VERIFIED` verdict from author or candidate checks.
- No silent APEX import, cover overwrite, evidence deletion, or mutation of the user's shared browser state.

## Delivery Strategy

Each implementation phase must ship working software independently:

1. discovery and documentation correctness;
2. recipe, neutral scaffold, and component starters;
3. font and fast-quality pipelines;
4. unified CLI and developer lane;
5. Theme Lab, cover capture, and visual comparison;
6. resumable/batched release evidence and CI tiers;
7. Iris drift inspection and APEXLang maintainability split;
8. benchmark, documentation, and full verification.

All source-changing phases must land before final package builds and evidence capture. After the final source
commit: build packages, capture Layers C/D/E without touching source, generate reports/catalogs, and commit
evidence plus Markdown only.
