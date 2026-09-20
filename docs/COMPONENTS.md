# Component Catalog

Registry of reusable application components (spec §36–§38). **Search here before creating a
component.** One row per component; the contract block lives in the component's own section.

Priority reminder (spec §7): existing app component → native APEX → native + CSS → native + Alpine
→ reusable custom component → custom HTML.

## Index

| Component | Kind | CSS | Alpine | Status | Pages |
|---|---|---|---|---|---|
| themeFactoryDisclosure | Alpine Disclosure | n/a | `static-files/js/components/themeFactoryDisclosure.js` | in-use | 409 |

## Reusable Components

### themeFactoryDisclosure

```text
COMPONENT       themeFactoryDisclosure
PURPOSE         Refresh-resilient disclosure widget demonstrating Alpine and APEX item state synchronization across region refreshes
CSS             n/a (uses Universal Theme button/region styling)
ALPINE          themeFactoryDisclosure(itemName)  static-files/js/components/themeFactoryDisclosure.js
APEX INPUT      itemName (e.g. P409_DISCLOSURE_OPEN, Y/N string value)
EVENTS          none
SERVER PROCESS  none
TEMPLATE OPTS   #DEFAULT#
RESPONSIVE      inherits container width
ACCESSIBILITY   Native button with type="button", x-bind:aria-expanded="open.toString()", aria-controls="theme_factory_disclosure_panel"; keyboard navigable (Enter/Space)
REFRESH         Refresh-safe: component owns no global refresh listener; Alpine reinitializes replacement markup via mutation lifecycle, reading initial state from APEX item
STATUS          in-use
```

#### Page 409 Verification Steps
1. Navigate to Page 409 (`Theme Factory Lifecycle` under Design).
2. Confirm disclosure button is rendered, initial item `P409_DISCLOSURE_OPEN` is `N`, and panel is hidden with `x-cloak`.
3. Activate toggle with Enter/Space or click: panel appears, `aria-expanded` transitions to `"true"`, and `P409_DISCLOSURE_OPEN` synchronizes to `Y`.
4. Click native `REFRESH_FIXTURE` button (`apex.region('theme_factory_disclosure_region').refresh()`):
   Dynamic content region refreshes via APEX AJAX; newly inserted DOM nodes initialize through Alpine's DOM mutation observer, executing `init()` which reads `P409_DISCLOSURE_OPEN === 'Y'` to restore open state without duplicate listeners or errors.
5. Click toggle to close: panel hides, item synchronizes to `N`. Refresh region: panel correctly remains closed.

## Native APEX components used in app 102 (do not rebuild — style them)

Cards, Content Row, Badge, Interactive Report, Interactive Grid, Classic Report, Modal Dialog,
Drawer, Side Navigation (`t-TreeNav`), Navigation Bar, Breadcrumb, Buttons (`t-Button`), Form items.
Reference pages live in app 102 (e.g. 1201 Regions – Standard, 1202 Region – Alert); use them as
the visual baseline for Iris.

## Theme Lab specimen registry

Page 406 is a consolidated native-component test surface. These groups are stable capture/audit targets; add a
native specimen here before expanding one-off browser page lists.

| Static ID | Native specimens covered |
|---|---|
| `theme_lab_typography` | Arabic/Latin samples, headings, links, all declared font weights, Font APEX isolation |
| `theme_lab_surfaces` | page/chrome/card/subtle surfaces, borders, semantic status colours |
| `theme_lab_buttons` | default, hot, primary, icon, disabled, hover and focus-visible states |
| `theme_lab_forms` | text/select/date/Popup LOV/radio/checkbox, required validation and error states |
| `theme_lab_cards` | Cards and content-row density, selection, badges, actions |
| `theme_lab_ir` / `theme_lab_ig` | IR and IG toolbars, grids, paging, selected/edit/error states |
| `theme_lab_calendar` / `theme_lab_chart` | calendar states and JET SVG chart text/tokens |
| `theme_lab_overlays` | menus, date picker, Popup LOV, modal dialog, drawer and focus containment |

## Template-time component profiles

Profiles live in `theme-templates/components/*.css.tmpl` and are copied into a package when it is created or
regenerated. They are not shared runtime CSS: the package owns the rendered selectors and can diverge afterward.

| Recipe key | Profiles | Rendered owner |
|---|---|---|
| `navigation` | rail, pill, editorial, minimal | `css/apex/shell.css` |
| `cards` | flat, layered, offset, buoyant | `css/apex/regions.css` |
| `buttons` | square, rounded, underline, pill | `css/apex/buttons.css` |
| `forms` | dense, comfortable, outlined, soft | `css/apex/forms.css` |
| `reports` | ruled, spacious | `css/apex/reports.css` |
| `dialogs` | flat, layered, offset | `css/apex/dialogs.css` |

## Contract template

```text
COMPONENT       <name>
PURPOSE         <one sentence>
CSS             .app-<name>                     static-files/css/components/<name>.css
ALPINE          <camelCaseName>                 static-files/js/components/<name>.js
APEX INPUT      <page item(s) it reads/writes>
EVENTS          <custom events dispatched>
SERVER PROCESS  <ajax callback / process names>
TEMPLATE OPTS   <UT template options relied on>
RESPONSIVE      <behaviour per breakpoint>
ACCESSIBILITY   <keyboard, ARIA, focus>
REFRESH         <behaviour after apexafterrefresh>
STATUS          draft | in-use | promoted
```

## Promotion log

| Date | Component | From page | Reason |
|---|---|---|---|
