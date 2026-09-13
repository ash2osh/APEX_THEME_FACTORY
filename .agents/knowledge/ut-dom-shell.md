# UT 26.1 / Iris DOM — page shell (header, side nav, title bar)

Confidence: HIGH for page 500 (standard page template, left nav), verified 2026-09-13 via Chrome
DevTools `evaluate_script` (computed styles) + `Core.min.css` / `Iris.min.css` grep.

## Structure and token hooks
| Element | Class | Painted by (token) |
|---|---|---|
| top accent strip | `.t-Header::before` | `--ut-header-strip-background-color` (default `--ut-palette-primary`), height `--ut-header-strip-size` (.375rem) |
| header bar | `header.t-Header > .t-Header-branding` | bg `--ut-header-background-color`, text `--ut-header-text-color`, bottom border `--ut-header-border-color`, `min-height: --ut-header-height` |
| logo | `.t-Header-logo > a.t-Header-logo-link` | `--ut-logo-text-color` (inherits) |
| nav-bar buttons | `.t-Header-navBar .t-Button.t-Button--header.t-Button--navBar` | `--a-button-*` atoms set on `.t-Button--header` (text `initial` → inherits header text) |
| menu toggle | `.t-Header-controls .t-Button--headerTree` (`.is-active` when nav open) | same |
| side nav panel | `.t-Body-nav` (sticky, `width: --ut-nav-width`) | bg `--ut-body-nav-background-color`, text `--ut-body-nav-text-color`, right border via inset box-shadow `--ut-body-nav-border-color` |
| tree | `.a-TreeView.t-TreeNav.t-TreeNav--styleA|styleB` | `--a-treeview-*` atoms; Iris sets selected/focused values to `hsla(0,0%,100%,.08)` / `#00688c` |
| tree row | `li.a-TreeView-node.a-TreeView-node--topLevel > .a-TreeView-row` (+ `.is-current--top`, `.is-selected`, `.is-hover`, `.is-focused`) | Iris rules keyed on `.t-TreeNav …`, some with `!important` (hover) |
| tree label | `.a-TreeView-content > a.a-TreeView-label` (+ `.is-current`) | inherits |
| title bar | `.t-Body-title` (sticky) | bg `--ut-body-title-background-color`, shadow `--ut-body-title-box-shadow`, border `--ut-body-title-border-width/-color`, backdrop `--ut-body-title-backdrop-filter` |
| hero (p500 title) | `.t-HeroRegion > .t-HeroRegion-icon + .t-HeroRegion-title (h1, 32px/700)` | Core |
| footer | `footer.t-Footer` | border `--ut-footer-border-color` |

## Body/nav state classes
`js-navExpanded` / `js-navCollapsed` + `js-navCollapsed--hidden` (nav width → 0) or `js-navCollapsed--icons`
(52px). `t-PageBody--hideLeft` / `--hideActions` also present on p500.

## Template options (list template "Side Navigation Menu", from apex_appl_template_options)
Style: `t-TreeNav--classic` | `t-TreeNav--styleA` (default in app 102, flat rows + 4px teal inset bar)
| `t-TreeNav--styleB` (rows with .25rem margins, `border-radius:.25rem`, current pill solid teal).
Collapse Mode: `js-navCollapsed--hidden` | `js-navCollapsed--default`. Also `js-defaultCollapsed`,
`js-addActions`, `js-hideDefaultIcon`. Set in `application.apx → navigationMenu.templateOptions`.

## Gotchas
- `.t-Header` itself is transparent; the colour lives on `.t-Header-branding`.
- Iris paints current/expanded top-level rows `color:#fff` for its dark nav — must be neutralised on a light nav.
- Hover tint on tree rows is `!important` in Iris → override needs `!important`.
- `.t-Body-main{--a-treeview-*}` in Iris targets content treeviews only; the nav is outside `.t-Body-main`.
