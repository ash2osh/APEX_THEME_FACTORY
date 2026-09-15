# Evaluation: APEX Refresh

## Execution Mode
- Mode: `CONNECTED` (requires live browser session via Chrome DevTools MCP attached to app at `localhost:8181`).

## Protocol & Constraints
- **Permitted Tools**: File read/view/edit tools, `chrome-devtools-mcp` (`list_pages`, `evaluate_script`, `take_snapshot`, `click_element`), `bash` (read-only scripts).
- **Prohibited Writes**: No importing unapproved applications; no modifying production files without recording diffs; no calling `Alpine.start()`.
- **Target Fixture**: App 102, Page 409 (`applications/ut/pages/p00409-theme-factory-lifecycle.apx`), component `static-files/js/components/themeFactoryDisclosure.js`, region `theme_factory_disclosure_region`, trigger item `P409_DISCLOSURE_OPEN`, button `REFRESH_FIXTURE`.

## Scenario Contract
Given: an Alpine component inside a region that is refreshed by a Dynamic Action (`REFRESH_FIXTURE` triggering `apex.region('theme_factory_disclosure_region').refresh()`).
Expected: component works after `apexafterrefresh`; no duplicate handlers; no `Alpine.start()` re-call; state re-synced from the APEX item `P409_DISCLOSURE_OPEN`.
Failure: duplicate handlers, broken state, repeated Alpine startup, stale DOM references.
Skills under test: apex-alpine-lifecycle.

## Required Artifact Checklist
1. Pre-refresh DOM snapshot & item state (`$v('P409_DISCLOSURE_OPEN')`).
2. Refresh execution log (`apex.region('theme_factory_disclosure_region').refresh()`).
3. Post-refresh DOM snapshot, event listener count check (no duplicates), click interaction verification, and item sync verification.
4. Chrome evidence JSON conforming to `tests/live/runtime-evidence.schema.json`.

## Verdict Rule
- **PASS**: Component functions cleanly after `apexafterrefresh`; click toggles open state; `P409_DISCLOSURE_OPEN` syncs bidirectionally; listener count on disclosure button is exactly 1 (no duplicate handlers); `Alpine.start()` is never re-called.
- **FAIL**: Duplicate event handlers registered on DOM nodes, broken disclosure toggle, `Alpine.start()` executed, or failure to sync with `P409_DISCLOSURE_OPEN`.
- **UNVERIFIED**: Evaluated offline or without live Chrome session on Page 409. Missing evidence: live DevTools interaction and listener counts after APEX region refresh.
