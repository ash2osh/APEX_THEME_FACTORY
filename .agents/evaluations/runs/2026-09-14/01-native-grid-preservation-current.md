# Run: 01-native-grid-preservation — current

Scenario file: `.agents/evaluations/01-native-grid-preservation.md`
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

Task: You have an existing Interactive Grid region and a Figma/Stitch table design with different visual
styling. Make the Interactive Grid match the visual styling of the design.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/current, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used. Stop before any import.
```

## Evaluee final summary

> Located the existing IG — page 1410, region `basic-reporting`, Static ID `Demo1`. Confirmed native IG, not
> touching it structurally... Styled it via CSS only, page-scoped (`html.page-1410`)... Used the project's
> documented `--a-gv-*` IG atom vocabulary... no new literals, no `!important`, no global `.t-*`/`.a-*`
> overrides.
>
> Files changed: `static-files/css/pages/p1410-interactive-grid.css` (new, scoped `html.page-1410 #Demo1.a-IG`,
> `--a-gv-header-cell-height`, `--a-gv-cell-height`, `--a-gv-cell-padding-x/-y`, `--a-gv-border-radius`,
> `--a-gv-row-hover-background-color`, `.a-GV-headerLabel` typography); `static-files/css/app.css` (+1 import
> line). Not touched: `applications/ut/*.apx`, `sample-themes/*/css/apex/reports.css`.

## git diff --stat / status

```
 static-files/css/app.css                               |  1 +
 static-files/css/pages/p1410-interactive-grid.css       | new file
```

## Verdict: PASS

Evidence: the IG was kept as a native `.a-IG` component and styled entirely through scoped CSS and the
documented `--a-gv-*` atom vocabulary — no custom HTML/Alpine table, no second table implementation, matching
Expected exactly. No Failure condition triggered (no replacement, no unscoped global override).
