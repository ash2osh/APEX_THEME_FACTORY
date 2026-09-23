# Pitfalls §2 — APEX JavaScript and widgets

Part of the [pitfalls index](../pitfalls.md); entry numbers are stable and cited as `pitfalls §2.N`.

## 2. APEX JavaScript and widgets

### 2.1 Navigation-bar menus are built by theme42 on `apexreadyend`; `theme42ready` fires on **window**
- `apex.theme42` runs its init map (`misc()` → `.t-NavigationBar-menu`.menu()) on `apexreadyend`, then
  `$(window).trigger('theme42ready')`. Hook `apex.jQuery(window).on('theme42ready', …)` to post-process menus;
  `document` does not receive it.

### 2.2 The `menu` widget accepts a `radioGroup` item
- `items: [{type:'radioGroup', get(){…}, set(v){…}, choices:[{label,value}]}]` renders `role=menuitemradio` +
  `aria-checked` + a check mark — the right primitive for a "choose one" nav-bar menu. Rebuild with
  `menu('option','items', […])`. `data-current="true"` on the source `<li>` becomes `current: true`.
- Synthetic `element.click()` on a rendered `menuitemradio` **does not** trigger the widget (it listens to
  mouse events); test with a real click (`chrome-devtools click uid`).

### 2.3 Pages without a navigation bar: `$()` chains don't throw
- `$('#missing').menu('option','items')` on an empty jQuery set returns the set, not an error. `try/catch` is
  not a guard — check `.length` and `Array.isArray(items)`. This produced `items.forEach is not a function`
  inside every dialog page (which has no nav bar) and broke the rest of theme42's init.

### 2.4 Cards regions render after DOM-ready and don't fire `apexafterrefresh` on `refresh()`
- The Cards region (`tableModelView` widget) loads data asynchronously; `apex.jQuery(fn)` runs before any card
  exists, and `apex.region(id).refresh()` did **not** emit `apexafterrefresh` (26.1.4). What fires, after each
  render and bubbling to `document`, is `tablemodelviewpagechange` (jQuery UI lower-cases
  `widgetEventPrefix + event`). Delegate: `$(document).on('tablemodelviewpagechange', '#static_id', fn)`.

### 2.5 Card > CSS Classes supports `&COLUMN.` substitution and lands on `.a-CardView`
- `card { cssClasses: [ app-theme-card &CARD_CLASS. ] }` → `<div class="a-CardView … app-theme-card app-theme-card--linen">`.

### 2.6 Alpine.js being registered as a static file doesn't mean it's loaded
- **Symptom (found 2026-09-15):** `static-files/js/app.js`'s own header comment claims "Alpine.js is loaded
  once (application-level file URL)", and `static-files/js/vendor/README.md` documents the load order — but
  `applications/ut/application.apx`'s `javaScript.fileUrls` never actually referenced `js/vendor/alpine.min.js`,
  only `demo.js`, Prism, and `js/app.js`. `static-files.apx` had it registered as an uploadable static file,
  which is a different thing from a page emitting a `<script>` tag for it. No `x-data`/`Alpine.data()` anywhere
  in the app could ever have run.
- **Fix:** add `#APP_FILES#js/vendor/alpine.min.js` to `application.apx`'s `javaScript.fileUrls`, after
  `js/app.js` and after any `js/components/*.js` entries (components hook `alpine:init`, which must be
  registered *before* Alpine's own CDN-build auto-start — see the vendor README's load-order note).
- **Check this again** whenever adding the first component file to a fresh checkout, or after any bulk
  `applications/ut/application.apx` regeneration — nothing currently guards against this silently regressing.

### 2.7 A Dynamic Content region that prints with `sys.htp.p` cannot be refreshed
- **Symptom (found 2026-09-16, page 409):** `apex.region(id).refresh()` on a `type: dynamicContent` region
  fires `apexbeforerefresh` and one `POST wwv_flow.ajax` (HTTP 200) — then nothing: `apexafterrefresh` never
  fires, the DOM is never swapped, the console stays clean. jQuery's `ajaxError` shows the real cause:
  `SyntaxError: Unexpected token '<', "<div x-dat"... is not valid JSON`.
- **Why:** in 26.1.4 the region renders as `<a-dynamic-content region-id=… ajax-identifier=…>`, a custom
  element whose refresh is `apex.server.plugin(…, { success: e => { s.innerHTML = e.regions[0].result } })`.
  `result` is the **return value** of the region's PL/SQL function body. `htp.p` output instead goes to the
  response stream *ahead of* the JSON envelope, so the body is `<html…>{json}`: the parse fails, `success`
  never runs, and `"result":null` is what the envelope actually carries.
- **Fix:** `return '<div …>' || … ;` from the function body (the APEXLang attribute is literally
  `plsqlFunctionBody`). Never `sys.htp.p`.
- **Note:** the stock UT demo page 1908 (*Dynamic Content Region*) has the same defect — it uses `htp.p` and
  fails identically on `apex.region('Demo1').refresh()`; it simply ships no refresh trigger. Don't copy it.
- Page items placed in the region's `regionBody` slot render as **siblings** of `<a-dynamic-content>`, so a
  refresh does not replace them: client-side item state (and an Alpine component that re-reads it in `init()`)
  survives the swap.
- **Confirmed on the fixed page 2026-09-17** (page 409 imported): three real clicks give `apexbeforerefresh` 3
  / `apexafterrefresh` 3, a new root node each time with the old one disconnected, one component instance and
  one click handler after every swap, and the envelope carrying the markup inside `"result"`. The `return`
  form is the whole fix — no JavaScript change was needed.
