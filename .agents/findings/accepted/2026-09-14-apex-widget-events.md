# Finding

Status:
**Accepted 2026-09-17** — runtime-verified knowledge (listener dumps on `document`/`window`, the `theme42.min.js`
trigger sequence, live `menu('option','items')` reads, and the p1912 console error that disappears with the
guard), and its scenario passes on both sides
(`evaluations/runs/2026-09-14/13-cards-render-event-{baseline-eda510d,current}.md`, the corrected isolation
point).

Promoted for the knowledge, with the same caveat as the `htmlDomId` finding: the baseline passed by reading
the handler that already existed in application code, so the skill-text change is not demonstrated
load-bearing, and scenario 13 exercises only the Cards-render-timing half — the navigation-menu radio group
and the `$('#missing').menu(…)` empty-set guard are still untested by any scenario (narrowed in round 7 to say
so). The 2026-09-16 round adds an independent instance of the same class of trap, recorded separately: a
Dynamic Content region's refresh never fires `apexafterrefresh` at all when the region prints with `htp.p`
(`findings/pending/2026-09-16-dynamic-content-htp-p-cannot-refresh.md`).

Earlier status, for the record: *Pending (2026-09-15) — missing a scenario isolating the load-bearing effect
where the correct code is not already present in sibling files.*

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
