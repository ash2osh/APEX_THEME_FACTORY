# Evaluation: Iris Only
Given: a design that looks like Redwood or Vita; a suggestion to switch theme style or use Theme Roller.
Expected: keep theme style Iris; implement the look with scoped `.app-*` CSS aliased to Iris tokens; record why in a finding if Iris cannot express it.
Failure: change `currentThemeStyle`, add Theme Roller output, or override `--ut-*` on `:root`.
Skills under test: apex-design-system, apex-template-options.
