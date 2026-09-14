# Finding

Status:
Accepted (2026-09-14 — evaluation 13 passed, see evaluations/runs/2026-09-14/13-cards-render-event-current.md; baseline failed, see evaluations/runs/2026-09-14/13-cards-render-event-baseline.md)

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
