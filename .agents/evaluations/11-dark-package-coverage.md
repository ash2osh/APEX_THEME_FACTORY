# Evaluation: Dark Package Coverage
Given: a dark theme package on Iris (light-only style) is declared "done" after checking pages 500 and 1402.
Expected: Iris' literal `:root` tokens and the widget-CSS fallbacks are remapped (`pitfalls.md` §1.1–1.4), the
reference app's demo surfaces (p4000, p6303, p6304) are restated, and the contrast audit
(`docs/CHROME_DEVTOOLS_MCP.md`) reports 0 package failures on the standard page list before the README's
*Verified* section is written.
Failure: white-on-white doc tables or search panels, a white IG footer / `#e0e0e0` pager, dark-on-dark radio
labels, ratios asserted without measurement.
Skills under test: apex-css-design-system, apex-accessibility, apex-design-review, chrome-devtools-mcp.
