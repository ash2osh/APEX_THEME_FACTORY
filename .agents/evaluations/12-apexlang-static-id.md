# Evaluation: APEXLang Static ID
Given: The Page Designer property **Static ID** is the APEXLang property `htmlDomId` inside `advanced { }`.
`staticId` also exists in the same group but is the compiler's *internal component identifier*
(`staticId (required)`), not the DOM id. Writing `advanced { staticId: theme_packages_cards }` validated but
produced no `id="theme_packages_cards"` at runtime; `htmlDomId` did.
Expected: "Give region X a Static ID so page CSS can target it" → `advanced { htmlDomId: x }`.
Failure: `advanced { staticId: x }`.
Skills under test: apexlang-design-editor.

Note (2026-09-15, after PR #4 review, P2): this scenario's task only exercises the `htmlDomId`-vs-`staticId`
half of the underlying finding (`2026-09-14-apexlang-static-id-is-htmldomid.md`). The finding's second
correction — app-level CSS/JS routed to `userInterface { css/javaScript }` instead of the top-level
`css { fileUrls }` / `javaScript { fileUrls }` blocks — is **not covered by any run of this scenario**, since
the task never asks the evaluee to add an app-level file reference. Do not treat a PASS here as evidence for
that half of the skill fix; a separate scenario task (e.g. "add a new app-wide JS file reference") is needed to
test it.
