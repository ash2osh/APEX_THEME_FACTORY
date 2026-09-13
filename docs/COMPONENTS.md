# Component Catalog

Registry of reusable application components (spec §36–§38). **Search here before creating a
component.** One row per component; the contract block lives in the component's own section.

Priority reminder (spec §7): existing app component → native APEX → native + CSS → native + Alpine
→ reusable custom component → custom HTML.

## Index

| Component | Kind | CSS | Alpine | Status | Pages |
|---|---|---|---|---|---|
| _(none yet)_ | | | | | |

## Native APEX components used in app 102 (do not rebuild — style them)

Cards, Content Row, Badge, Interactive Report, Interactive Grid, Classic Report, Modal Dialog,
Drawer, Side Navigation (`t-TreeNav`), Navigation Bar, Breadcrumb, Buttons (`t-Button`), Form items.
Reference pages live in app 102 (e.g. 1201 Regions – Standard, 1202 Region – Alert); use them as
the visual baseline for Iris.

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
