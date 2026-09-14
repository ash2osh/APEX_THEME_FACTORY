# Run: 11-dark-package-coverage — current (corrected, neutral prompt)

Scenario file: `.agents/evaluations/11-dark-package-coverage.md`
Worktree commit: `b0aa923` (`/tmp/eval/current2`)
Model: inherited from session (Sonnet 5)

## Why this re-run exists

Replaces `11-dark-package-coverage-current.md`. The Codex PR review on PR #4 (P2) correctly pointed out that
run's prompt named the exact things to check ("literal `:root` color tokens", "pages in the 4000/6300 range"),
supplying the answer rather than testing whether the evaluee finds it. This run uses the original neutral
prompt (same one used for the baseline runs) instead.

## Evaluee prompt

Identical to the corrected baseline run (`11-dark-package-coverage-baseline-eda510d.md`) — neutral, no hints —
only the worktree path changed (`/tmp/eval/current2`, commit `b0aa923`).

## Evaluee final summary

> The CSS technique was sound and already 90% applied — but incompletely: `--a-field-input-hover-background-color`
> was never set → every text input flashed Iris' literal white on hover; `--a-toolbar-background-color` was never
> set → IG header (p1410), Markdown Editor toolbar, Popup LOV search bar, CKEditor panels stayed white; ~50
> second-order `var()`-chain tokens left unaddressed (datepicker, menus, header nav-bar hover, chips,
> report-controls/results-items, chat); entire component families never opened at all: Faceted Search (p1411),
> Markdown Editor + Percent Graph (p1601/423), Calendar (p1800), Chart tooltips (p1902), Help Text (p1903), Map
> legend (p1906). Separately, the package README **overclaimed** a 14-page audit with "0 failures" when only
> 500/1402 were actually checked — corrected rather than left standing. Also filed a new pending finding
> (`2026-09-14-solarized-dark-2page-coverage-gap.md`) recording the gap per spec §50–58, deliberately left
> `evaluations/README.md` at "not yet run" since it didn't execute the formal protocol itself.

## git diff --stat / status

```
 .agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md | new file (evaluee's own finding)
 sample-themes/README.md                                                  | ~ (status honesty fix)
 sample-themes/solarized-dark/README.md                                   | ~ (corrected !important count, Verified section rewritten)
 sample-themes/solarized-dark/css/apex/buttons.css                        | +2 atoms
 sample-themes/solarized-dark/css/apex/dialogs.css                       | +3 atoms
 sample-themes/solarized-dark/css/apex/forms.css                         | +1 atom (field-input hover)
 sample-themes/solarized-dark/css/apex/misc.css                          | ~ (comment contrast-figure fix)
 sample-themes/solarized-dark/css/apex/regions.css                       | +5 atoms
 sample-themes/solarized-dark/css/apex/reports.css                       | +2 atoms (incl. toolbar background)
 sample-themes/solarized-dark/css/apex/shell.css                        | +2 atoms
 sample-themes/solarized-dark/css/tokens.css                             | +~35 atoms across 8 new component families
```

## Verdict: PASS — and matches (exceeds) the baseline run's thoroughness

Evidence: with a neutral prompt, the evaluee independently reconstructed the full literal/derived-token gap
list via source analysis, found and fixed a materially larger set of gaps than even the corrected baseline run
(`11-dark-package-coverage-baseline-eda510d.md`) — including one bug (`--a-field-input-hover-background-color`)
both runs found independently. It also caught and corrected an overclaimed "verified" status rather than
leaving it. No Failure condition triggered.

**Consequence for the finding**: `2026-09-14-ut-literal-root-tokens` cannot be promoted on scenario 11 — both
a properly isolated baseline (`eda510d`, old skill text) and current independently produced excellent, thorough
audits using nearly-identical skill text (`apex-css-design-system`'s literal-token guidance is byte-identical
between the two commits; only `apex-ut-dom-knowledge` gained a short pointer). The skill change was not shown
load-bearing. Demoted back to `findings/pending/`; see the finding's Status line. The gaps both evaluees found
are real (verified by direct reference-CSS grep against `app_ui-Core.min.css`/`Theme-Standard.min.css`), but
they exist in the shipped package regardless of skill-text era — recorded as a separate pending finding rather
than silently bulk-applied to `main` from an unverified throwaway-worktree run (no Chrome available to confirm
computed styles/contrast).
