---
name: apex-css-design-system
description: Use when writing or editing any CSS in static-files/css or a theme package under sample-themes/<name>/css — new component styles, page styles, theme tokens, styling a native APEX component (IG/IR/cards/dialog/form) to match a design
---

# apex-css-design-system

Structure: `static-files/css/{app.css, foundation/, components/, pages/}` + one **theme package** per look in
`sample-themes/<name>/css/{tokens.css, apex/*.css}` (spec §15 adapted; see `sample-themes/README.md`). Tokens:
`apex-design-system`. Selectors: `apex-css-selector-strategy`.

## Core principle
Scoped, token-based, source-controlled CSS that restyles Universal Theme without replacing it.

## Where a rule goes
| Rule affects | File |
|---|---|
| a new `--app-*` role (Iris default) | `static-files/css/foundation/tokens.css` — every role is declared here first |
| the look of a theme (tokens, app-wide regions / buttons / forms / reports) | `sample-themes/<name>/css/tokens.css` + `css/apex/<component>.css`, every rule under `html.app-theme-<name>`, atoms on `.apex-theme-iris` |
| one reusable `.app-*` component (theme-independent) | `static-files/css/components/<name>.css` (+ `js/components/<name>.js` if Alpine) |
| one page | `static-files/css/pages/<page-alias>.css` scoped by `html.page-<N>` |

`app.css` imports foundation → components → pages → the generated `@themes` block (never edit that block: run
`scripts/sync-static.sh`, which also copies the packages into the APEXLang export). A dark package must remap
Iris' literal `:root` tokens (`--ut-region-*`, `--ut-field-label-text-color`, `--a-checkbox-*`, …) — see
`sample-themes/solarized-dark/README.md`. Grep atoms in all four files of `.agents/knowledge/reference/ut-26.1/`.

**Adapter fences.** Lines between `/* @adapter <family>/<file>#N … */` and `/* @adapter-end … */` are rendered
from `theme-templates/adapters/<family>/<file>.css.tmpl` and shared by every theme of that family. Never edit
them in place: change the template (use `__NAME__` / `__PREFIX__`), run `scripts/theme.sh adapters`, and check
every member theme. A rule for one theme goes outside the fences.

## Writing a rule
1. Inspect the runtime element (`chrome-devtools-mcp`): real class list, winning rule, specificity.
2. Prototype in DevTools; measure.
3. Write the rule with `--app-*` tokens; scope it; comment any UT-internal selector with why.
4. Reload, console, screenshot, compare; check 4 widths.

## Native components — style, don't rebuild
IG: `.app-x .a-IG …`; IR: `.app-x .t-IRR-*`; Cards: `.app-x .a-CardView-*`; Region: `.app-x .t-Region-header/-body`.
Verify each class on the live DOM first — names differ across UT versions.

## Common mistakes
- `!important` to beat Iris — fix specificity/scope instead (spec §23).
- Repeating a literal that exists as a token (spec §17); any literal colour in `css/apex/*.css` (put it in `tokens.css`).
- Putting theme CSS in `static-files/css/` — it is neither scoped to the theme class nor synced as a package.
- Putting page CSS in Page Designer "Inline CSS" instead of the repo file.
- Proposing Google Fonts, external font URLs, or unlicensed fonts (fonts must be package-local licensed WOFF2 files; Font APEX icons untouched).
