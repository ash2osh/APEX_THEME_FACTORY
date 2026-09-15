# Agent Runtime Compatibility Design

**Date:** 2026-09-15
**Status:** Approved for implementation planning
**Scope:** Codex, Claude Code, and Google Antigravity project discovery and smoke verification

## 1. Purpose

Make the repository reliably self-describing to Codex, Claude Code, and Google Antigravity without duplicating the 1,432-line engineering specification into every runtime's always-loaded context. All three agents must receive the same non-negotiable project boundary and discover the same focused skills.

## 2. Goals

- Keep `AGENTS.md` as the concise canonical project entry point.
- Preserve `CLAUDE.md -> AGENTS.md` for Claude Code.
- Expose the same 20 project skills through each runtime's documented discovery path.
- Add an Antigravity workspace rule so project-wide constraints load even when no design skill is selected.
- Keep legacy `.agent/skills` compatibility without documenting it as the canonical Antigravity path.
- Replace the stale repository-initialization sample prompt.
- Provide deterministic structural checks and separately recorded live agent smoke tests.
- Keep permissions safe: smoke tests are read-only and never import, commit, or edit application source.

## 3. Discovery Layout

```text
AGENTS.md                              canonical concise instructions
CLAUDE.md -> AGENTS.md                 Claude project instructions
.agents/rules/apex-theme-factory.md    Antigravity workspace rule
.agents/skills/<name>/SKILL.md         canonical skill sources; Codex and Antigravity
.claude/skills/<name> -> ../../.agents/skills/<name>
.agent/skills -> ../.agents/skills     legacy compatibility only
```

`AGENTS.md` remains below Codex's default project-instruction byte limit and Claude's recommended concise size. It contains only always-applicable requirements:

- read `docs/AGENT_SPEC.md` and `docs/PROJECT.md`;
- APEX 26.1.x / Universal Theme 42 / Iris boundary;
- runtime truth through Chrome DevTools MCP;
- APEXLang source and explicit-import authorization;
- CSS/Alpine ownership boundaries;
- mandatory pitfalls review before theme/runtime/import work.

Detailed workflows remain in skills and docs so they load on demand.

## 4. Antigravity Workspace Rule

`.agents/rules/apex-theme-factory.md` repeats the concise non-negotiables rather than relying on Antigravity to interpret `AGENTS.md`. It is always active for the workspace and stays below Antigravity's 12,000-character rule limit.

The rule identifies `.agents/skills/design-to-apex/SKILL.md` as the router for design implementation, but does not force every non-design task to load it. It names the Chrome server as `chrome-devtools-mcp` while the shared skill documents the runtime-specific server aliases.

## 5. Documentation Corrections

`.agents/README.md` must describe:

- Codex canonical skills: `.agents/skills/`;
- Claude canonical skills: `.claude/skills/` symlinks;
- Antigravity canonical skills: `.agents/skills/`;
- `.agent/skills` as legacy compatibility only;
- root instruction/rule discovery separately from skill discovery.

`sample-prompts/init.md` becomes an idempotent session-readiness prompt. It must not run `git init`, create commits, assume the repository is new, import APEX, or change user configuration. It asks the agent to report:

1. active project instructions and relevant skills;
2. git branch and worktree status;
3. APEXLang validation result;
4. Chrome runtime identity and Iris status;
5. any source/runtime drift;
6. a stop before implementation.

`docs/AGENT_COMPATIBILITY.md` records supported discovery paths, MCP server names, installed versions used during the latest smoke run, exact smoke commands, expected structured results, and limits of structural-only validation.

## 6. Structural Verification

`scripts/check-agent-layout.sh` performs no network or model calls. It verifies:

- `AGENTS.md` exists, is non-empty, and stays below 32 KiB;
- `CLAUDE.md` resolves to repository `AGENTS.md`;
- Antigravity's workspace rule exists and stays below 12,000 characters;
- every canonical skill has `SKILL.md` with YAML delimiters, `name`, and `description`;
- skill names are unique and match their directory names;
- every `.claude/skills/<name>` symlink resolves to the matching canonical directory;
- `.agent/skills` resolves to `.agents/skills`;
- the runtime documentation lists the canonical paths accurately;
- the initialization prompt contains no `git init`, commit, import, permission bypass, or destructive command.

It prints one machine-readable summary line and exits non-zero on any mismatch.

## 7. Live Smoke Tests

Live smoke tests use a common prompt stored at `tests/agent-smoke/readiness-prompt.md`. The prompt requests JSON with:

```json
{
  "runtime": "codex|claude|antigravity",
  "instructionEntry": "path",
  "routerSkill": "path",
  "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
  "runtimeTruthTool": "server name",
  "importRequiresUserRequest": true,
  "wouldEdit": false
}
```

Commands run from the repository root in read-only/plan mode:

```bash
codex exec --ephemeral --sandbox read-only --output-schema tests/agent-smoke/result.schema.json "$(cat tests/agent-smoke/readiness-prompt.md)"
claude -p --permission-mode plan --no-session-persistence --json-schema "$(cat tests/agent-smoke/result.schema.json)" "$(cat tests/agent-smoke/readiness-prompt.md)"
agy -p --mode plan --sandbox --json-schema tests/agent-smoke/result.schema.json "$(cat tests/agent-smoke/readiness-prompt.md)"
```

The harness never uses any permission-bypass flag. Because these commands consume external model quota and depend on authentication, CI does not run them automatically. A maintainer runs them for a release and stores redacted results in `tests/agent-smoke/runs/<date>/`.

The recorded result includes CLI version, exit code, JSON response, and pass/fail assertions. It excludes conversation identifiers, credentials, home-directory paths, and full environment dumps.

## 8. Runtime-Specific Acceptance

### Codex

- Reports root `AGENTS.md` as the repository instruction entry.
- Discovers `.agents/skills/design-to-apex/SKILL.md`.
- Names `chrome-devtools` as the configured runtime-truth server.
- Refuses to import without an explicit user request.

### Claude Code

- Reports `CLAUDE.md`, resolving to `AGENTS.md`.
- Discovers `.claude/skills/design-to-apex/SKILL.md` through the project symlink.
- Names `chrome-devtools` as the configured runtime-truth server.
- Remains in plan mode and does not edit.

### Antigravity

- Reports `.agents/rules/apex-theme-factory.md` as an active workspace rule.
- Discovers `.agents/skills/design-to-apex/SKILL.md`.
- Names `chrome-devtools-mcp` as the configured runtime-truth server.
- Remains in plan/sandbox mode and does not edit.

## 9. Failure Semantics

- Structural failures identify the exact missing or broken path.
- A model authentication or quota failure is `UNVERIFIED`, not a compatibility failure.
- A valid response that omits or contradicts a non-negotiable requirement is `FAIL`.
- A runtime that cannot expose loaded instruction/skill paths is tested by asking it to state the rules and cite the files; the result must be labeled behavioral evidence rather than loader telemetry.
- One runtime's pass never substitutes for another runtime's smoke result.

## 10. Acceptance Criteria

- Structural verification passes for all three layouts.
- The stale initialization prompt is removed.
- Canonical and legacy paths are documented without contradiction.
- Codex, Claude Code, and Antigravity each have a dated passing smoke record produced with read-only/plan permissions.
- Each runtime identifies the same architecture and import boundary.
- No smoke test modifies the worktree, live APEX application, global agent configuration, or MCP configuration.
