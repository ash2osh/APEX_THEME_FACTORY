# sample-themes

One folder per theme package — the only editable copy of a theme. No symlinks: `scripts/sync-static.sh`
assembles `static-files/css|js/**` and every `sample-themes/<name>/css/**` into the APEXLang export
(`css/themes/<name>/…`) and regenerates the `@themes` block of `static-files/css/app.css`.

```text
sample-themes/<name>/
├── theme.json        name, class (app-theme-<name>), declarative template options
├── README.md         direction, technique, verification
├── css/theme.css     entry (imports tokens.css + apex/*.css)
├── css/tokens.css    token deltas, scoped to html.app-theme-<name>
├── css/apex/*.css    component rules, every selector prefixed .app-theme-<name>
└── preview/          captures
```

## How switching works
- **All** packages are loaded by `app.css`; each is inert unless `<html>` carries its class.
- Page 0 regions "Theme" (slot `banner`, standard pages) and "Theme (dialog…)" (slot `breadcrumbBar` =
  `#REGION_POSITION_01#`, the first position of the Modal Dialog / Drawer / Wizard templates) emit one inline
  script that adds `app-theme-<name>` to `<html>` before content paints — also inside dialog iframes.
- Choice: `#theme=<name>` in the URL hash (query parameters are rejected by session-state protection) →
  stored in `localStorage['app.theme']`; `#theme=default` clears it; `#theme=none` = bare Iris.
  `App.theme.use('<name>')` / `App.theme.current()` in `static-files/js/app.js` do the same.
- The app **default** is the `DEFAULT` literal in the page-0 regions, set by `scripts/apply-theme.sh <name>`,
  which also applies the theme's `templateOptions` (e.g. nav Style B) to `application.apx`. Declarative
  options are per-default-theme only; the live switch changes CSS alone.

| Theme | Direction | Status |
|---|---|---|
| [linen](linen/) | quiet product — white chrome, hairlines, flat 8px surfaces, teal for actions only | default in app 102 (2026-09-13) |

Adding a theme: copy `linen/` → `<name>/`, rename the class in `theme.json`/`css`, run `sync-static.sh`,
import, open with `#theme=<name>`. The theme style stays **Iris** for every package.
