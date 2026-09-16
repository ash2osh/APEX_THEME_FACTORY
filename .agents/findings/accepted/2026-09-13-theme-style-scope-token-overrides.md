# Finding

Status:
**Accepted 2026-09-17** — evaluation 14 run as a valid matched pair for the first time (one task, one neutral
`Given` that states only where atoms and modifiers are declared): **current PASS, baseline PASS**
(`evaluations/runs/2026-09-16/14-theme-style-scope-{current,baseline}.md`). Both evaluees placed the
`--a-field-input-border-*` override on the theme-style scope, neither at `:root`, neither as a property
override that would fight a modifier.

Promoted on the strength of the knowledge, not of a differential: the observation below is runtime-verified
(computed atom values and CSSOM walk on the live app, and the same mechanism re-confirmed across the
2026-09-16 live runs), and its scenario passes. The `docs/DESIGN_SYSTEM.md` §1 bullet this finding produced is
**not load-bearing** for the tested task, and the baseline run shows why: at `97a3354`
`static-files/css/apex/forms.css` already carried an `.apex-theme-iris { --a-field-input-*: … }` block, so the
repository taught the technique by example before the prose stated it. The bullet stays because it makes the
rule explicit for cases with no such example, not because an evaluee needed it here.

Earlier status, for the record: *Pending (2026-09-15) — missing a matched baseline/current re-run against the
canonical form-field prompt with the neutral Given.*

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
