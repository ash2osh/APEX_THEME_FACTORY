# Run: 10-theme-package-routing — baseline (sync-static.sh permitted)

Scenario file: `.agents/evaluations/10-theme-package-routing.md`
Worktree commit: `9276369` (`/tmp/eval/baseline10`)
Model: inherited from session (Sonnet 5)

## Why this re-run exists

The Codex PR review on PR #4 (P2, `chatgpt-codex-connector`) raised two issues with the original scenario 10
runs: (1) the current-worktree run explicitly skipped `scripts/sync-static.sh` even though the scenario's own
Expected line requires it ("then scripts/sync-static.sh") — the evaluee prompt template only permitted
`apex-validate.sh`, so no evaluee in the original matrix could actually complete the Expected behavior; (2) at
`9276369`, `AGENTS.md` itself (which every evaluee is told to read) already states "theme packages in
sample-themes/<name>/css... Assemble with scripts/sync-static.sh before apex-import" — identical to the current
commit's AGENTS.md line — so the baseline FAIL wasn't evidence of a skill-text gap; the evaluee "acknowledged
that rule before hand-editing anyway."

Both are valid. Re-run with the evaluee prompt updated to explicitly permit `scripts/sync-static.sh` (verified
safe: read its own source first — local file copy + a regex text substitution, no DB/Chrome/network).

## Evaluee prompt

Same as the original baseline prompt, with this permission line changed:
```
Do not run scripts/apex-import.sh, do not open Chrome, do not connect to the database; you may grep
.agents/knowledge/reference/, and you may run scripts/apex-validate.sh and scripts/sync-static.sh (both are
safe local operations — sync-static.sh only copies files and regenerates a generated CSS import block, no
DB/Chrome involved).
```

## Evaluee final summary

> `sample-themes/quietwhite/` — narrowly scoped to just the two things asked for (nav + buttons)... Generated
> by `scripts/sync-static.sh` (read its source first; confirmed pure file-copy + regex text substitution, no
> DB/Chrome/network — ran it): `static-files/css/app.css` — `@themes` block gained `@import
> "themes/quietwhite/theme.css";`... No changes to `applications/ut/application.apx`... **`apex-validate.sh` not
> run.** The task text described it as safe, but I read its source first: it opens a SQLcl connection to the
> database — conflicts with "do not connect to the database." I followed the stricter rule and skipped it.

## git diff --stat / status

```
 docs/DESIGN_SYSTEM.md                                                        | +entry
 sample-themes/README.md                                                       | +1 row
 sample-themes/quietwhite/{theme.json,README.md,css/theme.css,css/tokens.css,
   css/apex/shell.css,css/apex/buttons.css}                                    | new package
 static-files/css/app.css                                                      | +1 (sync-static.sh generated)
 applications/ut/shared-components/static-files/css/app.css                    | +1 (sync-static.sh mirror)
 applications/ut/shared-components/static-files.apx                           | +4 entries (sync-static.sh)
 applications/ut/shared-components/static-files/css/themes/quietwhite/**       | new (sync-static.sh mirror,
                                                                                   byte-identical to source)
```

## Verdict: PASS

Evidence: package structure matches Expected exactly, and — critically, unlike the original baseline run —
the evaluee ran `scripts/sync-static.sh` (now permitted and verified safe) to properly register the `@themes`
block, rather than hand-editing it. No Failure condition triggered. It also independently caught that
`apex-validate.sh`, despite being nominally permitted in this run's prompt, actually opens a DB connection —
and declined to run it, correctly prioritizing the stricter global constraint over the more specific
permission grant.

**Consequence**: with the one missing permission restored, baseline (old skill era, `9276369`) now also
produces a fully correct, registered package. Combined with AGENTS.md's routing instruction being identical
between this commit and current, this significantly weakens the case that `2026-09-14-theme-packages-routing`'s
promotion (via the *original* scenario 10 runs) demonstrated a real skill-text effect — see the finding's
Status line for the final call once the current-worktree re-run (`10-theme-package-routing-current-sync-permitted.md`)
is in.
