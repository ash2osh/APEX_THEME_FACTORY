# Release Gates and Theme Uniqueness Design

**Date:** 2026-09-20
**Status:** Approved for implementation planning
**Scope:** Theme release evidence, agent compatibility, neutral theme generation, and the visual differentiation of all eight shipped themes.

## 1. Outcome

The factory will make a theme release decision from evidence about the theme itself:

- Layer A — repository source
- Layer B — package artifact
- Layer C — database installation and lifecycle
- Layer D — browser runtime, responsive behavior, accessibility, fonts, and native APEX behavior

Agent compatibility will remain valuable, but it will become a repository-level compatibility signal rather than Layer E of every theme release. A theme can therefore become `VERIFIED` when A–D pass even if an external agent CLI is unavailable, out of quota, or awaiting authentication.

Theme production will begin from a neutral Universal Theme/Iris adapter, never from Linen or another theme's visual source. Every shipped theme will receive a documented identity and must differ from every other theme on multiple measurable axes. Shared selectors, accessibility protections, frozen Iris-token coverage, and packaging conventions remain common infrastructure; visual decisions do not.

## 2. Non-goals

- Do not remove `AGENTS.md`, skills, agent smoke tests, or compatibility documentation.
- Do not weaken Layers A–D or treat offline checks as runtime proof.
- Do not replace Universal Theme, create alternate theme styles, use Theme Roller, or introduce custom replacement markup.
- Do not rename existing themes or change the public `app-theme-<name>` classes.
- Do not change Linen as the application default.
- Do not add external runtime font URLs.
- Do not require every theme to have a different font family. Typography is one identity axis; overall identity must remain unique even when a licensed family is shared.

## 3. Architecture

### 3.1 Theme release and agent compatibility are separate products

`lib/theme_factory/release.py` owns only theme-bound A–D evidence. It accepts historical evidence manifests containing Layer E for backward compatibility, but Layer E cannot improve or degrade the theme verdict and is not rendered as a current release column.

`lib/theme_factory/agent_compatibility.py` owns project-level agent compatibility. It validates the three runtime smokes and the repository instruction scenarios that test agent behavior. Its status is one of `PASS`, `FAIL`, or `UNVERIFIED` and is bound to the instruction surface (`AGENTS.md`, `.agents/rules/`, and `.agents/skills/`), not to any theme archive.

The compatibility suite runs when one of those instruction surfaces changes, when a maintainer explicitly requests it, or on a scheduled compatibility job. It does not run once per theme.

Scenario 11, dark-package coverage, is not agent-independent. Its product assertions move into Layer D runtime coverage and the package policy tests. The agent-evaluation scenario remains useful as a training/evaluation record, but it is not required by the compatibility summary or theme verdict.

Historical `agent_behavior_matrix.json` and Layer E checks remain immutable evidence. Migration does not delete or rewrite them.

### 3.2 Neutral generation is not Linen inheritance

The neutral scaffold contains only:

- the required package directory and manifest structure;
- scoped CSS module imports;
- Universal Theme/Iris selector adapters;
- required accessibility, focus, RTL, Font APEX, and frozen-token safety hooks;
- placeholders represented by recipe variables and named component profiles.

It contains no Linen palette, Linen geometry, Linen spacing, Linen component profile selection, or Linen-specific selectors. The generator does not expose a `--from-theme` or copy-existing-theme path.

Generated modules carry `/* @theme-factory-generated */` and a profile marker. Handwritten theme modules are preserved. Regeneration may update generated modules only.

### 3.3 Recipe schema version 2

All eight themes receive `theme.recipe.json` files using schema version 2. Version 2 retains the existing identity, palette, font provenance, geometry, focus, and component fields and adds three explicit identity groups:

```json
{
  "rhythm": {
    "density": "compact | balanced | spacious",
    "spacing": "technical | editorial | soft | playful",
    "typeScale": "compact | balanced | editorial | display"
  },
  "interaction": {
    "hover": "none | lift | shift | glow",
    "selected": "fill | rail | underline | outline",
    "motion": "none | precise | smooth | buoyant"
  },
  "responsive": {
    "strategy": "compress | reflow | stack",
    "compactControlsAt": 768
  }
}
```

`compactControlsAt` accepts only `0`, `375`, `768`, or `1024`. These are the supported verification widths and prevent recipes from inventing arbitrary breakpoint systems.

Component profiles remain explicit for navigation, cards, buttons, forms, reports, and dialogs. New profile values may be added only when they represent a reusable visual pattern and ship with a focused template and test.

### 3.4 Identity matrix

The following matrix is the visual contract. Palette anchors and existing licensed fonts remain intact unless a contrast correction is required.

| Theme | Identity | Density / rhythm | Navigation | Cards / regions | Controls | Data / dialogs | Interaction |
|---|---|---|---|---|---|---|---|
| `linen` | Quiet editorial atelier; warm canvas and restrained teal thread | balanced / editorial | minimal, text-led | flat paper panels with hairline separators | calm rounded controls, comfortable fields | spacious reports, flat dialogs | underline selection, precise motion |
| `estate-slate` | Executive property operations; formal slate and champagne accents | balanced / technical | compact top chrome with section markers | crisp flat portfolio panels and metric strips | restrained rounded buttons, outlined fields | ruled financial tables, layered dialogs | rail selection, precise motion |
| `estate-slate-dark` | Nocturnal geospatial intelligence; luminous amber/emerald telemetry | compact / technical | dense vertical rail | layered monitoring panels with map-like inset frames | square controls and dense fields | spacious scan tables, offset detail dialogs | glow selection, precise motion |
| `solarized-dark` | Terminal/documentation workspace; low-chroma analytical surfaces | compact / technical | minimal command navigation | flat, low-elevation panes | underline actions and dense fields | strongly ruled reports, flat dialogs | underline selection, no decorative motion |
| `carbon-volt` | Industrial telemetry; graphite, acid lime, cyan, square geometry | compact / technical | segmented rail | hard-edged modular cards | square controls and dense fields | ruled telemetry grids, offset dialogs | outline selection, shift motion |
| `velvet-signal` | Expressive premium signal desk; aubergine depth and generous space | spacious / soft | pill navigation | layered sculpted surfaces | rounded buttons and soft fields | spacious reports, layered dialogs | fill selection, smooth lift |
| `cobalt-press` | Editorial press room; warm paper, rules, cobalt directives, vermilion marks | balanced / editorial | editorial tabs/rules | offset white sheets | underline actions and outlined fields | ruled tables, offset dialogs | underline selection, precise shift |
| `citrus-pop` | Friendly operations workspace; aqua, teal, tangerine, playful energy | spacious / playful | pill navigation | buoyant cards | pill actions and soft fields | spacious reports, layered dialogs | fill selection, buoyant lift |

The matrix deliberately prevents `estate-slate-dark` from being a dark recolor of `estate-slate`, and prevents `carbon-volt` from inheriting Solarized Dark's terminal layout.

### 3.5 Uniqueness gate

The fingerprint becomes recipe-aware and measures five independent dimensions:

1. normalized CSS structure by module;
2. component profile vector;
3. geometry and rhythm;
4. typography family and type-scale treatment;
5. palette distance and interaction/responsive behavior.

For each candidate/nearest-theme pair:

- `STRUCTURAL_RECOLOR` is an error at CSS similarity `>= 0.98` with five or more matching component profiles;
- `PROFILE_COLLISION` is an error at CSS similarity `>= 0.92` with five or more matching component profiles;
- `IDENTITY_COLLISION` is an error when geometry/rhythm, typography treatment, interaction, and responsive strategy all match and average palette Delta E is below `20`;
- `STRUCTURAL_SIMILARITY` is a warning at CSS similarity `>= 0.85`;
- warnings do not fail author checks, but every warning must appear in the generated uniqueness report for review.

Passing the automated gate is necessary, not sufficient. Runtime visual review must confirm that navigation, cards, forms, data surfaces, dialogs, focus, selected, error, disabled, and responsive states express the matrix.

### 3.6 Version and compatibility policy

Each materially restyled theme receives a minor version bump:

- themes at `1.0.0` become `1.1.0`;
- `solarized-dark` at `1.1.0` becomes `1.2.0`.

Names, classes, package structure, application switcher values, and font file paths remain stable. Consumer upgrades therefore replace presentation without requiring new application markup or JavaScript APIs.

## 4. Verification contract

### 4.1 Offline and package verification

Every theme must pass:

- recipe schema and contrast validation;
- scoped-selector and literal-color policy checks;
- font signature/reference/license validation;
- complete package contents and offline behavior;
- no error-level uniqueness findings against all discovered themes;
- generated uniqueness report containing every pair and warning;
- complete offline and package test suites.

### 4.2 Runtime verification

After an explicit user request to import app 102, use `scripts/sync-static.sh`, validate the APEXLang source, import through `docker-demo`, and use only the approved project Chrome daemon.

Each theme is checked at `1440`, `1024`, `768`, and `375` pixels on the consolidated Theme Lab and required consumer pages. Evidence covers switcher keyboard behavior and persistence; shell; regions; cards; forms; validation; IR/IG; standard reports; calendars; JET charts; menus; date picker; Popup LOV; modal/dialog/drawer; hover/focus/selected/disabled/error states; Arabic and Latin samples; declared WOFF2 faces; unchanged Font APEX; console and network cleanliness; overflow and clipped actions.

Only package-caused WCAG AA failures block the theme. Bare-Iris A/B attribution remains required for inherited Universal Theme failures.

### 4.3 Release reporting

Theme reports and the release matrix render A, B, C, D, and the theme verdict. Agent compatibility is rendered once in `docs/AGENT_COMPATIBILITY.md` and may be summarized separately in the README. It is never repeated as a theme column.

## 5. Rollout order

1. Decouple Layer E while preserving legacy evidence parsing.
2. Add recipe v2 and the stronger fingerprint/reporting model.
3. Migrate all eight themes to recipes without changing their visual source yet.
4. Upgrade the four legacy themes: Linen, Estate Slate, Estate Slate Dark, Solarized Dark.
5. Refine the four bilingual themes: Carbon Volt, Velvet Signal, Cobalt Press, Citrus Pop.
6. Regenerate static files, packages, covers, catalog, and A–D evidence.
7. Run project-level agent compatibility only if instruction surfaces changed or the user explicitly requests it.

## 6. Acceptance criteria

- A theme with A–D `PASS` is `VERIFIED` regardless of agent CLI availability.
- A Layer E `FAIL` or `UNVERIFIED` in historical evidence cannot change a theme verdict.
- Agent compatibility still reports current instruction-bound status independently.
- A newly scaffolded theme contains no bytes copied from Linen or another theme's handwritten CSS.
- Every shipped theme has a schema-v2 recipe and a unique identity matrix row.
- No pair of shipped themes triggers an error-level uniqueness finding.
- All warning-level pairs are visible in a generated report and explicitly reviewed.
- All eight themes pass offline/package checks and the four-width runtime matrix.
- Linen remains the default and all existing switcher names/classes remain unchanged.
