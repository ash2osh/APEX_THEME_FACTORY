# Run: 11-dark-package-coverage — post-import re-sweep

Scenario file: `.agents/evaluations/11-dark-package-coverage.md`
Execution mode: **CONNECTED** (live Chrome via the project daemon, own tab, restored afterwards)
Repository: `/home/ash/projects/APEX_THEME_FACTORY` at `74ab569` + the `sync-static.sh` output the user
imported on 2026-09-17
Package under test: `solarized-dark` **as built and imported today** — the fixes the 2026-09-16 evaluee could
only inject are now in `sample-themes/solarized-dark/css/**` and in the database
Measured by: this session (grader). Not a fresh evaluee run — the evaluee half ran on 2026-09-16
(`runs/2026-09-16/11-dark-package-coverage-current.md`); **this scenario's verdict is about the package, not
about the evaluee**, which is why re-running the sweep is what changes it.
Date: 2026-09-17

## Whose measurement this is

Stated because it matters to how much this run is worth: **the same session that applied the fixes measured
them.** The CSS came from the 2026-09-16 evaluee's own A/B-measured patch (quoted in its run log; its worktree
could not commit), was re-applied here on 2026-09-17, and is graded here. That is not the evaluee/grader
separation the 2026-09-16 round had.

What limits the damage: every number below is a mechanical measurement anyone can re-take with the snippet in
`docs/CHROME_DEVTOOLS_MCP.md` against the running app, the bare-Iris A/B in §4 is a falsifiable control that
would expose a package regression being mis-attributed to Universal Theme, and the instrument's own blind spot
(SVG `fill`) was fixed *before* this sweep, which is why p1902 could fail here rather than read as clean. What
it does not substitute for: an independent agent re-running the scenario end to end.

## Why this run exists

The 2026-09-16 verdict was FAIL, on the package: four package-caused defects, worst **1.06:1** on Interactive
Grid row selection. Its "still needed" line was explicit — *import, reload, re-run the sweep (p1902 above all),
extend the audit to read SVG `fill`*. The audit instrument was fixed on 2026-09-17
(`tools/browser_matrix.py` / `docs/CHROME_DEVTOOLS_MCP.md`, with a regression test in
`tests/test_browser_matrix.py::ContrastInstrumentTests`); the user imported on 2026-09-17. This is the re-run.

## 1. Resting sweep — 24 pages, 1440×900

Same page list as 2026-09-16, same documented snippet, now SVG-aware. All 24 pages carried
`html class="… app-theme-solarized-dark"`.

**7 failures across 24 pages, 0 of them package-caused.** Every page not listed measured 0.

| Page | Failures | Worst | Owner |
|---|---|---|---|
| p1304 badges-list | 2 | 2.94:1, 3.70:1 — `span.t-BadgeList-value`, white on `rgb(222,127,17)` / `rgb(180,114,130)` | UT literal (`--u-color-*`) |
| p1800 calendars | 5 | 2.10:1 ×5 — `div.fc-event-title`, white on `rgb(46,204,113)` | APEX literal `#2ecc71` (`app_ui-Core.min.css`) |

Both were already recorded as not-package-owned on 2026-09-16, and both are now proven so by A/B rather than
by attribution alone (§4).

The two resting-state package defects from 2026-09-16 are gone:

| Where | 2026-09-16 | 2026-09-17 |
|---|---|---|
| p1411 Faceted Search `Show All` / `Clear All` | 2.39:1 | **0 failures on the page** |
| p1906 MapLibre attribution + links | 2.57:1 | **12.25:1** both, plate `rgba(0,43,54,.75)` |

## 2. The states a resting sweep cannot see — where the FAIL came from

**Interactive Grid row selection (p1410)** — the headline defect. Same first body cell, clicked:

```json
{"html":"page-1410 app-UT app-theme-solarized-dark",
 "before":{"text":"Decommission servers","color":"rgb(238, 232, 213)","ownBg":"rgb(7, 54, 66)","ratio":10.61,"classes":"a-GV-cell u-tS is-readonly"},
 "after":{"text":"Decommission servers","color":"rgb(238, 232, 213)","ownBg":"rgba(42, 161, 152, 0.18)","resolvedBg":"rgb(13, 73, 81)","ratio":8.17,"classes":"a-GV-cell u-tS is-readonly is-focused"},
 "rowClasses":"a-GV-row is-readonly is-selected","rowSelected":true}
```

**1.06:1 → 8.17:1.** The cell's own background is now the package's `--app-accent-shade`
(`rgba(42,161,152,.18)`) instead of Iris' literal `#e4f1f7`. Captured to `assets/p1410-ig-row-selected.png` (not committed — `.gitignore` excludes `.agents/**/*.png`).

**Oracle JET charts (p1902)** — the defect that was *fixed in source but unverifiable* on 2026-09-16, because
JET bakes its colours at bootstrap. Measured with the SVG-aware audit, 8.5 s settle:

```json
{"page":"1902","svgCount":6,"svgTextNodes":25,
 "fills":{"rgb(238, 232, 213)":5,"rgb(147, 161, 161)":20},
 "failures":0,
 "worst":[{"label":"0","fill":"rgb(147, 161, 161)","ratio":4.86,"need":4.5,"pass":true}, …],
 "ojPrimary":"#eee8d5","ojSecondary":"#93a1a1"}
```

**25 of 25 nodes pass**, worst 4.86:1. On 2026-09-16 **24 of 25** measured 1.46–1.62:1, painted
`rgba(0,0,0,.65)` / `rgb(0,0,0)` — the `:root` values of `--oj-core-text-color-secondary` / `-primary`. The
fills are now exactly the package's base1 / base2. Captured to `assets/p1902-jet-charts.png` (not committed, same rule). The source comment
in `tokens.css` that read `NOT RUNTIME-VERIFIED` has been replaced with this measurement.

**Date picker current day (p1601)**, all 35 day cells of the inline picker:

```json
{"total":35,
 "worst":{"day":"30","cls":"is-disabled","color":"rgb(238, 232, 213)","ownBg":"rgba(0, 0, 0, 0)","resolvedBg":"rgb(7, 54, 66)","ratio":10.61},
 "special":[{"day":"17","cls":"is-current","color":"rgb(238, 232, 213)","ownBg":"rgba(0, 0, 0, 0)","resolvedBg":"rgb(7, 54, 66)","ratio":10.61}]}
```

The current day is no longer a light `#e4f1f7` chip (5.43:1 — AA-passing and still wrong); it takes the card
ground at **10.61:1**, and no day cell in the picker measures below that.

**Modal dialog (p1910 → p1912 in its iframe)**: opened for real ("Dialog with Auto Size"), then the documented
audit run **inside** the iframe document — `{"page":"1912","html":"page-1912 app-UT app-theme-solarized-dark","failures":0,"sample":[]}`,
body `rgb(0,43,54)`, title `rgb(253,246,227)`. `horizontalOverflow: 0`.

## 3. 375×812

p500, p1402, p1410, p1411 re-swept at 375 with device scale 2: **0 failures each**, theme class present on all
four.

## 4. Bare-Iris A/B — separating baseline defects from package regressions

Required Artifact Checklist item 4. On each page the same nodes were measured with the package class on the
document element, then with it removed, then restored:

| p1304 `.t-BadgeList-value` | with package | bare Iris |
|---|---|---|
| "31" | 2.94:1, white on `rgb(222,127,17)` | **2.94:1, white on `rgb(222,127,17)`** |
| "15" | 3.70:1, white on `rgb(180,114,130)` | **3.70:1, white on `rgb(180,114,130)`** |
| "12" / "188" / "34" / "3" | 7.44 / 9.09 / 9.84 / 11.23 | identical |

| p1800 `.fc-event-title` | with package | bare Iris |
|---|---|---|
| "Plan migration schedule" (+4 more) | 2.10:1, white on `rgb(46,204,113)` | **2.10:1, white on `rgb(46,204,113)`** |
| "Early Adopter Release" | 5.06:1 | identical |

Every value is byte-identical with and without `html.app-theme-solarized-dark`. Both failure groups are
Universal Theme / APEX literals that the package scope does not touch, and neither is a package regression.

## 5. Against the Verdict Rule

- **0 package-caused WCAG AA failures across all tested surfaces** — 24 pages at 1440, 4 at 375, the dialog
  iframe, and the three interaction states that a resting sweep structurally cannot reach.
- **Literal `:root` tokens remapped under `html.app-theme-solarized-dark`** — verified live, not by source
  reading: `--a-palette-primary-shade` resolves to `rgba(42,161,152,.18)` on the element scope while `:root`
  still holds `#e4f1f7`; `--a-base-link-text-color` to `#4b9fda`; `--oj-core-text-color-primary/-secondary` to
  `#eee8d5` / `#93a1a1` on the html scope.
- **Bare-Iris baseline defects separated and documented** — §4.
- Console clean on every page swept; `injectedStyleTags: 0` (nothing measured here comes from injection).

## Verdict: PASS

The package as built and installed no longer produces a single package-caused AA failure on the scenario's
surfaces, and the four defects that produced the 2026-09-16 FAIL are each measured fixed, including the one
(JET) that could not be observed at all before an import existed.

## Still outside this run's evidence — unchanged by it

Carried forward verbatim from 2026-09-16, because re-running the sweep does not extend its scope:

- 98 of app 102's 122 pages were not opened; 1024 and 768 were not swept in app 102 (they are covered for the
  consumer apps by Layer D).
- IRR / Card View / Media List / Timeline / Comments **selection** states were not driven individually. They
  share the `--a-palette-*` chain whose fix is measured on the Interactive Grid, but that is inference, not
  measurement.
- Keyboard focus rings and chip/error states beyond those listed were not exercised.

These are the reasons `.agents/findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md` is promoted
with its residual-coverage list intact rather than deleted.
