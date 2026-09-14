# Evaluation: Theme Style Scope Token Overrides
Given: Core/Iris declare the *base* component atoms (`--a-button-*`, `--a-field-*`, `--a-gv-*`, `--jui-dialog-*`,
`--a-menu-*`, most `--ut-*`) on `:root`, and every modifier / state / variant sets the same atoms on the element
(`.t-Button--small`, `.t-Button--hot`, `.t-Button--header`, floating-label containers, `.a-IRR`). Overriding the
base atoms on `body.apex-theme-iris` restyles every instance while all modifiers keep precedence, with zero
`:not()` chains and no property fights. The remaining exceptions are atoms set on an element
(`.a-IRR{--a-gv-border-radius}`, `.t-Region` radius via `--ut-region-*`) — override on that element — and Iris
rules that carry `!important` (tree-nav hover/current) — mirror the `!important` with a comment.
Expected: "restyle all form field inputs (floating-label text fields) app-wide to have a 1px solid border" →
base `--a-field-input-border-*` overridden on `body.apex-theme-iris` (theme-style scope); floating-label
containers keep their own padding/font-size because the modifier still wins, and no property override fights
it. (An earlier draft of this scenario used "restyle all buttons to 36px, app-wide" — dropped 2026-09-14
because at every commit this evaluation has actually run against, `buttons.css` already had the correct
36px-via-atoms result before any evaluee touched it, making it a no-op that can't discriminate old vs. new
skill behavior. The form-field-border task is a genuine from-scratch exercise of the same principle.)
Failure: `.apex-theme-iris .apex-item-text{border:…}` (a property override that fights a modifier/state and
breaks e.g. `:focus`/`:hover` variants), or `:root{--a-field-input-*:…}` (unscoped, leaks outside the theme
style).
Skills under test: apex-css-design-system, apex-css-selector-strategy, apex-design-system.
