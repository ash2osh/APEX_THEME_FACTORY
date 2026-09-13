# UT 26.1 / Iris DOM — buttons and form items

Confidence: HIGH (p1500 Buttons, p1600 Forms), verified 2026-09-13 via DevTools computed custom properties.

## Where the atoms live (this decides the override technique)
- **Base** `--a-button-*` and `--a-field-*` atoms are declared on `:root` by Core/Iris
  (e.g. `--a-button-background-color: rgba(22,21,19,.08)`, `--a-button-padding-y: .5rem`,
  `--a-button-font-size: .75rem`, `--a-button-border-radius: .25rem`, `--a-field-input-border-color: rgba(22,21,19,.5)`,
  `--a-field-input-padding-y/x: .25rem`, `--a-field-input-border-radius: .25rem`).
- **Modifiers** set atoms on the element: `.t-Button--hot` (Iris: bg `#161513`, text `#efeeec`, weight 700),
  `--danger|--success|--warning|--primary` (palette), `--simple`, `--noUI`, `--link`, `--header`/`--headerTree`/`--navBar`
  (transparent), `--tiny|--xsmall|--small|--large|--xlarge` (size), `--pill*` (radius 0), `--hideShow` (region collapse).
- Therefore: override base atoms on `body.apex-theme-iris` (inherits into every button/field); modifiers keep precedence.
  Override `.t-Button--hot` with a (0,2,0) rule that excludes palette/simple/noUI/link variants.

## Markup
Button: `button|a.t-Button[.t-Button--<mod>…] > span.t-Button-label` (icons: `span.t-Icon.fa.fa-*`).
Computed default: 31.6px tall, 12px/400, 4px radius, `0 2px 4px -3px` shadow; hot 700.
`.t-Button:focus` in Core switches state atoms (`--a-button-state-*`), no visible ring by default → add `:focus-visible` ring.
`rem` = 16px on these pages (`html` font-size not reduced); Core subtracts border from padding (computed 8px for .5625rem).

Field container (default template = Floating label):
```
div.t-Form-fieldContainer.t-Form-fieldContainer--floatingLabel|--stacked[.apex-item-wrapper.apex-item-wrapper--text-field]#<ITEM>_CONTAINER
  div.t-Form-labelContainer > label.t-Form-label
  div.t-Form-inputContainer > div.t-Form-itemWrapper > input.text_field.apex-item-text  + span.a-Form-error
```
Floating-label inputs are 47.6px (padding 25/7/5 set on the element by Core) — untouched by base-atom overrides.
Stacked inputs: ~30px when inside a small form variant (font 12px) — size modifiers win as expected.
Item type classes: `.apex-item-text`, `.apex-item-textarea`, `.apex-item-select`, radio/checkbox `.apex-item-group--rc input + label`.
