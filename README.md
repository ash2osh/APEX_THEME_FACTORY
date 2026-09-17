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
| Understand how it's verified before release | [Verification](#verification) |
| Work on the factory itself (agents, skills, specs) | [docs/AGENT_SPEC.md](docs/AGENT_SPEC.md) |

Two themes ship as examples: **[linen](sample-themes/linen/)** (quiet product — white chrome, hairlines, teal
for actions) and **[solarized-dark](sample-themes/solarized-dark/)** (VS Code Solarized Dark, tuned to pass
WCAG AA on a dark canvas).

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

Nothing is written. It exports your app, applies the change to a staging copy, compiles it, and prints exactly
what *would* change — which files are added, whether a bootstrap region is created, and whether it found an
existing Theme Factory install to upgrade. **Read this before applying.** A dry run is safe to repeat.

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

### 4. Check it worked

Load any page of your app. `<html>` should carry `app-theme-<name>`, and the console should be clean. If you
installed the switcher, open the **Theme** menu — exactly one entry is checked, and the choice survives a
reload.

### What the installer actually touches

It is deliberately narrow, and everything it owns is marked so it can be removed exactly:

- **Adds** static files under `css/themes/<name>/` (the CSS, `theme.json`, the preview image).
- **Adds** one hidden page-0 region carrying the bootstrap script, with the Static ID
  `theme_factory_bootstrap` and an HTML marker comment. A second one covers dialog templates.
- **Adds** `#APP_FILES#css/themes/<name>/theme.css` to the application's CSS file URLs.
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
| `4` | Refused — the application changed in the database while staging (someone else edited it); nothing written |
| `5` | Export, compile or import failed (the target is unchanged, or restored) |
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

```text
sample-themes/<name>/
├── theme.json        name, title, tagline, direction, class (app-theme-<name>), template options
├── README.md         direction, technique, what was verified
├── css/theme.css     entry point — imports tokens.css and apex/*.css
├── css/tokens.css    your colours and geometry, scoped to html.app-theme-<name>
├── css/apex/*.css    component rules, every selector prefixed .app-theme-<name>
└── preview/cover.jpg 960 px gallery image
```

### 1. Copy a starting point

```bash
cp -r sample-themes/linen sample-themes/midnight
```

Rename the class everywhere: `theme.json` (`"class": "app-theme-midnight"`) and every selector prefix in
`css/`. `linen` is the better base for a light theme, `solarized-dark` for a dark one — a dark theme has extra
work to do (see [the dark-theme trap](#the-one-trap-that-will-bite-you)).

### 2. Set your tokens

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
scripts/sync-static.sh          # assemble the CSS into the APEXLang export
scripts/apex-validate.sh        # compile-check (expect: Validation successful.)
scripts/apex-import.sh          # import — asks first; full replace of what's on disk
```

Your theme now appears in the navigation-bar **Theme** menu and on page 405 of app 102. Nothing to register by
hand: `sync-static.sh` ships `theme.json` and `cover.jpg` alongside the CSS, and both surfaces read them.

To make it the app's default: `scripts/apply-theme.sh midnight` (then sync + import again).

> `apex import` replaces the application with whatever is on disk, so always run `sync-static.sh` **before**
> validating and importing — otherwise you ship the previous build's CSS.

### 6. Audit contrast before you call it done

Not optional, and not eyeballable — a dark theme in particular will pass a screenshot review and still fail
WCAG AA in states you did not look at. Run the audit snippet in
[docs/CHROME_DEVTOOLS_MCP.md](docs/CHROME_DEVTOOLS_MCP.md) across the standard page list, then **drive the
states a resting sweep cannot see**: select a report row, open a date picker, hover a toolbar, open a dialog,
empty a search box. Every real defect found in this project's own dark theme lived in a state, not at rest.

### 7. Package it

```bash
scripts/package-theme.sh midnight          # → dist/midnight/midnight-1.0.0.zip
```

Builds are deterministic — same input, same bytes — and the ZIP carries its own installer, uninstaller and
manual instructions.

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
  external font URLs and `data:` URLs are rejected by the packager.
- **One theme per ZIP.** Multi-theme bundles are refused by design.
- **All installed packages load; only one is active** — each is inert unless `<html>` carries its class, which
  is what makes live switching instant and removal clean.

---

## Repository map

```text
sample-themes/<name>/   theme packages — the only editable copy of a theme
static-files/css/       shared foundation: --app-* roles, reset, app.css entry
static-files/js/        app.js (App.theme helper), Alpine components, vendor
applications/ut/        APEXLang export of the reference app (app 102) — generated + source
scripts/                export / validate / import, sync-static, apply-theme, package-theme
lib/theme_factory/      the installer, uninstaller, packager and verification engine
tools/                  live matrix, browser matrix, Chrome MCP daemon, agent smokes
docs/                   spec, design system, components, tooling guides
.agents/                agent skills, knowledge, findings, evaluations
```

| Script | What it does |
|---|---|
| `scripts/apex-export.sh` | Refresh `applications/ut/` from app 102 |
| `scripts/apex-validate.sh` | Compile-check the APEXLang source (read-only) |
| `scripts/apex-import.sh` | Validate + import (asks first; full replace) |
| `scripts/sync-static.sh` | Assemble `static-files/` + `sample-themes/*/css` into the export |
| `scripts/apply-theme.sh <name>` | Set the app's default theme |
| `scripts/package-theme.sh <name> [out]` | Build the distributable ZIP |
| `scripts/release-check.sh <name>` | Build + verify + write the release report |

---

## Verification

Run the offline gate any time — no credentials, no database:

```bash
bash tests/run-offline.sh
```

Release verification is deliberately layered, and a layer only passes with a retained, digest-bound artifact:

| Layer | Covers | Where it runs |
|---|---|---|
| **A** Repository source | clean tree, unit tests, agent layout | offline / CI |
| **B** Package artifact | deterministic ZIP, manifest, CSS policy | offline / CI |
| **C** Database install | install → reinstall → coexistence → switcher → uninstall ×2 → restore, on disposable consumer apps | local, live DB |
| **D** Browser runtime | both consumers at 1440/1024/768/375: console, network, contrast, fonts, keyboard switcher, persistence | local, live Chrome |
| **E** Agent behaviour | three agent runtimes + the evaluation scenarios | local |

> **CI proves A and B only.** A green CI badge says nothing about whether the theme installs, renders, or is
> accessible. C, D and E need local evidence — see [tests/live/RELEASE-MATRIX.md](tests/live/RELEASE-MATRIX.md).

```bash
scripts/release-check.sh linen      # → dist/linen/RELEASE-REPORT.md; exit 0 only when every layer PASSes
```

Evidence is bound to the package SHA-256 and the last **source** commit, so a report cannot outlive the code it
describes: change the source and the old evidence is rejected rather than quietly reused. Missing or failed
checks stay `UNVERIFIED`/`FAIL` — and so does the verdict.

Browser checks go through the shared Chrome MCP daemon (`python3 tools/chrome_mcp_daemon.py`), never a direct
MCP call — Chrome's debugging consent is per connection, so a direct call raises a prompt that only the person
at the machine can accept.
