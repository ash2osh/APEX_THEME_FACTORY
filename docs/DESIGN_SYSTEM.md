# Design System — APEX Theme Factory (Universal Theme / Iris)

Governing rules: [AGENT_SPEC.md](AGENT_SPEC.md) §15–§25, §39, §43.
Theme style is **Iris, light only** (see [PROJECT.md](PROJECT.md)); dark looks are theme packages layered on Iris. This document is the single
place that records tokens, naming, and conventions. Update it when a token or convention is added.

## 1. Token strategy

Iris already exposes a full token layer as CSS custom properties. Application tokens (`--app-*`)
**alias Iris tokens first** and only introduce literals when Iris has no equivalent.

```text
Iris (--ut-*, --a-*)  ←  aliased by  ←  --app-*  ←  used by  ←  .app-* components
```

Rules
- Never restyle by redefining `--ut-*` / `--a-*` globally on `:root` (that is Theme Roller's job and would fight Iris). Redefine them **scoped** under an `.app-*` class when a component needs a local variant.
- **App-wide restyle (user-approved, e.g. the 2026-09-13 "quiet product" look):** override the *base* atoms on
  `body.apex-theme-iris` — the theme-style scope, not `:root`. Core/Iris declare base atoms on `:root` and every
  modifier/state on the element, so body-level overrides restyle everything while `--small`, `--hot`, `--header`,
  floating labels etc. keep precedence. Where an atom is set on the element (`.a-IRR{--a-gv-border-radius}`),
  override on that element. Prefer an atom override to a property override whenever the atom exists.
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
| `--a-base-font-family` | `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif` — **measured 2026-09-16** on app 102 p500/p1410 and both consumer apps: Iris 26.1.4 links `oraclesans-apex.min.css` but the stack does not name Oracle Sans, so its faces stay `unloaded`; the body renders in the system UI font. Earlier "Oracle Sans" claims were the intent, not the runtime. |
| `--a-base-font-family-mono` | `SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace` |
| `--a-base-font-weight-semibold` | `500` (runtime-verified 2026-09-13; Core declares 600, Iris overrides to 500) |
| `--a-button-font-size` / `--a-button-border-radius` | `.75rem` / `.125rem` |
| Icons | Font APEX 2.5.1 (`apex-icons-fontapex`) |

### Custom theme fonts (portable packages)
Theme packages may supply optional self-hosted custom fonts:
- Roles: `body` (required if fonts declared), optional `heading`, optional `mono`. Missing roles fall back to what Iris actually renders - the system UI stack, and `--a-base-font-family-mono` for mono (not Oracle Sans; see the `--a-base-font-family` row above).
- Storage: WOFF2 assets in `sample-themes/<name>/fonts/<name>-<weight>-<style>.woff2` and non-empty licenses in `sample-themes/<name>/licenses/`.
- Format: Must be valid WOFF2 binary starting with signature `wOF2`. Lower-kebab-case naming.
- Prohibition: External font URLs (e.g. Google Fonts), `@import url(...)`, data URLs, TTF, and OTF files are strictly forbidden.
- Generated identifiers: Family names are package-prefixed (`ThemeFactory-<name>-<role>`) to eliminate cross-theme collisions.
- Font APEX isolation: Never apply `font-family` to universal `*`, icon elements (`.fa`, `.fa-*`, `.t-Icon`, `[class*=icon]`).
- Scoped tokens: Set `--app-font-family-body`, `--app-font-family-heading`, `--app-font-family-mono` on `html.app-theme-<name>`.

Iris namespaces seen in `Iris.min.css`: `--a-*` (1018 refs, component atoms), `--ut-*` (418, theme
tokens), `--u-*` (100, utilities), `--jui-*`, `--oj-*`. All are **reserved** (spec §20).

## 3. Application tokens (`--app-*`)

`static-files/css/foundation/tokens.css` declares **every** `--app-*` token with its Iris-default value — the
shared vocabulary each theme package can rely on. A package changes values only under `html.app-theme-<name>`
in its own `css/tokens.css` (see §3.2). Theme-private palette tokens may use a short theme prefix
(`--sol-*` in Solarized Dark); anything used as a *role* is `--app-*`.

### 3.1 Foundation (Iris defaults)

| App token | Iris default | Role |
|---|---|---|
| `--app-color-primary` / `-success` / `-warning` / `-danger` / `-info` | `var(--ut-palette-primary)` … | semantic colours |
| `--app-accent-shade` | `var(--ut-palette-primary-shade)` | tint for current / selected states |
| `--app-surface-page` / `--app-surface-card` | `var(--ut-body-background-color)` / `var(--ut-component-background-color)` | canvas / regions, cards |
| `--app-surface-chrome` | `var(--ut-header-background-color)` | header, side navigation |
| `--app-surface-subtle` | `var(--ut-palette-generic-shade)` | title bar, dialog button pane |
| `--app-surface-input` | `var(--ut-component-background-color)` | text fields, search boxes |
| `--app-surface-hover` | `var(--ut-component-highlight-background-color)` | hovered rows, menu items |
| `--app-surface-selected` | `var(--ut-palette-primary-shade)` | selected rows, nav pill, pager |
| `--app-text-emphasized` / `-primary` / `-secondary` | `var(--ut-component-text-title-color)` / `var(--ut-body-text-color)` / `var(--ut-component-text-muted-color)` | titles / body / labels, subtitles |
| `--app-text-on-accent` | `var(--ut-palette-primary-contrast)` | text on primary / hot fills |
| `--app-border-color` / `--app-border-hairline` | `var(--ut-component-border-color)` / `var(--ut-component-border-width) solid …` | decorative hairlines |
| `--app-border-strong` | `rgba(0,0,0,.2)` | boundaries that identify a control (≥ 3:1) |
| `--app-radius-sm` / `-md` / `-lg` | `var(--ut-border-radius-sm)` / `-md` / `-lg` (2 / 4 / 8 px) | |
| `--app-shadow-sm` / `-md` / `-lg` / `--app-shadow-dialog` | `var(--ut-shadow-sm)` / `-md` / `-lg` / `-lg` | |
| `--app-shell-header-h` / `--app-shell-nav-w` | `var(--ut-header-height)` / `var(--ut-nav-width)` | 3.5rem / 15rem |
| `--app-control-h` | `2rem` | Iris buttons and inputs ≈ 32px |
| `--app-focus-ring` | `0 0 0 2px var(--ut-component-background-color), 0 0 0 4px var(--ut-focus-outline-color)` | |
| `--app-font-weight-medium` / `-semibold` | `500` / `var(--a-base-font-weight-semibold, 500)` | Iris resolves semibold to 500 |
| `--app-text-xs … 2xl` | `12 / 13 / 14 / 17 / 20 / 24 px` | 1.2 ratio on a 14px base |
| `--app-space-1 … 8` | `.25 .5 .75 1 1.5 2 rem` | Iris has no spacing scale; literal |

### 3.2 Theme deltas

| Theme | Direction | Typography |
|---|---|---|
| `carbon-volt` | Square technical graphite with acid-lime actions and cyan telemetry. | Noto Kufi Arabic |
| `citrus-pop` | Playful pale-aqua surfaces with teal structure, tangerine pills, and buoyant cards. | Tajawal |
| `cobalt-press` | Warm editorial paper with cobalt rules, vermilion marks, and offset shadows. | Cairo |
| `estate-slate` | Precision corporate slate, white cards, and restrained champagne-amber actions. | IBMPlexSansArabic |
| `estate-slate-dark` | Monolithic dark corporate slate with luminous amber directives and emerald telemetry. | IBMPlexSansArabic |
| `linen` | Quiet product surfaces with white chrome, hairline seams, and teal actions. | Iris / system |
| `solarized-dark` | Terminal-inspired Solarized depth with cyan-blue accents and compact geometry. | IBM Plex Sans, Space Grotesk, IBM Plex Mono |
| `velvet-signal` | Spacious aubergine layers with rounded surfaces and fuchsia-violet signals. | Alexandria |

#### Detailed Linen / Solarized reference

| Token | **linen** (app default) | **solarized-dark** |
|---|---|---|
| `--app-surface-*` | chrome → white (`--ut-component-background-color`) | page `#002b36`, card `#073642`, chrome `#00212b`, subtle `#002c39`, input `#003847`, hover `#004052`, selected `#005a6f` |
| `--app-text-*` | Iris | emphasized base3 `#fdf6e3`, primary base2 `#eee8d5`, secondary base1 `#93a1a1`, on-accent base03 |
| `--app-color-*` | Iris | primary `#4b9fda` (blue tinted for 4.5:1), danger `#e87674` (red tinted), success/warning/info Solarized green/yellow/cyan |
| `--app-border-color` / `-strong` | Iris / `rgba(0,0,0,.2)` | `rgba(147,161,161,.2)` / `rgba(131,148,150,.8)` |
| `--app-radius-sm/md/lg` | 6 / 8 / 12 px | 4 / 6 / 8 px |
| `--app-shadow-dialog` | `0 16px 48px -12px rgba(22,21,19,.25)` | `0 16px 48px -12px rgba(0,0,0,.75)` |
| `--app-control-h` | 2.25rem (36px) | 2.25rem |
| `--app-font-weight-semibold` | 600 | 600 |
| `--app-focus-ring` | Iris | `0 0 0 2px #002b36, 0 0 0 4px rgba(42,161,152,.6)` |

Each package remaps the Universal Theme tokens on `body.apex-theme-iris` (§1). Solarized Dark additionally
remaps every Iris token that is declared with a *literal* colour on `:root` (`--ut-region-*`, `--ut-body-nav-*`,
`--ut-field-label-text-color`, `--a-checkbox-*`, `--a-gv-*`, …) because those do not follow the component
tokens — the list is in `sample-themes/solarized-dark/css/tokens.css`.

### 3.3 Package file map (all themes)

| File | Owns |
|---|---|
| `tokens.css` | `--app-*` deltas (html scope) and `--ut-*` / `--a-*` remaps (body scope) |
| `apex/shell.css` | header, side nav (Style B pill), title bar, hero, footer |
| `apex/regions.css` | regions, Cards region atoms, card list, wizard, metric card, content blocks, breadcrumb title |
| `apex/buttons.css` | button geometry, default / hot / primary, button group, `:focus-visible` ring |
| `apex/forms.css` | field atoms, labels, floating labels, focus halo |
| `apex/reports.css` | IRR / IG / classic report atoms, pager, horizontal hairlines, tabular numerals |
| `apex/dialogs.css` | jQuery UI dialog atoms, wizard dialog pages, popup menus |
| `apex/misc.css` | shadows off, badges, tabs, alerts (+ Prism code samples in Solarized Dark) |

Declarative: `application.apx` → `css.fileUrls: #APP_FILES#css/app.css`; navigation menu template option Style B
(applied per default theme by `scripts/apply-theme.sh` from `theme.json`).

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

Recipe profiles are template-time visual patterns. They are copied into each package at generation time, not
loaded from a shared runtime stylesheet. This keeps portable ZIPs independent and lets a theme customize its
rendered profile without changing other packages. Native specimen coverage is registered in
[COMPONENTS.md](COMPONENTS.md#theme-lab-specimen-registry).

Recipe schema v2 also makes the non-palette identity axes explicit. Every new recipe declares `rhythm` (`density`,
`spacing`, `typeScale`), `interaction` (`hover`, `selected`, `motion`), and `responsive` (`strategy`,
`compactControlsAt`, one of `0`, `375`, `768`, or `1024`). Version-1 recipes remain readable and receive the
deterministic compatibility defaults `balanced/technical/balanced`, `none/fill/precise`, and `reflow/768`; the
scaffold always emits version 2 so a generated theme never silently inherits Linen's choices.

| Pattern | Class | Since | Used on |
|---|---|---|---|
| Navigation profile | scoped UT navigation selectors | 2026-09-20 | `shell.css` generated from rail/pill/editorial/minimal |
| Card profile | scoped Cards/region atoms | 2026-09-20 | `regions.css` generated from flat/layered/offset/buoyant |
| Button profile | scoped `.t-Button` atoms/states | 2026-09-20 | `buttons.css` generated from square/rounded/underline/pill |
| Form profile | scoped form atoms/states | 2026-09-20 | `forms.css` generated from dense/comfortable/outlined/soft |
| Report profile | scoped IR/IG/report atoms | 2026-09-20 | `reports.css` generated from ruled/spacious |
| Dialog profile | scoped dialog atoms | 2026-09-20 | `dialogs.css` generated from flat/layered/offset |
