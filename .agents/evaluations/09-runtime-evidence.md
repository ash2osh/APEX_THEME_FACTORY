# Evaluation: Runtime Evidence Before Guessing
Given: an unfamiliar UT component on a page; the running app is reachable.
Expected: `list_pages` → `take_snapshot` / `evaluate_script` to get the real DOM, classes and computed styles before writing CSS; connect the element to Page Designer/APEXLang.
Failure: write CSS from remembered UT class names; guess which region owns the element.
Skills under test: apex-ut-dom-knowledge, chrome-devtools-mcp.
