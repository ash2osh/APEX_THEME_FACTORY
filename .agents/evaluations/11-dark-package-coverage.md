# Evaluation: Dark Package Coverage

## Execution Mode
- Mode: `CONNECTED` (requires live browser session via Chrome DevTools MCP attached to app at `localhost:8181`).

## Protocol & Constraints
- **Permitted Tools**: `chrome-devtools-mcp` (through `tools/chrome_devtools_client.py`), file reading/editing tools.
- **Prohibited Writes**: Marking package "Verified" without full live contrast audit; modifying core Iris tokens outside `.app-theme-<name>` scope.
- **Target Fixture**:
  - App 102 pages: 500 (Dashboard), 1402 (Interactive Report), 1410 (Interactive Grid), 1411 (Faceted Search), 1601 (Markdown/Percent), 1800 (Calendar), 1902 (JET Chart), 4000 (Buttons & Controls), 6303, 6304.
  - Consumer fixtures: Minimal (`9010`) and Business (`9011`) across viewports 1440, 1024, 768, 375 (per `tests/live/RELEASE-MATRIX.md`).

## Scenario Contract
Given: a dark theme package on Iris (light-only style) is declared "done" after checking pages 500 and 1402.
Expected: Iris' literal `:root` tokens and the widget-CSS fallbacks are remapped (`pitfalls.md` §1.1–1.4), the
reference app's demo surfaces (p4000, p6303, p6304) are restated, and the contrast audit
(`docs/CHROME_DEVTOOLS_MCP.md`) reports 0 package failures on the standard page list before the README's
*Verified* section is written.
Failure: white-on-white doc tables or search panels, a white IG footer / `#e0e0e0` pager, dark-on-dark radio
labels, ratios asserted without measurement.
Skills under test: apex-css-design-system, apex-accessibility, apex-design-review, chrome-devtools-mcp.

## Required Artifact Checklist
1. WCAG AA contrast audit JSON / table across all test surfaces.
2. Browser parity evidence JSON conforming to `tests/live/runtime-evidence.schema.json`.
3. Screenshot captures of all dark surfaces (IG, IRR, Faceted Search, Dialog, Navigation).
4. Bare-Iris comparison audit distinguishing APEX baseline defects from theme package regressions.

## Verdict Rule
- **PASS**: 0 package-caused WCAG AA contrast failures across all tested surfaces; all literal `:root` tokens remapped under `html.app-theme-solarized-dark`; bare-Iris baseline defects separated and documented.
- **FAIL**: Unremapped light surfaces, dark-on-dark text, unmeasured contrast ratios, or declaring "Verified" without live Chrome contrast audit evidence.
- **UNVERIFIED**: Evaluated offline or without live Chrome multi-page contrast audit. Missing evidence: live Chrome WCAG AA contrast audit results across the full release matrix.
