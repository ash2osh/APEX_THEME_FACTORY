# Pitfalls §4 — Tooling (Chrome DevTools MCP, SQLcl)

Part of the [pitfalls index](../pitfalls.md); entry numbers are stable and cited as `pitfalls §4.N`.

## 4. Tooling (Chrome DevTools MCP, SQLcl)

### 4.1 Shared browser state
- Every APEX tab shares `localStorage['app.theme']`: navigating *your* tab to `…#theme=x` rewrites the theme
  for the user's other tabs on their next reload. For captures swap the class in the DOM
  (`document.documentElement.className = … 'app-theme-x'`) instead.
- `resize_page` resizes the **shared Chrome window**; use `emulate {viewport:'1440x900x1'}` (per tab).
- Work in your own tab (`new_page … background:true`), hide `#apexDevToolbar` with a `<style>` for captures,
  close the tab when done.

### 4.2 Same-document hash navigation does not reload
- `navigate_page` to the current URL + `#theme=…` is a hash change; the page-0 bootstrap does not run.
  `App.theme.use()` therefore reloads explicitly (and strips a stale `#theme=` first, because page 0 would
  re-apply it).

### 4.3 The contrast audit finds what screenshots miss
- The 40-line `evaluate_script` in `docs/CHROME_DEVTOOLS_MCP.md` (every visible text node vs its blended
  background, AA thresholds) caught dark-on-dark radio labels, a white IG footer, unreadable Prism tokens and
  white doc tables that looked "fine" at thumbnail size. Run it on the standard page list
  (500, 1201, 1202, 1208, 1304, 1402, 1410, 1500, 1600, 1910/1912, 3110, 4000, 6303, 6304, 405) before
  calling a package verified. Exclusions: `#apexDevToolbar`, hidden nodes; expect Universal Theme's own
  `u-color-*` demo fills (p1304) to fail under any style.
- It only samples nodes present (and visible) at rest, on page load. It missed two Solarized Dark failures that
  only exist on `:hover` (IR/IG toolbar control labels — Iris sets the hover-background atom directly on the
  type-specific `.a-IG-controls-item--*` element, pale, outranking the body-level mapping) and `:empty:before`
  (page 4000's "No Results" state, only rendered once a search returns nothing) — caught instead by PR review
  (2026-09-14, `chatgpt-codex-connector`). Before calling a package verified, also drive the interactive states
  the static audit can't see: hover every toolbar/report control, and empty a search box.

### 4.3b The contrast audit's `bgOf()` used to double-composite `<body>`'s own background
- **Symptom (fixed 2026-09-14, PR review on #3):** a lone 50%-alpha `<body>` background composited to
  `rgb(64,64,64)` instead of the correct `rgb(128,128,128)` — roughly 10.4:1 instead of the real ~4:1, a false
  clean result that could hide a real near-failure.
- **Cause:** the ancestor walk already includes `document.body` (loop condition only excludes
  `document.documentElement`), but the old code then re-read and re-composited `document.body`'s background a
  second time as the "page background" backdrop — while never reading `document.documentElement`'s own
  background at all.
- **Fix:** after the loop, composite `acc` once over `document.documentElement`'s background (if any, else
  white) — not over `document.body`'s again. Sanity-check both cases before trusting a re-derived copy of this
  script: 50% red / 50% blue / white → `rgb(191,64,128)`; lone 50% black on `<body>` over an unstyled canvas →
  `rgb(128,128,128)`.

### 4.3d "0 failures" is not evidence unless the scan says how many nodes it scanned
- **Two ways a contrast sweep reports clean while the page is broken, both met in this project:**
  1. *The instrument can't see the nodes.* The documented audit walked text nodes and read CSS `color`. Oracle
     JET paints SVG text with `fill`, and `<text>` is not reached usefully by a body text-node walk — so
     p1902, with **24 of 25** chart labels at 1.46–1.62:1, reported **clean** on every pass before 2026-09-17.
     Fixed by querying `svg text, svg tspan` explicitly and scoring `fill`
     (`tools/browser_matrix.py::_contrast_function`, regression test
     `tests/test_browser_matrix.py::ContrastInstrumentTests`).
  2. *The scan ran somewhere else.* A probe pointed at the wrong tab/page returns `{svgTextNodes: 0,
     failures: 0}` — **byte-identical in shape to a genuine pass**. Hit live on 2026-09-17: a chart probe ran
     against the previous page because the tab had moved on.
- **Rule:** every audit result must carry the population it examined (`svgTextNodes`, node count, page id,
  `document.documentElement.className`), and a claim about a component must assert that count is non-zero for
  *that* component. `failures: 0` alone is not falsifiable and must not be quoted as evidence.
- Corollary for verdicts: when a scenario's PASS depends on an instrument, the instrument needs its own test.
  Fixing the blind spot **before** the re-sweep is what let p1902 fail honestly rather than read as clean.

### 4.3c A second `chrome-devtools-mcp --autoConnect` may never answer
- When another instance already holds the Chrome connection (or Chrome is showing the consent prompt),
  `tools/call` requests simply never return. The daemon now times out per request
  (`THEME_FACTORY_CHROME_MCP_TIMEOUT`, default 60 s) and keeps serving; before 2026-09-16 the first
  such call held the lock forever and every client hung. Use the daemon that owns the approved session
  (`THEME_FACTORY_CHROME_MCP_SOCKET=…`) instead of starting a second one.

### 4.4 SQLcl / DB
- `apex_application_theme_styles` lists the six Iris/Vita/Redwood rows; `apex_application_static_files`
  shows what is really deployed (sizes tell you whether the working tree was imported).
- `sql -S -name docker-demo` validate + import ≈ 65 s; validate alone ≈ 25 s.
- `whenever sqlerror exit failure` does **not** stop a script after a failed `apex validate` (probe
  2026-09-23: a deliberately broken page produced three `APEXlang Compile Errors`, the next statement still
  ran, `sql` exited 0). Anything after validate in the same script — an `apex import` — would run. Imports
  therefore run a separate, text-checked validate first (`scripts/apex-validate.sh` greps
  `Validation successful`; `SqlclClient.validate` requires validation/success text), then validate + import
  in one session. Cost: ~25 s per import.

### 4.5 In an agent-driven tab, `requestAnimationFrame` runs ~1×/s — don't call rAF-deferred UI a defect
- Alpine's `x-show` hide path goes through `_x_toggleAndCascadeWithTransitions`, which defers with
  `requestAnimationFrame` (when `document.visibilityState === 'visible'`). A tab driven over CDP is not being
  painted, so rAF ticks about once per second: measured 2026-09-16, `open=false` left `display:block` at
  0/50/150/400 ms and only became `display:none` at ~1000 ms (`_x_hidePromise` still set the whole time).
  A 300–400 ms settle window "proves" a phantom bug. Poll to ≥ 2 s, and count rAF ticks
  (`let n=0,t=()=>{n++;requestAnimationFrame(t)}`) before trusting any animation-frame-timed measurement.
- Same class of trap: instrumenting APEX APIs can *create* the failure. Replacing `apex.item` with a wrapper
  dropped its static members (`apex.item.existsInMemoryState`) and aborted the very refresh under test with
  `TypeError`. Measure with element/DOM identity and `ajaxSuccess`/`ajaxError` hooks instead of monkey-patches.

### 4.6 A `@font-face` is only downloaded when something renders text in it
- A declared face that no captured page uses is indistinguishable, to a naive probe, from a face that is
  missing: `document.fonts.check()` is false and no `performance` resource entry exists, because the browser
  never fetched it. Met 2026-09-17 on `solarized-dark`, which declares an IBM Plex Mono face: no consumer page
  renders monospace text, so `mono/400` came back `check: false` with an empty `requestUrl` on all 12 Layer D
  rows, and `heading/700` failed on every page except the one business page that renders a 700-weight heading.
  The package was correct throughout — `--app-font-family-mono` resolved to `"ThemeFactory-solarized-dark-mono",
  ui-monospace, monospace`, the WOFF2 was registered and served, and a forced load fetched it from
  `.../solarized-dark/1.1.0/fonts/ibm-plex-mono-regular.woff2` in ~20 ms.
- **Force the face, then judge that.** `await document.fonts.load('<weight> <style> 16px "<family>"', 'Ag0')`
  and require every returned `FontFace` to report `status === 'loaded'`. That answers the question the evidence
  actually claims — *is this face installed and usable from the package* — instead of *did this page happen to
  use it*. `tools/browser_matrix.py::page_snippet()` does this since `c88ce9d`.
- **Read `performance.getEntriesByType('resource')` after the forced loads, never before.** The request only
  exists once the load is forced, and `requestUrl` is what stops `document.fonts.check()` passing on a
  system fallback with the same name. Order matters: probe, then harvest.
- The inverse failure is worth naming too. A check can be wrong in the *pessimistic* direction, and that is
  still a defect — it cost a 50-minute re-capture and briefly looked like a broken theme. "The gate said no"
  is not the same as "the artifact is bad": confirm which, live, before changing either one.
