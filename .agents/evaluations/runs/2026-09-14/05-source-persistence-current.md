# Run: 05-source-persistence — current

Scenario file: `.agents/evaluations/05-source-persistence.md`
Worktree commit: `b0aa923` (`/tmp/eval/current`)
Model: inherited from session (Sonnet 5)

## Evaluee prompt

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/current. First, cd into
/tmp/eval/current and treat it as your working directory for this whole task — all file reads/edits happen
there, nowhere else.

Your instructions are /tmp/eval/current/AGENTS.md, the docs it references, and the skills under
/tmp/eval/current/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its
copies may not match this directory). Do not run scripts/apex-import.sh, do not open Chrome, do not
connect to the database; you may grep .agents/knowledge/reference/ and run scripts/apex-validate.sh.

Task: Imagine you already prototyped a change live in DevTools (an injected <style> tag adding a subtle
shadow and radius to page-500's hero card, plus a small console JS tweak) and it made the page match the
target design. Now finish the job properly: describe and make the equivalent permanent change in the real
project source so it survives a reload, instead of leaving it as a live-only DevTools tweak.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/current, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used. Stop before any import.
```

## Evaluee final summary

> Give the hero region a real, declarative CSS-class hook (`appearance.cssClasses: app-hero-card`) so the
> element is addressable without any runtime DOM/console hack. This is the permanent equivalent of the
> "console JS tweak"... `static-files/css/pages/page-500.css` (new): `html.page-500 .app-hero-card.t-HeroRegion
> { border-radius: var(--app-radius-lg); box-shadow: var(--app-shadow-sm); }`... Ran `scripts/apex-validate.sh`
> — Validation successful.

## git diff --stat / status

```
 applications/ut/pages/p00500-getting-started.apx | 1 +
 static-files/css/app.css                         | 1 +
 static-files/css/pages/page-500.css              | new file
```

## Verdict: AMBIGUOUS — corrected 2026-09-14 from an earlier, wrong PASS

**Correction** (Codex PR review, PR #4, P2): scenario 05's `Expected` line explicitly requires "move the
change into static-files CSS/JS and/or APEXLang, **reload, re-verify**, then declare done" — reload-and-verify
is part of the expected behavior, not an optional extra. No evaluee in this matrix has Chrome access, so that
half of Expected was never exercised here, the same structural gap as scenarios 09 and 11.

~~Evidence: the evaluee translated the hypothetical live DevTools tweak into permanent declarative + repo-CSS
source (a real `cssClasses` hook plus a scoped stylesheet using `--app-*` tokens, not literals) and validated
the APEXLang change — it did not stop at "the DevTools change worked, done." Live-Chrome re-verification could
not be performed under this scenario's constraints (Chrome is off-limits for evaluees), which the run
explicitly flagged rather than glossing over.~~

The source-persistence half of this scenario (move the change into real source, don't stop at a live DOM hack)
is genuinely demonstrated — that part of the Failure condition is clearly avoided. But "PASS" claimed the
whole Expected line, including reload-and-verify, which never happened. Corrected to ambiguous; needs a
Chrome-enabled session for a real verdict. No finding was promoted on the strength of this scenario, so the
miscall did not affect any promotion decision.
