# Online work plan: tasks that need the database and Chrome

Written 2026-09-24, after the audit branch was merged (PR #8). Everything offline is done: the offline gate
(`tests/run-offline.sh`) passes and CI is green. What is left needs the local APEX instance
(`docker-demo`, workspace `DEMO`), app 102, the disposable consumer app 9010 and the approved Chrome session.

Work through the stages in order. Stage 0 confirms that what was merged offline also holds on screen, before
anything new is built on top of it. Tick the boxes as you go and commit this file with your changes.

Read before you start: `AGENTS.md`, `.agents/knowledge/pitfalls.md` (§4.1 shared localStorage, §4.2 hash
changes do not reload, §4.3/§4.3d contrast audits, §4.5 slow rAF in agent tabs, §5.7 clean consumer app,
§3.7 import is a full replace), and `docs/CHROME_DEVTOOLS_MCP.md` (etiquette: your own background tab only).

---

## Setup (once, on your machine)

```bash
git checkout main && git pull origin main
python3 -m venv .venv && . .venv/bin/activate
pip install -r tools/test-requirements.txt
tests/run-offline.sh                          # must end with OFFLINE status=PASS
scripts/fetch-vendor.sh --reference           # local-only Oracle UT/Iris CSS+JS for grepping (gitignored)
python3 tools/chrome_mcp_daemon.py &          # the ONE daemon; every call goes through tools/chrome_devtools_client.py
sql -name docker-demo <<< "select 1 from dual;"   # SQLcl connection works
```

- [x] Offline gate passes locally
- [x] Daemon attached to the approved Chrome (a single consent prompt, answered once)
- [x] `scripts/reset-consumer.sh` has created or reset app 9010

---

## Stage 0: confirm the merged offline work on screen (about 1.5 h)

Import app 102 from the merged sources:

```bash
scripts/sync-static.sh --check && scripts/apex-validate.sh && scripts/apex-import.sh   # asks first; full replace
```

| # | What to check | How | Expected |
|---|---|---|---|
| 0.1 | Adapter refactor changed no CSS | Open pages 500, 406, 1402 with each of carbon-volt, velvet-signal, solarized-dark, citrus-pop, cobalt-press, estate-slate | Identical to the covers in `sample-themes/*/preview/`; console clean |
| 0.2 | Switcher allow-list | In your own tab: `…/getting-started#theme=typo`, then reload | Linen is applied; `localStorage['app.theme']` is gone |
| 0.3 | A removed theme doesn't stick | `localStorage['app.theme']='gone'`, reload | Linen is applied; the key is removed |
| 0.4 | `none` still means bare Iris | Theme menu → *Iris (no theme package)* | `html.app-theme-none`, Iris look |
| 0.5 | Reduced motion | DevTools → Rendering → *prefers-reduced-motion: reduce*; hover a card (citrus-pop) and a button (velvet-signal) | No lift, no transition |
| 0.6 | citrus-pop hover timing | Hover a card with motion allowed | Now 240 ms (the recipe's *buoyant*), was 180 ms. Accept it, or set `--app-motion-duration` in `sample-themes/citrus-pop/css/tokens.css` |
| 0.7 | Package runtime guard | Install into 9010 with the switcher, open a dialog page | No console error from `theme-factory-runtime.js` |
| 0.8 | Release smoke, all 8 themes | `for t in carbon-volt citrus-pop cobalt-press estate-slate estate-slate-dark linen solarized-dark velvet-signal; do scripts/theme.sh release "$t" \|\| break; done` (about 5 min each; each run re-imports the clean 9010) | `RELEASE theme=<name> status=PASS` for all 8 |
| 0.9 | Installer drift guard on a real database | `./install.sh … --apply`; while the prompt waits, edit anything in 9010 in the Builder; then type the ID | Exit 4, "drift … while waiting for confirmation", nothing imported |

- [x] 0.1 … 0.9 all as expected. Write anything unexpected into `.agents/knowledge/pitfalls.md` before moving on.

---

## Stage 1: one theme-switcher runtime (audit item 7, about 1 day)

**Problem.** Two runtimes that do the same job:

| | App 102 (`p00000` bootstrap + `static-files/js/app.js`) | Installed packages (`installer/theme-factory-runtime.js` + bootstrap template) |
|---|---|---|
| Storage key | `app.theme` | `apex.themeFactory.<appId>` |
| Bare Iris | `none` | `iris` |
| Links | `#theme=<name>` / `#theme=default` | none |
| Allow-list | `THEMES` string kept by sync-static | `config.themes` |
| Nav menu | SQL list entries `javascript:App.theme.use('x')`, radio rebuild in `app.js` | static list under `theme-factory-` IDs, radio rebuild in the runtime |

App 102 cannot simply use the installer: its navigation bar is a SQL list, which the installer refuses by
design. So app 102 keeps `sync-static` as the delivery path, but renders **the same code**.

**Steps**

1. **Shared bootstrap gains two opt-in features** (`lib/theme_factory/apexlang_runtime.py::build_bootstrap_html`,
   `installer/templates/bootstrap.html.tmpl`):
   - `hashLinks`: honour `#theme=<name>|default|iris` (and `none` as an alias of `iris`, so old links keep working).
   - `legacyKey`: if the new key is empty and `localStorage[legacyKey]` holds an allowed name, move it over
     (`none` → `iris`) and delete the legacy key. Nobody loses their choice.
   - With both off, the output must stay **byte-identical** to today's, so existing installs see no change and the
     installer's post-import projection still matches. Add a test that pins this.
2. **Default theme gets one source of truth.** Today `scripts/apply-theme.sh` edits `var DEFAULT` in page 0 by
   regex. Move it to a small file (for example `applications/ut/theme-factory.json` `{"defaultTheme": "linen"}`)
   that `apply-theme.sh` writes and `sync-static` reads.
3. **sync-static renders both page-0 bootstrap regions** from `build_bootstrap_html(default, switcherEnabled=True,
   themes, hashLinks=True, legacyKey="app.theme")`, replacing the handwritten script. Drift is reported like the
   current `THEMES` check (which this replaces).
4. **App 102 loads the runtime.** sync-static copies `installer/theme-factory-runtime.js` to `js/`; add
   `#APP_FILES#js/theme-factory-runtime.js` to the application JavaScript file URLs in
   `applications/ut/application.apx`, **before** `app.js`.
5. **`App.theme` becomes a thin wrapper** in `static-files/js/app.js`:
   - `use(name)` maps to `ApexThemeFactory.use` (`none` → `iris`).
   - `current()` reads `ApexThemeFactory.current()` (and returns `null` for `iris`).
   - Keep the name `App.theme`: `lists.apx` (nav entries) and page 405 call it.
   - Make the runtime's radio rebuild also look for `.app-theme-switcher` (app 102's list class), then delete the duplicate rebuild from `app.js`.
6. **Offline tests before touching the database:**
   - Run the rendered bootstrap in Node with mocked `localStorage`/`location`/`document`, as done for the THEMES check.
   - Cases: typo, removed theme, legacy migration (`app.theme=none` → `iris`), `#theme=default`, hash off in the installer output.
   - Update `tests/test_runtime_contract.py`, `tests/test_sync_static_module.py` and `tests/test_apexlang_patch.py`.
7. **Docs:**
   - Update the switcher paragraph in `sample-themes/README.md`.
   - Update `docs/PROJECT.md` ("Known: … URL hash").
   - Update pitfalls §4.1 (the storage key name changes).

**Live verification**
- [x] Nav **Theme** menu: exactly one radio checked, keyboard operable, choice survives reload
- [x] Page 405 cards: the current one shows the *Current* badge; choosing a card switches
- [x] `#theme=cobalt-press`, `#theme=default`, `#theme=none` links
- [x] A browser that still has `app.theme=solarized-dark` from before keeps Solarized after the first load
- [x] Dialog, drawer and wizard pages get the same theme (the second bootstrap region)
- [x] 9010 release smoke still PASS for one light and one dark theme
- [x] Console clean on every page above

**Done when** app 102 and every installed package run one bootstrap and one runtime, and the offline gate plus
the checklist above pass.

---

## Stage 2: responsive behaviour (audit item 6b, about 1 day)

None of the eight themes has an `@media` rule of its own. Universal Theme is responsive, but themes add margins,
thick borders, pill navigation, letter-spacing and grid backgrounds that were only ever checked at 1440 and 375.

**2.1 Audit first. Change nothing yet.**

For each theme × width (1440, 1024, 768, 375) × page (500 Getting Started, 406 Theme Lab, 1402 Interactive
Report, 1910 modal dialog, 1601 forms), in **your own background tab** (`new_page {url, background:true}` then
`emulate {pageId, viewport:"375x812x2,mobile,touch"}`), run:

```js
() => {
  const w = document.documentElement.clientWidth;
  const wide = [...document.querySelectorAll('body *')]
    .filter(e => e.getBoundingClientRect().right > w + 1 && getComputedStyle(e).position !== 'fixed')
    .slice(0, 15).map(e => e.tagName + '.' + [...e.classList].join('.'));
  return { page: document.documentElement.className, width: w,
           horizontalScroll: document.documentElement.scrollWidth > w, overflowing: wide };
}
```

Record the population (page, width, theme class, node count), per pitfalls §4.3d. Also look for clipped text,
wrapped buttons and unusable tables (skill `apex-responsive-design`), and run the contrast audit at 375 with
the navigation drawer open.

| Theme | Width | Page | Finding | Fix (own CSS / recipe block) |
|---|---|---|---|---|
| All 8 themes | 1440, 1024, 768, 375 | 500, 1402, 1910 | 0 horizontal scroll; layout clean; dialog responsive | Verified passing with standard UT grid & Iris tokens |
| All 8 themes | 1024, 768 | 406 | IG toolbar and specimen table contained within region view | Native UT behaviour (the first generated responsive rules had no effect; see 2.5) |
| All 8 themes | 375 | 1601 | RDS tab strip expands as horizontal touch-swipe carousel (`scroll: false`) | Native UT mobile design pattern |
| All 8 themes | 375 | All | Nav drawer open contrast exceeds WCAG AA (>5.5:1 dark, >7:1 light) | Passing |

**2.2 Generate the recipe's responsive block.**
- Each recipe already declares `responsive.strategy` (`compress` | `reflow` | `stack`) and `compactControlsAt` (768 for all 8).
- The generator (`lib/theme_factory/recipe.py::axis_css_values`) already produces the rules, and its self-reference bug was fixed on the audit branch.
- Emit them per theme as `css/apex/responsive.css`, starting with `/* @theme-factory-generated */`, imported **last** in `css/theme.css`.
- Add a drift check (like `theme.sh adapters --check`) so the file always matches the recipe.
- If the file is added to `lib/theme_factory/fingerprint.py::MODULES`, re-baseline the uniqueness numbers.

**2.3 Fix what the audit found** in each theme's own (unfenced) CSS inside `@media (max-width: 767px)`. Put
anything a whole family shares in its adapter template (`theme-templates/adapters/<family>/`) and run
`scripts/theme.sh adapters`.

**2.4 Verify.**
- [x] No horizontal scroll at 375 on the audit pages for all 8 themes
- [x] Release smoke PASS for all 8 (it covers 1440 and 375)
- [x] 768 and 1024 spot-checked on 406 and 1402
- [x] Covers unchanged, or re-captured with `scripts/theme.sh cover NAME --output … --apply --overwrite`

**2.5 Re-verify the corrected responsive rules (verified 2026-09-24).** A review of the first `responsive.css` against
UT 26.1's `Core.min.css` showed it changed nothing on screen:
- `stack` set grid columns on `.t-Cards`, which is a flex row, and on `.t-Region--cards`, which does not exist.
- `reflow` wrapped `.t-Header-controls` (a grid item) and `.t-Body-actions` (not flex).
- `compress` shrank `--app-control-h`, which the hand-written themes never read.

The generator (`lib/theme_factory/recipe.py::_responsive_rules`) now emits:

| Strategy | Themes | Rules at ≤ 768 px | What to look at |
|---|---|---|---|
| `stack` | citrus-pop, velvet-signal | `.t-Cards--{cols,2cols…5cols}` and `.a-CardView-items--grid{2…5}col` → one column | Page 405 gallery and a Cards region at 600–768 px: one card per row (UT itself keeps 2+ columns from 480 px) |
| `reflow` | linen, cobalt-press, estate-slate | `.t-Region-header` wraps; `.t-ButtonRegion-wrap` puts its content row under the left/right buttons | Region headers with several buttons and a long title (406); wizard/dialog button bars (1910) |
| `compress` | carbon-volt, solarized-dark, estate-slate-dark | `--a-button-padding-y: .375rem` on `.apex-theme-iris` (+ `--app-control-h`, `--app-space-unit`); inputs keep theme size | Buttons ≈ 30 px; inputs retain theme padding (≥ 30 px, touch-friendly); `.t-Button--small/large` modifiers unchanged |

- [x] `scripts/sync-static.sh && scripts/apex-validate.sh && scripts/apex-import.sh`
- [x] Each strategy looks right at 768 and 600 px on the pages above, and nothing changes at 1024 px and up
- [x] Release smoke PASS for one theme of each strategy (it covers 1440 and 375)

#### Live Verification Measurements (commit `e352fc7`)

| Theme | Width | Page | Measured Values (Raw JSON) | Status | Notes |
|---|---|---|---|---|---|
| `linen` | 768 | 1601 (Forms) | `{"page":"page-1600 app-UT app-theme-linen","width":768,"theme":"app-theme-linen","newCssLoaded":false,"newCssLoadedDeep":true,"regionHeaderWrap":"wrap","buttonPadY":"7px","buttonHeight":32,"inputPadY":"25px","counts":{"regionHeaders":6,"buttonRegions":0,"buttons":11,"inputs":3}}` | PARTIAL | `regionHeaderWrap: "wrap"` PASS; button regions = 0 on 1601 |
| `linen` | 768 | 1250 (Button Container) | `{"page":"page-1250 app-UT app-theme-linen","width":768,"theme":"app-theme-linen","newCssLoaded":false,"newCssLoadedDeep":true,"regionHeaderWrap":"wrap","buttonRegionAreas":"\"button-left button-right\" \"button-content button-content\"","buttonPadY":"7px","buttonHeight":32,"counts":{"regionHeaders":2,"buttonRegions":2,"buttons":17,"inputs":0}}` | PASS | `regionHeaderWrap: "wrap"`, `buttonRegionAreas` 2 rows |
| `linen` | 1024 | 1601 (Forms) | `{"page":"page-1600 app-UT app-theme-linen","width":1024,"theme":"app-theme-linen","newCssLoaded":false,"newCssLoadedDeep":true,"regionHeaderWrap":"nowrap","buttonPadY":"7px","buttonHeight":32,"inputPadY":"25px","counts":{"regionHeaders":6,"buttonRegions":0,"buttons":11,"inputs":3}}` | PASS | `regionHeaderWrap: "nowrap"` |
| `linen` | 1024 | 1250 (Button Container) | `{"page":"page-1250 app-UT app-theme-linen","width":1024,"theme":"app-theme-linen","newCssLoaded":false,"newCssLoadedDeep":true,"regionHeaderWrap":"nowrap","buttonRegionAreas":"\"button-left button-content button-right\"","buttonPadY":"7px","buttonHeight":32,"counts":{"regionHeaders":2,"buttonRegions":2,"buttons":17,"inputs":0}}` | PASS | `regionHeaderWrap: "nowrap"`, `buttonRegionAreas` 1 row |
| `solarized-dark` | 768 | 1601 (Forms) | `{"page":"page-1600 app-UT app-theme-solarized-dark","width":768,"theme":"app-theme-solarized-dark","newCssLoaded":false,"newCssLoadedDeep":true,"regionHeaderWrap":"nowrap","buttonPadY":"7px","buttonHeight":32,"inputPadY":"25px","counts":{"regionHeaders":6,"buttonRegions":0,"buttons":11,"inputs":3}}` | MISMATCH | First btn is `.t-Button--headerTree` (pad 7px); first inp is floating (pad 25px) |
| `solarized-dark` | 1024 | 1601 (Forms) | `{"page":"page-1600 app-UT app-theme-solarized-dark","width":1024,"theme":"app-theme-solarized-dark","newCssLoaded":false,"newCssLoadedDeep":true,"regionHeaderWrap":"nowrap","buttonPadY":"7px","buttonHeight":32,"inputPadY":"25px","counts":{"regionHeaders":6,"buttonRegions":0,"buttons":11,"inputs":3}}` | MISMATCH | Same element selection mismatch on 1601 |
| `solarized-dark` | 768 | 406 (Theme Lab) | `{"page":"page-406 app-UT app-theme-solarized-dark oj-agent-os-linux oj-agent-browser-chrome","width":768,"theme":"app-theme-solarized-dark","newCssLoaded":false,"buttonPadY":"7px","buttonHeight":32,"inputPadY":"3px","counts":{"regionHeaders":0,"buttonRegions":0,"buttons":16,"inputs":4}}` | MISMATCH | Body btn: padY 5px, height 30px; inp: padY 3px, height 24px; vars: `--a-button-padding-y: .375rem` (6px), `--a-field-input-padding-y: .25rem` (4px). UT Iris formula subtracts 1px border. |
| `solarized-dark` | 1024 | 406 (Theme Lab) | `{"page":"page-406 app-UT app-theme-solarized-dark oj-agent-os-linux oj-agent-browser-chrome","width":1024,"theme":"app-theme-solarized-dark","newCssLoaded":false,"buttonPadY":"7px","buttonHeight":32,"inputPadY":"6px","counts":{"regionHeaders":0,"buttonRegions":0,"buttons":16,"inputs":4}}` | MISMATCH | Body btn: padY 8px, height 36px; inp: padY 6px, height 30px; vars: `--a-button-padding-y: .5625rem` (9px), `--a-field-input-padding-y: .4375rem` (7px). UT Iris formula subtracts 1px border. |
| `citrus-pop` | 700 | 405 (Themes Gallery) | `{"page":"page-405 app-UT app-theme-citrus-pop","width":700,"theme":"app-theme-citrus-pop","gridSelector":"a-CardView-items a-CardView-items--grid3col ","gridTemplateColumns":"652.8px","cardCount":9}` | PASS | Single-track column (652.8px), cards stacked vertically |
| `citrus-pop` | 1024 | 405 (Themes Gallery) | `{"page":"page-405 app-UT app-theme-citrus-pop","width":1024,"theme":"app-theme-citrus-pop","gridSelector":"a-CardView-items a-CardView-items--grid3col ","gridTemplateColumns":"314.925px 314.938px 314.925px","cardCount":9}` | PASS | Multi-track (3 columns: 314.925px each) |

*Root font size: 16px. Horizontal scroll: none (`scrollWidth 753 <= innerWidth 768`). Console: clean (no JS errors).*
*Checkboxes left unticked per verification rule: solarized-dark computed padding differs from expected table strings due to UT's 1px border subtraction formula and selector collision with navbar header button; flat newCssLoaded check returns false due to `@import` nesting.*

**Review of these measurements: all three strategies pass.** The "MISMATCH" and "PARTIAL" rows are
errors in the check, not in the CSS:
- `newCssLoaded: false`: the probe did not descend into `@import`ed sheets; `newCssLoadedDeep: true` is the real answer.
- **compress**: UT paints `padding = var(--a-*-padding-y) − 1px border`. The variables read exactly as generated
  (768 px: 6 px / 4 px; 1024 px: 9 px / 7 px), and page 406 shows the intended result:
  buttons 36 → 30 px, inputs 30 → 24 px. On 1601 the probe's first matches were a `.t-Button--headerTree`
  and a floating-label input, which compress deliberately does not touch.
- **reflow**: page 1250 shows both rules (header wraps; button-region content drops below the buttons).
  Page 1601 has no button regions.
- **stack**: page 405 goes from 3 columns to 1.

Decided 2026-09-24: inputs keep the theme size for touch friendliness.
- **compress inputs live verification (2026-09-24)** on page 406 (`solarized-dark`):
  - 1024px: `{"width":1024,"theme":"app-theme-solarized-dark","compressCssLoaded":true,"button":{"id":"B19609960886662538","cls":"t-Button ","padTop":"8px","height":36},"input":{"id":"P406_REQUIRED","padTop":"6px","height":30},"rootFont":"16px","noHScroll":true}`
  - 768px: `{"width":768,"theme":"app-theme-solarized-dark","compressCssLoaded":true,"button":{"id":"B19609960886662538","cls":"t-Button ","padTop":"5px","height":30},"input":{"id":"P406_REQUIRED","padTop":"6px","height":30},"rootFont":"16px","noHScroll":true}`
  Buttons compress 36 → 30 px (padTop 8 → 5 px); inputs stay touch-sized at 30 px (padTop 6 px) across both widths.



---

## Stage 3: decisions only you can make

- [x] **Oracle files in git history.** Decision: history is not rewritten. `HEAD` no longer tracks the files, but
  the repository is public, so they stay downloadable from commits before `1052881`. Revisit if that matters.
- [x] **Leftover branches.** Both repos have only `main` (checked 2026-09-24). A future cloud session may
  recreate `claude/<session-branch>`; its content is always in `main`, so delete it with
  `git push origin --delete <branch>` when that session ends, or enable *Automatically delete head branches*.
- [x] **Uniqueness warnings accepted.** All 8 themes pass, but 4 warnings stay by decision:
  carbon-volt ↔ estate-slate-dark (PROFILE_SIMILARITY) and cobalt-press ↔ estate-slate (STRUCTURAL_SIMILARITY 0.889).
  They are warnings, not errors; differentiate the themes if they should read as distinct products.


---

## Reference

| Thing | Where |
|---|---|
| Reduced-motion rule | `static-files/css/foundation/tokens.css` (end of file) |
| Shipped-token contrast and recipe-drift check | `lib/theme_factory/checks.py::_token_issues` |
| Adapter families | `theme-templates/adapters/`, `lib/theme_factory/adapters.py`, `scripts/theme.sh adapters` |
| Page-0 bootstrap and default theme | `lib/theme_factory/sync_static.py` step 1b, `applications/ut/theme-factory.json` |
| Responsive rules per strategy | `lib/theme_factory/recipe.py::_responsive_rules`; regenerate with `scripts/theme.sh responsive` (`--check` for drift) |
| Release smoke | `tools/release_smoke.py`, `tools/browser_check.py` |
