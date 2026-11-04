# Contributing

Bug reports, fixes and new themes are welcome.

## Report a bug

Open an issue with the theme name and version, your APEX version, the page, and a screenshot. If the same page looks
wrong with no theme, it's probably a Universal Theme issue and not a theme issue.

## Change something

```bash
git clone https://github.com/ash2osh/APEX_THEME_FACTORY.git
cd APEX_THEME_FACTORY
python3 -m pip install -r tools/test-requirements.txt
tests/run-offline.sh    # must end with OFFLINE status=PASS
```

- You need Python 3.10 or newer. `tests/run-offline.sh` and the `scripts/apex-*.sh` scripts need bash, so on Windows
  run those in Git Bash or WSL. `scripts/theme.ps1`, `install-all-themes.ps1` and `build-demo.ps1` work in PowerShell.
- `tests/run-offline.sh` needs no database and no browser, and CI runs the same script.
- To add a theme, follow [Building and releasing a theme](docs/BUILDING_A_THEME.md).
- A theme colour change edits `css/tokens.css` and `theme.recipe.json` together.
- Generated files are never edited by hand. `AGENTS.md` lists them.
- Add a line to [CHANGELOG.md](CHANGELOG.md), and raise the theme's version in `theme.json` when its CSS changes.

## Licensing

Your contribution is released under the [MIT licence](LICENSE). Don't copy Oracle's Universal Theme runtime files
(`Core.min.css`, `Iris.min.css`, `theme42.min.js` and so on) into this repository or into a theme. A bundled font
needs an open licence, and its licence file goes in the theme's `licenses/` folder. If that licence reserves the font
name, a converted or subset file has to be renamed.
