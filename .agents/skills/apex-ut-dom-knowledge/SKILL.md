---
name: apex-ut-dom-knowledge
description: Use when you need the real Universal Theme 26.1 / Iris markup, class names or CSS variables for a component (region, IG, IR, cards, dialog, nav, buttons, forms) — before writing a selector or assuming structure
---

# apex-ut-dom-knowledge

Verified facts: `.agents/knowledge/ut-26.1-iris-runtime.md`, tokens `.agents/knowledge/iris-ut-tokens.md`, traps `.agents/knowledge/pitfalls.md`.
Offline CSS: `.agents/knowledge/reference/ut-26.1/` — UT `Core`/`Iris` **declare** tokens; the APEX widget CSS `app_ui-Core`/`app_ui-Theme-Standard` **consumes** atoms with light fallbacks. Grep all four.

## Core principle
Do not guess UT DOM. Inspect it (spec §4), then record verified structure as knowledge.

## Confirmed hooks (26.1.4 / Iris)
- `html.page-<N>.app-<ALIAS>`; `body.t-PageBody.apex-theme-iris` (+ `.t-PageBody--leftNav`, `.js-navExpanded`).
- Theme JS `theme42.min.js`; icons Font APEX 2.5.1; font Oracle Sans.
- CSS cascade: UT `Core.min.css` → `Iris.min.css` → app files. App CSS loads last.
- Token namespaces: `--ut-*` (theme), `--a-*` (component atoms, mostly element-scoped), `--u-*` (utilities). Reserved (spec §20).

## How to learn a component's DOM (once per component)
1. Open the app 102 reference page for it (e.g. 1201 Regions, 1100 Pages).
2. `take_snapshot` for hierarchy; `evaluate_script` to dump `outerHTML` of one instance (trim to 2 KB).
3. Note: wrapper class, header/body/footer classes, state classes (`is-active`, `is-collapsed`), which node gets `cssClasses:`, which node is replaced on refresh.
4. Save as `.agents/knowledge/ut-dom-<component>.md` with the page and date. Confidence HIGH only after 2+ pages.

## Common mistakes
- Assuming 24.x class names (e.g. IG toolbar) survive unchanged in 26.1.
- Treating one demo page's extra wrapper as the general structure (spec §56).
