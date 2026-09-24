# Reference assets (read-only)

Byte-for-byte copies of the CSS/JS that the running app loads, fetched from the local APEX instance
by `scripts/fetch-vendor.sh --reference` (versions and SHA-256 in `ut-26.1/MANIFEST.txt`).

**Local only.** These files are Oracle-copyrighted, so `ut-*/` is gitignored and never committed. A fresh
clone has only this README: run `scripts/fetch-vendor.sh --reference` against your APEX instance (default
`http://localhost:8181`, override with `APEX_ORIGIN`). Without an instance, read the same files in Chrome
DevTools (Sources panel) or use the Chrome DevTools MCP daemon.

Purpose: offline **token and selector discovery** (spec §17, skill `apex-ut-dom-knowledge`) —
`grep` these instead of guessing a `--ut-*` / `--a-*` name or a `.t-*` class. They are the
Universal Theme / Iris *design system* this project styles against.

| File | Source URL on the instance | Use |
|---|---|---|
| `ut-26.1/Core.min.css` | `/i/themes/theme_42/26.1/css/Core.min.css` | UT structure, component classes, template-option modifiers |
| `ut-26.1/Iris.min.css` | `/i/themes/theme_42/26.1/css/Iris.min.css` | Iris token values (`--ut-*`, `--a-*`), Iris overrides |
| `ut-26.1/theme42.min.js` | `/i/themes/theme_42/26.1/js/theme42.min.js` | UT runtime behaviour (nav, sticky, dialogs) |
| `ut-26.1/app_ui-Core.min.css` | `/i/app_ui/css/Core.min.css` | APEX widget CSS (IG/IR grid, cards, menus, fields…): which `--a-*` atom a component **consumes** and its light fallback |
| `ut-26.1/app_ui-Theme-Standard.min.css` | `/i/app_ui/css/Theme-Standard.min.css` | widget state atoms set on elements (e.g. `.a-GV-pageSelector-item.is-selected` → `--a-gv-pagination-button-selected-background-color`) |
| `ut-26.1/font-apex-2.5.1.min.css` | `/i/libraries/font-apex/2.5.1/css/font-apex.min.css` | icon class names (`.fa-*`) |
| `ut-26.1/oraclesans-apex.min.css` | `/i/libraries/oracle-fonts/oraclesans-apex.min.css` | Oracle Sans `@font-face` weights |

Rules
- Never copy these into `static-files/` or upload them to app 102 — APEX already serves them.
- Never edit them. Re-run `scripts/fetch-vendor.sh` after an APEX upgrade and diff the manifest.
- Runtime truth still wins: a value read here is a *candidate*; confirm it with Chrome DevTools on the
  element (many `--a-*` are redefined per component).
- An atom missing from `Core.min.css`/`Iris.min.css` is **not** dead: the widget CSS consumes it with a
  fallback (`var(--a-x, #fff)`), so a body-level declaration still applies. Grep all four CSS files.
- Iris `:root` values written as `var(--a-button-text-color)` resolve **at :root** — a body-level override of
  the referenced atom does not reach them; override the derived atom too (see solarized-dark `reports.css`).
