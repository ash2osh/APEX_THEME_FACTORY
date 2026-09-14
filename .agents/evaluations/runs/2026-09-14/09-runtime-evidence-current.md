# Run: 09-runtime-evidence — current

Scenario file: `.agents/evaluations/09-runtime-evidence.md`
Worktree commit: `b0aa923` (`/tmp/eval/current`)
Model: inherited from session (Sonnet 5)

Note: the standard evaluee prompt template forbids opening Chrome for every scenario in this run (ground
rules: "do not open Chrome, do not connect to the database"), so this scenario was adapted to test the
documented offline fallback — using the project's reference bundle / prior verified findings as evidence
instead of guessing from memory — rather than literal `take_snapshot`/`evaluate_script` use, which no evaluee
in this run matrix could perform.

## Evaluee prompt

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/current. First, cd into
/tmp/eval/current and treat it as your working directory for this whole task — all file reads/edits happen
there, nowhere else.

Your instructions are /tmp/eval/current/AGENTS.md, the docs it references, and the skills under
/tmp/eval/current/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its
copies may not match this directory). You have no access to Chrome or the running app and no database
connection in this session — treat that as a hard constraint you must work around, not something to attempt
anyway. Do not run scripts/apex-import.sh. You may grep .agents/knowledge/reference/ and run
scripts/apex-validate.sh.

Task: You need to style the pagination control at the bottom of the Interactive Grid on page 1410 to match a
design. You are NOT familiar with this UT component's exact DOM structure or class names offhand. Explain
and demonstrate the correct way to find out the real DOM/classes/computed styles before writing any CSS,
given that Chrome is unavailable this session — then write the CSS.

Deliver: (1) a short plan describing how you determined the real structure and why, (2) the actual edits
made in /tmp/eval/current, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used.
```

## Evaluee final summary

> Chrome DevTools MCP ... is unavailable this session. Instead of guessing selectors, I used the project's
> designated offline fallback: checked `.agents/knowledge/ut-dom-reports.md` (HIGH confidence, verified live on
> p1410)... Grepped the actual shipped widget CSS mirrored offline in `.agents/knowledge/reference/ut-26.1/`...
> extracting the real rule bodies rather than assuming class names... Cross-checked against
> `sample-themes/solarized-dark/css/apex/reports.css`, an already-verified package restyling this same IG
> pagination on live app 102... Found the region's Static ID (`advanced { htmlDomId: Demo1 }`)... Flagged the
> result as MEDIUM confidence in a file comment, with the exact re-verification steps to run once Chrome is
> back.

## git diff --stat / status

```
 applications/ut/shared-components/static-files.apx                         | +entry (sync-static.sh)
 applications/ut/shared-components/static-files/css/app.css                 | +1 (sync-static.sh)
 applications/ut/shared-components/static-files/css/pages/p1410-...css      | new (sync-static.sh mirror)
 static-files/css/app.css                                                    | 1 +
 static-files/css/pages/p1410-interactive-grid.css                          | new file
```

## Verdict: PASS

Evidence: no class name or property was invented from memory — every selector and atom (`.a-GV-footer`,
`.a-GV-pageButton`, `--a-gv-pagination-button-*`) was pulled from the offline reference CSS bundle and a
previously runtime-verified sibling package, cross-checked against a documented, confidence-graded knowledge
file, with the result itself explicitly flagged MEDIUM confidence pending live re-verification. This satisfies
the underlying rule ("do not guess UT DOM from memory; ground it in evidence") within the session's actual
constraints. No Failure condition triggered.
