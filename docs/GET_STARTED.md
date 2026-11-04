# Get started

This guide takes you from nothing to a working theme in your APEX app. It takes about 15 minutes.

## What you need

| Item | How to check it |
|---|---|
| Oracle APEX 26.1.x or 26.2.x | Run `select version_no from apex_release;` in SQL. |
| Universal Theme 42 with the Iris style | This is the default. You do not need to change it. |
| SQLcl 26.x with a saved connection | Run `sql -name <CONNECTION>`. You should reach the SQL prompt. |
| Python 3.10 or newer | Run `python3 --version`. |
| Your workspace name and app ID | Both are shown in App Builder. |

## Step 1: Get a theme package

Use one of these two ways.

**A. Build it from this repository** (for developers):

```bash
scripts/theme.sh release linen --offline
unzip dist/linen/linen-<version>.zip -d ~/theme
cd ~/theme/linen-<version>
```

Replace `<version>` with the version in the file name, for example `1.1.0`. Each package is one ZIP file that holds exactly one theme. The extracted folder has its own `install.sh`.

**B. Get a ZIP from a publisher.** Check its SHA-256 checksum against the value the publisher lists:

```bash
sha256sum linen-1.0.0.zip
```

> A checksum proves that the file is complete. It does not prove who made the file. Install only packages from a
> source you trust.

## Step 2: Preview the install

```bash
./install.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>
```

This command does **not** change your app. It copies the app, applies the theme to the copy, checks that it
compiles, and prints what would change. You can run it as often as you like.

Read the output before you go on. Check these points:

- The theme name and version are the ones you expect.
- The list of files to add looks right.
- An older Theme Factory install is upgraded, not duplicated.

## Step 3: Install

```bash
./install.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --apply
```

The installer asks you to type the app ID. If you type anything else, it stops and changes nothing.

Before it installs, the installer saves a full backup in `theme-factory-backups/`. Keep this folder. You need
it to restore the app.

To add a **Theme** menu to the navigation bar, add `--with-switcher` to the command. The menu lets each person
pick a theme. The choice is saved in their browser only.

## Step 4: Check the result

1. Open any page of the app.
2. Open the browser's developer tools and look at the `<html>` element. It should have a class named
   `app-theme-<name>`.
3. The browser console should show no errors.
4. If you added the switcher, open the **Theme** menu. One entry should be checked.

## Step 5: Undo an install

To remove the theme and keep the app:

```bash
./uninstall.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>            # preview
./uninstall.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --apply    # remove
```

To go back to the exact app from before the install, restore the backup. See
[Undo an install (restore)](#undo-an-install-restore) below.

## Install every theme at once (repository)

If you work from this repository, you can install all eight themes in one step:

```bash
scripts/install-all-themes.sh --app-id <APP_ID>            # preview
scripts/install-all-themes.sh --app-id <APP_ID> --apply    # install
```

Add `--connection <CONNECTION>` and `--workspace <WORKSPACE>` if you do not use the defaults
(`docker-demo` and `DEMO`).

## If something goes wrong

The installer ends with an exit code. Use this table to find the cause.

| Code | What it means | What to do |
|---|---|---|
| 0 | The install finished, or the preview finished. | Nothing. |
| 3 | The installer refused before it changed anything. The APEX version, the theme style or the app is not supported. | Check the version in the table under [What you need](#what-you-need). |
| 4 | Someone changed the app while the installer ran. | Run the preview again. |
| 5 | Export, compile or import failed. | Read the message. If the app is broken, restore the backup. |
| 6 | The install finished, but the check afterwards found a difference. | Read the message. Restore the backup if the app does not work. |
| 7 | You cancelled at the prompt. | Nothing changed. |

## Reference

These sections give the full details. You do not need them for a normal install.

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

It runs the same guarded transaction as `scripts/theme.sh install`: APEX 26.1.x or 26.2.x / UT 42 / Iris preflight,
checksum verification, backup, SQLcl validation, drift guard and post-import check.

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

