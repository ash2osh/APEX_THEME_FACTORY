# Run: 04-apex-refresh — current

Scenario file: `.agents/evaluations/04-apex-refresh.md`
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

Task: An Alpine component lives inside an APEX region that gets refreshed by a Dynamic Action (e.g. after a
filter change). Write or fix the component so it keeps working correctly after every refresh — no duplicate
handlers, no broken state, no repeated Alpine startup. Use an existing component in
static-files/js/components/ as your example if one is refreshable, or write a small new one that
demonstrates the correct pattern.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/current, (3) a final summary listing every file you changed with the key
selectors/properties/tokens/events you used. Stop before any import.
```

## Evaluee final summary

> `static-files/js/components/card-quick-actions.js` (new) — `Alpine.data('cardQuickActions', …)`... All state
> is local `x-data` state re-seeded from markup on every `init()`... `init()` binds `document` listeners;
> `destroy()` removes the same instance's listeners. Since APEX region refresh replaces the DOM subtree, Alpine
> calls `destroy()` on the old scope and `init()` on the new one automatically — this symmetry is what prevents
> the classic "duplicate handler" bug ... instead of ever calling `Alpine.start()` again. Persistent state goes
> through `apex.server.process(...)`, keeping APEX/DB authoritative.

## git diff --stat / status

```
 docs/COMPONENTS.md                                | +entry/contract
 static-files/css/app.css                          | 1 +
 static-files/css/components/card-quick-actions.css | new file
 static-files/js/components/card-quick-actions.js   | new file
```

## Verdict: AMBIGUOUS — corrected 2026-09-14 from an earlier, wrong PASS

**Correction** (Codex PR review, PR #4, P2): two problems. (1) The diff contains only a new, standalone
component (`static-files/js/components/card-quick-actions.js` + its CSS + a `docs/COMPONENTS.md` entry) — no
APEXLang region or Dynamic Action wiring it into an actual refreshable region, so there is nothing here a
refresh could actually be triggered against; the reasoning about `init()`/`destroy()` symmetry across a DOM
replacement is architecturally sound but was never exercised against a real refresh (Chrome was also
forbidden, so it couldn't have been anyway). (2) Expected specifically says "state re-synced from the APEX
item" — the component re-seeds from DOM markup and a generic `apex.server.process()` ajax call, not from an
APEX page item, which is a more specific requirement than what was delivered.

~~Evidence: relies on Alpine's own `init()`/`destroy()` scope-teardown symmetry across a region-DOM replacement
(no `Alpine.start()` re-call, no leaked `document` listeners since `destroy()` mirrors `init()`), and re-syncs
state from the DOM/server on every `init()` rather than caching stale state — matching Expected. No duplicate
handlers or broken-state pattern introduced.~~

Corrected to ambiguous. No finding was promoted on the strength of this scenario, so this only affects the
record. A valid run needs an actual `.apx` region + Dynamic Action refresh target and, ideally, a live
Chrome session to confirm no duplicate handlers actually appear after a real refresh.
