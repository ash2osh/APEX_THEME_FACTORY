# Run: 14-theme-style-scope — current

Scenario file: `.agents/evaluations/14-theme-style-scope.md`
Execution mode: **OFFLINE** (no Oracle, no `apex-validate.sh`, no browser — recorded per the scenario's mode choice)
Worktree: `/tmp/eval/14-theme-style-scope-current` at commit `4fc73b81ba305c17b11da9d8b37625938d5aa475`
Baseline counterpart: `14-theme-style-scope-baseline.md` (commit `97a3354`), **same prompt text**, dispatched in parallel
Evaluee: fresh general-purpose agent, not told which skill was under test
Date: 2026-09-16

## Evaluee prompt (verbatim — identical to the baseline run except the worktree path)

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/14-theme-style-scope-current. cd there and treat it as your working directory for this whole task — all file reads and edits happen there, nowhere else. Never read or write anything in /home/ash/projects/APEX_THEME_FACTORY.

Your instructions are /tmp/eval/14-theme-style-scope-current/AGENTS.md, the docs it references, and the skills under /tmp/eval/14-theme-style-scope-current/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its copies may not match this directory). Do not read anything under .agents/evaluations/ (out of scope for this task).

Execution mode: OFFLINE. Do not connect to Oracle, do not run scripts/apex-validate.sh, do not run scripts/apex-import.sh, do not open Chrome or use any browser/MCP tool. Compilation of your change therefore stays unvalidated — say so plainly in your report rather than claiming validation you did not run.

Environment: Core/Iris declare each component's atoms (--a-button-*, --a-field-*, --a-gv-*, --jui-dialog-*, --a-menu-*, most --ut-*) once at :root, and separately re-declare the same atom names on the specific selector for every modifier / state / variant (.t-Button--small, .t-Button--hot, .t-Button--header, floating-label containers, .a-IRR, tree-nav hover/current — some of the latter using !important). A few atoms (.a-IRR's --a-gv-border-radius, .t-Region's radius via --ut-region-*) are instead set directly on an element rather than at :root. Read-only offline copies of the Universal Theme / Iris CSS are under .agents/knowledge/reference/ut-26.1/ and you may grep them.

Task: restyle all form field inputs (floating-label text fields included) app-wide to have a 1px solid border in the app's border colour, instead of Iris' default underline-only style.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits, made in that directory, (3) a final summary listing every file you changed with the exact selectors, properties and tokens you used, and why you placed the change where you placed it. Stop before any import.
```

Neutrality check (pitfalls §6.2, and the reason round 6 rewrote this scenario's `Given`): the Environment
paragraph states only *where* Core/Iris declare atoms and modifiers. It does not say where an override should
go, does not mention `body.apex-theme-iris`, `:root`, theme packages, or "atom override beats property
override" — the conclusions this scenario exists to test. `.agents/evaluations/` was placed out of scope so
the evaluee could not read this file's own Verdict Rule.

## Evaluee final report (verbatim)

> Done. Work was entirely offline — no Oracle, no Chrome, no scripts that connect.
>
> ## Plan (what I decided before editing)
>
> Per `docs/DESIGN_SYSTEM.md` §1, an "app-wide restyle" in this project is a defined technique: override the **base atoms on the theme-style scope** (`body.apex-theme-iris`), never `:root`, because Core/Iris declare base atoms at `:root` and re-declare them on modifier selectors — so a body-level override reaches everything while genuine modifiers keep precedence. And per `apex-css-design-system`, app-wide *forms* appearance lives in `sample-themes/<name>/css/apex/forms.css`, not `static-files/css` (foundation/tokens.css explicitly forbids redeclaring `--a-*`).
>
> I verified the modifier question offline instead of assuming it, by grepping `.agents/knowledge/reference/ut-26.1/`:
>
> - `--a-field-input-border-width` / `-border-style` / `-border-color` are declared **only** at `:root` in Core/Iris. The field modifiers — `.t-Form-fieldContainer--floatingLabel`, `--large`, `--xlarge` — re-declare only *padding / font-size / label geometry* atoms, never the border atoms. **So one theme-style-scope block covers floating-label text fields too**; no per-modifier rule, no `!important`, no property override was needed.
> - The places that *do* set them on the element are all intentional exceptions that should keep winning: `.a-GV-cell .a-GV-columnItem input` (`width:0`, inline IG editors), `.apex-item-multi .apex-item-popup-lov` (`transparent`/`0`), pre/post text-block radius, and the `:focus`/`:focus-within` states that swap in `--a-field-input-state-border-color`.
> - Because Iris' `:root` chains (`--a-chip-border-color`, `--a-mdeditor-border-color`, `--a-filedrop-border-color`, `--a-report-controls-input-border-color`) resolve at `:root` (pitfalls §1.2), this override does **not** leak into chips / markdown editor / file drop — blast radius stays on field inputs.
>
> ## Files changed
>
> | File | Selector | Added |
> |---|---|---|
> | `sample-themes/linen/css/apex/forms.css` | `.app-theme-linen .apex-theme-iris` | `--a-field-input-border-width: 1px`, `--a-field-input-border-style: solid`, `--a-field-input-border-color: var(--app-border-color)` |
> | `sample-themes/solarized-dark/css/apex/forms.css` | `.app-theme-solarized-dark .apex-theme-iris` | `--a-field-input-border-width: 1px`, `--a-field-input-border-style: solid` (colour left at the existing `var(--app-border-strong)`) |
>
> Both went into the existing atom block of each package's `apex/forms.css` — the documented home for app-wide form appearance, scoped to `html.app-theme-<name>` + `body.apex-theme-iris`, specificity (0,2,0), which beats both Iris' `:root` and the widget CSS' own `:root --a-field-input-border-width`. I added them to **both** packages so the guarantee holds whichever theme is active. Rules are token-only, zero `!important`.
>
> I then ran `scripts/sync-static.sh` (local file copy only, no DB) to keep the APEXLang export in step; it rewrote the export copies of the two forms.css files.
>
> ## Two things you should know
>
> 1. **Accessibility regression in linen, by literal request.** "The app's border colour" is `--app-border-color`, which in linen is Iris' decorative hairline `rgba(0,0,0,.1)` → `rgb(230,230,230)` on white = **1.25:1** (computed, not runtime-measured). WCAG 1.4.11 wants ≥ 3:1 for a boundary that identifies a control, and this *replaces* Iris' own `rgba(22,21,19,.5)` at 3.3:1. I implemented what you asked rather than silently substituting, and left the caveat plus the one-line fix (`--a-field-input-border-color: rgba(22,21,19,.5)`) in a comment at the site. Say the word and I'll flip it. For the same reason I did **not** push `--app-border-color` into solarized-dark — its field border is deliberately `--app-border-strong` at a documented 3.3:1.
>
> 2. **The "underline-only" premise doesn't match the offline reference CSS.** In `reference/ut-26.1/`, Iris fields already resolve to `1px solid rgba(22,21,19,.5)`; I found no rule setting a bottom-only border or inset underline shadow on any field selector. The change is still correct and safe either way — it makes width/style explicit at a scope that outranks every `:root` declaration — but if the running app really renders underline-only, the source is something my offline copies don't show, and that needs a DevTools check.
>
> **Not validated:** I did not run `scripts/apex-validate.sh`, did not import, and did not inspect the running app. Compilation and runtime appearance of this change are unverified.

## Verdict: PASS

Against the scenario's Verdict Rule, measured on the diff, not on the prose:

- The three border atoms are declared on `.app-theme-linen .apex-theme-iris` (and
  `.app-theme-solarized-dark .apex-theme-iris`) — the package-scoped form of the theme-style scope the Rule
  names. **PASS clause 1.**
- No `:root` declaration anywhere in the diff (`grep ':root' ` over the patch: none). **PASS clause 3.**
- No property override: nothing in the diff sets `border`, `border-width`, `border-style` or `border-color`
  as a CSS property on `.apex-item-text` or any other element selector — only custom properties. Focus,
  hover, readonly, error and `--floatingLabel` keep their own declarations. **PASS clause 2 / neither Failure
  condition triggered.**
- Prohibited Writes ("no unscoped `:root` token overrides; no direct element property overrides fighting UT
  modifiers"): both respected.

Two things worth recording beyond the Rule. The evaluee did not assume the modifier question — it grepped
the offline Core/Iris copies to establish that no field modifier re-declares the border atoms, which is
exactly the reasoning the neutral `Given` was rewritten to require. And it refused to propagate the literal
`--app-border-color` into the dark package where a documented 3.3:1 border would have regressed, while
flagging that the same token *does* fall to ~1.25:1 in linen — i.e. it reported an accessibility consequence
of the instruction it was given rather than silently shipping or silently "fixing" it. Neither is required
for PASS; both are the behaviour the skills under test are meant to produce.

Caveat, stated plainly: this run is OFFLINE by design, so the resulting CSS is not compile-checked and not
runtime-measured. The Verdict Rule asks only about *where the override is placed and in what form*, which is
fully determined by the diff; it does not ask for a rendered result. (The scenario's artifact checklist item 4
— `apex-validate.sh` output — applies only to `CONNECTED` runs.)

## Matched-pair result

The baseline run at `97a3354` (the commit before `43eec93`, which introduced both the
`docs/DESIGN_SYSTEM.md` §1 "app-wide restyle → override base atoms on `body.apex-theme-iris`" bullet and the
finding behind it) reached the **same technique** — see `14-theme-style-scope-baseline.md`. So this scenario
is now validly tested as a matched pair against a neutral prompt for the first time, and the answer is:
current passes, baseline passes, the skill/doc text is **not load-bearing** for this task. The reason is
visible in the baseline tree: `static-files/css/apex/forms.css` at `97a3354` already contained an
`.apex-theme-iris { --a-field-input-*: … }` block, so the repository taught the technique by example even
where the prose did not yet state it. That is a real finding about the evaluation, not a defect in either
run.

## Full diff from the evaluee worktree

Complete `git diff`, captured before the worktree was removed (pitfalls §6.6). It includes the
`scripts/sync-static.sh` output (the export copies under
`applications/ut/shared-components/static-files/css/themes/**`), which is why files beyond `forms.css` appear:
the script re-copies every package file, so two stale comment lines in `shell.css`/`misc.css` were brought
back into step at the same time. No untracked files were created.

```diff
diff --git a/applications/ut/shared-components/static-files/css/themes/linen/apex/forms.css b/applications/ut/shared-components/static-files/css/themes/linen/apex/forms.css
index 0d6b427..bf9ad9f 100644
--- a/applications/ut/shared-components/static-files/css/themes/linen/apex/forms.css
+++ b/applications/ut/shared-components/static-files/css/themes/linen/apex/forms.css
@@ -4,7 +4,26 @@
 
 .app-theme-linen .apex-theme-iris {
     --a-field-input-border-radius: var(--app-radius-sm);
-    /* border colour stays Iris' rgba(22,21,19,.5): 3.3:1 on white; .45 measured 2.96:1 (WCAG 1.4.11) */
+
+    /* Full 1px box border on every field input, app-wide (requested 2026-09-16).
+       The three border atoms are declared *only* on :root in Core/Iris — no field modifier re-declares
+       them: .t-Form-fieldContainer--floatingLabel, --large, --xlarge set padding/font atoms only
+       (grep of reference/ut-26.1/{Core,Iris}.min.css). So this one theme-style-scope block reaches
+       stacked, inline and floating-label items alike, while the exceptions that *do* set them on the
+       element keep winning as intended: .a-GV-cell .a-GV-columnItem input (width 0 — inline IG editors),
+       .apex-item-multi .apex-item-popup-lov (transparent/0 — inner input of a multi-value popup LOV),
+       the pre/post text-block radius, and every :focus / :focus-within state that swaps in
+       --a-field-input-state-border-color. */
+    --a-field-input-border-width: 1px;
+    --a-field-input-border-style: solid;
+    /* ACCESSIBILITY CAVEAT — "the app's border colour" as requested. --app-border-color is linen's
+       decorative hairline (Iris --ut-component-border-color = rgba(0,0,0,.1)); composited on the white
+       card surface it is rgb(230,230,230), 1.25:1 against #fff (computed, not measured — offline).
+       WCAG 1.4.11 wants >= 3:1 for a boundary that identifies a control, and this replaces Iris' own
+       rgba(22,21,19,.5) at 3.3:1. If the faint look is not intended, the fix is this one line:
+       --a-field-input-border-color: rgba(22,21,19,.5). See .agents/knowledge/pitfalls.md §1.7. */
+    --a-field-input-border-color: var(--app-border-color);
+
     --a-field-input-padding-y: .4375rem;                   /* stacked/inline items → ~36px */
     --a-field-input-padding-x: .625rem;
     --a-field-input-focus-border-color: var(--app-color-primary);
diff --git a/applications/ut/shared-components/static-files/css/themes/linen/apex/shell.css b/applications/ut/shared-components/static-files/css/themes/linen/apex/shell.css
index e23ddb6..fd4350c 100644
--- a/applications/ut/shared-components/static-files/css/themes/linen/apex/shell.css
+++ b/applications/ut/shared-components/static-files/css/themes/linen/apex/shell.css
@@ -58,7 +58,7 @@
 /* Iris declares the hover tint with !important (Iris.min.css: `.is-hover{…!important}`); a
    translucent-white tint is invisible on a white panel, so the override must be !important too. */
 .app-theme-linen .apex-theme-iris .t-TreeNav .a-TreeView-node--topLevel .a-TreeView-row.is-hover {
-    background-color: var(--ut-component-highlight-background-color) !important;
+    background-color: var(--ut-component-highlight-background-color) !important; /* Iris: `.is-hover{…!important}` */
 }
 .app-theme-linen .apex-theme-iris .t-TreeNav .a-TreeView-node--topLevel .a-TreeView-row.is-hover + .a-TreeView-content,
 .app-theme-linen .apex-theme-iris .t-TreeNav .a-TreeView-node--topLevel .a-TreeView-row.is-hover + .a-TreeView-toggle,
diff --git a/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/forms.css b/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/forms.css
index 2bc84fb..59b3cca 100644
--- a/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/forms.css
+++ b/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/forms.css
@@ -9,6 +9,15 @@
     --a-field-input-background-color: var(--app-surface-input);
     --a-field-input-hover-background-color: var(--app-surface-input);   /* Iris literal #fff otherwise */
     --a-field-input-text-color: var(--app-text-emphasized);
+    /* Full 1px box border on every field input, app-wide (requested 2026-09-16). Same reasoning as
+       sample-themes/linen/css/apex/forms.css: Core/Iris declare these two atoms only on :root and no
+       field modifier (--floatingLabel, --large, --xlarge) re-declares them, so this block covers
+       floating-label items too; declaring them explicitly here also outranks the widget CSS' own
+       :root --a-field-input-border-width. The colour role stays --app-border-strong rather than this
+       package's --app-border-color (rgba(147,161,161,.2)): this border identifies the control and has
+       to hold >= 3:1 — WCAG 1.4.11, see README.md and .agents/knowledge/pitfalls.md §1.7. */
+    --a-field-input-border-width: 1px;
+    --a-field-input-border-style: solid;
     --a-field-input-border-color: var(--app-border-strong);        /* 3.3:1 on cards (WCAG 1.4.11) */
     --a-field-input-hover-border-color: var(--app-border-strong);
     --a-field-input-focus-border-color: var(--sol-cyan);
diff --git a/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/misc.css b/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/misc.css
index cafcf68..0902fcc 100644
--- a/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/misc.css
+++ b/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/misc.css
@@ -202,3 +202,17 @@
     color: var(--app-text-emphasized);
     background: var(--app-surface-hover);
 }
+
+/* Calendar (FullCalendar 5). UT gives default events a literal #2578cf background but colours their text
+   with --fc-event-text-color = --ut-palette-primary-contrast, which this package remaps to base03 for its
+   light primary: base03 on #2578cf is 3.3:1 (measured 2026-09-16, consumer 9011 page 3). Put default events
+   on the package primary so the contrast pair holds (base03 on --sol-blue-text = 5.2:1). */
+.app-theme-solarized-dark .apex-theme-iris .fc .fc-event.fc-apex-events-default,
+.app-theme-solarized-dark .apex-theme-iris .fc .fc-event.fc-apex-events-default .fc-event-main {
+    background-color: var(--app-color-primary);
+    border-color: var(--app-color-primary);
+}
+.app-theme-solarized-dark .apex-theme-iris .fc .fc-event.fc-apex-events-default:hover {
+    background-color: var(--app-color-primary);
+    filter: brightness(1.08);
+}
diff --git a/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/shell.css b/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/shell.css
index e07465d..f8dd1e1 100644
--- a/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/shell.css
+++ b/applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/shell.css
@@ -60,7 +60,7 @@
 /* Iris declares the hover tint with !important (Iris.min.css: `.a-TreeView-row.is-hover{…!important}`), so the
    override has to be !important too. */
 .app-theme-solarized-dark .apex-theme-iris .t-TreeNav .a-TreeView-node--topLevel .a-TreeView-row.is-hover {
-    background-color: var(--app-surface-hover) !important;
+    background-color: var(--app-surface-hover) !important; /* Iris: `.a-TreeView-row.is-hover{…!important}` */
 }
 .app-theme-solarized-dark .apex-theme-iris .t-TreeNav .a-TreeView-node--topLevel .a-TreeView-row.is-hover + .a-TreeView-content,
 .app-theme-solarized-dark .apex-theme-iris .t-TreeNav .a-TreeView-node--topLevel .a-TreeView-row.is-hover + .a-TreeView-toggle,
diff --git a/sample-themes/linen/css/apex/forms.css b/sample-themes/linen/css/apex/forms.css
index 0d6b427..bf9ad9f 100644
--- a/sample-themes/linen/css/apex/forms.css
+++ b/sample-themes/linen/css/apex/forms.css
@@ -4,7 +4,26 @@
 
 .app-theme-linen .apex-theme-iris {
     --a-field-input-border-radius: var(--app-radius-sm);
-    /* border colour stays Iris' rgba(22,21,19,.5): 3.3:1 on white; .45 measured 2.96:1 (WCAG 1.4.11) */
+
+    /* Full 1px box border on every field input, app-wide (requested 2026-09-16).
+       The three border atoms are declared *only* on :root in Core/Iris — no field modifier re-declares
+       them: .t-Form-fieldContainer--floatingLabel, --large, --xlarge set padding/font atoms only
+       (grep of reference/ut-26.1/{Core,Iris}.min.css). So this one theme-style-scope block reaches
+       stacked, inline and floating-label items alike, while the exceptions that *do* set them on the
+       element keep winning as intended: .a-GV-cell .a-GV-columnItem input (width 0 — inline IG editors),
+       .apex-item-multi .apex-item-popup-lov (transparent/0 — inner input of a multi-value popup LOV),
+       the pre/post text-block radius, and every :focus / :focus-within state that swaps in
+       --a-field-input-state-border-color. */
+    --a-field-input-border-width: 1px;
+    --a-field-input-border-style: solid;
+    /* ACCESSIBILITY CAVEAT — "the app's border colour" as requested. --app-border-color is linen's
+       decorative hairline (Iris --ut-component-border-color = rgba(0,0,0,.1)); composited on the white
+       card surface it is rgb(230,230,230), 1.25:1 against #fff (computed, not measured — offline).
+       WCAG 1.4.11 wants >= 3:1 for a boundary that identifies a control, and this replaces Iris' own
+       rgba(22,21,19,.5) at 3.3:1. If the faint look is not intended, the fix is this one line:
+       --a-field-input-border-color: rgba(22,21,19,.5). See .agents/knowledge/pitfalls.md §1.7. */
+    --a-field-input-border-color: var(--app-border-color);
+
     --a-field-input-padding-y: .4375rem;                   /* stacked/inline items → ~36px */
     --a-field-input-padding-x: .625rem;
     --a-field-input-focus-border-color: var(--app-color-primary);
diff --git a/sample-themes/solarized-dark/css/apex/forms.css b/sample-themes/solarized-dark/css/apex/forms.css
index 2bc84fb..59b3cca 100644
--- a/sample-themes/solarized-dark/css/apex/forms.css
+++ b/sample-themes/solarized-dark/css/apex/forms.css
@@ -9,6 +9,15 @@
     --a-field-input-background-color: var(--app-surface-input);
     --a-field-input-hover-background-color: var(--app-surface-input);   /* Iris literal #fff otherwise */
     --a-field-input-text-color: var(--app-text-emphasized);
+    /* Full 1px box border on every field input, app-wide (requested 2026-09-16). Same reasoning as
+       sample-themes/linen/css/apex/forms.css: Core/Iris declare these two atoms only on :root and no
+       field modifier (--floatingLabel, --large, --xlarge) re-declares them, so this block covers
+       floating-label items too; declaring them explicitly here also outranks the widget CSS' own
+       :root --a-field-input-border-width. The colour role stays --app-border-strong rather than this
+       package's --app-border-color (rgba(147,161,161,.2)): this border identifies the control and has
+       to hold >= 3:1 — WCAG 1.4.11, see README.md and .agents/knowledge/pitfalls.md §1.7. */
+    --a-field-input-border-width: 1px;
+    --a-field-input-border-style: solid;
     --a-field-input-border-color: var(--app-border-strong);        /* 3.3:1 on cards (WCAG 1.4.11) */
     --a-field-input-hover-border-color: var(--app-border-strong);
     --a-field-input-focus-border-color: var(--sol-cyan);

```
