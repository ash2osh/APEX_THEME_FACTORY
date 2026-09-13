---
name: apex-css-selector-strategy
description: Use when choosing a CSS selector for an APEX/Universal Theme element, when a rule is not applying, or when tempted to use !important, a global .t-* rule, or an nth-child path
---

# apex-css-selector-strategy

## Ladder (spec §21) — pick the highest rung that works
1. `.app-employee-card` — semantic class set via `cssClasses:` in APEXLang.
2. `#employee_summary` — Static ID.
3. `.app-employee-card .t-Region-header` — UT internal scoped under app class.
4. `.t-Region` — bare UT class. Only for verified app-wide intent.
5. `div > div:nth-child(2)` — never, unless documented with the reason.

## Diagnosing "my rule doesn't apply"
```text
evaluate_script: getComputedStyle(el).getPropertyValue(prop)  → is my value there?
  no → is the selector matching? (document.querySelectorAll(sel).length)
     no → wrong class name / element replaced after refresh → re-inspect DOM
     yes → specificity lost → scope higher (.app-x .t-…) or move rule later in app.css
```
Iris rules on `.t-Region` typically have specificity (0,1,0)–(0,3,0); a scoped `.app-x .t-Region-header` (0,2,0) placed after theme CSS wins most of them.

## Page scoping without new classes
`html.page-500 …` / `html.app-UT …` exist on every page — use `.page-<N>` for page-local rules.

## Common mistakes
- Styling the region *wrapper* when the visual box is `.t-Region-body`.
- Selectors that match the Builder dev toolbar (`#apexDevToolbar`) — exclude it.
- `!important` (only with a comment naming the verified conflict).
