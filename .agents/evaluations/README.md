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
| 09 | runtime-evidence | ambiguous 2026-09-14 — needs a Chrome-enabled session; not a valid PASS under this matrix's no-Chrome ground rules, corrected after PR #4 review — runs/2026-09-14/09-runtime-evidence-current.md |
| 10 | theme-package-routing | failed baseline / passed current 2026-09-14 — runs/2026-09-14/10-theme-package-routing-{baseline,current}.md |
| 11 | dark-package-coverage | passed baseline / passed current 2026-09-14 (corrected isolation + neutral prompt) — runs/2026-09-14/11-dark-package-coverage-{baseline-eda510d,current-neutral}.md |
| 12 | apexlang-static-id | passed baseline / passed current 2026-09-14 — runs/2026-09-14/12-apexlang-static-id-{baseline,current}.md |
| 13 | cards-render-event | passed baseline 2026-09-14 (corrected isolation) / passed current 2026-09-14 — runs/2026-09-14/13-cards-render-event-baseline-eda510d.md, runs/2026-09-14/13-cards-render-event-current.md |
| 14 | theme-style-scope | passed baseline / passed current 2026-09-14 — runs/2026-09-14/14-theme-style-scope-{baseline,current}.md |

Findings whose knowledge or skill change is already applied but whose scenario has not been run stay in
`findings/pending/` (status says so); they move to `accepted/` only after the row above reads *passed* with the
date and the session/transcript that ran it (spec §58 steps 8–10).

**2026-09-14 evaluation run** (19 evaluee runs, one fresh subagent per run, worktrees at `/tmp/eval/{current,baseline,baseline14}`):
promoted `2026-09-14-theme-packages-routing` (scenario 10) to `findings/accepted/`. Kept pending (baseline also
passed, so the skill change wasn't demonstrated load-bearing): `2026-09-14-apexlang-static-id-is-htmldomid`
(scenario 12), `2026-09-13-theme-style-scope-token-overrides` (scenario 14) — see each finding's Status line
for why. Left untouched per the run's instructions: `2026-09-13-ig-sticky-header-double-line` (no evaluation;
needs runtime verification). Full logs in `runs/2026-09-14/`.

**2026-09-14 correction** (same day, after a Codex PR review on PR #4 caught three real problems with the
run above — see each affected finding's Status line and the `*-eda510d`/`*-neutral` run logs for full detail):
- Scenarios 11 and 13 originally compared against baseline commit `9276369`, which predates `eda510d` —
  the commit that actually introduced the application code (Solarized Dark package; the Cards
  `tablemodelviewpagechange` handler) both scenarios are about. That wasn't isolating the skill-text
  change, it was also missing application code current had. Re-run against the correct isolation point
  (`eda510d`): **both now pass at baseline too.**
- Scenario 11's current-worktree prompt named the exact things to check (literal `:root` tokens, the
  4000/6300 page range), supplying the answer. Re-run with the original neutral prompt: still passes, and
  found an even larger, independently-confirmed set of real gaps than the corrected baseline run.
- Scenario 09 was graded PASS despite its `Expected` explicitly requiring `chrome-devtools-mcp`
  (`list_pages`→`take_snapshot`/`evaluate_script`), which no evaluee in this matrix could use (Chrome is
  off-limits for every evaluee here). Corrected to ambiguous/unresolved — this scenario needs a
  Chrome-enabled session to produce a real verdict.

Consequence: `2026-09-14-ut-literal-root-tokens` (scenario 11) and `2026-09-14-apex-widget-events` (scenario 13)
are **demoted back to `findings/pending/`** — a properly isolated baseline passes both, so the skill change was
not shown load-bearing by this evaluation. Both re-runs surfaced real, currently-unfixed gaps in the shipped
Solarized Dark package; recorded as `findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md` and
partially fixed in PR #5 rather than bulk-applied here from an unverified throwaway-worktree run.
