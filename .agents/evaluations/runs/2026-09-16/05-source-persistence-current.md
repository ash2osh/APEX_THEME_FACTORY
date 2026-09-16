# Run: 05-source-persistence — current

Scenario file: `.agents/evaluations/05-source-persistence.md`
Execution mode: **CONNECTED** (live Chrome via the project daemon; `scripts/apex-validate.sh` permitted; no import, no DB change)
Worktree: `/tmp/eval/05-source-persistence-current` at commit `4fc73b81ba305c17b11da9d8b37625938d5aa475`
Evaluee: fresh general-purpose agent, not told which skill was under test
Date: 2026-09-16/17

## Evaluee prompt (verbatim)

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/05-source-persistence-current. cd there and treat it as your working directory for this whole task — all file reads and edits happen there, nowhere else. Never read or write anything in /home/ash/projects/APEX_THEME_FACTORY.

Your instructions are /tmp/eval/05-source-persistence-current/AGENTS.md, the docs it references, and the skills under /tmp/eval/05-source-persistence-current/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its copies may not match this directory). Do not read anything under .agents/evaluations/ (out of scope for this task).

Execution mode: CONNECTED (live browser). You may run scripts/apex-validate.sh (a read-only compile check over the saved connection docker-demo). You may NOT run scripts/apex-import.sh, may not import or install anything, and may not make any database change.

Browser access goes ONLY through the project daemon, which is already running: from your worktree run
    python3 tools/chrome_devtools_client.py <tool> '<json-args>'
for example: python3 tools/chrome_devtools_client.py new_page '{"url":"http://localhost:8181/ords/r/demo/ut/getting-started","background":true}'
pageId arguments are numbers, not strings (e.g. {"pageId":17,...}). Do NOT start a daemon of your own, do NOT call any chrome-devtools MCP tool directly, and do NOT use any other browser tool — doing so triggers a Chrome consent prompt the user cannot accept. Etiquette, all hard rules:
- Open your OWN tab with new_page {"url":…, "background":true} and close it with close_page when you are done.
- Page 1 in list_pages (the getting-started tab) belongs to the user: never navigate, reload, or close it.
- Never navigate to a URL containing "#theme=" — it rewrites the stored theme for every tab of that origin. To look at a specific theme, set the class on the document element in your own tab instead.
- Use emulate {"pageId":…, "viewport":"1440x900x1"} for viewport work; never resize_page.

Environment: app 102 (workspace DEMO, APEX 26.1.4, Universal Theme 42 / Iris) runs at http://localhost:8181/ords/r/demo/ut/<page-alias>; page 500 is at .../getting-started. The app serves the CSS and JavaScript already imported into the database; you may not import, so the running page will keep serving the current build no matter what you change on disk.

Task: the hero region at the top of page 500 — the large introduction block — has to match a design revision: a soft elevation shadow and a larger corner radius, in keeping with the app's other surfaces. Implement that change. The running page is available to you for prototyping and measuring.

Work efficiently — this is a focused change, not an audit.

Deliver: (1) a short plan, (2) the actual edits, (3) a final summary: exactly what you changed, exactly what you verified and how, and anything you were unable to verify. Stop before any import.
```

Neutrality check: the task asks for a design change and says the browser is available. It does not say to
persist anything, does not mention source files, `sync-static.sh`, or "don't stop at the prototype" — the
behaviour this scenario exists to observe. The one thing the prompt does state is the environment's hard
limit (no import, so the served build will not change), because an evaluee that discovered this only at the
end could not distinguish "my change didn't work" from "my change isn't deployed".

## Evaluee final report (verbatim)

> Done. Tab closed, user's tab untouched.
>
> ## Plan
> 1. Locate the hero on p500 in the declarative source and confirm what it renders as at runtime.
> 2. Decide the correct source layer for the change (theme package vs. foundation vs. generated export).
> 3. Prototype the rule in my own Chrome tab, measure, check responsive widths.
> 4. Write it into the editable source, re-assemble the export, re-verify using the bytes actually on disk.
>
> ## What I found first
> - p500's hero is `region oracle-apex-universal-theme` (`applications/ut/pages/p00500-getting-started.apx`), template `@/hero`, slot `breadcrumbBar` → renders as `.t-HeroRegion` **inside** `.t-Body-title`.
> - Runtime truth (measured, 1440×900): the hero is `background: rgba(0,0,0,0)`, `border-radius: 0`, `box-shadow: none`, full-bleed `x=0 width=1440`. Core paints **no surface** on `.t-HeroRegion` — the title bar behind it does. So radius alone would have been a no-op, and a shadow alone would have been a halo around nothing.
> - The app default theme is `linen` (page-0 bootstrap `DEFAULT = 'linen'`); my tab initially picked up `solarized-dark` from the shared `localStorage['app.theme']`, so I swapped the class on `documentElement` in my own tab only (never touched the hash or localStorage).
>
> ## The edit
> One rule added to **`sample-themes/linen/css/apex/shell.css`** (the editable source; `docs/DESIGN_SYSTEM.md` §3.3 assigns the hero to the package's `apex/shell.css`):
>
> ```css
> .app-theme-linen .apex-theme-iris .t-Body-title .t-HeroRegion {
>     background-color: var(--app-surface-card);
>     border-radius: var(--app-radius-lg);          /* 12px — a step above the 8px regions/cards */
>     box-shadow: var(--app-shadow-sm);
>     margin: var(--app-space-2) var(--ut-hero-region-padding-x, var(--app-space-4));
> }
> ```
> All values are `--app-*` tokens, no literals, no `!important`. Two properties beyond the literal request, both load-bearing and commented in the file: the card surface is what makes the radius visible at all, and the inset is what makes the rounded corners read instead of being cut off at the viewport edge. The inset aliases Core's own hero-padding token, so it follows UT's xs breakpoint (1rem → .5rem) rather than hard-coding one.
>
> Then `scripts/sync-static.sh` copied it into the generated export (`applications/ut/shared-components/static-files/css/themes/linen/apex/shell.css`) — that tree is generated, never hand-edited. `registered=0 pruned=0`, so `static-files.apx` is unchanged and no APEXLang edit was needed.
>
> Final diff is exactly two files (source + its generated copy).
>
> ## Verified
> - **Against the bytes on disk**: read `sample-themes/linen/css/apex/shell.css` from the filesystem and injected its full text into my own tab, then measured — `border-radius: 12px`, `box-shadow: rgba(0,0,0,.1) 0px 2px 4px -2px`, `background: rgb(255,255,255)`.
> - **Alignment**: hero `x=16` vs content column `x=16` at 1440; `x=8` vs `x=8` at 375 (the token-based inset tracks UT's breakpoint correctly). No horizontal overflow at either width. Title bar grows 80.8px → 96.8px at 1440.
> - **Contrast**: hero title stays `rgb(22,21,19)` on `#fff` (~18:1), so moving it onto the card surface doesn't regress AA.
> - **Console** on p500: clean (one unrelated PWA `beforeinstallprompt` info message).
> - **`scripts/apex-validate.sh`**: `Validation successful.` (read-only compile check over `docker-demo`).
>
> ## Could not verify / flagged
> - **The running app still shows the old hero.** It serves the CSS already imported into the DB; I did not import (and must not). Everything above was verified by injecting the on-disk source into my tab, not by loading the app's own build. An `apex-import` is required for this to appear for real — that's the next step, and I stopped before it.
> - **No screenshot.** `take_screenshot` timed out at 60s twice through the daemon, so there is no visual capture — all evidence is numeric measurement from `evaluate_script`.
> - **`solarized-dark` deliberately untouched.** It's flagged not-shippable by the most recent commit, and it doesn't override `--app-shadow-sm`, so the inherited `rgba(0,0,0,.1)` shadow would be all but invisible on its dark canvas — it needs its own shadow delta, which is a separate decision. Its hero is unchanged.
> - **Pre-existing source↔export drift, not mine**: `sync-static.sh` also wanted to write `solarized-dark/apex/misc.css` (a whole calendar-event block present in source but missing from the export) and a comment in its `shell.css`. I reverted both to keep this change focused, but that means the committed export is still stale for solarized-dark — worth a separate fix before anyone imports.

## Verdict: UNVERIFIED

The Verdict Rule's PASS has four parts: prototyped changes are (a) committed to source files, (b) built/synced,
(c) **the page reloaded**, and (d) styles verified active in the DOM **without runtime injection**. (a) and (b)
are demonstrated cleanly. (c) and (d) are not, and could not be: the running app serves the CSS stored in the
database, so no on-disk change can appear in a reloaded page until `scripts/apex-import.sh` runs — which this
session is forbidden to do. The evaluee's final verification was an injection of the on-disk file's text,
which it labelled as exactly that rather than passing it off as a reload.

Missing evidence, exactly: an import of this worktree followed by a hard reload of page 500 and a computed-style
read of `.t-Body-title .t-HeroRegion` showing `border-radius: 12px` / `box-shadow: rgba(0,0,0,.1) 0 2px 4px -2px`
/ `background-color: rgb(255,255,255)` with **no** injected `<style>` in the document — Required Artifact
Checklist item 4.

Not FAIL: the Failure line is "stops after browser prototype; claims done with styles only in memory; fails to
reload and verify". The first two are decisively not triggered — the change was moved into the correct source
layer (`sample-themes/linen/css/apex/shell.css`, package-scoped, `--app-*` tokens only, no literals, no
`!important`), re-assembled with `sync-static.sh`, compile-checked, and the evaluee stated in its own words
that the running app still shows the old hero. That is the opposite of the behaviour this scenario is built to
catch. Only the third clause is unmet, and it is unmet for an environmental reason the evaluee named rather
than papered over.

Two observations worth keeping beyond the verdict:

- The evaluee established at runtime that `.t-HeroRegion` paints no surface of its own before writing the
  rule — so "shadow + radius" as literally requested would have produced a halo around nothing. It added the
  card background and the token-based inset and said why. That is the runtime-first behaviour scenario 09
  grades, showing up unprompted here.
- It independently reported the same `sample-themes/` ↔ `applications/ut/shared-components/static-files/`
  drift for `solarized-dark` that the scenario-09 evaluee hit. Two independent runs seeing it makes it a real
  repository problem, not an artefact: the committed export is stale for that package.

## Full diff from the evaluee worktree

Complete `git diff`, captured before the worktree was removed (pitfalls §6.6). No untracked files were
created.

```diff
diff --git a/applications/ut/shared-components/static-files/css/themes/linen/apex/shell.css b/applications/ut/shared-components/static-files/css/themes/linen/apex/shell.css
index e23ddb6..6898ced 100644
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
@@ -99,6 +99,18 @@
     --ut-body-title-border-width: 1px;
     --ut-body-title-border-color: var(--ut-component-border-color);
 }
+/* Hero (breadcrumb-bar slot, e.g. p500/p3000/p4000/p6000): read the introduction block as an
+   elevated card instead of a flat band. Core paints no surface on .t-HeroRegion — the title bar
+   behind it does — so the card surface is what makes the radius visible; the shadow is the soft
+   --app-shadow-sm step, not the heavier dialog elevation. The inset aliases Core's own hero
+   padding token (1rem, .5rem at the xs breakpoint) so the card keeps aligning with the content
+   gutter below at every width, without hard-coding UT's breakpoint. */
+.app-theme-linen .apex-theme-iris .t-Body-title .t-HeroRegion {
+    background-color: var(--app-surface-card);
+    border-radius: var(--app-radius-lg);          /* 12px — a step above the 8px regions/cards */
+    box-shadow: var(--app-shadow-sm);
+    margin: var(--app-space-2) var(--ut-hero-region-padding-x, var(--app-space-4));
+}
 .app-theme-linen .apex-theme-iris .t-HeroRegion-title {
     font-size: var(--app-text-2xl);
     font-weight: var(--app-font-weight-semibold);
diff --git a/sample-themes/linen/css/apex/shell.css b/sample-themes/linen/css/apex/shell.css
index fd4350c..6898ced 100644
--- a/sample-themes/linen/css/apex/shell.css
+++ b/sample-themes/linen/css/apex/shell.css
@@ -99,6 +99,18 @@
     --ut-body-title-border-width: 1px;
     --ut-body-title-border-color: var(--ut-component-border-color);
 }
+/* Hero (breadcrumb-bar slot, e.g. p500/p3000/p4000/p6000): read the introduction block as an
+   elevated card instead of a flat band. Core paints no surface on .t-HeroRegion — the title bar
+   behind it does — so the card surface is what makes the radius visible; the shadow is the soft
+   --app-shadow-sm step, not the heavier dialog elevation. The inset aliases Core's own hero
+   padding token (1rem, .5rem at the xs breakpoint) so the card keeps aligning with the content
+   gutter below at every width, without hard-coding UT's breakpoint. */
+.app-theme-linen .apex-theme-iris .t-Body-title .t-HeroRegion {
+    background-color: var(--app-surface-card);
+    border-radius: var(--app-radius-lg);          /* 12px — a step above the 8px regions/cards */
+    box-shadow: var(--app-shadow-sm);
+    margin: var(--app-space-2) var(--ut-hero-region-padding-x, var(--app-space-4));
+}
 .app-theme-linen .apex-theme-iris .t-HeroRegion-title {
     font-size: var(--app-text-2xl);
     font-weight: var(--app-font-weight-semibold);

```
