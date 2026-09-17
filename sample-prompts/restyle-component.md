Restyle one Universal Theme component in a theme package, correctly.

**Boundary:** APEX 26.1.x · UT 42 · Iris. Do not replace the component with custom markup; restyle the native
one.
**Blast radius:** edits CSS under `sample-themes/<name>/css/`. No database writes.
**Browser access:** project daemon only — `python3 tools/chrome_devtools_client.py <tool> '<json-args>'`.

## My request

- Component / page: << e.g. the Interactive Report toolbar on page 1402 >>
- Theme package: << name >>
- What should change: << description, screenshot or reference >>

## Do this

1. **Read the live DOM first** — `take_snapshot` and `evaluate_script` on the real page. Report the actual
   class chain and the computed values you are about to change. Do not start from memory or from a screenshot.
2. **Find where the current value comes from** before overriding it. Walk the cascade: is it a `--ut-*` atom,
   an `--a-*` atom, a literal in the widget CSS, or something declared on the element itself? `pitfalls.md`
   §1.9 describes how to trace it. Overriding the wrong layer produces a rule that works on one page and fails
   on the next.
3. **Prototype in the browser** by injecting the candidate CSS, and measure the result — before and after
   values, and contrast if you touched colour.
4. **Move it into source**: `sample-themes/<name>/css/apex/<area>.css`, every selector prefixed with the
   package class, values from tokens only. If you need a value that has no token, add the role to
   `static-files/css/foundation/tokens.css` with an Iris default first.
5. **Assemble and compile-check**: `scripts/sync-static.sh` then `scripts/apex-validate.sh`.
6. Say plainly whether the running app shows your change yet. It will **not** until someone imports — if you
   verified by injecting the on-disk file's text, label it as exactly that. Never call an injected change
   "verified live".

## Report

- The class chain and cascade path you traced.
- Before/after computed values, measured.
- Whether an import is needed for me to see it, and the exact commands if so.

## Red flags — stop and re-think

- Writing `.t-Region { … }` or any unprefixed Universal Theme selector.
- Reaching for `!important` without an Iris `!important` to mirror.
- Writing a literal colour that a token already holds.
- Claiming completion while the change exists only in DevTools.
