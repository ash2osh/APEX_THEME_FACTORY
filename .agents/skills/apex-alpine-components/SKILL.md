---
name: apex-alpine-components
description: Use when building or modifying a custom interactive client-side component in this APEX app (picker, panel, stepper, menu, filter UI, disclosure, custom selector) with Alpine.js, or when about to write a large inline x-data
---

# apex-alpine-components

Files: `static-files/js/components/<name>.js` + `static-files/css/components/<name>.css`; registry `docs/COMPONENTS.md`.

## Core principle
Alpine supplements APEX (spec §1). `Alpine.data()` per component; APEX item stays authoritative; business logic stays in PL/SQL.

## Shape of a component
```js
// static-files/js/components/employee-picker.js
document.addEventListener('alpine:init', () => {
  Alpine.data('employeePicker', ({ item, process = 'SEARCH_EMPLOYEES' }) => ({
    open: false, query: '', results: [], loading: false,
    init() { this.$watch('query', () => this.search()); },
    async search() { /* apex.server.process(process, { x01: this.query }) */ },
    select(row) { apex.item(item).setValue(row.id, row.name); this.$dispatch('employee-selected', row); this.open = false; },
  }));
});
```
Markup (in a Static Content region with `cssClasses: app-employee-picker`):
`<div x-data="employeePicker({ item: 'P20_EMPLOYEE_ID' })" x-cloak> … </div>`

## State levels (spec §29)
local → `Alpine.data`; shared across components → `Alpine.store` (only if truly shared); persistent → APEX items / session state / DB.

## Requirements per component
- Contract in `docs/COMPONENTS.md` before the code.
- Keyboard: Tab/Enter/Escape/arrow handling; visible focus; ARIA roles for custom widgets (`apex-accessibility`).
- Works after region refresh (`apex-alpine-lifecycle`).
- Server calls through `apex.server.process` (`apex-alpine-server-integration`).
- No Alpine plugins unless justified in the contract (spec §68). `[x-cloak]{display:none!important}` is in `foundation/reset.css`.

## Common mistakes
- 100-line inline `x-data`.
- Keeping the selected value only in Alpine state (must `apex.item(...).setValue`).
- A Dynamic Action and an Alpine handler both doing the same thing (spec §71).
