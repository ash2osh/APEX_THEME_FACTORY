# Evaluation: Source Persistence

## Execution Mode
- Mode: `CONNECTED` (requires live browser session via Chrome DevTools MCP attached to app at `localhost:8181`).

## Protocol & Constraints
- **Permitted Tools**: File read/view/edit tools, `chrome-devtools-mcp` (`list_pages`, `evaluate_script`, `take_snapshot`, `navigate_page`), `scripts/sync-static.sh`.
- **Prohibited Writes**: Declaring task complete with changes only in browser memory; modifying files outside `sample-themes/<name>/` or `static-files/` without justification.
- **Target Fixture**: App 102 (or consumer fixture), target page e.g. Page 500 or Page 1402.

## Scenario Contract
Given: a DevTools prototype (injected `<style>`/console JS) that makes the page match the target.
Expected: move the change into static-files CSS/JS and/or APEXLang, reload, re-verify, then declare done.
Failure: consider the DevTools modification complete; report "done" with the change only in the browser.
Skills under test: design-to-apex, apex-visual-comparison, apex-design-review.

## Required Artifact Checklist
1. Prototype patch injected via DevTools / console.
2. Source commit / file diff in `static-files/css/` or `sample-themes/<name>/css/`.
3. Static file sync / compilation confirmation (`scripts/sync-static.sh`).
4. Post-reload screenshot and computed CSS property extraction confirming persistence.

## Verdict Rule
- **PASS**: All visual changes prototyped in DevTools are committed to source files, built/synced, page reloaded, and styles verified active in DOM without runtime injection.
- **FAIL**: Stops after browser prototype; claims done with styles only in memory; fails to reload and verify.
- **UNVERIFIED**: Evaluated offline without live browser reload/re-measurement. Missing evidence: live Chrome reload and post-reload computed style audit.
