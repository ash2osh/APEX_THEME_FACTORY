# APEX Theme Factory — Implementation Review and Verification Status

> **Migration note (2026-09-20):** The A–E tables and verdict language in this historical report describe
> the former release contract. Current theme releases use Layers A–D only; project-level agent compatibility
> is validated once per instruction revision in [docs/AGENT_COMPATIBILITY.md](AGENT_COMPATIBILITY.md). The
> historical Layer E evidence below remains retained for audit and is not a current theme gate.

**Reviewed:** 2026-09-16 (independent review of `fd8aad4`, fixes applied the same day)
**Boundary:** APEX 26.1.x, Universal Theme 42, base theme `ut-26.1`, Iris only

## 2026-09-16 review findings and corrections

An independent read-only review of `fd8aad4` found that the installer could not survive a real APEX
re-export, and fixed the following in the working tree (all covered by `tests/run-offline.sh`):

| Sev | Finding | Correction |
|---|---|---|
| P0 | Ownership was recorded as APEXLang `//` comment markers. APEX never stores comments, so every real re-export was comment-free and reinstall, upgrade, second-package install and uninstall were refused as "collisions". | Ownership now lives in data APEX keeps: Page 0 regions carry `advanced { htmlDomId: theme_factory_bootstrap[_dialog] }` plus an HTML marker inside their source; switcher entries use the `theme-factory-` static-id namespace; file digests stay in `registry.json`. `strip_bootstrap_regions` / `strip_switcher_entries` parse blocks instead of comment spans. |
| P1 | Post-import verification required a byte-identical re-export. SQLcl re-indents fenced code, sorts `file` blocks and drops comments, so every real `--apply` would have ended `IMPORTED_POSTCHECK_FAILED`. | Install and uninstall compare `theme_factory_projection()` (URLs, declared and physical static files with digests, registry, owned regions, switcher entries, page set) between the staged and post-import export. |
| P1 | `--with-switcher` never produced a switcher on real targets: SQLcl exports all lists into `shared-components/lists.apx` (the code looked for `navigation-bar.apx`), the generated entry grammar used the invalid `cssClasses` property, and no `javaScript {}` block was created when the target had none. | The navigation bar is resolved through `navigationBar { list: @alias }`, must be a static list (otherwise the install refuses and points to `MANUAL-INSTALL.md`), entries use the exported grammar (`layout`, `link.target`, `icon`, `userDefinedAttributes { 2 }`), and the `javaScript {}` block is created when needed. Real `apex validate` accepted the result against DEMO app 104 (dry-run, no import). |
| P2 | Chrome MCP daemon: no request timeout (one unanswered call wedged every client), crash on SIGINT, stale socket on SIGTERM. | Reader thread with per-request queues and `THEME_FACTORY_CHROME_MCP_TIMEOUT`; signal handlers; ordered shutdown; client-side timeout. |
| P2 | Claude Code smoke could never run: the shared schema's `$schema` pointer is rejected by `claude --json-schema`. | Dialect pointer removed; a rejected schema is classified `FAIL` (harness defect), CLI envelope errors are surfaced. |
| P2 | Theme file chosen by glob order; `templateOptions.navigationMenuStyle` parsed but never applied; unsupported targets exited 2 instead of 3. | Theme resolved via `userInterface.currentTheme`; navigation style applied to `@/side-navigation-menu` template options; exit 3 for every unsupported-target refusal. |
| P2 | Restore silently discarded changes made after the backed-up operation. | `target.json` records `postOperationDigest`; restore refuses (exit 7) unless `--discard-later-changes`. |
| P2 | `scripts/release-check.sh` crashed with its default evidence directory. | Per-theme evidence folders are discovered from the evidence root; `PackageError` is reported without a traceback. |
| P3 | Staging exports were never removed (1,138 leftovers in `/tmp`); tests polluted `./theme-factory-backups` and `/tmp`; wrappers claimed but did not check Python 3.10+; stray non-WOFF2 files under `fonts/` were ignored; README restore command was wrong; `scripts/apply-theme.sh` read an obsolete manifest key; cancellation exited 0. | All corrected; cancellation exits 7. |

The offline fake `sql` now re-exports through `tests/fixtures/bin/apexlang_roundtrip.py`, which reproduces
the observed SQLcl transforms, and `tests/test_lifecycle_real_shape.py` drives install → reinstall →
coexistence → switcher off → uninstall → uninstall → restore against a fixture cut from a real consumer export.
Layer C (live import) is PASS: authorised `--apply` cycles were run against the disposable consumers on 2026-09-16 and re-recorded on 2026-09-17.

## Verdict (updated 2026-09-17, after the verification-integrity remediation)

Layers A–E are **PASS** for all four single-theme packages — `linen`, `solarized-dark`, `estate-slate`,
`estate-slate-dark` — with retained, digest-bound evidence at commit `7ac2e0204ca0`, so the release verdict
for each is **VERIFIED**. `solarized-dark` 1.1.0 ships five licensed WOFF2 faces and `estate-slate` /
`estate-slate-dark` ship four each; all are proven loaded from their package on every Layer D row. What closed
Layer E: all three runtime smokes pass (Codex and Claude Code 2026-09-16, Antigravity 2026-09-17 once its
provider had capacity), evaluation scenarios 04, 05, 09, 11 and 14 all pass, and both remaining findings were
promoted to `accepted` after the measurements that had been missing were taken against the imported build.

`estate-slate` and `estate-slate-dark` were committed 2026-09-17 (`a38076b`) by a concurrent session with no
Layer C/D/E evidence at all and no row in this report or `tests/live/RELEASE-MATRIX.md` — invisible to the
release system rather than flagged as unverified. Closed the same day as Task 6 of the verification-integrity
remediation (below): two more consumer fixtures were provisioned (9012 minimal, 9013 business) and both themes
were captured through the same Layer C/D/E pipeline as `linen`/`solarized-dark`.

Between the 2026-09-17 post-import round and this one, six defects were found and fixed in the verification
system itself — not in any theme — documented in
the 2026-09-17 verification-integrity-defects plan (removed 2026-09-23; see git history) and `.agents/knowledge/pitfalls.md` §4.6
and §5.5–5.6: the runtime-evidence schema went from documented-but-unenforced to validated at the gate; the
gate now checks font-evidence *completeness* (a count and a per-face check), not just its presence; Layer E
binds on instruction Markdown specifically, separate from the general source binding Layers C/D use; both
capture drivers re-check the working tree before each unit of live work, not only at start; `sync-static.sh`
stopped declaring `charSet` on binary files; and every `sample-themes/` directory is now checked to be either
verified or explicitly marked otherwise (`scripts/check-sample-themes-coverage.sh`). One of these — the font
evidence check — found a real measurement defect while the fix for another was being validated: a probe that
asked "did this page happen to use the face" rather than "is the face usable" had reported `solarized-dark`'s
mono face as missing on all 12 rows of the *previous* capture, when it was in fact correctly packaged and
served. Fixed and re-verified live before this evidence was captured.

The verdict is bounded by what the evidence covers, and the bounds are recorded rather than waived: app 102's
AA sweep covers 24 of its 122 pages at 1440 plus 4 at 375 (Layer D covers the consumer apps at all four
widths), and selection states beyond the Interactive Grid, keyboard focus rings and further chip/error states
are untested — see `.agents/findings/accepted/2026-09-14-solarized-dark-2page-coverage-gap.md`. `estate-slate`
and `estate-slate-dark` have the same automated per-row Layer D coverage as the other two themes but have not
had a dedicated multi-page driven-state accessibility sweep the way `solarized-dark` did. No known code defect
remains open.

The earlier report's `VERIFIED` claims for Apps 9010/9011 (2026-09-15) were withdrawn; they are now replaced by
actual evidence captured on the same application IDs, re-provisioned from the committed fixtures.

## Confirmed implementation

- **Single-theme portable ZIPs:** deterministic archive construction, strict member/path/checksum validation, no unlisted files, required cover/runtime/scripts/manual, CSS policy enforcement, and exact package identity checks.
- **APEX boundary:** package manifests and SQLcl preflight require APEX 26.1.x, Universal Theme 42, base theme `ut-26.1`, and Iris.
- **Installer lifecycle:** dry-run by default, explicit application-ID confirmation before import, immutable backup, drift guard, validation, post-import checks, optional switcher, per-browser/device persistence, uninstall, and restore.
- **Destructive safety:** registry parsing fails closed; installed package ownership is digest-bound; upgrades remove only a verified prior version; uninstalls reject unowned or modified files; backup restore verifies the recorded digest and refuses stale restores; managed APEX components are recognised by round-tripped identity (Static IDs, HTML marker, static-id namespace), never by APEXLang comments.
- **Custom fonts:** only declared WOFF2 files are packaged, signatures and licenses are checked, and undeclared font files are rejected.
- **Manual installation:** each ZIP contains theme-specific Builder instructions with a fully rendered bootstrap, exact static-file paths, optional switcher steps, the actual localStorage key, and complete uninstall guidance.
- **Agent structure:** Codex, Claude Code, and Antigravity discovery layouts are structurally checked. Structural compatibility is not the same as completed behavioral evaluation.

## Chrome DevTools MCP status

- A persistent daemon was started before remediation and tested without additional Chrome prompts.
- Live checks confirmed the open page is App 102, Page 409, with `body.apex-theme-iris` and `html.app-theme-solarized-dark`.
- The daemon implementation uses a per-user private socket directory, mode `0600`, refuses unsafe pre-existing paths, forwards only known chrome-devtools-mcp tools, drains stderr, validates initialization, limits request size, times out unanswered requests without blocking other clients, shuts down cleanly on signals, and makes automatic spawning explicit rather than silent.
- The original approved daemon process remains active at `/tmp/chrome_mcp.sock`. A second `chrome-devtools-mcp --autoConnect` instance started while it holds the Chrome connection never answers tool calls (observed again 2026-09-16); the daemon now reports that as a timeout instead of wedging. Use `THEME_FACTORY_CHROME_MCP_SOCKET=/tmp/chrome_mcp.sock` to reuse the approved session.

## Evidence layers

| Layer | Meaning | Status (2026-09-17) | Evidence |
|---|---|---|---|
| A | Repository source | PASS | clean tree, `tests/run-offline.sh` (208 + 11 + 113 test runs), `AGENT_LAYOUT status=PASS` |
| B | Package artifact | PASS | deterministic ZIPs, `verify-package`, `RELEASE-REPORT.md` |
| C | Database installation | PASS (both themes) | `tools/live_matrix.py` on TF-CONSUMER-MINIMAL-9010 and TF-CONSUMER-BUSINESS-9011, APEX 26.1.4: install, stale-restore guard, reinstall, switcher on/off, coexistence, uninstall ×2, unrelated-file preservation, restore — `2026-09-17-release-` (pruned 2026-09-23; in git history)<theme>/` |
| D | Browser runtime | PASS (both themes, 12 rows each) | `tools/browser_matrix.py` through the Chrome MCP daemon: both consumers at 1440/1024/768/375 + business Reports/Widgets; zero console errors, zero failed requests, AA contrast clean, keyboard-operable switcher, persisted selection, Font APEX intact |
| E | Agent behavior | PASS (both themes) | three runtime smokes PASS (`tests/agent-smoke/runs/2026-09-16/{codex,claude}.json`, `2026-09-17/antigravity.json`); scenarios 04, 05, 09, 11, 14 PASS; 0 pending findings — `2026-09-17-release-<theme>/agent_behavior_matrix.json` + `raw/` |

Live findings fixed during the matrix: empty `fileUrls` after switcher disable / last uninstall, a `file` block
on line 1 surviving uninstall (both invisible to the fake SQLcl until it gained the compiler checks in
`tests/fixtures/bin/apexlang_lint.py`), and Solarized Dark's default calendar events at 3.3:1.

## Work completed for the `VERIFIED` release, and what it does not cover

1. ~~Authenticate the Claude Code CLI and re-run its smoke.~~ Done 2026-09-16 (PASS). Antigravity followed on
   2026-09-17 once its provider had capacity — its 2026-09-16 `UNVERIFIED` was a `503 No capacity`, confirmed
   by a control run against the previous schema, not a repository defect.
2. ~~Run scenarios 04, 05, 09, 11, 14 and resolve the pending findings.~~ Done. 09 and 14 were graded
   2026-09-16; 04, 05 and 11 were blocked on an APEX import, which the user ran on 2026-09-17, and are graded
   in `.agents/evaluations/runs/2026-09-17/`. Both remaining findings are promoted to `accepted`.
3. ~~Regenerate `scripts/release-check.sh <theme>`.~~ Done — the verdict is `VERIFIED` for both themes.

**What `VERIFIED` here does not claim:** 98 of app 102's 122 pages were never opened under either package, the
1024/768 widths were exercised on the consumer apps but not on app 102, and interaction states beyond those
listed in the scenario-11 run log are untested. Scenarios 04, 05 and 11 were closed by grader measurement
against the imported build rather than by fresh evaluee sessions; each run log says so in its own header, and
scenario 05 additionally records that the evaluee's own CSS was never committed and so could not be the
imported artifact.
