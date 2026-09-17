# Finding

Status:
**Accepted (2026-09-17)** — scenario 04 passes against the imported build
(`.agents/evaluations/runs/2026-09-17/04-apex-refresh-postimport.md`). The source fix
(`applications/ut/pages/p00409-theme-factory-lifecycle.apx` returns its markup instead of `sys.htp.p`-ing it)
was imported by the user on 2026-09-17, and one real `REFRESH_FIXTURE` click now produces
`apexbeforerefresh` = 1 / **`apexafterrefresh` = 1** with a new Alpine root node and `"result"` carrying the
markup inside the JSON envelope — the exact inverse of the measurement below. Measured over three consecutive
refreshes: `beforeCount` 3 / `afterCount` 3, `alpineStartCalls` 0, one component instance per swap, one click
handler, `P409_DISCLOSURE_OPEN` synced both ways, `ajaxError` null.
Prior status, for the record: *Pending (2026-09-17) — runtime-verified twice… Missing before promotion: an
import of app 102 and one live `REFRESH_FIXTURE` click showing `apexafterrefresh` = 1.*

Category:
BUG (also APEXLANG-KNOWLEDGE / APEX-JAVASCRIPT-PATTERN)

Confidence:
CONFIRMED

APEX Version:
26.1.4 (Universal Theme / Iris)

Page:
app 102 page 409 (`theme-factory-lifecycle`, the scenario-04 refresh fixture); reproduced on the stock
Universal Theme demo page 1908 (*Dynamic Content Region*)

Component:
`region type: dynamicContent` → runtime custom element `<a-dynamic-content region-id=… ajax-identifier=…>`

## Observation

A `dynamicContent` region whose PL/SQL function body writes its markup with `sys.htp.p` **can never be
refreshed**. `apex.region(id).refresh()` (and the Dynamic Action that calls it) fires `apexbeforerefresh`,
issues one `POST wwv_flow.ajax` that returns HTTP 200 — and then nothing happens: `apexafterrefresh` never
fires, the DOM is never replaced, and the console stays clean, so the failure is silent.

The cause is in the response body. The region's refresh is
`apex.server.plugin({regions:[{id,ajaxIdentifier}],pageItems}, { success: e => { el.innerHTML = e.regions[0].result } })`,
and `result` is the **return value** of the function body. `htp.p` output is written to the response stream
*ahead of* the JSON envelope, so the body is `<div …>…</div>{"regions":[{…,"result":null}]}`: jQuery's JSON
parse fails (`SyntaxError: Unexpected token '<'`), `success` never runs, and the envelope's `result` is `null`
in any case.

## Evidence

Live, app 102 page 409, 2026-09-16, measured twice by two agents in separate Chrome tabs:

- Grader probe after `apex.region('theme_factory_disclosure_region').refresh()` + 3 s settle:
  `{"beforeCount":1,"afterCount":0,"oldRootConnected":true,"rootIsSame":true,"rootCount":1,
  "rootHtmlLenBefore":1939,"rootHtmlLenAfter":1939,"itemBefore":"N","itemAfter":"N"}`.
- Raw response for that request (`get_network_request`, 200, `content-type: application/json`): the four
  `htp.p` lines, then `{"regions":[{"id":"theme_factory_disclosure_region","ajaxIdentifier":"…","result":null}]}`.
- Evaluee run, same page via a real click on the `REFRESH_FIXTURE` button: identical counts, plus jQuery
  `ajaxError` = `SyntaxError: Unexpected token '<', "<div x-dat"... is not valid JSON`.
- Corroboration on stock page 1908 (`apex.region('Demo1').refresh()`): `changed:false`,
  `SyntaxError: Unexpected token '<', "<ul>\n<li>D"...`. Oracle's own demo has the same defect; it simply
  ships no refresh trigger.
- Full transcripts: `.agents/evaluations/runs/2026-09-16/04-apex-refresh-current.md`.

## Existing Assumption

`.agents/evaluations/04-apex-refresh.md` and the 2026-09-15 README round-8 entry call page 409 "the real
declarative refresh fixture", and `apex-alpine-lifecycle` treats `apexafterrefresh` as the hook that will fire
for a refreshable region. Nothing recorded that this particular region can never reach that event.

## Impact

Two levels:

1. **Project:** scenario 04 cannot be graded PASS against this fixture, no matter how correct the Alpine
   component is — the refresh under test is a no-op. The fixture has been in this state since it was
   committed (`e700804`).
2. **Reusable:** any agent building a refreshable Dynamic Content region in APEX 26.1 with `htp.p` ships a
   region that looks fine on first render and silently never refreshes. The correct form is
   `return '<…>' || … ;` from `plsqlFunctionBody`.

A useful second-order fact measured alongside it: page items placed in the region's `regionBody` slot render
as **siblings** of `<a-dynamic-content>`, so a refresh does not replace them — client-side item state (and an
Alpine component that re-reads it in `init()`) survives the swap by construction.

## Proposed Knowledge Change

1. `applications/ut/pages/p00409-theme-factory-lifecycle.apx`: `return` the markup instead of `sys.htp.p`-ing
   it (compile-checked by the evaluee: `scripts/apex-validate.sh` → `Validation successful.`), then import so
   scenario 04 has a fixture that can actually refresh.
2. `.agents/knowledge/pitfalls.md` §2: record the `htp.p` trap, the `<a-dynamic-content>` mechanism, the
   1908 corroboration, and the `regionBody`-items-are-siblings consequence.
3. `.agents/evaluations/04-apex-refresh.md`: note that the fixture must return its markup, so the next run
   does not re-derive this.

Item 2 is applied as part of the 2026-09-16 evaluation round. Items 1 and 3 need the user's decision, since
they require touching `applications/ut/` and importing app 102.

## Regression Scenario

Given: a `dynamicContent` region and a button whose Dynamic Action refreshes it. Expected: after the click,
`apexafterrefresh` fires once and the region's root node is a new element. Failure: `apexbeforerefresh` only,
same root node, `"result":null` in the AJAX envelope. This is exactly
`.agents/evaluations/04-apex-refresh.md`'s Required Artifact Checklist items 2–3 — no new scenario needed.

## Scope

Reusable APEX 26.1 knowledge (region type behaviour), plus a page-specific bug in this project's own
evaluation fixture.
