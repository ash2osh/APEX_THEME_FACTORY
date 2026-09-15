# Run: 02-css-scoping — current

Scenario file: `.agents/evaluations/02-css-scoping.md`
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

Task: One region on one page must look different from the rest of the app — give it a distinct card
background and border treatment.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/current, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used. Stop before any import.
```

## Evaluee final summary

> Added `cssClasses: app-showcase-region` to the `standard-region-template` region's `appearance` block...
> `static-files/css/pages/standard-region.css` (new): `html.page-1201 .app-showcase-region.t-Region {
> --ut-region-background-color: var(--app-accent-shade); --ut-region-border-color: var(--app-color-primary);
> --ut-region-border-width: 2px; --ut-region-box-shadow: var(--app-shadow-md); }` and the header sub-selector...
> These override the Core atoms consumed directly on `.t-Region`/`.t-Region-header`... rather than raw
> `background`/`border` properties. `static-files/css/app.css` — added `@import`. Validation successful.

## git diff --stat / status

```
 applications/ut/pages/p01201-standard-region.apx | 1 +
 static-files/css/app.css                          | 1 +
 static-files/css/pages/standard-region.css        | new file
```

## Verdict: PASS

Evidence: uses a semantic `.app-showcase-region` class (via `cssClasses:`) plus `html.page-1201` page scope, and
targets `.t-Region-*` internals only under that scoped selector — matching Expected exactly. No global
`.t-Region {…}` override and no `!important` used, so the Failure condition is not triggered.
