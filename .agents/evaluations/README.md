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
| 05 | source-persistence | ambiguous 2026-09-14 — reload-and-verify half of Expected needs a Chrome-enabled session, corrected after PR #4 review — runs/2026-09-14/05-source-persistence-current.md |
| 06 | component-reuse | passed 2026-09-14 (current only) — runs/2026-09-14/06-component-reuse-current.md |
| 07 | token-reuse | passed 2026-09-14 (current only) — runs/2026-09-14/07-token-reuse-current.md |
| 08 | iris-only | passed 2026-09-14 (current only) — runs/2026-09-14/08-iris-only-current.md |
| 09 | runtime-evidence | ambiguous 2026-09-14 — needs a Chrome-enabled session; not a valid PASS under this matrix's no-Chrome ground rules, corrected after PR #4 review — runs/2026-09-14/09-runtime-evidence-current.md |
| 10 | theme-package-routing | passed baseline / passed current 2026-09-14 (corrected: sync-static.sh permitted) — runs/2026-09-14/10-theme-package-routing-{baseline,current}-sync-permitted.md |
| 11 | dark-package-coverage | ambiguous both sides 2026-09-14 — isolation and prompt fixed, but the live contrast-audit half of Expected still needs a Chrome-enabled session (2 correction rounds) — runs/2026-09-14/11-dark-package-coverage-{baseline-eda510d,current-neutral}.md |
| 12 | apexlang-static-id | passed baseline / passed current 2026-09-14 — runs/2026-09-14/12-apexlang-static-id-{baseline,current}.md |
| 13 | cards-render-event | passed baseline 2026-09-14 (corrected isolation) / passed current 2026-09-14 — runs/2026-09-14/13-cards-render-event-baseline-eda510d.md, runs/2026-09-14/13-cards-render-event-current.md |
| 14 | theme-style-scope | passed baseline / passed current 2026-09-14 — runs/2026-09-14/14-theme-style-scope-{baseline,current}.md |

Findings whose knowledge or skill change is already applied but whose scenario has not been run stay in
`findings/pending/` (status says so); they move to `accepted/` only after the row above reads *passed* with the
date and the session/transcript that ran it (spec §58 steps 8–10).

**2026-09-14 evaluation run** (19 evaluee runs, one fresh subagent per run, worktrees at `/tmp/eval/{current,baseline,baseline14}`):
promoted `2026-09-14-theme-packages-routing` (scenario 10), `2026-09-14-ut-literal-root-tokens` (scenario 11),
`2026-09-14-apex-widget-events` (scenario 13). Kept pending (baseline also passed, so the skill change wasn't
demonstrated load-bearing): `2026-09-14-apexlang-static-id-is-htmldomid` (scenario 12),
`2026-09-13-theme-style-scope-token-overrides` (scenario 14). Left untouched per the run's instructions:
`2026-09-13-ig-sticky-header-double-line` (no evaluation; needs runtime verification). Full logs in
`runs/2026-09-14/`.

**2026-09-14 correction, round 1** (Codex PR review on PR #4 caught three real problems with the run above —
see each affected finding's Status line and the `*-eda510d`/`*-neutral` run logs for full detail):
- Scenarios 11 and 13 originally compared against baseline commit `9276369`, which predates `eda510d` —
  the commit that actually introduced the application code (Solarized Dark package; the Cards
  `tablemodelviewpagechange` handler) both scenarios are about. Re-run against the correct isolation point
  (`eda510d`): **both now pass at baseline too**, so `2026-09-14-ut-literal-root-tokens` and
  `2026-09-14-apex-widget-events` were **demoted back to `findings/pending/`**.
- Scenario 11's current-worktree prompt named the exact things to check (literal `:root` tokens, the
  4000/6300 page range), supplying the answer. Re-run with the original neutral prompt: still passes, and
  found an even larger, independently-confirmed set of real gaps than the corrected baseline run. Not present
  in this branch/PR — recorded and partially fixed on the separate branch
  `fix-solarized-dark-contrast-followups` (PR #5, `findings/pending/2026-09-14-solarized-dark-2page-coverage-gap.md`
  on that branch), rather than bulk-applied here from an unverified throwaway-worktree run or mixed into this
  evaluation-methodology branch.
- Scenario 09 was graded PASS despite its `Expected` explicitly requiring `chrome-devtools-mcp`
  (`list_pages`→`take_snapshot`/`evaluate_script`), which no evaluee in this matrix could use (Chrome is
  off-limits for every evaluee here). Corrected to ambiguous/unresolved — this scenario needs a
  Chrome-enabled session to produce a real verdict.

**2026-09-14 correction, round 2** (same PR, a second review pass on the round-1 commit caught scenario 10 too):
`AGENTS.md` itself (not just the `.agents/skills/` files) already stated the `sample-themes/<name>/css` +
`scripts/sync-static.sh` routing at baseline commit `9276369`, byte-identical to current — the original
baseline FAIL was the evaluee hand-editing the generated `@themes` block *despite already having that
instruction*, because the evaluee prompt never permitted running `sync-static.sh` (which the scenario's own
Expected line requires). Re-run with that permission restored on both sides (verified safe first — read the
script's source: local file copy + regex substitution, no DB/Chrome/network): **both now pass**, with no
hand-editing. `2026-09-14-theme-packages-routing` is **demoted back to `findings/pending/`** — see its Status
line.

**2026-09-14 correction, round 3** (a further PR #4 review pass, after rounds 1–2 were pushed, caught two more
overclaimed verdicts — same underlying class of error as scenario 09's original miscall, just not caught
there the first time):
- Scenario 05's `Expected` line requires reload-and-re-verify, not just a source edit — no evaluee here has
  Chrome, so that half was never exercised. Corrected to ambiguous.
- Scenario 11's `Expected` line requires the live contrast audit reporting 0 failures, which round 1's fix
  (isolation + neutral prompt) never addressed — both corrected runs are source-level substitutes, not the
  live audit itself. Corrected **both** to ambiguous. This changes *why* `2026-09-14-ut-literal-root-tokens`
  stays pending: not "baseline also passed, so not load-bearing" (round 1's framing) but "neither side could be
  validly completed at all" — a genuinely unresolved scenario, not a demonstrated non-effect. See the finding's
  Status line for the corrected reasoning.

**Net result**: none of the three findings originally promoted from this evaluation run survived scrutiny.
`2026-09-14-theme-packages-routing` and `2026-09-14-apex-widget-events` were tested to completion on a properly
isolated, fully-resourced, neutrally-prompted re-run and didn't show a load-bearing effect.
`2026-09-14-ut-literal-root-tokens` was never actually tested to completion at all — every attempt hit the same
missing ingredient (live Chrome) this whole evaluation matrix lacks. All three remain pending; the underlying
knowledge in each is still considered accurate. Two structural gaps in this matrix, not the skills, are what
actually failed here: baseline isolation / evaluee-prompt neutrality and permissions (rounds 1–2), and no
evaluee anywhere in this matrix having Chrome access despite some scenarios' `Expected` lines literally
requiring a live pass (round 3, plus the original scenario 09 miscall). Scenarios 05, 09 and 11 specifically
remain open on that basis — scenario 13's `Expected` is a code-correctness check only (the right event/guard/
API), not a runtime-verification requirement, so its PASS verdicts stand as graded.
