# Release Verification Matrix

A row may become `PASS` only when its referenced JSON artifact exists, validates against the runtime evidence
contract, and is bound (SHA-256) to the theme package and the source commit. The tables below are generated
from retained evidence under `.agents/evaluations/runtime/<date>-release-<theme>/`.

## Current source/package-bound status

<!-- @generated:theme-status:start -->
| Theme | A | B | C | D | E | Verdict |
|---|---:|---:|---:|---:|---:|---|
| carbon-volt | PASS | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED — release evidence is bound to a different source identity |
| citrus-pop | PASS | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED — release evidence is bound to a different source identity |
| cobalt-press | PASS | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED — release evidence is bound to a different source identity |
| estate-slate | PASS | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED — release evidence is bound to a different source identity |
| estate-slate-dark | PASS | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED — release evidence is bound to a different source identity |
| linen | PASS | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED — release evidence is bound to a different source identity |
| solarized-dark | PASS | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED — release evidence is bound to a different source identity |
| velvet-signal | PASS | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED — release evidence is bound to a different source identity |
<!-- @generated:theme-status:end -->

## Current evidence status (2026-09-17, commit `7ac2e0204ca0`, APEX 26.1.4)

| Theme | Layer | Coverage | Retained evidence | Status |
|---|---|---|---|---|
| linen | C database | install, stale-restore guard, reinstall, switcher enable/disable, coexistence with solarized-dark, uninstall ×2, unrelated-file preservation, restore — on TF-CONSUMER-MINIMAL-9010 and TF-CONSUMER-BUSINESS-9011 | `2026-09-17-release-linen/database_installation.json` + `raw/operation-*.json`, `raw/application-*.json` | **PASS** |
| solarized-dark | C database | install, stale-restore guard, reinstall, switcher enable/disable, coexistence with linen, uninstall ×2, unrelated-file preservation, restore — on TF-CONSUMER-MINIMAL-9010 and TF-CONSUMER-BUSINESS-9011 | `2026-09-17-release-solarized-dark/database_installation.json` + `raw/operation-*.json`, `raw/application-*.json` | **PASS** |
| estate-slate | C database | install, stale-restore guard, reinstall, switcher enable/disable, coexistence with estate-slate-dark, uninstall ×2, unrelated-file preservation, restore — on TF-CONSUMER-MINIMAL-9012 and TF-CONSUMER-BUSINESS-9013 | `2026-09-17-release-estate-slate/database_installation.json` + `raw/operation-*.json`, `raw/application-*.json` | **PASS** |
| estate-slate-dark | C database | install, stale-restore guard, reinstall, switcher enable/disable, coexistence with estate-slate, uninstall ×2, unrelated-file preservation, restore — on TF-CONSUMER-MINIMAL-9012 and TF-CONSUMER-BUSINESS-9013 | `2026-09-17-release-estate-slate-dark/database_installation.json` + `raw/operation-*.json`, `raw/application-*.json` | **PASS** |
| linen | D browser | minimal Home and business Home at 1440/1024/768/375; business Reports (IR + editable IG) and Widgets (Calendar + JET chart) at 1440/375; no custom fonts declared | `2026-09-17-release-linen/browser_runtime_matrix.json` + `raw/browser-*.json` | **PASS** (12 rows) |
| solarized-dark | D browser | minimal Home and business Home at 1440/1024/768/375; business Reports (IR + editable IG) and Widgets (Calendar + JET chart) at 1440/375; 5 declared WOFF2 faces, each forced to load and matched to its serving request | `2026-09-17-release-solarized-dark/browser_runtime_matrix.json` + `raw/browser-*.json` | **PASS** (12 rows) |
| estate-slate | D browser | minimal Home and business Home at 1440/1024/768/375; business Reports (IR + editable IG) and Widgets (Calendar + JET chart) at 1440/375; 4 declared WOFF2 faces, each forced to load and matched to its serving request | `2026-09-17-release-estate-slate/browser_runtime_matrix.json` + `raw/browser-*.json` | **PASS** (12 rows) |
| estate-slate-dark | D browser | minimal Home and business Home at 1440/1024/768/375; business Reports (IR + editable IG) and Widgets (Calendar + JET chart) at 1440/375; 4 declared WOFF2 faces, each forced to load and matched to its serving request | `2026-09-17-release-estate-slate-dark/browser_runtime_matrix.json` + `raw/browser-*.json` | **PASS** (12 rows) |
| all four | E agent | Codex PASS, Claude Code PASS (2026-09-16), Antigravity PASS (2026-09-17); scenarios 04, 05, 09, 11, 14 all PASS; 0 pending findings | `2026-09-17-release-<theme>/agent_behavior_matrix.json` + `raw/agent-runtime-*.json`, `raw/scenario-*.json`, `raw/finding-*.json` | **PASS** |

## New bilingual theme evidence (2026-09-19, commit `4495d5b70d0b`, APEX 26.1.4)

| Theme | Layer | Coverage | Retained evidence | Status |
|---|---|---|---|---|
| carbon-volt | C database | install, reinstall, switcher enable/disable, coexistence with velvet-signal, uninstall ×2, unrelated-file preservation, restore — on TF-CONSUMER-MINIMAL-9000 and TF-CONSUMER-BUSINESS-9001 | `2026-09-19-release-carbon-volt/database_installation.json` + `raw/operation-*.json`, `raw/application-*.json` | **PASS** |
| velvet-signal | C database | install, reinstall, switcher enable/disable, coexistence with carbon-volt, uninstall ×2, unrelated-file preservation, restore — on TF-CONSUMER-MINIMAL-9000 and TF-CONSUMER-BUSINESS-9001 | `2026-09-19-release-velvet-signal/database_installation.json` + `raw/operation-*.json`, `raw/application-*.json` | **PASS** |
| cobalt-press | C database | install, reinstall, switcher enable/disable, coexistence with citrus-pop, uninstall ×2, unrelated-file preservation, restore — on TF-CONSUMER-MINIMAL-9000 and TF-CONSUMER-BUSINESS-9001 | `2026-09-19-release-cobalt-press/database_installation.json` + `raw/operation-*.json`, `raw/application-*.json` | **PASS** |
| citrus-pop | C database | install, reinstall, switcher enable/disable, coexistence with cobalt-press, uninstall ×2, unrelated-file preservation, restore — on TF-CONSUMER-MINIMAL-9000 and TF-CONSUMER-BUSINESS-9001 | `2026-09-19-release-citrus-pop/database_installation.json` + `raw/operation-*.json`, `raw/application-*.json` | **PASS** |
| carbon-volt | D browser | minimal and business Home at 1440/1024/768/375; business Reports and Widgets at 1440/375; 4 Noto Kufi Arabic WOFF2 faces forced to load from the package | `2026-09-19-release-carbon-volt/browser_runtime_matrix.json` + `raw/browser-*.json` | **PASS** (12 rows) |
| velvet-signal | D browser | minimal and business Home at 1440/1024/768/375; business Reports and Widgets at 1440/375; 4 Alexandria WOFF2 faces forced to load from the package | `2026-09-19-release-velvet-signal/browser_runtime_matrix.json` + `raw/browser-*.json` | **PASS** (12 rows) |
| cobalt-press | D browser | minimal and business Home at 1440/1024/768/375; business Reports and Widgets at 1440/375; 4 Cairo WOFF2 faces forced to load from the package | `2026-09-19-release-cobalt-press/browser_runtime_matrix.json` + `raw/browser-*.json` | **PASS** (12 rows) |
| citrus-pop | D browser | minimal and business Home at 1440/1024/768/375; business Reports and Widgets at 1440/375; 4 real Tajawal WOFF2 faces forced to load from the package | `2026-09-19-release-citrus-pop/browser_runtime_matrix.json` + `raw/browser-*.json` | **PASS** (12 rows) |
| all four new themes | E agent | Required agent runtime and scenario evidence has not been captured for these packages | — | **UNVERIFIED** |

The four bilingual packages therefore remain **UNVERIFIED** release candidates: Layers A–D pass, while Layer E
is required before any catalog row can be promoted to `VERIFIED`.

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
coverage step is the other 98 pages of app 102 and the 1024/768 widths there. `estate-slate` and
`estate-slate-dark` have Layer C/D/E evidence as of 2026-09-17 but have not had a dedicated multi-page
accessibility sweep the way `solarized-dark` did; their AA contrast audit is the same automated per-row check
every theme gets, not a driven multi-state pass.

## Layer D rows

| Theme | Consumer | App ID / alias | Page | State/action | Width | Expected | JSON | Console | Network | Contrast | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| linen | business | 9011 /  | page 1 | switch via runtime → reload | 1024 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 1 | switch via runtime → reload | 1440 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 1 | switch via runtime → reload | 375 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 1 | switch via runtime → reload | 768 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 2 | switch via runtime → reload | 1440 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-1440.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 2 | switch via runtime → reload | 375 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-375.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 3 | switch via runtime → reload | 1440 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-1440.json` | 0 errors | 0 failed | clean | PASS |
| linen | business | 9011 /  | page 3 | switch via runtime → reload | 375 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-375.json` | 0 errors | 0 failed | clean | PASS |
| linen | minimal | 9010 /  | page 1 | switch via runtime → reload | 1024 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| linen | minimal | 9010 /  | page 1 | switch via runtime → reload | 1440 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| linen | minimal | 9010 /  | page 1 | switch via runtime → reload | 375 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| linen | minimal | 9010 /  | page 1 | switch via runtime → reload | 768 | active `linen`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 1 | switch via runtime → reload | 1024 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 1 | switch via runtime → reload | 1440 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 1 | switch via runtime → reload | 375 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 1 | switch via runtime → reload | 768 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 2 | switch via runtime → reload | 1440 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-1440.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 2 | switch via runtime → reload | 375 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-375.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 3 | switch via runtime → reload | 1440 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-1440.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | business | 9011 /  | page 3 | switch via runtime → reload | 375 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-375.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | minimal | 9010 /  | page 1 | switch via runtime → reload | 1024 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | minimal | 9010 /  | page 1 | switch via runtime → reload | 1440 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | minimal | 9010 /  | page 1 | switch via runtime → reload | 375 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| solarized-dark | minimal | 9010 /  | page 1 | switch via runtime → reload | 768 | active `solarized-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | business | 9013 /  | page 1 | switch via runtime → reload | 1024 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | business | 9013 /  | page 1 | switch via runtime → reload | 1440 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | business | 9013 /  | page 1 | switch via runtime → reload | 375 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | business | 9013 /  | page 1 | switch via runtime → reload | 768 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | business | 9013 /  | page 2 | switch via runtime → reload | 1440 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-1440.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | business | 9013 /  | page 2 | switch via runtime → reload | 375 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-375.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | business | 9013 /  | page 3 | switch via runtime → reload | 1440 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-1440.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | business | 9013 /  | page 3 | switch via runtime → reload | 375 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-375.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | minimal | 9012 /  | page 1 | switch via runtime → reload | 1024 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | minimal | 9012 /  | page 1 | switch via runtime → reload | 1440 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | minimal | 9012 /  | page 1 | switch via runtime → reload | 375 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate | minimal | 9012 /  | page 1 | switch via runtime → reload | 768 | active `estate-slate`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | business | 9013 /  | page 1 | switch via runtime → reload | 1024 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | business | 9013 /  | page 1 | switch via runtime → reload | 1440 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | business | 9013 /  | page 1 | switch via runtime → reload | 375 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | business | 9013 /  | page 1 | switch via runtime → reload | 768 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | business | 9013 /  | page 2 | switch via runtime → reload | 1440 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-1440.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | business | 9013 /  | page 2 | switch via runtime → reload | 375 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-375.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | business | 9013 /  | page 3 | switch via runtime → reload | 1440 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-1440.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | business | 9013 /  | page 3 | switch via runtime → reload | 375 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-375.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | minimal | 9012 /  | page 1 | switch via runtime → reload | 1024 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | minimal | 9012 /  | page 1 | switch via runtime → reload | 1440 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | minimal | 9012 /  | page 1 | switch via runtime → reload | 375 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| estate-slate-dark | minimal | 9012 /  | page 1 | switch via runtime → reload | 768 | active `estate-slate-dark`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | business | 9001 /  | page 1 | switch via runtime → reload | 1024 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | business | 9001 /  | page 1 | switch via runtime → reload | 1440 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | business | 9001 /  | page 1 | switch via runtime → reload | 375 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | business | 9001 /  | page 1 | switch via runtime → reload | 768 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | business | 9001 /  | page 2 | switch via runtime → reload | 1440 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-1440.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | business | 9001 /  | page 2 | switch via runtime → reload | 375 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-375.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | business | 9001 /  | page 3 | switch via runtime → reload | 1440 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-1440.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | business | 9001 /  | page 3 | switch via runtime → reload | 375 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-375.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | minimal | 9000 /  | page 1 | switch via runtime → reload | 1024 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | minimal | 9000 /  | page 1 | switch via runtime → reload | 1440 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | minimal | 9000 /  | page 1 | switch via runtime → reload | 375 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| carbon-volt | minimal | 9000 /  | page 1 | switch via runtime → reload | 768 | active `carbon-volt`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | business | 9001 /  | page 1 | switch via runtime → reload | 1024 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | business | 9001 /  | page 1 | switch via runtime → reload | 1440 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | business | 9001 /  | page 1 | switch via runtime → reload | 375 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | business | 9001 /  | page 1 | switch via runtime → reload | 768 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | business | 9001 /  | page 2 | switch via runtime → reload | 1440 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-1440.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | business | 9001 /  | page 2 | switch via runtime → reload | 375 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-375.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | business | 9001 /  | page 3 | switch via runtime → reload | 1440 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-1440.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | business | 9001 /  | page 3 | switch via runtime → reload | 375 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-375.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | minimal | 9000 /  | page 1 | switch via runtime → reload | 1024 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | minimal | 9000 /  | page 1 | switch via runtime → reload | 1440 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | minimal | 9000 /  | page 1 | switch via runtime → reload | 375 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| velvet-signal | minimal | 9000 /  | page 1 | switch via runtime → reload | 768 | active `velvet-signal`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | business | 9001 /  | page 1 | switch via runtime → reload | 1024 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | business | 9001 /  | page 1 | switch via runtime → reload | 1440 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | business | 9001 /  | page 1 | switch via runtime → reload | 375 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | business | 9001 /  | page 1 | switch via runtime → reload | 768 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | business | 9001 /  | page 2 | switch via runtime → reload | 1440 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-1440.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | business | 9001 /  | page 2 | switch via runtime → reload | 375 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-375.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | business | 9001 /  | page 3 | switch via runtime → reload | 1440 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-1440.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | business | 9001 /  | page 3 | switch via runtime → reload | 375 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-375.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | minimal | 9000 /  | page 1 | switch via runtime → reload | 1024 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | minimal | 9000 /  | page 1 | switch via runtime → reload | 1440 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | minimal | 9000 /  | page 1 | switch via runtime → reload | 375 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| cobalt-press | minimal | 9000 /  | page 1 | switch via runtime → reload | 768 | active `cobalt-press`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | business | 9001 /  | page 1 | switch via runtime → reload | 1024 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | business | 9001 /  | page 1 | switch via runtime → reload | 1440 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | business | 9001 /  | page 1 | switch via runtime → reload | 375 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | business | 9001 /  | page 1 | switch via runtime → reload | 768 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page1-768.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | business | 9001 /  | page 2 | switch via runtime → reload | 1440 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-1440.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | business | 9001 /  | page 2 | switch via runtime → reload | 375 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page2-375.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | business | 9001 /  | page 3 | switch via runtime → reload | 1440 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-1440.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | business | 9001 /  | page 3 | switch via runtime → reload | 375 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-business-page3-375.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | minimal | 9000 /  | page 1 | switch via runtime → reload | 1024 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1024.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | minimal | 9000 /  | page 1 | switch via runtime → reload | 1440 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-1440.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | minimal | 9000 /  | page 1 | switch via runtime → reload | 375 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-375.json` | 0 errors | 0 failed | clean | PASS |
| citrus-pop | minimal | 9000 /  | page 1 | switch via runtime → reload | 768 | active `citrus-pop`, no console errors, no failed requests, AA contrast clean, keyboard menu, persisted | `raw/browser-minimal-page1-768.json` | 0 errors | 0 failed | clean | PASS |

## How to regenerate

```bash
python3 tools/live_matrix.py --connection docker-demo --workspace DEMO --minimal-id 9010 --business-id 9011 --primary dist/<theme>/<theme>-1.0.0.zip --secondary dist/<other>/<other>-1.0.0.zip --apply
python3 tools/browser_matrix.py --theme <theme> --package dist/<theme>/<theme>-1.0.0.zip --minimal-url … --business-url … --business-extra-urls …
scripts/release-check.sh <theme>
```

Run them from a clean tree at the commit the packages were built from; evidence and Markdown commits do not
invalidate the binding (`lib/theme_factory/gitstate.py`), any other change does. `linen`/`solarized-dark` use
consumer apps 9010 (minimal) / 9011 (business); `estate-slate`/`estate-slate-dark` use 9012 (minimal) / 9013
(business), provisioned 2026-09-17; the four bilingual themes use 9000 (minimal) / 9001 (business), provisioned
2026-09-19 via `scripts/provision-consumer-fixtures.sh`.
