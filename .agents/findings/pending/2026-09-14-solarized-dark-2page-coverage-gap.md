# Finding

Status:
Pending — full source-level literal/derived-token audit completed 2026-09-14 in this PR. Every one of Iris'
282 literal-colour `:root` tokens and 121 `var()`-chains targeting one, cross-checked against the whole
`sample-themes/solarized-dark/css/` tree; every gap with confirmed consumption (offline widget-CSS mirror) and
a confirmed-present owning component (`applications/ut/pages/*.apx`) is now fixed — see Evidence §6 for the
full before/after count and the file-by-file list. Two categories remain deliberately unfixed, both explained
in Evidence §7 (not a gap, or not verifiable offline) — not blockers. Stays pending, not promoted to
`accepted/`, because a **live** contrast audit (docs/CHROME_DEVTOOLS_MCP.md) on the expanded page list has
still not run — no Chrome session in any pass that touched this finding. That live pass is the only remaining
step before this package's README can honestly drop "not fully verified."

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

## Existing Assumption

`sample-themes/README.md` and this package's own README stated "verified 2026-09-14" with a specific 14-page
runtime pass; `apex-design-review`'s completion checklist already required the contrast audit "on the standard
page list... with 0 package failures" before that claim — the checklist was correct, it just wasn't followed
before the status was written (now corrected in this PR).

## Impact

A theme package can look complete after a narrow, plausible-seeming spot check (the two most-visited pages)
while large parts of a 122-page reference app — anything using Interactive Grid rather than Interactive Report,
any hover state, any of ~10 item/region types absent from both checked pages — ship unthemed. A false "Verified"
claim is worse than no claim: it tells the next agent/human not to re-check. Closed by the full source audit in
Evidence §6 — every literal/derived-token gap with verifiable consumption and a confirmed-present page is now
fixed; only the JET/FullCalendar custom-property families remain genuinely unverifiable without Chrome.

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

Page-specific bug in this package, now closed at the source-review level (see Evidence §6): every gap with
confirmed consumption and a confirmed-present page is fixed as of this PR. Two categories remain genuinely
open, per §7: Oracle JET's/FullCalendar's own custom-property theming (unverifiable offline — their consuming
CSS isn't in the reference bundle) and a live Chrome contrast-audit pass to confirm every fix actually renders
as intended. Also a reusable process point: a theme package's "Verified" section should name exactly what was
runtime-checked vs. source-reviewed, since the two give very different confidence.
