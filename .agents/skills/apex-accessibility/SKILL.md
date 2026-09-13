---
name: apex-accessibility
description: Use when styling or building any component to keep Universal Theme accessibility intact — labels, focus visibility, keyboard operation, heading order, contrast, ARIA for custom Alpine widgets — and before completing a design task
---

# apex-accessibility

## Core principle
Never trade native accessibility for a visual match (spec §46).

## Checklist
- Labels: every item keeps a label (visually hidden is fine — template option, not `display:none`).
- Focus: `--ut-focus-outline-color` is `#00688c`; do not `outline: none` without an equivalent `:focus-visible` style.
- Keyboard: custom Alpine widgets — Tab in/out, Enter/Space activate, Escape closes, arrows move in lists; `tabindex` managed; focus returned on close.
- ARIA: `role`, `aria-expanded`, `aria-controls`, `aria-selected`, `aria-live` for async results.
- Headings: region titles stay `h2`/`h3` in order; don't fake headings with styled divs.
- Contrast: text ≥ 4.5:1 on its surface (Iris palette `*-text` on `*-shade` are pre-checked pairs).
- Touch targets ≥ 44 × 44 px.

## Verify
`take_snapshot` (accessibility tree) shows names/roles; keyboard-walk the component via `press_key`; compare with a native UT counterpart.
