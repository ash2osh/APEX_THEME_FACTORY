---
name: apex-template-options
description: Use when a design difference is structural (hide header, remove padding, stretch, sticky, collapsible, hero, card layout, button size) and might be a Universal Theme template option rather than CSS
---

# apex-template-options

Source of truth for names: `applications/ut/shared-components/themes/universal-theme/template-option-groups.apx` and each template's options in the theme export. Set them in APEXLang `templateOptions: [ … ]` (`apexlang-design-editor`).

## Core principle
If Universal Theme has a declarative switch for it, use the switch (spec §25). CSS is for appearance the switch doesn't cover.

## Decide
```text
Is the difference about layout/structure/behaviour (header shown, padding, stretch, position, size, style variant)?
  yes → grep template-option-groups.apx for the concept → set templateOptions → validate → verify
  no  → apex-css-design-system
```

## Typical structural options (verify names in the export before use)
Region: header visibility, body padding, stretch/remove borders, hero/card style variants, scroll body, accent.
Buttons: size, style (simple/display-as-link), stretch, spacing.
Items: label position, size, stretch.
Page: nav collapsed, sticky header, content max width.

## Iris caveat
Theme-style-level appearance (colors) is Iris + app CSS, never Theme Roller. Template options never change the theme style.

## Common mistakes
- Writing `.app-x .t-Region-header { display:none }` when "Hide Header" exists.
- Using template options for colour/branding (that's tokens/CSS).
