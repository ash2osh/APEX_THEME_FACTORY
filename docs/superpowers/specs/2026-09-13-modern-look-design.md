# Modern look for app 102 ("Quiet product") — design spec

Date: 2026-09-13 · Status: implemented in source (commits aa07754…), verified via DevTools proto on 500/1201/1402/1410/1500/1600/1910 at 1440/1024/768/375; **not imported** to app 102
Governing rules: `docs/AGENT_SPEC.md`, `docs/DESIGN_SYSTEM.md`. Theme style **Iris only**.

## 1. Goal

Give the Universal Theme 26.1 Reference app (app 102, 122 pages) a quieter, more contemporary
admin look — light chrome, hairline borders, flat surfaces, single teal accent for actions — without
changing palette, typeface, page templates, or any native APEX behaviour.

Direction chosen: **Quiet product** (over "Soft elevated" and "Brand-forward").
Scope chosen: **app-wide via one global CSS layer**; per-page `.apx` edits only where a template
option is unavoidable (none planned).

## 2. Non-goals

- No new palette or font: Iris primary `#00688c`, Oracle Sans stay.
- No redefinition of `--ut-*` / `--a-*` on `:root` (Theme Roller's job; banned).
- No replacement of native components (IG, IR, dialogs, items, nav) with custom markup.
- No Alpine components; `alpine.min.js` is not attached in this task.
- No structural redesign of the landing page hero or page templates.
- No import to the live app until the user asks.

## 3. Approach

**Scoped override layer.** All rules live under `body.apex-theme-iris` (present on every page) and
target Universal Theme's component classes, e.g. `.apex-theme-iris .t-Header { … }`. Loaded after
`Iris.min.css`, same specificity family, so rules win without `!important`. Detaching the file
restores Iris exactly.

Rejected: opt-in `.app-*` classes per region (requires editing 122 pages); redefining `--ut-*`
tokens (fights Iris).

Every UT class used is first verified on the running page (DevTools snapshot / `outerHTML`) and
recorded in `.agents/knowledge/ut-dom-<component>.md`.

## 4. Visual system

### Tokens (`static-files/css/foundation/tokens.css`)

| Token | Value | Why |
|---|---|---|
| `--app-radius-sm` / `-md` / `-lg` | `6px` / `8px` / `12px` | Iris radius scale (2/4/8) is too tight for the direction; literal, registered |
| `--app-shadow-dialog` | `0 16px 48px -12px rgba(22,21,19,.25)` | the only shadow in the system; dialogs/menus only |
| `--app-shell-header-h` | `3.5rem` (= `--ut-header-height`) | alias |
| `--app-shell-nav-w` | `15rem` (= `--ut-nav-width`) | alias |
| `--app-surface-chrome` | `var(--ut-component-background-color)` | header + side nav surface (white) |
| `--app-surface-subtle` | `var(--ut-palette-generic-shade)` | table headers, toolbars |
| `--app-accent-shade` | `var(--ut-palette-primary-shade)` | active nav pill, hover tints |
| `--app-border-hairline` | `1px solid var(--ut-component-border-color)` | every border |
| `--app-font-weight-medium/-semibold` | `500` / `600` | Iris semibold resolves to 500 at runtime (added during implementation) |
| `--app-control-h` | `2.25rem` (36px) | inputs, buttons, IG toolbar controls |
| `--app-focus-ring` | `0 0 0 2px var(--ut-component-background-color), 0 0 0 4px var(--ut-focus-outline-color)` | focus everywhere |
| Type scale | `--app-text-xs/sm/md/lg/xl/2xl` = 12/13/14/17/20/24 px | 1.2 ratio on a 14px base |

Existing seed tokens (`--app-color-*`, `--app-surface-*`, `--app-text-*`, `--app-space-*`) stay.

### Components (each = one file under `static-files/css/apex/`)

| File | What changes |
|---|---|
| `shell.css` | Header: white, hairline bottom, dark text, muted nav-bar icons, no top accent strip. Side nav: white, hairline right, muted items, active = teal text on `--app-accent-shade` pill (6px radius, 8px inset), no left colour bar; collapsed/hidden states untouched. Canvas stays `--ut-body-background-color`. Page title bar: transparent, title 24px/600. |
| `regions.css` | `.t-Region`: white, 8px radius, hairline, no shadow; header padding 12×16; title 15px/600; body padding 16. Cards (`.t-Card`, `.t-Cards`): same surface, hover = teal-shade border, no lift. |
| `buttons.css` | `.t-Button`: 36px, 6px radius, 13px/500; hot = teal fill/white text; default = white + hairline; hover = subtle tint; focus = `--app-focus-ring`. |
| `forms.css` | Text/textarea/select: 36px, 6px radius, hairline, teal ring on focus; labels 13px/500 muted; item spacing tightened. |
| `reports.css` | IR / IG / classic: header row `--app-surface-subtle`, 13px/600, row hairlines only (no vertical rules), 40px row height; IG toolbar white + hairline bottom; pagination muted. |
| `dialogs.css` | `.ui-dialog` (APEX modal): 12px radius, `--app-shadow-dialog`, hairline title bar, no gradient. Menus/popups share the shadow. |
| `misc.css` | Badges, alerts, breadcrumbs, tabs: flatten to hairline + tint, radius per scale. |

Load order in `app.css`: tokens → reset → typography → utilities → apex/shell → regions → buttons →
forms → reports → dialogs → misc.

### Wiring

`applications/ut/application.apx`: add
```
cascadingStyleSheets { fileUrls: [ #APP_FILES#css/app.css ] }
```
(exact APEXLang property verified with `apex validate`). `app.css` keeps its `@import` structure;
the sub-files are uploaded under the same relative paths when the user asks for the import.

## 5. Verification

Pages (representative of the 122): 500 Getting Started · 1201 Standard Region · a form page ·
an Interactive Report page · an Interactive Grid page · 1111 Standard Dialog.
Widths: 1440 / 1024 / 768 / 375. Console must stay clean. IG/IR sort, filter, refresh and dialog
open/close re-tested after the reports and dialogs sections.
Accessibility: focus visible on every control, AA contrast for all new text/surface pairs
(teal `#00688c` on white = 6.4:1; muted text `rgba(0,0,0,.65)` on `#fbf9f8` ≥ 4.5:1 — re-measured
at runtime), keyboard nav on side nav and dialogs.

## 6. Delivery

One commit per component file. Baseline screenshots in the scratchpad only. `docs/DESIGN_SYSTEM.md`
§3 updated with the new tokens; DOM findings in `.agents/knowledge/`; anything surprising in
`.agents/findings/pending/`. Final: `apex-design-review` checklist, then hand-off; import is the
user's call.
