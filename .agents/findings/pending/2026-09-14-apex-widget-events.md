# Finding

Status:
Pending — demoted 2026-09-14 from a premature Accepted. The first evaluation run (baseline at `9276369`) showed
a FAIL, but PR #4's Codex review (P2) correctly pointed out that `9276369` predates `eda510d`, which already
contains the correct `tablemodelviewpagechange` handler this finding is about — so that baseline wasn't
isolating the skill-text change, it was also missing the application code current had. Re-run against the
correct isolation point (`eda510d`, same app code as current, old Cards-silent skill text): PASS — see
evaluations/runs/2026-09-14/13-cards-render-event-baseline-eda510d.md. The evaluee got the right event by
reading the existing correct handler, not from skill guidance, so a properly isolated baseline also passes.
Current still passes: evaluations/runs/2026-09-14/13-cards-render-event-current.md. The knowledge itself
(pitfalls.md §2.4, the skill correction) is still accurate and worth keeping — it just hasn't been shown
load-bearing by this scenario. Original (invalid) baseline kept for the record:
evaluations/runs/2026-09-14/13-cards-render-event-baseline.md.

Category:
APEX-JAVASCRIPT-PATTERN

Confidence:
CONFIRMED

APEX Version:
26.1.4 (Universal Theme / Iris)

Page:
app 102 pages 500, 405, 1912

Component:
navigation-bar `menu` widget (theme42), Cards region (`tableModelView`)

## Observation

- theme42 builds `.t-NavigationBar-menu` widgets on `apexreadyend` and then triggers `theme42ready` on **window**;
  `menu('option','items')` can be rebuilt afterwards, and the widget supports `{type:'radioGroup', get, set, choices}`
  (renders `menuitemradio` + `aria-checked`). Synthetic `element.click()` does not activate an item.
- On pages without a navigation bar, `$('#missing').menu('option','items')` returns the empty jQuery set — no error —
  so `items.forEach` threw inside every dialog page and interrupted theme42's init chain.
- Cards regions render after DOM-ready; `apex.region(id).refresh()` fired no `apexafterrefresh`; the widget's
  `tablemodelviewpagechange` bubbles to `document` after each render. `card { cssClasses: [ … &COL. ] }` is
  substituted and lands on `.a-CardView`.

## Evidence

`evaluate_script` listeners on `document`/`window`, `theme42.min.js` (`g.trigger(l)` after `t(Z)`), runtime
`menu('option','items')` dumps, console error on p1912 before the guard.

## Existing Assumption

`apex-alpine-lifecycle` / spec §34 list `apexafterrefresh` as the refresh hook for refreshable regions; no note on
Cards' render timing or the menu radio group.

## Impact

Post-processing of menus/cards silently runs too early; dialog pages break.

## Proposed Knowledge Change

pitfalls.md §2; `ut-26.1-iris-runtime.md` "Events" section; Chrome doc troubleshooting rows.

## Regression Scenario

Given: mark the active card in a Cards region after load. Expected: hook `tablemodelviewpagechange` (or the region's
own events), not `apex.jQuery(fn)`. Failure: DOM-ready hook, or `apexafterrefresh` only.

## Scope

Reusable APEX 26.1 knowledge.
