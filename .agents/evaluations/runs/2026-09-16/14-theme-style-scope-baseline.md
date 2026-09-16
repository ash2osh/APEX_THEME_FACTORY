# Run: 14-theme-style-scope — baseline

Scenario file: `.agents/evaluations/14-theme-style-scope.md`
Execution mode: **OFFLINE**
Worktree: `/tmp/eval/14-theme-style-scope-baseline` at commit `97a3354` — the parent of `43eec93`, the commit
that introduced *both* the `docs/DESIGN_SYSTEM.md` §1 "app-wide restyle → override the base atoms on
`body.apex-theme-iris`" bullet **and** the finding
`.agents/findings/…/2026-09-13-theme-style-scope-token-overrides.md` it came from. Verified before running:
`git show 97a3354:docs/DESIGN_SYSTEM.md` has neither the bullet nor any mention of the theme-style scope, and
the finding file does not exist at that commit — so the baseline is isolated from the instruction under test
and from its source finding (pitfalls §6.1).
Current counterpart: `14-theme-style-scope-current.md` (commit `4fc73b8`), **same prompt text**, dispatched in
parallel.
Evaluee: fresh general-purpose agent, not told which skill was under test
Date: 2026-09-16

## Evaluee prompt (verbatim — identical to the current run except the worktree path)

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/14-theme-style-scope-baseline. cd there and treat it as your working directory for this whole task — all file reads and edits happen there, nowhere else. Never read or write anything in /home/ash/projects/APEX_THEME_FACTORY.

Your instructions are /tmp/eval/14-theme-style-scope-baseline/AGENTS.md, the docs it references, and the skills under /tmp/eval/14-theme-style-scope-baseline/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its copies may not match this directory). Do not read anything under .agents/evaluations/ (out of scope for this task).

Execution mode: OFFLINE. Do not connect to Oracle, do not run scripts/apex-validate.sh, do not run scripts/apex-import.sh, do not open Chrome or use any browser/MCP tool. Compilation of your change therefore stays unvalidated — say so plainly in your report rather than claiming validation you did not run.

Environment: Core/Iris declare each component's atoms (--a-button-*, --a-field-*, --a-gv-*, --jui-dialog-*, --a-menu-*, most --ut-*) once at :root, and separately re-declare the same atom names on the specific selector for every modifier / state / variant (.t-Button--small, .t-Button--hot, .t-Button--header, floating-label containers, .a-IRR, tree-nav hover/current — some of the latter using !important). A few atoms (.a-IRR's --a-gv-border-radius, .t-Region's radius via --ut-region-*) are instead set directly on an element rather than at :root. Read-only offline copies of the Universal Theme / Iris CSS are under .agents/knowledge/reference/ut-26.1/ and you may grep them.

Task: restyle all form field inputs (floating-label text fields included) app-wide to have a 1px solid border in the app's border colour, instead of Iris' default underline-only style.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits, made in that directory, (3) a final summary listing every file you changed with the exact selectors, properties and tokens you used, and why you placed the change where you placed it. Stop before any import.
```

This is the first time this scenario has been run as a genuinely matched pair: round 5 of the 2026-09-14
corrections found baseline and current had been given *different tasks* (buttons vs. form fields), and round 6
found the shared `Given` stated the scoping conclusion outright. Both defects are fixed here — one task, one
prompt, no answer supplied.

## Evaluee final report (verbatim)

> One file changed. Here is the report.
>
> ## Plan (as executed)
>
> Single file: `static-files/css/apex/forms.css` — extend the existing `.apex-theme-iris` field-atom block. No new token was needed (`--app-border-color` already exists in `foundation/tokens.css`), so no `tokens.css` or `DESIGN_SYSTEM.md` change.
>
> ## Correction to the premise — Iris is not underline-only
>
> Grepping the offline copies under `.agents/knowledge/reference/ut-26.1/`, Core draws **every** field type from one rule whose selector list is `.apex-item-text, .apex-item-textarea, .apex-item-select, .apex-item-multi, .apex-item-combobox, .apex-item-*-readonly, .u-TF-item--text/--select, select.group_selectlist, select.listmanager, .datetimepicker_newMonth`:
>
> ```css
> border-color: var(--a-field-input-state-border-color, var(--a-field-input-border-color));
> border-style: var(--a-field-input-border-style, solid);
> border-width: var(--a-field-input-border-width, 1px);
> ```
>
> Iris `:root` sets `--a-field-input-border-style: solid` and `--a-field-input-border-color: rgba(22,21,19,.5)`; `--a-field-input-border-width` is **never declared** by Core or Iris, so the 1px comes only from each rule's inline fallback. Nothing anywhere zeroes the top/side borders, and none of the `.t-Form-fieldContainer--floatingLabel` rules touch a border atom. So Iris 26.1 already renders a full 1px solid box on all four sides, floating-label fields included — what was actually missing was that the width/colour were Iris', not the app's.
>
> ## The edit
>
> `static-files/css/apex/forms.css`, inside the existing `.apex-theme-iris { … }` block (added, with an explanatory comment):
>
> | Property | Value |
> |---|---|
> | `--a-field-input-border-width` | `1px` |
> | `--a-field-input-border-style` | `solid` |
> | `--a-field-input-border-color` | `var(--app-border-color)` |
>
> ## Why there
>
> - **Selector `.apex-theme-iris` (body-level theme class), not `:root`.** These are inherited custom properties, so a declaration on `<body>` beats Iris' `:root` for every descendant while still losing to any selector closer to the element. That matters here because Iris/Core re-declare field atoms on `.t-Form-fieldContainer--floatingLabel`, `.t-Form--large/--xlarge`, `:hover`, `:focus-within`, `.apex-page-item-error` and `.is-readonly` — all of which must keep winning. Redefining `--a-*` on `:root` is explicitly banned by `docs/DESIGN_SYSTEM.md` §1, and is the technique `.agents/knowledge/ut-dom-buttons-forms.md` prescribes against.
> - **Atoms, not a `border:` shorthand on `.apex-item-*`.** One declaration set reaches all ~15 item types plus the floating-label variants through Core's own rule, with no `!important` and no specificity fight. A shorthand would have flattened the state layer.
> - **Floating-label coverage comes for free** — those containers declare only padding/typography atoms, never border atoms, so they inherit the box too; readonly keeps its dashed `--a-field-input-state-border-style` and error keeps `--ut-palette-danger`.
> - **States preserved:** readonly still gets `--a-field-input-state-border-style: dashed`, error still `--ut-palette-danger`, focus still the pre-existing `--a-field-input-focus-border-color: var(--app-color-primary)`.
>
> ## Two things to know
>
> 1. **Contrast trade-off.** The previous line in this file deliberately kept Iris' `rgba(22,21,19,.5)` (3.3:1 on white) citing WCAG 1.4.11. `--app-border-color` is `var(--ut-component-border-color)` = `rgba(0,0,0,.1)`, roughly 1.25:1 — a visible hairline, consistent with regions/cards/default buttons and with what `docs/superpowers/specs/2026-09-13-modern-look-design.md` line 65 specifies for `forms.css`, but the resting boundary no longer meets 3:1 on its own, so focus and error states now carry state identification. I replaced the old comment with this reasoning rather than leave a comment that no longer matched the code. One-line revert if you want the stronger colour back.
> 2. **Deliberate spillover.** Iris paints `.a-IRR-search` and `.a-IG-header .a-Toolbar-group--search` from the same atoms read on the element, so the IR and IG search wrappers now match the form fields. (They already tracked the pre-existing `--app-radius-sm` override, so this is not a new kind of coupling.) Iris' `--a-report-controls-input-*` aliases are resolved at `:root` and therefore unaffected.
>
> **Not validated.** Per the offline execution mode I ran no `scripts/apex-validate.sh`, no import, and no browser — the change is unverified at runtime. The reasoning above is from static reading of `Core.min.css` / `Iris.min.css`; it should be confirmed on p1600 (Forms) plus one floating-label page, checking readonly, error and `--large` items, before import.

## Verdict: PASS

Same Verdict Rule, same measurement on the diff: the three border atoms land on `.apex-theme-iris` — the
theme-style scope the Rule names in its "or `body.apex-theme-iris` for app-wide Iris style scope" branch (at
`97a3354` there are no theme packages yet, so this *is* the app-wide form) — with no `:root` declaration and
no property override. Neither Failure condition is triggered.

## What this means for the finding

The baseline reaches the correct technique **without** the `docs/DESIGN_SYSTEM.md` §1 bullet and without the
finding that motivated it. Its own reasoning shows why: the file it edited, `static-files/css/apex/forms.css`
at `97a3354`, already contained an `.apex-theme-iris { --a-field-input-border-radius: …; --a-field-input-
padding-*: …; }` block, so the repository demonstrated the technique by example. (The evaluee also cites
"`docs/DESIGN_SYSTEM.md` §1" — accurately, for the `:root` prohibition, which predates `43eec93`; the
*app-wide restyle* sentence it did not have.)

So: not load-bearing, cleanly established this time rather than left ambiguous. See
`.agents/findings/accepted/2026-09-13-theme-style-scope-token-overrides.md` for how that fed the promotion
decision.

## Full diff from the evaluee worktree

Complete `git diff`, captured before the worktree was removed (pitfalls §6.6). No untracked files were
created.

```diff
diff --git a/static-files/css/apex/forms.css b/static-files/css/apex/forms.css
index 80e2b53..304291f 100644
--- a/static-files/css/apex/forms.css
+++ b/static-files/css/apex/forms.css
@@ -4,7 +4,28 @@
 
 .apex-theme-iris {
     --a-field-input-border-radius: var(--app-radius-sm);
-    /* border colour stays Iris' rgba(22,21,19,.5): 3.3:1 on white; .45 measured 2.96:1 (WCAG 1.4.11) */
+
+    /* Boxed inputs, app-wide. Core draws every item type from these three atoms in one rule
+       (.apex-item-text/-textarea/-select/-multi/-combobox/.u-TF-item--*/select.listmanager …):
+           border-width: var(--a-field-input-border-width, 1px)
+           border-style: var(--a-field-input-border-style, solid)
+           border-color: var(--a-field-input-state-border-color, var(--a-field-input-border-color))
+       …-border-width is never declared by Core or Iris — the 1px is only each rule's inline
+       fallback — so declaring it here is what makes the 1px box ours rather than incidental.
+       Declared on the body theme class, not :root: modifier/variant/state selectors
+       (--floatingLabel, --large/--xlarge, :hover, :focus-within, .apex-page-item-error,
+       .is-readonly) re-declare field atoms closer to the element and must keep winning.
+       Floating-label containers set only padding/typography atoms, never border atoms, so they
+       inherit this box too; readonly keeps its dashed --a-field-input-state-border-style and
+       error keeps --ut-palette-danger. */
+    --a-field-input-border-width: 1px;
+    --a-field-input-border-style: solid;
+    /* Hairline in the app border colour, matching regions/cards/default buttons. Trade-off:
+       --app-border-color is rgba(0,0,0,.1) (~1.25:1 on white) where Iris' own field border was
+       rgba(22,21,19,.5) (3.3:1) — the resting boundary no longer meets WCAG 1.4.11 on its own,
+       so focus (--app-color-primary) and error (--ut-palette-danger) carry state identification. */
+    --a-field-input-border-color: var(--app-border-color);
+
     --a-field-input-padding-y: .4375rem;                   /* stacked/inline items → ~36px */
     --a-field-input-padding-x: .625rem;
     --a-field-input-focus-border-color: var(--app-color-primary);

```
