# Run: 07-token-reuse — current

Scenario file: `.agents/evaluations/07-token-reuse.md`
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

Task: A design calls for 8px corner radius on cards throughout the app. Find out whether this project
already has a token for that radius, and apply it correctly wherever cards need it (pick one representative
page-local card treatment to demonstrate the change if no single obvious target exists).

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/current, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used. Stop before any import.
```

## Evaluee final summary

> This project already has a radius token role for this — `--app-radius-sm/-md/-lg`... Each theme package
> defines its own literal scale... linen: 6/**8**/12px → 8px is `--app-radius-md`. solarized-dark: 4/6/**8**px →
> 8px is `--app-radius-lg`. [Applied per-theme:] `sample-themes/linen/css/apex/regions.css` — added `.a-CardView
> { --a-cv-border-radius: var(--app-radius-md) }`... `sample-themes/solarized-dark/css/apex/regions.css` —
> changed `--ut-cardlist-border-radius`/`--a-cv-border-radius` from `var(--app-radius-md)` to
> `var(--app-radius-lg)`.

## git diff --stat / status

```
 sample-themes/linen/css/apex/regions.css          | ~4 lines
 sample-themes/solarized-dark/css/apex/regions.css | ~4 lines
```

## Verdict: PASS

Evidence: no literal `8px` was hardcoded anywhere and no new `--app-radius-8` token was created — every
edit resolves to an existing `--app-radius-*` role, correctly picking the token whose *value* is 8px in each
theme's own scale (`--app-radius-md` in linen, `--app-radius-lg` in solarized-dark) rather than assuming a
single global mapping. This is a stronger result than the scenario's literal Expected line (which assumes one
global `--app-radius-lg` = 8px) because it correctly accounts for this repo's actual per-theme-package token
architecture — still fully consistent with the underlying rule (reuse the token, don't hardcode the literal).
