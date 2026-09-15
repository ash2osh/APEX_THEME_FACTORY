# Run: 12-apexlang-static-id — current

Scenario file: `.agents/evaluations/12-apexlang-static-id.md`
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

Task: Give the Cards region on page 405 (`theme_packages_cards`) a Static ID of `theme_packages_cards` in
its APEXLang source, so page CSS can target it.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/current, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used. Stop before any import.
```

## Evaluee final summary

> Per the project's APEXLang convention (`.agents/knowledge/pitfalls.md` §3.1: Static ID is `advanced {
> htmlDomId: … }`, not `staticId`)... Inspecting the file shows: `advanced { htmlDomId: theme_packages_cards }`
> already present, introduced in commit `eda510d`. No edits made. Ran `scripts/apex-validate.sh` — Validation
> successful.

## git diff --stat / status

```
(clean — no changes made; property already correct in the source)
```

## Verdict: PASS (weak differentiator)

Evidence: the evaluee correctly identified `advanced { htmlDomId: … }` as the right property (citing the
corrected knowledge file directly) and correctly recognized no change was needed since the region already had
it from a prior commit. This is consistent with Expected and does not hit the `staticId` Failure condition, but
— like `14-theme-style-scope`'s baseline run — the property was already correct in the codebase before this run,
so it mainly demonstrates the evaluee reads carefully rather than exercising skill knowledge to produce the
correct property from scratch. The real differentiating evidence for this finding is the baseline run
(`12-apexlang-static-id-baseline.md`), where the skill text was actually stale and the region genuinely lacked
the property.
