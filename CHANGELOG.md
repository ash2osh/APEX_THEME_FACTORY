# Changelog

## Unreleased

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

### Themes (each theme's version goes up)

- Citrus Pop, Cobalt Press, Estate Slate: the current item in a top menu bar now meets AA contrast (it was 2.3:1 to 3.25:1).
- Estate Slate: links on the pale info band now meet AA contrast (it was 4.3:1).
- Carbon Volt, Estate Slate Dark, Solarized Dark, Velvet Signal: printing keeps the dark background, so text stays readable.
- Estate Slate, Estate Slate Dark, Solarized Dark: the IBM Plex font files are renamed internally, as the Open Font
  License requires for modified files.

### Theme authors

- `theme.sh cover` no longer refuses a new theme because its cover is missing.
- Adding a theme no longer fails two tests that counted the themes.
- Pushing a `v*` tag builds every package and creates a draft GitHub release.

### Repository

- Oracle's Universal Theme runtime files and the third-party agent skills are removed from the repository and its
  history. The reference app stays, under the licence Oracle publishes it with (UPL 1.0).
