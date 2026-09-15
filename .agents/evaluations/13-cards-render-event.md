# Evaluation: Cards Render Event
Given: theme42 builds `.t-NavigationBar-menu` widgets on `apexreadyend` and then triggers `theme42ready` on
**window**; `menu('option','items')` can be rebuilt afterwards, and the widget supports
`{type:'radioGroup', get, set, choices}` (renders `menuitemradio` + `aria-checked`). Synthetic `element.click()`
does not activate an item. On pages without a navigation bar, `$('#missing').menu('option','items')` returns the
empty jQuery set — no error — so `items.forEach` throws inside every dialog page and interrupts theme42's init
chain. Cards regions render after DOM-ready; `apex.region(id).refresh()` fires no `apexafterrefresh`; the widget's
`tablemodelviewpagechange` bubbles to `document` after each render.
Expected: "mark the active card in a Cards region after load" → hook `tablemodelviewpagechange` (or the
region's own events).
Failure: a DOM-ready hook (`apex.jQuery(fn)`), or `apexafterrefresh` used as the Cards render signal.
Skills under test: apex-alpine-lifecycle, apex-alpine-components, chrome-devtools-mcp.

Note (2026-09-15, after PR #4 review, P2): this scenario's task only exercises the Cards-render-event half of
the underlying finding (`2026-09-14-apex-widget-events.md`). The finding also documents two navigation-bar
menu regressions — the empty-jQuery-set guard on `menu('option','items')` for pages without a nav bar, and
driving radio-style menu items via `set`/`choices` instead of a synthetic `.click()` — but no run of this
scenario has ever touched menu code, since the task only asks about the Cards region. Do not treat a PASS here
as evidence for those two menu-related corrections; a separate task exercising a page with and one without a
navigation bar is needed to test them.
