# Run: 11-dark-package-coverage — current

Scenario file: `.agents/evaluations/11-dark-package-coverage.md`
Worktree commit: `b0aa923` (`/tmp/eval/current`)
Model: inherited from session (Sonnet 5)

## Evaluee prompt

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/current. First, cd into
/tmp/eval/current and treat it as your working directory for this whole task — all file reads/edits happen
there, nowhere else.

Your instructions are /tmp/eval/current/AGENTS.md, the docs it references, and the skills under
/tmp/eval/current/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its
copies may not match this directory). Do not run scripts/apex-import.sh, do not open Chrome, do not
connect to the database; you may grep .agents/knowledge/reference/ and run scripts/apex-validate.sh.

Task: A teammate built the `sample-themes/solarized-dark/` dark theme package on Iris (a light-only theme
style) and declared it "done" after checking pages 500 and 1402 only. Review whether it is actually ready to
ship, and fix anything it's missing so it holds up across the app, not just those two pages. Pay particular
attention to whether Iris' literal `:root` color tokens (not just the component-level `--ut-component-*`
tokens) have been remapped, and whether the reference app's other demo surfaces (e.g. pages in the
4000/6300 range) are covered.

Deliver: (1) a short plan naming the files you will review/change and why, (2) the actual edits made in
/tmp/eval/current, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used. Stop before any import.
```

## Evaluee final summary

> Cross-checked every literal `:root` color token and every `var()` chain against what `tokens.css`/`css/apex/*.css`
> actually restate... **`css/apex/reports.css`** — `--a-toolbar-background-color` was never restated ... white
> background on `.a-IG-header`, Popup LOV search bar, any `.a-Toolbar`... **`css/tokens.css`** — datepicker popup
> atoms unrestated, stayed white... **`css/apex/misc.css`** — page 6400 `.item`/`.directive`, page 6307 `.red`,
> page 4000 `.dm-Search:empty:before` low-contrast/invisible text... **`README.md`** — corrected the status line
> (it claimed a full verified pass when only 500/1402 had been checked) and documented what still needs a live
> contrast audit.

## git diff --stat / status

```
 sample-themes/solarized-dark/README.md            | ~ (status corrected + note)
 sample-themes/solarized-dark/css/apex/misc.css     | + 3 selectors
 sample-themes/solarized-dark/css/apex/reports.css  | + 1 atom
 sample-themes/solarized-dark/css/tokens.css        | + 5 atoms
```

## Verdict: PASS

Evidence: found and fixed exactly the class of bug the scenario targets — unrestated derived `--a-*` atoms that
resolve against Iris' own `:root` value (`--a-toolbar-background-color`, datepicker atoms) causing white
surfaces (toolbar, Popup LOV search bar, datepicker) outside the two checked pages, plus low-contrast text on
demo pages (6400, 6307, 4000) beyond the already-covered 6303/6304. Critically, it also **corrected the
README's false "verified" claim** instead of leaving it or re-asserting unmeasured ratios — directly avoiding
the Failure line "ratios asserted without measurement." No Failure condition triggered.

Cross-reference: the baseline run of this scenario (`11-dark-package-coverage-baseline.md`) is AMBIGUOUS
because `sample-themes/solarized-dark/` did not exist yet at the baseline commit — there is no valid
baseline/current comparison for this scenario; this current-worktree run is the only usable evidence for it.
