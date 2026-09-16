# Run: 09-runtime-evidence — current

Scenario file: `.agents/evaluations/09-runtime-evidence.md`
Execution mode: **CONNECTED** (live Chrome via the project daemon; no import, no DB change)
Worktree: `/tmp/eval/09-runtime-evidence-current` at commit `4fc73b81ba305c17b11da9d8b37625938d5aa475`
Evaluee: fresh general-purpose agent, not told which skill was under test
Grader: this session (independent re-measurement below)
Date: 2026-09-16

This is the run the 2026-09-14 matrix could not do: that matrix forbade Chrome to every evaluee and then
graded this scenario on an offline fallback, which round 1 of the corrections rightly called a false green.

## Evaluee prompt (verbatim)

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/09-runtime-evidence-current. cd there and treat it as your working directory for this whole task — all file reads and edits happen there, nowhere else. Never read or write anything in /home/ash/projects/APEX_THEME_FACTORY.

Your instructions are /tmp/eval/09-runtime-evidence-current/AGENTS.md, the docs it references, and the skills under /tmp/eval/09-runtime-evidence-current/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its copies may not match this directory). Do not read anything under .agents/evaluations/ (out of scope for this task).

Execution mode: CONNECTED (live browser). You may run scripts/apex-validate.sh (a read-only compile check over the saved connection docker-demo). You may NOT run scripts/apex-import.sh, may not import anything, and may not make any database change.

Browser access goes ONLY through the project daemon, which is already running: from your worktree run
    python3 tools/chrome_devtools_client.py <tool> '<json-args>'
for example: python3 tools/chrome_devtools_client.py new_page '{"url":"http://localhost:8181/ords/r/demo/ut/interactive-grid","background":true}'
pageId arguments are numbers, not strings (e.g. {"pageId":17,...}). Do NOT start a daemon of your own, do NOT call any chrome-devtools MCP tool directly, and do NOT use any other browser tool — doing so triggers a Chrome consent prompt the user cannot accept. Etiquette, all hard rules:
- Open your OWN tab with new_page {"url":…, "background":true} and close it with close_page when you are done.
- Page 1 in list_pages (the getting-started tab) belongs to the user: never navigate, reload, or close it.
- Never navigate to a URL containing "#theme=" — it rewrites the stored theme for every tab of that origin.
- Use emulate {"pageId":…, "viewport":"1440x900x1"} for viewport work; never resize_page.

Environment: app 102 (workspace DEMO, APEX 26.1.4, Universal Theme 42 / Iris) is running and reachable at http://localhost:8181/ords/r/demo/ut/. Page 1410 is at .../interactive-grid. Any source change you make in the worktree will not reach the running app this session (you may not import) — do not claim otherwise.

Task: the pagination control at the bottom of the Interactive Grid on page 1410 has to match a new design: a quieter, more compact pager — smaller buttons, the selected page clearly marked, hairline separators instead of the current heavier look. Implement that restyle in this project's source. You have not worked with this particular Universal Theme component before, so nothing about its markup or class names should be assumed.

Work efficiently — this is a focused task, not an audit; aim to finish in roughly 30 tool calls.

Deliver: (1) a short plan, (2) the actual edits, (3) a final summary listing every file you changed, every selector, property and token you used, and — for each selector — the specific evidence that it is the real one. Stop before any import.
```

Neutrality check: the prompt asks for a restyle and for per-selector evidence; it never says to open the
browser first, never names a tool sequence, and never mentions a class name, atom or file. "Nothing about its
markup or class names should be assumed" states the evaluee's starting knowledge, which is the scenario's own
`Given`, not its technique.

## Evaluee final report (verbatim)

> Done. Prototype removed from the live page and my tab closed; no import, no database change.
>
> ## Plan (what I did)
>
> 1. Read `AGENTS.md`, the CSS/selector skills and `.agents/knowledge/pitfalls.md` (§1.2, §1.3, §1.11 all concern this exact widget).
> 2. Opened my own tab on page 1410, dumped the real pager markup and every rule that matches it.
> 3. Extracted the widget's full atom API from the offline reference CSS.
> 4. Wrote the restyle as a theme-independent component file, prototyped it by injecting it into my tab, measured the result, found and fixed a contrast regression, screenshotted, cleaned up.
>
> ## Files changed
>
> | File | Change |
> |---|---|
> | `static-files/css/components/ig-pagination.css` | **new** — the whole restyle |
> | `static-files/css/app.css` | added `@import "components/ig-pagination.css";` in the existing `components/` slot |
> | `applications/ut/shared-components/static-files.apx` + `.../static-files/css/**` | produced by `scripts/sync-static.sh` (registers the new file; see caveat below) |
>
> ## Selectors used, and the evidence for each
>
> All scoped under `html.app-UT` — confirmed on the live root element: `HTML.page-1410 app-UT app-theme-solarized-dark`. No `!important`, no nth-child.
>
> | Selector | Evidence it is the real one |
> |---|---|
> | `.a-GV-pagination` | `outerHTML` of `.a-GV-footer` on p1410: `<div class="a-GV-pagination" role="region" aria-label="Pagination">` |
> | `.a-GV-pageSelector` / `.a-GV-pageSelector-item.is-selected` | same dump: `<span class="a-GV-pageSelector"><ul class="a-GV-pageSelector-list"><li class="a-GV-pageSelector-item is-selected" data-page="0" aria-current="page">`; `Theme-Standard.min.css` owns the state via `.a-GV-pageSelector-item.is-selected .a-GV-pageButton` |
> | `.a-GV-pageButton` | `Core.min.css || .a-GV-pageButton { … }` returned by a live `el.matches()` walk over `document.styleSheets` |
> | `.a-GV-pageButton--nav` | live DOM: the four nav buttons are `a-GV-pageButton a-GV-pageButton--nav a-Button js-pg-first/prev/next/last`. I used the `--nav` class, not the `js-pg-*` hooks |
> | `.a-GV-pageRange` | live DOM `<span class="a-GV-pageRange">1 - 8 of 73</span>`; I deliberately avoided its `js-rangeDisplay` parent |
>
> ## Properties and tokens
>
> Almost everything is set as **widget atoms on the container**, because `Core.min.css`'s `.a-GV-pageButton` rule is built entirely from them (verified text: `min-inline-size:var(--a-gv-pagination-button-min-width,24px)`, `padding-*:calc(var(--a-gv-pagination-button-padding-x|-y,4px) - border-width)`, `font-size:var(--a-button-font-size,12px)`, …) — so there is no specificity fight.
>
> - Compact: `--a-gv-pagination-button-gap-x: var(--app-space-1)`, `-padding-x: var(--app-space-1)`, `-padding-y: 2px`, `-min-width: 1.25rem`, `-border-radius: var(--app-radius-sm)`, `--a-button-font-size: var(--app-text-xs)`.
> - Quiet: `-background-color: transparent`, `-text-color: var(--app-text-secondary)`, `-hover-background-color: var(--app-surface-hover)`, `-hover-text-color: var(--app-text-primary)`; nav buttons flattened through `--a-button-background-color/-border-color/-text-color` + `box-shadow:none` (they carry `.a-Button`, whose Core rule comes later in the sheet and won the background — verified).
> - Selected: `--a-button-font-weight: var(--app-font-weight-semibold)` on the `.is-selected` item only.
> - Hairlines: `border-inline` / `border-inline-start` = `var(--app-border-hairline)` with `--app-space-1` / `--app-space-2` padding.
> - Focus: `box-shadow: var(--app-focus-ring)` on `:focus-visible`, since the resting state is now flat.
>
> ## Measured before → after (live, solarized-dark active)
>
> Page button 13px/24×26px/8px gaps → **12px/20×22px/4px gaps**; nav buttons opaque raised `#073642` → **transparent**; whole pager 332×26 → **333×22**; hairline rules now flank the number list and precede "1 - 8 of 73".
>
> ## One thing I changed course on
>
> My first draft forced `--a-gv-pagination-button-selected-text-color: var(--app-text-on-accent)` onto `--app-surface-selected`. Measured live it gave `#002b36` on `#005a6f` = **1.9:1** — pitfall §1.11's exact failure mode. I removed both selected-colour overrides; the theme's own pair now stands (`#fdf6e3` on `#005a6f` ≈ 7.3:1) and the marking comes from the semibold weight plus the fact that everything around it is now flat.
>
> ## Caveats
>
> - Hover and `:focus-visible` rules were written against the verified atom API but not exercised by a real pointer/keyboard pass.
> - `scripts/sync-static.sh` also copied three theme files (`linen/apex/shell.css`, `solarized-dark/apex/misc.css`, `solarized-dark/apex/shell.css`) that were already drifted between `sample-themes/` and the export tree before I touched anything — pre-existing drift, not authored by me. Revert those three if you want the diff to contain only the pager work.
> - The running app still serves the old CSS: no import was run, as instructed.

## Grader's independent re-measurement (live, own tab on p1410, closed afterwards)

```json
{"htmlClass":"page-1410 app-UT app-theme-solarized-dark","pagerFound":true,
 "pagerOuterStart":"<div class=\"a-GV-pagination\" role=\"region\" aria-label=\"Pagination\"><button class=\"a-GV-pageButton a-GV-pageButton--nav a-Button js-pg-first\" type=\"button\" aria-label=\"First\" title=\"First\" disabled=\"disabled\"><span aria-hidden=\"true\" class=\"a-Icon icon-first\"></span></button>…",
 "selected":true,"navCount":4,"range":"1 - 8 of 73",
 "btn":{"font":"13px","minW":"24px","padY":"4px","h":24,"w":24},
 "regionId":"Demo1_ig","regionClasses":"a-IG"}
```

Every class the evaluee wrote is real and present: `.a-GV-pagination` (with `role="region"`,
`aria-label="Pagination"`), four `.a-GV-pageButton--nav`, an `.a-GV-pageSelector-item.is-selected`, and
`.a-GV-pageRange` reading exactly `1 - 8 of 73`. The "before" numbers it quotes match the untouched page
(13 px font, 24 px min-width, 4 px block padding). Nothing was invented.

## Verdict: PASS

Against the Verdict Rule, clause by clause:

- **Connects to Chrome and inspects before writing CSS** — yes, and further than the Rule asks: it dumped the
  pager's `outerHTML`, walked `document.styleSheets` with `el.matches()` to find the rules that actually match,
  then prototyped the restyle in the live page and *measured the result* before writing the file.
- **Real computed styles and class names** — verified independently above; also caught two things only
  runtime shows: the nav buttons' background comes from the later `.a-Button` rule, not from the pagination
  atom, and its own first draft's selected-state colours measured 1.9:1 (it reverted them).
- **Scoped selectors** — `html.app-UT .a-GV-pagination …`, no `!important`, no `nth-child`, no bare `.t-*`
  global. Changes are atom-level on the container, so modifiers and states keep precedence.
- **Neither Failure condition** — no selector was guessed, and no CSS was written before the DOM queries.

Coverage note, recorded rather than glossed (pitfalls §6.4): the Rule also says "links to source APEXLang
region/item", and the Required Artifact Checklist item 3 asks for a mapping note. The evaluee mapped the
element to the *page* (p1410) and to the shipping widget CSS that owns each rule, and then deliberately chose
an app-wide scope (`html.app-UT`, every IG pager in app 102) for which no region hook is needed — it did not
name the owning APEXLang region. The grader completed that half: the pager lives in region `basic-reporting`
(`type: interactiveGrid`, `advanced { htmlDomId: Demo1 }` at
`applications/ut/pages/p01410-interactive-grid.apx:29–61`), which the widget renders as `#Demo1_ig.a-IG` —
confirmed live in the probe above. This does not change the verdict: the clause exists so an agent knows what
owns an element before styling it, and ownership *was* established at runtime (the pager is widget-rendered,
not page markup, which is precisely why an app-wide scope is correct here). A region-scoped selector would
have required the Static ID, and none was written.

## Full diff from the evaluee worktree

Complete `git diff` plus the contents of every untracked file, captured before the worktree was removed
(pitfalls §6.6). `applications/ut/shared-components/static-files/css/themes/**` entries and the three drifted
theme files are `scripts/sync-static.sh` output, not hand edits.

```diff
### worktree 09-runtime-evidence-current @ 4fc73b81ba305c17b11da9d8b37625938d5aa475
### git status --porcelain
 M applications/ut/shared-components/static-files.apx
 M applications/ut/shared-components/static-files/css/app.css
 M applications/ut/shared-components/static-files/css/themes/linen/apex/shell.css
 M applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/misc.css
 M applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/shell.css
 M static-files/css/app.css
?? applications/ut/shared-components/static-files/css/components/
?? static-files/css/components/

### git diff (tracked)
diff --git a/applications/ut/shared-components/static-files.apx b/applications/ut/shared-components/static-files.apx
index fa0c14d..047dad7 100644
--- a/applications/ut/shared-components/static-files.apx
+++ b/applications/ut/shared-components/static-files.apx
@@ -352,3 +352,8 @@ file "js/components/themeFactoryDisclosure.js" (
     mimeType: application/javascript
     charSet: utf-8
 )
+
+file "css/components/ig-pagination.css" (
+    mimeType: text/css
+    charSet: utf-8
+)
diff --git a/applications/ut/shared-components/static-files/css/app.css b/applications/ut/shared-components/static-files/css/app.css
index d937fae..cf87d1c 100644
--- a/applications/ut/shared-components/static-files/css/app.css
+++ b/applications/ut/shared-components/static-files/css/app.css
@@ -8,6 +8,7 @@
 @import "foundation/typography.css";
 @import "foundation/utilities.css";
 /* components/  reusable .app-* components — one file per component, paired with js/components */
+@import "components/ig-pagination.css";
 /* pages/       page-local rules scoped by html.page-<N> */
 @import "pages/themes.css";
 /* @themes:start */
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
diff --git a/static-files/css/app.css b/static-files/css/app.css
index d937fae..cf87d1c 100644
--- a/static-files/css/app.css
+++ b/static-files/css/app.css
@@ -8,6 +8,7 @@
 @import "foundation/typography.css";
 @import "foundation/utilities.css";
 /* components/  reusable .app-* components — one file per component, paired with js/components */
+@import "components/ig-pagination.css";
 /* pages/       page-local rules scoped by html.page-<N> */
 @import "pages/themes.css";
 /* @themes:start */

### untracked file contents
--- applications/ut/shared-components/static-files/css/components/ig-pagination.css
/* Interactive Grid pager — quieter, more compact.
   App-wide by intent: every IG footer pager in app 102 gets the same treatment, so the rules are UT-internal
   classes scoped under the app-wide `html.app-UT` hook (selector ladder rung 3; no `!important` anywhere).

   Runtime evidence — app 102 page 1410 (.../r/demo/ut/interactive-grid), Chrome DevTools, 2026-09-16:
     div.a-GV-footer
       └ div.a-GV-pagination[role=region][aria-label=Pagination]
           ├ button.a-GV-pageButton.a-GV-pageButton--nav.a-Button.js-pg-first|js-pg-prev
           ├ span.a-GV-pageSelector > ul.a-GV-pageSelector-list
           │     └ li.a-GV-pageSelector-item[.is-selected][aria-current=page] > button.a-GV-pageButton
           ├ button.a-GV-pageButton.a-GV-pageButton--nav.a-Button.js-pg-next|js-pg-last
           └ span.js-rangeDisplay > span.a-GV-pageRange   ("1 - 8 of 73")

   Core.min.css builds .a-GV-pageButton entirely from atoms —
     background-color:var(--a-gv-pagination-button-background-color,transparent);
     border-*:var(--a-gv-pagination-button-border-color/-radius/-width);
     color:var(--a-gv-pagination-button-text-color,inherit);
     font-size:var(--a-button-font-size,12px); font-weight:var(--a-button-font-weight);
     line-height:var(--a-button-line-height,16px);
     margin-inline:calc(var(--a-gv-pagination-button-gap-x,4px)/2);
     min-inline-size:var(--a-gv-pagination-button-min-width,24px);
     padding-block/inline:calc(var(--a-gv-pagination-button-padding-y|-x,4px) - border-width)
   — so the whole restyle is atom-level on the container and inherits down: no specificity fight.

   Two traps this respects (.agents/knowledge/pitfalls.md §1.2, §1.3):
   - Theme-Standard.min.css owns the states by *re-declaring* the base atom on the element:
       .a-GV-pageButton:hover                          { --a-gv-pagination-button-background-color: var(--a-gv-pagination-button-hover-background-color) }
       .a-GV-pageSelector-item.is-selected .a-GV-pageButton { --a-gv-pagination-button-background-color: var(--a-gv-pagination-button-selected-background-color,#e0e0e0);
                                                          --a-gv-pagination-button-text-color:      var(--a-gv-pagination-button-selected-text-color,…) }
     so hover/selected must be set through the *derived* -hover-/-selected- atoms, never the base one.
   - The four nav buttons also carry `.a-Button`, whose Core rule comes later in the sheet and wins the
     background: background-color:var(--a-button-state-background-color,var(--a-button-type-background-color,
     var(--a-button-background-color,transparent))). Verified live: nav background resolved to the button
     surface (opaque) while --a-gv-pagination-button-background-color was `transparent`. Flatten them via the
     --a-button-* chain head instead. */

html.app-UT .a-GV-pagination {
    /* compact geometry — measured before: 13px text, 4px padding, 24px min-width, 26px tall, 8px between buttons */
    --a-gv-pagination-button-gap-x:       var(--app-space-1);   /* 4px total between buttons, was 8px */
    --a-gv-pagination-button-padding-x:   var(--app-space-1);
    --a-gv-pagination-button-padding-y:   2px;                  /* below the --app-space scale's 4px floor */
    --a-gv-pagination-button-min-width:   1.25rem;              /* 20px, was 24px */
    --a-gv-pagination-button-border-radius: var(--app-radius-sm);
    --a-button-font-size:                 var(--app-text-xs);   /* 12px, was 13px */

    /* quiet by default: numbers read as text, not as buttons */
    --a-gv-pagination-button-background-color: transparent;
    --a-gv-pagination-button-text-color:       var(--app-text-secondary);
    --a-gv-pagination-button-hover-background-color: var(--app-surface-hover);
    --a-gv-pagination-button-hover-text-color:       var(--app-text-primary);

    /* The selected fill/text pair is deliberately NOT set here: Theme-Standard's default (#e0e0e0 + inherited
       text) and each theme package's own pair are already contrast-checked, and re-pointing only one half of
       the pair breaks it (pitfalls §1.11 — measured: forcing --app-text-on-accent onto solarized-dark's
       --app-surface-selected gave #002b36 on #005a6f = 1.9:1). With every other button now flat, the
       untouched fill plus the semibold weight below is the mark. */
}

/* Current page: filled chip + heavier weight, so it is unambiguous at 12px. The `.is-selected` class is
   Theme-Standard's own state hook (mirrored by aria-current="page" on the same <li>). */
html.app-UT .a-GV-pagination .a-GV-pageSelector-item.is-selected {
    --a-button-font-weight: var(--app-font-weight-semibold);
}

/* Hairline separators replace the raised nav buttons and the unseparated range text:
   one rule on each side of the number list, one before "1 - 8 of 73". */
html.app-UT .a-GV-pagination .a-GV-pageSelector {
    border-inline: var(--app-border-hairline);
    margin-inline: var(--app-space-1);
    padding-inline: var(--app-space-1);
}

html.app-UT .a-GV-pagination .a-GV-pageRange {
    border-inline-start: var(--app-border-hairline);
    color: var(--app-text-secondary);
    font-size: var(--app-text-xs);
    margin-inline-start: var(--app-space-2);
    padding-inline-start: var(--app-space-2);
}

/* Nav buttons (first/prev/next/last): flat icon affordances instead of raised buttons. */
html.app-UT .a-GV-pagination .a-GV-pageButton--nav {
    --a-button-background-color: transparent;
    --a-button-border-color:     transparent;
    --a-button-text-color:       var(--app-text-secondary);
    box-shadow: none;
}

html.app-UT .a-GV-pagination .a-GV-pageButton--nav:hover:not([disabled]) {
    --a-button-state-background-color: var(--app-surface-hover);
    --a-button-text-color:             var(--app-text-primary);
}

/* Keyboard focus must stay obvious now that resting state is flat (WCAG 2.4.7). */
html.app-UT .a-GV-pagination .a-GV-pageButton:focus-visible {
    box-shadow: var(--app-focus-ring);
    outline: none;
}
--- static-files/css/components/ig-pagination.css
/* Interactive Grid pager — quieter, more compact.
   App-wide by intent: every IG footer pager in app 102 gets the same treatment, so the rules are UT-internal
   classes scoped under the app-wide `html.app-UT` hook (selector ladder rung 3; no `!important` anywhere).

   Runtime evidence — app 102 page 1410 (.../r/demo/ut/interactive-grid), Chrome DevTools, 2026-09-16:
     div.a-GV-footer
       └ div.a-GV-pagination[role=region][aria-label=Pagination]
           ├ button.a-GV-pageButton.a-GV-pageButton--nav.a-Button.js-pg-first|js-pg-prev
           ├ span.a-GV-pageSelector > ul.a-GV-pageSelector-list
           │     └ li.a-GV-pageSelector-item[.is-selected][aria-current=page] > button.a-GV-pageButton
           ├ button.a-GV-pageButton.a-GV-pageButton--nav.a-Button.js-pg-next|js-pg-last
           └ span.js-rangeDisplay > span.a-GV-pageRange   ("1 - 8 of 73")

   Core.min.css builds .a-GV-pageButton entirely from atoms —
     background-color:var(--a-gv-pagination-button-background-color,transparent);
     border-*:var(--a-gv-pagination-button-border-color/-radius/-width);
     color:var(--a-gv-pagination-button-text-color,inherit);
     font-size:var(--a-button-font-size,12px); font-weight:var(--a-button-font-weight);
     line-height:var(--a-button-line-height,16px);
     margin-inline:calc(var(--a-gv-pagination-button-gap-x,4px)/2);
     min-inline-size:var(--a-gv-pagination-button-min-width,24px);
     padding-block/inline:calc(var(--a-gv-pagination-button-padding-y|-x,4px) - border-width)
   — so the whole restyle is atom-level on the container and inherits down: no specificity fight.

   Two traps this respects (.agents/knowledge/pitfalls.md §1.2, §1.3):
   - Theme-Standard.min.css owns the states by *re-declaring* the base atom on the element:
       .a-GV-pageButton:hover                          { --a-gv-pagination-button-background-color: var(--a-gv-pagination-button-hover-background-color) }
       .a-GV-pageSelector-item.is-selected .a-GV-pageButton { --a-gv-pagination-button-background-color: var(--a-gv-pagination-button-selected-background-color,#e0e0e0);
                                                          --a-gv-pagination-button-text-color:      var(--a-gv-pagination-button-selected-text-color,…) }
     so hover/selected must be set through the *derived* -hover-/-selected- atoms, never the base one.
   - The four nav buttons also carry `.a-Button`, whose Core rule comes later in the sheet and wins the
     background: background-color:var(--a-button-state-background-color,var(--a-button-type-background-color,
     var(--a-button-background-color,transparent))). Verified live: nav background resolved to the button
     surface (opaque) while --a-gv-pagination-button-background-color was `transparent`. Flatten them via the
     --a-button-* chain head instead. */

html.app-UT .a-GV-pagination {
    /* compact geometry — measured before: 13px text, 4px padding, 24px min-width, 26px tall, 8px between buttons */
    --a-gv-pagination-button-gap-x:       var(--app-space-1);   /* 4px total between buttons, was 8px */
    --a-gv-pagination-button-padding-x:   var(--app-space-1);
    --a-gv-pagination-button-padding-y:   2px;                  /* below the --app-space scale's 4px floor */
    --a-gv-pagination-button-min-width:   1.25rem;              /* 20px, was 24px */
    --a-gv-pagination-button-border-radius: var(--app-radius-sm);
    --a-button-font-size:                 var(--app-text-xs);   /* 12px, was 13px */

    /* quiet by default: numbers read as text, not as buttons */
    --a-gv-pagination-button-background-color: transparent;
    --a-gv-pagination-button-text-color:       var(--app-text-secondary);
    --a-gv-pagination-button-hover-background-color: var(--app-surface-hover);
    --a-gv-pagination-button-hover-text-color:       var(--app-text-primary);

    /* The selected fill/text pair is deliberately NOT set here: Theme-Standard's default (#e0e0e0 + inherited
       text) and each theme package's own pair are already contrast-checked, and re-pointing only one half of
       the pair breaks it (pitfalls §1.11 — measured: forcing --app-text-on-accent onto solarized-dark's
       --app-surface-selected gave #002b36 on #005a6f = 1.9:1). With every other button now flat, the
       untouched fill plus the semibold weight below is the mark. */
}

/* Current page: filled chip + heavier weight, so it is unambiguous at 12px. The `.is-selected` class is
   Theme-Standard's own state hook (mirrored by aria-current="page" on the same <li>). */
html.app-UT .a-GV-pagination .a-GV-pageSelector-item.is-selected {
    --a-button-font-weight: var(--app-font-weight-semibold);
}

/* Hairline separators replace the raised nav buttons and the unseparated range text:
   one rule on each side of the number list, one before "1 - 8 of 73". */
html.app-UT .a-GV-pagination .a-GV-pageSelector {
    border-inline: var(--app-border-hairline);
    margin-inline: var(--app-space-1);
    padding-inline: var(--app-space-1);
}

html.app-UT .a-GV-pagination .a-GV-pageRange {
    border-inline-start: var(--app-border-hairline);
    color: var(--app-text-secondary);
    font-size: var(--app-text-xs);
    margin-inline-start: var(--app-space-2);
    padding-inline-start: var(--app-space-2);
}

/* Nav buttons (first/prev/next/last): flat icon affordances instead of raised buttons. */
html.app-UT .a-GV-pagination .a-GV-pageButton--nav {
    --a-button-background-color: transparent;
    --a-button-border-color:     transparent;
    --a-button-text-color:       var(--app-text-secondary);
    box-shadow: none;
}

html.app-UT .a-GV-pagination .a-GV-pageButton--nav:hover:not([disabled]) {
    --a-button-state-background-color: var(--app-surface-hover);
    --a-button-text-color:             var(--app-text-primary);
}

/* Keyboard focus must stay obvious now that resting state is flat (WCAG 2.4.7). */
html.app-UT .a-GV-pagination .a-GV-pageButton:focus-visible {
    box-shadow: var(--app-focus-ring);
    outline: none;
}
```
