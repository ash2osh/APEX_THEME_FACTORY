# Finding

Status:
**Rejected 2026-09-17** — measured to completion on a live sticky Interactive Grid (consumer 9011 page 2,
`business_ig`) in both themes, at rest and while stuck. The finding's mechanism is wrong in both halves, and
the rule it proposed would have been a no-op:

- `.is-stuck` is **not** applied at rest (`box-shadow: none`), so there is no doubled line at rest and nothing
  for a `box-shadow: none` rule to suppress. The proposed rule's own precondition ("inspect whether `.is-stuck`
  is set at rest. If yes, …") is false.
- The second line is **not** the first row's top border. Measured under linen, stuck:
  first body cell `border-top: 0px rgba(0,0,0,.1)` — zero width, it contributes nothing.
- What does stack, and only while stuck, is the **header cell's own** `border-bottom: 0.8px rgba(0,0,0,.1)`
  plus the sticky wrapper's `box-shadow: rgba(0,0,0,.1) 0 1px 0 0` — same hairline colour, ~1.8px total.
  Under solarized-dark the same pair reads `rgba(147,161,161,.2)`.

So: a ~1.8px hairline exists *while scrolled*, never at rest, and if anyone ever decides it is worth fixing,
the fix is to drop the header cell's `border-bottom` under `.is-stuck` — not to remove the shadow. Nobody has
reported it as a defect, and at 0.8px + 1px of the same 10%-alpha colour it is barely distinguishable from the
intended hairline. Recorded and closed rather than left pending.

Raw measurements, live, 2026-09-17 (own tab via the project Chrome MCP daemon, closed afterwards):

```json
solarized-dark, at rest : {"isStuck": false, "boxShadow": "none",
                           "headerCellBorderBottom": "0px rgb(238,232,213)",
                           "firstCellBorderTop": "0px rgba(147,161,161,0.2)"}
solarized-dark, scrolled: {"isStuck": true,
                           "boxShadow": "rgba(147,161,161,0.2) 0px 1px 0px 0px"}
linen, scrolled         : {"isStuck": true,
                           "wrapperBoxShadow": "rgba(0,0,0,0.1) 0px 1px 0px 0px",
                           "headerCellBorderBottom": "0.8px rgba(0,0,0,0.1)",
                           "headerCellBoxShadow": "none",
                           "firstBodyCellBorderTop": "0px rgba(0,0,0,0.1)"}
```

Also settled, since the 2026-09-16 status line left it open: app 102 page 1410's Interactive Grid renders no
`.js-stickyTableHeader` element at all, so that page could never have shown this. The original 1440px
screenshot that prompted the finding was of a scrolled grid — consistent with the corrected mechanism.

Previous status, for the record: *Pending (2026-09-16) — partial live evidence; still missing a second IG page
with the sticky widget and a measurement while scrolled.*

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
