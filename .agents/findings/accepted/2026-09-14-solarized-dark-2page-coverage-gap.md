# Finding

Status:
**Accepted (2026-09-17)** — scenario 11 passes against the fixed, imported package
(`.agents/evaluations/runs/2026-09-17/11-dark-package-coverage-postimport.md`). All four defects the live pass
found are now in `sample-themes/solarized-dark/css/**`, were built, installed and imported, and are measured
fixed on the running app: Interactive Grid row selection **1.06:1 → 8.17:1**, faceted-search text buttons
2.39:1 → 0 failures on the page, MapLibre attribution 2.57:1 → **12.25:1**, and the Oracle JET chart text that
could not be observed at all before an import — **25 of 25 SVG text nodes pass**, worst 4.86:1, fills exactly
the package's base1/base2. The 24-page sweep reports 7 failures, **0 package-caused**: p1304 badges and p1800
`apex-cal-green` are byte-identical with and without `html.app-theme-solarized-dark` (bare-Iris A/B), so they
are Universal Theme / APEX literals. The project's audit instrument, which scored SVG text by CSS `color` and
so reported the chart page clean, was fixed too (`tools/browser_matrix.py`, regression test in
`tests/test_browser_matrix.py::ContrastInstrumentTests`).

**Residual coverage, deliberately kept open and not claimed:** 98 of app 102's 122 pages were never opened;
1024/768 were not swept in app 102 (Layer D covers them for the consumer apps); IRR / Card View / Media List /
Timeline / Comments selection states were not driven individually — they share the `--a-palette-*` chain whose
fix is measured on the Interactive Grid, which is inference, not measurement; keyboard focus rings and further
chip/error states are untested. This finding is accepted for what it identified and fixed, not as a claim of
exhaustive coverage.

Prior status, for the record: *Pending (2026-09-17) — … **None of those three fixes is in this repository.**
They were authored in the scenario-11 evaluation worktree, which was thrown away … re-apply it there, rebuild,
install, and re-audit before this package ships.* That re-application happened on 2026-09-17 and is what the
run log above measures.
Superseded: the 2026-09-14 claim that "every literal/derived-token gap findable by source review is fixed" was
wrong in scope — it missed two whole `:root`-frozen families (`--a-palette-*` and `--a-base-link-text-color`)
besides the `--oj-*` family it had explicitly deferred.

Category:
BUG

Confidence:
CONFIRMED for every fixed atom's *existence and consumption* (mechanical extract-diff-grep against all four
files in `.agents/knowledge/reference/ut-26.1/` — see Evidence §6 — plus a real owning page for each; every
declaration in the fix is traceable to a specific `:root` line and a specific consuming selector).
LOW confidence, explicitly not runtime-verified, for whether every fix *renders as intended* — no Chrome
session has been available in any pass that touched this finding (see Evidence).

APEX Version:
26.1.4 (Universal Theme / Iris)

Page:
App 102, all 122 pages by source review; concrete misses trace to p1410 (Interactive Grid — different
component from the Interactive Report checked on p1402), p1411 (Faceted Search), p1601 (Markdown Editor /
Percent Graph item types, also used on p423), p1800 (Calendar), p1902 (Charts), p1903 (Help Text), p1906
(Map), p1405/p3003 (Comments / chat style) — none of which is p500 or p1402, the two pages the package was
originally "verified" against.

Component:
`sample-themes/solarized-dark/` theme package — now fully audited. Fixed across this PR (in order):
`--a-field-input-hover-background-color`, `--a-toolbar-background-color`, plus (this pass) ~50 more atoms:
`--ut-header-menubar-item-hover-*`, `--ut-component-icon-color`, `--ut-component-badge-text-color`,
`--ut-navtabs-item-hover-background-color`, the remaining datepicker/`--jui-datepicker-*`/menu-accel/chip/chat
second-order atoms, `--a-cv-icon-*`/`-initials-*`/`-active-border-color` (Card View avatars), File Drop,
Markdown Editor, Combo Box, and the report-controls/resultsitem/searchresults remainder — plus new-family
coverage for Faceted Search, Percent Graph, Help Text dialog, and Map legend. See Evidence §6 for the full
file list. Deliberately left unfixed (§7): `--oj-*`/`--fc-*` (Oracle JET / FullCalendar's own CSS custom
properties — their consuming runtime CSS isn't in the offline reference bundle, so consumption can't be
verified without Chrome), `--u-color-*` demo swatches, Diagram/Gantt/dev-toolbar (no such region in app 102),
and a few individually-verified non-issues (Map zoom control text, translucent chip-remove overlays, an unused
button-count atom, `--ut-palette-primary-alt-shade` with zero consumers, `--ut-hero-region-title-text-color`
already superseded by a direct property rule on the same selector).

## Observation

The package's README Status/Verified sections claimed a 14-page runtime contrast audit with "0 failures",
"console clean", and interaction checks — but per the task that prompted this review (an agent-evaluation run,
2026-09-14), only pages 500 and 1402 had actually been opened. That overclaim was corrected separately (see
`sample-themes/solarized-dark/README.md`'s 2026-09-14 addendum, this same PR).

Independent of the false claim, the underlying CSS genuinely under-applies the package's own documented
technique (pitfalls.md §1.1–1.2: restate every Iris `:root` literal, and every `var()` chain that resolves at
`:root`). Of Iris' 282 literal-colour `:root` custom properties, ~28 had no override anywhere in the package
that were real gaps (most of the rest are legitimately out of scope — `--u-color-*` demo swatches, Diagram/Gantt
with no such region in app 102, the dev toolbar). Of ~135 second-order tokens (Iris declares them as
`var(--other-literal-token)` on `:root`, which freezes to the light value *at `:root`* per standard CSS
custom-property substitution — the exact pitfalls.md §1.2 mechanism), roughly 50 were unaddressed with confirmed
consumption in the offline widget-CSS mirror or a confirmed-present owning component.

The two fixed here were invisible on both originally-checked pages specifically because of what those two pages
don't contain:
- `--a-field-input-hover-background-color` was never set, so `.apex-item-text:hover` (and siblings) fell back
  to Iris' literal `#fff` — every text input, on every page, flashed white on mouse hover. Page 500 is mostly
  read-only content; page 1402's own search field has a *direct* `.a-IRR-search-field` rule that bypasses the
  generic atom, so hovering it never exposed the bug.
- `--a-toolbar-background-color` was never set (`Iris.min.css`: `var(--ut-region-header-background-color)` at
  `:root`, frozen before this package's body-level override of that token reaches it — pitfalls.md §1.2 again).
  `.a-IRR-toolbar` (p1402) has its own direct override, so it looked fine — but `.a-IG-header` (Interactive
  Grid, p1410, a different component from the Interactive Report on p1402), the Markdown Editor toolbar, Popup
  LOV search bar, and CKEditor panels have no such direct rule and stayed white.

## Evidence

No Chrome DevTools session was available when this was found (two agent-evaluation runs, both explicitly
withheld Chrome/import/DB) — source-level audits, not runtime ones:
1. Regex-extracted every `:root { --name: value }` pair from `.agents/knowledge/reference/ut-26.1/Iris.min.css`
   (282 literal-colour, ~135 `var()`-chains targeting one of those 282).
2. Diffed that list against every `--name:` assignment anywhere under `sample-themes/solarized-dark/css/`.
3. For each gap, grepped `var(--the-token` across `Core.min.css` / `app_ui-Core.min.css` / `app_ui-Theme-
   Standard.min.css` to confirm real consumption, and grepped `applications/ut/pages/*.apx` for the owning
   region/item type to confirm the component actually ships in app 102.
4. `--a-field-input-hover-background-color` and the general shape of this gap were found **independently** by
   two separate agent sessions working from two different worktree commits (`eda510d` and `b0aa923`) with two
   different prompts — strong cross-confirmation it's a real, not spurious, gap.
5. Where evidence pointed the other way, the token was left alone: `--mg-ctrl-group-button-text-color` (Map
   zoom control text) has no themable background counterpart anywhere in Iris, so its literal black text is
   still correct.
6. **2026-09-14, full closure pass** (same PR, still no Chrome session): re-ran steps 1–3 as a script (extract
   all 802 `:root` custom properties, split into 280 literal-colour + 121 var-chains-to-a-literal, diff against
   the whole `sample-themes/solarized-dark/css/` tree). Before this pass: 117 literal / 98 chain gaps remained.
   Removed the out-of-scope categories (§7) and fixed every remaining one with confirmed consumption + a
   confirmed-present page:
   - `css/tokens.css`: datepicker completion (7 atoms) + `--jui-datepicker-*` (2), chat completion (15 atoms),
     `--ut-component-badge-text-color`, `--ut-component-icon-color`, `--ut-header-menubar-item-hover-*` (2),
     `--ut-navtabs-item-hover-background-color`.
   - `css/apex/dialogs.css`: `--a-menu-accel-text-color`, `--a-menu-focused-accel-text-color`,
     `--a-menu-callout-border-color`.
   - `css/apex/regions.css`: `--a-cv-active-border-color`, `--a-cv-icon-*` (2), `--a-cv-initials-*` (2).
   - `css/apex/reports.css`: `--a-report-controls-cell-label-border-color`, `--a-report-controls-input-*` (2),
     `--a-gv-nodata-message-text-color`, `--a-resultsitem-*` (2), `--a-searchresults-pagination-color`.
   - `css/apex/forms.css`: `--a-chip-border-color`, File Drop (4 atoms), Markdown Editor (3), Combo Box (1).
   - `css/apex/misc.css`: Faceted Search (6 atoms, new section), Percent Graph (4, new), Help Text dialog (1,
     new), Map legend (1, new), Chart tooltips (3, new).
   After this pass: 2 literal/chain candidates remained, both individually verified as non-issues (§7).
7. **Deliberately left unfixed, with reason**:
   - `--u-color-*` (45 colour + 45 contrast = 90 tokens) — Universal Theme's own demo-palette swatches (p1304
     badge-list); already documented app-wide as "identical under plain Iris", out of scope for any package.
   - `--a-diagram-*` / `--a-dev-toolbar-*` (25 tokens) — no Diagram/Gantt region and no dev-toolbar surface in
     app 102's 122 pages (confirmed: no `type: diagram` / `Gantt` hit in `applications/ut/pages/*.apx`).
   - `--oj-*` (Oracle JET's own custom-property theming, ~23 tokens) and `--fc-*` (FullCalendar's own, 4
     tokens) — both libraries' *consuming* CSS (JET's compiled runtime stylesheet, FullCalendar's own CSS) is
     not part of the offline `.agents/knowledge/reference/ut-26.1/` mirror (that mirror is Oracle APEX/UT's own
     CSS only), so — unlike every other atom in this finding — consumption cannot be verified without a live
     page. p1902 (Charts) and p1800 (Calendar) are confirmed-present pages that likely use some of these, but
     guessing which specific custom properties their compiled output actually reads, and to what visual effect,
     without being able to inspect it, would be exactly the "write CSS from remembered class names" pattern
     evaluation scenario 09 tests against. Left as the one remaining item needing a live Chrome pass.
   - Individually verified non-issues: `--a-button-count-*` (no button in app 102 has a count badge —
     `grep -rl "countBadge\|t-Button--badge" applications/ut/pages/*.apx` empty), `--a-chip-applied-is-active-
     remove-*-background-color` (translucent white overlays — `hsla(0,0%,100%,.1/.2)` — lighten whatever's
     underneath regardless of theme, not a literal opaque colour mismatch), `--mg-ctrl-group-button-text-color`
     (see §5), `--oj-color-spectrum-border-color` (JET colour-picker, no such item type present),
     `--ut-palette-primary-alt-shade` (`grep` across all four reference files: zero consuming rules — a
     declared-but-dead token, no possible visual effect), `--ut-hero-region-title-text-color` (Core:
     `.t-HeroRegion-title{color:var(--ut-hero-region-title-text-color,var(--ut-component-text-title-color))}`
     — but `regions.css` already sets `.t-HeroRegion-title{color:var(--app-text-emphasized)}` as a direct
     property on the same selector, loaded later in the cascade, so it already wins regardless of the atom;
     confirmed not a real gap, not just an unfixed one).

8. **2026-09-17, first live Chrome pass** (project Chrome MCP daemon, own background tab, theme applied before
   paint, 1440×900 plus 375×812 on four pages; import and DB changes withheld, so everything below measures
   app 102 as installed at commit `4c1abe1`). 24 pages — 500, 405, 423, 1202, 1208, 1304, 1402, 1405, 1410,
   1411, 1412, 1500, 1600, 1601, 1800, 1902, 1903, 1906, 1910, 3003, 3110, 4000, 6303, 6304 — plus dialog page
   1912 in its iframe; 4 469 visible text nodes; 0 console errors. Audit = the documented snippet plus a
   light-surface sweep (opaque backgrounds of luminance ≥ 0.6) for the "stayed white" failure mode.
   - Resting state: 10 failures, of which 7 are Universal Theme's / APEX's own literals (p1304 `--u-color-*`
     badge values 2.94:1 and 3.70:1; p1800 `apex-cal-green` events, white on the literal `#2ecc71`, 2.10:1 ×5),
     and 3 are the package's: p1411 Faceted Search `Show All`/`Clear All` at **2.39:1** and the p1906 MapLibre
     attribution text and links at **2.57:1**.
   - Non-resting: p1410 selecting an Interactive Grid row paints the cells Iris' `#e4f1f7` under base2 text —
     **1.06:1**; p1601's date picker renders its current day as a light `#e4f1f7` chip (5.43:1, AA-passing and
     visually wrong); p1902's JET charts paint **24 of 25** text nodes at 1.46–1.62:1.
   - Causes: `Core.min.css` declares `--a-palette-*` (15 atoms) and `--a-base-link-text-color` as `var(--ut-*)`
     **on `:root`**, and `Iris.min.css` does the same for 32 `--oj-*` tokens — the §1.2 freeze, in families
     this finding's §6 pass never enumerated. MapLibre's attribution plate is its own white surface inheriting
     the package's light body text.
   - Fixes and live A/B (candidate CSS injected into the running page, then re-measured): faceted search
     2.39 → **4.50**; map attribution 2.57 → **12.25**; IG selected row 1.06 → **8.17**; date picker current
     day → **9.28** on the dark wash. Re-running the whole 24-page sweep with the candidate CSS applied
     produced **no new failure and no new light surface** anywhere.
   - JET remains unverified: setting the `--oj-*` properties live, clearing `oj.ThemeUtils`' cache and
     refreshing the chart regions re-rendered the SVG (a marked text node was replaced) yet the new text still
     came out `rgb(0,0,0)` — JET resolves style defaults once at bootstrap, so only an import + reload can
     confirm the fix. FullCalendar, by contrast, is answered in the package's favour: UT declares `--fc-*` on
     `.apex-fullcalendar-5`, an element scope, so the package's body-level `--ut-*` does reach it (measured
     `--fc-page-bg-color` `#073642`, `--fc-event-bg-color` `#4b9fda`, `--fc-event-text-color` `#002b36`).
   - Method note worth keeping: the documented audit reads CSS `color`, so it scores SVG text by the wrong
     property and reported the chart page clean. An AA sweep that does not read `fill` cannot verify any
     package that ships charts.

## Existing Assumption

`sample-themes/README.md` and this package's own README stated "verified 2026-09-14" with a specific 14-page
runtime pass; `apex-design-review`'s completion checklist already required the contrast audit "on the standard
page list... with 0 package failures" before that claim — the checklist was correct, it just wasn't followed
before the status was written (now corrected in this PR).

## Impact

A theme package can look complete after a narrow, plausible-seeming spot check (the two most-visited pages)
while large parts of a 122-page reference app — anything using Interactive Grid rather than Interactive Report,
any hover state, any of ~10 item/region types absent from both checked pages — ship unthemed. A false "Verified"
claim is worse than no claim: it tells the next agent/human not to re-check. The full source audit in Evidence
§6 closed every gap it enumerated — but the live pass in §8 then found four more, three of them in families
that audit never enumerated at all, and the worst of them in a *state* no source diff can rank. The general
lesson stands and is now measured: source review finds gaps, only the browser establishes correctness.

## Proposed Knowledge Change

Not yet made (spec §58: record → evidence → scope → regression scenario → confirm old instructions fail it →
*then* change the skill — and per pitfalls.md §5.3, promoting before that evaluation runs is exactly the
mistake this project has already been caught making once). Candidate for a future session to evaluate: when
Chrome is unavailable, the extract-diff-grep method in Evidence §1–3 is a workable substitute for *finding*
coverage gaps, but not for *confirming* visual correctness — it should not by itself upgrade a package's status
to "verified".

## Regression Scenario

Matches `.agents/evaluations/11-dark-package-coverage.md` closely. That scenario's own evaluation runs
(2026-09-14, see `evaluations/runs/2026-09-14/11-dark-package-coverage-{baseline-eda510d,current-neutral}.md`
on branch `evaluations-run-2026-09-14`) were corrected 2026-09-14 from PASS to **ambiguous** — both runs are
source-level substitutes for a live Chrome contrast audit the scenario's `Expected` line requires, so neither
adequacy nor inadequacy of the skill guidance was actually established either way. This finding's own gap list
(§6–7 below) is independent of that open question — it's a directly-verified bug in the *package* (grep-
confirmed consumption + confirmed-present page), not something riding on how scenario 11 eventually resolves.
No new evaluation scenario is proposed; the existing 11 already covers this class of issue once it can
actually be run with Chrome.

## Scope

Page-specific bug in this package. Closed at the source-review level by Evidence §6, then reopened and widened
by the live pass in §8 (four further defects, three families the source pass had not enumerated). FullCalendar
is now resolved in the package's favour; Oracle JET is confirmed broken with a written but unverified fix; and
the live pass itself still needs to be repeated against an imported build, on the remaining 98 pages, at the
1024/768 widths and over the untested selection/focus states. Also a reusable process point: a theme package's "Verified" section should name exactly what was
runtime-checked vs. source-reviewed, since the two give very different confidence.
