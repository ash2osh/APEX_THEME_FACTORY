# Run: 10-theme-package-routing — current (sync-static.sh permitted)

Scenario file: `.agents/evaluations/10-theme-package-routing.md`
Worktree commit: `b0aa923` (`/tmp/eval/current10`)
Model: inherited from session (Sonnet 5)

## Why this re-run exists

Same reasons as `10-theme-package-routing-baseline-sync-permitted.md`: the original current-worktree run
explicitly skipped `scripts/sync-static.sh` (not permitted by the evaluee prompt), even though it's part of
the scenario's own Expected line. Re-run with that permission restored.

## Evaluee prompt

Same as the original current-worktree prompt, with `scripts/sync-static.sh` added to the permitted-scripts
line (identical wording to the corrected baseline prompt).

## Evaluee final summary

> Built `quietwhite` as a targeted package... Added one new token, `--app-surface-nav` (justified: existing
> `--app-surface-chrome` is documented as "header + side nav", and the task only asked for the nav)... Ran
> `scripts/sync-static.sh` (`themes=[linen quietwhite solarized-dark] copied=7 registered=5 pruned=0`), which
> mechanically updated `static-files/css/app.css`'s `@themes` block, mirrored into
> `applications/ut/shared-components/static-files/`, registered 5 entries in `static-files.apx`. Ran
> `scripts/apex-validate.sh` — Validation successful.

## git diff --stat / status

```
 docs/DESIGN_SYSTEM.md                                                | +rows
 sample-themes/README.md                                              | +1 row, +guidance
 static-files/css/foundation/tokens.css                               | +1 token (--app-surface-nav)
 sample-themes/quietwhite/{theme.json,README.md,css/theme.css,
   css/tokens.css,css/apex/shell.css,css/apex/buttons.css}            | new package
 static-files/css/app.css                                             | +1 (sync-static.sh generated)
 applications/ut/shared-components/static-files/**, static-files.apx  | mirror + 5 entries (sync-static.sh)
```

## Verdict: PASS

Evidence: package structure matches Expected exactly; `scripts/sync-static.sh` was run to properly register
the `@themes` block (no hand-edit); `apex-validate.sh` ran clean. No Failure condition triggered.

**Consequence**: with the missing permission restored on both sides, **baseline now also passes**
(`10-theme-package-routing-baseline-sync-permitted.md`) — the difference in the *original* pair of runs was
caused by an evaluee-prompt gap (sync-static.sh not permitted, forcing a choice between hand-editing or leaving
the package broken), not by a skill-text difference; `AGENTS.md`'s own routing instruction was already
identical between `9276369` and `b0aa923`. This is the same load-bearing-evidence problem that demoted the
other two findings from this run. `2026-09-14-theme-packages-routing` is demoted back to `findings/pending/`;
see the finding's Status line.
