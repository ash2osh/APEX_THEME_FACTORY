# UT 26.1 / Iris DOM — reports (IRR, IG, classic)

Confidence: HIGH (p1402 IR, p1410 IG), verified 2026-09-13 via CSSOM walk + computed styles.

## Shared atom family
IRR (`.a-IRR`) and IG (`.a-IG` / `.a-GV`) cells are painted from the **same `--a-gv-*` atoms** declared on `:root`:
`--a-gv-header-background-color` (#fff in Iris, but `.a-IRR-header{background:#fafafa}` is hard-coded on top),
`--a-gv-header-cell-height` (2.5rem), `-font-size`, `-font-weight`, `-border-color` (#e6e6e6), `-padding-x/y`,
`--a-gv-cell-height` (2rem), `--a-gv-cell-border-color`, `-padding-x/y`, `--a-gv-font-size` (.75rem),
`--a-gv-row-hover-background-color`, `--a-gv-border-color/-radius`, `--a-gv-footer-*`, `--a-gv-pagination-button-*`.
Exception: `.a-IRR { --a-gv-border-radius:.125rem; --a-gv-cell-padding-y:.5rem; --a-gv-cell-padding-x:.75rem }` is
set **on the element** → override there. `.a-IG` has no radius rule at all (region provides it).
Cell borders: `border-width: var(--a-gv-cell-border-width,1px)` — one value for all sides, so vertical rules
need a property override (`border-inline-width: 0`).
Classic report: `.t-Report-colHead` / `.t-Report-cell` use `--ut-report-header-cell-*` / `--ut-report-cell-*`
with `--a-gv-*` fallbacks; template option `t-Report--horizontalBorders` exists for the same effect declaratively.

## Markup (IRR)
```
div.a-IRR#<id>_worksheet_region
  .a-IRR-fullView > .a-IRR-toolbar#<id>_toolbar > .a-IRR-controls > .a-IRR-controlGroup--search
      button.a-Button.a-IRR-button.a-IRR-button--colSearch · input.a-IRR-search-field · button.a-IRR-button--search
    .a-IRR-tableContainer > table.a-IRR-table > thead th.a-IRR-header > a.a-IRR-headerLink · tbody td
    ul.a-IRR-pagination
```
IRR toolbar: `--a-toolbar-*`, controls `--a-report-controls-*` (inputs .75rem, radius .25rem).
Markup (IG): `div.a-IG > .a-IG-toolbar? > .a-IG-gridView > table … th.a-GV-header > .a-GV-headerLabel, td.a-GV-cell, tr.a-GV-row`.
Sticky header: `.js-stickyTableHeader.is-stuck` gets a 1px box-shadow (`--a-gv-header-cell-border-*`).
API check used: `apex.jQuery('.a-IG').interactiveGrid('getActions').invoke('refresh')` → model row count unchanged (73).
