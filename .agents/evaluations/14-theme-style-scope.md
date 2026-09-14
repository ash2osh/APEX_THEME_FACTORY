# Evaluation: Theme Style Scope Token Overrides
Given: Core/Iris declare the *base* component atoms (`--a-button-*`, `--a-field-*`, `--a-gv-*`, `--jui-dialog-*`,
`--a-menu-*`, most `--ut-*`) on `:root`, and every modifier / state / variant sets the same atoms on the element
(`.t-Button--small`, `.t-Button--hot`, `.t-Button--header`, floating-label containers, `.a-IRR`). Overriding the
base atoms on `body.apex-theme-iris` restyles every instance while all modifiers keep precedence, with zero
`:not()` chains and no property fights. The remaining exceptions are atoms set on an element
(`.a-IRR{--a-gv-border-radius}`, `.t-Region` radius via `--ut-region-*`) — override on that element — and Iris
rules that carry `!important` (tree-nav hover/current) — mirror the `!important` with a comment.
Expected: "restyle all buttons to 36px, app-wide" → base `--a-button-*` overridden on `body.apex-theme-iris`
(theme-style scope); `.t-Button--small` keeps its own size because the modifier still wins.
Failure: `.apex-theme-iris .t-Button{padding:…}` (a property override that fights the modifier and breaks
`.t-Button--small`), or `:root{--a-button-*:…}` (unscoped, leaks outside the theme style).
Skills under test: apex-css-design-system, apex-css-selector-strategy, apex-design-system.
