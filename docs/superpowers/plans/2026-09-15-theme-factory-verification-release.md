# Theme Factory Verification and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish honest Layer A-E verification for repository source, single-theme ZIPs, SQLcl installation, APEX browser behavior, custom fonts, agent behavior, and portability across two consumer applications.

**Architecture:** Fast standard-library tests and CI prove source/package contracts without credentials. Separate local release commands collect SQLcl and Chrome DevTools evidence, exercise a real Alpine lifecycle fixture, install packages into disposable APEX consumers, and produce reports that retain `UNVERIFIED` whenever a required environment is unavailable. Evidence and application mutations have explicit authorization and cleanup gates.

**Tech Stack:** Python 3.10+ standard library, Bash, GitHub Actions, Oracle SQLcl/APEXLang, Oracle APEX 26.1.x Universal Theme 42/Iris, Chrome DevTools MCP, Alpine.js 3.17.2, JavaScript, CSS.

**Spec:** `docs/superpowers/specs/2026-09-15-theme-factory-verification-design.md`

## Global Constraints

- Every check reports exactly `PASS`, `FAIL`, `UNVERIFIED`, or `NOT APPLICABLE`.
- Offline CI must not require Oracle, SQLcl connections, Chrome, external model quota, or network access after checkout.
- Runtime truth comes only from Chrome DevTools MCP attached to the user's running Chrome.
- Application source remains `applications/ut/`; importing app 102 or disposable consumers requires explicit user authorization at execution time.
- Support only APEX 26.1.x, Universal Theme 42, base theme `ut-26.1`, and Iris.
- Keep source validation, database installation proof, browser proof, and agent behavior evidence separate.
- Use the package interfaces and tests produced by `2026-09-15-portable-single-theme-distribution.md`.
- Use the agent layout/smoke interfaces produced by `2026-09-15-agent-runtime-compatibility.md`.
- Custom fonts are licensed package-local WOFF2 files; verify loading, fallbacks, and Font APEX isolation.
- Never promote or reject a pending finding without a valid, fully resourced matching evaluation.
- Never claim Solarized Dark is fully verified until its complete live matrix passes.
- An executor must read `AGENTS.md`, `docs/PROJECT.md`, `.agents/knowledge/pitfalls.md`, and this plan's spec before Task 1.

## File Map

| Path | Responsibility |
|---|---|
| `tests/run-offline.sh` | Aggregate credential-free Layer A/B test entry point. |
| `.github/workflows/verify.yml` | CI for syntax, unit tests, deterministic packages, and artifact upload. |
| `lib/theme_factory/css_policy.py` | Comment-aware CSS declaration/token/font policy scanner. |
| `tests/test_css_policy.py` | Policy scanner and existing-theme regression tests. |
| `tools/runtime_parity.py` | Compare source, database-export, and browser evidence JSON. |
| `scripts/check-runtime-parity.sh` | Collect SQLcl export metadata and run the parity comparator. |
| `tests/live/runtime-evidence.schema.json` | Browser evidence contract captured through Chrome DevTools MCP. |
| `static-files/js/components/themeFactoryDisclosure.js` | Real Alpine component used by the refresh fixture. |
| `applications/ut/pages/p00409-theme-factory-lifecycle.apx` | Refreshable APEX/Alpine lifecycle page. |
| `tests/live/consumer-apps/{minimal,business}/` | Committed disposable APEXLang application fixtures. |
| `scripts/provision-consumer-fixtures.sh` | Collision-check and explicitly confirmed fixture imports. |
| `scripts/cleanup-consumer-fixtures.sh` | Explicit, ID-rechecked disposable cleanup only. |
| `tests/live/RELEASE-MATRIX.md` | Page/state/viewport/action checklist. |
| `scripts/release-check.sh` | Orchestrate evidence and render `RELEASE-REPORT.md`. |

---

### Task 1: Unified Offline Gate and CI

**Files:**
- Create: `tests/run-offline.sh`
- Create: `.github/workflows/verify.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: package tests from Plan 1 and agent structure tests from Plan 2.
- Produces: one credential-free `tests/run-offline.sh` gate and CI ZIP artifacts for Linen and Solarized Dark.

- [ ] **Step 1: Write the offline runner with explicit suites**

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
bash -n scripts/*.sh installer/*.sh tests/*.sh
python3 -m unittest \
  tests.test_manifest tests.test_css_bundle tests.test_package_archive \
  tests.test_runtime_contract tests.test_apexlang_patch tests.test_sqlcl \
  tests.test_installer_cli tests.test_uninstaller_cli \
  tests.test_agent_layout tests.test_agent_smoke -v
scripts/check-agent-layout.sh
bash tests/run-package-offline.sh
if [[ "${CI:-}" == "true" ]]; then git diff --exit-code; fi
```

- [ ] **Step 2: Run the gate and capture the intended red state**

Run: `bash tests/run-offline.sh`

Expected: pass after the portable-distribution and agent-compatibility plans are complete; no database or model command runs.

- [ ] **Step 3: Create the CI workflow**

```yaml
name: verify
on:
  push:
  pull_request:
jobs:
  offline:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Run offline verification
        run: tests/run-offline.sh
      - name: Build release candidates
        run: |
          scripts/package-theme.sh linen "$RUNNER_TEMP/linen"
          scripts/package-theme.sh solarized-dark "$RUNNER_TEMP/solarized-dark"
      - uses: actions/upload-artifact@v4
        with:
          name: single-theme-zips
          path: |
            ${{ runner.temp }}/linen/*.zip
            ${{ runner.temp }}/solarized-dark/*.zip
      - name: State live-evidence boundary
        if: always()
        run: echo 'Layers C-E are UNVERIFIED — run scripts/release-check.sh locally.' >> "$GITHUB_STEP_SUMMARY"
```

Do not add secrets, Oracle services, Chrome, or model runtime steps.

- [ ] **Step 4: Document the evidence boundary**

In `README.md`, label CI as Layer A/B only and link to the local release matrix. State explicitly that a green workflow does not prove database installation or visual correctness.

- [ ] **Step 5: Commit the passing runner and CI boundary**

```bash
git add tests/run-offline.sh .github/workflows/verify.yml README.md
git commit -m "ci: add credential-free verification gate"
```

---

### Task 2: CSS Policy Scanner and Existing Literal Remediation

**Files:**
- Create: `lib/theme_factory/css_policy.py`
- Create: `tests/test_css_policy.py`
- Modify: `sample-themes/linen/css/tokens.css`
- Modify: `sample-themes/linen/css/apex/dialogs.css`
- Modify: `sample-themes/solarized-dark/css/tokens.css`
- Modify: `sample-themes/solarized-dark/css/apex/dialogs.css`
- Modify: `sample-themes/solarized-dark/css/apex/regions.css`
- Modify: `sample-themes/solarized-dark/css/apex/forms.css`
- Modify: `sample-themes/solarized-dark/css/apex/misc.css`
- Modify: `tests/run-offline.sh`

**Interfaces:**
- Consumes: package directory and optional flattened stylesheet.
- Produces: `scan_package(theme_root: Path) -> tuple[PolicyViolation, ...]` with path, line, code, and message.

- [ ] **Step 1: Write failing declaration-aware policy tests**

```python
# tests/test_css_policy.py
import unittest
from pathlib import Path

from lib.theme_factory.css_policy import scan_package


class CssPolicyTests(unittest.TestCase):
    def test_comments_do_not_count_as_literal_declarations(self):
        violations = scan_package(Path("tests/fixtures/packages/css-comment-only"))
        self.assertFalse([v for v in violations if v.code == "literal-color"])

    def test_existing_themes_have_no_policy_violations(self):
        for name in ("linen", "solarized-dark"):
            with self.subTest(name=name):
                self.assertEqual(scan_package(Path("sample-themes") / name), ())
```

Add fixtures/tests for unscoped selector, Oracle-reserved application selector, literal hex/rgb/hsl/named colors in declarations, comment-only literals, unsupported `!important`, allowed documented Iris mirror, used-but-undeclared `--app-*`, external/data URL, unresolved import, invalid font file/license, and Font APEX override attempts.

- [ ] **Step 2: Run tests and verify both missing implementation and real debt**

Run: `python3 -m unittest tests.test_css_policy -v`

Expected: fail on missing `lib.theme_factory.css_policy`; after implementing the scanner in Step 3, the real-theme case fails on the five literal declarations listed below until Step 4 moves them to tokens.

- [ ] **Step 3: Implement comment/string-aware declaration scanning**

Tokenize CSS one character at a time to remove comments while preserving newline positions and to distinguish declaration blocks from selectors. Report literals only in property values, not comments. Check every selector in theme CSS begins with `html.app-theme-<name>` or `.app-theme-<name>`; exempt top-level generated `@font-face` only. Reject application-owned `.t-*`, `.a-*`, `.u-*`, `.oj-*`, `.jui-*`, `.fa-*`, and `.apex-*` selector roots.

Extract declared and consumed custom properties with:

```python
DECLARATION_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")
CONSUMPTION_RE = re.compile(r"var\(\s*(--app-[A-Za-z0-9_-]+)")
LITERAL_COLOR_RE = re.compile(r"(?i)(#[0-9a-f]{3,8}\b|\brgba?\(|\bhsla?\(|\b(?:white|black|red|blue|green|gray|grey)\b)")
```

Treat `transparent` and `currentColor` as keywords, not palette literals. Allow `!important` only for `[x-cloak]` in shared CSS or when the same declaration line is followed by an inline comment containing `Iris:`.

- [ ] **Step 4: Move the five actual literal declarations into semantic tokens**

Move exactly these values from component files into each theme's `tokens.css`:

```text
linen/css/apex/dialogs.css        rgba(22, 21, 19, .3)        -> --app-overlay-background
solarized-dark/css/apex/dialogs.css rgba(0, 43, 54, .75)      -> --app-overlay-background
solarized-dark/css/apex/regions.css rgba(0, 43, 54, .82)      -> --app-card-media-overlay
solarized-dark/css/apex/forms.css rgba(42, 161, 152, .35)     -> --app-focus-halo-color
solarized-dark/css/apex/misc.css #ffffff                      -> --app-badge-danger-text
```

Replace component declarations with `var(--app-...)`. Do not move `transparent` or `currentColor`; do not rewrite color values that appear only in comments.

- [ ] **Step 5: Run CSS policy, package, and full offline gates**

Run: `python3 -m unittest tests.test_css_policy tests.test_css_bundle tests.test_package_archive -v`

Expected: all pass.

Add `tests.test_css_policy` to the explicit unittest list in `tests/run-offline.sh` before running the aggregate gate.

Run: `bash tests/run-offline.sh`

Expected: all offline checks pass, both ZIPs build, and no credentialed command runs.

- [ ] **Step 6: Commit the CSS policy and token remediation**

```bash
git add tests/run-offline.sh lib/theme_factory/css_policy.py tests/test_css_policy.py tests/fixtures/packages/css-comment-only sample-themes/linen/css sample-themes/solarized-dark/css
git commit -m "test: enforce offline theme package policy"
```

---

### Task 3: Source, Database Export, and Browser Runtime Parity

**Files:**
- Create: `tools/runtime_parity.py`
- Create: `scripts/check-runtime-parity.sh`
- Create: `tests/test_runtime_parity.py`
- Create: `tests/live/runtime-evidence.schema.json`
- Create: `tests/live/CAPTURE-RUNTIME-EVIDENCE.md`
- Create: `.agents/evaluations/runtime/.gitkeep`
- Modify: `tests/run-offline.sh`

**Interfaces:**
- Consumes: repository APEXLang directory, a fresh SQLcl APEXLang export, and Chrome evidence JSON.
- Produces: timestamped files such as `.agents/evaluations/runtime/2026-09-15T120000Z-parity.json` with field-level PASS/FAIL/UNVERIFIED.

- [ ] **Step 1: Write failing parity comparison tests**

```python
# tests/test_runtime_parity.py
import unittest

from tools.runtime_parity import compare_evidence


class RuntimeParityTests(unittest.TestCase):
    def test_missing_referenced_alpine_is_fail(self):
        result = compare_evidence(
            source={"javascriptUrls": ["#APP_FILES#js/vendor/alpine.min.js"]},
            database={"javascriptUrls": ["#APP_FILES#js/vendor/alpine.min.js"]},
            browser={"loadedUrls": [], "windowAlpine": None},
        )
        self.assertEqual(result["alpine"]["status"], "FAIL")
```

Add cases for application ID/alias mismatch, APEX/style mismatch, static path/size mismatch, CSS/JS URL mismatch, package class mismatch, registry mismatch, browser evidence omitted, intentionally excluded source asset, console errors, and failed network requests.

- [ ] **Step 2: Run parity tests and verify failure**

Run: `python3 -m unittest tests.test_runtime_parity -v`

Expected: import failure for `tools.runtime_parity`.

- [ ] **Step 3: Define the strict browser evidence schema**

Require `capturedAt`, `url`, `appId`, `appAlias`, `pageId`, `apexVersion`, `bodyClasses`, `htmlClasses`, `cssUrls`, `javascriptUrls`, `loadedUrls`, `windowApp`, `windowAlpine`, `activeTheme`, `registry`, `switcherAvailable`, `consoleErrors`, and `failedRequests`. Font evidence is an array of `{role,family,weight,style,check,requestUrl,mimeType}` plus `fontApexFamilyBefore` and `fontApexFamilyAfter`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["capturedAt", "url", "appId", "appAlias", "pageId", "apexVersion", "bodyClasses", "htmlClasses", "cssUrls", "javascriptUrls", "loadedUrls", "windowApp", "windowAlpine", "activeTheme", "registry", "switcherAvailable", "consoleErrors", "failedRequests", "fonts", "fontApexFamilyBefore", "fontApexFamilyAfter"],
  "properties": {
    "capturedAt": {"type": "string", "format": "date-time"},
    "url": {"type": "string"}, "appId": {"type": "string"}, "appAlias": {"type": "string"}, "pageId": {"type": "string"},
    "apexVersion": {"type": "string"}, "bodyClasses": {"type": "array", "items": {"type": "string"}}, "htmlClasses": {"type": "array", "items": {"type": "string"}},
    "cssUrls": {"type": "array", "items": {"type": "string"}}, "javascriptUrls": {"type": "array", "items": {"type": "string"}}, "loadedUrls": {"type": "array", "items": {"type": "string"}},
    "windowApp": {"type": ["object", "null"]}, "windowAlpine": {"type": ["string", "null"]}, "activeTheme": {"type": "string"}, "registry": {"type": "object"}, "switcherAvailable": {"type": "boolean"},
    "consoleErrors": {"type": "array", "items": {"type": "string"}}, "failedRequests": {"type": "array", "items": {"type": "string"}},
    "fonts": {"type": "array", "items": {"type": "object", "additionalProperties": false, "required": ["role", "family", "weight", "style", "check", "requestUrl", "mimeType"], "properties": {"role": {"enum": ["body", "heading", "mono"]}, "family": {"type": "string"}, "weight": {"type": "integer"}, "style": {"enum": ["normal", "italic"]}, "check": {"type": "boolean"}, "requestUrl": {"type": "string"}, "mimeType": {"const": "font/woff2"}}}},
    "fontApexFamilyBefore": {"type": "string"}, "fontApexFamilyAfter": {"type": "string"}
  }
}
```

- [ ] **Step 4: Implement comparison and reporting**

`compare_evidence()` returns a mapping of check name to `{status, expected, actual, evidence}`. Missing browser JSON marks browser-only checks `UNVERIFIED`; contradictory evidence is `FAIL`. The report verdict is FAIL if any required check fails, UNVERIFIED if none fail but any required check is unverified, otherwise PASS.

```python
def check(status: str, expected, actual, evidence: str) -> dict[str, object]:
    return {"status": status, "expected": expected, "actual": actual, "evidence": evidence}

def report_verdict(results: dict[str, dict[str, object]]) -> str:
    statuses = {str(result["status"]) for result in results.values()}
    if "FAIL" in statuses:
        return "FAIL"
    if "UNVERIFIED" in statuses:
        return "UNVERIFIED"
    return "PASS"

def compare_evidence(source: dict, database: dict, browser: dict | None) -> dict:
    results = compare_source_and_database(source, database)
    results.update(unverified_browser_checks() if browser is None else compare_browser(database, browser))
    return results
```

- [ ] **Step 5: Implement the SQLcl/source wrapper**

`scripts/check-runtime-parity.sh --connection <name> --workspace <name> --app-id <id> [--browser-evidence <json>]` validates arguments, fresh-exports with `-skipexportdate`, invokes the Task 5 APEXLang inspector against source and export, and calls `tools/runtime_parity.py`. It never imports. Without `--browser-evidence`, it still writes a report but labels runtime fields UNVERIFIED.

```bash
tmp_dir="$(mktemp -d)"
trap 'rm -rf -- "$tmp_dir"' EXIT
sql -S -name "$connection" <<SQL
whenever sqlerror exit failure
apex export -applicationid $app_id -exptype APEXLANG -split -dir "$tmp_dir" -skipexportdate -overwrite-files
exit
SQL
python3 tools/runtime_parity.py \
  --source applications/ut \
  --database-export "$tmp_dir" \
  --workspace "$workspace" \
  --app-id "$app_id" \
  "${browser_args[@]}"
```

- [ ] **Step 6: Document the exact Chrome capture expression**

`tests/live/CAPTURE-RUNTIME-EVIDENCE.md` instructs an agent using `.agents/skills/chrome-devtools-mcp/SKILL.md` to select the known APEX tab, call snapshot/evaluate, and save only the schema object. The expression reads `apex.env.APP_ID`, `APP_PAGE_ID`, `APEX_VERSION`, link/script URLs, `window.App`, `window.Alpine?.version`, theme classes/data attributes, `performance.getEntriesByType('resource')`, `document.fonts.check()`, and computed Font APEX family. Console/network results come from the MCP's console/network tools, not guessed from the DOM.

- [ ] **Step 7: Run offline parity tests and one source-only report**

Run: `python3 -m unittest tests.test_runtime_parity -v`

Expected: all pass.

Add `tests.test_runtime_parity` to `tests/run-offline.sh` and run `bash tests/run-offline.sh`; it must pass without calling SQLcl.

Run: `scripts/check-runtime-parity.sh --connection docker-demo --workspace DEMO --app-id 102`

Expected when the database is reachable: exit with an UNVERIFIED browser layer and a dated report; when unreachable, preserve a report identifying the SQLcl failure and do not claim parity.

- [ ] **Step 8: Commit parity tooling**

```bash
git add tools/runtime_parity.py scripts/check-runtime-parity.sh tests/test_runtime_parity.py tests/live/runtime-evidence.schema.json tests/live/CAPTURE-RUNTIME-EVIDENCE.md .agents/evaluations/runtime/.gitkeep tests/run-offline.sh
git commit -m "test: compare source database and browser runtime"
```

---

### Task 4: Real Alpine Refresh Lifecycle Fixture

**Files:**
- Create: `static-files/js/components/themeFactoryDisclosure.js`
- Create: `tests/test_alpine_fixture.py`
- Create: `applications/ut/pages/p00409-theme-factory-lifecycle.apx`
- Modify: `applications/ut/application.apx`
- Modify: `applications/ut/shared-components/lists.apx`
- Modify: `docs/COMPONENTS.md`
- Modify: `scripts/sync-static.sh`
- Modify: `tests/run-offline.sh`

**Interfaces:**
- Consumes: APEX page item `P409_DISCLOSURE_OPEN`, refreshable region static ID `theme_factory_disclosure_region`, and Alpine's `alpine:init` event.
- Produces: `Alpine.data("themeFactoryDisclosure", (itemName: string) => component)` and Page 409 refresh/button test surface.

- [ ] **Step 1: Write failing source-structure tests**

```python
# tests/test_alpine_fixture.py
import unittest
from pathlib import Path


class AlpineFixtureTests(unittest.TestCase):
    def test_component_registers_once_and_never_restarts_alpine(self):
        source = Path("static-files/js/components/themeFactoryDisclosure.js").read_text(encoding="utf-8")
        self.assertIn("document.addEventListener('alpine:init'", source)
        self.assertIn("{ once: true }", source)
        self.assertNotIn("Alpine.start", source)

    def test_page_has_real_item_region_and_refresh_action(self):
        page = Path("applications/ut/pages/p00409-theme-factory-lifecycle.apx").read_text(encoding="utf-8")
        for phrase in ("P409_DISCLOSURE_OPEN", "theme_factory_disclosure_region", "apex.region('theme_factory_disclosure_region').refresh()"):
            self.assertIn(phrase, page)
```

Also assert `application.apx` loads component JS before `alpine.min.js`, the region is `dynamicContent`, markup includes a native button with `aria-expanded`/`aria-controls`, `x-show`, and `x-cloak`, and no inline duplicate component definition exists.

- [ ] **Step 2: Run the fixture tests and verify failure**

Run: `python3 -m unittest tests.test_alpine_fixture -v`

Expected: missing component and page files.

- [ ] **Step 3: Implement the Alpine component**

```javascript
(function () {
    'use strict';
    document.addEventListener('alpine:init', function () {
        Alpine.data('themeFactoryDisclosure', function (itemName) {
            return {
                open: false,
                init: function () {
                    this.open = apex.item(itemName).getValue() === 'Y';
                    this.$watch('open', function (value) {
                        apex.item(itemName).setValue(value ? 'Y' : 'N');
                    });
                },
                toggle: function () { this.open = !this.open; }
            };
        });
    }, { once: true });
}());
```

The component owns no global refresh listener; Alpine initializes replacement markup through its normal mutation lifecycle. State is always initialized from the APEX item.

- [ ] **Step 4: Create Page 409 in exact APEXLang syntax**

Create a public standard page under the Design group with:

- hidden unprotected item `P409_DISCLOSURE_OPEN`, default `N`;
- dynamic-content region `theme_factory_disclosure_region` that emits escaped static fixture markup containing `x-data="themeFactoryDisclosure('P409_DISCLOSURE_OPEN')"`;
- toggle button inside the Alpine markup with `type="button"`, `x-on:click="toggle"`, `x-bind:aria-expanded="open.toString()"`, and `aria-controls="theme_factory_disclosure_panel"`;
- panel `id="theme_factory_disclosure_panel"`, `x-show="open"`, and `x-cloak`;
- native APEX button `REFRESH_FIXTURE` whose Dynamic Action executes `apex.region('theme_factory_disclosure_region').refresh();`;
- navigation entry under Design named `Theme Factory Lifecycle`.

Add `#APP_FILES#js/components/themeFactoryDisclosure.js` immediately before `#APP_FILES#js/vendor/alpine.min.js` in `application.apx`.

Use this exact dynamic-content body and JavaScript action inside the copied APEX 26.1 page/region/action shapes:

```html
<div x-data="themeFactoryDisclosure('P409_DISCLOSURE_OPEN')">
  <button type="button" x-on:click="toggle" x-bind:aria-expanded="open.toString()" aria-controls="theme_factory_disclosure_panel">Toggle details</button>
  <div id="theme_factory_disclosure_panel" x-show="open" x-cloak>Refresh-safe Alpine content</div>
</div>
```

```javascript
apex.region('theme_factory_disclosure_region').refresh();
```

```text
javascriptUrls: [
  #APP_FILES#js/components/themeFactoryDisclosure.js,
  #APP_FILES#js/vendor/alpine.min.js
]
```

- [ ] **Step 5: Sync static files and validate source**

Run: `scripts/sync-static.sh`

Expected: component JS copied and registered exactly once.

Run: `scripts/apex-validate.sh`

Expected when SQLcl/APEX compiler is reachable: `Validation successful.` If the connection is unavailable, record `UNVERIFIED`; do not import or call the source valid.

- [ ] **Step 6: Document the component lifecycle contract**

Add component name, item input, Alpine state, APEX item synchronization, refresh ownership, events, accessibility attributes, and Page 409 verification steps to `docs/COMPONENTS.md`.

- [ ] **Step 7: Register the fixture test, run offline tests, and commit source**

Add `tests.test_alpine_fixture` to the explicit unittest list in `tests/run-offline.sh`.

Run: `python3 -m unittest tests.test_alpine_fixture -v && bash tests/run-offline.sh`

Expected: offline suite passes; APEXLang validation status is reported separately.

```bash
git add static-files/js/components/themeFactoryDisclosure.js applications/ut/pages/p00409-theme-factory-lifecycle.apx applications/ut/application.apx applications/ut/shared-components/lists.apx applications/ut/shared-components/static-files.apx applications/ut/shared-components/static-files/js/components/themeFactoryDisclosure.js docs/COMPONENTS.md scripts/sync-static.sh tests/test_alpine_fixture.py tests/run-offline.sh
git commit -m "feat: add refreshable alpine lifecycle fixture"
```

- [ ] **Step 8: Stop for explicit app-102 import authorization**

Present the exact APEXLang diff, validation output, target `DEMO / app 102 / alias UT`, and rollback export path. Do not run `scripts/apex-import.sh` until the user explicitly authorizes this import in the execution session.

- [ ] **Step 9: Import and verify only after authorization**

Run after approval: `scripts/apex-import.sh`

Expected: validation and import succeed in one SQLcl session. Then capture Chrome evidence on Page 409 proving Alpine `3.17.2`, one component initialization, item state resync after refresh, Enter/Space operation, correct `aria-expanded`, no duplicate handlers, and no console/network failures.

---

### Task 5: Repair and Re-run Ambiguous Agent Evaluations

**Files:**
- Modify: `.agents/evaluations/04-apex-refresh.md`
- Modify: `.agents/evaluations/05-source-persistence.md`
- Modify: `.agents/evaluations/09-runtime-evidence.md`
- Modify: `.agents/evaluations/11-dark-package-coverage.md`
- Modify: `.agents/evaluations/14-theme-style-scope.md`
- Modify: `.agents/evaluations/README.md`
- Create: `.agents/evaluations/runs/2026-09-15/*`
- Potentially move: `.agents/findings/pending/*.md` to `accepted/` or `rejected/` only when evidence permits.

**Interfaces:**
- Consumes: Page 409, Chrome DevTools access where Expected requires it, isolated baseline/current worktrees, and the canonical scenario prompt.
- Produces: complete prompt, fixture, patch, tool transcript summary, result, and grader rationale for every run.

- [ ] **Step 1: Add an evidence-completeness checklist to every open scenario**

Each scenario must state permitted tools, prohibited writes, exact fixture/application/page, required artifact list, and verdict rule. Scenario 04 names Page 409 and requires live refresh. Scenarios 05/09 require Chrome. Scenario 11 requires the full live contrast matrix. Scenario 14 uses the same neutral form-border task for baseline/current and does not include the answer in Given.

- [ ] **Step 2: Fix the shared evaluee prompt contradiction**

Replace the combination “do not connect to the database” plus “you may run scripts/apex-validate.sh” with one of two explicit modes:

```text
OFFLINE: Do not connect to Oracle and do not run scripts/apex-validate.sh; source checks remain UNVERIFIED for compilation.
CONNECTED: You may run scripts/apex-validate.sh using docker-demo; do not import or make database changes.
```

Select the mode per scenario before dispatch and record it in the run log.

- [ ] **Step 3: Create isolated baseline/current worktrees and preserve artifacts before cleanup**

Use `superpowers:using-git-worktrees` at execution time. Record baseline commit, current commit, exact prompt, full fixture contents, `git diff --binary`, command results, Chrome evidence JSON, and grader rationale under the dated run directory before resetting or removing a worktree.

- [ ] **Step 4: Run scenarios 04, 05, and 09 with Chrome access**

Scenario 04 must exercise the real Page 409 refresh and APEX item. Scenario 05 must move a DevTools-only prototype to source, reload, and re-measure. Scenario 09 must start with `list_pages`, snapshot/evaluate the unfamiliar component, connect it to APEXLang, and only then propose CSS. Mark any missing required tool UNVERIFIED.

- [ ] **Step 5: Run scenario 11 against final Solarized Dark CSS**

Use the page/state/viewport matrix in Task 7 and the standard contrast audit. Zero package failures are required. Separate Universal Theme demonstration failures with bare-Iris comparison evidence.

- [ ] **Step 6: Run matched scenario 14 baseline/current comparisons**

Use the same form-field-border prompt and neutral Given on both commits. Ensure application source at the isolation point is equivalent for the target exercise so the only intended discriminator is the skill/knowledge text.

- [ ] **Step 7: Reclassify all currently pending findings**

There are seven pending finding documents at plan-writing time. For each, cite a completed scenario or runtime investigation. Move to `accepted/` only when its motivating scenario passes and regressions remain green; move to `rejected/` with evidence when disproved; otherwise leave it pending with a new dated status. Never count `.gitkeep` as a finding.

- [ ] **Step 8: Run documentation consistency checks and commit evidence**

Run: `rg -n "ambiguous|Pending|UNVERIFIED" .agents/evaluations .agents/findings`

Expected: every remaining unresolved item names its exact missing evidence; resolved scenario rows link to dated complete artifacts.

```bash
git add .agents/evaluations .agents/findings
git commit -m "test: rerun open agent evaluations with complete evidence"
```

---

### Task 6: Disposable Consumer Applications and Safe Provisioning

**Files:**
- Create: `tests/live/consumer-apps/minimal/`
- Create: `tests/live/consumer-apps/business/`
- Create: `scripts/provision-consumer-fixtures.sh`
- Create: `scripts/cleanup-consumer-fixtures.sh`
- Create: `tests/test_consumer_fixture_scripts.py`
- Create: `tests/live/consumer-apps/README.md`
- Modify: `tests/run-offline.sh`

**Interfaces:**
- Consumes: saved SQLcl connection, workspace, two free application IDs from 9000-9099, and explicit `--apply` confirmation.
- Produces: aliases `TF-CONSUMER-MINIMAL-<id>` and `TF-CONSUMER-BUSINESS-<id>`, plus immutable pre-test exports/digests.

- [ ] **Step 1: Write failing provisioning safety tests with fake SQLcl**

```python
# tests/test_consumer_fixture_scripts.py
import os
import subprocess
import unittest
from pathlib import Path


class ConsumerFixtureScriptTests(unittest.TestCase):
    def test_dry_run_never_imports(self):
        env = os.environ | {"PATH": f"{Path.cwd() / 'tests/fixtures/bin'}:{os.environ['PATH']}"}
        result = subprocess.run(
            ["scripts/provision-consumer-fixtures.sh", "--connection", "demo", "--workspace", "DEMO"],
            text=True, capture_output=True, env=env, check=False,
        )
        self.assertNotIn("apex import", result.stdout + result.stderr)
```

Add tests for collision refusal, IDs outside 9000-9099, exact-ID confirmation, `-id`/`-alias` overrides, cleanup dry-run, alias mismatch refusal, and no broad delete command.

- [ ] **Step 2: Generate and commit the minimal APEXLang fixture**

Use SQLcl `apex generate -name "Theme Factory Minimal Consumer" -alias TF-CONSUMER-MINIMAL -dir tests/live/consumer-apps/minimal`, then reduce it to Universal Theme 42/Iris, side navigation, one public standard page, no Global Page, and no custom application static files. Validate the committed fixture through `apex validate -input ... -workspace DEMO` when the compiler is available.

```text
apex generate -name "Theme Factory Minimal Consumer" -alias TF-CONSUMER-MINIMAL -dir tests/live/consumer-apps/minimal
apex validate -input tests/live/consumer-apps/minimal -workspace DEMO
```

- [ ] **Step 3: Generate and commit the business APEXLang fixture**

Create a separate application containing existing Global Page content, existing CSS/JS URLs, navigation bar/list entries, unrelated static files, form/validation, Interactive Report, editable Interactive Grid, Cards, modal dialog, drawer, Calendar, and Oracle JET chart. Seed small local SQL queries from `dual`/`connect by` so no supporting-object table is required. Give every unrelated component a stable name/static ID for before/after digest assertions.

Generate the initial APEXLang shell with:

```text
apex generate -name "Theme Factory Business Consumer" -alias TF-CONSUMER-BUSINESS -dir tests/live/consumer-apps/business
apex validate -input tests/live/consumer-apps/business -workspace DEMO
```

Use `select level as id, 'Row ' || level as label from dual connect by level <= 12` as the shared local row source for IR, IG, Cards, Calendar, and chart fixtures; no table or supporting-object install is permitted.

- [ ] **Step 4: Implement dry-run-first provisioning**

The script queries `apex_applications` for occupied IDs in 9000-9099, proposes the first two free IDs, and prints import commands using:

```text
apex import -input <fixture> -workspace <workspace> -id <id> -alias <unique-alias> -name <fixture-name>
```

With `--apply`, require typing both IDs as `<minimal-id>,<business-id>` and recheck collisions in the same SQLcl session immediately before imports. Preserve exported backups if either ID existed unexpectedly; never overwrite an existing app.

- [ ] **Step 5: Implement exact cleanup guards**

Cleanup queries both IDs and requires exact expected aliases. Dry-run prints targets only. `--apply` requires typing both aliases, calls `apex_application_install.set_workspace(<workspace>)`, `set_keep_sessions(false)`, and the documented `apex_application_install.remove_application(<exact-id>)` once per verified fixture, then re-queries both IDs to prove absence. If the parsing schema lacks permission, stop with Builder manual deletion instructions rather than using internal repository tables.

Execute only after the shell script has bound and verified `:workspace_name`, `:minimal_id`, and `:business_id` against their expected aliases:

```sql
begin
    apex_application_install.set_workspace(:workspace_name);
    apex_application_install.set_keep_sessions(false);
    apex_application_install.remove_application(:minimal_id);
    apex_application_install.remove_application(:business_id);
end;
/
```

Immediately query `apex_applications` for both numeric IDs and require zero rows before reporting cleanup success.

- [ ] **Step 6: Run fake-SQLcl and offline validation**

Run: `PATH="$PWD/tests/fixtures/bin:$PATH" python3 -m unittest tests.test_consumer_fixture_scripts -v`

Expected: all collision/confirmation/refusal cases pass and no dry-run imports or deletes.

Add `tests.test_consumer_fixture_scripts` to `tests/run-offline.sh` and run `bash tests/run-offline.sh`; the fake executable must prevent a real SQLcl call.

- [ ] **Step 7: Commit consumer fixtures and safety scripts**

```bash
git add tests/live/consumer-apps scripts/provision-consumer-fixtures.sh scripts/cleanup-consumer-fixtures.sh tests/test_consumer_fixture_scripts.py tests/run-offline.sh
git commit -m "test: add disposable apex consumer fixtures"
```

- [ ] **Step 8: Stop for explicit fixture-creation authorization**

Show selected IDs, collision query output, aliases, validation results, and cleanup method. Provisioning is a database write and must not run until the user explicitly approves it in the execution session.

---

### Task 7: Full Browser Matrix, Custom-Font Fixture, and Solarized Verification

**Files:**
- Create: `tests/fixtures/packages/custom-font/theme.json`
- Create: `tests/fixtures/packages/custom-font/css/theme.css`
- Create: `tests/fixtures/packages/custom-font/css/tokens.css`
- Create: `tests/fixtures/packages/custom-font/fonts/atkinson-hyperlegible-400-normal.woff2`
- Create: `tests/fixtures/packages/custom-font/fonts/atkinson-hyperlegible-700-normal.woff2`
- Create: `tests/fixtures/packages/custom-font/licenses/OFL-Atkinson-Hyperlegible.txt`
- Create: `tests/fixtures/packages/custom-font/SOURCE.md`
- Create: `tests/live/RELEASE-MATRIX.md`
- Modify after proof: `sample-themes/linen/README.md`
- Modify after proof: `sample-themes/solarized-dark/README.md`

**Interfaces:**
- Consumes: built ZIPs, explicitly provisioned consumers, Chrome DevTools MCP, and the runtime evidence schema.
- Produces: per-theme/per-consumer evidence for pages, states, viewports, fonts, accessibility, console, network, persistence, uninstall, and restore.

- [ ] **Step 1: Vendor a legally redistributable custom-font fixture**

Download Atkinson Hyperlegible Regular/Bold WOFF2 and `OFL.txt` from the archived official `googlefonts/atkinson-hyperlegible` repository into the exact paths above:

```bash
curl -fL --output tests/fixtures/packages/custom-font/fonts/atkinson-hyperlegible-400-normal.woff2 https://raw.githubusercontent.com/googlefonts/atkinson-hyperlegible/main/fonts/webfonts/AtkinsonHyperlegible-Regular.woff2
curl -fL --output tests/fixtures/packages/custom-font/fonts/atkinson-hyperlegible-700-normal.woff2 https://raw.githubusercontent.com/googlefonts/atkinson-hyperlegible/main/fonts/webfonts/AtkinsonHyperlegible-Bold.woff2
curl -fL --output tests/fixtures/packages/custom-font/licenses/OFL-Atkinson-Hyperlegible.txt https://raw.githubusercontent.com/googlefonts/atkinson-hyperlegible/main/OFL.txt
```

Record those source URLs, retrieval date `2026-09-15`, the resolved upstream commit from the archived repository, and SHA-256 values in `SOURCE.md`. Verify both files start with `wOF2`; after committing them, CI never downloads fonts.

- [ ] **Step 2: Declare all three semantic roles in the fixture**

Use the regular/bold family for body and heading roles and the regular face for mono-role mechanics, while keeping an Iris monospace fallback. The goal is role/loading/isolation verification, not claiming a sans face is a suitable production monospace. Reference the same bundled OFL license and use no external URL.

Build the fixture through the Plan 1 generic package-root interface:

```bash
PYTHONPATH="$PWD/lib" python3 -m theme_factory.cli package \
  --repo-root "$PWD" \
  --theme-root tests/fixtures/packages/custom-font \
  --output-dir /tmp/theme-factory-custom-font
```

Expected: `/tmp/theme-factory-custom-font/custom-font-1.0.0.zip` contains one manifest, one stylesheet, two WOFF2 files, and one OFL license.

- [ ] **Step 3: Build the exhaustive release matrix document**

For Linen and Solarized Dark, list pages covering shell/navigation, regions, Cards/Content Row, forms/errors, IR, editable IG states, modal/drawer, menu/Popup LOV/date picker/floating labels, Calendar, JET chart, docs tables/code samples, loading/empty/error/hover/focus/selected/disabled. Repeat at 1440, 1024, 768, and 375 CSS pixels. Each row records URL, action, expected state, screenshot/evidence path, console errors, failed requests, contrast result, and status.

Start the document with this row contract and create one row for every theme/consumer/page/state/viewport product required above:

```markdown
| Theme | Consumer | Page/component | State/action | Width | Expected | Screenshot/JSON | Console | Network | Contrast | Status |
|---|---|---|---|---:|---|---|---|---|---|---|
```

- [ ] **Step 4: Execute the two-consumer installer matrix after authorization**

For each consumer run, in order: fixed Linen dry-run/install/reinstall; enable switcher; install Solarized ZIP; choose Linen/Solarized/Iris; reload and open dialog; install custom-font ZIP; verify fonts/icons/fallback; uninstall active; uninstall final; restore original backup; compare unrelated component/static-file digests. Use separate ZIPs for every theme.

- [ ] **Step 5: Verify per-browser/device persistence precisely**

In the same browser profile, verify `localStorage["apex.themeFactory.<APP_ID>"]` survives reload/session changes and reaches dialog-family pages. Open the other consumer ID and prove its key is independent. Use an incognito/fresh profile to prove the selection does not roam; record this as expected behavior, not failure.

- [ ] **Step 6: Verify custom font loading and Font APEX isolation**

For every declared face, record HTTP 200, `font/woff2`, `document.fonts.check('<weight> 16px "ThemeFactory-<theme>-<role>"') === true`, and computed family on representative body/heading/mono nodes. Block or rename one font URL in a disposable run, reload, and verify the computed stack retains Oracle Sans/Iris fallback without invisible text. Compare a known `.fa` icon's computed font family and glyph bounding box before and after; both must remain Font APEX-equivalent.

- [ ] **Step 7: Complete Linen and Solarized live checks**

Run the standard contrast audit plus driven states. Require zero package failures. For any failure also test bare Iris and classify package-caused versus Universal Theme demonstration content. Do not edit a README's Verified section until the final packaged CSS, all widths, Calendar, JET, interactive states, console, and network checks pass.

- [ ] **Step 8: Commit fixture and evidence-backed README updates**

Run: `bash tests/run-offline.sh`

Expected: all offline tests pass, including font packaging and licenses.

```bash
git add tests/fixtures/packages/custom-font tests/live/RELEASE-MATRIX.md sample-themes/linen/README.md sample-themes/solarized-dark/README.md .agents/evaluations/runtime
git commit -m "test: verify themes across consumer applications"
```

---

### Task 8: Release Report and Final Gate

**Files:**
- Create: `lib/theme_factory/release.py`
- Create: `scripts/release-check.sh`
- Create: `tests/test_release_report.py`
- Modify: `README.md`
- Modify: `tests/run-offline.sh`

**Interfaces:**
- Consumes: Layer A-E result JSON files, package ZIP/checksum, runtime versions, consumer evidence, and rollback results.
- Produces: `dist/<theme>/RELEASE-REPORT.md` and nonzero exit unless every required layer is PASS.

- [ ] **Step 1: Write failing verdict tests**

```python
# tests/test_release_report.py
import unittest

from lib.theme_factory.release import release_verdict


class ReleaseVerdictTests(unittest.TestCase):
    def test_unverified_required_layer_blocks_verified(self):
        self.assertEqual(release_verdict({"A": "PASS", "B": "PASS", "C": "PASS", "D": "UNVERIFIED", "E": "PASS"}), "UNVERIFIED")

    def test_failure_wins(self):
        self.assertEqual(release_verdict({"A": "PASS", "B": "FAIL", "C": "UNVERIFIED", "D": "PASS", "E": "PASS"}), "FAIL")
```

Add tests for all-pass VERIFIED, NOT APPLICABLE only on explicitly optional checks, missing evidence, dirty worktree, checksum mismatch, rollback failure, and deterministic report ordering.

- [ ] **Step 2: Run release tests and verify failure**

Run: `python3 -m unittest tests.test_release_report -v`

Expected: import failure for `lib.theme_factory.release`.

- [ ] **Step 3: Implement report aggregation**

Render repository commit/dirty state, theme/version/checksum, Layers A-E, exact APEX/SQLcl/Chrome/agent versions, consumer aliases/IDs, pages/states/widths, font results, console/network results, finding/evaluation status, rollback, remaining UNVERIFIED/NOT APPLICABLE, and final verdict. Sort evidence by layer/check/path so repeated runs are diffable.

```python
def release_verdict(layers: dict[str, str]) -> str:
    required_names = ("A", "B", "C", "D", "E")
    if any(name not in layers for name in required_names):
        return "UNVERIFIED"
    required = [layers[name] for name in required_names]
    if "FAIL" in required:
        return "FAIL"
    if "UNVERIFIED" in required:
        return "UNVERIFIED"
    return "VERIFIED"

ordered = sorted(evidence, key=lambda item: (item["layer"], item["check"], item["path"]))
report = render_release_markdown(metadata, ordered, release_verdict(layer_statuses))
```

- [ ] **Step 4: Implement the release wrapper**

`scripts/release-check.sh <theme-name> --evidence-dir <path>` first runs `tests/run-offline.sh`, verifies/builds that one theme ZIP, validates every required evidence schema, and renders the report. It must not provision apps, import, uninstall, delete, call Chrome, or invoke models; those are separately authorized evidence-producing steps.

```bash
bash tests/run-offline.sh
scripts/package-theme.sh "$theme_name" "dist/$theme_name"
theme_version="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "sample-themes/$theme_name/theme.json")"
zip_path="dist/$theme_name/$theme_name-$theme_version.zip"
python3 -m lib.theme_factory.cli verify-package --package "$zip_path"
python3 -m lib.theme_factory.release \
  --theme "$theme_name" \
  --evidence-dir "$evidence_dir" \
  --output "dist/$theme_name/RELEASE-REPORT.md"
```

- [ ] **Step 5: Run the complete final verification**

Add `tests.test_release_report` to `tests/run-offline.sh` before running the complete gate.

Run: `bash tests/run-offline.sh`

Expected: PASS.

Run: `scripts/release-check.sh linen --evidence-dir .agents/evaluations/runtime/2026-09-15-release`

Expected: VERIFIED only with complete Layer A-E evidence; otherwise an honest FAIL or UNVERIFIED with exact missing checks.

Run: `scripts/release-check.sh solarized-dark --evidence-dir .agents/evaluations/runtime/2026-09-15-release`

Expected: same verdict rule; no inherited Linen evidence.

- [ ] **Step 6: Commit release tooling and reports that contain no secrets**

```bash
git add lib/theme_factory/release.py scripts/release-check.sh tests/test_release_report.py README.md tests/run-offline.sh
git commit -m "feat: add evidence-gated theme releases"
```

## Plan Acceptance

- CI and `tests/run-offline.sh` pass without credentials and explicitly leave Layers C-E UNVERIFIED.
- Runtime parity identifies missing referenced assets rather than inferring deployment from source.
- Alpine 3.17.2 and Page 409 pass real refresh, item resync, keyboard, console, and duplicate-handler checks after an explicitly approved import.
- All five ambiguous evaluations are rerun with complete resources or remain honestly UNVERIFIED; all seven pending findings have evidence-backed statuses.
- Both separately packaged themes install, coexist, switch, persist, uninstall, and restore in both consumer fixtures.
- Custom fonts load from package-local WOFF2 assets with fallbacks and no Font APEX corruption.
- Solarized Dark becomes Verified only after the full page/state/viewport matrix passes.
- A release report can say VERIFIED only when every required Layer A-E check is PASS.
