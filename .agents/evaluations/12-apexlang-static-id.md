# Evaluation: APEXLang Static ID
Given: The Page Designer property **Static ID** is the APEXLang property `htmlDomId` inside `advanced { }`.
`staticId` also exists in the same group but is the compiler's *internal component identifier*
(`staticId (required)`), not the DOM id. Writing `advanced { staticId: theme_packages_cards }` validated but
produced no `id="theme_packages_cards"` at runtime; `htmlDomId` did.
Expected: "Give region X a Static ID so page CSS can target it" → `advanced { htmlDomId: x }`.
Failure: `advanced { staticId: x }`, or app-level CSS/JS routed to `userInterface { css/javaScript }` instead of
the top-level `css { fileUrls }` / `javaScript { fileUrls }` blocks in `application.apx`.
Skills under test: apexlang-design-editor.
