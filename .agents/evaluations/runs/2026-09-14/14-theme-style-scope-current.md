# Run: 14-theme-style-scope — current

Scenario file: `.agents/evaluations/14-theme-style-scope.md`
Worktree commit: `b0aa923` (`/tmp/eval/current`)
Model: inherited from session (Sonnet 5)

Note: task changed from "restyle buttons to 36px" (already true at baseline14, a weak differentiator — see
`14-theme-style-scope-baseline.md`) to "give floating-label form fields a 1px solid border" so this run
exercises the pattern from scratch rather than confirming pre-existing CSS.

## Evaluee prompt

```
You are the Oracle APEX design-engineering agent for the project in /tmp/eval/current. First, cd into
/tmp/eval/current and treat it as your working directory for this whole task — all file reads/edits happen
there, nowhere else.

Your instructions are /tmp/eval/current/AGENTS.md, the docs it references, and the skills under
/tmp/eval/current/.agents/skills/ — read the ones that apply yourself; do NOT use the Skill tool (its
copies may not match this directory). Do not run scripts/apex-import.sh, do not open Chrome, do not
connect to the database; you may grep .agents/knowledge/reference/ and run scripts/apex-validate.sh.

Task: Core/Iris declare the base component atoms (--a-button-*, --a-field-*, --a-gv-*, --jui-dialog-*,
--a-menu-*, most --ut-*) on :root, and every modifier / state / variant sets the same atoms on the element
(.t-Button--small, .t-Button--hot, .t-Button--header, floating-label containers, .a-IRR). Overriding the base
atoms on body.apex-theme-iris restyles every instance while all modifiers keep precedence, with zero :not()
chains and no property fights. The remaining exceptions are atoms set on an element
(.a-IRR{--a-gv-border-radius}, .t-Region radius via --ut-region-*) — override on that element — and Iris
rules that carry !important (tree-nav hover/current) — mirror the !important with a comment. Given this,
restyle all form field inputs (floating-label text fields) app-wide to have a 1px solid border in
--app-border-color instead of Iris' default underline-only style.

Deliver: (1) a short plan naming the files you will change and why, (2) the actual edits made in
/tmp/eval/current, (3) a final summary listing every file you changed with the key
selectors/properties/tokens you used. Stop before any import.
```

## Evaluee final summary

> `.t-Form-fieldContainer--floatingLabel` only sets padding/font-size atoms on itself — it does not touch
> `--a-field-input-border-*`, so a body/theme-scope override of those atoms reaches floating-label inputs
> untouched, with zero `:not()` chains. ... "app-wide" = the default package, scoped `.app-theme-linen
> .apex-theme-iris`... Added `--a-field-input-border-width: 1px`, `--a-field-input-border-style: solid`,
> `--a-field-input-border-color: var(--app-border-color)` to the existing atom-override block.
> `sample-themes/solarized-dark/css/apex/forms.css` was deliberately left unchanged — it already gives fields a
> 1px solid border tuned for its own contrast requirement; swapping in the literal token there would regress
> accessibility.

## git diff --stat / status

```
 sample-themes/linen/css/apex/forms.css | ~4 lines (3 atoms added under existing .apex-theme-iris scope)
```

## Verdict: AMBIGUOUS — downgraded from PASS, see round 2 correction below (this heading fixed 2026-09-15)

Evidence: the change lands as base `--a-field-input-*` atoms on the theme-style scope
(`.app-theme-linen .apex-theme-iris`, the project's current form of "body.apex-theme-iris" now that app-wide
restyles are layered as theme packages), with no property override fighting a modifier and no unscoped `:root`
write — matching Expected. The evaluee additionally showed good judgment by not blindly propagating the same
literal token into the dark package where it would have regressed a documented contrast finding, without being
asked to.

**On "bare Iris" not being covered** (Codex PR review, PR #4, P2): a reviewer correctly noted the fix is
scoped to `.app-theme-linen`, so it does not reach the app's "Iris (no theme package)" state — a real,
user-selectable option (page 405's Cards gallery, `App.theme.use('none')`, per
`applications/ut/pages/p00405-themes.apx`: `'Universal Theme''s own style, no package applied.'`). Verified
this is intentional, not an oversight: this project's whole architecture routes app-wide restyles through
theme packages (`2026-09-14-theme-packages-routing`; `sample-themes/README.md`), and "Iris (no package)" is
the explicit, documented fallback for a visitor who wants *unmodified* Universal Theme — restyling it would
defeat the purpose of offering that option. Under this project's current conventions, "app-wide" for a
restyle request means "within the active package," not "reaching every possible display state including the
literal no-package baseline." This is worth stating explicitly (the scenario's `Expected` line doesn't spell
it out), but is not treated as a Failure here.

**Note 2026-09-14** (Codex PR review, PR #4, P2, round 1 of 2 on this scenario): this run used a *different*
task than the original baseline run (`14-theme-style-scope-baseline.md`, which tested the now-superseded
buttons wording) — not a valid matched pair. `.agents/evaluations/14-theme-style-scope.md` has been updated to
make this form-field task the canonical Expected/Failure text going forward (it's a genuine from-scratch
exercise, unlike buttons, which was a no-op at every commit tested).

**Correction 2026-09-14, round 2**: a further review pass on that same scenario file caught something more
fundamental — the "Task:" line quoted above (lines 23–31) is the scenario's own `Given` text verbatim,
including the sentence *"Overriding the base atoms on body.apex-theme-iris restyles every instance while all
modifiers keep precedence, with zero :not() chains and no property fights"* — that is the scoping conclusion
this scenario is meant to test whether the evaluee reaches **unaided**. Handing it over in the prompt means
this run's PASS cannot establish that. The scenario's `Given` has been rewritten to describe only the
environment (where atoms and modifiers are declared) without stating the scoping answer. This run's edits are
still real and still technically correct, but the **verdict is downgraded to ambiguous** — it doesn't
demonstrate unaided skill behavior, on top of not being a validly matched pair with baseline. A fresh run
against the now-neutral `Given` is needed on both sides before this scenario can support any promotion
decision.
