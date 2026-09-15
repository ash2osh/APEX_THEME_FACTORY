# Portable Single-Theme Distribution Design

**Date:** 2026-09-15
**Status:** Approved for implementation planning
**Scope:** Packaging, installation, optional switching, persistence, rollback, and manual installation

## 1. Purpose

Turn each Theme Factory package into a self-contained ZIP that can be installed into an existing Oracle APEX application without importing the factory's application 102. Each ZIP contains exactly one visual theme. The installation workflow supports a safe SQLcl path and a documented manual APEX Builder path.

The first supported consumer boundary is deliberately narrow:

- Oracle APEX `26.1.x`
- Universal Theme `42`
- subscribed base theme `ut-26.1`
- current theme style `Iris`

The installer must refuse every target outside that boundary. It must not attempt compatibility repair, theme migration, theme-style switching, or Theme Roller changes.

## 2. Goals

- Build a deterministic, self-contained ZIP from `sample-themes/<name>/`.
- Include shared `static-files/css/foundation/` dependencies in the built CSS.
- Install into a caller-selected application through a fresh APEXLang export, a narrow staged patch, validation, and an explicitly confirmed import.
- Never import `applications/ut/` into a consumer application.
- Make dry-run the default and show the exact target and diff before any live write.
- Preserve a complete pre-install export for recovery.
- Make installation and uninstallation idempotent.
- Allow multiple independently packaged themes to coexist in one consumer application.
- Keep the theme switcher optional.
- Persist a switcher selection per browser/device without database state.
- Provide complete manual APEX Builder instructions inside every ZIP.

## 3. Non-goals

- Supporting APEX 25.x, 26.2+, non-Universal themes, or non-Iris styles.
- Packaging more than one theme in one ZIP.
- Replacing the target application's navigation architecture.
- Adding account-level or cross-device preferences.
- Installing database tables, PL/SQL packages, Ajax callbacks, or authorization schemes.
- Using undocumented `wwv_flow_*` APIs or direct writes to APEX repository tables.
- Promising visual correctness for application-specific custom markup without consumer-app verification.

## 4. Distribution Contract

`scripts/package-theme.sh <theme-name>` builds:

```text
dist/<theme-name>/<theme-name>-<version>.zip
```

The ZIP root contains:

```text
<theme-name>-<version>/
├── theme.json
├── theme.css
├── theme-factory-runtime.js
├── install.sh
├── uninstall.sh
├── fonts/                         optional; WOFF2 files referenced by theme.json
├── lib/
│   └── theme_factory/
│       ├── __init__.py
│       ├── cli.py
│       ├── manifest.py
│       ├── apexlang.py
│       └── sqlcl.py
├── MANUAL-INSTALL.md
├── README.md
├── checksums.sha256
├── preview/
│   └── cover.jpg
└── licenses/
    ├── THIRD_PARTY.md
    └── <font-license>.txt          required for every declared font family
```

The ZIP contains one theme manifest and one theme stylesheet. The common runtime and installer utilities are copied into the ZIP so it remains usable outside this repository. The bundled Python library uses only the Python standard library; `install.sh` and `uninstall.sh` verify Python 3.10 or newer and invoke that local library without reading repository files.

### 4.1 Manifest

`theme.json` is validated against `schemas/theme-package.schema.json` and uses this version-one contract:

```json
{
  "schemaVersion": 1,
  "name": "linen",
  "title": "Linen",
  "version": "1.0.0",
  "tagline": "Light linen canvas, hairline seams, one teal thread.",
  "class": "app-theme-linen",
  "compatibility": {
    "apex": ">=26.1.0 <26.2.0",
    "themeNumber": 42,
    "baseTheme": "ut-26.1",
    "themeStyle": "Iris"
  },
  "templateOptions": {
    "navigationMenuStyle": "t-TreeNav--styleB"
  },
  "fonts": {
    "body": {
      "family": "Example Sans",
      "fallback": ["Oracle Sans", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
      "license": "licenses/OFL-Example-Sans.txt",
      "faces": [
        {"file": "fonts/example-sans-400-normal.woff2", "weight": 400, "style": "normal"},
        {"file": "fonts/example-sans-700-normal.woff2", "weight": 700, "style": "normal"}
      ]
    },
    "heading": {
      "family": "Example Display",
      "fallback": ["Oracle Sans", "sans-serif"],
      "license": "licenses/OFL-Example-Display.txt",
      "faces": [
        {"file": "fonts/example-display-700-normal.woff2", "weight": 700, "style": "normal"}
      ]
    },
    "mono": {
      "family": "Example Mono",
      "fallback": ["SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      "license": "licenses/OFL-Example-Mono.txt",
      "faces": [
        {"file": "fonts/example-mono-400-normal.woff2", "weight": 400, "style": "normal"}
      ]
    }
  },
  "assets": {
    "stylesheet": "theme.css",
    "runtime": "theme-factory-runtime.js",
    "cover": "preview/cover.jpg"
  }
}
```

`name` must match the package directory and `class` must equal `app-theme-<name>`. `version` uses semantic versioning. The entire `fonts` object is optional. When it exists, `body` is required; `heading` and `mono` are optional. Each role requires one or more faces, a non-empty bundled license file, a fallback list, an integer weight from 100 through 900, and style `normal` or `italic`. Version one permits only the manifest keys shown above; unknown keys fail validation so a misspelling cannot silently change installation behavior.

### 4.2 Custom fonts

Custom fonts are self-hosted theme assets. Sources live under `sample-themes/<name>/fonts/` and their licenses under `sample-themes/<name>/licenses/`; the package builder copies only files referenced by the manifest. External font URLs, CSS imports, data URLs, OpenType/TrueType files, and unlicensed font files are rejected.

Every font file must:

- use a lower-kebab-case `.woff2` filename;
- begin with the WOFF2 signature `wOF2`;
- remain within the theme package's `fonts/` directory;
- be referenced by at least one declared role and face, with no duplicate `(file, weight, style)` tuple inside one role;
- have a referenced, non-empty license under `licenses/`.

The CSS builder generates `@font-face` declarations before the flattened theme CSS with `font-display: swap`. Generated family identifiers are package-prefixed, such as `ThemeFactory-linen-body`, so separately installed packages cannot collide even if their manifests use the same display family name. Font usage remains scoped through these tokens on `html.app-theme-<name>`:

```css
--app-font-family-body: "ThemeFactory-linen-body", "Oracle Sans", sans-serif;
--app-font-family-heading: "ThemeFactory-linen-heading", "Oracle Sans", sans-serif;
--app-font-family-mono: "ThemeFactory-linen-mono", SFMono-Regular, Menlo, monospace;
```

The body role aliases the Iris base text family only while the package class is active. Heading selectors use the heading token only when that role exists; an omitted heading role resolves to Oracle Sans. An omitted mono role resolves to Iris' `--a-base-font-family-mono`. No theme rule sets `font-family` on icon elements or replaces Font APEX.

### 4.3 Stylesheet

`theme.css` is a flattened build artifact in this order:

1. `static-files/css/foundation/tokens.css`
2. `static-files/css/foundation/reset.css`
3. `static-files/css/foundation/typography.css`
4. `static-files/css/foundation/utilities.css`
5. the recursively resolved imports from `sample-themes/<name>/css/theme.css`

The build rejects remote imports, imports outside the two approved source roots, cycles, missing files, and duplicate imports. Source maps are not required. The output retains `html.app-theme-<name>` scoping so several separately installed ZIPs can coexist without activating one another.

The build banner records the theme name, package version, compatibility boundary, and source commit. It does not embed a wall-clock timestamp, so two builds from the same committed source are byte-for-byte identical.

Relative font URLs in generated `@font-face` declarations use `./fonts/<file>.woff2`; the installed stylesheet and its fonts retain that directory relationship. The build rejects an external URL, data URL, absolute path, undeclared font file, or declared file omitted from the ZIP.

### 4.4 Checksums

`checksums.sha256` covers every regular file in the ZIP except itself. `install.sh` and `uninstall.sh` verify the checksums before reading the manifest or touching a target. A mismatch exits before SQLcl is started.

## 5. Target-Owned Static Files

An installed package owns only this namespace in the target application's static files:

```text
theme-factory/packages/<theme-name>/<version>/theme.css
theme-factory/packages/<theme-name>/<version>/theme.json
theme-factory/packages/<theme-name>/<version>/cover.jpg
theme-factory/packages/<theme-name>/<version>/fonts/<font-file>.woff2
theme-factory/packages/<theme-name>/<version>/licenses/<font-license>.txt
theme-factory/runtime/theme-factory-runtime.js
theme-factory/runtime/registry.json
```

The target application's CSS URL references the versioned package stylesheet. The JavaScript URL is added only when switcher support is enabled. Installer-owned APEXLang blocks and components include the marker `APEX_THEME_FACTORY_MANAGED`; uninstallation may remove only marked content and the namespace above.

`registry.json` is regenerated from the manifests currently installed under `theme-factory/packages/`. It contains package name, title, version, class, and stylesheet URL. It never contains a second theme's CSS or embeds package manifests.

## 6. SQLcl Installer Interface

Each ZIP exposes:

```text
./install.sh --connection <saved-connection> --workspace <workspace> --app-id <number> [--with-switcher | --without-switcher] [--backup-dir <directory>] [--apply]
```

Behavior:

- Without `--apply`, perform a complete dry-run and exit without importing.
- `--with-switcher` explicitly enables or updates the shared switcher integration.
- `--without-switcher` explicitly disables the visible switcher and selects this package as the fixed default.
- With neither switcher flag, preserve the target's existing Theme Factory switcher state; a target with no prior integration receives fixed-theme mode.
- `--backup-dir` defaults to `./theme-factory-backups`; the installer never writes to an implicit home directory.
- Reject unknown arguments, missing values, non-numeric application IDs, invalid workspace names, and unsafe theme names.
- Never echo saved-connection secrets, SQLcl connection details, checksums containing secret paths, or database passwords.

### 6.1 Preflight

The installer must:

1. Verify `sql` is available and obtain its version.
2. Verify every ZIP checksum.
3. Validate `theme.json` locally.
4. Connect using the named SQLcl saved connection.
5. Query the selected workspace and application by exact ID.
6. Confirm APEX version matches `26.1.x`.
7. Confirm the application uses theme 42, base theme `ut-26.1`, and current style `Iris`.
8. Print application ID, alias, name, workspace, APEX version, theme number, base theme, and style.
9. Refuse if more than one candidate application or theme-style row is returned.

### 6.2 Fresh-export staging

The installer creates a unique temporary directory with `mktemp -d`, exports the selected application as split APEXLang with `-skipexportdate`, and resolves the generated alias directory from the export rather than assuming `applications/ut`.

The unmodified export is copied to:

```text
<backup-dir>/<workspace>-<app-id>/<UTC timestamp>-before-<theme-name>/
```

It also records `target.json` with the confirmed target metadata, source digest, SQLcl version, package version, and command mode. The backup contains no credentials.

### 6.3 Narrow APEXLang patch

The patcher supports the exact APEXLang shapes emitted by SQLcl for APEX 26.1.x and refuses every ambiguous structure. It performs only these changes:

- copy package files into `shared-components/static-files/theme-factory/...`;
- add or update their `file "..."` entries in `shared-components/static-files.apx`;
- add the package stylesheet URL to the application CSS file URLs without disturbing existing entries;
- apply the manifest's navigation template option only when the target uses the compatible side-navigation template and the requested option is valid;
- create or update marked Global Page bootstrap regions for standard and dialog/drawer/wizard positions;
- when `--with-switcher` is present, add the runtime URL and one marked native navigation-bar list entry, then regenerate its choices from `registry.json`;
- when `--without-switcher` is present, remove only the marked switcher UI/runtime reference and apply the installed package as the fixed default;
- when neither flag is present, preserve the existing switcher state and use fixed-theme mode only if no Theme Factory integration already exists.

If page 0 is absent, the installer creates a minimal Global Page through APEXLang and sets the application's `globalPage` reference. If an unmarked component occupies a required identity or a safe insertion point cannot be proved, installation refuses and points to `MANUAL-INSTALL.md`.

### 6.4 Validation and drift guard

After patching, the installer:

1. runs `apex validate` against the staged export;
2. requires `Validation successful.` with no warnings;
3. prints a summary and unified diff limited to Theme Factory-owned changes;
4. exports the live target a second time immediately before import;
5. compares its canonical digest with the original source digest;
6. refuses if the application changed during staging.

With `--apply`, the installer prints the exact target again and requires the user to type the numeric application ID. It then validates and imports the staged export in one SQLcl session. A `--yes` or bypass flag is intentionally absent from version one.

### 6.5 Post-install verification

After import, the installer reconnects read-only and confirms:

- target application ID and alias are unchanged;
- package static files exist with expected sizes;
- every declared font and license exists with its expected checksum;
- the stylesheet URL is present once;
- the runtime URL and switcher component are present exactly when requested;
- theme 42 and Iris remain current.

Runtime visual, accessibility, and console verification remains a release gate described in the verification specification; the installer must not claim visual success from database checks alone.

## 7. Optional Switcher and Persistence

Each ZIP still contains one theme. Installing several ZIPs creates several independent installed packages, which the optional shared switcher discovers through `registry.json`.

Switcher choices are:

- every installed Theme Factory package;
- `Iris`, meaning no package class is applied.

The switcher uses Universal Theme's native navigation menu and radio-group semantics. It must expose `role="menuitemradio"`, a single checked choice, keyboard operation, and an accessible label. It must not inject a floating custom control.

The selection is stored in:

```text
localStorage["apex.themeFactory.<APP_ID>"]
```

Allowed values are an installed package name or `iris`. The Global Page bootstrap embeds the exact application ID, default package, switcher-enabled flag, and installed-name allowlist, then applies the selected class before content paint on standard and dialog-family templates.

Persistence is per browser profile and device. It survives reloads and APEX sessions but does not follow an authenticated user to another browser. No database preference is created.

When switcher support is disabled, the bootstrap ignores local storage and always applies the configured default package. When switcher support is enabled and the saved value is invalid or no longer installed, it removes that value and applies the configured default; if no package remains, it applies bare Iris.

## 8. Uninstallation and Recovery

`uninstall.sh` accepts the same target arguments and is dry-run by default. It fresh-exports, backs up, validates target compatibility, and removes only:

- the selected package's namespaced static files;
- its stylesheet URL;
- its registry entry;
- marked switcher/bootstrap content that is no longer needed.

If other packages remain, their integration is preserved and the default is chosen deterministically: the existing valid default first, otherwise the lexicographically first installed package. If none remain, Theme Factory bootstrap/runtime/list content is removed and Iris remains active.

If an owned block differs from the installed checksum or marker contract, uninstallation refuses rather than deleting user-modified content. Recovery is performed by importing the recorded pre-operation backup through SQLcl after explicit target confirmation.

## 9. Manual APEX Builder Installation

Every ZIP's `MANUAL-INSTALL.md` contains two paths:

### Fixed theme

1. Verify APEX 26.1.x, Universal Theme 42, and Iris.
2. Upload `theme.css`, `theme.json`, every declared `fonts/*.woff2`, and every referenced font license as application static files while preserving their packaged paths.
3. Add the stylesheet URL to Shared Components → User Interface Attributes → Cascading Style Sheets.
4. Add the two provided Global Page bootstrap regions and set the packaged theme as default.
5. Apply the documented compatible navigation template option if the application uses side navigation.
6. Run the supplied browser verification checklist.

For a font-bearing package, the checklist confirms every face returns HTTP 200 with `font/woff2`, `document.fonts.check()` succeeds for each declared role and weight, fallback stacks remain present, and Font APEX icons retain their computed icon family.

### Theme with switcher

Perform the fixed-theme steps, then upload the runtime and registry, add the runtime file URL, add the documented native navigation-bar list entry, and verify radio/keyboard behavior. The guide includes complete copyable APEXLang/HTML/JavaScript snippets generated for that package; it does not say “repeat the automated process manually.”

The manual guide also documents uninstall and recovery steps.

## 10. Failure Semantics

Every failure exits non-zero and states whether the target was untouched, staged only, or imported. The installer must distinguish:

- invalid package;
- unsupported target;
- ambiguous APEXLang structure;
- validation failure;
- live-target drift;
- explicit user cancellation;
- import failure;
- post-install verification failure.

No error path deletes backups. Temporary staging may be removed only after its path is verified as a child of the directory created by `mktemp -d`.

## 11. Acceptance Criteria

- Linen and Solarized Dark each build into a single-theme ZIP with valid checksums.
- Extracting a ZIP outside the repository is sufficient to run dry-run, install, uninstall, and follow the manual guide.
- A package stylesheet has no unresolved local imports or missing shared `--app-*` definitions.
- A font-bearing fixture packages only declared WOFF2 faces and licenses, uses package-prefixed family identifiers, loads each face from the target application, and leaves Font APEX icons unchanged.
- A package with no `fonts` object continues to use Iris typography without generating font files or `@font-face` declarations.
- External URLs, data URLs, invalid WOFF2 signatures, missing licenses, undeclared files, duplicate face references, and paths outside `fonts/` or `licenses/` fail before ZIP creation.
- Dry-run makes no database changes.
- Wrong application ID, wrong workspace, non-Iris style, non-26.1 APEX, target drift, and ambiguous APEXLang all refuse before import.
- A confirmed install preserves unrelated target components and existing CSS/JavaScript URLs.
- Reinstalling the same version is idempotent.
- Installing a second package preserves the first package.
- Switcher-disabled mode always activates the selected package.
- Switcher-enabled mode lists installed packages plus Iris and persists selection under the application-namespaced browser key.
- Uninstall removes only owned content and always leaves a validated application or refuses without importing.
