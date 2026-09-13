# UT 26.1 / Iris DOM — regions, cards, content blocks, breadcrumb title

Confidence: HIGH (p1201 Standard Region, p500), verified 2026-09-13 via DevTools + Core/Iris grep.

## Standard region
```
div.t-Region[.t-Region--showIcon|--hideShow|--noUI|--noPadding|--scrollBody|.is-collapsed|.is-expanded|.a-Collapsible]#<static_id>[role=region]
  div.t-Region-header
    div.t-Region-headerItems.t-Region-headerItems--title  (padding: --ut-region-header-padding-y/-x, default .75rem)
      span.t-Region-headerIcon > span.t-Icon.fa.fa-*
      h2.t-Region-title (font: inherit from .t-Region-header → 16px/500 in Iris)
    div.t-Region-headerItems.t-Region-headerItems--buttons
  div.t-Region-bodyWrap
    div.t-Region-buttons.t-Region-buttons--top > .t-Region-buttons-left/-right
    div.t-Region-body (padding --ut-region-body-padding-y/-x, 1rem)
    div.t-Region-buttons.t-Region-buttons--bottom
```
Tokens consumed by Core on `.t-Region`: `--ut-region-background-color`, `-border-color`, `-border-radius`
(fallback `--ut-component-border-radius`), `-border-width`, `-box-shadow` (Iris: `--ut-shadow-sm`),
`-text-color`, `-margin`; on `.t-Region-header`: `--ut-region-header-background-color`,
`-header-border-color` (Iris `rgba(0,0,0,.075)`), `-header-border-width`. `.t-Region--noUI` drops bg/border/shadow.

## Cards list (`t-Cards`)
`ul.t-Cards[.t-Cards--featured|--basic|--compact|--displayIcons|--3cols|--hideBody|--iconsRounded|--animColorFill]
 > li.t-Cards-item > div.t-Card > a.t-Card-wrap > .t-Card-icon(.u-color.u-color-N) + .t-Card-titleWrap > h3.t-Card-title + .t-Card-body`
Tokens on `.t-Card-wrap`: `--ut-cardlist-background-color`, `-wrap-border-color`, `-border-radius`, `-wrap-border-width`, `-box-shadow`.

## Content block
`div.t-ContentBlock.t-ContentBlock--h1|h2|h3[.js-headingLevel-N] > .t-ContentBlock-header > h*.t-ContentBlock-title + .t-ContentBlock-body`
Heading size per level is a token set on the modifier class: `--ut-content-block-header-font-size` (2 / 1.5 / 1.25rem;
mobile ≤639px: 1.5 / 1.25 / 1rem), weight `--ut-content-block-header-font-weight` (Iris: bold 700).

## Breadcrumb as page title
`nav.t-BreadcrumbRegion.t-BreadcrumbRegion--useBreadcrumbTitle > ul.t-Breadcrumb > li.t-Breadcrumb-item(:last-child = title)`
Title font from `--ut-breadcrumb-title-font-size` (2rem) / `-line-height` (3rem) / `-font-weight` (Iris 700), read on
`.t-Body-title` scope. Trail items: `--ut-breadcrumb-item-text-color`.

## Weights
`--a-base-font-weight-semibold` = **500** at runtime under Iris (Core says 600). Oracle Sans provides 100–900.
