# Finding

Status:
**Accepted 2026-09-17** — the knowledge is runtime-verified (`advanced { staticId: … }` validates and produces
no DOM id; `htmlDomId` does — `document.getElementById` after import, plus
`tools/query-valid-props.mjs --component region`), and its scenario passes on both sides
(`evaluations/runs/2026-09-14/12-apexlang-static-id-{baseline,current}.md`). The 2026-09-16 round confirmed the
property again in passing: the scenario-09 grader probe resolved the p1410 Interactive Grid to `#Demo1_ig` from
`advanced { htmlDomId: Demo1 }`.

Promoted for the knowledge, with the isolation question recorded rather than pretended away: the baseline
evaluee reached the right answer by grepping the export, so the skill-text correction is not demonstrated
load-bearing, and no scenario in this suite isolates a case where no sibling component shows `htmlDomId`. The
second half of this finding — app-level CSS/JS being top-level `css`/`javaScript` blocks rather than
`userInterface` — is verified against `application.apx` but has never been exercised by an evaluation task;
scenario 12's Expected was narrowed in round 7 to say so.

Earlier status, for the record: *Pending (2026-09-15) — missing an evaluation scenario where no sibling
component demonstrates `htmlDomId`, plus one testing app-level CSS/JS routing.*

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
