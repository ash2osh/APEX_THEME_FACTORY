# Run: 14-theme-style-scope — baseline

Scenario file: `.agents/evaluations/14-theme-style-scope.md`
Worktree commit: `97a3354` (parent of `43eec93`, the commit that first introduced `body.apex-theme-iris` token
overrides into `docs/DESIGN_SYSTEM.md`/skills) — `/tmp/eval/baseline14`
Model: inherited from session (Sonnet 5)

## Evaluee prompt

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/baseline14. First, cd into
/tmp/eval/baseline14 and treat it as your working directory for this whole task — all file reads/edits
happen there, nowhere else.

Your instructions are /tmp/eval/baseline14/AGENTS.md, the docs it references, and the skills under
/tmp/eval/baseline14/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its
copies may not match this directory). Do not run scripts/apex-import.sh, do not open Chrome, do not
connect to the database; you may grep .agents/knowledge/reference/ and run scripts/apex-validate.sh.

Task: Core/Iris declare the base component atoms (--a-button-*, --a-field-*, --a-gv-*, --jui-dialog-*,
--a-menu-*, most --ut-*) on :root, and every modifier / state / variant sets the same atoms on the element
(.t-Button--small, .t-Button--hot, .t-Button--header, floating-label containers, .a-IRR). Overriding the base
atoms on body.apex-theme-iris restyles every instance while all modifiers keep precedence, with zero :not()
chains and no property fights. The remaining exceptions are atoms set on an element
(.a-IRR{--a-gv-border-radius}, .t-Region radius via --ut-region-*) — override on that element — and Iris
rules that carry !important (tree-nav hover/current) — mirror the !important with a comment. Given this,
restyle all buttons app-wide to 36px height.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/baseline14, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used. Stop before any import.
```

## Evaluee final summary

> `static-files/css/apex/buttons.css` ... already implements exactly the architecture in the task: base
> `--a-button-*` atoms ... are set once on `.apex-theme-iris` (the theme-style scope, not `:root`) ... Height
> math against Core's actual box model ... = 36px, exactly matching `--app-control-h: 2.25rem`... This is
> already 36px app-wide... Since the substantive change was already correct and committed, I made one edit... —
> strengthened the comment block... No other file needed edits.

## git diff --stat / status

```
 static-files/css/apex/buttons.css | (comment-only change)
```

## Verdict: PASS on the task actually run (weak differentiator) — NOT comparable to the current-worktree run

Evidence: the on-disk `buttons.css` at this commit already overrides `--a-button-*` atoms on `.apex-theme-iris`
(the theme-style scope) rather than `:root` or a `.t-Button` property override — matching this run's Expected
exactly. The evaluee neither introduced `:root{--a-button-*}` nor a `.apex-theme-iris .t-Button{padding:…}`
property override, so this run does not hit the Failure condition. However, this scenario is a weak
baseline/current differentiator: the correct pattern was already committed in the code the evaluee read
(commit `e5fd54a`, predating even this baseline checkout), so the run mostly verifies the evaluee can read and
confirm existing CSS rather than exercising skill knowledge to produce the pattern from scratch.

**Correction 2026-09-14** (Codex PR review, PR #4, P2): this run tested the *buttons* task
(`.agents/evaluations/14-theme-style-scope.md`'s original wording), while
`14-theme-style-scope-current.md` tested a *different* task (form-field borders) — the scenario file has
since been updated to make the form-field task canonical (see its own 2026-09-14 note), since the buttons
task is a no-op at every commit this evaluation has run against. **This baseline run and the current-worktree
run are not a valid matched pair** — comparing "PASS on buttons at baseline" against "PASS on forms at
current" says nothing about whether old vs. new skill text behaves differently on the *same* task. No baseline
run of the form-field-border task has been performed.

**Correction, round 2**: a further review pass caught that the "Task:" line quoted above also contains the
scenario's `Given` text verbatim, including the scoping conclusion this scenario is meant to test whether the
evaluee reaches unaided ("Overriding the base atoms on body.apex-theme-iris restyles every instance while all
modifiers keep precedence..."). `14-theme-style-scope.md`'s `Given` has been rewritten to describe only the
environment, not the answer. This run's own PASS (on the buttons task, itself a no-op — see above) is
downgraded to ambiguous for the same reason as the current-worktree run: it never demonstrated unaided skill
behavior even setting the task-mismatch problem aside.

The finding this scenario supports (`2026-09-13-theme-style-scope-token-overrides`) stays pending; treat this
specific baseline/current pairing as uninformative for that decision rather than as evidence either way. A
genuine test needs a fresh baseline14 run and a fresh current-worktree run, both using the now-neutral `Given`
and the same (form-field-border) task.
