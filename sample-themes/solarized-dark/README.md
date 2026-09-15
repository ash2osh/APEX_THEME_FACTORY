# Solarized Dark — a VS Code developer look for Universal Theme / Iris

*Precision terminal cyan and deep solarized blues.*

| | |
|---|---|
| Base | APEX 26.1.4 · Universal Theme 42 · theme style **Iris** (unchanged) |
| Direction | VS Code Solarized Dark: `#002b36` editor canvas, `#073642` regions and cards, `#00212b` chrome, cyan `#2aa198` for actions and selection, blue for links |
| Palette | Ethan Schoonover's Solarized (VS Code bundled theme); UI surfaces (input, hover, selected) are VS Code's own |
| Scope | app-wide, one CSS layer scoped under `html.app-theme-solarized-dark`; no page-level edits (the reference app's own `.dm-*` demo surfaces are restated in `misc.css`) |
| Status | 2026-09-14: AA contrast pass, tokens consolidated, verified on the pages below |

## Preview

| Getting Started (1440) | Interactive Report (1920) | Modal dialog (1920) | Mobile nav (375) |
|---|---|---|---|
| ![](preview/p500-getting-started-1440.jpg) | ![](preview/p1402-interactive-report-1920.jpg) | ![](preview/p1910-modal-dialog-1920.jpg) | ![](preview/p500-mobile-nav-375.jpg) |

## What's inside

```text
theme.json               manifest: name, title, tagline, direction, class, declarative template options (nav Style B)
css/theme.css            entry, loaded by static-files/css/app.css (@themes block, generated)
css/tokens.css           --sol-* palette, --app-* deltas (html scope), --ut-* / --a-* remaps (body scope)
css/apex/
  shell.css              header (#002c39) · side nav (#00212b, #005a6f pill, light text) · title bar · footer
  regions.css            Cards-region atoms · wizard (cyan active, green complete) · card list · metric card · headings
  buttons.css            36px / 13px-500 / 4px · default card surface + 3:1 border · hot cyan/dark text · primary blue-text
  forms.css              4px inputs on #003847 · 3.3:1 border · cyan focus · 13px/500 labels · floating labels
  reports.css            IRR / IG / classic: #00212b header 13px/600 · 40px rows · solid hover · themed pager and footer
  dialogs.css            jQuery UI dialog and menu atoms · wizard dialog pages
  misc.css               shadows off · badges · tabs · alert accent edge · Prism.js code samples ·
                          faceted search · percent graph · help dialog · map legend · chart tooltips
preview/                 cover.jpg (gallery) + the four captures above
```

Shared foundation (reset, typography, utilities, the full `--app-*` vocabulary with Iris defaults) lives in
`static-files/css/foundation/` and is not part of the package.

## Technique

Same as [linen](../linen/README.md): every rule is scoped to `html.app-theme-solarized-dark`; Universal Theme
tokens and component atoms are overridden on `body.apex-theme-iris` (never `:root`) so every modifier keeps
precedence. Two things a dark package must do that a light one can skip:

- **Remap the literal tokens.** Iris declares ~70 `--ut-*` tokens and ~100 `--a-*` atoms with *literal* light
  colours on `:root` (`--ut-region-text-color: #161513`, `--a-checkbox-background-color: #fff`, …). They do not
  follow `--ut-component-*`, so `tokens.css` restates each of them. Some Iris values are `var()` chains that
  resolve at `:root` (`--a-gv-pagination-button-text-color: var(--a-button-text-color)`), so the derived atom
  has to be set as well. Widget state atoms live in `/i/app_ui/css/Theme-Standard.min.css`
  (`--a-gv-pagination-button-selected-background-color`, fallback `#e0e0e0`).
- **Keep the hierarchy inside AA.** See below.

The five `!important`s in `shell.css` mirror Iris' own (`.a-TreeView-row.is-hover{…!important}`,
`.is-current--top.is-hover{color:#fff!important;background-color:#006c91!important}`) and are commented.

## Deviation from Solarized: text levels

Solarized's dark hierarchy is base1 / base0 / base01. On the `#073642` card surface those measure 4.9 / 4.1 /
2.4:1 — only base1 passes AA for 13–14px text. The package therefore uses **base3 / base2 / base1**
(titles / body / secondary) and tints the accents that are used *as text*:

| Role | Colour | On card `#073642` | On canvas `#002b36` |
|---|---|---|---|
| titles, input text (`--app-text-emphasized`) | base3 `#fdf6e3` | 12.0 | 13.9 |
| body (`--app-text-primary`) | base2 `#eee8d5` | 10.6 | 12.3 |
| labels, subtitles, placeholders (`--app-text-secondary`) | base1 `#93a1a1` | 4.9 | 5.6 |
| links, primary palette (`--sol-blue-text`) | `#4b9fda` (blue +17 % white) | 4.5 | 5.2 |
| validation / danger text (`--sol-red-text`) | `#e87674` (red +33 %) | 4.5 | 5.2 |
| dark text on cyan / green / yellow / blue-text fills (`--app-text-on-accent`) | base03 `#002b36` | 4.75 / 4.7 / 4.7 / 5.2 | |
| white on the red badge | `#ffffff` | 4.6 | |
| code (Prism, on the canvas): keyword green, string cyan, comment base0, number `#e174a9`, entity `#db815c` | | | 4.7 / 4.75 / 4.75 / 5.2 / 5.2 |
| input border (`--app-border-strong`) vs card — WCAG 1.4.11 | `rgba(131,148,150,.8)` | 3.3 | 3.6 |

Accents kept raw for icons, markers, highlight bars and large text (≥ 3:1): cyan 4.1, green 4.1, yellow 4.1 on cards.

## Apply / switch

```bash
scripts/apply-theme.sh solarized-dark   # make it the app default (page-0 DEFAULT + template options from theme.json)
scripts/sync-static.sh                  # assemble static-files + sample-themes/*/css into the APEXLang export
scripts/apex-import.sh                  # validate + import
```
Live, per browser: navigation-bar **Theme** menu or page 405 *Themes*; `#theme=solarized-dark` in a URL;
`App.theme.use('solarized-dark')` in the console.

## Status: source-reviewed, NOT fully verified — a live Chrome pass is still required

**Not "Verified".** The line below records a real automated contrast pass, but it is resting-state and
14-page only; several rounds of PR review since (2026-09-14, `chatgpt-codex-connector` on #2 and #5) and a
follow-up source audit (`.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md`) have found
and fixed real gaps that pass missed. As of the last addendum below, every literal/derived-token gap findable
by source review (grep against the offline reference CSS + confirmed page presence) is fixed — only Oracle
JET's and FullCalendar's own custom-property families remain, and those are unverifiable without Chrome (their
consuming CSS isn't in the offline reference bundle). Read this section as "the last known-good baseline plus
a changelog of fixes since", not as a current verification — do not extend "Verified" to the whole package
until a live pass of the audit below runs against the expanded page list (below) and the two JET/Calendar
pages get a real look.

### 2026-09-14 contrast-audit baseline (APEX 26.1.4 / Iris) — as claimed by the session that ran it, unverified since

**Not independently re-confirmed.** The paragraph below reports what a prior session's automated audit script
claimed; no later review (including the multiple PR-review rounds that found real gaps this pass missed — see
the addenda below) has re-run it or otherwise confirmed its own reliability. Given this package's demonstrated
pattern of overclaimed verification, treat these specific numbers the same way as everything else in this
README not labeled "confirmed 2026-09-15 or later": plausible, sourced from a real script run, but not
something this session can vouch for.

Automated text-contrast audit (every visible text node vs its effective background, AA thresholds) on pages
500, 1202, 1208, 1304, 1402, 1410, 1500, 1600, 3110, 4000, 6303, 6304, 405 and dialog page 1912: **0 failures
attributable to the package**. Remaining: page 1304 badge-list demo uses Universal Theme's `u-color-*` fills (white on `#de7f11`,
2.9:1) — identical under plain Iris. Widths 1440 / 375; console clean; IG paging, dialog open/close, nav-bar
menu, keyboard focus ring checked. This pass only samples nodes present at rest on page load — it cannot and
did not catch hover-only or empty-state-only failures (see below).

### 2026-09-14 addendum: two non-resting-state fixes (PR #2 review)

The automated pass above only samples text nodes at rest, so it missed two non-resting-state failures caught
by PR review (`#2`, `chatgpt-codex-connector`) and fixed by static CSS/reference-CSS analysis (no Chrome
available in that session; still needs a live re-check):
- `#P4000_SEARCH`'s empty-results state (`.dm-Search:empty:before`, page 4000 inline CSS hard-codes
  `rgba(0,0,0,.5)` for the "No Results" text) — fixed in `css/apex/misc.css`.
- IR/IG toolbar control labels on `:hover` (`.a-IG-controls-item--X`/`.a-IRR-controls-item--X` set
  `--a-report-controls-cell-label-hover-background-color` directly on the element with pale literals from
  `app_ui-Core.min.css`, outranking the body-level mapping, so the light label text landed on a pale hover
  background) — fixed in `css/apex/reports.css`.

A third comment on that PR (page-4000 search/category/results near-white-on-white) was already covered by the
`input#P4000_SEARCH` / `.dm-Search-*` rules below before this addendum.

### 2026-09-14 addendum: two more coverage gaps (agent-evaluation source review)

Two more atoms, found independently by two separate agent-evaluation runs doing an unrelated source review of
this package (see `.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md` for the full,
still-open gap list — this PR fixes only the two highest-confidence items from it):
- `--a-field-input-hover-background-color` was never set, so every text input flashed Iris' literal `#fff` on
  hover, app-wide — fixed in `css/apex/forms.css`.
- `--a-toolbar-background-color` resolves as `var(--ut-region-header-background-color)` at Iris' `:root`
  (pitfalls.md §1.2 — frozen before this package's body-level override of that token reaches it), so
  `.a-IG-header` (Interactive Grid, p1410), the Markdown Editor toolbar, Popup LOV search bar, and CKEditor
  panels stayed white — fixed in `css/apex/reports.css`.

### 2026-09-14 addendum: full literal/derived-token gap closure

Completed the systematic audit the two runs above started: every one of Iris' 282 literal-colour `:root`
tokens and 121 `var()`-chains targeting one, cross-checked against this package's whole `css/` tree. Fixed
every remaining gap with confirmed consumption and a confirmed-present owning page — ~50 atoms across
`tokens.css`, `apex/{dialogs,regions,reports,forms,misc}.css` — including full coverage for Card View
icon/initials avatars, the date picker, popup menus, Comments/chat, File Drop, Markdown Editor, Combo Box, and
new sections for Faceted Search (p1411), Percent Graph (p423/p1601), Help Text (p1903), and Map legend
(p1906). Full list, and what was deliberately left out and why, in
`.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md` §6–7.

**Newly-identified pages that need a live check before "Verified"** (beyond the original 14-page list):
1410, 1411, 1601, 423, 1800, 1902, 1903, 1906, 1405, 3003, 1412. Pages 1800 (Calendar) and 1902 (Charts) also
need Chrome to determine whether Oracle JET's/FullCalendar's own theming reaches this package at all — the
one remaining open question, unresolved by source review because their consuming CSS isn't in the offline
reference mirror.
