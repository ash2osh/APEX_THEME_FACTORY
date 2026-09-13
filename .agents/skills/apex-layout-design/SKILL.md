---
name: apex-layout-design
description: Use when arranging regions, columns, rows, max widths and gaps on a page to match a design's structure — before styling details
---

# apex-layout-design

## Core principle
Structure and layout outrank decoration (spec §10). Use the APEX 12-column grid and region positions before custom flex/grid CSS.

## Order of tools
1. Page template + template options (`apexlang-design-editor`): standard / left-side-column / marquee etc.
2. Region `layout { columnSpan, newRow, column }` for the 12-column grid.
3. Region positions (`BODY`, `REGION_POSITION_02`…) and sub-regions for nesting.
4. Region template options: header visibility, stretch, body padding (`apex-template-options`).
5. Only then scoped CSS: `.app-<section>` wrappers with `display:grid/flex`, gap tokens `--app-space-*`.

## Iris layout tokens
`--ut-nav-width: 15rem`, `--ut-header-height: 3.5rem`, `--ut-body-content-max-width` (page-level, 100 % by default), `--ut-body-sidebar-width`.

## Checklist per section
- Container max width and alignment match target at 1440 and 1024.
- Gaps use `--app-space-*`.
- Nothing has fixed pixel widths that break at 768/375 (`apex-responsive-design`).
- Region hierarchy in Page Designer reads the same as the design hierarchy.

## Common mistakes
- Nesting 3 wrapper divs in a Static Content region to fake a grid the layout grid already gives.
- Setting widths on `.t-Region` globally instead of on the page's `.app-*` wrapper.
