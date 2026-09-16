# Finding

Status:
**Accepted 2026-09-17** — the convention is live, not just documented: the running app loads
`r/demo/102/files/static/v…/css/app.css` with its generated `@themes` block and applies
`html.app-theme-<name>`, both consumer fixtures carry the same routing with a working switcher (Layer D
evidence, `evaluations/runtime/2026-09-16-release-*/`), and three of the five 2026-09-16 evaluees independently
routed their work through `sample-themes/<name>/css/**` + `scripts/sync-static.sh` without being told to
(scenarios 05, 09, 14).

Promoted for the convention, with the isolation result kept visible: evaluation 10 passes on **both** sides
once `sync-static.sh` is permitted, because `AGENTS.md` already stated the routing at the baseline commit
byte-identically — so the skill-table change is not demonstrated load-bearing. What the 2026-09-16 round did
add is a reason to keep the routing prose sharp: two independent evaluees found the generated export tree
**stale** for `solarized-dark` (`sample-themes/` ahead of
`applications/ut/shared-components/static-files/`), which is exactly the failure mode this finding exists to
prevent, one layer further down. That drift is unfixed and worth a separate pass.

Earlier status, for the record: *Pending (2026-09-15) — missing a scenario isolating the routing guidance
where `AGENTS.md` does not already specify `scripts/sync-static.sh`.*

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
