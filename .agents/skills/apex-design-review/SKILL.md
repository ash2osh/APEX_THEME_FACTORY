---
name: apex-design-review
description: Use when about to declare a design task complete, when preparing a hand-off summary, or when asked to review design-system debt
---

# apex-design-review

## Completion checklist (spec §75) — every applicable item must be true
Source: all changes in `applications/ut/*.apx`, `static-files/`; validate passes; nothing lives only in DevTools/console/Page Designer.
Architecture: UT base intact; native components reused; Alpine justified; logic server-side; theme style still Iris.
CSS: scoped selectors; tokens reused; no global `.t-*` overrides; no unexplained `!important`; 4 widths checked.
Alpine: single init; works after refresh; item sync; no console errors; keyboard OK.
APEX: DAs, refresh, dialogs, forms, validations, IG/IR behaviour verified.
Visual: compared against target at matching viewport; loading/empty/error states.
Theme package: contrast audit run on the standard page list (incl. the doc pages 4000/6303/6304) with 0 package failures; README has a *Verified* section; no literal colours in `css/apex/*.css`; `!important` only mirroring Iris.
Knowledge: new traps recorded in `.agents/knowledge/pitfalls.md`; COMPONENTS.md / DESIGN_SYSTEM.md updated.

## Debt scan (report; fix only if in scope — spec §63–§64)
HIGH: global UT overrides · many `!important` · duplicate components.
MEDIUM: repeated literal colours/spacing · near-identical cards · page CSS that became reusable.
LOW: naming inconsistencies.

## Hand-off format
Changed files · what/why per file · how verified (viewports, console, lifecycle) · findings filed · open questions.
