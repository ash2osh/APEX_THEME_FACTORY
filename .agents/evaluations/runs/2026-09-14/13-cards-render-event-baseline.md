# Run: 13-cards-render-event — baseline

Scenario file: `.agents/evaluations/13-cards-render-event.md`
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

Task: The Cards region on page 405 needs a small Alpine/JS enhancement: mark the currently active card with
an `is-active` class after the region renders/re-renders, so it stays correct if the grid re-sorts or
re-paginates. Write the code for this (you cannot run Chrome to test it live, but write it correctly per the
project's documented event/lifecycle knowledge for this widget).

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/baseline, (3) a final summary listing every file you changed with the key
selectors/properties/tokens/events you used. Stop before any import.
```

## Evaluee final summary

> Why `apexafterrefresh` and not a made-up event: this repo's own `docs/AGENT_SPEC.md` §34 and the
> `apex-alpine-lifecycle` skill name it as the documented completion signal for a refreshed region, and
> `.agents/knowledge/reference/ut-26.1/theme42.min.js` itself binds pagination-visibility logic to
> `apexafterrefresh` on `apex.regions[...].element` for report-family widgets — corroborating it inside this
> project's own reference bundle. I could not run Chrome DevTools to confirm live, so I deliberately avoided
> guessing an unverified proprietary event name and used the one this repo documents and demonstrates.
>
> `static-files/js/components/theme-style-cards.js` (new): `Alpine.data('themeStyleCardsActiveTracker', …)`
> binding/unbinding **`apexafterrefresh`** on `this.$el` ... `markActive()` toggles `is-active` based on
> `.t-Badge` presence.

## git diff --stat / status

```
 applications/ut/pages/p00405-theme-styles.apx | ~5 lines
 docs/COMPONENTS.md                             | +entry
 static-files/js/components/theme-style-cards.js | new file
```

## Verdict: FAIL

Evidence: the evaluee's own reasoning explicitly names and uses **`apexafterrefresh`** as the Cards render
signal — exactly the scenario's Failure condition (*"apexafterrefresh used as the Cards render signal"*). This
matches the underlying finding's evidence precisely: Cards regions render after DOM-ready and
`apex.region(id).refresh()` fires no `apexafterrefresh`; the correct hook is the widget's own
`tablemodelviewpagechange`, which the baseline skill set (`apex-alpine-lifecycle`, predating the
2026-09-14 pitfalls.md §2 correction) does not mention — the evaluee had no way to discover it and defaulted to
the generic (wrong, for Cards) region-refresh event, even after doing real research into the reference bundle.
