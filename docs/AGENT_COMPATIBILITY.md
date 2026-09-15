# Agent Compatibility Matrix and Smoke Contracts

This document records the discovery paths, runtime boundaries, offline validation commands, smoke harness contracts, and latest verification results for the three supported agent runtimes: **OpenAI Codex**, **Claude Code**, and **Google Antigravity**.

## 1. Supported Discovery Paths

| Runtime | Instruction Entry | Skills Discovery | Chrome DevTools MCP Tool |
|---|---|---|---|
| **Codex** | `AGENTS.md` (canonical root instructions) | `.agents/skills/` (native read) | `chrome-devtools` |
| **Claude Code** | `CLAUDE.md` (symlink to `AGENTS.md`) | `.claude/skills/<name>` (symlinks to `.agents/skills/`) | `chrome-devtools` |
| **Antigravity** | `.agents/rules/apex-theme-factory.md` (always-on rule) | `.agents/skills/` (native; `.agent/skills` legacy symlink) | `chrome-devtools-mcp` |

- Canonical skills reside in `.agents/skills/<name>/SKILL.md`.
- Router skill for design implementation: `.agents/skills/design-to-apex/SKILL.md`.
- Supported boundary: **APEX 26.1.x / Universal Theme 42 / Iris**.
- Application import authorization: **Explicit user confirmation required**; never import without a direct user request.
- Changes during inspection: **None** (`wouldEdit: false`).

## 2. Structural Layout Verification

Run the offline structural verifier to confirm entry files, symlinks, rules, and skill metadata across all runtimes without network or model access:

```bash
scripts/check-agent-layout.sh
```

Expected output:
```text
AGENT_LAYOUT status=PASS skills=20 claude_links=20 errors=0
```

## 3. Smoke Test Harness

The smoke runner executes the runtime in read-only / plan mode with a neutral prompt (`tests/agent-smoke/readiness-prompt.md`) and validates the returned JSON against `tests/agent-smoke/result.schema.json`.

```bash
python3 tools/agent_smoke.py <codex|claude|antigravity> [--date YYYY-MM-DD]
```

### Exit and Status Semantics

- **`0` (PASS):** Runtime completed successfully, produced valid JSON conforming to the schema, identified the expected entry file and Chrome tool, and respected all safety boundaries.
- **`1` (FAIL):** Runtime executed but returned incorrect paths, wrong boundary, attempted edits, or produced invalid output.
- **`2` (UNVERIFIED):** Runtime CLI is not installed, unauthenticated, out of quota, or timed out. This is not a failure of repository compatibility, but indicates that environment prerequisites were not met.

### Nature of Evidence

When a CLI does not expose its internal loader telemetry, the recorded result serves as **behavioral evidence** that the agent discovered and respects the project boundaries when given a neutral readiness prompt.

## 4. Latest Smoke Results

| Runtime | CLI version | Checked at (UTC) | Structural | Behavioral | Evidence |
|---|---|---|---|---|---|
| Codex | codex-cli 0.149.1 | 2026-09-15 | PASS | PASS | `tests/agent-smoke/runs/2026-09-15/codex.md` |
| Claude Code | not installed | 2026-09-15 | PASS | UNVERIFIED | `tests/agent-smoke/runs/2026-09-15/claude.md` |
| Antigravity | 1.2.3 | 2026-09-15 | PASS | UNVERIFIED | `tests/agent-smoke/runs/2026-09-15/antigravity.md` |
