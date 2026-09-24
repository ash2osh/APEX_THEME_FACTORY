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

- [ ] Offline gate passes locally
- [ ] Daemon attached to the approved Chrome (a single consent prompt, answered once)
- [ ] `scripts/reset-consumer.sh` has created or reset app 9010

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

- [ ] 0.1 … 0.9 all as expected. Write anything unexpected into `.agents/knowledge/pitfalls.md` before moving on.

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
- [ ] Nav **Theme** menu: exactly one radio checked, keyboard operable, choice survives reload
- [ ] Page 405 cards: the current one shows the *Current* badge; choosing a card switches
- [ ] `#theme=cobalt-press`, `#theme=default`, `#theme=none` links
- [ ] A browser that still has `app.theme=solarized-dark` from before keeps Solarized after the first load
- [ ] Dialog, drawer and wizard pages get the same theme (the second bootstrap region)
- [ ] 9010 release smoke still PASS for one light and one dark theme
- [ ] Console clean on every page above

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
| | | | | |

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
- [ ] No horizontal scroll at 375 on the audit pages for all 8 themes
- [ ] Release smoke PASS for all 8 (it covers 1440 and 375)
- [ ] 768 and 1024 spot-checked on 406 and 1402
- [ ] Covers unchanged, or re-captured with `scripts/theme.sh cover NAME --output … --apply --overwrite`

---

## Stage 3: decisions only you can make

- [ ] **Oracle files in git history.** `HEAD` no longer tracks them; old commits still contain them. Options:
  make the repo private, or rewrite history (`git filter-repo --path .agents/knowledge/reference/ut-26.1
  --invert-paths`, then force-push `main`; every clone must re-clone).
- [ ] **Leftover branches** (this cloud session may not delete branches). All their work is in `main`:
  - factory: `claude/determined-hawking-v3qviv` (PR #8, merged)
  - team: `claude/determined-hawking-v3qviv` (PR #2), `claude/hopeful-ride-eu60f9` (PR #1, squash-merged)
  - team: `codex/p1-remediation-flow-simplification` shares no history with `main` and was last touched
    2026-09-10. Keep a tag first if you want it: `git fetch origin codex/p1-remediation-flow-simplification && git push origin FETCH_HEAD:refs/tags/archive/codex-p1-remediation`
  - delete with `git push origin --delete <branch>`, or the trash icon on GitHub's Branches page
- [ ] **Uniqueness warnings** that predate the audit: cobalt-press ↔ estate-slate (STRUCTURAL_SIMILARITY 0.889),
  carbon-volt ↔ estate-slate-dark (PROFILE_SIMILARITY). Accept them, or differentiate the themes.

---

## Reference

| Thing | Where |
|---|---|
| Reduced-motion rule | `static-files/css/foundation/tokens.css` (end of file) |
| Shipped-token contrast and recipe-drift check | `lib/theme_factory/checks.py::_token_issues` |
| Adapter families | `theme-templates/adapters/`, `lib/theme_factory/adapters.py`, `scripts/theme.sh adapters` |
| Page-0 allow-list (replaced in Stage 1) | `lib/theme_factory/sync_static.py` step 1b |
| Release smoke | `tools/release_smoke.py`, `tools/browser_check.py` |
