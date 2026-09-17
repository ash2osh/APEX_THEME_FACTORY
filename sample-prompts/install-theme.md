Install a packaged Theme Factory theme into my Oracle APEX application.

**Boundary:** APEX 26.1.x · Universal Theme 42 · theme style **Iris** only. Never switch theme styles, never
use Theme Roller.
**Blast radius:** this writes to a database. Run the dry-run yourself; **stop and wait for my explicit
go-ahead before anything with `--apply`.**
**Browser access:** only through the project daemon —
`python3 tools/chrome_devtools_client.py <tool> '<json-args>'`. Never call a `chrome-devtools` MCP tool
directly: Chrome's debugging consent is per connection and raises a prompt only the person at the machine can
accept.

## My details

- Package ZIP or extracted directory: << path >>
- SQLcl saved connection: << name >>
- APEX workspace: << name >>
- Application ID: << id >>
- Theme switcher: << with | without | leave whatever the app already has >>

## Do this

1. Extract the package if needed and read its `MANUAL-INSTALL.md` and `theme.json`. Report the theme name,
   version, and whether it ships custom fonts.
2. Run the installer **in dry-run** (the default — no `--apply`):
   `./install.sh --connection <conn> --workspace <ws> --app-id <id>`
3. Read the dry-run output back to me in plain language: which static files it would add, whether it would
   create the page-0 bootstrap regions or found an existing Theme Factory install to upgrade, what it would add
   to the application's CSS file URLs, and whether the switcher can attach to a static navigation-bar list.
4. **Stop here.** Do not pass `--apply` until I tell you to.
5. After I confirm, re-run with `--apply` (plus `--with-switcher` or `--without-switcher` if I asked for one).
   The installer will ask you to type the application ID — type exactly that, nothing else.
6. Report the backup directory it wrote before importing. I need that path to roll back.
7. Verify live in the browser: load a page, confirm `<html>` carries `app-theme-<name>`, check the console is
   clean, and if a switcher was installed, open the **Theme** menu and confirm exactly one entry is checked and
   the choice survives a reload.

## Report

- The exit code and what it means. `0` success · `3` refused before touching anything (wrong APEX version,
  unsafe target, ownership conflict) · `4` the app changed in the database while staging · `5` export/compile/
  import failed · `6` imported but the post-import check disagrees with what was staged — tell me immediately ·
  `7` cancelled at the confirmation prompt.
- The backup path.
- What you verified in the browser, with the actual values you read — not "looks fine".

## Stop and ask me if

- The target is not APEX 26.1.x, or not Universal Theme 42 / Iris.
- The installer reports an ownership conflict, or that a file it would write already exists and is not ours.
- The switcher cannot attach because the navigation bar is not a static list — it will point you at
  `MANUAL-INSTALL.md`; relay that rather than rewriting my list.
- Anything returns exit `6`.
