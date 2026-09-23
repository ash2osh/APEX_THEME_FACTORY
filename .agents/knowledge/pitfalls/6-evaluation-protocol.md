# Pitfalls §6 — Evaluation protocol (spec §58/§62) — traps from the evaluation rounds

Part of the [pitfalls index](../pitfalls.md); entry numbers are stable and cited as `pitfalls §6.N`.

## 6. Evaluation protocol (spec §58/§62) — traps from the evaluation rounds

The first full run of the evaluation matrix (19 evaluee runs) needed **seven separate PR-review correction
rounds** before its conclusions held up (see `evaluations/README.md`'s correction log for the blow-by-blow).
Every round was a different flavour of the same underlying problem: something about how the scenario was run
made a PASS verdict claim more than the run actually demonstrated. None of it was about the skills under test —
all of it was about the evaluation harness itself. Six reusable traps, plus §6.7 from the 2026-09-17
post-import round:

### 6.1 A baseline commit must predate the *code/instruction under test*, not just the finding
- **Symptom:** compared scenario 13 (Cards render event) against baseline commit `9276369` because it predates
  the *finding*. But the actual correct handler (`tablemodelviewpagechange`) had already landed in application
  code at `eda510d`, a later commit still before the finding — so `9276369` was missing the handler entirely,
  not just missing the skill-text fix. The "baseline FAIL" this produced showed "no handler exists yet",
  not "the old skill text produces the wrong handler".
- **Fix:** find the exact commit that introduced the application-code side of what's being tested
  (`git log -S"the specific string" -- path`) and isolate the baseline *there*, not at an earlier commit that
  merely predates the knowledge file. Verify with `git show <commit>:<file> | grep <the-fix>` on both sides
  before trusting the pairing.

### 6.2 Never build an evaluee prompt by quoting a finding's `Given` verbatim if it states the conclusion
- **Symptom:** scenario 14's `Given` (built from the finding's own observational text, per spec's own
  instruction to reuse it) included *"overriding the base atoms on body.apex-theme-iris restyles every instance
  while all modifiers keep precedence"* — literally the scoping answer the scenario exists to test whether the
  evaluee reaches unaided. Both baseline and current runs were hand-fed the conclusion before being asked to
  apply it; neither PASS proved anything about unaided skill behaviour.
- **Fix:** a finding's `Given` records *what was learned*; a scenario's `Given` may only state *the environment*
  (where things live, what the constraints are) — never the technique that follows from it. When adapting a
  finding into a scenario, actively rewrite the sentence that names the fix; don't just copy the finding text
  in because the process doc said to reuse it.

### 6.3 An evaluee-prompt template's permissions must not contradict its own restrictions
- **Symptom:** the shared prompt template said both "do not connect to the database" and "you may... run
  `scripts/apex-validate.sh`" — but that script opens a SQLcl connection. Most evaluees ran it anyway and were
  graded PASS with the contradiction unflagged; one evaluee independently read the script's source, caught the
  conflict, and refused — an inconsistency in *compliance*, not in the CSS/APEXLang work being graded, that
  went unnoticed across most of a 19-run matrix.
- **Fix:** before reusing a prompt template across many runs, grep every script/tool it permits against every
  constraint it states, for exactly this kind of contradiction. If a genuinely offline substitute doesn't
  exist, don't forbid the resource the permitted tool needs.

### 6.4 A scenario's `Expected`/`Failure` may only describe what its task can actually trigger
- **Symptom:** scenario 12's `Failure` line named an app-level CSS/JS routing mistake the task (add a region
  Static ID) never comes near; scenario 13's `Expected`/`Failure` named two navigation-menu corrections a
  Cards-region-only task never touches. Passing verdicts on these scenarios were read as validating the whole
  underlying finding, when large parts of each finding were structurally untestable by the task as written.
- **Fix:** for every clause in `Expected`/`Failure`, ask "what would the evaluee have to *do* for this to be
  reachable?" — if the task never asks for that, either broaden the task or split the untestable part into its
  own scenario. Don't let an evaluation's Given/Expected outgrow what its Task line actually exercises.

### 6.5 When a verdict is downgraded, sweep every place that verdict is repeated, not just the Status line
- **Symptom:** three separate times, a run log's `## Verdict:` heading and its "Evidence" prose kept saying
  PASS (and, in one case, "clean differentiating evidence") for several review rounds *after* a correction
  elsewhere in the very same file had already downgraded the conclusion — because only the finding's Status
  line got updated in the moment, not the run log's own heading and prose that a reader (or a grep for
  "Verdict: PASS") would see first.
- **Fix:** a verdict correction isn't done until `grep -rn "PASS\|Verdict:"` across every file that mentions the
  scenario comes back consistent — the run log's own heading, its evidence paragraph, the scenario's row in
  `evaluations/README.md`, and the finding's Status line all have to agree, not just the last one you touched.

### 6.6 Resetting an evaluee worktree between runs destroys the evidence, not just the state
- **Symptom:** run logs recorded the prompt, the evaluee's *self-reported* summary, and `git diff --stat` — but
  `git checkout -- . && git clean -fd` between runs (necessary to stop one scenario's edits contaminating the
  next) meant the actual full diff and any seeded fixtures were gone by the time a reviewer asked to verify a
  specific claimed selector or contract.
- **Fix:** before resetting, capture the full `git diff` (not just `--stat`) and any files you seeded into the
  worktree yourself — either paste the diff into the run log or save it as a sibling `.patch` file. A run log
  that can't be independently re-diffed isn't the "session/transcript" evidence spec §58 asks for, it's a
  summary of one.
- **What it cost, concretely (2026-09-17):** scenario 05's evaluee had moved a hero-card rule into
  `sample-themes/linen/css/apex/shell.css` exactly as the scenario asks, but its worktree was reset and the
  rule was never committed. When the import that would have closed the scenario's remaining clauses finally
  happened, *that CSS did not exist anywhere* — so the clauses had to be closed on substituted CSS from the
  same pipeline, with the substitution written into the run log. A scenario can be blocked by its own lost
  artifact long after the run that produced it.

### 6.7 The author of a fix should not be its only grader
- **What happened (2026-09-17):** scenarios 04, 05 and 11 were re-measured by the same session that had applied
  the fixes under test, because their blocker (an APEX import) cleared long after the evaluee round ended and
  re-dispatching three fresh evaluees was out of scope. That is not the evaluee/grader separation §6.1–6.6
  exist to protect.
- **When it is unavoidable, do all three:** say so in the run log's header (not a footnote); prefer
  measurements anyone can re-take from a documented snippet over narrative claims; and include at least one
  *falsifiable control* — scenario 11's bare-Iris A/B (measure the same nodes with the package class removed,
  then restored) is one, because a package regression mis-attributed to Universal Theme would show up as a
  difference and it did not.
- **What it still doesn't buy you:** an independent agent re-running the scenario end to end. Record the
  verdict as resting on the measurement, and keep the residual coverage list intact rather than letting a PASS
  imply the scenario was re-run cleanly.
