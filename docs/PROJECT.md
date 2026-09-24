# Project: APEX Theme Factory

Design-engineering workbench for Oracle APEX on **Universal Theme / Iris**.
Governing spec: [AGENT_SPEC.md](AGENT_SPEC.md). Read it before any design work.

## Hard constraints

| Constraint | Value | Verified |
|---|---|---|
| APEX version | **26.1.4** (`apex.env.APEX_VERSION`) | runtime, 2026-09-13 |
| Theme | Universal Theme (theme 42), `baseTheme: ut-26.1` | `applications/ut/shared-components/themes/universal-theme/theme.apx` |
| Theme style | **Iris** — *mandatory*. Nothing in this project may depend on Vita, Redwood Light, or any other style. The reference app's theme-style switcher (nav bar, page 405, `APPLY_THEME_STYLE`, `P0_THEME_STYLE_ID`, Vita/Redwood previews) was removed 2026-09-14; the other styles remain as inert rows under Shared Components → Themes: the theme is *subscribed* to the standard Universal Theme, so its styles are read-only in the Builder (no Delete) and not expressible in APEXLang; removing them would mean unsubscribing the theme | `apex_application_theme_styles` (Iris `IS_CURRENT = Yes`) |
| Colour scheme | Iris ships **light only** (`--ut-color-scheme: light`; no `prefers-color-scheme` block in `Iris.min.css`) | `Iris.min.css` |
| Font | system UI stack (`--a-base-font-family` = `-apple-system, …, sans-serif`; `oraclesans-apex.min.css` is linked but Oracle Sans is not in the stack and never loads), icons Font APEX 2.5.1 | runtime `document.fonts` + computed style, 2026-09-16 |

## Target application

| | |
|---|---|
| URL | http://localhost:8181/ords/r/demo/ut/getting-started |
| Workspace | `DEMO` |
| Application | `102` — *Universal Theme 26.1 Reference*, alias `UT` |
| Landing page | 500 (Getting Started); Theme catalog 405; consolidated Theme Lab 406 |
| Schema / DB user | `DEMO` |
| SQLcl saved connection | `docker-demo` (`sql -name docker-demo`) |
| Static files prefix | `#APP_FILES#` → `r/demo/102/files/static/v…/` |
| Theme assets | `/i/themes/theme_42/26.1/css/Core.min.css`, `…/css/Iris.min.css`, `…/js/theme42.min.js` |

Runtime body classes on the landing page (useful selectors):
`t-PageBody t-PageBody--leftNav t-PageTemplate--standard apex-side-nav apex-icons-fontapex apex-theme-iris`
and `<html class="page-500 app-UT">`.

## Source layout

```text
APEX_THEME_FACTORY/
├── AGENTS.md                 # agent entry point (CLAUDE.md -> AGENTS.md)
├── docs/                     # AGENT_SPEC, DESIGN_SYSTEM, COMPONENTS, PROJECT, tool docs
├── applications/ut/          # APEXLang export of app 102 (declarative source of truth)
├── sample-themes/<name>/     # theme packages (theme.json, css/, preview/); all loaded, class-switched (default: linen)
├── static-files/css/         # app.css entry (+ generated @themes block), foundation/ (shared tokens, reset, …)
├── static-files/js/          # app.js (App.theme helper), components/, vendor/ (Alpine.js 3.17.2)
├── scripts/                  # theme.sh, apex-export / validate / import, apply-theme, sync-static, install-all-themes
└── .agents/                  # skills and knowledge
    ├── skills/               # also exposed via .claude/skills and .agent/skills symlinks
    └── knowledge/            # pitfalls + reference/ut-26.1: local-only (gitignored) copies of Core/Iris CSS, theme42.js, Font APEX
```

## Tooling

| Tool | Purpose | Doc |
|---|---|---|
| Chrome DevTools MCP (`--autoConnect` to the user's running Chrome) | runtime truth: DOM, computed CSS, console, network, screenshots | [CHROME_DEVTOOLS_MCP.md](CHROME_DEVTOOLS_MCP.md) |
| SQLcl `docker-demo` | `apex export / validate / import` in APEXLang | [APEXLANG_ROUNDTRIP.md](APEXLANG_ROUNDTRIP.md) |
| `scripts/install-all-themes.sh` | Installs any/all theme packages into any APEX application with switcher | [README.md](../README.md) |
| `scripts/theme.sh` | Recipe scaffold, fonts, author checks, covers, and `release` (check + package + live smoke) | [README.md](../README.md#releasing-a-theme) |
| `scripts/fetch-vendor.sh` | pulls Alpine.js into `static-files/js/vendor` and (`--reference` alone) the UT/Iris CSS+JS into the gitignored `.agents/knowledge/reference` for offline grep | [`.agents/knowledge/reference/README.md`](../.agents/knowledge/reference/README.md) |
| APEX Builder / Page Designer | semantic map of runtime elements | http://localhost:8181/ords/r/apex/app-builder |
| External skills `impeccable` (critique/audit/polish, Operate mode) and `web-design-guidelines` (checklist review) | design-quality passes on the CSS/Alpine layers; usage rules in the `design-to-apex` router | `skills-lock.json`; update with `npx skills update -p` |
| Codex PR review bot (`chatgpt-codex-connector`) | comments P-level findings on every pull request (verify each at runtime before acting); `@codex review` re-runs it | GitHub repo settings |
| Contrast audit (`evaluate_script` snippet) | AA text-contrast sweep of a page (the release smoke runs it automatically) | [CHROME_DEVTOOLS_MCP.md](CHROME_DEVTOOLS_MCP.md) |
| Pitfalls record | every trap met in this project, by layer, with the fix | [`.agents/knowledge/pitfalls.md`](../.agents/knowledge/pitfalls.md) |

CI runs `tests/run-offline.sh` on every push and pull request. Live checks need the local database and the
approved Chrome session, so they run locally through `scripts/theme.sh release NAME`.

## Not yet decided / open

- ~~Static files upload path~~ decided 2026-09-13: `scripts/sync-static.sh` assembles `static-files/css|js/**` and
  `sample-themes/*/css/**` into `applications/ut/shared-components/static-files/` (registering `file` entries,
  pruning stale ones); the app references `#APP_FILES#css/app.css` and `#APP_FILES#js/app.js`. Theme *linen*
  is the default in app 102 (declared in `applications/ut/theme-factory.json`); visitors switch with the nav-bar **Theme** menu or page 405 *Themes* (both discover
  packages from `css/themes/<name>/theme.json` in the static files) — see `sample-themes/README.md`.
- Known: APEX session-state protection rejects unknown query parameters on friendly URLs, so runtime switches
  use the URL hash (`#theme=<name>|default|iris`). Storage is namespaced per application (`localStorage['apex.themeFactory.' + appId]`).
  Page 0 can only address Standard-template slots; they map to other templates by position.
