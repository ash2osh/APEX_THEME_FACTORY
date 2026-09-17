---
name: apex-visual-comparison
description: Use when comparing the running APEX page against the target design (Figma/Stitch/screenshot) — measuring position, size, spacing, typography, colour — and before claiming a visual change is done
---

# apex-visual-comparison

## Core principle
A change is done when the runtime matches the target at matching viewports, not when the CSS reads right (spec §47).

## Loop
```text
reload → list_console_messages (no new errors) → resize_page to target width →
take_screenshot → put beside target → list mismatches by priority (§10) →
evaluate_script to measure the mismatched element → fix source → repeat
```

## Measure, don't eyeball
`() => { const r = document.querySelector('<sel>').getBoundingClientRect(); const cs = getComputedStyle(document.querySelector('<sel>')); return { x:r.x, y:r.y, w:r.width, h:r.height, font: cs.font, color: cs.color, bg: cs.backgroundColor, radius: cs.borderRadius, pad: cs.padding, gap: cs.gap }; }`

Compare in order: hierarchy → structure → layout → proportions → typography → spacing → colour → surfaces → interaction → decoration → pixels.

## Noise to ignore (spec §74)
≤ 1 px from font rendering/antialiasing/scale factor; the system UI stack Iris renders vs a design's Inter metrics; sub-pixel gaps. Stop when meaningful mismatches are gone.

## Output of a comparison
A short table: element · target · actual · fix. Keep it in the response, not in a file.
