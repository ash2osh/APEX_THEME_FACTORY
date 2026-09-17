# Evaluations

Regression scenarios for agent behaviour (spec §62). Each file = one scenario with Given / Expected /
Failure. To run one: give the scenario to a fresh agent session **without** naming the skill, record
what it does (baseline), then with the skill loaded. A skill change is accepted only when the
scenario that motivated it passes and the others still pass (spec §58).

| # | Scenario | Status |
|---|---|---|
| 01 | native-grid-preservation | passed 2026-09-14 (current only) — runs/2026-09-14/01-native-grid-preservation-current.md |
| 02 | css-scoping | passed 2026-09-14 (current only) — runs/2026-09-14/02-css-scoping-current.md |
| 03 | alpine-component-structure | passed 2026-09-14 (current only) on authoring structure; investigation found `alpine.min.js` itself was never loaded by `application.apx` (real fix on a separate branch/PR) — runs/2026-09-14/03-alpine-component-structure-current.md |
| 04 | apex-refresh | **UNVERIFIED** 2026-09-16 (live Chrome) — the deployed fixture cannot refresh at all: its Dynamic Content region prints with `sys.htp.p`, so the envelope's `result` is `null`, no DOM is swapped and `apexafterrefresh` never fires (confirmed independently by the grader). The Alpine component itself measured clean over 4 DOM swaps. Needs the `.apx` fix imported, then one real refresh — runs/2026-09-16/04-apex-refresh-current.md |
| 05 | source-persistence | **UNVERIFIED** 2026-09-16 (live Chrome) — prototype → source → `sync-static.sh` → validate all demonstrated live, and the evaluee stated the running app still serves the old build; the reload-with-no-injection half of `Expected` needs an import, which this session was forbidden to run — runs/2026-09-16/05-source-persistence-current.md |
| 06 | component-reuse | passed 2026-09-14 (current only) — runs/2026-09-14/06-component-reuse-current.md |
| 07 | token-reuse | passed 2026-09-14 (current only) — runs/2026-09-14/07-token-reuse-current.md |
| 08 | iris-only | passed 2026-09-14 (current only) — runs/2026-09-14/08-iris-only-current.md |
| 09 | runtime-evidence | **passed 2026-09-16** (live Chrome, current only) — real DOM dumped and `document.styleSheets` walked before any CSS was written, restyle prototyped and measured in the page, every class independently re-verified by the grader — runs/2026-09-16/09-runtime-evidence-current.md |
| 10 | theme-package-routing | passed baseline / passed current 2026-09-14 (corrected: sync-static.sh permitted; current run has a noted DB-compliance caveat, routing behavior unaffected) — runs/2026-09-14/10-theme-package-routing-{baseline,current}-sync-permitted.md |
| 11 | dark-package-coverage | **FAILED 2026-09-16** (live Chrome; the verdict is on the package, not the evaluee) — 24-page AA audit plus the interaction states a resting sweep cannot see found 4 package-caused defects in solarized-dark 1.0.0 as built, worst 1.06:1 on Interactive Grid row selection (grader-confirmed). Fixes exist only as the patch quoted in the run log — runs/2026-09-16/11-dark-package-coverage-current.md | **Follow-up 2026-09-17:** all four defects fixed in `sample-themes/solarized-dark/css/**` (the evaluee's own A/B-measured CSS, which its worktree was not allowed to commit) and verified on the rebuilt, installed package in consumer 9011: Interactive Grid row selection 1.06:1 → **10.61:1**, and the JET chart text the evaluation could not test at all → **13/13 nodes pass** (10.61:1 / 4.86:1). The project's audit snippet, which could not see SVG `fill`, was fixed too. The scenario stays **FAILED** until its own 24-page sweep is re-run against the fixed build — the verdict is on the package as it was, and re-running it is the remaining work.
| 12 | apexlang-static-id | passed baseline / passed current 2026-09-14 — runs/2026-09-14/12-apexlang-static-id-{baseline,current}.md |
| 13 | cards-render-event | passed baseline 2026-09-14 (corrected isolation) / passed current 2026-09-14 — runs/2026-09-14/13-cards-render-event-baseline-eda510d.md, runs/2026-09-14/13-cards-render-event-current.md |
| 14 | theme-style-scope | **passed baseline / passed current 2026-09-16** — first validly matched pair (one task, one neutral `Given`). Both sides override `--a-field-input-border-*` on the theme-style scope, neither at `:root`, neither as a property override; the doc/skill text is therefore *not* load-bearing — runs/2026-09-16/14-theme-style-scope-{baseline,current}.md |

### Standardized Execution Modes (2026-09-15)

To eliminate prompt contradictions (such as forbidding DB access while requesting compilation validation), all evaluation scenarios declare one of two explicit modes before dispatch:
- **`OFFLINE`**: Do not connect to Oracle and do not run `scripts/apex-validate.sh`; source checks remain UNVERIFIED for compilation.
- **`CONNECTED`**: You may run `scripts/apex-validate.sh` using `docker-demo` to validate APEXLang source; do not import or make database changes. Live browser tests connect Chrome DevTools MCP to `localhost:8181`.

Findings whose knowledge or skill change is already applied but whose scenario has not been run stay in
`findings/pending/` (status says so); they move to `accepted/` only after the row above reads *passed* with the
date and a run log documenting it (spec §58 steps 8–10).

**Evidence caveat** (added 2026-09-14 after PR #4 review, P2): the `runs/2026-09-14/*.md` files are **not**
full session transcripts or complete patches — each is a curated record (the exact evaluee prompt, the
evaluee's own final-report text quoted verbatim, `git diff --stat`, and the grader's verdict + reasoning). The
evaluee worktrees were deliberately reset (`git checkout -- . && git clean -fd`) between runs to prevent one
scenario's edits from contaminating the next, so the actual full patches and any seeded fixtures no longer
exist on disk and cannot be independently re-diffed from this repository — only from what's quoted in each
log. Treat specific claims in a run log (exact selectors, handler-cleanup logic, a seeded fixture's contents)
as *reported*, not independently re-verifiable after the fact. For any future evaluation run: capture the full
`git diff` (not just `--stat`) and any seeded fixture files into the run log, or copy the worktree's diff to a
patch file alongside it, **before** resetting — that's the gap this caveat exists to flag.

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

**2026-09-14 correction, round 4** (a further PR #4 review pass caught one more overclaimed verdict, a
different flavor than round 3): scenario 04's current-worktree run delivered only a new, standalone Alpine
component — no APEXLang region/Dynamic Action wiring it into an actual refreshable target, so the
duplicate-handler/reinit claims were never exercised against a real refresh; separately, its state-resync
mechanism (DOM markup + a generic ajax call) doesn't match Expected's specific "from the APEX item" wording.
Corrected to ambiguous — this one needs both a real `.apx` wiring *and* a live Chrome session, not Chrome
alone, so it's a distinct gap from round 3's scenarios.

**2026-09-14 correction, round 5** (a further PR #4 review pass caught a different kind of problem, in scenario
14 rather than the promoted findings): the baseline run tested the scenario file's *original* wording (restyle
buttons — a no-op at this commit, per its own log) while the current-worktree run substituted a *different*
task (form-field borders) to get a real differentiator. Nobody had updated the scenario file itself, so
`14-theme-style-scope.md`'s canonical Expected/Failure still described buttons even though nothing was ever
validly tested against it as a matched pair. Fixed: updated the scenario file to make the form-field task
canonical (documenting why buttons was dropped), and corrected both run logs and the finding's Status line to
say plainly that baseline and current tested different tasks — not "both passed, not load-bearing" but "never
validly compared at all." `2026-09-13-theme-style-scope-token-overrides` needs a fresh baseline14 run against
the now-canonical form-field prompt before any promotion decision can be made.

**2026-09-14 correction, round 6** (a further PR #4 review pass, three separate findings):
- Scenario 10's corrected current-worktree run executed `scripts/apex-validate.sh`, which does connect to a
  database (`sql -name "$CONN"`) — violating the same "do not connect to the database" instruction its
  corrected baseline counterpart explicitly read the script's source and refused to run over. Both were graded
  PASS without flagging the difference. Noted the compliance gap in the run log; the theme-package-routing
  behavior itself (what scenario 10 actually tests) is unaffected, since it doesn't depend on `apex-validate.sh`
  having run.
- Scenario 14's `Given` — even after round 5's task fix — still stated the exact scoping conclusion
  ("overriding on body.apex-theme-iris restyles every instance while modifiers keep precedence...") before
  posing the task, in both the baseline and current-worktree prompts. Neither PASS verdict actually
  demonstrated unaided skill behavior. Rewrote `Given` to describe only the environment (where atoms and
  modifiers are declared), not the scoping answer, and downgraded both existing runs to ambiguous.
- Separately (not a bug, but worth recording): scenario 14's form-field fix is scoped to the `linen` package
  and does not reach the app's "Iris (no theme package)" fallback state. Verified this is intentional — the
  project's architecture routes app-wide restyles through packages, and the no-package option exists
  specifically to offer *unmodified* Iris — documented in the run log rather than treated as a gap.

**2026-09-15 correction, round 7** (a further PR #4 review pass, four separate findings):
- **Systemic**: the standard evaluee-prompt template used across nearly every run in this matrix says both
  "do not connect to the database" *and* "you may... run scripts/apex-validate.sh" — but that script connects
  to a database (`sql -name "$CONN"`). Round 6 caught and noted this for scenario 10 specifically; fresh
  evidence shows the same contradiction, and the same silent violation (the evaluee ran it anyway, reported
  "Validation successful", and was graded PASS without the conflict being flagged), recurs in scenarios 02, 05,
  and both scenario-12 runs — almost certainly more across the matrix, since it's the template, not a
  per-scenario choice. This is recorded here as a **systemic template defect** rather than patched into every
  individual run log (impractical at this scale, and the underlying CSS/APEXLang conclusions those runs reach
  don't depend on whether `apex-validate.sh` happened to succeed) — any future run of this matrix should either
  explicitly permit database access or provide a genuinely offline validation path, not both forbid and permit
  it in the same prompt.
- Investigated a related question on scenario 03: confirmed `applications/ut/application.apx` never actually
  loads `alpine.min.js`, so no Alpine component anywhere in this project could ever have functioned — not
  specific to the evaluated stepper component. Real fix (adding the file URL, validated) lands on a separate
  branch, since it's an application bug, not an evaluation-methodology one.
- Scenarios 12 and 13 each only exercise part of the finding they were built to test (12: the `htmlDomId`
  question only, not the app-level file-routing correction; 13: the Cards-render-event question only, not the
  two navigation-menu corrections). Narrowed both scenarios' `Expected`/`Failure` to match what the task
  actually tests, with an explicit note on what remains uncovered.
- Scenario 08's package-assembly gap (the `redwood-density` sample was never run through `scripts/sync-static.sh`)
  was checked against the scenario's own `Expected` line, which asks only for the *technique* (scoped `.app-*`
  CSS, not `:root`, no Theme Roller, documented reasoning) in response to a stakeholder suggestion — unlike
  scenario 10, it does not require the result to be assembled or selectable. The evaluee's own summary was
  explicit that assembly/import was left undone. PASS verdict unchanged; see the run log for the distinction
  from scenario 10's stricter Expected line.

**Net result**: none of the three findings originally promoted from this evaluation run survived scrutiny.
`2026-09-14-theme-packages-routing` and `2026-09-14-apex-widget-events` were tested to completion on a properly
isolated, fully-resourced, neutrally-prompted re-run and didn't show a load-bearing effect.
`2026-09-14-ut-literal-root-tokens` was never actually tested to completion at all — every attempt hit the same
missing ingredient (live Chrome) this whole evaluation matrix lacks. `2026-09-13-theme-style-scope-token-overrides`
(scenario 14) was never validly tested either, for two compounding reasons — mismatched tasks, and a `Given`
that gave away the answer. All findings from this run remain pending; the underlying knowledge in each is
still considered accurate. This evaluation matrix turned out to have more structural problems than skill-text
problems: baseline isolation / evaluee-prompt neutrality and permissions (rounds 1–2), no evaluee anywhere
having Chrome access despite some `Expected` lines literally requiring a live pass (rounds 3–4, 9's original
miscall), a scenario definition and its own `Given` drifting out of sync with what was actually tested (rounds
5–6), one evaluee not complying with a stated constraint the other side did comply with (round 6), a
contradictory database instruction baked into the shared prompt template across most of the matrix, and two
scenarios only partially exercising the finding they were meant to validate (round 7). Scenarios 04, 05, 09, 11
and 14 remain open pending a Chrome-enabled and/or properly re-scoped re-run (04 also needs real APEXLang
wiring; 14 needs fresh runs against the rewritten `Given`) — scenarios 08's and 13's PASS verdicts stand for
what their (now explicitly narrowed, for 13) `Expected` lines actually ask, and scenario 10's PASS verdicts
stand for the routing behavior under test despite the noted compliance gap.

**2026-09-15 update, round 8** (Task 5: Evidence-completeness checklists and protocol hardening):
- Added explicit evidence-completeness checklists (permitted tools, prohibited writes, exact fixture target, required artifacts, verdict rules) to scenarios 04, 05, 09, 11, and 14.
- Replaced the contradictory "no DB + run apex-validate.sh" instruction with standardized `OFFLINE` and `CONNECTED` execution modes.
- Page 409 (`applications/ut/pages/p00409-theme-factory-lifecycle.apx`) and `themeFactoryDisclosure.js` committed as the real declarative refresh fixture for scenario 04.
- Pending live browser execution via Chrome DevTools MCP and live database import authorization, scenarios 04, 05, 09, 11, and 14 remain explicitly marked UNVERIFIED, naming the exact missing runtime evidence.


## 2026-09-16 run — the five Chrome-gated scenarios, finally run with Chrome

Six evaluee runs (04, 05, 09, 11 current; 14 current **and** baseline), one fresh agent each, none told which
skill was under test, each in its own `git worktree` at `4fc73b8` (baseline 14 at `97a3354`). Browser access
went through the project Chrome MCP daemon (`tools/chrome_devtools_client.py`), each evaluee in its own
background tab, the user's tab untouched, no `#theme=` navigation. No import, no install, no DB change: the
only database contact permitted was the read-only `scripts/apex-validate.sh`, and the `CONNECTED` mode text
says so, which removes the forbid-and-permit contradiction round 7 recorded as a systemic template defect.

| # | Verdict | One-line reason |
|---|---|---|
| 04 | UNVERIFIED | the fixture itself cannot refresh — `sys.htp.p` region, `result: null`, `apexafterrefresh` never fires |
| 05 | UNVERIFIED | persistence half proven live; reload-without-injection needs an import this session may not run |
| 09 | **PASS** | DOM and matching rules read live before any CSS; every selector re-verified by the grader |
| 11 | **FAIL** | live audit found 4 package-caused AA defects in `solarized-dark` 1.0.0 as built, worst 1.06:1 |
| 14 | **PASS / PASS** | matched neutral pair; both sides scope the atom override correctly, so the text is not load-bearing |

What changed methodologically, against the six traps in `knowledge/pitfalls.md` §6:
- **§6.1 baseline isolation** — 14's baseline is `97a3354`, the parent of `43eec93`, verified before the run to
  contain neither the `DESIGN_SYSTEM.md` §1 bullet nor the finding it came from.
- **§6.2 prompt neutrality** — no prompt states a technique, a class name, a token family or a page range. The
  evaluee prompts are quoted in full in each run log, with a neutrality note naming what was deliberately
  withheld. `.agents/evaluations/` was placed out of scope for every evaluee, so none could read its own
  Verdict Rule.
- **§6.3 contradictory permissions** — resolved by the `OFFLINE`/`CONNECTED` modes: OFFLINE runs were told not
  to run `apex-validate.sh` at all; CONNECTED runs were told they may, and that it connects.
- **§6.4 untestable clauses** — where a Verdict-Rule clause was only partly reachable (09's "link to the
  APEXLang region"), the run log says so explicitly and the grader completed the missing half itself rather
  than letting the PASS imply it.
- **§6.5 verdict sweep** — each verdict appears in exactly three places (run-log heading, the row above, the
  affected finding's Status line) and they were reconciled after grading.
- **§6.6 worktree evidence** — every run log embeds the **full** `git diff` plus the contents of any untracked
  file, captured before the worktree was removed. The 2026-09-14 evidence caveat above does **not** apply to
  `runs/2026-09-16/`: those logs can be re-applied and re-diffed.

Two results matter beyond their scenarios:
- **Scenario 11 is a release blocker.** `sample-themes/solarized-dark/` — and therefore
  `dist/solarized-dark/solarized-dark-1.0.0.zip` and the Layer C/D evidence captured against it — contains
  four measured package-caused AA failures, the worst of which makes a selected Interactive Grid row
  unreadable (1.06:1). The corrective patch is quoted in the run log but was **not** applied: this session was
  not permitted to edit `sample-themes/`.
- **Scenario 04's fixture has never worked.** Page 409 was committed in round 8 as "the real declarative
  refresh fixture"; it cannot refresh, and nothing noticed until a live run. See
  `findings/pending/2026-09-16-dynamic-content-htp-p-cannot-refresh.md`.

Finding dispositions from this run are in `findings/accepted/`, `findings/rejected/` and the Status lines of
what remains in `findings/pending/`.
