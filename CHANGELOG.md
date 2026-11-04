# Changelog

## Unreleased

### Install and uninstall

- A run that refuses before it imports no longer leaves a backup folder behind. Before, a refused install, such as
  `--with-switcher` on an app whose navigation bar isn't a static list, left a folder that looked restorable but had no
  translations.

## 1.0.1 (2026-11-04)

### Translated apps

- **Application-Based translations now survive an install, uninstall or restore on APEX 26.2.** Version 1.0.0 refused
  these apps. The installer now carries the translations through the import, repairs a bug in the translation file that
  SQLcl generates, seeds and publishes every language again, and compares every translated string with a copy it saved
  first. That copy also puts back text that APEX's own export leaves out, such as Faceted Search and Smart Filter labels
  and item help. Backups include the translations.
- **Text Message-Based translations** are confirmed to survive on 26.1 and 26.2, with no special handling.
- **Application-Based translations on APEX 26.1** can't be handled by the installer, because APEXLang doesn't support
  them on that version. The installer now explains this and the options, instead of showing a raw ORA-20987 error.

## 1.0.0 (2026-11-04)

### Install and uninstall

- An app with translated text is now refused, because an import empties that text. `--discard-translations` accepts
  the loss, and a manual install keeps it.
- A failed import is now reported as a failure. SQLcl exits 0 when an import fails, and the installer used to miss that.
- Running `install.sh` or `uninstall.sh` again from the extracted package folder works. Before this, the first
  backup made the package fail its own check, so every later run stopped with exit code 2.
- Removing the last theme puts the app's navigation menu style back.
- Backup folders are private to your user (mode 700).
- SQLcl calls stop after 30 minutes instead of 5, and `THEME_FACTORY_SQLCL_TIMEOUT` can change that.
- A refused app now gets the steps to refresh Universal Theme and set Iris.
- Each package includes this project's MIT licence.
- The guides now say what an install does to sessions, saved reports, role assignments and translated text.

- Windows PowerShell: every package has `install.ps1`, `uninstall.ps1` and `restore.ps1`, and the repository has
  `scripts/theme.ps1`, `install-all-themes.ps1` and `build-demo.ps1`. CI runs them on Windows and macOS.
- `restore.sh` replaces the long `python3 -m` restore command.
- Get started now explains how to set up SQLcl and is shorter, and the README opens with the themes.

### Themes (Solarized Dark is now 1.3.0, and the others are 1.2.0)

- Citrus Pop, Cobalt Press, Estate Slate: the current item in a top menu bar now meets AA contrast (it was 2.3:1 to 3.25:1).
- Estate Slate: links on the pale info band now meet AA contrast (it was 4.3:1).
- Carbon Volt, Estate Slate Dark, Solarized Dark, Velvet Signal: printing keeps the dark background, so text stays readable.
- Estate Slate, Estate Slate Dark, Solarized Dark: the IBM Plex font files are renamed internally, as the Open Font
  License requires for modified files.

### Theme authors

- `theme.sh cover` no longer refuses a new theme because its cover is missing.
- Adding a theme no longer fails two tests that counted the themes.
- Pushing a `v*` tag builds every package and creates a draft GitHub release.

### Public demo

- `scripts/build-demo.sh` builds one ZIP you can import on public APEX hosting: the reference app with all eight themes,
  under its own name, with a new session-state protection salt. [Put the demo online](docs/PUBLIC_DEMO.md) is the guide.

### Repository

- Oracle's Universal Theme runtime files and the third-party agent skills are removed from the repository and its
  history. The reference app stays, under the licence Oracle publishes it with (UPL 1.0).
