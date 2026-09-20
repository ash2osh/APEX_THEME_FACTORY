# sample-themes

One folder per theme package — the only editable copy of a theme. No symlinks: `scripts/sync-static.sh`
assembles `static-files/css|js/**` and every `sample-themes/<name>/css/**` into the APEXLang export
(`css/themes/<name>/…`) and regenerates the `@themes` block of `static-files/css/app.css`.

```text
sample-themes/<name>/
├── theme.json          name, title, tagline, direction, class (app-theme-<name>), declarative template options
├── README.md           direction, technique, verification
├── css/theme.css       entry (imports tokens.css + apex/*.css)
├── css/tokens.css      token deltas, scoped to html.app-theme-<name>
├── css/apex/*.css      component rules, every selector prefixed .app-theme-<name>
└── preview/cover.jpg   960 px gallery image (+ any other captures)
```

`sync-static.sh` also ships `theme.json` and `preview/cover.jpg` as `css/themes/<name>/theme.json|cover.jpg`: the
navigation-bar **Theme** menu and the **Themes** page (405) read them from `apex_application_static_files`, so a
package appears in both as soon as it is imported — nothing to register by hand.

## How switching works
- **All** packages are loaded by `app.css`; each is inert unless `<html>` carries its class.
- Page 0 regions "Theme" (slot `banner`, standard pages) and "Theme (dialog…)" (slot `breadcrumbBar` =
  `#REGION_POSITION_01#`, the first position of the Modal Dialog / Drawer / Wizard templates) emit one inline
  script that adds `app-theme-<name>` to `<html>` before content paints — also inside dialog iframes.
- Choice, per browser (`localStorage['app.theme']`): the navigation-bar **Theme** menu (list `navigation-bar`,
  one radio entry per package + *Iris (no theme package)*, active one checked) or the cards on page 405 — both call
  `App.theme.use('<name>')` from `static-files/js/app.js`; `'none'` = bare Iris, choosing the app default clears
  the stored value. `#theme=<name>` in the URL hash still works for links (`#theme=default` clears, `#theme=none`
  = bare Iris; query parameters are rejected by session-state protection). `App.theme.current()` reads the class.
- The Universal Theme *theme style* switcher (Vita / Redwood) was removed from app 102 on 2026-09-14; the theme
  style is Iris for every package and nothing in the app references another style.
- The app **default** is the `DEFAULT` literal in the page-0 regions, set by `scripts/apply-theme.sh <name>`,
  which also applies the theme's `templateOptions` (e.g. nav Style B) to `application.apx`. Declarative
  options are per-default-theme only; the live switch changes CSS alone.

<!-- @generated:theme-catalog:start -->
| Theme | Direction | Status |
|---|---|---|
| [carbon-volt](carbon-volt/) | Square technical graphite with acid-lime actions and cyan telemetry. | **UNVERIFIED — layers not current: D** |
| [citrus-pop](citrus-pop/) | Playful pale-aqua surfaces with teal structure, tangerine pills, and buoyant cards. | **UNVERIFIED — layers not current: D** |
| [cobalt-press](cobalt-press/) | Warm editorial paper with cobalt rules, vermilion marks, and offset shadows. | **UNVERIFIED — layers not current: D** |
| [estate-slate](estate-slate/) | Precision corporate slate, white cards, and restrained champagne-amber actions. | **UNVERIFIED — layers not current: D** |
| [estate-slate-dark](estate-slate-dark/) | Monolithic dark corporate slate with luminous amber directives and emerald telemetry. | **UNVERIFIED — layers not current: D** |
| [linen](linen/) | Quiet product surfaces with white chrome, hairline seams, and teal actions. | **UNVERIFIED — layers not current: D** |
| [solarized-dark](solarized-dark/) | Terminal-inspired Solarized depth with cyan-blue accents and compact geometry. | **UNVERIFIED — layers not current: D** |
| [velvet-signal](velvet-signal/) | Spacious aubergine layers with rounded surfaces and fuchsia-violet signals. | **UNVERIFIED — layers not current: D** |
<!-- @generated:theme-catalog:end -->

Adding a theme: define a strict `theme.recipe.json`, run `scripts/theme.sh new <name> --recipe <file>`, customize
only the generated package, then run `scripts/theme.sh check <name>`. The recipe chooses identity, palette,
typography, geometry, focus, and component profiles. Files marked `/* @theme-factory-generated */` are generator
owned; unmarked handwritten CSS survives regeneration. Existing recipe-less packages remain valid maintenance
targets. After an explicitly authorized sync/import, discovery is automatic on page 405 and in the Theme menu;
page 406 Theme Lab is the candidate test surface. The theme style stays **Iris** for every package.

Custom fonts are installed with `scripts/theme.sh font add`: pin the official metadata URL and upstream source
revision, declare exact weights, and commit only WOFF2 faces, the OFL license, and recorded SHA-256 provenance.
The tool verifies Basic Latin plus Arabic coverage and never creates a runtime network font dependency.

For a curated cover, use `scripts/theme.sh cover <name> --output sample-themes/<name>/preview/cover.jpg` first as
a dry run, then add `--apply --overwrite`. The capture owns a background tab, uses per-tab emulation, preserves
the user's active tab and `localStorage`, and rejects console/network failures.

Conventions
- Roles are `--app-*` (declared with Iris defaults in `static-files/css/foundation/tokens.css` — add a default
  there before using a new role in a package); a theme-private palette may use a short prefix (`--sol-*`).
- No literal colours in `css/apex/*.css` — every value is a token from `tokens.css`. `!important` only to mirror an
  Iris `!important`, with the Iris rule quoted in a comment.
- Dark packages must remap Iris' literal `:root` tokens (see `solarized-dark/README.md`, *Technique*).
- Custom fonts: optional self-hosted WOFF2 assets (`wOF2` signature) under `fonts/` with licenses under `licenses/`. External font URLs and data URLs are forbidden. Manifest declares `body` (required if fonts used), optional `heading` and `mono`. Family identifiers are package-prefixed (`ThemeFactory-<name>-<role>`) and Font APEX icons remain untouched.
- `preview/` holds `cover.jpg` plus a few curated `.jpg` captures; iteration PNGs never get committed
  (`.gitignore`). Every package README ends with a *Verified* section (pages, widths, contrast, console).
- `scripts/theme.sh check` caches only successful content-addressed results. Any consumed local/shared source or
  validator change invalidates the key. A candidate-lane PASS is not release evidence.
