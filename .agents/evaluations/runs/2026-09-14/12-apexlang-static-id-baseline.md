# Run: 12-apexlang-static-id — baseline

Scenario file: `.agents/evaluations/12-apexlang-static-id.md`
Worktree commit: `9276369` (`/tmp/eval/baseline`)
Model: inherited from session (Sonnet 5)

## Evaluee prompt

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/baseline. First, cd into
/tmp/eval/baseline and treat it as your working directory for this whole task — all file reads/edits happen
there, nowhere else.

Your instructions are /tmp/eval/baseline/AGENTS.md, the docs it references, and the skills under
/tmp/eval/baseline/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its
copies may not match this directory). Do not run scripts/apex-import.sh, do not open Chrome, do not
connect to the database; you may grep .agents/knowledge/reference/ and run scripts/apex-validate.sh.

Task: Give the Cards region on page 405 (`theme_packages_cards`) a Static ID of `theme_packages_cards` in
its APEXLang source, so page CSS can target it.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/baseline, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used. Stop before any import.
```

## Evaluee final summary

> Property: Region Static ID in APEXLang is `advanced { htmlDomId: ... }`, **not** `settings { staticId: ... }`.
> I verified this empirically before editing... Every region in `applications/ut/` that sets its own DOM Static
> ID does so via `advanced { htmlDomId: <value> }`... `settings { staticId: ... }` only appears on
> `plugin/componentInstructions` regions, where it's a reference... Using `staticId` here would have been the
> wrong property.
>
> Edit: `applications/ut/pages/p00405-theme-styles.apx`, added `advanced { htmlDomId: theme_packages_cards }`
> to `region official-theme-styles-cards`. Ran `scripts/apex-validate.sh` — "Validation successful."

## git diff --stat / status

```
 applications/ut/pages/p00405-theme-styles.apx | 3 +++
 1 file changed, 3 insertions(+)
```

## Verdict: PASS — but by overriding the stale skill via cross-file grep, not because of it

Evidence: `grep -n "staticId\|htmlDomId" /tmp/eval/baseline/.agents/skills/apexlang-design-editor/SKILL.md`
confirms the baseline skill's shortcut table still says the *wrong* thing: `| Hook for scoped CSS |
cssClasses: on region/item/button; staticId: |`. Despite that, the evaluee did not follow it — it
independently grepped `applications/ut/` for how other regions set a DOM Static ID, found `advanced {
htmlDomId: ... }` used everywhere a real Static ID is set, and correctly identified `staticId` as the
internal-component-identifier property instead. Final edit uses `advanced { htmlDomId: theme_packages_cards }`,
matching Expected exactly — no Failure condition triggered.
This weakens (does not eliminate) the case for promoting the finding on this scenario alone: the old skill text
is still wrong and would mislead a less-thorough run, but this particular run passed by verification discipline
rather than being blocked by the stale text. Compare against the current-worktree run, where the skill table is
already corrected, to see whether the *current* skill removes the need for that extra verification step.
