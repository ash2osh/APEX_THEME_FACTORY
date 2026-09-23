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

### 5.3 Don't promote a finding before its evaluation has run
- Spec §58 orders: record → classify → evidence → scope → *evaluation scenario* → confirm the old instructions fail
  it → smallest skill change → **run** the evaluations → verify → promote. Applying the skill change (step 7) is
  fine early; moving the file to `accepted/` before step 8 is not — the Codex review on PR #3 caught exactly that.
  Keep `Status: Pending — change applied; evaluation run pending` until the row in `evaluations/README.md` says
  *passed*.

### 5.4 Skills lag the architecture unless the protocol runs
- Skills still described `static-files/css/apex/` two commits after packages moved to `sample-themes/`. When
  the architecture moves, file the finding and fix the routing table in the same change (spec §58); the
  evaluation (`10-theme-package-routing.md`) is what keeps it honest.

### 5.x Evidence is bound to the last *source* commit
- Committing `.agents/evaluations/runtime/**` or Markdown moves HEAD but not the source under test;
  package banners and `release.py` bind to `lib/theme_factory/gitstate.py: last_source_commit()`
  (everything except the evidence root and `**/*.md`). Any other change — even to a tool or test —
  invalidates captured Layer C/D/E evidence and the packages' SHA-256, so finish source work, commit,
  build, capture, then commit evidence and docs.
- **The release sequence, in order — three of today's failures were this one rule in different clothes.**
  1. Commit **all** source. "Source" is wider than it looks: `sync-static.sh` output under `applications/ut/`,
     and `tests/agent-smoke/runs/**/*.json` written by a smoke re-run, both count. Only the evidence root and
     `**/*.md` do not.
  2. **Then** build the packages. Each `theme.css` embeds a `Source commit:` banner, so a package built before
     the final source commit is not what that source builds — and `release-check.sh` rejects the evidence with
     *"Evidence artifact is for a different package"*, after the capture has already cost you an hour.
  3. **Then** capture Layers C/D/E, touching nothing in the tree until it finishes.
  4. **Then** commit evidence and Markdown only — that keeps `last_source_commit` where the evidence expects it.
  A cheap guard worth adding before the next capture: assert that the `Source commit` banner inside the built
  ZIP equals `last_source_commit()` before the pipeline starts, so the mismatch fails in two seconds instead of
  fifty minutes. (Not added during this round on purpose — it is a source change, and making it would have
  invalidated the evidence it was meant to protect.)
- **Don't touch the working tree while a capture is running.** `tools/live_matrix.py` checks
  `git status --porcelain -- . :(exclude)<evidence root> :(exclude,glob)**/*.md` **at the start of each theme's
  run**, so a tree that goes dirty mid-pipeline fails the *next* theme and not the one in flight. Met
  2026-09-17: linen's Layer C captured cleanly, then re-running the three agent smokes wrote
  `tests/agent-smoke/runs/<date>/*.json` — not Markdown, not under the evidence root — and solarized-dark's
  run refused. Markdown edits are safe by construction (excluded); anything else is not. And because those
  smoke JSONs *are* source by this definition, committing them moves `last_source_commit` and stales any
  evidence captured just before — so a mid-pipeline smoke re-run costs both remaining captures **and** the one
  that had already succeeded. Start a capture from a committed tree and leave it alone until `PIPELINE_DONE`.
- **The `**/*.md` exclusion was wrong for Layer E — the tooling now catches this.** `last_source_commit()`
  treats Markdown as non-source, which is right for docs and evidence — but Layer E's *subject* is Markdown:
  the agent-readiness smokes measure what a runtime does after reading `AGENTS.md` / `.agents/rules/*.md` /
  the skills. Met 2026-09-17 (the daemon rule was added to `AGENTS.md` and the workspace rule after the three
  smokes were recorded) and handled by hand at the time — re-running `tools/agent_smoke.py` for all three
  runtimes. Fixed the same day (verification-integrity-defects plan, Task 3): `lib/theme_factory/gitstate.py`
  now has a *separate* `last_instruction_commit()` / `instruction_equivalent()` pair, scoped to
  `AGENTS.md`, `CLAUDE.md`, `.agents/rules/`, `.agents/skills/`, and `release.py` binds Layer E's raw artifacts
  (agent-runtime, agent-scenario, finding-resolution) on that instead of the general `source_equivalent`.
  Deliberately *not* folded into the shared binding: Layers C and D depend on code and package bytes, not on
  what an agent reads, so coupling them to instruction edits would force a full live re-capture (pitfalls
  above) for a wording change in a skill file. An edit to `AGENTS.md`/`.agents/rules/`/`.agents/skills/` now
  fails `release-check.sh` for Layer E by name automatically; editing `README.md` or `docs/*.md` still does
  not invalidate anything.
- **`scripts/sync-static.sh` output is source.** It writes into `applications/ut/shared-components/static-files/`,
  which is not excluded, so the ordinary import workflow (sync → validate → import) *always* produces a source
  change. Run it, commit it, and only then capture Layer C/D — capturing first and syncing afterwards costs a
  full re-record of both layers (paid on 2026-09-17). The same applies to any package-source edit: the theme
  ZIP's SHA-256 changes, so evidence bound to the old SHA is correctly rejected, even when the edit was only a
  comment.

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
- Killing `pipeline.sh` leaves its in-flight `browser_matrix.py` / `live_matrix.py` child reparented to init and
  still running — still driving the shared Chrome tab and still writing into the evidence root. Met 2026-09-17:
  the replacement run's installs raced the orphan's Layer D capture for ~90 seconds.
- Kill the worker, not just its shell: check `pgrep -af "browser_matrix|live_matrix|theme_factory.cli"` after any
  `pkill`, and wait for an in-flight `install`/`uninstall` to finish before stopping a pipeline, so no consumer app
  is left half-imported. (The bracket trick from §5.x still applies — `pipeline1[8].sh` so the pattern does not
  match the `pkill` command line itself.)
