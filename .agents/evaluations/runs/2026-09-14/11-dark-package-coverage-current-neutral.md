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

## Verdict: AMBIGUOUS — corrected 2026-09-14 from an earlier, wrong PASS

**Correction** (Codex PR review, PR #4, P2 — same point as the baseline run's correction): the scenario's
`Expected` line requires a live Chrome contrast audit reporting 0 failures before the README's Verified
section is written. This run, like its baseline counterpart, is a source-level substitute only — real,
thorough, well-evidenced work, but it does not exercise (and cannot satisfy) that half of Expected.

~~Evidence: with a neutral prompt, the evaluee independently reconstructed the full literal/derived-token gap
list via source analysis, found and fixed a materially larger set of gaps than even the corrected baseline run
(`11-dark-package-coverage-baseline-eda510d.md`) — including one bug (`--a-field-input-hover-background-color`)
both runs found independently. It also caught and corrected an overclaimed "verified" status rather than
leaving it. No Failure condition triggered.~~

**Consequence for the finding**: `2026-09-14-ut-literal-root-tokens` still cannot be promoted on scenario 11 —
not because "both sides passed and it wasn't load-bearing" (the original, now-corrected reasoning), but because
**neither side could be validly graded to completion** under this session's no-Chrome constraint. Promotion
requires a confirmed baseline FAIL, which this scenario has never produced (in either the original invalid-
isolation runs or these corrected-isolation ones). The finding stays pending, genuinely unresolved rather than
demonstrated-not-load-bearing; see its Status line. Separately, both evaluees independently found real,
verifiable literal-token gaps in the shipped package (confirmed by direct reference-CSS grep, independent of
any Chrome-dependent question) — recorded as a distinct pending finding
(`2026-09-14-solarized-dark-2page-coverage-gap.md`, branch `fix-solarized-dark-contrast-followups`) and largely
fixed there, since that part of the work stands on its own regardless of how this evaluation scenario resolves.
