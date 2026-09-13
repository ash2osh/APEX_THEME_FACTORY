# Linen — a quiet-product look for Universal Theme / Iris

*Light linen canvas, hairline seams, one teal thread.*

| | |
|---|---|
| Base | APEX 26.1.4 · Universal Theme 42 · theme style **Iris** (unchanged) |
| Direction | "Quiet product": white chrome, hairline borders, flat 8px surfaces, tighter density, Iris teal `#00688c` reserved for actions and selection |
| Palette / font | Iris palette and Oracle Sans, untouched — every colour is an Iris token alias |
| Scope | app-wide, one CSS layer; no page-level edits |
| Spec | [docs/superpowers/specs/2026-09-13-modern-look-design.md](../../docs/superpowers/specs/2026-09-13-modern-look-design.md) |
| Applied to app 102 | 2026-09-13 (import `2eb072f` + this package) |

## Preview

| Getting Started (1440) | Interactive Report | Modal dialog | Mobile nav (375) |
|---|---|---|---|
| ![](preview/p500-getting-started-1440.jpg) | ![](preview/p1402-interactive-report-1920.jpg) | ![](preview/p1910-modal-dialog-1920.jpg) | ![](preview/p500-mobile-nav-375.jpg) |

## What's inside

```text
css/
├── app.css                 entry point (@import order matters)
├── foundation/
│   ├── tokens.css          --app-* tokens: radius 6/8/12, one dialog shadow, type scale, weights 500/600, focus ring
│   ├── reset.css · typography.css · utilities.css
└── apex/
    ├── shell.css           header (white, no accent strip) · side nav (white, Style B pill, teal-on-shade current) · title bar · hero
    ├── regions.css         regions/cards 8px + hairline + no shadow · 14px/600 titles · content-block scale 24/20/17 · breadcrumb title
    ├── buttons.css         36px / 13px-500 / 6px · default white+hairline · hot + button-group teal · :focus-visible ring
    ├── forms.css           6px inputs · teal focus halo · 13px/500 muted stacked labels
    ├── reports.css         IRR / IG / classic: subtle 40px header 13px/600 · 40px rows · horizontal hairlines · tabular numerals
    ├── dialogs.css         12px radius · single soft shadow · hairline title bar · menus
    └── misc.css            alert/badge/component shadows off · badge radius
```

## Technique

Core/Iris declare each component's *base* atoms (`--a-button-*`, `--a-field-*`, `--a-gv-*`, `--jui-dialog-*`,
most `--ut-*`) on `:root` and every modifier/state on the element. Linen overrides the base atoms on
`body.apex-theme-iris` (the theme-style scope — never `:root`), so `--small`, `--hot`, `--header`, floating
labels, palette buttons etc. keep precedence. Atoms set on an element (`.a-IRR{--a-gv-border-radius}`) are
overridden on that element; the three `!important`s mirror Iris' own and are commented.
Detaching `css/app.css` restores Iris exactly.

## Declarative requirements (already in `applications/ut/application.apx`)

```apexlang
css {
    fileUrls: #APP_FILES#css/app.css
}
navigationMenu { templateOptions: [ … t-TreeNav--styleB ] }   # Side Navigation Menu → Style: Style B
```

## Apply / switch

```bash
scripts/apply-theme.sh linen      # points static-files/css at this theme
scripts/sync-static.sh            # copies css/** into the APEXLang export + registers file entries
scripts/apex-import.sh            # validate + import (asks for confirmation)
```

## Verified

Pages 500, 1201, 1402, 1410, 1500, 1600, 1910 · widths 1440 / 1024 / 768 / 375 · console clean ·
IG refresh, dialog open/close, keyboard focus · text contrast ≥ 5.4:1, input border 3.3:1.
Runtime hooks recorded in `.agents/knowledge/ut-dom-*.md`; open items in `.agents/findings/pending/`.
