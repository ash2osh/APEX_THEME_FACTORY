# Finding

Status:
Pending — demoted 2026-09-14 from a premature Accepted, after a second round of PR #4 review (P2) caught two
problems: (1) the original current-worktree run explicitly skipped `scripts/sync-static.sh` — not permitted by
the evaluee prompt — even though the scenario's own Expected line requires it, so no evaluee could actually
complete the expected behavior; (2) `AGENTS.md` itself (read by every evaluee) already stated the
`sample-themes/<name>/css` + `sync-static.sh` routing at baseline commit `9276369`, identical to current —
the original baseline FAIL was the evaluee choosing to hand-edit the generated `@themes` block despite already
having that instruction, not evidence the *skill* text mishandled the scenario. Re-run with
`scripts/sync-static.sh` explicitly permitted (verified safe beforehand: read its source — local file copy +
regex text substitution, no DB/Chrome/network) on both sides: **PASS at baseline**
(evaluations/runs/2026-09-14/10-theme-package-routing-baseline-sync-permitted.md, package correctly assembled
via the script, no hand-edit) **and PASS at current**
(evaluations/runs/2026-09-14/10-theme-package-routing-current-sync-permitted.md). The routing knowledge itself
(the `apex-css-design-system` / `design-to-apex` skill updates) is still accurate and worth keeping; this
scenario just never isolated a real skill-text effect — the discriminator in the original runs was an
evaluee-prompt permission gap, not the skill files. Original (invalid) runs kept for the record:
evaluations/runs/2026-09-14/10-theme-package-routing-{baseline,current}.md.

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
