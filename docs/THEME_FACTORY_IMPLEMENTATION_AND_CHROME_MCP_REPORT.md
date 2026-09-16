# APEX Theme Factory — Implementation Review and Verification Status

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
Layer C (live import) remains UNVERIFIED until an authorised `--apply` cycle is run against disposable consumers.

## Verdict

The repository implements the source, packaging, installer, documentation, runtime-client, and agent-layout foundations of the Theme Factory. Offline verification can prove those contracts. The project is **not yet release-verified** across all five evidence layers because the required disposable-consumer, full browser matrix, and three-agent behavioral artifacts are not retained.

The earlier report's `VERIFIED` claims for Apps 9010/9011, all matrix rows, both release packages, and all agent evaluations were unsupported by files in the repository. Those claims are withdrawn. Missing proof is recorded as `UNVERIFIED`, not converted into a pass.

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

| Layer | Meaning | Current status | Limit |
|---|---|---|---|
| A | Repository source | Pending final clean-tree gate | A dirty implementation worktree cannot be release-verified. |
| B | Package artifact | Pending final rebuilt ZIP verification | Must be run after the final commit from a clean tree. |
| C | Database installation | UNVERIFIED | No retained digest-bound two-consumer install/coexistence/uninstall/restore run. |
| D | Browser runtime | UNVERIFIED | Page 409 is narrow evidence; the required per-theme consumer matrix is absent. |
| E | Agent behavior | UNVERIFIED | Claude Code and Antigravity smokes and scenarios 04, 05, 09, 11, and 14 remain incomplete. |

The release checker now uses the specification's taxonomy: A source, B package, C database, D browser, E agent. Legacy arbitrary JSON lists and summary-only claims are rejected. A `PASS` or `FAIL` claim must reference an in-directory JSON artifact and match its SHA-256 digest. PASS summaries must also reference the raw SQLcl, browser-matrix, or agent-run JSON behind each required result. Summary and raw artifacts are bound to one theme, the exact 40-character Git commit, and the packaged ZIP SHA-256.

## Required work before a `VERIFIED` release

1. From a clean commit, run the complete offline gate and rebuild/verify each single-theme ZIP.
2. With explicit database-write authorization, provision two disposable APEX consumers and retain SQLcl artifacts for install, reinstall, coexistence, switcher transitions, uninstall, restore, and unrelated-component preservation.
3. Capture the full Linen and Solarized Dark browser matrix at all required widths, including fonts, Font APEX, keyboard, console, network, contrast, refresh, persistence, and dialog/report/grid states.
4. Run complete behavioral compatibility checks for Codex, Claude Code, and Antigravity and close or retain each open evaluation/finding with evidence.
5. Bind every passing live claim to a retained artifact digest, then generate the release report. Until then, the correct verdict is `UNVERIFIED`.
