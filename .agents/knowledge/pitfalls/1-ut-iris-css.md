# Pitfalls §1 — Universal Theme / Iris CSS

Part of the [pitfalls index](../pitfalls.md); entry numbers are stable and cited as `pitfalls §1.N`.

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
  resolved to `#161513` on p1500 until `--ut-region-text-color` was set. Finding: `pending/2026-09-14-ut-literal-root-tokens.md`.

### 1.1b Iris 26.1.4 does not render Oracle Sans
- `oraclesans-apex.min.css` is linked on every page, but `--a-base-font-family` is the system UI
  stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", …`); `document.fonts` lists the Oracle Sans
  faces as `unloaded` and `document.fonts.check('16px "Oracle Sans"')` is false (app 102 p500/p1410,
  consumers 9010/9011, 2026-09-16). Do not assert or "restore" Oracle Sans in a theme; a font-less
  package must leave the body family identical to bare Iris, which the browser matrix checks.

### 1.2 `var()` chains in Iris `:root` resolve at `:root`, not where consumed
- **Symptom:** `--a-button-text-color` overridden on body, but IG pager buttons still `#161513`.
- **Cause:** Iris `:root { --a-gv-pagination-button-text-color: var(--a-button-text-color) }` is computed on
  `:root` with `:root`'s value; a body-level override of `--a-button-text-color` never reaches it.
- **Fix:** override the *derived* atom too (`--a-gv-pagination-button-text-color`). Same for
  `--a-gv-header-text-color: var(--ut-component-text-muted-color)` etc.
- **Three whole families work this way and are easy to miss** (measured live on app 102, 2026-09-17):
  `Core.min.css :root` declares all 15 `--a-palette-*` atoms as `var(--ut-palette-*)` and
  `--a-base-link-text-color` as `var(--ut-link-text-color)`; `Iris.min.css :root` declares 32 `--oj-*`
  (Oracle JET) tokens as `var(--ut-*)`. Symptoms under a dark package: selecting an IG/IRR/Card View/Media
  List/Timeline/Comments row paints Iris' `#e4f1f7` under light text (**1.06:1** measured on p1410), faceted
  search's text buttons keep Iris' link blue (2.39:1, p1411), and JET chart axis/legend text is painted `#000`
  / `rgba(0,0,0,.65)` (1.46–1.62:1, p1902). Restate `--a-palette-*` and `--a-base-link-text-color` on the body
  scope; `--oj-*` has to go on the **html** scope — JET reads it off the document element, once, at bootstrap,
  and bakes the result into SVG `fill`, so it only responds to CSS present at page load — **confirmed by
  measurement 2026-09-17**, after an import made those bytes reachable: p1902 went from 24 of 25 chart text
  nodes at 1.46–1.62:1 to **25 of 25 passing**, worst 4.86:1, fills exactly the package's base1/base2. Until
  the import there was no way to observe it at all, so "reasoned but unverified" was the honest label (clearing
  `oj.ThemeUtils`' cache and refreshing the region is not enough). Consequence for auditing: an AA sweep that
  reads CSS `color` scores SVG text by the wrong property and will report a chart page clean.
- **Counter-example — not every library family is frozen:** UT declares FullCalendar's `--fc-*` on
  `.apex-fullcalendar-5`, an *element* scope, so those chains resolve there and do pick up a body-level
  `--ut-*` override (verified on p1800). Check the declaring selector before assuming a freeze.

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

### 1.10 A scripted `:root` literal-extraction pass can silently drop tokens
- **Symptom (found 2026-09-14):** a regex-based extraction of every `--name:value;` pair from `Iris.min.css`
  (join all `:root{}` blocks, split declarations tracking paren depth) came back with 802 tokens — but
  `--ut-palette-primary` wasn't among them, despite `grep` confirming `--ut-palette-primary:#00688c;` is
  right there in the file. Every atom that *chains* to it (`--ut-component-icon-background-color`,
  `--a-chat-user-primary-icon-background-color`, `--a-percent-chart-bar-background-color`, …) was invisible to
  the same pass as a result, and shipped with Iris' pale default instead of the package's accent — three
  separate contrast bugs from one silent parser gap, all caught by PR review, not by the script.
- **Fix:** don't trust one extraction method for a systematic audit. Cross-check with a second, independent
  method — here, `grep -o '\-\-[a-zA-Z0-9-]*:var(--the-suspect-token)'` across all four reference files finds
  every direct consumer regardless of how the `:root` block itself parses. When a script produces a "done"
  list, spot-check a few tokens you'd expect to be common (palette roots, `--ut-component-*`) are actually in
  it before trusting the list's absence of something as proof it isn't there.

### 1.11 Fixing a themed *text* atom without its paired *background* atom is a half-fix
- **Symptom (found 2026-09-15):** three separate atoms were set to a dark, accent-appropriate text colour
  (`--app-text-on-accent`) on the assumption they'd sit on an already-themed fill — `--ut-component-icon-color`,
  `--a-percent-chart-bar-text-color`, `--a-chat-user-primary-icon-text-color` — but none of their paired
  `-background-color` atoms had actually been overridden, so each stayed at Iris' literal teal `#00688c`
  (dark-on-dark-teal, ~2.4:1). Same root cause as 1.10 (the background atoms all chain to
  `--ut-palette-primary`, missed by the same parser gap) but a distinct lesson: text and background are a
  *pair*, and fixing one half from a token-name list without visually or textually confirming the other half
  is already covered reintroduces the same class of bug the fix was meant to close.
- **Fix:** when overriding any `*-text-color`/`*-icon-color` atom to something other than the package's default
  body text colour (i.e. you're clearly targeting a *filled* surface, not plain text-on-card), grep for the
  sibling `*-background-color` atom in the same family and confirm it's set too, in the same change.

### 1.12 A layout rule must match the layout UT actually uses on that element
- **Symptom (2026-09-24):** the first generated `responsive.css` passed every check and changed nothing on screen.
  It set `grid-template-columns` on `.t-Cards` (a flex row; only the `.t-Cards--{cols,2cols…5cols}` modifiers are
  grids), `flex-wrap` on `.t-Header-controls` (a grid item, not a flex container) and on `.t-Body-actions` (not
  flex), and targeted `.t-Region--cards` (no such class in UT 26.1).
- **Fix:** before writing a layout property, grep the element's own rule in
  `.agents/knowledge/reference/ut-26.1/Core.min.css` (and `app_ui-Core.min.css` for widgets such as
  `.a-CardView-items`) and confirm its `display`; then verify the computed value live at the target width. Working
  targets: `.t-Region-header` (non-wrapping flex row), `.t-ButtonRegion-wrap` (one-row grid left/content/right),
  `.a-CardView-items--grid{2…5}col` (grid).
