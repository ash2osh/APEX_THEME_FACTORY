---
name: chrome-devtools-mcp
description: Use when you need runtime truth from the running APEX app at localhost:8181 — DOM, generated classes, computed CSS, Iris token values, console errors, network failures, screenshots, responsive checks, or to prototype a CSS change — via the chrome-devtools MCP server attached to the user's running Chrome
---

# chrome-devtools-mcp (project usage)

Reference: `docs/CHROME_DEVTOOLS_MCP.md` (install, connection, troubleshooting).

## Connection facts
- Server name: `chrome-devtools` (Claude, Codex) / `chrome-devtools-mcp` (Antigravity), started with `--autoConnect`.
- It attaches to the **user's running Chrome** (remote-debugging toggle enabled). The first call may take 20–40 s. Do not launch another Chrome.
- Every page-scoped tool needs `pageId` from `list_pages`. The APEX tab is the one whose URL starts with `http://localhost:8181/ords/r/demo/ut/`. If it is missing, `new_page` with that URL.

## Standard inspection sequence
```text
list_pages → (navigate_page url|reload) → take_snapshot → evaluate_script → list_console_messages → take_screenshot
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
- Compare target vs implementation at the same viewport (`emulate viewport`, per tab — not `resize_page`, which resizes the user's window), at 1440 / 1024 / 768 / 375 (spec §45, §73).
- Own tab (`new_page … background:true`), never `#theme=` in the URL (shared localStorage), close the tab at the end — `docs/CHROME_DEVTOOLS_MCP.md`, *etiquette*.
- Before declaring a restyle done: run the **contrast audit** snippet from `docs/CHROME_DEVTOOLS_MCP.md` on the standard page list (`.agents/knowledge/pitfalls.md` §4.3).
- Screenshots go to the scratchpad; do not commit them.

## Common mistakes
- Passing a selector without `pageId` → `Required at pageId`.
- Reading `--a-*` on `:root` — most are component-scoped; read on the element.
- Inspecting the Builder tab (`/ords/r/apex/…`) instead of the app tab.
- Synthetic `element.click()` on APEX menu items (use `click uid`); rule finders that ignore custom-property-only rules and `@import`ed sheets (`pitfalls.md` §1.9).
