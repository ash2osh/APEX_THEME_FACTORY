# APEX Theme Factory

**[Live demo: try all eight themes](https://oracleapex.com/ords/r/orochimaru/theme-factory-demo/themes)**, and switch between them from the Theme menu.

**Eight ready-made themes for Oracle APEX. Change how an app looks without changing the app.**

Each theme is a small CSS package that sits on top of Universal Theme. Your pages, regions and business logic stay
as they are. Remove the theme, and the app goes back to the standard look.

| | |
|---|---|
| [![Carbon Volt](sample-themes/carbon-volt/preview/cover.jpg)](sample-themes/carbon-volt/)<br>**Carbon Volt** (dark)<br>Graphite surfaces with acid lime and cyan. | [![Citrus Pop](sample-themes/citrus-pop/preview/cover.jpg)](sample-themes/citrus-pop/)<br>**Citrus Pop** (light)<br>Fresh aqua, deep teal and tangerine. |
| [![Cobalt Press](sample-themes/cobalt-press/preview/cover.jpg)](sample-themes/cobalt-press/)<br>**Cobalt Press** (light)<br>Warm paper with cobalt and vermilion. | [![Estate Slate](sample-themes/estate-slate/preview/cover.jpg)](sample-themes/estate-slate/)<br>**Estate Slate** (light)<br>Corporate slate and champagne amber. |
| [![Estate Slate Dark](sample-themes/estate-slate-dark/preview/cover.jpg)](sample-themes/estate-slate-dark/)<br>**Estate Slate Dark** (dark)<br>Deep slate with amber and emerald. | [![Linen](sample-themes/linen/preview/cover.jpg)](sample-themes/linen/)<br>**Linen** (light)<br>Quiet white surfaces and one teal accent. |
| [![Solarized Dark](sample-themes/solarized-dark/preview/cover.jpg)](sample-themes/solarized-dark/)<br>**Solarized Dark** (dark)<br>Terminal cyan and deep Solarized blues. | [![Velvet Signal](sample-themes/velvet-signal/preview/cover.jpg)](sample-themes/velvet-signal/)<br>**Velvet Signal** (dark)<br>Aubergine depth and fuchsia signals. |

All eight meet WCAG AA text contrast on the reference app's pages, except its palette demo page (see
[Known issues](#known-issues)). All of them work on phones and respect the reduced-motion setting. Six bundle fonts
that include Arabic. You can install one theme, or install several and let people switch from a menu.

## Requirements

| You need | Details |
|---|---|
| Oracle APEX 26.1 or 26.2 | With Universal Theme 42 and the **Iris** style. New apps on 26.1 or later already use it. An older app needs [a theme refresh](docs/GET_STARTED.md#is-my-app-ready). |
| SQLcl, with a saved connection | [How to set it up](docs/GET_STARTED.md#what-you-need). |
| Python 3.10 or newer | Windows, macOS and Linux all work. |

No SQLcl? You can [install a theme by hand](docs/GET_STARTED.md#installing-by-hand) in App Builder.

## Quick start

Download a theme ZIP from the [Releases page](https://github.com/ash2osh/APEX_THEME_FACTORY/releases), extract it,
and open a terminal in the extracted folder.

**On Linux and macOS:**

```bash
./install.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>            # preview, changes nothing
./install.sh --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --apply    # install
```

**In Windows PowerShell:**

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>            # preview, changes nothing
powershell -ExecutionPolicy Bypass -File .\install.ps1 --connection <CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --apply    # install
```

The installer asks you to type the app ID before it changes anything. The [Get started guide](docs/GET_STARTED.md)
covers every step.

## Before you install on a live app

The installer previews first, saves a backup of your app's source, and only adds its own files and regions. It also
sets the navigation menu style, and it puts that back when you remove the last theme.

But APEX imports the whole app in one step, so:

- **Every active session of the app ends.** Install in a quiet period.
- **Private saved reports and role assignments stay.**
- **Translations stay, with one exception.** On APEX 26.1, Oracle's APEXLang format doesn't support the older
  Application-Based translations, so those apps need [a manual install](docs/GET_STARTED.md#if-your-app-is-translated).

Try it on a copy of your app first. [Get started](docs/GET_STARTED.md#before-you-install-on-a-shared-or-production-app)
has the details.

## Guides

| I want to… | Read |
|---|---|
| Install a theme in my app | [Get started](docs/GET_STARTED.md) |
| Remove a theme, or undo an install | [Undo an install](docs/GET_STARTED.md#undo-an-install) |
| Put a live demo of all the themes online | [Put the demo online](docs/PUBLIC_DEMO.md) |
| Build my own theme | [Building and releasing a theme](docs/BUILDING_A_THEME.md) |
| Fix something or add a theme to this project | [Contributing](CONTRIBUTING.md) |
| Report a security problem | [Security](SECURITY.md) |
| See what changed | [Changelog](CHANGELOG.md) |

## How it was tested

| Check | Coverage |
|---|---|
| Every page of the reference app | 123 pages, all eight themes, APEX 26.1 and 26.2, desktop and phone width: text contrast, layout overflow and console errors, with stock Iris as the control |
| Real installs | All eight themes on APEX 26.1 and 26.2. Upgrade, uninstall and restore on 26.2. All run on Linux |
| Install scripts on Windows and macOS | Run in CI against a simulated SQLcl, not a real database |
| Right-to-left | A 14-page sample in all eight themes, using the reference app's RTL switch, not a fully translated Arabic app |
| Translated apps | Both APEX translation methods, with the app checked in a French browser. See [the results](docs/GET_STARTED.md#if-your-app-is-translated) |
| Printing | Checked on a dark theme: dark themes print with their background so the text stays readable, which uses a lot of ink |

## Known issues

You only see these if you browse the reference app. They also happen with stock Iris, so they aren't theme defects.

| Where | What happens |
|---|---|
| Palette page 6302 | Palette colours used as text fail AA contrast. Only a change to the palette itself could fix that. |
| Page 3110 | Automated contrast checks flag card titles over images. This is a false alarm, because the check can't see the image. |
| Dialog pages 1111, 1112 and 1912–1922 | Opened by direct URL, they show APEX's dialog-template error. They work when opened from their buttons. |
| Pages using `EBA_UT_*` tables | They show an error until you [install the sample data](docs/PUBLIC_DEMO.md#step-4-install-the-sample-data). |
| Map page 1906 | The map needs internet access for its tiles. |

## License

The themes and tooling are [MIT licensed](LICENSE). Bundled fonts and other third-party material keep their own
terms, listed in [NOTICE.md](NOTICE.md).

The reference app in `applications/ut/` is based on Oracle's Universal Theme Reference sample, which Oracle publishes
under the Universal Permissive License 1.0. Oracle's Universal Theme runtime files aren't in this project: they ship
with APEX. This project isn't affiliated with or endorsed by Oracle.
