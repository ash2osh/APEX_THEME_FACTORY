# APEX Theme Factory

Change how an Oracle APEX app looks, without changing the app itself.

This project builds **themes** for Oracle APEX. A theme is a small CSS package. You install it into an APEX app
with one command. Your pages, regions and business logic stay the same. If you remove the theme, the app goes
back to the standard Universal Theme look.

## Which APEX version do I need?

| APEX version | Status |
|---|---|
| 26.1.x | Supported |
| 26.2.x | Supported |

Both versions use **Universal Theme 42** with the **Iris** style. Iris is the only style these themes support.
The installer checks your version first, and it stops when the version is not supported. Read
[Known issues](#known-issues) before you install on a shared or production app.

## Start here

| I want to… | Read this |
|---|---|
| Install a theme in my APEX app (start here if you are new) | [Get started](docs/GET_STARTED.md) |
| Remove a theme, or undo an install | [Undo an install](docs/GET_STARTED.md#undo-an-install-restore) |
| Build my own theme | [Building and releasing a theme](docs/BUILDING_A_THEME.md) |
| Release a theme | [Releasing a theme](docs/BUILDING_A_THEME.md#releasing-a-theme) |

## Quick start

You need an APEX app, a saved SQLcl connection and a theme package. The
[Get started guide](docs/GET_STARTED.md) explains each step.

1. **Check your APEX version.** Run this in SQL:

   ```sql
   select version_no from apex_release;
   ```

2. **Preview the install.** This changes nothing:

   ```bash
   ./install.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>
   ```

3. **Install for real.** You type the app ID to confirm:

   ```bash
   ./install.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --apply
   ```

`install.sh` comes inside each theme package. The [Get started guide](docs/GET_STARTED.md) shows how to build one.

## Safe by design

- **Preview first.** The installer does nothing until you add `--apply`.
- **Backup first.** Before it changes anything, it saves a full copy of your app.
- **Only its own files.** It never edits your pages, regions, processes or items.
- **Easy undo.** You can remove the theme, or restore the backup.

## The eight themes

[Carbon Volt](sample-themes/carbon-volt/) · [Citrus Pop](sample-themes/citrus-pop/) ·
[Cobalt Press](sample-themes/cobalt-press/) · [Estate Slate](sample-themes/estate-slate/) ·
[Estate Slate Dark](sample-themes/estate-slate-dark/) · [Linen](sample-themes/linen/) ·
[Solarized Dark](sample-themes/solarized-dark/) · [Velvet Signal](sample-themes/velvet-signal/)

## Known issues

| Area | What happens | Status |
|---|---|---|
| Reference app 102 on APEX 26.2 | The app is not re-imported from this source yet. Page 3007 has a third metric card demo that APEX 26.2 rejects with `column TICKER not found`. Your 26.2 copy of the app was updated by hand, so it still runs. | Open. Needs a decision on the demo. |
| Charts on the local APEX 26.1.5 test stack | Chart data calls return HTTP 404, so the Theme Lab charts do not draw. The stack pairs ORDS 26.3 with APEX 26.1.5. This is the likely cause, not yet confirmed. | Open. Environment issue. |
| Saved-report styling in dark themes | The rules now cover the APEX 26.2 saved-report group as well as the 26.1 element. No saved report was on the test page, so this is not checked visually. | Not verified. |

## For developers

```bash
tests/run-offline.sh    # offline checks; ends with OFFLINE status=PASS
```

Live checks need a database and a browser. See [Releasing a theme](docs/BUILDING_A_THEME.md#releasing-a-theme).

## License

MIT. See [LICENSE](LICENSE). Third-party material keeps its own terms. See [NOTICE.md](NOTICE.md).
Oracle's Universal Theme files are not redistributed. `scripts/fetch-vendor.sh --reference` fetches them from your
own APEX instance.
