# Finding

Status:
Pending (2026-09-16) — Partial live evidence: on consumer 9011 page 2 (`business_ig`, Linen, 1440 px, scrollY 0)
the IG header `.t-fht-thead.js-stickyTableHeader` has **no** `.is-stuck` at rest and `box-shadow: none`; the
first cell's `border-top` is `0.8px solid rgba(0,0,0,.1)`. So the sticky shadow is not the doubled line at
rest — the proposed `box-shadow: none` rule would change nothing there. App 102 page 1410 exposes no
`.js-stickyTableHeader` element at all (IG renders without the sticky widget on that page). Still missing: a
second IG page with the sticky widget, and a measurement while scrolled (`.is-stuck` true) to see whether the
doubled line only appears in the stuck state.

Category:
UNIVERSAL-THEME-KNOWLEDGE

Confidence:
MEDIUM

APEX Version:
26.1.4 (Universal Theme / Iris)

Page:
app 102 page 1410

Component:
Interactive Grid `.a-IG` / `.js-stickyTableHeader.is-stuck`

## Observation

With hairline row separators (`--a-gv-cell-border-color: rgba(0,0,0,.1)`), the IG header shows a doubled
line: the sticky-header box-shadow (`.js-stickyTableHeader.is-stuck { box-shadow: 0 1px 0 0 … }`) plus the
first row's top border. Visible in the 1440px screenshot; not present on the IRR (no sticky header there).

## Evidence

CSSOM: `.a-IRR-tableContainer .js-stickyTableHeader.is-stuck{box-shadow:0 var(--a-gv-header-cell-border-width,1px) 0 0 var(--a-gv-header-cell-border-color)}`;
screenshot scratchpad `proto-ig-p1410.jpeg`. Not yet measured whether `.is-stuck` is applied when not scrolled.

## Existing Assumption

None recorded.

## Impact

Cosmetic; visible on every IG with the quiet style.

## Proposed Knowledge Change

Inspect on 2+ IG pages whether `.is-stuck` is set at rest. If yes, add to `reports.css`:
`.apex-theme-iris .a-IG .js-stickyTableHeader.is-stuck { box-shadow: none }` only when the header is at
its natural position — likely needs the UT class that marks "actually stuck". Record result in `ut-dom-reports.md`.

## Regression Scenario

Given: IG at rest at 1440. Expected: single hairline under the header. Failure: double line.

## Scope

Page-specific until verified on a second IG page.
