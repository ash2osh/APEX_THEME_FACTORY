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
| Font | Oracle Sans (`--a-base-font-family`), icons Font APEX 2.5.1 | runtime `<link>` list |

## Target application

| | |
|---|---|
| URL | http://localhost:8181/ords/r/demo/ut/getting-started |
| Workspace | `DEMO` |
| Application | `102` — *Universal Theme 26.1 Reference*, alias `UT` |
| Landing page | 500 (Getting Started); 122 pages total |
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
├── scripts/                  # apex-export / validate / import, apply-theme, sync-static, fetch-vendor
└── .agents/                  # skills, knowledge, findings, evaluations (spec §50)
    ├── skills/               # also exposed via .claude/skills and .agent/skills symlinks
    ├── knowledge/            # + reference/ut-26.1: read-only copies of Core/Iris CSS, theme42.js, Font APEX
    ├── findings/{pending,accepted,rejected}/
    └── evaluations/
```

## Tooling

| Tool | Purpose | Doc |
|---|---|---|
| Chrome DevTools MCP (`--autoConnect` to the user's running Chrome) | runtime truth: DOM, computed CSS, console, network, screenshots | [CHROME_DEVTOOLS_MCP.md](CHROME_DEVTOOLS_MCP.md) |
| SQLcl `docker-demo` | `apex export / validate / import` in APEXLang | [APEXLANG_ROUNDTRIP.md](APEXLANG_ROUNDTRIP.md) |
| `scripts/fetch-vendor.sh` | pulls Alpine.js into `static-files/js/vendor` and the UT/Iris CSS+JS into `.agents/knowledge/reference` for offline grep | [`.agents/knowledge/reference/README.md`](../.agents/knowledge/reference/README.md) |
| APEX Builder / Page Designer | semantic map of runtime elements | http://localhost:8181/ords/r/apex/app-builder |
| External skills `impeccable` (critique/audit/polish, Operate mode) and `web-design-guidelines` (checklist review) | design-quality passes on the CSS/Alpine layers; usage rules in the `design-to-apex` router | `skills-lock.json`; update with `npx skills update -p` |

## Not yet decided / open

- ~~Static files upload path~~ decided 2026-09-13: `scripts/sync-static.sh` assembles `static-files/css|js/**` and
  `sample-themes/*/css/**` into `applications/ut/shared-components/static-files/` (registering `file` entries,
  pruning stale ones); the app references `#APP_FILES#css/app.css` and `#APP_FILES#js/app.js`. Theme *linen*
  is the default in app 102; visitors switch with the nav-bar **Theme** menu or page 405 *Themes* (both discover
  packages from `css/themes/<name>/theme.json` in the static files) — see `sample-themes/README.md`.
- Known: APEX session-state protection rejects unknown query parameters on friendly URLs, so runtime switches
  use the URL hash. Page 0 can only address Standard-template slots; they map to other templates by position.
