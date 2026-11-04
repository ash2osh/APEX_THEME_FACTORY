---
name: project-browser
description: Use when you need runtime truth from the running APEX app at localhost:8181 — DOM, generated classes, computed CSS, Iris token values, console errors, network failures, screenshots, responsive checks, or to prototype a CSS change — through the project browser daemon (Firefox by default)
---

# project-browser (project usage)

Reference: `docs/FIREFOX_DEVTOOLS_MCP.md` (Firefox, the default) and `docs/CHROME_DEVTOOLS_MCP.md` (Chrome, `THEME_FACTORY_BROWSER=chrome`).

## Connection facts
- Always through the project daemon, never a browser MCP tool directly: `python3 tools/browser_client.py <tool> '<json>'`, or `BrowserClient` in `tools/browser_client.py`. A direct call or a second daemon can raise a consent prompt the user may not be there to answer.
- The daemon owns one approved browser session: the user's Firefox, started from its launcher with the debugging port. Do not start another browser. Start the daemon only if it is not already running.
- Every page-scoped call takes a `pageId` from `list_pages`. The APEX tab's URL starts with `http://localhost:8181/ords/r/demo/ut/`. If it is missing, `new_page` with `{"url": ..., "background": true}`.

## Standard inspection sequence
```text
list_pages → navigate_page (url) → take_snapshot → evaluate_script → list_console_messages → take_screenshot
```

`evaluate_script` function shapes that answer spec questions:

| Question | `function` |
|---|---|
| Which app/page/theme am I on? | `() => ({...apex.env, body: document.body.className})` |
| Which region owns element X? | `() => { const r = document.querySelector('<sel>').closest('.t-Region,[id]'); return {id:r.id, cls:r.className}; }` |
| Which computed value is winning? | `() => getComputedStyle(document.querySelector('<sel>')).getPropertyValue('<prop>')` |
| What is an Iris token worth? | `() => getComputedStyle(document.documentElement).getPropertyValue('--ut-palette-primary')` |
| Region API state (IG/IR) | `() => apex.region('<static_id>').widget().interactiveGrid('getViews').grid.model.getTotalRecords()` |
| Force a region refresh to test lifecycle | `() => { apex.region('<static_id>').refresh(); return 'refreshed'; }` |

Prototype CSS by appending a `<style id="proto">` element; read the result; then delete it and move the rule to `static-files/css/`.

## Rules
- DevTools changes are never the deliverable (spec §14). Note prototypes in the response so the source step is not skipped.
- Treat any console error appearing after your change as a defect (spec §49).
- Compare target vs implementation at 1440 and 375 px (spec §45, §73). Firefox cannot shrink its window below about 500 px, so do not use `emulate` or `resize_page` for 375. Measure a phone width in the frame (`tools/phone_frame.py`, see `docs/FIREFOX_DEVTOOLS_MCP.md`), or run `tools/page_audit.py --widths 1440,375`.
- Own tab (`new_page` with `background: true`). Never put `#theme=` in the URL (it shares localStorage). Close the tab when you finish.
- Before declaring a restyle done, run the contrast audit snippet from `docs/CHROME_DEVTOOLS_MCP.md` on the standard page list (`.agents/knowledge/pitfalls.md` §4.3).
- Screenshots go to the scratchpad; do not commit them.

## Common mistakes
- Passing a selector without `pageId` → `Required at pageId`.
- Reading `--a-*` on `:root`. Most are component-scoped, so read on the element.
- Inspecting the Builder tab (`/ords/r/apex/…`) instead of the app tab.
- Synthetic `element.click()` on APEX menu items. Use the daemon's `click` with a uid instead. Rule finders must also read custom-property-only rules and `@import`ed sheets (`pitfalls.md` §1.9).
