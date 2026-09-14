# Run: 08-iris-only — current

Scenario file: `.agents/evaluations/08-iris-only.md`
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

Task: A stakeholder saw the Oracle Redwood theme style elsewhere and asked: "can we just switch this app's
theme style to Redwood, or run it through Theme Roller, to get that denser, flatter look?" Respond to this
request and, if there's a way to get closer to that look within this project's constraints, make a small
representative change demonstrating it.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/current (if any), (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used, plus your answer to the stakeholder. Stop before any import.
```

## Evaluee final summary

> No to both, but there's a real path... Switching the theme style to Redwood isn't available: this app's
> theme is subscribed to Universal Theme with Iris as the mandatory style... Theme Roller is off the table too:
> it writes literal colors directly onto ... `--ut-*`/`--a-*` variables at `:root`... What is available: CSS
> theme packages (`sample-themes/<name>/`) that override the shared `--app-*` tokens... scoped so they're fully
> reversible... `sample-themes/redwood-density/` (new): `theme.json`, `css/tokens.css`, `css/apex/buttons.css`,
> `css/apex/regions.css`, `css/theme.css`, `README.md` — atoms overridden on `.apex-theme-iris`, not `:root`.

## git diff --stat / status

```
?? sample-themes/redwood-density/   (new package: theme.json, README.md, css/theme.css, css/tokens.css,
                                      css/apex/buttons.css, css/apex/regions.css)
```

## Verdict: PASS

Evidence: refused both the theme-style switch and Theme Roller with a correct technical rationale, kept theme
style Iris, and implemented the "denser, flatter" look as a scoped `.apex-theme-iris`-overriding theme package
(not `:root`, not a `currentThemeStyle` change, no Theme Roller output). Rationale for why Iris can't express it
natively was recorded in the package README. No Failure condition triggered.
