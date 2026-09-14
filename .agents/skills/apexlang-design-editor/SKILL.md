---
name: apexlang-design-editor
description: Use when a design change needs a declarative APEX change — CSS Classes, Static ID, region/item/button template, template options, grid layout, region position, dynamic action, page CSS/JS file references — and must be edited in applications/ut/*.apx
---

# apexlang-design-editor

Files: `applications/ut/pages/pNNNNN-<alias>.apx`, `application.apx`, `shared-components/**`.
Grammar/compiler truth: global `apex` skill (`node tools/query-valid-props.mjs`). Round-trip: `apexlang-roundtrip`.

## Core principle
Smallest correct declarative change, then validate (spec §40).

## Where design properties live (find with grep before editing)
| Need | APEXLang property (search key) |
|---|---|
| Hook for scoped CSS | `cssClasses:` on region/item/button; Static ID = `advanced { htmlDomId: … }` (`staticId` is the internal component id, not the DOM id) |
| Structural variant | `templateOptions: [ … ]` (values from `shared-components/themes/universal-theme/template-option-groups.apx`) |
| Template swap | `template: @/standard` etc. |
| Layout | `layout { … }` — `columnSpan`, `newRow`, `startNewGrid` |
| Page-level CSS/JS | `css { fileUrls / inline }`, `javaScript { fileUrls / executeWhenPageLoads / functionAndGlobalVariableDeclaration }` |
| App-level CSS/JS | `application.apx` → top-level `css { fileUrls }` / `javaScript { fileUrls }` blocks |
| Behaviour | `dynamicAction … { when { event … } actions [ … ] }` |

## Procedure
1. `grep -n "<static id or region name>" applications/ut/pages/*.apx` to find the block.
2. Edit only that block; keep indentation, ordering and comments. LF endings.
3. If unsure a property/value is legal → query compiler truth; templates are examples, not oracles.
4. `scripts/apex-validate.sh`. New warning = your change.
5. Import only when the user asks; then verify runtime with `chrome-devtools-mcp`.

## Common mistakes
- Adding a CSS class in Page Designer and forgetting to export/update `.apx` (source drift).
- Reformatting a whole page file.
- Guessing template option names — read `template-option-groups.apx`.
