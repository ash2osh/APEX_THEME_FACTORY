# Finding

Status:
Pending — two highest-confidence gaps fixed 2026-09-14 in this PR (`--a-field-input-hover-background-color` in
`css/apex/forms.css`, `--a-toolbar-background-color` in `css/apex/reports.css` — both found independently by
two separate agent runs against different worktree commits, strong cross-confirmation). The remaining ~50
second-order tokens and six unopened-page component families listed below are **not yet fixed** — this finding
stays pending until those are addressed and a live contrast audit (docs/CHROME_DEVTOOLS_MCP.md) runs against
the standard page list plus the newly-identified pages (see Page). No formal evaluation has been run against
this finding (see Regression Scenario).

Category:
BUG

Confidence:
CONFIRMED for the two fixed atoms (grep-verified consumption in `.agents/knowledge/reference/ut-26.1/*.css`
against real component presence in `applications/ut/pages/*.apx`; `--a-field-input-hover-background-color` was
found independently by two separate agent sessions working from different worktree commits).
LOW confidence, explicitly not runtime-verified, for the remaining gap list below and for whether the two fixed
atoms render as intended — no Chrome session was available when this was discovered (see Evidence).

APEX Version:
26.1.4 (Universal Theme / Iris)

Page:
App 102, all 122 pages by source review; concrete misses trace to p1410 (Interactive Grid — different
component from the Interactive Report checked on p1402), p1411 (Faceted Search), p1601 (Markdown Editor /
Percent Graph item types, also used on p423), p1800 (Calendar), p1902 (Charts), p1903 (Help Text), p1906
(Map), p1405/p3003 (Comments / chat style) — none of which is p500 or p1402, the two pages the package was
originally "verified" against.

Component:
`sample-themes/solarized-dark/` theme package. Fixed here: `--a-field-input-hover-background-color`
(`css/apex/forms.css`), `--a-toolbar-background-color` (`css/apex/reports.css`). Still open: `--ut-header-
menubar-item-hover-*`, `--ut-component-icon-*`, `--ut-component-badge-text-color`, `--ut-navtabs-item-active-
highlight-color`/`-hover-background-color`, datepicker/menu/chip/chat/report-controls/resultsitem second-order
atoms, and new-family literals for faceted search, markdown editor, percent graph, FullCalendar, JET chart
tooltips (~50 declarations total, per the source audit below).

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

## Existing Assumption

`sample-themes/README.md` and this package's own README stated "verified 2026-09-14" with a specific 14-page
runtime pass; `apex-design-review`'s completion checklist already required the contrast audit "on the standard
page list... with 0 package failures" before that claim — the checklist was correct, it just wasn't followed
before the status was written (now corrected in this PR).

## Impact

A theme package can look complete after a narrow, plausible-seeming spot check (the two most-visited pages)
while large parts of a 122-page reference app — anything using Interactive Grid rather than Interactive Report,
any hover state, any of ~6 item/region types absent from both checked pages — ship unthemed. A false "Verified"
claim is worse than no claim: it tells the next agent/human not to re-check.

## Proposed Knowledge Change

Not yet made (spec §58: record → evidence → scope → regression scenario → confirm old instructions fail it →
*then* change the skill — and per pitfalls.md §5.3, promoting before that evaluation runs is exactly the
mistake this project has already been caught making once). Candidate for a future session to evaluate: when
Chrome is unavailable, the extract-diff-grep method in Evidence §1–3 is a workable substitute for *finding*
coverage gaps, but not for *confirming* visual correctness — it should not by itself upgrade a package's status
to "verified".

## Regression Scenario

Matches `.agents/evaluations/11-dark-package-coverage.md` closely, but that scenario's own evaluation runs
(2026-09-14, see `evaluations/runs/2026-09-14/11-dark-package-coverage-{baseline-eda510d,current-neutral}.md`)
showed the relevant skill guidance is already adequate at both the old and current commit — so this finding's
remaining gap list is a real, still-open bug in the *package*, not evidence of a skill-text problem to promote
against. No new evaluation scenario is proposed; the existing 11 already covers this class of issue.

## Scope

Page-specific bug in this package's current state (two atoms now fixed here; ~50 more listed above still open)
plus a reusable process point: a theme package's "Verified" section should name exactly what was
runtime-checked vs. source-reviewed, since the two give very different confidence.
