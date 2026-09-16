# Run: 04-apex-refresh — current

Scenario file: `.agents/evaluations/04-apex-refresh.md`
Execution mode: **CONNECTED** (live Chrome via the project daemon; `scripts/apex-validate.sh` permitted; no import, no DB change)
Worktree: `/tmp/eval/04-apex-refresh-current` at commit `4fc73b81ba305c17b11da9d8b37625938d5aa475`
Evaluee: fresh general-purpose agent, not told which skill was under test
Grader: this session (independent re-measurement below)
Date: 2026-09-16

## Evaluee prompt (verbatim)

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/04-apex-refresh-current. cd there and treat it as your working directory for this whole task — all file reads and edits happen there, nowhere else. Never read or write anything in /home/ash/projects/APEX_THEME_FACTORY.

Your instructions are /tmp/eval/04-apex-refresh-current/AGENTS.md, the docs it references, and the skills under /tmp/eval/04-apex-refresh-current/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its copies may not match this directory). Do not read anything under .agents/evaluations/ (out of scope for this task).

Execution mode: CONNECTED (live browser). You may run scripts/apex-validate.sh (a read-only compile check over the saved connection docker-demo) if you want your APEXLang edits checked. You may NOT run scripts/apex-import.sh, may not import anything, and may not make any database change.

Browser access goes ONLY through the project daemon, which is already running: from your worktree run
    python3 tools/chrome_devtools_client.py <tool> '<json-args>'
for example: python3 tools/chrome_devtools_client.py new_page '{"url":"http://localhost:8181/ords/r/demo/ut/theme-factory-lifecycle","background":true}'
Do NOT start a daemon of your own, do NOT call any chrome-devtools MCP tool directly, and do NOT use any other browser tool — doing so triggers a Chrome consent prompt the user cannot accept. Etiquette, all hard rules:
- Open your OWN tab with new_page {"url":…, "background":true} and close it with close_page when you are done.
- Page 1 in list_pages (the getting-started tab) belongs to the user: never navigate, reload, or close it.
- Never navigate to a URL containing "#theme=" — it rewrites the stored theme for every tab of that origin.
- Use emulate {"pageId":…, "viewport":"1440x900x1"} for viewport work; never resize_page.
- Page-scoped tools need the pageId from list_pages.

Environment: app 102 (workspace DEMO, APEX 26.1.4, Universal Theme 42 / Iris) runs at http://localhost:8181/ords/r/demo/ut/. Its page 409 is at .../theme-factory-lifecycle. That page has a disclosure widget built with Alpine.js inside a region, and a "Refresh Fixture" button whose Dynamic Action refreshes that same region. The component source is static-files/js/components/themeFactoryDisclosure.js and the page source is applications/ut/pages/p00409-theme-factory-lifecycle.apx. The running app serves the static files already imported into the database, so any source edit you make in the worktree will NOT appear in the browser this session — you may not import. Say so plainly rather than claiming a fix was verified live.

Task: establish, with live runtime evidence, whether that Alpine disclosure keeps working correctly every time its region is refreshed by that Dynamic Action. Exercise it for real in the browser and measure what actually happens, before and after refresh. If you find defects, fix the source in this worktree.

Deliver: (1) a short plan, (2) the exact measurements you took, quoted from the browser (state them as numbers/values, not impressions), (3) any edits you made and why, (4) a final summary: what you verified live, what you could not verify and why. Stop before any import.
```

Note on prompt design: `.agents/evaluations/` was placed out of scope so the evaluee could not read this
scenario's own Expected/Failure/Verdict text (pitfalls §6.2 — a prompt must not hand over the answer). The
environment paragraph states only where things live and what may not be done; it does not name the refresh
hook, Alpine lifecycle behaviour, or anything about duplicate handlers.

## Evaluee final report (verbatim)

> Work complete. My tab is closed; the user's Getting Started tab was never navigated.
>
> ## 1. Plan
>
> 1. Read the fixture source (`p00409-…apx`, `themeFactoryDisclosure.js`) and the `apex-alpine-lifecycle` skill / pitfalls record.
> 2. Open my own background tab on page 409, measure the disclosure at rest and after a real click.
> 3. Click the real "Refresh Fixture" button, measure DOM identity, Alpine state, item value, region events, console and the AJAX response.
> 4. If the refresh misbehaves, find the mechanism (region API source, response envelope), corroborate on a second page.
> 5. Reproduce the *correct* refresh client-side to test the Alpine lifecycle itself over repeated DOM swaps.
> 6. Fix source, compile-check with `apex-validate.sh`, stop before import.
>
> ## 2. Measurements (all quoted from the running page, app 102 / page 409, `apex.env.APEX_VERSION` = `26.1.4`, `Alpine.version` = `3.17.2`)
>
> **Baseline, fresh load:** `open=false`, panel inline style `display: none;`, computed `display:"none"`, height `0`, `aria-expanded="false"`, `apex.item('P409_DISCLOSURE_OPEN').getValue()` = `"N"`, 1 Alpine root node.
> **After a real click on "Toggle details":** `open=true`, `display:"block"`, height `20`, `aria-expanded="true"`, item `"Y"`. So the widget works before any refresh.
>
> **Real click on "Refresh Fixture" (the Dynamic Action):**
> - region events: `apexbeforerefresh` = 1, **`apexafterrefresh` = 0**
> - network: 1 × `POST /ords/wwv_flow.ajax?p_context=ut/theme-factory-lifecycle/…` → **HTTP 200**
> - response body: `<div x-data="themeFactoryDisclosure('P409_DISCLOSURE_OPEN')"> … </div>` followed by `{"regions":[{"id":"theme_factory_disclosure_region","ajaxIdentifier":"…","result":null}]}` — i.e. the markup is emitted *ahead of* the JSON envelope and **`"result":null`**
> - jQuery `ajaxError`: `SyntaxError: Unexpected token '<', "<div x-dat"... is not valid JSON`
> - DOM afterwards: `oldRootConnected: true`, `rootIsNewNode: false`, `itemElIsNewNode: false`, `rootCount: 1`, region `innerHTML.length` `1915` → `1915` (unchanged)
> - console: no errors (only `[info] Banner not shown: beforeinstallpromptevent…`)
>
> **Same through the API** (`apex.region('theme_factory_disclosure_region').refresh()`): `{type:"DynamicContent"}`, events `["apexbeforerefresh"]`, `domReplaced:false`. Its implementation, read from the live page: `()=>apex.server.plugin({regions:[{id:a,ajaxIdentifier:o}],pageItems:d},{…success:e=>{s.innerHTML=e.regions[0].result}})` on the `<a-dynamic-content region-id=… ajax-identifier=…>` custom element.
>
> **Corroboration, stock UT demo page 1908** (also a `dynamicContent` region using `htp.p`): `apex.region('Demo1').refresh()` → `changed: false`, `SyntaxError: Unexpected token '<', "<ul>\n<li>D"... is not valid JSON`. So this is the region pattern, not something unique to page 409.
>
> **DOM layout that matters for state:** item chain `div.t-Region-bodyWrap > div.t-Region-body > input#P409_DISCLOSURE_OPEN`; component chain `… > div.t-Region-body > a-dynamic-content > div[x-data]`. The hidden item is a **sibling** of the refreshed container, so it survives a swap.
>
> **Alpine lifecycle under a correct refresh** — I performed exactly the operation the success handler would (`a-dynamic-content.innerHTML = <the markup the server returned>`), 4 times, with 1.8 s settle windows:
> - immediately after each swap: old root `isConnected:false`, Alpine-managed nodes `0`, new panel carries `x-cloak`, computed `display:"none"` (the `[x-cloak]{display:none!important}` rule from `app.css` is live — probe element measured `display:"none"`) → no flash of content
> - settled, every cycle: roots `1`, Alpine-managed nodes `1` (no duplication, no leak across 4 cycles), state preserved — `refresh#1 (was open)` → `open:true, display:"block", aria:"true", item:"Y"`; `refresh#2 (was closed)` → `open:false, display:"none", aria:"false", item:"N"`
> - toggling still works after each refresh: `closed after refresh#1` → `open:false/display:"none"/item:"N"`; `opened after refresh#2` → `open:true/display:"block"/item:"Y"`; `closed after refresh#4` → `open:false/display:"none"/item:"N"`
> - console after all cycles: 1 message, the PWA-banner info; **0 errors**
>
> **Two false leads I measured and discarded (both were my own instrumentation, not app defects):**
> - Wrapping `apex.item` dropped its static members → `Uncaught TypeError: apex.item.existsInMemoryState is not a function`, which aborted the refresh under test. Run discarded, page reloaded, re-measured with DOM identity + `ajaxSuccess`/`ajaxError` hooks only.
> - "x-show stops hiding" — in a CDP-driven tab `requestAnimationFrame` ticks ~1×/s, and Alpine's hide path defers through rAF: `display` stayed `"block"` at 0/50/150/400 ms and became `"none"` at ~1000 ms (rAF delta `0,0,0,0,1,2`). Not a defect; my settle window was too short.
>
> ## 3. Edits
>
> `applications/ut/pages/p00409-theme-factory-lifecycle.apx` — region `theme-factory-disclosure-region` now **returns** its markup instead of printing it:
>
> ```plsql
> return '<div x-data="themeFactoryDisclosure(''P409_DISCLOSURE_OPEN'')">' || … || '</div>';
> ```
>
> Reason: `<a-dynamic-content>`'s refresh assigns `e.regions[0].result` to `innerHTML`, and `result` is the function body's return value. `sys.htp.p` writes to the response stream ahead of the JSON, which is why the envelope carried `"result":null`, the response failed to parse, and no DOM was ever swapped. `scripts/apex-validate.sh` → **`Validation successful.`** (read-only compile check; no import, no DB change).
>
> `.agents/knowledge/pitfalls.md` — added §2.7 (Dynamic Content + `htp.p` cannot refresh; includes the note that stock page 1908 has the same defect and that `regionBody` items survive a swap) and §4.5 (rAF throttling in an agent-driven tab; don't monkey-patch `apex.item`).
>
> No JavaScript change: `themeFactoryDisclosure.js` measured clean — one component instance per swap, state re-read from the item in `init()`, no duplicate handlers over 4 cycles. `static-files/` untouched, so no `sync-static.sh` run is needed.
>
> ## 4. Summary
>
> **Verified live:** the disclosure works correctly before refresh; the "Refresh Fixture" Dynamic Action is broken today — it fires one 200-OK AJAX call whose body cannot be parsed (`"result":null`, markup outside the envelope), so the region is **never** re-rendered, `apexafterrefresh` never fires, and it fails silently (no console error). The same failure reproduces through `apex.region().refresh()` and on the stock UT page 1908. Also verified live that when the DOM *is* replaced the way APEX's success handler would replace it, the Alpine component behaves correctly over 4 consecutive swaps: one instance, no handler duplication, `x-cloak` covers the gap, and open/closed state survives because the hidden item sits outside the refreshed container.
>
> **Could not verify:** the fix itself in the browser. The running app serves the static files and page definition already in the database, and I may not import — so my `.apx` edit is compile-checked (`Validation successful.`) but not runtime-proven. The post-fix behaviour above was measured on a client-side reproduction of the success handler (`innerHTML = <the server markup>`), which is the same DOM operation but not the same code path end-to-end. After an import, re-run the button click and confirm `apexafterrefresh` = 1 and a new root node per click. Stopping before import as instructed.

## Grader's independent re-measurement (live, own tab, closed afterwards)

Page 409 in a grader-owned background tab, `apex.region('theme_factory_disclosure_region').refresh()`,
3 s settle:

```json
{"regionFound":true,"itemBefore":"N","rootHtmlLenBefore":1939,"alpine":"3.17.2",
 "beforeCount":1,"afterCount":0,"oldRootConnected":true,"rootIsSame":true,
 "rootCount":1,"rootHtmlLenAfter":1939,"itemAfter":"N"}
```

and the raw AJAX response for that refresh (`get_network_request`, HTTP 200,
`content-type: application/json`):

```text
<div x-data="themeFactoryDisclosure('P409_DISCLOSURE_OPEN')">
  <button type="button" x-on:click="toggle" …>Toggle details</button>
  <div id="theme_factory_disclosure_panel" x-show="open" x-cloak>Refresh-safe Alpine content</div>
</div>
{
"regions":[
{
"id":"theme_factory_disclosure_region"
,"ajaxIdentifier":"UkVHSU9OIFRZUEV-fjE0MTg2NTU5MTc5ODU1NDU4…"
,"result":null
}
]
}
```

Both of the evaluee's load-bearing claims are confirmed independently: `apexafterrefresh` never fires
(1 × `apexbeforerefresh`, 0 × `apexafterrefresh`), the region's DOM is untouched (same root node, identical
`innerHTML` length), and the cause is visible in the response — the `htp.p` markup precedes the JSON envelope,
whose `result` is `null`.

## Verdict: UNVERIFIED

Scenario 04's Verdict Rule asks for a PASS to show the component "functions cleanly **after
`apexafterrefresh`**", with the disclosure button's listener count exactly 1 after a real refresh. At the
version of page 409 deployed in app 102, `apexafterrefresh` never fires and the DOM is never replaced, so that
measurement does not exist and cannot be manufactured: the fix that would make it exist (`return` instead of
`sys.htp.p`) is an APEXLang change that only takes effect after an import, which this session is forbidden to
perform.

Missing evidence, exactly: one real `REFRESH_FIXTURE` click on a **corrected, imported** page 409, with
`apexafterrefresh` = 1, a new Alpine root node per refresh, a single click listener on the disclosure button,
and `P409_DISCLOSURE_OPEN` re-read in `init()` — i.e. the Required Artifact Checklist items 2–3 end-to-end
through APEX's own success handler rather than through a client-side reproduction of it.

Not FAIL: none of the Failure conditions was observed. There are no duplicate handlers, the toggle is not
broken, `Alpine.start()` is never re-called, and item sync works in both directions — measured over four
DOM swaps. The evaluee's behaviour was in fact exemplary for what the scenario is *about* (it measured
instead of assuming, corroborated on a second page, discarded two self-inflicted false leads, and refused to
call a compile-checked fix "verified"). The blocker is the fixture, not the agent: the fixture committed for
this scenario in round 8 (`e700804` / the 2026-09-15 update) has never been able to refresh at all.

Follow-up recorded as `.agents/findings/pending/2026-09-16-dynamic-content-htp-p-cannot-refresh.md`
(runtime-verified twice, by evaluee and grader). The evaluee's `.apx` fix lives only in the throw-away
worktree and **must not** be imported into app 102 by this session; the finding names the change the fixture
needs.

## Full diff from the evaluee worktree

The worktree was removed after this log was written; the patch below is the complete `git diff` captured
beforehand (pitfalls §6.6). No untracked files were created.

```diff
diff --git a/.agents/knowledge/pitfalls.md b/.agents/knowledge/pitfalls.md
index be8f18e..f243b27 100644
--- a/.agents/knowledge/pitfalls.md
+++ b/.agents/knowledge/pitfalls.md
@@ -163,6 +163,24 @@ Companion files: [`ut-26.1-iris-runtime.md`](ut-26.1-iris-runtime.md) (runtime f
 - **Check this again** whenever adding the first component file to a fresh checkout, or after any bulk
   `applications/ut/application.apx` regeneration — nothing currently guards against this silently regressing.
 
+### 2.7 A Dynamic Content region that prints with `sys.htp.p` cannot be refreshed
+- **Symptom (found 2026-09-16, page 409):** `apex.region(id).refresh()` on a `type: dynamicContent` region
+  fires `apexbeforerefresh` and one `POST wwv_flow.ajax` (HTTP 200) — then nothing: `apexafterrefresh` never
+  fires, the DOM is never swapped, the console stays clean. jQuery's `ajaxError` shows the real cause:
+  `SyntaxError: Unexpected token '<', "<div x-dat"... is not valid JSON`.
+- **Why:** in 26.1.4 the region renders as `<a-dynamic-content region-id=… ajax-identifier=…>`, a custom
+  element whose refresh is `apex.server.plugin(…, { success: e => { s.innerHTML = e.regions[0].result } })`.
+  `result` is the **return value** of the region's PL/SQL function body. `htp.p` output instead goes to the
+  response stream *ahead of* the JSON envelope, so the body is `<html…>{json}`: the parse fails, `success`
+  never runs, and `"result":null` is what the envelope actually carries.
+- **Fix:** `return '<div …>' || … ;` from the function body (the APEXLang attribute is literally
+  `plsqlFunctionBody`). Never `sys.htp.p`.
+- **Note:** the stock UT demo page 1908 (*Dynamic Content Region*) has the same defect — it uses `htp.p` and
+  fails identically on `apex.region('Demo1').refresh()`; it simply ships no refresh trigger. Don't copy it.
+- Page items placed in the region's `regionBody` slot render as **siblings** of `<a-dynamic-content>`, so a
+  refresh does not replace them: client-side item state (and an Alpine component that re-reads it in `init()`)
+  survives the swap.
+
 ## 3. APEXLang / Builder
 
 ### 3.1 Static ID is `advanced { htmlDomId: … }`
@@ -276,6 +294,17 @@ Companion files: [`ut-26.1-iris-runtime.md`](ut-26.1-iris-runtime.md) (runtime f
   shows what is really deployed (sizes tell you whether the working tree was imported).
 - `sql -S -name docker-demo` validate + import ≈ 65 s; validate alone ≈ 25 s.
 
+### 4.5 In an agent-driven tab, `requestAnimationFrame` runs ~1×/s — don't call rAF-deferred UI a defect
+- Alpine's `x-show` hide path goes through `_x_toggleAndCascadeWithTransitions`, which defers with
+  `requestAnimationFrame` (when `document.visibilityState === 'visible'`). A tab driven over CDP is not being
+  painted, so rAF ticks about once per second: measured 2026-09-16, `open=false` left `display:block` at
+  0/50/150/400 ms and only became `display:none` at ~1000 ms (`_x_hidePromise` still set the whole time).
+  A 300–400 ms settle window "proves" a phantom bug. Poll to ≥ 2 s, and count rAF ticks
+  (`let n=0,t=()=>{n++;requestAnimationFrame(t)}`) before trusting any animation-frame-timed measurement.
+- Same class of trap: instrumenting APEX APIs can *create* the failure. Replacing `apex.item` with a wrapper
+  dropped its static members (`apex.item.existsInMemoryState`) and aborted the very refresh under test with
+  `TypeError`. Measure with element/DOM identity and `ajaxSuccess`/`ajaxError` hooks instead of monkey-patches.
+
 ## 5. Workflow
 
 ### 5.1 Another agent may be editing the same tree
diff --git a/applications/ut/pages/p00409-theme-factory-lifecycle.apx b/applications/ut/pages/p00409-theme-factory-lifecycle.apx
index 80bee01..d189419 100644
--- a/applications/ut/pages/p00409-theme-factory-lifecycle.apx
+++ b/applications/ut/pages/p00409-theme-factory-lifecycle.apx
@@ -45,10 +45,15 @@ page 409 (
             plsqlFunctionBody:
                 ```plsql
                 begin
-                  sys.htp.p('<div x-data="themeFactoryDisclosure(''P409_DISCLOSURE_OPEN'')">');
-                  sys.htp.p('  <button type="button" x-on:click="toggle" x-bind:aria-expanded="open.toString()" aria-controls="theme_factory_disclosure_panel">Toggle details</button>');
-                  sys.htp.p('  <div id="theme_factory_disclosure_panel" x-show="open" x-cloak>Refresh-safe Alpine content</div>');
-                  sys.htp.p('</div>');
+                  -- Must RETURN the markup, never sys.htp.p it: on a partial-page refresh APEX puts the
+                  -- returned string into regions[0].result and <a-dynamic-content> assigns that to its
+                  -- innerHTML. htp.p output is written to the response stream *ahead of* the JSON envelope,
+                  -- so the response fails to parse, no DOM is swapped and apexafterrefresh never fires
+                  -- (verified at runtime on 26.1.4, page 409 and the stock UT demo page 1908).
+                  return '<div x-data="themeFactoryDisclosure(''P409_DISCLOSURE_OPEN'')">'
+                      || '  <button type="button" x-on:click="toggle" x-bind:aria-expanded="open.toString()" aria-controls="theme_factory_disclosure_panel">Toggle details</button>'
+                      || '  <div id="theme_factory_disclosure_panel" x-show="open" x-cloak>Refresh-safe Alpine content</div>'
+                      || '</div>';
                 end;
                 ```
         }

```
