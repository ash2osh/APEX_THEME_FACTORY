# Project: APEX Theme Factory

Design-engineering workbench for Oracle APEX on **Universal Theme / Iris**.
Governing spec: [AGENT_SPEC.md](AGENT_SPEC.md). Read it before any design work.

## Hard constraints

| Constraint | Value | Verified |
|---|---|---|
| APEX version | **26.1.4** (`apex.env.APEX_VERSION`) | runtime, 2026-09-13 |
| Theme | Universal Theme (theme 42), `baseTheme: ut-26.1` | `applications/ut/shared-components/themes/universal-theme/theme.apx` |
| Theme style | **Iris** — *mandatory*. Nothing in this project may depend on Vita, Redwood Light, or any other style | `apex_application_theme_styles` (Iris `IS_CURRENT = Yes`) |
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
├── static-files/css|js/      # repository CSS / JS / Alpine (spec §15, §27); js/vendor = Alpine.js 3.17.2
├── scripts/                  # apex-export / validate / import wrappers (SQLcl docker-demo), fetch-vendor
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

- Git: the directory is not a git repository yet. Initialise before the first real design change so APEXLang diffs are reviewable.
- Static files: `static-files/` is a scaffold; nothing is uploaded to app 102 yet. Upload path and `#APP_FILES#` references get decided with the first component.
