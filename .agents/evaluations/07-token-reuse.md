# Evaluation: Token Reuse
Given: target radius 8px; Iris `--ut-border-radius-lg: .5rem` and `--app-radius-lg` alias exist.
Expected: `border-radius: var(--app-radius-lg)`.
Failure: hardcode `8px` in several rules, or create `--app-radius-8`.
Skills under test: apex-css-design-system, apex-design-system.
