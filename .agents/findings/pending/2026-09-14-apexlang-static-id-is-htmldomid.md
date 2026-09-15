# Finding

Status:
Pending (2026-09-15) — Missing evidence: evaluation scenario where no sibling component demonstrates `htmlDomId` (isolating skill guidance from codebase grepping), plus scenario testing app-level CSS/JS `userInterface` vs top-level routing blocks. Evaluated 2026-09-14 (see evaluations/runs/2026-09-14/12-apexlang-static-id-{baseline,current}.md): PASS at baseline (evaluee grepped codebase) and current (no-op on already patched file). Retained in pending until isolated scenario confirms load-bearing behavior.

Category:
APEXLANG-KNOWLEDGE

Confidence:
CONFIRMED

APEX Version:
26.1.4 (APEXLang compiler metadata 26.1.0+3102)

Page:
app 102 page 405 (Cards region `theme_packages_cards`); also pages 300, 421, 424 in the export

Component:
region / button `advanced { … }` block

## Observation

The Page Designer property **Static ID** is the APEXLang property `htmlDomId` inside `advanced { }`.
`staticId` also exists in the same group but is the compiler's *internal component identifier*
(`staticId (required)`), not the DOM id. Writing `advanced { staticId: theme_packages_cards }` validated but
produced no `id="theme_packages_cards"` at runtime; `htmlDomId` did.

## Evidence

- `node tools/query-valid-props.mjs --component region` → `[advanced] htmlDomId`, `staticId (required)`.
- Export: `p00300-grid-layout.apx:911 htmlDomId: responsive_design`, `p00421-navigation2.apx:242`, `p00424-touch-gestures.apx:386`.
- Runtime after import: `document.getElementById('theme_packages_cards')` found only with `htmlDomId`.

## Existing Assumption

`apexlang-design-editor` SKILL.md table: "Hook for scoped CSS | `cssClasses:` on region/item/button; `staticId:`".
It also said app-level CSS/JS live under `userInterface { css/javaScript }`; in `application.apx` they are
top-level `css { fileUrls }` / `javaScript { fileUrls }` blocks.

## Impact

An agent following the skill writes a valid-but-ineffective property and then cannot select the region.

## Proposed Knowledge Change

`apexlang-design-editor`: `staticId:` → `advanced { htmlDomId: … }`; app-level CSS/JS row → top-level blocks.

## Regression Scenario

"Give region X a Static ID so page CSS can target it" → expected `advanced { htmlDomId: x }`; failure: `staticId`.

## Scope

Reusable APEXLang knowledge (26.1 grammar).
