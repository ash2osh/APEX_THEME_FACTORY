# Iris `--ut-*` tokens — live computed values

Source: `getComputedStyle(document.documentElement)` on app 102 page 500, APEX 26.1.4,
`/i/themes/theme_42/26.1/css/Iris.min.css`, captured 2026-09-13 via Chrome DevTools MCP.
167 of the 418 `--ut-*` names referenced in Iris.min.css resolve on `:root`; the rest are
component-scoped (set inside selectors) and must be read on the element that uses them.

Confidence: CONFIRMED (runtime). Re-capture after any APEX upgrade.

| Token | Value |
|---|---|
| `--ut-alert-box-shadow` | `0 .125rem .25rem -.125rem rgba(0,0,0,.1)` |
| `--ut-alert-title-font-weight` | `500` |
| `--ut-alternate-heading-font-family` | `Georgia,Times,\` |
| `--ut-badge-border-radius` | `1rem` |
| `--ut-body-actions-background-color` | `#fbf9f8` |
| `--ut-body-actions-text-color` | `rgba(22,21,19,.7)` |
| `--ut-body-actionstoggle-background-color` | `#fbf9f8` |
| `--ut-body-actionstoggle-hover-background-color` | `#e8ddd8` |
| `--ut-body-actions-width` | `12.5rem` |
| `--ut-body-background-color` | `#fbf9f8` |
| `--ut-body-content-max-width` | `100%` |
| `--ut-body-nav-background-color` | `#302d2a` |
| `--ut-body-nav-border-color` | `rgba(0,0,0,.1)` |
| `--ut-body-nav-scrollbar-thumb-background-color` | `hsla(0,0%,100%,.2)` |
| `--ut-body-nav-scrollbar-track-background-color` | `#302d2a` |
| `--ut-body-nav-text-color` | `#fff` |
| `--ut-body-sidebar-background-color` | `#fbf9f8` |
| `--ut-body-sidebar-text-color` | `#161513` |
| `--ut-body-sidebar-width` | `15rem` |
| `--ut-body-text-color` | `#161513` |
| `--ut-body-title-backdrop-filter` | `saturate(180%) blur(8px)` |
| `--ut-body-title-background-color` | `#f1efed` |
| `--ut-body-title-border-width` | `0px` |
| `--ut-body-title-box-shadow` | `0 1px 0 0 rgba(0,0,0,.1)` |
| `--ut-body-title-text-color` | `#161513` |
| `--ut-border-radius` | `.25rem` |
| `--ut-border-radius-lg` | `.5rem` |
| `--ut-border-radius-md` | `.25rem` |
| `--ut-border-radius-sm` | `.125rem` |
| `--ut-breadcrumb-item-active-text-color` | `#161513` |
| `--ut-breadcrumb-item-text-color` | `rgba(22,21,19,.7)` |
| `--ut-breadcrumb-region-spacing` | `.5rem` |
| `--ut-breadcrumb-title-font-weight` | `700` |
| `--ut-button-region-box-shadow` | `0 .125rem .25rem -.125rem rgba(0,0,0,.1)` |
| `--ut-cardlist-box-shadow` | `0 .125rem .25rem -.125rem rgba(0,0,0,.1)` |
| `--ut-checkbox-item-spacing` | `1rem` |
| `--ut-color-scheme` | `light` |
| `--ut-comment-chat-active-background-color` | `rgba(0,0,0,.1)` |
| `--ut-comment-chat-background-color` | `rgba(0,0,0,.05)` |
| `--ut-component-background-color` | `#fff` |
| `--ut-component-badge-background-color` | `rgba(0,0,0,.05)` |
| `--ut-component-badge-border-radius` | `.25rem` |
| `--ut-component-badge-text-color` | `#000` |
| `--ut-component-border-color` | `rgba(0,0,0,.1)` |
| `--ut-component-border-radius` | `0.25rem` |
| `--ut-component-border-width` | `1px` |
| `--ut-component-box-shadow` | `0 1.5rem 3rem -1.5rem rgba(0,0,0,.3)` |
| `--ut-component-highlight-background-color` | `rgba(0,0,0,.025)` |
| `--ut-component-icon-background-color` | `#00688c` |
| `--ut-component-icon-color` | `#fff` |
| `--ut-component-inner-border-color` | `rgba(0,0,0,.05)` |
| `--ut-component-inner-border-width` | `1px` |
| `--ut-component-text-default-color` | `#000` |
| `--ut-component-text-muted-color` | `rgba(0,0,0,.65)` |
| `--ut-component-text-subtitle-color` | `rgba(0,0,0,.85)` |
| `--ut-component-text-title-color` | `#000` |
| `--ut-component-toolbar-background-color` | `rgba(0,0,0,.025)` |
| `--ut-content-block-header-font-weight` | `700` |
| `--ut-field-fl-input-focus-icon-background-color` | `#00688c` |
| `--ut-field-fl-input-focus-icon-color` | `#fff` |
| `--ut-field-input-focus-icon-color` | `#00688c` |
| `--ut-field-label-text-color` | `#161513` |
| `--ut-focus-outline-color` | `#00688c` |
| `--ut-footer-background-color` | `transparent` |
| `--ut-footer-border-color` | `rgba(22,21,19,.12)` |
| `--ut-footer-item-spacing` | `.75rem` |
| `--ut-header-background-color` | `#302d2a` |
| `--ut-header-border-color` | `hsla(0,0%,100%,.12)` |
| `--ut-header-box-shadow` | `none` |
| `--ut-header-height` | `3.5rem` |
| `--ut-header-menubar-background-color` | `#302d2a` |
| `--ut-header-menubar-item-border-color` | `hsla(0,0%,100%,.1)` |
| `--ut-header-menubar-item-current-background-color` | `hsla(0,0%,100%,.08)` |
| `--ut-header-menubar-item-current-text-color` | `#fff` |
| `--ut-header-menubar-item-hover-background-color` | `hsla(0,0%,100%,.08)` |
| `--ut-header-menubar-item-hover-text-color` | `#fff` |
| `--ut-header-menubar-item-split-border-color` | `hsla(0,0%,100%,.1)` |
| `--ut-header-menubar-item-split-icon-color` | `#fff` |
| `--ut-header-menubar-item-text-color` | `#fff` |
| `--ut-header-text-color` | `#fff` |
| `--ut-hero-region-title-font-weight` | `700` |
| `--ut-hero-region-title-text-color` | `#161513` |
| `--ut-linkslist-arrow-color` | `rgba(0,0,0,.2)` |
| `--ut-link-text-color` | `#0e7295` |
| `--ut-login-page-background-color` | `#e6e6e6` |
| `--ut-login-region-background-color` | `hsla(0,0%,100%,.65)` |
| `--ut-login-region-box-shadow` | `0 1.5rem 3rem -1.5rem rgba(0,0,0,.3)` |
| `--ut-login-region-filter` | `blur(4px)` |
| `--ut-logo-font-weight` | `700` |
| `--ut-logo-img-spacing` | `.5rem` |
| `--ut-navbar-button-badge-background-color` | `rgba(0,0,0,.3)` |
| `--ut-navbar-button-badge-border-radius` | `1rem` |
| `--ut-navtabs-background-color` | `#302d2a` |
| `--ut-navtabs-item-active-background-color` | `hsla(0,0%,100%,.08)` |
| `--ut-navtabs-item-active-highlight-color` | `#00688c` |
| `--ut-navtabs-item-border-color` | `hsla(0,0%,100%,.1)` |
| `--ut-navtabs-item-border-width` | `1px` |
| `--ut-navtabs-item-highlight-color` | `transparent` |
| `--ut-navtabs-item-highlight-width` | `0rem` |
| `--ut-navtabs-item-hover-background-color` | `hsla(0,0%,100%,.08)` |
| `--ut-navtabs-text-color` | `#fff` |
| `--ut-nav-width` | `15rem` |
| `--ut-palette-danger` | `#b3311f` |
| `--ut-palette-danger-contrast` | `#fff` |
| `--ut-palette-danger-shade` | `#ffebe8` |
| `--ut-palette-danger-text` | `#b3311f` |
| `--ut-palette-generic` | `#f2f2f2` |
| `--ut-palette-generic-contrast` | `#000` |
| `--ut-palette-generic-shade` | `#f9f9f9` |
| `--ut-palette-generic-text` | `#000` |
| `--ut-palette-info` | `#227e9e` |
| `--ut-palette-info-contrast` | `#fff` |
| `--ut-palette-info-shade` | `#e4f1f7` |
| `--ut-palette-info-text` | `#227e9e` |
| `--ut-palette-primary` | `#00688c` |
| `--ut-palette-primary-alt` | `#227e9e` |
| `--ut-palette-primary-alt-contrast` | `#fff` |
| `--ut-palette-primary-alt-shade` | `#e4f1f7` |
| `--ut-palette-primary-alt-text` | `#227e9e` |
| `--ut-palette-primary-contrast` | `#fff` |
| `--ut-palette-primary-shade` | `#e4f1f7` |
| `--ut-palette-primary-text` | `#00688c` |
| `--ut-palette-success` | `#436b1d` |
| `--ut-palette-success-contrast` | `#fff` |
| `--ut-palette-success-shade` | `#e4f5d3` |
| `--ut-palette-success-text` | `#436b1d` |
| `--ut-palette-warning` | `#8f520a` |
| `--ut-palette-warning-contrast` | `#fff` |
| `--ut-palette-warning-shade` | `#fceddc` |
| `--ut-palette-warning-text` | `#8f520a` |
| `--ut-region-background-color` | `#fff` |
| `--ut-region-body-padding-x` | `1rem` |
| `--ut-region-body-padding-y` | `1rem` |
| `--ut-region-border-width` | `1px` |
| `--ut-region-box-shadow` | `0 .125rem .25rem -.125rem rgba(0,0,0,.1)` |
| `--ut-region-buttons-padding-x` | `.75rem` |
| `--ut-region-buttons-padding-y` | `.5rem` |
| `--ut-region-font-size` | `.875rem` |
| `--ut-region-header-background-color` | `#fff` |
| `--ut-region-header-border-color` | `rgba(0,0,0,.075)` |
| `--ut-region-header-text-color` | `#161513` |
| `--ut-region-line-height` | `1.25rem` |
| `--ut-region-margin` | `1rem` |
| `--ut-region-text-color` | `#161513` |
| `--ut-report-cell-alt-background-color` | `rgba(0,0,0,.05)` |
| `--ut-report-cell-border-color` | `#e6e6e6` |
| `--ut-report-cell-hover-background-color` | `#fafafa` |
| `--ut-report-header-background-color` | `rgba(0,0,0,.025)` |
| `--ut-resultsregion-background-color` | `#fff` |
| `--ut-resultsregion-search-background-color` | `rgba(0,0,0,.025)` |
| `--ut-resultsregion-search-border-color` | `rgba(0,0,0,.1)` |
| `--ut-shadow-lg` | `0 1.5rem 3rem -1.5rem rgba(0,0,0,.3)` |
| `--ut-shadow-md` | `0 .75rem 1.5rem -.75rem rgba(0,0,0,.3)` |
| `--ut-shadow-sm` | `0 .125rem .25rem -.125rem rgba(0,0,0,.1)` |
| `--ut-smart-filter-max-width` | `30rem` |
| `--ut-tabs-item-active-font-weight` | `700` |
| `--ut-tabs-item-active-text-color` | `#0e7295` |
| `--ut-tabs-item-hint-highlight-color` | `rgba(0,0,0,.2)` |
| `--ut-tabs-item-hint-highlight-width` | `.25rem` |
| `--ut-tabs-item-text-color` | `#000` |
| `--ut-treeview-badge-background-color` | `#00688c` |
| `--ut-treeview-badge-text-color` | `#fff` |
| `--ut-wizard-header-background-color` | `#fafafa` |
| `--ut-wp-marker-color` | `#d9d9d9` |
| `--ut-wp-track-color` | `#d9d9d9` |
| `--ut-xs-field-input-font-size` | `1rem` |
| `--ut-xs-field-input-line-height` | `1.25rem` |
