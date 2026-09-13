# Design System — APEX Theme Factory (Universal Theme / Iris)

Governing rules: [AGENT_SPEC.md](AGENT_SPEC.md) §15–§25, §39, §43.
Theme style is **Iris, light only** (see [PROJECT.md](PROJECT.md)). This document is the single
place that records tokens, naming, and conventions. Update it when a token or convention is added.

## 1. Token strategy

Iris already exposes a full token layer as CSS custom properties. Application tokens (`--app-*`)
**alias Iris tokens first** and only introduce literals when Iris has no equivalent.

```text
Iris (--ut-*, --a-*)  ←  aliased by  ←  --app-*  ←  used by  ←  .app-* components
```

Rules
- Never restyle by redefining `--ut-*` / `--a-*` globally on `:root` (that is Theme Roller's job and would fight Iris). Redefine them **scoped** under an `.app-*` class when a component needs a local variant.
- Before adding an `--app-*` literal, check the Iris table below and `static-files/css/foundation/tokens.css`.
- New tokens only when reusable and design-system meaningful (spec §18).

## 2. Iris tokens (live values, app 102 page 500, APEX 26.1.4)

Read at runtime via `getComputedStyle(document.documentElement).getPropertyValue(name)`.
Full list of 167 `--ut-*` values: [`.agents/knowledge/iris-ut-tokens.md`](../.agents/knowledge/iris-ut-tokens.md).

### Palette

| Token | Value | Notes |
|---|---|---|
| `--ut-palette-primary` | `#00688c` | |
| `--ut-palette-primary-contrast` | `#fff` | |
| `--ut-palette-primary-shade` | `#e4f1f7` | |
| `--ut-palette-primary-text` | `#00688c` | |
| `--ut-palette-primary-alt` | `#227e9e` | |
| `--ut-palette-success` | `#436b1d` | |
| `--ut-palette-success-shade` | `#e4f5d3` | |
| `--ut-palette-warning` | `#8f520a` | |
| `--ut-palette-warning-shade` | `#fceddc` | |
| `--ut-palette-danger` | `#b3311f` | |
| `--ut-palette-danger-shade` | `#ffebe8` | |
| `--ut-palette-info` | `#227e9e` | |
| `--ut-palette-info-shade` | `#e4f1f7` | |
| `--ut-palette-generic` | `#f2f2f2` | |
| `--ut-palette-generic-shade` | `#f9f9f9` | |

### Surfaces, text, borders

| Token | Value |
|---|---|
| `--ut-body-background-color` | `#fbf9f8` |
| `--ut-body-text-color` | `#161513` |
| `--ut-component-background-color` | `#fff` |
| `--ut-component-border-color` | `rgba(0,0,0,.1)` |
| `--ut-component-border-width` | `1px` |
| `--ut-component-text-title-color` | `#000` |
| `--ut-component-text-subtitle-color` | `rgba(0,0,0,.85)` |
| `--ut-component-text-muted-color` | `rgba(0,0,0,.65)` |
| `--ut-link-text-color` | `#0e7295` |
| `--ut-focus-outline-color` | `#00688c` |
| `--ut-header-background-color` | `#302d2a` |
| `--ut-header-text-color` | `#fff` |
| `--ut-body-nav-background-color` | `#302d2a` |
| `--ut-body-title-background-color` | `#f1efed` |

### Radius, shadow, layout

| Token | Value |
|---|---|
| `--ut-border-radius-sm` | `.125rem` |
| `--ut-border-radius-md` | `.25rem` |
| `--ut-border-radius` | `.25rem` |
| `--ut-border-radius-lg` | `.5rem` |
| `--ut-badge-border-radius` | `1rem` |
| `--ut-component-border-radius` | `0.25rem` |
| `--ut-shadow-sm` | `0 .125rem .25rem -.125rem rgba(0,0,0,.1)` |
| `--ut-shadow-md` | `0 .75rem 1.5rem -.75rem rgba(0,0,0,.3)` |
| `--ut-shadow-lg` | `0 1.5rem 3rem -1.5rem rgba(0,0,0,.3)` |
| `--ut-component-box-shadow` | `0 1.5rem 3rem -1.5rem rgba(0,0,0,.3)` |
| `--ut-header-height` | `3.5rem` |
| `--ut-nav-width` | `15rem` |
| `--ut-body-content-max-width` | `100%` |

### Typography (from `--a-*` base layer)

| Token | Value |
|---|---|
| `--a-base-font-family` | `"Oracle Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, …, sans-serif` |
| `--a-base-font-family-mono` | `SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace` |
| `--a-base-font-weight-semibold` | `500` (runtime-verified 2026-09-13; Core declares 600, Iris overrides to 500) |
| `--a-button-font-size` / `--a-button-border-radius` | `.75rem` / `.125rem` |
| Icons | Font APEX 2.5.1 (`apex-icons-fontapex`) |

Iris namespaces seen in `Iris.min.css`: `--a-*` (1018 refs, component atoms), `--ut-*` (418, theme
tokens), `--u-*` (100, utilities), `--jui-*`, `--oj-*`. All are **reserved** (spec §20).

## 3. Application tokens (`--app-*`)

Defined in `static-files/css/foundation/tokens.css`. Current set is the seed from spec §16, aliased
to Iris:

| App token | Aliases |
|---|---|
| `--app-color-primary` | `var(--ut-palette-primary)` |
| `--app-color-success` / `-warning` / `-danger` / `-info` | `var(--ut-palette-success)` … |
| `--app-surface-page` / `--app-surface-card` | `var(--ut-body-background-color)` / `var(--ut-component-background-color)` |
| `--app-text-primary` / `--app-text-secondary` | `var(--ut-body-text-color)` / `var(--ut-component-text-muted-color)` |
| `--app-border-color` | `var(--ut-component-border-color)` |
| `--app-radius-sm` / `-md` / `-lg` | `var(--ut-border-radius-sm)` / `-md` / `-lg` |
| `--app-shadow-sm` / `-md` / `-lg` | `var(--ut-shadow-sm)` / `-md` / `-lg` |
| `--app-space-1 … 8` | `.25rem .5rem .75rem 1rem 1.5rem 2rem` (Iris has no spacing scale; literal) |

## 4. Naming

- Application classes: `app-block`, `app-block__element`, `app-block--modifier` (BEM, spec §19).
- Static IDs: `snake_case`, prefixed by page purpose when page-specific (`dash_kpi_row`).
- Alpine components: `Alpine.data('camelCaseName', …)`, one file per component in `static-files/js/components/`.
- Files: `static-files/css/components/<name>.css` pairs with `static-files/js/components/<name>.js`.

## 5. Selector policy (spec §21–§24)

`.app-x` → `#static_id` → `.app-x .t-Thing` → `.t-Thing` (only if verified app-wide) → structural (never).
`!important` only with a comment explaining the verified cascade problem.

## 6. Responsive

Universal Theme breakpoints are the reference; check every change at 1440, 1024, 768, 375 px
(spec §45). Iris navigation: side nav `--ut-nav-width: 15rem`, header `--ut-header-height: 3.5rem`.

## 7. Registry of reusable visual patterns

None yet. Add a row per pattern once promoted (spec §38) and cross-link to [COMPONENTS.md](COMPONENTS.md).

| Pattern | Class | Since | Used on |
|---|---|---|---|
