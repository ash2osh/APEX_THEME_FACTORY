---
name: apex-alpine-server-integration
description: Use when an Alpine component must read or write APEX page items, call an Ajax Callback or page process, refresh a region, open/close a dialog, or submit the page — bridging Alpine to APEX JavaScript APIs
---

# apex-alpine-server-integration

## Core principle
APEX JavaScript APIs are the bridge (spec §1, §30–§31). No raw `fetch()` to APEX endpoints; no business logic in JS (spec §70).

## API map
| Need | API |
|---|---|
| Read/write item | `apex.item('P20_X').getValue()` / `.setValue(v, display, suppressChange)` |
| Server call | `apex.server.process('NAME', { x01, pageItems: '#P20_X' }, { dataType: 'json', loadingIndicator })` → returns a promise |
| Refresh region | `apex.region('static_id').refresh()` |
| Open dialog | navigate via a button/DA with a prepared URL, or `apex.navigation.dialog(url, {…})` |
| Close dialog with value | `apex.navigation.dialog.close(true, { id: 1 })` |
| Submit | `apex.page.submit({ request: 'SAVE', validate: true })` |
| Messages | `apex.message.showErrors([...])` / `apex.message.showPageSuccess(...)` |
| Events | `apex.jQuery(el).on('apexafterrefresh', …)` |

The optional adapter (`static-files/js/apex/{items,server,regions,events}.js`, namespace `App.apex.*`) is a thin wrapper for consistency only (spec §66); add functions there only when two components need the same call.

## Ajax Callback process (PL/SQL side)
Declared in APEXLang as an `ajaxCallback` process on the page or app; returns JSON via `apex_json`. Authorization and validation happen there, not in Alpine.

## Common mistakes
- Trusting client state for authorization.
- Hidden copy of an item value in Alpine that drifts from session state.
- Calling `apex.server.process` on every keystroke without debounce.
