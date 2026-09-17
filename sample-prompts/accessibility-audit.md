Audit a theme or page for WCAG AA text contrast, honestly.

**Boundary:** APEX 26.1.x · UT 42 · Iris.
**Blast radius:** **read-only.** Measure and report; do not edit source, do not import, do not change database
or browser state beyond your own tab.
**Browser access:** project daemon only — `python3 tools/chrome_devtools_client.py <tool> '<json-args>'`. Open
your own tab, and close it when you are done; other tabs belong to someone else.

## My target

- Pages or URLs: << list, or "the standard page list" >>
- Theme package active: << name, or "bare Iris" >>
- Widths: << e.g. 1440 and 375 >>

## Do this

1. Use the audit snippet in `docs/CHROME_DEVTOOLS_MCP.md` exactly — it composites translucent ancestors
   properly and scores both CSS `color` for HTML text and `fill` for `svg text`/`tspan`. A hand-rolled variant
   will quietly miss chart labels or double-composite the page background.
2. Sweep every page at each width. Record for each: the page id, the document element's class, the failure
   count, **and how many nodes were scanned**.
3. Drive the states a resting sweep structurally cannot see, and audit each: select a report or grid row, hover
   report/grid toolbar controls, open a date picker, open a modal dialog (run the audit **inside** its iframe,
   or you are scoring the parent page), empty a search box.
4. For every failure, attribute it with a **bare-Iris A/B**: measure the same nodes with the theme class on the
   document element, then removed (~900 ms settle), then restored. Identical numbers ⇒ Universal Theme or APEX
   owns it. Different ⇒ the package owns it.
5. Do not fix anything. If you see an obvious fix, describe it and where it would belong.

## Report

A table per surface: ratio, foreground, resolved background, selector, required threshold, and owner
(package / Universal Theme / APEX). Then:

- Total nodes scanned and total failures — **never report `0 failures` without the scanned count**, because a
  scan that reached nothing looks identical to a clean page.
- Which states you drove and which you could not.
- Which pages and widths you did **not** cover.

If a runtime was unavailable, report that part `UNVERIFIED` and continue with the rest. Do not infer a pass
from a page you did not open.
