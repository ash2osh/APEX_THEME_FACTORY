# Run: 13-cards-render-event — baseline (corrected isolation)

Scenario file: `.agents/evaluations/13-cards-render-event.md`
Worktree commit: `eda510d` (`/tmp/eval/baseline-eda510d`) — **not** `9276369`
Model: inherited from session (Sonnet 5)

## Why this re-run exists

The Codex PR review on PR #4 (P2, `chatgpt-codex-connector`) pointed out that the original baseline
(`9276369`) predates `eda510d`, and `eda510d` already contains a correct `tablemodelviewpagechange` handler in
`static-files/js/app.js` — so the original `9276369` baseline wasn't isolating the skill-text change at all, it
was also missing the *application code* current had. Verified independently before re-running:

```
git show eda510d:static-files/js/app.js | grep tablemodelviewpagechange   # present
git show 9276369:static-files/js/app.js | grep tablemodelviewpagechange   # absent (whole handler missing)
git diff eda510d:.agents/skills/apex-alpine-lifecycle/SKILL.md b0aa923:.agents/skills/apex-alpine-lifecycle/SKILL.md
  # eda510d: "apexafterrefresh on the region (IG, IR, classic)" only
  # b0aa923 (current): adds "Cards regions instead fire tablemodelviewpagechange ... Verify at runtime first"
```

`eda510d` is the correct isolation point: same application code as `current` (the handler already exists), but
the *skill* text is still the old, Cards-silent version — isolating exactly the one variable spec §58 requires.

## Evaluee prompt

Identical to the original baseline run (`13-cards-render-event-baseline.md`), only the worktree path changed
(`/tmp/eval/baseline-eda510d` instead of `/tmp/eval/baseline`).

## Evaluee final summary

> Page 405's Cards region ... **already has** an "active card" mechanism — `static-files/js/app.js` hooks the
> Cards/table-model widget's **`tablemodelviewpagechange`** event (bubbles to the region; fires on load and
> every sort/filter/paginate, unlike `apexafterrefresh`) ... That existing code is this project's own
> documented lifecycle knowledge for this widget (this baseline predates the later `pitfalls.md` file, so the
> working implementation *is* the documentation here). ... extended the existing handler ... to clear-then-set
> `is-current`/`is-active`/`aria-current` across all cards every time the event fires.

## git diff --stat / status

```
 static-files/css/pages/themes.css | ~ (comment only)
 static-files/js/app.js            | ~ (extended existing tablemodelviewpagechange handler)
```

## Verdict: PASS — same weak-differentiator pattern as scenarios 12 and 14

Evidence: the evaluee used `tablemodelviewpagechange` correctly, but by its own account this was because it
*found the already-correct application code* and extended it, not because of anything the (still Cards-silent)
skill text told it. This properly isolated baseline **passes**, unlike the original `9276369` baseline (which
had no existing handler to read and defaulted to `apexafterrefresh`).

**Consequence for the finding**: `2026-09-14-apex-widget-events` cannot be promoted on the strength of scenario
13 — a correctly isolated baseline (same app code, old skill text) also passes. The original promotion,
based on comparing against `9276369` (missing app code entirely, not just missing skill text), conflated two
different variables and should not have been treated as spec §58 evidence that "the previous instructions
mishandle the scenario." Demoted back to `findings/pending/`; see the finding's Status line.
