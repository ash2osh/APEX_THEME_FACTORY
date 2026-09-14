# Evaluations

Regression scenarios for agent behaviour (spec §62). Each file = one scenario with Given / Expected /
Failure. To run one: give the scenario to a fresh agent session **without** naming the skill, record
what it does (baseline), then with the skill loaded. A skill change is accepted only when the
scenario that motivated it passes and the others still pass (spec §58).

| # | Scenario | Status |
|---|---|---|
| 01 | native-grid-preservation | not yet run |
| 02 | css-scoping | not yet run |
| 03 | alpine-component-structure | not yet run |
| 04 | apex-refresh | not yet run |
| 05 | source-persistence | not yet run |
| 06 | component-reuse | not yet run |
| 07 | token-reuse | not yet run |
| 08 | iris-only | not yet run |
| 09 | runtime-evidence | not yet run |
| 10 | theme-package-routing | defined 2026-09-14 — not yet run |
| 11 | dark-package-coverage | defined 2026-09-14 — not yet run |

Findings whose knowledge or skill change is already applied but whose scenario has not been run stay in
`findings/pending/` (status says so); they move to `accepted/` only after the row above reads *passed* with the
date and the session/transcript that ran it (spec §58 steps 8–10). No scenario has been run yet.
