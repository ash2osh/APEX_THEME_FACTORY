# Finding

Status:
Pending — demoted 2026-09-14 from a premature Accepted. Two problems with the original evaluation run, both
raised by PR #4's Codex review (P2) and independently verified: (1) the baseline (`9276369`) predated the
Solarized Dark package (`eda510d`), so there was nothing to review — not a real FAIL/AMBIGUOUS test of the
skill text; (2) the current-worktree prompt named the exact things to check ("literal `:root` color tokens",
"pages in the 4000/6300 range"), supplying the answer instead of testing whether the evaluee finds it. Re-run
with the correct isolation point (`eda510d`) and a neutral prompt on both sides: **PASS at baseline**
(evaluations/runs/2026-09-14/11-dark-package-coverage-baseline-eda510d.md) **and PASS at current**
(evaluations/runs/2026-09-14/11-dark-package-coverage-current-neutral.md) — verified beforehand that
`apex-css-design-system`'s literal-token guidance is byte-identical between the two commits, so this scenario
was never going to isolate a meaningful skill-text delta. The knowledge itself (pitfalls.md §1.1–1.4) is still
accurate and worth keeping; it just hasn't been shown load-bearing by this scenario. Both corrected runs
surfaced real, additional coverage gaps in the shipped Solarized Dark package (beyond what this finding
already covers) — recorded separately as
`.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md` rather than bulk-applied here.
Original (invalid) runs kept for the record: evaluations/runs/2026-09-14/11-dark-package-coverage-baseline.md,
evaluations/runs/2026-09-14/11-dark-package-coverage-current.md.

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
