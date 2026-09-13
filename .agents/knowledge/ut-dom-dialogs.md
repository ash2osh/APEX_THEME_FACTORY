# UT 26.1 / Iris DOM — modal dialogs and menus

Confidence: HIGH (p1910 → modal page 1912), verified 2026-09-13 via CSSOM walk + computed styles.

## Modal dialog (page-based)
Parent document chrome (jQuery UI, APEX-skinned):
```
div.ui-dialog.ui-dialog--apex.t-Dialog-page--standard[role=dialog][aria-modal]   (overflow:hidden; fixed)
  div.ui-dialog-titlebar > h1.ui-dialog-title + button.ui-dialog-titlebar-close(.ui-button) > span.ui-icon-closethick
  div.ui-dialog-content > iframe
div.ui-widget-overlay.ui-front
```
Iframe body: `t-Dialog-page t-Dialog-page--standard t-PageTemplate--dialog … apex-theme-iris` → `div.t-Dialog > .t-Dialog-header + .t-Dialog-bodyWrapperOut > .t-Dialog-bodyWrapperIn > .t-Dialog-body[role=main] + .t-Dialog-footer`.
The app CSS file loads in the iframe page too (same application), so `.apex-theme-iris` scoping works inside.

Atoms on `:root` (Iris values): `--jui-dialog-border-radius:.25rem`, `--jui-dialog-shadow: 0 1.5rem 3rem -1.5rem rgba(0,0,0,.3),0 0 0 1px rgba(0,0,0,.1)`,
`--jui-dialog-border-width:0`, `--jui-dialog-titlebar-padding-x/y: 1rem/.75rem`, `-titlebar-border-color rgba(0,0,0,.1)`,
`--jui-dialog-title-font-size:1rem`, `-font-weight` (semibold 500), `--jui-dialog-title-close-*` (button atoms), `--jui-dialog-buttonpane-*`,
`--jui-overlay-background-color: rgba(0,0,0,.25)`. Variants: `.ui-dialog--notification`, `.ui-dialog--modern` (handle-only titlebar),
`.t-Dialog--pullOutLeft/Right`, `.t-Drawer--pullOutTop/Bottom` (radius 0 !important).
Menus: `--a-menu-shadow`, `--a-menu-border-radius`, `--a-menu-border-color`, `--a-menu-background-color` on `:root`.
On open, APEX focuses the close button first (shows the focus ring).
