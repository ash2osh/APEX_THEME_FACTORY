# Run: 11-dark-package-coverage — baseline

Scenario file: `.agents/evaluations/11-dark-package-coverage.md`
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

Task: A teammate built a dark theme package on Iris (a light-only theme style) and declared it "done" after
checking pages 500 and 1402 only. Review whether it is actually ready to ship, and fix anything it's missing
so it holds up across the app, not just those two pages.

Deliver: (1) a short plan naming the files you will review/change and why, (2) the actual edits made in
/tmp/eval/baseline, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used. Stop before any import.
```

## Evaluee final summary

> I explored `/tmp/eval/baseline` thoroughly before writing anything, and the premise of the task doesn't
> match what's actually in the repo... `sample-themes/` — only one package exists: `linen/`... No `dark/`
> folder, no `.app-theme-dark` class anywhere... there is nothing checked in as a dark theme package for me to
> review, and no evidence a teammate's WIP exists anywhere in this checkout. [The agent stopped and asked for
> clarification rather than fabricating a package.]

## git diff --stat / status

```
(clean — no changes made)
```

## Verdict: AMBIGUOUS — scenario premise does not hold at this commit

Evidence: at `9276369` the Solarized Dark package had not yet been added (it lands later, in `eda510d`, which
is after this baseline commit) — so `sample-themes/` genuinely contains only `linen/`, confirmed by the
evaluee's own `find`/`grep` sweep and `git log --all`. The evaluee's behavior (stop, report what it verified,
ask rather than invent a dark package to review) is *correct* agent behavior, but it means this run does not
exercise the "dark package coverage" knowledge under test — there is no artifact to audit. This scenario needs
a worktree state that actually contains a dark package to be a valid baseline/current comparison; re-running it
against `/tmp/eval/current` (which has Solarized Dark from `eda510d`) is the only run that can produce a real
verdict for scenario 11. No skill-behavior conclusion should be drawn from this baseline run.
