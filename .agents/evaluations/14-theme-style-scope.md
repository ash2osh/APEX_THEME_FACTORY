# Evaluation: Theme Style Scope Token Overrides

## Execution Mode
- Mode: `OFFLINE` or `CONNECTED` (recorded per run).
  - `OFFLINE`: Do not connect to Oracle and do not run `scripts/apex-validate.sh`; source checks remain UNVERIFIED for compilation.
  - `CONNECTED`: You may run `scripts/apex-validate.sh` using `docker-demo`; do not import or make database changes.

## Protocol & Constraints
- **Permitted Tools**: File search and editing tools; for `CONNECTED` mode, `scripts/apex-validate.sh`.
- **Prohibited Writes**: No writing unscoped `:root` token overrides; no direct element property overrides fighting UT modifiers.
- **Target Fixture**: App 102 (or consumer business fixture Form page), neutral prompt: "restyle all form field inputs (floating-label text fields) within the active theme package to have a 1px solid border". The prompt MUST NOT supply the scoping rule or mention `body.apex-theme-iris` in the Given.

## Scenario Contract
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

## Required Artifact Checklist
1. Exact evaluee prompt text verifying neutral Given.
2. Git diff of the proposed CSS changes in `sample-themes/<name>/css/apex/forms.css`.
3. Selector specificity and cascade analysis report.
4. Validation output (`scripts/apex-validate.sh` if in `CONNECTED` mode).

## Verdict Rule
- **PASS**: Agent overrides base atom `--a-field-input-border-*` under `.app-theme-<name> .apex-theme-iris` (or `body.apex-theme-iris` for app-wide Iris style scope); does NOT use direct element property overrides that break focus/hover/modifier states; does NOT declare tokens at `:root`.
- **FAIL**: Overrides property directly (`.apex-item-text { border: ... }`) or declares overrides at `:root`.
- **UNVERIFIED**: Task tested with mismatched tasks between baseline/current, or with a non-neutral Given that provides the scoping solution. Missing evidence: fresh matched neutral-prompt comparison run.
