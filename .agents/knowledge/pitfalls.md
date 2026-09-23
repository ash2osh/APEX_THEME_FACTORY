# Pitfalls and lessons — living record

Every trap this project has fallen into, with the fix that worked. Organised by layer, not by date; each
entry says how it was verified. Add to it — the entry in its layer file, its heading line here — whenever something surprises you (spec §50–§58: file a finding
first if the lesson should change a skill). Confidence CONFIRMED unless marked. Verified on APEX 26.1.4 /
Universal Theme 42 / Iris, app 102, 2026-09-13 → 14.

Companion files: [`ut-26.1-iris-runtime.md`](ut-26.1-iris-runtime.md) (runtime facts),
[`iris-ut-tokens.md`](iris-ut-tokens.md) (token values), `ut-dom-*.md` (markup hooks),
[`reference/README.md`](reference/README.md) (offline CSS/JS copies), `../findings/` (protocol records — pending until their evaluation has run).

Entries live in one file per layer under `pitfalls/`. Entry numbers are stable, so `pitfalls §4.3c` still
means entry 4.3c: find it below and open its layer file. Skim this index before theme, runtime or import
work; read a layer file when one of its headings touches the task.

---

## 1. Universal Theme / Iris CSS — [pitfalls/1-ut-iris-css.md](pitfalls/1-ut-iris-css.md)
- **§1.1** Iris declares ~70 `--ut-*` tokens and ~100 `--a-*` atoms with *literal* colours on `:root`
- **§1.1b** Iris 26.1.4 does not render Oracle Sans
- **§1.2** `var()` chains in Iris `:root` resolve at `:root`, not where consumed
- **§1.3** "Atom not found in Core/Iris" ≠ dead
- **§1.4** `.u-Report` utility tables are hard-coded light in the widget CSS
- **§1.5** Component atoms declared *on the element* beat body-level overrides
- **§1.6** Iris `!important` on the tree nav
- **§1.7** Solarized (and most terminal palettes) fail AA on a card surface
- **§1.8** Reference-app demo pages style their own markup with literal light values
- **§1.9** Where a colour comes from when no rule seems to set it
- **§1.10** A scripted `:root` literal-extraction pass can silently drop tokens
- **§1.11** Fixing a themed *text* atom without its paired *background* atom is a half-fix

## 2. APEX JavaScript and widgets — [pitfalls/2-apex-javascript-widgets.md](pitfalls/2-apex-javascript-widgets.md)
- **§2.1** Navigation-bar menus are built by theme42 on `apexreadyend`; `theme42ready` fires on **window**
- **§2.2** The `menu` widget accepts a `radioGroup` item
- **§2.3** Pages without a navigation bar: `$()` chains don't throw
- **§2.4** Cards regions render after DOM-ready and don't fire `apexafterrefresh` on `refresh()`
- **§2.5** Card > CSS Classes supports `&COLUMN.` substitution and lands on `.a-CardView`
- **§2.6** Alpine.js being registered as a static file doesn't mean it's loaded
- **§2.7** A Dynamic Content region that prints with `sys.htp.p` cannot be refreshed

## 3. APEXLang / Builder — [pitfalls/3-apexlang-builder.md](pitfalls/3-apexlang-builder.md)
- **§3.1** Static ID is `advanced { htmlDomId: … }`
- **§3.2** App-level CSS/JS are top-level blocks
- **§3.3** Theme styles of a subscribed theme are read-only and not in APEXLang
- **§3.4** Removing the last app process
- **§3.5** Static files that only exist in the export
- **§3.6** Static files as data
- **§3.7** `apex import` is a full replace
- **§3.8** APEXLang comment lines never come back from `apex export`
- **§3.9** Lists are exported into one `shared-components/lists.apx`

## 4. Tooling (Chrome DevTools MCP, SQLcl) — [pitfalls/4-tooling.md](pitfalls/4-tooling.md)
- **§4.1** Shared browser state
- **§4.2** Same-document hash navigation does not reload
- **§4.3** The contrast audit finds what screenshots miss
- **§4.3b** The contrast audit's `bgOf()` used to double-composite `<body>`'s own background
- **§4.3d** "0 failures" is not evidence unless the scan says how many nodes it scanned
- **§4.3c** A second `chrome-devtools-mcp --autoConnect` may never answer
- **§4.4** SQLcl / DB
- **§4.5** In an agent-driven tab, `requestAnimationFrame` runs ~1×/s — don't call rAF-deferred UI a defect
- **§4.6** A `@font-face` is only downloaded when something renders text in it

## 5. Workflow — [pitfalls/5-workflow.md](pitfalls/5-workflow.md)
- **§5.1** Another agent may be editing the same tree
- **§5.2** Review before claiming
- **§5.3** Don't promote a finding before its evaluation has run
- **§5.4** Skills lag the architecture unless the protocol runs
- **§5.x** Evidence is bound to the last *source* commit
- **§5.5** Hardcoding a package version in a helper script silently skips a theme
- **§5.6** `pkill` on a wrapper shell orphans the Python process doing the work

## 6. Evaluation protocol (spec §58/§62) — traps from the evaluation rounds — [pitfalls/6-evaluation-protocol.md](pitfalls/6-evaluation-protocol.md)
- **§6.1** A baseline commit must predate the *code/instruction under test*, not just the finding
- **§6.2** Never build an evaluee prompt by quoting a finding's `Given` verbatim if it states the conclusion
- **§6.3** An evaluee-prompt template's permissions must not contradict its own restrictions
- **§6.4** A scenario's `Expected`/`Failure` may only describe what its task can actually trigger
- **§6.5** When a verdict is downgraded, sweep every place that verdict is repeated, not just the Status line
- **§6.6** Resetting an evaluee worktree between runs destroys the evidence, not just the state
- **§6.7** The author of a fix should not be its only grader
