---
name: apex-design-system
description: Use when translating design values (colors, radius, spacing, shadows, fonts) from Figma/Stitch/screenshots into this project, or when about to write a literal CSS value — to map it onto Iris and --app-* tokens first
---

# apex-design-system

Reference: `docs/DESIGN_SYSTEM.md` (token tables), `.agents/knowledge/iris-ut-tokens.md` (all 167 live `--ut-*` values).

## Core principle
Iris is the token source. `--app-*` aliases Iris; components use `--app-*`. Literals are the last resort.

## Mapping procedure
1. Extract the design value (e.g. radius 8px, primary #0A66C2, shadow y=12 blur=24).
2. Find the nearest Iris token: radius `.125/.25/.5rem`, shadows `--ut-shadow-sm/md/lg`, palette `--ut-palette-*`, surfaces `--ut-body-*`/`--ut-component-*`.
3. If an `--app-*` alias exists → use it. If Iris has it but no alias → add the alias to `static-files/css/foundation/tokens.css` and a row to `docs/DESIGN_SYSTEM.md`.
4. If neither exists and the value is reusable → new `--app-*` token with a design-system name (never page-numbered). Otherwise keep it page-local in `static-files/css/pages/`.
5. Colors: prefer Iris palette even if the design hex differs slightly — consistency beats a 5 % hue delta (spec §44). Record deliberate deviations in a finding.

## Iris-only rule
Never change `currentThemeStyle`, never add Theme Roller output, never redefine `--ut-*`/`--a-*` on `:root`.
Scoped redefinition is allowed: `.app-hero { --ut-component-background-color: … }`.

## Common mistakes
- Importing 100 Figma variables verbatim as `--app-*`.
- Hardcoding `#00688c` instead of `var(--app-color-primary)`.
- Reading `--a-button-*` on `:root` (component-scoped; read on the button).
