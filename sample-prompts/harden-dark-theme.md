Make a dark theme package survive Universal Theme, not just look right at rest.

**Boundary:** APEX 26.1.x · UT 42 · Iris. Iris ships **light only** — a dark package is an override layer, and
Universal Theme will fight it in specific, known places.
**Blast radius:** edits CSS under `sample-themes/<name>/css/`. No database writes.
**Browser access:** project daemon only — `python3 tools/chrome_devtools_client.py <tool> '<json-args>'`.

## My package

- Theme package: << name >>
- Where it is already installed and viewable: << app / URL >>

## Read this first

`.agents/knowledge/pitfalls.md` §1.2. The mechanism in one sentence: a `var()` chain resolves **where it is
declared**, not where it is used, so Universal Theme atoms declared on `:root` as `var(--ut-*)` freeze to
Iris' light literals before any body-level override can reach them. A dark package therefore looks correct
until something consumes one of those atoms.

Three families do this, and each needs restating inside the package's own scope:

| Family | Where it must be restated | What breaks if you skip it |
|---|---|---|
| `--a-palette-*` (15 atoms) | theme-style scope | selection in IG / IRR / Card View / Media List / Timeline / Comments goes near-white under light text; subtle badges; the date picker's current day |
| `--a-base-link-text-color` | theme-style scope | faceted-search text buttons keep Iris' link blue on a dark panel |
| `--oj-*` (Oracle JET) | the **html** scope | chart axis, group, legend and series labels paint black — JET reads these once at bootstrap and bakes them into SVG `fill` |

## Do this

1. For each family, measure the **current** resolved value at `:root` versus the package scope, live, and
   report both. That is the evidence the freeze is happening.
2. Restate the chain in the package's `tokens.css`. `--oj-*` goes on the html scope because JET reads it off
   the document element; the others go on the theme-style scope.
3. **Drive the interaction states**, because every real defect in this project's own dark theme lived in a
   state rather than at rest: select a report row, open the date picker, hover report and grid toolbars, open a
   modal dialog and audit **inside its iframe**, empty a search box to reach the "No results" state.
4. Audit charts with an SVG-aware sweep. The audit in `docs/CHROME_DEVTOOLS_MCP.md` scores `fill` for
   `svg text`/`tspan`; a sweep that only reads CSS `color` reports a broken chart page as clean.
5. Attribute every remaining failure with a **bare-Iris A/B**: measure the same nodes with the package class on
   the document element, then removed, then restored. Identical numbers mean Universal Theme or APEX owns the
   defect and no package change can fix it. Different numbers mean it is yours.
6. Note the JET caveat honestly: because JET resolves its colours once at bootstrap, an `--oj-*` fix **cannot**
   be observed by injecting CSS. It only appears after an import and a reload. Say so rather than claiming it
   works.

## Report

- The before/after resolved values per family.
- Contrast numbers per state, with the count of nodes scanned.
- The A/B table separating package defects from Universal Theme / APEX literals.
- What remains unverifiable without an import.
