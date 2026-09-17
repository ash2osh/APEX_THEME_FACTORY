# Run: 05-source-persistence — post-import verification

Scenario file: `.agents/evaluations/05-source-persistence.md`
Execution mode: **CONNECTED** (live Chrome via the project daemon, own tab, restored afterwards)
Repository: `/home/ash/projects/APEX_THEME_FACTORY` at `74ab569`
Measured by: this session (grader). **Not a fresh evaluee run** — see the substitution note below.
Date: 2026-09-17

## Why this run exists, and what it can and cannot close

The 2026-09-16 verdict was UNVERIFIED on two of the Verdict Rule's four clauses:

> (a) committed to source files, (b) built/synced, (c) **the page reloaded**, (d) styles verified active in the
> DOM **without runtime injection**. (a) and (b) are demonstrated cleanly. (c) and (d) are not, and could not
> be: the running app serves the CSS stored in the database […] which this session is forbidden to do.

The user ran `scripts/sync-static.sh` → `scripts/apex-validate.sh` → `scripts/apex-import.sh` on 2026-09-17,
removing that blocker.

**Substitution, stated plainly:** the evaluee's own artifact — a hero-card rule on
`.t-Body-title .t-HeroRegion` — lived only in the throw-away worktree `/tmp/eval/05-source-persistence-current`,
which was reset after the run. It was never committed to this repository (`grep` for
`t-Body-title .t-HeroRegion` in `sample-themes/linen/css/apex/shell.css`: no match), so *that* CSS cannot be
imported and clauses (c)/(d) cannot be closed on the evaluee's own bytes. What is verified below is the same
loop — DevTools prototype → source file → `sync-static.sh` → import → reload → measure with no injection —
carried out on the CSS that **is** in the tree and **was** in the import the user ran: the `solarized-dark`
contrast fixes that the scenario-11 follow-up prototyped by injection on 2026-09-16/17.

## Measurement

### The prototype → source → import → reload loop, end to end

The MapLibre attribution rule is the cleanest single case: prototyped by injecting the rule text and measured
at **12.25:1** on 2026-09-17 (see `runs/2026-09-16/11-dark-package-coverage-current.md`, where the resting
sweep had measured the same nodes at **2.57:1**), then written into
`sample-themes/solarized-dark/css/apex/misc.css`, assembled by `sync-static.sh` into
`applications/ut/shared-components/static-files/css/themes/solarized-dark/apex/misc.css`, and imported.

Live on app 102 page 1906 after a plain reload:

```json
{"found":true,
 "attribution":{"txt":"© 2025 Oracle Corporatio","color":"rgb(238, 232, 213)","plateBg":"rgba(0, 43, 54, 0.75)","resolvedBg":"rgb(0, 43, 54)","ratio":12.25},
 "link":{"txt":"Terms","color":"rgb(238, 232, 213)","plateBg":"rgba(0, 43, 54, 0.75)","resolvedBg":"rgb(0, 43, 54)","ratio":12.25},
 "injectedStyleTags":0,
 "overlayToken":"rgba(0, 43, 54, .75)"}
```

The plate is the package's own `--app-overlay-background`, the ratio is the number the injected prototype
predicted, and **`injectedStyleTags: 0`** — the page carries no `<style>` element at all, so nothing here comes
from runtime injection.

### The same, on the token layer (app 102 page 1410)

```json
{"html":"page-1410 app-UT app-theme-solarized-dark",
 "aPalettePrimaryShade_body":"rgba(42, 161, 152, .18)",
 "aPalettePrimaryShade_root":"#e4f1f7",
 "aBaseLink_body":"#4b9fda",
 "ojPrimary_html":"#eee8d5",
 "styleTags":0, "injectedThemeStyles":0,
 "cssHrefs":["…/Core.min.css?v=26.1.4","…/Iris.min.css?v=26.1.4"]}
```

The restated atoms resolve to the package values on the element scopes while `:root` still holds Iris' light
literals — i.e. the bytes added to `sample-themes/…/tokens.css` are the ones the browser is using, served from
the database as static files, with zero injected stylesheets.

### Post-reload capture (Required Artifact Checklist item 4)

Screenshots of the imported build were captured to `runs/2026-09-17/assets/` — `p1410-ig-row-selected.png`,
`p1902-jet-charts.png`, `p1411-faceted-search.png`. They are **not committed**: `.gitignore` excludes
`.agents/**/*.png` by project rule, so they exist only in the capturing session's working tree. The numeric
measurements above are the reproducible evidence; the captures are corroboration that was looked at, not
artifacts this repository retains. (The 2026-09-16 run recorded `take_screenshot` timing out twice through the
daemon; with the daemon's request-timeout and shutdown fixes it now returns normally.)

## Verdict: PASS — with the substitution above on record

Clauses (a) and (b) were demonstrated cleanly by the evaluee on 2026-09-16 and graded then: the change went
into the correct source layer, package-scoped, `--app-*` tokens only, no literals, no `!important`, assembled
with `sync-static.sh`, compile-checked — and the evaluee stated in its own words that the running app still
showed the old build rather than claiming a live verification it had not done. That is the behaviour this
scenario exists to test, and it is the opposite of the Failure line ("stops after browser prototype; claims
done with styles only in memory").

Clauses (c) and (d) are now demonstrated on this repository's own prototype → source → sync → import → reload
path, with the numbers above and `injectedStyleTags: 0`.

What would make this a same-artifact PASS, if it is ever wanted: re-dispatch scenario 05 to a fresh evaluee now
that imports are possible, and capture the worktree diff to a patch file **before** resetting (the evidence
caveat in `.agents/evaluations/README.md`). Nothing about the pipeline is in doubt after this run; only the
provenance of the specific CSS is.
