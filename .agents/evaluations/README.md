# Evaluations

Regression scenarios for agent behaviour (spec §62). Each file = one scenario with Given / Expected /
Failure. To run one: give the scenario to a fresh agent session **without** naming the skill, record
what it does (baseline), then with the skill loaded. A skill change is accepted only when the
scenario that motivated it passes and the others still pass (spec §58).

| # | Scenario | Status |
|---|---|---|
| 01 | native-grid-preservation | passed 2026-09-14 (current only) — runs/2026-09-14/01-native-grid-preservation-current.md |
| 02 | css-scoping | passed 2026-09-14 (current only) — runs/2026-09-14/02-css-scoping-current.md |
| 03 | alpine-component-structure | passed 2026-09-14 (current only) — runs/2026-09-14/03-alpine-component-structure-current.md |
| 04 | apex-refresh | passed 2026-09-14 (current only) — runs/2026-09-14/04-apex-refresh-current.md |
| 05 | source-persistence | passed 2026-09-14 (current only) — runs/2026-09-14/05-source-persistence-current.md |
| 06 | component-reuse | passed 2026-09-14 (current only) — runs/2026-09-14/06-component-reuse-current.md |
| 07 | token-reuse | passed 2026-09-14 (current only) — runs/2026-09-14/07-token-reuse-current.md |
| 08 | iris-only | passed 2026-09-14 (current only) — runs/2026-09-14/08-iris-only-current.md |
| 09 | runtime-evidence | passed 2026-09-14 (current only) — runs/2026-09-14/09-runtime-evidence-current.md |
| 10 | theme-package-routing | failed baseline / passed current 2026-09-14 — runs/2026-09-14/10-theme-package-routing-{baseline,current}.md |
| 11 | dark-package-coverage | ambiguous baseline / passed current 2026-09-14 — runs/2026-09-14/11-dark-package-coverage-{baseline,current}.md |
| 12 | apexlang-static-id | passed baseline / passed current 2026-09-14 — runs/2026-09-14/12-apexlang-static-id-{baseline,current}.md |
| 13 | cards-render-event | failed baseline / passed current 2026-09-14 — runs/2026-09-14/13-cards-render-event-{baseline,current}.md |
| 14 | theme-style-scope | passed baseline / passed current 2026-09-14 — runs/2026-09-14/14-theme-style-scope-{baseline,current}.md |

Findings whose knowledge or skill change is already applied but whose scenario has not been run stay in
`findings/pending/` (status says so); they move to `accepted/` only after the row above reads *passed* with the
date and the session/transcript that ran it (spec §58 steps 8–10).

**2026-09-14 evaluation run** (19 evaluee runs, one fresh subagent per run, worktrees at `/tmp/eval/{current,baseline,baseline14}`):
promoted `2026-09-14-theme-packages-routing` (scenario 10), `2026-09-14-ut-literal-root-tokens` (scenario 11),
`2026-09-14-apex-widget-events` (scenario 13) to `findings/accepted/`. Kept pending (baseline also passed, so
the skill change wasn't demonstrated load-bearing): `2026-09-14-apexlang-static-id-is-htmldomid` (scenario 12),
`2026-09-13-theme-style-scope-token-overrides` (scenario 14) — see each finding's Status line for why. Left
untouched per the run's instructions: `2026-09-13-ig-sticky-header-double-line` (no evaluation; needs runtime
verification). Full logs in `runs/2026-09-14/`.
