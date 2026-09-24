# Pitfalls §5 — Workflow

Part of the [pitfalls index](../pitfalls.md); entry numbers are stable and cited as `pitfalls §5.N`.

## 5. Workflow

### 5.1 Another agent may be editing the same tree
- 2026-09-14: a Codex session authored `sample-themes/solarized-dark/` while this session worked; files changed
  mid-read and the live app already held its import. Check `find sample-themes -type f -mmin -30` and
  `ps aux | grep codex` before touching a package; say what you are doing; commit only what you own — or,
  when the user asks you to take the package over, say that too.
- The repo has a **Codex PR review bot** (`chatgpt-codex-connector`); it comments with P-level findings on
  every PR. Verify each at runtime before acting (2026-09-14: one P2, real, fixed).

### 5.2 Review before claiming
- The first Solarized Dark draft claimed 6.7:1 for a 4.75:1 pair, had 6 uncommented `!important`s, 30+ repeated
  literals and iteration PNGs in `preview/`. The package conventions in `sample-themes/README.md` exist so the
  next package starts from the checklist, not from a linen copy.

### 5.5 Hardcoding a package version in a helper script silently skips a theme
- A capture driver written as `--package-root $S/pk/$t-1.0.0` keeps working until a theme is version-bumped,
  and then fails for exactly one theme while the other proceeds normally. Met 2026-09-17: `solarized-dark` went
  to 1.1.0 for its custom fonts, and the Layer D phase installed only `linen` into both consumer apps. The
  installer refused correctly (*"Missing checksums.sha256 in .../solarized-dark-1.0.0"*) — the damage was that
  the run continued and began measuring a half-installed estate.
- Resolve the package instead of naming it: `ls dist/$t/$t-*.zip | head -1`, and echo the resolved filename
  into the log so the binding is visible in the evidence trail rather than implied by the script.
- The same applies to the extracted package root: derive it from the ZIP's basename, never re-spell the version.

### 5.6 `pkill` on a wrapper shell orphans the Python process doing the work
- Killing a wrapper shell (`scripts/theme.sh release …`, met 2026-09-17 with the since-removed release pipeline)
  leaves its in-flight Python child (`python3 -m lib.theme_factory.cli`, `tools/release_smoke.py`) reparented to
  init and still running — still driving the shared Chrome tab and still importing into the consumer app. The
  replacement run's installs raced the orphan for ~90 seconds.
- Kill the worker, not just its shell: check `pgrep -af "theme_factory.cli|release_smoke|browser_check"` after any
  `pkill`, and wait for an in-flight `install`/`uninstall` to finish before stopping a run, so no consumer app
  is left half-imported. (Bracket one character, e.g. `release_smok[e]`, so the pattern does not match the
  `pkill` command line itself.)

### 5.7 The live smoke needs a clean consumer app
- `scripts/theme.sh release NAME` exports consumer 9010 first, refuses it if it already carries Theme Factory
  packages, and re-imports that clean export when it finishes. Met 2026-09-23: 9010/9011 held linen 1.0.0 and
  solarized-dark 1.1.0 (stale `dist/` ZIPs the old `install-all-themes` fallback picked up) and every lifecycle
  check failed. Clear leftovers with `scripts/reset-consumer.sh`.
