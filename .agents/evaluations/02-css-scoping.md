# Evaluation: CSS Scoping
Given: one region on one page must look different.
Expected: semantic `.app-*` class or Static ID selector; `.app-x .t-Region-*` for UT internals.
Failure: global `.t-Region { … }` override, or `!important` to win the cascade.
Skills under test: apex-css-selector-strategy, apex-css-design-system.
