# Run: 11-dark-package-coverage — baseline (corrected isolation + neutral prompt)

Scenario file: `.agents/evaluations/11-dark-package-coverage.md`
Worktree commit: `eda510d` (`/tmp/eval/baseline-eda510d-s11`) — **not** `9276369`
Model: inherited from session (Sonnet 5)

## Why this re-run exists

Two problems with the original run (`11-dark-package-coverage-baseline.md`, AMBIGUOUS): (1) `9276369` predates
`eda510d`, so the Solarized Dark package didn't exist yet — no artifact to review at all; (2) separately, the
`current`-worktree run of this scenario used a prompt that named the exact things to check ("literal `:root`
color tokens", "pages in the 4000/6300 range"), which the Codex PR review on PR #4 correctly flagged as
supplying the answer rather than testing whether the evaluee finds it unprompted. This run fixes both: correct
isolation commit (`eda510d`, package exists, knowledge/skill files not yet updated) and the original neutral
prompt (just "review whether it's ready to ship, fix what's missing" — no hints).

Verified before running: `apex-css-design-system` SKILL.md's literal-token guidance ("A dark package must remap
Iris' literal `:root` tokens... Grep atoms in all four files of `.agents/knowledge/reference/ut-26.1/`") is
**byte-identical** between `eda510d` and `b0aa923` (current) — only `apex-ut-dom-knowledge` gained a short
pointer to `pitfalls.md` and a one-line restatement of the same declares-vs-consumes idea. So this scenario was
never going to isolate a large skill-text delta; it mainly tests whether the evaluee does the grep work.

## Evaluee prompt

Identical to the original baseline run (neutral — no mention of `:root` tokens or specific page ranges), only
the worktree path changed.

## Evaluee final summary

> The package was far more thorough than "checked two pages" would suggest... But six component-atom groups had
> no scoped rule anywhere: standalone Tree (p1901) hover/active/placeholder/disabled/drag-helper states, Switch
> off-track (p1601/423), standalone Menu Bar (p1305/1120/407), field-input `:hover` background (p1600/1601 —
> "applies even on the already-verified pages"), File Upload progress bar (p1601), Card View icon/initials
> avatars (p3100/3110 — "both verified, but this specific atom wasn't"). Verified several plausible-looking
> candidates were **not** bugs (var() chains already resolving correctly) and left them alone, per change-scope
> discipline. README updated with a "Follow-up source review" section and an honest note that this is a static
> review pending a live runtime/contrast pass.

## git diff --stat / status

```
 sample-themes/solarized-dark/README.md            | + follow-up section
 sample-themes/solarized-dark/css/apex/forms.css   | +1 atom (field-input hover)
 sample-themes/solarized-dark/css/apex/regions.css | +4 atoms (Card View icon/initials)
 sample-themes/solarized-dark/css/tokens.css       | +~14 atoms (Tree, Switch, Menu Bar, File Drop)
```

## Verdict: PASS

Evidence: with a neutral prompt and the correct isolation commit, the baseline evaluee independently found and
fixed six distinct literal-token gaps beyond the two checked pages, using the same grep-the-reference-CSS
technique the (nearly identical at this commit) skill text already described — matching Expected without being
told what to look for. No Failure condition (unmeasured ratio claims, left-over white surfaces) triggered.

**Consequence for the finding**: pending the current-worktree re-run with the same neutral prompt
(`11-dark-package-coverage-current-neutral.md`), this weakens the promotion case for
`2026-09-14-ut-literal-root-tokens` on scenario 11 the same way scenarios 12/14 already did — see the finding's
Status line for the final call once both corrected runs are in.
