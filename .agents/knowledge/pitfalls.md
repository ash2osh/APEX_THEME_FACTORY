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

### 2.6 Alpine.js being registered as a static file doesn't mean it's loaded
- **Symptom (found 2026-09-15):** `static-files/js/app.js`'s own header comment claims "Alpine.js is loaded
  once (application-level file URL)", and `static-files/js/vendor/README.md` documents the load order — but
  `applications/ut/application.apx`'s `javaScript.fileUrls` never actually referenced `js/vendor/alpine.min.js`,
  only `demo.js`, Prism, and `js/app.js`. `static-files.apx` had it registered as an uploadable static file,
  which is a different thing from a page emitting a `<script>` tag for it. No `x-data`/`Alpine.data()` anywhere
  in the app could ever have run.
- **Fix:** add `#APP_FILES#js/vendor/alpine.min.js` to `application.apx`'s `javaScript.fileUrls`, after
  `js/app.js` and after any `js/components/*.js` entries (components hook `alpine:init`, which must be
  registered *before* Alpine's own CDN-build auto-start — see the vendor README's load-order note).
- **Check this again** whenever adding the first component file to a fresh checkout, or after any bulk
  `applications/ut/application.apx` regeneration — nothing currently guards against this silently regressing.

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

### 3.8 APEXLang comment lines never come back from `apex export`
- **Symptom (found 2026-09-16 review):** the installer marked its Page 0 regions and list entries with
  `// APEX_THEME_FACTORY_MANAGED:BEGIN/END` comment lines and treated a managed region *without* the
  markers as a foreign collision. APEX has no place to store APEXLang comments, so the first real
  re-export was comment-free and every reinstall/upgrade/uninstall was refused.
- **Fix:** ownership lives in data APEX keeps — region Static ID (`advanced { htmlDomId }`), an HTML
  comment inside `htmlCode`, list-entry static ids (`entry <staticId> (` — the identifier *is* the
  static id and round-trips), `userDefinedAttributes`, and file digests in `registry.json`
  (`lib/theme_factory/apexlang.py`: `strip_bootstrap_regions`, `strip_switcher_entries`).
- Corollary: never compare a staged export with a re-export byte-for-byte. SQLcl re-indents fenced
  code to the fence column, sorts `file` blocks in `static-files.apx`, and names page files after the
  page name. Compare a semantic projection (`theme_factory_projection`). The offline fake `sql`
  (`tests/fixtures/bin/sql` + `apexlang_roundtrip.py`) reproduces these transforms on purpose.

### 3.9 Lists are exported into one `shared-components/lists.apx`
- SQLcl 26.2 writes every list into `lists.apx` (`list navigation-bar ( … )`); there is no
  `navigation/lists/navigation-bar.apx`. Resolve the navigation bar through
  `navigationBar { list: @alias }` in `application.apx`, and check the list is static — app 102's
  navigation bar is a SQL-query list and cannot host static switcher entries.
- Valid entry grammar: `layout { sequence, parentEntry: @id }`, `link { target: { type: url url: # } }`,
  `icon { imageIconCssClasses }`, `userDefinedAttributes { 2: <li classes> }`. `cssClasses` is not an
  entry property (`node ~/.claude/skills/apex/apexlang/tools/query-valid-props.mjs --component-type-id 3525`).
- `application.apx` may have no `javaScript {}` block at all (app 104); create it next to `css {}`.

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
- It only samples nodes present (and visible) at rest, on page load. It missed two Solarized Dark failures that
  only exist on `:hover` (IR/IG toolbar control labels — Iris sets the hover-background atom directly on the
  type-specific `.a-IG-controls-item--*` element, pale, outranking the body-level mapping) and `:empty:before`
  (page 4000's "No Results" state, only rendered once a search returns nothing) — caught instead by PR review
  (2026-09-14, `chatgpt-codex-connector`). Before calling a package verified, also drive the interactive states
  the static audit can't see: hover every toolbar/report control, and empty a search box.

### 4.3b The contrast audit's `bgOf()` used to double-composite `<body>`'s own background
- **Symptom (fixed 2026-09-14, PR review on #3):** a lone 50%-alpha `<body>` background composited to
  `rgb(64,64,64)` instead of the correct `rgb(128,128,128)` — roughly 10.4:1 instead of the real ~4:1, a false
  clean result that could hide a real near-failure.
- **Cause:** the ancestor walk already includes `document.body` (loop condition only excludes
  `document.documentElement`), but the old code then re-read and re-composited `document.body`'s background a
  second time as the "page background" backdrop — while never reading `document.documentElement`'s own
  background at all.
- **Fix:** after the loop, composite `acc` once over `document.documentElement`'s background (if any, else
  white) — not over `document.body`'s again. Sanity-check both cases before trusting a re-derived copy of this
  script: 50% red / 50% blue / white → `rgb(191,64,128)`; lone 50% black on `<body>` over an unstyled canvas →
  `rgb(128,128,128)`.

### 4.3c A second `chrome-devtools-mcp --autoConnect` may never answer
- When another instance already holds the Chrome connection (or Chrome is showing the consent prompt),
  `tools/call` requests simply never return. The daemon now times out per request
  (`THEME_FACTORY_CHROME_MCP_TIMEOUT`, default 60 s) and keeps serving; before 2026-09-16 the first
  such call held the lock forever and every client hung. Use the daemon that owns the approved session
  (`THEME_FACTORY_CHROME_MCP_SOCKET=…`) instead of starting a second one.

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

### 5.x Evidence is bound to the last *source* commit
- Committing `.agents/evaluations/runtime/**` or Markdown moves HEAD but not the source under test;
  package banners and `release.py` bind to `lib/theme_factory/gitstate.py: last_source_commit()`
  (everything except the evidence root and `**/*.md`). Any other change — even to a tool or test —
  invalidates captured Layer C/D/E evidence and the packages' SHA-256, so finish source work, commit,
  build, capture, then commit evidence and docs.

## 6. Evaluation protocol (spec §58/§62) — traps from the 2026-09-14 run

The first full run of the evaluation matrix (19 evaluee runs) needed **seven separate PR-review correction
rounds** before its conclusions held up (see `evaluations/README.md`'s correction log for the blow-by-blow).
Every round was a different flavour of the same underlying problem: something about how the scenario was run
made a PASS verdict claim more than the run actually demonstrated. None of it was about the skills under test —
all of it was about the evaluation harness itself. Six reusable traps:

### 6.1 A baseline commit must predate the *code/instruction under test*, not just the finding
- **Symptom:** compared scenario 13 (Cards render event) against baseline commit `9276369` because it predates
  the *finding*. But the actual correct handler (`tablemodelviewpagechange`) had already landed in application
  code at `eda510d`, a later commit still before the finding — so `9276369` was missing the handler entirely,
  not just missing the skill-text fix. The "baseline FAIL" this produced showed "no handler exists yet",
  not "the old skill text produces the wrong handler".
- **Fix:** find the exact commit that introduced the application-code side of what's being tested
  (`git log -S"the specific string" -- path`) and isolate the baseline *there*, not at an earlier commit that
  merely predates the knowledge file. Verify with `git show <commit>:<file> | grep <the-fix>` on both sides
  before trusting the pairing.

### 6.2 Never build an evaluee prompt by quoting a finding's `Given` verbatim if it states the conclusion
- **Symptom:** scenario 14's `Given` (built from the finding's own observational text, per spec's own
  instruction to reuse it) included *"overriding the base atoms on body.apex-theme-iris restyles every instance
  while all modifiers keep precedence"* — literally the scoping answer the scenario exists to test whether the
  evaluee reaches unaided. Both baseline and current runs were hand-fed the conclusion before being asked to
  apply it; neither PASS proved anything about unaided skill behaviour.
- **Fix:** a finding's `Given` records *what was learned*; a scenario's `Given` may only state *the environment*
  (where things live, what the constraints are) — never the technique that follows from it. When adapting a
  finding into a scenario, actively rewrite the sentence that names the fix; don't just copy the finding text
  in because the process doc said to reuse it.

### 6.3 An evaluee-prompt template's permissions must not contradict its own restrictions
- **Symptom:** the shared prompt template said both "do not connect to the database" and "you may... run
  `scripts/apex-validate.sh`" — but that script opens a SQLcl connection. Most evaluees ran it anyway and were
  graded PASS with the contradiction unflagged; one evaluee independently read the script's source, caught the
  conflict, and refused — an inconsistency in *compliance*, not in the CSS/APEXLang work being graded, that
  went unnoticed across most of a 19-run matrix.
- **Fix:** before reusing a prompt template across many runs, grep every script/tool it permits against every
  constraint it states, for exactly this kind of contradiction. If a genuinely offline substitute doesn't
  exist, don't forbid the resource the permitted tool needs.

### 6.4 A scenario's `Expected`/`Failure` may only describe what its task can actually trigger
- **Symptom:** scenario 12's `Failure` line named an app-level CSS/JS routing mistake the task (add a region
  Static ID) never comes near; scenario 13's `Expected`/`Failure` named two navigation-menu corrections a
  Cards-region-only task never touches. Passing verdicts on these scenarios were read as validating the whole
  underlying finding, when large parts of each finding were structurally untestable by the task as written.
- **Fix:** for every clause in `Expected`/`Failure`, ask "what would the evaluee have to *do* for this to be
  reachable?" — if the task never asks for that, either broaden the task or split the untestable part into its
  own scenario. Don't let an evaluation's Given/Expected outgrow what its Task line actually exercises.

### 6.5 When a verdict is downgraded, sweep every place that verdict is repeated, not just the Status line
- **Symptom:** three separate times, a run log's `## Verdict:` heading and its "Evidence" prose kept saying
  PASS (and, in one case, "clean differentiating evidence") for several review rounds *after* a correction
  elsewhere in the very same file had already downgraded the conclusion — because only the finding's Status
  line got updated in the moment, not the run log's own heading and prose that a reader (or a grep for
  "Verdict: PASS") would see first.
- **Fix:** a verdict correction isn't done until `grep -rn "PASS\|Verdict:"` across every file that mentions the
  scenario comes back consistent — the run log's own heading, its evidence paragraph, the scenario's row in
  `evaluations/README.md`, and the finding's Status line all have to agree, not just the last one you touched.

### 6.6 Resetting an evaluee worktree between runs destroys the evidence, not just the state
- **Symptom:** run logs recorded the prompt, the evaluee's *self-reported* summary, and `git diff --stat` — but
  `git checkout -- . && git clean -fd` between runs (necessary to stop one scenario's edits contaminating the
  next) meant the actual full diff and any seeded fixtures were gone by the time a reviewer asked to verify a
  specific claimed selector or contract.
- **Fix:** before resetting, capture the full `git diff` (not just `--stat`) and any files you seeded into the
  worktree yourself — either paste the diff into the run log or save it as a sibling `.patch` file. A run log
  that can't be independently re-diffed isn't the "session/transcript" evidence spec §58 asks for, it's a
  summary of one.
