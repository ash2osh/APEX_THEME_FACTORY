---
name: apex-alpine-lifecycle
description: Use when an Alpine component lives inside a refreshable APEX region, dialog, IG/IR, or cascading LOV, or when a component stops working / duplicates handlers after refresh, or when tempted to call Alpine.start() again
---

# apex-alpine-lifecycle

## Core principle
APEX replaces DOM subtrees; Alpine initialises new subtrees automatically via MutationObserver. Never call `Alpine.start()` twice (spec §33). Bind lifecycle to APEX events, not polling (spec §34).

## Before attaching behaviour (spec §72)
1. Which region owns the element? (`chrome-devtools-mcp`: `el.closest('.t-Region').id`)
2. Is that node replaced on refresh? Test: `apex.region(id).refresh()` then check `el.isConnected`.
3. Which event signals completion? `apexafterrefresh` on the region; `apexafterclosedialog` for dialogs; `apexpagesubmit` before submit.

## Patterns
| Situation | Do |
|---|---|
| Component markup inside refreshed region | Keep it in the region; Alpine re-inits the new DOM. Re-read APEX item in `init()`. |
| Component outside, listens to region | `apex.jQuery('#region_id').on('apexafterrefresh', () => this.reload())` in `init()`, remove in `destroy()`. |
| Dialog returns a value | `apexafterclosedialog` handler reads `event.data`, sets APEX item, updates Alpine state. |
| IG/IR model changes | Use the IG/IR widget APIs (`interactiveGrid('getViews')`) not DOM scraping. |

## Verification (mandatory)
Refresh the region via DA and via `apex.region(id).refresh()`; interact; check console for `Alpine Expression Error`; ensure handler counts don't grow (`getEventListeners` in DevTools or a counter).

## Common mistakes
- `document.addEventListener` inside `init()` without cleanup → duplicates after each refresh.
- Caching element refs in a store across refreshes.
- Relying on `DOMContentLoaded` for components rendered later.
