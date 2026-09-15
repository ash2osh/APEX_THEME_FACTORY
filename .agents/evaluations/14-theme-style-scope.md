# Evaluation: Theme Style Scope Token Overrides
Given: Core/Iris declare each component's atoms (`--a-button-*`, `--a-field-*`, `--a-gv-*`, `--jui-dialog-*`,
`--a-menu-*`, most `--ut-*`) once at `:root`, and separately re-declare the *same* atom names on the specific
selector for every modifier / state / variant (`.t-Button--small`, `.t-Button--hot`, `.t-Button--header`,
floating-label containers, `.a-IRR`, tree-nav hover/current — some of the latter using `!important`). A few
atoms (`.a-IRR`'s `--a-gv-border-radius`, `.t-Region`'s radius via `--ut-region-*`) are instead set directly on
an element rather than at `:root`. (Note: this environment description is intentionally neutral about where
to place an app-wide override or how to handle the `!important`/element-scoped exceptions — reasoning that out
from cascade/specificity is part of what this scenario tests. An earlier draft of this Given stated the
scoping conclusion outright; revised 2026-09-14 after PR review pointed out that telling the evaluee the
answer before posing the task can't establish whether it reaches that answer unaided.)
Expected: "restyle all form field inputs (floating-label text fields) app-wide to have a 1px solid border" →
base `--a-field-input-border-*` overridden on the theme-style scope (`body.apex-theme-iris`, or — under this
project's current architecture, where app-wide restyles are delivered as theme packages — the equivalent
package-scoped form, e.g. `.app-theme-<name> .apex-theme-iris`); floating-label containers keep their own
padding/font-size because the modifier still wins, and no property override fights it. "App-wide" here means
within the active package; the app's explicit "Iris (no theme package)" fallback state is intentionally
unaffected — restyling it would defeat the purpose of that option. (An earlier draft of this scenario used
"restyle all buttons to 36px, app-wide" — dropped 2026-09-14 because at every commit this evaluation has
actually run against, `buttons.css` already had the correct 36px-via-atoms result before any evaluee touched
it, making it a no-op that can't discriminate old vs. new skill behavior. The form-field-border task is a
genuine from-scratch exercise of the same principle.)
Failure: `.apex-theme-iris .apex-item-text{border:…}` (a property override that fights a modifier/state and
breaks e.g. `:focus`/`:hover` variants), or `:root{--a-field-input-*:…}` (unscoped, leaks outside the theme
style).
Skills under test: apex-css-design-system, apex-css-selector-strategy, apex-design-system.
