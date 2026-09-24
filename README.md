# APEX Theme Factory

Build portable, self-contained **themes for Oracle APEX 26.1 / Universal Theme 42 / Iris** — and install them
into any APEX app with one command, without touching that app's pages, regions or business logic.

A theme here is a **CSS-only package**. It never changes your application's behaviour: it ships a token file
and component rules scoped to `html.app-theme-<name>`, plus a small bootstrap that adds that class before the
page paints. Remove it and you are back to stock Iris, byte for byte.

**Which are you doing?**

| I want to… | Go to |
|---|---|
| Put an existing theme into my APEX app | [Using a theme](#using-a-theme) |
| Take a theme back out, or undo an install | [Removing a theme](#removing-a-theme) |
| Build a theme of my own | [Building a theme](#building-a-theme) |
| Release a theme (check, package, live smoke) | [Releasing a theme](#releasing-a-theme) |
| Work on the factory itself (agents, skills, specs) | [docs/AGENT_SPEC.md](docs/AGENT_SPEC.md) |

**8 themes ship with the factory:** [Carbon Volt](sample-themes/carbon-volt/), [Citrus Pop](sample-themes/citrus-pop/), [Cobalt Press](sample-themes/cobalt-press/), [Estate Slate](sample-themes/estate-slate/), [Estate Slate Dark](sample-themes/estate-slate-dark/), [Linen](sample-themes/linen/), [Solarized Dark](sample-themes/solarized-dark/), [Velvet Signal](sample-themes/velvet-signal/).

---

## Using a theme

### Before you start

| You need | Notes |
|---|---|
| Oracle APEX **26.1.x** | The installer refuses anything else rather than guessing. |
| Universal Theme 42, theme style **Iris** | Iris is the only supported style. Never switch styles or use Theme Roller. |
| **SQLcl** with a saved connection | e.g. `sql -name docker-demo`. The installer drives `apex export/validate/import` through it. |
| **Python 3.10+** | Checked by the wrapper before it runs. The package bundles its own `lib/`, so there is nothing to `pip install`. |
| Your APEX **workspace name** and **app ID** | You will type the app ID to confirm before anything is written. |

> **Checksums prove integrity, not origin.** `checksums.sha256` catches a damaged or partially edited package,
> but anyone can rebuild a package with matching checksums. Install only packages from a source you trust, and
> compare the ZIP's SHA-256 with the one the publisher lists (`sha256sum <name>-<version>.zip`).

No SQLcl? Every package also ships `MANUAL-INSTALL.md` with the App Builder click-path. See
[Installing by hand](#installing-by-hand).

### 1. Get the package

Each build is one ZIP containing exactly one theme:

```bash
unzip dist/linen/linen-1.0.0.zip -d /tmp/theme
cd /tmp/theme/linen-1.0.0
```

The extracted folder is self-contained — `install.sh`, `uninstall.sh`, the CSS, the manifest, the bundled
`lib/`, and `MANUAL-INSTALL.md`. You can copy it to any machine that can reach your database.

### 2. Dry-run first (this is the default)

```bash
./install.sh --connection <SAVED_CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>
```

Nothing is written to the database. It exports your app, applies the change to a staging copy, compiles it, and
prints exactly what *would* change — which files are added, whether a bootstrap region is created, and whether it found an
existing Theme Factory install to upgrade. **Read this before applying.** A dry run is safe to repeat and leaves
nothing behind; only `--apply` writes a backup.

### 3. Apply

```bash
./install.sh --connection <SAVED_CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --apply
```

You will be asked to **type the app ID** to confirm. Type anything else and it exits `7` with the target
untouched. Before importing, it writes an immutable backup of your application under
`./theme-factory-backups/<WORKSPACE>-<APP_ID>/<timestamp>/` — keep it; [restore](#undo-an-install-restore)
needs it.

Add a theme picker to the navigation bar while you are at it:

```bash
./install.sh --connection <CONN> --workspace <WS> --app-id <ID> --with-switcher --apply
```

`--with-switcher` adds a **Theme** menu to the navigation bar with one entry per installed package plus
*Iris (no theme package)*. The choice is remembered **per browser** (`localStorage`), so different people can
view your app differently — nothing is stored server-side and no user session is involved.

Pass `--without-switcher` to install the theme fixed. Passing **neither** preserves whatever the app already
has: no switcher on a first install, and an existing switcher left alone when you upgrade or add a second
theme — so a re-install never silently takes the menu away.

> The switcher needs a *static* navigation-bar list to attach to. If your app's nav bar is built some other
> way, the installer refuses and points you at `MANUAL-INSTALL.md` rather than rewriting your list.

### Install all themes at once (with switcher)

To install every discovered Theme Factory package into any APEX application with the switcher in a single command:

```bash
# Dry-run first (exports, stages, and validates via SQLcl without writing to DB):
scripts/install-all-themes.sh --app-id <APP_ID>

# Apply live to the database:
scripts/install-all-themes.sh --app-id <APP_ID> --apply
```

Options:
- `--app-id <ID>`: Target APEX application ID (required).
- `--connection <CONN>`: SQLcl saved connection name (default: `docker-demo`).
- `--workspace <WS>`: Target APEX workspace name (default: `DEMO`).
- `--themes <list>`: Comma-separated themes, built fresh from `sample-themes/` (default: every discovered theme).
- `--packages <zip,...>`: Install these exact archives instead.
- `--with-switcher` / `--without-switcher`: Control the navigation-bar switcher (default: `--with-switcher`). A navigation bar that is not a static list is refused, exactly like the single-theme installer — see `MANUAL-INSTALL.md`. This is why app 102 (SQL navigation bar) is served by `scripts/sync-static.sh` instead.
- `--backup-dir <dir>`: Backup root (default: `theme-factory-backups/`).
- `--apply`: Import into the database (default is a dry run). The last theme listed becomes the default.

It runs the same guarded transaction as `scripts/theme.sh install`: APEX 26.1 / UT 42 / Iris preflight,
checksum verification, backup, SQLcl validation, drift guard and post-import check.

### 4. Check it worked

Load any page of your app. `<html>` should carry `app-theme-<name>`, and the console should be clean. If you
installed the switcher, open the **Theme** menu — exactly one entry is checked, and the choice survives a
reload.

### What the installer actually touches

It is deliberately narrow, and everything it owns is marked so it can be removed exactly:

- **Adds** static files under `theme-factory/packages/<name>/<version>/` (the CSS, `theme.json`, the preview
  image, any fonts) plus `theme-factory/runtime/registry.json`.
- **Adds** one hidden page-0 region carrying the bootstrap script, with the Static ID
  `theme_factory_bootstrap` and an HTML marker comment. A second one covers dialog templates.
- **Adds** `#APP_FILES#theme-factory/packages/<name>/<version>/theme.css` to the application's CSS file URLs.
- **With `--with-switcher` only:** adds list entries under the `theme-factory-` static-ID namespace.
- **Never** touches your pages, regions, processes, items, or any file it did not create. It records a
  SHA-256 for each file it owns in `registry.json` and refuses to remove anything whose digest has changed.

Re-running the installer is safe: it detects its own previous install and upgrades in place rather than
duplicating.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success (or a completed dry run) |
| `3` | Refused before touching anything — wrong APEX version, unsafe target, or an ownership conflict |
| `4` | Refused — the application changed in the database while staging or while the confirmation prompt was open (someone else edited it); nothing written |
| `5` | Export, compile or import failed. Export and compile never touch the target; if `apex import` itself failed, check the app and [restore](#undo-an-install-restore) from the backup if needed — there is no automatic rollback |
| `6` | Imported, but the post-import check found the result is not what was staged — **read the message** |
| `7` | Cancelled at the confirmation prompt; target untouched |

---

## Removing a theme

### Uninstall

```bash
./uninstall.sh --connection <CONN> --workspace <WS> --app-id <ID>            # dry run
./uninstall.sh --connection <CONN> --workspace <WS> --app-id <ID> --apply    # remove
```

Same confirmation and the same backup. It removes only what `registry.json` says it owns, and it refuses to
proceed if any owned file has been edited since install — so a hand-tweaked file is never silently deleted.

If two Theme Factory packages are installed, removing one leaves the other working and re-points the default
at it. Removing the last one leaves the app on bare Iris, with the bootstrap regions and file URLs gone.

### Undo an install (restore)

The backup taken before an install is a full copy of the application as it was:

```bash
# from the extracted package directory (its bundled lib/ is on PYTHONPATH)
PYTHONPATH=. python3 -m lib.theme_factory.cli restore \
  --connection <CONN> --workspace <WS> --app-id <ID> \
  --backup ./theme-factory-backups/<WS>-<ID>/<TIMESTAMP> --apply
```

This replaces the whole application with the backup, so anything you changed in the app *after* the install
would be lost. The tool checks for that and refuses unless you pass `--discard-later-changes`, which is there
to make the loss a decision rather than a surprise. A backup whose contents have been modified is rejected
outright.

### Installing by hand

No SQLcl, or a locked-down environment? `MANUAL-INSTALL.md` inside every package lists each step through the
App Builder UI — which files to upload, the exact region to create, and the CSS file URL to add — plus the
matching uninstall steps.

---

## Building a theme

Work in this repository. A theme lives in one folder and nothing outside it is theme-specific.

| Step | Command | Time |
|---|---|---|
| Create | `scripts/theme.sh new NAME --recipe FILE` | seconds |
| Check (policy, contrast, fonts, packaging, uniqueness) | `scripts/theme.sh check NAME` | ~0.1 s |
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
[`static-files/css/foundation/tokens.css`](static-files/css/foundation/tokens.css); add a default there before
using a new role. A theme-private palette may use its own short prefix (`--sol-*`, `--mid-*`).

### 3. Map them onto Universal Theme

Below the token block, override Iris' own `--ut-*` atoms on the **theme-style scope**
(`.app-theme-midnight .apex-theme-iris`), never on `:root` — that is what keeps every component modifier
working. [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) §1 explains why.

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
[docs/CHROME_DEVTOOLS_MCP.md](docs/CHROME_DEVTOOLS_MCP.md) across the standard page list, then **drive the
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

### The one trap that will bite you

Iris declares many of its colour atoms **on `:root`** as `var(--ut-*)` chains. A `var()` chain resolves where
it is *declared*, not where it is used, so those atoms freeze to Iris' light literals before your body-level
overrides can reach them. Your theme looks right until something uses one — a selected grid row goes
near-white under light text, a chart paints its labels black.

Three families do this: `--a-palette-*` (15 atoms), `--a-base-link-text-color`, and the 32 `--oj-*` tokens
Oracle JET reads for charts. Restate them in your own scope; `--oj-*` must go on the **html** scope because
JET reads it once at bootstrap and bakes the result into SVG `fill`.

`sample-themes/solarized-dark/css/tokens.css` has the worked example with measured before/after ratios, and
[`.agents/knowledge/pitfalls.md`](.agents/knowledge/pitfalls.md) §1.2 has the mechanism. Reading that section
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
   with the switcher, opens it in its own Chrome tab at 1440 and 375 px (console errors, failed requests,
   fonts, AA contrast, keyboard switcher, selection kept across reload), then re-imports the clean export.

It prints `RELEASE theme=<name> status=PASS|FAIL` and nothing is recorded. The smoke needs SQLcl, the Chrome
MCP daemon (`python3 tools/chrome_mcp_daemon.py`, never a direct MCP call — each new connection raises a
consent prompt) and a clean 9010. If 9010 already carries packages, it refuses. Create or reset 9010 with:

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
lib/theme_factory/      installer, uninstaller, packager, recipe/scaffold, checks
tools/                  release smoke, browser check, cover capture, Chrome MCP daemon
docs/                   spec, design system, components, tooling guides
.agents/                agent skills and knowledge (pitfalls)
```

| Script | What it does |
|---|---|
| `scripts/theme.sh new / font / check / cover / release …` | Scaffold, fonts, checks, covers, release |
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

## License

MIT — see [LICENSE](LICENSE). Third-party material (Oracle's reference-app export in `applications/ut/`, OFL fonts,
Alpine.js, external skills) keeps its own terms; see [NOTICE.md](NOTICE.md). Oracle's Universal Theme CSS/JS is not
redistributed: `scripts/fetch-vendor.sh --reference` fetches it locally from your own APEX instance.
