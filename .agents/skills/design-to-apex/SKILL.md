---
name: design-to-apex
description: Use when asked to implement, reproduce, restyle or improve any UI in this Oracle APEX (26.1, Universal Theme / Iris) project from a Figma, Stitch, screenshot, PDF, other-app or written design — including "make this page look like X" and "match this mockup"
---

# design-to-apex (router)

Governing spec: `docs/AGENT_SPEC.md`. Project facts: `docs/PROJECT.md`. Theme style is **Iris only**.

## Core principle
Universal Theme owns structure · APEXLang owns declarations · repo CSS owns appearance · Alpine owns
custom interaction · APEX JS APIs bridge · PL/SQL owns logic. Runtime truth comes from Chrome DevTools,
never from memory.

## Workflow (spec §77) — follow in order, one section at a time
1. UNDERSTAND the request. Split the design into sections (header, context, KPIs, content, grid, actions, dialogs).
2. INSPECT TARGET → `apex-design-system` (map values to Iris/`--app-*` tokens).
3. INSPECT SOURCE → `applications/ut/pages/pNNNNN-*.apx`, `static-files/`, `docs/COMPONENTS.md`.
4. INSPECT RUNTIME → `chrome-devtools-mcp` (DOM, computed CSS, console). Required before any CSS.
5. MAP COMPONENTS → `apex-component-selection`, `apex-ut-dom-knowledge`, `apex-template-options`.
6. CHOOSE IMPLEMENTATION in priority order: existing component → native APEX → native+CSS → native+Alpine → reusable custom → custom HTML.
7. IMPLEMENT one section → `apexlang-design-editor`, `apex-css-design-system`, `apex-css-selector-strategy`; if custom interaction → `apex-alpine-components`, `apex-alpine-lifecycle`, `apex-alpine-server-integration`.
8. VALIDATE SOURCE → `apexlang-roundtrip` (validate; import only when asked).
9. RELOAD, CHECK CONSOLE, COMPARE → `apex-visual-comparison`; then `apex-responsive-design`, `apex-accessibility`.
10. REVIEW → `apex-design-review` (completion checklist §75). Capture findings in `.agents/findings/pending/`.

Load only the skills the step needs.

## Red flags — stop and re-route
- About to write CSS without having run `take_snapshot`/`evaluate_script` on the page.
- About to replace an IG/IR/native item/dialog with custom markup "to match the design".
- About to write `.t-Region {` or `!important` or a literal that Iris already has as a token.
- About to call it done while the change exists only in DevTools.
- About to switch theme style or touch Theme Roller.
