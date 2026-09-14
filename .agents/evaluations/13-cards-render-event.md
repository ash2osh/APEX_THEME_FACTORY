# Evaluation: Cards Render Event
Given: theme42 builds `.t-NavigationBar-menu` widgets on `apexreadyend` and then triggers `theme42ready` on
**window**; `menu('option','items')` can be rebuilt afterwards, and the widget supports
`{type:'radioGroup', get, set, choices}` (renders `menuitemradio` + `aria-checked`). Synthetic `element.click()`
does not activate an item. On pages without a navigation bar, `$('#missing').menu('option','items')` returns the
empty jQuery set — no error — so `items.forEach` throws inside every dialog page and interrupts theme42's init
chain. Cards regions render after DOM-ready; `apex.region(id).refresh()` fires no `apexafterrefresh`; the widget's
`tablemodelviewpagechange` bubbles to `document` after each render.
Expected: "mark the active card in a Cards region after load" → hook `tablemodelviewpagechange` (or the
region's own events), guard any `menu('option','items')` access for an empty jQuery set, and drive radio-style
menu items via the widget's `set`/`choices` API rather than a synthetic `.click()`.
Failure: a DOM-ready hook (`apex.jQuery(fn)`), `apexafterrefresh` used as the Cards render signal, or an
unguarded `menu('option','items').forEach`.
Skills under test: apex-alpine-lifecycle, apex-alpine-components, chrome-devtools-mcp.
