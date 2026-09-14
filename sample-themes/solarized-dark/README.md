# Solarized Dark — a VS Code developer look for Universal Theme / Iris

*Precision terminal cyan and deep solarized blues.*

| | |
|---|---|
| Base | APEX 26.1.4 · Universal Theme 42 · theme style **Iris** (unchanged) |
| Direction | VS Code Solarized Dark: `#002b36` editor canvas, `#073642` regions and cards, `#00212b` chrome, cyan `#2aa198` for actions and selection, blue for links |
| Palette | Ethan Schoonover's Solarized (VS Code bundled theme); UI surfaces (input, hover, selected) are VS Code's own |
| Scope | app-wide, one CSS layer scoped under `html.app-theme-solarized-dark`; no page-level edits |
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
  misc.css               shadows off · badges · tabs · alert accent edge · Prism.js code samples
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
| code (Prism, on the canvas): keyword green, string cyan, comment base0, number `#dd629e`, entity `#d67147` | | | 4.7 / 4.75 / 4.75 / 4.5 / 4.5 |
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

## Verified (2026-09-14, APEX 26.1.4 / Iris)

Automated text-contrast audit (every visible text node vs its effective background, AA thresholds) on pages
500, 1202, 1208, 1304, 1402, 1410, 1500, 1600, 3110, 405 and dialog page 1912: **0 failures attributable to the
package**. Remaining: page 1304 badge-list demo uses Universal Theme's `u-color-*` fills (white on `#de7f11`,
2.9:1) — identical under plain Iris. Widths 1440 / 375; console clean; IG paging, dialog open/close, nav-bar
menu, keyboard focus ring checked.
