---
name: apex-component-selection
description: Use when deciding what APEX component a design element should become (table, KPI, card, dialog, side panel, status, avatar, stepper, filter) before implementing, or when tempted to build custom HTML/Alpine for something APEX already provides
---

# apex-component-selection

## Core principle
Every visual element gets a semantic mapping first; appearance comes second (spec §6–§8).

## Priority (spec §7)
1 existing app component (`docs/COMPONENTS.md`) → 2 native APEX → 3 native + existing CSS → 4 native + new `.app-*` class → 5 native + Alpine → 6 reusable custom (CSS) → 7 reusable custom (CSS+Alpine) → 8 custom HTML.

## Mapping table
| Design element | APEX component |
|---|---|
| KPI / stat tile | Cards region (or promoted `app-metric`) |
| Data table (read) | Interactive Report / Classic Report |
| Editable table | Interactive Grid |
| Form | native items in a Form region |
| Search | native search / IR search bar |
| Modal | Modal Dialog page |
| Side panel | Drawer page |
| Status pill | Badge template component |
| Avatar | Content Row / Cards initials |
| Nav / breadcrumbs | APEX navigation / breadcrumb |
| Grouped content | Region (Standard / Collapsible / Tabs) |
| Contextual actions | Buttons in region positions |
| Workflow state | native display + Badge |

## Preservation rule (spec §8)
Never replace IG, IR, native items, Select List, Popup LOV, validations, dialogs, page submit, forms, navigation, standard buttons to mimic a design. Style them (`apex-css-design-system`).

## Before choosing custom
- Search `docs/COMPONENTS.md` and `static-files/css/components/`.
- Check app 102 reference pages (1201 Regions, 1202 Alert, 1100 Pages) for a native look that is close.
- Write the component contract (COMPONENTS.md template) before code.
