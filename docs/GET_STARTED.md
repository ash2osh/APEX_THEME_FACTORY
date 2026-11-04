# Get started

This guide takes you from nothing to a working theme in your APEX app. It takes about 15 minutes once your tools are
set up.

## What you need

| Item | How to check it |
|---|---|
| Oracle APEX 26.1.x or 26.2.x | Run `select version_no from apex_release;` in SQL Workshop. |
| Universal Theme 42 with the Iris style | New apps on 26.1 or later already use it. Otherwise see [Is my app ready?](#is-my-app-ready) |
| SQLcl, with a saved connection | Run `sql -name <CONNECTION>`. You should reach the SQL prompt. |
| Python 3.10 or newer | Run `python3 --version`, or `py -3 --version` on Windows. |
| Your workspace name and app ID | Both are shown in App Builder. |

No SQLcl, or no way to run scripts? [Installing by hand](#installing-by-hand) needs only App Builder.

### Set up SQLcl

1. Download [SQLcl](https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/) and add its `bin` folder to
   your PATH. SQLcl also needs Java.
2. Save a connection to your app's parsing schema. Run `sql /nolog`, and then run this at the SQL prompt:

   ```sql
   conn -save <CONNECTION> -savepwd <SCHEMA>@//<HOST>:<PORT>/<SERVICE>
   ```

   SQLcl asks for the password and stores it in your user profile.

## Is my app ready?

Apps created on APEX 26.1 or later are ready. An app that came from an older version usually isn't, because Iris only
appears after a theme refresh, and the installer stops with exit code 3. To prepare it, work on a copy of the app:

1. In App Builder, open the app. If a banner says a new version of Universal Theme is available, click
   **Refresh Theme**. If there is no banner, go to **Shared Components > Themes**, open **Universal Theme**, click
   **Verify**, and then click **Refresh Theme**.
2. Go to **Shared Components > User Interface Attributes**, set **Theme Style** to **Iris**, and click
   **Apply Changes**. A refresh can change the current style, so check this even if you had already picked Iris.
3. Run the app and check it. A custom style from Theme Roller doesn't carry over, because these themes replace it.

Then run the preview in Step 2 to confirm that the app is ready.

## Before you install on a shared or production app

The installer changes only its own items, but APEX imports the whole app in one step. That has these effects:

| Item | What happens to it | Is it in the backup? |
|---|---|---|
| Active user sessions | **They end.** People have to sign in again, and unsaved work is lost. Install in a quiet period. | No |
| Filters a person applied without saving a report | **They are lost** along with the session. | No |
| Private saved reports | Kept. | No, they stay in the database |
| Access-control role assignments | Kept. | No, they stay in the database |
| Translated text | **It would be erased**, so the installer stops. See below. | No |

These results come from real installs on APEX 26.2. Try the install on a copy of your app first, and keep your usual
app and database backups as well.

**If your app is translated,** use [Installing by hand](#installing-by-hand), because it imports nothing and your
translations stay. If you're able to seed, translate and publish again afterwards, you can accept the loss by adding
`--discard-translations`. The uninstall and restore scripts have the same check and option.

## Step 1: Get a theme package

Each package is one ZIP that holds exactly one theme. Get it in one of these two ways.

**A. Download it** from the [Releases page](https://github.com/ash2osh/APEX_THEME_FACTORY/releases), and compare its
checksum with the value in `SHA256SUMS.txt` from the same release.

On Linux:

```bash
sha256sum linen-<version>.zip
unzip linen-<version>.zip -d ~/theme
cd ~/theme/linen-<version>
```

On macOS:

```bash
shasum -a 256 linen-<version>.zip
unzip linen-<version>.zip -d ~/theme
cd ~/theme/linen-<version>
```

In Windows PowerShell:

```powershell
Get-FileHash .\linen-<version>.zip -Algorithm SHA256
Expand-Archive .\linen-<version>.zip -DestinationPath $HOME\theme
cd $HOME\theme\linen-<version>
```

> A checksum proves that the file is complete. It does not prove who made it. Install only packages from a source you
> trust.

**B. Build it** from this repository.

On Linux and macOS:

```bash
git clone https://github.com/ash2osh/APEX_THEME_FACTORY.git
cd APEX_THEME_FACTORY
scripts/theme.sh release linen --offline
unzip dist/linen/linen-<version>.zip -d ~/theme
cd ~/theme/linen-<version>
```

In Windows PowerShell:

```powershell
git clone https://github.com/ash2osh/APEX_THEME_FACTORY.git
cd APEX_THEME_FACTORY
powershell -ExecutionPolicy Bypass -File .\scripts\theme.ps1 release linen --offline
Expand-Archive .\dist\linen\linen-<version>.zip -DestinationPath $HOME\theme
cd $HOME\theme\linen-<version>
```

Replace `<version>` with the version in the file name, for example `1.2.0`.

## Step 2: Preview the install

On Linux and macOS:

```bash
./install.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>
```

In Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>
```

`-ExecutionPolicy Bypass` applies to this one command, and it's needed because Windows blocks scripts by default.
Every other script in this guide works the same way: replace `./name.sh` with
`powershell -ExecutionPolicy Bypass -File .\name.ps1`.

If macOS or Linux says `permission denied`, run `bash install.sh` with the same options.

The preview does **not** change your app. It copies the app, applies the theme to the copy, checks that it compiles,
and prints what would change. You can run it as often as you like. Check these points in the output:

- The theme name and version are the ones you expect.
- The list of files to add looks right.
- An older Theme Factory install is upgraded, not duplicated.

## Step 3: Install

Add `--apply` to the same command:

```bash
./install.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --apply
```

The installer asks you to type the app ID. If you type anything else, it stops and changes nothing.

Before it installs, the installer saves a backup of the app's source in `theme-factory-backups/`. Keep this folder, and
keep it private, because it holds your app's source. You need it to restore the app.

To add a **Theme** menu to the navigation bar, also add `--with-switcher`. The menu lets each person pick a theme, and
the choice is saved in their browser only. The navigation bar must be a static list.

## Step 4: Check the result

1. Open any page of the app. It should show the new theme.
2. The browser console (F12) should show no errors.
3. If you added the switcher, open the **Theme** menu. One entry should be checked.

If the page looks unchanged, open the browser's developer tools and look at the `<html>` element. It should have a
class named `app-theme-<name>`.

## Undo an install

**To remove the theme and keep the app,** run the uninstall script. Preview it first, then add `--apply`:

```bash
./uninstall.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>            # preview
./uninstall.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --apply    # remove
```

It removes only what the install recorded, and it refuses to continue if one of those files has been edited since. If
two themes are installed, the other one keeps working and becomes the default. Removing the last one leaves the app
on standard Iris, with the navigation menu style put back. Active sessions end, as they do for an install.

**To go back to the exact app from before the install,** restore the backup:

```bash
./restore.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> \
  --backup ./theme-factory-backups/<WORKSPACE>-<APP_ID>/<BACKUP_FOLDER> --apply
```

This replaces the whole application with the backup, so anything you changed in the app after the install would be
lost. The script checks for that and stops unless you add `--discard-later-changes`. It rejects a backup whose contents
have been modified.

## If something goes wrong

The scripts end with an exit code. Use this table to find the cause.

| Code | What it means | What to do |
|---|---|---|
| 0 | The script finished, or the preview finished. | Nothing. |
| 2 | The package or a command option is wrong, or Python or SQLcl wasn't found. Nothing changed. | Read the message. Check that the ZIP is complete, and that Python and `sql` are installed and on your PATH. |
| 3 | The script refused before it changed anything. The APEX version or theme style isn't supported, or the app has translated text. | See [Is my app ready?](#is-my-app-ready) and [Before you install](#before-you-install-on-a-shared-or-production-app). |
| 4 | Someone changed the app while the script ran. | Run the preview again. |
| 5 | Export, compile or import failed. | Read the message. If the app is broken, restore the backup. |
| 6 | The script finished, but the check afterwards found a difference. | Read the message. Restore the backup if the app doesn't work. |
| 7 | You cancelled at the prompt, or a restore would lose later changes. | Nothing changed. |

## Reference

You don't need these sections for a normal install.

### Installing by hand

`MANUAL-INSTALL.md` inside every package lists each step in App Builder: which files to upload, the region to create,
and the CSS file URL to add, plus the matching removal steps. It needs no SQLcl or Python. It imports nothing, so
active sessions and translations aren't affected.

### Install several themes at once

From this repository, you can install all eight themes in one step, with the **Theme** menu:

```bash
scripts/install-all-themes.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>            # preview
scripts/install-all-themes.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --apply    # install
```

In Windows PowerShell, the script is `.\scripts\install-all-themes.ps1`.

| Option | What it does |
|---|---|
| `--themes <list>` | Installs only these themes, comma-separated, built from `sample-themes/`. The last one becomes the default. |
| `--packages <zip,...>` | Installs these exact ZIP files instead. |
| `--with-switcher` / `--without-switcher` | Adds the **Theme** menu or leaves it out. The default adds it, and a navigation bar that isn't a static list is refused. |
| `--backup-dir <dir>` | Sets where the backup goes. The default is `theme-factory-backups/`. |
| `--discard-translations` | Accepts that the import erases translated text. |

### What the installer changes

Everything it owns is marked, so it can be removed exactly.

- **Adds** static files under `theme-factory/packages/<name>/<version>/` (the CSS, `theme.json`, the preview image, and
  any fonts), plus `theme-factory/runtime/registry.json`.
- **Adds** two hidden Page 0 regions with the bootstrap script. Their Static IDs are `theme_factory_bootstrap` and
  `theme_factory_bootstrap_dialog`. An app with no Page 0 gets one, and it stays.
- **Adds** `#APP_FILES#theme-factory/packages/<name>/<version>/theme.css` to the application's CSS file URLs.
- **Sets** the Side Navigation Menu's style option when the theme asks for one (most use Style B). The first install
  records the old value, and removing the last theme puts it back.
- **With `--with-switcher` only:** adds list entries with the `theme-factory-` Static ID prefix, and the switcher script.

It doesn't touch your pages, processes, items, or any file it didn't create. It records a SHA-256 for each file it owns.
Running the installer again is safe: it finds its previous install and upgrades in place.

### Very large apps

Each SQLcl call stops after 30 minutes. For a very large app, set `THEME_FACTORY_SQLCL_TIMEOUT` to a higher number of
seconds. If a call is stopped during the import, check the app and restore the backup if it needs it.
