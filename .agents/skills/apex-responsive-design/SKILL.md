---
name: apex-responsive-design
description: Use when verifying tablet and mobile behaviour after any layout or component change, when a design only shows desktop, or when there is horizontal overflow, clipped content, wrapping buttons or unusable tables
---

# apex-responsive-design

## Core principle
Desktop-only targets still ship on phones (spec §45). Universal Theme's responsive grid is the base; app CSS must not break it.

## Check at 1440 · 1024 · 768 · 375 (`resize_page`)
- `document.documentElement.scrollWidth > innerWidth` → horizontal overflow (find with `[...document.querySelectorAll('*')].filter(e => e.getBoundingClientRect().right > innerWidth)`).
- Grid columns stack (UT `col-*` at < 640 px); custom `.app-*` grids need `@media (max-width: 640px)` fallbacks.
- IG/IR: horizontal scroll inside the region only; IR "stretch" template option; column widths.
- Dialogs ≤ viewport (`apex.navigation.dialog` width/maxWidth in the DA/URL).
- Buttons wrap gracefully; touch targets ≥ 44 px; side nav collapses (`js-navCollapsed--hidden`).

## Preferences
- `minmax()`/`auto-fit` grids with `--app-space-*` gaps over fixed widths.
- Hide with template option "Hide on mobile" or UT utility classes only after verifying they exist in 26.1.

## Common mistakes
- Fixed `width: 320px` on cards.
- Testing only with the side nav expanded.
