Something looks or behaves wrong in the running app — find out why before changing anything.

**Boundary:** APEX 26.1.x · UT 42 · Iris.
**Blast radius:** diagnosis is **read-only**. Propose a fix and tell me where it belongs; only edit source if I
say so, and never import.
**Browser access:** project daemon only — `python3 tools/chrome_devtools_client.py <tool> '<json-args>'`. Use
your own tab.

## The symptom

- Where: << page / URL / component >>
- What I see: << description or screenshot >>
- What I expected: << description >>

## Do this

1. **Reproduce it and measure it.** Read the actual DOM, computed styles, console messages and network
   requests. State the numbers. Do not theorise from the description alone.
2. **Find the mechanism, not a workaround.** Typical roots in this stack, each with a different fix:
   - a colour that "won't override" — a `var()` chain frozen at `:root` (`pitfalls.md` §1.2), or an atom
     declared directly on the element, which outranks body-level overrides (§1.5);
   - a component that renders empty or unstyled — it rendered **after** DOM-ready and your hook ran too early
     (Cards, IG: §2.4, §2.8);
   - something that never refreshes — a Dynamic Content region printing with `sys.htp.p`, so the AJAX envelope
     carries `"result":null` and `apexafterrefresh` never fires (§2.7);
   - a widget event that never fires — check the real event name on the real element, not the documented one.
3. **Check whether it is ours at all.** Remove the theme class from the document element, re-measure, restore.
   If the symptom survives without the package, it belongs to Universal Theme or APEX and the fix is different
   (or there isn't one).
4. **Corroborate on a second surface** — another page using the same component, or the stock Universal Theme
   demo page for it. A defect that reproduces on stock UT is not caused by this project.
5. **Name the layer the fix belongs in**: APEXLang declaration, theme package CSS, shared foundation CSS,
   Alpine component, or "nothing — this is upstream behaviour".

## Report

- The measurements, quoted as values.
- The mechanism, in one paragraph, with the evidence that proves it rather than suggests it.
- Whether it is package-caused, and how you established that.
- The proposed fix, the layer it belongs in, and what would have to be re-verified after it.
- If you could not determine the cause, say so and list what you ruled out. A named unknown beats a guess.

If this is a reusable trap rather than a one-off, propose a finding for `.agents/findings/pending/` following
the format of the existing ones, and a `pitfalls.md` section.
