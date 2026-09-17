Remove a Theme Factory theme from my Oracle APEX application, or roll back an install.

**Boundary:** APEX 26.1.x · Universal Theme 42 · Iris.
**Blast radius:** this writes to a database and can delete files it owns. Dry-run first; **stop for my
explicit go-ahead before `--apply`.**
**Browser access:** only through the project daemon —
`python3 tools/chrome_devtools_client.py <tool> '<json-args>'`.

## My details

- Package directory (or the installed theme name): << value >>
- SQLcl saved connection / workspace / application ID: << values >>
- What I want: << remove the theme | roll back to the pre-install backup >>

## If I asked to remove the theme

1. Dry-run: `./uninstall.sh --connection <conn> --workspace <ws> --app-id <id>`.
2. Report what it would delete. It removes only what `registry.json` records as owned, and it refuses if any
   owned file's SHA-256 has changed since install — if that happens, tell me **which file** rather than looking
   for a way around it. A changed file means someone edited it and it must not be silently deleted.
3. Stop. After I confirm, re-run with `--apply` and type the application ID when prompted.
4. Say what the app is left on: if another Theme Factory package is still installed it stays working and
   becomes the default; if it was the last one, the app returns to bare Iris with the bootstrap regions and the
   CSS file URL gone.
5. Verify live: reload a page, confirm `<html>` no longer carries `app-theme-<name>`, and the console is clean.

## If I asked to roll back

1. Find the backup directory written before the install (`./theme-factory-backups/<WS>-<APP_ID>/<timestamp>/`)
   and report which timestamps exist.
2. Warn me explicitly: restore replaces the **whole application** with the backup, so anything I changed in the
   app after the install is lost. The tool refuses unless `--discard-later-changes` is passed — do not pass it
   until I have said, in writing, that I accept losing those changes.
3. Run it from the extracted package directory:
   `PYTHONPATH=. python3 -m lib.theme_factory.cli restore --connection <conn> --workspace <ws> --app-id <id> --backup <dir> --apply`
4. If the tool reports the backup itself has been modified, stop — a tampered backup is refused by design and
   restoring it is not something to force.

## Report

Exit code, what was removed or restored, and what you confirmed in the browser with actual values.
