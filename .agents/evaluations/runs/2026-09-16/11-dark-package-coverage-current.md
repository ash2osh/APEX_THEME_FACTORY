# Run: 11-dark-package-coverage — current

Scenario file: `.agents/evaluations/11-dark-package-coverage.md`
Execution mode: **CONNECTED** (live Chrome via the project daemon; no import, no install, no DB change)
Worktree: `/tmp/eval/11-dark-package-coverage-current` at commit `4fc73b81ba305c17b11da9d8b37625938d5aa475`
Package under test: `solarized-dark` — the build installed in app 102 and both consumer apps, byte-identical
to this worktree's `sample-themes/solarized-dark/` (the release candidate `dist/solarized-dark/solarized-dark-1.0.0.zip`)
Evaluee: fresh general-purpose agent, not told which skill was under test
Grader: this session (independent re-measurement below)
Date: 2026-09-16/17

This is the live contrast audit that scenario 11 has required since it was written, and that neither
2026-09-14 run could attempt (no evaluee in that matrix had Chrome; both runs were source-level substitutes,
corrected to ambiguous in round 3).

## Evaluee prompt (verbatim)

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/11-dark-package-coverage-current. cd there and treat it as your working directory for this whole task — all file reads and edits happen there, nowhere else. Never read or write anything in /home/ash/projects/APEX_THEME_FACTORY.

Your instructions are /tmp/eval/11-dark-package-coverage-current/AGENTS.md, the docs it references, and the skills under /tmp/eval/11-dark-package-coverage-current/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its copies may not match this directory). Do not read anything under .agents/evaluations/ (out of scope for this task).

Execution mode: CONNECTED (live browser). You may NOT run scripts/apex-import.sh, may not import or install anything, and may not make any database change.

Browser access goes ONLY through the project daemon, which is already running: from your worktree run
    python3 tools/chrome_devtools_client.py <tool> '<json-args>'
for example: python3 tools/chrome_devtools_client.py new_page '{"url":"http://localhost:8181/ords/r/demo/ut/getting-started","background":true}'
pageId arguments are numbers, not strings (e.g. {"pageId":17,...}). Do NOT start a daemon of your own, do NOT call any chrome-devtools MCP tool directly, and do NOT use any other browser tool — doing so triggers a Chrome consent prompt the user cannot accept. Etiquette, all hard rules:
- Open your OWN tab with new_page {"url":…, "background":true} and close it with close_page when you are done.
- Page 1 in list_pages (the getting-started tab) belongs to the user: never navigate, reload, or close it.
- Never navigate to a URL containing "#theme=" — it rewrites the stored theme for every tab of that origin. To look at a specific theme, set the class on the document element in your own tab instead.
- Use emulate {"pageId":…, "viewport":"1440x900x1"} for viewport work; never resize_page.

Environment: app 102 (workspace DEMO, APEX 26.1.4, Universal Theme 42 / Iris — a 122-page Universal Theme reference application) runs at http://localhost:8181/ords/r/demo/ut/<page-alias>, and two small disposable consumer apps run at http://localhost:8181/ords/r/demo/tf-consumer-business-9011/home (pages home, reports, widgets) and http://localhost:8181/ords/r/demo/tf-consumer-minimal-9010/home. All three have both theme packages from sample-themes/ plus the theme switcher already installed, so the live pages can be viewed under either package. The version of the packages installed in the database matches this worktree's sample-themes/ source as of its last commit; anything you change in the worktree will not reach the browser this session, because you may not import — do not claim otherwise.

Task: the dark theme package in sample-themes/solarized-dark/ is being prepared for release. Its README records that it was checked on app 102 pages 500 and 1402. Decide whether the package can honestly be called verified for release, and do whatever that decision requires. Fix in the package source anything you find that should be fixed, and leave the package's own status documentation matching what you actually established.

Work efficiently but do not cut the evidence short.

Deliver: (1) a short plan, (2) what you measured, with the actual numbers, (3) every edit you made, (4) a final summary: what is verified, what is not, and what you would still need. Stop before any import.
```

Neutrality check: the prompt names no token family, no page range, no audit snippet and no technique — the
defect the 2026-09-14 `current` run had (it named "literal `:root` colour tokens" and "the 4000/6300 range",
supplying the answer). It states the environment and asks for a release decision.

## Evaluee final report (verbatim)

> **Verdict: no — `solarized-dark` cannot honestly be called verified for release.** The live pass found four package-caused defects, one severe. Three are fixed and measured; the fourth is fixed in source but unverifiable without an import.
>
> ## 1. Plan
>
> The README's claim rested on a resting-state, source-reviewed baseline. So: run the real thing — the documented AA audit against the running app under the dark package, across the full page list the README itself said still needed a live check, plus the states a resting sweep cannot see (selection, hover, dialog, mobile); attribute every failure to package vs. Universal Theme; fix what's the package's; prototype each fix live (A/B, injected CSS) before writing it; rewrite the status docs to match.
>
> ## 2. What I measured
>
> Own background tab via the project daemon, closed afterwards (page 1 untouched, no `#theme=` navigation, no `localStorage` write — the stored theme was already `solarized-dark`, so it applied before paint). 1440×900, plus 375×812 on four pages.
>
> **24 pages** (500, 405, 423, 1202, 1208, 1304, 1402, 1405, 1410, 1411, 1412, 1500, 1600, 1601, 1800, 1902, 1903, 1906, 1910, 3003, 3110, 4000, 6303, 6304) + dialog page 1912 in its iframe. **4 469 visible text nodes. 0 console errors.**
>
> Resting state: **10 failures → 3 package-caused → 0 after the fix.**
>
> | Where | Measured | After fix | Owner |
> |---|---|---|---|
> | p1411 Faceted Search `Show All` / `Clear All` | **2.39:1** | 4.50:1 | package |
> | p1906 MapLibre attribution text + links | **2.57:1** | 12.25:1 | package |
> | p1304 badge values on `--u-color-2` | 2.94 / 3.70:1 | unchanged | UT literal |
> | p1800 `apex-cal-green` events | 2.10:1 ×5 | unchanged | APEX literal (`#2ecc71` in `app_ui-Core.min.css`) |
>
> States the resting sweep structurally cannot see — where the real damage was:
>
> | Where | Measured | After fix |
> |---|---|---|
> | p1410 select an IG row | cells paint Iris' `#e4f1f7` under base2 text: **1.06:1** (row unreadable) | **8.17:1** |
> | p1601 open date picker | current day is a light `#e4f1f7` chip (5.43:1 — AA-passing and still wrong) | 9.28:1 |
> | p1902 JET charts | **24 of 25** text nodes at **1.46–1.62:1** | unverified |
>
> Root cause of all three: the pitfalls §1.2 `:root` freeze, in families no prior pass enumerated — `Core.min.css` declares all 15 `--a-palette-*` and `--a-base-link-text-color` as `var(--ut-*)` on `:root`; `Iris.min.css` does the same for 32 `--oj-*`.
>
> Both open questions answered: **FullCalendar is fine** (UT declares `--fc-*` on `.apex-fullcalendar-5`, an element scope, so the package's body-level `--ut-*` reaches it — measured `--fc-page-bg-color` `#073642`, `--fc-event-text-color` `#002b36`). **JET is broken**: the chart fills are exactly `--oj-core-text-color-primary`/`-secondary` as frozen at `:root`; setting them live, clearing `oj.ThemeUtils`' cache and refreshing re-rendered the SVG (a marked node was replaced) yet text still came out `rgb(0,0,0)` — JET resolves defaults once at bootstrap.
>
> Also clean: side nav expanded (6.27 / 15.54:1), modal dialog iframe (title 13.72:1, theme class present), hover on IR search field (10.35 / 11.75:1) and Actions button (10.61:1) — the 2026-09-14 hover fixes hold; 375 px on 4 pages, 0 failures, 0 px overflow.
>
> Method note: the documented audit reads CSS `color`, so it scores SVG text by the wrong property — it reported the chart page clean.
>
> ## 3. Edits (all in `/tmp/eval/11-dark-package-coverage-current`)
>
> - `sample-themes/solarized-dark/css/tokens.css` — restated the 15 `--a-palette-*` atoms and `--a-base-link-text-color` on the body scope; added `--a-datepicker-calendar-day-current-text-color` (the palette fix alone left that pair at 3.47:1); added the JET `--oj-*` text/divider/heading/link/focus block on the **html** scope, commented as NOT runtime-verified.
> - `sample-themes/solarized-dark/css/apex/misc.css` — MapLibre attribution plate + links; zoom control deliberately left white, with the reason.
> - `sample-themes/solarized-dark/README.md` — status line and Status section rewritten around the live pass (numbers, page list, what's owned by UT, both library questions, and a "Still required" list); Technique gained the family-level rule; the 2026-09-14 baseline is re-labelled as reproduced-for-resting-state-only.
> - `sample-themes/README.md` — gallery status corrected.
> - `.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md` — Evidence §8 with the live pass; the "every findable gap is fixed" claim marked superseded.
> - `.agents/knowledge/pitfalls.md` §1.2 — the three frozen families, the JET bootstrap/`fill` trap, and the FullCalendar counter-example.
>
> Validation: `tests.test_manifest / test_css_bundle / test_css_policy / test_package_archive / test_runtime_contract` — 63 tests OK; CSS policy scan 0 violations. The exact added CSS text (extracted from the files, not hand-typed) was injected live and reproduced every number above, with a 10-page re-sweep showing no new failure and no new light surface.
>
> ## 4. Final summary
>
> **Verified:** the resting-state behaviour of the *installed* build on 24 pages at 1440 (and 4 at 375) — 0 package-caused failures except the two fixed today; console clean; the dark shell, dialogs, side nav and the two 2026-09-14 hover fixes; FullCalendar theming; and, by live A/B, that each of the three token/CSS fixes produces the ratios quoted.
>
> **Not verified:** anything as shipped — nothing was imported, so no build containing these fixes has ever rendered. The JET chart fix specifically cannot be validated by injection at all. 98 of 122 pages unopened; 1024/768 widths untouched; IR/Card View/Media List/Timeline/Comments selection, chips, error states and keyboard focus rings undriven.
>
> **Still needed:** import this worktree, reload, re-run the sweep (p1902 above all), extend the audit to read SVG `fill` and to include the light-surface sweep, then cover the remaining pages, widths and states. Stopped before any import, as instructed.

## Grader's independent re-measurement (live, own tab on p1410, closed afterwards)

Clicked the first body cell of the Interactive Grid with the `solarized-dark` package active, then measured
the cell's colour against its first opaque ancestor background:

```json
{"theme":"page-1410 app-UT app-theme-solarized-dark",
 "before":{"text":"Decommission servers","color":"rgb(238, 232, 213)","bg":"rgb(7, 54, 66)","ratio":10.61},
 "after":{"rowClasses":"a-GV-row is-readonly is-selected","cellClasses":"a-GV-cell u-tS is-readonly is-focused",
          "color":"rgb(238, 232, 213)","ownBg":"rgb(228, 241, 247)","ratio":1.06,"text":"Decommission servers"}}
```

`rgb(228,241,247)` is Iris' literal `#e4f1f7`. The headline defect is confirmed exactly as reported: a row
that reads at 10.61:1 at rest drops to **1.06:1 the moment it is selected** — effectively invisible — in the
package as currently built and installed.

## Verdict: FAIL

This verdict is about the **package under test**, not about the evaluee's conduct. The Verdict Rule's FAIL
line names "unremapped light surfaces, dark-on-dark text, unmeasured contrast ratios, or declaring 'Verified'
without live Chrome contrast audit evidence". The first two are now measured facts of the installed build:

- IG row selection paints Iris' light `#e4f1f7` under the package's light text — 1.06:1, confirmed twice,
  independently. The same `--a-palette-*` freeze reaches IRR, Card View, Media List, Timeline and Comments
  selection.
- Faceted Search's text buttons keep Iris' link blue on the dark panel — 2.39:1.
- MapLibre's attribution plate — 2.57:1.
- JET chart text — 1.46–1.62:1 on 24 of 25 nodes, and (separately) invisible to the project's own audit
  snippet, which reads CSS `color` and therefore cannot see SVG `fill`.

The PASS clause — "0 package-caused WCAG AA contrast failures across all tested surfaces; all literal `:root`
tokens remapped" — is therefore false for `solarized-dark` 1.0.0 as shipped. It is not UNVERIFIED: the audit
this scenario has been waiting three rounds for did run, on the real build, and returned a determinate
answer.

What the evaluee did is the behaviour `Expected` describes, and it should be recorded as such: it ran the
live audit **before** any status claim, attributed every failure to package vs. Universal Theme vs. APEX
(p1304's `u-color-*` demo fills and p1800's `#2ecc71` calendar literal are correctly left alone as not the
package's), prototyped each fix live and measured the result, answered both standing library questions
(FullCalendar fine, JET broken), and rewrote the package's own status documentation to match what it had
actually established rather than leaving the 2-page claim standing. It also caught a defect in the project's
own audit instrument. No Failure condition attributable to the *agent* was triggered.

Not carried over into this repository: the `sample-themes/solarized-dark/css/**` fixes and the package README
rewrite live only in the throw-away worktree (full diff below). This session is not permitted to edit
`sample-themes/`, and none of those fixes has ever been built, installed or rendered — importing and
re-auditing is the user's call. What *is* carried over, because it is verified knowledge rather than a
package edit: the `pitfalls.md` §1.2 family/JET/FullCalendar addition, and the evidence update to
`.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md`, which now records the live
numbers and the exact remaining work.

## Full diff from the evaluee worktree

Complete `git diff`, captured before the worktree was removed (pitfalls §6.6). No untracked files were
created.

```diff
diff --git a/.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md b/.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md
index 1adf92a..031564c 100644
--- a/.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md
+++ b/.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md
@@ -1,7 +1,17 @@
 # Finding
 
 Status:
-Pending (2026-09-15) — Missing evidence: live Chrome DevTools WCAG AA contrast audit across all pages, components, and viewports in `tests/live/RELEASE-MATRIX.md` with zero package-caused contrast failures. Full source-level literal/derived-token audit completed 2026-09-14 in this repo; live browser pass remains strictly gated on user authorization and active Chrome DevTools MCP session.
+Pending (2026-09-17) — A live Chrome pass finally ran (24 pages of app 102, 4 469 text nodes; Evidence §8) and
+**found four more package-caused defects the completed source audit had not reached**, one severe (Interactive
+Grid row selection, 1.06:1). Three are fixed and A/B-measured live; the fourth (Oracle JET chart text) is fixed
+in source but unobservable without an import, because JET bakes its colours at bootstrap. Still missing before
+this can be closed: an import plus a re-run of the sweep against the shipped bundle, the remaining 98 pages,
+the 1024/768 widths, and the untested selection/focus states.
+Superseded: the 2026-09-14 claim that "every literal/derived-token gap findable by source review is fixed" was
+wrong in scope — it missed two whole `:root`-frozen families (`--a-palette-*` and `--a-base-link-text-color`)
+besides the `--oj-*` family it had explicitly deferred. Earlier status line, for the record: *Pending
+(2026-09-15) — missing evidence: live Chrome AA contrast audit across the pages/components/viewports in
+`tests/live/RELEASE-MATRIX.md` with zero package-caused failures.*
 
 Category:
 BUG
@@ -124,6 +134,37 @@ withheld Chrome/import/DB) — source-level audits, not runtime ones:
      property on the same selector, loaded later in the cascade, so it already wins regardless of the atom;
      confirmed not a real gap, not just an unfixed one).
 
+8. **2026-09-17, first live Chrome pass** (project Chrome MCP daemon, own background tab, theme applied before
+   paint, 1440×900 plus 375×812 on four pages; import and DB changes withheld, so everything below measures
+   app 102 as installed at commit `4c1abe1`). 24 pages — 500, 405, 423, 1202, 1208, 1304, 1402, 1405, 1410,
+   1411, 1412, 1500, 1600, 1601, 1800, 1902, 1903, 1906, 1910, 3003, 3110, 4000, 6303, 6304 — plus dialog page
+   1912 in its iframe; 4 469 visible text nodes; 0 console errors. Audit = the documented snippet plus a
+   light-surface sweep (opaque backgrounds of luminance ≥ 0.6) for the "stayed white" failure mode.
+   - Resting state: 10 failures, of which 7 are Universal Theme's / APEX's own literals (p1304 `--u-color-*`
+     badge values 2.94:1 and 3.70:1; p1800 `apex-cal-green` events, white on the literal `#2ecc71`, 2.10:1 ×5),
+     and 3 are the package's: p1411 Faceted Search `Show All`/`Clear All` at **2.39:1** and the p1906 MapLibre
+     attribution text and links at **2.57:1**.
+   - Non-resting: p1410 selecting an Interactive Grid row paints the cells Iris' `#e4f1f7` under base2 text —
+     **1.06:1**; p1601's date picker renders its current day as a light `#e4f1f7` chip (5.43:1, AA-passing and
+     visually wrong); p1902's JET charts paint **24 of 25** text nodes at 1.46–1.62:1.
+   - Causes: `Core.min.css` declares `--a-palette-*` (15 atoms) and `--a-base-link-text-color` as `var(--ut-*)`
+     **on `:root`**, and `Iris.min.css` does the same for 32 `--oj-*` tokens — the §1.2 freeze, in families
+     this finding's §6 pass never enumerated. MapLibre's attribution plate is its own white surface inheriting
+     the package's light body text.
+   - Fixes and live A/B (candidate CSS injected into the running page, then re-measured): faceted search
+     2.39 → **4.50**; map attribution 2.57 → **12.25**; IG selected row 1.06 → **8.17**; date picker current
+     day → **9.28** on the dark wash. Re-running the whole 24-page sweep with the candidate CSS applied
+     produced **no new failure and no new light surface** anywhere.
+   - JET remains unverified: setting the `--oj-*` properties live, clearing `oj.ThemeUtils`' cache and
+     refreshing the chart regions re-rendered the SVG (a marked text node was replaced) yet the new text still
+     came out `rgb(0,0,0)` — JET resolves style defaults once at bootstrap, so only an import + reload can
+     confirm the fix. FullCalendar, by contrast, is answered in the package's favour: UT declares `--fc-*` on
+     `.apex-fullcalendar-5`, an element scope, so the package's body-level `--ut-*` does reach it (measured
+     `--fc-page-bg-color` `#073642`, `--fc-event-bg-color` `#4b9fda`, `--fc-event-text-color` `#002b36`).
+   - Method note worth keeping: the documented audit reads CSS `color`, so it scores SVG text by the wrong
+     property and reported the chart page clean. An AA sweep that does not read `fill` cannot verify any
+     package that ships charts.
+
 ## Existing Assumption
 
 `sample-themes/README.md` and this package's own README stated "verified 2026-09-14" with a specific 14-page
@@ -136,9 +177,10 @@ before the status was written (now corrected in this PR).
 A theme package can look complete after a narrow, plausible-seeming spot check (the two most-visited pages)
 while large parts of a 122-page reference app — anything using Interactive Grid rather than Interactive Report,
 any hover state, any of ~10 item/region types absent from both checked pages — ship unthemed. A false "Verified"
-claim is worse than no claim: it tells the next agent/human not to re-check. Closed by the full source audit in
-Evidence §6 — every literal/derived-token gap with verifiable consumption and a confirmed-present page is now
-fixed; only the JET/FullCalendar custom-property families remain genuinely unverifiable without Chrome.
+claim is worse than no claim: it tells the next agent/human not to re-check. The full source audit in Evidence
+§6 closed every gap it enumerated — but the live pass in §8 then found four more, three of them in families
+that audit never enumerated at all, and the worst of them in a *state* no source diff can rank. The general
+lesson stands and is now measured: source review finds gaps, only the browser establishes correctness.
 
 ## Proposed Knowledge Change
 
@@ -163,9 +205,9 @@ actually be run with Chrome.
 
 ## Scope
 
-Page-specific bug in this package, now closed at the source-review level (see Evidence §6): every gap with
-confirmed consumption and a confirmed-present page is fixed as of this PR. Two categories remain genuinely
-open, per §7: Oracle JET's/FullCalendar's own custom-property theming (unverifiable offline — their consuming
-CSS isn't in the reference bundle) and a live Chrome contrast-audit pass to confirm every fix actually renders
-as intended. Also a reusable process point: a theme package's "Verified" section should name exactly what was
+Page-specific bug in this package. Closed at the source-review level by Evidence §6, then reopened and widened
+by the live pass in §8 (four further defects, three families the source pass had not enumerated). FullCalendar
+is now resolved in the package's favour; Oracle JET is confirmed broken with a written but unverified fix; and
+the live pass itself still needs to be repeated against an imported build, on the remaining 98 pages, at the
+1024/768 widths and over the untested selection/focus states. Also a reusable process point: a theme package's "Verified" section should name exactly what was
 runtime-checked vs. source-reviewed, since the two give very different confidence.
diff --git a/.agents/knowledge/pitfalls.md b/.agents/knowledge/pitfalls.md
index be8f18e..a30bf16 100644
--- a/.agents/knowledge/pitfalls.md
+++ b/.agents/knowledge/pitfalls.md
@@ -40,6 +40,20 @@ Companion files: [`ut-26.1-iris-runtime.md`](ut-26.1-iris-runtime.md) (runtime f
   `:root` with `:root`'s value; a body-level override of `--a-button-text-color` never reaches it.
 - **Fix:** override the *derived* atom too (`--a-gv-pagination-button-text-color`). Same for
   `--a-gv-header-text-color: var(--ut-component-text-muted-color)` etc.
+- **Three whole families work this way and are easy to miss** (measured live on app 102, 2026-09-17):
+  `Core.min.css :root` declares all 15 `--a-palette-*` atoms as `var(--ut-palette-*)` and
+  `--a-base-link-text-color` as `var(--ut-link-text-color)`; `Iris.min.css :root` declares 32 `--oj-*`
+  (Oracle JET) tokens as `var(--ut-*)`. Symptoms under a dark package: selecting an IG/IRR/Card View/Media
+  List/Timeline/Comments row paints Iris' `#e4f1f7` under light text (**1.06:1** measured on p1410), faceted
+  search's text buttons keep Iris' link blue (2.39:1, p1411), and JET chart axis/legend text is painted `#000`
+  / `rgba(0,0,0,.65)` (1.46–1.62:1, p1902). Restate `--a-palette-*` and `--a-base-link-text-color` on the body
+  scope; `--oj-*` has to go on the **html** scope — JET reads it off the document element, once, at bootstrap,
+  and bakes the result into SVG `fill`, so it only responds to CSS present at page load (clearing
+  `oj.ThemeUtils`' cache and refreshing the region is not enough). Consequence for auditing: an AA sweep that
+  reads CSS `color` scores SVG text by the wrong property and will report a chart page clean.
+- **Counter-example — not every library family is frozen:** UT declares FullCalendar's `--fc-*` on
+  `.apex-fullcalendar-5`, an *element* scope, so those chains resolve there and do pick up a body-level
+  `--ut-*` override (verified on p1800). Check the declaring selector before assuming a freeze.
 
 ### 1.3 "Atom not found in Core/Iris" ≠ dead
 - **Symptom:** grep of `Core.min.css`/`Iris.min.css` shows no `--a-gv-header-cell-font-size`,
diff --git a/sample-themes/README.md b/sample-themes/README.md
index e8d4b37..19ba9bc 100644
--- a/sample-themes/README.md
+++ b/sample-themes/README.md
@@ -37,7 +37,7 @@ package appears in both as soon as it is imported — nothing to register by han
 | Theme | Direction | Status |
 |---|---|---|
 | [linen](linen/) | quiet product — white chrome, hairlines, flat 8px surfaces, teal for actions only | default in app 102 (2026-09-13) |
-| [solarized-dark](solarized-dark/) | VS Code Solarized Dark: `#002b36` canvas, `#073642` surfaces, cyan/blue accents; text levels base3/base2/base1 for AA | source-reviewed, not fully verified — see solarized-dark/README.md |
+| [solarized-dark](solarized-dark/) | VS Code Solarized Dark: `#002b36` canvas, `#073642` surfaces, cyan/blue accents; text levels base3/base2/base1 for AA | live-measured on 24 pages 2026-09-17, four defects fixed in source; **not release-verified** — fixes unimported, JET chart fix unverified — see solarized-dark/README.md |
 
 Adding a theme: copy `linen/` → `<name>/`, rename the class in `theme.json`/`css`, add `preview/cover.jpg`
 (960 px, page 500 at 1280×700 with the side navigation open), run `sync-static.sh`, import — it shows up in the
diff --git a/sample-themes/solarized-dark/README.md b/sample-themes/solarized-dark/README.md
index b5a9d8b..8189667 100644
--- a/sample-themes/solarized-dark/README.md
+++ b/sample-themes/solarized-dark/README.md
@@ -8,7 +8,7 @@
 | Direction | VS Code Solarized Dark: `#002b36` editor canvas, `#073642` regions and cards, `#00212b` chrome, cyan `#2aa198` for actions and selection, blue for links |
 | Palette | Ethan Schoonover's Solarized (VS Code bundled theme); UI surfaces (input, hover, selected) are VS Code's own |
 | Scope | app-wide, one CSS layer scoped under `html.app-theme-solarized-dark`; no page-level edits (the reference app's own `.dm-*` demo surfaces are restated in `misc.css`) |
-| Status | 2026-09-14: AA contrast pass, tokens consolidated, verified on the pages below |
+| Status | 2026-09-17: live Chrome pass over 24 pages — four package-caused defects found, measured and fixed here. **Not release-verified**: the fixes are source-only, nothing has been imported or re-measured as shipped (see *Status* below) |
 
 ## Preview
 
@@ -21,7 +21,8 @@
 ```text
 theme.json               manifest: name, title, tagline, direction, class, declarative template options (nav Style B)
 css/theme.css            entry, loaded by static-files/css/app.css (@themes block, generated)
-css/tokens.css           --sol-* palette, --app-* deltas (html scope), --ut-* / --a-* remaps (body scope)
+css/tokens.css           --sol-* palette, --app-* deltas + --oj-* (JET) remaps (html scope),
+                         --ut-* / --a-* remaps incl. the --a-palette-* family (body scope)
 css/apex/
   shell.css              header (#002c39) · side nav (#00212b, #005a6f pill, light text) · title bar · footer
   regions.css            Cards-region atoms · wizard (cyan active, green complete) · card list · metric card · headings
@@ -30,7 +31,8 @@ css/apex/
   reports.css            IRR / IG / classic: #00212b header 13px/600 · 40px rows · solid hover · themed pager and footer
   dialogs.css            jQuery UI dialog and menu atoms · wizard dialog pages
   misc.css               shadows off · badges · tabs · alert accent edge · Prism.js code samples ·
-                          faceted search · percent graph · help dialog · map legend · chart tooltips
+                          faceted search · percent graph · help dialog · map legend + attribution ·
+                          chart tooltips · FullCalendar default events
 preview/                 cover.jpg (gallery) + the four captures above
 ```
 
@@ -49,6 +51,12 @@ precedence. Two things a dark package must do that a light one can skip:
   resolve at `:root` (`--a-gv-pagination-button-text-color: var(--a-button-text-color)`), so the derived atom
   has to be set as well. Widget state atoms live in `/i/app_ui/css/Theme-Standard.min.css`
   (`--a-gv-pagination-button-selected-background-color`, fallback `#e0e0e0`).
+- **Restate the whole atom family, not just the atoms you can see.** The same `:root` freeze applies to
+  families a page-by-page review never reaches: `--a-palette-*` (15 atoms, declared as `var(--ut-palette-*)`
+  on `:root` in `Core.min.css`) drives every *selection* state in the app, and Oracle JET's `--oj-*` family is
+  mapped onto `--ut-*` on `:root` by `Iris.min.css`. Both were missed until the 2026-09-17 live pass; see
+  *Status*. Third-party surfaces that take their text by inheritance (MapLibre's attribution plate) need a
+  rule of their own.
 - **Keep the hierarchy inside AA.** See below.
 
 The five `!important`s in `shell.css` mirror Iris' own (`.a-TreeView-row.is-hover{…!important}`,
@@ -84,27 +92,124 @@ scripts/apex-import.sh                  # validate + import
 Live, per browser: navigation-bar **Theme** menu or page 405 *Themes*; `#theme=solarized-dark` in a URL;
 `App.theme.use('solarized-dark')` in the console.
 
-## Status: source-reviewed, NOT fully verified — a live Chrome pass is still required
+## Status: live-measured 2026-09-17, four defects fixed — NOT release-verified
 
-**Not "Verified".** The line below records a real automated contrast pass, but it is resting-state and
-14-page only; several rounds of PR review since (2026-09-14, `chatgpt-codex-connector` on #2 and #5) and a
-follow-up source audit (`.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md`) have found
-and fixed real gaps that pass missed. As of the last addendum below, every literal/derived-token gap findable
-by source review (grep against the offline reference CSS + confirmed page presence) is fixed — only Oracle
-JET's and FullCalendar's own custom-property families remain, and those are unverifiable without Chrome (their
-consuming CSS isn't in the offline reference bundle). Read this section as "the last known-good baseline plus
-a changelog of fixes since", not as a current verification — do not extend "Verified" to the whole package
-until a live pass of the audit below runs against the expanded page list (below) and the two JET/Calendar
-pages get a real look.
+**Not "Verified".** A live Chrome pass finally ran (2026-09-17, details below). It is the first runtime
+evidence this package has, and it changes the picture in both directions: the 2026-09-14 resting-state numbers
+reproduced, *and* the pass found four real package-caused defects that no resting-state sweep could ever see —
+one of them (Interactive Grid row selection at **1.06:1**) severe.
 
-### 2026-09-14 contrast-audit baseline (APEX 26.1.4 / Iris) — as claimed by the session that ran it, unverified since
+Three things keep "Verified" out of reach:
 
-**Not independently re-confirmed.** The paragraph below reports what a prior session's automated audit script
-claimed; no later review (including the multiple PR-review rounds that found real gaps this pass missed — see
-the addenda below) has re-run it or otherwise confirmed its own reliability. Given this package's demonstrated
-pattern of overclaimed verification, treat these specific numbers the same way as everything else in this
-README not labeled "confirmed 2026-09-15 or later": plausible, sourced from a real script run, but not
-something this session can vouch for.
+1. **The fixes in this worktree have never been rendered.** The pass measured app 102 as installed, i.e. the
+   previous commit; the four fixes were validated by injecting the candidate CSS into the live page and
+   re-measuring (A/B, numbers below), which proves the rule works but not that the shipped bundle contains it.
+   Nothing has been imported. A shipped build must be re-measured before any release claim.
+2. **The JET chart fix cannot be validated that way at all** — Oracle JET reads its colours once at bootstrap
+   and bakes them into SVG `fill` attributes, so it only responds to CSS that is present at page load. See
+   *JET (`--oj-*`)* below: the defect is measured and confirmed, the fix is reasoned but **unverified**.
+3. **Coverage is 24 of 122 pages**, one desktop width plus four pages at 375. See *Still required*.
+
+### 2026-09-17 live Chrome pass (APEX 26.1.4 / Iris, app 102) — what was actually measured
+
+Method: own background tab through the project Chrome MCP daemon; theme applied before paint (the browser's
+stored theme was already `solarized-dark`, so no `#theme=` navigation and no `localStorage` write); viewport
+`1440x900x1`, plus `375x812x2,mobile,touch` for four pages. The audit is the documented
+`docs/CHROME_DEVTOOLS_MCP.md` snippet (every visible text node vs its composited effective background, AA
+thresholds), extended with a *light-surface sweep* (any opaque background of relative luminance ≥ 0.6 and
+≥ 300 px² — the "stayed white" failure mode a contrast audit cannot see, since a light-on-light pair can still
+pass AA).
+
+**Pages (24):** 500, 405, 423, 1202, 1208, 1304, 1402, 1405, 1410, 1411, 1412, 1500, 1600, 1601, 1800, 1902,
+1903, 1906, 1910, 3003, 3110, 4000, 6303, 6304 — plus dialog page 1912 inside its iframe (opened from 1910).
+**4 469 visible text nodes measured. Console: 0 errors on every page.** That includes all 14 pages of the
+2026-09-14 baseline, whose resting-state "0 package failures" claim is hereby independently reproduced — and
+shown to be insufficient, because every defect below is a state, a widget-rendered glyph, or a non-text
+surface.
+
+**Resting-state failures: 10 → 3 package-caused → 0 after the fix.**
+
+| Page | What fails | Measured | After the fix | Owner |
+|---|---|---|---|---|
+| 1411 | Faceted Search `Show All` / `Clear All` text buttons | #0e7295 on `#073642` = **2.39:1** | 4.50:1 | package (fixed) |
+| 1906 | MapLibre attribution bar text and its links | base2 on the white plate = **2.57:1** | 12.25:1 | package (fixed) |
+| 1304 | `t-BadgeList` demo values, white on `--u-color-2` `#de7f11` / `#b47282` | 2.94:1 / 3.70:1 | unchanged | Universal Theme (`--u-color-*` literals; the package never touches them — identical under plain Iris) |
+| 1800 | Calendar `apex-cal-green` events, white on `#2ecc71` | 2.10:1 ×5 | unchanged | APEX (`#2ecc71` is a literal in `app_ui-Core.min.css`'s `apex-cal-*` classes) |
+
+**Non-resting-state failures — the ones that matter, and the reason a resting sweep is not a verification:**
+
+| Where | State | Measured | After the fix |
+|---|---|---|---|
+| p1410 Interactive Grid | select a row | cells paint Iris' `#e4f1f7` under base2 text: **1.06:1** — the row becomes unreadable | 8.17:1 (cells take the package's cyan wash) |
+| p1601 date picker | open the picker | current day is a light `#e4f1f7` chip (5.43:1, so *AA-passing and still wrong*) in a dark calendar | 9.28:1 on the dark wash |
+| p1902 JET charts | at rest, but SVG-rendered | axis/group/legend labels `rgba(0,0,0,.65)` = **1.46:1**, series labels `#000` = 1.62:1; **24 of 25 chart text nodes fail** | unverified (see below) |
+
+The chart failures are invisible to the documented audit because it reads CSS `color`; SVG text takes its
+colour from `fill`. Any future "verified" claim for a package that ships charts has to measure `fill`.
+
+**Root causes — all three are the same mechanism (pitfalls.md §1.2), in families the source audit had not
+covered:**
+
+- `--a-palette-*` (15 atoms). `Core.min.css` declares the whole family as `var(--ut-palette-*)` **on `:root`**,
+  so it freezes to Iris' `#00688c` / `#e4f1f7` / `#fff` before this package's body-level `--ut-palette-*`
+  reaches it. Consumers are element-scoped rules, so restating the chain on the body scope fixes them all:
+  IG/IRR/Card View/Icon List/Media List/Timeline/Comments selection, subtle badges, the date picker's current
+  day, the report-controls error state. Fixed in `css/tokens.css`.
+- `--a-base-link-text-color` — same shape (`Core.min.css`, `:root`, `var(--ut-link-text-color)`); the faceted
+  search text buttons read it *on the element*, so they kept Iris' link blue. Fixed in `css/tokens.css`.
+- MapLibre's attribution plate is its own white surface that takes the inherited text colour. Fixed in
+  `css/apex/misc.css`; the zoom control group is deliberately left white (its glyphs are dark SVG images that
+  CSS cannot recolour) — an opaque light patch, not a contrast failure.
+
+**Also checked live, no failures:** side navigation expanded (labels 6.27:1, current item 15.54:1); modal
+dialog page 1912 inside its iframe (theme class present in the iframe, surface `#073642`, title 13.72:1);
+hover on the IR search field (10.35:1 / input text 11.75:1) and on the IR *Actions* toolbar button (10.61:1) —
+the two 2026-09-14 hover fixes hold at runtime; 375 px on pages 500 / 1402 / 1600 / 1410 — 0 failures and 0 px
+horizontal overflow on each.
+
+#### The two open questions from 2026-09-14, answered
+
+- **FullCalendar (`--fc-*`) — reached, no action needed.** UT declares the family on `.apex-fullcalendar-5`,
+  an element scope, so the chain resolves *there* and picks up this package's body-level `--ut-*`: measured on
+  p1800, `--fc-page-bg-color` `#073642`, `--fc-event-bg-color` `#4b9fda`, `--fc-event-text-color` `#002b36`,
+  `--fc-border-color` the package hairline. Day numbers 
+  measured base2 on the dark grid. The only calendar failures left are APEX's own `apex-cal-*` demo colours.
+- **Oracle JET (`--oj-*`) — consumed, *not* reached, fix written but NOT verified.** `Iris.min.css` maps 32
+  `--oj-*` tokens onto `--ut-*` atoms **on `:root`** — same freeze. Live proof: at `:root`
+  `--oj-core-text-color-primary` = `#000` and `--oj-core-text-color-secondary` = `rgba(0,0,0,.65)`, which are
+  exactly the two `fill` values the chart text carries, while the same tokens at body scope hold the package's
+  values. `css/tokens.css` now restates the text/divider/heading/link members on the **html** scope (JET reads
+  them off the document element). It could not be validated in-session: setting the properties live, clearing
+  `oj.ThemeUtils`' cache and refreshing the regions re-rendered the SVG (verified: a marked node was replaced)
+  but the new text still came out `rgb(0,0,0)` — JET resolves its style defaults once at bootstrap. **This one
+  needs an import and a reload to confirm, and it is the single biggest open item.** The rest of the `--oj-*`
+  family (JET text fields, collections, popups, semantic danger/warning/success text) is deliberately left
+  alone: no consuming component of that kind was found in app 102, and guessing values that cannot be seen is
+  what got this package into trouble before.
+
+#### Still required before "Verified"
+
+1. Import this worktree and re-run the sweep above against the shipped CSS — in particular p1902, whose fix is
+   unverifiable any other way, and a re-measure of the four fixed defects as rendered rather than as injected.
+2. Pages: 98 of app 102's 122 are still unopened under this package. Widths: 1024 and 768 were not exercised at
+   all (spec §45 wants ≥ 3), and 375 covered only four pages.
+3. States: only IG row selection, the date picker, two hovers, one dialog and the side nav were driven. IR row
+   selection, Card View / Icon List / Media List / Timeline / Comments selection, the report-controls error
+   state, chips, drag-and-drop and keyboard focus rings are untested — and every defect found this pass lived
+   in a state, not at rest.
+4. An SVG-`fill`-aware contrast audit, and the light-surface sweep, should be folded into the documented audit
+   snippet; the current one would have reported this package clean on the chart page.
+
+### 2026-09-14 contrast-audit baseline (APEX 26.1.4 / Iris) — reproduced 2026-09-17 for resting state only
+
+**Re-run 2026-09-17, and it holds — for what it measures.** The 14-page resting-state result below was
+reproduced independently by the live pass above (all 14 pages re-audited; 0 package-caused resting failures on
+each, the p1304 `u-color-*` exception included). What the 2026-09-17 pass also showed is that this number was
+never evidence of a verified package: the four defects found that day are all outside its sampling window
+(a selection state, an open date picker, a MapLibre surface, SVG `fill` text). The interaction claims in the
+paragraph below ("IG paging, dialog open/close, nav-bar menu, keyboard focus ring checked") remain
+unre-confirmed in that specific form; dialog open/close and the side nav were re-checked on 2026-09-17,
+IG paging and the focus ring were not.
 
 Automated text-contrast audit (every visible text node vs its effective background, AA thresholds) on pages
 500, 1202, 1208, 1304, 1402, 1410, 1500, 1600, 3110, 4000, 6303, 6304, 405 and dialog page 1912: **0 failures
@@ -156,3 +261,9 @@ new sections for Faceted Search (p1411), Percent Graph (p423/p1601), Help Text (
 need Chrome to determine whether Oracle JET's/FullCalendar's own theming reaches this package at all — the
 one remaining open question, unresolved by source review because their consuming CSS isn't in the offline
 reference mirror.
+
+*Closed 2026-09-17:* all eleven pages were opened and audited live, and both library questions were answered —
+see the 2026-09-17 section at the top of this Status block. Two of those pages (1411, 1906) carried real
+failures, and 1410 carried the worst one found so far. The source-review pass this addendum describes was
+therefore necessary but not sufficient: it never reached `--a-palette-*`, `--a-base-link-text-color` or the
+`--oj-*` family, all of which are the same `:root`-freeze mechanism it set out to close.
diff --git a/sample-themes/solarized-dark/css/apex/misc.css b/sample-themes/solarized-dark/css/apex/misc.css
index 0902fcc..e86a092 100644
--- a/sample-themes/solarized-dark/css/apex/misc.css
+++ b/sample-themes/solarized-dark/css/apex/misc.css
@@ -216,3 +216,17 @@
     background-color: var(--app-color-primary);
     filter: brightness(1.08);
 }
+
+/* Map (p1906, p1601 map item). MapLibre's attribution bar paints its own translucent white plate and takes
+   its text colour by inheritance, so the package's base2 body text landed on it: measured 2.57:1 on p1906,
+   2026-09-17. Give the plate the package overlay so the inherited text has a dark ground: 12.25:1 for both
+   the text and its links, measured with this rule injected. The zoom control group keeps MapLibre's white
+   chrome on purpose (it is an opaque light patch, not a contrast failure) — its glyphs are
+   dark SVG images that are not themable from CSS. */
+.app-theme-solarized-dark .maplibregl-ctrl-attrib {
+    background-color: var(--app-overlay-background);
+}
+.app-theme-solarized-dark .maplibregl-ctrl-attrib,
+.app-theme-solarized-dark .maplibregl-ctrl-attrib a {
+    color: var(--app-text-primary);
+}
diff --git a/sample-themes/solarized-dark/css/tokens.css b/sample-themes/solarized-dark/css/tokens.css
index a4ec6b3..1a6a6b6 100644
--- a/sample-themes/solarized-dark/css/tokens.css
+++ b/sample-themes/solarized-dark/css/tokens.css
@@ -78,6 +78,23 @@ html.app-theme-solarized-dark {
     --app-badge-danger-text: #ffffff;
 
     --app-font-weight-semibold: 600;
+
+    /* Oracle JET (charts, p1902). Iris maps JET's own token family onto --ut-* atoms *on :root*, so the chain
+       freezes to the light literals before this package's body-level --ut-* overrides can reach it
+       (pitfalls.md §1.2). JET's DVT layer reads the resolved value once, off the document element, and bakes
+       it into the SVG as a `fill` attribute, so the override has to sit on the html scope (where --app-* is
+       declared) and has to be present at page load: measured 2026-09-17 on p1902, chart axis / group / legend
+       labels were painted rgba(0,0,0,.65) = --oj-core-text-color-secondary's :root value (1.46:1 on the card)
+       and series labels rgb(0,0,0) = --oj-core-text-color-primary's (1.62:1).
+       NOT RUNTIME-VERIFIED: because JET caches those values at bootstrap, this fix cannot be observed without
+       an import + reload — see README.md, "JET (--oj-*)". */
+    --oj-core-text-color-primary: var(--app-text-primary);
+    --oj-core-text-color-secondary: var(--app-text-secondary);
+    --oj-heading-text-color: var(--app-text-emphasized);
+    --oj-core-text-color-brand: var(--app-color-primary);
+    --oj-link-text-color: var(--app-color-primary);
+    --oj-core-divider-color: var(--app-border-color);
+    --oj-core-focus-border-color: var(--sol-cyan);
 }
 
 /* Universal Theme / Iris tokens, overridden on the theme-style scope (body.apex-theme-iris, never :root) so
@@ -127,6 +144,36 @@ html.app-theme-solarized-dark {
     --ut-palette-danger-text: var(--sol-red-text);
     --ut-palette-info-text: var(--sol-cyan);
 
+    /* Core.min.css declares the whole --a-palette-* atom family as var(--ut-palette-*) *on :root*, so it
+       freezes to Iris' light literals (#00688c / #e4f1f7 / #fff) before the overrides above reach it
+       (pitfalls.md §1.2). Every consumer is an element-scoped rule, so restating the chain here is enough.
+       Measured 2026-09-17 on p1410: selecting an Interactive Grid row painted its cells #e4f1f7 under base2
+       text — 1.06:1; with these fifteen lines the same cells take the package's shade and measure 8.17:1.
+       Also feeds IRR/IG/Card View/Media List/Timeline/Comments selection, subtle badges, the date picker's
+       current day and the report-controls error state. */
+    --a-palette-primary: var(--ut-palette-primary);
+    --a-palette-primary-contrast: var(--ut-palette-primary-contrast);
+    --a-palette-primary-shade: var(--ut-palette-primary-shade);
+    --a-palette-danger: var(--ut-palette-danger);
+    --a-palette-danger-contrast: var(--ut-palette-danger-contrast);
+    --a-palette-danger-shade: var(--ut-palette-danger-shade);
+    --a-palette-warning: var(--ut-palette-warning);
+    --a-palette-warning-contrast: var(--ut-palette-warning-contrast);
+    --a-palette-warning-shade: var(--ut-palette-warning-shade);
+    --a-palette-success: var(--ut-palette-success);
+    --a-palette-success-contrast: var(--ut-palette-success-contrast);
+    --a-palette-success-shade: var(--ut-palette-success-shade);
+    --a-palette-info: var(--ut-palette-info);
+    --a-palette-info-contrast: var(--ut-palette-info-contrast);
+    --a-palette-info-shade: var(--ut-palette-info-shade);
+
+    /* Same mechanism: Core.min.css declares --a-base-link-text-color: var(--ut-link-text-color) on :root.
+       The faceted-search text buttons (.a-FS-toggleOverflow / .a-FS-clearAll / .a-FS-clearButton) set
+       --a-button-text-color from it *on the element*, so they kept Iris' #0e7295: measured 2.39:1 on the card
+       (p1411, 2026-09-17); restated it measures 4.50:1. Hover/active fall back to this token in UT's own
+       declarations, so one line covers all three states. */
+    --a-base-link-text-color: var(--ut-link-text-color);
+
     /* Iris declares these with literal colours on :root (they do not follow the component tokens) */
     --ut-region-background-color: var(--app-surface-card);
     --ut-region-header-background-color: var(--app-surface-card);
@@ -189,6 +236,10 @@ html.app-theme-solarized-dark {
     --a-datepicker-calendar-week-text-color: var(--app-text-secondary);
     --a-datepicker-calendar-header-text-color: var(--app-text-secondary);
     --a-datepicker-calendar-day-hover-background-color: var(--app-surface-hover);
+    --a-datepicker-calendar-day-current-text-color: var(--app-text-emphasized);   /* the current day's cell
+                            takes --a-palette-primary-shade as its background and --a-palette-primary as its
+                            text: with the restatement above that pair is #4b9fda on the cyan wash = 3.47:1
+                            (measured p1601, 2026-09-17), so the day's own text token is set explicitly */
     --a-datepicker-footer-background-color: var(--app-surface-card);
     --jui-datepicker-background-color: var(--app-surface-card);
     --jui-datepicker-border-color: var(--app-border-color);

```
