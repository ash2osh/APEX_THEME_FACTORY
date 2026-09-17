# Release Verification Matrix

A row may become `PASS` only when its referenced JSON artifact exists, validates against the runtime evidence
contract, and is bound (SHA-256) to the theme package and the source commit. The tables below are generated
from the retained evidence under `.agents/evaluations/runtime/2026-09-17-release-<theme>/`.

## Current evidence status (2026-09-17, commit `c88ce9df62cb`, APEX 26.1.4)

| Theme | Layer | Coverage | Retained evidence | Status |
|---|---|---|---|---|
| linen | C database | install, stale-restore guard, reinstall, switcher enable/disable, coexistence with solarized-dark, uninstall ×2, unrelated-file preservation, restore — on TF-CONSUMER-MINIMAL-9010 (no Global Page, no static files) and TF-CONSUMER-BUSINESS-9011 | `2026-09-17-release-linen/database_installation.json` + `raw/operation-*.json`, `raw/application-*.json` | **PASS** |
| solarized-dark | C database | same operations with linen as the coexisting package | `2026-09-17-release-solarized-dark/database_installation.json` + raw | **PASS** |
| linen | D browser | minimal Home and business Home at 1440/1024/768/375; business Reports (IR + editable IG) and Widgets (Calendar + JET chart) at 1440/375 | `2026-09-17-release-linen/browser_runtime_matrix.json` + `raw/browser-*.json` | **PASS** (12 rows) |
| solarized-dark | D browser | same pages and widths | `2026-09-17-release-solarized-dark/browser_runtime_matrix.json` + raw | **PASS** (12 rows) |
| both | E agent | Codex PASS, Claude Code PASS (2026-09-16), Antigravity PASS (2026-09-17); scenarios 04, 05, 09, 11, 14 all PASS; 0 pending findings | `2026-09-17-release-<theme>/agent_behavior_matrix.json` + `raw/agent-runtime-*.json`, `raw/scenario-*.json`, `raw/finding-*.json` | **PASS** |

Each Layer D row records: `apex.env` identity, html/body classes, CSS/JS URLs, loaded resources, `registry.json`,
console errors, failed requests (status ≥ 400 or network failure), `document.fonts` state for Font APEX, the icon
`::before` family, the body family compared with bare Iris on the same page, every font face the package
declares — each one forced to load and then matched to the request that served it, so a face no page happens to
render (solarized-dark's mono) is proven usable rather than reported missing (pitfalls §4.6) — the AA contrast audit from
`docs/CHROME_DEVTOOLS_MCP.md` (zero failures required), the switcher menu opened by keyboard with exactly one
checked `menuitemradio`, and the selection surviving a second reload under `apex.themeFactory.<APP_ID>`.

The audit scores CSS `color` for HTML text and `fill` for `svg text`/`tspan` (added 2026-09-17: evaluation
scenario 11 found Oracle JET chart labels failing at 1.46:1 while the older sweep reported the page clean).

Not covered by the automated rows (remains manual): driven hover/empty/validation-error states, Popup LOV and
date picker, dialog/drawer open states, IG edit/sort/filter interactions, and the reference app 102 itself.
Scenario 11's 24-page sweep of app 102 with driven states is the widest audit run so far and is what caught
the four `solarized-dark` defects fixed on 2026-09-17
(`.agents/evaluations/runs/2026-09-16/11-dark-package-coverage-current.md`). It was re-run against the fixed,
imported build on 2026-09-17 — 0 package-caused failures, the two remaining groups proven UT/APEX-owned by a
bare-Iris A/B (`.agents/evaluations/runs/2026-09-17/11-dark-package-coverage-postimport.md`). The remaining
coverage step is the other 98 pages of app 102 and the 1024/768 widths there.

## Layer D rows

| Theme | Consumer | App ID / alias | Page | State/action | Width | Expected | JSON | Console | Network | Contrast | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| linen | minimal | 9010 /  | page 1 | switch via runtime → reload | 1440 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| linen | minimal | 9010 /  | page 1 | switch via runtime → reload | 1024 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| linen | minimal | 9010 /  | page 1 | switch via runtime → reload | 768 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| linen | minimal | 9010 /  | page 1 | switch via runtime → reload | 375 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 1 | switch via runtime → reload | 1440 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 1 | switch via runtime → reload | 1024 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 1 | switch via runtime → reload | 768 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 1 | switch via runtime → reload | 375 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 2 | switch via runtime → reload | 1440 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-1440.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 2 | switch via runtime → reload | 375 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-375.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 3 | switch via runtime → reload | 1440 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-1440.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 3 | switch via runtime → reload | 375 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-375.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | minimal | 9010 /  | page 1 | switch via runtime → reload | 1440 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | minimal | 9010 /  | page 1 | switch via runtime → reload | 1024 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | minimal | 9010 /  | page 1 | switch via runtime → reload | 768 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | minimal | 9010 /  | page 1 | switch via runtime → reload | 375 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 1 | switch via runtime → reload | 1440 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 1 | switch via runtime → reload | 1024 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 1 | switch via runtime → reload | 768 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 1 | switch via runtime → reload | 375 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 2 | switch via runtime → reload | 1440 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-1440.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 2 | switch via runtime → reload | 375 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-375.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 3 | switch via runtime → reload | 1440 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-1440.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 3 | switch via runtime → reload | 375 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-375.json` | 0 errors | 0 failed | clean | PASS |

## How to regenerate

```bash
python3 tools/live_matrix.py --connection docker-demo --workspace DEMO --minimal-id 9010 --business-id 9011 --primary dist/<theme>/<theme>-1.0.0.zip --secondary dist/<other>/<other>-1.0.0.zip --apply
python3 tools/browser_matrix.py --theme <theme> --package dist/<theme>/<theme>-1.0.0.zip --minimal-url … --business-url … --business-extra-urls …
scripts/release-check.sh <theme>
```

Run them from a clean tree at the commit the packages were built from; evidence and Markdown commits do not
invalidate the binding (`lib/theme_factory/gitstate.py`), any other change does.
