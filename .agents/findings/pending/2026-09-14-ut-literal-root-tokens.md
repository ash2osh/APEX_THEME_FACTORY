# Finding

Status:
Pending (2026-09-15) — Missing evidence: live Chrome DevTools WCAG AA contrast audit on reference surfaces (p4000, p6303, p6304, and consumer fixtures) reporting 0 package failures before marking verified. Evaluated 2026-09-14 (demoted because both corrected runs are AMBIGUOUS due to lack of Chrome session; see evaluations/runs/2026-09-14/11-dark-package-coverage-{baseline-eda510d,current-neutral}.md). The knowledge in pitfalls.md §1.1–1.4 is accurate and retained.

Category:
UNIVERSAL-THEME-KNOWLEDGE

Confidence:
CONFIRMED

APEX Version:
26.1.4 (Universal Theme / Iris)

Page:
app 102 pages 1500, 1410, 6303, 6304 (repeated)

Component:
`--ut-*` / `--a-*` tokens on `:root`; APEX widget CSS `/i/app_ui/css/Core.min.css`, `Theme-Standard.min.css`

## Observation

1. Iris declares ~70 `--ut-*` and ~100 `--a-*` colour tokens as **literals** on `:root` (`--ut-region-text-color:
   #161513`, `--a-checkbox-background-color: #fff`, …). They do not follow `--ut-component-*`, so a package that only
   remaps the component tokens leaves those surfaces light or dark-on-dark.
2. Iris `:root` values written as `var(--a-button-text-color)` resolve at `:root`; a body-level override of the
   referenced atom does not reach them (`--a-gv-pagination-button-text-color` stayed `#161513`).
3. Atoms absent from `Core.min.css`/`Iris.min.css` are still live: the APEX widget CSS consumes them with light
   fallbacks (`.a-GV-footer{background:var(--a-gv-footer-background-color,#fff)}`), and `Theme-Standard.min.css`
   sets state atoms on elements (`.a-GV-pageSelector-item.is-selected .a-GV-pageButton{--a-gv-pagination-button-
   background-color:var(--a-gv-pagination-button-selected-background-color,#e0e0e0)}`).
4. `.u-Report` utility tables are painted white by the widget CSS with higher specificity than UT Core's token rule.

## Evidence

Chrome DevTools `evaluate_script` (computed styles and `getPropertyValue('--…')` per element), `document.styleSheets`
walk, regex over `reference/ut-26.1/Iris.min.css` `:root` blocks, grep of the fetched `app_ui-*.css`.

## Existing Assumption

DESIGN_SYSTEM §1 / finding 2026-09-13: "override the base atoms on body.apex-theme-iris and everything follows".
True for light restyles; incomplete for dark ones. The reference folder held only the UT CSS, so widget-consumed
atoms looked non-existent.

## Impact

Dark packages ship with unreadable surfaces on pages outside the verification list; agents delete "dead" atoms.

## Proposed Knowledge Change

pitfalls.md §1; reference README rules; `fetch-vendor.sh` fetches the widget CSS; `apex-css-design-system` and
`apex-ut-dom-knowledge` point at all four files; evaluation 11.

## Regression Scenario

Evaluation `11-dark-package-coverage.md`.

## Scope

Reusable Universal Theme 26.1 knowledge.
