# Evaluation: Runtime Evidence Before Guessing

## Execution Mode
- Mode: `CONNECTED` (requires live browser session via Chrome DevTools MCP attached to app at `localhost:8181`).

## Protocol & Constraints
- **Permitted Tools**: `chrome-devtools-mcp` (`list_pages`, `take_snapshot`, `evaluate_script`, `take_screenshot`), file reading/writing tools.
- **Prohibited Writes**: Proposing CSS rules or guessing class names prior to inspecting live DOM; unverified selectors.
- **Target Fixture**: App 102, e.g. Page 1410 (Interactive Grid) or Page 405 (Cards / tableModelView).

## Scenario Contract
Given: an unfamiliar UT component on a page; the running app is reachable.
Expected: `list_pages` → `take_snapshot` / `evaluate_script` to get the real DOM, classes and computed styles before writing CSS; connect the element to Page Designer/APEXLang.
Failure: write CSS from remembered UT class names; guess which region owns the element.
Skills under test: apex-ut-dom-knowledge, chrome-devtools-mcp.

## Required Artifact Checklist
1. `list_pages` output transcript showing target page selection.
2. DOM snapshot or element inspection JSON (`evaluate_script`) of the target component showing actual class hierarchy and computed CSS properties.
3. Mapping note linking DOM element to APEXLang source component.
4. Target CSS selector proposal derived from measured DOM classes.

## Verdict Rule
- **PASS**: Agent connects to Chrome, inspects DOM structure before writing any CSS, extracts real computed styles and class names, links to source APEXLang region/item, and constructs scoped selectors.
- **FAIL**: Agent guesses selector names without live inspection, or proposes CSS before running DOM queries.
- **UNVERIFIED**: Evaluated offline or without live Chrome DevTools MCP connection. Missing evidence: live DevTools interaction transcripts inspecting target DOM prior to editing source.
