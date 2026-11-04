# Building and releasing a theme

This guide is for theme authors. It covers how a theme is made, how to check it, and how to release it.
To install a theme into an app, read [Get started](GET_STARTED.md) instead.

## Building a theme

Work in this repository. A theme lives in one folder and nothing outside it is theme-specific.

| Step | Command | Time |
|---|---|---|
| Create | `scripts/theme.sh new NAME --recipe FILE` | seconds |
| Check (policy, shipped-token contrast, recipe drift, fonts, packaging, uniqueness, copied CSS) | `scripts/theme.sh check NAME` | ~0.2 s |
| See it in app 102 | `scripts/sync-static.sh`, `scripts/apex-validate.sh`, `scripts/apex-import.sh` | ~6 min |
| Release | `scripts/theme.sh release NAME` | ~5 min |

Iterate with `check`; import app 102 only when you need to see the page, and batch several edits per import.

```text
sample-themes/<name>/
├── theme.json        name, title, tagline, direction, class (app-theme-<name>), template options
├── README.md         direction, technique, what was verified
├── css/theme.css     entry point — imports tokens.css and apex/*.css
├── css/tokens.css    your colours and geometry, scoped to html.app-theme-<name>
├── css/apex/*.css    component rules, every selector prefixed .app-theme-<name>
└── preview/cover.jpg 960 px gallery image
```

### 1. Create from a recipe

```bash
scripts/theme.sh new midnight \
  --title "Midnight" --tagline "Compact nocturnal operations." --mode dark

# Or use a fully specified, versioned recipe:
scripts/theme.sh new midnight --recipe /path/to/midnight/theme.recipe.json
```

Recipe schema version 2 owns identity, light/dark mode, nine semantic palette anchors, body/heading typography,
four weights, geometry, focus, six component profiles, explicit rhythm, interaction, and responsive strategy.
Unknown or missing fields fail closed, core contrast is checked before generation, and the directory name must match
`identity.name`. Version-1 recipes remain readable with deterministic compatibility defaults; newly emitted recipes
are always version 2. The short command creates a neutral recipe that is ready for deliberate customization.

Generated CSS begins with `/* @theme-factory-generated */`. Regeneration may replace only those marked files;
unmarked modules are the handwritten escape hatch and are preserved. Existing recipe-less packages remain
supported for maintenance, but copying and global renaming is no longer the creation workflow.

The neutral templates provide shared Universal Theme adapters only; a recipe chooses the package's composition,
rhythm, interaction states, and responsive strategy. No theme is a parent of another theme, and Linen remains the
application default rather than a source template.

### 2. Customize the generated tokens and profiles

`css/tokens.css` is where a theme actually lives. Assign the `--app-*` roles — surfaces, text levels, accents,
borders, radii, shadows — and let the component rules inherit from them:

```css
html.app-theme-midnight {
    --app-surface-page:    #10131a;
    --app-surface-card:    #171b24;
    --app-text-primary:    #e6e8ee;
    --app-text-secondary:  #9aa3b2;
    --app-color-primary:   #6ea8fe;
    --app-radius-md:       6px;
}
```

The full role list with Iris defaults is
[`static-files/css/foundation/tokens.css`](../static-files/css/foundation/tokens.css); add a default there before
using a new role. A theme-private palette may use its own short prefix (`--sol-*`, `--mid-*`).

### 3. Map them onto Universal Theme

Below the token block, override Iris' own `--ut-*` atoms on the **theme-style scope**
(`.app-theme-midnight .apex-theme-iris`), never on `:root` — that is what keeps every component modifier
working. [docs/DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) §1 explains why.

### 4. Component rules

`css/apex/*.css` holds the per-component work. Two rules keep themes maintainable:

- **No literal colours** — every value comes from a token in `tokens.css`.
- **No `!important`** unless you are mirroring an Iris `!important`, with the Iris rule quoted in a comment.

### 5. See it in the reference app

```bash
scripts/theme.sh check midnight
scripts/sync-static.sh && scripts/apex-validate.sh && scripts/apex-import.sh
```

Theme Lab on page 406 shows typography, surfaces, buttons, forms/validation, cards, IR, IG, reports, calendar,
JET chart, menus, date picker, Popup LOV, modal, and drawer specimens. Page 405 is the theme gallery.

To make it the app's default: `scripts/apply-theme.sh midnight` (then sync + import again).

> `apex import` replaces the application with whatever is on disk, so always run `sync-static.sh` **before**
> validating and importing — otherwise you ship the previous build's CSS.

### 6. Audit contrast before you call it done

Not optional, and not eyeballable — a dark theme in particular will pass a screenshot review and still fail
WCAG AA in states you did not look at. Run the audit snippet in
[docs/CHROME_DEVTOOLS_MCP.md](CHROME_DEVTOOLS_MCP.md) across the standard page list, then **drive the
states a resting sweep cannot see**: select a report row, open a date picker, hover a toolbar, open a dialog,
empty a search box. Every real defect found in this project's own dark theme lived in a state, not at rest.

### 7. Package and release it

See [Releasing a theme](#releasing-a-theme). `scripts/theme.sh release midnight --offline` alone builds
`dist/midnight/midnight-<version>.zip`; builds are deterministic and the ZIP carries its own installer,
uninstaller and manual instructions.

Capture a gallery cover after `check` passes:

```bash
scripts/theme.sh cover midnight --output sample-themes/midnight/preview/cover.jpg          # dry run
scripts/theme.sh cover midnight --output sample-themes/midnight/preview/cover.jpg \
  --apply --overwrite
```

Capture uses a private background tab and per-tab emulation, snapshots and restores the browser's theme selection,
and refuses console or network errors. Keep only the curated 960 px JPEG; iteration screenshots belong under ignored `scratch/`.

### Shared adapter families

Themes that share a lot of Universal Theme plumbing (dark themes restating the same Iris atoms, for example)
share it through a **family template** rather than copies. `theme-templates/adapters/<family>/<file>.css.tmpl`
holds numbered segments; each member theme carries the rendered text between fences in its own
`css/tokens.css` or `css/apex/<file>.css`:

```css
/* @adapter dark/shell#1 prefix=cv - generated from theme-templates/adapters/dark/shell.css.tmpl; ... */
...shared rules, with __NAME__ and __PREFIX__ filled in for this theme...
/* @adapter-end dark/shell#1 */
```

- Families today: **dark**: solarized-dark, carbon-volt, velvet-signal. **light**: estate-slate, citrus-pop, cobalt-press.
- Change shared rules in the template, then run `scripts/theme.sh adapters`. `tests/run-offline.sh` fails while any
  fenced block differs from its template (`scripts/theme.sh adapters --check`), so a hand edit inside a fence
  cannot slip through.
- Everything outside the fences is the theme's own CSS, in its original order. Packages stay self-contained:
  the rendered CSS is committed in every theme.
- `scripts/theme.sh check` warns `COPIED_CSS` when 65 % or more of a theme's own CSS is copied in blocks from
  another theme: share it through a family instead.

### The one trap that will bite you

Iris declares many of its colour atoms **on `:root`** as `var(--ut-*)` chains. A `var()` chain resolves where
it is *declared*, not where it is used, so those atoms freeze to Iris' light literals before your body-level
overrides can reach them. Your theme looks right until something uses one — a selected grid row goes
near-white under light text, a chart paints its labels black.

Three families do this: `--a-palette-*` (15 atoms), `--a-base-link-text-color`, and the 32 `--oj-*` tokens
Oracle JET reads for charts. Restate them in your own scope; `--oj-*` must go on the **html** scope because
JET reads it once at bootstrap and bakes the result into SVG `fill`.

`sample-themes/solarized-dark/css/tokens.css` has the worked example with measured before/after ratios, and
[`.agents/knowledge/pitfalls.md`](../.agents/knowledge/pitfalls.md) §1.2 has the mechanism. Reading that section
before starting a dark theme will save you a day.

### Conventions worth knowing

- **Fonts are optional.** A theme with no font assets uses APEX's own stack and ships zero font files. Custom
  fonts must be package-local licensed **WOFF2** files under `fonts/` with licences under `licenses/` —
  external font URLs and `data:` URLs are rejected by the packager. Use `scripts/theme.sh font add` with an
  official metadata URL and pinned upstream revision; it converts in a temporary pinned fontTools environment,
  verifies Arabic/Latin coverage, and writes face SHA-256 values plus provenance into the recipe.
- **One theme per ZIP.** Multi-theme bundles are refused by design.
- **All installed packages load; only one is active** — each is inert unless `<html>` carries its class, which
  is what makes live switching instant and removal clean.

---

## Releasing a theme

```bash
scripts/theme.sh release midnight            # check + package + live smoke, ~5 min
scripts/theme.sh release midnight --offline  # check + package only, seconds
```

1. **Check** — the author checks must pass.
2. **Package** — builds and verifies `dist/<name>/<name>-<version>.zip`.
3. **Live smoke** (skipped with `--offline`) — exports the disposable consumer app 9010, installs the package
   with the switcher, opens it in its own Firefox tab at 1440 px (console errors, failed requests, fonts, AA
   contrast, keyboard switcher, selection kept across reload) and at 375 px inside a phone-width frame (layout
   overflow, AA contrast, console errors, failed requests), then re-imports the clean export.
   The phone row loads the page into a same-origin frame, so the consumer app must allow same-origin framing.
   `tests/live/consumer-apps/minimal` does (`embedInFrames: allowSameOrigin`, as app 102 does); a consumer that
   denies framing cannot run the 375 px row.

It prints `RELEASE theme=<name> status=PASS|FAIL` and nothing is recorded. The smoke needs SQLcl, the browser
daemon (Firefox by default: start Firefox from its launcher, then `python3 tools/firefox_mcp_daemon.py`; see
[docs/FIREFOX_DEVTOOLS_MCP.md](FIREFOX_DEVTOOLS_MCP.md)) and a clean 9010. Never a direct MCP call: each new connection
can raise a consent prompt. If 9010 already carries packages, it refuses. Create or reset 9010 with:

```bash
scripts/reset-consumer.sh      # re-imports tests/live/consumer-apps/minimal as app 9010 (asks first)
```

---

## Repository map

```text
sample-themes/<name>/   theme packages — the only editable copy of a theme
static-files/css/       shared foundation: --app-* roles, reset, app.css entry
static-files/js/        app.js (App.theme helper), Alpine components, vendor
applications/ut/        APEXLang export of the reference app (app 102) — generated + source
scripts/                theme.sh, export / validate / import, sync-static, apply-theme, install-all-themes
theme-templates/        neutral scaffold, component profiles, adapters/ (shared family segments)
lib/theme_factory/      installer, uninstaller, packager, recipe/scaffold, checks, adapters
tools/                  release smoke, browser check, page audit, phone-width frame, cover capture, browser daemons (Firefox, Chrome)
docs/                   spec, design system, components, tooling guides
.agents/                agent skills and knowledge (pitfalls)
```

| Script | What it does |
|---|---|
| `scripts/theme.sh new / font / check / cover / release …` | Scaffold, fonts, checks, covers, release |
| `scripts/theme.sh adapters [--check]` | Render shared adapter segments into member themes (check: drift only) |
| `scripts/apex-export.sh` | Refresh `applications/ut/` from app 102 |
| `scripts/apex-validate.sh` | Compile-check the APEXLang source (read-only) |
| `scripts/apex-import.sh` | Validate, then validate + import (asks first; full replace) |
| `scripts/sync-static.sh [--check]` | Assemble `static-files/` + `sample-themes/*/css` into the export |
| `scripts/apply-theme.sh <name>` | Set the app's default theme |
| `scripts/install-all-themes.sh` | Install several themes into any consumer app |
| `scripts/reset-consumer.sh` | Create or reset the release test app 9010 |

## Verification

```bash
tests/run-offline.sh   # unit tests, skills layout, app 102 export drift, every theme check + package (~20 s)
```

CI runs the same script. Live checks (database, browser) run locally through `scripts/theme.sh release`.
Open live work (runtime unification, responsive audit) is planned step by step in
[docs/ONLINE_WORK_PLAN.md](ONLINE_WORK_PLAN.md).
