# Evaluation: Source Persistence
Given: a DevTools prototype (injected `<style>`/console JS) that makes the page match the target.
Expected: move the change into static-files CSS/JS and/or APEXLang, reload, re-verify, then declare done.
Failure: consider the DevTools modification complete; report "done" with the change only in the browser.
Skills under test: design-to-apex, apex-visual-comparison, apex-design-review.
