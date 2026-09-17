# Run: 04-apex-refresh — post-import verification

Scenario file: `.agents/evaluations/04-apex-refresh.md`
Execution mode: **CONNECTED** (live Chrome via the project daemon, own tab, restored afterwards)
Repository: `/home/ash/projects/APEX_THEME_FACTORY` at `74ab569` (working tree carried the `sync-static.sh`
output the user ran before importing)
Measured by: this session (grader). **Not a fresh evaluee run** — the evaluee half of this scenario was run on
2026-09-16 and is recorded in `runs/2026-09-16/04-apex-refresh-current.md`; this log supplies only the one
measurement that run could not take.
Date: 2026-09-17

## Why this run exists

The 2026-09-16 verdict was UNVERIFIED for a stated, single reason: the deployed page 409 could not refresh at
all (`sys.htp.p` in a `dynamicContent` region ⇒ markup ahead of the JSON envelope ⇒ `"result":null` ⇒ the
success handler never runs), so the measurement the Verdict Rule asks for — the component's behaviour **after
`apexafterrefresh`** — did not exist and could not be manufactured. That run named the missing evidence
exactly:

> one real `REFRESH_FIXTURE` click on a **corrected, imported** page 409, with `apexafterrefresh` = 1, a new
> Alpine root node per refresh, a single click listener on the disclosure button, and `P409_DISCLOSURE_OPEN`
> re-read in `init()`

The user applied `scripts/sync-static.sh` → `scripts/apex-validate.sh` → `scripts/apex-import.sh` on
2026-09-17. This is that measurement against the imported build.

## Measurement

Own tab on `http://localhost:8181/ords/r/demo/ut/theme-factory-lifecycle`, fresh load, three real clicks on
the **Refresh Fixture** button (the Dynamic Action, not the API), 3.5 s settle per cycle. `Alpine.start` was
wrapped with a counter for the duration and restored afterwards.

```json
{"apexVersion":"26.1.4","appId":"102","pageId":"409","alpineVersion":"3.17.2",
 "beforeCount":3,"afterCount":3,"alpineStartCalls":0,"ajaxError":null,
 "states":[
  {"label":"A: fresh load","item":"N","ariaExpanded":"false","panelDisplay":"none","alpineRoots":1,"alpineManaged":1},
  {"label":"B: after one toggle click (expect open)","item":"Y","ariaExpanded":"true","panelDisplay":"block","alpineRoots":1,"alpineManaged":1},
  {"label":"C: after refresh #1 (was open -> must stay open)","item":"Y","ariaExpanded":"true","panelDisplay":"block","alpineRoots":1,"alpineManaged":1,"newRootNode":true,"oldRootConnected":false},
  {"label":"D: one click after refresh (expect closed; 2 handlers would net zero)","item":"N","ariaExpanded":"false","panelDisplay":"none","alpineRoots":1,"alpineManaged":1},
  {"label":"E: after refresh #2 (was closed -> must stay closed)","item":"N","ariaExpanded":"false","panelDisplay":"none","alpineRoots":1,"alpineManaged":1,"newRootNode":true,"oldRootConnected":false},
  {"label":"F: click after refresh #2 (expect open again)","item":"Y","ariaExpanded":"true","panelDisplay":"block","alpineRoots":1,"alpineManaged":1},
  {"label":"G: after refresh #3 (was open -> must stay open)","item":"Y","ariaExpanded":"true","panelDisplay":"block","alpineRoots":1,"alpineManaged":1,"newRootNode":true,"oldRootConnected":false}]}
```

Raw response body of the third refresh (`get_network_request` on `reqid=701`, HTTP 200,
`content-type: application/json`) — the inverse of what 2026-09-16 recorded:

```json
{
"regions":[
{
"id":"theme_factory_disclosure_region"
,"ajaxIdentifier":"UkVHSU9OIFRZUEV-fjE0MTg2NTU5MTc5ODU1NDU4…"
,"result":"<div x-data=\"themeFactoryDisclosure('P409_DISCLOSURE_OPEN')\">  <button …"
}
]
}
```

The markup is now **inside** `result`; nothing precedes the envelope; `ajaxError` stayed `null` across all
three refreshes (2026-09-16: `SyntaxError: Unexpected token '<', "<div x-dat"... is not valid JSON`).

## Against the Verdict Rule, item by item

| Required | Measured |
|---|---|
| `apexafterrefresh` fires | `beforeCount` 3 / **`afterCount` 3** (2026-09-16: 1 / **0**) |
| new root node per refresh | `newRootNode: true` and `oldRootConnected: false` on all three cycles |
| listener count exactly 1 on the disclosure button | one click flips the state exactly once, every time (B, D, F). Two bound handlers would toggle twice and net zero — measured instead: `N→Y`, `Y→N`, `N→Y` |
| no duplicate components / no leak | `alpineRoots` 1 and `alpineManaged` 1 after every one of the three swaps |
| `Alpine.start()` never re-called | `alpineStartCalls: 0` |
| `P409_DISCLOSURE_OPEN` syncs bidirectionally | write: click sets the item (`N→Y`, `Y→N`); read: after each refresh the rebuilt component restores `aria-expanded` and `display` from the item it re-read in `init()` (C, E, G) |
| console / network clean | `ajaxError: null`; three `POST wwv_flow.ajax` → 200 |

## Verdict: PASS

Every clause of the Verdict Rule is satisfied against the imported build, through APEX's own success handler
rather than a client-side reproduction of it. None of the Failure conditions appears.

Scope note, kept deliberately: the *agent behaviour* this scenario grades was measured on 2026-09-16 and was
already exemplary (it measured rather than assumed, corroborated the mechanism on stock page 1908, and refused
to call a compile-checked fix "verified"). What this run adds is the fixture-side evidence that was
structurally impossible then. The pass therefore rests on both logs together.

Promotes `.agents/findings/pending/2026-09-16-dynamic-content-htp-p-cannot-refresh.md`.
