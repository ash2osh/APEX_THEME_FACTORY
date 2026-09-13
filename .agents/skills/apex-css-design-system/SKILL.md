---
name: apex-css-design-system
description: Use when writing or editing any CSS in static-files/css — new component styles, page styles, styling a native APEX component (IG/IR/cards/dialog/form) to match a design
---

# apex-css-design-system

Structure: `static-files/css/{app.css, foundation/, apex/, components/, pages/}` (spec §15). Tokens: `apex-design-system`. Selectors: `apex-css-selector-strategy`.

## Core principle
Scoped, token-based, source-controlled CSS that restyles Universal Theme without replacing it.

## Where a rule goes
| Rule affects | File |
|---|---|
| tokens / aliases | `foundation/tokens.css` |
| all regions / buttons / forms app-wide (verified) | `apex/<component>.css` |
| one reusable `.app-*` component | `components/<name>.css` (+ `js/components/<name>.js` if Alpine) |
| one page | `pages/<page-alias>.css` scoped by `.page-<N>` or the page wrapper class |

`app.css` imports the others in that order.

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
- Repeating a literal that exists as a token (spec §17).
- Putting page CSS in Page Designer "Inline CSS" instead of the repo file.
