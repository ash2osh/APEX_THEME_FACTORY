Verify a theme package for release and report the honest verdict.

**Boundary:** APEX 26.1.x · UT 42 · Iris.
**Blast radius:** **read-only with respect to source.** Do not edit source to make a check pass. Do not import
into app 102. The live database layer touches only disposable consumer fixtures, and only if I have said so.
**Browser access:** project daemon only — `python3 tools/chrome_devtools_client.py <tool> '<json-args>'`.

## My target

- Theme: << name >>
- How far to go: << offline only (Layers A–B) | full (A–E, needs the live database and Chrome) >>

## The rule that matters

A layer passes **only** with a retained artifact bound by SHA-256 to the package and to the last source commit.
A missing layer is `UNVERIFIED`, never a pass. Do not convert absent database, browser or agent evidence into a
PASS, and do not treat one page as proof of a matrix.

## Do this

1. `bash tests/run-offline.sh` — Layers A and B. It refuses a dirty tree on purpose; if it does, show me
   `git status` rather than setting `THEME_FACTORY_ALLOW_DIRTY=1`.
2. **Order matters, and getting it wrong costs an hour.** Commit all source first — including
   `sync-static.sh` output under `applications/ut/` and any `tests/agent-smoke/runs/**/*.json`, both of which
   count as source. *Then* build the packages: each `theme.css` embeds a `Source commit:` banner, so a package
   built before the final source commit is not what that source builds, and the evidence will be rejected as
   "for a different package". *Then* capture evidence, touching nothing in the tree until it finishes. *Then*
   commit evidence and Markdown only.
3. If I asked for the full run: capture Layer C (`tools/live_matrix.py`) and Layer D
   (`tools/browser_matrix.py`) against the disposable consumers, and Layer E (`tools/agent_smoke.py` for each
   runtime, plus the evaluation scenario records).
4. `scripts/release-check.sh <theme>` — it exits non-zero unless every layer passes, and writes
   `dist/<theme>/RELEASE-REPORT.md`.

## Report

- The per-layer table with each artifact path, and the verdict.
- For any layer that is not PASS: exactly what evidence is missing and what would produce it. Be specific
  enough that someone could go and get it.
- The bounds of a PASS: which pages, widths and states the evidence actually covers, and which it does not.
  A verdict that hides its coverage is worse than an honest `UNVERIFIED`.

## Stop and tell me if

- An artifact's commit or package SHA does not match — that means the evidence and the package have drifted
  apart, and re-running the check will not fix it.
- A check fails. Report it; do not adjust the check, the thresholds, or the evidence to make it pass.
