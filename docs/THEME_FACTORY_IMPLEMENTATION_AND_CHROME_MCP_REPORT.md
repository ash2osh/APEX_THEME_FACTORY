# APEX Theme Factory — Implementation Review and Verification Status

**Reviewed:** 2026-09-16
**Boundary:** APEX 26.1.x, Universal Theme 42, base theme `ut-26.1`, Iris only

## Verdict

The repository implements the source, packaging, installer, documentation, runtime-client, and agent-layout foundations of the Theme Factory. Offline verification can prove those contracts. The project is **not yet release-verified** across all five evidence layers because the required disposable-consumer, full browser matrix, and three-agent behavioral artifacts are not retained.

The earlier report's `VERIFIED` claims for Apps 9010/9011, all matrix rows, both release packages, and all agent evaluations were unsupported by files in the repository. Those claims are withdrawn. Missing proof is recorded as `UNVERIFIED`, not converted into a pass.

## Confirmed implementation

- **Single-theme portable ZIPs:** deterministic archive construction, strict member/path/checksum validation, no unlisted files, required cover/runtime/scripts/manual, CSS policy enforcement, and exact package identity checks.
- **APEX boundary:** package manifests and SQLcl preflight require APEX 26.1.x, Universal Theme 42, base theme `ut-26.1`, and Iris.
- **Installer lifecycle:** dry-run by default, explicit application-ID confirmation before import, immutable backup, drift guard, validation, post-import checks, optional switcher, per-browser/device persistence, uninstall, and restore.
- **Destructive safety:** registry parsing fails closed; installed package ownership is digest-bound; upgrades remove only a verified prior version; uninstalls reject unowned or modified files; backup restore verifies the recorded digest; managed APEX components require marker ownership.
- **Custom fonts:** only declared WOFF2 files are packaged, signatures and licenses are checked, and undeclared font files are rejected.
- **Manual installation:** each ZIP contains theme-specific Builder instructions with a fully rendered bootstrap, exact static-file paths, optional switcher steps, the actual localStorage key, and complete uninstall guidance.
- **Agent structure:** Codex, Claude Code, and Antigravity discovery layouts are structurally checked. Structural compatibility is not the same as completed behavioral evaluation.

## Chrome DevTools MCP status

- A persistent daemon was started before remediation and tested without additional Chrome prompts.
- Live checks confirmed the open page is App 102, Page 409, with `body.apex-theme-iris` and `html.app-theme-solarized-dark`.
- The daemon implementation now uses a per-user private socket directory, mode `0600`, refuses unsafe pre-existing paths, restricts callable tools, drains stderr, validates initialization, limits requests, and makes automatic spawning explicit rather than silent.
- The original approved daemon process remains active at `/tmp/chrome_mcp.sock` for this session. Starting a second MCP process concurrently blocked behind the existing Chrome connection, so it was stopped without disturbing the working prompt-free session. The hardened daemon becomes active on the next deliberate restart.

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
