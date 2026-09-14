# Pitfalls and lessons — living record

Every trap this project has fallen into, with the fix that worked. Organised by layer, not by date; each
entry says how it was verified. Add to it whenever something surprises you (spec §50–§58: file a finding
first if the lesson should change a skill). Confidence CONFIRMED unless marked. Verified on APEX 26.1.4 /
Universal Theme 42 / Iris, app 102, 2026-09-13 → 14.

Companion files: [`ut-26.1-iris-runtime.md`](ut-26.1-iris-runtime.md) (runtime facts),
[`iris-ut-tokens.md`](iris-ut-tokens.md) (token values), `ut-dom-*.md` (markup hooks),
[`reference/README.md`](reference/README.md) (offline CSS/JS copies), `../findings/` (protocol records — pending until their evaluation has run).

---

## 1. Universal Theme / Iris CSS

### 1.1 Iris declares ~70 `--ut-*` tokens and ~100 `--a-*` atoms with *literal* colours on `:root`
- **Symptom:** a dark package remaps `--ut-component-*` and `--ut-body-*`, yet regions, radio labels, form
  labels, the side-column, checkboxes, chips, date picker, grid states stay light or dark-on-dark.
- **Cause:** Iris writes e.g. `--ut-region-text-color: #161513`, `--ut-field-label-text-color: #161513`,
  `--a-checkbox-background-color: #fff` as literals; they do **not** derive from the component tokens.
- **Fix:** restate every literal token on `body.apex-theme-iris` inside the package (`tokens.css`). Get the list
  with a regex over `reference/ut-26.1/Iris.min.css` `:root` blocks — value without `var(` and a `color|background|
  shadow` name. Families: region, body-nav/-title/-sidebar/-actions, field, footer, header, navtabs, linkslist,
  login, navbar-badge, resultsregion, report-cell-alt, treeview-badge, component-badge/-toolbar; atoms: button,
  chat, checkbox, chip, cr, cv, datepicker, field, gv, kb, menu, popuplov, report-controls, resultsitem,
  starrating, treeview.
- **Evidence:** `.t-Region{color:var(--ut-region-text-color,var(--ut-component-text-default-color))}` in Core
  resolved to `#161513` on p1500 until `--ut-region-text-color` was set. Finding: `accepted/2026-09-14-ut-literal-root-tokens.md`.

### 1.2 `var()` chains in Iris `:root` resolve at `:root`, not where consumed
- **Symptom:** `--a-button-text-color` overridden on body, but IG pager buttons still `#161513`.
- **Cause:** Iris `:root { --a-gv-pagination-button-text-color: var(--a-button-text-color) }` is computed on
  `:root` with `:root`'s value; a body-level override of `--a-button-text-color` never reaches it.
- **Fix:** override the *derived* atom too (`--a-gv-pagination-button-text-color`). Same for
  `--a-gv-header-text-color: var(--ut-component-text-muted-color)` etc.

### 1.3 "Atom not found in Core/Iris" ≠ dead
- **Symptom:** grep of `Core.min.css`/`Iris.min.css` shows no `--a-gv-header-cell-font-size`,
  `--a-gv-footer-background-color`, `--jui-overlay-background-color` → tempted to delete them as dead.
- **Cause:** the APEX **widget CSS** (`/i/app_ui/css/Core.min.css`, `Theme-Standard.min.css`) *consumes* atoms
  with light fallbacks: `.a-GV-footer{background-color:var(--a-gv-footer-background-color,#fff)}`. Nothing
  declares them, so a body-level declaration is the only way to theme that surface.
- **Fix:** grep all four files in `reference/ut-26.1/` (added 2026-09-14; `fetch-vendor.sh` fetches them).
  Known white fallbacks: `--a-gv-footer-background-color #fff`,
  `--a-gv-pagination-button-selected-background-color #e0e0e0` (set on
  `.a-GV-pageSelector-item.is-selected .a-GV-pageButton` by Theme-Standard), `.u-Report td #fff`,
  `.u-Report--staticBG tr:nth-child(2n) td #fff`, `.u-Report th[scope=rowgroup] #fafafa`, `--a-gv-border-color #e8e8e8`.

### 1.4 `.u-Report` utility tables are hard-coded light in the widget CSS
- Used by the reference pages' documentation tables (6303, 6304, 6307 …). Core UT's token rule
  `.u-Report td{background:var(--ut-report-cell-background-color,…)}` loses to the widget CSS
  `.u-Report--staticBG tr:nth-child(2n) td{#fff}` (higher specificity) — theme them explicitly
  (`solarized-dark/css/apex/reports.css`).

### 1.5 Component atoms declared *on the element* beat body-level overrides
- `.a-IRR{--a-gv-border-radius}`, `.t-WizardSteps-step.is-active .t-WizardSteps-marker{--ut-wp-marker-size}`,
  Theme-Standard's pager selection. Override on that element (or the atom it derives from), not on body.
  Checking: `getComputedStyle(el).getPropertyValue('--x')` on the element vs its parent shows where it changes.

### 1.6 Iris `!important` on the tree nav
- `.a-TreeView-row.is-hover{background-color:…!important}`, `.is-current--top.is-hover{color:#fff!important;
  background-color:#006c91!important}`. Mirroring them is the only way; quote the Iris rule in a comment
  (spec §23). Everything else in a package should have zero `!important`.

### 1.7 Solarized (and most terminal palettes) fail AA on a card surface
- On `#073642`: base1 4.9, base0 4.1, base01 2.4, blue 3.5, cyan 4.1, green 4.1, red 2.8, magenta 2.9 (: 1).
  Only base1/2/3 pass for 13–14 px text. Fix used: text levels base3/base2/base1; accents used *as text*
  tinted towards white until ≥ 4.5 (`mix(color, white, t)` stepping `t` by 0.01 — blue 17 %, red 33 %,
  magenta 31 %, orange 30 %); fills keep raw accents with **dark** text (`#002b36`: cyan 4.75, green 4.7,
  yellow 4.7; white on red 4.6 is the exception). Compute, don't eyeball: the WCAG formula is 20 lines of
  Python (see `docs/CHROME_DEVTOOLS_MCP.md`, contrast audit) — a hand-written "6.7:1" in a comment was 4.75.
- Borders that *identify* a control (inputs, default buttons on a same-coloured region) need ≥ 3:1
  (WCAG 1.4.11): `rgba(131,148,150,.8)` on the card = 3.3. Decorative hairlines can stay faint.
- Floating labels are 11 px on the highlight surface (`--ut-component-highlight-background-color`): base1 there
  is 4.2 → use the body colour.

### 1.8 Reference-app demo pages style their own markup with literal light values
- p4000 `input#P4000_SEARCH`, `.dm-Search-*`, `.dm-IconDialog-*`; p6303/p6304 `.dm-Report--doc`, `.class`,
  `.class.tag`, `.class-value/-var/-desc`; p6100/6200/6201 `.event-name`, `.icon-preview`, `.instructions`.
  Oracle's Vita Dark carried per-page overrides for these; a dark package restates them (misc.css "demo
  surfaces" section) at higher specificity than the page inline CSS (which loads *after* app.css, so equal
  specificity loses). Found by the Codex PR review, not by the page list — audit the *doc* pages too.

### 1.9 Where a colour comes from when no rule seems to set it
- Rules that only set **custom properties** are invisible to a matcher that filters on `style.color` /
  `style.backgroundColor` — check `r.style.getPropertyValue('--the-atom')` too.
- `@import`ed sheets (app.css → foundation, pages, themes) are nested: walk `rule.styleSheet.cssRules`.
- `.t-Region{color:var(--ut-region-text-color,…)}`-style fallbacks: read the custom property on the element
  to see which side of the fallback is live.

## 2. APEX JavaScript and widgets

### 2.1 Navigation-bar menus are built by theme42 on `apexreadyend`; `theme42ready` fires on **window**
- `apex.theme42` runs its init map (`misc()` → `.t-NavigationBar-menu`.menu()) on `apexreadyend`, then
  `$(window).trigger('theme42ready')`. Hook `apex.jQuery(window).on('theme42ready', …)` to post-process menus;
  `document` does not receive it.

### 2.2 The `menu` widget accepts a `radioGroup` item
- `items: [{type:'radioGroup', get(){…}, set(v){…}, choices:[{label,value}]}]` renders `role=menuitemradio` +
  `aria-checked` + a check mark — the right primitive for a "choose one" nav-bar menu. Rebuild with
  `menu('option','items', […])`. `data-current="true"` on the source `<li>` becomes `current: true`.
- Synthetic `element.click()` on a rendered `menuitemradio` **does not** trigger the widget (it listens to
  mouse events); test with a real click (`chrome-devtools click uid`).

### 2.3 Pages without a navigation bar: `$()` chains don't throw
- `$('#missing').menu('option','items')` on an empty jQuery set returns the set, not an error. `try/catch` is
  not a guard — check `.length` and `Array.isArray(items)`. This produced `items.forEach is not a function`
  inside every dialog page (which has no nav bar) and broke the rest of theme42's init.

### 2.4 Cards regions render after DOM-ready and don't fire `apexafterrefresh` on `refresh()`
- The Cards region (`tableModelView` widget) loads data asynchronously; `apex.jQuery(fn)` runs before any card
  exists, and `apex.region(id).refresh()` did **not** emit `apexafterrefresh` (26.1.4). What fires, after each
  render and bubbling to `document`, is `tablemodelviewpagechange` (jQuery UI lower-cases
  `widgetEventPrefix + event`). Delegate: `$(document).on('tablemodelviewpagechange', '#static_id', fn)`.

### 2.5 Card > CSS Classes supports `&COLUMN.` substitution and lands on `.a-CardView`
- `card { cssClasses: [ app-theme-card &CARD_CLASS. ] }` → `<div class="a-CardView … app-theme-card app-theme-card--linen">`.

## 3. APEXLang / Builder

### 3.1 Static ID is `advanced { htmlDomId: … }`
- `staticId` in the same group is the compiler's internal component identifier; it validates and does
  nothing at runtime. Export examples: `p00300-grid-layout.apx:911`.

### 3.2 App-level CSS/JS are top-level blocks
- `application.apx` → `css { fileUrls }`, `javaScript { fileUrls }` (not `userInterface { }`).

### 3.3 Theme styles of a subscribed theme are read-only and not in APEXLang
- With `baseTheme: ut-26.1` the grammar has no style children (only `style { currentThemeStyle }`); the
  Builder shows every theme-style field read-only with no Delete because the theme is subscribed to the
  standard Universal Theme. Deleting Vita/Redwood rows means **unsubscribing** (lose Refresh Theme, export
  balloons). Decision 2026-09-14: leave the rows inert; remove every *reference* instead (nav-bar list,
  page 405, app process, P0 item, preview PNGs, dead `.apex-theme-vita-dark` CSS).

### 3.4 Removing the last app process
- Deleting the only `appProcess` leaves an empty `shared-components/app-processes.apx`; delete the file
  (the export omits it when there are none) — an empty `.apx` is not a valid component file.

### 3.5 Static files that only exist in the export
- `theme_styles/*.png`, `pwa/*`, `demo/*` have no source under `static-files/`; `sync-static.sh` only prunes
  `css/` and `js/`. Remove such files **and** their `file "…" ( )` entry in `static-files.apx` by hand.

### 3.6 Static files as data
- `apex_application_static_files.file_content` is a BLOB; `json_value(file_content FORMAT JSON, '$.title')`
  works (23ai), so a list or Cards SQL can discover packages from `css/themes/<name>/theme.json`. `#APP_FILES#`
  substitutes inside Cards media URLs and list targets. Query the view with
  `apex_session_state.get_number('APP_ID')` (lists) or `:APP_ID` (regions).

### 3.7 `apex import` is a full replace
- Whatever is on disk gets shipped — including another agent's untracked files — and files absent from the
  export are removed from the app. Never import from a worktree that lacks the working tree's untracked
  packages; export → diff → import.

## 4. Tooling (Chrome DevTools MCP, SQLcl)

### 4.1 Shared browser state
- Every APEX tab shares `localStorage['app.theme']`: navigating *your* tab to `…#theme=x` rewrites the theme
  for the user's other tabs on their next reload. For captures swap the class in the DOM
  (`document.documentElement.className = … 'app-theme-x'`) instead.
- `resize_page` resizes the **shared Chrome window**; use `emulate {viewport:'1440x900x1'}` (per tab).
- Work in your own tab (`new_page … background:true`), hide `#apexDevToolbar` with a `<style>` for captures,
  close the tab when done.

### 4.2 Same-document hash navigation does not reload
- `navigate_page` to the current URL + `#theme=…` is a hash change; the page-0 bootstrap does not run.
  `App.theme.use()` therefore reloads explicitly (and strips a stale `#theme=` first, because page 0 would
  re-apply it).

### 4.3 The contrast audit finds what screenshots miss
- The 40-line `evaluate_script` in `docs/CHROME_DEVTOOLS_MCP.md` (every visible text node vs its blended
  background, AA thresholds) caught dark-on-dark radio labels, a white IG footer, unreadable Prism tokens and
  white doc tables that looked "fine" at thumbnail size. Run it on the standard page list
  (500, 1201, 1202, 1208, 1304, 1402, 1410, 1500, 1600, 1910/1912, 3110, 4000, 6303, 6304, 405) before
  calling a package verified. Exclusions: `#apexDevToolbar`, hidden nodes; expect Universal Theme's own
  `u-color-*` demo fills (p1304) to fail under any style.

### 4.4 SQLcl / DB
- `apex_application_theme_styles` lists the six Iris/Vita/Redwood rows; `apex_application_static_files`
  shows what is really deployed (sizes tell you whether the working tree was imported).
- `sql -S -name docker-demo` validate + import ≈ 65 s; validate alone ≈ 25 s.

## 5. Workflow

### 5.1 Another agent may be editing the same tree
- 2026-09-14: a Codex session authored `sample-themes/solarized-dark/` while this session worked; files changed
  mid-read and the live app already held its import. Check `find sample-themes -type f -mmin -30` and
  `ps aux | grep codex` before touching a package; say what you are doing; commit only what you own — or,
  when the user asks you to take the package over, say that too.
- The repo has a **Codex PR review bot** (`chatgpt-codex-connector`); it comments with P-level findings on
  every PR. Verify each at runtime before acting (2026-09-14: one P2, real, fixed).

### 5.2 Review before claiming
- The first Solarized Dark draft claimed 6.7:1 for a 4.75:1 pair, had 6 uncommented `!important`s, 30+ repeated
  literals and iteration PNGs in `preview/`. The package conventions in `sample-themes/README.md` exist so the
  next package starts from the checklist, not from a linen copy.

### 5.3 Don't promote a finding before its evaluation has run
- Spec §58 orders: record → classify → evidence → scope → *evaluation scenario* → confirm the old instructions fail
  it → smallest skill change → **run** the evaluations → verify → promote. Applying the skill change (step 7) is
  fine early; moving the file to `accepted/` before step 8 is not — the Codex review on PR #3 caught exactly that.
  Keep `Status: Pending — change applied; evaluation run pending` until the row in `evaluations/README.md` says
  *passed*.

### 5.4 Skills lag the architecture unless the protocol runs
- Skills still described `static-files/css/apex/` two commits after packages moved to `sample-themes/`. When
  the architecture moves, file the finding and fix the routing table in the same change (spec §58); the
  evaluation (`10-theme-package-routing.md`) is what keeps it honest.
