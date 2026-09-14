# Finding

Status:
Accepted (2026-09-14 — evaluation 10 passed, see evaluations/runs/2026-09-14/10-theme-package-routing-current.md; baseline failed, see evaluations/runs/2026-09-14/10-theme-package-routing-baseline.md)

Category:
APPLICATION-CONVENTION

Confidence:
CONFIRMED

APEX Version:
26.1.4 (Universal Theme / Iris)

Page:
app-wide

Component:
`sample-themes/<name>/css/**`, `static-files/css/app.css` `@themes` block, `scripts/sync-static.sh`

## Observation

Since commit `1f882d7` (2026-09-13) app-wide restyles are **theme packages**: `sample-themes/<name>/css/tokens.css`
+ `css/apex/*.css`, every rule scoped to `html.app-theme-<name>`, assembled into the export by
`scripts/sync-static.sh` and loaded by the generated `@themes` block of `static-files/css/app.css`. The page-0
bootstrap and the nav-bar Theme menu pick the active package per browser. `static-files/css/` keeps only the
shared foundation, `components/` and `pages/`.

## Evidence

`AGENTS.md` non-negotiables; `sample-themes/README.md`; `scripts/sync-static.sh`; `applications/ut/shared-components/static-files/css/themes/*`.

## Existing Assumption

`apex-css-design-system` routed "all regions / buttons / forms app-wide" to `static-files/css/apex/<component>.css`
(that folder no longer exists) and never mentioned `sample-themes/`, `html.app-theme-*` or `sync-static.sh`;
`design-to-apex` said "files under static-files/".

## Impact

An agent following the skills puts theme CSS in a folder that is not synced or loaded, unscoped to a theme class.

## Proposed Knowledge Change

Routing tables in both skills; a dark-package checklist line (remap Iris' literal `:root` tokens).

## Regression Scenario

Evaluation `10-theme-package-routing.md`.

## Scope

Application-wide convention.
