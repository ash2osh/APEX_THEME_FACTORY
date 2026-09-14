# Finding

Status:
Pending — evaluation 14 run 2026-09-14 (see evaluations/runs/2026-09-14/14-theme-style-scope-{baseline,current}.md): PASS at both baseline and current, so not promoted. The baseline run's first task (restyle buttons to 36px) was a no-op — `static-files/css/apex/buttons.css` already used the correct atom-on-theme-style-scope pattern before this knowledge was ever written down (committed at `e5fd54a`, predating the finding), so it wasn't a real test of the skill text; the current run used a fresh task (form-field borders) and also passed cleanly. The convention itself is sound and worth keeping documented, but no run has yet caught the *old* instructions actually failing it — re-run with a task where no sibling file already demonstrates the pattern, or once a genuine pre-finding-era regression surfaces.

Category:
APPLICATION-CONVENTION

Confidence:
CONFIRMED

APEX Version:
26.1.4 (Universal Theme / Iris)

Page:
app 102 pages 500, 1201, 1402, 1410, 1500, 1600, 1910 (app-wide)

Component:
`body.apex-theme-iris` scope; `--ut-*`, `--a-*`, `--jui-*` atoms

## Observation

Core/Iris declare the *base* component atoms (`--a-button-*`, `--a-field-*`, `--a-gv-*`, `--jui-dialog-*`,
`--a-menu-*`, most `--ut-*`) on `:root`, and every modifier / state / variant sets the same atoms on the
element (`.t-Button--small`, `.t-Button--hot`, `.t-Button--header`, floating-label containers, `.a-IRR`).
Overriding the base atoms on `body.apex-theme-iris` restyles every instance while all modifiers keep
precedence, with zero `:not()` chains and no property fights. The remaining exceptions are atoms set on an
element (`.a-IRR{--a-gv-border-radius}`, `.t-Region` radius via `--ut-region-*`) — override on that element —
and Iris rules that carry `!important` (tree-nav hover/current) — mirror the `!important` with a comment.

## Evidence

DevTools `getComputedStyle(document.documentElement)` lists the atoms on `:root`; CSSOM walk shows the
modifier declarations on element selectors; computed sizes after override: default button 35.6px / hot teal,
`.t-Button--hideShow` still 23.6px, floating-label input still 47.6px, IG/IRR header 40px. Console clean.

## Existing Assumption

`docs/DESIGN_SYSTEM.md §1` and evaluation `08-iris-only`: "never redefine `--ut-*` / `--a-*` globally on
`:root`; redefine scoped under an `.app-*` class". Read literally this forbids the app-wide restyle the user
approved and pushes toward property overrides against UT class names, which are more fragile.

## Impact

The approved "quiet product" restyle is implemented almost entirely as scoped atom overrides
(`static-files/css/apex/*.css`). Future app-wide changes should use the same technique; per-region variants
still go under `.app-*`.

## Proposed Knowledge Change

`docs/DESIGN_SYSTEM.md §1`: add the rule "app-wide restyle → override atoms on `body.apex-theme-iris`
(theme-style scope), never on `:root`; per-component variant → under `.app-*`". Evaluation `08-iris-only`
failure line stays (`:root` is still wrong); `02-css-scoping` gains an "app-wide, user-approved" branch.
`apex-css-selector-strategy` skill: prefer atom override over property override when the atom exists.

## Regression Scenario

Given: restyle all buttons to 36px. Expected: base `--a-button-*` on `body.apex-theme-iris`; `.t-Button--small`
stays small. Failure: `.apex-theme-iris .t-Button{padding…}` (breaks size modifiers) or `:root{--a-button-*}`.

## Scope

Application convention (this project) + reusable UT 26.1 knowledge (atom placement).
