# Cobalt Press

Light editorial theme for Universal Theme 42 / Iris: warm paper, ink structure, cobalt directives,
vermilion marks, low-radius panels, strong rules, and crisp offset shadows.

## Identity

Cobalt Press is the warm editorial light system: black rules on paper, offset white sheets, cobalt directive
underlines, vermilion annotations, outlined inputs, and deliberate shift motion. It is a standalone Cairo package,
not the inherited slate shell used by the original factory samples.

## Typography and provenance

- **Cairo**, weights 400/500/600/700, is used for body and headings.
- Arabic and Latin glyphs are retained in every static WOFF2 face.
- Source: `google/fonts` commit `f2bd09badbc763d8757951d52deec29da27e85fb`,
  `ofl/cairo/Cairo[slnt,wght].ttf`, instantiated at `slnt=0`.
- License: SIL Open Font License 1.1 in `licenses/OFL.txt`.
- Runtime family: `ThemeFactory-cobalt-press-body`; Font APEX icons remain isolated.

## Verification

**VERIFIED** — Layers A–D PASS at source commit `0d08cb36412f355067e8fb54cafc5b5a386849d3`
(2026-09-21), including the two-consumer SQLcl lifecycle and 8-row browser matrix. Agent compatibility
is a standalone project signal and is not a theme release gate.
